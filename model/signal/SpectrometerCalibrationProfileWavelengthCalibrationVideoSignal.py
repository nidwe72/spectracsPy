from typing import Dict

from numpy import poly1d

from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal


class SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal(SpectralVideoThreadSignal):

    peakValuesByPixels:Dict[int,float]=None
    interpolationPolynomial:poly1d=None

