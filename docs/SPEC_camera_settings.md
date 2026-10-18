# SPEC — Camera settings: one declared, applied and recorded state (DESIGN)

Status (2026-10-18): **DESIGN only — Q1–Q7 decided, rubber duck folded in place (§10, D1–D14); Q8 proposal
revised, awaits Edwin (§8)** — implementation only on Edwin's explicit request.
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

## 3 — Domain model (Qt-free, `spectracsPy-core` `plugin_sdk/camera/`)

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
  "every open sets every control" it would put auto WB and backlight 1 back between sessions — and every
  measurement open would then pay the full settling (§11c.11: 3 frames). With IDLE the measurement open finds the
  camera already in its target state and settles at frame 0. The dev capture view uses MEASUREMENT with no plugin;
  the legacy SpectralJob uses CALIBRATION.
- ⭐ **Backlight (Edwin's question) — yes:** the ELP ships with backlight compensation **on** (1), an in-camera
  brightness correction that reacts to the scene, so it would change the frame between reference and sample.
  MEASUREMENT and IDLE turn it **off**; CALIBRATION keeps the device default. Same pattern for white balance.
- ⚠ **Calibration changes once (D12):** today a Linux calibration open does not reset backlight, so calibrations
  authored after a measurement session ran with backlight **0** left in the camera; the CALIBRATION profile sets
  **1**. ⇒ after CS2 the ELP calibration is re-checked once (ROI, peak positions) on the rig.

### 3.4 Device defaults — where they come from, who can read them

- **Source:** the camera's firmware. Every UVC control answers `GET_DEF`; Linux `uvcvideo` returns it as
  `VIDIOC_QUERYCTRL.default`, Windows `usbvideo.sys` as `GetRange(..., pDefault, ...)`. Proven equal on both
  OSes for the ELP. **Nothing is stored in code or DB** — only the control names (§3.1) are code.
- **Utility:** `CaptureBackend.readDeviceDefaults() -> CameraSettings` (defaults + ranges + steps + menus),
  read-only, no stream needed. Reached by other code through the video thread (as `readCameraSettings` is today) and
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
  end** is — exactly the moments `__logCameraSettings` already logs (`CapturePanel.py:992`); the end snapshot catches
  drift over a minutes-long monitored sample.
- **`setExposure` reads back too** (D3): the open's refusal stays an open-time rule; a later change that does not
  read back as requested is logged ⛔ and lands in the snapshot — it is not silently trusted.
- **Where it lives (D7) — on the step, not a workflow column:** a `CameraSettingsRecordView` view-model
  (`spectracsPy-model`, `isShownInReport = False`, registered in `ViewModelFactory`), one per leg on that
  **acquisition step's `EvaluationResult`** — the precedent is the settling view (`SpectralWorkflowEngine.py:399-401`).
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
- **Virtual run (D14):** no backend is ever opened (`VideoThread.py:203`) ⇒ the record says
  `virtual — no camera controls (fileset …)`, the comparison is skipped, the PDF prints that one line.

## 5 — Applying: one writer per OS, every open, every change

- **Linux — `LinuxUvcControls.py`**, the twin of `WindowsUvcControls.py`: ioctl `QUERYCTRL` / `QUERYMENU` /
  `S_CTRL` / `G_CTRL` on the `/dev/videoN` the resolver found (safe: `SensorCaptureIndexResolver.py:77-104` returns
  the sysfs N, cv2 V4L2 opens exactly that). Rules (D6):
  - **one writer** — every cv2 control `set` goes out of `open` and `setExposure` (`CaptureBackend.py:122-147`,
    `:431-432`); cv2 keeps only format, size, buffer size, `CONVERT_RGB`;
  - **order** — `EXPOSURE_AUTO` → manual before `EXPOSURE_ABSOLUTE`; `AUTO_WHITE_BALANCE` off before the
    temperature; never write an `INACTIVE`-flagged control;
  - menus through `QUERYMENU`; node opened `O_RDWR`; applied again after `__reopenUnforced`.
- **Windows:** `planControls` becomes the generic resolve; `WindowsUvcControls` keeps its COM side and gains the
  **exposure set natively** (`IAMCameraControl.Set`) with the V4L2→log₂ converter, used by `open` **and**
  `setExposure` — the AE sweep on win32 pushes V4L2 numbers through cv2 MSMF today (`:430`). ⇒ CS3 and the
  converter are one phase (D4), or every Windows measurement is refused on `requested 90 vs applied −8`.
- **Proof, both OSes:** a MEASUREMENT open whose read-back does not match *requested* on any active control is
  **refused** (Q4: image controls too). CALIBRATION and IDLE warn.
- **Settling hold-back (5 frames, Edwin)** — owned by `VideoThread`, **before** `videoThreadSignal` is emitted, so
  `CapturePanel.__latestImage` never sees them (D13); after an open and after every WB/exposure change except the AE
  sweep's own probes (they already drain ~1.8 s). `heldBackFrames` per leg = "since the last change before this
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
  ⇒ **revised proposal: no extra flag.** The override itself is already explicit code
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
ACQUISITION group(s), merge the steps' `CameraSettingsRecordView`s into **one `TableView` "Camera settings"**. The
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
auto-advance lands on. ⇒ follow the **"Settling" precedent**: an **inner tab "Camera"** on each role page of
`CapturePanel` (beside Spectrum / Image / Settling, `CapturePanel.py:224-225, 1239`), showing that leg's snapshot with
⛔ on mismatch with the other leg. ⚠ Edwin's Q5 "a tab of Spectral step" — re-confirm on this basis (§8).

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
| Q8 | may a plugin switch an auto loop on in a measurement? | **revised proposal (§6.1):** yes, no extra flag — the explicit override is accepted, recorded, and badged ⛔ in the PDF and the Camera tab. Awaits Edwin |
| — | IDLE profile for the warm-keeper (D1) | proposal in §3.3 — speaks for itself, flagged so it is not a surprise |

## 9 — Phases (replace W1.4b-controls, W1.5 and W1.5b in SPEC_windows_build.md §12)

| phase | what | where | depends on | done when |
|---|---|---|---|---|
| CS0 | VM probe: VideoProcAmp 6, 10–13 + CameraControl 19 (power line, dynamic framerate, colour enable) | VM, probe | — | §3.1 Windows column final |
| CS1 | `CameraControl`, `CameraSettings` (plain-string JSON), `resolve` (3 profiles, clamp + step snap, skipped, inactive) | -core | — | unit tests: precedence, clamp/snap, skipped, inactive, JSON round-trip |
| CS2 | `LinuxUvcControls` + `readDeviceDefaults()`; `open(profile=…)` applies + reads back; one writer (cv2 sets out); `setExposure` via ioctl + read-back; refuse rule; openers pass their profile (incl. IDLE warm-keeper) | Py | CS1 | fake-ioctl tests; existing fake-cv2 tests rewritten; rig: read-back == §11c.11 table; calibration re-check (D12) |
| CS3 | Windows: `planControls` → `resolve`; **exposure set natively + V4L2→log₂ converter in `open` and `setExposure`** (old W1.5); same refusal rules | Py | CS0, CS1 | W1.6 tests green + converter + precedence tests; VM: "90 → −7 (7.8 ms)" |
| CS4 | plugin `cameraSettings(deviceDefaults)` (dict or `CameraSettings`, base `None`), `exposure` compat, exposure source drives the AE checkbox, `WHITE_BALANCE_KELVIN` constant goes (old W1.5b; DevSpectralPlugin declares exposure + WB, Q7); auto-loop override recorded + badged (Q8) | -core, Py, plugins | CS2, CS3 | DevSpectralPlugin declares; old signed row still works; plugin_sdk doc on units |
| CS5 | settling hold-back (5) in `VideoThread` before the signal, AE probes excluded (old W1.5c) | Py | CS2, CS3 | fake frame-source test: no unsettled frame reaches a burst |
| CS6 | `CameraOpenRecord` + `CameraLegSnapshot` → `CameraSettingsRecordView` on the step's `EvaluationResult`; leg start/end snapshots; re-measure replaces (incl. the settling-view gap); leg comparison; virtual record; `exposureApplied` derived | -model, Py | CS4, CS5 | round-trip via `ViewModelFactory` + `report_reconstruct.py`; re-opened run keeps it; `d2r_all_runs.py` header unchanged |
| CS7 | PDF: -core builder merges the records after ACQUISITION into one `TableView`; split on mismatch; virtual line | -core | CS6 | PDF shows the table; mismatch + virtual rendered; LIMS JSON rebuild |
| CS8 | GUI inner tab "Camera" per role page (per Q5 re-confirm) | Py | CS6 | click-through: filled after the reference leg; ⛔ on a forced mismatch |
| CS9 | Windows build re-run (`buildWindows.sh`, comtypes-only rule for any new KS code) → then W1.7 click-through | VM | CS3–CS8 | VERIFY ok |

Order rationale: the model first (CS1) so both backends apply the *same* resolution; CS3 carries the exposure
converter or Windows refuses every measurement (D4); the plugin seam (CS4) only once both backends obey it; the
record (CS6) only once it records something true on both OSes and the hold-back exists.

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
