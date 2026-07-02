import pyqtgraph as pg

from sciens.spectracs.view.application.widgets.chart.ChartThemeUtil import ChartThemeUtil


class SpectrumPlotWidget(pg.PlotWidget):
    # Lightweight themed line plot of a Spectrum's {nm: value}. Reused by the wizard for the acquisition
    # capture preview and the processing absorption curve (SPEC_pumpkin_integration.md C.3/C.5).

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ChartThemeUtil.stylePlotWidget(self)

    def plotSpectrum(self, spectrum, title=None, color="y"):
        self.clear()
        if title is not None:
            self.getPlotItem().setTitle(title, color=ChartThemeUtil.titleColorName())
        if spectrum is None or not spectrum.valuesByNanometers:
            return
        nanometers = sorted(spectrum.valuesByNanometers.keys())
        values = [spectrum.valuesByNanometers[nanometer] for nanometer in nanometers]
        self.plot(nanometers, values, pen=pg.mkPen(color, width=2))
