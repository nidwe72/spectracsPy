"""
Tooling (SPEC_pumpkin_integration.md A.5): bake the versioned pumpkin-oil virtual-capture image sets that
the virtual-spectrometer folder picker (A.4) consumes. For each demo oil it writes a folder

    spectracs-references/pumpkin_oil/virtual_captures/pumpkinoil_<variant>_v1/
        calibration.png   (the bundled CFL capture — the app calibrates the profile from this)
        reference.png     (encoded REFERENCE strip, shared vmax)
        sample.png        (encoded SAMPLE strip,    shared vmax)
        set.json          (provenance)

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python tests/bake_virtual_capture_sets.py
"""
import json
import os
import shutil

from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumToVirtualImageUtil import SpectrumToVirtualImageUtil
from sciens.spectracs.logic.spectral.verdict.RoastState import RoastState

ENCODER_VERSION = "v1"

_VARIANT_BY_ROAST = {
    RoastState.UNDER_ROASTED: "under",
    RoastState.PERFECT_ROASTED: "perfect",
    RoastState.OVER_ROASTED: "over",
}


def _defaultOutputRoot():
    here = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(here, "..", "..", "spectracs-references",
                                         "pumpkin_oil", "virtual_captures"))


def bake(outputRoot=None):
    outputRoot = outputRoot or _defaultOutputRoot()
    calibration = PlaygroundCalibrationLogicModule().calibrate()
    reference = LedReferenceSynthesisLogicModule().synthesize(
        LedReferenceSynthesisLogicModuleParameters()).getSpectrum()

    written = []
    for demoOil in PLAYGROUND_DEMO_OILS:
        parameters = OilSampleSynthesisLogicModuleParameters()
        parameters.setReference(reference)
        parameters.setTargetHue(demoOil.targetHue)
        result = OilSampleSynthesisLogicModule().synthesize(parameters)
        sample = result.getSpectrum()

        imageReference, imageSample = SpectrumToVirtualImageUtil().encode(
            reference, sample, calibration.profile, calibration.imageWidth, calibration.imageHeight)

        variant = _VARIANT_BY_ROAST[demoOil.roastState]
        folder = os.path.join(outputRoot, "pumpkinoil_%s_%s" % (variant, ENCODER_VERSION))
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(calibration.imagePath, os.path.join(folder, "calibration.png"))
        imageReference.save(os.path.join(folder, "reference.png"), "PNG")
        imageSample.save(os.path.join(folder, "sample.png"), "PNG")
        with open(os.path.join(folder, "set.json"), "w") as handle:
            json.dump({
                "usecase": "pumpkinoil",
                "variant": variant,
                "encoderVersion": ENCODER_VERSION,
                "roastState": demoOil.roastState.value,
                "targetHue": demoOil.targetHue,
                "achievedHue": round(result.getAchievedHue(), 2),
                "sharedVmax": True,
                "resample": "linear",
                "imageWidth": calibration.imageWidth,
                "imageHeight": calibration.imageHeight,
            }, handle, indent=2)
        written.append(folder)
    return written


if __name__ == "__main__":
    for folder in bake():
        print("baked", folder)
