from PySide6.QtGui import QImage

from base.Singleton import Singleton
from controller.application.ApplicationSignalsProviderLogicModule import ApplicationSignalsProviderLogicModule
from controller.application.navigationHandler.NavigationHandlerLogicModule import NavigationHandlerLogicModule
from model.databaseEntity.spectral.device import SpectrometerProfile, Spectrometer


class ApplicationContextLogicModule(Singleton):

    navigationHandler=None
    applicationSignalsProvider=None
    __spectrometer:Spectrometer=None
    __virtualCameraImage:QImage=None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ApplicationContextLogicModule, cls).__new__(cls)
            navigationHandler = cls.instance.getNavigationHandler()
            signalsProvider = cls.instance.getApplicationSignalsProvider()
        return cls.instance

    def getNavigationHandler(self):
        if self.navigationHandler is None:
            self.navigationHandler=NavigationHandlerLogicModule(None)
        return self.navigationHandler

    def getApplicationSignalsProvider(self):
        if self.applicationSignalsProvider is None:
            self.applicationSignalsProvider=ApplicationSignalsProviderLogicModule(None)
        return self.applicationSignalsProvider

    def setSpectrometer(self,spectrometer:Spectrometer):
        self.__spectrometer=spectrometer

    def getSpectrometer(self)->Spectrometer:
        return self.__spectrometer

    def setVirtualCameraImage(self,virtualCameraImage:QImage):
        self.__virtualCameraImage=virtualCameraImage

    def getVirtualCameraImage(self)->QImage:
        return self.__virtualCameraImage
