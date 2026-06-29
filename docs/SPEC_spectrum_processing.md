# SPEC — Spectrum Processing & Spectrum → Color

> Status: **IMPLEMENTED 2026-06-29** (all phases P1–P6, §8). Realises **Roadmap item #1**.
> Origin prototype: `spectrasTest.py` (flat throwaway script in repo root).
> Rubber-duck review §7; phases §8; testing/usage §9 — **11 unit tests pass** (`tests/test_spectrum_processing.py`).
> Deviation from plan: `pyspectra` is **kept** (still wired into spectrum import), not dropped (§4.5).

## 1. Purpose & scope

Two related concerns, both currently living only in the throwaway `spectrasTest.py`:

1. **General spectrum processing** — the clean-up chain applied to a raw captured spectrum
   (smooth → average frames → baseline-removal → **rebin** → **normalize**) before it can be
   evaluated. Most of this already exists on `SpectrumUtil`; two steps (rebin, normalize) do not.
2. **Spectrum → colour evaluation** — converting a processed spectrum into a perceptual colour
   (the CIE `colour` + `colorsys` pipeline). This becomes the body of `PumpkinPlugin.evaluation`
   and the first real evaluation step on the virtual device.

This spec gives both a permanent home, matched to existing conventions, and trims the prototype's
heavy dependency set.

## 2. Data model recap

`Spectrum` (`spectracsPy-model/sciens/spectracs/model/spectral/Spectrum.py`) stores its data as a
single dict — there are **no separate wavelength/value arrays**:

```python
spectrum.valuesByNanometers: Dict[int, float]   # nm -> intensity ; read directly (no getter)
spectrum.getCapturedValuesByNanometers() -> List[Dict[int, float]]   # raw per-frame captures
```

All processing reads/writes the `valuesByNanometers` dict, preserving keys and only replacing the
values via `dict(zip(keys, newValues))` (the established `SpectrumUtil` pattern).

## 3. General spectrum-processing pipeline

`SpectrumUtil` (`logic/spectral/util/SpectrumUtil.py`, `Singleton`) is the **façade** for the chain.
Each operation is exposed as one method that takes a `Spectrum` (optionally deep-copies via
`clone=True`) and returns the `Spectrum` — **and delegates its heavy lifting to a dedicated
per-operation logic module**, exactly mirroring `SpectralColorUtil.spectrumToColor → SpectrumToColorLogicModule`
(§4). The scipy code currently inline in `SpectrumUtil` **moves into** the corresponding module.

| `SpectrumUtil` method | Operation | Status | Heavy lifting (logic module) |
|------|------------------|--------|------|
| `mean()` | average captured frames | exists inline → **extract** | `MeanSpectrumLogicModule` |
| `smooth()` | Savitzky–Golay ×7 (scipy) | exists inline → **extract** | `SmoothSpectrumLogicModule` |
| `removeBaseline()` | morphological opening (scipy) | exists inline → **extract** | `RemoveBaselineLogicModule` |
| `rebin()` | resample 380–780 nm @ 1 nm (`spectres`) | **NEW** | `RebinSpectrumLogicModule` |
| `normalize()` | scale to unit max | **NEW** | `NormalizeSpectrumLogicModule` |

### 3.1 Per-operation logic modules (façade pattern)

Each operation is its own triple under its own folder, mirroring the `importSpectrum/` template
(plain non-singleton classes; `= None` / default class fields with manual get/set). `SpectrumUtil`
calls them:

```
logic/spectral/meanSpectrum/        MeanSpectrumLogicModule.meanSpectrum(params) -> Result
logic/spectral/smoothSpectrum/      SmoothSpectrumLogicModule.smoothSpectrum(params) -> Result
logic/spectral/removeBaseline/      RemoveBaselineLogicModule.removeBaseline(params) -> Result
logic/spectral/rebinSpectrum/       RebinSpectrumLogicModule.rebinSpectrum(params) -> Result
logic/spectral/normalizeSpectrum/   NormalizeSpectrumLogicModule.normalizeSpectrum(params) -> Result
```

- Every `...Parameters` carries `spectrum = None` plus any operation-specific options
  (`RemoveBaseline` → `windowSize`; `Rebin` → `start=380, stop=780, step=1`). Every `...Result`
  carries `spectrum = None` (the processed `Spectrum`).
- `SpectrumUtil` method shape (uniform across all five):
  ```python
  def rebin(self, spectrum, clone=False):
      parameters = RebinSpectrumLogicModuleParameters()
      parameters.setSpectrum(copy.deepcopy(spectrum) if clone else spectrum)
      result = RebinSpectrumLogicModule().rebinSpectrum(parameters)
      return result.getSpectrum()
  ```
- **Implementation notes** (now living in the modules, unchanged in behaviour from today's inline code
  except the two new ones):
  - `RebinSpectrumLogicModule` — `spectres.spectres(...)`, **flux-conserving** (the correct method for
    a spectrum; linear `numpy.interp` would be a downgrade). Rewrites `valuesByNanometers` with the
    new integer keys. **Edge case (§7.1):** `spectres` returns `NaN` for target wavelengths outside the
    input range; pass `fill=0.0` (or clamp the target grid to the input overlap) so a narrow spectrum
    does not poison the downstream colour maths.
  - `NormalizeSpectrumLogicModule` — divide all values by `max(values)`; guard the all-zero / empty
    case (no-op rather than divide-by-zero).

**Backward compatibility:** `mean` / `smooth` / `removeBaseline` are **already called** by the capture
and calibration paths (KB §13). This is a refactor *behind* the façade — the `SpectrumUtil` method
signatures and behaviour stay identical; only the implementation body moves into the module.

**Optional-step control:** there is **no orchestrator** — selecting which steps run is simply a matter
of which `SpectrumUtil` methods the caller invokes. Canonical order for the colour use-case:
`mean → smooth → removeBaseline → rebin → normalize`. This keeps a clean separation: **each module =
one cleanup operation, colour module (§4) = conversion** (which assumes already-processed input).

## 4. Spectrum → Colour evaluation

### 4.1 Placement & façade

`SpectralColorUtil` (`logic/spectral/util/SpectralColorUtil.py`, `Singleton`) stays the **stable,
lightweight façade**. It gains one method that **delegates** to a dedicated heavy-lifting logic
module (which owns the `colour` / `colorsys` import weight):

```python
# SpectralColorUtil
def spectrumToColor(self, spectrum: Spectrum) -> QColor:
    parameters = SpectrumToColorLogicModuleParameters()
    parameters.setSpectrum(spectrum)
    result = SpectrumToColorLogicModule().spectrumToColor(parameters)
    return result.getColor()
```

The façade returns a plain `QColor` (matches `wavelengthToColor`'s return type). The full HLS detail
stays on the Result for callers that want the raw hue number later.

### 4.2 The operation triple

New folder `logic/spectral/spectrumToColor/`, mirroring the `importSpectrum/` template
(plain non-singleton classes; `= None` class fields with manual get/set):

```
logic/spectral/spectrumToColor/
    SpectrumToColorLogicModule.py
        spectrumToColor(parameters: SpectrumToColorLogicModuleParameters)
            -> SpectrumToColorLogicModuleResult
    SpectrumToColorLogicModuleParameters.py
        spectrum   = None   # the (processed) Spectrum to evaluate
        lightness  = 0.20    # fixed swatch lightness (see §4.4); overridable per call
    SpectrumToColorLogicModuleResult.py
        color      = None   # QColor — the rendered swatch
        hue        = None   # float, degrees 0–360   (measured)
        lightness  = None   # float, 0–100           (measured, pre-override)
        saturation = None   # float, 0–100           (measured)
```

### 4.3 Algorithm (inside the LogicModule)

Input: `parameters.getSpectrum()`, assumed already processed (§3) — on the 380–780 nm grid and
max-normalized.

1. Build `SpectralDistribution(spectrum.valuesByNanometers)` (dict is already nm → value).
2. `cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]`,
   `illuminant = SDS_ILLUMINANTS["D65"]`.
3. `XYZ = sd_to_XYZ(sd, cmfs, illuminant, method='Integration')`.
4. `xy = XYZ_to_xy(XYZ)`.
5. `rgb = Converter().xy_to_rgb(xy[0], xy[1])` (`rgbxy`) → components to [0,1] (lib returns 0–255).
   *(see §4.5 — kept as the prototype's validated transform; the discarded luminance is irrelevant
   because the swatch resets lightness in step 8.)*
6. `hls = colorsys.rgb_to_hls(r, g, b)` — **HLS order**: `hls[0]=hue`, `hls[1]=lightness`,
   `hls[2]=saturation`.
7. Measured values: `hue = hls[0]*360.0`, `lightness = hls[1]*100.0`, `saturation = hls[2]*100.0`.
8. Swatch: `swatchRgb = colorsys.hls_to_rgb(hls[0], parameters.lightness, hls[2])`
   → `QColor.fromRgbF(*swatchRgb)`.
9. Populate and return the Result (`color`, `hue`, `lightness`, `saturation`).

### 4.4 The fixed-lightness swatch (deliberate)

The prototype renders the swatch with **lightness pinned to 0.20**, carrying over only the measured
hue + saturation (`hls_to_rgb(hue, 0.20, sat)`). This keeps weak/dark spectra rendering as a visible,
comparable hue chip. Spec'd as a `Parameters.lightness` field defaulting to `0.20` so a plugin can
override it; the *measured* lightness is still reported on the Result. **Decided:** `Parameters`
field, default `0.20`.

### 4.5 Dependency trim (Roadmap #1 goal)

Core needs **`colour`** + stdlib **`colorsys`** + **`PySide6.QtGui.QColor`**, plus two small validated
libs kept for parity (`rgbxy`, `spectres`). The trim targets the heavy/redundant ones:

| Prototype dep | Verdict |
|---------------|---------|
| `colour` | **keep** (SpectralDistribution, MSDS_CMFS, SDS_ILLUMINANTS, sd_to_XYZ, XYZ_to_xy) |
| `colorsys` (stdlib) | **keep** |
| `rgbxy` | **keep** — `Converter().xy_to_rgb`; tiny, produced the validated swatches (see §4.3 step 5) |
| `spectres` | **keep** — flux-conserving rebin (§3); correct method, small footprint |
| `luxpy` | **drop** — **dead code**: `spd(...)`/`spd_to_xyz(...)` (lines 125–126) compute values never read; the live path uses `colour.sd_to_XYZ` |
| `pandas` | **drop** — **dead code**: only builds the `DataFrame` feeding luxpy's dead `spd` calls; the live path uses a plain `dict` |
| `BaselineRemoval` | **drop** — **superseded**: `removeBaseline` uses scipy morphology (same purpose, no extra dep) |
| `pyspectra` | **KEEP** — still wired into `ImportSpectrumLogicModule` (`.dx`/JCAMP reader). *Not* droppable, contrary to the original plan; smoothing is scipy, but the import feature still needs `read_dx`. |
| `matplotlib` | **drop** — **demo-only**: plotting / PNG export, no role in the logic |

Four libs (`luxpy`, `pandas`, `BaselineRemoval`, `matplotlib`) are genuinely unused by **app code** — a
codebase grep finds them only in the root scratch scripts (`spectrasTest.py` etc.). `pyspectra` stays
(spectrum import). Note: there is **no `requirements.txt`** in the repo (deps live in the venv + the
PyInstaller specs, which reference none of the four), so the "trim" is realised as *app code being free
of them*, not a manifest edit. They are left installed (several are transitive deps, e.g. `luxpy` pulls
`pandas`/`matplotlib`); exclude them when a real requirements pin is introduced.

> The dropped libs are **not forgotten** — several may be useful later (e.g. `luxpy` for Roadmap #5's
> LED-spectra synthesis, `pyspectra` for `.dx`/JCAMP import). Each is catalogued with its purpose and
> a "why it might return" note in [`KB_spectrum_libraries.md`](KB_spectrum_libraries.md).

## 5. File summary

```
spectracsPy-model/.../model/spectral/Spectrum.py          (unchanged — reference only)
spectracsPy/.../logic/spectral/util/SpectrumUtil.py       (façade → delegates each op to its module)
spectracsPy/.../logic/spectral/util/SpectralColorUtil.py  (+ spectrumToColor façade)
spectracsPy/.../logic/spectral/meanSpectrum/      Mean…LogicModule + …Parameters + …Result   (extract)
spectracsPy/.../logic/spectral/smoothSpectrum/    Smooth…LogicModule + …Parameters + …Result  (extract)
spectracsPy/.../logic/spectral/removeBaseline/    RemoveBaseline…LogicModule + … + …          (extract)
spectracsPy/.../logic/spectral/rebinSpectrum/     Rebin…LogicModule + …Parameters + …Result   (NEW)
spectracsPy/.../logic/spectral/normalizeSpectrum/ Normalize…LogicModule + …Parameters + …Result(NEW)
spectracsPy/.../logic/spectral/spectrumToColor/   SpectrumToColor…LogicModule + … + …          (NEW)
```

## 6. Decisions (resolved)

1. **Swatch lightness** — ✅ `Parameters.lightness` field, default `0.20`.
2. **xy→rgb** — ✅ keep `rgbxy` (validated swatches; luminance discarded anyway by the 0.20 reset).
3. **`rebin` resampler** — ✅ keep `spectres` (flux-conserving = correct for spectra).
4. **Processing structure** — ✅ **one logic module per operation**, all called from the `SpectrumUtil`
   façade (no single orchestrator); optional steps = call the methods you want (§3.1).
5. **Dropped deps** — ✅ `luxpy`, `pandas`, `BaselineRemoval`, `matplotlib` unused by app code (only
   scratch scripts). **`pyspectra` kept** — still wired into spectrum import. `rgbxy`, `spectres`,
   `colour`, `colorsys` kept (§4.5).

## 7. Edge cases & risks (rubber-duck)

| # | Concern | Resolution |
|---|---------|------------|
| 7.1 | **`rebin` `NaN` at edges** — `spectres` returns `NaN` for targets outside the input range; a device spectrum covering only ~400–700 nm poisons `SpectralDistribution` → `XYZ`. | `RebinSpectrumLogicModule` passes `fill=0.0` (or clamps the target grid to the input overlap). Add a unit test for a narrow input (§9). |
| 7.2 | **`rgbxy` gamut clamp** — `Converter().xy_to_rgb` snaps out-of-gamut chromaticities to the Philips-Hue gamut boundary → possible hue shift on saturated colours. | Accepted (validated on the oil samples); recorded here as known behaviour. `colour.XYZ_to_sRGB` is the fallback if it ever bites. |
| 7.3 | **Backward compatibility** — `mean` / `smooth` / `removeBaseline` are live in the capture + calibration paths. | Façade method signatures + behaviour unchanged; extraction is body-only. Regression check: existing calibration "Detect peaks" + measurement still work. |
| 7.4 | **Empty / all-zero spectrum** — `normalize` divide-by-zero; `sd_to_XYZ` on an empty SD. | `normalize` no-ops on max≤0; `spectrumToColor` returns a neutral `QColor` (or raises a clear error) on an empty spectrum — decide at impl, test it (§9). |
| 7.5 | **`Result.lightness` vs swatch colour** — Result reports *measured* lightness, but `Result.color` uses the fixed 0.20. | Intentional (§4.4); documented so a consumer doesn't expect `color` to reflect `lightness`. |

Non-issues confirmed: per-operation modules are stateless (fresh instantiation is fine); `Spectrum`
is a plain non-ORM class, so tests construct it directly and avoid the SQLAlchemy mapper import-order
fragility that blocks other headless tests (KB §13).

## 8. Implementation phases

| Phase | Scope | Deliverables | Depends on | Definition of Done | Status |
|-------|-------|--------------|------------|--------------------|--------|
| **P1 — Processing primitives** | Add the two missing `SpectrumUtil` ops as logic modules | `rebinSpectrum/` + `normalizeSpectrum/` triples; `SpectrumUtil.rebin` / `.normalize` façade methods (incl. 7.1 fill) | — | `rebin` yields exactly `380..780` keys, no `NaN` (edges `0.0`); `normalize` makes max `1.0` and no-ops on all-zero | ✅ |
| **P2 — Extract existing ops** | Move inline scipy code into modules (no behaviour change) | `meanSpectrum/`, `smoothSpectrum/`, `removeBaseline/` triples; `SpectrumUtil` delegates; regression-check capture + calibration (7.3) | P1 (pattern) | `SpectrumUtil.mean/smooth/removeBaseline` signatures unchanged; output identical to pre-refactor; calibration callers unaffected | ✅ |
| **P3 — Colour conversion** | The spectrum→colour core | `spectrumToColor/` triple (`...Parameters{spectrum, lightness=0.20}`, `...Result{color, hue, lightness, saturation}`), algorithm §4.3 | P1 (needs rebin+normalize for real input) | returns a `QColor` + measured HLS; empty spectrum → neutral grey, no exception (7.4) | ✅ |
| **P4 — Façade method** | Thin colour entry point | `SpectralColorUtil.spectrumToColor(spectrum) -> QColor` | P3 | one-call entry returns the swatch `QColor`; colour libs imported lazily (façade stays light) | ✅ |
| **P5 — Tests + usage sample** | Verify (§9) | unit tests for each op + the colour pipeline; a runnable usage sample | P1–P4 | unit tests **all green**; usage sample runs end-to-end and prints sensible hues | ✅ (11/11) |
| **P6 — Dependency trim** | Remove dead libs | confirm `luxpy`/`pandas`/`BaselineRemoval`/`matplotlib` unused by app code; keep `pyspectra` (import) | P1–P5 | grep proves the four are app-unused (scratch scripts only); app + tests still import/pass | ✅ |

P1 and P3 are the substance; P2 is mechanical; P3 can start in parallel with P2 (P3 only needs P1's
primitives). P6 last, once nothing imports the dropped libs.

### 8.1 Overall Definition of Done (all met 2026-06-29)

- [x] Five `SpectrumUtil` ops (`mean/smooth/removeBaseline/rebin/normalize`) each delegate to a
      per-operation logic-module triple; façade method signatures unchanged (no caller breakage).
- [x] `SpectralColorUtil.spectrumToColor(spectrum) -> QColor` returns the swatch; `Result` exposes the
      measured `hue/lightness/saturation`; swatch lightness pinned to `Parameters.lightness` (default 0.20).
- [x] Edge cases handled: rebin `fill=0.0` (7.1), normalize all-zero no-op (7.4), empty spectrum →
      neutral grey (7.4).
- [x] `tests/test_spectrum_processing.py` — 11 tests pass; `tests/spectrum_to_color_usage_sample.py` runs.
- [x] App code free of `luxpy/pandas/BaselineRemoval/matplotlib`; `pyspectra` retained for `.dx` import.
- [x] Docs synced: this spec (IMPLEMENTED), `KB_spectrum_libraries.md`, `KNOWLEDGE_BASE.md`, ROADMAP #1.

## 9. Testing & usage sample

`Spectrum` is constructible without a DB, so these are plain unit tests (pytest), no fixtures/mapper.

### 9.1 Suggested unit tests

| Target | Input | Assertion |
|--------|-------|-----------|
| `normalize` | spectrum with max value `V>0` | `max(valuesByNanometers.values()) == 1.0` |
| `normalize` | all-zero spectrum | no-op, no exception (7.4) |
| `rebin` | input 400–700 nm | keys are exactly `380..780`; edge values filled `0.0`, no `NaN` (7.1) |
| `rebin` | input already 380–780 @1nm | keys unchanged; values ≈ input (idempotent) |
| `smooth` / `removeBaseline` | known small array | output matches the pre-refactor inline result (golden test — guards 7.3) |
| `spectrumToColor` | synthetic narrow Gaussian peak @ ~550 nm | hue lands in the green / yellow-green band (measured ≈66°; test band 45–180°) |
| `spectrumToColor` | narrow peak @ ~450 nm | hue lands in the blue/violet band (measured ≈259°) |
| `spectrumToColor` | narrow peak @ ~620 nm | hue lands in the red/orange band (measured ≈18°) |
| `spectrumToColor` | empty spectrum | neutral `QColor` or clear error (7.4) |

The hue-band assertions are the meaningful end-to-end checks: a green-wavelength peak must read as a
green swatch. Use a tolerance band, not an exact RGB (the `rgbxy`/CIE path is not bit-stable across
library versions).

### 9.2 Usage sample (runnable)

```python
import numpy
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil

# 1. synthesize a spectrum: a narrow Gaussian emission peak at 550 nm (green)
nm = numpy.arange(380, 781)
intensity = numpy.exp(-((nm - 550) ** 2) / (2 * 15 ** 2))
spectrum = Spectrum()
spectrum.setValuesByNanometers(dict(zip(nm.tolist(), intensity.tolist())))

# 2. process (pick the steps you need — no orchestrator)
spectrumUtil = SpectrumUtil()
spectrumUtil.smooth(spectrum)
spectrumUtil.removeBaseline(spectrum)
spectrumUtil.rebin(spectrum)
spectrumUtil.normalize(spectrum)

# 3. evaluate to a colour
color = SpectralColorUtil().spectrumToColor(spectrum)   # -> QColor
print(color.name(), color.hueF() * 360.0)               # expect a green-ish hue
```

This doubles as the smoke test for the whole chain and as the template for `PumpkinPlugin.evaluation`
(Roadmap #6).

## 10. Out of scope / later

- `EvaluationResult` view-model rendering (`ColorSwatch`, `Verdict`, …) into the result tab.
- The eventual `spectracs.plugin_sdk.util.ColorUtil` home — `plugin_sdk` does not exist yet; this
  logic lives under `logic/spectral/` until that package is scaffolded.
- Wiring `spectrumToColor` into `PumpkinPlugin.evaluation` (Roadmap #6).
