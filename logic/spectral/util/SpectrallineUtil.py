from base.Singleton import Singleton
from typing import Dict
from typing import List
from operator import attrgetter

from model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectralLineUtil(Singleton):

    def getSpectralLinesByProminences(self,spectralLinesCollection: List[SpectralLine] )->Dict[float,SpectralLine]:

        result:Dict[float,SpectralLine]={}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.prominence]=spectralLine
        return result

    def sortSpectralLinesByProminences(self,spectralLinesCollection: List[SpectralLine] )->Dict[float,SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('prominence'), reverse=True)
        return spectralLinesCollection

