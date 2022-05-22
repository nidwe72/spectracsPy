from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from model.spectral.SpectralJob import SpectralJob
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

import cv2
import threading
from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QImage
from model.spectral.SpectrumSampleType import SpectrumSampleType


class SpectrumVideoThread(QThread):

    #spectralVideoThreadSignal = pyqtSignal(SpectralVideoThreadSignal)
    spectralVideoThreadSignal = pyqtSignal(threading.Event, SpectralVideoThreadSignal)

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

    def __setCurrentFrameIndex(self, currentCount: int):
        self._currentFrameIndex = currentCount

    def __getCurrentFrameIndex(self):
        return self._currentFrameIndex

    def run(self):

        self.spectralJob = SpectralJob()

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
                self.spectralJob.title = "title"

                spectralVideoThreadSignalModel = SpectralVideoThreadSignal()
                spectralVideoThreadSignalModel.image=self.qImage
                spectralVideoThreadSignalModel.spectralJob = self.spectralJob
                spectralVideoThreadSignalModel.framesCount=self.getFrameCount()
                spectralVideoThreadSignalModel.currentFrameIndex=self.__getCurrentFrameIndex()

                imageToSpectrumLogicModule=ImageSpectrumAcquisitionLogicModule()
                spectrum=imageToSpectrumLogicModule.acquire(self.qImage)

                spectrum.setSampleType(self.getSpectrumSampleType())
                self.spectralJob.addSpectrum(spectrum)

                event = threading.Event()
                self.spectralVideoThreadSignal.emit(event,spectralVideoThreadSignalModel)
                event.wait()

        self.__setCurrentFrameIndex(0)
        self.cap.release()

    def stop(self):
        self._runFlag = False
        self.__setCurrentFrameIndex(0)

    def beforeCapture(self):
        pass

    def afterCapture(self):
        frameCount = self.getFrameCount()
        if frameCount > 0:
            self.__setCurrentFrameIndex(self.__getCurrentFrameIndex() + 1)
            currentCount = self.__getCurrentFrameIndex()
            if currentCount == frameCount:
                self._runFlag = False


    def setSpectrumSampleType(self,spectrumSampleType:SpectrumSampleType):
        self.spectrumSampleType=spectrumSampleType

    def getSpectrumSampleType(self):
        return self.spectrumSampleType




