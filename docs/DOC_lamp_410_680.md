# Choosing the lamp for 410–680 nm

**A spectral evaluation of Avonec 3 W LED combinations for pumpkin-seed-oil measurement, including the
deep-red star.**

*Internal working document · Spectracs · 7 August 2026*

> ## ⛔ SUPERSEDED 2026-08-12 by `DOC_lamp_rebuild.md` — do not order from this chapter
>
> The 2026-08-11 runs at ROI 400 nm (`20260811A/001,002`) measure 400–440 nm for the first time and
> overturn three inputs of this study: the oil's blue absorption is a **doublet at 421.4 / 436.5 nm**, not
> a single band near 439 (§8.2 and the Figure 5 caption); the camera's blue response is about **ten times**
> better than `instrumentResponse` assumes (13 DN predicted at 410 nm, **128 DN measured**); and §8.2's
> preferred explanation for the model/rig mismatch is refuted by the 440–447 : 448–460 ratio agreeing
> between starved and real-light measurements.
>
> ⭐ **§7.1's R2 board ranks 206 of 31 425** when the choice is re-scored on measured noise. The successor
> document lists every correction in its §8 and none of them have been applied here.
>
> ✔ **What still stands:** §3.1's digitised Avonec SPDs — `led_lamp_410_680.py` remains the digitiser and
> is imported by `lamp_rebuild_search.py`; §5's deep-red analysis; §6.2a's open IR-cut question; and §2.2's
> account of why the quiet window matters.

---

<!--TOC-->

<!--PAGEBREAK-->

## 1 · The question, and the short answer

Edwin asked for the Avonec LED combination that gives the best spectrum for the pumpkin-oil measurement
**across 410–680 nm**, taking into account a **3 W star-mounted 660 nm emitter**.

This document answers it by scoring **43 650 buildable seven-emitter allocations** against the pigment's
own absorption bands, computed from the **measured** spectra Avonec publishes for its own parts.

> ⭐ **680 nm is not an arbitrary top.** It is exactly where `KB_spectroscopy_physics.md` §7.2 puts the
> last measurable response — the Eu³⁺ 650.7 nm line resolves and response continues *"to ~680 nm"*. So
> the range asked for and the range the instrument can deliver are, for once, the same interval.

**Five findings. The first answers the star question; the fourth is a correction to this document itself.**

| | finding |
|---|---|
| **1** | ⭐⭐ **You do not need a second vendor. Avonec sells the 660 nm on a star board itself** — *3W High Power LED auf Starplatine 660nm tiefrot/hyper red*, **€2.75**, 2–4 working days, and its measured spectrum is already on file. A second vendor is needed **only** for 670/680 nm, which Avonec does not sell. |
| **2** | ⭐ **The backbone changes.** Over 410–680 nm the best white is **4000–4500 K**, not the 6500–7000 K the 430–670 study chose (50.12 against 55.71 alone). It is the only white with both a usable blue pump *and* a real red tail. |
| **3** | ⭐ **The 410 nm end is the bargain.** One **410–420 nm** emitter lifts 410 nm from **0.036 to 0.44** (12×) and the sub-Soret level **2.7×**. It is the largest single gain in the study. |
| **4** | ⛔ **An earlier version of this document claimed the camera ends the range past 640 nm. That claim is WITHDRAWN** (§6) — the ~40× fall it rested on was measured through a CFL, whose red output is Eu³⁺ *line* emission, so the ratio is the lamp's own structure. ⭐ Working assumption now: **the optics deliver to ~700 nm and the camera captures it**, so nothing inside 410–680 nm is known to be detector-limited. |
| **5** | ⭐ **The forecast says every region of 410–680 nm is usable** (§8). Modelled green and brown oils under the recommended lamp put nothing below the 1 % floor — and the quiet window 660–680 nm arrives essentially undiminished, because the oil is transparent there. |

⇒ **The recommendation:** build **R2** (§7.1) — all Avonec, all on Starplatine — and add a 670 nm star if
the quiet window is wanted now (§7.3). ⭐ **Neither half has to be taken on trust first:** §7.4 shows how
to price both — the red half free today on the existing lamp, the blue half with one emitter.

⭐ **And the concrete benefit, replacing §6's withdrawn one (§6.3):** the **619/624 nm red feature** is
real, moves between runs, and sits on the far anchor 620–630 where errors carry 17× leverage. It is
present on *both* bench lamps — the Sansi's 619 nm edge **amplifies it 4–6×, it does not cause it**. R2
reads 0.1–0.2 %/nm across that band. ⇒ **the recommended lamp removes the multiplier.**

> ⚠ **What this study is.** It ranks *candidate spectra*. It knows nothing about drive current, binning,
> thermal droop, diffuser transmission, or how emitters combine behind one diffuser — and real per-part
> output varies far more than normalised curves suggest. Treat every ranking here as a **shortlist for
> the bench**, not a result. §8's oil forecast is a *forward model* on top of that and carries its own,
> larger, uncertainty — §8.2 states the check it fails.

### 1.1 ⚠ Two corrections to the first draft of this study

Both were found by checking the shop rather than the archive, and both matter.

| | |
|---|---|
| ⭐⭐ **the 660 nm star is an Avonec part** | The first draft treated it as a second-vendor item with no measured spectrum, and modelled it. It is Avonec's own, so the **measured** `660nm.jpg` curve applies. §5.2's conclusion survives — but for a better reason than it had. |
| ⭐ **Avonec does sell a part inside the cyan gap** | The first draft said *"nothing between 460 and 515 nm"*. Wrong: there is a **480–485 nm türkis** (€2.75, on Starplatine) and a 490–495 nm cyan (sold out). Its Spektralmessung was harvested on 2026-08-07 and is now scored — see §4.2 finding 2. |

---

## 2 · Why 410 and why 680 — the two ends are not symmetric

The range was not chosen for roundness. Each end answers a different question about the pigment, and the
two questions have very different price tags.

### 2.1 The blue end: 410–430 nm makes the Soret a *band* instead of a flank

The oil's dominant absorption is the **Soret band of protochlorophyll at ~432 nm**
(`KB_spectroscopy_physics.md` §4.1). The shipped measurement window is **448–460 nm** — 16 to 28 nm above
the peak, i.e. **pure flank**. It sits there because that is where the instrument had light, not because
that is where the chemistry is.

⭐ **And the chemistry that matters is a *shift*, not only a depth.** Roasting and ageing strip the central
Mg²⁺ from protochlorophyll, giving **protopheophytin**. Demetallation lowers the macrocycle's symmetry, and
the textbook consequence is that **the Soret weakens *and* blue-shifts**. That is the green→brown axis at
the molecular level.

⛔ **A blue shift cannot be measured from one flank.** Seen only from 448–460 nm, a band that moves left
and a band that gets weaker look identical. To separate them you need light on **both sides** of 432 nm —
which is exactly what 410–430 nm buys.

⇒ The objective therefore scores not just the photon count at 432 nm but the **median level across
415–450 nm**, the *bracket*.

⚠ **One caveat on that bracket, found while checking the results.** 415–450 nm includes 450 nm, where
every phosphor white has its blue *pump peak* — so a lamp can score a good bracket on light that sits
entirely **above** the Soret and still be blind below it. The incumbent does exactly that (bracket 0.712,
propped by a pump peak of 1.000 at 450 nm, while reading **0.036 at 410 nm**). ⇒ **The honest
discriminator is the level strictly below the peak**, reported throughout as *sub-Soret* — the median
across **415–428 nm**. It is a reported diagnostic, not part of the objective, which stays frozen at the
bracket the ranking was computed on.

### 2.2 The red end: 660–680 nm is the first pigment-free window

Since the 2026-07-31 correction, the oil's red band is known to be the **Qy of protochlorophyll at
~623–626 nm**, not chlorophyll *a*'s 665 nm. That correction has a direct consequence for the range:

⭐ **Everything above ~660 nm is genuinely quiet.** There is no pigment feature there. That makes
660–680 nm the **baseline anchor the metric has never had** — the far anchor in use today (620–630 nm)
*contains the Qy band itself*, which is the whole reason `DOC_pedestal_correction.md` exists and why the
chord over-subtracts. A truly pigment-free anchor would make that correction unnecessary rather than
unproven.

⇒ So the red end is worth more than the blue end *scientifically*. §5 and §6 show it is also far more
expensive.

---

## 3 · Method

### 3.1 The source data — Avonec's own measured spectra

Avonec publishes a *Spektralmessung* for each 3 W part, but as a **JPG plot, not as numbers**. The set is
harvested to `spectracs-references/leds/avonec/`. This study digitises the plotted curve: the x axis is
calibrated on the plot's gridlines (with the image borders discarded, since the white margin also reads as
grey), and the y axis needs no calibration because every Avonec plot is normalised to 1.00 at its own peak.

⭐ **Thirteen curves are now calibrated, against seven in the 430–670 study.** That study excluded four
colour parts rather than guess their axes; those axes have now been read off the plots, the two remaining
whites with them, and the **480–485 nm** part was harvested for this study — it had been missed entirely.

**Every digitised peak is checked against the part number** (`--verify`):

| plot | digitised peak | part says | |
|---|---|---|---|
| `410nm-420nm` | 421.0 nm | 421 | ✓ |
| `430nm-435nm` | 430.0 nm | 432 | ✓ |
| `440nm-450nm` | 441.5 nm | 441 | ✓ |
| `455nm-460nm` | 457.5 nm | 458 | ✓ |
| `480nm-485nm` | 480.5 nm | 481 | ✓ *harvested 2026-08-07* |
| `515nm-525nm` | 514.5 nm | 520 | ✓ |
| `590nm-600nm` | 594.0 nm | 594 | ✓ |
| `600nm-610nm` | 615.0 nm | 615 | ✓ ⚠ *named 600–610, measures 615* |
| `630nm-640nm` | 635.5 nm | 635 | ✓ |
| `660nm` | 660.5 nm | 661 | ✓ |
| the five whites | — | bimodal, no single peak | — |

![**Figure 1** — Every Avonec 3 W spectrum used in this study, digitised from the shop's own Spektralmessung plots. Top: the ten colour parts, including the 480–485 nm türkis harvested for this study. Bottom: the five whites — each a narrow blue pump plus a broad phosphor hump, with the cyan dip near 480 nm common to all of them.](tmp/lamp410680/avonec_spd_atlas.png)

### 3.2 What is being scored

⛔ **Not flatness.** The measurement windows sit on flanks (§2.1), and a source's **peak must sit where you
measure, never its flank** — at a maximum, sensitivity to wavelength drift is second-order; on a flank it
is first-order. Measured three ways on the rig: an emitter *edge* inside an anchor costs 25 %/nm, an
emitter *centred* on it costs 0–5 %/nm.

The objective, in order:

| | criterion | why |
|---|---|---|
| 1 | photons at **432 / 574 / 625 nm** | the pigment's own band centres |
| 2 | median level across **415–450 nm** (Soret bracket) and **660–680 nm** (quiet window) | the two things the widened range exists to buy |
| 3 | the **log-slope** `abs(dlnI/dλ)` inside every measurement band, Q-band and far anchor weighted ×4 | §16.24.2's 17× error asymmetry — a steep emitter edge inside a band amplifies every R→S mismatch |
| 4 | no hole across 410–680 nm | the retired DIY array's 3× cliff at 500 nm is the failure mode to avoid |

### 3.3 The candidate set — integer emitters, not continuous weights

Candidates are **seven emitters allocated as whole parts**, matching the construction sketch: a white
phosphor lamp in the centre ringed by ~4 small heat-sinked emitters behind one common diffuser. At least
one white; at most three distinct add-on part numbers, so the board stays a board.

> ⚠ **One assumption is load-bearing and it is not exactly true.** One part is treated as weight 1.0 of
> its own normalised curve — i.e. every 3 W emitter is assumed to deliver the same radiant flux. It does
> not: green and cyan emitters sit in the semiconductor **"green gap"** and convert markedly worse than
> either the blue or the deep-red parts either side of them. ⚠ Avonec's datasheet PDFs are image-only, so
> per-part figures could not be read here. Counts are a **first-order allocation**, and any green or cyan
> slot should be read as *"at least this many"*.

### 3.4 The three families

| family | contents | count |
|---|---|---|
| **A · Avonec only** | the catalogue, orderable from one shop today — ⭐ **this now includes the 660 nm star** | 15 680 |
| **B · + modelled 660 star** | kept only as a **sensitivity check** on the measured 660 curve (§5.3) | 20 960 |
| **C · + longer deep-reds** | adds modelled 670 / 680 / 690 nm parts Avonec does not sell | 43 650 |

⚠ **The 670/680/690 parts are MODELLED** as skew-normal emitters (red-skewed, as real AlGaInP deep-reds
are). They have no published measurement on file.

<!--PAGEBREAK-->

## 4 · Results

### 4.1 The ranking, by family

Columns are the emitted level at each wavelength, relative to the combination's own peak. *worst* is the
steepest median log-slope over any measurement band, in %/nm. Lower score is better.

> **Notation.** `3×4000K · 2×410 · 1×430 · 1×455` means three 4000–4500 K whites, two 410–420 nm, one
> 430–435 nm and one 455–460 nm emitter. `star670` and up are the parts Avonec does not sell.

**A · Avonec only — everything here is orderable today**

| allocation, 7 emitters | I@432 | I@625 | I@660 | I@680 | worst | hole | score |
|---|---|---|---|---|---|---|---|
| 3×4000K · 2×410 · 1×430 · 1×455 | 0.831 | 0.598 | 0.353 | 0.176 | ⭐ 3.7 | 3.5 | **18.99** |
| 3×4000K · 2×410 · 1×440 · 1×**660** | 0.670 | 0.612 | 0.682 | 0.196 | 6.8 | 5.2 | 19.03 |
| ⭐ 3×4000K · 2×410 · 1×430 · 1×**660** | 0.810 | ⭐ 0.612 | ⭐ 0.682 | ⭐ 0.196 | 6.8 | 5.4 | 19.13 |
| 3×4000K · 2×410 · 1×440 · 1×455 | 0.691 | 0.598 | 0.353 | 0.176 | ⭐ 3.0 | 3.6 | 19.13 |
| 3×4000K · 2×410 · 1×430 · 1×440 | ⭐ 0.923 | 0.570 | 0.336 | 0.168 | 5.3 | 4.7 | 19.34 |
| 3×4000K · 2×410 · 1×430 · 1×**480** | 0.810 | 0.598 | 0.353 | 0.176 | 4.2 | ⭐ 3.4 | 19.46 |

⚠ **The top six span 18.99 to 19.46 — that is a tie, not a ranking.** What separates them is *which*
weakness you accept, not overall quality. The two without a deep red (rows 1 and 4) score marginally
better only because a 660 nm part raises the *worst* band slope to 6.8 %/nm; that steepness sits in the
**quiet window**, where nothing is measured today, not in a live band. ⇒ **Take the deep red.**

**C · + longer deep-reds — the only family that fills the quiet window**

| allocation, 7 emitters | I@432 | I@625 | I@660 | I@680 | worst | score |
|---|---|---|---|---|---|---|
| ⭐ 3×4000K · 2×410 · 1×440 · 1×**star670** | 0.670 | 0.598 | 0.541 | ⭐ 0.407 | 5.1 | **15.97** |
| 3×4000K · 2×410 · 1×430 · 1×**star670** | 0.810 | 0.598 | 0.541 | ⭐ 0.407 | 5.1 | 16.10 |
| 3×4000K · 1×410 · 1×430 · 2×**star670** | 0.670 | 0.598 | 0.729 | ⭐ 0.638 | 5.0 | 16.28 |

⭐ **670 nm, not 680 nm, is the right part for this range** — with the top at 680 nm a 670 emitter sits
*inside* the window with its flank covering 660–680, where a 680 emitter wastes half its output past the
edge. (In the earlier 689 nm version of this study, 680 won. The 9 nm change moved the answer.)

**For reference — the backbones alone, and the incumbent**

| allocation | I@432 | I@574 | I@625 | I@660 | I@680 | score |
|---|---|---|---|---|---|---|
| 7 × **4000–4500 K** | 0.231 | 0.893 | 0.598 | 0.353 | 0.176 | ⭐ **50.12** |
| 7 × 6500–7000 K | 0.288 | 0.831 | 0.412 | 0.197 | 0.088 | 55.71 |
| 7 × 5500–6000 K | 0.190 | 0.639 | 0.302 | 0.128 | 0.057 | 80.35 |
| 7 × 2900–3200 K | 0.094 | 0.845 | 0.507 | 0.226 | 0.099 | 143.22 |
| 7 × 10000–20000 K | ⛔ 0.099 | ⛔ 0.384 | ⛔ 0.162 | ⛔ 0.070 | ⛔ 0.031 | ⛔ 165.32 |
| **incumbent** — 3×6500K · 2×430 · 1×515 · 1×660 | 0.815 | 0.779 | 0.393 | 0.485 | ⛔ 0.099 | 26.44 |

⭐ **The incumbent ranks 1 897th of 43 650 on the widened objective** — not because it was wrong, it won
the range it was scored on, but because its two weak points are exactly the two ends this study adds:
**0.099 at 680 nm** and a **sub-Soret level of 0.322 against 0.87–0.89**.

### 4.2 Where the light actually lands

The most useful single table in this study: what each candidate puts on the grid, relative to its own
peak. **Every value below 0.10 is in the starved regime that produced the dead 440–447 bins.**

| | 410 | 432 | 450 | 480 | 500 | 520 | 540 | 574 | 625 | 660 | 680 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0** incumbent | ⛔ 0.036 | 0.815 | 1.000 | ⚠ 0.135 | 0.416 | 0.789 | 0.970 | 0.779 | 0.393 | 0.485 | ⛔ 0.099 |
| **R1** Avonec, no deep red | 0.443 | 0.831 | 0.748 | ⚠ 0.182 | 0.375 | 0.572 | 0.892 | 0.893 | 0.598 | 0.353 | ⚠ 0.176 |
| ⭐ **R2** Avonec 660 star | 0.442 | 0.810 | 0.561 | ⚠ 0.126 | 0.362 | 0.572 | 0.892 | 0.893 | 0.612 | ⭐ 0.682 | ⚠ 0.196 |
| **R3** R2 + the 480 filler | ⚠ 0.233 | 0.670 | 0.545 | ⭐ 0.456 | 0.475 | 0.575 | 0.892 | 0.893 | 0.612 | ⭐ 0.682 | ⚠ 0.196 |
| **R4** reach 680 (670 star) | 0.427 | 0.670 | 0.708 | ⚠ 0.133 | 0.362 | 0.572 | 0.892 | 0.893 | 0.598 | 0.541 | ⭐ 0.407 |

| | score | rank | **sub-Soret** 415–428 | quiet 660–680 | deepest dip | at |
|---|---|---|---|---|---|---|
| **R0** incumbent | 26.44 | 1897 | ⛔ 0.322 | ⛔ 0.221 | 0.066 | 410 nm |
| **R1** Avonec, no deep red | 18.99 | 106 | ⭐ 0.877 | 0.237 | 0.282 | 680 nm |
| ⭐ **R2** Avonec 660 star | 19.13 | 119 | ⭐ 0.874 | 0.352 | 0.184 | 476 nm |
| **R3** R2 + the 480 filler | 19.09 | 114 | ⚠ 0.544 | 0.352 | ⭐ 0.315 | 680 nm |
| **R4** reach 680 (670 star) | 15.97 | **1** | 0.737 | ⭐ 0.545 | 0.212 | 477 nm |

Three things fall out.

⭐ **1 · The 410 nm gain is the biggest single number in this study.** 0.036 → 0.44, a **12× lift**, and
sub-Soret **0.322 → 0.87**, a 2.7× lift. It is attributable to the violet part, not the backbone swap: a
bare 4000–4500 K board reads **0.007** at 410 nm; adding one 410–420 nm emitter takes it to **0.112** —
16× from a single part, and the score from 50.12 to 26.46. A 430–435 nm part in the same slot gives a
better I@432 (0.380 vs 0.301) but leaves 410 nm at **0.016**: it lights the peak without bracketing it.

⚠ **2 · The 480 nm hole CAN be filled — but not for free, and that corrects the first draft.** Avonec does
sell a **480–485 nm türkis** part (§1.1). Adding it lifts 480 nm from **0.126 to 0.456**, a 3.6× fill of
the deepest hole in the spectrum, and it moves the global minimum off 476 nm entirely. ⛔ **But on a
seven-slot board it costs a violet**, and the sub-Soret level collapses from **0.874 to 0.544**. The total
score barely moves (19.13 → 19.09), which is the honest reading: **it is a trade, not an upgrade.**

⇒ **Recommendation: skip it at seven slots, take it at eight.** The cyan region is not in any measurement
band today; the Soret bracket is the whole point of the blue end. ⚠ But it *is* inside the
carotenoid/lutein absorption (440–480 nm), so if a carotenoid feature is ever wanted, this part — not a
phosphor — is what makes it measurable.

⭐ **3 · The green LED disappears from every top allocation.** With a 4000–4500 K backbone the phosphor
already delivers 0.89 at 540 nm; a 515–525 nm part adds nothing the score can see. That reverses the
430–670 study's recommendation, and the backbone swap is the reason, not a change of mind about green.

![**Figure 2** — What the widened range buys, against the incumbent lamp. Grey dashed: the incumbent, blind below 425 nm and above 660 nm. **Solid green: R2, the recommended build** — a broad plateau across the whole Soret bracket and real output at 660 nm. Blue: R4, the 670 nm variant, the only one that fills the quiet window. Dotted gold: the 4000–4500 K backbone alone, showing how much of the middle comes free from the phosphor.](tmp/lamp410680/recommended_vs_backbone.png)

### 4.3 The ranking is not an artefact of the weighting

The objective is a judgement call, so it was stated five ways and the winner re-derived under each.

| weighting | winner | rank of "as written" |
|---|---|---|
| as written | 3×4000K · 2×410 · 1×440 · 1×star670 | **1** / 43 650 |
| photons first (band centres ×2) | 3×4000K · 2×410 · 1×430 · 1×star670 | **4** / 43 650 |
| smoothness first (steepness ×2.7) | *same as "as written"* | **1** / 43 650 |
| quiet window ×2.7 | 2×4000K · 2×410 · 1×440 · 2×star670 | 10 / 43 650 |
| **Soret peak only** *(bracket removed — the control)* | 3×4000K · 1×410 · 1×430 · 2×star670 | **4** / 43 650 |

⭐ **First under two weightings, 4th, 4th and 10th under the others.** And note what the control shows:
even when the bracket term is deleted — i.e. when the study is reduced back to the 430–670 question — the
**410–420 nm part still survives in the winner**. Its value is not an artefact of the criterion invented
to justify it.

⚠ **Two constants are robust across all five: the 4000–4500 K backbone and the 410–420 nm violet.**
Everything else — which blue, how many reds, which red — moves.

<!--PAGEBREAK-->

## 5 · The deep-red slot

### 5.1 Swapping only the red part

Six emitters held fixed, one red slot swapped:

| red part | I@625 | I@660 | I@680 | far-anchor slope | quiet-window median | source |
|---|---|---|---|---|---|---|
| 630–640 nm | ⭐ 0.734 | 0.359 | 0.176 | ⛔ 2.0 %/nm | 0.238 | measured (Avonec) |
| ⭐ **660 nm** | 0.612 | 0.682 | 0.196 | ⭐ 0.3 %/nm | 0.352 | ⭐ **measured (Avonec)** |
| star 660 nm | 0.598 | 0.686 | 0.253 | 0.2 %/nm | 0.468 | ⚠ modelled |
| ⭐ star 670 nm | 0.598 | 0.541 | ⭐ 0.407 | 0.2 %/nm | ⭐ 0.545 | ⚠ modelled |
| star 680 nm | 0.598 | 0.401 | ⭐ 0.510 | 0.2 %/nm | 0.443 | ⚠ modelled |
| star 690 nm | 0.598 | 0.359 | 0.390 | 0.2 %/nm | 0.311 | ⚠ modelled |

⛔ **The 630–640 nm part is disqualified, and by the rule the rig already measured.** Its **rising flank
sits inside the 620–630 nm anchor** — 2.0 %/nm against the 660's 0.3 — which is the Sansi's documented
failure mode, applied deliberately before building rather than discovered after. It buys the best I@625,
and pays in exactly the currency the far anchor cannot afford.

### 5.2 ⭐ The star is an Avonec part — the second vendor is not needed

The first draft of this study modelled the star as a second-vendor item. **Checking the shop settled it:
Avonec lists the 660 nm on a Starplatine themselves.**

| | |
|---|---|
| **bare emitter** | *3W High Power LED 660nm tiefrot / hyper red* — **€2.46** |
| ⭐ **on a star board** | *3W High Power LED auf Starplatine 660nm tiefrot / hyper red* — **€2.75** (€2.29 from 5, €2.15 from 10) |
| also | the same die on a *Grionec-Platine* (solderless, plug-together, removable) |
| stock | *ca. 2–4 Werktage* on all three |
| specs listed | 3 W, max 800 mA, 2.2–2.8 V, 120° beam, 30–50 lm |

⇒ **Two consequences, and both are good:**

⭐ **1 · The measured spectrum applies.** The star carries the same die as the bare part, so the digitised
`660nm.jpg` curve — verified to 0.5 nm against the part number — is the *right* input, not a Gaussian
stand-in. The whole "unmeasured second-vendor part" risk section of the first draft dissolves.

⭐ **2 · The star board is what the construction sketch needs.** A 20 mm metal-core PCB *is* the heat-sink
interface for *"a white lamp ringed by ~4 small heat-sinked emitters"*. And **410–420 nm (€3.55) and
430–435 nm (€2.86) are on Starplatine too** — so the entire recommended board is one order, one vendor,
one mounting standard.

⚠ **A second vendor becomes necessary only for 670 or 680 nm**, which Avonec does not sell in the 3 W
range — and §6 says do not buy those yet anyway.

### 5.3 How much an unmeasured deep-red bin could move things

Kept as a sensitivity check, since deep-red bins are specified loosely — a part sold as "660 nm" commonly
ships anywhere in 650–670 nm:

| assumed part | I@625 | I@660 | I@680 | far-anchor slope |
|---|---|---|---|---|
| 650 nm, FWHM 18 | 0.599 | 0.545 | 0.179 | 0.2 %/nm |
| 650 nm, FWHM 28 | 0.634 | 0.618 | 0.220 | ⚠ 1.0 %/nm |
| 655 nm, FWHM 22 | 0.600 | 0.657 | 0.210 | 0.2 %/nm |
| **660 nm, FWHM 22** *(nominal)* | 0.598 | **0.686** | 0.253 | 0.2 %/nm |
| 665 nm, FWHM 28 | 0.599 | 0.658 | ⭐ 0.377 | 0.2 %/nm |

⭐ **The far-anchor slope stays at 0.2 %/nm across the whole bin range**, except the widest 650 nm case
(1.0 %/nm), the only one whose flank creeps back into 620–630 nm. **Binning risk is low** — the 660 slot
is forgiving, and a 665 nm bin is quietly *better* for the quiet window.

### 5.4 ⛔ But no 660 nm part fills the quiet window

| | I@680 | quiet-window median 660–680 |
|---|---|---|
| Avonec 660 *(measured)* | 0.196 | 0.352 |
| star 670 | 0.407 | **0.545** |
| star 680 | **0.510** | 0.443 |

A 660 nm emitter is down to ~0.05 of its peak by 680 nm; most of the 0.196 above is the white phosphor's
tail, not the LED. **Covering 660–680 properly is a different part number, not a different weight** — and
the part is a **670 nm** 3 W star, which Avonec does not stock.

![**Figure 3** — The deep-red slot. The 630–640 nm part puts its rising flank inside the 620–630 nm far anchor, the failure mode the rig already measured on the Sansi. The Avonec 660 nm part is centred well but is fading by 675 nm. Only a ~670 nm part sits inside the 660–680 nm quiet window with its peak, which is what the "peak where you measure" rule demands.](tmp/lamp410680/deep_red_candidates.png)

<!--PAGEBREAK-->

## 6 · ⛔ WITHDRAWN — the claim that the camera ends the range

> ⛔⛔ **This chapter previously argued that response past 640 nm collapses, that the quiet window needs
> 10×–48× more emitted power than any board can supply, and that the whole thing is gated on the ELP's
> IR-cut filter. Edwin refuted it on 2026-08-07. The argument is withdrawn, and so are every number that
> depended on it.** What follows is the refutation and what is actually known.

### 6.1 Why it was wrong

The chapter rested on one figure: `KB_spectroscopy_physics.md` §7.2's *"the red channel falls ~40×
between 631 and 657 nm"*.

⛔ **That measurement was made through a CFL, and a CFL's red output is Eu³⁺ LINE emission, not a
continuum.** 631 nm sits on the red flank of the strong 626.6 nm line; 657 nm sits in the **gap** between
650.7 and 662. **A 40× ratio between those two wavelengths is what that lamp's own spectrum does.** No
instrument roll-off is needed to explain it — and §7.2 itself says the three causes cannot be separated.

⛔ **And the rebuttal this document offered was invalid.** It compared the 40× against the 631→657 fall of
**phosphor-white LEDs** (1.4–1.8×) and concluded the source could not account for it. That is the wrong
source class: a white LED has a smooth phosphor hump there, a CFL has lines and gaps. The comparison
proved nothing.

⭐ **The measured evidence points the other way.** Same camera, §16.25.4: the Sansi clips at 255 DN through
600–640 nm and **still reads 115 DN at 656 nm**. A 40× instrument roll-off between 631 and 657 is not
compatible with that — with a phosphor white's own gentle ~1.6× decline it would imply something like
7 000 DN at 631 nm, which is unreachable in 8 bits at a working exposure.

⇒ ⭐ **Working assumption, per Edwin: the optics deliver to ~700 nm and the camera captures it.** The
spectrometer's range is not known to be limited by the detector anywhere inside 410–680 nm.

### 6.2 What the camera has actually recorded

The honest replacement for a modelled response curve is the measurement itself — three lamps, as
recorded, lamp × instrument together.

![**Figure 4** — What the camera has actually recorded: three lamps in DN per bin (§16.25.4). The Sansi holds 149 DN at 630 and still returns 115 DN at 656 nm — the red end is not collapsed. ⚠ Two caveats are drawn on the plot: the Sansi clips at 255 through 600–640 nm in the screenshot set, so its mid-range there is a floor rather than a value; and the 680 nm column is dotted because `SPEC_metric_research.md` §9.1 P3 records that figure came from *"a screenshot ending at ~676 nm with a transferred wavelength scale"*.](tmp/lamp410680/measured_lamps.png)

⚠ **One oddity worth not explaining away:** the Sansi *rises* from 149 DN at 630 nm to 176 at 650. No
phosphor continuum does that. Either the two source tables are on different scales, or the Sansi uses a
**line-emitting red phosphor** (KSF/PFS, Mn⁴⁺, narrow lines near 631/648/660 nm), which would also explain
why it owns the deep red. Not decided here.

#### ⛔⛔ 6.2a A LATER MEASUREMENT CONTRADICTS THIS PANEL — unresolved  *(2026-08-09; `SPEC_capture_quality.md` §16.28.4)*

Two runs captured with the ROI opened to 690 nm — `20260808A` (**Sansi V2**) and `20260808B` (**Yuji**) —
record the red end collapsing on **both** lamps, on the same camera, the same evening:

| run | lamp | 630 | 640 | 650 | **656** | 660 |
|---|---|---|---|---|---|---|
| `20260808A` | Sansi V2 | 54.1 | 21.0 | 1.2 | **0.15** | 0.07 |
| `20260808B` | Yuji | 39.7 | 11.5 | 0.7 | **0.13** | 0.01 |

Against this chapter's *"still returns 115 DN at 656 nm"* that is a two-orders-of-magnitude disagreement in
**shape**, and both records cannot be right. ⚠ The **Yuji** rows are consistent between the two datasets (52
against 39.7 at 630 nm — the same ballpark at a different exposure). **The Sansi is where they diverge.**

⚠ **This does NOT restore the withdrawn §6 argument.** Three reconciliations remain open, and the 2026-08-09
session cannot choose between them:

1. **V1 ≠ V2.** §16.25.4's Sansi is the V1; this is the V2. §6.2's own KSF/PFS hypothesis would explain a V1
   that owns the deep red and a V2 that does not. ⚠ Though the new runs show **no line structure** at 648 or
   660 on either lamp — a smooth monotone decay, which is what a KSF lamp would *not* produce.
2. **The red end of Figure 4 is mis-scaled** — this chapter already flags that its 680 nm column came from *"a
   screenshot ending at ~676 nm with a transferred wavelength scale"*. That is exactly the failure mode that
   relabels a 630 nm value as "656 nm".
3. **Figure 4's mid-range is clipped** at 255 DN through 600–640 nm, so its red-end *shape* is not comparable
   with an unclipped run.

⭐⭐ **What decides it, with hardware already on the bench:** `EUROPIUM_RED_FAR_680/690/700` (687.7, 693.7,
707.0 nm) are the Eu³⁺ siblings of the 611.6 nm line the calibration already uses, and they are strong in the
calibration lamp — never markable before because the ROI ended blue of them. **Lines visible ⇒ the camera
passes 690 nm, §6's withdrawal stands, and the collapse belongs to the lamps. Lines absent ⇒ the IR-cut is the
gate and §6 must be re-opened.** Queued, not concluded.

#### ⭐⭐ 6.2b DECIDED 2026-09-04, by a halogen rather than by the europium lines — `KB_lamps.md`

A **60 W halogen** answers §6.2a's question without resolving any line, because a tungsten filament's SPD is
**analytic**: a Planck continuum that *rises* monotonically through 600–700 nm. Dividing a measured halogen
frame by Planck therefore leaves the instrument response by itself — the division §7.2 says no single lamp
permits, and the one thing a CFL's line spectrum could never support.

| finding | `KB_lamps.md` |
|---|---|
| the response carries a **dielectric edge at λ₅₀ = 641.8 nm**, 10→90 % over 16.5 nm — ~50× steeper per nm than anything else in it | §4.1 |
| ⇒ **the IR-cut is the gate.** At 650 nm ~82 %, at 660 nm ~87 % of the loss is that edge | §4.2 |
| the collapse is measured between **190 DN and 17 DN** — not a quantisation artefact | §4.3 |
| ⭐ **run `20260808B` (Yuji) is independently replicated** — same shape over 4000× of dynamic range | §5.3 |
| ⛔ **reconciliation 1 above is dead**: 115 DN at 656 nm would need the lamp to *emit* ~30× more at 656 than at 620 nm. Reconciliations 2 and 3 survive | §5.4 |

⇒ ⛔ **§6's withdrawal must be re-opened for everything past ~650 nm**, and §6.1's working assumption
(*"the optics deliver to ~700 nm and the camera captures it"*) is refuted there. ⭐ What survives intact is
§6.1's *criticism* — the CFL evidence really was worthless, for exactly the reason given. It is the
conclusion drawn from it that was too strong.
⛔ **And §5.4 / §7.3's deep-red reasoning loses its point**: 660–680 nm sits *behind* the edge, so no lamp
purchase reaches the quiet window. Marking the Eu³⁺ far lines remains a worthwhile independent check —
on these numbers they should be **invisible** — but it is no longer the blocker.
⚠ Rewriting §6 itself is left to Edwin; this is a pointer, not the rewrite.

### ⭐⭐ 6.3 The argument that replaces it — the 619/624 nm red feature

Withdrawing §6 does **not** leave the lamp choice unsupported at the red end. There is a real, measured
effect there, and it is a better argument than the one it replaces because it rests on rig data rather
than on a model.

`SPEC_capture_quality.md` §16.26.11 records it:

| | |
|---|---|
| what | a **sharp absorbance feature at 619/624 nm** that **moves between runs** |
| not noise | 200–600× the point-to-point standard deviation |
| ⭐ not present in nulls | invisible in every **same-liquid** null (615–622 nm reads +0.0011 ± 0.0009) — so it needs *something to change between `R` and `S`* |
| ⭐ **present on BOTH lamps** | archive **Yuji 0.008–0.013** against **Sansi 0.046–0.078** — 4–6× larger in *absolute* terms, so not merely the weaker fills |

⇒ ⭐ **The Sansi's 619 nm edge (−11 %/nm; §16.25.4 measures 25 %/nm at 622.0) AMPLIFIES the feature 4–6×.
It does not cause it.** The cause is still unidentified and requires something to change between the two
captures; the **refill null** (§16.26.11) is the pre-registered run that would find it, and it has not
been run.

⚠ **Correcting a premise while we are here: the archive lamp was the Yuji, never the Sansi.** §16.26.9
classifies the archive runs by blue/red ratio at ≈ 2.97 — the Yuji. The Sansi appears only as a candidate
in the 2026-08-06 null and probe runs. **No Sansi structure can have affected the measurements the metric
and its thresholds were built on.**

⚠ **And a second correction, from 2026-08-09: the 25 %/nm-at-622 disqualifier is V1-SPECIFIC.** Measured on
the **Sansi V2** (`20260808A`), the far anchor reads **1.47 %/nm median, 3.05 %/nm max** — Yuji-class — and the
V2's sharp feature has moved to **614.3 nm**, *outside* the anchor, structurally the same situation as the
Yuji's 610.9 nm line. ⇒ By this document's own rule — **it is LOCATION, not steepness** — the V2 passes the
test the V1 failed, and the recorded "do not adopt the Sansi" should be read as applying to the V1.

⚠ **The V2 was nonetheless NOT adopted** (`SPEC_capture_quality.md` §16.28.7). Measured against the Yuji on the
same rig it carries the white-LED valley between blue pump and phosphor — `I(470)/I(600)` = **0.35** against the
Yuji's **1.46** — and reproduces the V1's Soret steepness (7.48 %/nm across 440–460 against the Yuji's 2.27).
⭐ The decision rests mainly on **heat**: the V2 draws ~30 W against the Yuji's ~20 W, and §16.11.16 measured a
warmed fill reading as a *browner oil*, misclassifying 3 of 3 runs, with §16.11.17's decay-rate run queued next.

⭐⭐ **And this is the practical case for R2's flatness.** The feature lands squarely on the **far anchor
620–630**, the band carrying §16.24.2's **17× leverage**. R2 reads **0.1 %/nm at 625 and 0.2 %/nm across
620–630**, against the Sansi's 11–25 %/nm. ⇒ **the recommended lamp removes the multiplier.** It cannot
remove the disturbance — nothing about a lamp can, since it happens *between* the two captures — but 4–6×
off an error in the highest-leverage band is the single most concrete benefit in this document.

⚠ **Keep this separate from a different artefact in the same neighbourhood:** the archive is **convex at
626 nm on every fill**, the Qy maximum has never been observed, and a null-run control showed the
**instrument's own curvature** would fake one (`SPEC_metric_research.md` §9.1 item 5). Same region, not
the same effect, and it is not attributed to lamp line structure.

### 6.4 What survives, and the one test still worth running

| | |
|---|---|
| ⛔ **withdrawn** | "past 640 nm the camera is the limit"; the 10×–48× parity figures; the delivered-score ranking; the advice to hold the deep-red purchase |
| ✔ **untouched** | §4 and §5 — the emitted-spectrum ranking and the R2 build. Neither ever used the response model |
| ⭐ **still worth doing** | the one-evening test below, now as a *characterisation* rather than a gate |

⭐ **The test, and it needs no datasheet, no absolute calibration and no known flux:**

> **Shine the Avonec 660 nm LED alone into the slit and capture it.** What the instrument records is
> `SPD(λ) × response(λ)`. The `SPD(λ)` is known — the digitised `660nm.jpg` curve of §3.1, verified
> against the part number to 0.5 nm. **Divide the captured spectrum by it, and the quotient is the
> instrument's response across ~640–690 nm**, up to one unknown constant, which cancels because only the
> shape is in question.
>
> ⭐ **Chain it with the 630–640 nm part.** That curve spans ~605–665 nm, so the two overlap across
> ~645–665 nm; matching them there stitches one response curve from **605 to 690 nm** with no absolute
> measurement anywhere — and the same capture independently validates the digitised SPDs.

⇒ It is no longer a purchase gate. It is the measurement that would have prevented this chapter's error,
and both parts are on the R2 order anyway.

## ⭐⭐ 6a · TWO OF THIS DOCUMENT'S FINDINGS NOW CARRY MORE WEIGHT THAN WHEN WRITTEN  *(2026-08-25)*

The verdict metric is now **`Rv` = 100·(A[622–627] − A_valley)/(A[565–580] − A_valley)**
(`SPEC_red_ratio_metric.md`). Two things already argued here turn out to bear directly on it.

### ⭐⭐ 6a.1 Figure 5's carotenoid note is now evidence AGAINST the metric it was written under

Figure 5 says of the blue end:

> the carotenoid absorption at ~455 nm rides on top of the Soret, so the peak you can see is not the peak
> the chemistry is at

⭐ **That is the physical case against `Q%`'s denominator.** `Q%` divides a porphyrin Q band by the
448–460 nm window — a window this document shows is **contaminated by a pigment family that has no Q
bands at all**. Two unrelated chromophore systems in one ratio.

`Rv` divides one Q band by another. Numerator and denominator come from the **same** electronic system, so
Gouterman's four-orbital account applies to both terms — and demetallation (D₄ₕ → D₂ₕ) making band I the
weakest of four *is* what `Rv` measures. That is the likely reason `Rv` absorbs a 40–45 % dose swing and
three solvents where `Q%` moves 6.5 units on one oil.

### ⛔ 6a.2 §7.3's peak-POSITION hope does NOT apply to the red band — it lives in the Soret

This document argues that **position metrics are the ideal** — dilution-invariant by construction, since
Beer–Lambert scales amplitude and does not move a maximum — and that the demetallation shift is a position
*"unreachable from one flank"*.

⭐ **The far flank is now reachable**: in an index-matched solvent the 624 nm band is a whole peak, maximum
at 623–625 nm falling 81–99 % by 633 nm (`SPEC_red_ratio_metric.md` §6.6). So the objection is answered.

⛔ **But the red band's position is not a discriminator.** Measured over the index-matched runs it spans
**623.0–624.8 nm with green and brown interleaved**; second-derivative dip positions agree
(623.8 ± 0.6 nm in sunflower). **The demetallation blue shift this document wants is in the SORET**, and
it remains unreachable for the reason §7.2 gives — the incumbent cannot see the Soret's short-wavelength
side.

⇒ ⭐ **This does not weaken the case for the wider range; it redirects it.** The red extension is still
wanted — the 660–680 nm quiet window is a true pigment-free anchor, which nothing inside 440–630 is (the
quietest points measured are 540.5 and 558.0 nm, and both sit *inside* `Rv`'s own valley window). But it
should be justified as **an anchor**, not as a route to a red peak position.

## 7 · Recommendation

### 7.1 ⭐⭐ The board to build — R2, and every part is Avonec

**3 × Avonec 4000–4500 K + 2 × Avonec 410–420 nm + 1 × Avonec 430–435 nm + 1 × Avonec 660 nm** —
all four part numbers available *auf Starplatine*, one order, one vendor, ~€20 in emitters.

Its spectrum is the **solid green curve in Figure 2**.

| slot | part | why |
|---|---|---|
| **backbone** | 3 × **4000–4500 K** | ⭐ **not** 6500 K — beats every other white on this range (50.12 vs 55.71) and has the best red tail of the five |
| **violet** | 2 × **410–420 nm** | the Soret bracket, and the biggest single gain in the study |
| **blue** | 1 × **430–435 nm** | sits nearly **on** the Soret peak — I@432 **0.810** against 0.670 for the 440–450 nm part |
| **deep red** | 1 × **660 nm** | ⭐ the **measured** Avonec part; far-anchor slope 0.3 %/nm, and it triples I@660 (0.353 → 0.682) |
| **green** | ⛔ **none** | the 4000 K phosphor already gives 0.89 at 540 nm. This reverses the 430–670 study |
| **cyan 480** | ⏸ **only at 8 slots** | fills the 476 nm hole 3.6× but costs half the Soret bracket at seven (§4.2) |

### 7.2 If only one part is bought

⭐⭐ **1 × Avonec 3 W 410–420 nm**, on the existing lamp, behind the existing diffuser. On a bare
4000–4500 K board it lifts 410 nm **16×** and the sub-Soret level **3.3×**, taking the score from 50.12 to
26.46 — the largest single gain here, it survives all five weightings including the control that deletes
the criterion it was scored on, and it needs no new board.

⚠ Its benefit is **invisible until the capture clamp moves below 440 nm** — but that clamp is a software
choice, not a hardware one.

⚠ **And "one part" understates the work.** §7.1 requires every emitter behind the **same diffuser with
working distance**, or the Yuji's 1.8 % along-slit uniformity is traded away — a bare point emitter beside
a diffuse *panel* lamp **selects** emitters rather than mixing them. Getting those two behind one common
diffuser is arguably **harder** than the co-planar seven-emitter board, where the geometry solves itself.
⇒ read it as *one part plus a mixing problem the full build does not have*. §7.4 offers a way round it.

### 7.3 The 670 nm reach — re-priced

> ⚠ **This section previously said "do not buy the 670 nm reach yet", on §6's now-withdrawn argument.**
> With that argument gone, so is the reason to wait.

⭐ **On the evidence available, a 670 nm 3 W star is straightforwardly worth having.** The quiet window
660–680 nm is the only pigment-free region in the whole range (§2.2), it is the baseline anchor the metric
has never had, and §8's forecast puts the oil's absorbance there at **A ≈ 0.008** — the light that arrives
is the lamp, undiminished.

⚠ **The two costs that remain are real but small:**

| | |
|---|---|
| ⚠ **a second vendor** | Avonec sells no 670 nm in 3 W. It is the only part on the board that needs one |
| ⚠ **it is modelled** | no measured SPD; §5.3 shows the slot is forgiving, but the curve is a skew-normal, not a measurement |

⇒ **Sequence:**

| | step | cost |
|---|---|---|
| **1** | ⭐ Order **R2** — all Avonec, all on Starplatine | ~€20 in emitters |
| **2** | ⭐ Add a **670 nm star** from a second vendor if the quiet window is wanted now, or defer it as the one part that needs a second source | ~€3–5 |
| **3** | ⭐ Run the **660 nm response test** (§6.4) with a part from that same order — now a characterisation, not a gate | one evening |
| **4** | Move the capture clamp **below 440 nm and above 630 nm** and confirm both new ends | free — software |

⚠ **And whatever is built, build it as one rig change.** Every one of these moves invalidates the
thresholds, and the recalibration is the expensive part — bundling them means paying for it once.

### ⭐ 7.4 De-risk both halves before building anything

Neither half of the case has to be taken on trust. Both can be tested before a board exists.

**(a) ⭐ The red half is free today — no hardware at all.** Move the capture clamp past 630 nm on the
**existing Sansi**, which already reads 149 DN at 630 and 115 at 656 (§6.2), and look: does 660–680 nm
behave as a flat, pigment-free anchor, and does `far/near < 1` appear? That is a calibration and a
software clamp, and it tests the single most valuable claim in this study — §2.2's quiet window — before
anything is ordered.

**(b) The blue half needs one emitter, but not bolted beside the Yuji.** §7.2's caveat applies: a point
source next to a diffuse panel is a mixing problem. ⭐ **Cleaner: capture with the violet ALONE.**

> `T = S/R` only needs the lamp to have light **where you are measuring**, and both captures use the same
> lamp. So a violet-only source across ~405–450 nm yields a valid transmission curve over the whole Soret,
> and answers the one question the blue end exists for: **does the band's position move between a green
> and a brown oil?**
>
> ✔ No integration with the Yuji, no common diffuser, no uniformity regression — a lamp swap for one probe
> capture. ⛔ **It cannot produce `M`**: the baseline chord spans 510–540 and 620–630 and a violet-only
> lamp has neither. It is a **shape probe, not a verdict**. ⚠ Still needs the calibration extended below
> 440 nm, and its own exposure handling.

⇒ **Together these price both halves of the thesis for one calibration session and one emitter.**

---

<!--PAGEBREAK-->

## 8 · ⭐ What it would boil down to — a green-vs-brown forecast

*(Edwin 2026-08-07: "simulate an expected absorption curve based on typical green and brown oils … just
an anticipated estimate telling us what it all would boil down to".)*

> ⚠⚠ **A FORECAST, NOT A MEASUREMENT.** No oil was measured for this. It is a forward model of
> `A_oil(λ)` from the pigment physics of `KB_spectroscopy_physics.md` §4.1/§4.1a, with two free
> parameters tuned to values the rig actually reports. It can say **where the light goes and which
> regions are usable**. It cannot confirm any band ratio, because the ratios were put in by hand.

### 8.1 What it is anchored to

| anchor | value | source |
|---|---|---|
| band centres | 432 / ~574 / ~625 nm | protochlorophyll, KB §4.1a |
| the shipped windows | Soret 440–460, near 510–540, Q 560–580, far 620–630 | `DevSpectralPlugin.py` |
| ⭐ the class values | `M baseline` green **15.559**, brown **10.160**, threshold 10.35 | `SPEC_roast_ampel.md` §2b, 37 runs |
| ⭐ the absolute level | `B_Soret` (440–460) = **1.0272** | `SPEC_metric_research.md` §7.2 |
| the green→brown direction | Qy −17 %, 572 nm +14 %, per unit Soret | §16.11.16, one demetallated fill |

⚠ **Both anchors are needed, and the second is easy to miss:** `M` is a *ratio* of two baselined band
means, so it is **invariant under an overall scaling of `A`**. Fitting `M` alone leaves the absorbance
*level* free — exactly the quantity every photometric question here depends on. `B_Soret` pins it.

### 8.2 ⚠ The one falsifiable check — and it fails

Both free parameters went on `M` and on the 440–460 band level, so the **448–460** window was not fitted.
Its ratio to 440–460 is therefore a genuine prediction of the Soret slope's shape:

| | |
|---|---|
| model | 0.942 |
| rig | **0.674** (`B_Soret` 0.6924 / 1.0272) |
| | ⚠ **40 % apart** |

Trimming 440–447 off costs the rig **33 %** of its Soret band and costs the model **6 %**. So the real
curve rises far more steeply below 448 nm than a Soret centred at 432 with a 42 nm width can. Two
readings:

**(a)** the model's Soret is too broad or mis-placed — in which case the blue-end story needs re-checking,
since it rests on that slope;

**(b)** ⭐ **the rig's 440–447 bins are not real absorbance.** §7.13 documents exactly this: they are
starved bins, and `A = −log₁₀(S/R)` blows up as `S` approaches the floor, which *inflates* the 440–460
mean. `SPEC_metric_research.md` §7.2 calls the trim *"drops the non-measurements"* — the same claim from
the metric's side.

⇒ **(b) is independently documented and predicts the sign and rough size of what is seen**, so the failure
is *consistent with* a known instrument artefact rather than evidence against the pigment model. ⛔ **But
it is not proof, and it leaves the model's Soret slope unvalidated.** Every blue-end number below is
indicative.

![**Figure 5** — Forecast absorbance of a typical green and a typical brown oil. ⚠ Modelled, not measured. The brown curve is blue-shifted (demetallation), raised in the Q band and lowered at Qy — the directions the rig measured on an aged fill. Note the composite blue maximum sits near **440 nm, not at the Soret's 432 nm centre**: the carotenoid absorption at ~455 nm rides on top of the Soret, so the peak you can see is not the peak the chemistry is at.](tmp/lamp410680/oil_forecast_absorbance.png)

### 8.3 What the camera would see

Transmitted signal `S = R · 10^(−A)`, relative to the lamp's own peak. **Below 1 % is the starved regime
that made 440–447 dead bins.**

| | R2 lamp | S green | S brown | incumbent | S green (incumbent) |
|---|---|---|---|---|---|
| 410 nm | 0.442 | ⭐ 0.126 | 0.080 | ⛔ 0.036 | ⚠ 0.010 |
| **432 nm — Soret peak** | 0.810 | 0.062 | 0.066 | 0.815 | 0.063 |
| 450 nm | 0.561 | 0.049 | 0.053 | 1.000 | 0.087 |
| 520 nm | 0.572 | 0.486 | 0.416 | 0.789 | 0.670 |
| **574 nm — Q** | 0.893 | 0.585 | 0.509 | 0.779 | 0.511 |
| **625 nm — Qy** | 0.613 | 0.453 | 0.451 | 0.393 | 0.291 |
| 660 nm | 0.682 | ⭐ 0.667 | 0.644 | 0.485 | 0.475 |
| 680 nm | 0.196 | 0.193 | 0.187 | ⚠ 0.099 | 0.098 |

![**Figure 6** — What the camera would see. Green and brown under the recommended R2 lamp, against green under the incumbent. The five measurement windows are shaded. Nothing falls below the 1 % floor anywhere in 410–680 nm under R2 — which is the headline of this chapter.](tmp/lamp410680/oil_forecast_transmitted.png)

### 8.4 ⭐ What it boils down to

**1 · The quiet window is the clean win.** `A(660–680)` = 0.008 green / 0.022 brown — effectively
transparent, so what arrives there *is* the lamp. R2 delivers 0.682 at 660 nm against the incumbent's
0.485, and **0.196 vs 0.099 at 680 nm (2.0×)**. ⇒ a baseline anchor with no pigment in it, which 620–630
is not and never was.

**2 · ⭐ The blue gain is BELOW the peak, not at it — and that is the point.** At 432 nm the two lamps are
level (0.810 vs 0.815): the incumbent already carries two 430–435 emitters. The difference is underneath:

| | R2 lamp | incumbent | gain | S green (R2) | S green (incumbent) |
|---|---|---|---|---|---|
| 410 nm | 0.442 | 0.036 | ⭐ **12.4×** | 0.126 | ⚠ 0.010 — *at the floor* |
| 415 nm | 0.628 | 0.090 | 7.0× | 0.129 | 0.019 |
| 420 nm | 0.823 | 0.241 | 3.4× | 0.119 | 0.035 |
| 425 nm | 0.963 | 0.571 | 1.7× | 0.102 | 0.060 |
| 430 nm | 0.899 | 0.835 | 1.1× | 0.074 | 0.069 |

⇒ ⭐ **The incumbent cannot see the Soret's short-wavelength side, so it cannot see the demetallation blue
shift. R2 can.** That is the entire case for 410–420 nm, and it is a *shape* argument, not a photon-count
one.

**3 · ⚠ The blue is expensive in signal either way.** `A(432) = 1.11`, so the oil transmits **7.7 %** there
at the working recipe. Under R2 that is 0.062 of the lamp peak — above the floor, but not comfortably.
Halving the concentration would gain **3.6×**. ⇒ **the lamp and the capillary protocol are one change, not
two.**

**4 · ⭐ The three peaks do sit on a smooth lamp** — which is what you expected. `|dlnI/dλ|` of R2:

| | | |
|---|---|---|
| **432 nm** Soret | 6.0 %/nm | on the 430–435 emitter's own peak |
| **574 nm** Q | 2.0 %/nm | on the 4000 K phosphor's smooth hump |
| **625 nm** Qy | ⭐ 0.1 %/nm | flat — the 660 part's rise starts later |

For scale: an emitter **edge** inside a band costs 25 %/nm (the Sansi's measured failure, §16.25.4); a
source **centred** on a band costs 0–5 %/nm. All three land in the good regime, and the Qy anchor — the
one §16.24.2 says carries 17× the leverage — is the flattest of the three.

**5 · ⚠ A prediction that can be falsified.** The S1 window trim 440–460 → 448–460 should move `M` from
15.56/10.16 to **14.66/9.72**, class gap 53 % → 51 %. ⚠ Believe the direction, not the number — the brown
oil's chemistry is modelled from **one** measured fill (§16.11.16), which is the thinnest input here.

### ⭐⭐ 8.5 What the complete bands open *(Edwin 2026-08-07)*

`SPEC_metric_research.md` §9.1 closed **seven** analysis routes in a single session, *"every one of them
on the same wall: both principal bands are flanks and the range is clipped at both ends."* R2 plus the
clamp move is what removes that wall:

| band | today | with R2 + the clamp |
|---|---|---|
| **Soret 432** | right flank only (448–460); no light below 430 | ⭐ a **complete band** — 0.44 at 410, 0.81 at 432, both flanks visible |
| **Q 574** | already contained | unchanged, better lit (0.89) |
| **Qy 625** | at the clamp edge, used as a *baseline anchor* | ⭐ a **complete band**, with a pigment-free region beyond it |

⚠ **One asterisk on "complete":** the carotenoid at ~455 nm rides on top of the Soret, so even with full
coverage the observed blue maximum is a **composite** — §8.2's model puts it near 440, not 432.
Separating them needs decomposition, which is the first technique the full band enables. *The band you can
only get by covering it fully is also the band you then need to deconvolve.*

**What becomes possible:**

| | technique | why it needs the full band |
|---|---|---|
| **1** | ⭐⭐ **peak-POSITION metrics** | a position is **dilution-invariant by construction** — Beer–Lambert scales amplitude, it does not move a maximum. That is the target property the metric research states and **no ratio has**. The demetallation blue shift is a position, and it is unreachable from one flank |
| **2** | **band decomposition (C7)** | fitting Gaussian/Voigt shapes needs the whole band; returns **position, width and area separately** — three numbers where today there is one. §9.1 called it *"justified only if R2/R3 leave the truncated peaks as the limiting factor"*. They did |
| **3** | **derivative spectroscopy (C20)** | 2nd derivatives resolve overlapping bands and are baseline-free. §9.1 ranked it last because *"its weakest term is at the range edge"* — move the edge and that objection dies |
| **4** | **a real baseline** | anchoring on the pigment-free 660–680 window instead of a chord through 620–630, which *contains the Qy band*. Would make `r_Q`, the pedestal correction and assumption A1 **unnecessary** rather than unproven |
| **5** | **moments (C19), three-band (C18)**, and the **scatter-correction family** (§9.1 P3, via `far/near < 1`) | all need the region beyond the bands |

⛔ **The gate that comes with it, and it is unclosed.** Position metrics inherit
`SPEC_metric_research.md` **R1b**: *is λ stable to ≪ 0.9 nm across sessions?* Never verified. A blue shift
of a few nm measured against a calibration that may wander by 0.9 nm is not a measurement. ⭐ Cheap to
close — the CFL gives **Hg 404.66 / 435.83 / 546.07 / 576.96 / 579.07 plus Eu³⁺ 611.6 / 626.6 / 650.7** in
a single capture, an eight-point check across the whole working range. Worth doing in the same evening as
§6.4's response test.

⚠ **And the honest caveat on the whole chapter: the lamp is not today's bottleneck.** The null series put
the instrument at **0.42 %** and reseating at **~1.4 %** against a 3–5 % archive CV; §16.26.10 concluded
the residual **~3.8 % is the preparation**. A better lamp does not touch that term. ⇒ This is **access to
a class of measurement that is currently impossible**, not a reduction of today's noise — better *in
kind*, and untested.

---

## 9 · What would change these conclusions

| # | if this turned out otherwise | what changes |
|---|---|---|
| 1 | ⛔ **the instrument response past 640 nm** — the claim that it collapses is **WITHDRAWN** (§6.1); the 40× was the CFL's own line structure | already applied: §7.3 re-priced, §6's parity figures deleted. §6.4's test remains worth running, now as characterisation |
| 1b | ⚠ **the model's Soret slope** — §8.2's shape check fails by 40 %, explained by a documented artefact but not proved | §8's blue-end numbers, which are indicative only. The *ranking* in §4 does not use the oil model at all |
| 2 | ⭐ **per-part radiant flux** — assumed equal across 3 W parts | the *counts*, not the *parts*. The 4000 K backbone and the 410–420 violet survive any plausible reweighting |
| 3 | **the 660 nm bin** — assumed nominal | little; §5.3 shows the slot is forgiving across 650–670 nm, with only a wide 650 nm bin creeping into the far anchor |
| 4 | **diffuser transmission** (40–80 %) and along-slit uniformity | not modelled at all. Every emitter must sit behind the same diffuser with working distance, or the 1.8 % uniformity bar is traded away |
| 5 | **the digitised curves** | verified peak-by-peak against the part numbers (§3.1) to 1–6 nm |
| 6 | ⚠ **the catalogue** | this study was wrong once already about what Avonec sells (§1.1). The 480–485 nm part was missed; **the harvested SPD set should be re-checked against the live shop** before the order goes out |

⚠ **The one thing this study cannot do is see the benefit it recommends.** With the capture clamp at
440–630 nm, both new ends are outside the measurement. The lamp change and the clamp change are one
project, not two.

---

## 10 · Reproducing this

```
cd spectracsPy
./venv/bin/python diagnostics/led_lamp_410_680.py --verify --figures
PYTHONPATH=diagnostics ./venv/bin/python diagnostics/oil_forecast_410_680.py --figures
```

`--verify` re-derives every digitised peak and checks it against the part number; `--figures` writes
Figures 1–4 to `spectracs-references/tmp/lamp410680/`, and the forecast script writes Figures 5–6 to the
same place. The full ranking goes to `ranking.json`.

**Related:** `SPEC_capture_quality.md` §16.25.4 (the lamp brief), §16.25.4a (the 430–670 nm study this
widens), §16.25.4b (this study's summary) · `KB_spectroscopy_physics.md` §4.1 (the pigment correction),
§4.1a (the three band centres), §7.2 (the delivered range) · `KB_led_and_oil_spectra.md` (the Avonec
catalogue and the harvest method) · `SPEC_metric_research.md` §9.1 item 5 (extend the red, light the
blue) · `diagnostics/led_combination_search.py` (the 430–670 nm study).

---

## ⭐⭐⭐ 11 · 680 OR 710? — the question that decides whether the rebuild is a product improvement or a market  *(Edwin, 2026-09-02)*

§7.3 settles the **670 nm** reach on this project's own terms: the quiet window is the baseline anchor
the metric never had. A separate question surfaced from the other-oils analysis, and it is about **what
lies just past the top of this study's range**.

### 11.1 What 410–680 nm opens that 440–630 does not

| pigment | Soret | Qx | Qy | in **440–630**? | in **410–680**? |
|---|---|---|---|---|---|
| **protochlorophyll** *(pumpkin — our case)* | 432 | — | **625** | ⭐ yes | yes |
| **chlorophyll a** | **431** | **618** | **663** | ⛔ Soret and Qy both outside | ⭐⭐⭐ **all three inside** |
| **pheophytin a** | **409** | **609** | **664–667** | ⛔ | ⭐⭐ Qx and Qy inside, Soret at the very edge |

⭐⭐ **Chlorophyll a and its pheophytin are the pigment pair of every cold-pressed green oil that is not
pumpkin** — hemp above all. **410–680 puts that pair fully in range**, and that is the single largest
capability the rebuild adds beyond the pumpkin metric itself.

⛔ **But the Qy pair is useless as a discriminator: 663 against 664–667 is 1–4 nm.** The demetallation has
to be read on **Qx (618 vs 609, a 9 nm split)** — and ⭐ **that pair is already inside the present
440–630 window**, weak though the Qx bands are. ⇒ **The rebuild is not what makes a chlorophyll:pheophytin
ratio possible; it is what makes the pigment AMOUNT measurable.**

### 11.2 ⭐⭐⭐ What lies between 680 and 710, and why it is a different kind of thing

> **AOCS Cc 13i-96** — *total chlorophyll pigments in crude vegetable oils, expressed as pheophytin a*:
>
> **Tchl [mg/kg] = (A₆₇₀ − 0.5·A₆₃₀ − 0.5·A₇₁₀) / (345.3 · L)**

This is a **three-point, baseline-corrected absorbance in the VIS** — structurally identical to what this
instrument already computes. **630 and 670 are inside a 410–680 build. 710 is not.**

⚠ *(Note in passing what the norm's own title concedes: it says* expressed as pheophytin a *because at
670 nm chlorophyll and pheophytin cannot be told apart — §11.1's 1–4 nm. The norm sums them.)*

| range | what it buys |
|---|---|
| **440–630** *(today)* | the pumpkin metric; ⚠ a chlorophyll:pheophytin *state* ratio on the weak Qx pair, untested |
| **410–680** | ⭐⭐ the pumpkin metric improved (the eight arguments of §8.5 and `SPEC_lamp_rebuild.md`); chlorophyll a fully resolved; wine's 420 nm; beer's 430 nm |
| ⭐⭐⭐ **…to 710** | **AOCS Cc 13i-96 becomes executable** — a *published norm*, not a metric of our own |

> ⭐⭐⭐ **That is a qualitative change, not a quantitative one.** Everything this project measures today it
> had to invent and must therefore validate against a corpus of its own. **A norm arrives with its own
> authority.** Reaching 710 would mean the instrument could produce a number an oil chemist already
> accepts — at a fraction of a laboratory spectrophotometer's price.

### 11.3 ⛔ Why this is not a recommendation to extend to 710

1. ⛔ **The quiet window is IR-cut-gated.** §2.2 and §5 establish that the usable top end is bounded by
   the camera's IR-cut filter, not by the emitters. **680 → 710 may be a change to the sensor path, not
   one more star**, and this document has no measurement at 710 to say either way.
2. ⛔ **The norm is written for CRUDE oil before refining** — chlorophyll there is a catalyst poison and a
   photo-oxidation starter. Whether its absorptivity holds for a native cold-pressed oil is unestablished.
3. ⚠ **Nothing in the pumpkin case needs it.** The eight arguments for the red extension are all satisfied
   at or below 680.
4. ⚠ **And it would be a second rig change.** §7.3's closing warning applies with full force: every move
   invalidates the thresholds, and the recalibration is the expensive part.

⇒ **11-Q1:** does the present sensor path pass **710 nm** at all, and at what cost in exposure? ⭐ **This is
a measurement, not an argument** — point the existing camera at a 710 nm source, or at a broadband source
through a 710 filter, and read the counts. **It should be answered before any emitter order**, because it
decides whether the rebuild is *a better pumpkin instrument* or *an instrument that can execute a
published norm*.

⚠ **And it must not delay the order.** If 710 turns out to need a sensor change, that is a separate
project with its own budget — **R2 at 410–680 stands on its own eight arguments** and should not wait for
an answer about a different one.
