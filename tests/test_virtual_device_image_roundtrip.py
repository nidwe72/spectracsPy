"""
Track A round-trip (SPEC_pumpkin_integration.md A.3): synthesise REFERENCE + SAMPLE spectra, encode them
to full-resolution grayscale ROI strips (shared vmax, linear resample), decode each back through the REAL
acquisition reader (ImageSpectrumAcquisitionLogicModule), and assert the recovered colour / verdict match
the spectra-only path within +-3 deg. Proves the virtual-device image round-trip end to end, headless.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_virtual_device_image_roundtrip.py -q
"""
import unittest

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumToVirtualImageUtil import SpectrumToVirtualImageUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModule import VerdictLogicModule
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleParameters import VerdictLogicModuleParameters
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

HUE_TOLERANCE_DEGREES = 3.0


def _hue(color):
    return color.hueF() * 360.0


def _verdict(hue):
    parameters = VerdictLogicModuleParameters()
    parameters.setHue(hue)
    return VerdictLogicModule().verdict(parameters).getRoastState()


def _decode(image):
    # Read the encoded strip back exactly as a real acquisition would (SpectralVideoThreadSignal branch).
    signal = SpectralVideoThreadSignal()
    signal.image = image
    parameters = ImageSpectrumAcquisitionLogicModuleParameters()
    parameters.setVideoSignal(signal)
    return ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum


class VirtualDeviceImageRoundtripTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = cls.calibration.profile
        # ROI edges come back as floats; the reader iterates range(x1, x2), so coerce to int.
        profile.regionOfInterestX1 = int(profile.regionOfInterestX1)
        profile.regionOfInterestX2 = int(profile.regionOfInterestX2)
        profile.regionOfInterestY1 = int(profile.regionOfInterestY1)
        profile.regionOfInterestY2 = int(profile.regionOfInterestY2)
        cls.profile = profile

        # The reader reads its calibration from the app-context singleton, not a parameter — install it.
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = profile
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(spectrometerProfile)

        cls.reference = LedReferenceSynthesisLogicModule().synthesize(
            LedReferenceSynthesisLogicModuleParameters()).getSpectrum()

    def _roundtrip(self, demoOil):
        parameters = OilSampleSynthesisLogicModuleParameters()
        parameters.setReference(self.reference)
        parameters.setTargetHue(demoOil.targetHue)
        sample = OilSampleSynthesisLogicModule().synthesize(parameters).getSpectrum()

        imageReference, imageSample = SpectrumToVirtualImageUtil().encode(
            self.reference, sample, self.profile,
            self.calibration.imageWidth, self.calibration.imageHeight)
        recoveredReference = _decode(imageReference)
        recoveredSample = _decode(imageSample)

        sourceColor = SpectralColorUtil().spectrumToColor(
            SpectrumUtil().transmission(self.reference, sample))
        recoveredColor = SpectralColorUtil().spectrumToColor(
            SpectrumUtil().transmission(recoveredReference, recoveredSample))
        return sourceColor, recoveredColor

    def test_roundtrip_hue_within_tolerance(self):
        for demoOil in PLAYGROUND_DEMO_OILS:
            source, recovered = self._roundtrip(demoOil)
            self.assertLessEqual(
                abs(_hue(recovered) - _hue(source)), HUE_TOLERANCE_DEGREES,
                "%s: recovered hue %.1f deg vs source %.1f deg" % (
                    demoOil.label, _hue(recovered), _hue(source)))

    def test_roundtrip_verdict_unchanged(self):
        for demoOil in PLAYGROUND_DEMO_OILS:
            source, recovered = self._roundtrip(demoOil)
            self.assertEqual(_verdict(_hue(recovered)), _verdict(_hue(source)), demoOil.label)


if __name__ == "__main__":
    unittest.main()
