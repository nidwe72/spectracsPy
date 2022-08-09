from typing import Dict
from logic.persistence.database.PersistenceParametersGetSpectrometerVendors import \
    PersistenceParametersGetSpectrometerVendors
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device import SpectrometerVendor


class PersistSpectrometerVendorLogicModule:

    def saveSpectrometerVendor(self, spectrometerVendor:SpectrometerVendor):
        session = session_factory()
        session.add(spectrometerVendor)
        session.commit()
        # session.refresh()
        # session.expire_all()
        # session.close()!

    def getSpectrometerVendors(self,
                               persistenceParametersGetSpectrometerVendors: PersistenceParametersGetSpectrometerVendors) -> \
    Dict[int,SpectrometerVendor]:
        ids = persistenceParametersGetSpectrometerVendors.getIds()
        session = session_factory()
        resultList = session.query(SpectrometerVendor).all()

        result:Dict[int,SpectrometerVendor] = {}
        for spectrometerVendor in resultList:
            result[spectrometerVendor.id]=spectrometerVendor

        return result
