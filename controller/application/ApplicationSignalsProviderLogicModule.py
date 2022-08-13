from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QObject

from base.SingletonQObject import SingletonQObject

from model.application.navigation.NavigationSignal import NavigationSignal
from model.signal.SpectrometerProfileSignal import SpectrometerProfileSignal


class ApplicationSignalsProviderLogicModule(SingletonQObject,QObject):

    navigationSignal = pyqtSignal(NavigationSignal)
    spectrometerProfileSignal = pyqtSignal(SpectrometerProfileSignal)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def emitNavigationSignal(self,navigationSignalModel):
        self.navigationSignal.emit(navigationSignalModel)

    def emitSpectrometerProfileSignal(self,spectrometerProfileSignal:SpectrometerProfileSignal):
        self.spectrometerProfileSignal.emit(spectrometerProfileSignal)




