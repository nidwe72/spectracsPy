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

**Three of the four died on the same fact: the Qy maximum lies beyond 629.8 nm, so the far band is a
truncated flank rather than a resolved band.** A flank has no peak to bracket (C16), no curvature to
differentiate (B), and no turning point for a smooth baseline to pass under (C).

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

| | action | what it unblocks | status |
|---|---|---|---|
| ⭐⭐ **1** | **The capillary protocol** — `SPEC_capture_quality.md` §16.23, gates G1/G2 first | ⭐ within-green grading (SNR 1.8 → 18); a real concentration axis ⇒ **A2 and A4 become measurable**; OD-dosing ⇒ **retires the pedestal correction and A1** | ⏳ capillaries arriving |
| ⭐ **2** | ⭐ **R0b SIMPLIFIED — three oils, ONE evening, standard recipe, one tube each, plus one MCT blank** | the session confound (§3.4); a second brown fill (§2.2); the background *measured* rather than inferred (§7.12) | ⏸ postponed, **now 4 tubes not 9** |
| **3** | ⭐ **The DN guard** — two-sided, per §16.23.8 | stops the blue end silently entering the compressed regime; a precondition for trusting any absolute value | **to implement** |
| **4** | ⭐ **Trim the Soret window to 440–460 → 448–460** | free +7 % / +11 % / −15 % on the three axes; drops the bins §7.13 shows are contributing 28 % of `r_Q`; ⚠ moves the scale | ⭐ **ADOPTED (Edwin 2026-08-04)** |
| ⛔ **4a** | ⭐⭐ **RESOLVE THE DN CONTRADICTION** — our own specs disagree: 2.0–2.6 DN (`DOC_pedestal_correction.md` §7) vs 18–26 DN (`SPEC_capture_quality.md` §16.7.2e) for the same darkest bin | ⛔ **§16.23.6's entire dilution conflict is contingent on which is right.** Archived PDFs store derived spectra, not raw counts, so it needs one live capture — **and the DN guard (item 3) logs it anyway** | ⭐ **resolves itself with item 3** |
| ⛔ **4b** | ⭐ **THE STRAY-LIGHT GATE — block the beam, read `S`** (§16.23.6f) | decides whether the blue floor is quantisation (fixable in software) or stray light (needs baffling). **One capture, one minute** | gated on 4a |
| **4c** | **Dual-exposure absorbance** — low exposure for R, high for S, corrected by log(E_S/E_R) (§16.23.6e) | ⭐ dissolves §16.23.6's dilution conflict outright — both constraints met at 1:250, no lamp purchase | gated on 4b |
| **4d** | ~~analog-vs-digital gain test~~ | ✅ **DONE 2026-08-04: the gain is ANALOG** (no histogram gaps at any setting). ⚠ But the range is only **1.51×**, short of the 2.3× the guard needs — helpful, not sufficient (§16.23.6d) | done |
| **5** | **Extend the red range to ~660 nm** | ⭐ the structural fix — turns both flanks into bands and gives the first genuinely quiet region (§7.8, §7.9b) | hardware, cost unknown |
| **6** | **The validation study** — 12+ greens, 2–3 browns, jury **visual sub-score** recorded separately, plus **roast level** as objective ground truth | whether the instrument measures what it claims. **Never done, and not on any milestone** | open |
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

## 10 · Related documents

| topic | where |
|---|---|
| the metric being replaced, and its algebra | `DOC_metric_algebra.md` |
| the correction this document steps back from | `DOC_pedestal_correction.md` — esp. App. D.6, ch. 13 T4 |
| pigment identity, band positions, Gouterman | `KB_spectroscopy_physics.md` §4, §4.1 |
| the instrument and its limits | `DOC_capture_fidelity.md` |
| the sample and its preparation | `DOC_sample_physics.md` |
| capture-side constraints, series provenance | `SPEC_capture_quality.md` §16 |
| the go/no-go this feeds | `SPEC_capability_proof.md` |
| ⚠ **candidate source, NOT held** — free-base porphyrin band positions (protoporphyrin IX 506/532/580/630 nm) | [MDPI Pharmaceuticals 14(2):138](https://www.mdpi.com/1424-8247/14/2/138) · [PMC7914864](https://pmc.ncbi.nlm.nih.gov/articles/PMC7914864/) |
| ⚠ **the errand** — a primary UV-Vis of *protopheophytin a* | not on the open web; needs Scheer *Chlorophylls* or a primary paper |
