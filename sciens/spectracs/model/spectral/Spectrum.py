from typing import List, Dict

from PySide6.QtGui import QColor

from sciens.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType


class Spectrum:
    valuesByNanometers: Dict[int, float] = None

    __colorsByPixelIndices: Dict[int, QColor] = None

    __capturedValuesByNanometers: List[Dict[int, float]] = []

    def __init__(self):
        self.sampleType = SpectrumSampleType.SAMPLE
        self.valuesByNanometers=[]

    def setValuesByNanometers(self, valuesByNanometers):
        self.valuesByNanometers = valuesByNanometers

    def getSampleType(self):
        return self.sampleType

    def setSampleType(self, sampleType):
        self.sampleType = sampleType

    def getCapturedValuesByNanometers(self) -> List[Dict[int, float]]:
        return self.__capturedValuesByNanometers

    def addToCapturedValuesByNanometers(self, capturedValuesByNanometers: Dict[int, float]):
        self.__capturedValuesByNanometers.append(capturedValuesByNanometers)

    def getColorsByPixelIndices(self):
        return self.__colorsByPixelIndices

    def setColorsByPixelIndices(self, colorsByPixelIndices):
        self.__colorsByPixelIndices = colorsByPixelIndices
