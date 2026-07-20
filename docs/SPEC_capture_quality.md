# SPEC — Capture quality & fidelity (ROI clamp · robust reduction · dark level · normalization)

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
rare hot pixel (so no bad-pixel map either).

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
