<!--
MASTER DOCUMENT — Spectracs capture fidelity.
This markdown file is the SOURCE OF TRUTH. The PDF is generated from it:

    python3 docs/tools/build_capture_fidelity_pdf.py
    -> ../spectracs-docs/internal/Spectracs_CaptureFidelity.pdf

Never hand-edit the PDF. Edit here, re-run, commit both.
This is DOCUMENTATION, not a specification: it records what we built and WHY. It creates no work
items. Where a decision is still open it says so and points at the spec that owns it.
-->

# Capture Fidelity

*How a €30 webcam is made to measure a spectrum — and why every step is the way it is.*

**Audience.** Written for three readers at once: the **developer** returning to this code after a
month and needing the big picture; the **chemist** who wants to know whether the numbers can be
trusted and what they physically mean; and the **lab** receiving a Spectracs report and asking how
the instrument works. No code knowledge is required for chapters 1, 2 and 4 — code and file names
appear `like this` and can be skipped.

**What this is not.** This is not a specification and it asks for no work. It is the consolidated
record of what was measured, decided, and built. Every claim here is traceable to a spec section
listed in Appendix B.

**How to read it.** **Chapter 1 is a standalone summary** — the abstract plus a one-table
overview of every decision, for a reader who wants the impression without the argument. Chapters 2
and 3 then tell the story properly. Wherever a topic has more behind it than the story
needs, a green box points into **Appendix A — Knowledge base**, which treats that topic properly and
stands on its own. So the main text stays readable start to finish, and the background is there when
you want it — including the brightness law and the sRGB standard, in [KB 1](#kb-1-the-brightness-law-gamma-in-depth).

<!--TOC-->

<!--PAGEBREAK-->

## 1. Abstract and summary

*Chapter 1 stands alone. Read only this and you will know what the instrument is, what was decided,
and why — without the derivations.*

### 1.1 Abstract

**The problem.** Determine the quality of pressed pumpkin-seed oil — is it the prized deep green, or
has over-roasting turned it brown? — using hardware a mill owner can afford: a diffraction grating,
a white LED and a **consumer USB webcam**. A webcam is built to make pictures look good, not to
measure light. It applies automatic exposure and white balance, interpolates colour it never
measured, bends the brightness scale on purpose, and rounds everything to 8 bits. None of that is
compatible with quantitative measurement.

**The approach.** Nothing is measured in absolute terms. Every measurement is a **ratio** of two
spectra taken seconds apart — the pure solvent (`R`) and the oil dilution (`S`) — and the quantity
that matters is a further ratio, of two absorbance bands. That double-ratio structure is what makes
cheap hardware viable: the lamp's spectrum, the sensor's sensitivity, the grating, the lens, the
exposure, the dilution and even the camera's brightness curve are all *multiplicative* factors that
cancel. What is left over is a short, well-understood list — and this document is largely about that
list.

**The method.** One rule shaped the work: **measure first, then decide.** Every chapter in §3
follows the same arc — a symptom, a measurement that explains it, a decision, and its cost. Several
of them end in "change nothing", which is a legitimate outcome: the dark-frame chapter (§3.10) is a
full investigation whose conclusion is that the textbook correction is not needed here, and it is
precisely *because* it was measured that we can now rely on that.

**The outcome.** The instrument separates green from brown oils with a class separation of about
**10× the run-to-run scatter**, and does so **independently of dilution** — a sloppy sample
preparation cannot flip the verdict. Two errors were found and removed that had been biasing the
reference (a systematically dim group of frames after each exposure change, and automatic white
balance drifting between the two captures). One known error remains uncorrected: **sensor
self-heating**, worth about 1.7 % of the reference's shape (§3.6). The full list of open items is
in §6.

**The surprises worth knowing about.** Three findings ran against intuition and are documented in
detail because a future reader will otherwise re-derive them the hard way:

- the camera's **exposure control runs backwards** and saturates — a higher setting gives a *darker*
  image, and above a threshold nothing changes at all (§3.4);
- **undoing the camera's brightness curve *properly*, with the official sRGB formula, makes the
  measurement worse** than using the simplified textbook version — by 24 % of the class separation
  (§3.3);
- the sensible-sounding fix of **moving the analysis band away from the noisy dark region** costs a
  quarter of the discriminating power, because the darkest part of the band *is* the signal. The
  real fix was to dilute the sample instead (§3.12).

### 1.2 What is actually being measured

A drop of pumpkin-seed oil dissolved in isopropanol is placed in the light path. The instrument
never measures "how much light the oil absorbs" directly — it measures **two** spectra and divides
them:

```
  R(λ)   REFERENCE   pure isopropanol in the pot   -- "how much light arrives with no oil"
  S(λ)   SAMPLE      the oil dilution in the pot   -- "how much light arrives through the oil"

  T(λ) = S(λ) / R(λ)              transmission   — the fraction that got through
  A(λ) = −log10( T(λ) )           absorbance     — the Beer-Lambert quantity, ∝ concentration
```

Everything in this document exists to make that division trustworthy. **The ratio is the whole
design idea**, and understanding what it does and does not cancel (§2.4) explains almost every
decision that follows.

→ Background: [KB 2 — The Beer-Lambert law, and the algebra of why ratios are invariant](#kb-2-the-beer-lambert-law-and-the-algebra-of-ratios)

### 1.3 The chain, end to end

```
  LAMP  Yuji SunWave 6500 K white LED
    │
    ▼   light through the sample pot, through a slit, onto a diffraction grating
  CAMERA  ELP UVC webcam @ 2592 × 1944, fixed exposure, fixed white balance
    │     (inside the camera: sensor → white balance → demosaic → GAMMA ENCODE → 8-bit)
    ▼
  FRAME  a 2-D image: horizontal axis = wavelength, vertical axis = the slit's height
    │
    ├─ 1. crop to the region of interest (the bright band), drop the outer 20 % of rows
    ├─ 2. per pixel: grey = max(R, G, B)                                        §3.2
    ├─ 3. per wavelength column: Tukey biweight down the rows  (spatial)        §3.7
    ├─ 4. repeat for 150 frames; reject dim frames, then sigma-clipped mean     §3.8
    ▼
  SPECTRUM  one intensity value per wavelength, 440 … 630 nm
    │
    ▼   done once for the reference, once for the sample
  T = S / R   →   A = −log10(T)   →   evaluation (pigment bands, colour, verdict)
```

### 1.4 The decisions at a glance

The whole of chapter 3 in one table: what the capture chain does, and what led us to do it that way.
Each row is a section there.

| § | What we do | What led us there |
|---|---|---|
| 3.1 | Pin capture to **2592 × 1944** and trip an alarm if the calibration does not fit the frame | Capture had silently drifted to a different resolution than the wavelength calibration was authored at. Every wavelength was wrong, and the spectrum still looked perfectly plausible. |
| 3.2 | Reduce each pixel to **`max(R, G, B)`** | The broadcast luminance formula it replaced weights blue at 5/32 — it was discarding two thirds of the blue signal, exactly where the pigment band sits. The camera image of that region was vividly blue; the *weighting* was suppressing it. |
| 3.3 | Undo the camera's brightness curve with the **pure `^2.2` power law** — not the official piecewise sRGB curve *(designed, not yet built)* | Absorbances are compressed by ≈ 1/2.2. Measured: a pure power law leaves the verdict **bit-identical** at any exponent, while the physically more faithful sRGB curve costs **24 %** of the class separation and buys no colour improvement. |
| 3.4 | Auto-expose with a **direction-agnostic sweep** on the 99.9th percentile of the per-channel maximum, then **lock** the exposure | The camera's exposure control is *inverted* and clamps, so the original bisection drove to the worst possible setting. A luminance metric hid a fully clipped green channel behind an unclipped red one. |
| 3.5 | **Settle adaptively** — drain frames until the frame brightness stops changing | After an exposure change the camera *ramps* for about a second. A fixed wait was a per-camera magic number, and an earlier adaptive test watched a quantity that plateaus early and declared success too soon. |
| 3.6 | Nothing yet — **diagnosed and documented** | The camera heats itself: the channel balance drifts as a clean exponential, τ = 171 s, 1.7 % total, ~9 min to settle. The reference and sample straddle the steepest part of that curve. The largest error still uncorrected. |
| 3.7 | Reduce each wavelength column with a **Tukey biweight** over the central 60 % of rows | A single centre row let one hot pixel or dust speck corrupt a wavelength permanently — and a plain average over the rows is dragged by exactly the same pixel. |
| 3.8 | **Reject dim frames as whole frames**, then take a **sigma-clipped mean** | The reference burst runs right after an exposure sweep, so its first frames were systematically dim. A per-wavelength clip cannot reject a *coherent group* — the group inflates the spread and drags the mean toward itself. |
| 3.9 | **Freeze white balance at 6500 K** for measurement; leave it automatic for calibration | Automatic white balance re-converges after every exposure change, so the reference caught it mid-drift. It rescales channels *individually*, which is the one kind of change a ratio cannot cancel. Calibration needs the opposite, because it identifies emission lines by colour. |
| 3.10 | **No dark-frame subtraction, no bad-pixel map** | Measured over 150 dark frames at the worst-case exposure: black level **0.00 %** of full scale. The offset the textbook correction removes is not there, and the ~10 hot pixels are already handled by §3.7. |
| 3.11 | Clamp the captured range to **440–630 nm**, declared by the evaluation plugin | Outside that window the lamp is weak and the small optics roll off, so those wavelengths contribute noise dressed as data. The science declares what it needs; the capture layer obeys and fails loudly on a mismatch. |
| 3.12 | Prepare the sample at **1:30 or 1:33**, not 1:20 | The fresh 2026 oils absorb far more than the aged ones used for validation: the sample bottomed out at **DN 5 of 255**, inside the least trustworthy part of the camera's response. Diluting lifts it to 16–25 DN and changes the verdict by ±0.35 %. |
| 3.13 | Rebuild the **jar seat** and mark the fill line; document the sample's own **turbidity** as the next lever | The jar is lifted out and put back between the two captures a ratio is made of, and any change in how it sits enters absorbance as an offset *and* a slope. Rebuilding the seat took re-seat tilt from 2.84 % to **1.34 %** and metric scatter from 9.7 % to **2.9 %** — the largest fidelity gain in the project, and a printed part rather than an algorithm. It also handed the top of the error budget to the chemistry: a few drops of oil in isopropanol is not a solution but a dispersion, and the scatter it adds is **0.7–1.9× the pigment signal**. |

Chapter 4 is the mirror image of this table — the things that were seriously considered and
**deliberately not done**, with the reason for each.

### 1.5 The five things worth remembering

> **1. The reference cancels the instrument.** The lamp's spectrum, the sensor's per-wavelength
> sensitivity, the grating's efficiency and the lens's vignetting all appear identically in `R` and
> `S`, so they divide out exactly. This is why a cheap camera can do quantitative work at all, and
> why we do *not* need to characterise the sensor.
>
> **2. It cancels multiplicative errors, not additive ones.** Anything that *scales* the light
> cancels. Anything that *adds* to it — stray light, dark current, turbidity in the sample —
> survives the division and biases the result. **This is not a footnote: the sample's own turbidity
> adds a floor 0.7–1.9× the size of the pigment signal, and it is now the largest known error left
> in the instrument (§3.13).**
>
> **3. It cannot fix non-linearity.** The camera bends brightness on purpose (the "gamma" law). A
> ratio of two bent numbers is not the ratio of the true numbers. This is the one instrument error
> the reference leaves behind (§2.2, §3.3).
>
> **4. Ratios of two absorbance bands are immune to almost everything.** Dilution, gamma exponent,
> path length and overall gain all scale absorbance uniformly, and a ratio divides a uniform scale
> out. That is why the pumpkin verdict survives conditions that would wreck an absolute measurement.
>
> **5. Outliers come in two flavours and need two different cures.** A hot pixel is at the same
> place in *every* frame — only a spatial estimator kills it. A glitched frame is transient — only a
> temporal estimator kills it. Neither substitutes for the other (§2.5).

<!--PAGEBREAK-->

## 2. Foundations

*Reference material. If you already know what an EOTF is, skip to chapter 3.*

### 2.1 What a webcam actually hands you

A scientific (machine-vision) camera hands you a number proportional to the number of photons that
hit the pixel. A **consumer webcam does not.** Between the sensor and the USB cable sits an image
signal processor that has one job: make a picture that looks right on a screen. In order it applies

1. **automatic exposure** — adjusts integration time to a target brightness,
2. **automatic white balance** — rescales the R, G, B channels so white objects look white,
3. **demosaicing** — interpolates the colour filter mosaic into full-colour pixels,
4. **gamma encoding** — bends the brightness scale (the subject of §2.2),
5. **quantisation** — rounds to 8 bits, i.e. integers 0…255.

Only step 5 is unavoidable. Steps 1 and 2 are *turned off or frozen* by Spectracs (§3.4, §3.9)
because a control loop that changes between the reference and the sample destroys the ratio. Step 4
cannot be turned off on a UVC webcam — it can only be undone in software (§3.3).

→ Background: [KB 5 — How a colour camera sees light: Bayer mosaic, demosaicing, quantum efficiency](#kb-5-how-a-colour-camera-sees-light)

Throughout this document a stored 8-bit value is called a **DN** (*digital number*), 0…255. A DN is
not a physical quantity; it is a byte.

→ Background: [KB 4 — Digital numbers, quantisation and noise](#kb-4-digital-numbers-quantisation-and-noise)

### 2.2 The brightness law (gamma) — why it exists at all

Human vision is far more sensitive to differences among dark tones than among bright ones. If you
store brightness *linearly* in 8 bits, the dark half of the range gets too few code values and
shows visible banding, while the bright half gets more than the eye can use.

So every consumer imaging standard stores a **bent** version of brightness:

```
  stored value  =  light ^ (1 / γ)          with γ ≈ 2.2      (encoding, in the camera)
  light         =  stored value ^ γ                            (decoding, in the display)
```

The bend allocates more code values to the dark end, where the eye needs them. Your monitor applies
the inverse bend, so the picture looks right. The chain is invisible **as long as you only look at
the picture**. It becomes a problem the moment you do arithmetic on the stored values — as we do.

> **The consequence for us.** With `v = v_linear^(1/γ)`:
> `T_measured = S/R = (S_lin/R_lin)^(1/γ) = T_true^(1/γ)`, hence `A_measured = A_true / γ`.
> Our absorbances are compressed by a factor of about 2.2 — they are real, but not *physically*
> real. And because that factor is **uniform**, any *ratio* of two absorbance bands is unaffected.

→ Background — the full treatment, both formulas, the terminology (OETF/EOTF), the history and the
classic pitfalls: [KB 1 — The brightness law (gamma) in depth](#kb-1-the-brightness-law-gamma-in-depth)

### 2.3 The variants — pure power law versus the sRGB standard

Two different curves both get called "the 2.2 law", and the difference matters at the dark end.

**Variant A — the pure power law.** One clean formula, `light = (DN/255)^2.2`. It is the textbook
description and the one everybody quotes.

**Variant B — the sRGB standard** (IEC 61966-2-1, 1996), which is what cameras and monitors actually
implement. It is **piecewise** — defined in two branches with a switchover point (the *knee*):

```
  DN/255 ≤ 0.04045   →   light = (DN/255) / 12.92                  ← a straight line
  DN/255 >  0.04045   →   light = ((DN/255 + 0.055) / 1.055) ^ 2.4  ← a power curve
```

Two surprises live in that formula:

- **The exponent says 2.4, not 2.2.** The 2.4 is a *construction parameter* of the upper branch
  only. Together with the `+0.055 / 1.055` offset and the straight lower branch, the curve as a
  whole behaves like an exponent of **≈ 2.2**. Measured on our own oil spectra, the effective
  exponent comes out **2.10 – 2.24** across the mid-range — nowhere near 2.4. *2.2 is the answer;
  2.4 is an ingredient.*
- **The straight line at the bottom is deliberate.** A pure power curve has *infinite slope at
  zero* in the encoding direction: the darkest code values would represent vanishingly small light
  differences, wasting codes and hugely amplifying noise when decoded. The standard caps the slope
  at a finite 12.92 and splices a straight line below the knee. That region — roughly **DN ≤ 10** —
  is called the **toe**.

The two variants agree closely everywhere above the knee and disagree noticeably below it. Which
one to use is therefore a question about *how dark your darkest measurement is*. For Spectracs the
answer turned out to be counter-intuitive and is the subject of §3.3.

→ Background: [KB 1 — the exact sRGB formulas, and where the two variants diverge](#kb-1-the-brightness-law-gamma-in-depth)

### 2.4 What a reference measurement cancels — and what it does not

This is the single most useful mental model in the whole system. Write what the camera reports as

```
  measured  =  g(λ) · true(λ)  +  D            then bent by the gamma law
```

where `g(λ)` collects **everything multiplicative** — lamp brightness at that wavelength, grating
efficiency, lens transmission, sensor quantum efficiency, exposure time, gain — and `D` collects
**everything additive** — sensor dark current, black-level offset, stray light inside the housing.

| effect | multiplicative or additive? | does `T = S/R` remove it? |
|---|---|---|
| lamp spectrum (the LED's own shape) | multiplicative | **yes, exactly** |
| sensor spectral response (QE) | multiplicative | **yes, exactly** |
| grating efficiency, lens vignetting | multiplicative | **yes, exactly** |
| exposure time, analogue gain | multiplicative | **yes** — if identical in R and S |
| dark current, black level, stray light | **additive** | **no** — survives, biases T toward 1 |
| turbidity (a cloudy, badly dissolved sample) | **additive** | **no** — looks like absorption |
| gamma encoding | **neither** — non-linear | **no** — leaves a uniform `1/γ` on absorbance |

Read the table twice. It explains, in one place:

- why we never measured the sensor's spectral response, and never will (§4);
- why the dark level had to be *measured* before we could ignore it (§3.10);
- why "dissolve it properly" is the only lab instruction that really matters (§3.12);
- why exposure must be **locked** between reference and sample (§3.4);
- why gamma is the one residual worth a chapter of its own (§3.3).

→ Background: [KB 2 — the algebra of the ratio, and exactly where it stops holding](#kb-2-the-beer-lambert-law-and-the-algebra-of-ratios)

### 2.5 Two kinds of outlier need two different cures

A wrong pixel value can come from two completely different places, and no single estimator removes
both:

| | where it comes from | it appears… | the only cure |
|---|---|---|---|
| **spatial** | a hot / dead pixel, a dust speck, a smile-distorted edge row | in the **same place in every frame** | a robust estimator **across rows** |
| **temporal** | a USB glitch, a read spike, an exposure ramp | in **one frame, at all places** | a robust estimator **across frames** |

Averaging 150 frames does nothing at all to a hot pixel — it is in all 150. Averaging down the rows
does nothing to a glitched frame — it is in all rows. Spectracs therefore runs **both**, in that
order (§3.7, §3.8).

→ Background: [KB 3 — Robust statistics: median, MAD, sigma clipping and the Tukey biweight](#kb-3-robust-statistics-median-mad-sigma-clipping-tukey-biweight)

### 2.6 The lamp — what a "white" LED spectrum really is

The reference lamp is a Yuji SunWave 6500 K high-CRI white LED. A white LED is not a white light
source in the physical sense: it is a **narrow blue pump chip** plus a **broad phosphor** that
converts part of that blue into everything else.

![The measured reference spectrum. The narrow spike near 474 nm is the blue pump chip itself; the broad hump is phosphor emission. The dip near 580 nm is the phosphor's own gap. This shape is not flat — and it does not need to be, because it appears identically in R and S and divides out.](tmp/lamp_spd_annotated.png)

Two practical consequences follow from that shape, and both were checked on real data:

- **The blue-pump spike is not an artefact of ours.** It is a genuine feature of the lamp at
  ~473 nm, and it is *steep*. It appears in the reference and in the sample alike, so it cancels:
  measured across the edge, absorbance is smooth (0.165 → 0.165 → 0.136) even though the raw
  reference jumps from DN 186 to 228. This is §2.4's first row, visible in the data.
- **The red end is dim.** Beyond ~640 nm the small S-mount optics roll off hard, so that region is
  unusable. This is a genuine hardware limit, not a processing choice, and it is why the pumpkin
  evaluation uses two pigment bands rather than three.

→ Background: [KB 6 — White LEDs, colour temperature and colour rendering](#kb-6-white-leds-colour-temperature-and-cri)

<!--PAGEBREAK-->

## 3. The decisions — what we do, and what led us there

Each section below follows the same shape: **the problem**, **what we measured**, **the decision**,
and **what it costs**. They are in pipeline order, not chronological order.

### 3.1 Capture resolution is pinned to 2592 × 1944

**The problem.** The camera can deliver several resolutions and will silently substitute the
nearest one it supports. The wavelength calibration — the polynomial mapping pixel column → nm — is
authored at one specific resolution. If capture and calibration disagree, every wavelength is
wrong, and *nothing downstream can detect it*: you still get a smooth, plausible-looking spectrum.

**What we measured.** A production capture was running at 1600 × 1200 while the stored calibration
had been authored at 2592 × 1944, because the backend requested 1920 × 1080 — a mode this camera
does not have. The evaluation bands were mapping to the wrong wavelengths, and the Q-band had
fallen off the frame entirely. The resolution was proven from physics: the reference peak sits at
normalised position 0.69, which is 572 nm (the phosphor peak) only if the frame is 2592 wide.

**The decision.** Pin capture to **2592 × 1944** — the highest mode with working exposure control,
and the resolution the existing calibration was authored at, so no recalibration was needed. Add a
**tripwire**: if the calibration's region of interest does not fit inside the delivered frame, warn
once and clamp, so the failure can never again be silent.

**What it costs.** A per-camera magic number, and slower ~1.5 fps bursts at 8 megapixels — which in
turn is what made all the exposure timing fragile (§3.5).

### 3.2 The grey value of a pixel is `max(R, G, B)`

**The problem.** The sensor is a colour sensor with a Bayer filter, but a spectrum needs *one*
number per pixel. Which one?

The original code used the standard broadcast luminance formula, `qGray = (11·R + 16·G + 5·B)/32`.
That is a **photometric** weighting: it models how bright a colour looks *to the eye*, which
deliberately under-weights blue by a factor of three. For a spectrometer this is exactly wrong. At
450 nm the blue-filtered photosites are the ones that actually saw the light; weighting them 5/32
throws most of the signal away.

**What we measured.** With `qGray`, the reference trace read ~25 in the blue against ~115 in the
green — yet the raw camera image of that same region was **vividly blue**. The blue channel was
strong; the *weighting* was suppressing it.

**The decision.** The grey value of a pixel is **`max(R, G, B)`** — the brightest channel, i.e. the
one whose colour filter matches the light actually falling there. It is *radiometric* rather than
photometric.

→ Background: [KB 5 — why a Bayer sensor makes `max` the physically right choice](#kb-5-how-a-colour-camera-sees-light)

**Why it is safe.** Any homogeneous reduction cancels in `T = S/R`, because at a given wavelength
the reference and the sample have the *same colour* and differ only in brightness. So the change
does not bias transmission, absorbance or colour at all. What it buys is **signal-to-noise in the
blue** — roughly a factor of six — which is what let the Soret band become a usable measurement.

> **An unexpected bonus, found much later.** `max()` is an *order statistic*: for any strictly
> increasing function `f`, `max(f(R), f(G), f(B)) = f(max(R, G, B))`, exactly. That means gamma
> decoding commutes with the channel combine — it can be applied before or after with identical
> results. Had we stayed on the weighted sum, it could not (the decode of a sum is not the sum of
> decodes). A decision taken for signal-to-noise reasons quietly removed a whole class of ordering
> bug. Medians share this property; averages do not.

### 3.3 The brightness law: decode with the **pure** 2.2 power law

*Status: designed and verified, not yet implemented. This section records the decision and the
evidence behind it.*

**The problem.** §2.2 established that our absorbances are compressed by ≈ 1/2.2. The obvious fix is
to undo the camera's bend before doing any arithmetic. The question is which curve to undo it with —
§2.3's variant A or variant B — and whether doing so is safe for the pumpkin verdict.

**What we measured.** Every Spectracs report PDF embeds the complete workflow as JSON *and* both
full-resolution capture frames, so the entire pipeline could be replayed off-line at both the
spectrum and the pixel level. The replay reproduces the app bit-for-bit. Two oils measured in 2026,
plus the 32-run four-oil set from the capability proof, were re-processed under each candidate
decode.

**Result 1 — the verdict cannot be moved by a pure power law, at any exponent.**

| decode model | brown oil ratio | green oil ratio | verdict | perceived chroma | absorbed hue |
|---|---|---|---|---|---|
| as-is, no decode | **4.0591** | **5.1826** | red / green | 33.7 / 32.2 | 298.2° / 300.0° |
| pure power γ = 1.8 | 4.0591 | 5.1826 | red / green | 41.6 / 40.8 | 298.2° / 300.0° |
| pure power γ = 2.2 | 4.0591 | 5.1826 | red / green | 43.9 / 43.5 | 298.2° / 300.0° |
| pure power γ = 2.6 | 4.0591 | 5.1826 | red / green | 45.9 / 45.9 | 298.2° / 300.0° |
| true sRGB (with toe) | 3.6362 | 4.7391 | red / green | 43.5 / 42.7 | 292.8° / 296.8° |

Bit-identical to fifteen significant digits at every exponent — not "close", *identical*. The
absorbed colour is equally invariant, because chromaticity is computed after luminance has been
divided out, and a uniform scale changes only luminance. **Corollary for a fleet of cameras:** the
condition is "*a* pure power law", not "2.2 exactly", so pigment ratios from cameras with different
gammas are already directly comparable today. Only *absolute* absorbance and colour need the decode.

**Result 2 — the piecewise sRGB curve is worse for us, and was declined.** The toe rescales the
Soret band (440–460 nm) by a *sample-dependent* amount, because a browner, darker oil has more of
its band below the knee (17.4 % of bins) than a greener one (4.3 %). A non-uniform, sample-dependent
rescale of the numerator is precisely what a ratio cannot absorb:

| | | as-is | **pure 2.2** | true sRGB |
|---|---|---|---|---|
| 2026 pair | ratio gap | 1.123 | **1.123** | 1.103 (−1.8 %) |
| 32-run proof set | ratio gap | 1.277 | **1.277** | 1.156 (−9.5 %) |
| | within-group scatter (green) | 0.134 | **0.134** | **0.201** (+50 %) |
| | **separation ÷ noise** | **10.39** | **10.39** | **7.87 (−24 %)** |
| | colour gain (perceived chroma) | 29.1 | **40.6** | 39.9 |

The physically more faithful curve costs a quarter of the class separation and buys no measurable
colour improvement.

**The decision.** Decode with `light = (DN/255)^2.2`, applied **per channel, as the very first
operation on pixel values** — before the channel combine, before any averaging. The piecewise sRGB
EOTF is **deliberately declined**; this is an operational choice over a physical one, recorded so
that a later reader does not "correct" it toward the standard and silently lose the separation.

**Why "first" matters, by argument rather than by test.** The camera has *already* applied its bend
before we see anything, so undoing it must precede everything we do. `max()` and medians commute
with the decode exactly (§3.2); the two **averages** — Tukey and the sigma-clipped mean — do not,
because `mean(x)^γ ≠ mean(x^γ)`. Decoding first makes that gap zero by construction rather than
small by measurement. (Measured, had we got it wrong: 0.08–0.20 % on the ratio.)

**What it costs, and why we do it anyway.** It changes nothing about the verdict — that is the
point. The gains are a **+33 to +40 % increase in perceived colour chroma**, physically real
absorbance values, and cross-camera comparability of absolute numbers. But the real motive is
**closure**: we *know* the camera is non-linear, so as long as the assumption stays in the
pipeline, "maybe it's the gamma" remains a suspect for every future anomaly. Removing it retires
that suspicion permanently.

> **One thing must ship in the same change.** The colour code clamps absorbance at 3.0 before
> computing a colour, to stop a near-opaque wavelength from dominating the calculation. Today
> absorbance peaks at 1.3–1.6 and the clamp never fires. Decoding roughly doubles absorbance, so the
> clamp would begin cutting real signal. It must be raised to 6.6 at the same time.

→ Background: [KB 7 — From a spectrum to a colour: CIE XYZ, chromaticity, hue and chroma](#kb-7-from-a-spectrum-to-a-colour)

### 3.4 Auto-exposure: a direction-agnostic sweep on the channel peak

**The problem.** The exposure must be set so that the brightest wavelength is close to, but not at,
saturation — and then **locked**, because an exposure that differs between reference and sample is
a multiplicative error that does *not* cancel (§2.4).

**What we measured — three separate traps.**

1. **The camera's exposure control is inverted.** On this ELP module a *lower* exposure value gives
   a *brighter* image, and above roughly 16 the response flattens entirely. The original algorithm
   was a bisection that assumed brightness rises with the setting, so it drove straight to the
   extreme and picked the most clipped image available.
2. **You cannot measure exposure by watching the live video stream.** Frames arrive asynchronously,
   and a UVC exposure change takes a fixed wall-clock time to take effect. Reading the stream after
   a change returns frames from *before* it. At 8 megapixels the camera runs at 1–2 fps, which
   stretched the ramp to ~1.5 s and made every frame-counting scheme fail.
3. **Averaging hides clipping.** A luminance metric averages a clipped green channel together with
   an unclipped red one and reports a comfortable value while green is pinned at 255.

**The decision.**

- Metric = **channel peak**: the 99.9th percentile of `max(R, G, B)`, targeted at **245**. Working
  on the per-channel maximum *guarantees* no channel is saturating, which a luminance average
  cannot.
- Search = a **direction-agnostic sweep** (coarse ladder, then bisection on the sign of
  "above/below target"), which makes no assumption about which way the control runs. The lowest
  exposure value is excluded as a UVC artefact.
- Measurement is **synchronous, inside the video thread**: set the exposure, actively drain and
  discard frames for a settle period, *then* read. Never off the async stream.
- The chosen exposure is then **locked** and reused for the sample capture.

**What it costs.** An exposure sweep takes several seconds at 8 megapixels. The upper search bound
is still a hard-coded 500, which is not meaningful across camera models — a known open item (§6).

### 3.5 Settling: wait until the picture stops changing, don't count frames

**The problem.** After an exposure change the camera does not jump to the new brightness — it
*ramps* over roughly a second, and the ramp is neither instant nor of predictable length. Frames
captured during the ramp are systematically too dark.

**What we measured.** The original code discarded a single frame and waited a fixed 1.8 s. That
constant was measured for one camera at one resolution, and it silently failed elsewhere. Worse, an
early "adaptive" attempt read the *channel peak*, which plateaus as soon as the brightest pixels
saturate — while the rest of the frame is still ramping. It declared success early, in the flat part
of the curve, and let dim frames through.

**The decision.** Settle **adaptively on a quantity that does not plateau**: the mean brightness of
the brightest channel over the whole frame. Drain frames in 200 ms chunks until **three consecutive
reads agree within 1 %**, with a floor of 1500 ms (never declare success before the known latency
plateau) and a ceiling of 4000 ms (a never-settling ramp must not hang the app).

**What it costs.** Up to four seconds before a burst. In exchange, the timing constant stops being a
per-camera magic number.

### 3.6 Warm-up: the camera heats itself

**The problem.** Even with the lamp constant, exposure locked and white balance frozen, the
reference measured at the start of a session and the reference measured ten minutes later were not
the same shape.

**What we measured.** The channel balance — red divided by green — drifts as a clean single
exponential from the moment the camera is opened. Overall brightness stays pinned (the exposure
holds it); only the *shape* moves. This is **sensor self-heating**: as the die warms, the
per-wavelength sensitivity of the channels drifts, red being the most temperature-sensitive.

![Camera sensor self-heating at fixed exposure. The red/green ratio of the reference follows A − B·e^(−t/τ) with a time constant of 171 s, a total shape change of 1.68 %, and full settling after about nine minutes.](tmp/sensor_warmup_curve.png)

| quantity | value |
|---|---|
| time constant τ | **171 s (2.9 min)** |
| total shape change | **1.68 %** (red/green 0.682 → 0.694) |
| 90 % / 95 % settled | 6.6 min / 8.5 min |
| indistinguishable from equilibrium | **≈ 9 min** |

**Why it bites harder than it looks.** The camera is opened and released around each capture. So a
session typically opens the camera *cold*, captures the reference in the first seconds — on the
steepest part of the curve — and then the sample thirty to sixty seconds later, while it is still
warming fast. The reference-to-sample drift is therefore close to its worst case, and it resets
every session.

**The decision — recorded, not yet enforced.** The diagnosis and the curve are established; the
remedy (hold the capture button until the shape stabilises, or keep the camera warm across the
session) is designed but deliberately not built. In the meantime the operational rule is simply:
**let the camera run for a few minutes before the reference**, and capture the reference and the
sample close together.

> Note that this drift is a *shape* change, not a brightness change, and it therefore does **not**
> cancel in `T = S/R` — the reference and sample see different channel balances. It is the largest
> uncorrected error left in the instrument, at about 1.7 % on the reference shape.

### 3.7 Spatial reduction: a Tukey biweight down the slit

**The problem.** Each wavelength column contains many pixel rows — the height of the illuminated
slit. The original code read a single centre row, which meant one hot pixel or one dust speck
corrupted that wavelength permanently. But a plain average over the rows is no better: a single
stuck-at-255 pixel drags the whole column.

**The decision.** Reduce each column with a **Tukey biweight** — a robust average that weights each
row by how far it sits from the column's median, smoothly dropping to zero weight beyond 6 median
absolute deviations. Two refinement passes.

Two details matter as much as the estimator:

- **Saturated and dead pixels are masked *before* the reduction**, and masked **per channel** —
  saturation is a per-channel fact, so it has to be detected before the channels are combined.
- **The outer 20 % of rows are dropped** (top and bottom). Edge rows bleed the dark border outside
  the slit and carry the worst optical "smile" distortion. The measurement is broadband, so a
  generous central band costs nothing.

**Why a biweight and not a median.** The number of rows is modest, and a median throws away most of
the averaging benefit. The biweight keeps the noise reduction of a mean while still discarding a
genuine outlier — the right trade at small sample counts.

→ Background: [KB 3 — breakdown point, why MAD is scaled by 1.4826, and when each estimator wins](#kb-3-robust-statistics-median-mad-sigma-clipping-tukey-biweight)

### 3.8 Temporal reduction: reject dim frames, then a sigma-clipped mean

**The problem.** A burst of 150 frames is averaged to beat down noise. A plain mean is fine until
one frame is bad — and worse, until a *group* of frames is bad in the same direction.

**What we measured.** Reference spectra showed a systematic downward bias that the sample spectra
did not have. The cause: the reference capture runs an auto-exposure sweep immediately before its
burst (the sample reuses the locked exposure), and the exposure ramp left the **first several frames
of the reference burst systematically dim**. A per-wavelength sigma-clip cannot reject that: with a
sizeable minority all dim in the same direction, the per-bin spread inflates and the mean is dragged
toward them rather than away.

**The decision — two stages, because they catch different things.**

1. **Reject dim frames as whole frames.** Compute one brightness scalar per frame, then reject
   frames whose brightness is a median-absolute-deviation outlier against the median frame — with a
   floor of 2 % so that a pathologically tight cluster of clean frames does not over-reject, and a
   blatantly dim frame cannot hide behind it. Judging the *whole frame* on a single scalar is what
   makes the coherent dim group obvious; the 50 % breakdown point of the MAD is what makes it
   rejectable even when it is large. Symmetric, so a bright flare frame goes too.
2. **Then a sigma-clipped mean per wavelength.** Iteratively drop samples beyond 3σ (σ estimated
   robustly from the median absolute deviation), then average the survivors — keeping the full √N
   benefit while a single glitched value is discarded.

Additionally the burst **tops itself up**: it grabs until *N surviving* frames are collected rather
than N grabbed, so rejection does not quietly reduce the average's depth.

→ Background: [KB 4 — why averaging N frames buys √N, and what it cannot buy](#kb-4-digital-numbers-quantisation-and-noise)

**What it costs.** Bookkeeping, and a slightly longer burst. It removed a real bias in the
reference, which is the one spectrum every result divides by.

### 3.9 White balance: frozen for measurement, automatic for calibration

**The problem.** Automatic white balance continuously rescales the R, G and B channels. Between a
reference and a sample capture that is a *per-channel multiplicative change*, which breaks the
premise of §2.4 — it no longer cancels, because it is not the same factor in both.

**What we measured.** After the dim-frame work, a residual reference-only anomaly remained, and the
lamp was demonstrably constant. The cause was that opening the camera left **automatic white balance
and backlight compensation switched on**. They re-converge after every exposure change, and the
reference burst — which follows an exposure sweep — catches them mid-convergence.

**The decision — split by use case, because the two uses need opposite things.**

| use | white balance | why |
|---|---|---|
| **measurement** (reference, sample) | **fixed at 6500 K** | matches the 6500 K lamp; frozen, so it is identical in R and S and cancels exactly |
| **calibration** (mercury / europium lines) | **automatic** | line identification keys on the *colour* of each emission line; auto-WB is what the historical, working calibration used |

Gain and backlight compensation are pinned off in both cases; a fixed frame-buffer depth of one is
also set, so a capture never receives a stale queued frame.

**What it costs.** Two code paths where a naive design would have one — justified because the two
uses genuinely have opposite requirements.

### 3.10 Dark frames: we measured, and they were black

**The problem.** §2.4's table says any *additive* offset — sensor black level, dark current, stray
light — survives the division and biases transmission toward 1, worst exactly where the signal is
weakest. Textbook practice is to capture a dark frame and subtract it.

**What we measured.** 150 dark frames at the longest available integration time (the worst case for
dark current), analysed over the region of interest:

| quantity | result | interpretation |
|---|---|---|
| black level | **0.00 % of full scale** | no pedestal — true black really is 0 |
| saturated pixels | 0 % | — |
| hot pixels in the region of interest | ~10 | few, and fixed in place |

**The decision.** **Do not implement dark-frame subtraction.** The offset it would remove is not
measurably present, and the ~10 hot pixels are already handled by the spatial Tukey estimator
(§3.7), which is designed for exactly that failure. A per-pixel bad-pixel map was dropped for the
same reason.

**Why the measurement was worth doing anyway.** It converted an assumption into a fact, and it is
now load-bearing elsewhere: gamma decoding (§3.3) assumes true black is 0. Had there been a
pedestal of 8 or 16 DN, decoding without subtracting it would have swung the pigment ratio by −12 %
to +13 % — a *larger* effect than gamma itself. We can decode safely **because** this was measured.

> This is the clearest example in the project of Edwin's standing rule: **measure first, then
> decide.** The measurement's outcome was "do nothing", and that is a perfectly good outcome — it
> is what makes "do nothing" defensible rather than lazy.

### 3.11 The wavelength window: 440–630 nm, declared by the plugin

**The problem.** The camera sees more than the instrument can trust. Below ~440 nm and above
~630 nm the lamp is weak and the small S-mount optics roll off, so those regions contribute noise
dressed as data.

**The decision.** The evaluation plugin **declares** the wavelength window it needs and the bands it
will read; the host hard-clamps the captured region of interest to that window. The plugin also
asserts at construction time that its window covers every band it declares — so a mismatch fails
loudly at start-up rather than silently producing a spectrum with a missing band.

**What it costs.** Nothing, and it inverts the dependency correctly: the science declares what it
needs, the capture layer obeys.

### 3.12 Sample presentation: keep the signal out of the floor

**The problem.** This is a *lab* parameter, not a code parameter, but it belongs here because it
determines whether the capture chain has anything to work with. If the sample is too concentrated,
the transmitted light at the strongest absorption band falls to a handful of DN, where quantisation
is coarse and the camera's toe (§2.3) is at its least trustworthy.

**What we measured.** The 2026 oils are fresher and absorb considerably more than the aged 2023
oils used for the original validation. At the old strength (2 drops in 4 ml, ≈ 1:20), the sample
bottoms out at **DN 5 of 255** at 440 nm — 17 % of the Soret band sitting in the toe. The oil is
effectively opaque there.

**The decision.** Dilute more. Simulated on the measured spectra, the minimum acceptable strength is
about **1:27**; the working recipes are **1:30 or 1:33**:

| dilution | lowest sample DN at 440 nm (brown / green) | assessment |
|---|---|---|
| 1:20 (old) | 5 / 10 | too dark — 17 % of the band in the toe |
| 1:27 | 12 / 20 | the minimum that clears it |
| **1:30** — 6 ml + 2 drops | **16 / 25** | comfortable |
| **1:33** — 10 ml + 3 drops | **21 / 31** | comfortable, more headroom |

**Why this is safe to change mid-series.** The pigment ratio moves by **± 0.35 %** across every
dilution simulated, against an 8.7 % run-to-run spread. That is dilution-invariance doing its job:
the recipes are interchangeable, the verdict threshold is unaffected, and older runs stay
comparable.

**A practical point worth stating plainly.** The *transfer* volume does not matter. The measurement
sees the solution's concentration and the pot's fixed path length; how many millilitres are poured
in is irrelevant as long as the light path is filled. Only the **batch concentration** needs care —
which is why the recipe is "prepare a batch at a known concentration, then simply fill the pot",
and why a larger batch (more drops, proportionally more solvent) is the cheapest way to improve
precision: half a drop out of two is ±25 %, out of six it is ±8 %.

And the one instruction that genuinely matters at the bench: **dissolve it properly.** Turbidity is
additive (§2.4) and does not cancel — a cloudy sample reads as absorption that is not there.

→ Background: [KB 2 — dilution invariance, and the assumptions it rests on](#kb-2-the-beer-lambert-law-and-the-algebra-of-ratios)

<!--PAGEBREAK-->

### 3.13 The jar, and the sample's own turbidity

*Added 2026-07-31. Everything before this section is about the instrument. This one is about the two
things in front of it — the vessel and the liquid — which together turned out to dominate the error
budget more than anything downstream of the grating.*

**The mechanical half — measured, and fixed.** Absorbance is a ratio of two captures taken minutes
apart with the jar lifted out and put back between them. Any change in how the jar sits changes the
path through it, and that enters absorbance as an **offset *and* a slope**, not merely a level. A
dedicated re-seating probe attributed the bulk of the run-to-run scatter to that one joint.

A rebuilt seat and a marked-line fill protocol then cut it:

| | before | after |
|---|---|---|
| jar re-seat tilt | 2.84 % | **1.34 %** |
| metric CV, one fill re-seated | 9.7 % | **2.9 %** |

**That was the single largest fidelity improvement in the project**, and it is worth noting *what
kind* of improvement it was: not an algorithm, not a calibration — a printed part and a filling
habit.

**And a caveat found immediately afterwards.** Of that remaining 2.9 %, roughly **58 % is not
seating at all** but a slow drift while the freshly-mixed dilution settles. Removing the time trend
leaves a true seat-to-seat repeatability of about **1.9 %**. The mechanical work therefore
over-delivered on its own terms — and handed the top of the error budget to the chemistry.

**The chemical half — measured, not yet fixed.** A few drops of oil in isopropanol is **not a
solution**. The two are only partially miscible, so what forms is a cloudy dispersion of oil
droplets and never-soluble waxes. Scattered light does not reach the detector, so the instrument
records it as absorbance: a broad additive floor under the whole curve, the **pedestal**.

It is not small. Measured across eight fills, the pedestal runs **0.7 – 1.9 × the pigment signal in
the Q band** — the plinth is bigger than the thing standing on it. And because the metric is a
*ratio*, adding the same amount to numerator and denominator drags it toward 1:

```
true       12.37 / 1.00                    = 12.37
measured  (12.37 + 1.59) / (1.00 + 1.59)   =  5.39
```

That compression is the entire difference between the two pigment-ratio rows in the report, and the
reason a baseline correction exists at all.

**How much it costs, from an accident.** Oils bought in 2023 and measured in 2026 had three years to
clarify in the bottle. They carry **half** the pedestal of fresh oils — and they separated the two
quality classes about **8× better**. Nobody designed that experiment; the shelf did. It makes sample
clarity a **first-class instrument parameter**, and it is currently the largest known lever left.

**One consequence for handling.** The batch is mixed in a lab glass and a 4 ml aliquot is
transferred to the jar — so the transfer is a **sampling step out of a dispersion that is
sedimenting the whole time**. How much particulate travels with the aliquot depends on when and from
what depth it was drawn. Homogenise before drawing, or clarify after; doing neither leaves a large
sample-to-sample variable that is invisible in the finished spectrum.

> **Background.** The miscibility gap, the ouzo effect, why the droplets sediment rather than cream,
> the solvent-selection table and the vessel constraints are treated properly in
> `KB_spectroscopy_physics.md` §8. The open work is owned by `SPEC_capture_quality.md` §16.12 and
> `SPEC_capability_proof.md` §11.4e–f.

<!--PAGEBREAK-->

## 4. What we deliberately did not do

An engineering record is only useful if it also says what was considered and rejected, and why.
Everything in this table was examined seriously.

| not done | why not |
|---|---|
| **Sensor quantum-efficiency / blackbody-lamp calibration** | This is the standard recipe for *absolute* spectroscopy, where there is no reference. We measure `T = S/R`, and the sensor's response and the lamp's spectrum are common factors in both — they cancel exactly (§2.4). Measuring them would re-solve a problem the reference already solves. |
| **OECF characterisation** (mapping the camera's true response curve by stepping exposure) | Would refine the gamma model beyond the standard assumption. Ruled out of scope: the decision that depended on it (§3.3) resolved without it, and the pure power law is verdict-neutral regardless of the true exponent. |
| **The piecewise sRGB EOTF** (in favour of the pure 2.2 power law) | More physically faithful, and measurably worse for us: −24 % class separation, no colour gain (§3.3). Declined on evidence, not on convenience. |
| **Dark-frame subtraction** | Measured at 0.00 % of full scale — the offset it would remove is not there (§3.10). |
| **A per-pixel bad-pixel map** | ~10 hot pixels, already absorbed by the spatial Tukey estimator (§3.7). |
| **Spectrum normalisation** | `T = S/R` already self-normalises against the lamp, and exposure is locked across the pair. A further constant scale would cancel in every ratio and bias only absolute absorbance. Documented as a deliberate no-op. |
| **Shifting the Soret band to 450–470 nm** (to escape the toe) | Tested on 32 runs: costs 25 % of the discriminating power, because the steep flank being abandoned *is* the pigment signal. The real fix was the sample, not the band (§3.12). |
| **Trimming the band to 442–460 nm** | Genuinely the best-scoring variant (+4 %), but small, and it would force a threshold recalibration. Recorded with its price so it can be picked up if a margin ever tightens. |

<!--PAGEBREAK-->

## 5. As-built settings

Every value the capture chain depends on, in one place. Values marked **†** are per-camera and would
need revisiting on different hardware.

| stage | setting | value | §|
|---|---|---|---|
| camera | capture resolution † | 2592 × 1944 | 3.1 |
| camera | frame buffer depth | 1 (always the newest frame) | 3.9 |
| camera | analogue gain | 0 (off) | 3.9 |
| camera | backlight compensation | off | 3.9 |
| camera | white balance — measurement | fixed, 6500 K | 3.9 |
| camera | white balance — calibration | automatic | 3.9 |
| auto-exposure | metric | 99.9th percentile of `max(R,G,B)` | 3.4 |
| auto-exposure | target | 245 of 255 | 3.4 |
| auto-exposure | search range † | 2 … 500, direction-agnostic sweep | 3.4, 6 |
| settle | chunk / minimum / maximum | 200 ms / 1500 ms / 4000 ms | 3.5 |
| settle | stability criterion | 3 consecutive reads within 1 % | 3.5 |
| warm-up | time constant / practical wait | 171 s / ≈ 9 min | 3.6 |
| pixel | grey value | `max(R, G, B)` | 3.2 |
| pixel | gamma decode (designed) | `(DN/255)^2.2`, per channel, first | 3.3 |
| spatial | estimator | Tukey biweight, c = 6·MAD, 2 passes | 3.7 |
| spatial | rows used | central 60 % (20 % dropped each edge) | 3.7 |
| temporal | burst length | 150 frames, topped up to 150 survivors | 3.8 |
| temporal | dim-frame rejection | MAD, k = 3, 2 % scale floor, ≥ 5 frames | 3.8 |
| temporal | averaging | sigma-clipped mean, k = 3, ≤ 5 passes | 3.8 |
| window | wavelength range | 440 – 630 nm, plugin-declared | 3.11 |
| sample | dilution | 1:30 (6 ml + 2 drops) or 1:33 (10 ml + 3 drops) | 3.12 |
| sample | solvent | isopropanol, ≥ 99.8 %, fresh bottle | 3.13 |
| sample | equilibration after mixing | ≈ 15 min | 3.13 |
| vessel | jar re-seat tilt, as rebuilt | 1.34 % *(was 2.84 %)* | 3.13 |
| lamp | reference source | Yuji SunWave 6500 K, high-CRI white LED | 2.6 |

## 6. Known open items

Recorded honestly; none of these blocks a measurement today.

- **Sensor warm-up is diagnosed but not handled** (§3.6). At ~1.7 % on the reference shape this is
  the largest uncorrected error in the instrument. The remedy is designed; a warm-camera habit is
  the current mitigation.
- **The auto-exposure upper bound of 500 is hard-coded** (§3.4). Exposure units differ wildly
  between camera models, so this is not portable. It belongs with the other per-sensor values.
- **Gamma linearisation is designed and verified but not implemented** (§3.3). Verdict-neutral, so
  there is no urgency; the motive is closure.
- **The temporal half of the decode-order check is argued, not measured** (§3.3) — the individual
  burst frames are not persisted, only their mean. One instrumented bench run would settle it.
- **The new dilution protocol is predicted, not yet confirmed on the rig** (§3.12). One oil measured
  at both the old and the new strength would verify the invariance directly.
- **Prep noise and instrument noise are now partly separated** (§3.13) — the rebuild took the
  re-seat spread to 2.9 %, of which ~58 % is settling drift rather than seating. What remains
  unmeasured is **fill-to-fill** noise: several fills from one batch, which is what gives the
  quality threshold its first real error bar. Owned by `SPEC_capability_proof.md` §11.4f.
- **Everything about the brown oil post-rebuild is projection** (§3.13). The mechanical work was
  verified on green only; brown has not been measured since. Pre-rebuild the two classes had
  *identical* noise, which is why the fix is expected to transfer — but expected is not measured.
- **The sample's turbidity is the largest known remaining lever and nothing has been done about it**
  (§3.13). Three candidate routes exist — a better solvent (1-butanol), a 0.22 µm filter, or simply
  a fresher solvent bottle — and none has been tried. Owned by `SPEC_capture_quality.md` §16.12.
- **The far baseline anchor is not what it was documented to be.** The 600–630 nm window was
  described as oil-quiet; it carries real chlorophyll absorption and a substantial share of the
  discrimination rests on it. The metric works, but the explanation attached to it has been
  rewritten — `SPEC_capability_proof.md` §2.1a.
- **The class threshold rests on four oils.** Precision is close to solved; whether the threshold
  divides good from over-roasted oil *in general* is a panel question no amount of precision can
  answer. This is the binding constraint on the claim, not the instrument.

## Appendix A — Knowledge base

*Background for the topics the main text uses but does not stop to explain. Each entry stands on its
own and can be read in isolation. Nothing here is specific to Spectracs unless it says so.*

### KB 1 — The brightness law (gamma) in depth

**Where it comes from.** Two unrelated facts converged. First, a cathode-ray tube's brightness
responds to grid voltage as roughly `voltage^2.5` — a physical accident of electron optics. Second,
human brightness perception is approximately a power law with an exponent near 0.4, i.e. close to
the *inverse*. Encoding images with `^(1/2.2)` therefore did two jobs at once: it pre-compensated
the CRT, and it happened to store brightness in perceptually uniform steps. CRTs are long gone; the
second reason is why the encoding stayed.

**Why perceptual coding matters in 8 bits.** The eye can distinguish roughly a 1 % change in
brightness. Store light linearly in 256 steps and the step from 1 to 2 is a **100 %** jump —
grossly visible banding — while the step from 200 to 201 is 0.5 %, finer than anyone can see. Half
the code values are wasted at the top and there are far too few at the bottom. Bending the scale
before quantising spreads the code values where the eye needs them. Linear 8-bit imaging is simply
not viable; you would need about 12 bits to match what 8 bent bits achieve.

**Terminology.** The curve has direction-dependent names:

| term | meaning |
|---|---|
| **OETF** — opto-electronic transfer function | light → stored value. What the **camera** applies (the *encode*). |
| **EOTF** — electro-optical transfer function | stored value → light. What the **display** applies (the *decode*). This is the one we implement in software. |
| **gamma (γ)** | loosely, the exponent of either. "Gamma 2.2" conventionally means the *decode* exponent. |
| **linear light** | values proportional to photon count. What physics needs and what a camera does not give you. |

**The exact sRGB functions** (IEC 61966-2-1). With `L` = linear light and `V` = stored value, both
normalised to 0…1:

```
  encode (OETF)              L ≤ 0.0031308  ->  V = 12.92 · L
                             L >  0.0031308  ->  V = 1.055 · L^(1/2.4) − 0.055

  decode (EOTF)              V ≤ 0.04045    ->  L = V / 12.92
                             V >  0.04045    ->  L = ((V + 0.055) / 1.055)^2.4
```

**Why 2.4 yields "2.2".** Three ingredients combine: the exponent 2.4, the scale-and-offset
`(V + 0.055)/1.055`, and the linear segment at the bottom. The offset flattens the curve
considerably, and the linear segment flattens it further near black. The *composite* curve tracks a
pure `V^2.2` closely across most of the range. Neither 2.2 nor 2.4 describes the whole function
exactly — 2.2 describes its behaviour, 2.4 is a construction parameter.

**The toe, and why it exists.** A pure power curve has infinite slope at the origin in the encode
direction: as light approaches zero, an ever smaller change in light produces the same change in
stored value. In a quantised, noisy system that is catastrophic — the darkest codes would represent
immeasurably small light differences, and decoding would amplify sensor noise without bound. The
standard therefore caps the slope at a finite 12.92 and splices a straight line below the knee
(`V = 0.04045`, i.e. **DN ≈ 10** of 255). That region is the **toe**. It is the only place the two
variants differ meaningfully — and, for a spectrometer measuring a strongly absorbing sample, it is
exactly where the interesting measurement can end up.

**The classic pitfalls.** Any arithmetic on encoded values is wrong unless it is linear-preserving:

- **Averaging or resizing in gamma space** darkens the result — the canonical demonstration is that
  scaling down a black-and-white checkerboard should give mid-grey and instead gives something much
  darker.
- **Alpha blending and lighting** in gamma space produce the muddy transitions familiar from older
  software.
- **Ratios** — our case. `S/R` on encoded values yields `T_true^(1/γ)`, not `T_true`. Absorbance
  comes out compressed by `1/γ`. Because that is a *uniform* factor, band ratios are unaffected —
  which is the single reason our verdict survives untouched.

**How to tell whether data is encoded.** Photograph a scene with a known 18 % grey card. If the card
reads near DN 118 the data is gamma-encoded; if it reads near DN 46 it is linear. Webcams, JPEG,
PNG and anything intended for a screen are encoded by default. Machine-vision cameras and camera
RAW files are linear.

<!--PAGEBREAK-->

### KB 2 — The Beer-Lambert law and the algebra of ratios

**The law.** For a dissolved absorbing substance,

```
  A(λ)  =  ε(λ) · c · l
```

where `A` is absorbance, `ε(λ)` the molar extinction coefficient — a property of the *substance*,
varying with wavelength — `c` the concentration and `l` the path length through the liquid.
Absorbance relates to what is measured by `A = −log10(T)`, `T = S/R`.

**Why absorbance and not transmission.** Absorbance is **linear in concentration**; transmission is
exponential. Double the concentration and absorbance doubles, while transmission squares. Every
useful quantitative statement is therefore made in absorbance space, and this is why the pipeline
converts as early as it can.

**The algebra that makes a band ratio invariant.** Take two wavelength bands and their mean
absorbances `A₁` and `A₂`. Beer-Lambert gives `A₁ = ε₁·c·l` and `A₂ = ε₂·c·l`, so

```
  A₁ / A₂  =  ε₁ / ε₂
```

The concentration and the path length **cancel identically** — the ratio depends only on the
substance's own extinction spectrum. Everything that multiplies absorbance uniformly disappears the
same way: sloppy pipetting, a different pot, a different gamma exponent, an overall gain change.
This is a strong result and it is why the pumpkin verdict is a *ratio* rather than a level.

**Where it stops holding.** The law is an idealisation, and four things break it:

- **Stray light.** Any light reaching the sensor without passing through the sample adds a floor.
  It caps the measurable absorbance and pulls high readings down.
- **Too much absorbance.** Above roughly `A = 2` (1 % transmitted) the measurement is dominated by
  noise and stray light, and the relationship flattens. Practical working range is about
  `A = 0.1 … 1.5`.
- **Scattering / turbidity.** An undissolved or cloudy sample removes light by scattering rather
  than absorption. It is broadly wavelength-dependent, **additive**, and indistinguishable from real
  absorption in a single measurement. This is why "dissolve it properly" is the one lab instruction
  that genuinely matters.
- **Chemical interaction.** At high concentration molecules interact and `ε` itself changes. Not a
  concern at our dilutions.

**Why the ratio still needs the level to be sane.** Invariance to concentration is not permission to
use any concentration. If the sample is so strong that a band falls into the noise or the camera's
toe, the *inputs* to the ratio are corrupted before the algebra begins. Dilution invariance holds
across the range where both bands are well measured — which is exactly the range the dilution
protocol is chosen to guarantee.

### KB 3 — Robust statistics: median, MAD, sigma clipping, Tukey biweight

**The problem with the mean.** The arithmetic mean has a **breakdown point of zero**: a single
arbitrarily wrong value moves it arbitrarily far. The standard deviation is worse — an outlier
inflates it, which then makes the outlier look acceptable. Any estimator built on mean-and-SD is
therefore self-defeating in the presence of the very outliers it is meant to handle.

**Median — breakdown point 50 %.** Up to half the values can be arbitrarily wrong before the median
moves. The cost is *efficiency*: for clean, normally distributed data the median is only ~64 % as
efficient as the mean, i.e. it needs about 1.5× as many samples for the same precision. Excellent
protection, poor use of good data.

**MAD, and the 1.4826.** The robust counterpart of the standard deviation is the **median absolute
deviation**, `MAD = median(|xᵢ − median(x)|)`. For normally distributed data `MAD ≈ 0.6745 σ`, so it
is conventionally scaled by `1 / 0.6745 = 1.4826` to make it directly comparable to a standard
deviation. That factor is the only reason the number appears in the code; it carries no other
meaning.

**Sigma clipping.** Iteratively: compute a robust centre and scale (median and MAD·1.4826), discard
everything beyond `k·σ` (typically `k = 3`), repeat until nothing more is discarded, then take the
plain **mean of the survivors**. This gets the best of both — the median's resistance for the
*decision*, the mean's efficiency for the *estimate*. It is the standard reduction in astronomical
imaging, and it is what Spectracs uses across frames.

**Tukey biweight.** Instead of a hard in/out decision, weight each sample by how far it lies from
the centre, with the weight falling smoothly to exactly zero beyond a cutoff:

```
  u = (x − centre) / (c · MAD)
  w = (1 − u²)²   for |u| < 1,   otherwise 0          typically c = 6
```

Being *redescending* — weight zero, not merely small, far out — it fully discards a genuine outlier
while still using the information in every good sample. That makes it the better choice when the
sample count is **small**, which is why Spectracs uses it across the ~500 rows of a column while
using sigma clipping across the 150 frames.

**Judging a group, not a point.** All of the above assume outliers are *independent*. If a coherent
group of values is wrong in the same direction — for example the first frames of a burst, all dim
because the exposure was still ramping — per-point rejection fails: the group inflates the estimated
spread, which then accommodates it. The cure is to move up a level and judge each *frame* on a
single summary scalar. With MAD's 50 % breakdown point the dim group becomes obvious as a group,
even when it is large. This is exactly the reasoning behind §3.8's two-stage design.

### KB 4 — Digital numbers, quantisation and noise

**DN.** A *digital number* is simply the integer a pixel reports — here 0…255. It is not photons,
not lux, not anything physical. Two cameras reporting DN 100 need not have received the same light.

**Quantisation error.** Rounding to an integer costs up to ±0.5 DN. What matters is that this is an
**absolute** error against a **relative** measurement:

| signal | quantisation error | relative |
|---|---|---|
| DN 200 | ±0.5 | ±0.25 % |
| DN 50 | ±0.5 | ±1 % |
| DN 10 | ±0.5 | ±5 % |
| DN 5 | ±0.5 | **±10 %** |

A measurement that lands at DN 5 is intrinsically a 10 % measurement, whatever else you do. This is
why "keep the signal off the floor" (§3.12) is a fidelity requirement and not merely tidiness.

**Photon shot noise.** Light arrives as discrete photons, and their count fluctuates with a Poisson
distribution: collect `N` photons and the noise is `√N`. Relative noise is therefore `1/√N` — bright
signals are *relatively* quieter than dim ones, independently of the camera's quality. Combined with
quantisation, this means the dark end of a spectrum is noisy for two separate reasons at once.

**What averaging buys.** Averaging `M` independent frames reduces random noise by `√M`: 150 frames
give roughly a 12× improvement. But averaging is powerless against anything *systematic* —

- a hot pixel is identical in all frames (hence the spatial estimator, §3.7);
- a bias such as a black-level offset averages to exactly itself;
- a group of dim frames biases the mean rather than cancelling (hence §3.8's first stage).

`√M` also has diminishing returns: going from 150 to 600 frames buys a further factor of two for
four times the capture time.

**Noise amplification in absorbance.** Because `A = −log10(T)`, a relative error in `T` becomes an
*absolute* error in `A`: `δA ≈ 0.434 · δT/T`. At high absorbance `T` is small, so a fixed
signal-to-noise ratio in DN produces a growing error in `A`. This is the quantitative form of the
"stay below `A ≈ 1.5`" rule of thumb in KB 2.

### KB 5 — How a colour camera sees light

**The Bayer mosaic.** A sensor's photosites are colour-blind: they count photons across a broad
range. Colour comes from a physical filter grid bonded to the sensor — the **Bayer mosaic**,
typically one red, one blue and two green filters in each 2×2 cell (green is doubled because human
vision is most acute there). So every photosite measures exactly *one* colour channel, and two
thirds of the colour information at any location is missing by construction.

**Demosaicing.** The camera interpolates the missing channels from the neighbours, producing a
full-colour image. It is a guess, and it is tuned for photographs. On a spectrum image — where
colour changes smoothly and steeply along one axis — the interpolation smears slightly across
wavelengths. We cannot avoid it on a UVC camera; it is one reason the instrument's effective
resolution is somewhat below its pixel pitch.

**Quantum efficiency and why `max` is right.** Each channel has a broad response curve peaking near
450, 540 and 600 nm, overlapping heavily. In a spectrometer, each *column* of the image carries
essentially a single wavelength. At 450 nm the blue-filtered photosites are the ones actually
receiving light; the red ones are receiving very little and contributing mostly noise. Taking the
**maximum** of the three channels therefore selects the detector that saw the light, wavelength by
wavelength, with no calibration required. A luminance average would instead mix the signal with two
noisy channels — and a *photometric* average, weighted for the eye, deliberately suppresses blue
threefold, which for a spectrometer is precisely the wrong thing.

**White balance is per-channel gain.** "White balancing" multiplies the three channels by three
constants so that a neutral object reads neutral. Harmless in a photograph; hazardous in a ratio,
because if the constants change between two exposures they no longer cancel. Hence §3.9.

**UVC and its controls.** USB Video Class is the standard that lets a webcam work without a driver.
It exposes exposure, gain and white balance — but **the units are camera-specific**. An exposure
value of 100 means different things on different modules, the direction of the scale is not
guaranteed, and the usable range varies. This is why the auto-exposure algorithm must not assume a
direction (§3.4) and why the fixed upper bound of 500 is a known portability weakness.

### KB 6 — White LEDs, colour temperature and CRI

**A white LED is two things.** There is no LED that emits white. The overwhelmingly common
construction is a **blue pump chip** (typically 450–475 nm) coated with a **phosphor** that absorbs
part of that blue and re-emits it as a broad yellow band. Blue that escapes plus down-converted
yellow reads as white to the eye. The characteristic spectrum is therefore a **narrow spike** plus a
**broad hump**, with a **dip** between them where neither contributes — visible in the measured
reference in §2.6.

**Colour temperature (CCT).** The temperature in kelvin of the blackbody whose colour the source
most closely matches. Lower is warmer/redder (2700 K, incandescent), higher is cooler/bluer
(6500 K, daylight). It describes only the *colour*, and says nothing about the spectrum's shape —
two lamps of identical CCT can have wildly different spectra. For a spectrometer, CCT is close to
irrelevant; shape is everything.

**CRI, and why high CRI matters here.** The colour rendering index measures how faithfully a source
renders reference colours compared with a blackbody of the same CCT. A high-CRI lamp is one whose
spectrum has **no large gaps** — which is exactly the property a reference source needs. Any
wavelength where the lamp is weak is a wavelength where `T = S/R` divides a small number by a small
number and the result is noisy. A cheap low-CRI LED has a deep hole around 480 nm and a weak red
end; both would show up as noise bands in the transmission spectrum. Choosing a high-CRI lamp is a
signal-to-noise decision, not an aesthetic one.

**Why the lamp's own shape does not otherwise matter.** The spike, the hump and the dip all appear
identically in the reference and in the sample, so they divide out exactly (§2.4). The lamp does not
need to be flat — it needs to be **non-zero everywhere and stable in time**. Stability is why the
lamp is left permanently on.

### KB 7 — From a spectrum to a colour

**The CIE 1931 observer.** Human colour vision has three cone types, so any spectrum collapses to
three numbers. The standard observer defines three matching functions `x̄(λ)`, `ȳ(λ)`, `z̄(λ)`, and
a spectrum `P(λ)` becomes

```
  X = ∫ P(λ)·x̄(λ) dλ        Y = ∫ P(λ)·ȳ(λ) dλ        Z = ∫ P(λ)·z̄(λ) dλ
```

`Y` is defined to coincide with luminance. XYZ is a device-independent description of colour: two
different spectra with the same XYZ look identical, which is the whole phenomenon of metamerism.

**Chromaticity — dropping the brightness.** Normalising removes the intensity dimension:

```
  x = X / (X+Y+Z)          y = Y / (X+Y+Z)
```

The pair `(x, y)` is the colour *without* the brightness. This step has a consequence that matters
to us: **scaling a spectrum does not change its chromaticity**. So a colour computed from
*absorbance* is dilution-invariant for exactly the same algebraic reason a band ratio is (KB 2) —
and it is invariant to the gamma exponent too (§3.3).

**Hue, chroma, lightness.** Converting to HSL gives more intuitive coordinates. Two cautions:

- **Saturation misbehaves at the extremes.** A near-white colour can report ~100 % saturation while
  being visually almost grey. **Chroma** — computed as `(1 − |2L − 1|) · S` — stays small there and
  is the honest measure of colourfulness. Spectracs uses chroma, never raw saturation, when deciding
  whether a colour is meaningful.
- **Gamut clamping distorts hue.** Colours outside what sRGB can represent get clamped, and the
  clamping can shift the reported hue substantially. A deeply saturated absorbance colour sits far
  outside the sRGB gamut, so a hue read straight off a clamped conversion can be an artefact rather
  than a measurement.

**Transmitted colour versus absorbed colour.** They are different objects. The colour of the
*transmitted* light is what the eye sees and depends on concentration (double the oil and it looks
darker and more saturated). The colour derived from the *absorbance* spectrum describes what the
substance takes out of the light; it is dilution-invariant, and it is roughly the complement of the
perceived colour. The colorimetrically correct way to convert between them is to reflect the
chromaticity through the white point — `2·white − colour`, the "mixing-to-white" opposite — which
lands far closer to the true perceived hue than naively adding 180° to an HSL hue.

<!--PAGEBREAK-->

## Appendix B — Where the evidence lives

This document summarises; the specifications hold the derivations, the raw numbers and the
decision history.

| topic | specification |
|---|---|
| the whole capture chain, all topics | `docs/SPEC_capture_quality.md` |
| grey value `max(R,G,B)` | `SPEC_capture_quality.md` §15 |
| gamma: design, and the measured verification | `SPEC_capture_quality.md` §17, §17.5 |
| auto-exposure saga and tuning | `SPEC_capture_quality.md` §14.5 – §14.7 |
| dim-frame rejection, adaptive settle | `SPEC_capture_quality.md` §14.8 |
| white-balance split | `SPEC_capture_quality.md` §14.8 |
| sensor self-heating | `SPEC_capture_quality.md` §16 |
| dark-frame measurement | `SPEC_capture_quality.md` §4, §5 |
| resolution pin and tripwire | `SPEC_capture_quality.md` §4.9 |
| spatial / temporal reduction | `SPEC_capture_quality.md` §6 |
| wavelength window | `SPEC_capture_quality.md` §9 |
| pigment bands, band-placement re-test | `SPEC_pumpkin_peak_ratio_eval.md` §1b, §1b.3 |
| dilution protocol, lab procedure | `SPEC_capability_proof.md` §7.3 |
| what was actually run, dated | `LAB_DIARY_capability_proof.md` |
| the quality verdict built on all this | `SPEC_roast_ampel.md` |
| physics background | `docs/KB_spectroscopy_physics.md` |

## Appendix C — How this document is produced

The PDF is generated; it is never hand-edited.

```
source of truth   docs/DOC_capture_fidelity.md          (this file, markdown)
generator         docs/tools/build_capture_fidelity_pdf.py
output            ../spectracs-docs/internal/Spectracs_CaptureFidelity.pdf

    python3 docs/tools/build_capture_fidelity_pdf.py
    python3 docs/tools/build_capture_fidelity_pdf.py --out /tmp/preview.pdf --html
```

To update it: edit the markdown, re-run the generator, commit the markdown *and* the PDF. The
generator converts a small markdown subset (headings, lists, tables, code blocks, block quotes,
images, `<!--TOC-->` and `<!--PAGEBREAK-->` markers) into a print-styled page and drives headless
Chrome to render it — so the only external dependency is Chrome, which the sibling
`build_capability_status_pdf.py` already required.

Figures are embedded from `spectracs-references/` as data URIs, so the PDF is self-contained and
can be sent to the lab as a single file.
