from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QThread
from model.application.video.VideoSignal import VideoSignal
from PyQt6.QtGui import QImage
from PyQt6.QtMultimedia import QCamera
from PyQt6.QtMultimedia import QMediaDevices
import cv2

class VideoThread(QThread):

    videoSignal = pyqtSignal(VideoSignal)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.cap=None

    def run(self):

        # camera = QCamera()
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

        #self.cap = cv2.VideoCapture(4)
        self.cap = cv2.VideoCapture(0)

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # bar=cv2.VideoWriter.get(cv2.VIDEOWRITER_PROP_HW_DEVICE)
        # print(bar)

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,1)
        #self.cap.set(cv2.CAP_PROP_EXPOSURE, 150)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, 300)
        # foo=""
        # foo=self.cap.get(cv2.CAP_PROP_EXPOSURE)
        # print(foo)
        # print(fourcc)

        while self._run_flag:
            ret, frame = self.cap.read()
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                #needs QImage.Format.Format_RGB888 or crashes for some reason after some frames
                qImage = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)

                videoSignal= VideoSignal()
                videoSignal.image=qImage
                self.videoSignal.emit(videoSignal)

        self.cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False


