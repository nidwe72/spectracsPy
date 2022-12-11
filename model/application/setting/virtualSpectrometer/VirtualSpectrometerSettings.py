from PySide6.QtGui import QImage

from base.Singleton import Singleton


class VirtualSpectrometerSettings(Singleton):

    __virtualCameraImage: QImage = None

    def setVirtualCameraImage(self,virtualCameraImage:QImage):
        self.__virtualCameraImage=virtualCameraImage

    def getVirtualCameraImage(self)->QImage:
        return self.__virtualCameraImage


