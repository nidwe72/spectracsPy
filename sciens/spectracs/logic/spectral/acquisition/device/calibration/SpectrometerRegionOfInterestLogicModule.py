from PySide6.QtCore import QLine, QPoint
from PySide6.QtGui import qGray

from base.Singleton import Singleton
from sciens.spectracs.logic.appliction.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
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

        x1=0
        for x in range(1,image.width()):
            color = image.pixelColor(x,y)
            gray=qGray(color.red(),color.green(),color.green())
            if gray>20:
                x1=x
                break

        x2 = image.width()
        for x in reversed(range(1,image.width())):
            color = image.pixelColor(x,y)
            gray=qGray(color.red(),color.green(),color.green())
            if gray>20:
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



