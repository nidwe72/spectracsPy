"""
Track C (C.3) — the milestone's headless correctness gate (SPEC_pumpkin_integration.md C.4). For each demo
oil: synthesise R+S, encode them onto the virtual device, then drive the REAL SpectralWorkflowEngine +
PumpkinOilPlugin end to end (acquisition capture -> mean -> T/A -> colour -> verdict) and assert the
EVALUATION EvaluationResult's verdict matches the oil's known roast state — no GUI, no Qt event loop.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_pumpkin_workflow_end_to_end.py -q
"""
import unittest

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumToVirtualImageUtil import SpectrumToVirtualImageUtil
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.evaluation.VerdictView import VerdictView


class PumpkinWorkflowEndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = cls.calibration.profile
        for attribute in ("regionOfInterestX1", "regionOfInterestX2",
                          "regionOfInterestY1", "regionOfInterestY2"):
            setattr(profile, attribute, int(getattr(profile, attribute)))
        cls.profile = profile

        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = profile
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(spectrometerProfile)

        cls.reference = LedReferenceSynthesisLogicModule().synthesize(
            LedReferenceSynthesisLogicModuleParameters()).getSpectrum()

    def __runOil(self, demoOil):
        parameters = OilSampleSynthesisLogicModuleParameters()
        parameters.setReference(self.reference)
        parameters.setTargetHue(demoOil.targetHue)
        sample = OilSampleSynthesisLogicModule().synthesize(parameters).getSpectrum()

        imageReference, imageSample = SpectrumToVirtualImageUtil().encode(
            self.reference, sample, self.profile,
            self.calibration.imageWidth, self.calibration.imageHeight)
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        settings.setImage(VirtualCaptureRole.REFERENCE, imageReference)
        settings.setImage(VirtualCaptureRole.SAMPLE, imageSample)

        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        engine.runAll()
        return engine

    def __verdict(self, workflow):
        phase = workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
        step = list(phase.getSteps().values())[0]
        result = step.getEvaluationResult()
        verdictItems = [item for item in result.getItems() if isinstance(item, VerdictView)]
        return verdictItems[0].roastState

    def test_each_demo_oil_produces_the_expected_verdict(self):
        for demoOil in PLAYGROUND_DEMO_OILS:
            engine = self.__runOil(demoOil)
            self.assertEqual(self.__verdict(engine.getWorkflow()), demoOil.roastState.value, demoOil.label)

    def test_metadata_and_publishing_phases_are_skipped(self):
        engine = self.__runOil(PLAYGROUND_DEMO_OILS[0])
        self.assertTrue(engine.isSkipped(SpectralWorkflowPhaseType.METADATA))
        self.assertTrue(engine.isSkipped(SpectralWorkflowPhaseType.PUBLISHING))
        self.assertFalse(engine.isSkipped(SpectralWorkflowPhaseType.ACQUISITION))
        self.assertFalse(engine.isSkipped(SpectralWorkflowPhaseType.EVALUATION))

    def test_absorption_step_carries_a_plot_view(self):
        engine = self.__runOil(PLAYGROUND_DEMO_OILS[0])
        phase = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.PROCESSING)
        viewed = [step for step in phase.getSteps().values() if step.getView() is not None]
        self.assertEqual(len(viewed), 1)
        self.assertIsNotNone(viewed[0].getView().spectrum)


if __name__ == "__main__":
    unittest.main()
