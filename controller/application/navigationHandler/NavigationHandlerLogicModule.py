from PyQt6.QtCore import QObject

class NavigationHandlerLogicModule(QObject):

    mainContainerViewModule=None

    def __init__(self,parent):
        super().__init__()
        self.parent = parent

    def handleNavigationSignal(self,navigationSignal):
        target=navigationSignal.getTarget()

        if target=="Home":
            self.mainContainerViewModule.setWindowTitle("Spectracs")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(0)
        elif target=="SpectralJob":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrum")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(1)
        elif target=="SpectralJobImport":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Import spectrum")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(2)
        elif target=="SettingsViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Settings")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(3)
        elif target=="SpectrometerProfileListViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometers")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(4)
        elif target=="SpectrometerProfileViewModule":
            self.mainContainerViewModule.setWindowTitle("Spectracs > Spectrometer profile")
            self.mainContainerViewModule.mainViewModule.setCurrentIndex(5)







