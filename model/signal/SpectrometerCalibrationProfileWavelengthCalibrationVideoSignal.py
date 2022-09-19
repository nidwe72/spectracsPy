from typing import Dict

from numpy import poly1d

from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal


class SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal(SpectralVideoThreadSignal):

    peakValuesByPixels:Dict[int,float]=None
    interpolationPolynomial:poly1d=None

    spectralLinesByPixelIndices: Dict[int, SpectralLine] = None

