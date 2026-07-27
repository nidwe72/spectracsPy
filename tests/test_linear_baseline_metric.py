"""The linear-baseline pigment metric (SPEC_capture_quality.md §16.10.2 / §16.10.9).

What is asserted here is the PROPERTY that motivates the metric: a re-seating tilt enters absorbance as an
offset AND a slope, and the corrected ratio must be blind to both. The plain Soret/Q ratio is asserted to be
vulnerable to exactly the same disturbance, so the tests document the difference rather than just the feature.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_linear_baseline_metric.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.feature.SpectrumFeatureLogicModule import SpectrumFeatureLogicModule
from sciens.spectracs.model.spectral.Spectrum import Spectrum

SORET = (440.0, 460.0)
Q_BAND = (560.0, 580.0)
WINDOWS = ((520.0, 540.0), (600.0, 630.0))


def _spectrum(builder):
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {float(nm): builder(float(nm)) for nm in range(440, 631, 2)}
    return spectrum


def _oil(nm):
    # A crude two-band stand-in: a Soret bump at 450 and a weaker Q bump at 570, flat elsewhere.
    soret = 0.30 * 2.718 ** (-((nm - 450.0) ** 2) / 200.0)
    q = 0.08 * 2.718 ** (-((nm - 570.0) ** 2) / 200.0)
    return 0.05 + soret + q


class LinearBaselineMetricTest(unittest.TestCase):

    def setUp(self):
        self.module = SpectrumFeatureLogicModule()

    def __ratio(self, spectrum):
        return self.module.bandMean(spectrum, *SORET) / self.module.bandMean(spectrum, *Q_BAND)

    def __correctedRatio(self, spectrum):
        return self.__ratio(self.module.linearBaselineCorrected(spectrum, WINDOWS))

    def test_a_tilt_leaves_the_corrected_ratio_unchanged(self):
        # THE point of the metric. A tilt = offset + slope; the corrected ratio must not move.
        clean = _spectrum(_oil)
        tilted = _spectrum(lambda nm: _oil(nm) + 0.04 + 0.0012 * (nm - 440.0))
        self.assertAlmostEqual(self.__correctedRatio(clean), self.__correctedRatio(tilted), places=6)

    def test_the_plain_ratio_is_NOT_immune_to_that_tilt(self):
        # The comparison that justifies the whole exercise — same two spectra, uncorrected.
        clean, tilted = _spectrum(_oil), _spectrum(lambda nm: _oil(nm) + 0.04 + 0.0012 * (nm - 440.0))
        self.assertGreater(abs(self.__ratio(clean) - self.__ratio(tilted)) / self.__ratio(clean), 0.20)

    def test_it_survives_a_pure_offset_and_a_pure_slope_separately(self):
        clean = _spectrum(_oil)
        for disturbance in (lambda nm: 0.09, lambda nm: 0.0018 * (nm - 440.0)):
            disturbed = _spectrum(lambda nm, d=disturbance: _oil(nm) + d(nm))
            self.assertAlmostEqual(self.__correctedRatio(clean), self.__correctedRatio(disturbed), places=6)

    def test_it_stays_invariant_to_path_length_and_concentration(self):
        # A -> k*A scales the fitted baseline too, so the ratio of two corrected band means is unchanged.
        # This is what makes the metric usable across dilutions AND across units with different cuvettes.
        clean = _spectrum(_oil)
        for factor in (0.5, 2.0, 3.7):
            scaled = _spectrum(lambda nm, k=factor: k * _oil(nm))
            self.assertAlmostEqual(self.__correctedRatio(clean), self.__correctedRatio(scaled), places=6)

    def test_the_correction_actually_zeroes_the_anchor_windows(self):
        corrected = self.module.linearBaselineCorrected(_spectrum(_oil), WINDOWS)
        for low, high in WINDOWS:
            self.assertAlmostEqual(self.module.bandMean(corrected, low, high), 0.0, places=2)

    def test_the_source_spectrum_is_not_mutated(self):
        source = _spectrum(_oil)
        before = dict(source.valuesByNanometers)
        corrected = self.module.linearBaselineCorrected(source, WINDOWS)
        self.assertIsNot(corrected, source)
        self.assertEqual(source.valuesByNanometers, before)

    def test_it_returns_none_when_a_line_cannot_be_fitted(self):
        self.assertIsNone(self.module.linearBaselineCorrected(None, WINDOWS))
        self.assertIsNone(self.module.linearBaselineCorrected(_spectrum(_oil), ((1000.0, 1010.0),)))
        single = Spectrum()
        single.valuesByNanometers = {530.0: 0.1}          # one anchor point — no slope is defined
        self.assertIsNone(self.module.linearBaselineCorrected(single, WINDOWS))


class RoastBaselineGaugeTest(unittest.TestCase):
    """The second gauge must classify the 2026-07-27 runs the way §16.10.7 says it does."""

    # All 15 runs of 2026-07-27 (spectracs-references/tmp/20260727B + C), linear-baseline values.
    GREEN = [11.471, 12.047, 11.342, 14.209, 11.620, 11.681, 14.162, 10.565, 11.921]
    BROWN = [9.855, 10.002, 9.406, 9.649, 9.543, 7.714]

    def setUp(self):
        from sciens.spectracs.plugin_sdk.util.GaugeColorUtil import GaugeColorUtil
        from sciens.spectracs.plugins.dev.RoastBaselineGaugeView import RoastBaselineGaugeView
        self.util, self.view = GaugeColorUtil(), RoastBaselineGaugeView

    def __verdict(self, value):
        return self.view(value, render=None).verdictLabel

    def test_it_separates_every_run_of_2026_07_27(self):
        # The claim in §16.10.7: all 9 green above all 6 brown, no run on the wrong side.
        for value in self.GREEN:
            self.assertEqual(self.__verdict(value), "good — green", "green run %.3f misclassified" % value)
        for value in self.BROWN:
            self.assertEqual(self.__verdict(value), "probably too brown", "brown run %.3f misclassified" % value)

    def test_the_threshold_sits_between_the_two_classes(self):
        self.assertGreater(min(self.GREEN), self.view._THRESHOLDS[0])
        self.assertLess(max(self.BROWN), self.view._THRESHOLDS[0])

    def test_the_band_brackets_every_observed_run(self):
        # A value past an edge clamps the marker only (RD#5), but the scale should not need to clamp real data.
        self.assertGreaterEqual(self.view._BAND_LEFT, max(self.GREEN))
        self.assertLessEqual(self.view._BAND_RIGHT, min(self.BROWN))


if __name__ == "__main__":
    unittest.main()
