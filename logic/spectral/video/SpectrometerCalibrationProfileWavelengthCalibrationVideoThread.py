import threading

from PySide6.QtCore import Signal

from logic.appliction.video.VideoThread import VideoThread
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.SpectralJob import SpectralJob
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from model.spectral.SpectrumSampleType import SpectrumSampleType


class SpectrometerCalibrationProfileWavelengthCalibrationVideoThread(VideoThread[SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal]):

    videoThreadSignal = Signal(threading.Event, SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal)

    def createSignal(self) -> SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal:
        super().createSignal()

        self.spectralJob.title = "title"

        videoSignalModel = SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal()
        videoSignalModel.image=self.qImage
        videoSignalModel.spectralJob = self.spectralJob
        videoSignalModel.framesCount=self.getFrameCount()
        videoSignalModel.currentFrameIndex=self._getCurrentFrameIndex()

        imageToSpectrumLogicModule=ImageSpectrumAcquisitionLogicModule()
        spectrum=imageToSpectrumLogicModule.acquire(self.qImage)

        spectrum.setSampleType(SpectrumSampleType.UNSPECIFIED)
        self.spectralJob.addSpectrum(spectrum)

        return videoSignalModel

    # def setSpectrumSampleType(self,spectrumSampleType:SpectrumSampleType):
    #     self.spectrumSampleType=spectrumSampleType
    #
    # def getSpectrumSampleType(self):
    #     return self.spectrumSampleType

    def onStart(self):
        super().onStart()
        self.spectralJob=SpectralJob()

    def afterCapture(self):
        super().afterCapture()

        signal = self.createSignal()

        event = threading.Event()
        self.videoThreadSignal.emit(event,signal)
        event.wait()




