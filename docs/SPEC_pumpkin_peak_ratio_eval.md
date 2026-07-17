# SPEC — Pumpkin-oil peak-ratio evaluation (replace hue verdict)

Status: **P0–P4 IMPLEMENTED 2026-07-09** — render-only first sweep in the dev measurement bench
(`DevSpectralPlugin.evaluation` composes the generic ops; the bench shows a real EVALUATION phase with the
metrics). **P5** (calibration → verdict edges — needs real-oil measurements) and **P6** (wire the independent
`PumpkinOilPlugin`) are later. Awaits phone-width click-through. Supersedes the spectrum→hue verdict with an
**absorption peak-ratio** criterion. Raised 2026-07-05 ([[spectracs-pumpkin-peak-ratio-task]]); physics
grounded in Fruhwirth & Hermetter (2007) (`KB_led_and_oil_spectra.md` §2, `spectracs-references/articles/`).

> ### ⏭ NEXT PROMINENT TASK — **§1b: the settled, literature-anchored bands** (Edwin, 2026-07-16)
> **Blue = 440–460 nm** (right-hand slope of the uncapturable 430 nm Soret) · **Green Q-band = 560–580 nm**
> (literature peak ~570). **DESIGN — implement on explicit request only, and only AFTER the plugin story**
> ([`SPEC_project_structure.md`](SPEC_project_structure.md) → [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md)).
> Deltas + the traps in **§1b.1 / §1b.2**.
>
> **→ Supporting evidence + P5 prerequisites: §13 (2026-07-17).** The measurement model (`A = ε·c·l + b`),
> why the ratio cancels concentration×path but **not** an additive offset, and where dilution actually enters.
> **Verdict in one line:** the rig reproduces the literature's **band STRUCTURE** — same features, same
> wavelengths (λ_Q 572.5 vs 573.8, inside the paper's ±5–10 nm) — **not** its shape and **not** its ratios;
> and **nothing found blocks the metric** (§13.7).
> **§13 is NOTES ONLY — it changes nothing here and describes no as-is behaviour**; its numbers were computed
> with these §1b *design* bands, **not** with the shipped `BLUE_BAND=(450,490)` / `Q_SEARCH=(565,590)` (which
> were tuned on a **different lamp**). **Blocker it raises: dev measures two pots, production will use one
> (§13.4) — fix before P5.**

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

| Band | ~λ | What it is | Specificity | Measured over (**§1b**) |
|---|---|---|---|---|
| **Soret** | ~430 nm | strong blue absorption | **mixture:** pigment Soret **+ carotenoid (~445–475)** **+ Maillard roast-browning** | **440–460** — the right-hand **slope**; the 430 peak itself saturates (oil opacity at working dilution) |
| **Q-band 1** | **~570 nm** | weak green-pigment fingerprint | **clean:** intact green pigment only (no carotenoid, ~no browning) | **560–580** |
| Q-band 2 | ~630 nm | second Q-band | **LOST** with the current optics (see §2) | — |

The green transmission window (~500–560 nm) sits *between* Soret and Q-bands; roast-browning inflates the
blue while depleting the specific green pigment → **the two bands move in opposite directions with roast**,
which is exactly what makes a ratio informative.

## 1b. SETTLED BANDS — literature-anchored (Edwin, 2026-07-16) · **NEXT PROMINENT TASK**

> **Status: DESIGN — the next prominent task to implement, AFTER the plugin story**
> ([`SPEC_project_structure.md`](SPEC_project_structure.md) → [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md)).
> Implement on explicit request only.

Edwin's decision, from the literature plus what the rig can actually capture:

| # | Band | **Settled window** | Literature anchor | Why this window |
|---|---|---|---|---|
| **1** | **Blue — Soret right-hand slope** | **440–460 nm** | first prominent absorption peak at **430 nm** | **430 itself is NOT capturable** with the lamp + dilution in use — the oil is opaque there, so `T→0` and `A` is noise. The **right-hand slope** is the measurable proxy for the same peak. |
| **2** | **Green — pigment Q-band** | **560–580 nm** | green peak at **~570 nm** | centred on the literature peak; the clean green-pigment fingerprint. |

**Why these and not the current ones:** the shipped constants were chosen empirically off bench captures
(`BLUE_BAND=(450,490)`, `Q_SEARCH=(565,590)`). The windows above are anchored to the **published peak positions**
instead, and Edwin's judgement is that *"these are nice regions [that] give physical/chemical meaningful results."*
Band 1 moves down and narrows onto the slope of the real 430 nm peak; Band 2 re-centres from ~575 to the
literature's **570**.

**Recorded fact (2026-07-16):** a new full-spectrum bulb **does** deliver light across **430–650 nm** — matching
`DevSpectralPlugin.WAVELENGTH_MIN_NM/MAX_NM` exactly. **It does not make 430 nm measurable**: the limit there is
oil **opacity at the working dilution**, not illumination. This is what settles Band 1 on the slope rather than the
peak.

### 1b.1 Deltas to implement

| Constant (`DevSpectralPlugin`) | Today | Becomes | Note |
|---|---|---|---|
| `BLUE_BAND` | `(450.0, 490.0)` | **`(440.0, 460.0)`** | `A_blue` — the Soret right-hand slope |
| `Q_SEARCH` | `(565.0, 590.0)` | **`(560.0, 580.0)`** | `λ_Q` local-max search; default λ_Q `575.0` → **`570.0`** |

**Not changed by this decision — flagged so the implementer does not silently move them:**
- `BLUE_PEAK = (450,465)` is a **different thing**: it searches the **REFERENCE** spectrum for the blue peak as a
  *saturation gate* (§3.2), not an absorption feature. Edwin's 440–460 is about **absorption**. Leave `BLUE_PEAK`
  unless separately decided.
- `GREEN_BAND = (510,540)` is the **green-window anchor** (the transmission window / clarity floor, §3.3) — *not*
  the "green peak". Edwin's "green" here means the **Q-band**. Unchanged.
- `Q_BASELINE = (555,600)` — the Q-band baseline anchors. **Watch the clearance:** with `Q_SEARCH` starting at
  **560**, the lower baseline anchor at **555** is only 5 nm away (was 10). Verify the baseline still sits *outside*
  the peak's shoulder, or move it (e.g. 550) — see §11.

### 1b.2 Consequences to check when implementing

- **`browning = A_blue / A_green`** and **`gBlue = D_Q / A_blue`** both change meaning slightly, because `A_blue`
  now samples a narrower, bluer window. Any threshold intuition from the old window does not carry over —
  which is moot today (P5 has not run, so **no thresholds ship yet**), but must not be forgotten.
- **Re-check the ROI clamp:** `WAVELENGTH_MIN_NM = 430.0` already covers 440. No clamp change needed.
- **§9's claim that "all pumpkin eval bands sit inside 450–620"**
  ([`SPEC_capture_quality.md`](SPEC_capture_quality.md) §9) **becomes false** — `BLUE_BAND` would start at **440**,
  below 450. That spec's ROI-clamp reasoning must be re-checked against the new window.

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
| PB | ** NEXT PROMINENT TASK ** (§1b)  | TOUCH DevSpectralPlugin only:  | Bench EVALUATION still renders;   | LOW     |
|    | Literature-anchored bands:       | BLUE_BAND (450,490)->(440,460);| band shading on A(lambda) moves to|         |
|    | blue = 440-460 (Soret RIGHT-HAND | Q_SEARCH (565,590)->(560,580); | the new windows; D_Q still found  |         |
|    | SLOPE; 430 peak saturates at the | lambda_Q default 575->570.     | on capture001. CHECK: Q_BASELINE  |         |
|    | working dilution), green Q-band  | Do NOT touch BLUE_PEAK (that   | lower anchor 555 is now only 5nm  |         |
|    | = 560-580 (lit. peak ~570).      | gates the REFERENCE) nor       | from Q_SEARCH's 560 -> may need   |         |
|    | AFTER the plugin story. Edwin,   | GREEN_BAND (that is the 510-540| moving to ~550 (§11). Also fix    |         |
|    | 2026-07-16. Deltas in §1b.1.     | anchor, not "the green peak"). | capture-quality §9's "all bands   |         |
|    |                                  |                                | inside 450-620" -> now false.     |         |
| P5 | LATER: save metrics + test oils  | NEW feature persistence/export;| Metrics saved per oil; quant->qual| MED     |
|    | -> quant->qual bounds -> real    | PeakRatioVerdictLogicModule    | bounds derived; real verdict edges|         |
|    | verdict edges (§8 calibration)   | (calibrated edges)             | set. (Edwin's later step.)        |         |
|    | ** PB MUST LAND FIRST ** — no    |                                | (calibrating the old windows then |         |
|    | point calibrating windows that   |                                | moving them wastes the oil runs)  |         |
|    | are about to move.               |                                |                                   |         |
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

- **`Q_BASELINE`'s lower anchor vs the new `Q_SEARCH` (raised by §1b, 2026-07-16).** `D_Q` is a depth *below a
  baseline* interpolated between **555** and **600**. With `Q_SEARCH` moving to **560–580**, the lower anchor sits
  only **5 nm** from the search window's edge (was 10). If 555 lands on the Q-band's own shoulder, the baseline is
  pulled *down*, `D_Q` is *under*-reported, and every ratio built on it shifts — silently. **Decide at PB:** keep
  555, or move to ~550. Check against a real A(λ) rather than by eye.
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

## 13. Measurement model, dilution & sample presentation (2026-07-17) — **NOTES, not as-is**

> ### ⚠ STATUS — DESIGN NOTES. Nothing here is implemented. Nothing here describes the as-is.
> **Source:** the literature-vs-spectracs comparison in
> **`spectracs-references/comparisons/fig3A_vs_spectracs/`** (note + 3 plots + digitised CSVs + a script that
> regenerates all of it). Derived from **one** measurement (`spectracsPumkinOil20260716A`) against a
> **digitised print figure** — see §13.7 for how little the latter can carry.
>
> **⚠ BAND CAVEAT — read before any number below.** Everything in §13 was computed with the **§1b SETTLED
> (design) bands**: `BLUE_BAND=(440,460)`, `Q_SEARCH=(560,580)`. The **shipped plugin still uses the as-is
> constants** — `BLUE_BAND=(450,490)`, `Q_SEARCH=(565,590)` — chosen empirically off bench captures **with a
> different lamp** (§1b). Therefore:
> - these numbers **do not describe the as-is code or the as-is lamp**;
> - **§1b, §1b.1 and §3 are unchanged by this section** — the as-is delta table stays exactly as it is;
> - §13 is **evidence for the §1b decision + a P5 prerequisite list**, nothing more.
>
> **Sample (this run):** pumpkin oil dissolved in **isopropanol**, measured against an **isopropanol
> reference** — i.e. a *dilute alcoholic solution*, the same regime as Fig. 3A's methanol solution. **Not**
> the neat-oil regime of `capture001`.

### 13.1 The measurement model — where every term comes from

`A = −log₁₀(T)`, and **log turns multiplication into addition**. The detector cannot distinguish "absorbed"
from "never arrived", so *every* loss multiplies `T` and therefore *adds* to `A`:

```
T_meas = T_absorb · T_scatter · k
A_meas = −log₁₀(T_absorb) − log₁₀(T_scatter) − log₁₀(k)  =  ε(λ)·c·l  +  b

  ε(λ) chemistry — the pigment's fingerprint SHAPE, fixed
  c    concentration      <- dilution changes ONLY this
  l    path length
  b    EVERY non-pigment dimming, lumped:  b = −log₁₀(k)
       scattering (turbidity) · lamp drift between R and S · different/reseated cuvette ·
       fill level · exposure or gain changed between R and S
```

**`b` is not a fudge term** — it is the log of any flat light loss, and the pipeline cannot tell it from
absorption.

### 13.2 Why a ratio works — and exactly where dilution enters

Each band read is `(c·l) × (a pure chemistry number)`:

```
A_blue  = c·l · ε_blue          A_green = c·l · ε_green
D_Q     = A(λ_Q) − base(λ_Q) = c·l · Δε_Q      <- a DIFFERENCE of two points on the SAME curve

ideal (b=0):   G = D_Q/A_green = (c·l·Δε_Q)/(c·l·ε_green) = Δε_Q/ε_green    <- no c, no l. EXACT.
real  (b>0):   D_Q     = c·l·Δε_Q                <- b CANCELS   (a difference)
               A_green = c·l·ε_green + b         <- b SURVIVES  (a raw mean)
               G       = (c·l·Δε_Q) / (c·l·ε_green + b)
```

**The whole thing in one line: a ratio cancels MULTIPLICATION, not ADDITION.** `c·l` multiplies → cancels
exactly (§0.3's claim holds). `b` adds → never cancels.

**So dilution enters ONLY through `b`.** With `b = 0`, `G` is identical at any dilution. With `b > 0`,
diluting shrinks the numerator proportionally while `b` stays put → **`G` drifts**. That asymmetry — `D_Q`
baseline-corrected, `A_blue`/`A_green` raw means — is the single most important property of the current
feature set (§13.6/F5).

### 13.3 What this means in practice

- **Sloppy dilution is fine; cloudy dilution is not.** `G` cancels *how much oil* — so the amount need not be
  weighed or pipetted precisely. It cancels *nothing* additive. **Effort belongs on dissolving, not on
  measuring.** (Edwin's ~2 drops in 3 ml isopropanol ≈ 3% v/v, stirred ~20 s, **visibly clear** — fine as-is.)
- **A drift-free lamp is NOT required.** What is required: **`R` and `S` captured close together with nothing
  changed in between.** A slowly drifting lamp is harmless if the reference is re-taken per sample.
- **Turbidity was excluded for this run** (both directions): fine droplets → Rayleigh `∝λ⁻⁴`, steeply blue —
  fits *worse* than flat (rms 0.028 vs 0.024), and a joint flat+Rayleigh fit drives the Rayleigh coefficient
  **negative** (unphysical); big droplets → flat, but would look **milky**, and the solution is clear.
- **`D_Q` and `λ_Q` are the robust features.** `D_Q` is immune to a flat `b` by construction. The
  vulnerability is **only** the denominator.

### 13.4 ⭐ Dev rig ≠ production rig — a P5 blocker

**Dev measures two pots** (pot A: 3 ml alcohol = REFERENCE; pot B: 3 ml alcohol + 2 drops oil = SAMPLE).
**The end user will use one pot** (Edwin, 2026-07-17). `A = −log₁₀(S/R)` then also divides **two different
pieces of glass**:

```
dev  (two pots):  A = ε·c·l + b_glass     b_glass = −log₁₀(throughput_potB / throughput_potA)
prod (one pot):   A = ε·c·l               same glass in both captures  ->  b_glass = 0
```

**Consequence: any threshold calibrated in P5 on the two-pot rig carries `b_glass` baked in and will not
transfer to a one-pot end user** — and it lands on `A_green`, the `G_green` denominator, the smallest number
in the chain. **§0.6/§0.7 already demand the bench be "a faithful rehearsal of the real thing"; two-pots-in-dev
vs one-pot-in-production breaks that rehearsal at exactly the step whose purpose is transferable numbers.**
This sharpens §12/R2 ("sample-presentation — DECIDED: fixed concentration + volume; **pin the exact
cell/geometry**"): the *cell* matters as much as the volume, and **dev's cell must be production's cell**.

→ **Recommendation: switch dev to ONE pot before P5.** 3 ml alcohol → capture `R` → add the drops, stir, put
it back → capture `S`. Identical glass ⇒ `b_glass` gone. Zero cost; removes the error rather than correcting
it; makes dev physics-identical to production. If two pots must stay, **measure `b_glass` (§13.5 test P) and
subtract it — and record that production must NOT apply that correction.**

*Caveat, honestly:* the pots are **cosmetic pots, identical by production**. That is *not* optically matched
(cosmetic tolerance ≠ optical tolerance; wall thickness varies with mould flow/gate, and even the same pot
**rotated** differently transmits differently) — but the fitted `b = 0.053` (⇒ 11.4% throughput difference) is
**a lot** for two same-mould parts. Since that 0.053 is inferred *only* from the literature (unreliable
precisely in the green window where it was measured, §13.7), **`b` may be far smaller, or zero.** Not
established. §13.5 settles it.

### 13.5 The blank-vs-blank test — measuring `b` with no oil and no literature

Each test is the real workflow **with the oil left out**; the first that yields a flat non-zero line is the
culprit. **Test P is the one that matches Edwin's current setup — run it first.**

| test | `R` and `S` are… | isolates |
|---|---|---|
| **P** | **both pots, alcohol-only** — pot A as `R`, pot B as `S` | **⭐ pot-to-pot glass difference** |
| 0 | one pot, captured twice, nothing touched | lamp drift + **noise floor** |
| 1 | one pot, wait ~2 min (real prep time) between | drift on the workflow's timescale |
| 2 | one pot, lifted out and put straight back | repositioning (seat/angle → reflection) |
| 3 | one pot, alcohol tipped out and refilled fresh | fill level / meniscus |
| 4 | one pot, stirred 20 s as for a real sample | bubbles |

Nothing absorbs in any of these ⇒ **`A` must be 0.000 at every λ.** Any flat line **is `b`, measured
directly.** *Prediction if §13.4 holds: test P shows ~+0.05, flat — and swapping the pots' roles flips its
sign.* **Test 0 also yields the noise floor** — compare it against `D_Q ≈ 0.077`: that ratio is the metric's
real SNR and is worth knowing **before** any threshold work.

**Secondary test — the dilution series** (settles whether `b` scales with the oil): plot `A_green` vs
concentration; `A_green(c) = (l·ε_green)·c + b` is a straight line whose **intercept at zero oil is `b`**.
Intercept 0 ⇒ `G` is dilution-proof. If `b ∝ c·l` (haze proportional to oil), `G` is still *stable*, merely
biased by a constant that P5 thresholds absorb; if `b` is independent of the oil, `G` moves for non-quality
reasons.

### 13.6 Findings that touch this spec (recorded; **none applied**)

| # | finding | target |
|---|---|---|
| **F1** | **Dev two pots vs production one pot** → P5 thresholds won't transfer. **The load-bearing one.** | §13.4, sharpens §12/R2, §8/P5 |
| **F2** | **§3.2 is stale:** it specifies the reference *"captured once per session and reused for every sample"*; Edwin **re-takes `R` per sample** (better — it kills session drift). §3.2's gated-blue-window argument reasons *from* the once-per-session assumption ("fixed within a comparison set"), so with a per-sample reference the gate is re-evaluated per sample and the window may drift **between** samples in a comparison set. | §3.2 |
| **F3** | **λ_Q's raw local-max search is baseline-biased.** §3.1/R5 searches the max on `A`; because the Q-band rides the falling Soret tail the raw argmax is pulled **blue-ward** — measured **569.75 nm raw vs 572.50 nm baseline-corrected (2.75 nm)**; the literature curve, flatter there, shifts only −0.25 nm. A 2.75 nm error then drags the `λ_Q ± 5` window off-peak. **→ subtract the local baseline FIRST, then search.** | §3.1, §12/R5 |
| **F4** | **`Q_BASELINE` anchor clearance — §1b.1's own open warning, now measured.** 555→550→545 moves `D_Q(lit)` 0.034→0.033→0.032 and `D_Q(spx)` 0.074→0.076→0.077: a few percent — **but in *opposite* directions for the two sources**, so it biases comparisons. **→ move the anchor to 550** as §1b.1 suggests, and pin it before threshold work. | §1b.1, §3.1 |
| **F5** | **Asymmetric baseline robustness (design gap).** `D_Q` is baseline-corrected ⇒ a flat `b` cancels. `A_blue`/`A_green` are **raw means** ⇒ `b` survives. So `G = D_Q/A_denom` divides an offset-**immune** numerator by an offset-**sensitive** denominator — and `A_green ≈ 0.035` (clear solution) is the **smallest number in the pipeline**, so a `b` of +0.05 is **larger than the quantity itself**. §3.4's near-zero-denominator floor guards **divide-by-zero, not offset bias** — a floored `A_green` is still wrong, merely finite. **→ baseline-correct the denominator too, or measure `b` (§13.5) and subtract it, before `G` carries any threshold.** | §3.4, §3.3 |
| **F6** | **§1b's `BLUE_BAND=(440,460)` conflicts with §3.2's own guardrail** `W_blue=[450,490]` ("below ~450 = **saturated Soret**") — §1b settles the band 10 nm *into* the region §3.2 excludes. §1b.1 flags the knock-on to `SPEC_capture_quality.md` §9's "450–620" claim but **not this direct conflict**. In *this* run A(440)=0.66 — nowhere near saturated (generous isopropanol dilution); but `capture001` had **A≈2.5 at 445** (neat). **Whether 440–460 is safe depends on dilution** ⇒ the §3.2 saturation gate (`A ≤ 1.5`) becomes **load-bearing, not a formality**. **→ keep the gate active and LOG how many nm it trims**; if it routinely eats 440–450, the settled band is fiction at that dilution. | §1b, §3.2 |
| **F7** | **§2 CONFIRMED by measurement** — the ~630 nm Q-band is absent from the spectracs trace (flat/noisy ~0.03 where the literature shows a clear peak), exactly as §2 predicts from the S-mount red-end roll-off. **No change needed**; §1b's new full-spectrum bulb does **not** rescue it — the constraint is the **lens, not the lamp**. Evidence only. | §2 |

### 13.7 What the literature can — and cannot — validate

**Fig. 3A is a redrawn, print-smoothed illustration. It is a QUALITATIVE anchor only** (Edwin, 2026-07-17).

- **It gives:** three bands exist — Soret ~430, Q-band ~575, Q-band ~630. **That is all.**
- **It cannot give:** ratios or amplitudes; fine structure (the spectracs shoulders at ~582/593 nm are
  **not decidable** from it — print smoothing would erase exactly that; decide on the rig instead: does the
  pattern repeat across captures and oils, and is it above the §13.5 test-0 noise floor?); exact positions
  (the digest quotes **±5–10 nm**, and the 425/437 doublet may itself be stylised).
- **What was validated:** `λ_Q` **572.50 nm** (spectracs) vs **573.75 nm** (literature). Read this as *"the
  rig resolves a Q-band inside the literature's own ±5–10 nm tolerance"* — **not** as ~1 nm accuracy; the
  ~1 nm is precision between two *digitisations*. **This is the only thing the literature can validate, and
  it is sufficient.**
- **Peak WIDTH — nor is resolution comparable.** Baseline-subtracted FWHM: **literature 23.5 nm vs spectracs
  16.8 nm** — our band is *narrower*, but that reflects the **figure being smoothed** (print smoothing + a
  3–4 nm-thick printed line digitised at 1.4 nm/px, vs 0.13 nm/px for the spectracs PNG), **not** the rig
  out-resolving the authors' instrument. All that can be claimed: our band is **no broader than what the
  figure can show**. *(Aside: the paper's Q-band looks "sharper" mainly for an aspect-ratio reason — a ~40 nm
  bump spans 10% of Fig. 3A's 400 nm axis but 24% of our 170 nm one, i.e. 2.4× wider on the page at equal
  height. Same data.)*
- **What was NOT validated — the ratios.** `G_blue` 0.063 (lit) vs 0.220 (spx) = **3.5× apart**; `G_green`
  0.977 vs 0.885 = within 12%. **Neither is evidence.** The `G_green` agreement is contingent on the
  suspected `b` being *left in* (remove 0.056 → `A_green`→0.030, `D_Q` unchanged → `G_green`→2.43, a 2.5×
  disagreement); and the literature's `A_green` is digitised from the region where the paper's four printed
  curves **merge into one line** (±0.01 ≈ **±29%** on the denominator). Moreover **`A_blue` is *designed* to
  vary between oils** — §1's own table calls it a *mixture* (pigment Soret + carotenoid 445–475 + Maillard
  browning) — so `G_blue`'s gap **is not evidence of an instrument fault**; it may be the browning axis
  working. **`G_blue` is meaningful only within one rig across comparable samples, never rig-vs-literature.**

- **⚠ "Same peaks within the working window" — TRUE at 610, FALSE at 640. The edge decides it.**
  - **440–610 nm:** holds. Both show a **Soret flank** and the **~573 nm Q-band**, at the same wavelengths.
  - **440–640 nm (the stated working range, §1b):** **fails** — the literature's **third peak sits at 630 nm,
    *inside* that window**, and this rig does not show it (§13.6/F7: documented S-mount red roll-off, §2).
    Explainable, but it is still a peak in the window that is not in both — and it is **visible in the
    reproduced inset**, so any "same peaks in the working range" phrasing is contradicted by our own figure.
  - **Footnote either way:** within 440–610 spectracs shows a **~468 nm bump** and **~582/593 nm shoulders**
    that the paper's curve does not (§13.6 / open questions). Origin unresolved. So it is *"the same
    features, plus extra ones in ours"* — not *"identical"*.
  - **Safe summary line:** *"Within 440–610 nm the rig shows the same characteristics and the same peak as
    the literature: a Soret flank and the protochlorophyll/protopheophytin Q-band at 572.5 nm vs the
    literature's 573.8 nm, inside the paper's own ±5–10 nm tolerance. The literature's third peak at 630 nm
    is outside this rig's optical reach (known lens limitation); absolute heights are not comparable."*
- **⚠ NOR was "the same shape" validated — a tempting overclaim, so pin it.** *Same shape ⟺ constant ratio*:
  if two curves differ only by concentration × path, `A_spx/A_lit` is **one number at every λ**. Measured, it
  runs **0.59 (450) · 1.68 (500) · 2.64 (520) · 2.08 (573) · 0.96 (610)** — a **4.5× swing**. Not constant ⇒
  **not the same shape** — which is exactly why no `k·A_lit` fit works (rms 0.056), nor `k·A_lit + b`
  (rms 0.032 on a 0.05–0.66 signal). **What IS validated is the same band STRUCTURE** — a Soret flank, a
  green window, a Q-band at ~573 nm: **the same features at the same wavelengths**. Shape is what the ratios
  are *made of*, so "same shape" and "ratios disagree" cannot both hold. **And it would not even be a
  statement about the device:** different oil, different solvent, unknown dilution — a shape difference
  between these two curves is compatible with two flawless instruments.

**Conclusion: band POSITION validates; band RATIO does not.** The literature **cannot** calibrate this metric.
Thresholds must come from **real oils on the rig (§8, P5)** — exactly as this spec already plans. §13
**confirms that plan rather than shortcutting it**, and adds one prerequisite: **settle `b` first (§13.5),
else every `G` is denominator-biased.**

### 13.8 Verdict — what 2026-07-17 establishes (Edwin's summary, wording pinned)

1. **What was learned today is essential** — it is the measurement model behind every `G` this spec ships.
2. **Within 440–610 nm, spectracs shows essentially the same characteristics and peaks as the literature
   device:** a **Soret flank** and the **Q-band at 572.5 nm** vs the literature's **573.8 nm** — inside the
   paper's own **±5–10 nm** tolerance.
   *Window matters (§13.7): true at 610, **false at 640** — the literature's third peak sits at 630 nm,
   inside the stated 440–640 working range, and this rig cannot reach it (§2, §13.6/F7). "Essentially" also
   carries the ~468 nm bump and ~582/593 nm shoulders that spectracs shows and the paper's curve does not.*
3. **Both traces carry the same green-tetrapyrrole pigment fingerprint** (Soret flank + ~573 nm Q-band),
   confirming **the rig sees the pigment the literature describes**.
   > **⚠ The inference does not run backwards — do not upgrade this to identification.** A VIS spectrum
   > **cannot authenticate** the oil as pumpkin: green tetrapyrroles are not unique to *Cucurbita* (olive,
   > hemp and other green oils carry chlorophyll/pheophytin), so the signature says *"a green tetrapyrrole
   > is present"*, **not** *"this is pumpkin seed oil"*. This is the project's own standing scope caveat —
   > `Fruhwirth_Hermetter_2007_SUMMARY.pdf` ("colour alone **cannot authenticate** the oil … keep the
   > quality verdict and any purity claim separate") and
   > `spectracs-references/articles/Balbino_2022_…md` ("CIELAB colour alone can't authenticate PSO — only
   > NIR can"). Also §9 (Caveats / non-goals). **Quality verdict ≠ purity claim.**
4. **Chances are intact for a reliable, stable peak ratio as the metric.** Nothing found today blocks it:
   the ratio cancels conc×path **exactly** (§13.2), `D_Q` and `λ_Q` are robust, and the one open risk — an
   additive `b` — is **measurable without oil** (§13.5) and **removable for free** by using one pot (§13.4).
   *Not proven; not blocked.* Thresholds still require **P5 on real oils** (§8).

#### What it boils down to — **not a toy; a candidate field tool for the mill**

**Earned today.** A DIY grating spectrometer resolved a **weak vibronic band** — the hardest feature in this
oil's visible spectrum, ~14× smaller than the Soret beside it — at **572.5 nm**, 1.3 nm from the published
position, at a clean **16.8 nm FWHM**. That is instrument-grade behaviour, not toy behaviour.

**Why the *field* case is specifically strong.** The metric cancels exactly what a mill cannot control:
`G = D_Q/A_denom` divides out concentration × path (§13.2), so **nobody has to pipette**. Two drops in 3 ml,
20 s of stirring, one pot (§13.3/§13.4) is a **mill-floor protocol, not a lab protocol**. This is the §0.3
design decision paying off — and it is what makes "in the field" credible rather than aspirational.

**The honest boundary.** Today establishes that **the physics and the instrument are not the obstacle**. It
does **not** establish "deployable". Remaining, in order — **none of them physics**:

| # | gap | why it matters | cost |
|---|---|---|---|
| 1 | **No thresholds** (§8, P5) | it can **measure** but not **judge** — the difference between an instrument and a tool | the P5 dataset |
| 2 | **n = 1** — one oil, one capture. **Repeatability is the real field-readiness question and has not been run:** measure one oil ~5×, does `λ_Q` / `D_Q` / `G` repeat? | a field tool must give **the same answer twice** | an afternoon |
| 3 | **SNR unknown** — `D_Q ≈ 0.077` vs an unmeasured noise floor | decides whether `D_Q` differences are real | free — §13.5 test 0 |
| 4 | **`b` / one-pot** (§13.4, §13.5) | else every `G` is denominator-biased, and dev ≠ production | free / 5 min |

**Verdict to quote:** *"Not a toy — an instrument that resolves the right band, with a metric that tolerates
mill-grade sample prep. Field-readiness is now a calibration and repeatability question, not a physics
question."*

> **Knock-on for the cross-references below:** `KB_led_and_oil_spectra.md` §2 and
> `Fruhwirth_Hermetter_2007_SUMMARY.pdf` both say the bench **"reproduces Fig. 3A"**. Per §13.7 that
> overstates what a smoothed print figure can support — it reproduces the **band positions**, within
> ±5–10 nm. Wording to be softened when those docs are next touched (**not done here**).

## 14. Cross-references

- `spectracs-references/comparisons/fig3A_vs_spectracs/` — **the source of §13**: literature-vs-spectracs
  note, overview + 440–610 nm + peak-ratio plots, digitised CSVs, and the script that regenerates them.
- `KB_led_and_oil_spectra.md` §2 — the two-band physics + "our bench reproduces Fig. 3A" (see §13.7 caveat).
- `spectracs-references/articles/Fruhwirth_Hermetter_2007_SUMMARY.pdf` — the three peaks / ~575 Q-band digest.
- `SPEC_pumpkin_integration.md` — the plugin/engine architecture this modifies (Track C, `PumpkinOilPlugin`).
- `SPEC_measurement_evaluation_concept.md` — the green→brown roast-verdict concept.
- [[spectracs-pumpkin-peak-ratio-task]] — origin; `spectracs-docs/ROADMAP.md` deferred thread.
