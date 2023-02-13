from typing import List

from logic.spectral.util.IPeakSelectionLogicModuleSelectionParameter import IPeakSelectionLogicModuleSelectionParameter
from logic.spectral.util.PeakSelectionLogicModuleSelectByProminenceParameter import \
    PeakSelectionLogicModuleSelectByProminenceParameter
from model.spectral.Spectrum import Spectrum


class PeakSelectionLogicModuleParameters:

    __spectrum:Spectrum=None

    __selectionParameters:List[IPeakSelectionLogicModuleSelectionParameter]=[]

    def getSelectionParameters(self)->List[IPeakSelectionLogicModuleSelectionParameter]:
        return self.__selectionParameters

    def setSelectionParameters(self, selectionParameters:List[IPeakSelectionLogicModuleSelectionParameter]):
        self.__selectionParameters=selectionParameters
        return self

    def __addToSelectionParameters(self, selectionParameter: IPeakSelectionLogicModuleSelectionParameter):
        self.__selectionParameters.append(selectionParameter)
        return self

    def addSelectByProminence(self,count:int):
        parameter = PeakSelectionLogicModuleSelectByProminenceParameter()
        parameter.count=count
        self.__addToSelectionParameters(parameter)
        return self


    def getSpectrum(self):
        return self.__spectrum

    def setSpectrum(self, spectrum):
        self.__spectrum=spectrum
        return self





