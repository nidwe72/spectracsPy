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

---

## UC4 · Gamma verification + protocol change  ·  _2026-07-26_  ·  _status: ✅ ANALYSED (no new captures)_

**Goal.** Settle whether the camera's brightness non-linearity (the "2.2 law") can move the Roast Ampel verdict —
the question parked in [`SPEC_capture_quality.md`](SPEC_capture_quality.md) §17. **No rig time**: everything was
re-computed from data already embedded in the report PDFs. Full write-up in **§17.5** of that spec; band re-test in
[`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) §1b.3.

**Data used.** The two fresh-2026 captures `measurement_report_NowSBudget.pdf` (S-Budget, brown) and
`measurement_report_NowSteirerkraft.pdf` (Steirerkraft, green), plus the 32-run K/L/M/N + O/P/Q/R set for scatter.
Each PDF carries `workflow.json` (meaned R+S spectra) **and** both 2592×1944 RGB frames as `/EmbeddedFiles` — enough
to replay the pipeline at spectrum *and* pixel level. Replay matched the app bit-for-bit (4.05906808789795 and
5.182554) and reproduced the published group stats 3.75 ± 0.13 / 2.47 ± 0.11 exactly.

**Result — the verdict cannot be moved by gamma.** Decoding R and S with a pure power law at γ = 1.8 / 2.2 / 2.6
leaves the pigment ratio **bit-identical** (4.0591 and 5.1826, 15 significant digits) — `A_true = γ·A_measured` is a
uniform scale that a band ratio divides out. Absorbed hue *and* chroma are equally invariant (chromaticity ignores
scale). Only the *perceived* colour moves, and it is the one axis that does not discriminate the oils.
**Consequence for the fleet:** the condition is "*a* pure power law", not 2.2 specifically — so ratios from Edwin's
different cameras are already comparable today.

**Result — the piecewise sRGB EOTF is DECLINED.** The physically-faithful curve (linear toe below DN 10.3) rescales
the Soret band by a *sample-dependent* amount, because the browner oil dips deeper into the toe (17.4 % of its bins
vs 4.3 %). Cost, on the 32-run set: green SD **0.134 → 0.201** (+50 %), gap/noise **10.39 → 7.87 (−24 %)**, absorbed
chroma gap 11.8 → 9.7. Colour gain unchanged (43.7 vs 43.1 perceived chroma). Same direction on the 2026 pair.
⇒ **pure `x^2.2`**, deliberately chosen over the standard curve; recorded so nobody "fixes" it later.

**Result — band 440–460 re-tested, KEPT.** Shifting to 450–470 (to escape the toe) costs **25 %** of the
discriminating power. The lamp's blue-pump edge (ref DN 186 → 228 at 472–474 nm) turned out to be a non-issue — it
appears in R *and* S and **cancels in `T = S/R`** (despiker deviation 0.0019 there). What the despiker actually
flags is the **left** edge, 440.0–440.3 nm, deviation 0.166. A 442–460 trim scores best of all (10.84, +4 %) but was
declined as not worth another threshold re-anchor.

**⭐ Lab-condition change (Edwin) — the real finding.** The 2026 oils are **fresher and absorb much more** than the
aged 2023 oils. What got through at 4 ml + 2–3 drops in 2023 is now **over-absorbing**: sample bottoms out at
**DN 5 of 255** at 440 nm, 17 % of the Soret band sitting in the camera's toe. **The standard setup must change.**

**New protocol (see [`SPEC_capability_proof.md`](SPEC_capability_proof.md) §7.3).** Batch-and-pour at **1:30–1:33**
— *6 ml + 2 drops* improvised now, *10 ml + 3 drops* once the 10 ml graduated cylinder arrives; the transfer volume
does not matter (only the batch concentration does), so just fill the pot. Predicted effect: Soret floor
**5 → 16–25 DN**, **0 %** of bins in the toe, pigment ratio unchanged to **±0.35 %** ⇒ **Ampel threshold 4.4
carries over** and the 1:20 archive stays comparable. Neatly, this also makes the whole toe debate moot going
forward. **Not yet verified on the rig** — next bench session should run one oil at both 1:20 and 1:30 to confirm
the invariance directly.

**Open (minor):** low-DN guard (report per-capture band-minimum DN — largely obsolete once the protocol lands);
`dilution` metadata field; one-batch repeatability run to split prep noise from instrument noise in the 8.7 %
within-oil spread.

---

## Desk day — the sample, not the instrument  ·  _2026-07-31_  ·  _status: no rig time, 8 analyses, several claims withdrawn_

**Question asked.** Why does a fresh dilution drift for its first ~15 minutes (§16.11.7), and would a different
solvent or vessel help? **Everything below is analysis of PDFs already on disk.** New tools in `diagnostics/`:
`settling_sweep`, `settling_plot`, `far_anchor_probe`, `far_anchor_sweep`, `baseline_vs_raw`,
`baseline_variants`, `without_b002`, `pedestal_by_vintage`.

**1 · The settling drift reaches the shipped metric.** −5.4 % (set B) / −6.9 % (set C, t = −5.60) over ~30 min.
Detrending drops the pooled CV **2.92 % → 1.89 %**, so **58 % of what was counted as seating noise is a time
trend**. True seat-to-seat repeatability is ≈1.9 %. ⇒ §16.11.9's budget closure does not hold — the `jar` arm
over-predicts — and **the binding constraint moved from the mechanics to the liquid**. Curves:
`spectracs-references/tmp/settling_curves.png`.

**2 · The far baseline anchor is not oil-quiet — it measures pigment.** 600–630 nm carries real chlorophyll
absorption at **5.1 σ** (rise: green 0.0535 vs brown 0.0159 under an identical lamp — 37 runs, 6 fills, 2
sessions). It is the flank toward the true Q maximum near 665 nm, outside our clamp. **And it carries the
discrimination**: sweep the far edge in and Cohen's *d* falls **2.88 → 0.94** until the classes overlap. The
metric is a **three-region construction** (algebra verified against the code to 0.5 %) — restated in
`SPEC_capability_proof.md` §2.1a, and the `DevSpectralPlugin` comment corrected.

> ⚠ **Correction added later the same day** (left in place per the withdrawn-claims practice): "real
> **chlorophyll** absorption … flank toward the true Q maximum near **665 nm, outside our clamp**" names
> the **wrong molecule**. The oil's pigment is **protochlorophyll / protopheophytin** (Fruhwirth &
> Hermetter 2007 — the paper on our own disk), whose Qy band is at **~623–626 nm**, i.e. **at the edge of
> the clamp, not beyond it**. The 5.1 σ measurement and every consequence drawn from it stand; the
> attribution gets *stronger*. Sources and the full account: `KB_spectroscopy_physics.md` §4.1.

**3 · There is no better baseline available on a 440–630 window.** Twelve variants — offset-only, power-law,
AsLS, ModPoly, rubber band, full-range line, quiet-anchored LSQ and polynomials. **Monotone trade-off**: the more
spectrum a baseline may follow, the better it removes drift and dilution and the more class signal it removes
with them. AsLS gave the best dilution invariance of anything tested (−0.72 %) *and* 21/25 errors. The escape is
spectral coverage past ~700 nm — optics, not software.

**4 · ⭐ The 2023-vs-2026 gap is SOLVED, and it was Edwin's hypothesis.** The 2023 oils were bought in 2023 and
had three years to **clarify in the bottle**: pedestal **0.84 ± 0.19** against the fresh oils' **1.72 ± 0.23**,
no overlap on a single fill. That was the item flagged as the one thing that could kill the concept; it
decomposes into a **turbidity** half (raw CV 2.54 → 14.54 %, fixable three ways) and a **panel** half (Soret/Q
separation 1.96× → 1.36×, i.e. two oil pairs are differently far apart). **Neither is fatal.** Full account:
`SPEC_capability_proof.md` §11.4e.

**⇒ Clearing the oil is worth ~6× in discriminating power** (*d* 24.25 at pedestal 0.84 vs 2.88 at 1.72) — an
*observed* effect, not a projection, and the strongest argument yet for the butanol trial.
*(2026-08-01: 1-butanol subsequently rejected on hazard — H318 — and replaced by **2-butanol**; §16.12.7a.
The argument for a butanol is unaffected, the substance changed.)*

**5 · The aliquot step named.** The batch is mixed in a lab glass and a 4 ml aliquot goes to the jar — so the
transfer is a **sampling step out of a settling dispersion**, and it is the best fit to the brown fill-to-fill
asymmetry (green 0.0 %, brown 10.5 %). Pre-registered with the test that separates it from the competing
baseline-artifact explanation: §11.4f B2–B4.

**Claims made and WITHDRAWN today** *(nine; the full list is in `SPEC_capture_quality.md` §16.12.15 and
§11.4e)*. The load-bearing ones: *"camera self-heating is the confound"* (the camera streamed continuously);
*"λ⁻ⁿ scattering refuted"* (the test was **invalid**, not negative — one anchor contains pigment);
*"the mechanism inverted between the oil eras"* (unnormalised band means across different concentrations);
*"the rebuild made the baseline 120 % more valuable"* (**one run, B002, carries it**); *"heptane dissolves
polystyrene"* (RED 1.10 — it swells and crazes). **B002 stays in**, per §16.11.11's V2 rule: it has no physical
cause documented independently of the data, and dropping the worst re-seat from a re-seat-repeatability
measurement is circular.

**⇒ New practice: §11.4f is a PRE-REGISTRATION** — predictions and pass/fail for series D/E and the butanol
trial, written before the runs and not to be edited afterwards. Two of today's nine withdrawals were
after-the-fact-analysis traps; this is the cheapest available guard.

**Also written today:** `KB_spectroscopy_physics.md` §8 (solvent chemistry, the pedestal, Hansen/RED for the
vessel) and a new textbook document, `DOC_sample_physics.md` → *Light, Pigment and Solvent*
(`spectracs-docs/internal/`, 17 pp) — the companion to *Capture Fidelity*, covering everything in front of the
instrument.

**▶ Next, unchanged by any of this:** **brown series D and E** — and E must report **raw and baselined side by
side**, with the fills in **time order**.

---

## Series D — the brown oil, and the gate's discrimination criterion closes  ·  _2026-07-31 (evening rig session)_  ·  _status: PASS, pre-registered_

**Six re-seats of one brown fill** (`spectracs-references/tmp/20260731A/`), post-rebuild, still isopropanol —
§16.11.11 step 2's first half and the load-bearing measurement of the milestone. Scored against §11.4f A,
written the same morning and not edited. New tool: `diagnostics/brown_series_d.py`, deliberately built on
`settling_sweep`'s `measure`/`detrend` so the numbers are comparable with the green sets.

**1 · PASS, by twice the predicted margin.** Brown σ = **0.131** — raw CV **1.41 %** against a pre-registered
2.5–3.5 %. §16.11.12 offered two branches (σ ≈ 0.23–0.37 proves discrimination; σ ≈ 0.83 says the rebuild
helped green only); the result sits **below the good branch's floor**. Brown improved *more* than green did,
which is what §16.7.2o's "sobering" refutation predicted once it was read the right way round.

**2 · Discrimination.** Green 12.370 ± 0.367 vs brown **9.303 ± 0.131** — gap 33.0 %, **Cohen's *d* = 11.13**.
*(Later the same day: that *d* pools unequal groups — 12 green against 6 brown — with the RMS convention.
The conventional df-weighted form gives **9.80**; §16.13.5. The conclusion is unaffected.)*
At the shipped T = 10.6: green **+4.83 σ**, brown **+9.88 σ**. The ~10 % false-GREEN that §16.11.12 called
"all the remaining risk" becomes **0.009 %** — and **0.50 % even at the 95 % upper bound on σ**, so the
conclusion does not rest on six points estimating σ well. The brown mean also **survived the rebuild and a
different oil**: 9.303 against the archived 9.361, −0.62 %.

**3 · ⚠ The headline overstates it ~2×, and the diary should say so.** Green's 2.96 % is mostly a settling
trend (§16.12.11); detrended it is 1.89 %. Brown has **no trend to remove** (−0.15 %, t = −0.08), so the
like-for-like comparison is **1.58 % brown vs 1.89 % green** — close, not 2×. What brown really did better was
not accumulate a trend in the metric.

**4 · ⭐ And that is the finding.** Brown's *absorbances* settled ~3× harder than green's — `A_far` **−39 %**,
`A_near` −34 %, `A_Q` −23 %, against `A_Soret` −10 % — and the shipped metric moved **0.15 %**. The raw ratio
reads the same session as **+14.5 %**. A 39 % collapse in a baseline anchor producing a 0.15 % move is the
strongest common-mode-rejection evidence in the record, and it is the fourth independent argument for the
three-region construction (§2.1a). ⚠ Class-dependent: §16.12.12 measured brown's far window as genuinely quiet
where green's rises, so this does **not** generalise to green. Also **not a smooth drift** — `A_far` is flat for
16 minutes then steps between runs 004 and 005, which the ~15-minute relaxation picture does not explain.

**5 · One prediction wrong, recorded as such.** The −3 to −8 % settling trend predicted for brown's metric came
back as −0.15 %. It was extrapolated from green and the extrapolation was invalid for the reason in item 4.

**6 · Two negative results from the same six runs.** *Colour does not discriminate* — all five chips of
`SPEC_color_retrieval.md` read the same for both classes (hue-normalised variants **identical**), confirming
§16.10.15 on post-rebuild data and extending it from channels to the full HSL path. *Only the shipped metric
works* — `G'` *d* = −5.33 (**sign inverted**), `D_Q` −2.48, Greenness −1.99, and **pigment-ratio-legacy 0.11,
i.e. useless**.

**⇒ What is left is σ_fill, and only σ_fill.** Series D is re-seats of ONE fill; sample prep is excluded
entirely. §16.11.13's protocol inversion and §16.11.11's projected decision table are both built on σ₁ from
*fills* and stay gated. **Series E** — 6 separate fills, time-ordered, **raw and baselined side by side**
(§11.4f B/B2–B4) — is now the single measurement between the milestone and its gate.

**⚠ Unchanged by any of this:** `T = 10.6` is still **unvalidated**. Series D improved precision, not
correctness, and a 9.88 σ margin against a possibly-wrong threshold is a confident answer to the wrong question.

**Also unblocked:** §16.12.16 item 2c (re-run the far-anchor sweep on post-rebuild data) — it was waiting on
"a proper brown series" and now has one.

---

## The Kiendler session — an experiment that failed, and the pedestal that explains why  ·  _2026-08-01/02 (evening rig session)_  ·  _status: green confirmed; dilution question NOT answered; `r_Q` measured_

**Three preparations of one green oil** (`spectracs-references/tmp/20260801A|B|C/`, ten reports) — Ulrich
Kiendler, §11.4f F step 3's "green #2", run so as to double as the deliberate dilution-invariance experiment
§16.10.8 has wanted for weeks. Full account: `SPEC_capture_quality.md` §16.15. New tool:
`diagnostics/kiendler_dilution.py`.

**0 · The oils finally have names.** Kiendler (this session), **Steirerkraft** (`20270729B/C`, green #1),
**Spar S-Budget** (`20260731A`, series D brown) — corroborated by the archive's own filenames. Edwin's visual
read, *"Kiendler a little bit greener than Steirerkraft"*, is recorded **as** §11.4f D3's operator pre-read. It
is the only independent ground truth the campaign has, and it costs nothing.

**1 · The oil is green, decisively, and that part went exactly as designed.** A **14.279** ± 0.491, B **12.740**
± 0.065, C **13.039** ± 0.126 against T = 10.6 — margins +7.5, +4.4, +5.0 σ. Cohen's *d* vs brown **7.59**;
§16.13.9's parameter-free shape discriminator **9.73**, alongside Steirerkraft's 10.26, and flat across all
three preparations. A fifth oil-set that does not cross the threshold against Edwin's own read.

**2 · ⚠ The dilution experiment failed, and the Beer-Lambert control is how we know.** A nominal **1.214×**
concentration step moved `A_Soret` 1.36×, `A_Q` 1.80× and the **520–540 turbidity anchor 2.43×**. The two
*baseline-anchor* windows — pedestal, not pigment — moved the most. Set A's turbidity, 0.038, is the lowest of
the six post-rebuild sets; the other five sit at 0.09–0.13. **Set A was the anomaly, not B and C.**

**3 · And set A was still changing while it was measured.** Over 32 minutes: `A_near` **−36.8 %** (t = −6.93),
`A_Q` −17.3 %, `A_Soret` −8.3 % (t = −14.36) — while the shipped metric moved −1.3 % (t = −0.30). The lamp was
flat throughout, so this is the sample. Oil suspended rather than dissolved, separating in the beaker; B was
restirred and C was fresh, both read promptly. Same term as §16.12.6's settling drift, three times larger, and
for the first time **large enough to break a designed experiment**.

**4 · ⭐ Edwin caught the write-up understating it, and he was right.** His reading of the raw table — *"the
stronger dilutions have lower S/Q, so things are dilution-dependent?"* — is correct on every pair, and nominal
concentration is in fact the **only** self-consistent axis (slopes −0.59/−0.59/−0.58, spread 0.01; turbidity
fails the C→B pair in sign). The first draft of §16.15 had called the concentration axis "void". That was
wrong and is recorded as wrong. What is true is weaker: the session contains **effectively one contrast** — set
A against the two stirred preps — in which concentration and turbidity moved together, so it cannot separate
them; and −0.59 is separately incompatible with the archive's 1.5× pairs (predicts −21 %, measured +0.4 % and
+4.9 %). Set A's depletion is only 8–21 %, where ~53 % would be needed to reconcile.

**5 · ⭐⭐ And then the two readings turned out to be the same mechanism.** §16.14.4–6 had already *derived*
that invariance breaks only through `r_Q`, the pedestal's departure from its own best-fit line, with an error
`r_Q/B_Q` that is **concentration-dependent ∝ 1/c**. Set A had the smallest `B_Q` and read highest — the
predicted shape exactly. **Turbidity sets `r_Q`; concentration sets `B_Q`; the bias is their ratio.** §16.15.5's
either/or was a false dichotomy, and the argument between the two explanations dissolved rather than being won.

Fitted without any concentration axis at all — `B_Soret = M_inf·B_Q + (r_S − M_inf·r_Q)`, a line whose
**intercept is the residual**: Kiendler `r_Q` = **−0.0246 ± 0.0037 A** (intercept 7 σ from zero), Steirerkraft
**−0.0212 ± 0.0193**. **Two independent oils, same residual, same `M_inf`.** §16.14's model, until now pure
derivation, **describes measured data** — and its residual is **~3× §16.14.7's asserted bound of 0.008 A**,
which is superseded.

**6 · ⚠⚠ The corollary nobody will like.** Pedestal-free class index: Kiendler **10.00 ± 0.50**, Steirerkraft
**9.93 ± 2.15**. The shipped threshold is **10.6 — above both.** Remove the pedestal and **both green oils fall
below the threshold meant to certify them.** `T = 10.6` is not pigment-intrinsic; it is calibrated on inflated
numbers and tied to the current turbidity regime. **A successful clarification — the 0.22 µm filter, the
solvent programme — would silently invalidate it.** Nothing in the spec said so before today.

Worse for the panel: on that scale the two green oils are **indistinguishable**, though their measured means
differ by 10.9 %. So *"Kiendler is greener"* may be a pedestal difference, not a pigment one. Steirerkraft's
error bar is too wide to decide. **OPEN.**

**7 · The pre-registered prediction is not decidable, and that is the format's fault.** §11.4f D2's "green #2
within 10 % of green #1" fixed a threshold but never named the estimator: all runs pooled **+10.9 % (FAIL)**,
mean of set means +7.9 % (PASS), stirred fills only +4.2 % (PASS). Recorded **UNDECIDED** rather than picked
after the fact. **A threshold without an estimator is not a pre-registration** — §11.4f's own §16.10.16 trap,
sprung on the section that was written to avoid it.

**8 · One encouraging number.** B vs C — independent preparations 1.041× apart — agree to **−2.29 %** on the
shipped metric and **+0.15 %** raw. df = 1, so it falsifies rather than estimates, but it is the absence of bad
news §11.4f F wanted.

**▶ Next, and it is cheap:** repeat set A's recipe — **18 ml + 6 drops, read immediately after stirring**. Same
concentration as A, same turbidity as B/C. Lands near **12.9** ⇒ the pedestal did it; near **14.3** ⇒ Edwin's
dilution dependence is real and large. Nothing else in the queue separates them.

**Also now due:** fix and record stir-to-measure latency; log `A@520–540` as a per-run QC covariate (free, and
it would have flagged set A before anyone looked at the ratio); and **promote B4, the €15 scale** — at the
corrected slope, 10–20 % drop-volume scatter is a 2–8 % metric error against a 1.4–3.4 % re-seat σ, which would
make preparation the dominant term in the entire budget.

**⚠ What this session may NOT be used for:** §16.10.8's dilution-invariance measurement. It stays **OPEN**, and
the pooled archive figure `s = +0.033 ± 0.029` is **not** to be updated from these ten runs.
