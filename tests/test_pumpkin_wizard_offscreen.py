"""
Track C GUI wiring — drives the real WizardViewModule offscreen (QT_QPA_PLATFORM=offscreen): simulate the
A4 folder load + login binding, open the wizard, and walk the interactive flow — Measure both acquisition
steps, Next to PROCESSING (absorption plot), Next to EVALUATION (verdict). Asserts auto-calibration, the
Measure gating (Next disabled until measured), and the correct verdict. (SPEC_pumpkin_integration.md C.3/C.5)

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_pumpkin_wizard_offscreen.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.VerdictView import VerdictView
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule

PLUGIN_CODE_REF = "sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"


class PumpkinWizardOffscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        folder = os.path.join(os.path.dirname(__file__), "..", "..", "spectracs-references",
                              "pumpkin_oil", "virtual_captures", "pumpkinoil_perfect_v1")
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        for role, name in [(VirtualCaptureRole.CALIBRATION, "calibration.png"),
                           (VirtualCaptureRole.REFERENCE, "reference.png"),
                           (VirtualCaptureRole.SAMPLE, "sample.png")]:
            settings.setImage(role, QImage(os.path.join(folder, name)))
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(None)  # force auto-calibrate
        CurrentUserSession().login({"ok": True, "userId": "u", "username": "pumpkinTestUser",
                                    "roles": ["END_USER"], "pluginCodeRef": PLUGIN_CODE_REF,
                                    "pluginId": "p", "spectrometerDevice": "Virtuax"})

        cls.wizard = WizardViewModule()
        cls.wizard.initialize()
        cls.wizard.show()
        cls.app.processEvents()

    # small helpers over the wizard's private state (this test stands in for a human click-through)
    def __engine(self):
        return self.wizard._WizardViewModule__engine

    def __next(self):
        self.wizard.onClickedNext()
        self.app.processEvents()

    def test_flow_measure_then_advance_to_verdict(self):
        wizard = self.wizard
        # 1) opens on ACQUISITION with two capture tabs; Next is gated until measured
        self.assertEqual(wizard._WizardViewModule__shownPhases[0], SpectralWorkflowPhaseType.ACQUISITION)
        self.assertEqual(wizard._WizardViewModule__tabWidget.count(), 2)
        self.assertFalse(wizard._WizardViewModule__nextButton.isEnabled())

        # 2) Measure both steps (what the per-tab Measure buttons do)
        acquisition = self.__engine().getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in acquisition.getSteps().values():
            self.__engine().captureAcquisitionStep(step)
        wizard._WizardViewModule__refreshNav()
        self.assertTrue(wizard._WizardViewModule__nextButton.isEnabled())

        # 3) Next -> PROCESSING (an absorption plot tab), Next -> EVALUATION, Next -> METADATA (terminal)
        self.__next()
        self.assertEqual(wizard._WizardViewModule__shownPhases[wizard._WizardViewModule__cursor],
                         SpectralWorkflowPhaseType.PROCESSING)
        self.assertGreaterEqual(wizard._WizardViewModule__tabWidget.count(), 1)
        self.__next()
        self.assertEqual(wizard._WizardViewModule__shownPhases[wizard._WizardViewModule__cursor],
                         SpectralWorkflowPhaseType.EVALUATION)
        # Non-terminal proceed: text is "Next" + a permanent amber ▶ ICON (SPEC_acquisition_guidance); METADATA follows.
        self.assertEqual(wizard._WizardViewModule__nextButton.text(), "Next")
        self.assertFalse(wizard._WizardViewModule__nextButton.icon().isNull())
        self.__next()
        self.assertEqual(wizard._WizardViewModule__shownPhases[wizard._WizardViewModule__cursor],
                         SpectralWorkflowPhaseType.METADATA)
        self.assertEqual(wizard._WizardViewModule__nextButton.text(), "Save")

        # 4) the verdict rendered
        step = list(self.__engine().getWorkflow().getPhase(
            SpectralWorkflowPhaseType.EVALUATION).getSteps().values())[0]
        verdicts = [i for i in step.getEvaluationResult().getItems() if isinstance(i, VerdictView)]
        self.assertEqual(verdicts[0].roastState, "PERFECT-ROASTED")


if __name__ == "__main__":
    unittest.main()
