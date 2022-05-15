from model.spectral.SpectrumSampleType import SpectrumSampleType


class Spectrum:
    valuesByNanometers: dict = None

    def __init__(self):
        self.sampleType = SpectrumSampleType.SAMPLE

    def setValuesByNanometers(self, valuesByNanometers):
        self.valuesByNanometers = valuesByNanometers

    def getSampleType(self):
        return self.sampleType

    def setSampleType(self,sampleType):
        self.sampleType=sampleType


