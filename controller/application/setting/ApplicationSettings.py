from base.Singleton import Singleton
from model.application.setting.virtualSpectrometer.VirtualSpectrometerSettings import VirtualSpectrometerSettings
from model.databaseEntity.spectral.device import Spectrometer



class ApplicationSettings(Singleton):
    __spectrometer: Spectrometer = None


    def setSpectrometer(self,spectrometer:Spectrometer):
        self.__spectrometer=spectrometer

    def getSpectrometer(self)->Spectrometer:
        return self.__spectrometer

    def getVirtualSpectrometerSettings(self):
        return VirtualSpectrometerSettings()


