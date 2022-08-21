from PyQt6.QtGui import QColor

from base.Singleton import Singleton


class ApplicationStyleLogicModule(Singleton):

    def getPrimaryColor(self):
        result=QColor.fromRgb(61, 120, 72)
        return result

    def getPrimaryTextColor(self):
        result=QColor.fromRgb(255, 255, 255)
        return result