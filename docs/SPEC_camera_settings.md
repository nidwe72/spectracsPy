# SPEC — Camera settings: one declared, applied and recorded state (DESIGN)

Status (2026-10-18): **DESIGN only — Q1–Q10 all decided (§8); two rubber ducks folded in place (§10 D1–D14, §11 E1–E14)** — implementation only on Edwin's explicit request.
Grew out of `SPEC_windows_build.md` W1.4/W1.4b (§11c.11, §11c.12) and D10. It **absorbs** three planned steps of that
spec: the image-controls half of **W1.4b**, **W1.5b** (white balance declared by the plugin) and **W1.5** (the
exposure converter + `exposureUnit`) — they become phases here (§9), so they are not built twice.

Source: Edwin, 2026-10-18:

> * the plugin should have the possibility to overwrite all camera settings if needed
> * there should be some way for the plugin and other code to retrieve the default settings by some mean/utility
> * the capture backend should explicitly set the default values or plugin-overwritten values in order to ensure
>   that the values are consistent for every use case
> * the measurement report should have a section on the camera settings used — for this an appropriate domain
>   model should be created/updated
> * not quite sure how to integrate that into the existing Workflow, probably it should be rendered as part of
>   ACQUISITION step (reference and sample, though both should coincide). what you think?

---

## 1 — Today (what exists, where it is scattered)

| setting | who decides today | where | recorded? |
|---|---|---|---|
| exposure | plugin `DevSpectralPlugin.exposure = 90` (V4L2 units), else the AE sweep; calibration: AE sweep 1..500 | `CapturePanel.__pinnedExposure`, `VideoThread.requestAutoExpose` | ✅ `workflow.exposureApplied` (transient, report-JSON header; legs compared, mismatch printed) |
| frames | plugin `FRAMES` / `MeasurementStep.frames` | plugin | in the step |
| white balance | host constant `DevCaptureVideoThread.WHITE_BALANCE_KELVIN = 6500`; every other opener = auto | `CaptureBackend.open` | log line only |
| gain 0, backlight 0, manual AE mode | host, hard-coded | `CaptureBackend.open` (Linux, cv2) / `planControls` (Windows) | CAPTURE-SETTINGS log line only |
| brightness, contrast, saturation, hue, gamma, sharpness, power-line, dynamic framerate | **Linux: nobody** (whatever is in the camera) · Windows: device default (`planControls`, ids 0–5/7–9 only) | — | nowhere |
| backend, pixel format, conversion | host | `CaptureBackend` | log line only |

Three problems: (1) Linux leaves eight controls to chance — UVC values live **in the camera** and survive any
program that touched them (§11c.11 saw the VM's and the probe's values persist); (2) the plugin can pin exactly one
control; (3) the report carries one number (`exposureApplied`), the rest exists only in stdout.

**How the camera is really used (D1, D3)** — not "one open per leg", but one long-lived stream per opener, with
exposure changed mid-stream:

| opener | file | today's mode | exposure after open |
|---|---|---|---|
| measurement capture (bench + wizard) | `CapturePanel.py:511` `DevCaptureVideoThread` | WB 6500 frozen | AE sweep (~8 `setExposure`) or plugin pin; the sample leg only `setLiveExposure(locked)` — **same open for both legs** |
| dev capture view | `DevCaptureViewModule.py:329` | measurement thread, **no plugin** | seeded from `calibrationExposure`, slider, AE |
| calibration views (Hough lines, wavelength) | `…HoughLinesViewModule.py:130`, `…WavelengthCalibrationViewModule.py:168` | WB auto | opened at the legacy 150, then **AE sweep 1..500** |
| warm-keeper | `CameraWarmupService.py:85` | WB auto (calibration semantics) | `calibrationExposure` from `MainStatusBarViewModule.py:298`; continuous whenever the lease is free |
| legacy SpectralJob | `SpectrumVideoThread` | WB auto | — |

## 2 — The rule

**Every open sets every control the camera offers, to a value resolved as
`device default  ←  spectral profile  ←  plugin override`, reads every one back, and so does every later control
change; each capture leg snapshots the read-back at its start and end, and those snapshots are part of the
measurement record and the PDF.**

Three layers, three different kinds of thing (Edwin, 2026-10-18: *"how to handle 'default device settings' versus
'default spectral measurement settings'?"*):

| layer | what it is | owner | stored where |
|---|---|---|---|
| **device default** | the camera's factory state — a FACT about the camera, read-only | the manufacturer | in the camera firmware (`GET_DEF`), read at open; nowhere in our code/DB |
| **spectral profile** | Spectracs' settings for a USE CASE — what a spectrum needs, independent of any plugin. **CALIBRATION**, **MEASUREMENT**, **IDLE** (D1) | the host (Spectracs) | one table in code (-core, §3.3); per-camera numbers in the **code** dict `SpectrometerSensorUtil.py:26` (`calibrationExposure`) — ⚠ not the DB (D2) |
| **plugin override** | what one evaluation needs beyond the profile | the plugin | the plugin's `cameraSettings()` (§6) |

⇒ "default" alone is banned in this spec and in the report: it is either the **device default** or the **profile**
value. Every opener passes its profile **explicitly** to `open()` — never inferred from `whiteBalanceKelvin is None`
again (D1).

## 3 — Domain model (Qt-free, `spectracsPy-core`)

Placement (E11): the **vocabulary** — `CameraControl`, `CameraSettings` — in `plugin_sdk/camera/`, exported from
`plugin_sdk/__init__.py` (that also freezes it; `lintSelfContained` already allows `plugin_sdk.*`,
`PluginPublishUtil.py:22-29`). The **profiles + `resolve()`** in -core **outside** the SDK
(`logic/application/camera/`): host policy, so a profile edit is not an SDK-surface change.

### 3.1 `CameraControl` — OS-neutral names

One enum, the vocabulary every layer uses. The OS mapping lives in the backends (§5), never in the plugin.

| `CameraControl` | V4L2 (Linux) | DirectShow (Windows) | unit in the model |
|---|---|---|---|
| `EXPOSURE` | `EXPOSURE_ABSOLUTE` | `CameraControl_Exposure` (id 4) | **V4L2 units (100 µs)** — the plugin contract; the backend converts (Windows: whole log₂ s, `v4l2 = 10000·2^k`) |
| `AUTO_EXPOSURE` | `EXPOSURE_AUTO` (menu — ELP offers only 1 = manual, 3 = aperture priority; mapped via `QUERYMENU`, D6d) | Exposure flags | `MANUAL` / `AUTO` |
| `WHITE_BALANCE_AUTO` | `AUTO_WHITE_BALANCE` | WhiteBalance flags | bool |
| `WHITE_BALANCE_KELVIN` | `WHITE_BALANCE_TEMPERATURE` | `VideoProcAmp_WhiteBalance` (7) | K |
| `GAIN` | `GAIN` | `VideoProcAmp_Gain` (9) | camera units |
| `BACKLIGHT` | `BACKLIGHT_COMPENSATION` | `VideoProcAmp_BacklightCompensation` (8) | camera units |
| `BRIGHTNESS`, `CONTRAST`, `HUE`, `SATURATION`, `SHARPNESS`, `GAMMA` | same names | `VideoProcAmp_*` (0–5) | camera units |
| `POWER_LINE_FREQUENCY` | `POWER_LINE_FREQUENCY` (menu; newer kernels also 3 = auto) | KS VideoProcAmp id 13 — **to be probed (CS0)** | `DISABLED` / `50` / `60` / `AUTO` |
| `DYNAMIC_FRAMERATE` | `EXPOSURE_AUTO_PRIORITY` | KS CameraControl id 19 — **to be probed (CS0)** | bool |

⚠ "camera units" are deliberate: Gamma 100 on the ELP is not Gamma 100 on another camera. A plugin that overrides
an image control is therefore camera-specific by nature — the record (§4) says which camera it was.
⚠ The Windows "skipped" entries are no longer guesses (D5): W1.0b only probed VideoProcAmp ids 0–5/7–9; CS0 probes
6, 10–13 and CameraControl 19 in the VM before anything is written as "not exposed".

### 3.2 `CameraSettings` — a value object

`{CameraControl: value}`, partial or complete, immutable, `toJson()` / `fromJson()` with **plain strings as keys**
(-model and a LIMS addon need no enum; -core imports -model, never the reverse). Instances:

- **device defaults** — what the firmware reports (`GET_DEF`, §3.4), plus each control's range, step, menu;
- **requested** — the resolved target (§3.3), with a per-control *source*;
- **applied** — a read-back.

### 3.3 Resolution — `CameraSettings.resolve(deviceDefaults, profile, pluginOverride)` (pure, unit-tested)

1. **device default** for every control the camera offers;
2. **spectral profile** of the opener — the rules that exist today (`CaptureBackend.open`, `planControls`), moved
   into one table;
3. **plugin override** — MEASUREMENT only (§6.2) — wins over both;
4. **clamp** into the range **and snap to the control's `step`** (D6e — otherwise Q4's refusal fires on
   quantisation), transparently: `requested 7000 → 6500 (clamped)`, never silently;
5. a control the camera does not offer is dropped and listed as `skipped`; a control that is **inactive** in the
   resolved state (WB temperature under auto WB) is neither written nor compared (D6b/c).

The ELP, all layers (device defaults from §11c.11 of the Windows spec; "—" = the profile keeps the device default):

| control | device default | CALIBRATION | MEASUREMENT | IDLE (warm-keeper) | DevSpectralPlugin |
|---|---|---|---|---|---|
| auto exposure | 3 (aperture priority = **auto**) | **manual** | **manual** | **manual** | — |
| exposure | 78 | opened at the legacy **150**, then **AE sweep 1..500** (D2) | — (AE sweep if the plugin pins nothing) | `calibrationExposure` (150) | **90** |
| white balance auto | **on** | on — the peak detection is tuned for it | **off** | **off** (D1) | — |
| white balance temperature | 4600 K (inactive while auto) | — (inactive) | 6500 K (the lamp) | 6500 K | **6500 K** (declared explicitly, Q7) |
| gain | 0 | 0 | 0 | 0 | — |
| backlight compensation | **1 (on)** | — (on) | **0 (off)** | **0 (off)** | — |
| brightness / contrast / saturation / hue / gamma / sharpness | 0 / 32 / 75 / 0 / 100 / 3 | — | — | — | — |
| power line frequency | 50 Hz | — | — | — | — |
| dynamic framerate | off | — | — | — | — |

- ⭐ **IDLE = MEASUREMENT minus the plugin (D1).** Today the warm-keeper opens with calibration semantics, so under
  "every open sets every control" it would put auto WB and backlight 1 back between sessions. With IDLE the
  measurement open finds WB, backlight, gain and the image controls already in place. ⚠ Not "settles at frame 0"
  (E5): IDLE runs at `calibrationExposure` 150, the measurement at 90 ⇒ the exposure still changes and the
  hold-back (§5) still applies. The dev capture view uses MEASUREMENT with no plugin;
  the legacy SpectralJob uses CALIBRATION.
- ⭐ **Backlight (Edwin's question) — yes:** the ELP ships with backlight compensation **on** (1), an in-camera
  brightness correction that reacts to the scene, so it would change the frame between reference and sample.
  MEASUREMENT and IDLE turn it **off**; CALIBRATION keeps the device default. Same pattern for white balance.
- ⚠ **Calibration changes once (D12):** today a Linux calibration open does not reset backlight, so calibrations
  authored after a measurement session ran with backlight **0** left in the camera; the CALIBRATION profile sets
  **1**. ⇒ after CS2 the ELP calibration is re-checked once (ROI, peak positions) on the rig.

### 3.3a Exposure is a LIVE control — `resolve()` gives only its seed (E3, E5)

Every other control is set once per open. Exposure is changed while streaming — the AE sweep (~8 steps), the
operator's slider, the lock onto the sample leg. ⇒ `resolve()` produces the **seed** (plugin pin › profile seed ›
device default; the host supplies `calibrationExposure` as IDLE's/CALIBRATION's seed, since that dict lives in -model),
and each later change carries its own **source** (`auto-exposure`, `operator`, `locked-from-reference`):
`setLiveExposure(value, source)`.
- **Quantiser per control, supplied by the backend** with the device defaults: Linux = the V4L2 `step`; Windows
  exposure = whole log₂ steps. `resolve()` snaps through it; it cannot derive log₂ from a linear `step`.
- **`setExposure()` returns the applied value in V4L2 units** (Windows: `10000·2^k`, e.g. 90 → 78); VideoThread stores
  *that* in `_appliedExposure` (today it stores the request, `VideoThread.py:110/122/245`). The read-back comparison
  runs against the snapped value — otherwise every Windows AE probe logs ⛔.
- **The AE stays in V4L2 units on Windows too** (never native: `MIN_SEARCH_EXPOSURE = 2` would give `lo > hi`);
  `readCameraSettings` reports `exposureMin/Max` converted to V4L2 units (≈1.22..5000), so the slider and the AE learn
  the real range (today `__refreshExposureRange` ignores the native −1, `CapturePanel.py:608`). Probes that collapse
  onto the same `k` are harmless.
- **`exposureApplied` on Windows (E13):** the PDF and the header carry **both** the requested V4L2 value and the
  native one (`90 → −7 = 78`), so `d2r_all_runs.py:1489`'s "pinned = 90" test still reads the request.

### 3.4 Device defaults — where they come from, who can read them

- **Source:** the camera's firmware. Every UVC control answers `GET_DEF`; Linux `uvcvideo` returns it as
  `VIDIOC_QUERYCTRL.default`, Windows `usbvideo.sys` as `GetRange(..., pDefault, ...)`. Proven equal on both
  OSes for the ELP. **Nothing is stored in code or DB** — only the control names (§3.1) are code.
- **Utility:** `CaptureBackend.readDeviceDefaults(deviceId) -> CameraSettings` (defaults + ranges + steps + menus +
  quantiser), **static, no open, no stream** — Linux QUERYCTRL on its own fd, Windows COM `GetRange`; both safe from
  the GUI thread while the warm-keeper streams (E4). Reached by other code through the video thread (as `readCameraSettings` is today) and
  by the plugin through the host (§6) — **never** by a plugin touching the device: plugins are signed DB rows.

## 4 — The record: two levels, stored on the acquisition step (D3, D7)

```
CameraOpenRecord            (once per open — what was ASKED for)
  profile         "CALIBRATION" | "MEASUREMENT" | "IDLE"
  camera          {name, vendorId, modelId, sensorSerial}
  host            {os, backend: V4L2|MSMF, pixelFormat, conversion: own|backend, opencv}
  deviceDefaults  CameraSettings (+ ranges, steps)
  requested       CameraSettings (+ per-control source: device|profile|plugin, clamped/snapped flag)
  skipped         [CameraControl]   ·   inactive [CameraControl]
  heldBackFrames  int

CameraLegSnapshot           (per capture leg — what was IN FORCE)
  role            "reference" | "sample" | …
  atStart, atEnd  CameraSettings (read-back) + exposureNative {value, unit: "v4l2_100us" | "log2_s"}
  exposureSource  device | profile | plugin | auto-exposure | operator | locked-from-reference
```

- **Why two levels (D3):** one `DevCaptureVideoThread` serves both legs (`CapturePanel.py:511`); the sample leg only
  re-locks the exposure (`:345`); the AE sweep sets exposure ~8 times after the open (`VideoThread.py:109,121`), the
  slider too. So "the read-back after the open" is not what a leg ran under. The snapshot at **leg start and leg
  end** is. ⚠ Today `__logCameraSettings` runs **once, at the end** of a leg (`CapturePanel.py:992`, burst and monitored
  paths both arrive there) — that is the **end** snapshot; the **start** snapshot is new, after the AE / first frame
  (`:884/:889`) (E8). The end snapshot catches drift over a minutes-long monitored sample.
- **Each leg also carries `requestedExposure` + its source** (§3.3a), not only the open record (E5).
- **`setExposure` reads back too** (D3): the open's refusal stays an open-time rule; a later change that does not
  read back as requested is logged ⛔ and lands in the snapshot — it is not silently trusted.
- **Where it lives (D7) — on the step, not a workflow column:** a `CameraSettingsRecordView` view-model
  (`spectracsPy-model`, `isShownInReport = False`, registered in `ViewModelFactory`), one per leg on that
  **acquisition step's `EvaluationResult`** — the precedent is the settling view (`SpectralWorkflowEngine.py:399-401`).
  ⚠ No engine path touches the `EvaluationResult` for a plain burst ⇒ new `engine.attachCameraRecord(step, view)`,
  mirroring `__attachMonitorViews` (`:393-402`), replacing by **`isinstance`** — `isMonitorView` is transient and does
  not survive a reload (E8). A cancelled or failed leg drops its record (`CapturePanel.py:957, :1170`).
- ⛔ **VIEW mode (E1):** a re-opened run renders a step's `EvaluationResult` items whenever any exist
  (`WorkflowPhaseRenderer.renderStep`, `render/WorkflowPhaseRenderer.py:47-51`). The reference step has none today,
  so `WizardViewModule.__computedPanel` (`:227`) falls back to the spectrum plot; with a record view attached the tab
  would go **empty** (the visitor ignores the unknown type, `WorkflowItemVisitor.py:76`). ⇒ `stepViewModels()` filters
  the record view out, and the re-opened acquisition step gets **the same sub-tabs as the live panel** (Q10,
  Edwin: "the camera table should be always a sub-tab"): `Spectrum` (today's container-plot fallback) | `Camera`
  (the shared table, §7) | the Settling tabs if any. ⚠ As far as the code reads, a settled sample step re-opened
  today shows only its Settling tabs and no plot (the items win over the fallback) — this layout brings the plot
  back too. Test beside `test_saved_run_shows_the_settling_tabs.py`.
  That gives: per leg by construction; persisted via `EvaluationResult.resultJson`
  (`PersistSpectralWorkflowLogicModule.py:83`); in the report JSON per step (`SpectralWorkflow.py:170-172`); rebuilt
  by `report_reconstruct.py:105` and a LIMS addon via `ViewModelFactory`; **no Alembic revision**. ⚠ Edwin's Q2 "yes,
  a column" was given for the earlier design — re-confirm (§8). `header.exposureApplied` is *derived* from the
  snapshots in `toReportJson`, so `diagnostics/d2r_all_runs.py` & co. keep working.
- **Re-measure replaces:** a new capture of a role replaces that role's record view (the `isMonitorView` rule); a new
  **reference** already drops the sample container (`CapturePanel.py:996-1000`) — the sample's record (and its
  settling view, an existing gap) go with it.
- **Leg comparison** generalises today's exposure check: the active controls of `reference.atStart` vs
  `sample.atStart` (and each leg's start vs end) — else `⛔ CAMERA STATE MISMATCH: GAMMA 100 vs 120`, recorded and
  shown in the PDF. T = S/R cancels none of these (§16.24.1).
- **Virtual run (D14, E8):** virtual capture never reaches CapturePanel — it is
  `WizardViewModule.__buildCapturePanel` → `engine.captureAcquisitionStep(step)` (`:211`) with `__virtualFrameProvider`
  (engine `:257`); the bench refuses virtual devices (`:300`). ⇒ the engine's `frameProvider is None` branch writes the
  record `virtual — no camera controls (fileset …)`; the comparison is skipped, the PDF prints that one line.

## 5 — Applying: one writer per OS, every open, every change

- **Linux — `LinuxUvcControls.py`**, the twin of `WindowsUvcControls.py`: ioctl `QUERYCTRL` / `QUERYMENU` /
  `S_CTRL` / `G_CTRL` on the `/dev/videoN` the resolver found (safe: `SensorCaptureIndexResolver.py:77-104` returns
  the sysfs N, cv2 V4L2 opens exactly that). Rules (D6):
  - **one writer** — every cv2 control `set` goes out of `open` and `setExposure` (`CaptureBackend.py:183-217`,
    `:448-449`); cv2 keeps only format, size, buffer size, `CONVERT_RGB`;
  - **order** — `EXPOSURE_AUTO` → manual before `EXPOSURE_ABSOLUTE`; `AUTO_WHITE_BALANCE` off before the
    temperature; never write an `INACTIVE`-flagged control;
  - menus through `QUERYMENU`; node opened `O_RDWR`; applied **once, after the final cap exists** (after
    `__reopenUnforced` if it ran); `fcntl` imported lazily (R7);
  - **threads (E6):** `readCameraSettings` runs on the GUI thread (`CapturePanel.py:599, :705`) and today calls `cv2.get`
    on the worker's `VideoCapture` — safe only because the worker is parked. All reads go through
    `LinuxUvcControls`' own fd (the kernel serialises ioctls); VideoThread's check-then-use of `self._backend`
    (`:79`) vs `release()` (`:223-225`) gets a lock;
  - ℹ **what the read-back proves:** uvcvideo answers `G_CTRL` from its cache once a control is loaded ⇒ it catches
    driver clamping and refusals, **not** a camera that silently ignores `SET_CUR`. The leg snapshots' image
    statistics are the only evidence of that; stated, not hidden.
- **Windows:** `planControls` becomes the generic resolve; `WindowsUvcControls` keeps its COM side and gains the
  **exposure set natively** (`IAMCameraControl.Set`) with the V4L2→log₂ converter, used by `open` **and**
  `setExposure` — the AE sweep on win32 pushes V4L2 numbers through cv2 MSMF today (`:448`). ⇒ CS3 and the
  converter are one phase (D4), or every Windows measurement is refused on `requested 90 vs applied −8`.
- **Proof, both OSes:** a MEASUREMENT open whose read-back does not match *requested* on any active control is
  **refused** (Q4: image controls too). CALIBRATION and IDLE warn.
- ⛔ **A refusal must STOP, not spin (E2).** Today a refused open sets `_cap = None`, `read()` returns None at once and
  `__captureLoop` / `__capturePhysicalFrame` (`VideoThread.py:231-278`) spin with no sleep; the operator finally reads
  "No frames were delivered". ⇒ `open()` returns the `CameraOpenRecord` with a `refusal`; VideoThread emits
  `cameraRefused(str)` and leaves `run()`; CapturePanel shows the reason. (Windows has the same defect today.)
- **Settling hold-back (5 frames, Edwin)** — owned by `VideoThread` (D13, E7): a counter set after `open` (merging the
  warm-up loop at `:217-219`) and after a live `setExposure` (`:244`); `__capturePhysicalFrame` consumes held-back
  frames **without** `afterCapture`, so `frameIndex` does not advance, and sends them through `_emitPreview`
  (`isPreview=True`) — CapturePanel already keeps preview frames out of `__latestImage` (`:563`), and the live view does
  not freeze ~3 s on every slider tick. Excluded: the AE's probes **and** its final `best` step
  (`__settleUntilStable`, `:129`, already settles it). `heldBackFrames` per leg = "since the last change before this
  leg", usually 0 for the sample.
- Today's ELP values are the device defaults ⇒ no MEASUREMENT number changes; CALIBRATION changes once (§3.3, D12).

## 6 — The plugin side

### 6.1 Declaring

```python
class DevSpectralPlugin(SpectralPlugin):
    def cameraSettings(self, deviceDefaults):          # MEASUREMENT only; base class returns None
        return {"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500}   # a plain dict is enough (D10b)
```

- Returns a **partial** override — a `CameraSettings` **or a plain `{name: value}` dict**: a new plugin row that
  imports `plugin_sdk.camera` would `ImportError` on an older app, and the strict `SDK_VERSION` gate cannot see it
  (`version.py`); bumping the version would kill every signed v1 row (D10b).
- `deviceDefaults` is handed in by the host so a plugin can say *"device contrast + 4"* without touching hardware.
- **Sequence at the start of a measurement (E4)** — `CapturePanel.__startStream` (`:505`, thread created `:511`):
  1. `__resolveCamera`; 2. `CaptureBackend.readDeviceDefaults(deviceId)` (static, no open); 3. `plugin.cameraSettings(
  defaults)`, else the `exposure` attribute, inside try/except; 4. seed slider + AE checkbox from the override's
  exposure source; 5. `thread.setCameraProfile(MEASUREMENT)` + `thread.setOverride(…)`, then open. ⚠ Today
  `__syncExposureToSensor` runs in `__build` (`:294`), **before** `__resolveCamera` (`:126`) — it moves after it.
- ⚠ **DevSpectralPlugin keeps `exposure = 90` beside `cameraSettings()`** (E4): a new signed row loaded on an older app
  must not silently lose its pin.
- **Compatibility:** a plugin that still has only the `exposure` attribute (the signed v1.x rows) gets
  `{EXPOSURE: exposure}`; `cameraSettings` wins when both exist. `__pinnedExposure` also switches off the AE checkbox
  (`CapturePanel.py:397-472`) — CS4 routes that through the resolved **exposure source**, not the attribute (D10a).
- **White balance (Q7, Edwin: "both"):** the MEASUREMENT profile carries 6500 K (the lamp's colour, an instrument
  fact) **and** the plugin can — and DevSpectralPlugin does — declare it explicitly. The profile is the fallback for a
  plugin that says nothing; the explicit declaration makes the record read `source = plugin`.
- **Auto loops (D11, Q8).** An *auto loop* is a control the camera **keeps regulating by itself, frame by frame** —
  auto exposure, auto white balance, backlight compensation (an adaptive brightness correction). A plugin may change
  any frozen **value** (exposure, WB temperature, gain) freely. Switching an auto loop **on** in a MEASUREMENT means
  the camera may change the image *within* a burst, between two snapshots, where no read-back can see it.
  ⇒ **decided (Q8): no extra flag.** The override itself is already explicit code
  (`{"WHITE_BALANCE_AUTO": True}`), so it is accepted, recorded as `source = plugin`, and the PDF and the "Camera"
  tab carry `⛔ auto loop on — not a frozen instrument state` on that row. (The first proposal, a separate
  `allowAutoLoops = True` switch the plugin had to set as well, only made the plugin say the same thing twice.)

### 6.2 Calibration and measurement are two use cases — two profiles

Calibration (master authors the px→nm profile of a sensor) and a spectral measurement (a plugin evaluates a sample)
are distinct use cases (Edwin). Each has its own profile (§3.3); a plugin belongs to a measurement only, so its
override is applied on top of MEASUREMENT and never reaches CALIBRATION or IDLE.

## 7 — Workflow, PDF and GUI: where it shows

Edwin's question: *render it as part of ACQUISITION (reference and sample, both should coincide)?* — **Yes, one table
for the phase in the PDF, one inner tab per leg in the GUI.**

**PDF (measurement PDF, M2):** the report builder groups by **step only** (`WorkflowReportBuilder.__collectGroups`
`:60-97`), and DevSpectralPlugin sections ACQUISITION into Reference / Sample (`stepChevronPhases`,
`DevSpectralPlugin.py:1009`) ⇒ there is no phase-level slot (D8). ⇒ **one generic rule in -core's builder:** after the
ACQUISITION group(s), harvest the steps' `CameraSettingsRecordView`s directly (`willDrawInReport` rejects them,
`isShownInReport = False`) and append `("Camera settings", [cameraSettingsTable(records)], LEVEL_STEP)` —
**one `TableView` "Camera settings"**. The
builder is Qt-free and needs no plugin, so a LIMS addon rebuilding from JSON gets the same table.

```
Camera settings  —  HD USB Camera 32e4:8830 · Linux V4L2 · YUYV, own conversion          reference = sample ✓
┌────────────────────────┬────────────────┬───────────┬─────────────┬───────────────┐
│ control                │ device default │ requested │ applied     │ source        │
├────────────────────────┼────────────────┼───────────┼─────────────┼───────────────┤
│ Exposure               │ 78             │ 90        │ 90 (9.0 ms) │ plugin        │
│ White balance          │ auto           │ 6500 K    │ 6500 K      │ profile       │
│ Gain                   │ 0              │ 0         │ 0           │ profile       │
│ Backlight compensation │ 1 (on)         │ 0 (off)   │ 0 (off)     │ profile       │
│ Gamma                  │ 100            │ 100       │ 100         │ device        │
│ …                      │                │           │             │               │
└────────────────────────┴────────────────┴───────────┴─────────────┴───────────────┘
MEASUREMENT profile · held back 5 frames after open · skipped: —
```

- `applied` = the legs' snapshots; when they agree (start = end, reference = sample) one column. **On any difference**
  `applied` splits into `reference` | `sample`, the rows are marked ⛔, the header says `⛔ reference ≠ sample`.
- AE-chosen exposure reads `source = auto-exposure`, the locked sample `locked-from-reference`.
- **Windows:** `Exposure  90 → applied −7 (7.8 ms, nearest whole log₂ step)`.
- **Virtual run:** one line, `virtual — no camera controls (fileset …)`.
- **JSON:** the records already sit per step in the report JSON (§4) — no extra key needed.

**GUI (D9 — not a step):** a step-tab drives chevrons, auto-advance, `WizardViewModule.py:168` role filtering,
AcquisitionGuidance and mandatory-step completion; a roleless "Camera" step would be a third chevron that
auto-advance lands on. ⇒ follow the **"Settling" precedent**: an **inner tab "Camera"** in `CapturePanel`, showing the
active leg's snapshot with ⛔ on mismatch with the other leg. ⚠ There is **one** set of inner tabs, reparented between
the role pages (`__stepContent`, `CapturePanel.py:222, :318-323`) ⇒ the Camera tab is rebuilt in `__onRoleTabChanged`
(`:333`) from the active step's record (not Settling's stale-across-roles behaviour) (E10). Placed at **index 2, before
Settling** — the Director scenario addresses `innerTabs` by index (`automation/scenarios/measurement_bench.py:40`).
- **Who sees the tab (Q9):** only the **DevSpectralPlugin** — a new plugin hook `showsCameraTab() -> bool` (default
  `False`, Dev returns `True`), asked by the live `CapturePanel` **and** by the VIEW-mode host (which already loads
  the plugin from the persisted `pluginCodeRef`; a `CaptureView` flag would not survive a reload, `_view` is
  transient). Every other plugin's operator gets the table in the PDF only.
- **One Qt-free builder, three consumers (E9):** `cameraSettingsTable(records) -> TableView` in -core feeds the PDF, the
  Camera sub-tab live and the Camera sub-tab in a re-opened run; `TableView` already renders in both targets (Matplotlib `:585`, Qt `:488`). The record view
  stays **out** of the visitor dispatch ladder — no new visitor method anywhere.
- PDF limits: fontsize 6, right-aligned, no per-row colour ⇒ the mismatch is text in a column (`⛔ ref ≠ sample`);
  ℹ check the PDF font carries ⛔. ⚠ Edwin's Q5 "a tab of Spectral step" — re-confirm on this basis (§8).

## 8 — Decisions (Edwin, 2026-10-18) and what is open

| # | question | decision / proposal |
|---|---|---|
| Q1 | plugin override in calibration? | ✅ dissolved — calibration and measurement are two use cases with their own profiles (§6.2) |
| Q2 | where does the record persist? | ✅ **step view-model** on the acquisition step's `EvaluationResult` (Edwin re-confirmed after D7: "okay") — no column, no Alembic revision |
| Q3 | which report? | ✅ the measurement PDF (M2), after the ACQUISITION section |
| Q4 | read-back ≠ requested on an image control? | ✅ refuse (MEASUREMENT) |
| Q5 | GUI tab? | ✅ **inner tab "Camera"** on the Reference / Sample pages, like "Settling" (Edwin re-confirmed after D9: "okay") |
| Q6 | device default vs spectral defaults? | ✅ three named layers (§2) |
| Q7 | WB 6500 K: profile or plugin? | ✅ **both** (Edwin) — the MEASUREMENT profile carries it as the instrument fact; the plugin can and should override, DevSpectralPlugin declares it (§6.1) |
| Q8 | may a plugin switch an auto loop on in a measurement? | ✅ **yes, no extra flag** (Edwin: "sounds fine") — the explicit override is accepted, recorded `source = plugin`, and badged ⛔ in the PDF and the Camera tab (§6.1) |
| — | IDLE profile for the warm-keeper (D1) | proposal in §3.3 — speaks for itself, flagged so it is not a surprise |
| Q9 | does the **end-user wizard** show the "Camera" inner tab too, or only the master's bench? (`CapturePanel` serves both, `:162` / `:170`) (E10) | ✅ **only the DEV measurement bench plugin** (Edwin) — plugin hook `showsCameraTab()`, not a `CaptureView` flag (it would not survive a reload); everyone gets the table in the PDF |
| Q10 | a re-opened run (VIEW mode): where does the camera table go? (E1) | ✅ **always a sub-tab** (Edwin) — the re-opened step gets `Spectrum` \| `Camera` \| Settling, the same sub-tabs as live; not "beside the plot" |

## 9 — Phases (replace W1.4b-controls, W1.5 and W1.5b in SPEC_windows_build.md §12)

| phase | what | where | depends on | done when |
|---|---|---|---|---|
| CS0 | VM probe: VideoProcAmp 6, 10–13 + CameraControl 19 | VM, probe | — | §3.1 Windows column final |
| CS1a | vocabulary `CameraControl`, `CameraSettings` (plain-string JSON) in `plugin_sdk/camera`, exported | -core SDK | — | JSON round-trip tests |
| CS1b | profiles CALIBRATION/MEASUREMENT/IDLE + `resolve()` (backend quantiser hook, host exposure seed, clamp/snap, skipped, inactive) | -core `logic/application/camera` | CS1a | precedence, snap, skipped, inactive tests |
| CS2 | Linux `LinuxUvcControls` + static `readDeviceDefaults(deviceId)`; `open(profile=…)` applies + reads back (one writer, own fd, lock vs `release`); `setExposure` returns the applied value; **refusal stops + `cameraRefused` signal**; every opener passes its profile (incl. IDLE); diagnostics' `open(…, whiteBalanceKelvin=)` + Android/RPi signatures | Py | CS1b | fake-ioctl/controls-factory tests; broken cv2-order asserts rewritten; rig read-back == §11c.11; ELP calibration re-check |
| CS3 | Windows: `planControls` → `resolve`; exposure natively + converter in `open` and `setExposure` (returns `10000·2^k`); `exposureMin/Max` in V4L2 units; refusal stops | Py | CS0, CS1b | W1.6 tests rewritten; converter tests; VM "90 → −7 = 78" |
| CS4 | plugin `cameraSettings(deviceDefaults)` (dict or `CameraSettings`, base `None`); the §6.1 sequence in `__startStream`, `__syncExposureToSensor` moved; `setLiveExposure(value, source)`; DevSpectralPlugin declares exposure + WB and **keeps** `exposure = 90`; WB constant goes; hook `showsCameraTab()` (base `False`, Dev `True`, Q9) | -core, Py, plugins | CS2 (CS3 for Windows) | old signed row works; new row on an old app keeps its pin |
| CS5 | hold-back 5 in `VideoThread` (counter after open + live change; consumed without `afterCapture`; sent as preview); AE probes + `best` excluded | Py | CS2 | fake frame source: no held-back frame in a burst, preview not frozen |
| CS6 | `CameraOpenRecord` + `CameraLegSnapshot` (start after AE/first frame, end at `:992`, `requestedExposure` + source) → `CameraSettingsRecordView`; `engine.attachCameraRecord` (replace by `isinstance`); cancel/fail drops it; virtual record in the engine's `frameProvider is None` branch; `exposureApplied` derived (requested + native) | -model, Py | CS4, CS5 | round-trip via `ViewModelFactory` + `report_reconstruct.py`; `d2r_all_runs.py` unchanged |
| CS6.5 | Qt-free `cameraSettingsTable(records)` in -core; VIEW-mode filter in `stepViewModels()` + re-opened step as sub-tabs `Spectrum` \| `Camera` \| Settling (Q10) | -core, Py | CS6 | re-opened run shows the reference plot AND a Camera sub-tab (new test); settling test still green |
| CS7 | PDF: builder harvests the records after ACQUISITION, appends the table; mismatch as text; ⛔ glyph check | -core | CS6.5 | PDF shows the table; mismatch + virtual line rendered |
| CS8 | GUI inner tab "Camera" at index 2, rebuilt on role change; shown only when `plugin.showsCameraTab()` (Dev) (Q9) | Py | CS6.5 | click-through: filled after the reference leg; ⛔ on a forced mismatch; Director scenario still passes |
| CS9 | Windows: CS3 re-checked end to end in the VM + `buildWindows.sh` → W1.7 click-through | VM | CS3–CS8 | VERIFY ok |

Order rationale: the model first (CS1a/b) so both backends apply the *same* resolution; CS3 carries the exposure
converter or Windows refuses every measurement (D4); Linux leads (CS2 → CS4 → CS5 → CS6 …) and Windows (CS0, CS3) runs
in parallel, joining at CS9 (E: reorder); the record (CS6) only once the hold-back exists; the shared table (CS6.5)
before either consumer.

## 10 — Rubber duck (2026-10-18) — D1–D14, all folded in place above

| # | sev | finding | where it went |
|---|---|---|---|
| D1 | ⛔ | two profiles miss openers: the warm-keeper (calibration semantics, would re-enable auto WB + backlight between sessions), the dev capture view, legacy SpectralJob | IDLE profile, explicit `profile=` (§1, §2, §3.3) |
| D2 | ⛔ | calibration exposure is legacy 150 + AE 1..500, not `calibrationExposure`; that number is a code dict, not DB | §2, §3.3 |
| D3 | ⛔ | legs are not opens; exposure changes mid-stream (AE, slider, lock); `setExposure` unchecked | two-level record, leg start/end snapshots, exposure sources (§4) |
| D4 | ⛔ | Windows exposure refusal before the converter ⇒ every Windows measurement refused | converter merged into CS3 (§5, §9) |
| D5 | ⚠ | Windows "skipped" controls were guesses (ids 6, 10–13, CC 19 never probed) | CS0 (§3.1) |
| D6 | ⚠ | Linux ioctl rules: one writer, order, inactive controls, menus, step snap, O_RDWR | §3.3, §5 |
| D7 | ⛔ | record belongs on the step's `EvaluationResult`, not a workflow column (persisted, per leg, reconstructs, no Alembic) | §4; Q2 re-confirm |
| D8 | ⚠ | no phase-level slot in the report builder | builder rule in -core (§7) |
| D9 | ⛔ | a "Camera" step breaks chevrons / auto-advance / guidance | inner tab per role page (§7); Q5 re-confirm |
| D10 | ⚠ | AE checkbox tied to the attribute; ImportError on old apps; WB in two homes | plain-dict override, exposure source, Q7 (§6.1) |
| D11 | ⚠ | plugin switching auto loops on = within-burst drift | recorded + ⛔ badge, no extra flag (Q8, §6.1) |
| D12 | ⚠ | calibration DOES change (backlight 0 → 1) | stated + rig re-check after CS2 (§3.3) |
| D13 | ⚠ | hold-back owner unclear | `VideoThread`, before the signal, AE probes excluded (§5) |
| D14 | ℹ | virtual runs; missing test rewrites, SDK docs, header contract, Windows rebuild | §4, CS2/CS4/CS6/CS9 |

## 11 — Second rubber duck (2026-10-18, implementability) — E1–E14, folded in place above

| # | sev | phase | finding | where it went |
|---|---|---|---|---|
| E1 | ⛔ | CS6/8 | a record view on the reference step empties its tab in a re-opened run | VIEW-mode filter + table (§4, CS6.5, Q10) |
| E2 | ⛔ | CS2 | a refused open busy-loops and ends as "No frames were delivered" | refusal stops + `cameraRefused` (§5) |
| E3 | ⛔ | CS3 | Windows exposure: AE/slider range, snapped applied value, read-back vs request | §3.3a |
| E4 | ⚠ | CS4 | defaults-before-open sequence; `__syncExposureToSensor` order; keep `exposure = 90` | §6.1 |
| E5 | ⚠ | CS1–4 | exposure is live, not resolved once; IDLE does not settle at frame 0 | §3.3, §3.3a, §4 |
| E6 | ⚠ | CS2 | GUI-thread reads on the worker's cap; `_backend` race; G_CTRL is cached | §5 |
| E7 | ⚠ | CS5 | hold-back placement, preview, AE `best` excluded | §5 |
| E8 | ⚠ | CS6 | leg start is new (only the end is logged today); attach path; cancel; virtual seam | §4 |
| E9 | ⚠ | CS7/8 | one Qt-free table builder for PDF, tab, VIEW mode; PDF limits | §7 |
| E10 | ⚠ | CS8 | one set of inner tabs, reparented; wizard uses CapturePanel too; Director index | §7, Q9 |
| E11 | ⚠ | CS1 | vocabulary in the SDK, profiles + resolve outside it | §3 |
| E12 | ⚠ | CS2/3 | tests and diagnostics that break; Android/RPi signatures | CS2, CS3 rows |
| E13 | ℹ | CS6 | Windows `exposureApplied` = 78 for a pinned 90 | §3.3a |
| E14 | ℹ | — | stale line numbers in §4/§5 | fixed in place |
