"""A plot with annotations must HOLD STILL — the regression Edwin caught by eye (2026-08-10).

`Absorption (bands)` animated itself: the y-axis grew ~4.7 % per event-loop tick, without bound, so the curve
appeared to shrink. Cause: a band/marker caption is a TextItem with a FIXED PIXEL size, parked at the top of
the view and moved on every sigYRangeChanged. Added with pyqtgraph's default `ignoreBounds=False` it protrudes
above the range, auto-range expands to enclose it, the signal fires, the caption moves to the new top, and it
protrudes again. A closed loop with no damping.

⇒ Annotations (captions, band shading) must NEVER drive auto-range. ⚠ Guide LINES deliberately still do — that
is what makes a 60 DN guard visible when a fill peaks below it — and they cannot feed back, because they do
not move. Both properties are asserted here.
"""
import unittest

from PySide6.QtWidgets import QApplication

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer

TICKS = 12


def _spectrum(scale=1.0):
    values = {}
    for step in range(0, 200):
        nm = 440.0 + step
        values[nm] = scale * (0.05 + 2.0 * 2.718 ** (-((nm - 452.0) ** 2) / 200.0))
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(values)
    return spectrum


class PlotAnnotationsDoNotRescaleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def __ySpans(self, view):
        widget = QtWorkflowRenderer().render([view])
        widget.resize(900, 520)
        widget.show()
        viewBox = widget.findChild(SpectrumPlotWidget).getPlotItem().vb
        spans = []
        for _ in range(TICKS):
            self.app.processEvents()
            low, high = viewBox.viewRange()[1]
            spans.append(high - low)
        return spans

    def test_band_and_marker_captions_do_not_grow_the_axis(self):
        # The exact shape that ran away: four labelled bands, four mean bars, a labelled marker.
        view = (SpectrumPlotView(_spectrum(), "A(λ)")
                .addBand(448.0, 460.0, "S")
                .addBand(520.0, 540.0, "near anchor", "#5a6a7a55")
                .addBand(560.0, 580.0, "Q")
                .addBand(620.0, 630.0, "far anchor", "#5a6a7a55")
                .addLevel(0.8, 448.0, 460.0)
                .addLevel(0.2, 560.0, 580.0)
                .addMarker(572.0, "Q"))
        spans = self.__ySpans(view)
        self.assertAlmostEqual(spans[0], spans[-1], places=6,
                               msg="the y-range drifted %.3f -> %.3f over %d ticks — the caption/auto-range "
                                   "feedback loop is back" % (spans[0], spans[-1], TICKS))

    def test_a_labelled_bar_caption_does_not_grow_the_axis_either(self):
        view = SpectrumPlotView(_spectrum(), "A(λ)").addLevel(0.8, 448.0, 460.0, label="S̄")
        spans = self.__ySpans(view)
        self.assertAlmostEqual(spans[0], spans[-1], places=6)

    def test_a_guide_line_still_pulls_the_range_open(self):
        # ⚠ The other half of the rule: a DN guard above the data must stay visible. The plot settles (no
        # runaway) AND the range reaches the guard.
        view = (SpectrumPlotView(_spectrum(scale=0.01), "DN", axis=None)
                .addLevel(60.0, label="60 DN — too dilute", style="dashed"))
        spans = self.__ySpans(view)
        self.assertAlmostEqual(spans[0], spans[-1], places=6, msg="a guide line must not oscillate either")
        self.assertGreaterEqual(spans[-1], 59.0, "the guide must be inside the visible range")


if __name__ == "__main__":
    unittest.main()
