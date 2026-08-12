"""SPEC_capture_quality.md §16.23.10h — the windowed low-DN guard.

The defect these lock down (§16.23.10a): the shipped statistic was `min(S)` over EVERY bin of the capture.
On this lamp that lands at ~417 nm — the blue cutoff — on every single capture, so the reported number was a
property of the LAMP, not the fill. It fired on all three `20260812_BillaClever` runs and pointed the wrong
way (it said "too concentrated" while `A_Q` said "too dilute").

⚠ These exercise `CapturePanel`'s guard maths WITHOUT constructing the widget: the panel needs a camera and
cannot run offscreen (§9.5). The three methods under test are pure functions of (view, spectrum), so they are
called unbound against a lightweight stand-in.
"""
import unittest

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.CaptureView import CaptureView
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.view.spectral.workflow.CapturePanel import CapturePanel


def _linearFromDn(digitalNumber):
    """Camera DN -> the LINEAR value the pipeline stores. §16.23.10b: the thresholds are ENCODED."""
    return 255.0 * (digitalNumber / 255.0) ** 2.2


def _spectrum(valuesByNm):
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(valuesByNm))
    return spectrum


# The name-mangled privates, resolved once so the tests read like the spec.
_reading = getattr(CapturePanel, "_CapturePanel__guardReading")
_verdict = getattr(CapturePanel, "_CapturePanel__guardVerdict")


class _Panel(object):
    """Minimal stand-in — the guard maths touches no widget state."""
    _CapturePanel__guardReading = _reading
    _CapturePanel__guardVerdict = _verdict

    def reading(self, view, spectrum):
        return _reading(self, view, spectrum)

    def verdict(self, view, digitalNumber):
        return _verdict(self, view, digitalNumber)


class DnGuardWindowTest(unittest.TestCase):

    def setUp(self):
        self.panel = _Panel()
        # A capture starved ONLY below 448 nm — the shape every BillaClever run had. Outside the dead blue the
        # fill is healthy (~54 DN, run 003's actual reading).
        self.starvedBelow448 = _spectrum(
            [(417.0, _linearFromDn(0.4)), (430.0, _linearFromDn(6.0)), (437.0, _linearFromDn(14.0))]
            + [(nm, _linearFromDn(54.3 + 0.5 * (nm - 448.0))) for nm in (448.0, 452.0, 456.0, 460.0)]
            + [(520.0, _linearFromDn(196.0)), (572.0, _linearFromDn(130.0))])
        self.view = CaptureView().setGuardBand(448.0, 460.0, targetDn=(20.0, 50.0),
                                               colors={"inside": "#2ECC71", "outside": "#E74C3C"})

    def test_the_window_excludes_the_lamps_dead_blue(self):
        # ⭐ The whole point. Unwindowed this returns ~0.4 DN at 417 nm; windowed it returns the in-band value.
        digitalNumber, nanometer = self.panel.reading(self.view, self.starvedBelow448)
        self.assertAlmostEqual(nanometer, 448.0, places=3,
                               msg="the minimum must land inside 448-460, not on the lamp's blue cutoff")
        self.assertAlmostEqual(digitalNumber, 54.3, places=1)

    def test_a_starved_blue_does_not_trip_the_floor(self):
        # §16.23.10a: every sub-16 DN bin lay below 448 nm and none of them reaches the metric.
        digitalNumber, _nanometer = self.panel.reading(self.view, self.starvedBelow448)
        self.assertGreater(digitalNumber, 16.0,
                           "bins below 448 nm are structurally starved on this lamp and must not be read")

    def test_no_declared_window_keeps_the_legacy_global_minimum(self):
        # RD8 / §16.23.10f: a plugin that declares nothing behaves exactly as before — including badly.
        digitalNumber, nanometer = self.panel.reading(CaptureView(), self.starvedBelow448)
        self.assertAlmostEqual(nanometer, 417.0, places=3)
        self.assertAlmostEqual(digitalNumber, 0.4, places=1)

    def test_the_measured_billaclever_readings(self):
        # §16.23.10h — the three runs, from the embedded workflow.json of 20260812_BillaClever/00{1,2,3}.pdf.
        # Stored as the LINEAR minima actually present in those blobs; the guard must encode them to these DN.
        for linearMinimum, expectedDn in [(5.27, 43.7), (7.65, 51.8), (8.50, 54.3)]:
            spectrum = _spectrum([(417.0, 0.0), (430.0, 0.2), (448.0, linearMinimum), (460.0, linearMinimum * 3)])
            digitalNumber, nanometer = self.panel.reading(self.view, spectrum)
            self.assertAlmostEqual(digitalNumber, expectedDn, places=1)
            self.assertAlmostEqual(nanometer, 448.0, places=3)

    def test_encoding_happens_exactly_once(self):
        # RD7: the plot axis is display DN and `addLevel` does NOT re-encode. A second encode here would make a
        # genuinely starved fill look healthy — the error that cost three passes to find (§16.23.10b).
        util = SpectralColorUtil()
        spectrum = _spectrum([(450.0, _linearFromDn(30.0))])
        digitalNumber, _nanometer = self.panel.reading(self.view, spectrum)
        self.assertAlmostEqual(digitalNumber, 30.0, places=3)
        self.assertNotAlmostEqual(digitalNumber, util.encodeGammaFraction(30.0 / 255.0), places=1)

    def test_an_empty_window_yields_no_reading_rather_than_a_wrong_one(self):
        view = CaptureView().setGuardBand(700.0, 720.0, targetDn=(20.0, 50.0))
        self.assertIsNone(self.panel.reading(view, self.starvedBelow448))

    def test_a_broken_spectrum_never_breaks_a_capture(self):
        self.assertIsNone(self.panel.reading(self.view, None))
        self.assertIsNone(self.panel.reading(self.view, _spectrum([])))


class DnGuardVerdictTest(unittest.TestCase):

    def setUp(self):
        self.panel = _Panel()
        self.view = CaptureView().setGuardBand(448.0, 460.0, targetDn=(20.0, 50.0))

    def test_the_colour_flips_exactly_at_the_declared_edges(self):
        # §16.23.10e — 20-50 is Edwin's working window. Inclusive at both edges.
        for digitalNumber, expected, inside in [(19.9, "too-concentrated", False),
                                                (20.0, "in-window", True),
                                                (39.9, "in-window", True),      # the 2 cap / 8 mL prediction
                                                (50.0, "in-window", True),
                                                (50.1, "too-dilute", False)]:
            verdict, isInside = self.panel.verdict(self.view, digitalNumber)
            self.assertEqual(verdict, expected, "at %.1f DN" % digitalNumber)
            self.assertEqual(isInside, inside, "at %.1f DN" % digitalNumber)

    def test_the_archive_evidence_behind_the_window(self):
        # §16.23.10e, the honest cost: `20260804A` is caught, and the correctly-dosed archive runs are NOT.
        for digitalNumber in (74.0, 83.8, 97.7):        # 20260804A — over-dilute per §16.24.7
            self.assertEqual(self.panel.verdict(self.view, digitalNumber)[0], "too-dilute")
        for digitalNumber in (54.4, 61.3, 66.6):        # archive runs whose A_Q is already correct
            self.assertEqual(self.panel.verdict(self.view, digitalNumber)[0], "too-dilute",
                             "recorded, not endorsed — §16.23.10e's 7-of-8 cost")

    def test_no_declared_target_yields_no_verdict(self):
        verdict, isInside = self.panel.verdict(CaptureView().setGuardBand(448.0, 460.0), 39.9)
        self.assertIsNone(verdict)
        self.assertTrue(isInside, "no rule declared => nothing to paint red")


if __name__ == "__main__":
    unittest.main()
