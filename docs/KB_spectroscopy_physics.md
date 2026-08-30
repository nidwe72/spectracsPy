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
  **red 600–660** (the protochlorophyll Qy sits at ~623–626, §4.1 — this said "630–670" until 2026-07-31),
  blue 430–480 — then the verdict barely moves when LEDs are swapped/aged.

## 4. Why pumpkin oil is green-or-brown (the QM)

Styrian pumpkin-seed oil is **dichromatic**: green in a thin layer, red/brown in a thick one. Fruhwirth &
Hermetter (2007) explain it with exactly **Beer–Lambert + CIE CMFs** — i.e. §2–§3 here.

- Pigments give a **green transmission window ~520–560 nm**, between blue absorption
  (**protochlorophyll Soret ~432 nm** + carotenoid/lutein ~440–480) and red absorption
  (**protochlorophyll Qy ~623–626 nm**), with deep-red transmission beyond ~660 nm.
  *(⚠ read §4.1 — this bullet said "chlorophyll … Q ~660–670 … >670" until 2026-07-31, which is a
  different molecule and ~40 nm out.)*
- As **c·l rises**, the narrow green window is overwhelmed and deep-red dominates → perceived colour
  rotates **green → red**. Roasting adds **Maillard browning** (broad short-λ absorption) → toward brown.
- **Quality axis:** fresh/well-roasted → green; over-roasted/old → brown/dark. Conceptual verdict palette
  (from `unsorted/oilScores.svg`): **`#669900` excellent → `#446600` good → `#223300` bad** (note: that
  prior viz came from an LDA *classifier*, now abandoned — "oil spectra have no discriminating peaks";
  the current approach is spectrum→hue, but the palette is a useful target-colour anchor).

### 4.1 ⚠ CORRECTION — the pigment is PROTOchlorophyll, and its red band is at ~625 nm, not ~665 *(2026-07-31, sourced)*

**Everything above and in several other documents said "chlorophyll" with a Q maximum near 660–670 nm. That
is the wrong molecule and the wrong number.** The error is inherited: chlorophyll *a* is the textbook
default, and nobody checked it against the pumpkin-specific literature we already had on disk.

**What the pigment actually is.** Fruhwirth & Hermetter (2007) — the paper this whole section is built on —
say it explicitly: the oil's colour and fluorescence are due to *"various tetrapyrrol-type compounds like
**protochlorophyll (a and b)** and **protopheophytin (a and b)**, the latter being a protochlorophyll
lacking the magnesium ion"*. Protochlorophyll is **not** chlorophyll: it lacks the ring-D reduction, so it
is a **porphyrin**, where chlorophyll is a **chlorin**. That single structural difference is exactly what
sets the red band's position.

**Diagrams.** Two vector figures explain the structural and group-theoretical points, in
`DOC_sample_physics.md` §3.1–3.2 (→ *Light, Pigment and Solvent* PDF); sources
`docs/figures/pigment_macrocycle.svg` and `pigment_qband_symmetry.svg`, regenerated by
`docs/tools/build_pigment_figures.py`.

**Where its red band sits.**

| | Soret | red (Qy) band | fluorescence |
|---|---|---|---|
| chlorophyll *a* *(the wrong molecule)* | ≈ 430 nm | ≈ 662–665 nm | ≈ 668–675 nm |
| **protochlorophyll(ide) *a*** *(ours)* | **≈ 432–440 nm** | **≈ 623 nm (80 % acetone) / 626 nm (methanol)** | **≈ 630–636 nm** |

**Three independent confirmations, all consistent:**

1. **The paper's own figure.** `KB_led_and_oil_spectra.md` §2 read Fig. 3A off the published plot years ago
   and recorded *"Q-band 2 — **~630 nm** — weak Q-band (near the 635 nm fluorescence)"*. Our own notes had
   the right number all along; the prose around them did not.
2. **The paper's fluorescence.** Fruhwirth & Hermetter measure the oil's emission maximum at **635 nm** in
   methanol. A Stokes shift of ~10 nm puts the absorbing transition at **~625 nm** — right on the
   protochlorophyllide value, and ~30 nm away from anything chlorophyll *a* could produce.
3. **The independent pigment literature.** Protochlorophyll in pumpkin seed *oil* is reported emitting at
   **630 and 655 nm**, against 700 nm in the intact seed; and pumpkin seed pigments are identified as
   2,4-divinyl-protochlorophyll *a*, 2,4-divinyl-protopheophytin *a* and 2-vinyl-protopheophytin *a*, with
   protopheophytins making up **1.1–35.5 %** of the protochlorophylls as a storage-degradation product.

**⇒ The consequence, and it is not cosmetic.** Our capture window is 440–630 nm. If the red band were at
665 nm it would lie **outside** the window and 600–630 would be its distant flank. At ~625 nm the band lies
**at the very edge of — arguably just inside — the window**, and the 600–630 anchor sits on its **rising
edge, or on the band itself**. That reframes three things:

- §16.12.12's "the far anchor carries pigment" finding is **strengthened**, not weakened — it is nearer the
  band than anyone thought.
- `SPEC_capture_quality.md` §16.12.14a / §16.12.16 argue the escape from a peak-free window is *"spectral
  coverage past ~700 nm"*. If Qy is at ~625, the genuinely quiet region begins **much earlier (~660 nm+)**,
  so widening the window is a considerably cheaper fix than recorded. **This should be re-costed.**
- The comparison note in `spectracs-references/comparisons/fig3A_vs_spectracs/` lists *"the missing ~630 nm
  band"* as an open discrepancy. It is not a discrepancy — it is the Qy band, and we are **clipping it**.

**The chemistry of the green→brown axis, restated correctly.** Roasting and ageing strip the central Mg²⁺
from protochlorophyll, giving **protopheophytin** (the paper's own definition). Demetallation of a
tetrapyrrole lowers the symmetry from effectively four-fold to two-fold: the Soret weakens and blue-shifts,
and the red-region bands gain structure and change intensity. So the quantity our metric is ultimately
tracking is the **protopheophytin : protochlorophyll ratio** — which the pigment literature says varies
from 1 % to 36 % with storage alone. That is a real, chemically-grounded quality axis.

⚠ **Still inference, and labelled as such:** that our measured 600–630 rise *is* this band's edge is a
well-supported interpretation, not a measurement. We cannot see 625 nm cleanly — it sits where the lamp is
fading and at the clamp boundary. What is *measured* is the 5.1 σ green/brown difference in that rise
(§16.12.12). The correction above raises the prior on the interpretation considerably; it does not close it.
**The clean test is to widen the capture window and look**, which §16.12.16 should now re-cost.

⚠ **No code changes from this.** `665` appears only in comments and docstrings
(`DevSpectralPlugin`, `far_anchor_probe.py`, `far_anchor_sweep.py`) — never in a computation. The
synthesis models in §5 below, `KB_led_and_oil_spectra.md` and `SPEC_pipeline_playground.md` do carry the
wrong band position and **should be corrected before the virtual device is used for anything quantitative**.

#### ⭐⭐ 4.1a The three band centres, and why our windows are NOT on them *(Edwin 2026-08-06)*

| feature | centre | our measurement window | |
|---|---|---|---|
| **Soret** | **~432 nm** | 448–460 nm | ⚠ **16–28 nm above the peak — we measure the flank** |
| **Q band** | ⛔ ~~~574 nm~~ → **~568 nm** | 560–580 nm | ⚠ contains it — but see the correction below |
| **Qy** | **~623–626 nm** | 620–630 nm | ⚠ contains it — but that window is used as a **baseline anchor** |

> ⛔⛔ **CORRECTION 2026-08-21 — the Q band is at ~568 nm, and the "≈ 574" was an INSTRUMENT ARTIFACT.**
> `DOC_lamp_rebuild.md` §6 records a Bayer channel crossover at ~583 nm; the reference throughput falls to a
> **minimum at 581 nm and then jumps +17 %/nm**, identically in every run ever taken. The apparent maximum
> near 574–580 is the ramp into it, not a band. ⭐ In white spirit — where the real band grows large enough
> to beat the artifact — the maximum lands at **567.2, 567.5, 567.8 and 567.8 nm** on four independent
> fills, and `Pigment D_Q` finds an interior peak in 100 % of them against **7 %** of 110 isopropanol runs.
> ⚠ §3.6 "resolves the peak at ≈ 574" on isopropanol data and is subject to the same artifact; it should be
> re-read before being quoted. `SPEC_capture_quality.md` §16.12.7f and `DOC_lamp_rebuild.md` §6.1.
>
> ⚠ The **Qy at ~623–626 nm is UNAFFECTED and now confirmed a fourth time**: the same four white-spirit
> fills put its maximum at **622.8–625.0 nm**, inside §4.1's literature range (623 nm in 80 % acetone /
> 626 nm in methanol), from an instrument that was not looking for it.

⇒ **The windows were chosen by where the instrument had light and dynamic range, not by where the chemistry
is.** That is `SPEC_metric_research.md` §7.8's wall — *"both principal bands are flanks"* — stated from the
molecule's side rather than the metric's. ⚠ It also means "extend the red range" (§9.1 item 5) is only half
the fix: the other half is **enough light at 432–440 to sit on the Soret peak instead of its flank**.

⚠ At 432 nm the oil is nearly opaque at today's recipe — which is what made 440–447 dead bins (§7.13). But
that cuts both ways: **those bins are as much a source-brightness problem as an absorbance one.**

⭐ **A curiosity with practical value — the CFL's lines land almost exactly on all three:**

| pigment feature | CFL line | gap |
|---|---|---|
| Soret ~432 | **Hg 435.83** | 4 nm |
| Q ~574–580 | **Hg 576.96 / 579.07** | ~0 |
| Qy ~623–626 | **Eu³⁺ 626.6** | ~2 nm |

Not coincidence in the deep sense — mercury and europium emit where porphyrin rings absorb, both being
consequences of similar energy scales in the visible.

⛔ **But the CFL cannot be the measurement lamp.** Measured on the rig it gives **9 DN across 448–460 at
exposure 500** (the `EXPOSURE_MAX` cap, empty beam) against the Sansi's 212 DN at exposure 32 — **~17× dimmer
per unit exposure**. Its lines are bright relative to its own continuum, not absolutely. ⇒ It stays the
**wavelength standard** (§7), and the three-line coincidence is useful for a different reason: it makes the CFL
a natural check that the calibration still puts the pigment's features where they belong.

### ⭐⭐ 4.2 Who else lives in the blue window — and why `A_S` is a load reference, not a pigment band *(2026-08-10)*

The metric's numerator reads **448–460 nm**. That window is *not* the pigment's, and treating it as such
mis-describes what `M448` computes (`DOC_metric_algebra.md` §5.6a).

**The tenants, in order of how much of the window they own:**

| absorber | where it absorbs | does it care about roast? |
|---|---|---|
| **carotenoids** — lutein predominant | ~420–490 nm, three-finger vibronic structure (lutein ≈ 422 sh / 445 / 474; β-carotene ≈ 425 sh / 450 / 478, +5–10 nm in oil) | degraded by heat, but blind to the *pigment's* metal |
| **Maillard / browning products** | broad, rising monotonically toward the blue | created by roasting |
| **turbidity / scatter** | broad, rising toward the blue | no |
| **protochlorophyll Soret flank** | the red flank of a band at ~432 nm | ⭐ yes — but a **minority** of the window |

⭐ **Composition, from the source paper.** Fruhwirth & Hermetter (2007) §3.2: *"The predominant carotene found
in Styrian pumpkin seed oil was **lutein (71 %)** followed by **β-carotene (12 %)** and **cryptoxanthin β
(5.3 %)"*. ⚠ The paper gives **no protopheophytin concentration** and no carotenoid-to-tetrapyrrole ratio —
the "minority tenant" statement below is *our own measurement*, not a literature value.

**Why we know the pigment is the minority.** Our window sits 16–28 nm **above** the Soret peak, on the falling
flank, and demetallation blue-shifts that peak. If the window were the pigment's band, a conversion would cost
it **53–87 %** (Gaussian, FWHM 42–70 nm) — even a 10 nm shift costs 26–56 %. Measured across four commercial
oils spanning 1.5× in `M448`, `A_S` moves **±5 % with no ordering**, and the brownest reads *highest*.

**Three effects, two directions, hence flat:**

```
   roasting →   pigment Soret shifts out of the window   ↓
                carotenoids degrade (heat-labile)        ↓
                Maillard products accumulate             ↑
                                                     ≈ flat
```

⇒ **The blue window is a *load* reference** — it tracks how much oil is in the beam, not what state its
pigment is in — and that is precisely what makes the ratio dilution-invariant. ⇒ so the honest name for the
index is **pigment degradation per unit chromophore load, inverted**, or for a miller *"how brown the pigment
has gone, per litre of oil in the beam"*; `DOC_metric_algebra.md` §5.6b carries the four audience versions.
⛔ Never "chlorophyll content" — that is what it is not. ⚠ Empirically validated and
mechanistically explained, **not** guaranteed: an oscillator-strength sum rule applies to the *integral* over
a band, and a 12 nm slice on the flank does not inherit it.

**What the windows would have to be for the sum rule to do real work** (fraction of the band's area captured,
FWHM 42 nm):

| window | band at 432 nm | at 411 nm | shift costs |
|---|---|---|---|
| 448–460 *(today)* | 12.7 % | 1.6 % | −87 % |
| 440–490 *(full clamp)* | 32.6 % | 5.2 % | −84 % |
| 405–495 *(with the violet emitter)* | 93.5 % | 63.2 % | −32 % |
| 390–500 *(ideal)* | 99.1 % | 88.0 % | −11 % |

⇒ ⭐ **a second argument for the 410–420 nm emitter** of `DOC_lamp_410_680.md` §3, independent of brightness:
with 405–495 nm the numerator stops being a flank slice and becomes most of the band. Full sum-rule
conservation would need ~390 nm, which is likely past both lamp and camera — but the **ratio of the two Soret
peaks** (protopheophytin : protochlorophyll, the quantity the pigment literature itself tracks, §4.1) is
reachable, and is the more valuable of the two.

⚠ **What we cannot see today, and why**, in case anyone proposes reading pheophytinization off 448–460: (1)
both Soret peaks lie outside the 440 nm capture clamp; (2) from **one flank**, a band that shifts and a band
that weakens are indistinguishable (`DOC_lamp_410_680.md` §8.2); (3) Maillard fills the hole back in.

⭐ **The literature already endorses the axis, if not the window.** Fruhwirth & Hermetter §3.5: *"When pumpkin
seed oil deteriorates, e.g. under the influence of sunlight and oxidation, the intense green pigments are
destroyed… **This disappearance of the green pigments is used as a criterion for rapid and simple optical
quality control of pumpkin seed oils**."*

## 5. Synthesising spectra (the playground / virtual device)

- **REFERENCE** `R(λ)` = Σ LED SPDs (measured Avonec curves, or skewed-Gaussian per peak+FWHM); luxpy can
  build/mix these. This is the synthetic illuminant.
- **SAMPLE** `S(λ) = R(λ)·10^(−A_oil(λ)·c·l)`, with `A_oil` = pigment bands (**protochlorophyll ≈432 Soret / ≈625 Qy** — see §4.1, NOT
  chlorophyll 430/665; carotenoid 440–480) + browning slope. `c·l` is the green→brown knob; presets = points on the curve.
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

### ⭐ 7.1 Source illumination geometry — the lamp's diffuser decides how evenly the SLIT is lit

*(Edwin's observation 2026-08-06, comparing four lamps at the same exposure; numbers measured off the
screenshots, so treat them as ratios rather than absolutes.)*

**The mechanism.** The slit is a tall narrow aperture, and the camera images its whole height. A lamp
made of **several discrete emitters at several positions** lights different parts of that height
differently — emitter 1 favours the top of the slit, emitter 5 the bottom. The frame then shows
**streaks running along the dispersion axis**, because each row of the slit carries its own brightness.
A **diffuser** destroys the source's positional structure before the light reaches the slit and the
streaks go away.

⚠ **What matters is the diffuser's WORKING DISTANCE, not its presence.** A diffuser sitting directly on
the LED die cannot mix emitters that are millimetres apart; it needs a gap to average over.

| lamp | construction | **variation along the slit** |
|---|---|---|
| **Yuji** | ⭐ diffuser with working distance; likely one die + a phosphor blend rather than many emitters | **1.8 %** |
| Sansi | several dies; diffuser sits on the chip with no real distance | 3.5 % |
| DIY array | 7 × 3 W discrete LEDs, no diffuser at all | **6.5 %** |
| Philips CFL | bare tube, no diffuser, strong structure along its own length | 36.5 % |

⇒ **The reference lamp must be diffuse.** This is the physical reason the Yuji is the measurement source
and the ordering above is monotone in exactly the way the mechanism predicts.

⚠ **REFINED 2026-08-06 — most of the non-uniformity is NOT what a diffuser fixes.** Splitting the along-slit
variation into a smooth trend and local structure (`SPEC_capture_quality.md` §16.26.6) gives **83–85 % smooth
GRADIENT** against only ~3 % structure. A diffuser removes *structure* — the emitter-position streaking above.
A **gradient** is geometry: lamp centring, the illumination cone, vignetting. ⇒ **Centre the lamp before buying
a diffuser**, and expect a diffuser to attack the smaller half.

⭐ **And the reason uniformity matters at all is subtler than "even light is good".** A *static* along-slit
pattern **cancels in `T = S/R`** — both captures see it, and the spatial reduction weights the rows identically.
What does not cancel is a pattern that **changes between the two bursts**, which is exactly what re-seating the
jar does by re-aiming the beam (§16.26.2). ⇒ **Uniformity buys insensitivity to beam re-aiming, not "better
light".**

⛔ **Improvised paper diffusers are rejected, measured.** White paper above the lamp removes **32–38 % of the
relative blue** and adds 28 % of the relative far red — it is a *red filter*, not a neutral scatterer — and it
transmits only ≈ **7 %** (auto-exposure 32 → 441 against a cap of 500). It bought along-slit 8.92 % → 6.87 %.
⇒ **PTFE** is the correct material: spectrally flat, no optical brighteners, 50–80 % transmission. ⚠ Test any
candidate under a **365 nm torch** — if it glows blue it carries optical brighteners, which re-emit into the
Soret window and are neither stable nor cancellable.

⛔ **A second, different non-uniformity exists and this is NOT its cause.** A fine ripple *along the
dispersion axis* measures ~8 % on the DIY array **and ~8.5 % on the Yuji** — i.e. it is the same on a
lamp with a diffuser and a smooth continuum. It is therefore **instrumental** (grating/sensor sampling,
Bayer interpolation, possibly the render path), not a property of the lamp. ⚠ Do not attribute it to the
emitters; the tempting explanation was tested and failed.

⚠ **CORRECTION (2026-08-06) — the de-spike filter is far narrower than first written here.** The stored
spectra carry **1305 bins over 440–629.8 nm = 0.146 nm/bin**, so the plugin's `MedianFilterOp(kernelSize=7)`
spans **~1.0 nm, not ~20 nm**. The 607 nm lamp line has a measured FWHM of 2.7 nm (§16.13.9) = **18 bins**,
so **the de-spike does NOT remove it**, and it removes no other real lamp feature either. Any claim that a
band "crossing a lamp line is protected by the median filter" is wrong.

**Consequences for a slit baffle ("Gegenlichtblende").**

- A baffle narrows the acceptance cone. With a **diffuse** source that costs nothing and rejects stray
  light — worth doing on the Yuji.
- ⛔ With a **structured** source (the DIY array, a bare CFL) it *selects* particular emitters and can make
  the along-slit non-uniformity **worse**.
- ⭐ **The lamp sits at the base of the lower cone, so the cone walls are themselves a stray-light path**
  (Edwin 2026-08-06). Blackening/baffling the cone interior attacks the floor at its source; this is the
  same floor that `SPEC_metric_research.md` §7.13 showed compresses the darkest absorbance band and
  injects a false intercept into the pedestal fit. ▶ Quantify it first with the stray-light gate
  (`SPEC_capture_quality.md` §16.23.6f) before machining anything.

### ⭐ 7.2 The delivered spectral range is ~400–680 nm — the lens does NOT truncate the red

*(2026-08-06. Long-standing assumption refuted: the red end was believed lost to the camera lens.)*

A CFL frame calibrated on two mercury anchors (435.83 / 546.07 nm, dispersion **0.5057 nm/px**) predicts
every other known emitter in the tube to within the fit's own drift:

| observed | predicted | known line | species |
|---|---|---|---|
| — | 404.0 nm | 404.66 | Hg |
| — | 487.4 nm | 487.7 | Tb³⁺ |
| — | 613.3 nm | 611.6 | Eu³⁺ (strong) |
| — | 628.0 nm | 626.6 | Eu³⁺ |
| ⭐ **a resolved local maximum at ~653 nm** | | **650.7** | **Eu³⁺** |

⭐ **The Eu³⁺ 650.7 nm line resolves as a genuine peak on top of the falling tail** (+25 % above a fitted
exponential continuum, ~4 nm wide). That is direct evidence of both **signal and resolution at 650 nm**,
not an extrapolation. Measurable response continues to ~680 nm.

⚠ **But the roll-off is steep: the red channel falls ~40× between 631 and 657 nm** (IR-cut filter +
sensor QE + the source's own decline — one lamp cannot separate the three). So the 640–670 nm region
arrives at roughly **7–13 %** of the level at 630 nm.

⇒ **Two conclusions that must travel together.** (1) The **440–630 nm capture clamp is our software
choice, not a hardware limit** — which moves `SPEC_metric_research.md` §9.1 item 5 ("extend the red range
to ~660 nm", the structural fix for both-bands-are-flanks) from *hardware, cost unknown* toward a
calibration change. (2) ⛔ **Do not simply move the clamp.** At 7–13 % of the 630 nm level those bins sit
in the same starved regime as 440–447 did, and §7.13 measured what that regime does — not merely noise
but a *concentration-dependent compression* that corrupted `r_Q`. **The gate is photometric: whether a
lamp puts enough photons through 640–670 to clear the DN guard.** On the current roster only the Sansi
shows real deep-red output.

⚠ **A lamp is also a wavelength standard we already own.** The CFL gives Hg 404.66 / 435.83 / 546.07 /
576.96 / 579.07 plus Eu³⁺ 611.6 / 626.6 / 650.7 — an independent multi-point check of the calibration
across the whole working range, from one capture. Note §7's existing exposure caveat: the CFL needs its
own (much lower) calibration exposure, or the red cluster merges into one blob.

## 8. The sample: solvent chemistry, turbidity and the vessel

> **A readable version of this chapter exists.** `DOC_sample_physics.md` → *Light, Pigment and
> Solvent* (internal PDF) covers the same ground as continuous prose, with the textbook background
> — Beer–Lambert, the porphyrin band structure, Rayleigh vs Mie, dichromatism — that this KB entry
> assumes. Use that for reading; use this for looking things up.

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

| solvent | ε (25 °C) | ρ g/mL | b.p. °C | flash °C | GHS eye | dissolves oil | polystyrene | field-usable |
|---|---|---|---|---|---|---|---|---|
| **2-propanol** *(current)* | **17.9** | 0.786 | 82.6 | 12 | H319 | **marginal** — the gap above | ✅ safe | ✅ drugstore (**H225**) |
| 1-propanol | 20.1 | 0.803 | 97.2 | 22 | ⛔ **H318** | better (linear chain) | ✅ safe | ⛔ rejected on hazard |
| **1-butanol** | **17.8** | 0.810 | 117.7 | 35 | ⛔ **H318 Cat 1** | **good** | ✅ safe | ⛔ **REJECTED 2026-08-01** |
| **⭐ 2-butanol** *(sec-)* | **≈16** ⚠ *unverified* | 0.808 | 99.5 | 24 | ✅ **H319 Cat 2A** | better than IPA, **weaker than 1-butanol** *(branched)* | ~ "moderate–good, caution" — **soak-test mandatory** | ✅ H226; costlier |
| isobutanol | ~17.7 | 0.802 | 107.9 | 28 | ⛔ **H318 Cat 1** | good | ✅ | ⛔ rejected on hazard |
| tert-butanol | 12.5 | 0.789 | 82.4 | 11 | H319 | good | ✅ | ⛔ **m.p. 25.8 °C — solid at room temperature** |
| n-heptane | 1.92 | 0.684 | 98.4 | **−4** | — | ideal | ⛔ **swells + crazes** | ⛔ H225/H304/H411 |
| cyclohexane / isooctane | ~2 | — | — | — | — | ideal *(the AOCS/IUPAC choice)* | ⛔ cyclohexane **dissolves** PS | ⛔ |

**The original argument was for 1-butanol:** `ε = 17.8` against isopropanol's `17.9` — essentially identical
polarity, so band positions should barely shift — while its longer alkyl chain makes it a genuinely good
triglyceride solvent. Dissolution without solvatochromism.

⛔ **1-butanol is REJECTED on hazard (2026-08-01, `SPEC_capture_quality.md` §16.12.7a).** It carries **H318 —
serious eye damage, Category 1, irreversible** — as do 1-propanol and isobutanol. **2-butanol is the only
butanol isomer that is both liquid at room temperature and free of Cat-1 eye damage** (tert-butanol melts at
25.8 °C). Its flammability classification is also *better than the isopropanol we use today* (H226 vs H225).

⚠ **But the substitution is not free.** 2-butanol is a **secondary (branched)** alcohol, so by this section's
own chain-length rule its solvency sits **between** isopropanol and 1-butanol — a real but partial gain. It is
more volatile (99.5 °C vs 117.7 °C). And critically, **its ε is around 16, not 17.8**, so the "bands barely
move" argument that made a butanol attractive is weakened. ⚠ **That ε is unverified** — confirm it before
relying on the argument. Heptane (`ε = 1.9`) would move the bands hard, on top of dissolving the jar.

⚠ **The literature does not use neat isopropanol for oil pigments.** The standard methods read chlorophyll and
carotenoids in **cyclohexane** (445/470 nm), **hexane** (442/668 nm), **CCl₄**, or **ethanol + isooctane /
ethanol + heptane**. The field converged on hydrocarbons precisely because they give a true solution. Our choice
of IPA is a *field-usability* compromise, and §8.3 is the price we pay for it.

**And the community's answer to turbidity is CLARIFY, not WAIT.** Guidance to "measure within ~10 min" belongs
to nephelometry, where the particles *are* the analyte; the "10–15 min equilibration" boilerplate is thermal
equilibration and colour development. Neither is our case. Where particles are the *interferent*, the standard
practice is filtration or centrifugation before the cuvette, plus a fitted baseline for the residual.

### 8.5 The vessel

**Polystyrene is safe with alcohols and attacked by hydrocarbons.** Alcohols are essentially the *only*
PS-compatible organic family, so the jar and the solvent are a coupled choice: stay on alcohols and the cheap
transparent cosmetic jar keeps working; move to a hydrocarbon and the vessel must be replaced.

#### Quantifying it — Hansen solubility parameters and RED

Compatibility charts are qualitative and, as we found when they contradicted each other on PMMA, unreliable at
the margins. **Hansen solubility parameter theory gives a number instead.** Each substance carries three
coordinates — `δD` dispersion, `δP` polar, `δH` hydrogen bonding — and a polymer occupies a *sphere* of radius
`R₀` in that space:

```
Ra² = 4(δD₁−δD₂)² + (δP₁−δP₂)² + (δH₁−δH₂)²        RED = Ra / R₀
```

**RED** = **Relative Energy Difference**, i.e. how far outside the polymer's sphere a solvent sits, in units of
that sphere's radius. `RED < 1` dissolves; `RED ≈ 1` swells and stress-cracks; `RED > 1` is a non-solvent.

Against **polystyrene** (Hansen handbook: δD 21.3, δP 5.8, δH 4.3, R₀ 12.7):

| solvent | **RED** | reading |
|---|---|---|
| toluene | **0.65** | dissolves it |
| **cyclohexane** | **0.90** | **dissolves it** — the classic theta-solvent for PS |
| n-heptane | **1.10** | just outside — swells and stress-cracks, does **not** dissolve |
| **1-butanol** | **1.23** | outside — safe; the closest of the alcohols |
| **2-butanol** | ⚠ **not computed** | see the warning below — likely **closer to PS** than 1-butanol |
| isooctane | 1.27 | outside |
| **2-propanol** *(current)* | **1.29** | outside — safe |
| 1-propanol | 1.33 | outside |
| ethanol | 1.49 | comfortably outside |
| water | 3.23 | inert |

> ⚠ **2-butanol's RED is deliberately left blank rather than estimated.** Computing it needs the same source's
> polystyrene parameters, and a value derived from a different source would not be comparable with the rows
> above. **But the direction is predictable and it is the wrong one:** 2-butanol is a *secondary* alcohol, so
> its hydrogen-bonding term δH is **lower** than 1-butanol's — which moves it **toward** polystyrene in Hansen
> space, i.e. toward the swelling boundary that heptane sits on at 1.10. A resin-compatibility guide
> independently rates 2-butanol against PS only as *"moderate–good, with caution"*, against 1-butanol's clean
> "safe at 20 °C". **Two independent hints in the same direction ⇒ the overnight soak test
> (`SPEC_capture_quality.md` §16.12.7 item b) is a gate, not a precaution.**


**Three things this settles.** (1) **Butanol at 1.23 against isopropanol's 1.29 is not a borderline case** — both
sit comfortably outside, butanol only marginally closer. (2) **Heptane does not dissolve polystyrene**; at 1.10
it swells and crazes it, which disqualifies it for an optical vessel just as thoroughly but by a different
mechanism. (3) Of the hydrocarbons the analytical literature favours, **cyclohexane is the worst possible choice
for a PS jar** — at 0.90 it is a genuine solvent for it.

⚠ Published parameter sets disagree by a few percent, and polystyrene's `δD` is quoted as either ~18.6 or ~21.3
depending on convention — **mixing sets gives badly wrong answers.** The *ranking* is robust; treat the absolute
values as indicative and always compute a comparison within one set.

**The failure mode to watch is optical, not structural.** A crazed jar does not crack — it goes faintly hazy, and
haze scatters, which this instrument records as absorbance (§8.3). A slowly crazing vessel would therefore
masquerade as sample turbidity: exactly the thing a solvent change is meant to remove. Cheap check: cycle a spare
jar through ~20 fill/empty cycles and measure it as a blank against an unexposed one — far more sensitive than
the eye.

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

## ⭐⭐ 9. Standard photometric pigment methods — and the three reasons ours is not one  *(2026-08-29)*

Every textbook route to "how much chlorophyll is in this oil" is a **two- or three-wavelength photometric
formula** with a published extinction coefficient. They are worth knowing precisely, because §16.23's
protocol keeps drifting toward them and because one of them contains the idea our own metrics are built on.

### 9.1 The two formulas, stated correctly

**Chlorophyll pigments** — AOCS Cc 13d-55, and the form quoted almost everywhere:

```
C_chloro [mg/kg] = [ A670 − (A630 + A710)/2 ] / (a · d)  ×  DF
```

**Carotenoids** — the Mínguez-Mosquera convention, as β-carotene / lutein equivalent:

```
C_carot [mg/kg] = A470 · 10^6 / (2000 · 100 · d)  ×  DF   =   5 · A470 / d  ×  DF
```

with `d` the path length in cm and `DF = m_total / m_sample` the **gravimetric** dilution factor, applied as
a multiplier.

| symbol | value | note |
|---|---|---|
| carotenoid wavelength | ⭐ **470 nm** | the `E¹%₁cm = 2000` coefficient is *tied to 470*. **460 nm is wrong** and is a common misquote |
| carotenoid factor | **5** | `10⁶/(2000·100)`; arithmetic is exact |
| chlorophyll `a`, Mínguez | `10⁶/(613·100)` = **16.31** mg/kg per unit A | pheophytin *a*, `E = 613` |
| chlorophyll `a`, AOCS | ⚠ **0.1086** ⇒ **9.21** mg/kg per unit A | ⛔ **this constant is NOT independently confirmed here.** A figure of `0.1016` also circulates and looks like a transposition of it. Verify against the method before any number is published |

⛔ **The two conventions disagree by ~1.8×** (9.21 against 16.31) because they report different reference
pigments on different bases. ⇒ **an absolute ppm from either is only comparable to other numbers computed
the same way.** This is the same lesson as `T = 18.6 / 30.0 / 52` — a photometric threshold is
convention-bound, not a property of the oil.

⚠ **And the unit is mg/L, not mg/kg.** The `10⁶` conversion is per litre; calling the result mg/kg skips a
density divide (ρ ≈ 0.92) and runs **+8.7 %** high on a mass basis. The field does this universally and
calls it ppm, so it is a convention rather than an error — but it is not ours to inherit silently.

### ⭐⭐ 9.2 The one idea worth stealing — and the fallback that throws it away

The chlorophyll formula's real content is not the coefficient. It is `A670 − (A630 + A710)/2`: **a band
height read against the mean of two flanking anchors.** That is exactly `§16.20`'s pedestal subtraction and
exactly what `Rv` does at 622–627 against marker (3). The standard method reached the same construction from
turbidity in oil that we reached from the pedestal — independent arrival at the same answer.

⛔ **Which is why the "610 nm workaround" for a red-clamped instrument must be refused.** Told that a
spectrometer stops at 630 nm, the standard advice is to abandon 670 and compare bare `A610` between oils —
"0.4 is twice 0.2 at equal `DF`". That is Beer–Lambert-correct and **instrumentally worthless here**: it
silently drops the two anchors that made the 670 formula work, and `SPEC_capture_quality.md` §16.24 measures
the baseline at **62 % of raw Q**. A bare band absorbance on this instrument is mostly pedestal.

⇒ **A red-clamped instrument does not need a different wavelength. It needs the anchors kept.** That is the
whole design of `V` / `Q%` / `Rv`.

### 9.3 The three reasons the formulas do not transfer

| | |
|---|---|
| ⛔ **670 nm is outside the window** | §7.2: the delivered range ends ~636 nm at the ROI. The dominant chlorophyll band, *and* its 710 nm anchor, are both unreachable. The formula cannot be evaluated at all |
| ⛔ **They assume a MATRIX blank, we use a LAMP reference** | the standard method zeroes on **pure solvent from the same bottle**, so the matrix cancels and `DF` scales cleanly. We compute `T = S/R` against the lamp (§2), so the solvent's own absorbance rides through and does **not** scale with `DF`. The `DF` algebra is invalid on our spectra as recorded |
| ⚠ **The blue peak is not one pigment** | at 460–470 nm the carotenoids sit **on top of** the porphyrin Soret. The method's own literature says so plainly, and §4.2 says it for our lamp. A single absorbance there is a two-family mixture |

⭐ The second row is actionable, not merely a caveat. Now that sunflower is the solvent (`DOC_sample_physics.md`
§4A), a **same-batch matrix blank** is available for the first time — and it would remove the
sunflower-*bottle* variable measured on 2026-08-24 (`Q%` +2.4 between bottles, `hR` flat). ⏸ Not proposed
here as a change; recorded as the one place the standard convention is better than ours. `ROADMAP.md` §0a's
"one reference on pure solvent per fill" is already halfway to it.

### ⚠ 9.4 A band-assignment datapoint, and it disagrees with us

The literature fallback for a red-clamped instrument names pheophytin *a*'s minor bands at **~535 nm** and
**~608–610 nm**. Those are the free-base solution-phase positions and they are not what we measure: our
bands sit at **568** and **624** (`§4.1a`, `SPEC_red_ratio_metric.md` §2.5), and 2026-08-24's second-derivative
work explains the gap — aggregation in the lipid matrix **broadens and red-shifts** the long band, which is
whole only in an index-matched solvent (sunflower 623–625; isopropanol drifts to 629–630).

⇒ this **strengthens** §4.1a's standing warning rather than contradicting it: the assignment is literature,
the positions are ours, and 608–610 is one more reason not to quote a solution-phase number at a dispersion.
⛔ It is **not** evidence for moving any window.

### Sources for §9

- **Mínguez-Mosquera pigment method** (470 nm / `E=2000` lutein; 670 nm / `E=613` pheophytin *a*; `/100/d`,
  ×10⁶ → mg/kg): [*Use of chlorophyll and carotenoid pigment composition to determine authenticity of virgin
  olive oil*, JAOCS](https://link.springer.com/article/10.1007/s11746-000-0136-z) ·
  [Gandul-Rojas & Mínguez-Mosquera, *J. Sci. Food Agric.* **72**:31 (1996)](https://scijournals.onlinelibrary.wiley.com/doi/abs/10.1002/(SICI)1097-0010(199609)72:1%3C31::AID-JSFA619%3E3.0.CO;2-5).
- **AOCS Cc 13d-55** (the 630/670/710 three-wavelength form): referenced in
  [IUPAC, *Determination of chlorophyll pigments in oils*](http://publications.iupac.org/pac/1995/pdf/6710x1781.pdf).
  ⛔ The `0.1086` coefficient is quoted from secondary sources and **was not verified against the method text**.
- **Provenance of this section.** A 2026-08-29 Gemini transcript on mixing pumpkin oil into sunflower oil for
  VIS spectroscopy, reviewed at the bench:
  `spectracs-references/notes/20260829_gemini_oil_mixing_and_pigment_photometry.txt`. Its formulas carry the
  460-nm and constant errors corrected above; its preparation advice is folded into
  `SPEC_capture_quality.md` §16.23.2c. ⛔ It also recommends a **30–35 °C warm bath** to thin the oil, which
  `SPEC_settled_measurement.md` §34.2 measured as a **preparation fault** (+0.680 `Q%`). Do not follow it.


## Sources
- `KB_led_and_oil_spectra.md` (LED + oil sources). Fruhwirth & Hermetter (2007), *Seeds and oil of the
  Styrian oil pumpkin*, Eur. J. Lipid Sci. Technol. **109**(11):1128–1140, DOI
  [10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105) — record in
  `spectracs-references/articles/`.

### Sources for §4.1 (the pigment identity and its band positions)

- **Pigment identity, and the Mg-free degradation product.** Fruhwirth & Hermetter (2007), §3.5 —
  *"protochlorophyll (a and b) and protopheophytin (a and b), the latter being a protochlorophyll lacking
  the magnesium ion"*. Local copy:
  `spectracs-references/articles/Fruhwirth_Hermetter_2007_Styrian_oil_pumpkin.pdf`, and the free mirror at
  [gruenesglueck.com](http://www.gruenesglueck.com/wp-content/uploads/2014/09/1_krbiskernl_bersichtsartikel_fruhwirth-hermetter_2007.pdf).
  Same paper, Fig. 3 caption: emission maximum **635 nm** in methanol.
- **Protochlorophyllide band positions.** Qy ≈ **623 nm** in 80 % acetone, ≈ **626 nm** in methanol; Soret
  ≈ 440 nm — [*Protochlorophyllide Spectral Forms*, Pak. J. Biol. Sci. (2010)](https://scialert.net/fulltext/?doi=pjbs.2010.563.576).
  Monomeric-form emission ≈ 630–636 nm — [Biochim. Biophys. Acta (2006)](https://www.sciencedirect.com/science/article/pii/S0005272806001782).
  *(Protochlorophyll = protochlorophyllide esterified with phytol/geranylgeraniol; the ester sits on the
  propionate side chain, not the chromophore, so the visible bands are essentially unshifted.)*
- **Pumpkin-seed-specific pigment speciation.** 2,4-divinyl-protochlorophyll *a*,
  2,4-divinyl-protopheophytin *a*, 2-vinyl-protopheophytin *a*; protopheophytins **1.1–35.5 %** of
  protochlorophylls, rising with seed storage; protochlorophyll emission **630 + 655 nm** in the oil against
  700 nm in the seed — [*Histolocalisation of the oil and pigments in the pumpkin seed*](https://www.researchgate.net/publication/227928192_Histolocalisation_of_the_oil_and_pigments_in_the_pumpkin_seed).
- **Band nomenclature (Soret / Q, four-orbital model).** Gouterman (1961), *J. Mol. Spectrosc.* **6**:138.
- **⭐ Why demetallation moves intensity AWAY from the long-wavelength end.** A metallated ring (D₄ₕ)
  shows **two** Q bands (α, β); the free base (D₂ₕ) shows **four**, numbered I–IV from the longest
  wavelength. Their intensity ordering is classified into four types by substituent pattern — **etio**
  IV > III > II > I, **rhodo** III > IV > II > I, **oxo-rhodo** IV > II > III > I, **phyllo**
  IV > II > III > I. **Band I is the weakest in every one of them.** So a pigment whose Qy(0,0) is its
  dominant long-λ band while metallated becomes, on demetallation, the *weakest* of four — which is
  exactly the redistribution measured in `SPEC_capture_quality.md` §16.13.9.
  Sources: [*The Use of Spectrophotometry UV-Vis for the Study of Porphyrins*, InTech](https://cdn.intechopen.com/pdfs/37656/InTech-The_use_of_spectrophotometry_uv_vis_for_the_study_of_porphyrins.pdf);
  [Porphyrin overview, ScienceDirect](https://www.sciencedirect.com/topics/physics-and-astronomy/porphyrin).
  *(Protopheophytin carries the ring-E carbonyl, a "rhodofying" group, so the **rhodo** ordering is the
  expected one for it — band I still weakest.)*
- **Chlorophyll *a* comparison values** (the molecule we do *not* have): Qy 662–665 nm solvent-dependent —
  [PhotochemCAD, chlorophyll a](https://omlc.org/spectra/PhotochemCAD/html/122.html).

⚠ **2026-08-04 — OUR OWN INSTRUMENT DOES NOT CONFIRM THE Qy POSITION, and cannot at this range.**
Two independent tests on the 28-run post-rebuild corpus (`SPEC_metric_research.md` §7.11a): **28/28 runs
are still RISING at the 629.8 nm cut-off**, and a fixed-template fit returns a **negative amplitude** at
623–626 nm — physically impossible for an absorption band — while its residual bottoms at **~630 nm**.
So our spectra show **no resolvable Qy maximum at 623–626**. Three explanations cannot be separated:
solvent/matrix shift (literature is 80 % acetone and methanol; ours is oil in IPA), aggregation in the
lipid matrix, or ⚠ **instrument** — 620–630 nm is exactly where the lamp collapses
(`SPEC_capture_quality.md` §16.12.11 B) and a rising edge artifact is indistinguishable from a
red-shifted band edge. §16.12.12's 5.1 σ result confirms pigment IS present there; it does not exclude a
mixture. **This is an open discrepancy, not a correction — the values below are correctly sourced.**

⚠ **Not yet independently verified:** a primary measurement of *protopheophytin a*'s band positions. The
green→brown direction in §4.1 is argued from demetallation symmetry-lowering, which is textbook porphyrin
photochemistry, but the specific numbers for this molecule are not sourced here. Treat the mechanism as
sound and the exact shifts as unquantified.
- Implemented colour math: `SPEC_spectrum_processing.md`. Prior absorptance prototype: `unsorted/oils.jl`.
- Real measured spectra: `../../spectracs-evaluations/` (`.dx`/`.sgd`, incl. `light_*` references + `*abs*`).
