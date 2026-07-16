"""
Offscreen checks for the chevron StepBarWidget and its wiring into the measurement wizard:
  1) the generic widget accepts labels + a current index, paints without error, and reports them back;
  2) inside the wizard, the step bar shows ALL phases at once and the current index tracks navigation.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_step_bar_widget_offscreen.py -q
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
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule

PLUGIN_CODE_REF = "sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"
USER_ID = "test-step-bar"


class _StubMainContainer:
    class _MainView:
        def setCurrentIndex(self, index):
            pass
    def __init__(self):
        self.mainViewModule = _StubMainContainer._MainView()
    def setWindowTitle(self, title):
        pass


class StepBarWidgetOffscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_reports_steps_and_paints(self):
        bar = StepBarWidget()
        bar.setSteps(["Acquisition", "Processing", "Evaluation"])
        bar.setCurrentIndex(1)
        self.assertEqual(bar.getSteps(), ["Acquisition", "Processing", "Evaluation"])
        self.assertEqual(bar.getCurrentIndex(), 1)
        bar.resize(600, 34)
        bar.show()
        self.app.processEvents()  # exercises paintEvent (all steps visible, index 1 highlighted)


class WizardStepBarOffscreenTest(unittest.TestCase):

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
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(None)
        CurrentUserSession().login({"ok": True, "userId": USER_ID, "username": "stepBarUser",
                                    "roles": ["END_USER"], "pluginCodeRef": PLUGIN_CODE_REF,
                                    "pluginId": "p", "spectrometerDevice": "Virtuax"})
        ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = _StubMainContainer()

    def __private(self, wizard, name):
        return getattr(wizard, "_WizardViewModule__" + name)

    def test_step_bar_shows_all_phases_and_tracks_navigation(self):
        wizard = WizardViewModule()
        wizard.initialize()
        wizard.resetToNewMode()
        wizard.show()
        self.app.processEvents()

        stepBar = self.__private(wizard, "stepBar")
        # the pumpkin plugin contributes metadata, so the full sequence is all four phases, shown at once
        self.assertEqual(
            stepBar.getSteps(),
            ["Acquisition", "Processing", "Evaluation", "Metadata"])
        self.assertEqual(stepBar.getCurrentIndex(), 0)  # starts on Acquisition

        engine = self.__private(wizard, "engine")
        for step in engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION).getSteps().values():
            engine.captureAcquisitionStep(step)

        # walk to the terminal phase; the step bar index must follow the cursor each time
        for _ in range(10):
            if self.__private(wizard, "nextButton").text() == "Save":
                break
            wizard.onClickedNext()
            self.app.processEvents()
            self.assertEqual(stepBar.getCurrentIndex(), self.__private(wizard, "cursor"))

        self.assertEqual(stepBar.getCurrentIndex(), len(stepBar.getSteps()) - 1)  # ends on Metadata


if __name__ == "__main__":
    unittest.main()
