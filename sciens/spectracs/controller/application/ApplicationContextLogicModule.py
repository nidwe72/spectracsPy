from sciens.base.Singleton import Singleton
from sciens.spectracs.controller.application.ApplicationSignalsProviderLogicModule import ApplicationSignalsProviderLogicModule
from sciens.spectracs.controller.application.navigationHandler.NavigationHandlerLogicModule import NavigationHandlerLogicModule
from sciens.spectracs.controller.application.setting.ApplicationSettings import ApplicationSettings
from sciens.spectracs.logic.appliction.util.ApplicationConfigUtil import ApplicationConfigUtil
from sciens.spectracs.model.databaseEntity.application.ApplicationConfig import ApplicationConfig


class ApplicationContextLogicModule(Singleton):


    applicationSignalsProvider=None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ApplicationContextLogicModule, cls).__new__(cls)
            navigationHandler = cls.instance.getNavigationHandler()
            signalsProvider = cls.instance.getApplicationSignalsProvider()
        return cls.instance

    def getNavigationHandler(self)->NavigationHandlerLogicModule:
        return NavigationHandlerLogicModule()

    def getApplicationSignalsProvider(self):
        if self.applicationSignalsProvider is None:
            self.applicationSignalsProvider=ApplicationSignalsProviderLogicModule(None)
        return self.applicationSignalsProvider

    def getApplicationSettings(self)->ApplicationSettings:
        return ApplicationSettings()

    def getApplicationConfig(self)->ApplicationConfig:
        result = ApplicationConfigUtil().getApplicationConfig()
        return result

