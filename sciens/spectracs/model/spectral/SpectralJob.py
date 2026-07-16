from typing import List
from typing import Dict
from PySide6.QtCore import QObject
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectralJob(QObject):
    spectraBySampleTypes: Dict[str, List[Spectrum]]

    title:str

    def __init__(self):
        self.spectraBySampleTypes = {}

    def addSpectrum(self, spectrum: Spectrum):
        spectrumSampleType = spectrum.getSampleType()
        spectraOfSampleType = self.spectraBySampleTypes.get(spectrumSampleType)
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

    def getSpectra(self,spectrumSampleType)->List[Spectrum]:
        result=None
        result = self.spectraBySampleTypes.get(spectrumSampleType)
        return result

