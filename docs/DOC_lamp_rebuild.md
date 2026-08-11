# Rebuilding the lamp — choosing seven emitters on measured noise

> **WHAT IT BOILS DOWN TO**
>
> **The 410–680 study picked the wrong board, and it picked it for a good reason: the evidence it needed
> did not exist yet.** On 2026-08-11 the capture clamp moved to **400 nm** and two runs were taken through
> a DIY violet-fronted lamp. They measure a stretch — 400–440 nm — that no run in the archive had ever
> contained, and they overturn three of that study's inputs at once: the oil's blue absorption is a
> **doublet at 421.4 / 436.5 nm**, not a single band near 439; the camera's blue response is roughly **ten
> times better** than the model assumed; and the arithmetic that converts absorbance to sensor level had a
> factor of 2.2 in the wrong place.
>
> Re-running the choice against **31 425** buildable seven-emitter allocations, scored on the noise the
> metric would actually carry rather than on an emitted-spectrum bracket, puts the published R2 board at
> **rank 206**. The board that wins is a different shape: fewer whites, more violet, and a red part that
> serves 630 nm instead of 660.
>
> ⭐ **Buy: 2 × `4000k-4500k` + 2 × `410nm-420nm` + 1 × `440nm-450nm` + 1 × `480nm-485nm` +
> 1 × `630nm-640nm`.** Seven parts, all Avonec, one order.
>
> ⚠ **Fix the channel-crossover defect first** (§6). It is 0.15–0.24 in A — ten times everything this
> document optimises — and no lamp touches it.

**Companion documents.** `DOC_lamp_410_680.md` is the study this one revises; §8 lists the corrections it
implies. `SPEC_lamp_rebuild.md` is the build sheet. `DOC_capture_fidelity.md` covers the instrument,
`DOC_sample_physics.md` the sample, `DOC_metric_algebra.md` the arithmetic.

---

## 1 · The board

| qty | Avonec part | peak | what it is bought for |
|---|---|---|---|
| **2 ×** | `410nm-420nm` | 421 nm | sits on the measured Soret peak 1 (421.4 nm) |
| **1 ×** | `440nm-450nm` | 442 nm (half 432 / 453) | spans the dip and Soret peak 2 at 436.5, and the shipped 448–460 window |
| **1 ×** | `480nm-485nm` | 480 nm (half 470 / 496) | fills the 476 nm hole every other board has |
| **2 ×** | `4000k-4500k` | phosphor 585, pump 448 | the whole 500–650 backbone: clarity floor, Q band, far anchor |
| **1 ×** | `630nm-640nm` | 636 nm | the 627 nm band and the 620–630 far anchor |

![**Figure 1** — The board, part by part, each normalised to its own peak; black is the sum. The two `4000k-4500k` whites carry everything from 500 nm out — their phosphor tail is also what keeps the quiet window alive without a 660 nm emitter. `480nm-485nm` is the part no other board on this page has, and it sits on the 476 nm hole.](tmp/lamprebuild/board_parts.png)

⚠ **Buy all seven new.** The emitters in the current DIY lamp cannot be identified — its reference resolves
peaks at 413, 431, 464 and 473 nm, and nothing in the Avonec catalogue peaks at 413; Edwin, 2026-08-11:
*"not sure about the LEDs in my current build, might also be partly chinese."* An unknown bin moves the
balance the whole design rests on.

---

## 2 · Three things are now measured that the study had to assume

### 2.1 ⭐ The Soret is a doublet, and its maximum is at 421 nm

`DOC_lamp_410_680.md` Figure 5 states the composite blue maximum sits *"near 440 nm, not at the Soret's
432 nm centre"*. The measurement puts it at **421.4 nm** and resolves **two** peaks with a dip between.

| feature | run 001 | run 002 | Fruhwirth Fig. 3A, digitised |
|---|---|---|---|
| Soret peak 1 | 421.2 | 421.4 | 424.8 |
| dip | 431.8 | 432.8 | 430.5 |
| Soret peak 2 | 436.5 | 436.5 | 436.2 |
| Q | 579.9 | — | 573.8 |
| Qy | — | 627.6 | 629.1 |

⭐ **It is not an artefact of the lamp.** The frames were split into **20 independent 40-row bands along
the slit** and A(λ) recomputed for each: **20 of 20 resolve the doublet**, peak 1 at 421.3 ± 0.9 nm, peak 2
at 436.7 ± 0.9 nm. The lamp's own emitter peaks near 431 — exactly where the absorbance has its *dip* — so
lamp structure would have to work backwards to produce this. And the literature dip sits at 430.5 nm,
1.3 nm away.

⚠ **The literature column is a digitisation, not the authors' claim.** Fruhwirth & Hermetter (2007) states
**no absorption peak position anywhere in its prose**; the only wavelength in the text is the 635 nm
*fluorescence emission* maximum. Every number in that column is read off Fig. 3A by
`comparisons/fig3A_vs_spectracs/digitize_and_plot.py`, whose axis calibration is 300 nm → px 62,
700 nm → px 344 — **1.42 nm per pixel**, with only 8 px separating the two Soret peaks. Its own error is
±2–3 nm, larger than every discrepancy in the table.

⭐ **A second corpus corroborates the blue.** The capillary session `20260807A–D` reads 440–447 nm on
*starved* bins; the new lamp reads the same stretch with real light. The dilution-invariant ratio
`A(440–447) / A(448–460)` comes out **2.220–2.319** across four oils on the capillary runs and
**2.237 / 2.450** on the two new-lamp runs. They agree. ⛔ That kills `DOC_lamp_410_680.md` §8.2's
preferred reading — *"the rig's 440–447 bins are not real absorbance"* — and leaves the other one: the
forecast model's Soret is genuinely mis-placed and too broad.

### 2.2 ⛔ The camera's blue response was assumed, and the assumption was wrong

`led_lamp_410_680.instrumentResponse` says so itself: *"Below 440 nm nothing is measured at all — the blue
end is a stated assumption, not a result."* Applied to R2 at a 240 DN peak it predicts **13 DN**
(optimistic) or **3 DN** (pessimistic) at 410 nm.

⭐ **Run 002 measures 128 DN at 410 nm** — with fewer violet emitters than R2 carries. The modelled blue
roll-off is roughly an order of magnitude too pessimistic. Every blue-end number in that study understates
what the instrument delivers, and **no forecast in this document uses that model.**

### 2.3 ⚠ The arithmetic — a factor of 2.2, and it changes conclusions

Absorbance is defined on the **linear** values; the noise and the plots live in **display DN**; the two are
related by the `pow2.2` capture decode. So

> `S_dn = R_dn × 10^(−A / 2.2)` — **not** `R_dn × 10^(−A)`
>
> `σ_A = 0.434 × 2.2 × sqrt( (σ_dn/S_dn)² + (σ_dn/R_dn)² )`

Verified against run 002 at 421 nm: R = 131 DN, A = 1.210 → predicts S = **37.0 DN**; measured **37.0 DN**.
`lamp_rebuild_search.py --verify` re-runs that check.

⛔ **An earlier pass of this analysis used the wrong form**, which made every candidate's sample levels look
~2.2× darker than they are — worst where A is largest, i.e. the blue — and produced two claims that are
**withdrawn**: that R2 is 2–10× noisier than the current lamp below 500 nm, and that at the capillary dose
the 421 nm peak falls to 1.3 DN. R2 is *better* than the current lamp at 421, 432 and 625–640; the 421 peak
lands at **20.6 DN**, above the guard but with no margin.

---

## 3 · Method

### 3.1 The curve the lamp has to serve

![**Figure 2** — The anticipated absorbance, 404–680 nm, at the capillary dose. **Purple: measured on the new lamp** (`20260811A`, level-scaled onto the capillary dose by the 448–460 anchor) — the only data that exists below 440 nm. **Green: measured**, capillary corpus `20260807A`, mean of three reseats. **Grey: anticipated** — Fig. 3A's shape anchored on the capillary curve's own 629.8 value; nobody has captured this stretch, and it is the weakest input in the study. The spikes at 473 and 608 nm are the reduction's Bayer channel crossovers (§6), not features of the oil.](tmp/lamprebuild/anticipated_absorbance.png)

⭐ **And the same construction for all four oils of the capillary panel** — the successor to the old
study's Figure 5, with one difference that matters: over 440–630 nm this one is **measured**, not modelled
from five Gaussians.

![**Figure 3** — Green against brown across the whole range. Solid: the four capillary oils, each measured three times, extended below 448 nm by the shared blue template and above 630 nm by Fig. 3A's shape. Grey dashed: the old study's modelled green — peak 1.16 at 439 nm, and no doublet at all. The spikes at 473 and 608 nm are the channel crossovers of §6.](tmp/lamprebuild/green_vs_brown.png)

⚠ **Read the blue half of that figure carefully.** The four curves pair up by *level*, not by greenness —
Steirerkraft (M448 **9.96**) sits on top of Spar Premium (**7.69**), and Spar Steirisches (**8.76**) on top
of the brown S-Budget (**6.51**). That is because only one oil has ever been measured below 440 nm, so the
blue segment is one shape scaled per oil, and the pairing is dose. **The figure cannot show a green-brown
difference in the blue, and it should not be read as showing one** — that is the open question of §9.1.

### 3.2 What is scored, and why it is not what the old study scored

`DOC_lamp_410_680.md` scored **emitted SPD** through a modelled camera response, on a median across the
415–450 nm bracket plus a worst-band slope term. This study scores something narrower and much closer to
the result:

> ⭐ **The noise the metric would actually carry** — `σ_A` at the wavelengths that carry a number — computed
> from a **measured** absorbance curve and a **measured** noise level, with the lamp entering only through
> its emitted SPD normalised to a 240 DN peak.

Eight quantities. Band entries are the σ on the band *mean*, single wavelengths are the σ at that point,
and one entry is a **contrast**, because that is what the doublet actually costs to see:

| scored quantity | what it is | why |
|---|---|---|
| `soret-peak` | σ at 421.4 nm | the composite blue maximum |
| ⭐ `doublet` | σ on A(436.5) − A(432) | the doublet signature. That contrast is only **0.025–0.030**; nothing before scored it |
| `soret-band` | σ on the 448–460 mean | the shipped Soret window |
| `crossover` | σ at 476 nm | the Bayer B→G crossover — the largest artefact in the archive sits here |
| `clarity` | σ on 510–540 | clarity floor / near baseline anchor |
| `q-band` | σ on 560–580 | the metric's denominator |
| `far-anchor` | σ on 620–630 | far baseline anchor, and the 627 nm band |
| ⭐ `quiet` | σ on 660–680 | the pigment-free window — the anchor the metric has never had |

Ranking is **minimax**: the worst quantity decides, because a metric is only as good as its weakest input.

### 3.3 The one constant that carries everything

`σ_dn = 0.5 DN`, per curve. That is measured, not assumed. Run 002, high-frequency residual after a 9 nm
smooth, in display DN:

| band | reference level | reference noise | sample level | sample noise |
|---|---|---|---|---|
| 405–430 | 133 | **0.59** | 44 | **0.53** |
| 430–450 | 146 | 0.37 | 64 | 0.48 |
| 490–520 | 62 | 0.10 | 62 | 0.10 |
| 520–560 | 89 | 0.09 | 89 | 0.11 |
| 620–636 | 32 | 0.36 | 26 | 0.51 |

⭐ **The sample capture is not noisier than the reference** — same 0.1–0.6 DN wiggle in both, everywhere.
It only *looks* rougher because the oil absorbs 0.9–1.2 A in the blue, dropping that curve to a third of
the reference's height on a shared axis. Since `A = −log10(S/R)` responds to *relative* error, the sample
contributes **86 %** of the noise variance at 405–450 nm — not because anything is wrong with it, but
because it is the smaller of the two numbers.

⇒ **The noise floor of the measurement is set by the darkest thing in the sample capture, always**, and a
lamp can only ever raise the level that 0.5 DN sits on. That is the entire mechanism by which a flatter
lamp helps, and it bounds what one can be expected to fix.

---

## 4 · Results

### 4.1 The ranking

31 425 distinct seven-emitter allocations, from 5 white and 10 colour Avonec parts, ≤ 4 colour kinds.

![**Figure 4** — The top twelve of 31 425, by worst scored quantity. Part names abbreviated to their leading number. The published R2 board sits at **rank 206**; the 410–680 study's incumbent lamp at rank 8 329.](tmp/lamprebuild/ranking.png)

| rank | build | worst σ_A |
|---|---|---|
| **1** | 2 × `4000k-4500k` + 2 × `410nm-420nm` + 1 × `440nm-450nm` + 1 × `455nm-460nm` + 1 × `630nm-640nm` | **0.0209** |
| 2 | …same, `660nm` instead of `630nm-640nm` | 0.0209 |
| **6** | 2 × `4000k-4500k` + 2 × `410nm-420nm` + 1 × `440nm-450nm` + **1 × `480nm-485nm`** + 1 × `630nm-640nm` | 0.0215 |
| 206 | 3 × `4000k-4500k` + 2 × `410nm-420nm` + 1 × `430nm-435nm` + 1 × `660nm` — **R2 as published** | 0.0256 |
| 209 | R2 with `630nm-640nm` instead of `660nm` | 0.0257 |
| 8 329 | 3 × `6500k-7000k` + 2 × `430nm-435nm` + 1 × `515nm-525nm` + 1 × `660nm` — the old incumbent | 0.0620 |

⚠ **The top twelve are within 5 % of each other and should be read as a tie.** What separates them from R2
is not one part but a shape, and the shape is the finding:

> **two whites, not three · two violets · a 440–450 bridging part · one part in the 455–485 gap ·
> one red at 630–640.**

### 4.2 Where the difference comes from

![**Figure 5** — The objective itself, per scored quantity, log scale. The three boards agree closely on everything the current metric already reads — `clarity`, `q-band`, `soret-band`, `far-anchor` are all under 0.001 — and diverge on the three that the widened window opened: the Soret peak, the doublet contrast, and the crossover.](tmp/lamprebuild/objective_by_target.png)

| σ_A | soret-peak | **doublet** | soret-band | **crossover** | clarity | q-band | far-anchor | quiet | worst |
|---|---|---|---|---|---|---|---|---|---|
| rank 1 (`455nm-460`) | 0.0204 | **0.0209** | 0.0005 | 0.0133 | 0.0004 | 0.0004 | 0.0005 | 0.0011 | 0.0209 |
| rank 6 (`480nm-485`) | 0.0201 | 0.0215 | 0.0007 | **0.0059** | 0.0003 | 0.0004 | 0.0005 | 0.0011 | 0.0215 |
| R2 as published | 0.0229 | 0.0256 | 0.0010 | 0.0252 | 0.0003 | 0.0003 | 0.0006 | 0.0007 | 0.0256 |

⭐ **Two facts do the work.** The old metric's four bands are already easy — every board on this page reads
them at σ_A < 0.001, because they are wide bands in bright parts of the spectrum. **The board is decided
entirely by the three quantities the 400 nm clamp created**, and R2 is 1.2–4.3× worse on all three.

### 4.3 What each lamp puts on the sensor

![**Figure 6** — Delivered display DN with each lamp's own peak exposed to 240 of 255. Gold: the DIY lamp on the bench today, measured. Red dashed: R2 as published. Green: this study's board. R2's hole at 476 nm — 29 DN — is the study's own "deepest dip"; the shaded band is the 660–680 quiet window.](tmp/lamprebuild/delivered_dn.png)

| | 410 | 421 | 432 | 436.5 | 455 | **476** | 525 | 570 | 625 | 640 | 660 | flatness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bench lamp today (measured) | 128 | 131 | 169 | 148 | 190 | 174 | 70 | 92 | 37 | — | — | 10.1× |
| rank 1 | 136 | 234 | 197 | 209 | 238 | **55** | 143 | 178 | 172 | 200 | 78 | 5.1× |
| **rank 6 — recommended** | 139 | 237 | 194 | 202 | 149 | **123** | 146 | 181 | 175 | 203 | 79 | **4.6×** |
| R2 as published | 106 | 206 | 194 | 148 | 108 | **29** | 161 | 200 | 147 | 160 | 164 | 8.4× |

⭐ **The quiet window survives without a 660 nm part** — 78–79 DN, carried by the `4000k-4500k` phosphor
tail plus the `630nm-640nm` flank. The dedicated 660 part only sharpens it (σ 0.0011 → 0.0007) and costs
the far anchor (0.0005 → 0.0007). Since 620–630 is a shipped metric input and 660–680 is not, the trade
goes to `630nm-640nm`.

### 4.4 What the camera would see

![**Figure 7** — The successor to the old study's Figure 6. Reference and the two extreme oils under the recommended board, at the f = 1.75 dose of §9.2, on a log axis. Nothing approaches the 16 DN floor anywhere in 404–680 nm — the first time one dose has served both ends of the range.](tmp/lamprebuild/transmitted.png)

⭐ **Both oils clear the floor across the whole range at a single dose**, and the greenest and the brownest
are separated by a visible margin through 410–460 nm. ⚠ That separation is level, not shape — see the
caveat under Figure 3.

### 4.5 Robustness

The winner's rank under five re-weightings of the objective:

| weighting | winner's rank |
|---|---|
| as written | **1** |
| shipped metric ×2–3 | **1** |
| quiet window ×3 | **1** |
| drop the quiet window (control) | **1** |
| drop the crossover (control) | 2 |
| doublet ×3, Soret peak ×2 | 57 |

⚠ **The one weighting that moves it is worth reading, not explaining away.** Weighting the doublet three
times over picks `1 × 4000k-4500k + 2 × 410 + 1 × 430 + 2 × 440-450 + 1 × 455-460` — a board with **one
white**, which buys a marginally better doublet (0.0184 against 0.0209) and pays for it with flatness
**13.1×**, a far anchor 3.7× worse and a quiet window 2.8× worse. Equal weighting rejects it; a
doublet-obsessed weighting does not. **The lesson is that the doublet must not be optimised alone**, which
is exactly the risk this document runs after §2.1.

---

## 5 · The recommendation — and a deliberate departure from rank 1

⭐ **Build rank 6, not rank 1**, i.e. take `480nm-485nm` where the search puts `455nm-460nm`.

| | rank 1 | rank 6 |
|---|---|---|
| doublet | **0.0209** | 0.0215 *(2.6 % worse)* |
| crossover | 0.0133 | **0.0059** *(2.3× better)* |
| sum of all eight | 0.0575 | **0.0505** |
| flatness | 5.1× | **4.6×** |

Minimax ranks by the single worst quantity, and in both boards that is the doublet, where they differ by
2.6 %. On every other axis rank 6 is ahead, and it is **2.3× better at 476 nm** — the one wavelength where
the instrument has a known defect (§6). Rank 6 also has the flatter delivered spectrum, which is the thing
that buys exposure headroom.

⚠ **This disagrees with the old study on one part, and the reason is the objective, not the data.**
`DOC_lamp_410_680.md` §4.2 parked the cyan 480 as *"only at 8 slots — fills the 476 nm hole 3.6× but costs
half the Soret bracket at seven"*. A bracket median penalises it; a measured worst-band does not. ⛔
**Neither ranking is "the" answer — each is only as good as its objective.** This one has the advantage of
being anchored on data that did not exist when the other was written.

---

## 6 · ⚠ What no lamp fixes — and it is ten times larger than everything above

A(λ) shows level shifts at ~471, ~481, ~583 and ~614 nm, exactly where the reduction switches Bayer
channel. Per-channel absorbance at the same column, run 002:

| λ | R channel | G channel | B channel | stored |
|---|---|---|---|---|
| 480 | · | +0.162 | +0.217 | +0.203 |
| 485 | · | +0.056 | +0.209 | **+0.050** |
| 580 | +0.245 | +0.042 | · | **+0.035** |
| 585 | +0.182 | +0.020 | · | +0.171 |

⭐ **A spectrograph column carries one wavelength.** R, G and B at that column are three sensitivities
looking at the same light, so they must return the same `S/R`. They differ by **0.15–0.24 in A**, with
healthy DN in both channels. That is **ten times** the entire noise floor this document optimises, and the
board can do nothing about it — `480nm-485nm` only lifts the level, it does not remove the step.

**Ruled out:** a per-channel gain difference between the two captures. The `CAPTURE-SETTINGS` lines
(`CapturePanel.py:515`) are identical for `role=REFERENCE` and `role=SAMPLE`.

**Leading suspect:** stray light inside the spectrograph. The sample transmits 6 % at the Soret while the
reference is at full strength, so scattered blue is a far larger fraction of the sample's weak-channel
signal than of the reference's. ⇒ **Test:** recapture at A(Soret) ≈ 0.7. Steps shrink ⇒ glare, and the fix
is baffling and blackening. Steps hold ⇒ the reduction's channel handling.

⚠ **Fix this before the lamp.** It costs no hardware and it is the largest defect in the stored
spectra. §9.5 and Figure 8 are how.

---

## 7 · What must be re-derived after the swap

⚠ **Every one of these invalidates the thresholds, and the recalibration is the expensive part. Build it as
ONE rig change.**

| | what | why |
|---|---|---|
| 1 | the DN guard — 16 / 60 / 20–40 | already invalid: on the DIY lamp the sample sits at 57–199 DN across the Soret against a "60 DN = too dilute" edge |
| 2 | the Roast-Ampel thresholds | already invalid: run 002's gauges came back at 1.23 and 1.63 against bands of 4.8–9.6 and 6.0–12.0 — pegged off-scale |
| 3 | `B_Soret` = 0.6924 on 448–460 | the absolute level anchor; a lamp change moves it |
| 4 | the null series, floor 0.42 % | the instrument floor is lamp-dependent |
| 5 | frame rejection at the new exposure | two whites instead of three means less flux and a longer exposure |
| 6 | the dose | §9.2 |

⛔ **The colour chips are not comparable across this change.** `EvaluationColorUtil` integrates the whole
curve. The ratio metrics are.

---

## 8 · Corrections this implies to `DOC_lamp_410_680.md`

⛔ **Not applied there.** Listed so the disagreement is on the record rather than silently forked.

| § | what it says | what the measurement says |
|---|---|---|
| Figure 5 caption | the composite blue maximum sits *"near 440 nm"* | **421.4 nm**, and it is a doublet — 20 of 20 slit rows |
| §8.2 | the model/rig mismatch is *"consistent with a known instrument artefact"* | the 440–447 : 448–460 ratio agrees between starved and real-light measurements, so the bins were not the fault. The model's Soret is mis-placed |
| §8 model | `gaussian(432, FWHM 42)` + carotenoid `gaussian(455, FWHM 62)` | cannot produce a doublet at 421 / 436.5 with a dip at 432. `oil_forecast_410_680.py` lines 84–88 need refitting |
| `instrumentResponse` | the blue roll-off, *"a stated assumption, not a result"* | falsified: 13 DN predicted at 410 nm, **128 DN measured** |
| §7.1 | R2 is the build | superseded — rank 206 of 31 425 on a measured-noise objective |
| §4.2 | cyan 480 *"only at 8 slots"* | the recommended part on a seven-slot board here |

---

## 9 · What would change these conclusions

### 9.1 Does the blue end discriminate? — worth measuring, but it is **not** a purchase gate

There is **no evidence yet that the blue end separates oils.** §2.1 proves the doublet exists; nothing
proves it *moves*. The one blue-side quantity measured across four real oils — the 440–447 : 448–460 ratio
— spreads **4 %** against M448 gaps of 14–18 %. `DOC_lamp_410_680.md` §2.1 argues demetallation
blue-shifts the Soret: plausible chemistry, zero measurements.

> ⚠ **An earlier draft made this a gate on the order. That was wrong**, and Edwin said so: *"only because
> it might not deliver a better metric it does also not per hurts. and it would allow some other
> techniques to be applied and another metric might evolve."* He is right, and the numbers say how right.

⭐ **What the two violet slots cost.** Take the best seven-emitter board that contains **no**
`410nm-420nm` at all, optimised purely on the four bands today's metric reads, and compare:

| band | best board with no violet | the recommended board | difference |
|---|---|---|---|
| Soret 448–460 | 0.00051 | 0.00073 | **+0.00023** |
| clarity 510–540 | 0.00032 | 0.00034 | +0.00002 |
| Q 560–580 | 0.00033 | 0.00035 | +0.00002 |
| far anchor 620–630 | 0.00045 | 0.00051 | +0.00006 |

⭐ **0.00023 in absorbance, on the worst band.** For scale, the channel-crossover step of §6 is
**0.15–0.24** and run 002's measured far-anchor noise is **0.021**. The cost of carrying the violets is
two to three orders of magnitude below anything that matters — not merely small, but unmeasurable. And
they buy **13.3×** at the Soret peak (0.267 → 0.0201) and **2.7×** on the doublet contrast.

⇒ **The blue is cheap optionality, not a bet.** Even if it never yields a better *metric*, it makes the
band measurable at all, and it opens methods that cannot be attempted while the window starts at 440 nm —
a fitted band position, the demetallation shift, derivative or multivariate treatment of the doublet.
**Buy the violets regardless of how the experiment below comes out.**

⭐ **The experiment is still worth running, and it needs no purchase.** Figure 3 is the picture of the
gap: four measured oils, and below 448 nm they differ only by the level they were scaled to. Measure **Steirerkraft** and
**Spar S-Budget** — the greenest and the brown of the capillary panel, both on the shelf — on the current
lamp with the ROI at 400 nm. If the doublet separates them (P1/P2 ratio, dip position, or a shift in the
421 peak), there is a new metric to be had. If it does not, the board is unaffected and the question is
merely still open.

### 9.2 ⚠ The dose — and a correction

An earlier draft of this study said *"dilute to ≈ ×2.75 below the capillary dose"*. **That number was
picked to clear the DN floor, and clearing the floor is the wrong criterion**: diluting lifts the sample
level and shrinks the signal at the same rate, so `σ_A` alone always recommends more dilution and never
turns around. Scoring **signal-to-noise on the band depth** instead gives a real optimum.

`f` = how many times more dilute than the `20260807` capillary session (2 capillaries / 12 mL); absorbance
scales as `A/f`:

| f | SNR doublet | SNR Soret | SNR Q | recipe |
|---|---|---|---|---|
| 1.00 | 2.7 | 732 | 285 | 2 cap / 12 mL |
| 1.50 | **3.2** | 575 | 197 | 2 cap / 18 mL |
| **1.75** | **3.2** | 514 | 171 | **2 cap / 21 mL** |
| 2.00 | **3.2** | 464 | 151 | 2 cap / 24 mL |
| 2.75 | 2.8 | 357 | 111 | 2 cap / 33 mL |
| 4.00 | 2.3 | 257 | 77 | 2 cap / 48 mL |

Signal at the capillary dose: doublet contrast **0.0580**, Soret above clarity **0.5357**, Q above clarity
**0.1010**. Reproduced by `lamp_rebuild_search.py`, which prints this sweep.

⭐ **The optimum is f ≈ 1.5–2.0.** The doublet is the only quantity that wants *any* extra dilution; every
other band prefers less, so nothing argues for going past 2. ⭐ And `20260811A/002` already sat at
**f = 1.91** — on the optimum, by accident.

⚠ **One sober number falls out of this.** Even at the best dose the doublet **contrast** carries SNR ≈ 3.2
under this model, which reads the dip and the peak as single bins. Reading each over ±2 nm recovers about
5×, which matches the ~9σ measured on run 001. So the doublet is comfortably *visible* — its positions
reproduce to 0.2 nm across two runs and 20 slit rows — but its contrast as a **metric input** is a few-σ
quantity, not a strong one. Worth knowing before anything is built on it.

`SPEC_capture_quality.md` §16.23.6 concluded that on the old lamp *no* dilution satisfies both ends of the
spectrum. On this curve one does.

### 9.3 The Eu³⁺ test — decides `630nm-640nm` against `660nm`

`DOC_lamp_410_680.md` §6.2a is unresolved: runs `20260808A/B` show both old lamps collapsing to ~0.1 DN by
656 nm, and the chapter cannot say whether that is the lamps or the camera's IR-cut. `EUROPIUM_RED_FAR_680
/690/700` (687.7, 693.7, 707.0 nm) are strong in the calibration lamp. Open the ROI past 690 nm on a
**calibration-lamp** capture: lines visible ⇒ the camera passes 690 nm; lines absent ⇒ the IR-cut is the
gate and no red emitter reaches the quiet window at all.

### 9.4 The red end beyond 630 nm is anticipated, not measured

Everything in Figures 2 and 3 past 629.8 nm is Fig. 3A's shape scaled to a measured anchor. It is what makes the
`quiet` term scoreable, and it is the weakest input here. It also does not decide much: `quiet` is 0.0011
against a binding constraint of 0.0209, so even a large error there does not move the ranking.

### 9.5 The optical path — cheaper than the lamp, and probably worth more

⭐ **The diffuser splits the instrument into two zones that want opposite finishes**, and getting that
boundary wrong is a bigger error than any lamp choice on this page.

![**Figure 8** — Left: the stack, with the diffuser as the boundary between a white mixing chamber and a black optical path. Right: why a **cylinder** is the hard case. In a converging cone every wall bounce steepens the ray and stray light eventually walks out; in a parallel-walled tube a ray keeps its angle for ever and arrives at the slit indistinguishable from signal. A baffle is a washer — outer edge on the wall, hole just larger than the bundle, knife edge inward with the bevel toward the slit.](tmp/lamprebuild/baffles.png)

| zone | finish | why |
|---|---|---|
| board → diffuser | **matte white** | an integrating cavity; every bounce goes back into the mix and buys throughput |
| diffuser → sample → slit | ⭐ **matte black + baffles** | the optical path; every bounce here is stray light |

⛔ **A white or reflective tube wall would be actively harmful.** It converts the cylinder into a stray-light
injector — light of one wavelength landing where another belongs — and stray light is the leading suspect
for §6's 0.15–0.24 channel disagreement after the `CAPTURE-SETTINGS` check ruled out white balance. It is
also the most plausible explanation for the clarity floor collapsing from 0.105 to 0.008 between runs 001
and 002 while the Soret went *up*. The rig can afford the loss: it is dynamic-range limited, not light
limited.

⭐ **Position the baffles by sightline, not by calculation.** Put your eye at the slit and look down the
tube: **you must not be able to see any lit wall** — only the diffuser through the holes. Every visible
patch of wall is a one-bounce path into the spectrum. Two rings per cylinder is a reasonable start.

⚠ **Two ways to make it worse instead of better:**

| | |
|---|---|
| ⛔ **clipping the bundle** | the hole must clear the wanted beam at that station. Vignetting the spectrum costs more than the glare removed |
| ⛔ **a blunt or shiny rim** | at under ~0.1 mm, bevelled toward the slit. A square edge presents its own face to the beam and re-scatters forward, becoming the stray source it was installed to remove |

Black card cut with a compass cutter is adequate — the rings carry no load. Flock paper on the wall between
them beats paint, because at the grazing angles a cylinder is made of, even good matte black reflects a few
percent.

⭐ **Two cylinders is also a free diagnostic.** Blacken and baffle **one at a time** and re-measure: if the
481 / 583 nm steps shrink after the lower cylinder alone, the glare is on the illumination side; if only the
upper one moves them, it is between sample and slit.

**The diffuser itself.** The reference's normalised shape varies **15–30 % (blue) and 39–53 % (green/red)
along the slit**, and row-band mean absorbance runs 0.245 → 0.270 top to bottom. Removing the secondary
lenses already halved the flatness ratio (11.2× → 6.9×) and cut far-anchor noise 2.7×.

Geometry is not the constraint — for pitch 2.5 cm the residual ripple goes as `exp(−2πh/p)`, which is
3.5 × 10⁻⁶ by 5 cm and nil beyond. If emitters are still visible as discs, light is **bypassing** the
diffuser. ⚠ Nor does extra height cost light by itself: for an extended Lambertian source the throughput is
radiance × étendue, so a diffuser at 20 cm loses nothing **provided it still overfills the tube's
acceptance** — which means it must grow with the distance, roughly `aperture + 2·h·tan(acceptance)`. If it
does not grow, the loss goes as 1/h² and 11 → 20 cm costs 3.3×.

⭐ **Material: PTFE sheet, 0.5–1 mm** — near-Lambertian, spectrally flat 300–2500 nm, no fluorescence.
⛔ **Never paper, vellum, baking paper, Mylar or unspecified white plastic**: their **optical brighteners**
absorb 350–420 nm and re-emit at 420–470 nm, i.e. precisely on the doublet this whole board exists to
measure. Test any candidate in two minutes — capture the reference with and without it and divide; a
brightener shows as a dip at 380–420 plus a bump at 420–470 that no neutral scatterer produces.

---

## 10 · Reproducing this

```
source venv/bin/activate
PYTHONPATH=diagnostics python diagnostics/lamp_rebuild_search.py --verify --figures
python3 docs/tools/build_lamp_rebuild_pdf.py
```

The search writes `ranking.json` and the four figures to `spectracs-references/tmp/lamprebuild/`. Data
consumed, all carrying an embedded `workflow.json`:

| | |
|---|---|
| blue runs | `spectracs-references/tmp/20260811A/001.pdf`, `002.pdf` |
| capillary corpus | `spectracs-references/tmp/20260807{A,B,C,D}/00{1,2,3}.pdf` |
| literature Fig. 3A | `comparisons/fig3A_vs_spectracs/data/fig3a_literature_digitized.csv` |
| the oil panel | `business/internal/commmunication/Spectracs_Oil_Panel_2026-08-07.pdf` |
| Avonec SPDs | `spectracs-references/leds/avonec/`, digitised by `led_lamp_410_680.py` |
