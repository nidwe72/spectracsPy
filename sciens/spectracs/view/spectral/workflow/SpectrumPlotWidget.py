import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy

from sciens.spectracs.view.application.widgets.chart.ChartThemeUtil import ChartThemeUtil


class SpectrumPlotWidget(pg.PlotWidget):
    # Lightweight themed line plot of a Spectrum's {nm: value}. Reused by the wizard for the acquisition
    # capture preview and the processing absorption curve (SPEC_pumpkin_integration.md C.3/C.5).

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ChartThemeUtil.stylePlotWidget(self)
        # Responsive: shrink to fit narrow / phone-width panels (SPEC_dev_measure_bench.md §18/H1) — a modest
        # floor (NOT 0) keeps the plot usable and prevents total collapse in a horizontal layout.
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # SPEC_soret_448_trim.md §12.2 — the view-model's `style` names, mapped to Qt pen styles. A dashed curve
    # is what lets the FITTED BASELINE read as construction rather than as one more measured curve.
    __PEN_STYLES = {"dashed": Qt.PenStyle.DashLine, "dotted": Qt.PenStyle.DotLine}

    def plotSpectrum(self, spectrum, title=None, color="y", clear=True, width=2, style=None):
        # clear=False overlays onto the existing curves (used for gray per-frame traces + a green mean,
        # and for the reference/sample overlay — SPEC_dev_measure_bench.md N3).
        if clear:
            self.clear()
        if title is not None:
            self.getPlotItem().setTitle(title, color=ChartThemeUtil.titleColorName())
        if spectrum is None or not spectrum.valuesByNanometers:
            return
        nanometers = sorted(spectrum.valuesByNanometers.keys())
        values = [spectrum.valuesByNanometers[nanometer] for nanometer in nanometers]
        self.plot(nanometers, values, pen=self.pen(color, width, style))

    def addTrace(self, spectrum, color="y", width=2, style=None):
        # Overlay one more curve without clearing the plot.
        self.plotSpectrum(spectrum, title=None, color=color, clear=False, width=width, style=style)

    @classmethod
    def pen(cls, color="y", width=2, style=None):
        # One place that turns (color, width, style) into a pen — the plot lines, the guide levels and the
        # band bars all go through it, so a style name means the same thing everywhere.
        penStyle = cls.__PEN_STYLES.get(style)
        if penStyle is None:
            return pg.mkPen(color, width=width)
        return pg.mkPen(color, width=width, style=penStyle)
