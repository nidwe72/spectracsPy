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

## UC2 · Dilution-invariance  ·  _status: PENDING_

One oil, 2 drops vs 3 drops in 3 ml isopropanol. Expectation: metrics barely move across dilution. _TODO._

---

## UC3 · Discrimination  ·  _status: PENDING_

Three oils (too-green / typical / brown), fixed dilution. Expectation: three separated metric clusters. _TODO._
