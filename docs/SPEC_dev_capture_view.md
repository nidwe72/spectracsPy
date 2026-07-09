# Spec — "Capture images" development view (real-camera sub-milestone 1)

Status: **IMPLEMENTED (P0–P3 + exposure controls + nav) + click-through verified 2026-07-06/07** — driven
live in the running GUI (Settings → Development → Capture images) against the ELP: resolver→cv2 index 0,
backend captured the real CFL mercury-line spectrum (1600×1200 RGB888), dev view streams + saves PNG,
auto-selects the connected sensor, Start/Save read-only when not connected. **Added:** a live **exposure
slider** + an **"auto-exposure" checkbox** (default on, one-shot on stream start, status-bar progress,
locks the slider) driving our own bisection (§6, parent §9.3); a **Back** button; the full **breadcrumb**
`Settings > Development > Capture images`. The **green-doublet** clipping was traced to over-exposure and
fixed via per-camera exposure (ELP CFL=78) — calibration detect-peaks now resolves it; the residual is the
optical/slit limit (§9.2), accepted. Optional P4 (live resolution combo) not built. Windows auto-resolve
deferred (own milestone). Scope is **desktop Linux/Windows**. This is the **first** real-camera
sub-milestone; it deliberately precedes real
calibration because it is the *simplest possible consumer* of a live physical camera, so the shared
capture foundation (resolver + backend) can be built and proven here before any calibration wiring.

Parent: `SPEC_real_camera_capture.md` (this doc realises its milestones **R0 + R1** inside a new dev view;
calibration integration is sub-milestone 2 — see that spec §5).

---

## 1. Goal

A **"Capture images"** screen under **Settings → Development** that:

1. shows a **live stream** from the real spectrometer USB camera, and
2. lets the user **save the current frame as PNG** (user chooses the filename freely).

Three purposes, all real:
- **Dev / debug viewfinder** — see what the physical camera actually sees, live, without running a
  calibration or measurement flow.
- **Build virtual-spectrometer filesets from real captures** — save real ELP/Microdia frames to disk so
  they can populate a virtual fileset (the virtual device replays a folder of PNGs — see §4).
- **Human best-resolution check (§9.2 of the parent spec)** — the human judges, against the CFL line
  source, which capture resolution makes *this optical stack* resolve the spectrum sharpest; the finding
  is recorded in the KB and hardcoded per chipset. This view is that judging tool (§5).

---

## 2. What it reuses (nothing new in the pipeline)

| Piece | File | Role here |
|---|---|---|
| Preview sink | `.../view/application/widgets/video/VideoViewModule.py` | Renders the live `QImage` stream (`QPixmap.fromImage` → `QGraphicsPixmapItem`) — unchanged. |
| Capture thread | `.../logic/appliction/video/VideoThread.py` | A **continuous** run: `frameCount == 0` means `afterCapture()` never sets the stop flag, so it streams until `stop()`. Real (non-virtual) path only. |
| Backend | `.../video/capture/CaptureBackend.py` `DesktopCv2CaptureBackend` | **R1**: owns the cv2 flags; VideoThread routes through it (see parent §3.1). |
| Resolver | `SensorCaptureIndexResolver` (**new**, parent §2.1) | **R0**: sensor VID/PID → cv2 index; rejects the UVC metadata node. |
| Device catalog | `SpectrometerSensorUtil.getSpectrometerSensors()` | Source of the real sensors to pick from (ELP `32e4:8830`, Microdia `0c45:6366`). |
| Nav / Development gate | `SettingsViewModule.createDevelopmentGroupBox()` (L110), `updateAdministrationVisibility()` (L141) | New button + `NavigationSignal` target, master-only (inherits Development gating). |

**No changes to `ImageSpectrumAcquisitionLogicModule` or any downstream pipeline** — this view only
displays and saves a `QImage`. It touches nothing the measurement/calibration flows depend on.

---

## 3. Design

### 3.1 New view module — `DevCaptureViewModule` (PageWidget)

Navigated to from a new **"Capture images"** button in the Development group box
(`SettingsViewModule.py` L110–122), target `"DevCaptureViewModule"`, master-only.

Layout (follows the existing `PageWidget` / calibration-view shape):
- **Live view** — a `VideoViewModule` filling the main area.
- **Controls panel:**
  - **Sensor** combo — the real (non-virtual) sensors from the catalog (ELP, Microdia). Default = the
    active spectrometer profile's sensor if it is real, else the first real sensor.
  - **Connection status** label — result of the resolver: e.g. *"ELP `32e4:8830` → /dev/video0 (index 0)"*
    or *"not connected"*.
  - **Start stream** / **Stop stream** buttons.
  - **Save frame…** button — opens `QFileDialog.getSaveFileName` (PNG); saves the currently displayed
    `QImage`. The **user types the filename** — no role/name presets (§4).

### 3.2 Auto-resolve from the start (Edwin) — and it is the SM2 primitive

The view **auto-resolves** the cv2 index for the selected sensor via `SensorCaptureIndexResolver`
(parent §2.1), not a manual node dropdown. This is deliberate: it is exactly the *"is the attached
camera the one this spectrometer expects?"* check that **sub-milestone 2** needs when it verifies the
connected camera fits the selected `SpectrometerSetup`. Building it here means SM2 inherits a proven
sensor⇄camera matching primitive rather than inventing one.

Behaviour:
- On sensor-select (and on view open): call `resolveCaptureIndex(sensor)`.
  - **index found** → status shows the node; **Start stream** and **Save frame…** enabled.
  - **`None`** (unplugged / wrong camera / only the metadata node) → status shows *"not connected"*;
    **Start stream** and **Save frame…** rendered **read-only/disabled** (not a transient toast).
- Multi-camera correctness: because selection is by VID/PID, a laptop webcam present alongside the ELP
  does **not** hijack capture — the resolver picks the spectrometer node.

> Note (still to design in SM2): the resolver keys on **VID/PID = chipset**, shared by all units of a
> model; distinguishing *this physical unit* from *another of the same model* is the printed-serial
> concern (parent §9.1) and belongs to the connection/calibration UX, not this dev view.

### 3.3 Streaming lifecycle

- **Start** → build a real `VideoThread`, `setIsVirtual(False)`, `setDeviceId(resolvedIndex)`,
  `setFrameCount(0)` (continuous), connect its frame signal to the `VideoViewModule`, `start()`.
- **Stop** / view-close → `stop()` + join; release the backend. Must be robust to unplug mid-stream:
  a failed `read()` returns `None` (never raises — parent §0 MJPG finding), the view keeps the last
  frame and flips status to *"not connected"* + buttons read-only.

### 3.4 Capture format (MJPG / YUYV) — decided empirically at implementation

Per Edwin: three years ago a fixed set of cv2 flags "worked for me," possibly because **decoding YUYV to
a displayable image was the actual problem** back then. Resolution for this spec:
- Do **not** hard-force MJPG (parent §0: forcing MJPG wedged the ELP UVC stream on newer OpenCV).
- cv2's `read()` returns **BGR uint8 regardless of USB transport format**, so YUYV-vs-MJPG is a
  *negotiation/robustness* matter, not an app-side decode problem — the `cvtColor(BGR→RGB)` step is
  identical either way.
- **The exact flags are chosen at implementation time on the bench** (try default / YUYV / MJPG, keep
  whatever streams the ELP reliably), owned by `DesktopCv2CaptureBackend`. This dev view is a good place
  to shake that out.

---

## 4. Virtual-fileset tie-in (why "save PNG" matters beyond debugging)

The virtual spectrometer loads a folder by a **fixed filename convention**
(`VirtualSpectrometerViewModule.py:79`): `calibration.png` / `reference.png` / `sample.png`
(`SPEC_pumpkin_integration.md` A.4). So a real capture saved with the right name **is** a virtual-fileset
member — capture a real CFL frame here, save it as `calibration.png` into a folder, point the virtual
device at that folder, and it replays real data.

**Decision (Edwin): the view does NOT preset role filenames.** The user types whatever filename fits
their intent in the save dialog. The convention is documented (here + the virtual-device view) so the
user can *choose* to follow it; the dev view does not impose it. Keeps the tool general (it is also used
to grab arbitrary debug frames), and avoids baking the pumpkin-era role names into a generic capture UI.

---

## 5. Doubles as the §9.2 best-resolution tool (records to KB + hardcoded table)

The parent spec §9.2 / `KB_spectroscopy_physics.md` §7 hold an open loop: **a human must judge the best
capture resolution per camera against the CFL line source, record it in the knowledge base, and that
finding becomes a hardcoded per-chipset value in the app.** This view is the instrument for the *judging*
half of that loop.

- **Optional control (nice-to-have, not required for the SM1 gate):** a **resolution** combo listing the
  modes the selected chipset advertises, so the human can switch modes live and see which renders the
  CFL mercury lines sharpest.
- **Output of the human check** is not code from this view — it is a **KB entry** (per-camera verified
  best resolution) that a later change folds into the per-chipset hardcoded lookup (parent §4,
  `SpectrometerSensorSettings`). SM1 does **not** wire the chosen resolution into capture params; it only
  enables the human to *determine* it. (Capture params stay hardcoded for now — see §6.)

---

## 6. Explicitly deferred (recorded, not designed here)

- **Configurable capture params** (frame count, resolution, fourcc): stay **hardcoded** for now. Later
  configurable by some mechanism — **likely plugin-driven** — to be discussed (parent §4, §7.3). SM1 builds
  no settings UI for them beyond the optional live resolution combo.
- **Exposure — per-camera default + live manual slider (IMPLEMENTED 2026-07-07).** The view seeds the
  slider from the camera's **CFL-calibration exposure** (`getSensorSettings().calibrationExposure`, ELP=78)
  and applies it via `VideoThread.setExposure`; the **live slider** (`setLiveExposure` →
  `CaptureBackend.setExposure` on the open cap) lets a human dial the sweet spot mid-stream — verified the
  green clips/unclips live. This is the tool to *find* the still-TBD **LED-array measurement** exposure.
  Now also an **"auto-exposure" checkbox (default ON)** (IMPLEMENTED 2026-07-07): runs our own **bisection**
  (`AutoExposureLogicModule`) over the **live stream** — applies a candidate via the slider, lets the UVC
  stream settle, measures the delivered frame's 99.9-percentile brightness, targets ~92 % full-scale. Runs
  **one-shot** when enabled / on stream start; **progress shows in the app status bar** (under the logo,
  `ApplicationStatusSignal` "finding best exposure [i/N]"); the **manual slider is locked while it is on**.
  Verified on the ELP: clipped stream (slider 250) → auto-exposed to 61, green unclipped; toggling off
  unlocks the slider. Proving ground before the algorithm enters the calibration/measurement flows (§9.3).
  *(Open: one-shot vs continuous re-adjustment — see §9 Q.)*
- **Focus-assist dev tool (FUTURE task, captured here):** a companion dev view that uses a **sharpness
  algorithm** (e.g. maximise high-frequency energy / line contrast on the CFL lines) to help focus the
  grating-on-lens stack **better than the eye alone**. The instrument is already correctly focused; this is
  a quality aid that matters mostly for calibration. Not scoped yet — logged so it isn't lost.
- **Best-fit auto-exposure algorithm** (parent §9.3) — out of scope here; under discussion.
- **Android** — out of scope (`CaptureBackend` Android branch raises; parent §2.1).
- **Windows manual picker** — auto-resolve is the Linux-reference path; the Windows DirectShow
  ambiguity/fallback (parent §3.4) is a later concern, not part of SM1.

---

## 7. Implementation phases (implement on explicit request, in order)

Each phase has an independent verification gate; nothing after it starts until its gate passes.

```
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| Ph   | What                           | New / Touched                          | Gate (drive-and-observe)                 | Risk   |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| P0   | Resolver (parent R0) — LIFT    | NEW SensorCaptureIndexResolver         | resolveCaptureIndex(ELP)->0; rejects     | LOW    |
|      | the proven sysfs logic out of  | (adapt camera_capture_probe.py         | metadata node; None when unplugged.      |        |
|      | the probe into app code        | resolve_capture_index)                 | Unit-testable with a fake sysfs tree.    |        |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| P1   | Backend owns cv2; VideoThread  | TOUCH VideoThread (add setDeviceId,    | Existing VIRTUAL Hough calibration still | MEDIUM |
|      | routes through it (parent R1). | route non-virtual via backend),        | works unchanged; real calibration view   | (edits |
|      | Drop forced MJPG; tolerate     | CaptureBackend (own the flags, no      | still streams the ELP through the        | shared |
|      | empty reads. Params stay       | forced MJPG). Android untouched        | backend (index 0 ok here). No regression | live   |
|      | HARDCODED (no CaptureSettings  | (virtual branch never opens a cam).    | on virtual or Android import.            | code)  |
|      | build-out yet).                |                                        |                                          |        |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| P2   | Thin capture thread that emits | NEW DevCaptureVideoThread (Hough       | Emits frames to a VideoViewModule in a   | LOW    |
|      | each QImage to the preview     | thread minus ROI logic) + its frame    | throwaway harness; base VideoThread's    |        |
|      | (fills RD-1 gap).              | signal.                                | missing view-signal is covered.          |        |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| P3   | Dev capture view + wire into   | NEW DevCaptureViewModule; TOUCH        | Full §8 click-through: live ELP stream;  | LOW-   |
|      | Settings>Development           | SettingsViewModule (button, nav        | Save(copy) writes real PNG; unplug ->    | MED    |
|      | (master-only). Auto-resolve,   | target, master-gated). Save does       | not-connected + Start/Save read-only;    |        |
|      | status, Start/Stop, Save-as-   | qImage.copy() (RD-2).                   | replug recovers; 2nd webcam does NOT     |        |
|      | PNG (free filename).           |                                        | hijack (needs a 2nd camera on the bench).|        |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
| P4   | (OPTIONAL) live resolution     | TOUCH DevCaptureViewModule (combo;     | Switch modes live; human notes sharpest  | LOW    |
|      | combo — the §9.2 tool.         | hardcoded per-chipset candidate list,  | CFL mode -> records it in KB §7. Does    |        |
|      |                                | set-and-readback probe — RD-5).        | NOT gate P3.                             |        |
+------+--------------------------------+----------------------------------------+------------------------------------------+--------+
```

**Dependency order:** P0 → P1 → P2 → P3 (P4 optional, after P3). P0 and P1 are independent enough that
P1 can even be validated **before** P3 exists, using the *existing* real calibration view as a free R1
test harness (see RD-8).

---

## 8. Verification (click-through — Edwin's drive-and-observe review)

With the ELP plugged in, logged in as a master user:
1. Settings → Development → **Capture images** opens.
2. Sensor = ELP → status shows the resolved node; **live ELP frames** stream in the view.
3. **Save frame…** → type a name → a real PNG is written and re-opens as the captured frame.
4. **Unplug** the ELP → status flips to *"not connected"*, **Start/Save read-only** (no crash, no black
   frame spew).
5. **Replug** → status recovers; streaming works again.
6. With a **laptop webcam also connected**, ELP is still the one streamed (resolver picks by VID/PID,
   not index 0).
7. (If S1.5 optional resolution combo built) switch modes → live view changes; the human notes which
   mode resolves the CFL lines sharpest → records it in `KB_spectroscopy_physics.md` §7.

---

## 9. Rubber-duck pass — design risks surfaced against the as-is code (2026-07-06)

Recorded, not all resolved — flagged so implementation doesn't trip on them.

1. **"Reuses VideoThread" understates a small gap.** The **base** `VideoThread` sets `self.qImage` but
   **emits no frame signal to any view** (`onCapturedFrame` is commented out, `VideoThread.py:117`). The
   live views work only because each calibration subclass adds `videoThreadSignal.emit(...)` in its own
   `afterCapture()` override (e.g. `SpectrometerCalibrationProfileHoughLinesVideoThread`). So SM1 needs a
   **thin `DevCaptureVideoThread`** that emits the raw `QImage` each frame to `VideoViewModule` — the Hough
   thread minus the ROI logic. Minor, but it is *new* code, so §2's "nothing new in the pipeline" means
   "nothing new *downstream of capture*," not literally zero new classes.

2. **Save-during-stream can crash on the numpy buffer.** The `QImage` wraps the cv2 frame's numpy buffer
   directly (`VideoThread.py:112`, with an existing comment that the wrong format "crashes … after some
   frames" — a buffer-lifetime symptom). If the user hits **Save** while the thread is overwriting that
   buffer, the saved/So-displayed image can tear or hit freed memory. **Mitigation:** Save must snapshot
   `qImage.copy()` (deep copy, detaches from the numpy buffer) — or briefly pause the stream — before
   writing. Cheap; must be in the design.

3. **Auto-resolve on Linux is sysfs; Windows needs a different enumerator → SM1 is Linux-first.** pyusb
   (`isSensorConnected`) only answers *presence*, not the cv2 index; the USB-device→index bridge is
   **V4L2/sysfs on Linux** and the **DirectShow moniker path on Windows** (parent §2.1). The Linux path is
   verified; the Windows moniker enumerator (pygrabber/WMI) is *achievable but not yet built/tested*. So
   until that lands, the SM1 dev view on **Windows** would fall back to the manual picker / index 0 — i.e.
   auto-resolve is a **Linux-first** capability. Acceptable for a bench/dev tool, but state it in the view
   on Windows so it doesn't read as a bug. Flagged for Edwin: confirm Windows auto-resolve is a later
   milestone, not folded into SM1.

4. **Sensor combo is catalog-only → cannot stream a camera not in the catalog.** Auto-resolve keys on a
   known sensor's VID/PID (ELP / Microdia), so an arbitrary webcam or a new, uncatalogued spectrometer
   camera **cannot** be viewed here. Fine for the stated purposes (debug the *spectrometer* camera; build
   filesets from *real* captures) — noted so nobody expects a generic "any camera" grabber. A new camera
   model must be added to `SpectrometerSensorUtil` first.

5. **The optional resolution combo can't trivially enumerate modes via OpenCV.** cv2 exposes no clean
   "list supported modes" call; in practice you set W/H and read back what the driver accepted, or shell
   out to `v4l2-ctl`. So the live-resolution control (§5) likely needs a **hardcoded candidate list per
   chipset, probed by set-and-readback**, not a true enumeration. Keeps it optional/nice-to-have and does
   not gate S1.2.

### Second rubber-duck pass — implementation-sequencing risks (2026-07-06)

6. **P1 is the one risky phase — it edits shared, *working* code.** R0 is additive (new util) and R3-view
   changes are additive; but P1 refactors `VideoThread`, which the **virtual** calibration flow depends on
   today. Rule: keep the **virtual branch byte-for-byte untouched** (the backend is only entered on the
   non-virtual branch); default backend params = today's constants **minus** forced MJPG. Two behaviour
   changes to validate explicitly at P1's gate: (a) virtual Hough still renders; (b) the real path still
   streams the ELP **without** forced MJPG (the probe found un-forcing is *better*, but it is still a
   change).
7. **Android must not regress at P1.** `VideoThread` is shared with Android, which runs **virtual-only**,
   so it must never reach `getCaptureBackend().open()` or the resolver. Guard: the resolver import and any
   sysfs/pyusb touch stay on the non-virtual branch; `getCaptureBackend()` already returns the raising
   Android backend but `open()` is never called there. Add a P1 check: Android import + virtual capture
   still work.
8. **Free R1 test harness — validate P1 before building the view.** The *existing* real calibration view
   already drives a real `VideoThread` (index 0). So P1 can be regression-checked there (virtual + real)
   **before** P2/P3 exist — decoupling the risky refactor from the new UI. Do that rather than discovering
   a backend bug through the new view.
9. **Don't build `CaptureSettings` in SM1.** Parent §3.2 proposes a `CaptureSettings` value object; SM1
   keeps params **hardcoded**, so a single hardcoded default inside `DesktopCv2CaptureBackend` suffices.
   Promote to `CaptureSettings` only when configurability (frame count / per-chipset res / exposure)
   actually lands — avoids over-building ahead of the deferred "configurable, likely plugin-driven" work.
10. **Verification is hardware-gated and needs a *second* camera.** Every P1/P3 gate needs the ELP
    physically attached; the "no-hijack" check needs a **second camera** (laptop webcam) on the bench.
    These are Edwin's click-throughs, not CI — only P0 (resolver, fake-sysfs) and P2 (thread, harness) are
    meaningfully unit-testable. Bench prerequisite to line up before P3.

**Consistency check with SM2 (holds):** the resolver identifies a camera only to **chipset** granularity
(VID/PID is shared by all units of a model). So SM2's "does the attached camera fit the selected
spectrometer" can verify *chipset match* but **not** *this exact physical unit* — unit identity is the
printed **serial** (parent §9.1), which lives in the connection/calibration UX, not in USB resolution.
SM2 must not over-promise unit-level matching from the resolver alone.

---

## 11. ROI overlay when a profile is assigned (DESIGN — implement on explicit request)

Status: **IMPLEMENTED 2026-07-09 (awaits click-through §11.6).** Edwin's ask: *in the dev capture view,
overlay the ROI box when the current SpectrometerSetup has a profile assigned.* Headless-verified: the sink
draws/updates/hides one normalised rect item; the `__assignedRoi` predicate gates correctly across
no-profile / full-ROI / sensor-mismatch / half-populated-ROI. New file `BaseGraphicsRectItem`; `setRoi`/
`clearRoi` on `DevCaptureVideoViewModule`; `__applyRoiOverlay`+`__assignedRoi` on `DevCaptureViewModule`,
called on build / sensor-change / view-open.

### 11.1 What "has a profile assigned" means here

The dev capture view holds **no `SpectrometerSetup`** (§ nav is sensor-level: it drives a sensor combo +
`SpectrometerSensorUtil`, not a setup object). The only device handle it can already reach is the **active
`SpectrometerProfile`** via `ApplicationSettings.getSpectrometerProfile()` (installed by
`ActiveSpectrometerProfileLogicModule.installFromSession()` — server-authoritative, re-fetched by serial).
The ROI is two hops down that chain:

```
SpectrometerSetup ─spectrometerProfileId(FK)→ SpectrometerProfile
                                                 └─spectrometerCalibrationProfileId(FK)→ SpectrometerCalibrationProfile
                                                       └─ regionOfInterestX1/Y1/X2/Y2  (int px, two corners)
```

So in this view the ask maps to a concrete, already-reachable predicate — **no new `SpectrometerSetup`
wiring required**:

> **Show the ROI overlay iff** an active `SpectrometerProfile` is installed **and** its
> `spectrometerCalibrationProfile` has all four `regionOfInterest{X1,Y1,X2,Y2}` non-`None`.

(The four-field completeness check mirrors `SpectralWorkflowEngine` §132–144 and the `_CAL_FIELDS` tuple —
a half-populated calibration is treated as "no ROI", overlay off.) A `SpectrometerSetup` with **no**
profile FK resolves to no active profile here → predicate false → no overlay, which is exactly the
requested behaviour.

**Guard — sensor must match the profile's device (recommended).** The ROI belongs to one calibration of one
device. If the user selects a sensor in the combo that is **not** the active profile's sensor, the ROI is
meaningless for that frame. Reuse the VID/PID match the view already computes in `__activeRealSensorIndex`
(DevCaptureViewModule.py:205–216): overlay only when `__currentSensor()` equals the active profile's
`spectrometer.spectrometerSensor` (same vendorId+modelId). Otherwise overlay off, even if a profile is
assigned. This keeps the box honest when the combo is pointed at a different camera.

### 11.2 Coordinate space — 1:1, with one stated assumption

- ROI corners are **integer pixels on the full-frame sensor image** captured at calibration time.
- The live preview `QImage` is that same full frame; `imageItem` sits at scene origin **unscaled**, so
  **scene coordinates == image pixels**, and `fitInView(imageItem, KeepAspectRatio)` handles view scaling.
  ⇒ A rect drawn in scene coords lands on the correct pixels **with no manual scaling**.
- The corners are **not** guaranteed top-left/bottom-right (X1=left, X2=right, but Y1=lower Hough line,
  Y2=upper — see PlaygroundCalibrationLogicModule.py:70–73). Build the rect from
  `min/max(X1,X2)` × `min/max(Y1,Y2)` so orientation can't invert it.
- **Assumption to state (caveat):** this holds only while **live capture resolution == calibration
  resolution.** Both use the hardcoded per-chipset capture params today (§6), so they match. If a live
  **resolution combo** (optional P4, §5) ever changes the mode mid-stream, the overlay would misalign — at
  that point scale the rect by `liveImage.width()/calibWidth` (and height). Since no calibration frame size
  is stored, P4 would need to record it. **Out of scope now; logged so P4 doesn't silently break the box.**

### 11.3 Where to draw — extend the sink minimally

`DevCaptureVideoViewModule` is today a "no overlays" sink (its docstring). Give it a small, **optional** ROI
capability rather than a new subclass — the scene/pixmap plumbing already exists in `BaseVideoViewModule`:

- Add `setRoi(x1, y1, x2, y2)` and `clearRoi()` to `DevCaptureVideoViewModule`.
  - `setRoi` creates-or-updates **one** rect item on `self.scene`, positioned in scene/pixmap coords
    (normalised via min/max per §11.2). No fill; **dotted primary-colour pen**, matching the existing
    calibration overlays (`ApplicationStyleLogicModule().getPrimaryTextColor()`, `Qt.PenStyle.DotLine`).
  - `clearRoi` removes/hides that item.
- **Primitive:** a single rect item is cleaner than four lines. Repo has `BaseGraphicsPixmapItem` /
  `BaseGraphicsLineItem` but (verify at impl) no rect base — either add a trivial `BaseGraphicsRectItem`
  (`QGraphicsRectItem` subclass, mirroring `BaseGraphicsLineItem`) or, to stay 100 % on the proven path,
  draw the four edges as `BaseGraphicsLineItem`s exactly like
  `SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule` (lines 158–178). Recommend the rect
  item.
- **Lifecycle — set once, not per frame.** The ROI is static for a given profile+sensor, and `setPixmap`
  on `imageItem` does **not** disturb other scene items. So the per-frame `handleVideoThreadSignal` stays
  unchanged (still just `setPixmap` + `fitInView`); the rect is added on top of the pixmap once and left in
  place. The rect is inside the pixmap bounds, so `fitInView(imageItem)` already frames it — no z-order or
  scene-rect changes needed (rect added after `imageItem` ⇒ painted on top).

### 11.4 Driving it from the parent view

`DevCaptureViewModule` owns the predicate (it already reads the active profile and knows the selected
sensor). Recompute-and-apply at the moments the inputs can change — **not** per frame:

1. **On view open / after the profile is (re)installed** and **on sensor-combo change** and **on stream
   start**, call a private `__applyRoiOverlay()`:
   - resolve active profile → `spectrometerCalibrationProfile`;
   - if predicate (§11.1) true **and** sensor-match guard passes →
     `videoViewModule.setRoi(cal.regionOfInterestX1, …Y1, …X2, …Y2)`;
   - else → `videoViewModule.clearRoi()`.
2. Because the active profile is server-authoritative and installed once per session, no live DB polling is
   needed; if desired, `ActiveSpectrometerProfileLogicModule().installFromSession()` can be called on view
   open so a just-authored calibration shows immediately (same pattern the dev measurement bench uses).

### 11.5 Explicitly out of scope for this addition

- **No `SpectrometerSetup` object is wired into the view.** The predicate is satisfied through the active
  `SpectrometerProfile` handle the view already has. If a genuine "current setup" concept later lands in
  `ApplicationSettings` (there is no `getSpectrometerSetup()` today), the predicate can move to it verbatim.
- **No ROI editing/dragging** — this is a **read-only overlay** of the assigned calibration's ROI. ROI
  authoring stays in the calibration flow (`SpectrometerCalibrationProfileHoughLines*`).
- **No resolution-scaling** (§11.2 caveat) until/unless the optional P4 resolution combo lands.

### 11.6 Verification (click-through, when implemented)

With the ELP plugged in, logged in as master:
1. **Profile assigned + sensor matches** → open Capture images → the ROI box is drawn over the live stream
   at the calibrated pixel bounds; it stays put as the window resizes (rides `fitInView`).
2. **Switch the sensor combo to a different real sensor** → box disappears (guard §11.1); switch back →
   reappears.
3. **Log in / select a device whose profile has no ROI (or no profile assigned)** → **no** box, no error.
4. Box corners visually coincide with where the calibration/wavelength views crop (same X1/X2 band).

---

## 12. Cross-references

- `SPEC_real_camera_capture.md` — parent; R0/R1 realised here, calibration (R2/R3) is sub-milestone 2;
  §9.2 best-resolution loop, §9.1 per-unit serial identity.
- `KB_spectroscopy_physics.md` §7 — hardware; the per-camera best-resolution finding is recorded there.
- `SPEC_pumpkin_integration.md` A.4 — the `calibration/reference/sample.png` virtual-fileset convention.
- `VirtualSpectrometerViewModule.py` — the consumer of saved filesets.
- `SpectrometerCalibrationProfile.py` (spectracsPy-model) — holds `regionOfInterest{X1,Y1,X2,Y2}` (§11.1).
- `ActiveSpectrometerProfileLogicModule.py` — installs the active profile the overlay predicate reads.
- `SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule.py` — the overlay pattern §11.3 mirrors.
