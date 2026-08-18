# SPEC — `V` / `Q%` in the DEV plugin

> **Status: IMPLEMENTED 2026-08-14 — V2–V7, V9 (domain guard) and V10 (archive regenerated) all done.
> Only V8, the rig click-through, is left.** This document is the UI-and-integration half of
> [`SPEC_metric_research.md` §10](SPEC_metric_research.md) — which owns the *finding* and is
> **pre-registered and frozen**. Nothing here may change what §10 defines; where a decision here would
> touch the definition, it is recorded in §10 instead and cross-linked from here.
>
> Author: Edwin's session with Claude, 2026-08-14. Reproduce every number with
> `diagnostics/box_metrics.py` and `diagnostics/box_terms.py`.

---

## 1 · What this delivers, in one screen

The DEV plugin's `EVALUATION` phase gains **one gauge, four metric rows and one new step-tab**:

```
EVALUATION
 ├─ Metrics                         ← Q% gauge at the top, then Q% / V / the three band means
 ├─ Absorption (bands)        NEW   ← the V picture: 3 bars, a crosshair, a zero datum
 ├─ Absorption (bands, baseline)    ← the old chord picture, renamed
 ├─ Report                          ← both plots, additive
 ├─ Metrics (dev)                   unchanged
 └─ Absorption (bands, dev)         unchanged
```

⭐ **Almost everything below is expressible with primitives that already exist.** `addLevel` already
draws both a band bar and a full-width guide line (`SPEC_soret_448_trim.md` §12.2); `GaugeColorUtil` is
already orientation-aware and already takes a threshold *list*; `GaugeWidget` is generic over
`len(classes)`; `MatplotlibWorkflowRenderer` already draws levels, numbered badges and legend rows.
⇒ **No model change and no renderer change**, on either the screen or the paper path.

⛔ **ONE core change is required, and the first draft of this document was wrong to deny it.** There is
**no numpy anywhere in `spectracs-plugins`** and `SpectrumFeatureUtil` has no level-crossing helper, so
the crosshair of §6.2 cannot be computed in the plugin tier. §7's `levelCrossing` is an **additive**
addition to `SpectrumFeatureLogicModule` — it touches no existing behaviour — and it is a
**prerequisite of V5**, not a nicety.

---

## 2 · `Q%` — the human-readable form of `V`

```math
Q\% = 100 \times \frac{A_{Q} - A_{valley}}{A_{Soret}} = -100 \times V
```

Read as: **the Q band's height above the valley, as a percentage of the Soret flank.** The absorbance
units cancel, so this is a real percentage — nothing is invented and no constant is bolted on, and the
transform is exactly reversible.

| | |
|---|---|
| ⭐ direction | **higher = browner.** It reads as a roast index: the number rises as the oil darkens |
| range on the archive | **12.70 … 20.82** over 58 runs (fill means 13.8 … 20.4) |
| display precision | ⭐ **one decimal.** Within-fill sd is 0.70 and the refill floor 0.21 — 0.01 would be theatre |
| relation to `W` | `W` is already positive (0.163 … 0.239); quote it as a percentage if it ever appears in text |

⛔ **`V` stays the frozen quantity.** `Q%` is a *display transform*. Every spec sentence, every
diagnostic script and PRIO 2c's pre-registration continue to speak `V`; the screen speaks `Q%`.

⚠ **The sign flip inverts every ordering sentence.** §10's *"less negative = greener"* becomes
*"lower = greener"*, and **green is now BELOW the line**. That is the one place a careless edit flips
a verdict.

### 2.1 What was rejected, and why

| form | why not |
|---|---|
| rescale so the threshold lands on a round 20.0 | ⛔ anchors the display scale on a **provisional** threshold — PRIO 2c may move `T_V`, and every stored measurement would need rescaling. It also destroys the percentage reading |
| signed distance to the line (`18.6 − Q%`) | the most decision-useful form, and what the gauge computes *internally* — but it puts the sign back and inherits the same provisional-threshold problem |
| a 0–100 "greenness score" | ⛔ the corridor endpoints would be invented, and a score implies **ranking greens**, descoped in `SPEC_capability_proof.md` §1a and restated in `SPEC_capture_quality.md` §16.34.4 |

---

## 3 · The computation — three frozen constants, and one trap

In `DevSpectralPlugin`, beside the existing `PB_*` constants:

```python
V_SORET_BAND  = (448.0, 460.0)   # == PB_SORET_BAND — the same window
V_VALLEY_BAND = (500.0, 560.0)   # ⛔ NEW — NOT GREEN_BAND (510–540)
V_Q_BAND      = (565.0, 580.0)   # ⛔ NEW — NOT PB_Q_BAND (560–580)
V_THRESHOLD   = -18.6            # §10.3, in V×100. The gauge derives its +18.6 from THIS.
V_SORET_FLOOR = 0.15             # §3.1  — below this, nothing is reported at all
V_VERDICT_BAND = (12.0, 22.0)    # §3.1a — outside this, the VALUE stands but no verdict is drawn
```

⭐ **Q4 — one signed source for the threshold.** `T` lives once, in `V` units with `V`'s sign, and the
gauge negates it. Otherwise `−18.6` in `box_metrics.py` and `+18.6` in a gauge preset are two constants
in two repositories that mean the same thing and can drift apart silently.

⛔⛔ **The trap.** The plugin already carries `PB_Q_BAND = (560, 580)` and `GREEN_BAND = (510, 540)`.
**Neither is `V`'s window.** `V`'s Q band starts at **565**, and §10.1's edge test found the Q window
is the *sensitive* one — `572–578` breaks the separation outright. Reusing `PB_Q_BAND` would render
plausibly, disagree with `box_metrics.py`, and **nothing would error**. The constants are declared
separately, commented as pre-registered, and pinned by a test (§7 T1).

Computed on the **de-spiked** absorbance the tab already has — `__despikedAbsorption`, median
kernel 7 — with no baseline of any kind:

```python
soret  = util.bandMean(despiked, *V_SORET_BAND)
valley = util.bandMean(despiked, *V_VALLEY_BAND)
q      = util.bandMean(despiked, *V_Q_BAND)
qPercent = 100.0 * (q - valley) / soret        # V ×100 = −qPercent
```

⭐ **Sampling is already correct by construction.** `SpectrumFeatureLogicModule.bandMean` averages the
**native samples, both edges inclusive**, which §10.1a made the canonical convention precisely so this
line and `box_metrics.py` produce the same number. That reconciliation is **V0 and it is done**.

⚠ **The de-spike cannot drift either:** `diagnostics/settling_sweep.despikedAbsorption` calls
`_DevSpectralPlugin__despikedAbsorption` directly, so the diagnostics and the app share one kernel.

### 3.1 The denominator guard — one condition, three consumers

`A_Soret`'s archive minimum is **0.334**. A failed capture could drive it toward zero and `Q%` would
explode. ⇒ **No verdict below `A_Soret` < 0.15.** This is the same shape as the existing `__EPS` clamp
but it *withholds a verdict* instead of clamping into one.

⚠ **Q7 — it is evaluated ONCE and passed down, because it has three consumers:**

1. **no gauge at all** — not a clamped pill;
2. all five new metric rows read **`—`**;
3. the §6 plot draws the trace and the shaded bands but **no bars, no crosshair, no zero datum** —
   every one of those is an annotation asserting a number we just declined to report.

⭐ **Verified on real data, and it fires:** all **27 runs of the `20260806A` null series** — no oil in the
beam — correctly come back with no `Q%` verdict.

### ⭐⭐ 3.1a The DOMAIN guard — a second condition, on the same principle

```python
V_VERDICT_BAND = (12.0, 22.0)     # must equal the gauge's own band
```

⛔ **A gauge CLAMPS a value past its band edge** (`GaugeColorUtil`, RD#5) — the marker saturates and the
verdict is whatever the end class says. Measured across the archive, that is not hypothetical:

| | |
|---|--:|
| reports that receive a `Q%` value | 143 |
| inside the scored corridor 12.70 … 20.82 | 92 (64 %) |
| ⛔ above it, would clamp to **brown** | 49 — worst **39.90** |
| ⛔ below it, would clamp to **green** | 2 — worst **−28.34** |

⛔ **The negatives are the sharpest case.** `Q% < 0` means `A_Q` sits *below* `A_valley`: there is no Q
band at all, so the sample is not oil-shaped — and `measurement_report_cappy_002.pdf` at **−28.34**
would have been stamped **"good — green"**. ⇒ **No verdict outside the band.**

⚠ **The BAND, not the scored corridor.** Thirteen archived runs sit between 20.82 and 22.0 —
`20260731A/004` at 20.94, `20260808B/001` at 21.08 — and those are real brown-oil measurements a hair
past the corpus. **They keep their verdict.** The band is the gauge's own declared scale; past it the
metric was never scored at all.

⭐⭐ **It withholds the PILL ONLY — and that is why it is a second guard, not an extension of the first.**
A sub-floor `A_Soret` means the *measurement* is broken, so nothing is reported. An out-of-band `Q%`
means the measurement is fine and the **sample** is outside the metric's domain: the band means are
real, the bars belong where they are, and blanking them would destroy evidence. Only the verdict has no
basis, so only the verdict goes.

⭐ **It caught a fixture, too.** The synthesized playground oil used by `test_verdict_gauge` reads
`Q% ≈ 48` — more than double the archive's browning end — so it is nothing like a real oil spectrum
through this instrument, and it now correctly carries no pill.

---

## 4 · ⭐⭐ The gauge — THREE classes, because two would violate §10.3

`RoastQPercentGaugeView`, a thin preset of `VerdictGaugeView` exactly like its three siblings.

```
       green            │ 17.9 │  borderline — re-measure  │ 19.3 │  probably too brown
   bandLeft 12.0                        T = 18.6                            bandRight 22.0
```

| | |
|---|---|
| band | **ascending** — `bandLeft = 12.0` (green), `bandRight = 22.0` (brown). `GaugeColorUtil` is explicitly orientation-aware ("band may descend"), so this needs no SDK change |
| thresholds | `[17.9, 19.3]` → three classes. A value exactly on a boundary stays in the **left** class, which with an ascending band means the greener one — matching §10.3's `V > T_V` convention |
| render | `BAND \| LABEL \| SWATCH`, as `RoastFar620GaugeView` |
| chips | the siblings' `_GOOD` / `_BROWN` colours, plus a neutral amber for *borderline*, so a verdict reads the same everywhere |
| headroom | lowest run on record 12.70, highest 20.82 — the band clears both |

### 4.1 Why three classes is a requirement, not a refinement

§10.3 already says it: *"a fill whose runs straddle the line has no verdict and the gauge must say so
rather than average its way to one."* A two-class gauge **cannot** say so. Measured run by run at
`T = 18.6` (native sampling, `Q%`):

| fill | its runs |
|---|---|
| Steirerkraft half-strength | 16.49 · 17.63 · 18.38 · **19.35 · 19.44 · 19.79** |
| Steirerkraft aged 24 h | 15.97 · 18.10 · **19.34** |
| Spar Steirisches g.g.A. | 18.06 · 18.34 · **18.81** |

⇒ ⛔ **the pill would flip between two consecutive captures of the same jar** — one fill spans 3.3
units across six runs. That is the §16.20 defect class: *a gauge reporting a confident verdict it
cannot support.*

⚠⚠ **THE SCATTER THAT SIZED THIS ZONE HAS SINCE BEEN MEASURED AGAIN, AND IT IS 2.5× SMALLER**
*(2026-08-18, `SPEC_settled_measurement.md` §28)*. The 0.70 below is the within-fill sd of the OLD
protocol — a fill being re-measured while it cleared and browned (§16.36). Under the settled measurement,
five SEPARATE preparations of one oil scatter by **0.276**, and the archive's pooled within-fill figure was
**1.255**. ⇒ **the borderline zone is roughly 2.5× wider than today's measurement needs**, and every
straddler in §4.1a was measured under the drifting protocol.
⛔ **NOT re-derived here, deliberately.** The corpus that fixes the zone must be re-measured too — a
narrower zone hands out confident verdicts, so it may only be narrowed on data taken under the protocol it
will run under. ⇒ **re-derive after the brown series** (ROADMAP item 2); until then the zone stays wide,
which is the safe direction.

**The edges are measured, not chosen.** `18.6 ± 0.70` is the **within-fill sd** — the run-to-run
scatter of the very quantity on the axis. And it is free: the corpus's empty corridor runs
**17.14 … 20.19**, so `[17.9, 19.3]` sits entirely inside dead space and ⭐ **no corpus run changes
class.**

#### ⚠ 4.1a What the zone does NOT fix — measured, and pinned by a test

⛔ **The zone narrows the flip-flop; it does not abolish it.** Only one of the three straddlers is fully
absorbed:

| fill | its runs under the three classes |
|---|---|
| ⭐ Spar Steirisches g.g.A. | 18.06 · 18.34 · 18.81 — **all borderline**, no confident verdict at all |
| ⛔ Steirerkraft aged 24 h | **15.97 green** · 18.10 borderline · **19.34 brown** |
| ⛔ Steirerkraft half-strength | **16.49, 17.63 green** · 18.38 borderline · **19.35, 19.44, 19.79 brown** |

Those two fills span **more than the zone is wide** — 3.3 units in the half-strength case — so they
still produce both a green and a brown run. ⚠ Note *what* they are, though: a half-concentration
preparation and a 24-hour-aged fill, i.e. **§10.4's two known weaknesses of `V` itself**. The gauge is
reporting a real instability in the measurement, not inventing one. `test_v_metric.py`'s
`testTheBorderlineZoneCatchesWhatItCanAndNoMore` pins exactly this, so nobody later over-promises it.

### 4.2 The threshold

`T = 18.6`, with the corridor midpoint at **18.665** (native sampling, §10.3). 18.6 is kept on the
**strict** side per `SPEC_capture_quality.md` §16.10.17d — a false GREEN is the harder error to make —
and it matches the displayed decimal. No archived run lies between the two.

### 4.3 What the gauge still cannot promise

⚠ Both Spar g.g.A. oils read **green** under `T_V`, contradicting §16.30.1a's relabel, and the
threshold corpus deliberately excludes the boundary products. A pill drawn on a Spar oil is an
**extrapolation**. The tooltip says so; the gauge cannot. ⇒ PRIO 3a still owns ground truth.

---

## 5 · The Metrics tab — placement and rows

```
 ①  RoastQPercentGaugeView                    NEW — above both existing gauges
 ②  RoastPedestalGaugeView                    unchanged
 ③  RoastFar620GaugeView                      unchanged
 ④  colour chips                              unchanged
 ⑤  Q%                              18.4      NEW  ← head of the metric block
 ⑥  V ×100 (frozen def.)           −18.4      NEW  ← audit row, speaks box_metrics' language
 ⑦  A_Soret · 448–460 nm            0.563     NEW
 ⑧  A_valley · 500–560 nm           0.068     NEW
 ⑨  A_Q · 565–580 nm                0.160     NEW
 ⑩  Soret · 448–460 nm  … (every existing row, untouched)
```

⭐ **Q1 — all three gauges stay.** §16.20 built that ladder deliberately: *three verdicts in decreasing
order of how much correction has been applied*, so that each adjacent pair isolates exactly one change.
`Q%` joins it at the top as the **uncorrected-but-conditioned** rung. It is a lot of screen, and that
is what a dev bench is for; the end-user path shows one verdict and is untouched (§8).

⭐ **Q6 — precision, and why the three differ.** `Q%` one decimal (within-fill sd 0.70 — 0.01 would be
theatre). `V ×100` **two** decimals: its entire job is to be diffed against `box_metrics.py`, which
prints two. The three `A_*` rows three decimals, matching the existing `Soret · 448–460` row beside
them.

⭐ **Why keep ⑥ when it is ⑤ with a sign.** It is the number §10, `box_metrics.py` and every future
spec sentence speak, and having both on screen is what catches a window silently drifting out of sync
with the frozen definition.

⭐ **Why ⑦⑧⑨ when the tab already has `Soret · 448–460`.** That row *is* the same window — but
`Q · 560–580` and `Clarity · 510–540` are **not** `V`'s windows. Emitting all three of `V`'s inputs
under their own names is what makes the difference visible rather than a thing a reader must know.

**Tooltips carry the caveats that must travel with the number:** ⛔ a lamp swap moves it **4.84** —
more than the whole class gap, so *a chart cannot cross a lamp change*; ⛔ half concentration moves it
**2.19**; ⚠ **not yet tested on data it was not tuned on** — PRIO 2c / σ_fill is that test.

---

## 6 · The new `Absorption (bands)` step

The old tab draws the **chord** picture — two curves, a fitted dashed baseline, four bars, `λmax`.
`V`'s picture is a different one: **one curve, no baseline anywhere.** That is why it earns its own
tab instead of more bars on the old one.

| element | how |
|---|---|
| trace | `A(λ) despiked` only. ⛔ no corrected curve, ⛔ no fitted line — there is nothing to fit |
| shaded bands | ① Soret 448–460 · ② valley 500–560 · ③ Q 565–580 |
| **bars** | `addLevel(mean, lo, hi, number=n)` on the **despiked** curve for all three |
| ⭐ **crosshair** | horizontal arm at `A_valley` + vertical arm at the λ where the curve *attains* it |
| ⭐ **zero datum** | `addLevel(0.0, 448, 460)` — a **ranged** bar under the Soret window |
| marker | ⛔ none. The old tab marks `λmax` because `D_Q` measures a peak height; `V` is window means only, and a peak marker would suggest a quantity the metric does not use |
| legend | `NORTH_EAST`, five numbered badges (§6.3) |
| title | `A(λ) — V bands (despiked)` |

### 6.1 ⭐ Why the picture is the arithmetic

With the crosshair and the zero datum in place, both halves of the formula are **distances on screen**:

```
   ③ Q bar
      ↕   ← the NUMERATOR      (A_Q − A_valley)
   ④ valley crosshair ─────────────────────────────  full width
   ...
   ① Soret bar
      ↕   ← the DENOMINATOR    (A_Soret, measured from zero)
   ⑤ zero ───────────  under 448–460
```

That is the same rule the chord tab was built on (`SPEC_soret_448_trim.md` §12.3, §25.1): **a bar sits
on the curve that gives it meaning**, and the gap between two annotations *is* the number the verdict
divides. Without the zero datum the denominator has nothing to be measured against and the picture
tells only half the story.

### 6.2 The crosshair — at the λ where the curve attains its own window mean

⛔ **Not at the minimum.** Measured over 58 runs, the minimum inside 500–560 sits at **509.1 ± 5.3 nm**
— hard against the *left edge* — and `A_valley` lies **23 % above** it (0.0198 A). A cross drawn there
would sit on the curve but 23 % below the number `V` divides: it renders fine and is silently false,
exactly the failure §12.3 warns about.

⭐ **Instead: the λ inside 500–560 at which `A(λ) = A_valley`.** Both arms are then true statements —
the horizontal is exactly the number `V` uses, and the crossing point sits **on the curve**. Measured:
**522.2 ± 1.5 nm** across 58 runs, 15 fills, 7 products, range 518–526.

⚠ **Q5 — the helper's contract.** `levelCrossing(spectrum, lo, hi, value) -> nm | None`: scan the
window in wavelength order and return the **first** sign change of `A(λ) − value`, **linearly
interpolated** between the bracketing samples so the marker sits where the curve actually crosses
rather than on the nearest sample; `None` when the value lies outside the window's range. **First**,
because eight of fifteen fills show 3 or 5 sign changes from noise wiggles near the mean, all within a
nanometre or two of each other. For the valley window a crossing always exists — the mean of a
continuous curve lies between its min and max — so `None` here means the data is broken, and the
caller draws nothing.

⭐ **A by-product for `KB_spectroscopy_physics.md`:** the "valley" is **not a basin**. Its minimum is
pinned at the window's left edge and the curve rises monotonically from there toward the Q band, so
`A_valley` is a **slope average**, not a floor level. That is a physical reason for §10.1's
edge-sensitivity result, and one more piece of evidence against *"the valley is the pigment's own
zero"* — the same conclusion §10.2's `u` finding reaches from the other side.

### 6.3 The legend is not optional

`SpectrumPlotView.legendRows()` builds rows from exactly two sources: **levels carrying a `number`**,
and **traces carrying a label**. An unnumbered level gets no row. ⇒ the crosshair and the zero datum
must be **numbered too**, or they are two unexplained lines on the plot:

```
①  Soret band mean            448–460 nm      ← the denominator
②  valley band mean           500–560 nm
③  Q band mean                565–580 nm      ← numerator = ③ − ②
④  valley level   A(λ)=A_valley @ ~522 nm     ← the crosshair
⑤  zero                                       ← what ① is measured from
   A(λ) despiked                              ← the trace, named by its colour
```

### 6.4 Two rendering decisions, both forced by the renderer

⚠ **The zero datum is a RANGED bar, not a full-width line.** An unranged level renders as a
`pg.InfiniteLine` on screen and `ax.axhline` on paper, and a ranged one as a plain `plot()` call that
participates in autoscale **by construction** — so the ranged form needs no assumption on either path.
It is also exactly where the denominator is read.

⭐ **What the implementation then found, recorded so the reasoning is not overstated.** On the *screen*
path a guide line **does** drive auto-range, deliberately — `tests/test_plot_annotations_do_not_rescale`
states it outright: *"Guide LINES deliberately still do — that is what makes a 60 DN guard visible when
a fill peaks below it"*. So the ranged bar was not dodging a screen bug that existed; it removes an
assumption, and it is the right call for the matplotlib path regardless. **Verified after
implementation**: the Qt view settles at `y ∈ [−0.080, 1.663]` on an archived fill — zero visible,
range identical across twelve event-loop ticks (no runaway).

⭐ **Q2 — the bars are GOLD, and that is a semantic choice, not a free one.** On the chord tab
`__METRIC_BAR` (cyan `#35d3d3`) means *"measured on the subtracted curve"* — and this tab **has no
subtracted curve**, so cyan would carry a false meaning two tabs apart. But `__ANCHOR_BAR`
(gold `#c9a227`) already means *"measured on the raw/despiked curve"*, which is **exactly** what all
three `V` bars are. ⇒ gold, and the colour keeps meaning the same thing across both tabs.
⚠ The despiked trace is yellow `#e8e337`, so gold-on-yellow is the legibility risk to watch at V8; the
bars are horizontal against a diagonal curve, which is what makes it survivable. The crosshair and the
zero datum take a **distinct fourth colour** so construction never reads as measurement.

---

## 7 · `levelCrossing` — the one core addition

```python
# SpectrumFeatureLogicModule  (+ a SpectrumFeatureUtil passthrough)
def levelCrossing(self, spectrum, lo, hi, value) -> float | None
```

Contract in §6.2. **Additive** — no existing op changes — and it is where this maths belongs: the
plugin tier carries **no numpy at all**, and the numeric tests live beside `test_band_bar_identity.py`
in the app repo, not in the hermetic plugin suite.

## 8 · Tests — and where each one can actually live

⛔ **`spectracs-plugins/tests` is hermetic**: four files, no fixtures, spectra built synthetically
in-file. And `box_metrics.py` reads `spectracs-references/`**`tmp/`**, which is scratch, not committed.
⇒ A test asserting *"the plugin equals `box_metrics` on run 20260807D/001"* would depend on an
uncommitted folder. It is split instead:

| # | test | lives in | what it catches |
|---|---|---|---|
| **T1** | `test_v_metric_windows` — the constants equal §10.1 exactly, and `V_THRESHOLD` is negative | plugins | the `PB_Q_BAND` trap (§3) |
| **T2a** | `test_v_golden` — a **synthetic** spectrum reproduces an inlined `Q%` | plugins | window / formula / sign drift |
| **T2b** | ⭐ **not a test** — `box_terms.py` prints plugin-value vs script-value over the archive | diagnostics | a real-data divergence, checked by eye |
| **T3** | `test_v_band_bar_identity` — each bar equals `bandMean` of the **despiked** curve over its own window | app | the "fed the wrong curve, renders fine, silently false" failure |
| **T4** | `test_v_crosshair` — λ ∈ [500, 560] and `A(λ_cross) == A_valley` | app | the minimum-vs-mean confusion of §6.2 |
| **T4a** | `test_level_crossing` — exact on a ramp, FIRST of several, `None` outside the range | app | the §7 contract |
| **T5** | `test_q_percent_gauge` — 15.9 → green, 18.5 → green, 18.9 → **borderline**, 20.3 → brown, 25 → clamps | plugins | the three-class logic and the ascending band |
| **T6** | `test_v_zero_datum_is_ranged` — ⑤ carries `lowNm`/`highNm` | plugins | §6.4's autoscale trap regressing to a full-width line |
| **T7** | `test_v_gauge_roundtrip` — the three classes survive `toJson`/`fromJson` | plugins | `ViewModelFactory` **silently drops unknown types**; this proves the preset never becomes one |

⭐ **Why T7 passes by construction, and why it is still worth pinning.** `VerdictGaugeView.toJson` tags
`"type": "gauge"` — the **base** type — and every field round-trips (band, anchors, thresholds,
classes, `verdictLabel`, `swatchColor`). The preset subclass never appears in the JSON, so the factory
never gets the chance to drop it. That is the thin-preset pattern earning its keep.
⚠ **Consequence:** a saved run reloads with **the thresholds it was saved with**. If PRIO 2c moves `T`,
old runs keep their old line — correct (historical fidelity), but it means the threshold is *data* in
every stored measurement, not code.

---

## 9 · Phasing

| PH | deliverable | touches | gate |
|---|---|---|---|
| ✅ **V0** | the §10.1a sampling convention; `box_metrics` / `box_terms` drop the grid; §10.3/§10.4 reprint | `SPEC_metric_research.md`, 2 diagnostics | **DONE 2026-08-14** — green 15.940 ± 1.167, brown 20.443 ± 0.260, corridor 3.051, d 5.33, `T` 18.6 |
| ✅ **V1** | this document | `docs/` | **DONE** |
| ✅ **V2** | compute `V` / `Q%`; the guard evaluated **once** (§3.1). No UI | `DevSpectralPlugin` | **DONE** — T1, T2a green |
| ✅ **V2b** | the real-data reconciliation print (TABLE 6) | `diagnostics/box_terms.py` | **DONE** — 58 runs, worst |plugin − script| = **0.000e+00** |
| ✅ **V3** | the five metric rows at the head of the block | `DevSpectralPlugin` | **DONE** ⚠ the PDF grows here, not at V7 — `evaluation()` flags every item of the result |
| ✅ **V4** | `RoastQPercentGaugeView`, three classes | new file + `DevSpectralPlugin` | **DONE** — T5, T7 green |
| ✅ **V4a** | **CORE PREREQUISITE of V5** — `levelCrossing` | `SpectrumFeatureLogicModule` + `SpectrumFeatureUtil` (`spectracsPy-core`) | **DONE** — T4a green (9 cases) |
| ✅ **V5** | the new `Absorption (bands)` plot | `DevSpectralPlugin.__vBandPlot` | **DONE** — T3, T4, T6 green; crosshair lands 521.7–523.5 nm on archived fills |
| ✅ **V6** | rename the old tab → `Absorption (bands, baseline)`; fix the order | `DevSpectralPlugin.evaluation` | **DONE** — 4 label look-ups in the old tests re-pointed, cut-over recorded |
| ✅ **V7** | report, **additive** — both plots on paper | `DevSpectralPlugin` | **DONE** — smoke-rendered to PDF: gauge zones + 5 badges + crosshair all drawn |
| ✅ **V9** | §3.1a domain guard + `test_v_metric.py::VDomainGuardTest` | `DevSpectralPlugin` | **DONE** — 407 tests green; withholds on 38 of 143 archived reports, keeps the 13 near-misses |
| ✅ **V10** | ⭐ regenerate the archived reports (`regenerate_reports.py --write`) | `spectracs-references/tmp/` | **DONE 2026-08-14 — 170 rebuilt, 0 failures.** Backup `tmp_backup_pre_v_20260814/` (172 files, `diff -rq` clean) taken first. ⭐ `box_metrics.py` output **byte-identical before and after** (`md5 a4e1f30c…`) — the §10 evidence base survived. 105 reports keep a `Q%` verdict · 27 never had one (§3.1, the null series) · **38 lost theirs to §3.1a**, 34 of them the loose pre-rebuild one-offs. Archive 736 → 772 MB |
| ⏳ **V8** | rig click-through — **the only thing left after V10** | — | crosshair lands on the curve; ⑤ visible; gold-on-yellow legible (Q2's risk — it survives on paper); pill matches `box_metrics` on a live fill |

⛔ **Out of scope, deliberately: the PUBLISHING badge stays on `RoastPedestalGaugeView`.** That is the
one screen an end user sees, it drives the LIMS headline, and `V` has not yet met data it was not
tuned on. Switching it is a one-line change **after σ_fill passes** — and §16.20's record of that badge
once reporting *"good — green"* for brown oil is exactly why it does not move on a metric one session
old.

---

## ⭐ 9a · What the regenerated archive returned for free

Rebuilding 170 reports on today's plugin (V10) was a chore with a by-product: **the whole archive
scored on `Q%` in one pass**, which is the first look at the metric outside the fills it was found on.

### 9a.1 The four-oil panel — an independent ordering check

`Spectracs_Oil_Panel_2026-08-07.pdf` (`SPEC_capture_quality.md` §16.27.10) is built from
`tmp/20260807A`–`D`, four oils × three re-seats. All twelve rebuilt, and:

| oil | `Q%` × 3 re-seats | `Q%` verdict | `M448` (the panel's own column) |
|---|---|---|--:|
| Steirerkraft g.g.A. | 16.69 · 16.45 · 15.82 | good — green | 10.334 / 9.922 / 9.613 |
| Spar Premium g.g.A. | 17.14 · 18.31 · 17.86 | good — green | 7.827 / 7.706 / 7.539 |
| Spar Steirisches g.g.A. | 18.34 · 18.06 · 18.81 | ⚠ **borderline ×3** | 8.909 / 8.523 / 8.833 |
| Spar S-Budget | 19.67 · 19.72 · 20.37 | probably too brown | 6.507 / 6.497 / 6.512 |

⭐ **Identical ordering, from two metrics that share no construction** — `M448` divides a
baseline-corrected Soret by a baseline-corrected Q band; `Q%` divides a raw-curve band *difference* by a
raw Soret level, on different windows. ⚠ Not independent *evidence about the labels*, though — §10.6.2
still applies: one pigment system, many projections.

⭐ **The panel's transcribed `M448` numbers came back unchanged**, so it owes no reissue.
⛔ **But `Q%` may not be added to it** — Spar Steirisches goes all-borderline (correct per §3.1a, ugly on
a colleague-facing page) and Spar Premium reads green, which §10.3 forbids quoting. Recorded in
§16.27.10a.

### 9a.2 The archive-wide verdict census

| | reports |
|---|--:|
| keep a `Q%` verdict | **105** |
| no verdict — §3.1, `A_Soret` below floor (the `20260806A` null series) | 27 |
| no verdict — §3.1a, out of domain | **38** (34 = loose pre-rebuild one-offs) |

⚠ **62 of 170 reports carry no `Q%` verdict at all.** On a dev-bench archive spanning three rig states
that is the honest number, and it is the guards doing their job — but it is also a reminder of how
narrow the metric's proven domain currently is. **PRIO 2c / σ_fill is what widens it.**

## 10 · Open, and owned elsewhere

1. ⛔ **Ground truth** — PRIO 3a. `V`'s class separation is measured against labels that are judgment
   calls, and M448 is in the identical position. Project-wide, not metric-specific.
2. ⛔ **PRIO 2c / σ_fill** is `V`'s out-of-sample test (`SPEC_capture_quality.md` §16.34.3). Until it
   passes, every verdict this document renders is **bench-instrument only**.
3. ⚠ **The 448–460 flank** is not the Soret peak (432 nm). ROADMAP item 5 would upgrade `V` and M448
   at once.
4. ⚠ **The history tracker** (`SPEC_history_tracker.md`) is the same product in shape form and shares
   σ_fill as its control limit. Its statistic and `Q%`'s ±1.0 band are complementary, not alternatives.

## 11 · Related documents

| topic | where |
|---|---|
| the finding, frozen definition, threshold derivation | `SPEC_metric_research.md` §10 |
| the sampling convention and its limitation | `SPEC_metric_research.md` §10.1a |
| the gauge preset pattern | `SPEC_roast_ampel.md` §8.2, §8.3a |
| bars, levels, legend badges, the "picture is the arithmetic" rule | `SPEC_soret_448_trim.md` §12.2, §12.3, §25.1, §25.2 |
| the σ_fill gate `V` must pass | `SPEC_capture_quality.md` §16.34.3 |
| the shape-based sibling tracker | `SPEC_history_tracker.md` |
