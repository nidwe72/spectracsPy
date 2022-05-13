from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QThread
from model.application.video.VideoSignal import VideoSignal
from PyQt6.QtGui import QImage
import cv2

class VideoThread(QThread):

    videoSignal = pyqtSignal(VideoSignal)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.cap=None

    def run(self):

        self.cap = cv2.VideoCapture(0)
        while self._run_flag:
            ret, frame = self.cap.read()
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                # qImage = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB32)
                qImage = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)


                videoSignal= VideoSignal()
                videoSignal.image=qImage
                self.videoSignal.emit(videoSignal)

        self.cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False


