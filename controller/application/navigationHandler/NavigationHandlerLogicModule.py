from PySide6.QtCore import QObject

from model.application.navigation.NavigationSignal import NavigationSignal


class NavigationHandlerLogicModule(QObject):

    mainContainerViewModule=None

    def __init__(self,parent):
        super().__init__()
        self.parent = parent

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
        elif target=="SpectrometerProfileListViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometers")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectrometerProfileViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometer profile")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="SpectrometerCalibrationProfileViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometer profile > Calibration profile")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))
        elif target=="VirtualCameraViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings > Virtual camera")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(self.__getWidgetIndex(navigationSignal))


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
        elif target=="SpectrometerProfileListViewModule":
            result = 4
        elif target=="SpectrometerProfileViewModule":
            result = 5
        elif target=="SpectrometerCalibrationProfileViewModule":
            result = 6
        elif target=="VirtualCameraViewModule":
            result = 7


        return result

    def getViewModule(self,navigationSignal:NavigationSignal):
        index=self.__getWidgetIndex(navigationSignal)
        result=self.mainContainerViewModule.mainViewModule.widget(index)
        return result








