from PyQt6.QtCharts import QChart
from PyQt6.QtCharts import QChartView
from PyQt6.QtCharts import QLineSeries

from model.spectral.SpectralJob import SpectralJob
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobGraphViewModuleParameters import SpectralJobGraphViewModuleParameters



class SpectralJobGraphViewModule(QChartView):
    __moduleParameters:SpectralJobGraphViewModuleParameters

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = QChart()
        self.setChart(self.chart)

    def updateGraph (self,spectralJob:SpectralJob):
        spectra=spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
        spectrum=spectra[-1]

        valuesByNanometers=spectrum.valuesByNanometers
        series = QLineSeries()
        for nanometer in valuesByNanometers:
            series.append(nanometer,valuesByNanometers[nanometer])
        self.chart.addSeries(series)

    def setModuleParameters(self,moduleParameters:SpectralJobGraphViewModuleParameters):
        self.__moduleParameters=moduleParameters

    def getModuleParameters(self)->SpectralJobGraphViewModuleParameters:
        return self.__moduleParameters

