# SPEC — Metric research: what should replace or outperform the baselined band ratio

**Status: DESIGN / BRAINSTORM. Nothing here is implemented.** This document is a *pool of ideas* and
an *evaluation protocol*, written so that candidates can be argued about before any of them is coded.

**Owner:** Edwin · **Opened:** 2026-08-04 · **Prompted by:** `DOC_pedestal_correction.md`, and the
conclusion that the correction it describes is an unexplained fitted constant transferred across oils
on an untested assumption.

---

## 1 · Why step back

The shipped metric is

```math
M = \frac{B_{Soret}}{B_{Q}}
  read: two band means, each taken above a straight chord fitted through two anchor windows.
```

and the last three weeks went into a **correction to the denominator** (`r_Q`) because the chord
over-subtracts. That work reached an honest but uncomfortable place:

| finding | where |
|---|---|
| `r_Q` is real and reproducible within a rig state | ch. 6 |
| its cause is **unexplained** — two candidates tested and rejected, ≈ 51 % unaccounted | §4.1, §4.2, App. D |
| transferring one oil's `r_Q` to other oils is the load-bearing assumption, **supported by one oil** | A1, §6 |
| the headline 10.3 % → 3.0 % is **in-sample** | §7 |
| the orthodox alternative — *model the curvature instead of patching its consequence* — was **never priced** | App. D.6, T4 |

**⇒ The question this document asks is not "how do we correct `M`?" but "is `M` the right metric at
all?"** A metric that needed no baseline would make `r_Q`, assumption A1, and the whole correction
*unnecessary* rather than unproven.

⭐ **The target property is dilution-invariance**: the number must not move when the operator
prepares the sample a little stronger or weaker, because in the field nobody measures the
concentration.

---

## 2 · The corpus — exactly what may be used

Restricted, per Edwin, to the three post-rebuild oils. **`20270729A_aged24h` is excluded**: it is a
browner oil, not a noisier one (`SPEC_capture_quality.md` §16.11.16), and including it would put an
uncontrolled ageing axis into every score.

| oil | series | runs | preparations | what it can test |
|---|---|---|---|---|
| **Kiendler** *(green)* | `20260801A` `B` `C` | 6 + 2 + 2 = **10** | **3 strengths** — A accidentally over-dilute | **dilution-invariance** (`B_Q` spans 48 %) |
| **Steirerkraft** *(green)* | `20270729B` `C` | 6 + 6 = **12** | **2 strengths** | dilution-invariance (span only 14 %) |
| **S-Budget** *(brown)* | `20260731A` | **6** | **1 fill, re-seated 6×** | **class separation** and **re-seating stability** — *not* invariance |

**28 runs, 3 oils, 6 preparations.**

### ⚠ 2.1 What this corpus structurally cannot answer

- **Dilution-invariance for the brown class.** S-Budget exists at one strength. Every invariance score
  in this document is a *green-oil* score. This is the same hole as T1 in the pedestal document, and
  the same one-extra-fill fixes it.
- **Anything about ageing, roast level, or adulteration.** Three oils is a class demonstration, not a
  calibration.
- **Transfer across rig states.** All 28 runs are one rig state. `DOC_pedestal_correction.md` ch. 9
  showed a rebuild breaks constants; nothing here can see that.

#### ⛔ 2.2 Pseudo-replication — the limit that qualifies every effect size in this document

*(Found while rubber-ducking R3, 2026-08-04. It applies retroactively, and beyond this document.)*

**The 28 runs are not 28 independent observations of a class.** Six of them are one jar re-seated six
times. **The unit of replication for a question about the green/brown *classes* is the OIL, and we
have three** — two green, one brown.

Two consequences, and both are structural:

1. ⛔ **No permutation test for class is possible.** Permuting runs destroys the clustering and yields
   a null far too tight; permuting at oil level gives **3 labelings**, which is not a distribution.
   *There is no significance test for class separation available on this corpus, for any metric.*
2. ⚠ **Cohen's *d* is measured against the wrong yardstick.** *d* divides by within-group SD, which
   here is dominated by **re-seating scatter**. So `M`'s ***d* = 6.91 means "these two greens differ
   from this one brown by 6.9 × the noise of putting the jar back"** — not that a *new* brown oil
   would land there. Generalising to the class needs **between-oil variance for the brown class, and
   one brown oil cannot estimate it.**

**⇒ Every effect size in this document, and the 6.91 / 9.61 figures in `DOC_pedestal_correction.md`,
are correct as DESCRIPTIONS and do not support generalisation to the class.** They are not wrong; they
answer a narrower question than their presentation implies.

**The available substitute.** The only same-class oil pair we own — **Kiendler vs Steirerkraft** — gives
an empirical floor for "how far apart do two oils of the *same* class sit". Scored that way:

| candidate | class *d* | within-class *d* | **ratio** |
|---|---|---|---|
| `M` + pedestal correction | 9.61 | 0.27 | ⭐ **35.7** |
| Q peak, recalibrated per run | 3.98 | 0.18 | **22.0** |
| Q peak, per session | 4.05 | 0.20 | 20.0 |
| `M`, re-centred window | 7.16 | 1.11 | 6.5 |
| **`M`, shipped** *(incumbent)* | 6.91 | 1.21 | **5.7** |
| Q peak, raw | 3.87 | 1.35 | 2.9 |
| C1 flank-slope | 0.76 | 1.67 | ⛔ **0.46** |

⚠ **Read this table with two brakes on.** (i) The within-class contrast is **also a between-session
contrast**, so any method that removes session effects scores falsely well — the Q-peak recalibration
*is* a session calibration, so its 22.0 is substantially circular. (ii) It rests on **one pair of green
oils**. It is a reason to look, not a result. **R0b remains the only thing that fixes this**, and this
is now the third independent route to that conclusion (after §3.4 and T1).

---

## 3 · The evidence matrix — what we have at hand

### 3.1 ⭐ The spectral range, and the fact that changes everything

Measured on `20260801C/001`:

| | |
|---|---|
| usable range | **440.0 – 629.8 nm** |
| bins | **1305**, spacing **0.146 nm** |

Now put the pigment's own band positions beside it (`KB_spectroscopy_physics.md` §4.1,
protochlorophyll *a*):

| band | position | where it falls in our range |
|---|---|---|
| **Soret** | ≈ 432–440 nm | ⚠ **at or below the left edge — we see only its red flank** |
| Qy | ≈ 623–626 nm | ⚠ **at the right edge, truncated at 629.8 — we see only its blue flank** |

⇒ **Both principal bands are flank-only.** Neither peak maximum is in the data. Everything the
instrument currently reports about them is read off a shoulder.

This reframes Edwin's *"extrapolate the peaks for which we have only some flank"* from a nice-to-have
into **the central structural fact of the whole measurement**, and it argues for candidate class **B6**
(band decomposition) more strongly than anything else in this document.

The bin density is the good news: **1305 bins at 0.146 nm** leaves ample room for smoothing, which is
what class **B2** (derivatives) needs.

### 3.2 What we compute, and what we throw away

`diagnostics/settling_sweep.py::measure` already returns ~25 quantities per run. Every one of them is
an **amplitude** — a band mean, or a ratio of band means.

⭐ **Nothing currently uses a *shape* of anything.** In particular:

| available but unused | why it is interesting |
|---|---|
| ⭐ **the slope of the far window** `dA/dλ` over 620–630 | it is the Qy band's blue flank rising into the cut-off. A **slope is a derivative**, so it is *immune to any additive offset* — the entire `r_Q` problem cannot touch it |
| the slope of the Soret red flank, ~460–480 nm | the other flank, same immunity |
| curvature (2nd derivative) anywhere | kills a *linear* background exactly — i.e. kills the chord itself |
| band width, asymmetry, centroid, moments | intensity-normalised by construction ⇒ dilution-invariant *a priori* |
| the residual spectrum after baselining, as a curve | we reduce it to two numbers and discard the rest of 1305 bins |

**A sighting shot, not a result.** One run per oil, the two flank slopes and their ratio:

| oil | far slope 620–629.8 | Soret-flank slope 460–480 | ratio |
|---|---|---|---|
| Kiendler C | +0.00831 A/nm | −0.01494 A/nm | **−0.556** |
| Steirerkraft C | +0.00745 | −0.01574 | **−0.473** |
| S-Budget D *(brown)* | +0.00522 | −0.01285 | **−0.406** |

⚠ **One run each. This is a reason to look, not a finding.** It orders green-above-brown in the same
direction as `M`, using **no baseline, no anchors and no `r_Q`** — which is exactly the property this
document is hunting. It must be run over all 28 runs before it means anything. **⇒ It was, in §3.5, and it did not survive.**

### 3.3 Theory-anchored positions

Gouterman's four-orbital model (References 1, 5) gives band *positions and counts* from symmetry, not
from our data — a source of window placements that is **independent of the corpus**, and therefore
immune to the overfitting trap of §6.4:

- **Metalated** porphyrin (protochlorophyll, Mg present) — **D4h**, degenerate Eu states ⇒ a **two**-band
  Q region: Q(0,0) and Q(0,1).
- **Free base** (protopheophytin, Mg lost) — symmetry drops to **D2h**, the degeneracy is **lifted**,
  and the Q region splits into **four** bands: Qy(0,0), Qy(0,1), Qx(0,0), Qx(0,1).

⇒ **Demetallation is a change in band *count and position*, not only in amplitude.** That is the
physical basis for a speciation metric, and it is consistent with what we already measured on the aged
fill: Qy −17 % *and* 572 nm +14 % (§16.11.16). A metric built on *positions* would read that directly
instead of inferring it from two amplitudes.

⚠ Our range covers the Q region but truncates Qy. Which of the four free-base bands are reachable at
440–630 nm needs to be worked out from the literature before windows are drawn — **open question Q3**.

### ⚠ 3.4 The session confound — the corpus's worst problem, and it is not concentration

**Each oil was measured in its own session, on its own evening.**

| oil | session |
|---|---|
| Steirerkraft | `20270729B/C` — the oldest, immediately post-rebuild |
| S-Budget | `20260731A` |
| Kiendler | `20260801A/B/C` — the newest |

⇒ **oil class and measurement session are perfectly confounded.** Any candidate that appears to
separate the oils may be separating the *evenings* — lamp warm-up, WB convergence, seating, room
temperature, sample age-in-beam. Nothing in the existing data can tell the two apart.

**This is not hypothetical — §3.5 caught a candidate doing exactly that.**

**⇒ The single most valuable bench action available is one evening measuring all three oils
back-to-back in one session**, ideally each at two strengths. That one run would break the confound,
close Q5, and close T1 of the pedestal document simultaneously.

### ⭐ 3.5 First inspection — `diagnostics/metric_research_overview.py`

All 28 runs in four panels (`docs/figures/metric_overview.svg`): raw, normalised at 450 nm, 1st
derivative, 2nd derivative — Savitzky–Golay, 101 bins ≈ 14.7 nm. Three findings, in descending order
of importance.

**(a) ⚠ C1, the flank-slope ratio, is TASK-DEPENDENT — not simply refuted.** Over all 28 runs
rather than one run per oil:

| Soret-flank window | Kiendler *(green)* | Steirerkraft *(green)* | S-Budget *(brown)* |
|---|---|---|---|
| 460–480 | −0.468 ± 0.068 | −0.567 ± 0.051 | **−0.465 ± 0.069** |
| 478–500 | −1.350 ± 0.266 | −1.805 ± 0.174 | **−1.329 ± 0.186** |
| 462–470 | −0.293 ± 0.045 | −0.358 ± 0.034 | **−0.297 ± 0.047** |
| 480–510 | −1.753 ± 0.247 | −2.119 ± 0.217 | **−1.704 ± 0.268** |

**On every window, Kiendler ≈ S-Budget and Steirerkraft is the odd one out.** Under the roster the
documents use *(S-Budget = brown)* that is *green ≈ brown with the other green apart* — not class.
Scored as Cohen's *d*:

| comparison | `M` *(incumbent)* | **C1** |
|---|---|---|
| **{Kiendler, Steirerkraft} vs S-Budget** — green vs brown | **6.91** | 0.76 |
| Kiendler vs S-Budget | **7.88** | 0.05 |
| **Kiendler vs Steirerkraft** — green vs green | 1.21 | **1.67** |

⇒ **The two metrics answer different questions.** `M` is overwhelming at green-vs-brown and modest
between the two greens; **C1 is useless at green-vs-brown and slightly better than `M` between the two
greens.** ⛔ **Q6 is now answered — the target is green vs brown — so C1 is dead for this research.**
It is parked in §7 against a future within-class grading question.

⭐ *The sighting shot in §3.2 was still wrong for the reason §6.4 gives — one run per oil, ordered
correctly, and not reproducible over 28. Pre-registration earned its keep on day one.*

**(b) Two sharp instrument lines dominate derivative space.** Curvature of the corpus mean at a ~3 nm
scale:

| feature | \|d²A/dλ²\| | what it is |
|---|---|---|
| **473.04 nm** | **0.191** | a lamp line — an order of magnitude above any real feature |
| **608.24 nm** | **0.090** | the known 607 nm line (`DOC_metric_algebra.md` §5.9) |
| 580.23 nm | 0.011 | ⭐ a *real* band edge — the Q band's red side |
| 446, 452, 465, 479, 486 nm | ≤ 0.017 | real structure on the Soret flank |

⇒ **Any derivative candidate (C2, C3, C4, C10) must excise 473 and 608 before differentiating**,
otherwise it measures the lamp. Cheap, mandatory, and it applies to nothing else in the pool.
⚠ Note 473 sits **inside** the 460–480 window used above — though the table in (a) shows that is not
why C1 failed.

**(c) The normalised panel is where the eye should go next.** Panel B divides each run by its own
A(450) — concentration out, shape left — and the classes still overlap heavily, but the region
**560–590 nm** is where the curves visibly fan. That is the Q band and its red edge, it is the one
place (b) finds real structure, and it is not where the shipped 560–580 window is centred.

### ⭐⭐ 3.6 The Q band has a resolvable PEAK at ≈ 574 nm — and its POSITION carries the class

This is the strongest lead in the document, and it is a direct answer to *"we do not measure the peaks
of the other degenerate Q bands"*.

Smooth each run (SG, 151 bins ≈ 22 nm), detrend locally across 545–605 nm, take the maximum with a
parabolic sub-bin refinement:

| set | `B_Q` | **peak position** | runs |
|---|---|---|---|
| Kiendler A *(over-dilute)* | 0.0490 | **574.13 ± 0.12 nm** | 6 |
| Kiendler B | 0.0715 | 573.87 ± 0.05 | 2 |
| Kiendler C | 0.0716 | 573.99 ± 0.02 | 2 |
| Steirerkraft B | 0.0678 | 573.77 ± 0.15 | 6 |
| Steirerkraft C | 0.0731 | 573.93 ± 0.11 | 6 |
| **S-Budget D** *(brown)* | 0.1008 | **573.20 ± 0.24** | 6 |

**(i) It is dilution-stable.** Kiendler's `B_Q` varies by **×1.46** across its three preparations and
the peak moves **0.26 nm** — *non-monotonically* (574.13 → 573.87 → 573.99), so it is scatter, not a
trend. Over those same three preparations `M` spreads 10.3 %. ⭐ **A position is dilution-invariant by
construction (class B3); this is what that looks like on real data.**

**(ii) It separates.** On position alone:

| comparison | **peak position** | `M` |
|---|---|---|
| Kiendler vs S-Budget | **4.57** | 7.88 |
| {Kiendler, Steirerkraft} vs S-Budget | **3.87** | 6.91 |
| Kiendler vs Steirerkraft | **1.35** | 1.21 |

Weaker than `M` at green-vs-brown, marginally better between the greens — **and it uses no baseline,
no anchors, no `r_Q`, and no amplitude at all.**

**(iii) It moves the right way.** The browner oil sits at **573.20**, the greener at **574.13** — the
brown class is **blue-shifted**. That is the physics `SPEC_capture_quality.md` §16.11.16 already
recorded on the aged fill (*"572 nm +14 %"*), read here *directly as a position* instead of inferred
from an amplitude ratio over an auxiliary chord.

#### ⛔ 3.6a The threat that must be cleared first: wavelength calibration

A position metric is uniquely vulnerable to the instrument's λ-calibration drifting **between
sessions** — and §3.4 says every oil *is* a different session. The two lamp lines of §3.5(b) are fixed
by physics, so they are a free internal check. Measured with a crude centroid estimator:

| | Kiendler | Steirerkraft | S-Budget | spread of means |
|---|---|---|---|---|
| 473 nm line | 473.054 ± 0.229 | 473.263 ± 0.046 | 473.238 ± 0.024 | 0.21 nm |
| 608 nm line | 608.533 ± 0.325 | 608.204 ± 0.291 | 608.287 ± 0.124 | 0.33 nm |

⚠ **Inconclusive as run, and it must not be read as either confirmation or refutation.** The
estimator's own scatter (0.12–0.33 nm) is a large fraction of the 0.93 nm Q-band signal, and the two
lines move in **opposite** directions between sessions — which a simple calibration offset cannot do.
The likely explanation is that the crude centroid is noisy (the 608 line sits on the rising Qy flank,
which biases its local chord), not that calibration is broken.

#### ✅ 3.6b R1b RESULT — the threat is real, diagnosed, and CONVERTED INTO AN ASSET

`diagnostics/lamp_line_calibration.py` re-measured both lines with a Gaussian fitted on a wing-fitted
quadratic continuum — the same quality of estimator as the Q peak.

**The opposite-direction movement is real; it was not the estimator.** But it is not noise either:

| session | Δ 473 nm | Δ 608 nm | ⇒ implied pivot |
|---|---|---|---|
| Kiendler `20260801` | −0.093 | +0.216 | **513.7 nm** |
| Steirerkraft `20270729` | +0.060 | −0.143 | **512.8 nm** |
| S-Budget `20260731` | +0.036 | −0.073 | **517.4 nm** |

⭐ **Two lines moving in opposite directions about a common fixed point is a wavelength-SCALE change,
not an offset** — a dispersion (nm-per-bin) drift about a pivot in the optical layout. Three
independent sessions agree on that pivot within 5 nm, which no accident produces.

**And two reference lines are exactly enough to invert it** — two references, two parameters
(offset + scale). Applying the map that carries each run's lines onto the corpus grand mean:

| | raw | **recalibrated** |
|---|---|---|
| Kiendler | 574.049 ± 0.143 | 573.911 ± 0.099 |
| Steirerkraft | 573.849 ± 0.151 | 573.941 ± 0.205 |
| S-Budget *(brown)* | 573.201 ± 0.244 | 573.245 ± 0.206 |
| **Kiendler vs Steirerkraft** *(two greens — SHOULD be alike)* | *d* = 1.35 | ⭐ ***d* = 0.18** |
| **greens vs brown** *(the target)* | *d* = 3.87 | ***d* = 3.98** |

⇒ **The apparent difference between the two green oils was the instrument, not the oil.** Correcting
it collapses that difference by 7× while leaving the green-vs-brown separation intact. **The lamp
lines are not a threat to C14 — they are a built-in calibration standard that makes it better.**

⚠ **Two things this does not settle.** (i) The recalibration is currently applied **per run**, so each
run inherits the noise of its own two line fits — Steirerkraft's within-oil spread *rose* (0.167 →
0.302 nm) even as the between-oil bias fell. A **per-session** calibration should be tried instead
(**R2a**). (ii) It removes *relative* drift between sessions; it makes no claim about the absolute
wavelength scale.

⚠ **Wider consequence, for `SPEC_capture_quality.md`:** the wavelength scale drifts between sessions
by ±0.2 nm at 608 nm and **nothing in the pipeline corrects for it.** Band means over 20 nm windows
barely notice. Any position-based quantity does.

### ⭐ 3.7 R1 + R2 RESULT — the first full scoring pass

`diagnostics/metric_features.py` writes the §6.3 table (28 runs × 30 features);
`diagnostics/metric_scores.py` reads only that. **12 candidates scored** (§6.4 rule 2).

| candidate | id | baseline? | S1 Kiendler | **S2 (target)** | S3 CV |
|---|---|---|---|---|---|
| `M` + pedestal correction | C12 | yes | 2.98 % | **9.61** | 4.48 % |
| `M` + correction, re-centred window | C12b | yes | 2.43 % | 9.55 | 4.38 % |
| **`M`, Q window re-centred 566–582** | **C11b** | yes | 9.38 % | **7.16** | 4.48 % |
| `M`, Q window 564–584 | C11c | yes | 9.93 % | 7.13 | 4.78 % |
| **`M`, shipped 560–580** *(incumbent)* | C11 | yes | 10.31 % | 6.91 | 4.99 % |
| ⭐ **Q-peak position, recalibrated** | **C14c** | **NO** | **0.029 %** | 3.98 | **0.04 %** |
| Q-peak position, raw | C14 | NO | 0.045 % | 3.87 | 0.04 % |
| Q-peak height | C15a | NO | 29.7 % | 1.93 | 4.94 % |
| Q first moment | C5 | NO | 0.022 % | 1.50 | 0.08 % |
| flank-slope ratio | C1 | NO | 26.8 % | 0.76 | 14.8 % |
| far-window slope alone | C10a | NO | 62.0 % | 0.64 | 10.1 % |

**Three readings.**

**(a) ⭐ Edwin's window question, answered: the metric HOLDS, and slightly improves.** Re-centring the
Q window on the measured 574 nm peak moves S2 **6.91 → 7.16** and S1 **10.31 % → 9.38 %** — better on
both axes, and no instability. ⇒ **`M` is not fragile to that change.** The gain is small, so this is
not on its own a reason to re-scale the shipped metric; it is a reason to stop treating 560–580 as
load-bearing.

**(b) The pedestal correction scores BEST on separation** (9.61 vs 6.91). That is a point in its
favour this document had not previously scored — but ⚠ its S1 advantage (2.98 %) is the in-sample
artifact `DOC_pedestal_correction.md` §7 documents, and its S2 gain has never been tested
out-of-sample.

**(c) ⛔ RETRACTED 2026-08-04 — "C14 is 355× more dilution-stable" was a scale artifact.**

This section first read: *"S1 — dilution spread: `M` 10.31 % vs C14 0.029 %, **355× better**; S3
re-seating CV 4.99 % vs 0.04 %, **125× better**"* — and concluded the position was "a different
instrument". **Both multipliers are meaningless, and the conclusion with them.**

**Why.** S1 and S3 were quoted as a **per cent of the metric's own value**, and a wavelength carries a
huge arbitrary offset. The Q peak's 0.26 nm dilution spread is 0.045 % *of 574 nm* — but **6.4 %** if
the identical feature is written as *"nm above 570"*. A pure relabelling moves the score by 140×. Any
statistic that behaves that way is not measuring stability.

**The scale-free comparison** — nuisance measured against the signal the metric must carry, invariant
under any affine relabelling:

| | **`M`** | **Q-peak position** | |
|---|---|---|---|
| class separation | 5.85 *(ratio units)* | 0.682 *(nm)* | |
| dilution spread, Kiendler | 1.665 | 0.259 | |
| ⭐ **separation ÷ dilution spread** | **3.51** | 2.63 | **`M` is 1.3× better** |
| mean within-set sd | 0.485 | 0.115 | |
| ⭐ **separation ÷ within-set sd** | **12.05** | 5.96 | **`M` is 2× better** |

⇒ **The position candidate has no stability advantage at all.** It is not "a different instrument" — it
is simply **worse on every axis**, and its apparent immunity was an artifact of being measured on a
scale with a large offset. This is also exactly what S2 said all along (6.91 vs 4.05); Cohen's *d* is
already scale-free, which is why it never showed the phantom advantage.

⚠ **`diagnostics/metric_scores.py` has been changed to report `sep/dilut` and `sep/within` instead of
the two percentages**, so this class of error cannot recur. The raw dilution spread is still printed,
in the feature's own units, where it belongs.

⇒ **De facto: there is no case for switching to the position metric, and none for combining it either**
— §3.9's null result is now unsurprising rather than puzzling, since a strictly worse feature that
correlates with `M` (*r* = +0.31) has nothing to contribute.

### ✅ 3.8 R2a RESULT — calibrate per SESSION, not per run

§3.6b predicted it: the drift is a property of the **evening**, so averaging the two lines over the
session should keep the bias correction and drop the per-run fit noise. It does.

| Q-peak variant | S1 Kiendler | S1 Steirerkraft | **S2** | S3 CV |
|---|---|---|---|---|
| raw, uncalibrated | 0.045 % | 0.029 % | 3.87 | 0.04 % |
| calibrated **per run** | 0.029 % | *0.053 %* ⚠ | 3.98 | 0.04 % |
| ⭐ calibrated **per session** | 0.045 % | **0.029 %** | **4.05** | 0.04 % |

⇒ **Per-session dominates.** It gives the best separation *and* leaves within-oil spread exactly where
the raw feature had it, whereas per-run inflated Steirerkraft's spread (0.029 → 0.053 %) by injecting
each run's own line-fit noise. The Q first moment agrees independently: **1.88 per-session > 1.50 raw
> 1.37 per-run.**

**⇒ Adopted: `q_peak_nm_calsession` is the canonical position feature.** Per-run calibration is kept
in the table only as the control that demonstrates why.

### ⚠ 3.9 C15 RESULT — combining does NOT help, and the reason is instructive

§3.7 argued the position and the incumbent looked like complements — one 355× more stable, the other
1.7× more discriminating. **Scored, they are not.** Six pairings, z-sum (no weights fitted) against
Mahalanobis (the ceiling of any linear combination, fitted on the same 28 runs, therefore optimistic):

| pair | best single | **z-sum** | Mahalanobis *(ceiling)* |
|---|---|---|---|
| `M` + Q-peak position *(per session)* | 6.91 | **6.91** — *no gain at all* | 7.30 |
| `M` + Q-peak position *(per run)* | 6.91 | 7.65 | 7.93 |
| `M` re-centred + position | 7.16 | 7.03 | 7.49 |
| `M` **corrected** + position | 9.61 | **8.58** — *combining HURTS* | 9.73 |
| Q-peak height + position | 4.05 | 4.53 | 4.75 |
| `M` + Q-peak height | 6.91 | **4.85** — *hurts badly* | 7.75 |

**Why.** Two independent features of strength *d*₁ and *d*₂ combine to √(*d*₁² + *d*₂²) = √(6.91² +
4.05²) = **8.01**. The observed z-sum is **6.91** and even the fitted ceiling only reaches 7.30. The
information is not additive because it is not independent:

| within the green class *(n = 22)* | *r* |
|---|---|
| `M` vs Q-peak position | **+0.314** |
| `M` vs Q-peak height | **−0.676** |
| Q-peak position vs Q-peak height | +0.024 |

⇒ ⭐ **`M` and the peak position are reading the same axis, as the physics says they should** — both
are consequences of the same demetallation. The position is not a second, independent witness; it is
the *same* witness, speaking more steadily and less loudly.

⚠ The one pairing that appears to gain (`M` + **per-run** position, 6.91 → 7.65) uses the *noisier*
calibration that §3.8 just showed to be inferior on its own. **Treat it as an artifact until
reproduced**, not as a result — it is exactly the kind of best-of-six number §6.4 rule 2 exists to
discount. **20 candidates have now been scored** (14 scalars + 6 pairs).

**⇒ What this leaves.** C15 is closed. ⚠ **Revised 2026-08-04 after §3.7(c)'s retraction:** the honest
position is not "`M` discriminates, the position is stable" — it is that **`M` is better on every
scale-free measure**, and the position's supposed stability was an artifact. They are two views of one
axis, and one view is strictly worse. Any
real gain must come from a genuinely *independent* feature, which points at **C7** (band decomposition
recovering the truncated peaks, §3.1) and **B8** (isosbestic referencing) rather than at more
recombinations of what we already read.

### ⛔ 3.10 C7 RESULT — the Q region will not decompose on this data

§3.9 concluded that any real gain needs a genuinely *independent* feature, and pointed at band
decomposition. Fitted over 545–605 nm, one Gaussian plus a linear background against two:

| oil | 1 band | 2 bands | RMS gain | what the second component came out as |
|---|---|---|---|---|
| Kiendler C | RMS 0.00501, c = 574.1 | RMS 0.00452 | 10 % | ⛔ centre **595.8**, amplitude **−0.023** — *negative* |
| S-Budget D | RMS 0.00437, c = 573.4 | RMS 0.00410 | 6 % | centre 579.0, amplitude +0.083, with the first pushed to 569.7 |

⇒ **The model is not identifiable.** The two oils return *qualitatively different* solutions — one puts
a negative component at 596 nm (the fit absorbing baseline curvature, not a band), the other splits the
peak into two positives. Three extra free parameters buy 6–10 % of RMS. **Nothing comparable across
oils can be built on that.**

⚠ **This is not a refutation of C7, it is a refutation of C7 *unconstrained*.** The decomposition needs
its band centres **fixed from theory** rather than fitted — which is exactly **Q3**, still unanswered:
we do not yet hold the four D2h free-base Q-band positions for protopheophytin *a*. **⇒ C7 is blocked
on a literature errand, not on data.**

### ⚠ 3.11 B8 RESULT — a real ageing signal, but the isosbestic point is not yet locatable

**The dataset.** `20270729A_aged24h` is the *same oil, same session*, 24 h later than `20270729B/C` —
a speciation series with **no calibration confound** (§3.4 does not apply within one evening). It is
re-admitted here for this diagnostic only; it stays out of the §2 scoring corpus.

**A null test decides it.** Compare the aged-vs-fresh difference against random 3-vs-9 splits of the
*fresh runs alone* (200 draws) — whatever the split test produces is scatter, not speciation.

| normalisation | region | max \|difference\| | null 95th | **signal / null** |
|---|---|---|---|---|
| area over 500–630 nm | 500–630 | 0.00112 | 0.00112 | 1.00 |
| Soret-referenced | 460–630 | 0.0726 **at 471.4 nm** | 0.0355 | *2.05* |
| Soret-referenced | ⛔ **lamp zone 462–486 excluded** | 0.0365 | 0.0298 | **1.23** |
| Soret-referenced | ⭐ **pigment region 500–630 only** | 0.0177 at 574.4 nm | 0.0329 | ⛔ **0.54** |

⛔ **CORRECTED 2026-08-04, same day.** A first pass reported *"signal / null = 2.05, the signal is
real"*. It is not. **The 2.05 was the 473 nm lamp line** — its maximum sat at 471.4 nm, inside the
artifact zone §3.5(b) already flagged. Excise that zone and the ratio falls to 1.23; restrict to the
pigment region proper and it is **0.54, i.e. half the fresh-only noise floor.** A pointwise test with a
per-wavelength null band agrees: across 485–630 nm **no extremum reaches its own 95th percentile**
(520–540 ratio 0.44, 560–580 ratio 0.70, 620–630 ratio 0.47).

⚠ **This does not contradict §16.11.16**, which found the aged fill *is* a browner oil (Qy −17 %,
572 nm +14 % per unit Soret, 3/3 runs misclassified). That used the **metric** — a targeted,
low-dimensional read. This is a **whole-spectrum shape** test at *n* = 3, which is far less sensitive
and is what an isosbestic determination actually needs. **The oil differs; the difference is not
resolvable as a curve shape at three runs.**

**⇒ There are no usable isosbestic points in this data.** Crossings can be *computed* (499.1, 536.5,
550.3, 589.1 nm) but they are crossings of a curve that is itself below the noise floor. Reporting them
as candidates would be reading structure into scatter.

**⇒ B8 is blocked on more ageing states — and the experiment already exists.** `SPEC_capture_quality.md`
**§16.11.17's decay-rate run (0 / 1 / 2 / 4 / 24 h, one fill, one evening)** is precisely a speciation
series at five mixing ratios, in one session, and it is already the next scheduled bench task. ⭐ **It
would convert B8 from a two-point hint into a proper isosbestic determination at no extra cost** —
worth noting in that spec so the run is designed with this use in mind.

### ⛔ 3.12 Q3 ANSWERED — we do NOT hold the free-base band positions

**The answer is no, and `KB_spectroscopy_physics.md` §4 already says so in its own words:**

> ⚠ **Not yet independently verified:** a primary measurement of *protopheophytin a*'s band positions.
> … the specific numbers for this molecule are not sourced here. Treat the mechanism as sound and the
> exact shifts as unquantified.

**What we DO hold** — and it is more than I expected:

| held | value |
|---|---|
| the pigment's identity and its Mg-free product | Fruhwirth & Hermetter 2007 §3.5 *(PDF on disk)* |
| protochlorophyll(ide) **Qy** | ≈ **623 nm** (80 % acetone) / **626 nm** (methanol) |
| protochlorophyll(ide) **Soret** | ≈ 440 nm |
| free-base **band count and ordering** | D₂ₕ ⇒ **four** Q bands I–IV; **band I weakest in every type**; protopheophytin expected **rhodo** (III > IV > II > I) |
| speciation range in this oil | protopheophytins **1.1–35.5 %** of protochlorophylls, rising with storage |

**What we do NOT hold: any position in nm for the four free-base bands.** Generic porphyrin values
cannot be substituted — free-base Q-band positions move tens of nm with the substituent pattern, which
is precisely why the etio/rhodo/oxo-rhodo/phyllo classification exists. **⇒ C7 stays blocked, and the
errand is a primary UV-Vis measurement of protopheophytin *a* in a named solvent.**

#### ⭐ One thing theory gives us for free — and it reframes §3.9

If the 574 nm peak were the **Q(1,0) vibronic satellite** of the 625 nm Qy(0,0) rather than an
independent electronic transition, the spacing would be

```math
\tilde\nu = \frac{10^7}{574} - \frac{10^7}{625} = 1422\ \mathrm{cm^{-1}}
  read: porphyrin Q-band vibronic spacing is typically 1200-1400 cm-1. 1422 sits just above that
  range -- consistent, not conclusive.
```

⇒ **If that assignment holds, §3.9's redundancy is not a coincidence but a requirement.** `M` and the
peak position would be reading two features of *one electronic transition*, which is exactly why they
correlate (*r* = +0.314) and why combining them added nothing. **It also means no amount of
recombination inside the Q region can produce an independent witness** — the independence would have to
come from a *different* transition, i.e. from resolving the free-base bands, i.e. from C7, i.e. from
Q3's errand.

⚠ Consistency is not proof: the assignment needs the same literature that C7 needs.

#### 3.12a The web search — what it did and did not find *(2026-08-04)*

⛔ **No primary UV-Vis of protopheophytin *a* is available on the open web.** Searches for the compound
by every name it goes under — *protopheophytin a*, *2,4-divinyl-protopheophytin a*, *divinyl
pheoporphyrin* — return the pumpkin-oil literature we already hold and nothing spectroscopic. The
errand therefore needs a **specialist source** (Scheer's *Chlorophylls* handbook, or a primary
synthesis/characterisation paper), not free web material. ⇒ It is a purchase or a library request.

⚠ **A trap avoided:** the abundant results are for **pheophytin *a***, which is a **chlorin** (bands
505 / 535 / 606 / ~665 nm). Our pigment is a **porphyrin** — that is the whole point of
`KB_spectroscopy_physics.md` §4.1's correction. Those numbers must not be borrowed.

⭐ **What the search did establish — the canonical free-base porphyrin pattern.** Protoporphyrin IX,
free base, the closest well-characterised relative:

| band | position | our window |
|---|---|---|
| **IV** | ≈ 506 nm | — |
| **III** | ≈ 532–542 nm | ⚠ **our "quiet" NEAR ANCHOR is 520–540** |
| **II** | ≈ 580 nm | our Q window 560–580, and the 574 nm peak |
| **I** *(weakest in every ordering)* | ≈ 630 nm | our FAR anchor 620–630 |

⚠ Not held; not citable until obtained. Recorded as a candidate source in §10.

#### ⚠ 3.12b The consequence worth acting on — the near anchor may not be quiet

**Free-base band III lands inside the 520–540 window the baseline treats as pigment-free** — and under
the **rhodo** ordering the KB expects for protopheophytin, band III is the **strongest** of the four.

Tested on our own data (brown minus greens, Soret-referenced, against a null from 6-vs-16 splits of
the 22 green runs):

| region | mean difference | null 95th | ratio |
|---|---|---|---|
| band IV ≈ 506 (500–512) | +0.0097 | 0.0196 | 0.50 |
| band III ≈ 532 (526–546) | +0.0175 | 0.0230 | 0.76 |
| ⚠ **our near anchor 520–540** | **+0.0186** | 0.0218 | **0.85** |
| **band II ≈ 580 (566–586)** | **+0.0439** | 0.0240 | **1.83 — SIGNIFICANT** |
| our Q window 560–580 | +0.0442 | 0.0247 | **1.79 — SIGNIFICANT** |
| band I ≈ 630 (620–629.8) | −0.0061 | 0.0261 | 0.23 |
| control 545–560 | +0.0177 | 0.0235 | 0.75 |

#### ⚠ 3.12c Followed up — the near-anchor band is NOT supported, but its LEVERAGE is the real finding

Two further tests, because §3.12b's +0.0186 was suggestive enough to chase.

**(i) Is there a band-shaped feature in the near window?** A band would bow the window above its own
chord. There *is* a bow, and it orders by class:

| oil | turbidity (A_near) | bow above chord, 515–550 | **bow ÷ turbidity** | bow peak |
|---|---|---|---|---|
| Kiendler | 0.0615 | +0.01312 | **0.2377** | 528.6 nm |
| Steirerkraft | 0.1106 | +0.01687 | **0.1534** | 529.1 nm |
| S-Budget *(brown)* | 0.1038 | **+0.02231** | **0.2171** | 528.8 nm |

⛔ **But the raw ordering is turbidity, not species.** Normalised by turbidity the ordering *breaks* —
**Kiendler, a green, has the highest ratio** — and greens vs brown gives *d* = 0.47, nowhere near
significance. Decisively, **the bow peaks at the same wavelength (528.6–529.1 nm) in all three oils**,
which is what chord-versus-convex-curve geometry produces, not a band that appears with demetallation.
Free-base band III is expected at 532–542 nm, not 528.8.

⇒ **No evidence of free-base band III in the near window.** §3.12b's hypothesis is not supported by our
own data, and should not be carried forward as though it were.

**(ii) ⭐ But chasing it exposed something that does matter — the leverage of each window on `M`:**

| window | dM per 1 A of error | a 0.01 A error moves `M` by | vs the 5.85-unit class gap |
|---|---|---|---|
| **NEAR anchor 520–540** | **+156.5** | **+1.57 (+9.5 %)** | **27 % of the gap** |
| FAR anchor 620–630 | +152.9 | +1.53 (+9.2 %) | 26 % |
| Q band 560–580 | −251.7 | −2.52 (−15.2 %) | 43 % |
| Soret 440–460 | +17.9 | +0.18 (+1.1 %) | 3 % |

⚠ **The near anchor has essentially the same leverage as the far one — and unlike the far one it has
never been tested.** `DOC_pedestal_correction.md`'s A6 discusses only the far window; §4.1 and §4.2 are
an entire investigation of the far window's cleanliness; the near window is asserted quiet in one line
(*"chosen to be quiet — little pigment"*) and examined nowhere. **The Soret band, by contrast, is
nearly immune — 9× less sensitive than either anchor.** All the fragility is in the small denominator
and the two windows that set its baseline.

⇒ **Recommended: state the near anchor's leverage in A6, and test it the moment R0b gives a
within-session brown/green pair.** Not because a band was found — none was — but because a 0.01 A
systematic there would eat a quarter of the discrimination and nothing on record would notice.

⇒ **The free-base pattern is NOT resolvable here.** The only significant difference is in the Q region
— which is the region the metric already reads. Bands III and IV are elevated in the right direction
but stay below the noise floor; band I is not elevated at all (consistent with it being weakest, and
therefore uninformative either way).

⚠ **But the near anchor's +0.0186 at ratio 0.85 is a risk worth carrying forward, not a finding to
dismiss.** If it is real, the 520–540 window carries pigment for demetallated oils, the baseline chord
is anchored on it, and the bias is **oil-dependent** — which is exactly assumption **A6** in
`DOC_pedestal_correction.md`, and a candidate contributor to that document's unexplained `r_Q`.
**⇒ Add to `DOC_pedestal_correction.md` ch. 10 as a named risk, and re-test it the moment a within-session
brown/green pair exists (R0b).**

---

## 4 · Best-practice catalogue

The knowledge base Edwin asked for. Each entry: what it is, what it is invariant to, what it costs.
**The incumbent is B1.**

### B1 — Band ratio *(incumbent)*
Two band amplitudes divided. **Invariant to** concentration and path length, provided both bands are
measured above a *correct* baseline. **Costs:** needs a baseline; any additive error in the smaller
band propagates as `error/B` (§5 of the pedestal document — the whole problem).

### B2 — ⭐ Derivative spectroscopy *(expanded in §5)*
Differentiate `A(λ)` with respect to λ. **Invariant to** additive backgrounds by *order*: a constant
offset vanishes in the 1st derivative, a **linear** background vanishes in the **2nd**. **Costs:**
amplifies noise; needs smoothing, which trades spectral resolution.

### B3 — Position and moment metrics
λ<sub>max</sub>, band centroid, first moment, the wavelength of a zero-crossing in a derivative.
**Invariant to** concentration *by construction* — a position is not an amplitude, so `A → kA` leaves
it untouched. **Costs:** needs a resolvable feature; says nothing about how much pigment is present.

### B4 — Shape metrics
FWHM, asymmetry, kurtosis, area-to-height ratio. **Invariant to** amplitude scaling. **Costs:** needs
the band to be *in range* — which for us is exactly what §3.1 says it is not.

### B5 — Whole-spectrum normalisation
SNV, vector norm, area normalisation, MSC/EMSC. Divide the spectrum by its own scale, then read any
feature. **Invariant to** multiplicative scaling exactly. **Costs:** SNV and area normalisation also
absorb *real* class differences if the classes differ in overall absorbance; EMSC needs a reference
spectrum.

### B6 — ⭐ Band decomposition / curve fitting
Fit a sum of Gaussian or Lorentzian bands with **positions constrained by theory** (§3.3), and use
ratios of fitted **areas**. **Invariant to** concentration in the ratio, and — crucially — **recovers a
peak from a flank**, which §3.1 says is our situation for *both* principal bands. **Costs:** a model
with parameters is a model that can be fitted wrongly; needs constraints to stay identifiable.

### B7 — Continuum removal
The remote-sensing standard: divide by the convex hull rather than subtract a chord. Band depth =
1 − A/A<sub>hull</sub>. **Invariant to** multiplicative scaling by construction. ⭐ **Being a division
rather than a subtraction, it cannot commit the `r_Q` error at all** — the failure mode this entire
document exists because of is structurally absent.

### B8 — Isosbestic referencing
If two species interconvert (**protochlorophyll ⇌ protopheophytin** — exactly our ageing axis), there
is a wavelength where absorbance is species-independent. Ratio against it. **Invariant to**
concentration *and* to the total-pigment axis simultaneously. **Costs:** the isosbestic point must
exist in range and be located — a real experiment, and an attractive one.

### B9 — Chemometric projections
PCA / PLS-DA on normalised spectra; use scores or score ratios. **Invariant to** whatever the
normalisation removed. **Costs:** ⛔ needs far more than 3 oils; and the project already abandoned an
LDA classifier once (`KB_spectroscopy_physics.md` §4). **Not recommended at this corpus size** — listed
for completeness.

---

## 5 · Derivative spectroscopy, in more detail

Edwin asked for this one specifically, and it is the candidate that would most completely dissolve the
problem.

### 5.1 What it does

Take the numerical derivative of absorbance with respect to wavelength, normally via a
**Savitzky–Golay** filter: fit a low-order polynomial in a sliding window and read its derivative
analytically at the centre. Two properties matter.

**(a) Additive backgrounds die by order.** If the measured curve is pigment plus background,

```math
A(\lambda) = A_{pigment}(\lambda) + P(\lambda)
```

then differentiating removes whatever part of `P` is polynomial of lower order:

| background | 1st derivative | 2nd derivative |
|---|---|---|
| constant offset | **gone** | gone |
| **straight line** *(= our chord, and any tilt)* | survives as a constant | **gone** |
| quadratic | survives | survives as a constant |

⭐ **This is the headline.** The shipped metric subtracts a straight chord and then spends a whole
document correcting the residue. **A second derivative annihilates any straight line exactly — no
anchors, no chord, no `r_Q`, no assumption A1.** The pedestal correction would not be *improved*; it
would be *unnecessary*.

**(b) Narrow features are enhanced over broad ones.** For a band of width `W`, the amplitude of the
nth derivative scales roughly as `1/Wⁿ`. A weak narrow band on a broad smooth pedestal therefore gains
against it by `(W_pedestal / W_band)ⁿ`. Our pedestal is very broad; the Q features are not.

### 5.2 What it costs

**Noise.** Differentiation multiplies high-frequency noise. Each order costs roughly another factor of
the noise-to-signal ratio at the smoothing scale. The remedy is the SG window: wider window ⇒ less
noise, more distortion of narrow features.

| our situation | verdict |
|---|---|
| **1305 bins at 0.146 nm** | ⭐ excellent — a 51-bin SG window is only ~7.5 nm, far narrower than any band here |
| blue-edge bins reading **2.0–2.6 DN** (§7 of the pedestal doc) | ⛔ derivatives are hopeless *there* |
| 560–580 nm, and 620–630 nm | good signal — this is where a derivative metric would live |

⇒ **A derivative metric is plausible in the green-to-red, and not in the deep blue.** Which points at a
metric built from the **Q region and the Qy flank** rather than from the Soret band — a different
metric from `M`, not a re-baselined `M`.

### 5.3 How a metric would be formed

Three shapes, in increasing ambition:

1. **Ratio of derivative amplitudes** at two fixed wavelengths — the direct analogue of `M`, with no
   baseline. *(This is candidate C1, and Edwin's far-window-slope idea is its 1st-order case.)*
2. **Peak-to-peak of the 2nd derivative** across a band — a standard pharmacopoeial construction,
   robust to where exactly the band centre sits.
3. **Zero-crossing wavelength** of the 1st or 2nd derivative — a *position*, hence class B3, hence
   dilution-invariant with no ratio needed at all.

---

## 6 · Evaluation protocol

A candidate is a function from a run's spectrum to one number. Every candidate gets the same three
scores on the same 28 runs.

### 6.1 The three scores

**S1 — Dilution invariance (primary).** Across preparations of the *same* oil:

```math
s = \frac{d \ln(\text{metric})}{d \ln c}
  read: the same dilution sensitivity DOC_metric_algebra.md §5.7 already defines, and that
  DOC_pedestal_correction.md ch. 9 uses. |s| = 0 is perfect. Report it for Kiendler (3 strengths)
  and Steirerkraft (2), separately, never pooled.
```

Also report the plain **spread across preparations**, as the pedestal document does (10.3 % → 3.0 %),
because it is what a reader understands.

**S2 — Class separation.** Cohen's *d* between the two greens and the brown, on the 28 runs.
`DOC_metric_algebra.md`'s Cohen's-*d* appendix already defines the convention.

**S3 — Re-seating stability.** Within-set CV. S-Budget's six re-seats of one fill are the cleanest
probe on the rig for this, and Kiendler A's 12.7 % internal scatter is the cautionary comparison.

### 6.2 ⭐ S1 and S2 must be read together, never apart

**A metric can be perfectly dilution-invariant by being blind.** A constant is invariant. §8.2 of the
pedestal document makes this argument in the other direction — invariance and sensitivity arrive
together — and it is the single easiest way for this research to fool itself.

⇒ **Report S1 and S2 as a pair for every candidate, and rank on the pair.** A candidate that improves
S1 while degrading S2 has not improved anything.

### ⭐ 6.3 The artifact contract — one accumulating JSON feature table

*(Edwin, 2026-08-04.)* Every quantity discovered during any evaluation must survive into the next one,
so nothing is recomputed and no past finding is lost. **The harness's output artifact is a JSON table,
not a printout.**

```
diagnostics/out/metric_features.json
{ "schema": 1,
  "runs": [ { "run": "20260801A/001", "set": "Kiendler A", "oil": "Kiendler",
              "session": "20260801",
              "features": { "B_Q": 0.0490, "M": 17.115, "qPeakNm": 574.13,
                            "qPeakA": 0.1017, "slopeFar": 0.00551,
                            "line473Nm": 473.054, ... } } ] }
```

**Rules that make it useful rather than a dump:**

1. **Append-only in spirit.** A new evaluation *adds* feature keys; it never removes or renames one.
   Renaming breaks every stored comparison — deprecate instead.
2. **One row per run, never per set.** Set- and oil-level statistics are *derived*, so aggregation can
   change later without re-reading 28 PDFs.
3. **Raw features only — no verdicts.** `M`, the corrected `M`, Cohen's *d* and the S1/S2/S3 scores are
   computed *from* the table, so a change of threshold or class roster (**Q6**) costs nothing.
4. **Provenance per row:** run, set, oil, **session** — the last because §3.4 makes session a
   first-class confounder every future analysis must be able to condition on.
5. ⭐ **Reloading is free.** Parsing the 28 PDFs is the slow part of every experiment here; with the
   table on disk a new candidate is scored in milliseconds.

⚠ **The table is a cache, not a source of truth.** It carries the git revision of the harness that
wrote it and is regenerated — never hand-edited — when the extraction changes.

### 6.4 ⚠ The overfitting trap, and the rule that avoids it

We are about to try many candidates on **28 runs and 3 oils**. Some candidate *will* look excellent by
chance. `DOC_pedestal_correction.md` §7 already documents this failure mode in its own history — the
3.0 % that turned out to be in-sample.

**Three rules, agreed before any code runs:**

1. **Pre-register.** The candidate list is fixed in §7 of this document *before* evaluation. Anything
   invented after seeing scores is labelled **post-hoc** and reported separately.
2. **Count the attempts.** Every reported result states how many candidates were scored. A best-of-20
   number is not a best-of-1 number.
3. **Prefer theory-anchored parameters.** A window placed by Gouterman (§3.3) is worth far more than a
   window placed by scanning for the best score. ⇒ **Window *scanning* is allowed only as a diagnostic,
   never as a result.**

---

## 7 · The idea pool *(pre-registered candidate list)*

| # | candidate | class | needs a baseline? | notes |
|---|---|---|---|---|
| **C1** | ~~flank-slope ratio~~ — `dA/dλ`(620–630) ÷ `dA/dλ`(Soret flank) | B2 | **no** | ⛔ **DEAD for the target** (Q6 = green vs brown): *d* = **0.05**. Parked — it scores 1.67 on green-vs-green, beating `M`'s 1.21, if that question is ever asked |
| **C2** | 2nd-derivative amplitude ratio, Soret flank vs Q | B2 | **no** | kills the chord exactly |
| **C3** | 2nd-derivative **peak-to-peak** across 560–580 | B2 | **no** | robust to band-centre placement |
| **C4** | zero-crossing wavelength of D1 near the Q band | B2+B3 | **no** | a *position* ⇒ invariant with no ratio |
| **C5** | Q-region **centroid / first moment** over 550–600 | B3 | weakly | reads the 572 nm shift directly |
| **C6** | **continuum removal**, band depth at Q ÷ band depth at Soret flank | B7 | replaced | division, not subtraction ⇒ `r_Q`'s failure mode absent |
| **C7** | **band decomposition** with Gouterman-constrained positions; ratio of fitted areas | B6 | replaced | the only class that *recovers the truncated peaks* (§3.1) |
| **C8** | **area ratio** — ∫ over Q region ÷ ∫ over Soret flank, on the raw curve | B1/B4 | yes | cheap control: does integrating instead of averaging help at all? |
| **C9** | **SNV / vector-normalised** spectrum, then C1's slopes | B5 | no | tests whether normalisation alone buys anything |
| **C10** | far-window **slope ÷ mean** — shape over amplitude, within one window | B2/B4 | **no** | the cheapest possible shape metric; a control for C1 |
| **C11** | incumbent `M` | B1 | yes | ⭐ **the baseline of the comparison — every score is relative to this** |
| **C12** | incumbent `M` **+ pedestal correction** | B1 | yes | the current proposal, scored on the same footing as its rivals |
| ⭐ **C16** | **Q-manifold ratio** — the ~574 nm band ÷ the far-red 620–630 band | B1 | ⭐ **NONE** | *Edwin, 2026-08-04.* ✅ **SCORED §7.2: the baseline-free form (V3) beats plain `M`, 10.44 vs 5.70**, direction confirmed (brown 1.617 vs greens 1.28/1.25). Every baselined variant scored 1.8–2.2 ⇒ **use no baseline** |
| **C17** | ~~570 as the near baseline anchor~~ | — | — | ⛔ **RULED OUT** (Edwin, 2026-08-04): 570 is the signal; anchoring the baseline there subtracts the thing being measured |
| **C18** | ~~S/F — Soret ÷ far-red Qy~~ | B1 | trough | ⛔ **DEAD, §7.5:** raw *d* = **0.20** (band ratio 7:1 ⇒ no pedestal cancellation), trough-anchored only 1.34. The *worst* of the three pairs, not the best |
| **C19** | ~~Q-region SHAPE~~ — FWHM, asymmetry, area, height÷width | B4 | **local chord** | ⛔ **DEAD, §7.5:** σ 14 %, skew 24 %, height/FWHM 32 % dilution spread — all worse than `M`'s 10.3 %; best *d* = 1.65. ⚠ Only the *position* is scale-protected; a width is not |
| **C20** | ~~D2(574) ÷ D2(625)~~ | B2 | NONE | ⛔ **DEAD, §7.7:** dilution spread **97.4 %**, the worst in this document. The far D2 term scatters 41 % against the Q term's 15 % — a flank has no curvature |
| **C21** | ~~smooth-background removal, then V3~~ | B5 | fitted | ⛔ **DEAD for V3, §7.6:** the hull tracks the Qy flank at **101 %** — it removes the band. V3's *d* falls 3.54 → 1.94. ⚠ Still worth running as the pedestal document's **T4**, for `M` |
| ⭐⭐ **C14** | **Q-peak position** — the sub-bin maximum of the 545–605 detrended band | B3 | **no** | ⭐ **§3.6 — the strongest lead.** Dilution-stable (0.26 nm over ×1.46), *d* = 4.57 vs brown, blue-shifts the right way. ⛔ Gated on §3.6a |
| **C15** | **Q-peak position + height together** — position for class, height for confidence | B3+B4 | **no** | the C13 hybrid in its cleanest form, once C14 is trusted |
| **C13** | ⭐ **hybrid** — a derivative feature in the red (where SNR is good) combined with an amplitude feature in the blue (where derivatives fail) | B1+B2 | partly | *Edwin, 2026-08-04.* §5.2 says derivatives die at the blue edge and amplitudes suffer at the red; a metric need not use one family throughout. **The natural pairing after §3.5(c): a 560–590 derivative feature over a Soret-flank amplitude** |

⚠ **C11 and C12 are not candidates, they are the yardstick.** No candidate is interesting unless it
beats both on the S1/S2 pair.

### ⭐ 7.1 · R3 — the whole-spectrum band map *(DESIGN, not started)*

*(Edwin, 2026-08-04: "divide the whole spectrum into bands and check how the bands change". Written
after two rubber-duck passes, both of which found design-killers — recorded below so they are not
re-invented.)*

#### Why this and why now

Every other lead is blocked on something external — **C7** on a book (Q3), **B8** on §16.11.17's decay
run, everything on **R0b**. This one is blocked on nothing: it uses data in hand, and §6.3's table makes
each new statistic nearly free.

It also attacks the one problem the pool could not get past. §3.9 found `M` and the Q-peak position read
the **same axis** (*r* = +0.314), so combining them bought nothing, and the conclusion was *"any real
gain needs a genuinely independent feature"* — without knowing **where to look**. ⭐ **The map is how you
look.**

#### ⚠ What it is, and what it must never become

| | |
|---|---|
| ✅ **a diagnostic map** — *where does class information sit, and does any of it lie outside what `M` already reads?* | the whole purpose |
| ⛔ **a search for the best band pair** | ~37 bands ⇒ ~700 ratios on 3 oils. A spectacular winner is **guaranteed** and would be noise. This is exactly §6.4 rule 3 |

Same computation, opposite epistemic status. **Pre-commitment: any band the map highlights becomes a
pre-registered candidate for FUTURE data — never a result on this corpus.**

#### The design, after both ducks

| step | decision | why |
|---|---|---|
| **bands** | 10 nm wide, 5 nm step, 440–630 nm ⇒ ≈ 37, deliberately overlapping | a smooth map; see the resolution caveat below |
| **input** | **normalised raw absorbance — no chord, no anchors** | ⚠ duck 1: baselined input imports the very assumptions we are escaping, incl. the near anchor's untested 156 A⁻¹ leverage (§3.12c). A second pass *on* baselined values is a separate diagnostic — what the chord does to the map |
| **normalisation** | **full-range area**, plus Soret-referenced with 440–460 excluded | ⚠ duck 1: Soret-referencing makes the first band **divide itself** — zero variance, *d* undefined, and the map's left edge is garbage exactly where the signal is |
| **statistic 1** | plain *d*(λ): greens vs brown per band | where signal is at all |
| **statistic 2** | ⭐ **incremental separation** √(D²(`M`, band) − *d*²(`M`)), Mahalanobis | ⛔ duck 1 killed the obvious version: regressing each band on `M` across **all** runs lets the fit absorb the class difference **by construction**, returning a flat null map. A false, confident negative |
| **statistic 3** | dilution sensitivity across Kiendler's 3 preparations | ⚠ ~2 df — report **direction and rank only**, never a precise number |
| **noise floor** | ⛔ **NOT a permutation null.** Use the **Kiendler-vs-Steirerkraft** contrast per band | ⚠ duck 2, §2.2: run-level permutation is pseudo-replication; oil-level permutation gives 3 labelings. The same-class oil pair is the only honest floor available |
| **artifacts** | excise 473 and 608 nm from the data and interpolate across, *before* band-averaging | keeps all 37 bands instead of punching two holes; the interpolation is itself an assumption and is flagged on the figure |
| **output** | 37 × 2 band means into the §6.3 table (74 new keys — append-only, checked) + one figure | makes every future band question instant instead of a re-parse |

#### ⚠ Four caveats that must travel with the figure

1. **The session confound is untouched.** The map shows where three *evenings* differ. A colourful map
   is far more seductive than a table, so this belongs **on the figure**, not in a footnote.
2. **Effective resolution ≈ 5, not 37.** The features are ~40 nm wide; adjacent 10 nm bands share most
   of their content. Reading a 5 nm peak off this map is over-reading.
3. **Scope is narrower than it looks.** Full-range area normalisation is Soret-dominated, so every band
   becomes ≈ *band ÷ Soret*. **The map answers "which partner band beats 560–580 as `M`'s denominator",
   not "where is class information".** Say so, or it will be over-claimed.
4. **A flat map does not close the file.** ⚠ *Retracting my own earlier claim that it would.* A null
   bounds the increment; it does not disprove one. **Report the detectable increment** — *"this map
   could have found an added separation of ≥ X and found none"* — which the noise floor gives for free.
   A quantitative bound is a result; "we found nothing" is not.

#### Deliverables

`diagnostics/metric_band_map.py` (extraction into the table) and a figure `metric_band_map.svg`:
*d*(λ) and the incremental separation, both drawn **with** the Kiendler-vs-Steirerkraft floor, the four
shipped windows marked, and the two lamp lines flagged.

### ⭐ 7.2 · C16 RESULT — the crude version works, the sophisticated ones do not

**Order corrected first.** Two pre-checks asked whether C16 was *buildable*; neither asked whether the
effect *existed*. The third rubber-duck caught that, and also withdrew my "not buildable on this range"
verdict as **asserted, not measured** — a derivative needs no red anchor, and the trough penalty had
never been quantified. Four variants, scored against the §2.2 bar (`M` = **5.70**):

| | construction | sep/dilut | *d* | *d*(K\|S) | **§2.2 ratio** |
|---|---|---|---|---|---|
| **V1** | both bands above the **trough chord** | 12.96 | 2.97 | 1.57 | 1.89 |
| **V2** | peak height ÷ far **slope** — anchor-free | 1.20 | 2.60 | 1.17 | 2.23 |
| ⭐ **V3** | **raw A(574) / A(625) — no baseline at all** | **4.19** | 3.54 | **0.34** | ⭐ **10.44** |
| **V4** | local-chord height ÷ trough-chord far band | 8.09 | 2.91 | 1.64 | 1.77 |

**⇒ Only V3 clears the bar — the variant written as the control, expected to fail.** Every construction
with a baseline scores 1.8–2.2; the one with no baseline scores **10.44**.

**Why it works, and it is not luck.** The two raw bands are **nearly equal in absorbance**:

| oil | A(566–582) | A(620–630) | **V3 ratio** |
|---|---|---|---|
| Kiendler *(green)* | 0.1635 | 0.1290 | 1.2824 ± 0.0685 |
| Steirerkraft *(green)* | 0.2313 | 0.1872 | 1.2506 ± 0.1102 |
| **S-Budget** *(brown)* | 0.2443 | 0.1525 | ⭐ **1.6173 ± 0.1238** |

A common additive pedestal added to two **nearly equal** numbers barely moves their ratio — a
first-order cancellation. That is why V3 survives dilution (sep/dilut **4.19**, better than `M`'s 3.51)
despite having no baseline, and it is the mechanism behind Edwin's "shorter lever" intuition, arriving
through *near-equality* rather than through proximity.

⭐ **And the direction is the predicted one.** Browning should *raise* Q(574)/Qy(625) — Qy weakens,
oscillator strength moves blue. The brown oil sits at **1.617** against the greens' 1.28 and 1.25.
**A pre-registered physical prediction, confirmed.**

**The trough penalty, now measured instead of asserted.** V1 (1.89) against V3 (10.44) prices it: the
class-dependent anchor costs about **5× on the §2.2 ratio**. My original worry was right in direction —
and I was right to distrust it while it was unmeasured.

#### ⚠ What V3 does NOT do

1. **It does not beat the leaders.** 10.44 against `M`+correction's **35.74** and the recalibrated
   Q peak's **22.03**. It beats plain `M`, nothing more.
2. **Its raw separation is weak** — *d* = 3.54 against `M`'s 6.91. It wins the *ratio* only because the
   two greens agree closely (*d*(K\|S) = 0.34), i.e. by a **small denominator**.
3. ⚠ **That denominator rests on one pair of green oils** (§2.2). A ratio whose denominator is 0.34
   with unknown error is unstable; this is the least robust number in the table, not the most.
4. ⚠ **The session confound is untouched.** V3 may be less *session*-sensitive rather than more
   *oil*-sensitive, and this corpus cannot separate those.

**⇒ Verdict: C16 is real, cheap, and worth carrying — as V3, the baseline-free form.** It is not a
replacement for `M`, and the sophisticated variants are dead. **The finding that generalises beyond
C16 is that every baseline construction tried here *injected* between-oil variance rather than removing
it** — the same lesson as §3.12c's leverage table, from a third direction.

### ⛔ 7.3 · The out-of-sample test — and what it did to the pedestal correction

Every score above comes from the same 28 post-rebuild runs, i.e. from conditions each construction was
built for. `diagnostics/prerebuild_outofsample.py` scores them on the **pre-rebuild archive** instead —
a different rig state, different oils, a different protocol, and ⭐ **the only place on disk where a
BROWN oil exists at two strengths** (oilN/oilM, 2 and 3 drops), which the main corpus cannot offer.

| candidate | post-rebuild *d* | pre-rebuild *d* | retained | green 2→3 drops | **brown 2→3 drops** |
|---|---|---|---|---|---|
| `M` shipped | 6.91 | 1.32 | 19 % | **−0.4 %** | +4.9 % |
| ⛔ `M` + pedestal corr | 9.61 | 1.22 | **13 %** | **+8.3 %** | **+9.6 %** |
| `M` re-centred | 7.16 | 1.33 | 19 % | −0.7 % | +3.9 % |
| V3 | 3.54 | 1.06 | 30 % | −4.5 % | +12.8 % |
| ⭐ Q-peak position | 3.87 | 1.18 | 30 % | **+0.1 %** | ⭐ **+0.0 %** |

An independent second pre-rebuild contrast (`20260727B/E` green vs `C/D` brown, 25 runs) agrees:
`M` re-centred **3.25**, `M` shipped **3.15**, `M`+correction **2.84**, V3 **2.12**, Q-peak 0.49.

**⛔ The pedestal correction fails out of sample, on three counts at once.** It retains the least
separation (13 %), it is **worse than doing nothing** on dilution (+8.3 % / +9.6 % against plain `M`'s
−0.4 % / +4.9 %), and it falls below plain `M` on the independent contrast. Its entire advantage —
§7's 10.3 % → 3.0 %, *d* 6.91 → 9.61, the §2.2 ratio of 35.7 — **is in-sample**, exactly as
`DOC_pedestal_correction.md` §7 warned and its chapter 9 predicted. ⭐ **This is the first time that has
been demonstrated on a BROWN oil rather than argued.**

⚠ **Read the *d* column with care, per Edwin (2026-08-04): only post-rebuild series really count.**
Pre-rebuild runs carry ~3× the seating noise, so every candidate collapses to *d* ≈ 1.1–1.3 and the
ceiling is the rig, not the metric. **The dilution columns are the durable result** — they are
within-oil, so seating noise cancels, and they are the only brown-oil dilution numbers in existence.

⭐ **An unexpected second finding: the Q-peak position is essentially PERFECTLY dilution-invariant** —
+0.1 % and +0.0 % across the green *and* brown pairs, where everything else moves 4–13 %. It measures
one thing extremely well, and that thing is not class (*d* = 0.49 on the strongest contrast).

### ⭐⭐ 7.4 · Where "a better V3" has to come from — the diagnosis, and four routes

*(Edwin, 2026-08-04: V3 is not preferred over the corrected metric as it stands, but it "has potential
that removes so much headaches". This section is what that potential is made of.)*

#### 7.4.1 Why V3 is weak, in one table

| oil | Q 566–582: signal fraction | far 620–630 | **Soret 440–460** |
|---|---|---|---|
| Kiendler | 43 % | 36 % | **100 %** |
| Steirerkraft | 37 % | 39 % | 96 % |
| S-Budget *(brown)* | 48 % | ⛔ **16 %** | 94 % |

**Both of V3's bands are ~⅓ pigment and ~⅔ pedestal.** The pedestal is smooth, so it carries no class
information — it simply **dilutes the contrast, by about 3×**.

⭐ **The same table explains `M`.** Its numerator is ~**100 % signal**: the Soret is so strong the
pedestal is negligible there. That is `M`'s real advantage — not a better idea, but a band where the
background does not matter. Every difficulty `M` has (the chord, `r_Q`, this whole document) lives in
its **denominator**, which is the same weak Q band V3 uses.

⇒ **V3 is not a worse idea than `M`. It is the same idea applied to two weak bands instead of one
strong and one weak.** Remove the pedestal and V3's contrast should roughly **triple**, while `M`
cannot benefit equally because its numerator has nothing to gain. **That asymmetry is the "potential".**

#### 7.4.2 ⛔ The gap Edwin's framing exposes — the third pair was never tested

Edwin's picture: `M` compares **blue vs green**; V3 compares **green vs red**. Three bands make three
pairs, and only two have been tried:

| pair | numerator | denominator | status |
|---|---|---|---|
| `M` | blue Soret | green Q | ✓ scored |
| V3 | green Q | red Qy | ✓ scored |
| ⭐ **C18 — "S/F"** | **blue Soret** | **red Qy** | ⛔ **never tested** |

**S/F may be the best of the three on paper**, because it combines both advantages: a numerator that is
~100 % signal (`M`'s strength) over a denominator carrying **the largest single class effect in the
data** — the far-red signal fraction is 36–39 % in the greens and collapses to **16 %** in the brown.
⚠ It inherits V3's pedestal problem on the denominator side, but not on the numerator side.

⚠ **Three bands give only TWO independent numbers**, since S/F = (S/Q)·(Q/F). So "take the Soret into
account as well" means a **2-D feature**, not a third scalar — and whether those two dimensions are
genuinely independent is §3.9's redundancy question, asked properly for the first time.

ℹ **On "use a mean rather than a single frequency": already done** — V3 is A(566–582)/A(620–630), both
window means. The real version of that instinct is that a flat window **clips** a band spanning
~545–605, so using *more* of it means the **0th moment (integrated area)** or intensity-weighted
moments — which is route A below. Edwin's two upgrades converge on the same place.

#### 7.4.3 The four routes

**The target, stated precisely: remove the pedestal from the Q-manifold bands WITHOUT assuming any
window is quiet.** That last clause is the whole point — the chord assumes 520–540 and 620–630 are
pigment-free, §3.12c showed one was never tested and §4.1 showed the other carries Qy, and every
headache in this programme traces to that assumption rather than to baselining as such.

| route | what it produces | strength | risk |
|---|---|---|---|
| ⭐⭐⭐ **A · Q-region SHAPE** — width, asymmetry, integrated area | reads the **band splitting** directly (2 bands → 4 on demetallation) | amplitude-free ⇒ pedestal-immune **and** concentration-invariant with no baseline possible; inherits the position's measured **+0.0 %** dilution invariance | the splitting may be unresolvable — §3.10 already failed to fit 2 Gaussians |
| ⭐⭐ **B · Derivatives** — D2(574)/D2(625) | pedestal removal **by physics** | annihilates any linear background exactly; suppresses broad ones by (W_ped/W_band)²; no quiet-window assumption | ⚠ 625 is a **flank at the range edge**, so its D2 is the weakest term. Untested: C2 tried Soret-vs-Q, never Q-vs-Qy |
| ⭐⭐ **C · Smooth-background removal** — polynomial / ALS over 500–630 | a **real** baseline assuming only **smoothness**, never quietness | the only route that attacks the §7.4.1 diagnosis head-on: remove the pedestal and V3's contrast should triple | ⚠ reintroduces a fitted object — more DOF, which is exactly what Edwin values V3 for avoiding. This is **T4**, still never priced |
| **D · C18 / three-band** | the untested pair, and the 2-D question | free; comes straight from Edwin's framing | may be redundant with `M` (§3.9) |

⭐ **Why route A is recommended first.** We have already measured the Q region's **first moment** and
found it *perfectly* dilution-invariant but weakly discriminating. **The second and third moments —
width and skew — have never been looked at, and the physics says the splitting shows up THERE, not in
the position.** We measured the one moment least likely to carry the signal.

**Proposed order:** D (nearly free, closes an obvious gap) → A (cheap, untested, physics-led) → C (the
one that could actually restore V3's contrast) → B (last: its weakest term sits at the range edge).

⚠ **One thing to decide before any of it: scalar or 2-D verdict?** If two features prove genuinely
independent, the honest metric may be a **pair**, not a number — and that changes what the plugin
shows, not just what the research concludes.

### ⛔ 7.5 · R4a + R4b RESULT — both routes fail, both as the rubber duck predicted

**Two design-stage predictions were made before the code ran, and both held.** Recording that, because
it is the first time in this research that a duck pass has *saved* the work rather than corrected it
after the fact.

#### R4a — C18, the third band pair (Soret ÷ far-red)

| variant | sep/dilut | *d* | **§2.2 ratio** | dilution spread |
|---|---|---|---|---|
| ⛔ **C18r** raw, no baseline | 0.11 | **0.20** | 0.16 | **34.0 %** |
| **C18** above the trough chord | 5.32 | 2.45 | 1.34 | **31.7 %** |

⛔ **Prediction confirmed: the raw form cannot work.** *d* = **0.20** — no separation whatever. V3
survives baseline-free only because its two bands are *nearly equal* (0.16 vs 0.13), so a common
pedestal cancels to first order. S/F is ~1.0 over ~0.15 — **a factor of 7** — so the same pedestal
moves the ratio by δ/0.15. That is precisely the `error/B` failure `DOC_pedestal_correction.md` §5 is
about, arriving in a candidate designed without it in mind.

⚠ **And my "may be the best of the three pairs on paper" was wrong** — it is the pair with the *worst*
pedestal asymmetry. Even trough-anchored it reaches only 1.34, below plain `M`'s 5.70. **C18 is dead**,
and with it the idea that the untested pair was an oversight worth much.

ℹ The three-band identity S/F = (S/Q)·(Q/F) is recorded as `c18_identity_residual` — exact under a
shared baseline, and it is; so **three bands genuinely give two numbers**, now measured rather than
asserted.

#### R4b — C19, Q-region shape

⚠ **Dilution first, per the duck: for a shape statistic that is the primary risk, not discrimination.**

| statistic | Kiendler 6 drops → 7 → 7 | **dilution spread** | *d* |
|---|---|---|---|
| C19s σ (2nd moment) | 8.128 → 7.055 → 7.106 | ⛔ **14.4 %** | 0.16 |
| C19w FWHM | 19.13 → 18.82 → 18.60 | **2.8 %** | 0.96 |
| C19k skew (3rd moment) | −0.266 → −0.217 → −0.279 | ⛔ **24.3 %** | 1.47 |
| C19h height ÷ FWHM | 0.0046 → 0.0064 → 0.0065 | ⛔ **32.3 %** | 1.65 |
| C19a area ÷ height | 20.48 → 19.04 → 19.03 | 7.4 % | 0.70 |
| *(for reference)* `M` | | 10.3 % | 6.91 |
| *(for reference)* **Q-peak POSITION** | | ⭐ **0.05 %** | 3.87 |

⛔ **Prediction confirmed: shape is NOT protected against dilution.** σ moves 14 %, skew 24 %, height ÷
FWHM 32 % — all **worse than `M`'s 10.3 %**, the metric they were meant to improve on. My claim that
C19 would "inherit the position's +0.0 % invariance" was a non-sequitur: a maximum's *location* is
invariant under scaling; a *width* is not, because the band top approaches saturation while the flanks
do not.

**And the discrimination is absent anyway.** The best shape statistic reaches *d* = 1.65 against `M`'s
6.91. **The band splitting is not resolvable as an envelope statistic** — consistent with §3.10, where
a 2-Gaussian fit could not resolve it either. Two independent methods now say the same thing.

⚠ FWHM is the one stable member (2.8 %) but carries almost no signal (*d* = 0.96). **Stability without
discrimination is §6.2's blindness trap**, not a result.

#### ⇒ What R4a and R4b together establish

**The Q region has exactly one usable degree of freedom, and we have already found it.** Position
(dilution-perfect, weakly discriminating), amplitude (the incumbent's denominator), and now shape
(neither) all read the same demetallation axis — §3.9's redundancy, confirmed a third time.

⇒ **Route A is closed and route D is closed.** Of §7.4.3's four routes only **C** (smooth-background
removal, = the pedestal document's T4) and **B** (derivatives) remain — and **C is the only one that
attacks §7.4.1's diagnosis directly.** It is now the last untried idea capable of making V3 competitive.

### ⛔ 7.6 · Route C — a smooth baseline EATS the Qy band. Prediction confirmed.

The rubber duck raised an objection that had gone unexamined through four turns of this document:
route C's selling point is *"it assumes only SMOOTHNESS, never QUIETNESS"* — but a smooth baseline
separates background from signal **by scale**, and **the Qy flank rises monotonically from ~610 nm to
the 629.8 cut-off with no turning point**, because its maximum is outside our range. To any smoothing
operator that is indistinguishable from a slowly-rising background.

`diagnostics/route_c_precheck.py` measures it. Fits are over the **full 440–630 nm** (the duck's other
fix: 500–630 is almost entirely band, and leans on the class-dependent trough), parameter-free first:

| method | baseline slope through 620–630 | **as % of the real flank** | far band left |
|---|---|---|---|
| **convex hull** *(0 params)* | +0.00651 | ⛔ **101 %** | 0.0144 A |
| polynomial order 3 | −0.01508 | −234 % | 0.3062 A |
| polynomial order 5 | −0.00809 | −126 % | 0.1173 A |
| polynomial order 7 | +0.00817 | ⛔ **127 %** | 0.0241 A |

⛔ **The convex hull tracks the flank at 101 % — it removes essentially the entire band.** Order 7
overshoots at 127 %. The low orders fail the other way, running *below* the data and leaving 0.31 A of
"band" that is mostly pedestal. **There is no setting that removes the pedestal and keeps the Qy band.**

**And V3 gets worse, not better:**

| baseline | V3 class *d* |
|---|---|
| **none (raw V3)** | **3.54** |
| convex hull | 1.94 |
| polynomial 3 | 2.41 |
| polynomial 5 | ⛔ **0.17** — the three oils land at 1.300 / 1.313 / 1.319 |
| polynomial 7 | 3.88 |

⚠ **I predicted the contrast would roughly TRIPLE. It halves**, or collapses entirely at order 5. Only
order 7 nominally improves, and that is not bankable: a 7th-order polynomial over 190 nm is flexible
enough to find it by accident, it still eats 127 % of the flank, and picking the best of four orders is
exactly §6.4's multiplicity problem.

⇒ **Route C is CLOSED for V3.** The selling point repeated four times in this document is **false for
this instrument** — not because smoothness is a bad assumption, but because V3's denominator is a
**truncated flank** rather than a resolved band.

⚠ **Route C remains worth running for T4**, which asks whether modelling the curvature beats correcting
its consequence for **`M`** — whose denominator *is* properly bracketed. Different question; this check
does not answer it.

### ⛔ 7.7 · Route B — derivatives. The last route, and it fails at the same place.

| candidate | sep/dilut | *d* | §2.2 ratio | **dilution spread** |
|---|---|---|---|---|
| **C20** D2(574) ÷ D2(625) | 0.69 | 1.65 | 1.33 | ⛔ **97.4 %** |
| C20f the far D2 term alone | 0.39 | 1.10 | 0.94 | — |

⛔ **A 97 % dilution spread is the worst number in this entire document.** The metric changes by a
factor of two across Kiendler's three preparations, which is not a metric.

**And the diagnosis is precisely the predicted one:**

| term | magnitude | **relative scatter over all 28 runs** |
|---|---|---|
| D2 at 574 nm *(a real peak)* | 0.001246 | **15 %** |
| ⛔ D2 at 625 nm *(the Qy flank)* | 0.001153 | **41 %** |

**The Q term is well behaved; the far term is nearly three times noisier.** A second derivative measures
*curvature*, and a flank has little curvature by definition — its peak is outside the range. The
denominator is a small difference of large numbers, and the ratio inherits all of it.

⇒ **Route B is closed, and it fails at the same place route C did: the far band is a truncated flank.**

### ⛔⭐ 7.8 · All four routes are now closed — and they all failed for ONE reason

| route | what closed it | §|
|---|---|---|
| **A** Q-region shape | shape is not dilution-protected; splitting unresolvable | 7.5 |
| **B** derivatives | the far D2 term is 3× noisier — a flank has no curvature | 7.7 |
| **C** smooth background | a smooth baseline cannot distinguish a monotonic flank from a rising background | 7.6 |
| **D** third band pair | 7:1 band asymmetry ⇒ no pedestal cancellation | 7.5 |
| **E** λ⁻ⁿ turbidity baseline *(added 2026-08-05)* | the far anchor **rises** toward the red, so no physical `n` exists | **7.14** |

**Three of the four died on the same fact: the Qy maximum lies beyond 629.8 nm, so the far band is a
truncated flank rather than a resolved band.** A flank has no peak to bracket (C16), no curvature to
differentiate (B), and no turning point for a smooth baseline to pass under (C).

⭐ **Route E, added 2026-08-05, dies on the SAME window from the other side** (§7.14.2): it needs a
scattering-only anchor, and the far window rises 2.3× toward the red instead of falling, so the power-law fit
has no admissible exponent at all. That makes five routes, and it is the cleanest disproof of assumption A6 in
this document because it rests on no metric comparison.

⇒ ⭐⭐ **This is no longer an analysis problem. It is 30 nm of missing spectrum.** Extending capture to
roughly **660 nm** — which `KB_spectroscopy_physics.md` §4.1 already anticipated (*"if Qy is at ~625,
the genuinely quiet region begins much earlier, ~660 nm+"*) — would at a stroke:

- give the Qy band a **resolved maximum**, making C16/V3 bracketable
- give it **curvature**, making route B viable
- give a smooth baseline a **turning point** to pass under, making route C viable
- and supply a genuinely **quiet region past 660 nm** — the first one this instrument would ever have,
  which is what assumption A6 has always lacked

**⇒ The single highest-value change available to this research is not a metric. It is the red end of
the capture range.** ⚠ Cost unknown: the S-mount optics roll off hard past ~630 and the lamp collapses
there (`SPEC_pumpkin_peak_ratio_eval.md` §2, `SPEC_capture_quality.md` §16.12.11 B) — so this is a
hardware question, and it may be expensive or impossible. **But it is now the question, and nothing in
the 28 runs can substitute for it.**

### ✅ 7.9 · T4 ANSWERED — the orthodox alternative is priced, and it is not affordable

`DOC_pedestal_correction.md` ch. 13's **T4** asks the one question that could make the pedestal
correction *unnecessary* rather than merely unproven: chapter 4 concludes the whole problem is
**curvature**, and the document then corrects the *consequence* rather than modelling the *cause*.
Would a curved baseline do the job properly? `diagnostics/t4_curved_baseline.py` prices it — same
shipped windows, same `M`, **only the baseline changes**.

⚠ This is not a repeat of §7.6, which ran these baselines for **V3** and found they ate the Qy flank.
`M`'s denominator is 560–580, a **properly bracketed** band with a maximum at ~574 nm and ground on
both sides. The methods that died on a flank might work on a real band.

| baseline | class *d* | dilution | chapter 6 residual |
|---|---|---|---|
| **chord (shipped)** | **6.91** | 10.3 % | YES — this is `r_Q` |
| chord + `r_Q` *(the proposal)* | 9.61 | 3.0 % | no |
| convex hull, 0 params | 2.15 | 16.6 % | ⛔ VOID |
| polynomial order 3 | 0.97 | 20.1 % | ⛔ VOID |
| polynomial order 5 | 0.25 | 10.1 % | ⛔ VOID |
| polynomial order 7 | 1.99 | 23.7 % | ⛔ VOID |

⇒ **T4's answer is no.** Every curved baseline collapses class separation from 6.91 to **0.25–2.15**,
and three of four make dilution *worse*. The orthodox alternative is more expensive and much worse on
this instrument. ⭐ **T4 can be marked done and closed** — and the recommendation to run it early (mine,
in Appendix D.6) was wrong.

#### ⛔ 7.9a A retraction, and the guard that now prevents it

**A first reading of this table drew a conclusion that was wrong, and it nearly went into the
documents.** The hull's chapter-6 intercept came out at +0.0003 (*t* = 0.08) against the chord's
+0.229 (*t* = 4.4), and I read that as *"a genuinely curved baseline leaves nothing behind — the first
independent confirmation that `r_Q` is the chord's straightness."*

⛔ **It is not.** I looked at the intercept and not at the **slope**:

| baseline | slope | intercept |
|---|---|---|
| chord | **12.435** | +0.2294 (*t* = 4.4) |
| convex hull | ⛔ **0.249** | +0.0003 (*t* = 0.08) |

**The slope fell 50-fold, because the hull removed the SORET band.** The Soret's maximum is at ~432 nm,
below our 440 nm edge, so it is a monotonic **flank** — and a hull hugging the data from below simply
follows it down. `B_Soret` collapsed from ~1.1 A to ~0.02 A.

**The intercept vanished because there was nothing left to carry one.** That is weighing nothing on a
scale and concluding the scale is unbiased.

⇒ **`r_Q`'s cause remains unexplained**, exactly as §4.1 leaves it — ~51 % unaccounted. Nothing here
changes that.

⚠ **The guard now in the script** flags any baseline whose `B_Soret`/`B_Q` slope lands far from the
chord's 12.44 as **⛔ VOID**: a construction that is not measuring the same two bands cannot have its
straight-line test read at all. **With the guard in place all four curved baselines are void** — none
of them even qualifies to answer the residual question.

#### ⭐ 7.9b And this is §7.8's wall a third time — from the BLUE end

§7.8 concluded that three routes died because the far band is a truncated flank. T4 adds the symmetric
half: **the Soret is a truncated flank too** (peak ~432, our edge 440). §3.1 stated this on day one —
*"both principal bands are flank-only"* — as a fact about what we can measure. It is now also a fact
about what we can **process**:

> **A whole-range smooth baseline is unusable on this instrument in principle**, because it has no
> peak-free region to anchor on at *either* end and will follow both flanks down.

⇒ The case for extending the red range (§7.8) is unchanged, and a blue-side note is added: the range is
clipped at **both** ends, and every processing route that needs a resolved band rather than a flank is
blocked by that and not by any choice of algorithm.

### ⛔ 7.10 · The last mathematical route — constrained band reconstruction. CLOSED.

*(Edwin, 2026-08-04: "is there no mathematical workaround?")*

**The identifiability argument, stated first.** On a flank the band and the pedestal are **both smooth
monotone functions of λ**, so the measured curve decomposes into (band + background) infinitely many
ways — the data cannot distinguish a steep band tail on a low background from a shallow one on a high
background. **A peak is what breaks the tie**, because it is a feature the background is assumed not to
have. That is why the 574 nm band separates cleanly and the two flanks do not, and it is one statement
covering all four routes of §7.8 and T4 of §7.9.

**The one route that could evade it** — and the only one never tried — is to import the missing
constraint from **theory**: fix the band centre at its literature position, fix the shape family, and
fit only amplitude and width. We hold the metalated positions (`KB_spectroscopy_physics.md` §4.1: Soret
≈432–440, Qy 623/626), so unlike **C7** — blocked on the *free-base* positions we do not hold (**Q3**) —
this is specifiable today. `diagnostics/constrained_band_fit.py` runs it.

⚠ **An expectation was recorded in the script before running** (ill-conditioned, because the curvature
that pins a width down is the noisiest thing we measure — §7.7's 41 %). The outcome was worse.

| band | amplitude | σ (nm) | corr(A, σ) | window-narrowing shift | class *d* |
|---|---|---|---|---|---|
| Soret 432 *(flank)* | 1.867 ± 0.178 | 12.3 ± 0.5 | ⚠ **+0.873** poor | −1 % / −6 % | 0.42 |
| ⛔ **Qy 625** *(flank)* | **0.0015 ± 0.0077** | **70.8 ± 25.0** | — | ⛔ **−100 %** | 0.24 |
| ⭐ Q 574 *(VISIBLE — control)* | 0.132 ± 0.025 | 8.0 ± 0.3 | ✅ +0.432 | +15 % / +14 % | 1.26 |

⛔ **The Qy fit COLLAPSED — the algorithm's own answer is "there is no band here".** Amplitude
**0.0015 ± 0.0077**, i.e. indistinguishable from zero with an error five times the value; σ = **70.8 nm
fitted inside a 19.8 nm window**, which the data cannot constrain; and narrowing the window moves the
amplitude by **−100 %**. The free linear background term absorbed the entire flank, leaving the
Gaussian nothing to do. **That is the identifiability argument, confirmed by the optimiser rather than
argued.**

⚠ **A guard was needed here too** — the third today. A *low* amplitude–width correlation was first
printed as "✅ identifiable", but a low correlation between two parameters of a band that does not
exist means nothing. The script now voids any fit whose amplitude is indistinguishable from zero or
whose σ exceeds half its window.

**The Soret flank fits stably (−1 %) but tells us nothing useful:** its amplitude is a *concentration*
proxy, so *d* = 0.42, and its amplitude–width correlation of **+0.873** says the two are largely
exchangeable anyway.

⭐ **And the control settles where the blame lies.** The identical procedure on the 574 nm band — the
one band we can see whole — is the only one that is identifiable (+0.432). **The method is not at
fault; the flank is.** ⚠ But note the control's own *d* = 1.26, far below `M`'s 6.91: even where band
reconstruction *works*, it is not a better metric than the incumbent.

#### ⇒ The door is closed, and the conclusion is now general

Every mathematical route has been tried and every one fails at the same place. **A "workaround" can only
import the missing constraint from somewhere, and there are exactly four somewheres:**

| source of the constraint | verdict |
|---|---|
| **more range** — extend to ~660 nm | ✅ the real fix; hardware, not analysis |
| **theory** — fixed centre and shape | ⛔ **tested here: the fit collapses** |
| **a second measurement** — blank, filtered sample, spike | chemistry/protocol; **untried** (the pedestal document's T3) |
| **an edge assumption** — "background is flat at 440 and 630" | untestable, and almost certainly false |

⇒ **The information is not hidden in the data awaiting a better algorithm. It is not in the data.**
No mathematics recovers what was never measured. The remaining routes are physical: **extend the red
range**, or **measure the pedestal separately**.

### ⛔ 7.11 · Fixed template, amplitude only, centre swept — the door is shut

§7.10's fit collapsed because **σ ran to 70.8 nm**: a Gaussian that wide is nearly flat across a 20 nm
window, which the free linear background absorbs. **The width was the escape hatch.** Closing it gives
the best-conditioned form the problem admits — a **one-parameter** linear least-squares fit of a fixed
template, σ taken from the *measured* 574 nm band (8.0 nm), with the centre **swept** rather than
assumed. `diagnostics/fixed_template_fit.py`.

| centre | amplitude | rel. error | fit RMS | class *d* |
|---|---|---|---|---|
| **623.0** *(lit., 80 % acetone)* | ⛔ **−0.0309** | 29 % | 0.00920 | 0.76 |
| 624.0 | ⛔ −0.0287 | 34 % | 0.00954 | 0.86 |
| **626.0** *(lit., methanol)* | ⛔ −0.0138 | 98 % | 0.01012 | 1.06 |
| 628.0 | 0.0855 | 36 % | 0.00932 | 0.79 |
| **630.0** | 0.2161 | 21 % | ⭐ **0.00429** | 0.12 |

⛔ **At every literature position the fitted amplitude is NEGATIVE** — physically impossible for an
absorption band. The data is not merely uninformative about a band at 623–626; **it actively rejects
one.** The residual keeps falling as the centre moves red, bottoming at **~630 nm**, i.e. at or past our
cut-off.

**And it fails every other test:**

| test | result |
|---|---|
| assumed width σ = 6 / 8 / 10 / 12 nm | amplitude **0.084 / 0.216 / 0.181 / −0.028** — a 2 nm change swings it 2.5× and flips the sign |
| narrower window 614–629.8 | amplitude −12 %, class *d* **0.12 → 0.93** (8×) |
| correlation with raw absorbance in the window | **+0.779** — it is largely tracking total absorbance |
| class separation | **0.12**, and the greens *straddle* the brown (0.189 / 0.241 vs 0.212) |

⇒ **Closed.** Fixing the width removed the specific escape hatch and the fit still cannot recover a
band, because the remaining freedom simply moved into the assumed width and the linear background.

#### ⚠ 7.11a A side-finding for `KB_spectroscopy_physics.md` — and it is NOT clean

Two independent observations say the same thing: **28/28 runs are still rising at 629.8 nm**, and a
template fit returns a **negative** amplitude at the literature positions while preferring ~630.

⇒ **Our spectra show no resolvable Qy maximum at 623–626 nm.** Three candidate explanations, and we
cannot separate them:

1. **Solvent/matrix shift.** The literature values are 80 % acetone and methanol; our sample is oil in
   IPA. A few nm is normal — but 5–7 nm is a large shift.
2. **Aggregation** in the lipid/alcohol matrix, which red-shifts porphyrin bands.
3. ⚠ **Instrument.** 620–630 nm is exactly where the lamp collapses (39 DN against 130 at 530,
   `SPEC_capture_quality.md` §16.12.11 B) and absorbance runs away. **A rising instrument artifact at
   the edge is indistinguishable from a red-shifted band edge** — which is the *same* identifiability
   failure, one level up.

⚠ §16.12.12 established at 5.1 σ that the 620–630 **rise** tracks oil class, so pigment is certainly
present there. That does not exclude a *mixture* of pigment and edge distortion, and nothing in our
range can decompose it.

**⇒ Record as an open discrepancy, not a correction.** The KB's 623/626 values are correctly sourced;
what is new is that **our instrument does not confirm them**, and cannot, at this range.

#### ⛔⭐ 7.12 · Every mathematical route is now closed

| route | §|
|---|---|
| Q-region shape (2nd/3rd moments) | 7.5 |
| third band pair (Soret ÷ far-red) | 7.5 |
| smooth whole-range baseline, for V3 | 7.6 |
| derivatives | 7.7 |
| smooth whole-range baseline, for `M` (**T4**) | 7.9 |
| constrained band fit, free width | 7.10 |
| fixed template, amplitude only, centre swept | 7.11 |

**Seven routes, one cause.** A workaround can only *import* the missing constraint, and of the four
possible sources exactly one remains untried:

| source | verdict |
|---|---|
| **more range** — capture to ~660 nm | ✅ the real fix. Hardware, not analysis |
| theory — fixed centre and/or width | ⛔ tested twice (§7.10, §7.11); collapses both ways |
| **a second measurement** — blank, filtered sample, spike | ⭐ **UNTRIED** — this is the pedestal document's **T3** |
| an edge assumption | untestable, almost certainly false |

⇒ **The information is not hidden in the data awaiting a better algorithm. It is not in the data.**
The two remaining routes are physical: **extend the red range**, or **measure the pedestal separately**
(T3 — downgraded in `DOC_pedestal_correction.md` because turbidity is ≤ 17 % of `r_Q`, but never
evaluated as a way to obtain an *independent measurement of the background*, which is what every failed
route above actually lacked).

### ⭐⭐ 7.13 · The Soret window carries dead bins — and a quarter of `r_Q` is the camera, not the baseline

*(2026-08-04, prompted by Edwin's DN-guard proposal.)*

#### 7.13.1 The observation that started it

`DOC_pedestal_correction.md` §7 states plainly:

> *"At today's recipe the **440–447 nm bins already read 2.0–2.6 DN** against a reference near 88 —
> they are dark, and previous work established **they are not measurements**."*

**Those bins are inside the shipped Soret window (440–460).** Roughly a third of `M`'s numerator
window is contributed by bins the project had already written off — for every oil, in every run.

#### 7.13.2 What the numbers do when they are removed

Same metric, same Q window, same chord — **only the Soret window changes**:

| Soret window | class *d* | within-green *d* | dilution spread | `B_Soret` |
|---|---|---|---|---|
| **440–460** *(shipped)* | 6.91 | 1.21 | 10.3 % | 1.0272 |
| 444–460 | 7.27 | 1.29 | 9.2 % | 0.8517 |
| ⭐ **448–460** *(drops the non-measurements)* | **7.37** | **1.34** | **8.8 %** | 0.6924 |
| 450–462 | 7.31 | 1.37 | 8.7 % | 0.5735 |

⚠ **All three axes improve, and none of it changes what the instrument can do.** +6.7 % on class
separation (already far above any decision threshold), +10.7 % on the within-green task (still *d* ≈
1.3, where individual classification needs ≳ 3), −14.6 % on dilution spread (preparation noise still
exceeds the green-green signal). **Real, free, and modest.** The capillary attacks the dilution axis an
order of magnitude harder.

#### 7.13.3 ⭐ The substantive result — the anomaly shrinks

| Soret window | intercept `k` | ***t*(k)** | `r_Q` |
|---|---|---|---|
| **440–460** *(shipped)* | 0.2294 | **4.43** | **−0.0184** |
| 444–460 | 0.1620 | 3.45 | −0.0149 |
| ⭐ **448–460** | **0.1214** | **2.92** | **−0.0133** |
| 450–462 | 0.0962 | 2.66 | −0.0126 |

⇒ **Deleting 8 nm of bins removes 47 % of the intercept and 28 % of `r_Q`, and drops the anomaly's
significance from *t* = 4.43 to 2.92.**

**The control that rules out mere rescaling.** Trimming shrinks `B_Soret` by a factor 0.674. If it only
rescaled, slope and intercept would both scale by 0.674:

| | predicted by rescaling | observed | |
|---|---|---|---|
| slope | 8.383 | **9.101** | +8.6 % |
| intercept | 0.1547 | **0.1214** | ⭐ **−21.5 %** |

**The intercept fell 21.5 % further than rescaling explains.** The relationship changed, not the units.

#### 7.13.4 The mechanism, from the bottom

A measurement is two captures: **R**, the reference (solvent only) ≈ **88 counts** at 440–447 nm, and
**S**, the sample ≈ **2.0–2.6 counts** there. $A = \log_{10}(R/S)$.

**A camera never reads true zero** — dark offset plus stray light add junk counts. Call it +1:

| true S | measured S | true A | measured A | error |
|---|---|---|---|---|
| 2 | 3 | 1.64 | 1.47 | **−0.17** |
| 30 | 31 | 0.47 | 0.45 | −0.014 |

The same junk costs **twelve times more** at the dark end — which is why the **16 DN guard** exists
(`SPEC_capture_quality.md` §16.7.2e, target band 20–40 DN). And the error is always **negative**: junk
adds counts, so A reads too low.

**Now the same oil at two strengths, at 445 nm:**

| preparation | true S | measured | true A | measured A | under-read by |
|---|---|---|---|---|---|
| dilute | 3.5 | 4.5 | 1.40 | 1.29 | 0.11 |
| concentrated | 2.3 | 3.3 | 1.58 | 1.43 | **0.15** |

**The stronger preparation is darker, so the junk is a larger fraction of it, so it is under-read
more.** True A grew ×1.13; measured A grew only ×1.11.

⇒ The Q band (560–580, healthy counts) grows honestly; the Soret band is **compressed, and compressed
more at the strong end**. So the points of chapter 6's straight-line test **bend downward** at high
`B_Q` — and a straight line fitted to a downward-bending curve **must cross the y-axis above zero**.

**That crossing is `k`. Divide by the slope and you have `r_Q`.**

#### 7.13.5 ⇒ This is assumption A4, and the document predicted it

`DOC_pedestal_correction.md` ch. 10, **A4**:

> *"Beer–Lambert holds in both bands — absorbance is proportional to concentration, with no
> saturation… **stray light in a saturated band compresses absorbance, which would appear as a
> concentration-dependent error of its own.**"*

⭐ **The mechanism was named years' worth of pages ago and never measured.** What is new here is the
size: **28 % of `r_Q`.**

**And it explains why no chapter found it.** `r_Q`'s cause was hunted twice, both times on the
**denominator** side — §4.1 asked whether the *background under the green band* is curved enough
(≤ 17 %), §4.2 asked whether the baseline's *red foot* is contaminated (~32 %, then refuted). Both ask
*"what is wrong with the baseline near the green band?"* **This defect is in the blue band and it is a
camera problem, not a baseline problem.** Examining the baseline could never have found it.

⚠ **Not additive with §4.1's percentages** — those were computed on the 600–630 anchor with `r_Q` =
−0.0246, this on the shipped 620–630 anchor with −0.0184.

#### 7.13.6 What is not explained, and what follows

⚠ **After trimming, *t* = 2.92 — still significant at 8 df.** So **~72 % of `r_Q` survives** and remains
unaccounted for. The dead bins are a contributor, not the cause.

⚠ **Is this window scanning (§6.4 rule 3)?** The 448 boundary was fixed **before looking**, from the
document's own statement about 440–447. And the effect is **monotone** across all four windows — a
fitted artifact spikes at one point; a real one trends. The window centroid moves 4 nm, worth ~0.0035 A
against a 0.108 A change in `k`.

**⇒ Two recommendations.**

1. **Trim the shipped Soret window to 448–460.** Free on all three axes, justified by an existing
   documented fact rather than a scan. ⚠ `B_Soret` drops 1.03 → 0.69, so the metric's scale changes and
   any threshold must be re-derived.
2. ⭐ **The capture-side fix matters more.** Edwin's **DN guard** plus **capillary dosing to a common
   optical density** attack this at source: a fixed target OD means every oil presents the same `S`, so
   the guard and the OD target become **one constraint**, and the differential compression between
   classes disappears rather than being corrected.

---

### ⛔⭐ 7.14 · EXTERNAL-LITERATURE AUDIT — the orthodox scatter corrections, priced against our window  *(Edwin 2026-08-05: "that's a real, standard technique … make a web research on this and tell me what and how we could use this")*

Tool: **`diagnostics/scatter_correction_audit.py`** (reproduces every number below).
Prompted by a proposal of Edwin's that turned out to be single-point baseline anchoring
(`SPEC_capture_quality.md` §16.24.9 — proved a no-op on `M`). The question behind it is fair and had never
been asked head-on: **the wider spectroscopy community has standard machinery for removing a scattering
pedestal. Why are we not using it?** This section prices each named method against our actual window.

⚠ **This section CONFIRMS §7.8, it does not extend it.** The conclusion below was already reached there from
the inside; what is new is (a) the naming of the incumbent, (b) a **fifth** closed route with a sharper
diagnostic than the other four, and (c) the fact that the *literature's own prerequisites* independently
select the same fix. Treat it as corroboration from a second direction, not as a new finding.

#### 7.14.1 ⭐ The incumbent has a NAME, and it is the pharmacopoeial standard

| method | model assumed | what it requires |
|---|---|---|
| **Morton–Stubbs / Allen correction** | irrelevant absorption is **linear** across the band, corrected from flanking points | flanking points free of analyte |
| **Dual-wavelength (Chance)** | difference of λ_sample and λ_ref cancels scatter | a λ where the analyte does not absorb |
| **λ⁻ⁿ turbidity baseline** | scattering is a power law, n ≈ 4 (Rayleigh) → 2 (Mie) | a **scattering-only** window to fit `n` |
| **EMSC** | `x = Σᵢcᵢλⁱ + m·x_ref + Σⱼgⱼzⱼ + ε`; `x_corr = (x − baseline − interferents)/m` | a reference spectrum **and a training set** |
| **2nd derivative** | annihilates any locally-quadratic baseline exactly | resolved peaks with real curvature |

⭐ **Our shipped two-window linear baseline IS the Morton–Stubbs correction** — linear irrelevant absorption
removed from two flanking anchors, the same construction used for vitamin A in liver oils and, as the Allen
variant, for serum haemoglobin against bilirubin and turbidity. ⇒ **The incumbent is not a naive choice that
the literature would improve on; it is the textbook method.** Worth stating plainly, because §16.10.2 argues
for it from first principles and never noted that it has a century-old name.

#### ⛔ 7.14.2 ROUTE E — the λ⁻ⁿ power-law baseline. Closed, with the sharpest diagnostic in §7.

Physics-matched and already coded (`settling_sweep.powerLawBaseline`), so it cost nothing to test. Fitted
through the SHIPPED anchors, against the shipped linear baseline:

| set | n | LINEAR mean / CV | POWER-LAW mean / CV | `n` fitted |
|---|---|---|---|---|
| 20260804A controls | 4 | 17.465 / **0.69 %** | 16.043 / 1.21 % | **−4.00** |
| Steirerkraft B green | 6 | 15.619 / 3.58 % | 14.549 / 5.39 % | −3.37 |
| Steirerkraft C green | 6 | 15.499 / 4.61 % | 14.566 / 4.03 % | −3.07 |
| Kiendler A green | 6 | 17.115 / 4.99 % | 16.026 / 4.86 % | **−4.00** |
| S-Budget D brown | 6 | 10.160 / 1.94 % | 9.949 / **1.36 %** | −2.36 |

**Class separation: Cohen *d* 6.60 → 5.88.** No improvement on the two artifact runs either
(`20260804A` 002 −13.5 % → −13.7 %; 006 −8.8 % → −10.2 %).

⭐⭐ **But the number that matters is `n`, which RAILS AT THE −4 BOUND.** The reason is one line of data,
and it holds on **every set in the corpus, both classes, both rig states**:

| set | near 520–540 | far 620–630 | **far/near** |
|---|---|---|---|
| 20260804A ctrl | 0.0365 | 0.0891 | **2.44** |
| Steirerkraft B | 0.0981 | 0.1716 | **1.75** |
| Steirerkraft C | 0.1231 | 0.2035 | **1.65** |
| Kiendler A | 0.0378 | 0.0947 | **2.50** |
| S-Budget D *(brown)* | 0.1038 | 0.1526 | **1.47** |

**Scattering MUST fall toward the red** (λ⁻ⁿ with n > 0). **Ours rises, on all five sets.** No physical
exponent can fit that, so `curve_fit` runs to its bound and returns a curve bending the wrong way. ⇒ **Our far
window is not a turbidity window — it is the Qy flank**, which §16.12.12 kept deliberately *because* it
carries pigment. The two purposes are mutually exclusive and one window cannot serve both.

⚠ **Note the brown set is the least extreme (1.47) and still rises.** So this is not a green-oil artifact; it
is the instrument's window, and no oil in the archive escapes it.

⚠ **This is the cleanest available proof that assumption A6 (a quiet far anchor) is FALSE on this instrument** —
sharper than the four routes of §7.8, because it does not rest on a metric comparison at all: the fit simply
has no admissible solution.

#### 7.14.3 The other three, priced

- **2nd derivative** — re-run as a `|d²A|` band ratio: green 5.573 ± 2.051 vs brown 4.854 ± 1.085,
  **Cohen *d* = 0.38, classes OVERLAP**, CV 16–24 % per set. ⇒ **reproduces §7.7's route-B result from a
  different formulation.** A flank has no curvature; differentiating removes the baseline and the signal
  together.
- **Dual-wavelength (Chance)** — designed to track *changes* in one turbid suspension against a
  non-absorbing reference λ. Our two-window baseline already generalises it, and it needs the same
  non-absorbing λ we do not have.
- **EMSC** — the most powerful of the family, and the least applicable. It needs a **reference spectrum and a
  training set**, which would put fitted, data-derived components inside a **sealed, signed plugin**
  (`SPEC_plugin_distribution.md`) — a provenance problem as much as a science one. And its polynomial
  baseline term needs a **third** anchor window to be determined at all, which is the same blocker again.

#### ⇒ ⭐⭐ 7.14.4 Every method is gated by the SAME missing 30 nm

Each orthodox correction needs one of exactly two things, and our window supplies neither:

| requirement | needed by | do we have it? |
|---|---|---|
| an **absorption-free region** | λ⁻ⁿ, Allen/Morton–Stubbs, dual-wavelength | ⛔ no — 440–629.8 nm is pigment everywhere |
| a **resolved peak with curvature** | 2nd derivative, EMSC, band fitting | ⛔ no — both bands are flank-only |

⇒ **This is §7.8's conclusion arrived at from outside.** §7.8 closed four internal routes and concluded *"this
is no longer an analysis problem, it is 30 nm of missing spectrum"*; the external literature turns out to
require **precisely the same 30 nm**, for its own independent reasons. Two disjoint lines of argument now
select the same fix.

⚠ **Nothing here is newly actionable without the window.** The one deliverable available today is
documentary: §7.14.1's naming of the incumbent, which means the shipped baseline needs **defending less**,
not more — a reviewer asking *"why not use a proper scatter correction?"* can be answered *"we do; it is
Morton–Stubbs, and the alternatives need a quiet region this instrument does not have."*

⚠ **Cost caveat unchanged from §7.8:** the S-mount optics roll off past ~630 nm and the lamp collapses there,
so the red extension remains a **hardware** question that may be expensive or impossible. This section raises
its value; it does not lower its price.

#### ⭐⭐ 7.14.5 THE REOPENING CONDITION — and half the cost caveat is now REFUTED *(2026-08-06)*

⛔ **"The S-mount optics roll off past ~630 nm" is WRONG.** It was an assumption and it has been measured:
`KB_spectroscopy_physics.md` §7.2, from a CFL frame with its own wavelength solution (Hg 435.83 / 546.07,
0.7 nm residuals) — **response to ~680 nm, and the Eu³⁺ 650.7 nm line resolves as a genuine peak** (+25 % above
a fitted continuum, ~4 nm wide). ⇒ **The blocker was never the optics. It is the lamp**, which is a thing that
can be specified rather than discovered.

⭐ **The acceptance criterion is one number.** §7.14.2 closed the λ⁻ⁿ route because the far anchor reads MORE
than the near one — 1.47 to 2.50 on all five sets — which no physical exponent can fit. Scattering must fall
toward the red. So the test of whether a new far window is genuinely quiet is:

> **`far/near` = mean raw `A`(660–680) ÷ mean raw `A`(520–540)** — ⚠ on RAW absorbance, since the baseline is
> fitted *through* those anchors and a corrected spectrum is ≈ 0 in both by construction.

| result | reading |
|---|---|
| **0.39 – 0.63** | ⭐ consistent with real scattering (Rayleigh n≈4 → Mie n≈2) — a true turbidity window |
| **< 1 but higher** | partly quiet; some Qy tail still reaching in. Map where it becomes clean |
| **> 1** | ⛔ something else absorbs at 660–680 and this whole thread closes |

⇒ **What a quiet window buys, in order of confidence:** (1) ⭐⭐ **620–630 is freed from anchor duty to become a
third signal band** — §16.12.12 measured it tracking oil class at **5.1 σ**, information currently spent as
background, and this needs no new method at all; (2) Morton–Stubbs (§7.14.1: *we already use it*) stops
violating its own "flanking points free of analyte" precondition; (3) λ⁻ⁿ becomes fittable with a physical `n`;
(4) the pedestal is **measured** rather than inferred from an intercept whose ~72 % remains unexplained
(§7.13.6); (5) dual-wavelength becomes possible at all.

⚠ **The two requirements in §7.14.4's table are INDEPENDENT, and this matters.** Even if 660–680 is *not*
quiet, extending the range still delivers the second one — a **resolved peak with curvature**, which the
derivative/EMSC/band-fitting family needs. Measured 2026-08-06: a quadratic fit over 606–626 nm is **convex on
every archive fill**, so **the Qy maximum has never been observed**; it lies beyond 630. ⚠ That test needed a
control — the *null* runs are concave there and would have faked a peak at 623–625 nm, matching the literature
almost exactly. Without the null control this section would have reported a false confirmation.

⚠ **The blue side stays unsolved either way.** Morton–Stubbs wants clean points on *both* flanks; 520–540
remains a trough between the Soret tail and the Q band, and below the Soret there is only more Soret.

### ⛔ 7.15 · PEAK-VALUE METRICS — tested on the two peaks we can reach, and they LOSE *(Edwin 2026-08-06: "wouldn't the 3 peak values give good values to make a metric from?")*

The pigment offers three features — Soret ~432, Q ~574, Qy ~625 (`KB_spectroscopy_physics.md` §4.1a). Two of
them are inside today's range, so the idea is directly testable without any hardware change.

| candidate | class *d* | within-green *d* | dilution spread |
|---|---|---|---|
| `A(574)/A(625)` — peak ratio | 3.32 | 1.30 | −8.8 % |
| `A(574) − A(625)` — peak difference | 6.64 | 1.68 | ⛔ **−69.0 %** |
| **`M` shipped** (baselined bands) | **6.96** | **2.01** | **+3.0 %** |

⛔ **Worse on every axis.** Two reasons, and both generalise:

**1 · The shipped metric's power is the BASELINE, not the window positions.** Both peaks sit on a large
scattering pedestal — §16.24 measured it at **62 % of the raw Q band**. A raw ratio carries it straight into
the answer; a *difference* of absorbances is proportional to concentration by construction, which is exactly
the −69 % for a 2× dilution. ⇒ A peaks-only design does not escape the baseline machinery, it just loses the
correction and still needs anchors in quiet regions.

**2 · ⭐ A peak is where the sample transmits LEAST.**

| | `A` | `T` | |
|---|---|---|---|
| 448–460 *(shipped window)* | ≈ 0.66 | 22 % | ⭐ near the classical photometric optimum (~0.4–1.0) |
| 440–447 | ≈ 1.46 | 3 % | the dead bins of §7.13 |
| 432 *(Soret peak)* | ≳ 2 | ≲ 1 % | relative photometric error blows up |

⇒ **The flank is not only a compromise forced by the lamp — it is also the best-conditioned place to measure.**
Moving onto the Soret peak would put the measurement where the signal is weakest, which is the regime that
produced the dead bins in the first place.

⚠ **What this does NOT refute.** It says nothing about **432 nm**, the one peak never measured, and the Soret
is the strongest band. And it tested peak *values*, which is the weaker target: §3.6 already found that the Q
band's peak **POSITION** carries the class. A resolved band offers position, width and asymmetry; a flank
offers only height. ⇒ **The case for extending the range stands, but its justification changes** — not "peak
values make a better metric", which is now tested and false, but "a whole band offers shape parameters a flank
cannot".

⚠ n = 4 fills, one brown, dilution from a single half-strength pair. Enough to reject these two candidates; not
enough to reject peak-based metrics as a family.

### ⭐⭐ 7.16 · HARDENING `M448` — what it actually measures, measured  *(Edwin's session, 2026-08-10)*

Not a new candidate. A session spent asking what the shipped metric computes, prompted by Edwin being able to
**see** the baseline for the first time (the plot now draws the fitted line, both curves and the four band
means). Five results, all on archived data, no rig time. Full write-ups in `DOC_metric_algebra.md` §5.3d,
§5.3e and §5.6a; this is the index.

**① The tilt is worth 1 % at the Soret and 45 % at Q.** The two classes' baselines nearly coincide in the blue
and fan apart toward the red, because the near anchors agree and the far anchors do not. So the same tilt that
the numerator hardly notices *is* the denominator. ⇒ §5.3a's "the long lever costs about one per cent",
argued from geometry in 2026-07, is now measured at exactly 1 %.
⚠ The crossing wavelength is **not** a constant — 473 nm for two set means, 518 nm for a single-run pair.

**② The extrapolation is not load-bearing** (`diagnostics/soret_extrapolation_test.py`). Rebuild the numerator
with a flat offset at the near anchor — no line drawn where nothing was measured — and class *d* falls
**10.25 → 9.35 (−8.8 %)**, within-green *d* **1.34 → 1.31**, and the empty corridor keeps its relative width
(28 % of the green mean against 29 %). Remove the tilt under **Q** instead and *d* collapses **76 %**. ⇒ the
questionable half contributes almost nothing; the legitimate half (interpolation between two measured
anchors) carries everything.
⭐ **And the flat numerator is *better* on dilution: +0.1 % against +3.0 %** on the same oil at half strength.
⚠ One fill pair — suggestive, not established. Belongs with the threshold freeze, not with a second rescaling
of a metric whose thresholds were re-derived the same week.

**③ The numerator is a load reference, not a pigment band.** Across four commercial oils at matched dose,
`A_S` moves **±5 % with no ordering** while `M448` spans 1.5×, and the brownest oil reads *highest* in the
blue (r = −0.41 against the verdict). If 448–460 were the pigment's Soret, demetallation would cost it
53–87 %. ⇒ the tetrapyrrole is a minority tenant; carotenoids, browning products and scatter own the window,
and three effects pointing two ways is why it lands flat (`KB_spectroscopy_physics.md` §4.2).
⭐ That is *why* the ratio is dilution-invariant — and it means **"Soret ÷ Q" names the windows, not the
chemistry**. What it computes is **pigment degradation per unit chromophore load, inverted** (so a bigger
number is greener; `1/M448` is §16.27.5's concentration-free column). ⇒ `DOC_metric_algebra.md` §5.6b
carries the phrasing for four audiences — bench, colleague, laboratory and miller — of which the
miller's is the test of whether we understand it: **"how brown the pigment has gone, per litre of oil in
the beam"**. ⛔ None of them may say "chlorophyll content".
⚠ Empirically validated and mechanistically explained, **not** guaranteed; bounded at **4:1** against the class
signal meanwhile. Widening the oil panel tests it for free.

**④ Two Cohen's *d*s were being quoted as one, and they answer different questions.** This caused a real
confusion mid-session and is worth pinning:

| question | pairs | error term | *d* |
|---|---|---|---|
| across quality classes | Steirerkraft 9.96 vs S-Budget 6.51 *(12–53 % apart)* | within-fill | **4.1 – 15.6** |
| within the green class | Steirerkraft 10.36 vs Kiendler 11.08 *(7 % apart)* | fill-to-fill | **1.5 – 1.7** |

Both are true. The four-oil session's *d* = 4.09–15.57 is mostly *green versus brown*; "within-green *d* =
1.34" is two premium greens seven per cent apart, measured across preparations. ⇒ **always state which pair
and which error term**, or the same metric appears to pass and fail at once.

**⑤ Green-vs-green on the capillary session separates** — the three g.g.A. oils of 2026-08-07 give *d* = 4.09,
6.02 and 8.23 on gaps of 13.7 %, 13.8 % and 29.5 %. ⚠ The error term there is **three measurements of one
tube**, so this is an upper bound. Sensitivity to what a fresh preparation costs:

| assumed preparation CV → | 0.2 % | 1.0 % | 2.5 % | 4.5 % |
|---|---|---|---|---|
| *d* for a 13.7 % gap | 68.6 | 13.7 | 5.5 | **3.0** |
| *d* for a 7 % gap | 35 | 7.0 | 2.8 | 1.6 |

⇒ **even at the §16.26 reseat rms of 4.5 %, a 14 % gap still reaches *d* = 3.0.** The measurement that settles
it is the one the oil-panel document already names: **three tubes per oil at one dose**, one evening.

⇒ **Net effect on the programme.** Nothing here changes a shipped number. What changed is the account of *why*
the number works, and three claims that were argued are now measured. The one open risk it names —
an accidental normaliser — is bounded, testable by widening the panel, and points the right way.

## 8 · Open questions for Edwin

**Q1 — the window remark. ✅ ANSWERED (Edwin, 2026-08-04): "the rightest Q-band (the 620-630)".**
So: the Soret window and the 620–630 Qy window stay; **520–540 and 560–580 are the movable ones**.
⭐ §3.5(c) independently points at the same place — the curves fan at **560–590**, and the shipped Q
window stops at 580.

**Q2 — how far may windows move?** §6.4 rule 3 forbids scanning-for-best-score as a *result*. Are you
content with theory-placed windows only, or do you want a scan reported as a diagnostic map
(invariance as a function of window position) with the overfitting caveat attached?

**Q3 — the free-base band positions.** §3.3 needs the four D2h Q-band positions for
protopheophytin *a* to place windows by theory rather than by eye. We hold Fruhwirth & Hermetter and
the InTech porphyrin chapter; do they carry the numbers, or is this a literature errand first?

**Q4 — scope of the first pass.** ⚠ Reshaped by §3.5(a): C1 is out, so the baseline-free set is now
**C2, C3, C6, C10**. Run those four first, or the whole pool at once?

**⭐ Q6 — the target comparison. ✅ ANSWERED (Edwin, 2026-08-04): "Kiendler green vs S-Budget brown".**
The roster stands as the documents have it — **S-Budget is the brown one, Kiendler and Steirerkraft are
both green.** The target is **green vs brown**, and the yardstick to beat is `M` at *d* = 6.91.

⇒ **Consequence for C1: it is dead for the actual target** (*d* = 0.05). Its *d* = 1.67 on the
green-vs-green task is real but that task is not what we are solving; C1 stays in the pool only as a
note for a future within-class grading question.

**⭐ Q7 — scalar or 2-D verdict?** §7.4.2 shows three bands give **two** independent numbers, and §7.4.3
may produce a shape feature independent of both. If two features prove genuinely independent, the honest
metric is a **pair**, not a number — which changes what the plugin displays and how a threshold is
defined, not merely what this document concludes. Worth deciding before route A runs.

**Q5 — does the brown oil get a second fill?** Without it, every invariance number here is green-only,
and the same gap blocks T1 in the pedestal document. One extra fill closes both.

---

## 9 · Phasing *(proposed, not started)*

| phase | what | gate |
|---|---|---|
| **R0** | ✅ overview plot built (§3.5). Answer Q2–Q5; freeze the candidate list | Edwin |
| **R0b** | ⏸ **POSTPONED by Edwin, 2026-08-04** — one bench evening, all three oils in one session, two strengths each. Agreed as correct, deferred so the brainstorm can continue on data in hand | ⚠ *until it runs, no between-oil result here can be separated from a between-evening one — including the incumbent's* |
| **R1** | build the extraction + scoring harness. **Extraction writes §6.3's JSON feature table** (28 rows, every quantity found so far); scoring reads only that | harness reproduces C11's known numbers from the table alone |
| **R1b** | ⛔ **§3.6a — re-measure the two lamp lines with a proper profile fit.** Gates every position metric | λ stable to ≪ 0.9 nm across sessions? |
| **R2** | score the baseline-free set (**C14, C15, C2, C3, C6, C10**), with 473/608 nm excised per §3.5(b) | ⭐ **decision point: can the chord be abandoned?** |
| **R2a** | ✅ per-session vs per-run calibration (§3.8) — per-session adopted | done |
| ⭐ **R3** | **the whole-spectrum band map — §7.1.** Designed, not started. The only unblocked lead left | is there class information `M` cannot already see? |
| **R2b** | ✅ **C16 scored (§7.2)** — V3, the baseline-free variant, is the only one that clears the bar | done |
| **R2c** | ✅ **out-of-sample on the pre-rebuild archive (§7.3)** — ⛔ the pedestal correction fails; first brown-oil dilution numbers on record | done |
| ⭐ **R4a** | **C18 / three-band (route D)** — the untested pair, and whether S/Q and Q/F are independent | free; closes an obvious gap |
| ⭐⭐ **R4b** | **C19, Q-region shape (route A)** — 2nd and 3rd moments, where the band splitting should live | ⭐ the recommended first real attempt at "a better V3" |
| **R4c** | **C21, smooth-background removal (route C)** — also prices the pedestal document's T4 | does removing the pedestal triple V3's contrast? |
| **R4d** | **C20, derivatives (route B)** — last; its weakest term is at the range edge | — |
| **R3b** | score any remaining pool candidates; report with attempt count per §6.4 | — |
| **R4** | band decomposition (C7) — the largest piece of work, justified only if R2/R3 leave the truncated peaks as the limiting factor | — |
| **R5** | write findings back into `DOC_metric_algebra.md`; retire or keep `DOC_pedestal_correction.md`'s proposal accordingly | — |

**⇒ R2 was the original point of this document, and it has been run.** No baseline-free metric matched
`M` (§3.7, §3.9), so `r_Q` and assumption A1 are *not* moot — they remain unproven, as
`DOC_pedestal_correction.md` says.

**⇒ ⭐ R3 (§7.1) is now the live phase, and the only one not blocked on something external.** It asks
the question §3.9 left open — *is there class information anywhere that `M` cannot already see?* —
and either answer is worth having: a band that clears the floor is a pre-registered candidate for new
data, and a flat map is a **quantitative bound** on how much independent information the range can hold.

⚠ **But §2.2 now caps what any of these phases can conclude.** With one brown oil there is no
between-oil variance for the brown class, so no phase here can generalise from *these* oils to *the
classes*. **R0b is the binding constraint on the whole programme** — reached independently from §3.4
(session confound), from T1 in the pedestal document, and now from §2.2 (pseudo-replication).

---

## ⭐⭐ 9.1 · Where this leaves the programme, and what is next *(2026-08-04)*

**The analysis is finished.** Seven routes were opened and closed in one session (§7.5–§7.11), every one
of them on the same wall: **both principal bands are flanks** and the range is clipped at both ends.
`M` remains unbeaten, the pedestal correction remains in-sample only, and no metric change is pending.

⇒ **Every remaining lever is a LAB or CAPTURE change, not an analysis one.** In priority order:

#### ⭐⭐ Software — can start TODAY, no hardware, no bench time

| | action | what it costs | status |
|---|---|---|---|
| ⭐⭐ **S1** | **Trim the Soret window 440–460 → 448–460** (`DevSpectralPlugin.PB_SORET_BAND`) | one line, **plus a threshold re-derivation** (`B_Soret` 1.03 → 0.69) **plus a plugin re-sign**, since the window lives in the signed artifact | ✅ **SHIPPED 2026-08-10** (`SPEC_soret_448_trim.md`) — with the threshold re-derivation, as planned. ⚠ The "plugin re-sign" in the middle column was WRONG: `DevSpectralPlugin` cannot pass the publish lint at all (it imports four sibling gauge modules), so the bench loads the built-in and the trim is a plain commit — §18 S1. Thresholds re-derived on §16.20.4's own corpus: **T = 6.8** (pedestal) / **8.3** (far620) |
| ⭐⭐ **S2** | **The DN guard** — two-sided, per §16.23.8: record min(S), warn out of window, propose the correction | recipe becomes an input; guard warns, never blocks. ⭐ Its value is catching an out-of-range fill **at capture** rather than in analysis, which is why it must precede the capillary runs — and the capillary's ±10 % volume band is exactly what pushes a fill out of the DN window | ⏳ **SCHEDULED** — `SPEC_first_presentable_state.md` step 3b, in parallel with the aperture print (no schedule day) |
| ⭐ **S4** | ⭐ **Simulate the LED combination** — score cool-white backbone + violet ~430 + deep-red 630/660 for coverage across 430–670 nm. **Everything needed already exists**: 17 measured Avonec SPDs in `spectracs-references/leds/avonec/`, `LedReferenceSynthesisOp` and the interactive LED picker (`SPEC_pipeline_playground.md` §4, `PlaygroundViewModule.py`) | prices the whole lamp question (`SPEC_capture_quality.md` §16.25.4a) **before anything is soldered**; ⚠ weight by band, not flatness — §16.24.2's 17× asymmetry makes Q-band and far-anchor photons worth far more | ⏳ **no hardware, no bench time** |
| ⛔ **S3** | **Resolve the DN contradiction** — 2.0–2.6 vs 18–26 DN for the same darkest bin (`DOC_pedestal_correction.md` §7 vs `SPEC_capture_quality.md` §16.7.2e) | nothing — **S2 logs it as a side effect** | ⛔ **§16.23.6's whole dilution conflict is contingent on this** |

⚠ **S1 and S2 are the only items on this page needing neither the capillaries nor an evening at the bench.**

#### Bench and hardware

| | action | what it unblocks | status |
|---|---|---|---|
| ⭐⭐ **1** | **The capillary protocol** — `SPEC_capture_quality.md` §16.23, gates G1/G2 first | ⭐ within-green grading (SNR 1.8 → 18); a real concentration axis ⇒ **A2 and A4 become measurable**; OD-dosing ⇒ **retires the pedestal correction and A1** | ⏳ capillaries arriving |
| ⭐ **2** | ⭐ **R0b SIMPLIFIED — three oils, ONE evening, standard recipe, one tube each, plus one MCT blank** | the session confound (§3.4); a second brown fill (§2.2); the background *measured* rather than inferred (§7.12) | ⏸ postponed, **now 4 tubes not 9** |
| ⛔ **3** | ⭐ **THE STRAY-LIGHT GATE — block the beam, read `S`** (§16.23.6f) | decides whether the blue floor is quantisation (fixable in software) or stray light (needs baffling). **One capture, one minute** | gated on **S3** |
| ⚠ **0** | **A jar mount that repeats** — `SPEC_capture_quality.md` **§16.26**. ⛔ **REVISED 2026-08-06 (§16.26.10): this was over-ranked.** The null series put the **instrument floor at 0.42 %** on `M`, but the alarming re-seat numbers came from **empty-jar** runs; in the operating condition (jar filled with IPA) a re-seat costs **rms 1.36 %** — 4× less, and close to the floor | ⚠ **no longer the dominant term.** Instrument + re-seating reach ~1.4 % against a 3–5 % archive CV, leaving **~3.8 % unexplained** — and a null run is blind to the one thing left: **the preparation** | ⏸ **demoted**; still worth doing eventually, but it is not the lever |
| ⭐⭐ **P1** | ⭐⭐ **NEW SAMPLE HOLDER with a proper aperture — a SLIDE-IN jar solution** *(Edwin's priority 1, 2026-08-06)*. `SPEC_capture_quality.md` §16.25.2: two apertures at the jar's **inner** diameter, lower (stops light entering the wall) and upper (stops wall-exit + scatter). ▶ **Measure `f` first** with the opaque-oil test — ten minutes, no machining | removes the wall-bypass path; ⭐ a slide-in also controls **tilt**, and an aperture between jar and slit fixes the **angular acceptance** the reseat error works through. ⚠ On today's recipe worth only ~2.3 % per 1 % of `f` — its real value is as an **enabler for a stronger fill** | ⏳ **PRIO 1** |
| ⭐⭐ **P2** | ⭐⭐ **REDO green-vs-brown AND green-vs-green on the CAPILLARY protocol** *(Edwin's priority 2)*. §16.23; gates G1/G2 first | ⭐ the measured blocker: instrument 0.42 % + reseat 1.28 % against a 3–5 % CV ⇒ **~3.8 % is the preparation**, and §16.23.7 puts green-green at **SNR 1.8 → 18**. Green-vs-green is the capability gate (*d* ≈ 1.3–2.0 vs ≳ 3 needed) | ⏳ **PRIO 2** |
| ⭐ **P3** | ⭐ **The 660–680 nm QUIET-WINDOW test** — §7.14.4 above. ⚠ Two prerequisites: the calibration must extend past 630 (free), and **the lamp must actually reach 660–680, which is NOT established** — the "Sansi 24 DN at 680" figure came from a screenshot ending at ~676 nm with a transferred wavelength scale | ⭐ decides whether the whole scatter-correction family reopens, via `far/near < 1` | ⏳ on the backlog |
| ⭐⭐ **0a** | ⭐⭐ **THE REFILL NULL** — `SPEC_capture_quality.md` **§16.26.11** (protocol written, not run). Reference IPA → **empty, refill with fresh IPA**, capture as sample; truth is still `A = 0`. Every null so far kept the SAME liquid in both captures, so **the disturbance a real run actually performs has never been measured**. Run both lamps, n ≥ 4 | ⭐ splits the unexplained ~3.8 % into **handling** vs **dosing** — different problems, different fixes; **and it is the decisive lamp test**, because §16.26.5's "lamp-independent" was measured on gentle disturbances while a refill is not gentle | ⏳ **run this before 0b** |
| ⭐⭐ **0b** | ⭐⭐ **MEASURE THE GAP — repeat the CV with REAL fills.** A null has no sample, so it cannot see preparation error. If run-to-run scatter on actual oil is 3–5 % while nulls sit at 1.4 %, **the difference IS the preparation** | ⭐ settles what the archive CV actually is, and it is **the entire case for the capillary in one comparison** (§16.23.7: dosing spread 1.665 units against a 0.98-unit signal, SNR 1.8) | ⏳ **cheap, and the highest-value measurement on this page** |
| ⭐ **3b** | ⭐ **INSTRUMENT TODO — slit baffle ("Gegenlichtblende") on the Yuji + blacken the cone interior.** ⚠ The baffle is valid **only for a diffuse source** (`KB_spectroscopy_physics.md` §7.1): on the DIY array or a bare CFL it *selects* emitters and worsens along-slit uniformity. ⚠ The cone is **blued sheet metal** (black oxide) — specular, not black under illumination; matte paint is only a partial fix, **flocking is the standard answer** | attacks the stray-light floor **at source** — the same floor §7.13 showed compresses the Soret band and injects the false pedestal intercept | ⏸ **gated on 3** — measure before machining |
| **4** | **Dual-exposure absorbance** — low exposure for R, high for S, corrected by log(E_S/E_R) (§16.23.6e) | ⭐ dissolves §16.23.6's dilution conflict outright — both constraints met at 1:250, no lamp purchase | gated on **3** |
| **4b** | ~~analog-vs-digital gain test~~ | ✅ **DONE 2026-08-04: the gain is ANALOG** (no histogram gaps at any setting). ⚠ But the range is only **1.51×**, short of the 2.3× the guard needs — helpful, not sufficient (§16.23.6d) | done |
| **5** | **Extend the red range to ~660 nm — and get light onto 432 nm.** ⭐ **REFRAMED 2026-08-06** (`KB_spectroscopy_physics.md` §4.1a): the pigment's centres are **432 / ~574 / ~625 nm**, and our windows sit at 448–460 (16–28 nm **above** the Soret peak — pure flank), 560–580 (✓) and 620–630 (contains Qy, but used as a *baseline anchor*). ⇒ **§7.8's wall restated from the molecule's side**, and the fix is two-sided: extend the red **and** light the blue. ⚠ Also measured: the archive is **convex at 626 nm on every fill** — the Qy maximum has never been observed, and a null-run control showed the instrument's own curvature would fake one | ⭐ the structural fix — turns both flanks into bands and gives the first genuinely quiet region (§7.8, §7.9b) | ⭐ **REPRICED 2026-08-06 — no longer "hardware, cost unknown"**: the optics deliver to ~680 nm and the Eu³⁺ 650.7 nm line **resolves** (`KB_spectroscopy_physics.md` §7.2), so the 440–630 clamp is ours. The gate is now **photometric and it is a LAMP choice** — measured at 650/656 nm the **Sansi beats the Yuji 3.7×/5.5×**. ⛔ Do not move the clamp without it: at 7–13 % of the 630 nm level those bins are the 440–447 regime again |
| ⭐⭐ **6** | ⭐⭐ **THE VALIDATION STUDY** — 12+ greens, 2–3 browns, jury **visual sub-score** recorded separately, plus **roast level** as objective ground truth. ⛔ **Freeze thresholds BEFORE the first sample**; spread the panel across sessions and interleave classes (§3.4's confound); honour the ageing rule (§16.11.16); report per-oil, not pooled | whether the instrument measures what it claims. ⭐ **After the Soret trim + aperture + capillary the projected CV is ~1.4 % (from 3–5 %), lifting within-green *d* from 1.34 to ~3.5–5** — at which point the bottleneck stops being precision and becomes EVIDENCE, and this is the only item that addresses it | ⏳ **ON THE ROADMAP 2026-08-06.** ⚠ **PRIO 3a comes first** — a scaled-down validation (8 oils: 2 brown / 2 non-premium green / 4 premium green; two blind judges; ~4–5 days) that **freezes the thresholds** and is run **out-of-sample**, on oils P2 never saw. This entry is the FULL study, which earns the two claims P3a cannot: *"measures roast level"* and *"generalises"* |
| **7** | **Q3** — a primary UV-Vis of *protopheophytin a* | C7, band decomposition; not on the open web (§3.12a) | purchase/library |

⚠ **Two limits survive all of the above** and must be stated with any result: the **session confound**
(§3.4) and **one brown oil** (§2.2). Only item 2 addresses them.

### ⛔ 9.2 · RETIRED 2026-08-04 — the `r_Q` dilution series is no longer needed

*(Edwin's call, and the reasoning holds.)* The multi-strength run of `DOC_pedestal_correction.md`'s **T1**
existed to measure `r_Q` per oil and settle **A1**. **At fixed optical density none of that matters:**
`F` = 1 + \|`r_Q`\|/`B_Q` becomes the same constant for every sample, so the correction is a pure rescaling
that cannot change a ranking, a Cohen's *d*, or a verdict (§16.23.7). The same argument retires **A2** and
**A4** as *verdict* risks — they remain interesting physics and stop being blockers.

⚠ **But T1 was carrying four passengers, and two of them must not be dropped:**

| what it answered | verdict |
|---|---|
| `r_Q` per oil (**A1**), `k` vs `r_Q`, A2/A4 via a concentration axis | ⛔ **retired** — the correction is not used |
| ⭐⭐ **the session confound** (§3.4) | **KEEP** — the only open item that could invalidate `M` itself |
| ⭐ **a second brown fill** (§2.2) | **KEEP** — one bottle cannot support a class claim |
| the **MCT blank** (§7.12) | **KEEP** — one extra tube, and the last untried analysis route |

⇒ **The experiment shrinks rather than disappearing: three oils + one MCT blank, one evening, standard
recipe, no dilution series. Four tubes.** It no longer needs a wide span, a third preparation, or the
100 mL glass — those requirements belonged to the `r_Q` fit alone.

⭐ **Consequence for `DOC_pedestal_correction.md`:** T1 as written is superseded. Its chapter 13 should
record that the correction is not adopted, the correction is **not needed** under an OD-dosed protocol,
and the remaining value of that evening is the confound and the brown-class fill — not `r_Q`.

⭐ **And one conclusion is ready to act on now:** at fixed optical density the pedestal correction is a
pure rescaling that cannot affect any comparison (§16.23.7). **Ship `M baseline`; keep
`M baseline + pedestal` as a diagnostic only** — at fixed OD the two should track exactly, so divergence
means the dosing discipline has slipped. That turns a retired correction into a free process check.

---

## ⭐⭐ 10 · `V` — THE BEST METRIC ON RECORD, and the one to implement  *(2026-08-14)*

> **Status: PRE-REGISTERED. Definition FROZEN below.** Found on 2026-08-14 from Edwin's reading of the
> pivoted spectral panels; scored on 13 fills / 7 products / 53 runs. ⛔ **Not yet tested on data it was
> not tuned on** — ROADMAP **PRIO 2c / σ_fill** is that test. Reproduce everything with
> `diagnostics/box_metrics.py`.
>
> ⭐ **Two 2026-08-14 amendments, both below:** §10.1a pins the **sampling convention** (native samples,
> not a resampling grid) and reprints §10.3/§10.4 on it; the shipped threshold is **`T_V` = −18.6**.
> ⇒ The UI half — gauge, rows, the new band plot — lives in **`SPEC_v_metric_integration.md`**, which
> may not change anything frozen here.

### 10.1 The definition

On the **de-spiked raw absorbance — no baseline correction of any kind**:

```math
V = \frac{A_{valley} - A_{Q}}{A_{Soret}}   \qquad\text{reported as } V \times 100
```

| symbol | window | what it is |
|---|---|---|
| `A_valley` | **500–560 nm** | the flat window between the bands — the pigment's own transparent region |
| `A_Q` | **565–580 nm** | the Q band |
| `A_Soret` | **448–460 nm** | the Soret flank |

Each is the plain arithmetic mean of the absorbance inside the window, computed **per run**, then
averaged over a fill. `V` is always negative (the valley lies below the Q band); **less negative =
greener**. Worked example, Steirerkraft `20260807D/001`: `(0.07069 − 0.16703) / 0.57713 = −0.16693`.

#### ⭐ 10.1a THE SAMPLING CONVENTION — settled 2026-08-14, and it was a real hole

⛔ **"The plain arithmetic mean of the absorbance inside the window" does not define a number** until
you say *which samples*. It is now pinned, and the rule is the shipped code's rule:

> **A band mean is the plain arithmetic mean of the spectrum's OWN NATIVE SAMPLES inside `[lo, hi]`,
> both edges inclusive** — bit-identical to `SpectrumFeatureLogicModule.bandMean`, which is what the
> plugin calls and what the app can actually compute.

**Why it had to be settled before anything is built on §10.** `box_metrics.py` used to resample onto a
0.5 nm grid first (31 nodes in the Q window against **103 native samples**), and that read `V × 100`
**0.082 ± 0.023 systematically low** — the spec's own script and the app would have printed two
different numbers for the same jar. ⭐ Every number in §10.3/§10.4 below is reprinted on the native
convention; ⭐ **§10.5 is unaffected** (0.214 → 0.214, 0.703 → 0.701) and so is every gap/ratio
statistic in §10.2 and §10.4, because a common additive bias cancels in a difference and in a Cohen's
`d` alike. Only absolute levels moved.

⚠ **The limitation this exposes, recorded and NOT fixed.** A plain window mean over `N` samples
carries an `((f(a)+f(b))/2 − mean) / N` term — the endpoints get full weight where they deserve half —
so **it is not portable across sampling grids**, and its size depends on where the window edges sit
relative to the interior. Measured on the Q window: predicted `+0.00043`, observed `+0.00051`. A
**trapezoid (integral) mean** is portable and cuts the two conventions' disagreement 3.6× (0.082 →
−0.023). ⛔ Not adopted: it would move `bandMean` and therefore M448 and every shipped metric at once.
⚠ §9's *"MEAN, not integral"* decision was about a raw `A·nm` integral, which an integral **mean** is
not — so that door is closed by blast radius, not by principle.

⚠ **The common grid is still load-bearing elsewhere.** Ten distinct native wavelength axes live in
this archive (different calibrations, 413–424 nm starts, 1460–1538 points). Anything that compares two
curves **point by point** — `SPEC_history_tracker.md`'s `D = √(1−r²)` above all — must still resample
first. The grid was dropped for band **means** only, in `box_metrics.py` and `box_terms.py`.

⛔ **The windows are FROZEN.** They were chosen by eye from the physics, not optimised — but ~9
candidates were scored on these 13 fills, so re-tuning them would destroy the only thing that can
retire that selection risk. Edge sensitivity was checked: **15 of 17 single-edge variants still
separate under both labellings**; the Q window is the sensitive one (`572–578` fails).

⭐ **Why this construction.** The numerator is a **difference**, so any additive offset — stray light,
scattering, seating — cancels, both bands carrying it equally. The denominator is a **level**, so
multiplicative scale — concentration, exposure — cancels. That is the same immunity the linear
baseline provides, obtained arithmetically instead of by fitting, **and because nothing is fitted, no
anchor can contaminate it.** ⇒ That is not academic: `SPEC_capture_quality.md` §16.31.3a measures the
shipped chord's far foot sitting *on* the Qy band, giving every fill its own baseline slope.

### 10.2 What it measures — and `W`, the mechanistically pure form

```math
W = \frac{A_{Q} - A_{valley}}{A_{Soret} - A_{valley}}
```

— the **Q : Soret band-intensity ratio**, with the valley as the pigment's own zero. **Gouterman's
four-orbital model** makes that ratio *the* diagnostic for loss of the central Mg²⁺: in a metallated
porphyrin (D₄ₕ) the Q transition dipoles nearly cancel and Q stays weak; remove the metal
(**pheophytinization**, D₂ₕ) and the cancellation degrades, so **Q gains intensity relative to the
Soret**. Measured: `W` = **0.163–0.189 green, 0.198–0.238 brown**, browns 1.2–1.4× higher — the
predicted direction. ⭐ It is the same chemistry that turns cooked green vegetables olive.

⛔⛔ **`W` IS NOT DILUTION-INVARIANT ON THIS INSTRUMENT, AND IT IS TEMPTING TO CLAIM THAT IT IS.**
Algebraically `W` cancels `a → k·a + b` exactly — numerator and denominator are both differences — so
it is easy to argue that concentration cannot move it. **The archive says otherwise**, and the two dose
pairs move `W` the SAME way while their concentrations move OPPOSITE ways (`SPEC_capture_quality.md`
§16.36.5):

| | `A_Soret` | `A_valley` | `A_Q` | `W` |
|---|--:|--:|--:|--:|
| Kiendler 6 → 7 drops | +48.2 % | ⛔ **+178.5 %** | +83.7 % | **+5.4 %** |
| Steirerkraft → half | −29.8 % | ⛔ **−48.1 %** | −32.4 % | **+8.9 %** |

⭐ **The valley moves far more than proportionally in both** — it is not a constant background, so
`W`'s own zero moves with the dose. That is the mechanism behind the 20.9 % measured below.
⇒ **Never rest an argument on `W`'s invariance.** Use the *band-fall ratio* (§16.36.1): a dilution
multiplies every pigment band by the same `c`, so the two must fall by the same fraction — 1.00
exactly, whatever `c` is. It needs no assumption about backgrounds at all.

⭐ **`W = −V/(1−u)` with `u = A_valley/A_Soret` is an exact identity** (verified to 3 × 10⁻¹⁷ on all
49 runs). `u` spans **22 %** across the archive, and that factor is the entire reason `W` is noisier:
gap 3.77 sd vs `V`'s 5.05, dose 20.9 % vs 3.4 %, refill 16.1 % vs 7.4 %. ⇒ **`W` is the physics, `V`
is the better-conditioned estimator of it.** Ship `V`; quote `W` when explaining what it means.

⚠ **Three caveats on the physical claim.** (1) We measure the Soret **flank** — the peak is at 432 nm
(`KB_spectroscopy_physics.md` §4.1a) — so `W` is a proxy, and pheophytinization *moves* the Soret as
well as changing its strength, which amplifies the response but muddies its interpretation. (2) The
565–580 window is not Qy (~625 nm) but very plausibly its **Q(1,0) vibronic satellite**: §16.30.7f's
narrow 580.4 nm band sits **1229 cm⁻¹** above the 625 nm Qy, squarely in the 1200–1400 cm⁻¹ interval.
(3) ⛔ The algebra says `W` should be dose-invariant and `V` should drift; **the measurement says the
reverse, six times over** — so `V`'s conditioning advantage is empirical, not explained.

### 10.3 The threshold — `T_V = −18.6`

Derived by `soret_448_thresholds.py`'s own **corridor-midpoint** method on **its own 18-run corpus**
(Steirerkraft B + C green, S-Budget series D brown — the same runs both shipped M448 lines came from),
on the §10.1a native-sampling convention:

| | mean ± sd | |
|---|---|---|
| green (12 runs) | −15.94 ± 1.17 | highest green run −17.14 |
| brown (6 runs) | −20.44 ± 0.26 | lowest brown run −20.19 |
| empty corridor | **3.05 units wide** | Cohen's **d = 5.33** |
| corridor midpoint | −18.67 | |
| ⇒ ⭐ **shipped** | **`T_V` = −18.6** | |

⭐ **Why −18.6 and not the midpoint.** It sits just *inside* the corridor on the **strict** side of
−18.67, which is the side `SPEC_capture_quality.md` §16.10.17d's policy wants: a false GREEN is the
harder error to make. It costs nothing — **no archived run lies between −18.60 and −18.67** — and it
matches the one decimal the gauge displays, so the line on screen and the number beside it agree.
⚠ Both are inside the empty corridor, so **either separates the corpus perfectly**; this is a policy
choice, not a measurement.

⚠ **Where the rest of the archive lands** — and two things must be said out loud. **Both Spar g.g.A.
oils come out GREEN** under `T_V`, contradicting §16.30.1a's relabel; and **three fills straddle the
line at run level** — confirmed run by run on the native convention:

| fill | its runs (`V × 100`) |
|---|---|
| Steirerkraft half-strength | −16.49 · −17.63 · −18.38 · **−19.35 · −19.44 · −19.79** |
| Steirerkraft aged 24 h | −15.97 · −18.10 · **−19.34** |
| Spar Steirisches g.g.A. | −18.06 · −18.34 · **−18.81** |

⛔⛔ **This is a REQUIREMENT on any gauge built from `V`, not a footnote.** A two-class gauge shows a
different verdict for two consecutive captures of the same jar — one fill spans 3.3 units across six
runs. `SPEC_v_metric_integration.md` §4 discharges it with a third *borderline — re-measure* class
whose edges are the measured within-fill sd (±0.70), and which fits entirely inside the empty corridor
so that no corpus run changes class. ⛔ Neither is a
`V` defect — the corpus deliberately excludes the boundary products, exactly as it does for M448 — but
it means **`T_V` may not be quoted as classifying the Spar oils**. A fill whose runs straddle the line
has no verdict and the gauge must say so rather than average its way to one.

### 10.4 The scorecard, and two real weaknesses

| | `V` | M448 |
|---|---|---|
| class gap | ⭐ **5.05 sd** | 3.80 sd |
| separates under **both** labellings | ⭐ yes | ⛔ no |
| archive fills ordered correctly | ⭐ **17 / 18** | — |
| dose, ±40 % | ⭐ 3.4 % of class gap | 10 % |
| denominator distance from zero | ⭐ 10 sd | ⛔ **6 sd** |
| refill reproducibility | 7.4 % of class gap | ⭐ **3.7 %** |
| baseline dependence | ⭐ **none** | ⛔ chord foot on Qy |
| ⛔ **lamp swap, same oil** | ⛔ **4.84 units** | ⭐ 8 % |
| ⛔ **half concentration** | ⛔ **2.19 units** | ⭐ holds |
| evidence base | one session, 9 candidates scanned | months, rig-verified, shipped |

⛔ **The denominator point is the one Edwin raised and it is decisive against M448**: `B_Q` reaches
within **6 sd of zero** (0.0344 on `Ja! Natürlich`), which is why that oil's M448 inflates to 22.24
and why `20260811A` returns **M448 = −9.72**. `V` divides by a raw Soret level that no dilution can
drive small.

⛔⛔ **NEITHER "DOSE" PAIR IS A CLEAN DILUTION** *(2026-08-15)*. Tested with the band-fall ratio, which
is 1.00 for a pure dilution whatever the concentration change: **Kiendler 0.84, Steirerkraft 1.31.**
⇒ the **2.19** above is a **preparation** difference, not a dilution coefficient, and the archive
cannot calibrate a dilution correction for anything. ⚠ The number still describes what happens when you
halve a fill by hand — which is the operationally relevant case — but it may not be read as "`V`'s
sensitivity to concentration".

⛔ **The lamp weakness is `V`'s worst property.** §16.28's two-lamp control moves it 4.84 units on one
oil — larger than the entire green/brown span — where M448 moves 8 %. ⇒ **A chart cannot cross a lamp
change**, and `SPEC_lamp_rebuild.md`'s rebuild will reset it.

### 10.5 The history-tracker band — ±1.0

⭐⭐ **MEASURED AGAIN UNDER THE SETTLED PROTOCOL, 2026-08-18** (`SPEC_settled_measurement.md` §28,
series F): five SEPARATE preparations of one oil scatter by **σ = 0.276**, against the archive's pooled
WITHIN-FILL figure of **1.255** — 4.5× tighter, and across fresh fills rather than repeats of one jar.
⇒ the band arithmetic below stands, but its input has changed: on 0.276 a **±0.85** band is 3.1 σ
(1 alarm in 500) and ±1.0 is 3.6 σ. ⚠ And `SPEC_history_tracker.md` §11.4 adds the term this section
omits — the REFERENCE is measured too, so the comparison scatters by σ·√(1+1/n): a single-fill reference
inflates the false-alarm rate fifteenfold.

Measured refill floor: **pooled 0.21 units** (Kiendler 0.09, Billa Clever 0.18, Steirerkraft 0.23,
S-Budget 0.37); within-fill sd 0.70; class span 4.50. ⭐ **§10.1a changed none of this** — the pooled
floor moved 0.214 → 0.214 and the within-fill sd 0.703 → 0.701, because a common bias cancels in every
difference. The band derivation below therefore stands exactly as first written.

| band | multiple of refill sd | detects |
|---|---|---|
| ±0.64 | 3σ | 14 % of the class span |
| ⭐ **±1.0** | **4.7σ** | **22 %** — the recommended band |
| ±2.0 | 9.5σ | 45 % — post-mortem, not warning |

**Nothing benign on record reaches 1.0**: a refill costs 0.37, nine days costs 0.40, a ±40 % dose
change costs 0.12. **Everything that should fire does**: an undissolved fill drifts 2.28 in eight
minutes, half-strength 2.19, a class change 4.50, a lamp swap 4.84.
⚠ *nine days* and *undissolved* are not recomputed on the native convention — they are differences, so
§10.1a moves them by ≲0.05, well inside their own scatter.

⇒ ⭐ **The claim this supports:** *"Measured on your own instrument against your own reference press,
we tell you when a batch has drifted by a fifth of the distance between a good green oil and a brown
one — before you can see it."* ⚠ Provisional: the 0.21 floor comes from the **drop-based** recipe, and
**no refill pair exists on the capillary recipe with a non-Billa oil**. PRIO 2c settles it.

### 10.6 What `V` does NOT change

1. ⛔ **Ground truth is still the blocker, exactly as before.** `V`'s class separation is measured
   against labels that are judgment calls — and M448 is in the identical position: its shipped
   threshold rests on **18 runs from two products**, with the boundary oils held out as *"context,
   never an input to the line"*. ⇒ The gap is project-wide, not metric-specific; it neither favours
   nor blocks the switch, and **PRIO 3a still owns it**.
2. ⛔ **It is not independent evidence about any label.** `V` correlates 0.66–0.84 with the red slope,
   `S2` and M448 — §16.30.1a's point stands: one pigment system, many projections.
3. ⚠ **The 448–460 flank caveat applies to M448 too**, so ROADMAP item 5's "get light onto 432 nm"
   would upgrade both at once.

### 10.7 Two by-products worth keeping

- **`S2`** = mean SNV (over 448–629) of the raw spectrum across **617–629 nm**. ⭐ The most
  dilution-invariant quantity ever measured here — **0.01 within-fill sd** for a dose change, against
  M448's 0.36. ⛔ Overlaps the classes on Spar Premium, so it is parked on PRIO 3a, not dead.
- **`S1`** = the same over **490–578 nm**. Not a metric — 1.61 sd gap with 1.84 sd overlap — but
  **−0.372 ± 0.012 across all twelve fills, six products, four sessions**, a 3 % spread. ⭐ Nearly an
  invariant of pumpkin oil on this instrument, and therefore usable as a **run-validity check**: if
  `S1` departs from −0.372, that measurement is wrong, whatever the oil and whatever its strength.

### ⭐⭐ 10.8 WHAT `V` EARNED ON ITS FIRST LIVE EVENING — a feature nothing else could resolve  *(2026-08-15)*

⛔ **First, what it did NOT do.** `Q%` cannot tell *"less pigment in the beam"* from *"changed pigment"* —
both make the sample absorb less and both raise it. Edwin raised exactly that objection and it was
correct; the discriminator is the **band-fall ratio** (`SPEC_capture_quality.md` §16.36.1), not this
metric. Nothing below claims otherwise.

⭐⭐ **What it DID do is more fundamental: it was quiet enough for the feature to exist.** The Lugitsch
time-course turns over — clearing (which pushes `Q%` down) handing off to photodamage (which pushes it
up) — and the turn itself is tiny:

```
the feature      Q% 13.34 -> 13.27 -> 13.38      excursions of ~0.07-0.11 units
on Q%            no-re-seat floor sd 0.063   ->  1.1-1.7 sigma   ⭐ RESOLVABLE
on M448          within-fill floor sd 0.37   ->  0.27 sigma      ⛔ INVISIBLE
```

⇒ **On the incumbent the same feature is a quarter of one standard deviation.** The entire two-process
picture — and with it the discovery that the lamp changes the sample — would have stayed buried in what
everyone would have called re-seating noise. ⭐ **A metric earns its place by making a real thing
visible, and this one did that on its first evening in front of a live sample**, on an oil that was
never in any corpus.

⚠ Keep the claim the right size: this is about **resolving power**, not about `V` being right where
M448 is wrong. M448's noise here is dominated by its `B_Q` denominator (§10.4), which is a known and
already-documented weakness — this is that weakness costing a discovery, which is a sharper illustration
than any table of Cohen's `d`.

---

## 11 · Related documents

| topic | where |
|---|---|
| ⭐⭐ **`R`, the 624/568 peak ratio — the §12 candidate** | **§12 below** · `diagnostics/peak_ratio_archive.py` |
| ⭐ **`V` / `Q%` in the DEV plugin — gauge, rows, the new band plot** | **`SPEC_v_metric_integration.md`** |
| ⭐ **the white-spirit session that found it** | **`SPEC_capture_quality.md` §16.12.7f** · `SPEC_settled_measurement.md` §52 |
| ⭐ **the lamp changes the sample; the band-fall ratio; the no-re-seat floor** | **`SPEC_capture_quality.md` §16.36** |
| the metric being replaced, and its algebra | `DOC_metric_algebra.md` |
| the correction this document steps back from | `DOC_pedestal_correction.md` — esp. App. D.6, ch. 13 T4 |
| pigment identity, band positions, Gouterman | `KB_spectroscopy_physics.md` §4, §4.1 |
| the instrument and its limits | `DOC_capture_fidelity.md` |
| the sample and its preparation | `DOC_sample_physics.md` |
| capture-side constraints, series provenance | `SPEC_capture_quality.md` §16 |
| the go/no-go this feeds | `SPEC_capability_proof.md` |
| ⚠ **candidate source, NOT held** — free-base porphyrin band positions (protoporphyrin IX 506/532/580/630 nm) | [MDPI Pharmaceuticals 14(2):138](https://www.mdpi.com/1424-8247/14/2/138) · [PMC7914864](https://pmc.ncbi.nlm.nih.gov/articles/PMC7914864/) |
| ⚠ **the errand** — a primary UV-Vis of *protopheophytin a* | not on the open web; needs Scheer *Chlorophylls* or a primary paper |

---

## ⛔⛔ κ IS DEAD — the turbidity correction, proposed and buried in one week  *(2026-08-19/20)*

This spec hunts a baseline-free, dilution-invariant metric, and §10 left the **pedestal correction** open.
`SPEC_settled_measurement.md` §32.6 proposed one from the Billa Clever series and §39.5 buried it. Recorded
here so the idea is not re-invented from the same evidence.

**The proposal.** `Q% ≈ Q₀ + κ·A_valley`, κ ≈ 4.5. It looked extremely strong: at κ = 4.5 two runs of the
same dilution measured half an hour apart reconciled from **0.681 apart to 0.010**, and the corrected values
(20.06 and 20.05) matched Edwin's independent expectation exactly.

**Why it is dead.** Fitting each run's own tail (`A_valley ≤ 0.16`) and extrapolating to zero turbidity, over
the five good runs:

```
run     slope        Q0(v=0)
001    +8.195         18.793
004   -12.036         21.329
005    -5.572         21.174
006    -3.076         20.277
007   +12.781         18.397
                      ------
       sd of Q0        1.346      vs  sd of the raw answers  0.467   ->  THREE TIMES WORSE
```

⛔ **The slopes do not agree in sign.** The 002/003 reconciliation was two runs that happened to line up.

⭐⭐ **What survives, and it is the useful half:** comparing two runs **AT the same turbidity** needs no model
and works — matched-`A_valley` reading turned a 0.742 disagreement into **−0.026** (§39.1). Extrapolating
ONE run **TO** zero turbidity needs a slope, and the slope is not identifiable from a tail where turbidity
and lamp dose move together. ⇒ **compare at matched `A_valley`; never extrapolate to zero.**

⚠ And the physics behind the pedestal is still unmodelled: **λ⁻ⁿ scattering predicts the OPPOSITE SIGN** of
the measured κ (§32.3, §33.3), and a grey/Mie pedestal cancels in the numerator of `V` and would make the
more turbid fill read *lower* — it reads higher. §16.12.2B's λ⁻ⁿ refutation now has a second, independent
confirmation from the other end of the turbidity range.

---

## ⭐⭐⭐ 12 · `R` — THE 624/568 PEAK RATIO, and it separates the archive where `Q%` overlaps  *(Edwin 2026-08-21, from two peaks he marked on a screenshot; DESIGN — nothing built)*

> ⚠⚠ **SUPERSEDED IN PART, THE SAME DAY.** `R` was the first construction from these two bands; the one
> Edwin **decided on** is **`dQ100` — §12.8**, which is better on a bad fill, on dilution and against an
> optics change. §12.0–§12.7 are kept as the reasoning that got there and as the record of what `R` can and
> cannot do. ⭐ **§12.11 is R1, the turbidity arm, and it clears the confound this document raised three
> times.** The decision itself is on the roadmap under *DECIDED 2026-08-21*.

This spec hunts *"a baseline-free, dilution-invariant metric"* (§1). §10 found `V`, and shipped it. **§12 is a
second candidate, found by accident, that beats `V` on the one job §2's corpus exists to test — and it has a
failure mode `V` does not have.** ⛔ Nothing is built and nothing is proposed for shipping.

### 12.0 · How it was found

`SPEC_capture_quality.md` §16.12.7f ran two oils in de-aromatised white spirit. Edwin looked at the trace,
circled two peaks — **(1) at 568 nm** and **(2) at ~624 nm** — and asked whether the two oils differ there.
They do, by a factor of ~1.7, on a quantity that is pure shape.

⚠ **Language correction that this section inherits.** The archive is **oil in isopropanol** (§16.23), not
neat oil. Every comparison here is **IPA against white spirit**.

### ⭐ 12.1 · The definition, and every choice in it is forced

```
   R  =  P2 / P1

   P1 = A(568)  above the straight chord through 542-546 and 600-606      [the 568 nm band]
   P2 = A(623-626) - A(612-615)                                           [the 624 nm band]
```

| choice | why it is forced |
|---|---|
| ⭐ **both terms are DIFFERENCES of two absorbances** | a flat (grey/Mie) pedestal cancels **exactly** in each. `SPEC_settled_measurement.md` §52.3 measured one fill carrying **+0.078 A** of exactly that |
| ⭐ **both terms scale with concentration** | the ratio is dilution-invariant on the same algebra as `V` (`DOC_metric_algebra.md`) |
| ⭐⭐ **⛔ NO SORET ANYWHERE** | every window lies between 542 and 626 nm at `A` = 0.1–0.5. The 448–460 flank runs `A` = 1.2–1.7 with the 440–447 bins past 2.0, and §16.24's error budget is **dominated** by it. **A metric that never touches the Soret has no saturation term** — and §52.3 shows a real run where Soret compression moved `Q%` by 0.060 A of denominator |
| ⛔ **the right anchor is 612–615, NOT anything past 630** | the capture clamp is 440–630; 137 of the archive's reports carry exactly that span. A variant anchored at 632–635 scored **better** (gap/spread 5.8× vs 4.1×) and is **rejected for reading outside the clamp** |
| ⚠ **612 is the earliest usable left anchor** | the 608–610 nm lamp line (`DOC_lamp_rebuild.md` §6 — a Bayer channel crossover) reads **1.6–2.2× the 613 nm value in every run on disk**, and already contaminates the 612 nm bin of `20260817LigitschA/007`. Five anchors were tried (612–615, 613–616, 614–617, 612–616, 613–617); **all keep the corridor**, worst case +0.317. 612–615 is the widest margin |

⭐ Reproduced by **`diagnostics/peak_ratio_archive.py`** → `spectracs-references/tmp/peak_ratio_archive.csv`.
⚠ It reads each report's **own de-spiked trace** rather than the shipped code path, because 176 of the 196
reports predate `Absorption (bands)`'s current construction.

### ⭐⭐ 12.2 · The archive-wide result

**196 reports carry a `workflow.json`; 190 cover 542–628 nm; 137 sit at exactly the 440–630 clamp.**

| corpus | | green | brown | Cohen d | corridor | |
|---|---|---|---|---|---|---|
| §16.20.4's own threshold corpus *(Steirerkraft B+C n=12 vs S-Budget D n=6)* | **`R`** | 0.779 ± 0.049 | 0.417 ± 0.032 | **8.14** | +0.182 | CLEAN |
| " | `Q%` | 15.941 ± 1.169 | 20.436 ± 0.261 | 4.59 | +3.041 | CLEAN |
| **all labelled runs, both rig eras** *(n = 55 / 33)* | **`R`** | 0.804 [0.541–1.183] | 0.360 [0.215–0.479] | 3.19 | **+0.062** | ⭐ **CLEAN** |
| " | `Q%` | 15.807 [12.742–19.957] | 19.995 [17.145–24.657] | 2.78 | −2.812 | ⛔ **OVERLAP** |

⭐⭐ **At `T = 0.510`, zero misclassifications over 88 runs, 9 oils, 16 sessions and a rig rebuild**, and the
corridor survives leave-one-session-out on every session. The shipped `Q%` overlaps on the same corpus.
⚠ The brown class includes **Spar Premium under §16.30.1a's relabel** — see §12.5; leaving it out changes
`R`'s corridor by nothing (it sits at 0.350–0.359, well inside brown) and narrows `Q%`'s overlap to −1.558.

⛔ **`T = 0.510` IS FITTED, NOT VALIDATED.** It is the midpoint of a corridor drawn on this same corpus. The
three tests below are the only genuinely out-of-sample evidence that exists.

### ⭐⭐ 12.3 · Three out-of-sample tests it was not tuned on

**(a) The rig rebuild.** Pre-rebuild, 2026-07-27, different lamp, no part in setting `T`:

```
 green  20260727E   0.658 0.729 0.808 0.817 0.822 0.823 0.917
 brown  20260727C   0.298 0.310 0.369 0.369 0.445 0.468        corridor +0.190, both sides correct at T
```

⭐ `SPEC_v_metric_integration.md` §5 records that **a lamp swap moves `Q%` by 4.84 units** — more than its
whole green/brown span. **`R`'s threshold does not move at all.**

**(b) The solvent.** Both white-spirit sessions land on the correct side of a threshold derived entirely
from isopropanol data: Lugitsch **0.826 / 0.838 → green**, Billa Clever **0.344 / 0.438 → brown**. `Q%`
cannot do this — it moved **+6.71** and **+2.09** between the routes (§16.12.7f).

**(c) ⭐⭐ Fresh vs 24 h aged, same oil, same session** — the archive's only such pair, and the test that
decides whether `R` measures *which oil* or *how brown*:

| | fresh `20270729B/C` (n=12) | aged `20270729A_aged24h` (n=3) | d | corridor |
|---|---|---|---|---|
| **`R`** | 0.779 ± 0.049 | 0.590 ± 0.048 | **3.86** | **+0.020 SEPARATES**, aged reads lower ✓ |
| `Q%` | 15.941 ± 1.169 | 17.791 ± 1.708 | 1.46 | −1.186 OVERLAP |

⭐ It sees the ageing, in the right direction, on a set §16.11.16 records as *misclassifying on 3 of 3 runs*
under the older metric. ⛔ **But the corridor is 0.020 against 0.062 for the class split, on n = 3, one
session, one oil. This is the weakest link and the first thing to re-test.**

### ⛔⛔ 12.4 · THE FAILURE MODE — a paper diffuser erases the 624 nm band

`20260727B` is the archive's **diffuser A/B test** (§16.7.2f: it came off between run 003 and run 004).
Split by that, and by nothing else:

```
 diffuser IN   (001-003, 008-009)   R = 0.121 +/- 0.126     P2 collapses to  0.000 - 0.031 A
 diffuser OUT  (004-007)            R = 0.635 +/- 0.013     P2 a steady      0.066 - 0.072 A
```

⛔⛔ **Perfect separation, on an INSTRUMENT change.** Meanwhile `Q%` barely moves (15.6–17.1 either way) and
§16.15.9's own table records the shipped `M` moving **−2.4 %** and `B_Q` **−2.9 %** across the same split.
A 5 nm band sitting near the clamp edge is exactly what a diffuser washes out.

⇒ ⛔ **This is the one exclusion §12.2's corpus makes**, and it is stated rather than buried: with those five
runs left in, `R`'s corridor is **−0.494 (OVERLAP)** and the result collapses. The exclusion is defensible —
that session exists *to be* an optical A/B, and §16.26.6 rejected the improvised paper diffuser outright
(14× the light for the smaller half of the problem) — but it is a real condition on the claim.

⚠⚠ **AND IT IS A LIVE WARNING ABOUT `SPEC_lamp_rebuild.md`.** An optical change the shipped metric shrugs off
can **erase** this one. Before `R` is built on anything, it must be established that it survives the rebuild
the lamp spec proposes — and there is currently no reason to assume it will.

#### ⭐ 12.4a · The mechanism, and it makes the SOLVENT part of this metric's specification  *(2026-08-24)*

`SPEC_color_retrieval.md` §7.16.4a offers a physical account of §12.4, prompted by Edwin observing that
the 624 nm peak became **more pronounced in sunflower oil — and in white spirit**. Both are nonpolar and
index-matched to the oil (n ≈ 1.44 and 1.473 against the oil's 1.47) where isopropanol is polar at 1.377,
so both DISSOLVE the oil where isopropanol only emulsifies it.

⇒ **A grating spectrograph maps input angle onto wavelength.** Micron droplets scatter into a forward
lobe ~17° wide at 600 nm, so an emulsion broadens the instrument's effective linewidth. Narrow features
wash out; broad ones survive — which is exactly §12.4's diffuser result (`P2` 0.066–0.072 → 0.000–0.031
while `Q%` does not move), with the emulsion acting as a weak diffuser distributed through the sample
instead of sitting in front of it.

⛔ **If this holds, `R` is the most scatter-sensitive quantity in the project, and the SOLVENT is part of
its specification rather than a convenience.** It also predicts a narrower entrance aperture would
recover some of the band in isopropanol, at the cost of light.

⏸ **Untested.** The decisive experiment is E3 of `SPEC_color_retrieval.md` §7.16.5: measure the WIDTH of
the 608–610 nm lamp line with an isopropanol fill and with a white-spirit fill. Resolution loss broadens
it; veiling glare would shorten it without broadening. One number off two spectra.

### ⚠ 12.5 · What `R` is measuring, and the honest doubt

⭐⭐ **Two peaks means two pigments — and the 624 nm one has a name.** `KB_spectroscopy_physics.md` §4.1
puts **protochlorophyll(ide) *a* `Qy` at ≈ 623 nm (80 % acetone) / 626 nm (methanol)**. The four white-spirit
fills land at **622.8 · 623.2 · 624.8 · 625.0 nm** — inside that literature range, from an instrument that
was not looking for it. ⭐ That is a fourth independent confirmation of §4.1's pigment identification, and it
arrived by accident. ⇒ `R` is a **pigment-composition** ratio, which is why it survives a solvent change that
moves `Q%` by 18 σ.

⚠ **And it raises a question §4.1 can answer and this section cannot.** In isopropanol the band's maximum
sits at **≥ 628 nm** (§12.6) — which is where §4.1's table puts *fluorescence*, and where the
**protopheophytins** (1.1–35.5 % of the protochlorophylls, a storage-degradation product) would be expected.
⛔ Whether the 5 nm shift is solvatochromism or a different pigment being resolved is **open**, and it
matters: if it is the latter, `R` is measuring the degradation product directly.

⚠ **But the green class is broad — 0.541 to 1.183** — so `R` is carrying **oil identity as well as quality**,
and in a corpus where each oil appears at essentially one age those two are only partly separable. §12.3(c)
is the only evidence that the quality half is real, and it is n = 3.

⭐ **The one oil the two metrics disagree about is the one the archive argued over.** Spar Premium g.g.A.
(`20260807C`) reads **brown** at 0.350–0.359 under `R`, and **green** at 17.1–18.3 under `Q%`.
⚠ **§16.30.1a is "THE THIRD RELABEL — `Spar Premium` → BROWN again"**, and
`SPEC_v_metric_integration.md` §4.3 records `T_V` as *contradicting* that relabel in as many words. ⇒ **`R` agrees with the relabel and
`Q%` does not.** ⛔ That is one oil and it is not proof of anything — Edwin's relabel is itself a judgement,
not a reference measurement — but it is the opposite of a miss, and it is worth putting on the record.

⛔ **76 of 190 reports are not scored**: the 63 loose root one-offs, `20260806A` and the `20260811A` lamp
study. **39 of the 63 have a NEGATIVE `R`** — no 624 nm band above the 613 anchor at all — and 46 fall
outside `Q%`'s own 12–22 verdict band. Mixed rigs, mixed doses, no oil identity on disk. Unusable for either
metric, and they are excluded from **both** sides of every comparison above.

### ⭐ 12.6 · Both bands are only *measurable* in white spirit — because they are TALLER there, not because they moved  *(⛔ corrected 2026-08-21)*

| | n | maximum found at ≤ 627 nm | median position |
|---|---|---|---|
| labelled **isopropanol** runs | 110 | **7 %** | 628.8 nm |
| **white spirit** runs | 4 | **100 %** | 624.0 nm |

> ⛔ **AS FIRST WRITTEN, AND NOW WITHDRAWN.** *"The defensible statement is that the band's maximum sits
> ≥ 5 nm bluer in white spirit. The same holds at 568 nm: `Pigment D_Q` pins at the 577–581 window edge in
> every isopropanol run and is an interior peak at 567–568 nm in all four spirit runs."* Both halves read a
> **rank change as a wavelength shift.** `SPEC_capture_quality.md` §16.12.7f carries the full correction.

⛔ **At 568 nm there is no shift at all.** The band sits at 568 in **both** solvents. What competes with it is
a **~2 nm instrument feature at 580–581 nm** — the Bayer channel crossover of `DOC_lamp_rebuild.md` §6, where
reference throughput bottoms at 581 nm and then jumps +17 %/nm. In isopropanol the pigment band is small and
the artefact wins the argmax, so a peak-finder reports "580"; in white spirit the band roughly doubles and
overtakes it, so the finder reports "568". `KB_spectroscopy_physics.md` §4.1a already acted on this when it
moved our Q band from ≈ 574 to 568.

⛔ **At 624 nm the question is UNANSWERABLE, not merely unproven.** The clamp ends at **630**, so a maximum
"at 628.8" means *still rising at the edge* — the isopropanol band's true position is **not measured**.
"≥ 5 nm bluer" asserts a difference between two positions when only one of them exists. Whether the band moved
bluer, or merely grew tall enough to crest inside the window, cannot be told from data that stops at 630.
⚠ **This is not a fifth argument for the red extension** — it is a concrete instance of §13.6's fourth
line, *"Qy read as a shoulder, never as a band"*. The count stays at four.

⭐⭐ **What replaces both, and it is stronger.** Measured as a height above a local chord on Soret-normalised
absorbance — so a flat or smooth pedestal cancels — the 568 nm band runs **0.087–0.213** across 106 labelled
isopropanol fills and **0.235–0.289** across the four white-spirit fills: **no overlap on 110 fills.** Per oil
it roughly doubles (Lugitsch 2.25×, Billa Clever 1.73×). ⛔ Not turbidity — the correlation of normalised
turbidity with the 624 nm height across the isopropanol archive is **−0.016**, and the spirit fills are *more*
turbid than the clearest isopropanol ones while carrying taller bands. ⚠ **The cause is unsettled**; the
package/sieve effect predicts the opposite sign.

⇒ ⭐ **`R` is not an argument for the hydrocarbon, and this correction does not touch it.** `R` is built from
band heights against fixed anchor windows and never from a fitted peak position, so nothing above changes a
number in §12.2. It works on the shipping solvent. What white spirit buys is that both bands become **large
enough to measure well**, which is how the metric got noticed at all.

### ⏸ 12.7 · What has to happen before this is more than a hypothesis

| | |
|---|---|
| ⭐⭐ **1 · fresh vs aged on a SECOND oil** | the single experiment that decides quality-vs-identity. §12.3(c) is one session wide and its corridor is 0.020 |
| ⭐ **2 · survive the lamp rebuild** | §12.4 says an optical change can erase the band. ⛔ Test before ordering, not after |
| ⭐ **3 · a designed dilution series** | `R` is dilution-invariant *by construction*; that has not been **measured**. §2's Kiendler set (`B_Q` spans 48 %) is the corpus for it and the analysis is free |
| ⚠ **4 · a real threshold** | `T = 0.510` is a fitted midpoint. §16.17's mistake was deriving a threshold from too little; do not repeat it |
| ⛔ **not now** | no gauge, no plugin row, no verdict. `V`/`Q%` ships unchanged |

⚠ **And §16.12.7e's rule was bent to produce §12.2.** It says *"the 143-report archive is not reprocessed."*
It was, by `diagnostics/peak_ratio_archive.py`. ⭐ No shipped constant was touched and no archived verdict was
restated — `Q%` appears only as a like-for-like control — but the rule carved no such exception, so **Edwin
rules on it.**

---

### ⭐⭐⭐ 12.8 · `dQ100` — THE METRIC THAT WAS ACTUALLY DECIDED  *(Edwin 2026-08-21; supersedes `R` above as the candidate)*

⭐ **§12.0–§12.7 are kept as the reasoning that got here, and `R` is no longer the proposal.** The same
evening's work produced a better construction from the same two bands, and Edwin chose it. The path was:
`R = (2)/(3)` → Edwin's `(3)/(2)` → the SNV-580-aligned view → and out of that, algebraically, `dQ`.

```
                mean A over [563, 573]  -  mean A over [623, 626]
  dQ100 = 100 x ---------------------------------------------------
                        sd of A over [448, 626]
```

| | |
|---|---|
| **`A`** | the **de-spiked RAW absorbance** — ⛔ no baseline, no pedestal correction, no SNV applied first |
| ⭐⭐ **sampling** | **NATIVE**, the convention `V` uses (§10.1a). ⛔ **Not** a resampled grid — see §12.8b |
| **sign** | higher = browner. ⭐ Negative means the 624 band stands *taller* than 563–573 — the intact-pigment state. **Zero is a real landmark, so there is no shift and no offset constant** |
| **threshold** | `T = 30.0`; green `< 26.6` · borderline `26.6–33.5` · brown `> 33.5` |

#### ⭐ 12.8a · Why it is the same thing Edwin was reading off the SNV plot

He had been reading `y(568) − y(624)` in the SNV-580-aligned view. Written out:

```
  y(568) - y(624) = [(A568-mu)/sd - (A580-mu)/sd] - [(A624-mu)/sd - (A580-mu)/sd]
                  = (A568 - A624) / sd          <- mu AND A580 both cancel
```

⇒ **the 580 alignment and the SNV mean-centring drop out completely; only the SNV *scale* survives.**
Verified numerically on `20260821LugitschA/001`: the direct formula gives `0.039311`, the SNV-580 route
gives `0.039311`. ⚠ The alignment was scaffolding for the eye — it is what exposed the 581 nm crossover as
an instrument artifact (§16.12.7f) — but it is not part of the quantity, so the name must not reference it.

#### ⛔⛔ 12.8b · NATIVE SAMPLING IS LOAD-BEARING, and this was nearly shipped wrong

The first written definition said *"resample onto 448–626 nm in 0.25 nm steps."* Measured over the 68-run
corpus, that is **a different metric**:

```
                green max   brown min   corridor       T
  0.25 nm resample  +26.28     +32.99     +6.714      29.64
  NATIVE            +26.61     +33.45     +6.846      30.03      <- validated, and better
  max per-run difference 0.889 units, mean +0.458
```

⭐ Native is the project's existing convention, gives the *wider* corridor, and lands `T` on a round 30.0.
⚠ `tests/test_v_metric_windows.py`'s sibling must assert the convention, or the two will drift and
**nothing will error**.

#### ⭐⭐ 12.8c · Why `dQ100` beat `R` and `(3)/(2)` — the denominator is the whole story

The Billa Clever pair of 2026-08-21 is the only stress test on record: two pours of ONE dilution, one of
them the most turbid fill in the archive (`A_valley` 0.2647).

```
   metric on BC-1 (turbid) vs BC-2 (clean)      spread as % of the oil-to-oil gap
   ------------------------------------------------------------------------------
   (2) P2 alone           0.1222 / 0.0834             ~85 %   ruined
   (3)/(2)                2.2828 / 2.9079             ~57 %   ruined
   R  = (2)/(3)           0.4381 / 0.3439             ~24 %   damaged
   Q%                    21.832  / 22.038             ~ 2 %   survives
   dQ100                 +72.7   / +70.9              ~ 2 %   SURVIVES
```

⭐ **`R` and `(3)/(2)` carry identical information and are not equally good.** The noise lives in `P2`, a
small band height (0.1222 → 0.0834, nearly halving). In the **denominator** it is amplified (spread 0.625);
in the **numerator** merely scaled (0.094) — 6.6× less scatter for the same content. ⇒ **`R` is strictly
better than `(3)/(2)`**, and both are beaten by `dQ100`, whose denominator is a whole-window `sd` that a
local pedestal barely moves.

#### ⭐ 12.8d · Averaging around the peak — Edwin's suggestion, and it fixed the dilution problem

Sweeping the half-width `w1` around 568 nm (v1 = a point read, v2 = a 10 nm window):

```
    w1    corridor   corr/gap  |  dose drift (Kiendler, 48 % span)  drift/corridor
   -------------------------------------------------------------------------------
     0     +0.0229    0.055    |          0.0441                       1.9x  FAILS
     4     +0.0346    0.083    |          0.0353                       1.0x
     8     +0.0559    0.136    |          0.0319                       0.6x  OK
    10     +0.0671    0.166    |          0.0335                       0.5x  OK   <- SHIPPED
    12     +0.0777    0.194    |          0.0392                       0.5x  (touches 574)
   -------------------------------------------------------------------------------
   leave-one-oil-out chose w1=12 in 8/8 folds, 64/68 = 94 % held out
```

⭐⭐ **It nearly triples the corridor AND drops the dose drift below it** — v1 was *not* dilution-invariant
in practice (1.9× its corridor) despite being so algebraically; v2 is (0.5×). The dose slope barely moved
(−0.142 → −0.108); **what changed is that the corridor got wide enough to absorb it.**

⚠ **`w1 = 10`, not the 12 the search prefers.** 12 spans 562–574 and touches the 581 nm crossover ramp, for
14 % more corridor. 10 spans 563–573 and stays clear. ⛔ The half-width is still **fitted on the corpus it
is scored on** — 94 % leave-one-oil-out says the choice is stable, but the corridor value is not free.

### ⛔ 12.9 · THE BAND-PAIR SEARCH — and the trap it walks into

All 2 628 pairs of the form `[A(λ1) − A(λ2)] / sd(448–626)`, ranked by corridor/gap, with leave-one-oil-out:

```
    L1     L2    corr/gap   held out
   574    626     0.340     66/68 = 97 %, and 8/8 folds chose L1 in {574,576}
   576    624     0.320
   ---------------------------------------------------------------------------
   568    624    (dQ100)    the shipped construction
```

⛔⛔ **574–576 is the ramp into the 581 nm crossover** — the lamp feature §16.12.7f identifies, which is not
a band. The search's honest answer is that *the instrument's own artifact discriminates these oils better
than the 568 pigment band does*. That may even be true: ④'s height is not the lamp alone but **how the
reference and the sample fail to cancel across the handover**, which is instrument × sample. ⇒ it carries
real oil information **and it will move with any optics change.** §12.10 is why that disqualifies it.

⚠ A variant anchored at 632–635 scored better still and is rejected outright for reading **outside the
440–630 capture clamp**.

### ⛔⛔ 12.10 · THE DIFFUSER TEST — the one known failure mode, now measured on `dQ100`

`20260727B` is the archive's diffuser A/B test (§16.7.2f: it came off between run 003 and run 004). One
oil, one fill, an instrument change and nothing else:

```
   metric        diffuser IN (n=5)     diffuser OUT (n=4)   shift   % of class gap   vs corridor
   -------------------------------------------------------------------------------------------
   Q%           16.534 +/- 0.478      15.827 +/- 1.038      0.707       16.9 %      (no corridor)
   dQ100 v2     21.416 +/- 4.440      15.219 +/- 3.185      6.197       14.9 %      0.9x  SURVIVES
   dQ100 v1     23.290 +/- 4.337      19.529 +/- 3.060      3.761        9.0 %      1.6x  BROKEN
   R = (2)/(3)   0.121 +/- 0.126       0.635 +/- 0.013      0.514      115.9 %      8.3x  DESTROYED
```

⭐ **`dQ100 v2` is the only candidate that survives** — and §12.8d's window widening is again what saved it.
⚠ But by **0.9×**: an optics change of that size eats 92 % of the decision margin. It does not flip this oil
(which sits 9–15 units from `T`), but an oil near the line would flip. In *relative* terms (14.9 % of the
class gap) it is marginally steadier than `Q%` at 16.9 %.

⚠⚠ **`SPEC_lamp_rebuild.md`'s rebuild is a far larger optical change than a paper diffuser. `dQ100` must be
tested against it BEFORE the emitters are ordered, not after.**

### ⭐⭐⭐ 12.11 · R1 — THE TURBIDITY ARM, and the confound is not there  *(run 2026-08-21, analysis only, no rig time)*

**The question this had to answer**: `dQ100`'s numerator is a difference, so a **flat** pedestal cancels —
but real Mie turbidity has spectral **slope**, which does not cancel and does move `sd`. Per-session
correlations against `A_valley` ran as high as `r = −0.94`. ⇒ **did `dQ100` separate green from brown
because brown oils scatter more?** Different answers make it a different product.

**The corpus**: 68 isopropanol runs, 44 green / 24 brown. **Turbidity index `tau = A(510–540) / A_Soret`** —
concentration-free, because both terms scale with `c` (the raw `A_valley` is not, across oils).

#### 12.11a · Is turbidity confounded with class at all? — partly, and weakly

```
   green  tau 0.1087 +/- 0.0335  [0.0472, 0.2207]
   brown  tau 0.1389 +/- 0.0406  [0.0621, 0.2308]      Cohen d 0.84
   the two ranges OVERLAP over 0.0621 .. 0.2207 — nearly the whole span
```

Brown oils are somewhat more turbid. Not nothing, and not enough on its own.

#### ⭐⭐ 12.11b · THE DECIDING TEST — the within-session and between-class slopes have OPPOSITE SIGNS

ANCOVA: the slope of the metric on `tau` pooled from **within-session deviations only**, so every
between-oil difference is removed. That is the *pure* turbidity coefficient.

```
              within-session slope      between-class slope     ratio
   dQ100          -21.4  (r -0.13)          +1349.1           -63x   OPPOSITE SIGN
   Q%             +10.4  (r +0.36)           +138.5           +13x   same sign
```

⭐⭐⭐ **If turbidity drove the class separation the two slopes would agree. For `dQ100` they point in
opposite directions and differ 63-fold.** Within one session — same oil, same dilution, turbidity the only
thing moving — more turbidity drives `dQ100` **down**; between the classes it goes **up**. Turbidity works
*against* the separation, not for it.

⇒ and therefore **adjusting for turbidity makes the corridor WIDER**: `+6.846 → +6.950`.

⚠ **The contamination belongs to `Q%`, not to `dQ100`.** `Q%`'s within-session slope has the **same** sign
as its between-class slope, and turbidity explains 21 % of its variance against `dQ100`'s 12 %.

#### ⭐⭐ 12.11c · At MATCHED turbidity the classes still separate — in every bin

```
    tau bin        nG   nB   dQ green   dQ brown     gap
   0.060-0.090      9    2     -4.01      43.62     27.50   CLEAN
   0.090-0.110      8    5     -6.27      41.34      6.85   CLEAN
   0.110-0.130     13    2      7.90      46.47     21.81   CLEAN
   0.130-0.160      9    9     12.09      44.89     14.53   CLEAN
   0.160-0.240      1    6   (too few green)
```

**Clean in all four populated bins.** The tightest, 0.090–0.110, still gives 6.85 — essentially the
full-corpus corridor. ⇒ **nothing is lost by holding turbidity constant.**

#### ⛔ 12.11d · CORRECTIONS TO THIS DOCUMENT'S OWN EARLIER ALARM

1. **The `r = −0.94` figures were over-read.** They are per-session correlations on `n ≈ 6`. The pooled
   within-session slope is **−21.4 with `r = −0.13`**, and the individual session slopes scatter wildly:
   −718, −644, −235, −142, −15, +13, +75. A large `r` on six points with a small real slope is noise
   wearing a coefficient. The confound was raised three times in this document and it is not there.
2. **A naive pooled regression of `dQ100` on `tau` is the WRONG adjustment** and was tried first. It gives a
   `+207.6` slope and a residual corridor of `−17.4` — because the classes differ in **both** `tau` and
   `dQ100`, so a pooled fit removes the class signal along with the covariate. ⚠ The within-group
   (ANCOVA) coefficient is the correct one, and it is what §12.11b uses.

#### ⚠ 12.11e · WHAT R1 DOES NOT CLAIM

⛔ **R1 is an ELIMINATION, not an identification.** It rules out the one alternative explanation we could
name; it does not show what `dQ100` *is* measuring. **§12.12/S1 — the acid test — is what would make the
claim positive**, and it remains unrun.

⚠ It is also observational. `tau` is a proxy, the bins are unbalanced (2 brown runs in two of them), and no
fill's turbidity was ever *set* — only observed. **The designed version is still `R2`**: one monitored fill
with `W8`'s columns, read through a full clearing curve, compared at matched `A_valley` by §39.1's method.

### ⏸ 12.12 · WHAT IS STILL OPEN

| | |
|---|---|
| ⛔ **the lamp rebuild** | §12.10 — `dQ100` survives a diffuser by 0.9× its corridor; test before ordering |
| ⚠ **the settling curve** | `dQ100` has **never been recorded per-frame**; no run on disk carries `A(563–573)` or `A(623–626)`. `W8` then one run. ⛔ Not retroactive |
| ⚠ **the fitted half-width** | §12.8d — 94 % leave-one-oil-out, but chosen on the corpus it is scored on |
| ⚠ **the bimodal green class** | Ja!Natürlich (−26) and Lugitsch (−16) sit 30 units below Kiendler / Steirerkraft / Spar ggA (+11…+19) — four corridor-widths. Real structure or a mislabel |
| ⭐ **S1, the acid test** | pheophytinisation is acid-catalysed and irreversible. ⚠ **Run it in isopropanol** — acids barely dissociate in a de-aromatised hydrocarbon |



---

## ⭐⭐ 13 · THE EVENING SESSION — one axis, one rule, and what it refutes  *(2026-08-21 evening; analysis only, no rig time)*

§12 chose `dQ100`. The same evening Edwin asked four questions in a row — *is `Q%` more reproducible · can
`A_valley` be the baseline · can the two bands be compared against a local reference · can `Q%` and
`dQ100` be combined* — and answering them on the archive produced a tighter picture than any of the
individual answers. **The decision that came out of it is in `ROADMAP.md`'s 2026-08-21 evening block:
`Q%` keeps the gauges, the history tracker and the verdict; `dQ100` ships as a scalar.** This section is
the research record.

⭐ The mechanism is written up for readers rather than for us in [`DOC_sample_physics.md`](DOC_sample_physics.md)
§3.4a and [`DOC_metric_algebra.md`](DOC_metric_algebra.md) §5.8, both with the see-saw figure.

**The corpus throughout**: 88 labelled isopropanol runs (55 green / 33 brown, 20 oils), recomputed from
each report's own de-spiked trace, diffuser-IN runs and the opaque fill excluded.

### ⭐⭐⭐ 13.1 There is ONE axis, and `dQ100` already reads it

The measured green→brown direction in SNV space is **+0.12 at 571 nm and −0.14 at 624–626 nm** — so the
optimal linear read available inside 440–630 nm is a positive weight on the Q band and a negative one on
the Qy band, which is what `dQ100` computes. Correlations over the corpus:

```
   r(Q%,       dQ100) = +0.842        r(Q%_0.75,  dQ100) = +0.990
   r(B,        dQ100) = +0.997        r(chord dQ, dQ100) = +0.984
```

⇒ ⛔ **Metric algebra inside this window has hit diminishing returns.** The variants differ in
**conditioning, not in information**. What is left is windows, conditioning, and the clamp (§13.6).

### 13.2 The two packagings, both `0 / 88` with 100 % leave-one-oil-out

```
   B     = dQ100 + 1.617 x Q%                                          T = 58.0
   Q%_k  = 100 [ (A_Q - A_valley) - k (A_Qy - A_valley) ] / A_Soret    k = 0.75, T = 11.36
```

| | corridor | within-oil sd | within/corridor | diffuser | dose | at its own `T` |
|---|---|---|---|---|---|---|
| `Q%` | ⛔ −2.807 | 1.100 | — | 0.25× | 0.38× | 7 / 88 |
| `dQ100` | +6.846 | 4.308 | 0.63× | 0.89× | 0.47× | 0 / 88 |
| `Q%_0.75` | +2.517 | 0.717 | **0.28×** | 0.87× | 0.29× | 0 / 88 |
| `B` | +10.136 | 4.044 | 0.40× | **0.71×** | **0.23×** | 0 / 88 |

⭐ **`Q%_k` is `Q%` with a red-band term**: `k = 0` is `Q%` exactly, and anywhere in `k = 0.5 … 1.0` it goes
from 7/88 to 0/88. It keeps `Q%`'s units and the continuity of 143 archived reports for **one new constant
and one extra band mean**. ⚠ Whether a form clears §16.31.3a's bar is a *continuous* function of how much
`Q%` weight it carries (`k = 0.50` and `B` pass; `k = 0.75` gives 3; `dQ100` gives 2) — it is **not** a deep
property of `B`, and it costs ~30 % of the decision margin.

⛔ **Every constant here is fitted on the corpus it is scored on.** Broad plateaus and 100 % LOO say the
*choices* are stable; they do not make the corridors free. **`ROADMAP.md` M9 — pre-registration before the
next rig session — is the only route from "best candidate" to "validated".**

### ⚠⚠ 13.2a `Spar Premium` is not a labelling problem more fills can fix

Every `0 / 88` in the table above is conditional on one three-run tube whose class has never been clear.
⭐ **The evening's own data says the reason is that the oil is genuinely intermediate.** Excluded from the
fit, `B` opens a **15-unit** gap — green max **52.93**, brown min **67.93** — and `Spar Premium`'s three
runs land **inside** it, at **63.08 / 63.06 / 65.78**, 70–85 % of the way across and on neither side.

⇒ ⛔ **More fills of `Spar Premium` would settle whether that TUBE is representative — a real question —
but nothing about the LABEL.** If the oil sits between the classes, measuring it more precisely locates the
middle more precisely. And §16.31.3a already forbids settling it from the spectrum: one pigment system, so
every spectral statistic is a projection of the same chemistry and none of them is independent evidence.

| the two ways out | |
|---|---|
| ⭐ **exclude it, and say so** | report **0 / 85** with the exclusion stated — the branch §16.31.3a explicitly allows. Both `dQ100` and `B` pass it |
| ⭐⭐ **ground truth from OUTSIDE the spectrum** | taste, the mill's roast record, provenance, for that one oil. Permanent, and nothing else is |

⚠ ⇒ **Any headline of the form "0 / 88" must name its labelling.** The honest form of every count in §13.2
is *"0 / 85 with `Spar Premium` excluded, and 0 / 88 under the archive's current label for it."*

### ⭐⭐ 13.3 THE RULE — differences survive, ratios do not

> **Differences of equal-width windows survive; ratios of baseline-subtracted quantities do not.**
> Every candidate baseline in this spectrum — the valley, the trough between the bands, the flat bottom,
> the 607 nm bump — varies **more between fills than between oils**. A difference cancels it exactly; a
> ratio multiplies by it.

⚠ **The windows must be EQUAL WIDTH**, or the baseline does not fully cancel: 20 nm against 9 nm leaves a
residual `b × Δwidth` term (measured, r = 0.926 rather than 1.000 between the line-subtracted and the
no-line forms).

⇒ **No future candidate may divide by a locally-estimated baseline.** This is §12.8c's `R`-versus-`(3)/(2)`
finding re-derived from three independent directions in one evening, which is why it is promoted to a rule.

### ⛔ 13.4 REFUTED — so nobody re-runs them

| idea | result |
|---|---|
| `A_valley` as the **denominator** of `dQ` | worst measured, **11 / 88**. The level swings **19×** across the archive (0.013–0.248 A) — it is the fill's pedestal, not the oil's property |
| the 590–615 **rise** as a slope or a step | ⛔ 5–43 / 88. The 607 nm lamp line sits in the middle and the two sides behave differently |
| the **trough** between the bands as a baseline | ⛔ **there is no trough**: the argmin pins against its own search edge in 43 / 93 runs, and with the bump excised the deepest point is a coin flip between two sides 10 nm apart (sd 5–7 nm) |
| one horizontal **line** + the two band **areas** above it | ⛔ 7–15 / 88, under all four ways of drawing the line |
| the **two-species model** *inside 440–630* | ⛔ PC1 of the SNV'd red region is the **lamp**, not the oil (46 % of variance, a dipole on 608–610 nm, and it does **not** separate the classes) · ⛔ **no isosbestic point** (every class-mean crossing scores *d'* = 0.01–0.48) · ⛔ the archive cannot supply the degradation direction (within-fill drift vs the class axis, cos ≤ 0.57; the +24 h aged pair only +0.40) |
| the Qy **peak position** by parabola | ⛔ unconstrained on a shoulder (green 626.4 ± 129.6 nm) |
| ⭐ the pedestal's spectral **SLOPE** as a second, non-pigment channel *(2026-08-21)* | ⛔ **a CALENDAR artefact.** `[A(470–490)−A(600–620)]/A_Soret` scores **F = 32.07** between sessions against **6.97** for the turbidity level, and is non-monotone in `Q%` — so it looks like an independent axis. It splits **perfectly by date** over 12 sessions and 52 fills: **0.055–0.078** up to 2026-08-07, **0.018–0.029** from 2026-08-12 on, **no oil on both sides**. A rig-or-processing era boundary, not a property of any product. ⚠ **The near-miss is the lesson** — an unattributed channel cannot tell a rig change from an oil change (`DOC_metric_algebra.md` §1.5a). `diagnostics/pedestal_slope_era.py` |

⭐ **Kept as candidates, not pursued:** the **valley+591–597 chord** (noise-to-margin 0.24×, but it is a
third band read disguised as a baseline — `A(600–606)/A_Soret` carries class signal at *d* = 1.23 while
`A(623–626)/A_Soret` is the QUIETEST window in the red at *d* = 0.45); and the **red centroid** (green
617.31 ± 0.63 nm vs brown 611.87 ± 1.39 nm, `0 / 88`, and the **best diffuser robustness measured, 0.26×**
— but truncated at the clamp).

⚠ **The 607 nm lamp line is the trap in this region.** A right-anchor scan shows a broad plateau at
588–603 and a **cliff at 606** (corridor +15.5 → −6.9, 7/88, diffuser 2.50×). The ~1 nm de-spike does not
remove the line (FWHM 2.7 nm).

### ⭐⭐ 13.5 THE COUPLING, THE CONSERVED SUM — and a correction to §3.2's prediction

Measure **both** red features the same way — height above the valley, over the Soret:

| across the 20 oil means | green | brown | Cohen's *d* |
|---|---|---|---|
| `h(568)` | 15.80 | 20.00 | +2.78 |
| `h(624)` | 12.78 | 7.55 | −2.28 |
| **`h(568) + 0.68·h(624)`** | — | — | ⛔ **+0.28** — class-blind |
| `A_Soret` — the shared denominator | 0.7522 | 0.7777 | ⛔ **+0.16** |

⭐ **The coupling changes sign between the two levels**: `r(h568, h624)` is **−0.832** between oils
(composition — the plank tips) and **+0.811** within one oil's repeat fills (amount — the plank lifts).
A shared divisor moves both heights the *same* way, so a divisor artefact could only ever produce a
**positive** correlation. ⇒ the negative one is chemistry.

⭐ **The sum is conserved**: CV **5.4 %** across oils against 13.4 % and 30.6 % for the bands alone —
5.7× steadier than the noisier band and unable to tell green from brown. That is an **empirical stand-in
for an isosbestic point**, arrived at without the red extension. ⚠ The unweighted sum scores almost as
well (CV 6.5 %), so the effect is not a knife-edge fit.

⛔⛔ **AND THE CORRECTION.** §3.2 predicts that demetallation *weakens* the Soret. **We cannot see that.**
At *d* = 0.16 across oils the Soret is class-blind on this instrument, and the small sign it carries runs
the **other** way. Dose dominates it, and dose is not a class property. Two consequences:

1. ⭐ **`Q%`'s discrimination lives in its NUMERATOR** (*d* = 1.69) and not in a ruler that shrinks for one
   class (*d* = 0.30). Dividing by the Soret lifts *d* from 1.69 to **2.78** — it carries the nuisance and
   none of the effect, which is exactly what a normaliser should do. **The failure mode worth fearing is
   not present.**
2. ⚠ **§3.2's prediction remains untested here**, and anywhere it was treated as confirmed should say so.
   ⚠ The running pair `20270729C` / `20260731A` shows `A_Soret` 0.828 vs 0.730 (*d* = −2.77), which looks
   like a class difference and is a **dose difference between two fills**.

⇒ ⭐⭐ **It sharpens `S1`, the acid test, into a falsifiable prediction.** Not merely *"does the slope
collapse"* but: acidify one half of a split fill and **`h(568)` must RISE, `h(624)` must FALL, and their
SUM must stay put.** A conversion has to conserve the sum; a solvent artefact, a turbidity change or a
dilution error would not.

### ⛔⛔ 13.6 THE CLAMP IS NOW THE BINDING CONSTRAINT, not the arithmetic

Four independent lines hit the same 630 nm wall in one evening:

| line | how it hits the clamp |
|---|---|
| the red centroid | integrates to 626 nm ⇒ a truncated centroid is biased by wherever you truncate |
| the two-species model | the chl→pheo isosbestic lives near 660–680 nm, outside |
| valley-to-valley baselines | only ONE real valley is inside the window (500–560); the second sits ~640–660 |
| Qy itself | read as a **shoulder**, never as a band — which is why the parabola fit is unconstrained |

⇒ ROADMAP item 5's **red extension past ~660 nm** gained four arguments it did not have that morning, on
top of `KB_spectroscopy_physics.md` §4.1's own note that the widening should be **re-costed**. ⚠ None of
these is a metric problem.

### 13.7 ⚠ The solvent, re-measured

`Q%`'s white-spirit shift is **differential, not common-mode**, which is why no calibration constant fixes
it: green Lugitsch rises **+6.71** and brown Billa Clever **+2.08**, so the class gap collapses from
**5.85 → 1.23** (×0.21) and both oils cross `T`. `dQ100`'s gap **widens** (56.2 → 77.5). ⭐ Turbidity
explains only ~7 % of the green shift (the archive's within-session slope predicts +0.46 against +6.71
observed) — the rest is solvent chemistry.

⚠ **Neither metric is solvent-portable in VALUE**; `dQ100` shifts *more* (+32 on Billa Clever). What
differs is that its shifts do not cross its threshold. **Both thresholds are solvent-specific.**
⚠ And arm A failed its own `A_valley` gate (§16.12.7f), so the direction is trustworthy and the magnitude
is not.

---

## ⭐⭐ 14 · THE TRIGLYCERIDE ARM — sunflower, and what it does to the three metrics  *(2026-08-22/23; analysis only)*

> Pumpkin oil diluted in **sunflower oil** instead of isopropanol — run as a feasibility test for **MCT**, not
> as a solvent proposal. `20260822BillaClever/001` and `20260822Lugitsch/002`, both the standard 8 ml + 2
> capillaries, one session. A third fill at **3 capillaries** followed on 08-23.
> Written up for circulation as `docs/DOC_solvent_and_hue.md` →
> `spectracs-references/business/internal/commmunication/Spectracs_SolventAndHue_2026-08-23.pdf`.

### ⭐ 14.1 The headline — the baseline goes away

| | Billa `001` | Lugitsch `002` |
|---|--:|--:|
| `Q%` | 21.44 | 16.21 |
| `dQ100 v2` | +63.79 | −21.74 |
| `R` = A(623–626)/A(563–573) | 0.673 | 1.321 |
| `A_Soret` | 0.797 | 0.596 |
| **`A_valley`** | 0.165 | **0.018** |

**`A_valley` = 0.018 is the second lowest of 116 archived runs and the lowest at a usable pigment load**
(`valley/Soret` = 0.030 against an archive median of 0.13). RI: IPA 1.377, sunflower 1.473, pumpkin ≈ 1.47 —
the oil was never in solution in IPA, it was dispersed. ⭐ That fill also **settled immediately**:
`SETTLED_IMMEDIATE` at 106 s, `Q%` span **0.03** across seven reads, `tailSd` 0.0069.

### ⭐⭐ 14.2 The floor is a phase, not a pedestal — and its exponent is measurable

Define `F` = mean absorbance over pigment-free windows (472–500, 505–555, 588–604 nm). Four independent lines
say `F` is **undissolved oil**:

1. **spectrally flat** across 470–605 (IPA excess `S` = −3.1, sunflower −0.07 per 1000 nm) ⇒ particles ≫ λ,
   geometric regime. ⛔ Rules out sub-micron scatter (λ⁻¹…λ⁻⁴) *and* humic browning (exponential, S ≈ 10–20).
2. **supra-linear in loading.** `F ∝ c^p` with `c` measured pigment-only:

   | series | p | r (log-log) |
   |---|--:|--:|
   | Billa 20260812 (a dilution series) | **4.27** | 0.979 |
   | Lugitsch 20260814 (a dilution series) | **6.23** | 0.984 |
   | ⭐ **Lugitsch 2→3 cap, SUNFLOWER** | **2.04** | *(two points)* |

   `p = 1` is a dissolved component, `p = 0` a fixed jar/instrument term, `p ≫ 1` a solubility limit.
   ⇒ **sunflower is much closer to a true solution than IPA, and MCT should reach `p = 1`.** Two fills at
   different loadings measure it in one evening — a cheap, pre-registerable acceptance test for any new solvent.
3. **survives 300 s of ultrasound** (Edwin, 08-23) — sonication disperses, it cannot dissolve.
4. **collapses in a triglyceride** — `F/A_Soret` = 0.053 on the Lugitsch sunflower fill, the lowest of 31.

### ⚠ 14.3 The 3-capillary fill — Q% is the dilution-invariant one, not `dQ100`

Loading went ×2.21 (nominal 1.5 — a **47 % recipe overshoot**, itself a useful measurement):

| | 2 cap | 3 cap | shift | in fill-σ |
|---|--:|--:|--:|--:|
| **`Q%`** | 16.213 | 16.664 | **+0.45** | **+0.9 σ** |
| `dQ100 v2` | −21.743 | −15.617 | **+6.13** | **+2.3 σ** |
| `R` | 1.321 | 1.155 | −0.166 | — |

⛔ **§12.8d's claim that the widened window made `dQ100` dilution-invariant does not reproduce here** — it moved
2.5× more than `Q%`, and *toward* misclassification. ⚠ The 3-cap fill is past the instrument's edge
(`A_Soret` 1.405; **1.2 DN transmitted at 450 nm**), so `A_Soret` is probably under-read and `dQ100`'s
`sd(448–626)` inherits that. **Take a third loading point downward, not upward.**

### 14.4 Pooled fill noise, and the gaps in units of it

Within-session repeat fills, pooled over 6 sessions: **`Q%` sd 0.515 · `dQ100 v2` sd 2.681.** dQ100 is 5× noisier
in absolute units, so its large gaps must be read against that.

| set | `Q%` | `dQ100 v2` | ratio |
|---|---|---|---|
| white spirit | 1.23 = **2.4 σ** | 77.5 = **28.9 σ** | **×12** |
| sunflower, as measured | 5.23 = 10.2 σ | 85.5 = 31.9 σ | ×3.1 |
| **sunflower, floor-corrected** | 10.61 = **20.6 σ** | 85.5 = **31.9 σ** | **×1.5** |
| IPA, post-settling | 5.86 = 11.4 σ | 57.0 = 21.3 σ | ×1.9 |

⭐ **White spirit is `dQ100`'s strongest evidence on record** — `Q%` collapses to 1.23 units there for chemical
reasons (floor-correcting lifts it only to ~6 σ), exactly as §12.10's "no Soret ⇒ no saturation term" predicts.
⚠ **But half of dQ100's sunflower advantage is the floor suppressing `Q%`**, and the floor is what MCT removes.
In a clean prep the lead is ~×1.5, not "miles".

### ⛔ 14.5 Nothing is solvent-portable in VALUE — and the shift is DIFFERENTIAL

| | IPA | white spirit | sunflower |
|---|---|---|---|
| `dQ100` Billa | 36.6–46.6 (n=9) | 71.7 / 73.4 | 63.8 |
| `dQ100` Lugitsch | −20.6…−11.4 (n=13) | −4.1 / −5.8 | −21.7 |
| class gap | ~57 | ~77 | ~85 |

White spirit → sunflower shifts Billa −8.7 and Lugitsch −16.8 against a fill repeatability of 1.2 — 7 σ and 14 σ,
and **differential, not common-mode**. A common shift could be rescued by re-fitting `T` with one constant; this
cannot. **`T = 18.6` and `T = 30.0` both need re-deriving in MCT.** ⭐ `R`, by contrast, has now held across
three solvents without overlap: Billa 0.506–0.811, Lugitsch 1.024–1.321.

### ⭐ 14.6 The floor cannot be corrected away — one refuted attempt, recorded

`Q%′ = 100(A_Q − A_valley)/(A_Soret − A_valley)` — the same baseline applied to the denominator too — **is worse**:

| set | d(`Q%`) | d(`Q%′`) |
|---|--:|--:|
| IPA only | **9.27** | 5.57 |
| all three solvents | 2.82 | 2.50 |
| within-oil sd, Billa | ±1.00 | **±2.49** |

§13.4 already refuted the adjacent construction for the same reason: *`A_valley` swings 19× across the archive —
it is the fill's pedestal, not the oil's property.* ⇒ **`Q%` works *because* it leaves the denominator alone**;
the floor cancels exactly in its numerator and costs only −27 per A in the denominator. That is the design, and
it is right. **Fix the preparation, not the metric.**
