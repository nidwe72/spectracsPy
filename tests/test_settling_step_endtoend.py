"""The Settling step, end to end: capture -> record on the workflow -> the step appears in PROCESSING.

⚠ WRITTEN AFTER A RIG FINDING (2026-08-17): the settling tab did not appear on the bench even though the
monitored run completed. A unit test on `settlingStep()` alone could not have caught it — that method
was fine. The break has to be looked for on the WHOLE path, which is what this test walks.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin


class SettlingStepEndToEndTest(unittest.TestCase):

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

    def __capturedEngine(self):
        engine = SpectralWorkflowEngine(DevSpectralPlugin())
        engine.runPhase(SpectralWorkflowPhaseType.ACQUISITION)     # virtual provider fills both roles
        return engine

    def test_the_settling_step_is_declared_REPORT_ONLY_in_PROCESSING(self):
        """⭐ §27.11 — the resolution of a genuine conflict: the bench and the PDF read the SAME tree.

        The operator reads the settling curve under Sample, where the measurement happened, so PROCESSING
        must not grow a tab for it (Edwin, at the rig). But the report collector only ever sees WORKFLOW
        STEPS, and a `Q%` that was CHOSEN should carry the curve it was chosen from onto the paper.
        ⇒ the step is there, flagged report-only, and `WorkflowPhaseRenderer.renderStep()` draws nothing
        for it. See tests/test_report_only_step.py for both halves."""
        engine = self.__capturedEngine()
        engine.getWorkflow().setMonitorRecord(self.__record())
        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)
        steps = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values()
        settling = next((step for step in steps if step.getLabel() == "Settling"), None)
        self.assertIsNotNone(settling)
        self.assertTrue(settling.isReportOnly(), "it would grow a PROCESSING tab again")

    def __record(self):
        return {
            "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 1195.9,
            "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.82,
            "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
            "answer": {"valueKey": "qPercent", "value": 13.27, "t": 999.3,
                       "readAs": "VERTEX", "branch": "was-clearing"},
            "notes": [],
            "rows": [{"t": index * 60.0, "qPercent": 13.3, "valley": 0.06, "soret": 0.9,
                      "n": 50, "nAccepted": 50, "isDecisionRow": True} for index in range(5)],
        }

    def test_the_plugin_still_builds_the_step_from_a_record(self):
        # ⭐ The host places it (as a Sample inner tab); the PLUGIN still owns what it contains.
        step = DevSpectralPlugin().settlingStep(self.__record())
        self.assertIsNotNone(step)
        self.assertEqual("Settling", step.getLabel())
        self.assertEqual("Overview", step.getView().tabs[0][0])

    def test_a_run_that_produced_NO_VALUE_still_shows_its_curve(self):
        """⛔⛔ THE RIG BUG OF 2026-08-17, as a test.

        A monitored run that never settles leaves the SAMPLE step deliberately uncaptured (§12.1: "a
        cancelled capture is not a capture"). The settling step used to be built at the END of
        `processing()`, so the ops in between raised on the missing container and the whole phase died —
        killing the one tab that could explain WHY, in precisely the runs that need explaining.
        ⇒ ⭐ the diagnostic must survive the failure of the measurement it documents."""
        engine = self.__capturedEngine()
        workflow = engine.getWorkflow()
        acquisition = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in acquisition.getSteps().values():
            if step.getRole() == "sample":
                step.setContainer(None)          # what a NEVER_SETTLED run leaves behind
        workflow.setMonitorRecord({
            "outcome": "NEVER_SETTLED", "capsHit": True, "clearingSeconds": None,
            "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0",
            "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
            "answer": None, "notes": [],
            "rows": [{"t": index * 60.0, "qPercent": None, "valley": 0.9 - index * 0.02,
                      "soret": 0.9, "n": 50, "nAccepted": 50, "isDecisionRow": True}
                     for index in range(20)],
        })

        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)   # ⛔ must not raise on the missing container
        # ⭐ and the curve that explains the failure is still buildable from the record
        step = DevSpectralPlugin().settlingStep(engine.getWorkflow().getMonitorRecord())
        self.assertIsNotNone(step, "a run with no value lost the very curve that explains why")

    def test_without_a_record_there_is_no_Settling_step(self):
        engine = self.__capturedEngine()
        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)
        labels = [step.getLabel() for step
                  in engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values()]
        self.assertNotIn("Settling", labels)


if __name__ == "__main__":
    unittest.main()
