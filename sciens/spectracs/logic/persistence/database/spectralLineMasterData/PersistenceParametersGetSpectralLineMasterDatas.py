from typing import List

from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData


class PersistenceParametersGetSpectralLineMasterDatas:

    def __init__(self, *args, **kwargs):
        self.ids: List = []
        self.__baseEntity= None

    def getBaseEntity(self):
        if self.__baseEntity is None:
            self.__baseEntity=SpectralLineMasterData()
        return self.__baseEntity

    def setBaseEntity(self, baseEntity):
        self.__baseEntity=baseEntity
        return self


    def setIds(self, ids: List):
        self.ids = ids

    def getIds(self) -> List:
        return self.ids
