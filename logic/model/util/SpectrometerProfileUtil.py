from typing import Dict
from base.Singleton import Singleton
from logic.persistence.database.spectrometerProfile.PersistSpectrometerProfileLogicModule import \
    PersistSpectrometerProfileLogicModule
from logic.persistence.database.spectrometerProfile.PersistenceParametersGetSpectrometerProfiles import \
    PersistenceParametersGetSpectrometerProfiles
from model.databaseEntity.spectral.device import SpectrometerProfile


class SpectrometerProfileUtil(Singleton):

    def getSpectrometerProfiles(self) -> Dict[str, SpectrometerProfile]:
        spectrometerProfiles=PersistSpectrometerProfileLogicModule().getSpectrometerProfile(PersistenceParametersGetSpectrometerProfiles())
        return spectrometerProfiles


