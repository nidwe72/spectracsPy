# SPEC — Capture quality & fidelity (ROI clamp · robust reduction · dark level · normalization)

> **Looking for the big picture rather than the derivations?** Read
> [`DOC_capture_fidelity.md`](DOC_capture_fidelity.md) — the textbook-style *documentation* of this
> whole chain (why the brightness law exists, what `T = S/R` cancels, and one short chapter per
> decision), written for the developer, the chemist and the lab alike. It is generated to
> `spectracs-docs/internal/Spectracs_CaptureFidelity.pdf` via
> `docs/tools/build_capture_fidelity_pdf.py`. **This spec remains the source of truth** for the
> numbers and the decision history; the document summarises and points back here.

Status: **MIXED (2026-07-15)** — the M0 probe surfaced a production-breaking resolution mismatch that outranked the
original topics, and the work that followed is **IMPLEMENTED + RIG-VERIFIED + committed+pushed**:
- **§4.9 M0.5** — capture pinned to 2592×1944 + ROI⊆frame tripwire.
- **§13 / §14.1–14.3** — colour-constrained calibration line detection (green no longer mislabelled as Eu red at
  high resolution) + advanced/consensus anchor fix + resolution-aware calibration exposure.
- **§14.5–14.7** — shared **synchronous in-thread auto-exposure** with a per-channel (no-saturation) metric and a
  fixed settle; the dev bench, measurement `CapturePanel`, AND calibration all use it (fixed-exposure paths retired).
  §14.7 lists the tuned timing constants and known fragilities.
- **§9 (M1)** — plugin-driven wavelength ROI clamp (window **450–630 nm**, plugin-declared, host hard-clamps).
- **§6 (M2)** — robust reduction: spatial Tukey-biweight over an inset band + temporal sigma-clipped mean.

Still **DESIGN-only / not needed**: Topic 3 (normalization) = documented no-op (§7); **M3** (Topic 4, dark-frame
subtraction §5) = **not needed** — the dark was measured near-zero, and the M2 spatial Tukey already discards the
rare hot pixel (so no bad-pixel map either); **§17 gamma linearization** = **DE-RISKED DESIGN, ready to build**
(2026-07-26) — every open question in it was answered by measurement (§17.5), the decode is settled (pure `x^2.2`,
per channel, first in the reduction; the piecewise sRGB EOTF measured 24 % *worse* and was declined), and it is
**verdict-neutral by construction**, so it moves no threshold. Motive = closure + colour accuracy; implement on
explicit request. **§18** records the derived documentation artifact.

Source: Edwin. Investigated with two code-map sweeps + web research (astronomy CCD reduction) + rubber-duck
adversarial passes, then measured-then-built on the rig throughout. Governs the capture→spectrum path shared by both
hosts (`WizardViewModule`, `DevMeasurementBenchViewModule`) via `CapturePanel`. Relates to
[`SPEC_dev_capture_view.md`](SPEC_dev_capture_view.md), [`SPEC_dev_measure_bench.md`](SPEC_dev_measure_bench.md),
[`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md), [`SPEC_real_camera_capture.md`](SPEC_real_camera_capture.md).

## 0. The rule that governs all

**Every fidelity claim is verified on the real rig before code is written.** These topics decide whether a
sample/reference the operator trusts is actually faithful. We measure first (M0 probe), then build only what the
numbers justify. No blind implementation.

## 1. Problem — three operator-raised questions + one the review surfaced

1. **ROI is not plugin-driven (Topic 1).** The current lamp gives usable signal only ~**450–620 nm**, but capture
   uses a hardcoded **400–700 nm** window (`CapturePanel.__NM_MIN/__NM_MAX` :50-51, duplicated in
   `DevMeasurementBenchViewModule.py:55-56` and as the `ExtendedRoiLogicModule.extendedXBounds` defaults). The plugin
   API (`CaptureView`/`MeasurementStep`/`SpectralWorkflowStep`) has **no** wavelength field, so the lamp constraint
   has nowhere to live.
2. **Too many outliers in captured values (Topic 2).** Confirmed root causes: capture samples only the ROI **centre
   row** (`ImageSpectrumAcquisitionLogicModule.py:67,77` — one `qGray` pixel per column), throwing away the whole band
   height; and the 150 frames are combined with a **plain mean** (`MeanSpectrumLogicModule.py:14`, `.mean(axis=0)`) —
   no outlier rejection anywhere.
3. **Should the captured spectrum be normalized (Topic 3)?**
4. **[Review-surfaced] No dark-frame / black-level subtraction (Topic 4).** The single biggest fidelity gap; see §5.

## 2. What we verified before designing

- **`extendedXBounds` already narrows as well as widens** (`ExtendedRoiLogicModule.py:13-31`): it inverts the px→nm
  cubic for `nmMin/nmMax` and clamps to the raster. A plugin-supplied 450/620 flows in with **no new math** — today
  it's just fed the hardcoded 400/700.
- **`T = S/R` self-normalizes the lamp** (`TransmissionLogicModule.py:32-34`, with a 1%-of-peak reference-floor
  guard). Dividing sample by reference cancels the illuminant SPD *and* any multiplicative gain — the crux of Topic 3.
- **Exposure is already locked across Reference and Sample** (evidence chain, §6). Auto-expose is reference-only;
  the converged value is stored in `__lockedExposure` (`CapturePanel.py:480-481`) and re-pinned on the sample tab
  (`:230-242, :331-335`) on the same uninterrupted stream, with the slider disabled for the sample. **So exposure is
  NOT a fidelity gap** — the residual risk collapses onto the *additive* dark level (Topic 4).
- **All pumpkin eval bands sit inside 450–620:** `BLUE_PEAK=(450,465)`, `BLUE_BAND=(450,490)`, `GREEN_BAND=(510,540)`,
  `Q_SEARCH=(565,590)`, `Q_BASELINE=(555,600)` (`DevSpectralPlugin.py`). Max 600 < 620; the clamp won't starve them.
  > **⚠ EXPIRES with peak-ratio phase PB** ([`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md)
  > §1b, Edwin 2026-07-16): `BLUE_BAND` becomes **(440, 460)** — **440 < 450**, so this bullet's premise, and any
  > ROI-clamp reasoning resting on it, **must be re-checked** when PB lands. (The plugin's own clamp is already
  > `WAVELENGTH_MIN_NM = 430.0`, so the *clamp* is fine; it is this **450 lower bound** that goes stale.)

## 3. Milestones (ordered by fidelity impact)

**M0 (probe) → M1 (Topic 1 ROI clamp) → M2 (Topic 2 robust reduction) → M3 (Topic 4 dark, scoped by M0).**
Topic 3 = documented no-op (§7). Warmup protocol note (§8). **As-built: M1 ✅ IMPLEMENTED (§9), M2 ✅ IMPLEMENTED
(§6), M3 ✅ NOT NEEDED** (dark measured near-zero; Tukey covers hot pixels). All shipped after the §4/§13/§14
resolution+calibration+auto-exposure cascade.

---

## 4. M0 — the dark & warmup probe (measure first) — DETAILED

A **standalone read-only diagnostic** (no app changes), run on Edwin's real rig (real camera + lamp), not in the agent
sandbox — like the bench recordings. It reuses the *same* pixels the real pipeline sees (real backend + active
calibration profile) so its verdicts transfer. It gathers the evidence that decides M2 (bad-pixel map) and M3 (scalar
vs per-pixel dark) and measures the LED warmup. This is the "unit test" Edwin asked for.

### 4.1 Location & reuse
- New file **`diagnostics/capture_quality_probe.py`** (top-level, sibling of `automation/`; dev-only tooling, not app
  runtime). Human-gated prompts on the console (cover slit / lamp on), like the bench harness.
- **Reuses** `getCaptureBackend()` / `DesktopCv2CaptureBackend` (`CaptureBackend.py`) for grabs, the VID/PID→cv2-index
  resolver ([`SPEC_real_camera_capture.md`](SPEC_real_camera_capture.md)), and the **active
  `SpectrometerCalibrationProfile`** (ROI `X1/X2/Y1/Y2` + cubic `A–D`) so ROI band and px→nm match production.
- Exposure: **auto-expose on the lamp once** (reuse the bench auto-expose), then use that *same* locked exposure for
  the dark capture — mirrors the real R/S exposure lock (§6/§10).
- Outputs to **`spectracs-references/probe/<timestamp>/`**: `report.json` (all numbers + verdicts), console summary,
  and PNG plots (dark heatmap over ROI, warmup curve). No DB writes.

### 4.2 Phase A — Dark analysis  (human gate: *slit blocked / lamp off*, at operating exposure)
Capture **N=150** dark frames; build a per-pixel temporal stack over the **full frame** (hot-pixel hunt) with stats
focused on the **ROI band**.

| Metric | Definition | Reported as |
|---|---|---|
| Black level `D0` | median of per-pixel temporal mean over ROI band | DN (0–255) **and** % full-scale |
| Dark uniformity | spatial spread (std, IQR, max−min) of per-pixel dark mean across ROI | DN; "uniform" vs "structured" |
| Temporal dark noise | median per-pixel temporal std across ROI | DN |
| Hot pixels | pixels with dark-mean > `median + 6·MAD` (and/or > abs floor) | count total, **count in ROI band**, worst coords |
| Exposure dependence | `D0` at 3 exposures (¼×, 1×, 4×) | flat (offset) vs scaling (dark current) |

Dead pixels are **not** reliably found in the dark (a dead-low pixel reads 0 like everything); they're flagged in
Phase B (ROI pixels that stay ~0 while neighbours are lit).

### 4.3 Phase B — Warmup analysis  (human gate: *lamp cold-start on*)
Sample the lit reference band over time — 1 frame every **2 s for 5 min** (tunable). Per timepoint compute mean ROI-band
intensity **and** spectral centroid (color-drift proxy).

| Metric | Definition | Reported as |
|---|---|---|
| Intensity drift | ROI-band mean vs time | curve + % change cold→stable |
| Color drift | spectral centroid (nm) vs time | curve + nm shift |
| Time-to-stable | first time rolling change < **0.5 %** sustained over a 30 s window | seconds |
| Dead pixels | ROI pixels ~0 while neighbours bright | count, coords |

### 4.4 Thresholds (defaults, tunable, with rationale)
- **Black level matters** if `D0` > **1 % full-scale** (≈ 2.5 DN of 255). Below → Topic 4 negligible.
- **Uniform** (→ scalar option b) if ROI dark spatial std < **1 DN**; else **structured** (→ per-pixel option a).
- **Hot pixel:** dark-mean > `median + 6·MAD` (robust) *or* absolute > **15 DN**. **Bad-pixel map earns its place** if
  **≥1 hot/dead pixel falls inside the ROI band**.
- **Warmup stable:** rolling ROI-mean change < **0.5 %** over 30 s.

### 4.5 Decision gates the probe emits (printed as explicit verdicts)

| Finding | Verdict → milestone consequence |
|---|---|
| `D0` ≈ 0 & uniform | Topic 4 (M3) shrinks to near-nothing |
| `D0` significant, uniform | **scalar black-level (option b)** — no user step |
| `D0` structured / hot pixels in ROI | **per-pixel dark (option a) + bad-pixel map** earn their place |
| Warmup drift measurable | add a warmup gate before reference capture (§8) |
| No hot/dead pixels in ROI | **skip the bad-pixel map** (M2 spatial biweight alone suffices) |

### 4.6 Implementation steps (build order for the probe script)

```
+-----+---------------------------------------------+------------------------------------------+--------------------------+----------+
| Step| What                                        | Reuses / touches                         | Output / gate            | Risk     |
+-----+---------------------------------------------+------------------------------------------+--------------------------+----------+
| P1  | Scaffold script + console human-gate helper | new diagnostics/capture_quality_probe.py | runs, prompts, exits     | none     |
| P2  | Resolve real camera, open backend           | VID/PID resolver, getCaptureBackend()    | live frames grabbed      | rig-only |
| P3  | Load active calibration profile (ROI+cubic) | SpectrometerCalibrationProfile / session | ROI band + px->nm ready  | med (DB) |
| P4  | Auto-expose on lamp, lock exposure          | AutoExposureLogicModule.findExposure      | converged operating exp  | rig-only |
| P5  | Phase A: gate + grab 150 dark frames         | backend grab loop                        | per-pixel dark stack     | rig-only |
| P6  | Dark stats: D0, uniformity, hot, exp-dep     | numpy (median/MAD, per-pixel mean/std)   | dark metrics (4.2)       | none     |
| P7  | Phase B: gate + time-series lit capture      | backend grab loop + timer                | warmup samples           | rig-only |
| P8  | Warmup stats: drift, centroid, time-stable   | numpy + cubic for centroid               | warmup metrics + dead px | none     |
| P9  | Report writer: JSON + PNG plots + verdicts   | matplotlib, json                         | report.json + console    | none     |
| P10 | Run recipe in doc + probe README            | docs/SPEC_capture_quality.md             | one-command rig run      | none     |
+-----+---------------------------------------------+------------------------------------------+--------------------------+----------+
```
P1, P6, P8, P9 are pure/offscreen-testable in the agent sandbox; P2/P4/P5/P7 need the rig (real camera+lamp) and are
run by Edwin. P3 reads the DB profile (verify a profile is resolvable headless).

### 4.7 Status & run recipe
**BUILT 2026-07-15** — `diagnostics/capture_quality_probe.py` + `diagnostics/probe.sh`. Pure analysis
(`dark_stats`/`hot_pixels`/`warmup_stats`/`spectral_centroid`/`dead_pixels`/`_brightness`/`verdicts`) validated
offscreen via `--selftest` (green). Rig grabs (Phase A/B) reuse `getCaptureBackend()` + qGray reduction; scene
auto-resolves from the app's `SpectrometerCalibrationProfile` (ROI + cubic) with CLI overrides as the reliable
standalone path. **Auto-exposure is integrated** (Edwin 2026-07-15): the probe reuses the app's own
`AutoExposureLogicModule.findExposure` with the same brightness metric as the bench (99.9th-pct of the per-pixel max
channel, target 235) to converge the operating exposure **on the lit lamp FIRST**, then shoots the dark at that same
exposure — so the dark matches the real reference operating point (§6/§10) instead of the 150 fallback. `--exposure E`
forces a fixed value; `--no-auto-exposure` uses the 150 fallback. **Awaits the rig run** (Edwin) — its verdicts pick
M3 scalar-vs-per-pixel, the bad-pixel map, and the §8 warmup gate.

The masterUserExakta (ELP `32e4:8830`) setup resolved from the server DB: device **0** (video0 capture node), ROI
**665,794,2226,1658**, cubic **A=-6.72651743127379e-09, B=2.68123787138496e-05, C=0.115548014949371,
D=318.141502522378** (maps the ROI to ~405–634 nm; the lamp's 450–620 sits inside). No persisted `calibrationExposure`
→ auto-exposure supplies it.

```
# offscreen self-test (no camera):
diagnostics/probe.sh --selftest
# on the rig — auto-exposes on the lamp, then dark, then warmup (ROI + cubic from Exakta's calibration):
diagnostics/probe.sh --device 0 --roi 665,794,2226,1658 \
  --coeffs -6.72651743127379e-09,2.68123787138496e-05,0.115548014949371,318.141502522378
# dark-only quick pass (still auto-exposes on the lamp first):
diagnostics/probe.sh --device 0 --roi 665,794,2226,1658 \
  --coeffs -6.72651743127379e-09,2.68123787138496e-05,0.115548014949371,318.141502522378 --skip-warmup
```
Sequence: gate (lamp ON) → auto-expose → gate (lamp OFF) → 150-frame dark + ¼×/1×/4× sweep → gate (lamp ON cold) →
warmup. Output → `spectracs-references/probe/<timestamp>/report.json` (+ `dark_roi.png`, `warmup.png`) and the console
verdict block.

### 4.8 Rig findings (2026-07-15, first runs on masterUserExakta's ELP)
The probe surfaced several real issues before any milestone code:
- **RESOLUTION MISMATCH (potentially the most serious — production path).** The `--channels` run crashed because the
  live frame is ~1600 px wide while the calibration ROI goes to x=2226 (y=1658). Both live capture and the probe use
  `DesktopCv2CaptureBackend`, which **hardcodes a 1920×1080 request** (`CaptureBackend.py:54-55`) — and the ELP
  delivers ~1600 wide. So the calibration profile (ROI + px→nm cubic) was authored at a **higher resolution than
  capture delivers**, meaning in production the cubic no longer maps and the longer-wavelength eval bands may fall off
  the captured frame (at 1600 px the ROI reaches only ~544 nm, so `Q_SEARCH` 565–590 / `Q_BASELINE` 555–600 would be
  OFF-FRAME). The probe now reports the captured WxH, clips the ROI, prints the covered nm range, and flags off-frame
  eval bands. **Needs reconciling** — either force the calibration resolution in the backend, recalibrate at the
  capture resolution, or make ROI/cubic resolution-relative. **CONFIRMED on the rig 2026-07-15:** captured
  **1600×1200**; ROI clipped to x2=1600,y2=1200; covered range **405–544 nm only**; **Q_SEARCH (565–590) and
  Q_BASELINE (555–600) are OFF-FRAME** → the pumpkin Q-band evaluation runs on wavelengths never captured, and
  production's single-row extraction reads y≈1226 which is **off the 1200-tall frame**. New top-priority fix;
  `--list-modes` probes whether a wide-enough camera mode exists.
  **RESOLVED to a software mapping bug (2026-07-15):** `--list-modes` shows the ELP delivers exact modes incl.
  2592×1944 and 3264×2448 (all 4:3); `--compare-modes` confirms **DOWNSCALE, same FOV** (profile corr 1.000, peak Δ
  0.001, image corr 0.999) → the spectrum is present at every resolution, just resampled — **the Q-band is NOT lost**,
  only mis-mapped. The calibration resolution is **2592×1944** (proven by physics: the profile peak at norm-pos 0.69
  maps to 572 nm — a white-LED phosphor peak — only at W_cal=2592; 3264 gives 637 nm, too red; the 0.34 feature →
  ~436 nm blue pump). Root cause: `CaptureBackend` requests 1920×1080, which the ELP has no mode for, so it snaps to
  1600×1200 ≠ the 2592×1944 calibration. See §4.9 for the M0.5 fix.
- **Blue-clip lead CLEARED in the eval band; GREEN is the clipper.** Part 2 at exp 8: blue saturation is **0 % across
  BLUE_BAND (450–490)** — the white-LED-blue-peak fear is not confirmed (blue only clips at 408–414 nm, below the
  band). Instead **green** clips (~20 % of ROI pixels — the bright center rows) across ~425–490 nm, which biases the
  qGray reference there. Re-checkable once resolution/extraction are fixed. (Part 1's high G/B %sat is the center-row
  vertical profile: band-mean ~188 with the center rows pinned at 255.) The ELP likely also runs auto-WB/gain the
  backend doesn't pin.
### 4.9 M0.5 — capture-resolution reconciliation (FINAL decision + IMPLEMENTED)
**Decision (Edwin 2026-07-15, revised): PIN the ELP capture resolution to 2592×1944 — the resolution the existing
calibration was authored at.** We first tried "dynamically resolve the HIGHEST mode (3264×2448) + recalibrate", but the
ELP's **exposure control is BROKEN at its top mode** — the image clamps and `setExposure` has ~no effect (observed live
2026-07-15: the calibration auto-exposure sweep saw a flat peak ~100 across all exposures; Edwin independently hit the
same problem with the highest resolution ~3 years earlier). So the max mode is unusable. 2592×1944 is the **highest mode
with working exposure AND the calibration resolution**, so pinning it makes capture ⇔ calibration consistent **with no
recalibration** and keeps the Q-band on-frame (cubic maps the ROI to ~634 nm).

- **The fix (`DesktopCv2CaptureBackend.open`):** request **2592×1944** (an exact ELP mode) + readback confirm. Replaces
  the regression hardcode 1920×1080 (a mode the ELP lacks → snapped to 1600×1200, below the calibration size). A long
  code comment records WHY 2592 and why NOT max/1920, so nobody reverts it. `getResolution()` added.
- **No recalibration** — the existing profile (ROI 665,794,2226,1658 + cubic, authored at 2592) applies directly; the
  extraction center row (1226) is on-frame; the Q-band (555–600 nm) is covered.
- **Drift tripwire** (`ImageSpectrumAcquisitionLogicModule`): warns once + clamps if the ROI ever exceeds the frame —
  catches a future resolution/calibration drift (the exact class of bug that started this).
- **Trade-off accepted:** a per-sensor "magic number" (Edwin wanted dynamic), but it's the only mode that both works
  (exposure) and matches calibration. `TODO`: seed per-sensor in `SpectrometerSensorUtil` when a 2nd camera lands.
- **Verification:** re-run the probe at 2592 (existing ROI/coeffs, now valid) to confirm the covered range spans the
  eval bands (Q-band on-frame) and re-check green-channel clipping (§4.8).

**IMPLEMENTED + VERIFIED (2026-07-15, not committed):** `DesktopCv2CaptureBackend.open` pins **2592×1944**;
`ImageSpectrumAcquisitionLogicModule` gains the ROI⊆frame drift tripwire (warn-once + clamp). No recalibration needed.
Probe `--channels` at 2592 confirms: captured 2592×1944, **no mismatch/off-frame warnings, covered range 405–634 nm
(Q-band on-frame)**. M0.5 DONE. NB the probe's blue-clip verdict on that run is the **CFL calibration lamp** (line
source over-exposed at the probe's fixed exp 8), NOT the white-LED measurement reference — so it does not indict
`T=S/R`. The green/blue-clip fidelity question (§4.8) needs a white-LED `--channels` run at 2592 with the app's
contrast-picked exposure — follow-up, not blocking.

**⚠ SUPERSEDED by §14 (2026-07-15).** The paragraph below records an earlier exploration (a qGray contrast-sweep
rewrite of the calibration auto-exposure) that was **reverted** during isolation testing. The shipped solution is
different: calibration no longer auto-exposes at all — it captures at a fixed stored `calibrationExposure`. See §14
for the as-built, rig-verified state. Kept here only for the exposure-clamp evidence that justified pinning 2592.

**AutoExposureCaptureHelper improved along the way (2026-07-15) — REVERTED, see §14.**
While chasing recalibration (before we pivoted to pinning 2592, which removes the need to recalibrate at all), the
calibration auto-exposure was rewritten to fix the §4.8 ELP bug: max-over-channels metric + monotonic bisection + fixed
350 ms settle → replaced with a **qGray-luminance, contrast-maximizing (peak−background), fresh-frame-settle** sweep
(direction-agnostic; source-agnostic for CFL line vs LED broadband). It *also* proved the max-mode exposure clamp (flat
peak ~100 across all exposures at 3264 → the evidence for pinning 2592). This sweep rewrite was reverted; the live
`CapturePanel`/dev-view captures remain on the original `AutoExposureLogicModule` bisection (still vulnerable to the
§4.8 inversion — the deferred direction-agnostic-auto-exposure milestone, see §14).

**Root cause = a regression, not a design gap.** There is NO resolution-selection code anywhere — the only resolution
logic is the hardcoded 1920×1080 in `CaptureBackend.py:54-55`. Calibration-authoring uses the same
`VideoThread`→backend path, and `CaptureBackend` is a recent refactor (Real-camera / plugin-convergence milestones).
The DB calibration is 2592-wide, which the current backend can't produce — so it was authored before the refactor,
when capture ran at the ELP's higher/native resolution. The refactor ADDED `cap.set(1920×1080)` (a mode the ELP
lacks → snaps to 1600×1200), silently dropping capture below the calibration resolution. It survived because
**nothing validates the frame against the calibration** — the extractor clips silently and still emits a curve. The
per-channel/exposure issues (§4.8) are camera-hardware behaviours invisible in a combined qGray spectrum. All latent;
surfaced only because the M0 probe is the first tool to interrogate the raw sensor (measure-before-build). **Cheap
guard worth adding: assert ROI ⊆ frame + warn when the covered nm range doesn't span the plugin's declared bands.**

Original two issues, still valid:
- **App auto-exposure is broken for the ELP (NEW bug). `AutoExposureCaptureHelper` FIXED 2026-07-15 (not committed);
  `CapturePanel` half still pending.** The `--diagnose` sweep showed
  this ELP's exposure control is **inverted** (lower value = brighter: ROI mean 220@exp1 → 98@exp16) and **clamps**
  (identical for exp ≥ ~16). `AutoExposureLogicModule.findExposure` assumes brightness *rises monotonically* with
  exposure, so on this camera it floors to exposure 1 — the brightest, most channel-clipped point. Affects the
  bench/wizard REFERENCE auto-exposure in production, not just the probe. The probe now sidesteps it with a
  direction-agnostic **sweep picker** (brightest ROI max-channel p99.9 below a clip ceiling). **TODO (own milestone):**
  make the app's auto-exposure direction-agnostic / clamp-aware. Good operating point measured ≈ exp 4 (ROI mean 128,
  p99.9 241, 0 % saturated).
- **Dark is essentially ideal (leans M3 → near-noop).** At exposure 1 (the *longest* integration = worst case for
  dark current), the 150-frame dark gave **black level 0.00 % FS** and **0 % saturation**, with **~10 hot pixels** in
  the ROI band (after the near-zero-dark hot-pixel-threshold fix). Preliminary read: **Topic 4 (dark subtraction)
  near-negligible**; the bad-pixel map has ~10 real candidates (confirm at the true operating exposure). Probe bugs
  fixed en route: (a) wall-clock `drain()` settle (buffered-frame staleness floored auto-exposure); (b) hot-pixel
  detector now needs an absolute floor so a pure-black dark doesn't flag noise; (c) auto-exposure + brightness metric
  scoped to the ROI band; (d) picker switched from max-over-channels to **qGray luminance** p99.9 (below).
- **LEAD (worth a separate look): a low-weight channel (blue) clips across the ROI at *every* exposure.** Max-channel
  p99.9 = 255 for exp 1→500 while qGray p99.9 discriminates (250→212) and qGray %saturated = 0. So blue is pinned at
  255 over much of the ROI even at the dimmest setting — luminance never clips. If this is the **reference** blue
  channel clipping, `T = S/R` in the blue (the pumpkin `BLUE_BAND` 450–490) could be corrupted. NOT chased yet;
  flagged for a per-channel-saturation follow-up — **probe `--channels` mode built 2026-07-15** to confirm it (Part 1
  per-channel %sat vs exposure; Part 2 per-wavelength R/G/B + blue-sat, with a `channels.png` plot; awaits rig run).
  It's also *why* the app's max-channel auto-exposure metric is doubly
  wrong here (inverted curve AND a permanently-clipped channel) — the app fix should measure luminance, not
  max-channel. The probe's picker now uses qGray luminance and lands on ≈ exp 8.

---

## 5. Topic 4 (M3) — dark-frame / black-level subtraction

**Physics.** The sensor produces `measured = g·true + D`, where `D` = black level + dark current + stray light (an
**additive** offset). The evaluation is `T = S/R = (g·S_true + D)/(g·R_true + D)`. S/R cancels the **multiplicative**
`g` (why the lamp drops out) but **`D` survives**. Effect: **T biased toward 1** (contrast compressed), worst where
signal is low — the blue edge and the absorption dips, i.e. **exactly where `BLUE_BAND`/`Q_SEARCH` measure**. There is
**zero** dark/bias/offset handling anywhere in the acquisition path today (only *downstream* absorption baselining,
`DevSpectralPlugin.py:150`).

**Fix (scoped by M0).** Subtract a dark estimate per-pixel from **both** R and S **before** the ratio.
- Option **a** — capture a dark frame (lamp off / slit blocked), per-pixel subtract. Also yields the bad-pixel map
  (§6) → one step, two wins. Adds a "capture dark" acquisition step.
- Option **b** — scalar black-level read from a dark region of each frame; no user step; assumes a usable dark region
  exists.

**Bad-pixel map synergy:** the same dark that gives black-level subtraction also reveals hot/dead pixels — the only
deterministic kill for column-constant hot pixels (§6). Both gated on M0 showing bad pixels actually exist.

---

## 6. Topic 2 (M2) — robust reduction: spatial ≠ temporal

**STATUS: IMPLEMENTED + rig-verified (2026-07-15).** Estimators in a new pure-numpy `RobustReductionLogicModule`
(unit-tested, `diagnostics/robust_reduction_selftest.py`): **spatial** Tukey-biweight per column over an inset band
in `ImageSpectrumAcquisitionLogicModule` (measurement branch only — calibration branch untouched), masking
per-channel saturation to NaN before qGray; **temporal** sigma-clipped mean in `MeanSpectrumLogicModule` (rewritten:
align-by-key, tolerates N<150), which `MeanOp` delegates to → both the live display and the processing pipeline get
it. Inset drop = `__INSET_FRACTION` (0.2, tunable). Bad-pixel map NOT built (dark near-zero; Tukey covers the rare
hot pixel). Design below as-built.


**Load-bearing subtlety (confirmed by research + duck):** a hot pixel is at the *same location in every frame*, so
**no temporal combine over frames removes it** — it's the consistent value, not an outlier. Only **spatial** rejection
across rows, or a **bad-pixel mask**, kills it. Conversely, a glitch/cosmic-ray-like frame is transient — only the
*temporal* stage catches it. The two stages target different failure modes and live in different modules.

| Enemy | Nature | Killed by | Where |
|---|---|---|---|
| Hot / dead pixel | fixed location, every frame | **bad-pixel mask** (primary) + **spatial** robust estimator | `ImageSpectrumAcquisitionLogicModule` |
| Saturated pixel | censored value (`==255`) | **explicit mask**, both stages | both |
| Glitch frame / read spike | transient, one frame | **temporal sigma-clipped mean** | `MeanSpectrumLogicModule` / `MeanOp` |
| Random shot/read noise | Gaussian | averaging over rows + frames (√N) | both |

**The estimator, asymmetric because row-count ≪ frame-count:**

- **Spatial (rows), few samples — `ImageSpectrumAcquisitionLogicModule`:** replace the single-centre-row read with a
  reduction over an **inset band** (see below). Mask saturated (`==255`) / dead (`==0`), then **Tukey biweight**
  location per column (**Edwin-LOCKED 2026-07-15**: robust at small N, smoothly discards a hot pixel that lands in the
  band; superior to a hard σ-threshold when N is small). Tuning constant `c = 6·MAD`, 1–2 refinement iterations.
- **Temporal (frames), 150 samples — `MeanSpectrumLogicModule`/`MeanOp`:** replace the plain mean with a
  **sigma-clipped mean** (center/spread from **median+MAD**, **k=3σ**, iterate to convergence, ~3–5 passes; final =
  mean of survivors). Keeps the full √N noise benefit while rejecting glitch frames. Must **not** assume exactly 150
  frames — dropped frames are silently skipped (`__runBurst:188`) so N<150 is valid.
- **Bad-pixel map** (from the M0/M3 dark): the deterministic kill for column-constant hot pixels. Gated on M0.

**Inset band, not full ROI height (Edwin 2026-07-15).** Drop the top/bottom few rows of `Y1..Y2`: the edge rows can
bleed the dark border *outside* the slit **and** carry the most smile-induced λ error. Use a **moderate** band.

**`MeanSpectrumLogicModule.py:14` is rewritten regardless** — it uses deprecated `numpy.matrix`, assumes every frame
dict has identical keys/order, and zips against the *last* frame's keys (`:16`); the robust rewrite hardens this and
tolerates N<150.

**Shared-path note:** the temporal change touches **both** the live display mean **and** the real processing pipeline
(`MeanOp`) — identical reduction in both. Click-through verify after.

**Explicit non-goals (Edwin-confirmed):** Horne 1986 optimal (profile-weighted) extraction and smile/keystone
correction — over-engineering for a cheap slit + webcam. The inset moderate band is the pragmatic mitigation.

**Superseded idea (Edwin 2026-07-15):** "randomize which centre row is read." A random single row *adds* variance;
the band reduction uses all good rows at once and strictly dominates it. Kept here as rationale.

---

## 7. Topic 3 — normalization: nothing to wire in (documented no-op)

`T = S/R` already self-normalizes the lamp (§2), and exposure is already locked (§6), so absolute raw scale is
irrelevant downstream. Peak-normalizing each capture to its own max gives `T' = (S/R)·(maxR/maxS)` — a **constant
scalar** → a *vertical* rescale of T / a *constant offset* in A. It therefore:
- **cancels** in baseline-*differenced* metrics like `D_Q = peak − linearBaseline` (`DevSpectralPlugin.py:148-151`);
- **biases** absolute-A readings and the `VALUE_CEILING=1.5` threshold.

So per-capture normalization is **unnecessary and mildly harmful to absolute A** — *not* "destroys the signal" (an
earlier overstatement, corrected). **Decision (Edwin 2026-07-15): do not wire in any normalization, and no
display-only normalization either.** The `NormalizeSpectrumLogicModule` (max→1) stays unused. Recorded so it isn't
re-litigated.

## 8. Warmup protocol (mains LED bulb)

The 220 V LED bulb drifts in brightness/color over its first seconds–minutes (junction heating). If the **reference**
is captured cold and the **sample** later warm, `R` has shifted and `T = S/R` is wrong — no downstream math fixes it.
M0 measures the drift curve. **Open (decide after M0):** enforced warmup wait before reference capture vs a displayed
"let it warm up" coach line.

## 9. Topic 1 (M1) — plugin-driven wavelength ROI (450–630 nm)

**STATUS: IMPLEMENTED + rig-verified (2026-07-15).** As-built: `CaptureView.wavelengthMin/MaxNm` (None → legacy
400–700); `DevSpectralPlugin` declares the window (currently **450–630**, adjusted from the wire's monitor) on
every capture step + exposes `declaredEvalBands()` + asserts at build that the window ⊇ all eval bands (D1);
`CapturePanel.__captureWindow()` feeds it into the ROI clamp AND the preview overlay, with a shortfall warning
when the calibration can't physically reach the requested edge (D3). Design below as-built.

**Decision (Edwin 2026-07-15): HARD capture clamp, plugin-declared, for now.** The stored spectrum is truly limited
to the plugin's window; the dead lamp bands never enter the data (they'd only feed the S/R floor-guard garbage). The
range is a lamp property, so it may migrate to `SpectrometerCalibrationProfile` when real instruments carry per-lamp
ranges — noted, not now.

**Design:**
- New optional fields on `CaptureView`: `wavelengthMinNm` / `wavelengthMaxNm`, default `None`.
- `DevSpectralPlugin` sets the window (one plugin-level constant copied onto each capture step's `CaptureView`).
- `CapturePanel.__applyExtendedRoi` uses `camView.wavelengthMinNm or __NM_MIN` (and max) → `extendedXBounds`.
  **`None` falls back to today's 400–700** — non-plugin / non-doc behaviour unchanged.

**Two guards (duck-surfaced):**
- **Blue-side margin.** `BLUE_PEAK` starts *exactly* at 450 = the clamp edge; one rounding nm loses its first bin.
  Spec the plugin range as **outermost declared band ± a few-nm guard**, and **assert at plugin load that
  `range ⊇ all declared eval bands`**.
- **Shortfall warning.** `extendedXBounds` silently clamps to the raster (`ExtendedRoiLogicModule.py:29-31`) — if
  calibration can't physically reach 450 or 620 you get a *narrower* window with no notice. **Log/flag when the
  achieved window < requested** (an operator confidence signal).

## 10. Evidence chain — exposure is already locked (Topic 3 / §2)

- Auto-expose gated `role == REFERENCE` (`CapturePanel.py:443-445`); sample never auto-exposes (comment :438).
- Converged value → slider (`:392`) → live thread (`:287-288`); locked after the reference burst into
  `__lockedExposure` (`:480-481`).
- Sample tab re-pins `__lockedExposure` on the same running thread and **disables** slider + auto-expose checkbox
  (`:230-242, :309/313/315`); fresh stream start also uses it (`:331-335`).
- Backend holds it in V4L2 manual mode (`CaptureBackend.py:57-62,84-91`); no driver auto-exposure; gain never written
  (consistent by default).
- A **new** reference after a sample drops the stale sample so a mismatched S/R can't persist (`:482-486`).
- Verdict: **sample cannot be captured at a different exposure — T = S/R is exposure-consistent.**

## 11. Open questions for Edwin

1. **Row estimator** — **LOCKED: biweight** (Edwin 2026-07-15).
2. **Build order** — **LOCKED: the M0 probe script is built first** (Edwin 2026-07-15), run on the rig; its output
   picks the rest.
3. **M3 dark scope** — (a) per-pixel dark capture vs (b) scalar black-level. **Resolved by the M0 probe**, not now.
4. **Warmup handling** — enforced wait vs coach line. **Resolved after M0** measures the drift.

## 12. Sources

Astropy CCD Reduction & Photometry Guide (image combination; hot-pixel identification); IRAF `imcombine`
(kappa-sigma rejection); Horne 1986 (optimal extraction, cited as non-goal); Beers, Flynn & Gebhardt 1990 (Tukey
biweight); GNU Astronomy Utilities (sigma clipping). Full URLs in the research transcript.

## 13. Calibration wavelength anchor — color-constrained line detection (DESIGN, validated; port pending)

**Status (2026-07-15):** the wavelength-calibration line detection regressed at the 2592 capture resolution and was
re-designed + validated **end-to-end** in the standalone unit test `diagnostics/calibration_fix_test.py` (real ROI
detection → extract → detect 6 lines → refit ≤ 0.51 nm, monotonic; all lines on the correct features). **NOT yet ported
to the app.** App targets are the help-dialog reference `resource/expectedDetection.png` (405/436/487/546/611 nm).

### 13.1 Root cause
The app's `SpectrometerWavelengthCalibrationLogicModule` anchors on "**the single most-prominent peak = Hg green
546**". At 2592 the green doublet (546.5 + 542.4) resolves into two peaks — its prominence splits — and the sharp
**Europium red** line (~611) out-prominences it, so the anchor mislabels red as green and the whole calibration
(everything is found *relative* to green) collapses. At 1600 the doublet blended into one taller peak → green
dominated → it "worked before". Independent of exposure/auto-exposure (fails at all exposures).

### 13.2 Line-by-line detection chain (order = dependency; ALL relative to the GREEN anchor)
```
STEP 1  GREEN       SELECT BY COLOR       most-"green" peak, whole spectrum      [anchor]
   │                                       (prominence alone picks Eu red — wrong)
   ▼   g = green col
STEP 2  RED (Eu)    SELECT BY PROMINENCE  largest peak with col > g              [right of green]
   │                                       (611 saturates toward white — a colour filter would skip it)
   ▼
STEP 3  VIOLET      SELECT BY COLOR+POS   blue-ish peaks with col < g, clustered → LEFTMOST line
   │                                       (violet 405 & blue 436 both read blue-ish → split by position)
   ▼
STEP 4  BLUE        SELECT BY COLOR+POS   next blue-ish line after violet (only one → it IS blue 436)
   ▼
STEP 5  AQUA        SELECT BY COLOR       most-"cyan" peak, col < g
   ▼
STEP 6  GREEN-LEFT  SELECT BY COLOR       most-"green" peak in the doublet window  g-60 < col < g-4
```

### 13.3 Selector summary
```
LINE          SELECTED BY          COLOR        POSITION          PROMINENCE
green         COLOR                green         whole-spectrum    tie-break
red (Eu)      PROMINENCE           –             right of green    PRIMARY
violet        COLOR + POSITION     blue-ish      leftmost line     –
blue          COLOR + POSITION     blue-ish      next line         –
aqua          COLOR                cyan          left of green     tie-break
green_left    COLOR                green         doublet window    tie-break
```
Only two things change vs the app today: **green** anchors by *color* (was most-prominent-overall), and **violet/blue**
split by *blue-cluster + leftmost* (was a position cascade that mis-shifted when a line was absent). Eu = largest-right
(with a direct-max robustness tweak — the app's raise-the-threshold loop can jump to 0 peaks on the busy red end).

### 13.4 Color model — CURRENT (hard hue buckets) vs PROPOSED (soft, physics-grounded)  ← open design point
**Current** (`_hueBucket`, used by the test + the app's color guard): classify a pixel into a discrete bucket via
**hard-coded degree intervals** (`red <20`, `orange <45`, `yellow <70`, `green <160`, `cyan <200`, `blue <255`,
`violet <290`). Brittle at boundaries — a hue of 159° vs 161° flips green↔cyan. Edwin: dislike the hard intervals.
**Proposed (Edwin 2026-07-15): COMBINE two interval-free signals — a soft hue-similarity SELECTOR + a per-channel
dominance GUARD.** They're complementary: hue-similarity is physics-grounded and good at *selecting*, but hue is
unreliable at low saturation; per-channel dominance is a ratio that still discriminates when saturation is low — an
independent confirmation + confidence.
- **SELECT** (which peak is this line): reference colour per line = `SpectralColorUtil.wavelengthToColor(target_nm)`
  (green←546.5, blue←435.8, cyan←487.7, violet←404.7 …); `hueScore(p) = saturation(p) × max(0, cos(hue(p)−hue(ref)))`
  (smooth, no intervals); pick `argmax( hueScore × prominence )`.
- **GUARD / CONFIDENCE** (do we trust it): `chanScore(p)` = target channel dominance, normalised to [0,1] —
  green `(G−max(R,B))`, blue `(B−max(R,G))`, cyan `(min(G,B)−R)`, red `(R−max(G,B))`;
  `confidence = min(hueScore(picked), chanScore(picked))`; if `confidence < τ` → flag the anchor "low-confidence"
  (warn / prefer the next candidate).
Two independent votes (hue angle vs channel ratio). Gives the calibration a real per-line **confidence** to report
instead of a silent pass/fail. No arbitrary interval boundaries anywhere; reference colours come from the physical
wavelength→colour map.

**AS PROTOTYPED + VALIDATED (2026-07-15, `calibration_fix_test.py`, all 6 lines correct, refit 0.42 nm) — the roles
FLIPPED from the sketch above:**
- **`wavelengthToColor` hue ≠ the camera's rendering** (e.g. green ref = 84° yellow-green, but the camera's green line
  is ~120°). With a broad cosine, an off-hue but hugely-prominent peak (Eu red, hueScore 0.66 vs green ref) can win →
  **hue-similarity is UNRELIABLE as the selector.**
- So **channel dominance is the SELECTOR** (a gate: `chan_score(kind) > τ`), prominence ranks within it (Eu =
  prominence-only; violet/blue = leftmost within the blue-channel gate). **hue-similarity + channel are reported as
  CONFIDENCE** (two scores, not a single `min()`).
- **Bright/saturated lines score LOW on colour and that's expected, not failure:** green 0.15/0.19, red 0.00 (near
  white) are correctly detected by channel-gate + prominence; pure lines (violet 0.95, blue 0.81, aqua 1.00) confirm on
  both. So a low colour score = "bright line, colour unconfirmed", not "wrong". Report BOTH scores; don't hard-gate on
  a harsh `min`.
This keeps Edwin's goal (no hard hue intervals; weighted signals) and adds the finding that the **channel ratio is the
robust selector** and hue the softer confidence. **Ready to port** (`SpectrometerWavelengthCalibrationLogicModule` +
`SpectralLinesSelectionLogicModule`), verifying each change against `calibration_fix_test.py`.

### 13.5 Port — IMPLEMENTED (2026-07-15, not committed), DRY (Option A)
- **NEW `WavelengthLineDetectionLogicModule`** — the SINGLE source of truth for the colour-constrained detection
  (`detect(spectrum) → {SpectralLineMasterDataColorName: DetectedLine(pixelIndex, hueScore, chanScore)}`). No ORM deps.
- **`SpectralColorUtil`** gains `hueSimilarity(color, refColor)` + `channelDominance(color, kind)` (shared colour
  scoring; reference colours from `wavelengthToColor`).
- **`SpectrometerWavelengthCalibrationLogicModule.execute()`** now just calls `WavelengthLineDetectionLogicModule` and
  wraps the results into `SpectralLine` + master data (removed the 6 `_processSpectralLine*` methods + doublet
  constants). Downstream cubic fit unchanged.
- **`calibration_fix_test.py`** refactored to build a `Spectrum` and call the SAME module — its duplicated algorithm
  deleted (true DRY). `--replay` PASSES all 5 assertions (0.53 nm) via the app module.
- ROI: the app already re-detects the ROI each calibration (stored ROI can be stale — camera moved 665,794→558,902);
  no change needed there.
- **Standalone import** of the calibration logic module triggers a SQLAlchemy mapper-registry error (needs full app
  bootstrap) — CONFIRMED pre-existing (the old module imported the same ORM chain). Final end-to-end verification =
  run the calibration in the app on the rig.

## 14. Rig-driven calibration fixes — AS-BUILT, VERIFIED ON RIG (2026-07-15)

Running the ported §13 detection in the app on masterUserExakta's ELP surfaced three real bugs, each measured then
fixed and confirmed by Edwin on the rig. All uncommitted at time of writing; this section is the design-of-record.

### 14.1 Calibration no longer auto-exposes — fixed stored exposure  ⚠ SUPERSEDED by §14.6 Fix 4 (now auto-exposes)
- **Symptom:** both calibration steps captured a wrong-brightness burst — first bloomed, then dark — so the mercury
  green doublet collapsed and peak detection failed.
- **Root cause:** both steps ran an auto-exposure *pre-pass* (`AutoExposureCaptureHelper.autoExposeForSensor` →
  `AutoExposureLogicModule.findExposure`, a bisection that assumes brightness rises **monotonically** with the
  exposure value). This ELP's control is **inverted** (higher value = dimmer) — §4.8 — so the bisection can't
  converge and lands nondeterministically. The passing unit-test fixture never hit this: it captures at a **fixed**
  exposure 150.
- **Fix:** new `AutoExposureCaptureHelper.resolveFixedExposureCapture(sensor)` — resolves `(deviceIndex,
  storedExposure)` with **no bisection** (reuses the device-index resolver + `__seedExposure`). Both calibration
  views (`SpectrometerCalibrationProfileWavelengthCalibrationViewModule`, `...HoughLinesViewModule`) call it instead
  of `autoExposeForSensor`. Calibration is now a deterministic fixed-exposure capture.

### 14.2 Advanced (consensus) module anchored green with the same bug → "methods disagree"
- **Symptom:** calibration ran but reported **low confidence — methods disagree on many lines**.
- **Root cause:** the consensus cross-checks the simple detection against the independent "advanced" predict-and-snap
  module. We fixed green-anchoring in the *simple* module (§13) but `SpectrometerWavelengthCalibrationAdvancedLogicModule`
  still anchored green via `_anchorPixel(most-prominent)` — the exact doublet-split/Eu-out-prominence bug — so its
  cubic disagreed with the now-correct simple result.
- **Fix:** the advanced module now takes its green + red anchors from the shared `WavelengthLineDetectionLogicModule.
  detect()` (single source of truth). In-design: the consensus docstring already treats green/red as *shared* anchors;
  the second opinion's independence lives in the predict-and-snap of the OTHER lines. Removed the now-dead
  `_anchorPixel` + unused `peak_prominences` import.

### 14.3 ROI band too tall (bloom) → calibrationExposure is resolution-dependent
- **Symptom:** detected ROI matched the fixture horizontally (same lamp alignment) but was ~314 px **taller**
  vertically, with black margin above/below the light stripe.
- **Root cause:** the stored ELP `calibrationExposure=78` was tuned at the **old, lower** capture resolution. At the
  pinned 2592×1944 (§4.9) each emission line spreads over more pixels, so per-pixel intensity is lower and 78 now
  over-exposes → vertical bloom inflates the band-edge detection.
- **Fix:** `SpectrometerSensorUtil.__CAPTURE_SETTINGS_BY_HARDWARE_ID['32e4_8830']` calibrationExposure **78 → 150**
  (the single source of truth; the model repo). Confirmed on the rig: at 150 the ROI tightens to the fixture bounds
  (y≈906/1782) and the doublet resolves. **Lesson:** calibrationExposure must be re-judged whenever capture
  resolution changes.

### 14.4 Auto-exposure now — where it runs (FINAL, see §14.6)
| Path | Strategy |
|---|---|
| Calibration ROI/Hough + wavelength peak-detect | **Synchronous in-thread** sweep before the burst (§14.6 Fix 4) — the fixed-150 of §14.1 is RETIRED |
| Dev capture bench (`DevCaptureViewModule`) | **Synchronous in-thread** sweep (§14.5–14.6) |
| Measurement capture (`CapturePanel`) | **Synchronous in-thread** sweep; capture blocks on it, drops the first post-sweep frame (§14.6 Fix 5) |

`AutoExposureCaptureHelper` had zero callers and has been **deleted**.

### 14.5 Shared direction-agnostic auto-exposure — the decision logic
`AutoExposureLogicModule.findExposure` rewritten from a monotonic low→high bisection (which assumed brightness
rises with the exposure VALUE — false on the inverted-seeming ELP) to a **direction-agnostic sweep-and-select**:
- **Phase 1** probes a coarse geometric ladder across [min,max] and measures delivered brightness of each.
- **Phase 2** finds the first adjacent probe pair that straddles the target (one ≤target, one >target) and bisects
  that interval, tracking the crossing by the ≤target/>target SIGN (not by which side is brighter) — so it
  converges whether the exposure axis rises OR falls, and tolerates clamped/plateau regions a bisection can't.
- Selection: brightest measured exposure that stays ≤target (brightest capture without clipping); if all clip, the
  dimmest; direction-agnostic because the winner is chosen purely by measured brightness.
- Excludes exposure=1 (a UVC edge artifact that reads ~255, `MIN_SEARCH_EXPOSURE`).
- Signature unchanged; both callers share this one decision module (DRY). Offscreen self-test (synthetic normal /
  inverted / clamped / underexposed curves) all PASS within an 8-probe budget — never selects a clipping exposure
  when a non-clipping one exists.

### 14.6 The real bug was MEASUREMENT, not the search — synchronous in-thread AE (RIG-VERIFIED 2026-07-15)
The decision logic (§14.5) was never the problem; **measuring brightness through the async live stream was**. The
full saga (the lesson is expensive, and every fix below was measured then rig-verified):

- **What we saw:** the live AE returned garbage — probes reading a false 255 at low exposure, exp 22 and exp 500
  reading the *same* value, the search landing on exp 1 (dark) or maxing out at random, run-to-run inconsistent.
- **Root — async measurement + low fps.** Pinning 2592×1944 (§4.9) drops the ELP to ~1–2 fps. A manual exposure
  change then takes ~1.2–1.5 s of wall-clock to take effect (looks like a fixed *frame-count* of sensor latency,
  stretched long by the low fps). Measuring off the async streaming thread — read whatever `__latestImage` the Qt
  pipeline last pushed — reads frames from *before* the change applied → stale/wrong brightness. Frame-count
  settles fail (fps itself tracks exposure); wall-clock settles fought display/event-loop lag. **At a normal
  ~30 fps this latency is ~50–100 ms and the async approach would mostly have gotten away with it — the high
  resolution didn't create the fragility, it stretched every transient long enough to fail reliably.**
- **The tell:** `capture_quality_probe.py --diagnose` produced a clean monotonic curve at every exposure — because
  it reads the backend **directly and synchronously** (set exposure → actively drain → measure). The live path did
  the opposite.

**Fix 1 — synchronous in-thread sweep.** Run the sweep **inside the capture thread** (`VideoThread`, which owns the
backend). `requestAutoExpose()` sets a request the run loop picks up before the next grab; `__runAutoExposeSync`
does per probe: `setExposure` → `__drainSync` (actively read+discard for a fixed wall-clock window) → measure.
Progress/result return via `autoExposureProgress`/`autoExposureFinished`. No Qt event loop, no async reads → the
lag class is gone. Calibration burst threads inherit it (auto-expose runs before the 50-frame burst); `CapturePanel`
blocks on `__waitForAutoExposure()` so the reference burst runs after the sweep.

**Fix 2 — per-channel metric (`channelPeak`), NOT qGray.** First tried qGray (high percentile of luminance) to dodge
the max-over-channels "255 peg". That was wrong: qGray *averages the channels*, so a green line whose G and B clip
to white reads only ~246 — invisible as saturation. The AE then over-exposed until the strong green line clipped to
a white plateau (R≈G≈B), its green-channel dominance (`G−max(R,B)`) collapsed to ~0, and the colour-anchored
detection (§13) mis-anchored green onto the yellow line → calibration failed (8.6 nm). `channelPeak` = p99.9 of
`max(R,G,B)`, target **245** just below the 255 clip → *guarantees no channel saturates*, so lines stay chromatic.
(p99.9 not raw max, so a handful of hot pixels can't peg it; real line clipping is ≫0.1% of pixels.)

**Fix 3 — fixed settle drain, not adaptive.** A big exposure jump under-reads if measured too early (the sensor is
still ramping). First tried an *adaptive* stabilize-drain (drain in chunks until the reading stops changing) — it
**false-converged** in the ramp's flat ~1.2 s latency window (two similar chunks → "settled" at 225 when the true
value was 255), so the AE still picked the over-bright exposure. Measured the ramp directly (`--diagnose`-style
loop at fixed exp): ~1.2 s latency then a jump, steady by ~1.5 s. So each probe now drains a **fixed 1.8 s**
(`__AUTO_EXPOSE_SETTLE_MS`) — a flat wait past the settle can't misfire. Simpler and reliable; the cost is a ~15 s
sweep at low fps.

**Fix 4 — calibration auto-exposes (retired the fixed-150 path).** We first made calibration capture at a fixed
stored exposure (§14.1) because the *broken* AE over-exposed. Once the AE reliably prevents saturation, fixed-150
became the liability Edwin warned about: as the CFL **warms up brighter**, 150 clips → green plateau → detection
fails. Both calibration views (`...WavelengthCalibrationViewModule`, `...HoughLinesViewModule`) now call
`requestAutoExpose` before their burst (device index via `SensorCaptureIndexResolver`). `AutoExposureCaptureHelper`
(the old fixed/bisection pre-pass) is deleted. Rig: AE chose exp 32 on the warm lamp, green anchored correctly, **0.66 nm PASS**.

**Fix 5 — reference-only first-frame outliers.** After the sweep, two view-side hazards produced outlier frames at
the *start* of the reference burst (sample never sweeps, so never showed them): (a) the chosen exposure is a fresh
change → ramping — so `__runAutoExposeSync` now drains 1.8 s at `best` *before* handing back; (b) the thread emits
nothing during the ~15 s sweep, so `CapturePanel.__latestImage` stays stale (pre-sweep frame) — so `__runAutoExposure`
nulls it, and the reference path additionally **waits for the first post-sweep frame and discards it** (this ELP's
recurring first-frame quirk) so the burst starts on the second, clean frame.

> **AMENDED 2026-07-18 — the sweep now DOES emit (a live preview), and part (b)'s invariant is kept by a FLAG, not
> by silence.** The freeze in (b) meant no image at all for the whole ~15 s sweep (Edwin: "no image during
> auto-exposure", both the reference capture and Dev>Capture). `__runAutoExposeSync` now paints each drained frame
> via a new `VideoThread._emitPreview()` hook (`DevCaptureVideoThread` overrides it), so you watch the exposure
> ramp. Two traps, both hit and fixed: **(i)** a fire-and-forget emit **segfaulted** — the capture thread read the
> next frame (cv2) while the main thread painted the last (Qt), concurrently; the preview therefore uses the SAME
> `event.wait` one-frame backpressure as `afterCapture`, so the thread sits idle during each paint. **(ii)** these
> preview frames re-broke Fix 5: `CapturePanel.handleVideoThreadSignal` was setting `__latestImage` on *every*
> frame, so a preview frame landed there during the sweep and the drop consumed *it* instead of the mid-ramp
> outlier → the outliers returned. Fix: `VideoSignal.isPreview=True` on preview frames, and `CapturePanel` **skips
> `__latestImage` when `isPreview`** — so (b)'s "nothing lands in `__latestImage` during the sweep" still holds and
> Fix 5's drop is unchanged. Lesson: a "nothing happens here" invariant is fragile; make it explicit (a flag), not
> incidental (silence).

- **Lesson:** never auto-expose by reading an async live stream. Drive the sensor synchronously; drain by
  wall-clock past the settle; measure per-channel so nothing clips; and don't trust the first frame after a change.

### 14.7 Tuning constants & known fragilities (READ BEFORE porting to another camera/resolution)
The AE is robust *for this ELP at 2592×1944 under the CFL/LED lamps*, but several constants are **measured against
that specific setup**, not adaptive. If the camera, resolution (→ fps), or lamp changes materially, revisit these:

| Constant | Where | Value | Why / how it could break |
|---|---|---|---|
| `__AUTO_EXPOSE_SETTLE_MS` | `VideoThread` | 1800 ms | Sized to the measured ~1.5 s exposure ramp. Ramp is ~frame-count latency → its wall-clock scales with **fps**; at higher fps it's wasteful, at slower it could under-settle. |
| `DEFAULT_TARGET` | `AutoExposureLogicModule` | 245 | Per-channel clip headroom below 255. Fine for 8-bit; revisit if a channel needs more margin. |
| `MIN_SEARCH_EXPOSURE` | `AutoExposureLogicModule` | 2 | Excludes the exp=1 UVC edge artifact (reads ~255). Camera-specific. |
| iterations / ladder | callers pass 8 | 8 probes | 3 coarse + up to 5 refine. Each probe = one 1.8 s drain → ~15 s total (the UX cost). |
| first-frame discard | `CapturePanel` | drop 1 | Assumes exactly ONE bad frame after a sweep. If the camera emits >1, this wouldn't catch it. |
| drain window (test) | `calibration_fix_test.auto_expose` | 1800 ms | Mirrors the app; same fps assumption. |

**The real hardening (deferred):** replace the fixed settle with a *properly robust* adaptive one — drain until the
reading is stable for **K consecutive reads** AND a **minimum wait** has elapsed (past the latency window), with a
cap. That removes the magic numbers and the false-convergence trap. Also possible: run the AE at a **low resolution**
(fast fps → fast settle) then switch to 2592 for the final capture — kills most of the timing pain, at the cost of
resolution-switch complexity and verifying exposure carries across modes.

**Cleanup done:** the dead `AutoExposureCaptureHelper` has been deleted.

### 14.8 Reference-outlier CONFIRMED IN THE FIELD (2026-07-18) — drop-1 + fixed-settle is insufficient (DIAGNOSIS; fix deferred)

The §14.7 caveat *"drop 1 assumes exactly ONE bad frame … if the camera emits >1, this wouldn't catch it"* is now
**observed, not hypothetical.** Three bench captures (Edwin, ksnip 2026-07-18; same physical specimen used for BOTH
roles for convenience): the two **Reference** spectra show a thick band of **gray per-frame traces sitting BELOW the
green mean**; the **Sample** is a single clean line with almost none. Diagnosis (rubber-duck, code-grounded):

- **Reference-only ⇐ only the reference runs AE right before its burst.** Sample reuses the locked exposure
  (`CapturePanel.__lockedExposure`, `:343`) on a warm, already-settled stream — no exposure change, no ramp, uniform
  frames. Reference sweeps, then bursts.
- **Below the mean ⇐ the exposure ramps UP to `best`.** UVC/V4L2 exposure changes take **several frames** to take
  effect (the same ~1.2–1.5 s / ~frame-count latency §14.6 measured). The burst starts before the ramp fully lands, so
  the **first N reference-burst frames are still at the lower, not-yet-settled exposure → globally dimmer → below**.
  The single `best`-drain (Fix 5) + `drop 1` covers **one** such frame; the ELP produces **more than one**.
- **Why the sigma-clip doesn't rescue it (new angle, not just AE):** `MeanSpectrumLogicModule` reduces with a
  **per-wavelength-bin** `sigmaClippedMean`. That rejects an *isolated* read-spike (1 of N), but the ramp is a
  **coherent group** (several dim frames). With a large-minority dim cluster the per-bin σ inflates and the mean is
  pulled toward them — they survive the clip and **bias the reference low**.
- **Why it's not cosmetic — it corrupts T = S/R.** The reference is the denominator; a low-biased, non-uniform R
  biases **T high** and **distorts its shape**, so the pumpkin ratio / colour verdict inherits the error. Foundational.

**The fix — two phases (deferred; implement on explicit request). Design pinned 2026-07-18.**

Fix #1 **prevents** the dim frames (an adaptive *warmup* before the burst); Fix #2 **catches** any residue **and
guarantees the effective frame count** (per-frame rejection + top-up). Do both — #1 makes #2 cheap, #2 makes #1 safe.

Two kinds of capture, only one counted: **warmup frames** are grabbed-and-discarded to let the exposure ramp finish;
**burst frames** are the counted ones the mean is built from. The warmup stabilizes *exposure*, not the mean.

**Target flow (ASCII sequence — for later reference):**
```
 CapturePanel                 VideoThread / Camera            Reducer (MAD + σ-clip)
     │ requestAutoExpose ───────────▶│                              │
     │◀──── autoExposureFinished ────│  sweep, pick+apply `best`     │
 ═══ WARMUP / SETTLE — frames DISCARDED, not counted (Fix #1) ═══
     │ grab ────────────────────────▶│                              │
     │◀──────── frame ───────────────│                              │
     │ b = channelPeak(frame)        │                              │
     │ stable for K reads? ── no ──┐  │   (throwaway loop, capped)   │
     │        grab again  ◀─────────┘  │                              │
     │ ...yes → exposure settled      │                              │
 ═══ BURST — COUNTED, target N ═══
     │ grab ────────────────────────▶│                              │
     │ accepted.append(frame)  … until len == N                     │
 ═══ REJECT + TOP-UP — guarantees N EFFECTIVE (Fix #2) ═══
     │ MAD-reject(per-frame scalars) ──────────────────────────────▶│
     │◀──── survivors = N − k (dropped k dim/spike frames) ─────────│
     │ survivors < N ? ─ yes → grab k more (BURST) → re-MAD … cap   │
     │ survivors == N                                               │
 ═══ REDUCE ═══
     │ sigmaClippedMean(N clean) ──────────────────────────────────▶│
     │◀──────────────── green mean spectrum ───────────────────────│
```

**Per-frame rejection = MAD on a per-frame brightness scalar** (the axis-change that beats the per-bin σ-clip):
```
 scalarᵢ  = median over wavelength bins of frame i's spectrum   (one number per frame)
 median   = median(scalars);  MAD = median(|scalarᵢ − median|);  σ̂ = 1.4826·MAD
 drop frame i  if  |scalarᵢ − median| > k·σ̂   (k≈3)   ← MAD's 50% breakdown survives a big dim minority
```
Example — scalars `[86,88,101,100,102,99]` (2 ramp-dim): median 99.5, MAD 2.0, σ̂ 2.97, cutoff 8.9 → deviations
`[13.5,11.5,1.5,.5,2.5,.5]` → frames 1&2 dropped; σ-clip mean then rides the clean four. The per-bin σ-clip *keeps*
those two (their presence inflates the per-column σ → wide band); the per-frame scalar makes the coherent group obvious.

**Ensuring N effective:** the **grab-until-N-accepted** policy — a dropped frame is *replaced* (grab k more, re-run
MAD) until N survive, **capped at N + margin** so an unstable camera yields a clean "capture failed", not an infinite
loop. Because Fix #1 removes the systematic ramp, MAD drops ≈ 0 and the top-up almost never fires.

**Rubber-duck (impl, code-grounded 2026-07-18):**
- **Fix #1 lives in `VideoThread`, synchronously — reuse what's there.** `__runAutoExposeSync` already drains at
  `best` via `__drainSync(1800ms)` and measures `AutoExposureLogicModule.channelPeak(frame)`. Make that tail drain
  **adaptive**: loop `__drainSync(short)` → `channelPeak` until K consecutive peaks differ by < ε, or a cap. Same
  thread that owns the backend, same metric — no new machinery. Retire the fixed `__AUTO_EXPOSE_SETTLE_MS` reliance
  and the CapturePanel `drop 1`.
- **⚠ the burst reads the ASYNC stream, not the sync drain.** `CapturePanel`'s provider pumps `__latestImage`
  (`__pumpFrames(120)`), so there's a sync-AE → async-stream handoff. Once exposure is settled the async frames are at
  `best` (BUFFERSIZE=1 limits stale carry-over), but the handoff is why a *single* fixed drop was ever needed. Fix #2's
  rejection makes the burst robust to a stray handoff frame regardless.
- **Fix #2 is a PURE addition to the reducer — no capture change.** `RobustReductionLogicModule` already carries the
  MAD scaling (`__MAD_TO_SIGMA = 1.4826`) and MAD machinery; add `rejectDimFrames(stack) -> keep-mask` and call it in
  `MeanSpectrumLogicModule.meanSpectrum` **before** `sigmaClippedMean`. Unit-testable in isolation, headless.
- **Top-up is the ONLY capture-loop change.** `SpectralWorkflowEngine.__runBurst` is today a flat
  `for _ in range(frames)`; rework to *grab until N survive the reject* (cap N+margin). It already has each frame's
  extracted spectrum, so it can compute the per-frame scalar inline.
- **Two scalars, two stages — intentional.** Warmup judges RAW image brightness (`channelPeak`, pre-extraction, in the
  thread); reject judges the EXTRACTED spectrum (`median` across bins, in the reducer). Different data at different
  points; both are correct.
- **Virtual/headless path stays valid.** `__runBurst`'s default virtual provider yields identical frames → MAD == 0 →
  `rejectDimFrames` keeps all (the existing MAD==0 guards apply). No regression to headless tests.
- **Display collapses for free.** Post-fix, the gray per-frame traces should ride on the green mean (the reject removes
  the below-mean group), matching the Sample plot today.

**Impl phases (tabular):**
```
 Ph │ change                                                    │ where                              │ risk │ depends
 ───┼───────────────────────────────────────────────────────────┼────────────────────────────────────┼──────┼────────
 C1 │ per-frame MAD rejection BEFORE the σ-clip (un-biases the   │ RobustReductionLogicModule.reject… │ LOW  │ —
    │ mean even with today's warmup) — the immediate fidelity win│  + MeanSpectrumLogicModule         │ pure │
 C2 │ adaptive warmup: drain until K stable channelPeaks or cap; │ VideoThread (AE tail) + CapturePanel│ MED │ —
    │ retire fixed 1.8 s settle + drop-1                         │  (remove drop-1)                   │ rig  │
 C3 │ top-up burst: grab until N survive reject, cap N+margin    │ SpectralWorkflowEngine.__runBurst  │ MED  │ C1
    │ (guarantees N effective; clean fail at cap)               │                                    │      │
 C4 │ rig verify end-to-end                                     │ bench, live ELP                    │ —    │ C1-C3
 ───┴───────────────────────────────────────────────────────────┴────────────────────────────────────┴──────┴────────
 Order: C1 first (pure, safe, fixes the bias on its own) → C2 (root cause, fewer drops) → C3 (restore the count).
 C1 ⟂ C2 (independent); C3 needs C1's reject fn. C4 gates the whole.
```

> **AS BUILT — C1·C2·C3 IMPLEMENTED 2026-07-18 (unit + headless verified; C4 rig-verify pending Edwin's ELP).**
> - **C1** — `RobustReductionLogicModule.rejectDimFrames(stack) → keep-mask` (per-frame brightness = median across
>   bins; MAD-outlier reject, `DIM_FRAME_K=3`, `MIN_FRAMES_TO_REJECT=5`, plus a **relative scale floor**
>   `DIM_FRAME_SCALE_FLOOR=0.02` so a blatant dim frame can't survive a tight/identical clean cluster and the virtual
>   path keeps all). `MeanSpectrumLogicModule.meanSpectrum` applies it **before** `sigmaClippedMean`. Tests:
>   `test_capture_frame_rejection` — dim group dropped, clean/degenerate/too-few kept, never-reject-all, and the mean
>   stays on the clean cluster (~100, not the plain-mean ~94).
> - **C2** — `VideoThread.__settleUntilStable()` replaces the fixed final drain: drain `__SETTLE_CHUNK_MS` chunks and
>   measure `channelPeak` until `__SETTLE_STABLE_READS` consecutive reads are within `__SETTLE_TOLERANCE`, gated by
>   `__SETTLE_MIN_MS=1500` (past the latency plateau — avoids the §14.6 false-converge) and capped at
>   `__SETTLE_MAX_MS=4000`. The per-probe drain stays fixed (measuring mid-sweep must not adapt). `CapturePanel`'s
>   fixed 1-frame drop is retired. **Rig-only** to fully verify (camera timing).
> - **C3** — `SpectralWorkflowEngine.__runBurst` now GRABS UNTIL N frames survive `rejectDimFrames` (via
>   `__survivingFrameCount`), capped at `N + max(5, N//5)` accepted and a total-attempt cap (a wedged provider fails
>   cleanly). Test: 3 dim frames → burst tops up past N, ≥N survive. Existing burst tests unchanged (identical frames →
>   MAD≈0 + floor → all kept → exactly N).
> - **Pipeline unaffected on the virtual path** (identical frames → keep-all): pumpkin end-to-end, spectrum-processing,
>   wizard-offscreen all green (15).
>
> **C4 rig-verify (Edwin, live ELP):** re-shoot the reference — the gray band collapses onto the green mean (as the
> Sample already does); R does not sit systematically below a fixed-long-exposure control capture; and the effective
> frame count entering `sigmaClippedMean` equals N (log it). T = S/R then stable run-to-run.

> **AS BUILT — the residual reference-only band was AUTO WHITE-BALANCE, not the lamp (IMPLEMENTED 2026-07-19).**
> Rig retest of C1–C3: the below-*bias* was fixed (mean centered) but the reference stayed noisier than the sample,
> **and the lamp was constant/warm** — so it was not warmup. Root cause: `CaptureBackend.open` pinned only exposure +
> gain and **left auto-white-balance + backlight-compensation ON**; they re-converge after the AE exposure change, so
> the reference burst (right after the sweep) caught the transient while the settled sample did not. C2's `channelPeak`
> settle couldn't see it (it tracks the bright end; WB/backlight settle separately). **Fix (rig-confirmed: reference
> and sample now look the same):** freeze them at capture. **Mode-split** so calibration is untouched:
> - `CaptureBackend.open(deviceId, exposure, whiteBalanceKelvin=None)` — `None` → **auto-WB** (calibration keys on it,
>   §13/§14.6; set explicitly so a sticky manual WB can't leak in); a value → `AUTO_WB=0` then `WB_TEMPERATURE=value`
>   (+ read-back) + backlight off.
> - `VideoThread.WHITE_BALANCE_KELVIN = None` (default → all **calibration** threads stay on auto-WB, unchanged);
>   `DevCaptureVideoThread.WHITE_BALANCE_KELVIN = 6500` (the **measurement** path → fixed to the **6500 K lamp**, so WB
>   renders it neutrally, cancels in T = S/R, and removes a degree of freedom). TODO: seed per-lamp in
>   `SpectrometerSensorUtil` alongside VID/PID + exposure.
> - ⚠ **Calibration must be re-verified on the rig with the split** (calibration is back on auto-WB, so it should match
>   the historical ~0.6 nm PASS — confirm).
>
> **AS BUILT — fix (2) full-frame settle metric IMPLEMENTED 2026-07-19 (Edwin: multi-camera use makes it worth it).**
> `VideoThread.__settleUntilStable` now keys on `AutoExposureLogicModule.frameBrightness` (the MEAN of the brightest
> channel over the whole frame) with a **relative** tolerance (`__SETTLE_TOLERANCE_FRAC = 0.01`), instead of
> `channelPeak`. Rationale: channelPeak is the p99.9 PEAK — it saturates/plateaus at the AE target while the mid/dim
> regions still ramp, so the settle could read "stable" early; a frame MEAN stays linear and moves until the whole
> frame settles, and it makes no assumption that the ramp is uniform (matters across different cameras). `channelPeak`
> is untouched (still the sweep-search metric). Unit tests cover `frameBrightness`; **rig-confirmed on the measurement
> path 2026-07-19 (Edwin: works).** Calibration WB-split still awaits a rig calibration run.

### 14.9 Per-camera exposure range — the hardcoded `[1, 500]` (OPEN — **POSTPONED on the roadmap**, flagged 2026-07-19)

> Tracked in [`spectracs-docs/ROADMAP.md`](../../spectracs-docs/ROADMAP.md) → "Per-camera exposure range". Deferred by
> Edwin 2026-07-19: not urgent (the ELP works; the ~110–120 spectrum peak is mostly the deliberate no-clip AE metric,
> not the cap), but a real gap once multiple cameras are in use.

Investigating "why does the measured spectrum peak at ~110–120, not near 255?" surfaced a separate, real gap. Two
things cap the spectrum level:

1. **The AE metric (by design, keep):** AE targets `channelPeak` (p99.9 of the brightest CHANNEL) at **245** so *no
   channel clips*. The displayed spectrum is `qGray` (a luminance blend) after a robust per-column reduction, both of
   which sit **below** the max-channel peak — so at the brightest non-clipping exposure, qGray lands ~110–120. This is
   the no-clip ↔ dynamic-range trade-off; it is **correct** (unbiased for T = S/R) and should stay. Do NOT retarget AE
   to qGray (a channel would clip → breaks the colour-anchored calibration §13/§14.6 and distorts the peak).
   **⚠ REVISITED by §15:** the *spectrum reduction itself* switches `qGray → max-channel` (blue SNR/headroom) —
   which **aligns the spectrum with the max-channel AE target** (spectrum peak rises toward 245). AE is NOT
   retargeted; both reductions are unbiased. So this item's "~110–120, keep" no longer holds once §15 lands.
2. **🔴 The exposure search range is HARDCODED and NOT per-camera** (`CapturePanel.__EXPOSURE_MIN = 1`,
   `__EXPOSURE_MAX = 500`). The search itself is fine (a ladder + bisection refine over the range, not a fixed value
   set — `AutoExposureLogicModule.findExposure`). But V4L2 `exposure_time_absolute` **units differ wildly between
   cameras** (one camera's 500 ≈ another's 50 or 5000), and `cap.set(CAP_PROP_EXPOSURE, x)` **clamps to the camera's
   own min/max/step**. So a fixed `[1, 500]`:
   - can be **too low** on a camera whose useful range extends higher → AE tops out dark, the whole spectrum dim;
   - can be **too coarse/misaligned** on a camera with a different unit scale.
   With **multiple cameras in use (Edwin)** this is a genuine correctness/UX gap, the exposure sibling of the WB-per-lamp
   and settle-metric items.

**Planned fix (deferred, impl on explicit request):**
- **Read the camera's actual exposure range** at open — `CaptureBackend` exposes `cap.get(CAP_PROP_EXPOSURE)` min/max
  where the driver provides them (V4L2 does) — and drive the AE ladder over *that*, not a constant. Where the driver
  won't report a range, fall back to a **per-sensor seed** in `SpectrometerSensorUtil` (alongside VID/PID, exposure
  default, and the new WB-Kelvin — a natural home for all per-camera capture constants).
- **Diagnostic to disambiguate first (cheap):** log the exposure AE lands on. Near `__EXPOSURE_MAX` (500) ⇒ the cap is
  the limit (raise / per-camera it); well below ⇒ it is the no-clip metric (item 1), leave it.
- **Secondary (only if the captured image shows a bright region OUTSIDE the spectrum band):** measure the AE metric over
  the **ROI band** rather than the whole frame, so stray bright pixels can't starve the spectrum's exposure.

---

## 15. Radiometric intensity reduction — `qGray` → max-channel (the "gray value" fix)

> **Status: ✅ IMPLEMENTED + RIG-VERIFIED 2026-07-20 (G1–G6).** Edwin's rig pass confirmed G4 (calibration ~0.6 nm
> holds under the scale-invariant `prominence=0.01·peak`, green anchor + blue Hg 436 detected), G4b (extremes floor
> sane) and G6 (blue healthy, less dilution, the Yuji lamp reads full-spectrum). HIGHEST PRIORITY,
> the PREREQUISITE ahead of the Capability-Proof milestone (V) — every downstream metric reads this reduction.
> Done: G1 `SpectralColorUtil.toGrayMaximum/Luminance/Mean` (+ numpy siblings) + unit test (`test_gray_reduction.py`,
> 6 tests); G2 both real-capture creators (`ImageSpectrumAcquisitionLogicModule` :58 measurement/:127 robust/:132
> fallback) route through `toGrayMaximum`; G3 virtual encoder verified no-op (Grayscale8 → `test_virtual_device_
> image_roundtrip` green); G4 calibration made scale-invariant (`WavelengthLineDetectionLogicModule`:
> `prominence = 0.01·peak`, was absolute `1`); G5 display colorizers aligned. Full suite **198 passed, no
> regression.** **Not committed.** Rig-pending: G4 (calibration ~0.6 nm PASS + green-anchor holds on the real CFL),
> G4b (blue/red floor sane), G6 (blue healthy, less dilution). Settled with Edwin 2026-07-20.

### 15.1 The finding

The per-column spectrum intensity is formed with Qt's **photometric `qGray = (11·R + 16·G + 5·B)/32`** — blue
weight **5/32 ≈ 0.16** vs green **16/32 = 0.50**, so **blue reads ~3× low for the same light**. Evidence
(2026-07-20 rig, screenshots): the reference trace sits **~25 in the blue vs a ~115 green plateau** (≈1/5), yet
the **ROI raster image shows a vivid, bright blue band** — the blue *channel* is strong; the Yuji SunWave 6500 K +
camera capture blue fine. **The suppression is the weighting, not the LED or the sensor QE.** (The steep 465→480
rise in the trace is the Bayer green channel switching on — a reduction artifact, not a lamp edge.)

### 15.2 Why it (mostly) doesn't BIAS — but still matters

A **homogeneous** reduction (`qGray`, `max`, `mean`, `sum`) **cancels in `T = S/R` and `A = −log₁₀(S/R)`**: at each
column the reference and sample are the *same colour* (same λ), the sample just dimmer, so the weighting scales
both equally. ⇒ **the reduction does not change `T`, `A`, or any colour value** — consistent with §14.9 item 1
(the low `qGray` peak was unbiased). What `qGray` *does* cost:

- **Blue SNR + dilution headroom.** It keeps only 5/32 of the blue signal *and* adds read-noise from the R/G
  channels that see ~0 blue light → blue drowns in noise at lower absorbance → **forces heavy dilution.** A
  radiometric read gives ~3× blue signal with no empty-channel noise → **dilute less**, and an honest plot.
- The **blue is where it matters most**: the intrinsic *absorbed* colour and the Soret peak-ratio flank both live
  there ([`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) §0, [`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) §1b).

⇒ **Not a correctness fix — a fidelity/headroom fix.** But it is a **prerequisite** because it eases the dilution
constraint the whole Capability-Proof series (V) depends on.

### 15.3 Decision — max-channel, in a `ColorGrayUtil` (Edwin)

- **Reduction = `max(r, g, b)`** — reads the channel that actually saw that wavelength: largest blue, no
  empty-channel noise; it's already what the **ROI-finder** uses. It is positively homogeneous
  (`max(k·x) = k·max(x)`), so it **still cancels in `T`/`A`** → no metric bias.
- **Centralize into the EXISTING `SpectralColorUtil`** (Edwin — reuse, don't invent) —
  `spectracsPy-core/.../spectral/util/SpectralColorUtil.py`, a Qt-free `Singleton` in **core** that already takes
  a colour and reduces channels (`channelDominance(color, kind)` does `r,g,b = color.red(),…`). Add **three
  `toGray*()` variants** so "the gray of a pixel" lives in ONE place instead of inline across client code:
  - `toGrayMaximum()` → `max(r,g,b)` — **the new default**
  - `toGrayLuminance()` → `(11r+16g+5b)/32` — today's photometric (kept for reference / the eureka bench)
  - `toGrayMean()` → `(r+g+b)/3` — unweighted
  - *Nuance:* the robust per-column loop is numpy-vectorized, so also add array siblings
    (`toGrayMaximumArray(r,g,b)` …) in the same util — one source of truth, two entry shapes (both fine in core).
  Being in core, both the app-side reduction AND the virtual-device encoder import the same definition.
- **WB stays 6500 K** — the blue is already captured (raster proves it); this just *reads* it. Boosting blue via WB
  would risk clipping the pump and cancels in the ratio anyway.

### 15.4 Side-effect map — the `qGray` usages, categorized

The grep looks alarming; categorized it is small. Only categories **1–2 are mandatory changes**; 3 is
re-verification (and improves); 4–5 are optional/none.

| # | Category | Sites | Effect of the switch |
|---|---|---|---|
| **1** | **CREATES the spectrum value** (the reduction — *the* change) | `ImageSpectrumAcquisitionLogicModule` line **127** (measurement, robust) + **58** (calibration single-row) | route both through `ColorGrayUtil.toGrayMaximum`. **Tiny:** line 128 **already computes `maxChannel`** (for the saturation mask) — measurement branch is a one-token swap |
| **2** | **MUST MIRROR the reduction** (encoder) | `SpectrumToVirtualImageUtil` (virtual device encodes so `qGray(pixel)==value`) | **change together** — encode so `max(pixel)==value`, else virtual captures decode wrong |
| **3** | **CONSUMES the spectrum** — behaviour shifts (for the better) | `WavelengthLineDetectionLogicModule` (calibration line-detect), `SpectralWorkflowEngine:165` (`qGray>20` content threshold) | **re-verify / re-tune**, don't rewrite. Blue rises → calibration lines clearer; re-tune the `>20` constant |
| **4** | **DISPLAY only** (cosmetic) | `SpectralImageLogicModule:31,48` (hue-mapped raster render) | **optional** align; no measurement effect |
| **5** | **NOT affected** (already channel-based / agnostic) | `SpectrometerRegionOfInterestLogicModule` (max), `AutoExposureLogicModule` (max channel), `RobustReductionLogicModule` (reduces whatever array it's handed) | **nothing** |

### 15.5 Calibration — clarifying the "already uses max / might be affected" tension

Two different calibration-adjacent modules use **different** reductions:
- **`SpectrometerRegionOfInterestLogicModule`** (finds the ROI **x-bounds**) → **already `max`** → *unaffected*.
- **`WavelengthLineDetectionLogicModule`** (finds the **pixel position of Hg lines** → pixel→nm) reads the
  **`qGray` calibration spectrum** (§15.4 site 58) → *affected* — and **helped**: the blue **Hg 436 nm** line,
  currently crushed by 5/32, **rises** under `max`, easier to detect. The hue constraint (`colorsByPixelIndices`,
  §13) is unchanged (raw `QColor`s). **Re-verify the ~0.6 nm calibration still passes.**

### 15.6 Reconciliation with §14.9

§14.9 item 1 (correctly) said the `qGray` spectrum peaking ~110–120 is **unbiased for `T=S/R`** and warned *"do NOT
retarget AE to `qGray`."* This section does **not** violate that: **AE keeps targeting the max CHANNEL** (245,
no-clip). We change the **spectrum reduction** to max — **aligning the spectrum with what AE already targets**, so
the spectrum peak rises toward the channel peak and blue recovers ~3×. Both `qGray` and `max` are unbiased; we pick
`max` for blue SNR/headroom. (Annotate §14.9 item 1 → "revisited by §15".)

### 15.7 Implementation phases  *(DESIGN — implement on explicit request only)*

```
+----+-------------------------------------------+----------------------------------+-----------------------------------+---------+
| Ph | What                                      | New / Touched                    | Gate                              | Risk    |
+----+-------------------------------------------+----------------------------------+-----------------------------------+---------+
| G1 | SpectralColorUtil: add toGrayMaximum/      | TOUCH SpectralColorUtil (existing | Unit: the 3 reductions match hand-| LOW     |
|    | Luminance/Mean (scalar, take colour) +    | core util); + numpy siblings     | computed on sample pixels. No     |         |
|    | toGray*Array(r,g,b) numpy siblings        | toGray*Array                     | behaviour change yet.             |         |
| G2 | Route the 2 REAL-capture creators through  | TOUCH ImageSpectrumAcquisition    | Real spectrum blue lifts ~3-6x,   | LOW-MED |
|    | toGrayMaximum. Measurement (:127) reuses   | :127 (use already-computed       | peak rises ~115->~245; T/A a      |         |
|    | the already-computed maxChannel; calib     | maxChannel) + :58 (pixelColor->  | virtual round-trip still matches  |         |
|    | (:58) reads pixelColor (line 60 already).  | toGrayMaximum)                   | (unchanged). No metric change.    |         |
| G3 | VERIFY the virtual encoder is a NO-OP       | SpectrumToVirtualImageUtil is    | test_virtual_device_image_        | LOW     |
|    | (Grayscale8 -> gray: max==qGray). NO code  | Format_Grayscale8 -> gray pixels | roundtrip stays GREEN; add an     | (was MED|
|    | change; assert the invariant in a comment. | round-trip identically           | assert/comment on the invariant.  | -> LOW) |
| G4 | CALIBRATION scale-invariance (the real     | WavelengthLineDetection       | On rig: green anchor holds, Eu-red   | MED     |
|    | risk, §15.9/9): NORMALIZE the calib         | (normalize + prominence)      | not hijacked, blue Hg436 detected,   | (rig)   |
|    | spectrum before find_peaks OR re-tune the   | + SpectralWorkflowEngine:165  | ~0.6nm PASS. Positions stable => no  |         |
|    | ABSOLUTE prominence=1 to the new scale;     | (>20 gate, opt bump)          | DB migration.                        |         |
|    | >20 has-signal gate opt bump                |                               |                                      |         |
| G4b| Verify the deep-blue/far-red noise floor    | inspection on rig traces      | Extremes floor sane; Tukey biweight  | LOW-MED |
|    | isn't inflated by max's upward bias (§15.9/10)|                             | absorbs the max-of-noise spikes.     |         |
| G5 | OPTIONAL: align the display render         | TOUCH SpectralImageLogicModule    | Raster/plot read consistently.    | LOW     |
| G6 | Rig-verify end-to-end                      | measurement                      | Blue healthy; less dilution;      | -       |
|    |                                           |                                  | calibration + metrics intact.     |         |
+----+-------------------------------------------+----------------------------------+-----------------------------------+---------+
Order: G1 -> G2 -> G3(verify) -> G4(rig); G5 optional; G6 last. All plugins/metrics inherit it for free.
```

### 15.8 Cross-references
- §14.9 (AE targets max-channel — this aligns the spectrum to it) · §13 (colour-anchored line detection — hue
  constraint unchanged) · §5 (dark-frame, the additive sibling) · §6 (robust reduction — operates on whatever
  gray the caller forms).
- [`SPEC_capability_proof.md`](SPEC_capability_proof.md) — milestone **V depends on this** (§10.3 confounder,
  camera reduction). · [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) §0 — why blue carries the intrinsic colour.

### 15.9 Implementation rubber-duck (risks & de-risks, vs as-is code, 2026-07-20)

The headline: **the entire behavioural change is confined to REAL camera captures** (colour Bayer pixels). Virtual
captures, the metrics, stored data, and colour VALUES are all untouched. Why:

1. **Virtual encoder is a NO-OP — the big de-risk.** `SpectrumToVirtualImageUtil` writes `QImage.Format_Grayscale8`
   (neutral gray, R=G=B=v). For a gray pixel `max(v,v,v) == qGray(v,v,v) == v`, so every virtual capture (and every
   baked asset, and `test_virtual_device_image_roundtrip`) **decodes identically under max**. G3 needs no code — just
   assert the invariant. *(Side note: the virtual device therefore won't SHOW the blue-recovery — its baked assets
   are already qGray-derived; only real captures benefit. Re-baking from max captures is optional, later.)*
2. **T/A and every metric are unchanged even for REAL captures.** `max` is positively homogeneous, and at one column
   reference & sample are the same colour (sample dimmer), so `max` cancels in `T=S/R`/`A` exactly as `qGray` did.
   ⇒ no metric regression; the visible change is only the **raw R/S plot + blue SNR/headroom**.
3. **No stored-data migration.** Calibration profiles store ROI + the pixel→nm cubic — **intensity-independent**.
   `max` changes line *heights*, not line *positions*, so existing calibrations stay valid and the nm map is unchanged.
4. **Spectrum peak rises ~115 → ~245** (aligns with the max-channel AE target, §14.9/§15.6). Verify nothing hardcodes
   ~115 (expected: only plot autoscale + the *relative* transmission floor, both fine).
5. **`>20` ROI-has-signal gate (`SpectralWorkflowEngine:165`)** — a coarse "is there any signal here" sanity check;
   `max ≥ qGray`, so it errs toward *finding* signal (safe). Optional small bump; low-risk. (Uses `image.pixel()`
   int — switch to `pixelColor()` if routed through the util, or leave: on a real frame the raw compare is fine.)
6. **Calibration line-detection (rig re-verify, the one MED-risk).** Real CFL, colour pixels: `max` lifts the blue
   **Hg 436** line (currently crushed 5/32) → *more* detectable (good). The §13 colour constraints
   (`channelDominance`/`hueSimilarity`, raw `QColor`s) are unchanged. Re-verify: green anchor still dominates, the
   ~0.6 nm fit still passes, no spurious blue peak hijacks the anchor. Can't unit-test (needs the rig).
7. **Two entry shapes, one formula.** Measurement path is numpy (`toGrayMaximumArray`, reusing the `maxChannel`
   line 128 already computes for the saturation mask — a one-token swap); calibration/threshold/display are scalar
   (`toGrayMaximum(color)`). Both live in `SpectralColorUtil` → single source of truth.
8. **Bonus:** keeping `toGrayLuminance`/`toGrayMean` in the util lets the Capability-Proof eureka bench compare all
   three reductions on the same capture — the reduction becomes a knob, not a hardcode.

**Second pass (2026-07-20, "be safe") — new findings:**

9. **⭐ The sharpest risk — calibration line-detection uses an ABSOLUTE `prominence=1`.**
   `WavelengthLineDetectionLogicModule` runs `find_peaks(intensities, …, prominence=1)` on the **raw, un-normalized**
   spectrum, and the anchoring is **prominence-RANK-sensitive** (header: *"out-prominences it → mislabels red as
   green"*; Eu-red = "most-prominent peak right of green"). `max` lifts amplitudes 2–6× → `prominence=1` is
   relatively looser → a lifted spurious bump could admit a fake peak or **flip the anchor**. **Fix: normalize the
   calibration spectrum before `find_peaks` (scale-invariant — the robust option, also immunizes against exposure)
   OR re-tune `prominence` to the new scale.** Rig-verify either way. This — not the reduction swap — is the real work of G4.
10. **`max` is an UPWARD-biased estimator** (`max ≥ any channel`): at low-signal extremes (deep-blue ~430, far-red
   >640) it can inflate the noise floor. The Tukey-biweight over rows absorbs the max-of-noise spikes, but verify the
   extremes (G4b). *(A bias-free alternative — the per-λ dominant channel — is heavier; keep `max` + this check.)*
11. **DE-RISK confirmed: no raw-spectrum colour consumer.** Every `spectrumToColor` caller passes **transmission**
   (`PlaygroundViewModule:151`) or a synthetic SPD — none a raw reference/sample spectrum. So the oil colour is
   **fully invariant** to the reduction (grep-verified, not assumed).
12. **Swap-completeness checklist:** route the measurement reduction **and** its all-clipped fallback (`:132`) through
   the util (`maxChannel` — the mask `:129` already uses it, so reduction+mask become consistent); the calibration
   branch (`:58`) reads `pixelColor()` (QColor) not `pixel()` (int) to feed the scalar `toGrayMaximum`. **Do not**
   claim linearity: `max` recovers blue *signal* but values remain gamma-encoded (C1 is the separate, postponed fix).

---

## 16. Camera sensor SELF-HEATING — reference-shape drift over minutes  *(RIG-DIAGNOSED 2026-07-20)*

**Symptom.** Same oil measured twice gives an **absorbed-colour hue that drifts ~5°** run-to-run while the
*perceived* colour is stable. Root: the **reference SPD shape** tilts run-to-run (red ↑ vs green/blue by ~1%),
amplified into the absorbed colour by `A = −log₁₀(S/R)` in the low-absorbance regime (pumpkin oil T≈0.9 → A≈0.02–0.05;
a 1% transmission change → ~19% change in the tiny green `A`). See `SPEC_capability_proof.md §10.5`.

### 16.1 Diagnosis chain (what it is NOT, then what it is)

Instrumented capture with two diagnostics (both `spectracsPy` app + `spectracsPy-core`):
- `CAPTURE-SETTINGS` line per capture (`CapturePanel.__logCameraSettings` → `VideoThread`/`CaptureBackend.readCameraSettings`): landed exposure + live V4L2 WB/gain/backlight.
- `CaptureDiagnosticsLogger` (`SPECTRACS_LOG_SPECTRA=<dir>`): per-frame spectra + the C1 dim-frame keep-mask + brightness + reduced mean, hooked into the Qt-free `SpectralWorkflowEngine.captureAcquisitionStep`. Driven headless by `diagnoseCapture.py` / `runDiagnose.sh` (real ELP + local server; masterUserExakta calibration).

Ruled out, in order:
1. **AE / auto-WB drift** — `CAPTURE-SETTINGS` identical across runs (exposure=90, WB=6500, gain=0, all pinned).
2. **Evaporation of the blank** — the drift **reverses after an idle gap** (a monotonic-loss process can't reset up); and it's hours-scale, not minutes (Edwin).
3. **Lamp thermal / warm-up** — the Yuji lamp is external, always on, already warm; it doesn't cool in a 13-min idle. But the drift **reset** across that idle → the thing that cooled was the **camera** (released each session).
4. **Sensor dark current** — a prior dark-frame test was clean. But that tests the *additive offset*; this is a *multiplicative per-channel responsivity/QE* drift — a different mechanism the dark test can't see.

**Conclusion: camera sensor SELF-HEATING** — as the die warms from operation, per-channel QE drifts (red most temperature-sensitive), tilting the channel balance. Overall brightness stays pinned (~143, exposure holds it); only the *shape* moves.

### 16.2 Quantified — the warm-up curve

`diagnoseCapture.py --runs 15 --interval 45 --ae-once --frames 40` (fixed exposure, cold start) → `red/green` vs
time is a **clean single exponential** `A − B·e^(−t/τ)`:

| quantity | value |
|---|---|
| time constant τ | **171 s (2.9 min)** |
| total shape change | **1.68%** (red/green 0.682 → 0.694) |
| 90% / 95% settled | 6.6 min / 8.5 min |
| within measurement noise of equilibrium | **~9 min** |

Curve: `spectracs-references/tmp/sensor_warmup_curve.png`.

### 16.3 The camera lifecycle makes it WORSE (code-confirmed)

The camera does **NOT** run for the app's lifetime. It streams **only while the ACQUISITION step is the active
view**: `WizardViewModule.__renderRealAcquisition()` calls `CapturePanel.startStream()` (opens the camera **cold**);
`stopStream()` + `backend.release()` fire on navigating away (to Processing/Evaluation), `hideEvent`, or a plugin
switch. So **every measurement run cold-starts the camera**, captures **R first at the coldest, steepest part of the
curve**, then S ~30–60 s later while it warms fastest → the **R→S gain drift is maximised**, and it **resets every
run**. Because the sensor gain cancels in `S/R` only when R and S share a temperature, this residual is exactly what
tilts `A`; run-to-run variation in the cold-start state varies it → the observed hue drift.

### 16.4 Fixes (options — DESIGN, implement on explicit request)

Operational (no code): stay on acquisition streaming ~10 min before capturing R; keep the R→S gap minimal.
App-side (the real fix, ranked):
1. **Warm-up hold** — on entering acquisition, stream until `red/green` (or the reference shape) stabilises, or a fixed ~10 min, before enabling the capture button. Deterministic; the diagnostic already measures the stabilisation.
2. **Keep the camera open/warm across phases** — don't `release()` on nav to Processing/Evaluation (only on plugin switch / app exit), so the sensor stays at equilibrium between R and S and between runs.
3. **Minimise R→S** — capture S as soon after R as the protocol allows.

⚠ Prerequisite honesty: confirm the mechanism accounts for the *full* 5° with a **warm re-run** (one oil × two runs after 10-min warm-up, R→S tight) — if the hue drift collapses to ~0–1°, self-heating was the whole story (`SPEC_capability_proof.md §10.5`). NOT yet done. Also: the intermittent gray-frame outliers (§14.8) are still un-reproduced (0 rejected across ~1500 diagnostic frames) — orthogonal to this shape drift.

### 16.5 Tooling shipped (uncommitted at time of writing)

`CaptureDiagnosticsLogger` (core), the `CAPTURE-SETTINGS` read-back (`CaptureBackend.readCameraSettings` / `VideoThread` / `CapturePanel`), the engine logging hook, `diagnoseCapture.py` (+ `--runs/--interval/--ae-once/--frames`), `runDiagnose.sh`, and `tests/test_capture_diagnostics_logger.py`.

### 16.6 The warm-keeper — W1–W4 IMPLEMENTED 2026-07-20 (Phase 1: lease; single-owner subscriber model POSTPONED)

**Status:** W1–W4 built (headless-green: `tests/test_camera_lease.py` + compile + import-cycle-free); **W5 = rig
validation pending** (handoffs without EBUSY across phase-nav / calibration / dev-capture; then the warm oil re-run
→ does the 5° tilt collapse?). W6 (red/green guard) postponed. Files: `logic/application/video/CameraLease.py`,
`CameraWarmupVideoThread.py`, `CameraWarmupService.py`; `VideoThread.py` (run() restructure + `_isWarmKeeper`);
`view/main/MainStatusBarViewModule.py` (amber warming state + presence-driven start/stop).


**Decision (Edwin 2026-07-20):** keep the sensor warm by **streaming continuously**. The full single-owner
"one thread, many frame-subscribers" `CameraService` is the clean *end-state* but is **POSTPONED** (it forces the
in-thread-processing consumers — wavelength-calibration + spectral-job — onto a subscriber model, touches
master-only calibration, and needs multi-subscriber frame delivery with the segfault-copy history + producer/
consumer threading + WB/AE arbitration). Phase 1 is the **lease warm-keeper**: lower risk, ships the thermal fix,
and is the *seed* of the eventual `CameraService`.

**Mechanism.** All five capture consumers subclass `VideoThread` and open via `getCaptureBackend().open()` in
`VideoThread.run()` → **one enforcement point**:
- `CameraLease` (singleton): `acquire()`/`release()` with a consumer count. First `acquire()` → warm-keeper
  `pause()`; last `release()` → warm-keeper `resume()`. Holds `warmSince`.
- `VideoThread.run()`: a real, non-virtual, **non-warm-keeper** thread `acquire`s before `open()` and `release`s
  after `release()` (in `finally`) — auto-coordinates measurement / both calibration threads / dev-capture /
  spectral-job with **no change to their internals**.
- `CameraWarmupService` (singleton): owns the warm-keeper thread, streams the real device during idle, flagged so
  `VideoThread.run()` skips the lease for it (idle-holder, not a consumer).

**Second-pass rubber-duck corrections (2026-07-20):**
- **The warm-keeper is a READ-AND-DISCARD thread, NOT a `DevCaptureVideoThread`.** `DevCaptureVideoThread.afterCapture`
  emits a frame then BLOCKS in `__waitForRender(event)` until a subscriber `event.set()`s — with no subscriber the
  warm-keeper would stall after one frame (no continuous readout). The **base `VideoThread`** already reads+discards
  (its `afterCapture` only advances the index, no emit) and with `frameCount=0` never stops → use a tiny
  `CameraWarmupVideoThread(VideoThread)` with `_isWarmKeeper`. Bonus: no signals → cross-thread `stop()/wait()` is
  affinity-safe.
- **`VideoThread.run()` needs a guaranteed-release `finally`.** Today `backend.release()` is at the END of `run()`
  with no `finally`; adding `lease.acquire()` before `open()` without one means a mid-loop exception holds the lease
  FOREVER (camera wedged until restart). W2 = wrap the REAL path: `acquire → try{ open, warmup, loop } finally{
  release backend; release lease }` (the loop serves both virtual+real, so wrap only the real path — a careful
  restructure, not a two-liner).
- **The lease AVOIDS WB/exposure arbitration** — each consumer opens the device fresh with its own settings
  (calibration auto-WB, measurement 6500K+AE), so there is no shared-mode state machine (the hardest part of the
  single-owner model simply doesn't exist here). Reconfirms Phase 1 = lease.

**Hard parts / risks:**
1. **`pause()` releases BEFORE the consumer opens — synchronously** (`stop()` + bounded `wait()` for `backend.release()`,
   then return) so the two never both hold `/dev/video0` (EBUSY). Reuse the `_STUCK_CAPTURE_THREADS` bounded-wait +
   park pattern so a wedged cv2 read can't deadlock the handoff. **#1 risk.** Note C-D: the first consumer after
   login can wait a few seconds on the warm-keeper's multi-second 2592×1944 `open()` (blocking cv2, ignores the stop
   flag) — acceptable/one-time. Lease count needs a mutex; `finally` matches release to acquire.
2. **`warmSince` persists across ~1 s handoffs** (warm as long as anyone streams); resets only on a real gap
   (device unplugged / nothing streaming > ~30 s cooldown). All consumers stream continuously while they hold it.
3. **Start post device-resolution** (`installFromSession`, `LoginViewModule`), real sensor only (virtual/no-camera skip).
4. **Indicator:** `MainStatusBarViewModule` gains an **amber warming** state while `present and now−warmSince < 9 min`
   (data: τ≈2.9 min, settles ~9 min, §16.2), else green "connected & warm". Reuse the presence poll.
5. **Accepted:** continuous 2592×1944 streaming all session (USB/CPU — rig-validate); `diagnoseCapture.py` conflicts
   with the running app (document "stop the app first").

**Phases (DESIGN — implement on explicit request):**
```
+----+------------------------------------------------+------------------------------------------+
| Ph | What                                           | Files — New·Touch                        |
+----+------------------------------------------------+------------------------------------------+
| W1 | CameraLease singleton (mutex count + warmSince) | NEW CameraLease + CameraWarmupService +  |
|    | + CameraWarmupService (idle stream, pause=stop+ | CameraWarmupVideoThread (READ-DISCARD,   |
|    | bounded-wait, resume) + CameraWarmupVideoThread | base VideoThread, no emit — NOT DevCap)  |
|    | (read-discard base thread, _isWarmKeeper)       |                                          |
| W2 | VideoThread.run: acquire -> try{open,loop}      | TOUCH VideoThread.py (careful run()      |
|    | finally{release backend; release lease}. warm-  | restructure — guaranteed-release finally)|
|    | keeper + virtual exempt. #1 = release-before-open|                                         |
| W3 | Start hook post device-resolution (real sensor | TOUCH LoginViewModule (+ MainContainer/  |
|    | only); stop on logout/disconnect               | bench install points)                    |
| W4 | Indicator: amber "warming up (N min)" < 9 min, | TOUCH MainStatusBarViewModule            |
|    | else green "connected & warm"                  |                                          |
| W5 | Rig validation: warm-keeper survives phase     | (rig)                                    |
|    | nav / calibration / dev-capture without EBUSY; |                                          |
|    | warm oil re-run → does the 5° tilt collapse?   |                                          |
+----+------------------------------------------------+------------------------------------------+
W6 (POSTPONED): red/green stability guard at measurement time (item c). Single-owner CameraService: later.
```

### 16.7 Field evidence — the drift caught a dilution pair red-handed *(2026-07-27, measured)*

Edwin measured the same oil at two dilutions five minutes apart — `NowSteirerkraftA` (2 drops in 8 ml, 00:03)
and `NowSteirerkraftB` (2 drops in 6 ml, 00:08) — and the pigment ratio **diverged by 48 %** (3.739 vs 5.547),
where it should be dilution-INVARIANT. Replay (`diagnostics/gamma_dilution_diverge{,2}.py`) puts it on §16:

**The samples agree; the blanks do not.** Peak-normalized, the two SAMPLE spectra differ **only in the Soret
band** (B/A = 0.817 there, 0.99–1.04 in every other band) — exactly what a higher concentration does, and
nothing else. The two REFERENCE spectra differ **everywhere above ~500 nm**, as a smooth tilt:

| band | 440–460 | 480–500 | 520–540 | 560–580 | 600–620 | 620–640 |
|---|---|---|---|---|---|---|
| reference B/A (peak-normalized) | 1.010 | 0.991 | 0.961 | **0.930** | 0.950 | 0.928 |

**Cross-swap proves it.** Recomputing each sample against the *other* run's reference moves the ratio by
20–28 % — more than half the total divergence, from the blank alone:

| | A sample | B sample |
|---|---|---|
| **with its own reference** | 3.739 | 5.547 |
| **with the other reference** | 4.786 (+28 %) | 4.372 (−21 %) |

**Why a 7 % blank error wrecks a ratio.** `A_Q ≈ 0.15` at this dilution. A relative reference error δ moves
absorbance by `0.434·δ`, i.e. **2.9·δ relative on the denominator** — 7 % in, ~20 % out. The same δ on the
Soret band (`A ≈ 0.7`) costs only 4 %. **The ratio's dilution-invariance assumes both bands carry real signal;
here the denominator is mostly instrument drift.** (This is also why the 32-run proof held at SD ≈ 4 %: those
runs were captured back-to-back in one thermal state.)

**Not §16's sensor self-heating — but the culprit is NOT yet pinned** *(refined twice on 2026-07-27, after Edwin
pushed back on both the camera AND the lamp: "both had been running for minutes")*. What the data says
unambiguously, from the per-channel replay of the embedded frames (`diagnostics/gamma_reference_valley.py`):

| whole-frame channel level | run A | run B | B/A |
|---|---|---|---|
| **BLUE** (sees the InGaN **pump**) | 64.61 DN | 63.72 DN | **0.986** |
| **GREEN** (sees the **phosphor**) | 107.67 DN | 104.57 DN | **0.971** |
| **RED** (sees the **phosphor**) | 40.29 DN | 38.75 DN | **0.962** |

The reference peak sits at **472.7 nm — the pump** — and **phosphor/pump fell 5.04 %** (0.7353 → 0.6982) while
the pump held. So the two phosphor-fed channels fell together and the pump-fed channel did not.

**Two mechanisms produce exactly that signature, and the spectrum alone cannot separate them:**
1. **Lamp** — white-LED phosphor thermal quenching (conversion efficiency drops as the junction heats; the blue
   pump barely moves). Weak corroboration: the pump peak moved 472.7 → 473.3 nm, the direction InGaN shifts when
   it gets *hotter*. Against it: Edwin reports the lamp had been on for minutes.
2. **Camera** — a white-balance / channel-gain shift (R and G gains down relative to B) is *indistinguishable*
   from the outside. `DevCaptureVideoThread` pins WB at 6500 K with `AUTO_WB=0`, so this should not happen — but
   "should not" is not evidence.

#### 16.7.1 MEASURED — the drift time-course, 12 min on the rig *(2026-07-27, `diagnostics/reference_drift_probe.py`)*

Rather than keep arguing lamp-vs-camera from two captures, the time course was measured: exposure picked once
(landed at 64; 128 and 256 clip) then **pinned**, WB 6500 K, 21 samples over 12 minutes, camera freshly opened
with the lamp already warm. Log archived at `spectracs-references/probe/drift_20260727_0124.log`.

| | result |
|---|---|
| **camera settings across all 21 samples** | `exp=64 wb=6500 autoWb=0 gain=0` — **never moved** |
| **phosphor/pump** | 0.6437 → 0.6543, **+1.65 %**, monotone and clearly **asymptoting** (+0.9 % by 2½ min, +1.5 % by 7 min, flat after ~10) |
| pump level | −0.77 % — the blue **falls** while the phosphor **rises** |
| frame spread | 0–1.8 % (no dim-frame group; the burst is clean at a pinned exposure) |

**Three conclusions, and the middle one kills my own hypothesis:**

1. **The white-balance/gain bug is ruled out.** `wb`, `autoWb` and `gain` are constant to the digit for 12
   minutes. Whatever moves the spectrum, it is not the camera's controls.
2. **⚠ The sign is OPPOSITE to Edwin's A/B event.** Warming this rig makes phosphor/pump **rise** 1.65 %; between
   his two blanks it **fell** 5.04 %. A lamp phosphor droop (§16.7's hypothesis 1) predicts a *fall*, so it is not
   what this run shows — this is blue falling relative to green+red, which is **§16.2's documented sensor
   self-heating signature** (red ↑ vs green/blue, ~1 %), seen cleanly because the camera was cold-opened while the
   lamp was already warm. **So the A/B event is neither warm-up mechanism: wrong sign, and 3× too large.**
3. **A real but modest warm-up exists and is worth respecting**: ~1.6 %, settling in ~10 minutes from camera open.
   At `A_Q ≈ 0.15` that is still ~4 % on the pigment ratio, so a 10-minute settle before critical runs is cheap
   insurance — but it is not the explanation being hunted.

**What the A/B event then was — narrowed, still open.** It is a *smooth* spectral tilt (§16.7's table: 1.010 at
440–460 declining monotonically to 0.928 at 620–640), **not** a localized feature — which also rules out oil
carry-over in the blank cuvette (that would bite as a Soret-shaped notch at 440–470, not a smooth ramp). With
warm-up and camera controls both excluded, the leading remaining candidate is **beam geometry**: the cuvette was
removed and refilled between the two runs, and re-seating it shifts which part of the slit/grating is illuminated,
which tilts throughput smoothly across wavelength. **Decisive test — `diagnostics/cuvette_reseat_probe.py` (built 2026-07-27, awaiting Edwin's hands).**
It is not "measure six times": each round captures a **before** (untouched since the previous round's after),
prompts for a re-seat, then captures an **after**. So it yields two paired sets over the same timescale —
**re-seat deltas** (before→after) and **no-touch deltas** (after→next before, drift + noise only). If seating is
innocent the two are indistinguishable; if it is the culprit, the re-seat arm stands out against its own control
rather than against an assumption. Each delta is reported as the spectral tilt, the level change, and — using
Edwin's own `A_Soret = 0.801 / A_Q = 0.144` — **the pigment-ratio swing that seating error would have caused**.
Validated with a null run (nothing moved): noise floor **0.07–0.14 % tilt / 0.5–1.1 % ratio**, against the A/B
event's 5.04 % / 20–28 % — roughly 50× the discrimination needed, and the null correctly returns "innocent".
Run: `--changes 6` after a 5-minute settle. If the tilt reappears, cuvette seating is the error source, no
warm-up protocol would ever have fixed it, and the R→S→R′ bracket catches it every time.

**The discriminator already exists and costs nothing: the `CAPTURE-SETTINGS` line** printed for every capture
(§ capture-settings logging) carries `exposure_applied`, `wb`, `autoWb`, `gain`. Compare the two runs' lines: if
`wb`/`gain`/`autoWb` are identical, mechanism 1 (lamp); if they moved, mechanism 2 (camera) — and it is a bug,
not physics. **Do this before spending time on either fix.** Cross-check on the sensor: §16.2's self-heating
tilts the **other** way (red ↑ vs green/blue) at ~1 %, so this is not that. Note also that auto-exposure pins the
**peak**, which *is* the pump — so either mechanism is invisible in level and shows up purely as this shape
change. If mechanism 1 survives: §8's lamp warm-up drift-to-stable was never measured, and
`diagnostics/capture_quality_probe.py` Phase B (1 frame / 2 s × 5 min) measures exactly it; the clean physical
test is to keep the camera streaming and power-cycle only the lamp.

**Consequences.**
- This is **not** a gamma effect (the decode is a uniform scale on `A` and cancels in the ratio, §17.5.1 — and
  the pre-§17 run's 5.183 sits *between* the two new ones), **not** a floor effect (§17.8.5), and **not**
  fixable by normalization (§17.8.5).
- **Baseline subtraction makes it worse, not better:** removing the red-anchor offset (0.120 / 0.090 — itself
  drift) shrinks the denominator to 0.058 / 0.054 and the two ratios go to 9.43 vs 13.16.
- ⇒ **Blocking for any ratio work at low absorbance** — and the lever is the **lamp warm-up**, not §16's
  camera warm-keeper (W5/W6 stay worth finishing, but they would not have caught this).
- The cheap protocol fix that also *measures* the problem: bracket the run **R → S → R′** — blank, sample, blank
  again — and accept it only if the two blanks agree band-wise within ~1 %. That is a plugin acquisition step,
  not new physics, and it turns an invisible corruption into a visible per-run number. It also **self-corrects**
  if wanted: with two blanks straddling the sample, interpolate the reference to the sample's timestamp.
- **Measure the lamp first** (§8, still unmeasured): run the Phase-B warmup probe once and read off how long the
  phosphor/pump ratio takes to settle. That number becomes the coach line "lamp warming — N min left".

### 16.7.2 ⭐ SOLVED — cuvette RE-SEATING is the error source *(2026-07-27, measured on the rig)*

`diagnostics/cuvette_reseat_probe.py`, 6 re-seats of the **same** cuvette with the same liquid, exposure pinned,
5-minute settle first, each re-seat paired against a no-touch control over the same timescale:

| arm | n | tilt (phosphor/pump) mean · max | implied pigment-ratio swing mean · max | level |
|---|---|---|---|---|
| **re-seat** | 6 | **2.84 % · 6.71 %** | **9.6 % · 22.0 %** | 1.51 % |
| no-touch (control) | 5 | 0.26 % · 0.57 % | 0.7 % · 1.7 % | 0.22 % |

> **Re-seating moves the spectrum 11× as much as leaving it alone.** And the size matches the crime exactly:
> Edwin's A/B blanks differed by **5.04 %**, which sits inside the observed re-seat range (0.82 – 6.71 %).
> **§16.7's open question is closed.**

**The mechanism is visible in the numbers.** Across all 12 captures the **pump band moves 1.42 %** while the
**phosphor band moves 7.04 %** — a **5× larger swing in green+red than in blue**. Re-seating does not dim the
light uniformly (that would cancel in `T = S/R` anyway); it **tilts** it, and it tilts the half of the spectrum
where the Q band lives. Most likely the cuvette acts as a weak prism/window: a fraction of a millimetre of
displacement changes the beam's angle into the grating and which part of the dispersed image lands in the ROI, and
grating efficiency is a function of both angle and wavelength.

The `ph/pump` sequence also suggests **discrete seating states** rather than a continuum —
`0.6509 · 0.6945 · 0.6911 · 0.6854 · 0.6853 · 0.6781 · 0.6821 · 0.6678 · 0.6674 · 0.6600 · 0.6610 · 0.6956` —
clustering around **0.667 ± 0.010** and **0.690 ± 0.004**, i.e. the cuvette drops into one of a couple of
positions (rotated 180°? resting against a different wall?) with slow settling in between.

#### 16.7.2b Waiting does NOT fix it — the 60 s settling test *(2026-07-27, second rig run)*

Edwin's hypothesis after seeing the photo of his own rig: the pot is a wide shallow screw-jar with a **free
liquid surface in the beam**, carried by a fragile stack of two 25 cm cones, so a change may disturb the
**liquid and the mechanics** rather than the centring — in which case *waiting* would fix it. Tested directly:
6 re-seats, each followed by a **60-second window sampled continuously**.

| | tilt | implied ratio swing |
|---|---|---|
| peak excursion during the window | mean 4.62 %, max 8.90 % | — |
| **settled, after the full 60 s** | **mean 3.34 %, max 5.11 %** | **10.1 %, max 15.4 %** |
| untouched control | **0.09 %** | 0.3 % |

> **The residual after a minute is 37× the untouched control. Waiting does not bring it back.**

**But the curves refine the picture, and Edwin is partly right.** Per round, the share of the disturbance that
survives the minute: **78 · 96 · 91 · 46 · 51 · 94 %** — on average **76 % permanent, 24 % transient**. There is
a real settling component (round 5 fell to −8.9 % and was still climbing back at t = 60 s, last-third movement
1.10 %), and a fast transient in the first ~2 s that the earlier one-shot test was measuring blind. It simply
never returns to where it started.

**The decisive observation is the state sequence.** The undisturbed `ph/pump` *before* each round reads
`0.6923 · 0.6632 · 0.6828 · 0.6972 · 0.6890 · 0.6621` — a **5.3 % band** — while the no-touch control between
rounds is **0.09 %**. So each re-seat lands the instrument in a **new random optical state inside that band, and
it then holds that state until the next disturbance**. That is not a settling delay; it is
**irreproducibility of the optical state after re-seating**, and no pause can cure it.

**What is still open** is *which* element fails to reproduce — the jar's position, or the liquid surface inside
it (a 3 cm meniscus is a lens, and contact-line pinning is genuinely discrete, which fits the clustering seen in
the first run). **One experiment separates them: fill the jar to the brim, close the lid so there is no free
surface and no air gap, and re-run this same probe.** If the scatter collapses, it was the liquid surface — and
brim-filling is the fix. If it persists, it is the seating/mechanics and the answer is a keyed or clamped holder.
That test also pins the path length (§16.7.4), so it is worth doing regardless.

#### 16.7.4 The pot's fill level IS the path length — a correction to `SPEC_capability_proof.md` §7.3

The pot is a **3 cm × 1.3 cm screw-jar** (photo, 2026-07-27) with the beam running **vertically** through it.
`SPEC_capability_proof.md` §7.3 states *"the TRANSFER volume does not matter … the pot's fixed path length"*.
That is true for a cuvette with a horizontal beam and a fixed width; **here the path length is whatever depth was
poured**, and nothing in the protocol pins it:

| poured | depth | vs a full jar |
|---|---|---|
| 4 ml | 0.57 cm | 44 % |
| 6 ml | 0.85 cm | 65 % |
| 8 ml | 1.13 cm | 87 % |
| 9.2 ml | 1.30 cm | full |

**1 ml ≈ 0.14 cm ≈ 11 % of a full path ⇒ 11 % straight onto absorbance** — comparable to the ±25 % drop-count
error the spec already calls the dominant prep term. It also makes "2 drops in 6 ml vs 8 ml" ambiguous: pouring
the *whole batch* in gives `c × l = 1.333 × 0.750 = 1.000` (identical absorbance, a null experiment), while
pouring a *fixed* amount from each batch gives 1.333. The measured Soret ratio was 1.21, so probably the latter —
but the experiment cannot say, which is the point. **Fill to the brim and close the lid**: the path becomes the
jar's own 1.3 cm, and the free surface disappears with it.

#### 16.7.2c The same test with the SAMPLE in the jar — two channels, moving opposite ways *(2026-07-27)*

Edwin's question: does re-seating behave differently when the jar holds the light-green sample rather than the
blank, and might the sample *reduce* the artefact? It does both — and the run exposes an error channel the blank
run was structurally blind to.

| | blank | **sample (green)** |
|---|---|---|
| **tilt** mean · max | 3.27 % · 5.23 % | **1.84 % · 3.76 %** *(−44 %)* |
| implied pigment-ratio swing | 9.7 % | **5.5 %** |
| **level** mean · max | 1.68 % · 3.68 % | **4.95 % · 14.21 %** *(2.9×)* |
| untouched control (tilt) | 0.09 % | **0.02 %** |

**1. ⚠ CONFOUNDED — the surfactant reading below is WITHDRAWN (Edwin, 2026-07-27).** The two runs differ in
**two** ways, not one: between them Edwin also laid a **frosted-glass diffuser** (from an old camera lens) on top
of the jar. So the −44 % tilt cannot be attributed to the oil. *(The withdrawn reading was: two drops of oil act
as a surfactant and stabilise the meniscus. It may still be true — it is simply not what this pair of runs
shows.)*

**The evidence actually points at the diffuser.** The **untouched control** also improved, 0.09 % → **0.02 %**,
a 4.5× gain — and nothing is disturbed during a control interval, so meniscus reproducibility cannot explain it.
A diffuser can: it scrambles the angular distribution of the beam, so *any* small geometric change — jar
position, meniscus curvature, thermal creep — couples far more weakly into which part of the slit and grating is
illuminated. Desensitising the optics to geometry is exactly what a diffuser is for.

**And it plausibly fixes a specific defect Edwin identified: the jar's centre pin.** These acrylic jars carry a
small **moulding gate — a nub of extra acrylic in the middle of the bottom**, sitting right in the beam, and it
read visibly dark before the diffuser was added. A defect at the centre of the aperture whose *rotational
position changes every time the jar is put back* is a strong candidate for the **discrete seating states**
(0.667 vs 0.690, §16.7.2) — the jar returns at a different angle, the pin's shadow lands differently. The
diffuser smooths that shadow out, which is what Edwin observed.

**The clean experiment (one variable):** same liquid, same fill, toggle **only** the diffuser — 6 re-seats with,
6 without. Two cautions for it: (a) the diffuser costs light (the exposure had to go 64 → 256, i.e. ~4× less
signal, some of which is the sample's own absorption) so the SNR trade must be measured, not assumed; and (b) if
the glass simply **rests on the jar**, it is lifted and replaced along with it and so becomes part of the
disturbance — **mount it on the cone, not on the jar**, before drawing conclusions.

**2. The level swings 3× more — and only an ABSORBING liquid can show this.** On a blank, `A ≈ 0`, so the path
length is invisible: pour any depth and the transmitted intensity is the same. With the sample, intensity depends
on path through Beer-Lambert, so a level change is a **path change**: at a mean `A ≈ 0.3`, the observed 5 %
average implies ≈ 7 % of path (≈ 0.9 mm of a 13 mm jar), and the 14 % worst case implies ≈ 20 % (≈ 2.7 mm). The
jar is not returning to the same *effective depth of liquid in the beam* — exactly the variable §16.7.4 flagged
as unpinned.

**3. ⚠ CORRECTED — "level cancels in the ratio" is only half true, and the wrong half is the dangerous one.**
Two different things move the measured level, and they behave oppositely:

- **Path length** (more or less liquid in the beam): `A = ε·c·l`, so **both bands scale together** and
  `A_Soret/A_Q` is **exactly** invariant — verified: ×0.9, ×1.1, ×1.2 all give 5.563. Harmless for the verdict.
- **Throughput mismatch between the R capture and the S capture** (light lost or gained in the optics, not in
  the liquid): `A_measured = A_true − log10(k)`, an **additive offset**. That does *not* cancel, and because the
  denominator `A_Q ≈ 0.144` is small the offset eats a large fraction of it:

  | level mismatch R vs S | offset in A | pigment ratio error |
  |---|---|---|
  | 2 % | 0.009 | **+5.2 %** |
  | 5 % | 0.021 | **+14.2 %** |
  | 14 % | 0.057 | **+53.6 %** |

  ⇒ **a throughput mismatch is MORE damaging than a tilt of the same size**, and it is the same additive term
  that shows up as the non-zero red-anchor "baseline" (0.09–0.12 measured, §16.7). The probe reports tilt and
  level separately, but **both must be small** — the earlier claim that level was benign applies only to the
  path-length half.

**4. The instrument itself is excellent.** The untouched control reached **0.02 % tilt / 0.04 % level** — so the
camera, lamp and reduction chain contribute essentially nothing at this timescale. Every bit of the error under
discussion is **sample handling**, and re-seating still moves the spectrum ≈ 70× more than leaving it alone.

⇒ **Brim-filling gains a second, independent justification.** It removes the free surface (the tilt channel,
§16.7.2b) *and* pins the path length to the jar's own 1.3 cm (the level channel, §16.7.4). One change, both
channels — and it is the next thing to measure.

#### 16.7.2d What the last run would have cost the S/Q ratio — and the missing measurement *(2026-07-27)*

Putting §16.7.2c's two channels through the corrected algebra, per round of the sample run:

| round | shape (tilt) | level | S/Q if the level was PATH | S/Q if it was THROUGHPUT |
|---|---|---|---|---|
| 1 | −6.5 % | 7.47 % | −6.5 % | **+16.3 %** |
| 2 | +3.0 % | 0.35 % | +3.0 % | +3.9 % |
| 3 | +3.7 % | 5.19 % | +3.7 % | **+18.5 %** |
| 4 | −1.5 % | 14.21 % | −1.5 % | **+53.3 %** |
| 5 | −1.9 % | 0.48 % | −1.9 % | −0.7 % |
| 6 | +0.4 % | 2.03 % | +0.4 % | +5.7 % |
| **mean \|error\|** | | | **2.8 %** | **16.4 %** |

**The answer depends entirely on a split we have not yet measured** — and the two ends differ by 6×. That is the
open question, not a detail.

**The blank run already gives half of it.** With `A ≈ 0` the path length is **invisible** (pour any depth, the
same light comes through), so a blank's level variation is **pure throughput**: measured **1.68 % mean /
3.68 % max**. Reference and sample each get their own re-seat, so the mismatch that enters a real measurement is
~√2 × one draw:

| throughput mismatch R vs S | S/Q error |
|---|---|
| 2.4 % (typical) | **+6.3 %** |
| 5.2 % (bad pair) | **+14.8 %** |

⇒ **~6 % of S/Q error from throughput alone, on top of the tilt term.** The remainder of the sample run's larger
level swings is then path length — harmless for the ratio, but it means the jar is not returning to the same
depth-in-beam, which §16.7.4 already flagged.

**The measurement that closes it: re-run the blank with the diffuser mounted.** Blank isolates throughput
(no path sensitivity), and toggling only the diffuser isolates the diffuser. Two runs, one variable each.

#### 16.7.2e The live plot must be drawn in DN — the linearized trace caused a real measurement error

§17.7/15 predicted the linearized trace would "look alarming" and listed a DN display as optional. It is not
optional: on **2026-07-27 it cost a series of measurements.** Edwin saw the 440 nm end of the linear plot sitting
on the axis, concluded the signal was vanishing, and diluted 1.7× further — which halved the Q band, doubled the
error amplification, and took the run-to-run CV from 3.6 % to **14.2 %** (§16.7.5). The signal had in fact been
**60 DN, four times the guard**.

**Why the linear plot hides it.** Both axes are drawn 0…255, but the decode `255·(v/255)^2.2` crushes the bottom:

| landmark | DN axis | linear axis |
|---|---|---|
| saturation | 255 (100 %) | 255 (100 %) |
| AE target | 245 (96 %) | 234 (92 %) |
| healthy blank | 180 (71 %) | 119 (47 %) |
| healthy sample band | 120 (47 %) | 49 (19 %) |
| a dim-but-fine bin | 60 (24 %) | 10.6 (**4.1 %**) |
| **low-DN guard** | **16 (6 %)** | **0.58 (0.2 %)** |

**The entire usable-but-dim range 16–60 DN occupies the bottom 4 % of a linear plot** — one or two pixels above
the axis. Everything down there reads as "zero" whether it is healthy or dead.

**The principle: linear light for the MATHS, DN for the EYES.** `T = S/R`, the CIE integrals and Beer-Lambert all
require linear light — that is settled and stays (§17). But the live plot is not a physics readout, it is an
*exposure instrument*, and every decision made from it is a sensor fact: clipping at 255, the AE target at 245,
quantization taking over below 16. Those landmarks sit at fixed, recognisable heights **only on a DN axis** — the
same reason a camera histogram shows raw levels and an audio meter shows dBFS rather than linear amplitude.

**Implementation is display-only and trivial:** the decode is invertible and the inverse already exists
(`SpectralColorUtil.encodeGammaFraction`), so the panel plots `encode(value)` while the pipeline keeps the linear
values untouched. Label the axis **DN**, and draw the 16 DN guard line on it.

#### 16.7.2f Recipe verified, blank still the bottleneck — and the error is HEAVY-TAILED *(2026-07-27, 4 runs)*

Four fills of one sample at the new **18 ml : 6 drops**, diffuser **removed** (`tmp/20260727B/004-007`):

| | this morning | **these four** | 2023 |
|---|---|---|---|
| `A_Q` | 0.096 | **0.225** | 0.210 |
| amplification `0.434/A_Q` | 4.5 | **1.9** ✅ | 2.1 |
| darkest bin | 60 DN | **18–26 DN** ✅ | 4–16 DN |
| **S/Q CV** | 14.2 % | **14.3 %** ✗ | 3.6 % |

**The recipe did exactly what it was designed to do** — the amplifier is back to the 2023 value and the darkest
bin is in the target window. **And the CV did not move**, because the blank error roughly doubled at the same
moment: implied blank term `14.3 / 1.9 = 7.5 %` against this morning's `14.2 / 4.5 = 3.2 %`. The diffuser came
off between run 003 and run 004 — and the two diffuser runs before it (001/002) sit **1.0 % apart**. That is the
strongest evidence yet that the diffuser is doing real work.

**⭐ The error is not Gaussian — it is "usually fine, occasionally awful".**

```
S/Q:  4.225   4.482   4.137   5.569
      └─────── three within CV 4.2 % ───────┘   └─ one outlier, +28 %
```

Same shape as the six measured re-seat tilts (`6.71 · 0.82 · 1.05 · 2.10 · 1.11 · 5.23` — median 1.6 %, two
large). **⇒ report the MEDIAN of 3–4 fills, never the mean.** The median is the right estimator for a
heavy-tailed error; the mean is dragged by exactly the bad seating we cannot yet prevent. Here: median **4.353**
vs mean 4.603, and **the three clean fills already meet the ≤ 4.1 % target on their own.**

**New observation — the red anchor is now 75 % of the denominator.** `A_red` ran 0.144–0.183 against `A_Q`
0.196–0.243, and it **scales with concentration** (3× stronger sample → ~3× baseline: it was 0.042–0.064 this
morning). So it is the *sample*, not a throughput offset. It is **not turbidity** either — the slope rises toward
the **red** (+2.4…3.0e-3 /nm), the opposite of a scattering power law. So most of the "Q band" is broad oil
extinction rather than the chlorophyll Q peak. Two consequences, one reassuring and one closed:
- Dilution invariance survives (baseline and pigment both scale with `c`, so the ratio still divides out).
- **Subtracting it does NOT help discrimination** — on the 32-run set, `(S−R)/(Q−R)` gives d = **9.79 vs 10.39**
  (−6 %). Tested, rejected; leave the metric as it is.

**⇒ Next: diffuser back on (mounted to the cone, not the jar) + report the median of 3 fills.** Predicted CV
~2–4 %, i.e. discrimination restored.

#### 16.7.2g The diffuser A/B — CLAIM WITHDRAWN once n reached 4 *(2026-07-27)*

Edwin confirmed the split (001-003 with the diffuser, 004-007 without) and a fourth diffuser run (008) arrived
afterwards. **It overturns the reading taken at n = 2.**

| | S/Q | median | CV (all) | CV minus its one high outlier |
|---|---|---|---|---|
| **with diffuser** (001·002·003·008) | 4.972 · 4.924 · **6.691** · 4.239 | 4.948 | 20.1 % | **8.7 %** (n=3) |
| **without** (004·005·006·007) | 4.225 · 4.482 · 4.137 · **5.569** | 4.354 | 14.3 % | **4.2 %** (n=3) |

At n = 2 the diffuser pair happened to fall 1.0 % apart, which read as a 6× improvement. With the fourth run the
"clean" diffuser scatter is **8.7 %** — if anything *worse* than without. Formally: variance ratio **F = 4.3 on
df 2,2**, significant only above **19**. ⇒ **the two configurations are not distinguishable at this sample
size**, and the earlier "tightens the blank ~3×, the scatter ~6×" is withdrawn. (The blank spreads also
converged once n = 4: **4.6 % with vs 4.1 % without**.) The 14 % absolute-level difference likewise fails to
establish itself — **t-test p = 0.37**.

**A caveat had been attached to the first reading ("n = 2 and n = 3 — encouraging, not established"), but the
claim was still led with. The lesson is procedural: on a heavy-tailed error, n < 6 per arm cannot support a
comparison at all.**

**What IS robust across all eight runs**, and consistent with everything measured before:

- **two high outliers in eight** (6.69, 5.57) — one in four, exactly the rate the re-seat probe predicted;
- **the other six sit at CV 8.2 %** (mean 4.50), against 17.8 % for the raw set;
- the diffuser **cannot** be expected to fix this *while it rests on the jar*, because it is lifted and
  re-seated along with it — it is part of the disturbance, not a shield from it.

⇒ Nothing here changes the plan; it removes a false positive from it. **Mount the diffuser rigidly to the cone,
then run n ≥ 6 per configuration** — below that, this experiment cannot answer the question it is asking. And
report the **median**, which survives both outliers untouched.

#### 16.7.2h Nine same-sample runs: the scatter is ALL in the denominator *(2026-07-27)*

With runs 008 and 009 the diffuser arm reaches n = 5 and the comparison is still flat — **F = 1.47 (needs > 9.1),
medians 4.97 vs 4.35 with Mann-Whitney p = 0.29.** The withdrawal in §16.7.2g stands: *a diffuser resting on the
jar shows no measurable effect either way.*

The nine runs together say something more useful. On **one sample**:

| | range | CV |
|---|---|---|
| `A_Soret` (numerator) | 0.874 – 1.091 | **6.6 %** |
| `A_Q` (denominator) | 0.134 – 0.243 | **17.7 %** |
| `A_red` (baseline, 600–630) | 0.090 – 0.183 | 21.5 % |
| **S/Q** | 4.137 – 6.691 | **16.6 %** |

**The numerator is 2.7× steadier than the denominator, and the denominator moves with the baseline at
r = +0.99 (p < 0.0001).** `A_Q` and `A_red` are, run to run, the same quantity: the Q band is mostly the broad
baseline (74–77 %, §16.7.2f) and it is the baseline that wanders. Hold the denominator at its mean and the S/Q
CV falls **16.6 % → 6.6 %**, i.e. *all* the excess scatter is there.

**Consequence worth testing properly: a baseline-aware metric is immune to exactly this error.** Measuring each
candidate's class gap on the 2023 set against **today's** reproducibility:

| metric | class gap | today's CV | gap / CV |
|---|---|---|---|
| **S/Q** (current) | 41 % | 16.6 % | **2.47** |
| **(S−R)/(Q−R)** de-baselined | 63 % | 13.7 % | **4.58** |
| S/(Q−R) | 59 % | 11.7 % | 5.00 |
| (S−R)/Q | 45 % | 20.0 % | 2.26 |

Under the **2023** noise the raw ratio was best (d = 10.39 vs 9.79, §16.7.2f). Under **today's** noise the
de-baselined form is ~1.9× better. Both are true and consistent: subtracting `A_red` removes the additive term
that now dominates, at the cost of a noisier denominator when that term is quiet.

**⚠ Do NOT switch the metric on this evidence.** The candidates were compared on the same nine runs that revealed
the problem, which is how one overfits; `(S−Q)/(Q−R)` scores highest of all (5.24) and is a physically
meaningless combination, which is the tell. Only `(S−R)/(Q−R)` has a principled reading — subtract the baseline
from both bands. **Order of business: fix the instrument first** (the baseline wander is a symptom, not a fact of
nature); if it proves irreducible, validate `(S−R)/(Q−R)` on data that was not used to choose it, both classes,
n ≥ 15, one fixed optical configuration.

#### 16.7.2i Narrowing the bands (Edwin's proposal) — tested *(2026-07-27)*

Proposal: Soret **450–460** instead of 440–460, Q **560–570** instead of 560–580. Scored on both axes — class
gap from the 2023 set, reproducibility from the nine same-sample runs:

| bands (Soret / Q) | today CV | 2023 d | class gap | **gap / CV** |
|---|---|---|---|---|
| **CURRENT** 440–460 / 560–580 | 16.6 % | **10.39** | 41 % | 2.47 |
| **EDWIN** 450–460 / 560–570 | 15.7 % | 8.89 | 47 % | **3.00** |
| only Q narrowed 440–460 / 560–570 | 18.7 % | 8.95 | 42 % | 2.25 |
| **only S narrowed 450–460 / 560–580** | **13.8 %** | 9.97 | 46 % | **3.34** |
| Q avoids the crossover 555–570 | 21.2 % | 7.65 | 41 % | 1.96 |

**The proposal improves the composite by 21 % — and the gain is entirely the SORET half.** Narrowing Q *alone*
makes things **worse** (2.25). The best variant on this data is **Soret 450–460 with Q left at 560–580**: it is
the only one that improves today's reproducibility *and* nearly keeps the 2023 separation (9.97 vs 10.39).

**Two predictions of mine that the data refused:**

1. *"440–450 is floor-limited, so dropping it removes the noisiest part."* **Wrong** — per sub-band:

   | sub-band | sample DN | A | CV of A |
   |---|---|---|---|
   | Soret 440–450 | 45.8 | 1.351 | **5.7 %** (the steadiest) |
   | Soret 450–460 | 98.3 | 0.611 | 9.0 % |
   | Q 560–570 | 133.6 | 0.184 | **19.5 %** (the noisiest) |
   | Q 570–580 | 104.1 | 0.223 | 16.3 % |

2. *"560–580 straddles the green→red crossover (§16.8), so avoiding it should help."* **Wrong** — 570–580 is the
   *less* noisy half of the Q band, and pushing the window to 555–570 is the worst variant tested (1.96).

**The mechanism that does fit** is baseline-fraction matching: the wandering additive baseline (§16.7.2h) is
~14 % of A(440–460), ~23 % of A(450–460) and ~70 % of A_Q. The narrower Soret window carries a baseline share
closer to the denominator's, so the common term cancels better in the ratio. That is a *physical* prediction and
therefore testable: the best window should be the one whose baseline fraction best matches the denominator's.

**⚠ Not significant yet.** 16.6 % → 13.8 % is **F = 1.45 on df 8,8, needing 3.4**. Same discipline as §16.7.2h:
**fix the instrument first**, and if the baseline wander survives, test *Soret 450–460* on fresh data — both
classes, n ≥ 15, one optical configuration — before touching `PB_SORET_BAND`.

#### 16.7.2j Broadening the Q band — tested, and it fails on BOTH axes *(2026-07-27)*

Proposal: widen the Q window, e.g. start it at 500 nm. Unlike the narrowing test (§16.7.2i) this one is
unambiguous — **every widening is monotonically worse on both axes** (Soret held at 440–460):

| Q band | today CV | 2023 d | gap / CV |
|---|---|---|---|
| **560–580 (current)** | **16.6 %** | **10.39** | **2.47** |
| 555–585 | 18.1 % | 9.37 | 2.25 |
| 550–590 | 19.4 % | 8.59 | 2.14 |
| 520–590 | 22.5 % | 6.61 | 1.88 |
| 500–590 | 24.5 % | 5.98 | 1.72 |
| 500–560 | 32.3 % | 3.89 | 1.31 |

Separation falls because the added region is not pigment-specific — the class difference lives in the Q *peak*,
not in the clarity shoulder (the 500–540 band alone scored d = 4.03, §16.8.1). **The current 560–580 is at the
optimum of everything tested, in both directions.**

**⭐ The reproducibility half is the important finding, because it identifies the noise.** Widening a window
should *reduce* a band mean's scatter as `1/√bins`. It does the opposite:

| window | bins | CV of A | `1/√n` predicts |
|---|---|---|---|
| 565–575 | 68 | 18.0 % | (reference) |
| 560–580 | 137 | 17.7 % | 12.7 % |
| 550–590 | 274 | 19.9 % | 9.0 % |
| 520–620 | 687 | **21.8 %** | **5.7 %** |

⇒ **the error is a COHERENT offset across wavelength, not per-bin noise.** Ten times the bins buys nothing; the
CV even rises as more of the wandering baseline is included. This closes off a whole family of would-be fixes:
**more bins, heavier smoothing, longer bursts and more frames cannot touch this error.** Only two things can —
**instrument stability** (remove the wander) or a **baseline-differential metric** (subtract the common term,
§16.7.2h). That is the same conclusion three independent analyses have now reached.

#### 16.7.2k ⭐ SNV — the textbook correction for the error we derived *(2026-07-27, promising, NOT adopted)*

Edwin asked for the refined version of §16.7.2h: fit and subtract a baseline instead of one anchor number. Four
models were tried; two matter.

| metric | class gap | **SD today (n=9)** | **d_today** | 2023 d |
|---|---|---|---|---|
| **raw S/Q** (current) | 1.277 | 0.822 | **1.55** | **10.39** |
| constant baseline `(S−R)/(Q−R)` | 3.378 | 2.031 | 1.66 | 9.79 |
| **linear baseline** (2 anchor windows) | 3.277 | 1.259 | **2.60** | **10.27** |
| **SNV difference** | 0.439 | **0.0325** | **13.52** | 6.69 |

*(`d_today` = class gap ÷ today's SD, both in the metric's own units — the only scale-invariant comparison, and
the decision-relevant one: can the classes be told apart given TODAY's reproducibility. `≥ 3.3` gives 95 %
single-shot calls, `≥ 4.7` gives 99 %.)*

**Two candidates worth carrying forward:**

- **Linear baseline** — fit a straight line through two oil-quiet windows (520–540 and 600–630) and subtract it.
  **The only variant that improves today's scatter while keeping the 2023 separation intact** (d 10.27 vs 10.39).
  A conservative, physically plain change.
- **SNV difference** — standardise each absorbance spectrum (`(A − mean)/SD` over the capture window), then take
  `mean(440–460) − mean(560–580)`. **d_today = 13.52, nearly 9× the raw ratio.**

**Why SNV is not a lucky fit.** §16.7.2h/j derived the error model from the data: `A_measured = k·A_true + b`,
with a wandering multiplicative `k` (path/throughput) and additive `b` (baseline), `b` coherent across
wavelength. **SNV is the standard chemometric correction for exactly that model** — dividing by the spectrum's
own SD removes `k`, subtracting its own mean removes `b`. It was in the plan already as the "eureka preproc"
idea (`SPEC_capability_proof.md`).

**The evidence that it corrects the real failure, not the sample:**

```
run              003     007        <- the two runs that were WILD outliers in the raw ratio
raw S/Q        6.691   5.569        <- +60 % and +33 % excursions
SNV diff       2.615   2.672        <- ordinary members of the pack (all nine: 2.563 … 2.672)
```

The nine same-sample runs give **SD 0.0325 (CV 1.2 %)**, leave-one-out **0.019–0.035** — no single run carries
it. And the 2023 classes remain cleanly split with **no overlap** (green 2.410–2.533, brown 1.920–2.158).

**⭐ Run 003 is a DOCUMENTED fault, and it is the single best piece of evidence here.** Edwin observed the jar
**sitting badly** on that run — the exclusion is causal, not statistical, and it is recorded as such. Which makes
003 a natural experiment: one *observed* seating fault, put through both metrics.

| | run 003 | the other eight | distance | error |
|---|---|---|---|---|
| **raw S/Q** | 6.691 | 4.722 ± 0.529 | **3.7 σ** | **+42 %** |
| **SNV difference** | 2.615 | 2.597 ± 0.034 | **0.5 σ** | **+1 %** |

**SNV absorbs a known, seen, physical fault almost completely.** That is a far stronger claim than "it reduces
unexplained scatter" — the scatter has a name, Edwin watched it happen, and the correction repairs it. It also
closes the loop on the whole §16.7 chain: re-seating → geometry change → additive/multiplicative error → SNV is
the standard correction for that error → the observed bad seat is corrected.

*(Note the exclusion does NOT flatter SNV: removing 003 improves the raw ratio a lot — CV 16.6 % → 11.2 %,
d_today 1.55 → 2.41 — and leaves SNV essentially unchanged, 13.52 → 12.87. The incumbent gains from the cut and
still loses by 5×.)*

**⚠ The same exclusion cannot settle the diffuser question.** With 003 out for cause the diffuser arm reads CV
8.8 % (n=4) against 14.3 % (n=4) — but **F = 0.37 on df 3,3, needing 9.3.** And with each group minus its own
worst run the ranking reverses (8.8 % vs 4.2 %). **A comparison whose verdict flips with the outlier rule is not
a result.** Fix the rule before the data: n ≥ 6 per arm, pre-registered exclusion criteria (a documented physical
cause, as here — never "it looks wrong").

**⚠ Why this is a lead and not a switch:**
1. Nine runs, **one sample, one day, one instrument state**. The class gap still comes from the 2023 set.
2. Under *stable* conditions the raw ratio is the better discriminator (2023 d 10.39 vs 6.69) — SNV buys immunity
   by discarding information. It is the right choice only while `b` and `k` wander.
3. It is **not a ratio**: the Roast Ampel thresholds (4.4 / band 6.0→3.0) would need complete re-derivation, and
   today's sample reads 2.56–2.67, *above* the 2023 green range — consistent with fresh 2026 oils reading higher,
   but it must be re-anchored, not translated.
4. SNV normalises over the **capture window**, so the window (440–630) becomes part of the metric's definition
   and must be pinned.
5. Several candidates were compared on the same nine runs — the usual selection risk. SNV's defence is that it
   was derived from the error model rather than chosen by score, and that it fixes the two known outliers.

⇒ **Validation experiment before any adoption:** both oil classes, n ≥ 15, one fixed optical configuration, data
not used to choose the metric. Test **linear-baseline** and **SNV difference** side by side against the raw
ratio. Meanwhile the instrument fix remains first — with `b` and `k` held still, the raw ratio is still the best
discriminator we have.

#### 16.7.2l ⭐ Why 2023 did NOT wander: the oil changed, not the instrument *(2026-07-27)*

Edwin's question, and the sharpest one of the investigation: *the instrument is the same and the jar was re-seated
in both series — so why did the 2023 runs hold CV 3.6 % while the 2026 runs scatter 14–17 %?*

**Because `A_Q` is not the same quantity in the two series.** Splitting the denominator into its broad baseline
(measured at 600–630, where the oil should absorb little) and the rest:

| | A_Soret | A_Q | A_red (baseline) | **pigment Q** = Q − red | baseline share |
|---|---|---|---|---|---|
| 2023 green | 0.647 | 0.172 | 0.093 | **0.079** | 54 % |
| 2023 brown | 0.616 | 0.247 | 0.113 | **0.135** | 45 % |
| **2026 fresh** | 0.992 | 0.212 | **0.154** | **0.059** | **72 %** |

The *total* `A_Q` is unremarkable (0.212 against 0.172–0.247). Its composition is not: **the pigment content of
the denominator is roughly halved and the broad baseline has gone from ~50 % of it to 72 %.**

**The mechanism — why that alone reproduces the observed 2–3×.** The two halves of `A_Q` respond differently to
a disturbance:

- **The pigment half co-varies with the Soret band.** Same molecules, same concentration, same path length, so a
  re-seat that changes the path moves both bands together and **the ratio cancels it**. This is precisely the
  mechanism that makes the ratio dilution-invariant in the first place.
- **The baseline half does not.** It is broad extinction from suspended matter, with its own geometry dependence.

So the ratio's self-correction only ever applied to the *pigment fraction* of the denominator. In 2023 about half
the denominator was self-correcting; in 2026 only ~28 % is. **The same jar wobble therefore produces 2–3× more
ratio error, with no change to the instrument and no change in handling.** The numerator agrees: `A_Soret` CV is
2.6 % in 2023 against 6.0 % now.

**Where the extra baseline comes from — and a correction to §16.7.2f.** Most likely **suspended solids that have
not settled**: fresh unfiltered pumpkin oil is cloudy, and the 2023 oils had three years to clarify themselves.
§16.7.2f dismissed turbidity because the baseline does not rise toward the blue like Rayleigh scattering — **that
test was too narrow.** Large particles (Mie / geometric regime, particle ≫ λ) scatter almost **greyly**, which
looks exactly like the broad, near-flat offset observed. The two eras' baselines even carry opposite slopes
(2023 −1.1e-3 /nm, 2026 +3.0e-3 /nm), consistent with different particle populations rather than with one
wavelength law.

**⭐ The lever this hands us — sample clarification.** Let a diluted sample **stand overnight**, or **filter /
centrifuge** it, and re-measure. Falsifiable prediction: `A_red` falls, the pigment share of `A_Q` rises, and the
S/Q scatter drops — **with the instrument untouched**. If it holds, this is a bigger and cheaper win than any
optical fix discussed so far, because it attacks the reason the denominator is fragile rather than the
disturbance that exploits it.

**And an irony worth recording.** The 2026 oils read "greener" — the reason `SPEC_roast_ampel.md`'s threshold
moved 2.8 → 4.4 — **precisely because their Q-pigment is low**. The property that raises the ratio is the same
one that shrinks its denominator, so **the fresher and greener the oil, the more fragile its measurement.** That
is a property of the metric, not of the rig, and it argues for the baseline-corrected or SNV form (§16.7.2k)
independently of every instrument consideration.

#### 16.7.2m Is the BROWN class safe even when the green wanders? *(Edwin's hypothesis, 2026-07-27)*

Edwin: *maybe I must accept that the green oil is volatile, but the brown oil is not — so it stays below the
Ampel threshold and the verdict still holds.* **The mechanism is right and 2023 confirms it. The 2026 oils do
not inherit the comfort.**

**2023 — hypothesis confirmed.** Per-oil, 4 runs each:

| class | mean CV | baseline share | pigment Q |
|---|---|---|---|
| green (K,L,O,P) | **2.8 %** | 54 % | 0.079 |
| **brown (M,N,Q,R)** | **2.0 %** | 45 % | **0.135** |

oilN reaches CV **0.5 %**, oilQ 1.3 % — no green oil comes close. Exactly what §16.7.2l predicts: the brown oils
carry **1.7× the pigment content in the denominator**, so more of it self-corrects. And every 2023 oil sat
**5–65 SD** from its threshold: the classification was never in doubt for either class.

**2026 — the ordering survives, the margin does not.** The 2026 brown has **1.8× the pigment-Q of the 2026
green** (0.055 vs 0.031), so it *should* be the steadier of the two, as in 2023. But **both sit far below the
2023 levels** (0.135 / 0.079 then), and both carry a **72 % baseline share** — beyond anything measured in 2023.
The brown is relatively better off and absolutely worse off.

**The margin is what settles it.** Against the 4.4 threshold:

| | S/Q | gap to 4.4 | at CV 5 % | at CV 11 % |
|---|---|---|---|---|
| 2026 brown (`NowSBudget`) | 4.06 | 0.34 | **1.7 SD** | 0.8 SD |
| 2026 green (`NowSteirerkraft`) | 5.18 | 0.78 | 3.0 SD | 1.4 SD |

**Even at an optimistic 5 % CV the brown oil sits 1.7 SD below the threshold — a ~4 % misclassification rate,
and worse if its CV is nearer the green's.** So the argument *"the brown is safe, so ignore the green's
wander"* **does not hold for these oils**: they are intrinsically closer together than the 2023 pair (24 % apart
vs 41 %) *and* individually more fragile. In 2023 that argument would have been sound; in 2026 it is not.

**▶ NEXT STEP — the missing measurement is small and decisive: 4–6 fills of the 2026 BROWN oil.** Its CV is the one number
that decides whether the verdict is safe in the direction that matters (catching an over-roasted oil). If it
lands near 4–5 % the brown side is workable while the green stays noisy; if it lands near the green's, the whole
2026 pair needs the instrument fix or the SNV metric before any verdict is trustworthy.

#### 16.7.2n The jar-wall rings, and WHERE the diffuser belongs *(Edwin's observation, 2026-07-27)*

Edwin, from visual inspection: the diffuser does homogenise the disk nicely, **but the jar's WALLS throw rings
around it** — and the spectrometer slit probably does not sit exactly over the jar's centre.

**The rings are a real error source, and of the right kind.** Light entering the acrylic wall is refracted and
guided, emerging around the disk having travelled a **different path** — much of it never crossing the full
liquid depth. Any of it that reaches the slit is **stray light**: signal that did not experience the sample's
absorption. Two consequences, both matching what we measure:
- stray light **biases high absorbances low** (it caps `A_max` at `−log10(f)` for a stray fraction `f`), which
  bites hardest in the Soret band — the numerator;
- **its share depends on where the jar sits**, so it changes on every re-seat. That is precisely the
  geometry-coupled error §16.7.2 has been chasing.

**⭐ Mounting the diffuser at the SLIT is better than on the jar — for two independent reasons.**

1. **Mechanical (already established).** On the jar it is lifted and re-seated every time, so it is part of the
   disturbance (§16.7.2g explains the null result that way).
2. **Optical, and this one is the subtle one.** A diffuser *at the jar* becomes a new extended source **in the
   jar's own plane**: it takes the disk **and the rings** and smears them together, so ring light is mixed into
   everything the slit sees — it can make stray light *worse* even while the field looks more uniform. A
   diffuser *at the slit* only scrambles the light that **already arrived** there; it cannot import ring light
   that the geometry was not already delivering. It homogenises the **angular** distribution entering the
   grating, which is exactly what makes the response independent of how the beam arrives.

That is also standard instrument practice: fibre spectrometers use a **cosine corrector / diffuser at the
entrance** for precisely this reason. Edwin's instinct matches the textbook. Costs to accept: light (already
seen, exposure 64 → 256, affordable per §16.7.2f) and possibly a little spectral resolution, since the diffuser
fills the acceptance cone.

**But the targeted fix for the rings is not the diffuser at all — it is an APERTURE.** A black mask over the jar
with a central hole (≈ 15–20 mm of the 30 mm jar) blocks the wall-guided light at its source, before any optics
can mix it in. Cheap, printable as part of the holder, and it has a bonus: it **fixes the illuminated area**, so
the measured geometry stops depending on how the jar is centred. Diffuser and aperture solve *different*
problems and are complementary:

| | what it fixes |
|---|---|
| **aperture over the jar** | *which* light is measured — blocks wall/ring stray light |
| **diffuser at the slit** | *how* the light arrives — removes angular/positional sensitivity |

**Cheap test for whether stray light is actually significant:** measure a deliberately **over-concentrated**
sample (say 3× the standing recipe). Without stray light `A_Soret` scales linearly with concentration; with a
stray fraction `f` it **flattens off** toward `−log10(f)`. The concentration at which it stops rising gives `f`
directly — and if it flattens early, the aperture is worth building before anything else.

#### 16.7.3 What follows from it

1. **⭐ The real fix is procedural and free: do not remove the cuvette between reference and sample.** Leave it
   seated and exchange the *liquid* in place (aspirate the blank, pipette the sample in). The no-touch arm is the
   measurement of that protocol: **0.7 % ratio error instead of 9.6 % — a 14× improvement**, larger than anything
   else discussed in this document.
2. **Mechanical backup:** a keyed / clamped / spring-loaded holder so the cuvette can only return one way. Worth
   it for the end-user product, where "don't touch it" is not enforceable.
3. **R→S→R′ bracket (§16.7) is still worth having** — it *detects* the residue and any other event, and it costs
   one extra blank capture. Detection ≠ prevention: item 1 prevents.
4. **Re-anchor expectations, not thresholds.** Nothing about the verdict maths changes; what changes is that a
   run's reference must be earned by not disturbing the optics. The Roast Ampel threshold and the 47/66 hue bands
   are unaffected by this finding.
5. **⭐ The Capability Proof's noise floor WAS this — reconciled 2026-07-27.** Edwin confirms the 32-run series
   also changed cuvettes, so the apparent contradiction (CV 3.6 % vs a 9.6 % mean re-seat error) needed
   resolving. It resolves cleanly, because the re-seat error is **skewed**: the six measured tilts were
   6.71 · 0.82 · 1.05 · 2.10 · 1.11 · 5.23 %, i.e. **median 1.60 %** with two large excursions dragging the mean
   to 2.84 %. Predicted ratio error = tilt × 0.434/A_Q, and the two data sets differ in A_Q as well
   (capability set **0.210 ± 0.068**, the new dilute pair **0.144–0.178**):

   | | A_Q | typical re-seat (median) | bad re-seat (max) |
   |---|---|---|---|
   | 32-run capability set | 0.210 | **3.3 %** | 13.9 % |
   | NowSteirerkraft A/B | 0.16 | 4.4 % | **18.2 %** |

   **Observed: capability within-class CV 3.6 % / 4.5 %; A/B reference-attributable divergence 20–28 %.** Both
   land on their predictions. ⇒ **Cuvette seating was never absent — it IS the dominant term in the published
   proof's scatter**, and Edwin's A/B pair simply caught a bad re-seat at a thinner dilution.

6. **Therefore the proof itself should get sharper.** Removing the seating term (no-touch arm: 0.26 % tilt →
   0.5 % ratio error) leaves the non-seating noise, `√(3.6² − 3.3²) ≈ 1.4 %`, for a total near **1.5 % instead of
   3.6 %** — about **2.4× tighter, i.e. Cohen's d ≈ 25 instead of 10.4**. That is a concrete, falsifiable
   prediction: re-run a few oils with the cuvette left seated and the within-class SD should collapse. It also
   means the *published* d = 10.39 understates the method — it was measuring the holder as much as the oil.

### 16.8 The Q band sits in the sensor's colour-filter CROSSOVER *(2026-07-27 — why the blank reads low at 580 nm)*

Edwin: *"the pure alcohol blank has such small values at 580 nm, yet the capture image looks uniform."* Both
observations are correct, and the resolution is that **the dip is the camera, not the light.** Replaying the
embedded full-resolution blank frame per channel (`diagnostics/gamma_reference_valley.py`, raw DN):

| nm | R | G | B | max = the spectrum | winner |
|---|---|---|---|---|---|
| 540–550 | 5.2 | **186.9** | 0.0 | 186.9 | GREEN |
| 560–570 | 10.6 | **152.0** | 0.0 | 152.0 | GREEN |
| **570–580** | 39.2 | **121.1** | 0.0 | **121.1  ← the notch (57 % of peak)** | GREEN |
| 580–590 | **127.6** | 77.6 | 0.0 | 127.6 | RED |
| 590–600 | **152.3** | 47.6 | 0.0 | 152.3 | RED |

The light really is smooth — the **green filter has rolled off and the red filter has not yet risen**, so
`max(R,G,B)` (§15's reduction) dips where neither is efficient. `sum(R,G,B)` at 570–580 is 160 vs `max`'s 121,
i.e. the photons are there, split across two half-open filters. **`max()` hands over GREEN → RED at ~580 nm with
only a 24 DN margin** — the Q band's own upper edge.

**This does not bias `T`** — the notch is instrument response, common to reference and sample, and it cancels in
`S/R`. What it costs is **photons and stability, exactly at the denominator**:

| candidate denominator band | level (DN) | photons (ΣRGB) | drift between the two blanks |
|---|---|---|---|
| clarity 500–540 | 195.6 | 246.2 | −2.5 % |
| green peak 520–545 | 192.2 | 212.4 | −2.6 % |
| **Q 560–580** | **136.4** | **161.5** | **−4.0 %** |
| red 590–620 | 138.3 | 163.3 | −2.7 % |

⇒ the Q band is simultaneously the **darkest** part of the usable range, the place where the reduction **switches
channel**, and the **most drift-prone** — and §16.7 needs it as a small denominator (`A_Q ≈ 0.15`). That is the
structural reason the ratio is fragile, independent of whatever causes the drift.

#### 16.8.1 Option (b) — moving the denominator — TESTED AND REFUTED *(2026-07-27)*

The obvious response to "the denominator sits in the darkest, twitchiest band" is to move it somewhere brighter.
**Measured, it is wrong.** `diagnostics/pigment_denominator_trial.py` replays the full **32-run Capability-Proof
set** through the app's own chain (`AbsorptionOp` → `MedianFilterOp(7)` → `bandMean`, exactly
`DevSpectralPlugin.__pigmentRatio`) and scores each candidate on **both** axes that matter — class separation on
a stable set, and fragility on Edwin's drift-affected A/B pair:

| denominator | green (mean ± SD) | brown (mean ± SD) | **Cohen's d** | A/B divergence |
|---|---|---|---|---|
| **Q 560–580 (current)** | 3.750 ± 0.134 | 2.472 ± 0.111 | **10.39** | **48.2 %** |
| clarity 500–540 | 8.117 ± 0.918 | 5.249 ± 0.414 | 4.03 *(−61 %)* | 75.1 % |
| green peak 520–545 | 7.393 ± 0.834 | 4.711 ± 0.327 | 4.23 *(−59 %)* | 71.2 % |
| wide green 500–560 | 7.888 ± 0.917 | 5.140 ± 0.397 | 3.89 *(−63 %)* | 74.4 % |
| red 590–620 | 6.386 ± 0.472 | 4.203 ± 0.229 | 5.89 *(−43 %)* | 66.3 % |
| Q widened 555–590 | 4.240 ± 0.180 | 2.773 ± 0.125 | 9.46 *(−9 %)* | 50.7 % |

*(The current band reproduces `SPEC_roast_ampel.md` §2's published 3.75 ± 0.13 / 2.47 ± 0.11 and d = 10.39
exactly — so the replay is trustworthy before it is used to judge alternatives.)*

**The dark band wins on both axes, and by a lot.** It also has the *lowest* within-class scatter (CV 3.6 % / 4.5 %
vs 7–11 % for every brighter band) despite having the fewest photons. **Photon count was the wrong model.** What
makes a denominator good is how much genuine *pigment* absorbance it carries: 560–580 is a chlorophyll Q band, so
numerator and denominator move together as one substance. The brighter bands are not pigment bands — their
absorbance is mostly baseline and scattering, which varies independently run to run, so they add noise to the
ratio *and* dilute the class difference. Moving the denominator trades a real chemical signal for photons the
metric does not actually need.

⇒ **Keep 560–580.** The crossover costs less than the chemistry would.

**Remaining options** (DESIGN — none implemented):
- **(a) Leave the band, fix the stability — now the ONLY sensible route.** The instrument is worst exactly where
  the chemistry is best; that is unlucky, not fixable by band choice. §16.7's R→S→R′ bracket plus the lamp/WB
  discriminator. Note every candidate band diverged 48–75 % on the drifted pair — **drift dominates all of them**,
  which is further evidence that stability, not band placement, is the lever.
#### 16.8.2 Option (c) — ΣRGB instead of max — ALSO TESTED, ALSO REFUTED *(2026-07-27)*

Every archived run embeds both full-resolution capture frames, so all three reductions can be replayed from the
**same pixels** (`diagnostics/reduction_sum_vs_max.py`, 32 runs × 2 frames, decode → combine → absorbance →
median(7) → band means):

| reduction | green | brown | **d** | green CV | A/B divergence | notch depth |
|---|---|---|---|---|---|---|
| **max (current)** | 3.731 ± 0.128 | 2.460 ± 0.116 | **10.41** | 3.4 % | 49.2 % | 55 % |
| sum | 3.653 ± 0.126 | 2.412 ± 0.114 | 10.34 | 3.5 % | 48.2 % | 50 % |
| gated sum (>6 DN) | 3.405 ± 0.441 | 2.312 ± 0.146 | **3.33** | 12.9 % | 48.2 % | 50 % |

*(The pixel-level replay reproduces the spectrum-level results — d = 10.41 vs 10.39, A/B divergence 49.2 % vs
48.2 % — so it is measuring the same thing the app does.)*

**`sum` is a wash, and the gate is harmful.** Two things worth keeping:

1. **In LINEAR light the crossover discards much less than it appears to in DN.** At 570–580 the DN reading is
   G = 121, R = 39 — which *looks* like `max` throwing away a quarter of the light. Decoded, that is G = 49.4 and
   **R = 4.1**: the second channel carries only ~8 %. The notch is therefore mostly a *real* dip in the sensor's
   total response, not an artefact of `max`, and `sum` only lifts the floor 50.2 → 55.9 (55 % → 50 % depth). The
   earlier "the photons are there" framing was a DN-space illusion — gamma expands small values.
2. **⚠ A gated sum breaks the reference cancellation.** The gate fires at *different wavelengths* for blank and
   sample (the sample is dimmer, so more of its channels fall under the floor and get zeroed while the blank
   keeps them), so `S/R` acquires a sample-dependent, wavelength-dependent bias — d collapses 10.41 → 3.33 and CV
   triples. **Any conditional applied per-spectrum rather than per-pair is dangerous for the same reason.**

⇒ **Keep `max`.** All three structural options are now closed by measurement: the band placement (b), the
reduction (c), and — by elimination — only **(a) instrument stability** remains.

---

## 17. Gamma linearization — the one instrument nonlinearity the reference does NOT cancel  *(DE-RISKED DESIGN — Edwin 2026-07-24, verified 2026-07-26 (§17.5); impl on explicit request)*

Prompted by an AI thread on "camera linearization for spectral imaging" (`Downloads/pumpkin/Google Gemini.html`).
The thread's general point is correct — a consumer camera applies a non-linear (gamma) curve so relative-intensity
maths is wrong unless linearized — but **most of its recommendations we already satisfy for free, and one we should
adopt.** This section records the reasoning and the plan.

### 17.1 Why we DISCARD the QE / blackbody-lamp calibration (recorded, not chased)
The thread spends most of its length on characterizing the sensor's **Quantum-Efficiency (relative spectral
response) curve** — via a Planck's-law blackbody (halogen) lamp or the ASTM solar standard — and dividing it out.
**That is for _absolute_ spectroscopy (no reference).** We do **reference-based transmission**: `T = S/R`
(isopropanol blank vs. sample). The sensor's per-wavelength QE **and** the lamp's own spectrum are **common factors
in both R and S, so they cancel exactly in the ratio.** That is the entire point of a reference measurement — it
divides out the instrument+illuminant response. So the blackbody/QE calibration would be **effort spent
re-solving a problem the reference already solves.** We do **not** pursue it. (Likewise **OECF characterization —
doubling exposure to map the response curve — is out of scope for now**, Edwin.)

### 17.2 The residual the reference does NOT cancel = the nonlinearity (gamma)
Linearity is the one thing a ratio cannot fix. With encoding `v = v_lin^(1/γ)` (γ ≈ 2.2, sRGB):
`T_measured = S/R = (S_lin/R_lin)^(1/γ) = T_true^(1/γ)`  ⇒  `A_measured = A_true / γ` — a **uniform scale** on
absorbance. To recover true absorbance, linearize R and S **before** dividing.

### 17.3 Why it is an ACCURACY upgrade, not a correctness fix for the verdict
Because `A_true = γ·A_measured` is a *uniform* scale, **band ratios are gamma-invariant** — the Soret/Q pigment
ratio (the pumpkin verdict) is unchanged. This is almost certainly why the **Capability Proof already succeeded**
(10–13× class separation, dilution-invariant) with gamma-encoded data. So gamma linearization does **not** rescue
the verdict; it improves everything the ratio does *not* protect:
- **Colour accuracy** (the hue chips / `spectrumToColor`) — colour is *non-linearly* wrong without it; **biggest
  real gain**.
- **Dark-band fidelity** — the gamma toe distorts most near black, exactly where the dim Soret 440–460 slope lives.
- **Multi-camera consistency** — different cameras carry different gamma; linearizing normalizes absolute absorbance
  across the fleet (Edwin runs several cameras).
- Makes absorbance *physically real* (today it is ~1/γ ≈ 0.45× compressed).

### 17.4 The plan (design; implement on explicit request)
- **Linearize PER-CHANNEL, FIRST — before any reduction.** Decode each of R,G,B (`c_lin = (c/255)^γ`), then form
  the intensity from the linear channels. *Amended 2026-07-26 (§17.5):* the original "you cannot gamma-decode the
  `qGray` *sum*" warning is a **leftover from the qGray era**. §15 replaced that weighted sum with **max-channel**,
  and `max()` is an **order statistic**: for any strictly increasing `f`, `max(f(R),f(G),f(B)) ≡ f(max(R,G,B))`.
  Decoding before or after the channel combine is therefore **provably identical**, not merely close. The same
  holds for the **median** despike. The only genuine non-commuters are the two *averages* — the Tukey biweight
  (spatial) and the sigma-clipped mean (temporal) — so **decode-first remains mandatory by concept**, and it is
  free: there is no cost to doing it in the right place. Measured residual if one got the order wrong anyway:
  **0.08–0.20 %** on the pigment ratio (§17.5).
- **Use the PURE POWER LAW `v_lin = (v/255)^2.2`. The piecewise sRGB EOTF is DECLINED** *(decision 2026-07-26,
  measured — §17.5)*. The real sRGB curve is piecewise (linear toe below DN ≈ 10.3, `((v+0.055)/1.055)^2.4`
  above, net behaviour ≈ 2.2). It is the more physically faithful model — and it **costs 24 % of the pumpkin class
  separation** while buying **no measurable colour gain**, because the toe rescales the Soret band by a
  *sample-dependent* amount (deeper-dipping = browner samples lose more), which injects scatter into the one band
  that carries the signal. The pure power law is a **uniform** scale and is therefore *exactly* verdict-neutral.
  This is a deliberate operational choice over a physical one: **do not "fix" it to the standard curve** — that
  silently loses a quarter of the separation. Home for a per-camera gamma override (if ever needed):
  `SpectrometerSensorUtil` (alongside WB-Kelvin / exposure). OECF characterization stays out of scope.
- **Where:** a linearization step in the frame→spectrum reduction path — concretely in
  `ImageSpectrumAcquisitionLogicModule.__reducedColumnValues`, right after the RGB array is sliced out of the frame
  and **before** `toGrayMaximumArray` (the first line of our code that touches pixel values).
- **Ship the colour ceiling with it (REQUIRED, same commit).** `DevSpectralPlugin.__colourChips` passes
  `ceiling=3.0` to `EvaluationColorUtil.spectrumToHsl` — a clamp that stops a `T→0` spike dominating the CIE
  integral. It is dormant today (A peaks 1.3–1.6). Linearization doubles A to ~2.9–3.5 and the clamp **starts
  cutting real signal**: measured absorbed hue drift 298.2° → 296.9° and chroma 63.2 → 59.0, where the unclamped
  path stays *exactly* 298.2°/63.2. Scale it **3.0 → 6.6** (= 3.0·γ), or make it relative to the spectrum max.
- **Dark level / pedestal: already retired.** §4's 150-frame dark at exposure 1 measured **black level 0.00 % FS**.
  A pedestal would be a *bigger* lever than gamma (a +8/+16 DN offset swings the ratio −12 %…+13 %, non-monotone),
  so this is load-bearing: decode assumes true black is 0, and on this camera it is.
- **Known limit:** we only have **8-bit, already-demosaiced, gamma-encoded** frames (UVC via cv2), **not true RAW**
  — so this is *approximate* linearization (precision loss; pure-power model), not the thread's RAW ideal.
  Good enough for colour + cross-camera consistency; not a path to absolute radiometry.

**Implementation walkthrough: [§17.6](#176-implementation-rubber-duck--walked-against-the-as-is-code-2026-07-26)**
— the plan above vs the as-is code (12 findings, phases L0–L6). It **reopens one gate**: the hue-band verdict of
the shipped `PumpkinOilPlugin` rides the *perceived* axis, which is the one axis gamma moves.

**Status: DE-RISKED DESIGN — every open question answered (§17.5), implement on explicit request.** The motive is
**closure**, not accuracy (Edwin 2026-07-26): we *know* the camera is non-linear, so leaving the assumption in the
pipeline keeps "maybe it's the gamma" on the suspect list for every future anomaly forever. Linearizing removes it
permanently. The colour gain (+33–40 % perceived chroma) is the bonus. Because the decode is verdict-neutral, this
is a **strictly safe** change: the Roast Ampel threshold does **not** move. *(Narrowed by §17.6/1: safe for the
peak-**ratio** verdict — the older **hue-band** verdict still needs the L0 measurement.)*

### 17.5 Measured verification of §17 — the 2026 oils  *(Edwin 2026-07-26; §17.3's claim, now measured)*

§17.3 *asserted* that gamma linearization cannot move the pumpkin verdict. This section **measures** it, on the
two fresh-2026 captures (`measurement_report_NowSBudget.pdf`, `measurement_report_NowSteirerkraft.pdf`) and — where
scatter is needed — on the full **32-run** Capability-Proof set (K/L/O/P green · M/N/Q/R brown).

**Method.** Every report PDF embeds `workflow.json` (the meaned R and S spectra, 1305 pts, 440–629.8 nm) **and**
both full-resolution 2592×1944 RGB capture frames as `/EmbeddedFiles`. So the whole pipeline could be replayed
off-line at two levels: **spectrum level** (decode R and S → `AbsorptionOp` → `MedianFilterOp(7)` → `bandMean` →
`EvaluationColorUtil`) and **pixel level** (replay `ImageSpectrumAcquisitionLogicModule` on the frames: ROI
x 820–2125 / y 906–1783 read off the overlay, 20 % inset, max-channel + Tukey-per-column). The replay reproduces
the app **bit-for-bit** — ratio `4.05906808789795` → 4.0591 and `5.182554` → 5.1826, Soret/Q 0.807/0.199 and
0.698/0.135 — and the 32-run group statistics reproduce `SPEC_roast_ampel.md` §2's published 3.75 ± 0.13 /
2.47 ± 0.11 exactly. **The numbers below are the app's own maths, not a re-derivation.**

#### 17.5.1 The verdict is invariant — structurally, not by luck

| decode model | S-Budget ratio | Steirerkraft ratio | verdict @ 4.4 | perceived chroma | absorbed hue |
|---|---|---|---|---|---|
| as-is (today) | **4.0591** | **5.1826** | RED / GREEN | 33.7 / 32.2 | 298.2° / 300.0° |
| pure power γ=1.8 | 4.0591 | 5.1826 | RED / GREEN | 41.6 / 40.8 | 298.2° / 300.0° |
| pure power γ=2.2 | 4.0591 | 5.1826 | RED / GREEN | 43.9 / 43.5 | 298.2° / 300.0° |
| pure power γ=2.6 | 4.0591 | 5.1826 | RED / GREEN | 45.9 / 45.9 | 298.2° / 300.0° |
| true sRGB EOTF (toe) | 3.6362 | 4.7391 | RED / GREEN | 43.5 / 42.7 | 292.8° / 296.8° |

**Bit-identical at every exponent** — 15 significant digits, not "close". `A_true = γ·A_measured` is a *uniform*
scale and a ratio of two band means divides it out exactly. The **absorbed** colour (hue *and* chroma) is equally
invariant, because the CIE path drops luminance at `XYZ_to_xy` and chromaticity ignores scale. Only the
**perceived** colour (from `T`) moves — and that is the one axis that does not discriminate the oils anyway.

**Fleet consequence (better than §17.3 assumed):** the condition is "*a* pure power law", not "2.2 specifically".
So across Edwin's several cameras the **pigment ratio is already directly comparable today**, whatever each
camera's exponent. Only *absolute* absorbance and colour need linearizing for cross-camera comparability.

#### 17.5.2 Why the piecewise sRGB EOTF is declined (the load-bearing measurement)

Effective gamma per band (= `A_decoded / A_as-is`, which for a pure power law is exactly γ at every bin):

| band | sample DN range | % of bins below the knee (10.3 DN) | effective gamma |
|---|---|---|---|
| **Soret 440–460** | **5.1 … 79** | **17.4 %** (brown) / 4.3 % (green) | **1.58 … 2.14** |
| blue-green 460–510 *(context)* | 80 … 164 | 0 % | 2.14 … 2.24 |
| clarity 510–540 | 144 … 163 | 0 % | 2.21 … 2.22 |
| Q 560–580 | 56 … 115 | 0 % | 2.01 … 2.17 |
| deep red 600–630 *(context)* | 60 … 113 | 0 % | 2.02 … 2.17 |

Everywhere except Soret the two models agree within ~5 %. In Soret — where the oil absorbs hardest and the sample
bottoms out at **DN 5** — the toe drags the effective gamma to 1.6, **and by a sample-dependent amount** (the
browner oil has 17.4 % of its bins under the knee vs the green oil's 4.3 %). A non-uniform, sample-dependent
rescale of the numerator band is exactly what a ratio cannot absorb:

| | | as-is | **pure 2.2** | true sRGB |
|---|---|---|---|---|
| **2026 pair** | ratio gap | 1.123 | **1.123** | 1.103 (−1.8 %) |
| | absorbed chroma gap | 14.8 | **14.8** | 10.1 (−32 %) |
| **2023 proof (32 runs)** | ratio gap | 1.277 | **1.277** | 1.156 (−9.5 %) |
| | green SD · brown SD | 0.134 · 0.111 | **0.134 · 0.111** | **0.201** · 0.053 |
| | **gap/noise (Cohen's d)** | **10.39** | **10.39** | **7.87 (−24 %)** |
| | absorbed chroma gap | 11.8 | **11.8** | 9.7 (−18 %) |
| | within-oil dilution spread | 8.7 % | 8.7 % | 8.8 % |

Same direction on **both** oil sets. Dilution invariance survives the toe (8.7 → 8.8 %) — the damage is
**inflated within-group scatter** (green SD +50 %), visible only on the 32-run set, because two runs have no
scatter to show. And the colour gain the whole exercise is *for* is unaffected by the choice:

| | perceived chroma, as-is | **pure 2.2** | true sRGB |
|---|---|---|---|
| 2026 pair | 32.9 | **43.7 (+33 %)** | 43.1 |
| 2023 proof (32) | 29.1 | **40.6 (+40 %)** | 39.9 |

⇒ the piecewise refinement delivers marginally *less* colour and costs a quarter of the discriminator. **Pure
`x^2.2`.** Recorded so a later reader does not "correct" it toward the standard.

#### 17.5.3 Decode order — measured on real pixels

Replaying the extractor on the embedded full-resolution frames, decode-**before**-combine vs post-hoc scalar
decode differ by **0.20 %** (S-Budget) and **0.08 %** (Steirerkraft) on the ratio, and by **< 0.2°** on every hue.
That is the Jensen gap of the Tukey row average alone (`mean(x)^γ ≠ mean(x^γ)`, gap ∝ spread). The **temporal**
half could not be measured — the 150 burst frames are not persisted, only their mean — so it is *argued*: frame-to-
frame spread (shot noise, after §14.8's C1–C3 dim-frame rejection) is smaller than row-to-row spread across the
slit height (vignetting, smile, illumination profile), so the temporal gap should be **≤** the spatial one. If that
ever needs measuring rather than arguing, it takes one bench run that dumps the raw burst.

#### 17.5.4 Consequences recorded elsewhere

- **`SPEC_roast_ampel.md` §2** — the 4.4 threshold is anchored to the *decode model*; under pure `x^2.2` it does
  **not** move.
- **`SPEC_pumpkin_peak_ratio_eval.md` §1b.3** — the Soret band-placement re-test this investigation triggered
  (the toe worry is what prompted "shift 440 → 450"; measured answer: don't).
- **`SPEC_capability_proof.md` §7.3 / `LAB_DIARY_capability_proof.md`** — the dilution-protocol change that
  removes the Soret band from the toe entirely, which makes this whole subsection moot going forward.

**Side observation (independent of gamma):** the darkest Soret bins sat at **DN 5 of 255** (≈2 % FS), where
quantization alone is ±10 % relative. Harmless in practice (the band mean over ~140 bins averages it away) but it
means the oil was near-opaque at 440 nm at the 1:20 dilution — the finding that drove the protocol change. An open,
minor proposal: a **low-DN guard** (report the per-capture band-minimum DN, so the floor is *visible* before a bin
ever reaches 0 and absorbance saturates silently). Largely obsolete once the protocol lands (floor moves 5 → 16 DN).

### 17.6 Implementation rubber-duck — walked against the as-is code  *(2026-07-26)*

§17.4/§17.5 settled the **physics** (pure `x^2.2`, decode-first, verdict-neutral). This pass walks that plan
through the code that would actually execute it. The headline correction: **"verdict-neutral" is proven for the
peak-RATIO verdict, and the shipped end-user plugin does not use it** — see finding 1. Everything else is
mechanical, but three of the mechanics are *silent* if missed (2, 3, 5).

1. **⭐ `PumpkinOilPlugin`'s verdict is NOT gamma-invariant — §17.5 measured the wrong verdict.**
   `PumpkinOilPlugin.evaluation` reads `EvaluationColorUtil().spectrumToRgbAndHue(transmission)` and hands the hue
   to `VerdictOp` → `VerdictLogicModule` (bands **47° / 66°**). That is the **perceived** axis — the one axis
   §17.5.1 explicitly measured as *moving* (perceived chroma 32.9 → 43.7). `T → T^γ` is a per-wavelength
   distortion of transmission, **not** a scale, so its chromaticity is free to shift; only the *absorbed*
   chromaticity and the *band ratio* are provably invariant. §17.5 tabulated perceived **chroma** but never
   perceived **hue**, so the number that decides the pumpkin verdict is the one number not yet measured.
   ⇒ **L0 (below) is a gate, not a formality:** replay the perceived HUE, as-is vs γ=2.2, on the 2026 pair *and*
   the 32-run set, and compare the shift against the 47/66 band edges. The same shift lands on
   `test_pumpkin_workflow_end_to_end` and on `test_virtual_device_image_roundtrip`'s ±3° hue tolerance. The
   Roast-Ampel 4.4 threshold stays untouched either way (§17.5.4).
   *(If the hue does move: the bands are calibrated against a decode model exactly as the 4.4 threshold is —
   re-anchor them in the same commit, or the end-user verdict silently changes meaning.)*

2. **⭐ Keep the 0–255 scale: decode with a 256-entry LUT, never a normalization to [0,1].**
   Use `f(v) = 255·(v/255)^γ` — monotone with `f(0)=0`, `f(255)=255`. That preserves the saturation/dead mask at
   `ImageSpectrumAcquisitionLogicModule.py:133`, `valid = (gray < 255.0) & (gray > 0.0)`, **exactly**: no other DN
   maps onto the endpoints (`f(254)=252.8`, `f(1)=0.0013`). If the decode instead returned [0,1], that mask would
   silently stop rejecting anything — every value is `< 255` — and clipped pixels would flow into the Tukey
   estimate unnoticed. Plot autoscale, the probes and the diagnostics logs also keep their familiar scale.
   Implementation: `LUT = ((numpy.arange(256) / 255.0) ** GAMMA) * 255.0`, then index the **uint8** slice at
   `:129` *before* `.astype(numpy.float32)`. Exact (256 possible inputs), and it removes a per-frame
   `numpy.power` over ~0.7 Mpx × 150 frames × 2 roles from the burst path. A per-camera exponent becomes one
   table rebuild.

3. **⭐ The low-reference guard silently becomes 12× stricter — the spectral window shrinks.**
   `TransmissionLogicModule.DEFAULT_REFERENCE_FLOOR_FRACTION = 0.01` masks every bin where the reference is below
   **1 % of the reference peak**. Taken in the *linear* domain that is `0.01^(1/2.2)` = **12.3 % of peak DN**:
   every bin whose reference sits between 1 % and 12.3 % of peak DN silently vanishes from `T` — and therefore
   from `A`, the band means and the colour integral. Nothing errors; the spectrum just gets shorter at the edges,
   where the white-LED reference is weakest (deep blue ≈440, far red ≈630 — both **inside** the pumpkin ROI).
   ⇒ Re-express the guard in the same commit: `0.01 → 0.01^γ ≈ 6.3e-5`, or apply the floor in DN before the
   decode. L0 should also just *read off* the reference at 440/630 nm as a % of peak, so we know whether the ROI
   was ever near that edge.

4. **The raw-DN domain boundary — decode ONLY the measurement extraction.** Explicitly do **not** decode:
   - **the calibration branch (`:58-61`)** — line detection needs peak *positions* (invariant under any monotone
     map) and raw `QColor` hues (untouched), but its anchoring is **prominence-RANK-sensitive** (§15.9/9).
     Decoding compresses dim peaks relative to bright ones, so the blue **Hg 436** line that §15 just rescued
     would lose relative prominence against `prominence = 0.01·peak` — reintroducing the G4 anchor risk for
     **zero** benefit. Calibration stays in DN.
   - **`SpectralWorkflowEngine.__calibrationRoiHasSignal`** (`qGray(image.pixel(...)) > 20`) — reads raw pixels,
     unaffected, leave it.
   - **`SpectrometerRegionOfInterestLogicModule`** (geometry) and **`AutoExposureLogicModule.frameBrightness` /
     `VideoThread.__settleUntilStable`** (steers the camera; the AE target 245 and the 1 % settle tolerance are
     DN facts, §14.9/§14.8-fix-2) — all stay raw.
   ⇒ The rule, worth a comment at both branches so nobody "unifies" them later: **anything that steers the
   camera or finds geometry stays in DN; only the measurement extraction linearizes.**

5. **The virtual encoder stops being a no-op — it must gamma-ENCODE.** §15's big de-risk does **not** repeat here.
   `SpectrumToVirtualImageUtil.__encodeOne` writes `gray = 255·value/vmax`; with a decoding reader every virtual
   capture returns `value^γ`. Fix: `gray = 255·(value/vmax)^(1/γ)` — which makes the virtual device *more*
   faithful (it now models what a real camera does) and improves dark-bin quantization. Consequences: the
   `§15 INVARIANT` comment block in that file is superseded; **re-bake** the sets
   (`tests/bake_virtual_capture_sets.py`) and bump `ENCODER_VERSION "v1" → "v2"` — the folder name and `set.json`
   carry it for exactly this reason, and a stale `v1` folder on disk would otherwise decode γ-distorted. Tests
   that ride this path: `test_virtual_device_image_roundtrip`, `test_pumpkin_workflow_end_to_end`,
   `test_frame_provider_burst`, `test_capture_frame_rejection` (it *encodes* a deliberately dim image — still
   rejected, more strongly). Virtual `T` stays invariant either way (reference and sample share one `vmax`).

6. **Robust-statistics constants: self-scaling except one.** Under `x^γ` a small relative deviation multiplies by
   γ — and so does the MAD — so `TUKEY_C`, `SIGMA_K` and `DIM_FRAME_K` are ratios and keep their meaning. The
   exception is the **fixed** `DIM_FRAME_SCALE_FLOOR = 0.02`: 2 % measured in the linear domain is ≈ **0.9 % in
   DN**, so the docstring's "effective reject band ≥ K·2 % ≈ 6 % dim" becomes ≈ 2.7 % dim — C1 dim-frame
   rejection gets ~γ× more trigger-happy in the MAD≈0 case. Either divide it out (`0.02 → ~0.045`) or accept it
   deliberately and fix the docstring. `tests/test_capture_frame_rejection.py` pins the current behaviour.

7. **The colour ceiling is copy-pasted 4× across 2 repos — and one copy ships from the DB.** `ceiling=3.0` lives
   in `DevSpectralPlugin.__colourChips` (3 `spectrumToHsl` + 3 `complementViaWhitePoint` call sites),
   `spectracsPy/tests/test_color_retrieval.py` and `spectracs-plugins/tests/test_dev_plugin_improved_colour.py`.
   §17.4 says "scale 3.0 → 6.6" — but under M3 the plugin is a **sealed, versioned DB blob**: a linearizing host
   plus an older assigned plugin version = clamped chips, silently, with no version check that would catch it.
   ⇒ Prefer §17.4's own alternative and make the ceiling **relative** (cap inside `EvaluationColorUtil.__sanitize`
   at `k·max(values)`), which is gamma-proof *and* skew-proof and deletes the constant from plugin code. If the
   absolute number is preferred, at minimum hoist it host-side to `EvaluationColorUtil.ABSORBANCE_CEILING` so one
   edit moves all four.

8. **Stamp the decode model into the run.** Stored runs hold *post-extraction* values (DbMeasurement blobs, the
   `workflow.json` embedded in every report PDF), so old runs keep rendering exactly as today — good — but a
   post-change absolute `A` is γ× a pre-change one, and every baseline in `LAB_DIARY_capability_proof.md` /
   `SPEC_capability_proof.md` is pre-change. Record `captureDecode: "pow2.2"` (or the per-camera exponent) in the
   workflow metadata so the era is visible **in the artifact** instead of inferred from its date. Ratio metrics
   stay comparable across the boundary (§17.5.1) — absolute absorbance and colour do not.

9. **Put the decode in core, or the replays drift.** `diagnostics/calibration_probe.py`,
   `diagnostics/capture_quality_probe.py`, `diagnostics/calibration_fix_test.py` and the §17.5 off-line replay
   each re-implement the extractor. Home the decode next to the reductions it precedes —
   `SpectralColorUtil` in `spectracsPy-core` (`decodeGammaArray` / `gammaLut`, alongside `toGrayMaximumArray`) —
   so probes import it. Otherwise §17.5's replay silently stops reproducing the app bit-for-bit, and that
   reproducibility is what made the whole verification credible.

10. **Per-camera home + Android.** The exponent belongs where §14.9 already parks per-sensor facts:
    `SpectrometerSensorUtil` (`spectracsPy-model`), beside WB-Kelvin and exposure. Default 2.2 everywhere until
    measured. §17.5.1's fleet note bounds the damage: ratios are already cross-camera comparable, so a wrong
    per-camera exponent costs colour and absolute `A` — never the ratio verdict. The same extractor runs on
    Android; the LUT is plain numpy, so nothing new there.

11. **Quantization gets γ× worse exactly where the signal is — so ship the low-DN guard with the decode.** One DN
    step at DN 5 is 20 % relative before decode, ≈44 % after; §17.5's side observation puts the Soret floor at
    DN 5. The ~140-bin band mean still averages it away, but after linearization the plot's toe is compressed
    toward zero, so a near-floor capture is *harder* to spot by eye. That promotes the §17.5 "low-DN guard"
    (report the per-capture band-minimum DN) from *minor proposal* to **ship it in the same milestone**.

12. **Ordering rule for the retired pedestal.** If dark-level subtraction ever returns (§5), it must be applied
    **in DN, before** the LUT — the sensor's black level is added ahead of the camera's encoding, so subtracting
    after the decode subtracts the wrong quantity. Put the rule in the LUT construction comment, where the next
    person will be standing.

**Phases**  *(DESIGN — implement on explicit request only)*

```
+----+------------------------------------------+---------------------------------+------------------------------------+--------+
| Ph | What                                     | New / Touched                   | Gate                               | Risk   |
+----+------------------------------------------+---------------------------------+------------------------------------+--------+
| L0 | MEASURE-FIRST GATE (off-line, no code):  | the §17.5 replay tooling        | Hue shift known + compared to      | -      |
|    | perceived HUE as-is vs g=2.2 (2026 pair  | (workflow.json in the report    | 47/66. Reference at 440/630 nm     | (gate) |
|    | + 32 runs) vs the 47/66 verdict bands    | PDFs)                           | as % of peak known (finding 3).    |        |
|    | (finding 1); reference-edge headroom     |                                 | => go / re-anchor-bands / stop.    |        |
| L1 | Core decode: gamma LUT + decodeGamma-     | TOUCH SpectralColorUtil (core)  | Unit: f(0)=0, f(255)=255, monotone,| LOW    |
|    | Array next to the toGray* reductions      | + unit test                     | LUT == closed form. No behaviour   |        |
|    |                                          |                                 | change yet.                        |        |
| L2 | Wire into the extractor: LUT on the uint8 | TOUCH ImageSpectrumAcquisition- | Mask semantics unchanged; spectrum | LOW-MED|
|    | slice BEFORE astype/toGrayMaximumArray;   | LogicModule :129-133 (+ a       | shape changes as predicted; suite  |        |
|    | comment the DN-domain boundary at :58     | comment at the calib branch)    | green except the known movers.     |        |
| L3 | Reference floor re-expressed for the      | TOUCH TransmissionLogicModule   | The 440/630 bins still present in  | MED    |
|    | linear domain (0.01 -> ~6.3e-5) - SAME    | (constant + comment)            | T; window length unchanged vs      |        |
|    | commit as L2, else the window shrinks     |                                 | today's run.                       |        |
| L4 | Virtual encoder inverse-gamma; re-bake     | TOUCH SpectrumToVirtualImage-   | Round-trip test green again; the   | LOW-MED|
|    | the sets; ENCODER_VERSION v1 -> v2         | Util + bake script + the 4      | 3 baked v2 folders written.        |        |
|    |                                          | virtual-path tests              |                                    |        |
| L5 | Colour ceiling made RELATIVE (host-side); | TOUCH EvaluationColorUtil +     | Chips unchanged on a pre-decode    | LOW    |
|    | DIM_FRAME_SCALE_FLOOR decision; decode    | DevSpectralPlugin + 2 tests;    | run; no clamp on a post-decode     |        |
|    | stamp in the workflow metadata; low-DN    | RobustReduction constant        | one; stamp present in workflow.json|        |
|    | guard                                    |                                 |                                    |        |
| L6 | Rig verify on the ELP: calibration ~0.6nm | -                               | Calibration PASS; ratio matches    | -      |
|    | still PASSES, ratio unmoved, chroma up    |                                 | the pre-decode run to ~0.2%;       |        |
|    |                                          |                                 | chips visibly richer.              |        |
+----+------------------------------------------+---------------------------------+------------------------------------+--------+
Order: L0 (gate) -> L1 -> L2+L3 (one commit) -> L4 -> L5 -> L6. L2 without L3 is a silent regression.
```
*(Ordering revised by §17.7/21 — **L2·L3·L4 are ONE commit**: the reader's decode and the virtual encoder are
inverse halves, so either one alone leaves the virtual device γ-distorted. The full as-built table is §17.7.)*

**Status after the duck:** the plan is sound and the physics is closed, but §17.4's *"strictly safe — no verdict
moves"* holds only for the ratio verdict. **L0 must run before any code**: it is off-line, uses tooling that
already exists, and it decides whether the pumpkin hue bands need re-anchoring alongside the decode.

### 17.7 Second rubber-duck pass — the mechanics of writing it  *(2026-07-26)*

§17.6 walked the *design* against the code. This pass walks the **edit itself**: what a first cut would get wrong
while typing, and what the phase table has to look like as a result. It **revises §17.6's ordering** (finding 21).

13. **⭐ Do not put a mutable γ on the `SpectralColorUtil` singleton.** `sciens.base.Singleton.__new__` hands back
    **one process-wide instance** per class, shared by the video thread and the GUI thread. A `setGamma()` on it is
    global mutable state read mid-burst from another thread — and a silent cross-test leak: the unit tests run in
    one process, so a test that sets γ=1.0 to exercise the no-op path poisons every test that runs after it.
    ⇒ LUT as a **module-level constant** built at import for the default γ, plus a small `lutFor(gamma)` dict cache
    for overrides. γ is passed in, never stored.

14. **The LUT *replaces* the `astype`, and must sit after the ROI slice.** At `:129` today the chain is
    frombuffer → reshape → **slice** → `.astype(numpy.float32)`. `frame = LUT[slicedUint8]` yields float32
    directly, so it is a one-line change, not two. Two traps: build the LUT **float32** (a float64 LUT silently
    upgrades the whole hot array — 2× memory, and the new dtype flows into the Tukey estimator), and keep it
    **after** the slice (decoding before it means 5 Mpx instead of ~0.7). `numpy.frombuffer` is read-only, but
    fancy indexing returns a fresh writable array, so the NaN mask at `:135` keeps working.

15. **The live trace will look alarming on the rig — and that is correct.** The decode is near-identity at the top
    (DN 245 → 233) and crushes the middle (DN 120 → 49): the reference plateau drops ~2.5× while the peak barely
    moves, so the plot reads *dimmer and more peaked*. That is the visual opposite of §15's "blue lifts ~3×"
    result, which is what the eye at the rig is now calibrated to. Two defences: warn the operator **before** L6 so
    it is not read as a regression, and consider keeping the **capture-panel live plot in DN** (display-only) —
    the panel is an exposure-judging instrument, and exposure is a DN fact for exactly the reason AE stays in DN
    (§14.9, §17.6/4).

16. **Grep-verified, not assumed: nothing else judges the spectrum's amplitude.** `CapturePanel` reads no spectrum
    values at all (its only numeric clamps are the exposure slider); `AcquisitionGuidance` carries no amplitude
    threshold; the sole absolute-amplitude gate in the chain is `SpectralWorkflowEngine.__calibrationRoiHasSignal`
    (`qGray(image.pixel(...)) > 20`), which reads **raw pixels** and is therefore unaffected. So the blast radius
    of the scale change is exactly the three sites already named — the saturation mask, the reference floor, and
    the dim-frame scale floor. Worth the grep: "some view surely shows a peak number" was the obvious fear, and
    it is false.

17. **Every touched file exists 4–5 times in the tree.** `ImageSpectrumAcquisitionLogicModule.py`,
    `SpectrumToVirtualImageUtil.py` and `SpectrometerSensorUtil.py` each have copies under
    `android/server/app_src/`, `android/spike/app_src/`, both `.buildozer/android/app/` trees and
    `deployment/spectracsPy-model/`. An APK built from a half-synced `app_src` ships the **old reader with the new
    encoder** (or the reverse) — a γ-distorted spectrum with no error anywhere. Decide per phase and write it
    down: `.buildozer/` are build artifacts (leave), `app_src/` is APK source (mirror or knowingly defer with
    Android marked stale).

18. **The dim-frame test cannot catch a half-landed change — don't let it reassure you.**
    `test_capture_frame_rejection` scales the *spectrum* by 0.45 before encoding, so after inverse-encode +
    decode the frame is still 45 % dim (and if the encoder half were missing, 17 % — dimmer, still rejected). It
    stays green either way. The test that actually detects the mismatch is
    `test_virtual_device_image_roundtrip` (recovered ≈ source). Treat that one as the L4 gate.

19. **Make the domain visible in the code, not only in a comment.** Both branches of
    `ImageSpectrumAcquisitionLogicModule` write into the same `Spectrum` type, which carries no unit — one branch
    now DN, the other linear. §17.6/4's comment is the weak form of the fix; the cheap strong form is naming:
    rename `__reducedColumnValues` → `__reducedLinearColumnValues`, and mark the dict built at `:105` as linear.
    A future reader edits at the name, not at the comment.

20. **No hidden normalization in the colour path — confirmed.** `SpectrumToColorLogicModule` aligns onto the CMF
    grid and integrates; it never normalizes, and chromaticity is scale-invariant. So the perceived hue moves
    (§17.6/1) purely because the spectrum's **shape** changes — there is no scale bug to find there, and no knob
    in that module that could compensate. Recorded so the L0 result is not chased into the wrong file.

21. **⭐ Ordering correction: L2, L3 and L4 are ONE commit.** §17.6's table had L4 following L2. But the reader's
    decode and the virtual encoder are **inverse halves of one transform**: with only L2, every virtual capture
    reads `value^γ`; with only L4, it reads `value^(1/γ)`. Either gap distorts the **DEV bench demo, the plugin
    round-trip and the doc-automation screencasts**, which all run on the virtual path. L3 is already welded to L2
    (§17.6/3). ⇒ one atomic commit: extractor + reference floor + encoder + re-bake.

22. **Skip the per-camera γ hook for now (YAGNI, and it would be param plumbing).**
    `SpectrometerSensorUtil.getSensorSettings(sensor)` needs a `SpectrometerSensor` object; the extractor holds no
    sensor handle — it pulls only the calibration profile out of `ApplicationContextLogicModule`. Wiring γ
    per-camera therefore means threading a sensor through the capture path, which is exactly the plumbing pattern
    we avoid elsewhere. §17.6/10 already concludes every camera starts at 2.2, and §17.5.1 shows a wrong exponent
    costs colour only, never the ratio. ⇒ **document the seam, do not build it** until a second camera is
    actually measured.

**Implementation phases — as-built table**  *(supersedes §17.6's; DESIGN, implement on explicit request only)*

```
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| Ph | What                              | Files touched                              | Gate / how you know it worked         | Risk |
+====+===================================+============================================+=======================================+======+
| L0 | MEASURE-FIRST GATE. Off-line      | (none - analysis only, the §17.5 replay)   | Perceived hue shift KNOWN for both    |  -   |
|    | replay: perceived HUE as-is vs    |                                            | oils + the 32 runs, compared against  | gate |
|    | g=2.2 on the 2026 pair + 32 runs, |                                            | 47/66. Reference at 440/630 nm as %   |      |
|    | vs the 47/66 verdict bands.       |                                            | of peak known. => GO / RE-ANCHOR      |      |
|    | Also: reference-edge headroom     |                                            | BANDS / STOP.                         |      |
|    | for the floor change (17.6/3).    |                                            |                                       |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| L1 | Core decode util. Module-level    | spectracsPy-core .../spectral/util/        | New unit test: f(0)=0, f(255)=255,    | LOW  |
|    | float32 LUT + lutFor(gamma)       |   SpectralColorUtil.py           (TOUCH)   | strictly monotone, LUT == closed form |      |
|    | cache; NO gamma stored on the     | spectracsPy/tests/test_gamma_decode.py     | to 1e-6, dtype float32. Whole suite   |      |
|    | singleton (17.7/13). Doc the      |                                  (NEW)     | unchanged - nothing calls it yet.     |      |
|    | per-camera seam, don't build it.  |                                            |                                       |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| L2 | READER: LUT on the uint8 slice,   | .../acquisition/ImageSpectrumAcquisition   | Mask still rejects 255/0 (assert on a | MED  |
| +  | replacing .astype (17.7/14).      |   LogicModule.py  :129 (+:105, :115 rename)| clipped fixture). Ratio matches the   |      |
| L3 | Rename -> __reducedLinearColumn   | .../transmission/TransmissionLogicModule.py| pre-change run to ~0.2% (17.5.3).     | ONE  |
| +  | Values; DN-domain comment at the  |   DEFAULT_REFERENCE_FLOOR_FRACTION          | T covers the SAME nm window as before |COMMIT|
| L4 | calibration branch :58.           | .../synthesis/SpectrumToVirtualImageUtil.py| (the L3 check - else the window       |      |
|    | FLOOR: 0.01 -> 0.01^g (~6.3e-5).  | tests/bake_virtual_capture_sets.py          | silently shrank).                     |      |
|    | ENCODER: inverse gamma + version  |   ENCODER_VERSION v1 -> v2                  | test_virtual_device_image_roundtrip   |      |
|    | v1 -> v2; RE-BAKE the 3 sets.     | spectracs-references/.../virtual_captures/  | GREEN = the two halves match (17.7/18)|      |
|    | ATOMIC - see 17.7/21.             |   pumpkinoil_{under,perfect,over}_v2  (NEW) | + pumpkin e2e + frame_provider_burst. |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| L5 | Fallout, one commit per bullet:   | plugin_sdk/util/EvaluationColorUtil.py     | Chips: no clamp on a post-decode run; | LOW  |
|    | (a) ceiling RELATIVE, host-side   | plugins/dev/DevSpectralPlugin.py (drop 3.0)| identical output on a pre-decode one. |      |
|    | (b) DIM_FRAME_SCALE_FLOOR /g      | RobustReductionLogicModule.py (+docstring) | Rejection count unchanged on the C1   |      |
|    | (c) captureDecode stamp in the    | workflow metadata + report JSON            | fixtures. Stamp visible in a fresh    |      |
|    |     workflow/report JSON          | tests: test_color_retrieval,                | workflow.json + report PDF. Low-DN    |      |
|    | (d) low-DN guard (band-min DN)    |   test_dev_plugin_improved_colour           | line printed per capture.             |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| L5b| ANDROID mirror decision (17.7/17) | android/{server,spike}/app_src/... (3 files)| Either mirrored, or Android recorded  | LOW  |
|    | - mirror app_src or record stale  |                                            | as knowingly stale in this spec.      |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+
| L6 | RIG VERIFY on the ELP. Warn the   | (none)                                     | Calibration ~0.6 nm still PASSES      |  -   |
|    | operator FIRST that the live      |                                            | (untouched by design); pigment ratio  | rig  |
|    | trace legitimately looks dimmer   |                                            | unmoved vs the pre-decode run; colour |      |
|    | in the mid-band (17.7/15).        |                                            | chips visibly richer; window intact.  |      |
+----+-----------------------------------+--------------------------------------------+---------------------------------------+------+

DEPENDENCIES
  L0 ──gates──▶ everything (it can still say "re-anchor 47/66 first")
  L1 ──────────▶ L2+L3+L4  (the util must exist before the reader imports it)
  L2·L3·L4  =  ONE ATOMIC COMMIT   (decode ⟷ encode are inverse halves; floor is welded to decode)
  L5, L5b   =  after, independently revertable
  L6        =  last, needs Edwin + the ELP + the lamp warm (§16)

ROLLBACK
  The atomic commit is a single revert: no schema change, no stored-data migration (stored spectra are
  post-extraction values and keep rendering as-is), and the v1 baked sets are still on disk next to v2.
```

**What this pass changed:** ordering (L2·L3·L4 atomic), one design simplification (no per-camera γ yet), and three
coding traps that would each have shipped quietly — singleton γ state, a float64 LUT, and an Android `app_src`
half-sync.

### 17.8 AS-BUILT — L0–L5b implemented 2026-07-26 *(L6 rig-verify pending; ONE decision open)*

> **Status: IMPLEMENTED, NOT COMMITTED.** 277 app tests + 23 plugin tests green. **L0 fired both warnings** —
> the hue verdict moves and the window narrows — so §17.6/1 and §17.6/3 were not theoretical. The floor is fixed
> in code; the **47/66 band re-anchor is Edwin's call** and is the one thing still open.

#### 17.8.1 L0 result — measured, 61 archived runs

Replayed every `measurement_report_*.pdf` in `spectracs-references/tmp/` through the app's own
`TransmissionLogicModule` → `EvaluationColorUtil` → `VerdictOp`, as-is vs pure `x^2.2`:

| | measured |
|---|---|
| perceived hue shift | **−4.34° mean**, range **−10.75° … +1.15°** (systematically *browner*) |
| **verdict flips** | **2 of 61** — `oilR_001` (70.11° → 64.03°) and `oilR_002` (70.34° → 64.10°), both UNDER-ROASTED → PERFECT-ROASTED across the 66° edge |
| shift is sample-dependent | the greenest oils move most (`oilG_002` −10.75° at hue 86.7°), the brownest least (`NowSBudget` −1.52°) — so it is a **compression of the hue scale, not an offset** |
| window narrowing (§17.6/3) | the naive floor cut bins in **14 of 61 runs**, worst `oilB_002` **1520 → 1421** (−6.5 %); `floor = 0.01^γ` restores **all 61 exactly** |

⇒ **§17.3's "the pumpkin verdict is unchanged" is true only of the peak-RATIO verdict.** The `PumpkinOilPlugin`
hue verdict is not gamma-neutral, and the bands were anchored against gamma-encoded data exactly as the Roast
Ampel 4.4 threshold was. Script: **`diagnostics/gamma_l0_gate.py`** (re-runnable, reads only the archived PDFs; it also prints
the naive-vs-fixed floor comparison).

**⚠ OPEN DECISION (Edwin):** re-anchor `VerdictOp`'s 47/66 to the linearized hue scale, or leave them. Not
decided here — it is a product-semantics recalibration against real oils, the same kind of call as 2.8 → 4.4.
Note a uniform offset is **not** right: the shift is scale-compressing, so the honest re-anchor maps the two
band edges through the same replay rather than subtracting 4.34° from each. Untouched meanwhile: the DEV/Roast
Ampel ratio path (bit-identical), and every absorbed-colour chip.

#### 17.8.2 What was built

| Ph | As-built |
|---|---|
| **L1** | `SpectralColorUtil`: module-level float32 LUT + `_LUT_CACHE`/`lutFor`-style cache, `captureGamma()`, `captureDecodeDescriptor()`, `gammaLut()`, `decodeGammaArray()` (uint8 → LUT fast path, else closed form), `encodeGammaFraction()`. γ is a parameter, never singleton state (§17.7/13). New `tests/test_gamma_decode.py` — 10 tests, incl. fixed endpoints, strict monotonicity, float32 dtype, encode/decode inverse, 8-bit round-trip, and no-leak on a γ override. |
| **L2** | `ImageSpectrumAcquisitionLogicModule.__reducedColumnValues` → **`__reducedLinearColumnValues`**; the LUT decode on the uint8 ROI slice **replaces** `.astype(np.float32)`, after the slice. Calibration branch carries the DN-domain comment and is untouched. |
| **L3** | `TransmissionLogicModule.DEFAULT_REFERENCE_FLOOR_FRACTION` 0.01 → **6.31e-5** (= `0.01^2.2`), with the measured justification inline. |
| **L4** | `SpectrumToVirtualImageUtil` gamma-**encodes** (`encodeGammaFraction`); the §15 no-op invariant comment is superseded in place. `ENCODER_VERSION v1 → v2`, sets **re-baked** (`pumpkinoil_{under,perfect,over}_v2`, `set.json` now carries `captureDecode`), 3 tests re-pointed. v1 folders left on disk for rollback. |
| **L5** | (a) **Relative colour ceiling**: `EvaluationColorUtil.RELATIVE` + `RELATIVE_CEILING_MULTIPLE = 2.0` (cap = 2× the spectrum's own p95); `DevSpectralPlugin`'s four `3.0`s are gone. (b) `DIM_FRAME_SCALE_FLOOR` 0.02 → **0.045** (= ×γ) so C1 keeps its DN-domain aggressiveness. (c) **`captureDecode` stamp** injected into the embedded `workflow.json` header by `WorkflowReportBuilder` — no `-model` dependency, **no DB column, no migration**. (d) **Low-DN guard**: `CAPTURE-LOWDN role=… minDn=… at=…nm` printed per capture, minimum mapped back through the decode's inverse into camera DN, flagged below 16 DN. |
| **L5b** | **Android app_src recorded as knowingly stale** — not mirrored. `diff -rq` shows **179 differences across 139 files**: `android/{server,spike}/app_src/` are July-3 build snapshots, not maintained mirrors, so mirroring 3 files would have produced exactly the half-synced tree §17.7/17 warns about. The next APK build must re-sync the whole tree. |
| **L6** | **PENDING — needs Edwin + the ELP.** |

#### 17.8.3 Verification beyond the suite

- **Relative ceiling, on real spectra** (`diagnostics/gamma_ceiling_check.py`): dormant on every archived run, as-is *and*
  decoded (0 clamped bins of 1305), while it independently **reproduces §17.5(4)**: under the old absolute 3.0 a
  decoded `NowSBudget` clamps to 298.2° → 296.9° / chroma 63.2 → 59.0, under RELATIVE it stays exactly
  298.2°/63.2. A synthetic `T→0` spike (5 bins at A=40) still gets caught: hue error +1.8° uncapped → +0.4° capped.
- **`test_virtual_device_image_roundtrip` green** = the L4 gate: decode and encode are genuine inverse halves
  (§17.7/18 — the dim-frame test *cannot* prove this, and stayed green throughout).
- **One test changed, deliberately**: `test_pumpkin_oil_spectrum_to_color_eval`'s low-reference-guard case
  pinned the old constant on synthetic data. It now asserts **both** halves of the new policy — a bin at 1e-5 of
  peak is still masked, and one at 0.5 % of peak (≈11 % of peak DN) **survives**, which is precisely the class of
  bin the old constant deleted at the spectrum's edges.

#### 17.8.4 Rig runbook for L6

1. **Expect the live trace to look dimmer in the mid-band** — decode maps DN 245 → 233 but DN 120 → 49. That is
   linear light, not a regression (§17.7/15).
2. Calibration must still pass **~0.6 nm** — it is in DN by design and should be bit-unchanged.
3. Pigment ratio must match a pre-decode run to ~0.2 % (§17.5.3's Jensen gap); colour chips visibly richer.
4. Watch the new `CAPTURE-LOWDN` line: if `minDn` sits near 5 the sample is too concentrated (the protocol change
   in `SPEC_capability_proof.md` §7.3 moves it to ~16).
5. **The virtual-spectrometer folder setting must be re-pointed to a `_v2` set** — a `v1` folder now decodes
   γ-distorted (that is what the version bump is for).

#### 17.8.5 First field run — two things linearization is NOT guilty of *(2026-07-27)*

Edwin's first post-§17 pair (`NowSteirerkraftA/B`) raised two suspicions. Both were replayed off the archived
PDFs; the full diagnosis lives in **§16.7** (it is reference drift). Recorded here because both suspicions land
naturally on this section:

1. **"At 440 nm practically no light comes through."** Measured, in camera DN: the sample bottoms at **52 DN**
   (A) and **38 DN** (B) of 255, against a ~177 DN reference — healthy, and *brighter* than the pre-§17 run
   (10 DN). What changed is the PLOT: 52 DN decodes to **7.6 of 255 in linear light (3 % of the plot height)**,
   so a perfectly good band now looks extinct. This is §17.7/15 arriving exactly as predicted, on the first
   real run. The new `CAPTURE-LOWDN` line is the antidote — it reports DN, and 38–52 DN is far above its 16 DN
   warning. *(It also strengthens the case for §17.7/15's other half: show the capture-panel live plot in DN.)*
2. **"Should absorbance be normalized before taking ratios?"** It makes **no difference — measured at 8.9e-16**
   (`gamma_dilution_diverge.py`). A ratio of two band means from the *same* spectrum is already scale-free, so
   every multiplicative normalization (peak, area, SNV's scale half) cancels exactly — the same algebra that
   makes the ratio dilution-invariant and gamma-invariant. Only an **additive** correction can move a ratio,
   and here it moves it the wrong way (§16.7): subtracting the baseline shrinks an already-tiny denominator.

---

## 18. The derived documentation artifact — `DOC_capture_fidelity.md` → internal PDF  *(as-built 2026-07-26)*

This spec is the **source of truth**; it is also long, chronological and written for whoever is doing the work.
Edwin asked for a second view of the same material: a **textbook-style document** giving the big picture without
the derivations, readable by three audiences at once — himself as developer, his chemist colleague, and the lab
that receives a Spectracs report (the PDF can be sent alongside one). That artifact now exists.

```
source of truth   docs/DOC_capture_fidelity.md                 <- markdown master, edit HERE
generator         docs/tools/build_capture_fidelity_pdf.py
output            ../spectracs-docs/internal/Spectracs_CaptureFidelity.pdf   (~30 pages, self-contained)

    python3 docs/tools/build_capture_fidelity_pdf.py            # regenerate
    python3 docs/tools/build_capture_fidelity_pdf.py --out /tmp/preview.pdf --html
```

**It is documentation, not specification.** It creates no work items and holds no authority: every claim in it is
a summary of a section here, and its Appendix B is the index back. When a decision in this spec changes, update
the document and re-run the generator — the PDF is never hand-edited.

**Structure** (Edwin's brief: abstract first, then reference material, then the argumentation): §1 is a
**standalone summary** — abstract + a one-table overview of every decision (`§ | what we do | what led us there`)
— so a reader gets the impression without reading on; §2 is the **foundations/reference** part (why the
brightness law exists, its variants, what `T = S/R` cancels, spatial vs temporal outliers, what a white-LED
spectrum is); §3 is **one chapter per decision**, each as *problem → what we measured → decision → what it
costs*, covering the topics Edwin listed: grey value `max(R,G,B)`, the brightness law, camera warm-up, the
sigma-clipped mean and dim-frame rejection, dark frames, auto-exposure, fixed white balance — plus the resolution
pin, the ROI window and the sample dilution; §4 is **what we deliberately did not do**; §5 the as-built settings
table; §6 open items; **Appendix A a knowledge base** (7 entries: gamma/sRGB in depth, Beer-Lambert and the
algebra of ratios, robust statistics, DN/quantisation/noise, Bayer/demosaic/QE, white LEDs/CRI, spectrum→colour),
cross-linked from the exact spot in the main text by clickable "→ Background" boxes.

**Toolchain.** Markdown → styled HTML → headless Chrome `--print-to-pdf`, matching the existing
`build_capability_status_pdf.py`, so the only dependency stays Chrome (no pandoc, no weasyprint). The generator
carries a small markdown-subset converter (headings, lists, GFM tables, fenced code, block quotes as call-outs,
data-URI images resolved against the repo and `spectracs-references/`, `<!--TOC-->` / `<!--PAGEBREAK-->`) and
**fails the build on a dangling internal link** — dead links are silent in a PDF, so they must not be shippable.

**Figures** are embedded from `spectracs-references/tmp/`: `lamp_spd_annotated.png` (§2.6) and
`sensor_warmup_curve.png` (§3.6). The PDF is therefore self-contained and portable as a single file.
