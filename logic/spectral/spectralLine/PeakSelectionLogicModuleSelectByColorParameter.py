from logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.Spectrum import Spectrum


class PeakSelectionLogicModuleSelectByColorParameter(IPeakSelectionLogicModuleSelectionParameter):
    __spectralLine: SpectralLine = None

    def getSpectralLine(self):
        return self.__spectralLine

    def setSpectralLine(self, spectralLine):
        self.__spectralLine = spectralLine
        return self
