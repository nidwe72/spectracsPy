# KB — Spectrum-related Python libraries (reference / brain-helper)

> A catalogue of the Python libraries that touch the **spectrum → processing → colour** problem space,
> assembled while extracting the `spectrasTest.py` hue prototype (see
> [`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md)).
> Purpose: when a library is **dropped** from the production path it should not be *forgotten* — several
> are genuinely useful and may come back for a future feature. This records **what each does**, **how it
> relates to our spectrum work**, and **why it is in / out** today. Last updated 2026-06-29.

## Status at a glance

| Library | Area | Status in app | Could return for… |
|---------|------|---------------|-------------------|
| `colour` (colour-science) | Colorimetry / CIE | **in use** (spectrum→colour core) | any CIE / colour-space work |
| `colorsys` (stdlib) | RGB↔HLS/HSV | **in use** (hue extraction) | hue/lightness/saturation maths |
| `rgbxy` | CIE xy → RGB | **in use** (swatch RGB) | quick xy→RGB, lamp-style colour |
| `spectres` | Spectral resampling | **in use** (`rebin`) | any flux-conserving rebinning |
| `colormath` | Colour difference (ΔE) | **in use** (`SpectralColorUtil.getColorDifference`) | colour-match scoring / verdicts |
| `scipy.signal` / `scipy.ndimage` | Smoothing / morphology | **in use** (`smooth`, `removeBaseline`) | filtering, peak finding |
| `numpy` | Arrays | **in use** (everywhere) | — |
| `luxpy` | Lighting / colour science | **dropped** (was dead code) | LED/illuminant modelling, advanced colorimetry |
| `BaselineRemoval` | Baseline correction | **dropped** (superseded by scipy) | alt. baseline algorithms (ZhangFit/ModPoly) |
| `pyspectra` | Spectra I/O + transforms | **in use** (`.dx` import) | reading `.dx`/JCAMP files, `sav_gol` |
| `pandas` | DataFrames | **dropped** (was plumbing) | tabular export / analysis |
| `matplotlib` | Plotting | **dropped** (demo-only) | offline/report plotting (app uses pyqtgraph) |

## In use

### `colour` (colour-science) — the colorimetry workhorse
Full CIE colour-science toolkit. We use it for the spectrum→colour core: build a
`SpectralDistribution` from `{nm: value}`, then `sd_to_XYZ` (CIE 1931 2° observer, D65 illuminant,
Integration method) → `XYZ_to_xy`. Pins `numpy<2` (relevant: the app pins **numpy 1.26.4** for this).
Also offers `XYZ_to_sRGB`, chromaticity-diagram plotting, colour-difference, spectral upsampling — a
candidate to *replace* several of the dropped libs if we ever want a single-dependency colour stack.

### `colorsys` (stdlib) — cheap colour-space conversions
Standard library, no install. We use `rgb_to_hls` / `hls_to_rgb`. **Gotcha: HLS order** (Hue,
**Lightness**, Saturation), not HSL — `hls[1]` is lightness, `hls[2]` is saturation. The hue swatch
fixes lightness to 0.20 and re-renders via `hls_to_rgb`.

### `rgbxy` — CIE xy → RGB (Philips Hue origin)
Tiny pure-Python lib written for **Philips Hue lamps**. `Converter().xy_to_rgb(x, y)` maps a
chromaticity coordinate (luminance discarded) to an RGB via Hue's Wide-gamut/D65 matrix + reverse
gamma. Kept because it produced the **validated** oil-sample swatches; its luminance-discard is
harmless here since we reset lightness anyway. `colour.XYZ_to_sRGB` is the principled alternative if we
ever drop it.

### `spectres` — flux-conserving spectral resampling
Resamples a spectrum onto a new wavelength grid by **integrating over bin edges**, conserving total
flux — the *correct* way to rebin a spectrum (linear `numpy.interp` would smear/scale incorrectly).
Used by `SpectrumUtil.rebin` to map onto the 380–780 nm @ 1 nm grid. Small footprint; kept.

### `colormath` — colour difference (ΔE)
Already wired in `SpectralColorUtil.getColorDifference`: sRGB → Lab → `delta_e_cie2000`. The natural
tool for "how close is the measured colour to a target" — likely the basis of an evaluation **verdict**
(pass/fail by ΔE threshold) in a plugin.

### `scipy` (`signal`, `ndimage`) — smoothing & baseline
`savgol_filter` (Savitzky–Golay) backs `SpectrumUtil.smooth`; `minimum_filter1d`/`maximum_filter1d`
(morphological opening) back `SpectrumUtil.removeBaseline`. Also `find_peaks` for line detection
elsewhere. The reason `BaselineRemoval`/`pyspectra` could be dropped.

## Dropped — kept on record (may return)

### `luxpy` — lighting & colour-science toolbox
A large research-grade toolbox: spectral power distributions, LED/illuminant modelling, advanced
colorimetry, display calibration. In the prototype its `spd()` / `spd_to_xyz()` results were
**computed but never read** (dead code) — the live path used `colour` instead. **Why it might return:**
Roadmap **#5** wants the virtual REFERENCE image **synthesized from a set of LED spectra** — luxpy is a
prime candidate for building those LED SPDs. Worth remembering when that item starts.

### `BaselineRemoval` — baseline correction algorithms
Provides `ZhangFit` (adaptive iteratively reweighted penalized least squares), `ModPoly`, `IModPoly`.
The prototype used `ZhangFit`; we replaced baseline removal with a scipy morphological-opening approach
(no extra dep, resolution-adaptive). **Why it might return:** if morphological opening proves too crude
for a given spectrum, `ZhangFit`/`IModPoly` are stronger, well-regarded baseline estimators.

### `pyspectra` — spectra I/O + transforms  *(still in use)*
Two roles: `readers.read_dx` (read **`.dx` / JCAMP** spectrum files) and
`transformers.spectral_correction.sav_gol` (smoothing). Smoothing is scipy now, **but `read_dx` is
still wired into `ImportSpectrumLogicModule`** — so `pyspectra` is **not** dropped (the spectrum
import/export backend is only partial, KB §13). Kept for that reader.

### `pandas` — DataFrames
Only used in the prototype to wrap data into a `DataFrame` feeding luxpy's dead `spd` calls; the live
path uses a plain `dict`. **Why it might return:** tabular export of spectra / batch analysis /
CSV round-tripping.

### `matplotlib` — plotting
The prototype's step-by-step PNG dumps (`sample_step1..6`). The **app charts with pyqtgraph** (MIT;
QtCharts was removed — KB §14), so matplotlib has no place in the running app. **Why it might return:**
offline analysis scripts or generating figures for the **PDF report** (Roadmap, deferred).

## Cross-references
- [`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md) — where the keep/drop decisions are made
  (the dependency-trim table, §4.5).
- [`KNOWLEDGE_BASE.md`](KNOWLEDGE_BASE.md) §6 (pipeline), §13 (numpy<2 pin), §14 (pyqtgraph charting).
