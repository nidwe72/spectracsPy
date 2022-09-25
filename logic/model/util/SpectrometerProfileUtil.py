from typing import Dict
from base.Singleton import Singleton
from logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from logic.persistence.database.spectrometerProfile.PersistSpectrometerProfileLogicModule import \
    PersistSpectrometerProfileLogicModule
from logic.persistence.database.spectrometerProfile.PersistenceParametersGetSpectrometerProfiles import \
    PersistenceParametersGetSpectrometerProfiles
from model.databaseEntity.spectral.device import SpectrometerProfile, SpectrometerCalibrationProfile


class SpectrometerProfileUtil(Singleton):

    def getSpectrometerProfiles(self) -> Dict[str, SpectrometerProfile]:
        spectrometerProfiles=PersistSpectrometerProfileLogicModule().getSpectrometerProfile(PersistenceParametersGetSpectrometerProfiles())
        return spectrometerProfiles

    def initializeSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        if spectrometerProfile.spectrometerCalibrationProfile is None:
            spectrometerCalibrationProfile=SpectrometerCalibrationProfile()
            SpectrometerCalibrationProfileUtil().initializeSpectrometerCalibrationProfile(spectrometerCalibrationProfile)
            spectrometerProfile.spectrometerCalibrationProfile=spectrometerCalibrationProfile



