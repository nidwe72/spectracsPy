"""PROCESSING must survive a run that produced NO VALUE.

⛔⛔ THE RIG BUG OF 2026-08-17, kept as a test. A monitored run that never settles leaves the SAMPLE step
deliberately uncaptured (§12.1: "a cancelled capture is not a capture") — and `processing()` used to walk
straight into `TransmissionOp` on the missing container, killing the whole phase and with it the one tab
that could explain WHY.

⇒ ⭐ THE RULE: a diagnostic must survive the failure of the measurement it documents. The settling views
themselves live on the SAMPLE step now (tests/test_settling_views_on_the_sample_step.py), so they are
untouched by whatever PROCESSING does; this test guards the phase that used to take them down with it.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.plugin_sdk.roles import SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin


class ProcessingSurvivesAValuelessRunTest(unittest.TestCase):

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

    def test_an_uncaptured_sample_does_not_take_the_phase_down(self):
        engine = SpectralWorkflowEngine(DevSpectralPlugin())
        engine.runPhase(SpectralWorkflowPhaseType.ACQUISITION)
        acquisition = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in acquisition.getSteps().values():
            if step.getRole() == SAMPLE:        # ⚠ the CONSTANT — a "sample" literal matched nothing, and
                step.setContainer(None)         # this assertion was silently vacuous until 2026-08-17

        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)   # ⛔ must not raise

    def test_a_complete_run_still_builds_the_ordinary_processing_steps(self):
        engine = SpectralWorkflowEngine(DevSpectralPlugin())
        engine.runPhase(SpectralWorkflowPhaseType.ACQUISITION)
        engine.runPhase(SpectralWorkflowPhaseType.PROCESSING)
        labels = [step.getLabel() for step
                  in engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values()]
        self.assertIn("Spectra", labels)
        # ⛔ and nothing about settling is declared here any more — it belongs to the SAMPLE step (§27.12)
        self.assertNotIn("Settling", labels)


if __name__ == "__main__":
    unittest.main()
