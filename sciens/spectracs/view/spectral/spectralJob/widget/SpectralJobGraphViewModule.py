import random
from collections import deque

import numpy as np
import pyqtgraph as pg

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.spectral.SpectralJob import SpectralJob
from sciens.spectracs.view.application.widgets.chart.ChartThemeUtil import ChartThemeUtil
from sciens.spectracs.view.spectral.spectralJob.widget.SpectralJobGraphViewModuleParameters import SpectralJobGraphViewModuleParameters
from sciens.spectracs.view.spectral.spectralJob.widget.SpectralJobGraphViewModulePolicyParameter import \
    SpectralJobGraphViewModulePolicyParameter

# Bounded overlay: keep at most this many spectrum curves in PLOT_SPECTRA mode
# (spec decision D3). High enough to look identical to the old unbounded
# overlay for any realistic burst, while killing the unbounded-growth creep.
MAX_SPECTRA_CURVES = 200


class SpectralJobGraphViewModule(pg.PlotWidget):
    __moduleParameters: SpectralJobGraphViewModuleParameters
    allSpectraValues = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ChartThemeUtil.stylePlotWidget(self)

        # Ring buffer of the overlaid raw-spectrum curves (PLOT_SPECTRA), and the
        # single persistent mean curve (PLOT_SPECTRA_MEAN).
        self.__spectraCurves = deque()
        self.__meanCurve = None

        # Axes are frozen to the first spectrum for parity with the old chart
        # (spec D4) - set once, then never rescaled.
        self.__axesInitialized = False

    def setTitle(self, title):
        # Caller sets the chart title via this widget; keep the white title brush
        # the QtCharts chart used (was chart.setTitle + setTitleBrush).
        # PlotWidget proxies to PlotItem via __getattr__, so call it explicitly.
        self.getPlotItem().setTitle(title, color=ChartThemeUtil.titleColorName())

    def clearGraph(self):
        for curve in self.__spectraCurves:
            self.removeItem(curve)
        self.__spectraCurves.clear()

        if self.__meanCurve is not None:
            self.removeItem(self.__meanCurve)
            self.__meanCurve = None

        self.allSpectraValues = None
        self.__axesInitialized = False

    def updateAxes(self, spectralJob: SpectralJob):
        # Freeze the axes to the first captured spectrum (parity, spec D4).
        if self.__axesInitialized:
            return

        spectra = spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
        spectrum = spectra[-1]

        nanometers = list(spectrum.valuesByNanometers.keys())
        intensities = list(spectrum.valuesByNanometers.values())

        if len(nanometers) == 0:
            return

        self.setXRange(min(nanometers), max(nanometers), padding=0)
        self.setYRange(min(intensities), max(intensities), padding=0)

        self.getPlotItem().setLabel('bottom', 'wavelength (nm)')
        self.getPlotItem().setLabel('left', 'intensity (a.u.)')

        self.__axesInitialized = True

    def updateGraph(self, spectralJob: SpectralJob):
        policy = self.getModuleParameters().getPolicy()
        if policy == SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA:

            spectra = spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
            spectrum = spectra[-1]

            valuesByNanometers = spectrum.valuesByNanometers

            nanometers = list(valuesByNanometers.keys())
            intensities = list(valuesByNanometers.values())

            randomGray = random.randint(50, 200)
            curve = self.plot(nanometers, intensities, pen=ChartThemeUtil.grayPen(randomGray, width=1))

            # Bounded overlay: drop the oldest curve once we exceed the cap
            # (pyqtgraph will not free it for us - spec D3 / constraint C2).
            self.__spectraCurves.append(curve)
            while len(self.__spectraCurves) > MAX_SPECTRA_CURVES:
                oldest = self.__spectraCurves.popleft()
                self.removeItem(oldest)

            self.updateAxes(spectralJob)


        elif policy == SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA_MEAN:
            spectra = spectralJob.getSpectra(self.getModuleParameters().getSpectrumSampleType())
            spectrum = spectra[-1]

            if len(spectrum.valuesByNanometers) > 0:

                values = list(spectrum.valuesByNanometers.values())
                keys = list(spectrum.valuesByNanometers.keys())

                if self.allSpectraValues is None:
                    lenValues = len(values)
                    self.allSpectraValues = np.empty([0, lenValues])
                else:
                    self.allSpectraValues = np.vstack((self.allSpectraValues, np.array(values)))

                if isinstance(self.allSpectraValues, np.ndarray) and self.allSpectraValues.size != 0:
                    meanSpectrumValues = np.mean(self.allSpectraValues, axis=0)

                    # Single persistent curve updated in place (spec D3.3),
                    # instead of removeAllSeries + rebuild every frame.
                    if self.__meanCurve is None:
                        self.__meanCurve = self.plot(keys, meanSpectrumValues.tolist(),
                                                     pen=ChartThemeUtil.primaryPen(width=2))
                    else:
                        self.__meanCurve.setData(keys, meanSpectrumValues.tolist())


                else:
                    print("skipped meanSpectrumValues")

    def setModuleParameters(self, moduleParameters: SpectralJobGraphViewModuleParameters):
        self.__moduleParameters = moduleParameters

    def getModuleParameters(self) -> SpectralJobGraphViewModuleParameters:
        return self.__moduleParameters
