import numpy as np
import random
import numpy.typing
from PySide6.QtCharts import QChart
from PySide6.QtCharts import QChartView
from PySide6.QtCharts import QLineSeries

from PySide6.QtGui import QBrush
from PySide6.QtGui import QColor
from PySide6.QtGui import QPen

from model.spectral.SpectralJob import SpectralJob
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobGraphViewModuleParameters import SpectralJobGraphViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobGraphViewModulePolicyParameter import \
    SpectralJobGraphViewModulePolicyParameter


class SpectralJobGraphViewModule(QChartView):
    __moduleParameters: SpectralJobGraphViewModuleParameters
    allSpectraValues=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = QChart()
        self.chart.setBackgroundBrush(QBrush(QColor("transparent")))
        self.chart.setTitleBrush(QBrush(QColor("white")));
        self.setChart(self.chart)

    def updateGraph(self, spectralJob: SpectralJob):
        policy = self.getModuleParameters().getPolicy()
        if policy==SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA:

            spectra = spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
            spectrum = spectra[-1]

            valuesByNanometers = spectrum.valuesByNanometers
            series = QLineSeries()

            randomGray = random.randint(50, 200)
            pen = series.pen();
            pen.setWidth(1);
            pen.setBrush(QBrush(QColor.fromRgb(randomGray,randomGray,randomGray)))
            series.setPen(pen)



            for nanometer in valuesByNanometers:
                series.append(nanometer, valuesByNanometers[nanometer])
            self.chart.addSeries(series)


        elif policy == SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA_MEAN:
            spectra = spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
            spectrum = spectra[-1]

            if len(spectrum.valuesByNanometers)>0:

                values = list(spectrum.valuesByNanometers.values())
                keys = list(spectrum.valuesByNanometers.keys())

                if self.allSpectraValues is None:
                    lenValues = len(values)
                    self.allSpectraValues=np.empty([0, lenValues])
                else:
                    self.allSpectraValues=np.vstack((self.allSpectraValues, np.array(values)))

                if isinstance(self.allSpectraValues,numpy.ndarray) and self.allSpectraValues.size != 0:
                    meanSpectrumValues=np.mean(self.allSpectraValues,axis=0)

                    self.chart.removeAllSeries()
                    series = QLineSeries()

                    pen = series.pen();
                    pen.setWidth(2);
                    pen.setBrush(QBrush(QColor("#33663d")))
                    series.setPen(pen)

                    valuesByNanometers=dict(zip(keys,meanSpectrumValues.tolist()))
                    for nanometer in valuesByNanometers:
                        series.append(nanometer, valuesByNanometers[nanometer])
                    self.chart.addSeries(series)


                else:
                    print("skipped meanSpectrumValues")

    def setModuleParameters(self, moduleParameters: SpectralJobGraphViewModuleParameters):
        self.__moduleParameters = moduleParameters

    def getModuleParameters(self) -> SpectralJobGraphViewModuleParameters:
        return self.__moduleParameters
