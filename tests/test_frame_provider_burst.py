"""S1d — offscreen coverage of the injected frame-provider burst path
(SPEC_plugin_driven_convergence.md §9.1 / §9.4).

`SpectralWorkflowEngine.captureAcquisitionStep(step, frameProvider)` runs the numeric burst by pulling
`frames` frames from a host-injected provider. On the rig that provider pumps the live camera thread; here a
SYNTHETIC provider emits a canned frame, so the burst path — the ONE seam the whole convergence milestone
rides on — is exercised with NO hardware and NO Qt event loop, BEFORE the rig (§9.5).

Asserts the seam is transparent: fed the same frame the virtual default would read, the injected provider
yields an identical spectrum, and the burst pulls exactly `frames` frames from it.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_frame_provider_burst.py -q
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


class SyntheticFrameProvider:
    """A fake live-frame source (S1d): returns a canned frame each call and counts invocations. Stands in
    for the rig's real provider (which pumps DevCaptureVideoThread) so CI can exercise the burst path."""

    def __init__(self, frame):
        self.__frame = frame
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.__frame


class FrameProviderBurstTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = calibration.profile
        for attribute in ("regionOfInterestX1", "regionOfInterestX2",
                          "regionOfInterestY1", "regionOfInterestY2"):
            setattr(profile, attribute, int(getattr(profile, attribute)))
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = profile
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(spectrometerProfile)

        reference = LedReferenceSynthesisLogicModule().synthesize(
            LedReferenceSynthesisLogicModuleParameters()).getSpectrum()
        sampleParameters = OilSampleSynthesisLogicModuleParameters()
        sampleParameters.setReference(reference)
        sampleParameters.setTargetHue(PLAYGROUND_DEMO_OILS[0].targetHue)
        sample = OilSampleSynthesisLogicModule().synthesize(sampleParameters).getSpectrum()

        imageReference, imageSample = SpectrumToVirtualImageUtil().encode(
            reference, sample, profile, calibration.imageWidth, calibration.imageHeight)
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        settings.setImage(VirtualCaptureRole.REFERENCE, imageReference)
        settings.setImage(VirtualCaptureRole.SAMPLE, imageSample)
        cls.referenceImage = imageReference

    def __referenceStep(self, engine):
        phase = engine.runPhaseHook(SpectralWorkflowPhaseType.ACQUISITION)
        steps = [step for step in phase.getSteps().values() if step.getRole() is not None]
        return steps[0]

    def test_injected_provider_is_pulled_once_per_frame(self):
        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        step = self.__referenceStep(engine)
        provider = SyntheticFrameProvider(self.referenceImage)
        engine.captureAcquisitionStep(step, frameProvider=provider)
        self.assertEqual(provider.calls, step.getFrames() or 1)
        self.assertIsNotNone(step.getContainer())
        spectrum = step.getContainer().getSpectra()[step.getRole()]
        self.assertGreater(len(spectrum.valuesByNanometers), 0)

    def test_provider_seam_is_transparent(self):
        # The same frame the virtual default reads, fed through the injected provider, yields an identical
        # spectrum — proving the seam adds no behavioural change (the S1b acceptance, exercised via a provider).
        defaultEngine = SpectralWorkflowEngine(PumpkinOilPlugin())
        defaultStep = self.__referenceStep(defaultEngine)
        defaultEngine.captureAcquisitionStep(defaultStep)  # virtual default provider
        expected = dict(defaultStep.getContainer().getSpectra()[defaultStep.getRole()].valuesByNanometers)

        injectedEngine = SpectralWorkflowEngine(PumpkinOilPlugin())
        injectedStep = self.__referenceStep(injectedEngine)
        injectedEngine.captureAcquisitionStep(
            injectedStep, frameProvider=SyntheticFrameProvider(self.referenceImage))
        actual = dict(injectedStep.getContainer().getSpectra()[injectedStep.getRole()].valuesByNanometers)

        self.assertEqual(actual, expected)

    def test_capture_context_frames_override_and_onframe(self):
        # S2b: the host's Frames count overrides the step's, and onFrame fires once per extracted frame
        # (what the bench uses to live-plot the running mean + step the progress bar).
        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        step = self.__referenceStep(engine)
        provider = SyntheticFrameProvider(self.referenceImage)
        seen = []
        engine.captureAcquisitionStep(
            step, frameProvider=provider, frames=3,
            onFrame=lambda spectrum, index, total: seen.append((index, total)))
        self.assertEqual(provider.calls, 3)
        self.assertEqual(seen, [(0, 3), (1, 3), (2, 3)])
        self.assertIsNotNone(step.getContainer())

    def test_dropped_frames_are_skipped(self):
        # A provider that returns None (a dropped camera frame) is skipped, not fatal — one good frame still
        # yields a spectrum (mirrors the bench's per-frame `if latestImage is None: continue`).
        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        step = self.__referenceStep(engine)
        frames = [None, self.referenceImage, None]
        spectrum = engine.captureAcquisitionStep(
            step, frameProvider=lambda: frames.pop(0) if frames else None, frames=3)
        self.assertIsNotNone(spectrum)
        self.assertGreater(len(step.getContainer().getSpectra()[step.getRole()].valuesByNanometers), 0)


if __name__ == "__main__":
    unittest.main()
