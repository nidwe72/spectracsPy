import pyqtgraph as pg

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

    def plotSpectrum(self, spectrum, title=None, color="y", clear=True, width=2):
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
        self.plot(nanometers, values, pen=pg.mkPen(color, width=width))

    def addTrace(self, spectrum, color="y", width=2):
        # Overlay one more curve without clearing the plot.
        self.plotSpectrum(spectrum, title=None, color=color, clear=False, width=width)
