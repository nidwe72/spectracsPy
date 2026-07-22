# Lab diary — Capability Proof (milestone V)

A dated running log of **what was actually run and what was seen** — the go/no-go evidence trail for the
Capability Proof milestone. The *protocol* (how to run) lives in `SPEC_capability_proof.md` §7; this file is the
*record* (what happened). One entry per run. Append-only; correct with a follow-up note, don't rewrite history.

Use cases (SPEC §7.2, named by what they prove): **UC0 · Correction sanity** → **UC1 · Repeatability** →
**UC2 · Dilution-invariance** → **UC3 · Discrimination**.

Rig reminders (SPEC §10.2): lamp = **Yuji SunWave 6500 K** — a phosphor-converted white LED (blue pump chip
~455–475 nm + broad phosphor); lock exposure / gain / white-balance @ 6500 K; DEV bench + DevSpectralPlugin only
(wizard untouched until the gate passes). Capture ROI is now **440–630 nm** (§7.0.2). **Sharp `A(λ)` spikes,
raster-verified:** ~473 nm = the real blue-pump line (inside BLUE_BAND → mildly biases A_blue); ~607 nm = a
registration artifact on the steep red slope (no raster line; outside all eval bands). Not oil signal either way.

Processing ladder (as built, SPEC §8.2): `raw → de-spike(median k7) → despiked → flat-offset(red-end mean) →
despiked+baseline` (NO SG — near-no-op for chromaticity). **Metrics show raw + `· despiked`** (flat-offset is colour-only — it
hurt the band means on oilH); **colour is a 10-variant set** (intrinsic & intrinsic-perceived each: natural,
hue-norm, · despiked, · despiked+baseline; perceived: natural + hue-norm). The PROCESSING "Absorption" tab overlays
raw / despiked / despiked+baseline.

---

## UC0 · Correction sanity  ·  _2026-07-20_  ·  _status: ✅ DEMONSTRATED_

**Goal.** Stand the pipeline up end-to-end and show the flat-offset + light-SG correction moves values sensibly:
colour chips with raw + `· improved` twins, and an `Absorption (improved)` overlay (raw vs corrected).

**Seen (oilG exports, `spectracs-references/tmp/measurement_report_oilG_00{1,2}.pdf`).** The improved absorbance
sits ~0.02 below the raw curve and the signal-free 490–550 nm trough reads ~0 — the flat-offset anchor found the
transparent floor and removed it; light SG de-noised without flattening the Q-band bump (~573 nm). The absorbed
colour chips got a corrected twin. **Verdict:** machinery works; the correction does what it should. ✔

---

## UC1 · Repeatability  ·  _2026-07-20_  ·  _status: FIRST EVIDENCE (N=2)_

**Setup.** Oil **G**, single dilution, measured **twice** (oilG_001, oilG_002). Setup / dilution / prep: _TODO
confirm_. Lamp Yuji SunWave 6500 K, WB locked.

**Colour — run-to-run hue (the headline).**

| Chip | 001 | 002 | Δhue |
|---|---|---|---|
| Intrinsic (perceived-family) — raw | H 106° | H 101° | 5° |
| Intrinsic (perceived-family) · **improved** | H 115° | H 115° | **0°** |
| Intrinsic — raw | H 286° S100 L77 | H 281° S100 L78 | 5° |
| Intrinsic · **improved** | H 295° S100 L71 | H 295° S100 L66 | **0°** (hue) |
| Perceived | H 86° | H 87° | 1° |

**Result.** The flat-offset correction collapses the run-to-run hue spread of the intrinsic/absorbed colour from
~5° to **0°** (normalized improved chip byte-identical: H115 S80 L50). Confirms the Entry-0 hypothesis — the
additive baseline `b` differs run-to-run and drifts the raw absorbed chromaticity; removing it makes the intrinsic
colour repeatable. Perceived hue was already stable (1°). Lightness of the non-normalized improved chip still
drifts (L71 vs L66) — hue is the locked, robust axis.

**Peak-ratio metrics (these exports: RAW only — paired improved metrics were added just after).** Greenness G
1.195 vs 0.974 (~20%), Browning ratio 1.648 vs 1.743 (~6%), D_Q 0.032 vs 0.029 @ 573 nm. The larger ratio variance
is expected (raw, uncorrected). **Next export will carry paired raw / `· improved` metric rows** — re-run to see
whether the correction tightens A_blue / A_green / their ratio (D_Q should barely move; it is locally-baselined).

**Caveats.** N=2 (not the recommended ~5×). Same oil, same dilution — this is repeatability, NOT invariance (UC2).

**Follow-ups.** Re-export oilG with paired metrics; extend to N≈5; then UC2 (one oil × two dilutions).

**Reference-tilt investigation (oilJ → diagnoseCapture, 2026-07-20) — SOLVED.** The *absorbed* colour drifts ~5°
run-to-run while *perceived* holds — traced to a reference-shape tilt (red↑ vs green/blue) amplified by `−log₁₀` at
low absorbance (SPEC §10.2). `CAPTURE-SETTINGS` logging showed exposure/WB/gain **identical** across runs (rules out
AE/AWB). `diagnoseCapture.py` (real ELP, same pot untouched) then showed the tilt **resets after an idle gap** —
ruling out evaporation (irreversible, hours-scale) and the lamp (external, always on) — and a `--ae-once` warm-up
run gave a **clean single-exponential** red/green vs time: **camera sensor self-heating** (channel-balance /
responsivity drift; the dark-frame test missed it because that's dark *offset*, not gain). **τ = 2.9 min, settles to
within noise by ~9 min, 1.68% total shape change.** **FIX: warm up the camera ~10 min (stream) before measuring, and
keep R→S close in time** — then R and S share the sensor state and the tilt cancels in `S/R`. Curve:
`spectracs-references/tmp/sensor_warmup_curve.png`. Tools: `runDiagnose.sh` / `diagnoseCapture.py`
(`--runs/--interval/--ae-once/--frames`), `CaptureDiagnosticsLogger` (per-frame JSON via `SPECTRACS_LOG_SPECTRA`).

---

## UC2 · Dilution-invariance  ·  _2026-07-21_  ·  _status: ✅ CONFIRMED (clean data)_

Same oil, **matched pots** (4 ml alcohol both), warm camera. **K = 2 drops, L = 3 drops.** Absorbances scale
uniformly (`A_blue` ×2.04, `A_green` ×2.06 ⇒ `b`≈0). **Browning ratio invariant: K 3.13 ↔ L 3.10 (1%)**; intrinsic
hue 293↔289. (Contrast the contaminated pre-K G↔K = 1.7↔3.1 — mismatched alcohol.) Greenness NOT perfectly invariant
(D_Q under-scales). Full: SPEC_capability_proof §11.1. PDFs: `oilK_00{1-4}`, `oilL_00{1-4}`.

---

## UC3 · Discrimination  ·  _2026-07-21_  ·  _status: ✅ green↔brown (2 of 3 oils)_

Same recipe (4 ml + 3 drops), matched pots, warm camera. **L = green, M = brown**, 4 runs each. The oils **separate
unambiguously**: `A_blue` 0.365↔0.213 (−42%, ~20× noise), **Browning ratio 2.92↔1.98 (−32%, ~12× noise)**. Raw hue
289↔281 (8°); baseline hue only 5° (clamp halves colour discrimination → use raw not baseline). Greenness INVERTED
(useless), D_Q weak. **Direction inverted vs the name:** greener = MORE blue absorption (more green pigment) = higher
Browning ratio → it's a *freshness/pigment* index, not "browning". Physically: brown oil = degraded green pigment
(NOT Maillard), reddish in bulk via dichromatism. Full: SPEC_capability_proof §11.2–11.5. PDFs: `oilL_00{1-4}`,
`oilM_00{1-4}`. **Brown dilution-invariance (N-series, brown at 2 drops, 2026-07-21):** Browning ratio M(3drops)
1.98 ↔ N(2drops) 1.82 (~8%, weaker than green's 1% — residual scatter `b`, degraded oil is more turbid); but brown
(~1.8–2.0) stays a distinct cluster far below green (~2.9), so discrimination is **dilution-robust**. PDFs
`oilN_00{1,2}`. **Remaining:** only the 3rd "too-green" oil. **Verdict so far: GO.**

**PB-band re-analysis (2026-07-22) — the new Pigment ratio (Soret/Q) is the best discriminator yet.** Re-computed
the V3 metric (440–460 Soret / 560–580 Q, despiked band means) from the spectral data embedded in all 16 K/L/M/N
PDFs (green = K,L · brown = M,N; K/N = 2 drops, L/M = 3 drops). **Pigment ratio (Soret/Q): green 3.83 ± 0.13 vs
brown 2.41 ± 0.08 — Δ/noise ≈ 13.5**, clusters fully non-overlapping (worst green 3.67 > best brown 2.59, gap 1.08).
Beats the legacy Browning ratio (Δ/noise 10.7) and the Soret/clarity safety net (7.2). **Dilution-invariant:** green
K(2d) 3.89 ↔ L(3d) 3.76 (3.3%); brown N(2d) 2.35 ↔ M(3d) 2.48 (5.4%). Physics: Soret & Q both scale with pigment
conc → ratio cancels dilution, isolates the Soret-to-Q *shape*, which shifts with pigment degradation; Q is nearly
equal between groups (0.21 vs 0.20) so the split is real Soret signal. **Rubber-duck reversal:** the weak-Q-denominator
worry did NOT bite here — over a 20-nm despiked mean Soret/Q is the *tightest* metric. Still 2 oils (3rd pending).
Full table: SPEC_capability_proof §11.2a.

**Colour: same hue, different chroma (2026-07-22).** After switching colorIntrinsicPerceived to the white-point
complement (option (b), §8.4), green and brown gave the *same* perceived hue (~67°) — puzzling until measured as
angle+distance from white: all 16 runs sit at the **same absorbed hue-angle (245.5°)**, differing only in **chroma**
(green 0.234 vs brown 0.198, Δ/noise ≈ 6.5, dilution-invariant). The complement reflects through white → preserves
direction → same hue; the hue-normalized chips fix S/L and discard the chroma → identical chips. The earlier "~12°
absorbed hue" split (§11.2a) was a gamut-clamp artifact (blue-violet far out of sRGB folds to different HSL hues);
the real colour separator is **chroma**, and the Pigment ratio is its numeric face. Physics: same pigment family →
same band positions → same hue; browning cuts pigment *amount* → chroma toward grey, no hue shift. Detail:
SPEC_capability_proof §11.2b.
