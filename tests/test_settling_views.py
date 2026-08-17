"""P8/P9 — SeriesPlotView and TableView, on BOTH render targets.

⭐ The point of the render seam (SPEC_plugin_driven_convergence.md §2A) is that screen and paper come
from ONE declaration and cannot drift. A new view-model type is therefore only really added once both
targets draw it — so this test renders the same two views through Qt and through matplotlib.

⭐⭐ And the third use is the reason the view type is worth its two renderers at all
(SPEC_settled_measurement.md §18.1): the live convergence trace, the Settling step-tab and the PDF page
are three USES of one object, not three features.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sciens.spectracs.plugin_sdk import SeriesPlotView, TableView
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

RECORD = {
    "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 1195.9,
    "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.82,
    "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": {"valueKey": "qPercent", "value": 13.2744, "t": 999.3,
               "readAs": "VERTEX", "branch": "was-clearing"},
    "notes": ["215.0s re-clouding — the gate was reset"],
    "rows": [{"t": minutes * 60.0, "qPercent": qPercent, "valley": valley, "soret": 0.9,
              "n": 50, "nAccepted": 49, "isDecisionRow": True}
             for minutes, valley, qPercent in [(0.275, 0.945454, 26.0574), (3.551, 0.088927, 14.0030),
                                               (6.827, 0.045262, 13.4689), (16.655, 0.025733, 13.2744),
                                               (23.207, 0.032076, 13.4737)]],
}


def graphTab(group, label):
    """A single-graph tab's SeriesPlotView. ⭐ Every curve lives in its own full-height tab; the Overview
    is TEXT (Edwin, at the rig 2026-08-17 — this reverses §18.8's combined-first rule)."""
    return dict(group.tabs)[label]


def summaryOf(group):
    """The Overview tab: a LIST of view-models (a heading + aligned metric rows), not a chart."""
    assert group.tabs[0][0] == "Overview"
    return group.tabs[0][1]


def test_each_curve_gets_its_own_panel_in_its_own_units():
    step = DevSpectralPlugin().settlingView(RECORD)

    # ⛔ THE CRITERION NEEDS ITS OWN PANEL: theta is a RATE (A/min) and A_valley is an ABSORBANCE, so
    # drawing theta on the A_valley axis asserts an equivalence that does not exist (rig, 2026-08-17).
    assert [label for label, _ in step.tabs][1:4] == ["Q%", "Turbidity", "Rate"]
    assert graphTab(step, "Turbidity").panels[0]["levels"] == [], \
        "the rate threshold was drawn on the absorbance axis again"
    assert 0.0017 in [level["value"] for level in graphTab(step, "Rate").panels[0]["levels"]]
    # ⭐ log ONLY where the data spans a decade: A_valley falls 0.945 -> 0.026 here (36x), Q% does not.
    assert graphTab(step, "Turbidity").panels[0]["scale"] == "log"
    assert graphTab(step, "Q%").panels[0]["scale"] == "linear"
    # ⭐ the latched answer is marked, or the reader cannot see WHICH row became the number
    points = graphTab(step, "Q%").panels[0]["points"]
    assert points and points[0]["y"] == pytest.approx(13.2744)


def test_the_overview_is_a_TEXT_summary_with_no_chart_in_it():
    # ⭐ Edwin, at the rig: three stacked panels left each of them short, and the numbers that answer
    # "what did I measure and why can I trust it" are TEXT. ⚠ This REVERSES §18.8's combined-first rule.
    items = summaryOf(DevSpectralPlugin().settlingView(RECORD))
    assert isinstance(items, list)
    assert not any(hasattr(item, "panels") for item in items), "a chart crept back into the Overview"

    fields = {item.label: item.value for item in items if hasattr(item, "value")}
    assert fields["Outcome"] == "SETTLED_AFTER_CLEARING"
    assert fields["Q%"] == "13.27"
    assert fields["Read as"] == "VERTEX · was-clearing"
    assert "inside" in fields["Verdict domain"]
    # ⭐ the audit line: without it a saved run is a picture, not a record
    assert fields["Evaluator"] == "dev-clearing clearing-1.0"
    assert fields["Distinct frames"] == "82.0 %"


def test_a_run_with_no_value_says_so_instead_of_showing_a_number():
    record = dict(RECORD, outcome="NEVER_SETTLED", answer=None, clearingSeconds=None)
    fields = {item.label: item.value
              for item in summaryOf(DevSpectralPlugin().settlingView(record)) if hasattr(item, "value")}
    assert fields["Outcome"] == "NEVER_SETTLED"
    assert "none" in fields["Value"]
    assert "Q%" not in fields, "a value was shown for a run that produced none"


def test_no_record_means_NO_settling_view_at_all():
    # ⛔ §18.4: a plain-burst capture has no trajectory, and an empty graph is worse than a missing tab.
    assert DevSpectralPlugin().settlingView(None) is None
    assert DevSpectralPlugin().settlingView({"rows": []}) is None


def test_both_render_targets_draw_the_series_plot():
    view = graphTab(DevSpectralPlugin().settlingView(RECORD), "Turbidity")

    from PySide6.QtWidgets import QApplication
    from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
    application = QApplication.instance() or QApplication([])
    widget = QtWorkflowRenderer().render([view])
    assert widget is not None and widget.layout().count() > 0

    from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
    figures = MatplotlibWorkflowRenderer().render(_reportView(), [("PROCESSING", [view])])
    assert figures, "the report produced no page for the settling view"
    assert len(figures[0].axes) >= 1


def test_both_render_targets_draw_the_generic_table():
    table = (TableView(title="Decisions", caption="every decision row")
             .addColumn("t", "t", "s", "%.1f").addColumn("valley", "A_valley", None, "%.4f")
             .addColumn("qPercent", "Q%", None, "%.2f"))
    for row in RECORD["rows"]:
        table.addRow(row)

    assert table.textRows()[0][2] == "26.06", "per-column formatting is the plugin's, and it was ignored"

    from PySide6.QtWidgets import QApplication
    from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
    application = QApplication.instance() or QApplication([])
    widget = QtWorkflowRenderer().render([table])
    assert widget is not None and widget.layout().count() > 0

    from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
    figures = MatplotlibWorkflowRenderer().render(_reportView(), [("PROCESSING", [table])])
    assert figures


def test_one_tab_per_graph_each_holding_exactly_one_panel():
    tabs = DevSpectralPlugin().settlingView(RECORD).tabs
    byLabel = dict(tabs)
    assert all(len(byLabel[label].panels) == 1 for label in ("Q%", "Turbidity", "Rate"))
    # ⛔ tabs FLATTEN to sections on paper (§18.8): the graph tabs stay out of the report so the same
    # curves are not printed once per page.
    assert all(byLabel[label].isShownInReport is False for label in ("Q%", "Turbidity", "Rate"))


def test_sub_tabs_appear_only_when_they_have_something_to_say():
    # ⭐ §18.8: conditional inclusion is entirely plugin-side — the plugin simply does not add a tab when
    # there is nothing in it, so a miller's report never carries a page of empty diagnostics.
    quiet = dict(RECORD, rows=[dict(row, nAccepted=50, soret=0.9) for row in RECORD["rows"]])
    labels = [label for label, _ in DevSpectralPlugin().settlingView(quiet).tabs]
    # ⭐ Health is the conditional one: nothing dipped, so it is absent. Decisions rides along because a
    # trajectory exists, and on the master bench that table is wanted (relaxed after the rig).
    assert "Health" not in labels, "Health appeared with nothing to say: %s" % labels
    assert labels[0] == "Overview"

    # nAccepted dipping (which is EXPECTED while clearing, §23/V2) is exactly what Health exists to show
    noisy = dict(RECORD, rows=[dict(row, nAccepted=41) for row in RECORD["rows"]])
    labels = [label for label, _ in DevSpectralPlugin().settlingView(noisy).tabs]
    assert "Health" in labels

    # ⚠ Decisions needs a TRAJECTORY, not a single row — on the master bench even three rows of "what the
    # gate compared" is what the operator wants (relaxed from 8 after the rig, 2026-08-17).
    assert "Decisions" in labels
    single = dict(RECORD, rows=RECORD["rows"][:1])
    assert "Decisions" not in [label for label, _ in DevSpectralPlugin().settlingView(single).tabs]


def test_a_table_renders_a_record_it_knows_nothing_about():
    # ⭐ §18.8: the fit that makes TableView worth having — `columns` + `rows` IS a MonitorRecord, so the
    # host draws any plugin's trajectory without one line of plugin-specific knowledge.
    columns = [{"key": "widget", "label": "Widget", "unit": "flurbs", "format": "%.3f"}]
    table = TableView(title="Someone else's plugin", columns=columns,
                      rows=[{"widget": 1.5}, {"widget": 2.25}])
    assert table.headerLabels() == ["Widget (flurbs)"]
    assert table.textRows() == [["1.500"], ["2.250"]]


def _reportView():
    from sciens.spectracs.plugin_sdk import ReportView
    return ReportView(title="Test report")
