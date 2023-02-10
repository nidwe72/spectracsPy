from model.spectral.Spectrum import Spectrum

class ImageSpectrumAcquisitionLogicModuleResult:

    __spectrum:Spectrum=None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum=spectrum