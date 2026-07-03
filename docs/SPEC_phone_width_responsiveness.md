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

---

## 5. Fix patterns (workstream C — direction only, not yet designed per-site)

- Replace hardcoded `setFixedWidth`/`setMinimumWidth`/`resize` with **size policies** + sensible
  minimums (or none). E.g. A1: drop the 720 minimum; let the status label **elide** or wrap.
- `QLabel.setWordWrap(True)` for any text that can be long.
- Wrap wide content (tables, long forms) in a **`QScrollArea`** (horizontal where a table genuinely
  needs it) rather than forcing the window wide.
- Let button rows **wrap** (flow layout) or shrink instead of demanding a fixed total width.
- Prefer layouts over absolute geometry (A2).

Per-site fixes are a **follow-up spec/impl**, produced from the §4.1 catalogue.

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
| P2   | Width audit -> catalogue         | 2a walk every screen under --phone (click-through)| (observe only)           | no     | P1     |
|      |                                  | 2b log each clip: file:line + fix-pattern (S5)    | -> new AUDIT table (S4)  |        |        |
|      |                                  | 2c confirm seeds A1(720),A2(600) + implicit ones  |                          |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P3   | Fix, desktop-clean               | 3a A1: drop 720 min -> elide/wrap status label    | MainStatusBarViewModule  | no     | P2     |
|      |                                  | 3b A2: resize(600,600) -> layout/size-policy      | HomeViewModule           |        |        |
|      |                                  | 3c catalogue items: policies/wrap/scroll (S5)     | per-catalogue views      |        |        |
|      |                                  | 3d re-walk --phone after each -> until no clip    | ./runApp.sh --phone      |        |        |
+------+----------------------------------+---------------------------------------------------+--------------------------+--------+--------+
| P4   | On-device verify                 | 4a build APK once (buildozer)                     | android/                 | no     | P3     |
|      |                                  | 4b walk on real Note20, catch font-metric clips   | (device)                 |        |        |
|      |                                  | 4c fix residuals, rebuild if needed               |                          |        |        |
+======+==================================+===================================================+==========================+========+========+
```

**P1 result (implemented 2026-07-03):** 3 edits in `spectracsMain.py` (import `os` + `_parsePhoneModeArgs`
& `QT_SCALE_FACTOR` before `QApplication`; QSS gate `is_android() or phoneMode`; `elif phoneMode` fixed-width
branch). Acceptance **PASS**: offscreen boot of the real `MainContainerViewModule` reports width **412** with
the 720px status-bar content clipped (not expanded) — no `maximumWidth` fallback needed. Ready for P2 audit.

**Notes**
- P1 is the only *new-code* phase; P2 is pure observation; P3 edits existing views; P4 is device QA.
- Each phase gated by explicit request (spec-first). Recommend implementing **P1 alone first**, run
  the P1e acceptance check, *then* decide P2/P3 scope from what the audit actually shows.
- P3 rows are provisional — the real P3 work-list is P2's catalogue output, not this seed.

---

## 7. Resolved (was: open questions)

1. **Default width = 412** — Note20 at *default* Display-zoom (confirmed 2026-07-03). `--phone=360`
   available for the narrow case.
2. **`--phone` is desktop-only** (D6). Android keeps `showFullScreen`.
3. **`--phone-zoom=<f>` CLI flag, default 1.1** (D3), tuned to the user's 1920×1080 monitor; explicit
   `QT_SCALE_FACTOR` env still overrides.

All P0 decisions settled — spec is ready for P1 implementation on request.
