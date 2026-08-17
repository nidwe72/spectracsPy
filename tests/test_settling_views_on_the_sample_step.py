"""The settling views live on the SAMPLE step — SPEC_settled_measurement.md §27.12.

⭐ THE PROPER FIX, after two wrong turns. The settling curves are provenance of ONE capture, so they hang
off that capture's step: the report already harvests an acquisition step's EvaluationResult (it pulls the
raster and spectrum views off exactly the same place), and `renderStep()` sends a CaptureView step to the
capture path, which never looks at it. ⇒ collected on paper, invisible as a tab, no flag needed.

⛔ WHAT THIS REPLACED. First the views reached nothing (the panel built a WIDGET, and the report collects
view-models). Then a report-only STEP in PROCESSING — which meant the same record was built TWICE into
two homes, with a persisted column invented to hide one of them. The duplication was the tell.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.plugin_sdk import ReportView
from sciens.spectracs.plugin_sdk.roles import SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer

RECORD = {
    "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 1195.9,
    "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.82,
    "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": {"valueKey": "qPercent", "value": 13.27, "t": 999.3,
               "readAs": "VERTEX", "branch": "was-clearing"},
    "notes": [],
    "rows": [{"t": index * 60.0, "qPercent": 13.3, "valley": 0.06, "soret": 0.9,
              "n": 50, "nAccepted": 50, "isDecisionRow": True} for index in range(5)],
}


class FakeMonitorResult:
    """Only what `__attachMonitorViews` reads — no camera, no ring, no frames."""

    def __init__(self, record=RECORD):
        self.__record = record
        self.spectrum = None
        self.views = []

    def toRecord(self):
        return self.__record


class SettlingViewsOnTheSampleStepTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        folder = os.path.join(os.path.dirname(__file__), "..", "..", "spectracs-references",
                              "pumpkin_oil", "virtual_captures", "pumpkinoil_perfect_v2")
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        for role, name in [(VirtualCaptureRole.CALIBRATION, "calibration.png"),
                           (VirtualCaptureRole.REFERENCE, "reference.png"),
                           (VirtualCaptureRole.SAMPLE, "sample.png")]:
            settings.setImage(role, QImage(os.path.join(folder, name)))
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(None)

    def __engineWithSettling(self, record=RECORD):
        engine = SpectralWorkflowEngine(DevSpectralPlugin())
        engine.runPhase(SpectralWorkflowPhaseType.ACQUISITION)
        step = self.__sampleStep(engine)
        result = FakeMonitorResult(record)
        engine._SpectralWorkflowEngine__attachMonitorViews(step, result)
        return engine, step, result

    @staticmethod
    def __sampleStep(engine):
        steps = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION).getSteps().values()
        # ⚠ the CONSTANT, not a string literal: the role is "SAMPLE", and a lowercase literal here
        # silently matched nothing — which is how a test quietly stops testing anything.
        return next(step for step in steps if step.getRole() == SAMPLE)

    @staticmethod
    def __settlingViews(step):
        return [item for item in step.getEvaluationResult().getItems()
                if isinstance(item, TabGroupView)]

    def test_the_views_hang_off_the_sample_step(self):
        _engine, step, result = self.__engineWithSettling()
        views = self.__settlingViews(step)
        self.assertEqual(1, len(views))
        self.assertEqual("Overview", views[0].tabs[0][0])
        # ⭐ ONE construction: the panel renders the very objects the report will collect.
        self.assertIs(views[0], result.views[0])
        self.assertTrue(views[0].isShownInReport)

    def test_the_sample_step_still_renders_as_the_capture_panel_not_as_tabs(self):
        # ⚠ Invisible BY CONSTRUCTION: renderStep sends a CaptureView step to the capture path, which
        # never looks at the EvaluationResult. No flag, no guard, nothing to forget.
        _engine, step, _result = self.__engineWithSettling()
        rendered = WorkflowPhaseRenderer(captureHandler=lambda s, v: "CAPTURE-PANEL").renderStep(step)
        self.assertEqual("CAPTURE-PANEL", rendered)

    def test_the_report_collects_them_under_ACQUISITION(self):
        engine, _step, _result = self.__engineWithSettling()
        builder = WorkflowReportBuilder(engine.getWorkflow(), ReportView(title="Test report"))
        groups = builder._WorkflowReportBuilder__collectGroups()
        # ⚠ a group is (label, items, headingLevel) since D4 (§27.14a) — the level is not this test's subject
        acquisition = [item for label, items, *_ in groups if label == "Acquisition" for item in items]
        self.assertTrue(any(isinstance(item, TabGroupView) for item in acquisition),
                        "the settling views did not reach the report's Acquisition section")

    def test_re_measuring_REPLACES_rather_than_accumulates(self):
        # ⛔ Two curves on one capture would be two contradictory provenances for one number.
        engine, step, _result = self.__engineWithSettling()
        engine._SpectralWorkflowEngine__attachMonitorViews(step, FakeMonitorResult())
        self.assertEqual(1, len(self.__settlingViews(step)))

    def test_a_plain_burst_attaches_nothing(self):
        engine, step, result = self.__engineWithSettling(record={"rows": []})
        self.assertEqual([], self.__settlingViews(step))
        self.assertEqual([], result.views)

    def test_the_machine_payload_carries_the_record(self):
        # The PDF's other half: a reader parsing the embedded JSON gets the trajectory, not just the answer.
        engine, _step, _result = self.__engineWithSettling()
        engine.getWorkflow().setMonitorRecord(RECORD)
        payload = engine.getWorkflow().toReportJson()
        self.assertEqual("SETTLED_AFTER_CLEARING", payload["monitorRecord"]["outcome"])
        self.assertEqual(5, len(payload["monitorRecord"]["rows"]))


if __name__ == "__main__":
    unittest.main()
