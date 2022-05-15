import typing
from PyQt6.QtCore import QObject
from model.spectral.Spectrum import Spectrum


class SpectralJob(QObject):
    spectraBySampleTypes: typing.Dict[str, typing.List[Spectrum]]

    title:str

    def __init__(self):
        self.spectraBySampleTypes = {}

    def addSpectrum(self, spectrum: Spectrum):
        spectrumSampleType = spectrum.getSampleType()
        spectraOfSampleType = self.spectraBySampleTypes[spectrumSampleType]
        if spectraOfSampleType is None:
            spectraOfSampleType = []
        spectraOfSampleType.append(spectrum)
        self.spectraBySampleTypes[spectrumSampleType] = spectraOfSampleType

    def getSpectrum(self,spectrumSampleType):
        result=None
        spectraOfSampleType = self.spectraBySampleTypes[spectrumSampleType]
        if isinstance(spectraOfSampleType,list):
            result=spectraOfSampleType[0]
        return result
