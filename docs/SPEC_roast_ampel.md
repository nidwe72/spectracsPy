# SPEC — The Roast Ampel (green / amber / red oil-quality traffic light)

Status: **DESIGN — implement on explicit request only.** Raised by Edwin 2026-07-22/23. Grew out of the
colour-mapping discussion on top of the Capability Proof results. "Ampel" = German/Austrian for **traffic
light**; that is exactly what this is — a three-state green/amber/red verdict the miller can read at a glance.
An **interactive mockup + rendered A4 PDF** exist at `spectracs-references/ampel/roast_ampel_mockup.{html,pdf}`
(page order: concept → miller's read → K/L/M/N samples). Not implemented in the app yet.

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

## 2. The three states (traffic-light thresholds)

| Ratio band | Verdict | Light | Miller action |
|---|---|---|---|
| **≥ 2.8** | **good — green** | 🟢 | On the right path — keep the roast profile. |
| **2.6 – 2.8** | **probably too brown** | 🟡 | Watch it — trend to browner; consider easing the roast. |
| **< 2.6** | **definitely too brown** | 🔴 | Over-roasted — reduce roast intensity (lower temp / shorter time). |

**⚠ Thresholds 2.8 / 2.6 are PROVISIONAL / illustrative — not yet calibrated.** They were chosen to sit inside
the *empty gap* the proof found (no sample between best-brown **2.59** and worst-green **3.67**). They are good
enough for the mockup and the story, **not** for a field verdict. See §5 (calibration) — this is the gating
open item before the Ampel ships as a real control.

Validation snapshot (from `SPEC_capability_proof.md` §11.2a):

| Sample | Oil | Drops | Ratio | Verdict under the provisional bands |
|---|---|---|---|---|
| K | Spar Premium (green) | 2 | 3.89 | good — green |
| L | Spar Premium (green) | 3 | 3.76 | good — green |
| M | Hofer Bellasan (brown) | 3 | 2.48 | definitely too brown |
| N | Hofer Bellasan (brown) | 2 | 2.35 | definitely too brown |

Group means: green K,L = **3.83 ± 0.13**, brown M,N = **2.41 ± 0.08**; Δ/noise ≈ **13.5**. No real sample lands
in the amber "probably" band yet — that band is currently only exercised by dragging the mockup's probe.

> **Amber is a shared readiness item with the Capability Proof.** Getting **one real sample into the 2.6–2.8
> amber zone** validates this middle state *and* is one of the two remaining items that complete the Capability
> Proof (the other being the third "too-green" oil). See `SPEC_capability_proof.md` §11.6. Until an amber sample
> exists, the "probably too brown" verdict is untested by real data.

---

## 3. The colour rendering (band + swatch)

Beside the verdict light, each measurement shows an **olive band** (green-olive → brown-olive) with a marker at
the sample's ratio, and a **solid swatch** below painted with the band colour at that spot. This is the "reads
like real oil" cue on top of the abstract light.

Design of the colour map (all interpolation in **OKLab** so olive mid-tones stay olive):

- **Marker position** is *linear* in ratio across the band (anchored to the group means 3.83 → 2.41).
- **Colour is non-linear**, two-segment, pivoting at `BROWN_START = 2.8`:
  - **Above 2.8** — a *subtle* olive drift: fresher green `#9B9E57` at the top easing to muted olive `#8B8952`
    at the pivot. (So K reads a hair fresher than L rather than identical.)
  - **Below 2.8** — the **brown kick-in**: muted olive `#8B8952` → brown-olive `#6E5A34`, full brown at 2.41.
- Anchors are **illustrative olives**, chosen by eye — *not* measured intrinsic colours (see §5).

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

## 6. App integration (design sketch)

Where it lands and how (all DESIGN):

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

`spectracs-references/ampel/roast_ampel_mockup.html` — self-contained, theme-aware. Per-measurement units
(band + marker + swatch + verdict pill) for K/L/M/N, a group-separation panel, and an interactive **probe**
slider (drag through the ratio range to see the colour bend and the light change, including the amber band no
real sample occupies). All colour maths (OKLab interpolation, the two-segment `colorRgb`, the `verdict()`
thresholds) is inline JS and is the reference implementation for the numbers above.
