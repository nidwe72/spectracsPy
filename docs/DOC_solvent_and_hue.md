# The solvent that made the colour visible

**Internal note · 2026-08-23 · one evening's result**

<!--
  SOURCE OF TRUTH: this file. Edit the prose HERE, never the PDF.
  REGENERATE:
    python3 docs/tools/build_capture_fidelity_pdf.py \
      --source docs/DOC_solvent_and_hue.md \
      --out ../spectracs-references/business/internal/commmunication/Spectracs_SolventAndHue_2026-08-23.pdf \
      --title "The solvent that made the colour visible"
  FIGURES: docs/tools/... none — built ad hoc; the three PNGs live in docs/figures/solvent_hue_*.png
-->

On the evening of 22 August we diluted pumpkin seed oil in **sunflower oil** instead of isopropanol — a
feasibility test for MCT oil, nothing more. Two oils, one recipe, two runs.

It produced the cleanest measurement in the archive, and for the first time the difference between two
pumpkin oils was **visible to the naked eye**.

<!--TOC-->

---

## 1. Two oils, one recipe

Both fills are the standard preparation: **8 ml of solvent, 2 capillaries of oil**. Same session, same
reference, one after the other.

| | Billa Clever `001` | Lugitsch `002` |
|---|---|---|
| `Q%` — the shipped verdict metric | **21.44** | **16.21** |
| `dQ100 v2` | **+63.8** | **−21.7** |
| `R` = A(624) / A(568) | **0.673** | **1.321** |
| A_Soret 448–460 nm | 0.797 | 0.596 |
| **A_valley 500–560 nm** — the baseline | 0.165 | **0.018** |

Every metric separates them, and not narrowly. `Q%` by 5.2 units against a fill-to-fill scatter of ~0.5.
`dQ100` by 85 units. `R` by a factor of two.

![The two absorbance spectra. The shaded windows are the bands every metric is built from.](figures/solvent_hue_spectra.png)

---

## 2. ⭐ The number that matters most: 0.018

**A_valley = 0.018 on the Lugitsch fill.** That window sits between the two pigment bands and should
contain almost nothing. In the archive it usually reads 0.09 and has been as high as 0.28 — undissolved
oil, scattering light across the whole visible range and burying everything underneath it.

**0.018 is the second lowest of 116 archived runs, and the lowest at a usable pigment load.**

The reason is refractive index. Isopropanol is n ≈ 1.377; pumpkin oil is n ≈ 1.47. The oil never truly
dissolved — it dispersed, and the droplets scattered. Sunflower oil is n ≈ 1.473. Like into like: a real
solution, and the baseline simply goes away.

> **What that fill also did:** it settled **immediately**. `SETTLED_IMMEDIATE` at 106 s, `Q%` moving
> 16.213 → 16.200 across the entire run — a span of **0.03 units**, against a fill-to-fill benchmark of
> 0.38. Seven consecutive reads, flat.

That is the prize hiding behind the solvent question. The drawdown rule, the D2 coach, the twenty-minute
clock, TEST B and TEST C — the whole settling apparatus exists to wait out a clearing transient. **A fill
that has no transient does not need any of it.**

---

## 3. ⭐⭐ And you can see it

Two eprouvettes, ~3 cm of liquid, viewed end-on against a phone light table. No instrument.

![Left: Billa Clever. Right: Lugitsch. Both 8 ml + 2 capillaries — the four small rings in each tube are the two capillaries, doubled by reflection.](figures/solvent_hue_photo.png)

Measured off the photograph, five patches per tube:

| | hue, photographed | hue, predicted from the spectrum |
|---|---|---|
| Billa Clever | **90.1° ± 3.5** | **88.0°** |
| Lugitsch | **106.2° ± 2.0** | 118.2° |

**16.1° apart, against a combined scatter of ±4.0° — a four-sigma separation, by eye, with no instrument
in the loop.**

And the first row is the one to notice. An uncalibrated phone photograph, automatic white balance, no
grey card — and the spectrometer predicted Billa's hue to **within two degrees**.

![The same two oils rendered from the spectrum alone, at both path lengths.](figures/solvent_hue_swatches.png)

---

## 4. Why this matters beyond one evening

**A second, independent channel.** Every threshold we own — `Q%`'s T = 18.6, `dQ100`'s T = 30.0 — is a
constant fitted on the corpus it is scored on. That is the honest worry behind the pre-registration work.
A naked-eye colour difference depends on **no window, no threshold and no corpus**. It is the one thing in
the project that cannot be accused of circularity.

**And it agrees with the metric.** Across the 26 archived fills at the default recipe, chroma and `Q%`
correlate at **r = −0.79** — and **−0.77** once turbidity is regressed out of both sides. They are two
views of one axis, not two unrelated numbers.

**The colour pipeline now renders what the eye sees.** The fix shipped on 23 August: a sixth chip that
keeps luminance and renders at a declared 3 cm viewing path, plus excitation purity replacing a saturation
field that read 100 % on every sample ever measured. 579 tests green.

**A free out-of-sample result.** The colour code extrapolates the un-measured 636–780 nm region. We had
been holding the last measured sample across it; that would have predicted Billa at 115°. The photograph
says 90°. The conservative assumption gives 86°. **The photograph arrived after the choice was made and
could have refuted it — instead it settled a question the spectra alone could not.**

---

## 5. Next: MCT oil

Sunflower was only ever the stand-in. It proved the two things that transfer:

- a **triglyceride solvent dissolves pumpkin oil out of the capillaries** — the thing we actually set out to test
- and an **RI-matched solvent removes the baseline**

MCT (medium-chain triglyceride, C8/C10) should be better on all three counts where sunflower is weak:

| | sunflower | **MCT** |
|---|---|---|
| double bonds | ~60 % linoleic — photo-oxidises under the lamp | **saturated — none.** That is why it is sold as a shelf-stable carrier oil |
| own colour | +0.035 A at 450 nm (a carotenoid tail we must reference out) | **water-clear** |
| refractive index vs pumpkin ≈ 1.47 | 1.473 | 1.449 — still far closer than IPA's 1.377 |
| viscosity | ~50 mPa·s | ~25–30 — mixes more easily |
| evaporation | none | none. *IPA evaporates, and a 20-minute run concentrates the sample* |

There is even a number to aim at. The baseline grows with loading as `F ∝ c^p`: **p ≈ 4.3–6.2 in
isopropanol, p ≈ 2.0 in sunflower.** A true solution is **p = 1**. Two fills at different loadings measure
it in one evening, and MCT should land at or near 1.

---

## 6. What this is not — read before quoting any of it

> This note is written to be honest as well as encouraging. Five things it does **not** establish:

1. **n = 1 per oil.** Two runs. Everything above is a single comparison, not a distribution.
2. **The Billa run is the weakest in the set** — flagged `DEGRADING_FILL`, answer taken at the first look,
   with a reference 14 % dimmer than its neighbours and a dropout at 610 nm.
3. **No threshold survives a solvent change.** `T = 18.6` and `T = 30.0` were fitted in isopropanol and
   would both need re-deriving in MCT. The *separation* travels; the *numbers* do not.
4. **The colour gap is mostly the baseline, not the pigment.** With the baselines matched, the residual
   pigment-only difference is ΔE00 ≈ 3.5 — noticeable side by side, not obvious across a room. What makes
   the tubes look so different is the 0.165-versus-0.018 baseline. That is real and reproducible, but it
   is a statement about how the oil disperses, not yet about how green it is.
5. **MCT itself is untested.** Everything in §5 is a prediction.

---

## 7. The honest summary

One evening, two runs, one solvent swap:

- the **cleanest baseline in 116 runs** (0.018 A), and a fill that **settled in 106 seconds** with a 0.03-unit spread
- **all three metrics separating the two oils** by wide margins
- a **four-sigma colour difference visible by eye**, with the spectrometer predicting one of the two hues to two degrees
- a **shipped fix** so the report renders what the tube looks like
- and a **measured target** — `p = 1` — for the MCT run that comes next

⭐ The measurement is not the bottleneck any more. The preparation was, and we now know what to do about it.
