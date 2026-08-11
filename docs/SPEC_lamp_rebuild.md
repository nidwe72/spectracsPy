# SPEC — THE LAMP REBUILD (seven Avonec emitters, chosen on measured noise)

> ## STATUS: DESIGN. Nothing implemented, nothing ordered.
> This document selects a **seven-emitter lamp** and states what must be re-measured after it is built.
> It **supersedes the build recommendation** of `DOC_lamp_410_680.md` §7.1 (R2), and §11 lists the
> corrections to that chapter which this one implies.
>
> ⚠ **The numbers in §3, §5 and §6 came from an ad-hoc pass and are superseded.**
> `DOC_lamp_rebuild.md` + `diagnostics/lamp_rebuild_search.py` are now the authority: a full enumeration
> of **31 425** seven-emitter allocations against an objective that also scores the **doublet contrast**
> and the **660–680 quiet window**, with band means properly averaged over their bins. **The build in §1
> is unchanged** — it comes out rank 6 of 31 425, within 2.6 % of rank 1 and ahead of it on every other
> axis (`DOC_lamp_rebuild.md` §5). R2 as published lands at **rank 206**.

**Origin.** Edwin, 2026-08-11: the DEV plugin's capture clamp was moved to **400 nm**, a DIY LED lamp with a
violet front end was put behind a diffuser, and two runs were captured (`20260811A/001`, `/002`). Those two
runs measure a stretch — 400–440 nm — that no run in the archive had ever contained, and what they measure
contradicts three inputs of the lamp study. This document redoes the lamp choice on the new evidence.

---

## 1 · The question, and the answer

**Question.** Which seven 3 W emitters should the lamp carry?

⭐ **Answer.**

| qty | Avonec part | peak | what it is for |
|---|---|---|---|
| **2 ×** | `410nm-420nm` | 421 nm | sits on the measured Soret peak 1 (421.4 nm) |
| **1 ×** | `440nm-450nm` | 442 nm (half 432 / 453) | the dip, Soret peak 2 (436.5) and the shipped 448–460 band |
| **1 ×** | `480nm-485nm` | 480 nm (half 470 / 496) | fills the 476 nm hole — the largest single gain over R2 |
| **2 ×** | `4000k-4500k` | phosphor 585, pump 448 | the whole 500–650 backbone: clarity, Q band, far anchor |
| **1 ×** | `630nm-640nm` | 636 nm | the 627 nm fourth peak and the 620–630 far anchor |

All Avonec, all Starplatine, one vendor, one order. **Buy all seven new** — the emitters in the current DIY
lamp cannot be identified (§4.3) and an unknown bin moves the balance the whole design rests on.

---

## 2 · What is new since `DOC_lamp_410_680.md`

Three of that study's inputs have changed. Two are measurements it did not have; one is an arithmetic
error in the analysis that produced the first draft of this document, corrected here.

### 2.1 ⭐ The Soret is a DOUBLET, and its peak is at 421 nm — not 439

`DOC_lamp_410_680.md` Figure 5 states the composite blue maximum sits *"near 440 nm, not at the Soret's
432 nm centre"*. The measurement puts it at **421.4 nm**, and resolves **two** peaks with a dip between:

| | run 001 | run 002 | Fruhwirth Fig. 3A (digitised) |
|---|---|---|---|
| Soret peak 1 | 421.2 | 421.4 | 424.8 |
| dip | 431.8 | 432.8 | 430.5 |
| Soret peak 2 | 436.5 | 436.5 | 436.2 |
| Q | 579.9 | — | 573.8 |
| Qy | — | 627.6 | 629.1 |

⭐ **The doublet is not an artefact.** The frames were split into **20 independent 40-row bands along the
slit** and A(λ) recomputed for each: **20 of 20 resolve it**, peak 1 at 421.3 ± 0.9 nm, peak 2 at
436.7 ± 0.9 nm. The lamp's own emitter peaks at ~431 — where A has its *dip* — so lamp structure cannot
be producing it, and the literature dip sits at 430.5, 1.3 nm away.

⚠ **The literature column is a digitisation, not the authors' claim.** `Fruhwirth & Hermetter (2007)`
states **no absorption peak position anywhere in its prose** — the only wavelength in the text is the
635 nm *fluorescence emission* maximum. Every number in that column is read off Fig. 3A by
`comparisons/fig3A_vs_spectracs/digitize_and_plot.py`, whose axis calibration is `300 nm → px 62,
700 nm → px 344` = **1.42 nm per pixel**, with only 8 px between the two Soret peaks. Its own error is
±2–3 nm, which is larger than every discrepancy in the table.

### 2.2 ⛔ The study's blue camera-response model is falsified

`led_lamp_410_680.instrumentResponse` says so itself: *"Below 440 nm nothing is measured at all — the blue
end is a stated assumption, not a result."* Applied to R2 at a 240 DN peak it predicts **13 DN
(optimistic) / 3 DN (pessimistic) at 410 nm**.

⭐ **Run 002 measures 128 DN at 410 nm**, with fewer violet emitters than R2 carries. The modelled blue
roll-off is roughly an order of magnitude too pessimistic. **Every blue-end forecast in that study
understates what the instrument delivers**, and no forecast in this document uses that model.

### 2.3 ⚠ THE ARITHMETIC CORRECTION — read this before reusing any earlier number

Absorbance is defined on the **linear** values; the noise and the plots live in **display DN**; the two are
related by the `pow2.2` capture decode. Therefore:

```
S_dn = R_dn × 10^(−A / 2.2)          NOT  R_dn × 10^(−A)
σ_A  = 0.434 × 2.2 × sqrt((σ_dn/S_dn)² + (σ_dn/R_dn)²)
     = 0.955 × sqrt(...)
```

Verified against run 002 at 421 nm: R = 131 DN, A = 1.210 → predicts S = **37.0 DN**; measured **37.0 DN**.

⛔ **An earlier pass of this analysis used `10^(−A)` on the DN axis.** It made every candidate's sample
levels look ~2.2× darker than they are, worst where A is largest — the blue — and it produced two
conclusions that are **wrong and are withdrawn here**:

| withdrawn claim | corrected |
|---|---|
| *"R2 is 2–10× noisier than the current lamp below 500 nm; do not build it"* | R2 is **better** than the current lamp at 421, 432 and 625–640; it loses only at 460 and 476 |
| *"at the capillary dose the 421 nm peak lands at 1.3 DN, twelve times under the floor"* | it lands at **20.6 DN** under R2 — above the 16 DN guard, though with no margin |

---

## 3 · The objective, and why it differs from the study's

`DOC_lamp_410_680.md` scored **emitted SPD** through a modelled camera response, on a median across the
415–450 nm bracket plus a worst-band slope term. This document scores something narrower and closer to the
result:

> ⭐ **The noise the metric would actually carry**, `σ_A(λ)`, at the wavelengths that carry a number —
> computed from a **measured** absorbance curve and a **measured** noise level, with the lamp entering only
> through its emitted SPD normalised to a 240 DN peak.

Three inputs, all measured, none modelled:

| input | value | source |
|---|---|---|
| the sample's A(λ) | run 002, 400–636 nm | `20260811A/002.pdf`, embedded `workflow.json` |
| per-curve noise | **0.5 DN**, in *both* captures, in *every* band | §4.2 |
| the ceiling | 240 DN of 255 — the exposure is set by the lamp's own peak | §4.2 |

**Scored wavelengths:** 410, 421, 432, 436.5, 455, 476, 525, 570, 625, 640 nm — the doublet, the shipped
Soret window, the crossover, the clarity floor, the Q band, the far anchor. Ranking is **minimax**: the
worst band decides, because a metric is only as good as its weakest input.

⚠ **The two objectives disagree about one part, and this is why.** §4.2 of the study parked the cyan 480
as *"only at 8 slots — fills the 476 nm hole 3.6× but costs half the Soret bracket at seven"*. Under the
objective above it is the single most valuable part on the board (§7.1). The bracket-median penalises it;
the measured worst-band does not. ⛔ **Neither ranking is "the" answer — each is only as good as its
objective**, and this one has the advantage of being anchored on data the study did not have.

---

## 4 · The measurements this rests on

### 4.1 The blue runs — `20260811A/001` and `/002`

Captured 2026-08-11, 20:53 and 21:59. ROI **400.06–635.87 nm, 1634 bins** — the first runs in the archive
containing 400–440 nm. `001` was taken with lenses on the LEDs; `002` after Edwin removed them.

| | 001 | 002 |
|---|---|---|
| blue maximum | **0.802 @ 421.2 nm** | **1.209 @ 421.5 nm** |
| A(440–447) | 0.5822 | 0.7262 |
| A(448–460) | 0.2375 | 0.3247 |
| reference DN @ 410 / 432 / 625 / 635 | 90 / 178 / 22 / 13 | **128 / 169 / 37 / 23** |
| σ_A(620–636) | 0.057 | **0.021** |

⭐ **Removing the lenses roughly doubled the green/red half** (520 nm 29 → 66 DN, 550 nm 46 → 98, 625 nm
22 → 37) and cut the far-anchor noise **2.7×**. It also revealed a distinct emitter peak at **413 nm** that
`001` shows only as a shoulder.

### 4.2 The noise is the same in both captures — and that settles a recurring question

Edwin, repeatedly: *"the reference curve is smooth and the sample curve is not."* Measured, run 002,
high-frequency residual after a 9 nm smooth, in display DN:

| band | ref level | ref noise | sample level | sample noise |
|---|---|---|---|---|
| 405–430 | 133 | **0.59** | 44 | **0.53** |
| 430–450 | 146 | 0.37 | 64 | 0.48 |
| 490–520 | 62 | 0.10 | 62 | 0.10 |
| 520–560 | 89 | 0.09 | 89 | 0.11 |
| 620–636 | 32 | 0.36 | 26 | 0.51 |

⭐ **The sample is not noisier.** Same ~0.1–0.6 DN wiggle in both, everywhere. It only *looks* rougher
because the oil absorbs 0.9–1.2 A in the blue, dropping that curve to a third of the reference's height on
a shared axis. Since `A = −log10(S/R)` responds to *relative* error, the sample contributes **86 % of the
noise variance** at 405–450 nm — not because anything is wrong with it, but because it is the smaller of
the two numbers. ⇒ **The noise floor of the measurement is set by the darkest thing in the sample capture,
always**, and `σ_dn = 0.5 DN` is the constant that carries this into every forecast below.

⚠ **This also bounds what a lamp can fix.** The lamp cannot reduce σ_dn; it can only raise the level the
0.5 DN sits on. That is the entire mechanism by which a flatter lamp helps.

### 4.3 The current lamp is identified by its own shape — and the whites are the fault

| | pump ÷ I(550) | I(630) ÷ pump |
|---|---|---|
| Avonec `2900k-3200k` | 0.50 | 1.67 |
| Avonec `4000k-4500k` | 0.61 | 1.20 |
| Avonec `6500k-7000k` | 1.25 | 0.40 |
| Avonec `10000k-20000k` | 2.50 | 0.15 |
| **the current DIY lamp, measured** | **2.23** | **0.14** |

⭐ **The whites are cool — 10000 K class.** One fact explains both defects at once: the 464 nm pump that
consumes the dynamic range, *and* the dead red end. A cool white has almost no phosphor past 600 nm.

⚠ **Dimming them would not help.** Drive current scales pump and phosphor together, so the green and red
would fall with the peak. **They must be replaced, not attenuated.**

⛔ **The blue emitters cannot be identified.** The reference resolves peaks at **413, 431, 464, 473 nm**;
the catalogue's `410nm-420nm` digitises to a **421 nm** peak and nothing in it peaks at 413. Edwin
(2026-08-11): *"not sure about the LEDs in my current build, might also be partly chinese."* ⇒ **no part
of the current lamp may be carried into the new build.**

### 4.4 The capillary corpus — `20260807A/B/C/D`

Four oils × three measurements, one session, one preparation recipe. ROI **440.0–629.8 nm**. Described in
`spectracs-references/business/internal/commmunication/Spectracs_Oil_Panel_2026-08-07.pdf`.

| run | oil | €/l | M448 |
|---|---|---|---|
| `20260807D` | Steirerkraft g.g.A. | 37.96 | 9.96 |
| `20260807A` | Spar Steirisches g.g.A. | 19.98 | 8.76 |
| `20260807C` | Spar Premium g.g.A. | 35.96 | 7.69 |
| `20260807B` | Spar S-Budget (brown) | 11.98 | 6.51 |

⭐ **The cross-check these two corpora make possible.** The capillary runs read 440–447 nm on *starved*
bins; the new lamp reads the same stretch with real light. The dilution-invariant ratio
`A(440–447) / A(448–460)`:

| | ratio |
|---|---|
| Steirerkraft / Spar Steirisches / Spar Premium / S-Budget (capillary) | 2.283 / 2.220 / 2.319 / 2.286 |
| `20260811A/001` / `/002` (real light) | 2.450 / 2.237 |

**They agree** — the new-lamp runs bracket the capillary values. ⛔ This kills `DOC_lamp_410_680.md`
§8.2's preferred reading **(b)**, *"the rig's 440–447 bins are not real absorbance"*. Together with the
421.4 nm peak it leaves reading **(a)**: the forecast model's Soret (centre 432, FWHM 42) plus carotenoid
(455, FWHM 62) is genuinely mis-placed and too broad.

⚠ **And the blue does not discriminate — yet.** That ratio spreads **4 %** across four oils whose M448
gaps are 14–18 %. §12.1 is the test that settles whether the blue end earns its slots at all.

---

## 5 · The build

Restating §1 with the numbers each part is bought for.

| qty | part | delivers |
|---|---|---|
| 2 × | `410nm-420nm` | 410 nm: **139 DN**; 421 nm: **237 DN**. σ_A(421) 0.0074 |
| 1 × | `440nm-450nm` | 436.5 nm: 202 DN. σ_A(436.5) 0.0066 against R2's 0.0090 |
| 1 × | `480nm-485nm` | 476 nm: **123 DN** against R2's **29**. σ_A(476) **0.0061** against R2's **0.0261** |
| 2 × | `4000k-4500k` | 525 nm 146 DN, 570 nm 181 DN — σ_A 0.0047 / 0.0039 |
| 1 × | `630nm-640nm` | 625 nm 175 DN, 640 nm 203 DN — σ_A 0.0042 / 0.0036 |

All figures are emitted SPD normalised to a 240 DN peak, with σ_A computed per §2.3 on run 002's
absorbance.

---

## 6 · The comparison

Reference DN, peak normalised to 240:

| build | 410 | 421 | 432 | 436.5 | 455 | 476 | 525 | 570 | 625 | 640 | 660 | flatness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current DIY lamp (measured) | 128 | 131 | 169 | 148 | 190 | 174 | 70 | 92 | 37 | — | — | 10.1× |
| **★ this build** | 139 | 237 | 194 | 202 | 149 | **123** | 146 | 181 | 175 | 203 | 79 | **2.5×** |
| R2 with `630nm-640` | 106 | 205 | 194 | 148 | 108 | **29** | 160 | 199 | 176 | 196 | 86 | 8.4× |
| R2 as published | 106 | 206 | 194 | 148 | 108 | **29** | 161 | 200 | 147 | 160 | 164 | 8.4× |

σ_A on the same sample:

| build | 410 | 421 | 432 | 436.5 | 455 | **476** | 525 | 570 | **625** | 640 | **worst** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| current DIY lamp | 0.0096 | 0.0134 | 0.0077 | 0.0090 | **0.0042** | **0.0043** | 0.0097 | 0.0076 | 0.0197 | — | — |
| **★ this build** | **0.0089** | **0.0074** | **0.0067** | **0.0066** | 0.0053 | 0.0061 | **0.0047** | **0.0039** | **0.0042** | **0.0036** | **0.0089** |
| R2 with `630nm-640` | 0.0117 | 0.0086 | 0.0067 | 0.0090 | 0.0074 | 0.0262 | 0.0042 | 0.0035 | 0.0042 | 0.0038 | 0.0262 |
| R2 as published | 0.0116 | 0.0086 | 0.0067 | 0.0090 | 0.0073 | 0.0261 | 0.0042 | 0.0035 | 0.0050 | 0.0046 | 0.0261 |

⭐ **Worst band 0.0089 against R2's 0.0261 — 2.9×.** Flatness 2.5× against 8.4×. Better than the current
lamp at every scored band except 455 and 476, where it is marginally behind.

---

## 7 · Why it beats R2 — two substitutions

### 7.1 ⭐ Drop the third white, add `480nm-485`

R2 spends three slots on `4000k-4500k`. The phosphor already owns 500–650 nm; a third one mostly raises
the **pump peak that sets the exposure**, which costs every other band. Spending that slot on the cyan
takes 476 nm from **29 DN to 123 DN** — σ_A **0.0262 → 0.0061**. That one substitution is the entire 2.9×
on the worst band.

⭐ **And it lands on a known defect.** 476 nm is where the reduction's **Bayer B→G crossover** sits
(§12.3). R2 as published would put its deepest spectral hole directly on the largest artefact in the
stored spectra.

### 7.2 `440nm-450` instead of `430nm-435`

`430nm-435` sits on the *dip* of the doublet. `440nm-450` (peak 442, half-points 432/453) spans the dip,
Soret peak 2 at 436.5 and the shipped 448–460 window. σ_A(436.5) **0.0090 → 0.0066**.

### 7.3 ⛔ Do NOT add a fourth white

Tested (`4W + 2×410 + 1×430 + 1×630-640`): the extra white dilutes the violets and every blue band gets
worse — 410 nm 0.0117 → 0.0154, 421 nm 0.0086 → 0.0111 — with no gain in the red. The study's **count of
three** whites is closer to right than four; this document goes to **two**.

---

## 8 · The one open choice — `630nm-640` or `660nm`

Identical below 600 nm. The trade:

| red part | 625 | 640 | 660 |
|---|---|---|---|
| `630nm-640` | **0.0042** | **0.0036** | 0.0086 |
| `660nm` | 0.0055 | 0.0048 | **0.0037** |

⭐ **660 nm still reads 79 DN with no 660 part at all** — carried by the `4000k-4500k` phosphor tail plus
the `630nm-640` flank. The quiet window survives either way; the `660nm` part only sharpens it.

⇒ **Take `630nm-640`**, unless §12.2 comes back saying the camera genuinely reaches past 660 nm *and* the
quiet window is wanted as a primary anchor. The far anchor at 620–630 is a shipped metric input today; the
quiet window is not.

---

## 9 · What must be re-done after the swap

⚠ **Every one of these invalidates the thresholds, and the recalibration is the expensive part. Build it
as ONE rig change.** (`DOC_lamp_410_680.md` §7.3.)

| | what | why |
|---|---|---|
| 1 | **Re-derive the DN guard** (`DevSpectralPlugin.DN_GUARD_LOW/HIGH`, `DN_TARGET_LOW/HIGH` = 16 / 60 / 20 / 40) | already invalid: on the DIY lamp the sample sits at 57–199 DN across the Soret against a "60 DN = too dilute" edge |
| 2 | **Re-derive the Roast-Ampel thresholds** (`SPEC_roast_ampel.md`) | already invalid: run 002's gauges came back at 1.23 and 1.63 against bands of 4.8–9.6 and 6.0–12.0 — pegged off-scale |
| 3 | **Re-measure `B_Soret`** (`SPEC_metric_research.md` §7.2 = 0.6924 on 448–460) | the absolute level anchor; a window and lamp change moves it |
| 4 | **Re-run the null series** (`SPEC_capture_quality.md` §16.26, floor 0.42 %) | the instrument floor is lamp-dependent |
| 5 | **Re-check frame rejection at the new exposure** | two whites instead of three means less total flux and a longer exposure |
| 6 | **Re-derive the dose** | §12.4 |

⛔ **The colour chips are not comparable across this change.** `EvaluationColorUtil` integrates the whole
curve, so the colour row changes with the lamp *and* with the window. The ratio metrics do not.

---

## 10 · What this document does NOT change

| | |
|---|---|
| `WAVELENGTH_MIN_NM = 400.0` | already shipped 2026-08-11 and vindicated — Soret peak 1 at 421.4 nm lives inside it |
| the metric bands | 448–460, 510–540, 560–580, 620–630 all stay; this is a lamp change, not a metric change |
| the capillary preparation | `SPEC_capture_quality.md` §16.27.7 shows it does not shift the scale; only the *dose* is re-opened (§12.4) |
| the diffuser | §12.5 — a separate, cheaper, and probably more valuable fix |

---

## 11 · Corrections this implies to `DOC_lamp_410_680.md`

⛔ **Not applied.** Listed so the disagreement is on the record rather than silently forked.

| § | what it says | what the measurement says |
|---|---|---|
| Figure 5 caption | *"the composite blue maximum sits near 440 nm"* | **421.4 nm**, and it is a doublet — 20/20 independent slit rows |
| §8.2 | the model/rig mismatch is *"consistent with a known instrument artefact"* (reading b) | reading **(a)**: the 440–447 : 448–460 ratio agrees between starved and real-light measurements (§4.4), so the bins were not the fault. The model's Soret is mis-placed |
| §8 model | `gaussian(432, FWHM 42)` + `gaussian(455, FWHM 62)` carotenoid | cannot produce a doublet at 421/436.5 with a dip at 432. `diagnostics/oil_forecast_410_680.py` lines 84–88 need refitting against `20260811A` |
| `instrumentResponse` | blue roll-off, *"a stated assumption, not a result"* | falsified: 13 DN predicted at 410 nm, **128 DN measured** (§2.2) |
| §7.1 | R2 is the build | superseded by §1 — on a measured-noise objective (§3) |
| §4.2 | cyan 480 *"only at 8 slots"* | the most valuable part on a 7-slot board under this objective (§7.1) |

---

## 12 · Open questions — the tests that would change this

### 12.1 Does the blue end discriminate? — worth measuring, **not** a purchase gate

There is **no evidence yet that the blue end separates oils.** §2.1 proves the doublet exists; nothing
proves it *moves*. The only blue-side quantity measured across four real oils spreads 4 % against M448
gaps of 14–18 %. `DOC_lamp_410_680.md` §2.1 argues demetallation blue-shifts the Soret — plausible
chemistry, zero measurements.

> ⚠ **An earlier draft made this a gate on the order. That was wrong** (Edwin, 2026-08-11: *"only because
> it might not deliver a better metric it does also not per hurts"*). The two violet slots cost the shipped
> metric **0.00023 in A** on its worst band — against §12.3's 0.15–0.24 crossover step and a measured
> far-anchor noise of 0.021 — and buy **13.3×** at the Soret peak. **Buy them regardless of how the
> experiment comes out.** Full numbers: `DOC_lamp_rebuild.md` §9.1.

⭐ **The experiment is still worth running, and needs no purchase.** Measure **Steirerkraft** and
**S-Budget** — the greenest and the brown, both on the shelf — on the current lamp with the ROI at 400 nm.
If the doublet separates them there is a new metric to be had; if not, the board is unaffected and the
question is merely still open.

### 12.2 The Eu³⁺ test — decides `630nm-640` vs `660nm`

`DOC_lamp_410_680.md` §6.2a, unresolved: runs `20260808A/B` show both old lamps collapsing to ~0.1 DN by
656 nm, and the chapter cannot say whether that is the lamps or the camera's IR-cut. `EUROPIUM_RED_FAR_680
/690/700` (687.7, 693.7, 707.0 nm) are strong in the calibration lamp. Open the ROI past 690 on a
**calibration-lamp** capture: lines visible ⇒ the camera passes 690 and §6's withdrawal stands; lines
absent ⇒ the IR-cut is the gate and no red emitter reaches the quiet window.

### 12.3 ⚠ The channel-crossover steps — bigger than anything the lamp can fix

A(λ) shows level shifts at ~471, ~481, ~583 and ~614 nm, exactly where the reduction switches Bayer
channel. Per-channel absorbance at the same column, run 002:

| λ | R ch | G ch | B ch | stored |
|---|---|---|---|---|
| 480 | · | +0.162 | +0.217 | +0.203 |
| 485 | · | +0.056 | +0.209 | **+0.050** |
| 580 | +0.245 | +0.042 | · | **+0.035** |
| 585 | +0.182 | +0.020 | · | +0.171 |

⭐ **A spectrograph column carries one wavelength**, so R, G and B at that column are three sensitivities
looking at the same light and must return the same `S/R`. They differ by **0.15–0.24 in A** — at healthy
DN in both channels. That is **ten times** the entire noise floor this document optimises.

**Ruled out:** a per-channel gain difference between the captures. The `CAPTURE-SETTINGS` lines
(`CapturePanel.py:515`) are identical for `role=REFERENCE` and `role=SAMPLE`.

**Leading suspect:** stray light inside the spectrograph — the sample transmits 6 % at the Soret while the
reference is at full strength, so scattered blue is a far larger fraction of the sample's weak-channel
signal. ⇒ **Test:** recapture at A(Soret) ≈ 0.7. Steps shrink ⇒ glare, and the fix is baffling and
blackening. Steps hold ⇒ the reduction's channel handling.

⛔ **No lamp fixes this**, and this build's `480nm-485` only mitigates the 476 nm one by lifting the level.

### 12.4 ⚠ The dose — corrected

An earlier draft said *"dilute to ≈ ×2.75 below the capillary dose"*. **That number was picked to clear
the DN floor, which is the wrong criterion**: diluting lifts the sample level and shrinks the signal at the
same rate, so `σ_A` alone always says "more dilute" and never turns around.

Scored on **signal-to-noise of the band depth** the optimum is **f ≈ 1.5–2.0** — 2 capillaries in
18–24 mL against the `20260807` session's 12 mL. The doublet is the only quantity wanting extra dilution;
every other band prefers less. ⭐ `20260811A/002` already sat at **f = 1.91**. Sweep in
`DOC_lamp_rebuild.md` §9.2, reproduced by `lamp_rebuild_search.py`.

⚠ Even at the best dose the doublet **contrast** carries SNR ≈ 3.2 read as single bins (≈ 5× better read
over ±2 nm, matching the ~9σ measured on run 001). Comfortably visible; a few-σ **metric input**.

`SPEC_capture_quality.md` §16.23.6 concluded that on the old lamp *no* dilution satisfies both ends. On
this curve one does.

### 12.5 ⭐ The optical path — cheaper than the lamp, and probably worth more

> ⭐ **The diffuser is the boundary between two zones that want OPPOSITE finishes**, and the spectrometer
> is **two cylinders**, not cones — the harder case: in a converging cone every wall bounce steepens the
> ray and stray light walks itself out; in a parallel-walled tube a ray keeps its angle for ever and
> reaches the slit as if it were signal.
>
> **board → diffuser: matte WHITE** (an integrating cavity; bounces buy throughput).
> **diffuser → sample → slit: matte BLACK + baffles** (the optical path; bounces are stray light).
> ⛔ A reflective tube wall would be actively harmful — it is the mechanism §12.3 is looking for.
>
> Baffles are washers: outer edge on the wall, hole just clearing the bundle, knife edge inward under
> ~0.1 mm with the bevel toward the slit. ⭐ **Place them by sightline** — eye at the slit, no lit wall
> visible. ⭐ **Two cylinders is a free diagnostic:** blacken one at a time and see which moves the
> 481 / 583 nm steps. Figure 8 and the full argument: `DOC_lamp_rebuild.md` §9.5.

⚠ Height is not the constraint, and extra height is not automatically a loss: for an extended Lambertian
source throughput is radiance × étendue, so a diffuser at 20 cm loses nothing **provided it still overfills
the tube's acceptance** — it must grow with the distance, roughly `aperture + 2·h·tan(acceptance)`. If it
does not grow, the loss goes as 1/h² and 11 → 20 cm costs 3.3×.


Measured from the raw frames: the reference's normalised shape varies **15–30 % (blue) and 39–53 %
(green/red) along the slit**, and row-band mean absorbance runs 0.245 → 0.270 top to bottom. Removing the
lenses already halved the flatness ratio (11.2× → 6.9×) and cut far-anchor noise 2.7×.

Geometry is not the constraint: for pitch `p` = 2.5 cm at height `h` = 11 cm the residual ripple goes as
`exp(−2πh/p)` ≈ 0. If emitters are still visible as discs, light is **bypassing** the diffuser.

| | |
|---|---|
| ⭐ **material** | **PTFE sheet 0.5–1 mm** — near-Lambertian, spectrally flat 300–2500 nm, no fluorescence |
| ⛔ **never** | paper, vellum, baking paper, Mylar, unspecified white plastic — **optical brighteners** absorb 350–420 nm and re-emit 420–470 nm, i.e. exactly on the doublet |
| | close the cavity, matte-white walls, two diffusers (~3 cm and ~10 cm), sealed at the rim |
| | **test any candidate in 2 min:** capture the reference with and without it and divide — a brightener shows as a dip at 380–420 plus a bump at 420–470 |
| | **target:** along-slit shape variation < 5 % (today 15–53 %) |

⚠ **Take the Mylar off the sample jar.** Diffusing at the sample defeats the cone's collimation, spreads
the path length, and does not divide out if it reseats between the two captures.

---

## 13 · Reproduce

```
source venv/bin/activate
PYTHONPATH=diagnostics python diagnostics/led_lamp_410_680.py --figures   # digitised Avonec SPDs
```

Data used, all with `workflow.json` embedded and readable via
`json.loads(PdfReader(path).attachments["workflow.json"][0])`:

| | |
|---|---|
| blue runs | `spectracs-references/tmp/20260811A/001.pdf`, `002.pdf` |
| capillary corpus | `spectracs-references/tmp/20260807{A,B,C,D}/00{1,2,3}.pdf` |
| literature Fig. 3A | `spectracs-references/comparisons/fig3A_vs_spectracs/data/fig3a_literature_digitized.csv` |
| oil panel | `spectracs-references/business/internal/commmunication/Spectracs_Oil_Panel_2026-08-07.pdf` |

⚠ **The selection search itself is not yet a committed script.** It enumerates every 7-slot allocation of
5 white × 10 colour Avonec parts (≤ 4 colour kinds), scores each per §3, and ranks minimax. It should
become `diagnostics/lamp_rebuild_search.py` before any of §6's numbers are quoted elsewhere.
