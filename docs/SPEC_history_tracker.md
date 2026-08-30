# SPEC — The history tracker: a SHAPE distance that alarms when an oil changes

**Status: DESIGN. Nothing here is implemented.** Every number below is measured on archived reports
and reproducible with the scripts in §10; nothing is projected.

> ⭐⭐ **SUPERSEDED IN PART, 2026-08-14 — the tracker's statistic is now `V`, not the shape distance
> `D`.** `SPEC_metric_research.md` **§10** defines it: `V = (A_valley − A_Q)/A_Soret` on raw
> absorbance, no baseline. It beats `D` on every property this document cares about — refill
> reproducibility **0.21 units = 4.7 % of the class span** against `D`'s 14.6 %, and a **±1.0** alarm
> band that stays silent on every benign change on record while catching an undissolved fill, a
> half-strength prep and a class change. ⇒ **Read §3–§6 as the derivation of why a baseline-free,
> offset-cancelling quantity is the right shape for this problem — that reasoning is what produced
> `V` — and §10 of the metric-research spec for the statistic to implement.** The `D`-specific
> results below stand as measured and are not withdrawn; they are simply no longer the recommendation.

**Owner:** Edwin · **Opened:** 2026-08-14 · **Prompted by:** Edwin, looking at the six-oil panel —
*"if you look at the three curves of the BillaJaNatürlich runs in the 560–580 nm region then the
similarity of the three curves is obvious… though M448 does differ very much. So could we put this
similarity into a mathematical concept?"*

**Relation to what exists:** `SPEC_capture_quality.md` **§16.34** established *what the metric can be
sold as* — a history tracker, not a quality meter — using the **scalar** `M448` / `B_Q`. This document
specifies the **multivariate** sibling: instead of asking *"has the number moved?"* it asks *"has the
curve changed shape, in any direction at all?"*. It also un-parks `SPEC_roast_ampel.md` **§9.3a** and
ROADMAP item **3a**, which named the deviation alarm but deferred its design.

---

## 1 · Why a shape distance rather than another metric

The metric hunt (`SPEC_metric_research.md`, `SPEC_capture_quality.md` §16.29–§16.32) has now lost five
candidates to the same two failures: a **small denominator** (§16.29, §16.30.2, §16.30.7f, §16.31.2)
and a **label dependence** — §16.31.3 found two statistics that separate the oils under *opposite*
labellings, which means the labels were carrying the result.

⭐ **A deviation alarm is immune to both.** It has no denominator, because it is not a ratio. It needs
no labels, because the reference is the user's own oil. §16.34's table applies here unchanged:

| requirement | absolute verdict | history tracker |
|---|---|---|
| class labels (§16.31.3) | ✅ | ❌ |
| ground truth (§16.31.4) | ✅ | ❌ |
| an absolute threshold | ✅ | ❌ |
| cross-instrument calibration | ✅ | ❌ — the mill compares against its own instrument |
| **reproducibility** | ✅ | ✅ **the only requirement** |

**The use case, in Edwin's words:** *"I start with a big bag of pumpkin seed, make the first pressing,
and call that my reference absorption spectrum. Subsequent pressings from the same bag are compared
against it. Can the shape distance tell me whether something has changed fundamentally?"*

---

## 2 · Where it came from — the observation

The three `20260812BillJaNatuerlich` runs move **22.4 %** in amplitude (`B_Q/B_Soret` = 0.0578 →
0.0442 → 0.0373 over eight minutes) while their **shape over 560–580 nm stays visibly the same**.
Amplitude and shape are therefore carrying different information, and only one of them is being read
by the shipped metric family.

📈 **Figure: `spectracs-references/tmp/oil_shape_panel.png`** (`diagnostics/oil_shape_panel.py`) —
**eight fills** since 2026-08-14: the six oils above plus the archive's two other **Steirerkraft**
fills, drawn in one teal family so that *one product, three fills* reads at a glance. One oil is
opened up run by run (`--oil`, default `Ja! Natürlich`).

⚠ **Read the third panel, not the second.** Panel 2 is SNV'd over the whole 448–629 capture range,
where the Soret sets the standard deviation — §3.1 rules that out for the metric. **Panel 3
renormalises inside 550–600 and is therefore literally the set of vectors `D` compares.**

⚠ Two corrections to the first reading, both established below: the visual tightness is partly an
artefact of the other five oils being spread across the plot (Ja! Natürlich is in fact the
**second-worst** of the six in shape repeatability, §5.1), and the shape's apparent stability there is
**drift that happens to be slow**, not noise that happens to be small (§6.4).

---

## 3 · The mathematics

### 3.1 The nuisance group, and SNV as its quotient map

After the linear baseline, one run over a window of `n` wavelengths is a vector `a ∈ ℝⁿ`. Everything
the tracker must ignore — concentration, seating, exposure — acts on it as

```math
a → k·a + b            (k > 0)
```

which is §16.7.2h's own measured error model. **SNV is exactly the quotient map for that
two-parameter group:**

```math
z = (a − mean(a)) / sd(a)
```

is invariant under `a → k·a + b` by construction. What survives is a point on a sphere: pure shape,
no amplitude, no offset.

> ⛔ **SNV must be taken over the ANALYSIS window, not over the 448–629 capture window.** Otherwise
> the Soret dominates the standard deviation and the Q-band shape becomes a rounding error. This is
> the same choice that made SNV load-bearing in §16.31 and useless in §16.30.7 — *"choose the
> normalisation per statistic, not once"* (§16.31.1).

### 3.2 `D` — the shape distance

Similarity between two runs is the cosine of the angle between their SNV vectors, which is identically
the Pearson correlation `r` of the raw window values. The distance is

```math
D = √(1 − r²) = sin θ            reported in %
```

read as: **the fraction of a run's own variation that the reference cannot explain, after a free
rescale and a free offset.**

Three properties earn it its place:

1. ⭐ **It is a true metric.** `arccos r` is geodesic distance on the sphere, so the triangle
   inequality holds — which is what makes "distance from the reference, over time" a coherent thing to
   plot, and what makes §6.4's straightness test possible at all.
2. ⭐ **It is dimensionless**, so it is comparable across oils and across windows.
3. ⭐ **It has no denominator and no threshold of its own** — the two failure modes of §1.

### 3.3 The residual curve — keep it, do not collapse it

`D` is a scalar, and a scalar says *how far*, never *which way*: two unrelated faults give the same
number. The quantity it summarises is a **curve**, one value per wavelength:

```math
r(λ) = z(λ) − c·z_ref(λ)         with c fitted by least squares
```

Reference `Ja! Natürlich 001`, sampled every 5 nm over 550–600:

| | 550 | 555 | 560 | 565 | 570 | 575 | 580 | 585 | 590 | 595 | 600 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| JN 002 — *silent* | −0.18 | −0.10 | −0.13 | −0.18 | 0.09 | 0.18 | 0.10 | −0.16 | 0.02 | 0.12 | 0.04 |
| S-Budget 001 — *alarm* | **−1.14** | **−0.95** | −0.56 | −0.02 | **0.52** | **0.47** | 0.25 | −0.06 | 0.29 | 0.47 | 0.35 |

The silent row is structureless at ±0.18. The alarm row is a clean systematic ramp. ⇒ **The alarm is
one number; the diagnosis is free, because the curve is already computed before it gets squared.**
Edwin 2026-08-14: *"I just want an alarm, the cause is not part of the alarm — but if the slope or
form completely changed, that info might be of interest."* This is that information, at no extra cost.

### 3.4 `k = 1` versus `k ≥ 5` — and what `D` actually is

**With one reference press** there is no spread, so there is no model of natural variation. Fit only a
scale, `ẑ = c·z_ref`; everything else is residual. For SNV vectors this gives exactly

```math
D² = ‖r‖² / ‖z‖² = 1 − r²
```

⇒ **`D` is the normalised `SPE` of a one-component model whose single component is the reference
spectrum itself.** That is both why the scalar is the right statistic for *"first press = my
reference"*, and why it cannot distinguish *extreme but familiar* from *new and strange* — with one
reference press, nothing is familiar yet.

**With `k ≥ 5` reference presses**, PCA on the centred reference set gives directions `p₁…p_A` with
score variances `λ₁…λ_A`, and the distance splits in two:

| statistic | definition | reads as |
|---|---|---|
| **`T²`** (Hotelling) | `Σ_a t_a²/λ_a`, `t_a = ⟨z − z̄, p_a⟩` | *the same kinds of variation the reference always shows, but an extreme amount* — Mahalanobis distance in score space |
| **`SPE`** (Q) | `‖ z − z̄ − Σ_a t_a p_a ‖²` | ⭐ *a direction of variation the reference set never showed* — *this* is "something changed fundamentally" |

> ⭐⭐ **The reason to collect `k ≥ 5` presses of the reference lot is not statistical decoration.** It
> is what buys the `T²`/`SPE` split, and with it a control limit derived from the mill's own process
> instead of a number we would otherwise have to guess. §6.2 shows the harder consequence of `k = 1`:
> *which* run you nominate as the reference can flip the verdict.

### 3.5 It is not invented here

`SNV → PCA → T² + SPE + contribution plots` is **multivariate statistical process control** (MSPC),
factory-floor technology since the early 1990s; the classification cousin is **SIMCA**, and the
one-component angular form is the remote-sensing **Spectral Angle Mapper**. ⭐ This matters for §11:
the method's failure modes are documented literature, not house rules — which is a materially
different thing to defend in front of a lab.

---

## 4 · How it relates to the scalar tracker of §16.34

> ⭐⭐ **THE SCALAR IS NOW `RvLin`, NOT `M448`/`B_Q`** *(2026-08-30)*. This chapter was written when the
> scalar half of the tracker was still undecided and `M448` was the placeholder. `SPEC_metric_research.md`
> **§16.11** chose `RvLin` for the continuous number on 2026-08-29, and **§16.14** confirmed it against
> Edwin's eye the next day: on three GREEN oils `RvLin` put Lugitsch 22.8 above the other two while calling
> Esterer and Steirerkraft equal — which is exactly what the eye reported. `RvCont` split that equal pair by
> 12.04 and is out; `Q%` named Esterer the greenest and inverts.
> ⇒ **read every `M448` in the table below as `RvLin`.** The *argument* of this chapter is unaffected —
> `D` and a scalar have complementary blind spots whichever scalar it is — but the column heading is stale.
> ⛔ **And the gate has moved with it**: §9's σ_fill is now `SPEC_metric_research.md` §16.16's registered
> run (Lugitsch, six fills, cut at 2.0), because §16.15 retired every σ_fill figure measured under the
> pre-vortex recipes. ⚠ Until that evening runs, this document's tolerance has no floor to stand on.


They are complementary, and neither replaces the other:

| | §16.34 scalar (`M448` / `B_Q`) | this document (`D`) |
|---|---|---|
| answers | *how much* has it moved, and in which direction | *whether* anything changed, in any direction |
| needs a metric choice | ✅ yes — and five candidates have died choosing it | ❌ no |
| direction of change | ✅ signed — browner / greener | ❌ unsigned (⇒ read the residual curve, §3.3) |
| blind to | changes orthogonal to the chosen bands | a pure amplitude change (by construction) |
| gated on | σ_fill (§16.34.3) | σ_fill — **the same run** (§9) |

⭐ **The blind spots are complementary, which is the argument for shipping both**: `D` cannot see a
pure concentration change, and `M448` cannot see a shape change that leaves the band ratio alone.
📌 `SPEC_roast_ampel.md` §9.3a's three open questions (units of the tolerance, σ_fill as the floor,
symmetry of the band) apply here unchanged — §9.3a asked them of the scalar; §7 answers the first two
for `D` and leaves the third open.

---

## 5 · Evidence base I — does shape separate oils at all?

Six oils, three runs each, one fill per oil (`diagnostics/shape_similarity.py`).

### 5.1 The floor, and the trap

| fill | `D_within` % (560–580) | amplitude CV % |
|---|---|---|
| Spar Premium g.g.A. | **0.95** | 1.9 |
| Steirerkraft g.g.A. | 1.64 | 3.6 |
| Spar Steirisches | 1.64 | 2.4 |
| Billa Clever | 6.26 | 4.7 |
| ⛔ Ja! Natürlich | 8.95 | 22.4 |
| ⛔ Spar S-Budget | 11.56 | 0.1 |

⚠ **The observation of §2 does not generalise.** On four of the six oils the *amplitude* is more
stable than the shape. Ja! Natürlich is the fill where shape wins because its amplitude is collapsing
toward the sensor floor — not because shape is the inherently stabler quantity.

### 5.2 ⛔ The trap: most of the correlation is the shared flank

| window | mean `D_between` | pooled `D_within` | ratio |
|---|---|---|---|
| 560–580 raw shape | 24.1 % | 5.2 % | 4.7× |
| 560–580, common shape (PC1) removed | 79.1 % | 53.4 % | ⛔ **1.5×** |
| 550–600 raw shape | 25.4 % | 4.3 % | 5.9× |
| 550–600, common shape removed | 66.6 % | 36.2 % | ⛔ **1.8×** |

Every pumpkin oil shares one rising flank through the Q band, and that shared flank is most of the
correlation. Strip it and the ratio falls to **1.5–1.8× — the same F ≈ 1.3–1.9 wall §16.30.7g hit.**

> ⛔⛔ **As an oil-IDENTITY fingerprint this fails exactly where its predecessors failed. It is
> specified here only as a DEVIATION ALARM against a stored reference**, which is a different and much
> weaker question. Do not quote §5 as discrimination evidence.

---

## 6 · Evidence base II — what a re-preparation costs

### 6.1 A second fill of the same oil (`diagnostics/shape_refill.py`)

| product | `D_within` | `D_refill` | ratio |
|---|---|---|---|
| Steirerkraft (3 fills, 9 days apart) | 4.62 % | **26.20 %** | ⛔ 5.7× |
| Kiendler (3 fills, one evening) | 4.53 % | 13.35 % | ⛔ 2.9× |
| Spar S-Budget (2 fills, 7 days) | 6.64 % | 8.96 % | 1.3× |
| Billa Clever (2 fills, same evening) | 6.69 % | 5.42 % | ⭐ 0.8× |

⚠ **Same-session refills are cheap; cross-session ones are not.** Steirerkraft's two 2026-07-29 fills
agree to **6.8 %**; against the 2026-08-07 fill they sit at **35.7 / 36.1 %** while their *amplitude*
held to 6 %. ⛔ Something real changed — but oil ageing, lamp ageing and a protocol change are
**mutually confounded** in the archive, and attributing change to the sample is the tracker's entire
job. ⇒ §7.5's session control sample is not optional.

### 6.2 ⭐⭐ The decisive number: one drop moves the shape 18 %

The Kiendler triple is the only archive set where the dose was varied on purpose and nothing else was
(`diagnostics/kiendler_dilution.py`): **A** = 18 mL + 6 drops, **B** = A enriched to 7 in place,
**C** = a fresh 18 mL + 7 drops.

| pair | differs by | `D` |
|---|---|---|
| **B vs C** — same dose, two independent preparations | nothing intended | ⭐ **4.45 %** (floor 2.1 %) |
| **A vs B** | one drop | ⛔ **17.73 %** |
| **A vs C** | one drop | ⛔ **17.87 %** |

SNV is invariant to `a → k·a + b` algebraically, so this **cannot** be concentration acting as a scale
factor. It is concentration acting **non-linearly** — stray light, path length, and the baseline
anchors themselves shifting.

> ⛔⛔ **Uncontrolled dosing would make the tracker read the pipette, not the seed.** This is
> §16.21.1's *"hold the dose fixed"* arriving from an independent direction, and it promotes the
> capillary (§16.23.7) from a noise-reduction nicety to **the enabling prerequisite**.

### 6.3 ⛔ Derivatives lose — and that sharpens §16.31.5a

Edwin 2026-08-14: *"Steirerkraft and Spar Premium should trigger the alarm — obviously the slopes and
curvatures differ."* Tested by running the whole comparison in derivative space
(`diagnostics/shape_derivatives.py`):

| representation | passes (560–580) | passes (550–600) | median margin (550–600) |
|---|---|---|---|
| **curve** | **11 / 18** | **13 / 18** | **+4.41 %** |
| slope (SG, 25 pt) | 10 / 18 | 11 / 18 | +4.28 % |
| curvature (SG, 25 pt) | 8 / 18 | 9 / 18 | +0.44 % |

⛔ **Every differentiation costs passes, at both windows.** Ja! Natürlich's own runs went from
13.7 / 20.2 % on the curve to 35.3 / 45.4 % on the slope, while the nearest stranger only went
18.0 → 39.9 %: everything inflated, the signal inflated less. **Differentiation multiplies each
Fourier component by `2πf`, and the oil difference is broad (low `f`) while the noise is not.**

> ⭐⭐ **This sharpens §16.31.5a rather than repeating it.** That section blamed the loss on
> *adaptivity* — an extremum uses one point where a windowed fit uses forty. This test kept every
> point and averaged over all ~100 of them, and derivatives still lost. ⇒ The rule is not "more points
> beat better math", it is the harder statement underneath: **this data is SNR-limited, and any
> operation that boosts high-frequency content is unaffordable regardless of how many points it
> averages.**

### 6.4 ⭐⭐ The result that reframes the floor: the scatter is DRIFT, not noise

Runs within a fill are time-ordered — which noise cannot exploit and a drift cannot hide from. Noise
has no memory, so `D(1,2)`, `D(2,3)`, `D(1,3)` should be alike. A monotone drift must give
`D(1,3) > D(1,2)` and `D(1,3) > D(2,3)`, and a *straight* trajectory makes the triangle inequality
tight (`diagnostics/shape_drift_signature.py`, 550–600 nm):

| fill | D(1,2) | D(2,3) | D(1,3) | signature | straightness |
|---|---|---|---|---|---|
| Ja! Natürlich | 11.96 % | 7.53 % | 17.36 % | **DRIFT** | **0.89** |
| Steirerkraft | 2.17 % | 3.36 % | 5.29 % | **DRIFT** | **0.96** |
| Spar Steirisches | 2.99 % | 1.58 % | 3.78 % | **DRIFT** | 0.83 |
| **Spar Premium** | 2.53 % | 2.32 % | 1.56 % | ⭐ **noise-like** | 0.32 |
| Spar S-Budget | 16.63 % | 1.59 % | 16.79 % | **DRIFT** (a step) | 0.92 |
| Billa Clever A | 15.94 % | 4.72 % | 18.56 % | **DRIFT** (a step) | 0.90 |
| Billa Clever B | 11.28 % | 10.62 % | 11.29 % | DRIFT | 0.52 |

⭐⭐ **Six of seven fills carry the drift signature, five of them as a near-straight march.** This is
§16.33 / §16.34.4 seen from a second direction — *"Ja! Natürlich's 15.3 % run-to-run CV is 93 %
settling drift… it is not a hard oil to measure, it is an undissolved one."*

⇒ **Three consequences, and they are the most important paragraphs in this document:**

1. ⭐ **The within-fill scatter is NOT the instrument's floor.** It is the tracker correctly reporting
   that the sample changed while it was being measured. Every "failure" in §5 and §7 is a **protocol**
   result, not a metric result.
2. ⭐ **The real floor is Spar Premium's**, the one fill with no drift: **`D_within` = 0.95 % (560–580)
   and 1.24 % (550–600)**, pairwise 0.7–2.5 %. ⭐ That is an independent cross-check on §16.26 —
   a 1–2 % shape floor sits right on top of the **1.36 % rms re-seat cost** measured there by a
   completely different route.
3. ⭐ **Two distinct signatures are already distinguishable**: a *march* (Steirerkraft, straightness
   0.96 — steady dissolution) versus a *step* (S-Budget and Billa Clever A: `D(1,2)` ≈ 16 %, then
   `D(2,3)` ≈ 1.6–4.7 % — run 001 is different, then stability). ⇒ **"Discard run 001, or settle until
   `D` between consecutive runs falls below the floor"** is a free protocol rule, and §7.4 adopts it.

---

## 7 · The design — settled choices

| # | choice | why |
|---|---|---|
| **7.1** | **Baseline**: linear chord over the shipped anchors (520–540, 620–630) | load-bearing — §16.31.1 measured that dropping it separates nothing at all |
| **7.2** | **Window: 550–600 nm**, ⛔ *not* 560–580 | 13/18 vs 11/18 passes, median margin +4.41 % vs +1.35 % (§8.1). ⚠ Against intuition: 560–580 is where every oil looks *alike*; the discriminating information is in the wings |
| **7.3** | **SNV over that window**, then `D = √(1−r²)` ⛔ **no derivative** | §3.1, §6.3 |
| **7.4** | **Protocol**: fixed dose (capillary), standardised settle, discard run 001 or settle until consecutive-run `D` < floor | §6.2, §6.4 item 3, §16.34.3a |
| **7.5** | ⛔ **A control sample every session** (null jar, or a fixed optical standard) charted alongside — ⭐ **and the scope is now a PRODUCT-LINE EPOCH (§11.3)**, which records the lamp, the protocol and the read rule, so "cannot cross" is enforced rather than remembered | the only way to split instrument drift from oil change — §6.1. ⛔ **A chart cannot cross a rig change**; the 2026-07-29 rebuild already broke comparability once (§16.11) |
| **7.6** | **Reference = the epoch's running MEAN, `k ≥ 3` (5 comfortable)**, not one — ⭐ **PRICED IN §11.4**: a 1-fill reference inflates the comparison noise by √2 and the false-alarm rate 15× (0.2 % → 3.0 %); **3 is the minimum, 5 comfortable**, and the reference is the MEAN, never the first measurement | §3.4, §6.2 — with `k = 1` the reference may itself be the outlier and there is no way to know |
| **7.7** | **Control limit** = pooled within-reference `D` + 3σ, floored at σ_fill — ⚠ and the σ in it is the COMPARISON σ, `σ·√(1+1/n)`, not the run-to-run σ (§11.2) | §9. ⚠ A band tighter than σ_fill alarms on the tube, not the oil (`SPEC_roast_ampel.md` §9.3a item 2) |
| **7.8** | **Alarm shows one number; clicking it shows the residual curve** | §3.3 — the diagnosis costs nothing |

⚠ **Open**: is the band symmetric? Drifting *less* like the reference in the greener direction may not
warrant the same alarm as the browner one. `SPEC_roast_ampel.md` §9.3a item 3, unanswered here.

---

## 8 · The acceptance gate

### 8.1 Edwin's test, and where it stands (`diagnostics/shape_alarm_test.py`)

> *"Reference = Ja! Natürlich run 001. Spar S-Budget must ALARM. Ja! Natürlich runs 002 and 003 must
> stay SILENT."*

| window | own runs | nearest stranger | verdict |
|---|---|---|---|
| 560–580 | 13.73 / **20.18** % | **18.01 %** (Steirerkraft) | ⛔ **FAILS** — no threshold exists |
| **550–600** | 11.96 / 17.36 % | **33.41 %** (Spar Steirisches) | ⭐ **PASSES, margin +16.05 %** |

> ⚠ **CORRECTED 2026-08-14: that +16.05 % margin is inflated by the far anchor.** The chord's far foot
> sits on the Qy band (§16.35.1), and `Ja! Natürlich` has the most Qy of any fill, so the anchor
> distorts it most. Re-run with the foot moved off Qy (596–604) the margin is **+2.98 %** — it still
> passes, but narrowly. The aggregate 13-of-18 is unchanged by the anchor.

Steirerkraft lands at 34–38 % and Spar Premium at 53–55 %: both alarm, exactly as required.
Generalised to all 18 runs as reference: **13 / 18** pass. ⛔ The five failures are **Spar S-Budget
(3/3)** and **Billa Clever (2/3)** — the two fills §6.4 shows were still changing during measurement.
⭐ **Steirerkraft, Spar Steirisches and Spar Premium pass on every single reference run.**

⇒ **The test is passable today**, on the plain curve, at 550–600, from a fill that has settled.

### 8.2 ⚠ What passing it does not mean

⛔ **Edwin's test is the EASY case.** Telling S-Budget from Ja! Natürlich is telling two *products*
apart. "Same seed bag, second press" is a far smaller change. Passing §8.1 is **necessary and nowhere
near sufficient**, and §9.2 is the experiment that prices the hard case.

### 8.3 ⭐ THE THREE-TIER ALARM — it reproduces the grouping 17/17, and it classifies FILLS, not oils  *(Edwin 2026-08-14)*

> *"From the oils of the panel I think we have three groups per shape. **A**: the Ja! Natürlich runs.
> **B**: Spar Premium and Steirerkraft g.g.A. **C**: Spar S-Budget, Billa Clever and Spar Steirisches
> g.g.A. We take Ja! Natürlich run 001 as the reference shape. JN 002/003 → silent; Spar Premium or
> Steirerkraft → **probably minor difference**; S-Budget or Billa Clever → **probably major
> difference**."*

Implemented as two thresholds on `D` (`diagnostics/shape_tiered_alarm.py`). Pinned configuration:

```
   reference = 20260812BillJaNatuerlich/001.pdf      window = 540-584 nm
   T1 = 14.7 %   (silent | minor)                    T2 = 22.8 %   (minor | major)
```

| tier | fill | `D` per run | verdict |
|---|---|---|---|
| **A** silent | Ja! Natürlich 002, 003 | 11.34, 14.16 % | ✓ ✓ |
| **B** minor | Steirerkraft g.g.A. | 15.25, 15.98, 16.96 % | ✓ ✓ ✓ |
| **B** minor | Spar Premium g.g.A. | 22.16, 21.17, 21.95 % | ✓ ✓ ✓ |
| **C** major | Spar S-Budget | 23.44, 32.80, 32.45 % | ✓ ✓ ✓ |
| **C** major | Billa Clever | 28.57, 30.16, 25.27 % | ✓ ✓ ✓ |
| **C** major | Spar Steirisches | 29.47, 29.22, 29.12 % | ✓ ✓ ✓ |

⭐ **17 / 17 runs land in the assigned tier.** The ordering Edwin read off the panel is real and the
alarm reproduces it exactly.

⛔⛔ **And three findings say it must not be quoted as a result.**

**1 · The window was fitted to the answer.** Scanning 105 candidate windows, **only 4 separate all
three tiers**, and the winner's margins are **+1.09 % (A|B) and +1.28 % (B|C)** — *at or below* the
1–2 % instrument floor of §6.4. Choosing 1 of 105 to make a grouping work, on 17 comparisons, is the
selection risk §16.7.2k's note 5 names, in its purest form.

**2 · The grouping is a property of the oils AND the window, not of the oils.** At the two windows
this document had already justified for other purposes:

| window | what happens to the tiers |
|---|---|
| **560–580** — where the grouping is *visually* obvious | ⛔ **A and B overlap by 2.17 %**: JN 003 at 20.18 % sits beyond Steirerkraft at 18.01 % |
| **550–600** — §7.2's two-tier window | ⛔ **B and C INVERT**: Spar Premium runs to 52.98–54.62 % while S-Budget sits at 50.16–53.00 % |

**3 · ⛔⛔ The decisive one: the tiers classify FILLS, not OILS.** Run the same thresholds against
fills outside Edwin's grouping:

| fill | `D` range | verdict |
|---|---|---|
| **Steirerkraft `0729B`** — *the same product as tier B* | **27.88 – 34.42 %** | ⛔ **probably major difference** |
| Kiendler `0801A` | 31.74 – 36.21 % | probably major |
| S-Budget `0731A` | 31.61 – 34.51 % | probably major |
| Billa Clever `0812A` | 26.45 – 33.18 % | probably major *(consistent with `0812B`)* |

> ⛔⛔ **Steirerkraft is tier B in its 2026-08-07 fill and tier C in its 2026-07-29 fill.** One
> product crosses both thresholds depending on which fill is measured. That is §6.1's refill cost
> (26.20 % for this product) landing exactly where it was predicted to: **above `T2`**. ⇒ Until
> `D_refill` is brought below `T1`, a three-tier alarm reports the preparation, not the oil.

⇒ ⛔⛔ **STATUS 2026-08-14: REFUTED.** The refutation arrived sooner than §9.3 and from a defensible
change of baseline rather than new data: moving the chord's far anchor off the Qy band (620–630 →
596–604, §16.35.2) takes this alarm from **17/17 to 4/17**. A result that a legitimate anchor choice
destroys was fitted, not found — which is precisely what pinning the configuration was for. ⭐ The
**two-tier** alarm of §8.1 is unaffected (13/18 under either anchor). ⚠ Superseded in any case by
`SPEC_metric_research.md` §10's `V`, whose ±1.0 band needs one threshold, not two.

*(Original framing kept below for the record.)* The configuration is frozen in the script
so that §9.3's data can falsify it rather than be fitted to it. ⭐ The two-tier alarm of §8.1 is
unaffected — it needs one threshold, not two, and its margin is +16.05 %, an order of magnitude
above these.

### 8.4 ⚠ THE WORKING HYPOTHESIS — "the faint fill's shape would survive a stronger dilution"

> *"Maybe though the BillaJaNatürlich was measured with a faint `A_Q`, the shape is the one that would
> survive a stronger dilution. That is an assumption for now, a working hypothesis if you like."*

Restated so it can be refuted: **`D` is invariant to concentration even near the sensor floor.** Three
probes (`diagnostics/shape_dilution_hypothesis.py`), and they disagree:

| probe | result | reads as |
|---|---|---|
| **0 · the designed dilution test** (§6.2, Kiendler) | one drop moves the shape **17.7–17.9 %**; two preparations at the same dose agree to **4.45 %** | ⛔ **against** — on a different oil, but it is the only *designed* test on disk |
| **1 · the drift direction** (560–580) | as the fill dissolves, JN moves **toward Steirerkraft** (18.13 → 15.60 %) and **away from all four others** (+1.9 to +6.1 %) | ⭐ **for** — a better-dissolved JN does look more like tier B |
| **1 · the same probe** (540–584) | non-monotone: JN 002 is nearest to *everything*, 003 moves back out | ⚠ **neither** — the trend is the "run 002 is the settled one" pattern of §6.4, not a march |
| **2 · extrapolating the march** | `f` = 1 → 15.60 %, `f` = 2 → 30.10 %, `f` = 4 → 57.41 % | ⛔ **against** — the direction turns away immediately, so the first leg's approach to Steirerkraft is incidental, not a road |

⇒ ⚠ **UNRESOLVED, and it should not be resolved by argument.** The hypothesis is cheap to test
directly and §9.3 is that test. ⚠ Note it also carries a load-bearing consequence: `Ja! Natürlich 001`
is the **least-dissolved** run of a drifting fill (§6.4), so §8.3's reference is the least
representative point of that fill — which is a second, independent reason the tiers may be fitting
the fill rather than the oil.

---

## 9 · What must be measured before this ships

### ⭐⭐ 9.0 THE 2026-08-15 PROTOCOL CHANGE MOVES THIS PRODUCT FORWARD, NOT BACK

⚠ **At first reading it looks like a loss.** `SPEC_capture_quality.md` §16.36 established that the lamp
degrades the sample while measuring it, so §16.34.3d retires 3-runs-per-fill: **one measurement per
fill** is all that is now possible. The tracker loses its within-fill averaging.

⭐⭐ **It is a gain, and the arithmetic says so:**

```
old protocol   3 runs averaged, within-fill sd 0.70   ->  sd of the mean = 0.70/sqrt(3) = 0.40
new protocol   ONE measurement at the algorithm's chosen point
               bounded below by the no-re-seat floor   0.063   (§16.36.6, 10 repeats untouched)
               bounded above by the best archived fills 0.38
               => somewhere in 0.06 .. 0.38, against the old 0.40
```

⇒ **A single clean measurement plausibly MATCHES OR BEATS the old three-run average** — because roughly
two thirds of that average's noise WAS the drift the new protocol removes. This is not precision traded
for simplicity; it is very likely both.

⭐ **And that lands directly on this document's central number.** The alarm band (§10.5's ±1.0 in `Q%`)
is set by σ_fill. A smaller per-measurement noise means either a **tighter, more defensible band** — the
detection claim in §4 scales straight off it — or the same band with real margin underneath it.

⚠ **One NEW term enters σ_fill, and it must be measured rather than assumed.** Damage accumulates while
the fill clears, and clearing time varies between fills:

| clearing time varies by | the damage term varies by |
|---|---|
| ±3 min | 0.05-0.08 units |
| ±5 min | 0.08-0.13 units |
| ±10 min | 0.17-0.27 units |

Against the 0.21 refill floor that is **material but not dominant** — and ⭐ the **zero-dose
extrapolation** of `SPEC_settled_measurement.md` §2.3 is exactly its correction, which promotes that
number from a curiosity to a σ_fill component. ⇒ **the run must log clearing time per fill**, so the
correlation can be checked directly.

⛔ **The condition is unchanged and still open:** all of this says the measurement should be cleaner. It
does not say what σ_fill is. Edwin's own framing — *"under the assumption that the refill tests give
approximately the same metric values"* — names the assumption exactly, and §16.34.3's criterion was
fixed before the data on purpose.

### 9.1 σ_fill — the same run, and it is already HIGHEST PRIORITY

ROADMAP **σ_fill** / **PRIO 2b** (`SPEC_capture_quality.md` §16.34.3) measures across-fill
reproducibility at a fixed dose. ⭐ **That run prices this document's control limit at no extra cost** —
compute `D` between fills as well as `M448`, from the same captures. Pre-registered, in §16.34.3's form:

| across-fill `D` measured | claim | verdict |
|---|---|---|
| ≤ 3 % | *"detects a 5 % shape change"* | strong |
| ~5 % | *"detects an 8 % shape change"* | usable |
| ⛔ ≳ 10 % | — | **no shape tracker** — §6.1's refill costs would dominate |

⚠ **The prior**: §6.4's undrifted floor is 1–2.5 %, and §6.1's same-session refills cost 4.5–6.8 %.
So the expected answer is in the "strong to usable" band — but every one of those numbers comes from
fills that were never *prepared* as a reproducibility test, which is the whole reason to run it.

### 9.2 ⭐ The spike test — what converts this into a datasheet number

We do not know what a "fundamental change" is worth in `D` units, and until we do this is an opinion.
**Blend known fractions of a foreign oil (sunflower or rapeseed — cheap, and wildly different in
pigment) into a settled reference oil, and find the smallest fraction whose `D` clears the control
limit.** One evening. It yields the sentence the product needs — *"detects a change of X % against
your own reference"* — and it happens to be the **authenticity/adulteration** question a lab already
charges money for (`SPEC_wirtschaftliches.md`: the lab-as-channel-partner is the key).

### 9.3 ⭐⭐ The Ja! Natürlich dilution ladder — one evening, and it settles §8.4 *and* §8.3

**The same Ja! Natürlich oil at 1×, 2× and 3× nominal dose**, three fills each, one session, one
exposure state, standardised settle, dose held by capillary. It answers three things at once:

1. ⭐ **§8.4's hypothesis directly** — does the shape at 3× dose equal the shape at 1×? If `D(1×, 3×)`
   sits at the §6.4 floor the hypothesis holds; if it reaches the 18 % the Kiendler triple showed, it
   is dead and the weak-fill shape is a concentration artefact.
2. ⭐ **Whether §8.3's tiers survive their own reference.** A 2–3× JN fill clears the `B_Q ≥ 0.065`
   break of §16.34.1, so the same tier assignment can be recomputed from a reference that is *not*
   below the sensor floor and *not* the least-dissolved run of a drifting fill.
3. ⭐ **`σ_fill` for one oil**, free — three fills per dose is exactly §9.1's design at one dose.

⚠ It does **not** replace §9.1 (which needs several oils) or §9.2 (which prices a *foreign* change
rather than a dose change). ⭐ But it is the cheapest run on this page, it settles the question Edwin
actually asked, and its 1× arm is directly comparable with the 2026-08-12 archive.

### 9.4 Smaller open items

- **Justify the window** on more than 18 runs — §7.2's choice rests on 13/18 vs 11/18.
- **`k ≥ 5` in practice**: how many presses is a mill actually willing to bank as its reference?
- **Symmetry of the band** (§7 open item).
- **Does `D` survive a lamp rebuild?** ⛔ Assume not (§7.5); the imminent rebuild
  (`SPEC_lamp_rebuild.md`) is the chance to measure it rather than assume it.

---

## 10 · The scripts

All under `diagnostics/`, all reproducing every number in this document:

| script | produces |
|---|---|
| `shape_similarity.py` | §3's definition in code; §5.1, §5.2 — the floor, and the PC1 collapse |
| `shape_refill.py` | §6.1, §6.2 — refill cost, and the Kiendler one-drop result |
| `shape_alarm_test.py` | §8.1 — Edwin's test literally, all-18 generalisation, §3.3's residual curve |
| `shape_derivatives.py` | §6.3 — curve vs slope vs curvature |
| `shape_drift_signature.py` | §6.4 — drift vs noise, and the straightness statistic |
| `shape_tiered_alarm.py` | §8.3 — the three-tier alarm, its pinned config, and the out-of-sample fills that break it |
| `shape_dilution_hypothesis.py` | §8.4 — the three probes on Edwin's working hypothesis |
| `oil_shape_panel.py` | §2's figure → `spectracs-references/tmp/oil_shape_panel.png` |

```
PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
    ./venv/bin/python diagnostics/<script>.py
```

---

## 11 · ⛔ What this document does NOT establish

1. ⛔ **Not a discrimination result.** §5.2 fails the same wall as §16.30.7g. Nothing here says the
   shape distance can tell one oil from another as a general claim.
2. ⛔ **Not validated against anything a customer cares about.** `D` fires on *any* change — roast,
   variety, storage, extraction temperature, and a dosing slip. Whether a detected change matters is
   §16.31.4's gap, untouched. ⇒ The framing must stay **deviation alarm**, never *quality meter*.
3. ⛔ **`n` is small and opportunistic.** Six oils, three runs, one fill each for §5; four products
   with repeat fills for §6, none of them prepared as a reproducibility test. The floor rests on
   **one** undrifted fill.
4. ⛔ **One instrument, one operator, one rig state.** Nothing here has crossed a rebuild.
5. ⛔⛔ **§8.3's three-tier alarm is a fitted hypothesis, not a finding.** 1 window chosen from 105,
   margins at the instrument floor, and the same product lands in two different tiers depending on
   which fill is measured. It is pinned so §9.3 can refute it. ⚠ The **two-tier** alarm of §8.1 does
   not share this weakness — one threshold, +16.05 % margin — and is the only alarm form this
   document puts forward.
6. ⚠ **§16.34's scalar tracker is not superseded** — see §4. If only one ships, the scalar has the
   longer evidence base; this one has the wider aperture.

---

---

## ⭐⭐ 11 · THE UNIT IS A PRODUCT-LINE EPOCH — not a batch, and not one measurement  *(Edwin, 2026-08-18)*

> ⚠ **Scope: the SCALAR tracker of §4** (`Q%`, the shipped `V` form) — not `D`. Every figure is in `Q%`
> units, from series F (`SPEC_settled_measurement.md` §28: five separate preparations of one oil in one
> evening, read under §29's corrected rule). ⭐ The arithmetic of §11.4 is metric-agnostic and carries over
> to `D` unchanged; ⛔ the σ does not. Do not read a `Q%` band as a `D` band.

### ⛔⛔ 11.1 THE BATCH IS THE WRONG UNIT — Edwin's objection, in numbers

*"I think that one batch should not differ by that band"* — and *"if a batch would only involve, say, 10
presses, the history tracker only gives insight in hindsight."* **Both are correct, and together they
retire the per-batch reference.**

| | |
|---|---|
| within-batch scatter (fill to fill) | **σ = 0.277** |
| a ±0.85 band against that | 3.1 σ ⇒ fires **0.2 %** of the time |

⇒ on a homogeneous batch the alarm **never speaks**. A 10-press batch would spend 3–5 presses building a
reference **in order to buy silence**, and by the time anything could be said the batch is pressed, bottled
and gone. ⛔ **That is not a tracker, it is a ritual** — and the "hindsight" charge lands exactly.

### ⭐⭐ 11.2 THE UNIT THAT WORKS — a PRODUCT-LINE EPOCH

Edwin's design: the miller opens an epoch — say **`SparSBudget_Autumn2026`** — and every pressing of that
product line is measured into it. **The reference accumulates across the epoch; each new pressing is an
observation against it.**

| a new pressing judged on | comparison σ | at ±0.85 | band for 3 σ |
|---|---|---|---|
| **1 fill** vs a 20-fill epoch | 0.284 | 3.0 σ | 0.85 |
| 2 fills | 0.205 | 4.1 σ | 0.62 |
| **3 fills** | 0.172 | 5.0 σ | 0.51 |

⭐ **And there is plenty to see at that level.** Different green oils scatter by **1.167**
(`SPEC_v_metric_integration.md` V0) — **4.2× the within-batch noise** — so a genuine step between pressings
is **4.1 σ on a single fill** and 6.8 σ on three.

⇒ three things fall out, and they are the whole argument:
1. ⭐ **A new pressing is judged on its FIRST fill — before it ships.** Prospective, not hindsight.
2. ⭐ **Nothing is spent on ritual.** The fills that would have established a *batch* reference instead
   deepen the *epoch's* reference; every measurement makes the next one sharper.
3. ⭐ **It no longer matters how many presses a batch contains** — the question Edwin could not answer, and
   with the reference at product level the design does not need it answered.

### ⭐⭐ 11.3 THE EPOCH IS THE COMPARABILITY SCOPE — which is why it is more than a label

An epoch is not a name for a time span; it is **the set of conditions under which two numbers may be
compared at all**. It therefore records what it was measured under:

```
ProductLineEpoch  SparSBudget_Autumn2026
   ├─ seed lot / harvest            a new harvest is a NEW NORMAL, not a drift
   ├─ instrument + lamp identity    a lamp swap moves the scale 4.84 units (§16.28)
   ├─ protocol version              capillary recipe, bath time
   └─ read-rule + metric version    §29's read, §17.6's capture-decode era
```

⭐ Then **§7.5's "a chart cannot cross a rig change" stops being a sentence someone has to remember and
becomes a thing the software cannot do**: the chart refuses to plot across an epoch instead of drawing a
cliff. ⛔ The 2026-07-29 rebuild already broke comparability once (§6.1/§16.11) — with epochs it would have
broken *visibly*.

⛔⛔ **AND THE INTEGRITY RULE THAT MAKES IT WORTH SHOWING TO ANYONE:** if a miller can open an epoch freely,
a miller can also reset one to bury a drift. ⇒ **every epoch change is logged with a reason and is visible
on the chart.** A QC record that can be silently re-based is worth nothing to the third party it exists to
convince, and that third party is the point (§11.5).

### ⚠ 11.4 THE REFERENCE IS A MEASUREMENT TOO — the arithmetic, which survives the change of unit

The reference carries its own error. Built from `n` fills it has standard error σ/√n, so the quantity the
alarm actually tests — **new minus reference** — scatters by **σ·√(1 + 1/n)**:

| reference built from | comparison σ | false alarms at ±0.85 |
|---|---|---|
| ⛔ **1 fill** | 0.391 | **3.0 % — 1 alarm in 33** |
| ⭐ 3 fills | 0.319 | 0.8 % |
| 5 fills | 0.303 | 0.5 % |
| 20 fills (a mature epoch) | 0.284 | 0.3 % |
| the true mean | 0.276 | 0.2 % |

⇒ **a single-fill reference inflates the noise by √2 and the false-alarm rate FIFTEENFOLD.** The band width
is the visible parameter; **how the reference was built matters as much, and was left implicit** until this
section.

⛔ **THE WORKED EXAMPLE — and note how the outlier gets chosen.** Edwin asked what happens if **13.5** were
the reference. It is series F's *lowest* of five. Nothing crosses ±0.85, so no alarm fires — but the worst
ORDINARY measurement already consumes **77 % of the band** and the line sits permanently **0.41
off-centre**: a chart showing an oil that drifts upward for ever, because the anchor was an outlier. On the
**mean** of the same five, the worst deviation is **0.406 = 48 %**.
⚠ That outlier was picked by being *first to hand* — so **"the first measurement becomes the reference" is
not a neutral default; it is a coin flip that costs half the band when it loses.**

⇒ ⭐ **the reference is the MEAN of ≥ 3 fills** (5 comfortable, the curve flattens after that — §7.6's
`k ≥ 5` reached from a second direction); ⛔ **never one measurement, never "the first one"**; below three
the tracker says **"reference still forming"** and draws **no band** — a band it cannot honour teaches the
operator to ignore alarms; and the reference's own `n` is shown beside the chart, because the same
deviation means different things at n = 1 and n = 20.

### ⭐⭐ 11.5 WHAT IT IS FOR — it speaks while the gauge still says PASS

⛔ Not quality detection: `SPEC_roast_ampel.md`'s gauge already answers that. The value is **when** it
speaks. A typical green oil sits at **15.94** with **2.66 units of headroom** before the verdict line at
18.6:

| | speaks at | |
|---|---|---|
| the gauge | **18.60** | "this pressing failed" |
| the tracker, 1 fill (±0.85) | **16.79** | 32 % of the way to failure |
| the tracker, 3 fills (±0.51) | **16.45** | 19 % of the way |

⇒ ⭐⭐ **the gauge tells the miller a batch is lost; the tracker tells him the roast is creeping while every
batch still passes.** That is the difference between discarding product and adjusting the oven, and it is
the ordinary reason food producers buy control charts.

⭐ **The second reason is commercial, and it is the stronger one: the epoch chart is a document to hand to
the retailer.** A chain contract is a promise of *consistency*, not merely of quality — "the same as last
delivery". This turns that promise from *trust me* into evidence, continuously, at a fraction of a
per-batch lab certificate. ⇒ it is the first feature that sells to the customer's customer, and the natural
thing for the lab channel partner (`SPEC_wirtschaftliches.md`) to resell as a service layer.

### ⭐ 11.5a WHEN IT STARTS WORKING — the answer is days, not seasons  *(Edwin's cadence, 2026-08-18)*

Edwin's own timing: preparing the dilution ~3 min, warming ~3 min, measuring 5–6 min ⇒ **10–15 minutes**,
which he judges doable **once a day, or once per 1000 litres**. ⭐ At 15 min per 1000 L that is **0.9
seconds per litre** — and the comparison that matters is not per-litre but per-decision: one bad batch
reaching a retail chain costs more than a decade of such measurements.

⇒ at one measurement a day the epoch's reference matures fast, which answers *when the feature starts
paying*:

| after | reference | false alarms at ±0.85 |
|---|---|---|
| **3 days** | 3 fills — the minimum | 0.8 % |
| ~1 week | 5 fills | 0.5 % |
| ⭐ **~1 month** | 20 fills | **0.3 %** |

⇒ **usable in three days, mature in a month, and sharper every week without extra effort.**
⚠ **What that cadence costs**: the quality claim then has 1000-litre granularity, and a mid-batch excursion
is invisible. Edwin's own judgement is that a batch does not vary that much, and §11.1's 0.277 agrees — but
it is the first question a serious buyer asks, so it belongs in the datasheet rather than in a footnote.

### ⭐⭐ 11.5b IT CAN BE VALIDATED WITHOUT THE RIG — which is why it is the low-risk item on the board

⭐ Edwin, 2026-08-18: *"the epoch tracker is only software, and software changes have less surprises than
the physical stuff."* ⚠ The direction is right; the reason is sharper than that. This project's software has
surprised plenty — in one session: a successful measurement silently discarded (§27.25), the clear branch
reporting its most damaged look (§29), `width: 1px` making a gradient invisible (§27.23), and two tests that
could not fail. **The difference is the FEEDBACK LOOP, not the medium**: a physics surprise costs a rig
session and sometimes weeks (§16.36.8's scatter "resisted explanation"); a software surprise costs minutes,
is findable by inspection, and can be *proved* fixed by a test that goes red when the bug is put back.

⭐⭐ **And this feature has a luxury the physics never had: it can be validated entirely OFFLINE against data
that already exists.** Replay series F and the 124 archived reports through the tracker and you can see
exactly what it would have said about every measurement ever made — before it ships, with zero rig time.
⇒ **make that replay the acceptance gate** (§8), not a rig session.
⚠ The one dependency that is not software: the band rests on σ and on epoch discipline. The code will be
right; whether the band is 0.85 or 0.5 is decided by the brown series.

### ⚠ 11.6 Who it is NOT for — stated so the claim stays honest

- ⛔ a farm-gate miller selling to neighbours: the gauge suffices, and the discipline will not be kept;
- ⛔ anyone who will not measure every pressing the same way — **an irregular chart is worse than none**,
  because it trains people to ignore alarms;
- ⚠ it cannot see small drift from one fill. It sees "a third of the way to failure", not "5 % more
  roasted". A real instrument, not a fine one.

### ⛔ 11.7 What still gates it

1. ⛔⛔ **`SPEC_settled_measurement.md` §29 — the read fix — is a PREREQUISITE, not an improvement.**
   Unfixed, the clear branch reports the most lamp-damaged look it saw: 0.013 · 0.037 · 0.084 · **0.482**
   across four fills. ⇒ up to **half a band** of pure artifact, ONE-DIRECTIONAL so no history averages it
   away, and indistinguishable from a real change. It is the one error this tracker cannot survive.
2. ⚠ **Epoch scoping must exist before the first chart is drawn**, or the first lamp change silently
   invalidates a season of data.
3. ⚠ **σ = 0.277 rests on five fills of one oil in one evening** and still contains the unexplained R/S gap
   (§28.5). ⭐ The brown series (§9.1) sets the real number, and every row above moves with it.

---

## ⭐⭐ THE 2026-08-19/20 FINDINGS — what the Billa Clever series says about this spec  *(SPEC_settled_measurement.md §37, §39, §43)*

### ⭐⭐ THE SHAPE DISTANCE WORKS — and an earlier note here said otherwise, wrongly

`D = √(1 − r²)` over 460–630 nm, on each run's promoted capture:

| | pairs | min | median | max |
|---|---|---|---|---|
| **within** Lugitsch A (7 fills, one oil) | 21 | 0.045 | **0.104** | 0.198 |
| **within** Billa Clever (5 fills) | 10 | 0.067 | 0.163 | 0.231 |
| ⭐ **between** the two oils | 35 | **0.338** | 0.384 | 0.476 |

⭐ **No overlap across 45 pairs.** ⛔ A first pass (§37.4) called the tracker *blocked* on the strength of
`D` failing to separate run **002** from the good ones — a **category error**: 002 is the same oil, badly
*prepared*, and a shape alarm is supposed to be blind to it. The turbidity correlation that pass reported
(r = +0.835) was six pairs of the one oil whose fills clear most unevenly; on Lugitsch's 21 pairs it is
**+0.073**. Both claims are withdrawn (§37.7).

### ⭐⭐ BUT `D` AND `Q%` CARRY NEARLY THE SAME INFORMATION — build the SCALAR half for drift

```
D  =  0.0494 · |ΔQ%|  +  0.0897            r = +0.972 over 55 pairs, two oils
```

| | resolves |
|---|---|
| the **scalar** tracker (`Q%`) | **0.076** — measured like-for-like across two separate dilutions |
| the **shape** alarm at D = 0.25 | ≈ **3.2 `Q%` units** |

⇒ ⭐⭐ **the scalar side is ~40× the more sensitive, and `D` is largely a noisier restatement of it.** The
shape half is **not** an independent second opinion on drift. ⭐ Its real job is the *categorical* question —
*is this even the same kind of oil?* (a different pressing, a different supplier, adulteration) — and
⛔ **no such sample exists in the archive, so `D`'s value against its actual use case is UNMEASURED.**

### ⭐⭐ THRESHOLD: PER-OIL, NOT SHARED

⚠ A shared number assumes every oil's within-oil floor stays under ~0.2; an oil whose fills clear as
unevenly as Billa's raises its own floor and starts false-alarming. ⭐ A per-oil threshold, from that oil's
own reference fills, depends on nothing else.

- ⭐ **interim:** the pooled floor — 24 within-oil pairs, max 0.198, against a best between-oil 0.338 ⇒
  ⚠ **0.28–0.30**, not the 0.25 first proposed: with five Billa fills the worst within-oil pair is 0.231.
- ⭐ **switch to the oil's own floor at five fills** — which is this spec's existing "≥3, 5 comfortable"
  ladder, now with a reason attached to each rung.
- ⭐ **three fills DO seed a reference** (the ≥3 floor). What three fills cannot give is the *threshold*, and
  it does not have to come from them.

### ⛔ W5 WAS WITHDRAWN — the last row's spectrum is NOT persisted  *(Edwin, 2026-08-20)*

The answer is read at the `Q%` minimum, i.e. **a different turbidity for every fill** (sd 0.0398 at the
answer against 0.0182 at the last row, 2.2× — figure `figures/w5_two_spectra.png`). Storing the last row's
spectrum too would have tightened the within-oil floor.

⛔ **It is not stored.** `MonitorRow.spectrum` is transient and absent from `toDict()`, so it would have meant
a new `MonitorResult` field, a record key and a persistence change — for the less sensitive half of the
tracker. ⚠ **The cost is sensitivity, not correctness**: the separation above is unaffected.

⭐ **And the honest half comes free:** `valleyAtRead` **is** persisted (built 2026-08-20, §51), so the tracker
can *see* when two spectra were taken at very different clearing states and **flag the comparison** rather
than silently making it.

---

### ⛔⛔ A SOLVENT CHANGE IS INDISTINGUISHABLE FROM AN OIL CHANGE — measured  *(2026-08-21)*

`D` over the archive's labelled sessions plus the four white-spirit fills of
`SPEC_capture_quality.md` §16.12.7f, on **both** windows this document names
(`diagnostics/tracker_d_solvent.py`):

| | 460–630 nm | 550–600 nm |
|---|---|---|
| **within** one oil, one solvent, fill vs fill — *the noise floor* | 0.047 – 0.274 | 0.012 – 0.258 |
| **between** two different oils, same solvent — *the signal* | 0.066 – 0.505 | 0.049 – 0.373 |
| ⛔ **same oil, isopropanol vs white spirit** | **0.326 – 0.466** | **0.430 – 0.572** |
| | 1.3× the alarm | **1.7× the alarm** |

⭐ **On 550–600 nm the solvent change is LARGER than any oil difference in the archive**; on 460–630 it
sits inside the range two different oils span. Either way it clears the `D = 0.25` alarm comfortably.

⇒ ⭐⭐ **This is the operational argument for never changing the solvent, and it stands on its own.** A
history tracker is a **longitudinal** instrument: a protocol change does not degrade the history, it
**deletes** it — every archived point becomes incomparable, the reference lot must be re-measured and the
threshold re-derived. `DOC_sample_physics.md` §4.9 makes the chemical case for isopropanol; this one needs
no chemistry at all.

⚠ **And one number here is a warning, not a reassurance.** The within-oil floor reaches **D = 0.274** —
*above the alarm*, on one oil in one session, fill against fill. The fills inflating it are the turbid
ones. ⇒ the emulsion is also this tracker's largest noise source, and the fix is **settling discipline**
(`SPEC_settled_measurement.md` §40's drawdown rule), **not** a change of solvent.

⭐ Frame: `DOC_metric_algebra.md` §1.5a — *the less you explain, the more you must control.*

## ⭐⭐ THE 2026-08-27 POSITION — `±20` is nearly earned, and the condition is the BASELINE, not the tolerance

`SPEC_red_ratio_metric.md` §12.8 · `ROADMAP.md` §0

Sunflower fill means for the two oils that have several, `20260826EstererD` set aside (§12.8.4):

```
Lugitsch  all 5 fills   119.8  114.3  98.9  100.8  107.2     sd 8.86   range 20.9
          08-26 only            98.9  100.8  107.2           sd 4.37   range  8.4
Esterer   3 fills         77.5   90.2   88.5                 sd 6.90   range 12.7

08-26:  Lugitsch 102.3  vs  Esterer 85.4     gap 16.9    pooled sd 5.78
single fills:   Esterer max 90.2  |  Lugitsch min 98.9   clear gap 8.7
```

⭐ **Single fills of the two oils no longer overlap.** That is new, and it is the thing this spec has been
waiting for — the ±20 band needs σ_fill ≤ **6.7** to be a 3σ alarm, and Esterer sits at 6.90 with recent
Lugitsch at 4.37.

⛔⛔ **BUT NOT AGAINST THE ARCHIVE AS IT STANDS, AND THIS IS THE DESIGN POINT.** Lugitsch's five fills span
**20.9** — so a ±20 tracker whose reference set is built from the existing history **would fire on Lugitsch's
own scatter**. That span is old recipe and old lamp; restricted to 08-26 it is 8.4.

⇒ **The tracker is viable if and only if its reference set is rebuilt under the current recipe.** Not derived
from the archive. This is not a tolerance question and no choice of threshold repairs it: a baseline is a claim
about an oil measured on a particular instrument under a particular preparation, and this archive contains at
least three of each.

⭐ **The σ_fill run IS the baseline run** (`ROADMAP.md` §0). Budget ~5 fills per oil: at σ = 4.37, three fills
pin an oil's mean to ±2.5 and five to ±2.0, which is what a ±20 band needs underneath it. ⛔ And it must carry
`ROADMAP.md` §0b's instrument fields, or the baseline is anchored to a camera state nobody can reconstruct and
the evening has to be repeated.

⚠ **Two fills is a hint, not a result.** The strongest evidence that the recipe change helps is `EstererB`
against `EstererE` — 1.73 apart, with within-fill run scatter of 1.8 and 2.9, i.e. **indistinguishable**. That
is two fills. σ_fill with 5 df is what turns it into a number.
