from chromos.spectracs.model.application.video.VideoSignal import VideoSignal
from chromos.spectracs.model.spectral.Spectrum import Spectrum


class ImageSpectrumAcquisitionLogicModuleParameters:
    __videoSignal: VideoSignal = None
    __spectrum: Spectrum = None
    __acquireColors: bool = False

    def getVideoSignal(self):
        return self.__videoSignal

    def setVideoSignal(self, videoSignal):
        self.__videoSignal = videoSignal
        return self

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum = spectrum

    def getAcquireColors(self):
        return self.__acquireColors

    def setAcquireColors(self, acquireColors):
        self.__acquireColors = acquireColors
