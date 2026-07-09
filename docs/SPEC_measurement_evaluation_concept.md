# SPEC — Measurement & Evaluation Concept (sound, LED-independent)

> Status: **DESIGN / CONCEPT (spec-first).** Defines *how* a Spectracs measurement is turned into a
> stable quality verdict. Supersedes the "absorption → colour" wording in
> `spectracs-docs/SPECTRAL_WORKFLOW_CONCEPT.md` §4 (see §6). Physics: `KB_spectroscopy_physics.md`.
> Domain facts: `KB_led_and_oil_spectra.md`. The playground (`SPEC_pipeline_playground.md`) is the
> dev/test bench that exercises this concept.
>
> **Concrete evaluation as of 2026-07: the peak-ratio criterion.** The current, implemented realisation of
> this concept is `SPEC_pumpkin_peak_ratio_eval.md` — see its **§0 Concept & rationale**. It reads the
> specific pigment bands (Soret-flank blue + ~575 nm Q-band + green anchor → a *greenness* ratio) instead of
> collapsing the spectrum to a single hue, so it separates *why* an oil is off (browned vs faded vs turbid).
> The hue/colour verdict below remains the earlier framing; the peak-ratio is the physically-specific
> successor, running render-only in the dev measurement bench pending real-oil calibration.

---

## 1. Purpose

Objective quality management for **pumpkin-seed-oil**: the roast level shows as **colour** (too brown =
over-roasted, too green = under-roasted, a "perfect green" = best). We derive that colour **objectively
from a spectrum**, and the derivation must be **stable** — independent of the exact LED light source,
which drifts and ages.

## 2. The four spectra (one mental model)

```
R(λ)  REFERENCE     = light through the blank (isopropanol)   ≈ the LED SPD
S(λ)  SAMPLE        = light through the oil = R(λ)·T(λ)        (raw camera reading — illuminant-dependent!)
T(λ)  transmittance = S/R = 10^(−A)                           (intrinsic to the oil — illuminant-free)
A(λ)  absorbance    = −log10(S/R)                             (Beer–Lambert; same info as T)
```
Intensities are 8-bit grayscale (0–255), arbitrary units; only **ratios** (T) and **shape** (colour) are
meaningful — never absolute `S`.

## 3. The sound pipeline (canonical, do these in order)

```
1. MEASURE   R and S, each averaged over many frames           (SNR ↑; SpectrumUtil.mean)
2. CONDITION smooth → removeBaseline → rebin(380–780) → normalize   (SpectrumUtil, both R and S)
3. NORMALIZE T(λ) = S(λ) / R(λ)        ◀── the step that removes the LEDs
4. COLOUR    QColor = spectrumToColor(T)  under a FIXED D65     (intrinsic oil colour, LED-independent)
5. VERDICT   hue(QColor) → green↔brown band → label + swatch    (+ keep A = −log10(T) for the plot)
```
**Colour the `T`** — not raw `S` (double-counts the LED light) and not `A` (gives the complementary
colour). Verdict from the **hue**; `A` is for the absorption plot/analysis only.

## 4. Why this is stable (the whole reason for the reference)

- `S = R·T` is **illuminant-dependent**: swap/age an LED → `R` changes → the colour of `S` shifts for the
  *same* oil. **Judging raw `S` is not stable.** (This is the 3-years-ago prototype's weakness.)
- `T = S/R` **cancels `R`** (Beer–Lambert: `T = 10^(−εcl)`, illuminant-free). This is exactly what a
  spectrophotometer does when it measures a blank and reports %T. The CIE conversion (step 4) then uses a
  **fixed D65**, not the LEDs → the colour is **LED-independent and stable in the mean**.
- **Under an LED swap (still gap-free):** `T`/`A` don't move in expectation; only **noise** changes —
  relative noise in `T(λ) ≈ noise / R(λ)`, blowing up where `R` is low and **undefined at a true gap**
  (`R≈0`). The hue is a **CMF-weighted integral over all λ**, so local noise averages out.
- **Design rule for the light source:** `R` must be **gap-free** and **strong across the diagnostic
  bands** — green window **520–560**, red **630–670**, blue **430–480**. Then the verdict barely moves
  when LEDs are swapped or age. (A warm-white continuum + colour peaks achieves this — see
  `KB_led_and_oil_spectra.md`.)

> **Testable claim:** with this pipeline, swapping a diagnostic-band-preserving LED set changes the
> verdict negligibly. The playground is built to demonstrate exactly this.

## 5. Colour & verdict details

- **Swatch:** `spectrumToColor` renders at fixed lightness 0.20, so the swatch shows **chromaticity/hue**,
  not brightness — appropriate, since concentration/path (not quality) drives lightness.
- **Discriminator = hue** (robust: the swatch fixes lightness, so sample amount/path doesn't sway the
  verdict). Anchor "perfect green" ≈ **hue 80°**.
- **Caveat on the legacy palette** `unsorted/oilScores.svg` (`#669900` excellent → `#446600` good →
  `#223300` bad): those three are **hue-degenerate — all hue ≈ 80°**, differing only in **lightness**
  (0.30/0.20/0.10). I.e. that viz encoded quality as *darkness* (and came from the *abandoned* LDA
  classifier), **not** the green→brown *hue* rotation this pipeline uses. Use it as a stylised display
  anchor; **do not** seed hue thresholds from it.
- **Verdict bands are plugin-owned constants** (per the workflow model — the plugin is the source of
  truth; no `referenceData()` hook). Shape: `hue < lo → BROWN/over-roasted; hue > hi → UNDER; inside →
  GREEN, and ≈ perfect-green → PERFECT`.
- **`EvaluationResult`** carries view-models: `ColorSwatch(measured)`, `ColorSample(perfect green)`,
  `Label(hue/L/S)`, `Verdict`.

## 6. Correction of prior wording

`SPECTRAL_WORKFLOW_CONCEPT.md` §4 and `spectrasTest.py` describe converting "the absorption spectrum" to
colour. **That is corrected here:** colour comes from the **transmission `T`** (the legacy `.dx` that
"worked" must have been a transmission/reflectance curve, not true absorbance — colouring real absorbance
yields the complement). `A` remains the right object for *peak/analysis* and the absorption *plot*, and
for any future feature work — but **not** for the swatch.

## 7. Mapping to the workflow object model

| Concept step | Phase · step (settled model) | Operation |
|---|---|---|
| measure R, S (frames) | ACQUISITION · reference / sample steps | (capture) → `MeanOp` |
| condition | PROCESSING | smooth/removeBaseline/rebin/normalize |
| `T = S/R` | PROCESSING | `TransmissionOp` |
| `A = −log10(T)` | PROCESSING (plot) | `AbsorptionOp` |
| colour(T), hue, verdict | EVALUATION · step (with view) | `SpectralColorUtil.spectrumToColor` + `VerdictOp` |

`SpectraContainer` lineage: `C0{reference}`,`C0'{sample}` → `C1{reference,sample}` (mean+conditioned) →
`C2{transmission}` → `C3{absorption}` → `EvaluationResult`.

## 8. Open / deferred

- **Numeric verdict thresholds** (`lo`, `hi`, perfect-green hue, tolerance) need **real, provenance-known**
  measurements to calibrate — the local `spectracs-evaluations` spectra are **not trustworthy** for this
  (unknown capture). Deferred until controlled captures exist. **For a demo**, derive provisional bands
  from the **synthetic presets' own achieved hues** (playground §8) — self-consistent, not from the
  hue-degenerate `oilScores.svg` palette. **Quality is perfect-centred** (target ≈ 80°; too-green =
  under-roasted, too-brown = over-roasted), per the band sketch in §5 — not monotonic in hue.
- **Absorbance vs absorptance:** use **`A = −log10(T)`** (Beer–Lambert standard) for the absorption plot;
  the legacy Julia prototype used `1 − S/R` (bounded). Colour is unaffected (it uses `T`).
- **Lightness/saturation** are currently informational; whether they carry quality signal (beyond hue) is
  an open research question — revisit with real data.

## Sources
`KB_spectroscopy_physics.md`, `KB_led_and_oil_spectra.md`, `SPEC_spectrum_processing.md` (implemented
colour math), `spectracs-docs/SPECTRAL_WORKFLOW_CONCEPT.md` (object model). Fruhwirth & Hermetter (2007),
*Seeds and oil of the Styrian oil pumpkin*, Eur. J. Lipid Sci. Technol. **109**(11):1128–1140, DOI
[10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105) — dichromatism via Beer–Lambert + CMFs;
reference record in `spectracs-references/articles/`.
