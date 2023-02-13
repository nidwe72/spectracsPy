from typing import List

import numpy as np
from numpy import float32
from scipy.signal import find_peaks, peak_prominences

from logic.spectral.util.PeakSelectionLogicModuleSelectByProminenceParameter import PeakSelectionLogicModuleSelectByProminenceParameter
from logic.spectral.util.PeakSelectionLogicModuleParameters import PeakSelectionLogicModuleParameters
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.Spectrum import Spectrum


class PeakSelectionLogicModule:

    __selectedPeaks:List[SpectralLine]=None

    __moduleParameters:PeakSelectionLogicModuleParameters=None


    def getModuleParameters(self):
        return self.__moduleParameters

    def setModuleParameters(self, moduleParameters):
        self.__moduleParameters=moduleParameters
        return self

    def execute(self):
        self.__resetSelection()
        for selectionParameter in self.getModuleParameters().getSelectionParameters():

            someType = type(selectionParameter)



            if isinstance(selectionParameter,PeakSelectionLogicModuleSelectByProminenceParameter):
                self.__selectPeaksByProminence(selectionParameter)

        return

    def __resetSelection(self):
        self.__selectedPeaks=[]
        self.__setSelectedPeaks(self.__selectedPeaks)

    def __setSelectedPeaks(self, selectedPeaks:List[SpectralLine]):
        self.__selectedPeaks=selectedPeaks

    def __getSelectedPeaks(self)->List[SpectralLine]:
        return self.__selectedPeaks

    def __selectPeaksByIntensities(self, spectrum: Spectrum, count: int, leftSpectralLine: SpectralLine = None,
                                   rightSpectralLine: SpectralLine = None, ):
        pass

    def __selectPeaksByProminence(self, selectParameter:PeakSelectionLogicModuleSelectByProminenceParameter):

        result = []
        spectrum=self.getModuleParameters().getSpectrum()
        intensities = np.asarray(list(spectrum.valuesByNanometers.values()),float32)

        for candidateProminence in range(1,255):
            peaks, _ = find_peaks(intensities, distance=3, width=3, rel_height=0.5, prominence=candidateProminence)

            if len(peaks)==selectParameter.count:
                break;

        prominences = peak_prominences(intensities, peaks)[0]
        peaksByProminences=dict(zip(prominences,peaks))
        for foundProminence,peak, in peaksByProminences.items():
            spectralLine = SpectralLine()
            spectralLine.pixelIndex=peak
            spectralLine.prominence = foundProminence
            spectralLine.intensity = spectrum.valuesByNanometers.get(peak)
            result.append(spectralLine)

        return result

