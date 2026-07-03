# Spec — Phone-Width Responsiveness (desktop "phone mode" + width audit)

Status: **DRAFT / spec only — no implementation until explicitly requested.**
Scope: PySide6 app, both desktop and Android. Goal: eliminate controls that render **too wide**
and get **cut off at the right edge** on the phone, by first reproducing the constrained width on
the Linux desktop (fast iteration) and fixing what can be fixed there.

---

## 1. Problem (current state, as found)

- On the Android build many controls extend past the right edge of the screen and are clipped.
- Root cause is layout demanding **more logical width than the phone has**, not physical pixels.
- Building the APK per iteration is slow, so we want to **reproduce the phone width on desktop**
  and drive the fix there via click-through review, deferring on-device checks to the end.

### 1.1 The unit that matters: logical dp, not physical px

The target phone is a **Samsung Galaxy Note20 5G**:

- Physical panel: **1080 × 2400 px**, 6.7", ~393 ppi.
- Qt lays out in **logical (device-independent) pixels** at the display's device-pixel-ratio.
- Note20's effective density is **~2.6× → ~412 logical dp wide** (Samsung default display zoom).
  Usable height after status/nav bars ≈ **883 dp**.

> **Caveat — density is not fixed.** Android's reported density (and thus the logical width) depends
> on the device's *Display zoom / DPI* setting. Depending on that setting the Note20 reports a
> logical width anywhere in **~360–412 dp**. This is precisely why the reproduction width must be a
> **parameter**, not a hardcoded constant. Design target: **412** (default); test the narrow case at
> **360**.

---

## 2. Decisions locked in (from discussion, 2026-07-03)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Reproduce width via | **CLI flag on the startup script** (`runApp.sh --phone`) |
| D2 | Target width | **412 dp** default (Note20), overridable to test 360 etc. |
| D3 | Magnification for viewing | **`--phone-zoom=<f>` CLI flag**, default **1.1** (tuned to fit the full ~883 dp height on the user's 1920×1080 monitor). Drives `QT_SCALE_FACTOR` under the hood. Env var still wins if set. |
| D4 | Triage order | **Desktop first** (fix everything reproducible under `--phone`); real device **later** |
| D5 | Height | Fit the monitor; vertical **scroll** handles overflow (matches phone) — width is the invariant |
| D6 | `--phone` scope | **Desktop-only.** Android path (`showFullScreen`) is untouched. |
| D7 | Touch-density QSS in phone mode | **Apply `ANDROID_TOUCH_DENSITY_QSS` when `phoneMode` too** (not just `is_android()`), so enlarged indicators/scrollbars/drop-downs add their real width — else desktop under-reports clipping. (Rubber-duck finding.) |

---

## 3. The dev switch — "phone mode" (workstream A)

### 3.1 Invocation (no `runApp.sh` change required)

`runApp.sh` already does `exec ./venv/bin/python spectracsMain.py "$@"` and inherits the environment,
so the flags pass straight through:

```bash
./runApp.sh --phone                       # 412 dp wide, zoom 1.1 (Note20 defaults)
./runApp.sh --phone=360                    # narrow-density case
./runApp.sh --phone --phone-zoom=1.4       # bigger window (more vertical scroll)
QT_SCALE_FACTOR=1.6 ./runApp.sh --phone    # env override still wins over --phone-zoom
```

Magnification is implemented by setting **`QT_SCALE_FACTOR`** from `--phone-zoom` before `QApplication`
is built. Qt reads it at construction and **only changes the device-pixel-ratio** — the layout still
believes it is 412 dp wide, so the audit stays faithful while the window is comfortable to view.

Why default **1.1**: the window is 412×~883 dp. `QGuiApplication.availableGeometry()` reports **logical**
pixels (already divided by the scale factor), so the height branch (§3.2) self-corrects — a too-high
zoom never overflows, it just shrinks the visible logical height and adds vertical scroll. On the user's
**1920×1080** primary, `883 × 1.1 ≈ 970 px` fits the whole phone height under the taskbar; higher factors
are safe but start clipping the vertical slice. Override per-monitor with `--phone-zoom`.

### 3.2 Code change (spectracsMain.py) — *when implementation is requested*

**Three edits, all in `spectracsMain.py`:**

1. **Parse the flags early** (top of module, *before* `QApplication` at line 62 — `QT_SCALE_FACTOR`
   must be set before construction):
   - read `--phone` / `--phone=<W>` → `phoneMode: bool`, `phoneWidth: int = 412`.
   - read `--phone-zoom=<f>` → `phoneZoom: float = 1.1`.
   - **parse order matters:** test `--phone-zoom=` first, then `--phone=`, then bare `--phone`
     (`--phone` is a prefix of the others — naive `startswith` misfires). (Rubber-duck finding.)
   - if `phoneMode` and `QT_SCALE_FACTOR` not already in `os.environ`, set
     `os.environ["QT_SCALE_FACTOR"] = str(phoneZoom)` (explicit env wins → escape hatch).
   - optionally strip the flags from `sys.argv` before `QApplication(sys.argv)` (Qt ignores unknown
     args, so this is cosmetic).

2. **Gate the touch-density QSS on phone mode too** (lines 70–72) — change
   `if is_android():` to `if is_android() or phoneMode:` around the
   `styleSheet += ANDROID_TOUCH_DENSITY_QSS` append, so the enlarged indicators/scrollbars/drop-downs
   contribute their real width to the audit (D7).

3. **Branch the window sizing** — replace the current desktop `else` (lines 91–95, which forces
   `setMinimumWidth(screen/2)`):

   ```python
   elif phoneMode:
       h = min(883, int(QGuiApplication.primaryScreen().availableGeometry().height() * 0.95))
       mainContainerViewModule.setFixedWidth(phoneWidth)   # width is the invariant we audit against
       mainContainerViewModule.setFixedHeight(h)           # vertical scroll (PageWidget QScrollArea) handles overflow
       mainContainerViewModule.show()
   else:
       # ... existing half-screen desktop behavior, unchanged ...
   ```

`setFixedWidth` (not just minimum) is *intended* to guarantee the constrained width and clip children
past 412 — exactly as the phone's `showFullScreen` clips. **P1 acceptance check:** confirm Qt actually
clips (the window stays 412 and the 720px status bar is cut off) rather than *expanding* the window to
honor the child minimum. If it expands, also set `maximumWidth` on the central widget as a fallback.
Either way the offender is surfaced; the check is about width *fidelity*.

### 3.3 Fidelity limits (why P4 on-device stays mandatory)

Desktop phone mode is a **high-fidelity approximation, not pixel-identical**:

- **Font family/metrics differ** desktop vs Android → a few text-width overflows appear only on device.
- **Effective density** on the real Note20 depends on its Display-zoom setting (§1.1); `--phone=412`
  matches the default, but the device may report 360.

So P4 (build APK, verify) remains required — desktop just removes ~90% of the iterations.

### 3.4 Non-goals for the switch

- Not a production feature; a **developer tool** kept in the tree for future responsive work.
- No device-chrome frame, no orientation toggle, no preset picker — just width + fit-height. (Could
  add `--phone` presets later; not now.)

---

## 4. Audit — offenders found by grep (workstream B seed)

Concrete width-forcing call sites already located (`grep` over `sciens/`). The status bar is the
headline: it is **always on screen**, so its minimum propagates to the whole window.

| # | File:line | Code | Severity | Note |
|---|-----------|------|----------|------|
| A1 | `view/main/MainStatusBarViewModule.py:53` | `self.label.setMinimumWidth(int(480 * 1.5))` → **720px** | **Critical** | Always visible → forces entire window ≥720dp. Prime cause of right-edge clipping. |
| A2 | `view/home/HomeViewModule.py:24` | `spectralJobsOverviewViewModule.resize(600, 600)` | High | Absolute 600px on the Home landing content. |
| A3 | `view/playground/PlaygroundViewModule.py:196` | `label.setFixedSize(120, 36)` | Low | Small; likely fine at 412, verify. |
| A4 | `view/settings/…/SpectrometerCalibrationProfileViewModule.py:50` | `editCalibrationProfileButton.setMinimumWidth(100)` | Low | Fine standalone; watch in a wide button row. |
| A5 | `view/spectral/workflow/EvaluationResultRenderer.py:57` | `block.setFixedSize(96, 96)` | Low | Fixed colour swatch; fine. |

Beyond these explicit widths, the click-through walk should also catch the *implicit* culprits that
grep can't see: wide `QTableView`s (too many columns), non-wrapping `QLabel`s (missing
`setWordWrap(True)`), horizontal button rows that don't wrap, and any absolute-geometry layouts.

### 4.1 Method

1. Implement §3, launch `QT_SCALE_FACTOR=1.5 ./runApp.sh --phone`.
2. Click-through-review every screen (Home → each settings page → playground → workflow/eval →
   login/header). For each clipped control, record file:line + which fix pattern (§5) applies.
3. Produce the offender catalogue as the input to the fix phase.

### 4.2 All-screens visual review (P2 output, done 2026-07-03)

Method used: `MainViewModule` is a `QStackedWidget` that builds every page up-front with seeded
models. A throwaway offscreen harness (`scratchpad/shoot_screens.py`) booted the app in `--phone`
mode and grabbed each page as a PNG at **412 dp width, tall window** (so full content shows while
horizontal clipping stays visible). 13/14 pages captured (Wizard auto-starts a plugin run on show →
harness artifact, not a layout bug); reviewed with vision. Seeded from Edwin's annotated screenshot
of `SpectrometerProfileViewModule` (issues 1–8).

**The finding that reframes everything:** vertical spacing is driven by `addStretch()`/spacers, so the
*same* layout looks **cramped ("stick together") on the short phone** and **spread-out with huge gaps
on the tall desktop**. Fixed spacing tokens fix both simultaneously — this is why the fixes must be
generic, per Edwin.

Findings saturate to ~7 recurring root causes (→ generic rules in §5):

| Screen | Observed problem(s) | Rule |
|--------|---------------------|------|
| **(every screen)** | Header logo "SPECT" overflows right edge, collides with account icon; only the icon has a box | R6 |
| **(every screen)** | Vertical gaps uneven — stretch-driven, not tokenized (cramped on phone / huge on desktop) | R2 |
| SpectrometerProfile (05) | label/field misalignment (1,2); Edit beside graph clips (3); sensor table overflows + own scrollbar (4); combo text "…SlightHaze" clipped; section gaps (5,6,7) | R1,R3,R4,Rwrap,R2 |
| Settings (03) | Acquisition 4-button row clipped both sides; section styling inconsistent (some `QGroupBox`, some bare labels); big uneven gaps | R3,R7,R2 |
| SpectrometerProfileList (04) | two tables clipped right — Serial column runs off; title bars cut; breadcrumb abuts table (5) | R4,R2 |
| UserList (09) | table "Enabled" column clipped off right; horizontal scrollbar present but last col hidden behind frame | R4 |
| SpectrometerConnection (08) | large centered info text clipped **both** sides (no word-wrap); stretch-floated serial row | Rwrap,R2 |
| SpectralJob (01) | Oil/Light + averaged/raw toggles cramped; ‹›  nav arrows tiny; button rows tight | R3 |
| VirtualSpectrometer (07) | "save physically captured images" label rendered as a gray chip next to a bare box — reads oddly | R1,R7 |
| Home (00) | 4-button footer row ("New measurement" nearly edge-to-edge) tight at true 412 | R3 |
| **(Android-only, from Edwin)** | table gridlines render **red** on device | R5 |

Not yet re-reviewed (captured, findings expected to repeat): Import (02), User (10), Playground (11),
Login (13). Wizard (12) not captured. These add no new *rule* — same form/spacing/table patterns.

---

## 5. Generic layout ruleset (the fix framework)

**Design principle (Edwin):** do **not** patch screens one-by-one. The 8 annotations + all-screens
review (§4.2) collapse to **~7 reusable rules**. Each rule lives in *shared* code (a widget helper) or
*shared* QSS, so **both desktop and Android inherit the fix** from a single edit. Fixing the rules,
not the screens, is the whole strategy. Rules overlap with — and should reuse —
`SPEC_visual_harmonization.md` workstream A (the spacing system).

| Rule | What it is | Fixes | Both OS? |
|------|-----------|-------|----------|
| **R1 — FormRow / form grid** | One helper for every label+field pair → a 2-col grid with a **shared label-column width** per form; fields expand. Labels get one consistent style (kills the ad-hoc gray "chip" variance). | 1, 2, misalignment everywhere; VirtualSpectrometer chip | ✅ shared widget |
| **R2 — Spacing tokens (fixed, not stretch)** | Named spacing constants (`SPACE_SECTION`, `SPACE_ROW`, `SPACE_AFTER_BREADCRUMB`). **Remove vertical `addStretch()`** that distributes space — it's the cause of cramped-on-phone / spread-on-desktop. Reuse harmonization §3. | 5, 6, 7; every uneven-gap screen; desktop⇄phone consistency | ✅ shared tokens |
| **R3 — Responsive control row** | A container that lays children **horizontally when width ≥ threshold, else vertically**. The one genuinely responsive rule. | 3 (Edit→below graph); Settings/Home/SpectralJob button rows | ✅ desktop=row, phone=stack |
| **R4 — Table wrapper** | Standard table container: columns **fit the viewport** (stretch last / ResizeToContents + elide); horizontal scroll only when unavoidable and the **last column never hides behind the frame**. | 4; ProfileList, UserList, sensor table | ✅ shared widget |
| **R5 — Table/border color in shared QSS** | Define gridline/border color once in the global sheet; stop relying on the platform default that renders **red on Android**. | 4 (red borders) | ✅ shared QSS |
| **R6 — Header logo box** | Logo in a fixed **bordered box like the account icon**, contents scaled/clipped to fit; header sizes to the viewport (this also removes offender **A1**'s 720px min). | 8; header overflow on every screen; A1 | ✅ shared header |
| **R7 — Section container** | One section pattern app-wide (pick: titled `QGroupBox` *or* header+divider) instead of mixing group-boxes and bare labels. | Settings inconsistency; general tidiness | ✅ shared widget |
| **Rwrap — Long text wraps/elides** | Messages `setWordWrap(True)`; single-line values (combo current text, table cells) **elide** with `…`. | Connection message; clipped combo text | ✅ per-widget rule |

**Sequencing note:** R6 subsumes grep-offender **A1** (720px status bar) — do R6 first, it unblocks the
window actually being 412-clean. A2 (`resize(600,600)`) folds into R1/R2 when HomeViewModule is
touched. A3/A4/A5 are low and mostly fine at 412.

### 5.1 Per-rule design (P3a, done 2026-07-04)

Grounding: the app already has a layout framework — `PageWidget`
(`view/application/widgets/page/PageWidget.py`), `Metrics` token scale
(`logic/appliction/style/Metrics.py`: XS4 S8 M12 L16 XL24), `PageLabel` (the gray field-label chip),
and one generated QSS (`ApplicationStyleLogicModule`). **Most rules extend these; few need new code.**
Cross-refs to `SPEC_visual_harmonization.md` ("spec C/D/RD…") are noted where the mechanism already
exists.

**R1 — FormRow / shared label column.**
- *Current:* `PageWidget.createLabeledComponent(label, component)` builds a **separate** `QWidget`
  per row, each with its own `QGridLayout` at `columnStretch(0,30)/(1,70)` — a *proportional* split.
  At 412 dp, col0 = ~124 px; multi-word labels ("save physically captured images") overflow/wrap and
  neighbouring rows in different containers don't share a column edge → the misalignment in (1,2).
- *Change:* add `PageWidget.createForm(rows: list[(label, widget)])` that lays **all** rows in **one**
  shared `QGridLayout` — col0 = labels, col1 = fields — with a **fixed label-column width**
  (`labelColumnWidth`, default derived from the widest label, capped at `Metrics` * k ≈ 160 dp; beyond
  cap the `PageLabel` elides). Fields get `columnStretch(1,1)`. Keep `createLabeledComponent` as a
  thin single-row shim delegating to `createForm([...])`.
- *Both OS:* pure layout in shared base → every form aligns identically on desktop and phone.

**R2 — Spacing tokens + kill vertical stretch.** (mostly `SPEC_visual_harmonization` workstream A —
already landed as `Metrics`.)
- *Current:* `Metrics` exists and is used, but the "spread on desktop / cramped on phone" comes from
  form pages **not** setting `compactMainContainer=True` (only that flag adds the trailing
  `setRowStretch(row,1)` in `createMainContainer`; without it QGrid distributes slack across rows).
  The breadcrumb gap (5) is missing because `PageWidget_topMost`'s borderless container uses
  `setContentsMargins(0, Metrics.S, 0, Metrics.S)` — too tight under the title.
- *Change:* (a) set `compactMainContainer=True` on all **editor/form** pages (leave hub/menu pages
  filling, per DESIGN_GUIDE); (b) add token `SPACE_AFTER_BREADCRUMB = Metrics.L` and use it as the
  top margin of the top-most container; (c) sweep remaining raw-pixel margins to `Metrics`.
- *Both OS:* fixed tokens replace stretch → identical rhythm at any window height.

**R3 — Responsive control row (the one width-aware rule).**
- *Current:* `PageWidget.verticalLayout` is a **static** per-page bool (H or V), not width-driven.
- *Change:* new `ResponsiveRow(QWidget)` in `view/application/widgets/` — lays children horizontally
  while `width() >= threshold`, else stacks vertically; re-evaluates in `resizeEvent`. `threshold` =
  sum of children `sizeHint().width()` + spacing (auto), overridable. Apply to: graph+`Edit`
  (SpectrometerProfile → Edit drops below graph, fixes (3)), Settings "Acquisition" button row, and
  footer nav rows (`createNavigationGroupBox`).
- *Both OS:* desktop (wide) keeps the row; phone (narrow) stacks — same widget, no per-OS branch.

**R4 — Table wrapper (fit columns / reachable scroll).**
- *Current:* raw `QTableView`/`QListView`; columns exceed 412 → last column clipped behind the frame,
  horizontal scrollbar present but can't reveal it (ProfileList, UserList, sensor table).
- *Change:* util `applyTableLayout(view)` in a `view/application/widgets/table/` helper:
  `horizontalHeader().setStretchLastSection(True)`, per-column
  `setSectionResizeMode(ResizeToContents)` with the **last** column `Stretch`,
  `setTextElideMode(ElideRight)`, `setHorizontalScrollBarPolicy(AsNeeded)`, and a sane
  `minimumSectionSize`. When columns still exceed width, horizontal scroll reaches every column (no
  hidden last col). Route all table views through it.
- *Both OS:* shared util; identical behavior.

**R5 — Table border/gridline color in shared QSS (kills Android red).**
- *Current:* QSS already sets `QTableView { gridline-color: {border}; border: 1px solid {border}; }`
  and `QHeaderView::section` borders `{border}`. The **red** Edwin saw on device is likely a
  table-like widget **not** matched by the `QTableView` selector (e.g. a `QTableWidget`/custom sensor
  table) falling back to a platform default.
- *Change:* broaden selectors to `QTableView, QTableWidget` (+ `QAbstractItemView` gridline where
  applicable); add explicit `gridline-color`/`border` so no widget inherits a platform red. **Verify
  on device (P4)** — root cause is only confirmable on Android.
- *Both OS:* one QSS edit; desktop unaffected, Android red removed.

**R6 — Header logo box (also removes offender A1).**
- *Current:* `MainStatusBarViewModule` renders the logo into a 480×100 pixmap, `setScaledContents`,
  `setFixedHeight(70)`, and on **desktop** `setMinimumWidth(int(480*1.5))` = **720** (A1). The
  account button already has the target look: `1px solid #5A5A5A`, `border-radius:6px`, fixed
  70×70 box. The logo has **no box** and its ~480 dp width overflows a 412 window (clips "RACS",
  collides with the icon) — issue (8).
- *Change:* (a) wrap the logo `QLabel` in a bordered box mirroring the account button's QSS (same
  border/radius, `HEADER_CONTENT_HEIGHT`); (b) **drop the 720 minimum entirely** (both OS) — set the
  logo box `sizePolicy` to shrink, render the SVG with **KeepAspectRatio** (not `setScaledContents`,
  which distorts) so it fits the available header width; (c) reserve the account-button width so logo
  and icon never overlap.
- *Both OS:* removes the whole-window 720 min (A1) on desktop *and* the phone overflow; logo scales
  to fit either width.

**R7 — One section container.**
- *Current:* mixed — some sections are titled bordered `QGroupBox`, others bare `QLabel` headings
  (Settings). Machinery exists: `borderlessMainContainer`, `sectionLabel`/`plain` QGroupBox
  properties (spec C2/C2b/C11).
- *Change:* add `PageWidget.createSection(title, content)` producing **one** pattern app-wide — a
  borderless `sectionLabel` heading + `Metrics.S` gap + content (reserve bordered group-box for
  top-level panels only). Route all section headings through it.
- *Both OS:* shared helper; uniform look.

**Rwrap — long text wraps / elides.**
- *Current:* `QLabel` default no wrap → the SpectrometerConnection info text is clipped **both**
  sides; combo current-text clips without an ellipsis.
- *Change:* (a) `createMessageLabel(text)` helper with `setWordWrap(True)` for prose/status text;
  (b) for combos showing long values set `setSizeAdjustPolicy(AdjustToMinimumContentsLengthWithIcon)`
  + a minimum so the current text **elides with `…`**; table cells already elide (`ElideRight`).
- *Both OS:* per-widget rules; no branch.

**New code introduced (small):** `createForm` (R1) + `createSection` (R7) on `PageWidget`;
`ResponsiveRow` widget (R3); `applyTableLayout` util (R4); `createMessageLabel` (Rwrap). Everything
else is flag flips (R2), QSS edits (R5), and a header rework (R6). All shared → both OS benefit.

---

## 6. Implementation phases

```
+======+==================================+===================================================+==========================+========+========+
| PH   | GOAL                             | STEPS                                             | FILES                    | IMPL?  | DEP    |
+======+==================================+===================================================+==========================+========+========+
| P0   | Spec + offender seed             | width=logical-dp; --phone flag; grep offenders    | docs/SPEC_phone_width_*   | DONE   | --     |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P1   | The --phone dev switch           | 1a parse --phone[=W] / --phone-zoom=<f> (order!)  | spectracsMain.py         | DONE   | P0     |
|      | (3 edits, spectracsMain.py)      | 1b set os.environ QT_SCALE_FACTOR if unset        |   (top, before line 62)  |        |        |
|      |                                  | 1c gate ANDROID_TOUCH_DENSITY_QSS on phoneMode    |   (lines 70-72)          |        |        |
|      |                                  | 1d elif phoneMode: setFixedWidth+fit-height       |   (lines 91-95 else)     |        |        |
|      |                                  | 1e ACCEPT: PASS - real window = 412, CLIPS not exp |   (offscreen boot test)  |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P2   | All-screens AI visual review     | 2a offscreen harness shoots every stack page @412 | scratchpad/shoot_screens  | DONE   | P1     |
|      | -> catalogue + root causes       | 2b vision-review 13/14 pages                      | -> AUDIT tables (S4.2)    |        |        |
|      |                                  | 2c distil to ~7 generic root causes (S5 rules)    |                          |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P3a  | Generic ruleset DESIGN           | per-rule widget API / QSS keys / threshold (S5.1) | docs (this spec S5.1)    | DONE   | P2     |
|      | (R1..R7 + Rwrap)                 | grounded in PageWidget/Metrics/QSS; mostly extend  |                          |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P3b  | Generic ruleset IMPL             | R6 first (subsumes A1) -> R2/R1 -> R3 -> R4/R5    | shared widgets + QSS +   | no     | P3a    |
|      | (fix rules, not screens)         | -> Rwrap/R7; re-shoot --phone after each rule      | spectracsMain QSS        |        |        |
|      |                                  | screens inherit fixes; re-review until clean       | ./runApp.sh --phone      |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P4   | On-device verify                 | 4a build APK once (buildozer)                     | android/                 | no     | P3b    |
|      |                                  | 4b walk on real Note20; confirm red borders gone  | (device)                 |        |        |
|      |                                  | 4c catch font-metric residuals, rebuild if needed |                          |        |        |
+======+==================================+===================================================+==========================+========+========+
```

**P1 result (implemented 2026-07-03):** 3 edits in `spectracsMain.py` (import `os` + `_parsePhoneModeArgs`
& `QT_SCALE_FACTOR` before `QApplication`; QSS gate `is_android() or phoneMode`; `elif phoneMode` fixed-width
branch). Acceptance **PASS**: offscreen boot of the real `MainContainerViewModule` reports width **412** with
the 720px status-bar content clipped (not expanded) — no `maximumWidth` fallback needed. Ready for P2 audit.

**Notes**
- P0, P1, P2, **P3a** all **DONE**. **P3b in progress:** **R6 DONE** 2026-07-04 (`MainStatusBarViewModule`:
  logo now in a bordered box via `_AspectLogoLabel` scale-to-fit; 720px min removed → offender A1 gone;
  full "SPECTRACS" renders un-clipped at 412, verified by re-shoot). Remaining P3b: R2, R1, R3, R4/R5, Rwrap/R7.
- Strategy is **fix rules, not screens** (Edwin): each rule = one shared helper/QSS edit → every screen
  inherits it → desktop + Android both benefit. Per-screen patching is explicitly rejected.
- Recommend P3b order **R6 → R2 → R1 → R3 → R4/R5 → Rwrap/R7**, re-shooting `--phone` after each rule
  so regressions surface immediately (the harness makes this cheap).

---

## 7. Resolved (was: open questions)

1. **Default width = 412** — Note20 at *default* Display-zoom (confirmed 2026-07-03). `--phone=360`
   available for the narrow case.
2. **`--phone` is desktop-only** (D6). Android keeps `showFullScreen`.
3. **`--phone-zoom=<f>` CLI flag, default 1.1** (D3), tuned to the user's 1920×1080 monitor; explicit
   `QT_SCALE_FACTOR` env still overrides.

All P0 decisions settled — spec is ready for P1 implementation on request.
