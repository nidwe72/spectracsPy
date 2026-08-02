<!--
MASTER DOCUMENT — the pedestal correction.
This markdown file is the SOURCE OF TRUTH. The PDF is generated from it:

    python3 docs/tools/build_pedestal_correction_pdf.py
    -> ../spectracs-docs/internal/Spectracs_PedestalCorrection.pdf

Never hand-edit the PDF. Edit here, re-run, commit both.

Chapters 1-7 and both figures come from `diagnostics/pedestal_correction.py`; chapter 9's
out-of-sample test comes from `diagnostics/all_metrics_archive.py`. Both call the SHIPPED code paths
rather than re-implementing them. Re-run both before regenerating this PDF.

This document is DOCUMENTATION plus ONE PROPOSAL. The proposal (chapter 7) is NOT implemented and
must not be implemented on the strength of this document alone — chapter 12 says what would have to
be true first.

⚠ The renderer's math notation is deliberately small. It supports _{} ^{} \frac \sqrt and the symbol
list in build_capture_fidelity_pdf.py. It does NOT support \; — use plain spaces around operators.
-->

# The Pedestal Correction

*Why the Pigment Index reads about 29 % too high, where the error comes from, and what a single
subtraction would do about it.*

**Why this document exists.** On 2026-08-01 three preparations of the same green oil returned three
different verdict numbers — 14.28, 12.74 and 13.04 — a spread of 10.8 % on an oil that had not
changed. Chasing that down produced a measurement of a quantity the specification had only ever
derived on paper, and with it a correction that would remove most of the spread. This document
explains the whole chain from first principles, so that the proposal can be judged rather than
believed.

**Its companions.** *Capture Fidelity* covers the instrument — how a webcam becomes a spectrum.
*Light, Pigment and Solvent* covers the sample. *From Spectrum to Verdict* covers the arithmetic that
turns an absorbance curve into a verdict. **This document is a correction to that arithmetic**, and
assumes only chapter 5 of it.

**How to read it.** Chapters 2–4 build the problem from nothing and contain no algebra beyond a
subtraction. Chapter 5 is the one piece of real algebra and is worth the effort — everything after it
is consequence. Chapter 8 says what the corrected number physically IS; chapter 9 is the first real
test of it. Chapter 10 lists every assumption in one place. **Chapter 12 is the chapter that says why
this may be wrong**, and should be read before anybody acts on it.

**Status.** The measurement is real. The correction is a **proposal** — fitted on one oil,
confirmed out-of-sample on a second, and shown by the same test NOT to survive a rig rebuild.

<!--TOC-->

<!--PAGEBREAK-->

## 1 · The claim, in one page

The instrument produces an absorbance curve. The verdict is a **ratio of two heights** taken off that
curve, after a straight line has been subtracted from it:

```math
M = \frac{B_{Soret}}{B_{Q}}
```

`B_Soret` is the pigment's blue absorption band (440–460 nm); `B_Q` is its much weaker green-yellow
band (560–580 nm). Green oil scores high, brown oil low, and the shipped threshold is 10.6.

**The problem.** The straight line that gets subtracted is an approximation, and it does not remove
exactly the right amount. What it leaves behind at the Q band we call `r_Q`. Because `B_Q` is a small
number, a small leftover is a large fraction of it — and `B_Q` is the **denominator**, so the whole
ratio inherits that fraction.

**The measurement.** `r_Q` = **−0.0246 ± 0.0037 A**, obtained from ten runs of one oil. A second oil
gives a consistent −0.0212 ± 0.0193 A, but that interval contains zero and adds very little — chapter
10 weighs it honestly, and the real confirmation is chapter 9's out-of-sample test. `r_Q` is
**negative**, meaning the correction subtracts slightly too much.

**The size.** At the standard recipe this inflates the verdict number by about **29 %**; on an
over-dilute sample it reached **43 %**.

**The proposal.** Put the leftover back before dividing:

```math
M_{corrected} = \frac{B_{Soret}}{B_{Q} - r_{Q}}
```

One subtraction, using quantities every run already computes. Applied to the three preparations that
started this, their spread falls from **10.8 % to 2.5 %**.

**What it costs.** The numbers move to a different scale — green lands near 10.0 instead of 12–14,
brown near 7.6 instead of 9.3 — so **the threshold 10.6 becomes meaningless and must be re-derived.**

**What it assumes.** That `r_Q` is a *constant*. That is the whole risk. Chapter 9 tests it out-of-sample
for the first time, and chapter 12 shows a concrete case where it changes the answer.

<!--PAGEBREAK-->

## 2 · What the instrument actually hands us

Everything below starts from one curve: **absorbance against wavelength**, written $A(\lambda)$.

Absorbance is defined from two captures — the reference (pure solvent, no oil) and the sample:

```math
A(\lambda) = \log_{10}\frac{R(\lambda)}{S(\lambda)}
```

`A = 0` means the sample passes as much light as the blank. `A = 1` means it passes a tenth of it.
`A = 2`, a hundredth. The scale is logarithmic, so **high absorbance means very little light is
getting through** — and there is a ceiling, because once the transmitted signal falls into the sensor
noise the number stops meaning anything.

From that curve the plugin reads **four wavelength windows**:

| window | range | what lives there |
|---|---|---|
| **Soret band** | 440–460 nm | the pigment's strong blue absorption |
| near anchor | 520–540 nm | chosen to be *quiet* — little pigment |
| **Q band** | 560–580 nm | the pigment's weak second absorption |
| far anchor | 600–630 nm | also chosen as quiet |

The two **anchors** are not measurements of the pigment. They exist to answer a different question,
which is the subject of the next chapter.

**A note on band values.** Each window's value is the mean absorbance over the points inside it.
Where this document quotes a set's value it is the **mean over that set's runs**. One consequence
worth knowing when checking the arithmetic: the mean of a ratio is not exactly the ratio of the
means, so recomputing `M` from the quoted `B_Soret` and `B_Q` reproduces the quoted `M` to about
0.05 %, not exactly.

<!--PAGEBREAK-->

## 3 · The pedestal, and why a baseline is subtracted at all

A cuvette of diluted oil does not only *absorb* light. It also **scatters** it — off undissolved oil
droplets suspended in the alcohol. Scattered light misses the camera just as absorbed light does, so
the instrument cannot tell the two apart. Both arrive as "absorbance".

The result is that the measured curve sits on a **pedestal**: a broad, smooth background that is
present at every wavelength and has nothing to do with the pigment.

```math
A_{measured}(\lambda) = A_{pigment}(\lambda) + P(\lambda)
```

The pedestal `P` is a nuisance and it is large. Earlier work measured it at roughly **7 % of the
Soret band but 52–61 % of the Q band** — because the Q band is intrinsically weak, the same
background is a far bigger share of it.

**The standard remedy** is to estimate `P` from places where the pigment is quiet, and subtract it.
That is what the two anchor windows are for: fit a straight line through 520–540 nm and 600–630 nm,
and subtract that line from the whole curve. Everything called `B_...` in this document means a band
value **after** that subtraction.

This works well. It is the reason the shipped metric survives jar-tilt events that send the
uncorrected ratio wandering by 29 %, and nothing here argues against doing it.

**But a straight line is a straight line, and the pedestal is not straight.**

<!--PAGEBREAK-->

## 4 · What a straight line cannot remove — and which way it errs

Scattering does not fall off linearly with wavelength. It falls off roughly as a power law,
$P \propto \lambda^{-n}$, which is a **convex** curve: steep in the blue, flattening toward the red.

Now the geometry that decides everything:

- We fit the line through two windows, at **520–540 nm** and **600–630 nm**.
- A straight line through two points on a convex curve is a **chord**.
- **A chord lies *above* the curve everywhere between its endpoints.**
- The Q band, **560–580 nm, lies exactly between them.**

So at the Q band the fitted line sits **above** the true pedestal, and subtracting it removes the
pedestal **plus a slice of genuine pigment signal**.

Write the leftover as `r`, defined as what the line fails to remove — negative where the line
over-subtracts:

```math
B_{X} = A_{pigment,X} + r_{X}
```

**This predicts the sign before we measure anything: `r_Q` must be negative.** It is a real
prediction and it could have come out wrong. Measured, `r_Q` = −0.0246 A.

**Why the Soret band escapes.** 440–460 nm lies *outside* the two anchors, not between them. There
the chord runs below the curve, and in any case the Soret band is ten to twenty times taller, so a
leftover of 0.025 A is a rounding error against 1.1 A. Throughout this document `r_Soret` is treated
as negligible; chapter 10 lists that as an assumption.

<!--PAGEBREAK-->

## 5 · Where the error lands — and why the denominator suffers

This is the one piece of algebra in the document. Take it slowly; everything afterwards follows.

Write the true pigment absorbance in each band as concentration `c` times path length $\ell$ times
that band's extinction coefficient `e`:

```math
A_{pigment,Soret} = c \cdot \ell \cdot e_{Soret} \qquad A_{pigment,Q} = c \cdot \ell \cdot e_{Q}
```

Substituting into chapter 4's definition, what we actually measure is:

```math
B_{Soret} = c \cdot \ell \cdot e_{Soret} + r_{Soret} \qquad B_{Q} = c \cdot \ell \cdot e_{Q} + r_{Q}
```

The **true** index — the one that depends only on which pigment is present, not how much — is the
ratio of the extinction coefficients:

```math
M_{\infty} = \frac{e_{Soret}}{e_{Q}}
```

Now form the index we actually compute, dropping `r_Soret` as negligible:

```math
M = \frac{B_{Soret}}{B_{Q}} = \frac{c \cdot \ell \cdot e_{Soret}}{c \cdot \ell \cdot e_{Q} + r_{Q}}
```

Divide top and bottom by $c \cdot \ell \cdot e_{Q}$:

```math
M = M_{\infty} \cdot \frac{1}{1 + \frac{r_{Q}}{c \cdot \ell \cdot e_{Q}}}
```

**Read that denominator.** The error term is not `r_Q` on its own — it is `r_Q` **divided by the
pigment signal**. Three consequences follow immediately, and they are the whole story:

1. **The error is a *fraction*, not an offset.** A fixed leftover does more damage to a weak sample
   than a strong one.
2. **It grows without limit as the sample is diluted.** Halve the concentration and you double the
   error. This is why over-dilute preparations misread — see figure 2.
3. **`r_Q` sits in the denominator, so its sign is inverted in the result.** `r_Q` negative makes the
   whole expression **larger**. The index reads **high**, not low.

**Why the denominator and not the numerator.** The same absolute error `e` shifts a ratio by `e/B` in
each band, so the damage ratio is simply how much bigger one band is than the other:

```math
\frac{B_{Soret}}{B_{Q}} = \frac{1.1160}{0.0856} \approx 13
```

**An error in `B_Q` is about thirteen times more damaging than the same error in `B_Soret`.** That is
the entire reason this document is about the Q band.

Finally, rearranging the same expression into the form used from here on:

```math
M = M_{\infty} \cdot \Big( 1 - \frac{r_{Q}}{B_{Q}} \Big)
```

The bracket is the **inflation factor**. With `r_Q` negative it is greater than 1.

## 6 · Measuring `r_Q` — a test with no free parameters

We now need `r_Q` from data. The trick is to avoid needing to know the concentration at all — which
matters, because the session that produced this data proved the concentration was not reliably known.

Return to chapter 5's two measured quantities and eliminate `c`:

```math
B_{Soret} = M_{\infty} \cdot B_{Q} + \Big( r_{Soret} - M_{\infty} \cdot r_{Q} \Big)
```

That is the equation of a **straight line** relating two things we measure directly. Vary the
concentration however sloppily you like: every run must fall on it.

**And here is the test.** If there were no leftover at all — a perfect baseline — then both `r` terms
are zero, the bracket vanishes, and **the line passes through the origin.** That makes intuitive
sense: with no pedestal left, when one band's pigment signal is zero so is the other's.

So: plot `B_Soret` against `B_Q`, one point per run, and look at where the line crosses. The
intercept is the leftover. **No fitted concentration, no assumed recipe, no free parameters.**

![The straight-line test](figures/pedestal_line.svg)

Fitted at run level, so the intercept carries an honest standard error:

| oil | runs | slope = $M_{\infty}$ | **intercept** *k* | *t* | ⇒ $r_Q = -k / M_{\infty}$ |
|---|---|---|---|---|---|
| **Kiendler** | 10 | 9.998 ± 0.502 | **+0.2463 ± 0.0351** | **7.01** | **−0.0246 ± 0.0037 A** |
| **Steirerkraft** | 12 | 9.930 ± 2.149 | +0.2103 ± 0.1860 | 1.13 | −0.0212 ± 0.0193 A |
| S-Budget | 6 | — | — | — | one concentration only — cannot be fitted |

**Reading the table.**

- The intercept is **not zero**, at 7 standard errors for Kiendler. The baseline leaves something
  behind, and the amount is what chapter 4 predicted in sign.
- The **slope** is the pedestal-free index $M_{\infty}$, and both green oils give ≈ 9.9–10.0.
- **Steirerkraft's fit proves nothing on its own** (*t* = 1.13). Its `B_Q` values span only
  0.0785–0.0928 — **17 % of the mean against Kiendler's 48 %**, too short a lever to locate an
  intercept — and its 95 % interval on `r_Q`, −0.0590 … +0.0166, **contains zero**. It is quoted
  because its point estimate independently agrees, not because it is significant. Chapter 10's A1
  weighs how little that is worth.
- **The brown oil cannot be used at all.** It exists at one concentration, and you cannot fit a line
  through points that share an x-value.

**Where Kiendler's leverage came from — and the irony in it.** Its `B_Q` spans 0.0536–0.0867, wide
enough to fit, *only because one of its three preparations was accidentally too dilute*. The botched
sample is what made the measurement possible.

<!--PAGEBREAK-->

## 7 · The correction, worked end to end

Start from chapter 5's result and solve for the quantity we actually want:

```math
M_{\infty} = \frac{M}{1 - \frac{r_{Q}}{B_{Q}}} = \frac{B_{Soret}}{B_{Q} - r_{Q}}
```

**It collapses to a single subtraction.** `B_Q − r_Q` is nothing other than the pigment part of the Q
band with the baseline's over-subtraction put back. Then divide as before.

### Worked example — Kiendler set A, the over-dilute one

| step | | |
|---|---|---|
| 1 | read the baselined Soret band | `B_Soret` = 0.8221 A |
| 2 | read the baselined Q band | `B_Q` = 0.0576 A |
| 3 | the shipped index | 0.8221 / 0.0576 = **14.27** |
| 4 | put the leftover back | `B_Q − r_Q` = 0.0576 − (−0.0246) = **0.0822** A |
| 5 | divide again | 0.8221 / 0.0822 = **10.00** |
| 6 | how inflated step 3 was | 14.27 / 10.00 = **1.43**, i.e. **+43 %** |

Step 4 is the whole correction. Everything else was already being computed.

### The same, for every set on record

| set | `B_Q` | inflation | M shipped | **M corrected** |
|---|---|---|---|---|
| **Kiendler A** *(over-dilute)* | 0.0576 | **+42.8 %** | 14.279 | **10.00** |
| Kiendler B | 0.0849 | +29.0 % | 12.740 | **9.88** |
| Kiendler C | 0.0856 | +28.8 % | 13.039 | **10.13** |
| Steirerkraft B | 0.0828 | +29.8 % | 12.489 | 9.62 |
| Steirerkraft C | 0.0901 | +27.3 % | 12.251 | 9.62 |
| S-Budget D *(brown)* | 0.1085 | +22.7 % | 9.303 | **7.58** |

**The three Kiendler preparations spread 10.8 % before and 2.5 % after.** That is the result the
proposal rests on.

![Inflation against pigment signal](figures/pedestal_inflation.svg)

### Why one cannot simply concentrate the problem away

The inflation is `|r_Q| / B_Q`, so working at higher concentration shrinks it. How much higher?

| target inflation | needs `B_Q` ≥ | relative to today's 0.0856 |
|---|---|---|
| 30 % | 0.082 | 1.0× — *this is where we are* |
| 20 % | 0.123 | 1.4× |
| 10 % | 0.246 | **2.9×** |
| 5 % | 0.493 | **5.8×** |

**There is no room.** At today's recipe the 440–447 nm bins already read 2.0–2.6 DN against a
reference near 88 — they are dark, and previous work established they are not measurements. Working
1.4× stronger pushes more of the Soret band into that floor; 2.9× is out of the question.

**⇒ The concentration route is closed. Either correct the number arithmetically, or reduce `r_Q`
itself by making the sample physically clearer — filtration, or a solvent that dissolves rather than
suspends.**

<!--PAGEBREAK-->

## 8 · What the corrected number IS, physically

Chapter 7 produced a quantity that is more stable than the one we had. **Stability is not meaning.**
A number can be beautifully reproducible and still measure nothing in particular, so this chapter asks
what $M_{\infty}$ corresponds to in the sample — and, just as importantly, where that correspondence
stops being established.

### 8.1 Three layers of grounding

**Beer-Lambert — the derivation itself.** Every step of chapter 5 is `A = ε · c · ℓ` plus algebra.
$M_{\infty} = e_{Soret}/e_{Q}$ is a ratio of **extinction coefficients**: quantities belonging to the
molecule, not to the sample, the operator or the instrument.

**Porphyrin spectroscopy — why those two bands exist at all.** The Soret and Q bands are not windows
we invented; they are the standard electronic structure of a porphyrin macrocycle. In the four-orbital
picture the Soret transition is intensely allowed and the Q transitions are weak — which is precisely
*why* the denominator of this metric is small and fragile, and therefore why this whole document is
about the Q band rather than the Soret one.

It also supplies the chemistry the verdict depends on. The pigment is **protochlorophyll**, a
porphyrin. Losing its central magnesium — which is what ageing and roasting do, giving
**protopheophytin** — lowers the macrocycle's symmetry from D4h to D2h, splits the Q bands and
redistributes intensity among them. **A Soret-to-Q ratio therefore probes metallation state**, which
is the chemical difference between a fresh oil and a degraded one.

**Scattering — and a prediction that could have failed.** Chapter 4 did not *fit* the sign of `r_Q`;
it **predicted** it, from λ⁻ⁿ scattering being convex and the Q band lying between the two anchors.
Measured, `r_Q` = −0.0246. **Had it come out positive the model would have been dead.** A prediction
that risks refutation and survives is worth substantially more than a good fit, and it is the main
reason to believe the mechanism is the one described rather than a curve that happens to match.

### 8.2 ⭐ Why invariance and sensitivity arrive together

The oil is not one pigment. It is a **mixture** of intact protochlorophyll and its degradation
products, and the entire point of the verdict is that their proportions differ between a fresh oil and
an old one. For a mixture the corrected index becomes

```math
M_{\infty} = \frac{\sum_{i} c_{i} \cdot e_{Soret,i}}{\sum_{i} c_{i} \cdot e_{Q,i}}
```

Now apply the two operations that matter, one after the other:

**Dilute the sample** — multiply every $c_{i}$ by the same factor `k`:

```math
\frac{\sum_{i} k \cdot c_{i} \cdot e_{Soret,i}}{\sum_{i} k \cdot c_{i} \cdot e_{Q,i}} = \frac{\sum_{i} c_{i} \cdot e_{Soret,i}}{\sum_{i} c_{i} \cdot e_{Q,i}}
```

`k` cancels. **Dilution-invariant — whatever the composition is.**

**Degrade the sample** — change the *proportions* between species. The sums no longer scale together,
because the species have different ε at the two bands, so the ratio moves. **Speciation-sensitive.**

**Both properties fall out of the same three lines.** Neither was tuned in, and they are exactly the
pair the application needs: blind to how much oil went into the alcohol, sensitive to what the pigment
has become. It is also the measured result — `SPEC_capture_quality.md` §16.13.9 refuted
single-species scaling at *d* = 10.26, so the mixture reading is not an assumption but an observation.

### 8.3 ⚠ Three places the physics is NOT settled

**(a) The 560–580 nm assignment is open — and it is the denominator of the verdict.** Two candidates,
which are not equivalent:

| candidate | what the metric would then be |
|---|---|
| **Q(1,0)** — vibronic satellite of the intact, Mg-bearing pigment | a comparison of two bands of the *same* molecule |
| **Qx of protopheophytin** — the metal-free degradation product | a literal **intact ÷ degraded** ratio, with a far stronger justification |

Evidence gathered 2026-07-31 leans to the second: `A_Q` is *equal* across the classes while `A_Soret`
differs by 9 %, and the 572 nm feature is *stronger in the brown oil* — a band that grows as the oil
degrades is hard to attribute to the intact molecule. **Not proven.** No source we hold assigns this
band, and the comparison is between two different bottles rather than one oil before and after
demetallation. The **acid test** — split one oil, demetallate half, re-measure — settles it in an
afternoon (`SPEC_capture_quality.md` §16.13.8).

**(b) Our windows are not the bands, so the number is not literature-comparable.** 440–460 nm is the
right-hand *slope* of the Soret band; its peak may lie below the 440 nm edge of the ROI entirely. So
$M_{\infty} \approx 10.0$ is **our windows' number**, not a molar ratio anyone could look up or
reproduce on another instrument. **It is dilution-invariant but not absolutely calibrated** — a
relative index. Putting it on the published scale would mean measuring in 80 % acetone, the literature
standard for protochlorophyll; recorded, not scheduled.

**(c) Beer-Lambert is strained exactly where the numerator lives.** At the Soret band the sample
transmits ~6.5 % and the blue edge is already dark, so linearity is weakest at the very band the
numerator is built from. This is assumption A4 in the next chapter, and it is not a small print item.

### 8.4 What may therefore be claimed

**Defensible today:** that the *invariance* is a consequence of Beer-Lambert and not of tuning; that
the *sensitivity to degradation* reflects real macrocycle chemistry; and that the sign of the pedestal
residual was predicted from scattering physics before it was measured.

**Not defensible today:** that $M_{\infty}$ is a molecular constant, that it can be compared with a
published figure, or that the metric is a proven intact-to-degraded ratio. **The first two are matters
of calibration convention; the third is one afternoon's experiment away.**

<!--PAGEBREAK-->

## 9 · ⭐ The out-of-sample test — the first real evidence, and the limit it finds

Everything so far was fitted. This chapter tests the result against data that had no part in
producing it.

**The setup.** `r_Q` was fitted on **one oil, Kiendler, on the post-rebuild rig**. The archive holds
several *within-oil dilution pairs* — the same oil measured at two deliberate strengths. Each is an
independent test with an unambiguous prediction:

> If the correction is right, it must push each pair's dilution slope **toward zero.** If it pushes
> any of them away, something is wrong with it.

No fitting is involved. `r_Q` is simply carried over and applied.

| pair | rig state | span | shipped *s* | **corrected *s*** | |
|---|---|---|---|---|---|
| green `oilK → oilL` | pre-rebuild | 1.50× | +0.01 | **+0.28** | ✗ worse |
| brown `oilN → oilM` | pre-rebuild | 1.50× | +0.12 | **+0.26** | ✗ worse |
| green `0729B → 0729C` | **post-rebuild** | 1.17× | −0.12 | **−0.00** | ✓ **fixed** |

### What the good row is worth

**On the post-rebuild pair the correction takes the dilution slope from −0.12 to −0.00.** That is the
proposal doing exactly what it claims, on data it never saw — and it is **not circular**: `r_Q` was
measured on *Kiendler*, this pair is *Steirerkraft*. It is the first evidence that the residual is a
property of the instrument rather than of one oil, and it is the strongest single result in this
document.

### What the two bad rows are worth

**On both pre-rebuild pairs the correction makes invariance markedly worse** — and those pairs are
the archive's principal evidence that the shipped metric is dilution-invariant at all. A correction
that destroys that is not a small matter.

### The reading that fits all three rows

**`r_Q` transfers between oils, but not across a rig rebuild.** That is physically sensible: the
residual is the curvature of the scattering pedestal as the optics present it, and the 2026-07-29
rebuild changed the optics. Three consequences follow, and they are now part of the proposal:

1. **`r_Q` is a per-rig-state calibration constant**, not a constant of nature. It must be
   **re-measured after any mechanical change** to the instrument.
2. **It must never be applied retroactively.** Correcting archived pre-rebuild results with today's
   `r_Q` produces worse numbers than leaving them alone.
3. **Assumption A1 splits in two.** "Same for every sample" is now supported *within one rig state*
   and refuted *across rig states*. The next chapter reflects that.

⚠ **This does not rescue the proposal, and it is not meant to.** One good row is one good row. But it
is the first test the correction could have failed outright and did not, and it converts A1 from an
untested hope into a bounded, testable claim.

<!--PAGEBREAK-->

## 10 · Every assumption, in one place

The correction is one subtraction, but it rests on six statements. They are listed in descending
order of how much damage they would do if false.

**A1 — `r_Q` is the same for every sample *within one rig state*.** *This is the load-bearing one, and
chapter 9 has now split it in two.*

`r_Q` describes the curvature of a particular sample's pedestal, and pedestals come from suspended
droplets, which differ between preparations. If `r_Q` varied sample to sample, subtracting one fixed
number would not be a correction but a new error.

#### ⚠ What the two-oil agreement is worth — considerably less than it looks

The two fitted values are −0.0246 and −0.0212, 16 % apart, and it is tempting to read that as
confirmation. It is not:

| | Kiendler | Steirerkraft |
|---|---|---|
| `B_Q` span, as % of its mean | **48 %** | 17 % |
| `r_Q` | −0.0246 ± 0.0037 | −0.0212 ± 0.0193 |
| 95 % interval | −0.0319 … −0.0173 | **−0.0590 … +0.0166** |

**Steirerkraft's interval contains zero.** That oil on its own cannot establish that a residual exists
at all, let alone that it matches. And the formal comparison — difference −0.0035 ± 0.0196, *p* = 0.86
— is close to vacuous: **the smallest difference it could detect is 0.0385, which is 156 % of `r_Q`
itself. It would miss a doubling.**

The cause is the **lever arm**. `r_Q` is an extrapolation back to `B_Q` = 0, and Steirerkraft's `B_Q`
span is barely a third of Kiendler's. Same rig, same protocol, same operator — only the concentration
range differs, and that alone makes the interval five times wider.

⚠ **A tempting shortcut that does not work, recorded so nobody re-derives it.** One can instead ask
*"what `r_Q` would make Steirerkraft's two fills read the same?"* That gives **−0.0242 — a striking
2 % from Kiendler's value.** Bootstrapped over its runs, its 95 % interval is **−0.114 … +0.010 —
wider than the regression it was meant to improve on.** The apparent precision was entirely an
artefact of quoting a point estimate without an error bar.

#### What the evidence actually is, in descending order of weight

1. **The consequence test (chapter 9).** Carrying Kiendler's `r_Q` onto Steirerkraft drives its
   dilution slope from −0.12 to **−0.00**, and its two fills from a −1.85 % gap to **+0.02 %**.
   Testing what the constant *does* has far more power than comparing two blurry parameters, because
   the fills either land on top of one another or they do not.
2. **Reproducibility within one oil.** Kiendler's two independent preparation contrasts give
   **−0.0206** (−0.0287 … −0.0138) and **−0.0288** (−0.0379 … −0.0213) — overlapping intervals,
   bracketing the pooled −0.0246. So `r_Q` reproduces across independent preparations of one oil.
3. **The two-oil point-estimate agreement.** Real, and nearly weightless, for the reasons above.

#### ⇒ The verdict splits

- **Across OILS, within one rig state: supported** — on items 1 and 2, not on item 3.
- **Across RIG STATES: refuted.** The same constant applied to pre-rebuild pairs makes invariance
  *worse*, +0.01 → +0.28 and +0.12 → +0.26.

**⇒ `r_Q` is a per-rig-state calibration constant.** It must be re-measured after any mechanical
change and never applied retroactively. Chapter 12 shows the assumption still changing an answer
*within* a rig state, so "supported" is not "settled".

**A2 — `r_Soret` is negligible.** The leftover at the Soret band is treated as zero. Justification:
the Soret band lies outside the anchors and is 13× taller, so the same leftover is 13× less
important. **Not separately measured** — the fit cannot distinguish `r_Soret` from
$M_{\infty} \cdot r_{Q}$, because only the combination appears in the intercept. If `r_Soret` is not
zero, the quoted `r_Q` absorbs it and is biased.

**A3 — the pedestal is convex.** Chapter 4's sign prediction depends on it. Scattering theory says
convex; the measured sign agrees. If some sample's pedestal were concave, the correction would push
the wrong way.

**A4 — Beer-Lambert holds in both bands.** That absorbance is proportional to concentration, with no
saturation. At the Soret band the transmitted signal is already at ~6.5 % and the blue edge is dark,
so this is **weakest exactly where the numerator lives**. Stray light in a saturated band compresses
absorbance, which would appear as a concentration-dependent error of its own.

**A5 — one pigment species dominates each band.** The model has a single `e_Soret` and a single
`e_Q`. The oil actually contains protochlorophyll *and* its degradation product, and the whole point
of the verdict is that their proportion changes. The index is therefore already a mixture ratio; the
correction does not change that, but $M_{\infty}$ should be read as "the pedestal-free index", not as
a physical extinction ratio.

**A6 — the two anchor windows are quiet.** They are not, entirely: the far anchor at 600–630 nm sits
on the pigment's Qy flank. Pigment contamination of an anchor scales with concentration, so it is
**harmless to the argument here** — it cannot produce a concentration-independent intercept. What the
intercept measures is specifically the part that does *not* scale.

<!--PAGEBREAK-->

## 11 · What the correction buys, and what it costs

**Buys — the spread collapses.** Three preparations of one oil: 10.8 % → 2.5 %.

**Buys — the number stops depending on preparation quality.** Today an unusually clear or unusually
cloudy sample shifts the verdict by ~10 % with nothing to warn the operator. That is the property
that makes a measurement **transferable between operators and sites** — which matters more for a
laboratory partner than precision does.

**Costs — the threshold must be re-derived.** Everything moves down: greens from 12–14 to ≈ 9.6–10.1,
brown from 9.3 to ≈ 7.6. **The shipped `T` = 10.6 would sit above both green oils and reject them.**
A corrected threshold would land near 8.6, but it must be *derived*, not scaled.

**Costs — one more constant to maintain.** `r_Q` becomes a calibration parameter with a provenance,
an uncertainty and a review schedule.

**Does not buy — better discrimination.** Between green and brown the correction changes very little,
because both classes are inflated by similar amounts. **It is an accuracy and transferability fix,
not a sensitivity fix.** Anyone hoping it will sharpen the green/brown call should not expect it to.

**A caution about `T` that applies whether or not the correction is adopted.** The present threshold
was calibrated on inflated numbers. If the sample is ever made physically cleaner — a filter, a
better solvent — `r_Q` shrinks toward zero, every reading falls by up to 29 %, and **`T` = 10.6 stops
being valid with no error message and no visible symptom.** That risk exists today.

<!--PAGEBREAK-->

## 12 · ⚠ The chapter that argues against the proposal

**Read this before acting on the document.**

### The ranking test, and how it fails

The correction appears to confirm something independent: the operator's own visual judgement that the
Kiendler oil is slightly greener than the Steirerkraft one. Corrected, Kiendler reads 10.00 and
Steirerkraft 9.62 — Kiendler greener by 3.9 %, agreeing with the eye.

**That agreement is an artefact of assumption A1.** The 9.62 was obtained by applying *Kiendler's*
`r_Q` to Steirerkraft. Using each oil's **own** measured `r_Q` instead:

| | corrected with shared $r_{Q}$ | corrected with each oil's own $r_{Q}$ |
|---|---|---|
| Kiendler | 10.00 | 10.00 |
| Steirerkraft | 9.62 | **9.93** |
| S-Budget | 7.58 | 7.58 |
| **Kiendler vs Steirerkraft** | **+3.9 %** | **+0.7 %** |

**Under the second reading the two green oils are indistinguishable, and the apparent confirmation of
the visual ranking disappears entirely.** The data cannot currently decide between the two readings,
because Steirerkraft's own `r_Q` is known only to ±0.019 — an error bar wide enough to contain both.

**⇒ The correction must not be adopted because it agrees with the eye. On this evidence, whether it
agrees with the eye is a free parameter.**

### Three other ways this could be wrong

- **The fit is dominated by one contrast.** Kiendler's intercept is driven by set A sitting apart
  from sets B and C. That is one comparison with n = 6 against n = 4, not ten independent points.
- **The two axes share a spectrum.** `B_Soret` and `B_Q` come from the same measurement, so noise
  common to both inflates the *slope*. The **intercept** is the claim and is more robust — but the
  concern is real and unquantified.
- **Set A was changing while it was measured.** Its bands drifted 8–37 % over 32 minutes. The fit
  treats its six runs as six samples of one state; they are not.

<!--PAGEBREAK-->

## 13 · What would settle it

Four tests. **T0 has been done — chapter 9. The rest have not.**

**T0 — carry `r_Q` onto a pair it was not fitted on. ✅ DONE (chapter 9), and it passed once and
failed twice.**
Within a rig state the correction did exactly what it promised; across a rebuild it did the opposite.
That result is what makes T1 worth doing and T1b necessary.

**T1 — measure `r_Q` on every oil in the campaign.** Each oil needs at least two preparations of
genuinely different strength, ideally spanning more than Steirerkraft's narrow 17 %. Then ask the
only question that remains: **within one rig state, is `r_Q` one constant, or does each sample have
its own?** If the four values agree within their errors, A1 is supported well enough to adopt. If
they scatter, the correction is dead in this form. **This costs nothing beyond what the campaign is
already scheduled to do**, provided each oil is prepared at two strengths rather than one.

**T1b — re-measure `r_Q` after the next mechanical change, and check it moved.** Chapter 9 says it
should. If it does not move when the optics change, the whole physical story is wrong and the value
is fitting something else. This is a cheap and unusually sharp test, because it predicts a *change*
rather than a constancy — and a prediction of change is much harder to satisfy by accident.

**T2 — report both numbers in parallel.** Compute `M` and $M_{\infty}$ on every run and record both.
The corrected number changes no decision while it is only being recorded, and after a dozen samples
its behaviour is known rather than argued about.

**T3 — attack `r_Q` physically instead.** If the sample can be made genuinely clear — 0.22 µm
filtration, or a solvent that dissolves the oil rather than suspending it — then `r_Q` goes toward
zero, and no arithmetic correction is needed at all. **This is the better outcome**, and it is the
strongest remaining argument for the filtration work: not that it improves precision, but that it
removes the term that makes the number non-transferable.

**The recommendation of this document is T2 immediately, T1 during the campaign, T1b at the next rig
change — and explicitly not to change the shipped verdict.**

<!--PAGEBREAK-->

## Appendix A — every number

Produced by `diagnostics/pedestal_correction.py`. Set values are means over runs.

| set | n | A_Soret raw | A_Q raw | turbidity 520–540 | `B_Soret` | `B_Q` | M shipped |
|---|---|---|---|---|---|---|---|
| Kiendler A | 6 | 0.8263 | 0.1108 | 0.0378 | 0.8221 | 0.0576 | 14.279 |
| Kiendler B | 2 | 1.1231 | 0.1994 | 0.0919 | 1.0819 | 0.0849 | 12.740 |
| Kiendler C | 2 | 1.1705 | 0.2082 | 0.1018 | 1.1160 | 0.0856 | 13.039 |
| Steirerkraft B | 6 | 1.0931 | 0.1968 | 0.0981 | 1.0331 | 0.0828 | 12.489 |
| Steirerkraft C | 6 | 1.1864 | 0.2300 | 0.1231 | 1.1043 | 0.0901 | 12.251 |
| S-Budget D | 6 | 1.0855 | 0.2251 | 0.1038 | 1.0093 | 0.1085 | 9.303 |

**Provenance.** Kiendler = `spectracs-references/tmp/20260801A|B|C/`, one evening, three
preparations of one oil. Steirerkraft = `20270729B/C`, two fills. S-Budget = `20260731A`, six
re-seats of one fill ("series D"). All post-rebuild, same instrument and protocol.

**Constants used.** `r_Q` = −0.0246 A (Kiendler, run-level fit). Bands: Soret 440–460, Q 560–580,
anchors 520–540 and 600–630 nm.

**Chapter 9's dilution pairs.** `oilK`/`oilL` = one green oil at 2 and 3 drops; `oilN`/`oilM` = one
brown oil at 2 and 3 drops (both 2026-07-21, PRE-rebuild); `20270729B`/`C` = Steirerkraft at two
strengths, post-rebuild. Produced by `diagnostics/all_metrics_archive.py`, which also emits the
whole archive — 122 measurements across 40 series — as a single CSV.

## Appendix B — reproduction

```
export PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"

./venv/bin/python diagnostics/pedestal_correction.py    # chapters 1-7: numbers + both figures
./venv/bin/python diagnostics/all_metrics_archive.py    # chapter 9: the out-of-sample test

python3 docs/tools/build_pedestal_correction_pdf.py     # rebuild this PDF
```

The first prints every table in chapters 1–7 and writes both figures into `docs/figures/`. The second
prints chapter 9's dilution-pair table, plus the whole-archive metric matrix it is drawn from. The
third rebuilds this PDF from the markdown master.

## Appendix C — where this sits in the specifications

| | |
|---|---|
| the derivation this confirms | `SPEC_capture_quality.md` §16.14.4–6 — pedestal curvature as the *only* mechanism that can break dilution invariance |
| the session that measured it | §16.15, and the lab diary entry for 2026-08-01/02 |
| the bound this supersedes | §16.14.7 asserted a bound of 0.008 A on the residual from pooled archive data; the measured value is ~3× that |
| the threshold at risk | §16.10.17d, and §16.15.7 for what the pedestal-free scale does to it |
| the open question | §16.10.8, dilution invariance, which the 2026-08-01 session did **not** close |
