# Spec — Real USB-camera capture (desktop, VID/PID → device selection)

Status: **DESIGN.** No code in this spec is implemented yet — it is written to be reviewed and
implemented on explicit request. Scope is **desktop Linux/Windows real capture**; Android real capture
stays deferred (cross-refs `docs/SPEC_android_port.md` §6 and the `CaptureBackend` scaffold).

Goal: capture real frames from the USB spectrometer camera the same way the app already renders the
virtual device — so a **non-virtual** `SpectrometerSensor` drives the calibration, wavelength-calibration
**and measurement** flows off a live camera, with the **right physical device** selected automatically
from its USB VID/PID (not a hardcoded index).

---

## 0. Grounding — verified on this machine (2026-07-05)

The camera Edwin has plugged in **is already in the device catalog**:

- `lsusb` → `ID 32e4:8830 HD USB Camera` — this is the `elp4KDevice` (ELP, `vendorId=32e4`,
  `modelId=8830`, `isVirtual=False`) hardcoded in
  `spectracsPy-model/.../logic/model/util/spectrometerSensor/SpectrometerSensorUtil.py`.
- `cv2.VideoCapture(0, CAP_V4L2).read()` **works today** → BGR `uint8` `(H,W,3)` numpy array
  (defaulted to 640×480; camera advertises MJPEG + YUYV up to 3264×2448).
- The camera exposes **two** `/dev/video*` nodes (`video0`, `video1`) — `video1` is the UVC **metadata**
  node and is *not* capturable (`VideoCapture(1)` fails to open). This is normal for UVC and is the whole
  reason "device index" ≠ "USB device."
- Sysfs cleanly disambiguates them:
  `/sys/class/video4linux/videoN/device/../idVendor` + `idProduct` give the USB VID/PID, and
  `/sys/class/video4linux/videoN/index` = **0 for the capture node, 1 for the metadata node**.
- Dependency reality: `opencv-python-headless`, `numpy`, `pyusb` present; **`PySide6.QtMultimedia`
  is not installed** → QCamera is *not* an option, cv2 is the path (matches current code).

So the hardware and the cv2 path already work. What's missing is **(a)** picking the correct device
instead of `0`, **(b)** routing every capture site through one backend, and **(c)** a real-capture branch
in the workflow "Measure" step.

**End-to-end verified 2026-07-05** (standalone probe `camera_capture_probe.py` at repo root, kept as a
retest tool — not app code):
resolver picked cv2 index 0 for the ELP by VID/PID, opened it, and captured a **real dispersed spectrum**
(1600×1200, horizontal blue→red band) once a lamp illuminated the slit. Three findings that shape the
design below:
- **Do not hard-force MJPG.** On OpenCV 4.13 (newer than the app's pinned 4.7) forcing MJPG raised inside
  `cap.read()` on empty warm-up buffers and *wedged the UVC stream*. The backend must tolerate empty/failed
  reads (never let `read()` raise) and should prefer raw/YUYV or fall back to it.
- **USB link matters.** The camera is a USB-2 UVC device; behind a hub it failed with kernel `-71 (EPROTO)`
  and delivered zero frames (`select() timeout`). Direct-to-port fixed it. Worth a diagnostic hint in the
  not-connected path (distinguish "no device" from "device present but no frames").
- **Exposure must be configurable.** Auto-exposure meters correctly for a bright source (mean ~72) but
  parks at a near-black value (exp 78, mean ~0) for faint light; manual exposure/gain recovered signal.
  This answers open-question #4 in part — see §7.

---

## 1. Current state — what exists, what's hardcoded

| Piece | File | State |
|---|---|---|
| Real capture engine | `.../logic/appliction/video/VideoThread.py` `run()` L51, `__capturePhysicalFrame()` L105 | **Works.** `cv2.VideoCapture(videoDeviceId)` with **`videoDeviceId = 0` hardcoded (L62, `#todo:hardCoded`)**; MJPG/1920×1080; linux exposure 150 / win32 −3; emits `QImage(Format_RGB888)`. |
| Backend abstraction | `.../video/capture/CaptureBackend.py` | **Scaffold only, not wired.** `DesktopCv2CaptureBackend` duplicates the VideoThread cv2 path; `getCaptureBackend()` platform-picks. VideoThread does **not** route through it yet. |
| USB presence check | `.../logic/model/util/spectrometerSensor/ApplicationSpectrometerUtil.py` `isSensorConnected()` L11 | **Works.** `usb.core.find(idVendor, idProduct)` from the sensor's `vendorId`/`modelId`. **But there is no mapping from a found USB device to a cv2 index** — this only answers yes/no. |
| Device catalog | `SpectrometerSensorUtil.getSpectrometerSensors()` | 3 devices: `virtualDevice` (`isVirtual=True`), `microdiaDevice` (0c45/6366), `elp4KDevice` (32e4/8830). |
| Domain model | `SpectrometerSensor.py` (`isVirtual` + VID/PID), `Spectrometer.py` | **No USB index, no resolution, no exposure columns.** |
| Calibration ROI capture | `.../device/calibration/SpectrometerCalibrationProfileHoughLinesViewModule.py` ~L92 | Builds a `VideoThread` subclass, `setIsVirtual(sensor.isVirtual)`, `start()`. Already routes real vs virtual off `isVirtual`. |
| Wavelength-cal capture | `.../calibration/SpectrometerCalibrationProfileWavelengthCalibrationViewModule.py` ~L146 | Same shape. |
| **Measurement "Measure"** | `.../logic/spectral/workflow/SpectralWorkflowEngine.py` `captureAcquisitionStep()` L94 → `__capture()` L157 | **Virtual-only, bypasses VideoThread.** Reads `virtualSettings.getImage(role)` directly N times (a comment notes VideoThread would deadlock without a Qt event loop). **No real-capture path here at all.** |
| Image → Spectrum | `.../logic/spectral/acquisition/ImageSpectrumAcquisitionLogicModule.py` `execute()` L19 | Consumes a **`QImage`**, samples the ROI centre row → `Spectrum`. Identical for real/virtual. |
| Preview sink | `.../view/application/widgets/video/VideoViewModule.py` `handleVideoThreadSignal()` | `QPixmap.fromImage(image)` into a `QGraphicsPixmapItem`. |

**Invariant to preserve:** everything downstream of capture consumes a **`QImage`**. Any real backend
must yield a `QImage` (RGB888) — the format the whole pipeline is normalized to.

---

## 2. The core problem — selecting the *right* physical camera

Today `videoDeviceId = 0` "happens to work" only because the spectrometer is the sole/first camera. That
breaks the moment there is a laptop webcam, a second UVC device, or the OS enumerates the metadata node
first. The domain already identifies devices by **USB VID/PID** (`isSensorConnected`), so the design's job
is to turn *"sensor X is connected"* into *"...and it is cv2 capture index N."*

### 2.1 Resolver — `SensorCaptureIndexResolver` (new)

Proposed new util (desktop): `spectracsPy/.../logic/appliction/video/capture/SensorCaptureIndexResolver.py`

```
resolveCaptureIndex(sensor: SpectrometerSensor) -> int | None
```

**Linux (primary, verified above):**
1. Glob `/sys/class/video4linux/video*`.
2. For each, read `device/../idVendor`, `device/../idProduct`; keep nodes matching the sensor's
   `vendorId`/`modelId` (hex, case-insensitive).
3. Among matches, prefer the one whose `index` file == `0` (the **capture** node); the metadata node
   is `index >= 1`. The cv2 index is the integer `N` in `videoN`.
4. Fallback within a match set: pick the first node whose `cv2.VideoCapture(N).read()` returns a frame
   (probe-and-release). This also filters out non-capturable nodes on kernels without a clean `index`.

**Windows:** DirectShow gives no stable VID/PID→index map. Strategy: enumerate `0..N`, open each,
compare frame/name heuristically; if ambiguous, fall back to the **configured index** (§4) or `0` and
surface the choice in the UI (§3.4). *Documented as best-effort; Linux is the reference platform.*

**Android:** out of scope — resolver returns `None`, capture stays deferred (`CaptureBackend` Android
branch already raises).

The resolver returns `None` when no matching capturable node is found; callers then show the existing
"device not connected / no image" notification instead of blindly opening index 0.

> Note: this is Linux-sysfs, not pyusb — pyusb (`isSensorConnected`) answers *presence*; sysfs answers
> *which video node*. They stay complementary: presence gates the button, resolver gates the open.

---

## 3. Design

### 3.1 Route all capture through `CaptureBackend` (finish the P7 wiring)

Extract VideoThread's inline cv2 block (L60–L75) so `run()` does:

```
if not self.getIsVirtual():
    self._backend = getCaptureBackend()
    deviceId = self._resolvedDeviceId          # from resolver, set by the caller (§3.3)
    self._backend.open(deviceId)
...
# __capturePhysicalFrame:
qimg = self._backend.read()
if qimg is not None:
    self.qImage = qimg
    ...optional save...
```

`DesktopCv2CaptureBackend` becomes the single owner of cv2 flags. **Move the exposure/FOURCC/resolution
config into the backend** (it currently lives in VideoThread) and make **resolution + exposure params of
`open()`** rather than constants (§3.2). One capture code path, platform-selected, testable in isolation.

### 3.2 Capture parameters (resolution / exposure / fourcc)

Today these are magic constants (1920×1080, MJPG, exp 150/−3). Promote to a small value object,
`CaptureSettings(width, height, fourcc, exposure, autoExposure)`, passed into `backend.open(...)`.
Defaults = today's constants (no behavior change until configured). Source of the values → §4.

### 3.3 Who resolves the index — the view modules

The three capture entry points already read `sensor.isVirtual`. Extend each: when **not** virtual,
call `resolveCaptureIndex(sensor)`; if `None`, show the existing not-connected notification and abort;
else pass the index to the thread (`thread.setDeviceId(idx)`), then `start()`. No new UI required for the
happy path — the correct camera is chosen automatically.

Touch points:
- `SpectrometerCalibrationProfileHoughLinesViewModule` (~L92)
- `SpectrometerCalibrationProfileWavelengthCalibrationViewModule` (~L146)
- and the workflow engine — §3.5.

### 3.4 Optional manual override (UI)

For the Windows-ambiguity and multi-camera cases, add a small **"Camera"** selector to the
spectrometer/device settings view: a combo listing detected capturable nodes (label = sysfs `name` +
resolved VID/PID), default = auto-resolved. Stored per-sensor (§4). This is a *fallback affordance*, not
the primary flow — auto-resolution should cover the single-spectrometer case.

### 3.5 Real capture in the workflow "Measure" step (the real gap)

`SpectralWorkflowEngine.__capture()` (L157) is virtual-only and deliberately avoids VideoThread (no Qt
event loop in that call path). For real capture it needs its **own** short-lived, event-loop-free grab —
which is exactly what `CaptureBackend` gives us (no QThread needed):

```
def __capture(self, role, frames):
    if sensor.isVirtual:
        image = virtualSettings.getImage(role)            # existing path
        return [acquire(image) for _ in range(frames)]
    backend = getCaptureBackend()
    backend.open(resolveCaptureIndex(sensor))
    try:
        out = []
        for _ in range(frames):
            img = backend.read()                          # QImage
            if img is not None:
                out.append(acquire(img))
        return out
    finally:
        backend.release()
```

This keeps the "N frames averaged" semantics and reuses `ImageSpectrumAcquisitionLogicModule`
unchanged (it only wants a QImage). **Warm-up:** discard the first few reads (auto-exposure settle) —
observed on this camera the first frame(s) after open are dark; grab ~5 throwaway frames before counting.

---

## 4. Capture parameters — per USB-vendor/chipset, via `SpectrometerSensorSettings`

**Decided (Edwin, 2026-07-05):** capture parameters are **not** user-tuned per DB row; they are
**hardcoded per USB-camera vendor/chipset**, because the spectrometer is a **DIY device with a small,
known set of cameras**. Two production cameras matter:

| Chipset / vendor | VID:PID | Role | Notes |
|---|---|---|---|
| **Microdia / Sonix** (`AUTOMAT`) | `0c45:6366` | **Production batch** | Cheap Chinese cams, quality fine — the intended volume camera. |
| **ELP** (`EXAKTA`) | `32e4:8830` | Premium / dev | More expensive; the unit currently on the bench. Native capture observed **1600×1200** (it snaps 1920×1080→nearest). |

So the resolution/exposure/fourcc live in a **per-chipset lookup keyed by VID:PID**, with a safe global
default. The natural home is the **already-existing but orphan** `SpectrometerSensorSettings` (today just
`exposureTime:int=150`, referenced nowhere) — wire it up (at least **transiently**, in memory) to hold:

- `captureWidth`, `captureHeight` — resolved **per chipset** (Microdia vs ELP differ), not a global constant.
- `exposure`, `autoExposure` — per chipset **and** per light source (§9.3).
- `fourcc` — default **not** hard-forced MJPG (see §0 wedge finding); prefer YUYV / tolerate empty reads.

No DB schema change required for milestone 1 — `SpectrometerSensorSettings` can start as an in-memory,
VID:PID-keyed table and be promoted to DB later if persistence is wanted. **Best-resolution resolution
(picking the right mode per chipset for our purpose) is its own concern — see §9.2.**

### 4.1 Camera identity / virtual serial (orthogonal — surfaced 2026-07-05)

A separate but important issue: **the cameras do not expose a USB serial number** (the Chinese Microdia
cams don't; the ELP likely doesn't either). That breaks any attempt to bind *a specific physical camera
item* to *its calibration profile* by serial. The intended solution (Edwin's original design) is to
**assign a virtual serial number** to each camera item, stored in the app, so a calibration is tied to
the right physical unit. This is **not** the same as capture parameters — it is device *identity*. See
§9.1 for the design thread; it must be resolved together with the connection/calibration UX (§9.4).

---

## 5. Milestones (implement on explicit request, in order)

- **R0 — Resolver, verified standalone.** Build `SensorCaptureIndexResolver`; unit-drive it on this
  machine: `resolveCaptureIndex(elp4KDevice)` → `0`, and it must **reject** the metadata node. No UI.
  *Gate: prints the correct index for the plugged-in ELP; returns `None` when unplugged.*
- **R1 — Backend owns cv2; VideoThread routes through it.** Extract inline cv2 → `DesktopCv2CaptureBackend`
  with `CaptureSettings`; VideoThread calls `getCaptureBackend()` + `setDeviceId`. Behavior identical to
  today when index resolves to 0. *Gate: live preview in the calibration view still renders off the real
  camera.*
- **R2 — Real device selection in calibration + wavelength-cal views.** Wire the resolver into both
  view modules; unplug → not-connected notice; replug → live frames. *Gate: Hough ROI + wavelength
  calibration both run off the real ELP with no hardcoded 0.*
- **R3 — Real capture in the workflow Measure step.** Add the non-virtual branch to
  `SpectralWorkflowEngine.__capture` with warm-up. *Gate: run a full measurement workflow end-to-end on
  the real camera; a `Spectrum` comes out and the pumpkin/plugin evaluation renders.*
- **R4 — (optional) Manual camera override UI** (§3.4) + per-device capture settings (§4).
- **R5 — (optional) Resolution/exposure tuning** for the real spectrometer (spectra are read from the
  ROI centre row, so vertical resolution and exposure directly affect SNR — worth a tuning pass once R3
  produces real spectra).

Android real capture remains **out of this spec** (deferred, `SPEC_android_port.md` §6).

---

## 6. Verification (click-through, per Edwin's drive-and-observe review)

For each of R2/R3, with the ELP plugged in:
1. Launch the app (real, non-virtual sensor selected).
2. Calibration view → **live camera image** visible (not the virtual PNG).
3. Unplug camera → capture shows the not-connected notification (not a black frame / crash).
4. Replug → capture works again.
5. Run the measurement workflow → a real `Spectrum` is produced and the evaluation step renders.
6. Confirm a second camera (e.g. a laptop webcam) present does **not** hijack capture — the ELP is still
   the one selected (resolver picks by VID/PID, not index 0).

---

## 7. Decisions & open threads (updated 2026-07-05)

**Decided:**
1. **Capture parameters are per USB-vendor/chipset, hardcoded** (DIY, known camera set) — not per-DB-row
   user tuning. Home = `SpectrometerSensorSettings`, transient/in-memory to start (§4). No schema change
   for milestone 1.
2. **Windows is the primary *customer* target** — Linux is dev-first (auto-resolve works today), but the
   port must **not forget Windows**: it needs the manual camera-picker fallback (§3.4) since USB→index
   auto-resolution isn't clean on DirectShow. Windows integration is a first-class future milestone, not
   an afterthought.
3. **Frame count is set by the plugin.** Global default **50**; the plugin overrides — `PumpkinOilPlugin`
   should set **20** (Edwin: 20 gives a confident mean in practice). So the measurement/"Measure" path
   reads the count from the plugin's `MeasurementStep` (default 50, pumpkin 20). Calibration bursts keep
   their own count (currently 50). *(Today: live path hardcodes 50, workflow hardcodes 5 — both get
   reconciled to "plugin-driven, default 50".)*
4. **Exposure is currently MANUAL and fixed** — clarifying §4/§0: the app sets `AUTO_EXPOSURE=1` which on
   V4L2 means *manual* mode, then forces a fixed value (`150` Linux / `-3` Windows). So there is **no
   auto-exposure** today; it is a fixed manual number that differs by OS. **For R0–R3, keep the current
   fixed per-chipset manual value** — the **best-fit exposure algorithm (§9.3) is postponed** to a separate
   design/test pass (Edwin: "we can postpone the algorithm").
5. **Measurement UX = live-during-burst, then graph.** During the 20/50-frame capture the live camera
   image/capture is shown; afterwards the captured spectrum is shown as a graph (the legacy `SpectralJob`
   pattern). The new Wizard must adopt this (§9.4).
6. **Identity keys on SERIAL, not username.** The master user authors, per serial, the
   { device, calibration, plugin } bundle; the end user registers by entering the label serial. This
   **reverses Roadmap #3's** "select an `AppUser`" direction and supersedes the "username = future serial"
   idea. Full object model → its own `SPEC_connection_and_calibration_ux` (§9.4).

**Open threads (need detailed design before implementing — see §9):**
- **9.1 Camera identity / virtual serial** — cams have no serial; bind camera-item ↔ calibration via an
  assigned virtual serial.
- **9.2 Best-resolution resolution** — pick the right capture mode per chipset "for our purpose".
- **9.3 Best-fit exposure algorithm** — one algorithm, two light sources (CFL calibration lamp vs 7×3W
  LED measurement array).
- **9.4 Connection + calibration UX** — a "sound setup" the end user understands: camera attached via USB
  ⇄ user profile ⇄ calibration profile. The current "Connect spectrometer" button only picks a stored
  profile; it does no hardware handshake. This needs its own detailed, end-user-sensible design.

**Multiple-camera edge case:** must be handled (Edwin) — when more than one camera is present (or more
than one matches a chipset), disambiguate. Feeds the resolver (§2.1) and the manual picker (§3.4).

---

## 8. Cross-references

- `docs/SPEC_android_port.md` §6 — deferred Android UVC-over-OTG / RPi-network capture.
- `CaptureBackend.py` — the scaffold this spec finishes wiring (its own docstring calls this "the P7
  wiring step").
- `spectracs-domain-model` / `spectracs-pipeline-overview` memories — device model + capture→spectrum flow.

---

## 9. Design threads surfaced 2026-07-05 (captured, not yet designed)

These came out of Edwin's review of the as-is code. They are **recorded, not resolved** — each needs its
own design pass (some may become separate specs). Do not implement against these yet.

### 9.1 Camera identity via serial number — **already exists in the model**
- **Problem:** the USB cameras expose **no USB serial** (Microdia Chinese cams don't; ELP likely doesn't),
  so a physical unit can't be identified from the USB layer — yet a **wavelength calibration is specific to
  one physical spectrometer unit** and must stay bound to it.
- **As-is (verified in code):** the identity mechanism **already exists** and matches Edwin's design — it is
  **not** a new thing to invent:
  - `SpectrometerProfile.serial` (`spectracsPy-model/.../device/SpectrometerProfile.py:13`) is a DB column;
    the entity already chains **serial → `Spectrometer` (→ sensor/chipset) → `SpectrometerCalibrationProfile`**
    (lines 15-21).
  - `RegisterSpectrometerProfileViewModule` (`.../view/spectrometerConnection/`, line 32) prompts:
    *"Your spectrometer has been calibrated in the factory. Please supply the serial number of the device
    for downloading the calibration profile."* — i.e. the **printed-label serial on the physical hand-held
    unit is the key** that fetches the matching factory calibration. Lookup is by serial
    (`RegisterSpectrometerProfileViewModule.py:75-76`).
- **So the "virtual serial" = `SpectrometerProfile.serial`**, a per-unit key printed on the device label —
  independent of the (missing) USB serial.
- **Open:** connect this profile-identity to the **live USB device** — the USB resolver (§2.1) picks the
  camera by VID:PID (chipset), but VID:PID is shared by all units of a model; the printed serial is what
  distinguishes *this* unit and its calibration. The flow that ties *entered serial ⇄ resolved USB camera ⇄
  active calibration* is the connection/calibration UX (§9.4).

### 9.2 Best-resolution resolution ("best mode for our purpose")
- **Problem:** each chipset advertises many modes (the ELP: 320×240 … 3264×2448); the app currently
  forces one global `1920×1080` and the ELP silently snaps to `1600×1200`. We need to **choose the right
  capture mode per chipset** for spectroscopy (the spectrum is read from a horizontal ROI row, so the
  wavelength axis wants enough horizontal pixels; vertical is ROI-limited).
- **Intended approach (Edwin):** hardcode the chosen mode **per USB vendor/chipset** (§4) as the seed —
  BUT **empirically verify it first against the CFL bulb** before fixing the value. Rationale: the device
  is a **hand-held spectrometer whose grating is attached to the camera's lens**, so "best resolution" is a
  property of the *whole optical stack* (grating + lens + sensor), not just the sensor's max mode — a
  visual/quantitative check (does the CFL's mercury lines resolve sharpest?) decides it. Hardware
  construction is documented in `KB_spectroscopy_physics.md` §7.
- **Open:** the actual chosen resolution for Microdia vs ELP (to be determined by the CFL inspection), and
  the selection rule (fixed per-chipset table, seeded from that inspection).

### 9.3 Best-fit exposure algorithm (two light sources)
- **Problem:** exposure is a fixed manual number today (§7.4). Edwin's goal is **one algorithm that finds
  the best exposure**, but there are **two distinct illumination regimes**:
  1. **CFL bulb** — the **calibration** source (mercury emission lines; the spectrum we already captured).
  2. **Array of 7 × 3 W LEDs** — the **measurement** source (the actual sample illumination).
  Each needs a different well-exposed operating point (avoid clipping the bright Hg green line; maximise
  SNR on the LED spectrum without saturation).
- **Intended approach (to design):** an auto-exposure search — e.g. ramp exposure/gain until the peak
  channel approaches but does not clip (~95% of full-scale), per light source. Relates to the warm-up in
  §3.5 and the per-chipset exposure defaults in §4.
- **Open:** the algorithm itself, whether it runs per-measurement or is calibrated once per source, and
  how the "which light source is active" context is known.

### 9.4 Connection + calibration UX ("a sound setup the end user understands")
> **This thread now has its own spec:** `docs/SPEC_connection_and_calibration_ux.md` (the full serial-keyed
> object model, master-authoring + end-user self-registration flows, connection status, measurement UX).
> The material below is the design record that seeded it; the CX spec is authoritative going forward.
- **Problem / as-is:** the "Connect spectrometer" button (`SettingsViewModule.py:69`) only opens a combo
  that **picks a stored profile** — it does **no hardware handshake** and never calls `isSensorConnected`.
  The only connection feedback anywhere is a text suffix `" (not connected)"` on a *different* screen
  (`SpectrometerProfileViewModule.py:83`); `getSpectrometersHavingSensorConnected()` is dead code. No
  icon/badge/toast. The new measurement Wizard has **no live preview**; only calibration bursts and the
  legacy `SpectralJob` widget show frames (and only *during* a capture burst — there is no idle
  viewfinder; see the legacy-flow note below).
- **Target (Edwin):** a coherent setup the end user follows — **camera attached via USB ⇄ user profile ⇄
  calibration profile** — where the app *resolves the real camera* (new resolver + `isSensorConnected`),
  *shows clearly that a valid camera is connected*, and *offers live view during measuring* on the
  measurement view. This is the "connection and calibration issue" to specify in detail.
- **Prerequisites & object model — key on SERIAL, not username (Edwin, 2026-07-05):** this is an
  **integration** issue with an object model that must be specified (likely its own
  `SPEC_connection_and_calibration_ux`). Decisions so far:
  - **The serial is the pivot key** — `SpectrometerProfile.serial`, printed on the unit's label — **not**
    the username. (Reverses the earlier "username = future serial" idea and Roadmap #3's "replace serial
    with an `AppUser` selection".)
  - **Why serial (rubber-duck insight):** the serial is a **stable, human-assigned natural key** identical
    on the master side and the end-user side, so it **structurally resolves decision D15** of
    `SPEC_pumpkin_integration.md` — D15 bound the device by a soft code-name string precisely because
    profile `uuid4` ids are random per-client and would *dangle*; a serial does not dangle.
  - **Master user authors, per serial:** serial → { `Spectrometer` (model→sensor/chipset), a
    `SpectrometerCalibrationProfile` produced by calibrating against the CFL, the **plugin** (codeRef) }.
    Plugin thus becomes a property of the **instrument (serial)**, not the person. **This authoring UI does
    not exist today** — only the seed sets `AppUser.pluginId`/`spectrometerDevice`, and no
    `SpectrometerProfile` is ever created via UI.
  - **End user registers by serial:** types the label serial → app resolves the whole bundle (device +
    calibration + plugin) → session. `RegisterSpectrometerProfileViewModule` already prompts for the serial
    "for downloading the calibration profile" but is **not** wired to plugin/session (it only appends to the
    **global** `ApplicationConfig`).
  - **Current split-brain to fix:** plugin/device are bound **per-user** (`AppUser.pluginId` +
    `spectrometerDevice` string, server DB); the profile/calibration mapping is **global**
    (`ApplicationConfig.isDefault`, app DB) — two unconnected sides in two databases. Re-keying on serial
    lets both meet on `SpectrometerProfile.serial`.
  - **Cleanest end-state:** strip `pluginId`/`spectrometerDevice` off `AppUser` (back to pure auth+role);
    everything flows from the registered serial; registration records a **user ⇄ serial** link.
- **Distribution — DECIDED (Edwin, 2026-07-05): server-authoritative.** The serial-object
  (`SpectrometerProfile`) **moves to the server DB**; the master authors it there, and the end-user client
  **resolves it by serial at registration** (download-by-serial — the product shape, not local-first). This
  makes the **plugin a real FK** (`DbPlugin` is already server-DB) instead of a soft string, and it makes
  the **serial the natural cross-boundary key**. Reuses the existing Pyro/login substrate (login already
  returns `pluginCodeRef`/`spectrometerDevice`; a resolve-by-serial RPC returns the whole bundle).

#### Refined role model (Edwin, 2026-07-05) — master authors the serial-object; end user self-registers

The master does **not** set up end-user `AppUser`s. The master administers **the serial-keyed setup
object**; the end user **registers himself** and enters the serial.

- **The serial-keyed object = `SpectrometerProfile` (moving to the SERVER DB), and its master editor already
  largely exists.** `SpectrometerProfileViewModule` ("Settings > Spectrometer profiles > Spectrometer
  profile") already edits **serial + `Spectrometer` (device) + an embedded
  `SpectrometerCalibrationProfileViewModule`** (serial `QLineEdit` L174; calibration sub-editor L181-184;
  device combo L177). **The only missing field is the plugin reference** — today the plugin hangs off
  `AppUser.pluginId`; it moves onto the **server-side** `SpectrometerProfile` as a **real FK to `DbPlugin`**,
  so serial → { device, calibration, **plugin** }. **Knock-on (new open item, §9.4-a):** since
  `SpectrometerProfile` moves server-side but `SpectrometerCalibrationProfile`/`Spectrometer` are app-DB
  today, the calibration (and how the client caches it for offline measurement) must be reconciled.
- **Master admin — setup surface added, user-admin KEPT (Edwin):** setup is about *instruments*, not
  *people*, so the master gains **`SpectrometerProfile` CRUD** (serial + device + calibration + plugin) as
  the setup surface. The existing master **User admin** (`UserListViewModule`/`UserViewModule`) is **kept** —
  for master-only data the master alone may edit/inspect — it simply stops being the *setup* path: the master
  does **not** create end-user accounts; end users self-register.
- **End-user self-registration — NEW view module.** A registration screen where the end user **creates his
  own account and enters the serial key** (from the unit's label) → the app resolves the serial-object's
  bundle → binds it (session, and/or a persisted `user ⇄ serial`). This is distinct from today's
  `RegisterSpectrometerProfileViewModule` (which only appends a profile to the **global** `ApplicationConfig`
  and does no account creation / plugin resolution). Registration should require the serial to **already
  exist** (master authored it) — which naturally enforces the milestone order (master setup → then end-user
  registration).
- **`AppUser` slims down:** drop `pluginId`/`spectrometerDevice`; identity+role only. Plugin/device/
  calibration all resolve **through the registered serial**.

**Refinement decisions — LOCKED (Edwin, 2026-07-05):**
1. **Plugin ref / placement:** `SpectrometerProfile` **lives on the server DB** → plugin is a **real FK to
   `DbPlugin`** (not a soft string). End users resolve the serial-object **from the server** (download-by-
   serial). *(Answers old Q1 + Q5 — server-authoritative, see the Distribution decision above.)*
2. **Master keeps User admin:** `UserViewModule`/`UserListViewModule` are **retained** for master-only
   data/inspection, but are **not** the setup path; the master does not create end-user accounts.
3. **Self-registration gating:** the **serial must already exist** (master-authored); a **valid serial is
   sufficient** — no separate approval step for the milestone. **Registration form captures (Edwin):**
   **password**, **first + last name**, and the **serial** (the end user creates his own account). *(Today
   `AppUser` has `username`/`passwordHash`/`displayName`; first+last name likely split `displayName` or add
   `firstName`/`lastName`.)*
4. **Cardinality:** **one `AppUser` ⇄ one serial** (one user, one spectrometer) for now; many-per-user later.
5. **Resolve location:** **server** (per decision 1).

**Follow-on decisions from "`SpectrometerProfile` on the server DB" (§9.4-a) — LOCKED (Edwin, 2026-07-05):**
- **a1 LOCKED:** move the whole coherent graph — device catalog (`Spectrometer`/`Sensor`/`Chip`) **+**
  `SpectrometerProfile` **+** `SpectrometerCalibrationProfile` — to the **server DB together** (FKs stay
  intra-DB; client fetches by serial). App DB keeps only local/cache.
- **a2 LOCKED:** **resolve the bundle into the session** at login/registration (like `pluginCodeRef`); a
  persistent local cache is optional/deferred — the product is online-required anyway (LIMS + licence check).
- **Rationale detail below (model-vs-item trace):**
- **a1-detail. Model vs item — where `Spectrometer.id` is used (traced):** `Spectrometer.id` is referenced by
  **exactly one thing — `SpectrometerProfile.spectrometerId`**; no measurement/spectrum record uses it, and
  a **server RPC `getSpectrometers()` already exists** (`SpectracsPyServerClient.py:126`). So the model is
  already layered the way Edwin describes:
  - **`Spectrometer` = the MODEL** (modelName + sensor + vendor + style) — shared catalog, seeded as 3
    (Phantom/InVision/InLight).
  - **`SpectrometerProfile` = the ITEM** (unique **serial** → one `Spectrometer` model + its own
    calibration). "Different items of the same model but different profile" is **already** modeled here.
  - **Leaning (to confirm):** move the whole coherent graph — device catalog (`Spectrometer`/`Sensor`/
    `Chip`) **+** `SpectrometerProfile` **+** `SpectrometerCalibrationProfile` — to the server DB together,
    so all FKs stay intra-DB and the client fetches by serial. The existing `getSpectrometers()` RPC shows
    this direction was already anticipated. App DB keeps only local things (virtual settings, prefs, and any
    cached bundle).
- **a2. Caching vs online-required (new constraint, Edwin):** the product is **online-required anyway** —
  there will be **LIMS integration** (lab information management system) and a **monthly rental-fee / license
  check**. So local caching is a *convenience*, not an offline-capability requirement: the bundle can simply
  be resolved at login/registration and held in session (like `pluginCodeRef` today), with a persistent
  local copy optional. **To discuss.** *(These commercial/integration constraints are logged as roadmap
  threads — see ROADMAP "Still-deferred design threads".)*
- **Measurement UX — decided (Edwin):** follow the legacy pattern — **while the burst (20/50 frames) is
  captured, show the live camera image/capture; afterwards show the captured spectrum as a graph.** The new
  Wizard `WizardViewModule` currently has neither (Measure button + static plot only) → it should adopt
  live-during-burst-then-graph. This is now a decision, not an open question (see §7).
- **Legacy-flow reference (verified in code):** in `SpectralJobViewModule`, the wired **"Measure"** button
  is the *reference/Light* one → `onClickedMeasureLightButton` → `referenceWidget.startVideoThread()`
  (`SpectralJobViewModule.py:101,106`), which runs a 50-frame `SpectrumVideoThread`. Frames stream **into**
  the "Spectrum image (last captured)" preview tab **during** the burst (`SpectralJobWidgetViewModule.py:
  56-92`), after skipping the first 3 warm-up frames. So the legacy view showed a **live view *during*
  capture, not an idle viewfinder before pressing Measure** — and the *sample*/"Oil" Measure button
  (`SpectralJobViewModule.py:52`) is **not wired** to anything. This is the closest existing precedent for
  the target measurement UX.
- **Open:** the full screen-by-screen flow; where identity (§9.1), resolution (§9.2), exposure (§9.3) and
  connection status surface to the user. Likely its own spec (`SPEC_connection_and_calibration_ux`).
```
