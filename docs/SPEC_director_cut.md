# SPEC — "Director's Cut" bench screencast (two-sweep narrated run)

> **STATUS 2026-07-25 — COMPLETE + RIG-VERIFIED (Edwin).** E1·E2·E3·E4 offscreen-green (267 spectracsPy + 23
> plugins); **S1·S2 rig-verified** — the two-sweep video runs end-to-end on the bench (capture → jump → ö-typed
> metadata → verdict pointing → publish; then Back into Evaluation for the six pointed Metrics fields + Absorption
> (bands) + Report, and Back into Processing for Spectra + Absorption). E1 metadata-field objectNames
> (`PluginExecutionView.metadata.<name>`); E2 `workflowItemObjectName` slug + objectNames on the gauge (`visitGauge`)
> and each metric row (`visitMetricField`); E3 Director helpers `point()` / `visit_tab()` / unicode `type_text`
> (xdotool); E4 `resolveByObjectName` (visible-preferring) behind `DocModeUdpService.__lookup`; S1/S2 = the two-sweep
> `measurement_bench.py` rewrite (retired the stale one). Tests: `test_director_cut_enablers.py` (E2+E4) +
> metadata-objectName case in `test_plugin_execution_view_offscreen.py`.

A definitive narrated screencast of the DEV **measurement bench** running end-to-end, in **two sweeps within one
recording**: a **forward sweep** that *does* the measurement (and rides the should-be auto-advance straight to the
verdict), then a **backward sweep** that *explains* the phases the jump skipped. Supersedes the existing
`automation/scenarios/measurement_bench.py`, which is **stale** against the post-M2 code (see §6). Extends the Director
harness (`automation/automation_director.py`, `SPEC_doc_automation.md`).

## 1. Why two sweeps (the auto-advance forces it)

The DEV plugin is now permanently **should-be** (AUTO_ADVANCE + Reference/Sample step-chevrons, §7b/X). After both
roles are captured, **Next jumps from the Sample boundary straight to Details (METADATA)** — Processing and Evaluation
are *skipped forward*, reachable only by **Back** (Option C: Back no longer invalidates, so their computed content
survives). A single forward walk of every phase — what the old scenario did — is therefore impossible. The two-sweep
structure turns that into a feature:

- **Sweep 1 — "do it" (forward):** capture → *jump* → Details (enter dummy data) → Verdict/Publish (explain + publish).
- **Sweep 2 — "explain it" (backward):** Back into Evaluation (Metrics · Absorption (bands) · Report), then Back into
  Processing (Spectra · Absorption). The record ends there.

One continuous recording; two clearly-commented sections in `run(d)`.

## 2. Sweep 1 — forward beat sheet

| # | Beat | Director calls (targets in §5) | Right-panel narration |
|---|---|---|---|
| 1 | Cover + login + open bench | `cover` → `login("bench")` → `cover(AGENDA)` → human-gate (calibrated rig) → `nav("DevMeasurementBenchViewModule")` | use-case + agenda |
| 2 | **Reference** chevron (step 0; role-tabs hidden — chevron IS the selector) | `doc(phase="Acquisition")`; narrate; human-gate (place blank); `click(CAPTURE)`; `wait_capture(CAPTURE)`; `dismiss()` | explain the reference/blank |
| 3 | Advance to **Sample** chevron | `wait_ready(NEXT, enabled)`; `click(NEXT)` *(Reference→Sample — NOT `roleTabs`)* | — |
| 4 | **Sample** chevron | narrate; human-gate (swap sample); `click(CAPTURE)`; `wait_capture` | explain the sample |
| 5 | **Jump** to Details | `wait_ready(NEXT, enabled)`; `click(NEXT)` *(boundary → auto-advance jump to Details)* | "measurement done — now label it" |
| 6 | **Details** (METADATA) form | `doc(phase="Details")`; `click(MD_TITLE)`; `type_text("Kernöl-20260724A")`; `click(MD_TEMP)`; `type_text("122")` *(dateOfRoasting left at today's default)* | explain the metadata fields as they're filled |
| 7 | Advance to **Verdict/Publish** | `click(NEXT)` *(Details→Verdict/Publish)* | — |
| 8 | **Verdict/Publish** (single step; tab bar hidden) | `doc(phase="Verdict/Publish")`; narrate the verdict badge; `click(SEND_LIMS)`; `sleep`; screenshot | explain the verdict, then the publish-to-LIMS action |

## 3. Sweep 2 — backward beat sheet

**Back is always exactly ONE chevron stop — it never jumps** (only the Next at the acquisition boundary jumps, §1).
Chevron: `[Reference, Sample, Processing, Evaluation, Details, Verdict/Publish]`. From Verdict/Publish (5): Back→Details
(4), Back→Evaluation (3) — two single steps; then one more Back→Processing (2).

| # | Beat | Director calls | Narration |
|---|---|---|---|
| 8b | **Bridge** (still on Verdict/Publish, before the first Back) | `narrate(...)` | "the end-user flow is done; step Back any time to see the detail" (§13) |
| 9 | Back → Details → Back → **Evaluation** | `click(BACK)` ×2 | "let's look at what the measurement produced" |
| 10 | **Metrics** tab (index 0, shown on entry) — **point + explain** SIX fields | `visit_tab(TABS, "Metrics")`; then for each field in order — **Verdict** (gauge), **Intrinsic · despiked**, **Intrinsic-perceived · despiked**, **Soret · 440–460 nm**, **Q · 560–580 nm**, **Pigment ratio** — glide the cursor to its item objectName (E2) then `narrate` | one narration line per field (§4 map), cursor on the field |
| 11 | **Absorption (bands)** tab (index 1) | `go_to_tab(TABS, 1)`; narrate | explain the band-marked A(λ) spectrum |
| 12 | **Report** tab (index 2) | `go_to_tab(TABS, 2)`; narrate | explain the one-click embedded-data PDF |
| 13 | Back → **Processing** | `click(BACK)` | "and the raw processing behind it" |
| 14 | **Spectra** tab (index 0) | `go_to_tab(TABS, 0, activate=False)`; narrate | reference-vs-sample overlay |
| 15 | **Absorption** tab (index 1) | `go_to_tab(TABS, 1)`; narrate | A(λ) = −log₁₀(S/R) |
| 16 | End | screenshot; `finish` | — |

**Deliberately skipped** (Edwin): the Evaluation `(dev)` tabs (Metrics (dev), Absorption (bands, dev)) and the
Processing Transmission / Reference image / Sample Image / Absorption (dev) tabs. So step-tabs are visited by
**explicit `go_to_tab`**, NOT `walk_tabs` (which would walk *every* tab). See D-subset.

## 4. Metrics field → view-model map (for the on-tab narration)

The six explained fields live in the **"Metrics"** tab (the new PB-band `EvaluationResult`, Evaluation index 0):

| Edwin's name | View-model in the tab | Kind | objectName (E2 slug) | Unique in tree? |
|---|---|---|---|---|
| **Verdict** | `RoastGaugeView` (first item; render = BAND\|LABEL\|SWATCH; caption `"Verdict"`) | gauge | `workflowItem.verdict` | ✓ (only gauge on the tab) |
| **Intrinsic despiked** | `MetricFieldView("Intrinsic · despiked")` | colour chip | `workflowItem.intrinsic_despiked` | ✗ dup in Metrics (dev) |
| **Intrinsic-perceived despiked** | `MetricFieldView("Intrinsic-perceived · despiked")` | colour chip | `workflowItem.intrinsic_perceived_despiked` | ✗ dup in Metrics (dev) |
| **Soret** | `MetricFieldView("Soret · 440–460 nm")` | metric row | `workflowItem.soret_440_460_nm` | ✓ |
| **Q** | `MetricFieldView("Q · 560–580 nm")` | metric row | `workflowItem.q_560_580_nm` | ✓ |
| **pigment ratio** | `MetricFieldView("Pigment ratio")` | metric row | `workflowItem.pigment_ratio` | ✓ |

**Slug rule (shared by E2 renderer + the scenario):** lowercase, every run of non-alphanumeric chars → one `_`,
strip leading/trailing `_`. The renderer sets the objectName; the scenario references the exact strings above (or
computes the same slug). The two **must** agree — that coupling is the field-pointing contract.

**D-point RESOLVED = point each field (Edwin 2026-07-25):** the Director **glides the cursor to each named field**
(the Verdict gauge and each listed chip/row) and narrates it — the viewer sees exactly which field is being explained,
not a narration over the whole tab. This requires per-item objectNames on the rendered view-models (**E2**, now core,
§7): the gauge and each `MetricFieldView` get a stable objectName keyed by label, and the scenario `go_to`-points each
before narrating. (The old `describe_metrics` narrated blind; this is the upgrade Edwin asked for.)

## 5. objectName targets (post-M2 — the current names)

| Alias | objectName | Status |
|---|---|---|
| `CAPTURE` | `CapturePanel.captureButton` | ✓ current |
| `INNER_TABS` | `CapturePanel.innerTabs` (Spectrum=0, Image=1) | ✓ current (C2 order) |
| `NEXT` | **`PluginExecutionView.nextButton`** | ✓ (old scenario used `DevMeasurementBenchViewModule.nextButton` — STALE) |
| `BACK` | **`PluginExecutionView.backButton`** | ✓ current |
| `TABS` | **`PluginExecutionView.tabWidget`** (all phases render into this ONE widget) | ✓ (old scenario used per-phase `processingTabs`/`evaluationTabs`/`publishingTabs` — STALE) |
| `SEND_LIMS` | `DevMeasurementBenchViewModule.sendToLimsButton` | ✓ current |
| `MD_TITLE` / `MD_TEMP` | **`PluginExecutionView.metadata.title` / `.temperature`** | ✗ **need adding (E1)** |
| role tabs | `CapturePanel.roleTabs` | **hidden in should-be** — do NOT use; advance via `NEXT` |

## 6. Why the old `measurement_bench.py` is stale

- **Retired objectNames:** `DevMeasurementBenchViewModule.{nextButton, processingTabs, evaluationTabs, publishingTabs}`
  vanished when M2 rehomed the bench onto `AbstractPluginExecutionView` (one `PluginExecutionView.tabWidget`, base
  nav buttons). `d.click(NEXT)` / `walk_tabs(PROCESSING_TABS)` would fail.
- **Forward-linear assumption:** it does `click(NEXT)` Acquisition→Processing→Evaluation→Publishing. Under
  AUTO_ADVANCE the boundary Next jumps to Details, so that walk no longer matches the nav.
- **Role switching via `roleTabs`:** in should-be the role-tabs are hidden (chevron is the selector); Reference→Sample
  is a `NEXT`, not a `go_to_tab(ROLE_TABS, …)`.
- **Stale labels:** `EVAL_METRICS`/`TAB_NARRATION` reference the pre-§7b labels (Greenness G, "Reference raster", …).

## 7. Impl enablers (needed before the scenario can run — DESIGN only here)

- **E1 (required) — metadata-field objectNames.** In `AbstractPluginExecutionView._buildMetadataForm`, set
  `widget.setObjectName("PluginExecutionView.metadata.%s" % name)` per field, so the Director can focus+type the
  title/temperature. Benefits both hosts. Tiny; offscreen-testable (assert the objectName exists).
- **E2 (required — D-point resolved) — per-item objectNames in `QtWorkflowRenderer`.** So the Director can glide the
  cursor to an *individual* Metrics field (the Verdict gauge and each listed chip/row), each rendered view-model
  widget gets a stable objectName keyed by label, e.g. `setObjectName("workflowItem.%s" % slug(label))` in
  `visitGauge` / `visitMetricField` (gauge caption or metric label). Then the scenario points via a glide-only
  `go_to`/`click(...,activate=False)`-style locate on that objectName before narrating. Touches the shared renderer,
  but additively (objectNames are inert for existing consumers). Offscreen-testable (assert the objectNames exist);
  the cursor-glide itself is rig.
- **E3 — Director harness helpers (three small additions to `automation_director.py`):**
  - `visit_tab(name, label)` — resolve the index via `d.tabs(name)` and `go_to_tab` it (name tabs by label; skip the
    already-shown one). Replaces the wrong `walk_tabs` for our curated subset.
  - `point(name)` — locate + glide the cursor to a widget and STOP (no activate). Needed to point at a metric
    label/gauge without clicking it (a click would pop a tooltip or do nothing useful). `click` always activates, so
    a distinct primitive is required.
  - `type_text` unicode fix — the title `Kernöl-20260724A` contains **ö**; `pyautogui.write` is ASCII-only / layout-
    dependent and will drop or mangle it. Route `type_text` (or a `type_unicode`) through **`xdotool type`** (or a
    clipboard paste), which emits arbitrary unicode reliably.
- **E4 (recommended hardening) — visible-preferring lookup in `DocModeUdpService.__lookup`.** Today it uses
  `findChild` (FIRST match) then rejects it if invisible. For our scenario it happens to work (the Metrics (new) tab is
  index 0, so its chip is first in the tree AND visible when we point). But the duplicated chips make that a
  tree-order accident — make `__lookup` iterate `findChildren(QWidget, name)` and return the **visible** one, so
  pointing is correct regardless of tab order. ~5 lines; strictly a robustness upgrade.

## 8. Decisions — ALL RESOLVED (Edwin 2026-07-25)

- **D-file → ONE version, rewrite `measurement_bench.py` in place.** No separate `director_cut.py`, no stale old code
  kept — the two-sweep scenario *is* the bench screencast (`bench.sh` keeps working).
- **D-point → point each field.** The Director glides the cursor to the Verdict gauge and each named chip/row and
  narrates it (E2 is core, not optional). Edwin: the verdict and the other required fields must be *explained*, not
  narrated blind.
- **D-subset → add the `visit_tab(name, label)` helper** (E3). An impl detail of the harness; folded into the build.
- **D-publish-live → just click.** `click(SEND_LIMS)` with no human-confirm gate; the operator ensures SENAITE is up
  (rig responsibility, not a scripted branch).
- **D-dateOfRoasting → leave the QDateEdit default (today).** Only title + temperature are typed.

## 9. Rubber-duck — what would bite

1. **The jump is the whole reason for two sweeps.** If anyone "fixes" sweep 1 to click through every phase forward,
   it breaks — the boundary Next *jumps*. Sweep 1 must go capture → capture → **one Next = jump** → Details. The
   Processing/Evaluation content is reached only in sweep 2 via Back. ⚠
2. **Back must not re-capture.** Option C keys the re-jump on a *fresh capture*; sweep 2 only navigates (no capture),
   so the computed phases stay intact and Back-viewable. Good — but if the scenario ever re-touches the capture button
   during sweep 2 it would invalidate + re-arm the jump. Don't. ✔
3. **Role advance is `NEXT`, not `roleTabs`.** Should-be hides the role-tabs; scripting `go_to_tab(ROLE_TABS,…)` would
   locate a hidden widget. Reference→Sample = `click(NEXT)` once Reference is captured. ⚠
4. **One tab widget for all phases.** `PluginExecutionView.tabWidget` is cleared+rebuilt per stop, so the *same*
   objectName yields Processing tabs, then Evaluation tabs, depending on the current cursor. `go_to_tab(TABS, i)`
   indexes the CURRENT phase's tabs — correct, but the scenario must be on the right phase first. ⚠
5. **Metadata typing needs focus.** `type_text` types wherever focus is; without E1 objectNames the Director can't
   `click` the field to focus it first. E1 is the one hard prerequisite. ⚠
6. **Tab indices vs labels.** Evaluation = [Metrics, Absorption (bands), Report, Metrics (dev), Absorption (bands,
   dev)]; Processing = [Spectra, Absorption, Transmission, Reference image, Sample Image, Absorption (dev)]. The
   wanted indices (0/1/2 and 0/1) are stable today, but a future reorder would silently point at the wrong tab →
   prefer D-subset's `visit_tab(label)`. ⚠
7. **Verdict is a gauge, not a MetricFieldView.** D-point is taken, so **E2 must also objectName the `RoastGaugeView`
   in `visitGauge`** (keyed off its caption), not just the metric rows — else the cursor can't point at the Verdict. ⚠
8. **`walk_tabs` is the wrong primitive here.** It walks *every* tab; Edwin wants a curated subset (skips the (dev)
   tabs, Transmission, the rasters). Use explicit `go_to_tab`/`visit_tab`. ✔
9. **Real hardware + human gates.** Reference/Sample are physical cuvette swaps → keep `wait_for_human` gates; the
   bench also refuses a virtual/uncalibrated device (a human-confirm gate before `nav`). Unchanged from the old
   scenario. ✔
10. **`d.doc(phase=…)` label must match the chevron.** Post-rename the phase captions are "Details" / "Verdict/Publish"
    (the chevron labels) — pass those exact strings (already fixed in the current scenario's OUTLINE). ✔
11. **Camera handoff / single recording.** The `cover` card after login performs the camera handoff so Home is never
    filmed (§18.1); the two sweeps are one `run(d)` so `start/stop_recording` brackets the whole thing. ✔

## 10. Impl phases (when Edwin says go — NOT yet implemented).  U=unit · W=offscreen-widget · R=rig

```
┌────┬────────────────────────────────────────────────┬──────────────────────────────────┬──────────────────────────┬────┐
│ Ph │ Task                                           │ Files                            │ Verifiable               │Kind│
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ E1 │ metadata-field objectNames                     │ AbstractPluginExecutionView      │ objectName present per    │ W  │
│    │ ("PluginExecutionView.metadata.<name>")        │ ._buildMetadataForm              │ field (offscreen)         │    │
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ E2 │ per-item objectNames "workflowItem.<slug>" on  │ QtWorkflowRenderer               │ objectName per gauge/     │ W  │
│    │ gauge + metric rows (+ shared slug rule)        │ (visitGauge, visitMetricField)   │ metric row (offscreen)    │    │
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ E3 │ harness: visit_tab(name,label) + point(name) + │ automation_director.py           │ helpers unit-exercisable; │ W  │
│    │ unicode type_text (xdotool) for the ö title    │                                  │ ö types on rig            │    │
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ E4 │ (hardening) __lookup returns the VISIBLE match │ DocModeUdpService.__lookup       │ dup-label locate resolves │ W  │
│    │ (findChildren) not the first                   │                                  │ to the shown one          │    │
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ S1 │ Scenario sweep-1 forward (capture ×2 → jump →  │ automation/scenarios/            │ rig: live app run         │ R  │
│    │ Details type → Verdict/Publish → click publish)│ measurement_bench.py (rewrite)   │                           │    │
├────┼────────────────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┼────┤
│ S2 │ Scenario sweep-2 backward: Back→Evaluation      │ same scenario file               │ rig: tabs land, each field│ R  │
│    │ (point+explain 6 Metrics fields, Absorption    │                                  │ pointed + narrated, subset│    │
│    │ (bands), Report) → Back→Processing (Spectra,   │                                  │ only                      │    │
│    │ Absorption)                                    │                                  │                           │    │
└────┴────────────────────────────────────────────────┴──────────────────────────────────┴──────────────────────────┴────┘
```
Sequence: **E1 → E2 → E3 → E4 → S1 → S2**. E1–E4 are offscreen/unit-testable (the code enablers); S1/S2 are inherently
rig (real camera + LIMS + video). E4 is a recommended robustness step, not a hard blocker for *this* scenario.

## 11. Impl rubber-duck — what would bite while coding

1. **Duplicate objectNames (the twin chips).** `Intrinsic · despiked` / `Intrinsic-perceived · despiked` exist in BOTH
   the Metrics and Metrics (dev) tabs (the 10-chip set is duplicated). `locate` uses `findChild` (first match) + a
   visible check — it happens to resolve correctly because Metrics is tab 0 (first in the tree, visible when we
   point). Fragile-by-accident → **E4** makes it correct-by-construction (return the visible match). ⚠
2. **`ö` won't type.** `pyautogui.write("Kernöl-…")` drops/mangles the umlaut. **E3** routes typing through
   `xdotool type` (or clipboard). Verify on the rig with the German layout. ⚠
3. **Pointing needs a non-clicking primitive.** `click` always activates; clicking a metric label pops its tooltip,
   clicking a plain widget may no-op or error in `__activate`. Add `point(name)` = locate + glide only. ⚠
4. **The slug contract couples two files.** E2's renderer slug and the scenario's field objectNames must match
   exactly (`Soret · 440–460 nm` → `soret_440_460_nm`). Define the slug once; list the exact strings (§4). A silent
   mismatch = a locate failure mid-video. ⚠
5. **E2 is app-wide but inert.** Adding `setObjectName` in `visitGauge`/`visitMetricField` touches EVERY rendered
   gauge/metric across the app (wizard, pumpkin, LIMS badge). objectNames are inert for existing code — but confirm no
   existing test asserts an *empty* objectName, and that two metrics with the same label on the *same* tab don't
   collide (none do today; a defensive `findChildren`-visible lookup (E4) covers future ones). ✔
6. **The verdict appears twice, never at once.** `workflowItem.verdict` is set on the Metrics-tab gauge AND the
   PUBLISHING badge gauge (both caption `"Verdict"`). They never coexist in the tree (the tab widget is rebuilt per
   stop), so each is unambiguous when shown — pointing at the verdict works in both sweep-1 (publish badge) and
   sweep-2 (Metrics gauge). ✔
7. **Metadata form is rebuilt each render.** `_buildMetadataForm` runs on every METADATA render, so E1's objectNames
   are re-set each time — consistent, no stale widget. The Director must locate AFTER the jump lands on Details
   (the form doesn't exist before). ✔
8. **`wait_capture` per role.** Reference auto-exposes (long, button disabled the whole time); Sample doesn't
   (only `__capturing` gates). `wait_capture` already handles both edges — reuse it, don't hand-roll a wait. ✔
9. **Next-gate timing.** After each capture, `wait_ready(NEXT, enabled=True)` before clicking Next — the boundary
   Next enables only once BOTH roles are captured; the Reference→Sample Next enables once Reference is captured. ⚠
10. **`describe_metrics`/`EVAL_METRICS`/`TAB_NARRATION` are dead.** The rewrite drops them (pre-§7b labels). Fresh
    narration keyed to the new labels + the six pointed fields. ✔

## 12. Storyboard — how the run looks (chevron cursor + screen + narration)

```
Chevron (6 stops):   Ref · Smp · Proc · Eval · Det · V/P
                     (Ref/Smp are step-chevrons; the rest are phase stops)

════════ SWEEP 1 — "DO IT" (forward; the Next at the Smp boundary JUMPS) ════════

  cursor   chevron position                on screen / action            right doc panel
  ──────   ─────────────────────────────   ───────────────────────────   ─────────────────────────
  Ref ►    [Ref] Smp  Proc Eval Det  V/P    place blank → CAPTURE          "the reference / isopropanol blank"
           · Next (enabled once Ref shot) ↓
  Smp ►     Ref [Smp] Proc Eval Det  V/P    swap sample → CAPTURE          "the sample = oil in the blank"
           · Next (both shot) ⤵⤵ JUMP over Proc+Eval
  Det ►     Ref  Smp  Proc Eval[Det] V/P    type title=Kernöl-20260724A    "measurement done — now label it"
                                            type temperature=122            (date left at today's default)
           · Next ↓
  V/P ►     Ref  Smp  Proc Eval Det [V/P]   point ► Verdict badge          "green=fresh, brown=over-roasted"
                                            click PUBLISH TO LIMS           "…sent to the lab's LIMS"

════════ SWEEP 2 — "EXPLAIN IT" (backward; each Back = exactly ONE stop) ════════

  V/P ►     Ref  Smp  Proc Eval Det [V/P]   (bridge)                       "done — step Back for the detail"
           · Back ↑
  Det ►     Ref  Smp  Proc Eval[Det] V/P
           · Back ↑
  Eval►     Ref  Smp  Proc[Eval]Det  V/P    tab: Metrics                   point+explain each, in order:
                                              ► Verdict (gauge)              "the roast-ampel verdict"
                                              ► Intrinsic · despiked          "intrinsic colour, spikes removed"
                                              ► Intrinsic-perceived·despiked  "…as the eye would see it"
                                              ► Soret · 440–460 nm            "blue pigment band"
                                              ► Q · 560–580 nm                "green pigment band"
                                              ► Pigment ratio                 "Soret/Q — the discriminator"
                                            tab: Absorption (bands)         "the band-marked A(λ) spectrum"
                                            tab: Report                     "one-click PDF, data embedded"
           · Back ↑
  Proc►     Ref  Smp [Proc]Eval Det  V/P    tab: Spectra                   "reference vs sample, overlaid"
                                            tab: Absorption                "A(λ) = −log₁₀(S/R)"
                                            ── END (finish recording) ──

Skipped on purpose: Eval's (dev) tabs; Proc's Transmission / Reference image / Sample Image / Absorption (dev).
```

## 13. Narration copy (draft — the right-panel "why" hints)

Register (SPEC_doc_automation §16.0): the app's own status-bar coach line carries the terse imperative; these doc-panel
hints carry the narrated *why* — never an echo. Dwell auto-scales with word count.

**Opening summary card (the `cover` AGENDA — Edwin: surface the verdict + Ampel here):**
```
AGENDA = [
  "Measure a real pumpkin-seed oil on a real spectrometer, end to end.",
  "Get a roast VERDICT — the Roast Ampel: green for a fresh oil, brown for an over-roasted one.",
  "See the analytical metrics the verdict is built on.",
  "Generate a PDF report with all the spectral data embedded — ready to send to a lab's LIMS.",
]
use_case = "From a real sample to a lab-ready roast verdict, on the bench."
```
(The gauge is genuinely green→brown — classes "good — green" / "probably too brown", one threshold at 4.4
(recalibrated for the 2026 oils, was 2.8); no amber/red. Narration matches the on-screen colours.)
```
```

**Sweep 1 — do it:**
| Beat | Hint |
|---|---|
| Acquisition | "First we capture two spectra — a reference blank, then the sample. Everything is measured against the reference." |
| Reference | "The reference is pure isopropanol in the cuvette — no oil. It's the 100 % baseline; whatever the oil absorbs shows up relative to this." |
| Sample | "The sample is that same solvent with the pumpkin-seed oil dissolved in. The difference between the two spectra is the whole measurement." |
| (after Sample Next → jump) | "Measurement done. The bench jumps straight to the summary — a details form, then the verdict. We'll come back for the analysis." |
| Details (form) | "A few labels for the record — they travel with the run and into the report." |
| · typing title | "The title identifies the batch — here, Kernöl-20260724A." |
| · typing temperature | "And the temperature the oil was roasted at — 122 °C." |
| Verdict badge | "The headline: the Roast Ampel — the roast verdict, read straight from the pigment ratio. Green means a fresh, well-roasted oil; brown means over-roasted." |
| Publish | "One click sends this measurement and its PDF report to the lab's LIMS as a new sample." |
| **Bridge → sweep 2** | "That's the whole end-user flow — measure, verdict, publish. But nothing is hidden: an interested user can step Back through the phases any time to see the detail behind the verdict." |

**Sweep 2 — explain it:**
| Beat / field | Hint |
|---|---|
| (Back into Evaluation) | "Now the analysis behind that verdict — the numbers the Ampel is built on." |
| ► Verdict (gauge) | "The verdict again as the analytical gauge — the marker rides the pigment-ratio scale, from green (fresh) down to brown (over-roasted)." |
| ► Intrinsic · despiked | "The oil's intrinsic colour — what it actually absorbs — with the narrow instrument spikes removed." |
| ► Intrinsic-perceived · despiked | "The same colour flipped to how the eye would perceive it — the green a person sees." |
| ► Soret · 440–460 nm | "The Soret band: blue-light absorption from the green pigment. A fresh oil absorbs strongly here." |
| ► Q · 560–580 nm | "The Q band: the green pigment's second fingerprint, in the yellow-green." |
| ► Pigment ratio | "Soret over Q — the one dilution-invariant number that separates a green oil from a browned one. This drives the Ampel." |
| Absorption (bands) | "The absorbance spectrum with those bands marked — the pigment features the metrics read." |
| Report | "The one-click PDF: every spectrum, metric and the verdict on one page, raw data embedded for the lab." |
| (Back into Processing) | "And underneath it all — the raw processing." |
| Spectra | "The two captured spectra overlaid, reference against sample, before any maths." |
| Absorption | "Turned into absorbance, A(λ) = −log₁₀(sample / reference): the oil's absorption bands stand out as peaks." |

Copy is a draft — tune wording on the rig; the structure (which hint on which beat/field) is what the scenario wires.
