from typing import List

from model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectralLinesSelectionLogicModuleResult:

    __spectralLines: List[SpectralLine] = None

    def getSpectralLines(self):
        return self.__spectralLines

    def setSpectralLines(self, spectralLines):
        self.__spectralLines=spectralLines