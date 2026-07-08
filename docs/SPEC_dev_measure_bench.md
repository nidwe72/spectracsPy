# SPEC — Dev Measurement Bench ("Swiss knife")

Status: **IMPLEMENTED + click-through verified on the real ELP camera (2026-07-08)** — full bench walk-through
(acquire reference + sample → transmission + absorption). P0–P6 + P-seed done; P7 optional/not done.
Audience: **master** users only (gated under the Settings → Development group box).

## 0. As-built — fixes that came out of the real-hardware click-through

The bench itself worked as designed; driving it on the ELP surfaced (and fixed) gaps in the *shared*
calibration/setup code it depends on:

- **Auto-exposure in calibration authoring.** The calibration wizard (ROI/Hough + peak-detection) fired a
  one-shot 50-frame burst with no device-id and no exposure → bloomed capture → Hough + peak detection
  failed. Added a reusable **`AutoExposureCaptureHelper`** (live pre-pass → `AutoExposureLogicModule`, with
  status-bar progress) called before both bursts; real cameras only.
- **Green doublet resolved.** (a) `SmoothSpectrumLogicModule` parameterized (the 7×/window-10 savgol merged
  the ~4 nm doublet); calibration now smooths lightly (the 50-frame mean already denoises). (b) 6th anchor
  `MERCURY_MANGO_GREEN_LEFT` (542.4) via a best-effort local search left of the dominant green; skips if
  unresolved.
- **ROI left bound catches blue lines.** `SpectrometerRegionOfInterestLogicModule` now uses the brightest
  *channel* (max r,g,b) over a small vertical window instead of `qGray` (which under-weights blue), so a
  visible blue line is no longer clipped out of the ROI.
- **Active profile freshness.** `ActiveSpectrometerProfileLogicModule` re-fetches the calibrated profile via
  the server **RPC** (`resolveInstrumentBySerial`) — Save persists on the server and never refreshes the
  in-memory `ApplicationSettings`; the bench re-installs it on open so a just-authored calibration is seen.
- **Missing import** of `SpectrometerSensorUtil` in the bench (crashed `__startRun`); auto-exposure moved
  off `showEvent` onto the Capture click (nested-loop-in-showEvent corrupted the stream thread).

## 1. Purpose

A generic, real-camera measurement bench for the master user. It runs the *same real
measurement* an end-user plugin runs for a specific use case (e.g. pumpkin oil) — capture a
reference, capture a sample, compute transmission and absorption — **without** any use-case
evaluation/verdict. It is the real-world thing, minus the use-case layer on top.

It is deliberately the *generic sibling* of the end-user plugin wizard. The plugin drives a
broader, use-case-specific set of steps (metadata form, colour target, verdict, publishing); the
bench stops after absorption and shows the master the intermediate artifacts so they can judge —
by eye and by plot — whether a capture is factually sound. It is the tool a master reaches for
*before/while authoring* a use-case plugin.

## 2. Relationship to the plugin/engine architecture

The bench is a faithful mirror of the production pipeline — it reuses the real seams:

| Concern                     | Owner                                                        |
|-----------------------------|-------------------------------------------------------------|
| *What* to measure           | `DevSpectralPlugin` (roles `REFERENCE`+`SAMPLE`)            |
| *What* processing to run    | `DevSpectralPlugin.processing` → `MeanOp → TransmissionOp → AbsorptionOp` |
| Real capture (frames)       | **The view** (Qt `VideoThread` preview + exposure/auto-exposure) |
| Pixel→spectrum extraction   | `ImageSpectrumAcquisitionLogicModule` (shared, per plugin)  |
| px↔nm calibration           | The master's **pre-existing `SpectrometerProfile` (Spectrum setup)** — consumed, not created |
| Wizard shell + plots        | Reuse `WizardViewModule` building blocks (`StepBarWidget`, `SpectrumPlotWidget`, `PageWidget`) |

The plugin never touches pixels. It only declares roles/frame-counts and the op chain — exactly
like `PumpkinOilPlugin`, minus `evaluation`/`metadata`.

### `DevSpectralPlugin`

- Standalone `SpectralPlugin` subclass. **Not** subclassed or shared by any other plugin.
- `acquisition` → declares `REFERENCE` + `SAMPLE` steps (frames configurable, e.g. 20).
- `processing` → `MeanOp → TransmissionOp → AbsorptionOp`; declares `SpectrumPlotView` steps for
  Spectra (ref+sample overlay), Transmission and Absorption.
- `evaluation`, `metadata`, `publishing` → not implemented / inherited `pass` → auto-skipped.

### Transient binding — only the plugin is injected

End-user plugins resolve from the logged-in user's binding
(`CurrentUserSession().getPluginCodeRef()` → `WizardViewModule.__startNew` → `importPlugin`). The
bench does **not** touch that binding and does **not** register a codeRef. It news the plugin up
and hands it to the engine constructor (which already accepts any plugin instance):

```
plugin   = DevSpectralPlugin()              # transient — no session, no codeRef
engine   = SpectralWorkflowEngine(plugin)   # ctor already takes a plugin directly
workflow = engine.getWorkflow()
plugin.acquisition(workflow)                # declares REFERENCE + SAMPLE
# --- the VIEW owns real capture (see §3): frames → per-frame extraction → fill step containers
plugin.processing(workflow)                 # real Mean → Transmission → Absorption
# read the processing SpectrumPlotView steps → render into the wizard tabs
```

**Calibration is NOT injected transiently.** It comes from the master's existing
`SpectrometerProfile` (their configured Spectrum setup), read from the app context by the
extraction module. The bench only *requires* one to be present (see §4 precondition).

## 3. Why the view owns capture

`SpectralWorkflowEngine.captureAcquisitionStep`/`__capture` is **virtual-device only**: it reads a
*static image* per role (`virtualSettings.getImage(role)`) and re-extracts it N times. It
deliberately avoids the Qt `VideoThread` to stay headless-safe. Real capture with
exposure/auto-exposure lives solely in `DevCaptureVideoThread` / `VideoViewModule`. So the bench's
acquisition panel:

1. Streams a **live preview** (`VideoViewModule`; optionally a live spectrum via
   `SpectrumVideoThread`, which already runs each frame through `ImageSpectrumAcquisitionLogicModule`).
2. On **Capture**, grabs N frames, runs each through `ImageSpectrumAcquisitionLogicModule` (using
   the installed profile), accumulates into the step's spectrum, and sets the step container —
   i.e. it replicates what `captureAcquisitionStep` does, but sourced from the real camera.

Capture never routes through the engine's virtual path.

## 4. Measurement flow

**Precondition:** a calibrated `SpectrometerProfile` (Spectrum setup) must be installed. If absent,
the bench shows an **in-window inline dialog** (no native window — per the GUI-refinements guide)
stating that calibration has to be set up first, with an action to the instrument-setup flow.

**Camera identity:** the bench uses the **device bound to the installed setup** (the ROI + px↔nm
polynomial are device/optics-specific). It does not offer a free camera picker; if the resolved
device differs from the calibrated one, warn.

1. **Capture REFERENCE**: live preview; auto-expose if enabled → **lock the exposure value**;
   Capture N frames → per-frame extraction → `MeanOp`; **retain one representative frame** (e.g.
   frame N/2) as a `QImage` for the processing raster tab.
2. **Capture SAMPLE**: N frames at the **locked** exposure (auto-expose disabled for the sample);
   retain a representative frame.
3. **Process** (on Next into the PROCESSING phase): `plugin.processing(workflow)` →
   `MeanOp` reduces the per-frame spectra to a mean per role, `TransmissionOp` → `T = S/R`,
   `AbsorptionOp` → `A = −log10(S/R)`.
4. **Display**: render the processing `SpectrumPlotView` steps into the wizard tabs, plus the two
   **view-injected raster tabs** built from the retained frames + the ROI (§7).

**Re-capture:** re-capturing the reference re-runs auto-expose and re-locks the exposure; if a
sample was already captured, it is invalidated (its exposure no longer matches) and must be redone.

### Exposure — correctness, not polish

`T = S/R` is only valid when reference and sample share the same exposure/gain. Auto-expose on the
reference, **lock** the value, reuse it for the sample. Show the locked value; let the master
override it.

### Where the mean is taken

**`MeanOp`** — extract a spectrum per frame, then mean the *spectra* (matches the production
pipeline exactly). The displayed raster (§7) is a single **preview-only** representative frame; it
is a human sanity-check, not the data source.

## 5. Rubber-duck walkthrough (what it validated, and the reflectance note)

Master points the Swiss knife at a sample and runs the wizard:

- **Calibration is a precondition, not a step.** For a real device the extraction module reads the
  master's installed `SpectrometerProfile`. The bench does not calibrate; it requires a calibrated
  setup and guards if missing. (The engine's `__ensureCalibration` → `PlaygroundCalibrationLogicModule`
  path is never reached, because the bench doesn't use the engine's virtual capture and a real
  installed polynomial stands on its own.)
- **Absorption vs reflectance (the duck).** Absorption is derived from *transmission*:
  `A = −log10(S/R)`, where R = light **through** a blank and S = light **through** the sample —
  *transmission geometry* (lamp → through sample → camera). It is meaningful only for
  **translucent** samples (liquid in a cuvette, thin film). An **opaque** object (a rubber duck)
  would need **reflectance** — light bounced off the surface (lamp + camera same side), a different
  geometry and math the current op chain does not implement. **Scope:** the sample sits **between
  the bulb and the camera** (transmission geometry); absorption via transmission only; translucent
  samples; the view states this. Reflectance = future feature, out of scope for now.

## 6. Latent cleanup (not a prerequisite) — decouple calibration from Playground

`SpectralWorkflowEngine.__ensureCalibration()` imports and calls
`PlaygroundCalibrationLogicModule().calibrateImage(...)` — the *production* engine depends on
*dev/playground* code. The bench does not hit this path (it consumes an installed profile), so this
is **not** a prerequisite. But it remains worth fixing: extract the calibration heuristic into a
stable `logic/spectral/calibration/SpectrometerCalibrationLogicModule` and make Playground a
consumer. Tracked here, sequenced independently.

## 7. View — a phase/step wizard (mirrors `WizardViewModule`)

The bench reuses the end-user wizard shell so it *feels* like a real run:

- `StepBarWidget` chevrons across the top = the phase sequence (**Acquisition ▸ Processing**;
  Evaluation/Metadata/Publishing create 0 steps → auto-skipped, no chevron/tab).
- A `QTabWidget` where the current phase's **steps become tabs**.
- A Back / Cancel / Next footer (`createNavigationGroupBox`). Runs are ephemeral (no persistence),
  so at the terminal PROCESSING phase Next becomes **Close** (returns to Settings) — there is no
  Save.

Difference from the end-user wizard: the ACQUISITION step panel is **not** a bare "Measure" button.
It embeds the live camera preview + exposure controls from `DevCaptureViewModule`.

Tabs by phase:

- **ACQUISITION** → `Reference`, `Sample` — each is a **single panel**. Before Capture it shows the
  **live camera stream** (+ exposure slider, auto-expose, frames selector, Capture button).
  During/after Capture the *same* panel shows the **per-frame spectra overlaid in gray** with the
  **mean spectrum on top in green**. No raster is shown in this phase.
- **PROCESSING** → `Reference raster`, `Sample raster` (**view-injected** — the plugin is Qt-free
  and cannot carry `QImage`s; built from the retained representative frames + the profile ROI: raw
  frame with everything **outside the ROI blacked out** + the **cropped ROI raster**), then the
  plugin's `SpectrumPlotView` steps: `Spectra` (ref+sample overlaid), `Transmission` (`T = S/R`),
  `Absorption` (`A = −log10(S/R)`).

### Build approach

Reuse the leaf widgets (`StepBarWidget`, `SpectrumPlotWidget`, `PageWidget` nav helpers) and the
engine + `DevSpectralPlugin`. Do **not** fork `WizardViewModule` (its plugin resolution and
acquisition panel are private + session-hardwired). Two options:
- **(A, recommended for v1)** New `DevMeasurementBenchViewModule(PageWidget)` that assembles the
  shell from the shared widgets and supplies its own live-capture acquisition panel.
- **(B, optional follow-up)** If duplication hurts, extract a common `WizardShell` base with an
  overridable `buildAcquisitionPanel(step)` + plugin source, and have both wizards extend it.

## 8. Wireframe

ACQUISITION phase — "Reference" step tab (single panel; Sample identical). Same panel, two states:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ‹ Back    Measurement Bench (dev)                                [master only]│
│   ●━━━━━━━━━━━━━━━○        Acquisition  ▸  Processing        (StepBar chevrons)│
├──────────────────────────────────────────────────────────────────────────────┤
│  [ Reference ] [ Sample ]                         ← phase steps = tabs         │
│                                                                                │
│   BEFORE Capture                          DURING / AFTER Capture               │
│  ┌───────────────────────────┐          ┌───────────────────────────┐         │
│  │ Exposure [===|--] 78       │          │  per-frame (gray)          │         │
│  │ ☑ Auto-expose  Frames[20▾] │          │  + mean (green) on top     │         │
│  │ ┌──── live stream ───────┐ │          │ ┌───────────────────────┐ │         │
│  │ │   (camera preview)     │ │   ─────► │ │      ╱╲  ← mean (green)│ │         │
│  │ │                        │ │          │ │   ╱╲╱ ╲  ┄ frames(gray)│ │         │
│  │ └────────────────────────┘ │          │ │  ╱     ╲__            │ │         │
│  │ [ Capture reference ]      │          │ └───────────────────────┘ │         │
│  └───────────────────────────┘          │ status: ✓ (20 frames)      │         │
│                                          └───────────────────────────┘         │
│                                              [ Cancel ]            [ Next → ]   │
└────────────────────────────────────────────────────────────────────────────┘
```

PROCESSING phase (after Next; runs `plugin.processing`):

```
│   ●━━━━━━━━━━━━━━━●        Acquisition  ▸  Processing                          │
│  [ Reference raster ] [ Sample raster ] [ Spectra ] [ Transmission ] [ Absorp.]│
│ ┌── Reference raster tab ──────────────┐   ┌── Absorption tab ───────────────┐ │
│ │ ┌ raw, non-ROI black ┐┌ ROI crop ┐   │   │ A(λ) = −log10(S/R)              │ │
│ │ │▓░▒▓██▓▒░░▓▓▓▓▓▓▓▓▓▓▓││░▒▓██▓▒░  │   │   │ ┌────────────────────────────┐ │ │
│ │ └────────────────────┘└──────────┘   │   │ │   pyqtgraph absorption plot │ │ │
│ └──────────────────────────────────────┘   │ └────────────────────────────┘ │ │
│                                             └─────────────────────────────────┘ │
```

## 9. Implementation phases

Listed in build order. Labels are stable (referenced by the D-/N-notes); the leading number is the
build sequence.

| Seq | # | Phase | Goal | Key files | Depends on |
|-----|---|-------|------|-----------|------------|
| 1 | P0 | Plot overlay support | Extend `SpectrumPlotWidget` with a multi-curve overlay (`clear=False` / `addTrace`) — N3; used by P2 + P5 | `SpectrumPlotWidget` | — |
| 2 | P1 | DevSpectralPlugin | Roles REFERENCE+SAMPLE; processing `Mean→Transmission→Absorption` + `SpectrumPlotView` steps for Spectra/Transmission/Absorption; no eval/metadata/publishing | `logic/spectral/plugin/dev/DevSpectralPlugin` (new) | — |
| 3 | P-seed | `masterUserExakta` seed | Add master user + ELP `SpectrometerSetup` (serial, EXAKTA sensor 32e4/8830); calibration authored once via existing flow using auto-exposure (D6); login installs active profile into `ApplicationSettings` (§11) | `UserSeedLogicModule`, `PersistSpectrometerSetupLogicModule`, login path | — (resolves D1/N1) |
| 4 | P3 | Calibration precondition + camera source | Require a *real* installed `SpectrometerProfile` with `spectrometer.spectrometerSensor` populated (auto-calibrated bare profiles carry no device id — N1); inline dialog if absent (D1); resolve camera via `SensorCaptureIndexResolver(sensor)` | app context, `SensorCaptureIndexResolver`, instrument-setup nav | P-seed |
| 5 | P2 | Live-capture acquisition panel | Single panel: DevCapture live preview + exposure/auto-expose + frames dropdown (D2); after Capture, per-frame spectra (gray) + mean (green) via overlay; lock exposure on ref, reuse for sample | `DevCaptureViewModule` parts, `VideoViewModule`/`SpectrumVideoThread`, `AutoExposureLogicModule`, `SpectrumPlotWidget` | P0, P3 |
| 6 | P4 | Capture → extraction wiring | N frames → `ImageSpectrumAcquisitionLogicModule` per frame → fill acquisition step containers; **retain 1 representative frame per role**; then `plugin.processing`; re-capture invalidation (N2) | bench view, `ImageSpectrumAcquisitionLogicModule`, P1 | P1, P2 |
| 7 | P5 | Wizard view + tabs | `DevMeasurementBenchViewModule`: StepBar + step-tabs + nav; acquisition tabs (single panel); processing tabs = **view-injected** raster tabs (ROI-black + crop) + plugin plot steps (Spectra overlay uses P0); terminal Next = Close (D4) | new view + `StepBarWidget`, `SpectrumPlotWidget`, `PageWidget` | P0, P4 |
| 8 | P6 | Registration / nav | Master-gated dev button + stack index + nav title + Back | `MainViewModule`, `NavigationHandlerLogicModule`, `SettingsViewModule` | P5 |
| — | P7 (opt) | Calibration decouple | Latent cleanup from §6 — not blocking, detached | `SpectrometerCalibrationLogicModule` (new), engine, Playground | — |

## 10. Decisions (resolved)

- **D1 — no calibrated setup:** show an **in-window inline dialog** ("calibration must be set up
  first", with an action to instrument setup). Not a native window (GUI-refinements guide).
- **D2 — frame count:** small **dropdown, default 20** (e.g. 10 / 20 / 50).
- **D3 — transmission floor:** keep the **op default** for `referenceFloorFraction`; surface a
  control later only if plots look noisy.
- **D4 — persistence:** **ephemeral** (v1 — dev tool). No saved runs; terminal Next = Close.
- **D5 — reflectance:** **out of scope** (future). Sample sits between bulb and camera
  (transmission geometry); absorption via transmission only.
- **D6 — ELP calibration source:** **author once** via the existing master flow (persisted); the
  calibration capture uses **auto-exposure** (not the static 78). See §11.

### Remaining minor design notes

- **N1 — camera source (VERIFIED — needs care):** `SpectrometerProfile` and
  `SpectrometerCalibrationProfile` carry **no** VID/PID/device-path directly. Camera identity is
  only reachable via the relationship `SpectrometerProfile.spectrometer → Spectrometer.spectrometerSensor
  → SpectrometerSensor.vendorId (VID) / .modelId (PID)`, and `SensorCaptureIndexResolver` keys on
  exactly those same fields — so they *agree* **when the relationship is populated**. But the
  engine's auto-calibration shortcut (`__ensureCalibration`) builds a bare `SpectrometerProfile()`
  with no `spectrometer`/`serial` → **zero device identity**. So the bench must require a *real*
  instrument-setup profile (sensor populated), not an auto-calibrated bare one, and resolve the
  camera through `spectrometer.spectrometerSensor`. No new model field needed if that path is used.
- **N2 — re-capture invalidation:** re-capturing the reference re-locks exposure and invalidates an
  already-captured sample (must be redone).
- **N3 — plot overlay (VERIFIED — needs new code):** `SpectrumPlotWidget.plotSpectrum(spectrum,
  title, color)` calls `self.clear()` first → **single self-clearing curve**. The acquisition panel
  (gray per-frame traces + green mean) *and* the `Spectra` overlay (ref+sample) both need multiple
  curves. Add an overlay capability — a `clear=False` flag or an `addTrace(spectrum, color)` method
  (per-curve pen already works via `pg.mkPen`). Shared by P2 and P5.

## 11. Seed data — `masterUserExakta` + ELP setup (resolves N1)

Grounded in the seed mechanism (`UserSeedLogicModule.seed()`, run idempotently on every server
start from `SpectracsPyServer.__init__`). What exists vs. what the bench needs:

**Already present:**
- Master-user seed pattern: `SEED_USERS` holds `("masterUser", "masterUser", MASTER_USER)`.
  Add a peer `("masterUserExakta", "masterUserExakta", MASTER_USER)`.
- ELP sensor in the catalog: `SpectrometerSensorUtil.getSpectrometerSensors()` — codeName `EXAKTA`,
  **`vendorId="32e4"`, `modelId="8830"`**, `isVirtual=False`. `SensorCaptureIndexResolver` keys on
  these same fields → camera resolves correctly (N1 satisfied via `spectrometer.spectrometerSensor`).
- ELP capture setting: `__CAPTURE_SETTINGS_BY_HARDWARE_ID["32e4_8830"] = calibrationExposure=78`.
- ELP instrument seed pattern: `__seedElpInstrument()` creates `elpUser` + serial `"ELP-0001"` via
  `PersistSpectrometerSetupLogicModule.getOrCreateInstrument(serial, spectrometerId, pluginId)`.

**Binding is via serial, not a user column** (correction to earlier assumption): `AppUser.registeredSerial`
→ `SpectrometerSetup` → plugin. `CurrentUserSession.getPluginCodeRef()` is filled at **login** by
`InstrumentLogicModule.resolveBundle(registeredSerial)` (returns `pluginCodeRef`, device, calibration).
The bench's transient `DevSpectralPlugin()` is independent of this — but the seed user's serial still
governs whether login resolves a **calibration** at all.

**The gap that blocks the bench precondition:** `__seedElpInstrument` creates an **empty**
`SpectrometerCalibrationProfile` (no ROI, no `interpolationCoefficientA–D`). `resolveBundle`'s guard
(`cal.interpolationCoefficientA is not None`) then returns `calibration=None` → the bench's
"calibrated setup present" precondition (D1) **fails**. And there is **no hard-coded ELP coefficient
set anywhere** — real ROI + A–D are produced at runtime by the calibration algorithm and saved via
`InstrumentAuthoringLogicModule.saveProfile`.

**D6 — resolved: (a) author once.** `masterUserExakta` runs the existing master
calibration/authoring flow one time; the algorithm produces real ROI + A–D and persists them, so
the numbers match the physical optics (no fake constants, no seeded coefficients). The seed only
ships the scaffolding (user + ELP `SpectrometerSetup` + serial + empty calibration profile).
**Detail:** the calibration capture uses the **auto-exposure** functionality
(`AutoExposureLogicModule.findExposure(...)`) to determine the CFL exposure, rather than relying on
the static `calibrationExposure=78` (78 becomes a fallback / starting point).
*(Rejected: (b) seed measured constants — no measured set exists yet; (c) placeholders — wrong
wavelengths.)*

**Active-profile wiring (the "in-memory vs DB" point).** There are two separate places calibration
lives: (1) **persisted in the DB** per serial (durable), and (2) **loaded into memory** at runtime
in `ApplicationSettings.getSpectrometerProfile()` — and the bench's extraction reads only (2). So
even after `masterUserExakta` has authored + saved the calibration to the DB, the bench won't see it
unless that profile is *loaded into memory* for the running session. Requirement: **logging in as
`masterUserExakta` must install the resolved calibrated profile into `ApplicationSettings`**, so the
bench opens ready without a manual visit to the Spectrometer-setup screen. (Confirm whether login
already does this; if not, it's a small wire-up. Alternative: seed an
`ApplicationConfigToSpectrometerProfile(isDefault=True)`.)

*(Phase `P-seed` is listed in the build-ordered table in §9.)*
```
