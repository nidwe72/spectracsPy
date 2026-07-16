from PySide6.QtCore import QLine, QPoint
from PySide6.QtGui import qGray

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.application.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal

class SpectrometerRegionOfInterestLogicModule(Singleton):
    pass

    def getHorizontalBoundingLines(self, videoSignal:SpectrometerCalibrationProfileHoughLinesVideoSignal):
        houghLineLogicModule = HoughLineLogicModule()
        houghLines = houghLineLogicModule.getHoughLines(videoSignal.image)
        return houghLines;


    def getVerticalBoundingLines(self, videoSignal:SpectrometerCalibrationProfileHoughLinesVideoSignal):
        image = videoSignal.image
        upperLine = videoSignal.upperHoughLine.y1()
        lowerLine = videoSignal.lowerHoughLine

        y2 = videoSignal.upperHoughLine.y2()
        y1 = videoSignal.lowerHoughLine.y1()

        y = int(y1 + (y2 - y1) / 2.0)

        threshold = 20
        x1=0
        for x in range(1,image.width()):
            if self.__columnBrightness(image, x, y) > threshold:
                x1=x
                break

        x2 = image.width()
        for x in reversed(range(1,image.width())):
            if self.__columnBrightness(image, x, y) > threshold:
                x2=x
                break

        leftBoundingLine=QLine()
        leftBoundingLine.setP1(QPoint(x1, 0))
        leftBoundingLine.setP2(QPoint(x1, image.height()))
        videoSignal.leftBoundingLine=leftBoundingLine

        rightBoundingLine=QLine()
        rightBoundingLine.setP1(QPoint(x2, 0))
        rightBoundingLine.setP2(QPoint(x2, image.height()))
        videoSignal.rightBoundingLine = rightBoundingLine

    def __columnBrightness(self, image, x, yCenter):
        # Brightest CHANNEL over a small vertical window — NOT qGray. Luminance under-weights blue
        # (~5/32), so a visible blue CFL line reads as low gray and was skipped, clipping the ROI's left
        # bound. max(r,g,b) matches the auto-exposure metric, so a line auto-exposure kept is also seen
        # here; the ±2-row window tolerates a line that does not cross the exact centre row.
        best = 0
        height = image.height()
        for dy in (-2, -1, 0, 1, 2):
            yy = yCenter + dy
            if 0 <= yy < height:
                color = image.pixelColor(x, yy)
                channelMax = max(color.red(), color.green(), color.blue())
                if channelMax > best:
                    best = channelMax
        return best



