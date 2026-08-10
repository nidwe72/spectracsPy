# SPEC — THE SORET TRIM (440–460 → 448–460) AND THE BAND-MARKING AUDIT

> ## ✅ IMPLEMENTED 2026-08-10 — phases A1 · B1 · B2 · B3 · B4 · C1 · C2 · C3. **C4 (rig click-through) is
> Edwin's.** 344 tests green (318 app + 26 plugins). See **§20** for what the build actually found — three
> places where the plan was wrong and the code went a different way.

> **Status of the text below: as-designed.** Read §20 for the deltas. Edwin 2026-08-10: *"now I would like the DEV plugin
> to use the metric with the Soret band starting at 448 nm"* + *"tell me if the involved band regions used by
> the plugin are also marked correctly by the plugin at the according SpectralStep/s"*.
>
> **Two parts, one commit-sized change:**
> * **§2–§7** — the trim itself: what moves, what must move *with* it, and what must be measured before it ships.
> * **§8** — the marking audit, answered as a table: **the primary plot marks 3 of the 5 windows its own metrics
>   read**, and one of the three is the *wrong* window by 10 nm.

**Origin.** `SPEC_metric_research.md` §7.13 (S1, **ADOPTED by Edwin 2026-08-04**) and
`SPEC_first_presentable_state.md` §2 step 1. This document is the build sheet those two point at.

---

## 1 · The claim being shipped

`DOC_pedestal_correction.md` §7: the **440–447 nm bins read 2.0–2.6 DN against a reference near 88** — the
project had already written them off as *not measurements*. They sit inside the shipped Soret window, so
roughly a third of the metric's numerator window is contributed by bins that carry no signal, for every oil,
in every run.

Measured effect of removing them (`SPEC_metric_research.md` §7.13.2/§7.13.3, whole archive):

| axis | 440–460 | 448–460 | change |
|---|---|---|---|
| class *d* (green vs brown) | 6.91 | **7.37** | +6.7 % |
| within-green *d* | 1.21 | **1.34** | +10.7 % |
| dilution spread | 10.3 % | **8.8 %** | −14.6 % |
| `B_Soret` | 1.0272 | **0.6924** | ⚠ **the scale moves** |
| intercept `k` / *t*(k) | 0.2294 / 4.43 | 0.1214 / **2.92** | −47 % |
| refitted `r_Q` | −0.0184 | **−0.0133** | −28 % |

⭐ Corroborated post-rebuild: `SPEC_capture_quality.md` §16.28.2a — **`M448 + pedestal` transfers across a lamp
swap at 3 %** against 51 % for the raw ratio, and §16.27.5 finds *d* better on `M448` for all three oil pairs
(15.57 / 11.61 / 6.02 against 13.47 / 9.63 / 5.61).

⚠ **It is not free of consequence.** `SPEC_capture_quality.md` §16.28.3 measured `M448` **worse in 8 of 10
fills on run-to-run repeatability**, by ~20 % relative. ⇒ The corrected claim there: **`M448` is specifically
an illumination-robustness device**, better on discrimination and lamp/exposure transfer, not on re-seating
noise. Ship it for what it is.

---

## 2 · The one-line change, and the three things that must move with it

```python
PB_SORET_BAND = (448.0, 460.0)      # was (440.0, 460.0)
```

⛔ **Changing only that line ships a broken plugin.** Four things are welded to the window:

| # | what | why it moves | §  |
|---|---|---|---|
| **C1** | the constant + a frozen legacy alias | 14 diagnostics read `plugin.PB_SORET_BAND` and would silently redefine their published numbers | §3 |
| **C2** | `PB_R_Q` — the pedestal residual | it is **fitted through the Soret window**; −0.0184 belongs to 440–460 | §4 |
| **C3** | both gauge thresholds + gradient anchors | `B_Soret` falls ×~0.65–0.67 ⇒ every number on both scales moves | §5 |
| **C4** | the visible labels `Soret · 440–460 nm` | and with them a Director scenario hook and two tests | §6 |

---

## 3 · C1 — the constant, and the legacy freeze the diagnostics need

**The hazard is already documented in the file itself.** `DevSpectralPlugin` keeps
`PB_BASELINE_WINDOWS_LEGACY_600` alive purely so that ten diagnostics keep meaning what they meant:

> *"⚠ `PB_BASELINE_WINDOWS_LEGACY_600` ABOVE MUST KEEP MEANING 600-630 FOREVER … Repointing it would silently
> redefine every historical number in the specs."*

**`PB_SORET_BAND` is in exactly that position now.** These read it live and publish numbers off it:

`settling_sweep.py` *(the reference metric §16's whole evidence base is built on)*, `metric_bench.py`,
`pedestal_by_vintage.py`, `metric_walkthrough.py`, `far_anchor_sweep.py`, `far_anchor_probe.py`,
`scatter_correction_audit.py`, `red_band_two_lamps.py`, `soret_448_since_0729.py`, `metric_algebra_plots.py`,
`spar_three_oils.py`, `soret_right_edge_sweep.py`, `qband_shape.py`, `oil_forecast_410_680.py`.

⇒ **Add the frozen alias in the same commit, following the existing pattern:**

```python
# ⚠ MUST KEEP MEANING 440-460 FOREVER — the window every §16 number before 2026-08-10 was measured on.
PB_SORET_BAND_LEGACY_440 = (440.0, 460.0)
PB_SORET_BAND = (448.0, 460.0)          # SPEC_metric_research.md §7.13 S1, adopted 2026-08-04
```

**Decision D-diag — which diagnostics repoint.**

| group | action |
|---|---|
| archive-reproducing (`settling_sweep`, `metric_bench`, `pedestal_by_vintage`, `baseline_vs_raw`) | ⭐ **pin to `PB_SORET_BAND_LEGACY_440`** — their published tables must stay reproducible |
| forward-looking (`spar_three_oils`, `red_band_two_lamps`, `far_anchor_sweep`) | follow the shipped constant; they already quote `M448` as the headline |
| `soret_448_since_0729.py` | its `SHIPPED`/`TRIMMED` pair **inverts**; rewrite as `LEGACY_440` vs shipped, or retire it — the comparison it exists for is over |
| `oil_forecast_410_680.py` | ⚠ **contains a live falsifiable prediction** (`DOC_lamp_410_680.md` §5: the trim should move `M`). Leave its hard-coded 1.0272 alone; the trim is the experiment |

⚠ `settling_sweep.py`'s own `R_Q_620 = -0.0184` is a **second copy** of `PB_R_Q` and must be pinned in the same
breath as its Soret window, or the legacy pin is only half a pin.

---

## 4 · C2 — `r_Q` is window-paired, and this is the one real decision

`PB_R_Q = -0.0184` is not a property of the Q band. It is the intercept of a straight line fitted through
`B_Soret` against `B_Q`, divided by that line's slope — so **the numerator window is inside its derivation.**
§7.13.4 shows *why* it moves: the dead blue bins are where stray light compresses absorbance most, and that
compression is what bends the line and lifts the intercept. Trim them and 47 % of the intercept goes with them.

The plugin's own comment already forbids the mirror-image error for the anchor:

> *"move the anchor and the residual moves with it, so pairing these bands with that constant would be a
> category error."*

⇒ **Pairing 448–460 with −0.0184 is the same category error, one axis over.**

**⚠ But every published `M448 + ped` number uses −0.0184.** `spar_three_oils.py` and `red_band_two_lamps.py`
both import `R_Q_620 = -0.0184`, so §16.27's whole `M448+ped` column and §16.28.2a's **3 % lamp-transfer
headline** are on the *mismatched* pair.

**Decision D-rq — three options:**

| | option | consequence |
|---|---|---|
| **(a)** ⭐ **recommended** | ship `PB_R_Q = -0.0184` **now**, with the mismatch stated in the docstring; refit to −0.0133 at the threshold freeze (`SPEC_first_presentable_state.md` step 6) | one change at a time; the plugin reproduces §16.27/§16.28 **exactly**; the debt is written down and lands with the derivation that has to happen anyway |
| (b) | ship `-0.0133` in the same commit | window-consistent from day one — but it **invalidates every published `M448+ped` number**, including the 3 % lamp result, before anything has re-measured them |
| (c) | ship both, show two rows | the tab already carries three verdicts; a fourth on a fifth scale is the thing §16.20 warns against |

Sizing (b) if Edwin prefers it: `B_Q` runs 0.049–0.101 on the archive, so Δ`r_Q` = 0.0051 shifts the
denominator by **5–10 %**, *more for the low-`B_Q` greens than for the browns* — i.e. **not a rescale, a
re-shaping**. It compresses green-vs-brown separation slightly. That alone is reason to do it under a
derivation, not beside a window change.

---

## 5 · C3 — the thresholds. ⛔ Do not multiply by 0.674

Both shipped gauges read the trimmed numerator:

| gauge | metric | today | scale |
|---|---|---|---|
| `RoastPedestalGaugeView` *(primary; also the LIMS badge)* | `B_Soret / (B_Q − r_Q)` | **T = 10.6**, band 14.0→7.5 | green 12.331 ± 0.465, brown 8.590 ± 0.156 |
| `RoastFar620GaugeView` | `B_Soret / B_Q` | **T = 12.5**, band 19.0→9.0 | green 15.559 ± 0.615, brown 10.160 ± 0.197 |

⚠ **The obvious move — scale both by §7.13's 0.674 — is wrong, and the archive says so.** Per-run
`M448 / M440` from `SPEC_capture_quality.md` §16.27's table:

| fill | class | `M448 / M440` |
|---|---|---|
| A Spar ggA | green-ish | 0.672 / 0.667 / 0.668 |
| C Spar Premium | mid | 0.653 / 0.651 / 0.648 |
| B Spar S-Budget | brown | 0.642 / 0.653 / 0.652 |

**The factor is class-dependent (0.642–0.672) — which is exactly why the trim improves `d`.** A single 0.674
multiplier sits *above* every observed factor and would therefore move the line **toward brown**, silently
re-classifying borderline greens. ⛔ Not acceptable for a change advertised as "free".

⇒ **Derive, don't rescale. The pre-implementation measurement task (D-thresh):**

1. New diagnostic `diagnostics/soret_448_thresholds.py` (or extend `soret_448_since_0729.py`): over **every
   post-rebuild run** (2026-07-29 onward, the §16.11 rig state), emit per-run `M448` and `M448+ped` with the
   shipped anchors and whichever `r_Q` D-rq selects.
2. Report per class: mean ± sd, **min green / max brown**, the empty corridor, Cohen's *d*.
3. Set each `T` at the **corridor midpoint** (`RoastFar620GaugeView`'s own derivation policy, §16.20.4), then
   **verify no archived run changes class** against today's shipped thresholds. A run that flips is a finding,
   not a rounding error — report it, do not absorb it.
4. Rescale `_ANCHORS` / `_BAND_LEFT` / `_BAND_RIGHT` so the gradient keeps its shape: pivot at the new `T`,
   edges kept clear of the extreme observed runs (the docstrings state that intent explicitly — preserve it).
5. **Rewrite both gauge docstrings** with the new scale block. Those docstrings are the only written record of
   where a threshold came from; a stale one is worse than none.

⚠ **`RoastPedestalGaugeView`'s T = 10.6 is INHERITED, not derived** (from the 600–630 scale, §16.10.17d) and
§16.27.6 has already shown it rejects both supermarket ggA oils. ⭐ **Do not fix that here.**
`SPEC_first_presentable_state.md` step 6 owns the real derivation, on the capillary corpus. This change owes
only *"the same verdicts, on the new scale"*.

⚠ `RoastGaugeView` (T = 4.4, raw Soret/Q) and `RoastBaselineGaugeView` (T = 10.6, 600–630) are **imported but
no longer instantiated** by the plugin. They still read `PB_SORET_BAND` indirectly through the caller. Either
re-derive them too, or ⭐ **delete the two dead imports** and mark both classes legacy — recommended, it is one
line each and `test_three_verdicts.py` already asserts `RoastGaugeView(` is absent from the source.

---

## 6 · C4 — the labels, and the two things downstream of them

Every visible string that names the window (`DevSpectralPlugin.__newEvaluationResult`):

| line | today | after |
|---|---|---|
| metric row | `"Soret · 440–460 nm"` | `"Soret · 448–460 nm"` |
| its tooltip | *"mean absorbance over the 440–460 nm Soret right-hand slope…"* | 448–460 + ⭐ **one clause on why**: *"…the 440–447 bins are below the DN floor and are excluded"* |
| `Pigment ratio · clarity` tooltip | *"on the NEW bands (440–460 / 510–540)"* | 448–460 / 510–540 |
| `Soret · baseline` tooltip | *"mean 440–460 absorbance measured above the fitted 520–540/620–630 baseline"* | 448–460 |

⛔ **The label rename breaks the Director screencast, silently.** `automation/scenarios/measurement_bench.py`
points the camera at `"workflowItem.soret_440_460_nm"`, a slug derived from the label text. After the rename
the widget is `workflowItem.soret_448_460_nm` and the lookup finds nothing.

⇒ **Update in the same commit:** `automation/scenarios/measurement_bench.py` (`METRIC_FIELDS`), and
`tests/test_director_cut_enablers.py` (two assertions on the slug rule + the objectName stamp).

⚠ **Saved runs keep the old label.** `DbMeasurement` stores rendered view-models, so archived measurements will
show `Soret · 440–460 nm` beside new ones showing 448–460. **That is correct and must not be migrated** — the
old runs *were* measured on the old window. Worth one line in the release note.

---

## 7 · What deliberately does NOT change

| | why |
|---|---|
| `WAVELENGTH_MIN_NM = 440.0` | ⭐ the trim is a **metric-window** change, not a capture change. Keeping 440–447 captured is what lets the DN guard (§16.23.8) and the diagnostics keep *measuring* the dead-bin regime, and keeps the stored spectra comparable with the whole archive. Narrowing the clamp would destroy both |
| `declaredEvalBands()` | still correct by construction; the bluest declared edge simply moves 440 → 448 (`BLUE_BAND`/`BLUE_PEAK` start at 450). The `__assertWindowCoversBands` guard keeps passing |
| the legacy "Metrics (dev)" tab | untouched. Its `BLUE_BAND` 450–490 is a different construction and the whole point of the tab is cross-tab continuity |
| the colour chips | integrate the whole curve; unaffected by a band window |
| the dose recipe | ⚠ §16.23.6f: *"the dose and the 448 trim are ONE decision"* — at ×1.20 the 440–447 bins fall to 3–5 DN. That coupling is **already accounted for**: the trim is what makes the stronger dose safe, not a reason to re-open it here |

**Publish path.** The window lives in a signed artifact, so this needs a **version bump + re-sign + re-assign**
(M3 B4/B5). `SPEC_first_presentable_state.md` step 1 deliberately puts a **no-op version bump first**, to prove
the publish path works before a real change rides on it. ⭐ **Keep that order** — it is the only rehearsal the
F16 first-real-publish runbook gets.

---

## 8 · ⭐ THE MARKING AUDIT — the answer to the second question

**Short answer: no.** The primary plot marks **3 of the 5** windows its own tab's metrics read, and one of the
three is the *wrong window*, off by 10 nm on the left edge. The legacy plot marks 3 of 5.

### 8.1 Step `Absorption (bands)` — the primary, despiked plot

Marked: `PB_SORET_BAND`, `GREEN_BAND` (510–540), `PB_Q_BAND` + a Q-peak marker.

| window | read by | marked? |
|---|---|---|
| Soret 440–460 *(→ 448–460)* | both gauges, `Soret ·`, `Soret · baseline`, both pigment ratios, the LIMS badge | ✅ |
| Q 560–580 | both gauges, `Q ·`, `Q · baseline`, both ratios, the badge | ✅ |
| Clarity 510–540 | `Clarity ·` row, `Pigment ratio · clarity` | ✅ |
| ⛔ **baseline near anchor 520–540** | ⭐ **both gauges + the LIMS badge** (`PB_BASELINE_WINDOWS`) | ⛔ **NOT marked** |
| ⛔ **baseline far anchor 620–630** | ⭐ **both gauges + the LIMS badge** | ⛔ **NOT marked at all** |

⛔ **Defect B1 — the far anchor is invisible.** 620–630 is the most load-bearing window on the tab: §16.20 moved
it there deliberately, §16.12.12 established it **measures pigment rather than correcting**, and sweeping its
edge inward collapses *d* from 2.88 to 0.94. **Every verdict on the screen runs through it and the plot does
not draw it.** A reader cannot see that the metric is three-region.

⛔ **Defect B2 — the near anchor is impersonated.** What is drawn at that place is `GREEN_BAND` **510–540**, a
*different* window feeding only the clarity row. The anchor is **520–540**. One grey block, two meanings,
10 nm apart — a reader who assumes the shading shows the baseline fit is wrong on the left edge and cannot
tell.

⚠ **Defect B3 — the curve is not the one the numbers are on.** The plot draws the **despiked** absorbance; the
gauges read band means **above the fitted 520–540/620–630 line**. The line itself is never drawn, so the
"height above baseline" that the verdict *is* cannot be seen. `Soret · baseline` and `Q · baseline` are on the
tab specifically so a reader can see what the correction did — the plot could show it in one stroke.

### 8.2 Step `Absorption (bands, dev)` — the legacy plot

Marked: `BLUE_BAND` (450–490), `GREEN_BAND` (510–540), `Q_SEARCH` (565–590) + the Q marker.

| window | read by | marked? |
|---|---|---|
| Blue 450–490 | `Soret A_blue`, `Pigment ratio · legacy`, `G' (alt.)` | ✅ |
| Green 510–540 | `Clarity A_green`, `Greenness G`, `Pigment ratio · legacy` | ✅ |
| Q search 565–590 | `Pigment D_Q` peak search | ✅ |
| ⛔ **Q baseline 555–600** | ⭐ `D_Q` — and therefore `Greenness G`, the tab's headline | ⛔ **NOT marked** |
| ⚠ blue peak 450–465 | the **reference gate** that decides which λ enter `A_blue` | ⚠ not marked *(defensible — it is a gate on the reference, not a window on this curve)* |

⛔ **Defect B4 — `D_Q`'s local baseline anchors are invisible.** `D_Q` is a peak height **above a chord drawn
across 555–600**, and that chord is the whole construction. The plot marks where the peak is *searched* and
hides what it is measured *against*.

### 8.3 Shared renderer defects

⚠ **Defect B5 — band labels are dropped by both renderers.** `SpectrumPlotView.addBand(lo, hi, label)` accepts
a label and `toJson`/`fromJson` round-trip it, but `QtWorkflowRenderer` (`LinearRegionItem`, one grey brush)
and `MatplotlibWorkflowRenderer` (`axvspan`, `color="0.5"`) both **ignore `band[2]`**. ⇒ Every shaded block
looks identical; nothing on screen or on paper says which is Soret and which is Q. With the anchors added
(B1/B2) there would be **five** identical grey blocks, two of them overlapping.

⚠ **Defect B6 — marker labels are asymmetric.** `matplotlib` annotates `marker[1]`; the Qt renderer draws a
bare dashed line. The `"Q"` label appears **on paper but not on screen** — the one place the two renderers are
supposed to agree by design (M2: *"preview = PDF"*).

### 8.4 ⇒ The proposed fix

**F1 — mark what is read.** ⭐ **SETTLED by Edwin 2026-08-10 — see §14 for the exact four-window set** (the
clarity 510–540 shading is *dropped*, which is also what dissolves defect B2). Legacy plot: add
`*Q_BASELINE` (555–600).

**F2 — label every band.** `.addBand(*self.PB_SORET_BAND, "Soret")`, `"Q"`, `"clarity"`, `"anchor"`, `"anchor"`.
Free at the call site; needs F3 to be visible.

**F3 — honour the label in both renderers.** Small text at the top of the span, same string on both. ~5 lines
each. Do both together or the PDF drifts from the screen.

**F4 — distinguish anchors from measurement bands.** Decision **D-bandstyle**:

| | option | note |
|---|---|---|
| **(a)** ⭐ **recommended** | extend to `addBand(lowNm, highNm, label=None, color=None)`; anchors drawn in a distinct hue | symmetric with `addTrace(spectrum, label, color)`; JSON already serialises the tuple as a list, so it round-trips unchanged; both renderers already map colour names |
| (b) | label only, all grey | cheapest; two overlapping grey blocks (510–540 vs 520–540) still read as one |
| (c) | leave B1/B2 unmarked | ⛔ the status quo — the verdict's own windows stay invisible |

**F5 — draw the fitted baseline** on the primary plot as a third trace (`linearBaselineCorrected` already
computes the fit). ⭐ Optional but high value: it makes B3 visible and turns the two `· baseline` rows into
something a reader can *see*. Also fixes the Qt marker label (B6) while in the file.

⚠ **F1 alone changes a test.** `test_dev_plugin_improved_colour.py::test_second_band_marked_spectrum_uses_the_pb_bands`
asserts `windows == {(440,460),(510,540),(560,580)}` — it becomes `{(448,460),(510,540),(520,540),(560,580),(620,630)}`.

---

## 9 · Files touched

| file | change |
|---|---|
| `spectracs-plugins/…/dev/DevSpectralPlugin.py` | C1 constant + legacy alias, C2 `PB_R_Q` docstring, C4 labels/tooltips, F1/F2 bands, F5 baseline trace, dead gauge imports |
| `…/dev/RoastPedestalGaugeView.py`, `RoastFar620GaugeView.py` | C3 threshold + anchors + docstring rewrite |
| `spectracsPy-model/…/view/SpectrumPlotView.py` | F4(a) `addBand(..., color=None)` |
| `spectracsPy/…/render/QtWorkflowRenderer.py` | F3 label, F4 colour, B6 marker label |
| `spectracsPy-core/…/report/MatplotlibWorkflowRenderer.py` | F3 label, F4 colour |
| `diagnostics/soret_448_thresholds.py` *(new)* | D-thresh, §5 |
| `diagnostics/settling_sweep.py` + the archive-reproducing set | D-diag pins |
| `automation/scenarios/measurement_bench.py` | the slug |
| `tests/test_director_cut_enablers.py`, `test_three_verdicts.py`, `spectracs-plugins/tests/test_dev_plugin_improved_colour.py` | labels, `PB_R_Q`, band set |

**Order:** ① no-op version bump + publish rehearsal → ② D-thresh measurement run → ③ code + tests →
④ publish + assign → ⑤ click-through on the bench (both plots, both gauges, the PDF).

---

## 10 · Open decisions

| id | question | recommendation |
|---|---|---|
| **D-rq** | ship `r_Q` = −0.0184 or the refitted −0.0133? | ⭐ **−0.0184 now**, refit at the threshold freeze (§4a) |
| **D-thresh** | how are the two thresholds set? | ⭐ **derived on the post-rebuild archive**, corridor midpoint, verified no archived run flips class — ⛔ **not** a 0.674 multiply (§5) |
| **D-diag** | which diagnostics pin to the legacy window? | ⭐ the four archive-reproducing ones (§3) |
| **D-bandstyle** | how are anchor bands distinguished? | ⭐ **(a)** `addBand(..., color=None)` + labels in both renderers (§8.4) |
| **D-deadgauges** | ⚠ *"dead"* = **imported but never instantiated**. `RoastGaugeView` (T = 4.4, raw Soret/Q) and `RoastBaselineGaugeView` (T = 10.6, 600–630) were the first two Ampeln; §16.20 replaced them with the two that ship. The imports are still at the top of `DevSpectralPlugin.py`, so the classes look live and their stale thresholds look current. Nothing renders them | ⭐ drop the two imports, mark both classes legacy in their docstrings (§5). ⛔ Do **not** re-derive their thresholds for 448 — that would be maintaining a scale nobody reads |
| **D-frames** | 150 → 60 frames per burst | ⭐ **yes** (§11) — the frame count is not the limiting error term and the archive says so |
| **D-levels** | shape of the new plot primitive | ⭐ **one** `addLevel(value, lowNm=None, highNm=None, …)` covering both the band-mean bars and the DN guard lines (§12.2) |
| **D-dnguard** | what is the upper guard line? | ⭐ **60 DN** — §16.23.8's own two-sided rule (`< 16` too concentrated, `> ~60` too dilute) — **plus** the 20/40 target pair as faint dotted lines, all four as plugin constants (§13) |

---

# SECOND ROUND — Edwin 2026-08-10

> Five further asks, in the same commit area. §11 is independent of the trim; §12–§14 extend the §8 audit
> and are governed by Edwin's rule: ⭐ **"everything should be done by the corresponding plugin-view-model in
> the most generic way"** — i.e. **no plugin-specific drawing code in either renderer**. What the plugin knows
> (which windows, which values, which guard levels) it *declares*; what the renderer knows (how a span, a bar
> or a level line looks) it *draws*.

## 11 · The capture burst: `FRAMES` 150 → 60

```python
FRAMES = 60   # was 150
```

**Edwin:** *"I also think that 60 frames to be captured per measurement are enough."* ⭐ **Agreed, and the
archive supports it rather than merely tolerating it.**

**The argument.** Frame averaging only attacks **temporal** noise, and it does so as 1/√N — so 150 → 60 costs
a factor **√(150/60) = 1.58×** on that one term. What that term is worth is measured:

| error term | size | source |
|---|---|---|
| **instrument floor** — null run 003, nothing moved between the two bursts | **0.42 % on `M`** | §16.26.1 |
| careful jar reseat, rms | **4.47 %** | §16.26.3 |
| archive run-to-run CV | **3–5 %** | §16.26.0 |

⇒ **Worst case the floor goes 0.42 % → 0.66 %, against a reseat term of 4.47 %.** Still ~7× below the thing
that actually limits the measurement, and §16.26.1's conclusion — *"the instrument is not the error"* — is
nowhere near being overturned by it.

⚠ **And 0.66 % is an over-estimate.** Run 003's 0.42 % is not pure shot noise: it contains lamp and AE drift
between the two bursts, which more frames do not fix. Only the shot-noise share scales with 1/√N, so the true
increase is smaller than the arithmetic above.

⭐ **What it buys is more than convenience.** At ~30 fps the burst drops from ~5 s to ~2 s, i.e. **~2.5× less
time per capture and ~2.5× less time in the beam.** §16.22.1a measured the sample at ≤ 40 °C in-beam and
estimated **3–5× faster degradation** there, and §16.11.16 turned "measure within the hour" into a *verdict*
rule. ⇒ Shorter bursts are a small move in the right direction on the one axis that is currently biting, and
they make §16.11.17's decay-rate run (0/1/2/4/24 h in one evening) materially cheaper to execute.

⚠ **Safe against the frame machinery:** `RobustReductionLogicModule.MIN_FRAMES_TO_REJECT = 5`, so per-frame MAD
rejection still has ample population at 60; §14.8's C3 top-up (grab-until-N-accepted, cap N+margin) is
unaffected. `CapturePanel` seeds its combo from `step.getFrames()`, so the declaration is all that changes.

⚠ **Not the same question as the dev bench's own defaults.** `PumpkinOilPlugin.FRAMES = 5` is untouched.

**Optional 10-minute control** (not a gate): two null runs back to back, one at 60 and one at 150, and compare
the `M` error against 003's 0.42 %. Cheap, and it converts the argument above into a measurement.

## 12 · The plot view-model — three asks, one primitive set

### 12.1 What has to become drawable

| # | Edwin's ask | today |
|---|---|---|
| **P1** | *"the means … a bar that consumes the width of the band, rendered at the corresponding height"* | ⛔ nothing — the means exist only as text rows |
| **P2** | *"the slope of the baseline … visualized"* | ⛔ nothing — the fitted line is invisible (defect B3) |
| **P3** | *"the upper DN guard value rendered by a line as the lower one"* | ⚠ the **lower** line is drawn, but **hard-coded in both renderers** (`__LOW_DN_GUARD = 16.0`, `ax.axhline(16.0)`) — the plugin cannot state it, change it, or add a second one |

⇒ P3 is the one that proves the rule: today a *renderer* owns a *measurement constant*. That is backwards, and
it is why the plugin cannot add the upper line without editing two renderers.

### 12.2 ⭐ The primitive — `addLevel`, the horizontal twin of `addMarker`

`SpectrumPlotView` already has the vertical primitive: `addMarker(nm, label)` → a vertical line at an x. What
is missing is its **horizontal** counterpart, and *one* primitive covers both P1 and P3:

```python
def addLevel(self, value, lowNm=None, highNm=None, label=None, color=None, style=None):
    """A horizontal annotation at y=`value`.
       lowNm/highNm omitted -> a full-width guide line   (the DN guards, P3)
       lowNm/highNm given   -> a BAR spanning that band  (the band means, P1)"""
    self.levels.append((value, lowNm, highNm, label, color, style))
    return self
```

**Decision D-levels — why one primitive and not two:** a band-mean bar *is* a level line clipped to an x-range.
Two names (`addGuide` + `addBandLevel`) would duplicate the renderer branch for no gain, and the round-trip
would carry two lists instead of one. ⚠ The alternative — hanging `level=` on `addBand` — is rejected: a level
is a **value** (it moves with the data, it belongs to the metric) while a band is a **window** (a constant of
the method). Bundling them would force a redraw of the shading whenever a number changes, and it would make
"a guide line with no band" unexpressible.

**P2 needs no new primitive.** The fitted baseline is a *curve*, so it is a trace:
`.addTrace(fittedLine, "baseline 520–540 / 620–630", "#b06000", style="dashed")` — the plugin computes it (the
fit already exists inside `SpectrumFeatureUtil.linearBaselineCorrected`; ⚠ it must **expose** the fitted line,
which today it consumes internally and discards). One addition to `addTrace`: `style=None|"dashed"|"dotted"`,
mapped to `pg.mkPen(style=Qt.PenStyle.DashLine)` and matplotlib `ls="--"`. The plugin's own comment currently
says *"SpectrumPlotView carries no linestyle, so colour distinguishes them"* — this retires that limitation,
and a dashed baseline against solid data is the right reading of *"visualize the slope"*.

### 12.3 ⭐⭐ The identity that makes P1 and P2 one picture

This is the part worth getting right, because it makes the metric **readable off the plot**:

$$\text{mean}(A_{\text{despiked}}) - \text{mean}(\text{line}) = B_{\text{Soret}}$$

⇒ **Draw the bar at the raw band mean of the plotted curve, draw the fitted line beneath it, and the vertical
gap between them IS the baselined value the gauges divide.** No third artefact, no "corrected curve" tab, no
explaining. The two `· baseline` rows stop being numbers a reader has to trust and become a distance on screen.

⭐ **And the anchors prove themselves.** A bar drawn over 520–540 and one over 620–630 will land **exactly on
the fitted line** — that is what "fitted through the anchors" means. A reader who sees the two anchor bars
sitting on the line and the Soret bar floating high above it has understood the whole construction in one
glance. ⚠ It is also a live self-check: if an anchor bar ever sits *off* the line, the fit is broken.

⇒ **Draw a bar on all four declared bands** (§14), not only the two the ratio uses.

⚠ **"Beneath", literally — not beside.** The fitted line is a full-width dashed curve running *under* the data
across the whole x-range. It **touches** the curve at the two anchors (that is what the fit means) and the
curve **rides above it** at S and at Q, because both band values are positive. There is no second panel and
nothing sits side by side.

### 12.3a The picture, drawn

Illustrative fill-A numbers (`SPEC_capture_quality.md` §16.27: `A_Soret` 0.90, `A_Q` 0.189, `B_Sor620` 0.866,
`B_Q620` 0.066 ⇒ the fitted line runs ≈ 0.041 under the Soret and ≈ 0.133 under Q). Schematic, not to scale.

```
  ░░░ = addBand    (the grey region)            ●●● = the despiked A(λ) — the plotted curve
  ━━━ = addLevel   (bar at the band mean)       ┄┄┄ = addTrace(style="dashed") — the fitted baseline
  │   = the GAP — and the gap IS the metric

  A(λ)      S 448-460      near 520-540    Q 560-580        far 620-630
1.00 ┤  ━━━━━                ░░░░░░░     ░░░░░░░          ░░░░
     │  ░░│●░                ░░░░░░░     ░░░░░░░          ░░░░
0.80 ┤  ░░│░●●               ░░░░░░░     ░░░░░░░          ░░░░
     │  ░░│░░ ●●             ░░░░░░░     ░░░░░░░          ░░░░
0.60 ┤  ░░│░░   ●●           ░░░░░░░     ░░░░░░░          ░░░░
     │  ░░│░░     ●●         ░░░░░░░     ░░░░░░░          ░░░░
0.40 ┤  ░░│░░       ●●       ░░░░░░░     ░░░░░░░          ░░░░
     │  ░░│░░         ●●●    ░░░░░░░     ░░░░░░░          ░░░░
0.20 ┤  ░░│░░            ●●●●░░░░░░░    ●━━━━━━━●   ┄ ┄ ┄●━━━━●●
     │  ░░│░░ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄━━━━━━━●●●●┄░┄░┄░┄░┄●●●●●●●● ░░░░
0.00 ┤┄ ┄░┄░┄                ░░░░░░░     ░░░░░░░          ░░░░
     └──────────────────────────────────────────────────────────
     440   460   480  500   520   540   560   580   600  620  636
```

**Read it as:** the `S` bar is pinned near the top; the dashed line passes far below it; **that whole vertical
run `│` is `B_Soret` = 0.87** — the metric's numerator, as a distance. The `near` bar at 520–540 sits *on* the
dashed line, and so does the `far` bar at 620–630. Nothing about the construction is left to the caption.

The red half carries the small numbers, so it needs its own y-scale — which is also the honest reason the
one-plot version cannot show everything:

```
  A(λ)          near 520-540      Q 560-580              far 620-630
0.22 ┤  ░░░░░░░░░░░        ░░░░░░░░░░░                 ░░░░░░
     │  ░░░░░░░░░░░        ░░░●●●●●░░░                 ░░░░░░
0.18 ┤  ░░░░░░░░░░░        ━━━━━━━━━━━                ┄━━━━━━●┄
     │● ░░░░░░░░░░░      ●●░░░░░│░░░░░●●    ┄ ┄ ┄ ┄ ┄●●●░░░░░ ●●
0.14 ┤ ●░░░░░░░░░░░    ●●  ░░░░░┄░┄░┄░┄ ●●●●●  ●●●●●●  ░░░░░░
     │  ●●●░░░░░░░░ ●●● ┄ ┄░┄░┄░░░░░░░       ●●        ░░░░░░
0.10 ┤  ━━━━━━━━━━━●       ░░░░░░░░░░░                 ░░░░░░
     │┄ ░░░░░░░░░░░        ░░░░░░░░░░░                 ░░░░░░
0.06 ┤  ░░░░░░░░░░░        ░░░░░░░░░░░                 ░░░░░░
     └──────────────────────────────────────────────────────────
       520       540      560       580      600      620    636
```

⚠ **Corrected by the rubber-duck pass (§16 duck #1):** the anchor bars sit on the line **to within a small
residual**, not exactly — the fit is a weighted least-squares through *every* anchor point, not a chord
through the two window means. The *gap = metric* identity below is exact; the *on the line* property is not.

⭐ **Three things this second view makes visible at once, and each of them is a claim §16 argues in prose:**

1. **`B_Q` is the small number.** The `Q` bar floats **0.056** above the line against the Soret's 0.87 — a
   **16× asymmetry**, which is exactly the error budget of `spectracs-error-budget-asymmetry` / §16.24 seen
   as a picture. A reader who sees this understands immediately why the denominator is the fragile half.
2. ⭐ **The baseline RISES to the red** — the `near` bar sits at 0.10, the `far` bar at 0.18. That slope is not
   scattering (which falls with λ); it is §16.12.12's finding that **the far anchor MEASURES**, sitting on
   protochlorophyll's Qy band. *"Visualize the slope"* turns out to visualize the most contested assumption in
   the metric.
3. **Both anchor bars lie on the dashed line** — the running self-check of §12.3.

⚠ The two anchor bars sitting on the line is *near-arithmetically forced*, so it proves the **rendering**, not
the physics. It is still worth drawing: when it ever fails by more than the §16 duck-#1 residual, the fit or
the band declaration is wrong.

### 12.4 What the plugin then declares — `Absorption (bands)`

```python
fit = util.fittedBaseline(despiked, self.PB_BASELINE_WINDOWS)     # new accessor, §12.2
view = (SpectrumPlotView(despikedAbsorption, title="A(λ) — PB bands (despiked)")
        .addTrace(fit, "baseline 520–540 / 620–630", "#b06000", style="dashed")   # P2
        .addBand(*self.PB_SORET_BAND,       "S")                                  # §14
        .addBand(*self.PB_BASELINE_WINDOWS[0], "near anchor")
        .addBand(*self.PB_Q_BAND,           "Q")
        .addBand(*self.PB_BASELINE_WINDOWS[1], "far anchor")
        .addLevel(soretMean, *self.PB_SORET_BAND, label="S̄")                      # P1
        .addLevel(nearMean,  *self.PB_BASELINE_WINDOWS[0])
        .addLevel(qMean,     *self.PB_Q_BAND,     label="Q̄")
        .addLevel(farMean,   *self.PB_BASELINE_WINDOWS[1])
        .addMarker(newQLambda, "Q")
        .setShownInReport(True))
```

⚠ **The means passed here must be the means of the plotted curve** (the despiked absorbance), *not* the
baselined ones — otherwise §12.3's identity breaks and the bars float free of the picture. The baselined
values stay where they are: the `Soret · baseline` / `Q · baseline` metric rows.

### 12.5 Renderer work, both sides, kept symmetric

| renderer | levels | trace style | band label/colour |
|---|---|---|---|
| `QtWorkflowRenderer` | `pg.InfiniteLine(angle=0)` when unranged; `pg.PlotDataItem([lo,hi],[v,v])` when ranged | `mkPen(style=…)` | text item at span top + brush colour |
| `MatplotlibWorkflowRenderer` | `ax.axhline` / `ax.plot([lo,hi],[v,v])` | `ls=` | `annotate` + `axvspan(color=)` |

⚠ **Do both in the same commit.** M2's contract is *"the preview IS the PDF"*; B6 (the `"Q"` marker label
drawn on paper but not on screen) is what happens when they drift. Fix B6 while in the file.

**Serialization.** `toJson`/`fromJson` gain `"levels"` and the trace `"style"` — both are additive, and
`fromJson` must tolerate their absence so **saved runs from before this change still load** (the same
back-compat rule the `bands`/`markers` lists already follow).

## 13 · The DN guard becomes declared data

**Today:** `QtWorkflowRenderer.__LOW_DN_GUARD = 16.0` and `MatplotlibWorkflowRenderer`'s `ax.axhline(16.0)` —
two copies of a measurement constant living in view code, drawn automatically whenever `axis="dn"`.

**After:** the renderer draws only what is declared, and the *plugin* declares both guards on its
`Reference vs Sample` step:

```python
SpectrumPlotView(title="Reference vs Sample", axis="dn")
    .addTrace(...).addTrace(...)
    .addLevel(self.DN_GUARD_LOW,  label="16 DN — too concentrated", color="#c87a3c", style="dashed")
    .addLevel(self.DN_GUARD_HIGH, label="60 DN — too dilute",       color="#c87a3c", style="dashed")
```

**Decision D-dnguard — the upper value is 60, not 40.** §16.23.8 states the guard two-sided: **`< 16 DN` too
concentrated, `> ~60 DN` too dilute, `20–40 DN` in window.** 16 and 60 are the *rejection* edges and are the
true counterparts of each other; 20–40 is the *target*, a different statement.

⭐ **My lean: draw all four now, in two visual weights.**

| lines | value | weight | says |
|---|---|---|---|
| guards | **16 / 60 DN** | dashed, amber | *reject* — outside this the fill is wrong |
| target | **20 / 40 DN** | dotted, faint | *aim* — inside this the fill is right |

**Why not defer the target pair** (the earlier draft's position): the question an operator actually has at the
bench is *"am I in the window?"*, not *"have I cleared the rejection edge?"* — §16.23.8's whole point is that a
fill sitting at 17 DN is legal and bad. Two faint lines answer the real question and cost nothing: same
primitive, four `addLevel` calls, no renderer branch.

⚠ The coupling worry that motivated deferring — *the plot and the warning must quote the same numbers* — is
**dissolved by doing it generically**: all four values become plugin constants (`DN_GUARD_LOW/HIGH`,
`DN_TARGET_LOW/HIGH`), and step 3b's warning reads the same four. Deferring would have been the way to *create*
a second source of truth, not to avoid one.

⚠ **Back-compat:** removing the automatic 16 DN line changes every existing `axis="dn"` plot that does not
declare levels. Only `DevSpectralPlugin`'s Spectra step uses `axis="dn"` today, so the blast radius is one
call site — but the renderer should keep the auto-line **only if no levels are declared**, so a saved run from
before this change still shows its guard.

⭐ Note the DN levels are read in the **displayed** DN space (`axis="dn"` inverse-decodes the curve for
drawing); a declared level on such a plot is therefore already in DN and must **not** be decoded again.

## 14 · The confirmed band set for `Absorption (bands)` — ⭐ common understanding

**Yes — understood, and it is what §8 asked for.** The grey regions on the EVALUATION step
`Absorption (bands)` become exactly these four:

| band | window | role |
|---|---|---|
| **S** | **448–460** | metric numerator *(the trim, §2)* |
| **near anchor** | **520–540** | baseline fit input |
| **Q** | **560–580** | metric denominator |
| **far anchor** | **620–630** | baseline fit input |

⭐ **Consequence, stated explicitly because it is a deliberate loss:** the **clarity 510–540 shading is
dropped.** That is the right call — it is what dissolves **defect B2** (today's single grey block at 510–540
is read as the 520–540 anchor and is wrong by 10 nm on the left edge). Two overlapping near-identical spans
would have been the worst of both.

⚠ **The `Clarity · 510–540 nm` metric row and `Pigment ratio · clarity` stay.** They are the stable-denominator
safety net and nothing about them changes — only their window is no longer shaded on this plot. If that ever
feels wrong, the honest fix is a fifth band in a *different* colour (D-bandstyle(a) makes it one line), not a
return to one grey block meaning two things.

⇒ **The four bands, four mean-bars, one dashed baseline, one Q marker.** That is the whole plot.

## 15 · Files touched — delta from §9

| file | additional change |
|---|---|
| `spectracsPy-model/…/view/SpectrumPlotView.py` | `addLevel(...)`, `addTrace(..., style=)`, `levels`/`style` in `toJson`/`fromJson` |
| `spectracsPy/…/render/QtWorkflowRenderer.py` | levels (ranged + unranged), trace style, retire the hard-coded `__LOW_DN_GUARD` behind the no-levels fallback |
| `spectracsPy-core/…/report/MatplotlibWorkflowRenderer.py` | the same three, symmetrically |
| `spectracsPy-core/…/plugin_sdk/util/SpectrumFeatureUtil.py` | ⭐ **expose the fitted baseline** (`fittedBaseline(spectrum, windows)`); `linearBaselineCorrected` computes it today and discards it |
| `spectracs-plugins/…/dev/DevSpectralPlugin.py` | `FRAMES = 60`; the §12.4 declaration; the two DN guard levels on the Spectra step |
| `tests/` | a view-model round-trip test for `levels`/`style`; a renderer smoke test that both draw them; ⭐ **an identity test** — `mean(despiked over band) − mean(fit over band) == B_Soret` (§12.3), which is the one assertion that keeps the picture honest |

---

## 16 · Impl rubber-duck — what would bite while coding

*(Verified against the code 2026-08-10, not reasoned from the spec. ⚠ = act on it, ✔ = checked, no action.)*

1. ⭐⭐ **"The anchor bar lands exactly ON the line" is NOT exact — soften §12.3a.**
   `SpectrumFeatureLogicModule.linearBaselineCorrected` does **not** draw a chord through the two window
   means. It runs a **weighted least-squares fit through every point in both windows**, with equal *total*
   weight per window (`w = 1/len(window)`, passed as `sqrt(w)` because polyfit weights the residual).
   The normal equations force `r̄₁ + r̄₂ = 0` and, once the within-window λ–residual covariance is factored
   out, `r̄₁ = r̄₂ = 0` — so each anchor bar sits on the line **only up to that covariance term**. On the far
   anchor, which rides the Qy flank, that term is not obviously negligible.
   ⇒ **Say "sits on the line to within a small residual", not "exactly".** And the check in §12.3 becomes a
   **tolerance assertion**, never an equality.
   ✔ **The identity itself survives intact and IS exact**: `corrected = value − (slope·nm + intercept)`
   pointwise on the same keys, and `bandMean` is a plain mean over those keys — so
   `mean(despiked) − mean(fit) = B_band` holds for **any** band, to floating-point. The identity test is safe;
   the "on the line" claim is the one that needs the tolerance.

2. ⭐ **`fittedBaseline` needs no new maths — it is a subtraction.** `linearBaselineCorrected` returns a
   Spectrum on **the same nm keys** with exactly `value − line(nm)`. So `fit = despiked − corrected`,
   pointwise and exactly. ⇒ Implement the new accessor as that subtraction (keeps the ops boundary: the
   plugin must not hand-roll spectral arithmetic), **not** as a second polyfit — a second fit would be a
   second source of truth for the same line. ⚠

3. ⚠⚠ **There is a THIRD hard-coded DN guard, and §13 does not reach it.**
   `CapturePanel.__LOW_DN_WARN = 16.0` draws a guard on the **live capture preview** — the plot the operator
   actually watches while dosing — besides `QtWorkflowRenderer.__LOW_DN_GUARD` and matplotlib's
   `axhline(16.0)`. The live preview is host chrome fed by `CaptureView`, not by `SpectrumPlotView`, so
   declaring levels on the *plot* view-model leaves it untouched.
   ⇒ **Decision D-captureguard. ⭐ My lean: THREAD IT — do the live preview too.** Three reasons, in order of
   weight: (1) the dosing decision is made **there**, not in the report — a guard on the two plots you read
   *afterwards* protects nothing at the moment it matters; (2) the whole feature is "one source of truth",
   and stopping at two of three copies leaves the *most-read* plot as the stale one; (3) it is cheap —
   `CaptureView` gains four optional fields and `CapturePanel` reads them instead of its private constant,
   with no new drawing code. ⚠ Cost, stated: `CaptureView` starts carrying display constants, which is a
   slight widening of its remit (it is otherwise a capture *shell*). Acceptable — they are measurement
   constants the plugin already owns, not styling. ⛔ The one outcome to avoid is silently fixing two of
   three.

4. ⚠ **`SpectrumPlotWidget` has no linestyle either — the count is four files, not three.**
   `plotSpectrum(spectrum, title=None, color="y", clear=True, width=2)` and `addTrace(spectrum, color, width)`
   both bottom out in `pg.mkPen(color, width=width)`. The dashed baseline needs `style=` threaded through the
   **widget** as well as the model + renderer.

5. ⚠ **Levels on an `axis="dn"` plot must NOT be gamma-encoded.** The renderer maps the *curve* through
   `SpectralColorUtil.toDisplayDnSpectrum`; a declared `16` is **already** display DN. Encoding it would put
   the guard at 0.58 — which is precisely the bug the DN axis exists to prevent.
   ⭐ Corroboration for D-dnguard from that util's own docstring: *"the whole usable-but-dim range **16..60
   DN** occupies the bottom 4 %"* — 16/60 is the pair the codebase already thinks in.

6. ✔ **`FRAMES = 60` needs no combo change.** `CapturePanel` builds
   `choices = sorted(set(__FRAME_CHOICES + [default]), key=int)` — the plugin-declared value is injected even
   when it is not one of the stock choices. Checked; nothing else to touch.

7. ⚠ **The bars must be fed the mean of the PLOTTED curve, not the baselined mean.** Passing `far620Soret`
   (0.87) where `bandMean(despiked, …)` (0.95) belongs puts the S bar below where the curve actually is —
   **and nothing errors**. The picture would silently stop being true. The identity test in §15 is what
   catches this; write it first.

8. ⚠ **`bandMean` is inclusive on both edges** (`lo <= nm <= hi`), so the trim drops bins strictly below 448
   and keeps one landing exactly on 448.0. Harmless — but the threshold-derivation diagnostic must call the
   **same util**, not a hand-rolled numpy mask. `soret_448_since_0729.metrics()` uses its own
   `(lam >= lo) & (lam <= hi)` mask, which is why its numbers can differ from the app's in the last digit.

9. ⚠ **Saved runs must still load.** `SpectrumPlotView.fromJson` must default `levels=[]` and `style=None`;
   every `DbMeasurement` blob written before this change has neither key. Same back-compat rule the existing
   `bands`/`markers` lists follow. The PDF's embedded `workflow.json` grows by ~10 numbers — negligible.

10. ⚠ **Label collision on paper.** The report axes is ~3.4 in tall and spans 196 nm; four band labels plus a
    trace legend plus the title will fight for the top strip, and 520–540 / 560–580 are close together.
    Mitigate at implementation with the real figure (label inside the span, or only above a minimum span
    width). ⛔ Do not solve it by labelling on screen and not on paper — that is exactly the M2 drift.

11. ⚠ **`RoastGaugeView` is instantiated by a live test.** `test_director_cut_enablers.py` builds one to assert
    the verdict objectName. ⇒ D-deadgauges means **drop the two imports from the plugin**; do **not** delete
    the classes.

12. ✔ **The clamp assertion still passes.** `__assertWindowCoversBands` compares against
    `WAVELENGTH_MIN_NM = 440`; 448 > 440, so the trim cannot starve it. No change needed.

13. ⚠ **`PB_R_Q` exists twice** — the plugin's, and `settling_sweep.R_Q_620`. Whatever D-rq decides, **both
    move together** or the diagnostics silently stop describing the app.

14. ⚠ **Ordering hazard in the threshold run.** The derivation diagnostic imports `plugin.PB_SORET_BAND`. If
    it runs *after* C1 lands it reads 448 (good); if it runs *before*, it reads 440 and quietly derives the
    wrong scale. ⇒ Either run it after C1, or have it take the window as an explicit argument. ⭐ Prefer the
    explicit argument — a derivation script that silently follows a moving constant is how a threshold gets
    mis-attributed.

---

## 17 · Implementation phases

```
 ┌──────┬────────────────────────────────────────────────┬──────────┬─────────┬──────────────────────────────┐
 │ ph.  │ what                                           │ tier     │ needs   │ gate / done when             │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ A1   │ FRAMES = 150 -> 60                             │ plugin   │   —     │ a bench capture still reads  │
 │      │ (§11; one line, independent of everything)     │          │         │ sane; ~2 s burst             │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ A0   │ no-op version bump -> sign -> publish ->       │ desk +   │   —     │ ⭐ the M3 publish path is     │
 │      │ assign -> load  (the F16 rehearsal)            │ server   │         │ proven BEFORE it carries a   │
 │      │                                                │          │         │ real change                  │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ B1   │ view-model: addLevel(), addTrace(style=),      │ -model   │   —     │ round-trip test green;       │
 │      │ levels/style in toJson+fromJson (defaults!)    │          │         │ old blobs still load         │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B2   │ renderers: levels (ranged+unranged), trace     │ view +   │ B1      │ Qt and matplotlib draw the   │
 │      │ style, band label+colour, marker label (B6);   │ -core +  │         │ SAME thing; smoke test on    │
 │      │ ⚠ 4 files — widget too (duck #4)               │ widget   │         │ both                         │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B3   │ plugin declares the picture: 4 bands, 4 bars,  │ plugin   │ B2      │ ⭐ IDENTITY TEST first        │
 │      │ dashed fitted baseline, labels (§12.4, §14)    │ + -core  │         │ (duck #7); then the plot     │
 │      │ + fittedBaseline() accessor (duck #2)          │          │         │ reads as §12.3a              │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B4   │ DN guards declared: 16/60 + 20/40 faint;       │ plugin   │ B2      │ guard lines identical on     │
 │      │ retire the auto-16 behind a no-levels fallback │ + view   │         │ screen, on paper — and       │
 │      │ ⚠ D-captureguard: CaptureView too? (duck #3)   │          │         │ (if adopted) in the live     │
 │      │                                                │          │         │ preview                      │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ C1   │ PB_SORET_BAND = 448-460 + LEGACY_440 alias;    │ plugin   │   —     │ the four archive-reproducing │
 │      │ D-diag pins in the diagnostics (§3)            │ + diag   │         │ scripts print their OLD      │
 │      │                                                │          │         │ published numbers unchanged  │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ C2   │ threshold derivation run over the post-rebuild │ desk     │ C1      │ ⭐ per-class corridor + d      │
 │      │ archive; window passed EXPLICITLY (duck #14)   │ (data)   │ (or arg)│ printed; NO archived run     │
 │      │                                                │          │         │ changes class                │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ C3   │ both gauges: T + anchors + docstring rewrite;  │ plugin   │ C2      │ test_three_verdicts green;   │
 │      │ labels/tooltips 440->448; Director slug;       │ + auto   │         │ the Director scenario still  │
 │      │ drop the 2 dead imports (duck #11)             │ + tests  │         │ finds every field            │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ C4   │ publish + assign + RIG CLICK-THROUGH:          │ rig      │ A0, B3, │ ⭐ one real measurement: both │
 │      │ both plots, both gauges, the PDF, the badge    │          │ B4, C3  │ verdicts sane, PDF == screen │
 └──────┴────────────────────────────────────────────────┴──────────┴─────────┴──────────────────────────────┘

   A1 ──────────────────────────────────────────────────────────────┐
   A0 ──────────────────────────────────────────────────────────┐   │
   B1 ──> B2 ──┬──> B3 ────────────────────────────────────┐    │   │
               └──> B4 ───────────────────────────────────┐│    │   │
   C1 ──> C2 ──────> C3 ─────────────────────────────────┐││    │   ▼
                                                         ▼▼▼▼▼▼▼▼▼▼▼
                                                              C4  (rig)
```

⭐ **Ship B before C.** The picture (B1–B4) is pure gain, independent of the metric change, and it is the
thing that makes C reviewable — with the bands drawn and the baseline visible you can *see* the window move
from 440 to 448 and *see* what it does to the gap. Doing C first means changing a number you cannot look at.

⚠ **A0 is not optional and not busywork.** `SPEC_first_presentable_state.md` step 1 puts the no-op bump first
on purpose: it is the only rehearsal the first-real-publish runbook (F16) gets, and it is far cheaper to
debug the publish path when nothing else changed.

⚠ **C2 is the only phase that needs data rather than code** — it is desk work over the existing archive, so
it does not wait on the rig. C4 does.

⛔ **§17 is SUPERSEDED by §19.** The second rubber-duck pass (§18) found that this plugin cannot be published
at all, which removes work from A0 and C4. Read §19.

---

## 18 · Second rubber-duck pass — the publish path, the SDK surface, and what a threshold does to saved runs

*(2026-08-10. The first pass looked at the drawing; this one at the tiers around it.)*

### ⛔⛔ S1 — THE DEV PLUGIN CANNOT BE PUBLISHED. §7's "re-sign" is wrong for it.

`PluginPublishUtil.lintSelfContained` refuses any `sciens.*` import that is not the SDK:

```python
_PLUGIN_SDK_ROOT = "sciens.spectracs.plugin_sdk"
#   allowed:  from sciens.spectracs.plugin_sdk import ...
#   refused:  anything else under sciens.*      -> PluginSourceError, BEFORE signing
```

**`DevSpectralPlugin` opens with four refused imports** — `RoastGaugeView`, `RoastBaselineGaugeView`,
`RoastPedestalGaugeView`, `RoastFar620GaugeView`, all under `sciens.spectracs.plugins.dev.*`. ⇒ Publishing it
raises today, and has never worked.

**Three consequences, and they all simplify the plan:**

1. ⭐ **The trim ships by editing the repo. No signing, no version bump, no assignment.** The bench loads the
   **built-in** (M3 dispatch: `version=None` → built-in; a bare/unsealed row → built-in). §7's paragraph on
   the signed artifact is **retracted for this plugin**.
2. **A0's rehearsal must use `PumpkinOilPlugin`** — verified: it imports `colorsys` and `plugin_sdk`, nothing
   else, so it passes the lint. A0 therefore belongs to `SPEC_first_presentable_state.md` step 1, **not to
   this spec**. Keeping it here would have coupled the trim to an unrelated milestone.
3. **New decision D-devpublish** — *should* the DEV plugin be distributable? If yes, the fix is mechanical:
   the four gauge classes import **only** the SDK (`VerdictGaugeView, GaugeRender, GaugeColorUtil`), so
   inlining them into `DevSpectralPlugin.py` makes it lint-clean. ⚠ It also makes the module ~1000 lines and
   couples four presets to one file. ⭐ **My lean: not now.** It is the bench's own instrument; distribution
   buys nothing until an end-user plugin needs these gauges, and the trim must not wait on a refactor.

### ⚠ S2 — a threshold change silently mixes scales in the saved-runs table

`VerdictGaugeView` **caches** `verdictLabel` and `swatchColor` at construction, `toJson`/`fromJson` round-trip
them, and `GaugeWidget` renders `view.verdictLabel` **directly** — no recomputation. That is deliberate (*"a
saved-runs table reads them without maths or a re-run"*).

⇒ After C3, a saved run from before it keeps the verdict computed under **T = 10.6 on the 440 scale**, shown
beside new runs under the new T. **Each was correct when written; the column is not comparable.** Nothing
warns, and the number that would explain it is not stored.

⭐ **This is precisely what M3's deferred A3 provenance stamp (`SpectralWorkflow.pluginVersion`) exists for.**
⇒ C3 is the moment it stops being optional — either land A3, or (minimum) put the cut-over date in the
release note and in both gauge docstrings. ⚠ Same family as §6's "saved runs keep the old label": the label
mismatch is *visible*, this one is not.

### ⚠ S3 — the SDK gate is exact equality, so a bump is not free

`SDK_VERSION = 1`; `checkSdkCompatibleVersion(row["targetSdkVersion"], …)` runs for DB rows and
`checkSdkCompatible(plugin)` for built-ins, and **both directions raise**. Adding `addLevel` / `style` grows
the SDK surface, which invites a bump to 2 — but that would **invalidate every sealed row until re-signed**.

⇒ **D-sdkbump: do not bump.** Built-ins default `targetSdkVersion` to the live `SDK_VERSION`, so they are
unaffected either way, and **no distributed plugin calls the new methods** (S1: the only plugin that would is
unpublishable). ⚠ The accepted residual risk: an *old* app loading a *new* sealed plugin that calls
`addLevel` gets an `AttributeError` instead of the friendly version error. Bump once, in one go, if
D-devpublish is ever taken.

### ✔ S4 — Android needs no mirroring

`android/spike/app_src` is a **gitignored build artifact**: `stage_app_src.sh` does `rm -rf app_src/sciens`
then rsyncs `sciens/` from all six sibling repos. The duplicate `SpectrumPlotView.py` there is staged, not
maintained. ⇒ Nothing to do but re-stage before an APK build.

### ✔ S5 — the burst headroom already scales with the frame count

`__runBurst`: `maxFrames = target + max(5, target // 5)` (+20 %), `maxAttempts = maxFrames + target`. At 60
that is +12 replacement frames and a 132-attempt cap — the same *proportions* as at 150. A1 touches nothing
here. *(The first pass checked the combo seeding; this checks the top-up loop.)*

### ⚠ S6 — A1 does not invalidate C2, and the reason must be written down

C2 derives thresholds from **150-frame archive runs**; the app will then capture **60-frame** ones. Frame
averaging changes **variance, not expectation** — so there is no bias and the corridor stays valid. ⚠ But the
margins are quoted in σ, and the class spreads widen slightly (§11's ≤0.24 pp), so the σ-margins shrink a
little. ⇒ State it in the gauge docstrings; do **not** re-derive.

### ⚠ S7 — the archive becomes frame-count-mixed, and nothing records it

Once A1 lands, later runs are 60-frame while the archive is 150-frame, and **no diagnostic table has a
frame-count column**. Cheap fix: add the frame count to the `CAPTURE-SETTINGS` stdout line that already logs
exposure / WB / gain. ⛔ Not doing it repeats §16.27's exposure reconstruction, where the setting had to be
recovered from the reference level because it was never persisted.

### ⚠ S8 — band and level colours must go through the report renderer's colour map

`MatplotlibWorkflowRenderer` maps trace colours via `self.__COLORS.get(color, color)` — that map exists
because pyqtgraph short names (`'c'`, `'y'`, `'g'`) are not all matplotlib colours. Band/level colours must
use the **same** map or paper and screen diverge on exactly the axis M2 forbids. *(Hex is safe both ways.)*

### ⚠ S9 — the legend will land on the Q bar

Labelling the baseline trace makes `ax.legend(fontsize=7, loc="best")` appear on the EVALUATION plot, and
"best" favours the empty lower-right — which is where the Q band sits. ⇒ Either pass an explicit `loc`, or
leave the baseline trace unlabelled and let the dash + the band labels carry it. ⭐ Prefer the latter: one
dashed line among solid ones needs no legend.

### ⚠ S10 — the two tabs will disagree about the clarity band, on purpose

§14 drops the 510–540 shading from `Absorption (bands)`, but the **legacy** tab keeps it (there it is a real
metric window). A reviewer flipping between tabs sees the band on one and not the other. Intended — say so in
the release note, or it reads as a rendering bug.

### ✔ S11 — no SDK export change

`SpectrumPlotView` is already exported from `plugin_sdk/__init__.py`; new **methods** ride along with the
class. Nothing to add to `__all__`.

---

## 19 · Implementation phases (v2 — after the second pass)

```
 ┌──────┬────────────────────────────────────────────────┬──────────┬─────────┬──────────────────────────────┐
 │ ph.  │ what                                           │ tier     │ needs   │ gate / done when             │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ A1   │ FRAMES = 150 -> 60                             │ plugin   │   —     │ a bench capture reads sane;  │
 │      │ + log the frame count in CAPTURE-SETTINGS (S7) │          │         │ ~2 s burst; count in the log │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ B1   │ view-model: addLevel(), addTrace(style=),      │ -model   │   —     │ round-trip test green;       │
 │      │ levels/style in toJson+fromJson (DEFAULTS)     │          │         │ pre-change blobs still load  │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B2   │ renderers: levels (ranged+unranged), trace     │ view +   │ B1      │ Qt == matplotlib on one      │
 │      │ style, band label+colour, marker label;        │ -core +  │         │ fixture; colours through the │
 │      │ ⚠ 4 files: model, widget, Qt, matplotlib       │ widget   │         │ __COLORS map (S8)            │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B3   │ IDENTITY TEST first, then the plugin declares  │ plugin   │ B2      │ ⭐ the plot reads as §12.3a;  │
 │      │ 4 bands + 4 bars + dashed baseline;            │ + -core  │         │ anchor bars on the line      │
 │      │ fittedBaseline() = despiked - corrected        │          │         │ within tolerance (duck #1)   │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ B4   │ DN guards declared 16/60 + 20/40 faint;        │ plugin   │ B2      │ the SAME four values on the  │
 │      │ retire the auto-16 behind a no-levels          │ + view   │         │ eval plot, the PDF and the   │
 │      │ fallback; ⭐ D-captureguard: CaptureView too    │          │         │ LIVE preview — one source    │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ C1   │ PB_SORET_BAND = 448-460 + LEGACY_440 alias;    │ plugin   │   —     │ the 4 archive-reproducing    │
 │      │ D-diag pins (incl. settling_sweep.R_Q_620)     │ + diag   │         │ scripts print OLD numbers    │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ C2   │ threshold derivation over the post-rebuild     │ desk     │ C1 or   │ ⭐ corridor + d printed; NO   │
 │      │ archive; window + r_Q passed EXPLICITLY        │ (data)   │ explicit│ archived run changes class   │
 ├──────┼────────────────────────────────────────────────┼──────────┼─────────┼──────────────────────────────┤
 │ C3   │ gauges: T + anchors + docstrings (incl. the    │ plugin   │ C2      │ test_three_verdicts green;   │
 │      │ S6 note); labels 440->448; Director slug;      │ + auto   │         │ the Director finds every     │
 │      │ drop 2 dead imports; ⚠ S2 provenance/release   │ + tests  │         │ field; cut-over date written │
 ├══════┼════════════════════════════════════════════════┼══════════┼═════════┼══════════════════════════════┤
 │ C4   │ RIG CLICK-THROUGH — one real measurement:      │ rig      │ A1, B3, │ ⭐ both verdicts sane;        │
 │      │ both plots, both gauges, the PDF, the badge    │          │ B4, C3  │ PDF == screen                │
 └──────┴────────────────────────────────────────────────┴──────────┴─────────┴──────────────────────────────┘

   ┌─ DROPPED from v1 by the second pass ─────────────────────────────────────────────────────────────┐
   │ A0  no-op version bump + sign + publish + assign   -> S1: this plugin CANNOT pass the publish     │
   │                                                       lint. The rehearsal belongs to             │
   │                                                       first_presentable_state step 1, with the   │
   │                                                       PUMPKIN plugin. Not this spec's work.      │
   │ C4  "publish + assign + click-through"             -> shrinks to CLICK-THROUGH. The bench loads   │
   │                                                       the built-in; the trim ships as a commit.  │
   └──────────────────────────────────────────────────────────────────────────────────────────────────┘

   A1 ────────────────────────────────────────────────────────────┐
   B1 ──> B2 ──┬──> B3 ──────────────────────────────────────┐    │
               └──> B4 ─────────────────────────────────────┐│    │
   C1 ──> C2 ──────> C3 ───────────────────────────────────┐││    ▼
                                                           ▼▼▼▼▼▼▼▼
                                                              C4  (rig)

   optional, decoupled:  D-devpublish  (inline the 4 gauge classes -> the plugin becomes publishable)
                         D-sdkbump     (only together with D-devpublish)
                         A3 stamp      (SpectralWorkflow.pluginVersion — the honest fix for S2)
```

⭐ **What the second pass bought:** one phase deleted, one phase shrunk, and the discovery that **the trim is
a plain commit** — no signing ceremony, no re-assignment, no version thread. The only ceremony left is the
rig click-through, which was always the real gate.

---

# 20 · BUILD REPORT — 2026-08-10

**Shipped:** A1 (frames), B1–B4 (the picture + the DN guards), C1 (the trim), C2 (the derivation),
C3 (gauges, labels, slug). **344 tests green** — 318 app, 26 plugins. **C4 stays with Edwin: the rig.**

## 20.1 ⭐ The thresholds, DERIVED — and the gate as written was the wrong gate

`diagnostics/soret_448_thresholds.py`, on §16.20.4's own corpus (Steirerkraft B+C vs S-Budget D, 18 runs) so
that the **window is the only thing that changed**:

| gauge | green (n=12) | brown (n=6) | *d* | corridor | ⭐ **T** | margins |
|---|---|---|---|---|---|---|
| `RoastPedestalGaugeView` *(primary)* | 8.369 ± 0.352 | 5.593 ± 0.129 | 9.24 | 5.748 – 7.831 | **6.8** | green +4.46 σ · brown +9.37 σ |
| `RoastFar620GaugeView` | 10.560 ± 0.453 | 6.615 ± 0.151 | 10.25 | 6.796 – 9.895 | **8.3** | green +4.99 σ · brown +11.16 σ |

⭐ **The 440-scale column reproduced §16.20.4 and both gauge docstrings to the digit** (Steirerkraft B+C span
11.610 – 13.337 on `M+ped`, 14.671 – 18.356 on `M`), so the pipeline is verified against published numbers
before it derives anything new.

⭐ **The pedestal gauge's line is now DERIVED for the first time** — 10.6 was inherited from the 600–630 scale
and never re-fitted. The new line is *better balanced*: green +3.72 σ → **+4.46 σ** while brown still clears by
9 σ. §16.10.17d's policy (a false GREEN is the costlier error) survives without a hand nudge.

### ⚠ The gate "no archived run may change class" FAILED, and it deserved to

**Because the old pedestal threshold did not agree with its own corridor.** An inherited line must disagree
with a correctly derived one somewhere — so the gate as written could only ever be met by *inheriting again*.
Restated to what it should have been: **no run of the DERIVATION CORPUS may move** — and none does (0/18).
Outside it, **3 of 31 move**, each enumerated rather than absorbed:

| run | change | reading |
|---|---|---|
| `Steirerkraft A aged 24 h` #1 | far620 green → **brown** | ⭐ a **correction**: §16.11.16 established that fill as a genuinely browner oil whose 3 runs the old scale misclassified. The trim catches one of the three |
| `Spar ggA` #1 and #3 | pedestal brown → **green** (#2 stays brown) | the fill now **straddles** the line — §16.27.6's "the metric produces a graded scale where T assumes a binary one", restated. T = 10.6 rejected both ggA oils outright; this line splits one |

⚠ `Steirerkraft half-strength` #6 reads brown on **both** scales (10.385 vs T 10.6; 6.613 vs T 6.8) — the
deliberate half-dilution fill, failing identically before and after. Not a regression.

⛔ **Neither move is a licence to retune.** §16.27.6 still owns the ggA question and it belongs to the
validation study (ROADMAP PRIO 3).

## 20.2 What the build changed about the design

1. ⚠ **The class-change gate was restated** (§20.1). Recorded because the *original* wording is the kind that
   gets met by doing the wrong thing.
2. ⚠ **Bar colour is a two-ground problem.** The first cut used `#e8e8e8` for the mean bars — invisible on
   white paper. Every colour a plugin declares is drawn on a **dark plot AND a white page**, so the palette is
   mid-tones only (`__BAND_BAR` teal `#2a9d8f`, `__ANCHOR_BAR` slate `#7a8ea0`). ⭐ A rule for future plugin
   colours, not a one-off fix. *(Pre-existing and untouched: the primary trace has no declared colour, so the
   screen draws it yellow and the report blue.)*
3. ⚠ **`LinearRegionItem` draws its drag handles as bright vertical lines** — on a non-movable annotation those
   read as data. Pens set to `None`; the fill *is* the band.
4. ⚠ **Band labels moved INSIDE the axes on paper** (`va="top"` at 0.985) — the strip above the axes belongs to
   the marker labels, and with four bands plus the Q marker the two rows collided, exactly as §18 S9 predicted.
5. ✔ **The identity holds on real data**, verified on two archive runs before any rig time:
   `20270729B/001` (green) S bar 0.8061 − line 0.0407 = **gap 0.7654 == B_Soret 0.7654**;
   `20260731A/001` (brown) 0.7584 − 0.0609 = **0.6976 == 0.6976**. The anchor bars land on the line, and the
   fitted baseline **rises to the red** (0.041 → 0.20) — §16.12.12's "the far anchor measures", now visible.

## 20.3 Deviations from §19 worth knowing

* **`Q_BASELINE` (555–600) is now marked on the legacy plot** (defect B4) — it was listed under F1 and is easy
  to lose; it shipped.
* **`test_three_verdicts` no longer repeats the thresholds.** It reads `_THRESHOLDS[0]` and pins the derived
  values in one dedicated test with the corpus written next to them. A copy of a threshold in a test fails for
  the wrong reason at every re-derivation.
* **`metric_algebra_plots.py` derives its Soret caption from the constant** instead of the typed "440–460".
  ⚠ The **committed figures and the published `Spectracs_MetricAlgebra.pdf` were made on 440–460**; regenerating
  redraws that band. Deliberate regeneration only.
* **`soret_448_since_0729.py` inverted**: its `SHIPPED` is now the frozen legacy window and `TRIMMED` is what
  the app computes. The comparison it exists for still reads the same way round.

## 20.4 ⛔ Still open — for Edwin

| | |
|---|---|
| **C4 — the rig click-through** | one real measurement: both plots, both gauges, the PDF, the LIMS badge. Nothing here has met a camera |
| **D-rq** | `PB_R_Q` stays −0.0184 (the 440-fitted value). The window-consistent refit is −0.0133 and is owed at the threshold freeze |
| **S2 — the saved-runs scale mix** | verdicts are cached into the saved run, so pre-2026-08-10 rows carry the old scale with nothing recording it. The honest fix is M3's A3 stamp (`SpectralWorkflow.pluginVersion`) |
| **The 60-frame corpus** | thresholds are derived on 150-frame runs; averaging changes variance not expectation, so they stand — but the first 60-frame fills are worth checking against the corridor |

---

# 21 · CHANGE REQUEST — DN limits move to SAMPLE, and white band captions  *(Edwin 2026-08-10, after the first working click-through)*

> **DESIGN ONLY.** Two changes on top of §20's build.

## 21.1 The DN limits belong to the SAMPLE step, not the Reference one

**Ask:** *"render the DN limits not in the REFERENCE phase, but in the SAMPLE pseudo-phase, and render it there
the same way as in the PROCESSING phase (also with the labels)."*

⭐ **This is right on the physics, not just on the layout.** §16.23.8 states the guard on **`min(S)` over the
analysis range, after the SAMPLE capture**. The reference is the solvent blank: its level is set by
auto-exposure and judged against R ≈ 88, never against 16/60 DN. Drawing those two edges on the reference
preview asserted a rule that does not apply there — and worse, invited the operator to "fix" a reference that
was never wrong.

**Two code facts this lands on:**

1. ⛔ **`CapturePanel.__drawLowDnGuard` reads the WRONG step today.** It takes `self.__steps[0].getView()` —
   which is always the *Reference* step — and draws that declaration on whichever role is on screen. So the
   guards are currently reference-declared and shown everywhere. The panel already maintains `__activeStep`
   and four other methods already read it; this one must too. ⇒ the fix and the ask are the same edit.
2. **Captions need the renderer's draw path.** `__drawLowDnGuard` draws bare `InfiniteLine`s; the PROCESSING
   plot draws labelled ones through `QtWorkflowRenderer.__drawLevel`.

**⭐ The generic shape (Edwin's standing rule — the view-model owns it, in one place):**

| | today | proposed |
|---|---|---|
| `CaptureView` | `dnGuards=(16,60)`, `dnTarget=(20,40)` — bare numbers, captions nowhere | **`levels=[...]`**, the SAME 6-tuple shape as `SpectrumPlotView.addLevel` |
| the four values | declared twice (Spectra plot + CaptureView) | built **once** in the plugin, handed to both |
| the drawing | `QtWorkflowRenderer.__drawLevel` *and* a private copy in `CapturePanel` | ⭐ **`SpectrumPlotWidget.addLevel(...)`** — the widget is the common ground of both callers |

⇒ value, caption, colour and style live once; the live preview and the PROCESSING plot cannot drift; and the
`ignoreBounds` rule (§20.2 / the runaway) is enforced in a single method instead of two.

⚠ **Consequences to accept knowingly:**
* the **Reference preview loses its guard line entirely**. Its `__logLowDnGuard` stdout line is untouched and
  still reports both roles, so nothing stops being *measured* — only the drawn rule moves.
* a plugin that declares no levels still gets the legacy single 16 DN line (unchanged fallback).
* `test_dev_plugin_improved_colour` asserts the guards on `steps[0]`; it becomes per role — **Reference: none,
  Sample: four**. That assertion is the regression test for fact 1 above.

## 21.2 White band captions — but only on screen

**Ask:** *"in the 'Absorption(bands)' step use white as the labels color."*

⛔ **The cause is a bug, not a taste question.** The Qt renderer currently draws a band caption in the band's
own **shading** colour: `pg.TextItem(..., color=color or self.__LEVEL_COLOR)`. For the two anchors that colour
is `#5a6a7a55` — *semi-transparent slate*, chosen to make the SHADING recede. So the captions "near anchor"
and "far anchor" render deliberately faint, which is exactly what Edwin is looking at.

⇒ **A caption never inherits the shading colour.** Band and marker captions take the renderer's own
`__LEVEL_COLOR`, set to **white**.

⛔ **The plugin must NOT declare the caption colour**, tempting as it looks: the same view-model is drawn on a
dark screen *and* on white paper, and white is invisible in the PDF. This is §20.2's two-ground rule again —
so the caption colour stays a **renderer** decision: Qt white, matplotlib keeps its paper-legible `0.45` grey.

**Scope:** every Qt band caption (both band plots) and the marker caption. The Q marker line is already white,
so a white "Q" is consistent.

⚠ **One thing deliberately NOT made white — flag for Edwin:** the **DN guard captions** in the live preview and
on the Spectra plot are colour-coded by meaning (amber = reject edge, muted green = target window). Their
colour carries information, so the proposal keeps them as they are. Say the word if you want those white too.

---

# 22 · CHANGE REQUEST — numbered annotations + a positioned legend  *(Edwin's annotated screenshot, `ksnip_20260810-211901.png`)*

> **DESIGN ONLY.** Assessment first, then the shape.

## 22.1 What the screenshot shows

Edwin's mock, drawn over a REAL rig run, numbers the **lines** ① Soret band mean ② Q-band mean ③ red-anchor
mean ④ quiet-anchor mean ⑤ baseline correction, and puts a bordered, semitransparent legend in the top-right.
⭐ **Note what he numbered: the four mean BARS and the dashed BASELINE — the line-like things. The BANDS keep
their inline captions.** That distinction is the right one and the design keeps it.

**Two defects are visible in the same image, and they are the argument for the change:**

* ⛔ **Two "Q"s, 10 nm apart** — the Q *band* caption at 570 and the Q *marker* caption at 580. A reader cannot
  tell which is which, and there is no room to say more.
* ⛔ **"near anchor" / "far anchor" are barely legible** — they inherit the anchor's semi-transparent SHADING
  colour. That is §21.2's bug, independently confirmed. ⚠ It is **not** fixed by this change: even a perfect
  legend needs the band captions readable. §21.2 still stands on its own.

⚠ And the thing with no caption at all today is the **dashed baseline** — deliberately, because a matplotlib
legend would have landed on the Q band (§18 S9). A number + a positioned box is exactly the way out of that
trade-off.

## 22.2 ⭐ Assessment — yes, with one condition

**The plot now carries ten annotations** (4 bands, 4 bars, 1 baseline, 1 marker). Inline captions do not scale
to ten: they collide, they sit at the TOP of the plot while the thing they name is at mid-height, and they
have room for two words. A badge sits **on** the item, at its own y, and the legend has room for prose.

| | inline caption | numbered + legend |
|---|---|---|
| ≤ 3 annotations | ⭐ better — no lookup | worse — indirection for nothing |
| ≥ 4, or items at different heights | collides, points vaguely | ⭐ better |
| an item with no room for a caption (the baseline) | impossible without occlusion | ⭐ solved |
| screencast / paper narration ("look at 3") | no handle | ⭐ a stable handle |

⇒ **The condition: it is an OPTION, not a replacement.** Both mechanisms stay; a view that numbers nothing
renders exactly as today. The Q *band* keeps "Q" and the Q *bar* becomes ②, which also dissolves the
duplicate-caption defect.

## 22.3 The shape

**D-number — the number is DECLARED, never auto-assigned.** `addLevel(..., number=1)`, `addTrace(...,
number=5)`. ⛔ Auto-numbering by declaration order looks tempting and is a trap: insert one annotation and
every later number shifts, silently invalidating a saved PDF, a lab notebook entry and any Director narration
that says "marker 3". A declared number is a stable identifier.

**D-legendtext — the legend row IS the annotation's existing `label`.** No second text field. Rule:

| annotation has | drawn as |
|---|---|
| `label`, no `number` | inline caption, as today |
| `label` + `number` | a badge at the item **and** a legend row `(n) label` — no inline caption |
| `number`, no `label` | a badge, no legend row *(allowed, pointless — worth a warning)* |

**D-legendpos — position is plugin-declared, style is renderer-owned.** `SpectrumPlotView(...,
legendPosition="NORTH_EAST")`, with a `LegendPosition` enum in `plugin_sdk` (NORTH_EAST / NORTH_WEST /
SOUTH_EAST / SOUTH_WEST). ⛔ The **alpha, the border, the badge colour and the text colour are NOT
plugin-declared** — the same view-model is drawn on a dark screen and on white paper, and this is the third
time that rule has bitten (near-white bars §20.2, white captions §21.2). Renderer constants, one per ground.

**D-badgeanchor — where the badge sits.** A ranged level: centred on its band, offset above the bar. A trace:
at an optional `numberAt=<nm>` (default: the curve's leftmost point) — the baseline in Edwin's mock is
numbered at its far left, which is exactly the default.

**Mechanics — both renderers do this natively, no hand-rolled boxes:**

| | screen | paper |
|---|---|---|
| legend box | `pg.LegendItem(pen=…, brush=…, frame=True)` + `setParentItem(vb)` + `.anchor()` — corner-anchored, so it **cannot** move with the data | `ax.text(..., transform=ax.transAxes, bbox=dict(boxstyle="round", fc=(1,1,1,.75), ec="0.4"))` |
| badge | `pg.TextItem(fill=…, border=…)` | `ax.annotate(..., bbox=dict(boxstyle="circle"))` — a real circle |

⚠ **Both go in with `ignoreBounds=True`** (§20.2's runaway). The legend is parented to the **ViewBox**, not to
the data, so it cannot feed the auto-range at all — belt and braces.

## 22.4 Wording — two corrections to the mock

* **"(5) baseline correction" → "fitted baseline (subtracted)".** The dashed line *is* the fitted baseline; the
  correction is what subtracting it does. The distinction matters on this plot specifically, because §12.3's
  whole point is that the **gap** between a bar and this line is the corrected value.
* ⭐ **"red-anchor" is deliberately right, keep it.** ⛔ Never call 620–630 "quiet": §16.12.12 measured that it
  carries real pigment (green 0.0535 vs brown 0.0159, 5.1 σ) and sweeping it inward collapses *d* from 2.88 to
  0.94. "quiet-anchor" for 520–540 is fine.

## 22.5 ⭐ Worth adding while we are here

**Put the same number on the METRIC ROW.** `(1) Soret · 448–460 nm` in the Metrics tab, `(2) Q · 560–580 nm`,
and so on. The plot answers *where*, the table answers *how much*, and the number is the only thing that
currently ties them together — a reader looking at bar ① has to guess which row it feeds. Cheap: the label
already exists, and `MetricFieldView` needs no new field.

## 22.6 Open questions for Edwin

1. **Which items get numbers** — the mock numbers the 4 bars + the baseline and leaves the bands captioned.
   Confirm, or number the bands too (⇒ 9 badges, which I would advise against: the bands already read).
2. **The metric-row numbering of §22.5** — in or out?
3. **`AUTO` placement?** NORTH_EAST is empty on the absorbance curve but NOT on the DN plot (the reference
   climbs to the right). A later `AUTO` could pick the emptiest quadrant by sampling the drawn curves;
   for now a declared position per view is enough. Worth having on the roadmap or not?

---

# 23 · LEANS + IMPL RUBBER-DUCK — the numbered legend  *(Edwin 2026-08-10)*

> **DESIGN ONLY.** Scope settled by Edwin: ⭐ **legend and numbering go on the `Absorption (bands)` step and
> nowhere else.** Verified against a working probe (`pyqtgraph 0.14.0`), not reasoned from the docs.

## 23.1 The three leans

| # | question | ⭐ lean |
|---|---|---|
| 1 | which items get numbers | **the 4 mean bars + the baseline — exactly the mock.** The bands keep captions. Numbering all nine would trade a readable word ("S") for a lookup, and the bands are the one annotation whose position already *is* its meaning |
| 2 | metric-row numbering | ⛔ **OUT** — Edwin's scoping decides it, and it is the right call for a second reason: a `(1)` on a metric row is a promise that the number means the same thing in a table that is *also* rendered into the PDF and read without the plot beside it. Cross-referencing is a good idea that deserves its own decision, not a side effect |
| 3 | `AUTO` placement | **roadmap line, not now.** With the scope at one plot, a declared corner is enough. `AUTO` needs curve sampling per render and would have to agree between two renderers — real work for a plot whose empty corner is known |

## 23.2 Padding — the shape of the API

Edwin: *"NORTH_EAST and also a padding from the according edge should be supplied."*

```python
SpectrumPlotView(..., legendPosition=LegendPosition.NORTH_EAST, legendPadding=14)
```

⛔ **THE PADDING IS A MAGNITUDE; THE RENDERER OWNS THE SIGN.** This is the trap and the probe walked into it:
pyqtgraph anchors with `legend.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-14, 14))` — at NORTH_EAST the x
offset must be **negative** and y **positive**. A plugin that supplies a signed `(-14, 14)` and is then moved to
SOUTH_WEST puts its legend **off-screen**. ⇒ the plugin supplies a positive number (or `(x, y)` pair), the
renderer derives `(±x, ±y)` from the enum.

**Units: points.** pyqtgraph's offset is device pixels and matplotlib's annotate offset is points; at our
scales they agree closely enough that one declared number produces the same visual gap on screen and on paper.
⚠ Declaring it in *data* units would be wrong — the gap would change with every rescale.

## 23.3 Impl rubber-duck — what would bite

*(⚠ = act on it, ✔ = checked, ⭐ = a decision worth making deliberately.)*

1. ⭐⭐ **The legend rows must be DERIVED from the numbered annotations, never a second list.** `legendRows=[...]`
   beside `addLevel(number=…)` would drift the moment someone renumbers — a badge saying ③ over a legend row
   saying ③ *is the whole contract*. ⇒ the renderer walks bands/levels/traces, takes everything with a
   `number`, sorts ascending, and emits `(n) label`. One source of truth.
2. ⭐ **Declared numbers are NOT in wavelength order, and that is deliberate.** The mock reads 1 Soret (448),
   2 Q (570), 3 red anchor (625), **4 quiet anchor (530)**, 5 baseline — i.e. *the two metric bands, then the
   two anchors, then the construction*. An auto-numbering by λ would produce 1,4,2,3,5 and destroy the
   grouping. ⇒ third independent argument for D-number (declared, never derived).
3. ⚠ **Validate the numbers at build time.** Duplicates and gaps are programming errors that render as a
   *plausible* plot — two badges reading ③, or a legend row with no badge. `DevSpectralPlugin` already fails
   loud in `__assertWindowCoversBands`; the same treatment applies here.
4. ⚠ **`LegendItem.addItem(item, name)` needs an item, and it reserves a SAMPLE COLUMN.** The probe passed
   `pg.PlotDataItem(pen=None)` and the empty column is visible as a gap left of every row. Two ways out:
   a zero-width `ItemSample` subclass, or ⭐ **draw the badge itself as the sample** so a row reads `[③] red-anchor
   mean` — which also removes the `(3)` prefix from the text. The mock uses the prefix; the sample is nicer and
   costs the same. **Edwin's call.**
5. ⚠ **Badge SHAPE differs between renderers by default.** `pg.TextItem(fill=…)` fills a **rectangle**;
   matplotlib's `bbox=dict(boxstyle="circle")` gives a real **circle**. ⇒ pick one shape for both — lean:
   **rounded box** (`boxstyle="round"` on paper), because the circle needs a second item on screen
   (`ScatterPlotItem` under a `TextItem`) for no gain. ⛔ Do not ship rect-on-screen / circle-on-paper.
6. ⚠ **Badge position needs a rule, and "centre of the band" is not it.** In the probe ② landed on the Q bar
   right next to the dashed Q marker, and ④ sat on the curve. ⇒ **centre of the band, offset a few POINTS
   above the bar** — a device offset, so it does not drift when the range changes. For a trace, an optional
   `numberAt=<nm>` defaulting to the curve's left end (which is where the mock puts ⑤).
7. ⚠ **A numbered trace must NOT also enter matplotlib's own `ax.legend()`.** The report renderer legends any
   trace carrying a label; a numbered baseline would then appear **twice on paper** — once in our box, once in
   matplotlib's. ⇒ numbered annotations are excluded from the trace legend by construction.
8. ✔ **The legend cannot cause the §20.2 runaway.** It is `setParentItem(vb)`-ed, not added through
   `plot.addItem`, so it never enters `childrenBounds`. Probe: y-range `-0.072 .. 2.178`, unchanged over 8
   ticks. ⚠ The **badges** DO go through `addItem` and must keep `ignoreBounds=True`.
9. ⚠ **Style stays renderer-owned — for the third time.** Border, fill alpha, badge colour, text colour: the
   same view-model is drawn on a dark plot and on white paper. Only `legendPosition` and `legendPadding` are
   plugin-declared. (Near-white bars §20.2, faint captions §21.2, this.)
10. ⚠ **Serialization + back-compat.** `number` on band/level/trace tuples, `legendPosition`/`legendPadding`
    on the view; a pre-2026-08-10 blob has none of them → no legend, no badges, renders exactly as today.
    Same padding rule `fromJson` already applies to bands and levels.
11. ⚠ **Phone width.** The plugin also runs in the wizard at 412 dp. A five-row legend at 9 pt is a large
    fraction of that plot. Not a blocker (the bands plot is a bench view), but if it ever lands on a phone the
    legend needs a smaller type size or a collapse rule — worth knowing before it is discovered on a rig.
12. ⚠ **The legend occludes.** NORTH_EAST is empty *on this curve* — an absorbance that falls from the left.
    ⛔ It is NOT empty on the DN plot (the reference climbs to the right), which is exactly why the scope is
    one step. If the legend is ever reused elsewhere, the corner is a per-view decision, not a default.
13. ⚠ **`Absorption (bands, dev)` keeps inline captions.** With numbering scoped to one step, the two plots
    now annotate *differently*. That is intended (the legacy tab is a comparison artifact) — worth one line in
    the release note so it does not read as an oversight.

## 23.4 What the probe already proves

A `pg.LegendItem(pen=…, brush=QColor(20,20,20,170), frame=True, labelTextColor="#ffffff")`, parented to the
ViewBox and anchored `itemPos=(1,0), parentPos=(1,0), offset=(-14,14)`, renders exactly Edwin's mock:
**semitransparent, bordered, north-east, padded** — with five text rows and badges sitting on the annotations,
and the y-range provably still. Nothing in §23.3 is a blocker; items 4, 5 and 6 are cosmetic decisions that
should be made before the code, not during it.

## 23.5 Settled by Edwin 2026-08-10

* **D-sample: BADGE-AS-SAMPLE.** The legend's sample column paints the badge itself, so a row reads
  `[③] red-anchor mean`. The `(n)` text prefix of the mock is dropped — the badge carries the number in both
  places, which is the whole point of the contract.
* **D-frame: the legend box has SQUARE corners** (`frame=True` as-is on screen; `boxstyle="square"` on paper).
  ⚠ This settles the *box*. The **badge** shape stays as mocked — a **circle** — which on screen means a
  `ScatterPlotItem(symbol='o')` disc under a centred `TextItem`, and on paper `boxstyle="circle"`. Two items
  per badge on screen; that is the honest cost of matching the mock on both grounds.

---

# 24 · CHANGE REQUEST — also render the baseline-SUBTRACTED spectrum?  *(Edwin 2026-08-10)*

> **DESIGN ONLY.** ⚠ I measured this before answering, and **the measurement killed my first argument for it.**

## 24.1 What it would buy — measured, on two real runs

| run | raw span | corrected span | **y-zoom** | if OVERLAID: separation |
|---|---|---|---|---|
| green `20270729B/001` | 0.083 – 2.078 (1.996) | −0.079 – 2.051 (2.130) | ⛔ **×0.94** | 0.028 – 0.205 = **1.4 – 10.3 %** of the y-span |
| brown `20260731A/001` | 0.074 – 2.103 (2.029) | −0.057 – 2.051 (2.108) | ⛔ **×0.96** | 0.052 – 0.170 = 2.6 – 8.4 % |

⛔ **The subtraction buys NO resolution.** I expected the Q region to gain ~2.7× of vertical space; it gains
**nothing** (×0.94, marginally worse), because the baseline at 448 nm is only ~0.04 while the Soret flank still
towers at 2.05. **The Soret flank sets the y-range before and after.**

⇒ **The real lever for reading `B_Q` is a y-RANGE CLIP, not the subtraction.** That is a different feature
(`yRange=(lo, hi)` on the view — generic, and useful elsewhere), and it is what would actually make the
metric's fragile half legible: `B_Q` = 0.069 against `B_Soret` = 0.765 is **11×**, i.e. §16.24's asymmetry, and
no single linear axis shows both halves well.

⭐ **A genuine bonus the measurement did produce:** on the corrected curve the two anchors read **+0.0004 and
−0.0004** — 0.05 % of `B_Soret`. So §18 duck #1's hedge ("on the line only up to the within-window residual")
is true but far tighter than feared: the equal-weight LSQ fit lands the anchors on zero to four decimals.
⇒ the tolerance in `test_band_bar_identity` can be tightened from 0.02 to ~0.005 and still hold.

## 24.2 ⭐ What I say: yes — but as its OWN step, and not for the reason I first assumed

**Yes, render it.** The corrected curve is *literally what the verdict reads*: on it, `B_Soret` and `B_Q` are
heights above **zero** rather than gaps you measure by eye, and both anchors sit visibly ON zero — the running
self-check of §12.3, made unambiguous.

⛔ **But NOT overlaid on `Absorption (bands)`.** Two reasons, both measured or structural:

1. the two curves sit within **1.4 – 10.3 %** of each other, so over most of the range they read as one thick
   line — the separation is only obvious in the red, where both hug the bottom;
2. ⚠ **it would ambiguate the bars.** The mean bars are means of *the plotted curve*, and the whole §12.3
   picture is "bar − line = the metric". With two curves a reader cannot tell which one a bar belongs to, and
   the answer would silently become "the wrong one".

⇒ **A separate EVALUATION step, `Absorption (baselined)`**: the corrected curve, the same four bands, bars at
the corrected means — which now **are** `B_Soret` / `B_Q` directly — and a zero line the two anchor bars land
on. The construction lives on one tab, the result on the other.

## 24.3 Open, for Edwin

1. **Step count.** EVALUATION goes 5 → 6 tabs (Metrics, Absorption (bands), **Absorption (baselined)**, Report,
   Metrics (dev), Absorption (bands, dev)). Fine on the bench; noted for the phone-width layout.
2. **Legend/numbering there?** Scope says `Absorption (bands)` only. ⭐ Lean: keep it that way — on the
   baselined plot the bars *are* the values, so inline captions suffice and a second legend would be noise.
3. ⭐ **Do you want the y-range clip** (`yRange=(-0.05, 0.30)`) on the baselined step? It is the only thing that
   makes `B_Q` readable as a height. ⚠ Cost: the Soret bar (0.77) goes off-scale on that view — the Q half and
   the Soret half genuinely do not fit one linear axis.

---

# 25 · SETTLED DESIGN — the `Absorption (bands)` plot, final  *(Edwin 2026-08-10, over four mockup rounds)*

Supersedes the open questions in §21–§24. Everything here was agreed against a rendered mockup on real data
(`20270729B/001`), not on paper.

## 25.1 The picture

| # | element | drawn on | why |
|---|---|---|---|
| ① | Soret band mean | ⭐ the **SUBTRACTED** curve | its height **is** `B_Soret`, the numerator `M` divides |
| ② | Q-band mean | ⭐ the **SUBTRACTED** curve | its height **is** `B_Q`, the denominator |
| ③ | red-anchor mean (620–630) | ⭐ the **RAW** curve | the anchor DEFINES the line; its bar landing on the dashed line is the proof |
| ④ | quiet-anchor mean (520–540) | ⭐ the **RAW** curve | same |
| — | `A(λ) despiked` | — | the measurement |
| — | `A(λ) − baseline` | — | what ① and ② are measured on |
| — | `fitted baseline` (dashed) | — | what ③ and ④ define |

⭐ **The rule behind it (Edwin's):** *a bar sits on the curve that gives it meaning.* Fit inputs on the raw
curve, metric inputs on the corrected one. It replaces both of my proposals — "all bars on raw" (the metric
stayed a gap you had to measure by eye) and "all bars on corrected" (③ and ④ collapse onto the axis and stop
distinguishing themselves).

⭐ **A colour rule falls out for free: a bar wears the colour of the curve it was measured on.** Cyan bar → cyan
curve, gold bar → yellow curve. Ownership is readable without a caption — which is exactly what makes two
curves safe to overlay (§24.2's objection, answered).

## 25.2 Numbering and legend

* **Bars are numbered; CURVES ARE NOT.** A curve is named in the legend by text **in its own colour**; a bar is
  named by a badge. ⇒ the legend has two row kinds, and the kind tells you what the row is.
* **Badge fill = a DARKENED shade of the bar colour, ring = the bar colour, numeral = white.**
  ⚠ Measured, and this is why: white on the raw bar colours is **1.84 : 1** (cyan) and **2.42 : 1** (gold)
  against a 4.5 : 1 requirement — unreadable at bench size and worse in print. Darkened: **5.24 : 1** and
  **4.96 : 1**. The badge still reads as "the cyan one" / "the gold one", so Edwin's rule is kept, not dropped.
  *(Third instance of the two-ground rule: near-white bars §20.2, faint captions §21.2, this.)*
* **Legend box: square corners, semitransparent, bordered, `NORTH_EAST`.**
* **Padding is a MAGNITUDE; the renderer owns the sign** (§23.2). Shipped value **34 pt** — enough to clear the
  band-caption row, which is what Edwin asked for after seeing the box collide with `red anchor`.
* **Rows are DERIVED** from the numbered levels (ascending) then the labelled traces (declaration order).
  ⛔ Never a parallel list — badge and row must be the same fact (§23.3 duck #1).

## 25.3 Band captions stay

At the **top**, in **white** (§21.2 — they had been inheriting the anchors' semi-transparent shading colour,
which is why "near anchor" / "far anchor" read as ghosts). ⚠ **Bottom-anchoring is rejected**: it was only a
workaround for the legend collision, and the padding solves that properly.

⚠ **New, found in the final mockup: the `red anchor` caption is CLIPPED by the right plot edge.** Its band is
centred at 625 with the window ending at 636, so a centred caption overflows and reads "ed anchor". Nothing to
do with the legend — it would happen without one. ⇒ **clamp**: a caption whose box would leave the view pulls
its anchor to that edge instead of centring.

## 25.4 Also in this build (from §21.1)

**The DN limits move to the SAMPLE step**, drawn with their captions like the PROCESSING plot. `CaptureView`
stops carrying `dnGuards`/`dnTarget` (bare numbers, captions nowhere) and carries **`levels`** in the same
shape as `SpectrumPlotView` — so value, caption, colour and style exist once and the live preview cannot
drift from the report. ⛔ And `CapturePanel.__drawLowDnGuard` must read `__activeStep`, not `steps[0]` — today
it draws the *Reference* step's declaration on whichever role is on screen.

## 25.5 What this does to the §12.3 identity

The identity is unchanged and still exact — `mean(raw) − mean(line) = mean(corrected)` — but **the picture now
states it differently**: it used to be a gap between a bar and a line; it is now a height on the corrected
curve. ⇒ the test gets *more* specific, not weaker: **anchor bars must equal `bandMean(raw)`, S/Q bars
`bandMean(corrected)`**. That assertion is what stops a later edit feeding a bar the wrong curve — which would
render plausibly and be wrong.

## 25.6 BUILD REPORT — implemented 2026-08-10

**351 tests green** (324 app + 27 plugins). Verified on real archive runs and on both renderers before any rig
time. ⛔ C4 (rig click-through) still Edwin's.

**What the build changed about §25:**

1. ⚠ **The measured curve is declared as a TRACE, not as the view's primary spectrum.** Only a trace carries a
   label, and the legend names every curve by text in its own colour — a primary would have left the yellow
   curve as the one unnamed thing on the plot. `view.spectrum` is therefore `None` on this view; the identity
   test reads `allTraces()[0][0]`.
2. ⚠ **The marker is now `λmax`, not `Q`.** With the Q band captioned "Q" and the marker sitting *inside* it,
   two captions read "Q" a few nm apart — §22.1's duplicate defect, which numbering was supposed to dissolve
   and did not, because both captions survived. The marker now names what the line actually is.
3. ⚠ **Marker captions moved to the BOTTOM row, in both renderers.** A marker usually sits inside a band, so
   band captions (top) and marker captions (bottom) would otherwise overprint — `λmax` was drawn straight
   through `Q`. Bands own the top row, markers the bottom.
4. ⚠ **The paper legend is drawn per row, not as one text block.** Each row carries its own colour and
   matplotlib paints a text block in one; the first cut was ragged-right and monochrome. Rows are now
   individual `ax.text` calls inside a drawn `Rectangle`, with the curve colours **darkened for paper** —
   the screen's `#e8e337` yellow on white is unreadable. *(Fourth instance of the two-ground rule.)*
5. ⚠ **The anchor-on-the-line tolerance is RELATIVE, not absolute.** On real archive data the residual is
   0.0004 (0.05 % of `B_Soret`); on the synthetic test fixture, whose anchor windows are far more curved, it
   is ~2 %. An absolute tolerance would have encoded the fixture. The test asserts `< 5 % of B_Soret`.

**Also in this build:** `CapturePanel.__drawLowDnGuard` now reads `__activeStep` (it read `steps[0]`, i.e.
always the Reference declaration), the DN levels are declared on the SAMPLE step only, and both renderers
clamp a band caption that would overflow the window edge (`red anchor` at 625 nm read as "ed anchor").

## 25.7 ✅ Click-through confirmed — Edwin 2026-08-10

> *"okay, all works as expected"* — driven in the running app after the §25 build.

⇒ **C4's GUI half is done**: EVALUATION → `Absorption (bands)` renders the two curves, the fitted baseline,
the four numbered bars on their correct curves, the legend, the captions — and it **holds still** (the
auto-range runaway of §20.2 is gone, confirmed on the rig-side app rather than only in the headless harness).

⚠ **What this confirmation does NOT cover**, and is therefore still owed on the next real measurement:
the **PDF** end of M2 (verified headless here, not on a saved report), the **LIMS badge** on PUBLISHING, and
the **60-frame capture** against the 150-frame-derived corridor (§20.4). None is blocking; all are one real
run away.

**Cross-references updated in the same commit** — each of these said something that is now false:

| doc | was | now |
|---|---|---|
| `SPEC_metric_research.md` §9.1 S1 | "ADOPTED — ship it with the next threshold work" | ✅ SHIPPED, and the row's *"plus a plugin re-sign"* is retracted (§18 S1: the plugin cannot pass the publish lint) |
| `SPEC_first_presentable_state.md` step 1 | "no-op version bump, then Soret trim + re-sign" | trim ✅ done; ⛔ the publish rehearsal is still owed and must use `PumpkinOilPlugin` |
| `SPEC_roast_ampel.md` §8.6 table | T = 10.6 / 12.5 | T = **6.8 / 8.3**, with the scale-change warning |
| `SPEC_capture_quality.md` §16.27.11 | "the 448 trim landing … quotes `M448` as if it ships" | it ships; both thresholds moved with it |
