from PySide6.QtCore import QLine

from sciens.spectracs.model.application.video.VideoSignal import VideoSignal


class SpectrometerCalibrationProfileHoughLinesVideoSignal(VideoSignal):

    lowerHoughLine:QLine=None
    upperHoughLine: QLine = None
    centerHoughLine: QLine = None

    calibrationStepLowerHoughLine:QLine=None
    calibrationStepUpperHoughLine: QLine = None
    calibrationStepCenterHoughLine: QLine = None

    leftBoundingLine: QLine = None
    rightBoundingLine: QLine = None





