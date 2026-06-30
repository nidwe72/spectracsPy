# KB — Spectroscopy physics (the model behind the pipeline)

The physics the Spectracs pipeline implements, written so the playground/plugin code and this doc share
one mental model. Companion: `KB_led_and_oil_spectra.md` (LED + oil specifics, sources),
`KB_spectrum_libraries.md` (libs), `SPEC_spectrum_processing.md` (the implemented colour math).
Reference data: `../../spectracs-references/` + `../../spectracs-evaluations/` (both non-versioned).

---

## 1. The measurement chain

```
LED light source ──▶ cuvette (blank=REFERENCE | oil=SAMPLE) ──▶ grating/disperser ──▶ camera image
                                                                                         │
                                              calibration (ROI + pixel→nm polynomial)  ──┘
                                                                                         ▼
                                                            Spectrum: { nm → intensity (0–255) }
```

- **Light source** = a set of **Avonec 3 W LEDs** (warm-white continuum + colour peaks) → a broadband,
  daylight-like SPD with shallow dips (not gaps). See `KB_led_and_oil_spectra.md`.
- **Dispersion → image:** the grating spreads wavelengths across the sensor's x-axis; each pixel column
  ≈ one wavelength, its grayscale = intensity at that wavelength.
- **Calibration** (master step) sets the **ROI** (which rows/cols are the spectrum) and the
  **pixel→nm polynomial** (cubic `poly1d`). Acquisition samples a ROI row, maps each column x→nm via the
  polynomial, reads `gray = qGray(pixel)` → `Spectrum.valuesByNanometers[nm] = gray`.
- **Units caveat:** intensities are **8-bit grayscale (0–255), arbitrary units** — not radiometric.
  Ratios (transmission) and shape (colour) are meaningful; absolute values are not.

## 2. Reference, sample, transmission, absorption — four distinct spectra

```
R(λ)  REFERENCE     = light through the blank (isopropanol)        ≈ the LED SPD
S(λ)  SAMPLE        = light through the oil = R(λ)·T(λ)            (what the camera sees)
T(λ)  transmittance = S/R                                          (fraction passed, 0..1)
A(λ)  absorbance    = −log10(T) = −log10(S/R)                      (Beer–Lambert, unbounded ≥0)
```

**Beer–Lambert:** `A(λ) = ε(λ)·c·l` — absorbance scales linearly with **concentration c × path length l**.
So `T = 10^(−ε c l)` and `S = R·10^(−ε c l)`. The `c·l` product is a single physical knob (see §4).

> **Two absorption conventions exist in this project — pick deliberately:**
> - **absorbance** `A = −log10(S/R)` (Beer–Lambert; the concept doc, our pipeline plan).
> - **absorptance** `1 − S/R` (bounded 0..1; the prior Julia prototype `oils.jl`).
> They agree for small absorption and diverge for strong; absorbance is the physically standard one.

## 3. Spectrum → colour

Implemented in `SpectralColorUtil.spectrumToColor` (`SPEC_spectrum_processing.md` §4). Pipeline:
```
SPD (rebinned 380–780 @1nm, normalized)
  → CIE XYZ   (sd_to_XYZ, CIE-1931 2° CMFs, D65 illuminant, Integration)
  → xy        (XYZ_to_xy)
  → RGB       (xy_to_rgb, clamped)
  → HLS       (colorsys.rgb_to_hls)  →  hue (0–360), lightness, saturation
  → swatch QColor at FIXED lightness 0.20 (so only chromaticity/hue is shown)
```
**Hue is the green↔brown/red discriminator.** Validation anchors: peak ~550 nm → ~66°, ~450 → ~259°,
~620 → ~18°. **Colour the TRANSMISSION** `T` (not raw `S`, not the absorbance): the oil looks green
because it *transmits* green; colouring the absorbance would give the complement, and colouring raw `S`
double-counts the LED light (see §3.1).

### 3.1 Reference-normalisation = stability (the core of a sound concept)
Always judge from the **reference-normalised** spectrum, never from the raw oil measurement:
- `S(λ) = R(λ)·T(λ)` is **illuminant-dependent** — change an LED and the derived colour/hue shifts for the
  *same* oil. Unstable.
- `T = S/R` **cancels the LED SPD** (Beer–Lambert; this is why a spectrophotometer always measures a
  blank and reports %T). The colour is then computed under a **fixed D65** in the CIE step →
  **LED-independent and stable in the mean**.
- **Stability under an LED swap (still gap-free):** `T`/`A` don't move in expectation; only **noise**
  changes — relative noise in `T(λ) ≈ noise/R(λ)`, so it grows where `R` is low and is *undefined at a
  true gap* (`R≈0`). The hue is a CMF-weighted **integral over all λ**, so it averages local noise out.
- **Design rule:** choose LEDs so `R` stays strong across the diagnostic bands — green window 520–560,
  red 630–670, blue 430–480 — then the verdict barely moves when LEDs are swapped/aged.

## 4. Why pumpkin oil is green-or-brown (the QM)

Styrian pumpkin-seed oil is **dichromatic**: green in a thin layer, red/brown in a thick one. Fruhwirth &
Hermetter (2007) explain it with exactly **Beer–Lambert + CIE CMFs** — i.e. §2–§3 here.

- Pigments give a **green transmission window ~520–560 nm**, between blue absorption
  (chlorophyll Soret ~430 nm + carotenoid/lutein ~440–480) and red absorption (chlorophyll Q ~660–670),
  with deep-red transmission >670.
- As **c·l rises**, the narrow green window is overwhelmed and deep-red dominates → perceived colour
  rotates **green → red**. Roasting adds **Maillard browning** (broad short-λ absorption) → toward brown.
- **Quality axis:** fresh/well-roasted → green; over-roasted/old → brown/dark. Conceptual verdict palette
  (from `unsorted/oilScores.svg`): **`#669900` excellent → `#446600` good → `#223300` bad** (note: that
  prior viz came from an LDA *classifier*, now abandoned — "oil spectra have no discriminating peaks";
  the current approach is spectrum→hue, but the palette is a useful target-colour anchor).

## 5. Synthesising spectra (the playground / virtual device)

- **REFERENCE** `R(λ)` = Σ LED SPDs (measured Avonec curves, or skewed-Gaussian per peak+FWHM); luxpy can
  build/mix these. This is the synthetic illuminant.
- **SAMPLE** `S(λ) = R(λ)·10^(−A_oil(λ)·c·l)`, with `A_oil` = pigment bands (chlorophyll 430/665,
  carotenoid 440–480) + browning slope. `c·l` is the green→brown knob; presets = points on the curve.
- **Calibration honoured:** rasterise the synthetic SPD onto the ROI as a grayscale strip via the
  **pixel→nm polynomial**, store as the virtual device's REFERENCE/SAMPLE image, and let the *existing*
  acquisition read it back — so ROI + calibration are genuinely exercised (and Roadmap #5's three image
  slots get filled).
- **Inverse (colour→spectrum) is ill-posed** (metamerism) — we forward-model, never invert. Fallbacks in
  `KB_led_and_oil_spectra.md` §3 if a display-side reconstruction is ever needed.

## 6. Map to pipeline operations (reusable, plugin-SDK-shaped)

| Physics | Operation (SpectraContainer → SpectraContainer) | Status |
|---|---|---|
| build `R` from LEDs | `LedReferenceSynthesisOp` | greenfield (luxpy / measured curves) |
| build `S` from `R`+oil | `OilSampleSynthesisOp` | greenfield |
| frame averaging | `MeanOp` (`SpectrumUtil.mean`) | implemented |
| denoise / baseline / rebin / normalize | smooth/removeBaseline/rebin/normalize | implemented |
| `A = −log10(S/R)` (or `1−S/R`) | `AbsorptionOp` | greenfield |
| `T = S/R` for colour | (transmission for the swatch) | greenfield |
| `colour = f(T)` | `SpectralColorUtil.spectrumToColor` | implemented |
| hue → verdict band | `VerdictOp` / plugin constants | greenfield |

## Sources
- `KB_led_and_oil_spectra.md` (LED + oil sources). Fruhwirth & Hermetter (2007), ResearchGate 227762370.
- Implemented colour math: `SPEC_spectrum_processing.md`. Prior absorptance prototype: `unsorted/oils.jl`.
- Real measured spectra: `../../spectracs-evaluations/` (`.dx`/`.sgd`, incl. `light_*` references + `*abs*`).
