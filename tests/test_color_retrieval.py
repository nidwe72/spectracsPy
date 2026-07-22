"""SPEC_color_retrieval.md — the colour-chip machinery (K4).

Proves the physics (dilution-invariance of the absorbance colour, dichromatism of the transmission colour) and the
guards (F9 negative-absorbance clamp, F10 achromatic source), plus a render smoke for the swatch+HSL cell.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_color_retrieval.py -q
"""
import math
import unittest

from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.model.spectral.Spectrum import Spectrum


def _spectrum(valuesByNanometers):
    spectrum = Spectrum()
    spectrum.valuesByNanometers = dict(valuesByNanometers)
    return spectrum


def _absorbance():
    # A pumpkin-ish absorbance: strong in the blue (~460), a Q-band bump (~575), low in the green.
    out = {}
    for nanometer in range(400, 701, 5):
        blue = math.exp(-((nanometer - 460) / 40.0) ** 2) * 1.2
        qband = math.exp(-((nanometer - 575) / 15.0) ** 2) * 0.5
        out[nanometer] = blue + qband + 0.05
    return out


def _hueDelta(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


class DilutionInvarianceTest(unittest.TestCase):
    """F8 — the property that justifies the whole intrinsic/perceived split."""

    def setUp(self):
        self.util = EvaluationColorUtil()
        self.absorbance = _absorbance()

    def test_absorbance_hue_invariant_under_scaling(self):
        # A → 2·A (twice the oil): chromaticity — hence hue — must not move.
        hue1, _, _ = self.util.spectrumToHsl(_spectrum(self.absorbance), converter="srgb")
        doubled = {nm: 2.0 * v for nm, v in self.absorbance.items()}
        hue2, _, _ = self.util.spectrumToHsl(_spectrum(doubled), converter="srgb")
        self.assertLess(_hueDelta(hue1, hue2), 2.0)

    def test_transmission_hue_shifts_with_dilution(self):
        # T = 10^-A, doubling the oil → T² : the hue MUST move (dichromatism).
        transmission = {nm: 10.0 ** (-v) for nm, v in self.absorbance.items()}
        squared = {nm: 10.0 ** (-2.0 * v) for nm, v in self.absorbance.items()}
        hue1, _, _ = self.util.spectrumToHsl(_spectrum(transmission), converter="rgbxy")
        hue2, _, _ = self.util.spectrumToHsl(_spectrum(squared), converter="rgbxy")
        self.assertGreater(_hueDelta(hue1, hue2), 3.0)


class ComplementTest(unittest.TestCase):
    """SPEC_capability_proof.md option (b) — colorIntrinsicPerceived as the white-point complement of the absorbed
    colour, replacing the old +180° HSL hue flip (validated ~4° vs ~34° on K/L/M/N)."""

    def setUp(self):
        self.util = EvaluationColorUtil()
        self.absorbance = _absorbance()

    def test_complement_beats_the_180_flip_against_true_perceived_hue(self):
        absHue, _, _ = self.util.spectrumToHsl(_spectrum(self.absorbance), converter="srgb", ceiling=3.0)
        compHue, _, _ = self.util.complementViaWhitePoint(_spectrum(self.absorbance), ceiling=3.0)
        # ground truth: the perceived hue of the transmission this absorbance implies (T = 10^-A)
        transmission = {nm: 10.0 ** (-v) for nm, v in self.absorbance.items()}
        percHue, _, _ = self.util.spectrumToHsl(_spectrum(transmission), converter="srgb")
        flip = (absHue + 180.0) % 360.0
        self.assertLess(_hueDelta(compHue, percHue), _hueDelta(flip, percHue))  # closer to the truth than +180
        self.assertTrue(30.0 <= compHue <= 110.0, compHue)                      # green-yellow family, not blue-violet

    def test_complement_is_dilution_invariant(self):
        c1, _, _ = self.util.complementViaWhitePoint(_spectrum(self.absorbance), ceiling=3.0)
        doubled = {nm: 2.0 * v for nm, v in self.absorbance.items()}
        c2, _, _ = self.util.complementViaWhitePoint(_spectrum(doubled), ceiling=3.0)
        self.assertLess(_hueDelta(c1, c2), 2.0)

    def test_complement_of_grey_is_achromatic(self):
        flat = _spectrum({nm: 1.0 for nm in range(400, 701, 5)})
        _, saturation, lightness = self.util.complementViaWhitePoint(flat)
        self.assertLess(self.util.chroma(saturation, lightness), EvaluationColorUtil.ACHROMATIC_CHROMA)

    def test_complement_of_empty_is_zero(self):
        self.assertEqual(self.util.complementViaWhitePoint(_spectrum({})), (0.0, 0.0, 0.0))


class GuardsTest(unittest.TestCase):

    def test_negative_absorbance_does_not_crash(self):
        # F9: A goes negative where T>1 (noise). It must be clamped, not corrupt the CIE integral.
        util = EvaluationColorUtil()
        spectrum = _spectrum({nm: (v - 0.3) for nm, v in _absorbance().items()})  # push some values < 0
        hue, saturation, lightness = util.spectrumToHsl(spectrum, converter="srgb", ceiling=3.0)
        for value in (hue, saturation, lightness):
            self.assertTrue(math.isfinite(value))
        self.assertGreaterEqual(hue, 0.0)
        self.assertLess(hue, 360.0)

    def test_flat_spectrum_is_achromatic(self):
        # F10: a flat spectrum is grey → CHROMA below the achromatic threshold on BOTH converters (raw HLS
        # saturation would wrongly read ~100% near white — hence chroma).
        util = EvaluationColorUtil()
        flat = _spectrum({nm: 1.0 for nm in range(400, 701, 5)})
        for converter in ("rgbxy", "srgb"):
            _, saturation, lightness = util.spectrumToHsl(flat, converter=converter)
            self.assertLess(util.chroma(saturation, lightness), EvaluationColorUtil.ACHROMATIC_CHROMA, converter)

    def test_empty_spectrum_returns_zero(self):
        self.assertEqual(EvaluationColorUtil().spectrumToHsl(_spectrum({}), converter="srgb"), (0.0, 0.0, 0.0))

    def test_rgb_from_hsl(self):
        util = EvaluationColorUtil()
        red, green, blue = util.rgbFromHsl(120.0, 80.0, 50.0)          # green
        self.assertGreater(green, red)
        self.assertGreater(green, blue)
        # hue wraps
        self.assertEqual(util.rgbFromHsl(30.0, 80.0, 50.0), util.rgbFromHsl(390.0, 80.0, 50.0))
        # the +180 complement of a blue-violet hue lands in the yellow-green family
        complement = (250.0 + 180.0) % 360.0
        self.assertTrue(60.0 <= complement <= 110.0)


class RenderSmokeTest(unittest.TestCase):
    """K2/F12 — a MetricFieldView carrying BOTH color and value renders in both targets."""

    def test_matplotlib_renders_swatch_plus_hsl(self):
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
        view = MetricFieldView("Intrinsic", value="H 96° · S 80% · L 50%", color=(40, 200, 60))
        figures = MatplotlibWorkflowRenderer().render(ReportView("test"), [("Evaluation", [view])])
        self.assertTrue(figures)                       # must not raise; draws swatch + text

    def test_qt_renders_swatch_plus_hsl(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
        QApplication.instance() or QApplication([])
        widget = QtWorkflowRenderer().render([MetricFieldView("Intrinsic", value="H 96°", color=(40, 200, 60))])
        self.assertIsNotNone(widget)                   # color+value cell built without error


if __name__ == "__main__":
    unittest.main()
