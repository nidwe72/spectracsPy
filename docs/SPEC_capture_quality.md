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

### 16.7.0 ⭐ SUMMARY OF THE 2026-07-27 INVESTIGATION — read this first

§16.7–§16.9 were written as the day unfolded, so they are chronological and long. This is the consolidated
result. Everything below was measured on Edwin's rig with `diagnostics/cuvette_reseat_probe.py` and the same
paired untouched control, or replayed from the archived report PDFs.

**The question:** three same-sample runs scattered **CV 14.2 %** where the 2023 series held **3.6 %**.
Same instrument, same jar handling.

#### The error budget — instrument side

| source | tilt (corrupts the ratio) | where measured |
|---|---|---|
| **jar seating + its own optics** | **2.81 %** | §16.9.3h (2.84 % total minus the cone's 0.39 %) |
| holder nudge | 0.56 % | §16.9.3f |
| camera nudge | 0.42 % | §16.9.3d |
| cone lifted off and replaced | 0.39 % | §16.9.3h |
| untouched control | **0.04–0.09 %** | every run |

**⇒ the jar is ~98 % of the variance.** The cone joint, which has a defined seat, is *more* repeatable than a
1 mm nudge of the camera — **the fix is a keyed seat for the jar, not more careful handling.**

#### What the tilt budget costs the PEAK RATIO

The tilt figures only matter once converted: `ratio error = 0.434 × tilt / A_Q`. At the current recipe
(`A_Q = 0.225`), and — crucially — remembering that **a real measurement contains TWO jar operations**, the
blank fill and the sample fill:

| source | tilt | → ratio error |
|---|---|---|
| **jar seating** (per operation) | 2.81 % | **5.4 %** |
| jar **level** (per operation, additive offset — does *not* cancel) | 1.68 % | 2.4 % |
| → combined, per jar operation | | **5.9 %** |
| → **two operations (R and S), independent** | | **8.4 %** |
| holder + camera + cone together | | 1.5 % |
| **PREDICTED total** | | **8.5 %** |
| *observed*, 8 clean runs at this recipe | | *11.2 %* |

The budget accounts for **~76 %** of what was actually measured; the remainder is sample prep (drop count, fill
level) and the heavy tail. **Close enough to trust the ranking, not close enough to claim it is complete.**

**What a keyed jar seat would buy** — assuming the jar becomes as repeatable as the cone joint already is
(0.39 % tilt / 0.25 % level, both measured):

| | σ of the pigment ratio | 4.2 vs 4.8 (gap 13.3 %) | your 2026 pair (gap 24 %) |
|---|---|---|---|
| today, one measurement | 8.5 % | 78 % correct | 92 % |
| today, **median of 3 fills** | 4.9 % | 91 % | 99 % |
| **keyed seat**, one measurement | **1.9 %** | **100 %** | 100 % |
| keyed seat + median of 3 | 1.1 % | 100 % | 100 % |

⇒ **The keyed seat is worth ~4.4×, and it is the only single change that makes a one-shot borderline call
reliable.** The median of 3 is worth ~1.7× and costs nothing but time — do both, and the borderline case stops
being borderline. *(2023 for scale: gap 41 %, σ 3.6 % — never in doubt.)*

#### The error budget — sample side

| | 2023 series | 2026 fresh oil |
|---|---|---|
| `A_Q` (the denominator) | 0.172–0.247 | 0.212 |
| of which broad **baseline** | ~50 % | **72 %** |
| **pigment** content | 0.079–0.135 | **0.059** |
| error amplification `0.434/A_Q` | 2.1 | 4.5 → **1.9** after the recipe fix |

**⇒ the 2026 oils are not the 2023 oils.** Only the *pigment* half of the denominator co-varies with the Soret
band and cancels in the ratio; the baseline half does not. Halving the pigment content doubles the damage from
the same physical disturbance (§16.7.2l).

#### What was ESTABLISHED

1. **The error model:** `A_measured = k·A_true + b`, with `b` **coherent across wavelength** — proved by the
   bin-scaling test (widening a band makes the CV *rise*, where random noise would make it fall, §16.8.2/§16.7.2j).
   **⇒ more bins, more smoothing, longer bursts and more frames cannot touch this error.**
2. **It is heavy-tailed** — "usually fine, occasionally awful" (tilts 6.71 · 0.82 · 1.05 · 2.10 · 1.11 · 5.23).
   **⇒ report the MEDIAN of 3–4 fills, never the mean** (§16.7.2f).
3. **Waiting does not help**: 76 % of each disturbance is permanent; the jar lands in a *new* optical state and
   holds it (§16.7.2b).
4. **The live plot must be drawn in DN** — the linear trace hides the usable-but-dim range in its bottom 4 % and
   directly caused a series of over-diluted measurements (§16.7.2e). **Implemented.**
5. **The recipe**: 0.333 drops/ml, batched as **18 ml + 6 drops**, verified to put the darkest bin at 18–26 DN
   and the amplification back to 1.9 (`SPEC_capability_proof.md` §7.3).

#### What was RULED OUT — each with its evidence

| suspect | verdict | evidence |
|---|---|---|
| the brightness law (§17) | **innocent** | undoing the decode changes S/Q by **0.00e+00** |
| normalizing before the ratio | **no-op** | 8.9e-16 |
| sample ageing | **innocent** | the three runs go up then down, not monotone |
| narrower or wider bands | **rejected** | 560–580 is optimal in *both* directions (§16.7.2i/j) |
| moving the denominator band | **rejected** | d 10.39 → 4.03 (§16.8.1) |
| ΣRGB instead of max | **rejected** | d 10.34; a *gated* sum collapses to 3.33 (§16.8.2) |
| de-baselining, on stable data | **rejected** | d 9.79 vs 10.39 (§16.7.2f) |
| the diffuser | **no effect** | F = 1.47, p = 0.29 (n=5); dirty and loose it *adds* ~1.5 % level noise |
| camera alignment / cone joint | **minor** | 0.42 % / 0.39 % against the jar's 2.81 % |

#### The two live leads

- **SNV difference** — `d_today = 13.52` against the raw ratio's 1.55, and it pulls the *observed* bad seating
  (run 003, a 3.7 σ outlier) back to **0.5 σ**. It is the textbook correction for the error model derived above,
  not a fit. **Needs validation on data it was not chosen from** (§16.7.2k).
- **Sample clarification** — untested, cheap: let the dilution stand overnight or filter it, and watch `A_red`
  fall. It attacks *why* the denominator is fragile rather than the disturbance that exploits it (§16.7.2l).

#### Claims made and WITHDRAWN during the day *(kept deliberately — each was overturned by the next measurement)*

| claim | why it fell |
|---|---|
| "it is the lamp — phosphor droop" | the drift probe's sign was **opposite** (§16.7.1) |
| "the diffuser tightens the blank 3×, the scatter 6×" | an n = 2 artefact; gone at n = 4 (§16.7.2g) |
| "level cancels in the ratio" | true only of the *path* half; a throughput mismatch does **not** (§16.7.2c) |
| "the holder is in the beam" (from the level channel) | that was the moving **dirt**; the *tilt* evidence survives (§16.9.3f) |
| "440–450 is floor-limited, so drop it" | it is the **steadiest** sub-band of all (§16.7.2i) |
| "the green→red crossover hurts the Q band" | 570–580 is the *less* noisy half (§16.7.2i) |
| "turbidity is excluded" | excluded only as *Rayleigh*; large-particle **grey** scattering fits (§16.7.2l) |

#### ▶ Next, in order

1. ~~Brown-2026 oil, 4–6 fills~~ — **DONE (§16.7.2o)**: brown is *not* steadier (CV 11.4 % vs 11.2 %), the
   classes separate at only **d = 1.23**, and **~26 % of single verdicts would be wrong today.**
2. **▶ Keyed jar seat + aperture, one printed part** — now the critical path, not an optimisation: it takes the
   error rate from 26 % to ~0 % (§16.9, §16.7.2o).
3. **Sample clarification test** — independent of the hardware.
4. **SNV validation** — both classes, n ≥ 15, one optical configuration, fresh data.
5. **Decide the 47/66 hue bands** — the L0 gate found 2 of 61 archived runs flip under linearization (§17.8.1);
   still Edwin's call.

---

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

#### 16.7.2o ▶ THE BROWN OIL, 6 FILLS — the next-step measurement, and it is sobering *(2026-07-27, `tmp/20260727C`)*

The measurement §16.7.2m called decisive. Six fills of the 2026 **brown** oil, same recipe, same session:

| metric | GREEN (n=8) | BROWN (n=6) | **d** |
|---|---|---|---|
| **S/Q** | 4.723 ± 0.529 | 4.105 ± 0.467 | **1.23** |
| SNV difference | 2.597 ± 0.034 | 2.515 ± 0.072 | 1.54 |

**Three findings, none of them comfortable.**

**1. Edwin's hypothesis is NOT confirmed for the 2026 oils.** Brown CV **11.4 %** against green **11.2 %** — the
brown is no steadier. It held in 2023 (2.0 % vs 2.8 %) because the brown oils then carried 1.7× the pigment in
the denominator; the 2026 brown does not have that advantage (baseline share 68 % vs the green's 72 % — barely
different, and both far above 2023's ~50 %).

**2. The classes barely separate — d = 1.23.** Against the 4.4 threshold, on a **single** measurement:

| | green reads BROWN | brown reads GREEN |
|---|---|---|
| one measurement | **27 %** | **26 %** |
| median of 3 fills | 15 % | 14 % |
| **keyed jar seat (σ 1.9 %)** | **0.0 %** | **0.0 %** |

**A quarter of verdicts would be wrong today.** The means are on the correct sides of 4.4 — the metric and the
threshold are right — but the scatter swamps a 15 % gap. **The keyed seat is not an optimisation here; it is
what makes the instrument usable on these oils.**

**3. ⚠ The SNV enthusiasm of §16.7.2k must be re-scaled.** That section quoted `d_today = 13.52` — computed with
the **2023** class gap (0.44) against today's SD. **The actual 2026 pair is 5.4× closer in SNV space** (gap
0.082), so its real `d` is **1.54**, only marginally ahead of the raw ratio's 1.23. SNV still corrects the
observed bad seating (§16.7.2k's run-003 evidence stands) and still beats S/Q — but it is **not** a substitute
for fixing the instrument, and the "9× better" framing was an artefact of borrowing a gap from a different pair
of oils.

**A recipe note:** the brown ran at **13–16 DN** in its darkest bin, below the 20–40 target — it absorbs more
than the green at the same dilution (`A_Soret` 1.25 vs 0.99). **Dilute the brown ~25 % further**, or the Soret
band starts trading into the quantization floor.

⇒ **The next step is no longer a measurement — it is the keyed jar seat.** Every alternative has now been tested
and none of them substitutes for it: not the bands, not the reduction, not the diffuser, not the metric, not
waiting, not averaging alone.

#### 16.7.2p SNV applied to BOTH 2026 classes — halves the errors, does not rescue the verdict *(2026-07-27)*

§16.7.2k proposed SNV on the green set alone. Applied to both — 8 green fills (`20260727B`, 003 excluded for
documented cause) and 6 brown (`20260727C`):

| metric | green | brown | d ± SE | **misclassified (leave-one-out)** |
|---|---|---|---|---|
| **S/Q** | 4.722 ± 0.529 | 4.105 ± 0.467 | 1.23 ± 0.59 | **4 / 14 = 29 %** |
| **SNV difference** | 2.597 ± 0.034 | 2.515 ± 0.072 | 1.55 ± 0.61 | **2 / 14 = 14 %** |

**SNV halves the error rate — but the two are statistically indistinguishable.** The `d` difference is 0.32 and
each carries SE ≈ 0.6, so on this pair of oils the metric choice is **not** resolved by the data; only the
counted errors favour SNV, and 2-vs-4 out of 14 is itself a thin margin.

**The failure mode is asymmetric, and that matters for a product.**

```
   SNV  green 2.563 2.572 2.580 2.581 2.594 2.604 2.611 2.672
        brown 2.375 2.516 2.527 2.537 2.563 2.572   <- only the top TWO browns reach into the green range
```

**SNV classifies every green correctly (0/8); all its errors are browns leaking upward** — the green set is 2×
tighter in SNV (SD 0.034 vs 0.072). For an Ampel whose job is to *catch* over-roasted oil, that is the **wrong**
asymmetry: it never cries wolf, and it misses one brown in three. S/Q's errors are spread both ways (3 green,
1 brown).

**With the median of 3 fills**, same thresholds: S/Q → 15.6 % / 12.6 %; SNV → **1.9 % green / 16.1 % brown**.
SNV's asymmetry survives averaging, because averaging cannot fix a *gap* that is only 1.1 brown-SDs wide.

**⚠ One outlier behaves differently in the two sets, and it bounds what SNV can do.**

| | S/Q | SNV |
|---|---|---|
| `B/003` — documented bad seat | 6.691 (3.7 σ) | **2.615 — corrected, mid-pack** |
| `C/006` | 3.223 | **2.375 — still the low outlier** |

SNV removes an offset-and-scale error (`B/003`, a seating fault) but **not a change of spectral shape**. `C/006`
also carried `A_Q = 0.379` against 0.25–0.31 for its siblings — a genuinely different spectrum, not a
mis-seating. **So SNV is a correction for the disturbance, not a repair for a bad sample.**

⇒ **Verdict on the metric question: keep S/Q for now.** SNV is ahead on counted errors, behind on the asymmetry
that matters, and level with S/Q statistically. Neither reaches a usable error rate on these oils, because both
are limited by the same 11 % instrument scatter — **which is the keyed seat's job, not the metric's** (§16.7.2o).

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

## 16.9 Optical hardening — the aperture mask and the fixed diffuser  *(DESIGN, 2026-07-27; build on explicit request)*

Three small parts that attack the dominant error (§16.7.2n). They are **independent**, solve **different**
problems, and stack:

| part | fixes | error it removes |
|---|---|---|
| **A — aperture mask** | *which* light is measured | wall-guided ring light (stray light), and the dependence on jar centring |
| **B — diffuser mount** | *how* the light may arrive | angular/positional sensitivity of the grating response |
| **C — kinematic jar seat** (§16.9.4) | *at what ANGLE* the sample sits | the re-seating tilt — **98 % of the instrument variance** |

### 16.9.1 The one rule that decides whether the OPTICAL parts work

> **Parts A and B mount to the HOLDER or the CONE. Neither ever touches the jar.**

This is the whole lesson of §16.7.2g: a diffuser resting on the jar is **lifted and re-seated with it**, so it
becomes part of the disturbance instead of a shield from it — which is why its A/B came out null (n=5, p = 0.29).
An aperture glued to the jar would fail identically. Mounted to the holder, both parts define a **fixed optical
geometry that the jar moves through**, rather than a geometry the jar carries with it.

**Part C is the deliberate exception, and not a violation of the rule.** The seat (§16.9.4) is the one part that
*must* touch the jar — but it touches it in order to **define the jar's angle**, not to ride along with it. The
distinction is the same one: a component that the jar *carries* inherits the disturbance; a component the jar is
*registered against* removes it. A and B are geometry the jar passes through; C is the datum it returns to.

### 16.9.2 Part A — the aperture mask

**What it does.** A black, matte disc with a central hole, held **above the jar** in a fixed position, so the
spectrometer can only see the central region of the liquid. Light that entered the acrylic **wall** — refracted,
guided, and emerging as the rings Edwin observed — is blocked before any optic can mix it in.

**Why it matters more than it looks.** Wall light never crossed the full liquid depth, so it is stray light: it
**biases high absorbances low** (capping `A_max` at `−log10(f)` for a stray fraction `f`), it hits the **Soret
numerator** hardest, and **its share changes every time the jar is re-seated**. A fixed aperture also **pins the
measured area**, so centring errors stop mattering — the jar can sit a millimetre off and the same patch of
liquid is measured.

**Geometry (to be finalised on the rig).**
```
jar outer diameter        30 mm            (measured, photo 2026-07-27)
jar depth (base)          13 mm
wall thickness            MEASURE  — the ring source; aperture must clear it with margin
aperture hole             start 16 mm, adjustable      <- ~5 mm clear of a ~2 mm wall on each side
mask thickness            2-3 mm, opaque
finish                    MATTE BLACK on the underside (a shiny mask re-reflects into the beam)
position                  fixed to the holder, centred on the OPTICAL axis, not on the jar
standoff                  as close to the liquid surface as handling allows (a distant mask lets
                          wall light sneak back in at an angle)
```
**Notes.** Spectrally neutral by construction — it sits in **undispersed white light**, so it cannot tilt the
spectrum the way a throughput change does. Print in black PETG/PLA, or line a printed ring with matte black
paper. Make the hole a **separate insert** so 12 / 16 / 20 mm can be swapped without reprinting the holder.

### 16.9.3 Part B — the diffuser mount

**What it does.** Holds the frosted glass **at the spectrometer entrance, immediately before the slit**, rigidly
attached to the upper cone / spectrometer mount.

**Why at the slit and not on the jar** (the non-obvious half, §16.7.2n): a diffuser in the **jar's plane**
becomes an extended source there and smears the disk *and the rings* together — it can make stray light **worse**
while making the field *look* more uniform, which may be exactly what Edwin observed. At the slit it can only
scramble light that **already arrived**, and it homogenises the **angular** distribution entering the grating —
which is what makes the response independent of how the beam arrives. This is standard instrument practice
(fibre spectrometers use a cosine corrector at the entrance for the same reason).

**Constraints.**
```
position     immediately in front of the slit, covering the full entrance aperture
mounting     rigid to the cone/spectrometer; NEVER removed for a jar change
material     the frosted camera glass already on hand
light cost   measured: exposure 64 -> 256 (~4x). Affordable — headroom to 500 (§14.9), and the
             untouched control sits at 0.02% tilt (§16.7.2c), so SNR is not the limiting factor
risk         RESOLUTION: filling the acceptance cone can blur the slit image -> re-verify calibration
```

### 16.9.3b The EMPTY-BEAM measurement (Edwin's idea) — what it can and cannot answer

Measuring the lamp **with no jar at all** is worth doing, but for two specific purposes rather than as a general
reference.

**⚠ First the limit, so it is not over-read.** The jar is a **refracting slab**: ~4 mm of acrylic at n ≈ 1.49
plus ~10 mm of isopropanol at n ≈ 1.377 shift the focal plane by **≈ 4 mm** when it is removed. So *no jar* is a
**different optical configuration**, not a neutral baseline — an empty-beam spectrum cannot serve as the
reference for computing "the jar's transmission".

**What it IS good for:**

**(a) Separating instrument drift from jar handling.** Run `reference_drift_probe.py` with **no jar in the
beam**. Whatever drifts then is lamp + optics + sensor alone. Compare with the same run *with* a jar left
untouched: the difference is the jar's own contribution to drift (thermal creep in the acrylic, liquid settling,
the holder relaxing). Today we cannot tell those apart.

**(b) ⭐ Sizing the ring problem directly — the measurement that decides whether the aperture is worth
building.** Four captures at **one pinned exposure** (chosen so the brightest cell does not clip):

```
                       no aperture      with aperture
     no jar                 A                 B         <- pure geometric vignetting  = B/A
     jar + blank            C                 D         <- vignetting + ring blocking = D/C

     ring fraction   f_ring = 1 − (D/C)/(B/A)
```

Because the rings exist **only** when the jar is present, dividing out the no-jar column removes the aperture's
plain geometric vignetting and leaves the wall-guided light alone. `f_ring` is then literally *the share of what
the slit collects that came through the jar WALL rather than the liquid*. **A few percent would make the
aperture the highest-value part in §16.9**, and it also predicts how much of the re-seat error it can remove —
`f_ring` is the part that changes when the jar moves.

**⚠ Corrected by Edwin (2026-07-27): there are TWO rings, not one.** The lamp itself throws a ring — light
diffusing through the outline of its own disk — which is present **with or without the jar**, and which Edwin
describes as *"more calm"*. That does not break the 2×2; it explains what it measures:

| ring | present | behaviour | what it costs |
|---|---|---|---|
| **lamp ring** | always | fixed — the lamp does not move | **ACCURACY**: a constant stray fraction compresses high absorbances (the Soret most) |
| **jar-wall ring** | only with the jar | changes on every re-seat | **REPRODUCIBILITY**: it is the run-to-run wander |

The lamp ring appears in **both columns** of the 2×2 and therefore **cancels in the ratio-of-ratios** — so
`f_ring` still isolates the jar's *marginal* contribution, which is precisely the part that varies with seating.
(First-order: the jar also refracts the lamp ring, so the cancellation is approximate, not exact.) A calm,
constant ring is the *benign* kind — it biases the number without scattering it, and the same aperture removes
both.

**Protocol notes.** One exposure for all four cells (removing the jar raises the level, so pick the exposure on
cell A). Do not auto-expose per cell — that would divide out the very thing being measured. Capture the ROI
**image** as well as the spectrum: with and without the jar the rings should be directly visible in the
difference, which is a useful sanity check on `f_ring` before trusting the arithmetic.

**⭐ Run the block TWICE — with the diffuser and without (Edwin, 2026-07-27).** The diffuser costs ~4× light, so
one exposure cannot span both; instead pin an exposure **per block**. `f_ring` is a ratio-of-ratios *within* a
block, so it stays exposure-independent and the two blocks remain comparable.

```
   block 1: NO diffuser      (lamp -> jar -> slit)          exposure pinned on its own cell A
   block 2: diffuser ON JAR  (as Edwin has it today)        exposure pinned on its own cell A
   -> f_ring(no diffuser)  vs  f_ring(diffuser on jar)
```

**This is a falsifiable test of §16.7.2n's central claim.** If a diffuser in the jar's plane smears the rings
across the whole field, then with it fitted the aperture can no longer *selectively* block them — the ring light
is everywhere — so **`f_ring` should come out SMALLER with the diffuser on the jar while the contamination is
unchanged or worse**. If instead `f_ring` is the same in both blocks, the smearing argument is wrong and the
diffuser is optically neutral about placement (leaving only the mechanical reason to move it). Either way the
answer is one extra block of four captures, and it decides where the diffuser belongs on evidence rather than on
my reasoning.

### 16.9.3c Probing ALIGNMENT instead — nudge the camera *(Edwin, 2026-07-27; no hardware needed)*

The 2×2 needs an aperture, which does not exist yet. Edwin's alternative is better for the question that matters
most: **disturb the camera instead of the jar.** It perturbs exactly the variable the diffuser is supposed to
desensitise — where the light arrives and at what angle — so it measures what the diffuser buys **directly**,
rather than inferring it from a seating experiment that the diffuser was never mounted to influence.

Implemented as `cuvette_reseat_probe.py --disturb camera`. Everything else is unchanged: the same paired design
(disturbed round vs untouched control over the same timescale), the same settling window, the same tilt / level /
implied-ratio reporting. Only the prompt differs:

```
    --disturb jar      TAKE THE CUVETTE OUT AND PUT IT BACK IN            (§16.7.2, already measured)
    --disturb camera   NUDGE THE CAMERA / UPPER CONE ~1 mm, same way      (alignment sensitivity)
    --disturb none     CHANGE NOTHING                                     (null run — the floor)
```

**The comparison to run, two blocks of 6:**

```
    block 1   --disturb camera,  NO diffuser        -> alignment sensitivity, bare
    block 2   --disturb camera,  diffuser fitted    -> alignment sensitivity, diffused
```

**If the diffuser does what it is supposed to, block 2's tilt collapses toward the untouched control.** That is
a direct measurement of its value on its own terms — unlike §16.7.2g, which asked a diffuser *resting on the
jar* to fix a *jar* disturbance and unsurprisingly found nothing.

**Protocol discipline.** Nudge by a **similar amount and in the same direction** every round — the between-block
comparison only holds if the disturbance is comparable, and "a little bit" is not otherwise reproducible. **Do
not touch the jar at all** during these runs. A `--disturb none` block is worth one run as the floor, since
today's controls have ranged 0.02–0.26 % depending on configuration.

**What each outcome means:**

| result | reading |
|---|---|
| bare block shows a large tilt, diffused block small | the diffuser works; mount it at the slit (§16.9.3) and the alignment error goes away |
| both blocks small | alignment is not a significant error source here — the seating error is about the jar's own optics (wall rings, meniscus), and the aperture matters more than the diffuser |
| both blocks large | the diffuser does not fix alignment on this rig; look to mechanical rigidity of the two-cone stack instead |

#### 16.9.3d RESULT — alignment is NOT the problem; the jar is *(2026-07-27, 6 camera nudges, no diffuser)*

`--disturb camera`, 6 rounds, jar untouched throughout, ~1 mm nudges of the upper cone:

| disturbance | tilt mean | tilt max | implied ratio swing |
|---|---|---|---|
| **jar re-seat** (§16.7.2c) | **2.84 %** | 6.71 % | 9.6 % |
| **camera nudge** | **0.42 %** | 1.42 % | 1.3 % |
| untouched control | 0.09 % | 0.23 % | 0.1 % |

**The jar is ~7× the error source the camera alignment is** — and the practical gap is far wider than that,
because **in normal use the camera is never touched while the jar is moved for every single measurement.**

⇒ **This lands on the third row of §16.9.3c's outcome table.** Alignment sensitivity is real but small, so the
**diffuser's ceiling is ~0.4 % of tilt** — it cannot fix a 2.8 % problem it does not touch. **The aperture
(the jar's own optics: wall rings, meniscus) is the part worth building; the diffuser mount is a distant
second.** That reverses the priority §16.9 was written with, on evidence, before anything was printed.

**A second observation, useful for the mount design.** The response is **threshold-like, not proportional**:
four of the six nudges produced nothing above the noise floor, and two produced 0.9 % and 1.6 %. That is the
signature of **play or stiction in the cone stack** — a small push does nothing until something slips, then it
stays slipped (61 % of each excursion was permanent). So the fix for alignment, if it is ever needed, is
**mechanical rigidity, not damping**.

*(Caveats: n = 6, the nudge magnitude is not calibrated, and the with-diffuser block was not run — it is now a
low priority given the ceiling above. The comparison against the jar figures is fair in kind, since both used
the same probe, the same rig, and the same paired control.)*

#### 16.9.3e Decomposing the mechanical stack — EMPTY beam *(Edwin, 2026-07-27)*

§16.9.3d measured a camera nudge with the jar in place. The follow-up removes the jar entirely and disturbs the
**stack itself**, so nothing that moves can be blamed on the jar's optics:

```
    --disturb holder   nudge the JAR HOLDER only,  beam empty
    --disturb stack    nudge the camera AND the holder, beam empty
```

**What each outcome means — and the `holder` case is the interesting one:**

| result | reading |
|---|---|
| empty **holder** nudge moves the spectrum | **the holder is intercepting light itself** — it is part of the aperture, not just a jar carrier. It then needs fixing rigidly *and* it is a candidate for the aperture function §16.9.2 wants to add |
| empty holder nudge does nothing | the holder matters only through the jar it carries — so a **keyed/clamped jar seat** is the fix, and the holder body can stay as it is |
| empty **stack** ≈ camera alone (0.42 %, §16.9.3d) | the holder adds nothing; the residual alignment sensitivity is the cone joint |
| empty **stack** ≫ camera alone | the two disturbances compound — the stack has more than one loose degree of freedom |

**Why an empty beam is the right control here** (and why it was *not* right for the ring 2×2, §16.9.3b): the
question is purely *"how much does the instrument care about its own geometry"*, which needs no sample at all.
The focus-shift objection that disqualifies the empty beam as a *reference* does not apply, because nothing is
being ratioed against a jar-in measurement — each block is compared only against **its own** untouched control.

**Expect low numbers.** The camera-with-jar block already came in at 0.42 % mean tilt against a 0.09 % control,
and the jar re-seat at 2.84 %. If the empty-beam blocks land near the control, that is a *useful negative*: it
confines the entire problem to the jar's own optics, which is what §16.9.2's aperture addresses.

#### 16.9.3f RESULT — the STACK is a real error source; the dirt was the LEVEL half *(2026-07-27)*

> **✅ RE-RUN CLEAN (no diffuser, no jar) — the conclusion SURVIVES, and the confound is now measured.**
>
> | same disturbance, empty beam | tilt mean | tilt max | **level** | control |
> |---|---|---|---|---|
> | with the dirty diffuser | 0.99 % | 1.81 % | **2.23 %** | 0.05 % |
> | **without it (clean)** | **0.98 %** | 2.07 % | **0.74 %** | 0.04 % |
>
> **The TILT is unchanged (0.99 → 0.98 %) — that error is the STACK. The LEVEL fell 3× (2.23 → 0.74 %) — that
> error WAS the moving dirt.** Physically consistent: dust is broadly **grey**, so shifting it changes how much
> light gets through but not the colour balance. The confound was real and it touched only the channel dust can
> touch. *(23× the untouched floor, 76 % of each excursion permanent.)*
>
> ⇒ **Take the dirty diffuser out.** It has never demonstrated a measurable benefit (§16.7.2g), it adds a
> level-noise channel of its own (~1.5 %), and removing it doubles the light — exposure 64 instead of 128, peak
> 205 DN instead of 114. If a diffuser is ever reinstated it must be **clean and rigidly fixed**; of the three
> properties, **immobility matters most, cleanliness second, placement last.**
>
> *(Original provisional note retained below.)* Edwin: the frosted glass was still in place during this run,
> **it carries dirt that cannot be cleaned off** (it came from an old camera lens), and **it moved when the jar
> holder was nudged.** So three things moved together — camera, holder, and a *patterned absorber* — and the
> tilt/level below cannot be attributed to the holder. A retry with **no diffuser and no jar** is the clean
> version and is the next run.
>
> **The dirt is itself a finding, and a simple rule falls out of it:** a fixed pattern in the beam is
> **harmless** — it is common to the reference and the sample, so it cancels in `T = S/R`. It only becomes an
> error source **when it moves**. As deployed (dirty, loose, riding with the jar/holder) the diffuser was
> therefore a *net negative*, which fits every null and negative result it has produced: §16.7.2g's
> indistinguishable A/B, and quite possibly the level inflation measured here. **If a diffuser is kept, it must
> be rigidly fixed — cleanliness matters far less than immobility.**

Camera **and** holder nudged ~1 mm, **no jar at all**, 6 rounds:

| disturbance | tilt | level | control |
|---|---|---|---|
| jar re-seat (jar in) | **2.84 %** | 1.68 % | 0.09 % |
| camera nudge (jar in) | 0.42 % | 0.44 % | 0.09 % |
| **camera + holder (EMPTY beam)** | **0.99 %** | **2.23 %** | 0.05 % |

**19× the untouched floor with no jar present at all** — so this is pure mechanics, and §16.9.3e's *informative*
case has landed: **the holder is intercepting light.** Adding it to the camera nudge multiplies the tilt **2.4×**
and the level **5.1×**. An empty holder cannot affect anything optically unless it is part of the aperture, so
that is what it is.

**Two consequences, one of them a correction to how the earlier numbers should be read.**

1. **The holder is already an aperture — a badly-defined one.** That settles where §16.9.2's mask belongs: it is
   not a new part bolted on, it is **the holder done properly** — a defined, centred, matte-black opening
   instead of whatever the current body happens to occlude.
2. **⚠ If a jar change also lifts the upper cone, the 2.84 % jar figure CONTAINS this.** Edwin's stack is an
   upper cone *placed onto* a lower tube; if it must come off to reach the jar, then every "jar re-seat" was
   also a stack re-seat. Decomposed: jar alone ≈ **1.85 %** (linear) or **2.66 %** (quadrature). **Open
   question for Edwin: does changing the jar require lifting the upper cone?** If yes, a rigid or hinged stack
   removes a third of the error before the aperture is even printed.

**The level number is the one to watch.** 2.23 % of throughput, and a level mismatch of that size between the R
and S captures moves the pigment ratio by **≈ 6 %** (§16.7.2c's additive-offset algebra). The stack does not
have to be *touched* between reference and sample for this to bite — it only has to **relax**, and 73 % of each
excursion here was permanent.

**RANKING of the tilt error, all measured on the same rig with the same probe and control:**

| source | tilt | note |
|---|---|---|
| **jar re-seat** | **2.84 %** | the biggest single contributor |
| **stack (camera + holder)** | **0.98 %** | 23× the floor, 76 % permanent |
| camera alone | 0.42 % | so the holder adds ≈ 0.56 % |
| untouched control | 0.04 % | |

**⚠ The open question decides whether these add or nest:** *does changing the jar require lifting the upper
cone?* If it does, the 2.84 % already contains the 0.98 %, and **making the stack rigid removes a third of the
jar error for free**. If not, they are independent and both need fixing.

⇒ **Priority:** (1) **rigid stack / hinged access** — new, cheap, and possibly nested inside the jar figure;
(2) **aperture built into the holder**; (3) **diffuser — removed for now**, on the evidence above.

#### 16.9.3g ⭐ The jar re-seat is a COMPOUND — and the split is untested *(2026-07-27)*

Edwin confirms: **changing the jar requires lifting the upper cone.** So every "jar re-seat" measured in §16.7.2
was really **two** disturbances in one operation:

```
    jar re-seat (2.84 % tilt)  =  the jar seating  ⊕  the cone lifted off and replaced
```

**The nudge figure cannot settle the split, because it is a lower bound.** §16.9.3f's 0.98 % came from a ~1 mm
*nudge*; **lifting the cone off and putting it back is a far larger disturbance than a nudge.** How the 2.84 %
divides is therefore unknown, and the possibilities are not close together:

| if a cone lift alone gives… | then the JAR itself is… | cone share of the variance |
|---|---|---|
| 0.98 % (the nudge, lower bound) | 2.67 % | 12 % |
| 1.5 % | 2.41 % | 28 % |
| 2.0 % | 2.02 % | 50 % |
| 2.5 % | 1.35 % | **77 %** |
| 2.84 % | 0 % | **100 % — the jar would be innocent** |

**⇒ The decisive measurement, and it needs no hardware: `--disturb cone`.** Lift the upper cone off and put it
back exactly as for a real jar change — same grip, same care — **with the beam empty and the jar untouched**.
Whatever that produces is the half of every jar change that is *not* the jar.

**This can invert the whole build plan.** If a cone lift alone lands near 2.5 %, then the aperture, the jar
seating, the meniscus and the wall rings are all secondary, and **the fix is mechanical access — a hinge, a
kinematic seat, or a side-loading holder that lets the jar be changed without lifting the cone.** If it lands
near the 0.98 % nudge, the jar's own optics dominate after all and §16.9.2's aperture keeps its priority.

**Do this before printing anything.** It is one 17-minute run and it decides which part gets built.

#### 16.9.3h ANSWER — the cone is innocent; it really is the jar *(2026-07-27, `--disturb cone`)*

Upper cone lifted off and replaced exactly as for a jar change, **beam empty, jar and holder untouched**,
6 rounds:

| | tilt mean | tilt max | level | control |
|---|---|---|---|---|
| **cone lift off/on** | **0.39 %** | 0.81 % | 0.25 % | 0.04 % |

**Decomposition of the 2.84 % jar re-seat, which contains this by necessity:**

```
     full jar re-seat   2.84 %      (measured)
     cone lift alone    0.39 %      (measured)
     -> the JAR itself  2.81 %      (quadrature)   — the cone is 2 % of the variance
```

**The jar's own seating and optics are ~98 % of the problem.** A hinge or side-loading holder would buy
essentially nothing. §16.9.3g's inversion scenario is closed: the aperture and the jar seat keep their priority.

**Final ranking of the tilt error**, everything measured on the same rig, same probe, same control:

| source | tilt | |
|---|---|---|
| **jar seating + its optics** | **2.81 %** | `############################` |
| holder nudge (inside the stack test) | 0.56 % | `#####` |
| camera nudge | 0.42 % | `####` |
| cone lift off/on | 0.39 % | `###` |
| untouched control | 0.04 % | |

**A pleasant surprise in there:** the cone joint is *more* repeatable than a 1 mm nudge of the camera or holder
(0.39 % vs 0.42 / 0.56 %) — a full lift-and-replace returns closer to true than a small push does. That is what a
**defined seat** buys, and it is the argument for giving the *jar* one: the cone already has a seat, the jar does
not. **The lesson generalises — the fix for the jar is a KEYED SEAT, not more care in handling.**

⇒ **Build order, now settled by measurement:** (1) **keyed / kinematic jar seat + aperture built into the
holder** — one printed part addressing 98 % of the error; (2) sample clarification (§16.7.2l), which is
independent and attacks the *fragility* rather than the disturbance; (3) everything else — cone, camera,
diffuser — is noise-floor housekeeping.

### 16.9.4 Part C — the kinematic jar seat *(DESIGN, 2026-07-27; build on explicit request)*

The part that attacks the 98 % (§16.7.2n). Per the build order above it is **the same printed part as the
aperture** (§16.9.2) — printing them separately would make their mutual alignment a second error source.

#### 16.9.4a Do this FIRST — the zero-print experiment

> **Do not re-seat the jar at all.** Leave it in the holder and change the liquid with a syringe.

This removes the dominant error source outright, costs nothing, and can run today. For the §16.10.8 dilution
series in particular the entire ≥4× concentration span can be built by **successive addition to a fixed blank**,
never lifting the jar — which decouples the dilution-invariance experiment from the hardware fix entirely.
Cost: rinse carryover. **Run this before printing anything**, both because it is faster and because it is the
cleanest confirmation that the mechanism in §16.10.1 is what we think it is.

#### 16.9.4b Why an FDM printer is good enough — repeatability ≠ accuracy

The obvious objection: the printer holds ±0.1–0.3 mm, and the error budget is **31 µm** (§16.10.1). An order of
magnitude short.

It does not matter. **A kinematic mount never has to put the jar in a *known* place — only in the *same* place
twice.** Repeatability is set by contact-point stability (surface finish, µm) and not by the absolute position of
the features. A part printed 0.3 mm off nominal still returns the jar to arc-minute repeatability, because the
seat's *job* is to be deterministic, not correct.

What is wrong today is **over-constraint**. A flat jar bottom on a flat rest admits infinitely many contact sets,
so the angle is decided by whichever dust grain or moulding high-spot wins that day. Three points admit exactly
one. That is the whole fix.

#### 16.9.4c Geometry

```
        TOP VIEW (seat plate, jar OD 30 mm — §16.9.2)

              ● ball @ 120°
         ▁▁▁▁▁▁▁▁▁▁▁▁▁
      ▁▁▀   ┌───────┐   ▀▁▁
    ▕  ▏    │ Ø16   │    ▕  ▏   ◀ wall pad (hard)
    ▕  ▏    │ clear │    ▕  ▏
      ▔▀▁   └───────┘   ▁▀▔
         ▔▔▔▔▔▔▔▔▔▔▔▔▔
        ●              ●
                ╰─ flexure pad (sprung) presses the jar
                   onto the two hard pads

   balls on a Ø25 mm bolt circle  →  r = 12.5 mm, clear of the Ø16 mm aperture (r = 8 mm)
```

| feature | value | why |
|---|---|---|
| ball bolt circle | **Ø25 mm**, 3 × 120° | outside the Ø16 mm clear aperture, inside the Ø30 mm jar rim |
| contact elements | **3 × Ø6 mm steel balls**, press-fit + CA into conical pockets | **do NOT print the contact points** — FDM layer ridges shift under load and wear |
| *preferred variant* | **3 × M3 dome-head screws into heat-set inserts** | lets you **tram the seat perpendicular to the optical axis once, then lock** — turns print tolerance into a one-time adjustment |
| rotational index | notch in the plate + sticker on the jar | a moulded jar bottom is **not flat**; three points on an irregular rim still repeat perfectly *provided the jar returns in the same rotation*. Costs nothing, probably worth as much as the balls |
| lateral constraint | **2 hard pads + 1 sprung**, at 120°, offset 60° from the balls | sprung pad = printed PETG cantilever ≈ 1 mm × 15 mm. No play, and it absorbs jar-diameter variation |
| preload | O-ring or light compression spring under the cone, **2–5 N, acting centrally** | without it the lateral flexure's friction can hold the jar off one ball |

#### 16.9.4d Print settings that actually matter

| setting | value | why |
|---|---|---|
| material | **PETG or ASA — not PLA** | PLA creeps under sustained preload and softens near the lamp |
| perimeters / infill | 4+ / 40–60 % near the contacts | a floppy plate flexes under preload and returns differently |
| orientation | plate flat, **pockets facing up** | Z is the printer's accurate axis; a sloped pocket is a layer staircase |
| pockets | conical, ≥45° walls | self-supporting, no supports to scar the contact |
| layer height | 0.15–0.2 mm | — |
| combine | **one part with the §16.9.2 aperture** | their relative alignment stops being an error source |

#### 16.9.4e Expected gain, and the honest limit

Contact stability of ~5 µm over a Ø25 mm bolt circle is 5/25000 rad ≈ **0.7 arc-minutes**, against roughly **0.5°**
today (§16.10.1) — order **40×**, with large margin over §16.10.3's target of merely reaching the cone joint's
0.39 %.

*That is the mount's own repeatability.* The real floor is set by debris and by whether the jar bottom itself
deforms under preload — which is exactly why V2 below is a gate and not a formality.

**Verification is already written**: `cuvette_reseat_probe.py --disturb jar`, run before and after. Tilt should
fall from **2.81 % toward 0.39 %**.

#### 16.9.4f Candidate — printed magnetic kinematic coupling *(noted 2026-07-27, Edwin; NOT adopted)*

**Michael Hathaway, "Kinematic Bed Mounts"** — <https://www.printables.com/model/1057179-kinematic-bed-mounts>
(`Dimple_1.5_V2.stl`, `Trough_1.5_V2.stl`). A **9–10 mm ball bearing between two printed pucks**; each puck holds
4 × 3/8" cylinder magnets that clamp the joint shut. Dimple-against-dimple = a located point; dimple-against-trough
= the ball slides along the groove. Author's BOM: 5 dimple + 3 trough prints, 4 balls, 32 magnets, high-temp epoxy;
print in ABS/PC/nylon. Designed to replace Ender 5 bed adjusters.

Recorded as a **candidate for the §16.9.4 carrier interface**, not as the design. What recommends it: correct
topology, a steel ball as the moving contact, and **magnets supply the preload** that §16.9.4c specced as an
O-ring or spring — centrally and symmetrically, which is better than the version above.

What would have to change first:

| issue | why it matters here | change |
|---|---|---|
| **4 joints** | four points on a plane is **over-constrained** — the exact defect being fixed; the author uses 4 because a printer bed is rectangular | use **3**: one dimple–dimple + two dimple–trough (Kelvin-style cone/groove/groove) |
| **printed dimple + trough** | the ball is hard, its *seats* are not; under preload plastic creeps and the contact migrates. Fine at a bed's ~100 µm, marginal against our **31 µm** (§16.10.1) | PC/nylon for stiffness; consider a hardened washer or a second ball epoxied into each seat so steel runs on steel |
| **32 magnets** | sized for a heavy heated bed at speed; excess preload is what indents printed seats | start at **one magnet per puck**, add only if the joint lifts |
| **high-temp plastic** | the author's reason is the heated bed, which we do not have | same materials, different reason: creep and stiffness, not heat. PETG probably acceptable |
| **troughs allow sliding** | deliberate thermal-expansion relief. Tolerable for us **only because §16.9.2's aperture pins the measured area**, so lateral drift does not change which liquid is read — three balls define a plane wherever they sit along their grooves | keep, but the aperture becomes a dependency rather than an option |

**No repeatability figure is quoted by the author**, and printer bed mounts typically target 50–100 µm. Three
contacts repeating to ~20 µm on a Ø60 mm carrier circle would be ≈0.019° — inside budget — but that is an
estimate, not a measurement. It enters **V2 (§16.9.5)** like any other arm before anything is built around it.

### 16.9.5 Verification — and it must be pre-registered this time

Three of today's readings were overturned by the next run (§16.7.2g, §16.7.2i, §16.7.2f). The protocol below
fixes the rules **before** the data:

| gate | test | pass condition |
|---|---|---|
| **V0** | **stray-light sizing** — measure a 3× over-concentrated sample | `A_Soret` scales linearly ⇒ stray light is small, the aperture is optional. It **flattens** ⇒ `f = 10^(−A_plateau)`, and the aperture is the highest-value part on the list |
| **V1** | **calibration survives the diffuser** — run the wavelength calibration with the mount fitted | still **~0.6 nm**, green anchor holds (§14.6). *A gate, not a formality: a diffuser at the slit can cost resolution* |
| **V2** | **re-seat repeatability**, `cuvette_reseat_probe.py`, **n ≥ 6 per arm**, exclusion = documented physical cause only | tilt and level both fall against the no-hardware baseline (3.27 % / 4.95 %, §16.7.2c) |
| **V3** | **end-to-end** — 6 fills of one sample | S/Q CV **≤ 4 %** (the level needed to separate 4.2 from 4.8, §16.7.2f) |

**Arms for V2**, in this order, so a null result is still informative: *baseline → **no-re-seat control**
(§16.9.4a, syringe fill) → seat only → seat + aperture → seat + aperture + diffuser*. Diffuser-only is optional.

The **no-re-seat control is the most informative arm and needs no hardware at all**: it is the floor the seat is
trying to reach. If tilt does *not* collapse when the jar is never lifted, the mechanism in §16.10.1 is wrong and
Part C should not be built — so run that arm **before** printing.

### 16.9.6 Consequences to plan for

1. **The threshold must be re-anchored afterwards.** Changing the optical configuration shifted the measured S/Q
   by **14 %** between the diffuser and no-diffuser sets (§16.7.2g). Fix the final configuration **first**, then
   re-anchor the Roast Ampel threshold to it, and do not compare runs across the change.
2. **Re-run the calibration** once the hardware is final (V1), and record the configuration alongside it.
3. **The DN plot is the acceptance instrument.** After the light loss, check `CAPTURE-LOWDN` still lands at
   20–40 DN with the standing recipe; if not, adjust exposure before the dilution (§16.7.2e).
4. **This does not replace the sample-side lever.** §16.7.2l's clarification test (let the dilution settle /
   filter it) attacks why the denominator is fragile; the hardware attacks the disturbance that exploits it.
   They are independent and both worth having.

---

## 16.10 Why the jar dominates — and the three levers that follow  *(2026-07-27; Edwin's three paths, answered)*

After §16.7.2o showed a **26 % verdict error rate** on the 2026 oils, Edwin's reading was that the problem may be
structural: *even if this rig's seating is fixed, another device will seat differently.* He proposed three ways
out — build every unit identically, understand why seating matters so much, or find a more robust metric. **All
three have an answer, and two of them are measured.**

### 16.10.1 The mechanism — the jar is the only element that BENDS light

Everything else in the stack merely *carries hardware*. The jar is a **refracting slab** — ~13 mm of liquid at
n ≈ 1.377 between acrylic windows — and a tilted slab **steers the beam**:

| jar tilted by | beam displaced at the slit |
|---|---|
| 0.2° | 12 µm |
| **0.5°** | **31 µm** |
| 1.0° | 62 µm |
| 2.0° | 124 µm |

A hand-spectrometer slit is **~100–200 µm** wide *(not yet measured on this rig — worth doing)*. **So a
half-degree tilt moves the beam by roughly a third of the slit width.** The slit then converts that into a
throughput change, and because the grating **disperses by angle**, the change is wavelength-dependent — which is
exactly the **tilt** that corrupts the pigment ratio.

Moving the camera by 1 mm, by contrast, moves the *detector*; the beam still fills the slit the same way. The
measurements agree: **jar 2.81 %, camera 0.42 %, cone 0.39 %** — a 7× gap that the beam-steering picture
explains and a "things wobble" picture does not.

> **⇒ The jar must be constrained in ANGLE, not merely in position.** A flat jar on a flat surface is angularly
> constrained only by the flatness of both faces and by whatever dust lies between them.

**Falsifiable, and cheap:** deliberately **tilt** the jar by a small known angle (a shim under one edge) and
compare against **translating** it by a known distance. The model predicts tilt dominates translation by roughly
the ratio above; if translation turns out to matter equally, the beam-steering explanation is wrong.

### 16.10.2 Lever A — the tilt-invariant metric *(measured, best of everything tested)*

A tilt is **an offset *and a slope*** in absorbance. That is why the earlier candidates only half-worked: a
constant-anchor subtraction removes the offset, SNV removes offset and scale — **neither removes a slope.**
Fitting a straight line through two oil-quiet windows (520–540 and 600–630) and subtracting it removes both.

⚠ **The LOO column below is SUPERSEDED — read §16.10.10's scoring note first.** Leave-one-*run*-out is
optimistic here: runs within a fill share a seating state, so holding out one run leaves its near-twins in
training. The honest figure is leave-one-**fill**-out, and on the 25-run set it is **1/25 for the linear
baseline and 9/25 for S/Q** (§16.10.12's bench). The n=14 numbers are kept as the original evidence trail.

| metric | green (n=8) | brown (n=6) | d | **misclassified (LOO — see warning)** | 2023 set d |
|---|---|---|---|---|---|
| S/Q (current) | 4.722 ± 0.529 | 4.105 ± 0.467 | 1.23 | 4 / 14 = **29 %** | **10.39** |
| SNV difference | 2.597 ± 0.034 | 2.515 ± 0.072 | 1.55 | 2 / 14 = 14 % | 6.69 |
| **LINEAR baseline** | 11.861 ± 1.055 | 9.354 ± 0.834 | **2.59** | **1 / 14 = 7 %** | **10.27** |

**Four times fewer errors than S/Q on the 2026 oils, and it keeps the 2023 separation intact** (10.27 vs 10.39) —
the only candidate to improve the bad case without paying for it in the good one. **Software only.**

*Caveats: n = 14, one pair of oils, one day; and although the linear-baseline form was chosen from the physics of
a tilt rather than from a scoreboard, it was scored on data that had already been explored. It needs the same
validation as §16.7.2k — both classes, n ≥ 15, one optical configuration, fresh data — before `PB_SORET_BAND`'s
neighbours are touched in code.*

### 16.10.3 Lever B — a kinematic (3-point) jar seat

Not "a tighter holder": **a seat that defines the jar's ANGLE.** Three hard contact points constrain tilt to a
few arc-minutes and are indifferent to dust, where a flat-on-flat interface is not. Combine it with §16.9.2's
aperture — the same printed part does both jobs, and §16.9.3h showed the target is modest: **get the jar to
where the cone joint already is (0.39 % tilt), and the verdict error rate goes from 26 % to ~0 %.**

The cone joint is the existence proof: it is *more* repeatable than a 1 mm nudge of the camera **because it has
a defined seat**. The jar has none.

### 16.10.4 Lever C — the median of 3 fills

Costs nothing but time, needs no hardware, and is the right estimator for a **heavy-tailed** error (§16.7.2f).
Worth ≈ 1.7×.

### 16.10.5 The manufacturing question — you need less than it appears

Edwin's worry: *another device will seat differently.* **Per-device differences largely do not matter, because
`T = S/R` cancels a stable instrument.** A unit with a *different but stable* geometry measures its own
reference in that geometry, and the ratio still reports the oil.

What actually breaks a measurement is a unit that changes **between its own R and S captures**. That is a
**stability** requirement, not a manufacturing-tolerance one — and it is far cheaper to meet:

| requirement | why | how |
|---|---|---|
| **within a run: rigid** | the tilt error is a *change* between R and S | kinematic seat; ideally integrate the jar into the optical assembly (Edwin's own suggestion, and the strongest form of this) |
| **between units: threshold only** | absolute level can shift with configuration (measured: **14 %** between two optical configurations, §16.7.2g) | one reference sample of known ratio, measured per device at commissioning |

Second-order effects do remain per unit — stray light, and small differences in the px→nm calibration — so the
per-device reference measurement is not optional. But **"every unit built identically" is not the requirement**;
"every unit stable within a run, and calibrated once" is.

### 16.10.6 Combined, and what is still open

*Superseded in places by §16.10.7–16.10.12 (same day, later). Current state:*

| lever | effect | status |
|---|---|---|
| linear-baseline metric | S/Q 9/25 → **1/25** errors (leave-one-fill-out, §16.10.10) | ✅ **IMPLEMENTED** 2026-07-27, equal-weighted fit (§16.10.9); still needs a fresh *session* |
| **no-re-seat control (syringe fill)** | attacks the 98 % term directly | **free, run it FIRST** (§16.9.4a) — also unblocks §16.10.8 |
| kinematic angular seat + aperture | σ 11 % → ~2 % | designed (§16.9.4), not built; candidate coupling in §16.9.4f |
| median of 3 fills | ×1.7 | free, adopt now — improved by B3 (deliberate 120° rotation) |
| "inconclusive" third gauge zone | removes the last LOFO error at 4 % width | analysed (§16.10.11), **not implemented** |
| sample clarification | attacks the *fragility* (§16.7.2l) | untested |

They are independent and they multiply. **Nothing measured suggests the approach is unsound** — the instrument
resolves a class gap on oils whose *pigment* difference is genuinely small; what it lacks is a seat that returns
the sample to the same angle twice.

**Still open:** the slit width (unmeasured, and it sets the sensitivity), the tilt-vs-translation test above,
a fresh-**session** validation of the linear baseline, **dilution invariance (§16.10.8 — blocked on the seat)**,
the near-zero denominator guard (§16.10.9), and the 47/66 hue-band decision from §17.8.1.

### 16.10.7 Cross-group verification of the linear baseline *(2026-07-27, all 15 runs of the day)*

**Grouping correction to §16.10.2:** that table sliced `20260727B` by wall-clock, which put runs 008/009 in the
no-diffuser set. Per Edwin's own labelling the diffuser runs are 001–003 **and** 008–009; no-diffuser is 004–007.
No run was excluded anywhere below — the two visible extremes (green 007 at 14.209, brown 006 at 7.714) are in
every number.

| series | n | S/Q (CV) | LINEAR base (CV) |
|---|---|---|---|
| green, no diffuser (`B` 004–007) | 4 | 4.605 (14.4 %) | 12.267 (10.8 %) |
| green, diffuser (`B` 001–003, 008–009) | 5 | 5.212 (17.4 %) | 11.990 (11.0 %) |
| brown (`C` 001–006) | 6 | 4.105 (11.4 %) | 9.361 (8.9 %) |

⚠ **"improves in all five" does NOT generalise — one counter-example found later the same day.** On the
7-run green `20260727E` series the linear baseline was *worse* on scatter: **S/Q CV 7.9 % vs LINEAR 9.0 %**.
It still won decisively there on the thing that matters (7/7 correct vs 5/7), because the class gap widened
far more than the scatter did — but **"the metric always tightens the scatter" is false** and should not be
relied on. Separation, not repeatability, is what it reliably buys.

CV improves in **all five** groups of the *morning* set, mean factor 0.71 ≈ **1.4× better
repeatability** — and the class gap widens at the same time, so both terms of *d* move the right way at once.

**Ranked by LINEAR base, all 9 green runs sort above all 6 brown** (worst green 10.565 > best brown 10.002,
gap 0.563). Ranked by S/Q the classes **interleave** — three greens fall below a brown, and no threshold
classifies all 15. This is a *separation* result against Edwin's labels, **not** a threshold calibration; the
implied 10.28 midpoint is provisional (±2.7 % margin at n=15, one day) and must not ship as an Ampel threshold.

#### 16.10.7a First OUT-OF-SAMPLE check — the threshold held *(2026-07-27 12:50–13:26, 6 fresh runs)*

The first runs the shipped 10.3 threshold was **not** anchored on. Nothing refitted. Brown = `20260727D`
(001–003), green = `20260727E` (001–003) — Edwin referred to the green folder as "20260727Da"; the runs are
in `E`, which is the folder written immediately after `D`.

| label | run | S/Q | old gauge | LINEAR | new gauge |
|---|---|---|---|---|---|
| brown | 001 | 5.142 | **good — green** ← wrong | 9.475 | probably too brown |
| brown | 002 | 3.535 | probably too brown | 7.804 | probably too brown |
| brown | 003 | 3.598 | probably too brown | 8.023 | probably too brown |
| green | 001 | 5.484 | good — green | 13.395 | good — green |
| green | 002 | 4.810 | good — green | 12.834 | good — green |
| green | 003 | 4.743 | good — green | 12.116 | good — green |

**S/Q 5 / 6 · LINEAR base 6 / 6.** Brown 001 is the instructive one: at S/Q 5.142 it reads *greener than two
of the actual green runs*, and the old gauge passes it. The linear baseline places it at 9.475, correctly brown.

Separation **within this fresh set** is far wider than in the anchoring set — gap **2.641** (vs 0.563), worst
green 17.6 % above the threshold, best brown 8.0 % below it; S/Q overlaps by 0.398. Corrected-Q denominators
ran 0.071–0.114, so the §16.10.9 near-zero guard was not approached.

**All 21 runs of the day pooled:**

| metric | green (n=12) | brown (n=9) | d | at the shipped threshold |
|---|---|---|---|---|
| S/Q @ 4.4 | 4.960 [4.137 .. 6.692] | 4.101 [3.224 .. 5.142] | 1.28 | **5 of 21 wrong**, classes overlap by 1.005 |
| LINEAR base @ 10.3 | 12.278 [10.564 .. 14.186] | 9.050 [7.714 .. 9.999] | **3.06** | **0 of 21 wrong**, gap 0.565 |

The binding constraint is unchanged — green `B008` 10.564 against brown `C002` 9.999. The fresh runs did not
narrow it.

⚠ **"0 of 21/25 wrong" is IN-SAMPLE.** Under leave-one-**fill**-out — threshold refitted on three fills and
tested on the fourth — the linear baseline scores **1/25**, not 0. The miss is brown `C002` (10.011) against a
held-out threshold of 9.988. S/Q scores 9/25 on the same basis. 1/25 remains good, and the *small* gap between
in-sample and LOFO is itself the reassuring part (the weak candidates in §16.10.12's bench collapsed instead) —
but the honest headline number is 1/25.

**Margin trend as data accumulated** — every batch has *tightened* the constraint, never loosened it, which is
what one expects if 10.3 was drawn slightly optimistically from a small sample:

| after | worst green | margin above 10.3 |
|---|---|---|
| `B`+`C` (15 runs) | 10.564 | +2.6 % |
| + `D`/`E` 001–003 (21 runs) | 10.564 | +2.6 % |
| + `E` 004–007 (25 runs) | 10.506¹ | **+2.0 %** |

¹ under the equal-weighted fit now shipped (§16.10.9); 10.452 under the original unweighted one.

*What this does and does not establish:* it tests the **threshold** out of sample, not the instrument
configuration and not the oils — same rig, same day. Six runs are enough to have **falsified** the threshold
and not enough to have confirmed it; the value is that it had a real chance to fail and did not. The
§16.10.2 fresh-data validation (both classes, n ≥ 15, one configuration, a different session) still stands.
It is also the first evidence bearing on §16.10.8 — two fresh fills landing where predicted is *consistent*
with fill-to-fill stability, but resolves nothing about dilution.

### 16.10.8 Dilution invariance — UNRESOLVED, and seating is why *(2026-07-27)*

The 2023 library **cannot** answer it: each oil was measured 2–4 times at *one* dilution, within-oil level spread
only ±4.5 %. Its weak-lever signal is merely suggestive — the linear baseline is about half as level-sensitive as
S/Q (slope −0.435 vs −0.707).

On today's green oil, across a real 2.19× dilution span (3.15× per run), **neither** metric shows a significant
level dependence (LINEAR r=+0.248, t=0.89; S/Q r=−0.454, t=1.76; n=14, needs |t|>2.18). That is not a clean bill
of health — it is a power failure:

| | spread |
|---|---|
| metric spread from **seating alone** (9 runs, one dilution) | 1.34× |
| metric spread across a **2.19× dilution change** | 1.35× |
| absorbance *level* spread from seating alone | 1.57× |

**Seating noise alone is as large as the entire dilution effect**, so the dilution term is buried. The last row
also compromises absorbance level as a concentration proxy, which is what weakens the 2023 test above.

*An earlier reading of two low green runs (NowSteirerkraftA 9.097, cap003 9.588) as evidence of dilution
dependence was over-attributed — the A/B pair sits at near-identical level (0.1923 vs 0.1819) yet 35 % apart in
metric, which is seating, not dilution.*

**Consequence — this promotes Lever B.** The kinematic seat is no longer only "improves the numbers"; it is a
**prerequisite for measuring dilution invariance at all**, which is the claim the Capability Proof rests on.
The settling experiment: after the seat fix, one oil, ≥4× concentration span, n ≥ 5 per level, one session
(≈20 runs) — enough power to resolve a log-log slope of ~0.1.

> **▶ Read §16.14 before running that experiment (added 2026-07-31).** The algebra says `S/Q_lin` is invariant
> **by construction** and that exactly one mechanism can break it — curvature in the turbidity pedestal. That
> changes the readout: the signature to look for is a **curved** log–log plot flattening toward high
> concentration (local slope ∝ 1/c), not a constant non-zero slope. Same runs, sharper test, and a quantitative
> target (`r_Q`, bounded at ≲ 0.01 A by §16.14.7) instead of a null hypothesis to fail to reject.

### 16.10.9 ▶ NEXT TASK — implement the linear-baseline metric *(marked 2026-07-27; DESIGN only, do not implement until asked)*

Fit a straight line through 520–540 and 600–630 of the ABSORPTION spectrum, subtract it, then take S/Q of the
corrected spectrum. **One function, no hardware.** Keep the raw S/Q alongside for comparison.

Carry these caveats into the implementation: separation is demonstrated at **fixed dilution only** (§16.10.8);
the threshold is provisional; and the band edges plus the two quiet windows were chosen *after* seeing the tilt
problem, so they are fitted, not independent. Fresh-data validation (both classes, n ≥ 15, one configuration)
still gates any change to `PB_SORET_BAND`'s neighbours.

Prototypes: `linear_metric.py`, `oil_table.py`, `dilution_invariance.py` (2026-07-27 session scratchpad).

**Baseline fit = EQUAL WEIGHT PER WINDOW** *(implemented 2026-07-27)*. Each anchor window contributes total
weight 1, not one unit per sample point. Compared on all 25 runs of the day against the two alternatives:

| fit | green (n=16) | brown (n=9) | d | gap |
|---|---|---|---|---|
| unweighted least-squares over all points | 12.103 [10.452 .. 14.186] | 9.050 [7.714 .. 9.999] | 2.85 | +0.453 |
| **equal weight per window** *(shipped)* | 12.177 [10.506 .. 14.273] | 9.060 [7.722 .. 10.011] | **2.88** | **+0.495** |
| line through the two window centroids | 12.115 [10.446 .. 14.218] | 9.046 [7.707 .. 9.996] | 2.84 | +0.450 |

**The choice is for predictability, NOT accuracy.** Run values move ≈0.5 %, *d* spans 2.84–2.88, within-series
CV is identical to a tenth of a percent, and **no verdict changes on any of the 25 runs under any of the three
fits** — a +0.495 vs +0.453 gap at n=25 with ~10 % scatter is not a real difference. What equal weighting buys
is that a window's influence stops depending on how many points happen to fall in it: unweighted, 520–540's 135
points were outvoted by 600–630's 212, and *widening a window would silently re-weight the baseline*. Measured:
the corrected value at 450 nm shifts **8.03 %** under the unweighted fit when one window is sampled 4× denser,
and **0.31 %** under equal weighting — a factor of ~26.

*Not an exact invariance:* the within-window spread of λ still depends on the point count, so a small residual
remains. Equal weighting also does **not** make the fit width-invariant — a wider window moves its own centroid,
and that legitimately changes the line.

### 16.10.10 The blank's own tilt does NOT predict a run's error — a useful NULL *(2026-07-27)*

Idea: the blank is captured every run through the same geometry, so `R`'s own spectral tilt should fingerprint
that run's seating and let the error be regressed out of data already collected. Tested on all 25 runs
(`diagnostics/reference_tilt_covariate.py`; tilt = slope of log₁₀ R per 100 nm — **log** so a pure throughput
change is an offset and the scalar reads SHAPE, not brightness):

| metric | r | t (n=25) | variance explained |
|---|---|---|---|
| S/Q raw | +0.129 | 0.63 | 1.7 % |
| S/Q linear base | −0.200 | 0.98 | 4.0 % |

**Null** (needs \|t\| > 2.07). Regressing it out moves *d* 2.88 → 3.05, but at r = −0.20 that is fitting noise;
**not adopted**.

**Why it had to be null, and why that matters.** The error is not "R has a tilt" — it is that the geometry
**differs between the R capture and the S capture**, because the jar is emptied and refilled in between.
`T = S/R` cancels whatever geometry is *common* to both; what survives is the **change**. R's absolute tilt
describes R's geometry alone and is structurally incapable of reporting the R→S difference. The null therefore
**confirms** §16.10.1 rather than contradicting it — and it promotes the bracketing protocol below from a nice
check to *the only way to observe the quantity that does the damage*.

### 16.10.11 A third gauge zone — ÜBERGANG, "measure again" *(2026-07-27, analysed; impl on request)*

Zone = threshold × (1 ± f), on the 25 runs at the shipped 10.3:

| f | zone | inconclusive | confident wrong | LOFO wrong |
|---|---|---|---|---|
| 0 % | — | 0/25 | 0 | **1** |
| 2 % | 10.09–10.51 | 0/25 | 0 | 0 |
| **4 %** | **9.89–10.71** | **3/25** | **0** | **0** |
| 10 % | 9.27–11.33 | 9/25 | 0 | 0 |
| 15 % | 8.76–11.85 | 13/25 | 0 | 0 |

At 2 % it costs nothing and neutralises the single leave-one-fill-out error (brown `C002`, which becomes
"measure again" instead of wrong). At 4 % it costs 3 runs — `E006`, `C002`, `B008`, precisely the boundary
cases already known — for a clean sheet. **Recommend f = 4 %, documented as pragmatic.**

⚠ **The uncomfortable part.** Within-series CV is ~10 %, so one run's σ ≈ 1.0 in metric units and a
*statistically honest* zone would be ±1–2σ = **±10–20 %** — which makes half the measurements inconclusive.
The truthful statement is that **single-run precision does not support confident verdicts near the threshold at
all**; a narrow zone is a compromise, not a rigorous interval. The real fix is the median of 3 fills (σ ÷ 1.7,
§16.10.4) plus the seat, after which ±6 % would carry the weight ±10 % does today.

#### 16.10.11a The honest form — distance ÷ measured scatter *(worked on the 25 runs, 2026-07-27)*

Not a fitted classifier (§16.10.14 measured those as worse *and* mis-calibrated) — two arithmetic steps.

**Step 1 — σ from repeat FILLS, never from repeat captures.** This choice is the whole method: re-capturing one
fill without touching the jar gives ~1 % and excludes the dominant error, so a confidence built on it is a
fiction. Repeat *fills* include the seating.

| fill | n | CV |
|---|---|---|
| green B | 9 | 10.3 % |
| green E | 7 | 9.1 % |
| brown C | 6 | 8.9 % |
| brown D | 3 | 10.7 % |
| **pooled** | | **9.7 % → σ = 1.00 metric units at the threshold** (dof 21) |

**Step 2 — `z = (x − T)/σ`, then `P = Φ(z)`.** Use a **t-distribution** on the real dof rather than the normal:
the error is heavy-tailed (§16.7.2f), so the Gaussian is optimistic exactly where it matters.

| confidence | decided | inconclusive | wrong |
|---|---|---|---|
| 80 % | 17/25 | 8 | **0** |
| 90 % | 14/25 | 11 | **0** |
| 95 % | 10/25 | 15 | **0** |
| 99 % | 6/25 | 19 | **0** |

**Zero errors at every level** — the mechanism does its job. But at 95 % the instrument decides only **40 % of
single measurements**. That is the same fact as "the margin is 2 %", restated in the unit a user cares about.
Median of 3 fills recovers part of it (≈16/25 decided at 95 %).

⚠ **What the number means.** `P = 0.964` is **P(the true metric value is above the threshold)** — *not*
P(the oil is green). Two uncertainties stack: measurement scatter, which this estimates, and whether 10.3
divides green from brown oil at all, which 25 runs on one rig cannot establish. The wording must therefore be
**"above threshold, 96 % confident"**, never "96 % green" — otherwise an unvalidated threshold is laundered
through a respectable-looking probability.

**σ should be measured per session**, not baked in, so the confidence self-calibrates. That is the real use of
the B1 bracketing idea (§16.10.12): it cannot correct an individual run, but it does sample the seating spread.

**This is what prices the seat (§16.9.4), in the only unit that matters:**

| σ | decided at 95 % |
|---|---|
| 9.7 % (today) | 10/25 |
| 3.0 % (cone-joint level, §16.10.3's target) | **≈21/25** *(estimate, same 25 values)* |

From deciding 40 % of samples to deciding 84 %.

### 16.10.12 Idea backlog — marked, not built *(2026-07-27, Edwin)*

| # | idea | status | note |
|---|---|---|---|
| **B1** | **Bracket the sample between two blanks: R → S → R** | **marked for later** | Free, no hardware. If the two blanks disagree, the geometry moved *during the run* and it can be discarded. **Promoted by §16.10.10's null** — it is the only protocol that observes the R→S change, which is the quantity that actually causes the error. It also directly measures the R-to-S stability that §16.10.5's manufacturability argument rests on. |
| **B2** | **Internal standard doped into the SAMPLE** | **postponed** | A trace of a stable dye with a sharp band where the oil is featureless. Its band amplitude measures path × concentration *for that run*, so the oil bands are normalised by it and **dilution stops being an assumption and becomes a measurement** — which is what §16.10.8 is blocked on. Will NOT fix tilt (a shape error, not an amplitude one). Cost: a consumable, plus finding a dye that misses the useful parts of 440–630. |
| B3 | Rotate the jar 120° between replicates | idea | Converts an arbitrary-but-fixed per-fill bias into something closer to random, so the median of 3 (§16.10.4) actually averages it down. Free. |
| B4 | Weigh the oil instead of counting drops (~€15 scale) | idea | "2 drops" varies 10–20 %. §16.10.8 cannot resolve dilution invariance while dilution itself is known only to ±15 %. |
| B5 | Double-beam bypass channel | idea | Split light *around* the jar onto a different strip of the **slit height** — the grating disperses each height independently, so one exposure yields two spectra on different sensor rows. Lamp/exposure/WB drift then appears in both and divides out exactly, per frame. **Does not see the jar's seating** (the bypass never traverses it), so it kills the small terms, not the 98 % one. |

### 16.10.13 Candidate-metric bench — nothing beat the linear baseline *(2026-07-27, `diagnostics/metric_bench.py`)*

Seven candidates, same 25 runs, same de-spiked absorbance, scored **leave-one-FILL-out**: runs within a fill
share a seating state, so leave-one-*run*-out leaves a run's near-twins in training and inflates the score.
Four fills — green `B`, green `E`, brown `C`, brown `D`.

| candidate | \|d\| | in-sample | **LOFO** |
|---|---|---|---|
| **S/Q linear base** *(shipped)* | 2.88 | 0/25 | **1/25** |
| area ratio (same bands, integrated not averaged) | 2.89 | 0/25 | 1/25 |
| centroid nm (first moment of the corrected curve) | 2.24 | 1/25 | 3/25 |
| S/Q raw | 1.24 | 5/25 | 9/25 |
| absorbed hue | 0.64 | 7/25 | 12/25 |
| 2nd-derivative ratio (Savitzky-Golay) | 1.07 | 6/25 | 17/25 |
| Q λ-max | 0.37 | 8/25 | 19/25 |

**Nothing beat the shipped metric.** Area ratio ties but is the same bands integrated rather than averaged — a
restatement, not evidence. Q λ-max and the 2nd derivative failed; the latter is a verdict on **untuned**
Savitzky-Golay parameters (green spanned 0.155–9.411 — noise amplification) more than on the technique.

⚠ **Correction to the first reading of this bench.** The centroid was initially written up as "the one genuine
find — position-based, independent, worth carrying as a second opinion". §16.10.14 then measured its error
correlation against the shipped ratio at **r = −0.95**: it is *not* independent, it reads the same quantity with
a sign flip. It is not a second opinion.

### 16.10.14 Combining metrics / emitting a probability — measured, does NOT help *(2026-07-27)*

**Q: could several metrics be combined into a verdict or a probability?** Two independent reasons why not, on
today's data.

**(a) The candidates fail on the SAME runs.** Error correlations of the within-class deviations:

| | lin. base | centroid | area | S/Q raw | hue |
|---|---|---|---|---|---|
| **lin. base** | 1.00 | **−0.95** | 1.00 | 0.80 | 0.48 |
| **centroid** | −0.95 | 1.00 | −0.95 | −0.90 | −0.49 |

Every candidate is disturbed by the same seating event, so there is **no independent second opinion to
combine**. Averaging metrics that are wrong together changes nothing.

**(b) At n=25 a fitted model is WORSE than a hand-set threshold.** Logistic regression, refit inside the LOFO
loop (no leakage):

| features | LOFO |
|---|---|
| plain threshold on the linear base *(what ships)* | **1/25** |
| logistic, linear base **alone** | 7/25 |
| logistic, linear base + centroid | 7/25 |
| logistic, + absorbed hue | 10/25 |
| logistic, all five | 9/25 |

Not a bug: the threshold search minimises misclassifications directly, while logistic regression minimises
log-loss, is pulled by well-separated points, and with 4 folds + imbalanced training sets + L2 shrinkage toward
the class prior the boundary lands badly. Adding features makes it worse — textbook overfitting.

**(c) The probabilities would be confidently wrong**, which is the worst outcome of the three:

```
20260727C/004  brown  P(green) = 0.642  WRONG
20260727C/005  brown  P(green) = 0.615  WRONG
20260727C/003  brown  P(green) = 0.566  WRONG
```

A "64 % green" printed beside a wrong verdict converts an error into a *justified-looking* error. **Do not ship
a fitted probability.**

**What an honest confidence WOULD be:** §16.10.11's route — distance from the threshold divided by the
**measured** replicate scatter. That is estimable (how far does a repeat of the same oil move?), needs no fitted
model, degrades gracefully, and yields "green / brown / measure again" naturally. A genuinely fitted probability
needs many more fills, since the between-fill variation is what must be sampled and there are currently four.

An agreement rule (ratio and centroid must concur, else inconclusive) scores 2/25 inconclusive · 23 confident ·
1 wrong — no better than the single metric, and (a) explains why.

### 16.10.15 Colour channels do NOT discriminate this oil pair *(2026-07-27)*

All nine channels the DEV plugin can render, same 25 runs, same LOFO scoring:

| channel | green (n=16) | brown (n=9) | d | overlap | LOFO |
|---|---|---|---|---|---|
| absorbed hue | 258.31 [255.83..263.08] | 257.34 [256.36..259.27] | 0.64 | YES | 12/25 |
| intrinsic-perceived hue | 78.31 [75.83..83.08] | 77.34 [76.36..79.27] | 0.64 | YES | 12/25 |
| absorbed chroma | 69.44 [61.96..86.67] | 64.75 [57.65..75.69] | 0.84 | YES | 12/25 |
| absorbed lightness | 65.28 [56.67..69.02] | 67.63 [62.16..71.18] | −0.84 | YES | 16/25 |
| perceived hue | 70.67 [70.00..71.29] | 70.57 [69.90..71.43] | 0.23 | YES | 10/25 |
| perceived chroma | 36.27 [33.33..40.00] | 36.99 [32.94..40.39] | −0.32 | YES | 14/25 |
| absorbed / perceived **saturation** | **100.00 every run** | **100.00 every run** | 0.00 | YES | 7/25¹ |

¹ tie-breaking noise on a **constant**, not a result.

**Every channel overlaps**; best \|d\| is 0.84 against the shipped ratio's 2.88. Three structural findings:

1. **Saturation is pinned at 100.0 on every run**, absorbed and perceived — the F10 problem
   [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) already flags (near-white chromaticities read S ≈ 100 %
   in HLS, which is why chroma exists). A structurally constant channel arguably should not be displayed.
2. **`intrinsic-perceived hue` = `absorbed hue` + 180° by construction**, so identical *d* and identical LOFO —
   it can add interpretability, never discriminating power. With the normalized variants fixing S and L, the
   **five chips carry two independent numbers**: absorbed hue and perceived hue. Not five pieces of evidence.
3. **Absorbed hue's brown range is NESTED inside green's** (256.4–259.3 within 255.8–263.1). No threshold
   separates nested ranges — this is not a tuning problem.

**Likely why:** at 6 drops in 18 ml both oils are pale, and chromaticity of a ~1:3000 dilution retains little of
the difference obvious in the bottle. A band *ratio* survives dilution because it is a shape measure; hue is
what little is left of an almost-white sample. This predicts colour would work better **undiluted** — exactly
where absorbance saturates and the ratio stops working. **The two approaches want opposite concentrations.**

Colour therefore stays a **visual aid** on this oil pair, not a discriminator.

### 16.10.16 The sub-10 asymmetry — a real signal, and the re-run trap *(Edwin 2026-07-27)*

**Edwin's observation, and it holds:** on all 25 runs, *nothing green ever read low.*

```
runs below 10.0:   8,  ALL brown
lowest green:      10.506  (E006)
highest brown:     10.011  (C002)
empirical no-man's land:  10.011 .. 10.506
```

**A single sub-10 reading IS strong evidence.** Fitting each class with the measured σ (§16.10.11a):

| | mean | σ | P(run < 10.0) |
|---|---|---|---|
| green | 12.18 | 1.18 | **3.3 %** (1 in 31) |
| brown | 9.06 | 0.88 | 86 % |

→ **likelihood ratio 26 : 1 for brown.** The intuition is well founded.

**Caveat 1 — "no green was ever that low" ≠ green never goes there.** Zero events in 16 green runs is *exactly*
what a 3.3 % rate predicts (expected 0.5). It bounds the rate as small, not zero; the nonparametric 95 % ceiling
(rule of three) is **18.8 %**. Expect a sub-10 green eventually.

**Caveat 2 — the PROCEDURE is weaker than the observation.** The proposed rule was: borderline reading, re-run,
if it lands low call it brown. But the first reading cannot be discarded — the evidence is the **pair**:

| first | re-run | mean | LR for brown |
|---|---|---|---|
| 10.4 | 9.8 | 10.10 | **5 : 1** |
| 10.4 | 9.5 | 9.95 | 13 : 1 |
| 10.4 | 10.1 | 10.25 | 2 : 1 |

5 : 1, not 26 : 1 — the borderline 10.4 is itself mildly pro-green and pulls back.

**Caveat 3 — the trap.** A rule that fires when **either** reading is low has, for green oil,
`1 − (1 − 0.033)² = 6.5 %` false-brown — it **doubles** the error rate. Generalised: *"keep measuring until one
lands low"* converges on calling everything brown. Selecting among readings is not the same as combining them.

**The fix is small:** take the **mean or median of the fills and evaluate that** against the threshold, i.e.
§16.10.11a with σ/√n. Edwin's rule is the special case; doing it this way captures the same intuition while
keeping the error rate honest.

Two conditions on any re-run: it must be a **new fill and a new seating** (re-capturing one fill repeats the
same disturbance and is not a second opinion), and 10.0 is an **observed extreme on 25 runs** — observed extremes
move outward as data accumulates, as the §16.10.7a margin trend already shows.

### 16.10.17 End-user measurement protocol *(2026-07-27, Edwin approved the shape; DESIGN — impl on request)*

The operator-facing form of §16.10.11a. Turns "the margin is 2 %" into a procedure a miller can run.

#### 16.10.17a Why 3 fills — and it beats the theory

σ of the **median** of n fills, measured empirically from every n-subset of the real data (not assumed):

| n fills | σ_rel | vs n=1 | decided @95 % |
|---|---|---|---|
| 1 | 9.8 % | 1.00× | 8/25 |
| 2 | 5.7 % | 1.71× | 15/25 |
| **3** | **4.8 %** | **2.03×** | 16/25 |
| 4 | 3.4 % | 2.90× | 20/25 |
| 5 | 2.1 % | 4.60× | 22/25 |

Median-of-3 tightens σ by **2.03×**, beating the √3 = 1.73 an *average* would give — because the error is
heavy-tailed (§16.7.2f) and the median is the right estimator for that. **The data confirms lever C's premise
(§16.10.4).**

#### 16.10.17b The decision table

σ single fill ≈ **1.04**, σ median-of-3 ≈ **0.51** (metric units, at the shipped **T = 10.6**, §16.10.17d).

```
FILL 1
   >= 13.3   ->  GREEN, done          (T + 25 %, = T + 2.58 sigma)
   <=  7.9   ->  BROWN, done          (T - 25 %)   -- theoretical, see 16.10.17d
   else      ->  take 2 more fills

MEDIAN OF 3
   >= 11.6   ->  GREEN                (T + 9 %, = T + 1.96 sigma_3)
   <=  9.6   ->  BROWN                (T - 9 %)
   else      ->  ÜBERGANG   (transition -- see 16.10.17c for the term)
```

Three fills nearly **halve** the clearance needed (2.7 units → 1.0) because σ halves. At the earlier
T = 10.3 the fill-1 gate was 12.9 and 5 of 16 green runs cleared it (≈31 %); at 10.6 the gate rises to 13.3, so
the one-fill shortcut fires **less often** — part of the price of the stricter policy.

⚠ **The stopping rule must be FIXED IN ADVANCE.** This is §16.10.16's trap in another guise: if the operator may
keep adding fills until the answer looks decided, the error rate inflates exactly as *"re-run until it goes low"*
did. The 99 % early exit against a 95 % final gate is crude alpha-spending; the statistically clean variant is
**always three fills, no early exit**. Ship the clean one unless the 31 % early exit is worth the complexity.

#### 16.10.17c Wording

> **Übergang after fill 1:**
> "This sample sits close to the green/brown boundary — one measurement can't settle it.
> Prepare a **fresh fill** and measure again. Two more will decide it."

**Deliberately WITHOUT the direction.** If the operator knows it leaned brown, a brown-ish second reading reads
as *confirmation* and invites stopping there — optional-stopping bias re-entering through the human. Withhold
direction until the protocol completes. (Harmless to show it in a fully automated flow with no human decision.)

**"Fresh fill" is not pedantry** — re-capturing the same fill repeats the same seating disturbance and adds no
information at all (§16.10.10). The screen must not say merely "measure again".

**Before the first fill — capture the operator's OWN read** *(consistency-instrument design, `SPEC_capability_proof.md`
"positioning term"; not yet built)*. A "your assessment: green / brown / unsure" field at sample preparation.
The point is **independence**: if the operator sees the verdict first they are anchored, and the agreement
between human and instrument — which is most of the product's value — stops meaning anything. Same
anti-anchoring principle as withholding the direction on a borderline re-fill, applied one step earlier.

**⚠ TERMINOLOGY — the third state is „ÜBERGANG", never „grenzwertig"** *(Edwin 2026-07-27)*. Colloquial German
„grenzwertig" means *dubious / pushing it*, so it **condemns the oil** — when the truth is that the
**measurement** has not separated it. Nothing is wrong with a sample that lands there. „Übergang" describes the
*region* (and matches what the gradient bar literally does: grün → Übergang → braun) without a verdict on the
product. The same word is used on the customer flyer. English prose in this spec still uses *borderline*
adjectivally ("a borderline reading") — that is analysis language, not a user-facing label.

Outcomes:

| | |
|---|---|
| ✅ | **"Green — consistent with a good roast."** *(high confidence)* |
| 🔴 | **"Brown — consistent with over-roasting."** *(high confidence)* |
| ⚪ | **„Übergang — diese Probe liegt zwischen den beiden Klassen."** Drei Füllungen haben sie nicht getrennt. Das ist ein echtes Ergebnis: die Probe liegt im Übergangsbereich. |

The third **must** read as an answer, not a failure — presented as a failure the operator keeps measuring until
it tips, and the trap returns. And **no percentage labelled "% green"** may reach the UI: the number is
P(above threshold) (§16.10.11a). A qualitative "high confidence" badge is defensible; "96 % green" is not.

#### 16.10.17d ⚠ BROWN is the harder call — and the threshold embeds an unmade decision

*Correction to a pooled figure quoted earlier in the session: "85 % of triplets resolve" is true overall but is
dominated by green, which supplies 119 of the 140 triplets. Split by class it is very different:*

| | resolved at fill 1 (99 %) | resolved after 3 fills (95 %) |
|---|---|---|
| green | 5/16 = **31 %** | 114/119 triplets = **96 %** |
| brown | 0/9 = **0 %** | 5/21 triplets = **24 %** |

The classes are **not equidistant** from the threshold: green's mean sits **1.86 σ** above 10.3, brown's only
**1.23 σ** below. So a brown oil essentially never resolves on one fill, and a *mildly* brown one (fill `C`,
mean 9.371 — triplet medians land at P ≈ 0.06–0.08, just missing the 0.05 gate) often stays in ÜBERGANG even
after three. A strongly brown one (fill `D`, mean 8.44) resolves easily.

**Why:** 10.3 was placed midway between the observed *extremes* (worst green 10.506, best brown 10.011) — a
placement that protects the green verdict and pays for it in brown detection power.

| threshold | green protected | brown detected | in-sample errors |
|---|---|---|---|
| **10.3** *(shipped)* | strongly | weakly | 0/25 |
| ~10.6 *(midway between class MEANS)* | weakly | strongly | 2/25 (`B008` 10.604, `E006` 10.506 flip) |

**For a quality-control instrument the usual instinct is the opposite of what ships: passing bad oil as good is
normally the costlier error.** It is **a product decision, not a midpoint formula**, and 10.3 silently answered
it the wrong way round.

#### ✅ DECIDED 2026-07-27 (Edwin): passing bad oil is the costlier error → **threshold = 10.6**, IMPLEMENTED

| | T = 10.3 | **T = 10.6** |
|---|---|---|
| brown triplets resolved @95 % | 1/21 = 5 % | **11/21 = 52 %** ← the point of the change |
| green triplets resolved @95 % | 114/119 = 96 % | 95/119 = 80 % |
| in-sample misclassifications | 0/25 | 1/25 |
| fill-1 green gate | 12.90 | **13.28** |
| 3-fill gates | ≥ 11.27 / ≤ 9.33 | **≥ 11.60 / ≤ 9.60** |

**Brown detection ×10.** The accepted cost is green `E006` (10.506) reading brown.

⚠ **Budget for 1–2 accepted false-browns, not exactly 1:** `B008` clears the new line by **0.004** (10.604 vs
10.600) — functionally a coin flip that could land either way on a repeat. The direction is deliberate: a false
BROWN costs a re-check, a false GREEN ships bad oil.

The decision table in §16.10.17b is stated for T = 10.3; **the shipped gates are the 10.6 column above.**

**Still open (not implemented):** the near-zero denominator guard. `ratio()` clamps at `EPS = 1e-3`, so a run
that drove the corrected Q to ≤ 0 would yield an enormous ratio, clamp to the band's left edge, and report a
confident **"good — green"**. Today's denominators ran 0.062–0.114, i.e. ≥ 62× the guard, so it is nowhere near
firing — but a silent false-green is the worst failure direction this instrument has, and the fix (return
`None` so the gauge omits itself) is small.

---

## 16.11 ⭐ THE REBUILD — measured *(Edwin 2026-07-29/30; the jar halved, the camera took its place, first sub-3 % metric)*

The first re-measurement of §16.7–§16.10 after mechanical work. Everything here is measured on Edwin's rig with
the same `diagnostics/cuvette_reseat_probe.py` and the same paired untouched control, or extracted from the
embedded `workflow.json` of the archived report PDFs. **Read §16.11.4 and §16.11.9 before quoting any number
from §16.11.3** — the headline gain is real but its cause is not the one it appears to be.

Data: `spectracs-references/tmp/reseat_20260729/` (probe logs, arms `none`/`jar`/`camera`),
`tmp/20270829A/` (3 PDFs, 24 h-aged dilution), `tmp/20270729B/` and `tmp/20270729C/` (6 PDFs each, fresh green
oil, two different dilutions). *Folder names carry typo'd years; the measurements are 2026-07-29/30.*

⚠ **`spectracs-references/` is NOT under version control** (checked 2026-07-30). §16.11.3a preserves every
*derived* per-run value, so nothing in §16.11 depends on those files surviving — but the **raw spectra** (1305
bins per run, plus the reference/sample frames) exist on one disk only. §16.10.13 re-benched seven candidate
metrics against archived runs, so that data has already proved reusable once. **`git init` there, or back it up.**

### 16.11.0 Summary

| | before | after | |
|---|---|---|---|
| `jar` re-seat tilt (composite) | 2.84 % | **1.34 %** | **2.1× better** |
| `camera` 1 mm nudge | 0.42 % | **1.98 %** | now the dominant sensitivity |
| `none` floor | 0.04–0.09 % | **0.07 %** | unchanged → the comparison is valid |
| S/Q linear-baseline CV, one fill re-seated | 4.95 % *(n=3, aged oil)* | **2.96 % / 2.89 %** *(n=6 ×2)* | **first result under §16.10.3's 3 % target** |
| σ at the threshold | 1.04 *(single fill)* | **0.367** *(re-seat only)* | tighter than §16.10.17b's median-of-**3** |

**12/12 runs across both dilutions returned "good — green"**, worst run 3.4 σ clear of T = 10.6.

### 16.11.1 What changed on the instrument

Edwin rebuilt the jar holder, the upper-cone-on-lower-cone seat, and the camera mount, then added a **protocol**:
when setting the upper cone into its ring on the lower cone, shift it against a **marked line** to take up the
~1 mm play in the ring. That is a hand-executed approximation of §16.9.4's kinematic constraint — it removes the
*translational* degree of freedom the ring leaves open, at zero hardware cost.

### 16.11.2 Probe arms — old vs rebuilt

| arm | old (§16.9.3) | rebuilt | factor over today's floor | permanent |
|---|---|---|---|---|
| `none` (null control) | 0.04–0.09 % | **0.07 %** | — | 29 % |
| **`jar`** (out and back in; on this rig that necessarily lifts and re-seats the cone) | 2.84 % | **1.34 %** | 27× | 66 % |
| **`camera`** (~1 mm nudge) | 0.42 % | **1.98 %** | 32× | 81 % |
| `cone` / `holder` / `stack` | 0.39 / 0.56 / — | **NOT RUN** | | |

**The unchanged floor is what licenses the comparison.** Same script, same measurement noise, so the halved jar
figure is a change in the mechanics and not in the instrument that measures it. The `jar` arm's own no-touch
control read 0.05 %, so nothing drifted underneath it either.

⚠ **`jar` and `camera` are NOT equally comparable across sessions.** `jar` is a *defined operation* — "take the
cuvette out and put it back" is the same physical act in both sessions, so 2.84 % → 1.34 % is a clean
before/after. `camera` is *operator-calibrated* ("nudge about 1 mm, the same way each round"): reproducible
within a session, not between them. **Do not conclude the camera mount got worse** — nudging harder tonight
produces 4.7× on its own.

What IS solid, because it is internal to one session: **the optical train is now more sensitive to camera
position than to jar seating** — 1.98 % per mm against 1.34 % for a full jar re-seat. That reverses the old
ranking, where the jar led by ~7×. It is a *sensitivity*, not a per-measurement error: nobody nudges the camera
during a normal run. It is a fragility statement — one knock now costs more than a jar change.

⚠ **The verdict string is unchanged and must not be read as a null result.** `jar.txt` still prints
"CUVETTE SEATING IS AN ERROR SOURCE" because that test is `tilt ÷ floor ≥ 3`, and the floor is so low that
1.34 % is still 27× it. It measures *detectability*, not magnitude.

### 16.11.3 Six-run repeatability, replicated on two dilutions

Fresh green oil (not the aged 2023 stock). **One fill, re-seated between every run** — same experimental basis as
§16.11.4's aged-oil triplet, so the two are directly comparable.

| | set B (`20270729B`) | set C (`20270729C`) | B+C pooled |
|---|---|---|---|
| A_Q raw (560–580) | 0.197 | 0.230 | — |
| S/Q linear baseline, mean | 12.489 | 12.251 | 12.370 |
| σ | 0.370 | 0.354 | **0.367** |
| **CV** | **2.96 %** | **2.89 %** | **2.96 %** |
| verdict | 6× green | 6× green | **12/12 green** |

Two independent sets agreeing to 0.07 % on CV. Sub-3 % is the rig's repeatability, not a lucky draw. 95 % CI on
2.96 % at n=6 is **[1.85 %, 7.26 %]** — much tighter than the aged triplet's [2.6 %, 31 %], still not a figure to
hard-code.

**The plain ratio, on the same runs, does not do this:** set B plain S/Q CV **11.13 %** against the linear
baseline's 2.96 %. See §16.11.5.

#### 16.11.3a The raw record — every run of both series

`<<` marks a tilt event (|slope| > 0.015 A/100 nm). Note it fires only on **early** runs in both series
independently — that is §16.11.7's finding, and it is visible in the timestamps alone.

```
+------------------------------------------------------------------------+
|               SERIES B  ·  tmp/20270729B  ·  dilution #1               |
|     fresh green oil | ONE fill, re-seated each run | A_Q raw 0.197     |
+----------+---------+--------+--------+---------+--------------+--------+
|   run    |  A_Sor  |  A_Q   |  S/Q   | S/Q_lin |  tilt/100nm  |verdict |
|  +time   |   _lin  |  _lin  | plain  | SHIPPED |  vs median   | T=10.6 |
+==========+=========+========+========+=========+==============+========+
|001 22:39 |  1.096  | 0.086  | 5.311  |  12.749 |  -0.0204 <<  | GREEN  |
|002 22:44 |  1.022  | 0.078  | 6.864  |  13.021 |  -0.0398 <<  | GREEN  |
|003 22:50 |  1.031  | 0.085  | 5.334  |  12.194 |   +0.0004    | GREEN  |
|004 22:55 |  1.024  | 0.083  | 5.233  |  12.335 |   +0.0087    | GREEN  |
|005 23:01 |  1.025  | 0.081  | 5.488  |  12.602 |   -0.0016    | GREEN  |
|006 23:07 |  1.002  | 0.083  | 5.386  |  12.031 |   +0.0092    | GREEN  |
+==========+=========+========+========+=========+==============+========+
|   mean   |  1.033  | 0.083  | 5.603  |  12.489 |              |        |
|    sd    |  0.032  | 0.003  | 0.624  |  0.370  |              |        |
|    CV    |  3.12%  | 3.48%  | 11.13% |  2.96%  |              |  6/6   |
+----------+---------+--------+--------+---------+--------------+--------+

+------------------------------------------------------------------------+
|               SERIES C  ·  tmp/20270729C  ·  dilution #2               |
|  same oil, fresh dil. | ONE fill, re-seated each run | A_Q raw 0.230   |
+----------+---------+--------+--------+---------+--------------+--------+
|   run    |  A_Sor  |  A_Q   |  S/Q   | S/Q_lin |  tilt/100nm  |verdict |
|  +time   |   _lin  |  _lin  | plain  | SHIPPED |  vs median   | T=10.6 |
+==========+=========+========+========+=========+==============+========+
|001 23:35 |  1.188  | 0.093  | 4.863  |  12.807 |  -0.0188 <<  | GREEN  |
|002 23:40 |  1.117  | 0.090  | 5.277  |  12.475 |  -0.0210 <<  | GREEN  |
|003 23:46 |  1.085  | 0.089  | 5.626  |  12.204 |  -0.0188 <<  | GREEN  |
|004 23:56 |  1.083  | 0.089  | 5.205  |  12.235 |   +0.0055    | GREEN  |
|005 00:02 |  1.090  | 0.091  | 5.070  |  11.943 |   +0.0035    | GREEN  |
|006 00:08 |  1.062  | 0.090  | 4.992  |  11.840 |   +0.0123    | GREEN  |
+==========+=========+========+========+=========+==============+========+
|   mean   |  1.104  | 0.090  | 5.172  |  12.251 |              |        |
|    sd    |  0.045  | 0.002  | 0.267  |  0.354  |              |        |
|    CV    |  4.05%  | 1.67%  | 5.16%  |  2.89%  |              |  6/6   |
+----------+---------+--------+--------+---------+--------------+--------+

+-----------------------------------------------------------------------------+
|                    B vs C  —  the two dilutions compared                    |
+--------------------------+----------------+----------------+----------------+
|                          |    SERIES B    |    SERIES C    |   B+C pooled   |
+==========================+================+================+================+
| A_Q raw (concentration)  |     0.197      |     0.230      |     +16.8%     |
|  S/Q linear base, mean   |     12.489     |     12.251     |     12.370     |
|    sd (metric units)     |     0.370      |     0.354      |     0.367      |
|  CV  <-- SHIPPED metric  |     2.96%      |     2.89%      |     2.96%      |
| plain S/Q CV (contrast)  |     11.13%     |     5.16%      |     8.53%      |
|  worst run above T=10.6  |     3.9 sd     |     3.5 sd     |     3.4 sd     |
|         verdicts         |    6x GREEN    |    6x GREEN    |  12/12 GREEN   |
+--------------------------+----------------+----------------+----------------+
```

**Three things to read off it directly:**

1. **`A_Sor_lb` declines monotonically in both series** (1.096 → 1.002; 1.188 → 1.062) while `A_Q_lb` holds
   almost constant. A settling fill, not fill-to-fill scatter → these were re-seats (§16.11.7).
2. **`S/Q plain` and `S/Q_lin` disagree about which runs are outliers.** B/002 is the plain ratio's extreme
   (6.864) and the linear baseline's near-median. C/003 likewise (5.626 plain, 12.204 lin). The metric is
   *rejecting* exactly the runs the plain ratio over-reacts to (§16.11.5).
3. **`S/Q_lin` never comes within 1.2 units of the threshold** in twelve runs across two dilutions.

### 16.11.4 ⚠ What actually caused the gain — the CONCENTRATION, not the protocol

Two variables moved at once: a fresh, properly-concentrated dilution **and** the marked-line protocol. The
arithmetic assigns almost all of it to the oil.

| | aged triplet | fresh sets |
|---|---|---|
| A_Q raw | 0.126 | 0.197 / 0.230 |
| error amplification `0.434/A_Q` | 3.42 | 2.21 |
| linear-baseline CV | 4.95 % | 2.96 % |

> Rescale the aged set's 4.95 % for the A_Q change **alone**: `4.95 × 0.126/0.197` = **3.17 %**.
> Observed: **2.96 %**. → **concentration explains ~93 % of the improvement.**

The direct evidence agrees. Pairwise `phosphor/pump` tilt on the fresh sets is **2.10 % (reference) / 2.00 %
(sample)** — statistically the same as the aged set's 2.2 / 3.1 %, and set B run 002 is the largest single tilt
event in either. `F = 2.80, p = 0.15` on the CV difference: not significant on its own.

**On the raw numbers the marked-line protocol has no demonstrated effect on tilt.** It may still be doing
something (§16.11.7 shows the late runs of both sets are exceptionally clean) but this experiment cannot
attribute it, because the oil changed in the same step. **The only clean test is the unrun `cone` arm** — empty
beam, no oil, and the marked line is exactly what that arm disturbs.

Corollary, and it retires an open question: **the aged dilution's low A_Q was the ageing, not the recipe.**
A 24 h-old dilution read 0.126 where a fresh one reads 0.197–0.230.

### 16.11.5 ⭐ The linear baseline eating a tilt event — the clearest case in the record

Set B run **002** took a large tilt: slope **−0.0398 A/100 nm** against the median, twice anything in the aged
set; raw Q 0.160 where the others read ~0.20; clarity 0.077 against ~0.092.

| | run 002 | the other five | CV all 6 | CV dropping 002 |
|---|---|---|---|---|
| plain S/Q | **6.864** | 5.2–5.5 | **11.13 %** | 1.77 % |
| S/Q linear baseline | **13.021** | 12.0–12.7 | **2.96 %** | 2.37 % |

The plain ratio is wrecked — 002 inflates its CV **6.3×** and would have reported a spectacularly green oil. The
linear baseline places it mid-pack; the same event costs it a factor of **1.25**.

The aged triplet showed the identical mechanism at smaller scale: its run 001 carried by far the worst tilt, and
came out as the plain ratio's *outlier* (5.452, highest of three) but the linear baseline's *median* (10.441).

**This is the strongest evidence yet for the shipped metric, and it is exactly the behaviour §16.10.2 predicted
but had never caught in a single identifiable run.**

### 16.11.6 Dilution invariance — first evidence, and §16.10.8 is partially unblocked

Sets B and C are two different dilutions of the same oil, **17 % apart in A_Q** (0.197 → 0.230).

| | |
|---|---|
| metric means | 12.489 vs 12.251 — a **1.9 %** difference |
| significance | `t = 1.14, p = 0.28` — **not significant** |
| pooled CV across both dilutions | 2.96 % — *identical* to each set alone |
| against the old σ_fill of 9.7 % | a gap this small had only an **11 %** chance of occurring |

**The between-dilution term adds nothing measurable.** §16.10.8 declared dilution invariance *unmeasurable*
because seating noise produced a spread as large as a deliberate 2.19× dilution change; that is no longer true,
because σ finally dropped enough to see past it.

⚠ **This does not resolve §16.10.8.** n = 2 dilutions, only 17 % apart, where the failed test used 2.19×. It is
the first evidence in the right direction and nothing more. §16.11.8 also gives a mechanism by which invariance
*must* fail at higher concentration.

> **§16.14 (2026-07-31) reads these two numbers as a bound.** The 1.9 %-over-17 % gives an apparent log–log
> slope of ≈ −0.12 ⇒ a pedestal-curvature residual `|r_Q| ≲ 0.01 A` — an **upper bound**, not a measurement
> (`p = 0.28`, `n = 2`, and `A_Q` is a compromised concentration proxy). The sign is the direction a curved
> pedestal predicts. §16.14.6 also explains why §16.11.8's high-concentration failure and this
> low-concentration one are *different* mechanisms, making the total error **U-shaped** in concentration.

### 16.11.7 A fresh dilution is NOT stable for its first ~15 minutes — and this killed the learning hypothesis

Absorbance tilt vs each set's median, **in run order**:

| run | set B slope (ΔA/100 nm) | set C slope |
|---|---|---|
| 001 | −0.0204 | −0.0188 |
| 002 | **−0.0398** | −0.0210 |
| 003 | +0.0004 | −0.0188 |
| 004 | +0.0087 | +0.0055 |
| 005 | −0.0016 | +0.0035 |
| 006 | +0.0092 | +0.0123 |

Every tilt event is an **early** run, in both sets independently. Set B ran 22:39→23:07, set C 23:35→00:08, and
in both the runs stop tilting about **11 minutes in**. Two supporting signals: the Soret · linear baseline
declines monotonically through each set (B 1.096 → 1.002, C 1.188 → 1.062, ~10 % over 35 min), and the tilt moves
from negative to positive — which is what sedimentation of blue-scattering particles looks like.

**⇒ Protocol: let a fresh dilution equilibrate ~15 min before measuring.** Free, and it should shrink σ_fill too.

This **withdraws** the operator-learning reading offered when only set B existed ("both events were the first two
runs, probably getting the knack of the marked line"). It was flagged at the time as a post-hoc selection and
therefore §16.10.16's trap; set C's independent replication of the *same time pattern* shows the cause is the
liquid, not the operator. It also means the monotone decline is **one fill settling** — confirming these were
re-seats, not fills.

### 16.11.8 ⚠ Soret STRAY-LIGHT compression — do NOT raise the concentration

Signal levels in the Soret band:

| | reference | sample | A_Soret | T |
|---|---|---|---|---|
| set B | 110.2 DN | **14.8 DN** | 1.09 | 8.1 % |
| set C | 111.4 DN | **12.8 DN** | 1.19 | **6.5 %** |

From B to C, raw Q rose **+16.8 %** but Soret only **+6.9 %**. Under Beer-Lambert both scale identically. **A
numerator that under-responds at high absorbance is the textbook signature of stray light / offset compression**,
and T < 10 % is where it always begins. Reconciling the two sets requires ~9 DN of additive stray light, ~8 % of
the reference level.

**This withdraws the recommendation to raise concentration toward the recipe's A_Q = 0.225** (offered while
diagnosing the aged oil's weak Q denominator, §16.11.10). The rig is at the top of its usable absorbance range:
more concentration compresses the numerator and would **break** the dilution invariance §16.11.6 just found.

Caveats: a two-point comparison, and the two dilutions may differ in more than concentration. But **12 DN of
signal is marginal on its own merits** regardless of the fit, and it is cheap to check — the probe already
captures dark frames at the operating exposure.

### 16.11.9 The error budget now CLOSES — three convergent measurements

§16.7.0's budget accounted for only ~76 % of the observed scatter. It now closes:

| basis | predicted | observed |
|---|---|---|
| `jar` arm 1.34 %, 2 jar ops, at the aged oil's A_Q 0.126 → plain S/Q | 6.5 % | **6.95 %** *(aged triplet)* |
| same, ×0.71 for the linear baseline, at the fresh oil's A_Q 0.197 | 2.98 % | **2.96 %** *(set B)* |
| aged set's 4.95 % rescaled for A_Q alone | 3.17 % | 2.96 % |

The first two are the notable ones: **a tilt probe run on a blank with no oil in the beam predicts the scatter of
six real oil measurements.** (The 0.71 linear-baseline factor was fitted on the aged triplet, so row 2 is not a
fully out-of-sample prediction; rows 1 and 3 are.)

### 16.11.10 Claims made and WITHDRAWN during the rebuild *(kept deliberately, per §16.7.0's practice)*

| claim | withdrawn because |
|---|---|
| "the aged triplet's tilt looks like LED phosphor thermal drift" *(monotone `phosphor/pump` decline)* | the `jar` arm predicts the same scatter from seating alone (§16.11.9); n=3 could not tell drift from a heavy tail |
| "σ went 9.7 % → 4.95 %, a 2× win" | **9.7 % is fill-to-fill** (§16.10.11a) and contains sample prep; 4.95 % and 2.96 % are **re-seat only**. Invalid comparison — see §16.11.11 |
| "raise the concentration to A_Q 0.225 to strengthen the Q denominator" | §16.11.8 — the Soret band is already stray-light compressed at T = 6.5 % |
| "the two tilt events were the first two runs → operator learning on the marked line" | §16.11.7 — set C replicates the *time* pattern, so it is the dilution settling |
| "the marked-line protocol delivered the sub-3 % CV" | §16.11.4 — concentration explains ~93 %; the protocol is untested until the `cone` arm runs |

### 16.11.11 ▶ Next, in order *(Edwin marked these 2026-07-30; the D/E split is the merge of his steps 2 and 3)*

1. **⭐ The `cone` arm** — `diagnostics/reseat_all.sh cone holder stack`. Ten minutes, empty beam, no oil, and the
   rig is already set up for it. **The only clean test of the marked-line protocol** (§16.11.4 cannot attribute it
   because the oil changed in the same step). Also splits the 1.34 % composite via `√(jar² − cone²)`, which
   matters now that the cone's old 0.39 % is no longer negligible inside it. Do this first.
2. **⭐ THE BROWN OIL, 12 runs as two series** — one session, and it answers **both** remaining questions on the
   class where the risk actually lives (§16.11.12):
   - **series D — brown, 6 RE-SEATS of one fill.** Directly comparable to B and C, so it yields the brown σ that
     decides the discrimination question. This is the load-bearing measurement of the whole milestone.
     ✅ **RUN 2026-07-31 — §16.13. σ = 0.131 (raw CV 1.41 %, residual 1.58 %), PASS; *d* = 11.13 (9.80
     df-weighted, §16.13.5); brown clears
     T = 10.6 by 9.88 σ.** The discrimination question is answered on re-seat data.
   - **series E — brown, 6 SEPARATE FILLS**, one stock, each given ~15 min to equilibrate (§16.11.7). Yields
     **σ_fill** — the quantity §16.10.17b's decision table is built on, still unmeasured because everything in
     §16.11.3 is re-seat-only.

   σ_fill cannot be reasoned out: drop-count error (±10–20 %) changes concentration, which a *dilution-invariant*
   ratio should cancel entirely — §16.11.6 suggests it largely does, but §16.10.8 is not resolved. Outcomes for
   E: **~3 %** → invariance holds in practice, apply the projection below; **~5–6 %** → prep adds a modest term,
   median-of-3 still wanted; **~9 %** → prep dominates, mechanical work is **done**, and attention moves to
   §16.10.12's B4 (weigh the oil, ~€15 scale).
3. **Green, 6 separate fills** — demoted, and deliberately. Green now sits **4.82 σ** clear of the threshold
   (§16.11.12), so even a 3× worse σ_fill leaves it decided. Brown's fills are worth more than green's.
4. **`camera` with the diffuser fitted.** §16.7.2g withdrew the diffuser A/B because jar noise buried it. At
   1.98 %/mm, camera alignment is the variable the diffuser targets and the sensitivity is finally large enough
   to measure the difference cleanly. Mount it to the cone, not the jar (§16.7.2n).
5. **Stray-light check on the Soret band** if series D/E confirm the numerator misbehaving (§16.11.8).

#### What σ = 0.367 would do to the decision table — CONDITIONAL on step 2's series E

Not to be shipped until σ is measured **from fills**. Recorded because the consequence is large:

| | shipped (σ₁ = 1.04) | projected (σ₁ = 0.367) |
|---|---|---|
| fill-1 GREEN gate | 13.28 | **11.55** |
| fill-1 BROWN gate | 7.92 | 9.65 |
| median-of-3 gates | ≥ 11.60 / ≤ 9.60 | ≥ 10.95 / ≤ 10.25 |
| the 12 runs of §16.11.3 clearing on ONE fill | **0/12** | **12/12** |
| brown `20260727C` (mean 9.361) deciding on ONE fill | no | **yes** (≤ 9.65) |

That is §16.10.17b's "always three fills" compromise becoming unnecessary for most samples — the outcome
§16.10.11a priced at "from deciding 40 % of samples to deciding 84 %". **It hangs entirely on step 2.**

### 16.11.12 ⭐ Does green-vs-brown discrimination now work? — the gap never moved, the SCATTER did *(2026-07-30, Edwin's read, checked against the archived brown data)*

Edwin's judgement after the rebuild: *"we could reach our goal of discriminating green versus brown."* Checked
against the brown oil already on file — `20260727C`, 6 fills, mean **9.361**, CV 8.9 % (§16.10.2). **The archived
data supports it, with one named assumption.**

| | old rig | today |
|---|---|---|
| green mean | 12.130 | **12.370** |
| brown mean (`20260727C`) | 9.361 | *not re-measured* |
| **class gap** | 3.0 units = **27.7 %** | **unchanged** |
| green σ | 1.322 | **0.367** |

**The classes were always 27.7 % apart.** Discrimination failed because σ was a third of the gap; it is now an
eighth. Nothing about the oils or the metric changed — only the instrument's noise.

| scenario | Cohen's d | green reads BROWN | brown reads GREEN |
|---|---|---|---|
| old rig (the d = 2.88 regime of §16.10.13) | 2.72 | 9.0 % | 6.9 % |
| **today — green measured, brown ASSUMED unchanged** | **4.67** | **0.03 %** | **9.9 %** |
| today — brown improves by green's factor (0.28×) | **9.81** | 0.03 % | **0.15 %** |

*t-distribution on the real dof, per §16.10.11a — the error is heavy-tailed, so the Gaussian is optimistic
exactly where it matters. Gaussian would read 0.0001 % / 6.8 % on row 2.*

**The green side is finished.** 4.82 σ clear of T = 10.6; a green oil misreading as brown is a ~1-in-3700 event
on a single fill. That is better than the state §16.10.11a priced at "deciding 84 % of samples".

**The brown side carries all the remaining risk — and it is the expensive direction.** ~10 % false-GREEN on one
fill, which is precisely the failure §16.10.17d chose T = 10.6 to avoid. That figure is inherited entirely from
old-rig, old-oil, fill-to-fill data and has not been re-measured.

#### Why brown is EXPECTED to improve — §16.7.2o's sobering finding, re-read

§16.7.2o measured brown CV **11.4 %** against green **11.2 %** and called it sobering: Edwin's hypothesis that
the brown class would be inherently steadier was refuted. **That refutation is now the strongest argument in
favour.** Brown scattering *like* green means brown's error had the **same source** — seating, not anything
oil-specific. The fix that took green 11.2 % → 2.96 % therefore has no mechanism by which to skip brown.

⚠ **This is a prediction, not a result.** It is exactly what series D measures, and the two outcomes are both
informative:

| series D returns | reading |
|---|---|
| σ ≈ 0.23–0.37 | brown improved with green → **discrimination is proven**, re-derive the decision table |
| σ ≈ 0.83 (unchanged) | the rebuild helped green only → something oil-specific in the brown, itself a finding |

✅ **RESOLVED 2026-07-31 — §16.13. σ = 0.131**, below the good branch's floor: brown improved *more* than green
did, and the "expected to improve" argument above was right for the reason it gave. Measured *d* = **11.13**
*(RMS pooled SD, unequal n — **9.80** df-weighted, §16.13.5)*, against the 4.67 of this section's row 2 and
the 9.81 of its optimistic row 3. ⚠ Those two projections were themselves computed RMS-style, so the
comparison is like-for-like. **Brown's ~10 % false-GREEN is
0.009 %** (0.50 % at the 95 % upper bound on σ). ⚠ Still **re-seats, not fills** — §16.13.6.

⚠ **Caveats on the arithmetic above, all pointing the same way (optimistic):** the brown mean is old-rig / FILLS
while the green is rebuilt-rig / RE-SEATS; the green mean moved +2 % between vintages so the gap mixes them; the
brown groups are n = 6; and the tails are heavy (§16.7.2f), which the t-correction only partly absorbs. **None of
this touches the central point** — the gap is 27.7 % and green's σ is 2.96 %, both measured, and that ratio is
what discrimination depends on.

**⇒ `SPEC_capability_proof.md`'s go/no-go gate is within reach of one brown session.** §16.11.11 step 2 is the
measurement that closes it.

### 16.11.13 What σ = 0.367 does to "first measurement gives the verdict" — the architecture INVERTS *(Edwin's question 2026-07-30; DESIGN, conditional on series D — do NOT ship before it)*

§16.10.17b's shipped decision table stays authoritative until series D and E land. This section records what
follows *if* brown behaves like today's green (§16.11.12's assumption), because the consequence is not a
parameter change — it is a different protocol shape.

⚠ **Status 2026-07-31: series D has landed (§16.13) and it supports the assumption — but this section is
STILL GATED, on series E.** Every gate multiplier below is derived from **σ₁, the single-*fill* σ**; series D
measured re-seats of one fill, which excludes sample preparation entirely. σ_fill is unmeasured. **Nothing here
ships until series E reports.**

**How often ONE fill decides**, for this green oil (mean 12.370) and the archived brown `20260727C` (mean 9.361),
at T = 10.6. Gates are `T ± k·σ` on a **single pooled σ** — the operator does not know the class in advance:

| σ₁ | gates BROWN / GREEN | green decided | brown decided | actual misclassification |
|---|---|---|---|---|
| **1.04 — SHIPPED (§16.10.17b)** | 7.92 / 13.28 | **19 %** | **8 %** | — |
| 0.367 conservative, 99 % | 9.65 / 11.55 | 98.8 % | 78.7 % | 1·10⁻⁹ |
| **0.367 conservative, 95 %** ← recommended | **9.88 / 11.32** | **99.8 %** | **92.2 %** | 5·10⁻⁸ |
| 0.367 conservative, 90 % | 10.00 / 11.20 | 99.9 % | 95.8 % | 3·10⁻⁷ |
| 0.307 expected (brown scales 0.28×), 99 % | 9.81 / 11.39 | 99.6 % | 97.4 % | 1·10⁻¹² |

*Normal-tail arithmetic, to stay comparable with §16.10.17b's own 2.58/1.96 multipliers. §16.10.11a's heavy-tail
correction applies and makes the ÜBERGANG rates somewhat worse; it does not move the misclassification column,
which is buried many σ deep either way.*

#### (a) "Always three fills" flips from nearly free to expensive

§16.10.17b chose **"always three fills, no early exit"**, calling the shortcut *crude alpha-spending* and worth
skipping. **That reasoning was correct for σ = 1.04** — the shortcut fired on only 19 % of green and 8 % of brown
samples, so mandating three fills cost almost nothing that wasn't going to be spent anyway.

At σ = 0.367 the shortcut fires on **~99 %** of samples. Mandating three fills would **triple the operator's work
on nearly every measurement for zero information gain.** The recommendation therefore reverses: **the one-fill
path becomes the normal path and the three-fill sequence becomes the exception.**

⚠ **And this is statistically CLEANER, not dirtier** — which is the counter-intuitive part. A two-stage test that
*usually continues* carries real alpha-spending problems; a one-stage test with a *rare* fallback carries almost
none. §16.10.17b's warning was aimed at the first shape. The new numbers put us in the second.

#### (b) The gate multiplier stops controlling the error rate — so choose it for the OPERATOR

Read the misclassification column: **10⁻⁹ to 10⁻⁷ regardless of the gate.** With a 27.7 % class gap against a
2.96 % σ (§16.11.12), real errors are set by class *separation*, not by gate placement. What the gate still
controls is only **how often ÜBERGANG fires** — 21 % of browns at 99 %, 7.8 % at 95 %, 4.2 % at 90 %.

**⇒ Pick the multiplier for user experience, not for statistics. Recommend 95 %:** it costs nothing measurable in
error rate and cuts the brown fallback rate ~3× against the 99 % gate.

This retires a habit worth naming: on the old rig, tightening the gate genuinely bought accuracy. It no longer
does. Tightening now only buys *more re-measurements*.

#### (c) The asymmetry survives — and creates a NEW human risk

Green needs the fallback **0.2 %** of the time, brown **7.8 %** (95 % gates, conservative σ). The residual
uncertainty concentrates on the class where being wrong is expensive — the safe direction, and §16.10.17d's
threshold choice working exactly as intended.

But it means **an ÜBERGANG is almost always a brown sample** (~97 % of them, at these class frequencies). That
makes §16.10.17c's decision to **withhold the direction** *more* load-bearing than when it was written, not less:

> An operator who notices that "measure again" nearly always ends in BROWN will begin treating ÜBERGANG **as** a
> brown verdict and stop bothering with the two confirming fills. That reintroduces §16.10.16's optional-stopping
> bias **through the human**, where no amount of statistics in the instrument can see it.

The wording must survive an operator who has seen the message fifty times. §16.10.17c's text was written for a
screen the user met occasionally; it now needs to hold up as a routine screen shown to one class of sample.

#### The proposed shape

```
ONE fill
   >= 11.32   ->  GREEN,  done              (T + 1.96 sigma_1)
   <=  9.88   ->  BROWN,  done              (T - 1.96 sigma_1)
   else       ->  ÜBERGANG -> two more fills, verdict on the MEDIAN of 3
```

One measurement, three outcomes, decided in ~99 % of green and ~92 % of brown cases. Against §16.10.17b's
"prepare three fills, always" that is a materially different product, and the first time the measurements have
supported it.

#### ⚠ What the "96 %" is NOT — the rate is a property of the OIL POPULATION, not of the instrument

A 50/50 mix of our two oils decides on one fill **96.0 %** of the time. That number is *"96 % of measurements of
these two oils"* — **not** 96 % of samples a miller brings in. Per-oil, at the 95 % gates:

| oil | µ | decides on ONE fill |
|---|---|---|
| our green (B+C, measured) | 12.370 | **99.8 %** |
| archived brown `20260727C` — the **mild** one | 9.361 | **92.1 %** |
| archived brown `D` — strongly brown | 8.440 | 100.0 % |
| green `E006` — the worst green on record (§16.10.17d) | 10.565 | **5.1 %** |
| `B008` — sat 0.004 above the old threshold (§16.10.17d) | 10.604 | **5.0 %** |
| an oil sitting exactly **at** T | 10.600 | **5.0 %** |

Blended over an assumed population instead of two known oils — **this is the commercially relevant number**:

| assumed distribution of real oils | decides on one fill |
|---|---|
| all clearly green (11.8–13.0) | 98.6 % |
| all clearly brown (9.0–10.0) | 78.7 % |
| **uniform across the whole observed range (9.0–13.0)** | **64.1 %** |
| concentrated near the threshold (10.0–11.5) | 23.3 % |

**⇒ The defensible claim is "a clearly-green or clearly-brown oil now decides in ONE measurement."** The claim
*"95 % of measurements give an instant verdict"* is **not** supported — it requires knowing how many real oils sit
near the boundary, and two oils cannot tell us. We have no data on that distribution.

This is not a defect. An oil truly at 10.6 **should** return ÜBERGANG, and §16.10.11a's principle stands:
certainty where none exists is worse than useless. But it does mean the ÜBERGANG rate cannot be quoted as an
instrument specification — it is half instrument, half agronomy.

#### The assumption chain behind any of these numbers, worst first

1. **T = 10.6 actually divides green from brown oil.** **UNVALIDATED**, and independent of everything in §16.11.
   §16.10.11a states it exactly: `P = 0.964` is P(the *metric* is above the threshold), *not* P(the oil is green).
   **Everything measured on 2026-07-29/30 improved PRECISION, not CORRECTNESS** — and a precise instrument
   reading a wrong threshold is confidently wrong 96 % of the time. Needs reference oils with independent ground
   truth; that is `SPEC_capability_proof.md`'s territory and the reason the lab-as-channel-partner route exists.
2. **Brown σ improves like green's** — series D (§16.11.11).
3. **σ_fill ≈ σ_reseat** — series E (§16.11.11).
4. **Normal tails.** The error is heavy-tailed (§16.7.2f), so every percentage in §16.11.13 is optimistic.
5. **These two oils represent the population** — the tables above.

Items 2–3 are one brown session away. Item 1 is not an instrument problem and **no amount of mechanical work will
close it.**

**⭐ The real milestone of the rebuild, stated precisely:** the instrument is now precise enough that **the
threshold's correctness has become the binding constraint.** It never was before — seating noise swamped it. That
reframes the next phase of the project from instrument work to validation work.

#### What must NOT change yet

| | |
|---|---|
| **σ₁ = 0.367** | green only, and **RE-SEAT only** — series E measures the fill term |
| **brown σ** | assumed, never measured on the rebuilt rig — series D |
| **the shipped gates** | §16.10.17b's 13.28 / 7.92 / 11.60 / 9.60 remain authoritative until D and E |
| **the stopping rule** | still must be **fixed in advance** (§16.10.17b's ⚠). Moving from "always 3" to "1, then 3 if ÜBERGANG" is a change to a pre-registered rule and must be decided *before* the brown data is seen, not after |

That last row matters more than it looks: choosing the protocol shape *after* seeing series D would be the same
optional-stopping error one level up. **The decision to adopt this shape should be made now, conditional on
D's σ, with the acceptance criterion written down first.**

⚠ **Open decision for Edwin (recommend deciding BEFORE series D runs):** adopt the one-fill-plus-fallback shape
if series D returns brown σ ≤ 0.45, at 95 % gates? Or keep "always three fills" regardless, buying a simpler
story and an unimpeachable stopping rule at 3× the operator time?

### 16.11.14 The Soret band's LEFT EDGE — Edwin's "Knick" at 440 nm is real, moving the edge is REFUTED *(Edwin's question 2026-07-30, tested on series B + C + brown `20260727C`)*

Edwin: *"the left interval of the Soret band at 440 nm might not be the best to use — there is a small Knick
there — would starting at say 443 nm be better?"* **The observation is correct and its cause is worse than a
spectral feature. Moving the edge is nevertheless refuted: every alternative tested is worse on separation.**

#### The Knick is absorbance SATURATION at the ROI boundary, not a feature of the oil

| set | ref DN @ 440 | **sample DN @ 440** | A | T |
|---|---|---|---|---|
| B | 87.3 | **0.85** | 2.02 | 1.0 % |
| C | 88.3 | **0.65** | 2.14 | 0.7 % |

**Sub-1 DN.** Most pixels read 0; the value is set by dark offset and stray light, not by the oil. Two
corroborating signs: the first bin's gradient is **−0.53 A/nm** against a typical −0.05…−0.15, and **439.97 nm is
the first bin in the data** — there is nothing to its left, so the "bend" is the curve flattening as it runs out
of signal at the ROI edge. Signal only recovers around **448–451 nm** (5.9–7.5 DN at 448.6, 13–15 DN at 451.5).

⇒ **Bins 440–447 are, strictly, not measurements.** This is a *direct observation* of the dynamic-range problem
§16.11.8 inferred from the B→C non-proportionality — which hardens "do NOT raise the concentration" from a
two-point argument into something visible in the raw DN.

#### Sweep 1 — moving the left edge, band right edge held at 460

| Soret left | B CV | C CV | brown CV | **d** | gap/CV | metric mean (B) |
|---|---|---|---|---|---|---|
| **440 — SHIPPED** | 2.97 % | 2.90 % | 8.93 % | **4.64** | 9.3 | 12.498 |
| 441 | 2.92 % | 2.97 % | 9.08 % | 4.59 | 9.2 | 11.961 |
| 442 | 2.94 % | 2.92 % | 9.17 % | 4.63 | 9.4 | 11.429 |
| **443 — Edwin's proposal** | 2.97 % | 2.97 % | 9.22 % | **4.67** | 9.5 | 10.885 |
| 445 | 2.91 % | 3.24 % | 9.39 % | 4.61 | 9.4 | 9.811 |
| 448 | 2.89 % | 3.40 % | 9.67 % | 4.62 | 9.5 | 8.375 |
| 450 | 2.76 % | 3.50 % | 9.88 % | 4.61 | 9.6 | 7.471 |
| 455 | 2.88 % | 4.06 % | 10.52 % | 4.37 | 8.9 | 5.710 |

**Flat.** A 20 nm band mean averages the 3–5 bad bins away. 443's `d` = 4.67 against 440's 4.64 is noise, not
signal. **No statistical case for the change on this test.**

#### Sweep 2 — the DECISIVE test: fixed 20 nm width, band slid right

Sweep 1 confounds two effects — discarding bad bins *and* narrowing the band. Holding the width constant
separates them:

| band | B CV | C CV | brown CV | **d** | gap/CV |
|---|---|---|---|---|---|
| **440–460 — SHIPPED** | 2.97 % | **2.90 %** | **8.93 %** | **4.64** | **9.3** |
| 443–463 | 2.95 % | 3.09 % | 9.32 % | 4.62 | 9.4 |
| 445–465 | 2.87 % | 3.50 % | 9.61 % | 4.50 | 9.1 |
| 448–468 | 2.83 % | 3.89 % | 10.13 % | 4.41 | 8.9 |
| 450–470 | 2.74 % | 4.24 % | 10.61 % | 4.29 | 8.6 |
| 453–473 | 2.77 % | 4.81 % | 11.38 % | 4.13 | 8.1 |

**Sliding right monotonically degrades set C, the brown oil, and `d`.** Set B improves slightly — but B is the
*less* concentrated sample, i.e. the easy case; every harder case gets worse. **440–460 is the best band of the
six.**

**Mechanism:** the Soret slope is steep here, so sliding right lands on the flank where absolute absorbance is
lower. Class contrast is lost faster than noise is gained back by discarding the dim bins.

#### Two tempting readings, both rejected

| reading | why rejected |
|---|---|
| "B-vs-C agreement improves as the edge moves right (1.93 % → 0.93 %), exactly as stray light predicts" | **1.15 σ → 0.46 σ** on n = **2** dilutions. The right prediction with no power behind it. Do not quote it. |
| "443 gives the best `d`, so adopt it" | 4.67 vs 4.64 — inside the noise, and sweep 2 shows the direction is wrong once band width is held constant |

#### Cost of changing it, and when to revisit

440 → 443 moves the metric **12.50 → 10.89 (−13 %)**, so T = 10.6 would become ~9.2 and **all of §16.10.17d's
threshold work would need redoing.** For no measurable gain, that is not a trade worth making.

**⇒ DECISION: keep 440–460. ▶ REVISIT at the next threshold recalibration** — which is coming anyway (series D/E,
then the validation phase of §16.11.13). At that point the edge moves for free, and it should be chosen on a
**signal-floor criterion** — e.g. require sample DN ≥ 10, which lands at **~450 nm** — rather than inherited from
wherever the ROI happens to end. Doing it then costs nothing; doing it now costs the threshold.

**A quiet win worth recording:** a metric whose band includes bins carrying **0.85 DN** still returns CV 2.9 % and
`d` = 4.6. The linear baseline plus band-averaging is more robust than it had any right to be.

### 16.11.15 The DILUTION recipe — keep 18 ml + 6 drops; and a conflict with `SPEC_capability_proof.md` §7.3 *(Edwin proposed 6 → 5 drops, 2026-07-30; REFUTED, but §7.3's premise needs re-testing)*

Edwin: *"I think I should change the default dilution from 18 ml alcohol and 6 drops to 18 ml and 5 drops."*
**Refuted on four checks. Keep 18 ml + 6 drops.** But the question exposed a genuine inconsistency between this
spec and `SPEC_capability_proof.md` §7.3 — recorded at the end, because it matters more than the drop count.

⚠ **TERMINOLOGY, and the source of a real confusion in the 2026-07-30 thread.** *Dilution* and *concentration* are
**inverses**: more drops = more concentrated = **less** diluted. Advice phrased as "lower the dilution" and
"raise the concentration" mean the *same* thing. Prefer stating **A_Q** (measured) or the **ratio** (nominal), never
"stronger/weaker".

#### The operating window — and 6 drops sits inside it

```
   too dilute                      GOOD                     too concentrated
  ─────────────────┬──────────────────────────────────────┬──────────────────
   A_Q < 0.15      │   A_Q 0.19 - 0.23                    │  A_Q > 0.25
   0.434/A_Q       │   <- 18 ml / 6 drops, FRESH,          │  Soret compresses,
   amplification   │      measured within the hour        │  dilution invariance
   blows up        │                                      │  at risk (16.11.8)
   set A: CV 4.95% │   CV 2.9%                            │
```

#### Check 1 — CV tracks 1/A_Q, so a weaker dilution costs precision

| | A_Q | amplification `0.434/A_Q` | CV | n |
|---|---|---|---|---|
| set A (24 h-aged) | 0.126 | 3.44 | **4.95 %** | 3 |
| set B | 0.197 | 2.20 | 2.96 % | 6 |
| set C | 0.230 | 1.89 | **2.89 %** | 6 |

Monotone over three points, and §16.11.4 attributed **93 %** of the B/C gain to exactly this mechanism.
6 → 5 drops is −16.7 %, so A_Q 0.230 → 0.192 and **predicted CV 2.89 % → 3.47 %, ~20 % worse** — the wrong
direction on the one number §16.11.12 and §16.11.13 both rest on.

#### Check 2 — it does not fix the 440 nm floor it was meant to fix

| drops | A @ 440 | sample DN | |
|---|---|---|---|
| 6 | 2.14 | 0.64 | floored |
| **5** | 1.78 | **1.45** | **still floored** |
| 4 | 1.43 | 3.31 | still floored |
| 3 | 1.07 | 7.52 | still floored |

You would have to reach **3 drops** to lift 440 nm to usability — putting A_Q at ~0.115, *worse than the aged
oil*, with CV past 5 %. **The saturation is a dynamic-range problem, not a concentration problem**, and
§16.11.14 already has the free fix (move the band edge at the next recalibration).

#### Check 3 — the compression is not reaching the metric

B → C is a +16.8 % concentration step:

| | Soret | Q | |
|---|---|---|---|
| **raw** bands | +8.5 % | +16.8 % | diverge — §16.11.8's compression |
| after **linear baseline** | +6.9 % | +8.4 % | near-proportional |

The metric moves only **−1.4 %**. The baseline absorbs the compression before it reaches the ratio. So the
*motivation* for backing off — "saturation is corrupting the reading" — does not hold at these levels. §16.11.8
warns against going **higher**; it is not an argument for going lower.

#### Check 4 — one drop is not yet a controllable quantity

Sets B and C differ **16.8 %** in A_Q. If both were nominally the 6-drop recipe, **that 16.8 % IS the drop-size
scatter** (§16.10.12 B4: "2 drops varies 10–20 %") — and one drop is 16.7 %. **Changing the nominal value by
exactly one unit of its own noise cannot be expected to do anything reproducible.** §16.10.12's **B4 (weigh the
oil, ~€15 scale)** is the lever that actually controls concentration; the drop count is not.

#### The advice that was WITHDRAWN, and why it looked like a reversal

Recorded because the sequence confused Edwin, reasonably:

| when | data in hand | advice | status |
|---|---|---|---|
| after set A | A_Q 0.126, amplification 3.42 | "raise the concentration toward A_Q 0.225" | **WITHDRAWN** |
| after set C | Soret 0.65 DN, non-proportional bands | "do not raise it further" (§16.11.8) | stands |
| 2026-07-30 | the three-point trend above | "do not lower it either" | stands |

**The first advice was aimed at the wrong target.** Set A's weak A_Q of 0.126 was the **24-hour ageing, not the
recipe** (§16.11.4) — but that was not yet known when the advice was given. The *same* 18 ml / 6 drops produced
A_Q 0.197 and 0.230 on fresh oil, squarely in range. **The recipe was never the problem; the age of the dilution
was.** Net position across the whole investigation: **18 ml / 6 drops has been correct throughout.**

#### ⇒ The actual guidance is about FRESHNESS, not the drop count

| | A_Q | CV |
|---|---|---|
| 24 h old | 0.126 | 4.95 % |
| fresh | 0.197–0.230 | 2.9 % |

**Prepare fresh, wait ~15 min to settle (§16.11.7), measure within the hour.** That is the whole dilution
protocol, and the 2026-07-29/30 session already followed it.

#### ⚠ OPEN — this contradicts `SPEC_capability_proof.md` §7.3, which was decided on a SIMULATION

§7.3 (revised 2026-07-26) moved the recipe from 1:20 to **1:30–1:33** *because* the sample bottomed out at 440 nm,
and tabulated a simulated **min DN @ 440 = 16 (brown) / 25 (green)** at 1:30. Its own arithmetic ("2 drops in
4 ml ≈ 1:20") implies **1 drop = 0.1 ml**, so **18 ml + 6 drops = 1:30 — exactly what §7.3 prescribes.**

**But the measurement disagrees with the simulation by a wide margin:**

| | @ 440 nm |
|---|---|
| §7.3 simulated at 1:30, green | DN **25** (⇒ A ≈ 1.01) |
| measured 2026-07-29, set B | DN **0.85** |
| measured 2026-07-29, set C | DN **0.65** (A = 2.14) |

At the same *nominal* dilution the oil absorbs **~2.1× more** than §7.3 modelled. If A scales with concentration,
the real ratio is nearer **1:14**, implying a drop of **~0.21 ml, not 0.10 ml**.

*Caveat: §7.3's "DN 25 of 255" may assume a fuller-scale reference than today's 88 DN at 440 nm, which would
absorb part of the gap. **The direction is robust; the factor is not.***

**Two conclusions, and they pull opposite ways — do not resolve this from the armchair:**

1. **We do not know what dilution ratio "18 ml + 6 drops" actually is.** The 1:30 label rests on an assumed drop
   volume that today's absorbance contradicts. **▶ Measure it: weigh 20 drops (B4's scale does this in a minute).**
   Until then every ratio in either spec is nominal.
2. **§7.3's decision criterion has since been tested and does not bind.** §7.3 chose the weaker dilution to keep
   the 440 nm bins out of the sRGB toe. §16.11.14 tested whether those bins hurt the metric — **they do not** (the
   left-edge sweep is flat, and sliding the band away is strictly worse). §7.3 also found the metric's *value*
   invariant across 1:20–1:33 (±0.35 %), which agrees with §16.11.6. What §7.3 never checked is the metric's
   **scatter**, and that is what §16.11.15's Check 1 measures: **scatter goes as 1/A_Q.**

**⇒ Synthesis: among dilutions that are value-invariant, pick the STRONGEST that keeps the bands linear** — the
opposite of §7.3's conclusion, reached because §7.3 optimised the wrong quantity (toe-avoidance) while this
section optimises σ. **Neither spec should be edited until the drop volume is weighed**; §7.3's table is a
simulation, §16.11.15's is a measurement, and the discrepancy is currently unexplained.

---

## 16.12 The settling drift and the solvent question  *(Edwin's research thread 2026-07-30/31; both analyses RUN — see §16.12.11)*

§16.11.7 found that a fresh dilution is not stable for its first ~15 minutes and prescribed a wait. This section
asks *why*, whether the number is standard practice, what the drift costs the metric, and whether the fix is a
protocol step or a change of solvent.

> **⚡ Read §16.12.11 first — it is the measurement, and it overturns half of what precedes it.**
>
> 1. **The drift is real and it reaches the shipped metric.** 58 % of the pooled "seating" variance is a time
>    trend; true seat-to-seat repeatability is **≈1.9 %, not 2.96 %** — which unseats §16.11.9's budget closure
>    and reorders §16.11.11.
> 2. **The mechanism proposed in §16.12.2–§16.12.6 is UNTESTED, not confirmed.** The λ⁻ⁿ fit is anchored on a
>    contaminated window, so §16.12.2–§16.12.6 are kept as the reasoning that led to the test, not as findings.
> 3. **▶ And the test exposed a larger problem than the one it was aimed at: the shipped linear baseline's far
>    anchor (600–630 nm) is NOT oil-quiet — it stands on real green-pigment absorption, 5.1 σ, and ~3.4× more for
>    green than for brown (§16.12.12).** That anchor is load-bearing for every metric we ship, and the leak is
>    class-dependent, so it does not cancel in a ratio. **▶ Next: sweep the far anchor (§16.12.12).**

### 16.12.1 What §16.11.7 established, and what it did not

Established: in sets B and C independently, the absorbance tilt settles about 11 minutes in, the tilt moves
negative → positive, and `Soret · linear baseline` declines monotonically ~10 % over each 35-minute set. The
negative→positive move is the signature of **blue-biased scattering leaving the beam**.

Not established: that the *metric* drifts. Everything above is measured on the Soret band and on the raw tilt.
The shipped metric is a **ratio**, and a ratio cancels any effect that moves numerator and denominator together.
Whether the settling reaches the ratio is the open question of §16.12.5.

**One confound was raised and is REFUTED.** The diary records camera sensor self-heating at τ = 2.9 min, settling
by ~9 min — the same timescale, and it would reproduce the "early runs tilt, in both sets" pattern if the camera
had cooled in the 28-minute gap between B and C. **Edwin (2026-07-30): the camera streamed continuously across
both sets**, so self-heating had long since plateaued. §16.11.7's reading stands: the cause is the liquid.

### 16.12.2 The mechanism has a name — miscibility gap, then the ouzo effect

Oil + 2-propanol is a **partially miscible system with an upper critical solution temperature**. Below the UCST
there is a miscibility gap; solubility rises with temperature until oil and solvent mix in all proportions, and
**water content raises the critical temperature steeply** ([JAOCS, Rao & Arnold 1957](https://link.springer.com/article/10.1007/BF02637892);
[UCST](https://en.wikipedia.org/wiki/Upper_critical_solution_temperature)).

So at room temperature our "dilution" is plausibly not a solution but a **metastable dispersion** — the
[ouzo effect](https://www.sciencedirect.com/topics/agricultural-and-biological-sciences/ouzo-effect): rapid
dilution out of a marginal solvent throws spontaneous nanodroplets which then coarsen by Ostwald ripening
([ACS Cent. Sci. 2023](https://pubs.acs.org/doi/full/10.1021/acscentsci.2c01194)). Fresh unfiltered pumpkin oil
additionally carries waxes, phospholipids and press fines that isopropanol will not dissolve at all.

Small particles scatter as ~λ⁻⁴ (blue-biased); as they ripen and cream out, the blue excess decays — **which is
exactly the sign flip §16.11.7 measured.** Two populations are therefore in play, and they call for different
fixes:

| population | size | dissolves in butanol/heptane? | removable by filter? |
|---|---|---|---|
| waxes, phospholipids, press fines | ~0.5–50 µm | yes | **yes** |
| ouzo nanodroplets | ~50–200 nm | yes (gap closes) | **no** — smaller than any practical pore |

Separating the two is what §16.12.9 is for.

### 16.12.3 Is "~15 min" known in the community? NO — and the literature says CLARIFY, not WAIT

Two pieces of standard guidance were found, they point opposite ways, and **neither supports our wait**:

- *"measure turbid samples within ~10 min of dispensing"* — that is **nephelometry**, where the particles **are
  the analyte** ([JASCO](https://jascoinc.com/wp-content/uploads/2017/10/APP-Note-UV0014-Chromaticity-and-Turbidity.pdf)).
  Opposite situation.
- *"allow 10–15 min equilibration"* — **thermal equilibration and colour development** in wet-chemistry SOPs.
  Different mechanism; the number matching ours is coincidence.

Our case is the third one: **the particles are the interferent.** There the field's answer is not patience — it is
**clarification (filtration or centrifugation) before the cuvette, plus a fitted baseline for the residual.**

Corroborating: the standard oil-pigment methods **do not use neat isopropanol.** Chlorophyll and carotenoids in
oils are read in **cyclohexane** (445/470 nm), **hexane** (442/668 nm), **CCl₄**, or **ethanol + isooctane /
ethanol + heptane** ([Chem. Papers](https://link.springer.com/article/10.2478/s11696-013-0502-x);
[olive-oil pigments](https://www.researchgate.net/publication/265295009_Rapid_Determination_of_Olive_Oil_Chlorophylls_and_Carotenoids_by_Using_Visible_Spectroscopy)).
The field converged on hydrocarbons precisely because they give a true solution.

**⇒ `~15 min` is our instrument's number, not a community constant.** It stays as the interim protocol, but it is a
workaround for a solvent choice, not received practice — which is why §16.12.7 outranks it.

### 16.12.4 ⛔ The linear baseline leaks HALF the scatter into the Soret band — *correct geometry, but the term is NOT PRESENT (§16.12.11 B)*

`PB_BASELINE_WINDOWS = ((520, 540), (600, 630))` — anchors at ~530 and ~615 nm. The Soret band centroid is
**450 nm, i.e. an 80 nm extrapolation beyond the nearest anchor**, which is where a wrong curve shape hurts most.

Scattering goes as **λ⁻ⁿ** (n ≈ 4 for particles ≪ λ, falling toward 0 as they grow into the Mie regime). A straight
line cannot follow it. Let the true scatter be `s·(530/λ)⁴`, amplitude `s` at 530 nm:

| λ | the fitted line subtracts | true λ⁻⁴ scatter | **residual left behind** |
|---|---|---|---|
| 450 nm — Soret | 1.422 s | 1.924 s | **+0.502 s** |
| 530 nm — anchor | 1.000 s | 1.000 s | 0 *(by construction)* |
| 570 nm — Q | 0.789 s | 0.747 s | **−0.041 s** |
| 615 nm — anchor | 0.552 s | 0.552 s | 0 *(by construction)* |

**Half the scatter amplitude survives the correction and lands in the Soret band** — and with the *opposite* sign
in Q, so both errors push the ratio the same way. This is the one mechanism that can carry a settling trend
**through** a ratio.

At §16.11.8's levels (A_Soret ≈ 1.1, A_Q ≈ 0.197) the relative ratio error is `0.502s/1.1 + 0.041s/0.197 ≈ **0.65 s**`.

⚠ **Do not read that as "turbidity costs 3 %".** §16.11.9's budget closes at 2.98 % predicted vs 2.96 % observed
from the `jar` arm alone — there is **no room in that closure for a large turbidity term**, so `s` is bounded from
above by our own data. The **0.65 coefficient is geometry and stands**; the amplitude `s` is unmeasured. §16.12.6
measures it.

### 16.12.5 ⚠ OPEN — is set B's 2.96 % the SETTLING TREND rather than seating noise?

A CV discards run order. Six numbers lying on a descending straight line still spread about their mean, so the CV
is large — but that spread is **structure, not repeatability**, and the CV cannot tell them apart.

A perfect linear ramp of total range R over n points contributes, by itself,
`SD = R·√((n+1)/(12(n−1)))` — at n = 6 that is **0.342·R**. §16.11.7 reports the Soret declining ~9 % across each
set, and **0.342 × 9 % ≈ 3.1 % — essentially the whole observed 2.96 %, with zero measurement noise in it.**

**If the ratio trends the way the Soret does, then §16.11.9's closure is two similar numbers meeting by
coincidence, and the `jar` arm is not the binding constraint.** The saving grace is that a ratio cancels a common
trend — but §16.12.4 is precisely the mechanism that moves Soret and Q *differently*, so it would not cancel.

This must be settled before series D/E, because §16.11.11 step 2 is scoped on the assumption that seating
dominates.

### 16.12.6 ▶ The two free analyses — one sweep, no rig time

`diagnostics/metric_bench.py` already loads these PDFs and pulls the spectra from the embedded workflow JSON.
Datasets: **sets B and C** (6 runs each, §16.11) as the primary target, and the **21 runs of 2026-07-27**
(`20260727B` / `20260727E` / `20260727C`) as the wider sample with both oil classes.

**A · Detrend.** Fit `metric = a + b·t + residual` against **elapsed time** (not run index) and report raw CV vs
**residual** CV. The residual SD is the number that belongs in the error budget.
- residual CV **collapses (≲1.5 %)** → settling dominated set B; §16.11.9's closure is coincidental; §16.11.11
  reorders, liquid over mechanics.
- residual CV **barely moves** → the ratio did cancel the trend; the closure stands; §16.11.7 matters less.

**B · λ⁻ⁿ fit.** Per run, fit `A = k·λ⁻ⁿ` to **all wavelength points inside both baseline windows** (~50 points, so
the fit is over-determined and yields a residual to judge it by), subtract it instead of the straight line, and
recompute.
- **the time series collapses onto its settled value** → mechanism confirmed *and* fixed in software.
- **n lands in 2–4, and n *decreases* run-to-run within a set** → the droplets are growing: Ostwald ripening
  observed directly, from data already on disk.
- **n ≈ 0** → it is a flat offset, not scatter, and §16.12.2 is wrong.

Caveats: fit `n` per run rather than pinning it at 4 (if the droplets grow, n changes); `k` and `n` trade off
against a genuine flat offset; **6 points is an indication, not a verdict** — detrending leaves 4 df, so **pool B
and C** (12 points, shared decay, separate offsets). The physics predicts an exponential relaxation
`a + b·exp(−t/τ)`, which would hand us **τ directly** for comparison against the diary's sensor τ = 2.9 min — but
3 parameters on 6 points is thin. **Linear first; exponential only if the linear residuals show curvature.**

### 16.12.7 ⭐ The solvent — 1-butanol is the branch that retires the others

Isopropanol is a *marginal* solvent for triglycerides; that marginality is the whole problem. The candidates:

| solvent | dissolves oil | polystyrene-safe | practical for a mill | notes |
|---|---|---|---|---|
| **2-propanol** (today) | marginal | ✅ | ✅ drugstore | the miscibility gap ⇒ §16.12.2 |
| **1-propanol** | better (linear, not branched) | ✅ | ~ specialist supplier | gentle intermediate step |
| **1-butanol** | **good** | ✅ rated at 20 °C | ~ specialist supplier, cheap | bp 118 °C, flash 35 °C; **odour to be tested** |
| **n-heptane** | ideal | ❌ **dissolves PS** | ❌ H225/H304/H411 | bench reference method only |

**1-butanol is strategically the strongest option, because one swap potentially retires three other work items at
once:** polystyrene-safe → **no container work, no FEP window, no milling**; a genuine triglyceride solvent →
**dissolves the waxes rather than requiring their removal, so no filter and no per-measurement consumable**; closes
the miscibility gap → **no ouzo dispersion and no 15-minute wait.** Edwin 2026-07-31: cost and availability are
both acceptable via specialist suppliers. **Marked as a track to try in practice.**

Open items on it: (a) **odour** — 1-butanol's odour threshold is low and persistent, and an Ölmühle is a food
premises; the quantity is ~4 ml in a closed jar so emission is small, but this is a *check*, not an assumption;
(b) **crazing** — soak a spare PS jar overnight, because alcohols craze *stressed* polystyrene even when the chart
says "good", and injection-moulded jars are full of frozen-in stress; (c) **solvatochromism** — the pigment's Soret
and Q positions shift with solvent polarity (protochlorophyllide's Qy alone moves 623→626 nm between acetone and
methanol, `KB_spectroscopy_physics.md` §4.1), so `PB_SORET_BAND` / `PB_Q_BAND` and any threshold must be re-derived.
Edwin 2026-07-30: **acceptable, no valid threshold is load-bearing yet.**

**n-Heptane keeps one valuable role: a bench-only reference method.** Run one oil in both solvents and the
difference **is** the measured cost of the IPA dispersion — it converts an unknown into a number, and it never
ships.

### 16.12.8 The container problem is DOWNSTREAM of the solvent — do not buy anything yet

Only relevant **if heptane becomes necessary**. Every good triglyceride solvent attacks polystyrene; alcohols are
essentially the only PS-safe organic family, so there is no drop-in. The binding constraint is that **light passes
through the jar AND the lid — both must be transparent** (Edwin), and a clear jar with a matching clear lid is not
an off-the-shelf glass item.

- ⭐ **Milled glass lid + FEP window** *(Edwin's proposal, best of the options)*. Mill an aperture in a glass jar's
  lid and clamp a fluorinated-ethylene-propylene film disc over it. FEP is >95 % transmissive across 400–700 nm
  with <2 % haze at 100–200 µm ([FEP properties](https://eureka.patsnap.com/materials/fep-film-properties-applications),
  [AdTech transmission data](https://adtech.co.uk/technical-data/fep-uv-transmission-data/)) and chemically immune
  to everything under discussion. Sold cheaply as resin-3D-printer sheet.
  - **Clamp, never glue** — FEP's non-stick nature is the same property that makes it solvent-proof; use an O-ring
    groove or a screwed retaining ring.
  - **Tension sets flatness** — a sagging film is a weak lens with run-to-run variation.
  - **Possible bonus:** n(FEP) ≈ 1.344 against IPA 1.377 / heptane 1.387. Overfill so the film **contacts the
    liquid** and that interface reflects ~0.015 % instead of the ~2.5 % of a liquid–air surface — **and the
    meniscus disappears.** The meniscus is a curved surface whose shape varies with fill and tilt, i.e. exactly the
    kind of term that lives in the `jar` arm. Worth a `reseat_all.sh jar` A/B if built.
- **Rig-mounted window, open jar** — make the window part of the *instrument*, not the consumable. Takes the lid
  out of the `jar` arm entirely (it is re-seated every run today) and a fixed element cancels in `S/R`. Cost:
  evaporation from an open vessel.
- **Glass Petri dish** — **rejected** (Edwin): spill risk in handling, and a loose lid on a shallow dish lets the
  fill depth change, which is path length.
- **PMMA lid** — **rejected**: the compatibility charts contradict each other on heptane (C at 20 °C in one,
  aliphatics D in another, acceptable in a third). Not a basis for a measurement instrument.

Whichever is built, `diagnostics/reseat_all.sh jar` gives a quantitative 10-minute A/B against the current 1.34 %.

### 16.12.9 The 0.22 µm PTFE filter — a DIAGNOSTIC, not a protocol step

A disposable Luer-fitted disc holding a solvent-resistant PTFE membrane; the dilution is pushed through from a
syringe. Pigments are **dissolved molecules ~1 nm** and pass freely; waxes and press fines are **particles** that
do not absorb selectively — they scatter, broadband and blue-biased. **So it removes pure interference and keeps
the signal.**

**Use 0.22 µm, and the pore size is the point.** Ouzo nanodroplets (~50–200 nm) are below any practical pore, so
filtration **cannot** remove them. That makes the filter a clean mechanism discriminator:

- **filtering removes the drift** → the culprit was micron-scale particulate ⇒ butanol should dissolve it.
- **filtering does not remove the drift** → true nanodroplets ⇒ only a solvent change can help.

**Both branches point at 1-butanol**, so this is cheap confirmation for the record rather than a fork in the road.

**Demoted from "fix" to "diagnostic" (Edwin 2026-07-31):** ~€1 per filter plus an extra manual step is real
friction for a miller. As a one-off bench test it needs 4–6 filters (~€6). Caveats: some pigment rides on the
removed particles and the membrane can adsorb a little — both effects are roughly uniform across wavelength, so
they shift absolute A but should barely touch a **ratio**. Validate by splitting one fill: if A_Q drops somewhat
but the ratio holds, it is clean. *(If clarification ever were needed as a shipped step, a ~€40 mini-centrifuge
beats filters — one-off cost, no consumable.)*

### 16.12.10 Also worth one cheap check — the isopropanol bottle itself

99 % is fine on the label, but **IPA is strongly hygroscopic** and an opened bottle pulls water from the air
continuously. Per §16.12.2, water content is the *steep* lever on the critical solution temperature. Buy one fresh
sealed ≥99.8 % bottle and compare against the working bottle; if the fresh one is visibly clearer, the solvent has
been quietly degrading across the whole 2026 dataset.

### 16.12.11 ✅ AS-RUN — `diagnostics/settling_sweep.py`, sets B and C  *(2026-07-31)*

Both analyses of §16.12.6 ran on the twelve PDFs already on disk. **Analysis A answers its question yes.
Analysis B refutes the mechanism this section proposed.**

*(Note: the set directories are named `20270729{A,B,C}` on disk — a year typo. File mtimes are the real capture
times and carry the elapsed-time axis, because `header.timestampIso` is `None` in every embedded workflow.)*

#### A · The metric DOES trend with time — and the trend is most of the "seating" scatter

| | raw CV | **residual CV** | trend over set | t *(4 df)* |
|---|---|---|---|---|
| **set B** `S/Q linear base` | 2.96 % | **2.44 %** | −5.38 % | −1.84 |
| **set C** `S/Q linear base` | 2.89 % | **1.09 %** | −6.93 % | **−5.60** ✅ |
| **pooled B+C** `S/Q linear base` | 2.92 % | **1.89 %** | — | — |
| set B `A_Soret raw` | 3.30 % | 1.73 % | −7.82 % | **−3.76** ✅ |
| set C `A_Soret raw` | 4.04 % | 2.07 % | −9.13 % | **−3.87** ✅ |

**⇒ The shipped ratio does NOT cancel the settling.** It declines ~5–7 % across each 30-minute set, replicated in
both, significant in C. §16.12.5's open question is answered: **58 % of the pooled variance is the time trend**
(`1 − (1.89/2.92)²`), and in set C alone **86 %**. The true seat-to-seat repeatability is **≈1.9 %, not 2.96 %.**

**⚠ This compromises §16.11.9's error-budget closure.** The `jar` arm predicted 2.98 % against an observed 2.96 %
— but the observed figure is mostly a settling trend that a blank-beam tilt probe cannot produce. Against the
detrended 1.89 %, the `jar` arm now **over**-predicts by ~1.6×. The three-way convergence was partly two unrelated
numbers landing close together.

**⇒ §16.11.11 reorders: the liquid, not the mechanics, is the binding constraint.** The `cone` arm and the
mechanical programme drop below the dilution work. Series D/E should be planned around this — and series E's
σ_fill, measured with 6 separate fills each given ~15 min, is now the single most informative number available.

#### The complete error table for sets B and C — every quantity that feeds the metric

| | set B raw CV | set B resid | set C raw CV | set C resid | **pooled raw** | **pooled resid** |
|---|---|---|---|---|---|---|
| `S/Q` **raw** *(no baseline)* | 11.14 % | 11.78 % | 5.16 % | 5.71 % | **8.68 %** | 9.26 % |
| `S/Q` **linear baseline** *(shipped)* | 2.96 % | 2.44 % | 2.89 % | **1.09 %** | **2.92 %** | **1.89 %** |
| `S/Q` power baseline *(rejected)* | 4.05 % | 3.60 % | 2.70 % | 0.51 % | 3.44 % | 2.57 % |
| `A_Soret` 440–460 | 3.30 % | 1.73 % | 4.04 % | 2.07 % | 3.69 % | 1.91 % |
| `A_Q` 560–580 | 9.98 % | 11.15 % | 7.52 % | 7.64 % | 8.83 % | 9.56 % |
| `A_near` 520–540 | 9.82 % | 10.65 % | 8.89 % | 7.95 % | 9.36 % | 9.40 % |
| `A_far` 600–630 | 19.91 % | 22.12 % | 13.97 % | 14.84 % | **17.20 %** | 18.84 % |

**⭐ Read the first two rows against the last four.** The shipped metric's 2.92 % is **lower than three of its
own four inputs** — `A_Q` 8.83 %, `A_near` 9.36 %, `A_far` 17.20 % — while the *raw* ratio, built from the same
bands without a baseline, sits at 8.68 %. **The linear baseline is doing common-mode rejection**: a seating tilt
moves all four windows together, and subtracting the fitted line cancels the shared part. That is why a
correction anchored on a **17 %-noisy** window still produces a **3 %** metric, and it is a third independent
reason the baseline earns its place (`SPEC_capability_proof.md` §2.1a).

It is also visible run-by-run: set B's run 002 dips −18.7 % in `A_Q`, −15.9 % in `A_near` and −38.9 % in `A_far`
while `A_Soret` barely moves (+0.6 %). Raw `S/Q` reads it as a wild outlier (6.86 against ~5.3); after the
baseline it is a mild one (13.02 against ~12.4).

**📈 Curves: `spectracs-references/tmp/settling_curves.png`** (`diagnostics/settling_plot.py`) — **six panels** against
elapsed minutes: **A** raw `S/Q`, **B** the shipped baselined `S/Q`, then all four input absorbances as
% deviation (**C** `A_Soret`, **D** `A_Q`, **E** `A_near`, **F** `A_far`). Two things to look at: `A_Soret`
walks steadily downhill in both sets while `A_Q` is flat and noise-dominated — which is why the ratio cannot
cancel the drift — and panels **E/F** show how noisy the two baseline anchors are in their own right, which is
what makes the table above surprising.

*(A_Q raw trends weakly and never significantly; the trend enters the ratio mainly through the Soret numerator.
Set B run 002 is the known §16.11.7 tilt outlier — `A_Q` 0.160 against ~0.20 elsewhere — which inflates set B's
raw-ratio CV to 11 % and is why set B's trend fails significance where set C's does not.)*

#### B · ⛔ The λ⁻ⁿ test is INVALID as run — and it exposed something bigger: **the far baseline anchor is corrupted**

The model-free diagnostic. Ratio of mean absorbance in the near window (520–540) to the far one (600–630):

| predicted by | 530/615 |
|---|---|
| λ⁻⁴ — Rayleigh, particles ≪ λ (ouzo nanodroplets) | 1.81 |
| λ⁻² | 1.35 |
| wavelength-flat — particles ≫ λ (Mie), or a plain offset | 1.00 |
| **measured, all 12 runs** | **0.687 – 1.019, median ≈ 0.73** |

Absorbance in the "oil-quiet" windows is **higher at 615 nm than at 530 nm**; the free-fitted exponent is
**n ≈ −2.6**, i.e. rising as ~λ^+2.6. No scattering law of any particle size is red-biased, so the first reading
was that scattering is refuted. **That reading is wrong, and the cause is worse.** Reference levels, set B/C run
001:

| | 440–460 | 520–540 | 560–580 | 600–630 | **620–630** |
|---|---|---|---|---|---|
| REFERENCE (DN) | 110 | **130** | 65 | 57 | **39** |
| SAMPLE (DN) | 13 | 101 | 40 | 40 | 25 |
| ABSORPTION | 1.16 | 0.11 | 0.22 | 0.16 | **0.20** |

**The CFL reference collapses from 130 DN at the near anchor to 39 DN at the top of the far anchor — a 3.3×
drop — and absorbance rises monotonically as it does.** §9 already put the lamp's useful range at 440–630; the far
window sits **on the cliff edge**, where quantization, residual dark offset and stray light all bias
`−log₁₀(S/R)` at 25–39 DN.

**⇒ The far anchor is inflated by a low-signal artifact, so the power law is fitted through a corrupted point and
its n ≈ −2.6 is meaningless. The scattering hypothesis is UNTESTED, not refuted** — with an unknown artifact δ
subtracted from the far anchor the true ratio could well exceed 1. `S/Q power base` scoring worse than linear
(3.44 % vs 2.92 % pooled) fits this too: a power law is more sensitive to a bad end-anchor than a straight line.

**⚠ The consequence reaches far past this section: the SHIPPED linear baseline uses the same corrupted anchor.**
`PB_BASELINE_WINDOWS`' far window is load-bearing for every metric we ship, and it is standing on the lamp's cliff.

Two candidates were raised for the rise: **(a)** the low-signal bias above, which the DN table made look like the
leading explanation, and **(b)** the rising flank of the pigment's **real** red (Qy) band. **✅ SETTLED the same
day by §16.12.12: (a) is REFUTED and (b) is CONFIRMED at 5.1 σ.**

> ⚠ **The band's identity and position were WRONG throughout §16.12 — corrected 2026-07-31, see
> `KB_spectroscopy_physics.md` §4.1.** This section originally said "the chlorophyll Q maximum near 665 nm,
> outside the 440–630 clamp". The pigment is **protochlorophyll**, not chlorophyll (Fruhwirth & Hermetter
> 2007, the paper this project is built on), and its Qy band is at **~623–626 nm** — **at the edge of our
> window, not outside it.** The 5.1 σ measurement is unaffected; only the attribution changes, and it gets
> *stronger*. See §16.12.14a and §16.12.16 for the consequence that does change a decision. The lamp's
collapse to 39 DN is real and worth knowing, but it is *not* what produces the rise — the rise is green-pigment
absorption. Read §16.12.12 before acting on anything in this subsection.

#### What survives

Analysis **A stands on its own** and does not depend on any of this: it compares the shipped metric against
elapsed time, and the trend is there, replicated, and significant in set C. The drift is real, it reaches the
shipped metric, and it resets with a fresh fill — the camera streamed continuously (§16.12.1) and the lamp is
external and always on, so **the fill remains the only element that restarts between sets.**

What analysis B delivered is not the mechanism but a **blocker**: with the far anchor corrupted, no baseline-shape
question — λ⁻ⁿ or otherwise — can be settled on this data. **Fix the anchor first, then re-run B.** Until then the
solvent track (§16.12.7) is the only *unblocked* line of attack on the drift.

### 16.12.12 ✅ The far anchor carries PIGMENT, not a lamp artifact — 5.1 σ  *(`diagnostics/far_anchor_probe.py`, 2026-07-31)*

§16.12.11 B left two candidates for the rise toward 630 nm and named the lamp cliff the leading one. **That was
wrong.** The discriminator is the oil class, measured under the same lamp: 37 runs, 28 green and 9 brown, across
six fills and two sessions. `rise` = A(620–630) − A(600–610), i.e. the slope **inside** the far anchor.

| fill | class | A_Soret | A_530 | A_Q | A 600–610 | A 620–630 | **rise** | ref far DN |
|---|---|---|---|---|---|---|---|---|
| green B 07-27 | green | 0.981 | 0.113 | 0.204 | 0.122 | 0.178 | **0.055** | 45.4 |
| green E 07-27 | green | 0.920 | 0.102 | 0.192 | 0.128 | 0.182 | **0.055** | 33.7 |
| set B 07-29 | green | 1.093 | 0.098 | 0.197 | 0.124 | 0.172 | **0.048** | 37.3 |
| set C 07-29 | green | 1.186 | 0.123 | 0.230 | 0.149 | 0.203 | **0.055** | 36.9 |
| brown C 07-27 | brown | 1.242 | 0.163 | 0.306 | 0.217 | 0.237 | **0.021** | 34.7 |
| brown D 07-27 | brown | 0.991 | 0.136 | 0.251 | 0.168 | 0.175 | **0.007** | 36.0 |

| | green (n=28) | brown (n=9) | |
|---|---|---|---|
| **rise** | **0.0535 ± 0.007** | **0.0159 ± 0.010** | **5.10 σ separation** |
| reference DN 620–630 *(control)* | 38.9 ± 8.0 | 35.2 ± 2.8 | **same lamp state** |

**⇒ Candidate (a), the instrument artifact, is REFUTED.** The lamp is in the same state for both classes — the
reference sits at 35–39 DN throughout — yet the rise differs **3.4×** by oil. An instrument effect cannot know
which oil is in the jar. **For brown the far window is genuinely quiet (rise 0.007–0.021); for green it is not.**

**⇒ Candidate (b) is CONFIRMED: the far anchor is standing on real green-pigment absorption** — the rising flank
toward the pigment's red (Qy) band. Supporting:
regressing `rise` on the raw greenness ratio `A_Soret/A_Q` gives **intercept −0.0013, i.e. zero** — the rise
vanishes exactly when the greenness does, which is the pigment prediction and not the artifact one. (R² is only
0.157 because concentration varies between fills; the *intercept* is the diagnostic here, not the fit quality.)

⚠ **A regression of `rise` on any single band amplitude does NOT work as a test, and the first attempt at one was
misleading.** Neither `A_Q` (which runs **higher** in brown — it is the metric's denominator, not a pigment
axis) nor `A_Soret` (stray-light compressed at T < 10 %, §16.11.8 — brown reads 1.158 against green's 1.034) is a
clean green-pigment amplitude. The class contrast under a fixed lamp is the valid test.

#### Why this is worse than a lamp artifact would have been

An instrument artifact is common-mode: both classes get it, and a ratio largely cancels it. **This does not
cancel — it is the measured signal leaking into the baseline that is supposed to be signal-free, and it leaks
~3.4× more for green than for brown.** The far anchor sets the fitted baseline's slope, that slope is subtracted
from both bands, and the Q denominator is small enough that a slope error moves the ratio hard. **So an unknown
part of the green↔brown separation we are shipping comes from the baseline construction rather than from the
Soret band.**

This does not mean the discrimination is wrong — §16.10's leave-one-fill-out scoring is empirical and stands.
It means **we do not currently know how much of it is pigment physics and how much is window placement.**

#### It also explains why analysis B could never have worked

§16.12.11 B tried to fit a scatter pedestal through two "oil-quiet" windows. **One of them is not oil-quiet.**
The scattering hypothesis is still untested, and the reason is now precisely identified: you cannot fit a
baseline through a window that contains the analyte.

#### ▶ The test this calls for — a far-anchor sweep, free, same PDFs

§16.11.14 swept the Soret band's left edge and refuted moving it; **nobody has ever swept the baseline windows.**
Slide the far anchor left in steps (e.g. 600–630 → 595–615 → 590–605 → 585–600) and re-score the green↔brown
separation with §16.10's leave-one-fill-out. Outcomes:
- **separation holds or improves** → move the window and the contamination is retired for free.
- **separation degrades** → part of today's discrimination genuinely rests on the pigment flank, and that must be
  said out loud in `SPEC_capability_proof.md` rather than left implicit in a window constant.

Either way the answer belongs in the spec before the capability-proof verdict is defended.

### 16.12.13 ⚠ AS-RUN — the far-anchor SWEEP: the contamination is CARRYING the discrimination  *(`diagnostics/far_anchor_sweep.py`, 2026-07-31)*

§16.11.14 swept the Soret band's edges; the baseline windows had never been swept. Two sweeps, near anchor
(520–540) held fixed throughout. Discrimination scored on §16.10.9's basis — 25 runs, 4 fills, 2026-07-27 —
and the settling trend on sets B and C, mean of the two.

**SWEEP 1 — right edge pulled in, left edge pinned at 600 nm**

| far window | LOFO | \|d\| | gap | CV/fill % | trend % | resid CV % |
|---|---|---|---|---|---|---|
| **600–630 nm** | **1/25** | **2.88** | **+0.495** | 9.72 | **−6.15** | 1.76 ← *shipped* |
| 600–625 nm | 2/25 | 2.65 | +0.166 | 9.50 | −5.90 | 1.75 |
| 600–620 nm | 4/25 | 2.28 | OVERLAP | 9.41 | −4.96 | 1.68 |
| 600–615 nm | 9/25 | 1.95 | OVERLAP | 9.13 | −3.68 | 1.45 |
| 600–610 nm | 12/25 | 0.94 | OVERLAP | 10.04 | **−2.55** | **1.14** |

**SWEEP 2 — fixed 20 nm width, window slid left**

| far window | LOFO | \|d\| | gap | CV/fill % | trend % | resid CV % |
|---|---|---|---|---|---|---|
| **610–630 nm** | **1/25** | **3.28** | **+0.782** | 10.30 | **−7.60** | 2.08 |
| 605–625 nm | 2/25 | 2.92 | +0.260 | 9.34 | −6.25 | 1.88 |
| 600–620 nm | 4/25 | 2.28 | OVERLAP | 9.41 | −4.96 | 1.68 |
| 595–615 nm | 11/25 | 1.76 | OVERLAP | 9.72 | −4.24 | 2.01 |
| 590–610 nm | 13/25 | 1.06 | OVERLAP | 10.48 | −4.04 | 3.05 |
| 585–605 nm | 12/25 | 1.04 | OVERLAP | 11.83 | −5.74 | 6.12 |

#### Both sweeps say the same thing, monotonically

**The redder the far anchor reaches, the better green separates from brown — and the worse the metric drifts.
They are the same quantity.** Push the window further red than shipped (610–630) and Cohen's d *rises* 2.88 →
3.28 and the clean gap widens +0.495 → +0.782, while the settling trend worsens −6.15 % → −7.60 %. Pull it in
and both fall together, until at 600–610 the classes **overlap outright** (d 0.94) and the drift is at its
mildest (−2.55 %, residual CV 1.14 %).

**⇒ There is no free win. §16.12.12's contamination is not a defect sitting beside the measurement — it is
doing a large share of the measuring.** Remove it and the discrimination goes with it.

#### What this does and does not change

**It does NOT show the metric is broken.** The shipped 600–630 window sits near the optimum of this trade-off,
and §16.10's leave-one-fill-out scoring stands on its own as an empirical result. Nothing here says the verdicts
were wrong.

**It DOES falsify the documented rationale.** `DevSpectralPlugin`'s comment describes `PB_BASELINE_WINDOWS` as
two *"OIL-QUIET"* windows that *"sit where the oil itself is featureless"*. For the far window that is
demonstrably false (§16.12.12, 5.1 σ), and the sweep shows the falsity is load-bearing rather than incidental.

**⇒ The metric must be restated.** It is not "Soret/Q with a seating-tilt correction". It is a **three-region
construction** in which 600–630 nm contributes real green-pigment information with a negative sign, via the
fitted baseline's slope. That belongs in `SPEC_capability_proof.md` explicitly — a reader currently cannot tell
from either spec that a third pigment band is in the measurement.

Two consequences follow from the restatement, and both are testable:
1. **The metric is more exposed than documented to anything that moves the far window** — the settling
   (§16.12.11 A) and the lamp's red-end collapse to 39 DN (§16.12.11 B) both act there.
2. **▶ If that window carries useful pigment signal, declare it as an explicit third band** rather than
   smuggling it in through the baseline. An honest three-band metric can be tuned, reasoned about and
   error-budgeted; a baseline anchor that secretly measures cannot.

#### ⚠ Caveats — do NOT adopt 610–630 on this evidence

- **Choosing the best window from this sweep is exactly §16.10.16's trap.** The robust signal is the *monotone
  trend across both sweeps*, not any single score. 1/25 against 2/25 is one run.
- **LOFO here rests on 4 fills, only 2 of them brown** (one with just 3 runs).
- **The 07-27 fills are PRE-rig-rebuild** — within-fill CV ~9.7 % against the 2.96 % of §16.11.3. This is the
  noisy dataset. It is §16.10.9's published basis so the numbers are comparable, but **a post-rebuild re-run
  with a proper brown series would be far stronger** — which is another reason series D/E matters.
- The trade-off is measured on green↔brown discrimination only. The third "too-green" oil (§16.11.12) is not in
  this data at all.

### 16.12.14 ⛔ "Drop the red anchor now the rig is fixed" — REFUTED, and backwards  *(Edwin's hypothesis, `diagnostics/baseline_variants.py`, 2026-07-31)*

**Edwin's reasoning, which is sound:** the far (red) window was adopted as a baseline anchor when the rig had
much more mechanical wobble. §16.11 rebuilt it — jar tilt **2.84 % → 1.34 %**. If the red anchor was mostly
compensating that wobble, its advantage should now have shrunk, and a simpler correction that never touches the
red end might be enough.

Five variants, all ratios of the **same two bands**, differing only in the correction:

| variant | what it does |
|---|---|
| `raw` | no correction |
| **`offset NEAR only`** | subtract the constant `mean(520–540)` — **Edwin's proposal, no red window** |
| `offset FAR only` | subtract the constant `mean(600–630)` |
| `linear NEAR+FAR` | the shipped metric |
| `2nd derivative` | window-free; annihilates any linear baseline exactly |

#### Precision — within-fill CV %

| variant | grn B | grn E | brn C | **set B** | **set C** | **POST avg** | PRE avg |
|---|---|---|---|---|---|---|---|
| `raw` | 16.64 | 7.92 | 11.38 | 11.14 | 5.16 | **8.15** | 11.98 |
| **`offset NEAR only`** | 9.21 | 13.70 | 12.02 | 14.12 | 6.67 | **10.39** | 11.64 |
| `offset FAR only` | 13.70 | 14.62 | 7.86 | 7.63 | 8.87 | **8.25** | 12.06 |
| **`linear NEAR+FAR`** | 10.35 | 9.09 | 8.91 | **2.96** | **2.89** | **2.92** | 9.45 |
| `2nd derivative` | 68.17 | 81.40 | 46.57 | 60.23 | 60.84 | 60.54 | 65.38 |

#### ⭐ The test — what the correction still BUYS, pre vs post rebuild

`gain = raw CV / variant CV`. **If the red anchor were compensating wobble, its gain had to FALL after the
rebuild.**

| variant | PRE gain | POST gain | change |
|---|---|---|---|
| `raw` | 1.00× | 1.00× | — |
| **`offset NEAR only`** | 1.03× | **0.78×** | **−24 %** *(worse than no correction at all)* |
| `offset FAR only` | 0.99× | 0.99× | −1 % |
| **`linear NEAR+FAR`** | 1.27× | **2.79×** | **+120 %** |
| `2nd derivative` | 0.18× | 0.13× | −27 % |

**⇒ REFUTED, and in the opposite direction: the rebuild made the baseline MORE valuable, not less — its gain
more than DOUBLED.**

> ⚠ **The +120 % is carried by ONE RUN — see §16.12.14c.** Drop set B's run 002 and the post-rebuild gain falls
> to **1.32×** against the pre-rebuild 1.27 %, i.e. essentially unchanged. **The REFUTATION survives** (every
> single-anchor variant is still worse than the two-anchor line, with or without B002); the *"more valuable
> after the rebuild"* half does not. Read §16.12.14c before quoting the +120 %.

The mechanism is worth stating, because it inverts the intuition. **Pre-rebuild, the mechanical wobble was so
large that it swamped everything** — every variant landed at 9–12 % CV and no correction could reach past the
noise. **Post-rebuild the mechanical term is gone, and what remains is exactly the common-mode offset-plus-slope
the linear baseline was built to remove.** The wobble was not what the baseline was fixing; the wobble was
*masking how much the baseline fixes*.

**Edwin's specific proposal costs 3.6× in precision:** `offset NEAR only` reads **10.39 %** post-rebuild against
`linear NEAR+FAR`'s **2.92 %** — and at 0.78× gain it is *worse than applying no correction at all*.

#### Settling and dilution agree — post-rebuild sets only

| variant | B trend % | C trend % | pooled CV % | B→C dilution % |
|---|---|---|---|---|
| `raw` | −9.66 | −1.80 | 8.15 | −7.68 |
| `offset NEAR only` | **−16.22** | −7.56 | 10.39 | −2.27 |
| `offset FAR only` | +1.86 | −9.15 | 8.25 | −2.74 |
| **`linear NEAR+FAR`** | −5.38 | −6.93 | **2.92** | **−1.91** |
| `2nd derivative` | −98.75 | −35.32 | 60.54 | +84.78 |

#### Discrimination — PRE-rebuild only

| variant | LOFO | \|d\| | gap |
|---|---|---|---|
| `raw` | 9/25 | 1.24 | OVERLAP |
| `offset NEAR only` | 10/25 | 1.85 | OVERLAP |
| `offset FAR only` | 3/25 | 2.71 | **+0.860** |
| **`linear NEAR+FAR`** | **1/25** | **2.88** | +0.495 |
| `2nd derivative` | 17/25 | 1.07 | OVERLAP |

**Neither anchor alone works — it is the SLOPE between them that does the job.** `offset FAR only` is no better
than raw on precision (0.99× gain) despite using the red window, and `offset NEAR only` is worse than raw. Only
the two-anchor line delivers, which is consistent with §16.12.11 A's finding that the noise is common-mode
offset **and** slope.

*(`2nd derivative` is decisively out at 60 % CV — recorded so it is not proposed again.)*

#### ⚠ Caveats

- **The pre/post comparison is not a controlled A/B.** It also changes session, oil vintage (2023 vs 2026 stock)
  and dilution recipe. The *direction* is robust — a −24 %/+120 % split is not a subtle effect — but the factor
  is not.
- **Post-rebuild is 2 fills, both green, 6 runs each.** Discrimination cannot be scored there at all.
- Pre-rebuild `green B` raw CV of 16.64 % is anomalously high even for that dataset.

**⇒ Keep the red anchor.** The hypothesis was worth testing and the instinct was reasonable; the data says the
rebuild strengthened the case for the baseline rather than weakening it.

### 16.12.14a ⛔ WHOLE-SPECTRUM baselines TRIED and REJECTED — the window has no peak-free region  *(Edwin, same harness, 2026-07-31)*

The natural follow-up: stop fitting through two hand-chosen windows and let a standard chemometric baseline use
the **whole spectrum**. Four added to the same harness — the naive full-range least-squares line, the classic
**rubber band** (convex hull from below), **ModPoly** (Lieber & Mahadevan-Jansen: fit, clip above the fit,
refit), and **AsLS** (Eilers & Boelens asymmetric least squares) at two smoothness/asymmetry settings.

| variant | grn B | grn E | brn C | set B | set C | **POST CV** | PRE CV | **LOFO** | \|d\| | gap | B→C dil. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **`linear NEAR+FAR`** *(shipped)* | 10.35 | 9.09 | 8.91 | 2.96 | 2.89 | **2.92** | 9.45 | **1/25** | **2.88** | **+0.495** | **−1.91** |
| `full-range line` | 11.73 | 8.86 | 9.49 | 4.16 | 2.48 | **3.32** | 10.03 | **1/25** | 2.45 | +0.129 | −3.02 |
| `ModPoly ord3` | 13.15 | 5.50 | 9.13 | 8.87 | 4.68 | 6.77 | 9.26 | 13/25 | 0.60 | OVERLAP | −5.14 |
| `AsLS 1e5/0.01` | 10.88 | 5.26 | 7.00 | 8.28 | 5.29 | 6.78 | 7.71 | **21/25** | 0.29 | OVERLAP | **−0.72** |
| `AsLS 1e6/0.001` | 11.60 | 11.16 | 10.45 | 9.45 | 6.34 | 7.90 | 11.07 | 4/25 | 0.94 | OVERLAP | −6.75 |
| `rubber band` | 26.00 | 20.85 | 12.42 | 21.58 | 19.21 | 20.39 | 19.76 | 14/25 | 0.51 | OVERLAP | −21.07 |
| `raw` *(reference)* | 16.64 | 7.92 | 11.38 | 11.14 | 5.16 | 8.15 | 11.98 | 9/25 | 1.24 | OVERLAP | −7.68 |

**⇒ Not one of them beats the two-window line, and the sophisticated ones are the WORST.**

#### Why — and it is structural, not a tuning problem

**Every whole-spectrum baseline algorithm assumes the spectrum returns to baseline somewhere. Ours never does.**
The capture clamp is 440–630 nm; the **Soret band starts at the very left edge** (440–460) and the **chlorophyll
Q flank rises into the right edge** (§16.12.12). There is no peak-free region for a hull, a clipped polynomial or
an asymmetric fit to sit on — so they anchor on the pigment itself and **absorb the signal into the baseline**.

The failure is visible in the numbers rather than inferred:
- **`AsLS 1e5/0.01` is the clearest case.** It gives the *best dilution invariance of any variant tested*
  (**−0.72 %**) and a decent CV — and then scores **21/25 leave-one-fill-out errors with d = 0.29.** It has
  removed the concentration term *and the class difference along with it*. A baseline that flexible eats exactly
  what we are trying to measure.
- **`rubber band` is catastrophic across the board** (CV 20 %, dilution −21 %): the hull's vertices land wherever
  noise happens to dip lowest, so it is a noise amplifier here.
- **`ModPoly ord3`** halves nothing and loses the classes outright.

#### The one that nearly works, and what it teaches

**`full-range line` — a plain least-squares line over all 440–630 nm — comes second on precision (3.32 % vs
2.92 %) and ties the shipped metric on LOFO (1/25).** It is also a two-parameter offset-plus-slope removal; it
just picks its slope from everything instead of from two windows.

That is informative: **what the correction must do is remove an offset AND a slope — that much is settled by four
variants agreeing (§16.12.14). Where you anchor it is a second-order choice, but not a free one:** the full-range
line's class gap collapses to **+0.129** against the shipped **+0.495**, and its dilution error is 58 % larger.
Fitting through the pigment drags the slope, exactly as §16.12.12 predicts.

**⇒ Keep the two-window linear baseline.** Recorded so neither the chemometric family nor the naive full-range
line is proposed again without new evidence — and note the *precondition* that would change the answer: **a wider
capture window with a genuinely pigment-free region** would make AsLS viable. That is a lamp-and-optics change,
not a software one.

> ⚠ **"beyond ~700 nm" was WRONG and this precondition is CHEAPER than recorded** *(2026-07-31,
> `KB_spectroscopy_physics.md` §4.1)*. It rested on the pigment being chlorophyll with a Q maximum near
> 665 nm. It is **protochlorophyll**, Qy ≈ **623–626 nm** — so the genuinely pigment-free region begins
> around **660 nm**, not 700+. A window extension of ~30 nm past our present 630 clamp, rather than ~70,
> may be enough to obtain a real peak-free anchor. **Re-cost before dismissing the optics route again.**

*(Caveats as §16.12.14: pre/post is not a controlled A/B, post-rebuild is 2 green fills, discrimination is
pre-rebuild only. AsLS parameters were not tuned beyond two settings — but the failure mode is structural, so
tuning is unlikely to rescue it while the window ends sit on pigment.)*

### 16.12.14b Fit over MORE spectrum but anchor only where the oil is quiet — and the trade-off this exposes  *(Edwin, 2026-07-31)*

The remaining reading of "use the whole spectrum": keep the *quiet-anchored* philosophy but stop fitting through
only two window **means**. Five more variants, varying how much of the spectrum counts as quiet and how much
freedom the fit has:

| variant | fitted on | order |
|---|---|---|
| `lin 2win LSQ` | every point inside the **same two windows** (not just their means) | 1 |
| `lin ex-bands` | everything in 440–630 **except** the Soret and Q bands | 1 |
| `poly2 ex-bands` | same mask | 2 |
| `poly3 ex-bands` | same mask | 3 |
| `lin ex-band+carot` | also excludes 460–510 nm, where the carotenoids absorb | 1 |

| variant | POST CV | PRE CV | mean \|trend\| | B→C dil. | **LOFO** | \|d\| | **gap** |
|---|---|---|---|---|---|---|---|
| **`linear NEAR+FAR`** *(shipped)* | **2.92** | 9.45 | 6.16 | −1.91 | **1/25** | **2.88** | **+0.495** |
| `lin 2win LSQ` | **2.89** | 9.39 | 6.07 | −1.93 | **1/25** | 2.85 | +0.453 |
| `lin ex-band+carot` | 3.19 | 9.39 | 5.54 | −2.75 | 2/25 | 2.47 | +0.127 |
| `lin ex-bands` | 3.34 | 10.02 | 5.93 | −3.07 | **1/25** | 2.46 | +0.190 |
| **`poly2 ex-bands`** | 3.35 | **5.39** | **1.78** | **−1.90** | 5/25 | 1.34 | OVERLAP |
| `poly3 ex-bands` | 6.38 | 8.44 | 3.69 | −3.13 | 13/25 | 0.85 | OVERLAP |

#### Two results

**1. Fitting the two windows by least squares instead of through their means changes nothing.** `lin 2win LSQ`
lands within ~1 % of the shipped metric on every measure (CV 2.89 vs 2.92, gap +0.453 vs +0.495). **The two
window means are a sufficient statistic** — the within-window slope carries no usable extra information. Worth
knowing: it closes off an obvious "improvement" that isn't one.

**2. `poly2 ex-bands` is the best nuisance-remover found anywhere in this thread — and it cannot discriminate.**
It halves the pre-rebuild CV (**5.39 %** against the shipped 9.45 %), gives the flattest settling of any variant
(**mean \|trend\| 1.78 %** against 6.16 %), and matches the best dilution invariance (−1.90 %). Then it scores
**5/25 LOFO with the classes OVERLAPPING.**

#### ⭐ The axis this exposes — and it is the same finding as §16.12.13, from the other end

Order every variant by **how much spectrum the baseline sees and how much freedom it has to follow it**:

| baseline freedom | nuisance removal | class separation |
|---|---|---|
| none (`raw`) | poor (CV 8.15) | none (OVERLAP, 9/25) |
| **2 windows, line** | **good (CV 2.92)** | **best (gap +0.495, 1/25)** |
| whole spectrum − bands, line | good (CV 3.34) | degraded (gap +0.190) |
| whole spectrum − bands, poly2 | **best (PRE CV 5.39, trend 1.78)** | gone (OVERLAP, 5/25) |
| whole spectrum, AsLS | **best dilution (−0.72)** | destroyed (21/25) |

**The more spectrum the baseline is allowed to follow, the better it removes drift, dilution and seating noise —
and the more class signal it removes with them.** Monotone across seven variants.

**⇒ This is §16.12.13's window sweep seen from the opposite direction, and together they say the same thing: the
green↔brown information lives in the BROAD SPECTRAL SHAPE, not in the two narrow bands alone.** Any correction
flexible enough to flatten the broad shape flattens the discriminator with it. **There is no smarter baseline to
be had on this window** — precision and separation are drawing on the same resource.

**The only escape is more spectral coverage.** A window reaching past the pigment's red band would give a
genuinely signal-free region to anchor on, and AsLS's −0.72 % dilution figure hints at real headroom there.
That is a lamp-and-optics change, not software (§16.12.14a). ⚠ **How much more coverage is now a smaller
number than this section assumed** — the band is at ~623–626 nm, not ~665, so "past ~660 nm" replaces
"past ~700 nm" (`KB_spectroscopy_physics.md` §4.1).

**⇒ Keep `linear NEAR+FAR`. No variant tested beats it on the quantity that decides the milestone.**

*(One thing worth keeping in the drawer: if a future QC indicator needs a dilution- and settling-immune number
that is **not** the class discriminator — "was this measurement stable?" rather than "which oil is it?" —
`poly2 ex-bands` is the best candidate found. Different job, different tool.)*

### 16.12.14c ⚠ SENSITIVITY — how much of §16.12 rests on set B's run 002?  *(Edwin asked, `diagnostics/without_b002.py`, 2026-07-31)*

B002 is §16.11.7's largest tilt event, flagged **there, before any of the §16.12 work**: per-run tilt slope
−0.0398 against ≤ −0.0204 for every other run in the set. This thread independently found it anomalous three
more ways — quiet-window shape ratio 1.019 vs ~0.71, `A_far` −38.9 %, `A_Q` −18.7 % while `A_Soret` is +0.6 %.

**Everything recomputed with it dropped. Nothing below is adopted** — see the verdict at the end.

#### Set B, 6 runs vs 5

| metric | CV % all 6 | t | **CV % w/o 002** | **t** |
|---|---|---|---|---|
| `S/Q raw` | 11.14 | −0.68 | **1.77** | +0.94 |
| `S/Q linear base` | 2.96 | −1.84 | **2.37** | −1.36 |
| `A_Soret` | 3.30 | **−3.76** | 3.68 | **−4.11** |
| `A_Q` | 9.98 | −0.02 | **4.42** | **−5.79** |
| `A_near` 520–540 | 9.82 | −0.50 | **6.56** | **−5.90** |
| `A_far` 600–630 | 19.91 | +0.22 | **6.37** | **−3.73** |

#### Baseline variants, post-rebuild

| variant | POST CV all | dil. % | **POST CV w/o** | **dil. % w/o** |
|---|---|---|---|---|
| `raw` | 8.15 | −7.7 | **3.47** | −3.3 |
| `offset NEAR only` | 10.39 | −2.3 | 4.72 | +3.6 |
| `offset FAR only` | 8.25 | −2.7 | 6.23 | −5.4 |
| **`linear NEAR+FAR`** | **2.92** | **−1.9** | 2.63 | −1.1 |
| `lin 2win LSQ` | 2.89 | −1.9 | 2.58 | −1.1 |
| `full-range line` | 3.32 | −3.0 | 2.22 | −1.5 |
| **`poly2 ex-bands`** | 3.35 | −1.9 | **1.58** | **−0.1** |
| `AsLS 1e5/0.01` | 6.78 | −0.7 | 3.46 | +2.7 |

#### What CHANGES

1. **⛔ §16.12.14's "+120 %" headline is B002.** Post-rebuild gain of the baseline over raw: **2.79× → 1.32×**,
   against a pre-rebuild 1.27×. *"The rebuild made the baseline more valuable"* **does not survive** — the gain
   is essentially unchanged by the rebuild. Caveat now carried at §16.12.14 itself.
2. **⚠ §16.11.9's budget closure weakens further.** Set B observed CV **2.96 % → 2.37 %** (2.15 % detrended)
   against the `jar` arm's 2.98 % prediction. The celebrated match at 2.96 vs 2.98 was **partly propped up by
   the outlier**; the arm now over-predicts by ~1.3–1.4×. This *strengthens* §16.12.11 A's conclusion that the
   mechanics are not the binding constraint.
3. **The settling evidence gets STRONGER, not weaker.** With B002 gone, `A_Q`, `A_near` and `A_far` all trend
   **significantly** downward (t −5.79, −5.90, −3.73) where they were flat before — B002's dip was *masking*
   the trends. But note the corollary: in set B all four absorbances now sink together and **the ratios do not
   trend** (`S/Q raw` t +0.94, `S/Q linear base` t −1.36). Set C's ratio still trends (t −5.60). So set B's
   drift is common-mode and cancels; set C's does not. **Unresolved, and it needs the brown series.**
4. **`poly2 ex-bands` becomes clearly best on precision AND dilution** — 1.58 % CV and −0.1 % dilution, beating
   the shipped 2.63 % / −1.1 %. Its discrimination is **unchanged** (5/25, OVERLAP — scored on 07-27 data that
   contains no B002), so §16.12.14b's trade-off axis is untouched and if anything starker.

#### What SURVIVES

- **Edwin's original hypothesis stays refuted.** `offset NEAR only` is still far worse than the two-anchor line
  (4.72 vs 2.63) and its dilution error flips sign to **+3.6 %**; `offset FAR only` is worse still at 6.23.
  **Both anchors are needed, with or without B002.**
- **§16.12.11 A's headline holds.** Pooled `S/Q linear base` 2.92 → 2.67 % raw, 1.89 → 1.63 % detrended; the
  trend's share of variance goes 58 % → **63 %**.
- **§16.12.12 / §16.12.13 / §16.12.14a / §16.12.14b are untouched** — all scored on 07-27 fills.

#### ⇒ VERDICT: do NOT exclude it

**§16.11.11's V2 rule is "exclusion = documented physical cause only", and B002 has no cause documented
independently of the measurement itself.** No bumped jar, no lamp event, no mis-fill was recorded — the anomaly
is visible only in the data it would be excluded from.

Worse, it is **circular**: §16.11.7 attributed the early-run tilts to **the dilution settling**, i.e. to the
phenomenon under study. Sets B and C are *re-seat repeatability* measurements. **Dropping the worst re-seat from
a re-seat-repeatability measurement removes signal, not noise** — it is the tail of the distribution being
characterised. That is §16.10.16's trap in its purest form.

**⇒ Keep B002 in every headline number. Keep this section as the sensitivity statement**, because "one of six
runs moves the gain from 2.79× to 1.32×" is exactly the fragility a reader of §16.12.14 needs to know about.
**The real fix is n, not exclusion** — series D/E's twelve brown runs.

### 16.12.15 Claims made and WITHDRAWN in this thread *(per §16.7.0's practice)*

| claim | withdrawn because |
|---|---|
| "camera self-heating (τ = 2.9 min) may be the §16.11.7 confound" | the camera streamed continuously across sets B and C, so it had plateaued *(Edwin 2026-07-30)* |
| "s ≈ 0.05 A, so turbidity costs the entire 3 % error budget" | §16.11.9's closure bounds `s` from above — no room for a term that size. The **leak coefficient 0.65 is geometry and stands**; the amplitude was an illustration, not a measurement |
| "use a 0.45 µm filter" | 0.45 µm and 0.22 µm both sit **above** the 50–200 nm nanodroplets; 0.22 µm is the right choice and the size limit is what makes it a discriminator (§16.12.9) |
| "the filter is the highest value-per-euro fix" | ~€1/measurement + an extra step is not shippable to a mill *(Edwin 2026-07-31)*; demoted to bench diagnostic |
| "the miller would not accept 1-butanol's odour" | unevidenced — I stated a guess as fact. Cost and availability are acceptable *(Edwin 2026-07-31)*; odour is an open **test**, not an objection |
| "in-app countdown showing dilution age" | not practicable *(Edwin 2026-07-30)* |
| "glass Petri dish as the transparent vessel" | spill risk and variable fill depth = variable path length *(Edwin 2026-07-30)* |
| **"the drift is λ⁻ⁿ scattering, correctable by a power-law baseline"** | **untestable, not tested — §16.12.11 B. The far anchor sits on the lamp's cliff (39 DN at 620–630 vs 130 at 530), so the fit is anchored on a low-signal artifact. Re-run once the anchor is fixed** |
| "the quiet windows rise with λ, therefore scattering is REFUTED" | **first reading of the run, corrected the same day.** The rise is not the sample's scattering shape — but nor is it the instrument. §16.12.12: it is **green-pigment absorption in the far window**. Refutation withdrawn; the scattering hypothesis returns to *untested* |
| "the far-anchor rise is a low-signal artifact at the lamp's cliff (39 DN)" | **§16.12.12 — REFUTED at 5.1 σ.** Same lamp state for both classes (ref 35–39 DN), yet the rise differs 3.4× by oil. The lamp collapse is real; it is not the cause |
| "regress `rise` on A_Q (then A_Soret) to test pigment-scaling" | neither is a green-pigment axis — A_Q runs **higher** in brown, A_Soret is stray-light compressed (§16.11.8). The first regression returned a nonsense −96 %/196 % decomposition. **The class contrast under a fixed lamp is the valid test** |
| "s = 0.05 A is a plausible scatter amplitude" | unmeasurable on this data for the same reason; the amplitude question is open, not void |
| "the ouzo nanodroplets explain the settling" | no measured support either way — treat as unevidenced pending a valid far anchor |

### 16.12.16 ▶ Next, in order  *(revised after the §16.12.14 variant test)*

| | action | cost | what it decides |
|---|---|---|---|
| ~~1~~ | ~~detrend + λ⁻ⁿ sweep~~ | — | ✅ **DONE 2026-07-31, §16.12.11.** Trend confirmed; λ⁻ⁿ refuted |
| 1 | **⭐ Re-scope §16.11.11 around the detrended 1.89 %** | free | the `jar` arm over-predicts by ~1.6× — the `cone` arm and the mechanical programme are no longer the binding constraint. **Series E (σ_fill) becomes the most informative measurement available** |
| ~~2a~~ | ~~far anchor: lamp or pigment?~~ | — | ✅ **DONE, §16.12.12.** PIGMENT, 5.1 σ |
| ~~2b~~ | ~~sweep the far anchor~~ | — | ✅ **DONE, §16.12.13.** The contamination is CARRYING the discrimination — remove it and the classes overlap. No free win; the shipped window is near-optimal |
| ~~2~~ | ~~restate the metric~~ | — | ✅ **DONE 2026-07-31** — `SPEC_capability_proof.md` **§2.1a** (three-region algebra, verified to 0.5 %) + the `PB_BASELINE_WINDOWS` comment in `DevSpectralPlugin` rewritten. Doc-only; 22 tests green |
| ~~2d~~ | ~~raw-vs-baselined on dilution + settling~~ | — | ✅ **DONE, §2.1a** (`diagnostics/baseline_vs_raw.py`). **The baseline HALVES both errors** (dilution 5.49→2.75 %, settling 11.90→6.20 %) and **§11.4c's sign is vindicated** — the 11 h/30 min conflict is a **non-monotonic settling curve**, not a sign flip |
| 2 | **⭐ Decide: declare 600–630 as an explicit third band?** (`SPEC_capability_proof.md` §2.1a) | a design call | now that it earns its place on **three** axes — discrimination, dilution invariance, settling immunity — it should arguably be named and error-budgeted rather than disguised as a correction anchor. Gated on post-rebuild data so the window is not fitted on today's 4 fills |
| 2c | Re-run the sweep on POST-rebuild data with a proper brown series | rides on series D/E | today's sweep rests on pre-rebuild 07-27 fills (within-fill CV ~9.7 % vs 2.96 %) and only 2 brown fills. **✅ UNBLOCKED 2026-07-31 — series D (§16.13) is the brown series it was waiting for** |
| ~~2e~~ | ~~drop the red anchor now the rig is fixed?~~ | — | ⛔ **REFUTED 2026-07-31, §16.12.14.** The rebuild made the baseline **more** valuable (gain 1.27× → 2.79×); `offset NEAR only` costs 3.6× precision and is worse than no correction. **Keep the red anchor** |
| ~~2f~~ | ~~whole-spectrum baseline (AsLS / rubber band / ModPoly)?~~ | — | ⛔ **REJECTED 2026-07-31, §16.12.14a.** None beats the two-window line; AsLS scores 21/25 LOFO errors because it absorbs the class difference. **Structural: our 440–630 window has no peak-free region.** Revisit if the capture window widens past **~660 nm** *(revised down from "~700 nm" — the pigment's Qy is at ~623–626, not ~665; `KB_spectroscopy_physics.md` §4.1)* |
| **2h** | **⭐ NEW — re-cost the WINDOW EXTENSION** *(2026-07-31)* | a lamp/optics question | §4.1's correction moves the pigment-free region from ">700 nm" to "~660 nm+". Extending the clamp ~30 nm would give a **true** peak-free anchor, which would in one step unblock AsLS (2f), remove the far anchor's class contamination (§16.12.13), and give a clean read of the Qy band we are currently clipping. Was priced as prohibitive on a wrong premise |
| 2g | **⭐ The ALIQUOT step** — the batch is mixed in a lab glass and a 4 ml aliquot goes to the jar, i.e. a **sampling step out of a settling dispersion** | a stirrer | named 2026-07-31 as the leading σ_fill mechanism and the best fit to the green 0.0 % / brown 10.5 % asymmetry. Design + the test that separates it from the correction-artifact hypothesis: `SPEC_capability_proof.md` §11.4f **B2–B4** |
| 3 | **⭐ 1-butanol trial** (§16.12.7) — odour test, PS soak test, then a rig run | ~€20 | the only **unblocked** line of attack on the drift while item 2 is open |
| 4 | 0.22 µm PTFE filter (§16.12.9) | ~€6 once | still discriminates micron particulate from sub-pore populations, independently of any baseline model |
| 5 | Fresh ≥99.8 % IPA (§16.12.10) | ~€10 | control for solvent degradation |
| 6 | Container / FEP window (§16.12.8) | — | **only if butanol fails and heptane becomes necessary** |

Items 1 and 2 are free and both bear on work already scheduled — do them before series D/E.

⚠ **Superseded in part by §16.13.8** — series D ran on 2026-07-31 and re-ordered this list: item 1's
re-scoping is done, 2c is unblocked, and **series E is now the only measurement between the milestone and its
gate**.

---

## 16.13 ⭐ SERIES D — the brown oil, and the gate CLOSES  *(Edwin's rig session 2026-07-31; `diagnostics/brown_series_d.py`)*

Six re-seats of one brown fill, post-rebuild, still isopropanol — §16.11.11 step 2's first half, and the
load-bearing measurement of the whole milestone. Data: `spectracs-references/tmp/20260731A/` (6 PDFs).
Scored against §11.4f A of `SPEC_capability_proof.md`, **written the day before and not edited since**.

⚠ Read §16.13.3 before quoting the CV. The headline "1.41 % against green's 2.96 %" is **not** a like-for-like
comparison, for exactly the reason §16.12.11 established.

### 16.13.0 Summary

| | green B+C *(n=12)* | **brown D** *(n=6)* |
|---|---|---|
| `S/Q linear base` mean | 12.370 | **9.303** |
| σ | 0.367 | **0.131** |
| raw CV | 2.96 % | **1.41 %** |
| **residual CV** *(the comparable figure)* | **1.89 %** | **1.58 %** |
| settling trend in the metric over the set | −5.4 % / −6.9 % | **−0.15 %** *(t = −0.08)* |

**The pre-registered PASS criterion was brown within-fill CV ≤ 3.5 %. Measured: 1.41 %. PASS.**
Cohen's *d* = **11.13** *(RMS pooled SD; **9.80** on the conventional df-weighted form — these groups are
unequal in size, see §16.13.5)*; at the shipped T = 10.6 green sits **4.83 σ** above and brown **9.88 σ**
below. The
~10 % false-GREEN rate that §16.11.12 called "all the remaining risk" is gone.

**⇒ `SPEC_capability_proof.md`'s discrimination gate is met on re-seat data.** What it is *not* yet met on is
**fill-to-fill** — series E is untouched, and §16.13.6 says why that still matters.

### 16.13.1 The raw record

```
+-----------------------------------------------------------------------------+
|          SERIES D  ·  tmp/20260731A  ·  BROWN oil, ONE fill, re-seated       |
+--------+--------+---------+--------+---------+--------+---------+-----------+
|  run   |  min   | A_Soret |  A_Q   | A_near  | A_far  | S/Q raw | S/Q_lin   |
|        |        |         |        | 520-540 |600-630 |         | SHIPPED   |
+========+========+=========+========+=========+========+=========+===========+
|  001   |   0.0  |  1.122  | 0.236  |  0.108  | 0.143  |  4.760  |   9.451   |
|  002   |   5.3  |  1.120  | 0.242  |  0.116  | 0.143  |  4.635  |   9.163   |
|  003   |  10.5  |  1.104  | 0.239  |  0.115  | 0.142  |  4.622  |   9.146   |
|  004   |  15.9  |  1.082  | 0.232  |  0.108  | 0.144  |  4.653  |   9.394   |
|  005   |  21.5  |  1.064  | 0.211  |  0.095  | 0.117  |  5.043  |   9.403   |
|  006   |  38.4  |  1.021  | 0.191  |  0.080  | 0.097  |  5.340  |   9.264   |
+========+========+=========+========+=========+========+=========+===========+
|  mean  |        |  1.086  | 0.225  |  0.104  | 0.131  |  4.842  |   9.303   |
|   sd   |        |  0.039  | 0.020  |  0.014  | 0.020  |  0.291  |   0.131   |
|   CV   |        |  3.58%  | 8.86%  | 13.31%  | 15.19% |  6.00%  |  *1.41%*  |
+--------+--------+---------+--------+---------+--------+---------+-----------+
```

**The four inputs fall apart and the metric does not.** Runs 005–006 against 001–004, group means: `A_far`
−25.4 %, `A_near` −21.7 %, `A_Q` −15.3 %, `A_Soret` −5.9 %, raw `S/Q` **+11.2 %** — while the shipped
`S/Q_lin` moves **+0.5 %**.

### 16.13.2 Scored against the pre-registration — one hit, one miss, one PASS by a wider margin than predicted

Per §11.4f's rules the predictions stand as written and are marked right or wrong.

| §11.4f A predicted | measured | verdict |
|---|---|---|
| within-fill CV `S/Q linear base` **2.5 – 3.5 %** | **1.41 %** | ✅ **PASS** on the criterion (≤ 3.5 %) — but the *range* is **wrong**, low by ~2×. The rebuild transferred to brown **better** than green's 3.33× predicted |
| within-fill CV `S/Q raw` **3 – 8 %** | **6.00 %** | ✅ correct, inside the range |
| settling trend over ~30 min **−3 to −8 %** | **−0.15 %** *(t = −0.08)* | ⛔ **WRONG** — and informatively so, see §16.13.4 |

The failed prediction is the interesting one. It was extrapolated from green, where the metric trends −5 to
−7 %. Brown's *underlying absorbances settled harder than green's* — and the metric still did not move.

### 16.13.3 ⚠ The honest comparison is RESIDUAL, not raw — 1.58 % against 1.89 %

§16.12.11 showed that green's 2.96 % is mostly a settling trend, not seating: detrended it is **1.89 %**. Brown
has essentially no trend to remove, so its raw and residual figures are the same number.

| | raw CV | residual CV | trend | t *(4 df)* |
|---|---|---|---|---|
| set B `S/Q linear base` | 2.96 % | 2.44 % | −5.38 % | −1.84 |
| set C `S/Q linear base` | 2.89 % | 1.09 % | −6.93 % | **−5.60** |
| pooled B+C | 2.92 % | **1.89 %** | — | — |
| **brown D `S/Q linear base`** | **1.41 %** | **1.58 %** | **−0.15 %** | −0.08 |

*(brown's residual exceeds its raw because detrending spends a degree of freedom — `n−2` — on a slope that is
not there. That is the correct behaviour and it is the sign of a genuinely flat series.)*

**⇒ On seat-to-seat repeatability the two classes are close: 1.58 % brown against 1.89 % green.** The
2.96 % → 1.41 % headline overstates the gap roughly 2×. What brown really did better was **not accumulate a
settling trend in the metric**, and that is a separate finding rather than a repeatability one.

**⚠ Which figure belongs where.** The residual is the right number for the **error budget** (§16.11.9), because
it isolates seating. The **raw** CV is the right number for the **deployed decision**, because a real sample is
measured once, at whatever point in its settling curve it happens to be, and nobody detrends a single
measurement. §16.13.5's margins therefore use raw σ throughout — the conservative choice for brown, and it is
still decisive.

### 16.13.4 ⭐ Brown settled ~3× harder than green, and the shipped metric absorbed all of it

The strongest common-mode-rejection evidence in the record so far.

| trend across the set | set B *(green)* | set C *(green)* | **brown D** |
|---|---|---|---|
| `A_Soret` 440–460 | −7.82 % | −9.13 % | **−10.00 %** |
| `A_Q` 560–580 | −0.28 % | −8.02 % | **−23.15 %** |
| `A_near` 520–540 | −6.36 % | −13.56 % | **−33.56 %** |
| `A_far` 600–630 | +5.88 % | −11.08 % | **−39.14 %** |
| `S/Q` **raw** | −9.66 % | −1.80 % | **+14.51 %** *(t = +3.36)* |
| `S/Q` **linear baseline** *(shipped)* | −5.38 % | −6.93 % | **−0.15 %** *(t = −0.08)* |

A **39 % fitted collapse in the far anchor** produced a **0.15 % move in the metric** *(trend statistics
throughout, as in §16.12.11 — the raw first-to-last fall in `A_far` is −32 %)*. The two quiet windows and the Q
band lost a fifth to two-fifths of their value while the Soret lost a tenth — the signature of a **scattering
pedestal clearing** while the true pigment absorbance stays put (§16.12.2's mechanism, seen far more clearly
than in any green set). The raw ratio reads that as a **+14.5 % rise**; the three-region construction
(`SPEC_capability_proof.md` §2.1a) cancels it.

**And it was not a smooth drift.** `A_far` sits at 0.143 / 0.143 / 0.142 / 0.144 through 16 minutes, then drops
to 0.117 and 0.097. That is a **step between runs 004 and 005**, not a monotone relaxation — so the ~15-minute
settling picture of §16.11.7 is not the whole story for brown. Not diagnosed; the session was not designed to.

**⚠ Do not generalise this to green.** §16.12.12 measured that brown's far window is genuinely quiet
(rise 0.007–0.021) where green's rises (0.0535). Brown's metric is therefore *structurally* less exposed to
what the far anchor does. The immunity above is a **class-dependent property**, consistent with §16.12.12/13,
not a general claim about the baseline.

### 16.13.5 Discrimination — the numbers

| | value |
|---|---|
| green mean / σ *(B+C, n=12)* | 12.370 / 0.367 |
| brown mean / σ *(D, n=6)* | **9.303 / 0.131** |
| gap | **3.066 = 33.0 %** of the brown mean |
| pooled σ | 0.275 |
| **Cohen's d** | **11.13** |
| green margin to T = 10.6 | **+4.83 σ** → false-BROWN **0.027 %** *(t, 11 df)* |
| brown margin to T = 10.6 | **+9.88 σ** → false-GREEN **0.009 %** *(t, 5 df)* |
| midpoint of the class means | 10.837 |

§16.11.12 pre-registered the two readings: *σ ≈ 0.23–0.37 → discrimination is proven*; *σ ≈ 0.83 → oil-specific
noise*. **0.131 is below the good branch's floor**, and *d* = 11.13 beats even its optimistic
"brown improves by green's factor" row (*d* = 9.81).

**The brown mean did not move across a rig rebuild and a different oil.** Archived `20260727C` (old rig, six
*fills*, §16.10.2) read **9.361**; series D reads **9.303**, a difference of **−0.62 %**. That retro-validates
§16.11.12's arithmetic, which had no choice but to borrow that old mean.

> ⚠ **Which pooled σ — the *d* above is convention-dependent, because these groups are UNEQUAL in size**
> *(added 2026-07-31)*. Green here is sets B+C pooled (**n = 12**) against brown's **n = 6**. Two formulas
> for the pooled SD are in circulation and they diverge when *n* differs:
>
> | | pooled σ | *d* |
> |---|---|---|
> | simple RMS — what `brown_series_d.py` computes | 0.2755 | **11.13** |
> | df-weighted `sqrt(((n1-1)s1² + (n2-1)s2²)/(n1+n2-2))` — the conventional choice at unequal *n* | 0.3129 | **9.80** |
>
> **The df-weighted 9.80 is the more defensible figure to quote here**, and is what a statistician would
> compute. Nothing downstream changes: both are far past any threshold, and the per-class σ-margins and
> error rates below are computed separately and are untouched. ⚠ *d* is also biased upward at small *n* —
> Hedges' correction on the df-weighted form gives **9.34**. `brown_series_d.py` now prints all three.
> *(`DOC_metric_algebra.md` §1.3 is all 6-vs-6, where the two conventions coincide exactly.)*

#### How well is σ actually known? — n = 6 is a loose estimator

The point estimate is not the honest number to plan on. A χ² interval on six points:

| σ used | margin | false-GREEN *(t, 5 df)* |
|---|---|---|
| point estimate 0.131 | 9.88 σ | 0.009 % |
| **95 % upper bound 0.322** | **4.03 σ** | **0.50 %** |
| if brown were green-like (0.367) | 3.53 σ | 0.83 % |
| old-rig assumption (0.830) | 1.56 σ | 8.95 % |

**⇒ Even at the upper end of what six runs can exclude, brown clears the threshold by 4 σ.** The conclusion does
not depend on the point estimate being right. *(t-distribution per §16.10.11a — the error is heavy-tailed, so
the Gaussian is optimistic exactly where it matters; it would read 0.000003 % on the 4.03 σ row.)*

### 16.13.6 ⚠ What this does NOT settle — σ_fill, and series E is now the only thing left

**Series D is re-seats of ONE fill.** Every number above excludes sample preparation. The shipped protocol
(§16.10.17b) and the projected decision table (§16.11.11) are both built on **σ_fill**, which remains exactly as
unmeasured as it was yesterday — the historical brown figure is **10.5 % on n = 2 fills, t = 1.47, not
significant** (§11.4f B).

**Nothing here may be shipped on the strength of series D alone.** §16.11.13's protocol inversion is explicitly
gated on brown behaving like green *from fills*, and §16.11.11's "12/12 clearing on one fill" projection needs
σ₁ from fills, not re-seats.

**One weak prior update, offered as no more than that.** §11.4f B's competing hypotheses for brown's
fill-to-fill weakness are (i) the aliquot step — real sampling variation — and (ii) an artifact of the baseline
correction. Series D shows the correction *rescuing* brown from a 39 % pedestal collapse rather than injecting
noise into it, which sits awkwardly with the crude form of (ii). It is not a test of (ii): re-seats of one fill
are not fills, and the pre-registered discriminator remains series E reporting **raw and baselined side by
side**, in **time order** (§11.4f B3).

### 16.13.7 Two negative results from the same six runs

**Colour does not discriminate these two classes at all.** All five chips of `SPEC_color_retrieval.md`, across
green B+C and brown D:

| chip | green *(n=12)* | brown *(n=6)* |
|---|---|---|
| Intrinsic | H 298–300° | H 298–300° |
| Intrinsic-perceived | H 67–69° | H 68–69° |
| Perceived | H 70° | H 70–71° |
| hue-normalised variants | H 300° · S 38 % · L 34 % | H 300° · S 38 % · L 34 % — **identical** |

This **confirms §16.10.15** ("colour channels do NOT discriminate this oil pair") on post-rebuild data and
extends it from channels to the full HSL colour-retrieval path. The chips remain worth showing as a
presentation feature; they are not a verdict input, and no threshold should ever be hung on them.

**Metric ranking — only the shipped one works.** Cohen's *d*, green vs brown, on the despiked dev metrics.
*(Green here is sets B+C pooled, n = 12, against brown's n = 6 — so these are RMS-convention values on
unequal groups, §16.13.5. The **ranking** is unaffected: the convention scales every row alike.)*

| metric | *d* | |
|---|---|---|
| **`S/Q linear base`** *(shipped)* | **11.13** | the only usable one |
| `G'` (alt.) | −5.33 | **sign inverted** — brown reads *higher* |
| Pigment `D_Q` | −2.48 | inverted |
| Greenness `G` | −1.99 | inverted |
| `A_Soret` | 1.18 | weak |
| Clarity `A_green` | 0.54 | none |
| **Pigment ratio · legacy** | **0.11** | **useless** |
| Pigment ratio · clarity | — | raw CV 12.1 %, degraded further (clarity itself 13.3 %) |

Consistent with §16.10.13's bench, on a class pair it had not seen.

### 16.13.8 ▶ Next, revised

| | action | why it moved |
|---|---|---|
| **1** | **⭐ Series E — brown, 6 separate fills, time-ordered, raw + baselined side by side** | now the **only** thing between the milestone and its gate. §16.12.16 item 1 already promoted it; series D removes every competing candidate for "most informative measurement available" |
| 2 | §16.12.16 item **2c** — re-run the far-anchor sweep on post-rebuild data | **unblocked**: it was waiting on "a proper brown series" and now has one |
| 3 | §16.12.16 item **2** — declare 600–630 an explicit third band? | also gated on post-rebuild brown data; §16.13.4 adds a fourth axis (settling immunity, class-dependent) to the argument |
| 4 | Diagnose the **run-004→005 step** in the quiet windows | new, from §16.13.4. Cheap: it is visible in data already on disk, and it does not fit the ~15-min relaxation picture |
| **5** | **⭐ The ACID TEST — demetallate half of one oil and re-measure** | new, from §16.13.9. One bottle, split, half acidified; same turbidity, same dilution, **one variable**. Converts "the far-window slope tracks demetallation" from the best available explanation into a measured causal link. An afternoon and a drop of acid |
| — | the `cone` arm and the mechanical programme | **stay demoted** (§16.12.11). Brown's seating is 1.58 % residual; there is no mechanical win of that size left to take |

**Unchanged:** the 1-butanol trial (§16.12.7) remains the only unblocked line of attack on the drift itself, and
§16.13.4 raises its value — the settling it would remove is **larger on brown than anything green showed**.

### 16.13.9 ⭐ The far-window difference is SPECIATION, not concentration — and the instrument is not the limit  *(Edwin's question 2026-07-31, `diagnostics/qband_shape.py`)*

§16.12.12 measured that the 600–630 rise separates the classes at 5.1 σ but never asked **why**. Two
explanations were live and had never been separated:

| | prediction |
|---|---|
| **(a) concentration** — brown simply has less pigment | brown = *k* × green: one scale factor, **same shape** |
| **(b) speciation** — brown has a different *mixture* of pigment molecules | the **shape** changes, not just the amplitude |

#### The test has no free parameters

Under (a), any ratio of two features taken **inside** the Q region is class-independent, because *k*
cancels. So a class difference in such a ratio refutes (a) outright. Ratios are built from
**differences** wherever possible, since a difference cancels the additive turbidity pedestal — the one
large known contaminant (52–61 % of `A_Q`).

| | green `20270729C` | brown `20260731A` | *d* |
|---|---|---|---|
| `A_Q` 560–580 | 0.2300 ± 0.0173 | 0.2251 ± 0.0199 | **0.26** — equal |
| `A_Soret` 440–460 | 1.1864 | 1.0855 | 2.31 — 9 % apart |
| `A_far / A_Q` | 0.6889 | 0.5794 | 2.49 |
| rise (620–630 − 600–610) | 0.0547 | 0.0121 | 6.61 |
| Q amplitude (572 − 550) | 0.1275 | **0.1495** | **−3.16** — brown HIGHER |
| **rise ÷ Q-amplitude** | **0.4274 ± 0.039** | **0.0800 ± 0.028** | **10.26** |

**⇒ (a) is REFUTED.** Pure scaling predicts *d* = 0 on the last row; measured *d* = **10.26**, a factor
of **5.3**. Brown is not pigment-poor — `A_Q` is *equal* and its 572 feature is *stronger*. The
Q-region shapes genuinely differ.

#### Where the intensity went

Normalising each class by its own Q amplitude:

| region | green | brown | brown − green |
|---|---|---|---|
| 560–580 nm | 0.803 | 0.813 | +0.010 *(anchor)* |
| 580–600 nm | 0.216 | 0.321 | +0.106 |
| 600–615 nm | 0.076 | 0.150 | +0.074 |
| **615–630 nm** | **0.407** | **0.215** | **−0.193** |

Intensity has moved **out of 615–630 and into 580–615** at roughly constant total. That is the direction
demetallation predicts: in a free-base porphyrin the longest-wavelength Q band (band I) is the **weakest
of the four in every substitution class** — etio, rhodo, oxo-rhodo and phyllo alike
(`KB_spectroscopy_physics.md` §4.1). Protochlorophyll's Qy(0,0) is its dominant long-λ band; on losing
the Mg it becomes band I of four, i.e. the weakest.

#### ⚠ The instrument is NOT the limiting factor — this is a WINDOW problem

It is tempting to read "we cannot see the 2-vs-4 band structure" as a resolution limit. It is not:

| | |
|---|---|
| grid spacing | 0.146 nm/bin, 1305 bins over 440–630 |
| 473 nm lamp artifact | **FWHM 1.0 nm** |
| 607 nm registration artifact | **FWHM 2.7 nm** |
| Q bands to be resolved | **20–30 nm** |

**The rig out-resolves the target by 10–20×.** What actually prevents the structure being seen is
(1) **window truncation** at 630 nm — the dominant limit; (2) the two species **always coexisting**, so
no pure spectrum of either is ever observed; (3) **20–30 nm intrinsic linewidths** in room-temperature
solution, which merge the four free-base bands into shoulders; and (4) the **turbidity pedestal**
suppressing contrast.

**⇒ A better spectrometer buys nothing. A wider window buys everything.** This is an independent — and
possibly the strongest — argument for §16.12.16 item 2h.

#### Epistemic status, stated plainly

| link | status |
|---|---|
| the pigments are protochlorophyll + protopheophytin | **sourced** (Fruhwirth & Hermetter 2007) |
| roasting/ageing strips the Mg | **sourced** (same; storage range 1–36 %) |
| Mg loss ⇒ D₄ₕ→D₂ₕ ⇒ 2 Q bands → 4 | **deduction** from group theory |
| free-base band I is the weakest ⇒ long-λ intensity falls | **sourced** (etio/rhodo/oxo-rhodo/phyllo classification) |
| the two classes' Q-region shapes differ | **measured** here, *d* = 10.26 |
| the cause is *specifically* demetallation | ⚠ **abduction** — best available explanation, not a controlled result |

The last row is the honest weak point: these are **two different bottles**, which differ in more than
their protopheophytin fraction. Everything upstream survives even if it is wrong — the *speciation*
reading holds regardless; only the *mechanism* would change.

**▶ The experiment that would close it, and it is cheap.** Take **one** oil, split it, and deliberately
demetallate half — acidification is the standard laboratory route from chlorophyll to pheophytin. Same
bottle, same turbidity, same dilution, **one variable**. If the 600–630 slope collapses in the acidified
half, the causal link is measured rather than inferred. An afternoon and a drop of acid.

---

## 16.14 The ALGEBRA of dilution invariance — which metrics are invariant by theory, and what actually breaks it  *(Edwin's question 2026-07-31, after `DOC_metric_algebra.md`; DERIVATION + one experiment design, nothing implemented)*

§16.10.8 declared dilution invariance unmeasurable and §16.11.6 gave the first evidence in the right direction.
Neither asked the prior question: **which of our metrics is invariant *by construction*, and what is the
mechanism by which the shipped one fails?** The answer turns out to be sharp, and it converts §16.10.8's
open question from "does it hold?" into a **bounded quantity with a distinctive experimental signature**.

### 16.14.1 The model

```
A(λ)  =  ε(λ)·c·l   +   P(λ)
         pigment        scattering pedestal
```

`ε` extinction, `c` concentration, `l` path length; `P` the turbidity pedestal, which does **not** track pigment
concentration (§5 of `DOC_sample_physics.md`). Dilution invariance = unchanged under `c → k·c`.

### 16.14.2 With no pedestal the shipped metric is EXACTLY invariant — and the proof is one line

Every step from the curve to the two corrected band means is **linear and homogeneous** in the data: the band
mean, the least-squares line fit through the anchors, and the subtraction. So scaling the input scales the
output identically:

```
B_X  =  c·l·( ε̄_X − ℓ_ε(λ̄_X) )  ≡  c·l·e_X
```

where `ℓ_ε` is the line the fit produces on `ε` alone and `e_X` is the band's baseline-corrected extinction.
Hence

```
S/Q_lin  =  e_Soret / e_Q
```

with `c` and `l` gone. **A degree-1 homogeneous functional over a degree-1 homogeneous functional is degree-0.**
This is invariance by construction, not by approximation.

⚠ One sub-step is worth recording because it is *exact* and is easily mistaken for an approximation:
`B_X = A_X − L(λ̄_X)` holds exactly, because the mean of a straight line over a window equals that line at the
window's centroid. The only approximation in the three-region identity (§2.1a of `SPEC_capability_proof.md`) is
replacing the least-squares slope with the two-centroid slope — **not** this step.

#### ⭐ The proof never mentions chlorophyll — so the far-anchor contamination is HARMLESS to invariance

The homogeneity argument uses only that a component scales with `c`. §16.12.12's finding — that 600–630 nm
carries real pigment — therefore **does not break dilution invariance at all**. That pigment scales with `c`
exactly as the band pigment does and cancels in the quotient along with everything else. It changes the
*effective* `e_X`, i.e. what the metric means chemically; it does not change whether it is invariant.

This is worth stating loudly because the intuition runs the other way: the contamination looks like the metric's
dirty secret, and on this axis it is not one. **§16.12.13's warning stands for discrimination, not for
invariance.**

### 16.14.3 The classification — every shipped metric

The rule that falls out: **a ratio is dilution-invariant iff its numerator and denominator are both
pedestal-free and corrected the same way.**

| metric | invariant by theory? | why |
|---|---|---|
| every band mean — `A_Soret`, `A_Q`, `A_clarity`, `A_near`, `A_far`, `B_Soret`, `B_Q`, `A_blue`, `D_Q` | **never** | all scale with `c` by construction |
| **`S/Q_lin`** *(shipped)* | **yes** — exactly, if `P` is linear in λ | both terms had the *same* line subtracted |
| `S/Q_plain`, `S/Q_clarity`, `S/Q_legacy` | only if `P ≈ 0` | uncorrected; `P` survives in both terms and does not scale |
| `G = D_Q/A_clarity`, `G' = D_Q/A_blue` | **no** | **mixed** — a locally baseline-corrected numerator over an *uncorrected* denominator |

⚠ The `G`/`G'` row is a defect that had not been named before: these two are not merely weak discriminators
(§16.13.7 measured `G` at *d* = −1.99, `G'` at −5.33), they are **structurally incapable** of dilution
invariance, because the correction is applied to one side of the quotient only.

### 16.14.4 What actually breaks it — pedestal CURVATURE, and nothing else

Put `P` back. The fit is linear, so it splits cleanly:

```
B_X  =  c·l·e_X  +  r_X          with   r_X  =  P̄_X − ℓ_P(λ̄_X)
```

`r_X` is the pedestal's **departure from its own best-fit line**, evaluated at band X. Then:

| pedestal | invariance |
|---|---|
| `P = 0` | exact ✓ |
| `P` exactly **linear** in λ | **also exact** ✓ — the fit removes it completely, `r ≡ 0` |
| `P` curved | broken, in proportion to `r` |

**⇒ Invariance fails only to the extent that turbidity is non-linear in λ over 440–630.** Scattering goes
roughly as λ⁻ⁿ, and a straight line is an approximation to a curve; that curvature is the *entire* residual
error. Nothing else in the construction can produce a dilution dependence.

*(This also re-frames §16.12.6 B's λ⁻ⁿ experiment. That test was withdrawn as invalid because an anchor contains
pigment — but the quantity it was reaching for, the pedestal's shape, is exactly `r`. The experiment was asking
the right question with the wrong instrument.)*

### 16.14.5 The sensitivity — and why the denominator is hit ~10× harder, again

Differentiating `S/Q_lin = (x·e_S + r_S)/(x·e_Q + r_Q)` with `x = c·l`, for small residuals:

```
d ln(S/Q_lin) / d ln c   ≈   r_Q/B_Q  −  r_S/B_Soret
```

Measured band values (§16.13 / `DOC_metric_algebra.md`): `B_Soret` ≈ 1.10 (green) / 1.01 (brown),
`B_Q` ≈ 0.090 / 0.109. So `B_Soret/B_Q` is **12.3 (green), 9.3 (brown)** — the *same* absolute curvature
residual is an order of magnitude more damaging in the denominator. The second term is negligible and

```
d ln(S/Q_lin) / d ln c   ≈   r_Q / B_Q
```

This is the same amplification structure that makes the plain ratio fail (§16.13 / §6 of the doc: the pedestal is
~7 % of the Soret band but **52–61 % of the Q band**). The baseline shrinks it greatly; it never removes it.

### 16.14.6 ⭐ The error is CONCENTRATION-DEPENDENT — and that gives a falsifiable signature

`r_Q` is **fixed**; `B_Q = c·l·e_Q + r_Q` **grows with concentration**. Therefore

```
sensitivity  ≈  r_Q / (c·l·e_Q)     ∝  1/c
```

**The metric becomes more invariant as you concentrate, and degrades at high dilution.** Two consequences:

**(a) A log–log plot of `S/Q_lin` against concentration must be CURVED, flattening toward high `c`.** A
*constant* log–log slope would falsify the pedestal-curvature explanation and point at something else — genuine
concentration-dependent chemistry, or stray light. This is a much sharper test than "is the slope zero?", which
is what §16.10.8's design was reaching for, and it needs the same runs.

**(b) The error curve is U-shaped, so there is an optimal working concentration.** Pedestal curvature degrades
invariance at **low** `c`; §16.11.8's Soret stray-light compression degrades it at **high** `c` (the numerator
saturates, `T` at the Soret is already 6.5 %). These are different mechanisms failing in opposite directions.
The recipe should sit at the minimum between them — which is an argument that §16.11.15's "keep 18 ml + 6 drops"
is defensible on a second, independent axis, and a reason not to move it in either direction casually.

⚠ **This is in direct tension with any "just concentrate more" instinct.** Raising `c` improves dilution
invariance *and* worsens the Soret compression. Neither effect is currently measured well enough to locate the
minimum.

### 16.14.7 Against the measured record

| | |
|---|---|
| baseline halves the dilution error | 5.49 % → **2.75 %** (§16.12.16 item 2d, `baseline_vs_raw.py`) — consistent: the correction removes the linear part of `P` and leaves `r` |
| §16.11.6's two dilutions | 17 % apart in `A_Q` → **1.9 %** in the metric, `t = 1.14, p = 0.28` |

Taking §16.11.6 at face value, `ln(12.251/12.489) / ln(0.230/0.197) = −0.124`, i.e. an apparent log–log slope of
≈ **−0.12**, which via §16.14.5 implies `r_Q` of order **−0.01 A**.

⚠ **Do not quote that as a measurement.** It is not statistically distinguishable from zero (`p = 0.28`), it
rests on `n = 2` dilutions only 17 % apart, and it uses `A_Q` as a concentration proxy — which §16.10.8 showed is
itself compromised by seating. Treat `|r_Q| ≲ 0.01 A` as an **upper bound**, and note the sign is the direction
§16.14.6(a) predicts for a curved pedestal.

### 16.14.8 What this does and does not settle

**Settles:** which metrics *can* be invariant (§16.14.3); that the far-anchor contamination is irrelevant to
invariance (§16.14.2); and that there is exactly **one** mechanism to chase, not several (§16.14.4).

**Does not settle:** whether `r_Q` is actually small. §16.10.8 stays open. But its experiment now has a
quantitative target and a distinctive shape to look for rather than a null hypothesis to fail to reject.

**⇒ A prediction that costs nothing and is worth writing down before the solvent work:** if the residual
dilution error and the settling drift are both the pedestal, then **clearing the sample must shrink BOTH
together** — the 1-butanol trial (§16.12.7) or the 0.22 µm filter (§16.12.9). If one collapses and the other
does not, this model is wrong. That is a free extra readout on runs already planned, and §16.12.7's trial
should record the dilution error alongside the CV it was designed to measure.

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
