from typing import List

import numpy as np
from numpy import float32
from scipy.signal import find_peaks, peak_prominences

from logic.spectral.spectralLine.PeakSelectionLogicModuleSelectByColorParameter import \
    PeakSelectionLogicModuleSelectByColorParameter
from logic.spectral.spectralLine.PeakSelectionLogicModuleSelectByPixelIndex import \
    PeakSelectionLogicModuleSelectByPixelIndex
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleResult import SpectralLinesSelectionLogicModuleResult
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleSelectByIntensity import PeakSelectionLogicModuleSelectByIntensity
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleSelectByProminenceParameter import PeakSelectionLogicModuleSelectByProminenceParameter
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleParameters import SpectralLinesSelectionLogicModuleParameters
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.Spectrum import Spectrum


class SpectralLineSelectionLogicModule:

    __selectedLines:List[SpectralLine]=None

    __moduleParameters:SpectralLinesSelectionLogicModuleParameters=None


    def getModuleParameters(self):
        return self.__moduleParameters

    def setModuleParameters(self, moduleParameters):
        self.__moduleParameters=moduleParameters
        return self

    def execute(self)->SpectralLinesSelectionLogicModuleResult:
        result=SpectralLinesSelectionLogicModuleResult()
        self.__resetSelection()
        for selectionParameter in self.getModuleParameters().getSelectionParameters():
            if isinstance(selectionParameter,PeakSelectionLogicModuleSelectByProminenceParameter):
                self.__selectByProminence(selectionParameter)
            if isinstance(selectionParameter,PeakSelectionLogicModuleSelectByIntensity):
                self.__selectByIntensity(selectionParameter)
            if isinstance(selectionParameter,PeakSelectionLogicModuleSelectByPixelIndex):
                self.__selectByPixelIndex(selectionParameter)

        result.setSpectralLines(self.__getSelectedLines())

        return result

    def __resetSelection(self):
        self.__selectedLines=[]
        self.__setSelectedLines(self.__selectedLines)

    def __setSelectedLines(self, selectedPeaks:List[SpectralLine]):
        self.__selectedLines=selectedPeaks

    def __getSelectedLines(self)->List[SpectralLine]:
        return self.__selectedLines

    def __selectPeaksByIntensities(self, spectrum: Spectrum, count: int, leftSpectralLine: SpectralLine = None,
                                   rightSpectralLine: SpectralLine = None, ):
        pass

    def __selectByProminence(self, selectParameter:PeakSelectionLogicModuleSelectByProminenceParameter):

        result = self.__getSelectedLines()
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

        self.__setSelectedLines(result)

        return result

    def __selectByIntensity(self,selectParameter:PeakSelectionLogicModuleSelectByIntensity):
        selectedLines = self.__getSelectedLines()
        selectedLines=sorted(selectedLines,key=lambda x:x.intensity,reverse=True)
        result=selectedLines[0:selectParameter.getCount()]
        self.__setSelectedLines(result)

    def __selectByPixelIndex(self, selectParameter: PeakSelectionLogicModuleSelectByPixelIndex):
        selectedLines = self.__getSelectedLines()
        selectedLines = sorted(selectedLines, key=lambda x: x.pixelIndex, reverse=True)
        result = selectedLines[0:selectParameter.getCount()]
        self.__setSelectedLines(result)

    def __validateByColor(self,selectParameter:PeakSelectionLogicModuleSelectByColorParameter):
        #todo:unfinished
        suppliedNanometer = selectParameter.getSpectralLine().spectralLineMasterData.nanometer
        suppliedColor = SpectralColorUtil().wavelengthToColor(suppliedNanometer)

        selectedLines = self.__getSelectedLines()
        selectedLinesByColorDifferences=[]
        for selectedLine in selectedLines:
            SpectralColorUtil().getColorDifference(suppliedColor, selectedLine.pixelIndex)


        selectedLines = sorted(selectedLines, key=lambda x: x.pixelIndex, reverse=True)



        # colorDifference =
        pass

