from typing import Dict

from logic.persistence.database.spectrometerProfile.PersistenceParametersGetSpectrometerProfiles import \
    PersistenceParametersGetSpectrometerProfiles
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device import SpectrometerProfile


class PersistSpectrometerProfileLogicModule:

    def saveSpectrometerProfile(self, spectrometer: SpectrometerProfile):
        session = session_factory()
        session.add(spectrometer)
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