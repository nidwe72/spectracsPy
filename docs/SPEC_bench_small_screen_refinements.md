# SPEC — Measurement-bench small-screen refinements

Status: **IMPLEMENTED** (P1–P4 + S7 + S8, 2026-07-10) — awaits on-device click-through (bench needs a real camera +
master login, so acquisition/capture couldn't be driven headless). Static verification done: all touched files
compile; `plugin_sdk` exports + style builder wired; renderer applies bold to ratio labels only; bench view
constructs with 2 role tabs (top-most, hint+status removed — S7), base-line off, shared step-content reparenting
cleanly; evaluation page is a Metrics|Spectrum tab panel; no inline progress bar; not-connected diagnostics route to
the app status bar.
Scope: `DevMeasurementBenchViewModule` (dev master "Swiss-knife" bench) — refinements from click-through on a
small/phone-width screen. Extends `SPEC_dev_measure_bench.md`; does not change the pipeline or the analysis window.
Source: two annotated ksnip screenshots (2026-07-10) — Acquisition tab + Evaluation tab.

Affected files:
- `sciens/spectracs/view/settings/development/DevMeasurementBenchViewModule.py` (the bench view)
- `sciens/spectracs/view/spectral/workflow/EvaluationResultRenderer.py` (metric label rendering)
- `spectracsPy-model/sciens/spectracs/model/spectral/evaluation/MetricFieldView.py` (carries an optional style)
- `spectracsPy-model/sciens/spectracs/model/spectral/evaluation/MetricFieldViewStyle.py` (**new** — style composite + builder)
- `sciens/spectracs/logic/spectral/plugin/dev/DevSpectralPlugin.py` (which metrics get a bold-label style)
- `sciens/spectracs/logic/appliction/style/ApplicationStyleLogicModule.py` (only if the tab base-line needs a QSS fix)

Six changes: **S1** a phase's *steps* wrap in a tab panel · **S2** capture progress → app status bar ·
**S3** drop the inactive-tab white line · **S4** split Evaluation into *Metrics* | *Spectrum* tabs ·
**S5** bold labels for dilution-independent metrics (via a style composite) · **S6** remove the "Analysis window" readout.

---

## S1 — A phase's *steps* wrap in a tab panel *(screenshot 1, markers 1 + 2)*

**Confirmed with Edwin (2026-07-10).** The **phase** rendering stays exactly as it is — the `StepBarWidget` chevron
strip *Acquisition › Processing › Evaluation* and the **Back / Next** buttons keep driving phase navigation over the
`QStackedWidget`. What changes: **the `WorkflowStep`s *within* a phase are wrapped in a real `QTabWidget`** (a
TabsPanel) that comprises the whole content of that phase's page. The concrete case here is the **Acquisition**
phase, whose two steps are *Reference* and *Sample*.

**Observed today.** Acquisition uses a bare `QTabBar` (`__roleTabBar`, marker 1) as a thin strip; the actual step
content (the shared `[ Captured image | Spectrum ]` inner tabs + the Frames/Exposure/Capture controls) sits in a
*separate* area below it. So the "tabs" are a strip, not a container.

**Requested.** "The top-level container [of the phase's content] should be a **TabsPanel** and the tabs should
comprise the whole content" — the step tabs should *frame* the content, not float above it.

**Design.**
- Replace the bare `QTabBar` (`__roleTabBar`) with a real `QTabWidget` (`__roleTabs`) whose two tabs are the
  **Reference** and **Sample** acquisition steps. Its pane spans the full content width; the phase-level hint text
  and the connection-status line may stay above it (they are phase context, not step content).
- **Preserve §15 Option A** (`SPEC_dev_measure_bench.md`): still exactly **one** live-video widget and **one**
  spectrum plot, re-plotted per active role — not two copies. Mechanism: on the tab-widget's `currentChanged`,
  **reparent** the single shared content widget (inner tabs + controls) into the newly-selected step page, then run
  today's `__onRoleChanged` logic (set `__activeRole`, sync the locked sample exposure, re-plot). This gives the
  "tabs comprise the whole content" framing while keeping the single-instance design.
- **Back navigates *phases*, not steps** (Edwin): unchanged — `onClickedBack` still steps the phase cursor (or exits
  to Settings). Step switching is done by clicking the Reference/Sample tabs. **Next** and its gating are unchanged
  (`__acquisitionComplete()` still gates leaving Acquisition; `__runProcessing` / `__runEvaluation` still run on
  Next). *Cancel* / *Close* unchanged.
- **Other phases:** *Processing* already conforms — its steps are a `QTabWidget` (`__processingTabs`). *Evaluation*
  is effectively a single step; leave it as one page (no forced single-tab wrapper) unless we later want symmetry.

**Do not** change phase navigation, what each phase computes, or the extended-ROI mechanics — this restructures only
the Acquisition phase's step container.

**Interaction with S3.** The white base line moves from the old `QTabBar` to the new `QTabWidget`'s internal tab
bar; apply the S3 fix there (`__roleTabs.tabBar().setDrawBase(False)`), noting the `QTabWidget::pane` border (QSS)
may already reframe the edge — verify during implementation.

---

## S2 — Capture progress in the app status bar, not an inline bar *(screenshot 1, markers 3 + 4)*

**Observed.** During a capture a `QProgressBar` (`__captureProgress`) is shown inline in the acquisition controls
(built at `__buildAcquisitionPanel`, driven by `__beginCaptureProgress` / `__stepCaptureProgress` /
`__endCaptureProgress`). The app already has a global status strip (marker 4, "ready for action…").

**Requested.** Remove the inline progress bar; show per-frame capture progress in the **app status bar** (marker 4).

**Design.** Reuse the exact mechanism auto-exposure already uses (`__emitAutoExposeProgress` /
`__clearStatus` → `ApplicationStatusSignal` via `getApplicationSignalsProvider().emitApplicationStatusSignal`):
- Delete the `__captureProgress` widget and its `controlsLayout` row (row 3).
- `__beginCaptureProgress(total)` — store the total; emit nothing or an initial 0/total.
- `__stepCaptureProgress(i)` — emit `ApplicationStatusSignal` with `isStatusReset=False`,
  `stepsCount=total`, `currentStepIndex=i`, `text="Capturing frame %d / %d"`.
- `__endCaptureProgress()` — emit a reset signal (`isStatusReset=True`), like `__clearStatus`.
- The per-frame event-loop pump (`__pumpFrames`) already lets the strip repaint between frames.

Net: `__captureProgress` field and widget are gone; the three helpers keep their names but drive the status bar.

---

## S3 — Drop the white base line on the inactive tab *(screenshot 1, marker 5)*

**Observed.** The inactive *Sample* tab shows a thin white line (the tab bar's base line drawn under the tabs).

**Requested.** Remove that line — it is not wanted.

**Design.** Call `setDrawBase(False)` on the Reference/Sample tab bar. After S1 that bar belongs to the new
`QTabWidget`, so: `self.__roleTabs.tabBar().setDrawBase(False)` (pre-S1 equivalent: `self.__roleTabBar.setDrawBase(False)`).
The existing `QTabBar` QSS already sets no border; the base line is the `drawBase` element, so the code call is the
fix. If a hairline persists at the pane edge, it is the `QTabWidget::pane` border — leave that (it frames the panel).

---

## S4 — Split Evaluation into two step-tabs: *Metrics* | *Spectrum* *(screenshot 2, marker 1)*

**Observed.** The Evaluation page stacks everything in one `QScrollArea` (`__evaluationScroll`): a wrapping
"PROVISIONAL…" header, **six** metric rows (Greenness G, Pigment D_Q, Browning A_blue, Clarity A_green,
Browning ratio, G' alt.), an optional "⚠ low confidence" line, the caption, and the tall absorption-bands plot.
Together they overflow → a **vertical scrollbar**.

**Requested (Edwin, revised).** Don't try to cram it all onto one scrolling page. **Split the Evaluation content into
two tabs/steps**: the **metric fields** in one, the **spectrum/graph** in the other. This is the same
"steps → `QTabWidget`" idea as S1 (see the Deferred note): each tab holds much less, so the scrollbar problem
disappears.

**Design.**
- Give the Evaluation page a `QTabWidget` with two tabs:
  - **Metrics** — the `EvaluationResultRenderer` output (header + six metric rows + optional low-confidence line).
  - **Spectrum** — the `A(λ) — bands` plot (`__absorptionBandsPlot`) + its caption, filling the tab.
- The bands plot no longer competes with the metrics for height, so it can use the full tab (no forced tiny height).
- **Scroll:** the *Metrics* tab may keep a lightweight `QScrollArea` only as a fallback for very short windows; the
  *Spectrum* tab needs none. Target = no scrollbar in the observed case.
- **Cosmetic-phase scope:** implement as **view-level** tabs (the plugin still emits one Evaluation step + the
  view-drawn plot). Promoting *Metrics* / *Spectrum* to real **plugin-declared steps** is part of the Deferred
  plugin-convergence work — noted, not built here.

---

## S5 — Bold labels for dilution-independent metrics *(screenshot 2, marker 2)*

**Observed.** Metric rows render with a plain label chip (`EvaluationResultRenderer.__addMetricRow` →
`TooltipPageLabel`). Some metrics are ratios (independent of how strongly the oil is diluted); others are absolute
absorptions (scale with the diluted concentration).

**Requested.** Metric values that **do not depend on the concentration of the diluted oil** should render their
**labels in boldface**.

**Rationale (Beer–Lambert, `A = ε·c·l`).** Absolute absorptions scale with concentration `c`; a **ratio** of two
absorptions cancels `c` (and path length), so it is intrinsic to the oil regardless of dilution. Of
`DevSpectralPlugin.__peakRatioResult`:

| Metric | Formula | Dilution-independent? | Bold label? |
|---|---|---|---|
| Greenness **G** | D_Q ÷ A_green | yes (ratio) | **bold** |
| Pigment D_Q | absolute depth | no | normal |
| Browning A_blue | absolute | no | normal |
| Clarity A_green | absolute | no | normal |
| **Browning ratio** | A_blue ÷ A_green | yes (ratio) | **bold** |
| **G' (alt.)** | D_Q ÷ A_blue | yes (ratio) | **bold** |

This matches the screenshot: *Clarity A_green* is not bold; *Browning ratio* and *G' (alt.)* are.

**Design (Edwin's steer — style as a composite, not a flag on the view-model).** The domain knowledge ("this metric
is a dilution-independent ratio") lives in the **plugin**; it expresses that as a **presentation style** it attaches
to the metric — the `MetricFieldView` does **not** grow style flags/methods of its own.

- New **`MetricFieldViewStyle`** — a Qt-free plain-data *composite* (in `spectracsPy-model`, beside `MetricFieldView`)
  holding presentation attributes. Start minimal: `labelBold: bool` (default `False`); extensible later
  (value emphasis, colour, …).
- Built via a **builder** (fluent), e.g. `MetricFieldViewStyle.builder().labelBold(True).build()` — so adding style
  attributes later doesn't churn call sites.
- `MetricFieldView` gains an **optional `style`** attribute (default `None` / a neutral style). It only *carries* the
  composite; it holds no Qt and no styling logic.
- `DevSpectralPlugin` attaches a `labelBold(True)` style to **Greenness G**, **Browning ratio**, **G' (alt.)** at
  creation. The plugin decides *why* (it knows they're ratios); the view-model only sees the resulting style.
- `EvaluationResultRenderer.__addMetricRow` reads `metricFieldView.style` and, when `labelBold`, sets the
  `TooltipPageLabel`'s **`QFont` bold** — **not** `setStyleSheet` (which would clobber the gray-chip QSS). Value field
  unchanged. Qt stays entirely in the renderer.
- Generic: any plugin can style a metric this way; only `DevSpectralPlugin` uses it now.

---

## S6 — Remove the "Analysis window" readout *(screenshot 2, marker 3)*

**Observed.** The Evaluation page shows a line "Analysis window: 400–692 nm" — written to the page message label by
`__showEffectiveWindow` (`__messageLabel.setText(...)`, called from `__applyExtendedRoi`).

**Requested.** That label is not needed / not wanted.

**Design.** Remove the readout: drop the `__showEffectiveWindow` call (and the method) so no "Analysis window…" text
is set. **Keep** the extended-ROI clamp itself (it is functional — only the text is removed). The page message label
may be left present-but-empty, or removed if it serves no other purpose.

**Status: DONE** (P1).

---

## S7 — Acquisition hint removed; role `QTabWidget` at the top of the phase content *(follow-up, ksnip 14:23)*

**Observed after S1 (2026-07-10).** S1 landed correctly — the Reference/Sample `QTabWidget` now frames the step
content (inner tabs + controls inside its pane), and the white line is gone. But the tab panel is **not at the top
of the phase content**: the multi-line **hint** "Transmission geometry — place the sample between the bulb and the
camera. Capture the reference (blank) first, then the sample." sits above it (built as `hint` in
`__buildAcquisitionPanel`), and below that the **connection-status** line (`__statusLabel`, e.g. "Connected:
32e4:8830 → cv2 index 0").

**Requested (Edwin).** The hint is "not needed at all and should be removed" so the `QTabWidget` sits at the top
level of the phase content.

**Decision (Edwin).** The app header already carries a live connection indicator (`MainStatusBarViewModule.
connectionButton` — a camera glyph: **green = connected**, white = disconnected, grey = no instrument, driven by the
§12 presence poller). So:
- **Positive case (device connected):** show **no** inline text — the header icon already conveys it.
- **Negative case (no device / virtual / not resolvable):** the diagnostic goes to the **app status bar**.

**Design.**
- **Remove the hint label** (`hint = self.createMessageLabel("Transmission geometry …")` + its `addWidget`) entirely.
- **Remove the inline `__statusLabel`** from the acquisition panel. Rework `__resolveCamera`:
  - `resolvedIndex is not None` (connected) → set no inline text; the green header icon covers it (optionally emit an
    `ApplicationStatusSignal` reset so any prior error clears).
  - no sensor / `isVirtual` / `resolvedIndex is None` → emit the existing diagnostic string
    ("The active setup has no camera device…", "…virtual device; the bench needs a real camera.", "Not connected —
    no VID:PID camera found…") to the **app status bar** via `ApplicationStatusSignal` (`isStatusReset=False`).
    Capture is disabled in these states anyway, so it never competes with capture progress.
- **Net:** the role `QTabWidget` becomes the first element of the acquisition phase content, directly under the
  breadcrumb.

**Status: DONE.** Hint + `__statusLabel` removed; `__resolveCamera` clears the status bar when connected and pushes
the diagnostic there otherwise (new `__emitStatusMessage` helper). Verified offscreen: the role `QTabWidget` is the
first acquisition-panel widget; no "Transmission geometry"/"Connected:" text remains.

---

## S8 — Drop the pane border + padding on the bench's nested tab widgets *(follow-up, ksnip 14:38)*

**Observed.** With the tabs now framing the content (S1), each nested `QTabWidget` draws a bordered, padded card
(the global QSS `QTabWidget::pane { border: 1px solid {border}; padding: {panelPadding}px; }` in
`ApplicationStyleLogicModule`). At bench depth this stacks card-in-card: the outer **role** tabs pane (marker 1 —
"we do not need this border and padding") wraps the inner **Captured image | Spectrum** tabs pane (marker 2 — "also
not need this border"), which wraps the image. Two nested frames read as heavy/cramped at phone width.

**Decided with Edwin (final; annotated: `ksnip_20260710-143857_annotated.png`).** The captured-image area is
wrapped by three concentric frames (confirmed by pixel inspection — paired border lines ~14px apart = border +
padding). **Keep exactly ONE frame** (the inner tab pane); drop the redundant outer card and the innermost image
outline:
- **① OUTER** — the role `QTabWidget::pane` (`__roleTabs`, big card ~x51). → **REMOVE border + padding.**
- **② INNER** — the content `QTabWidget::pane` (`__innerTabs`, Captured image | Spectrum, ~x66). → **KEEP** — this is
  the single frame that stays around the image area. (Edwin's "(3) QTab inner border to retain" = *this* pane.)
- **③ INNERMOST** — the image widget's own outline (~x80): the QSS rule
  `BaseImageViewModule, BaseVideoViewModule { border: 1px solid {border}; }` (`ApplicationStyleLogicModule` ~L154,
  the E2/C2 "image-area outline"). → **REMOVE** (for the bench's video widget). ② already defines the image area,
  so ③ is redundant here.

**Design.**
- **① Remove `__roleTabs` pane** — `border: none; padding: 0`. **Caveat:** a widget-local `QTabWidget::pane { … }`
  set on `__roleTabs` *cascades to its descendant* `__innerTabs` and would wipe ② too. Scope it so only the outer
  pane matches: give `__roleTabs` an objectName and use `QTabWidget#<roleTabsName>::pane { border:none; padding:0 }`.
  `__innerTabs` (different/no objectName) keeps its global bordered pane → ② stays.
- **② Keep `__innerTabs`** — no change; it retains the global `QTabWidget::pane` border (+ padding around the image).
- **③ Remove the bench video border** — the outline comes from the global class rule `BaseVideoViewModule`. Remove it
  **only for the bench** (other views keep the E2/C2 outline): a widget-local stylesheet on `__videoViewModule`.
  Use a type selector to beat the global rule's specificity — `DevCaptureVideoViewModule { border: none; }` — since a
  bare `border:none` (universal, specificity 0) loses to the app's type-selector rule. Verify on the running app.
- **Scope: acquisition only.** The triple-nesting is unique to the acquisition role-tabs→content-tabs→video stack.
  Processing / Evaluation have single-level panes and are **not** in scope (no card-in-card problem there).
- The `QTabBar` tab headers (the clickable Reference/Sample, Captured image/Spectrum chips) are unchanged.

**Status: DONE.** `__roleTabs` objectName `benchRoleTabs` + scoped `QTabWidget#benchRoleTabs::pane { border:none;
padding:0 }` (①); `__innerTabs` untouched (②); `__videoViewModule` gets local `BaseVideoViewModule { border:none }`
(③). Verified: the three stylesheets are set as intended and `__innerTabs` keeps the global bordered pane. Qt cascade
guarantees ③ wins (a widget's own sheet is always preferred over the app sheet, regardless of specificity). Live
pixel confirmation is Edwin's click-through (the offscreen platform doesn't paint QSS content).

---

## S9 — One snug frame around the step content (revises S8's frame arrangement) *(is/should ksnip 15:15 & 15:19)*

**Observed (is-state, `ksnip_20260710-151529.png`).** A single frame wraps the whole step block — Captured
image/Spectrum tabs + plot + Frames/Exposure + Capture button — but its top sits *below* the Reference/Sample tab
bar with a gap (it is the `stepContent`-level / role-tabs-pane frame). Note: this frame **includes the controls**,
so it is not the `__innerTabs` plot-only pane — S8's "keep ② around the plot" is therefore *not* what should remain.

**Requested (should-state, `ksnip_20260710-151927.png` — Edwin's red "remove" / green "add").**
- **Remove** the current frame as positioned (red) — the one that starts up near the Reference/Sample level.
- **Add** (green) a **snug frame whose top is at the Captured image/Spectrum tab row**, wrapping the plot **and** the
  controls + Capture button. Reference/Sample tabs sit *outside/above* the frame.

So: **exactly one frame, around `stepContent` (`__innerTabs` + controls), attached at the Captured image/Spectrum
tab bar.** Not a role-level frame, not a plot-only frame.

**Design (supersedes S8 ①/②; keeps S8 ③).**
- **`__roleTabs` pane** — border:none, padding:0 (as S8 ①): no frame at the Reference/Sample level.
- **`__innerTabs` pane** — now also **border:none, padding:0** (this *reverses* S8 ②): the plot must not carry its own
  frame, else it doubles with the new `stepContent` frame.
- **`__stepContent`** — **add a 1px theme-border** (green). Scope with an objectName so the border does **not**
  cascade to children: `QFrame#benchStepContent { border: 1px solid <getBorderColor()>; }` (make `__stepContent` a
  `QFrame`, or set `WA_StyledBackground`). Add small layout margins (`Metrics.S`) so content is inset from the border.
  Its top aligns with `__innerTabs`' tab bar → matches the green "add".
- **`__videoViewModule`** — keep S8 ③ (no image outline).
- Net frames around the captured image: **one** (the `stepContent` frame). Tab headers unchanged.

**Note on S8 rendering.** The is-state may predate a restart with S8 (or S8's ① didn't paint) — either way S9
re-asserts all pane borders explicitly, so the result is deterministic once running. Verify on the app.

**Status: SUPERSEDED by S10 — do not implement.** The one-frame-on-`__stepContent` arrangement was replaced by the
uniform rule below after reviewing a Wireloom mock (`docs/mock_bench_acquisition.wireloom`).

---

## S10 — Uniform rule: every `QTabWidget` keeps its pane border *(supersedes S9; agreed 2026-07-10 via Wireloom mock)*

**Requested (Edwin).** "Every `QTabWidget` should have this inner border." Confirmed against the Wireloom mock
`docs/mock_bench_acquisition.wireloom` (outer frame + inner-tab-widget frame, two nested frames).

**Key insight (rubber-duck).** The global stylesheet already gives *every* tab widget a pane border:
`QTabWidget::pane { border: 1px solid {border}; padding: {panelPadding}px }` (`ApplicationStyleLogicModule`). So the
rule is the **default**, and S8 ①/S9 were *overrides that stripped it*. S10 is therefore mostly **deletion** — remove
the overrides and let the global QSS apply uniformly. In the Acquisition phase the two nested frames then fall out of
the widget nesting for free:
- **`__roleTabs` pane (Reference/Sample)** = the **OUTER** frame — it wraps the whole step (`__stepContent`).
- **`__innerTabs` pane (Captured image/Spectrum)** = the **INNER** frame — it wraps the active tab's plot/video.
- The **controls** (Frames/Exposure/Capture) are siblings *below* `__innerTabs` inside `__stepContent`, so they sit
  in the OUTER frame, *below* the inner frame. (The mock draws them inside the inner frame — a mock artifact; the
  natural Qt result is inner-frame-around-plot/video-only, which Edwin accepted.)

**Design (supersedes S8 ①/②/S9; keeps S8 ③).**
- **`__roleTabs`** — **remove** the S8 ① override (`QTabWidget#benchRoleTabs::pane { border:none; padding:0 }`) and
  the `benchRoleTabs` objectName → the role-tabs pane regains the global border = OUTER frame.
- **`__innerTabs`** — **no override** (never apply S9's `border:none`) → keeps the global border = INNER frame.
- **`__stepContent`** — **no border of its own** (drop S9's `QFrame#benchStepContent`); it stays a plain, borderless
  reparent container.
- **`__videoViewModule`** — **keep** S8 ③ (`BaseVideoViewModule { border:none }`) so the image is not double-framed
  inside the inner pane.
- **Processing (`__processingTabs`) + Evaluation (`__evaluationTabs`)** — already carry no override → already framed
  by the global QSS. Audit only; no change.

**Status: IMPLEMENTED (code, 2026-07-10)** — single edit: deleted the S8 ① `__roleTabs` pane override + objectName;
comments refreshed to S10; L2–L5 verified already-compliant (no `::pane`/`benchStepContent`/`WA_StyledBackground`
remains; only the intentional video `border:none` survives). Compiles. **Awaits on-device click-through** (bench needs
a real camera + master login): expect OUTER frame below Reference/Sample, INNER frame around the plot/video with the
controls below it inside the outer frame, Processing/Evaluation framed identically, and no double border on the image.

---

## S11 — Drop the WORKFLOW-PHASE frame (the phase `QStackedWidget`) *(click-through ksnip 16:55 → 17:06; distinct from S10)*

**The phase container.** Phases (Acquisition/Processing/Evaluation) are a `StepBarWidget` + a `QStackedWidget`
(`__stack`) whose pages are the phase contents. The global QSS gives **every `QStackedWidget` a 1px border**
(`ApplicationStyleLogicModule`: `QStackedWidget { border: 1px solid {border} }`), so `__stack` draws a frame around
the current phase page — the border below the StepBar that Edwin's arrow marks. This is the **WorkflowPhase** frame,
*not* the WorkflowStep (`__roleTabs`, Reference/Sample) frame.

**Requested (Edwin).** "The border that wraps a WorkflowPhase should not have the border, as it is the only 'content'
component." The stack shows a single phase page at a time, which already carries its own tab-widget frames (S10), so
the stack frame just doubles up.

**False start (recorded so we don't repeat it).** First tried `borderlessMainContainer = True`. That removes a
*different* frame — the base `PageWidget.createMainContainer()` `QGroupBox` around StepBar+stack (and restyles the
title) — so the arrow border survived. Reverted.

**Design.** Give `__stack` an objectName and a widget-local override: `benchPhaseStack` +
`QStackedWidget#benchPhaseStack { border: none; }`. ObjectName-scoped so it does **not** touch the internal
`QStackedWidget`s of the nested `QTabWidget`s (already `border:none` globally). Bench-only; other views keep the
generic stacked-widget border. **Does NOT touch** the S10 step/content tab frames (`__roleTabs`, `__innerTabs`,
`__processingTabs`, `__evaluationTabs`).

**Status: IMPLEMENTED (code, 2026-07-10)** — objectName + local stylesheet on `__stack`; compiles. Awaits on-device
click-through: expect the phase frame (below the StepBar) gone, with the step + content tab frames unchanged.

---

## S12 — Centre the Processing raster vertically *(phone click-through ksnip 17:19)*

**Observed.** The Processing → *Full frame* / *Cropped ROI* raster sits at the top of its tab with dead space below.
`__rasterImageTab` laid out `[caption, image, addStretch(1)]` — a single trailing stretch top-packs the content.

**Design.** Add a **leading** `addStretch(1)` too (`stretch · caption · image · stretch`) so the raster centres
vertically. Bench-local. **Status: IMPLEMENTED** (compiles; awaits click-through).

---

## S13 — Enlarged checkbox indicator is real-device-only *(phone vs desktop ksnip 17:20 / 17:26)*

**Observed.** On desktop `--phone` the auto-exposure checkbox icon looked oversized. **Root cause (not a bug):** phone/
android mode appends `ANDROID_TOUCH_DENSITY_QSS` (spectracsMain.py) which sets `QCheckBox::indicator { 26px }` — an
intentional finger target vs the `13px` desktop indicator.

**Decision (Edwin).** Keep 26px on a **real** Android device; on **desktop `--phone`** (mouse) show the desktop 13px
icon.

**Design.** Split the touch QSS: move the `QRadioButton/QCheckBox::indicator { 26px }` line into a new
`ANDROID_ONLY_TOUCH_QSS` appended only under `is_android()`. `--phone` keeps the *width-relevant* touch overrides
(scrollbars/spinbox) for the width audit but the checkbox stays desktop-size. **Caveat:** the `--phone` width audit no
longer reflects the 26px checkbox width — accepted. **Status: IMPLEMENTED** — verified offscreen: indicator = 15px on
desktop and desktop-`--phone`, 28px on the android style path.

---

## S14 — Native combo-box down-arrow, global *(desktop ksnip 17:26 — "would expect a downwards arrow")*

**Observed.** The Frames `QComboBox` drop-down showed an empty bordered box, no arrow glyph — at both densities.
**Root cause:** the global QSS styled `QComboBox::down-arrow` / `::drop-down` as border boxes; styling `::drop-down`
at all **suppresses Qt's native ▼** (verified), so the box replaced the arrow.

**Design (global; Edwin: "globally, want the arrow glyph").** Remove the base `::down-arrow` + `::drop-down` rules
(`ApplicationStyleLogicModule`) and the touch-density `QComboBox` lines (spectracsMain.py) → Qt draws its **native ▼**
at every density. The border-triangle QSS trick does **not** work in Qt (renders as a box — tested); an image asset
was the alternative but is unnecessary. **Cost:** the phone drop-down *button* reverts to default width (combo stays
fully tappable). **Status: IMPLEMENTED** — verified: native ▼ renders under the real app stylesheet. Also fixed a
`.format()` `KeyError` from a literal `{ }` in the replacement comment (would have crashed startup).

---

## Deferred — plugin-driven convergence of the two measurement views *(not part of this spec)*

Raised by Edwin (2026-07-10), to be handled **after** these cosmetic changes land:
- The generated **plugin code** wants inspecting — the intent is that *almost everything* the view does is
  **driven by its plugin** (steps, metrics, layout hints), not hard-coded in the view.
- The **end-user default measurement view** and this **dev measurement bench** should share the **same
  plugin-integration concept**, so that the two views' code ends up **nearly identical** — each is a thin host that
  renders whatever its plugin declares.
- Consequence for S1/S5 to keep in mind (design, not build): the "steps → `QTabWidget`" wrapping (S1) and the
  "dilution-independent → bold" flag (S5) should be **generic host behaviours reading plugin-declared data**, not
  bench-only specials. S5 already does this (the flag lives on `MetricFieldView`, any plugin can set it); S1's step
  tabs should likewise be a generic per-phase render, so the same host code serves both views.

This is an **implementation-detail / refactor** to scope separately once the cosmetics are in. Recorded here only so
the cosmetic work does not paint us into a bench-specific corner.

## Out of scope / unchanged
- The acquisition pipeline, the 400–700 nm extended-ROI mechanics, exposure/auto-exposure, ROI overlay.
- The Processing tab's internal raster/spectra sub-tabs.
- End-user plugins and the real pumpkin plugin (S5's flag is available to them but not required).

## Verification (click-through, small-screen / `--phone`)
1. Acquisition: the Reference/Sample steps render as a full-width `QTabWidget` framing the content (S1); the phase
   strip + Back/Next are unchanged; switching tabs still drives the single shared video/plot.
2. Capture a role: no inline progress bar; the app status strip shows "Capturing frame i/N", then clears (S2).
3. The inactive *Sample* tab shows no white line (S3).
4. Evaluation: two tabs *Metrics* | *Spectrum*; neither shows a vertical scrollbar in the observed case (S4).
5. On the *Metrics* tab: *Greenness G*, *Browning ratio*, *G' (alt.)* labels bold; the three absolute metrics plain (S5).
6. No "Analysis window: …" line anywhere (S6).
