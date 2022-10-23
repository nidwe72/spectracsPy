from typing import Dict

from logic.persistence.database.spectralLineMasterData.PersistenceParametersGetSpectralLineMasterDatas import \
    PersistenceParametersGetSpectralLineMasterDatas
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData


class PersistSpectralLineMasterDataLogicModule:

    def saveSpectralLineMasterData(self, spectralLineMasterData: SpectralLineMasterData):
        session = session_factory()
        session.add(spectralLineMasterData)
        session.commit()

    def getSpectralLineMasterDatas(self,
                                   persistenceParametersGetSpectralLineMasterDatas: PersistenceParametersGetSpectralLineMasterDatas) -> \
            Dict[int, SpectralLineMasterData]:
        ids = persistenceParametersGetSpectralLineMasterDatas.getIds()
        session = session_factory()
        resultList = session.query(SpectralLineMasterData).all()

        result: Dict[int, SpectralLineMasterData] = {}
        for spectralLineMasterData in resultList:
            result[spectralLineMasterData.id] = spectralLineMasterData

        return result
