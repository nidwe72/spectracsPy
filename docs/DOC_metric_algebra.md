<!--
MASTER DOCUMENT — Spectracs metric algebra.
This markdown file is the SOURCE OF TRUTH. The PDF is generated from it:

    python3 docs/tools/build_metric_algebra_pdf.py
    -> ../spectracs-docs/internal/Spectracs_MetricAlgebra.pdf

Never hand-edit the PDF. Edit here, re-run, commit both.
This is DOCUMENTATION, not a specification: it explains what the shipped code computes. It creates no
work items. Where something is open it says so and points at the spec.

Every number in this document is produced by the diagnostics named in Appendix C, which call the
SHIPPED code paths rather than re-implementing them.
-->

# From Spectrum to Verdict

*What the DEV plugin computes, the physics underneath it, and which of the numbers deserve to be believed.*

**Why this document exists.** The evaluation tab shows roughly twenty numbers. One of them decides the
verdict; most of the others are historical, and at least one is inverted with respect to its name. This
document writes down what each is, in formulas, so that reading a report does not require reading the
source — and puts the physics beside the algebra, because the metric only makes sense with both.

**Its companions.** *Capture Fidelity* covers the instrument — how a webcam becomes a spectrum.
*Light, Pigment and Solvent* covers the sample — what is in the jar and what it does to a photon. This
one starts where those finish, at the absorbance curve $A(\lambda)$, and ends at the verdict.

**How to read it.** Chapter 1 stands alone and contains the claim. Chapter 3 is the physics, chapter 5
the metric that matters; if you read only two, read those. Chapters 6–7 are colour and caveats.
Everything historical has been moved to the appendices.

**A note on the worked numbers.** Two data sets carry every example:

| | set | oil | runs | provenance |
|---|---|---|---|---|
| **green** | `20270729C` | fresh green | 6 re-seats of one fill | `SPEC_capture_quality.md` §16.11.3 |
| **brown** | `20260731A` | brown | 6 re-seats of one fill | §16.13, "series D" |

Both are post-rebuild: same instrument, protocol and dilution recipe. They are the most directly
comparable green/brown pair on record. Quoted values are the **mean of the six runs**.

<!--TOC-->

<!--PAGEBREAK-->

## 1. The claim

### 1.1 The winning metric

One number decides the verdict. It is the **Pigment Index** — internally
`Pigment ratio · linear baseline`:

```math
\op{Pigment Index} = \frac{B_{Soret}}{B_{Q}}
  B_{X} = mean absorbance in band X, measured above a baseline fitted through two anchor windows (§5).
```

with $B_{Soret}$ over **440–460 nm** and $B_{Q}$ over **560–580 nm**, both read on the de-spiked
absorbance after subtracting a straight line fitted through **520–540** and **620–630 nm**.

> ⭐ **The far anchor moved from 600–630 to 620–630 on 2026-08-03** (`SPEC_capture_quality.md` §16.20).
> **This document is written throughout on the shipped 620–630 window**; §5a records what the move changed
> and why, and is the only place the old window's numbers appear as a live comparison. Two consequences
> worth carrying into every table below: the **scale moved**, so no threshold survives the change
> untouched; and `r_Q`, the pedestal residual, belongs to its anchor and moved with it (§5a.2).

### 1.2 What it achieves

| | green `20270729C` | brown `20260731A` |
|---|---|---|
| **Pigment Index** | **15.499 ± 0.714** | **10.160 ± 0.197** |
| at the shipped threshold **T = 12.5** | **+4.20 σ** above | **+11.87 σ** below |

The gap is **5.339 = 52.5 % of the brown mean**, against a pooled σ of 0.524 — **Cohen's *d* = 10.20**.

**The two classes do not overlap, on any run, in either set.**

### 1.3 What Cohen's *d* means

The figure is used throughout this document, so it is worth defining once. A raw gap between two class
means is uninformative on its own: 5.339 units is impressive only if the measurement's own run-to-run
scatter is much smaller than that. **Cohen's *d*** divides one by the other:

```math
d = \frac{\bar{x}_{1} - \bar{x}_{2}}{s_{pooled}}, \qquad s_{pooled} = \sqrt{\frac{s_{1}^{2} + s_{2}^{2}}{2}}
  the difference between the two class means, in units of their pooled standard deviation.
```

The subscripts 1 and 2 label the two groups being compared — here **1 = green, 2 = brown**:

| symbol | meaning | value here |
|---|---|---|
| $\bar{x}_{1}$ | the **mean** of group 1 — the average of green's six runs | 15.499 |
| $\bar{x}_{2}$ | the **mean** of group 2 — the average of brown's six runs | 10.160 |
| $s_{1}$ | the **standard deviation** of group 1 — how much green's runs scatter about their own mean | 0.714 |
| $s_{2}$ | the standard deviation of group 2 — brown's scatter | 0.197 |
| $s_{pooled}$ | the two scatters combined into one, as the root-mean-square of $s_{1}$ and $s_{2}$ | 0.524 |

So $d = (15.499 - 10.160) / 0.524 = 5.339 / 0.524 = 10.20$. Note that only the **standard deviations**
enter, not the sample sizes: *d* describes how far apart the two *populations* look, not how confident we
are about it. Confidence comes from n, and is handled separately in §5.8.

Read out loud, it is **"how many standard deviations apart the two groups are"**. It is dimensionless,
so it does not care what units a metric carries, and it is therefore directly comparable **between rival
metrics**. That is why every metric in this document is scored with it.

| *d* | conventional reading | overlap of two normal distributions |
|---|---|---|
| 0.2 | small effect | almost complete |
| 0.5 | medium | heavy |
| **0.8** | **large** | substantial |
| 3 | very large | the distributions barely touch |
| **10.20** | **our Pigment Index** | **none observed** |

**Our *d* = 10.20 means the class means sit ten pooled standard deviations apart** — which is why no run
of either set comes near the other's range.

⚠ Three reading notes. With n = 6 per class the *value* of *d* is loosely estimated, even though its sign
and rough size are not in doubt; §5.8 gives the interval that actually matters. A **negative** *d* in this
document means the ordering is **inverted** — brown reading higher than green. And *d* comes in more than
one recipe: **Appendix B** gives both pooled-SD conventions, the small-sample correction, and which is
used where.

#### The same idea outside statistics

The identical construction is standard in several other fields under other names — worth knowing, because
a reader from any of them already understands the figure. The neutral, field-independent term for the
whole family is the **standardised mean difference (SMD)**; Cohen's *d* is one recipe within it
(Appendix B).

| name | field | relation |
|---|---|---|
| **d′ ("d-prime")** | signal detection, psychophysics | the same quantity; the sensitivity of a detector |
| **Fisher's discriminant ratio** | pattern recognition | $J = d^{2}/2$ — here 60.9 |
| **Z-score, "sigma level"** | process control, Six Sigma | distance from a *limit*, not between two groups |
| **peak resolution** $R_{s}$ | chromatography | separation ÷ typical width — the same shape of idea |

**The Z-score row is already in use here without the label**: the **"+4.66 σ above T"** and
**"+9.88 σ below T"** of §1.2 are Z-scores — one group measured against a threshold, rather than two
groups against each other.

### 1.4 Three properties that make the claim worth making

> **1. It is dilution-invariant *by construction*, not by luck.** Every step from the curve to the two
> band means is linear and homogeneous, so concentration and path length cancel exactly in the
> quotient. This is proved, not asserted (§5.6). It means the recipe can change without recalibrating
> the verdict.
>
> **2. It is a ratio of two chemical SPECIES, not a measure of "how much pigment".** What it tracks is
> intact protochlorophyll against its magnesium-free degradation product protopheophytin. Across our
> two classes the *total* Q-region absorbance is identical (0.2300 vs 0.2251) while the shape differs
> at *d* = 10.3 — nothing is missing, something has been **converted** (§3.3).
>
> **3. It survives the instrument.** Lamp brightness, camera gain, grating efficiency and exposure all
> scale the absorbance uniformly and divide straight out. A €30 webcam can carry it.

**⇒ Green-versus-brown discrimination works.** That is the claim, and §5.8 is where it is defended.

### 1.5 What the claim is *not*

⚠ **Precision is not correctness.** *d* = 10.20 says the instrument reliably distinguishes *these two
bottles*. Whether **T = 12.5** is the right place to cut the population of real pumpkin oils is a
separate, still-unvalidated question requiring reference oils with independent ground truth
(`SPEC_capture_quality.md` §16.10.11a). A precise instrument reading a wrong threshold is confidently
wrong.

⚠ **These are re-seat numbers.** Both sets are six re-seats of *one fill*, so they exclude sample
preparation entirely. Fill-to-fill scatter remains unmeasured for brown
(`SPEC_capability_proof.md` §11.4f B).

### 1.6 The chain, in one line

```math
2 captures \Rightarrow R(\lambda), S(\lambda) \Rightarrow A(\lambda) \Rightarrow \op{despike} \Rightarrow 4 band means \Rightarrow the index
```

<!--PAGEBREAK-->

## 2. From two captures to an absorbance curve

### 2.1 The burst mean

Each capture is a burst of **150 frames** (`DevSpectralPlugin.FRAMES`). Frames whose overall brightness
is an outlier are rejected, then each wavelength bin is averaged with a sigma-clipped mean:

```math
R(\lambda) = \op{mean}_{f \in F_{kept}} r_{f}(\lambda) \qquad S(\lambda) = \op{mean}_{f \in F_{kept}} s_{f}(\lambda)
  F_{kept} excludes frames rejected by the per-frame MAD test (SPEC_capture_quality.md §14.8 C1).
```

The reference is pure isopropanol in the same jar, measured in the same session. Dividing by it removes
the lamp's own spectrum — the single most important idea in the instrument.

### 2.2 Transmittance, with a floor guard

```math
T(\lambda) = \frac{S(\lambda)}{R(\lambda)} \quad for R(\lambda) > f \cdot \max_{\lambda} R(\lambda), \quad f = 6.31 \times 10^{-5}
```

Where the reference is at or below that fraction of its own peak the wavelength is **masked out
entirely** rather than divided; below the floor $S/R$ amplifies noise without bound. The constant looks
odd because it lives in linear light — it is the historical "1 % of peak" expressed after gamma
decoding, $0.01^{2.2}$ (`SPEC_capture_quality.md` §17).

### 2.3 Absorbance

```math
A(\lambda) = -\log_{10} T(\lambda) = -\log_{10}\frac{S(\lambda)}{R(\lambda)}
  defined only where T(\lambda) > 0; other wavelengths carry no value at all.
```

This is the **Beer–Lambert** quantity, $A = \epsilon c l$ — linear in concentration, which is what makes
ratios of it behave (*Light, Pigment and Solvent* §2.2).

### 2.4 De-spiking

Every metric except the "raw" twin rows is computed on the **de-spiked** curve — a moving median with a
7-point kernel:

```math
A_{d}(\lambda_{i}) = \op{median}\{A(\lambda_{i-3}), \ldots, A(\lambda_{i+3})\}
```

A median *rejects* isolated outliers where a smoothing filter would average them in. The grid spacing is
0.146 nm, so the kernel spans ≈1 nm — narrow enough to leave a 20–30 nm pigment band untouched, wide
enough to kill single hot pixels.

> **⚠ It does not remove the two named instrument artifacts.** Two narrow features near **473 nm**
> (FWHM 1.0 nm) and **607 nm** (FWHM 2.7 nm) are wider than the kernel and survive it. Both are **lamp
> emission lines** that fail to cancel in $S/R$ (§5.9). **Since the far anchor moved to 620–630, both now
> sit outside every measurement window** and both are harmless to the index. On the old 600–630 anchor the
> 607 nm line lay *inside* it — one of the reasons the window moved (§5a.1).

<!--PAGEBREAK-->

## 3. The physics the metric rests on

*This chapter is the short form. The full chemistry — miscibility, turbidity, the vessel — is in*
*Light, Pigment and Solvent*, *whose §3 this compresses.*

### 3.1 The pigment is protochlorophyll, not chlorophyll

Fruhwirth & Hermetter's review of the Styrian oil pumpkin identifies the oil's colourants explicitly:
*"various tetrapyrrol-type compounds like **protochlorophyll (a and b)** and **protopheophytin (a and
b)**, the latter being a protochlorophyll lacking the magnesium ion"* [1].

Protochlorophyll is chlorophyll's biosynthetic **precursor**. It lacks chlorophyll's ring-D reduction, so
it is a **porphyrin** where chlorophyll is a **chlorin** — and that single bond moves the red absorption
band by ~40 nm:

| | Soret | red (Qy) band | fluorescence |
|---|---|---|---|
| chlorophyll *a* *(the textbook default — **not** ours)* | ≈ 430 nm | ≈ 662–665 nm | ≈ 668–675 nm |
| **protochlorophyll(ide) *a*** *(ours)* | **≈ 432–440 nm** | **≈ 623–626 nm** | **≈ 630–636 nm** |

Protochlorophyllide's Qy is measured at **623 nm** in 80 % acetone and **626 nm** in methanol [2], and the
oil's own fluorescence maximum of **635 nm** [1] corroborates it — a fluorescing molecule emits ~10 nm to
the red of the transition it absorbs on, putting the absorber at ~625 nm and nowhere near 662.

**This matters because our capture window ends at 630 nm.** The red band is therefore *at the edge of what
we can see*, not beyond it — which is the whole reason the far window behaves as it does (§3.4), and, once
that was understood, the reason the anchor was narrowed onto **620–630** so as to sit on the band rather
than straddle its foot (§5a.1).

### 3.2 Soret and Q — where the bands come from

All porphyrin-type spectra share one two-part shape, explained by **Gouterman's four-orbital model** [3]:
the visible spectrum is governed by four frontier orbitals, two nearly-degenerate occupied and two
nearly-degenerate empty.

| band | transition | character |
|---|---|---|
| **Soret** (also **B**) | S₀ → S₂ | **very strong**, blue, ~430–440 nm |
| **Q** | S₀ → S₁ | **weak** — 1/5 to 1/10 of the Soret — yellow-green to red |

**In a metallo­porphyrin** the magnesium sits on a four-fold symmetry axis (D₄ₕ). The two Q transitions
are then **degenerate** — equal energy, polarised at right angles in the plane of the ring — and what
appears is one origin band **Q(0,0)** (also α) plus a vibronic satellite **Q(1,0)** (β).

> **"Degenerate" carries no sense of decay.** It means two states happen to share an energy. Symmetry is
> what enforces the sharing, so lowering the symmetry **lifts** the degeneracy and the states separate.

### 3.3 What roasting does — and why it rearranges rather than removes

Heat and acid **strip the central magnesium out of the ring**, replacing it with two protons. The product
is **protopheophytin** (*pheo-*, Greek *phaiós*, "dusky"). It is not only roasting: in pumpkin seeds
protopheophytins accumulate as a **storage** degradation product, reported at **1.1–35.5 %** of the
protochlorophylls [4].

Spectroscopically the two protons sit on **one** axis, so the symmetry drops **D₄ₕ → D₂ₕ**, the degeneracy
is lifted, and the two Q transitions separate into distinct **Qx** and **Qy** bands. Each keeps its own
vibronic satellite, so a metal-free ring shows **four** Q bands, numbered **I–IV from the longest
wavelength**: I = Qy(0,0), II = Qy(1,0), III = Qx(0,0), IV = Qx(1,0).

**⭐ And the redistribution has a known direction.** Free-base porphyrin spectra are classified into four
types by Q-band intensity ordering — *etio* (IV > III > II > I), *rhodo* (III > IV > II > I), *oxo-rhodo*
and *phyllo* [5]. **Band I, the longest-wavelength band, is the weakest in every one of them.** So a
pigment whose long-λ band *dominates* while metallated finds it demoted to weakest-of-four once the
magnesium goes. Intensity moves toward the blue. *(Protopheophytin carries the ring-E carbonyl, a
"rhodofying" group, so* rhodo *is its expected type — band I still weakest.)*

**⇒ The verdict is a ratio of two chemical species**, intact against degraded — not a measure of how much
pigment is present.

### 3.4 ⭐ Why this appears as a change of SLOPE

![**Figure 1** — the mechanism, and the whole of what the baseline does. **Top:** with the magnesium intact, one dominant Q origin sits at the very edge of our capture window, so the far red — and with it the **620–630 anchor** — stands **high**, and the fitted line through the two anchors is **steep**. **Bottom:** once the magnesium is gone that intensity is spread across weaker bands further blue; nothing tall is left near 630, the anchor drops, and the same line goes **nearly flat**. Total area is similar; only its distribution differs. **The two solid bars are the only numbers the metric takes from the curve** — one mean per anchor window — and the dashed line through them is what gets subtracted before Soret and Q are read. ⚠ Schematic: it models the pigment bands only, with no turbidity pedestal, so its contrast is far larger than the measured 1.65×, and its two near anchors differ where the real ones nearly coincide — **compare the right-hand ends.**](figures/pigment_far_window_slope.svg)

> ⚠ **"Slope" means the FITTED BASELINE's slope, which lives *between* the two windows.** It is easy to read
> it as the slope *inside* the far window, and the metric never sees that: `linearBaselineCorrected` reduces
> each anchor to a **single number — its mean absorbance** — and fits a line through the two means. A 10 nm
> window collapses to one value, so its internal shape is averaged away before the fit begins.
>
> What the far anchor contributes is therefore its **height**, and the slope follows from the two heights by
> arithmetic — the table below.

<!-- ⚠ This table must stay OUT of the block quote above: the renderer does not typeset tables inside
     block quotes and they come out as raw pipe characters (caught 2026-08-03 by verifying the built PDF). -->

| | `A_near` 520–540 | `A_far` 620–630 | difference | ÷ 95.0 nm = slope |
|---|---|---|---|---|
| green | 0.1231 | 0.2035 | **0.0804** | 8.46 × 10⁻⁴ A/nm |
| brown | 0.1038 | 0.1526 | **0.0488** | 5.14 × 10⁻⁴ A/nm |

— which reproduces §5.3's fitted **8.56 / 5.22 × 10⁻⁴** to within 1 %, the remainder being the anchor
windows' *internal* slope that the least-squares fit does see and the two-centroid chord does not (§5.5).

> ⚠ **An unresolved tension, visible only at this zoom.** The sourced Qy is **623–626 nm**
> (`KB_spectroscopy_physics.md` §4.1), which would put the band's *maximum* inside 620–630 — yet the measured
> green absorbance **rises monotonically** across the window (+0.0766 A over 10 nm) rather than peaking and
> falling. Either the band shifts red in isopropanol relative to the acetone and methanol values, or the
> lamp's red collapse biases it: the reference reads 39 DN at 620–630 against 130 at 530 (§16.12.11 B), and a
> dim reference inflates absorbance. **Both are testable and neither has been tested.** It matters because
> the shipped anchor sits exactly there — §16.11.17's timed series would see it for free, as would any run
> that logs the reference level per bin.

Our far window is **narrow and sits on a flank, not on a peak**. The slope across such a window
reports **the height of the nearest peak**, not the total pigment. A tall band whose edge crosses the
window gives a steep rise; move that intensity 30–50 nm blue and split it, and the window is left on flat
ground even though just as much light is absorbed overall.

That makes the far window an unusually **specific** probe: it responds to *whether the intact, symmetric
pigment is still there*, and is comparatively blind to how much total pigment the oil contains.

### 3.5 The far window is a measuring band — measured, not assumed

The far window was introduced as an "oil-quiet" anchor. It is not quiet. Across 37 runs, six fills and
two sessions under an identical lamp, the *rise* $A(620\!-\!630) - A(600\!-\!610)$ is **0.0535 for green
against 0.0159 for brown — a 5.1 σ separation** (`SPEC_capture_quality.md` §16.12.12). The reference sits
at 35–39 DN in both classes, so the lamp is in the same state: an instrument artifact cannot know which
oil is in the jar.

**And it is load-bearing.** Sweeping the far window's right edge inward, Cohen's *d* falls **2.88 → 0.94**
and the classes overlap outright by 600–610 nm (§16.12.13). The contamination *carries* the
discrimination.

> ⭐ **Both measurements above were made across 600–630**, the anchor of the day, and the shipped window is
> its red third. They are quoted unchanged because the direction they establish is what motivated the
> narrowing: the further red the window reaches, the more of the intact pigment it sees. §4.2 shows the
> shipped 620–630 window separating the classes by **33 %** — a wider class difference than the 30 nm
> window it replaced, from a third as many points.

> **⛔ Changing these windows is a metric redesign, not a tidy-up**, and it is gated on post-rebuild data
> (`SPEC_capture_quality.md` §16.12.16).

### 3.6 The difference is speciation, not concentration — and the test has no free parameters

Under simple Beer–Lambert with one absorbing species, brown = *k* × green: the curves differ by **one
scale factor**, so any ratio of two features taken *inside* the Q region is class-independent. A class
difference in such a ratio refutes pure scaling outright.

| | green | brown | *d* |
|---|---|---|---|
| `A_Q` 560–580 | 0.2300 ± 0.0173 | 0.2251 ± 0.0199 | **0.26** — equal |
| Q amplitude (572 − 550) | 0.1275 | **0.1495** | **−3.16** — brown HIGHER |
| **rise ÷ Q-amplitude** | **0.4274 ± 0.039** | **0.0800 ± 0.028** | **10.26** |

**Pure scaling predicts *d* = 0 on the last row. Measured *d* = 10.26, a factor of 5.3.** Brown is not
pigment-poor — `A_Q` is equal and its 572 feature is *stronger*. Normalising each class by its own Q
amplitude shows where the intensity went: **out of 615–630 (−0.193) and into 580–615 (+0.07 to +0.11)**,
exactly the direction §3.3's band-I rule predicts. *(`diagnostics/qband_shape.py`;
`SPEC_capture_quality.md` §16.13.9.)*

### 3.7 ⚠ Why we cannot simply look at the two-versus-four bands

The natural objection is that a better spectrometer would settle all of this. **It would not:**

| | |
|---|---|
| grid spacing | 0.146 nm/bin, 1305 bins over 440–630 |
| narrowest feature resolved *(473 nm lamp line)* | **FWHM 1.0 nm** |
| second lamp line *(607 nm)* | **FWHM 2.7 nm** |
| Q bands to be separated | **20–30 nm wide** |

The rig **out-resolves the target by 10–20×**. Four other things stand in the way: **window truncation**
at 630 nm (the dominant limit); the two species **always coexisting**, so no pure spectrum of either is
ever presented; **20–30 nm intrinsic linewidths** merging the four free-base bands into shoulders; and the
**turbidity pedestal** suppressing contrast.

**⇒ The remedy is a wider window, not a finer instrument** — an argument that redirects an entire class of
"buy better hardware" thinking toward a much cheaper change.

<!--PAGEBREAK-->

## 4. The windows and the band means

Everything downstream is built from four wavelength windows — two pigment bands and two baseline anchors.

| symbol | window | what it sits on | source |
|---|---|---|---|
| $A_{Soret}$ | **440–460 nm** | red flank of the **Soret (B)** band, ~432 nm | `PB_SORET_BAND` |
| $A_{Q}$ | **560–580 nm** | a band in the **Q region** — assignment open, §7.4 | `PB_Q_BAND` |
| $A_{near}$ | **520–540 nm** | between bands — the quieter anchor | `PB_BASELINE_WINDOWS[0]` |
| $A_{far}$ | **620–630 nm** | **on** the **Qy(0,0)** band, ~623–626 nm — a *measuring* band (§3.5) | `PB_BASELINE_WINDOWS[1]` |

![**Figure 2** — the de-spiked absorbance of both classes, with the four windows shaded and each curve's own fitted baseline drawn dashed. The lower panel magnifies the weak-absorbance region — **no part of this window is signal-free** (§3.5). Note how little separates the two curves inside the Q window, and how much separates them inside the far window.](metric_algebra_bands.png)

### 4.1 Windows and band means — the notation used from here on

A **window** is a wavelength interval. Write $W_{X}$ for the *set of measured grid points* that fall
inside window $X$:

```math
W_{X} = \{\lambda : lo_{X} \le \lambda \le hi_{X}\}
  read: "all wavelengths λ between the window's lower and upper edge". |W_{X}| is how many there are.
```

So $W_{Soret}$ is the 138 grid points between 440 and 460 nm, $W_{far}$ the 71 points between 620 and
630 nm, and so on. The **band mean** is then simply their average:

```math
A_{X} = \frac{1}{|W_{X}|} \sum_{\lambda \in W_{X}} A_{d}(\lambda)
  the sum of the de-spiked absorbance over the window's points, divided by their number.
```

A plain unweighted mean of every surviving grid point — **not** an integral. For two 20 nm bands the
choice makes no difference to the ratio, and a mean keeps the same unit as the other band readings, where
an integral would inject a bandwidth factor into the unequal-width comparisons
(`SPEC_pumpkin_peak_ratio_eval.md` §9).

### 4.2 Geometry and measured values

| window | points | centroid $\bar{\lambda}$ | green | brown | CV green | CV brown |
|---|---|---|---|---|---|---|
| Soret 440–460 | 138 | 449.98 nm | 1.1864 | 1.0855 | 4.04 % | 3.58 % |
| Q 560–580 | 137 | 570.02 nm | 0.2300 | 0.2251 | 7.52 % | 8.86 % |
| near 520–540 | 135 | 529.93 nm | 0.1231 | 0.1038 | 8.89 % | 13.31 % |
| **far 620–630** | **71** | **624.96 nm** | **0.2035** | **0.1526** | 12.99 % | 14.54 % |

The centroids matter in §5.5. **Read the $A_{Q}$ row**: 0.2300 against 0.2251, a 2 % difference against
7–9 % scatter. On its own the Q band carries no usable class information (*d* = 0.26).

**Now read the $A_{far}$ row against it.** 0.2035 against 0.1526 — the two classes differ by **33 %** in
the window that was introduced as a *baseline anchor*. That is the largest class difference of any window
in the table, and it is why §3.5 calls the far window a measuring band. The 620–630 window is only 10 nm
wide and holds a third as many points as its 600–630 predecessor, yet it separates the classes better,
because it stands **on** the Qy band instead of straddling its foot (§5a.1).

<!--PAGEBREAK-->

## 5. ⭐ The Pigment Index — the metric that works

### 5.1 What problem the baseline solves

Re-seating the jar tilts the beam slightly, and that enters the absorbance curve as **an offset and a
slope together** — the whole curve lifts *and* rotates. A constant subtraction removes the offset;
standard normal variate removes offset and scale; **neither removes a slope.** A straight line fitted
through two separated anchor windows removes both (`SPEC_capture_quality.md` §16.10.2).

### 5.2 The definition

Take every grid point inside **either anchor window** — $W_{near}$ (520–540 nm, 135 points) and
$W_{far}$ (620–630 nm, 71 points), in the notation of §4.1 — and fit **one straight line** through all
206 of them at once.

The line is $A = m\lambda + c$, with **$m$ its slope** in absorbance per nanometre and **$c$ its
intercept** — the value the line would take at $\lambda = 0$ nm. The intercept has no physical meaning on
its own; it is simply the second number needed to pin a line down once the slope is chosen. What matters
is the line's *value across our window*, which §5.3 tabulates.

The fit is **weighted least squares**, with each of the two windows carrying **equal total weight**
regardless of how many points it contains. *(What that means and why squares: Appendix A.)*

Subtract the fitted line from the **whole** curve, re-read the two pigment bands on the corrected curve,
and divide:

```math
B(\lambda) = A_{d}(\lambda) - (m\lambda + c)
```

```math
B_{Soret} = \frac{1}{|W_{Soret}|}\sum_{\lambda \in W_{Soret}} B(\lambda) \qquad B_{Q} = \frac{1}{|W_{Q}|}\sum_{\lambda \in W_{Q}} B(\lambda)
```

```math
\op{Pigment Index} = \frac{B_{Soret}}{\max(B_{Q},\, \epsilon)}, \qquad \epsilon = 10^{-3}
  the epsilon is a division guard, never reached in practice.
```

### 5.3 What the correction does to each band

Measured fits, mean over each set:

| | slope $m$ | intercept $c$ | baseline under Soret | baseline under Q |
|---|---|---|---|---|
| green | +8.563 × 10⁻⁴ A/nm | −0.3312 A | 0.0541 | **0.1569** |
| brown | +5.216 × 10⁻⁴ A/nm | −0.1730 A | 0.0618 | **0.1244** |

```math
B_{Soret} = 1.1864 - 0.0541 = 1.1323 \qquad B_{Q} = 0.2300 - 0.1569 = 0.0731 \quad (green)
```

| | $A_{Soret} \to B_{Soret}$ | $A_{Q} \to B_{Q}$ |
|---|---|---|
| green | 1.1864 → 1.1323 *(−5 %)* | 0.2300 → **0.0731** *(−68 %)* |
| brown | 1.0855 → 1.0237 *(−6 %)* | 0.2251 → **0.1008** *(−55 %)* |

**The Soret barely notices; the Q band loses more than half its value.** That asymmetry follows from
geometry — the baseline is a small fraction of a large absorbance and a large fraction of a small one —
and it is the whole story of §5.4.

> **The fitted line is now roughly twice as steep** as it was on the 600–630 anchor (+8.56 against
> +4.81 × 10⁻⁴ A/nm for green). Nothing about the oil changed: the far anchor moved 10 nm redder and
> 33 % higher up the Qy flank, so a line pinned through the same near window has to climb harder to reach
> it. Both lines cross at ≈525 nm, inside the near anchor, which is where two lines fitted through the
> same window must meet.

![**Figure 3** — the same two curves after each has had its own baseline subtracted. The two anchor windows are pinned to zero by construction; everything else is now measured relative to them.](metric_algebra_corrected.png)

### 5.4 ⭐ Why it discriminates — the denominator inverts

| | green | brown | green ÷ brown | *d* | separation |
|---|---|---|---|---|---|
| $A_{Q}$ *(before)* | 0.2300 | 0.2251 | 1.02 | 0.26 | overlap |
| $B_{Q}$ *(after)* | **0.0731** | **0.1008** | **0.73** | **−10.83** | **clean, inverted** |
| $B_{Soret}$ | 1.1323 | 1.0237 | 1.11 | 2.70 | clean |
| **Pigment Index** | **15.499** | **10.160** | **1.53** | **10.20** | **clean** |

Before correction the two classes' Q bands are indistinguishable. After correction the ordering
**reverses** and becomes decisive: brown's corrected Q band is 38 % *higher*, at *d* = −10.83 with no
overlap between the two sets of six runs.

![**Figure 4** — the Q band before and after correction. Left: the curves lie on top of each other inside the shaded window. Right: after each curve's own baseline is removed, brown stands clearly above green. Nothing about the oils changed between the panels — only what the band is measured *above*.](metric_algebra_qzoom.png)

**Why.** The baseline under the Q band differs by class — **0.1569** green against **0.1244** brown — so
green has *more* subtracted. And green's baseline sits higher because $A_{far}$ is 0.2035 against 0.1526:
620–630 *is* intact pigment (§3.5). The causal chain:

```math
intact pigment raises A_{far} \Rightarrow raises the fitted baseline \Rightarrow lowers B_{Q} \Rightarrow raises the index
```

**The two effects multiply:**

```math
\frac{\op{index}_{green}}{\op{index}_{brown}} = \frac{B_{Soret,green}}{B_{Soret,brown}} \times \frac{B_{Q,brown}}{B_{Q,green}} = 1.106 \times 1.379 = 1.525
```

The numerator contributes ×1.11 and the **denominator ×1.38** — the inverted Q band is by far the larger
term, and moving the anchor onto the Qy band nearly doubled its lead (it was ×1.20 on 600–630). A
*d* = 2.70 numerator and a *d* = −10.83 denominator compose into *d* = 10.20.

> ⚠ **Why the composed *d* is not simply bigger.** Both components improved, and the class gap grew from
> 31.7 % to 52.5 % of the brown mean — yet *d* slipped from 11.04 to 10.20 on this pair, because the
> **scatter grew too**: green's run-to-run CV went 2.89 % → 4.61 %. A 10 nm window collects a third as
> many points as a 30 nm one and sits in the lamp's dimmest stretch, so it is noisier. On the spec's
> pooled-green basis the comparison comes out the other way (*d* 9.80 → **10.35**, `SPEC_capture_quality.md`
> §16.20.4) because pooling two fills adds fill-to-fill scatter, which cost the old anchor more than the
> new one. **Both are measured; neither transfers to the other's data set.** See §5.8.

**This is why the uncorrected ratio fails** (Appendix D.1): it divides a signal-bearing Soret band by a Q
band that carries nothing. Only after the baseline is removed does the denominator become a
discriminator — and then the dominant one.

### 5.5 The three-region identity

Because the baseline is a straight line read at the band centroids, the metric can be written without
mentioning a baseline at all. With $t_{X}$ the position of band $X$ between the anchor centroids:

```math
t_{X} = \frac{\bar{\lambda}_{X} - \bar{\lambda}_{near}}{\bar{\lambda}_{far} - \bar{\lambda}_{near}} \qquad t_{Soret} = -0.841 \qquad t_{Q} = +0.422
```

```math
B_{X} \approx A_{X} - \big[(1 - t_{X})\,A_{near} + t_{X}\,A_{far}\big]
```

```math
\op{Pigment Index} \approx \frac{A_{Soret} - 1.841\,A_{near} + 0.841\,A_{far}}{A_{Q} - 0.578\,A_{near} - 0.422\,A_{far}}
  Verified against the shipped code: max error 0.02 % (green), 0.05 % (brown).
```

**Read the signs.** $A_{far}$ enters the numerator **positively** and the denominator **negatively** —
both *raise* the index. This is not "Soret over Q with a correction"; it is a **three-region measurement**
in which the red window participates twice, with the largest coefficient of any numerator term save the
Soret band itself.

> **Why the identity is now all but exact.** The real fit is a least-squares line through ~206 points and
> is **steeper** than the naive two-centroid chord — but only by **+1.2 % (green) and +1.6 % (brown)**,
> against +13.8 % / +5.4 % on the 600–630 anchor. The excess steepness comes from the anchor windows'
> *internal* slope, and a 10 nm window climbing the Qy flank has far less of it to contribute than a
> 30 nm one. With the chord and the fit nearly coincident, the identity's error falls to **0.02 %**.
>
> ⚠ This improvement arrives **despite** the geometry getting worse, not because of it. The windows'
> weighted centroid moved from 572.5 nm to **577.5 nm** while the Q band stays at 570.0 — so the extra
> steepness now pivots **7.4 nm** from the Q band rather than 2.5 nm, and no longer cancels there. It
> simply has almost nothing left to pivot *with*. The old anchor's identity held by a lucky cancellation;
> this one holds because the two lines are nearly the same line.

### 5.6 ⭐ Dilution invariance — the proof

Model the curve as pigment plus a scattering pedestal that does **not** track concentration:

```math
A(\lambda) = \epsilon(\lambda)\,c\,l + P(\lambda)
  \epsilon extinction, c concentration, l path length, P the turbidity pedestal.
```

Take $P = 0$ for a moment. Every step from the curve to the two corrected band means — the band mean, the
least-squares fit, the subtraction — is **linear and homogeneous** in the data. So scaling the input
scales the output identically:

```math
B_{X} = c\,l\,\big(\bar{\epsilon}_{X} - \ell_{\epsilon}(\bar{\lambda}_{X})\big) \equiv c\,l\,e_{X}
```

```math
\op{Pigment Index} = \frac{c\,l\,e_{Soret}}{c\,l\,e_{Q}} = \frac{e_{Soret}}{e_{Q}}
```

$c$ and $l$ are gone. A degree-1 homogeneous functional over a degree-1 homogeneous functional is
degree-0. **This is invariance by construction, not by approximation.**

> **One step is exact and is easily mistaken for an approximation.** $B_{X} = A_{X} - L(\bar{\lambda}_{X})$
> holds *exactly*, because the mean of a straight line over a window equals that line at the window's
> centroid. The only approximation in §5.5 was the slope.

**The proof never mentions chlorophyll.** It uses only that a component scales with $c$ — so §3.5's
far-anchor pigment contamination is **harmless to invariance**. It changes what the metric *means*
chemically; it does not change whether it is invariant.

### 5.7 What breaks invariance — pedestal curvature, and nothing else

Restore $P$. The fit is linear, so it splits:

```math
B_{X} = c\,l\,e_{X} + r_{X}, \qquad r_{X} = \bar{P}_{X} - \ell_{P}(\bar{\lambda}_{X})
  r_{X} = the pedestal's departure from its OWN best-fit line, at band X.
```

| pedestal | invariance |
|---|---|
| $P = 0$ | exact |
| $P$ exactly **linear** in λ | **also exact** — the fit removes it completely, $r \equiv 0$ |
| $P$ curved | broken, in proportion to $r$ |

**So invariance fails only to the extent that turbidity is non-linear across 440–630 nm.** Scattering goes
roughly as $\lambda^{-n}$ and a line approximates a curve; that curvature is the *entire* residual error.

**The sensitivity, and the denominator is hit ten times harder again:**

```math
\frac{d \ln (\op{index})}{d \ln c} \approx \frac{r_{Q}}{B_{Q}} - \frac{r_{Soret}}{B_{Soret}} \approx \frac{r_{Q}}{B_{Q}}
```

The second term drops because $B_{Soret}/B_{Q}$ is **15.5** (green) and **10.2** (brown).

**And the error is concentration-dependent**, since $r_{Q}$ is fixed while $B_{Q}$ grows with $c$:

```math
\op{sensitivity} \approx \frac{r_{Q}}{c\,l\,e_{Q}} \propto \frac{1}{c}
```

Two consequences: a log–log plot of the index against concentration must be **curved**, flattening toward
high $c$ (a constant slope would falsify the pedestal explanation); and the total error is **U-shaped**,
because curvature degrades invariance at *low* $c$ while Soret stray-light compression degrades it at
*high* $c$ (`SPEC_capture_quality.md` §16.11.8). An optimal working concentration exists between them.

**Against the record:** the baseline **halves** the dilution error (5.49 % → 2.75 %). And the residual
dependence is bounded directly: pooling the three within-oil dilution pairs on record gives a log–log slope
of **+0.033 ± 0.029** — consistent with zero *(`SPEC_capture_quality.md` §16.10.8)*. In practice a realistic
preparation error of ±17 % moves the index by about **0.6 %**, and even a *fourfold* dilution error moves it
under 5 %, against a class gap of **52 %**. ⚠ That slope is an **upper** bound: each pair is a different fill
as well as a different dilution, so it carries fill-to-fill scatter with it.

> **Those two figures were measured on the 600–630 anchor** and are quoted here because they are what the
> record holds — the halving experiment has not been repeated on 620–630. What *has* been measured on both
> is the cleanest single dilution pair, post-rebuild: log–log slope **−0.12** on the old anchor against
> **−0.05** on the new one (§5a.1). The anchor move more than halved the residual concentration dependence
> — the one number in this chapter that improves for a reason the theory predicts, since a narrower window
> further from the Soret band gives the pedestal's curvature less room to differ across it.

### 5.8 Performance

| | value |
|---|---|
| green mean / σ *(n = 6)* | 15.499 / 0.714 |
| brown mean / σ *(n = 6)* | **10.160 / 0.197** |
| gap | **5.339 = 52.5 %** of the brown mean |
| pooled σ | 0.524 |
| **Cohen's *d*** | **10.20** |
| green margin to T = 12.5 | **+4.20 σ** |
| brown margin to T = 12.5 | **+11.87 σ** |

**The threshold is T = 12.5 and it was DERIVED, not inherited** — the midpoint of the empty corridor
between the highest brown run and the lowest green run, rounded (`SPEC_capture_quality.md` §16.20.4). There
was no predecessor on this scale to inherit from. ⚠ **T = 10.6 belongs to a different metric** — the
pedestal-corrected index of §5a.3 — and to the old 600–630 gauge before it. Reading this chapter's numbers
against 10.6 is the single easiest mistake to make with this document.

> ⚠ **Why this green margin differs from the spec's.** `SPEC_capture_quality.md` §16.20.4 scores green as
> sets **B+C** pooled (n = 12); this document declares green as set **C alone** (n = 6, 5 df). Fewer degrees
> of freedom, and the t-distribution charges heavily for that. Both are correct for their own data set;
> **neither may be quoted with the other's.**

> ⚠⚠ **The comparison that must not be made.** The 600–630 anchor scored *d* = **11.04** on exactly this
> pair, against **10.20** here. That is not a regression in the metric: the class gap grew from 31.7 % to
> 52.5 % while the noise grew alongside it, and *d* is their quotient. On the spec's pooled basis the same
> anchor move reads *d* 9.80 → **10.35**, i.e. an improvement. **A single *d* is not a property of a metric
> — it is a property of a metric and a data set together.** What the anchor move buys is stated in §5a.1
> and it is not primarily discrimination; it is dilution invariance, fill-to-fill repeatability, and a
> baseline anchor that no longer straddles a lamp line.

**How well is σ known?** With n = 6 the point estimate is not what to plan on. A χ² interval on brown's σ
gives [0.123, **0.483**] — and **even at the upper bound brown clears the threshold by 4.84 σ**. The
conclusion does not depend on six points estimating σ well.

**The brown mean also survived a rig rebuild and a different oil**: archived `20260727C` reads **10.268**
on this anchor from six *fills* on the old rig; series D reads **10.160**, a difference of **−1.05 %**.
⚠ Its scatter does not survive: σ = 0.917 against series D's 0.197, i.e. **4.7×**. That is the rebuild, not
the anchor — §16.11 measures the same factor on the old metric — but it is worth seeing that the narrower
window did nothing to rescue a badly-seated rig.

*(t-distribution throughout, per `SPEC_capture_quality.md` §16.10.11a — the error is heavy-tailed, so the
Gaussian is optimistic exactly where it matters.)*

### 5.9 ✅ The 607 nm artifact no longer touches the metric

The lamp's 607 nm emission line used to sit **inside** the far anchor, because that anchor began at
600 nm. On the 620–630 window it does not: **no band this metric reads contains it.**

| window | range | contains the 607 nm line? |
|---|---|---|
| Soret | 440–460 | no |
| Q | 560–580 | no |
| near anchor | 520–540 | no |
| **far anchor** | **620–630** | **no** *(600–630 did)* |

On the old anchor its contribution was measurable: bridging the line by interpolation across 604–612 nm
lowered $A_{far}$ by **7.2 %** (green) and **8.4 %** (brown), moving the index −5.9 % / −4.9 % and *d* from
11.04 to 11.65 — slightly *better* without it. It was never creating the discrimination, but it **was**
baked into the absolute scale on which that anchor's threshold had been calibrated. It no longer is.

⚠ **This is a reason the thresholds could not be carried across.** A scale that included a lamp line and a
scale that excludes it are not the same scale, whatever else changed with them. It is also why the line's
physics still matters below: the lamp is the same lamp, and a *different* lamp would still move things —
just no longer through this particular door.

#### What the artifact actually is

Both named artifacts are **lamp emission lines**, present in the reference spectrum itself:

| | position in the reference | height above the local continuum |
|---|---|---|
| 473 nm feature | ~475 nm | **+48 %** |
| 607 nm feature | ~606 nm | **+20 %** |

A sharp line in the lamp should *cancel* in $T = S/R$, since it appears in both captures. That it does
**not** cancel — it survives into the absorbance as a spike — means the two captures do not see it
identically. The project's term for this is **registration**: the reference and the sample are two
separate jar insertions, and anything that displaces the beam between them (the jar seating, §5.1) shifts
where a given wavelength lands on the sensor. A sharp line offset by a fraction of its own width turns
into a derivative-shaped spike when the two spectra are divided. The artifact's 2.7 nm width is
consistent with a shift of that order.

⚠ **This attribution is the project's, and I could not confirm it cleanly.** Estimating the line's
position separately in reference and sample gives an apparent offset, but the estimate is confounded: the
oil's own absorbance changes across the window, which tilts the local continuum and drags any centroid
measure with it. **The lamp-line origin is verified; the registration mechanism is plausible and
untested.** A competing explanation — detector nonlinearity or in-instrument stray light at a bright,
high-contrast line — has not been excluded.

**⇒ What would move the threshold** is therefore a change to **the lamp's line spectrum** (a different
lamp, or an ageing one) or to **the reference↔sample alignment** (calibration, jar seating, optics). A
different *camera* is at most a second-order influence, through how the sensor grid samples the line —
an earlier draft of this document overstated it.

<!--PAGEBREAK-->

## 5a ⭐⭐ Where the far anchor came from — and the three verdicts  *(2026-08-03; `SPEC_capture_quality.md` §16.20)*

Everything above is written on the shipped **620–630 nm** far anchor. It was **600–630** until 2026-08-03,
and every number in chapters 4–5 changed when it moved — not because the oils or the instrument changed,
but because the line the bands are measured above is drawn through a different window. §5's algebra is
unchanged in *form*; only where the second window sits.

This chapter is the record of that move: why it was made, what it cost, and why the bench now shows the
index three ways rather than one.

### 5a.1 Why the window moved — and why it is the direction nobody tried

§5.9 and §5.5 together make the problem plain: the far anchor **straddles** two things it should not.
It contains the **607 nm lamp line**, and it stands on the **pigment's own Qy band** — protochlorophyll's
Qy is at ~623–626 nm, not chlorophyll's ~665, so that band sits *inside* the window rather than beyond it.

Two earlier attempts moved the wrong way. Pulling the right edge **in** (600→620) collapses the class gap;
excising 618–630 as "the lamp's red cliff" deletes the Qy flank and makes the residual *worse*. **Both
remove the pigment information.** The move that works keeps it and drops 600–615 instead:

```
   old  600 |==============================| 630
            straddles the 607 nm line AND the Qy band

   new                      620 |==========| 630
            starts clear of the line, centred on Qy
```

Measured on post-rebuild data, against the shipped anchor:

| | 600–630 *(old)* | **620–630** *(new)* |
|---|---|---|
| Cohen's *d*, green vs brown *(pooled green B+C)* | 9.80 | **10.35** |
| Cohen's *d*, green vs brown *(this document's pair)* | **11.04** | 10.20 |
| dilution slope `s` | −0.12 | **−0.05** |
| pedestal residual `r_Q` | −0.0246 | **−0.0184** |
| re-seat σ / class gap | 12.0 % | **11.4 %** |
| σ_fill / class gap | 6.2 % | **4.4 %** |
| `M∞` — the scale | 9.998 | 12.450 |
| three-region identity error (§5.5) | 0.52 % | **0.02 %** |
| 607 nm lamp line inside the anchor | **yes** | **no** |

⚠ **Read the first two rows together.** Discrimination improves on the pooled-green basis and slips
slightly on this document's declared pair. That is not a contradiction: *d* is a gap divided by a scatter,
and which data set supplies the scatter decides the answer. **The honest summary is that the anchor move
is roughly neutral for discrimination** and buys its keep elsewhere — halving the dilution slope, cutting
fill-to-fill scatter by a third, and removing a lamp line from the measurement.

⚠ **The scale moves, so `T` must be re-derived** — that cost is real and is the reason this is not simply
an improvement. And the gains are **not** what a first look suggested: a sweep scored on *pre-rebuild*
fills showed the class gap doubling, and that gain **did not survive** re-scoring on clean data. What
survives is the table above.

### 5a.2 ⚠ `r_Q` belongs to its anchor

`r_Q` is defined as the pedestal's departure from **its own best-fit line** (§5.7). Move the anchor and
the line moves, so the residual moves with it:

```math
r_{Q}(600-630) = -0.0246 A \qquad r_{Q}(620-630) = -0.0184 A
```

**Pairing 620–630 band means with the 600–630 constant is a category error**, and it is an easy one to
make because both are called `r_Q`. The shipped constant is per-anchor and per-rig-state (§5.7's residual
does not survive a mechanical rebuild).

### 5a.3 The three verdicts, and why the raw ratio lost its

| | metric | `T` | why |
|---|---|---|---|
| **1** | $B_{Soret} / (B_{Q} - r_{Q})$ | **10.6** | the pedestal-corrected index — the primary |
| **2** | $B_{Soret} / B_{Q}$ | **12.5** | the same anchor, uncorrected — **this document's Pigment Index** |
| **3** | $A_{Soret} / A_{Q}$ | ⛔ **none** | the raw ratio — **shown as a value, with no verdict** |

Each adjacent pair isolates one step of the construction. ⚠ The three sit on **different scales**: compare
verdicts, never numbers.

**The raw ratio carries no threshold because none exists.** On post-rebuild data green reads 5.387 ± 0.510
and brown 4.842 ± 0.290 — Cohen's *d* **1.20**, and the classes **overlap outright** (lowest green run
4.863 below the highest brown run 5.340). No line separates them.

⚠⚠ **And its shipped threshold had been wrong for weeks.** `T` = 4.4 sat **below the entire brown class**
(minimum 4.622), so every run of the brown reference oil was reported *"good — green"* — on the
PUBLISHING badge, the one screen an end user sees. §5.4's argument for why the baselined index
discriminates and the raw one does not was right all along; the gauge had simply never been re-scored
against a post-rebuild brown series.

<!--PAGEBREAK-->

## 6. Colour

The evaluation tab carries ten colour chips. They are a presentation feature, and this chapter exists
partly to say why they are **not** a verdict input.

### 6.1 How a spectrum becomes a colour

```math
\op{SPD} \Rightarrow \op{CIE} XYZ \Rightarrow xy \Rightarrow \op{RGB} \Rightarrow \op{HSL} \Rightarrow hue
```

The spectrum is rebinned to 380–780 nm at 1 nm, integrated against the **CIE 1931 2° colour-matching
functions** under **D65**, reduced to chromaticity $xy$, converted to RGB and read as HSL
(`SPEC_spectrum_processing.md` §4). **Luminance is discarded at the $XYZ \to xy$ step**, so every colour
reported is chromaticity-derived.

Two converters are used deliberately: absorbance-derived chips use **sRGB** (full gamut), transmission-
derived chips use the tuned **rgbxy** module (verdict-compatible, so the pumpkin hue thresholds are
untouched). Absorbance values are sanitised first — non-finite → 0, **negatives → 0** (absorbance goes
negative where $T > 1$, and negatives corrupt the CIE integral) — and capped by a **relative** ceiling at
twice the 99th-percentile value, so a $T \to 0$ spike cannot dominate.

### 6.2 The three families

| family | source | behaviour under dilution |
|---|---|---|
| **Intrinsic** | absorbance | **invariant** — $A \to kA$ leaves chromaticity unchanged |
| **Intrinsic-perceived** | absorbance, complemented | invariant |
| **Perceived** | transmission | **dilution-dependent** — $T \to T^{k}$ |

**Intrinsic-perceived** is the *colorimetric* complement: reflect the absorbed chromaticity through the
D65 white point, $2 \cdot white - absorbed$ — the "other half of the light". This lands ~4° from the true
perceived hue, against ~34° for a naive +180° HSL flip.

Each family is shown at its measured saturation and lightness plus a **hue-normalised** twin at fixed
S = 38 %, L = 34 %, so that only hue varies between oils. A guard greys any chip whose **chroma**
$(1 - |2L - 1|) \cdot S$ falls below 8 % — near-white and near-black have no meaningful hue, and HSL
saturation alone would report a false one.

### 6.3 ⛔ Measured: colour does not discriminate these oils

| chip | green *(n = 12)* | brown *(n = 6)* |
|---|---|---|
| Intrinsic | H 298–300° | H 298–300° |
| Intrinsic-perceived | H 67–69° | H 68–69° |
| Perceived | H 70° | H 70–71° |
| hue-normalised variants | H 300° · S 38 % · L 34 % | **identical** |

This **confirms** `SPEC_capture_quality.md` §16.10.15 ("colour channels do NOT discriminate this oil
pair") on post-rebuild data, and extends it from raw channels to the full HSL retrieval path.

**Why it fails is instructive.** Colour is a *broadband integral* — the CMFs weight the whole visible
range — so the narrow, structured differences that carry the class signal (§3.6: a redistribution inside
a 50 nm slice of the Q region) are averaged away against the enormous Soret absorbance that both oils
share. The metric wins precisely because it looks at **narrow windows**; colour loses for the same reason.

**⇒ The chips are worth showing and must never be thresholded.**

<!--PAGEBREAK-->

## 7. What these numbers do not mean

### 7.1 A band mean is not dilution-invariant

$A_{Soret}$ separates our two sets at *d* = 2.31 and $B_{Soret}$ at *d* = 2.70, with no overlap. **Do not
use them.** The two sets happen to share a dilution recipe, so the comparison is valid only *within* that
accident. Only ratios divide the common factor out — which is why the UI marks ratios in bold as decision
metrics and shows the band means without thresholds.

### 7.2 A ratio is invariant only if BOTH sides are corrected the same way

> **A ratio is dilution-invariant if and only if its numerator and denominator are both pedestal-free and
> corrected the same way.**

The legacy $G = D_{Q}/A_{clarity}$ and $G' = D_{Q}/A_{blue}$ apply the correction to **one side only** — a
locally baseline-corrected numerator over an uncorrected denominator. They are not merely weak
discriminators; they are *structurally* incapable of dilution invariance (`SPEC_capture_quality.md`
§16.14.3).

### 7.3 The three verdicts are not on the same scale

The tab shows **three** readings of the same capture (§5a.3), each on its own scale:

| | metric | threshold |
|---|---|---|
| **1** | $B_{Soret}/(B_{Q} - r_{Q})$ — baseline **and** pedestal | **10.6** |
| **2** | $B_{Soret}/B_{Q}$ — baseline only *(this document's Pigment Index)* | **12.5** |
| **3** | $A_{Soret}/A_{Q}$ — raw | **none** |

**Only the verdicts are comparable — never the numbers.** They are ratios of different quantities, and the
two thresholds are not interchangeable: 10.6 belongs to metric 1 and 12.5 to metric 2. ⚠ That 10.6 was
*also* the old 600–630 gauge's threshold is a coincidence of arithmetic, not a shared scale — it was
retained on metric 1 by explicit decision after being checked against the new corridor, not carried over
(`SPEC_roast_ampel.md` §2b).

### 7.4 ⚠ We do not know what the 560–580 band is

Two candidates, and they are not equivalent: the **Q(1,0)** vibronic satellite of the intact pigment, or a
**Qx** band of protopheophytin. Since 560–580 is the index's *denominator*, the difference is not
academic — if it is the degradation product, the metric is a literal *intact ÷ degraded* ratio.

Evidence favours the second (§3.6: `A_Q` equal across classes while the 572 feature is *stronger* in
brown), but **no source we hold assigns this band**, and the comparison is between two bottles rather than
one oil before and after demetallation. Open: `SPEC_pumpkin_peak_ratio_eval.md` §15.5.

### 7.5 Precision is not correctness, and these are re-seat numbers

Both restated from §1.4 because they are the two most commonly dropped caveats. **T = 12.5 is
unvalidated**; and σ_fill — the scatter a real single measurement is subject to — is unmeasured for brown.

<!--PAGEBREAK-->

## 8. Reference sheet

Green = `20270729C`, brown = `20260731A`, both the mean of six runs.

| shown as | symbol | formula | green | brown | *d* |
|---|---|---|---|---|---|
| Soret · 440–460 | $A_{Soret}$ | mean $A_{d}$ over 440–460 | 1.186 | 1.086 | 2.31 |
| Q · 560–580 | $A_{Q}$ | mean $A_{d}$ over 560–580 | 0.230 | 0.225 | 0.26 |
| Clarity · 510–540 | $A_{clarity}$ | mean $A_{d}$ over 510–540 | 0.114 | 0.095 | 1.62 |
| far · 620–630 | $A_{far}$ | mean $A_{d}$ over 620–630 | 0.204 | 0.153 | 2.08 |
| Pigment ratio *(verdict 3)* | — | $A_{Soret} / A_{Q}$ | 5.172 | 4.842 | 1.18 |
| Pigment ratio · clarity | — | $A_{Soret} / A_{clarity}$ | 10.409 | 11.572 | −1.08 |
| Soret · linear baseline | $B_{Soret}$ | mean $B$ over 440–460 | 1.132 | 1.024 | 2.70 |
| Q · linear baseline | $B_{Q}$ | mean $B$ over 560–580 | 0.073 | 0.101 | −10.83 |
| **Pigment ratio · linear baseline** *(verdict 2)* | **Pigment Index** | $B_{Soret} / B_{Q}$ | **15.499** | **10.160** | **10.20** |
| **· with the pedestal put back** *(verdict 1)* | — | $B_{Soret} / (B_{Q} - r_{Q})$ | **12.380** | **8.590** | **9.33** |
| Greenness G | $G$ | $D_{Q} / A_{clarity}$ | — | — | −1.99 |
| Pigment D_Q | $D_{Q}$ | peak above a local line | — | — | −2.48 |
| Soret A_blue | $A_{blue}$ | reference-gated 450–490 | — | — | 1.18 |
| Pigment ratio · legacy | — | $A_{blue} / A_{clarity}$ | — | — | 0.11 |
| G' (alt.) | $G'$ | $D_{Q} / A_{blue}$ | — | — | −5.33 |

### Constants

| constant | value | where |
|---|---|---|
| capture window | 440–630 nm | `WAVELENGTH_MIN_NM` / `MAX` |
| frames per capture | 150 | `FRAMES` |
| de-spike kernel | 7 points ≈ 1 nm | `MedianFilterOp` |
| reference floor | 6.31 × 10⁻⁵ of peak | `TransmissionLogicModule` |
| division guard $\epsilon$ | 10⁻³ | `DevSpectralPlugin` |
| hue-normalised S / L | 38 % / 34 % | `DevSpectralPlugin` |
| achromatic chroma guard | 8 % | `EvaluationColorUtil` |
| **far anchor** | **520–540 + 620–630 nm** | `PB_BASELINE_WINDOWS` |
| pedestal residual $r_{Q}$ | **−0.0184 A** *(this anchor's own, §5a.2)* | `PB_R_Q` |
| verdict threshold T | **12.5** on the Pigment Index | `SPEC_capture_quality.md` §16.20.4 |
| verdict threshold T | 10.6 on the pedestal-corrected index | `SPEC_roast_ampel.md` §2b |

<!--PAGEBREAK-->

## Appendix A — the least-squares fit

§5.2 fits a straight line through the two anchor windows. This is what "fit" means.

### A.1 Residuals, and why they are squared

A trial line $A = m\lambda + c$ will not pass exactly through every measured point. The **residual** at
each wavelength is how far the measurement sits above or below it:

```math
r(\lambda) = A_{d}(\lambda) - (m\lambda + c)
  positive where the curve lies above the trial line, negative where it lies below.
```

"As close as possible to all the points at once" is then made precise by minimising the **sum of the
squared** residuals. Squaring does two things: it removes the sign, so points above and below the line
cannot silently cancel each other out; and it penalises one large miss more heavily than several small
ones, which is what makes the fit follow the bulk of the data rather than being dragged by outliers on
one side.

### A.2 The weighting, and why it is not one-point-one-vote

```math
\op{SSR}(m, c) = w_{near}\sum_{\lambda \in W_{near}} r(\lambda)^{2} \, + \, w_{far}\sum_{\lambda \in W_{far}} r(\lambda)^{2}
  the weighted sum of squared residuals, one term per anchor window.
```

with per-point weights $w_{near} = 1/|W_{near}|$ and $w_{far} = 1/|W_{far}|$ — each window's points
weighted by one over that window's point count, so **each window contributes total weight 1**.

> **Why not weight every point equally?** The far window holds 212 points against the near window's 135,
> so an unweighted fit would let the red end pull about **1.6× harder** — and, worse, *widening a window
> would silently move the baseline* as a side effect. A window is one piece of evidence about where the
> baseline runs, not one piece per sample. Measured across the 25 runs of 2026-07-27 the two fits differ
> by ~0.5 % and change **no verdict**: this is for predictability under a window change, not accuracy.

### A.3 The minimisation

```math
(m, c) = \arg\min_{m, c} \op{SSR}(m, c)
  read: the slope and intercept AT WHICH that sum is smallest.
```

$\arg\min$ denotes the *argument* that minimises — the pair $(m, c)$, not the value of the sum itself.
Nothing is actually searched for: setting the two partial derivatives to zero gives a pair of linear
equations with a closed-form solution. The implementation calls `numpy.polyfit` of degree 1 with
`w = sqrt(weights)`, because `polyfit` weights the *residual* rather than its square.

<!--PAGEBREAK-->

## Appendix B — Cohen's *d*: the variants, and which is used where

§1.3 gives one formula. There are several in circulation, they do not always agree, and this appendix
says which this project uses and why.

### B.1 The family — Cohen's *d* is one member of it

**Standardised mean difference (SMD)** is the umbrella term: *a mean difference expressed in
standard-deviation units*. It does not say **which** standard deviation, and that is exactly where the
named variants differ:

| variant | denominator | when it is the right choice |
|---|---|---|
| **Cohen's *d*** | the **pooled** SD of both groups | two groups of comparable status — **our case** |
| **Hedges' *g*** | the same, × a small-sample bias correction | the same, at small *n* — see B.3 |
| **Glass's Δ** | the **control** group's SD alone | when one group is a reference standard whose scatter is the meaningful yardstick |

So Cohen's *d* is *an* SMD, not a synonym for it — although many fields (Cochrane, for one) say "SMD"
as the umbrella and then report a specific recipe. **This project uses Cohen's *d* and writes it *d*.**
Glass's Δ would be defensible once we have a certified reference oil; we do not, and neither of our two
classes is a control.

### B.2 ⚠ Two pooled-SD conventions — and they diverge at unequal *n*

Within Cohen's *d* itself there are two formulas for the denominator:

```math
s_{pooled}^{RMS} = \sqrt{\frac{s_{1}^{2} + s_{2}^{2}}{2}}
  the simple root-mean-square of the two standard deviations.
s_{pooled}^{df} = \sqrt{\frac{(n_{1}-1)\,s_{1}^{2} + (n_{2}-1)\,s_{2}^{2}}{n_{1} + n_{2} - 2}}
  the degrees-of-freedom-weighted form: the larger group's scatter counts for more.
```

**When the two groups are the same size these are algebraically identical** — substitute
$n_{1} = n_{2} = n$ into the second and it collapses into the first. They part company only when the
groups differ in size, and then the df-weighted form is the conventional choice.

**Where each applies in this project:**

| comparison | *n* | conventions agree? | *d* |
|---|---|---|---|
| **everything in this document** — green `20270729C` vs brown `20260731A` | **6 vs 6** | ✔ **identical** | **10.20** |
| `SPEC_capture_quality.md` §16.20.4 — green sets **B+C pooled** vs brown | **12 vs 6** | ⛔ **differ** | df-weighted **10.35** |

⚠ **The one unequal-*n* comparison is in the spec, not here**, and there the two conventions differ by
12 %. `diagnostics/brown_series_d.py` computes the RMS form; the **df-weighted 9.80 is the more
defensible figure to quote**. Nothing downstream changes — the per-class σ-margins and error rates are
computed separately and are untouched — but the number should not be quoted without naming its recipe.

### B.3 Hedges' *g* — the small-sample correction

Cohen's *d* is biased **upward** when samples are small, and n = 6 is small. Hedges' correction removes
most of that bias:

```math
g = d \cdot \Big(1 - \frac{3}{4\,df - 1}\Big), \qquad df = n_{1} + n_{2} - 2 = 10
g = 10.20 \cdot 0.923 = 9.42
```

**So the bias-corrected separation is ≈ 9.4, not 10.20** — about 8 % lower. It changes no conclusion in
this document, both being far beyond "large", but *g* is what a statistician would ask for at this sample
size and the figure to quote externally.

> **Convention adopted here:** every *d* reported in this document and in the specs is **uncorrected
> Cohen's *d* on the RMS pooled SD**. Multiply by **0.923** for Hedges' *g* on the 6-vs-6 comparisons.
> Where a figure is quoted outside the project, quote *g*.

<!--PAGEBREAK-->

## Appendix C — reproducing the numbers

Every value in this document is recomputed from the archived report PDFs' embedded workflow JSON by
diagnostics that call the **shipped** `SpectrumFeatureUtil` and `DevSpectralPlugin` code paths, so the
document cannot drift from the application.

| script | produces |
|---|---|
| `diagnostics/metric_walkthrough.py` | every intermediate quantity of the chain, both classes |
| ↳ `METRIC_ANCHOR=600 …` | the same, on the superseded 600–630 anchor — the §5a comparison column |
| `diagnostics/qband_shape.py` | the speciation-vs-concentration test and the resolution measurement |
| `diagnostics/brown_series_d.py` | the series-D discrimination statistics |
| `diagnostics/metric_algebra_plots.py` | figures 2–4 |
| `docs/tools/build_pigment_figures.py` | figure 1 |

Cohen's *d* is the pooled-SD standardised difference on n = 6 per class (defined in §1.3); with six runs
a *d* of this size is bounded well away from zero but its point value is loose.

⭐ **`METRIC_ANCHOR` is the one switch that reproduces this whole document on either anchor.**
`metric_walkthrough.py` reads it, and `metric_algebra_plots.py` follows whatever the walkthrough is set
to, so text and figures cannot drift apart. Default **620** — the shipped window. Every number in
chapters 4–5 and every figure 2–4 comes out of one run at that default; §5a's comparison column comes
out of one run at `METRIC_ANCHOR=600`.

<!--PAGEBREAK-->

## Appendix D — the legacy metrics *(historical)*

The **"Metrics (dev)"** tab predates the literature bands and uses older machinery on different windows:
`BLUE_BAND` 450–490, `GREEN_BAND` 510–540, `Q_SEARCH` 565–590. It is retained so that old numbers stay
comparable, and for no other reason. All *d* values are green `20270729C` vs brown `20260731A`.

### D.1 The uncorrected ratios

```math
S/Q_{plain} = \frac{A_{Soret}}{\max(A_{Q},\, \epsilon)} \qquad S/Q_{clarity} = \frac{A_{Soret}}{\max(A_{clarity},\, \epsilon)}
```

| | green | brown | *d* | verdict |
|---|---|---|---|---|
| $S/Q_{plain}$ | 5.172 ± 0.267 | 4.842 ± 0.291 | 1.18 | **overlaps** |
| $S/Q_{clarity}$ | 10.409 ± 0.601 | 11.572 ± 1.401 | −1.08 | **overlaps, and inverted** |

Neither works. $S/Q_{clarity}$ is worse than useless — it points the wrong way and its brown scatter is
14 %. §5.4 explains why: the uncorrected Q band carries no class information.

### D.2 The Q-band peak height $D_{Q}$

Rather than a window mean, this finds the local maximum in the search band and measures its height above
a **local** two-anchor line:

```math
(\lambda_{Q}, A_{peak}) = \arg\max_{\lambda \in [565, 590]} A(\lambda)
L(\lambda_{Q}) = \bar{A}_{[550,560]} + \big(\bar{A}_{[595,605]} - \bar{A}_{[550,560]}\big)\frac{\lambda_{Q} - 555}{600 - 555}
D_{Q} = A_{peak} - L(\lambda_{Q})
```

The anchors are ±5 nm windows around 555 and 600 nm. A flat offset lifts peak and line equally, so $D_{Q}$
is already immune to an additive pedestal — which is why its de-spiked twin barely moves.

### D.3 The reference-gated blue band $A_{blue}$

```math
A_{blue} = \op{mean}\{A(\lambda) : \lambda \in [450, 490],\ R(\lambda) \ge 0.25 \max_{[450,465]} R,\ A(\lambda) \le 1.5\}
```

Two gates: wavelengths where the *reference* is weak are dropped (trimming the LED's cyan dip), and
saturated wavelengths are dropped. It is the only metric that reads the reference spectrum directly.

### D.4 The derived ratios, and how they perform

```math
G = \frac{D_{Q}}{A_{clarity}} \qquad G' = \frac{D_{Q}}{A_{blue}} \qquad S/Q_{legacy} = \frac{A_{blue}}{A_{clarity}}
```

| metric | *d* | note |
|---|---|---|
| **Pigment Index** *(§5, for comparison)* | **10.20** | the only usable one |
| $G'$ | −5.33 | **sign inverted** — brown reads higher |
| $D_{Q}$ | −2.48 | inverted |
| $G$ "Greenness" | −1.99 | inverted — despite the name |
| $A_{blue}$ "Soret" | 1.18 | weak |
| $A_{clarity}$ | 0.54 | none |
| $S/Q_{legacy}$ | **0.11** | **useless** |

> **⚠ Three are inverted with respect to their names.** "Greenness G" reads *higher* on the brown oil. The
> names are historical; `SPEC_pumpkin_peak_ratio_eval.md` §11 found the direction reversed and the fields
> were renamed once already ("Browning A_blue" → "Soret A_blue"). **Treat every label on the legacy tab as
> a hypothesis, not a description.** §7.2 adds that $G$ and $G'$ cannot be dilution-invariant either.

<!--PAGEBREAK-->

## References

### Pigment identity and band positions

1. **Fruhwirth, G. O. & Hermetter, A. (2007).** *Seeds and oil of the Styrian oil pumpkin: components and
   biological activities.* Eur. J. Lipid Sci. Technol. **109**(11), 1128–1140.
   DOI [10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105). §3.5 identifies protochlorophyll
   a/b and protopheophytin a/b; Fig. 3 gives the 635 nm fluorescence maximum. Local copy in
   `spectracs-references/articles/`; free mirror at
   [gruenesglueck.com](http://www.gruenesglueck.com/wp-content/uploads/2014/09/1_krbiskernl_bersichtsartikel_fruhwirth-hermetter_2007.pdf).
2. **Protochlorophyllide spectral forms.** Pak. J. Biol. Sci. (2010) —
   [scialert.net](https://scialert.net/fulltext/?doi=pjbs.2010.563.576). Qy ≈ 623 nm (80 % acetone),
   ≈ 626 nm (methanol); Soret ≈ 440 nm; minor bands 505, 535, 606 nm.
3. **Gouterman, M. (1961).** *Spectra of porphyrins.* J. Mol. Spectrosc. **6**, 138 — the four-orbital
   model that names the Soret and Q bands.
4. **Histolocalisation of the oil and pigments in the pumpkin seed** —
   [ResearchGate](https://www.researchgate.net/publication/227928192_Histolocalisation_of_the_oil_and_pigments_in_the_pumpkin_seed).
   Speciation as 2,4-divinyl-protochlorophyll a, 2,4-divinyl-protopheophytin a, 2-vinyl-protopheophytin a;
   protopheophytins 1.1–35.5 % of protochlorophylls, rising with storage.
5. **The four porphyrin spectral types and their Q-band intensity ordering** — *The Use of
   Spectrophotometry UV-Vis for the Study of Porphyrins*,
   [InTech](https://cdn.intechopen.com/pdfs/37656/InTech-The_use_of_spectrophotometry_uv_vis_for_the_study_of_porphyrins.pdf);
   [Porphyrin overview, ScienceDirect](https://www.sciencedirect.com/topics/physics-and-astronomy/porphyrin).
   Etio IV > III > II > I; rhodo III > IV > II > I; oxo-rhodo and phyllo IV > II > III > I — **band I
   weakest in all four**.
6. **Chlorophyll *a* comparison values** (the molecule we do *not* have) —
   [PhotochemCAD](https://omlc.org/spectra/PhotochemCAD/html/122.html).

⚠ **Not independently sourced:** a primary measurement of *protopheophytin a*'s band positions. §3.3's
direction is argued from the classification in [5], which is textbook porphyrin spectroscopy, but the
specific numbers for this molecule are not sourced here.

### Colour science

7. **CIE 1931 2° colour-matching functions** and the D65 illuminant, via the `colour-science` package;
   pipeline documented in `SPEC_spectrum_processing.md` §4.
8. **Kreft, S. & Kreft, M.** — the dichromaticity index, with pumpkin seed oil as its type example.

### Owning specifications

| topic | document |
|---|---|
| the baseline's derivation, error budget, series D | `SPEC_capture_quality.md` §16.10–16.14 |
| what the anchors contain; the far-window sweep | `SPEC_capture_quality.md` §16.12.12–14 |
| speciation vs concentration; the resolution argument | `SPEC_capture_quality.md` §16.13.9 |
| dilution-invariance algebra | `SPEC_capture_quality.md` §16.14 |
| the three-region algebra; pre-registration | `SPEC_capability_proof.md` §2.1a, §11.4f |
| legacy metrics; band naming; the open 560–580 assignment | `SPEC_pumpkin_peak_ratio_eval.md` §11, §15 |
| colour retrieval | `SPEC_color_retrieval.md`, `SPEC_spectrum_processing.md` |
| pigment chemistry in full | `DOC_sample_physics.md`, `KB_spectroscopy_physics.md` §4.1 |
