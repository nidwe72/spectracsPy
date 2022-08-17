from typing import Generic, TypeVar

import cv2
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage

S = TypeVar('S')

class VideoThread(QThread,Generic[S]):

    #videoThreadSignal = pyqtSignal(threading.Event, S)
    qImage: QImage

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

    def run(self):

        self.onStart()

        self.cap = cv2.VideoCapture(0)

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # bar=cv2.VideoWriter.get(cv2.VIDEOWRITER_PROP_HW_DEVICE)
        # print(bar)

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        # self.cap.set(cv2.CAP_PROP_EXPOSURE, 150)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, 300)
        # foo=""
        # foo=self.cap.get(cv2.CAP_PROP_EXPOSURE)
        # print(foo)
        # print(fourcc)

        while self._runFlag:

            self.beforeCapture()

            ret, frame = self.cap.read()
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                # needs QImage.Format.Format_RGB888 or crashes for some reason after some frames
                self.qImage = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)
                # self.onCapturedFrame(qImage)

                self.afterCapture()

        self._setCurrentFrameIndex(0)
        self.cap.release()

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
            if currentCount == frameCount:
                self._runFlag = False

    def createSignal(self)->S:
        return None

    def onStart(self):
        return None






