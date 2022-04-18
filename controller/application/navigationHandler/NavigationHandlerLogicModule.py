from PyQt6.QtCore import QObject

class NavigationHandlerLogicModule(QObject):

    mainViewModule=None

    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        print(NavigationHandlerLogicModule)

    def handleNavigationSignal(self,navigationSignal):
        target=navigationSignal.getTarget()

        if target=="Home":
            self.mainViewModule.setWindowTitle("Spectracs")
            self.mainViewModule.setCurrentIndex(0)
        if target=="SpectralJob":
            self.mainViewModule.setWindowTitle("Spectracs > Spectrum")
            self.mainViewModule.setCurrentIndex(1)

        if target=="SpectralJobImport":
            self.mainViewModule.setWindowTitle("Spectracs > Import spectrum")
            self.mainViewModule.setCurrentIndex(2)




