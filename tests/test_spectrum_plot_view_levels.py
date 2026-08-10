"""SpectrumPlotView's new primitives and their BACK-COMPAT — SPEC_soret_448_trim.md §12.2 / §18 duck #9.

`addLevel` carries the band-mean bars and the DN guard lines; `addTrace(style=)` carries the dashed fitted
baseline. Both are additive, and both must survive the round trip through a DbMeasurement blob.

⚠ The load-bearing case is the OLD blob: every saved run written before 2026-08-10 has no "levels" key and no
trace "style", and 3-element bands. It must still load, and the renderers must still be able to index its
bands positionally — which is why fromJson pads rather than leaving ragged tuples.
"""
import unittest

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView


def _spectrum():
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({440.0: 0.5, 500.0: 0.4, 600.0: 0.3})
    return spectrum


class SpectrumPlotViewLevelsTest(unittest.TestCase):

    def test_a_level_is_a_guide_line_without_a_range_and_a_bar_with_one(self):
        view = (SpectrumPlotView(_spectrum(), "t")
                .addLevel(16.0, label="16 DN", color="#c87a3c", style="dashed")
                .addLevel(0.87, 448.0, 460.0, label="S̄"))
        guide, bar = view.levels
        self.assertEqual((guide[0], guide[1], guide[2]), (16.0, None, None))
        self.assertEqual((bar[0], bar[1], bar[2]), (0.87, 448.0, 460.0))

    def test_levels_bands_and_trace_styles_round_trip(self):
        view = (SpectrumPlotView(_spectrum(), "t")
                .addTrace(_spectrum(), "baseline", "#b06000", style="dashed")
                .addBand(448.0, 460.0, "S", "#5a6a7a55")
                .addLevel(60.0, label="60 DN")
                .addLevel(0.19, 560.0, 580.0))
        restored = SpectrumPlotView.fromJson(view.toJson())
        self.assertEqual(restored.levels, view.levels)
        self.assertEqual(restored.bands, view.bands)
        self.assertEqual(restored.allTraces()[1][3], "dashed")
        self.assertEqual(restored.allTraces()[1][2], "#b06000")

    def test_a_pre_change_blob_still_loads_and_is_padded_for_the_renderers(self):
        # Exactly the shape a DbMeasurement written before 2026-08-10 carries: 3-element bands, no "levels",
        # no trace "style".
        legacy = {"type": "plot", "title": "A(λ)", "spectrum": _spectrum().toJson(),
                  "traces": [{"values": _spectrum().toJson(), "label": "A raw", "color": "#888888"}],
                  "bands": [[440.0, 460.0, "Soret"]], "markers": [[575.0, "Q"]],
                  "axis": None, "isShownInReport": True}
        view = SpectrumPlotView.fromJson(legacy)
        self.assertEqual(view.levels, [])
        self.assertEqual(view.bands, [(440.0, 460.0, "Soret", None)])   # padded to today's arity
        self.assertEqual(view.allTraces()[1], (view.traces[0][0], "A raw", "#888888", None))
        self.assertTrue(view.isShownInReport)

    def test_legend_rows_are_derived_numbered_bars_first_then_curves(self):
        # SPEC_soret_448_trim.md §25.2 — the rows are DERIVED, never a parallel list: a badge and its legend
        # row must be the same fact, or they drift the first time someone renumbers.
        # ⚠ Numbers are DECLARED, and Edwin's order is NOT wavelength order (1 Soret, 2 Q, 3 red anchor at
        # 625, 4 quiet anchor at 530) — asserted here, because auto-numbering by position would sort them
        # 1,4,2,3 and destroy the grouping.
        view = (SpectrumPlotView(title="t")
                .addTrace(_spectrum(), "A(λ) despiked", "#e8e337")
                .addTrace(_spectrum(), "A(λ) − baseline", "#35d3d3")
                .addLevel(0.77, 448.0, 460.0, label="Soret band mean", color="#35d3d3", number=1)
                .addLevel(0.20, 620.0, 630.0, label="red-anchor mean", color="#c9a227", number=3)
                .addLevel(0.07, 560.0, 580.0, label="Q-band mean", color="#35d3d3", number=2)
                .addLevel(16.0, label="a guide line with no number"))
        rows = view.legendRows()
        self.assertEqual([row[0] for row in rows], [1, 2, 3, None, None])
        self.assertEqual([row[1] for row in rows[:3]],
                         ["Soret band mean", "Q-band mean", "red-anchor mean"])
        self.assertEqual([row[1] for row in rows[3:]], ["A(λ) despiked", "A(λ) − baseline"])
        self.assertEqual(rows[3][2], "#e8e337", "a curve is named by its own colour")

    def test_the_legend_declaration_round_trips_and_defaults_to_absent(self):
        from sciens.spectracs.model.spectral.plugin.view.LegendPosition import LegendPosition
        view = (SpectrumPlotView(title="t").setLegend(LegendPosition.NORTH_EAST, padding=34.0)
                .addLevel(0.5, 448.0, 460.0, label="S", color="#35d3d3", number=1))
        restored = SpectrumPlotView.fromJson(view.toJson())
        self.assertEqual(restored.legendPosition, LegendPosition.NORTH_EAST)
        self.assertEqual(restored.legendPadding, 34.0)
        self.assertEqual(restored.levels[0][6], 1, "the number survives the round trip")
        self.assertIsNone(SpectrumPlotView(title="t").legendPosition, "no legend unless declared")

    def test_the_padding_signs_always_point_into_the_plot(self):
        # ⛔ The trap of §23.2: a plugin supplying a SIGNED offset would push its legend off-screen the moment
        # the corner changed. The magnitude is the plugin's, the signs are the enum's.
        from sciens.spectracs.model.spectral.plugin.view.LegendPosition import LegendPosition
        self.assertEqual(LegendPosition.NORTH_EAST.paddingSigns(), (-1.0, 1.0))
        self.assertEqual(LegendPosition.SOUTH_WEST.paddingSigns(), (1.0, -1.0))
        self.assertEqual(LegendPosition.NORTH_WEST.corner(), (0.0, 0.0))
        self.assertEqual(LegendPosition.SOUTH_EAST.corner(), (1.0, 1.0))

    def test_all_traces_pads_a_hand_built_three_tuple(self):
        # A caller that appends to `traces` directly (or an older in-memory view) must not break the renderers.
        view = SpectrumPlotView(title="t")
        view.traces.append((_spectrum(), "legacy", "c"))
        self.assertEqual(view.allTraces()[0][3], None)


if __name__ == "__main__":
    unittest.main()
