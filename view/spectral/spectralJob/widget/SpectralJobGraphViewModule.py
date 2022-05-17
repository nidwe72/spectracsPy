from PyQt6.QtCharts import QChart
from PyQt6.QtCharts import QChartView
from PyQt6.QtCharts import QLineSeries

from model.spectral.SpectralJob import SpectralJob
from model.spectral.SpectrumSampleType import SpectrumSampleType


class SpectralJobGraphViewModule(QChartView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = QChart()
        self.setChart(self.chart)

    def updateGraph (self,spectralJob:SpectralJob):
        spectra=spectralJob.getSpectra(SpectrumSampleType.UNSPECIFIED)
        spectrum=spectra[-1]

        valuesByNanometers=spectrum.valuesByNanometers
        series = QLineSeries()
        for nanometer in valuesByNanometers:
            series.append(nanometer,valuesByNanometers[nanometer])
        self.chart.addSeries(series)
