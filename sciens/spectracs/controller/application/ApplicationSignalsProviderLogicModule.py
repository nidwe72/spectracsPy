from PySide6.QtCore import QObject, Signal

from sciens.base.SingletonQObject import SingletonQObject
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal

from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.signal.SpectrometerProfileSignal import SpectrometerProfileSignal
from sciens.spectracs.model.signal.UserSignal import UserSignal


class ApplicationSignalsProviderLogicModule(QObject, metaclass=SingletonQObject):
    navigationSignal = Signal(NavigationSignal)
    spectrometerProfileSignal = Signal(SpectrometerProfileSignal)
    applicationStatusSignal = Signal(ApplicationStatusSignal)
    userSessionSignal = Signal()  # login/logout changed -> consumers re-read CurrentUserSession
    userSignal = Signal(UserSignal)  # user created/updated/deleted -> user list re-fetches

    def emitNavigationSignal(self, navigationSignalModel):
        self.navigationSignal.emit(navigationSignalModel)

    def emitUserSessionSignal(self):
        self.userSessionSignal.emit()

    def emitUserSignal(self, userSignal: UserSignal):
        self.userSignal.emit(userSignal)

    def emitSpectrometerProfileSignal(self, spectrometerProfileSignal: SpectrometerProfileSignal):
        self.spectrometerProfileSignal.emit(spectrometerProfileSignal)


    def emitApplicationStatusSignal(self, applicationStatusSignal):
        self.applicationStatusSignal.emit(applicationStatusSignal)
