# SPEC — Plugin-driven GUI convergence (Milestone 1)

Status: **IMPLEMENTED (2026-07-10)** — awaits on-device click-through of the Pumpkin-on-bench path. Source: Edwin.
**Milestone 1**; the PDF report ([`SPEC_bench_pdf_export.md`](SPEC_bench_pdf_export.md)) is **Milestone 2**, built on
top of it.

## Status — what landed (2026-07-10)

All phases **P0–P7 implemented + the wizard converged**; app imports clean, 6 tests pass, evaluation/processing verified
on the real bench.
- **P0** ✅ view-models re-homed `model.spectral.evaluation → model.spectral.plugin.view` (façade unchanged).
- **P1** ✅ visitor seam (`WorkflowItemVisitor` + `dispatchItem` + `QtWorkflowRenderer`; `EvaluationResultRenderer` = façade).
- **P2** ✅ `SpectrumPlotView` (traces + bands + **markers**), new `SpectrumCaptureView`; real plot/image visits.
- **P3** ✅ `WorkflowPhaseRenderer` (steps→tabs, headless-skip, capture-path branch + `decorateCapturePanel` hook).
- **P4** ✅ EVALUATION = plugin-declared **Metrics + Spectrum** steps (band-marked absorption + Q-peak marker).
- **P5** ✅ PROCESSING rendered generically (Spectra overlay = multi-trace). Raster tabs stay host dev chrome.
- **P6** ✅ **wording only** — acquisition tab labels + Measure text come from the plugin's steps/`CaptureView`
  (Pumpkin shows its own wording); the camera/exposure/ROI/§15-reparenting flow is unchanged (host, by design).
- **P7** ✅ master-only **bench plugin selector** (Dev / Pumpkin), decoupled from `SpectrometerSetup`.
- **Wizard** ✅ `WizardViewModule.__computedPanel` routes through `WorkflowPhaseRenderer`.

**Also fixed (pre-existing, surfaced by the click-through):** V4L2 mid-stream exposure (`CaptureBackend.setExposure`
re-asserts manual mode) and the tall-frame raster display (`ScaledImageLabel` fits both width AND height). **Bench UX:**
the footer **Back** button is hidden on the first phase (ACQUISITION) — use Cancel to leave.

**Deferred (not functional gaps):** full P6 capture-panel migration (only code-dedup; the generic capture path is
unused for the bench); `CaptureView.prompt` has no display home yet (S7 removed the hint label), so the declared prompt
is not shown; the pre-existing `Next →`/`Next ▶` nav-glyph test assertion.

> **P6 is now the ▶ NEXT plugin-platform item (see ROADMAP).** Since this was written, an **acquisition-guidance** layer
> (coach line + amber next-action cue) was built that gives `CaptureView.prompt` a home — see
> [`SPEC_acquisition_guidance.md`](SPEC_acquisition_guidance.md). It is implemented in **both** hosts (Decision B):
> `WizardViewModule` and `DevMeasurementBenchViewModule`, with the derive/coach/highlight logic **mirrored** (~90 lines)
> because their acquisition panels are still separate. **The main prize of P6 is now deduplication:** once ACQUISITION
> routes through this shared capture path, collapse the two mirrored guidance implementations into one. Edwin flagged a
> "tight discussion" before starting P6.

Grounded in the verified architecture: `plugin_sdk/base/SpectralPlugin.py` (per-phase hooks), the Qt-free view-models
in `spectracsPy-model/.../model/spectral/evaluation/`, the shared `view/spectral/workflow/EvaluationResultRenderer.py`,
`SpectralWorkflowEngine`, and the two hosts `DevMeasurementBenchViewModule` (dev bench) + `WizardViewModule`
(end-user measurement view).

---

## 0. The rule that governs all

**The plugin drives the GUI of both the dev measurement bench and the end-user measurement view.** Both become
**thin hosts** rendering *whatever the plugin declares* — phases → steps → view-models — with **no phase, step, or tab
hardcoded per view**. The boundary that falls out of the design:

> **The plugin declares every *shell*** — structure (phases/steps/tabs), content (metrics, plots, prompts, image
> presence + labels). **The host injects only what the plugin cannot know in advance** — hardware-derived pixels and
> spectra, and the camera mechanics (live feed, burst, exposure, ROI).

---

## 1. Where we are (the divergence)

| Concern | Bench (`DevMeasurementBenchViewModule`) | Wizard (`WizardViewModule`) |
|---|---|---|
| Phase nav | `StepBarWidget` + `QStackedWidget` + Back/Next | one phase at a time, `__runHookOnce` |
| Acquisition | role step-tabs, one shared video reparented, Measure | `__acquisitionPanel(step)` + Measure |
| Processing | `__processingTabs` + raster/spectra sub-tabs (hardcoded) | `__computedPanel(step)` → `SpectrumPlotWidget` |
| Evaluation | `__evaluationTabs` **Metrics \| Spectrum** (*view-level*, not steps) | `__computedPanel` → `EvaluationResultRenderer` |
| Shared today | `EvaluationResultRenderer().render(evaluationResult)` only | same |

The evaluation view-model → Qt path is already shared; **everything else** is duplicated and hardcoded per host.

---

## 2. How it works — the render seam (prose + diagrams)

Everything the host draws funnels through **one dispatch point**, `dispatchItem(item, visitor)` — the single
`isinstance` ladder over the view-model vocabulary. A **visitor** implements one method per view-model type; each
render *target* is one visitor implementation. Today there is one target (Qt); M2 adds a second (matplotlib) against
the identical seam. Because both go through the same `dispatchItem`, **screen and PDF cannot drift**, and a new
view-model type is a **one-place change**.

**A. The render seam — one declaration, many targets**
```
   PLUGIN  (Qt-free)                  DevSpectralPlugin / PumpkinOilPlugin
   ─ acquisition()/processing()/evaluation() build & attach view-models
                     │
                     ▼
   WORKFLOW MODEL  (Qt-free plain data)
   Workflow ─► Phase ─► Step
                        ├─ evaluationResult = [ LabelView, MetricFieldView,
                        │                        ColorSwatchView, VerdictView,
                        │                        SpectrumPlotView(traces[], bands[]) ]
                        └─ _view = SpectrumPlotView | SpectrumCaptureView | CaptureView
                     │
                     │  host reads the view-models
                     ▼
        ┌─────────────────────────────────────────────┐
        │   dispatchItem(item, visitor)               │  ◄── THE SEAM: the single
        │   (the ONE isinstance ladder, defined once) │       isinstance ladder
        └─────────────────────────────────────────────┘
                     │  calls one method per type
        ┌────────────┼──────────────┬───────────────┬──────────────────┐
        ▼            ▼              ▼               ▼                  ▼
   visitLabel  visitMetricField  visitSpectrumPlot  visitSpectrumCapture ...
        └────────────── interface: WorkflowItemVisitor ──────────────┘
                     ▲                                   ▲
        implemented by                                   implemented by
   ┌───────────────────────┐                    ┌──────────────────────────┐
   │ QtWorkflowRenderer     │                    │ MatplotlibRenderer  (M2) │
   │  → QWidget  (screen)   │                    │  → figure (Report + PDF) │
   └───────────────────────┘                    └──────────────────────────┘
```

**B. How the host walks a phase — and where `CaptureView` branches off**

Passive content is *stateless* (data → widget), so it rides the visitor. A `CaptureView` is *interactive* (it needs
the live sensor, a Measure button, per-frame progress, and the `step`), so it **cannot** ride the pure visitor — the
host's **capture path** consumes it for its shell params and owns the machinery.
```
   WorkflowPhaseRenderer.render(phase) ─────────────► QTabWidget (one tab per step)
   │
   for step in phase.getSteps():
   │
   ├─ step has a CaptureView?  ──YES──►  HOST CAPTURE PATH   (NOT the visitor)
   │                                     live video ─ [Measure] ─► engine.captureAcquisitionStep(step)
   │                                     per-frame progress
   │                                     decorateCapturePanel(panel, step)  ◄── bench: exposure/ROI
   │                                                                            wizard: no-op (empty slot)
   │
   └─ else (passive content) ──────────►  for vm in step.viewModels():
                                              host pre-fills any host-owned data (SpectrumCaptureView.image)
                                              dispatchItem(vm, QtWorkflowRenderer) ─► tab body
   (headless step → no view-models → no tab)
```
`decorateCapturePanel(panel, step)` is the **dev-chrome extension hook**: a method that does nothing by default; the
bench overrides it to inject exposure / auto-exposure / ROI controls; the wizard leaves it empty. It lets one shared
panel serve both hosts without forking.

**C. Convergence — two hosts, one renderer (and where M2 reuses it)**
```
   DevMeasurementBenchViewModule                 WizardViewModule
   ─ nav: StepBar + stack + Back/Next            ─ nav: linear, phase-at-a-time
   ─ dev chrome: exposure / ROI                  ─ (no dev chrome)
   ─ camera: one shared widget, reparented       ─ camera: per-step Measure
              │                                             │
              └────────────────────┬────────────────────────┘
                                   ▼
                     WorkflowPhaseRenderer            ◄── SHARED (the content path)
                                   │
                          dispatchItem(...)           ◄── SHARED seam
                                   │
                  ┌────────────────┴───────────────┐
                  ▼                                ▼
          QtWorkflowRenderer              MatplotlibRenderer  (M2: Report tab + PDF)
             (screen, both hosts)            (same seam, different target)
```
"Converge" means the two hosts **share the content path** (`WorkflowPhaseRenderer` + the seam) but keep their own
**navigation, camera handling, and dev chrome** — the plugin drives *what*, the host still owns *how the camera
behaves*. Not identical files; identical content path.

---

## 3. Plugin model vocabulary

All plugin-facing view-models are **Qt-free plain data**. Plugins import them only through the `plugin_sdk` facade, so
the internal package can be re-homed transparently (see **Namespace** below).

| Model | Plugin sets | Host sets | Renders as | Path | Phase(s) |
|---|---|---|---|---|---|
| `EvaluationResult` | ordered list of items | — | container (walked) | — | any |
| `LabelView(text)` | text | — | caption | `visitLabel` | any |
| `MetricFieldView(label, value, tooltip, style, color)` **¶** | all | — | label chip + read-only field (or swatch when `color` set) | `visitMetricField` | evaluation |
| `MetricFieldViewStyle(labelBold)` | all | — | bold label | (on metric) | evaluation |
| `ColorSwatchView(rgb, label)` | all | — | filled swatch | `visitColorSwatch` | evaluation |
| `VerdictView(roastState, hueDegrees)` | all | — | headline | `visitVerdict` | evaluation |
| `SpectrumPlotView(traces[], bands[], title)` **†** | traces, bands, title | (spectra already in model) | plot (curves + band overlays) | `visitSpectrumPlot` | processing, evaluation |
| `SpectrumCaptureView(caption, cropped, roiOverlay)` **‡** | caption, `cropped`, `roiOverlay`, *its presence = "show it"* | **`image`** (masked/cropped frame) | scaled raster image | `visitSpectrumCapture` | acquisition, processing |
| `CaptureView(prompt, captureLabel, showLivePreview, geometry, showFramesControl, showExposureControls)` **‡** | shell params + dev-chrome flags | live video, burst, progress | capture panel | **host capture path** (not visitor) | acquisition |

**¶ extended** (2026-07-13): `MetricFieldView` gained an optional `color` (a plain `(r,g,b)` 0-255 tuple). When set,
`value` is unused and the value cell renders a filled swatch at field height instead of the read-only text field — a
labeled colour row that aligns in the **same metric grid** as the text metrics (the shape is identical; only the value
cell differs, so it needs no new view-model type and no accumulator change). The plugin computes the colour (e.g. via
`EvaluationColorUtil`). Both render targets branch inside `visitMetricField` (Qt swatch / matplotlib patch). Used by
`DevSpectralPlugin` evaluation ("color" row, no target); `PumpkinOilPlugin` keeps its `ColorSwatchView` measured/target
comparison blocks (unchanged).

**‡ extended** (M2, 2026-07-11): `CaptureView` gained `showFramesControl` / `showExposureControls` (+ fluent setters),
**hidden by default** — the plugin decides whether the bench's frame-count + exposure/auto-exposure dev chrome is
exposed (an end-user plugin wants a bare Measure button; auto-exposure still runs). `SpectrumCaptureView` gained a
report `attachmentName` and a host-set Qt-free `reportImage` for the PDF (M2, `SPEC_bench_pdf_export.md`).

**† extended** (M1, additive): today `SpectrumPlotView(spectrum, title)` = one trace, no bands; extend to
`traces=[(spectrum,label,color)]` + `bands=[(lo,hi,label)]`, keeping the single-spectrum constructor valid. Covers
both the Reference+Sample overlay ("Spectra") and the band-marked absorption plot.

**‡ new** (M1). `SpectrumCaptureView` (was "ImageView") is the captured raster the spectrum is extracted from —
plugin-declared *shell* (caption + `cropped` full-frame-vs-ROI + `roiOverlay` paint-the-ROI-rectangle), **host-filled**
`.image` (it applies the crop/overlay and injects pixels the plugin can't know in advance). The bench's *Full frame* /
*Cropped ROI* tabs become two `SpectrumCaptureView`s (`cropped=False, roiOverlay=True` and `cropped=True`); the wizard
declares none. `CaptureView` is the interactive acquisition shell (§2B).

**Deferred to M2:** `ReportView` + a per-view-model `shownInReport` flag. Nothing else is deferred on the model side.

**Namespace (M1 cleanup).** The view-models live in `sciens.spectracs.model.spectral.evaluation` — a misnomer now that
they span acquisition/processing too. Re-home them under the plugin namespace:
**`sciens.spectracs.model.spectral.plugin.view`** (Edwin) — they *are* the plugin's declared views, so grouping under
`plugin` reads cleanest. Re-exported by `plugin_sdk`; plugins import from `plugin_sdk`, so the move is **transparent to
plugin code** (facade unchanged); only internal imports update.

---

## 4. Design summary

- **Generalize step content to a view-model list.** `EvaluationResult.getItems()` is already "an ordered list of
  view-models"; give *any* step a uniform `viewModels()` (an adapter reading `evaluationResult` / `_view` /
  `container`, lighter than lifting a list onto the entity). The host renders a step by walking that list — phase-
  agnostic. Headless steps (no view-models) render no tab.
- **The visitor seam** (§2A) — `WorkflowItemVisitor` + `dispatchItem`; `QtWorkflowRenderer` implements it (today's
  `EvaluationResultRenderer` behaviour, plus real `visitSpectrumPlot`/`visitSpectrumCapture`).
- **The generic phase renderer** — `WorkflowPhaseRenderer` (steps → `QTabWidget`, S10 frame conventions), the single
  home of "steps → tabs", with the `decorateCapturePanel` hook and the capture-path branch (§2B).
- **Acquisition** stays the semi-declarative exception: plugin declares the `CaptureView` shell + role/frames; host
  owns camera + burst; bench adds dev chrome via the hook; the one-shared-camera reparenting is a bench render
  strategy, invisible to the declaration.

---

## 4b. Bench plugin selection (master affordance + M1 acceptance test)

Today the bench transiently injects `DevSpectralPlugin`, hardcoded. Add a **master-only plugin dropdown** at the top of
the bench so the master picks *which* plugin drives it (Dev Swiss-knife, PumpkinOil, any registered) — **decoupled from
the `SpectrometerSetup` binding**: the bench still uses the current calibrated setup for *capture* (hardware), but the
plugin is chosen freely and **overrides** whatever plugin a setup would reference. Selecting one re-injects it and
re-runs the workflow.

This is the **acceptance test for M1**: on a generic host, selecting PumpkinOil must render swatches+verdict and Dev
must render metrics — same host, different plugin. The dropdown reads a **`PluginRegistry`** (enumerate available
plugins) — in-app classes now, **+ DB-stored plugins** once [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md)
lands. So selection *consumes* what distribution *provides* — the registry is the join point. The selector lands with
M1 (folds into P7); the DB-plugin source of the registry is M3.

---

## 5. Implementation phases
```
┌──────┬───────────────────────────────────────────────┬────────────────────────────────┬──────────────────────────────┐
│ Phase│ Change                                         │ Files                          │ Unblocks / Verify            │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P0   │ Re-home view-models to model.spectral.plugin.  │ spectracsPy-model pkg move;    │ nice namespace. Verify:      │
│      │ view (facade unchanged) + rename ImageView.    │ plugin_sdk facade              │ plugins unchanged, imports ok│
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P1   │ Extract the render VISITOR: WorkflowItem-      │ new view/…/render/ pkg;        │ the shared seam. Regression- │
│ M1a  │ Visitor + dispatchItem + QtWorkflowRenderer    │ EvaluationResultRenderer.py    │ safe (plot branch dead).     │
│      │ (behaviour identical).                         │                                │ Verify: screenshot-diff.     │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P2   │ Extend SpectrumPlotView (traces[]+bands[]);    │ spectracsPy-model viewmodel;   │ overlay/band plots + rasters │
│      │ add SpectrumCaptureView(caption,cropped,       │ render pkg                     │ declarable. Verify: multi-   │
│      │ roiOverlay). Implement visitSpectrumPlot +     │                                │ trace, bands, cropped/ROI    │
│      │ visitSpectrumCapture.                          │                                │ image render.                │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P3   │ Generic WorkflowPhaseRenderer: steps→QTabWidget│ new WorkflowPhaseRenderer.py   │ one "steps→tabs" place.      │
│ M1b  │ (S10 frames); headless skipped; body via       │                                │ Verify: renders EVALUATION   │
│      │ visitor; decorateCapturePanel hook.            │                                │ generically.                 │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P4   │ EVALUATION as real plugin steps: Metrics +     │ DevSpectralPlugin; Pumpkin-    │ plugin-declared tabs. Verify:│
│      │ (banded) Spectrum steps via P3; drop bench     │ OilPlugin; bench view;         │ remove from plugin → tabs    │
│      │ __evaluationTabs.                              │ WizardViewModule               │ vanish.                      │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P5   │ PROCESSING via P3: Spectra(multi-trace)/T/A +  │ plugins; bench view            │ processing generic + rasters │
│      │ raster tabs as SpectrumCaptureViews; drop      │ (__processingTabs gone);       │ plugin-declared. Verify: T/A │
│      │ bench processing/raster hardcode.              │ WizardViewModule               │ + Full/Cropped render.       │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P6   │ CaptureView + host ACQUISITION path: plugin    │ spectracsPy-model CaptureView; │ acquisition plugin-driven;   │
│      │ declares shell; host wires capture + fills     │ host capture renderer; plugins;│ camera host. Verify: prompts │
│      │ SpectrumCaptureView.image; bench dev chrome    │ bench dev-chrome override      │ from plugin; dev chrome ok.  │
│      │ via decorateCapturePanel.                      │                                │                              │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P7   │ Converge hosts: both delegate ALL phase        │ DevMeasurementBenchViewModule; │ one content renderer. Verify:│
│ M1c  │ content to WorkflowPhaseRenderer; only nav +   │ WizardViewModule               │ a plugin edit hits both      │
│      │ dev chrome remain per host.                    │                                │ views identically.           │
├──────┼───────────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ P8   │ Click-through both hosts (desktop + --phone);  │ this spec                      │ CaptureView + Spectrum-      │
│      │ finalise spec.                                 │                                │ CaptureView in; shownInReport│
│      │                                                │                                │ → M2.                        │
└──────┴───────────────────────────────────────────────┴────────────────────────────────┴──────────────────────────────┘
```

## 6. Open questions
- **Step content source:** adapter reading `evaluationResult`/`_view`/`container` (lighter, proposed) vs a real
  `viewModels()` list lifted onto the step (cleaner, bigger).
- **Navigation:** keep two nav skins (bench StepBar+Back/Next vs wizard linear) over one content renderer (proposed),
  or unify navigation too?
- **P0 timing:** do the namespace re-home first (clean base) or last (avoid churn during the refactor)?

## 7. Out of scope / unchanged
Pipeline extraction, calibration, the evaluation maths, persistence (Save still a no-op), the plugin's *domain* logic,
and the *camera mechanics* (live feed, burst, exposure, ROI) — those stay host machinery forever. This is a
**host/rendering** refactor: same pixels, driven generically.

> **Superseded for ACQUISITION by Milestone 3 (D1-A, 2026-07-13).** To unblock SM3 (real capture in the wizard)
> without duplicating the bench's burst logic, the camera *mechanics* (burst, auto-exposure, ROI) move **out of
> the bench view into the shared engine** (`captureAcquisitionStep`), so both hosts capture through one call. They
> are still mechanics — they just live in a shared home, not per host. Only **navigation + dev-chrome** stay host.
> See §9.

## 8. Verification (when implemented)
1. Adding/removing a step in the plugin changes both hosts identically, no per-view edits.
2. Metrics|Spectrum and the raster tabs are plugin-declared (removing them from the plugin removes the tabs).
3. `EvaluationResultRenderer` output byte-identical after the P1 extraction (screenshot diff).
4. A `SpectrumCaptureView(cropped=True)` shows the cropped ROI; `roiOverlay=True` paints the ROI rectangle — both from
   plugin flags, pixels host-filled.

---

## 9. Milestone 3 — ACQUISITION convergence & shared capture (unblocks SM3)

Status: **DESIGN — decisions locked 2026-07-13 (Edwin).** ACQUISITION is the last un-converged phase (bespoke in
**both** hosts, differently). This milestone routes it through the shared render seam, **extracts the real-capture
mechanism into the engine so the wizard gains real capture (SM3)**, and collapses the ~100-line mirrored
acquisition-guidance. Design-only; Stages S2–S3 are **rig-gated**. Grounded in the acquisition map of both hosts
(2026-07-13).

**Where each host stands today (the divergence to remove):**
- **Bench:** real camera; **one** `DevCaptureVideoViewModule` reparented across Reference/Sample role-tabs; **one**
  capture button whose label flips; capture is **host-run** — a per-frame burst loop
  (`ImageSpectrumAcquisitionLogicModule`) in the view, with auto-exposure, ROI widening, exposure-lock-on-sample.
  Fully bespoke; does **not** use `WorkflowPhaseRenderer` for acquisition.
- **Wizard:** **no camera**; one Measure button *per step* in sibling tabs; capture delegated to
  `engine.captureAcquisitionStep(step)`, which reads the **virtual** device only.
- **Dead shared skeleton:** `WorkflowPhaseRenderer` already has a `CaptureView` branch + `captureHandler` +
  `decorateCapturePanel(panel, step)` params — **wired by nobody**. Both hosts read `CaptureView` fields directly,
  never through the renderer.

### 9.1 The §7 revision (D1 = A) — a frame-provider seam, not swallowing the camera

§7 said camera mechanics "stay host machinery forever." **Refined for acquisition (rubber-duck 2026-07-13):** the
engine stays **headless** — it does *not* absorb the live camera. `SpectralWorkflowEngine.captureAcquisitionStep`
gains a **frame-provider seam**: `captureAcquisitionStep(step, frameProvider)` runs the numeric burst by calling
`frameProvider()` `frames` times through `ImageSpectrumAcquisitionLogicModule().execute()` — the bench and the engine
already call the **same** `execute()`. The **provider** is host-injected: virtual → a static-image provider (today's
`__capture`); real → a host provider that pumps the live `DevCaptureVideoThread`. The nested `QEventLoop` frame-pump
and the exposure→thread wiring stay **host-side**, so the engine never becomes Qt/camera-coupled. Auto-exposure is
**already** a shared numeric module (`AutoExposureLogicModule.findExposure(measure, …)`, a pure algorithm over a host
`measure` callback — the identical pattern). So what actually relocates is thin (the burst loop's provider
indirection); the wizard gains real capture by being handed the **same real provider**, not by duplicating the bench.
New boundary: **the engine owns the burst maths; the host owns the frame source, camera thread, nav, and dev-chrome.**

### 9.2 Locked decisions

- **D1 = A** — extract capture into the engine; delivers SM3; revises §7 (9.1).
- **D2 = yes** — the bench adopts the wizard's **per-step-tab + per-step-Measure** layout; the single shared camera
  widget is reparented into the *active* step tab (real device only); bench dev-chrome via `decorateCapturePanel`.
  Retire the bench's single-flipping-button, `roleTabs`, and `__roleSpectra` cache.
- **D3 = yes** — keep **two nav skins** (bench `StepBar` + Back/Next + stack vs. wizard linear phase-at-a-time) over
  the one shared content path. Navigation is genuine host identity; unifying it is high-risk, low-value.
- **D4** — a shared **`AcquisitionGuidance`** helper, **~75%** of the ~100 mirrored lines (rubber-duck-measured, not
  a total collapse): the byte-identical icon painters (~40 lines: `__paintGuidanceIcon` / `__amberDotIcon` /
  `__amberArrowIcon` / `__setButtonDot` / emit-reset) lift **now** (cheap, standalone); the derivation (~17 lines)
  collapses after D1-A (`role in __roleSpectra` → `step.getContainer() is not None`); the highlight logic (~15 lines)
  mostly collapses after D2 via a thin per-host tab-bar/button accessor. **Stays host-specific (~15 lines):** the
  `__refreshGuidance` **entry gate** (bench keys off its stack-cursor + camera-ready; wizard off view-mode /
  shownPhases) — it *cannot* unify because **D3 keeps two nav skins**. Net: one shared helper + a ~15-line host
  entry-gate + a highlight-targets accessor per host.
- **D5 = adapter** — the renderer reads step content via the existing `WorkflowPhaseRenderer.stepViewModels` adapter
  (`evaluationResult` / `_view` / `container`); acquisition enters through the already-present `_view → CaptureView`
  branch wired to `captureHandler`. **No `viewModels()` list on the persisted entity; no plugin/persistence change.**

### 9.3 Target architecture

- **The frame-provider seam (9.1):** `engine.captureAcquisitionStep(step, frameProvider)`. The shared capture panel
  builds the provider + burst params from a small **capture context** and passes it to the Measure handler.
- **Shared capture panel** = the renderer's (currently-dead) `CaptureView` branch, wired: `captureHandler(step,
  captureView)` builds prompt + Measure + live preview (when `showLivePreview` and the device is real) + per-frame
  progress; on Measure it calls `engine.captureAcquisitionStep(step, provider)` and plots `step.getContainer()`.
- **`decorateCapturePanel` gains a capture-context channel (rubber-duck fix).** The current 2-arg
  `decorateCapturePanel(panel, step)` has no way to feed the bench's frames / exposure / ROI *into* the engine call.
  It gains a **capture context** it populates — `{ frameProvider, frames, exposure control, ROI-widen callback }` —
  which the Measure handler passes to `captureAcquisitionStep`. The wizard leaves the context at its defaults
  (virtual static-image provider). Without this the dev-chrome would be decorative but disconnected.
- **Camera machinery is EXTRACTED into the shared panel, not refactored in place (S2).** The camera widget
  (`DevCaptureVideoViewModule`), thread (`DevCaptureVideoThread`), device-index resolution, live preview, and the
  real frame-provider all move **out of the bench** into the shared capture panel as host-generic, reusable assets —
  so S3 (wizard real capture) is *pointing the wizard at the same panel* + adding its own calibrated-serial gate, not
  a second build. One camera-widget instance is reparented into the active step tab (bench Option-A), used by
  whichever host has a real device; virtual device → no live preview, Measure still works (virtual provider).
- **Guidance** = the shared `AcquisitionGuidance` helper (D4), keyed off `step.getContainer()`; each host injects its
  own entry-gate + highlight targets.
- **Exposure-lock-on-sample + ROI widening** are not lost — they survive as **capture-context parameters** (real
  provider) + bench dev-chrome, not bespoke view logic.

### 9.4 Implementation phases (staged; S2–S3 rig-gated)

| # | Phase | Impl tasks | Rig | Acceptance |
|---|---|---|---|---|
| **S1a** | Guidance painters → shared util | extract the ~40 byte-identical lines (`__paintGuidanceIcon` etc.) into `AcquisitionGuidance`; both hosts delegate | no | screenshot-diff: guidance visuals unchanged |
| **S1b** | Frame-provider seam | add `captureAcquisitionStep(step, frameProvider)`; virtual = static-image provider (today's `__capture`); back-compat default | no | offscreen wizard capture byte-identical to today |
| **S1c** | Shared panel on the **wizard** | wire the renderer's dead `captureHandler` / `decorateCapturePanel` (+ capture-context); route wizard ACQUISITION through the renderer (per-step tab, Measure → engine); adapter yields `CaptureView` via `_view` | no | offscreen: wizard acquisition renders via renderer; Next-gating intact |
| **S1d** | Synthetic live-frame provider | a fake provider emitting canned frames on a timer, so the **real-frame burst path** gets no-rig coverage before the rig | no | offscreen: burst via the provider yields the expected spectrum |
| **S2a** | Extract camera machinery → shared panel | move `DevCaptureVideoViewModule` + `DevCaptureVideoThread` + device-index resolution + live preview + real frame-provider **out of the bench** into the shared panel (host-generic) | **yes** | bench live preview + resolution work from the shared panel |
| **S2b** | Capture-context channel | `decorateCapturePanel` populates the capture context (provider + frames + exposure + ROI-widen); Measure passes it to the engine | **yes** | bench dev-chrome drives the engine capture (auto-expose, frames, ROI) |
| **S2c** | Bench through the shared panel | bench ACQUISITION delegates to the shared panel + dev-chrome; adopt per-step-tab layout (D2); retire single button / `roleTabs` / `__roleSpectra` | **yes** | **golden-frame**: identical input frames → identical spectrum; **+ live bench smoke** (capture succeeds) |
| **S3** | Wizard real capture = **SM3** | point the wizard at the same shared panel with the real provider; add the wizard's calibrated-serial gate | **yes** | live-burst → graph in the wizard on a real device |
| **S4a** | Full guidance collapse | derivation + highlight into `AcquisitionGuidance`; each host keeps its ~15-line entry-gate + highlight-targets accessor | — | a plugin step edit changes both hosts identically |
| **S4b** | Cleanup + click-through | delete the bench bespoke acquisition panel; click-through both hosts + `--phone` | — | no bespoke acquisition code remains |

Sequencing: **S1a–S1d are no-rig** (the whole seam is proven offscreen, incl. the burst path via S1d's synthetic
provider) → **S2a–S2c** extract + wire the real camera on the rig → **S3** is then a *flip* (same panel, real
provider, + the wizard's own calibrated-serial gate) → **S4** dedups guidance and deletes the bespoke code.

### 9.5 Risk & acceptance

Acquisition is the most hardware-entangled code and the bench real-capture is the hero path.
- The engine stays **headless** — only the burst's provider indirection moves in (9.1); the live camera never enters
  the engine, so offscreen/headless tests keep working.
- **S1 gets a synthetic live-frame provider (S1d)** so the frame-provider burst path — the one seam that carries the
  whole milestone — is exercised offscreen *before* the rig, not first-tested on hardware.
- The bench acceptance bar is **not** "byte-unchanged" (live camera frames are non-deterministic): it is a
  **golden-frame** test (identical recorded input frames → identical extracted spectrum, proving the extraction maths
  is untouched) **plus** a **live bench smoke** (capture still succeeds).
- The scary work (extracting the camera machinery, S2) is isolated and rig-gated; SM3 (S3) only flips on once S2's
  shared panel is proven on the bench — the working bench path stays protected until the shared machinery is proven
  around it.
