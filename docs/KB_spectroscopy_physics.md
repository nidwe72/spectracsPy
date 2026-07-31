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

## 7. Physical instrument construction (hardware)

The Spectracs device is a **hand-held DIY spectrometer optically coupled to a USB camera**: the
diffraction/grating unit is mounted in front of (attached to) the **camera's lens**, so the optical system
is *grating-block + camera-lens + sensor* as one stack. Consequences for the rest of the system:

- **Camera hardware:** a small, known set of USB (UVC) cameras — **Microdia/Sonix `0c45:6366`** (the cheap
  Chinese cam intended for the **production batch**) and **ELP `32e4:8830`** (more expensive; the current
  bench/dev unit). See `SPEC_real_camera_capture.md` §4.
- **Resolution is an *optical* question, not just a data one:** because the grating sits on the lens, the
  "best" capture resolution is whatever makes *this optical stack* resolve the spectrum best — it must be
  **judged empirically against a known line source (the CFL lamp)**, then hardcoded per chipset. Higher
  sensor resolution does not automatically mean better spectral resolution once the lens/grating optics
  are the limiting factor. (`SPEC_real_camera_capture.md` §9.2.)
  - **Verified best-resolution per camera (human-judged → hardcoded).** The workflow: a human switches
    capture modes live in the **"Capture images" dev view** (`SPEC_dev_capture_view.md`), inspects the CFL
    mercury lines, and records the sharpest mode here; that recorded value then becomes the hardcoded
    per-chipset capture resolution in the app (`SpectrometerSensorSettings`, `SPEC_real_camera_capture.md`
    §4). This table is the source of truth for the finding + rationale; the code holds the value.

    | Camera / chipset | VID:PID | Best resolution (CFL-verified) | Notes |
    |---|---|---|---|
    | **ELP** | `32e4:8830` | *TBD (observed native 1600×1200; snaps 1920×1080→1600×1200)* | bench/dev unit; sharp CFL lines confirmed at this mode, formal best-mode judgement pending |
    | **Microdia / Sonix** | `0c45:6366` | *TBD* | production-batch cam; not yet judged |
- **Two light sources, two jobs** (drives the future best-fit-exposure work, §9.3 of that spec):
  - **CFL bulb** — the **calibration** source. Mercury emission **lines** (≈436 nm blue, 546 nm green,
    577/579 nm yellow, 611 nm orange) at known wavelengths → drives the pixel→nm wavelength calibration.
    A real capture of this on the ELP is verified (sharp vertical emission lines).
  - **Array of 7 × 3 W LEDs** — the **measurement** source (broadband, illuminates the sample). This is
    the "LED light source" in §1's chain.
  - **Exposure is per-camera AND per-light-source.** Measured on the ELP (2026-07-07): the old fixed
    exposure 150 **over-exposed** the CFL capture — clipping blue+green and merging the whole red cluster
    into one saturated blob — while **~78** keeps the brightest line (green ~546) unclipped and resolves
    8 bands. So each camera needs a **CFL-calibration exposure** (ELP=78, seeded in
    `SpectrometerSensorUtil`) *and* a separate **LED-measurement exposure** (brighter broadband source,
    TBD). Even perfectly exposed, the mercury green **doublet is only marginally resolved** (shoulder +
    peak, ~14 px, shallow valley) — the optical/slit limit, not exposure (§9.2). The right value also
    drifts with lamp brightness/distance → motivates auto-exposure (`SPEC_real_camera_capture.md` §9.3).
- **Per-unit identity:** each produced spectrometer carries a **printed serial label** used as the key to
  its factory calibration profile (`SpectrometerProfile.serial`) — the USB cameras themselves expose no
  serial. (`SPEC_real_camera_capture.md` §9.1.)
- **External physical-hardware reference — comparable DIY spectroscope.** Review of a simple AliExpress
  hand-held spectroscope: <https://star-hunter.ru/en/simple-spectroscope-review-aliexpress/> — a low-cost
  grating-based visual spectroscope in the same class as the Spectracs optical stack. Useful reference for
  the optical layout and what to expect from a cheap grating + lens build.

## 8. The sample: solvent chemistry, turbidity and the vessel

*Added 2026-07-31 after the solvent investigation. Everything here is about what happens **before** the light
reaches the grating — and it turns out to dominate the error budget more than anything downstream of it.*

### 8.1 Why a solvent at all

Neat pumpkin oil is effectively opaque across the pigment bands at any sane path length. Diluting into a
transparent solvent brings the absorbance into the instrument's usable range (`A ≈ 0.1–1.2`) without needing a
micrometre cuvette. The solvent is therefore part of the measurement, not a convenience.

### 8.2 Oil + isopropanol is NOT a solution — it is a metastable dispersion

Pumpkin oil is a **nonpolar triacylglycerol**; isopropanol is *semi-polar* — a polar –OH on a small nonpolar
isopropyl group. The two are only **partially miscible**: the system has an **upper critical solution
temperature (UCST)**, and below it there is a **miscibility gap** where oil and solvent separate into two
phases. Solubility rises with temperature until the critical point, above which they mix in all proportions —
and **water content raises that critical temperature steeply**, so an aged, hygroscopic bottle of "99 %" IPA is
a worse solvent than a fresh one.

A few drops in a few millilitres therefore **exceeds solubility**, and what forms is a cloudy dispersion:

- **oil nanodroplets** thrown out by rapid dilution from a marginal solvent — the **ouzo effect**, which then
  coarsen by **Ostwald ripening** and **coalescence** (no surfactant to stabilise them);
- **micro-particulate** that was never soluble at all — waxes, phospholipids, seed sediment.

The **pigment itself does dissolve** (protochlorophyll/pheophytin are moderately polar tetrapyrroles) — that is
the real absorbance signal. The suspended material is a separate, unwanted optical population.

**It sediments, it does not cream.** Oil ρ ≈ 0.92 g/mL against IPA ρ ≈ 0.785 — the droplets are *denser* than the
solvent and fall. Stokes' law makes the rate go as the **square of the radius**, so a fresh fine dispersion is
kinetically stable for a while and then clears faster and faster as the droplets coarsen.

### 8.3 The pedestal — why turbidity is worse than it sounds

Scattered light never reaches the detector, so **the instrument records it as absorbance**. For particles at or
above the wavelength the loss is broad and smooth in λ, so it lifts the entire curve off zero. We call that
additive floor the **pedestal**, `c`.

It is not a small correction. Measured on real fills, `c` runs **0.7–1.9 × the pigment signal in the Q band** —
**the plinth is bigger than the thing standing on it.**

And it is specifically corrosive to a **ratio**, because adding the same `c` to numerator and denominator drags
any ratio toward 1:

```
true       12.37 / 1.00                    = 12.37
measured  (12.37 + 1.59) / (1.00 + 1.59)   =  5.39
```

The pigment did not change. The pedestal compressed the reading by more than half. This is the entire difference
between the raw and baseline-corrected pigment ratios the plugin emits, and it is why a baseline correction
exists at all.

**Corollary, measured:** clearing the sample is worth roughly **6× in discriminating power** — oils that had
three years to clarify in the bottle carried **half** the pedestal and separated **8× better**
(`SPEC_capability_proof.md` §11.4e). **Sample clarity is a first-class instrument parameter, not housekeeping.**

### 8.4 Choosing a solvent — polarity and solvency are different axes

The key insight, and it is not obvious: **how well a solvent dissolves oil is not the same as how polar it is.**
Solvency for a triglyceride tracks the **alkyl chain length**; solvatochromic band shifts track the
**dielectric constant**. They can be varied almost independently.

| solvent | ε (25 °C) | ρ g/mL | b.p. °C | flash °C | dissolves oil | polystyrene | field-usable |
|---|---|---|---|---|---|---|---|
| **2-propanol** *(current)* | **17.9** | 0.786 | 82.6 | 12 | **marginal** — the gap above | ✅ safe | ✅ drugstore |
| 1-propanol | 20.1 | 0.803 | 97.2 | 22 | better (linear chain) | ✅ safe | ~ supplier |
| **1-butanol** | **17.8** | 0.810 | 117.7 | 35 | **good** | ✅ safe *(soak-test for crazing)* | ~ supplier |
| n-heptane | 1.92 | 0.684 | 98.4 | **−4** | ideal | ⛔ **dissolves it** | ⛔ H225/H304/H411 |
| cyclohexane / isooctane | ~2 | — | — | — | ideal *(the AOCS/IUPAC choice)* | ⛔ | ⛔ |

**Why 1-butanol is the interesting one:** `ε = 17.8` against isopropanol's `17.9` — **essentially identical
polarity, so band positions should barely shift** — while its longer alkyl chain makes it a genuinely good
triglyceride solvent. You get the dissolution without the solvatochromism. Heptane (`ε = 1.9`) would move the
bands hard, on top of dissolving the jar.

⚠ **The literature does not use neat isopropanol for oil pigments.** The standard methods read chlorophyll and
carotenoids in **cyclohexane** (445/470 nm), **hexane** (442/668 nm), **CCl₄**, or **ethanol + isooctane /
ethanol + heptane**. The field converged on hydrocarbons precisely because they give a true solution. Our choice
of IPA is a *field-usability* compromise, and §8.3 is the price we pay for it.

**And the community's answer to turbidity is CLARIFY, not WAIT.** Guidance to "measure within ~10 min" belongs
to nephelometry, where the particles *are* the analyte; the "10–15 min equilibration" boilerplate is thermal
equilibration and colour development. Neither is our case. Where particles are the *interferent*, the standard
practice is filtration or centrifugation before the cuvette, plus a fitted baseline for the residual.

### 8.5 The vessel

**Polystyrene is safe with alcohols and destroyed by hydrocarbons.** Alcohols are essentially the *only*
PS-compatible organic family, so the jar and the solvent are a coupled choice: stay on alcohols and the cheap
transparent cosmetic jar keeps working; move to heptane and the vessel must be replaced.

*(Even with alcohols, soak-test a spare jar overnight — injection-moulded PS carries frozen-in stress and
alcohols craze stressed PS even when the compatibility chart says "good".)*

**The awkward constraint is that light passes through the jar AND the lid**, so both must be transparent — and a
clear vessel with a matching clear lid is not an off-the-shelf glass item. The workable answer is a **milled
glass lid carrying a clamped FEP film window**: fluorinated ethylene propylene transmits **> 95 % across
400–700 nm** with **< 2 % haze** at 100–200 µm and is chemically immune to everything under discussion. Clamp it,
never glue it — its non-stick nature is the same property that makes it solvent-proof.

**Refractive indices matter here.** FEP `n ≈ 1.344` sits very close to isopropanol `1.377` and heptane `1.387`.
If the film is allowed to **contact the liquid**, that interface reflects ~0.015 % instead of the ~2.5 % of a
liquid–air surface — **and the meniscus disappears**, removing a curved surface whose shape varies with fill
level and tilt. Polystyrene (`n = 1.59`) is a poorer match than borosilicate (`1.47`).

### 8.6 What this means for the instrument

1. **Sample clarity belongs in the error budget**, next to seating and lamp drift. It is currently the largest
   single lever we know of and the cheapest to pull.
2. **A fresh dilution is not stable.** It drifts for ~15 min after mixing and continues, non-monotonically, for
   hours (`SPEC_capture_quality.md` §16.12, `SPEC_capability_proof.md` §11.4a–e).
3. **The solvent is a product decision, not only a chemical one.** Whatever we ship, a miller has to buy, store
   and handle it — which is why heptane is a bench-only reference method however good its chemistry is.
4. **Every transfer out of a dispersion is a sampling step.** If the batch is mixed in one vessel and an aliquot
   is measured in another, the particulate load that travels with the aliquot depends on *when* and *from what
   depth* it was drawn — the dispersion is sedimenting the whole time. Homogenise before drawing (a stirrer) or
   clarify after (a filter); doing neither leaves a large, invisible, sample-to-sample variable.
   (`SPEC_capability_proof.md` §11.4f B2.)

**Sources.** JAOCS, Rao & Arnold 1957, *Alcoholic extraction of vegetable oils IV — solubilities in aqueous
2-propanol*, [10.1007/BF02637892](https://doi.org/10.1007/BF02637892) · the ouzo effect and its nanodroplet
nucleation, [ACS Cent. Sci. 2023](https://pubs.acs.org/doi/full/10.1021/acscentsci.2c01194) · spectrophotometric
pigment methods, [Chem. Papers](https://link.springer.com/article/10.2478/s11696-013-0502-x) · FEP optical and
chemical data, [AdTech transmission tables](https://adtech.co.uk/technical-data/fep-uv-transmission-data/).

## Sources
- `KB_led_and_oil_spectra.md` (LED + oil sources). Fruhwirth & Hermetter (2007), *Seeds and oil of the
  Styrian oil pumpkin*, Eur. J. Lipid Sci. Technol. **109**(11):1128–1140, DOI
  [10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105) — record in
  `spectracs-references/articles/`.
- Implemented colour math: `SPEC_spectrum_processing.md`. Prior absorptance prototype: `unsorted/oils.jl`.
- Real measured spectra: `../../spectracs-evaluations/` (`.dx`/`.sgd`, incl. `light_*` references + `*abs*`).
