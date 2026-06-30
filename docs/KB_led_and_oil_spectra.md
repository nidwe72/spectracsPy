# KB — LED hardware & pumpkin-oil spectra (synthesis reference)

Research notes backing the **playground** synthesis (REFERENCE from LEDs, SAMPLE = oil) and Roadmap #5.
Captured 2026-06-30. Sources at the bottom. This is a knowledge-base note, not a spec.

---

## 1. LED hardware — the real light source

The device's light source is **3 W high-power LEDs** from **Avonec** (Germany):
**https://www.avonec.de/3w-high-power-led/** ← *the shop. Don't lose this.*

> **The shop publishes MEASURED spectra of its LEDs** — confirmed. Each product page's "Dokumente" has a
> **Spektralmessung** (a measured-spectrum **JPG plot**, ~64 KB) + a (mostly image-only) datasheet PDF.
> The spectra live at a predictable path:
> **`https://www.avonec.de/media/products/Spektralmessungen/3W/single/<RANGE>.jpg`**
> (e.g. `515nm-525nm.jpg`, `455nm-460nm.jpg`, `630nm-640nm.jpg`, `660nm.jpg`). They are **plot images, not
> data files** — so to use them we either (a) read **peak + FWHM (+ skew)** off the plot into the Gaussian
> model, or (b) **digitise** the curve for a near-exact SPD.
>
> **Verified — green 515–525 (`515nm-525nm.jpg`):** peak ≈ **515 nm**, **FWHM ≈ 30 nm**, slight red skew.
> Monochromatic shape — a skewed Gaussian fits.
> **Verified — warm-white 2900–3200 K (`2900k-3200k.jpg`):** **bimodal** — blue pump peak ≈ **448 nm**
> (~0.29) + broad phosphor hump **500–700 nm peaking ≈ 586 nm** (1.0), with the **cyan dip ≈ 475 nm**
> (~0.04) and a small notch ~650 nm. **A Gaussian cannot represent this → use the measured spectrum**
> (digitised) for whites. (Confirms the "no gaps, only low-intensity dips" memory: the only weak spot is
> cyan ~470–510, which no Avonec colour LED can fill.)
>
> **Decision:** the measured JPGs are the **primary SPD source** (digitise the curve); skewed-Gaussian is
> a fallback only for any LED lacking a measurement. **luxpy not required.**

### Harvested measured spectra — `spectracs-references/leds/avonec/` (full set)
All Avonec 3 W single-LED Spektralmessung JPGs are now stored locally (resolved via
`shop.php?do=ProductMediaContent&pcdId=<N>` → `<img src>`). One file per LED, named `<range>.jpg`:

| Visible colour LEDs | White LEDs | (IR, ignore) |
|---|---|---|
| `410nm-420nm` (UV-A/actinic) | `2900k-3200k` (warm white) | `740nm` |
| `430nm-435nm` (hyper violet) | `4000k-4500k` (neutral) | `850nm` |
| `440nm-450nm` (royal blue) | `5500k-6000k` (white) | |
| `455nm-460nm` (blue) | `6500k-7000k` (cool) | |
| `515nm-525nm` (green) | `10000k-20000k` (cold) | |
| `590nm-600nm` (yellow) | | |
| `600nm-610nm` (orange) | + `datasheet_515nm-525nm.pdf` | |
| `630nm-640nm` (red) | | |
| `660nm` (deep red) | | |

Missing: **390–410 UV-A** (no Spektralmessung published) — **synthesise it with luxpy** (or a
skewed-Gaussian ~400 nm) if that LED is used. To use a measured curve: read peak/FWHM/skew off the
plot, or **digitise** it (trace the JPG → nm/intensity pairs). The green is peak~515/FWHM~30; the
warm-white is the bimodal pump+phosphor described above.

### Visible-range 3 W products (peak / dominant wavelength as listed)

| Colour | Wavelength | Note |
|---|---|---|
| UV-A (Schwarzlicht) | 390–410 nm | violet/UV edge |
| UV-A / actinic | 410–420 nm | |
| **hyper violet** | **430–435 nm** | near chlorophyll Soret band |
| **royal blue** (königsblau) | **440–450 nm** | |
| blue | 455–460 nm | |
| **green** (grün) | **515–525 nm** | sits in the oil's green transmission window |
| yellow (gelb) | 590–600 nm | |
| orange | 600–610 nm | |
| **red** (rot) | **630–640 nm** | |
| **deep red** / hyper red | **660 nm** | |
| warm white | 2900–3200 K | broadband phosphor — the continuum base |
| neutral white | 4000–4500 K | |
| white | 5500–6000 K | |
| cool white | 6500–7000 K / 10000–20000 K | |
| (IR 740/850 nm — out of visible, ignore) | | |

### Proposed REFERENCE LED set (matches Edwin's recollection: 2–3 UV/blue + green + 2× red + 2× warm white)
- **2× warm white 2900–3200 K** — broadband base (blue pump ~450 nm + wide phosphor hump) → this is why
  the real reference had **"no real gaps, only lower-intensity regions"** (the classic warm-white dip is
  around cyan ~490–510 nm).
- **hyper violet 430–435** (+ optionally UV-A 410–420) — violet end.
- **royal blue 440–450** *or* **blue 455–460**.
- **green 515–525**.
- **red 630–640** + **deep red 660** — the "two reds".

So **REFERENCE R(λ) = Σ (warm-white continua) + Σ (coloured LED peaks)** — gap-free with shallow dips,
exactly the observed shape.

### Synthesis recipe (for the spec)
- Per coloured LED: a Gaussian at its peak nm, FWHM ≈ 20–30 nm (narrower for UV/violet/blue), amplitude =
  drive weight (× 3 W). 
- Per warm-white LED: narrow blue-pump peak (~450 nm) + broad phosphor hump (centroid ~580–600 nm,
  FWHM ~100 nm) — or a measured/luxpy white-LED SPD.
- **luxpy** (installed; see `KB_spectrum_libraries.md`) has an SPD/LED builder
  (`spdbuild` / phosphor-LED + multi-LED mixing to a target CCT/chromaticity) — prime tool for this.
- Prefer **measured Avonec SPDs** if downloadable; else the Gaussian model above.

---

## 2. Pumpkin-seed-oil spectrum — the science behind the QM

Styrian pumpkin seed oil (*Steirisches Kürbiskernöl*) is **dichromatic**: **red** in a thick layer
(bottle), **green** in a thin layer (on salad). Fruhwirth & Hermetter (2007) explain this quantitatively
with the **Beer–Lambert law + CIE colour-matching functions** — i.e. *exactly the physics our pipeline
models*.

**Mechanism (drives SAMPLE synthesis):** the oil has a narrow **green transmission window (~520–560 nm)**
between a blue absorption (chlorophyll Soret ~430 nm + carotenoids 400–500 nm) and a red absorption
(chlorophyll Q-band ~660–670 nm), plus **deep-red transmission beyond ~670 nm**. As **concentration ×
path length** rises (Beer–Lambert), the narrow green window is overwhelmed and the deep-red transmission
dominates → the perceived colour rotates **green → red/brown**. Thin/low-conc → green.

**Pigments:** protochlorophyll(a/b) + protopheophytin(a/b) (tetrapyrroles → green, red fluorescence,
emission max ~635 nm); carotenoids, **lutein** predominant (yellow, absorbs ~440–480 nm). Pumpkin-seed
extract UV/VIS max ~440 nm.

**Quality axis:** roasting adds **Maillard browning** (broad short-λ absorption) on top — shifting the
transmitted colour further toward brown. So the green↔brown verdict axis is governed by
**(pigment concentration × path)** *and* **roast-browning** — both expressible as terms in `A_oil(λ)`.

### Implication for SAMPLE synthesis (forward, physical)
`A_oil(λ) = chlorophyll(Soret≈430, Q≈665) + carotenoid/lutein(≈440–480) + browning(rising toward blue) `,
scaled by **concentration × path** (the dichromatism knob). Then `SAMPLE S = R · 10^(−A_oil)`, colour from
the **transmission** (S or T=S/R). Presets ("excellent" green vs "bad/over-roasted" brown) = different
`(pigment amps, browning amp, conc×path)`; forward-run → verify against the preset's target HSL.

---

## 3. The inverse problem (colour → spectrum) — options, if ever needed

Going from a target **HSL/colour back to a spectrum is ill-posed** (metamerism — many spectra → one
colour). We do **not** need it for SAMPLE synthesis (we forward-model `A_oil`). Noted here in case we
later want to back out a plausible spectrum from a measured `QColor` (e.g. for display):

- **Metameric-black decomposition:** spectrum = fundamental metamer (from RGB/XYZ) + metameric black
  (null-space of the sensitivities). Pick one via a smoothness prior.
- **Smoothest / least-norm metamer:** Finlayson & Morovic **LPCC** (linear-programming centre of cube);
  least-slope-squared (LHTSS).
- **Physically-plausible reconstruction** bounded to [0,1] (MDPI *Sensors* 2020, 20(21):6399).
- **Graphics RGB→spectrum:** Smits (1999); Mallett & Yuksel (2019, three smooth bases); Jakob & Hanika
  (2019, sigmoid-polynomial).

**Recommendation:** forward physical model for SAMPLE (above); reserve inverse methods only for
display-side reconstruction, and prefer a bounded smoothest-metamer method then.

---

## 4. Local historical data — provenance UNKNOWN, do not trust as ground truth

> ⚠️ **Capture provenance is unknown** (which reference? which device? normalised how?), so these
> measured spectra **may be misleading** and must **not** be used as ground-truth presets or validation
> targets. Treat as historical artefacts only. **Playground presets are fully synthetic** from the
> controlled physical oil model (§ `KB_spectroscopy_physics.md`) — known provenance, every parameter ours.

Historical measured Styrian-oil spectra under **`../../spectracs-evaluations/`** (sibling, non-versioned):
- **17 `.dx`** (JCAMP-DX, 362–938 nm @~0.3 nm, intensity) — e.g. `20230120/oil_{weinhandel,spar,lugitsch}_mean.dx`.
- **338 `.sgd`** incl. **12 `light_*` REFERENCE** spectra, **76 `*abs*`** absorption, plus raw/mean SAMPLE.
- Named oils + prices `../../unsorted/oils.txt`; quality classes (EXZELLENT / SEHR GUT) `oilScore.txt`;
  Julia prototype `oils.jl`/`oils3.jl` — note it computed absorption as **absorptance `A = 1 − S/R`**
  (bounded), and reduced each spectrum to an **18-band feature vector**.
- **Verdict colour palette** from `../../unsorted/oilScores.svg` (rendered to
  `../../spectracs-references/oils/oilScores_rendered.png`): per-oil stacked green bar +1–3 stars,
  **`#669900` excellent → `#446600` good → `#223300` bad**. (That viz was the abandoned LDA classifier;
  the palette is still the target-colour anchor.)

Harvested LED spectra + this index live in **`../../spectracs-references/`**. Physics in
`KB_spectroscopy_physics.md`.

## Sources
- Avonec 3 W high-power LEDs: https://www.avonec.de/3w-high-power-led/
- Fruhwirth & Hermetter (2007), *Seeds and oil of the Styrian oil pumpkin* — ResearchGate 227762370;
  Wikipedia *Pumpkin seed oil*.
- Carotenoid/chlorophyll spectral properties in solvents: ScienceDirect S2772753X22001666;
  β-carotene in pumpkin: PMC8857520.
- Spectral reconstruction: *Physically Plausible Spectral Reconstruction*, MDPI Sensors 20(21):6399;
  Finlayson & Morovic (metamer LPCC); Mallett & Yuksel (2019).
