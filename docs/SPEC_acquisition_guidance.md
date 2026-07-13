# SPEC — Acquisition guidance (coach line + next-action highlight)

Status: **IMPLEMENTED — both hosts (2026-07-13)**; offscreen-verified (wizard 18/18, bench 17/17, status-bar 8/8) +
`test_pumpkin_wizard_offscreen` green. Source: Edwin. Depends on the plugin-driven convergence
([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md), M1): both hosts render plugin-declared
phases → steps → step-tabs.

**What landed:** guidance in `WizardViewModule` (end-user) **and** `DevMeasurementBenchViewModule` (bench);
`ApplicationStyleLogicModule.getGuidanceColor()`; plugin-authored short `CaptureView.prompt`s + per-phase hints in
**both** `PumpkinOilPlugin` and `DevSpectralPlugin`; new `SpectralWorkflowPhase.setHint()`/`getHint()` (transient);
new `ApplicationStatusSignal.guidance` flag + amber/no-bar rendering in `MainStatusBarViewModule`. No regressions.

**The cue is an icon (2026-07-13, Edwin).** The amber "act here" cue is an **icon in the control's icon slot** — an amber
**●** on a Measure/Capture button or a target tab. The **Next** button carries a **permanent amber ▶** (its
proceed-arrow) set in `__refreshNav`, **not** a per-state cue: it **dims when the button is disabled and brightens when
enabled** (so "you can proceed now" reads for free); terminal actions (Save/Close) drop the arrow. The earlier
2px-border + `[guidance="true"]` QSS rule are **gone**; icons are painted in code from `getGuidanceColor()`
(`__paintGuidanceIcon`: `●` ellipse, `▶` polygon).

**Status text is muted-amber, centered, with no progress bar (2026-07-13, Edwin).** Plugin/guidance text (the
acquisition coach + phase hints) is emitted with `ApplicationStatusSignal.guidance = True`; `MainStatusBarViewModule`
renders it as a plain **centered** muted-amber label (transparent chunk/groove, value 0). **Host operational** status
keeps the normal bar: capture progress ("frame 5/10"), auto-exposure, and the bench not-connected diagnostic all emit
`guidance = False`. Leaving a run (**Cancel**, or terminal **Save**/**Close**) resets the bar via
`__goHome`/`__goToSettings`.

**All guidance text is plugin-authored (2026-07-13, Edwin — "the plugin decides").** Two plugin seams:
- **Per-step** acquisition prompt → `CaptureView.prompt`, shown **verbatim** as the coach line (no "Step N of M"
  wrapper). Both plugins: Reference "Insert isopropanol and capture", Sample "select oil-tab and capture oil-dilution".
- **Per-phase** hint → `SpectralWorkflowPhase.setHint()`, set by the plugin in its
  `acquisition`/`processing`/`evaluation`/`publishing` hook; the host shows `phase.getHint()` as the coach line, or
  blanks if unset. Used for the **computed** phases (PROCESSING "You can view the measurement results here." /
  EVALUATION "The measurement has been evaluated." / PUBLISHING "Send the result to the laboratory if you want.")
  **and** for the **ACQUISITION-complete** state: when every step is captured the coach shows the ACQUISITION phase's
  hint — both plugins set **"measurement complete"**. The host hard-codes **no** wording — future plugins author their
  own with zero host changes.

**Decision B (Edwin, 2026-07-13) — the bench host renders guidance too (superseded Decision A).** The coach/amber
mechanism now lives in **both** hosts. Each binds the *same* derived next-action to its own controls:
- **Wizard** — per-role Measure buttons + role step-tabs.
- **Bench** — the *single* shared `__captureButton` (amber when you're on the next-to-capture role-tab) + the
  Reference/Sample `__roleTabs` (amber ● on the role-tab to switch to). Bench-only guard: when the real camera is not
  resolved, guidance stays silent so `__resolveCamera`'s not-connected diagnostic is not overwritten.

**Known duplication (intentional, temporary):** the derive-next-action + coach + highlight helpers are **mirrored**
across the two hosts (~90 lines), because their acquisition panels are still separate. This is the Option-B cost we
accepted to get bench guidance now. **The capture-panel convergence (deferred M1 "P6") is the ▶ NEXT plugin-platform
item and will dedupe this** — once ACQUISITION routes through the shared `WorkflowPhaseRenderer` capture path, the
guidance logic collapses into one place. See ROADMAP "▶ NEXT" and
[`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md) deferred-P6.

## 0. The rule that governs all

**A first-time user must always be able to answer "what do I do next?" without prior knowledge — and the answer is
authored by the plugin, not hard-coded in the host.** The wizard stays generic: it derives *which* step is next and
renders *whatever guidance the plugin declared* for that step.

## 1. Problem

In the ACQUISITION phase the plugin declares N acquisition steps, rendered as step-tabs (Pumpkin: **Reference** +
**Sample**). Each tab = a `Measure` button + a status label + a plot. `Next` stays disabled until **every** step is
captured (`WizardViewModule.__acquisitionComplete`). A newcomer faces four unanswered unknowns:

1. Do I need to visit both tabs, or is one optional?
2. Which one first? (Reference/sample order matters physically.)
3. What's the physical setup for *this* tab before I press Measure?
4. What now? — that the greyed-out `Next` just became live after the last capture.

The top progress/status bar (`MainStatusBarViewModule`, a signal-driven `QProgressBar`) is **unused by the wizard**
today — a free channel.

## 2. Design — one derived "next action", surfaced in two places

Do **not** sprinkle independent hints. Compute a single **next action** from acquisition state (the same state
`__refreshNav` / `__acquisitionComplete` already track) and surface that one answer in two surfaces:

1. **Coach line (primary)** — the top status bar states the single next step in imperative voice.
2. **Amber "act here" highlight (secondary)** — one control at a time is tinted amber; the tint moves as steps complete.

Both read from the same derived next-action, so they can never disagree.

### 2.1 The hint source already exists — `CaptureView.prompt` (no new SDK)

Plugins **already** declare a per-step prompt via `CaptureView(prompt=...)`
(`PumpkinOilPlugin.__measurementStep` → `PumpkinOilPlugin.py:83`; `DevSpectralPlugin.py:221`). Today it is **orphaned**:
`WorkflowPhaseRenderer.py:64-65` renders it as a `QLabel`, but only on the *generic capture path that the wizard/bench
do not use*; S7 removed the wizard's inline hint label (`DevMeasurementBenchViewModule.py:558` — "prompt has no home
since S7"). **This feature gives that declared-but-homeless field a home.** No new plugin API.

- Hint source per step = `step.getView().prompt` (the step's `CaptureView.prompt`), falling back to a generic
  `"Press %s" % captureLabel` when a plugin declares no prompt.
- Content change (small, plugin-side, P4): Pumpkin currently sets the **same** generic prompt on both steps. It should
  differentiate — Reference: *"Insert the blank/reference, then Capture"*; Sample: *"Now insert the oil sample, then
  Capture."* This is what makes step 3 above ("physical setup for this tab") answerable.

### 2.2 The "post-step" case is just the next step's pre-hint

Edwin's example — *after Reference is captured, show "Now insert the oil" and highlight the Sample tab* — needs **no**
separate post-capture hook. The derive-next-action logic handles it: once Reference has a container, the first
*incomplete* step is Sample, so the coach line swaps to Sample's prompt and the amber cue jumps to the Sample tab. The
hint belongs to the step you are **about to do**, not the one you just finished. One static prompt per step covers it.

### 2.3 Future (designed-for, NOT built): data-dependent guidance

The only thing a static per-step prompt cannot express is guidance that depends on the **captured spectrum itself**
(e.g. *"reference too dark — re-measure"*, or a dynamic confirmation). That would need a plugin callback receiving the
`SpectraContainer` after `captureAcquisitionStep`, e.g. `onCaptured(step, container) -> guidance` that overrides the
static prompt. **Not in scope now.** The derive-next-action helper (§3) must be shaped so such a hook can later override
the prompt string without a redesign — i.e. guidance text flows through **one** function that today only reads
`CaptureView.prompt`.

## 3. Derive-next-action (single source of truth)

A pure helper on `WizardViewModule` (order-independent; steps may be captured out of order):

```
steps      = ordered role-bearing acquisition steps
nextStep    = first s in steps with no container   (None if all captured)

if nextStep is not None:
    coachText = nextStep.getView().prompt        # the plugin's prompt, VERBATIM (no "Step N of M")
    amber ●   = nextStep.tab            if current tab != nextStep's tab   # draw them to the tab
                nextStep.measureButton  if current tab == nextStep's tab   # then to the ● on the button
else:                                             # all captured
    coachText = acquisitionPhase.getHint()       # the plugin's ACQUISITION hint → "measurement complete"
    amber ●   = none                              # the permanent bright Next ▶ carries "proceed"
```

- The Next button's amber **▶** is NOT part of this per-state logic — it is a permanent icon set in `__refreshNav`
  (§4.2), dim/bright with the button's enabled state.
- `coachText` is emitted with `guidance=True` (§4.1); a `None` value rests the bar.
- Only active in **NEW** mode (`not __isView()`); VIEW/read-only saved runs get no guidance.
- Re-run on **two** triggers: (a) after every capture (`__refreshNav` already fires), and (b) on **tab change**
  (`tabWidget.currentChanged`) — because *which* control carries the amber ● depends on the active tab.

## 4. Surfaces

### 4.1 Coach line — top status bar

Reuse the existing signal path (no new widget): build an `ApplicationStatusSignal` and
`ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(sig)`.

- Guidance emissions set `guidance=True` (rendered muted-amber, centered, **no** bar — §status-text note); operational
  emissions (capture/auto-exposure progress) keep `guidance=False` and a real fill.
- **Reset on leave**: `isStatusReset=True` when ACQUISITION is left, on entering a hint-less phase, and on
  Cancel/terminal (`__goHome`/`__goToSettings`), so nothing lingers in other views (cf. desktop-switch reset `3d455cd`).

### 4.2 Amber highlight — "act here" (icon-based; final, 2026-07-13)

**One uniform mechanism: an amber icon in the control's icon slot.** No borders, no per-widget QSS. Icons are painted in
code from `getGuidanceColor()` (`__paintGuidanceIcon(shape)` → `QPixmap(12,12)` → `QPainter` → `QIcon`; a filled
`drawEllipse` for **●**, a right-pointing `drawPolygon` for **▶**). Cleared with the empty `QIcon()`.

- **Measure / Capture button** → amber **●** via `button.setIcon(...)` when it's the act-here target.
- **Next button** → amber **▶** (its proceed-arrow, in guidance amber): `setIcon(▶)` **and** drop the redundant text
  arrow (`setText("Next")`); restoring the "Next →" text is `__refreshNav`'s job on the next cycle. Only ever applied in
  the non-terminal "Next →" state (acquisition complete), never on Save/Close.
- **A single tab** → amber **●** via `tabBar().setTabIcon(idx, ●)`; the label text is left its normal colour, so it stays
  legible. (A single tab can't take a border and can't be selected in QSS — the icon slot is the clean per-tab lever.)
- **Selected tab is already green** (`#3D7848`, existing `QTabBar::tab:selected`) — "you're on the right tab" comes for
  **free**; do not restyle it.
- **Captured/done tabs** → a **✓ glyph** in the tab label (`setTabText("✓ …")`), *not* a colour, so "done" never clashes
  with the green selected-tab.

Exactly **one** amber target at any time; it moves as steps complete / tabs change.

### 4.3 Phase hints — computed phases (plugin-declared, 2026-07-13)

On entering a **computed** phase (PROCESSING / EVALUATION / PUBLISHING) there is nothing to *act* on, so no amber — but
the coach line shows a short **plugin-authored** description of where you are:

- **Seam:** `SpectralWorkflowPhase.setHint(text)` / `getHint()` (transient, not persisted). The plugin sets it inside the
  phase hook it already implements (`processing`/`evaluation`/`publishing`); the host reads `phase.getHint()` on entry.
- **Host behaviour:** `hint` present → emit it as the coach line (plain, 0-progress); `hint` absent → reset the coach
  line (blank). The host authors **no** wording.
- Shipping text (each plugin free to diverge): PROCESSING "You can view the measurement results here.", EVALUATION "The
  measurement has been evaluated.", PUBLISHING "Send the result to the laboratory if you want." (Pumpkin declares no
  PUBLISHING → no publishing hint.)
- VIEW mode / DB-loaded runs: hints are transient, so they're simply absent (guidance is a live-run concern).

## 5. Color token

Add to `ApplicationStyleLogicModule` a dedicated semantic token (do **not** overload `warning`/`danger` — a helpful cue
is not a problem):

- **`getGuidanceColor()` → amber `#C9942E`** (a *dedicated* token, not `warning`/`danger` — a helpful cue is not a
  problem). Used only to **paint the ●/▶ guidance icons in code**; there is no `[guidance="true"]` QSS rule (the earlier
  border approach was dropped, 2026-07-13).

## 6. Non-goals

- **Do not touch `StepBarWidget`** (the 4-phase chevrons). Intra-acquisition steps do not belong there.
- No pulse/animation — **static** amber only (v1).
- No "hide hints" toggle / experience-fade — guidance stays **always-on** (Edwin: navigation should make sense and not
  be annoying regardless of experience).
- No data-dependent guidance / `onCaptured` hook (§2.3) — future.

## 7. Implementation phases

```
+------+--------------------------------+-----------------------------------------------+----------------+
| Ph.  | What                           | Where                                         | Depends on     |
+------+--------------------------------+-----------------------------------------------+----------------+
| P0   | Color token + QSS selector     | ApplicationStyleLogicModule                   | -              |
|      | getGuidanceColor() #C9942E;    | (getter + [guidance="true"] button rule in    |                |
|      | button [guidance] amber rule   |  APPLICATION_STYLE_SHEET_TEMPLATE)            |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| P1   | Derive-next-action helper      | WizardViewModule.__deriveNextAction()         | -              |
|      | (pure: nextStep, hint,         | reads step.getView().prompt; testable;        |                |
|      | coachText, captured/total)     | funnels ALL guidance text (shape for §2.3)    |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| P2   | Coach line                     | WizardViewModule -> ApplicationStatusSignal   | P1             |
|      | emit on refresh; reset on      | (emit in __refreshNav; reset on phase-leave / |                |
|      | leave                          |  hide)                                         |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| P3   | Amber highlight                | WizardViewModule.__acquisitionPanel /         | P0, P1         |
|      | button property + tab          | __refreshNav; wire tabWidget.currentChanged;  |                |
|      | setTabTextColor; done ✓ glyph  | setProperty("guidance") unpolish/polish       |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| P4   | Plugin content: differentiate  | PumpkinOilPlugin.__measurementStep            | P1 (to show)   |
|      | Reference vs Sample prompts    | (+ DevSpectralPlugin) CaptureView(prompt=...) |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| P5   | All-captured state             | WizardViewModule nav (Next button amber +     | P1, P3         |
|      | "press Next" + amber on Next   | "press Next" coach text)                       |                |
+------+--------------------------------+-----------------------------------------------+----------------+
| ~~P6~~ | DROPPED (Edwin) — no inline    | —                                             | —              |
|      | per-tab prompt; coach line only|                                               |                |
+------+--------------------------------+-----------------------------------------------+----------------+
```

## 8. Decisions locked (Edwin, 2026-07-13)

- Static amber `#C9942E` via a **dedicated** `guidance` token (not `warning`/`danger`). Name TBD (proposed: `guidance`).
- **Guidance style = 2px muted-amber BORDER, no fill** — on buttons (Capture / Next). A single tab can't be bordered,
  so the target-tab cue is an **amber bullet ● icon** (`setTabIcon`, code-painted dot) with the **label text unchanged**;
  accepted asymmetry (mark vs border).
- Always-on for experienced users too.
- Highlight the **next control**: selected tab already green (free) + Measure/target-tab amber; done = ✓ glyph.
- **P6 dropped** — no inline per-tab prompt label; coach line is the only hint home.
- Plugin-authored per-step hint via the **existing** `CaptureView.prompt` — no new SDK field.
- Coach line + amber both read one derived next-action.
- Data-dependent post-capture hook is a **future hint in this spec** (§2.3), not built.

## 9. Open questions

- **Coach wording with out-of-order capture**: "Step {pos} of {n}" uses the next-incomplete step's position, so
  capturing Sample first reads "Step 1 of 2" (Reference) next. Accept, or switch to "{captured} of {n} captured — next:
  …"? (default: position phrasing).
- **Guidance color name**: `guidance` (proposed) vs `hint` / `next` / `coach`.
