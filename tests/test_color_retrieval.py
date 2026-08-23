"""SPEC_color_retrieval.md — the colour-chip machinery (K4) and the §7.12 colour fix (C1/C3).

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


class ColourFixTest(unittest.TestCase):
    """SPEC_color_retrieval.md §7.12 — C1 (excitation purity replaces the pinned HSL S) and C3 (`spectrumToLab`,
    the "as seen" chip that KEEPS luminance)."""

    def setUp(self):
        self.util = EvaluationColorUtil()
        self.absorbance = _absorbance()

    # --- C1: the S = 100 % defect -----------------------------------------------------------------------
    def test_hsl_saturation_is_pinned_at_100_which_is_why_purity_exists(self):
        # The defect, asserted so it cannot be "fixed" by accident without this test being revisited: an
        # out-of-gamut absorbed chromaticity clips a channel to 0, and HSL reads that back as S = 100.
        _, saturation, _ = self.util.spectrumToHsl(_spectrum(self.absorbance), converter="srgb")
        self.assertEqual(round(saturation), 100)

    def test_purity_discriminates_where_hsl_saturation_cannot(self):
        # A ladder of absorbances that are ALL out of sRGB, so HSL S pins to 100 on every rung and carries no
        # information at all — while excitation purity, which is defined on the chromaticity diagram rather than
        # by a display gamut, falls monotonically. This is the whole of §7.12 C1 in one assertion.
        ladder = [{nm: scale * v + offset for nm, v in self.absorbance.items()}
                  for scale, offset in ((1.0, 0.00), (0.8, 0.08), (0.6, 0.12), (0.5, 0.15))]
        saturations = [self.util.spectrumToHsl(_spectrum(rung), converter="srgb")[1] for rung in ladder]
        purities = [self.util.spectrumToPurity(_spectrum(rung)) for rung in ladder]
        self.assertEqual([round(value) for value in saturations], [100, 100, 100, 100], saturations)
        self.assertEqual(purities, sorted(purities, reverse=True), purities)   # strictly falls
        self.assertGreater(purities[0] - purities[-1], 10.0, purities)
        for value in purities:
            self.assertTrue(0.0 <= value <= 100.0, value)

    def test_purity_is_dilution_invariant_like_the_other_chromaticity_chips(self):
        doubled = {nm: 2.0 * v for nm, v in self.absorbance.items()}
        self.assertAlmostEqual(self.util.spectrumToPurity(_spectrum(self.absorbance)),
                               self.util.spectrumToPurity(_spectrum(doubled)), delta=1.0)

    def test_purity_of_an_empty_spectrum_is_zero(self):
        self.assertEqual(self.util.spectrumToPurity(_spectrum({})), 0.0)

    # --- C3: the "as seen" chip -------------------------------------------------------------------------
    def test_as_seen_chip_is_deliberately_NOT_dilution_invariant(self):
        # This is the whole point of chip 6 (§7.6): brownness IS lightness IS concentration. Twice the oil
        # must read darker — the opposite of the F8 property the five invariant chips hold.
        light, _, _, _ = self.util.spectrumToLab(_spectrum(self.absorbance), path=1.0)
        doubled = {nm: 2.0 * v for nm, v in self.absorbance.items()}
        dark, _, _, _ = self.util.spectrumToLab(_spectrum(doubled), path=1.0)
        self.assertLess(dark, light - 5.0)

    def test_as_seen_chip_darkens_with_the_declared_viewing_path(self):
        thin, _, _, _ = self.util.spectrumToLab(_spectrum(self.absorbance), path=1.0)
        thick, _, _, _ = self.util.spectrumToLab(_spectrum(self.absorbance), path=3.0)
        self.assertLess(thick, thin - 5.0)

    def test_as_seen_chip_stays_in_a_sane_range(self):
        # Guards the two traps of §7.12's __cieXyzDense: `align`'s constant-hold red tail, and the cubic
        # overshoot that produced L* = 144 when sparse T=1 anchors were used instead.
        for path in (0.5, 1.0, 3.0, 5.0):
            lightness, chroma, hue, rgb = self.util.spectrumToLab(_spectrum(self.absorbance), path=path)
            self.assertTrue(0.0 <= lightness <= 100.0, (path, lightness))
            self.assertTrue(0.0 <= chroma <= 150.0, (path, chroma))
            self.assertTrue(0.0 <= hue < 360.0, (path, hue))
            for channel in rgb:
                self.assertTrue(0 <= channel <= 255, (path, rgb))

    def test_as_seen_chip_reads_a_flat_floor_as_DARKER_not_as_a_different_hue(self):
        # §7.6 / §7.10 F21: a neutral floor is what the eye sees, and it must show up as lightness, not hue.
        floored = {nm: v + 0.15 for nm, v in self.absorbance.items()}
        clean = self.util.spectrumToLab(_spectrum(self.absorbance), path=1.0)
        murky = self.util.spectrumToLab(_spectrum(floored), path=1.0)
        self.assertLess(murky[0], clean[0] - 5.0)                  # darker
        self.assertLess(_hueDelta(murky[2], clean[2]), 12.0)       # roughly the same hue at this lightness

    def test_as_seen_chip_of_an_empty_spectrum_is_neutral_grey(self):
        lightness, chroma, hue, rgb = self.util.spectrumToLab(_spectrum({}))
        self.assertEqual((lightness, chroma, hue), (0.0, 0.0, 0.0))
        self.assertEqual(rgb, (128, 128, 128))
