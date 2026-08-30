# SPEC — `Rv`, the red ratio: the 624 band measured against the Q band

> # ⭐⭐⭐ `Rv` IS THE VERDICT METRIC
>
> **Edwin's decision, 2026-08-25.** Implementing it is the highest-priority item on `ROADMAP.md`.
> This document is the contract.
>
> ```
> Rv = 100 · (A[622–627] − A_valley) / (A[565–580] − A_valley)     T = 52,  higher = greener
> ```
>
> ⛔ **STATUS: CHOSEN, NOT YET BUILT.** `Q%` is what the code ships today and it keeps the verdict pill
> until `Rv` lands **and** clears §7. Do not read "winner" as "shipped" — nothing below is implemented.
>
> ⛔ **§7 still stands and is not waived by the decision.** Every constant here is fitted on the corpus it
> is scored on, exactly as `dQ100`'s were when `SPEC_capture_quality.md` §16.31.3a refused it. The
> decision settles *which metric the programme builds toward*; §7 settles *when it may carry a verdict*.
> Applying that bar unevenly would make it meaningless.
>
> Origin: **Edwin, 2026-08-24**, reading the `Absorption (bands)` page of `20260824Lugitsch/001.pdf` —
> *"take (3) mean and a potential mean marked by the red boxes and put them into relation"*
> (`~/ksnip_20260824-220622.png`). The observation is that the **624 nm peak is the only feature on that
> page with no band marker.**
>
> The *finding* is recorded in `SPEC_metric_research.md` §15; the physics in §2.5 below.
>
> Reproduce every number from the embedded `workflow.json` of the archived reports;
> `diagnostics/d2r_all_runs.py` and `diagnostics/today_report.py` carry the working code.

---

## 1 · What this delivers, in one screen

```
EVALUATION
 ├─ Metrics                    ← Rv gauge BESIDE the Q% gauge, + 2 new metric rows
 ├─ Absorption (bands)         ← ONE new band marker (6) at 622–627 nm; markers 1–5 unchanged
 ├─ Absorption (bands, baseline)   unchanged
 ├─ Report                         additive
 ├─ Metrics (dev)              ← Rv variants (window sweep, hR) for research only
 └─ Absorption (bands, dev)        unchanged
```

⭐ **No new spectral machinery.** `Rv` is built from **three band means the plugin already computes** —
`A_valley`, `A_Q`, `A_Soret` — plus **one new band mean**. No baseline fit, no local floor, no level
crossing, no robust statistic. `bandMean` is the only primitive required.

⛔ **`Rv` does NOT replace `Q%`.** Q% keeps its gauge and its verdict until §7 passes. `Rv` ships first
as a **number beside it**, which is the same discipline `dQ100` was held to on 2026-08-21.

---

## 2 · The metric

```math
R_v \;=\; 100 \times \frac{A_{624} - A_{valley}}{A_{Q} - A_{valley}}
```

**Both peaks measured above the same line** — marker **(4)**, `A_valley`, which the plot already draws.

| | |
|---|---|
| direction | ⭐ **higher = greener.** Opposite to `Q%`. This inverts every ordering sentence — see §2.3 |
| units | dimensionless; absorbance cancels |
| dilution | **scale-invariant by construction**: `A → cA` sends numerator and denominator both to `c·(…)` |
| range, labelled corpus | **21.9 … 125.8** over 98 guarded runs |
| display precision | ⭐ **one decimal.** Pooled within-series sd is 5.7 (§6.3) — a second decimal would be theatre |

### 2.1 ⭐⭐ It is `Q%` with the denominator swapped

```math
Q\% = 100\cdot\frac{A_{Q}-A_{valley}}{A_{Soret}}
\qquad\qquad
R_v = 100\cdot\frac{A_{624}-A_{valley}}{A_{Q}-A_{valley}}
```

**Same numerator quantity.** `Q%` divides the Q band's height above the valley by the **Soret flank**;
`Rv` divides the **624 band's** height above the valley by that same Q-band height. So `Rv` is not a new
family — it is the shipped metric with its denominator replaced by the term that carries the
green/brown information, and `A_Soret` drops out of the verdict path entirely.

⭐ **This is why the guards compose exactly** (§3.2): `Rv`'s denominator *is* `Q%`'s numerator.

### 2.2 Why the pedestal subtraction is load-bearing, not a refinement

Edwin's ratio as first drawn is `A_624 / A_Q` — no `A_valley`. Both peaks sit **on** the scattering
pedestal, and that pedestal is **additive**, so it does **not** cancel in a raw ratio:

| form | errors, 95 guarded labelled runs |
|---|--:|
| `A_624 / A_Q` — as first drawn | **4** |
| **`Rv` — pedestal removed** | **1** |

⇒ Subtracting marker (4) from **both** terms is the whole difference. It is not optional.

### 2.3 ⛔ The direction trap

`Q%` reads *higher = browner*; `Rv` reads *higher = greener*. **Green is now ABOVE the line.** Every
gauge preset, every ordering sentence and every threshold comparison flips. `SPEC_v_metric_integration.md`
§2 records the same hazard for the `V → Q%` sign flip and calls it *"the one place a careless edit flips
a verdict."* It applies here with equal force, and §8 T3 pins it.

### ⭐⭐ 2.5 Why this ratio, physically — the metric and the photophysics are congruent

⭐ **`Rv` is not a curve-fit that happens to work.** `KB_spectroscopy_physics.md` predicted its shape
before the measurement existed:

> A metallated ring (D₄ₕ) shows **two** Q bands (α, β); the free base (D₂ₕ) shows **four**, numbered I–IV
> from the longest wavelength. […] **Band I is the weakest in every one of them.** So a pigment whose
> Qy(0,0) is its dominant long-λ band while metallated becomes, on demetallation, the *weakest* of four.

| | pigment | symmetry | predicted | measured (SNV, 500–627 nm) |
|---|---|---|---|---|
| green oil | protochlorophyll, **Mg in** | ~D₄ₕ | long-λ band dominant | **624 nm is the tallest feature**, z ≈ 2.2 |
| brown oil | protopheophytin, **Mg out** | D₂ₕ | band I becomes weakest of four | **569 nm tallest** (z ≈ 2.75); 624 falls to z ≈ 0.5–0.75 |

⇒ **624 nm is band I**, 565–580 nm a shorter Q component. `Rv` is therefore a **symmetry diagnostic**: it
measures the D₄ₕ→D₂ₕ demetallation directly — the chemistry that browns the oil. Protopheophytin carries
the ring-E carbonyl, a rhodofying group, so the expected ordering is *rhodo* (III > IV > II > I) and band I
is still weakest.

⭐⭐ **And this is the physical case against `Q%`.** `Q%` divides by the Soret, and
`DOC_lamp_410_680.md` Fig. 5 already says of that window: *"the carotenoid absorption at ~455 nm rides on
top of the Soret, so the peak you can see is not the peak the chemistry is at."* **Carotenoids have no Q
bands and are not part of the porphyrin system**, so `Q%` ratios a porphyrin band against a window
contaminated by a different pigment family. `Rv` stays inside one chromophore's Q manifold — numerator and
denominator from the same electronic system. That is the likely reason `Rv` absorbed a 40–45 % dose swing
and three solvents (§6.2, §6.6) where `Q%` moved 6.5 units on one oil.

⭐ `Rv` is the **ratio form** of `DOC_metric_algebra.md` §5.8's see-saw at 568/624; `dQ100` is the
difference form.

### ⭐⭐ 2.5a EXTERNAL CORROBORATION — the analytical literature says the Soret is contaminated, from its own evidence  *(2026-08-29)*

The argument above is ours, built from our own corpus, and that is a weakness when the conclusion is
*"replace the shipping metric's denominator"*. It is worth recording that the **standard photometric methods
for pigments in edible oils reach the same statement independently**, from oil chemistry rather than from any
of our runs.

`KB_spectroscopy_physics.md` §9 records the methods in full. The relevant part:

> the carotenoid absorption at 460–470 nm and the porphyrin **Soret** band **overlap**, and the standard
> method says so explicitly — a single absorbance there is a two-pigment-family mixture, and separating them
> needs chromatography, not photometry.

⇒ **three independent arrivals at the same place**: `DOC_lamp_410_680.md` Fig. 5 (our lamp), §2.5 above (our
spectra), and the AOCS / Mínguez-Mosquera method literature (neither). ⭐ This is the strongest form the
argument has had, because the third one has no stake in `Rv`.

⭐ **And the standard chlorophyll formula is `Rv`'s construction.** AOCS Cc 13d-55 reads
`A670 − (A630 + A710)/2` — a band height against the **mean of two flanking anchors**. That is §2.2's pedestal
subtraction, arrived at from turbidity in oil rather than from our pedestal work. The methods and this spec
agree on *how to read a band*; they differ only on which band the clamp leaves us.

⚠ **What this does NOT do.** It does not touch §7's pre-registration gate, it is not evidence for `Rv` over
`dQ100` (both are anchored the same way), and it says nothing about the diffuser failure of §6.7. It removes
one objection — *"the Soret complaint is a story fitted to our own corpus"* — and nothing else.

⚠ **Three caveats travel with this argument and must not be dropped when it is quoted:**

1. ⛔ **Q-manifold conservation is untested, not shown** — total Q per unit Soret reads 7.85 / 5.56 / 6.71
   on the three oils. If demetallation only redistributed intensity that should be flat. It is not —
   though the denominator is the same contaminated Soret, so this is not a clean test either way.
2. ⛔ **The band assignment is literature, not this instrument.** The KB's own 2026-08-04 warning:
   *"OUR OWN INSTRUMENT DOES NOT CONFIRM THE Qy POSITION, and cannot at this range."*
   ⚠ **And the literature does not agree with itself across phases** *(2026-08-29)*: the standard
   red-clamped fallback names pheophytin *a*'s minor bands at **535** and **608–610 nm** — free-base
   *solution* positions — against our **568** and **624**. `KB_spectroscopy_physics.md` §9.4 holds the
   reconciliation (aggregation in the lipid matrix broadens and red-shifts the long band; it is whole only
   in an index-matched solvent). ⛔ It is **not** a reason to move a window, and this spec does not move one
   — but a reader who checks the band positions against a textbook will find a 15 nm discrepancy, and it
   should not surprise them.
3. ⛔ **Consistency is not mechanism.** Two different pigments in differing proportions would produce the
   same crossover. Separating them needs the red extension or a deliberate demetallation.

⏸ **The fuller write-up is still owed** — into the *body* of `KB_spectroscopy_physics.md` (the passage is
currently buried in its sources list), `DOC_sample_physics.md`, and §5.8 — then regenerate
`Spectracs_LightPigmentSolvent.pdf` and `Spectracs_MetricAlgebra.pdf`.

### 2.4 What was rejected, and why

| form | why not |
|---|---|
| `R = A(624)/A(568)` (`SPEC_metric_research.md` §12) | no pedestal removal ⇒ 3 errors where `Rv` makes 1; and its 568 window is *not* marker (3), so it cannot reuse the plot |
| `hR = h624/h568` on **local floors** | 1 error, and the flattest across solvents (§6.2) — but its 624 floor window **604–616 contains the 609 nm Bayer crossover** (`DOC_lamp_rebuild.md` §6). A plain mean there is inflated by +0.024…+0.050 A against a band height of only 0.071…0.077 on brown oils — **up to 40 % of the measurand** — so it needs a robust statistic on an artefact-bearing window. Kept as a **dev-panel research variant**, not a shipping candidate |
| `area(624)/area(Soret)` (`diagnostics/band_width_by_solvent.py`) | ⛔ **not a quality metric at all** — 25 errors / 82 on green-vs-brown, and a 300× swing on ONE oil across solvents. It is a *solvent* discriminator and E3 built it as one. §9 restates this |
| `dQ100` | **0 errors** and still the best single discriminator — but it is a *different* proposal with its own withdrawn history (2026-08-21), it needs `sd` over 448–626 rather than band means, and it cannot be drawn on the bands plot. Orthogonal decision; not settled here |

---

## 3 · The computation

Beside the existing `V_*` constants in `DevSpectralPlugin`:

```python
RV_VALLEY_BAND = (500.0, 560.0)   # == V_VALLEY_BAND — the SAME window, marker (4)
RV_Q_BAND      = (565.0, 580.0)   # == V_Q_BAND      — the SAME window, marker (3)
RV_RED_BAND    = (622.0, 627.0)   # ⛔ NEW — the only new window. §3.1
RV_THRESHOLD   = 52.0             # ⛔ PROVISIONAL AND FITTED — §7 owns it
RV_QPCT_FLOOR  = 12.0             # §3.2 — the LOWER half of Q%'s domain band, and only the lower half
RV_VERDICT_BAND = (20.0, 130.0)   # §4.1 domain guard, must equal the gauge band
```

```python
valley = util.bandMean(despiked, *RV_VALLEY_BAND)
q      = util.bandMean(despiked, *RV_Q_BAND)
red    = util.bandMean(despiked, *RV_RED_BAND)
rv     = 100.0 * (red - valley) / (q - valley)  # denominator guarded by §3.2
```

Computed on the **de-spiked** absorbance the tab already holds (`__despikedAbsorption`, median kernel 7),
with **no baseline of any kind** — the same trace `Q%` reads, so the two cannot diverge.

⛔⛔ **THE TRAP — marker (3) is 565–580, not 560–580.** The plugin carries **both** `PB_Q_BAND = (560,580)`
and `V_Q_BAND = (565,580)`. The `Absorption (bands)` page Edwin was reading is **V's** plot, so its marker
(3) is **565–580**. `SPEC_v_metric_integration.md` §3 already warns that reusing `PB_Q_BAND` *"would render
plausibly, disagree with `box_metrics.py`, and nothing would error."* Using the wrong one here additionally
**breaks the guard proof of §3.2**, because that proof requires `Rv`'s denominator to be *exactly* `Q%`'s
numerator. Pinned by §8 T1.

### 3.1 ⭐ Why 622–627 and not Edwin's wider box — the clamp decides it

The red box drawn on the screenshot spans roughly 618–632 nm. **That window does not exist on most of the
archive.** Report wavelength maxima, deduplicated:

| `wlmax` | reports |
|---|--:|
| **629.8 nm** | 143 |
| 635.9 nm | 47 |
| 649.9 nm | 14 |
| 661.6 / 664.5 nm | 2 / 2 |

⇒ **A 620–630 window is truncated on the majority of the corpus**, and silently: `bandMean` averages
whatever samples fall inside and returns a number either way. Measured on the 95 guarded labelled runs:

| red window | errors | overlap | clamp-safe at 629.8 |
|---|--:|--:|---|
| **622–627** | **1** | **−0.107** | ✅ |
| 621–627 | 1 | −0.132 | ✅ |
| 620–628 | 2 | −0.161 | ✅ |
| 620–630 | 2 | −0.172 | ⛔ truncated on 143 reports |

**622–627 is chosen on principle first**: symmetric about 624.5, entirely inside every epoch in the
archive, and clear of the 609 nm crossover. That it also scores best is **not** the argument — see §7.2,
where window choice is named as one of the fitted degrees of freedom.

⚠ **The red flank is still cut.** Even at 635.9 nm the 624 band has not returned to baseline (0.127 /
0.075 / 0.111 A at 633 nm on the triad). `Rv` reads the peak, not the whole band. This is a **fifth
argument** for the red extension in `SPEC_lamp_rebuild.md`, alongside the four in
`SPEC_metric_research.md` §13.

### 3.2 ⭐⭐ The guards — inherited, provably sufficient, and only the LOWER half

`Rv` **adds no new denominator guard.** It needs exactly two conditions, both already computed:

1. `A_Soret ≥ 0.15` — `SPEC_v_metric_integration.md` §3.1
2. `Q% ≥ 12.0` — ⛔ **the LOWER edge of §3.1a's domain band, and only the lower edge**

**Proof.** `Rv`'s denominator is `A_Q − A_valley`, which by §2.1 equals `Q% · A_Soret / 100`. Under both
conditions it is bounded below by `12.0 × 0.15 / 100 = 0.0180 > 0`. It cannot vanish or change sign
wherever `Rv` is reported.

**Verified on the archive:** of 141 guarded report-parses, **0 have a non-positive denominator**; observed
minimum **0.0372**, twice the algebraic bound. Ungarded, 12 distinct reports do go non-positive — every
one the `cappy` non-oil samples or the `20260806A` null series with no oil in the beam, i.e. exactly what
the existing guards already withhold.

### ⛔⛔ 3.2a Why the UPPER bound must NOT be inherited — the first draft of this spec got it wrong

The first draft made `Rv` inherit the whole band, `Q% ∈ [12, 22]`, on the tidy-sounding principle
*"where `Q%` reports, `Rv` reports."* **That principle is wrong**, and a replicate fill measured at 22:32
on the evening this was written proved it:

| | `Q%` | verdict | `Rv` | verdict |
|---|--:|---|--:|---|
| `20260824SparSBudget/001` | 21.32 | brown | 31.1 | brown |
| **`20260824SparSBudget/002`** | **23.12** | ⛔ **none — outside the domain band** | **42.4** | brown ✅ |

`Q%` correctly withholds: 23.12 is past the scale it was scored on. But `Rv` reads 42.4, comfortably
inside its own corridor and on the correct side of the line — and the first draft would have **thrown
that verdict away because a metric it does not use ran off its own scale.**

⭐ **The upper bound is `Q%`'s domain concern, not `Rv`'s.** Only the lower bound enters the denominator
proof. Measured over the labelled corpus, dropping it recovers **3 runs** — and all three read correctly:

| run | `Q%` | `Rv` | reads |
|---|--:|--:|---|
| `20260821BillaCleverA/002` | 22.04 | 36.9 | brown ✅ |
| `20260727C/006` | 24.65 | 51.0 | brown ✅ |
| `20260727D/002` | 22.83 | 36.7 | brown ✅ |

Error count is **unchanged at 1** either way (§6.1), so this is not a scoring improvement — it is a
correctness fix. `Rv` is then evaluated on **98** labelled runs rather than 95.

⇒ ⭐ **`Rv` has its own domain guard** (§4.1) and does not borrow anyone else's.

---

## 4 · The gauge

A second `VerdictGaugeView` preset beside the `Q%` gauge — **not** replacing it.

```
   probably too brown  │  52  │            good — green
  bandLeft 20                                        bandRight 130
```

| | |
|---|---|
| band | **ascending, green on the RIGHT** — the mirror of the `Q%` gauge. `GaugeColorUtil` is orientation-aware, so no SDK change |
| classes | **two** at first. A third *borderline* class needs a scatter estimate `Rv` does not yet have (§6.3) — adding one now would invent its width |
| headroom | labelled corpus spans 21.9…125.8; the band clears both ends |

### 4.1 The domain guard is still needed, and is `Rv`'s own

Q%'s domain guard does **not** bound `Rv`. Over the 141 guarded report-parses `Rv` ranges **−6.6 …
294.4** — far outside the labelled corpus — because a sample may pass `Q%`'s domain and still have no
624 band at all. ⇒ `RV_VERDICT_BAND = (20.0, 130.0)`, applied with the same §3.1a semantics: **the value
and the bars stand; only the pill is withheld.** A gauge clamps past its band edge, so without this a
`Rv` of 294 would read *"good — green"* on authority it does not have.

---

## 5 · The plot — one new marker

`Absorption (bands)` gains marker **(6)**, a band bar over 622–627 at the mean of that window, in the
existing `addLevel` idiom (`SPEC_soret_448_trim.md` §12.2). Markers (1)–(5) are untouched; the legend
gains one row: `6  red band mean`.

⭐ **This is the smallest change that makes Edwin's observation visible by default.** The peak he had to
draw a box around becomes a labelled feature, and the two quantities `Rv` relates — (6) and (3), both
above (4) — are then readable straight off the page.

---

## 6 · Evidence

### 6.1 Classification, 98 guarded labelled runs (60 green / 38 brown)

| metric | green | brown | best cut | errors |
|---|---|---|--:|--:|
| **`Q%`** (shipped) | 16.04 ± 1.80 [12.73 … 20.79] | 19.99 ± 1.30 [17.14 … 24.65] | 18.19 | **9** |
| **`Rv`** | 83.6 ± 21.8 [39.5 … 125.8] | 37.7 ± 6.4 [21.9 … 51.0] | 51.0 | **1** |

At the provisional `T = 52`: **1 error**. Excluding the single failing fill (§6.4): **0 errors**,
gap **+3.1** (green min 54.1, brown max 51.0).

⚠ Effect sizes are close — `|d|` 2.60 vs 2.42. **`Rv`'s advantage is in the tails, not the means.**
`Q%`'s classes overlap across a 3.65-unit span containing 9 runs; `Rv`'s overlap is one fill wide.

### 6.2 ⭐⭐ Across solvents — the result `Q%` cannot match

Two oils, every solvent measured, guarded runs only:

| | `Rv` | `Q%` |
|---|---|---|
| **Lugitsch** (green) isopropanol, n=16 | 98.4 … 125.2 | 13.48 … 18.90 |
| white spirit, n=2 | 103.1 … 104.9 | 20.62 … 20.79 |
| sunflower (old bottle), n=2 | 114.5 … 125.2 | 16.21 … 16.66 |
| sunflower (fresh bottle), n=1 | 115.0 | 18.90 |
| **Lugitsch, all solvents** | **98.4 … 125.2** | **13.48 … 20.79** |
| **BillaClever** (brown) isopropanol, n=14 | 28.3 … 46.4 | 18.76 … 21.45 |
| white spirit, n=1 | 36.4 | 21.83 |
| sunflower (old bottle), n=1 | 34.2 | 21.45 |
| **BillaClever, all solvents** | **28.3 … 46.4** | **18.76 … 21.83** |

⇒ **`Rv` separates the two oils by a factor of 2.1 with no overlap in any solvent** (green floor 98.4,
brown ceiling 46.4). **`Q%` overlaps outright** on 18.76 … 20.79 — a brown Billa fill and a green
Lugitsch fill are indistinguishable by the shipped metric once the solvent is allowed to vary.

⚠ Not a portability *proof*: two oils, and n=1 in three of the six cells.

### 6.3 ⛔ The margin is thinner than the noise

**Pooled within-series sd of `Rv` = 5.74** across 18 repeat-fill series. The green–brown gap at its
narrowest is **3.1**. ⇒ The corpus separates, but **a single borderline fill has no safety margin.**
This is the strongest argument against giving `Rv` a verdict pill on this evidence, and it is why §4
ships two classes and no *borderline* band — the width of that band is exactly what is not yet known.

⇒ ⏸ **`σ_fill` for `Rv` is owed**, from the same T1 five-fill session `SPEC_settled_measurement.md` §35
already schedules for `Q%`. It costs nothing extra: the same fills, one more column.

### 6.4 The one failure, stated as a failure

`20270729B/002.pdf`, labelled **green**, reads `Rv = 39.5` against a best cut of 51.0.

| its five siblings | 54.1, 57.5, 63.3, 65.7, 70.2 |
|---|---|
| `dQ100` on 002 | **+26.6** vs siblings +6.7 … +14.4 — also flagged |
| `Q%` on 002 | **13.02** — the *greenest* reading in the whole archive |

Two independent 624-based metrics call that fill anomalous and `Q%` calls it exceptional. ⛔ **It is
scored as an error regardless.** Excluding it requires a reason that is not "it disagrees with the
metric" — §16.31.3a forbids exactly that move. ⏸ **P1: pull its raw frames** before it is discussed again.

### ⭐⭐ 6.5 THE SECOND LIGHT DOSE — all three oils, and `Rv`'s margin holds

⚠ **Revision note.** This section was written twice before it was right. Draft 1 read the `002` runs as
**replicate fills** — wrong: Edwin re-measured *the same already-exposed aliquots*. Draft 2 read them as a
dose experiment but had only the two brown oils and concluded `Rv` was in trouble. The **Lugitsch second
dose** (`20260824Lugitsch/002`, 22:40) completes the set and changes that conclusion.

#### What one further dose did to each oil

| | `A_Soret` | `A_valley` | `A_Q` | `A_624` | `Q%` | `Rv` |
|---|--:|--:|--:|--:|--:|--:|
| **Lugitsch** (green) | −1.0 % | **+4.9 %** | **+1.7 %** | **+0.6 %** | +0.18 | **−1.6** |
| **SparPremium** (brown) | +2.1 % | +24.9 % | +16.7 % | +20.9 % | +1.71 | +1.4 |
| **SparSBudget** (brown) | +3.3 % | **+33.3 %** | +20.6 % | **+39.4 %** | +1.80 | +11.3 |

⭐⭐ **The green oil barely moves; the brown oils move 17–39 %.** Lugitsch's bands shift 0.6–4.9 % where
the browns shift by an order of magnitude more. Whatever the beam is doing to these samples, it is doing
it **far more to the brown oils**.

#### ⭐⭐ g4: the green/brown margin survives — and `Rv` gets the order right twice

| | run 001 | run 002 | margin 001 | margin 002 |
|---|---|---|--:|--:|
| **`Rv`** — Lugitsch vs nearest brown | 115.0 vs 44.0 | 113.4 vs 45.5 | **+71.0** | **+67.9** |
| **`Q%`** — Lugitsch vs nearest brown | 18.90 vs 18.19 | 19.08 vs 19.90 | ⛔ **−0.71** | +0.81 |

**`Rv`'s green/brown margin falls only 4.4 %** and stays an order of magnitude clear of the §6.3 scatter.
⇒ ⭐ **g4 passes.** Draft 2's worry — that exposure erodes what `Rv` is actually for — is **not** borne out.

Full ordering, against Edwin's bench ranking *Lugitsch ≫ SparPremium ≳ SparSBudget*:

| run | `Rv` | `Q%` |
|---|---|---|
| **001** | Lug 115.0 > Prem 44.0 > SBud 31.1 ✅ | Prem 18.19 < Lug 18.90 < SBud 21.32 ⛔ |
| **002** | Lug 113.4 > Prem 45.5 > SBud 42.4 ✅ | Lug 19.08 < Prem 19.90 < SBud 23.12 ✅ |

⇒ **`Rv` is right in both runs. `Q%` is wrong in 001 and right in 002** — and it is right in 002 only
because the *brown* oils degraded past Lugitsch. `Q%` did not measure better; the sample moved under it.
⛔ A metric that reaches the right answer because the sample spoiled has not earned the verdict.

#### ⛔ What still stands from draft 2

`Rv`'s **between-brown** gap still collapses **77 %** (12.9 → 3.0) while `Q%`'s holds (3.13 → 3.23):
SparSBudget's 624 band rises +39.4 % against SparPremium's +20.9 %, so the two browns converge. ⇒ **`Rv`
must not be used to rank two brown oils against each other on exposed samples.** That is outside §2's
claim, and §9 now says so.

⚠ The false-pass concern is **narrowed, not withdrawn**: the browns drift toward green (+1.4, +11.3)
while the green drifts slightly toward brown (−1.6), so the margin closes from both sides — but by
3.1 against a margin of 71.0.

#### ⛔⛔ The confound this cannot resolve

**Lugitsch had ~2.4× the beam time in run 001**: `SETTLED_AFTER_CLEARING`, 257 s of clearing over 16 rows,
against ~105 s and 7 rows for both Spars. Its `002` then came back `SETTLED_IMMEDIATE`. So two readings
fit equally well:

| | |
|---|---|
| **(a) green oil is photostable** | the pigment that makes it green resists the beam |
| **(b) Lugitsch had already saturated** | it absorbed its change during the longer 001 run, and 002 shows the flat tail |

⇒ ⏸ **g4′ — the discriminating run**: dose a **fresh** Lugitsch aliquot with a *matched* beam time to the
Spars (~105 s), then re-dose. If it then moves 17–39 % like the browns, (b) is right and §6.5's headline
is an artefact of unequal exposure. **Cheap, one evening, and it decides whether "green oil is
photostable" is a finding or a coincidence.**

### ⭐⭐⭐ 6.6 THE FRESH POUR — dilution-invariance demonstrated at 40 %, and §6.5's mechanism identified

At 23:13–23:21 Edwin poured the **remaining ~4 ml** of each prepared sample into a clean tube and measured
again (`003`). That stock had stood the same ~2.5 h **but never entered the beam** — which separates
standing time from beam dose, and turned out to answer §6.5's open mechanism outright.

#### ⛔⛔ The remaining 4 ml is FAR more concentrated — the prep is not homogeneous

| `003` vs `001` | `A_Soret` | `A_valley` | `A_Q` | `A_624` |
|---|--:|--:|--:|--:|
| Lugitsch | **+39.5 %** | +50.1 % | +42.3 % | +41.5 % |
| SparPremium | **+45.5 %** | +88.7 % | +60.0 % | +70.3 % |
| SparSBudget | +15.2 % | +1.2 % | +14.2 % | +16.1 % |

The second half of the same prepared sample carries up to **45 % more absorber** than the first half.
⇒ **The pigment-rich material settles in the mixing vessel**: the first pour takes the leaner top, the
remainder is the richer bottom.

⛔ **This challenges `SPEC_capture_quality.md` §16.12.7g's "the oil dissolves — a true solution"**, which
rests on the refractive-index match (n 1.473 vs 1.47). A true solution does not stratify in two hours.
⚠ It does not refute the index match; it says the *preparation* is not homogeneous, whatever the optics.
⇒ ⏸ **Mix immediately before pouring, and record whether the pour is first or second half.**

#### ⭐⭐ It also identifies §6.5's mechanism — settling, not photochemistry

§6.5 offered "more oil in the beam" against "photo-browning" and could not choose. The fresh pour chooses:
the same stratification that makes the *remainder* richer will, inside a standing tube, enrich the
**beam region** over 96 minutes. That is §6.5's near-uniform scaling (`k` = 1.02 / 1.18 / 1.26), and it is
the hypothesis §6.5 ranked first.

⇒ ⭐ **Photo-browning is now doubly disfavoured**, and "green oil is photostable" (§6.5's confound (a))
loses its footing: Lugitsch changed least between 001 and 002 because it is the **best-dissolved** — the
oil sunflower's index match serves best — not because its pigment resists light. **The finding is about
the preparation, not the pigment.** ⏸ g4′ still worth running, but its likely answer is now (b).

#### ⭐⭐⭐ And this is the strongest dilution-invariance evidence in the corpus

A ~40 % dose change is exactly what a dilution-invariant metric must absorb:

| | `A_Soret` change | `Q%` change | `Rv` change |
|---|--:|--:|--:|
| Lugitsch | **+39.5 %** | −0.20 | **−0.5** |
| SparPremium | **+45.5 %** | −0.39 | **+0.7** |
| SparSBudget | +15.2 % | +1.45 | +6.5 |

⭐ On the two well-behaved oils, a **40–45 % dose swing moves `Rv` by under 0.8 %**. §2's
scale-invariance is no longer only algebraic — it is measured, on samples that did not exist when the
metric was defined.

#### ⭐⭐ Order across all three rounds — `Rv` 3/3, `Q%` 1/3

| round | `Rv` | `Q%` |
|---|---|---|
| **001** first pour | Lug 115.0 > Prem 44.0 > SBud 31.1 ✅ | Prem 18.19 < Lug 18.90 < SBud 21.32 ⛔ |
| **002** same tube, +96 min | Lug 113.4 > Prem 45.5 > SBud 42.4 ✅ | Lug 19.08 < Prem 19.90 < SBud 23.12 ✅ |
| **003** fresh pour, 2nd half | Lug 114.5 > Prem 44.7 > SBud 37.6 ✅ | **Prem 17.80 < Lug 18.70** < SBud 22.77 ⛔ |

⛔ **`Q%` inverts Lugitsch and SparPremium in BOTH pours of fresh sample**, and is right only in `002` —
the round where the brown oils had degraded past Lugitsch. ⭐ `Rv` is right in all three.

Per-oil spread over the nine runs:

| | `Rv` spread | `Q%` spread |
|---|--:|--:|
| Lugitsch | **1.6** | 0.38 |
| SparPremium | **1.4** | **2.10** |
| SparSBudget | 11.3 | 1.80 |

`Q%`'s 2.10-unit spread on one oil across one evening exceeds any green/brown margin it offers.
`Rv`'s worst spread is 11.3, ~16 % of its 71-unit margin.

⚠ **SparSBudget is the exception in every panel here** — the smallest concentration step, the only
non-monotone `Rv`, the only `003` to show a clearing transient (`SETTLED_AFTER_CLEARING`, 210 s / 13 rows
against ~108 s / 7 for the others). Something about that fill behaves differently and this spec does not
explain it. ⏸ It is the first candidate for a repeat.

### ⛔⛔⛔ 6.7 THE DIFFUSER TEST HAS ALREADY RUN — AND `Rv` FAILS IT

`20260727B` is the archive's diffuser A/B (`SPEC_capture_quality.md` §16.7.2f): the paper diffuser was
**IN** for runs 001–003 and 008–009 and came **OUT** for 004–007. **All nine are the same green oil.**
`Rv` must read green, or refuse.

| run | diffuser | `A_Soret` | `Q%` | `Rv` | guard | `Rv` verdict |
|---|---|--:|--:|--:|---|---|
| 001 | IN | 0.663 | 17.10 | 54.6 | passes | green |
| **002** | **IN** | 0.678 | 16.35 | **50.3** | **passes** | ⛔ **BROWN — WRONG** |
| 003 | IN | 0.591 | 15.88 | 65.0 | passes | green |
| 004 | OUT | 0.726 | 15.60 | 66.5 | passes | green |
| 005 | OUT | 0.698 | 16.07 | 71.1 | passes | green |
| 006 | OUT | 0.694 | 17.08 | 73.5 | passes | green |
| 007 | OUT | 0.759 | 14.56 | 73.7 | passes | green |
| **008** | **IN** | 0.688 | 16.86 | **50.9** | **passes** | ⛔ **BROWN — WRONG** |
| 009 | IN | 0.589 | 16.37 | 53.9 | passes | green |

- diffuser **OUT**: `Rv` = 66.5 … 73.7, spread **7.2**, all comfortably green.
- diffuser **IN**: `Rv` = 50.3 … 65.0, straddling the line — **2 of 5 read brown**.
- ⛔⛔ **Both guards pass on every one of the nine.** `A_Soret` ≥ 0.15 ✅, `Q%` ≥ 12 ✅, `Rv` inside
  (20, 130) ✅. **§3.2 and §4.1 do not catch this.** The number simply comes out wrong and looks fine.
- ⭐ **`Q%` is untouched**: 15.6 … 17.1 with the diffuser IN, 14.6 … 17.1 with it OUT. The shipped metric
  shrugs off an optical change that moves `Rv` by 20 units.

⛔ **And the headline 1/98 does not see this**, because `peak_ratio_archive.DIFFUSER_IN` excludes those
five runs as an instrument fault — an exclusion that **predates `Rv`** and is not special pleading, but it
does mean **§6.1's corpus has the known `Rv`-breaking condition removed from it.** Stated plainly here so
the two numbers are never quoted without each other.

#### ⛔ The obvious mitigation does not work

A band-presence guard — refuse when the 624 feature has no height above its local 612–615 → 627–630 chord —
looked like the fix. It is not:

| | chord height |
|---|---|
| diffuser IN (n=5) | 0.0000 (band gone) |
| diffuser OUT (n=4) | 0.0046 … 0.0218 |
| `20260812_BillaClever/001` — a **normal brown** run | **0.0000** |
| `20280819BillaClever/001` — a **normal brown** run | **0.0000** |
| `20260817LigitschA/001` — a **normal green** run | 0.0098 |

⇒ **A washed-out band and a genuinely weak band are the same measurement.** Any threshold that refuses the
diffuser also refuses most brown isopropanol runs — which are exactly the runs `Rv` exists to classify.
There is no cheap algorithmic guard here.

⇒ ⭐ **The mitigation is procedural, not algorithmic**: the optical path must be fixed and recorded, and
**`Rv` must be re-validated after ANY optical change** — the lamp rebuild included. `SPEC_lamp_rebuild.md`
should carry this as a blocker.

---

## 7 · ⛔⛔ THE GATE — pre-registration, and it blocks everything above

**Nothing in §1–§6 may be quoted as a validated result.** Every number above is measured on the corpus
that the metric's form was chosen against.

### 7.1 What `Rv` inherits from `dQ100`'s refusal

`SPEC_capture_quality.md` §16.31.3a refused `dQ100` because its constants were fitted on its own corpus
and its headline rested on the **Spar Premium relabel**. `Rv` is in the *same* position, with one
difference in its favour and one against:

| | |
|---|---|
| ⭐ **in favour** | the 2026-08-24 triad fixes SparPremium's class **by eye at the bench** — a label no metric could have contaminated, and the first such label for that oil. Under it `Rv` is right and `Q%` is wrong |
| ⛔ **against** | n = 1 fill per oil in that triad, and `Rv`'s *form* was still chosen post-hoc on the archive |

### 7.2 The fitted degrees of freedom — declare them or the test is worthless

1. **the red window** — 4 candidates compared on the scored corpus (§3.1);
2. **the threshold 52** — the midpoint of a gap measured on the scored corpus;
3. **the pedestal subtraction** — chosen *because* it beat the raw form 4 → 1 (§2.2);
4. **the domain band (20, 130)** — drawn around the observed corpus range.

### 7.3 The held-out test

⭐ **Freeze §3's constants in this document, then measure fills that did not exist when it was written.**

| | |
|---|---|
| **pre-registered claim** | `Rv > 52` classifies green vs brown with ≤ 1 error |
| **held-out set** | ≥ 12 fills: ≥ 3 oils × ≥ 2 fills × ≥ 2 solvents, labelled **by eye before the number is read** |
| **must include** | the **brown arm in the fresh bottle** — BillaClever has no fresh-sunflower fill, so §6.2's bottle result rests on one oil |
| **fails if** | > 1 error, or the threshold has to move to hold |
| ✅ **g4 — the dose arm** | ✅ **RAN 2026-08-24 (§6.5) and PASSED**: `Rv`'s green/brown margin falls only 4.4 % (71.0 → 67.9) under a second dose and the 3-oil order is correct in both runs. ⏸ **g4′ still owed** — a matched-beam-time Lugitsch dose, to separate "green oil is photostable" from "Lugitsch had already saturated" (§6.5) |

⛔ **Until §7.3 reports, `Rv` ships as a number and `Q%` keeps the verdict.** That is not caution for its
own sake — it is the identical bar `dQ100` was held to, and applying it unevenly would make the standard
meaningless.

---

## 8 · Tests

| id | test |
|---|---|
| **T1** | `RV_Q_BAND == V_Q_BAND` and `RV_VALLEY_BAND == V_VALLEY_BAND`, asserted on the constants — the §3 trap |
| **T2** | the guard proof: sweeping a synthetic spectrum across `A_Soret` and `Q%`, the denominator is `> 0.018` whenever `A_Soret ≥ 0.15` **and** `Q% ≥ 12` — and ⛔ a run with `Q% > 22` still yields an `Rv` verdict (§3.2a) |
| **T3** | direction: a spectrum with a larger 624 band yields a **higher** `Rv` and a **greener** verdict — §2.3 |
| **T4** | domain guard: `Rv = 294` renders the value and the bars but **no pill** |
| **T5** | clamp: a trace truncated at 629.8 nm yields the **same** `Rv` as the identical trace extended to 635.9 — proves 622–627 is epoch-independent |
| **T6** | golden values: the 2026-08-24 first pour reproduces 115.0 / 44.0 / 31.1 to 1 decimal |
| **T7** | `diagnostics/` and the plugin agree to 1e-9 on the whole archive — the `box_metrics.py` reconciliation, extended |
| **T8** | `walkReports()` yields **no path containing `/oldPdfs/`**, and its count equals `find <archive> -name "*.pdf" -not -path "*/oldPdfs/*" | wc -l` — pins §11.1 so the bug cannot return |

---

## 9 · What is NOT claimed

- ⛔ **Not that `Rv` beats `dQ100`.** `dQ100` makes **0** errors on the same 95 runs. `Rv`'s case is that it
  is drawable on the existing plot, computable from existing band means, and guard-compatible — **not**
  that it classifies better.
- ⛔ **Not that `Rv` is solvent-portable.** §6.2 is two oils, three solvents, several cells at n=1.
- ⛔ **Not that the 624 band is understood.** `SPEC_capture_quality.md` §16.12.7g records the mechanism as
  an *argument, not a measurement*, and `SPEC_color_retrieval.md` §7.16.4a establishes only the negative half.
- ⛔ **Not that `area(624)/area(Soret)` is related.** It is a solvent discriminator: 25 errors / 82 on
  green-vs-brown. It must never be promoted to a quality metric.
- ⛔ **Not a ranking between two BROWN oils on exposed samples.** §6.5: `Rv`'s between-brown gap collapses
  77 % under one further dose while `Q%`'s holds. `Rv` is a green/brown discriminator, and that is all.
- ⛔⛔ **NOT robust to a diffuser — measured, not feared (§6.7).** On the archive's own diffuser A/B,
  2 of 5 blurred runs of a GREEN oil read brown, **both guards passing**. `Q%` is unaffected. No cheap
  guard exists, because a washed-out band and a weak band are indistinguishable. ⇒ `Rv` must be
  re-validated after any optical change, and this is a **blocker on `SPEC_lamp_rebuild.md`**.

---

## 10 · Build order

| phase | what | gate |
|---|---|---|
| **P0** | ✅ **DONE** — `sorted(os.walk(...))` fixed via `peak_ratio_archive.walkReports()`, all four walkers migrated, §16.12.7g re-run and `n = 72` confirmed (§11.1). ⏸ still owed: promote the scratchpad scripts to `diagnostics/red_ratio_archive.py` and add T8 | — |
| **P1** | pull the raw frames of `20270729B/002` (§6.4) | — |
| **P2** | `Rv` + the two metric rows + marker (6), **no gauge** | P0 |
| **P3** | record the finding in `SPEC_metric_research.md` §12 as `R`'s valley-referenced sibling | P2 |
| **P4** | `σ_fill` for `Rv` from the T1 five-fill session (§6.3) | lab |
| **P5** | ⛔ **the §7.3 held-out set**, incl. the fresh-bottle brown arm | lab |
| **P6** | the gauge + `RV_THRESHOLD`, **only if P5 passes** | P4, P5 |

⇒ **P2 is the only phase that touches shipping code before a lab session**, and it moves no verdict.

---

## 11 · Open questions

1. ✅ **RESOLVED 2026-08-24 — the walk bug is fixed and `n = 72` is CONFIRMED UNCHANGED.**
   `sorted(os.walk(root))` consumes the generator before the loop body runs, so the in-place
   `subfolders[:]` prune could not affect traversal: **415 PDFs were walked where 210 exist**, 205 of them
   `oldPdfs/` duplicates. Fixed by `peak_ratio_archive.walkReports()`, now used by all four walkers
   (`peak_ratio_archive`, `band_width_by_solvent`, `solvent_colour_separation`,
   `dominant_wavelength_archive` — the last never pruned at all).
   ⭐ **No published number moves.** Every leaked copy sits under a `oldPdfs/...` series, and `classOf`
   returns `None` for those, so **0 of the 205 duplicates were ever labelled green/brown**: every
   label-filtered statistic was already correct. Re-running the fixed `band_width_by_solvent.py` reproduces
   §16.12.7g exactly — **isopropanol n = 72**, index-matched n = 7, per-fill areas identical.
   ⚠ The two *unfiltered* scripts were the real exposure: `peak_ratio_archive.collect()` and
   `dominant_wavelength_archive` would have doubled on their next run. `collect()` now returns **208 rows,
   0 from `oldPdfs/`**, a superset of the 196-row CSV on disk (the 12 extra are genuinely new reports —
   the 0822 sunflower, 0823 newchips and 0824 triad). **The CSVs on disk were never contaminated**; they
   predate `oldPdfs/`. They are stale, not wrong — regenerating them is a separate call.

2. ⏸⭐⭐ **OWED AND ESSENTIAL — the PHYSICAL argument is not written down here yet.** Edwin, 2026-08-25:
   the Gouterman four-orbital account and `Rv` are **congruent**, and that must reach the specs and the
   regenerated PDFs. In one line: demetallation D₄ₕ→D₂ₕ (protochlorophyll → protopheophytin) makes the
   longest-wavelength Q band — **band I, our 624 nm** — the *weakest of four*, so `Rv` is a **symmetry
   diagnostic**, not a curve-fit; and `Q%`'s Soret denominator is carotenoid-contaminated
   (`DOC_lamp_410_680.md` Fig. 5), i.e. it ratios a porphyrin band against a different pigment family,
   while `Rv` stays inside one chromophore's Q manifold. `Rv` is also the **ratio form of
   `DOC_metric_algebra.md` §5.8's see-saw** (`dQ100` being the difference form).
   ⇒ lands in **§2.5 here**, the **body** of `KB_spectroscopy_physics.md` (the passage is currently buried
   in its sources list), `DOC_sample_physics.md`, and §5.8 — then regenerate
   `Spectracs_LightPigmentSolvent.pdf` and `Spectracs_MetricAlgebra.pdf`.
   ⚠ Three caveats must travel with it: Q-manifold conservation is **untested, not shown**; the band
   assignment is literature, not this instrument (the KB's own 2026-08-04 warning); and the same crossover
   could come from **two pigments in differing proportions** rather than one changing symmetry.
   **Full working note: memory `spectracs-rv-gouterman-owed`.**
3. **The name.** `Rv` signals kinship with §12's `R` and states the difference (valley-referenced). `E`
   collides with the E3 experiment. Edwin's call.
4. **Two classes or three?** §4 says two until §6.3's scatter is measured. Confirm.
5. **Does `Rv` supersede `R`** in `SPEC_metric_research.md` §12, or sit beside it? They differ only by the
   pedestal, and `Rv` is strictly better on this corpus (1 error vs 3).
6. **Is the solvent recorded anywhere?** It is not — the `METADATA` phase is empty and `pluginVersion` is
   `None` in every archived report. §6.2 could only be assembled because Edwin remembered. **This should
   be fixed before any further solvent work**, independently of `Rv`.


---

## ⭐⭐⭐ 12 · THE 2026-08-26/27 SESSION — the eye order is reproduced, and σ_fill is the blocker

Eight fills across three oils in sunflower, under the new lab recipe, **first two DISTINCT reads of each
aliquot** (later reads are a dose series, not repeats: Stekko's four runs span 14.8 `Rv`, its first two
span 0.9). Esterer and Stekko were held **unlabelled** through the whole session so their class could not
be taken from the metric being judged on them; Edwin's eye-ranking arrived afterwards.

### 12.1 ⭐⭐ `Rv` reproduces the eye order. `Q%` inverts it.

> **EYE, 2026-08-27:** Lugitsch greenest · Esterer and Stekko a little browner · **all three GREEN.**

| oil (sunflower) | `Rv` mean | `Q%` mean |
|---|---|---|
| Lugitsch | **109** | 17.26 |
| Esterer | **92** | **14.45** |
| Stekko | **74** | 17.51 |

`Rv` gives Lugitsch > Esterer > Stekko — the eye's order. `Q%`, where *lower* is greener, makes **Esterer
the greenest of the three**. ⭐ This is the sharper form of §6's Spar Premium inversion: there the oils
straddled green and brown, here **all three are green** and `Q%` still gets the ordering wrong.
Green-vs-brown is not the discriminating test any more — the order *within* green is.

⚠ Adding six eye-labelled green runs left the archive at **1 error in 116 at T = 52**, unchanged.

### 12.2 ⛔⛔ AND THE FILL, NOT THE OIL, IS NOW THE DOMINANT TERM

```
WITHIN a fill, Rv repeats to        sd 1.36           the measurement is fine
BETWEEN fills of ONE oil             8.4 Rv  Lugitsch, 3 fills,  sigma_fill  4.37
                                    30.0 Rv  Esterer,  3 fills,  sigma_fill 15.03
```
⭐ **Both rows are CONFIRMED fills only.** A fourth Esterer fill whose attribution was changed at the
bench is excluded from every statistic in this section (§12.4); it sits inside the range above and
changes nothing.

**Esterer's best fill (107.4) is indistinguishable from Lugitsch's best (107.2)**, while its worst reads
77.5. Four fills, each internally repeatable to a few units, disagreeing with each other by thirty. ⇒ the
oil *means* still order correctly, but **a single fill can no longer identify the oil** — and a verdict is
read off one fill.

⛔ **Nothing else in this spec can be judged until σ_fill exists.** Not §7's M9 error count, not the
08-24 → 08-26 session step (12.8 `Rv`, the size of one evening's fill spread), not a tracker tolerance.
⇒ **ROADMAP item 0**: six fills of ONE oil, one evening, one bottle, nothing else varied.

⛔⛔ **THE OVERLAP RESTS ON CONFIRMED LABELS AND IS NOT A LABELLING ARTEFACT.** Esterer's highest fill
(107.4) and Lugitsch's highest (107.2) are both operator-confirmed, made three and seven hours apart. The
one fill whose attribution was changed sits *inside* the range and is excluded from these numbers anyway.
⇒ a single fill cannot identify the oil, and that conclusion does not depend on any disputed label.

⚠ **What is still open is the CAUSE, not the observation.** A preparation that genuinely varies by 30 `Rv`
and a bench drifting through a nine-hour evening produce the same table. ⇒ ROADMAP item 0 measures it
rested, in one sitting, with nothing else varied.

### 12.4 ⚠ The one fill with an uncertain label

`20260826EstererC` was measured as `LugitschD`, read `Rv` 86.2 — below Esterer's second fill — and so
produced the first Lugitsch/Esterer overlap in the archive. It was then reassigned to Esterer.
⛔ **It is plotted and named but scores NOTHING** (`PROVISIONAL_ATTRIBUTION` in `d2r_all_runs.py`), because
letting it score would remove the overlap it created — the metric used to fix the label the metric is
then judged on, which is §7's M9 circularity arriving from a new direction. It may inform nothing until
an independent Esterer fill confirms the reassignment at the bench.
⚠ **No other fill of the session is in doubt.** In particular `20260826EstererD` is operator-confirmed;
its surprising value is a measurement, not a suspicion.

### 12.5 A check on the whole story — the scatter is not Rv's windows

Divide each spectrum by its own `A_Soret` (concentration out) and ask how far the fills of ONE oil differ
at each wavelength. They differ **everywhere in the visible**, smallest in the blue-green and growing
steadily to the red: Esterer's spread is 0.026 at 480 nm, 0.066 at 560, 0.116 at 610, 0.133 at 632 —
a factor of five across the range. Lugitsch shows the same shape at about two-thirds the size.

⇒ **not a 624-band effect and not a flat offset.** A flat offset would indicate path length or seating;
a spike at 624 would indicate the pheophytin band alone. A smooth red-weighted divergence is neither — it
is the balance of the whole absorber population moving, which is what incomplete dissolution in an
index-matched solvent would do.

⭐ Confirmed on a quantity sharing nothing with `Rv`: a broad **R/G** ratio (500–585 against 590–636, no
valley datum, ratio of transmitted light rather than of corrected absorbances). Fill-to-fill spread
**0.106** against an oil-to-oil difference of **0.005** — twenty to one, and the ranges overlap.
⇒ ⛔ **no choice of window removes this, and no optical check at dilution — eye or camera — can identify
a fill.** The eye's threshold at dilution sits between ~28 `Rv` (three oils, indistinguishable) and
~70 `Rv` (Lugitsch against the Spars, plainly different in the 2026-08-24 photographs).

### 12.6 ⭐⭐ `20260822Lugitsch/002` — the cleanest fill on record, and what it says about the preparation

The highest `Rv` in the whole sunflower archive is **125.16**, and its `A_valley` is **0.0181** — five
times lower than any other fill. ⛔ It is not an artefact and it should NOT be excluded.

| | 002 | 003 (its sibling) | 20260824Lugitsch/001 |
|---|---|---|---|
| `A_Soret` | 0.5963 | 1.4048 | 0.8124 |
| `A_valley` | **0.0181** | 0.1292 | 0.0840 |
| **`valley / A_Soret`** | **0.0303** | 0.0920 | 0.1034 |
| `A624 / A_Q` *(no valley at all)* | **1.2120** | 1.0933 | 1.0970 |
| `Rv` | **125.16** | 114.47 | 115.01 |

⭐ **Two things stack, and only the second is interesting.** It is the most dilute fill *and* it carries
**three times less turbidity per unit oil**. Dilution alone leaves `valley/A_Soret` unchanged, so the
second is a real difference in the sample, not in how much of it there is.

⭐⭐ **ITS OWN SIBLING PROVES IT.** Regressing run 003 against run 002 across 490–630 nm:

```
A003 = 2.304 * A002 + 0.0885        residual sd 0.019 on a range of 0.311
```

**The same spectrum, scaled by 2.3, plus a constant.** A pure concentration difference gives a scale
factor and nothing else; the additive pedestal of 0.0885 is the signature of **broadband scatter**. 003
carries ~0.09 of it and 002 does not — `A_valley` measuring exactly what it exists to measure.

⚠ **The reading is real but fragile.** `A624/A_Q` is 1.212 against 1.093 for both comparison runs, so the
raw band ratio — which touches no valley — agrees that 002 is different. But with numerator and
denominator of 0.121 and 0.096, `Rv` is then very sensitive to small errors in a valley of 0.018.
Sanity checks pass: no negative absorbance anywhere in 500–560 (min +0.0050), coverage 410–636 nm.

⇒ ⭐⭐ **KEEP IT, AND READ IT AS EVIDENCE ABOUT THE PREPARATION.** It will inflate Lugitsch's σ_fill for a
reason that is not measurement error: a better-dissolved fill reads higher `Rv`. That is the same axis as
the 2026-08-26 recipe change (shake → 40 inversions), observed four days *earlier* and by accident.
⛔ Excluding it as an outlier would delete the archive's one clean data point on the very effect ROADMAP
item 0 exists to measure.

### ⛔ 12.7 `Rv − Q%′` — "use `A_Soret` as well", tested and SHELVED

**Edwin's question, 2026-08-27:** `Rv` weighs `A624` against `A_Q` and never looks at the Soret — should
`A_Soret` come in as well? **Answer: it can, in exactly one form, and it does not change the problem.**
Recorded here so the algebra is not re-derived and the sweep is not re-run.

**The obvious version is a trap.** Putting the Soret in as the *reference* — `Rv_S = (R−V)/(S−V)` —
cuts fill variance impressively and destroys the metric, because it shrinks the oil gap faster than the
noise. The Soret is carotenoid-contaminated (§2.5), so anchoring there mixes pigment families:

| candidate (08-26 fills) | σ_fill | oil gap | **gap/σ** | errors | Cohen's *d* |
|---|---|---|---|---|---|
| **`Rv`** — Q reference, shipped | 11.07 | 10.62 | 0.96 | **1** | 2.76 |
| `Rv_S` — Soret as reference | **4.16** | 1.47 | 0.35 | 11 | 1.84 |
| `hR = R/Q` — no valley datum | 5.64 | 5.13 | 0.91 | 5 | 2.54 |
| **`Rv − Q%′`** — Soret as a *correction* | 9.31 | **10.93** | **1.17** | **1** | **3.02** |

⭐ The one form that helps subtracts rather than divides — the archive's own rule, *differences survive,
ratios don't*:

```
Rv'' = 100 · [ (R − V)/(Q − V)  −  (Q − V)/(S − V) ]
                ^^^^^^^^^^^^^      ^^^^^^^^^^^^^^^
                this IS Rv          this IS Q%, valley-corrected
```

`Rv` and `Q%` correlate at **r = −0.64** over the archive — two readings of one axis — so the difference
cancels the common mode and keeps what they disagree about.

**On the full sunflower corpus, scale-free.** ⚠ `Rv'' = 1.077·Rv − 25.70` (r = 0.9954), a *wider* scale
than `Rv`, so no raw spread may be compared between them. Divided by each metric's own green-to-brown
distance:

| | `Rv` | `Rv − Q%′` |
|---|---|---|
| σ_fill ÷ own gap | 0.249 | **0.199** |
| Cohen's *d*, 116 scored runs | 3.10 | **3.40** |
| errors | 1 | 1 |
| **day-to-day drift of the one repeated oil ÷ own gap** | 0.36 | **0.35** |
| Esterer vs Lugitsch, single fills inside 08-26 | overlap | **overlap** |

⛔⛔ **THE VERDICT — Edwin, 2026-08-27: "does not change the problem."** The pooled σ_fill gain is real
(≈20 % scale-free) and it buys **nothing on either thing that actually blocks the programme**. The one
oil measured on all three days drifts by the same fraction of the gap; inside a single day Esterer's best
fill still cannot be told from Lugitsch's worst. A correction term cannot repair a preparation that
delivers different amounts of the absorber being measured — **fills B and D differ by 9 % in `A624` with
`A_Q` identical to 0.03 %**, and no Soret term touches that.

⛔ **And the method is the same one that already failed once.** Six algebraic forms, chosen by me, scored
on the corpus they would be quoted against — the identical setup that made the blue-flank reference look
excellent on 115 runs before it failed on the first new sample (§12.3). Any adoption is an §7/M9 event.

⚠ **State the corpus with the number.** The table above is the full sunflower archive; the 08-26 fills
alone give σ_fill 11.07 → 9.31 for the same two metrics. Both are correct and they are not the same
claim — a σ_fill quoted without its fill set means nothing.

⛔ **It also costs `Rv`'s best property.** On the `Rv`-native plot the 624 band's height *is* `Rv`
(§5); a difference of two ratios cannot be drawn.

⇒ **Rendered, not adopted:** pages 8 and 9 of `20260825_d2r_all_runs.pdf`
(`diagnostics/d2r_all_runs.py`, `pageDifferenceMetric` + the parameterised `pageByDay`). If it is ever
revisited, the corpus is the **σ_fill run** (ROADMAP item 0), which has a proper fill-variance
denominator instead of eight fills across two oils.

### ⭐⭐ 12.8 THE 2026-08-27 FILLS — the lamp is bounded, `EstererD` is decomposed, and a mechanism is refuted

Five fills after midnight (`LugitschC`, `EstererB`, `EstererC`, `EstererD`, `EstererE`), ten reads.

#### 12.8.1 ⭐⭐ The lamp is worth ~2 `Rv`. Measured, not argued.

The evening carried exactly **two** reference spectra (md5 over all 1634 points; ref 1 before 17:21, ref 2 at
~00:26). Because both `SAMPLE` and `REFERENCE` legs are stored, every fill can be recomputed against the
*other* reference — a direct measurement of the whole evening's lamp tilt:

| fill | time | `Rv` own ref | `Rv` other ref | shift |
|---|---|---|---|---|
| Esterer | 17:21 | 77.3 | 76.3 | −1.0 |
| Stekko | 18:01 | 73.4 | 70.1 | −3.2 |
| Lugitsch | 18:36 | 100.1 | 102.2 | +2.0 |
| LugitschB | 22:15 | 100.5 | 102.3 | +1.8 |
| LugitschC | 00:27 | 107.0 | 105.1 | −1.8 |
| EstererB | 00:57 | 90.0 | 89.7 | −0.3 |
| EstererD | 02:17 | 107.3 | 105.6 | −1.7 |

⇒ **~2 `Rv`, against a 30 `Rv` Esterer trend across the same hours.** A flat dimming cancels exactly in `Rv`
(numerator and denominator are both valley-differences), so only the *tilt* survives, and the tilt is small.
⭐ **One reference per fill is still right** (`ROADMAP.md` §0a) — but it will not fix σ_fill, and this is the
number that says so.

#### 12.8.2 ⭐⭐ `EstererD` is a smooth spectral tilt, NOT a 624-band event

Fill means, `A_D / A_B` across 440–636, straight line removed, residual in units of its own sd:

```
   Soret   +1.6 sd        raw:  A_Soret  -12.4 %
   valley  -0.8 sd              A_valley -15.7 %
   A_Q     +0.2 sd              A_Q       +0.04 %   <- the two curves cross here
   A624    +0.0 sd              A624      +9.06 %
```

**Zero at 624.** The ratio climbs monotonically 0.78 → 1.15 from 480 to 630 nm with no structure where `Rv`
looks. ⇒ `Rv` did not misfire on a band artefact; it reported a sample whose red-to-Q balance really differed.
Regressed the §12.6 way over 490–631: `A_D = 1.150·A_B − 0.0412` — more absorber **and** 0.041 less scatter
pedestal.

#### 12.8.3 ⛔⛔ THE DISSOLUTION EXPLANATION WAS PROPOSED AND THEN REFUTED THE SAME NIGHT

§12.8.2 invited the obvious reading: D read 107 because it was better dissolved. `EstererE` tested it. E was
made by a **two-stage recipe** — 1 ml sunflower + the capillary, which empties itself, ~45 s of fast rotation
at the bottom while still concentrated, then to 4 ml and ~60 s more; **no arm-swing, no slow inversions**.

| fill means | B (old) | E (two-stage) | |
|---|---|---|---|
| `A_Soret` | 1.0508 | 1.1577 | **+10.2 %** |
| `A_valley` | 0.1714 | 0.1597 | **−6.9 %** |
| `A_Q` | 0.3173 | 0.3170 | −0.09 % |
| `A624` | 0.3027 | 0.2985 | −1.4 % |
| **`Rv`** | **90.0** | **88.3** | **−1.7** |

⭐ **The recipe demonstrably works** — less scatter *and* more pigment in solution, and the Soret rise is
confined to the band itself rather than the broad blue shoulder, so it is carotenoid dissolving, not turbidity.
⛔ **And `Rv` moved 1.7, one run's noise.** A genuine dissolution improvement does not raise `Rv` by 17. ⇒ the
dissolution story for D is **dead**, and the blue-shoulder scatter proxy that carried it is not fit either
(`r = −0.90` across Esterer's four fills, `+0.65` across Lugitsch's three).

⭐⭐ **What survives is better than the hypothesis.** `Rv` held still while the spectrum around it moved 10 %
in the blue — preparation-invariance demonstrated on a change nobody designed as a test. And **B and E differ
by 1.73 while the two runs inside E differ by 2.86**: the first two independent fills in the sunflower archive
that cannot be told apart.

#### 12.8.4 `EstererD` set aside — and what the exclusion costs

Edwin, 2026-08-27. D is the only fill made with the hard arm-centrifuge extrusion, a step the two-stage recipe
has **retired** — a reason about the METHOD, which is what makes it admissible where "it reads oddly" would
not be. ⚠ **But it also removes the only Esterer/Lugitsch single-fill overlap in the archive**, and the Esterer
mean moves 91 → 85. Reason and benefit point the same way, which is exactly when this kind of call needs a
witness. ⇒ `diagnostics/d2r_all_runs.py` re-reads the excluded reports every run and prints σ_fill **both
ways** — 6.9 over the three fills kept, 12.4 with D back in — on the console and on the figure. **One fill by
D's own method reopens it.**

### 12.3 Refuted along the way — so nobody re-runs them

| claim | why it died |
|---|---|
| **`Rv` rides turbidity** (`r = +0.86` on three Lugitsch fills, +1.1 per 0.01 `A_valley`) | the **second Esterer fill** sits at the same `A_valley` as the first (0.171 vs 0.182) and **15.4 `Rv` higher**. Over all 16 runs of the evening `r = −0.07`. ⛔ Pooling oils whose slopes have opposite signs (§5 of the ROADMAP) gives ~0 by construction and must never be quoted |
| **the blue-flank reference** `A[556–566]` in place of `A_Q` | best of ~50 windows on 115 archived runs — corridor **−1.45 → +0.91**, errors 1 → 0, drift −25 % — and then **FAILED ON THE FIRST NEW SAMPLE**: a spoiled Lugitsch reads `Rv′` **228.1**, identical to the fresh fill's 228.1, because its thin denominator collapses with the numerator. `Rv` halves correctly on the same sample (99.5 → 50.7). ⛔ Do not re-run the sweep |
| **`d2R` as a second witness** | not fill-invariant: 1.41–1.51 on one fill and 1.94 on another of the same oil, one evening — 76 % of the session step it was supposed to corroborate. `Rv` agreed to 0.6 across the same pair |
| **SNV shape as independent evidence** | `SNV(624) − SNV(569)` tracks `Rv` at **r = 0.993** over 19 runs. Agreement there is the same measurement re-expressed, not corroboration. Its binary "which band is taller" also flipped for Lugitsch between two sessions |
| **`A_Soret` brought into `Rv`** | one form of six survives (`Rv − Q%′`) and improves the pooled σ_fill by ~20 % scale-free — but leaves the day-to-day drift and the Esterer/Lugitsch single-fill overlap **unchanged**. Tested and shelved, ⇒ §12.7 |

---

## ⛔⛔ 13 · THE BASELINE IS NOT SETTLED — `Rv`'s corridor over the whole archive is NEGATIVE  *(2026-08-29)*

`SPEC_metric_research.md` **§16** is the full write-up; this section exists so the finding cannot be missed
by anyone reading only `Rv`'s own spec.

Scored over **124 labelled runs, three solvents, both sides of the rebuild** — one shared threshold, which is
the property `Rv` was chosen for on 2026-08-25:

| metric | cut | errors | corridor | Cohen's d |
|---|--:|--:|--:|--:|
| **`Rv`** *(shipped)* | 52.5 | **1** | **−11.5** ⛔ green and brown OVERLAP | 2.86 |
| `RvCont` — both bands above one fitted continuum | 65.0 | **0** | **+5.1** | 3.51 |
| `R` — `SPEC_metric_research.md` §12 | 51.2 | **0** | **+5.9** | 3.53 |

⛔ **`Rv` green and brown overlap by 11.5 units across the archive, and two independent coherent
constructions both turn that positive.** On the isopropanol corpus alone — the 88 runs M9 would be
pre-registered against — `Rv`'s corridor is −11.5 with 1 error, `RvCont`'s is **+18.0** with none, and the
run `Rv` gets wrong is `20270729B/002`, the same one ROADMAP item 1's phase **P1** already exists to pull the
raw frames of.

⛔⛔ **AND IT IS NOT A PROPOSAL TO SWAP — the hold-out kills it.** Every cut above is fitted on the runs it
is scored against. Fit the threshold on isopropanol alone and apply it untouched to the other 36 runs:
**`Rv` 0/36, `R` 0/36, `RvCont` 1/36, `RvLin` 6/36, `RvTest` 6/36**; in the other direction `Rv` and `R` give
5/88 against `RvCont`'s 8/88. ⇒ **`Rv` transfers best, and `RvCont`'s 0-errors-on-124 was bought by fitting
the cut on all 124.** `SPEC_metric_research.md` §16.3a.

⭐⭐ **What survives is the finding, not a replacement.** `Rv`'s whole-archive corridor really is negative,
and **four independent baseline constructions fail to close it without costing transfer** — so the overlap
is **not a baseline artefact**. That is worth more than a candidate: it says the 11.5-unit overlap has to be
explained somewhere else (§6.7's diffuser, the brown end, or the labels), and rules out a whole family of
fixes at the desk instead of at the bench.

⭐ **Two things from §16 that apply to `Rv` as it stands today.**

1. **A flat pedestal cancels EXACTLY in `Rv`** (measured: +0.10 A leaves it unmoved to three figures), so no
   amount of scatter, bubbles or particulate can move it. ⛔ **A TILT can, and by a lot**: `Rv` moves **+5.1**
   per 0.01 A per 100 nm of baseline slope, because its numerator carries a 94.5 nm lever arm. Every "`Rv`
   rides turbidity" argument in §12.3 should be re-read as being about *tilt*, not level.
2. ⭐ **`RvTest − Rv` is exactly the trough depth**, by the identity
   `RvTest − Rv = 100·(A_valley − A[612–615])/(A_Q − A_valley)`, and it flags the fills already suspected on
   other grounds: `20260826EstererD` **−29.6**, `20260824Lugitsch` **−20.1**, `20260826Stekko/004` **−16.0**.
   Worth carrying as a fill-quality diagnostic whichever metric ships.

⚠ **And it reopens §12.8.4.** `EstererD` was set aside on the METHOD, with the standing note that its removal
is also convenient. The family disagrees about it: `Rv` 107.4 and `RvCont` 113.2 call it Esterer's **highest**
fill, `RvTest` 80.2 and `RvLin` 88.9 call it the **lowest**. ⇒ **the exclusion is not baseline-independent**,
and that has to be on the table when the replicate fill is finally run.

---

## ⭐⭐ 14 · THE FIRST NEGATIVE `Rv` — and what it does and does not mean  *(2026-08-29, `20260828BillaCleverA`)*

The first brown fill made under the settled sunflower recipe reads **`Rv` = −10.0** (runs −7.1 and −13.0),
against **31.0 – 46.4** for the same oil across five archived fills. `SPEC_metric_research.md` §16.7 is the
write-up; this section carries it in `Rv`'s own spec because it is a property of the shipped metric.

**The mechanism.** The band is still there; the region it sits in has fallen below the valley:

```
A[622-627]  0.0662     the red band
A[500-560]  0.0768     the valley Rv baselines it against  ->  numerator NEGATIVE
A[612-615]  0.0213     but the band is +0.0449 above its OWN shoulder
```

⇒ §16.1's inverted trough, at the opposite extreme and on a brown oil. On the same capture `RvTest` reads
29.9 and `RvLin` 29.3 — both firmly positive, because their baseline is 11 nm away instead of 70.

#### ⛔ 14.1 NOT A GAUGE PROBLEM, AND NOT A SENSITIVITY PROBLEM — both claims withdrawn

| claim | verdict |
|---|---|
| *"a negative value is off the gauge's scale"* | ⛔ **wrong.** `SPEC_roast_ampel.md`'s `bandLeft` / `bandRight` / `gradientAnchors` are configuration; a thermometer shows negatives. Covering −13 … +130 is a config change |
| *"the metric is hypersensitive near zero"* | ⛔ **wrong, measurably.** `Rv = 100·num/den`, so an absolute numerator error `δ` moves it by `100·δ/den` — **constant**, not amplified. ⭐ The six most error-sensitive runs in the archive are all **GREEN** (`20260826Stekko`, `den` = 0.081, where 0.01 A moves `Rv` by 12.3 against 4.3 on a thick fill). Billa's negative reading sits at `den` = 0.098, *less* sensitive than several green fills |

#### ⭐ 14.2 What survives

**1 · The verdict is untouched.** `T` = 52, higher = greener. 34.2 and −10.0 are both emphatically brown;
nothing misclassifies, and the margin is enormous.

**2 · A 44-unit swing on one oil disqualifies `Rv` as a CONTINUOUS quantity** — which is what
`SPEC_history_tracker.md` needs it to be — regardless of the sign. ⚠ Part of that 44 may be method rather
than oil: this fill uses the same-jar reference (§16.8) and the archive is two-jar. Unresolved.

**3 · A sign change means the PREMISE failed, not that the value is low.** `Rv`'s numerator is defined as
*how far the 624 band sits above its baseline*; when it is negative the number reports the baseline's
position rather than the band's. Still plottable, no longer the same measurement.

#### 14.3 Sign robustness across 132 runs, and it orders by extrapolation distance

| metric | min | negatives | its numerator's baseline is carried |
|---|--:|--:|---|
| **`Rv`** | **−13.0** | **2** | 94.5 nm, from a different part of the spectrum |
| `RvCont` | **1.0** | 0 | 20.5 nm past the continuum fit's edge |
| `RvLin` | 16.3 | 0 | 11.0 nm past the far anchor |
| `RvTest` | 17.0 | 0 | 11.0 nm — the band's own shoulder |

⭐ `RvTest` is the only one that structurally cannot go negative: a band that is not taller than its own
shoulder is not a band. ⛔ `RvCont` came within **1.0** — its numerator on `BillaCleverA/002` is 0.0014 A,
a coincidence rather than a margin. **Sign robustness and §16.2's structural argument pick different
metrics; both are true and neither settles the choice.**

⚠ **One brown fill is one brown fill.** Everything here at the brown end rests on this fill plus the three
archived brown sunflower fills — the corpus gap §16.3c already names as the blocker.

#### ⭐⭐⭐ 14.4 THE REPLICATE ARRIVED, AND IT IS WORSE — `Rv` scatters 36 units on one brown oil

`20260828BillaCleverB`, same recipe, 32 minutes after A: **`Rv` A −10.0 → B 26.2, a 36.3-unit swing on
two fills of one oil.** Four times `Rv`'s worst green-pair scatter of the same night. On the same pair
`RvLin` moves 6.3 and `RvTest` 6.1.

⭐ **The verdict is untouched and that is the point.** All seven fills of 2026-08-28/29 classify correctly
against `T` = 52 — greens 83–94, browns −10 and 26 — and **nothing came near the line.** A 36-unit scatter
cost `Rv` nothing as a threshold.

⇒ ⭐⭐ **The threshold and the number are two different products.** `Rv` keeps the verdict job it has never
failed; `SPEC_metric_research.md` §16.9 makes `RvLin` the leading candidate for the CONTINUOUS job
(`SPEC_history_tracker.md`), which `Rv` demonstrably cannot do. ⛔ Neither is adopted — see §16.9c.
