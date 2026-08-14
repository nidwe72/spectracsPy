"""SPEC_v_metric_integration.md §7 — `levelCrossing`, the one core addition `V` needed.

The V tab's crosshair has to be true in BOTH arms at once: the horizontal at the valley band MEAN (the
number the metric divides) and the vertical at the λ where the curve actually attains it. Marking the
window's MINIMUM instead would sit on the curve but 23 % below that number — it renders fine and is
silently false (§6.2). This pins the contract that makes the honest version possible.

⚠ It lives here, not in the plugin suite, because `spectracs-plugins` carries NO numpy at all — which is
the whole reason this maths is in core rather than in the plugin (§1).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_level_crossing.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.feature.SpectrumFeatureLogicModule import SpectrumFeatureLogicModule
from sciens.spectracs.model.spectral.Spectrum import Spectrum


def _spectrum(pairs):
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(pairs))
    return spectrum


class LevelCrossingTest(unittest.TestCase):

    def setUp(self):
        self.module = SpectrumFeatureLogicModule()

    def testExactOnALinearRamp(self):
        # 500 nm -> 0.0 rising to 600 nm -> 1.0; the 0.25 level is at 525 nm, and the answer must be
        # INTERPOLATED, not snapped: the samples here are 10 nm apart and 525 is not one of them.
        ramp = _spectrum((500.0 + 10.0 * step, step / 10.0) for step in range(11))
        self.assertAlmostEqual(525.0, self.module.levelCrossing(ramp, 500.0, 600.0, 0.25), places=9)
        self.assertAlmostEqual(583.0, self.module.levelCrossing(ramp, 500.0, 600.0, 0.83), places=9)

    def testFirstOfSeveralCrossings(self):
        # ⚠ Eight of fifteen archived fills cross their own mean 3 or 5 times from noise wiggles (§6.2).
        # FIRST is the one deterministic choice, and this pins it: a sawtooth crossing 0.5 three times
        # must answer with the earliest.
        wobbly = _spectrum([(500.0, 0.0), (510.0, 1.0), (520.0, 0.0), (530.0, 1.0)])
        self.assertAlmostEqual(505.0, self.module.levelCrossing(wobbly, 500.0, 530.0, 0.5), places=9)

    def testASampleSittingExactlyOnTheLevel(self):
        ramp = _spectrum((500.0 + 10.0 * step, step / 10.0) for step in range(11))
        self.assertAlmostEqual(530.0, self.module.levelCrossing(ramp, 500.0, 600.0, 0.3), places=9)

    def testOutsideTheWindowsRangeIsNone(self):
        # ⛔ The one honest None: the curve is never at that level here.
        ramp = _spectrum((500.0 + 10.0 * step, step / 10.0) for step in range(11))
        self.assertIsNone(self.module.levelCrossing(ramp, 500.0, 600.0, 4.0))
        self.assertIsNone(self.module.levelCrossing(ramp, 500.0, 600.0, -1.0))

    def testTheWindowIsRespected(self):
        ramp = _spectrum((500.0 + 10.0 * step, step / 10.0) for step in range(11))
        # 0.25 lives at 525 nm, which is outside 560–600 — so within that window there is no crossing.
        self.assertIsNone(self.module.levelCrossing(ramp, 560.0, 600.0, 0.25))

    def testAFlatWindowAnswersInsteadOfReturningNone(self):
        # ⚠ A constant window's own mean can land a few ULPs OUTSIDE [min, max] (mean of 0.1 repeated is
        # 0.09999999999999998). That is arithmetic, not a missing crossing — and a caller drawing a
        # crosshair at a window's own mean must never get nothing back.
        flat = _spectrum((500.0 + step, 0.1) for step in range(61))
        mean = self.module.bandMean(flat, 500.0, 560.0)
        self.assertNotEqual(0.1, mean)                       # the rounding is real
        self.assertIsNotNone(self.module.levelCrossing(flat, 500.0, 560.0, mean))

    def testTooFewPointsIsNone(self):
        self.assertIsNone(self.module.levelCrossing(_spectrum([(500.0, 0.1)]), 500.0, 560.0, 0.1))


class ValleyCrosshairTest(unittest.TestCase):
    """T4 — the property the crosshair rests on, on a curve shaped like the real thing."""

    def setUp(self):
        self.module = SpectrumFeatureLogicModule()
        # The archive's shape through the valley: a minimum near the window's LEFT edge (~509 nm) rising
        # monotonically toward the Q band — which is why A_valley is a slope average, 23 % above the
        # minimum, and why the crosshair may not be drawn at the minimum (§6.2).
        values = {}
        nm = 440.0
        while nm <= 630.0:
            key = round(nm, 2)
            values[key] = 0.030 + 0.000045 * (key - 509.0) ** 2
            nm += 0.2
        self.spectrum = _spectrum(values.items())

    def testTheCrossingIsInsideTheWindowAndOnTheLevel(self):
        valley = self.module.bandMean(self.spectrum, 500.0, 560.0)
        crossing = self.module.levelCrossing(self.spectrum, 500.0, 560.0, valley)
        self.assertIsNotNone(crossing)
        self.assertTrue(500.0 <= crossing <= 560.0, crossing)
        # The curve AT the crossing equals the level the horizontal arm is drawn at — the property that
        # makes both arms of the cross true statements at the same time.
        nearest = min(self.spectrum.valuesByNanometers.items(),
                      key=lambda pair: abs(pair[0] - crossing))
        self.assertAlmostEqual(valley, nearest[1], places=3)

    def testTheMinimumIsNotTheAnswer(self):
        # ⛔ The whole point of §6.2: the minimum sits at the left edge and is well BELOW the mean, so a
        # cross drawn there would be off the number the metric divides.
        valley = self.module.bandMean(self.spectrum, 500.0, 560.0)
        inWindow = [(nm, v) for nm, v in self.spectrum.valuesByNanometers.items() if 500.0 <= nm <= 560.0]
        minimumNm, minimumValue = min(inWindow, key=lambda pair: pair[1])
        self.assertLess(minimumValue, valley)
        self.assertLess(minimumNm, 515.0)                     # pinned at the left edge
        self.assertNotAlmostEqual(minimumNm,
                                  self.module.levelCrossing(self.spectrum, 500.0, 560.0, valley), places=0)


if __name__ == "__main__":
    unittest.main()
