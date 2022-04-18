from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QObject

from base.SingletonQObject import SingletonQObject

from model.application.navigation.NavigationSignal import NavigationSignal

class ApplicationSignalsProviderLogicModule(SingletonQObject,QObject):

    navigationSignal = pyqtSignal(NavigationSignal)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def emitNavigationSignal(self,navigationSignalModel):
        self.navigationSignal.emit(navigationSignalModel)





