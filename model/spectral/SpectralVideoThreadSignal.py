from PySide6.QtCore import QObject
from PySide6.QtGui import QImage

from model.application.video.VideoSignal import VideoSignal
from model.spectral.SpectralJob import SpectralJob


class SpectralVideoThreadSignal(VideoSignal):
    spectralJob: SpectralJob

