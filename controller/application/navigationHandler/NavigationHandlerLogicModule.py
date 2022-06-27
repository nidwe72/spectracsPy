from PyQt6.QtCore import QObject

class NavigationHandlerLogicModule(QObject):

    mainViewModule=None

    def __init__(self,parent):
        super().__init__()
        self.parent = parent

    def handleNavigationSignal(self,navigationSignal):
        target=navigationSignal.getTarget()

        if target=="Home":
            self.mainViewModule.setWindowTitle("Spectracs")
            self.mainViewModule.setCurrentIndex(0)
        elif target=="SpectralJob":
            self.mainViewModule.setWindowTitle("Spectracs > Spectrum")
            self.mainViewModule.setCurrentIndex(1)
        elif target=="SpectralJobImport":
            self.mainViewModule.setWindowTitle("Spectracs > Import spectrum")
            self.mainViewModule.setCurrentIndex(2)
        elif target=="SettingsViewModule":
            self.mainViewModule.setWindowTitle("Spectracs > Settings")
            self.mainViewModule.setCurrentIndex(3)
        elif target=="CameraSelectionViewModule":
            self.mainViewModule.setWindowTitle("Spectracs > Camera selection")
            self.mainViewModule.setCurrentIndex(4)





