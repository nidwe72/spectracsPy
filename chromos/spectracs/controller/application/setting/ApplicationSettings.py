from chromos.base.Singleton import Singleton
from chromos.spectracs.model.application.setting.virtualSpectrometer.VirtualSpectrometerSettings import VirtualSpectrometerSettings
from chromos.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile


class ApplicationSettings(Singleton):

    __spectrometerProfile: SpectrometerProfile = None

    def getVirtualSpectrometerSettings(self):
        return VirtualSpectrometerSettings()

    def setSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        self.__spectrometerProfile=spectrometerProfile

    def getSpectrometerProfile(self)->SpectrometerProfile:
        return self.__spectrometerProfile






