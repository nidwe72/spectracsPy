from controller.application.ApplicationSignalsProviderLogicModule import ApplicationSignalsProviderLogicModule
from controller.application.navigationHandler.NavigationHandlerLogicModule import NavigationHandlerLogicModule


class ApplicationContextLogicModule:

    navigationHandler=None
    applicationSignalsProvider=None

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


