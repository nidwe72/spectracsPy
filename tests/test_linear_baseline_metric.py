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

    def test_a_window_does_not_dominate_the_fit_by_having_more_points(self):
        # A window is ONE piece of evidence about the baseline, not one per sample point. Sampling one window
        # more densely — same span, same values — must not drag the fit toward it.
        #
        # This is a MUCH-REDUCED sensitivity, not an exact invariance: the within-window spread of λ still
        # depends on the point count, so a small residual remains. What equal weighting buys is measured
        # here rather than asserted as absolute — on this construction the corrected value at 450 nm shifts
        # 8.03 % under the old unweighted fit and 0.31 % under equal weighting, a factor of ~26.
        step = lambda nm: 0.10 if nm <= 560.0 else 0.20   # the windows disagree, so weighting has leverage
        sparse = _spectrum(step)
        dense = _spectrum(step)
        denser = dict(sparse.valuesByNanometers)                          # 600-630 sampled 4x denser
        denser.update({600.0 + 0.5 * i: step(600.0 + 0.5 * i) for i in range(61)})
        dense.valuesByNanometers = denser

        def shift(corrector):
            a, b = corrector(sparse), corrector(dense)
            return abs(a - b) / abs(a)

        def equalWeighted(spectrum):
            return self.module.linearBaselineCorrected(spectrum, WINDOWS).valuesByNanometers[450.0]

        def unweighted(spectrum):
            # What the op used to do — plain least-squares over every anchor point.
            import numpy
            lam = numpy.array(sorted(spectrum.valuesByNanometers))
            val = numpy.array([spectrum.valuesByNanometers[k] for k in lam])
            mask = numpy.zeros_like(lam, dtype=bool)
            for low, high in WINDOWS:
                mask |= (lam >= low) & (lam <= high)
            slope, intercept = numpy.polyfit(lam[mask], val[mask], 1)
            return step(450.0) - (slope * 450.0 + intercept)

        self.assertGreater(shift(unweighted), 0.05)          # the old behaviour moves materially
        self.assertLess(shift(equalWeighted), 0.01)          # the new one barely moves
        self.assertLess(shift(equalWeighted) * 10, shift(unweighted))

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

    # All 21 runs of 2026-07-27, linear-baseline values as the plugin computes them (de-spiked).
    #   anchoring set  (§16.10.7)  20260727B = green, 20260727C = brown
    #   OUT-OF-SAMPLE  (§16.10.7a) 20260727E = green, 20260727D = brown — measured AFTER the threshold
    #                              was fixed, and classified 6/6 by it with nothing refitted.
    ANCHORING_GREEN = [11.534, 12.119, 11.422, 14.273, 11.666, 11.725, 14.261, 10.604, 11.979]
    ANCHORING_BROWN = [9.859, 10.011, 9.420, 9.662, 9.553, 7.722]
    FRESH_GREEN = [13.500, 12.931, 12.194]
    FRESH_BROWN = [9.469, 7.812, 8.032]
    LATER_GREEN = [13.132, 11.936, 10.506, 11.051]   # 20260727E 004-007, added after the fresh check
    GREEN = ANCHORING_GREEN + FRESH_GREEN + LATER_GREEN
    BROWN = ANCHORING_BROWN + FRESH_BROWN

    def setUp(self):
        from sciens.spectracs.plugin_sdk.util.GaugeColorUtil import GaugeColorUtil
        from sciens.spectracs.plugins.dev.RoastBaselineGaugeView import RoastBaselineGaugeView
        self.util, self.view = GaugeColorUtil(), RoastBaselineGaugeView

    def __verdict(self, value):
        return self.view(value, render=None).verdictLabel

    # §16.10.17d — the threshold moved 10.3 -> 10.6 as a POLICY choice (passing bad oil is the costlier
    # error), which deliberately accepts a small number of false BROWNs. These are the accepted ones.
    ACCEPTED_FALSE_BROWN = [10.506]      # 20260727E/006

    def test_no_brown_run_is_ever_called_green(self):
        # THE asymmetric guarantee the 10.6 policy buys: a false GREEN ships bad oil, so this direction
        # must be clean. It is the assertion that would have to fail before the threshold is lowered again.
        for value in self.BROWN:
            self.assertEqual(self.__verdict(value), "probably too brown",
                             "brown run %.3f called GREEN — the costly direction" % value)

    def test_green_runs_are_correct_except_the_accepted_false_browns(self):
        for value in self.GREEN:
            if value in self.ACCEPTED_FALSE_BROWN:
                self.assertEqual(self.__verdict(value), "probably too brown",
                                 "%.3f is documented as an accepted false brown" % value)
                continue
            self.assertEqual(self.__verdict(value), "good — green", "green run %.3f misclassified" % value)

    def test_the_out_of_sample_runs_are_classified_by_the_unrefitted_threshold(self):
        # §16.10.7a — these six were measured AFTER the threshold was fixed. Called out separately from the
        # anchoring set because only THIS assertion is evidence rather than curve-fitting: a threshold always
        # classifies the data it was drawn from. (They pre-date the 10.6 policy move and still all pass.)
        for value in self.FRESH_GREEN:
            self.assertEqual(self.__verdict(value), "good — green")
        for value in self.FRESH_BROWN:
            self.assertEqual(self.__verdict(value), "probably too brown")

    def test_the_threshold_sits_above_the_brown_class_and_is_deliberately_strict(self):
        threshold = self.view._THRESHOLDS[0]
        self.assertGreater(threshold, max(self.BROWN))          # no brown may reach it
        self.assertLess(threshold, min(v for v in self.GREEN    # but it IS above the lowest green, on purpose
                                       if v not in self.ACCEPTED_FALSE_BROWN))
        self.assertLess(min(self.GREEN), threshold)             # ...which is what makes it strict

    def test_the_band_brackets_every_observed_run(self):
        # A value past an edge clamps the marker only (RD#5), but the scale should not need to clamp real data.
        self.assertGreaterEqual(self.view._BAND_LEFT, max(self.GREEN))
        self.assertLessEqual(self.view._BAND_RIGHT, min(self.BROWN))


if __name__ == "__main__":
    unittest.main()
