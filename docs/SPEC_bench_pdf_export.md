# SPEC — Plugin-driven PDF report (Milestone 2)

Status: **DESIGN — not implemented** (spec-first; implement on explicit request only). **Depends on Milestone 1**
([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md)) — the plugin-declared step-tabs, the shared
render visitor, and the view-model vocabulary all come from M1. Source: Edwin (2026-07-10; decisions settled in
discussion).

Grounded in the verified architecture (see M1 spec). PDF toolkit present: **matplotlib 3.7.1 `PdfPages`** + PIL +
numpy. **No** reportlab/pypdf/pikepdf installed → §5 adds **pypdf** (confirmed).

---

## 0. Concept & settled decisions

The plugin creates a PDF report as a **step of the EVALUATION phase**, driven by the plugin like the rest of the GUI.

| Decision | Landed |
|---|---|
| **Placement** | a plugin-declared **`Report` `SpectralWorkflowStep`** rendered as a **tab** in EVALUATION (next to Metrics \| Spectrum — an M1 plugin-declared step-tab) |
| **Render engine** | **matplotlib only — zero Qt widgets** render the report content; the tab shows a matplotlib-rendered **image preview** that *is* the PDF |
| **Visible content** | a **plugin-curated, cross-phase** selection via a per-view-model **`shownInReport`** flag (not a mirror of one tab) |
| **Hidden metadata** | the **whole Workflow** serialized to JSON, embedded as a PDF file attachment (the LIS payload) |
| **Embed library** | **pypdf** (pure-Python, Android-safe) — new dependency |
| **Style fidelity** | extend `EvaluationResult.toJson` to round-trip `MetricFieldViewStyle.labelBold` |
| **LIS/LIMS send** | **deferred** (the embedded JSON is its forward-compatible hook) |

**Why it's cheap:** a PDF is a **second render target for the same view-models** the plugin already declares. M1 gives
the render seam (the visitor); M2 adds a matplotlib implementation of it. Screen and paper come from one declaration.

---

## 1. The `Report` step (plugin-declared, rendered as an EVALUATION tab)

- In `evaluation(workflow)` the plugin adds a `SpectralWorkflowStep` (e.g. `role="REPORT"`, `label="Report"`) carrying
  a Qt-free **`ReportView`** descriptor (title, subtitle, logo, `embedMetadata`). Via M1's generic phase renderer this
  surfaces as a **tab** beside Metrics | Spectrum. No `ReportView` → no tab (fully plugin-driven).
- The **Report tab body is rendered by matplotlib**, not Qt: the host renders the report figures with the Agg backend,
  rasterises them, and shows them as **image previews** (a plain image container — *not* a matplotlib Qt canvas and
  *not* Qt widgets composing the content). The preview **is** the PDF, page for page.
- The tab carries a **Save / Export** action that writes those same figures to a `.pdf` (+ embedded metadata, §5).

> Depends on M1: the "plugin-declared step → tab" rendering and the shared visitor. Before M1, the Report step has no
> generic host to render it.

---

## 2. `ReportView` — the descriptor (Qt-free, new view-model)

Beside the others in `spectracsPy-model/.../model/spectral/evaluation/`:

```
class ReportView:
    def __init__(self, title, subtitle=None, logo=None, embedMetadata=True):
        self.title = title            # "Pumpkin-oil measurement report"
        self.subtitle = subtitle      # operator / run timestamp
        self.logo = logo              # optional asset key, host-resolved
        self.embedMetadata = embedMetadata   # attach the whole-Workflow JSON (§5)
```

Deliberately thin: the report **body is not listed here** — it is gathered generically from the workflow by the
`shownInReport` flags (§3). The plugin controls the body by *flagging content as it builds it*, not by re-listing it.

---

## 3. Visible content — `shownInReport` (per view-model, cross-phase)

**Fine-grained flag on the view-models.** Every renderable view-model (`SpectrumPlotView`, `MetricFieldView`,
`ColorSwatchView`, `VerdictView`, `LabelView`) gains a `shownInReport: bool` (default `False`), with a fluent setter,
e.g. `spectrumPlotView.setShownInReport(True)` / a constructor kwarg. The plugin opts content in **wherever it builds
it, in any phase**.

**Edwin's canonical example:** the **absorption `SpectrumPlotView`** is built in `processing()` and displayed in the
**PROCESSING** phase — it is *not* shown in the EVALUATION GUI. The plugin calls `setShownInReport(True)` on it → it
**appears in the PDF** but still never appears in the EVALUATION tab. So the visible report is a **plugin-curated
selection across phases**, independent of what each phase's GUI shows.

**Report body assembly (host).** The report renderer walks `workflow` → every phase → every step → its view-models
(via the M1 seam) and includes **only those with `shownInReport == True`**, in workflow order, grouped by phase. Each
is drawn by the **matplotlib** implementation of the visitor:

- `MetricFieldView` → a label/value row (bold label when `style.labelBold`).
- `ColorSwatchView` → a filled rectangle + caption.
- `VerdictView` → a headline line.
- `LabelView` → a paragraph.
- `SpectrumPlotView` → an **actual plotted curve** from `spectrum.valuesByNanometers` (matplotlib line plot).

The **same `dispatchItem` seam** as M1's Qt renderer guarantees the matplotlib output stays in lock-step with the
vocabulary.

---

## 4. The matplotlib render target (M2's half of the M1 seam)

`MatplotlibEvaluationRenderer` implements M1's `EvaluationItemVisitor`, emitting matplotlib artists onto the current
figure/page instead of Qt widgets. It is used for **both** the Report-tab preview and the saved PDF (render once →
show as image *and* `PdfPages.savefig`). No Qt import in this renderer. Pages: title/subtitle/logo (from `ReportView`),
then one region per phase-group of flagged view-models.

---

## 5. Hidden metadata — the whole Workflow, embedded

**Scope: the entire `SpectralWorkflow` is serialized** (not just the evaluation slice) — every phase → step → its
`SpectraContainer` spectra (`{nm: value}`), `EvaluationResult`, and view, plus run header
(`plugin`, `user`, `timestampIso`). This is the complete machine-readable record for a LIS: raw acquisition through
verdict, full provenance.

- **Serialization:** the entities already expose `toJson()` (`Spectrum`, `SpectraContainer`, `EvaluationResult`,
  workflow graph). The payload is a `workflow.toReportJson()` walk over `getPhases()`/`getSteps()`.
- **Completeness fix (required):** `EvaluationResult.toJson()` currently **drops `MetricFieldViewStyle`** — extend it
  to round-trip `"style": {"labelBold": bool}` under the `"metric"` type, so the embedded metric models are faithful.
  Additive; also fixes persisted-run reloads losing bold styling.
- **Embedding (pypdf):** matplotlib cannot attach a file to a PDF. So: matplotlib writes the visible pages to a temp
  PDF; **pypdf** attaches `workflow.json` as a proper `/EmbeddedFiles` entry (the standard mechanism, cf.
  Factur-X/ZUGFeRD) and writes the final PDF. Add pypdf to `requirements` + the buildozer recipe (pure-Python →
  Android-safe).

**The clean split:** *visible* report = the `shownInReport` **subset** (curated); *hidden* metadata = the **whole
Workflow** (complete). Curation drives what a human reads; completeness drives what a machine ingests.

---

## 6. Control flow (plugin drives)
1. Plugin, across `processing()`/`evaluation()`: builds its view-models as today, calls `setShownInReport(True)` on
   the ones for the report, and adds a `Report` step with a `ReportView` in `evaluation()`.
2. Host (M1 generic renderer): renders EVALUATION step-tabs incl. the **Report** tab = matplotlib preview + Save.
3. Save → host: matplotlib pages from the flagged view-models → temp PDF → pypdf embeds `workflow.json` → final PDF;
   offer open/save.
4. (Deferred §7) a PUBLISHING `Send to LIS` step transmits it.

---

## 7. Deferred — send to an external LIS/LIMS (plugin-owned)
Not designed now. When built: a plugin-declared `Send to LIS` step (naturally in **PUBLISHING**); the host transmits
the report to a configured lab system. The **embedded whole-Workflow JSON (§5) is the payload** a LIS ingests without
parsing the visuals. **Concrete target: SENAITE LIMS** (Edwin runs a **local** instance) — integration is a push to its
**JSON REST API (`senaite.jsonapi`)**, creating an AnalysisRequest / posting results (SENAITE is Plone/Zope, not native
FHIR); the local instance means the send can be tested end-to-end. The PDF travels as the human-readable rendition
alongside the JSON. HL7 v2 / ASTM / FHIR remain possible for *other* LIS targets later, but SENAITE's REST API is first.

---

## 8. Dependencies & platform
- **matplotlib / PIL / numpy** — present. **pypdf** — new (embedding). pikepdf rejected (C-ext, worse for Android).
- **Desktop-first:** the bench is master-only/desktop → PDF export is desktop-first; matplotlib on Android is heavy →
  Android PDF **deferred** (revisit with the Android port). pypdf is Android-safe.
- **Save/dialog:** honour no-native-windows — in-window save flow or a fixed `reports/` dir + open; decide at impl.

## 9. Out of scope / unchanged
Pipeline, calibration, evaluation maths, persistence (report reads the in-memory workflow). Wiring the report into the
end-user wizard is free once M1 + this land (both hosts share the renderer) but verifying it there is a follow-up.

## Verification (when implemented)
1. EVALUATION shows a **Report** tab only because the plugin declared a `ReportView`.
2. The Report-tab preview equals the saved PDF, and contains exactly the `shownInReport`-flagged content — including
   the PROCESSING absorption plot, which is **not** in the EVALUATION GUI.
3. No matplotlib/pypdf/Qt import leaks into `plugin_sdk` (plugin stays Qt-free).
4. `pdfdetach -list` shows an embedded `workflow.json`; it round-trips **every** phase's spectra and the
   `MetricFieldView` incl. `style.labelBold`.
