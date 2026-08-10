"""The identity that makes the EVALUATION plot readable — SPEC_soret_448_trim.md §12.3.

    mean(curve over band) - mean(fittedBaseline over band) == bandMean(corrected over band)

The plot draws a BAR at the band mean of the plotted (despiked) curve and the FITTED BASELINE beneath it, so
the vertical gap between them IS the baselined value the gauges divide. If that identity ever stops holding,
the picture is lying while every number stays right — which is the one failure mode nothing else would catch
(the bars are fed a mean; feeding the WRONG mean raises nothing).

⚠ Deliberately also asserts the weaker sibling claim with a TOLERANCE, not equality: the baseline is a
weighted least-squares fit through every point of both anchor windows, NOT a chord through the two window
means, so an anchor band's bar sits ON the fitted line only up to the within-window residual (§16 duck #1).
"""
import unittest

from sciens.spectracs.logic.spectral.feature.SpectrumFeatureLogicModule import SpectrumFeatureLogicModule
from sciens.spectracs.model.spectral.Spectrum import Spectrum

SORET = (448.0, 460.0)
NEAR = (520.0, 540.0)
Q = (560.0, 580.0)
FAR = (620.0, 630.0)
WINDOWS = (NEAR, FAR)


def _spectrum():
    # A crude stand-in with the archive's shape: a big Soret flank, a small Q bump, a red rise on the Qy band,
    # and a tilted pedestal under all of it (the thing the baseline is there to remove).
    values = {}
    for step in range(0, 981):
        nm = 440.0 + step * 0.2
        pedestal = 0.030 + 0.00080 * (nm - 440.0)
        soret = 3.0 * 2.718 ** (-((nm - 432.0) ** 2) / 900.0)
        qBand = 0.075 * 2.718 ** (-((nm - 572.0) ** 2) / 120.0)
        qy = 0.055 * 2.718 ** (-((nm - 627.0) ** 2) / 90.0)
        values[round(nm, 1)] = pedestal + soret + qBand + qy
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(values)
    return spectrum


class BandBarIdentityTest(unittest.TestCase):

    def setUp(self):
        self.module = SpectrumFeatureLogicModule()
        self.spectrum = _spectrum()
        self.corrected = self.module.linearBaselineCorrected(self.spectrum, WINDOWS)
        self.baseline = self.module.fittedBaseline(self.spectrum, WINDOWS)

    def test_the_gap_between_the_bar_and_the_line_is_the_baselined_value(self):
        # The whole point of drawing bar + line: the gap IS the metric. Exact, not approximate.
        for band in (SORET, NEAR, Q, FAR):
            bar = self.module.bandMean(self.spectrum, *band)
            line = self.module.bandMean(self.baseline, *band)
            self.assertAlmostEqual(bar - line, self.module.bandMean(self.corrected, *band), places=10,
                                   msg="band %s" % (band,))

    def test_the_fitted_baseline_shares_the_curves_grid(self):
        # A bar and a line read on different grids would break the identity silently.
        self.assertEqual(sorted(self.baseline.valuesByNanometers.keys()),
                         sorted(self.spectrum.valuesByNanometers.keys()))

    def test_the_anchor_bars_sit_on_the_line_within_tolerance_but_not_exactly(self):
        # Duck #1: equal-weight LSQ across two windows, not a two-point chord — so this is a tolerance claim.
        for anchor in (NEAR, FAR):
            residual = self.module.bandMean(self.corrected, *anchor)
            self.assertLess(abs(residual), 0.02, msg="anchor %s drifted off the fitted line" % (anchor,))

    def test_the_soret_bar_floats_far_above_the_line_and_q_only_a_little(self):
        # The 16x asymmetry the second view is drawn to show (§12.3a / §16.24): if this ever inverts, the
        # plot's story and the error budget have parted company.
        soret = self.module.bandMean(self.corrected, *SORET)
        qBand = self.module.bandMean(self.corrected, *Q)
        self.assertGreater(soret, 0.0)
        self.assertGreater(qBand, 0.0)
        self.assertGreater(soret / qBand, 5.0)

    def test_no_baseline_when_the_windows_are_empty(self):
        self.assertIsNone(self.module.fittedBaseline(self.spectrum, ((900.0, 910.0),)))


if __name__ == "__main__":
    unittest.main()
