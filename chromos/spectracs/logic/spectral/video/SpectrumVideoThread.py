import threading

from PySide6.QtCore import Signal

from chromos.spectracs.logic.appliction.video.VideoThread import VideoThread
from chromos.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from chromos.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from chromos.spectracs.model.spectral.SpectralJob import SpectralJob
from chromos.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from chromos.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType



class SpectrumVideoThread(VideoThread[SpectralVideoThreadSignal]):

    videoThreadSignal = Signal(threading.Event, SpectralVideoThreadSignal)

    def createSignal(self) -> SpectralVideoThreadSignal:
        super().createSignal()

        self.spectralJob.title = "title"

        spectralVideoThreadSignalModel = SpectralVideoThreadSignal()
        spectralVideoThreadSignalModel.image=self.qImage
        spectralVideoThreadSignalModel.spectralJob = self.spectralJob
        spectralVideoThreadSignalModel.framesCount=self.getFrameCount()
        spectralVideoThreadSignalModel.currentFrameIndex=self._getCurrentFrameIndex()

        imageToSpectrumLogicModule=ImageSpectrumAcquisitionLogicModule()

        spectrum = imageToSpectrumLogicModule.execute(
            ImageSpectrumAcquisitionLogicModuleParameters().setVideoSignal(spectralVideoThreadSignalModel)).spectrum

        spectrum.setSampleType(self.getSpectrumSampleType())
        self.spectralJob.addSpectrum(spectrum)

        return spectralVideoThreadSignalModel


    def setSpectrumSampleType(self,spectrumSampleType:SpectrumSampleType):
        self.spectrumSampleType=spectrumSampleType

    def getSpectrumSampleType(self):
        return self.spectrumSampleType

    def onStart(self):
        super().onStart()
        self.spectralJob=SpectralJob()

    def afterCapture(self):
        super().afterCapture()

        signal = self.createSignal()

        event = threading.Event()
        self.videoThreadSignal.emit(event,signal)
        event.wait()




