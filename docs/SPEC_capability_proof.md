# SPEC — Capability Proof (the three-oil discrimination × dilution-invariance gate)

Status: **DESIGN — implement on explicit request only.** Milestone **V** (Viability / Validation). Raised by
Edwin 2026-07-19. This is the project's **go/no-go gate**, not a feature: it proves the core scientific claim
the whole product rests on. Everything downstream (calibrated verdict thresholds → LIMS push → field rollout →
Android) is justified **only if this passes**. That is why it must be done **fast** — further development of the
whole project depends on its outcome.

Builds directly on: [`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) (the peak-ratio metric +
§13 dilution/measurement model), [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) (intrinsic colour + §0
dilution physics), [`SPEC_capture_quality.md`](SPEC_capture_quality.md) (signal fidelity — already good enough to
trust colour), and [`SPEC_dev_measure_bench.md`](SPEC_dev_measure_bench.md) (the bench this all runs in).

---

## 0. Why this milestone exists

**Product goal (recap).** A *cheap DIY VIS spectrometer* + *convenient software* for the **pumpkin-oil mill
owner**. A second stakeholder is the **laboratory owner** who already has those mills as customers. The miller's
benefit is twofold: a **documentation tool** (measure in the field, submit to the lab) and the ability to **judge
whether the last press produced good oil**.

**Working purely in the VIS region** — we are bound to visible colour, i.e. the pigment bands and the perceived
colour of the oil. No UV, no NIR, no FTIR (those are the lab's tools, not the mill-floor tool).

**The gate.** Before investing further, prove that this cheap VIS instrument + pipeline can actually do the job:
tell the three practically-occurring oils apart, and do it in a way a mill floor can't accidentally break
(sloppy dilution). If the oils don't separate or the metrics aren't dilution-stable, we learn it **now**, cheaply,
on the dev bench — instead of after building the field/LIMS/Android stack on top of an unproven core.

---

## 1. The claim to be proven

**Three oils that occur in practice** (the roast axis, per
[`SPEC_measurement_evaluation_concept.md`](SPEC_measurement_evaluation_concept.md)):

| Class | Roast | Looks (human eye) |
|---|---|---|
| **too-green** | under-roasted | vivid green |
| **typical green** | good / target | classic Styrian green |
| **brown** | over-roasted | dark brown |

**Two sub-claims — both mandatory:**

1. **Dilution-invariance (within an oil).** The *same* oil measured at **two dilutions** — Edwin's *3 ml
   isopropanol + 2 drops* vs *3 ml isopropanol + 3 drops* — must yield **essentially the same metrics**. This is
   dilution-invariance *by concept* (§3): the metrics are built to cancel "how much oil is in the beam."
2. **Discrimination (between oils).** The three oils must yield **distinctly different metrics**.

**The human-eye anchor.** The three oils **look different to the naked eye**, so a VIS instrument that reproduces
what the eye sees *should* be able to separate them — the claim is physically plausible, not a moonshot. The
proof is to demonstrate the instrument does it **objectively and repeatably**.

**Acceptance — human judgment first (Edwin).** The first pass is **judged by inspection**: run the series, look
at the metric tables, and see whether within-oil metrics cluster while between-oil metrics separate. **No numeric
pass/fail thresholds are set yet** — those come later, from the data (this is exactly `SPEC_pumpkin_peak_ratio_eval.md`
P5 / §8 calibration). A quantitative separation criterion (e.g. within-oil spread ≪ between-oil spread) is an
*open question* for §9, to be pinned once the first series exists.

---

## 2. The metrics — and their evaluation-display order

Three metric families. **Display order in the EVALUATION step (Edwin):** the **peak-ratio metrics FIRST** (the
productive, quantitative verdict driver), then the **colour chips**, then **PCA LAST** (an optional bonus).

### 2.1 Peak-ratio — Soret/Q band ratio  *(PRIMARY — listed first)*

The three-axis absorption metric from `SPEC_pumpkin_peak_ratio_eval.md §3`: `D_Q` (green-pigment depth,
baseline-corrected), `browning = A_blue/A_green`, `clarity = A_green`, and the headline **greenness ratio
`G = D_Q / A_denom`**.

**Keep the old bands AND add the new literature bands (Edwin) — show BOTH:**

| Band set | Blue window | Q search | Status |
|---|---|---|---|
| **old (as-is)** | `BLUE_BAND=(450,490)` | `Q_SEARCH=(565,590)` | shipped; keep for now |
| **new (PB, literature-anchored)** | `(440,460)` — Soret right-hand slope | `(560,580)`, λ_Q 575→**570** | `SPEC_pumpkin_peak_ratio_eval.md §1b.1`; implement here |

Showing both `G_old` and `G_new` side-by-side lets us **see which band set separates the oils better** — the same
"see the effect" philosophy as the preprocessing bench (§4). The PB deltas + traps (esp. the `Q_BASELINE` lower
anchor 555→**550** clearance) are already fully specified in `SPEC_pumpkin_peak_ratio_eval.md §1b.1`/§11/§13.6-F4 —
this milestone just implements them; it does **not** re-derive them.

**Dilution behaviour.** `G` cancels the multiplicative `c·l` **exactly** (§3). The residual risk is the *additive*
offset `b` on the denominator (`A_green`, the smallest number in the chain) — §13/F5. → **baseline-correct the
denominator** (at least for the new ratios). The preprocessing bench (§4) is where we confirm this actually
tightens the within-oil cluster.

### 2.2 Intrinsic absorption colour  *(visual)*

`colorAbsorbed` and `colorIntrinsicPerceived` (the hue-complement that reads in the green-brown family) from
`SPEC_color_retrieval.md`. The **absorbance** colour is **dilution-invariant by construction** — chromaticity `xy`
drops luminance, so a pure scale `A→k·A` leaves the colour unchanged (§0 of that spec). The residual risk is again
the *additive* `b`, which shifts chromaticity → **baseline correction helps colour too**. Swatch S/L tuning in §5.

### 2.3 PCA consistency  *(OPTIONAL bonus — listed last, NOT required for the gate)*

**Not mandatory (Edwin).** The miller already knows they are milling pumpkin seed — so a "this is pumpkin oil"
readout is a **nice selling point**, not a metric the milestone hinges on. It sits **at the end of the list** and
the gate can pass without it.

**Scope = consistency / novelty, stated as two verdicts (Edwin's exact intent):**
- *"this is very probably pumpkin oil"* (sample sits inside the trained pumpkin-oil spectral cloud), and
- *"this cannot be pumpkin oil"* (sample is a clear outlier).

**⚠ Honesty boundary — NOT authentication.** A VIS spectrum **cannot authenticate** pumpkin oil: green
tetrapyrroles (protochlorophyll/protopheophytin) are **not unique to *Cucurbita*** — olive, hemp and other green
oils carry chlorophyll/pheophytin too (`SPEC_pumpkin_peak_ratio_eval.md §13.8`, Fruhwirth 2007, Balbino 2022). So
PCA says *"consistent with / an outlier of the pumpkin class we trained on"* — a **quality-of-fit / novelty**
statement — never *"authentic pumpkin, not adulterated."* The wording above ("very probably" / "cannot be") is
deliberately probabilistic, not a purity claim. **Preprocess with SNV before PCA** (§3/§4) so the cloud is about
spectral *shape*, not dilution.

### 2.4 The three-oil separation itself — a simple metric-space distance judge

**No LDA / no supervised classifier (Edwin: "forget LDA — many have tried this and all failed";** the 2021
`tests/lda3.py`/`lda4.py` prototypes are that abandoned path). The three-oil call is made by a **simple distance
in metric space** — the oils are represented by their (peak-ratio, colour) metric vector, and "which class" is
"nearest cluster." Transparent, debuggable, and it degrades gracefully with n=3 classes and few samples, where a
trained discriminant would overfit. PCA (§2.3) is a *separate*, optional "is it pumpkin at all" gate, **not** the
class separator.

---

## 3. The spine — dilution-invariance IS the preprocessing problem

Diluting an oil does **exactly two things** to the absorbance spectrum (`SPEC_color_retrieval.md §0`,
`SPEC_pumpkin_peak_ratio_eval.md §13`):

```
A_meas(λ) = ε(λ)·c·l   +   b
            └── SCALE ──┘   └ OFFSET ┘
  c·l   multiplicative — how much oil × path      (dilution changes this directly)
  b     additive — glass mismatch, scatter, lamp drift between R and S, exposure change
```

A **ratio** and a **chromaticity** both cancel the *multiplicative* term; **neither cancels the additive `b`**.
That is the whole game — and it is exactly what the preprocessing steps are for:

| Metric | Cancels scale `c·l`? | Cancels offset `b`? | What closes the gap |
|---|---|---|---|
| **peak-ratio `G`** | ✅ ratio | ⚠️ numerator yes (`D_Q` baseline-corrected), **denominator no** | baseline-correct `A_denom` |
| **intrinsic colour** | ✅ chromaticity | ⚠️ **no** — `b` shifts `xy` | baseline correction |
| **PCA cloud** | depends | depends | **SNV** (removes both) |

**All three converge on the same recipe:** `baseline-correct → (optionally) SNV → smooth`. So the "experimental
preprocessing concept" you asked for is **not a side-quest — it is the machinery that earns dilution-invariance.**
That is the spine of this spec.

**Note — the steps overlap, which is the point.** SNV subtracts each spectrum's own mean (kills a *flat* `b`) and
divides by its std (kills scale); morphological baseline removal kills a *sloping/curved* baseline; smoothing kills
noise. For a purely flat `b`, SNV's mean-subtraction alone suffices; a curved background needs the baseline step.
**We don't know which the rig actually has** — so we *measure it* (§4). And preprocessing may end up **per-metric**
(colour may want baseline-only, peak-ratio and PCA may want full SNV) — an §9 open question the bench answers.

---

## 4. The experimental preprocessing bench — the "eureka machine"

**Goal (Edwin's words):** be able to judge the effect of each step — *"a possible eureka moment saying 'yes,
baseline correction did make it better indeed.'"* Not a fixed pipeline: a **comparison harness** that computes the
metrics **with and without** each preprocessing step and shows them **side by side**, so the effect on
within-oil clustering / between-oil separation is *visible*.

### 4.1 What exists vs what is new (from the 2026-07-19 pipeline scan)

| Step | Module | Status |
|---|---|---|
| **Smoothing** | `SmoothSpectrumLogicModule` — Savitzky-Golay (`savgol_filter`), defaults passes=7/window=10/polyorder=3 | ✅ exists, **wired into nothing** |
| **Baseline removal** | `RemoveBaselineLogicModule` — morphological opening (min→max filter), ~10%-width window | ✅ exists, **unused** |
| **Normalize** | `NormalizeSpectrumLogicModule` — **max-normalization only** | ✅ exists, not what we need |
| **SNV** | — | ❌ **does not exist — build it** (per-spectrum: subtract mean, divide by std; tiny) |
| default T/A path | `MeanOp→TransmissionOp→AbsorptionOp` | **no smoothing, no baseline** — only robust frame-reduction + transmission floor mask |

The `SpectrumUtil` façade already exposes the ops as **discrete, composable steps** (`mean → smooth → removeBaseline
→ rebin → normalize`) — so adding SNV as a sixth op and driving a **toggleable chain** is natural. **Light smoothing
only** for the peak-ratio path — never the default 7-pass smoother, which would erode the weak `D_Q` band
(`SPEC_pumpkin_peak_ratio_eval.md §12/R4`).

### 4.2 The comparison harness (the actual deliverable)

For a captured oil, the bench computes the metric set under a small matrix of preprocessing combinations and
renders them together, e.g.:

```
                       G_new    D_Q     A_green   colorIntrinsic(hue)   ...
  raw (no preproc)      …        …        …          …
  + baseline            …        …        …          …
  + SNV                 …        …        …          …
  + baseline + smooth   …        …        …          …
```

Then, across the two dilutions of one oil (§7 Run 1), the *within-oil spread* of each row is what tells you a
step helped — the row whose numbers barely move between dilutions is the winning preprocessing. **That table is
the eureka moment.** (Rendered on the bench; no persistence required for the first pass — same render-only stance
as the peak-ratio first sweep.)

---

## 5. Colour-swatch S/L tuning  *(cosmetic — aids comparison)*

Purely to make the three oils' chips **maximally eye-distinguishable** when comparing them on screen / in the PDF.
Today the normalized chips are pinned **S=80, L=50** (hard-coded in `DevSpectralPlugin.__chip`; achromatic guard
`ACHROMATIC_CHROMA=8.0` in `EvaluationColorUtil`). This milestone **re-tunes S/L** (a knob turn, not new
machinery) so green↔brown pops for side-by-side reading — and possibly picks a slightly different S/L than 80/50
if that separates the three oils better to the eye. Cosmetic, but it genuinely helps testing and viewing results.
Document the chosen values; the underlying colour numbers (H/S/L fields) are unchanged.

---

## 6. Dev-plugin deltas  *(scope = the DEV plugin only, Edwin)*

The wizard / end-user host is **left untouched** until the proof passes; all of this lands in `DevSpectralPlugin`
+ the bench. Summary of touches (details in the referenced specs):

- **PB bands (§2.1):** add the new `(440,460)` / `(560,580)` band set alongside the old; move λ_Q 575→570 and the
  `Q_BASELINE` lower anchor 555→550 for the new set (`SPEC_pumpkin_peak_ratio_eval.md §1b.1`). Emit both `G_old`
  and `G_new`.
- **Preprocessing hooks (§4):** new `SnvSpectrumLogicModule` + `SpectrumUtil.snv(...)`; a bench comparison harness
  that runs the metric set under the preprocessing matrix.
- **Evaluation reorder (§2):** peak-ratio metrics **first**, colour chips next, PCA (if built) **last**.
- **Swatch S/L (§5):** re-tune the normalized-chip constants.
- **Protocol note:** support both the two-pot and one-pot capture flows (§7) — for the dev bench this is a
  measurement-procedure choice, not necessarily code.

---

## 7. Lab instructions — the staged measurement protocol  *(NEW, Edwin)*

A **repeatable bench procedure**, ordered so the *first* run is the one that makes sense first.

### 7.0 The lab diary — and its first entry  *(Edwin)*

Two distinct artifacts, don't conflate them:
- **Lab *instructions*** (this §7) = the **protocol** — *how* to run a measurement.
- **Lab *diary*** = a **dated running log** of what was actually run and what was observed — one **entry** per
  experiment. It is the evidence trail the whole go/no-go decision is read from. Suggested home:
  `spectracs-docs/LAB_DIARY_capability_proof.md` (scaffold on request), each entry: *date · setup (A/B) · oil ·
  dilution · preprocessing on/off · the metric table · what was seen*.

**Entry 0 — the first experiment, and likely the first implementation task (Edwin):** the *smallest* useful
slice — **one oil, ONE dilution, corrections ON vs OFF, restricted to the COLOUR values only.**
- Not a dilution test yet (one dilution can't show invariance) and not the peak-ratio or PCA — deliberately
  narrow. Its job is to stand up the **with-vs-without-corrections comparison end-to-end on the most
  human-readable output** (the intrinsic-colour swatch + H/S/L), on a single captured sample.
- What it answers: *does baseline / SNV / smooth actually move the colour, and toward what?* — the first, cheapest
  "eureka" read (§4), and the walking skeleton for everything after it.
- Because it is one metric family on one sample, it is the natural **first thing to build** (a colour-only cut of
  the §4.2 comparison harness) before the harness grows to all metrics and the multi-run series below.

### 7.0.1 Entry 0 — the improved-colour lab use case (calculation + display)  *(Edwin)*

Realized concretely, not as an abstract toggle: the plugin renders the **corrected** absorption and two **corrected
colour chips beside the raw ones**, so raw-vs-improved sit side by side for the eyeball read. **`DevSpectralPlugin`
drives all of it**; the end-user host is untouched.

**The correction (SETTLED, Edwin 2026-07-20): flat-offset baseline + light Savitzky-Golay. No SNV.** Grounded in
the literature (§10.1): the additive `b` is best removed by the *lowest-order* correction that fixes it — a
**constant-offset subtraction** (subtract `A` at a signal-free/transparent window so it reads zero) preserves the
band amplitudes the colour depends on, whereas SNV/MSC (built for turbid samples) would smear exactly those. A
**light** SG (polyorder 2–3, window ≤ the narrowest peak's FWHM) denoises without eroding the Q-band, applied
**after** the baseline (§10.1).

**How it's calculated** (one new derived spectrum, a pure helper `__improvedAbsorption(a)` called by both hooks):

```
frames ─► Mean ─► {REFERENCE, SAMPLE}
                    ├─► Transmission ─► T(λ)        ─► colorPerceived*   (offset-invariant — NO twin needed)
                    └─► Absorption   ─► A_raw(λ)
                             ├─(existing)─► spectrumToHsl(srgb) ─► colorAbsorbed, colorIntrinsicPerceived (+180°)
                             └─► CORRECT ─► A_improved(λ)      ◄── flat-offset subtract, then light SG
                                     └─► spectrumToHsl(srgb) ─► colorAbsorbedImproved,
                                                                colorIntrinsicPerceivedImproved (+180°)
```

**Why only the two absorbance chips get an Improved twin:** an additive `b` on `A` is a *uniform scale* on `T`
(chromaticity unchanged) but a chromaticity *shift* on the absorbance colour — so `colorPerceived` needs no twin;
`colorAbsorbed` / `colorIntrinsicPerceived` are exactly the offset-sensitive two.

**How it's displayed.** A new PROCESSING tab overlays raw vs improved (reuse `SpectrumPlotView().addTrace()`):

```
[ Spectra ] [ Transmission ] [ Absorption ] [ Absorption (improved) ]   ◄── NEW tab (raw ╌╌ vs improved ──)
```

The two Improved chips sit **directly under their raw counterparts** in the EVALUATION colour group:

```
 Intrinsic (perceived-family)            [chip]   H  39   S 80   L 50
 Intrinsic (perceived-family) · improved [chip]   H  44   S 80   L 50    ◄── colorIntrinsicPerceivedImproved
 Intrinsic (absorbed)                    [chip]   H 219   S 62   L 41
 Intrinsic (absorbed) · improved         [chip]   H 231   S 71   L 45    ◄── colorAbsorbedImproved
 Perceived                               [chip]   H  71   …               (unchanged — no twin)
```

**Impl surface (minimal, plugin-local):** new `__improvedAbsorption(a)` helper (flat-offset + light SG); declare
the "Absorption (improved)" overlay in `processing()`; one extra `spectrumToHsl` → two extra `__chip` rows in
`evaluation()`. `EvaluationColorUtil` / `__chip` / `MetricFieldView` / `SpectrumPlotView` **reused as-is**. The
correction reaches the plugin through a small **`plugin_sdk`** exposure (keeps the plugin `plugin_sdk`-only, like
`MeanOp`) — either a thin `baselineOffset` util or `SpectrumUtil.baselineOffset()` wrapped in `plugin_sdk`.
**Open knob:** the transparent-window anchor for the offset (min over the green window vs the analysis-window
min) — decide on first data. **Caveat:** the flat-offset removes only a *flat* `b`; if the rig's `b` is sloping
(scatter/RI), a 1st-derivative or a large-window baseline is the fallback (§10.1) — the bench will reveal it.

> **Common-mode caveat (see §10.4):** the camera-linearity nonlinearity is present in BOTH the raw and improved
> paths, so Entry 0 stays valid as a *relative* comparison (the confounder cancels in the with-vs-without read);
> only *absolute* colour claims inherit the linearity caveat.

### 7.1 Two setups, in order

| Setup | Cells | Purpose | When |
|---|---|---|---|
| **A — two-pot** | pot A = blank (3 ml isopropanol) as REFERENCE; pot B = alcohol + oil as SAMPLE | **quick look** — hope it already separates the oils reasonably | first, because it is the current bench flow |
| **B — one-pot** | one pot: capture R (3 ml alcohol) → add drops, stir → capture S | **transferable** — identical glass in R and S ⇒ `b_glass = 0`; matches the one-pot end user | after A, for the trustworthy numbers |

Setup A carries a glass-mismatch offset `b_glass` that will **not** transfer to the one-pot field user
(`SPEC_pumpkin_peak_ratio_eval.md §13.4`). It is fine for a *quick* "does anything separate" read; Setup B is the
one any threshold work must use. Running A then B also **directly demonstrates** whether `b_glass` matters (does
the separation survive the switch?).

### 7.2 Run sequence

0. **Run 0 / Entry 0 — colour, corrections on vs off, ONE oil × ONE dilution (§7.0).** The first diary entry and
   first build target: capture one oil at one dilution, render the **colour chips only**, side-by-side **with and
   without** each correction. **Observation to record:** whether/how the corrections shift the colour. No
   invariance claim yet — this is the skeleton.
1. **Run 1 — dilution-invariance, ONE oil (Edwin).** Take **one** oil (start with the
   *typical green*) and measure it at the two dilutions: **2 drops** and **3 drops** in 3 ml isopropanol. Compare
   the metric tables (§4.2) across the two dilutions. **Expectation to confirm:** the metrics barely move.
   *This is the run that validates the whole "dilution-invariant by concept" premise before anything else.*
2. **Run 2 — three-oil discrimination.** Measure all three oils (too-green / typical / brown), each at a fixed
   dilution. **Expectation:** the metric vectors land in three visibly separated clusters (§2.4).
3. **Run 3 (recommended) — repeatability.** Measure one oil **~5×** (re-prep each time). Field-readiness is
   "does it give the same answer twice" (`SPEC_pumpkin_peak_ratio_eval.md §13.8 gap 2`); this is cheap and worth
   knowing before any threshold. Also yields the **noise floor** to compare against `D_Q` (the metric's real SNR).

### 7.3 Per-capture procedure (one-pot, Setup B)

```
3 ml isopropanol into the pot  →  place, capture REFERENCE
→  add N drops of oil, stir ~20 s until visibly clear  →  capture SAMPLE
→  bench computes T = S/R, A = −log10(S/R), then the preprocessing matrix + metrics (§4.2)
```

Sloppy drop-counting is fine — the ratio cancels *how much* oil (§3). Effort belongs on **dissolving cleanly**
(clear, not cloudy), because turbidity is additive and does **not** cancel.

---

## 8. Implementation phases  *(DESIGN — implement on explicit request only)*

```
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| Ph | What                                      | New / Touched                    | Gate (drive-and-observe)            | Risk    |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V1 | SNV op + wire the unused smooth/baseline   | NEW SnvSpectrumLogicModule (+     | On a captured A(λ): snv/baseline/   | LOW     |
|    | into SpectrumUtil as composable steps      | Params/Result); TOUCH SpectrumUtil| smooth each produce a sane spectrum;|         |
|    |                                            | (add snv())                      | façade order documented.            |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V2a| ** FIRST IMPL TASK / Diary Entry 0 (§7.0)**| TOUCH DevSpectralPlugin.evaluation| One oil, one dilution: colour chips  | LOW-MED |
|    | COLOUR ONLY, corrections ON vs OFF, one    | + DevMeasurementBenchViewModule   | shown WITH vs WITHOUT each correction|         |
|    | oil x one dilution. The walking skeleton.  | (colour-only comparison strip)   | side by side; the shift is visible.  |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V2 | Grow it to the full preprocessing x metric | TOUCH DevSpectralPlugin.evaluation| Bench shows the preproc x metric    | MED     |
|    | comparison harness (the eureka table):     | + DevMeasurementBenchViewModule   | matrix; numbers change as steps     | (the    |
|    | ALL metrics WITH/WITHOUT each step. RENDER. | (render the matrix)              | toggle; within-oil spread readable. | core)   |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V3 | PB new bands ALONGSIDE the old; emit G_old  | TOUCH DevSpectralPlugin (add new  | Eval shows G_old and G_new; D_Q     | LOW     |
|    | AND G_new (§2.1). Q_BASELINE 555->550 chk. | band consts; λ_Q 570; anchor 550)| still found on capture001. §1b.1    |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V4 | Evaluation reorder: ratio FIRST, colour,   | TOUCH DevSpectralPlugin.evaluation| Metric list order = ratio, colour,  | LOW     |
|    | PCA last                                   | (step ordering)                  | (pca). Matches §2.                  |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V5 | Swatch S/L re-tune for eye separation      | TOUCH DevSpectralPlugin.__chip    | Three oils' chips visibly distinct; | LOW     |
|    |                                            | (S/L consts)                     | H/S/L fields unchanged.             |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V6 | Lab-protocol doc + RUN the series (Run 1 -> | measurement (this doc §7); maybe  | Run 1: within-oil metrics cluster;  | MED     |
|    | Run 2 -> Run 3). Human-judged separation.  | a capture-set folder             | Run 2: three oils separate (eye).   |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V7 | OPTIONAL: simple metric-space distance     | NEW small distance judge          | Nearest-cluster call for a sample;  | LOW     |
|    | judge for the three-oil call (§2.4)        | (no sklearn classifier)          | transparent distances shown.        |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V8 | OPTIONAL BONUS: PCA consistency ("very     | NEW PCA-on-SNV consistency score  | Outlier/inlier score + the two-     | MED     |
|    | probably / cannot be pumpkin oil"), LAST   | (sklearn PCA, desktop)           | verdict wording; caveat shown.      |         |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
Order: V1 -> V2a (the FIRST task = colour-only skeleton / Diary Entry 0) -> V2 (grow to all metrics); V3/V4/V5
are independent dev-plugin touches (any order after V1); V6 needs V2-V5; V7/V8 optional, after V6 data exists.
PCA (V8) is a bonus and NOT required to pass the gate.
```

**The gate passes when:** Run 1 shows within-oil metrics essentially stable across the two dilutions, and Run 2
shows the three oils in visibly separated metric clusters — **judged by inspection** (§1). Numeric thresholds and
the calibrated verdict edges are the *next* milestone (peak-ratio P5), not this one.

> **✅ PREREQUISITE DONE (Edwin 2026-07-20, rig-verified):** the **radiometric intensity
> reduction** `qGray → max-channel` (`SPEC_capture_quality.md §15`, G1–G6). Every metric here reads that reduction; the
> current `qGray` suppresses blue ~3×, forcing heavy dilution. It doesn't *bias* the metrics (it cancels in `T/A`)
> but it caps blue fidelity/headroom — so it lands **before** the V phases.

---

## 9. Open questions / caveats

- **Per-metric preprocessing (§3).** SETTLED for **colour**: flat-offset + light SG, **no SNV** (§7.0.1, §10.1).
  Still open for the ratio/PCA path — §10.1's caution ("SNV is for turbid samples, can smear band ratios") now
  makes even the PCA-SNV of §2.3/§3 questionable; the comparison bench (§4) decides, don't hard-pick before data.
- **Flat vs sloping `b`.** The flat-offset removes only a *flat* offset; a sloping/curved `b` (scatter, RI) needs a
  1st-derivative or a large-window baseline. Which the rig has is unknown → measure (`SPEC_pumpkin_peak_ratio_eval.md
  §13.5` blank-vs-blank test P + noise-floor test). Note RI mismatch (§10.3/C3) is a real source of a sloping `b`.
- **How strict is "essentially the same"?** A quantitative separation criterion (within-oil spread ≪ between-oil
  spread) is deferred to the first data (§1) — human inspection first.
- **`b_glass` transfer.** Setup A (two-pot) numbers won't transfer to the one-pot field user; only Setup B does.
  Any later threshold work uses Setup B.
- **PCA training set size.** A consistency cloud needs enough real pumpkin spectra to be meaningful; with n=few it
  is illustrative, not statistical. Keep the "very probably / cannot be" wording honest to the sample size.
- **Smoothing erosion.** Keep smoothing light on the peak-ratio path (weak `D_Q`); the comparison bench will show
  if even light smoothing hurts.

## 10. Literature basis & camera/optical confounders  *(web research, 2026-07-20)*

Grounds the preprocessing decision and records the confounders a consumer-camera VIS photometer faces. Kept here
as the decision's evidence trail; **this argumentation is a candidate for user-facing documentation later** (Edwin).
Confidence is flagged: **[consensus]** = textbook/review; **[single-paper]**; **[inference]** = reasoned, no direct source.

### 10.1 Why flat-offset + light smoothing, and NOT SNV — grounded

- **Flat-offset = "baseline offset correction,"** the 0th-order rung of the baseline ladder (*offset → linear
  detrend → polynomial → rubber-band → AsLS/airPLS*). The governing rule: **use the lowest-order correction that
  fixes the actual artifact** — higher-order/iterative fits risk over/undershoot that *distorts recovered peaks*,
  which a constant subtraction cannot. **[consensus]** — Rinnan, Van den Berg & Engelsen 2009 (*TrAC* 28(10), the
  canonical preprocessing review); Eigenvector chemometrics wiki. A 1st derivative also removes a constant offset
  (2nd removes a linear one) but amplifies noise. **[consensus]** — Spectroscopy Europe, *Back to basics: derivatives*.
- **SNV/MSC are the wrong tool here.** Built to remove *multiplicative scatter* in **turbid/particulate** samples
  (Barnes, Dhanoa & Lister 1989); a **clear** solution has little such scatter, and SNV rescales each spectrum by
  its own std and can **smear relative band amplitudes** — exactly the quantity chromaticity depends on. So SNV
  ahead of a colour step is inappropriate. **[inference, grounded in Barnes 1989 + Rinnan 2009; T. Davies column]**
- **Light Savitzky-Golay:** polyorder 2–3, **window ≤ the narrowest peak's FWHM**; the clean order is
  **baseline → then smooth** (order-of-ops is contested, but this is the defensible convention). **[consensus /
  single-review]** — Savitzky & Golay 1964; Yan 2025 review (PMC12221524).
- **Practitioner order for a camera photometer:** `dark-subtract → linearize → (flat-field) → S/R → A=−log10 →
  baseline-offset → smooth`. Linearize + dark-subtract must precede the ratio; baseline + smooth come after. **[inference from §10.1/§10.3]**

### 10.2 What the literature VALIDATES in our existing design

- Pumpkin pigments are **protochlorophyll/protopheophytin** (the "proto" precursors, **not** ordinary
  chlorophyll) → olive-oil 670 nm constants don't transfer → **self-calibrate the bands** (our stance).
  **[authoritative]** — Fruhwirth & Hermetter 2008 (*Eur. J. Lipid Sci. Technol.* 110:637).
- The chlorophyll **~670 nm Q-band is just outside 430–650** → confirms the two-band optics constraint
  (`SPEC_pumpkin_peak_ratio_eval.md §2`); in-band proxies = Soret flank 430–470, carotenoid 430–490, pheophytin
  Qx 505–606 — our (440–460)/(560–580) sit in these. **[consensus + inference]**
- **`D_Q` (peak minus a two-point linear baseline) = the IUPAC/Pokorný pheophytin method** — textbook, not invented.
  **[consensus method]** — IUPAC PAC 67(10):1781 (1995).
- **Oil colour via CIELAB from VIS transmission** is established (positioned to replace Lovibond); compute in
  **XYZ/Lab, sRGB only for display** — matches our K-series converter split. **[consensus]** — Brühl 2021.
- DIY practice: **lock exposure/gain/WB at 6500 K**, read **grayscale along dispersion** — matches our
  `DevCaptureVideoThread` 6500 K + qGray. **[community + peer-reviewed consensus]** — Public Lab; Ju et al. HardwareX 2021.

### 10.3 Camera & optical confounders (ranked) — standard fix + our state

| # | Confounder | Standard fix | Our state |
|---|---|---|---|
| **C1** | **Sensor nonlinearity / sRGB gamma** — `A=−log10(S/R)` needs LINEAR intensity; consumer cameras gamma-encode | shoot RAW or invert the camera response (a fixed γ=2.2 is not enough) | **NOT handled** — see §10.4. **Postponed.** |
| **C2** | **Dark current / black-level** — additive, does NOT cancel in −log10(S/R); worst at high A | dark-frame subtract S & R before the ratio, matched temp | **NOT handled** — no dark-frame in the path. Postponed. |
| **C3** | **Refractive-index mismatch** (oil-in-IPA vs IPA blank) — a *physical source* of our additive `b` | one-pot / matched cell minimizes it at source | ties to §7.1 Setup B / `…§13.4` one-pot |
| **C4** | **Stray light / 2nd-order diffraction** — blue/UV lands near 2×λ, contaminates the red end; caps max A | order-sorting / long-pass filter | hardware — noted |
| **C5** | **8-bit ceiling + stray light** cap max measurable A | higher bit depth / RAW; dilute to stay off floors | 8-bit qGray today; dilution control |
| **C6** | **ROI/geometry drift** breaks PRNU/vignetting cancellation in S/R | rigid optics, re-reference often | one-pot + per-sample R help |
| **C7** | **sRGB gamut clipping** distorts colour of deeply-coloured oils | compute in XYZ/Lab, convert sRGB for display only | already done (K-series) |
| **C8** | **`qGray` luminance reduction suppresses blue ~3×** (weights blue 5/32) — not radiometric | max-channel reduction | ✅ **IMPLEMENTED + RIG-VERIFIED** (`SPEC_capture_quality.md §15`, G1–G6) — the **prerequisite**, done ahead of V (not postponed like C1/C2) |

*Caveats on sourcing (agent): the SNV-before-colour and proxy-band conclusions are reasoned inferences, not single
quotable sentences; a few pigment constants are secondary — verify before hard-coding.*

### 10.4 As-is camera-linearity state — CODE-CHECKED 2026-07-20, **POSTPONED**

Inspected the capture→`S/R` path to bank the state (Edwin — check, don't fix). **Finding:** the spectrum intensity
is the **8-bit `qGray`** of the camera frame (saturated channels masked first; some paths use per-channel
`max(r,g,b)` for ROI/auto-exposure). **There is NO gamma linearization, NO inverse camera-response, and NO
dark-frame subtraction** anywhere before `T=S/R` / `A=−log10(S/R)`. The only `gamma` in the tree
(`SpectralColorUtil`, 0.80) is *display* wavelength→RGB rendering — unrelated. Robust reduction
(Tukey/sigma-clip/dim-frame) + the transmission floor are statistical conditioning, not photometric linearization.

⇒ **C1 and C2 are unaddressed by design today** — `A` is formed from gamma-encoded 8-bit values. **Decision
(Edwin 2026-07-20): POSTPONED** — recorded as state, not a task. When picked up it belongs in
[`SPEC_capture_quality.md`](SPEC_capture_quality.md). Entry 0 remains valid meanwhile because the nonlinearity is
**common-mode** across the raw/improved comparison (§7.0.1 caveat).

## 11. Cross-references

- [`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) — the peak-ratio metric (§3), the PB bands
  (§1b), and the dilution/measurement model + `b`/one-pot analysis (§13). This milestone implements PB and acts on §13.
- [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) — the intrinsic-colour metric + §0 dilution physics + the
  five chips + swatch S/L.
- [`SPEC_capture_quality.md`](SPEC_capture_quality.md) — signal fidelity (the reason colour is now trustworthy).
- [`SPEC_dev_measure_bench.md`](SPEC_dev_measure_bench.md) — the bench host these deltas land in.
- `tests/lda3.py` / `tests/lda4.py` (workspace root, 2021) — the abandoned LDA prototypes; retained as the record
  of why §2.4 uses a simple distance judge, not a supervised classifier.
```
