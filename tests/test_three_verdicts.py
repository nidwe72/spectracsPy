"""The three-verdict EVALUATION of the DEV plugin (SPEC_capture_quality.md §16.20, Edwin 2026-08-03).

The plugin shows the pigment index three ways, in decreasing order of correction:

    1  620-630 baseline + pedestal   RoastPedestalGaugeView   T = 6.8
    2  620-630 baseline              RoastFar620GaugeView     T = 8.3
    3  raw Soret/Q                   a VALUE ROW, no gauge    (no threshold exists)

Each adjacent pair isolates exactly one change.

⚠ 2026-08-14: a FOURTH gauge, `RoastQPercentGaugeView`, now heads the tab — and it is NOT a rung of this
ladder (SPEC_v_metric_integration.md §5). The rungs differ from each other by how much CORRECTION was
applied, which is what makes the isolate-one-change property true; `Q%` is a different metric on a
different construction (raw curve, no chord, and a different Q window). The tests below therefore assert
against `__ladder()` — the two rungs — and separately assert that nothing has slotted between them. What is asserted here is the STRUCTURE (which items appear,
in what order, and which of them carries a verdict) plus the two regression guards that the implementation
rubber-duck identified as the ways this change could go wrong silently.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_three_verdicts.py -q
"""
import unittest

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.plugins.dev.RoastPedestalGaugeView import RoastPedestalGaugeView
from sciens.spectracs.plugins.dev.RoastFar620GaugeView import RoastFar620GaugeView


def _spectrum(soretHeight, qHeight, pedestal=0.05):
    # Same crude two-band stand-in as test_linear_baseline_metric: a Soret bump at 450 and a weaker Q bump at
    # 570 on a flat pedestal. Heights are the knobs the tests turn to move the ratio across a threshold.
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {
        float(nm): pedestal
        + soretHeight * 2.718 ** (-((float(nm) - 450.0) ** 2) / 200.0)
        + qHeight * 2.718 ** (-((float(nm) - 570.0) ** 2) / 200.0)
        for nm in range(440, 631, 2)}
    return spectrum


class ThreeVerdictsTest(unittest.TestCase):

    def setUp(self):
        self.plugin = DevSpectralPlugin()

    def __evaluate(self, spectrum):
        return self.plugin._DevSpectralPlugin__newEvaluationResult(spectrum, None, None)

    @staticmethod
    def __gauges(result):
        return [item for item in result.getItems() if type(item).__name__.startswith("Roast")]

    @staticmethod
    def __ladder(result):
        # §16.20's two rungs only. `Q%` is excluded deliberately: it is a different metric on a different
        # construction, it runs on its own scale, and its Q band is a DIFFERENT WINDOW (565-580, not
        # 560-580) — so "a taller Q drives it the same way" is not a claim that transfers.
        return [item for item in result.getItems()
                if type(item).__name__ in ("RoastPedestalGaugeView", "RoastFar620GaugeView")]

    @staticmethod
    def __rowLabels(result):
        return [item.label for item in result.getItems()
                if type(item).__name__ == "MetricFieldView" and item.label]

    # ---------------------------------------------------------------- structure

    def test_the_ladder_pair_stays_adjacent_below_the_q_percent_gauge(self):
        # ⚠ CHANGED 2026-08-14 (SPEC_v_metric_integration.md §5). A THIRD gauge now heads this tab — but
        # `Q%` is NOT a new rung of §16.20's ladder. The rungs differ by HOW MUCH CORRECTION was applied,
        # which is what makes "each adjacent pair isolates exactly one change" true; `Q%` is a different
        # metric on a different construction (raw curve, no chord at all).
        # ⇒ what must be asserted is that the LADDER'S OWN PAIR is still adjacent and still in order. If
        # something ever slots between them, that property dies quietly and this is what notices.
        gauges = self.__gauges(self.__evaluate(_spectrum(0.30, 0.08)))
        self.assertEqual([type(g).__name__ for g in gauges],
                         ["RoastQPercentGaugeView", "RoastPedestalGaugeView", "RoastFar620GaugeView"])

    def test_the_ladder_gauges_are_captioned_plainly(self):
        # Edwin 2026-08-03: the wavelengths are dropped from the visible label — the tooltips still name the
        # window, and the screen should read as a verdict, not as a specification. The earlier hedge (window
        # in the caption, so a historical "Verdict · linear baseline" could never be confused with the new
        # one) is moot now that every archived report has been regenerated and no longer carries that string.
        gauges = self.__ladder(self.__evaluate(_spectrum(0.30, 0.08)))
        self.assertEqual(gauges[0].caption, "Verdict · baseline + pedestal")
        self.assertEqual(gauges[1].caption, "Verdict · baseline")

    def test_the_raw_ratio_is_a_value_row_and_carries_NO_verdict(self):
        # §16.20 — the raw Soret/Q cannot separate the classes on post-rebuild data (Cohen's d 1.20; the
        # classes overlap outright), so it is shown as a number and deliberately given no gauge. A pill here
        # would be a guess wearing a verdict's clothes.
        result = self.__evaluate(_spectrum(0.30, 0.08))
        raw = [label for label in self.__rowLabels(result) if "raw Soret/Q" in label]
        self.assertEqual(len(raw), 1)
        self.assertIn("no verdict", raw[0])
        for gauge in self.__gauges(result):
            self.assertNotIn("raw", gauge.caption)

    def test_the_metric_rows_use_the_same_anchor_as_the_verdicts(self):
        # A tab that shows a verdict computed one way and its supporting band means computed another is a
        # reading trap. Both rows must name 620-630, and neither may still say 600-630.
        labels = self.__rowLabels(self.__evaluate(_spectrum(0.30, 0.08)))
        self.assertIn("Soret · baseline", labels)
        self.assertIn("Q · baseline", labels)
        self.assertFalse([label for label in labels if "linear baseline" in label])

    # ---------------------------------------------------------------- classification

    def test_each_gauge_flips_its_verdict_across_its_own_threshold(self):
        # Reads each gauge's OWN line rather than repeating it — the thresholds are re-derived whenever the
        # metric's window moves (they did on 2026-08-10, SPEC_soret_448_trim.md §5), and a copy here would
        # fail for the wrong reason every time. The values themselves are pinned in the test below.
        for view in (RoastPedestalGaugeView, RoastFar620GaugeView):
            threshold = view._THRESHOLDS[0]
            self.assertEqual(view(threshold + 1.0, render=0).verdictLabel, "good — green")
            self.assertEqual(view(threshold - 1.0, render=0).verdictLabel, "probably too brown")

    def test_the_thresholds_are_the_ones_derived_on_the_trimmed_soret_window(self):
        # SPEC_soret_448_trim.md §5 / `diagnostics/soret_448_thresholds.py`: corridor midpoints on §16.20.4's
        # own corpus (Steirerkraft B+C vs S-Budget D) with the 448-460 numerator.
        #   pedestal  green 8.369 +/- 0.352, brown 5.593 +/- 0.129, corridor 5.748 .. 7.831  -> T 6.8
        #   far620    green 10.560 +/- 0.453, brown 6.615 +/- 0.151, corridor 6.796 .. 9.895 -> T 8.3
        # ⛔ Changing either number without re-running that script is how a threshold loses its provenance.
        self.assertEqual(RoastPedestalGaugeView._THRESHOLDS, [6.8])
        self.assertEqual(RoastFar620GaugeView._THRESHOLDS, [8.3])
        # The gradient must keep the threshold inside its band, or the marker rides off the scale.
        for view in (RoastPedestalGaugeView, RoastFar620GaugeView):
            self.assertGreater(view._BAND_LEFT, view._THRESHOLDS[0])
            self.assertLess(view._BAND_RIGHT, view._THRESHOLDS[0])

    def test_a_taller_q_band_drives_both_gauges_down(self):
        # The Q band is the denominator: a taller Q means a smaller index. Driving the evaluation end to end
        # proves the WIRING — that each gauge is fed the ratio it claims to show.
        #
        # ⚠ Deliberately asserts DIRECTION, not verdict labels. The synthetic two-band stand-in above is not
        # calibrated to the instrument's scale (it tops out around 7 where a real green oil reads 12-16), so
        # asserting "good — green" off it would be asserting an artefact of the stand-in. The thresholds are
        # exercised directly against the gauge classes in the test above, where the numbers are real.
        weak = self.__ladder(self.__evaluate(_spectrum(0.30, 0.055)))
        strong = self.__ladder(self.__evaluate(_spectrum(0.30, 0.130)))
        for weaker, stronger in zip(weak, strong):
            self.assertGreater(weaker.value, stronger.value)

    def test_the_pedestal_gauge_reads_lower_than_the_uncorrected_one(self):
        # r_Q is negative, so putting it back ENLARGES the denominator and the corrected index must come out
        # below the plain one. If this ever inverts, the sign of PB_R_Q has been flipped.
        pedestal, far620 = self.__ladder(self.__evaluate(_spectrum(0.30, 0.08)))
        self.assertLess(pedestal.value, far620.value)

    # ---------------------------------------------------------------- regression guards (the rubber duck)

    def test_both_anchors_are_pinned_and_the_names_say_which_ships(self):
        # ⛔ RD#1, restated after the 2026-08-03 tidy-up. The SHIPPED anchor now owns the plain name and the
        # superseded one carries its window in its name, so no reader has to remember which is which.
        #
        # Both are pinned because both are load-bearing. PB_BASELINE_WINDOWS drives all three verdicts;
        # PB_BASELINE_WINDOWS_LEGACY_600 is what settling_sweep's `... linear` keys are computed from, and
        # those keys ARE the reference every comparison table in SPEC_capture_quality §16 is built on —
        # repointing them would silently redefine every historical number in the spec.
        self.assertEqual(self.plugin.PB_BASELINE_WINDOWS, ((520.0, 540.0), (620.0, 630.0)))
        self.assertEqual(self.plugin.PB_BASELINE_WINDOWS_LEGACY_600, ((520.0, 540.0), (600.0, 630.0)))
        # The residual belongs to the anchor it was fitted on (§16.20.2); pairing 620-630 bands with the
        # 600-630 anchor's -0.0246 would be a category error, so the shipped value is pinned too.
        self.assertEqual(self.plugin.PB_R_Q, -0.0184)

    def test_the_new_window_is_declared_so_the_capture_clamp_is_asserted_against_it(self):
        # RD#2. 630 nm is exactly WAVELENGTH_MAX_NM, so the anchor sits hard against the capture edge; the
        # assertion must actually see it, or a future narrowing of the ROI starves it silently.
        self.assertIn((620.0, 630.0), self.plugin.declaredEvalBands())
        self.plugin._DevSpectralPlugin__assertWindowCoversBands()

    def test_the_publish_badge_does_not_use_the_metric_that_cannot_classify(self):
        # RD#3 / §16.20 — the LIMS publish step is the ONE screen an end user sees. It used to carry a verdict
        # driven by the raw Soret/Q on T = 4.4, a threshold sitting BELOW the entire brown class, so it read
        # "good — green" for brown oil. The badge must now come from the primary metric.
        import inspect
        source = inspect.getsource(DevSpectralPlugin.publishing)
        self.assertIn("RoastPedestalGaugeView", source)
        self.assertNotIn("RoastGaugeView(", source)


if __name__ == "__main__":
    unittest.main()
