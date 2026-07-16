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
