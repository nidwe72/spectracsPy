"""SPEC_v_metric_integration.md §6.1 — the V tab's own bar identity, sibling of `test_band_bar_identity`.

    the bar at ① IS A_Soret · the bar at ② IS A_valley · the bar at ③ IS A_Q
    and the number on screen, Q% = 100·(③ − ②)/①, is the gap ②→③ over the gap ⑤→①

⛔ THE FAILURE THIS EXISTS FOR. Feeding a bar the wrong curve — the baseline-corrected one, say, as the
chord tab legitimately does — raises nothing, renders plausibly, and makes the picture lie while every
number stays right. `V` subtracts nothing, so ALL THREE of its bars must sit on the DESPIKED curve.

⚠ It also pins the direction: the plot's two visible gaps must reconstruct the displayed metric exactly.
If someone later "improves" the plot by drawing the bars on a corrected curve, Q% and the picture part
company silently — and this is the only thing that would notice.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_v_band_bar_identity.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.feature.SpectrumFeatureLogicModule import SpectrumFeatureLogicModule
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

SORET = (448.0, 460.0)
VALLEY = (500.0, 560.0)
Q = (565.0, 580.0)


def _spectrum():
    # The archive's shape: a big Soret flank, a valley whose minimum sits near its LEFT edge, a Q bump,
    # a Qy rise at the red end, and a tilted pedestal under all of it — the thing `V` deliberately does
    # NOT remove, because its numerator is a difference and its denominator a level.
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


class VBandBarIdentityTest(unittest.TestCase):

    def setUp(self):
        self.module = SpectrumFeatureLogicModule()
        self.plugin = DevSpectralPlugin()
        self.despiked = self.plugin._DevSpectralPlugin__despikedAbsorption(_spectrum())
        self.view = self.plugin._DevSpectralPlugin__vBandPlot(self.despiked)
        self.levels = {level[6]: level for level in self.view.levels}

    def testEachBarIsTheBandMeanOfTheDespikedCurve(self):
        for number, window in ((1, SORET), (2, VALLEY), (3, Q)):
            bar = self.levels[number]
            self.assertEqual(window, (bar[1], bar[2]), "bar %d spans the wrong window" % number)
            self.assertAlmostEqual(self.module.bandMean(self.despiked, *window), bar[0], places=12,
                                   msg="bar %d is not the DESPIKED curve's band mean" % number)

    def testTheBarsAreNotOnABaselinedCurve(self):
        # ⛔ The specific wrong curve: the chord-corrected one. On a pedestalled spectrum it differs by
        # far more than rounding, so this cannot pass by accident.
        corrected = self.module.linearBaselineCorrected(self.despiked, self.plugin.PB_BASELINE_WINDOWS)
        self.assertNotAlmostEqual(self.module.bandMean(corrected, *SORET), self.levels[1][0], places=3)

    def testThePictureReconstructsTheDisplayedMetric(self):
        # ⭐ §6.1 — the two visible gaps ARE the two halves of the formula.
        numerator = self.levels[3][0] - self.levels[2][0]     # ③ Q bar  −  ④/② valley level
        denominator = self.levels[1][0] - self.levels[5][0]   # ① Soret bar  −  ⑤ zero
        self.assertAlmostEqual(self.plugin._DevSpectralPlugin__vTerms(self.despiked)[3],
                               100.0 * numerator / denominator, places=12)

    def testTheCrosshairArmSitsAtTheValleyBarsHeight(self):
        # Both arms true at once: ④'s height IS ②'s height, and its λ is where the curve attains it.
        self.assertAlmostEqual(self.levels[2][0], self.levels[4][0], places=12)
        crossing = self.view.markers[0][0]
        self.assertTrue(VALLEY[0] <= crossing <= VALLEY[1], crossing)

    def testTheZeroDatumIsActuallyZero(self):
        # ⚠ It is what the DENOMINATOR is measured from. A non-zero "zero" would silently rescale the
        # only visual statement the plot makes about A_Soret.
        self.assertEqual(0.0, self.levels[5][0])


if __name__ == "__main__":
    unittest.main()
