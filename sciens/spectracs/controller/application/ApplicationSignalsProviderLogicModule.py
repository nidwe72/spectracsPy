from PySide6.QtCore import QObject, Signal

from sciens.base.SingletonQObject import SingletonQObject
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal

from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.signal.SpectrometerProfileSignal import SpectrometerProfileSignal


class ApplicationSignalsProviderLogicModule(SingletonQObject, QObject):
    navigationSignal = Signal(NavigationSignal)
    spectrometerProfileSignal = Signal(SpectrometerProfileSignal)
    applicationStatusSignal = Signal(ApplicationStatusSignal)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def emitNavigationSignal(self, navigationSignalModel):
        self.navigationSignal.emit(navigationSignalModel)

    def emitSpectrometerProfileSignal(self, spectrometerProfileSignal: SpectrometerProfileSignal):
        self.spectrometerProfileSignal.emit(spectrometerProfileSignal)

    def emitApplicationStatusSignal(self, applicationStatusSignal):
        self.applicationStatusSignal.emit(applicationStatusSignal)
