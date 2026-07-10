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
| `MetricFieldView(label, value, tooltip, style)` | all | — | label chip + read-only field | `visitMetricField` | evaluation |
| `MetricFieldViewStyle(labelBold)` | all | — | bold label | (on metric) | evaluation |
| `ColorSwatchView(rgb, label)` | all | — | filled swatch | `visitColorSwatch` | evaluation |
| `VerdictView(roastState, hueDegrees)` | all | — | headline | `visitVerdict` | evaluation |
| `SpectrumPlotView(traces[], bands[], title)` **†** | traces, bands, title | (spectra already in model) | plot (curves + band overlays) | `visitSpectrumPlot` | processing, evaluation |
| `SpectrumCaptureView(caption, cropped, roiOverlay)` **‡** | caption, `cropped`, `roiOverlay`, *its presence = "show it"* | **`image`** (masked/cropped frame) | scaled raster image | `visitSpectrumCapture` | acquisition, processing |
| `CaptureView(prompt, captureLabel, showLivePreview, geometry, showFramesControl, showExposureControls)` **‡** | shell params + dev-chrome flags | live video, burst, progress | capture panel | **host capture path** (not visitor) | acquisition |

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

## 8. Verification (when implemented)
1. Adding/removing a step in the plugin changes both hosts identically, no per-view edits.
2. Metrics|Spectrum and the raster tabs are plugin-declared (removing them from the plugin removes the tabs).
3. `EvaluationResultRenderer` output byte-identical after the P1 extraction (screenshot diff).
4. A `SpectrumCaptureView(cropped=True)` shows the cropped ROI; `roiOverlay=True` paints the ROI rectangle — both from
   plugin flags, pixels host-filled.
