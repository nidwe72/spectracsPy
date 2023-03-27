from typing import Dict

from sqlalchemy.orm import class_mapper
from sqlalchemy import inspect

from logic.model.util.databaseEntity.SqlUtil import SqlUtil
from logic.persistence.database.spectralLineMasterData.PersistenceParametersGetSpectralLineMasterDatas import \
    PersistenceParametersGetSpectralLineMasterDatas
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData


class PersistSpectralLineMasterDataLogicModule:

    def saveSpectralLineMasterData(self, spectralLineMasterData: SpectralLineMasterData):
        session = session_factory()
        session.add(spectralLineMasterData)
        session.commit()

    def getSpectralLineMasterDatasOld(self,
                                      persistenceParametersGetSpectralLineMasterDatas: PersistenceParametersGetSpectralLineMasterDatas) -> \
            Dict[int, SpectralLineMasterData]:
        ids = persistenceParametersGetSpectralLineMasterDatas.getIds()
        session = session_factory()
        resultList = session.query(SpectralLineMasterData).all()

        result: Dict[int, SpectralLineMasterData] = {}
        for spectralLineMasterData in resultList:
            result[spectralLineMasterData.id] = spectralLineMasterData

        return result

    def getSpectralLineMasterDatas(self,
                                   moduleParameters: PersistenceParametersGetSpectralLineMasterDatas) -> \
            Dict[int, SpectralLineMasterData]:

        if moduleParameters is None:
            moduleParameters = PersistenceParametersGetSpectralLineMasterDatas()

        baseEntity = moduleParameters.getBaseEntity()
        selectStatement = SqlUtil.createSelect(baseEntity)
        result = SqlUtil.executeSelect(baseEntity, selectStatement)

        return result

    def getChangedAttributes(self, entity):
        result = []
        inspr = inspect(entity)
        attrs = class_mapper(entity.__class__).column_attrs  # exclude relationships
        for attr in attrs:
            hist = getattr(inspr.attrs, attr.key).history
            if hist.has_changes():
                result.append(attr)
        return result
