from PyQt6.QtCore import QObject
from PyQt6.QtGui import QImage
from model.spectral.SpectralJob import SpectralJob


class SpectralJobSignal(QObject):
    spectralJob: SpectralJob
    image:QImage
