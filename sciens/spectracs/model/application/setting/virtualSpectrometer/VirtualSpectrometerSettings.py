from PySide6.QtGui import QImage

from sciens.base.Singleton import Singleton


class VirtualSpectrometerSettings(Singleton):

    __virtualCameraImage: QImage = None
    __doSavePhysicallyCapturedImages: bool = False

    def setVirtualCameraImage(self,virtualCameraImage:QImage):
        self.__virtualCameraImage=virtualCameraImage

    def getVirtualCameraImage(self)->QImage:
        return self.__virtualCameraImage

    def getDoSavePhysicallyCapturedImages(self)->bool:
        return self.__doSavePhysicallyCapturedImages

    def setDoSavePhysicallyCapturedImages(self,doSavePhysicallyCapturedImages:bool):
        self.__doSavePhysicallyCapturedImages=doSavePhysicallyCapturedImages


