from typing import Dict

from numpy import poly1d

from model.databaseEntity.spectral.device import SpectrometerProfile, SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from model.spectral.Spectrum import Spectrum


class SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal(SpectralVideoThreadSignal):

    __spectrum:Spectrum=None

    peakValuesByPixels:Dict[int,float]=None
    model:SpectrometerCalibrationProfile=None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum=spectrum



