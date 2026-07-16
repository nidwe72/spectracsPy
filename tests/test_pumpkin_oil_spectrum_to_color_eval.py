"""
Pumpkin-oil spectrum -> colour evaluation — end-to-end regression of the SYNTHETIC pipeline
(SPEC_pipeline_playground.md / SPEC_measurement_evaluation_concept.md).

Two jobs:
  1. Assert the recipe's invariants headlessly — no Qt widgets, no server, no DB-write. The synthesis
     RECIPE (SpectrumSynthesisUtil + PlaygroundDemoOils) is the versioned source of truth; this test
     pins the expected behaviour (ordering, tolerances, verdict labels, T/A relationship, calibration).
  2. Render a DOCUMENTATION PDF of what the playground shows, to the NON-VERSIONED sibling folder
     spectracs-references/reports/ (the rendered artefact is not committed; the recipe is).

Decoupled from the (volatile) PlaygroundViewModule: depends only on the logic + matplotlib + the shared
CameraCaptureRenderUtil.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_pumpkin_oil_spectrum_to_color_eval.py -q
"""
import colorsys
import os
import unittest

import numpy

from sciens.spectracs.logic.playground.CameraCaptureRenderUtil import CameraCaptureRenderUtil
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumSynthesisUtil import SpectrumSynthesisUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.verdict.RoastState import RoastState
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModule import VerdictLogicModule
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleParameters import VerdictLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum


def _verdict(hue):
    parameters = VerdictLogicModuleParameters(); parameters.setHue(hue)
    return VerdictLogicModule().verdict(parameters).getRoastState()


class PumpkinOilSpectrumToColorEvalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.reference = LedReferenceSynthesisLogicModule().synthesize(
            LedReferenceSynthesisLogicModuleParameters()).getSpectrum()
        cls.oils = []
        for demoOil in PLAYGROUND_DEMO_OILS:
            parameters = OilSampleSynthesisLogicModuleParameters()
            parameters.setReference(cls.reference); parameters.setTargetHue(demoOil.targetHue)
            cls.oils.append((demoOil, OilSampleSynthesisLogicModule().synthesize(parameters)))

    # --- reference (LED light source) -----------------------------------------------------------

    def test_reference_is_continuous_above_410nm(self):
        values = self.reference.valuesByNanometers
        floor = 0.02 * max(values.values())
        weak = [nm for nm in range(410, 701) if values[nm] < floor]
        self.assertEqual(weak, [], "reference has a near-zero gap at %s" % weak[:6])

    def test_reference_strong_in_diagnostic_bands(self):
        values = self.reference.valuesByNanometers
        maximum = max(values.values())
        for low, high in [(430, 480), (520, 560), (630, 670)]:
            bandMax = max(values[nm] for nm in range(low, high + 1))
            self.assertGreater(bandMax / maximum, 0.3, "diagnostic band %d-%d too weak" % (low, high))

    # --- oil model ------------------------------------------------------------------------------

    def test_transmission_hue_monotonic_in_roast(self):
        util = SpectrumSynthesisUtil()
        previousHue = 999.0
        for roast in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            hue = util.transmissionHue(self.reference, util.synthesizeSample(self.reference, roast))
            self.assertLessEqual(hue, previousHue + 0.5, "hue not monotonic at roast %s" % roast)
            previousHue = hue

    def test_three_oils_hit_their_targets(self):
        for demoOil, result in self.oils:
            self.assertLessEqual(abs(result.getAchievedHue() - demoOil.targetHue), 4.0,
                                 "%s hue %.1f off target %.1f" % (demoOil.label, result.getAchievedHue(),
                                                                  demoOil.targetHue))

    def test_three_oils_hues_strictly_ordered_under_perfect_over(self):
        hues = [result.getAchievedHue() for _, result in self.oils]  # order: under, perfect, over
        self.assertGreater(hues[0], hues[1], "under should be greener (higher hue) than perfect")
        self.assertGreater(hues[1], hues[2], "perfect should be greener than over-roasted")

    def test_three_oils_verdicts_match_roast_state(self):
        for demoOil, result in self.oils:
            self.assertEqual(_verdict(result.getAchievedHue()), demoOil.roastState, demoOil.label)

    # --- transmission / absorption ops ----------------------------------------------------------

    def test_transmission_absorption_and_low_reference_guard(self):
        reference = Spectrum(); reference.setValuesByNanometers({450: 1.0, 500: 0.005, 550: 0.8, 600: 1.0})
        sample = Spectrum(); sample.setValuesByNanometers({450: 0.5, 500: 0.004, 550: 0.4, 600: 0.1})
        transmission = SpectrumUtil().transmission(reference, sample)
        absorption = SpectrumUtil().absorption(reference, sample)
        self.assertNotIn(500, transmission.valuesByNanometers, "low-reference guard should mask 500 nm")
        self.assertAlmostEqual(transmission.valuesByNanometers[450], 0.5)
        self.assertAlmostEqual(absorption.valuesByNanometers[600], 1.0)  # -log10(0.1)

    def test_verdict_band_edges(self):
        self.assertEqual(_verdict(72.0), RoastState.UNDER_ROASTED)
        self.assertEqual(_verdict(60.0), RoastState.PERFECT_ROASTED)
        self.assertEqual(_verdict(35.0), RoastState.OVER_ROASTED)

    # --- calibration (integration: real CFL image, cv2 + advanced matcher) ----------------------

    def test_cfl_calibration_is_monotonic_and_plausible(self):
        calibration = PlaygroundCalibrationLogicModule().calibrate()
        polynomial = calibration.polynomial()
        x1 = int(calibration.profile.regionOfInterestX1)
        x2 = int(calibration.profile.regionOfInterestX2)
        self.assertLess(x1, x2)
        step = max(1, (x2 - x1) // 50)
        nanometers = [float(polynomial(x)) for x in range(x1, x2, step)]
        self.assertTrue(all(nanometers[i] <= nanometers[i + 1] for i in range(len(nanometers) - 1)),
                        "px->nm polynomial is not monotonic")
        self.assertTrue(380.0 < calibration.nanometerAtX1 < 470.0,
                        "violet start nm implausible: %.1f" % calibration.nanometerAtX1)
        self.assertTrue(560.0 < calibration.nanometerAtX2 < 720.0,
                        "red end nm implausible: %.1f" % calibration.nanometerAtX2)

    # --- documentation PDF (side artefact; never gates the regression) ---------------------------

    def test_zzz_render_documentation_pdf(self):
        outputPath = renderDocumentationPdf(self.reference, self.oils,
                                            PlaygroundCalibrationLogicModule().calibrate())
        self.assertTrue(os.path.exists(outputPath) and os.path.getsize(outputPath) > 2000,
                        "documentation PDF was not written")


def _reportPath():
    here = os.path.dirname(__file__)
    reportsDir = os.path.normpath(os.path.join(here, "..", "..", "spectracs-references", "reports"))
    os.makedirs(reportsDir, exist_ok=True)
    return os.path.join(reportsDir, "PumpkinOilSpectrumToColorEval.pdf")


def _sortedXY(spectrum):
    nanometers = sorted(spectrum.valuesByNanometers.keys())
    return nanometers, [spectrum.valuesByNanometers[nm] for nm in nanometers]


def renderDocumentationPdf(reference, oils, calibration):
    # Re-renders the same data the playground shows into a multi-page PDF (matplotlib Agg). Decoupled
    # from the view; camera strips come from the shared CameraCaptureRenderUtil so they match the app.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from PIL import Image  # content-detected load (the CFL file is JPEG despite a .png name)

    outputPath = _reportPath()
    referenceNanometers, referenceValues = _sortedXY(reference)

    computed = []
    for demoOil, result in oils:
        sample = result.getSpectrum()
        transmission = SpectrumUtil().transmission(reference, sample)
        absorption = SpectrumUtil().absorption(reference, sample)
        measuredColor = SpectralColorUtil().spectrumToColor(transmission)
        computed.append((demoOil, result, sample, absorption, measuredColor))

    with PdfPages(outputPath) as pdf:
        # 1) title + recipe (with the Spectracs logo)
        figure = plt.figure(figsize=(8.3, 11.7)); figure.clf()
        logoPath = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "docs", "assets",
                                                 "spectracs_logo.png"))
        textTop = 0.93
        if os.path.exists(logoPath):
            logoAxes = figure.add_axes([0.07, 0.90, 0.52, 0.06]); logoAxes.axis("off")
            logoAxes.imshow(numpy.asarray(Image.open(logoPath)))
            textTop = 0.86
        lines = ["Pumpkin oil — spectrum to colour evaluation",
                 "Synthetic proof-of-concept (SPEC_pipeline_playground.md)", "",
                 "Recipe (versioned): LED reference + physical oil model, reference-normalised T=S/R,",
                 "colour(T) under fixed D65, hue -> roast-state verdict.", "",
                 "Calibration: fresh automatic CFL — nm range %.1f .. %.1f" % (
                     calibration.nanometerAtX1, calibration.nanometerAtX2), ""]
        for demoOil, result, _sample, _absorption, color in computed:
            lines.append("  %-16s target %4.0f°  ->  measured %4.0f°  %s   swatch %s" % (
                demoOil.label, demoOil.targetHue, result.getAchievedHue(),
                _verdict(result.getAchievedHue()).value, color.name()))
        figure.text(0.07, textTop, "\n".join(lines), va="top", family="monospace", fontsize=10)
        pdf.savefig(figure); plt.close(figure)

        # 2) calibration image
        figure, axes = plt.subplots(figsize=(8.3, 6))
        axes.imshow(numpy.asarray(Image.open(calibration.imagePath))); axes.axis("off")
        axes.set_title("Calibration capture (Philips CFL) — ROI x %d-%d, y %d-%d" % (
            calibration.profile.regionOfInterestX1, calibration.profile.regionOfInterestX2,
            calibration.profile.regionOfInterestY2, calibration.profile.regionOfInterestY1))
        pdf.savefig(figure); plt.close(figure)

        # 3) LED setup
        figure, axes = plt.subplots(figsize=(8.3, 5.2))
        for name, spd in SpectrumSynthesisUtil().perLedSpectra(nanometers=referenceNanometers):
            axes.plot(referenceNanometers, list(spd), linewidth=1.0, label=name)
        axes.plot(referenceNanometers, referenceValues, color="black", linewidth=2.0, label="overall R(λ)")
        axes.set_title("LED setup — individual SPDs + overall reference"); axes.set_xlabel("nm")
        axes.legend(fontsize=7); pdf.savefig(figure); plt.close(figure)

        # 4) reference + 5) oil spectra + 6) absorption
        figure, axes = plt.subplots(figsize=(8.3, 4.0))
        axes.plot(referenceNanometers, referenceValues, color="#2e7d32")
        axes.set_title("Reference spectrum R(λ)"); axes.set_xlabel("nm"); pdf.savefig(figure); plt.close(figure)

        figure, axes = plt.subplots(figsize=(8.3, 4.0))
        for demoOil, _result, sample, _absorption, color in computed:
            nanometers, values = _sortedXY(sample)
            axes.plot(nanometers, values, label=demoOil.label, color=(color.redF(), color.greenF(), color.blueF()))
        axes.set_title("Oil sample spectra S(λ)"); axes.set_xlabel("nm"); axes.legend()
        pdf.savefig(figure); plt.close(figure)

        figure, axes = plt.subplots(figsize=(8.3, 4.0))
        for demoOil, _result, _sample, absorption, color in computed:
            nanometers, values = _sortedXY(absorption)
            axes.plot(nanometers, values, label=demoOil.label, color=(color.redF(), color.greenF(), color.blueF()))
        axes.set_title("Absorption A = -log10(T)"); axes.set_xlabel("nm"); axes.legend()
        pdf.savefig(figure); plt.close(figure)

        # 7) camera captures (shared renderer)
        captures = [("REFERENCE", reference)] + [(demoOil.label, sample)
                                                 for demoOil, _r, sample, _a, _c in computed]
        figure, axesList = plt.subplots(len(captures), 1, figsize=(8.3, 1.4 * len(captures)))
        for axis, (label, spectrum) in zip(axesList, captures):
            axis.imshow(CameraCaptureRenderUtil().renderStripArray(spectrum, calibration))
            axis.set_title(label, fontsize=8); axis.axis("off")
        figure.suptitle("Camera capture (what the sensor sees)"); figure.tight_layout()
        pdf.savefig(figure); plt.close(figure)

        # 8) measured vs target swatches
        figure, axes = plt.subplots(figsize=(8.3, 3.5)); axes.axis("off")
        axes.set_title("Measured vs target")
        for row, (demoOil, result, _sample, _absorption, color) in enumerate(computed):
            y = 0.8 - row * 0.25
            axes.text(0.05, y + 0.05, demoOil.label, fontsize=10)
            axes.add_patch(plt.Rectangle((0.35, y), 0.12, 0.12, color=(color.redF(), color.greenF(), color.blueF())))
            targetRgb = colorsys.hls_to_rgb(demoOil.targetHue / 360.0, 0.20, 0.85)
            axes.add_patch(plt.Rectangle((0.50, y), 0.12, 0.12, color=targetRgb))
            axes.text(0.66, y + 0.05, "%.0f°  %s" % (result.getAchievedHue(),
                                                     _verdict(result.getAchievedHue()).value), fontsize=10)
        axes.text(0.35, 0.95, "measured", fontsize=9); axes.text(0.50, 0.95, "target", fontsize=9)
        pdf.savefig(figure); plt.close(figure)

    return outputPath


if __name__ == "__main__":
    unittest.main()
