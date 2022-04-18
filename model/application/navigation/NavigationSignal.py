from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

class NavigationSignal(QObject):
    target = ""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def getTarget(self):
        return self.target

    def setTarget(self, target):
        self.target = target
