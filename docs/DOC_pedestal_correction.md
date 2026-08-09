<!--
MASTER DOCUMENT — the pedestal correction.
This markdown file is the SOURCE OF TRUTH. The PDF is generated from it:

    python3 docs/tools/build_pedestal_correction_pdf.py
    -> ../spectracs-docs/internal/Spectracs_PedestalCorrection.pdf

Never hand-edit the PDF. Edit here, re-run, commit both.

Chapters 1-7 and all eight figures come from `diagnostics/pedestal_correction.py`; chapter 9's
out-of-sample test comes from `diagnostics/all_metrics_archive.py`. Both call the SHIPPED code paths
rather than re-implementing them. Re-run both before regenerating this PDF.

This document is DOCUMENTATION plus ONE PROPOSAL. The proposal (chapter 7) is NOT implemented and
must not be implemented on the strength of this document alone — chapter 12 says what would have to
be true first.

⚠ The renderer's math notation is deliberately small. It supports _{} ^{} \frac \sqrt and the symbol
list in build_capture_fidelity_pdf.py. It does NOT support \; — use plain spaces around operators.
-->

# The Pedestal Correction

*Why the Pigment Index reads about 26 % too high, where the error comes from, and what a single
subtraction would do about it.*

**Why this document exists.** On 2026-08-01 three preparations of the same green oil returned three
different verdict numbers — 17.12, 15.45 and 15.91 — a spread of 10.3 % on an oil that had not
changed. Chasing that down produced a measurement of a quantity the specification had only ever
derived on paper, and with it a correction that would remove most of the spread. This document
explains the whole chain from first principles, so that the proposal can be judged rather than
believed.

**Its companions.** *Capture Fidelity* covers the instrument — how a webcam becomes a spectrum.
*Light, Pigment and Solvent* covers the sample. *From Spectrum to Verdict* covers the arithmetic that
turns an absorbance curve into a verdict. **This document is a correction to that arithmetic**, and
assumes only chapter 5 of it.

**How to read it.** **§1.1 is the whole argument on one page** — start there, and return to it whenever
the thread is lost. §2.1 lists every symbol. Chapters 2–4 build the problem from nothing and contain no
algebra beyond a subtraction; **§3.1 is the one picture that carries all of them.** Chapter 5 is the one
piece of real algebra and is worth the effort — everything after it is consequence. Chapter 8 says what
the corrected number physically IS; chapter 9 is the first real test of it. Chapter 10 lists every
assumption in one place. **Chapter 12 is the chapter that says why this may be wrong**, and should be
read before anybody acts on it.

**Status.** The measurement is real. The correction is a **proposal** — fitted on one oil,
confirmed out-of-sample on a second, and shown by the same test NOT to survive a rig rebuild.

⭐ **Rewritten 2026-08-03 onto the SHIPPED anchor.** The correction now ships in the bench plugin, and the
far baseline window moved from 600–630 nm to **620–630 nm** (`SPEC_capture_quality.md` §16.20). **Every
number in this document is on the 620–630 anchor**, which is what the instrument computes.

⚠ **`r_Q` belongs to its anchor, and the two must never be mixed:**

| far anchor | `r_Q` | |
|---|---|---|
| **620–630 nm** | **−0.0184 ± 0.0043 A** | **the shipped configuration — this document** |
| 600–630 nm | −0.0246 ± 0.0037 A | the older window, kept only in §4.1–4.2 |

⚠ **§4.1 and §4.2 are deliberately still on 600–630.** They are the investigation that *moved* the window,
and on the new anchor the 607 nm lamp line lies **outside** it entirely — so "what is the far anchor
contaminated with" is not a question this anchor can be asked. Those two sections say so where they start.

⚠ **Added 2026-08-02: §4.1 and §4.2.** Checking the mechanism for *size* rather than sign shows that
the pedestal's own curvature accounts for **at most a sixth** of the measured residual (Appendix D.3);
the obvious replacement suspect, a contaminated far anchor, was then tested and **refuted** (§4.2). **Nothing on record explains
`r_Q`'s size.** ⚠ *Superseded in part 2026-08-04: A4's failure — dead bins in the Soret
window — accounts for **28 %**. See the box at A4 and `SPEC_metric_research.md` §7.13.* This leaves the correction itself untouched, since `r_Q` is fitted rather than derived,
but it weakens chapter 8's appeal to a successful prediction, reframes chapter 9's rebuild failure, and
closes one of chapter 13's routes. Read §4.1–4.2 alongside chapter 8.

<!--TOC-->

<!--PAGEBREAK-->

## 1 · The claim, in one page

The instrument produces an absorbance curve. The verdict is a **ratio of two heights** taken off that
curve, after a straight line has been subtracted from it:

```math
M = \frac{B_{Soret}}{B_{Q}}
  read: the verdict number is the blue band divided by the green-yellow band, both baselined.
```

`B_Soret` is the pigment's blue absorption band (440–460 nm); `B_Q` is its much weaker green-yellow
band (560–580 nm), both measured above a straight line fitted through **520–540 and 620–630 nm**. Green
oil scores high, brown oil low.

**On the name.** `M` is the **Pigment Index** — the shipped verdict number, defined in *From Spectrum
to Verdict* §5.2. It is written `M` throughout this document only because it appears inside fractions
on nearly every page. Nothing new is being introduced; §2.1 lists every symbol.

**The problem.** The straight line that gets subtracted is an approximation, and it does not remove
exactly the right amount. What it leaves behind at the Q band we call `r_Q`. Because `B_Q` is a small
number, a small leftover is a large fraction of it — and `B_Q` is the **denominator**, so the whole
ratio inherits that fraction.

**The measurement.** `r_Q` = **−0.0184 ± 0.0043 A**, obtained from ten runs of one oil — **the
Kiendler oil, and every corrected number in this document uses that one value.** A second oil gives
−0.0275 ± 0.0284 A, but that interval contains zero and adds very little; the brown oil gives nothing
at all — chapter 10 weighs this honestly, and the real confirmation is chapter 9's out-of-sample test.
`r_Q` is **negative**, meaning the correction subtracts slightly too much. It is obtained as the
**x-intercept** of a straight-line fit, not its slope — §6 separates the three quantities that fit
returns, because confusing them is easy and the geometry is the whole argument.

**The size.** At the standard recipe this inflates the verdict number by about **26 %** (an inflation
factor `F` = 1.26, defined in §5.1); on an over-dilute sample it reached **38 %**.

**The proposal.** Put the leftover back before dividing:

```math
M_{\infty} = \frac{B_{Soret}}{B_{Q} - r_{Q}}
  read: add the over-subtracted amount back into the denominator, then divide as before.
```

$M_{\infty}$ is the **pedestal-free Pigment Index** — what the ratio would be if the baseline left
nothing behind. The ∞ is not a limit of anything physical; it is read as *"at infinite concentration"*,
because that is where the residual becomes negligible (§5).

One subtraction, using quantities every run already computes. Applied to the three preparations that
started this, their spread falls from **10.3 % to 3.0 %** — ⚠ an **in-sample** figure, for the
reason §7 gives; the test that could fail is chapter 9's.

**What it costs.** The numbers move to a different scale — green lands near 12.4 instead of 15.5–17.1,
brown near 8.6 instead of 10.2 — so **any threshold set on the uncorrected scale must be re-derived.**
⚠ The shipped plugin retains `T` = 10.6 on this metric (`SPEC_capture_quality.md` §16.20.7); it lands
inside the class corridor and classifies every archived run correctly, but it was **inherited, not
derived on this scale**.

**What it assumes — the one sentence to carry.** That **`r_Q` belongs to the instrument, not to the
oil**: that it is fixed by where the anchors sit and how the pedestal curves between them, so one
number measured on one oil may be applied to every other sample in that rig state. That is the whole
risk. It has to be true for the correction to be worth having at all — a per-oil constant could never
be calibrated in the field — and it is currently supported by **one oil**. Chapter 6 states the claim
and its caveats in full, chapter 9 tests it out-of-sample for the first time, and chapter 12 shows a
concrete case where it changes the answer.

<!--PAGEBREAK-->

## 1.1 · ⭐ The whole derivation on one page

Every step from a photograph to the corrected number, with **one real set carried through all of
them** — Kiendler C, two runs, post-rebuild. Nothing on this page is new; it is the rest of the
document compressed, and it is here so that the shape of the argument can be seen before the detail
arrives.

| # | what happens | the step | Kiendler C |
|---|---|---|---|
| **1** | two captures, one with solvent only, one with the sample | $A = \log_{10}(R/S)$ | a curve, ~1.14 A at 450 nm |
| **2** | average the curve over four fixed windows | $A_{X} = \op{mean}$ over window `X` | `A_Soret` 1.1705 · `A_Q` 0.2082 · `A_near` 0.1018 · `A_far` 0.2011 |
| **3** | fit a straight line through the two *anchor* windows | the **chord** | 520–540 and **620–630** *(§3.1)* |
| **4** | subtract that line everywhere | $B_{X} = A_{X} - \op{chord}$ | `B_Soret` **1.1397** · `B_Q` **0.0716** |
| **5** | divide the two remaining heights | $M = B_{Soret} / B_{Q}$ | **15.91** ← *the uncorrected verdict* |
| **6** | but the chord is straight and the pedestal is not, so a leftover stays at Q | $r_{Q} = -k/M_{\infty}$, the **x-intercept** of $B_{Soret}$ vs $B_{Q}$ *(§6)* | **−0.0184 ± 0.0043 A** *(t = 4.43)* — **one oil's**, applied to all |
| **7** | a leftover in the *denominator* inflates the ratio | $F = 1 - r_{Q}/B_{Q}$ | **1.257**, i.e. **+25.7 %** |
| **8** | put the leftover back, then divide again | $M_{\infty} = B_{Soret} / (B_{Q} - r_{Q})$ | **12.66** ← *the corrected verdict* |

**Reading the page as one sentence.** *Steps 1–5 are the shipped metric. Step 6 says the baseline in
step 3 does not do its job exactly. Step 7 says the error lands where it hurts most, because `B_Q` is
small and it is the denominator. Step 8 undoes it.*

**Where each step can go wrong**, with the chapter that examines it:

| step | the risk | where |
|---|---|---|
| 3 | the anchors are not clean — the far one carries pigment, and the older 600–630 window also carried the 607 nm lamp line | **§4.1**, A6 |
| 4 | a straight line cannot follow a curved pedestal — this is the whole problem | ch. 4 |
| 6 | **`r_Q` may belong to the oil rather than to the instrument** — the load-bearing assumption; it may also not survive a rig rebuild | **§6**, ch. 9, A1 |
| 8 | the numbers land on a new scale, so any threshold set on the uncorrected one must be re-derived | ch. 11 |

<!--PAGEBREAK-->

## 2 · What the instrument actually hands us

Everything below starts from one curve: **absorbance against wavelength**, written $A(\lambda)$.

Absorbance is defined from two captures — the reference (pure solvent, no oil) and the sample:

```math
A(\lambda) = \log_{10}\frac{R(\lambda)}{S(\lambda)}
  read: how many factors of ten the sample dims the light, at each wavelength.
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
| far anchor | **620–630 nm** | chosen to start after the 607 nm lamp line and to sit on the pigment's Qy band *(§16.20)* |

The two **anchors** are not measurements of the pigment. They exist to answer a different question,
which is the subject of the next chapter.

**A note on band values.** Each window's value is the mean absorbance over the points inside it.
Where this document quotes a set's value it is the **mean over that set's runs**. One consequence
worth knowing when checking the arithmetic: the mean of a ratio is not exactly the ratio of the
means, so recomputing `M` from the quoted `B_Soret` and `B_Q` reproduces the quoted `M` to about
0.05 %, not exactly.

### 2.1 Every symbol, in one place

Nothing here is needed yet — this table exists so that no symbol later in the document has to be
looked up by hunting backwards through the prose. **The last column is the one that matters**: it
says of each quantity whether we *measured* it, *derived* it, *fitted* it, or merely *assumed* it.

| symbol | what it is | unit | typical value | where it comes from |
|---|---|---|---|---|
| λ | wavelength | nm | 420–650 | the calibration |
| `R`, `S` | reference and sample intensity | DN | ~88, ~6 at Soret | **measured** |
| $A(\lambda)$ | absorbance, $\log_{10}(R/S)$ | A | 0 – 1.3 | **measured** (ch. 2) |
| `A_X` | raw band mean over window `X` | A | `A_Q` = 0.2082 | **measured** |
| $P(\lambda)$ | the **pedestal** — the broad background under the spectrum; *what causes it* is Appendix D | A | ~0.10 at 530 nm | **inferred**, never observed alone |
| $A_{pigment}$ | what the pigment alone would absorb | A | — | **not observable** — the thing we want |
| `B_X` | band mean **after** the linear baseline | A | `B_Soret` = 1.1397, `B_Q` = 0.0716 | **derived** from `A_X` |
| `r_X` | the **residual** — what the baseline fails to remove at band `X` | A | `r_Q` = −0.0184 | **fitted** (ch. 6) — the **x-intercept**, $-k/M_{\infty}$, *not* the slope |
| `r_Soret` | the same, at the Soret band | A | treated as 0 | **assumed** — A2, not measured |
| `M` | the **Pigment Index** — the uncorrected verdict number | — | 15.91 (green), 10.16 (brown) | **computed**, shipped |
| $M_{\infty}$ | the **pedestal-free** Pigment Index | — | 12.66 (green), 8.59 (brown) | **derived** — the correction |
| `F` | the **inflation factor**, $M / M_{\infty} = 1 - r_Q/B_Q$. Quoted as a percentage it is always `F` − 1 = \|`r_Q`\|/`B_Q` — the y-axis of Figure 8 | — | 1.257, i.e. +25.7 % | **derived** (§5.1) |
| `T` | the verdict threshold | — | **10.6** | **shipped constant** — invalid after correction (ch. 11) |
| `c` | pigment concentration | — | unknown | **eliminated** by the fit (ch. 6) |
| $\ell$ | optical path length | cm | fixed by the cuvette | constant, cancels |
| `e_X` | extinction coefficient at band `X` | — | unknown | **cancels** — only their ratio survives |
| `k` | intercept of the straight-line test, $r_{Soret} - M_{\infty} r_Q$ | A | +0.2287 ± 0.0516 | **fitted** (ch. 6) — carries **both** bands' leftovers, inseparably |
| `t` | Student's *t* of that intercept | — | 4.43 | **computed** |
| `s` | dilution slope of the index | — | −0.05 → +0.05 | **computed** (ch. 9) |
| `n` | scattering exponent, $P \propto \lambda^{-n}$ — used **only** in Appendix D | — | ~4 in theory | **assumed** — not measurable on this rig |

⚠ **Two rows deserve a second look.** `n` is *assumed*, not measured, and it appears nowhere outside
Appendix D — the λ⁻ⁿ fit was withdrawn as invalid on this instrument (`SPEC_capture_quality.md`
§16.12.11 B), so the pedestal's convexity rests empirically on the measured **sign** of `r_Q` alone. And
`r_Soret` is *assumed zero* — chapter 6's fit cannot separate it from $M_{\infty} \cdot r_{Q}$, so if
it is not zero, the quoted `r_Q` has quietly absorbed it.

<!--PAGEBREAK-->

## 3 · The pedestal, and why a baseline is subtracted at all

The measured curve does not sit on zero. It sits on a **pedestal**: a broad, smooth background that
is present at every wavelength and belongs to no pigment. Light lost to it never reaches the camera,
so the instrument cannot tell it from absorbance — it simply arrives as "absorbance".

⚠ **What the pedestal is made of is not settled, and this document does not need it to be.** The
original suspect — light scattered off undissolved oil droplets — turned out to account for at most a
sixth of the effect this document measures. **That investigation is Appendix D**, gathered there
because it is motivation rather than machinery. What chapters 3–13 need is only the pedestal's
*shape*.

```math
A_{measured}(\lambda) = A_{pigment}(\lambda) + P(\lambda)
  read: what we see is what the pigment absorbed PLUS a broad background that has nothing to do with it.
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

### 3.1 The whole thing, in one picture

Everything above and everything below is contained in **Figure 1**. It is one real measurement —
Kiendler C, run 1, on the shipped **520–540 / 620–630** anchors — with nothing idealised:

![**Figure 1** — Left: the four windows, the fitted line, and the two heights the verdict is made of. Right: the same run zoomed on 515–630 nm, showing what the far anchor is actually sitting on.](figures/pedestal_chord.svg)

**Read the left panel first.** The black curve is the absorbance. The four shaded windows are the
regions the plugin reads. The dashed red line is the fitted baseline, drawn through the two anchor
windows. The two green arrows are `B_Soret` and `B_Q` — **the verdict is the ratio of those two
arrows.** That is the entire reading workflow.

**Then the right panel, which is where the trouble is.** Zoomed in, two things are visible that the
left panel is too coarse to show:

- The **fitted line rises toward the red**. A background that decays with wavelength cannot do that,
  so whatever this line is tracking, it is not a simple decaying pedestal — §4.1 pursues it, and it is
  the thread that eventually moved the window.
- The far anchor **starts after the 607 nm lamp line** and sits on the pigment's own **Qy band**
  (~623–626 nm). That placement is deliberate (`SPEC_capture_quality.md` §16.20): the older 600–630
  window straddled both, and §4.1–4.2 are the investigation of what that cost.

Chapter 4 develops the consequence of the chord being a chord; §4.1 returns to what this panel shows.

### 3.2 ⭐⭐ The premise of this document, measured  *(2026-08-09; full record in `SPEC_capture_quality.md` §16.28)*

Everything from chapter 4 onward rests on §3.1's claim that the far anchor is **not** sitting on empty spectrum
but on the pigment's own Qy band. That was placement by argument — taken from the literature and from which
window separated the classes better. It has since become a measurement.

Two runs on the same rig with **two different lamps** put the lamps' own sharp emission structure 3.4 nm apart,
and the absorbance maximum stayed at **629–630 nm** under both, at 256 σ. Instrument structure moves with the
instrument; this did not. There is a real absorption band there, and the far anchor is standing on it.

⇒ **The pedestal correction is compensating for a band that has been measured, not for one that was suspected.**
⚠ And the corollary runs the way this document has always argued: confirming the band makes `r_Q` **more**
necessary, not less. A reader who takes "the far anchor is confirmed" as licence to drop the residual has
inverted the finding. The same session also priced the correction against a change of lamp — a third axis
chapter 11 never tested it on — and it improves lamp transfer at both window choices.

⚠ **One thing that session did NOT confirm.** The *near* anchor is not flat either: 520–540 nm sits on a
reproducible bump peaking near 530 nm, present under both lamps, with the region's true minimum at
**505–511 nm**. Chapter 10's assumption list should be read with that in mind — **both** anchor windows sit on
signal, and only the far one is corrected.

<!--PAGEBREAK-->

## 4 · What a straight line cannot remove — and which way it errs

**The pedestal is convex** — steep in the blue, flattening toward the red. That is a statement about
its *shape*, and it is the only thing this chapter needs; every candidate background the project has
considered has it, which is why the argument below survives Appendix D's verdict on the cause.

Now the geometry that decides everything:

- We fit the line through two windows, at **520–540 nm** and **600–630 nm**.
- A straight line through two points on a convex curve is a **chord**.
- **A chord lies *above* the curve everywhere between its endpoints.**
- The Q band, **560–580 nm, lies exactly between them.**

So at the Q band the fitted line sits **above** the true pedestal, and subtracting it removes the
pedestal **plus a slice of genuine pigment signal**.

![**Figure 2** — Three possible pedestal shapes and the chord through each. Only the curvature matters: the overall slope is irrelevant to where the chord falls.](figures/pedestal_cases.svg)

**Figure 2's middle panel is worth dwelling on.** If the pedestal happened to be exactly straight, the fit
would remove it **completely** and there would be no residual at all — no correction needed, no
document. The entire problem is curvature, and nothing else. Note also that the *slope* of the
pedestal is irrelevant to all three panels; only which side of the chord the curve falls on matters.

Write the leftover as `r`, defined as what the line fails to remove — negative where the line
over-subtracts:

```math
B_{X} = A_{pigment,X} + r_{X}
  read: after baselining, band X still carries r_X — negative where the line took away too much.
```

**This predicts the sign before we measure anything: `r_Q` must be negative.** Measured, `r_Q` =
−0.0184 A. ⚠ It is a real prediction that could have come out wrong — but **Appendix D.2 shows it is
worth much less than it looks**, because convexity is shared by every candidate background and the
rest of the argument is window geometry.

**Why the Soret band escapes.** 440–460 nm lies *outside* the two anchors, not between them. There
the chord runs below the curve, and in any case the Soret band is ten to twenty times taller, so a
leftover of 0.025 A is a rounding error against 1.1 A. Throughout this document `r_Soret` is treated
as negligible; chapter 10 lists that as an assumption.

### 4.1 ⚠ The mechanism gets the sign right and the SIZE wrong — by about six times

> **In one line:** the pedestal's own curvature can supply at most a sixth of `r_Q` (Appendix D.3);
> the obvious replacement suspect has since been tested and refuted (§4.2); **nothing on record
> explains the rest**; and the correction does not depend on the answer.
>
> ⚠⚠ **§4.1 AND §4.2 ARE THE ONLY SECTIONS STILL ON THE 600–630 ANCHOR, DELIBERATELY.** They are the
> investigation that *moved* the window, so their subject is that window's contamination — and on the
> shipped 620–630 anchor the 607 nm lamp line lies **outside** it entirely, so the question cannot be put
> to it. Every `r_Q` in these two sections is **−0.0246 A**, the old anchor's value.

*Added 2026-08-02, while drawing §3.1's figure. It does not change the correction, but it changes
what `r_Q` is understood to be, and it supersedes part of chapter 8.*

The argument above is qualitative: convex ⇒ negative. The quantitative question — *is the leftover
the right SIZE?* — is where a mechanism can actually fail, because a model that gets the sign right
and the magnitude wrong is not yet the right model.

**That test was run on the original suspect, and the suspect failed it — the whole of it is Appendix
D.3.** The verdict in one line: a pedestal bounded by the raw absorbance at 530 nm supplies **≤ 17 %**
of the measured 0.0246 A, and no curvature the sample can physically produce reaches the rest.

⇒ **Something else is bending the baseline.** §3.1's right-hand panel says what:

```math
r_{Q} \approx -0.471 \cdot \delta_{far}
  read: an offset on the far anchor lands on the Q band with weight 0.471 — the same interpolation
  weight §5.5 of *From Spectrum to Verdict* quotes. An anchor that reads HIGH pushes r_Q negative.
```

The far window contains the **607 nm artifact** (*From Spectrum to Verdict* §5.9) and the **lamp's red
cliff**, where 620–630 nm sits near 39 DN against 130 at 530 and absorbance runs away
(`SPEC_capture_quality.md` §16.12.11 B). Averaging only the clean stretches of that window — 600–606
and 610–618 nm — estimates what the anchor would have read without them:

| set | `A_far` as used | `A_far` clean | excess $\delta_{far}$ | ⇒ contribution to `r_Q` |
|---|---|---|---|---|
| Kiendler A | 0.0705 | 0.0505 | +0.0200 | −0.0094 |
| Kiendler B | 0.1401 | 0.1050 | +0.0351 | −0.0165 |
| Kiendler C | 0.1462 | 0.1100 | +0.0362 | −0.0171 |
| Steirerkraft B | 0.1322 | 0.0976 | +0.0346 | −0.0163 |
| Steirerkraft C | 0.1591 | 0.1194 | +0.0397 | −0.0187 |
| S-Budget D | 0.1311 | 0.1045 | +0.0266 | −0.0125 |
| | | **mean** | **+0.0320** | *(see below — the mean is the wrong statistic)* |

#### ⚠ Why multiplying that mean would be wrong — and the corrected number

It is tempting to take +0.0320 A, multiply by 0.471, and declare 61 % of `r_Q` explained. **That is
wrong, and an earlier draft of this document said it.** A contamination that grows with the pigment
moves every run *along* the fitted line of chapter 6 and lands in the **slope**. Only a term that does
**not** grow can shift the **intercept** — and `r_Q` is defined as the intercept. This is assumption
A6's own argument, and the draft quoted it approvingly a page earlier and then failed to apply it.

Most of that excess does grow with the pigment. Decomposing it and regressing each part on the Q-band
amplitude across the six sets:

| part of the excess | slope | intercept | R² |
|---|---|---|---|
| the **607 nm** feature | +0.361 | −0.0053 | 0.94 |
| the **rise past 618 nm** | +0.261 | +0.0129 | 0.90 |

Both are dominated by a term proportional to the pigment — which is independently established: the
620–630 nm rise was measured at **5.1 σ** to track the *oil class* under a fixed lamp, making it green
pigment (Qy flank) rather than a lamp artifact (`SPEC_capture_quality.md` §16.12.12).

Taking the **intercept** of the whole excess instead:

```math
\delta_{far,non-scaling} = +0.0169 \pm 0.0177 A \qquad t = 0.96
  read: the part of the contamination that does NOT grow with the pigment — the only part that can
  bias r_Q. On six sets it is not significantly different from zero.
```

| | contribution to `r_Q` | share of −0.0246 A |
|---|---|---|
| far anchor, **non-scaling** part | −0.0079 ± 0.0083 A | **32 % ± 34 %** |
| the original suspect, at its upper bound *(Appendix D.3)* | −0.0042 A | ≤ 17 % |
| **unaccounted** | ~−0.0125 A | **~51 %** |

![**Figure 3** — What the measured residual is made of, and how far its original suspect gets (Appendix D.3).](figures/pedestal_attribution.svg)

**Figure 3** stacks those three contributions against the measured total.

**⇒ Two conclusions, and they are of very different strengths.**

**Solid: the original suspect is ruled out as the main term.** That verdict rests on nothing but the
pedestal's bounded magnitude — Appendix D.3 gives it in full. At the most generous reading it supplies
a sixth of the residual.

**⚠ Not established: that the far anchor supplies the rest.** The estimate has the right sign and a
plausible size, but on six sets it is 1.0 σ from zero. **A hypothesis with a number attached is not a
result** — so the next section tests it rather than adopting it.

### 4.2 ⛔ The far anchor, tested — and it is not the cause either

The test costs nothing. The red anchor is a *parameter*, every measurement is already on disk, and the
baseline routine already accepts a list of windows. **Excise the 607 nm lamp line — 606–610 nm — from
the red anchor, refit, and see what becomes of `r_Q`.**

> ⛔ **An earlier draft also removed 618–630 nm, calling it "the lamp's red cliff". That was wrong.**
> The lamp does collapse there, but the *rise* in absorbance across 620–630 was measured to track the
> **oil class** under a fixed lamp, at 5.1 σ — so it is the pigment's own **Qy flank**, and
> protochlorophyll's Qy sits at ~623–626 nm, inside that stretch. Removing it does not clean the
> anchor; it **throws away the most information-rich part of the window**. The corrected test excises
> the 607 nm line and nothing else.

⚠ One detail decides whether the comparison is fair: the baseline fit gives **each window equal total
weight**, so splitting the red end in two would hand it twice the influence it had. The near window is
therefore counted twice, restoring the original balance. Exactly one thing then changes: which red
points are used.

**Stated before running:** if the anchor supplies ~32 %, `|r_Q|` should fall from 0.0246 to about
0.017. If it supplies nothing, `r_Q` should not move. If it supplies everything, `r_Q` should collapse.

| oil | anchor | slope $M_{\infty}$ | intercept `k` | *t* | `r_Q` |
|---|---|---|---|---|---|
| **Kiendler** | shipped | 9.998 | 0.2463 | 7.01 | **−0.0246** |
| **Kiendler** | **607 line excised** | 8.748 | **0.2836** | **10.53** | **−0.0324** |
| Steirerkraft | shipped | 9.930 | 0.2103 | 1.13 | −0.0212 |
| Steirerkraft | **607 line excised** | 7.094 | 0.3941 | 2.59 | **−0.0556** |

**Every outcome allowed for was a decrease. The residual got bigger — on both oils — and more
significant** (Kiendler's *t* rises from 7.01 to 10.53, so this is not noise).

#### Exactly which wavelengths, and what the rejected draft cost

**606.0–610.0 nm** is removed — 4 nm, 28 of the window's 212 grid points, 13 %. The red anchor's
centroid moves only **615.1 → 616.1 nm**, so the near-red lever is essentially unchanged and there is
**no geometry confound**.

The two ⛔ rows below also delete 618–630 nm, the pigment's Qy flank. They are not tests of the
artifact; they price the mistake:

| far anchor | centroid | $M_{\infty}$ | `k` | *t* | `r_Q` | dilution `s` |
|---|---|---|---|---|---|---|
| **shipped 600–630** | 615.1 | 9.998 | 0.2463 | 7.01 | **−0.0246** | **−0.12** |
| **607 line excised** *(the valid test)* | **616.1** | 8.748 | 0.2836 | 10.53 | **−0.0324** | **−0.20** |
| ⛔ also deletes the Qy flank 618+ | 609.1 | 8.806 | 0.2549 | 9.16 | −0.0289 | −0.16 |
| ⛔ deletes the 607 line AND the Qy flank | 609.4 | 7.468 | 0.3044 | 13.53 | −0.0408 | −0.22 |

**Removing the one genuine artifact makes the residual bigger and the metric measurably more
dilution-variant** — `s` goes −0.12 → −0.20. That is the practical form of the result: the sensitivity
is `r_Q`/`B_Q` (§5), so a larger residual must show up as worse invariance, and it does.

The ⛔ rows show what deleting the Qy flank costs: $M_{\infty}$ collapses to 7.468 and `s` reaches
−0.22 — the same finding, from another direction, as the measurement that removing the far window's
pigment content makes the two oil classes overlap.

**Reading it properly.** `r_Q` = −`k`/$M_{\infty}$ compounds two separate movements, and they deserve
separate quotation: the **intercept rose 15 %** and the **slope fell 12 %**. The intercept is the claim
— it is the thing that had to vanish if the anchor were the cause — and it went the wrong way. The rest
of the change is the scale shifting, which is expected: those red points carry real pigment
information, so removing them lowers the pedestal-free index. That also means **the clean-anchor number
is on a different scale and must never be compared against the threshold.**

**⇒ Two candidate mechanisms are now dead**: the pedestal's own curvature (too small — Appendix D.3)
and anchor contamination (wrong direction, here). **`r_Q` is real, reproducible, transfers between oils within one
rig state, does not survive a rebuild — and is unexplained.**

This *strengthens* chapter 13's recommendation rather than weakening it. A correction that works
empirically and is not understood mechanistically is exactly the kind that should be reported in
parallel and not yet allowed to decide anything.

#### What this changes, and what it does not

**It does not touch the correction.** `r_Q` is *fitted*, not derived. Chapter 6 measures it from the
intercept without assuming any mechanism, and chapter 7 subtracts it. All of that stands regardless of
what causes the residual.

**It does change three readings elsewhere in this document:**

1. **The successful sign prediction is much weaker than it was once presented.** A too-high far anchor
   drives `r_Q` negative *just as* a convex pedestal does — and so does every other candidate. The sign
   discriminates between none of them. **Appendix D.2** works out what it is actually worth.
2. **Chapter 9 becomes the expected result rather than a surprise.** `r_Q` failed to survive the rig
   rebuild. An instrument artifact — a lamp spectrum and an optical path — is exactly the kind of
   thing that changes when the instrument is rebuilt, while a property of the sample would not.
3. **Chapter 13's T3 is aimed at the wrong target.** Filtering the sample or changing the solvent
   attacks *turbidity*, which supplies at most a sixth of `r_Q` (Appendix D.4). **Filtration cannot
   remove what is not turbidity**, so it can no longer be presented as the strong lever on the
   residual — even though the replacement lever is not yet identified.

It also explains a result this document reaches by a different route: chapter 10 finds that `r_Q`
behaves as a **constant** rather than scaling with turbidity. An instrument artifact does not scale
with how cloudy the sample is. Two independent observations, one explanation.

⚠ **This is an attribution, not a decomposition.** $\delta_{far}$ is not perfectly constant across
sets (+0.0200 to +0.0397), and "clean stretches" is a judgement about which parts of a window to
trust. The claim is that the far anchor is the **leading** term, not that the arithmetic closes
exactly.

<!--PAGEBREAK-->

## 5 · Where the error lands — and why the denominator suffers

This is the one piece of algebra in the document. Take it slowly; everything afterwards follows.
**Every step is carried alongside by one real set — Kiendler C — so that no line is only symbols.**

Write the true pigment absorbance in each band as concentration `c` times path length $\ell$ times
that band's extinction coefficient `e`:

```math
A_{pigment,Soret} = c \cdot \ell \cdot e_{Soret} \qquad A_{pigment,Q} = c \cdot \ell \cdot e_{Q}
  read: Beer-Lambert, once per band. How much pigment there is, times how strongly it absorbs there.
```

Substituting into chapter 4's definition, what we actually measure is:

```math
B_{Soret} = c \cdot \ell \cdot e_{Soret} + r_{Soret} \qquad B_{Q} = c \cdot \ell \cdot e_{Q} + r_{Q}
  read: what we read off the curve is the pigment's true signal PLUS whatever the baseline left behind.
  with numbers: B_Soret = 1.1397 A and B_Q = 0.0716 A — but only the sums are observable, not the parts.
```

The **true** index — the one that depends only on which pigment is present, not how much — is the
ratio of the extinction coefficients:

```math
M_{\infty} = \frac{e_{Soret}}{e_{Q}}
  read: c and l have cancelled. What is left belongs to the molecule, not to the preparation.
```

Now form the index we actually compute, dropping `r_Soret` as negligible:

```math
M = \frac{B_{Soret}}{B_{Q}} = \frac{c \cdot \ell \cdot e_{Soret}}{c \cdot \ell \cdot e_{Q} + r_{Q}}
  read: the numerator is clean; the denominator carries the leftover.
  with numbers: M = 1.1397 / 0.0716 = 15.91
```

Divide top and bottom by $c \cdot \ell \cdot e_{Q}$:

```math
M = M_{\infty} \cdot \frac{1}{1 + \frac{r_{Q}}{c \cdot \ell \cdot e_{Q}}}
  read: the error is not r_Q by itself — it is r_Q measured AGAINST the pigment signal.
```

**Read that denominator.** The error term is not `r_Q` on its own — it is `r_Q` **divided by the
pigment signal**. Three consequences follow immediately, and they are the whole story:

1. **The error is a *fraction*, not an offset.** A fixed leftover does more damage to a weak sample
   than a strong one.
2. **It grows without limit as the sample is diluted.** Halve the concentration and you double the
   error. This is why over-dilute preparations misread — see **Figure 8**.
3. **`r_Q` sits in the denominator, so its sign is inverted in the result.** `r_Q` negative makes the
   whole expression **larger**. The index reads **high**, not low.

**Why the denominator and not the numerator.** The same absolute error `e` shifts a ratio by `e/B` in
each band, so the damage ratio is simply how much bigger one band is than the other:

```math
\frac{B_{Soret}}{B_{Q}} = \frac{1.1397}{0.0716} \approx 16
  read: the two bands differ in height by a factor of 16, so the same absolute error matters 16x more
  in the smaller one.
```

**An error in `B_Q` is about sixteen times more damaging than the same error in `B_Soret`.** That is
the entire reason this document is about the Q band. Drawn to scale, with the leftover shown against
each band on one axis:

![**Figure 4** — The same 0.0184 A leftover against each band, on a single absorbance scale. Against the Soret band it is 2 % and invisible; against the Q band it is 26 %.](figures/pedestal_bands.svg)

**Nothing is exaggerated in Figure 4** — it is one axis, and the red slab is the same height in
both panels. The asymmetry is entirely because the Q band is small.

### 5.1 The inflation factor `F` — the quantity this document is about

Rearranging the same expression gives the form used from here on:

```math
M = M_{\infty} \cdot F , \qquad F = 1 - \frac{r_{Q}}{B_{Q}}
  read: the number we compute is the true one multiplied by F. F is what the pedestal residual does to it.
```

**`F` is the inflation factor**, and it is the single quantity this whole document measures. It is a
pure number:

- `F` = 1 — no residual, the index is correct.
- `F` > 1 — the index reads **high** by a factor `F`. This is our case: `r_Q` is negative, so
  −`r_Q`/`B_Q` is positive.
- Quoted as a percentage, "the inflation" means **(`F` − 1) × 100 %**. At the standard recipe
  `F` = 1.257, i.e. **+25.7 %**.

```math
F = 1 - \frac{-0.0184}{0.0716} = 1.257
  with Kiendler C's numbers: a 1.8 % leftover on a band that is 7.2 % tall inflates the ratio by 25.7 %.
```

⚠ **Earlier drafts of this document had no symbol for `F`** and called it *the inflation factor*, *the
inflation*, and *inflation of the index* in three different places. If you are comparing against an
older copy, those are all this one number.

#### The same number wears three other hats

`F` − 1 = |`r_Q`| / `B_Q` is not a new invention, and recognising where else it appears is the fastest
route to understanding what it is:

| where it appears | as what | reference |
|---|---|---|
| here | the **inflation** of a single reading | this chapter |
| *From Spectrum to Verdict* §5.7 | the **dilution sensitivity** $d \ln M / d \ln c$ — how much the index moves when concentration does | already derived there, under a different name |
| chapter 6 of this document | the **intercept** of a straight line, $k = -M_{\infty} \cdot r_{Q}$ | how we measure it |

**One quantity, three faces: an inflation, a dilution slope, and an intercept.** They are the same
`r_Q`/`B_Q` seen from three directions, and each is measurable in a different way — which is why the
argument can be checked rather than believed.

![**Figure 5** — The same residual as a vertical gap in the spectrum, as an intercept in the fit, and as an inflation of the verdict. Chapter 6 measures the middle one because it is the only one that needs no assumption about concentration.](figures/pedestal_faces.svg)

**If one thing in this document is worth carrying away, it is Figure 5.** The middle panel is the
one chapter 6 measures — not because it is the most intuitive, but because it is the only one of the
three that can be read off the data **without knowing the concentration**.

#### ⇒ The sign ledger

Three sign inversions happen in a row here, and they are the easiest thing in the document to get
backwards. In order:

| | |
|---|---|
| 1 | The pedestal is **convex**, so the chord through the anchors runs **above** it at the Q band |
| 2 | Subtracting that chord removes too much ⇒ `r_Q` is **negative** (−0.0184 A) |
| 3 | So `B_Q` reads **too small** — the denominator is understated |
| 4 | A too-small denominator makes the ratio **too big** ⇒ `F` > 1, the index reads **high** |
| 5 | The correction subtracts a negative number, i.e. **adds** |`r_Q`| back to `B_Q` |
| 6 | The denominator grows ⇒ the corrected index comes out **lower**: 15.91 → 12.66 |

**The correction always lowers the number.** If a corrected value comes out *above* its shipped one,
something has gone wrong.

## 6 · Measuring `r_Q` — a test with no free parameters

### ⭐ First: measuring `r_Q` and applying it are two different jobs

Confusing these two is the single most common misreading of this document, so it is worth separating
them before any algebra:

| | **measuring `r_Q`** | **applying the correction** |
|---|---|---|
| what it is | a **calibration**, done once per rig state | one subtraction, on **every** run |
| what it needs | one oil, at **two or more genuinely different concentrations** | nothing but `B_Q` and the stored `r_Q` |
| how often | after every mechanical change to the instrument (ch. 9) | every measurement |
| which oils it works on | only those prepared at more than one strength | **any oil, any sample** |

**The correction applies to every oil.** Chapter 7 corrects the brown oil exactly as it does the
greens. What some oils cannot do is *contribute to measuring* the constant — and that is a statement
about how they happened to be prepared, not about what they are. This chapter is entirely about the
first column.

### Eliminating the concentration

We now need `r_Q` from data. The trick is to avoid needing to know the concentration at all — which
matters, because the session that produced this data proved the concentration was not reliably known.

Return to chapter 5's two measured quantities and eliminate `c`:

```math
B_{Soret} = M_{\infty} \cdot B_{Q} + \Big( r_{Soret} - M_{\infty} \cdot r_{Q} \Big)
  read: a straight line, y = slope*x + intercept. The concentration has vanished — it moves points
  ALONG the line, never off it. The bracket is the intercept, and it is where r_Q hides.
```

That is the equation of a **straight line** relating two things we measure directly. Vary the
concentration however sloppily you like: every run must fall on it.

**And here is the test.** If there were no leftover at all — a perfect baseline — then both `r` terms
are zero, the bracket vanishes, and **the line passes through the origin.** That makes intuitive
sense: with no pedestal left, when one band's pigment signal is zero so is the other's.

So: plot `B_Soret` against `B_Q`, one point per run, and look at where the line crosses — that is
**Figure 7**, two subsections below. The intercept is the leftover. **No fitted concentration, no
assumed recipe, no free parameters.**

#### ⭐ Which of the fit's three numbers is `r_Q` — and which two it is not

A straight-line fit returns two numbers, and the quantity this document is about is **neither of
them** — it is a third, computed from both. Getting this backwards makes the next four pages
unreadable, so:

![**Figure 6** — One regression over Kiendler's ten runs, and the three numbers read off it: the slope is dB_Soret/dB_Q, the ratio the pigment obeys; the intercept k is what the fit returns; r_Q is the x-intercept — the only one of the three that lies outside the data.](figures/pedestal_anatomy.svg)

| | what it is | Kiendler |
|---|---|---|
| **slope** | $dB_{Soret}/dB_Q = e_{Soret}/e_Q$ — **the ratio the pigment obeys** as concentration changes. Additive offsets in either band cancel from a slope, so this is pedestal-free **without needing `r_Q` at all**: it is the *target* quantity $M_{\infty}$, estimated from the ensemble | **12.450 ± 0.874** |
| **intercept** `k` | what the regression literally returns: the height of the line at $B_Q = 0$ | **+0.2287 ± 0.0516 A** |
| **x-intercept** | ⇒ **`r_Q` = −`k` / $M_{\infty}$** — where the line crosses $B_{Soret} = 0$ | **−0.0184 ± 0.0043 A** |

⚠ **`r_Q` is not the slope.** It is the **x-intercept** — the place on the horizontal axis where the
line says the Q band still reads something after the pigment has gone. That is exactly the claim the
correction rests on, stated geometrically: *drive the pigment to zero and `B_Q` does not arrive at
zero, it arrives at −0.0184 A.*

And that crossing sits at a **negative `B_Q`** — outside any data, off the left edge of a plot drawn
on the measured range. It is the one of the three quantities that can never be seen directly. Both
**Figures 6 and 7** therefore extend the x-axis into the negative region on purpose, so the crossing
is visible rather than implied.

⚠ **All three numbers are one fit over Kiendler's ten runs — not three measurements.** Figure 6
draws a single regression; the slope, the intercept arrow and the X marker are three things read
off it. In particular the slope is an **ensemble** parameter, not a corrected reading of any one
run: chapter 7's per-run arithmetic estimates the same target one measurement at a time, and
Kiendler's ten runs give values from 11.83 to 12.99 around it. **Measuring `r_Q` and applying it
stay two different jobs** — the slope belongs to the first.

**Why `r_Q` and not `k` is the quantity carried forward.** `k` is in absorbance units on the *Soret*
axis and mixes both bands' leftovers together; `r_Q` is the leftover in the *Q* band, in the units
and at the position where the correction is applied. Dividing by the slope converts one to the other.

#### ⚠ What the intercept actually contains — and what is assumed away

Read the bracket again. It is **not** simply $-M_{\infty} \cdot r_{Q}$; it is

```math
k = r_{Soret} - M_{\infty} \cdot r_{Q}
  read: BOTH bands' leftovers land in the SAME intercept. The fit returns their combination and
  cannot see them separately — no amount of extra data at more concentrations will split them.
```

This is a structural limit, not a precision problem. Both leftovers are concentration-independent,
so both move the line vertically and **only their combination is observable.** Converting `k` into
`r_Q` therefore requires *deciding* that all of it belongs to the Q band:

```math
r_{Q} = \frac{r_{Soret} - k}{M_{\infty}} \qquad\qquad r_{Q} = - \frac{k}{M_{\infty}}
  read: LEFT is what the fit actually determines. RIGHT is what this document uses everywhere. The
  step between them is the substitution r_Soret := 0 — a choice, not a result.
```

**That substitution is assumption A2** (ch. 10), and it is *not measured*. Its justification is the
16× asymmetry of §5: the same absolute leftover is 16 times more damaging in the small Q band than in
the big Soret one, so charging the whole intercept to Q is the conservative reading — it attributes
the effect where it does the damage. **But if `r_Soret` is not in fact zero, `r_Q` is wrong by
`r_Soret`/$M_{\infty}$**, and nothing in this chapter would reveal it.

![**Figure 7** — The straight-line test, on all three oils. Each line crosses B_Soret = 0 at its own r_Q, marked with an X in the shaded region — that crossing is r_Q, and it lies outside the data. The brown oil's line is dashed because its six runs share one concentration: it is drawn to show where the oil sits, not as a result.](figures/pedestal_line.svg)

**Figure 7** is fitted at run level, so the intercept carries an honest standard error:

| oil | runs | slope = $M_{\infty}$ | **intercept** *k* | *t* | ⇒ $r_Q = -k / M_{\infty}$ | 95 % CI on `r_Q` |
|---|---|---|---|---|---|---|
| **Kiendler** | 10 | 12.450 ± 0.874 | **+0.2287 ± 0.0516** | **4.43** | **−0.0184 ± 0.0043 A** | −0.0283 … −0.0085 |
| **Steirerkraft** | 12 | 11.181 ± 4.189 | +0.3078 ± 0.2953 | 1.04 | −0.0275 ± 0.0284 A | −0.0908 … **+0.0358** |
| *S-Budget* ⚠ | *6* | *7.884 ± 2.697* | *+0.2292 ± 0.2719* | *0.84* | *−0.0291 ± 0.0359 A* | *−0.1288 … **+0.0706*** |

⚠ **The S-Budget row is shown in italics because it is not a result.** All six of its runs are one
fill re-seated, so the regression has no dilution spread to work with — the numbers are what the
arithmetic returns, not what the oil says. They are printed rather than dashed out because *"cannot
be fitted"* is a statement about what a fit would be **worth**, not about whether one can be
computed, and the error bars say that better than a dash does. **Only the Kiendler row is carried
forward.**

**Reading the table.**

- The intercept is **not zero**, at 4.4 standard errors for Kiendler. The baseline leaves something
  behind, and the amount is what chapter 4 predicted in sign.
- The **slope** estimates the pedestal-free index $M_{\infty}$: ≈ 12.5 and 11.2 for the two greens,
  **7.9 for the brown**. That last gap is not a defect of the brown fit — it is the measurement the whole
  metric exists to make, and it is why the three oils are **fitted separately and never pooled.** One
  line through all the points would return a meaningless intermediate slope.
- **Steirerkraft's fit proves nothing on its own** (*t* = 1.04). Its `B_Q` values span only
  0.0652–0.0751 — **14.2 % of the mean against Kiendler's 48 %**, too short a lever to locate an
  intercept — and its 95 % interval on `r_Q` **contains zero**, as does S-Budget's. It is quoted
  because its point estimate independently agrees, not because it is significant. Chapter 10's A1
  weighs how little that is worth.
- **The brown oil cannot contribute at all.** Its six points share one true x-value, and you cannot
  locate a distant intercept from points that do not spread. **This is not a statement about brown
  oil** — see below.

> **⇒ THE SHARED `r_Q` IS KIENDLER'S.**
>
> Every corrected number in this document — including both the Steirerkraft and the brown-oil ones —
> is computed with **`r_Q` = −0.0184 A, the Kiendler fit**. It is the only one of the three with a
> lever arm long enough to mean anything, and `diagnostics/pedestal_correction.py` takes it
> literally: `shared = residual["Kiendler"]`.
>
> **This is only legitimate if `r_Q` is a property of the instrument rather than of the oil** — see
> the next box, and A1 in chapter 10.

### ⭐⭐ `r_Q` is claimed to be a property of the **instrument**, not of the **oil**

This is the load-bearing claim of the entire document, and everything else is downstream of it.

> **The claim.** `r_Q` is set by where the anchors sit and how the pedestal curves between them —
> **a property of the baseline chord and the optics.** It is therefore **one number per rig state,
> shared by every sample measured in that state**, and it does *not* belong to the oil.

**Why it has to be that.** `r_Q` is measured on one oil at several strengths, and then applied to
oils that were never part of that measurement — including the brown one, which is the class that
fixes the threshold. If `r_Q` were a property of the *pigment*, that transfer would be illegitimate
and the correction would collapse into "each oil needs its own calibration", which no field
instrument can deliver. **The correction is only worth having if the constant is shared.**

**What the evidence for it actually is.**

| oil | `r_Q` | worth |
|---|---|---|
| Kiendler | −0.0184 ± 0.0043 | the only real measurement (*t* = 4.4) |
| Steirerkraft | −0.0275 ± 0.0284 | agrees — but its interval spans −0.09 … +0.04 |
| S-Budget *(brown)* | *−0.0291 ± 0.0359* | *not a measurement at all* |

The three agree. ⚠ **But two of the three error bars are wide enough to agree with almost anything**,
so what the table shows is *absence of contradiction*, not confirmation. **The shared-`r_Q`
assumption is supported by one oil.**

**And it is not a cosmetic choice.** Correcting each green oil with its own `r_Q` instead of the
shared one changes the answer to the question the instrument exists to answer:

| Kiendler vs Steirerkraft, after correction | |
|---|---|
| with the **shared** `r_Q` | **+0.9 %** — the two greens are alike |
| with **each oil's own** `r_Q` | **+11.4 %** — they are clearly different oils |

⇒ **The ranking survives only under the shared assumption.** Chapter 10 raises this as A1 and
chapter 12 argues the case against it.

#### ⚠ Caveats — three reasons this cannot yet be treated as settled

| caveat | what it says |
|---|---|
| **C1 — one oil** | Only Kiendler has a lever arm. Steirerkraft's interval contains zero; the brown oil has **no usable `r_Q` at all**, and it is the class that sets the threshold `T`. |
| **C2 — the mechanism is open** | §4.1 (**Figure 3**) accounts for at most 17 % of `r_Q`'s size from the pedestal's own curvature (Appendix D.3) and perhaps 32 % from the far anchor; **≈ 51 % is unaccounted.** With no mechanism, oil-independence cannot be argued from physics — only measured. |
| **C3 — the leading suspect is pigment-dependent** | The far anchor is the strongest candidate for the missing part, and §16.12.12 measured the 620–630 rise to be green-pigment Qy absorption at 5.1 σ. **A pigment-driven term is by definition oil-dependent** — so C2's gap is not neutral, it points the wrong way. |

**None of this makes the correction wrong.** It makes it *unverified in the one respect that matters*
— which is precisely what chapter 13's **T1** is designed to settle, and why this document recommends
recording both numbers rather than shipping the corrected one.

### ⭐ The lever arm — why the three oils differ so much

`r_Q` is an **extrapolation back to `B_Q` = 0**. Everything therefore depends on how far apart the
points are along the x-axis: a short lever locates a distant intercept badly. Here is the actual
spread, and it explains all three rows of the table above at once:

| oil | preparations | `B_Q` range | **span, as % of mean** | *t* on the intercept |
|---|---|---|---|---|
| **Kiendler** | **3**, one accidentally over-dilute | 0.0445 – 0.0725 | **48.3 %** | **4.43** |
| Steirerkraft | 2 fills | 0.0652 – 0.0751 | 14.2 % | 1.04 |
| **S-Budget** *(brown)* | **1 fill, re-seated 6×** | 0.0968 – 0.1050 | 8.0 % | *0.84 — no lever at all* |

**The point about S-Budget is not that its span is small — it is that none of the span is signal.**
Re-seating a cuvette moves the optics, not the concentration, so all six points are draws from the
*same* true `B_Q`. Compare its 8.0 % against Kiendler set A *on its own*, which scatters 12.7 % within
one preparation: its whole pooled spread is smaller than one set's noise.

And noise in x is worse than no spread at all. It supplies no leverage, and it biases the slope
**toward zero** — the regression-attenuation effect that chapter 12 raises under *"the two axes share
a spectrum"*. A fit through it would not be imprecise; it would be wrong in a known direction.

**⇒ What S-Budget lacks is two strengths, not something about being brown.** Prepare it at two and it
fits like any other oil — which is why chapter 13's T1 puts it first.

**Where Kiendler's leverage came from — and the irony in it.** Its 48.3 % span is wide enough to fit
*only because one of its three preparations was accidentally too dilute*. The botched sample is what
made the measurement possible.

<!--PAGEBREAK-->

## 7 · The correction, worked end to end

Start from chapter 5's result and solve for the quantity we actually want:

```math
M_{\infty} = \frac{M}{1 - \frac{r_{Q}}{B_{Q}}} = \frac{B_{Soret}}{B_{Q} - r_{Q}}
  read: divide out the inflation factor F — which is the same as putting the leftover back first.
  with numbers: 15.91 / 1.257 = 12.66, and 1.1397 / (0.0716 + 0.0184) = 12.66. The same thing twice.
```

**It collapses to a single subtraction.** `B_Q − r_Q` is nothing other than the pigment part of the Q
band with the baseline's over-subtraction put back. Then divide as before.

#### ⭐ What is in the correction, and what is only motivation

Three chapters of physics precede this one, so it is worth listing exactly what the corrected number
is computed from:

| input | what it is | contains λ? | contains scattering? |
|---|---|---|---|
| `B_Soret` | a measured band mean above the chord | no | no |
| `B_Q` | a measured band mean above the chord | no | no |
| `r_Q` | **one fitted constant** — chapter 6's x-intercept, in absorbance | no | no |

⚠ **Neither wavelength nor any scattering law appears in the arithmetic.** There is no exponent `n`,
no particle size, no Rayleigh or Mie term, no λ anywhere. **Delete chapters 3 and 4 entirely and this
chapter still computes the same numbers.**

**Where λ *does* enter — both of them upstream, in the shipped metric:**

1. **The window definitions** (440–460, 520–540, 560–580, 620–630). λ enters as a *choice of windows*,
   not as a variable in an equation. This is why **`r_Q` belongs to its anchor** (§1): move the far
   window from 600–630 to 620–630 and the constant moves from −0.0246 to −0.0184.
2. **The chord.** The baseline line is fitted across the two anchor windows and read off at the Q
   band, and 570 nm lies **0.421** of the way from the near anchor's centroid (530) to the far one's
   (625). That is real λ-dependence — and it is **step 4**, before any correction exists. *(Measured
   on Kiendler C run 1 the shipped least-squares chord lands at an effective weight of 0.4208, so the
   two-centroid reading is exact to three decimals.)*

**Where scattering enters: nowhere that is computed.** Appendix D does put a λ⁻ⁿ pedestal into a
formula, but that formula is a **test of the story, not a step of the calculation** — and the story
failed it, accounting for ≤ 17 % of `r_Q`'s size. **Appendix D is the only place in this document
where scattering is argued rather than merely pointed at**, precisely because nothing here depends on
it.

**⇒ Why this matters beyond bookkeeping.** If `r_Q` were $f(\lambda, n, \text{turbidity})$ one could
read the formula and see whether the pigment appears in it. It is not — it is a single empirically
fitted number with no derivation — so **whether `r_Q` belongs to the instrument or to the oil is not
inspectable, only measurable.** That is caveat C2 in §6, and it is why chapter 13's T1 is an
experiment rather than a calculation. It also makes chapter 9 unsurprising: a constant fitted to one
optical configuration has no reason to survive a rebuild, and it did not.

### Worked example — Kiendler set A, the over-dilute one

| step | | |
|---|---|---|
| 1 | read the baselined Soret band | `B_Soret` = 0.8366 A |
| 2 | read the baselined Q band | `B_Q` = 0.0490 A |
| 3 | the uncorrected index | 0.8366 / 0.0490 = **17.12** ← *`M` shipped* |
| 4 | put the leftover back | `B_Q − r_Q` = 0.0490 − (−0.0184) = **0.0674** A |
| 5 | divide again | 0.8366 / 0.0674 = **12.45** ← *`M∞` corrected* |
| 6 | the inflation factor, from `r_Q` and `B_Q` alone (§5.1) | `F` = 1 − (−0.0184 / 0.0490) = **1.375**, i.e. **+37.5 %** |
| 7 | **divide the inflation out of the shipped number** | `M / F` = 17.12 / 1.375 = **12.45** ✓ *the same answer as step 5* |

Step 4 is the whole correction. Everything else was already being computed.

**Steps 4–5 and steps 6–7 are two routes to one number** — subtract the leftover then divide, or
divide out the inflation it causes. They must agree, and that agreement is the arithmetic check on
every row of the table below: **`M` corrected = `M` shipped / `F`**, with `F` fixed by `B_Q` alone
once `r_Q` is known. No second measurement enters between the two `M` columns.

### The same, for every set on record

| set | `B_Q` | inflation (`F` − 1) | M shipped | **M corrected** |
|---|---|---|---|---|
| **Kiendler A** *(over-dilute)* | 0.0490 | **+37.5 %** | 17.115 | **12.45** |
| Kiendler B | 0.0715 | +25.7 % | 15.452 | **12.29** |
| Kiendler C | 0.0716 | +25.7 % | 15.911 | **12.66** |
| Steirerkraft B | 0.0678 | +27.1 % | 15.619 | 12.29 |
| Steirerkraft C | 0.0731 | +25.1 % | 15.499 | 12.39 |
| S-Budget D *(brown)* | 0.1008 | +18.2 % | 10.160 | **8.59** |

**The three Kiendler preparations spread 10.3 % before and 3.0 % after.** That is the result the
correction rests on. **Figure 8** shows why the over-dilute one moved furthest: the inflation is
`|r_Q|` measured against the pigment signal, so it grows as that signal shrinks.

**What Figure 8's vertical axis is.** It is `F` − 1 expressed as a percentage — the same quantity
as the *inflation* column of the table above, and defined once in §5.1:

```math
F - 1 = -\frac{r_{Q}}{B_{Q}} = \frac{|r_{Q}|}{B_{Q}} = \frac{M - M_{\infty}}{M_{\infty}}
  read: three ways to say one thing — the leftover measured against the pigment signal; and,
  equivalently, by how much the shipped index exceeds the corrected one, relative to the corrected
  one. Kiendler A: 0.0184/0.0490 = 0.375, and (17.115 - 12.445)/12.445 = 0.375. The same number.
```

The curve is that expression with `r_Q` held at the shared −0.0184 A and `B_Q` running along the
x-axis; each set sits on the curve at its own `B_Q`. **Nothing in the figure is fitted** — it is
one constant divided by a measured band height.

#### ⚠ That 3.0 % is **in-sample** — and partly a construction

`r_Q` was fitted on these very ten runs, and the correction is algebraically a **projection onto the
fitted line.** For a point lying exactly on it the two operations are the same thing:

```math
\frac{B_{Soret}}{B_{Q} - r_{Q}} = \frac{M_{\infty} B_{Q} + k}{B_{Q} + k / M_{\infty}} = M_{\infty}
  read: substitute r_Q = -k/M_inf and the correction returns the SLOPE, identically, for every B_Q
  on the line. Checked numerically: B_Q = 0.045, 0.072 and 0.101 all give 12.449689.
```

**So what survives the correction is precisely each set's residual off the regression** — and the
regression was chosen to minimise exactly that. The 3.0 % is therefore closer to a restatement of
*"a straight line fits these ten points well"* (R² = 0.962) than to independent evidence that the
correction transfers.

This does not make the number wrong; it makes it **the wrong kind of evidence to lean on.** It shows
the correction is *self-consistent*, which it must be. ⇒ **The test that can actually fail is chapter
9's**, on pairs `r_Q` was never fitted to — and it passed once and failed twice.

![**Figure 8** — The vertical axis is `F` − 1 = |`r_Q`| / `B_Q`, in percent, drawn with the shared `r_Q` = −0.0184 A; the six sets are placed on it by their own `B_Q`. A fixed leftover is a growing fraction of a shrinking `B_Q`, which is why the over-dilute preparation is the one that misreads worst.](figures/pedestal_inflation.svg)

### Why one cannot simply concentrate the problem away

The inflation `F` − 1 is `|r_Q| / B_Q`, so working at higher concentration shrinks it. How much higher?

| target inflation (`F` − 1) | needs `B_Q` ≥ | relative to today's 0.0716 |
|---|---|---|
| 30 % | 0.061 | 0.9× — *this is where we are* |
| 20 % | 0.092 | 1.3× |
| 10 % | 0.184 | **2.6×** |
| 5 % | 0.368 | **5.1×** |

**There is no room.** At today's recipe the 440–447 nm bins already read 2.0–2.6 DN against a
reference near 88 — they are dark, and previous work established they are not measurements. Working
1.3× stronger pushes more of the Soret band into that floor; 2.6× is out of the question.

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

**A prediction that could have failed — and what it is worth.** Chapter 4 did not *fit* the sign of
`r_Q`; it **predicted** it, from a convex pedestal and the Q band lying between the two anchors.
Measured, `r_Q` = −0.0184. Had it come out positive the model would have been dead.

⚠ **This is worth much less than it first appears, and Appendix D.2 works out exactly how much.** The
prediction was of a *sign*, and convexity is shared by every candidate background the project has
considered — including a far anchor reading too high, which drives `r_Q` negative just the same. A
prediction that the whole field of rivals satisfies discriminates between none of them. **What
survives is that the residual is real and its sign is understood; what does not survive is any claim
about its cause.**

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
residual's sign was predicted before it was measured (⚠ Appendix D.2 prices that prediction).

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

| pair | rig state | span | uncorrected *s* | **corrected *s*** | |
|---|---|---|---|---|---|
| green `oilK → oilL` | pre-rebuild | 1.50× | −0.01 | **+0.20** | ✗ worse |
| brown `oilN → oilM` | pre-rebuild | 1.50× | +0.09 | **+0.20** | ✗ worse |
| green `0729B → 0729C` | **post-rebuild** | 1.17× | **−0.05** | **+0.05** | ⚠ **no better** |

### ⛔ On this anchor the good row is GONE — and that is the important finding

**On the 600–630 anchor this test was the strongest single result in the document**: the correction took
the post-rebuild pair's dilution slope from −0.12 to −0.00. **On the 620–630 anchor it takes it from −0.05
to +0.05** — the same magnitude, opposite sign. **The correction no longer improves invariance; it
overshoots.**

The reason is not mysterious, and it is not a failure of the correction. **The anchor move already did the
work.** Moving the far window to 620–630 cut the dilution slope from −0.12 to −0.05 on its own
(`SPEC_capture_quality.md` §16.20.2), leaving the pedestal correction little to fix — and `r_Q`, fitted on
Kiendler, then carries it past zero.

⇒ **On the shipped anchor the case for the pedestal correction is materially weaker than it was on the old
one.** That is the honest reading, and it is exactly the trade §16.20.4a described: the two are alternative
routes to the same fix, and applying both can overcorrect.

### What the two bad rows are worth

**On both pre-rebuild pairs the correction makes invariance markedly worse** — and those pairs are
the archive's principal evidence that the shipped metric is dilution-invariant at all. A correction
that destroys that is not a small matter.

### The reading that fits all three rows

**`r_Q` transfers between oils, but not across a rig rebuild.** That is physically sensible: the
residual is a property of the instrument rather than of the sample, and the 2026-07-29 rebuild changed
the instrument.

⭐ **§4.1 upgrades this from "sensible" to "expected".** If most of `r_Q` comes from a corrupted far
anchor — a lamp spectrum and an optical path — then it *must* move when the rig is rebuilt, and it
*must* be shared between oils measured on the same rig. **That is exactly the pattern chapter 9
found**, and it was found before the mechanism was understood. Three consequences follow, and they are
now part of the proposal:

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
chapter 9 has now split it in two.* ⚠ **And on the shipped anchor its best supporting evidence has
evaporated** — see item 1 below.

`r_Q` describes the curvature of a particular sample's pedestal, and pedestals come from suspended
droplets, which differ between preparations. If `r_Q` varied sample to sample, subtracting one fixed
number would not be a correction but a new error.

#### ⚠ What the two-oil agreement is worth — considerably less than it looks

The two fitted values are −0.0184 and −0.0275, **49 % apart**, and on the older 600–630 anchor they were
16 % apart — an agreement that looked like confirmation and was not. On this anchor it does not even look
like one:

| | Kiendler | Steirerkraft |
|---|---|---|
| `B_Q` span, as % of its mean | **48 %** | 14 % |
| `r_Q` | −0.0184 ± 0.0043 | −0.0275 ± 0.0284 |
| 95 % interval | −0.0269 … −0.0099 | **−0.0832 … +0.0282** |

**Steirerkraft's interval contains zero.** That oil on its own cannot establish that a residual exists
at all, let alone that it matches. And the formal comparison — difference +0.0091 ± 0.0287, *t* = 0.32 —
is close to vacuous: **the smallest difference it could detect is about 0.057, which is over three times
`r_Q` itself. It would miss a tripling.**

The cause is the **lever arm**. `r_Q` is an extrapolation back to `B_Q` = 0, and Steirerkraft's `B_Q`
span is barely a third of Kiendler's. Same rig, same protocol, same operator — only the concentration
range differs, and that alone makes the interval five times wider.

⚠ **A tempting shortcut that does not work, recorded so nobody re-derives it.** One can instead ask
*"what `r_Q` would make Steirerkraft's two fills read the same?"* That gives **−0.0242 — a striking
2 % from Kiendler's value.** Bootstrapped over its runs, its 95 % interval is **−0.114 … +0.010 —
wider than the regression it was meant to improve on.** The apparent precision was entirely an
artefact of quoting a point estimate without an error bar.

#### What the evidence actually is, in descending order of weight

1. ⛔ **The consequence test (chapter 9) no longer supports it on this anchor.** On 600–630 it was the
   strongest evidence there was — Kiendler's `r_Q` drove Steirerkraft's dilution slope from −0.12 to
   −0.00 and its two fills from a −1.85 % gap to +0.02 %. **On 620–630 the slope goes −0.05 → +0.05 and
   the fill gap −0.77 % → +0.81 %**: no improvement in either, only a sign flip. The anchor move had
   already removed most of what the correction used to fix.
2. **Reproducibility within one oil.** Kiendler's two independent preparation contrasts give
   **−0.0232** and **−0.0155**, bracketing the pooled −0.0184. So `r_Q` still reproduces across
   independent preparations of one oil — this is now the **strongest** evidence left, item 1 having
   gone.
3. **The two-oil point-estimate agreement.** Real, and nearly weightless, for the reasons above.

#### Should `r_Q` be a constant at all, or should it scale with turbidity?

A1 assumes `r_Q` is a fixed number. But the original mechanism argued otherwise: `r_Q` is the
*curvature of the pedestal*, and on the Appendix D reading a cloudier sample would bend it more. On
that reading `r_Q` should be **proportional to turbidity**, not constant — and the sets differ enormously in
turbidity, Kiendler A at 0.0378 A against Kiendler C at 0.1018 A, a factor of 2.7 given one `r_Q`.

The two models are distinguishable on data already in hand. Writing τ for the 520–540 nm turbidity:

```math
B_{Soret} = M_{\infty} \cdot B_{Q} + k \qquad \op{versus} \qquad B_{Soret} = M_{\infty} \cdot B_{Q} - M_{\infty} \cdot \rho \cdot \tau
  left: a constant residual, so a constant intercept. right: a residual proportional to turbidity, so no intercept at all.
```

| oil | **constant `r_Q`** | `r_Q` ∝ turbidity |
|---|---|---|
| **Kiendler** | R² = **0.9620**, intercept *t* = 4.43 | R² = 0.9281, τ coefficient **−1.97** |
| **Steirerkraft** | R² = 0.4160 | R² = **0.4837**, τ coefficient +1.57 |

⚠ **On this anchor the result is weaker than it was on 600–630, and it is no longer unanimous.** The
constant model wins clearly on **Kiendler** — and the proportional one there wants a *negative* τ
coefficient, implying a **positive** `r_Q`, contradicting both chapter 4's sign prediction and the direct
measurement. But on **Steirerkraft the proportional model now fits slightly better** (R² 0.4837 against
0.4160), where on the old anchor the constant model won both.

⇒ **The honest statement is that the constant form is supported by the oil with a real lever and is not
distinguishable on the oil without one.** Steirerkraft's fit explains under half the variance either way
(R² ≈ 0.4), so it is not evidence for the proportional model so much as an absence of evidence for
anything.

⚠ **This is a check, not a proof, and it has a real weakness.** τ is measured as the raw 520–540 nm
absorbance, which is not pure turbidity — assumption A6 concedes the anchors carry some pigment. So τ
is strongly correlated with `B_Q` across these sets, and two collinear regressors cannot be cleanly
separated on six sets. What can fairly be said is that **the data gives no encouragement to the
turbidity-scaled model**, and that A1's constant form is the better-supported of the two on the
evidence available.

#### ⇒ The verdict splits

- **Across OILS, within one rig state: supported** — on items 1 and 2, not on item 3.
- **Across RIG STATES: refuted.** The same constant applied to pre-rebuild pairs makes invariance
  *worse*, −0.01 → +0.20 and +0.09 → +0.20.

**⇒ `r_Q` is a per-rig-state calibration constant.** It must be re-measured after any mechanical
change and never applied retroactively. Chapter 12 shows the assumption still changing an answer
*within* a rig state, so "supported" is not "settled".

**A2 — `r_Soret` is negligible.** The leftover at the Soret band is treated as zero. Justification:
the Soret band lies outside the anchors and is 13× taller, so the same leftover is 13× less
important. **Not separately measured** — the fit cannot distinguish `r_Soret` from
$M_{\infty} \cdot r_{Q}$, because only the combination appears in the intercept. If `r_Soret` is not
zero, the quoted `r_Q` absorbs it and is biased.

**A3 — the pedestal is convex.** Chapter 4's sign prediction depends on it. Every candidate
background on record is convex and the measured sign agrees; if some sample's pedestal were concave,
the correction would push the wrong way. ⚠ **This assumption does less work than it looks** (Appendix
D.2): because *every* rival is convex, the agreement identifies no mechanism — and the sign
prediction's remaining content is the **window geometry**, a design choice rather than physics. The
correction does not depend on A3 at all — `r_Q` is fitted — but the *explanation* does, and the
explanation is the weaker part.

**A4 — Beer-Lambert holds in both bands.** That absorbance is proportional to concentration, with no
saturation. At the Soret band the transmitted signal is already at ~6.5 % and the blue edge is dark,
so this is **weakest exactly where the numerator lives**. Stray light in a saturated band compresses
absorbance, which would appear as a concentration-dependent error of its own.

> ### ⭐⭐ A4 FAILS, AND IT ACCOUNTS FOR 28 % OF `r_Q` *(measured 2026-08-04)*
>
> **This paragraph predicted the mechanism and never measured it. It has now been measured, and A4
> moves from "assumed" to "known to fail, by this much".**
>
> §7 of this document already records that **the 440–447 nm bins read 2.0–2.6 DN against a reference
> near 88** and *"are not measurements"*. **Those bins are inside the Soret window 440–460** — so about
> a third of this metric's numerator window is contributed by them.
>
> Delete them and re-run chapter 6's straight-line test:
>
> | Soret window | intercept `k` | ***t*(k)** | `r_Q` |
> |---|---|---|---|
> | **440–460** *(shipped)* | 0.2294 | **4.43** | **−0.0184** |
> | 444–460 | 0.1620 | 3.45 | −0.0149 |
> | ⭐ **448–460** | **0.1214** | **2.92** | **−0.0133** |
> | 450–462 | 0.0962 | 2.66 | −0.0126 |
>
> ⇒ **47 % of the intercept and 28 % of `r_Q` come from eight nanometres of dead bins.**
>
> **Why.** A camera never reads true zero — dark offset and stray light add counts, so `S` reads high
> and **`A` reads low**. The same +1 count costs **0.17 A** at S = 2 and 0.014 A at S = 30. A stronger
> preparation is darker, so the junk is a larger *fraction* of it, so it is under-read *more*: at
> 445 nm a dilute fill is under-read by 0.11 A and a concentrated one by 0.15 A. **`B_Soret` therefore
> grows more slowly than concentration** while `B_Q` — at 560–580, where counts are healthy — grows
> honestly. Chapter 6's points **bend downward** at the strong end, and a straight line fitted to a
> downward-bending curve **must cross the axis above zero**. That crossing is `k`.
>
> **Not a rescaling artifact.** Trimming shrinks `B_Soret` by ×0.674. Pure rescaling predicts slope
> 8.383 and intercept 0.1547; observed are **9.101** and **0.1214** — the intercept fell **21.5 %
> further** than rescaling explains, so the relationship itself changed.
>
> **⇒ Why no chapter found it.** §4.1 and §4.2 both hunted `r_Q` on the **denominator** side — the
> curvature of the background under the Q band (≤ 17 %) and the cleanliness of the red anchor (~32 %,
> refuted). Both ask *"what is wrong with the baseline near the green band?"* **This defect is in the
> blue band and it is a camera problem, not a baseline problem.** No examination of the baseline could
> have found it. ⚠ Not additive with §4.1's shares — those are on the 600–630 anchor.
>
> ⚠ **`r_Q` does not dissolve.** After trimming, *t* = 2.92 is still significant, so **~72 % survives**
> unexplained. This is a contributor, not the cause.
>
> **⇒ Two consequences.** Trimming the Soret window to **448–460** improves class separation
> (6.91 → 7.37), within-green separation (1.21 → 1.34) and dilution spread (10.3 % → 8.8 %) — modest
> but free, and `B_Soret` drops 1.03 → 0.69 so any threshold must be re-derived. And the capture-side
> fix matters more: a **DN guard** plus **dosing to a common optical density** makes every sample
> present the same `S`, so the compression becomes identical across oils instead of differential.
> Full working: `SPEC_metric_research.md` §7.13.

**A5 — one pigment species dominates each band.** The model has a single `e_Soret` and a single
`e_Q`. The oil actually contains protochlorophyll *and* its degradation product, and the whole point
of the verdict is that their proportion changes. The index is therefore already a mixture ratio; the
correction does not change that, but $M_{\infty}$ should be read as "the pedestal-free index", not as
a physical extinction ratio.

**A6 — the two anchor windows are quiet.** They are not, and this assumption has been **overtaken by
§4.1 — it is now the most interesting one in the list, not the dullest.**

The original argument was: the far anchor sits on the pigment's Qy flank, but *pigment* contamination
scales with concentration, so it cannot produce a concentration-independent intercept and is therefore
harmless. **That argument is still correct, and it is beside the point.** The far window also carries
two contaminations that are **not** pigment and do **not** scale with concentration:

⚠ **But §4.1 also shows the far window's contamination is mostly of the harmless, scaling kind** — the
620–630 rise is the pigment's own Qy flank at 5.1 σ. Only its **non-scaling** remainder can bias `r_Q`,
and that remainder is +0.0169 ± 0.0177 A: the right sign, a plausible size, and **not significantly
different from zero on six sets.**

| contaminant | scales with concentration? | can it produce an intercept? |
|---|---|---|
| the pigment's Qy flank | yes | **no** — the original argument holds |
| the **607 nm artifact** | no — it is an instrument feature | **yes** |
| the **lamp's red cliff** past 618 nm | no — it is the lamp's spectrum | **yes** |

**⇒ A6 fails as written — but §4.2 shows the failure does NOT explain `r_Q`.** Removing the
contamination entirely makes the residual larger, so the anchor's uncleanliness is a real defect of the
construction and *not* the source of the residual this document is about.

<!--PAGEBREAK-->

## 11 · What the correction buys, and what it costs

**Buys — the spread collapses.** Three preparations of one oil: 10.3 % → 3.0 %. ⚠ In-sample (§7):
the correction projects onto the line `r_Q` was fitted to, so this shows self-consistency, not
transfer.

**Buys — the number stops depending on preparation quality.** Today an unusually clear or unusually
cloudy sample shifts the verdict by ~10 % with nothing to warn the operator. That is the property
that makes a measurement **transferable between operators and sites** — which matters more for a
laboratory partner than precision does.

**Costs — the threshold must be re-derived.** Everything moves down: greens from 15.5–17.1 to ≈ 12.3–12.7,
brown from 10.2 to ≈ 8.6. ⚠ The shipped plugin **retains `T` = 10.6** on the corrected metric: it lands
inside the class corridor (8.77 … 11.61) and classifies every archived run correctly, but it was
**inherited from the older 600–630 scale, not derived on this one** — the corridor's own midpoint is 10.2
(`SPEC_capture_quality.md` §16.20.7).

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

The correction appears to bear on something independent: the operator's own visual judgement that the
Kiendler oil is slightly greener than the Steirerkraft one.

**⚠ On this anchor the argument INVERTS relative to the 600–630 version of this document, and that is
itself the point.** Using the shared `r_Q` the two oils come out nearly identical; using each oil's
**own** measured `r_Q` Kiendler pulls well ahead:

| | corrected with shared $r_{Q}$ | corrected with each oil's own $r_{Q}$ |
|---|---|---|
| Kiendler | 12.45 | 12.45 |
| Steirerkraft | 12.33 | **11.18** |
| S-Budget | 8.59 | **—** *no own `r_Q` exists — see below* |
| **Kiendler vs Steirerkraft** | **+0.9 %** | **+11.4 %** |

*(On the 600–630 anchor the same table read +3.9 % shared against +0.7 % own — the opposite way round.)*

**So on one reading the two green oils are indistinguishable and on the other Kiendler is markedly
greener, and which you get depends entirely on an assumption the data cannot settle** — Steirerkraft's
own `r_Q` is known only to ±0.028, an error bar wide enough to contain both. ⚠ **That the swing reverses
direction when the anchor moves is the strongest possible demonstration that this comparison is not
measuring the oils.**

**⇒ The correction must not be judged by whether it agrees with the eye. On this evidence, whether it
agrees with the eye is a free parameter — and one that changes sign with the choice of window.**

### ⚠ The brown oil is the one class where nothing has been tested

The dash in the table above is not a small print item, and an earlier draft of this document got it
wrong: it repeated the same number in both columns, which reads as *"the brown oil is insensitive to
the choice"* when it in fact means *"we cannot compute the comparison at all."* S-Budget exists at one
concentration, so it has no `r_Q` of its own to compare against the shared one (chapter 6 says why).

Line up what is known per oil, and the gap is stark:

| oil | own `r_Q`? | tested out-of-sample? | evidence that the shared `r_Q` applies to it |
|---|---|---|---|
| **Kiendler** | yes, *t* = 4.43 | it *is* the fit | — |
| **Steirerkraft** | yes, but *t* = 1.04 | ✓ chapter 9's post-rebuild pair | ⚠ **and it shows no gain** |
| **S-Budget** *(brown)* | **no** | **no** | **none** |

**And the brown oil is the class on the other side of the threshold.** The correction moves it by
18.2 %, on a constant that has never been checked against it, and any re-derived `T` is fixed by
exactly where the green and brown classes land. So the untested oil is load-bearing for the decision
the metric exists to make.

The one thing that can be said in its favour is indirect: `r_Q` is a property of the *pedestal*, not
of the pigment, and S-Budget's turbidity (0.1038 A at 520–540 nm) sits squarely inside the greens'
range (0.0981–0.1231). On the quantity that should drive `r_Q`, the brown oil looks like the oils the
constant was measured on. That is an argument for plausibility, **not evidence** — and it is the whole
of the case.

**⇒ T1 must include the brown oil at two strengths.** Until then the corrected brown number is an
extrapolation, and the threshold derived from it inherits that.

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

Five tests. **T0 has been done — chapter 9, and repeated 2026-08-04 on a brown oil (box above). T4 has been done — see below, and it closed negative. T1, T1b and T2 have not.**

> ### ⛔ Added 2026-08-04 — T0 has been repeated on a BROWN oil, and the correction failed it
>
> `SPEC_metric_research.md` §7.3 scored this correction against plain `M` on the **pre-rebuild
> archive** — data it was never fitted to — including **the only brown oil on disk that exists at two
> strengths** (oilN/oilM, 2 and 3 drops). Chapter 12's central complaint was that the brown class was
> wholly untested. It is no longer.
>
> | | green 2→3 drops | **brown 2→3 drops** | class *d* retained across the rebuild |
> |---|---|---|---|
> | `M` uncorrected | **−0.4 %** | **+4.9 %** | 19 % |
> | ⛔ **`M` + this correction** | **+8.3 %** | **+9.6 %** | **13 %** |
>
> **The correction made dilution invariance WORSE than doing nothing, on both classes** — and it
> retained the least separation of any candidate. An independent second pre-rebuild contrast (25 runs,
> `20260727`) agrees: uncorrected 3.15, corrected **2.84**.
>
> ⇒ **Chapter 7's 10.3 % → 3.0 % and chapter 11's "buys" are in-sample, and now demonstrably so
> rather than arguably so.** §7's ⚠ predicted exactly this; chapter 9 predicted it; this is the
> measurement.
>
> ⚠ Pre-rebuild runs carry ~3× the seating noise, so the *d* column has a low ceiling for every
> candidate. **The dilution columns are the durable result** — they are within-oil, so seating noise
> cancels.
>
> **⇒ This does not retract the correction; it settles its status.** `r_Q` is real (ch. 6) and its
> in-sample behaviour is exactly as described. What is now measured is that **it does not transfer** —
> which is what A1 always required and never had. The recommendation below stands and is strengthened:
> **record both numbers, do not change the shipped verdict.**

**T0 — carry `r_Q` onto a pair it was not fitted on. ✅ DONE (chapter 9), and it passed once and
failed twice. ⛔ REPEATED 2026-08-04 on a brown oil — see the box above; it failed again, and worse
than doing nothing.**
Within a rig state the correction did exactly what it promised; across a rebuild it did the opposite.
That result is what makes T1 worth doing and T1b necessary.

**T1 — measure `r_Q` on every oil in the campaign, and the brown oil first.** Each oil needs at least
two preparations of genuinely different strength, ideally spanning more than Steirerkraft's narrow
14 %. Then ask the only question that remains: **within one rig state, is `r_Q` one constant, or does
each sample have its own?** If the four values agree within their errors, A1 is supported well enough
to adopt. If they scatter, the correction is dead in this form. **This costs nothing beyond what the
campaign is already scheduled to do**, provided each oil is prepared at two strengths rather than one.

**The brown oil is the priority within T1**, because it is the only class with no `r_Q` of its own, and
because the threshold is set by where the brown class lands. ⚠ **The "no out-of-sample check" half of
this is now obsolete** — the box at the top of this chapter supplies one, and the correction failed it.
T1 is therefore no longer a test of whether the correction *might* transfer; it is the measurement of
**why it does not**.
It is also the cheapest of the four to fix: one extra fill at a different strength.

**T1b — re-measure `r_Q` after the next mechanical change, and check it moved.** Chapter 9 says it
should. If it does not move when the optics change, the whole physical story is wrong and the value
is fitting something else. This is a cheap and unusually sharp test, because it predicts a *change*
rather than a constancy — and a prediction of change is much harder to satisfy by accident.

**T2 — report both numbers in parallel.** Compute `M` and $M_{\infty}$ on every run and record both.
The corrected number changes no decision while it is only being recorded, and after a dozen samples
its behaviour is known rather than argued about.

**T3 — attack `r_Q` physically instead — but at the RIGHT target.** If `r_Q` can be driven toward zero
at source, no arithmetic correction is needed at all. **This is the better outcome.** But §4.1 changes
where to aim:

| route | attacks | effect on `r_Q` |
|---|---|---|
| ~~refit with the far window's contaminated stretches excluded~~ | the anchor's non-scaling part | ⛔ **DONE, §4.2 — it made `r_Q` WORSE.** The route is closed |
| 0.22 µm filtration, or a dissolving solvent | turbidity, ~17 % of it | real but modest — it cannot touch an instrument artifact |

**⇒ The filtration work is no longer the strongest lever on `r_Q`.** It remains worth doing for other
reasons, but the cheap, sharp move is to fix the far window — a change to the instrument and the
window definition, not to the sample. `SPEC_capture_quality.md` §16.12.11 B reached the same
conclusion from the other direction and is the place to do it.

**T4 — price the orthodox alternative, and find out whether the correction is needed at all.
✅ DONE 2026-08-04, and the answer is NO.**
Chapter 4 concludes that the entire problem is *curvature*; this document then corrects the
consequence rather than modelling the cause. The mainstream remedies do the opposite — a **curved
baseline** (polynomial, rubber-band, ALS/airPLS) or a **second-derivative** reading, which
annihilates a linear background exactly. **Appendix D.6** sets out both.

`SPEC_metric_research.md` §7.9 priced them, on the shipped windows with only the baseline changing:

| baseline | class *d* | dilution spread |
|---|---|---|
| **chord (shipped)** | **6.91** | 10.3 % |
| chord + `r_Q` | 9.61 | 3.0 % |
| convex hull | 2.15 | 16.6 % |
| polynomial 3 / 5 / 7 | 0.97 / 0.25 / 1.99 | 20.1 / 10.1 / 23.7 % |

⛔ **Every curved baseline collapses the class separation and three of four make dilution worse.** The
reason is structural, not a matter of tuning: **both principal bands are flanks** — the Soret's maximum
is at ~432 nm below the 440 nm edge, Qy's at ~625 with the window ending at 629.8. A smooth baseline
has no peak-free region to anchor on at *either* end, so it follows both flanks down. The convex hull
removes ~98 % of the Soret band.

⚠ The derivative half fared no better: a second-derivative Q-manifold ratio scored a **97 % dilution
spread** (`SPEC_metric_research.md` §7.7), because a *flank* has almost no curvature to differentiate.

⇒ **T4 is closed. The orthodox alternative is not affordable on this instrument**, and the reason it is
not is the same 30 nm of missing red range that blocks four other routes (§7.8). ⚠ My earlier
recommendation to run T4 "as soon as anyone has an afternoon" was right about the cost and wrong about
the prospect.

⛔ **One retraction belongs here, because it concerns this document's own chapter 6.** A first reading
of T4's output found the hull's straight-line intercept at *t* = 0.08 against the chord's *t* = 4.4,
and concluded that a curved baseline leaves no residual — i.e. that `r_Q` is confirmed to be the
chord's straightness. **That was wrong.** The hull had destroyed the Soret band, so the fitted *slope*
fell from 12.44 to 0.25 and there was nothing left to carry an intercept. **`r_Q`'s cause remains
unexplained, as §4.1 states.** The scoring script now voids any baseline whose slope departs from the
chord's.

**⭐ THE RECOMMENDATION, AS IT STANDS 2026-08-04.** ⛔ **T1 is retired** (box above) and **T4 is done and
negative**. What remains:

| | |
|---|---|
| ⛔ **do not adopt the correction** | in-sample only (§7); fails out of sample on a brown oil (T0's box); and **28 % of `r_Q` is a camera artifact** (the A4 box) |
| ⭐ **and it is about to become unnecessary** | at fixed optical density it is a pure rescaling — see T1's retirement box |
| ✅ **keep computing it — T2** | not as a verdict but as a **diagnostic**: at fixed OD `M` and `M∞` must track exactly, so divergence means the dosing discipline has slipped |
| ✅ **T1b at the next rig change** | still cheap, still sharp — it predicts a *change* rather than a constancy |

**⇒ Ship `M baseline`. Keep `M baseline + pedestal` as a process check. Do not change the shipped
verdict.** ✅ T4 is done and closed; ⚠ its
negative result *removes* the escape route, so the correction can no longer be set aside as
"superseded by a better baseline". It has to be judged on its own evidence — which, after T0's repeat
on a brown oil, is that it works in-sample and does not transfer.

<!--PAGEBREAK-->

## Appendix A — every number

Produced by `diagnostics/pedestal_correction.py`. Set values are means over runs.

| set | n | A_Soret raw | A_Q raw | turbidity 520–540 | `B_Soret` | `B_Q` | M uncorrected |
|---|---|---|---|---|---|---|---|
| Kiendler A | 6 | 0.8263 | 0.1108 | 0.0378 | 0.8366 | 0.0490 | 17.115 |
| Kiendler B | 2 | 1.1231 | 0.1994 | 0.0919 | 1.1045 | 0.0715 | 15.452 |
| Kiendler C | 2 | 1.1705 | 0.2082 | 0.1018 | 1.1397 | 0.0716 | 15.911 |
| Steirerkraft B | 6 | 1.0931 | 0.1968 | 0.0981 | 1.0580 | 0.0678 | 15.619 |
| Steirerkraft C | 6 | 1.1864 | 0.2300 | 0.1231 | 1.1323 | 0.0731 | 15.499 |
| S-Budget D | 6 | 1.0855 | 0.2251 | 0.1038 | 1.0237 | 0.1008 | 10.160 |

**Provenance.** Kiendler = `spectracs-references/tmp/20260801A|B|C/`, one evening, three
preparations of one oil. Steirerkraft = `20270729B/C`, two fills. S-Budget = `20260731A`, six
re-seats of one fill ("series D"). All post-rebuild, same instrument and protocol.

**Constants used.** `r_Q` = **−0.0184 A** — **the Kiendler fit, used as the shared constant for every
oil in every table above** (`shared = residual["Kiendler"]` in the script). Bands: Soret
440–460, Q 560–580, anchors **520–540 and 620–630 nm** — the shipped configuration (§16.20).
⚠ §4.1–4.2 alone use the older 600–630 anchor and its `r_Q` = −0.0246 A; they are the investigation that
moved the window.

**Chapter 9's dilution pairs.** `oilK`/`oilL` = one green oil at 2 and 3 drops; `oilN`/`oilM` = one
brown oil at 2 and 3 drops (both 2026-07-21, PRE-rebuild); `20270729B`/`C` = Steirerkraft at two
strengths, post-rebuild. Produced by `diagnostics/all_metrics_archive.py`, which also emits the
whole archive — 122 measurements across 40 series — as a single CSV.

## Appendix B — reproduction

```
export PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"

./venv/bin/python diagnostics/pedestal_correction.py    # chapters 1-7: numbers + Figures 1-8
./venv/bin/python diagnostics/all_metrics_archive.py    # chapter 9: the out-of-sample test

python3 docs/tools/build_pedestal_correction_pdf.py     # rebuild this PDF
```

The first prints every table in chapters 1–7 and writes **Figures 1–8** into `docs/figures/`. The second
prints chapter 9's dilution-pair table, plus the whole-archive metric matrix it is drawn from. The
third rebuilds this PDF from the markdown master.

<!--PAGEBREAK-->

## Appendix D — Scattering: the hypothesis, and what it does and does not explain

**Why this is an appendix.** Scattering is where this investigation started: it is the reason anyone
expected a curved background, and it correctly predicted the *sign* of `r_Q`. It then failed the only
test that could have confirmed it — the **size** — and it appears in **no formula the correction
computes** (§7). It is therefore motivation, not machinery, and collecting it here keeps it from
reading as support that the main text never claims.

**Everything this document says about scattering is in this appendix.** Chapters 3–13 keep only two
things: that the pedestal is **convex**, which is a statement of shape and not of cause; and the one
number this appendix produces, **≤ 17 %**.

### D.1 Why it was the obvious suspect

A cuvette of diluted oil does not only *absorb* light. It also **scatters** it — off undissolved oil
droplets suspended in the alcohol. Scattered light misses the camera just as absorbed light does, so
the instrument cannot tell the two apart: both arrive as "absorbance".

That is what puts the measured curve on a **pedestal** — a broad, smooth background present at every
wavelength and belonging to no pigment. Earlier work measured it at roughly **7 % of the Soret band
but 52–61 % of the Q band**; because the Q band is intrinsically weak, the same background is a far
larger share of it. A nuisance that large has to be subtracted, which is what the anchor windows and
the chord are for (ch. 3).

### D.2 What it predicts — convexity, and therefore the sign

Scattering does not fall off linearly with wavelength. It falls off roughly as a power law,

```math
P(\lambda) \propto \lambda^{-n}
  read: steep in the blue, flattening toward the red. For every n > 0 this curve is CONVEX.
```

and convexity is the whole of chapter 4's geometry: a straight line through two points on a convex
curve is a **chord**, a chord lies *above* the curve between its endpoints, the Q band lies between
the anchors, so the subtraction removes too much and **`r_Q` must be negative**. Measured, it is:
−0.0184 A on the shipped anchor. Had it come out positive, the model would have been dead.

⚠ **That prediction is worth much less than it looks, and it is worth being precise about why.**
Read what each premise contributes:

| premise | what it is | how much it constrains |
|---|---|---|
| the Q band lies **between** the anchors | a **design choice** — where the windows were put | pure geometry, no physics at all |
| the pedestal is **convex** | shared by λ⁻ⁿ for **every** n > 0, by Mie at any particle size, by an absorption tail, and by a far anchor reading too high | almost nothing — no realistic candidate is concave |

⇒ **The sign test discriminates convex from concave — not scattering from anything else.** Conditional
on there being any real decreasing background between the anchors, the negative sign was close to
forced, and a test that nearly cannot fail carries nearly no information when it passes. `r_Q` is in
accordance with the scattering law **and with every rival simultaneously**, which is exactly why it
fails to select scattering. *Agreement that nothing could have disagreed with is not support.*

### D.3 The size test — where the hypothesis could fail, and did

A mechanism that predicts the right sign and the wrong magnitude is not yet the right mechanism. The
pedestal at 530 nm is at most 0.1018 A — the whole raw absorbance there, of which the pigment takes
some, so this is an **upper bound**. What residual would a pure $\lambda^{-n}$ pedestal of that size
leave at the Q band?

| scattering law | exponent `n` | residual it leaves at Q |
|---|---|---|
| very shallow | 2 | 0.0015 A |
| **Rayleigh — the steepest real scattering** | **4** | **0.0042 A** |
| unphysically steep | 6 | 0.0077 A |
| unphysically steep | 10 | 0.0155 A |
| | **measured** *(600–630 anchor)* | **0.0246 A** |

**Rayleigh scattering accounts for about 17 % of the measured residual.** Reaching 0.0246 A from a
power law alone would take `n` ≈ 15 — and **`n` = 4 is the ceiling, not the middle**: larger particles
scatter *more* flatly, not more steeply, so no particle size in the sample can do this.

⇒ **Scattering is ruled out as the main term.** That verdict is unusually solid for this document,
because it rests only on the pedestal's magnitude — bounded above by the raw absorbance — and on
n = 4 being a ceiling. **≤ 17 %** is the number the rest of the document uses.

⚠ The measured value quoted here is **−0.0246 A**, the *600–630* anchor's, because this test belongs
to the investigation that moved the window (§4.1). On the shipped 620–630 anchor `r_Q` = −0.0184 A;
the ratio is what matters and it does not improve.

### D.4 What survives, and where it is used

| what survives | where the main text uses it |
|---|---|
| the pedestal is **convex** — a statement of *shape*, needing no cause | ch. 4's sign argument; assumption **A3** |
| scattering supplies **≤ 17 %** of `r_Q` | §4.1's attribution and Figure 3; caveat **C2** in §6; **T3** in ch. 13 |
| `r_Q` does **not** scale with turbidity (ch. 10) | consistent with this appendix: an instrument artifact does not care how cloudy the sample is. Two independent observations, one explanation |
| the correction contains **no** λ and **no** scattering term | §7's input table — the reason this is an appendix |

**⇒ The one practical consequence.** Chapter 13's **T3** proposed attacking `r_Q` physically, by
filtering the sample or changing the solvent. Both attack **turbidity**, and turbidity is at most a
sixth of the residual. **Filtration cannot remove what is not turbidity**, so it is not the strong
lever it was once presented as — even though the replacement lever is not yet identified.

### D.5 Reference

**Rayleigh and Mie scattering** — any optics text. What matters here is only the bound: the exponent
in $P \propto \lambda^{-n}$ reaches **n = 4** for particles much smaller than the wavelength and
*decreases* toward larger particles. It never exceeds 4, which is the ceiling D.3 uses to rule out a
pure scattering explanation of `r_Q`'s size.

⚠ `n` is **assumed**, never measured here: the λ⁻ⁿ fit was withdrawn as invalid on this instrument
(`SPEC_capture_quality.md` §16.12.11 B). The pedestal's convexity is therefore a claim from theory
whose only empirical support is the measured **sign** of `r_Q` — and D.2 has just shown how little
that is worth.

### D.6 ⭐ Is this a standard technique?

A fair question to put to a correction with no mechanism behind it, and the honest answer has two
halves: **the move is orthodox; this particular application of it is not yet a validated instance of
it.**

⚠ **None of the sources named in this section are held by the project.** They are named so the
technique can be located in the literature, not cited as support — the References section's rule
applies here too. Obtaining them is cheap and has not been done.

#### The shape of the move is well known, under at least four names

| family | what it does | relation to chapter 6 |
|---|---|---|
| **the Youden plot** *(analytical method validation)* | plot response against sample amount; a non-zero **intercept** diagnoses constant additive bias, while proportional bias shows in the **slope** | chapter 6 **is** a Youden plot, with the Q band on the x-axis instead of sample amount |
| **blank by extrapolation to zero** | the intercept of a calibration line estimates the blank; subtract it | the same operation, under the name every calibration course teaches |
| **Morton–Stubbs / Allen corrections** *(pharmacopoeial "irrelevant absorption")* | correct a band reading for a background assumed linear across it, using points either side | structurally the chord of chapter 3 |
| **EMSC** *(extended multiplicative scatter correction)* | models an **additive** baseline plus a **multiplicative** scale and removes both | designed for turbid samples — the closest chemometric relative |

**So nothing about diagnosing an additive offset from an intercept is unusual.** Separating constant
from proportional error this way is routine method validation.

#### Where this document departs from all four

| standard practice | what this document does |
|---|---|
| the blank is **measured** — a real blank cuvette, per sample or per batch | `r_Q` is **inferred** from an intercept and never observed directly (§6) |
| the interferent is **named and characterized** | ~51 % of `r_Q` is unaccounted; two candidates were tested and both rejected (D.3, §4.2) |
| the constant belongs to **the sample or batch it was measured on** | **one oil's constant is applied to every other oil** — assumption **A1**, supported by one oil |

**The third row is the whole difficulty.** It is the step that makes the correction usable in the
field, and it is the step no standard version of the technique performs. Everything chapter 12
argues, and everything T1 is designed to test, lives in that row.

#### ⚠ The alternative that was never priced

There is a more orthodox answer to the actual problem, and this document does not consider it.
Chapter 4 concludes that *"the entire problem is curvature, and nothing else"* — and then, instead of
**modelling** the curvature, corrects its consequence downstream. The mainstream remedies attack the
cause:

| remedy | what it assumes | why it would suit this problem |
|---|---|---|
| **a curved baseline** — polynomial, rubber-band, or asymmetric least squares (ALS / airPLS / arPLS) | the background is smooth and slowly varying | removes the over-subtraction at source; no constant to transfer between oils |
| **derivative spectroscopy** | nothing beyond smoothness | a second derivative **annihilates a linear background exactly** and strongly suppresses curved ones — the classic treatment for a weak band on a broad pedestal, which is exactly `B_Q` |

**Both have the property `r_Q` lacks**: they follow from a *stated model of the background* that can
be inspected, argued with, and violated — rather than from a constant fitted to outcomes on one oil.

⚠ **Neither is obviously affordable here**, which is why this is a question and not a recommendation.
The rig offers only **two** anchor windows, so a polynomial baseline has very little to fit; and
derivatives cost signal-to-noise on bins that already read 2.0–2.6 DN at the blue edge (§7). **But the
cost was never estimated.** ⇒ **A fourth test belongs in chapter 13: price a curved baseline and a
second-derivative reading against the present chord-plus-`r_Q`, on data already on disk.** If either
works, the correction — and A1 with it — becomes unnecessary rather than unproven.

## References

Only sources the project actually holds are listed. Where a claim in this document rests on no source,
it says so rather than borrowing authority from a neighbouring one.

### The two bands, and the molecule they belong to

1. **Gouterman, M. (1961).** *Spectra of porphyrins.* J. Mol. Spectrosc. **6**, 138. The four-orbital
   model that names the Soret and Q bands, and that explains **why the Q transitions are weak while the
   Soret is intensely allowed** — which is the whole reason this document's denominator is fragile
   (ch. 8.1).
2. **Fruhwirth, G. O. & Hermetter, A. (2007).** *Seeds and oil of the Styrian oil pumpkin: components
   and biological activities.* Eur. J. Lipid Sci. Technol. **109**(11), 1128–1140.
   DOI [10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105). Identifies protochlorophyll
   a/b and protopheophytin a/b in this oil. Local copy in `spectracs-references/articles/`.
3. **Protochlorophyllide spectral forms.** Pak. J. Biol. Sci. (2010),
   [scialert.net](https://scialert.net/fulltext/?doi=pjbs.2010.563.576). Band positions and the
   **80 % acetone convention** that ch. 8.3(b) names as the route to a literature-comparable number.
4. **Histolocalisation of the oil and pigments in the pumpkin seed** —
   [ResearchGate](https://www.researchgate.net/publication/227928192_Histolocalisation_of_the_oil_and_pigments_in_the_pumpkin_seed).
   Protopheophytins run 1.1–35.5 % of protochlorophylls and **rise with storage** — the mixture that
   ch. 8.2's speciation argument depends on.
5. **The four porphyrin spectral types and their Q-band ordering** — *The Use of Spectrophotometry
   UV-Vis for the Study of Porphyrins*,
   [InTech](https://cdn.intechopen.com/pdfs/37656/InTech-The_use_of_spectrophotometry_uv_vis_for_the_study_of_porphyrins.pdf).
   Textbook support for demetallation rearranging Q-band intensity (ch. 8.1).

⚠ **Not sourced, and load-bearing:** no reference we hold **assigns the 560–580 nm band**. Chapter
8.3(a) states this openly; it is the denominator of the metric, and the acid test is one afternoon's
work.

### Scattering, baselines and Beer–Lambert

6. **Rayleigh and Mie scattering** — moved to **Appendix D.5** with the rest of the scattering
   material, and listed here as a pointer only.
7. **Two-point baseline subtraction** — the standard turbidity remedy in analytical spectrophotometry:
   estimate the background from wavelengths where the analyte is quiet, interpolate, subtract. Chapter 3
   applies it; chapter 4 is about its one unavoidable error.
8. **Beer–Lambert** — any physical-chemistry text. Assumption A4, and the reason chapter 5's algebra is
   three lines rather than a model.

### Our own measurements and their owning specifications

| topic | where |
|---|---|
| the derivation this document corrects | `SPEC_capture_quality.md` §16.14.4–6 |
| the session that measured `r_Q` | §16.15, and the lab diary for 2026-08-01/02 |
| **the far anchor's corruption — the 607 nm artifact** | `DOC_metric_algebra.md` §5.9 |
| **the withdrawn λ⁻ⁿ fit, and the lamp's red cliff** | `SPEC_capture_quality.md` §16.12.11 B |
| the interpolation weights 0.529 / 0.471 | `DOC_metric_algebra.md` §5.5 |
| the dilution sensitivity — `F` − 1 under another name | `DOC_metric_algebra.md` §5.7 |
| speciation vs concentration, refuted at *d* = 10.26 | `SPEC_capture_quality.md` §16.13.9 |
| the threshold at risk | §16.10.17d, §16.15.7 |
| the instrument, end to end | `DOC_capture_fidelity.md` |
| the sample, end to end | `DOC_sample_physics.md` |

## Appendix C — where this sits in the specifications

| | |
|---|---|
| the derivation this confirms | `SPEC_capture_quality.md` §16.14.4–6 — pedestal curvature as the *only* mechanism that can break dilution invariance |
| the session that measured it | §16.15, and the lab diary entry for 2026-08-01/02 |
| the bound this supersedes | §16.14.7 asserted a bound of 0.008 A on the residual from pooled archive data; the measured value is ~3× that |
| the threshold at risk | §16.10.17d, and §16.15.7 for what the pedestal-free scale does to it |
| the open question | §16.10.8, dilution invariance, which the 2026-08-01 session did **not** close |
