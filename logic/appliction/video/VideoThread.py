import cv2
from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QImage
from model.application.video.VideoSignal import VideoSignal


class VideoThread(QThread):
    videoSignal = pyqtSignal(VideoSignal)
    qImage: QImage

    def __init__(self):
        super().__init__()
        self._runFlag = True
        self.cap = None
        self.qImage = None

        self._frameCount = 0
        self._currentFrameCount = 0

    def setFrameCount(self, spectraCount: int):
        self._frameCount = spectraCount

    def getFrameCount(self):
        return self._frameCount

    def __setCurrentFrameCount(self, currentCount: int):
        self._currentFrameCount = currentCount

    def __getCurrentFrameCount(self):
        return self._currentFrameCount

    def run(self):

        # device = QCamera()
        # videoInputs = QMediaDevices.videoInputs()
        # for cameraDevice in videoInputs:
        #     cameraName=cameraDevice.description()
        #     print(cameraName)
        #     cameraId=cameraDevice.id()
        #     print("cameraDevice.position()")
        #     print(cameraDevice.position())
        #
        #     print("cameraDevice.photoResolutions()")
        #     print(cameraDevice.photoResolutions())
        #
        #     print(cameraId)
        #     cameraDeviceFormats=cameraDevice.videoFormats()
        #     print(cameraDeviceFormats)
        #     for cameraDeviceFormat in cameraDeviceFormats:
        #         print(cameraDeviceFormat.resolution())
        #         print(cameraDeviceFormat.pixelFormat())

        # self.cap = cv2.VideoCapture(4)
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

                if self.doesEmitVideoSignal():
                    videoSignal = VideoSignal()
                    videoSignal.image = self.qImage
                    self.videoSignal.emit(videoSignal)

        self.cap.release()

    def stop(self):
        self._runFlag = False
        self.__setCurrentFrameCount(0)

    def beforeCapture(self):
        pass

    def afterCapture(self):
        frameCount = self.getFrameCount()
        if frameCount > 0:
            self.__setCurrentFrameCount(self.__getCurrentFrameCount() + 1)
            currentCount = self.__getCurrentFrameCount()
            if currentCount == frameCount:
                self._runFlag = False
                self.__setCurrentFrameCount(0)

    def doesEmitVideoSignal(self):
        return True
