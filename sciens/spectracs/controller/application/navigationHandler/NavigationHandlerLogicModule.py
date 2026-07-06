from sciens.base.Singleton import Singleton
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal


class NavigationHandlerLogicModule(Singleton):

    mainContainerViewModule=None

    def __init__(self):
        self.__previousNavigationSignal=None

    def handleNavigationSignal(self,navigationSignal):
        target=navigationSignal.getTarget()

        if target=="Home":
            self.mainContainerViewModule.setWindowTitle("Spectracs")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectralJob":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrum")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectralJobImport":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Import spectrum")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SettingsViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectrometerCalibrationProfileViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometer setup > Calibration")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="VirtualSpectrometerViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Virtual spectrometer")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="UserListViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Users")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="UserViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Users > User")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="PlaygroundViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Playground")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="WizardViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Measurement")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="LoginViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Login")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="PluginListViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Plugins")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="PluginViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Plugins > Plugin")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectrometerSetupListViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Spectrometer setups")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectrometerSetupViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Spectrometer setups > Spectrometer setup")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="RegistrationViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Register")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="AppUserSettingsViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Account settings")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="DevCaptureViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Development > Capture images")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))

        self.setPreviousNavigationSignal(navigationSignal)

    def __getWidgetIndex(self, navigationSignal:NavigationSignal):
        result=None
        target=navigationSignal.getTarget()

        if target=="Home":
            result=0
        elif target=="SpectralJob":
            result = 1
        elif target=="SpectralJobImport":
            result = 2
        elif target=="SettingsViewModule":
            result = 3
        elif target=="SpectrometerCalibrationProfileViewModule":
            result = 4
        elif target=="VirtualSpectrometerViewModule":
            result = 5
        elif target=="UserListViewModule":
            result = 6
        elif target=="UserViewModule":
            result = 7
        elif target=="PlaygroundViewModule":
            result = 8
        elif target=="WizardViewModule":
            result = 9
        elif target=="LoginViewModule":
            result = 10
        elif target=="PluginListViewModule":
            result = 11
        elif target=="PluginViewModule":
            result = 12
        elif target=="SpectrometerSetupListViewModule":
            result = 13
        elif target=="SpectrometerSetupViewModule":
            result = 14
        elif target=="RegistrationViewModule":
            result = 15
        elif target=="AppUserSettingsViewModule":
            result = 16
        elif target=="DevCaptureViewModule":
            result = 17


        return result

    def getViewModule(self,navigationSignal:NavigationSignal):
        index=self.__getWidgetIndex(navigationSignal)
        result=self.mainContainerViewModule.mainViewModule.widget(index)
        return result


    def getPreviousNavigationSignal(self):
        return self.__previousNavigationSignal


    def setPreviousNavigationSignal(self, navigationSignal):
        self.__previousNavigationSignal=navigationSignal






