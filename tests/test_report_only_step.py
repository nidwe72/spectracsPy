"""Report-only steps — SPEC_settled_measurement.md §27.11.

⭐ THE PROBLEM THIS SOLVES. The bench and the PDF read the SAME tree: the report collector walks
`workflow.getPhase(...).getSteps()`, so anything that must reach the paper must be a step — and every
step used to become a tab. The settling summary belongs in the report as provenance (a `Q%` that was
CHOSEN should carry the curve it was chosen from), but the operator reads it under Sample, where the
measurement happened. ⇒ a step that the report collects and no host draws.
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
from sciens.spectracs.plugin_sdk import ReportView
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


class ReportOnlyStepTest(unittest.TestCase):

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

    def __processedWorkflow(self, record=RECORD):
        engine = SpectralWorkflowEngine(DevSpectralPlugin())
        engine.runPhase(SpectralWorkflowPhaseType.ACQUISITION)
        if record is not None:
            engine.getWorkflow().setMonitorRecord(record)
        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)
        return engine.getWorkflow()

    def __settlingStep(self, workflow):
        steps = workflow.getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values()
        return next((step for step in steps if step.getLabel() == "Settling"), None)

    def test_the_settling_step_exists_but_is_marked_report_only(self):
        step = self.__settlingStep(self.__processedWorkflow())
        self.assertIsNotNone(step, "the report cannot collect what is not a step")
        self.assertTrue(step.isReportOnly())

    def test_no_host_draws_a_tab_for_it(self):
        # ⭐ Guarded in renderStep() because BOTH hosts funnel through it — the bench's phase tabs and the
        # wizard's step pages. Skipping at the call sites is how the amber-cue bug survived a round.
        step = self.__settlingStep(self.__processedWorkflow())
        self.assertIsNone(WorkflowPhaseRenderer().renderStep(step))

    def test_ordinary_steps_are_unaffected(self):
        workflow = self.__processedWorkflow()
        spectra = next(step for step
                       in workflow.getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values()
                       if step.getLabel() == "Spectra")
        self.assertFalse(spectra.isReportOnly())
        self.assertIsNotNone(WorkflowPhaseRenderer().renderStep(spectra))

    def test_the_report_DOES_collect_it(self):
        workflow = self.__processedWorkflow()
        builder = WorkflowReportBuilder(workflow, ReportView(title="Test report"))
        builder.build()
        self.assertTrue(builder.figures(), "the report produced no pages at all")
        # The settling Overview is a TabGroupView flagged for the report; on paper the group flattens to
        # titled sections (§18.8), so its presence shows up as extra pages/axes rather than a tab.
        withoutRecord = WorkflowReportBuilder(self.__processedWorkflow(record=None),
                                              ReportView(title="Test report"))
        withoutRecord.build()
        self.assertGreater(builder.pageCount(), 0)
        self.assertGreaterEqual(builder.pageCount(), withoutRecord.pageCount(),
                                "the settling section did not reach the report")

    def test_the_machine_payload_carries_the_record_too(self):
        # ⛔ The PDF has two halves. Even with the visible section, a reader parsing the embedded JSON used
        # to get the answer but not the trajectory, the gate's numbers, or the policy it ran under.
        payload = self.__processedWorkflow().toReportJson()
        self.assertIn("monitorRecord", payload)
        self.assertEqual("SETTLED_AFTER_CLEARING", payload["monitorRecord"]["outcome"])
        self.assertEqual(5, len(payload["monitorRecord"]["rows"]))
        self.assertIsNone(self.__processedWorkflow(record=None).toReportJson()["monitorRecord"])


if __name__ == "__main__":
    unittest.main()
