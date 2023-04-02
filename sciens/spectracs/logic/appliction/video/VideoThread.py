import os
from typing import Generic, TypeVar

import cv2
from PySide6.QtCore import QThread
from PySide6.QtGui import QImage

from sys import platform

from appdata import AppDataPaths

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

S = TypeVar('S')

class VideoThread(QThread,Generic[S]):

    qImage: QImage
    _isVirtual:bool=False

    def __init__(self):
        super().__init__()
        self._runFlag = True
        self.cap = None
        self.qImage = None

        self._frameCount = 0
        self._currentFrameIndex = 0
        self.cap=None
        self.spectralJob=None


    def setFrameCount(self, spectraCount: int):
        self._frameCount = spectraCount

    def getFrameCount(self):
        return self._frameCount

    def _setCurrentFrameIndex(self, currentCount: int):
        self._currentFrameIndex = currentCount

    def _getCurrentFrameIndex(self):
        return self._currentFrameIndex

    def setIsVirtual(self, isVirtual: int):
        self._isVirtual = isVirtual

    def getIsVirtual(self):
        return self._isVirtual


    def run(self):

        self._runFlag=True

        self.onStart()

        #todo:hardCoded
        videoDeviceId=0
        #videoDeviceId = 1

        #self.cap = cv2.VideoCapture(0)
        self.cap = cv2.VideoCapture(videoDeviceId)

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # bar=cv2.VideoWriter.get(cv2.VIDEOWRITER_PROP_HW_DEVICE)
        # print(bar)

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        if platform=='linux':
            #self.cap.set(cv2.CAP_PROP_EXPOSURE, 300)
            #self.cap.set(cv2.CAP_PROP_EXPOSURE, 500)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, 150)
        elif platform=='win32':
            self.cap.set(cv2.CAP_PROP_EXPOSURE, -3)



        #self.cap.set(cv2.CAP_PROP_EXPOSURE, 300)
        # foo=""
        # foo=self.cap.get(cv2.CAP_PROP_EXPOSURE)
        # print(foo)
        # print(fourcc)

        while self._runFlag:

            self.beforeCapture()
            self.__captureFrame()


        self._setCurrentFrameIndex(0)
        self.cap.release()

    def __captureFrame(self):

        isVirtual = self.getIsVirtual()

        doSavePhysicallyCapturedImages = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().getDoSavePhysicallyCapturedImages()

        temporaryDirectory=None
        if doSavePhysicallyCapturedImages:
            app_paths = AppDataPaths()
            app_paths.setup()
            temporaryDirectory = app_paths.app_data_path+'/tmpImages'

            if not os.path.isdir(temporaryDirectory):
                os.makedirs(temporaryDirectory)

        if isVirtual:
            self.__captureVirtualFrame()
        else:
            self.__capturePhysicalFrame(temporaryDirectory)

    def __capturePhysicalFrame(self,temporaryDirectory:str):
        ret, frame = self.cap.read()
        if ret:
            rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgbImage.shape
            bytesPerLine = ch * w
            # needs QImage.Format.Format_RGB888 or crashes for some reason after some frames
            self.qImage = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)

            if temporaryDirectory is not None:
                self.qImage.save(temporaryDirectory+'/test.png','PNG')

            # self.onCapturedFrame(qImage)

        self.afterCapture()

    def __captureVirtualFrame(self):

        self.qImage=ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().getVirtualCameraImage()
        self.afterCapture()


    def stop(self):
        self._runFlag = False
        self._setCurrentFrameIndex(0)

    def beforeCapture(self):
        pass

    def afterCapture(self):
        frameCount = self.getFrameCount()
        if frameCount > 0:
            self._setCurrentFrameIndex(self._getCurrentFrameIndex() + 1)
            currentCount = self._getCurrentFrameIndex()
            if currentCount == frameCount-1:
                self._runFlag = False

    def createSignal(self)->S:
        return None

    def onStart(self):
        return None






