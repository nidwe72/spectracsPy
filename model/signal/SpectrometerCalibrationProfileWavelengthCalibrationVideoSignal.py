from typing import Dict
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal


class SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal(SpectralVideoThreadSignal):

    peakValuesByPixels:Dict[int,float]=None

