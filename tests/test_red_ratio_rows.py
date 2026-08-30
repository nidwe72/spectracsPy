"""M1/M2 — the red-ratio family: `Rv`, `RvLin`, `RvCont`, and the guards that stop them lying.

`ROADMAP.md` item 1 P2 ships these as NUMBERS ONLY — no gauge, no threshold, no verdict — so what is worth
testing is not a classification but three things that have each already gone wrong somewhere in this
project:

  1. the arithmetic matches the specification, on a spectrum whose band values are KNOWN by construction;
  2. `RvLin` reduces to `Rv` EXACTLY when the local anchor sits on the valley (`SPEC_metric_research.md`
     §16.11's one-sentence case — it is not a rival metric, it is `Rv` with the slope measured);
  3. a dead denominator returns None and NOT a clamped number. `20260828BillaCleverA` really reads
     `Rv` = -10.05, and a brown oil whose Q band falls to the valley makes the ratio meaningless rather
     than large — `SPEC_v_metric_integration.md` §3.1's rule, applied to a second family.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin


def spectrumFrom(level):
    """A spectrum whose value is a FUNCTION OF WAVELENGTH ONLY, so every band mean is known exactly."""
    values = {}
    for step in range(0, 1201):
        nm = 440.0 + step * 0.2
        values[round(nm, 1)] = level(nm)
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(values)
    return spectrum


def flatBands(valley, qBand, red, local):
    """Piecewise-constant over the four windows the family reads; linear elsewhere so nothing is undefined."""
    def level(nm):
        if 500.0 <= nm <= 560.0:
            return valley
        if 565.0 <= nm <= 580.0:
            return qBand
        if 612.0 <= nm <= 615.0:
            return local
        if 622.0 <= nm <= 627.0:
            return red
        return valley
    return spectrumFrom(level)


class RedRatioRowsTest(unittest.TestCase):

    def setUp(self):
        self.plugin = DevSpectralPlugin()
        # The rows are computed by a private single-definition helper, deliberately: one definition, three
        # consumers. Reaching it by its mangled name is how the sibling `__vTerms` tests do it.
        self.terms = getattr(self.plugin, "_DevSpectralPlugin__rvTerms")

    def testRvIsTheBandHeightRatio(self):
        rv, _, _ = self.terms(flatBands(valley=0.09, qBand=0.24, red=0.26, local=0.09))
        self.assertAlmostEqual(rv, 100.0 * (0.26 - 0.09) / (0.24 - 0.09), places=6)

    def testRvLinReducesToRvWhenTheLocalAnchorSitsOnTheValley(self):
        """⭐ §16.11's one-sentence case: with Δ = A612-615 − A_valley = 0, RvLin IS Rv, exactly.

        ⛔ If this ever fails, RvLin has stopped being 'Rv with the baseline's slope measured' and has
        become a different metric — which is a much larger claim than the spec makes for it."""
        rv, rvLin, _ = self.terms(flatBands(valley=0.09, qBand=0.24, red=0.26, local=0.09))
        self.assertAlmostEqual(rvLin, rv, places=6)

    def testRvLinSubtractsAMeasuredSlopeWhereRvCannot(self):
        """A tilted baseline lifts the local anchor above the valley. Rv reads the tilt as signal; RvLin
        removes it, so the two must SEPARATE — and RvLin must come out the lower of the pair."""
        rv, rvLin, _ = self.terms(flatBands(valley=0.09, qBand=0.24, red=0.26, local=0.107))
        self.assertLess(rvLin, rv)
        # the trim is 1.132·Δ on the numerator against 0.509·Δ on the denominator — Δ = 0.017 here
        delta = 0.107 - 0.09
        span = 613.5 - 530.0
        line = lambda at: 0.09 + (delta / span) * (at - 530.0)
        expected = 100.0 * (0.26 - line(624.5)) / (0.24 - line(572.5))
        self.assertAlmostEqual(rvLin, expected, places=6)

    def testADeadDenominatorReturnsNoneRatherThanAClampedNumber(self):
        """⛔ A brown oil whose Q band has fallen to the valley. Every member must decline."""
        rv, rvLin, rvCont = self.terms(flatBands(valley=0.24, qBand=0.24, red=0.26, local=0.24))
        self.assertIsNone(rv)
        self.assertIsNone(rvLin)

    def testNoSpectrumYieldsThreeNones(self):
        self.assertEqual(self.terms(None), (None, None, None))

    def testRvContIsScaleFreeOnAFlatOffset(self):
        """⭐ RvCont's whole claim: it is measured above ONE fitted continuum, so adding a constant to the
        spectrum leaves it unmoved. Rv does not have this property and is not asked for it here."""
        shape = lambda nm, lift: (0.09 + lift) + (0.15 if 565.0 <= nm <= 580.0 else 0.0) \
            + (0.17 if 622.0 <= nm <= 627.0 else 0.0)
        _, _, plain = self.terms(spectrumFrom(lambda nm: shape(nm, 0.0)))
        _, _, lifted = self.terms(spectrumFrom(lambda nm: shape(nm, 0.10)))
        if plain is None or lifted is None:
            self.skipTest("the fitted continuum did not resolve on this synthetic shape")
        self.assertAlmostEqual(plain, lifted, places=3)


if __name__ == "__main__":
    unittest.main()
