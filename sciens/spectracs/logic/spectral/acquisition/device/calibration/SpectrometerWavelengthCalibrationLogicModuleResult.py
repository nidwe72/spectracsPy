from typing import List

from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectrometerWavelengthCalibrationLogicModuleResult:

    __spectralLines: List[SpectralLine] = None

    def getSpectralLines(self):
        if self.__spectralLines is None:
            self.__spectralLines=[]
        return self.__spectralLines

    def setSpectralLines(self, spectralLines):
        self.__spectralLines=spectralLines
