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

**⭐⭐ Read §1.5a first if you read nothing else.** It is one page on *what kind of number this is* —
operational rather than mechanistic, in-matrix rather than molecular — and it is the frame every chapter
after it sits in. It also carries the discipline that frame costs.

**How to read it.** Chapter 1 stands alone and contains the claim. Chapter 3 is the physics, chapter 5
the metric that decides the verdict — if you read only two, read those. Chapter 6 is how the instrument
decides *when* that number is ready, chapter 7 the difference metric that scores better and still does not
decide, and §5.8 is the mechanism connecting 5 and 7. Chapters 8–9 are colour and caveats. Everything
historical has been moved to the appendices.

> ⚠ **Restructured 2026-08-21.** Until then this document's chapter 5 was the **Pigment Index**, a
> Soret-to-Q ratio on a baseline-corrected curve, and it was the shipped verdict source. `Q%` replaced it.
> The Pigment Index is now **Appendix E** and its far-anchor history **Appendix Ea** — unretracted, fully
> intact, and no longer deciding anything. Its section numbers `5.x` are `D.x` there.

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

### ⭐⭐⭐ 1.1 The metric that decides the verdict — `Rv`

*(2026-08-25)* One number decides it, and that number is **`Rv`**, the **red ratio**:

```math
R_v = 100\,\frac{A_{624} - A_{valley}}{A_{Q} - A_{valley}}
```

with $A_{624}$ over **622–627 nm**, $A_{Q}$ over **565–580 nm** and $A_{valley}$ over **500–560 nm**,
each a plain mean of the de-spiked absorbance. **Higher is greener** — the opposite of the metric it
replaces — and the provisional threshold is **`T = 52`**.

⭐ **Read it as one sentence:** *the 624 nm band's height above the valley, as a percentage of the
Q band's height above that same valley.* Both terms sit above the same datum, both scale with dose, so
the ratio is scale-invariant by construction — and a 40–45 % dose swing moves it by under 0.8 %.

⭐⭐ **It is a symmetry diagnostic, not an intensity one.** Chapter 3's photophysics says demetallation
(D₄ₕ → D₂ₕ, protochlorophyll → protopheophytin) makes the longest-wavelength Q band the *weakest of
four*. `Rv` compares that band against a shorter one, so it measures the browning chemistry itself
rather than a proxy for it. Numerator and denominator come from **one** chromophore's Q manifold.

| against the archive | |
|---|---|
| labelled runs misclassified | **1 / 98** — `Q%` makes **9** |
| across three solvents | green 98.4–125.2, brown 28.3–46.4, **no overlap** — `Q%` overlaps outright |
| one oil, one solvent change | `Rv` moves ~3 %; **`Q%` moves 6.5 units**, more than its whole class separation |

⛔ **STATUS.** `Rv` is **chosen, not yet built**. `Q%` — chapter 5 — is what the instrument computes
today and it keeps the verdict until `Rv` is implemented and pre-registered. This chapter describes
where the programme is going; chapter 5 describes what it currently does.

⛔ **Three things `Rv` does not fix.** It is **turbidity-sensitive** (opposite-signed slopes: turbidity
pushes brown up and green down, eroding the gap from both sides); its **margin is smaller than the
within-fill scatter**; and a **paper diffuser erases the band it reads**, silently, with every guard
passing. Chapter 9 is the full list.

### 1.1a The metric it replaces

Until 2026-08-25 that number was **`Q%`**:

```math
Q_{\op{pct}} = 100\,\frac{A_{Q} - A_{valley}}{A_{Soret}}
```

with $A_{Q}$ over **565–580 nm**, $A_{valley}$ over **500–560 nm** and $A_{Soret}$ over **448–460 nm**,
each a plain mean of the de-spiked absorbance over that window. **Higher is browner**; the shipped
threshold is **`T = 18.6`**. ⛔ **No baseline is fitted and none is subtracted** — chapter 5 is why that
matters more than it sounds.

A second metric, **`dQ100`**, is computed and printed beside it but **does not decide anything**:

```math
dQ100 = 100\,\frac{A(563\ldots573) - A(623\ldots626)}{\op{sd}\,A(448\ldots626)}
```

It separates the archive's two classes better than `Q%` does — cleanly, where `Q%` overlaps — and it is
still not the verdict source, for reasons that are about evidence rather than performance (§7.4).
Chapter 6 is its account, and §5.8 shows that the two are reading **one see-saw in two different places**.

> ⚠ **This chapter used to describe a third metric, the `Pigment Index`** — a Soret-to-Q ratio taken on a
> baseline-corrected curve. It shipped as the verdict source until 2026-08-21 and is now **Appendix E**.
> Nothing in that appendix is retracted; it simply no longer decides anything.

### 1.2 What it achieves

| | green `20270729C` | brown `20260731A` |
|---|---|---|
| **`Q%`** | **15.891 ± 0.845** | **20.443 ± 0.260** |
| at the shipped threshold **T = 18.6** | **3.20 σ** below | **7.09 σ** above |
| `dQ100` *(scalar, no verdict)* | 13.746 ± 5.745 | 47.369 ± 4.714 |

On this pair the gap is **4.552 units** against a pooled σ of 0.625 — **Cohen's *d* = 7.28**, and the two
sets do not overlap on any run.

⚠ **One pair is not the archive.** Over all **88 labelled runs** `Q%`'s two classes **do** overlap
(§5.4): its corridor is **−2.807** and 7 runs fall on the wrong side of `T`. The honest form of the claim
is therefore narrower than this table looks — see §1.5.

### 1.3 What Cohen's *d* means

The figure is used throughout this document, so it is worth defining once. A raw gap between two class
means is uninformative on its own: 4.552 units is impressive only if the measurement's own run-to-run
scatter is much smaller than that. **Cohen's *d*** divides one by the other:

```math
d = \frac{\bar{x}_{1} - \bar{x}_{2}}{s_{pooled}}, \qquad s_{pooled} = \sqrt{\frac{s_{1}^{2} + s_{2}^{2}}{2}}
  the difference between the two class means, in units of their pooled standard deviation.
```

The subscripts 1 and 2 label the two groups being compared — here **1 = green, 2 = brown**:

| symbol | meaning | value here |
|---|---|---|
| $\bar{x}_{1}$ | the **mean** of group 1 — the average of green's six runs | 15.891 |
| $\bar{x}_{2}$ | the **mean** of group 2 — the average of brown's six runs | 20.443 |
| $s_{1}$ | the **standard deviation** of group 1 — how much green's runs scatter about their own mean | 0.845 |
| $s_{2}$ | the standard deviation of group 2 — brown's scatter | 0.260 |
| $s_{pooled}$ | the two scatters combined into one, as the root-mean-square of $s_{1}$ and $s_{2}$ | 0.625 |

So $d = (20.443 - 15.891) / 0.625 = 4.552 / 0.625 = 7.28$. Note that only the **standard deviations**
enter, not the sample sizes: *d* describes how far apart the two *populations* look, not how confident we
are about it. Confidence comes from n, and is handled separately in §E.8.

Read out loud, it is **"how many standard deviations apart the two groups are"**. It is dimensionless,
so it does not care what units a metric carries, and it is therefore directly comparable **between rival
metrics**. That is why every metric in this document is scored with it.

| *d* | conventional reading | overlap of two normal distributions |
|---|---|---|
| 0.2 | small effect | almost complete |
| 0.5 | medium | heavy |
| **0.8** | **large** | substantial |
| 3 | very large | the distributions barely touch |
| **7.28** | **`Q%` on this pair** | **none observed** |

**Our *d* = 7.28 means the class means sit seven pooled standard deviations apart** — which is why no run
of either set comes near the other's range. ⚠ On the full archive the same metric scores far lower; one
well-behaved pair is not a population (§5.4).

⚠ Three reading notes. With n = 6 per class the *value* of *d* is loosely estimated, even though its sign
and rough size are not in doubt; §E.8 gives the interval that actually matters. A **negative** *d* in this
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

> **1. It is dilution-invariant *by construction*, not by luck.** Numerator and denominator both scale
> with concentration and path length, so both cancel in the quotient — and the numerator is a
> **difference**, so a flat pedestal cancels too. Nothing is fitted, so no anchor can be contaminated
> (§5.2). It means the recipe can change without recalibrating the verdict.
>
> **2. It is a ratio of two chemical SPECIES, not a measure of "how much pigment".** What it tracks is
> intact protochlorophyll against its magnesium-free degradation product protopheophytin. Across the
> archive the *total* red absorption is conserved to within 3.6 % while its **split** between two bands
> swings by *d* ≈ 2.3 — nothing is missing, something has been **converted** (§3.4a, §5.8).
>
> **3. It survives the instrument.** Lamp brightness, camera gain, grating efficiency and exposure all
> scale the absorbance uniformly and divide straight out. A €30 webcam can carry it.

**⇒ Green-versus-brown discrimination works** — on a matched pair, decisively; across the whole archive,
with a measured overlap. §5.4 and §5.6 are where both halves are defended.

### 1.5 What the claim is *not*

⛔ **`Q%`'s classes overlap across the archive.** 7 of 88 labelled runs sit on the wrong side of `T`, and
no threshold fixes all of them. Any statement of the form *"the instrument tells green from brown"* is
true of a matched pair and **not** true of the archive as a whole. `dQ100` is 0/88 on the same runs and
is still not shipped as the verdict (§7.4) — which is the honest state of this project in one sentence.

⚠ **Precision is not correctness.** *d* = 7.28 says the instrument reliably distinguishes *these two
bottles*. Whether **T = 18.6** is the right place to cut the population of real pumpkin oils is a
separate, still-unvalidated question requiring reference oils with independent ground truth
(`SPEC_capture_quality.md` §16.10.11a). A precise instrument reading a wrong threshold is confidently
wrong.

⚠ **Nor is it solvent-portable.** In white spirit `Q%` reads a **green** oil as brown, twice (§5.6).

⚠ **These are re-seat numbers.** Both sets are six re-seats of *one fill*, so they exclude sample
preparation entirely. Fill-to-fill scatter remains unmeasured for brown
(`SPEC_capability_proof.md` §11.4f B).

### 1.5a ⭐⭐ WHAT KIND OF NUMBER THIS IS — one page, and it frames every chapter after it  *(2026-08-21)*

*Everything past this chapter is detail. This section is the frame the detail sits in, and it is short on
purpose. If a sentence in this document is ever quoted on its own, quote from here first.*

⭐⭐ **A detector does not need a causal model in order to be valid.** The validity requirement for
something that answers *"is this oil too brown?"* is that it responds to what you care about and not to
what you do not. Naming the mechanism is **interpretation** — a different question, and not a
precondition. An **octane number**, a **Brix** reading and a **durometer** value are all operational
definitions: real physics underneath, rigorously defined, decision-grade — and nobody mistakes 95 RON for
a measurement of a molecule. It is defined against a reference engine and reference fuels; change the
engine and the number changes, and *that is not a defect*. `DOC_pedestal_correction.md` says the same of
`Q%` in one line: **dilution-invariant but not absolutely calibrated.**

⭐⭐ **And a metric restricted to ONE mechanism can be worse than one that reads the whole sample.** If
roasting moves the pigment **and** the waxes **and** the press fines **and** the moisture together, then a
number reading the bundle carries more signal than a number reading only the pigment. Discarding
covarying information *because it is not yet explained* throws away real discriminating power — which is
why broad chemometric models routinely beat single-wavelength targeted reads on real product.

⭐ **This describes what already ships. It is not a proposal, and not a change of direction.** `Q%` is
measured on a **turbid emulsion** (`DOC_sample_physics.md` chapter 5 and §4.9); its valley window contains
that turbidity; its `A_Q` window contains a ~581 nm instrument line (`DOC_lamp_rebuild.md` §6). It has
always been an **in-matrix** number. Chapter 3's Gouterman physics is the **rationale for the metric's
SHAPE** — why a difference of two windows, why those bands, why a ratio — and **not** a claim that
magnesium is the only thing contributing to the value.

#### ⛔ The price of not explaining — and it is the whole discipline

**An unattributed number is valid exactly to the degree that everything except the product is held
constant.** That is not a philosophical caveat; it is an operating condition, and it fails easily. Two
examples, both measured in a single afternoon (2026-08-21):

- a spectral feature that separated the archive's oils at **F = 32.07** — five times better than the
  turbidity level, and non-monotone in `Q%`, so it looked like an independent axis — split **perfectly by
  calendar date** across 12 sessions and 52 fills, with no oil on both sides. A rig-or-processing era
  boundary, not a property of any product *(`SPEC_metric_research.md` §13.4)*.
- the **same oil** measured in two solvents sits `D` = **0.43–0.57** apart on the history tracker's own
  shape distance — **larger than any oil difference in the archive** on that window, and 1.7× its alarm
  threshold *(`SPEC_history_tracker.md`, "a solvent change is indistinguishable from an oil change")*.

⇒ ⭐⭐ **THE LESS YOU EXPLAIN, THE MORE YOU MUST CONTROL.** An operational metric does not lower the
standard of discipline; it **raises** it. Same solvent, same recipe, same rig, same settling rule, same
jar — because when the number moves and there is no mechanism to appeal to, the *only* thing standing
between *"the oil changed"* and *"the instrument changed"* is the protocol. This is exactly what a control
chart demands of a process, and it is why the history tracker's reference must be the mill's own lot at
`k ≥ 5` rather than a single nominated run (`SPEC_history_tracker.md` §3.4).

### 1.6 The chain, in one line

```math
2 captures \Rightarrow R(\lambda), S(\lambda) \Rightarrow A(\lambda) \Rightarrow \op{despike} \Rightarrow 3 band means \Rightarrow Q%
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
> emission lines** that fail to cancel in $S/R$ (§E.9). **Both sit outside every BAND window** the shipped
> metrics read — `Q%`'s three and `dQ100`'s two. ⚠ **But 448–626 nm is `dQ100`'s denominator**, and both
> lines fall inside it: masking them out of that `sd` shifts `dQ100` by **−0.735 ± 0.929** units (up to
> 2.34), about 11 % of its corridor. ⛔ Masking is not the fix — it *narrows* the corridor slightly, 6.846
> → 6.433 — but "harmless" is the wrong word for a band mean's ruler. On the old 600–630 anchor the 607 nm
> line lay inside a *measuring* window, which is one of the reasons that window moved (§Ea.1).

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
we can see*, not beyond it — which is the whole reason the far window behaves as it does (§E.0), and, once
that was understood, the reason the anchor was narrowed onto **620–630** so as to sit on the band rather
than straddle its foot (§Ea.1).

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

### 3.4 The far window is a measuring band — measured, not assumed

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

### 3.5 The difference is speciation, not concentration — and the test has no free parameters

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

### 3.6 ⚠ Why we cannot simply look at the two-versus-four bands

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

<!--PAGEBREAK-->


## 4. The windows and the band means

Everything downstream is built from wavelength windows — the three `Q%` reads, the two more `dQ100`
needs, and two baseline anchors that belong to the historical metric in Appendix E.

| symbol | window | what it sits on | used by | source |
|---|---|---|---|---|
| $A_{Soret}$ | **448–460 nm** | red flank of the **Soret (B)** band, ~432 nm | `Q%` | `V_SORET_BAND` |
| $A_{Q}$ | **565–580 nm** | a band in the **Q region** — assignment open, §9.4 | `Q%` | `V_Q_BAND` |
| $A_{valley}$ | **500–560 nm** | the flat window **between** the two bands | `Q%` | `V_VALLEY_BAND` |
| $A(563\ldots573)$ | **563–573 nm** | the same Q band, trimmed clear of the 581 nm crossover | `dQ100` | — |
| $A(623\ldots626)$ | **623–626 nm** | **on** the **Qy(0,0)** band, ~623–626 nm | `dQ100` | — |
| $A_{near}$ | 520–540 nm | between bands — the quieter anchor | *Appendix E only* | `PB_BASELINE_WINDOWS[0]` |
| $A_{far}$ | 620–630 nm | **on** the Qy band — a *measuring* band (§3.4) | *Appendix E only* | `PB_BASELINE_WINDOWS[1]` |

⚠ **The Soret window moved from 440–460 to 448–460 nm** when the 440–447 bins were found to be starved
and exposure-sensitive; Appendix E's tables predate that trim and are quoted on 440–460.

⚠⚠ **`Q%`'s Q window (565–580) reaches into the 581 nm channel crossover**, which
`DOC_lamp_rebuild.md` §8.1 shows is an **instrument** feature, not a band — it finds the ramp rather than
the pigment in 93 % of 110 isopropanol runs. `dQ100`'s 563–573 stops short of it deliberately. ⛔ Trimming
`Q%`'s window does **not** rescue it (measured: *d* 2.78 → 2.33–2.45, still overlapping), so the shipped
windows are **not** to be re-tuned.

![**Figure 2** — the de-spiked absorbance of both classes, with the windows the **shipped** metrics read: `Q%`'s Soret, valley and Q, and the Qy band `dQ100` pairs with them. ⛔ There is no baseline drawn because none is fitted — chapter 5 takes three plain window means off this curve and divides. The lower panel magnifies the weak-absorbance region, where **no part is signal-free** (§3.4); note the 473 and 607 nm lamp lines sitting outside every window, and how little separates the two classes inside the Q window against how much separates them at 623–626. ⚠ Appendix E's metric fits a line through two further windows, 520–540 and 620–630, which are not shown here.](metric_algebra_bands.png)

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
(`SPEC_pumpkin_peak_ratio_eval.md` §10).

### 4.2 Geometry and measured values

| window | points | centroid $\bar{\lambda}$ | green | brown | CV green | CV brown |
|---|---|---|---|---|---|---|
| Soret 440–460 | 138 | 449.98 nm | 1.1864 | 1.0855 | 4.04 % | 3.58 % |
| Q 560–580 | 137 | 570.02 nm | 0.2300 | 0.2251 | 7.52 % | 8.86 % |
| near 520–540 | 135 | 529.93 nm | 0.1231 | 0.1038 | 8.89 % | 13.31 % |
| **far 620–630** | **71** | **624.96 nm** | **0.2035** | **0.1526** | 12.99 % | 14.54 % |

The centroids matter in §E.5. **Read the $A_{Q}$ row**: 0.2300 against 0.2251, a 2 % difference against
7–9 % scatter. On its own the Q band carries no usable class information (*d* = 0.26).

**Now read the $A_{far}$ row against it.** 0.2035 against 0.1526 — the two classes differ by **33 %** in
the window that was introduced as a *baseline anchor*. That is the largest class difference of any window
in the table, and it is why §3.4 calls the far window a measuring band. The 620–630 window is only 10 nm
wide and holds a third as many points as its 600–630 predecessor, yet it separates the classes better,
because it stands **on** the Qy band instead of straddling its foot (§Ea.1).

<!--PAGEBREAK-->

## ⭐⭐⭐ 4a. `Rv` — the metric that decides the verdict  *(2026-08-25)*

Chapter 4's table ends on a sentence worth re-reading before this one starts: the **620–630 nm window
separates the classes by 33 %**, the largest class difference of any window in the table — *"and it is why
§3.4 calls the far window a measuring band."* That window was introduced as a **baseline anchor**. It
turned out to be the measurement.

`Rv` is what you get when you stop using it as an anchor and read it as the band it is.

### 4a.1 The definition

```math
R_{v} = 100\,\frac{A_{624} - A_{valley}}{A_{Q} - A_{valley}}
```

with $A_{624}$ over **622–627 nm**, $A_{Q}$ over **565–580 nm** and $A_{valley}$ over **500–560 nm** — the
same three plain means of the de-spiked absorbance chapter 4 defines. Only $A_{624}$ is new; the other two
are `Q%`'s own windows, unchanged.

**Higher is greener**, and the provisional threshold is **`T = 52`**.

⭐ **In one sentence:** *the 624 nm band's height above the valley, as a percentage of the Q band's height
above that same valley.* Both peaks measured above one datum — the line the `Absorption (bands)` plot
already draws as marker (4).

### 4a.2 It is `Q%` with the denominator swapped

```math
Q_{\op{pct}} = 100\,\frac{A_{Q}-A_{valley}}{A_{Soret}}
\qquad\qquad
R_{v} = 100\,\frac{A_{624}-A_{valley}}{A_{Q}-A_{valley}}
```

**The numerator quantity is the same.** `Q%` divides the Q band's height above the valley by the **Soret
flank**; `Rv` divides the **624 band's** height above that same valley by that same Q-band height. This is
not a new family — it is the shipped metric with its denominator replaced, and $A_{Soret}$ dropping out of
the verdict path entirely.

⭐ That single fact carries most of chapter 4a: every advantage below follows from *which* quantity sits
underneath.

### ⭐⭐ 4a.3 Why this ratio, physically — the metric and the photophysics are congruent

This is the part that does not depend on any statistic, and it survives the threshold moving.

`KB_spectroscopy_physics.md` states the four-orbital result before any of this was measured:

> A metallated ring (D₄ₕ) shows **two** Q bands (α, β); the free base (D₂ₕ) shows **four**, numbered I–IV
> from the longest wavelength. […] **Band I is the weakest in every one of them.** So a pigment whose
> Qy(0,0) is its dominant long-λ band while metallated becomes, on demetallation, the *weakest* of four.

Chapter 3 supplies the chemistry: our pigment is **protochlorophyll**, and roasting and storage convert it
to **protopheophytin** by stripping the magnesium. That conversion is exactly a D₄ₕ → D₂ₕ symmetry drop.

| | pigment | symmetry | Gouterman predicts | measured — SNV over 500–627 nm |
|---|---|---|---|---|
| **green oil** | protochlorophyll, **Mg in** | ~D₄ₕ | long-λ band dominant | **624 nm is the tallest feature**, *z* ≈ 2.2 |
| **brown oil** | protopheophytin, **Mg out** | D₂ₕ | band I becomes the **weakest of four** | **569 nm tallest** (*z* ≈ 2.75); 624 collapses to *z* ≈ 0.5–0.75 |

⇒ **624 nm is band I.** `Rv` compares band I against a shorter Q component, which makes it a **symmetry
diagnostic**: it measures the demetallation itself, not a downstream consequence of it. Protopheophytin
carries the ring-E carbonyl — a rhodofying group — so the expected intensity ordering is *rhodo*
(III > IV > II > I), and band I is still the weakest.

⭐ `Rv` is the **ratio form** of §5.8's see-saw; `dQ100` is the **difference form**. §5.8 already draws the
plank with a cap at 568 nm and the same amount removed at 624 nm. `Rv` reads both ends as one number.

### ⭐⭐ 4a.4 And this is the physical case against the Soret denominator

`DOC_lamp_410_680.md` Figure 5 says of the blue end:

> the carotenoid absorption at ~455 nm rides on top of the Soret, so the peak you can see is not the peak
> the chemistry is at

**Carotenoids have no Q bands and are not part of the porphyrin system at all.** So `Q%` divides a
porphyrin band by a window belonging to a *different pigment family*, whose concentration varies for
reasons that have nothing to do with roasting. Gouterman's account governs the numerator and says nothing
about the denominator.

`Rv` keeps both terms inside **one chromophore's Q manifold**. That is almost certainly why it absorbs a
40–45 % dose swing and three solvents where `Q%` moves 6.5 units on one oil — and it is an argument from
mechanism, not from the corpus.

### 4a.5 What it buys — the four measured advantages

| | `Rv` | `Q%` |
|---|---|---|
| **1 · archive** | **1 error / 98** labelled runs; **0 / 88** within isopropanol | **9 errors / 98** |
| **2 · solvent** | green **98.4–125.2**, brown **28.3–46.4** across isopropanol, white spirit *and* sunflower — **no overlap in any** | classes **overlap outright**; one oil moves **6.5 units** on solvent alone |
| **3 · dilution** | a **40–45 % dose swing moves it < 0.8 %** | — |
| **4 · ordering** | correct in **3 of 3** rounds of the 2026-08-24 triad | correct in **1 of 3**, and that one only because the brown oils had degraded past the green |

⭐ **Advantage 3 is the one that was not fitted.** The 2026-08-24 fresh pours carried 15–45 % more absorber
than the first pours of the same preparations, on samples that did not exist when the metric was defined.
`Rv` moved by 0.5 and 0.7 units on the two well-behaved oils. Scale-invariance is algebraic — numerator and
denominator both scale with $c$ — but here it is also **measured**.

⭐ **Advantage 4 deserves its sting spelled out.** `Q%` was right in round 002 *because the sample spoiled*:
the brown oils degraded past Lugitsch between the two rounds. A metric that reaches the right answer
because the sample changed has not earned the verdict.

### 4a.6 Two structural advantages that are not about accuracy

**It is drawable.** `Rv` needs **one** new band mean. The `Absorption (bands)` page already plots markers
(2), (3) and (4) — valley, Q band, valley level. Adding marker (6) at 622–627 makes `Rv` a **distance you
can read off the page**: on an axis where the valley is pinned to 0 and the Q band to 1, the height of the
624 band *is* `Rv`/100.

**The guards compose for free.** `Rv`'s denominator **is** `Q%`'s numerator, since
$A_{Q}-A_{valley} = Q_{\op{pct}}\cdot A_{Soret}/100$. So the two guards already in the plugin —
$A_{Soret} \ge 0.15$ and $Q_{\op{pct}} \ge 12$ — bound it below by $12 \times 0.15/100 = 0.018$. Verified
across the archive: **0 of 141 guarded reports** have a non-positive denominator, observed minimum 0.0372.
No new guard, no second code path.

⚠ Only the **lower** half of `Q%`'s domain band may be inherited. The upper bound is `Q%`'s own scale
concern: a fill reading `Q%` 23.12 is past `Q%`'s corridor but yields a perfectly good `Rv` of 42.4.

### ⛔⛔ 4a.7 Where it fails — and every failure here is measured, not feared

**1 · A diffuser silently breaks it.** `20260727B` is the archive's diffuser A/B — nine runs, all the same
green oil. Diffuser out: `Rv` = 66.5, 71.1, 73.5, 73.7. Diffuser in: 54.6, **50.3**, 65.0, **50.9**, 53.9 —
**2 of 5 read brown**, with **both guards passing on all nine**. `Q%` is untouched (15.6–17.1 in, 14.6–17.1
out). ⛔ And no cheap guard exists: a washed-out band and a genuinely weak band are the same measurement,
so any threshold that refuses the diffuser also refuses most brown runs. ⇒ **any optical change forces a
full re-validation** — a standing blocker on the lamp rebuild.

**2 · It is turbidity-sensitive, with opposite-signed slopes.** Within-oil: **+105** `Rv` per unit
turbidity on a brown oil, **−108 to −148** on a green one. Turbidity does not *create* the separation — it
**erodes** it from both sides, pushing brown up and green down toward the line. This is the whole of the
11.3-unit wobble on the one turbid oil of 2026-08-24.

**3 · The margin is thinner than the noise.** Pooled within-series sd is **5.7**; the green/brown gap at
its narrowest is **3.1**. The corpus separates, but a genuinely borderline oil has no safety margin. This
is why the gauge ships **two** classes and no *borderline* band — the width of that band is exactly what is
not yet known.

**4 · It needs the far flank.** A second-derivative check on `Rv`'s band is computable on only **44 of 98**
labelled runs, because the archive's 629.8 nm epoch has no data past the peak.

### 4a.8 ⛔ Why not `dQ100`, which scores better

`dQ100` makes **0 errors** on the same 98 runs to `Rv`'s 1. It was not adopted, and the reason should be
stated plainly enough to argue with: `Rv` is **drawable on the existing plot**, **guard-compatible without
new code**, and **interpretable as one physical quantity** rather than a z-scored difference. `dQ100` also
needs $\op{sd}$ over 448–626 rather than band means, and carries its own withdrawal history.

⇒ **The decision is on buildability and interpretability, not accuracy.** If a future corpus separates them
on accuracy, that is a reason to revisit it.

### 4a.9 Status, and what would overturn this

⛔ **`Rv` is chosen, not built.** `Q%` — chapter 5 — is what the instrument computes today and keeps the
verdict pill until `Rv` is implemented **and** pre-registered.

⛔ **The pre-registration is not waived by the decision.** Every constant here — the 622–627 window,
`T = 52`, the pedestal subtraction, the domain band — is fitted on the corpus it is scored on, exactly as
`dQ100`'s were when they were refused. The decision settles *which metric the programme builds toward*;
M9 settles *when it may carry a verdict*.

⭐ **What would overturn it**, stated in advance so it can happen:

1. the pre-registered test misclassifies more than one held-out fill, or `T` has to move to hold;
2. the lamp rebuild moves `Rv` while leaving `Q%` alone (§4a.7 case 1);
3. a preparation that removes turbidity turns out to remove pigment with it, so the sample cannot be made
   homogeneous without changing what is measured.

<!--PAGEBREAK-->

## 5. ⭐⭐ `Q%` — the metric that decides the verdict TODAY

> ⛔ **Superseded as the intended verdict by `Rv` (§1.1), 2026-08-25 — but still SHIPPING.** Everything
> in this chapter remains an accurate account of what the instrument computes, and the see-saw of §5.8 is
> the mechanism `Rv` reads the other way round: `Rv` is that see-saw as a **ratio**, `dQ100` as a
> **difference**.

### 5.1 The definition

```math
Q_{\op{pct}} = 100\,\frac{A_{Q} - A_{valley}}{A_{Soret}}
```

with the three windows of §4: $A_{Q}$ over **565–580 nm**, $A_{valley}$ over **500–560 nm** and
$A_{Soret}$ over **448–460 nm**, all read on the **de-spiked RAW absorbance**.

| | |
|---|---|
| ⛔ **no baseline** | nothing is fitted and nothing is subtracted before the three means are taken. That is the whole point — see §5.2 |
| ⭐⭐ **native sampling** | each band mean is the plain arithmetic mean of the spectrum's **own samples** inside the window, both edges inclusive. ⛔ **Not** a resampled grid: interpolating onto 0.5 nm first reads `Q%` **0.082 ± 0.023 low** |
| **sign** | higher = browner. The valley lies below the Q band, so the numerator is positive on every real fill |
| **threshold** | `T = 18.6`. Green below, brown above |

⚠ **The name inverts its own history.** The quantity was found as $V = (A_{valley} - A_{Q})/A_{Soret}$,
which is always **negative**; the shipped form is $Q% = -100V$. Anything in the archive labelled `V` or
`T_V = -18.6` is this metric with the sign the other way up.

### 5.2 Why it is built this way — a difference over a level

Two independent nuisances have to cancel, and the construction handles one with each half:

| the nuisance | what it does to the curve | what cancels it |
|---|---|---|
| **stray light, scattering, seating** | adds a roughly flat offset $b$ to everything | the **numerator is a difference** — both bands carry $b$ equally, so it subtracts out exactly |
| **concentration, path, exposure** | multiplies the whole curve by a factor $c$ | the **denominator is a level** — it scales with $c$ just as the numerator does |

⭐ That is the same immunity a fitted baseline provides (Appendix E), obtained **arithmetically instead of
by fitting** — and because nothing is fitted, no anchor can be contaminated.

⭐⭐ **The denominator earns its place by removing noise, not by adding signal** — which is the property a
normaliser must have, and the one worth checking rather than assuming. Over the 88-run archive:

| | green | brown | Cohen's *d* |
|---|---|---|---|
| $A_{Q} - A_{valley}$ — the numerator alone | 0.1175 | 0.1594 | +1.69 |
| $A_{Soret}$ — the denominator alone | 0.7518 | 0.7968 | **+0.30** |
| $Q_{\op{pct}}$ — the quotient | 15.80 | 20.00 | **+2.78** |

The Soret carries almost **no** class information, yet dividing by it lifts the separation from 1.69 to
2.78. It is carrying the nuisance — dose, path, exposure — and none of the effect. ⇒ ⭐ **`Q%`'s
discrimination lives in the numerator**, where a band relation belongs, and not in a ruler that happens to
differ between the classes.

⚠ **This corrects a natural misreading of the running pair.** There $A_{Soret}$ reads 0.828 green against
0.730 brown (*d* = −2.77, §10), which looks like a class difference. It is a **dose difference between those
two fills**; across twenty oils it washes out to 0.16.

⛔ **That distinction is not cosmetic.** A fitted line has to stand on something, and in this window there
is nothing quiet to stand on — §3.4 measures the far anchor carrying a **5.1 σ** class difference of its
own. Appendix E's metric fits through it **deliberately** and accounts for what that costs (§E.1, §E.4);
`Q%` fits nothing, so the question never arises for it.

### 5.3 What it measures

$W = (A_{Q} - A_{valley})/(A_{Soret} - A_{valley})$ is the same quantity in mechanistically pure form:
the **Q : Soret band-intensity ratio with the valley as the pigment's own zero**. §3.2 makes that ratio
the diagnostic for loss of the central Mg²⁺ — pheophytinisation, the first step of degradation.

$W = \frac{Q_{\op{pct}}/100}{1 - u}$ with $u = A_{valley}/A_{Soret}$ is an exact identity. $u$ spans 22 % across
the archive, which is the whole of why $W$ is the noisier of the two and why the shipped form divides by
the Soret alone.

⚠ We measure the Soret **flank**, not its peak at ~432 nm, so $W$ is a proxy for the true band ratio
rather than the ratio itself.

### 5.4 Performance

On the two running sets (6 re-seats each, one fill, post-rebuild):

| | green `20270729C` | brown `20260731A` | Cohen's *d* |
|---|---|---|---|
| $Q_{\op{pct}}$ | **15.891 ± 0.845** | **20.443 ± 0.260** | **+7.28** |
| $A_{Soret}$ | 0.828 ± 0.038 | 0.730 ± 0.033 | −2.77 |
| $A_{valley}$ | 0.116 ± 0.011 | 0.096 ± 0.014 | −1.69 |

Across the whole labelled archive — **88 isopropanol runs, 8 oils, both rig eras**:

| | green *(55 runs)* | brown *(33 runs)* | corridor | wrong at `T = 18.6` |
|---|---|---|---|---|
| $Q_{\op{pct}}$ | 15.801 ± 1.588 | 19.996 ± 1.370 | ⛔ **−2.807** | **7 / 88** |

⛔ **The corridor is negative: the two classes OVERLAP.** No threshold classifies all 88 correctly.
Leave-one-oil-out holds 91 %. §5.6 is where that is unpacked; it is the single most important limitation
of the shipped metric and it is not a defect of the threshold.

Run-to-run reproducibility is its strength and is genuinely excellent: pooled within-oil scatter is
**1.100** units, and two pours of one dilution have agreed to **0.076**.

### 5.5 The threshold, and what the gauge does with it

`T = 18.6` sits on the strict side of the corridor midpoint measured on the 18-run corpus that fixed it
(−18.665 in `V` units), deliberately, because **a false GREEN is the harder error to make** — a miller
told his brown oil is fine has no way to discover otherwise. No archived run lies between the two values.

The tracker band is **±1.0** units, provisional; 3σ on the measured refill scatter would be 0.64.

### 5.6 ⛔ Where it fails, and all three are measured

**1 · The classes overlap.** 7 of 88 runs sit on the wrong side, and they are not random: they cluster on
the two adjacent Spar oils, which `Q%` has never separated.

**2 · It is not solvent-portable.** `20260821LugitschA` is a **green** oil measured in white spirit:
`Q%` reads **20.79 and 20.62** — brown, twice, wrongly. In isopropanol the same oil reads green. A solvent
change moves it by +6.7 / +2.1 units, which is more than its whole decision margin.

**3 · A turbid fill can invert it.** `20280819BillaClever/003`, an opaque fill, reads **8.45** — a
confident GREEN on a brown oil, four units below anything else in the archive.

⚠ **And the margin is thinnest where it matters.** On the cleanest matched-recipe pair on record
(Lugitsch, 7 runs vs Billa Clever, 6, both fully settled) the worst brown fill clears `T` by **1.8 σ** —
6.9 % of the green-to-brown gap. Brown is the binding class: a miller told his oil is fine when it is not
is the expensive error.

### 5.7 Dilution invariance

Both halves of the construction scale with concentration $c$, so `Q%` is dilution-invariant **by
construction** — the algebra is the same as Appendix E.6's and is not repeated. Measured, a ±40 % dose
change moves it **0.12** units. ⚠ **Halving** the concentration moves it **2.19** — the invariance is
first-order, not exact, and a 2× dilution error is not absorbed.

### ⛔⛔ 5.7a The other face of invariance — it is also a BLINDNESS  *(2026-09-02)*

Every section above treats dilution invariance as a virtue, and for the job these metrics were built for
it is one: the operator's pipetting must not become the oil's verdict.

> ⛔⛔ **But invariance under scaling is invariance under *any* scaling — including one the operator did
> not intend.**
>
> Blending a **spectrally featureless** oil into a pigmented one multiplies the host spectrum by a
> constant. That is arithmetically a dilution. ⇒ **`Rv`, `V`, `Q%` and `dQ100` — every band ratio in this
> document — return the same number for the pure oil and for a 30 % blend.** So does the SNV shape
> distance `D` of `SPEC_history_tracker.md`, which divides out mean and standard deviation.

**The case is not hypothetical.** The hardest adulteration in edible oils — virgin olive oil cut with
**refined** hazelnut oil — is exactly this shape: refining strips the pigments, so the adulterant carries
no structure in 440–630 nm.

⚠ **The boundary is sharp, and it should be stated wherever these metrics are offered for identity work:**

| adulterant | effect on the spectrum | seen by a ratio or by `D`? |
|---|---|---|
| **refined / bleached** oil | scales the host down | ⛔ **no — indistinguishable from a dilution** |
| **virgin, pigmented** oil (rapeseed, sunflower) | ⭐ adds its own bands | ⭐ **yes** |
| oil of different turbidity | tilts the baseline | ⚠ partly, and confounded with §9.1's pedestal |

⇒ ⭐⭐ **For a verdict this is harmless** — nobody grades a blend. **For an identity or conformity check it
is disqualifying on its own**, and the fix is not a better ratio but a **second, non-invariant number**:
the level. `SPEC_history_tracker.md` §8.1 carries that consequence and the open measurement (8-Q1).

### 5.8 ⭐⭐ The see-saw, and why a DIFFERENCE is worth twice a level  *(2026-08-21)*

> ⭐ **Why this closes the chapter.** Everything above defines `Q%` and measures it. This section says what
> it is *doing* — and the algebra is **general**, so it also carries chapter 7's `dQ100` and, in a different
> guise, Appendix E's Pigment Index. It is the bridge from §3.3's mechanism to the arithmetic of §5.1, and
> chapter 7 points back here rather than repeating it.

§3.3 establishes that roasting **redistributes** intensity rather than removing it. Written as two
band heights — each measured above the flat valley and scaled by the Soret flank, so both are
concentration-free — that redistribution has an exact algebraic shape.

```math
h_{568} = 100\,\frac{A(565\ldots580) - A(500\ldots560)}{A(448\ldots460)} \qquad
h_{624} = 100\,\frac{A(623\ldots626) - A(500\ldots560)}{A(448\ldots460)}
```

Define the two quantities the pair can be resolved into — a **level** and a **difference**:

```math
\op{pivot} = \frac{h_{568} + h_{624}}{2} \qquad \op{tilt} = h_{568} - h_{624}
```

from which, identically,

```math
h_{568} = \op{pivot} + \frac{1}{2}\op{tilt} \qquad h_{624} = \op{pivot} - \frac{1}{2}\op{tilt}
```

Class means over the **88 labelled isopropanol runs** of the report archive:

| | `h(568)` | `h(624)` | pivot | tilt |
|---|---|---|---|---|
| green *(55 runs)* | 15.80 | 12.78 | **14.29** | 3.02 |
| brown *(33 runs)* | 20.00 | 7.55 | **13.77** | 12.45 |
| **green → brown** | **+4.20** | **−5.23** | **−0.52** | **+9.43** |

![**Figure 6** — the see-saw. **Left:** the mechanism of §3.3, drawn as a plank that tips further as the magnesium leaves. **Right:** the same thing decomposed into the numbers a metric consumes. Every band bar is the common grey **pivot** plus a coloured cap at 568 nm and exactly the same amount removed at 624 nm. ⚠ The "tilt" bars are in the Soret-scaled units used throughout this section, **not** the shipped `dQ100` scale; the figure's footnotes give both.](figures/tilt_seesaw.svg)

#### ⭐ The three consequences, and all three are arithmetic

**1 · The pivot is a nuisance, and it is most of the number.** It is **~90 %** of `h(568)` and it moves by
**−0.52** between the classes against the tilt's **+9.43** — so it carries essentially none of the roast
signal. It is total pigment, and it wobbles with concentration, path and re-seating: pooled *within* one
oil's repeat fills the two heights correlate at **+0.811** (they rise and fall together), while *between*
oils they correlate at **−0.832** (one rises as the other falls). Any metric that reads a single band
inherits that wobble; a **difference** cancels it exactly, because it is common to both terms.

**2 · A difference collects BOTH class gaps.** The two ends move in *opposite* directions, so subtracting
them adds their gaps rather than cancelling them:

```
   +4.20  −  (−5.23)  =  +9.43
```

⭐ A metric reading one end collects one gap; the difference collects both. That factor of ~2 is not a
tuning gain — it is forced by the mechanism, and it is why `dQ100`'s green→brown separation is roughly
twice `Q%`'s on the same corpus.

**3 · Reading one end is reading the tilt anyway — at half scale, plus noise.** Since
$h_{568} = \op{pivot} + \frac{1}{2}\op{tilt}$ and the pivot barely differs between classes, a
single-band metric is a **proxy** for the difference: measured over the archive, `Q%` predicts **71 %** of
`dQ100`'s variance ($r = +0.842$), and 69 % of the 624 nm band's between-oil variance — a band it never
reads. The 29 % it misses is the pivot's wobble, and that is precisely the part a difference discards.

⚠ **The Soret is the ruler.** Both heights are divided by `A_Soret`, which is what makes them
concentration-free (§9.1). Theory says demetallation should weaken it too (§3.2) — which would make the
ruler class-dependent — but **that is not visible here**: across the 20 oil means the Soret scores
*d* = **0.16**, and the small sign it carries runs the *other* way. Dose dominates it, and dose is not a
class property. ⇒ the shared denominator is not manufacturing the coupling above, and §5.2's decomposition
shows it is not manufacturing `Q%`'s discrimination either.

⚠ We nonetheless read the Soret's **flank** at 448–460 nm rather than its peak near 432 nm, because the
peak saturates. That is the least-bad choice available, not a clean one, and §E.3a's error budget is where
its cost is accounted.

<!--PAGEBREAK-->

## 6. ⭐⭐ The settling algorithm — deciding *when* the number is ready

Chapter 5 says what `Q%` is. It does not say **which look at the jar** the reported value comes from —
and on a real fill that is a separate question with its own machinery: `ClearingEvaluator`, version
**`clearing-3.0`**, living in `DevSpectralPlugin.py`. This chapter is self-contained; the full account is
`SPEC_settled_measurement.md`.

### 6.1 The problem — the sample changes while you look at it

A fresh fill is a **suspension**, not a solution (`DOC_sample_physics.md` §4.3–4.5): droplets of oil
scatter light until they dissolve or coalesce. The jar therefore goes into the instrument **muddy** and
**clears** over minutes — and `Q%` moves the whole time, because scattering lifts the whole absorbance
curve and the valley most of all.

So a single capture answers *"what was this fill like at the arbitrary moment I pressed the button"*,
which is not a property of the oil.

⚠ **And a fixed wait does not fix it**, because fills differ: some arrive clear, some clear over twenty
minutes, and some go the **other way** — they ripen, coarsen, and never settle at all.

⇒ The instrument watches the whole trajectory and decides two things for itself: **when to stop looking**
(the *gate*) and **which look is the answer** (the *read*). They are separate decisions with separate
rules, and conflating them is what earlier versions of this algorithm got wrong.

### 6.2 ⭐ What happens when a muddy jar goes in

![**Figure 6** — the whole run as a sequence. The operator fills and inserts; the instrument captures one **reference**, then loops. Each pass reduces 60 frames to one spectrum, hands it to the evaluator, and gets back one of five answers: *carry on* (the common case), or one of the four decisions shown as diamonds. When the loop ends the evaluator is asked **once more** — `finalize(rows)` — and only then does it name the answer. ⭐ Note what is *not* here: nothing asks the operator to judge when the sample is ready, and nothing waits a fixed time.](figures/settling_sequence.svg)

**Reading it left to right:** the two guards come first, because a row that cannot be read must never
reach a trend test. Then the three trend tests decide whether to keep looking. Then — after the loop, not
during it — the read rule picks the answer out of the finished curve.

| the row-level guards | |
|---|---|
| `A_Soret < 0.15` | the **measurement** is broken. Abort at once rather than spend 25 minutes of lamp on a fill that cannot produce a number |
| **too dark to read** | ⭐ **dropped before every other test**, so no trend, hunt or vertex ever sees one. ⛔ "Too dark" is **not** "broken" — a fill that is still clearing is still clearing, and the run carries on |

### 6.3 ⭐⭐ The four outcomes, on real fills

![**Figure 7** — every curve here is measured, not drawn: each panel is one archived run's own recorded trajectory. Solid green is `Q%` (left axis), dashed blue is `A_valley` — the turbidity — on its own scale (right axis), and the ring marks the value that run reported. **A** is the case the whole algorithm exists for. **B** needs almost none of it. **C** is the fill that gets worse. **D** is what happens when a fill is read before it is readable.](figures/settling_cases.svg)

| | what the curve does | what the algorithm does |
|---|---|---|
| **A · the muddy fill** | `A_valley` falls **ten-fold** over 15 minutes; `Q%` falls with it from 29.3, turns, and flattens | the gate waits, and the **VERTEX** at the minimum is the answer: **20.23** |
| **B · it arrived clear** | `A_valley` never falls; `Q%` never turns | nothing to wait for — the **FIRST look** is the answer, **20.79**, and the run is over in under two minutes |
| **C · it goes backwards** | `A_valley` **rises** steadily — the droplets are coarsening, not dissolving | **TEST C** ends the run. There is a value, but the outcome is `DEGRADING_FILL`, not "settled" — the operator is told to prepare a fresh dilution |
| **D · ⛔ the opaque fill** | it starts at `A_valley` **2.67** — nearly opaque — and clears to 0.06 over 14 minutes. `Q%` starts at **8.45**, climbs to 39, and only then settles near 20 | ⛔ the run reported **8.45** — the first look, taken through mud. On a brown oil that is a confident **GREEN** |

⭐⭐ **Panel D is the argument for the whole chapter in one picture.** The first look is a perfectly good
answer in panel B and a catastrophic one in panel D, and nothing in a *single* capture distinguishes them.
Only the trajectory does.

### 6.4 The gate — when to stop looking

Three tests run on `A_valley`, the turbidity. Each asks a different question, and TEST C exists because
the first two agree on a fill that is getting worse.

| | asks | rule | constants |
|---|---|---|---|
| **A · flat?** | has the turbidity stopped falling? | the rate between rows at least `GATE_SPAN_SECONDS` apart is below θ, twice consecutively | `THETA_PER_MINUTE = 0.005`, `GATE_SPAN_SECONDS = 70`, `GATE_CONSECUTIVE = 2` |
| **B · re-clouding?** | has it started rising again? | a rising trend over the last `m` rows moves the hunt window forward | `TREND_ROWS = 5`, 2σ |
| **C · degrading?** | is it ripening rather than settling? | a **significant** monotone rise — significance, not magnitude — ends the run | `DEGRADE_TREND_ROWS = 10`, `DEGRADE_SIGMA = 4.0`, `DEGRADE_RISE_FRACTION = 0.01` |

⭐ **θ is a RATE, not a per-sample step**, so the gate behaves identically on live frames and on a replayed
curve at any cadence. That correction came from a replay: *"j = 2 windows"* is only right when a window is
~35 s long, and on 3.3-minute samples the same rule fired two samples late.

⭐ **Raising θ from 0.0017 to 0.005 cost nothing and saved dose** — measured on the one archived fill that
actually cleared, the gate promotes **3.3 minutes earlier** and the value read is **bit-identical**. It can
afford to, because θ decides only when to *stop looking*; the answer is protected by the read rule.

⛔ **TEST C is the mirror image of TEST B, not another instance of it** — same observable, opposite
prognosis. Panel C's fill rises at 0.0012/min, far *below* θ, so TEST A calls it flat and TEST B stays
silent while the run stalls without a word. ⚠ It must not be "fixed" by lowering θ: TEST B moves the hunt
window forward, which is right for a re-cloud and catastrophic for a ripening fill, because it would
discard the only good look in the run.

### 6.5 The read — which look is the answer

| branch | `readAs` | the answer | panel |
|---|---|---|---|
| `arrived-clear` | `FIRST_SETTLED_WINDOW` | the **first** look — the curve never turned, so nothing later is better and everything later has had more lamp on it | B, D |
| `was-clearing` | `VERTEX` | a vertex fitted around the `Q%` **minimum**, wherever it sits | A, C |

The branch is decided by **depth** — how far below its first look the minimum lies — against the measured
single-window noise: `SINGLE_WINDOW_SIGMA = 0.063` (10 repeats, jar untouched, at `FRAMES = 60`) times
`DEPTH_SIGMA_MULTIPLE = 2.0`.

⭐⭐ **And `clearing-3.0` reads at the END of the run, not when the gate fires.**

The reason is that **a noise dip looks exactly like a minimum while you are standing on it.** A run of 36
windows offers 36 chances for scatter to produce a low point, and the deepest of them is not necessarily
the one the chemistry made. Something has to separate the two, and it cannot be depth — the spurious dips
are often the deeper ones.

⭐ **What separates them is what happens NEXT.** After a *real* minimum the fill has stopped clearing and
only browning is left — and browning goes **one way**. So the curve should climb from there and never come
back down. After a *noise* dip the curve climbs too, and then falls back, because nothing has actually
changed. That is the whole rule:

> **The drawdown** of a candidate is the largest fall-back the curve makes anywhere after it. A candidate
> is admissible only if `drawdown ≤ 10 × tailSd`, where `tailSd` is the run's **own** noise floor — the
> residual scatter of the last `TAIL_ROWS = 8` rows about a straight line.

⚠ Note what the rule is measured against: **not** a fixed threshold in `Q%` units, but the noise *this run*
happens to have. A steady run is judged strictly and a scattery one leniently, which is the correct way
round.

![**Figure 8** — the rule on the run that motivated it. **Top:** `20280819BillaClever/006`, the whole trajectory. Two candidate minima, and the fate of the curve after each one is completely different — it falls back after the first (pink) and only climbs after the second (green). **Bottom:** the same two, zoomed. The dashed line is the *running high* after the candidate; the arrow is the largest fall-back below it. The first candidate's drawdown is **39.7 × tailSd** and is refused; the second's is **2.5 ×** and stands. ⚠ The 18.989 marked here is what `clearing-2.0` actually reported for this run — the figure shows what version 3.0 changed, not what ships today.](figures/settling_drawdown.svg)

On this run the arithmetic is:

| | candidate | drawdown | ÷ tailSd | verdict |
|---|---|---|---|---|
| the noise dip | 18.989 *(the vertex through the lowest row)* | 0.3329 | **39.7 ×** | ⛔ refused |
| the real minimum | 19.782 | 0.0212 | **2.5 ×** | ✅ accepted |

with `tailSd = 0.0084 Q%`. ⭐ **The threshold sits in the gap between them**, not at either end: 10 is
roughly mid-way between the 2.5× a real minimum produced and the 39.7× a spurious one did, on a corpus
where that gap ran about 14-fold. ⚠ It is a **chosen** constant with margin, not a derived optimum.

⇒ The cost of the rule is that the answer cannot be named while the run is going — `finalize(rows)` needs
the rows *after* a candidate to judge it, and at least three usable rows in total, since nothing could be
fitted through fewer. ⭐ **The benefit is that run 006's answer moved 0.79 units**, which is nearly four
times the whole clean-set scatter, and in the direction that mattered.

⛔⛔ **That hook spans two repositories and fails silently if the halves disagree.** An old core with a new
plugin is not an error: `finalize` simply never runs — no exception, no log line — and the answer quietly
reverts to the gate-time read. On one archived run that is **19.782 silently becoming 18.989**.
`MonitorEngine` therefore carries an explicit `SUPPORTS_FINALIZE = True` flag that the plugin checks
*before* a drop of lamp is spent.

### 6.6 The outcomes — and the ones that carry no value

`MonitorOutcome` is a **closed** set, and every member is said out loud to the operator. ⛔ An outcome
without a value must always say *why*, or the operator learns to read a missing number as a bug.

| outcome | value? | meaning |
|---|---|---|
| `SETTLED_IMMEDIATE` | ✅ | the curve never turned — the first look is the answer *(panels B, D)* |
| `SETTLED_AFTER_CLEARING` | ✅ | it cleared in the beam — vertex read *(panel A)* |
| `DEGRADING_FILL` | ✅ | TEST C — the fill was going backwards. The first look stands as the least contaminated one, **but the run did not settle** *(panel C)* |
| `COMPLETED` | ✅ | a plain burst finished its frames |
| `NEVER_SETTLED` | ⛔ | a cap was hit with the gate never firing |
| `MEASUREMENT_BROKEN` | ⛔ | below the Soret floor |
| `CANCELLED` · `STALLED` · `FAILED` | ⛔ | the operator stopped it · frames stopped arriving · the evaluator raised |

⚠ **`SETTLED_IMMEDIATE` is misnamed and deliberately not renamed.** It once meant "settled at once"; it now
means "the curve never turned", which can be reached *minutes* into a run — panel D reaches it after 46
windows. The string is persisted in every saved record, and renaming it would silently orphan them.

### 6.7 ⚠ What this does not yet do

⭐ **The read rule is versioned, and it has to be.** `evaluatorVersion` is stamped into every record —
`clearing-1.0` read the look at which the gate finished confirming, `2.0` the first look unless the curve
turned, `3.0` the end-of-run drawdown read. ⛔ **And "clearing-2.0" names two different algorithms in the
archive**: TEST C changed a read without bumping the string, and the replay harness caught it on its first
run. Any recomputation of archived numbers must be able to say which rule produced them — which is why
Figure 7's panels carry their version in the caption line.

⛔⛔ **An absolute `A_valley` ceiling is specified and not built** (`ROADMAP.md` item M3). It is exactly
what would have refused panel D before it produced a number, and it is metric-independent — it refuses a
fill that should not be measured at all, whatever the metric. **It is the highest-value unbuilt item on
this page.**

⛔ **`Q%` is the only metric ever monitored.** `dQ100` has never been recorded per frame — neither
`A(563–573)` nor `A(623–626)` exists in any archived record — so **no `dQ100` settling curve has ever been
observed**, and none of this chapter's rules have been tested against one (§7.4, `ROADMAP.md` item W8).

<!--PAGEBREAK-->

## 7. ⭐ `dQ100` — reading both ends of the see-saw

> ⚠ **Status.** `dQ100` is **not** the verdict source. Edwin's decision of 2026-08-21 keeps `Q%` on the
> gauges, the history tracker and the too-brown verdict, and ships `dQ100` as a **scalar printed beside
> it** — no pill, no gauge, no alarm — until it has been pre-registered and tested out of sample.
> `ROADMAP.md`'s 2026-08-21 evening block is the decision; §7.4 is why.

### 7.1 The definition

```math
dQ100 = 100\,\frac{A(563\ldots573) - A(623\ldots626)}{\op{sd}\,A(448\ldots626)}
```

on the de-spiked RAW absorbance, **native sampling**, no baseline. Higher = browner; **zero is a real
landmark** — negative means the 624 nm band stands *taller* than the Q band, the intact-pigment state — so
there is no offset constant. `T = 30.0`.

⚠ The sampling convention is load-bearing and was nearly shipped wrong: resampling onto a 0.25 nm grid
first shifts runs by up to **0.889** units and moves `T` from 30.03 to 29.64. They are different metrics.

### 7.2 Its relation to `Q%` — they read one see-saw in two places

§5.8 derives this and Figure 6 draws it. In brief: write the two red band heights above the valley,
scaled by the Soret, and resolve them into a **pivot** (their mean) and a **tilt** (their difference).
`Q%` is then the pivot plus **half** the tilt; a difference metric is the **whole** tilt with no pivot.

| | green `20270729C` | brown `20260731A` |
|---|---|---|
| 568 nm end *(= `Q%`)* | 15.89 | 20.44 |
| 624 nm end | 10.92 | 7.46 |
| **pivot** | **13.41** | **13.95** |
| **tilt** | 4.97 | 12.98 |

⭐ The pivot — total pigment — moves by **0.54** between the two oils; the tilt moves by **8.01**. The
consequences are §5.8's three: the pivot is a nuisance and most of `Q%`'s number; a difference collects
both class gaps instead of one; and `Q%` is therefore a **proxy** for the difference, at half scale plus
the pivot's wobble. Measured over the archive, `Q%` predicts **71 %** of `dQ100`'s variance ($r = 0.842$).

### 7.3 Performance

| | green `20270729C` | brown `20260731A` | Cohen's *d* |
|---|---|---|---|
| $dQ100$ | 13.746 ± 5.745 | 47.369 ± 4.714 | **+6.40** |

Across the 88-run archive, against `Q%` on identical runs:

| | corridor | pooled within-oil sd | scatter as % of the class gap | wrong at its own `T` | leave-one-oil-out |
|---|---|---|---|---|---|
| $Q_{\op{pct}}$ | ⛔ −2.807 | 1.100 | 26.2 % | 7 / 88 | 91 % |
| $dQ100$ | ⭐ **+6.846** | 4.308 | **10.7 %** | **0 / 88** | **100 %** |

⭐ **Read the two scatter columns together.** `Q%` is five times tighter in raw units and still the worse
metric, because what a verdict spends is scatter **per unit of the decision** — and there `dQ100` is 2.4×
better. On the matched-recipe settled pair its separation is *d′* = 20.0 against `Q%`'s 10.7, and its
worst brown fill clears `T` by 4.4 σ against 1.8 σ.

It also survives the two failures of §5.6: on the white-spirit green oil it reads −4.9 (**green**,
correctly), and on the opaque fill it reads 180.7 — a broken-looking number rather than a confident wrong
verdict.

### 7.4 ⛔ Why it does not own the verdict

**1 · Its headline result is conditional on one contested label.** Relabel `Spar Premium` green — one
tube, one evening, three runs — and `dQ100`'s corridor collapses to −0.280 with 2/88 wrong.
`SPEC_capture_quality.md` §16.31.3a's rule is that no statistic may be quoted under a labelling derived
from it, and that relabel came from the **red far slope**, which is the region `dQ100` reads. `M448`
(Appendix E) cleared that bar by separating under all three treatments of the tube. **`dQ100` does not.**

**2 · Every constant is fitted on the corpus it is scored on** — the 563–573 half-width included.
Leave-one-oil-out at 94 % says the *choice* is stable; it does not make the corridor value free.

**3 · An optics change still eats most of the margin.** A paper diffuser moves it **14.9 %** of the class
gap — 0.9× its own corridor — against `Q%`'s 16.9 %. Marginally the steadier of the two in relative terms,
but §5.6's lesson stands for both: ⛔ **test against the lamp rebuild BEFORE ordering emitters.**

⭐ **What would change this** is a **pre-registration**: freeze the windows, the threshold and the
predictions in writing before the next rig session, then let new fills test them on data the metric has
never seen. That is `ROADMAP.md`'s item M9, and it is the only route from "best candidate" to "validated".

<!--PAGEBREAK-->


## 8. Colour

The evaluation tab carries ten colour chips. They are a presentation feature, and this chapter exists
partly to say why they are **not** a verdict input.

### 8.1 How a spectrum becomes a colour

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

### 8.2 The three families

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

### 8.3 ⛔ Measured: colour does not discriminate these oils

| chip | green *(n = 12)* | brown *(n = 6)* |
|---|---|---|
| Intrinsic | H 298–300° | H 298–300° |
| Intrinsic-perceived | H 67–69° | H 68–69° |
| Perceived | H 70° | H 70–71° |
| hue-normalised variants | H 300° · S 38 % · L 34 % | **identical** |

This **confirms** `SPEC_capture_quality.md` §16.10.15 ("colour channels do NOT discriminate this oil
pair") on post-rebuild data, and extends it from raw channels to the full HSL retrieval path.

**Why it fails is instructive.** Colour is a *broadband integral* — the CMFs weight the whole visible
range — so the narrow, structured differences that carry the class signal (§3.5: a redistribution inside
a 50 nm slice of the Q region) are averaged away against the enormous Soret absorbance that both oils
share. The metric wins precisely because it looks at **narrow windows**; colour loses for the same reason.

**⇒ The chips are worth showing and must never be thresholded.**

<!--PAGEBREAK-->

## 9. What these numbers do not mean

### 9.1 A band mean is not dilution-invariant

$A_{Soret}$ separates our two sets at *d* = 2.31 and $B_{Soret}$ at *d* = 2.70, with no overlap. **Do not
use them.** The two sets happen to share a dilution recipe, so the comparison is valid only *within* that
accident. ⭐ §5.2 measures the same trap from the other side: across **twenty** oils $A_{Soret}$ scores
*d* = 0.16 — it is class-blind, and what looks like separation on one pair is dose. Only ratios divide the common factor out — which is why the UI marks ratios in bold as decision
metrics and shows the band means without thresholds.

### 9.2 A ratio is invariant only if BOTH sides are corrected the same way

> **A ratio is dilution-invariant if and only if its numerator and denominator are both pedestal-free and
> corrected the same way.**

The legacy $G = D_{Q}/A_{clarity}$ and $G' = D_{Q}/A_{blue}$ apply the correction to **one side only** — a
locally baseline-corrected numerator over an uncorrected denominator. They are not merely weak
discriminators; they are *structurally* incapable of dilution invariance (`SPEC_capture_quality.md`
§16.14.3).

### 9.3 ⚠ The verdict ladder — and why only one rung carries a pill

The dev tab grew **three** readings of the same capture, on three different scales. It is worth knowing
what happened to each, because the numbers are still printed and only one of them decides anything:

| | metric | its threshold was | today |
|---|---|---|---|
| **1** | $B_{Soret}/(B_{Q} - r_{Q})$ — baseline **and** pedestal | 10.6 | ⛔ gauge **retired** (§16.20) |
| **2** | $B_{Soret}/B_{Q}$ — baseline only, **the Pigment Index** | 12.5 | ⛔ was the verdict until 2026-08-21 → **Appendix E** |
| **3** | $A_{Soret}/A_{Q}$ — raw | 4.4 | ⛔ gauge **retired**; still printed, deliberately **with no verdict** |
| **4** | $Q_{\op{pct}}$ — chapter 5 | — | ⭐ **18.6, and the only gauge the plugin now builds** |

⛔ **Rung 3 is the cautionary one.** On post-rebuild data the raw ratio does not separate the classes at
all — green 5.387 ± 0.510 against brown 4.842 ± 0.290, Cohen's *d* = 1.20, with the lowest green run
(4.863) below the highest brown one (5.340). No threshold classifies all 28 archived runs. Its shipped
`T = 4.4` sat **below the entire brown class** (minimum 4.622) and therefore called every run of the brown
S-Budget oil *"good — green"*. It is still shown, without a pill, for continuity with older reports.

⚠ **The durable lesson, and the reason this section survives its own subject matter: only VERDICTS are
comparable, never the numbers.** These are ratios of different quantities and their thresholds are not
interchangeable — 10.6 belonged to rung 1 and 12.5 to rung 2, and that 10.6 was *also* the old 600–630
gauge's threshold is a coincidence of arithmetic, not a shared scale (`SPEC_roast_ampel.md` §2b).
⛔ The same applies to `Q%` at 18.6 and `dQ100` at 30.0: nothing carries across.

### 9.4 ⚠ We do not know what the 560–580 band is

Two candidates, and they are not equivalent: the **Q(1,0)** vibronic satellite of the intact pigment, or a
**Qx** band of protopheophytin. Since 560–580 is the index's *denominator*, the difference is not
academic — if it is the degradation product, the metric is a literal *intact ÷ degraded* ratio.

Evidence favours the second (§3.5: `A_Q` equal across classes while the 572 feature is *stronger* in
brown), but **no source we hold assigns this band**, and the comparison is between two bottles rather than
one oil before and after demetallation. Open: `SPEC_pumpkin_peak_ratio_eval.md` §15.5.

### 9.5 Precision is not correctness, and these are re-seat numbers

Both restated from §1.4 because they are the two most commonly dropped caveats. **T = 12.5 is
unvalidated**; and σ_fill — the scatter a real single measurement is subject to — is unmeasured for brown.

<!--PAGEBREAK-->

## 10. Reference sheet

Green = `20270729C`, brown = `20260731A`, both the mean of six runs.

**The verdict metric, the metric it replaces, and the companion scalar**

| shown as | symbol | formula | green | brown | *d* |
|---|---|---|---|---|---|
| ⭐ **`Rv`** *(the verdict, ch. 4a)* | $R_{v}$ | $100(A_{624} - A_{valley})/(A_{Q} - A_{valley})$ | **66.9** | **37.0** | **+3.95** |
| **`Q%`** *(shipped today)* | $Q_{\op{pct}}$ | $100(A_{Q} - A_{valley})/A_{Soret}$ | **15.891** | **20.443** | **+7.28** |
| `dQ100` *(scalar only)* | — | $100\,[A(563..573) - A(623..626)]/\op{sd}A(448..626)$ | 13.746 | 47.369 | +6.40 |
| Soret · 448–460 | $A_{Soret}$ | mean $A_{d}$ over 448–460 | 0.8281 | 0.7304 | −2.77 |
| Q · 565–580 | $A_{Q}$ | mean $A_{d}$ over 565–580 | 0.2478 | 0.2448 | −0.15 |
| valley · 500–560 | $A_{valley}$ | mean $A_{d}$ over 500–560 | 0.1162 | 0.0955 | −1.69 |
| Q · 563–573 | — | mean $A_{d}$ over 563–573 | 0.2331 | 0.2314 | −0.09 |
| Qy · 623–626 | — | mean $A_{d}$ over 623–626 | 0.2069 | 0.1502 | −2.29 |
| window sd · 448–626 | — | $\op{sd}$ of $A_{d}$ over 448–626 | 0.1915 | 0.1716 | −3.07 |

⚠⚠ **Read the `Rv` and `Q%` rows against each other, and do not skip past it.** On *this particular pair*
`Q%` separates **better** — *d* = +7.28 against `Rv`'s +3.95. That is not a misprint and it is not
explained away: this sheet compares **one** green series against **one** brown series, and this pair is
one `Q%` handles well. `Rv`'s case is not that it beats `Q%` on every pair; it is that across the **whole**
labelled archive it misclassifies **1 run to `Q%`'s 9**, and that it holds across solvents and dose where
`Q%` does not (§4a.5). ⭐ A metric can lose a chosen pair and still win the corpus — and a document that
only printed the pairs where the new metric wins would be worthless.

⚠ Note also `Rv`'s scatter on the green series: sd **8.9** over six runs (54.1–81.6) against the brown
series' 5.9. That is §4a.7 case 3 — the margin is thinner than the noise — visible in one cell.

⭐ **Read the $A_{Q}$ and $A(563..573)$ rows.** On their own the Q band carries **no** class information
(*d* = −0.15 and −0.09). It becomes decisive only when referenced — to the valley (`Q%`) or to the Qy band
(`dQ100`). The band is not the signal; the **relation** is (§5.8).

**Historical — the Pigment Index and the legacy metrics** *(Appendices D and E; quoted on the old
440–460 Soret window)*

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
| **Pigment ratio · linear baseline** *(the OLD verdict)* | **Pigment Index** | $B_{Soret} / B_{Q}$ | **15.499** | **10.160** | **10.20** |
| **· with the pedestal put back** | — | $B_{Soret} / (B_{Q} - r_{Q})$ | **12.380** | **8.590** | **9.33** |
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
| **`Q%` windows** | **448–460 · 500–560 · 565–580 nm** | `V_SORET_BAND` / `V_VALLEY_BAND` / `V_Q_BAND` |
| **`Q%` verdict threshold T** | **18.6** *(as `T_V = −18.6`)* | `SPEC_v_metric_integration.md` |
| `Q%` tracker band | ±1.0 units *(provisional)* | — |
| `dQ100` windows | 563–573 · 623–626 · sd 448–626 nm | — |
| `dQ100` threshold T | 30.0 · green < 26.6 · brown > 33.5 | `SPEC_metric_research.md` §12.8 |
| sampling convention | **NATIVE** — no resampling, both metrics | §5.1, §7.1 |
| *historical* far anchor | 520–540 + 620–630 nm | `PB_BASELINE_WINDOWS` |
| *historical* pedestal residual $r_{Q}$ | −0.0184 A *(that anchor's own, §Ea.2)* | `PB_R_Q` |
| *historical* threshold T | 12.5 on the Pigment Index | `SPEC_capture_quality.md` §16.20.4 |
| *historical* threshold T | 10.6 on the pedestal-corrected index | `SPEC_roast_ampel.md` §2b |

<!--PAGEBREAK-->

## Appendix A — the least-squares fit

§E.2 fits a straight line through the two anchor windows. This is what "fit" means.

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
| ↳ `METRIC_ANCHOR=600 …` | the same, on the superseded 600–630 anchor — the Appendix Ea comparison column |
| `diagnostics/qband_shape.py` | the speciation-vs-concentration test and the resolution measurement |
| `diagnostics/brown_series_d.py` | the series-D discrimination statistics |
| `diagnostics/metric_algebra_plots.py` | figures 2–4 |
| `docs/tools/build_pigment_figures.py` | figure 1 |

Cohen's *d* is the pooled-SD standardised difference on n = 6 per class (defined in §1.3); with six runs
a *d* of this size is bounded well away from zero but its point value is loose.

⭐ **`METRIC_ANCHOR` is the one switch that reproduces this whole document on either anchor.**
`metric_walkthrough.py` reads it, and `metric_algebra_plots.py` follows whatever the walkthrough is set
to, so text and figures cannot drift apart. Default **620** — the shipped window. Every number in
chapters 4–5 and every figure 2–4 comes out of one run at that default; Appendix Ea's comparison column comes
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
14 %. §E.4 explains why: the uncorrected Q band carries no class information.

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
| **Pigment Index** *(Appendix E, for comparison)* | **10.20** | the only usable one |
| $G'$ | −5.33 | **sign inverted** — brown reads higher |
| $D_{Q}$ | −2.48 | inverted |
| $G$ "Greenness" | −1.99 | inverted — despite the name |
| $A_{blue}$ "Soret" | 1.18 | weak |
| $A_{clarity}$ | 0.54 | none |
| $S/Q_{legacy}$ | **0.11** | **useless** |

> **⚠ Three are inverted with respect to their names.** "Greenness G" reads *higher* on the brown oil. The
> names are historical; `SPEC_pumpkin_peak_ratio_eval.md` §11 found the direction reversed and the fields
> were renamed once already ("Browning A_blue" → "Soret A_blue"). **Treat every label on the legacy tab as
> a hypothesis, not a description.** §9.2 adds that $G$ and $G'$ cannot be dilution-invariant either.

<!--PAGEBREAK-->

<!--PAGEBREAK-->

## Appendix E — ⭐ The Pigment Index, the baseline-corrected metric  *(historical)*

> ⚠ **This was chapter 5 until 2026-08-21, when `Q%` became the shipped verdict source and
> this metric stopped being one.** Nothing in it is retracted — the baseline algebra, the
> dilution-invariance proof and the error budget are all still correct, and the far-anchor
> history in Appendix Ea is still the best account of why that window sits where it does.
> It is an appendix because it no longer decides anything. Its section numbers were `5.x`;
> they are `E.x` here.

### E.0 ⭐ Why the correction is needed — the mechanism, read as a change of SLOPE

> This was **chapter 3.4** until 2026-08-21. It is the physical motivation for everything below, and
> it is here rather than in the physics chapter because every quantity in it — the two anchor windows,
> the fitted line, `linearBaselineCorrected` — belongs to this metric and to no other. The shipped `Q%`
> fits no line at all (§5.2).

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

— which reproduces §E.3's fitted **8.56 / 5.22 × 10⁻⁴** to within 1 %, the remainder being the anchor
windows' *internal* slope that the least-squares fit does see and the two-centroid chord does not (§E.5).

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

<!--PAGEBREAK-->

### E.1 What problem the baseline solves

Re-seating the jar tilts the beam slightly, and that enters the absorbance curve as **an offset and a
slope together** — the whole curve lifts *and* rotates. A constant subtraction removes the offset;
standard normal variate removes offset and scale; **neither removes a slope.** A straight line fitted
through two separated anchor windows removes both (`SPEC_capture_quality.md` §16.10.2).

This construction is not new and not ours. It is the **Morton–Stubbs correction for irrelevant absorption**,
introduced by Morton and Stubbs in 1946 for the spectrophotometric assay of vitamin A in liver oils, and still
in pharmacopoeial use today — in its three-point **Allen** form it is the standard correction for serum
haemoglobin against interference from bilirubin and turbidity. *Irrelevant absorption* is the pharmacopoeial
term for any absorbance that does not come from the analyte: impurities, degradation products, or, as here, a
scattering pedestal. The method asks two things of the measurement: that this irrelevant absorption is
**linear across the analytical window**, and that the anchors it is fitted from lie **outside the analyte's own
absorption**, so that what they measure is background and nothing else.

Naming it matters, but not as a certificate. Morton–Stubbs rests on two conditions, and this instrument
satisfies neither of them.

The first is that the irrelevant absorption is **linear** across the window. A scattering pedestal is convex,
so a straight chord over-subtracts in the middle; the size of that over-subtraction is the residual $r_Q$ to
which `DOC_pedestal_correction.md` is devoted. It is worth about a quarter of the Q band at working strength.

The second is that the flanking anchors contain **none of the substance being measured**. Ours plainly do. The
red anchor at 620–630 nm sits on the pigment's own Qy flank, and comparing it against the scattering law that
should govern a true background — the pedestal at 625 nm can be at most about half its value at 530 nm for
small particles, or three-quarters for large ones — puts between **half and four-fifths of that anchor's
absorbance down to pigment rather than background**. By the method's own standard it is not a correction
window at all.

Neither deviation is an oversight, and the second is deliberate. Removing the Qy flank from the anchor has
been tried, and the oil classes then overlap: the contamination is carrying the speciation signal the metric
exists to detect. Nor does it break the dilution invariance derived later in this chapter, because anchor
pigment scales with concentration exactly as the bands do and divides out of the ratio.

What it does cost is comparability. Because a concentration-proportional amount is subtracted from both bands
before the ratio is taken, $M_\infty$ is not the pigment's Soret-to-Q ratio in any absolute sense — it is that
ratio as seen through this window, on this instrument. That is the deeper reason the threshold is tied to this
rig and this recipe rather than to the molecule.

So the honest statement is narrower than "we use the standard method". We use its construction, knowingly
outside its stated conditions, and the two departures are quantified above. Naming it earns its place by
supplying those conditions as a checklist — which is how the departures came to be measured at all.

### E.2 The definition

Take every grid point inside **either anchor window** — $W_{near}$ (520–540 nm, 135 points) and
$W_{far}$ (620–630 nm, 71 points), in the notation of §4.1 — and fit **one straight line** through all
206 of them at once.

The line is $A = m\lambda + c$, with **$m$ its slope** in absorbance per nanometre and **$c$ its
intercept** — the value the line would take at $\lambda = 0$ nm. The intercept has no physical meaning on
its own; it is simply the second number needed to pin a line down once the slope is chosen. What matters
is the line's *value across our window*, which §E.3 tabulates.

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

### E.3 What the correction does to each band

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
and it is the whole story of §E.4.

> **The fitted line is now roughly twice as steep** as it was on the 600–630 anchor (+8.56 against
> +4.81 × 10⁻⁴ A/nm for green). Nothing about the oil changed: the far anchor moved 10 nm redder and
> 33 % higher up the Qy flank, so a line pinned through the same near window has to climb harder to reach
> it. Both lines cross at ≈525 nm, inside the near anchor, which is where two lines fitted through the
> same window must meet.

![**Figure 3** — the same two curves after each has had its own baseline subtracted. The two anchor windows are pinned to zero by construction; everything else is now measured relative to them.](metric_algebra_corrected.png)

### E.3a What the asymmetry costs — the error budget it implies

The table above is usually read as a statement about signal. It is equally a statement about error, and in
that reading it is much sharper. If the baseline lands in the wrong place by some small amount, the two bands
do not suffer equally: the same absolute error is divided by 1.13 at the Soret and by 0.073 at the Q band.

| a 0.001 A baseline error is worth | on the metric |
|---|---|
| at the Q band | **1.4 %** |
| at the Soret | 0.09 % |

The metric is therefore about **fifteen times** more sensitive to where the baseline lands under the Q band
than under the Soret — the ratio is simply $B_{Soret}/B_{Q}$, so it is exactly the band asymmetry read as an
error budget. The figure grows as the fill weakens: at roughly half the standard concentration the corrected
Q band falls to 0.036 A and the same error costs 2.8 %, a seventeen-fold asymmetry
(`SPEC_capture_quality.md` §16.24.2). Weak fills do not merely add noise; they multiply the leverage of every
error that reaches the denominator. Everything at the blue end is a rounding error, and the precision of the whole
construction is set by one number: the fitted line's height at roughly 570 nm.

This overturns the intuition that the geometry suggests. The Soret window sits **outside** both anchors — it
is an extrapolation some 80 nm beyond the nearest one, which looks like the exposed end and is the first thing
a reader worries about. It is not: the baseline lands near zero there, so the long lever costs about one per
cent. The fragile band is the **interpolated** one, sitting between the anchors where the geometry is
comfortable. The quantity to reason about is not how far a window is from its anchors, but what fraction of
that window's absorbance the baseline removes.

### E.3b The objection this raises, and what the archive says

If the denominator is that exposed, and if the red anchor is the noisier of the two — it is a third the width
of the near window, sits where the lamp is dimmest, and rides the Qy flank — then the metric ought to be
hostage to it. On one archived set the far anchor scatters by 0.031 A between re-seats of a single fill, while
the entire corrected Q band is 0.068 A. Roughly two fifths of that scatter feeds the baseline at the Q band,
so a denominator built this way should carry something like 0.013 A of noise. The measured figure is
**0.0019 A**, some seven times smaller.

The reason is that the far anchor and the Q band do not wander independently. Across the runs of a set they
move together, and what the subtraction removes is largely the part they share. Measured as a correlation
between the two band means, run by run within a set, the figure runs from 0.84 to 0.99, and the corrected
band's scatter comes out four to eighteen times below what independent noise would predict.

That result needs one qualification, because part of that agreement is trivial. The fill also changes slowly
during a set, and both bands follow concentration, which would correlate them whatever else were true.
Removing that axis and correlating what remains separates the two cases. In one set the agreement survives
almost untouched — concentration accounts for three per cent of the far anchor's variance, and the two bands
still track at 0.99, which is common-mode rejection in the strict sense. In another, concentration accounts
for most of the variance and the remaining correlation falls to 0.34, so there the subtraction is removing a
concentration drift that the ratio would have divided out anyway. Both mechanisms are present, in proportions
that differ from fill to fill.

What survives the qualification is the measured consequence rather than a single explanation: the corrected
Q band's scatter really is far below the independent prediction in every set examined. What varies is how
much credit the baseline deserves for it, and this is one session's worth of evidence across five sets. It is
recorded here because it answers the objection that §3.4 otherwise leaves open — an anchor placed on signal,
and on the noisiest part of the spectrum, would seem to be the worst possible choice for the denominator, and
in practice it is not.

### E.3c Why that is not a coincidence — the two windows share one axis and differ on the other

There is a physical reason the arrangement behaves this way, and it is worth stating because it turns a lucky
empirical result into a designed one. The two windows sample the same Q manifold of the same molecule, and
that manifold can be moved along two independent axes.

The first is simply **how much pigment is in the beam** — concentration, path length, how the jar happens to
sit. Beer–Lambert scales every band of a fixed pigment population by the same factor, so this axis moves the
far window and the Q window *together*. It is the axis that varies between re-seats of one fill, and it is
precisely what the correlation of §E.3b measures. That the correlation is *positive* is the diagnostic: if
speciation were driving the run-to-run scatter, intensity would be moving *between* the two windows and they
would vary in opposition.

The second is **speciation** — the loss of magnesium that turns protochlorophyll into protopheophytin. As §3.3
describes, that lowers the symmetry from $D_{4h}$ to $D_{2h}$, lifts the degeneracy of the Q states and
redistributes intensity out of the reddest band toward the blue. This axis moves intensity *from* one window
*into* the other, and leaves the total roughly where it was.

The two axes are cleanly separable in the archive, and the separation is stark:

| between green and brown | green | brown | Cohen's *d* |
|---|---|---|---|
| far window alone | 0.1566 | 0.1526 | **0.08** |
| Q window alone | 0.1792 | 0.2251 | −0.95 |
| Soret window alone | 1.0353 | 1.0855 | −0.35 |
| **far ÷ Q — the split between them** | 0.8673 | 0.6750 | **3.43** |

**No single window separates the classes.** The far window on its own is worthless for it, at *d* = 0.08. What
separates them is how the intensity is *divided* between the two, which is exactly what a redistribution
mechanism predicts and what a change in amount cannot produce.

This is what makes the far anchor defensible despite §16.10.2a's second violation. It shares the amount axis
with the band it is subtracted from, so the fluctuations they have in common — seating, path, concentration —
partly cancel in the subtraction. And it differs from that band on the speciation axis, so the quantity the
metric exists to detect survives the same subtraction. An anchor genuinely free of pigment, as Morton–Stubbs
requires, would share neither: it would cancel less noise and carry no signal. The window is doing two jobs at
once because the physics of the two axes allows it to.

⚠ The argument is a reading of the measurements above rather than an independent prediction, and the
within-set evidence behind it is one session. It is offered as the reason the arrangement is not accidental,
not as proof that it must hold on another instrument.

### E.3d ⭐⭐ The tilt, measured — 1 % at the Soret, 45 % at Q  *(2026-08-10)*

§E.3a argues from geometry that the extrapolated end is cheap and the interpolated end is fragile. This
section measures it, on the two set means, and adds the picture that answers the question a reader of §E.3
almost always asks first.

**The question.** If the greener oil's baseline is *higher* under Q — which is how it ends up with a smaller
denominator — then it must also be doing something to the Soret. Does the numerator not pay for the
denominator's advantage?

**The answer is: the two lines fan.** They nearly coincide at the blue end and separate steadily toward the
red, because the two classes agree at the near anchor and disagree at the far one. The tilt is therefore
almost free where the numerator sits and decisive where the denominator sits:

| where | green's line | brown's line | difference | as a fraction of that band |
|---|---|---|---|---|
| Soret 448–460 | 0.0576 | 0.0639 | −0.0063 | ⭐ **1 % of `B_Soret`** |
| near anchor 520–540 | 0.1227 | 0.1035 | +0.0192 | *(pinned by the fit)* |
| Q 560–580 | 0.1569 | 0.1244 | +0.0325 | ⭐⭐ **45 % of `B_Q`** |
| far anchor 620–630 | 0.2040 | 0.1531 | +0.0510 | *(pinned by the fit)* |

**One tilt, two wildly different consequences** — and it is the same 1 % that §E.3a predicts from the
geometry, now measured rather than argued.

![**Figure 5** — the same two set means as Figure 2, with attention on the fitted lines rather than the curves. **Top:** across the whole window the two baselines are nearly on top of each other in the blue and fan apart toward the red. **Bottom:** magnified onto the region where that fan matters. The tilt that costs the numerator ~1 % is worth ~45 % of the denominator, and what tilts it is the green oil's larger red band at ~625 nm — the Qy band the far anchor stands on. ⚠ The wavelength at which the two lines cross is **not** a property of the metric: it is 473 nm for these two set means and 518 nm for a single-run pair. What is stable is the fanning, not where the fan closes.](metric_algebra_pivot.png)

⚠ **Do not read the crossing point as a constant.** It is set by where two nearly-parallel lines happen to
meet, so it moves with the pair and with the fill; only the *direction* of the fan is a property of the
classes.

### E.3e The extrapolation, removed — what it was actually worth

§E.3a's claim can be tested directly rather than reasoned about: build the numerator **without** the
extrapolation — a flat offset at the near anchor, no line drawn where nothing was measured — and leave the
denominator exactly as it is, since the Q band lies *between* the anchors and its correction is interpolation
on any background model. `diagnostics/soret_extrapolation_test.py` does this on the derivation corpus:

| numerator's background | green (n=12) | brown (n=6) | class *d* | green-green *d* | dilution |
|---|---|---|---|---|---|
| **the fitted line** *(shipped)* | 10.560 ± 0.453 | 6.615 ± 0.151 | **10.25** | 1.34 | +3.0 % |
| **flat at the near anchor** | 9.671 ± 0.441 | 6.218 ± 0.093 | **9.35** | 1.31 | ⭐ **+0.1 %** |
| flat at both bands *(no tilt at all)* | 6.676 ± 0.732 | 5.171 ± 0.143 | 2.46 | 0.42 | −10.1 % |
| no background at all | 3.738 ± 0.340 | 3.256 ± 0.164 | 1.62 | 1.85 | ⛔ classes overlap |

⇒ **Removing the extrapolation costs 8.8 % of the class separation and 2 % of the within-green one**, and the
empty corridor keeps the same relative width (28 % of the green mean against 29 %). The discrimination does
**not** rest on the line drawn outside the anchors. What it does rest on is the tilt under **Q** — remove that
and *d* collapses by 76 %, which is §E.3d's 45 % arriving as a number.

⭐ **The unexpected half.** The flat numerator is *better* on dilution invariance — **+0.1 % against +3.0 %**
for the same oil at half strength. Mechanistically that is consistent with §9.13.4: `B_Soret` weights the far
anchor at +0.94, and the blue end is where stray-light compression makes absorbance concentration-*dependent*;
a flat offset drops that term. ⚠ It rests on **one** fill pair and is not established — the proper test is a
real dilution series, and it belongs with the threshold-freeze work rather than in a second rescaling of a
metric whose thresholds were re-derived the same week.

### E.4 ⭐ Why it discriminates — the denominator inverts

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
620–630 *is* intact pigment (§3.4). The causal chain:

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
> new one. **Both are measured; neither transfers to the other's data set.** See §E.8.

**This is why the uncorrected ratio fails** (Appendix E.1): it divides a signal-bearing Soret band by a Q
band that carries nothing. Only after the baseline is removed does the denominator become a
discriminator — and then the dominant one.

### E.5 The three-region identity

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

### E.6 ⭐ Dilution invariance — the proof

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
> centroid. The only approximation in §E.5 was the slope.

**The proof never mentions chlorophyll.** It uses only that a component scales with $c$ — so §3.4's
far-anchor pigment contamination is **harmless to invariance**. It changes what the metric *means*
chemically; it does not change whether it is invariant.

#### E.6a ⭐⭐ What the numerator actually is — a load reference, not a pigment measurement  *(2026-08-10)*

The proof above needs the numerator to *scale with concentration*. It does not need the numerator to be the
pigment's Soret band — and measurement says it largely is not. This matters for how the index is described,
so it is recorded rather than left implicit.

**The measurement.** On the four-oil session — one recipe, one night, four different commercial products —
the raw blue window is **flat while the index spans 1.5×**:

| fill *(green → brown)* | `A_S` raw | `M448` |
|---|---|---|
| Steirerkraft g.g.A. | 0.5634 | 9.96 |
| Spar Steirisches g.g.A. | 0.6189 | 8.76 |
| Spar Premium g.g.A. | 0.5591 | 7.69 |
| Spar S-Budget | 0.6162 | 6.51 |

`A_S` moves ±5 % with **no ordering**, and the **brownest oil reads highest in the blue**. Correlation with
the verdict: **r = −0.41** — if the numerator were driving the index this would be strongly positive.

**Why it is flat — the arithmetic that rules out the simple reading.** Our window sits 16–28 nm *above* the
Soret peak, on the falling flank. Demetallation blue-shifts that peak, so if the window were the pigment's
band it would swing violently:

| Soret FWHM | window reads at 432 nm | at 411 nm | a full conversion would cost |
|---|---|---|---|
| 42 nm *(the fitted width)* | 0.472 of peak | 0.060 | **−87 %** |
| 55 nm | 0.641 | 0.189 | −71 % |
| 70 nm | 0.758 | 0.354 | −53 % |

Even a modest 10 nm shift costs 26–56 %. We measure the brownest oil **9 % higher** than the greenest. ⇒ the
tetrapyrrole is a **minority tenant** of 448–460; the majority is carotenoid, browning product and scatter
(`KB_spectroscopy_physics.md` §4.2).

**Three effects, pointing two ways, is why it lands flat** — pigment leaving the window (down), carotenoids
degrading with roast (down), Maillard products arriving (up).

⭐ **And that is exactly what makes the index work.** A numerator that *did* track roast would be a second
quality signal, and the index would be one quality signal divided by another, with the two partly cancelling.
Because the blue window tracks *how much oil is in the beam* rather than *what state its pigment is in*, it
acts as the load reference the ratio needs. §16.27.5 measured the same thing from the other side: the Soret
scaled ×1.236 against a fill-strength difference of ×1.211 while the Q denominator moved ×1.024.

⚠ **The standing to claim, and not more.** This is **empirically validated and mechanistically explained**,
not guaranteed by a conservation law. An oscillator-strength sum rule would apply to the *integral over the
band*; a 12 nm slice on the flank does not inherit it. Compensation among three terms can hold for four oils
and fail for a fifth — an unusually carotenoid-rich variety, or a roast dark enough for Maillard to dominate.
⇒ **widening the oil panel tests this for free**, with no hardware.

**How big could the confound be? — the bound, worked through.** The worry is specific: carotenoids sit in the
numerator's window and have nothing to do with the pigment's state, so a different oil could carry a different
numerator for reasons unrelated to roast. Two spreads decide how much that could matter, both from the
matched-dose session:

| | across the four oils | mean | as ± about the mean |
|---|---|---|---|
| `A_S` — the numerator | 0.5591 … 0.6189 | 0.5894 | **± 5.1 %** |
| `M448` — the quantity being read | 6.51 … 9.96 | 8.23 | **± 21.0 %** |

Because the index is a quotient, an error in the numerator passes into `M448` **one for one**: 5 % in, 5 %
out. So assume the most pessimistic thing available — that **none** of that ±5 % is dose variation, **none**
of it is real pigment, and **all** of it is carotenoid noise. The confound then moves the index by ±5 % while
the quantity being read spans ±21 %:

> ⭐ **21 / 5 ≈ 4.** Not "the confound is absent", but "at its largest conceivable size it cannot manufacture
> the ordering we observe".

**And the ordering itself is the wrong shape for that story.** If carotenoids were driving the verdict, the
oil with the largest numerator would read greenest. Sorted by verdict, it does not:

| oil | `A_S` | `M448` | |
|---|---|---|---|
| Steirerkraft g.g.A. | 0.5634 | **9.96** | greenest — yet the *second-smallest* numerator |
| Spar Steirisches g.g.A. | 0.6189 | 8.76 | the largest numerator, second place |
| Spar Premium g.g.A. | 0.5591 | 7.69 | the smallest numerator, third |
| Spar S-Budget | 0.6162 | **6.51** | brownest — yet nearly the *largest* numerator |

Hence `r` = **−0.41** where the confound predicts a strongly positive number.

⚠ **Two limits on that check, stated so it is not over-read.** With n = 4, `r` = −0.41 is nowhere near
significance (|r| > 0.95 would be needed), so it is the **absence of the confound's signature**, not evidence
that the confound is absent — the weight rests on the 4:1 bound, not on the correlation. And the bound is a
statement about **this panel**: a variety with genuinely extreme carotenoid content could exceed ±5 %, which
is precisely why widening the panel is the test.

#### E.6b ⇒ Naming — how to say what this index is, to four different audiences

**"Soret ÷ Q" describes the windows, not the chemistry**, and everything above is why. The blue window is not
the pigment's band (it is mostly carotenoid, browning and scatter, §E.6a) and the denominator is not "the Q
band" as a chemical quantity — it is that band's height *above a fitted line*, which is what rises as the
porphyrin loses its magnesium. A name that survives those two facts is worth having, because the wrong one
invites the wrong reasoning.

**The literal reading, term by term:**

| term | what it actually is |
|---|---|
| **chromophore load** | how much light-absorbing material sits in the beam *altogether* — pigment plus carotenoid, browning product and haze. Operationally: how much oil, times the path |
| **pigment state** | how far the green pigment has gone down the degradation road (magnesium lost, intensity redistributed out of the red band) |
| **per unit** | divided by, so the dose cancels — §E.6's invariance proof |

⚠ **One inversion to keep straight.** `M448` is `B_Soret / B_Q`, i.e. **load ÷ state**, so a *bigger* number is
*greener*. The quantity that reads naturally as "state per load" is **`1/M448`** — which is exactly
§16.27.5's concentration-free column (Steirerkraft 0.1005 = 1/9.96).

**The same claim, at four registers.** All four say one thing; they differ only in what the listener already
knows. ⛔ None of them may say "chlorophyll content", which is what the index is *not*.

| audience | formulation |
|---|---|
| **bench / physics** | the Q band's height above the fitted 520–540 / 620–630 baseline, divided by the blue window's — pigment degradation per unit chromophore load, inverted so that greener reads higher |
| **a colleague, operationally** | the blue window says *how much stuff is in the beam*; the Q band above the baseline says *how far the pigment has degraded*; dividing makes the dilution cancel, so what is left is a property of the oil rather than of the tube |
| **the laboratory** *(LIMS, channel partner)* | a **ratiometric absorbance index**: two band means of the same sample, background-corrected against a common two-window baseline; dimensionless and concentration-independent by construction |
| **the miller** | ⭐ **how brown the pigment has gone, per litre of oil in the beam** — a sloppy dilution moves both numbers together, so it cannot move the verdict |

⭐ The analogy that carries the miller's version: you do not judge water by *how much* dirt came out of it,
you judge it by dirt **per litre**. The same dirt in a bigger sample is not dirtier water.

⚠ **Where even the careful name is generous: "state".** It sounds like we know *which* state. We do not — we
read one number that rises as degradation proceeds, not a protopheophytin : protochlorophyll ratio. That
specific reading is what a 410–420 nm emitter would buy (`KB_spectroscopy_physics.md` §4.2).

### E.7 What breaks invariance — pedestal curvature, and nothing else

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
> **−0.05** on the new one (§Ea.1). The anchor move more than halved the residual concentration dependence
> — the one number in this chapter that improves for a reason the theory predicts, since a narrower window
> further from the Soret band gives the pedestal's curvature less room to differ across it.

### E.8 Performance

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
pedestal-corrected index of §Ea.3 — and to the old 600–630 gauge before it. Reading this chapter's numbers
against 10.6 is the single easiest mistake to make with this document.

> ⚠ **Why this green margin differs from the spec's.** `SPEC_capture_quality.md` §16.20.4 scores green as
> sets **B+C** pooled (n = 12); this document declares green as set **C alone** (n = 6, 5 df). Fewer degrees
> of freedom, and the t-distribution charges heavily for that. Both are correct for their own data set;
> **neither may be quoted with the other's.**

> ⚠⚠ **The comparison that must not be made.** The 600–630 anchor scored *d* = **11.04** on exactly this
> pair, against **10.20** here. That is not a regression in the metric: the class gap grew from 31.7 % to
> 52.5 % while the noise grew alongside it, and *d* is their quotient. On the spec's pooled basis the same
> anchor move reads *d* 9.80 → **10.35**, i.e. an improvement. **A single *d* is not a property of a metric
> — it is a property of a metric and a data set together.** What the anchor move buys is stated in §Ea.1
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

### E.9 ✅ The 607 nm artifact no longer touches the metric

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
separate jar insertions, and anything that displaces the beam between them (the jar seating, §E.1) shifts
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

### ⭐ E.10 The pedestal correction — the idea, the measurement, and why it is legacy  *(added 2026-08-21)*

§E.7 shows *why* a straight chord leaves an error: a real scattering pedestal is **convex** in λ, a fitted
line is not, so the line cannot follow it and a leftover survives the subtraction. §E.7 stops at the
diagnosis. **This section is what the plugin did about it.** The full account is
`DOC_pedestal_correction.md`; this is the shape of it.

#### The idea, in one chain

Carrying one real set through — Kiendler C, post-rebuild:

| # | what happens | | Kiendler C |
|---|---|---|---|
| 1–2 | capture, and average over the four windows | $A_{X}$ | `A_Soret` 1.1705 · `A_Q` 0.2082 |
| 3 | fit the chord through the two anchors | 520–540 and 620–630 | |
| 4 | subtract it everywhere | $B_{X} = A_{X} - \op{chord}$ | `B_Soret` **1.1397** · `B_Q` **0.0716** |
| 5 | divide | $M = B_{Soret}/B_{Q}$ | **15.91** ← the uncorrected verdict |
| 6 | ⛔ but the chord is straight and the pedestal is not, so a leftover stays at Q | $r_{Q}$ | −0.0184 A |
| 7 | ⚠ a leftover in the **denominator** inflates the ratio | $F = 1 - r_{Q}/B_{Q}$ | **1.257** — i.e. **+25.7 %** |
| 8 | put it back, then divide again | $M_{\infty} = B_{Soret}/(B_{Q} - r_{Q})$ | **12.66** ← the corrected verdict |

⭐ **Step 7 is why this was worth doing at all.** The leftover is the same size at both bands, but
$B_{Q}$ is **sixteen times smaller** than $B_{Soret}$ — so the identical absolute error is a rounding
detail in the numerator and a **quarter of the value** in the denominator. Correcting the denominator
alone therefore recovers almost the whole effect, for one constant. It is the same asymmetry §E.3a's error
budget is about, seen from the other end.

#### ⭐⭐ How `r_Q` is measured — a test with no free parameters

This is the elegant part, and it is what makes the constant defensible rather than fitted. Take chapter
E.7's two measured quantities and **eliminate the concentration**:

```math
B_{Soret} = M_{\infty} \cdot B_{Q} + \big( r_{Soret} - M_{\infty} \cdot r_{Q} \big)
```

That is a straight line relating two things the instrument measures directly — and **`c` has vanished
from it.** Concentration moves a run **along** the line, never off it. So you may prepare the same oil as
sloppily as you like at two or more strengths; every run must still land on that line.

⭐ **And the test writes itself.** If the baseline were perfect, both $r$ terms are zero, the bracket
vanishes, and **the line passes through the origin** — which is exactly what it should mean physically:
with no pedestal left, when one band's pigment signal is zero so is the other's. **It does not pass
through the origin.** The intercept *is* the leftover, and $r_{Q} = -k / M_{\infty}$ falls out of the fit.

⇒ No fitted concentration, no free parameter, and the null hypothesis is a **point**, not a range.

#### ⚠ Measuring it and applying it are two different jobs

Confusing these is the commonest misreading of `DOC_pedestal_correction.md`, so it is worth separating:

| | **measuring `r_Q`** | **applying the correction** |
|---|---|---|
| what it is | a **calibration**, once per rig state | one subtraction, on **every** run |
| what it needs | one oil at **two or more genuinely different concentrations** | nothing but $B_{Q}$ and the stored constant |
| how often | after every mechanical change to the instrument | every measurement |
| which oils | only those prepared at more than one strength | ⭐ **any oil, any sample** |

⇒ The correction applies to every oil, including the brown one. What some oils cannot do is *contribute
to measuring* the constant — a statement about how they were prepared, not about what they are.

#### What it cost

| | green `20270729C` | brown `20260731A` | Cohen's *d* | threshold |
|---|---|---|---|---|
| $B_{Soret}/B_{Q}$ — the Pigment Index | 15.499 | 10.160 | **10.20** | 12.5 |
| $B_{Soret}/(B_{Q} - r_{Q})$ — pedestal put back | 12.380 | 8.590 | **9.33** | 10.6 |

⚠ **Note that the correction SCORES WORSE** — *d* falls from 10.20 to 9.33. It was never adopted to
discriminate better; it was adopted because $B_{Q}$ without it is not the pigment's absorbance but the
pigment's absorbance minus a line's error, and a quantity that means something is worth a little
separation. That trade is the whole case for it, and it should be stated rather than implied.

Two properties carried forward from `DOC_pedestal_correction.md`:

| | |
|---|---|
| ⭐ **`r_Q` is a property of the INSTRUMENT, not the oil** | which is what makes a single constant defensible at all. ⛔ It does **not** survive a mechanical rebuild |
| ⚠ **`r_Q` belongs to its anchor** | −0.0246 A on 600–630, −0.0184 A on 620–630 (§Ea.2). Pairing one anchor's band means with the other's constant is a category error, and an easy one because both are called `r_Q` |

#### ⛔ Why it is legacy

**1 · Its gauge is retired.** `RoastBaselineGaugeView` (T = 10.6) went with §16.20; the number is still
computed and printed, but it draws no pill (§9.3, rung 1).

**2 · There is no longer a residual to correct.** `r_Q` is defined as *the pedestal's departure from its
own best-fit line*. `Q%` fits no line (§5.2), so no such line exists and the quantity is undefined for it —
not small, **undefined**. The correction did not fail; its subject was removed.

⭐⭐ **3 · And this is the part worth keeping.** The pedestal did not stop mattering — **the correction
stopped applying.** `Q%` handles the same physics differently and, for one component, better: its numerator
is a **difference**, so a *flat* pedestal cancels **exactly**, with no constant to measure, no anchor to
belong to and nothing to invalidate on a rebuild. That is strictly stronger than correcting for it.

⚠ **But only for the flat component.** Real Mie scattering has spectral **slope**
(`DOC_sample_physics.md` §5.2), and a slope does not cancel between two windows at different wavelengths.
⇒ `Q%` traded a *curvature* residual it had to measure for a *slope* residual it does not — an improvement,
not an escape. The honest one-line summary of this appendix's subject is: **the pedestal is still the
largest single nuisance in the jar; what changed is which part of it survives the arithmetic.**

⚠ **Nothing here is retracted.** `r_Q`'s measurement, the instrument-property claim and
`DOC_pedestal_correction.md` in full remain valid, and they are what any reading of the archive's **143
older reports** depends on — those numbers were produced by this correction and cannot be interpreted
without it.

<!--PAGEBREAK-->

## Appendix Ea — ⭐⭐ Where the far anchor came from — and the three verdicts  *(2026-08-03; `SPEC_capture_quality.md` §16.20)*

Everything above is written on the shipped **620–630 nm** far anchor. It was **600–630** until 2026-08-03,
and every number in chapters 4–5 changed when it moved — not because the oils or the instrument changed,
but because the line the bands are measured above is drawn through a different window. Appendix E's algebra is
unchanged in *form*; only where the second window sits.

This chapter is the record of that move: why it was made, what it cost, and why the bench now shows the
index three ways rather than one.

### Ea.1 Why the window moved — and why it is the direction nobody tried

§E.9 and §E.5 together make the problem plain: the far anchor **straddles** two things it should not.
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
| three-region identity error (§E.5) | 0.52 % | **0.02 %** |
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

### Ea.2 ⚠ `r_Q` belongs to its anchor

`r_Q` is defined as the pedestal's departure from **its own best-fit line** (§E.7). Move the anchor and
the line moves, so the residual moves with it:

```math
r_{Q}(600-630) = -0.0246 A \qquad r_{Q}(620-630) = -0.0184 A
```

**Pairing 620–630 band means with the 600–630 constant is a category error**, and it is an easy one to
make because both are called `r_Q`. The shipped constant is per-anchor and per-rig-state (§E.7's residual
does not survive a mechanical rebuild).

### Ea.3 The three verdicts, and why the raw ratio lost its

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
PUBLISHING badge, the one screen an end user sees. §E.4's argument for why the baselined index
discriminates and the raw one does not was right all along; the gauge had simply never been re-scored
against a post-rebuild brown series.

### Ea.4 ⭐ The far anchor's peak, measured on two lamps  *(2026-08-09; `SPEC_capture_quality.md` §16.28)*

§Ea.1 placed the window on 620–630 nm on the argument that protochlorophyll's Qy *should* be centred there. The
peak has since been measured: two runs on the same rig under **two different lamps** — a Sansi V2 and the Yuji,
whose own sharp emission structure sits 3.4 nm apart — put the absorbance maximum at **629–630 nm** under both.
Lamp structure would have moved with the lamp; this did not.

<!--PAGEBREAK-->

## References

### Pigment identity and band positions

1. **Fruhwirth, G. O. & Hermetter, A. (2007).** *Seeds and oil of the Styrian oil pumpkin: components and
   biological activities.* Eur. J. Lipid Sci. Technol. **109**(11), 1128–1140.
   DOI [10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105). §3.4 identifies protochlorophyll
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
