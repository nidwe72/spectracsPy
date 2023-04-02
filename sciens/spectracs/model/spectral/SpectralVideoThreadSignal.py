from sciens.spectracs.model.application.video.VideoSignal import VideoSignal
from sciens.spectracs.model.spectral.SpectralJob import SpectralJob


class SpectralVideoThreadSignal(VideoSignal):
    spectralJob: SpectralJob

