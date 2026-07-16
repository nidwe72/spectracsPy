"""
Regression: a virtual-spectrometer capture set must not be read through a STALE calibration profile.

Before this fix, SpectralWorkflowEngine.__ensureCalibration trusted any installed polynomial and skipped
re-detection, so an ROI tuned for a different capture (e.g. the older 1854x336 CFL crop) was applied to the
new 2592x1944 set — the reader sampled a black row, the spectrum came out empty, and ROI/peak detection
"stopped working". The engine now re-detects the ROI when the stored one doesn't land on signal in the
CURRENT calibration image.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_stale_calibration_recovery.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import SpectrometerCalibrationProfile
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.VerdictView import VerdictView


class StaleCalibrationRecoveryTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.folder = os.path.join(os.path.dirname(__file__), "..", "..", "spectracs-references",
                                  "pumpkin_oil", "virtual_captures", "pumpkinoil_perfect_v1")

    def __loadFolderIntoDevice(self):
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        for role, name in [(VirtualCaptureRole.CALIBRATION, "calibration.png"),
                           (VirtualCaptureRole.REFERENCE, "reference.png"),
                           (VirtualCaptureRole.SAMPLE, "sample.png")]:
            settings.setImage(role, QImage(os.path.join(self.folder, name)))

    def __installStaleProfile(self):
        # ROI tuned for the old 1854x336 CFL crop: centre row = 170, which is black in the 1944-tall v1 image.
        profile = SpectrometerCalibrationProfile()
        profile.regionOfInterestX1 = 10
        profile.regionOfInterestX2 = 1840
        profile.regionOfInterestY1 = 300
        profile.regionOfInterestY2 = 40
        profile.interpolationCoefficientA = 0.0
        profile.interpolationCoefficientB = 0.0
        profile.interpolationCoefficientC = 0.146
        profile.interpolationCoefficientD = 306.0
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = profile
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(spectrometerProfile)

    def __sampleSpectrum(self, engine):
        phase = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        step = list(phase.getSteps().values())[0]
        spectrum = list(step.getContainer().getSpectra().values())[0]
        return list(spectrum.valuesByNanometers.values())

    def __verdict(self, engine):
        phase = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.EVALUATION)
        step = list(phase.getSteps().values())[0]
        items = step.getEvaluationResult().getItems()
        return [item for item in items if isinstance(item, VerdictView)][0].roastState

    def test_stale_profile_is_rejected_and_run_recovers(self):
        self.__loadFolderIntoDevice()
        self.__installStaleProfile()

        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        engine.runAll()

        values = self.__sampleSpectrum(engine)
        self.assertGreater(max(values), 5, "spectrum is empty — stale ROI was used instead of re-detecting")
        self.assertEqual(self.__verdict(engine), "PERFECT-ROASTED")

    def test_real_device_keeps_its_profile_when_no_calibration_image(self):
        # A real device (no virtual CALIBRATION image) must NOT have its stored polynomial discarded.
        ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().setImage(
            VirtualCaptureRole.CALIBRATION, None)
        self.__installStaleProfile()
        before = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        SpectralWorkflowEngine(PumpkinOilPlugin())._SpectralWorkflowEngine__ensureCalibration()
        after = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        self.assertIs(after, before, "stored profile was dropped even though there is no calibration image")


if __name__ == "__main__":
    unittest.main()
