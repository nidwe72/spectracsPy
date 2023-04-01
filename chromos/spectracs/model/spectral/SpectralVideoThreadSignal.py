from chromos.spectracs.model.application.video.VideoSignal import VideoSignal
from chromos.spectracs.model.spectral.SpectralJob import SpectralJob


class SpectralVideoThreadSignal(VideoSignal):
    spectralJob: SpectralJob

