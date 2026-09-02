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

## Current state — executive summary *(2026-07-24)*

*A scannable snapshot of where the gate stands. Detail + provenance in §11; scope narrowing in §1a.*

### In one line
The go/no-go gate: prove a cheap DIY VIS spectrometer + this pipeline can **detect over-roasting** — flag a
**good green** oil vs a **browned / over-roasted** one — *and* do it so a sloppy mill floor (loose dilution)
can't break it. Everything downstream (LIMS, field, Android) is justified only if this holds.

### The claim — two mandatory sub-claims

| # | Sub-claim | Meaning | Status |
|---|---|---|:--:|
| 1 | **Dilution-invariance** | same oil at 2 vs 3 drops → same number | ✅ proven |
| 2 | **Discrimination** | good-green vs over-roasted-brown → clearly different numbers | ✅ proven |

⭐⭐ **2026-08-18 — THE MEASUREMENT THE GATE WAS ARGUED ON HAS BEEN REPLACED, AND IT MOVES THE VERDICT FROM
"proven on averages" TO "one fill decides".** Under the settled protocol
(`SPEC_settled_measurement.md` §27/§28) five separate preparations of one oil scatter by **σ = 0.276**,
against the archive's pooled within-fill **1.255**. On the shipped `Q%` scale, brown's margin to `T` is
1.843:

| protocol | that margin | a SINGLE measurement classifies correctly |
|---|---|---|
| the archive's scatter (1.255) | 1.5 σ | 92.9 % brown · 98.3 % green · **91.3 % both** |
| ⭐ series F (0.276), **if brown matches green** | **6.7 σ** | **~100 % both** |

⇒ the gate's claim stops being *"the class means differ"* and becomes *"one fill decides the class"*, which
is the form a product needs. ⛔ **Conditional, and the condition is scheduled**: those class means come from
the OLD protocol and brown's σ has never been measured under the new one — ROADMAP item 2 (series E: six
fills of one brown stock) is exactly that measurement, and ROADMAP item 1 (§29's read fix) must land first
because a +0.48 one-directional bias is 37 % of brown's margin.

**Scope narrowed (§1a):** the old "too-green" third class and the "which green is better" ranking are **dropped**
— that is a matter of taste, not the miller's need. Brown is *not* a matter of taste (tastes worse, sells
cheaper). Goal = a **binary over-roast warning**, not a three-way roast scale.

### The metric that carries it

| Metric | Role | Result |
|---|---|---|
| **Pigment ratio (Soret/Q, 440–460 / 560–580)** | primary verdict driver | **the winner** |
| Colour chroma (distance from white) | corroborating | Δ/noise ≈ 6.5, dilution-invariant |
| PCA "is it pumpkin at all" | optional bonus, **not** authentication | out of gate |

Class call = **simple nearest-cluster distance**, not a trained classifier (§2.4).

> ⚠ **The first row's name is wrong.** The metric is not a two-band ratio — a **third pigment-bearing region at
> 600–630 nm** enters through the baseline slope and carries a large share of the discrimination. **See the
> restatement in §2.1a** *(2026-07-31)*. The results are unaffected; the description was.

### The evidence

| Claim | Green (good) | Brown (over-roasted) | Separation | ✓ |
|---|:--:|:--:|:--:|:--:|
| Pigment ratio, all 32 runs | 3.75 ± 0.13 | 2.47 ± 0.11 | **Δ/noise ≈ 10.8, non-overlapping** | ✅ |
| Pigment ratio, K/L/M/N | 3.83 ± 0.13 | 2.41 ± 0.08 | Δ/noise ≈ 13.5 | ✅ |
| Dilution-invariance (2↔3 drops) | 3.3 % | 5.4 % | ≪ 1.4 between-oil gap | ✅ |
| Colour (chroma) | 0.234 | 0.198 | Δ/noise ≈ 6.5 | ✅ |
| Threshold | — | — | **Ampel zone at 2.8 exists** | ✅ |

Cluster gap: **worst green 3.67 > best brown 2.59** — a clean, empty separation.

### Proven vs open

| Aspect | State |
|---|---|
| Dilution-invariant good/brown discrimination | ✅ **Proven, not marginal** (10–13× noise) |
| Physics understood (settling, matched/mismatched bands) | ⚠ **PARTLY — 2026-07-31.** §11.4c's sign is ✅ **vindicated** (§2.1a: signs agree; the 11 h/30 min conflict is a **non-monotonic settling curve**, and §11.4a's +24.3 % reproduced to +24.25 %). But §11.5 is still **silent on the third region** the metric actually uses (§2.1a) |
| Freshness-protocol repeatability (green ×5) | ✅ Validated (§11.4a) |
| Verdict threshold | ✅ Exists (Ampel 2.8) |
| Miller-facing verdict in-app | ✅ **Implemented** — the Roast Ampel gauge shows an easy green/brown read, not raw numbers ([`SPEC_roast_ampel.md`](SPEC_roast_ampel.md) §8) |
| Sample preparation | ✅ **Easy** — a few drops of oil in isopropanol + a swirl; no lab skills |
| Broaden panel: +1 brown, +4 green | ⏳ **The one open item — confirmatory** (§11.6) |
| Brown ×5 fresh runs | ⏳ In progress (2 done; age-robust as predicted) |
| Metric description matches the metric | ✅ **Settled 2026-08-03** — text fixed 2026-07-31 (§2.1a), and the covert-vs-explicit decision below was then answered by moving the anchor to **620–630 nm**, where it sits *on* protochlorophyll's Qy band and is declared in `declaredEvalBands()` — i.e. option **(a)**, arrived at by relocating the band rather than renaming it (`SPEC_capture_quality.md` §16.20) |
| Linear baseline earns its place | ✅ **Measured 2026-07-31** (§2.1a) — halves BOTH error terms: dilution 5.49 → 2.75 %, settling 11.90 → 6.20 % |
| ~~Third too-green oil~~ | ⛔ Retired — out of scope (§1a) |
| ~~Amber-band sample~~ | ⛔ Retired — no intermediate oils in practice (§1a) |

> ### ⚠ UPDATE 2026-07-27 — the table above is the **2023-oil** picture and does NOT hold on the 2026 oils
>
> A full day of instrument work ([`SPEC_capture_quality.md`](SPEC_capture_quality.md) §16.7–§16.10, 25 runs)
> changed three of these rows. Recorded here because the summary above would otherwise read as settled.
>
> | row above | 2026 reality |
> |---|---|
> | *Dilution-invariant discrimination ✅ proven (10–13× noise)* | **UNRESOLVED on the 2026 oils** (§16.10.8). Not refuted — **unmeasurable**: seating noise alone produces a 1.34× metric spread, as large as a deliberate 2.19× dilution change, so the dilution term is buried. The 2023 evidence stands for the 2023 oils; it does not transfer. |
> | *Verdict threshold ✅ exists (Ampel 2.8)* | 2.8 → **4.4** (2026-07-25 recalibration), plus a **second** gauge at **10.3** on the linear-baseline metric ([`SPEC_roast_ampel.md`](SPEC_roast_ampel.md) §2a). Both provisional. ⛔ **BOTH SUPERSEDED 2026-08-03** — see the note below. |
>
> ⛔ **THRESHOLDS SUPERSEDED 2026-08-03 (`SPEC_roast_ampel.md` §2b, `SPEC_capture_quality.md` §16.20.7).** The
> plugin now shows **three** verdicts on the **620–630 nm** far anchor: `baseline + pedestal` at `T` = 10.6,
> `baseline` at `T` = 12.5, and the **raw Soret/Q as a VALUE WITH NO VERDICT**. The raw gauge was retired
> because on post-rebuild data its classes **overlap** (Cohen's *d* 1.20) — and ⚠ its shipped `T` = 4.4 sat
> **below the entire brown class**, so the PUBLISHING badge reported brown oil as "good — green" on every run.
> | *Proven, not marginal (10–13× noise)* | On the 2026 oils the raw Soret/Q ratio gives **d = 1.24 and the classes OVERLAP** — 9/25 wrong under leave-one-fill-out. The margin that made 2023 look easy is largely absent here. |
>
> **What rescued the gate is a metric change, not new hardware.** The linear-baseline pigment ratio
> (§16.10.9, implemented) separates all 25 runs of 2026-07-27 — **1/25** under leave-one-fill-out vs S/Q's 9/25,
> *d* 2.88 vs 1.24 — and costs nothing on the 2023 set (*d* 10.27 vs 10.39). Two green runs that the old gauge
> called brown are now correct.
>
> **What is now the gate's real blocker:** the jar's re-seating, ~**98 %** of instrument variance (§16.7.2n).
> It is not merely costing margin — it **prevents the dilution-invariance experiment from being run at all**,
> and dilution invariance is one of the two mandatory sub-claims in §1. The cheapest next step is not hardware:
> §16.9.4a's **no-re-seat control** (syringe-fill in place, zero parts) both tests the mechanism and yields a
> clean dilution series.
>
> **Revised honest read:** the *binary discrimination* claim is in better shape than this morning (a metric that
> separates 25/25 in-sample, 24/25 honestly). The *dilution-invariance* sub-claim is **not** currently
> demonstrated on the oils that matter, and cannot be until the seat is fixed. **GO on discrimination, HOLD on
> dilution invariance.**

> ### ⭐ UPDATE 2026-07-30 — the seat WAS fixed, and the blocker moved
>
> Edwin rebuilt the jar holder, cone seat and camera mount and re-measured
> ([`SPEC_capture_quality.md`](SPEC_capture_quality.md) **§16.11**, 12 fresh green runs across two dilutions plus
> a full probe sweep). Three rows of the 2026-07-27 banner above have changed.
>
> | 2026-07-27 read | 2026-07-30 measurement |
> |---|---|
> | *the jar's re-seating, ~98 % of instrument variance — **the gate's real blocker*** | jar tilt **2.84 % → 1.34 %** (2.1×, floor unchanged at 0.07 % so the comparison holds). Metric σ **9.7 % → 2.96 %** — first result under §16.10.3's 3 % target, replicated on two dilutions (§16.11.3) |
> | *dilution invariance **cannot be measured** until the seat is fixed* | **first evidence, in the right direction** (§16.11.6): two dilutions 16.8 % apart give metric means 1.9 % apart, `t = 1.14, p = 0.28`, and the pooled CV across both equals each alone. ⚠ n = 2 dilutions only 17 % apart — **§16.10.8 is partially unblocked, NOT resolved** |
> | *GO on discrimination, HOLD on dilution invariance* | discrimination `d` **2.72 → 4.67** on the archived brown, and → 9.81 if brown's scatter improves as green's did. **The green side is finished** (4.82 σ clear, false-brown ~1-in-3700). **All residual risk is brown: ~10 % false-GREEN on one fill**, unmeasured since the rebuild (§16.11.12) |
>
> **⇒ The gate is one brown session away.** §16.11.11's series **D** (6 re-seats → the brown σ that decides it)
> and **E** (6 fills → σ_fill). §16.7.2o's uncomfortable finding that brown scatters *like* green (11.4 % vs
> 11.2 %) is now the argument in favour: same error source ⇒ the same fix should apply.
>
> ### ✅ 2026-07-31 — series D ran. Discrimination is PROVEN on re-seat data
>
> | | result |
> |---|---|
> | brown σ, `S/Q linear base` *(6 re-seats, one fill)* | **0.131** — raw CV **1.41 %**, residual **1.58 %** |
> | pre-registered PASS criterion *(§11.4f A)* | ≤ 3.5 % → **PASS**, by ~2× more than predicted |
> | green 12.370 ± 0.367 vs brown **9.303 ± 0.131** | gap 33.0 %, **Cohen's *d* = 11.13** *(RMS pooled SD; **9.80** df-weighted — unequal n, `SPEC_capture_quality.md` §16.13.5)* |
> | at the shipped `T = 10.6` | green **+4.83 σ** *(false-brown 0.027 %)*, brown **+9.88 σ** *(false-green 0.009 %; 0.50 % at σ's 95 % upper bound)* |
> | brown mean vs archived `20260727C` *(old rig, different oil)* | 9.303 vs 9.361 = **−0.62 %** — the mean survived the rebuild |
>
> **§16.11.12's "all residual risk is brown, ~10 % false-GREEN" is retired.** The row above it —
> discrimination `d` → 9.81 *if* brown's scatter improves as green's did — is not just met but exceeded; brown
> improved **more** than green.
>
> **⇒ The gate's DISCRIMINATION criterion is met. What remains is σ_fill.** Series D excludes sample
> preparation entirely, so §11.4f **B** (series E, 6 separate fills, raw + baselined side by side, time-ordered)
> is now the single outstanding measurement — and §16.11.13's protocol inversion stays gated on it. Full
> account: [`SPEC_capture_quality.md`](SPEC_capture_quality.md) **§16.13**.
>
> ⚠ **This changes precision, not the threshold.** The paragraph below still stands in full: `T = 10.6` remains
> **unvalidated**, and series D does nothing to validate it. A 9.88 σ margin against a possibly-wrong threshold
> is a confident answer to the wrong question.
>
> **⚠ The blocker has MOVED, not disappeared — and it is no longer an instrument problem.** Everything measured
> on 2026-07-29/30 improved **precision**, not **correctness**. `T = 10.6` dividing green from brown oil is still
> **unvalidated** (§16.10.11a: `P = 0.964` is P(the *metric* exceeds the threshold), *not* P(the oil is green)),
> and a precise instrument reading a wrong threshold is confidently wrong ~96 % of the time. **The instrument is
> now precise enough that the threshold's correctness is the binding constraint** — which is this spec's territory,
> and needs reference oils with independent ground truth. No further mechanical work can close it.
>
> ⚠ Also: **§7.3's recipe table is contradicted by measurement** — see the note in that section.

### ⚖ Where this stands after 2026-07-27 — will the mill profit? *(Edwin asked directly; honest read)*

**The one-line summary of the day:** brown oil does read lower than green — in 2023 and again in 2026 — but a
**single run cannot decide it**, so the workflow moved to a **multi-fill, median-of-3 paradigm** (§16.10.17)
that earns its confidence instead of asserting it.

**Amendment to that summary:** the effect is **much smaller on fresh oils than 2023 suggested**. The 2023 set
gave *d* ≈ 10; today's fresh oils give ***d* = 1.24 on the raw ratio**, and it took the linear baseline to reach
2.88. ✅ **SOLVED 2026-07-31 — see §11.4e.** The 2023 oils were bought in 2023 and had three years to **clarify in
the bottle**: they carry **half the scatter pedestal** (0.84 vs 1.72, no overlap across eight fills). The gap
decomposes into a **turbidity** half (raw CV 2.54 % → 14.54 %, fixable) and a **panel** half (Soret/Q separation
1.96× → 1.36×, i.e. two different oil pairs are differently far apart). Neither is fatal, and the claim no
longer needs to lean on the 2023 number.

#### The uncomfortable observation

**The instrument's borderline zone probably coincides with the EYE's borderline zone.** A strongly over-roasted
oil reads ~8.0 and resolves on one fill — and a miller can *see* that one. A mildly brown oil sits at ~9.4,
needs three fills, and often still returns ÜBERGANG (§16.10.17d: only 52 % of brown triplets resolve even
after the 10.6 policy move) — and that is precisely where human judgement also fails.

So at today's precision the value is **NOT "detects what the eye cannot"**. It is:

| what it genuinely delivers | why the eye cannot |
|---|---|
| an **objective, recordable number** | the eye produces no artefact; a PDF with spectrum + verdict + embedded raw data is actionable by a buyer, lab or certification scheme ([`SPEC_lims_integration.md`](SPEC_lims_integration.md)) |
| **consistency** across operators, batches, seasons | a fixed reference does not tire, does not acclimatise to a drifting product, does not disagree with the next person |
| **contractual / incoming-goods** use | a number settles a dispute; an opinion does not |

That is a real product. It is simply not yet the *"sees what you can't see"* product.

#### What would convert it — and it is mechanical, not scientific

σ = **9.7 %** today; §16.10.3's target is **~3 %**. At 3 % most samples decide on a **single fill**, and the
marginal cases — the ones the eye fails on — begin to resolve. That is **a printed jar seat and a syringe-fill
protocol** (§16.9.4), not a research programme. **This is the strongest argument for the mechanical work, and it
is stronger than any of the statistical arguments in §16.10.**

#### The real risk is dilution, not the metric

If the reading depends on how carefully someone doses drops into isopropanol, **field use by a non-laboratory
person is fragile** — and §16.10.8 established we currently *cannot measure* whether it does, because seating
noise swamps the dilution term. This is the one open item that could **undermine** the concept rather than
merely limit it. It is also **free to resolve**: syringe-fill in place, one session (§16.9.4a).

#### Who the user actually is

~20 minutes per verdict shapes the customer. That fits a **QC station, a laboratory, or a cooperative** far
better than a miller mid-press — which points the same way as the market analysis's own conclusion
(`spectracs-references/business/SPEC_wirtschaftliches.md` §7/§12: *the lab as channel partner*). A lab has the
patience for three fills and **needs** the documentation; a busy miller has neither.

#### 📌 The positioning term: a CONSISTENCY INSTRUMENT *(Edwin 2026-07-27 — adopt this wording)*

Edwin's framing, and it is better than "documentation instrument":

> *"No magic tool — but telling one that this might be worth inspecting further. The miller uses it when he is
> not sure himself, and the tool will probably also say it is not sure. Or the tool says it first, then the
> miller."*

Why this is more than a nice phrase:

1. **Agreement between two INDEPENDENT judgements is worth more than either alone.** The miller's read is
   expert but subjective and unrecordable; the instrument's is crude but objective and recordable. Concurrence
   yields a defensible record *with expertise behind it* — which neither produces separately.
2. **Disagreement is the payload, not the failure.** Miller says green, tool says brown ⇒ something wants
   attention: an unusual sample, or the miller's internal calibration has drifted.
3. **An ÜBERGANG verdict is a feature.** When both are unsure, "unsure" is the truth. A tool that manufactures
   certainty where none exists is worse than useless. §16.10.17c's third outcome is therefore a design virtue,
   not an admission.
4. **⭐ The strongest form — a miller acclimatises, an instrument does not.** If the product drifts slowly over a
   season or over years, this year's oil looks fine because it resembles last year's. **Human reference points
   move with the product; a fixed spectral reference does not.** This is a class of error the eye *structurally
   cannot* catch — and it is not per-sample detection, it is **consistency across time**. This is what the
   instrument is genuinely better at, and it is the core of the positioning.
5. **The 10.6 threshold decision is coherent with this** (§16.10.17d). A triage instrument should over-refer:
   a second look at good oil is cheap, missing bad oil is not. Choosing 10.6 and choosing "consistency
   instrument" are the same decision reached from two directions.

**⚠ Design consequence — ORDER MATTERS (feature, not yet built).** If the miller sees the verdict before forming
their own judgement, the two are **no longer independent** — they have been anchored, and the agreement stops
meaning anything. The workflow must therefore **capture the operator's own read BEFORE revealing the result**:
a "your assessment: green / brown / unsure" field filled in at sample preparation (§16.10.17c). Then agreement
is evidence, disagreement is a flag, and over a season the divergence record becomes **calibration data for the
instrument AND the miller**. Same anti-anchoring principle as withholding the direction on a borderline re-fill.

**The honest caution to keep attached:** a sceptic will ask why buy a tool that mostly confirms what you already
thought. The answer cannot be the individual verdict — it must be **the record, the trend, and that a buyer or
lab need not take the miller's word for it.** Positioned as a per-sample oracle it looks redundant; positioned
as consistency over time plus evidence for third parties, it does not.

#### Verdict

The science is **sound, and today made it more sound, not less** — you now know what limits it, which is worth
more than a flattering number. What is unproven is not the physics but the **field robustness**: one rig, one
day, two oils, dilution invariance unmeasured.

> **Do the syringe experiment (§16.9.4a) and one fresh session before telling anyone this is ready, and position
> it first as a documentation-and-consistency instrument rather than a detection one.**

That a single day of careful measurement could localise **98 %** of the error to one mechanical joint is itself
the encouraging part. *Instruments that cannot be debugged do not become products.*

### Can we be hopeful? — honest read

**Yes — and with the too-green class dropped, more so than before.** The biggest prior risk (green-vs-greener
tangled with settle-drift) is **out of scope**. What's left is the *easy, big* cut — intact green pigment vs
degraded brown pigment — already demonstrated at 10–13× the noise, non-overlapping, dilution-robust.

| Question | Honest answer |
|---|---|
| Is the core binary claim proven? | **Effectively yes** — strong, clean, on 4 oils / 32 runs. |
| Does the settle-drift threaten it? | **No** — it pushes green *up*, away from 2.8; corrupts only the fine gradation we no longer need (§11.4b). |
| What could still surprise us? | Only that the broadened panel breaks the pattern — unlikely (price + eye + spectrum agree three ways). |
| Overall | **GO on the core claim**; remaining work strengthens evidence, it is not make-or-break. |

**Bottom line:** with scope honestly set to *over-roast detection*, this is no longer "hopeful but unproven" —
the core capability is **demonstrated**; the outstanding item (a wider oil panel) is about *confidence*, not
*viability*. And the delivery side is **already in place**: the verdict reaches the miller as an easy-to-read
in-app **Roast Ampel** (a green/brown read, not raw numbers), and preparing a sample is a few-drops-and-swirl
affair — so nothing exotic stands between the proven science and the mill floor.

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

### 1a. Scope NARROWED — binary *good-green vs over-roasted-brown* (Edwin 2026-07-24)

The three-class ambition is **reduced to a binary, deliverable goal: detect over-roasting.** Flag whether an oil
is a **good green** or a **browned / over-roasted** one. The **"too-green" class is DROPPED as a goal.** Rationale:

- **In practice oils are one of two types** — the green (good) type or the brown (over-roasted) type. There is no
  meaningful population of intermediate "amber" oils on a mill floor, so the empty 2.6–2.8 middle is **not a gap
  to fill** but a rarely-occupied boundary.
- **Ranking green oils against each other is out of scope.** "Your green is greener/fresher than his" is partly a
  **matter of taste** — not a claim the miller needs, nor one the instrument should arbitrate.
- **Brown is NOT a matter of taste.** An over-roasted oil objectively **tastes worse and sells cheaper.** That is
  the one call worth making — and it is the coarse, robust call the metric already nails.

**Consequences for the gate:**
- The **third "too-green" oil** measurement is **no longer required** (removes the old §11.6 item 1).
- The **fine green-vs-greener separation** — the settle-drift-entangled hard part — is **out of scope**. The
  settle-drift (§11.4a) therefore corrupts only a fine gradation **we don't need**, so the §11.4b "silver lining"
  is now the *whole* story, not a consolation prize.
- The **verdict threshold already exists**: the Roast-Ampel zone boundary at **2.8** ([`SPEC_roast_ampel.md`](SPEC_roast_ampel.md)).
  Calibrating finer roast-degree gradations is deferred / out of scope.
- What remains is **confirmatory, not make-or-break**: broaden the panel (1 brown + 4 green, §11.6) to lift the
  good-vs-brown call from n=4 bottles to a wider set. The core claim — *dilution-invariant good/brown
  discrimination* — is already met.

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

### 2.1a ⚠ RESTATEMENT — the shipped metric is a **THREE-REGION** construction, not a two-band ratio  *(2026-07-31; DRAFT for Edwin. Forced by `SPEC_capture_quality.md` §16.12.12–§16.12.13)*

Everything above describes the metric as a **ratio of two pigment bands** with a baseline correction applied to
clean it up. **That description is incomplete, and the incompleteness is load-bearing.** This section restates
what the shipped code actually computes. No result below is withdrawn — §11's verdicts stand — but the
*explanation* attached to them has to change before the gate is defended.

#### What the code actually computes

`DevSpectralPlugin` + `SpectrumFeatureUtil.linearBaselineCorrected`, in three steps:

1. Fit a straight line `b(λ)` through the mean absorbance of two anchor windows —
   **near `W_n` = 520–540 nm** (centroid 530) and **far `W_f` = 600–630 nm** (centroid 615).
2. Subtract it: `A'(λ) = A(λ) − b(λ)`.
3. Metric = `mean(A' over 440–460) / mean(A' over 560–580)`.

Expand step 1 at the two band centroids (450 and 570) and the metric written out in full is:

```
                A_Soret − 1.941·A_near + 0.941·A_far
    S/Q   =   ──────────────────────────────────────
                A_Q     − 0.529·A_near − 0.471·A_far
```

**`A_far` is not a correction term. It is a fourth measured quantity that enters the numerator with a POSITIVE
coefficient (+0.941) and the denominator with a NEGATIVE one (−0.471) — both of which raise the ratio.** More
signal in 600–630 nm means a higher green score, mechanically.

*(Verified numerically, not just derived: the expanded formula reproduces `linearBaselineCorrected`'s own output
to within **0.5 %** on both classes — green `20270729B/001` 12.690 vs 12.749, brown `20260727C/001` 9.841 vs
9.859, green `20260727B/001` 11.621 vs 11.666. The small residual is the centroid approximation — the code uses
band *means*, the formula uses the band centre.)*

#### Why that matters: the far window is not signal-free

`DevSpectralPlugin`'s own comment calls these *"the two OIL-QUIET windows"* that *"sit where the oil itself is
featureless."* **For the far window this is false**, measured two ways on 37 runs across six fills and two
sessions (`SPEC_capture_quality.md` §16.12.12):

- Absorbance **rises** across 600→630 nm, and the rise is **green 0.0535 vs brown 0.0159 — 5.1 σ**, while the
  reference lamp sits at the same 35–39 DN for both classes. An instrument effect cannot know which oil is in
  the jar.
- Regressing that rise on the greenness ratio gives **intercept ≈ 0**: the rise vanishes exactly when the
  greenness does.

It is **real green-pigment absorption** — the rising flank toward the pigment's red (Qy) band. For brown oil
the far window genuinely *is* quiet (rise 0.007–0.021); for green it is not.

> ⚠ **Corrected 2026-07-31** (`KB_spectroscopy_physics.md` §4.1): this said *"chlorophyll … Q maximum near
> 665 nm, outside our clamp"*. The pigment is **protochlorophyll** (Fruhwirth & Hermetter 2007) and its Qy
> is at **~623–626 nm** — **at the edge of the clamp, not beyond it**. The measurement is untouched; the
> attribution gets stronger, and the case for widening the window gets considerably cheaper.

#### And it is carrying a large share of the discrimination

The far-anchor sweep (`SPEC_capture_quality.md` §16.12.13), scored on §16.10.9's basis — 25 runs, 4 fills:

| far window | LOFO errors | Cohen's d | class gap |
|---|---|---|---|
| 610–630 nm *(further red)* | 1/25 | **3.28** | **+0.782** |
| **600–630 nm — shipped *at the time of this sweep*** | **1/25** | **2.88** | **+0.495** |
| 600–620 nm | 4/25 | 2.28 | OVERLAP |
| 600–615 nm | 9/25 | 1.95 | OVERLAP |
| 600–610 nm *(contamination removed)* | 12/25 | **0.94** | OVERLAP |

**Monotone, and replicated by a second sweep that slides the window instead of shrinking it.** The further red
the anchor reaches, the better green separates from brown — because for green the window mean climbs the
chlorophyll flank while for brown it barely moves. **Remove the contamination and the classes overlap outright.**

#### ⇒ The restated claim

> The pigment ratio is a **three-region measurement**: the Soret band (440–460), the Q band (560–580), and a
> **third pigment-bearing region at 600–630 nm** which enters through the fitted baseline's slope and raises the
> green score. It is **not** "two pigment bands with an instrument-artifact correction."

**What this does NOT change.** §11's results are empirical — leave-one-fill-out scoring on real fills — and they
stand. The shipped 600–630 window sits near the optimum of the trade-off it participates in. **Nothing here says
a verdict was wrong.**

**What it DOES change.**
1. **The physical story in §11.5 is incomplete** — it explains Soret and Q, and is silent on the third region
   that the sweep shows is doing comparable work.
2. **The metric is more exposed than documented** to anything that moves 600–630 nm: the settling drift
   (`SPEC_capture_quality.md` §16.12.11 A) and the lamp's red-end collapse to 39 DN (§16.12.11 B) both act
   exactly there.
3. **`SPEC_pumpkin_peak_ratio_eval.md` §1b.1's "literature-anchored bands" framing is only two-thirds true.**
   440–460 and 560–580 are literature-anchored; the third region is not — it arrived as a baseline anchor
   chosen for being *quiet*, and it turns out not to be.

#### ▶ The decision this forces — covert or explicit?

> ⭐⭐ **ANSWERED 2026-08-03 — option (a), by RELOCATION.** The window was moved to **620–630 nm** so that it stands squarely on protochlorophyll's Qy(0,0) band instead of straddling its foot, and it is declared in `declaredEvalBands()`. That converts the covert third region into a stated one without inventing a new coefficient, so the recommendation below (*"do (b) now, schedule (a) after series D/E"*) is **superseded**. The fitting-trap warning in the last paragraph still stands and was honoured: 620–630 was adopted on **post-rebuild** data with a real brown series, and it was not the top scorer of the sweep below. `SPEC_capture_quality.md` §16.20; the pedestal residual was re-fitted with the anchor (−0.0246 → −0.0184).

**(a) Declare it.** Make 600–630 an explicit third band in the plugin, with its own name and its own entry in
`declaredEvalBands()`, and write the metric as a stated three-band formula. Then it can be tuned, error-budgeted,
and defended. Costs: the metric's definition changes shape (values need not change at all if the coefficients
are kept identical), and the spec text has to be rewritten in several places.

**(b) Keep it covert, document it honestly.** Change nothing in code; add this restatement to the specs so no
reader is misled. Cheapest, and it keeps every number stable — but it leaves a measuring band disguised as a
correction, which is how this went unnoticed for months.

**Recommendation: (a), after series D/E.** The sweep rests on **pre-rig-rebuild** 07-27 fills (within-fill CV
~9.7 % against §16.11.3's 2.96 %) with only **two brown fills**, one of them 3 runs. Redesigning the metric on
that basis would repeat §16.10.16's trap. **Do (b) now — it is free and it removes the misleading text — and
schedule (a) on post-rebuild data with a real brown series.** ⚠ Do **not** adopt 610–630 on today's evidence
even though it scores better; picking the best window out of a sweep is exactly the fitting trap.

#### ✅ RESOLVED — §11.4c's sign is NOT contradicted, and the baseline EARNS ITS KEEP  *(`diagnostics/baseline_vs_raw.py`, 2026-07-31)*

The draft above suspected the linear baseline of *reversing and amplifying* the settling effect, because §11.4c
predicts settling **inflates** S/Q (§11.4a: 3.66 → 4.57 over 11 h) while `SPEC_capture_quality.md` §16.12.11 A
measured the shipped metric **deflating** over 30 min. **Measured on the archived PDFs, that suspicion is wrong
on both counts.** Raw and baseline-corrected S/Q, on every dataset on disk — every number is a change that
*should be zero*:

**Dilution invariance** — the metric's whole justification (§3):

| pair | RAW % | **LIN. BASE %** | raw weak→strong | base weak→strong |
|---|---|---|---|---|
| green `oilK`→`oilL`, 2→3 drops *(§11.1 UC2)* | −3.20 | **+0.36** | 3.887 → 3.762 | 6.625 → 6.648 |
| brown `oilN`→`oilM`, 2→3 drops *(§11.4)* | **+5.59** | +5.98 | 2.347 → 2.478 | 3.272 → 3.467 |
| green set B→C, ~17 % apart *(§16.11.6)* | −7.68 | **−1.91** | 5.603 → 5.172 | 12.489 → 12.251 |
| **mean \|error\|** | **5.49** | **2.75** | | |

**Settling:**

| interval | RAW % | **LIN. BASE %** | signs |
|---|---|---|---|
| green fresh→aged, ~11 h *(§11.4a)* | **+24.25** | **+6.28** | agree |
| green set B, ~28 min *(§16.12.11 A)* | −9.66 | −5.38 | agree |
| green set C, ~33 min | −1.80 | −6.93 | agree |
| **mean \|error\|** | **11.90** | **6.20** | |

**📈 `spectracs-references/tmp/baseline_vs_raw.png`.**

**Three findings, and they change the tone of this section:**

1. **No sign flip anywhere — the signs agree on every dataset.** What looked like a contradiction is a
   **timescale difference**: over ~11 h the ratio *inflates*, over ~30 min it *deflates*. §11.4c's physics
   describes the hours-scale clearing and remains correct; §16.12.11 A describes a different, faster,
   opposite-signed phase. **⇒ The settling curve is NON-MONOTONIC**, which is new, and it explains why
   §11.4a's "measure fresh, don't reuse an aged cuvette" and §16.11.7's "let a fresh dilution equilibrate
   ~15 min" are both right — they guard different phases of the same curve.
2. **§11.4a is reproduced exactly.** Its 3.66 → 4.57 is **+24.3 %**; the raw metric here measures **+24.25 %**
   on the same PDFs. An independent confirmation of the whole toolchain, three months on.
3. **⭐ The linear baseline HALVES BOTH error terms** — dilution 5.49 → 2.75 %, settling 11.90 → 6.20 %. It is
   not a liability that happens to boost discrimination; it demonstrably improves **both invariances the metric
   claims**, on data that long predates it.

*(One exception, and it is the expected one: brown `oilN`→`oilM` is the single pair where the baseline does not
help (+5.98 vs +5.59). §11.4 already established that the brown oil carries more particulate scatter and that
its dilution-invariance is measurably weaker. Caveats: the aged-green point is **n = 1 PDF** against 8 fresh
runs, and each dilution pair is 4 runs per level.)*

#### ⇒ This strengthens the recommendation, and flips it toward (a)

The far window is not a defect to be tolerated for the discrimination it buys. **It is earning its place on
three independent axes — discrimination (§16.12.13), dilution invariance, and settling immunity.** A component
doing that much work should not be disguised as a correction anchor: it should be **declared, named,
error-budgeted and tunable**.

**Revised recommendation: do (b) immediately** — the misleading text is already fixed in `DevSpectralPlugin`
and in these specs — **and schedule (a) as a genuine design step**, still gated on post-rebuild data with a
real brown series so the window choice itself is not fitted on today's four fills (§16.10.16's trap).

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

> ⚠ **And a note for whoever reads "olive carries them too" as a market opportunity — it is not one.**
> The physics does invite the thought: the same pigment family sits in olive oil, so a colour instrument
> looks transferable. **The standard of that market forbids it.** The IOC method for the organoleptic
> assessment of olive oil **mandates dark blue tasting glasses** *"to prevent the taster from perceiving
> the colour of the oil, thus eliminating any prejudices"*, plus red or neutral lighting — because in
> olive oil **colour is explicitly not a quality indicator** (it varies with cultivar, harvest timing and
> filtration). Their instrumental screening work goes through **volatiles** (HS-GC-IMS, e-nose), not
> colour. ⇒ **Shared pigments, incompatible grading culture.** Commercial reasoning:
> `spectracs-references/business/SPEC_oelmuehlen_verzeichnis.md` §84.B (outside git).

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
**Anchor — SETTLED (Edwin 2026-07-20): the analysis-window min.** Read the scalar `A` to subtract at the lowest-
absorbance point across the whole analysis window (the truly transparent, signal-free region — most likely the
red end), not the local green-window trough (which risks subtracting a real shoulder). Matches textbook practice
(Rinnan 2009: offset-correct off the genuinely transparent region). The green-window min stays as a *knob* to try
only if drift directly under the feature turns out to dominate. **Caveat:** the flat-offset removes only a *flat*
`b`; if the rig's `b` is sloping (scatter/RI), a 1st-derivative or a large-window baseline is the fallback (§10.1)
— the bench will reveal it.

**The new LogicModule — name SETTLED: `FlatOffsetBaselineLogicModule`** (folder `logic/spectral/flatOffsetBaseline/`,
method `flatOffsetBaseline`, sibling `…Parameters`/`…Result`). Parallels the existing `RemoveBaselineLogicModule`
(both verb-first, both under `logic/spectral/`) and reads as "apply a flat offset baseline." *Flat* = 0th-order /
constant (vs the morphological one); *Offset* = subtract a single scalar. (Considered: `OffsetBaselineLogicModule`,
`AnchorBaselineLogicModule` — `FlatOffset…` is the combined name that names both the order and the operation.)
The `plugin_sdk` exposure (`baselineOffset` / `SpectrumUtil.baselineOffset()`) delegates to this module.

**Why not reuse `RemoveBaselineLogicModule` (the algorithm already in the tree):** it is a **morphological opening**
(`minimum_filter1d` then `maximum_filter1d` over a resolution-adaptive window ≈ 10% of the spectrum width). It was
built to isolate **sharp emission lines** for calibration peak-detection — with its default small window it would
strip the **broad colour-carrying absorption envelope** we are trying to measure. A morphological opening with a
*very large* window ≈ a flat offset, but that is a roundabout way to get a constant. So Entry 0 uses the dedicated
`FlatOffsetBaselineLogicModule` directly. (This distinction is to be captured as a doc comment on
`RemoveBaselineLogicModule` — see §8.1 pending code touches.)

> **Common-mode caveat (see §10.4):** the camera-linearity nonlinearity is present in BOTH the raw and improved
> paths, so Entry 0 stays valid as a *relative* comparison (the confounder cancels in the with-vs-without read);
> only *absolute* colour claims inherit the linearity caveat.

### 7.0.2 Capture ROI — narrow to the lamp's usable band  *(Edwin 2026-07-20)*

The DEV plugin currently declares the host-clamped capture window as `WAVELENGTH_MIN_NM = 430.0` /
`WAVELENGTH_MAX_NM = 650.0` (`DevSpectralPlugin`). **Decision: retune to `440.0 … 630.0 nm`** — the CFL lamp
actually delivers reasonable light only across ~440–630, so the outer 430–440 / 630–650 edges feed the `S/R`
floor-guard mostly noise. Narrowing the ROI keeps those dead margins out of the stored spectrum entirely.

Guard: the window must still ⊇ every `declaredEvalBand()` (asserted in `acquisition()`). `440–630` covers the raw
bands (blue 450–490, Q 555–600) **and** the incoming new PB literature bands (blue Soret slope **440**–460, green
560–580, `Q_BASELINE` anchor 550) — the min moving to 440 is exactly what the new 440-nm blue band needs, so the
two changes are consistent, not in tension. Update the §9/M1 comment block alongside the constants.

### 7.1 Two setups, in order

| Setup | Cells | Purpose | When |
|---|---|---|---|
| **A — two-pot** | pot A = blank (3 ml isopropanol) as REFERENCE; pot B = alcohol + oil as SAMPLE | **quick look** — hope it already separates the oils reasonably | first, because it is the current bench flow |
| **B — one-pot** | one pot: capture R (3 ml alcohol) → add drops, stir → capture S | **transferable** — identical glass in R and S ⇒ `b_glass = 0`; matches the one-pot end user | after A, for the trustworthy numbers |

Setup A carries a glass-mismatch offset `b_glass` that will **not** transfer to the one-pot field user
(`SPEC_pumpkin_peak_ratio_eval.md §13.4`). It is fine for a *quick* "does anything separate" read; Setup B is the
one any threshold work must use. Running A then B also **directly demonstrates** whether `b_glass` matters (does
the separation survive the switch?).

### 7.2 Lab use cases (the run taxonomy — named by what each PROVES)

Renamed 2026-07-20 (Edwin): "Entry 0 / Run 1-3" were unillustrative. Each use case is now named by the claim it
tests. UC0 is the build skeleton; UC1-UC3 are the scientific runs. (Old → new: Entry 0 → UC0; Run 3 → UC1;
Run 1 → UC2; Run 2 → UC3.)

- **UC0 · Correction sanity — colour, corrections on vs off, ONE oil × ONE dilution (§7.0).** The build skeleton
  and first diary entry: capture one oil at one dilution, render the **colour chips + paired metrics**, each shown
  side-by-side **with and without** the correction (raw vs `· improved`). **Observation to record:** whether/how the
  correction shifts each value. No invariance claim yet — this proves the machinery moves things sensibly.
- **UC1 · Repeatability — ONE oil, same dilution, N runs.** Measure one oil **~5×** (re-prep each time). Proves
  "does it give the same answer twice" (`SPEC_pumpkin_peak_ratio_eval.md §13.8 gap 2`) → the **variance floor** /
  noise floor to compare against `D_Q` (the metric's real SNR). Cheap and worth knowing before any threshold.
- **UC2 · Dilution-invariance — ONE oil, two dilutions (Edwin).** Take **one** oil (start with the *typical green*)
  and measure it at **2 drops** and **3 drops** in 3 ml isopropanol. Compare the metric tables (§4.2) across the two
  dilutions. **Expectation to confirm:** the metrics barely move. *This validates the whole "dilution-invariant by
  concept" premise.*
- **UC3 · Discrimination — three oils.** Measure all three oils (too-green / typical / brown), each at a fixed
  dilution. **Expectation:** the metric vectors land in three visibly separated clusters (§2.4).

Order to run: UC0 (skeleton, done) → UC1 (repeatability) → UC2 (invariance) → UC3 (discrimination).

### 7.3 Per-capture procedure — **REVISED 2026-07-26 for the fresh 2026 oils (batch-and-pour)**

> ⚠ **CONTRADICTED BY MEASUREMENT 2026-07-30 — do not act on the dilution table below until the drop volume is
> weighed.** This section's recommendation (1:30–1:33) rests on a **simulation** predicting min DN @ 440 nm = 25
> for green. The rebuilt rig **measures 0.65–0.85 DN** at the nominal 1:30 — the oil absorbs ~2.1× more than
> modelled, implying a real ratio nearer **1:14** and a drop of **~0.21 ml**, not the **0.10 ml** this section's
> "2 drops in 4 ml ≈ 1:20" arithmetic assumes. Separately, §7.3's *criterion* — keeping the 440 nm bins out of the
> sRGB toe — has since been tested and **does not bind**: those bins do not hurt the metric, and moving the band
> away from them is strictly worse. What §7.3 never checked is the metric's **scatter**, which goes as `1/A_Q`, so
> the correct rule is the opposite of the one below: **among dilutions whose metric VALUE is invariant, pick the
> STRONGEST that keeps the bands linear.** Full analysis, both tables, and the ▶ action (weigh 20 drops):
> [`SPEC_capture_quality.md`](SPEC_capture_quality.md) **§16.11.15** and **§16.11.14**. Current working recipe is
> **18 ml + 6 drops, fresh, ~15 min to settle, measured within the hour** (§16.11.7, §16.11.15).

**Why it changed.** The lab conditions changed with the 2026 oils: they are **fresher and absorb far more** than
the aged 2023 oils. At the old strength (2 drops in 4 ml ≈ **1:20**) the sample bottoms out at **DN 5 of 255** at
440 nm — 17 % of the Soret band sitting in the camera's sRGB *toe*, the least trustworthy part of its response
([`SPEC_capture_quality.md`](SPEC_capture_quality.md) §17.5). The oil is essentially opaque there. **Too much
absorption, not too little.**

**The fix is a weaker dilution.** Simulated on the measured 2026 spectra (Beer-Lambert scaling, sample DN
re-quantized to integers), the minimum acceptable strength is ≈ **1:27**; **1:30–1:33** is comfortable:

| dilution | min DN @ 440 (brown / green) | verdict |
|---|---|---|
| 1:20 (old) | 5 / 10 | **too dark** — 17 % of Soret bins in the toe |
| 1:25 | 10 / 18 | still marginal |
| 1:27 | 12 / 20 | minimum that clears it |
| **1:30** | **16 / 25** | comfortable |
| **1:33** | **21 / 31** | comfortable, more headroom |

**The pigment ratio moves ±0.35 % across all of them** (vs an 8.7 % run-to-run spread) — dilution-invariance doing
its job. So the recipes are **interchangeable mid-series**, the Ampel threshold **4.4 is unaffected**, and the
existing 1:20 runs stay comparable.

**Key insight that shapes the recipe: the TRANSFER volume does not matter.** The measurement sees the solution's
*concentration* and the pot's fixed path length. How many ml you pour in is irrelevant as long as the beam passes
through liquid. **Only the batch concentration needs to be accurate** — so prepare the batch in whatever glass
reads best, then simply fill the pot.

> **⚠ CORRECTED 2026-07-27 — this holds only if the pot is filled to a REPEATABLE level.** The pot is a 3 cm ×
> 1.3 cm screw-jar and the beam runs **vertically** through it, so the **path length is the fill depth**: 4 ml =
> 0.57 cm, 6 ml = 0.85 cm, 8 ml = 1.13 cm. **1 ml ≈ 11 % of a full path ⇒ 11 % on absorbance** — the same order
> as the ±25 % drop-count error this section calls the dominant prep term. The claim above is true for a cuvette
> with a horizontal beam and a fixed width, not for this geometry. **Fix: fill the jar to the brim and close the
> lid** — the path becomes the jar's own 1.3 cm, and the free liquid surface (a 3 cm meniscus sitting in the
> beam) disappears with it. See `SPEC_capture_quality.md` §16.7.4, and §16.7.2/2b for what that free surface and
> the re-seating cost: **a 5.3 % band of irreproducible optical states, ~10 % on the pigment ratio.**

```
Prepare a BATCH at 1:30–1:33 in the measuring glass, swirl until clear
   6 ml isopropanol +  2 drops oil   = 1:30   (1 pot-fill  — improvised interim recipe)
  10 ml isopropanol +  3 drops oil   = 1:33   (2 pot-fills — standing recipe, 10 ml cylinder)
  20 ml isopropanol +  6 drops oil   = 1:33   (5 pot-fills — when running a series)
→  fill the pot with PURE isopropanol, place, capture REFERENCE
→  empty, fill the pot from the swirled batch                →  capture SAMPLE
→  bench computes T = S/R, A = −log10(S/R), then the preprocessing matrix + metrics (§4.2)
```

> ### ⭐ RECALIBRATED RECIPE — measured 2026-07-27, USE THIS ONE
>
> Derived from three same-sample runs that scattered **CV 14.2 %** (vs the 2023 series' 3.6 %), anchored on two
> runs of known dilution (8 ml + 2 drops → A_Soret 0.664; 6 ml + 2 drops → 0.801). Diagnosis: **the sample had
> been diluted 1.7× too far** — the Q band, which is the ratio's denominator, fell to `A_Q ≈ 0.09`, and the error
> amplification `0.434/A_Q` rose from 2.1 (2023) to 4.5. See `SPEC_capture_quality.md` §16.7.
>
> **Standing recipe: 0.333 drops/ml.**
>
> ```
> BATCH:  18 ml isopropanol + 6 drops oil   — swirl until clear, ~4 pot fills
>         (9 ml + 3 drops if you need less; avoid 2-drop batches)
> ```
>
> | recipe | drops/ml | A_Soret | A_Q | darkest bin | error amplification |
> |---|---|---|---|---|---|
> | 10 ml + 2 drops | 0.200 | 0.51 | 0.099 | 58 DN | 4.4 — **too weak** |
> | 8 ml + 2 drops | 0.250 | 0.63 | 0.124 | 44 DN | 3.5 — weak |
> | **18 ml + 6 drops** | **0.333** | **0.84** | **0.166** | **27 DN** | **2.6 ← target** |
> | 8 ml + 3 drops | 0.375 | 0.95 | 0.186 | 21 DN | 2.3 — edge |
> | 6 ml + 3 drops | 0.500 | 1.26 | 0.248 | 10 DN | 1.7 — **at the floor** |
>
> **Why more drops for the same concentration:** drop count is the crudest step — ±½ drop is ±25 % at 2 drops,
> ±17 % at 3, **±8 % at 6**.
>
> **⚠ CLARIFY THE SAMPLE (2026-07-27, untested lever).** Fresh unfiltered oil carries suspended solids that
> scatter greyly across the whole window. Measured: the broad baseline is **72 %** of the Q band in the fresh
> 2026 oils against **~50 %** in the three-year-old 2023 ones, and the pigment content of the denominator is
> **halved** — which is why the same jar handling scatters 2-3x more now (`SPEC_capture_quality.md` §16.7.2l).
> **Let the diluted sample stand overnight, or filter/centrifuge it, before measuring**, and check that `A_red`
> (600-630 nm) drops. This is untested but it is the cheapest lever available: it attacks why the denominator is
> fragile rather than the disturbance that exploits it.
>
> **Two rules that matter as much as the recipe:**
> 1. **Fill the jar identically every time, blank and sample.** The beam is vertical, so the fill depth *is* the
>    path length — 1 ml ≈ 11 % of absorbance (§16.7.4). Fill to the brim, or mark one volume and keep to it.
> 2. **Let the instrument confirm it.** Every capture prints `CAPTURE-LOWDN role=… minDn=…`:
>    **20–40 DN = correct · < 16 DN = too strong, add solvent · > 50 DN = too weak, add a drop.** That makes the
>    recipe self-correcting regardless of drop size or oil batch.
>
> **Expected:** CV 14.2 % → ~8 % from the recipe alone → ~4.5 % with a stabilised blank → **~2.6 % averaging 3
> fills**, i.e. back to 2023-series quality and under the 4.1 % needed to separate S/Q 4.2 from 4.8.

- **Glassware.** A 10 ml **graduated cylinder** (narrow bore, ~0.2 ml graduations) — not a beaker. Read the bottom
  of the meniscus at eye level. Volume error then ≈ 2 %, leaving the **drop count** as the dominant prep error.
- **Drop count is the crude step.** ±½ drop is ±25 % at 2 drops, ±17 % at 3, ±8 % at 6. Preparing a larger batch
  at the same concentration is the cheapest precision win available; alcohol *per run* is 4 ml either way once the
  batch yields ≥ 5 fills.
- **Swirl before every pour** — a standing batch can stratify.
- **Evaporation is forgiving**: it concentrates the oil, and the ratio is dilution-invariant. Keep it covered
  anyway so the DN stays in range.
- Sloppy drop-counting remains tolerable — the ratio cancels *how much* oil (§3). Effort belongs on **dissolving
  cleanly** (clear, not cloudy), because turbidity is additive and does **not** cancel.
- **Record the recipe per run.** The METADATA form has no dilution field yet (`title`, `temperature`,
  `dateOfRoasting`); until one exists, put it in the **title** ("Steirerkraft 10ml+3"). Every report PDF embeds the
  whole workflow JSON, so the recipe then travels with the evidence. *Proposal, design-only:* add a `dilution`
  `MetadataField` to `DevSpectralPlugin.metadata()` — one line.

**Suggested one-batch experiment (cheap, not yet run).** The 8.7 % within-oil spread mixes **prep noise** and
**instrument noise**, which have never been separated. Fill the pot 2–4× from a *single* batch: that spread is
instrument-only. Compare against the existing four-separate-preps figure. If much smaller, prep dominates and
batch-and-pour is a permanent win; if similar, drop-counting was never the bottleneck. Either answer finally gives
the Ampel threshold a measured error bar.

*History: the 2023 proof series ran at 3–4 ml with 2–3 drops (≈1:20); all 32 archived runs are at that strength.*

---

## 8. Implementation phases  *(DESIGN — implement on explicit request only)*

```
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| Ph | What                                      | New / Touched                    | Gate (drive-and-observe)            | Risk    |
+----+-------------------------------------------+----------------------------------+-------------------------------------+---------+
| V1 | FlatOffset baseline op (Entry-0 needs it)  | NEW FlatOffsetBaselineLogicModule | On a captured A(λ): flatOffset/snv/ | LOW     |
|    | + SNV op (bench toggle) + wire smooth/      | + SnvSpectrumLogicModule (+ each   | baseline/smooth each produce a sane |         |
|    | baseline into SpectrumUtil as steps        | Params/Result); TOUCH SpectrumUtil| spectrum; façade order documented.  |         |
|    |                                            | (add flatOffset()/snv())         |                                     |         |
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

### 8.1 Entry-0 concrete code touches — the E-phases  *(IMPLEMENTED 2026-07-20)*

Entry 0 (colour-only walking skeleton) is a **subset of V1+V2a**: flat-offset + light SG only, **no SNV** (RD-B —
SNV is deferred to the V2 eureka bench, not needed for the colour skeleton). Settled design decisions:

- **G1 seam = two SDK ops (option B), NOT a `SpectrumUtil` export.** Add role-agnostic `BaselineOffsetOp` +
  `SmoothOp` (thin `SpectraContainer → SpectraContainer` adapters, like `MeanOp`), exported through `plugin_sdk`.
  Keeps the SDK curated, mirrors what the plugin already composes with, and these two ops become V2's toggle units.
  The ops are **non-destructive** (deep-copy each spectrum before the LogicModule mutates it) — mandatory, because
  the raw `absorption` object is reused by the raw chip, the metrics, and the raw plot in the same `evaluation()`.
- **G2 = colour-only overlay.** `SpectrumPlotView.addTrace(spectrum, label, color)` has **no linestyle**, so the
  "Absorption (improved)" tab is two *coloured* traces (raw muted grey `0.6`, improved green `g`), not dashed.
- **G3 = light SG** = 1 pass / window 7 / polyorder 3 (`SmoothOp` defaults).
- **G4/RD-A = robust floor lives INSIDE the module.** `FlatOffsetBaselineLogicModule` reads its scalar floor as the
  **minimum of a median-filtered copy** (a moving median rejects a lone cold pixel that a peak-preserving
  Savitzky-Golay would *not* — caught while testing), then subtracts from the raw input — making the op
  order-independent while external composition stays literature-correct (offset → light SG, §10.1). The median
  filter is its **own** `MedianFilterSpectrumLogicModule` (not inline scipy) — a distinct smoothing algorithm gets
  its own module, like `SmoothSpectrumLogicModule` for Savitzky-Golay; `FlatOffsetBaselineLogicModule` delegates.

```
+----+---------------------------------------------+-------------------------------------+----------+
| Ph | What                                        | File(s) — New·Touch                 | Repo     |
+----+---------------------------------------------+-------------------------------------+----------+
| E1 | FlatOffsetBaselineLogicModule: floor =      | NEW flatOffsetBaseline/{Module,     | core     |
|    | min(median-filtered copy) -> subtract from  | Parameters, Result}.py + NEW        |          |
|    | RAW -> clip>=0 (G4/RD-A). Median = its OWN  | medianFilter/{Module,Parameters,    |          |
|    | MedianFilterSpectrumLogicModule (not inline)| Result}.py; SpectrumUtil.medianFilter|         |
| E2 | Role-agnostic non-destructive SDK ops:      | NEW ops/BaselineOffsetOp.py,        | core     |
|    | BaselineOffsetOp(->E1) + SmoothOp; export   | ops/SmoothOp.py; TOUCH plugin_sdk/  |          |
|    | via plugin_sdk (SpectrumUtil NOT exported)  | __init__.py                         |          |
| E3 | Doc comment on RemoveBaselineLogicModule    | TOUCH RemoveBaselineLogicModule.py  | core     |
| E4 | __improvedAbsorption(a) + 2 twin chips      | TOUCH DevSpectralPlugin.evaluation  | plugins  |
| E5 | "Absorption (improved)" PROCESSING tab      | TOUCH DevSpectralPlugin.processing  | plugins  |
| E6 | ROI 430/650 -> 440/630 + §9 comment         | TOUCH DevSpectralPlugin (consts)    | plugins  |
| E7 | Diary Entry 0 scaffold                       | NEW LAB_DIARY_capability_proof.md   | docs     |
+----+---------------------------------------------+-------------------------------------+----------+
Tests (spectracsPy/tests): FlatOffset LogicModule unit (E1), BaselineOffsetOp/SmoothOp op tests (E2),
headless evaluation "7 chips + improved hue" (E4). Never edit android/*/app_src (stale build-staging).
```

### 8.2 De-spike batch (F-phases) — *(IMPLEMENTED 2026-07-20, after the oilH finding)*

The UC1 repeatability data (oilH, §7.0.1 below) showed the flat-offset **hurts** the small band-mean metrics (it
subtracts a floor comparable to `A_green` and injects its own variance). Two corrections + a de-spike, so the
processing becomes a clean ladder:

```
raw ──[de-spike: median k≈7]──► despiked ──[flat-offset: red-end anchor mean]──► despiked+baseline
        │                                                                              │
        └── METRICS = raw + `· despiked`  (flat-offset dropped from metrics)           │
            COLOUR (10-chip set) uses raw / despiked / despiked+baseline  ◄────────────┘
            (processed rungs hue-normalized; NO SG — near-no-op for chromaticity, Edwin)
```

- **De-spike (F1)** — new `MedianFilterOp` (wraps `MedianFilterSpectrumLogicModule`, kernel 7, non-destructive).
  Removes the narrow **instrument** spikes (the ~473 nm blue-pump edge, the ~607 nm registration artifact) while
  leaving broad oil bands intact. Safe for every metric (oil features are 20–100 nm; spikes are 1–5 px).
- **Floor estimator (F2)** — `FlatOffsetBaselineLogicModule` gains `floorMode`: **`anchorMean`** (default) = mean of
  `A` over a deep-red transparent window **[615, 625] nm**, OUTSIDE every metric band and low-variance (a mean, not
  a min); **`medianMin`** (the old min-of-median) kept selectable per Edwin.
- **Metrics colour-split (F3/F4)** — metrics recompute on **raw + de-spiked** (flat-offset removed from them);
  `D_Q` still barely moves (local baseline), `A_blue` drops where the ~473 spike inflated it. De-spike computed
  once, shared.
- **Colour = a 10-variant set (Edwin 2026-07-20)** — intrinsic (absorbance) then intrinsic-perceived (+180°
  complement) then perceived (transmission). Each intrinsic family: **natural, hue-norm, · despiked,
  · despiked + baseline**; perceived: **natural + hue-norm**. Processed rungs are hue-normalized (fixed S/L) so only
  HUE moves. `baseline-corrected` = de-spike → flat-offset(anchorMean), **NO SG** (near-no-op for chromaticity).
- **Ladder tab (F5)** — the PROCESSING absorption tab shows three traces: raw (grey) → despiked (orange) →
  despiked+baseline (green), so the spike removal and baseline shift are visible.
- **Kernel caveat:** k=7 fully kills the ~473 spike (~2 px) but only tames the ~607 (~5 px); bump to 9 on the rig
  if needed (607 is outside all bands anyway). Rig re-export pending to see raw-vs-despiked on real `b`.

Tests: `test_flat_offset_baseline.py` (both floor modes, MedianFilterOp), `test_dev_plugin_improved_colour.py`
(despiked metric twins, 3-trace ladder). 46 targeted tests green.

### 8.3 PB-band "Evaluation (new)" tab — the V-phase (V3) — *(IMPLEMENTED 2026-07-22, Edwin)*

The PB literature bands land as a **new, parallel EVALUATION view** rather than by mutating the shipped metrics —
"emit both" (§2.1) realized as **tab-vs-tab**, not cell-vs-cell. All in `DevSpectralPlugin.py` (mean → `bandMean`
already exists, no core change). Unit + headless GREEN (24 plugin tests: 7 new/updated in
`test_dev_plugin_improved_colour.py`); **RIG-VERIFIED 2026-07-22 (Edwin)** — the new tab renders on the bench and
the Pigment ratio discriminates cleanly on K/L/M/N (§11.2a).

- **New step `Evaluation (new)`** (a second `SpectralWorkflowStep` in `evaluation()`, after `Spectrum`, before
  `Report`). Reads the PB windows on the **despiked** absorbance as plain band **MEANS** (`__newEvaluationResult`):
  `Soret · 440–460`, `Q · 560–580`, `Clarity · 510–540`, then **`Pigment ratio`** = Soret/Q (primary, bold =
  dilution-invariant) and **`Pigment ratio · clarity`** = Soret/clarity-floor (the stable-denominator safety net),
  plus the **10-variant colour set DUPLICATED** here.
- **Mean, NOT integral (§9 decision, Edwin 2026-07-22):** the two 20-nm bands make the Soret/Q ratio identical
  either way, and means keep the same unit + cross-tab comparability as the legacy `A_blue`/`A_green`; an integral
  would inject a bandwidth factor into the unequal-width Soret/clarity comparison (20 vs 30 nm → 33 % artifact).
- **New step `Spectrum (new)`** — a **second band-marked A(λ) plot** (despiked) shading the PB Soret + Q windows +
  the 510–540 clarity floor, Q local-max marked. Sits beside `Evaluation (new)`.
- **Renames (physics; §11 found "browning" inverted):** legacy tab `Browning A_blue → Soret A_blue`,
  `Browning ratio → Pigment ratio · legacy` (compute UNCHANGED — old 450–490 / 510–540 means — so §11 numbers stay
  directly comparable, only the label strings move). Three distinct ratio labels avoid collision: `Pigment ratio`
  (new Soret/Q) vs `Pigment ratio · clarity` (new Soret/clarity) vs `Pigment ratio · legacy` (old-band Browning).
- **Colour-chip S/L "C scheme" (§5):** hue-normalized chips drop from vivid `S 80 / L 50` to calm/darker
  **`S 38 / L 34`** (`__NORM_SATURATION`/`__NORM_LIGHTNESS`); applies to every normalized chip in both tabs.
- **`declaredEvalBands`** gains 440–460 & 560–580 (both inside the 440–630 clamp — no window change). Doc-automation
  scenario `measurement_bench.py` relabelled to match.
- **✅ Q-denominator worry RESOLVED on K/L/M/N (§11.2a, 2026-07-22):** the pre-registered rubber-duck concern that
  the weak 560–580 Q band would make `Pigment ratio` (Soret/Q) jumpy is **not borne out** — over a 20-nm despiked
  mean it is the *tightest* discriminator (Δ/noise ≈ 13.5, beats legacy 10.7). Re-confirm on the 3rd oil.
- **Follow-up ✅ DONE — the intrinsic-perceived complement (§8.4 below), 2026-07-22.**

Tests: `test_dev_plugin_improved_colour.py` — new-tab band means + both pigment ratios, 10 duplicated chips, the
`Spectrum (new)` PB bands, C-scheme S/L, legacy renames (no "Browning" survives). 24 plugin tests green.

### 8.4 Intrinsic-perceived complement — option (b), the white-point reflection — *(IMPLEMENTED + RIG-VERIFIED 2026-07-22)*

The `+180° HSL` hue flip that produced `colorIntrinsicPerceived` was replaced by the **colorimetric complement**:
reflect the absorbed chromaticity through the **D65 white point** (`2·white − absorbed`) — the additive
"mixing-to-white" opposite. New `EvaluationColorUtil.complementViaWhitePoint(spectrum, ceiling)`; the DEV plugin
routes all four intrinsic-perceived rungs through it and the per-chip `hueOffset` is retired.

**Chosen by empirical comparison on all 16 K/L/M/N runs** (each candidate's intrinsic-perceived hue vs the *actual*
perceived hue from measured transmission):

| method | mean hue error vs true perceived | verdict |
|---|---|---|
| `+180° HSL` (old) | 33.9° | wrong — overshoots to green |
| Lab-180 (negate a\*,b\*) | 38.3° | **worse than HSL — dropped** |
| **b1 · reflect through white (xy)** | **4.0°** | ✅ chosen — principled, near-free |
| (c) perceived @ reference dilution | 0.3° | exact, but needs an anchor knob + redefines the chip |

- **Key finding:** a 180° rotation in *any* space (HSL or Lab) is *not* "the other half of the light" — it's off by
  ~34–38°. The white-point reflection (the true additive complement w.r.t. the lamp) lands within ~4°, and it drops
  straight into the xy the absorbed path already computes (no Lab round-trip). **Lab-180 was retired by the data.**
- **Honest consequence:** the accurate complement shows green and brown as **near-identical amber** (both perceived
  ~71°) — the eye genuinely can't separate them here. The old flip's apparent 11–20° hue "separation" was a
  distortion artifact. Discrimination stays with the **absorbed colour** + **Pigment ratio** (§11.2a); the
  intrinsic-perceived chip's only job is "…and to your eye it looks like this amber." (Why green and brown give the
  *same* complement hue — same absorbed hue-angle, different chroma — is worked out in **§11.2b**.)
- (c) is kept on the shelf as the gold-standard "perceived @ reference dilution" (needs a normalization anchor,
  e.g. Soret mean = 0.5) if an *exact* dilution-invariant perceived colour is ever wanted. Tests:
  `test_color_retrieval.py::ComplementTest` (beats-the-flip, dilution-invariant, achromatic guards).

---

## 9. Open questions / caveats

- **Per-metric preprocessing (§3).** SETTLED for **colour**: flat-offset + light SG, **no SNV** (§7.0.1, §10.1).
  Still open for the ratio/PCA path — §10.1's caution ("SNV is for turbid samples, can smear band ratios") now
  makes even the PCA-SNV of §2.3/§3 questionable; the comparison bench (§4) decides, don't hard-pick before data.
- **Baseline ↔ colour-hue tension (OPEN — needs the 3rd oil).** Flat-offset baseline correction is *double-edged*
  on the intrinsic/absorbed hue: it **helps repeatability** (oilG ×2, UC1: run-to-run hue spread 5° → 0°, by removing
  the additive `b` that drifts chromaticity) but **hurts discrimination** (green↔brown, UC3: raw hue separates 8°
  ≈5× noise vs baseline-corrected only 5° ≈2.6× — the clamp/over-compression roughly *halves* colour discrimination).
  **Interim resolution (§11, diary):** on the discriminator path use **RAW/despiked hue, not baseline-corrected hue**;
  buy stability the other way — warm camera + settled sample + higher concentration (out of the log-amplified
  near-transparent regime) — instead of by subtracting `b`. This trade-off was only observed on **two** oils, so it
  is **untested with three distinct oils**: the open question is whether raw-hue discrimination survives the too-green
  oil, or whether a *smarter* correction is needed (see next bullet — a sloping/derivative `b` fix, not the flat 0th
  order). Note the sRGB→gamut clamp is *not* the bottleneck here (clamp-free CIELAB clusters just as tight, 4° vs 5°),
  so the "softening"/Lab colour variant stays POSTPONED (§11, 2026-07-21). Resolvable only once the 3rd oil is run.
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
- **The rig lamp is a Yuji SunWave 6500 K bulb** — a phosphor-converted white LED (a **blue pump chip ~455–475 nm
  + broad phosphor** down-conversion), matching the 6500 K WB lock. Its SPD is therefore a narrow-ish blue peak
  (~20 nm FWHM) riding on a very broad (~100–150 nm) phosphor hump, plus a red-phosphor shoulder ~590–600 nm
  (see `spectracs-references/tmp/lamp_spd_annotated.png`, built from a reference raster).
- **The two sharp `A(λ)` spikes are NOT both lamp lines (raster-verified 2026-07-20):**
  - **~473 nm = REAL lamp feature** — the blue pump peak; a genuine narrow bright column in the blue channel of the
    raster, present in both reference and sample. It sits **inside `BLUE_BAND` (450–490)** and is reference-gated
    *kept*, so it mildly contaminates `A_blue`.
  - **~607 nm = a registration ARTIFACT, not a line** — the raster red channel is smooth there (no bump), just a
    steep rolloff; the spike is sub-pixel R/S misregistration on that steep slope not cancelling in S/R. It lands
    **outside every eval band** (`Q_BASELINE` ends 600), so it touches no metric.
  - Future (roadmap, not Entry-0): mask the blue-pump column out of `A_blue` and/or sub-pixel-align R vs S so
    steep-slope artifacts stop leaking.
- **Why the blue spike only became obvious after the max()-reduction (Edwin, §15 `ColorGrayUtil.toGrayMaximum`):**
  not a bug of max() — it *stopped hiding* the feature. `qGray` at the blue-pump column is ~58% green-channel /
  42% blue (Rec.601 weights blue ×0.114), and the green channel there is on its smooth phosphor slope (no peak) —
  so `qGray` **smears the sharp blue peak into the smooth green**, flattening its edges → tiny A-spike. `max()` is
  the *pure blue channel* = the sharp peak, steep edges intact → the sub-pixel-drift non-cancellation shows. So
  max() gives the faithful blue (what we want for `A_blue`) and the de-spike cleans the surfaced artifact — the
  chain (max() for fidelity → de-spike for the artifact) is consistent. A pure amplitude scaling would cancel in
  the ratio; the effect is **shape/weighting**, not scale.

### 10.3 Camera & optical confounders (ranked) — standard fix + our state

| # | Confounder | Standard fix | Our state |
|---|---|---|---|
| **C1** | **Sensor nonlinearity / sRGB gamma** — `A=−log10(S/R)` needs LINEAR intensity; consumer cameras gamma-encode | shoot RAW or invert the camera response | **Not handled — and MEASURED HARMLESS for the verdict (2026-07-26).** Decoding is designed but not built; the pigment ratio is *bit-identical* under a pure-power decode at any exponent, so C1 cannot move the go/no-go. See §10.4 and [`SPEC_capture_quality.md`](SPEC_capture_quality.md) §17.5. |
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

**RESOLVED AS A RISK 2026-07-26 (still not implemented, and no longer needs to be).** The postponement above was
made without knowing the *size* of the effect. It has since been measured, off-line, by replaying the pipeline
from the spectra embedded in the report PDFs — see [`SPEC_capture_quality.md`](SPEC_capture_quality.md) §17.5:

- **C1 (gamma) cannot move the verdict.** `A_true = γ·A_measured` is a **uniform** scale, so a ratio of two
  absorbance bands divides it out *exactly*: the pigment ratio is bit-identical (15 significant digits) at
  γ = 1.8 / 2.2 / 2.6. The Capability Proof's separation was therefore never at risk from C1 — and, because the
  condition is "*a* pure power law" rather than "2.2 exactly", ratios are already comparable across cameras with
  different gammas. Absolute absorbance and colour *do* inherit the caveat (as §7.0.1 says); only they.
- **C2 (dark/black level) is measured absent** — 0.00 % of full scale over 150 dark frames at the worst-case
  exposure (`SPEC_capture_quality.md` §4). Not "unaddressed", but *not present on this camera*.
- The decode itself (pure `x^2.2`; the piecewise sRGB curve was measured to cost 24 % of the class separation and
  was declined) remains designed-and-unbuilt, motivated by **colour accuracy and closure**, not by the verdict.

### 10.5 The absorbed-colour reference tilt — UC1 finding (oilJ, 2026-07-20)

**Observation.** Run-to-run (same oil), the **perceived** colour is rock-stable (H89 → H89) but the **absorbed**
(intrinsic) colour drifts **~5° hue** (H282 → H287). De-spiking does **not** remove it (still 5°), so it is a
*broadband* effect, not the blue-pump spike.

**Root cause (raster-verified).** The reference SPD **shape** tilts ~1% run-to-run (green ~1% down vs blue/red;
`R2/R1` ≈ blue 1.006 / green 0.994 / red 1.011). That tiny tilt blows up in the absorbed colour because:
- **Perceived** = CIE colour of `T = S/R`, dominated by the **high-transmission** green–red window (T≈0.94), read
  *linearly* → a ~1% shift barely moves it.
- **Absorbed** = CIE colour of `A = −log₁₀(S/R)`, in the **low-absorbance** regime (A≈0.02–0.05). The `−log₁₀`
  amplifies (`dA = −dT/(T·ln10)`): a **+1.2% green T** becomes a **−19% swing in the small green A** (0.026→0.021),
  which tilts the absorbed hue's blue/green balance. Same fragility as `A_green` (the oilH finding) — the
  **low-A + log-amplification** regime.

**Likely source of the reference tilt (ranked):** (1) AE / auto-WB re-convergence between captures; (2) lamp
thermal drift (the LED's blue-pump-to-phosphor ratio shifts with junction temperature). Both re-captured references
carry it.

**Diagnostic shipped (2026-07-20):** each acquisition burst prints a `CAPTURE-SETTINGS role=… exposure_applied=…
exposure_cv2=… wb=… autoWb=… gain=…` line to stdout (`CapturePanel.__logCameraSettings` → `VideoThread` /
`CaptureBackend.readCameraSettings`). Runbook: `./runApp.sh` from a terminal, capture Reference+Sample twice,
`grep CAPTURE-SETTINGS` — if exposure/wb differ run-to-run it's AE/AWB; if identical it's thermal. See
[[spectracs-capture-settings-logging]].

**⚠ G↔K DILUTION FINDING RETRACTED (Edwin 2026-07-21): the pre-K samples had MISMATCHED ALCOHOL in the ref vs
sample pots** — so the alcohol/path did NOT cancel in `A=−log10(S/R)` (a large uncontrolled additive `b`). G–J are
therefore CONTAMINATED and not trustworthy for invariance/ratio claims. The observed G(1.7)↔K(3.1) browning-ratio
gap is at least partly that setup error, NOT clean dilution. **K is the first CORRECT setup (matched 4 ml both
pots)** → the K-series is the first trustworthy data. THEORY still holds: intrinsic absorbed colour IS
dilution-invariant (dilution scales `A→k·A`; chromaticity `xy` is scale-invariant), broken only by the additive `b`
(glass/scatter/**mismatched alcohol**) — which the baseline removes. Clean dilution-invariance test still needed:
**matched pots, one oil, two dilutions.**  (Superseded prior note — kept the still-valid points below.)
The additive `b` does NOT cancel in a ratio, so at high dilution (tiny `A_green`) it dominates → the ratio is pulled
toward 1; **lever = higher concentration** so `b` is negligible. **Lever (confirms §10.5 deepest-lever): measure at HIGHER concentration** (K `A_green`≈0.06 already
~2× truer) → `b` negligible → ratios dilution-invariant WITHOUT the noisy baseline, and the colour leaves the
log-amplified regime (more stable AND more discriminating). Absorbed colour (baseline) IS ~invariant G↔K (hue ~295
vs 300). **Colour gamut clamp POSTPONED (2026-07-21, Edwin):** confirmed real (XYZ→sRGB out-of-gamut, green ch −1 to
−5, clamped) BUT NOT the discrimination bottleneck — clamp-free CIELAB clusters just as tight (4° vs sRGB 5°), so Lab
is NOT the fix; the baseline↔discrimination tension is (untested without 3 distinct oils). "Softening" colour variant
deferred. See [[spectracs-colour-retrieval]] / SPEC_color_retrieval.

**ROOT CAUSE FOUND (2026-07-20): camera sensor SELF-HEATING** — the reference-shape tilt is a per-channel
responsivity/QE drift as the sensor warms (τ≈2.9 min, ~1.68% red/green, settles ~9 min); ruled AE/AWB (settings
pinned), evaporation (reversible after idle) and lamp (external, warm) out; the camera cold-starts every run (streams
only during ACQUISITION). Full write-up + fix options in **`SPEC_capture_quality.md §16`**. Confirmation pending: a
warm re-run (1 oil ×2 after 10-min warm-up) to check it's the *whole* 5°.

**Deepest lever:** the absorbed colour is fragile only because pumpkin oil at this dilution is nearly transparent
(T≈0.9). **Less dilution → larger A → out of the log-amplified regime** — now feasible since the max()-reduction
restored blue fidelity (the heavy dilution was to fight qGray's blue suppression, §15). Otherwise treat absorbed
colour as a *soft* signal and lean discrimination on `D_Q` (immune to all of this).

## 11. RESULTS — clean-data validation (K / L / M series, 2026-07-21)

**The earlier series (A–J) are CONTAMINATED** — mismatched alcohol in the reference vs sample pots (a large
uncontrolled additive `b` that does NOT cancel in `S/R`) and a cold camera (the sensor self-heating tilt,
`SPEC_capture_quality.md §16`). **The K/L/M series is the first clean data:** matched pots (equal alcohol both),
warm camera, higher concentration (`A` out of the log-amplified low-signal regime). On this data the capability-proof
premises hold.

**Oils (two distinct commercial products, not one oil roasted):** the **green/fresh** oil (K, L) = **"Spar Premium
100 % steirisches Kürbiskernöl g.g.A"** (a premium PGI Styrian oil — high green-pigment content); the **brown**
oil (M, N) = **"Hofer Bellasan Kürbiskernöl"** (a cheaper supermarket oil — lower pigment). So UC3 is really a
**premium-vs-commodity quality/authenticity discrimination**, exactly the field use case.

### 11.1 UC2 — dilution-invariance ✓ (K vs L, same oil, 2 vs 3 drops)
Absorbances scale **UNIFORMLY**: `A_blue` ×2.04, `A_green` ×2.06 (identical ⇒ pure `A→k·A` scaling ⇒ `b`≈0 — matched
pots worked). **The Browning ratio is invariant: K 3.13 ↔ L 3.10 (1%)** across the 2× concentration change (vs the
contaminated G(1.7)↔K(3.1)). Intrinsic hue stable (293↔289). ⚠ Greenness NOT perfectly invariant (1.43↔1.20) —
`D_Q` under-scales (×1.74 vs A's ×2.06), a `D_Q`-method effect, not `b`.

### 11.2 UC3 — discrimination ✓ (L green vs M brown, same recipe 4 ml + 3 drops, 4 runs each)
| metric | L green | M brown (mean±spread) | separation / within-oil noise |
|---|---|---|---|
| **A_blue** | 0.365 | 0.213 ± 0.008 | **−42%, ~20× noise** |
| **Browning ratio** | 2.92 | 1.98 ± 0.08 | **−32%, ~12× noise** |
| raw intrinsic hue | 289 | 281 ± 1.6 | 8°, ~5× |
| baseline hue | 300 | 295 ± 2 | 5°, ~2.6× (weak) |
| D_Q | 0.155 | 0.140 | −10%, weak |
| Greenness | 1.23 | 1.30 | **inverted** |

The oils **separate unambiguously** — `A_blue` / Browning ratio split by **12–20× the within-oil scatter**. With
§11.1, the **Browning ratio is the primary discriminator: dilution-invariant AND separating.**

### 11.2a PB-band re-analysis — the new **Pigment ratio (Soret/Q)** wins (all 16 K/L/M/N runs, 2026-07-22)

Re-computed the **V3 PB-band metric** (§2.1 / §8.3) directly from the spectral data embedded in every K/L/M/N PDF
(`workflow.json` → PROCESSING absorbance → median-k7 despike → band **means** on 440–460 Soret / 560–580 Q /
510–540 clarity). Grouping **green = K,L · brown = M,N** (2×2: K/N = 2 drops, L/M = 3 drops).

| metric (despiked, means) | green K,L | brown M,N | \|Δ\| | **Δ / within-group noise** |
|---|---|---|---|---|
| Soret 440–460 alone | 0.79 ± 0.22 | 0.50 ± 0.08 | 0.29 | 1.9 |
| Q 560–580 alone | 0.21 ± 0.06 | 0.20 ± 0.03 | 0.00 | ~0 |
| **Pigment ratio = Soret / Q** | **3.83 ± 0.13** | **2.41 ± 0.08** | **1.41** | **13.5 — best** |
| Pigment ratio · clarity (Soret/510–540) | 8.44 ± 0.60 | 5.12 ± 0.32 | 3.32 | 7.2 |
| legacy Browning≈ (450–490 mean / clarity) | 3.07 ± 0.11 | 1.88 ± 0.11 | 1.19 | 10.7 |

- **The Pigment ratio (Soret/Q) is the strongest discriminator of all** — Δ/noise ≈ **13.5**, beating the legacy
  Browning ratio (10.7) and the Soret/clarity safety net (7.2). The clusters are **fully non-overlapping**: worst
  green **3.67** > best brown **2.59**, a gap of **1.08** against within-group scatter of ~0.1.
- **Dilution-invariant too:** green K(2drops) 3.89 ↔ L(3drops) 3.76 (**3.3 %**); brown N(2drops) 2.35 ↔ M(3drops)
  2.48 (**5.4 %**) — both far below the 1.41 between-oil gap. So Soret/Q is dilution-invariant AND separating.
- **Why Soret/Q works (physics):** both bands scale with pigment concentration (Beer–Lambert), so the ratio cancels
  dilution and isolates the pigment *shape*; green vs brown differ strongly in the Soret-to-Q balance (fresher
  pigment → relatively more Soret). The Q denominator is nearly identical *between* groups (0.21 vs 0.20), so the
  separation is driven almost entirely by real Soret signal.
- **⚠ Rubber-duck reversal (§8.3):** the pre-registered worry that the weak 560–580 Q denominator would make the
  ratio jumpy is **not borne out on K/L/M/N** — over a 20-nm despiked mean the Q band is stable enough that Soret/Q
  is the *tightest* of the three. The §8.3 "watch" is downgraded to **verified fine on K/L/M/N; re-confirm on the
  3rd oil.**
- **Caveats:** still only **two oils** (3rd "too-green" oil pending for a 3-cluster proof); the "legacy≈" row uses a
  plain band mean, not the plugin's reference-gated `A_blue`, so it is indicative — the Soret/Q and Soret/clarity
  rows are exact.

### 11.2b Colour discriminates via CHROMA, not hue — and a §11.2a correction (2026-07-22)

The white-point complement (§8.4) gave *identical* intrinsic-perceived hues (~67°) for green and brown, even though
the absorbed colours looked like they differed. Resolved by measuring the absorbed chromaticity as **angle + distance
from the D65 white point** across all 16 runs:

| | angle from white | chroma (distance from white) |
|---|---|---|
| green (K,L) | **245.5° ± 0.4°** | 0.234 ± 0.006 |
| brown (M,N) | **245.4° ± 0.2°** | 0.198 ± 0.005 |

- **Same hue, different chroma.** Every run sits at the same angle (245.5°) — one hue direction. What separates the
  oils is the **distance from white** (green more saturated, brown washed toward grey), **Δ/noise ≈ 6.5**, and it is
  dilution-invariant (xy is scale-invariant).
- **Why the perceived hue is identical:** the complement is a reflection through white — a rigid motion that preserves
  *direction*. Same absorbed angle → same complement angle (~65.5°) → same hue. The chroma difference survives, but
  the **hue-normalized chips fix S/L and discard it**, so the normalized chips look identical.
- **§11.2a correction:** the "~12° absorbed *hue* separation" reported there was a **gamut-clamp artifact** — the
  absorbed blue-violet is far outside sRGB (blue channel 1.4–1.6), and clamping folds same-hue/different-chroma
  colours to slightly different *HSL* hues. In the honest xy space the angle is identical; the real colour separator
  is **chroma**, of which the `Pigment ratio` (3.8 vs 2.4) is the numeric face.
- **Physics:** same pigment family (protochlorophyll/protopheophytin) → same band positions → same hue; browning
  degrades the pigment *amount*, moving the absorbed colour toward grey (lower chroma) without rotating its hue.
- **Practical:** for a *visible* colour discriminator, use a **natural-chroma** chip (green = richer amber, brown =
  paler), not the hue-normalized one; or read the `Pigment ratio`. The GO verdict is unaffected.

### 11.3 Metric hygiene (SETTLED)
- **Primary: Browning ratio** (`A_blue/A_green`) — invariant + separates.
- Secondary: `A_blue` (strongest split but dilution-DEPENDENT — trust only at matched concentration) + **raw/de-spiked hue**.
- **DROP for discrimination:** Greenness (inverted here), `D_Q` (weak + under-scales), and the **baseline-corrected
  hue** — the clamp/over-compression HALVES colour discrimination (raw hue 8°/5× vs baseline 5°/2.6×, now validated on
  DISTINCT oils; the earlier-retracted concern is REAL on clean data). Colour *discrimination* = **raw/de-spiked hue**;
  colour *stability* comes from warm camera + settled sample + high concentration, NOT the baseline. The **Lab / gamut-
  clamp rabbit-hole is DROPPED** (§10.5) — it was never the bottleneck.
- **⚠ DIRECTION IS INVERTED vs the metric name:** the greener/fresher oil absorbs MORE blue (`A_blue` 0.37 vs 0.21) →
  HIGHER Browning ratio. So "Browning ratio — higher = more browned" is **BACKWARDS**; it is really a **freshness /
  green-pigment index**. Rename (metric + tooltips) when the plugin is next touched.

### 11.4 Sample clearing (blue-weighted turbidity)
Within a session the absolute `A_blue` and Browning ratio drift DOWN ~7–10% over ~20 min (both L and M), while
`A_green` / `D_Q` / hue hold. `A_blue` drops FASTER than `A_green` ⇒ the drift is **turbidity / scatter — blue-weighted
(∝ 1/λ⁴)** — clearing as the sample settles; NOT evaporation (would RAISE `A`) nor the (warm) camera. **Let the sample
settle (`A_blue` stops falling) before the definitive capture** — §7.3 "dissolve cleanly", now quantified (~10% of the
Browning ratio is unsettled turbidity).

**The BROWN oil carries MORE scatter than the green (N-series, 2026-07-21).** Its dilution-invariance is measurably
weaker: brown Browning ratio M(3 drops) ~1.90 ↔ N(2 drops) ~1.79 (~7–8%, both settled, 4 runs each; more dilute →
lower ratio as the residual `b` pulls it toward 1), and the absolutes scale **non-uniformly**
(`A_blue` ×0.73 vs `A_green` ×0.80) — vs the green oil's clean ×2.04 / ×2.06 and 1% ratio invariance (§11.1).
Non-uniform scaling = a **residual additive `b`**, physically the degraded/roasted oil's higher **turbidity /
particulate scatter** (a blue-weighted `b` that doesn't cancel in `S/R`; possibly incl. an undissolved dirt speck).
So scatter is a real, **oil-dependent** property — worse for degraded oils — and settling longer (and/or a quick
filter) tightens the brown oil's invariance. It does NOT threaten discrimination (§11.6).

### 11.4a Settle-time dependence & the mandatory timing protocol (2026-07-24 — the §11.4 effect, run to 11 h)

**The observation (Edwin, rig).** The *same* green Steirerkraft (Spar Steirerkraft g.g.A) cuvette measured
**~3.66** in the afternoon (O/P series) read **4.57** when re-measured **~11 h later**, and within that evening
session it climbed **4.0 → 4.58 over a few minutes**. The **brown S-Budget** (Q/R) was **unchanged** afternoon
→ evening. Room temp had dropped 26 °C → 24.5 °C. **Stirring the aged cuvette brought it straight back to 3.82.**

**Diagnosis (from the embedded `workflow.json` of `now.pdf` vs O/P).** *Not the instrument* — the reference
spectra overlay exactly (blue/green balance 1.271 vs 1.275). The **sample cleared**: the absorbance drop is
strongly *wavelength-dependent* — deep Soret **A(440) −17 %** (0.873→0.727), the weak **510–540 valley ~−50 %**,
the **Q 560–580 −36 %**. The fractional loss is biggest where the signal is *smallest* (the scatter-dominated
valley/Q) and smallest where pigment dominates (440) — the fingerprint of **turbidity settling out of the beam,
pigment largely intact.** As the baseline under the weak Q denominator falls, **Soret/Q inflates** (3.66→4.57);
the Soret/clarity safety-net inflates the same way (7.05→10.79), so it does *not* rescue it — both denominators
clear.

**Mechanism.** A fresh oil-in-isopropanol dilution is a **cloudy dispersion**, not a true solution (oil droplets
+ micro-particulate, denser than IPA ρ≈0.92 vs 0.79 → they **sink**). Freshly mixed = fine droplets → **very slow
Stokes settling (v ∝ r²)** → kinetically stable, steady readings. Over hours the droplets **coarsen** (coalescence
+ Ostwald ripening) → settle *faster*, and the scatter leaves the light path → baseline drops → weak Q collapses
toward the floor. So the **settling rate accelerates with age**; and an aged cuvette, once disturbed
(handling/insertion), re-suspends coarse sediment that re-settles in **minutes** — which is exactly the observed
4.0 → 4.58 minutes-scale climb (the ratio *chasing* the clearing in real time). The colder room may assist
clearing, but the dominant variable is **settle time**, not temperature or the sensor.

**Why green and not brown.** The green oil has a **real but weak** Q-band pigment feature riding on the turbidity
baseline; when the baseline clears, that weak denominator collapses and the ratio swings. The brown oil's bands
already sit on the floor (degraded pigment, §11.5) → no differential → its ratio is stable regardless.

**⚠ Danger for the gate / Ampel (record).** A **cleared / over-settled green sample reads a HIGHER S/Q — i.e.
"greener / fresher" — the WRONG direction.** The Pigment ratio is trustworthy **only while both bands sit well
above the measurement floor**; once the sample over-clears (or is too dilute / degraded), the weak Q denominator
falls to the floor and the ratio inflates. Stirring recovered it (4.57→3.82), confirming settled scatter (not
pigment loss) and giving a free discriminating test: re-suspend → if the ratio drops back, it was clearing.

**MANDATORY measurement protocol for the pigment-ratio metric (green oils):**
1. **Agitate GENTLY** (a swirl, not a vigorous stir) immediately before every capture. Vigorous stirring
   *coarsens* the droplets faster and whips in **microbubbles** — both add scatter noise.
2. **Wait a fixed short settle** — the *same* each run (~60–90 s: long enough for bubbles to clear, short enough
   that the dispersion is still present).
3. **Capture**, and **measure fresh, within the first ~1 h** — the kinetically-stable window (fine droplets,
   slow reproducible settling).
4. **Do NOT re-stir an aged sample — discard and re-prepare.** Once the sample has aged (~2 h → ratio drifts up
   to ~4.9, §11.4c), stirring is **unreliable**: it re-suspends *coarse, fast-settling* droplets (which re-clear
   in seconds) + bubbles, so the reading lands anywhere — **sometimes lower, sometimes even higher** than
   before. Coalescence and any pigment oxidation are irreversible; stirring cannot restore a fresh state.
   **⚠ "the stir made it worse" is itself the age indicator** — treat that inconsistency as "sample too old,
   re-prepare." (Rig, Edwin 2026-07-24.)
5. **Keep the Soret band-mean ≳ 0.5** (enough oil, without saturating the 440 Soret toward the 1.5 ceiling) so
   the weak Q stays above the floor; **cap/seal the cuvette** over longer sessions to limit evaporation drift;
   **log the settle time + room temperature** with each run.

Caveat: the "first ~1 h is flat" part is *inferred* from the physics — the afternoon O/P runs span only ~35 min
and were each freshly handled, so part of their stability is consistent timing, not proof of an undisturbed hold.
Testable directly: fresh prep, measure every ~15 min undisturbed over 2–3 h and watch the drift rate grow.

### 11.4b Floor-subtracted metric TRIED and REJECTED — raw Soret/Q wins (2026-07-24)

The §11.4a floor-sensitivity (the weak Q denominator riding on a variable turbidity floor) motivated testing a
**floor-subtracted** ratio `(Soret − clarity)/(Q − clarity)` — subtract the 510–540 clarity band from both
windows before dividing. Computed on **all 32 K/L/M/N/O/P/Q/R runs** (despiked band means; green = K,L,O,P ·
brown = M,N,Q,R):

| metric | green | brown | **Δ / noise** | gap (worst-green → best-brown) |
|---|---|---|---|---|
| **raw Soret/Q** | 3.75 ± 0.13 | 2.47 ± 0.11 | **10.8** | +0.91 |
| floor-sub `(S−c)/(Q−c)` | 6.38 ± 0.27 | 3.97 ± 0.32 | **8.1** | +1.20 |

**Floor-subtraction is WORSE, not better.** Δ/noise drops **10.8 → 8.1** and the within-group scatter roughly
**doubles** (green sd 0.13 → 0.27). Reason: subtracting the floor removes the *stabilizing bulk* of the already-
weak Q band, leaving a tiny, noisy denominator (`Q − clarity` ≈ 0.05–0.07); dividing by that **amplifies** noise.
Keeping the floor *in* the denominator (raw Q ≈ 0.14) is the more stable choice. **It also does NOT fix the
settle-state drift** — tonight's Steirerkraft under floor-sub is still high vs afternoon (afternoon 6.58 → fresh
6.83–7.44, over-settled 7.18). **Decision: keep the raw Soret/Q Pigment ratio; do not adopt floor-subtraction.**

**Silver lining — the drift does NOT break the verdict.** The settle-state clearing pushes a green oil **UP**
(3.7 → 4.5), i.e. *further above* the 2.8 threshold, never toward "brown." So the coarse green/brown Ampel call
is safe; the drift corrupts only the **absolute value** (fine gradation, threshold-calibration). The one residual
risk is a *genuinely borderline* oil near 2.8 that clears and tips over the line — so **borderline samples need
the §11.4a protocol most.** Net: raw Soret/Q + a pinned agitate-then-fixed-settle protocol is the recommendation;
a metric change is not the fix.

### 11.4c Why the sample settles/clears — the physical chemistry (2026-07-24)

The measured "drift" (§11.4/§11.4a) is not chemistry going wrong; it is the **physics of a fine dispersion
settling**. The full picture, for the record:

- **It is a dispersion, not a true solution.** Isopropanol (2-propanol) is *semi-polar* — a polar –OH on a small
  nonpolar isopropyl group — while pumpkin oil is a **nonpolar triacylglycerol**. Oil is only *partially*
  miscible in IPA, so a few drops in a few mL **exceeds solubility** and forms a **cloudy emulsion**: tiny oil
  droplets + micro-particulate (waxes, phospholipids, seed sediment) suspended in the solvent. The **pigment**
  (protochlorophyll/pheophytin — moderately polar tetrapyrroles) *does* dissolve — that is the real absorbance
  signal — but the suspended oil/particulate **scatters** light, which is the turbidity baseline.
- **Density → it sinks (sediments, not creams).** Oil ρ ≈ 0.92 g/mL vs IPA ρ ≈ 0.785 g/mL (Δρ ≈ 0.13). The
  denser droplets/particulate fall to the **bottom**, below the beam path in the middle of the cuvette.
- **Brownian motion = the "kinetically stable at first" part.** Freshly mixed, the droplets are *tiny*; thermal
  (Brownian) jostling overwhelms the small gravitational pull, so the fine fraction stays suspended → readings
  are steady for a while.
- **Stokes' law = why the rate accelerates.** Terminal settling velocity `v = (2/9)·Δρ·g·r²/η` scales with the
  **droplet radius squared**. Fine droplets settle glacially; as they grow, settling speeds up nonlinearly.
- **Coarsening over hours** grows the droplets — **coalescence** (droplets collide and merge, with no surfactant
  to stabilise them) and **Ostwald ripening** (oil's slight IPA-solubility lets molecules diffuse from small,
  high-curvature droplets to large ones). Bigger droplets → faster settling → the **stable-then-accelerating**
  clearing seen on the 11 h sample and even minute-to-minute after handling (§11.4a).
- **Optical effect.** As scatterers leave the beam, the **turbidity baseline drops**; the weak Q pigment band
  rides on that baseline, so it collapses toward the floor and **Soret/Q inflates** — the whole §11.4a effect.
- **Temperature is a secondary modulator.** Lower T *raises* viscosity η (Stokes → slower settling) but *lowers*
  oil/wax solubility (more comes out of solution) and shifts the emulsion balance. Net small; the dominant
  variable is **elapsed settle time**, not the 1–2 °C room swing.
- **Why NOT the intuitive opposite (darkening/clouding).** Oxidation is slow (days, and it degrades pigment, it
  doesn't clear scatter); evaporation would *concentrate* the sample → *raise* A (wrong sign); fresh
  precipitation would *add* scatter → cloudier (wrong sign). Over ~hours the **physical sedimentation of the
  initial dispersion wins** over every darkening process — the sample goes *more transparent*.

**Consequence:** this is exactly why the §11.4a protocol (**agitate → fixed short settle → capture; measure
fresh, don't reuse an aged cuvette**) is mandatory, and why the raw ratio carries a settle-state wobble. It is
also why *stirring recovered* the aged sample (§11.4a) — re-suspending the sunken scatterers restores the
baseline. Nothing here is instrument or pigment failure; it is colloid physics.

### 11.4d Why *the green oil* needs a fresh sample — matched vs mismatched bands

The freshness requirement (§11.4a) is not symmetric: it bites the **green** oils and barely touches the brown
one. The reason is structural, and it explains itself once you see each band as two stacked contributions:

> **Every band reading = real pigment absorption + haze** (the broadband scatter baseline from the turbidity,
> §11.4c). Over time the haze **settles out of the beam**, so its contribution shrinks; the dissolved pigment
> stays.

**Principle — haze is a bigger *share* of a band when the pigment there is weak.** A band with strong pigment
absorption is mostly real signal, and the haze is a minor add-on; a band with weak pigment absorption is
*mostly haze*. So how much a band's reading moves when the haze clears depends on how pigment-rich that band is.

**The ratio only drifts when the two bands are *mismatched*.** The metric is Soret ÷ Q, and clearing acts on the
**ratio**, not on each band alone:
- **Two haze-dominated bands (matched)** → the haze rides on top of *both*; when it clears it shrinks numerator
  and denominator by the *same fraction*, and in the division it **cancels**. Each band's absolute value falls,
  but the ratio holds. (Same math that makes the metric dilution-invariant — a common factor cancels.)
- **One pigment-strong band ÷ one haze-dominated band (mismatched)** → clearing removes the haze mostly from the
  *weak* band; numerator and denominator move by *different* amounts, so nothing cancels and the **ratio drifts**.

**Applied to the two oils:**
- **Brown oil = two faint bands (matched).** Its pigment is degraded (§11.5), so pigment absorption is weak in
  *both* the Soret and the Q window — both are haze-dominated. Settling clears the haze from both equally → it
  cancels in the ratio → the ratio is **robust to age** (≈2.5 the whole time), even though each band's absolute
  absorbance drops. The brown oil is *forgiving*.
- **Green oil = one strong band ÷ one faint band (mismatched).** Fresh green oil has a **strong Soret pigment**
  (numerator ≈ real signal, haze a minor share — deep A(440) barely moved, §11.4a) but a **weak Q pigment**
  (denominator ≈ half haze: Q-pigment ≈ 0.067 ≈ the baseline ≈ 0.07). Clearing drains the haze mostly out of the
  weak Q denominator while the strong Soret numerator holds → the two move differently → the **ratio inflates**
  (3.7 → 4.6 over 11 h). The green oil is *susceptible*.

**Consequence.** The green oil's ratio is only trustworthy while its Q band still has its *fresh* haze+pigment
level — i.e. **measured fresh, at a fixed settle state** (§11.4a). The mismatch is intrinsic to a *fresh, high-
pigment* oil (that is exactly what a strong-Soret / weak-Q oil is), so it cannot be removed by a metric tweak
(floor-subtraction made it worse, §11.4b) — only by the protocol. The brown oil needs no such care because its
matched bands make the ratio self-cancel. **Net: freshness discipline is a green-oil requirement; the metric's
own dilution-invariance protects the brown one for free.**

### 11.4e ✅ SOLVED — why the 2023 oils separated 8× better: they were CLEARER  *(Edwin's hypothesis, measured 2026-07-31)*

§16.10's amendment left this open: *"the 2023 set gave d ≈ 10; today's fresh oils give d = 1.24 on the raw ratio
… that 2023-vs-2026 gap has no explanation yet, and the capability claim currently leans on the larger number."*
**Edwin's explanation — the 2023 oils were bought in 2023 and are physically old — is correct, and it is
measurable.**

**Old oil is CLEAR oil.** §11.4c's dispersion settles in the *bottle* just as it does in the cuvette: three years
lets the waxes and particulate drop out, so an aged oil carries far less turbidity into the dilution. That is
directly quantifiable as the **pedestal** — the additive scatter floor under the whole absorbance curve,
recoverable from the two metric variants as `c/Q_true = (baselined − raw)/(raw − 1)`
(`diagnostics/pedestal_by_vintage.py`):

| fill | oil vintage | **pedestal** | raw CV |
|---|---|---|---|
| K green | 2023 | 0.95 | 3.92 % |
| L green | 2023 | 1.04 | 2.43 % |
| M brown | 2023 | 0.67 | 3.32 % |
| N brown | 2023 | 0.69 | 0.50 % |
| B green | 2026 | 1.84 | 16.64 % |
| E green | 2026 | 1.94 | 7.92 % |
| C brown | 2026 | 1.70 | 11.38 % |
| D brown | 2026 | 1.41 | 22.24 % |

**2023 oils: pedestal 0.84 ± 0.19. 2026 oils: 1.72 ± 0.23 — 2.1× more scatter, with no overlap between the two
groups on a single fill.** Pedestal vs raw CV correlates at r = 0.65 across all eight.

#### The gap decomposes into two ORDINARY problems, not one frightening one

| half | 2023 → 2026 | cause | fixable by |
|---|---|---|---|
| **precision** | raw CV 2.54 % → 14.54 % | **turbidity — confirmed above** | butanol (`SPEC_capture_quality.md` §16.12.7), filtering, or the rig rebuild |
| **separation** | Soret/Q ratio 1.96× → 1.36× | the two oil **pairs** are differently far apart | **more oils** |

⚠ **The second half is NOT evidence that the effect fails to transfer.** It is evidence that a **2-vs-2 panel
cannot pin down class separation at all** — 1.96× vs 1.36× is the ordinary spread of picking two different pairs.
That is the panel-breadth gate (§11.6), now quantified instead of feared.

#### ⇒ The consequence, and it is encouraging

**Clearing the oil is worth roughly 6× in discriminating power.** The 2023 oils, at half the pedestal, delivered
**d = 24.25** against the 2026 oils' **2.88**. This is an *observed* instance of "halve the pedestal, d rises
several-fold" — not a projection. **It is the strongest evidence available that
`SPEC_capture_quality.md` §16.12.7's butanol route is worth running**, because butanol is meant to do chemically
and immediately what three years in a bottle did by sedimentation, and to do it more completely (it dissolves
waxes that would never settle).

It also reframes the risk register: the item flagged in §16.10 as *the* thing that could kill the concept now has
an explanation, and **neither half of it is fatal** — one has three independent fixes (one already delivered by
the rebuild), the other is the confirmatory oil-panel work that was always the known gate.

#### ⛔ WITHDRAWN in the same session — the "mechanism inversion"

While chasing this I claimed the *discriminating mechanism had inverted* between the two eras, because the 2026
brown's raw `A_Soret` (1.117) exceeds the green's (0.950) where in 2023 green led 0.785 to 0.494.

**That was an error: I compared unnormalised band means across preparations at different concentrations.**
Normalising by Q — which is exactly what the metric does:

| | Soret/Q green | Soret/Q brown | green ÷ brown |
|---|---|---|---|
| 2023 oils | 6.64 | 3.38 | **1.96×** |
| 2026 oils | 12.12 | 8.88 | **1.36×** |

**Green leads brown in both eras, by the same mechanism.** Nothing inverted; the 2026 brown simply sits at a
higher concentration, which lifts all of its absolute band means together. §11.5's physical story stands
unchanged. *(Recorded per §16.7.0's practice — the claim was made, and it was wrong.)*

### 11.4f 📌 PRE-REGISTRATION — predictions for series D/E and the butanol trial  *(written 2026-07-31, BEFORE the measurements)*

**What "pre-registration" means here, and why it is worth the page.** Every number below is written down
**before** the runs that will test it. Once data exists it is very easy — and completely unconscious — to decide
after the fact which analysis was the intended one, which run was an outlier, and which prediction we "really"
made. §16.10.16 named that trap and this spec has fallen into it twice already (`SPEC_capture_quality.md`
§16.12.14's headline, §11.4e's withdrawn inversion). Writing the predictions and the **pass/fail criteria**
first converts the next session from a *fit* into a *test*: whatever comes back, we already know what it means.

**Rules of the game:** these numbers are not to be edited after the data lands. If a prediction is wrong, it is
marked wrong and the reason recorded — that is the point of having made it.

#### A · Series D — brown, 6 re-seats of one fill, post-rebuild, still isopropanol

| quantity | today | **predicted** | basis |
|---|---|---|---|
| within-fill CV, `S/Q linear base` | 9.79 % *(pre-rebuild)* | **2.5 – 3.5 %** | brown and green had **identical** pre-rebuild noise (9.79 vs 9.72), so the rebuild's 3.33× should transfer |
| within-fill CV, `S/Q raw` | 11–22 % *(pre-rebuild)* | 3 – 8 % | same, minus the pedestal term which the rebuild does not touch |
| settling trend over ~30 min | unmeasured on brown | −3 to −8 % | green showed −5.4 / −6.9 % |

**PASS** = brown within-fill CV ≤ 3.5 %. **FAIL** = ≥ 6 %, which would mean the rebuild does *not* transfer and
brown carries an oil-specific noise term the mechanics cannot reach.

##### ✅ SCORED 2026-07-31 — series D ran the same day. **PASS.**

*Full account: `SPEC_capture_quality.md` §16.13. Per the rules above, the predictions stand as written.*

| predicted | measured | |
|---|---|---|
| within-fill CV `S/Q linear base` **2.5 – 3.5 %** | **1.41 %** | ✅ **PASS** on the criterion — ⛔ but the *range* is **wrong, low by ~2×**. The rebuild transferred to brown *better* than green's 3.33× |
| within-fill CV `S/Q raw` **3 – 8 %** | **6.00 %** | ✅ correct |
| settling trend over ~30 min **−3 to −8 %** | **−0.15 %** *(t = −0.08)* | ⛔ **WRONG.** Brown's *absorbances* settled harder than green's (`A_far` −39 %) and the shipped metric absorbed all of it — §16.13.4 |

**⇒ Discrimination: *d* = 11.13, brown clears T = 10.6 by 9.88 σ (4.03 σ at the 95 % upper bound on σ).**
*(That *d* uses the RMS pooled SD on unequal groups — 12 green runs against 6 brown. The conventional
df-weighted form gives **9.80**, and Hedges' small-sample correction **9.34**. All three are far past the
gate; quote the df-weighted figure externally. `SPEC_capture_quality.md` §16.13.5.)*
The gate's discrimination criterion is **met on re-seat data**; §11.4f B is now the only thing outstanding.

⚠ **Two honest qualifications.** (1) The comparable figure against green's 2.96 % is **1.58 % vs 1.89 %**
residual, not 1.41 % vs 2.96 % — green's raw CV is inflated by a settling trend brown did not have
(§16.13.3). (2) This is **one fill re-seated**; σ_fill is untouched.

#### B · Series E — brown, 6 separate fills, ~15 min equilibration each

| quantity | today | **predicted** | note |
|---|---|---|---|
| σ_fill, `S/Q linear base` | 10.5 % *(n = 2 fills, t = 1.47, **not significant**)* | **3 – 6 %** | the load-bearing unknown of the whole milestone |
| σ_fill, `S/Q raw` | 0.3 % *(n = 2)* | **1 – 4 %** | ⚠ see the split below |

##### ⭐ What each outcome in that range MEANS — derived 2026-08-01, before the data

*Not an edit to the prediction above — a derived consequence of it, written down first so the reading is fixed
in advance. Computed in `diagnostics/one_fill_decision.py`; full table `SPEC_capture_quality.md` §16.11.13.*

The gate rule is `T ± 2.576·σ₁`. Applied to the **measured** class means (green 12.251, brown 9.303), the
question "does ONE measurement decide?" has a sharp boundary — and brown is the binding class because it sits
closer to T (margin 1.297 against green's 1.651):

| series E returns brown σ_fill | one measurement decides | reading |
|---|---|---|
| **≤ 3.3 % CV** (σ ≤ 0.307) | **≥ 95 %** | ✅ adopt §16.11.13's inversion — one fill, ÜBERGANG fallback |
| 3.8 % | 85 % | marginal; probably still three fills |
| 5.4 % | 39 % | ⛔ keep "always three fills" |
| 10.5 % *(today's figure)* | 2 % | ⛔ unchanged, and prep is the dominant error term |

⚠ **The pre-registered 3–6 % range straddles that boundary exactly.** At its optimistic end one measurement is
enough; at its pessimistic end it is enough fewer than half the time. **There is no useful interpolation — the
outcome is close to binary**, which is the right property for a pre-registration to have.

**⇒ There is no failure mode, only a cost.** Small σ_fill → one measurement; large σ_fill → three fills, which
is exactly what ships today (`SPEC_capture_quality.md` §16.10.17b). The downside of series E is the status quo.

⚠ **The prediction that matters most, and it is a strange one.** On the two brown fills we have, the *raw* ratio
agrees to **0.3 %** while the *baselined* ratio differs by **10.5 %** — and green runs the other way (raw 2.8 %,
baselined 0.0 %). **Prediction: this split reproduces.** If it does, brown's "weak fill-to-fill" — the main open
risk on the milestone — is **an artifact of the correction, not a property of the oil**, and the mechanism is
§16.12.12's (the far anchor carries pigment; brown's far window is flat where green's rises, so the fitted slope
responds differently by class).

**⇒ Series E must report raw and baselined side by side.** If it only reports the shipped metric the question
cannot be answered.

#### B2 · ⭐ The ALIQUOT STEP — a σ_fill mechanism named *(2026-07-31, before series E)*

**The prep as actually performed** *(Edwin, clarified 2026-07-31)*: 18 ml isopropanol + 6 drops of oil are mixed
in a **lab glass**, and a **4 ml aliquot** is then transferred into the polystyrene jar that goes into the
instrument. The mixing vessel and the measurement vessel are different.

**⇒ The transfer is a SAMPLING step out of a settling dispersion, and it is currently uncontrolled.** While the
batch stands, the particulate sediments (§11.4c — oil ρ 0.92 against IPA 0.785, it sinks). *When* and *from what
depth* the 4 ml is drawn therefore decides how much scatterer travels into the jar. Off the top gives a clear
aliquot; drawn low or poured, a loaded one. Two fills from the *same stock* can differ substantially in pedestal
for no reason but draw timing and depth.

**This is now the leading explanation for the brown asymmetry**, and it fits the observed pattern where the
earlier candidates did not:

| | green | brown |
|---|---|---|
| fill-to-fill, `S/Q linear base` | **0.0 %** | **10.5 %** |
| particulate load (§11.4) | low | **high — brown carries more scatter** |

A draw-sensitivity mechanism predicts exactly this: green has little to settle, so its aliquot is nearly
insensitive to how it is taken; brown has much more, so it is not.

**Prediction: stirring the batch during the draw collapses brown's σ_fill.** A magnetic stirrer keeps the
suspension homogeneous, so the aliquot becomes representative regardless of timing or depth. That removes
draw-timing and draw-depth from the error budget entirely.

⚠ **Note this competes with §11.4f B's other pre-registered hypothesis** — that brown's fill-to-fill is an
artifact of the baseline correction (raw fills agree to 0.3 %, baselined differ by 10.5 %). **The two are
distinguishable and series E separates them:**

| series E outcome | reading |
|---|---|
| brown σ_fill collapses on **both** raw and baselined | **the aliquot step** — sampling, fixed by stirring |
| σ_fill stays ~10 % **baselined** but ~0 % **raw** | **the correction** — §16.12.12's far anchor, not fixable by prep |
| both stay high | neither; something else, and the milestone needs rethinking |

#### B3 · Confounds to control in series E

Six fills from one stock over a session introduces two drifts that would **masquerade as σ_fill** by putting a
monotone trend across the fills:

- **Evaporation.** An open 18 ml of isopropanol on a running stirrer concentrates over an hour — increased
  surface renewal, slight plate warming. Dilution invariance keeps the damage modest (green ~0.4 %, brown ~6 %
  per 50 % concentration change) but it is free to avoid. **⇒ Cover the beaker.**
- **Plate warming.** A warming stock dissolves more oil as the session runs, so the pedestal drifts *downward*
  across the fills — the same signature, opposite sign. **⇒ Use a non-heating stirrer**, and do not leave it
  running unnecessarily.

**⇒ Report the fills in time order** so either drift is visible as a trend rather than absorbed into σ_fill.
This is the same lesson as §16.12.11 A: a CV discards run order and a monotone drift then masquerades as
repeatability.

#### B4 · ⚠ A protocol decision to take DELIBERATELY before series E

**Stirred aliquoting is a different protocol from the hand-mixed one the historical 10.5 % came from.** If the
stirrer is used, series E measures the *new* protocol — which is the more useful number, since what matters is
what the shipping procedure achieves, not what a superseded one did.

**But it is then not strictly a test of B's pre-registered 3–6 %**, which was written against hand mixing.
Record which protocol was used. If the result surprises, one hand-mixed comparison session resolves it.

**The combination worth aiming at eventually: stir → aliquot → FILTER into the jar** (0.22 µm PTFE, §16.12.9).
Stirring makes the sample representative; the filter then removes the particulate that stirring deliberately
kept suspended. Neither alone gives both.

#### C · The butanol trial

> ⛔ **CANCELLED 2026-08-01 — the solvent programme is paused; see `SPEC_capture_quality.md` §16.12.7b.**
> Isopropanol stays. This trial is not scheduled and its predictions are not live. Kept on record because
> the reasoning still applies if series E/§11.4f D reopen the question.
>
> ⛔ **SUBSTANCE CHANGED 2026-08-01 — the predictions below were written for 1-BUTANOL and do NOT transfer.**
> 1-butanol is rejected on hazard (**H318, serious eye damage Cat 1**); the candidate is now **2-butanol**
> (`SPEC_capture_quality.md` §16.12.7a). Per §11.4f's rules the table is left exactly as written rather than
> quietly re-tuned — but 2-butanol is a **branched** alcohol whose solvency sits *between* isopropanol and
> 1-butanol, so **every "predicted" figure below is too optimistic for it**, and the last row is wrong
> outright: ε goes 17.9 → **≈16**, not 17.8, so band positions may shift **more** than 5 nm.
> **▶ Re-derive this table for 2-butanol before the trial runs, and pre-register the new numbers as C2.**

| quantity | today (IPA) | **predicted (1-butanol — SUPERSEDED, see above)** |
|---|---|---|
| **pedestal** `c/Q_true` | **1.72** | **≤ 0.9** *(f ≥ 0.5 — matching what three years of shelf-clearing achieved, §11.4e)* |
| `S/Q raw`, green | 5.4 | **7.3 – 9.1** |
| `S/Q raw`, brown | 4.1 | **5.5 – 6.7** |
| `S/Q linear base`, green | 12.4 | 12.4 – 13.5 |
| `S/Q linear base`, brown | 9.0 | 9.0 – 9.8 |
| within-fill CV, raw | 8.2 % | **2 – 4.5 %** |
| within-fill CV, baselined | 2.9 % | 1.6 – 2.4 % |
| brown σ_fill | 10.5 % | **2 – 4 %** |
| brown dilution error | +6.0 % | **1 – 2 %** |
| settling trend / 30 min | −6 % | **≈ 0** |
| band positions | — | **shift < 5 nm** *(ε 17.9 → 17.8, KB §8.4)* |

**The single sharpest test — raw and baselined must CONVERGE.** Green sits at 5.38 raw against 12.37 baselined,
and that entire factor of 2.3 *is* the pedestal by construction. Remove the pedestal and they must approach. No
free parameters; the convergence ratio reads `f` straight off.

**PASS** = pedestal ≤ 0.9 **and** raw/baselined converge. **FAIL** = pedestal unchanged, which would mean the
dispersion is not what the pedestal is made of and §8.2's chemistry is wrong.

#### D · Consequence if C passes — single-sample reliability  *(⛔ dormant: C cancelled, §16.12.7b)*

Using §16.10.17's rule `P = Φ(d/2)` with the class gap of 3.37:

| single-sample CV | d | P(correct call) |
|---|---|---|
| 9.5 % *(today's brown)* | 3.28 | **95 %** |
| 6.6 % | 4.72 | 99 % |
| **3 – 5 %** *(predicted)* | 6.2 – 10.4 | **99.9 – 99.99 %** |

**Predicted: single-sample reliability moves from ~1 error in 20 to ≤ 1 in 1 000.**

⚠ **This is P(above threshold), not P(the oil is good).** §16.10.17b's warning binds harder the better these
numbers get: whether 10.6 divides green from brown *in general* is a panel question that 4 oils cannot answer,
and no amount of precision substitutes for it. **The panel remains the gate.**

#### E · What would make us abandon the butanol route  *(⛔ dormant: C cancelled, §16.12.7b)*

- Odour unacceptable in a food premises *(a phone call, not an experiment)*.
- Crazing of a polystyrene jar on an overnight soak.
- Pedestal unchanged after the swap — the FAIL condition in C.

#### F · 📌 THE FOUR-OIL CAMPAIGN — pre-registered 2026-08-01, BEFORE the runs

> **⚠ This REPLACES series E as designed in §B above.** §B specified *six fills of one brown oil*
> (df = 5, one oil). Edwin's campaign instead spends the same effort on *two fills each of four oils*
> (df = 4, four oils). **The trade is a little statistical power for much better representativeness** —
> and it attacks the oil *panel*, which §16.10.17d says is what the threshold actually needs. §B's
> predictions for σ_fill still stand and are tested here; only the sampling design changes.

**Edwin's plan, recorded as stated.** Four oils, two fills each, replacing series E's single-oil design:

| step | oil | fills | note |
|---|---|---|---|
| 1 | **brown #1** *(today's, series D oil)* | series D **+ one fresh refill** (18 ml + 6 drops) | brown reaches 2 fills |
| 2 | **green #1** | B + C — **already done** | 2 fills, two dilutions |
| 3 | **green #2** *(new oil)* | series **U** + **V** | to be bought/prepared |
| 4 | **brown #2** *(new oil)* | two series | oil not yet purchased |

⇒ **4 oils × 2 fills = 8 fills.** Runs per fill as Edwin's existing practice (6 re-seats); see D3.

##### D1 Why this design is nearly as powerful as series E — the point that justifies it

Each oil's fill-pair contributes **1 degree of freedom** to a fill-to-fill variance. Four oils **pool to
df = 4**, against series E's df = 5 from six fills of one oil — and the pooled figure is *spread across four
oils*, so it is more representative of what a real sample does.

| design | df | 95 % CI on σ spans | to **prove** σ_fill ≤ 0.307 needs σ̂ ≤ |
|---|---|---|---|
| 2 fills, one oil | 1 | **71×** | 0.019 (0.21 % CV) — unattainable |
| **this campaign** | **4** | 4.8× | **0.129 (1.39 % CV)** |
| series E | 5 | 3.9× | 0.147 (1.58 % CV) |

⚠ **Step 1 alone therefore proves nothing about σ_fill** — two fills of one oil is df = 1. It is a
**falsification** test: a second brown fill landing far from 9.303 would be highly informative; landing close
is merely the absence of bad news. **The estimate only exists once the campaign completes.**

##### D2 Predictions — fixed now, not to be edited afterwards

| quantity | **predicted** | basis |
|---|---|---|
| brown #1, fill-2 mean | **9.0 – 9.6** *(within ~3 % of 9.303)* | series D's mean survived a rig rebuild *and* a different oil to −0.62 % |
| **pooled σ_fill, `S/Q linear base`** | **2 – 5 % CV** | between series D's 1.41 % re-seat and the historical 10.5 %; §11.4f B predicted 3–6 % for brown alone |
| green #2 vs green #1 class means | within **10 %** | oils of the same class differ, but far less than the 33 % class gap |
| **any oil crossing T = 10.6 against Edwin's own read** | **none** | if one does, the threshold — not the instrument — is wrong |
| the raw-vs-baselined split of §11.4f B | **reproduces** on brown, absent on green | unchanged prediction, now testable on 2 brown oils |

**PASS** = pooled σ_fill ≤ 3.3 % CV ⇒ adopt §16.11.13's one-fill protocol.
**FAIL** = ≥ 6 % ⇒ keep the three-fill protocol; prep dominates and §11.4f B2's aliquot work becomes the priority.
**Between** = point estimate favourable but unproven at df = 4; decide on the operational cost, not the statistics.

##### D3 Design details that matter

- **Runs per fill.** σ_fill is estimated from the scatter of fill *means*, so re-seat noise enters as
  σ_reseat/√n: at n = 1 it contributes 18 % of the variance budget, at n = 3 **6 %**, at n = 6 **1.5 %**.
  Edwin's habitual 6 runs is statistically the best of the three; **3 would be an acceptable time-saver**.
  Whatever is used, **record it** — the analysis must subtract the re-seat term.
- **⭐ Record Edwin's own verdict for each oil BEFORE measuring it** (§16.10.17c's operator pre-read).
  Without it the campaign yields four oils and four numbers; with it, four oils with **independent ground
  truth** — which is what turns it from a precision experiment into a threshold-validation one. Costs nothing.
- **Confounds** carry over unchanged from §11.4f B3: cover the beaker (evaporation), non-heating stirrer,
  and **report the fills in time order** so any drift shows as a trend rather than inflating σ_fill.
- **Report raw and baselined side by side** (§11.4f B), else the split prediction cannot be tested.

##### ⭐ D3a AMENDMENT 2026-08-02 — prepare each oil as a SERIAL DILUTION, not two fills at one strength

*Added after the fact, and flagged as such per §11.4f's rules. **No prediction above is edited** — this
changes only how the remaining fills are prepared, and it is strictly additive to what D1–D3 measure.*

The campaign as written gives each oil **two fills at the same nominal strength**. That estimates
σ_fill, which is what it was designed for, and it says **nothing** about the pedestal residual `r_Q`
— because two preparations at one strength span ~1.1× in `B_Q`, and
`SPEC_capture_quality.md` §16.16.2 shows that geometry returns `se(r_Q)` ≈ 0.022, i.e. an interval
that contains zero. **Steirerkraft was already run that way and produced exactly that non-result.**

**⇒ Prepare each oil as a serial dilution instead** — one stock at 18 ml + 6 drops, then 1 : 1 and
1 : 1 again, 4 runs at each of the three points (§16.16.5). Same rig time. It still yields the
preparation-to-preparation comparison the campaign wanted, **and** adds a per-oil `r_Q` at
`se` ≈ 0.002.

**Why it is worth the change:** `r_Q` turned out to be the term that makes the shipped verdict depend
on how the sample was prepared (§16.15.7), and whether it is one instrument constant or a per-sample
property is currently unanswerable. **Four independent `r_Q` values settle it outright** — no amount
of further work on a single oil can. §16.16.6's three protocol controls (fixed stir-to-measure
latency, per-run turbidity log, **non-monotone measurement order**) apply to every oil.

⚠ **This does not relax D3's other requirements** — runs per fill, the operator pre-read, the
confound list and the raw-vs-baselined reporting all stand unchanged.

##### D4 ⚠ What this campaign will NOT settle

**It closes the precision half and not the threshold half.** All four oils are expected to be *clearly* green
or *clearly* brown. Such a panel confirms **that the classes separate**; it cannot show **where the boundary
belongs**, because nothing sits near it. `T = 10.6` would still rest on judgement (§16.10.17d).

**⇒ One oil that Edwin would call *borderline* is worth more to this milestone than another clear one.** If
such a sample can be obtained, it should replace one of the clear oils rather than be added to them.

### 11.5 Physical interpretation — why it works, and why the brown oil looks reddish
`A_blue` reads the **green chlorophyll-type pigment content** (its Soret band ~430–470 nm). Fresh/green oil = high
pigment = high `A_blue`; roasted/aged brown oil = **degraded pigment = low `A_blue`**. This is **pigment degradation,
NOT Maillard browning** — the **Maillard reaction** (amino acids + reducing sugars + heat → brown *melanoidins* +
roasted flavour; what browns roasted seeds, coffee, toast) would *add* broad blue absorption (`A_blue` UP), but it
went DOWN. So the discriminator has real chemical meaning (pigment / freshness), not just a statistical split.
**The reddish bulk appearance fits:** pumpkin-seed oil is **dichromatic** — thin/dilute → green, thick/bulk → red —
because the green pigment leaves a narrow green transmission window that collapses to red as path length grows;
degrade the pigment and the amber/red base shows through → browner/reddish in bulk. (The *diluted* transmission hue
barely moves, 70↔73, because the red is a thick-layer effect not seen in the thin cuvette; `A_blue` captures the
*cause* even in the thin sample — which is why absorbance beats perceived colour as the discriminator.)

### 11.6 Status & remaining
- **UC1 repeatability ✓** (warm + settled + concentrated → intrinsic hue ~1°, ratios ~few %).
- **UC2 dilution-invariance ✓** — clean for the green oil (Browning ratio K↔L 1%); **weaker but adequate for the
  brown** (M↔N ~8%, residual scatter `b`, §11.4). Discrimination is **robust across dilution regardless**: brown
  clusters ~1.8–2.0 (2 & 3 drops), green ~2.9–3.1 — the green↔brown gap (~1.0) dwarfs brown's dilution wobble (~0.13).
- **UC3 discrimination ✓ green↔brown** (Browning ratio, `A_blue`) — and confirmed dilution-robust by the N-series.
- **Freshness-protocol repeatability ✓ green (Edwin 2026-07-24):** with the §11.4a discipline (fresh sample +
  uniform dilution) the green Steirerkraft oil held a **small ratio variance across 5 runs** (afternoon + evening),
  confirming the protocol is the antidote to the §11.4d susceptibility. **Brown ×5 in progress** (2 fresh + 1 at
  +11 h already ≈2.5; 2 more fresh due) — §11.4d predicts the brown is *age-robust* (matched faint bands), so its
  5-run spread should be tight without special care.
- **Scope narrowed to binary good-green vs over-roasted-brown (§1a, Edwin 2026-07-24)** — the too-green class and
  the fine green-ranking are dropped, which **retires two of the old three remaining items.**
- **REMAINING for the gate — ONE confirmatory item (Edwin 2026-07-24):**
  1. **Broaden the oil panel — TODO.** The conclusion rests on **2 brown (~2.5) + 2 green (~3.5)** oils. It is
     almost certainly not a coincidence — **price, perceived colour, and the measured ratio all agree** (cheap
     commodity → brown → low ratio; better oil → green → high ratio; *walks like a duck*). To make it **safe**,
     measure the oils already on hand: **1 more brown + 4 more green** (each fresh, per §11.4a), turning 2-vs-2 into
     a broad multi-oil panel triangulated by three independent signals — removing the small-N doubt.
- **RETIRED (no longer gate items, per §1a):**
  - ~~third "too-green" oil~~ — the too-green class is dropped; only over-roast detection is the goal.
  - ~~a real amber-band sample~~ — practically there are no intermediate oils; the empty 2.6–2.8 middle is a
    rarely-occupied boundary, not a gap that must be exercised. (If a borderline oil ever turns up it *validates*
    the middle zone, but it is not required for GO.)
  - "no numeric thresholds" — **superseded**: the verdict threshold exists as the **Roast-Ampel 2.8 zone boundary**
    ([`SPEC_roast_ampel.md`](SPEC_roast_ampel.md)); finer roast-degree calibration is out of scope.
- **Verdict: GO on the core claim** — green↔brown separate cleanly (Δ/noise ~10.8, non-overlapping) and
  dilution-robustly, which is exactly the binary over-roast call the product needs. The one open item (broaden
  the panel) is **confirmatory strengthening of already-strong n=4 evidence**, not a risk to the outcome.

## 11.7 Deliverable — the one-page summary (artifact + PDF)

A stakeholder-facing one-pager distills §11 into a single scannable page: the GO verdict, the Browning-ratio
strip plot (two non-overlapping clusters), the 2×2 factorial table (K/L/M/N), seven takeaways, gate status, and
a **photo of the physical samples** (`SparPremioumAndHoferBellana.jpg` — upper row Hofer/commodity/brown, lower
row Spar/premium/green; dilution increasing left→right). The caption makes the sales point: at this dilution both
oils read pale amber to the eye, the eye's judgement drifts day-to-day and has no side-by-side reference, so the
instrument's fixed comparable number is the value-add.

- **Source (single self-contained HTML):** `scratchpad/capability_proof_summary.html` — inline CSS, no external
  assets (dual light/dark theme + an `@media print` block that forces the light identity, `print-color-adjust:exact`,
  A4). The sample photo is embedded as a **base64 `data:` URI** (resized to ~1400 px wide first) so it survives both
  the artifact CSP and the local-file PDF render. The strip-plot SVG must use **CSS classes** for fills, not
  `fill="var(--x)"` presentation attributes (SVG attrs don't resolve `var()`).
- **Published artifact (same URL on re-publish):** https://claude.ai/code/artifact/467cd564-f923-466b-8d9e-b4f311207b6c
- **PDF:** `spectracs-references/tmp/CapabilityProof_pumpkin-oil_summary.pdf`

**PDF recipe (reusable — HTML → PDF via headless Chrome):**

```
# 1. (if embedding a photo) resize + re-encode small, then base64 it into an <img src="data:...">
convert SparPremioumAndHoferBellana.jpg -resize 1400x -quality 82 oils_resized.jpg
#    base64 the jpg and inline it as  <img src="data:image/jpeg;base64,…">  (Python base64.b64encode)

# 2. render the self-contained HTML to A4 PDF (the @media print block in the HTML supplies A4 + colours)
google-chrome --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT.pdf" "file://$ABS_PATH_TO.html"
```

Notes: `--no-pdf-header-footer` drops Chrome's URL/date chrome; `@page{size:A4;margin:13mm}` +
`-webkit-print-color-adjust:exact` in the HTML's `@media print` do the page setup and force the swatch/oil colours
to print. The VAAPI stderr warning is harmless. Re-publishing the **same file path** in the same session keeps the
artifact URL stable; from another session pass that URL as `url=` or a new one is minted.

## 11.8 Deliverable — the colleague-facing *current-state* status report (PDF)

A short, non-technical **status report** for sharing the gate's standing with a colleague — distinct from the
§11.7 GO-verdict one-pager (that is the evidence artifact; this is the *"where do we stand"* narrative). It mirrors
the **Current state** executive summary at the top of this spec, in plain prose + three headline stats, and — its
distinguishing feature — **embeds the two live Roast-Ampel screenshots** to show the result already reaches the
user in a usable form: the everyday **Send-to-LIMS** verdict first ("what the miller always sees"), then the
optional analytical **Evaluation** gauge ("if interested in the detail").

- **Generator (single source of truth — do NOT hand-edit the PDF):**
  [`docs/tools/build_capability_status_pdf.py`](tools/build_capability_status_pdf.py). Self-contained: it
  base64-embeds the two screenshots (Pillow-resized/cropped) into an inline-CSS A4 HTML and renders via headless
  Chrome. One command regenerates it: `python3 docs/tools/build_capability_status_pdf.py`.
- **Output PDF:** `spectracs-references/tmp/Spectracs_CapabilityProof_status.pdf` (2 pages, A4).
- **To update** (evidence moved, UI changed, scope shifted): edit the copy/stats in the generator's HTML string;
  if the gauge UI changed, re-take the two Ampel screenshots and repoint `LIMS_IMG` / `EVAL_IMG` at the top of the
  script (the header docstring spells out which screen each is); re-run. The screenshots are the live app, so a
  UI-accurate refresh means re-shooting them — the script does the rest.
- **Provenance note:** keep this report's numbers in step with §11 and the top-of-spec Current-state section; all
  three tell the same story at different depths (report = shareable prose, Current-state = scannable tables, §11 =
  full data + provenance).

## 12. Cross-references

- [`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) — the peak-ratio metric (§3), the PB bands
  (§1b), and the dilution/measurement model + `b`/one-pot analysis (§13). This milestone implements PB and acts on §13.
- [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) — the intrinsic-colour metric + §0 dilution physics + the
  five chips + swatch S/L.
- [`SPEC_capture_quality.md`](SPEC_capture_quality.md) — signal fidelity (the reason colour is now trustworthy).
- [`SPEC_dev_measure_bench.md`](SPEC_dev_measure_bench.md) — the bench host these deltas land in.
- `tests/lda3.py` / `tests/lda4.py` (workspace root, 2021) — the abandoned LDA prototypes; retained as the record
  of why §2.4 uses a simple distance judge, not a supervised classifier.
- **`SPEC_wirtschaftliches.md`** — market/economics analysis (will the miller profit, realistic Spectracs revenue,
  lab-as-channel model). **⚠ Lives OUTSIDE this git repo at `spectracs-references/business/SPEC_wirtschaftliches.md`
  and must NEVER be committed / pushed to GitHub** (confidential business analysis). Referencing it by name from
  here is fine; the file itself stays off GitHub. See also the sales-offer material in the same folder
  (`Verkaufsangebot_Mueller.md`, `Spectracs_Roestampel_Flyer.pdf`).
