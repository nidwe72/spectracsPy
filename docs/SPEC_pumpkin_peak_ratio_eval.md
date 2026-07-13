# SPEC — Pumpkin-oil peak-ratio evaluation (replace hue verdict)

Status: **P0–P4 IMPLEMENTED 2026-07-09** — render-only first sweep in the dev measurement bench
(`DevSpectralPlugin.evaluation` composes the generic ops; the bench shows a real EVALUATION phase with the
metrics). **P5** (calibration → verdict edges — needs real-oil measurements) and **P6** (wire the independent
`PumpkinOilPlugin`) are later. Awaits phone-width click-through. Supersedes the spectrum→hue verdict with an
**absorption peak-ratio** criterion. Raised 2026-07-05 ([[spectracs-pumpkin-peak-ratio-task]]); physics
grounded in Fruhwirth & Hermetter (2007) (`KB_led_and_oil_spectra.md` §2, `spectracs-references/articles/`).

---

## 0. Concept & rationale — *why we did it this way*

**Concept.** Objective quality management for pumpkin-seed oil, done optically: measure a REFERENCE (blank)
and a SAMPLE (oil) spectrum with the DIY grating spectrometer, compute absorption `A(λ) = −log₁₀(S/R)`, and
reduce it to a few **physically-meaningful numbers** — a headline *greenness* ratio plus supporting
*pigment / browning / clarity* axes — that map to a **green→brown quality verdict**. It is grounded in
Fruhwirth & Hermetter (2007): the oil's colour comes from tetrapyrrole pigments (protochlorophyll /
protopheophytin) with a classic **Soret + Q-band** absorption signature; roasting/oxidation tips the balance
(browning up, intact green pigment down).

**Design decisions and their reasons:**

1. **Peak-ratio, not a colour/hue verdict.** The hue verdict throws away structure — it collapses the whole
   spectrum to one colour. The peak-ratio reads the *specific pigment bands* Fruhwirth identifies, so it is
   physically interpretable and separates *why* an oil is off (browned vs faded vs turbid), which a single
   hue cannot.
2. **Two bands, driven by the hardware.** The S-mount lens ahead of the C-mount camera loses the ~650 nm
   region (the third Q-band), so the criterion uses only the **Soret-flank blue** and the **~575 nm Q-band**
   (+ a green-window anchor). We designed *around* the optics rather than pretend the red band is there (§2).
3. **A *ratio*, not absolute absorption.** `G = D_Q / A_denom` cancels concentration × path length (both
   bands scale with it) → robust to how much oil is in the beam; and `A = −log₁₀(S/R)` already divides out
   the LED. The absolute features (`S_pig`, `clarity`) are kept only for the axes that genuinely need a fixed
   sample geometry (§3).
4. **Reference-gated blue window (a hybrid, evaluated per session).** The blue is the fragile end —
   saturated Soret below ~450, the LED **cyan dip** above ~480. So the blue window is bounded by *reference
   health* (keep λ where the LED is still bright), not a hard-coded wavelength: it divides out the LED but
   trust follows brightness, so we sample where the lamp is strong (§3.2).
5. **Generic ops + plugin composition — NO shared `PeakRatioLogicModule`.** The shared code is only the
   *generic* `SpectrumFeatureUtil` ops (band-mean, peak-in-range, linear-baseline, reference-gated-band); the
   pumpkin band constants + feature composition live **in the plugin**. This keeps the shared layer reusable
   by any use-case and the plugins independent — the objection to a "shared but pumpkin-specific" module (§7).
6. **Bench-first, render-only first sweep.** Physics gives the *sign* of every correlation; only real-oil
   measurement gives the *thresholds* — and even the sign must be confirmed on this rig. So the first sweep
   **renders** the metrics (both `G_green` and `G_blue`) with a *provisional* verdict; saving + calibrating
   against known-good/bad oils (→ real edges) is a deliberate later step (§8, P5).
7. **Evaluation is its own workflow phase, owned by a plugin.** Not view code and not a Processing tab: the
   bench's `DevSpectralPlugin.evaluation` produces the `EvaluationResult`; the workflow's EVALUATION phase
   renders it. This mirrors the production pipeline (the pumpkin plugin will do the same), so the bench is a
   faithful rehearsal of the real thing (§4, `SPEC_dev_measure_bench.md` §15).
8. **Metric-field rendering + measurement UX.** Metrics are shown as Spectrometer-setup-style rows (gray
   label chip + read-only field, click-for-tooltip description) so they read as *values you can trust*, not
   prose; the acquisition shows the spectra building live per frame with a progress bar. These make the
   bench a usable *calibration instrument*, which is its whole point (`SPEC_dev_measure_bench.md` §16–18).

---

## 1. Why (physics) — the two usable pigment bands

Styrian pumpkin-seed oil's green colour comes from tetrapyrrole pigments (protochlorophyll/protopheophytin)
with a classic **Soret + Q-band** absorption signature (`KB_led_and_oil_spectra.md` §2, Fruhwirth Fig. 3A):

| Band | ~λ | What it is | Specificity |
|---|---|---|---|
| **Soret** | ~430 nm | strong blue absorption | **mixture:** pigment Soret **+ carotenoid (~445–475)** **+ Maillard roast-browning** |
| **Q-band 1** | **~575–580 nm** | weak green-pigment fingerprint | **clean:** intact green pigment only (no carotenoid, ~no browning) |
| Q-band 2 | ~630 nm | second Q-band | **LOST** with the current optics (see §2) |

The green transmission window (~500–560 nm) sits *between* Soret and Q-bands; roast-browning inflates the
blue while depleting the specific green pigment → **the two bands move in opposite directions with roast**,
which is exactly what makes a ratio informative.

## 2. Hardware constraint driving "two bands only" (Edwin, 2026-07-09)

The current rig — an **S-mount 12 mm / 16 mm lens ahead of the C-mount camera** — does **not** deliver the
**~650 nm region** (small S-mount optics roll off / vignette hard at the red end; confirmed by the bench
spectrum fading to ~0 past ~655 nm and by the app's analysis window clamping at ~692 nm). So the **~630 nm
Q-band is unusable**. This spec therefore uses **only Band 1 (Soret/blue) and Band 2 (~575 Q-band)**. If red
throughput is fixed later, a third-band extension is a follow-up (§10).

## 3. Feature definitions (on the ABSORPTION spectrum A(λ) = −log₁₀(S/R))

The `processing` hook already stores an `ABSORPTION`-role `Spectrum` (`AbsorptionOp`); its
`valuesByNanometers` is a `{float nm: A}` dict. All features are computed from it (optionally after
`SpectrumUtil().smooth(...)`). **Read by nearest-nm-within-window** — there is no nm-target accessor today
(§7), so define a helper `bandValue(A, λ0, halfWindow)` = mean of A over `[λ0−hw, λ0+hw]` (skip masked gaps).

### 3.0 Quantities at a glance

**Base (per wavelength λ):** `R` = reference (LED, no oil) · `S` = sample (through oil) · `T = S/R`
transmission · `A = −log₁₀T` absorption.

> **Naming:** the greenness *ratio* is **`G`** (not `R`) — `R` is reserved for the reference spectrum, to
> avoid the collision that used to make the two hard to tell apart.

| Quantity | Formula | Role | Path-dep? |
|---|---|---|---|
| `A_blue` | `mean{ A(λ) : λ ∈ W_blue }`, `W_blue = [450,490] ∩ {R(λ)≥0.25·R_bluepeak} ∩ {A(λ)≤1.5}` | ① blue window — browning proxy (§3.2) | scales conc×path |
| `A_green` | `mean{ A(λ) : 510 ≤ λ ≤ 540 }` | ② green anchor — clarity / normalizer (§3.3) | scales conc×path |
| `D_Q` | `mean{ A(λ):570–580 } − base_Q`, `base_Q = A(555)+[A(600)−A(555)]·(575−555)/(600−555)` | ③ Q-band depth — green pigment (§3.1) | scales conc×path |
| **`G`** (greenness) | `D_Q / A_denom`, `A_denom ∈ { A_green default, A_blue alt }` | headline verdict driver (§3.4, §4) | **ratio → cancels** |
| browning | `A_blue / A_green` | roast axis, pigment-independent (§3.4) | **ratio → cancels** |
| clarity | `A_green` | turbidity / darkening floor (§3.4) | **needs fixed geometry** |
| `S_pig` | `D_Q` | absolute pigment strength (§3.5) | **needs fixed geometry** |
| verdict | `G>underEdge→UNDER`, `G<overEdge→OVER`, else `PERFECT` | edges calibrated on real oils (§4, §8) | — |

**Path/concentration (Edwin uses a fixed concentration + volume):** the ratios (`G`, browning) are already
path-independent; the *absolute* features (`S_pig`, `clarity`) are the ones that require the fixed geometry
to be comparable across samples. The reference `R` is the lamp (measured on the blank) — it does **not**
depend on the oil concentration. All band reads are single-window means → **skip masked gaps** and read a
small window (not an exact nm key — the keys are polynomial floats, §12/R6).

Illustrative (~`capture001`): `A_blue≈0.34`, `A_green≈0.12`, `D_Q≈0.24` → `G_green≈1.9`, `G_blue≈0.69`,
browning≈2.8. **Diagram of the three bands on A(λ):** `spectracs-docs/pumpkin_peak_ratio_bands.png`.

### 3.1 Band 2 — green-pigment Q-band depth `D_Q` (the specific signal, PRIMARY)
**This is the one clean, confirmed absorption peak in the bench captures** (`capture001`, A≈0.46 at ~570 nm)
— the robust, well-conditioned feature the whole criterion should lean on. It sits on the Soret tail, so use
a **local-baseline-corrected depth**, not the raw value:
```
baseline575 = linear interp between A(λL) and A(λR),  λL≈555, λR≈600
D_Q         = bandValue(A, 575, hw=5) − baseline575(575)
```
`D_Q` ≈ amount of intact green pigment. (Fresh oil: a clear positive bump; degraded: → 0.)

### 3.2 Band 1 — blue absorption `A_blue` (the "everything that browns" signal, WEAKER feature)
**There is no discrete blue *peak* to sample.** In the bench captures the absorption spikes at the far-left
edge (~445 nm, A≈2.5 — the saturated true Soret ~430, where T→0 → noise, and the transmission floor-guard
`TransmissionLogicModule.DEFAULT_REFERENCE_FLOOR_FRACTION` + weak deep-blue LED can mask it) and then slides
monotonically down through the blue into the low green-window floor. So the blue signal is a **slope/edge,
not a peak** — a single-point value (e.g. at 465 nm) is calibration-fragile (a few nm of drift → a big A
change). Therefore define `A_blue` as a **windowed mean over the Soret downslope, bounded from BOTH ends by reference
health, not fixed wavelengths**:
```
A_blue = mean( A[λ] for λ in W_blue )
  W_blue = [450, 490]                          # fixed physical guardrails
           ∩ { λ : R[λ] ≥ R_health · R_bluepeak }   # reference-health gate — trims the cyan dip
           ∩ { λ : A[λ] ≤ A_sat_ceiling }           # saturation guard — trims the saturated Soret
  R_bluepeak = max R over ~450–465;  R_health ≈ 0.25–0.30;  A_sat_ceiling ≈ 1.5
```
**Hybrid window, evaluated once per session (SETTLED with Edwin, 2026-07-09).** Fixed outer guardrails cap
the physics (below ~450 = saturated Soret; above ~490 = green window / deep carotenoid — same on every rig);
the **reference-health gate** trims the array-specific **LED cyan dip** *inside* them. Key point: the LED
fall-off is *not* a bias source — `A = −log₁₀(S/R)` divides the LED envelope out — but where `R` is weak, `A`
is **noisy** (and below the 1% floor, **masked**), so "keep it where the lamp is bright" is the right rule.
Because the **reference is captured once per session and reused for every sample**, the gated window is
**fixed within a comparison set** (adapts only across arrays/aging) — deterministic when comparing oils,
adaptive when hardware changes. Compute it once from the session `R`, and **log which wavelengths it kept**
(no silent trimming). Still the weaker feature (carotenoid-contaminated slope) — its **job is to rise with
browning**, and it is a *diagnostic*, not the default denominator (§3.4).

### 3.3 Band 3 — green-window anchor `A_green` (clarity floor + reliable normalizer)
The **absorption *minimum* / transmission *maximum*** at ~510–540 nm — the clear window between the Soret and
the Q-band (the green you see). Measure `A_green = mean A over ~510–540` (flat region; equivalently the
transmission peak). It is the **highest-SNR region of the whole spectrum** (LED green peak strong, oil
absorption low & flat). Three jobs:
- **Reliable normalizer** — a far steadier denominator than the fragile `A_blue` (§3.4). *Guard:* it can go
  near-zero for a very clear oil → floor/clamp before dividing (in practice a turbidity floor keeps it ~0.1–0.2).
- **Clarity / turbidity feature** — rises with scattering, heavy-roast darkening, sediment; a quality signal
  the two narrow pigment bands can't see.
- **The pivot** that lets the three axes separate (§3.4).

### 3.4 Features & the three-axis decomposition
Three bands give three semi-independent readings instead of one overloaded ratio:

| Axis | Feature | Meaning |
|---|---|---|
| **pigment** | `D_Q` (baseline-corrected Q-band, §3.1) | intact green pigment |
| **browning** | `A_blue / A_green` (blue→green slope) | short-λ browning, isolated from pigment |
| **clarity** | `A_green` (§3.3) | non-selective turbidity/darkening floor |

Headline **greenness ratio `G`** (single-number verdict driver, §4):
```
G = D_Q / A_denom
```
`A_denom` is chosen at calibration (§8, §11): **`A_green` is the reliable default** (lead with the high-SNR
anchor); `A_blue` is the browning-sensitive alternative *if* it proves stable on the rig. Either way `G`
cancels path/concentration (all bands scale with conc×path) and A already divides out the LED → doubly
normalized. **Near-zero denominator guard:** floor `A_denom` to a small minimum before dividing, and mark
low-confidence if it hits the floor (applies to whichever band is `A_denom`).

### 3.5 Secondary feature — pigment strength `S_pig = D_Q`
Absolute (path-dependent) green-pigment amount. Needs the **fixed sample geometry** to compare across
samples. Distinguishes *faded/old* (low `S_pig`, ~normal `G`) from *over-roasted* (low `G`, high browning).
Reported alongside `G`; not the primary verdict driver in Phase 1.

## 4. Evaluation phase — features consumed & verdict

### 4.0 What the evaluation phase consumes
The evaluation reads the ABSORPTION spectrum `A(λ)` and computes, in order:
1. **Band reads** (§3.1–3.3): `A_blue`, `A_green`, `D_Q`.
2. **Features:** `G = D_Q/A_denom` (primary), `S_pig = D_Q`, `browning = A_blue/A_green`, `clarity = A_green`.
3. **Verdict + confidence** (§4.1).

**Minimal verdict set:** `D_Q`, `A_green` → `G`. **Full set** adds `A_blue` (→ browning) and `S_pig` (splits
*over-roasted* from *faded*). The diagnostic axes (browning, clarity) explain *why* a verdict came out and
drive the calibration analysis, even if the shipped threshold is a single cut on `G`.

**Confidence flag** — the evaluation must return **low-confidence** (not a false verdict) when: the blue
window is empty/saturated, `A_green ≈ 0` (near-zero denominator), or the Q-band baseline points (555/600)
fall in transmission-floor gaps (guards from §5).

### 4.1 Verdict mapping (mirrors the existing two-edge structure)

Roast direction from physics (**validate sign against real oils, §8**): browning lowers `G`, less roasting
keeps more green → higher `G`. So a **two-threshold band on `G`** parallels the current hue bands:

| Condition | RoastState |
|---|---|
| `G > underEdge` | **UNDER_ROASTED** (too green/raw) |
| `G < overEdge` | **OVER_ROASTED** (too brown) |
| otherwise | **PERFECT_ROASTED** |

Reuse `RoastState` (str-Enum). Add a `PeakRatioVerdictLogicModule` (+ `...Parameters` with `overEdge`,
`underEdge`) analogous to `VerdictLogicModule` (`overRoastedBelowHue=47`, `underRoastedAboveHue=66`). Edges
are **calibrated, not assumed** (§8) — seed with placeholders flagged "provisional/demo" exactly as the hue
edges are today.

## 5. Practical handling (must be in the design)

- **Saturation guard.** If `A_blue` itself exceeds a ceiling (e.g. > ~1.5) the blue is over-range → mark the
  measurement **low-confidence** (thin the sample / shorten path) rather than emit a false verdict.
- **Masked-gap guard.** If the 555–600 baseline points or the 465 point fall in a transmission-floor gap
  (no A value), surface "insufficient signal" — do not extrapolate.
- **Smoothing/baseline order.** Smooth (Savitzky-Golay, existing `SmoothSpectrumLogicModule`) **before**
  band extraction; the local linear baseline (§3.1) is per-band, not the morphological `removeBaseline`.
- **Fixed path for `S_pig`.** Only `R` is path-independent; if `S_pig` is used in the verdict, standardize
  the cuvette/film thickness.

## 6. Output / display

**Phase 1 — bench (plugin-driven EVALUATION tab).** `DevSpectralPlugin.evaluation` produces an
`EvaluationResult`; the bench renders it as a new **Evaluation tab** alongside the existing processing tabs.
It shows:
- a **`color` row** (2026-07-13): the sample's perceived colour as a metric-grid **swatch** (no target), computed
  by the plugin from the transmission via `EvaluationColorUtil` and emitted as a `MetricFieldView("color", color=rgb)`
  — the value cell renders a swatch instead of text, aligning in the same metric grid (SPEC_plugin_driven_convergence
  §3 ¶). Flagged `isShownInReport` so it also appears on the PDF;
- the three-axis features `D_Q`, `A_blue`, `A_green`, the ratio `G` (and the confidence flag), plus the
  provisional verdict band;
- **the three bands shaded on the Absorption plot** — the Q-band at ~575 (with its 555–600 baseline), the
  **reference-gated blue window** (show which λ the gate actually kept — and the actual peak-search λ, §12/R8),
  and the ~510–540 green anchor — so the human sees exactly what was measured (and that the cyan dip was
  excluded);
- **both** `G_green` and `G_blue` (denominator not yet fixed — §3.4), so the human can compare across oils.

**First sweep = RENDER ONLY, no persistence (Edwin, 2026-07-09).** Phase 1 just *renders* these numbers;
**no saving/export**, and the verdict band is **provisional** (real edges await calibration). A LATER step
(§10 P5) adds saving + testing different oils + mapping the quantitative values to qualitative descriptions
(good/bad, clear, strong) → then the calibrated verdict edges.

**Later — plugin verdict.** When wired into `PumpkinOilPlugin.evaluation`, keep the Qt-free `plugin_sdk`
boundary. `EvaluationResult` currently serializes `swatch|verdict|label|plot` (`EvaluationResult.py:41–78`).
Reuse existing views first — `VerdictView(roast.value)` + `LabelView("R = %.2f (D_Q %.2f / A_blue %.2f)")`
(zero serialization change); add a numeric `PeakRatioView {ratio, dQ, aBlue, overEdge, underEdge}` only if a
richer UI is wanted (that needs `EvaluationResult` (de)serialization **and** `plugin_sdk/__init__.py`
extended). Optionally keep `ColorSwatchView` (measured vs target) — colour and peak-ratio are complementary.

## 7. Where it plugs in (code map — generic ops + plugin composition; NO `PeakRatioLogicModule`)

**Architecture pivot (Edwin, 2026-07-09):** there is **no shared `PeakRatioLogicModule`.** Only **generic,
reusable spectral-feature ops** are shared; the **pumpkin composition** (band λ constants + which features)
lives **in the plugin**. See the third rubber-duck pass (§12) for the reasoning.

**Shared — generic spectral-feature ops (no pumpkin knowledge, reusable by any use-case):**
| Piece | File | Role |
|---|---|---|
| Feature util (façade) | **new** `SpectrumFeatureUtil` — Qt-free, exposed via `plugin_sdk` (like `MeanOp`/`AbsorptionOp`) | `bandMean(spectrum, lo, hi)` (window mean, skips gaps → `None` if empty); `peakInRange(spectrum, lo, hi) → (λ, val)`; `linearBaseline(spectrum, λ, aLo, aHi)`; `referenceGatedBand(value, gate, lo, hi, gateFrac, valueCeiling)` (2-spectrum). Trivial ones are **util functions**; only `referenceGatedBand` (and `peakInRange` if it wraps `find_peaks`) warrant a backing `logic/spectral/feature/…LogicModule`. Each op returns a value **or `None`** (the low-level "couldn't compute" guard — §12/R7). |

**Phase 1 — bench plugin *composes* the ops with HARD-CODED pumpkin constants (Edwin's #1 decision):**
| Piece | File | Change |
|---|---|---|
| Evaluation hook | `DevSpectralPlugin.evaluation` (currently `pass`) | read `ABSORPTION` + meaned `REFERENCE` (both already in its PROCESSING — the ABSORPTION step + the "Spectra" step); **compose the generic ops with hard-coded pumpkin λ's** (450–490, 510–540, 575, 555/600, gate 0.25, ceiling 1.5) → `D_Q, A_blue, A_green, G_green, G_blue, browning, clarity`; own the **composition-level guards** (floor `A_denom`, confidence flags — §12/R7); build an `EvaluationResult` (metrics as `LabelView`s + provisional verdict) → EVALUATION phase step. *No shared feature-config yet — pumpkin-specifics live here for now (bench was meant generic; accepted).* |
| Bench view | `DevMeasurementBenchViewModule.py` | run `runPhaseHook(EVALUATION)` in `__runProcessing`, append an **Evaluation tab** (readout + band markers, §6). **RENDER ONLY — no export** (§12/R3 postponed). |

**Later — pumpkin plugin (independent) & shared-config refactor:**
| Piece | File | Change |
|---|---|---|
| Reference in PROCESSING | `PumpkinOilPlugin.processing` | add the meaned REFERENCE (as the bench plugin has) so *its* evaluation can feed the gate |
| Wire-up | `PumpkinOilPlugin.evaluation` | compose the **same generic ops** with the pumpkin constants; emit views (§6); may A/B alongside the hue verdict |
| Refactor (when 2nd consumer appears) | shared pumpkin **feature-config** (constants object, **not** logic) | promote the hard-coded constants to a small config both plugins read — avoids duplication. Deferred until now. |

`Spectrum.valuesByNanometers` keys are **floats** — the ops read a **small window** (never an exact-nm key)
and skip masked gaps (§12/R6). The existing `find_peaks` wrapper works in **pixel-index** space; a generic
`peakInRange` over nm is the right primitive here.

**Verdict** (`RoastState` via two edges, §4): a `PeakRatioVerdictLogicModule` is only needed at P5 (real
calibrated edges). Until then the plugin emits a **provisional** verdict inline.

## 8. Calibration protocol (mandatory before shipping a threshold)

Physics gives the **sign**; only measurement gives the **thresholds** — and even the sign must be confirmed
on *this* rig.
1. Measure a handful of oils of **known quality** (trusted good / over-roasted / faded) on the actual
   S-mount rig, fixed path.
2. Plot `R` (and `S_pig`) per sample; confirm good oils separate (expected: good = higher `R`).
3. Set `overEdge`/`underEdge` from the observed separation (or a tiny 1-D boundary on `R`; 2-D on
   `R`×`S_pig` if one feature is insufficient).
4. Anchor against precedent: Lankmayr et al. (2004) classified 186 Styrian oils by UV-Vis+NIR+FTIR
   chemometrics into sensory-quality classes (`spectracs-references/articles/`). Treat the local historical
   `.dx`/`.sgd` oil spectra as **provisional** (unknown provenance — `KB_led_and_oil_spectra.md` §4).

## 9. Caveats / non-goals

- **Quality/roast only — NOT authentication.** Colour/pigment ratios cannot detect adulteration/blending
  (Balbino et al. 2022 — CIELAB couldn't separate sunflower-cut PSO; only NIR could). Keep any purity claim
  out of this verdict.
- **Sign of the `R`→roast correlation is a hypothesis** until §8 confirms it on real samples.
- **Two-band limitation is optics-driven**, not fundamental — revisit if the red end is recovered (§10).
- `PERFECT_HUE`/hue path may be kept in parallel initially (A/B the two verdicts) before removing hue.

## 10. Implementation phases (implement on explicit request) — bench-first, render-only first sweep

```
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| Ph | What                             | New / Touched                  | Gate (drive-and-observe)          | Risk    |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P0 | Generic spectral-feature ops:    | NEW SpectrumFeatureUtil        | Drive on a real/synthetic A(λ):   | LOW     |
|    | bandMean/peakInRange/linear-     | (+ backing logic module for    | ops return sane band values;      |         |
|    | Baseline/referenceGatedBand      | the non-trivial ones). NO tests| None on empty/masked. (No tests.) |         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P1 | DevSpectralPlugin.evaluation     | TOUCH DevSpectralPlugin (pass  | Workflow gains an EVALUATION step;| MED     |
|    | COMPOSES the ops w/ hard-coded   | -> compose ops; __findAbsorption| numbers sane vs capture001        | (phase  |
|    | pumpkin consts -> EvaluationResult| + __findReference)            | (G_green~1.9 etc.). No tests.     | added)  |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P2 | Bench renders it: Evaluation tab | TOUCH DevMeasurementBench       | Eval tab shows G_green/G_blue/D_Q/| MED     |
|    | (metrics readout + band-marked   | ViewModule (__runProcessing:   | A_blue/A_green + bands shaded on  |         |
|    | A(λ) plot). RENDER ONLY, no save | run EVAL hook + __evaluationTab)| A(λ). No persistence.            |         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P3 | Bench acquisition: role combo -> | TOUCH DevMeasurementBench       | Reference/Sample = two tabs; one  | LOW-MED |
|    | two tabs (Reference / Sample)    | ViewModule (combo -> QTabWidget)| stream; exposure-lock + N2 intact.|         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P4 | Shared extended-ROI overlay in   | NEW ExtendedRoiLogicModule     | Capture + bench previews draw the | LOW     |
|    | capture view + bench preview     | (promote BenchRoiLogicModule); | 400-700 box; matches analysed win.|         |
|    | (draw the 400-700 window)        | TOUCH capture §11 + bench       |                                   |         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P5 | LATER: save metrics + test oils  | NEW feature persistence/export;| Metrics saved per oil; quant->qual| MED     |
|    | -> quant->qual bounds -> real    | PeakRatioVerdictLogicModule    | bounds derived; real verdict edges|         |
|    | verdict edges (§8 calibration)   | (calibrated edges)             | set. (Edwin's later step.)        |         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
| P6 | LATER: pumpkin plugin composes   | TOUCH PumpkinOilPlugin (proc + | Independent plugin: add meaned ref| MED     |
|    | the SAME generic ops; promote    | eval); NEW shared feature-     | to processing; composes ops; may  |         |
|    | consts to a shared feature-config| config (constants, not logic)  | A/B vs hue. Consts now shared.    |         |
+----+----------------------------------+--------------------------------+-----------------------------------+---------+
Order: P0 -> P1 -> P2;  P3 & P4 independent (any time after P0/P1);  P5 after P2;  P6 after P5.
```

**Note:** the §8 calibration pass is folded into **P5** — it needs the P2 render *and* the P5 saving to build
the good/bad dataset. **No verdict thresholds ship before P5.** P1–P2 are the render-only first sweep
(metrics shown, verdict provisional). (Optional after P6: `PeakRatioView` + serialization; future third-band
~630 if red throughput is fixed.)

**Status: P0–P4 IMPLEMENTED 2026-07-09 (headless-verified; awaits click-through).** P0 `SpectrumFeatureUtil`
+ `SpectrumFeatureLogicModule`; P1 `DevSpectralPlugin.evaluation` composes the ops with hard-coded pumpkin
constants → `EvaluationResult` (verified `G_green≈1.907`, `A_blue≈0.428` with the ref-gate trimming the cyan
dip at ~473 nm, vs `capture001`); P2 bench Evaluation tab (`EvaluationResultRenderer` + band-shaded A(λ)
plot); P3 role combo → two tabs; P4 shared `ExtendedRoiLogicModule` (promoted from `BenchRoiLogicModule`),
capture-view overlay + bench preview draw the 400–700 window. **P5** (save + calibrate → real verdict edges)
needs real-oil measurements — deferred. **P6** (pumpkin plugin) — separate follow-up.

**Restructure requested after the bench run (Edwin 2026-07-09; DESIGN, implement on request) — `SPEC_dev_measure_bench.md` §15:**
P2's Evaluation moves from a Processing *tab* to its **own EVALUATION phase** (StepBar Acq|Proc|Eval, eval
hook runs on phase entry) — **E1**; the acquisition UI restructures to a role tab-bar + a shared
`[ Captured image | Spectrum ]` container (Option A), auto-exposure shows the image tab / after-capture shows
the spectrum tab — **E2/E3**. The P0/P1/P4 logic is unchanged.

## 11. Open questions

- **Denominator confirmation** (Edwin): §3.4 leads with **`A_green` (the high-SNR green anchor)** as the `G`
  denominator, `A_blue` as the browning-sensitive alternative. Calibration confirms which separates real
  oils better — and whether the 3-axis `(D_Q, A_blue/A_green, A_green)` beats a single ratio. Also settle
  `R_health`, the blue guardrails, and the `A_denom` near-zero floor.
- Is `G` alone enough, or is the 2-feature (`G`,`S_pig`) boundary needed to split over-roasted from faded?
  → decide from §8 bench data.
- Under-roasted band: does "too green" ever occur in practice for PSO, or collapse to a single
  good/over-roasted threshold? → §8.

## 12. Rubber-duck pass — implementation risks & missing pieces (2026-07-09, vs as-is code)

Surfaced by ducking the design against the actual plugin/pipeline code. Recorded, not all resolved.

### Structural
1. **Reference `R` availability — RESOLVED by the plugin-driven model.** The blue gate (§3.2) needs `R`.
   Since plugins are **independent**, each plugin feeds `R` from its **own** `processing` to its own
   evaluation — no shared cross-plugin coupling. The bench's `DevSpectralPlugin.processing` already carries
   the meaned reference (the "Spectra" step) → its evaluation reads it directly. `PumpkinOilPlugin`
   currently stores only ABSORPTION+TRANSMISSION, so it must **add the meaned reference** when peak-ratio
   lands there (§7, §10.5). (Original "asymmetry" worry dissolved — it was an artefact of trying to share
   one extraction path across two plugins.)
2. **Sample-presentation / path length — DECIDED (Edwin): fixed concentration + volume.** Needed because
   the *absolute* features (`S_pig`, `clarity`) scale with conc×path; the ratios (`G`, browning) are
   already path-independent (§3.0). Pin the exact cell/geometry so the absolute features are comparable
   across the calibration set.
3. **Feature-capture for calibration — POSTPONED (Edwin).** First sweep (P1–P2) **renders metrics only, no
   saving**. A LATER step (P5) adds persistence + testing different oils + mapping the quantitative values to
   qualitative descriptions (good/bad, clear, strong) → that's when `overEdge`/`underEdge` get set. So the
   verdict is *provisional* until P5; the "metric bounds for good vs bad oils" come from the P5 dataset.

### Correctness / robustness
4. **Smoother erosion of `D_Q` — NOT AN ISSUE (verified).** The bench T/A pipeline (`MeanOp`→`TransmissionOp`
   →`AbsorptionOp`) applies **no smoothing at all**, so `D_Q` is intact by default. (The lightened smoothing
   Edwin recalls was on the *calibration peak-detection* path — different code.) Only add **light** smoothing
   if the far tail proves noisy; never the default 7-pass `SmoothSpectrumLogicModule`.
5. **`D_Q` should search the local max, not hard-read 575.** Calibration error / neat-vs-solvent shift moves
   the Q-band a few nm; a fixed 570–580 window can clip it. Use a **local-max search in ~565–590**, measure
   depth there.
6. **Float-nm keys → window/nearest reads — HANDLED.** `valuesByNanometers` keys are polynomial floats
   (no exact `555.0`), so `bandValue` always reads a **small window mean** and **skips masked gaps** (the
   transmission floor-guard leaves holes, esp. in the blue) — never an exact-key lookup. Window reads are
   also immune to the JSON float-key round-trip on the persisted plugin path
   ([[spectracs-workflow-persistence-spec]]).
7. **Near-zero denominator — HANDLED.** Floor whichever band is `A_denom` (`A_green` or `A_blue`) before
   dividing; flag low-confidence if it hits the floor (§3.4).
8. **px→nm calibration dependency — LOW RISK.** The calibration is high-fidelity (Edwin), so bands land
   correctly; R5 (peak search) + R1 (reference gate) absorb any small shift. The bench readout showing the
   **actual λ each band used** (§6) is a cheap sanity display, not a fix for a suspected problem.

### Integration
9. **Bench evaluation is plugin-driven — RESOLVED (Edwin).** Not view-level: `DevSpectralPlugin.evaluation`
   (today `pass`) runs the shared `PeakRatioLogicModule` → `EvaluationResult` → the bench renders an
   **Evaluation tab**. `PumpkinOilPlugin` is a separate, independent plugin that uses the same module. The
   extractor is shared logic **used by the plugin**, never the view (§7, scope).
10. **Two verdicts coexisting** (hue + peak-ratio A/B) → two `VerdictView`s in one `EvaluationResult`;
    acceptable (Edwin) — the `EvaluationResult` (de)serialization + UI must show both.

### Second rubber-duck pass — vs the updated plugin-driven / render-only / two-tabs / shared-ROI design (2026-07-09)

**Structural**
11. **The bench gains an EVALUATION phase — its phase machinery must absorb it.** The bench hard-codes
    `__phases = [ACQUISITION, PROCESSING]` + StepBar `["Acquisition","Processing"]` + a 2-page stack. Now
    `DevSpectralPlugin.evaluation` emits a step → an EVALUATION phase appears. Reconcile "Evaluation **tab**"
    with the engine's **phase** model: simplest is the bench view **flattens PROCESSING+EVALUATION steps
    into one tab strip** (…Absorption │ Evaluation), not a third StepBar phase. Either way
    `__phases`/StepBar/stack/nav need touching (P2).
12. **Render-only ⇒ no calibrated verdict yet.** P1–P2 render metrics (show **both** `G_green` and `G_blue`)
    but the verdict has **no real edges** (calibration = P5). Show a clearly *provisional* verdict — don't
    imply a trustworthy good/bad in the first sweep.

**Integration**
13. **Rendering an `EvaluationResult` in the bench needs a renderer + a custom band-plot.** Reuse the
    wizard's `EvaluationResult` renderer if one exists, else a small bench one. The **band-marked absorption
    plot is not a standard view type** → add one, or the bench draws markers directly on its Absorption tab
    (pyqtgraph `LinearRegionItem`/`InfiniteLine`).
14. **Extended-ROI overlay needs the frame width, and should also appear in the bench acquisition preview.**
    Drawing the 400–700 box requires inverting nm→px via the calibration + the frame width (known only after
    a frame) → compute on first frame (as bench §12 does). Show the shared overlay in **both** the capture
    view and the bench's live ref/sample preview.

**Minor**
15. **`DevSpectralPlugin.evaluation` reads two steps** — ABSORPTION (absorption step) + the meaned REFERENCE
    (the "Spectra" step). Add `__findAbsorption` + `__findReference`.
16. **Two-tabs refactor touches live state** — exposure-lock, N2 (fresh reference clears sample),
    `__stepForRole`, per-role plots must survive the combo→tabs swap; re-point `__onRoleChanged` →
    tab-changed (widget change, not logic).

### Third rubber-duck pass — generic-ops vs a shared `PeakRatioLogicModule` (2026-07-09)

Edwin: `PeakRatioLogicModule` is **too specific** — it bakes pumpkin band-constants + composition into a
"shared" module that is neither generic nor plugin-owned. **Pivot: no `PeakRatioLogicModule`.** Only
**generic spectral-feature ops** are shared; the **plugin owns the composition** (§7).

17. **Bench-shows-pumpkin-features vs composition-in-plugin — RESOLVED (Edwin #1).** For now,
    `DevSpectralPlugin.evaluation` **hard-codes the pumpkin constants** and composes the generic ops
    directly. Accepted that the "generic" bench plugin takes on pumpkin-specifics for now; a shared
    **feature-config** (constants, not logic) is deferred to P6 when the pumpkin plugin becomes the 2nd
    consumer.
18. **Qt-free boundary — the generic ops go through `plugin_sdk`** (wrap logic modules like `MeanOp` does);
    `SpectrumFeatureUtil` is the façade. Plugins stay `plugin_sdk`-only.
19. **`referenceGatedBand` is a 2-spectrum op** (value A + gate R). Generic ("mask a band by a gate
    spectrum's health"), just a 2-input signature.
20. **Proportion — util functions, not a `LogicModule` per one-liner.** `bandMean`/`ratio`/`linearBaseline`
    are util functions; only `referenceGatedBand` (and `peakInRange` if it wraps `find_peaks`) get a backing
    logic module.
21. **Guard split (was §12/R7, clarified).** Low-level "couldn't compute" → the generic op returns `None`;
    use-case "what that means" (floor the denominator, set confidence) → the plugin composition. Don't put
    pumpkin-confidence logic in a generic op.
22. **No unit tests for now (Edwin #6).** Verification is drive-and-observe (numbers sane vs `capture001`);
    granular op tests deferred.

## 13. Cross-references

- `KB_led_and_oil_spectra.md` §2 — the two-band physics + "our bench reproduces Fig. 3A".
- `spectracs-references/articles/Fruhwirth_Hermetter_2007_SUMMARY.pdf` — the three peaks / ~575 Q-band digest.
- `SPEC_pumpkin_integration.md` — the plugin/engine architecture this modifies (Track C, `PumpkinOilPlugin`).
- `SPEC_measurement_evaluation_concept.md` — the green→brown roast-verdict concept.
- [[spectracs-pumpkin-peak-ratio-task]] — origin; `spectracs-docs/ROADMAP.md` deferred thread.
