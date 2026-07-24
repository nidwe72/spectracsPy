# SPEC — The Roast Ampel (green / brown over-roast traffic light)

Status: **DESIGN — implement on explicit request only.** Raised by Edwin 2026-07-22/23. Grew out of the
colour-mapping discussion on top of the Capability Proof results. "Ampel" = German/Austrian for **traffic
light**; that is exactly what this is — a **two-state green / (too-)brown** verdict the miller can read at a
glance (a single 2.8 threshold, §2; the earlier three-state amber middle was **dropped** — the goal is over-roast
detection, [`SPEC_capability_proof.md`](SPEC_capability_proof.md) §1a).
An **interactive mockup + rendered A4 PDF** exist at `spectracs-references/ampel/roast_ampel_mockup.{html,pdf}`
(concept → miller's read → bench photo → K…R samples → group separation; four oils / 32 runs). Not
implemented in the app yet — **§8 is the app-integration build design.**

Builds directly on:
- [`SPEC_capability_proof.md`](SPEC_capability_proof.md) — the K/L/M/N validation that gives us the metric
  and the provisional thresholds (§11.2a).
- [`SPEC_pumpkin_peak_ratio_eval.md`](SPEC_pumpkin_peak_ratio_eval.md) — the **PB-band pigment ratio** this
  Ampel is built on (Soret 440–460 / Q 560–580) + the dilution/measurement model.
- [`SPEC_color_retrieval.md`](SPEC_color_retrieval.md) — intrinsic colour + chroma (the corroborating axis)
  and the §0 dilution physics that makes the ratio trustworthy.
- Prior art: `spectracs-references/oils/oilScores_rendered.png` (from `unsorted/oilScores.svg`) — Edwin's
  earlier "good→bad" green→olive→dark verdict-bar concept. **The Ampel is that idea, made quantitative and
  put on the validated pigment ratio.**

---

## 0. Why this exists — the miller's control instrument

The product goal (recap from the Capability Proof) is a cheap VIS spectrometer + software for the **pumpkin-oil
mill owner**. Two benefits: a **documentation tool** (measure in the field → submit to the lab) and the ability
to **judge whether the last press produced good oil**.

The Ampel is the second benefit made concrete: a headline **quality-warning** on the mill floor.

> Roast the pumpkin seeds too hot or too long and the pressed oil goes **brown** instead of the prized
> deep green. The Ampel gives the miller an **objective warning**: when a press comes out too brown, the red
> light tells him something has gone **fundamentally wrong** with the batch — most often the roasting.

**Framing correction (Edwin 2026-07-23):** it is *not* a dial the miller tunes reading-by-reading — he won't
measure-and-adjust in a tight loop. Its value is the **alarm**: a fixed, objective reference that flags a
too-brown press (which he'd otherwise judge by an eye that drifts day to day and has no side-by-side reference).
Green = fine, nothing to act on; amber = borderline, worth a closer look; red = something's wrong, the oil is
too brown — the usual cause being over-roasting. So it is primarily a **quality gate / red-flag**, not a
closed-loop controller.

---

## 1. The metric behind the light

**PB-band pigment ratio** `= mean(Soret band 440–460 nm) / mean(Q band 560–580 nm)` (despiked band means; see
`SPEC_pumpkin_peak_ratio_eval.md`). Higher ratio ⇒ **greener / fresher**; lower ratio ⇒ **browner / more
degraded** (over-roasted, aged, or oxidised pigment).

Why this metric and not raw colour:
- **Dilution-invariant.** It is a ratio of two absorbance bands; scaling the amount of oil (`A → k·A`) cancels.
  Validated: green K(2 drops) 3.89 ↔ L(3 drops) 3.76 (3.3 %); brown N(2 drops) 2.35 ↔ M(3 drops) 2.48 (5.4 %).
  A sloppy mill-floor dilution can't flip the verdict — the whole point of the Capability Proof gate.
- **Chroma is the secondary/corroborating axis** (green group 0.234 vs brown 0.198, same absorbed hue 245.5°).
  Kept as a cross-check, **not** the primary trigger — chroma is a thinner, drift-sensitive signal.

---

## 2. The two states (traffic-light threshold) — *one line, updated 2026-07-23*

A **single** threshold at 2.8 (the earlier three-state 2.6–2.8 amber band was **dropped** — see the note):

| Ratio band | Verdict | Light | Miller action |
|---|---|---|---|
| **≥ 2.8** | **good — green** | 🟢 | On the right path — keep the roast profile. |
| **< 2.8** | **probably too brown** | 🔴 | Too brown — usual cause over-roasting; look at the batch (lower temp / shorter time). |

**⚠ The 2.8 threshold is PROVISIONAL / illustrative — not yet calibrated.** It sits in the *empty gap* the
proof found (no sample between best-brown and worst-green). Good enough for the mockup and the story, **not**
for a field verdict. See §5 (calibration) — the gating open item before the Ampel ships as a real control.

**Why one line, not three (Edwin 2026-07-23).** A second brown line at 2.6 ("probably" vs "very probably") was
tried and **removed**: the fourth oil (S-Budget, Q/R) has a 6.5 % dilution spread that *straddled* 2.6 —
2.45 at 2 drops vs 2.62 at 3 drops, the **same oil earning two verdicts**. A threshold a sample's own scatter
can cross is no threshold. Against the single 2.8 line all 16 brown-oil runs (2.33 … 2.68) sit brown and all
16 green runs clear it — with room to spare. 2.8 is also the colour pivot (§3), so verdict and swatch flip
together.

Validation snapshot — **four oils, 32 runs** (from `SPEC_capability_proof.md` §11.2a + the O/P/Q/R series):

| Sample | Oil | Drops | Ratio | Verdict |
|---|---|---|---|---|
| K · L | Spar Premium (green) | 2 · 3 | 3.89 · 3.76 | good — green |
| O · P | Steirerkraft (green) | 2 · 3 | 3.69 · 3.66 | good — green |
| Q · R | Spar S-Budget (brown) | 2 · 3 | 2.45 · 2.62 | probably too brown |
| M · N | Hofer Bellasan (brown) | 3 · 2 | 2.48 · 2.35 | probably too brown |

Group means: green K,L,O,P = **3.75 ± 0.13**, brown M,N,Q,R = **2.47 ± 0.11**; Δ/noise ≈ **10.8**, and no run
of any oil falls between best-brown **2.68** and worst-green **3.59** (empty gap 0.91). The green/brown
*separation* is validated on four oils; only the *threshold placement* still needs §5's calibration.

---

## 3. The colour rendering (band + swatch)

Beside the verdict light, each measurement shows an **olive band** (green-olive → brown-olive) with a marker at
the sample's ratio, and a **solid swatch** below painted with the band colour at that spot. This is the "reads
like real oil" cue on top of the abstract light.

Design of the colour map (all interpolation in **OKLab** so olive mid-tones stay olive):

- **Marker position** is *linear* in ratio across the band, anchored to **fixed endpoints** (as-built
  **left = 4.5, right = 2.0**; the mockup uses 4.0) — replaces the earlier group-mean anchoring 3.83 → 2.41, so
  the position is comparable across oils and independent of the sample set.
- **Colour is non-linear**, pivoting at `BROWN_START = 2.8`:
  - **Above 2.8** — a *subtle* olive drift: fresher green `#9B9E57` at the left easing to muted olive `#8B8952`
    at the pivot.
  - **Below 2.8** — the **brown kick-in**, made *aggressive* as-built: muted olive `#8B8952` → warm brown
    `#6E4A22` already by 2.4 → dark brown `#442C0E` at the right edge (the earlier subtle `#8B8952`→`#6E5A34`
    ramp read too olive on-screen — Edwin, rig 2026-07-24).
- Anchors are **illustrative olives/browns**, chosen by eye — *not* measured intrinsic colours (see §5).

Rationale for the non-linearity: the interesting decision is at the brown end, so the green region is kept calm
(small drift = "still fine, just fresher/less fresh") and the brown transition is given the visual budget.

**Colour encodes the ratio, not the literal colour.** The rendered olive/brown is **not the oil's measured
colour** — it *encodes the pigment ratio* (a monotonic mapping, so a browner swatch always means a lower ratio).
It ships **beside** the true-colour chip (`SPEC_color_retrieval.md`), which carries the oil's measured
appearance — the two answer different questions (verdict-coding vs. what-it-looks-like). State this plainly in
the UI as a description of the idea; no need to argue the point (per Edwin 2026-07-23 — dropped the defensive
"it does not lie" framing).

---

## 4. Open design decisions (settle before/while implementing)

- **D-onset-vs-boundary.** The colour brown-onset (2.8) currently coincides with the good/amber verdict
  threshold (2.8). Clean and consistent as-is. Optional: decouple — brown *tint* could start at 2.8 while the
  oil isn't *called* "too brown" until 2.6. Edwin's call.
- **D-thresholds.** 2.8 / 2.6 are placeholders (see §5). The final numbers need calibration data.
- **D-amber-meaning.** Is "probably too brown" a genuine warn state the process should react to, or a dead-band
  the verdict shouldn't dwell in? Affects whether the app nags on amber.
- **D-swatch-source.** Keep the swatch **gauge-derived** (colour = f(ratio), so the two greens look alike by
  construction — good for showing dilution-invariance) *or* switch it to each run's **own measured intrinsic
  colour** (`colorAbsorbed`, from `SPEC_color_retrieval.md`), so two greens may legitimately differ. The latter
  is a real second measurement; the per-run values live in the 16 Capability-Proof PDFs' `workflow.json`.

---

## 5. Calibration — the gate before this is a real control (NOT yet done)

The provisional thresholds rest on **two oils at two dilutions each** and a big empty gap between them. Before
the Ampel drives a miller's decisions it needs a proper cut-off study:

1. **More oils spanning the green→brown continuum**, ideally with a known roast/degradation axis (roast a single
   seed lot at graded temperature/time) so ratio can be regressed against roast degree.
2. **Sensory / lab ground truth** to place "too brown" where the market does — cf. `Lankmayr_2004`
   (186 Styrian oils → sensory-quality classes) in `spectracs-references/articles/`.
3. From that, set defensible `GOOD`/`WARN` cut-offs (replacing 2.8 / 2.6) and decide the amber-band width.
4. Re-verify **dilution-invariance holds across the whole range**, not just at the two proof points.

Until then the Ampel is a **demonstrator**, and the app must not present its verdict as authoritative.

---

## 6. App integration (design sketch) — *superseded by §8*

The concrete, code-grounded build design now lives in **§8**; this sketch is kept for the rationale. Where it
lands and how (all DESIGN):

- **Host:** the pumpkin/DEV plugin's **EVALUATION** view (the plugin-driven host per
  `SPEC_plugin_driven_convergence.md`). The Ampel is the headline metric there — big light + ratio + one-line
  action, with the band+swatch strip beneath.
- **Rendering seam:** reuse `MetricFieldView` (colour + value + shownInReport) from `SPEC_color_retrieval.md`
  so the same widget renders in-app **and** into the **PDF report** (`SPEC_bench_pdf_export.md`) unchanged.
- **Persistence:** store `pigmentRatio` + `verdict` (+ thresholds version) with the measurement
  (`SPEC_workflow_persistence.md`) so a saved run replays the same light, and the LIMS push
  (`SPEC_lims_integration.md`) can carry the verdict as a field result.
- **Live/on-capture:** the light should update as soon as the burst is reduced, so the miller sees it at the
  press, not only after save. Pair with the acquisition guidance cue (`SPEC_acquisition_guidance.md`).
- **Provenance:** stamp the thresholds/calibration version onto the verdict (once calibrated) so field results
  are traceable to which cut-offs produced them.

---

## 7. Reference mockup

`spectracs-references/ampel/roast_ampel_mockup.html` — self-contained apart from the bench photo it
references (`KLMNOPQR_report.jpg`); theme-aware. Per-measurement units (band + marker + swatch + verdict
pill) for **K…R** (four oils, 32 runs — see §2), a bench-photo panel with a per-row legend, a per-oil
group-separation panel, and an interactive **probe** slider (screen-only; hidden from the PDF via
`@media print`). All colour maths (OKLab interpolation, the two-segment `colorRgb`, the single-threshold
`verdict()`) is inline JS and is **the reference implementation** the app port (§8) must reproduce exactly.
The `SAMPLES`/`OILS` arrays at the top of the `<script>` are the only data to touch when a series is added.

---

## 8. Plugin-driven Ampel — app integration design *(✅ IMPLEMENTED 2026-07-24 — G0–G8, 21 plugin + 215 spectracsPy tests green; G9 rig verify pending Edwin. Raised 2026-07-23; all §8.9 decisions resolved bar the deferred D8-table-decl future task.)*

> **Implementation note (G0–G8 done 2026-07-24).** New: `GaugeColorUtil` (core `plugin_sdk/util`), `VerdictGaugeView`
> + `GaugeRender` (model `plugin/view`, factory `"gauge"`), `visitGauge` on `WorkflowItemVisitor` + both renderers
> (`MatplotlibWorkflowRenderer`, Qt `GaugeWidget`), sdk exports, plugin `RoastGaugeView` + gauge first in
> `Evaluation (new)` + LABEL|SWATCH badge in `publishing()` (+ `__pigmentRatio`), `_PublishTab` renders the badge
> above the button, `stepViewModels` excludes `LimsPublishView` (RD#3). Tests: `spectracs-plugins/tests/test_verdict_gauge.py`.
> Verified visually in both targets + report end-to-end (gauge flagged into the 6-page PDF).
>
> **Rig-verified + refined 2026-07-24 (Edwin, first real capture).** Works on the ELP rig. Adjustments from
> the click-through: the gauge renders as a **labeled metric-grid ROW** — caption **"Verdict"** is
> the gray label chip (`TooltipPageLabel`, identical to the metric labels) in col 0, the band+swatch+pill sit in
> col 1 aligned with the metric field values; the two `Evaluation (new)` header sentences ("Pumpkin oil — PB
> literature bands…" and "Colour — processed variants…") were **removed**. Mirrored in the PDF renderer
> (label left, gauge in the value column). 236 tests green.
>
> **End-user-perception pass — Options A & B IMPLEMENTED 2026-07-24 (§8.4).** Evaluation gauge = **Option A**:
> `bandLeft = 5.0` (marker off the left edge) + a dashed **2.8 threshold tick**. LIMS badge = **Option B**: a
> **big verdict pill + a coarse green|red `ZONES` bar** (symbolic equal-width, D-zones-split), **no swatch, no
> number** (D-lims-number) — a stable verdict that doesn't jitter with the ±5 % settle-state wobble. New
> `GaugeRender.ZONES` + `GaugeColorUtil.zoneMarkerPosition`; both renderers; 238 tests green. **Only the rig
> sign-off remains.**

The plugin should **drive an Ampel** in the app that reproduces the mockup. This section is the grounded
build design; nothing here is implemented yet. It supersedes the §6 sketch. **Design steer (Edwin 2026-07-23):
make the view-model as GENERIC as possible** — the roast Ampel is one *instance* of a reusable
**classified-metric band**, driven entirely by data, not a roast-specific widget.

### 8.1 What the user asked for (2026-07-23)

1. The plugin drives an Ampel that **essentially follows** `roast_ampel_mockup.{html,pdf}`.
2. **Make the view-model generic** — parameterize *everything* that varies: the metric value, the gradient
   band colours (explicit, plugin-supplied), the threshold(s), the class labels. **Design for N thresholds →
   N+1 classes** (§8.2). The plugin declares its setup by **subclassing** the generic view (a thin preset that
   injects its constants), and those values **persist** in the embedded `workflow.json` (§8.3a/§8.3b).
3. The widget renders an **additive subset** of components (no `FULL`): any of **label** (pill) / **band**
   (+marker) / **swatch** / **value** (§8.4). The **swatch shows the metric value printed on it** in a
   plugin-provided colour (**white** for roast) — Edwin 2026-07-24.
4. **No probe.** The underlying metric is fixed (measured), never user-editable — the Ampel is a static
   readout, not the mockup's draggable probe.
5. Band endpoints **left = 4.0, right = 2.0** — fixed, deliberately *wider* than the data to anticipate very
   green and very brown oils (Edwin; see §3 / D8-endpoints).
6. The Ampel is the **first entry of the `Evaluation (new)` step-tab** (§8.5).
7. The verdict **badge** also appears in the **PUBLISHING / LIMS final step**, beside the publish button — the
   end-user's headline "oil state + publish, at one glance" (§8.6). Styled like the PDF pill.

### 8.2 The generic model — a classified-metric band (the discussion Edwin asked for)

The abstraction is: **one fixed metric value, shown against an ordered set of classes, with a continuous
colour band and a semantic badge.** Everything is data on the view-model; the renderers only draw. This is
what makes it reusable beyond roast (any pass/fail or graded metric).

**Two independent colour systems** — keep them separate, they answer different questions:
- **Band gradient** — a *continuous* ramp that "reads like the oil" (olive → brown). Parameterized by
  `gradientAnchors` = an ordered list of `(metricValue, rgb)` stops, interpolated in **OKLab**. As-built (rig
  2026-07-24) = `[(4.5, #9B9E57), (2.8, #8B8952), (2.4, #6E4A22), (2.0, #442C0E)]` — fresh-olive → muted-olive
  pivot → an **aggressive** warm-then-dark brown below 2.8. (The mockup still shows the older 3-anchor
  `4.0/2.8/2.0` ramp; the app supersedes it.)
- **Class / badge colours** — *discrete* (green good / red brown, amber if a middle class exists), one per
  class, supplied **explicitly by the plugin** on each class (§8.3a — light + dark variants for theme).
The **swatch** render is the *band* colour sampled at the value (an oil-coloured chip); the **pill** is the
*class* colour. Distinct on purpose.

**N thresholds → N+1 classes (the generalization).**
- `thresholds = [t₁, t₂, … tₙ]` — boundary metric values, ordered from the `bandLeft` side toward `bandRight`
  (descending here, e.g. `[2.8]`, or `[2.8, 2.6]` to re-admit the old amber middle class).
- `classes = [c₀, c₁, … cₙ]` — **n+1** entries, ordered the same way; each `= {label, colors}` (§8.3a).
- `classify(value)` = locate `value` among the thresholds (a bisect respecting the band orientation) → the
  class index → its label + colour is the verdict badge.

**The payoff:** the 2-state vs 3-state decision (§2, and its whole history) becomes **plugin data, not a code
change** — `thresholds=[2.8]` today; a calibrated `thresholds=[2.8, 2.6]` with an amber class later needs zero
renderer/model edits. Same widget serves a future oxidation index, a different oil metric, etc.

**Qt-free util** — `spectracsPy-core/sciens/spectracs/plugin_sdk/util/GaugeColorUtil.py`, exported from
`plugin_sdk/__init__.py`. A faithful port of the mockup's OKLab helpers (`srgbToLin`/`linToSrgb`/`toOklab`/
`fromOklab`/`lerp`) — **self-contained, no new dependency**, and deliberately *not* routed through
`EvaluationColorUtil` (its `colour`-science XYZ path is a different colour space). Generic entry points:
```
gradientColorAt(value, anchors) -> rgb          # OKLab interpolation across the anchors (the swatch colour)
gradientStops(anchors, n)       -> [(pos,rgb)]  # n+1 stops across [left,right] for the band fill
positionOf(value, left, right)  -> 0..1         # marker position, linear in the metric
classify(value, thresholds)     -> index        # which class (orientation-aware)
```
**The util holds NO roast constants** (Edwin: colours/labels/gradient are the plugin's to own — §8.3a). The
roast anchors/thresholds/classes live plugin-side, not here; `GaugeColorUtil` is pure generic maths. **Unit-
test against the mockup:** `classify(3.69,[2.8])==0` (good), `classify(2.62,[2.8])==1` (brown),
`gradientColorAt(2.8, roastAnchors)` = muted-olive, endpoints exact.

### 8.3 The view-model: `VerdictGaugeView` (generic, data-only)

A first-class item type (the band+marker is the mockup's signature; no existing view-model can draw it).
`spectracsPy-model/sciens/spectracs/model/spectral/plugin/view/VerdictGaugeView.py`, extending `ReportableView`.
Generic and domain-agnostic — the roast plugin specialises it via `RoastGaugeView` (§8.3a). Carried data (all
plain, Qt-free — **no logic, no probe**):

| field | meaning |
|---|---|
| `value: float` | the fixed metric (here the despiked `Soret/Q` pigment ratio). Read-only. |
| `bandLeft`, `bandRight` | marker-scale endpoints (as-built `5.0`, `2.0`; may descend). NB the gradient anchors start at 4.5 — 5.0→4.5 is flat fresh-olive headroom so the greenest oils aren't pinned to the edge. |
| `gradientAnchors: [(value, rgb)]` | the band ramp (§8.2). |
| `thresholds: [float]` | n class boundaries (§8.2). |
| `classes: [{label, colors}]` | the n+1 classifications + their **badge label + explicit colours** (§8.3a). |
| `valueColor` | colour of the metric value drawn **on** the swatch (Edwin: plugin-provided — **white** for roast). Single colour (sits on the olive chip, so theme-independent), unlike the per-class pill colours. |
| `render` | which components to draw — a set of `LABEL` / `BAND` / `SWATCH` / `VALUE` (§8.4). |
| `caption: str?` | the left-column label chip — as-built `"Verdict"` (both views). |
| `verdictLabel: str` | **cached** at construction = `classes[classify(value, thresholds)].label`. Stored so a list/table reads it without maths (§8.11 — mirrors `VerdictView.roastState`). |
| `swatchColor: str` | **cached** hex = `gradientColorAt(value)`. Stored so a table can paint the run's swatch directly, no re-derive, no re-run (§8.11). |

**Verdict is derived at *construction* and cached** (`verdictLabel`, `swatchColor`) — not re-derived on every
read. The **raw setup** (`value`, `thresholds`, `classes`, `gradientAnchors`) is *also* stored, so the full
widget can render and a run stays inspectable/re-derivable; the two are consistent because both come from the
same `value` at build time. `toJson()/fromJson()` round-trip every field + `isShownInReport`; register the
`"gauge"` tag in **`ViewModelFactory`** (`spectracsPy-model/.../plugin/view/ViewModelFactory.py`).

### 8.3a Who owns the colours + labels — the plugin (and the subclass question)

**Yes — the colours, labels and gradient are the plugin's, not the generic view's or the core util's**
(Edwin 2026-07-23). The generic `VerdictGaugeView` + `GaugeColorUtil` + renderers hold *no* roast semantics; the DEV
(and later pumpkin) plugin owns *what the classes are, what they're called, and what colour each is*.

- **Class badge colours = explicit plugin data, as hex strings** (Edwin's pick). Each `classes[k]` carries its
  own `colors` — plain **6-digit hex** (`"#b7d878"`), which **both renderers consume natively** (Qt QSS,
  matplotlib accepts hex directly) — *no `rgba()` strings, no `(r,g,b)` tuples* (see the final rubber-duck on
  colour format). One `{"text","bg"}` set suffices: the app is **single dark-themed** (`#191919` bg), and a
  dark chip with light text also reads fine on the white PDF; an optional `{"printText","printBg"}` override is
  available if the paper pill needs a lighter treatment. (A future `warn`/amber class is just another entry.)
- **Band gradient** — always explicit plugin data (`gradientAnchors`, hex); no semantic shortcut for a
  continuous ramp. Same ownership as the labels — declared the same way (below).

**On subclassing `VerdictGaugeView` — use constructor injection (final decision, 2026-07-24).** Edwin's intent
(*the plugin declares the labels/colours/gradient*, floated as an abstract `getThresholds()`) is right; the
**safe, simple realisation is a thin subclass that passes its constants to `super().__init__()`** — no
accessors:

```python
# in the plugin (spectracs-plugins), importing VerdictGaugeView, GaugeRender, GaugeColorUtil from plugin_sdk
class RoastGaugeView(VerdictGaugeView):
    _GOOD  = {"text": "#b7d878", "bg": "#2f3b1f"}     # light-green text on a dark-green chip (dark app + white PDF)
    _BROWN = {"text": "#ef9a80", "bg": "#3b241f"}     # light-red text on a dark-brown chip
    # 4.5 fresh-olive -> 2.8 muted pivot -> AGGRESSIVE brown (2.4 warm brown, 2.0 dark brown); as-built rig values
    _ANCHORS    = [(4.5, "#9B9E57"), (2.8, "#8B8952"), (2.4, "#6E4A22"), (2.0, "#442C0E")]
    _THRESHOLDS = [2.8]
    _BAND_LEFT, _BAND_RIGHT = 5.0, 2.0   # 5.0 marker scale; anchors start at 4.5 (headroom)
    def __init__(self, value, render, caption="Verdict"):
        classes = [{"label": "good — green",       "colors": self._GOOD},
                   {"label": "probably too brown", "colors": self._BROWN}]
        util = GaugeColorUtil()                                       # the PLUGIN computes the cache (RD#12) —
        index = util.classify(value, self._THRESHOLDS, self._BAND_LEFT, self._BAND_RIGHT)   # NOT the model (circular dep)
        super().__init__(                                            # the base just STORES everything (pure data)
            value, render=render, caption=caption,
            bandLeft=self._BAND_LEFT, bandRight=self._BAND_RIGHT, gradientAnchors=self._ANCHORS,
            thresholds=self._THRESHOLDS, classes=classes, valueColor="#FFFFFF",
            verdictLabel=classes[index]["label"], swatchColor=util.gradientColorAt(value, self._ANCHORS))
```

**Why the plugin computes the cache, not the base (RD#12).** `GaugeColorUtil` lives in core `plugin_sdk`; core
already imports the model view-models, so the **model must not import core** (circular). The plugin *can* (it
imports from the sdk), so it resolves `verdictLabel`/`swatchColor` and passes them in; the model just stores
them. `fromJson` reads them from JSON — also no compute, no core import. Model stays pure data (§8.11 / RD#9).

**Why constructor injection over accessors (rubber-duck RD#2).** The base holds **plain fields**; `toJson`,
`fromJson`, and both renderers read *only the fields*. That makes reload airtight: `ViewModelFactory` (model
layer, maps `"type"`→class — it cannot see a plugin subclass) rebuilds a **base** `VerdictGaugeView` by calling
the same `__init__` with the JSON values. An accessor style (`getThresholds()` overridden by the subclass, base
`__init__` snapshotting it) *also* works, but it introduces a **footgun**: a renderer that calls
`view.getThresholds()` instead of `view.thresholds` returns the right value while authoring yet the base default
on a reloaded instance. Constructor injection has no accessor to misuse and is just as declarative — the
subclass still reads as a preset. (If per-aspect overridable methods are ever wanted, name the seeds
`defaultThresholds()` *distinct* from the fields and keep the rule "read fields, never seeds" — D8-accessor.)
Either way the anchors/thresholds/classes/colours land verbatim in `workflow.json` under `"type":"gauge"` —
Edwin's "inspect the `SpectralWorkflow` to see how the gauge was set up" (§8.3b).

> Constraint that keeps it safe: the subclass must add **no new persisted state of its own** — everything it
> contributes has to flow through the base's serialized fields (resolved in `__init__`). A subclass that needed
> its own extra serialized fields would require a plugin-registration hook on `ViewModelFactory` (couples the
> Qt-free model layer to plugin classes) — deferred unless a real need appears (D8-accessor).

### 8.3b How plugin view-models persist today (as-is) — the picture Edwin asked for

Grounded from the current code, so the gauge's persistence needs nothing new:

- A step's items live in an **`EvaluationResult`** (`spectracsPy-model/.../plugin/view/EvaluationResult.py`) —
  a DB entity with a `resultJson` TEXT column holding an ordered list of view-models. `toJson()` =
  `[item.toJson() for item in items]`; `syncToColumn()` writes `resultJson = json.dumps(toJson())`.
- **Each view-model owns its `toJson()/fromJson()`** and emits a `"type"` tag + its **field values**. E.g.
  `MetricFieldView.toJson()` → `{"type":"metric","label":…,"value":…,"color":…,"style":…,"isShownInReport":…}`.
  So *whatever a view-model stores as instance attributes is exactly what persists* — values, not methods.
- **`ViewModelFactory.fromJson(entry)`** (model layer) maps `entry["type"]` → the registered class and calls
  its `fromJson`. It only knows the base types in its `__BY_TYPE` map — hence the thin-subclass rule (§8.3a):
  a plugin subclass must serialize as a registered base `"type"`.
- **Where this JSON ends up:** (1) the saved-run DB record (`SPEC_workflow_persistence.md`), and (2) the
  **`workflow.json` embedded inside the report PDF** (via `pypdf` attachments — this is the same blob we read
  out of the K…R measurement PDFs). Both already carry every view-model's serialized fields.

**Consequence for the gauge:** because `RoastGaugeView` resolves its accessors into the base's serializable
fields (§8.3a), the gauge's `value / bandLeft / bandRight / gradientAnchors / thresholds / classes / render`
all land in that `workflow.json` under `"type":"gauge"`. So **today's mechanism already gives Edwin the
"inspect the embedded SpectralWorkflow to see how the gauge was set up" property** — no new persistence work,
nothing deferred. (The only thing *not* captured is subclass *methods*; but their resolved outputs are, which
is what matters.)

**Worked example — the two gauges as they persist.** Same run (oil O, ratio 3.69). Both are the *same*
`"type":"gauge"` view-model carrying the *full* setup; they differ **only in `render`** (and the report flag).
The verdict is **not stored** — a reader derives it: `classify(3.69, [2.8]) → class 0 → "good — green"`.

```jsonc
// EVALUATION step "Evaluation (new)" → resultJson: [ <this gauge>, {"type":"label",…}, {"type":"metric",…}, … ]
{
  "type": "gauge",
  "value": 3.69,
  "bandLeft": 5.0, "bandRight": 2.0,
  "gradientAnchors": [[4.5, "#9B9E57"], [2.8, "#8B8952"], [2.4, "#6E4A22"], [2.0, "#442C0E"]],
  "thresholds": [2.8],
  "classes": [
    {"label": "good — green",       "colors": {"text": "#b7d878", "bg": "#2f3b1f"}},
    {"label": "probably too brown", "colors": {"text": "#ef9a80", "bg": "#3b241f"}}
  ],
  "valueColor": "#FFFFFF",
  "verdictLabel": "good — green",
  "swatchColor": "#939455",
  "render": ["band", "label", "swatch"],
  "caption": "Verdict",
  "isShownInReport": true
}

// PUBLISHING step "Send to LIMS" → resultJson: [ <this gauge> ] ,  _view: {LimsPublishView…}
{
  "type": "gauge",
  "value": 3.69,
  "bandLeft": 5.0, "bandRight": 2.0,
  "gradientAnchors": [[4.5, "#9B9E57"], [2.8, "#8B8952"], [2.4, "#6E4A22"], [2.0, "#442C0E"]],
  "thresholds": [2.8],
  "classes": [
    {"label": "good — green",       "colors": {"text": "#b7d878", "bg": "#2f3b1f"}},
    {"label": "probably too brown", "colors": {"text": "#ef9a80", "bg": "#3b241f"}}
  ],
  "valueColor": "#FFFFFF",
  "verdictLabel": "good — green",
  "swatchColor": "#939455",
  "render": ["label", "swatch"],
  "caption": "Verdict",
  "isShownInReport": false
}
```

Notes: `isShownInReport` controls whether an item is *drawn on the PDF pages*, **not** whether it is embedded
in `workflow.json` (the whole workflow is embedded regardless — that is why the LIMS badge, `false`, still
persists). The two blocks carry identical setup on purpose (self-contained + replayable); if the byte-cost ever
matters, the label-only badge could drop `gradientAnchors`/`bandLeft`/`bandRight` (unused when only `LABEL`
renders) — a later optimisation, not needed now.

### 8.4 Rendering — one vocabulary, both targets, selectable components

Add `visitGauge(view)` to the render seam so screen and paper cannot drift (the M1 invariant):
`WorkflowItemVisitor` (`spectracsPy-core/.../report/WorkflowItemVisitor.py`) — declare `visitGauge` + add
`VerdictGaugeView` to the `dispatchItem` ladder; then implement it in both targets.

`render` is an **additive set of component flags — no `FULL`** (Edwin 2026-07-23): the plugin composes exactly
the parts it wants. Each renderer draws only the flagged components:
- **`LABEL`** — the verdict **pill**: class label on a rounded, class-coloured badge. Rendered **big/headline**
  when there is no `BAND` in the set (the LIMS/Option-B case), inline otherwise.
- **`BAND`** — the OKLab gradient band (from `gradientStops`) + a value marker at `positionOf(value)` + a
  **dashed threshold tick** at each `positionOf(threshold)` (the decision line — Option A).
- **`SWATCH`** — a solid chip = `gradientColorAt(value)` (the oil-coloured square) **with the metric value
  printed on it** in `valueColor` (white for roast), formatted to **2 dp** (`3.78`, D8-value-format).
- **`VALUE`** — the numeric metric as standalone text (`3.78`, 2 dp), in default app ink.
- **`ZONES`** *(Option B, 2026-07-24)* — a **coarse verdict bar**: `n+1` class-coloured segments of **equal
  width** (symbolic, **D-zones-split** — the threshold sits at the visual centre, not proportional to the ratio
  range), the threshold(s) as white dividers, and a marker at `zoneMarkerPosition(value)` (the value's depth
  within its own class). Jitter-tolerant. Segment fill = each class's `colors["zone"]`, **falling back to
  `colors["bg"]`** so a zone matches its verdict badge (Edwin 2026-07-24). In the LIMS row it is a **secondary**
  element — a modest fixed width beside the prominent big pill.

Pill text is **white** (`colors["text"] = "#FFFFFF"`) on the dark badge; the big headline pill is the prominent
element, the zone bar secondary.

Composed per use-site: the **Evaluation gauge** = `BAND | LABEL | SWATCH` (value on the swatch; `bandLeft = 5`
so the marker isn't pinned to the left edge, + the 2.8 tick — Option A), caption chip **"Verdict"** (both views);
the **LIMS badge** = `LABEL | ZONES` (**big** white-text pill + a secondary coarse zone bar, **no swatch, no
number** — D-lims-number, Option B), caption chip **"Verdict"**. Both render as a **labeled metric-grid row**
(caption = the gray chip in col 0). `render` serializes as a name-list (`["band","label","swatch"]`,
`["label","zones"]`) in `workflow.json` (§8.3b).

**Always a labeled metric-grid ROW** (Edwin 2026-07-24) — `visitGauge` participates in the shared metric grid
(does *not* flush it), so the caption is the gray label chip in col 0 (a `TooltipPageLabel`) and the gauge sits
in col 1, aligned with any metric fields. The **col-1 content is chosen by the render flags**:
- **With `BAND` (Option A / Evaluation)** — band + swatch + inline pill; caption chip "Verdict".
- **Without `BAND` (Option B / LIMS)** — caption chip "Verdict" (fixed height, text **vertically centred**) +
  a **big pill that fills the available width** + a **secondary** fixed-width zone bar. The chip, pill and zone
  all share `HEADLINE_HEIGHT` (40 px); `GaugeWidget` keys the treatment on "no `BAND`". `_PublishTab` zeroes the
  badge widget's layout margins so the "Verdict" chip **left-aligns with the Publish button** below (Edwin
  2026-07-24).

- **Qt** (`spectracsPy/.../workflow/render/GaugeWidget.py` + `QtWorkflowRenderer.visitGauge`) — `_GaugeBandBar`
  paints the gradient (`QLinearGradient` from `gradientStops`, **square corners**, top-aligned) + dashed
  threshold tick(s) + the value marker; `_GaugeZoneBar` paints the equal-width class segments + dividers + the
  zone marker; the **swatch** and inline **pill** share a rounded radius + `_CHIP_HEIGHT` (inline pill
  Expanding; headline pill big/fixed with the zone bar filling). Colours from `classes[k].colors`.
- **matplotlib** (`spectracsPy-core/.../report/MatplotlibWorkflowRenderer.py`) — mirrors it: caption left; band
  (`imshow` of `gradientStops`) + dashed-`axvline` threshold tick(s) + marker; the zone bar (`Rectangle` per
  segment + divider `axvline`s + marker); pill as a rounded **text-bbox** (not `FancyBboxPatch` — bow-ties in a
  wide/short axes). `zoneMarkerPosition`/`positionOf` live in `GaugeColorUtil` so both renderers share them.
  Reserve `__H_GAUGE_IN`. (The Evaluation band+tick is in the PDF; `ZONES` is Qt/LIMS-only but implemented here
  for the visitor contract.)

**Pill styling**, drawn identically by the Qt pill, the matplotlib pill and the LIMS badge. The **colour** comes
from the class's explicit hex `colors` (§8.3a) — the plugin's roast default is a dark chip + light text
(`good` → text `#b7d878` on `#2f3b1f`; `bad` → text `#ef9a80` on `#3b241f`) that reads on both the dark app and
the white PDF. The **shape** is app style (rounded, small uppercase letter-spaced) — the renderer owns the
*shape*, the plugin owns the *colour*. No `rgba`/alpha: both renderers eat 6-digit hex natively (final RD).

### 8.5 Placement — first item of `Evaluation (new)`

In `DevSpectralPlugin.__newEvaluationResult` (`spectracs-plugins/.../plugins/dev/DevSpectralPlugin.py`),
**prepend** the gauge as the first item of the tab, via the plugin-side subclass (§8.3a):

```python
ratio = ratio(soret, qBand)                       # already computed here; None-safe → skip the gauge
result.addItem(RoastGaugeView(ratio, render=GaugeRender.BAND | GaugeRender.LABEL | GaugeRender.SWATCH))
```

`RoastGaugeView` is the plugin's thin preset (§8.3a) — roast anchors / `thresholds=[2.8]` / green+brown
classes — constructing a generic `VerdictGaugeView`. The step already does `for item in newResult.getItems():
item.setShownInReport(True)`, so the gauge flows into the **PDF report** with no extra work (§8.7); the value
is the same `Soret/Q` as the `Pigment ratio` row → one source of truth. **The two header sentences that used
to lead this tab** ("Pumpkin oil — PB literature bands…" and "Colour — processed variants…") **were removed**
on the rig (Edwin 2026-07-24) — the gauge row + labeled metric rows are self-explanatory.

### 8.6 The verdict badge in the PUBLISHING / LIMS step — the end-user's headline view

**As-is (from the code).** The publish step *already exists*: `DevSpectralPlugin.publishing()` declares a
`Send to LIMS` step whose view is a **`LimsPublishView`** — the plugin view-model Edwin remembered. It is a
*passive descriptor* (target `backend`/`configKey`, `sampleTypeName`, `analyses`); the host renders it via a
**bespoke `_PublishTab`** (`DevMeasurementBenchViewModule`) = a summary line + a "Publish to LIMS" button +
a status line. So the button is done; the step carries **no verdict** today, and it is rendered *outside* the
generic visitor seam.

**Should-be (Edwin 2026-07-23).** For the end user this PUBLISHING step is the **most important view**: the
oil's verdict **and** the publish action in one glance. So the final step must show the **verdict badge**
(e.g. `good — green`) prominently, with the publish button beneath.

**The right mental model (Edwin): a step carries a *set* of plugin view-models.** The publish button is just
*one* view-model in that set; the step is *meant* to also hold another — the verdict badge (a `RoastGaugeView`
in `LABEL` mode). This is already how steps are structured — a step has an `EvaluationResult` (a list of
view-models) *and* a passive `_view`; the publish step today simply carries only the `LimsPublishView` on
`_view` and an empty item list. So the change is to **populate the step's item list with the badge** and
render the whole set:
- `publishing()` puts a `RoastGaugeView(ratio, render=GaugeRender.LABEL | GaugeRender.SWATCH)`
  into the step's `EvaluationResult`
  (items) and keeps the `LimsPublishView` as the publish descriptor. It computes the ratio via a shared
  private `__pigmentRatioAndVerdict(workflow)` (re-reads PROCESSING `ABSORPTION` via `__findRole`, despikes,
  band means → the same generic `GaugeColorUtil`); publishing receives `workflow`, so recompute is cheap and
  keeps the phase hooks independent (no cross-phase stashing).
- The host renders the step's **item list** through the shared `QtWorkflowRenderer` (the badge = the *same*
  pill as everywhere) **above** the `LimsPublishView` publish widget. Concretely: `__runPublishing` renders
  `stepViewModels(step)`'s non-`LimsPublishView` items first, then the publish button/status (today's
  `_PublishTab`). `LimsPublishView` stays special-cased (interactive + server call), exactly as `CaptureView`/
  `ReportView` are — it is conceptually one item in the set, just not a passive visitor node.
- Render the badge **large** here (headline), optionally with the oil-colour swatch — this is the glance view.

**Alternative (lower-touch):** keep `_PublishTab` bespoke and add `verdictLabel`/`verdictLevel` fields to
`LimsPublishView`, drawing the pill inside `_PublishTab`. Simpler, but duplicates pill drawing and special-
cases the badge instead of treating it as another view-model in the step — **recommend the set-of-view-models
approach** (D8-lims-render).

**Bottom line — what it boils down to.** The publish step gains **one extra view-model** (the `RoastGaugeView`
badge) in its item list; the host draws the step's items above the existing publish button. The badge **is
persisted** like every view-model (§8.3b) — "no *new* persistence" means no new *machinery* is needed, the
existing `EvaluationResult`→JSON path already carries it; and "no *model* change" means the recommended path
doesn't edit the `LimsPublishView` class (the badge rides in the step's item list instead). **The only decision
for you** is D8-lims-render: render the badge through the shared seam (recommended — reuses the pill, touches
only the host's `__runPublishing`) *or* bolt verdict fields onto `LimsPublishView` and draw the pill inside
`_PublishTab` (lower-touch, duplicates the pill). Not blocking — it's an implementation-time call.

**Separate follow-up (distinct concern):** also sending the verdict into the *lab record* as a LIMS **analysis
field-result** (server-side, via `publishSampleToLims`) — that is the record *carrying* the verdict, vs the
step *displaying* it. Optional; not required for the headline view.

### 8.7 Persistence, report, live update

- **Report:** covered by the existing `setShownInReport(True)` loop (§8.5) → `MatplotlibWorkflowRenderer`.
- **Persistence:** `VerdictGaugeView.toJson/fromJson` + the `ViewModelFactory` registration make a saved run replay
  the same light (`SPEC_workflow_persistence.md`); the stored value + endpoints + `thresholds` + `classes` +
  `gradientAnchors` pin both the geometry and the verdict.
- **Live/on-capture:** the Ampel is built in `evaluation()`, so it appears as soon as the burst is reduced and
  the phase renders — no separate live path needed (§6 goal met by placement).

### 8.8 Files touched (grounded)

| Layer | File | Change |
|---|---|---|
| core util | `spectracsPy-core/.../plugin_sdk/util/GaugeColorUtil.py` | **new** — OKLab port; generic `gradientColorAt`/`gradientStops`/`positionOf`/`classify`. **No roast constants.** |
| sdk export | `spectracsPy-core/.../plugin_sdk/__init__.py` | export `VerdictGaugeView`, `GaugeColorUtil`, `GaugeRender` |
| model | `spectracsPy-model/.../plugin/view/VerdictGaugeView.py` | **new** generic view-model (value, endpoints, `gradientAnchors`, `thresholds`, `classes`{label,colors}, `render` as name-list, accessors §8.3a; `toJson/fromJson`) |
| model | `spectracsPy-model/.../plugin/view/ViewModelFactory.py` | register `"gauge"` |
| seam | `spectracsPy-core/.../report/WorkflowItemVisitor.py` | `visitGauge` + dispatch entry |
| render (PDF) | `spectracsPy-core/.../report/MatplotlibWorkflowRenderer.py` | `visitGauge` (render-mode aware) + `__H_GAUGE_IN` |
| render (Qt) | `spectracsPy/.../workflow/render/QtWorkflowRenderer.py` | `visitGauge` + `GaugeWidget` (labeled row; render-mode aware) + pill |
| app style | pill *shape* QSS (rounded/uppercase) | the badge shape only — **colours come from the plugin** per class (§8.3a) |
| **plugin** | `spectracs-plugins/.../plugins/dev/DevSpectralPlugin.py` (+ a `RoastGaugeView` preset, §8.3a) | **owns roast colours/labels/gradient**; prepend it in EVALUATION; add the badge to the PUBLISHING step's item list + shared `__pigmentRatioAndVerdict` |
| LIMS step | `spectracsPy/.../development/DevMeasurementBenchViewModule.py` | render the step's badge item(s) above the publish button (`__runPublishing`/`_PublishTab`) |
| tests | `spectracs-plugins/tests/test_dev_plugin_improved_colour.py` (+ new `GaugeColorUtil` test) | Ampel first in EVALUATION; badge in PUBLISHING; N-class `classify`; port values |

Note `LimsPublishView` is *not* edited under the recommended (set-of-view-models) LIMS approach — the badge is
a separate `VerdictGaugeView` item in the step, not new fields on the publish descriptor. It gains `verdictLabel`/
`verdictLevel` only under the lower-touch alternative (§8.6 / D8-lims-render).

### 8.9 Open decisions (settle at build time)

- **D8-endpoints (RESOLVED — marker scale 5.0 → 2.0).** Deliberately wider than the data to **anticipate very
  green and very brown oils** (Edwin). The marker `bandLeft` moved 4.0 → 4.5 → **5.0** on the rig (2026-07-24)
  so the greenest oils (~4.5) sit *off* the left edge (~17 %) instead of pinned at 0 % (end-user perception,
  Option A). The **gradient anchors still start at 4.5**, so the 5.0→4.5 stretch is flat fresh-olive headroom.
  A run above 5.0 has its **marker clamped to the edge** while its **value text stays the true number**. (RD#5.)
  **Brown ramp made aggressive (rig, 2026-07-24):** the roast anchors are now 4-point
  `[(4.5,#9B9E57),(2.8,#8B8952),(2.4,#6E4A22),(2.0,#442C0E)]` — an extra warm-brown anchor at 2.4 makes the
  brown clearly visible right below the 2.8 pivot (the old subtle 2.8→2.0 ramp read too olive on-screen).
- **D8-view-vs-reuse (RESOLVED — dedicated view).** The design uses the dedicated generic `VerdictGaugeView`
  (§8.3) — the only faithful way to get the band+marker and it keeps the render seam clean. (The rejected
  fallback was `VerdictView` pill + a `MetricFieldView` chip, which loses the band+marker.)
- **D8-naming (RESOLVED — Edwin 2026-07-23): base type = `VerdictGaugeView`**, plugin subclass =
  `RoastGaugeView`. (It is a fixed metric read against a coloured scale with a marker + a verdict badge — a
  gauge, not an LDA "classification" and not a literal street "Ampel".) The English word "Ampel" is kept only
  for the *product concept* / this spec's title; all code identifiers use the gauge names. Existing `VerdictView`
  (the old 3-state `RoastState` pill) is unrelated and stays.
- **D8-colour-source (RESOLVED — explicit).** Each class carries **explicit** `colors` supplied by the plugin
  (light + dark variant); no semantic `level`→theme indirection. Band `gradientAnchors` are always explicit
  plugin data. Renderers/util hold no colour constants; the renderer owns only the pill *shape* (§8.4).
- **D8-render (RESOLVED — additive, no `FULL`).** `render` is an OR-able set of `LABEL`/`BAND`/`SWATCH`/`VALUE`;
  the plugin composes exactly what it wants and it **serializes as a name-list** in `workflow.json` (§8.3b).
- **D8-accessor (RESOLVED — constructor injection).** The plugin subclass passes its constants to
  `super().__init__()`; the base holds plain fields (`toJson`/`fromJson`/renderers read fields only). Chosen
  over the accessor style (`getThresholds()` override) to avoid the reload footgun (RD#2). A subclass with its
  *own* extra serialized state would still need a factory plugin-registration hook — deferred unless needed.
- **D8-colour-format (RESOLVED — hex, no rgba).** Colours are 6-digit hex strings, consumed natively by both
  renderers; `GaugeColorUtil.hexToRgb` is internal to the gradient maths only. Deliberate deviation from the
  `(r,g,b)`-tuple `MetricFieldView` convention, for JSON readability (RD#11).
- **D8-theme (RESOLVED — none).** The app is single dark-themed; no theme detection. Qt uses the class `colors`
  as-is; the PDF (white paper) reuses them (dark chip / light text), with an optional `printText`/`printBg`
  override. (RD#6.)
- **D8-classes.** Ship with `thresholds=[2.8]` / 2 classes (matches §2). The model already supports N — a
  calibrated amber middle class (`thresholds=[2.8, 2.6]`, add a `warn` class) is then a data change only.
- **D8-lims-render (RESOLVED — generic seam, Edwin 2026-07-24).** The LIMS badge is a normal
  `VerdictGaugeView(LABEL)` item rendered through the visitor seam (reuses the pill, no `LimsPublishView`
  change); the host draws it above the publish button. Requires the RD#3 `stepViewModels` fix.
- **D8-summary (RESOLVED for now — cache on the view-model; DB column later).** The gauge caches
  `verdictLabel` + `swatchColor` as stored fields, so the saved-runs **table** reads them off the deserialized
  item (the existing `VerdictView` pattern — level 2, §8.11), no re-run. A denormalized DB summary column
  (level 3) is a later `SPEC_workflow_persistence.md` optimisation for scale, not the gauge's concern.
- **D8-lims-field (RESOLVED — display-only for now).** The badge is display-only in the PUBLISHING step; the
  verdict is **not** written into the LIMS lab record as an analysis field-result in this build. Revisit if/when
  the lab wants it queryable server-side (a later `SPEC_lims_integration.md` add-on).
- **D8-value-format (RESOLVED — 2 dp).** The gauge value renders to **2 decimals** (`3.78`), matching the
  mockup. Note the `Pigment ratio` metric row shows 3 dp (`3.783`); both read the same number, the gauge is just
  the compact form.
- **D-a overview-table gauge column (RESOLVED — deferred, don't stopgap).** Not built in this pass: a hard-coded
  gauge column beside the `VerdictView` column is the "VerdictView-or-gauge fork" smell (§8.11). Wait for
  **D8-table-decl** (plugin-declared result columns) so the table is generic. The G1 cached fields already
  pre-wire it, so deferring costs nothing.
- **D8-swatch-source.** The §4 `D-swatch-source` question (gauge-colour vs measured `colorAbsorbed`) is
  unchanged and orthogonal to this widget.
- **Calibration caveat still stands (§2/§5):** the light is a **demonstrator** — 2.8 is uncalibrated. The app
  must keep a visible "provisional / not calibrated" note near the Ampel (it currently lives only in the README
  and this spec after the mockup's caveat paragraph was removed on 2026-07-23).

---

## 8.10 Implementation plan — rubber-duck + phases *(DESIGN; build on explicit request)*

### Rubber-duck — the traps a first cut would hit (walked against the real code)

1. **`classify()` orientation.** The band is **descending** (4.0 left → 2.0 right) and `thresholds=[2.8]` is
   descending too — a naïve ascending `bisect` gives the wrong class. Rule: class index = *number of thresholds
   `value` is at-or-below*, walking bandLeft→bandRight. Pin it with the unit test (`classify(3.69,[2.8])==0`,
   `classify(2.62,[2.8])==1`, boundary `classify(2.8,[2.8])==0`).
2. **Subclass mechanism (RESOLVED — constructor injection, not accessors).** The plugin subclass passes its
   constants to `super().__init__()`; the base holds **plain fields** that `toJson`/`fromJson`/both renderers
   read. `fromJson` rebuilds a **base** `VerdictGaugeView` via the same `__init__` from the JSON values (the
   model layer can't see a plugin subclass). The tempting accessor style (`getThresholds()` overridden, base
   snapshots it) has a **reload footgun** — a renderer calling `view.getThresholds()` gets the right value while
   authoring but the base default after reload. Constructor injection has no accessor to misuse. (§8.3a — D8-accessor.)
3. **`stepViewModels` silently drops `LimsPublishView`.** Confirmed: it excludes only `(CaptureView,
   ReportView)`, so a naïve `QtWorkflowRenderer().render(stepViewModels(step))` would feed `LimsPublishView` to
   `dispatchItem`, which returns `None` → the publish button **vanishes**. Fix: render the badge item(s)
   explicitly and keep the publish widget separate; **add `LimsPublishView` to that exclusion tuple** so it's
   never treated as a passive visitor item (§8.6).
4. **Both visitors must implement `visitGauge`.** Adding it abstract to `WorkflowItemVisitor` means every
   subclass needs it or `NotImplementedError` at runtime. Confirmed only **two** exist (`QtWorkflowRenderer`,
   `MatplotlibWorkflowRenderer`) — do both in the same change.
5. **`bandLeft` clamps a value past the edge (RESOLVED).** Was raised as K's max run 4.034 > 4.0; the endpoint
   was then moved to **4.5** on the rig for headroom. Either way, a value past the left edge clamps **only the
   marker line** to the edge while the **value text stays the true number** and the swatch colour clamps to the
   left anchor. So `positionOf` clamps to `[0,1]` and `gradientColorAt` clamps to the anchor range, but the
   value the plugin passes is displayed verbatim — the marker can saturate, the number never lies. Unit-tested.
10. **Swatch renders the value ON it (new, Edwin 2026-07-24).** `SWATCH` is no longer a bare chip — it draws the
   metric value on the coloured square in `valueColor` (white for roast). Watch-outs: **(a) contrast** — white
   on the *greenest* swatch (`#9B9E57`) is low (~2.8:1, under the 3:1 large-text line); on brown it's fine.
   Mitigation if it reads poorly: a 1 px dark text outline / soft shadow (both renderers) — keep in reserve,
   don't gold-plate. **(b) sizing** — the chip must be big enough for the number in both renderers (Qt fixed
   size; matplotlib reserved patch). **(c)** `valueColor` is a *single* colour on the olive chip (theme-
   independent), distinct from the per-class pill colours; serialize it (round-trip test).
6. **Theme (RESOLVED — no detection needed).** Verified: the app is **single dark-themed**
   (`ApplicationStyleLogicModule.getBackgroundColor()` = `#191919`, text `#DDDDDD`) — there is no light/dark
   toggle to read. So the target is *static per renderer*: the Qt pill uses the (dark-app) `colors`; the PDF is
   white paper, and the same dark-chip/light-text pill reads fine there too (optional `printText`/`printBg`
   override if a lighter paper pill is wanted). No runtime theme code.
11. **Colour format (RESOLVED — hex, no rgba).** Provide colours as **6-digit hex** strings. Both renderers eat
   hex natively (Qt QSS `background-color:#…`; matplotlib `facecolor="#…"`). *Avoid `rgba()`/alpha* — matplotlib
   can't take a CSS `rgba()` string, and translucency would need background compositing. `GaugeColorUtil` has a
   `hexToRgb` used only *internally* for the OKLab gradient maths; the model stays pure hex (readable in
   `workflow.json`). Deliberate, minor deviation from the existing `(r,g,b)`-tuple `MetricFieldView.color`
   convention — chosen for JSON readability + because the util already parses hex. (D8-colour-format.)
7. **`render` flag ↔ name-list.** `GaugeRender` (an `enum.Flag`) needs `fromNames`/`toNames` so the OR-set
   round-trips as `["band","label","swatch"]`. Keep the names stable (they're persisted).
8. **Graceful forward-compat.** An older app reloading a `"gauge"` it doesn't know → `ViewModelFactory` returns
   `None` and the item is skipped (existing defensive behaviour). Fine — note it, don't guard further.
9. **Layer direction.** `VerdictGaugeView` (model) imports **nothing** from core; `GaugeColorUtil` (core) is
   pure maths; the visitor (core) imports the model view for `isinstance` — the existing core→model direction.
   `GaugeColorUtil` callers are the **renderers** (band/marker/classify at draw time) **and the plugin** (the
   §8.11 cache, RD#12). The model never calls it.
12. **Cache computed by the plugin, not the model (from §8.11 caching).** `verdictLabel`/`swatchColor` are
   `GaugeColorUtil` results, but the model can't call `GaugeColorUtil` (core → model already, so model → core
   would be circular). So the **plugin** (`RoastGaugeView.__init__`) computes them and passes them in; the base
   just stores them; `fromJson` reads them from JSON. A base built *directly* without them (not via the plugin
   or `fromJson`) simply has them `None` — acceptable, those two paths always supply them. Renderers may read
   the cache or recompute (same `value` → consistent); the cache's real customer is the table (§8.11).

### Phases (bottom-up; each independently testable)

```
┌──────┬───────────────────────────────────────────────┬────────────────────┬──────────┬────────────────────────────────┐
│ Ph   │ Deliverable                                    │ Repo               │ Depends  │ Done-when (verify)             │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G0   │ GaugeColorUtil: OKLab port + gradientColorAt / │ core               │ —        │ unit: classify 3.69→0, 2.62→1, │
│      │ gradientStops / positionOf / classify (no      │ plugin_sdk/util    │          │ boundary 2.8→0; endpoints/pivot │
│      │ roast constants); hex→rgb; clamp out-of-band   │                    │          │ colours exact; clamp works     │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G1   │ VerdictGaugeView model (plain fields, hex,      │ model              │ —        │ round-trip incl valueColor +    │
│      │ +valueColor +cached verdictLabel/swatchColor)   │ plugin/view        │          │ verdictLabel/swatchColor;       │
│      │ + GaugeRender enum.Flag + factory (ctor-inj.)   │                    │          │ factory rebuilds; model≠core dep│
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G2   │ Visitor seam: visitGauge on WorkflowItemVisitor │ core               │ G1       │ dispatchItem routes a gauge to  │
│      │ + dispatchItem branch                          │ report/            │          │ visitGauge                     │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G3   │ Matplotlib visitGauge (render-mode aware) +     │ core               │ G0,G1,G2 │ a page renders w/o error; band+ │
│      │ __H_GAUGE_IN; value-on-swatch in valueColor    │ report/            │          │ marker+pill+swatch(+value) land│
│      │ (RD#10); marker clamps, value true (RD#5)      │                    │          │ ; clamped marker, true number  │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G4   │ Qt visitGauge + GaugeWidget (labeled row; mode- │ app (spectracsPy)  │ G0,G1,G2 │ widget builds; visual check;   │
│      │ aware; pill=hex QSS, dark app; value-on-swatch  │ workflow/render    │          │ flushMetricGrid first; value   │
│      │ in valueColor RD#10; marker clamp RD#5)         │                    │          │ on swatch legible              │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G5   │ plugin_sdk exports VerdictGaugeView,            │ core sdk __init__  │ G0,G1    │ plugin can import all three    │
│      │ GaugeColorUtil, GaugeRender                     │                    │          │                                │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G6   │ RoastGaugeView preset (ctor-inj; computes       │ plugins (dev)      │ G1,G5    │ gauge is items[0] of Eval(new);│
│      │ verdictLabel/swatchColor via GaugeColorUtil,    │                    │          │ None-safe skip; cache correct  │
│      │ RD#12); prepend BAND|LABEL|SWATCH in Eval(new)  │                    │          │ (unit test)                    │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G7   │ publishing(): badge into step items + shared    │ plugins (dev)      │ G6       │ publish step carries the badge │
│      │ __pigmentRatioAndVerdict(workflow)             │                    │          │ item; same value as Eval gauge │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G8   │ Bench __runPublishing: badge above publish      │ app (bench)        │ G4,G7    │ LIMS tab shows badge + button; │
│      │ button; exclude LimsPublishView in             │                    │          │ button still works (RD#3)      │
│      │ stepViewModels (RD#3)                          │                    │          │                                │
├──────┼───────────────────────────────────────────────┼────────────────────┼──────────┼────────────────────────────────┤
│ G9   │ Rig / click-through: Eval gauge on screen +     │ —                  │ all      │ Edwin drive-and-observe: screen│
│      │ in PDF; LIMS badge; saved-run replay           │                    │          │ == PDF; workflow.json inspect  │
└──────┴───────────────────────────────────────────────┴────────────────────┴──────────┴────────────────────────────────┘
Milestones:  M-A generic core = G0·G1·G2·G5   │   M-B rendering = G3·G4   │   M-C plugin+host = G6·G7·G8   │   M-D verify = G9
```

**Suggested order:** M-A first (the reusable gauge, no roast, fully unit-tested with nothing to look at yet) →
M-B (now it draws in both targets — first visual) → M-C (roast wiring + the LIMS headline) → M-D (rig). G3 and
G4 are independent and can be done in either order / parallel; everything in M-C is strictly after M-A/M-B.

**Not in this build (related / deferred — the cached fields from G1 pre-wire them, so none blocks the build):**

```
D-a  Overview-table gauge column: _gaugeSummary(workflow) reads cached verdictLabel/swatchColor →      app        stopgap; coexists w/ VerdictView col (§8.11)
     a chip + label column in WorkflowsTableModel. Level-2, no re-run.
D-b  Plugin-DECLARES its overview-table summary(s) (D8-table-decl) — generalises MetadataField.          later      Edwin's deferred task; own small spec
     showInWorkflowsTable to result-derived label/colour; retires the hard-coded VerdictView/gauge fork.
D-c  Level-3 denormalized DB summary column (D8-summary) for scale — SPEC_workflow_persistence.          when N grows
D-d  Verdict → LIMS lab record as an analysis field-result (D8-lims-field), server-side.                 optional
```

---

## 8.11 Table / list display — reading the gauge WITHOUT re-running the workflow *(Edwin 2026-07-24)*

**The concern.** The saved-runs **table** (many workflows) will want to show a gauge summary per row — the
verdict, and the run's swatch colour. Re-executing each workflow to get that would be wasteful. This is a
*different* concern from the view-model round-trip (RD#2): that was one workflow's full fidelity; this is a
cheap **projection** across many.

**As-is (grounded).** There is already a precedent, and it does **not** re-run. The Home table
(`SpectralJobsOverviewViewModule` / `WorkflowsTableModel`) shows `Date · Verdict · Hue` + one column per
`showInWorkflowsTable` metadata field. Its `_verdictView(workflow)` walks the **deserialized** EVALUATION
`EvaluationResult.getItems()` for a `VerdictView` and reads `.roastState` / `.hueDegrees`. `VerdictView`
deliberately **stores** those (its own comment: *"so the saved-runs list reads verdict/hue off this model — no
DB column, no string parse"*). So today it's *deserialize-blob + read-a-cached-field*, never a re-run.

**Three levels of efficiency:**

1. **Re-run the plugin per row** — rejected (Edwin), wasteful.
2. **Deserialize the blob, read a cached field off the item** — the *current* `VerdictView` pattern. Cheap per
   row once the workflow is loaded; the value is a stored field, no maths.
3. **Denormalized DB summary column** on the saved-run record — the verdict/colour written as a real column at
   save, so the table query needn't deserialize the blob at all. Best at scale.

**Design for the gauge (recommended).** Follow the `VerdictView` pattern **now** (level 2), which is exactly
why §8.3 makes the gauge **cache** `verdictLabel` + `swatchColor` as stored fields:
- Add a `_gaugeView(workflow)` (mirror of `_verdictView`) and a gauge column to `WorkflowsTableModel` that
  paints a small chip from `swatchColor` + shows `verdictLabel` — **a field read, no `GaugeColorUtil`, no
  re-run.** (`SpectralJobsOverviewViewModule`.)
- This composes with RD#2: the table reads the *deserialized view-model's fields*, so those cached fields must
  serialize — they do (constructor injection stores them; `toJson` writes them; §8.3b). Same "read fields, never
  re-execute" contract, one more reason the fields (not accessors, not re-run) are the source of truth.

**For scale (level 3, when the table grows).** Promote `verdictLabel` + `swatchColor` (+ `value`) to a
denormalized **summary column** on the saved-run entity, written at save — the table then filters/sorts/paints
without touching the JSON blob. This is a `SPEC_workflow_persistence.md` concern (it rides the same
`showInWorkflowsTable` / summary-projection machinery), **not** the gauge's to own; the gauge just has to
*expose* the summary cheaply, which the cached fields already do. Deferred until the row count warrants it
(**D8-summary**).

**Coexistence with the existing Verdict column (build note).** The table's `Verdict`/`Hue` columns are wired to
`VerdictView` (the pumpkin plugin). A DEV-plugin run has a **gauge**, not a `VerdictView`, so its Verdict column
is blank today. The minimal fix is a `_gaugeSummary(workflow)` that reads `verdictLabel`/`swatchColor` and a
column that shows whichever a run has. But hard-coding "VerdictView **or** gauge" is a smell —

**Future task, NOT part of this gauge story (Edwin 2026-07-24): let the plugin declare what the overview table
renders.** The clean end-state is that the **plugin** tells the table which per-run summary(s) to show (label +
colour + value), instead of the table hard-coding `VerdictView` then gauge then the next type. Today
`SPEC_workflow_persistence.md` already lets a plugin declare **metadata** columns via
`MetadataField.showInWorkflowsTable` (§ there) — but *only metadata*, not **result-derived** summaries; this
task **generalises that same mechanism** to result-derived label/colour/value. It is **independent of this gauge
build** (own small spec when picked up); the gauge's cached `verdictLabel`/`swatchColor` merely happen to be the
shape such a declaration would surface, so nothing here blocks or depends on it. Tracked as **D8-table-decl**.

## 8.12 Deferred — the staleness / high-ratio guard *(Edwin 2026-07-24; POSTPONED, low priority)*

**Priority note.** In the app the primary user is the **miller measuring FRESH oil** — that is the audience the
verdict serves. **Sample aging is a secondary topic of less interest**, so this guard is explicitly **postponed**
(not part of any current build). Recorded here so the idea isn't lost.

**The idea.** When the Pigment ratio comes back **implausibly high**, the sample has most likely *stood and
cleared* (settling drains the haze out of the weak Q denominator → the ratio inflates — [`SPEC_capability_proof.md`](SPEC_capability_proof.md)
§11.4a/§11.4d). The guard would **softly ask** the user — *"This reading is unusually high; a fresh, well-mixed
sample would sit below ~5. Has the sample been standing? Re-agitate or prepare a fresh one."* — a **nudge, never
a gate** (the green oil drifts *up*, away from 2.8, so the verdict itself is never endangered — §11.4b silver
lining).

**Threshold — and why the raw ratio alone is a weak trigger.**
- Fresh green measures **3.7–4.1**; *aged* green reached **4.57 / 4.7 / 4.9**; the band's left edge is **5.0**.
- A fixed cutoff at **~5.2** is only a *sanity ceiling* (it fires past the band, above even the aged 4.9 seen) —
  it catches truly off-the-charts readings but **misses moderate aging** (4.5–4.9). That is acceptable, since the
  verdict is safe there anyway.
- **Sharper trigger (recommended if built): ratio-high *and* absolute Soret *low*.** An aged/cleared sample has a
  *weak* Soret (~0.40, down from ~0.5); a **genuinely greener oil has a strong Soret**. Keying on *Soret-low*
  distinguishes a **stale sample** (warn) from a legitimately high reading — a genuinely fresh, high-pigment
  green oil reads high *with a strong Soret* and must **not** false-alarm. (This mattered even more under the old
  three-oil scope; with the scope narrowed to over-roast detection — [`SPEC_capability_proof.md`](SPEC_capability_proof.md)
  §1a — it is now just good hygiene, reinforcing why the guard is postponed, not urgent.)

**Placement (when picked up).** A plugin-level warning **view item** in the Evaluation (new) step (a styled
`LabelView`, or a `warn`/`note` field surfaced on the gauge view-model), computed from the ratio + the Soret band
mean the plugin already has. Design-only; no build until requested.
