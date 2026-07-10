# SPEC — Plugin-driven PDF report (Milestone 2)

Status: **IMPLEMENTED (2026-07-11)** — built, click-through verified on the dev bench, uncommitted→committed. Rode on
**Milestone 1** ([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md)) — the plugin-declared
step-tabs, the shared render visitor, and the view-model vocabulary all come from M1. Source: Edwin (2026-07-10; all
decisions settled over three rubber-duck rounds, then implemented + refined 2026-07-10/11).

## Status — what landed (2026-07-11)

Built as phases **D0–D8** (§10), then extended by on-device feedback:

- **D0** deps: matplotlib + Pillow + **pypdf** pinned in `requirements.txt`; pypdf added to `requirements-android-main.txt`
  + `android/spike/buildozer.spec` (matplotlib on Android deferred with the port).
- **D1** predicate boolean **`isShownInReport`** (+ `setShownInReport`) on the six renderable view-models via a tiny
  `ReportableView` mixin; `MetricFieldViewStyle.labelBold` → **`isLabelBold`** (+ `setLabelBold`).
- **D2** the lossy central `EvaluationResult.toJson` ladder replaced by **per-view-model `toJson()`/`fromJson()`** (type-
  tagged) + `ViewModelFactory`; now faithful — traces/bands/markers, capture descriptors and metric style all round-
  trip (also fixes persisted-run reload). `test_workflow_persistence` stays green.
- **D3** **`ReportView`** descriptor + **`SpectralWorkflow.toReportJson()`** (whole-workflow walk: header + every phase →
  step → spectra `{nm:value}` + serialized view-models).
- **D4** Qt-free **`MatplotlibWorkflowRenderer`** (implements the M1 `WorkflowItemVisitor`) → A4-portrait `PdfPages`,
  `resource/logo.png` in every page header, real curves/bands/markers.
- **D5/D6** host **`WorkflowReportBuilder`** (QImage→PIL, preview pixmaps, native `QFileDialog` save) → matplotlib pages
  to a temp PDF, then **pypdf** embeds `workflow.json` + each flagged capture as a named `capture_*.png` attachment.
  The bench EVALUATION renders a **Report** step-tab (preview + Save) only because the plugin declared a `ReportView`.
- **D7** `DevSpectralPlugin` flags report content; **D8** verified end-to-end (multi-page PDF; `pdfdetach` lists
  `workflow.json` + captures; no pypdf/renderer leak into `plugin_sdk`).

**Refinements after the first walk-through (all on the Report tab):**
- **Fit-to-width preview** — new reusable `PdfPreviewWidget` (vertical, scales pages to the viewport width, H-scrollbar
  off, never upscales past native). **Zero** horizontal padding so the page hugs the width on every device.
- **"Open bigger"** button (beside Save) — opens the pages in a **full-window** in-window view via new
  `InWindowDialog.showWidget(...)`; offered on **every** device (desktop + phone).
- **Report content grew, plugin-declared:** ACQUISITION now flags each role's **captured frame + its spectrum**
  (host fills `.image`/`.spectrum`); PROCESSING flags the **Reference-vs-Sample overlay** *and* the **absorption**
  curve; EVALUATION flags the **metrics** *and* the **band-marked Q spectrum**.
- **Capture-chrome visibility (`CaptureView`)** — new plugin flags `showFramesControl` / `showExposureControls`
  (+ setters), **hidden by default**; the bench honours them. `DevSpectralPlugin` leaves them hidden (auto-exposure
  runs under the hood); any plugin can opt in.

**Known follow-ups (not blocking):** wiring the Report into the Pumpkin plugin + end-user wizard (free once declared —
both hosts share the renderer); the LIS/LIMS send (§7, SENAITE) stays deferred. Pre-existing test debt in
[`SPEC_test_hygiene_debt.md`](SPEC_test_hygiene_debt.md).

---

### Original design (as settled 2026-07-10)

Grounded in the **as-built M1 architecture** (names verified 2026-07-10). PDF toolkit present: **matplotlib 3.7.1
`PdfPages`** + PIL + numpy (matplotlib/PIL present in the venv but undeclared). **No** pypdf/pikepdf/reportlab
installed → §8 adds **pypdf** (confirmed).

> **Naming reconciliation (this spec predated M1 landing).** M1 shipped with different names than earlier drafts here
> assumed. This spec now uses the **real** names: the visitor is **`WorkflowItemVisitor`** + **`dispatchItem`** (not
> "EvaluationItemVisitor"); the Qt implementation is **`QtWorkflowRenderer`** (not "QtEvaluationRenderer"); view-models
> live in **`model.spectral.plugin.view`** (not "model.spectral.evaluation/viewmodel"). Also: `visitSpectrumPlot`
> already draws real pyqtgraph curves in M1 — there is **nothing to upgrade**; the matplotlib target just mirrors it.

---

## 0. Concept & settled decisions

The plugin creates a PDF report as a **step of the EVALUATION phase**, driven by the plugin like the rest of the GUI.

| Decision | Landed |
|---|---|
| **Placement** | a plugin-declared **`Report` `SpectralWorkflowStep`** rendered as a **tab** in EVALUATION (beside Metrics \| Spectrum — an M1 plugin-declared step-tab) |
| **Render engine** | **matplotlib only — zero Qt widgets** render the report content; the tab shows a matplotlib-rendered **image preview** that *is* the PDF |
| **Visible content** | a **plugin-curated, cross-phase** selection via a per-view-model **`isShownInReport`** flag (not a mirror of one tab) |
| **Serialization** | **generic per-view-model `toJson()`/`fromJson()`** (type-tagged) — replaces today's central lossy ladder; `EvaluationResult` + the workflow walk just compose it |
| **Hidden metadata** | the **whole Workflow** serialized to JSON (`SpectralWorkflow.toReportJson()`), embedded as a PDF file attachment (the LIS payload) |
| **Captured images** | **not** in the JSON (no base64 bloat); each flagged capture is **embedded as a named PDF attachment** (`capture_*.png`) and shown on the page — extractable on command, descriptor carries its `attachmentName` |
| **Embed library** | **pypdf** (pure-Python, Android-safe) — new dependency |
| **Boolean naming** | predicate-form: attribute `isShownInReport` / `isLabelBold`; fluent setters `setShownInReport(bool)` / `setLabelBold(bool)` returning `self` |
| **Logo** | **`resource/logo.png`** placed in **every page header** (matplotlib + PIL, Qt-free; the app-header logo itself is an inline SVG, so we use the committed raster) |
| **Save UX** | native `QFileDialog` save (same convention as "save PNG" in the capture dev view) — bench is desktop/master-only |
| **Scope this milestone** | **bench + `DevSpectralPlugin` only**; Pumpkin plugin + end-user wizard are free-but-verify-later follow-ups (§9) |
| **Style fidelity** | the generic serializer round-trips `MetricFieldViewStyle.isLabelBold` (also fixes persisted-run reloads losing bold) |
| **LIS/LIMS send** | **deferred** (the embedded JSON is its forward-compatible hook; concrete target SENAITE, §7) |

**Why it's cheap:** a PDF is a **second render target for the same view-models** the plugin already declares. M1 gives
the render seam (`WorkflowItemVisitor`/`dispatchItem`); M2 adds a matplotlib implementation of it. Screen and paper come
from one declaration.

---

## 1. The `Report` step (plugin-declared, rendered as an EVALUATION tab)

- In `evaluation(workflow)` the plugin adds a `SpectralWorkflowStep` (e.g. `role="REPORT"`, `label="Report"`) carrying
  a Qt-free **`ReportView`** descriptor (title, subtitle, logo, `embedMetadata`). Via M1's generic
  `WorkflowPhaseRenderer` this surfaces as a **tab** beside Metrics | Spectrum. No `ReportView` → no tab (fully
  plugin-driven).
- The **Report tab body is rendered by matplotlib**, not Qt: the host renders the report figures with the Agg backend,
  rasterises them, and shows them as **image previews** (a plain image container — *not* a matplotlib Qt canvas and
  *not* Qt widgets composing the content). The preview **is** the PDF, page for page.
- The tab carries a **Save / Export** action that writes those same figures to a `.pdf` (+ embedded metadata, §5) via a
  native save dialog.

> Depends on M1: the "plugin-declared step → tab" rendering and the shared visitor. Before M1, the Report step has no
> generic host to render it.

---

## 2. `ReportView` — the descriptor (Qt-free, new view-model)

Beside the others in `spectracsPy-model/.../model/spectral/plugin/view/`:

```
class ReportView:
    def __init__(self, title, subtitle=None, logo=None, embedMetadata=True):
        self.title = title            # "Pumpkin-oil measurement report"
        self.subtitle = subtitle      # operator / run timestamp
        self.logo = logo              # optional asset key; None -> host default resource/logo.png
        self.embedMetadata = embedMetadata   # attach the whole-Workflow JSON (§5)
```

Deliberately thin: the report **body is not listed here** — it is gathered generically from the workflow by the
`isShownInReport` flags (§3). The plugin controls the body by *flagging content as it builds it*, not by re-listing it.
`ReportView` is a **passive descriptor** (it does not itself flow through `dispatchItem`; the host reads it to build the
report frame: header, logo, save action).

---

## 3. Visible content — `isShownInReport` (per view-model, cross-phase)

**Fine-grained flag on the view-models.** Every renderable view-model (`SpectrumPlotView`, `MetricFieldView`,
`ColorSwatchView`, `VerdictView`, `LabelView`, `SpectrumCaptureView`) gains a predicate attribute **`isShownInReport`**
(default `False`) with a fluent **`setShownInReport(True)`** (returns `self`). The plugin opts content in **wherever it
builds it, in any phase**.

**Edwin's canonical example:** the **absorption `SpectrumPlotView`** is built in `processing()` and displayed in the
**PROCESSING** phase — it is *not* shown in the EVALUATION GUI. The plugin calls `setShownInReport(True)` on it → it
**appears in the PDF** but still never appears in the EVALUATION tab. So the visible report is a **plugin-curated
selection across phases**, independent of what each phase's GUI shows.

**Report body assembly (host).** The report renderer walks `workflow` → every phase → every step → its view-models
(via the M1 `dispatchItem` seam) and includes **only those with `isShownInReport == True`**, in workflow order, grouped
by phase. Each is drawn by the **matplotlib** implementation of the visitor:

- `MetricFieldView` → a label/value row (bold label when `style.isLabelBold`).
- `ColorSwatchView` → a filled rectangle + caption.
- `VerdictView` → a headline line.
- `LabelView` → a paragraph.
- `SpectrumPlotView` → an **actual plotted curve** (all traces + bands + markers, mirroring `QtWorkflowRenderer`).
- `SpectrumCaptureView` → the host-filled image, drawn on the page **and** embedded as a named attachment (§5b).

The **same `dispatchItem` seam** as M1's Qt renderer guarantees the matplotlib output stays in lock-step with the
vocabulary.

---

## 4. The matplotlib render target (M2's half of the M1 seam)

`MatplotlibWorkflowRenderer` implements M1's **`WorkflowItemVisitor`**, emitting matplotlib artists onto the current
figure/page instead of Qt widgets. It is used for **both** the Report-tab preview and the saved PDF (render once → show
as image *and* `PdfPages.savefig`). No Qt import in this renderer.

- **Page format:** **A4 portrait**, auto-paginating — page 1 header = title / subtitle / **logo**, then the flagged
  content flows in workflow order grouped by phase, continuing onto further pages via `PdfPages` when it overflows.
- **Per-page header logo:** `resource/logo.png` loaded via PIL and placed in **every** page's header band (Qt-free;
  Android-safe). `ReportView.logo`, when set, overrides the default asset key (host-resolved).

---

## 5. Hidden metadata — the whole Workflow, embedded (generic serialization)

**Scope: the entire `SpectralWorkflow` is serialized** (not just the evaluation slice) — every phase → step → its
`SpectraContainer` spectra (`{nm: value}`), its `EvaluationResult` view-models, plus a run header
(`plugin`, `user`, `timestampIso`). This is the complete machine-readable record for a LIS: raw acquisition through
verdict, full provenance.

**Generic serialization (the settled fix).** Today all serialization lives in one central `EvaluationResult.toJson`
isinstance-ladder, which is **lossy by drift** — it drops `SpectrumPlotView` traces/bands/markers, omits
`SpectrumCaptureView`, and drops `MetricFieldViewStyle`. Replace it with a **uniform per-view-model protocol**:

- Each renderable view-model implements **`toJson()`** (emitting a `"type"` tag) and a classmethod **`fromJson()`**; a
  tiny `type → class.fromJson` **factory** reconstructs. `EvaluationResult.toJson`/`fromJson` stop knowing types — they
  just call `item.toJson()` / the factory.
- **Faithful by construction:** the model that owns a field serializes it, so new fields can't silently vanish.
- **Bonus:** this is the same path persisted-run reload uses — the generic protocol also fixes reloads currently losing
  bold styling (round-trips `isLabelBold`).
- **Captured images carry a descriptor only** — `caption`, `cropped`, `roiOverlay`, and an `attachmentName` (§5b) — but
  **not** the raw pixels (the *data* is the extracted spectrum, already embedded via `SpectraContainer`).

**Workflow walk.** `SpectralWorkflow.toReportJson()` traverses `getPhases()` → `getSteps()` → each step's
`getContainer()` spectra + `getEvaluationResult().getItems()` (each `item.toJson()`), tagged by phase/step. This walk
does not exist today; the getters do.

**Embedding (pypdf):** matplotlib cannot attach a file to a PDF. So: matplotlib writes the visible pages to a temp PDF;
**pypdf** attaches `workflow.json` as a proper `/EmbeddedFiles` entry (the standard mechanism, cf. Factur-X/ZUGFeRD) and
writes the final PDF.

### 5b. Captured images as named attachments (extractable on command)

Captured photos ride the **same `/EmbeddedFiles` rail** as `workflow.json`: each `SpectrumCaptureView` with
`isShownInReport` is (a) **drawn visibly** on its page, and (b) **embedded as its own named attachment** —
`capture_reference.png`, `capture_sample.png`, … Any PDF tool (`pdfdetach -list`, pypdf) pulls it out by name **on
command**. To close the loop, the capture's JSON descriptor carries its `attachmentName`, so a downstream tool reads
`workflow.json` → `"attachment": "capture_reference.png"` → extracts exactly that image. Lean JSON, addressable images.

**The clean split:** *visible* report = the `isShownInReport` **subset** (curated); *hidden* metadata = the **whole
Workflow** JSON (complete) **+ named image attachments** (addressable). Curation drives what a human reads;
completeness drives what a machine ingests.

---

## 6. Control flow (plugin drives)
1. Plugin, across `processing()`/`evaluation()`: builds its view-models as today, calls `setShownInReport(True)` on the
   ones for the report, and adds a `Report` step with a `ReportView` in `evaluation()`.
2. Host (M1 generic renderer): renders EVALUATION step-tabs incl. the **Report** tab = matplotlib preview + Save.
3. Save → host: matplotlib pages from the flagged view-models → temp PDF → pypdf embeds `workflow.json` **and** the
   flagged `capture_*.png` attachments → final PDF; native save dialog → open/save.
4. (Deferred §7) a PUBLISHING `Send to LIS` step transmits it.

---

## 7. Deferred — send to an external LIS/LIMS (plugin-owned)
Not designed now. When built: a plugin-declared `Send to LIS` step (naturally in **PUBLISHING**); the host transmits the
report to a configured lab system. The **embedded whole-Workflow JSON (§5) is the payload** a LIS ingests without
parsing the visuals. **Concrete target: SENAITE LIMS** (Edwin runs a **local** instance) — integration is a push to its
**JSON REST API (`senaite.jsonapi`)**, creating an AnalysisRequest / posting results (SENAITE is Plone/Zope, not native
FHIR); the local instance means the send can be tested end-to-end. The PDF travels as the human-readable rendition
alongside the JSON. HL7 v2 / ASTM / FHIR remain possible for *other* LIS targets later, but SENAITE's REST API is first.

---

## 8. Dependencies & platform
- **matplotlib / PIL / numpy** — present in the venv but **undeclared**; add matplotlib + PIL to `requirements.txt` /
  `requirements-android-main.txt`. **pypdf** — new (embedding); add everywhere. pikepdf rejected (C-ext, worse for
  Android). Also add to the Android `buildozer.spec` requirements line (`android/spike/buildozer.spec`).
- **Desktop-first:** the bench is master-only/desktop → PDF export is desktop-first; matplotlib on Android is heavy →
  Android PDF **deferred** (revisit with the Android port). pypdf is Android-safe.
- **Save/dialog:** native `QFileDialog.getSaveFileName` (existing convention), defaulting the filename; append `.pdf`.

---

## 9. Out of scope / unchanged
Pipeline, calibration, evaluation maths, persistence (report reads the in-memory workflow). This milestone wires the
report into **`DevSpectralPlugin` on the bench only**. Wiring it into the **Pumpkin plugin** and the **end-user wizard**
is free once this lands (both hosts share the renderer) — but declaring+verifying it there is a follow-up.

---

## 10. Implementation phases (tabular)

Ordered; each phase compiles/imports clean before the next. Model repo first (D1–D3), then render (D4), host (D5–D6),
plugin (D7), verify (D8). D0 can run anytime.

| Phase | Scope | Deliverable | Verify (gate) |
|---|---|---|---|
| **D0** | Deps | matplotlib + PIL + **pypdf** → `requirements.txt`, `requirements-android-main.txt`, `android/spike/buildozer.spec`; `pip install pypdf` in venv | `import pypdf`, `from matplotlib.backends.backend_pdf import PdfPages` OK |
| **D1** | Model — booleans | add `isShownInReport` (+ `setShownInReport`) to the 6 renderable view-models; rename `MetricFieldViewStyle.labelBold` → **`isLabelBold`** (+ `setLabelBold`), update all references (bench metrics, `QtWorkflowRenderer.visitMetricField`) | app imports; bench bold ratio labels still render bold |
| **D2** | Model — generic serialization | per-view-model `toJson()`/`fromJson()` (type-tagged) + `type→class` factory; `EvaluationResult.toJson`/`fromJson` delegate; drop the central ladder | round-trip unit test: every view type incl. plot traces/bands/markers, `SpectrumCaptureView` descriptor, `isLabelBold` survive to-and-back |
| **D3** | Model — descriptor + walk | `ReportView`; `SpectralWorkflow.toReportJson()` walking phases→steps→(spectra + `item.toJson()`) + run header | JSON contains every phase's spectra `{nm:value}` and every step's items |
| **D4** | Render — matplotlib target | `MatplotlibWorkflowRenderer(WorkflowItemVisitor)`; A4-portrait `PdfPages`; `resource/logo.png` per-page header; renders `isShownInReport` items grouped by phase (real curves) | offscreen: figures + a temp `.pdf` produced; a `SpectrumPlotView` draws its curve |
| **D5** | Host — Report tab | `WorkflowPhaseRenderer`/bench renders a `REPORT` step = matplotlib **preview image** + **Save** action (native dialog) | Report tab appears **only** when the plugin declared a `ReportView` |
| **D6** | Host — PDF assembly + embedding | Save → matplotlib pages → temp PDF → **pypdf** embeds `workflow.json` **and** named `capture_*.png` attachments → final PDF | `pdfdetach -list` shows `workflow.json` + each flagged capture image |
| **D7** | Plugin — `DevSpectralPlugin` | flag PROCESSING absorption plot + EVALUATION metrics + verdict via `setShownInReport(True)`; declare a `ReportView` in `evaluation()` | bench EVALUATION shows a Report tab; the PROCESSING absorption plot is **in the PDF** but **not** in the EVALUATION GUI |
| **D8** | Verify — end-to-end | offscreen render + on-device click-through | preview == saved PDF; attachments round-trip; **no matplotlib/pypdf/Qt import leaks into `plugin_sdk`** (plugin stays Qt-free) |

**Dependency order:** D1→D2→D3 (model) → D4 (needs D1–D3) → D5 (needs D4) → D6 (needs D5 + D0's pypdf) → D7 (needs
D3–D6) → D8 (last). D0 independent.

---

## Verification (acceptance)
1. EVALUATION shows a **Report** tab only because the plugin declared a `ReportView`.
2. The Report-tab preview equals the saved PDF, and contains exactly the `isShownInReport`-flagged content — including
   the PROCESSING absorption plot, which is **not** in the EVALUATION GUI.
3. No matplotlib/pypdf/Qt import leaks into `plugin_sdk` (plugin stays Qt-free).
4. `pdfdetach -list` shows an embedded `workflow.json` **and** the named `capture_*.png` image(s); `workflow.json`
   round-trips **every** phase's spectra and the `MetricFieldView` incl. `style.isLabelBold`, and each capture
   descriptor's `attachmentName` matches an embedded image.
</content>
</invoke>
