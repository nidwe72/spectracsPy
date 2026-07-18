"""SPEC_capture_quality.md §14.8 — per-frame brightness rejection (C1) + the top-up burst (C3).

C1: the temporal reduction drops whole frames that are a GLOBAL brightness outlier (the coherent dim group an
auto-exposure ramp leaves in the reference burst) BEFORE the per-bin sigma-clip — which can't reject a
large-minority dim group, so without this the reference mean is biased low and T = S/R is corrupted.
C3: the burst grabs until N frames SURVIVE that rejection, so the effective count feeding the mean stays N.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_capture_frame_rejection.py -q
"""
import unittest

import numpy as np

from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum


def _stackOfBrightness(brightnesses, bins=20):
    # One frame per brightness; every bin in a frame = that brightness, so the per-frame median (the reject
    # scalar) is exactly the brightness — lets us drive the reject deterministically.
    return np.array([np.full(bins, b, dtype=float) for b in brightnesses])


class RejectDimFramesTest(unittest.TestCase):
    """C1 — the per-frame brightness reject (pure numpy)."""

    def test_rejects_coherent_dim_group(self):
        # 7 clean (~100, with noise so MAD>0) + 3 dim (~80): the dim group is a MAD-outlier on the per-frame
        # scalar and is dropped, where a per-bin sigma-clip would keep it.
        stack = _stackOfBrightness([98, 99, 100, 101, 102, 100, 99, 80, 82, 84])
        keep = RobustReductionLogicModule().rejectDimFrames(stack)
        self.assertEqual(int(keep.sum()), 7)
        self.assertTrue(keep[:7].all())          # clean kept
        self.assertFalse(keep[7:].any())         # dim rejected

    def test_keeps_clean_stack(self):
        stack = _stackOfBrightness([98, 99, 100, 101, 102, 100, 99, 101, 100, 99])
        self.assertTrue(RobustReductionLogicModule().rejectDimFrames(stack).all())

    def test_keeps_when_too_few_frames(self):
        # Below MIN_FRAMES_TO_REJECT there is no trustworthy robust center — keep all (a dim one included).
        stack = _stackOfBrightness([100, 100, 100, 70])
        self.assertTrue(RobustReductionLogicModule().rejectDimFrames(stack).all())

    def test_keeps_degenerate_constant(self):
        # All identical (the virtual/headless path) -> MAD==0 -> keep all, never over-reject.
        self.assertTrue(RobustReductionLogicModule().rejectDimFrames(np.full((10, 20), 100.0)).all())

    def test_never_rejects_everything(self):
        # A pathological spread must still leave the sigma-clip something to average.
        stack = _stackOfBrightness([10, 200, 10, 200, 10, 200, 10, 200])
        self.assertTrue(RobustReductionLogicModule().rejectDimFrames(stack).any())


class MeanSpectrumRejectionTest(unittest.TestCase):
    """C1 — the reject un-biases the temporal mean (the whole point: R must not sit low)."""

    def test_dim_group_does_not_bias_mean(self):
        spectrum = Spectrum()
        for value in (99, 100, 101, 100, 99, 101, 100):        # 7 clean ~100
            spectrum.addToCapturedValuesByNanometers({450: float(value), 500: float(value), 550: float(value)})
        for value in (78, 80, 82):                              # 3 dim ~80 (the exposure-ramp group)
            spectrum.addToCapturedValuesByNanometers({450: float(value), 500: float(value), 550: float(value)})

        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        mean = MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum().valuesByNanometers

        # Plain mean would be ~94 (dragged down by the dim group); the reject keeps it on the clean cluster ~100.
        self.assertGreater(mean[450], 98.0)
        self.assertGreater(mean[500], 98.0)
        self.assertGreater(mean[550], 98.0)


class FrameBrightnessTest(unittest.TestCase):
    """§14.8 fix 2 — the full-frame settle metric (mean of the brightest channel)."""

    def test_mean_of_max_channel(self):
        from PySide6.QtGui import QImage, qRgb
        from sciens.spectracs.logic.application.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
        image = QImage(4, 4, QImage.Format.Format_RGB888)
        image.fill(qRgb(10, 200, 30))                       # max(R,G,B) = 200 at every pixel
        self.assertAlmostEqual(AutoExposureLogicModule.frameBrightness(image), 200.0, delta=1.0)
        self.assertEqual(AutoExposureLogicModule.frameBrightness(None), 0.0)

    def test_mean_sits_below_the_peak(self):
        # A frame that is mostly dark with a bright stripe: the MEAN is far below the PEAK — which is the whole
        # point (the mean keeps moving through the ramp where channelPeak has already plateaued).
        from PySide6.QtGui import QImage, qRgb
        from sciens.spectracs.logic.application.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
        image = QImage(10, 10, QImage.Format.Format_RGB888)
        image.fill(qRgb(0, 0, 0))
        for x in range(10):
            image.setPixelColor(x, 5, image.pixelColor(x, 5))  # no-op keep; set a bright row below
        for x in range(10):
            image.setPixel(x, 5, qRgb(0, 250, 0))
        peak = AutoExposureLogicModule.channelPeak(image)
        mean = AutoExposureLogicModule.frameBrightness(image)
        self.assertGreater(peak, 200)                        # the bright row pegs the peak
        self.assertLess(mean, peak)                          # the mean is pulled down by the dark majority


class CaptureTopUpTest(unittest.TestCase):
    """C3 — the burst grabs extra frames to REPLACE rejected dim ones, so N survive into the mean."""

    @classmethod
    def setUpClass(cls):
        from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
        from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
        from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
        from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
        from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
        from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
        from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
        from sciens.spectracs.logic.spectral.synthesis.SpectrumToVirtualImageUtil import SpectrumToVirtualImageUtil
        from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
        from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole

        calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = calibration.profile
        for attribute in ("regionOfInterestX1", "regionOfInterestX2", "regionOfInterestY1", "regionOfInterestY2"):
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

        dimReference = Spectrum()
        dimReference.valuesByNanometers = {nm: value * 0.45 for nm, value in reference.valuesByNanometers.items()}

        imageReference, _ = SpectrumToVirtualImageUtil().encode(
            reference, sample, profile, calibration.imageWidth, calibration.imageHeight)
        imageDim, _ = SpectrumToVirtualImageUtil().encode(
            dimReference, sample, profile, calibration.imageWidth, calibration.imageHeight)
        cls.referenceImage = imageReference
        cls.dimImage = imageDim

    def __referenceStep(self, engine):
        from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
        phase = engine.runPhaseHook(SpectralWorkflowPhaseType.ACQUISITION)
        return [step for step in phase.getSteps().values() if step.getRole() is not None][0]

    def test_topup_replaces_rejected_dim_frames(self):
        from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
        from sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin

        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        step = self.__referenceStep(engine)
        target = 8
        dimCount = 3
        state = {"n": 0}

        def provider():
            state["n"] += 1
            return self.dimImage if state["n"] <= dimCount else self.referenceImage

        engine.captureAcquisitionStep(step, frameProvider=provider, frames=target)
        captured = step.getContainer().getSpectra()[step.getRole()].getCapturedValuesByNanometers()

        # Topped up past `target` to replace the 3 dim frames...
        self.assertGreater(len(captured), target)
        # ...and at least `target` frames survive the very reject the final mean applies.
        keys = list(captured[0].keys())
        stack = np.array([[frame.get(key, np.nan) for key in keys] for frame in captured], dtype=float)
        survivors = int(RobustReductionLogicModule().rejectDimFrames(stack).sum())
        self.assertGreaterEqual(survivors, target)


if __name__ == "__main__":
    unittest.main()
