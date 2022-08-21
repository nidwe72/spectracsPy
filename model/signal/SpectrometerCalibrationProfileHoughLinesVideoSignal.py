from PyQt6.QtCore import QLine

from model.application.video.VideoSignal import VideoSignal


class SpectrometerCalibrationProfileHoughLinesVideoSignal(VideoSignal):

    lowerHoughLine:QLine=None
    upperHoughLine: QLine = None
    centerHoughLine: QLine = None

    calibrationStepLowerHoughLine:QLine=None
    calibrationStepUpperHoughLine: QLine = None
    calibrationStepCenterHoughLine: QLine = None





