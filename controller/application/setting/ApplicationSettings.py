from base.Singleton import Singleton
from model.application.setting.virtualSpectrometer.VirtualSpectrometerSettings import VirtualSpectrometerSettings
from model.databaseEntity.spectral.device import Spectrometer, SpectrometerProfile


class ApplicationSettings(Singleton):

    __spectrometerProfile: SpectrometerProfile = None

    def getVirtualSpectrometerSettings(self):
        return VirtualSpectrometerSettings()

    def setSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        self.__spectrometerProfile=spectrometerProfile

    def getSpectrometerProfile(self)->SpectrometerProfile:
        return self.__spectrometerProfile



