from typing import Dict
from chromos.base.Singleton import Singleton
from chromos.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from chromos.spectracs.logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from chromos.spectracs.logic.persistence.database.spectrometerProfile.PersistSpectrometerProfileLogicModule import \
    PersistSpectrometerProfileLogicModule
from chromos.spectracs.logic.persistence.database.spectrometerProfile.PersistenceParametersGetSpectrometerProfiles import \
    PersistenceParametersGetSpectrometerProfiles
from chromos.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from chromos.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile


class SpectrometerProfileUtil(Singleton):

    def getSpectrometerProfiles(self) -> Dict[str, SpectrometerProfile]:
        spectrometerProfiles=PersistSpectrometerProfileLogicModule().getSpectrometerProfile(PersistenceParametersGetSpectrometerProfiles())
        return spectrometerProfiles

    def initializeSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        if spectrometerProfile.spectrometerCalibrationProfile is None:
            spectrometerCalibrationProfile=SpectrometerCalibrationProfile()
            SpectrometerCalibrationProfileUtil().initializeSpectrometerCalibrationProfile(spectrometerCalibrationProfile)
            spectrometerProfile.spectrometerCalibrationProfile=spectrometerCalibrationProfile

    def setConfiguredSpectrometerProfileIntoApplicationSettings(self) :
        applicationConfig = ApplicationContextLogicModule().getApplicationConfig()
        spectrometerProfilesMapping=applicationConfig.getSpectrometerProfilesMapping()

        for spectrometerProfilesMappingEntry in spectrometerProfilesMapping:
            if spectrometerProfilesMappingEntry.isDefault:
                spectrometerProfile = spectrometerProfilesMappingEntry.spectrometerProfile
                applicationSettings = ApplicationContextLogicModule().getApplicationSettings()
                applicationSettings.setSpectrometerProfile(spectrometerProfile)
                break

        return


