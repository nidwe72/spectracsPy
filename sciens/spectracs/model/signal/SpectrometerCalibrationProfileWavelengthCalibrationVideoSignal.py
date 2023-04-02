from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal(SpectralVideoThreadSignal):

    __spectrum:Spectrum=None

    model:SpectrometerCalibrationProfile=None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum=spectrum



