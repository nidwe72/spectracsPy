# SPEC — Pipeline Playground (test/dev bench)

> Status: **IMPLEMENTED 2026-06-30** (all 7 phases). Verified: Phase-2–5 logic unit-tested headless;
> Phase-1 CFL calibration runs DB-free (advanced matcher) → px→nm cubic (404–635 nm); click-through of
> the 4 tabs as master (calibration image, reference SPD, 3 oil spectra, measured-vs-target swatches +
> verdicts); role-gating confirmed (Playground hidden when logged out).
>
> Demo hues used: **UNDER 72° / PERFECT 60° / OVER 35°** (green → yellow-green → brown). These are the
> hues real oil-like transmission actually yields through the (correct) colour pipeline — the achievable
> green→brown range is naturally narrow (the oil's colours don't "breathe" far), not a defect.
>
> A master-only top-level view that
> runs the spectral pipeline on **synthetic** REFERENCE and SAMPLE spectra and shows the result. It is
> the dev shortcut for what the pumpkin **plugin** will do. Builds on
> `SPEC_measurement_evaluation_concept.md` (the sound pipeline), `KB_spectroscopy_physics.md`,
> `KB_led_and_oil_spectra.md`. Bridges Roadmap **#5** (virtual-device images, *deferred here*) and **#6**
> (absorption + evaluation).

---

## 1. Goal & scope (first cut)

Display, in the playground, the pieces of one synthetic run as **flat tabs**:
1. the **CFL calibration image** (→ the px→nm polynomial),
2. the synthesised **reference spectrum**,
3. the synthesised **oil sample spectra** (3 demo oils),
4. the **measured-vs-target colour** for each oil.

Known-provenance, fully controlled (every parameter ours; **no captured/unknown data**). **Reuse the same
utility methods the plugin will use** (`SpectrumUtil`, `SpectralColorUtil`) + new reusable **logic
modules/ops** — so the playground *is* the first real implementation of #6's building blocks.

**First-cut scope:** **spectra-only** — synthesise directly on the calibration's nm axis; **no image
round-trip**. **Deferred:** the virtual-device 3-image slots (#5), an interactive LED picker, the
LED-swap stability check (§11). **Non-goals:** end-user wizard, run persistence, real verdict thresholds.

## 2. The tabs (3 oils, flat — no nested selector)

| Tab | Shows | Backed by |
|---|---|---|
| **1 · Calibration** | `testSpectra/cfl_philips_calibration.png` + the fitted px→nm polynomial | §3 |
| **2 · LED setup** | each Avonec LED's SPD + the overall reference `R(λ)` (white) | §4 |
| **3 · Reference spectrum** | the synthesised LED reference `R(λ)` (pyqtgraph plot) | §4 |
| **4 · Oil spectra** | the 3 synthesised sample spectra `S(λ)` (under/perfect/over-roasted), overlaid | §5 |
| **5 · Absorption** | per oil: absorbance `A = −log10(T)` (the transmission valley shifts with roast) | §6 |
| **6 · Camera capture** | the dispersed strips the sensor would see — REFERENCE rainbow + each oil's transmitted window | §3–§5 |
| **7 · Measured vs target** | per oil: measured swatch `colour(T)` next to its target swatch (3 pairs) + verdict | §6–§8 |

The page is a `PageWidget` whose main-container widget is a `QTabWidget` (mirror
`SpectralJobsWidgetViewModule`). Tabs share one `SpectraContainer` chain.

## 3. Calibration — fresh & automatic (CFL)

- Use a **dedicated playground virtual spectrometer profile**; feed `cfl_philips_calibration.png` as its
  virtual camera image and run the **existing automatic HEURISTIC calibration** — the only wired path: a
  **consensus** of prominence anchor-and-grow + predict-and-snap
  (`SpectrometerWavelengthCalibrationConsensusLogicModule`; RANSAC/rascal modes are placeholders, unused).
  It detects the bright lines, matches them to the **CFL master-data nm** in `SpectralLineMasterDataUtil`
  (Hg 405.4, 436.6, Tb aqua, Hg green ×2, …), and fits the **cubic px→nm** (`SpectrallineUtil.polyfit`).
  **This already works in the live app.** Output: a `SpectrometerCalibrationProfile` (ROI + polynomial).
- **The polynomial is what the playground needs** — it defines the **nm axis** the spectra are
  synthesised on. (ROI matters only for the deferred image path, §11.) **Verify** the known CFL lines map
  back to their nm.

## 4. Reference synthesis — `LedReferenceSynthesisOp`

- `R(λ) = Σ weightᵢ · SPDᵢ(λ)`, evaluated on the calibration nm axis. **Per-LED SPD = the shop's
  MEASURED spectrum** (digitised from the Avonec Spektralmessung JPGs in `spectracs-references/`;
  whites are bimodal pump+phosphor → measured is mandatory). **390–410 UV-A (the only LED without a
  measured curve) → synthesised with luxpy** (decided; luxpy is installed). Including it also fills the
  violet edge (<410 nm) so `R` isn't ~0 there — easing the low-`R` division guard (§6).
- **Default set** (first cut, fixed): 2× warm-white + hyper-violet + royal-blue + green + red + deep-red
  — gap-free, strong in the diagnostic bands 430–480 / 520–560 / 630–670. Output:
  `SpectraContainer{reference:[R]}`.

## 5. Sample synthesis — `OilSampleSynthesisOp` (physical, 3 demo oils)

- `S(λ) = R(λ) · 10^(−A_oil(λ) · c·l)` with
  `A_oil(λ) = chlorophyll(Soret≈430, Q≈665) + carotenoid/lutein(≈440–480) + browning(↗ short-λ)`.
- **`c·l` (concentration × path) + browning amplitude** are the green→brown knobs (Beer–Lambert
  dichromatism).
- **3 fixed presets, named by roast state**, tuned so `colour(T)` lands on each demo hue (§8):
  **PERFECT-ROASTED** (~80°), **UNDER-ROASTED** (~100°, greener), **OVER-ROASTED** (~45°, brown). Output:
  `SpectraContainer{sample:[S_perfect, S_under, S_over]}` (`inputs=[reference]`).

## 6. Process — Transmission & Absorption (**logic module + utility shortcut**)

Per the established per-op pattern (like `MeanSpectrumLogicModule`), **two-input** (reference + sample):
- **`TransmissionLogicModule`** (+ `…Parameters{reference, sample}` + `…Result{spectrum}`) → `T = S/R`.
- **`AbsorptionLogicModule`** (+ `…Parameters` + `…Result`) → `A = −log10(T)`.
- **`SpectrumUtil` shortcuts:** `SpectrumUtil.transmission(reference, sample)` and
  `SpectrumUtil.absorption(reference, sample)` — the convenience façade (note: two-arg, unlike the
  existing single-spectrum ops).
- Condition both R and S first (`smooth → removeBaseline → rebin 380–780 → normalize`) so they share the
  grid before dividing. **Guard division where `R` is low** (floor `R` / mask sub-threshold λ) so a dip
  can't blow up `T`. `T` feeds colour; `A` is the absorption plot.

## 7. Evaluate — colour & verdict

- **`QColor = SpectralColorUtil.spectrumToColor(T)`** (fixed D65 → LED-independent; concept §3) → measured
  **hue / lightness / saturation**.
- `EvaluationResult` view-models: **`ColorSwatch`** (measured), **`ColorSample`** (the oil's target),
  **`Label`** (hue/L/S), **`Verdict`**. First concrete take on **`EvaluationResult` → GUI rendering**.

## 8. Demo hue anchors & verdict band (CONFIRMED)

Hue in degrees (`colorsys` hue × 360), swatch saturation fixed at **0.85** (display), rendered at the
pipeline's fixed lightness 0.20. **Quality is perfect-centred, NOT monotonic** — a *target* hue with
deviation worse on both sides:

Presets and verdict labels use **one roast-state vocabulary** (no separate quality names):

| Preset = verdict label | Target hue | Reads as (L0.20 / L0.40) |
|---|---|---|
| **PERFECT-ROASTED** | **~80°** | `#415e08` / `#83bd0f` (yellow-green) |
| **UNDER-ROASTED** | **~100°** | `#255e08` / `#49bd0f` (fresher green) |
| **OVER-ROASTED** | **~45°** | `#5e4908` / `#bd910f` (brown/amber) |

**Verdict band (provisional/demo):** **PERFECT-ROASTED** ≈ 80° ± tolerance; **UNDER-ROASTED** = too green
(hue ≳ 90°); **OVER-ROASTED** = too brown (hue ≲ 65°). Exact edges are demo-only and derive from the
presets' achieved hues; **real thresholds need provenance-known captures** (concept §8).
The `oilScores.svg` palette is **display-only** (hue-degenerate — all 80°, differ in lightness), **not** a
threshold source.

## 9. Reuse vs greenfield

| Reuse (implemented) | New (greenfield, plugin-SDK-shaped) |
|---|---|
| `Spectrum`, `SpectraContainer` (fix dup-`__init__`) | `LedReferenceSynthesisOp` (LED SPDs → R) |
| `SpectrumUtil` mean/smooth/removeBaseline/rebin/normalize | `OilSampleSynthesisOp` (R + oil model → S) |
| `SpectralColorUtil.spectrumToColor` | `TransmissionLogicModule` + `AbsorptionLogicModule` (+ `SpectrumUtil` shortcuts) |
| heuristic-consensus calibration + `SpectrallineUtil.polyfit` + CFL master data | `VerdictOp` (hue → band); `EvaluationResult` GUI rendering |
| `QTabWidget`, `PageWidget`, nav registration | LED-SPD digitiser (measured JPG → nm/intensity) |

Logic modules/ops stay plain `SpectraContainer → SpectraContainer` so the pumpkin plugin reuses them.

## 10. Placement & registration

**Master-only** top-level **"Playground"** view; launch button gated on
`CurrentUserSession().hasRole(MASTER_USER)`; register in `MainViewModule` + `NavigationHandlerLogicModule`
(mirror the User-admin gate/registration).

## 11. Later extensions (out of first cut)

- **Interactive LED picker** in the Reference tab (toggle Avonec LEDs, live SPD) — empirical LED-set choice.
- **LED-swap stability check** — perturb the LED set, watch the verdict barely move (concept §4) → proof
  of LED-independence.
- **Virtual-device 3-image slots (#5) + image-path round-trip** — grow `VirtualSpectrometerSettings` to
  calibration/REF/SAMPLE images; rasterise SPD → ROI strip via the polynomial → existing
  `ImageSpectrumAcquisitionLogicModule`. Replaces §1's spectra-only shortcut with the faithful image path.
- **Oil-model tuning UI**, real verdict thresholds.
- **FUTURE REQUEST — LED-combination optimisation (separate task).** The LED-synthesis bench is a good
  tool to *search LED combinations* for an **even better continuous (gap-free, flat) reference light
  source** — try other Avonec LED sets/weights and score the resulting `R(λ)` for flatness/coverage.
  This is a **distinct future requirement**; the **current default LED set is fine and must NOT be
  modified** for the present task.

## 12. Open / deferred

- **Auto-calibration** — the HEURISTIC consensus already works in the live app; for the playground just
  drive it on the static CFL PNG and **verify** the known lines map back to nm (§13 P1). Manual fallback
  only if the static-image path mis-fits.
- **Division-by-low-`R` guard** — floor/mask where the synthetic `R` is ~0 (e.g. <410 nm) so `T` stays sane.
- **`SpectraContainer` dup-`__init__` bug** — fix when first used.
- **luxpy** — confirmed dependency (already installed), used to synthesise the 390–410 UV-A SPD (§4).

## 13. Implementation phases

First cut only (later extensions §11 are separate). Logic before view; each phase compiles + is testable.

| # | Phase | Repo | Deliverable | Verify |
|---|-------|------|-------------|--------|
| **1** | CFL calibration | `spectracsPy` (+ existing model) | Dedicated playground profile; auto-calibrate `cfl_philips_calibration.png` (HEURISTIC consensus → CFL master-data nm → `polyfit`) → persist `SpectrometerCalibrationProfile`; expose its **px→nm polynomial** | Known CFL lines map back to their nm (overlay/print); polynomial monotonic across 400–700 |
| **2** | Transmission/Absorption ops | `spectracsPy` | `TransmissionLogicModule` + `AbsorptionLogicModule` (+ Params/Result triples) + `SpectrumUtil.transmission/absorption(reference, sample)` shortcuts; low-`R` guard | Unit test: known R,S → T=S/R, A=−log10(T); guard handles R≈0 |
| **3** | Reference synthesis | `spectracsPy` (+ refs) | `LedReferenceSynthesisOp`: digitise Avonec measured SPDs (+ **luxpy** for 390–410 UV-A) → `R(λ)` on the calib nm axis; default LED set | Unit test: R gap-free incl. violet edge, strong in 430–480/520–560/630–670; plot sane |
| **4** | Sample synthesis (3 oils) | `spectracsPy` | `OilSampleSynthesisOp`: `A_oil` model + `c·l`/browning; 3 presets tuned to the demo hues | Unit test: `colour(T)` of each preset lands within ±~5° of 80/100/45 |
| **5** | Verdict | `spectracsPy` | `VerdictOp`: hue → perfect-centred band → label | Unit test: 80→PERFECT-ROASTED, 100→UNDER-ROASTED, 45→OVER-ROASTED |
| **6** | Playground view (the 4 flat tabs) | `spectracsPy` | `PageWidget` + `QTabWidget`: Calibration image · Reference plot · 3 oil-spectra overlaid · measured-vs-target swatch pairs | Click-through: navigate, all four tabs render; swatches ≈ targets |
| **7** | Master-only registration | `spectracsPy` | Launch button (role-gated) + `MainViewModule`/nav registration | Click-through: visible as master, hidden otherwise |

> First milestone (#6's "absorption displayed end-to-end") is reached at Phase 6: a synthetic run shown
> as calibration → reference → oil spectra → colour, all from owned parameters.

## 14. Regression test & documentation PDF (IMPLEMENTED)

`tests/test_pumpkin_oil_spectrum_to_color_eval.py` → `PumpkinOilSpectrumToColorEvalTest` (unittest;
runs under pytest). **Decoupled from the view** — depends only on the logic recipe + matplotlib, so it
survives the playground changing. Two jobs:
- **Assertions (headless, no Qt widgets/server):** reference continuity + diagnostic-band strength,
  hue monotonic in roast, the 3 oils hit targets (±4°) / strictly ordered / correct verdicts, T/A +
  low-`R` guard, CFL calibration monotonic + plausible nm range. Asserts **ordering/tolerances/labels**,
  not exact numbers — robust to colour-module changes.
- **Documentation PDF (side artefact):** renders the same content the playground shows (8 pages:
  recipe, calibration image, LED setup, reference, oil spectra, absorption, camera captures, measured-
  vs-target) via matplotlib `PdfPages`, to the **non-versioned** `spectracs-references/reports/`. Camera
  strips come from the shared `logic/playground/CameraCaptureRenderUtil` (numpy) so they match the app.

Split: **recipe = code, versioned**; **PDF = rendered artefact, not versioned**. 10/10 pass.
