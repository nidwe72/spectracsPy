# SPEC — Simplified, plugin-driven navigation + ROI-cropped capture preview

Status: **M1 + M2 + M3-core IMPLEMENTED & RIG-VERIFIED 2026-07-24/25** (nav-model SDK + base extraction: both hosts
rehomed onto `AbstractPluginExecutionView`; DEV plugin drives the should-be flow; Edwin drove the bench on the rig —
works as expected; full suite **249 passed**). **Deferred:** P3/Change G (plugin-declared rasters) + X (remove the
temporary toggle). Source: Edwin, 2026-07-24. Decisions confirmed inline by Edwin on 2026-07-24 (§3, §4, §5, §6).

**M1 as built (2026-07-24):** `plugin_sdk/policy/{NavigationMode,NavigationPolicy,WorkflowPolicy}.py` (Qt-free,
exported via the `plugin_sdk` facade); `SpectralPlugin.policy()` default = `WorkflowPolicy.default()` (both real
plugins verified unchanged: STEP, no expansion); `logic/spectral/navigation/{NavStop,NavigationModel}.py` (pure
`stops(workflow, policy)`, in `spectracsPy-core` — no Qt/engine dep; canonical `PHASE_ORDER` + default phase labels
kept here to stay Qt-free); `model/.../plugin/view/MetadataFormView.py` (transient form descriptor). Tests:
`tests/test_navigation_model.py` (per-phase / step-expand / skip-empty / **mode-independent** / metadata-as-step /
default-policy / facade-exports).

**M2 IN PROGRESS (2026-07-24):**
- **Nav brain (done):** `logic/spectral/navigation/NavigationFlow.py` (Qt-free jump/terminal decisions) +
  `tests/test_navigation_flow.py` (9).
- **Metadata carve-out (done, Change E revised for safety):** `NavigationModel.stops(workflow, policy,
  hasMetadataFields=False)` — the metadata chevron appears from field-presence, rendered as a **transient**
  `MetadataFormView` (NOT a persisted step), so **saved runs are unchanged** (`save()` cascade-persists every step,
  so materialising a metadata step would have altered the stored graph — avoided).
- **B1 base (done, offscreen-tested):** `view/spectral/workflow/AbstractPluginExecutionView.py` — the shared
  navigation host (chevron plan, cursor, Back/Next, AUTO_ADVANCE jump, lazy hook population, terminal→`_onFinish`),
  with subclass seams `_resolvePlugin` / `_renderStop` / `_onFinish` / `_hasMetadataFields` / `_canAdvanceFrom`.
  `tests/test_plugin_execution_view_offscreen.py` (5: STEP flow, jump-to-metadata, per-step chevrons, Back into
  populated phases, terminal/save). Full suite **240 passed**; **wizard/bench untouched (app still works).**
- **B2 (done — wizard rehomed, offscreen-green):** `AbstractPluginExecutionView` gained VIEW mode, the shared
  metadata form, run persistence (D-save), and render hooks (`_beforeRender`/`_afterRender`/`_decorateNav` +
  Change F single-step-no-tab). `WizardViewModule` is now a **thin subclass** (~300 lines) providing only
  `_resolvePlugin` (session), `_renderStop` (real/virtual capture + computed panels), guidance, Cancel/Delete,
  `_leave`→Home. **All three wizard guard tests green** (persistence NEW→VIEW→delete; measure→verdict→terminal +
  the amber Next-arrow; chevron tracking) + full suite **240 passed**. **Not offscreen-covered → needs a
  click-through:** the live-camera acquisition path and the guidance highlight visuals.
- **B3 (done — bench rehomed, offscreen-green):** `DevMeasurementBenchViewModule` is now a base subclass; the fixed
  4-page `QStackedWidget` is **gone** (per-stop rendering), plugin picker via `_resolvePlugin`, bench **saves**
  (D-save, via `_pluginProvenance`), `_leave`→Settings, raster/report/publish tabs ported, the CapturePanel kept as
  a **persistent singleton** (report/raster read its frames after leaving acquisition). New
  `tests/test_dev_bench_nav_offscreen.py` (3 tests: chevron, Next-gating, step-through+finish, Back,
  no-publishing) with the camera mocked + a stub plugin. Full suite **243 passed**. Also added: computed-phase
  cache invalidation on Back-into-acquisition (re-capture ⇒ re-process).
- **Rig-verified by Edwin (2026-07-24):** the bench walk-through works; the capture dev view is fine. **One
  regression found + fixed:** the acquisition guidance (amber ● on the next tab + the coach line) stopped
  refreshing *after a capture* — the refactor had moved guidance to a render-only hook, but a capture only calls
  `_refreshNav` (no re-render). Fix: `_refreshNav` now fires an `_afterNav()` hook that both hosts use for
  guidance, so it updates on capture too (this was a latent bug in the wizard as well). Guard test added
  (`test_refresh_nav_fires_guidance_hook_on_capture`). Also reworded the DEV Sample prompt
  ("select oil-tab…" → "Insert the oil dilution and capture") — the old wording made no sense once on the tab.
- **M2 COMPLETE.**
- **M3 rig-verified (Edwin 2026-07-24/25): the should-be flow works as expected on the bench.** Four cosmetic
  fixes landed from the rig walk-through: (1) scrollbars off on the capture video view (the crop `fitInView` tripped
  a stray one — `BaseVideoViewModule`); (2) the chevron seam between two gray segments drawn in lighter gray
  (`#6E6E6E`) so they read apart (`StepBarWidget`); (3) a single-plot step now **fills** the panel vertically (skip
  the top-packing stretch + plot Expanding — `QtWorkflowRenderer`); (4) the cropped preview **fills** the view
  (`IgnoreAspectRatio`) so there are no black letterbox margins around the strip (`DevCaptureVideoViewModule`).
- **M3 (core done — offscreen-green):** the DEV plugin now declares the whole should-be
  presentation. **P1** `policy()` = AUTO_ADVANCE + `stepChevronPhases={ACQUISITION}` + the **role-lift**
  (`CapturePanel.setActiveStep` hides the internal role-tabs so the chevron is the role selector; bench `_renderStop`
  focuses the panel per step; `_canAdvanceFrom` gates an earlier ACQ step on itself, the boundary on all-captured).
  **P2** `metadata()` = the 3 fields (land on the form after measuring). **P4/Change A** cropped preview:
  `CaptureView.croppedPreview` + `DevCaptureVideoViewModule.setCropToRoi` (fitInView to the ROI rect, box hidden) +
  `CapturePanel` wiring. **P5** the temporary `SIMPLIFIED_NAVIGATION` toggle (flip False ⇒ as-is). Tests:
  `test_dev_plugin_m3_declarations.py` (4) + a should-be bench-nav flow test; full suite **249 passed**. **Rig
  click-through needed:** the per-chevron camera focus, the visual ROI crop, exposure-lock-on-sample under the
  role-lift. **Deferred: P3/Change G** (rasters as plugin-declared `SpectrumCaptureView` — the host raster hook
  stays for now; low priority as the should-be flow jumps past PROCESSING) and **X** (remove the toggle after rig
  sign-off).

## 0. Goal & why

Make the **DEV plugin**, driven on the master measurement bench, present the *flow an end-user actually sees* — so
the **Director** screencast records the real end-user experience, not the dev Swiss-knife with all its intermediate
tabs. Four behavioural changes, a temporary test toggle, and two forward seams:

- **Change A — ROI-cropped capture preview.** During ACQUISITION (esp. the AE sweep) show **only the cropped ROI
  strip**, not the whole sensor frame.
- **Change B — auto-advance.** One Next out of ACQUISITION jumps forward, halting on the **METADATA** form, with
  every intermediate phase still **Back-reachable**; one more Next → PUBLISHING.
- **Change C — DEV gains the METADATA phase** (title / roasting-temp / date, taken over from PumpkinOilPlugin), the
  landing spot after measuring.
- **Change D — per-step "virtual" chevrons.** The plugin can ask that each ACQUISITION *step* (Reference, Sample)
  appear as **its own chevron entry**, so the run-through reads intuitively — **purely a UX/navigation change; the
  workflow→phase→step model is untouched behind the scenes.**
- **Change E — METADATA becomes a normal phase with step(s)** (via a new `MetadataFormView`), removing its special
  case; a plugin can later split metadata into multiple steps. (§4.7)
- **Change F — a phase with one step renders without a tab** (general rule). (§4.7)
- **Change G — the bench's raster inspection tabs are plugin-declared** (`SpectrumCaptureView`), not host-injected —
  "no black magic." (§4.7)
- **The plugin drives all of it** via a `WorkflowPolicy` (container composing `NavigationPolicy`); the DEV toggle is
  **temporary test scaffolding** (§6). The **measurement bench now also saves** its runs (D-save = yes).
- **Forward seams (later):** reorder a phase's steps + choose the default-selected step (§7.2); phase contents (§7.3);
  guidance/hints → the container (§7.4).

**The unifying idea (§4):** rather than keep patching the bench's bespoke navigation, introduce **one generic,
plugin-declared navigation model** — a flat list of **navigation stops (chevrons)** derived from the workflow + the
`NavigationPolicy`. Per-phase chevrons, per-step chevrons (Change D), the metadata stop (C), and the auto-advance
jump (B) all fall out of that one model. This is the "as generic as possible" route Edwin asked for — and it
**dissolves** the cursor↔stack misalignment risk (§9b-1) instead of working around it.

---

## 1. The intended end-state flow (should-be, toggle ON)

```
  chevron:  [ Reference ] [ Sample ] [ Processing ] [ Evaluation ] [ Metadata ] [ Publishing ]
                 │            │          (Back-reachable, fully populated)          ▲
   capture ──────┘   capture ─┘                                                     │
   reference          sample                                                        │
                        │  one Next completes ACQUISITION → runs PROC+EVAL+PUB       │
                   Next │  hooks, JUMPS forward, HALTS on the METADATA form ─────────┤
                        ▼                                                            │
                   METADATA  (title / roasting temp / date)  ◄─ lands "after measuring"
                        │  Next
                        ▼
                   PUBLISHING  (verdict badge + Publish)   ◄─ final phase
```
Reference and Sample are **two chevron entries but still the two steps of the one ACQUISITION phase** (Change D).
**Toggle OFF (old-nav regression test)** = today's shape + the new metadata stop: one "Acquisition" chevron (role
sub-tabs inside), stepping ACQ → PROC → EVAL → METADATA → PUBLISHING one Next each.

---

## 2. Note on genericity — what is generic today, and what is not  *(answers Edwin's questions)*

Convergence Milestone 1 ([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md)) made the
**content path** generic, but its **D3 deliberately kept navigation per-host**. So:

| Concern | Generic today? | Why / consequence |
|---|---|---|
| **Phase/step content** (what's in each tab) | **Yes** — `WorkflowPhaseRenderer` + the visitor render whatever view-models the plugin declares | Edwin's "generic" intuition is correct *here*. |
| **Metadata form rendering** | Partly — the **wizard** builds the form from `MetadataField`s | But the **bench's bespoke nav never added METADATA to its phase list**, so it never *appears* on the bench. The renderer is generic; the bench's navigation is not, so it never invokes it. |
| **Navigation shell** (chevron, phase list, Next/Back, the stack) | **No** — D3 kept two skins: bench `StepBar`+fixed `QStackedWidget`+hand-coded state machine; wizard linear | This is exactly why C (metadata) and D (step chevrons) need bench work — the bench hand-codes its nav. **§4 fixes the root cause by making navigation generic.** |
| **Saving the run** | **No** — the **wizard** has `__saveNewRun`; the **bench has no save at all** | The bench is a measure-and-**inspect** dev tool, not a saved-run producer — a deliberate host difference, not a genericity gap. Metadata on the bench is therefore render+edit only (no persistence in scope). |

**Takeaway:** content is generic; *navigation and run-persistence are per-host by an explicit past decision (D3).*
The pile-up of navigation requests (B, C, D) is the signal to **revisit D3 for navigation** — §4.

---

## 3. Current architecture (grounded, brief)
- Phase spine: `SpectralWorkflowPhaseType` = ACQUISITION, PROCESSING, EVALUATION, **METADATA**, PUBLISHING;
  engine `PHASE_ORDER` (25), `runPhaseHook` (77), `isSkipped` (89). `metadata()` returns `list[MetadataField]`.
- **Bench** `DevMeasurementBenchViewModule`: `StepBarWidget` + **fixed 4-page `QStackedWidget`** (ACQ0/PROC1/EVAL2/
  PUB3, built at 120) + `__cursor`; `__renderPhase` (323) does `__stack.setCurrentIndex(self.__cursor)` — cursor ==
  page index, positionally. `onClickedNext` (368) explicit state machine. No METADATA, no save.
- **CapturePanel** (shared): `__roleTabs` (Reference/Sample) with ONE reparented camera + ONE spectrum plot; role
  machinery already present (`__stepForRole` 233, active-step, exposure-lock-on-SAMPLE 247, guidance cue). Change D
  lifts role selection **out** of `__roleTabs` and up into the chevron.
- Preview: `DevCaptureVideoViewModule.handleVideoThreadSignal` (22) paints the **whole frame** (`fitInView(imageItem)`
  27); `setRoi` (29) overlays a dotted box; the ROI rect is already computed in
  `CapturePanel.__applyPreviewRoiOverlay` (401). AE brightness is whole-frame and display-independent.
- **Wizard** already renders METADATA and halts there; runs Pumpkin in STEP mode. Wizard changes are **deferred**
  (§8 D-wizard) — DEV is `benchOnly`.

---

## 4. The generic navigation model (the unifying design)

### 4.1 `NavStop` + `NavigationModel` (Qt-free, shared)
A **`NavStop`** is one chevron entry:
```python
class NavStopKind(Enum): PHASE; STEP
class NavStop:
    kind          # PHASE or STEP
    phaseType     # the owning phase
    step          # the SpectralWorkflowStep (STEP kind only)
    label         # chevron text: phase label, or the step's label ("Reference"/"Sample")
```
**`NavigationModel.stops(workflow, policy) -> list[NavStop]`** derives the flat chevron list generically:
- walk `PHASE_ORDER`; include a phase iff it will show (non-empty via `isSkipped`; METADATA iff `metadata()` has
  fields);
- for each included phase: **if `policy.expandsSteps(phaseType)`** → emit one `STEP` stop per step (label = step
  label); **else** → one `PHASE` stop (label = phase label).

The chevron = `[stop.label for stop in stops]`; the cursor indexes `stops`. **Behind the scenes nothing changes** —
stops are a *view* over the existing workflow→phase→step graph (Change D is "just UX", as Edwin put it).

**Illustration — the SAME code, two plugins, two chevrons.** `NavigationModel.stops()` is a pure function of the
workflow + policy; the host just renders the list it returns.

```
DEV plugin, should-be policy (AUTO_ADVANCE, expandSteps={ACQUISITION}):

  stops = [                                                      chevron shown:
    NavStop(STEP,  ACQUISITION, step=Reference, "Reference"),  ┐
    NavStop(STEP,  ACQUISITION, step=Sample,    "Sample"),     ┘ two steps, one phase   [Reference][Sample]
    NavStop(PHASE, PROCESSING,                  "Processing"), ─ phase tabs              [Processing]
    NavStop(PHASE, EVALUATION,                  "Evaluation"), ─ phase tabs              [Evaluation]
    NavStop(PHASE, METADATA,                    "Metadata"),   ─ metadata form           [Metadata]
    NavStop(PHASE, PUBLISHING,                  "Publishing"), ─ verdict + publish        [Publishing]
  ]
  cursor ── one index into this list; Back/Next move it; AUTO_ADVANCE jumps it to the Metadata stop.

Pumpkin plugin, default policy (STEP, no expansion):

  stops = [
    NavStop(PHASE, ACQUISITION, "Acquisition"),   ← role sub-tabs stay INSIDE (not expanded)   [Acquisition]
    NavStop(PHASE, PROCESSING,  "Processing"),                                                  [Processing]
    NavStop(PHASE, EVALUATION,  "Evaluation"),                                                  [Evaluation]
    NavStop(PHASE, METADATA,    "Metadata"),                                                    [Metadata]
    # PUBLISHING absent — Pumpkin declares no publishing steps (isSkipped)
  ]
```

**How the host draws it (one loop, no per-plugin/per-host branches):**
```
  render():
     stepBar.setSteps([s.label for s in stops])
     stepBar.setCurrentIndex(cursor)
     stop = stops[cursor]
     if stop.kind == STEP:   show CapturePanel.setActiveStep(stop.step)     # acquisition step
     else:                   show phaseContent(stop.phaseType)              # phase tabs / metadata form
```
Add a step, flip `expandSteps`, change the policy mode — the chevron and flow change with **zero host edits**. That
is the whole point of moving navigation into a declared model.

### 4.2 `NavigationPolicy` + `NavigationMode` (Qt-free, plugin_sdk)
```python
class NavigationMode(Enum): STEP; AUTO_ADVANCE
class NavigationPolicy:                        # ONE cross-cutting concern: flow/navigation
    @staticmethod
    def default(): ...                          # STEP, no step-expansion (today)
    def __init__(self, mode=STEP, stepChevronPhases=()): ...
    def mode(self): ...
    def expandsSteps(self, phaseType): ...       # phaseType in stepChevronPhases
    # forward-compatible home for §7.2 (default-selected step per phase)

# The CROSS-CUTTING POLICY CONTAINER (Edwin) — composes NavigationPolicy, grows by composition.
# Name TBD — see D-policy-name (§10). Using «WorkflowPolicy» as the working name.
class WorkflowPolicy:
    def __init__(self, navigation=None /*, future: report=…, guidance=…, publish=…, save=… */):
        self.navigation = navigation or NavigationPolicy.default()
    @staticmethod
    def default(): return WorkflowPolicy()

# base plugin — ONE cross-cutting hook, returns the container (not NavigationPolicy directly)
def policy(self) -> WorkflowPolicy: return WorkflowPolicy.default()
```
The host reads `plugin.policy().navigation`. Default ⇒ every existing plugin unchanged (one PHASE stop each, STEP
mode). DEV should-be preset = `WorkflowPolicy(navigation=NavigationPolicy(AUTO_ADVANCE,
stepChevronPhases={ACQUISITION}))`. **Why a container, not a bare `navigation()` hook:** a future cross-cutting
concern (report inclusion at the *workflow* level, guidance/hints, publish config, save) becomes a **new composed
field on `WorkflowPolicy`**, not a new plugin hook — the plugin surface stays one `policy()` method.

**Division of labour: the plugin declares a POLICY; the host derives the MODEL.** A plugin never touches
`NavStop`/`NavigationModel` — it only declares steps (as it already does) and a `NavigationPolicy`. What that looks
like in the DEV plugin:
```python
class DevSpectralPlugin(SpectralPlugin):
    SIMPLIFIED_NAVIGATION = True                      # temporary test toggle (removed after the sweep, §6)

    def policy(self):                                 # ← the ONLY new hook (cross-cutting container)
        if self.SIMPLIFIED_NAVIGATION:
            return WorkflowPolicy(navigation=NavigationPolicy(
                NavigationMode.AUTO_ADVANCE, stepChevronPhases={SpectralWorkflowPhaseType.ACQUISITION}))
        return WorkflowPolicy.default()               # STEP, no expansion = today

    def acquisition(self, workflow):                  # unchanged — still just declares two steps
        phase = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        phase.addToSteps(self.__measurementStep(REFERENCE, "Reference", "Insert isopropanol and capture"))
        phase.addToSteps(self.__measurementStep(SAMPLE,    "Sample",    "Select oil-tab and capture"))

    def metadata(self, workflow):                     # Change C — taken over from Pumpkin as-is
        return [MetadataField("title", "Title", MetadataField.TEXT, showInWorkflowsTable=True, order=0),
                MetadataField("temperature", "Roasting temperature (°C)", MetadataField.NUMBER, order=1),
                MetadataField("dateOfRoasting", "Date of roasting", MetadataField.DATE, order=2)]

    def __measurementStep(self, role, label, prompt):
        step = SpectralWorkflowStep(); step.setRole(role); step.setLabel(label)
        step.setFrames(self.FRAMES); step.setMandatory(True)
        step.setView(CaptureView(prompt=prompt, captureLabel="Capture " + label, geometry="transmission")
                     .setCroppedPreview(self.SIMPLIFIED_NAVIGATION))     # Change A
        return step
```
The host then calls `NavigationModel.stops(engine.getWorkflow(), plugin.navigation())` and renders the list — the
plugin stays declarative, the host stays generic.

**Boundary — content vs. policy (Edwin's separation-of-concerns point).** The clean rule:
- **Content** → the phase methods (`acquisition/processing/evaluation/publishing`) and `__fooStep()` build
  view-models. They should declare **only content** — *what* is on screen.
- **Cross-cutting FLOW/presentation** → the `navigation()` policy object. Navigation mode, step-chevrons, and
  (future) default-selected-step are cross-cutting, so they belong in one declared policy, not scattered in the
  content methods. This is exactly the split you're after.
- **Per-item facts stay on the item.** A flag like `shownInReport` ("is published to the PDF") is intrinsically
  *local* to one curve/metric — the natural, discoverable place is the fluent `.setShownInReport(True)` right where
  that item is built. Pulling it into a central policy would force referencing items by id and read *worse*, not
  better. So: **cross-cutting → policy; per-item → on the item.** `phase.setHint(...)` (the coach line) is the one
  current wart — a guidance concern living in a content method; it can migrate to the container later if we want
  content methods 100% pure.
- **The container (Edwin):** the cross-cutting concerns live in **one composite class** that *has-a*
  `NavigationPolicy` (and, later, sibling sub-policies) — see §4.2. The plugin exposes it via a single `policy()`
  hook, so future cross-cutting concerns are added by **composition**, never a new hook. Name → **D-policy-name**
  (§10, proposals there).

### 4.3 How a host renders from the model
- **Chevron** = the stop labels; **cursor** = index into `stops`.
- **Render the current stop** by `kind`:
  - `PHASE` stop → the phase's tabs (existing per-phase panels / `WorkflowPhaseRenderer`).
  - `STEP` stop → **just that step's content**. For an ACQUISITION step: the shared **CapturePanel focused on that
    step's role** (`setActiveStep(step)`; `__roleTabs` hidden — the chevron replaces them).
- **Back/Next** walk `stops` one at a time. Multiple stops may map to the **same underlying page** (both ACQUISITION
  step-stops → the one CapturePanel, differing only by active role) — so the bench renders **per-stop on demand**
  instead of a fixed positional stack. *This removes the misalignment class of bug entirely (§9b-1).*

### 4.4 Change B — auto-advance as a cursor jump over stops
AUTO_ADVANCE: the Next that leaves the **last ACQUISITION stop** (Sample) runs `__runProcessing()` +
`__runEvaluation()` + `__runPublishing()` (populate all), then sets the cursor to the **halt stop** — the first
`METADATA` stop if metadata fields exist, else the final stop — and renders. STEP mode = one stop per Next. From
METADATA, a normal Next → PUBLISHING. The jump fires once; afterwards Back/Next just walk `stops`.

### 4.5 Change C — the METADATA stop
`DevSpectralPlugin.metadata()` returns Pumpkin's three fields (`title` TEXT+`showInWorkflowsTable`, `temperature`
NUMBER, `dateOfRoasting` DATE). It enters `stops` as a `PHASE` stop; rendering it needs a **metadata form panel** on
the bench (extract a shared `MetadataFormPanel(specs)` from the wizard's `__metadataPanel`/`__metadataSpecs`/
`__readMetadata` — dedup, preferred). **Render+edit only; not persisted on the bench** (§2). It is the auto-advance
halt (§4.4).

### 4.6 Change D — per-step "virtual" chevrons
Driven by `policy.expandsSteps(ACQUISITION)`. The two ACQUISITION steps become two `STEP` stops ("Reference",
"Sample"). Selecting one shows the CapturePanel focused on that role; `__roleTabs` is hidden (the chevron *is* the
role selector). **This relocation — moving role selection out of the panel's internal tabs up into the chevron — is
the "role-lift"** (§9b-11): the host drives the active role via a new `setActiveStep(step)` instead of the internal
tab bar. Capture/exposure-lock/guidance logic is unchanged — only *where the role is chosen* moves; because the
exposure-lock-on-Sample and the live camera key off the active role, it is **rig-verified**, not offscreen-only. Next from
"Reference" → "Sample"; Next from "Sample" (last ACQUISITION stop) triggers the §4.4 jump. **Acquisition-complete
gating** applies when leaving the *last* ACQUISITION stop (both captured), not each step — a step-stop's own Next is
allowed once that step is captured (more intuitive; matches Edwin's intent).

### 4.7 Uniformity fixes (Edwin 2026-07-24) — "no special-cases, no black magic"
Three corrections that make the model uniform and fully plugin-driven:
- **(E) METADATA becomes a normal phase with step(s).** Today `metadata()` returns a bare `list[MetadataField]` and
  the phase has **no** engine steps — the odd-one-out that forced a special case in `stops()`. Fix: a new
  **`MetadataFormView`** view-model (Qt-free, carries the fields), rendered as the editable form; the METADATA phase
  carries **step(s)** whose content is a `MetadataFormView`. For now the field list maps to **one** metadata step
  (the engine *materialises* it from `metadata()`, so the plugin API is unchanged) — **later a plugin can declare
  multiple metadata steps** to structure metadata (Edwin's "there might arise the need to structure meta by steps").
  Result: `stops()` treats METADATA like every other phase (count steps); the special case disappears (§9b-1).
- **(F) A phase with exactly ONE step renders WITHOUT a tab.** General rule (both hosts): a single-step phase shows
  its step content directly — no redundant one-tab bar. Applies to metadata (one form), PUBLISHING (one Send-to-LIMS
  step), etc. Multi-step phases keep their tabs. (Edwin: "if a phase has only one step, display the step not in an
  explicit tab.")
- **(G) The bench's raster inspection tabs are PLUGIN-DECLARED, not host-injected.** Today the bench injects
  "Reference/Sample raster" tabs as host dev-chrome (the "hook"/black magic). Fix: the **DEV plugin declares them**
  as `SpectrumCaptureView` steps — the existing view-model where the *plugin declares the shell* and the *host fills
  the `.image`* pixels (the by-design pattern, convergence P5's own TODO). This **removes the dev-tab hook entirely**;
  every bench tab is now plugin content. One fewer subclass difference (§10).

---

## 5. Change A — ROI-cropped capture preview
`DevCaptureVideoViewModule.setCropToRoi(bool)` (default False). In `handleVideoThreadSignal`, when cropping and an
ROI rect is known → `videoWidget.fitInView(<roi rect>, KeepAspectRatio)` and hide the dotted box; **no ROI yet ⇒
full-frame fallback**. Scene coords == image pixels, so fitting the ROI rect *is* the crop (no per-frame copy).
Plugin flag `CaptureView.croppedPreview: bool = False` (+ fluent setter); `CapturePanel` wires it from
`__applyPreviewRoiOverlay`. DEV should-be sets it True.

---

## 6. As-is vs should-be — a TEMPORARY test toggle  *(confirmed — Edwin)*
`DevSpectralPlugin.SIMPLIFIED_NAVIGATION = True` selects the whole should-be preset — `policy()` →
`WorkflowPolicy(navigation=NavigationPolicy(AUTO_ADVANCE, stepChevronPhases={ACQUISITION}))`, and
`CaptureView.setCroppedPreview(True)`. Its
sole purpose is regression-checking the old nav during the sweep (flip OFF ⇒ old step-through must still work);
**removed after the sweep** (§11 phase X) ⇒ DEV permanently should-be. Base defaults keep every other plugin
byte-unchanged. The METADATA phase (C) is **permanent, independent of the toggle**; the toggle governs only
auto-advance + step-chevrons + cropped-preview.

---

## 7. Forward seams (future — designed-for now)
- **7.1 Step order** — already plugin-driven (insertion order); reorder `addToSteps`, or a future order override on
  `NavigationPolicy`.
- **7.2 Default-selected step when a phase opens** — home = `NavigationPolicy` (`{phase: defaultStepLabel}`); the
  host sets the tab index from it. Deferred.
- **7.3 Phase contents** — deferred; stays plugin-declared view-models, no host change.
- **7.4 Guidance/hints → the container (future, ILLUSTRATIVE — not M1–M3).** Today the coach line is
  `phase.setHint(text)` inside content methods. To make content methods 100% pure, guidance becomes a composed
  sub-policy on `WorkflowPolicy`:
  ```python
  def policy(self):
      return WorkflowPolicy(
          navigation=NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={ACQUISITION}),
          guidance=GuidancePolicy({                              # ← a future composed member
              SpectralWorkflowPhaseType.ACQUISITION: "measurement complete",
              SpectralWorkflowPhaseType.PROCESSING:  "You can view the measurement results here.",
              SpectralWorkflowPhaseType.EVALUATION:  "The measurement has been evaluated.",
              SpectralWorkflowPhaseType.PUBLISHING:  "Send the result to the laboratory if you want.",
          }))
  ```
  The host reads `plugin.policy().guidance.hintFor(phaseType)` when rendering a phase (instead of
  `phase.getHint()`), and `processing()/evaluation()/…` drop their `setHint` calls → pure content. **Deferred —
  shown only to validate the container shape; M1–M3 keep `setHint`/`getHint` unchanged (§9b-15).**

---

## 8. Open decisions (recommendations adopted unless Edwin objects)
- **D-A1** crop the whole ACQUISITION live preview (adopted), not only AE.
- **D-A2** crop as a plugin `CaptureView.croppedPreview` flag (adopted).
- **D-metadata-reuse** extract a shared `MetadataFormPanel` (adopted, "as generic as possible").
- **D-wizard** the wizard **adopts** the NavigationModel in **M2** (behaviour-preserving, default policy). What is
  *deferred* is an end-user *plugin* selecting AUTO_ADVANCE / step-chevrons — none does yet (Pumpkin stays STEP).
- **D-scope** RESOLVED → **base-first** (§10, Edwin): generic NavigationModel, base extracted first, then DEV
  behaviour. (The bench's fixed stack + misalignment risk are retired, not patched.)
- **D-report** RESOLVED (§4.4/§4.5): land on METADATA then PUBLISHING.
- **D-policy-name** → `WorkflowPolicy` (Edwin's lean adopted; §10 lists the alternatives).

---

## 9. Rubber-duck — design self-check
1. **One-shot jump** — after landing, Back-then-Next walks `stops` via the normal cursor; the jump fires only on
   leaving the last ACQUISITION stop. ✔
2. **Halt set = {METADATA-with-fields}**, else the final stop — computed from `stops`, not hard-coded. ✔
3. **Change D is view-only** — `stops` is a projection of the unchanged workflow→phase→step graph; the engine,
   hooks, containers, and persistence model are untouched. ✔
4. **Regression** — `NavigationPolicy.default()` + `croppedPreview=False` ⇒ every non-DEV plugin unchanged; toggle
   OFF ⇒ DEV old-nav (bar the intentional metadata stop). ✔

## 9b. Rubber-duck — IMPLEMENTATION self-check (base-first M1 → M2 → M3)

**M1 — nav model (SDK)**
1. **METADATA special-case DISSOLVED by Change E.** Because `metadata()` now materialises into a real **step**
   (§4.7-E), the METADATA phase *has* a step like any other — so `NavigationModel.stops()` counts steps uniformly,
   **no metadata special case**. (Earlier plan special-cased it; Change E removes that.) The materialisation must run
   for **both** NEW (from `plugin.metadata()`) and VIEW (from persisted `SpectralWorkflowMetadata` rows) so the step
   exists in both. ⚠
2. **`MetadataFormView` is an *editable* view-model** — unlike passive views (labels/plots) it holds live input
   widgets and feeds save. It rides the visitor like the rest, but its `visitMetadataForm` builds inputs (reusing the
   `MetadataFormPanel`), and save reads them back. Keep read-model vs. write-back explicit. ⚠
3. **Expanded headless steps** — expanding a phase whose steps carry no view-models would yield empty chevron stops.
   ACQUISITION steps always carry a `CaptureView`, so fine; `stops()` should still skip/limit expansion to renderable
   steps (or document that expansion targets capture phases). Minor.

**M2 — base extraction, behaviour-preserving (the crux)**
4. **Subclass surface is now genuinely tiny** (Changes E/G + D-save shrank it): `resolvePlugin()` + (a) the **leave
   destination** (end-user → Home, bench → Settings; **saving is unified in the base**, D-save = yes, so only the
   destination differs); (b) an optional **plugin-selector slot** (bench any-picker / end-user assigned-picker /
   none); (c) the **guidance entry-gate** (convergence D4). The old **dev-tab hook is GONE** — rasters are
   plugin-declared `SpectrumCaptureView`s (§4.7-G). ✔
   4a. **Bench-save is a *desired* change, not preserved.** D-save = yes means the bench starts persisting runs. It's
   still behaviour-*adding* (not breaking), and exercised only when DEV drives the full flow (M3); verify by
   click-through + a save round-trip test, not "byte-unchanged". ⚠
5. **VIEW mode lives in the base** (wizard has it; the bench enters it too now that it saves) — read-only + editable
   metadata ride the base. ✔
6. **AUTO_ADVANCE is NEW-mode only** — the base gates the jump to run-creation; browsing a saved run (VIEW) must
   never auto-jump. ⚠
7. **CapturePanel is UNTOUCHED in M2** — default policy ⇒ no step-expansion ⇒ ACQUISITION stays ONE stop with its
   internal `__roleTabs`, exactly as today. The role-lift is strictly M3, so M2 carries **zero camera risk**. ✔
8. **Guard the refactor with tests FIRST.** The wizard has offscreen coverage
   (`test_workflow_wizard_persistence_offscreen`); the **bench nav is likely under-covered**. Add a bench offscreen
   nav test (stops → chevron → Back/Next) **before** re-homing the bench, so "behaviour-preserving" is *guarded*, not
   merely asserted. ⚠
9. **Metadata materialisation must not double-persist.** The METADATA step now carries the form, but the saved rows
   remain `SpectralWorkflowMetadata` — ensure save maps the `MetadataFormView` back to those rows once (no new
   entity, no duplicate). Verify the wizard persistence test stays green. ⚠
10. **Single-step-no-tab (Change F) is a *general visible change*** — it drops the one-tab bar for single-step phases
    (metadata, PUBLISHING, Pumpkin's one-step EVALUATION). So M2's "no visible change" holds for *multi*-step phases;
    single-step phases intentionally lose their redundant tab. Land F explicitly (not silently) and screenshot-check
    the affected phases. ⚠

**M3 — DEV behaviour (policy + content)**
11. **Role-lift is the rig-risk.** Driving CapturePanel's active role from the chevron (`setActiveStep`) + hiding
    `__roleTabs`: verify the SAMPLE exposure-lock (keys off the active role), the amber guidance cue (retarget to
    the chevron), and the one-shared-camera reparent all still fire. **Rig-verify.** ⚠
12. **Acquisition-complete gating with step-chevrons.** Recommended rule: **free** navigation among the ACQUISITION
    step-stops (capture Reference/Sample in any order); the all-captured gate is enforced **only at the jump** (Next
    off the *last* ACQUISITION stop). Define it exactly so a half-captured Sample-stop can't jump. ⚠
13. **DEV rasters = `SpectrumCaptureView` steps (Change G).** DEV declares Reference/Sample raster steps in
    PROCESSING; the host fills `.image` from the captured frame. Verify the host image-fill path feeds these (the
    frame is host-owned — the plugin declares the shell only), and that they land as PROCESSING tabs (multi-step
    phase ⇒ tabs, so Change F does not collapse them). ⚠
14. **The jump = run hooks + land on halt.** Between the last ACQUISITION stop and the halt (METADATA) stop, run each
    `engine.runPhaseHook` (populate); set cursor → halt; keep per-stop render lazy. Idempotent (hooks clear+rebuild).
    ✔
15. **Toggle OFF ≠ literal pre-work nav.** OFF gives STEP nav BUT keeps the permanent METADATA stop (DEV.metadata()
    is permanent). Expected — the toggle regression-tests the *nav mechanism*, not metadata presence. Document so no
    one reads OFF as byte-identical to today. ✔
16. **Cropped preview** — display-only, needs an ROI (full-frame fallback pre-ROI); AE brightness unchanged. ✔
17. **Toggle removal (X)** — deleting `SIMPLIFIED_NAVIGATION` leaves DEV permanently should-be; ensure no OFF branch
    lingers. ✔

**Cross-cutting**
18. **`setHint` stays as-is in M1–M3** — the guidance→container migration (§7.4) is future/illustrative, **not** in
    scope; the base reads `phase.getHint()` as today. No scope creep. ✔
19. **Director anchors on the BASE** — stable `objectName`s (chevron / Back / Next / capture / metadata fields /
    publish) added in M2 so both subclasses are drivable by one script; check against doc-automation §16. ✔

**Final pass (additions)**
20. **Define WHEN the metadata step is materialised.** `stops()` counts steps uniformly, so the METADATA step must
    already exist when `stops()` runs. Rule: the **engine materialises** it eagerly during workflow build — from
    `plugin.metadata()` (NEW) or the persisted `SpectralWorkflowMetadata` rows (VIEW). Cheap (metadata() just returns
    a list, no computation), unlike processing/evaluation which stay lazy. ⇒ metadata eager, heavy hooks lazy. ⚠
21. **`stops()` is mode-independent.** AUTO_ADVANCE vs STEP produce the **same** stop list — only cursor *behaviour*
    (the jump) differs. Unit-test that invariant so a policy change can't silently reshape the chevron. ✔
22. **The bench needs an offscreen test harness.** The bench is camera-coupled and has ~no offscreen coverage; M2-B3
    must make `DevPluginExecutionView` instantiable offscreen on the **virtual device** (as the wizard tests already
    do) — that harness is a deliverable of B3, not an afterthought. ⚠
23. **New offscreen GUI tests must dodge modal dialogs.** Cancel/confirm go through `InWindowDialog.confirm`; an
    unpatched modal *hangs* the suite (the T2 lesson — see `SPEC_test_hygiene_debt.md`). Patch the confirm in every
    new nav/save test; the `conftest.py` hang-watchdog is the backstop. ⚠
24. **`MetadataFormView` is transient, values persist as rows.** The view-model is a render descriptor (like
    `CaptureView`) — **not** persisted; only the entered values persist as `SpectralWorkflowMetadata`. On VIEW-load,
    rebuild the form-view from the rows. No new persisted entity, no serializer work. ✔
25. **Raster `SpectrumCaptureView` in VIEW mode may lack pixels.** Its `.image` is host-filled from the *live*
    capture; a saved bench run reopened later has no live frame. Acceptable (rasters are dev inspection, bench is
    master-only) — but decide: re-fill from a persisted capture, or show the shell empty in VIEW. Note, don't block. ⚠

## 9c. Rubber-duck — B2 (wizard) + B3 (bench) rehoming, pre-impl (2026-07-24)

The base (B1) is built + offscreen-tested; it handles **NEW-mode** navigation only. Rehoming the two real hosts:

**B2 — rehome `WizardViewModule` onto the base**
1. **VIEW mode must be added to the base.** NEW plan is *predictive* (assume PROC/EVAL will populate); VIEW plan is
   *actual* (the loaded run's populated phases + persisted metadata rows). `_plannedPhases` branches on
   loaded-vs-engine; `_ensurePopulated` already no-ops in VIEW (guarded).
2. **VIEW uses default STEP policy** (browsing a saved run never auto-jumps) — `_policy()` returns default when
   there is no live plugin (already handled).
3. **Metadata source differs by mode** — NEW: `plugin.metadata()`; VIEW: persisted rows. `_hasMetadataFields` and
   the form specs branch on mode.
4. **Move the metadata form + save INTO the base** (shared) so the bench inherits them (D-save, §10). Use
   single-underscore names (`_metadataWidgets`) — update the guard tests' private accessors accordingly.
5. **Keep the class name `WizardViewModule`** — 8 non-test files reference it (NavigationHandler, Login, Main, Home,
   Registration, …). Subclass the base; defer the `EndUserPluginExecutionView` rename (cosmetic).
6. **Don't stomp the amber-arrow / guidance.** The base `_refreshNav` sets no icon; add an `_afterRender` /
   `_decorateNav` hook so the wizard re-applies its amber Next-arrow + coach cues. Move the `_rendering` guard flag
   into the base so the tab-change churn during a re-render is ignored.
7. **Camera lifecycle:** the base clears the tab widget each render → orphans the `CapturePanel`. Add a
   `_beforeRender` hook so the wizard stops the stream before the clear.
8. **Extra nav buttons:** base makes Back + Next; the wizard overrides `createNavigationGroupBox` to add Cancel +
   Delete (VIEW).
9. **Guard tests:** THREE exist (`test_workflow_wizard_persistence_offscreen`, `test_pumpkin_wizard_offscreen`,
   `test_step_bar_widget_offscreen`) — keep all green; update `_WizardViewModule__{engine,cursor,tabWidget,
   nextButton}` → base `_…`, and `__shownPhases[__cursor]==METADATA` → `_plan[_cursor].phaseType==METADATA`.
10. **Edge — empty computed phase.** The predictive plan shows PROC/EVAL always; if a plugin's evaluation returns 0
    steps (weak signal), the old wizard *skipped* it but the plan shows an empty stop. **Fix:** prune an empty
    computed stop on arrival (auto-skip forward), else accept the degenerate-case difference. Recommend prune.

**B3 — rehome `DevMeasurementBenchViewModule` onto the base**
1. **Retire the fixed 4-page `QStackedWidget`** → render per-stop into the base's tab widget; the bench's
   `__buildProcessingPage`/`__runProcessing`/… become `_renderStop` dispatch (rebuilding tabs each render). This is
   what makes the cursor↔page misalignment impossible.
2. **Build a bench offscreen test FIRST** (none exists — §9b-22): instantiate `DevPluginExecutionView` on the
   virtual device; drive stops→chevron→Back/Next + a save round-trip. It is the only guard for B3.
3. **Plugin selector:** the bench overrides `getMainContainerWidgets` to add the `QComboBox`; `_resolvePlugin` =
   the selected entry; changing it restarts the run.
4. **Bench save is NEW behaviour** (D-save=yes): `_onFinish` = persist + go to **Settings** (leave-destination
   differs from the wizard's Home). Reuse the base's shared save.
5. **Raster tabs stay host-injected in B3** (plugin-declared rasters = Change G is M3/P3) — `_renderStop(PROCESSING)`
   adds them.
6. **Camera:** Back into ACQUISITION restarts the stream — via `_renderStop(ACQUISITION)`; dev-chrome
   (exposure/ROI/frames) stays via `CaptureView` flags + `decorateCapturePanel`.

**Cross-cutting**
- **Change F (single-step → no tab)** lands in the base `_renderCursor` (hide the tab bar when the stop rendered
  exactly one tab) — applies to both hosts at once.
- **Biggest risks:** B2's VIEW mode + guidance visuals (not covered offscreen → needs click-through); B3's stack
  retirement + first-ever bench save (guarded by the new bench offscreen test).
- **Scope call (D-b2-scope):** put metadata-form + save in the base during **B2** (recommended — the bench inherits
  them in B3) vs. keep them wizard-private and move in B3.

---

## 10. Host convergence — one plugin-execution view (the DRY end-state)  *(Edwin 2026-07-24)*

Edwin's deeper point: the **measurement bench** and the **end-user measurement view** should not be two classes —
they are *the same view* with one difference (the bench can *select* which plugin to run). DRY should apply.

**The two classes today:**
- **`WizardViewModule`** = the **end-user plugin-execution view**. Runs the session's *assigned* plugin
  (`session.getPluginCodeRef()`, WVM:147). Has save (`__saveNewRun`), the METADATA form, real capture (SM3).
- **`DevMeasurementBenchViewModule`** = the **master bench**. Runs an *arbitrarily selected* plugin
  (`__selectedEntry` over `PluginRegistry.availablePlugins(includeBenchOnly=…)`, DMBVM:240). No save, no metadata.

**They already share** `SpectralWorkflowEngine`, `WorkflowPhaseRenderer` + the visitor (content), `CapturePanel`
(acquisition), **and `StepBarWidget`** (the chevron). After §4 makes *navigation* generic too, the residual
difference is essentially **one thing: how the plugin is selected**. So the target (Edwin's framing) is **one base
class + two thin subclasses**:

```
AbstractPluginExecutionView (base — everything shared)
  owns:  engine · NavigationModel chevron+cursor · WorkflowPhaseRenderer content ·
         CapturePanel acquisition · METADATA form · save · Back/Next · guidance ·
         generic automation anchors (objectNames) so the Director can drive it
  abstract:  resolvePlugin() -> SpectralPlugin        ◄── the ONLY thing subclasses differ on
      │
      ├── EndUserPluginExecutionView   resolvePlugin() = the user's assigned plugin
      │       · 1 assigned  → auto-run it (no picker)
      │       · N assigned  → a picker LIMITED to the user's assigned set   (never a dev plugin)
      │
      └── DevPluginExecutionView   (= the "measurement bench")
              resolvePlugin() = a picker over ANY registered plugin (incl. benchOnly dev plugins)
```

- **Dev-chrome** (exposure / ROI / frames) is already **plugin-declared** through `CaptureView` flags, so it needs
  **no** subclass difference — the dev plugin turns it on, an end-user plugin leaves it off.
- **`resolvePlugin()` is the *headline* difference**, but honestly (per the impl rubber-duck §9b-4) the base also
  exposes a couple of small overridable hooks: the **"where do I go when I leave" destination** (end-user → Home;
  bench → Settings) — note **saving is now unified in the base** (D-save = yes, below), so only the *destination*
  differs, not whether it saves — and an optional **plugin-selector slot** (bench any-picker / end-user
  assigned-picker / none), plus the **guidance entry-gate** (convergence D4). The bench's raster-tab hook is **gone**
  (rasters are plugin-declared now, §4.7-G). Small, but real — the subclasses are thin, not empty.
- **Save lives in the base** (both persist — DRY). If master runs should *not* clutter the saved-runs list, that is
  a one-line overridable hook, not a fork (D-save).
- The `benchOnly` registry flag + the per-user *assigned set* enforce the selection scope (an end-user picker never
  offers a dev plugin).

**Why this is safe now (and wasn't before):** convergence D3 kept two nav skins because there was no shared nav
model. §4 *is* that model. Both classes already use `StepBarWidget` + engine + renderer + `CapturePanel`; once both
compute their chevron from `NavigationModel.stops()`, they are near-duplicates whose only diff is `resolvePlugin()`.
Extracting the base is then mechanical, not risky.

**The Director becomes generic, too (postponed but designed-for).** The Director screencast is a *separate,
postponed* concern — but the goal is that it can drive **both** subclasses conveniently. That falls out of the base:
because both subclasses inherit the same navigation + the same **automation anchors** (stable `objectName`s on the
chevron, Back/Next, capture, metadata fields, publish — doc-automation §16), **one Director script drives either
subclass identically**. Requirement on the design: put those anchors on the **base**, not per-subclass.

**Staging — base extraction FIRST (Edwin 2026-07-24).** Rather than build the DEV behaviour on the bench and merge
later (throwaway work), extract the base **first**, as a *behaviour-preserving refactor*, then add the DEV behaviour
once on the base. Discipline: **refactor with no visible change, then add behaviour.**
1. **M1 — nav model (SDK, additive/safe):** `NavigationPolicy` + `NavStop` + `NavigationModel.stops()`. No host
   change; every plugin on the default policy.
2. **M2 — base extraction, behaviour-preserving:** create `AbstractPluginExecutionView` that renders chevron +
   content from `NavigationModel` and **fully honours** the model (auto-advance, step-chevrons, metadata stop) —
   but since every current plugin is on the **default** policy, **nothing visible changes**. Re-home
   `WizardViewModule` → `EndUserPluginExecutionView` (behaviour byte-unchanged; offscreen suite green) and
   `DevMeasurementBenchViewModule` → `DevPluginExecutionView` (retire the fixed 4-page stack). The bench **inherits
   the METADATA form + save** from the base — so Change C's host side and generic Director anchors come *for free*.
   (Save turning ON for the bench is a *desired* change per D-save = yes, but it is exercised only once DEV declares
   the flow in M3 — see §9b-4a.)
3. **M3 — DEV behaviour via policy + content:** DEV `navigation()` → AUTO_ADVANCE + step-chevrons, DEV `metadata()`
   (the three fields), `CaptureView.croppedPreview`, and the temporary toggle — all of which merely *activate* the
   capability M2 already built. Then remove the toggle (X).

Why base-first is safe here: M2 is a pure refactor (default policy everywhere ⇒ no behaviour change), guarded by the
existing offscreen tests; the wizard hero path is touched **without** changing what it does. The DEV behaviour (M3)
then lands once and both subclasses are capable.

**Why M1 precedes M2 (not a feature jumping the queue).** The base is *defined* as "render from
`NavigationModel.stops()`", so the model must exist first — M1 is the data/contract the base is built of, not a
competing milestone. More importantly, the two views navigate *differently today* (wizard lazy `__nextVisibleAfter`
vs. bench eager state machine); extracting a shared parent before unifying navigation would force the parent to
absorb **both** skins — the messy merge we rejected. The `NavigationModel` **replaces both mechanisms with one**,
turning M2 into a clean *lift* rather than a *merge*. M1 is also tiny, pure, and unit-tested, so it de-risks M2
(extract against an already-proven model). Read M1 + M2 as one "base extraction" theme — M1 defines the model, M2 is
the extraction proper; nothing DEV-specific happens until M3.

**Sub-decisions:**
- **D-save — RESOLVED = YES (Edwin 2026-07-24):** the measurement bench **also saves** its runs, like the end-user
  view. Save lives in the base and is **on for both** subclasses; the only per-subclass leftover is the *leave
  destination* (Home vs Settings). Consequence → the saved-runs note below.
- **D-policy-name — RESOLVED = `WorkflowPolicy`** (Edwin's lean; alternatives that were on the table: `PluginPolicy`,
  `PresentationPolicy`, `BehaviourPolicy`/`PluginBehaviour`, `ExecutionPolicy`).
- **D-assigned-source (deferred):** where the end-user's *assigned* plugin set comes from for the N-assigned picker —
  ties to the plugin-distribution assignment model (`SPEC_plugin_distribution.md` B5) + `SpectrometerSetup`.

**Saved-runs (deferred, Edwin):** now that the bench saves too (D-save = yes), the saved-runs list will hold master
runs — Edwin's fix is a **plugin selector/filter on the saved-runs list** (filter runs by plugin). A *separate* later
issue, parked here, not part of this work.

---

## 11. Out of scope / unchanged
- Capture **mechanics** (burst, AE algorithm, ROI computation, calibration) — A changes only what the preview
  *shows*.
- Evaluation maths, PDF report, LIMS publishing, the **workflow→phase→step model** (D is view-only) — unchanged.
- **Bench run-persistence** and **wizard navigation adoption** — deferred (§2, §8).
- Phase **order**, DB/schema — unchanged; `NavStop`/`NavigationModel`/`NavigationPolicy`/`croppedPreview` are
  runtime/declared.

---

## 12. Implementation phases (when Edwin says go — NOT yet implemented)

Ordered **base-first** (§10): M1 the model, M2 the behaviour-preserving base extraction, M3 the DEV behaviour.
Test legend: **U** = offscreen unit (pure, no Qt) · **W** = offscreen widget (Qt offscreen, virtual device) ·
**R** = rig (real ELP camera) · **E** = eyeball (visual confirmation).
```
┌──────┬─────┬────────────────────────────────────────────┬──────────────────────────────────────────────┬──────────┐
│ Mil. │ Ph. │ Change                                      │ What can be tested                             │ Test kind│
├──────┼─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│ M1 ✅│ S0  │ NavigationMode + NavigationPolicy +         │ stops() unit tests: per-phase / step-expand /  │ U        │
│ nav  │     │ WorkflowPolicy container; policy() default; │ skip-empty / metadata-as-step; stops() SAME    │          │
│ model│     │ NavStop + NavigationModel.stops();          │ under STEP vs AUTO_ADVANCE (§9b-21); every     │          │
│      │     │ + MetadataFormView (Change E)               │ existing plugin default ⇒ unchanged; imports   │          │
├──────┼─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│ M2   │ B1  │ AbstractPluginExecutionView renders from    │ chevron built from stops(); correct stop       │ W        │
│ base │     │ stops(); metadata materialised as a step;   │ renders; Back/Next walk; metadata form renders │          │
│      │     │ save in base; Director objectName anchors   │ + edits + saves; anchors present               │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ B1f │ Single-step phase → no tab (Change F),      │ single-step phase (metadata/PUBLISHING/1-step  │ W (+E)   │
│      │     │ general both hosts                          │ EVAL) has NO QTabWidget; multi-step keeps tabs │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ B2  │ Wizard → EndUserPluginExecutionView         │ existing wizard offscreen persistence+nav      │ W        │
│      │     │ (resolvePlugin = assigned)                  │ tests stay GREEN (guard); flow unchanged bar F │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ B3  │ Bench → DevPluginExecutionView (any picker);│ NEW bench offscreen nav harness (virtual dev): │ W        │
│      │     │ retire fixed stack; save ON; leave→Settings │ stops→chevron→Back/Next; save round-trip;      │          │
│      │     │ (§9b-22 harness is a B3 deliverable)        │ picker present; leave-destination = Settings   │          │
├──────┼─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│ M3   │ P1a │ DEV policy() → AUTO_ADVANCE + step-chevrons │ [Reference][Sample] are 2 chevrons; 1 Next     │ W        │
│ DEV  │     │ (nav + wiring)                              │ (last ACQ)→METADATA→PUBLISHING; Back reveals    │          │
│      │     │                                             │ populated PROC/EVAL; setActiveStep switches     │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P1b │ Role-lift camera behaviours (hide roleTabs, │ live feed on the active role; exposure-lock on │ R        │
│      │     │ exposure-lock-on-Sample, shared camera)     │ Sample reused from Reference; guidance cue      │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P2  │ DEV metadata() = 3 fields                   │ METADATA step appears; form after measuring;   │ W        │
│      │     │                                             │ values persist (round-trip)                     │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P3  │ DEV rasters as SpectrumCaptureView (Change  │ raster tabs plugin-declared; host fills .image │ W (+E)   │
│      │     │ G); retire host raster hook                 │ from a (virtual) frame; no host dev-tab inject │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P4a │ croppedPreview flag → setCropToRoi plumbing │ flag flips the mode; AE brightness path        │ W        │
│      │     │                                             │ unchanged; no-ROI ⇒ full-frame fallback         │          │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P4b │ fitInView-to-ROI actual crop (box hide)     │ preview shows ONLY the ROI strip               │ R/E      │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ P5  │ SIMPLIFIED_NAVIGATION temporary toggle      │ OFF ⇒ STEP flow; ON ⇒ should-be — both offscr  │ W        │
│      ├─────┼────────────────────────────────────────────┼──────────────────────────────────────────────┼──────────┤
│      │ X   │ CLEANUP: remove toggle after rig sign-off   │ DEV permanently should-be; no OFF branch left  │ W        │
└──────┴─────┴────────────────────────────────────────────┴──────────────────────────────────────────────┴──────────┘
```
**Testability shape:** M1 is **pure unit** (U). M2 is entirely **offscreen widget** (W) on the virtual device —
including the new bench harness (§9b-22) — so the whole base extraction is guarded without hardware. In M3 only
**P1b** (the role-lift camera behaviours) and **P4b** (the visual crop) need the **rig**; everything else — the nav,
the metadata, the raster declaration, the flag plumbing, the toggle — is offscreen. So real-hardware exposure is two
small, isolated slices at the very end.
**M2 is the crux:** it implements the model-honouring host in the base; for **multi-step** phases on the **default**
policy nothing visible changes (a pure refactor guarded by the offscreen suite), while Change F (single-step → no
tab) and D-save (bench now saves) are the *intended* visible changes, landed explicitly. M3 flips the DEV policy +
content on. The old cursor↔stack-misalignment risk never arises — the base renders per-stop, there is no fixed stack.

**Postponed (separate concern):** the Director screencast — enabled generically by the base's automation anchors
(§10), verified when that milestone runs. **Deferred:** `selection=ASSIGNED` N-assigned picker (D-assigned-source);
saved-runs plugin filter.
