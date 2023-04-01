from typing import Dict

from chromos.spectracs.logic.persistence.database.spectrometerProfile.PersistenceParametersGetSpectrometerProfiles import \
    PersistenceParametersGetSpectrometerProfiles
from chromos.spectracs.model.databaseEntity.DbBase import session_factory
from chromos.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile


class PersistSpectrometerProfileLogicModule:

    def saveSpectrometerProfile(self, spectrometerProfile: SpectrometerProfile):
        session = session_factory()
        session.add(spectrometerProfile)
        session.commit()

    def getSpectrometerProfile(self,
                               persistenceParametersGetSpectrometerProfile: PersistenceParametersGetSpectrometerProfiles) -> \
    Dict[int, SpectrometerProfile]:

        ids = persistenceParametersGetSpectrometerProfile.getIds()
        session = session_factory()
        resultList = session.query(SpectrometerProfile).all()
        result: Dict[int, SpectrometerProfile] = {}
        for spectrometer in resultList:
            result[spectrometer.id] = spectrometer
        return result
