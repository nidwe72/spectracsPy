# SPEC — the oil profile and its readings: what can be read beside `Rv`

> **Status: DESIGN — and DECIDED for the plugin** *(Edwin, 2026-09-19: "today's sentences will be
> incorporated into the plugin")*. Nothing of this is in the app or a plugin yet. A **reference
> implementation** exists in the report build of the internal test-suite report (chapter 8, "Zehn Öle im
> Profil") and in an HTML page made the same day; both live outside the public repos
> (`spectracs-references/business/…/testSuiteInspectionAndMeasurement/`, `profile_dump.py` +
> `build_test_suite_report.py`, block `CHAPTER 8`). This document is the contract that an in-app version
> would implement.
>
> ⛔ **The verdict stays `Rv`** (`SPEC_red_ratio_metric.md`, M9 not waived). The profile explains a
> verdict; it never changes one.
>
> ⛔ **The cut points in §4 were set on 2026-09-19 on the corpus they are shown on and are NOT
> pre-registered.** They are an illustration until §8's tests have run.

---

## 1 · Why — the Kiendler case

On 2026-09-14 six oils were measured into `20280831_suite` (§16.23 of `SPEC_metric_research.md`). Edwin's
visual comparison of freshly prepared samples (2026-09-18/19) puts nine of the ten suite oils where `Rv`
puts them. **Kiendler looks clearly greener — like an oil at `Rv` ≈ 80, where it measures 63.6.**

The analysis of that one disagreement (session of 2026-09-18/19) gave the design:

- **`Rv` measures a composition, not a colour.** It is the 624/568 nm ratio inside the tetrapyrrole Q
  manifold, i.e. (inversely) the **protopheophytin share** — how much of the green pigment has lost its
  magnesium (`SPEC_red_ratio_metric.md` §2.5, `KB_spectroscopy_physics.md` §4.1). It is dilution-invariant
  by construction.
- **The eye sees a colour**, and more goes into it: how much absorber is in the sample at all (a pale
  sample stays on the green side of the dichromatism, `DOC_sample_physics.md` §3.7), and how much roast
  browning dims the green window.
- **In nine oils these move together**, because roasting drives demetallation *and* Maillard browning.
  In Kiendler they come apart: partly demetallated pigment, a pale sample (A448 0.68 against 0.93 for the
  darkest), and a steep, carotenoid-like blue edge rather than a browning tail.
- ⇒ A report that shows only `Rv` **contradicts** such a case. A report that shows the profile can
  **explain** it.

Four findings of that session are worth keeping on their own:

| finding | number | status |
|---|---|---|
| Kiendler's paleness is the oil, not the capillary | both fills 0.691 / 0.667 (2 % apart) vs fill-to-fill dose scatter of 2–12 %; 25–27 % below Esterer/Birnstingl | ✅ measured |
| browning and `Rv` move together over the ten oils | r = −0.71 (ρ = −0.68); Kiendler is the clearest exception (low `Rv`, low browning) | ✅ measured, n = 10 |
| a simulated transmission colour (CIELAB hue, D65, path ×4–12) tracks `Rv` better once every sample is scaled to equal A448 | r 0.84→0.92 (×4), 0.72→0.85 (×8), 0.56→0.70 (×12) | ⚠ scratch analysis, not committed; assumes full transmission above 636 nm |
| Kiendler's residual against `Rv` in that simulation | +12.7° hue (`Rv` alone) → −0.5° (`Rv` + Q% + A448) | ⚠ same caveat; partly circular (colour computed from the same spectra) |

⛔ **Scaling does NOT change `Rv`.** "`Rv` on an equal-load spectrum" is `Rv` (the scale factor cancels).
A metric that agrees with the eye on Kiendler would have to put the load *back in*, which brings the
capillary dose back — rejected (§7).

---

## 2 · The four values

Per run, band means on the absorbance trace (same windows and despiking as `Rv`):

```
Rv        = 100 · (A[622–627] − A[500–560]) / (A[565–580] − A[500–560])    green-pigment integrity
B         =        A[498–504] / A[448–460]                                   browning (proxy)
A448      =        A[448–460]                                                sample darkness
Q%        = 100 · (A[565–580] − A[500–560]) / (A[448–460] − A[500–560])    green-yellow balance
```

| value | what it is | what it is NOT |
|---|---|---|
| **`Rv`** | share of the tetrapyrroles still metallated; higher = less protopheophytin | a colour, a roast degree, a load |
| **B** | how far the blue absorption reaches into the green; carotenoid stops before ~500 nm, Maillard products do not | a Maillard measurement — it is one flank, and carotenoid vs browning is not cleanly separable from 448 nm up |
| **A448** | how strongly the **prepared sample** absorbs blue = oil × dose × path | a property of the oil alone until the dose is known (weighing) |
| **Q%** | Q band relative to the blue absorbers (carotenoid + browning + Soret flank) | "pigment-rich": protopheophytin's 569 nm band sits in the numerator, so strong demetallation *raises* Q% |

⚠ **Q% is not shown as a column** (Edwin, 2026-09-19). Seven of ten oils sit inside ±2 of each other;
low values occur in the greenest oils and high values in the most degraded one, so on its own it
invites the wrong reading. It survives only as the input of one hypothesis sentence (§5).

---

## 3 · Aggregation

Run → fill (mean of the runs of the fill) → sample/oil (mean of the fills). The same arithmetic as
`rv_dump.py` / `diagnostics/tracker_rv_fidelity.py.fills()`. σ per value from the fill scatter; known
magnitudes over the suite: `Rv` ≈ 4 (σ_fill), Q% up to ≈ 2, B up to ±0.02, A448 2–12 % (capillary).

---

## 4 · Levels (⛔ provisional, not pre-registered)

| value | levels | "at the cut" |
|---|---|---|
| `Rv` | low < 52 (= the verdict threshold T) · mid 52–95 · high ≥ 95 | within ±4 of a cut |
| B | low < 0.105 · high ≥ 0.105 | within ±0.01 of 0.105 |
| A448 | pale < 0.70 · mid 0.70–0.85 · dark > 0.85 | none — no σ while the dose is unknown |
| Q% | low < 18 · mid 18–22 · high > 22 | within ±1 of a cut |

**"at the cut" replaces "borderline"** (Edwin: *"grenzwertig" ist ein negativer Begriff*). It means *not
classified*, not *bad*.

### 4.1 ⚠ The browning gate — the provisional darkness rule

**B is only classified when 0.75 ≤ A448 ≤ 0.95.** Outside that range it is reported as *not assessed*.

Why: every absorbance trace carries a small wavelength-independent offset **c** (residual scatter,
re-seating, a baseline that is not exactly zero). It sits in numerator and denominator:

```
B_measured = (A500 + c) / (A448 + c)
```

With c = 0.01 and the same oil (true B = 0.085): a dark sample (A448 0.90) reads 0.095, a pale one (0.50)
reads 0.103. A pale sample therefore reads **browner** than it is. The same term as the pedestal of
`DOC_pedestal_correction.md` — absorbance that does not scale with the amount of oil.

- An offset-free variant `(A500 − A550) / (A448 − A550)` was tried and **fails**: a difference of small
  numbers, scattering across zero within one oil (Lugitsch −0.024 … +0.003).
- ⭐ **The proper fix is a two-dose fill** (e.g. 1 and 2 capillaries into 4 ml): the pigment doubles, c does
  not, so c is solvable per oil — the same route by which `r_Q` was measured on Kiendler (2026-08-01).
  Until it has run, the 0.75–0.95 range is a rough proposal, not a derived one.
- ⛔ **Do not widen the range to bring Kiendler back** (it is at 0.679). That would choose the rule after
  seeing the oil.

Consequence over the suite: browning is classified for **3 of 10 oils** (Esterer low; Birnstingl and
Spar Premium high). Kiendler's reading "degraded but hardly browned" is therefore **not** asserted,
although its B (0.093) is low.

---

## 5 · Rules → readings

Sentences are generated from the levels, in this order. **● established** (physics or a firm statement
about what the measurement can say) before **◐ hypothesis** (not validated).

| # | condition | sentence (DE) | sentence (EN) | status |
|---|---|---|---|---|
| R1 | `Rv` high / mid / low / at the cut | Grünpigment intakt. / teilweise abgebaut. / weitgehend abgebaut. / Grünpigment-Erhalt an der Schwelle. | Green pigment intact. / moderately degraded. / largely degraded. / Green-pigment integrity at the cut. | ● |
| R2 | A448 pale | Helle Probe: wirkt grüner, als der Messwert sagt. | Pale sample: will look greener than the measured value suggests. | ● (dichromatism) |
| R3 | A448 dark | Dunkle Probe: wirkt brauner, als der Messwert sagt. | Dark sample: will look browner than the measured value suggests. | ● |
| R4 | B not assessed | Bräunung nicht bewertet: Probe zu hell. / … zu dunkel. / … knapp außerhalb des Bereichs. *(within 0.01 of a gate edge)* | Browning not assessed: sample too pale. / too dark. / just outside the range. | ● |
| R5 | B at the cut | Bräunung an der Schwelle — keine Einstufung. | Browning at the cut — not classified. | ● |
| R6 | B high, `Rv` low | Deutlich gebräunt — typisch für eine kräftige Röstung. | Clearly browned: typical of a strong roast. | ◐ |
| R7 | B high, `Rv` not low | Deutlich gebräunt. | Clearly browned. | ◐ |
| R8 | B low | Wenig Röstbräunung. | Little roast browning. | ◐ |
| R9 | Q% low | Gelb überwiegt Grün, im Vergleich zu den anderen Ölen. | Yellow outweighs green relative to the other oils. | ◐ |

⭐ **The Kiendler rule** — `Rv` low/mid **and** B low ⇒ *"demetallated without browning; consistent with
stored seed or a gentle roast; will look greener than `Rv` suggests"* — is the reading this whole design
exists for. It is **held back** until the browning gate (§4.1) is replaced by the two-dose correction,
because today it cannot fire on the one oil that motivated it.

**Removed:** a guard sentence for "Q% high and `Rv` low" (*"balance raised by the degraded pigment itself,
not a sign of much green pigment"*). It explained a value that is no longer shown (Edwin, 2026-09-19).

### 5.1 Who sees what

| audience | values | sentences |
|---|---|---|
| **internal** | `Rv` (named), B, A448 (+ Q% on request); band windows allowed | all; ◐ marked "hypothesis, not validated — internal only" |
| **lab owner** | same values under the lab-owner names; ⛔ **no band windows anywhere** (the windows are the recipe) | all; ◐ marked "hypothesis, not validated" (no "internal only" — he reads them) |
| **customer** | `Rv` only, as the verdict | **at most two ● sentences** (R1 plus the first of R2–R5), **no ◐**, nothing internal |

In documents for internal and lab-owner readers the sentences a customer would not see are rendered
**faint**, so the reader sees both views at once.

### 5.2 Names

| value | internal | lab owner / DE | lab owner / EN | customer |
|---|---|---|---|---|
| `Rv` | protochlorophyll share (`Rv`) | Grünpigment-Erhalt | Green-pigment integrity | Green-pigment integrity |
| B | browning proxy (A500/A448) | Bräunung | Browning | — |
| A448 | sample absorbance (A448) | Probendunkelheit | Sample darkness | — (only as the R2/R3 sentence) |
| Q% | tetrapyrroles : blue absorbers (Q%) | Grün-Gelb-Balance *(not shown)* | Green-yellow balance *(not shown)* | — |

⚠ "Sample **depth**" was rejected — it reads as fill height or path length, which is exactly what it is
not. "Pigment state" and "pigment : carotenoid" were rejected — carotenoids are pigments too.

---

## 6 · Presentation (as built in the report, 2026-09-19)

- Column order: **Oil · Green-pigment integrity · Readings · Browning · Sample darkness**. The first two
  headers bold; all headers **top-aligned**.
- **Colour only on the integrity levels**: mid = green, high = a slightly lighter green, low = brown.
  Browning and darkness levels are **all the same plain grey chip, not bold** — *not assessed* and *at the
  cut* included; the ¹/² markers carry the distinction.
- A small bar under `Rv`, 0–130, with a tick at T = 52.
- **B and A448 are displayed ×100** (Edwin, 2026-09-19: readability) — B 0.122 → **12.2**, A448 0.744 →
  **74.4**, headers "index ×100" / "absorbance ×100". The cut points follow in every displayed text
  (B cut 10.5, at the cut ±1, browning gate 75–95, pale < 70, dark > 85). ⚠ Computation and §4 stay in
  the unscaled units; only the rendering multiplies.
- In-cell reasons are replaced by markers explained in the legend: **¹** at the cut (B within ±0.01 of
  0.105), **²** not assessed (A448 outside 0.75–0.95).
- The **legend sits below the table**.
- Readings: one sentence per line, the ●/◐ glyph as the bullet (● grey, ◐ amber).
- Sorted by `Rv`, lowest first. A row where the eye disagrees with `Rv` is shaded (a marker of an
  observation, not a measurement).

---

## 7 · Why rules and not a learned model

- **n = 10 oils.** A clustering or a regression would be fitted to exactly the ten oils it is shown on —
  the trap M9 exists for.
- **Explainable.** Each sentence traces to a named rule with a stated reason; that is what a producer
  needs when "it looks green but the device says degraded".
- **Upgradeable.** When seed age, a sensory panel or a carotenoid reference exist, single rules are
  validated or replaced; the structure stays.

⛔ **Rejected: a load-sensitive "Rv2"** that would agree with the eye. It would re-import the capillary
dose (2–12 %) that `Rv` was chosen to cancel, and it would be fitted to one oil.
⛔ **Rejected: Q% folded into the verdict** — that was `Rv − Q%`, tested and shelved in
`SPEC_red_ratio_metric.md` §12.7. Q% as a *separate descriptor* is a different question.

---

## 8 · Open — in the order they should run

1. **Pre-register** the cut points and rules of §4–§5 (M9 style) **before** 2.–4. are evaluated.
2. **Best-before dates** of all ten bottles next to `Rv` (costs nothing). Prediction: Kiendler was
   pressed late in the season, i.e. from long-stored seed (KB §4.1: protopheophytin 1.1–35.5 % of the
   protochlorophylls, rising with seed storage, without Maillard browning).
3. **Equal-absorbance photograph:** Kiendler prepared as dark as Esterer and Birnstingl (one capillary into 3 instead
   of 4 ml), photographed against both. Kiendler falls back toward its `Rv` ⇒ paleness was the cause.
   Still looks ≈ 80 ⇒ something `Rv` does not read (the blue edge, or the red above 636 nm).
4. **Two-dose fill** per oil ⇒ solve c, replace the §4.1 gate, and let the Kiendler rule fire or not on
   its merits.
5. The 15- (or 9-) pair photographic round robin of the six new oils as the transitive eye ranking.
6. *(later, needs a lab)* Mínguez-Mosquera carotenoid reference on 2–3 oils (Kiendler, Esterer, Spar Premium) to anchor
   "carotenoid-like vs browned".
7. *(later, needs hardware)* A 405–420 nm emitter splits Q% into proper axes (carotenoid fingers, the
   protochlorophyll ~432 / protopheophytin ~411 nm Soret peaks); the red extension adds the red window
   the eye uses. Both add rows to §2 and rules to §5; neither changes the structure.

### 8.1 In-app implementation *(decided 2026-09-19; build when asked)*

⭐ **Why it matters now.** Edwin's stance of 2026-09-19: for its niche — expert millers, no comparable tool
anywhere — the software is **shippable once these readings are in the plugin and a final cleanup has been
done** (the cleanup is planned for a separate session). `Rv` as chosen stands; separating oils more than
~20 `Rv` apart is sufficient for now; the settled measurement works as it is.

What ships to millers, and what does not:

- ⭐ **Only ● sentences reach a miller.** The ◐ sentences (R6–R9) stay internal until §8's tests 1–4 have
  run — they carry the browning proxy and Q%, both unvalidated.
- ⭐ **The cut points are versioned plugin constants** (see below): when a cut moves, a miller's older
  reports must stay explainable by the version they were made with.
- ⭐ **First delivery as a parallel-measurement pilot** with one or two millers, measured alongside the
  in-house bench for a few weeks — the open risk is a different operator's preparation scatter, not the
  software.

- **Features:** a pure, Qt-free function beside `plugin_sdk/util/SpectrumFeatureUtil.py`, per run.
- **Levels + rules:** a small module with the cut points as **versioned constants** of the plugin — a new
  set of cuts is a new plugin version, never a silent change of yesterday's reading.
- **Output:** the verdict (`Rv`) unchanged; the profile as its own view-model in the EVALUATION step with
  `shownInReport` (M2 PDF) and fields for SENAITE (LIMS). Sentence templates keyed by rule id, DE/EN,
  with their evidence status.

---

## 9 · The ten suite oils (reference output, 2026-09-19)

Two runs per fill; fills per oil in brackets. ⛔ Oil names only — the report's two-letter designations
and their mapping stay in the non-public business folder.

| oil | `Rv` | level | B | level | A448 | level | Q% |
|---|---|---|---|---|---|---|---|
| Spar S-Budget (4) | 27.9 | low | 0.122 | not assessed ² | 0.744 | mid | 25.6 |
| Spar Premium (2) | 37.3 | low | 0.122 | high | 0.797 | mid | 20.5 |
| Spar ggA (2) | 56.6 | mid | 0.108 | at the cut ¹ | 0.787 | mid | 20.2 |
| **Kiendler (2)** | **63.6** | **mid** | **0.093** | **not assessed ²** | **0.679** | **pale** | **17.9** |
| Birnstingl (2) | 69.7 | mid | 0.122 | high | 0.927 | dark | 19.0 |
| Steirerkraft (5) | 79.8 | mid | 0.109 | not assessed ² | 0.636 | pale | 20.3 |
| Stekko (2) | 83.3 | mid | 0.097 | not assessed ² | 0.486 | pale | 21.3 |
| Esterer (2) | 85.4 | mid | 0.085 | low | 0.906 | dark | 14.2 |
| Lugitsch (6) | 107.5 | high | 0.100 | at the cut ¹ | 0.790 | mid | 20.6 |
| Ja Natürlich (5) | 123.6 | high | 0.090 | not assessed ² | 0.745 | mid | 15.2 |

---

## 10 · Cross-references

`SPEC_red_ratio_metric.md` (the verdict, §2.5 the band assignment, §7 M9, §12.7 `Rv − Q%`) ·
`SPEC_metric_research.md` §16.23 (the ten-oil evening, §16.23.7 the eye check) ·
`KB_spectroscopy_physics.md` §4.1 (protochlorophyll/protopheophytin, storage) and the 448–460 nm tenant
table · `DOC_sample_physics.md` §3.7 (dichromatism, path length) · `DOC_pedestal_correction.md` (the
non-scaling term, `r_Q`).
