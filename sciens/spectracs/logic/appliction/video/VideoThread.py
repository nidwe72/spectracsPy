import os
from typing import Generic, TypeVar

from PySide6.QtCore import QThread
from PySide6.QtGui import QImage

from sciens.spectracs.logic.appliction.video.capture.CaptureBackend import getCaptureBackend
from sciens.spectracs.model.databaseEntity.AppDataPathUtil import get_app_data_dir
from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

S = TypeVar('S')

class VideoThread(QThread,Generic[S]):

    qImage: QImage
    _isVirtual:bool=False

    def __init__(self):
        super().__init__()
        self._runFlag = True
        self.qImage = None

        # Real capture is routed through a platform CaptureBackend (owns cv2). _deviceId defaults to 0,
        # preserving today's behaviour; the resolver sets the correct index via setDeviceId (SM2).
        self._backend = None
        self._deviceId = 0

        self._frameCount = 0
        self._currentFrameIndex = 0
        self.spectralJob=None

    def setDeviceId(self, deviceId: int):
        self._deviceId = deviceId


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

        # Virtual mode serves frames from VirtualSpectrometerSettings and must never touch a
        # physical camera. This is also required on Android, where there is no usable capture device
        # (getCaptureBackend() there raises on open). Only open a backend for a real sensor.
        if not self.getIsVirtual():
            self._backend = getCaptureBackend()
            self._backend.open(self._deviceId)

            # Warm-up: the first frames after open can be empty while the UVC stream settles; discard a
            # few so the first delivered frame is real (spec §3.5 / §0). read() never raises → None ok.
            for _ in range(6):
                if self._backend.read() is not None:
                    break

        while self._runFlag:

            self.beforeCapture()
            self.__captureFrame()


        self._setCurrentFrameIndex(0)
        if self._backend is not None:
            self._backend.release()
            self._backend = None

    def __captureFrame(self):

        isVirtual = self.getIsVirtual()

        doSavePhysicallyCapturedImages = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().getDoSavePhysicallyCapturedImages()

        temporaryDirectory=None
        if doSavePhysicallyCapturedImages:
            temporaryDirectory = get_app_data_dir()+'/tmpImages'

            if not os.path.isdir(temporaryDirectory):
                os.makedirs(temporaryDirectory)

        if isVirtual:
            self.__captureVirtualFrame()
        else:
            self.__capturePhysicalFrame(temporaryDirectory)

    def __capturePhysicalFrame(self,temporaryDirectory:str):
        qImage = self._backend.read() if self._backend is not None else None
        if qImage is not None:
            # backend.read() already yields a detached RGB888 QImage (freed-buffer safe).
            self.qImage = qImage

            if temporaryDirectory is not None:
                self.qImage.save(temporaryDirectory+'/test.png','PNG')

        # On a failed/empty read qImage stays as the last good frame; always advance the burst.
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






