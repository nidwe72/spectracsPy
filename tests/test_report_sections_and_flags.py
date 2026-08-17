"""What actually reaches the PDF — D1 (§27.13b), F3/W6 (§27.14) and D4 (§27.14a).

⭐ These are the measurements that found the defects, turned into gates:
  * a settled run prints its summary AND its three curves — but NOT the two diagnostic tables, which
    declined the report (Edwin, 2026-08-17: "I want all 3 graphs to be rendered in the report");
  * a capture nested in a printed tab group gets an /EmbeddedFiles attachment, with a UNIQUE name;
  * a phase the RECORD marks as sectioned is headed per step ("Reference" / "Sample"), and a step
    sub-heading is not shouted in the phase heading's capitals.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_report_sections_and_flags.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image

from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.SeriesPlotView import SeriesPlotView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.plugin_sdk import ReportView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

ACQUISITION = SpectralWorkflowPhaseType.ACQUISITION

RECORD = {
    "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 1195.9,
    "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.82,
    "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": {"valueKey": "qPercent", "value": 13.27, "t": 999.3,
               "readAs": "VERTEX", "branch": "was-clearing"},
    "notes": [],
    "rows": [{"t": index * 60.0, "qPercent": 13.3 - 0.1 * index, "valley": 0.9 / (index + 1),
              "soret": 0.9, "n": 50, "nAccepted": 41, "isDecisionRow": True} for index in range(12)],
}


def _capture(caption, cropped=False):
    capture = SpectrumCaptureView(caption=caption, cropped=cropped).setShownInReport(True)
    capture.reportImage = Image.new("RGB", (8, 8))
    return capture


def _workflow(steps):
    workflow = SpectralWorkflow()
    phase = SpectralWorkflowPhase()
    phase.setType(ACQUISITION)
    workflow.addToPhases(phase)
    for step in steps:
        phase.addToSteps(step)
    return workflow


def _step(role, label, items):
    step = SpectralWorkflowStep()
    step.setRole(role)
    step.setLabel(label)
    result = EvaluationResult()
    for item in items:
        result.addItem(item)
    step.setEvaluationResult(result)
    return step


def _texts(figures):
    return [text.get_text() for figure in figures for text in figure.texts]


def _render(workflow):
    builder = WorkflowReportBuilder(workflow, ReportView(title="Test report")).build()
    return builder, builder.figures()


class ReportSectionsAndFlagsTest(unittest.TestCase):

    # --- D1: the flag is honoured at every depth -------------------------------------------------------

    def test_a_settled_run_prints_the_summary_AND_all_three_curves(self):
        # ⭐⭐ Edwin, 2026-08-17, after reading the first report: "I want all 3 graphs to be rendered in the
        # report." §18.6 is why it matters — a Q% that carries its own settling curve shows the reader that
        # the value was CHOSEN, when, and on what evidence.
        # ⛔ AND THE FLAG IS STILL DOING ITS JOB, which is the whole point of D1: the two DIAGNOSTIC TABLES
        # declined the report and stay off paper. This test therefore fails in BOTH directions — a renderer
        # that ignored the flag again would drag Health and Decisions in behind the curves.
        settling = DevSpectralPlugin().settlingView(RECORD)
        _builder, figures = _render(_workflow([_step(SAMPLE, "Sample", [settling])]))

        self.assertEqual(3, sum(len(figure.axes) for figure in figures),
                         "expected exactly the three settling curves to be plotted")
        texts = _texts(figures)
        self.assertIn("Overview", texts)
        self.assertIn("Settling — how this measurement was chosen", texts)
        self.assertIn("SETTLED_AFTER_CLEARING", texts)
        # ⚠ The heading is the PLOT'S OWN TITLE, not the short tab label: a tab whose single child titles
        # itself lets the child name it, so paper carries the version with the units (§27.22).
        for curve in ("Q%", "A_valley 500–560 nm", "|Δ A_valley / Δt|  (the gate)"):
            self.assertIn(curve, texts, "the %s curve did not reach the paper" % curve)
        for table in ("Health", "Decisions"):
            self.assertNotIn(table, texts,
                             "%s is a diagnostic table and declined the report" % table)

    def test_the_curves_are_still_all_there_for_the_screen(self):
        # ⛔ §27.14/W5 — D1 must not have quietly thinned the object the bench renders.
        labels = [label for label, _ in DevSpectralPlugin().settlingView(RECORD).tabs]
        self.assertEqual(["Overview", "Q%", "Turbidity", "Rate", "Health", "Decisions"], labels)

    def test_render_still_accepts_a_plain_two_tuple_group(self):
        # ⚠ §27.16/N7 — several tests call the renderer directly with (label, items).
        plot = SeriesPlotView(title="t", xLabel="x").setShownInReport(True)
        plot.addPanel("p", "P")
        plot.addSeries("p", [0.0, 1.0], [1.0, 2.0], "s", "#e08000")
        figures = MatplotlibWorkflowRenderer().render(ReportView(title="r"), [("Processing", [plot])])
        self.assertTrue(figures)

    # --- W6/F3: nested captures are attached, and names do not collide ---------------------------------

    def test_a_capture_nested_in_a_printed_group_is_attached(self):
        group = TabGroupView().addTab("Full frame", _capture("whole")) \
                              .addTab("Cropped ROI", _capture("roi", cropped=True))
        group.setShownInReport(True)
        builder, figures = _render(_workflow([_step(SAMPLE, "Sample", [group])]))

        names = [name for name, _bytes in builder._WorkflowReportBuilder__captures]
        self.assertEqual(["capture_sample.png", "capture_sample_2.png"], names)
        self.assertIn("whole  [attachment: capture_sample.png]", _texts(figures))

    def test_an_unflagged_nested_capture_is_neither_drawn_nor_attached(self):
        # ⚠ attaching a PNG the page never shows would put a file in the payload with nothing pointing at it
        group = TabGroupView().addTab("Full frame", _capture("whole")) \
                              .addTab("Cropped ROI", SpectrumCaptureView(caption="roi", cropped=True))
        group.setShownInReport(True)
        builder, figures = _render(_workflow([_step(SAMPLE, "Sample", [group])]))

        self.assertEqual(["capture_sample.png"],
                         [name for name, _bytes in builder._WorkflowReportBuilder__captures])
        self.assertNotIn("roi", _texts(figures))

    def test_two_captures_on_one_step_get_distinct_names(self):
        # ⛔ PRE-EXISTING AND MEASURED: both were "capture_sample.png", and pypdf keeps ONE entry per name,
        # so every report written so far silently dropped its cropped frame from /EmbeddedFiles.
        builder, _figures = _render(_workflow([_step(SAMPLE, "Sample",
                                                     [_capture("full"), _capture("cropped", cropped=True)])]))
        names = [name for name, _bytes in builder._WorkflowReportBuilder__captures]
        self.assertEqual(len(names), len(set(names)), "two attachments share a name: %s" % names)

    # --- D4: the record decides the sections -----------------------------------------------------------

    def test_a_sectioned_phase_is_headed_per_step(self):
        workflow = _workflow([_step(REFERENCE, "Reference", [_capture("reference frame")]),
                              _step(SAMPLE, "Sample", [_capture("sample frame")])])
        workflow.setSectionedPhases({ACQUISITION})
        _builder, figures = _render(workflow)

        texts = _texts(figures)
        self.assertIn("ACQUISITION", texts)      # the phase still names itself, above its sections
        self.assertIn("Reference", texts)
        self.assertIn("Sample", texts)
        # ⛔ §27.16/N7: a step sub-heading must not shout in the phase heading's capitals
        self.assertNotIn("REFERENCE", texts)
        self.assertNotIn("SAMPLE", texts)

    def test_without_the_declaration_the_phase_stays_one_flat_section(self):
        # ⭐ §27.16/N5 — every run made before D4 reads exactly this way, so archived reports cannot regress.
        workflow = _workflow([_step(REFERENCE, "Reference", [_capture("reference frame")]),
                              _step(SAMPLE, "Sample", [_capture("sample frame")])])
        texts = _texts(_render(workflow)[1])
        self.assertIn("ACQUISITION", texts)
        self.assertNotIn("Reference", texts)
        self.assertNotIn("Sample", texts)

    def test_the_settling_section_lands_under_its_own_step(self):
        # ⭐ The point of D4 for §27: the curves belong to the capture they describe, on paper as on screen.
        workflow = _workflow([_step(REFERENCE, "Reference", [_capture("reference frame")]),
                              _step(SAMPLE, "Sample", [DevSpectralPlugin().settlingView(RECORD)])])
        workflow.setSectionedPhases({ACQUISITION})
        texts = _texts(_render(workflow)[1])
        self.assertLess(texts.index("Sample"), texts.index("Overview"))
        self.assertLess(texts.index("Reference"), texts.index("Sample"))


if __name__ == "__main__":
    unittest.main()


class ReportPlotLayoutTest(unittest.TestCase):
    """Nothing runs off the page, the curves line up, and a title stays with its plot.

    ⛔ Edwin, from the first report that carried curves (2026-08-17): "some graphs is cut-off at the left".
    The axes rect starts AT the content margin, but matplotlib draws the tick labels and the rotated y-label
    OUTSIDE it — measured: the gate panel's label reached figure x = -0.000, i.e. off the paper.
    """

    @staticmethod
    def __settlingFigures():
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView as _RV
        return MatplotlibWorkflowRenderer().render(
            _RV(title="p"), [("Acquisition", [DevSpectralPlugin().settlingView(RECORD)])])

    @staticmethod
    def __leftOf(figure, ax):
        box = ax.get_tightbbox(figure.canvas.get_renderer())
        return figure.transFigure.inverted().transform((box.x0, box.y0))[0]

    def test_no_axis_label_falls_off_the_left_edge(self):
        figures = self.__settlingFigures()
        for figure in figures:
            figure.canvas.draw()
            for ax in figure.axes:
                self.assertGreater(self.__leftOf(figure, ax), 0.0,
                                   "a plot's labels are printed past the paper's edge")

    def test_the_curve_panels_share_one_left_edge(self):
        # ⚠ The settling curves are SEPARATE view-models rendered in separate calls, so a per-plot fit would
        # give each its own left edge and the stack would step down the page (§27.22).
        lefts = {round(ax.get_position().bounds[0], 4)
                 for figure in self.__settlingFigures() for ax in figure.axes}
        self.assertEqual(1, len(lefts), "the curve panels do not line up: %s" % sorted(lefts))

    def test_a_plot_title_is_not_orphaned_onto_the_previous_page(self):
        # ⚠ Block-by-block flow used to leave "A_valley 500–560 nm" alone at the foot of one page with its
        # curve on the next. The title, its header lines and the first panel are now reserved as one lump.
        from sciens.spectracs.model.spectral.plugin.view.LabelView import LabelView
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView as _RV
        plot = SeriesPlotView(title="A_valley 500-560 nm", xLabel="minutes").setShownInReport(True)
        plot.addPanel("valley", "A_valley")
        plot.addSeries("valley", [0.0, 1.0], [0.9, 0.4], "valley", "#4aa3df")
        filler = [LabelView("filler %d" % index).setShownInReport(True) for index in range(20)]
        figures = MatplotlibWorkflowRenderer().render(_RV(title="p"), [("Acquisition", filler + [plot])])

        titlePage = next(index for index, figure in enumerate(figures)
                         if "A_valley 500-560 nm" in [text.get_text() for text in figure.texts])
        plotPage = next(index for index, figure in enumerate(figures) if figure.axes)
        self.assertEqual(titlePage, plotPage, "the plot's title was left on the previous page")
