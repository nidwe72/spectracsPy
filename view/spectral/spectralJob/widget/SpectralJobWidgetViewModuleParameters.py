from chromos.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType


class SpectralJobWidgetViewModuleParameters:

    def __init__(self):
        self.spectrumSampleType = SpectrumSampleType.UNSPECIFIED

    def setSpectrumSampleType(self, spectrumSampleType: SpectrumSampleType):
        self.spectrumSampleType = spectrumSampleType

    def getSpectrumSampleType(self):
        return self.spectrumSampleType
