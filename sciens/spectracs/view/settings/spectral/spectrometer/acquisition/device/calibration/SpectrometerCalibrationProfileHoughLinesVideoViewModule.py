from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPen, QBrush

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from spectracs.view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from spectracs.view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule



class SpectrometerCalibrationProfileHoughLinesVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):

    upperHoughLineItem:BaseGraphicsLineItem=None
    lowerHoughLineItem: BaseGraphicsLineItem = None
    centerHoughLineItem: BaseGraphicsLineItem = None

    leftBoundingLineItem: BaseGraphicsLineItem = None
    rightBoundingLineItem: BaseGraphicsLineItem = None

    calibrationStepUpperHoughLineItem:BaseGraphicsLineItem=None
    calibrationStepLowerHoughLineItem: BaseGraphicsLineItem = None
    calibrationStepCenterHoughLineItem: BaseGraphicsLineItem = None


    def handleVideoThreadSignal(self, videoSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):

        if videoSignal.currentFrameIndex==1:
            self.scene.removeItem(self.upperHoughLineItem)
            self.upperHoughLineItem=None

            self.scene.removeItem(self.lowerHoughLineItem)
            self.lowerHoughLineItem=None

            self.scene.removeItem(self.centerHoughLineItem)
            self.centerHoughLineItem=None

            self.scene.removeItem(self.calibrationStepUpperHoughLineItem)
            self.calibrationStepUpperHoughLineItem=None

            self.scene.removeItem(self.calibrationStepLowerHoughLineItem)
            self.calibrationStepLowerHoughLineItem=None

            self.scene.removeItem(self.calibrationStepCenterHoughLineItem)
            self.calibrationStepLowerHoughLineItem=None

            self.scene.removeItem(self.leftBoundingLineItem)
            self.leftBoundingLineItem=None

            self.scene.removeItem(self.rightBoundingLineItem)
            self.rightBoundingLineItem=None

        image = videoSignal.image
        scene = self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)


        self.__getCalibrationStepUpperHoughLineItem().setLine(videoSignal.calibrationStepUpperHoughLine.p1().x(),
                                                              videoSignal.calibrationStepUpperHoughLine.p1().y(),
                                                              videoSignal.calibrationStepUpperHoughLine.p2().x(),
                                                              videoSignal.calibrationStepUpperHoughLine.p2().y())

        self.__getCalibrationStepLowerHoughLineItem().setLine(videoSignal.calibrationStepLowerHoughLine.p1().x(),
                                                              videoSignal.calibrationStepLowerHoughLine.p1().y(),
                                                              videoSignal.calibrationStepLowerHoughLine.p2().x(),
                                                              videoSignal.calibrationStepLowerHoughLine.p2().y())

        self.__getCalibrationStepCenterHoughLineItem().setLine(videoSignal.calibrationStepCenterHoughLine.p1().x(),
                                                              videoSignal.calibrationStepCenterHoughLine.p1().y(),
                                                              videoSignal.calibrationStepCenterHoughLine.p2().x(),
                                                              videoSignal.calibrationStepCenterHoughLine.p2().y())

        self.__getUpperHoughLineItem().setLine(videoSignal.upperHoughLine.p1().x(),
                                                              videoSignal.upperHoughLine.p1().y(),
                                                              videoSignal.upperHoughLine.p2().x(),
                                                              videoSignal.upperHoughLine.p2().y())

        self.__getLowerHoughLineItem().setLine(videoSignal.lowerHoughLine.p1().x(),
                                                              videoSignal.lowerHoughLine.p1().y(),
                                                              videoSignal.lowerHoughLine.p2().x(),
                                                              videoSignal.lowerHoughLine.p2().y())

        self.__getCenterHoughLineItem().setLine(videoSignal.centerHoughLine.p1().x(),
                                                              videoSignal.centerHoughLine.p1().y(),
                                                              videoSignal.centerHoughLine.p2().x(),
                                                              videoSignal.centerHoughLine.p2().y())

        if videoSignal.leftBoundingLine is not None:
            self.__getLeftBoundingLineItem().setLine(videoSignal.leftBoundingLine.p1().x(),
                                                                  videoSignal.leftBoundingLine.p1().y(),
                                                                  videoSignal.leftBoundingLine.p2().x(),
                                                                  videoSignal.leftBoundingLine.p2().y())

        if videoSignal.rightBoundingLine is not None:
            self.__getRightBoundingLineItem().setLine(videoSignal.rightBoundingLine.p1().x(),
                                                                  videoSignal.rightBoundingLine.p1().y(),
                                                                  videoSignal.rightBoundingLine.p2().x(),
                                                                  videoSignal.rightBoundingLine.p2().y())


        if videoSignal.currentFrameIndex>videoSignal.framesCount-1:
            self.scene.removeItem(self.calibrationStepUpperHoughLineItem)
            self.scene.removeItem(self.calibrationStepLowerHoughLineItem)
            self.scene.removeItem(self.calibrationStepCenterHoughLineItem)

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)

    def initialize(self):
        super().initialize()

    def __getUpperHoughLineItem(self):
        if self.upperHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 4)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.upperHoughLineItem = BaseGraphicsLineItem()
            self.upperHoughLineItem.itemName='upperHoughLine'
            self.upperHoughLineItem.setPen(pen)
            self.scene.addItem(self.upperHoughLineItem)
        return self.upperHoughLineItem

    def __getLowerHoughLineItem(self):
        if self.lowerHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 4)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.lowerHoughLineItem = BaseGraphicsLineItem()
            self.lowerHoughLineItem.itemName='lowerHoughLine'
            self.lowerHoughLineItem.setPen(pen)
            self.scene.addItem(self.lowerHoughLineItem)
        return self.lowerHoughLineItem

    def __getCenterHoughLineItem(self):
        if self.centerHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 6)
            self.centerHoughLineItem = BaseGraphicsLineItem()
            self.centerHoughLineItem.itemName='centerHoughLine'
            self.centerHoughLineItem.setPen(pen)
            self.scene.addItem(self.centerHoughLineItem)
        return self.centerHoughLineItem

    def __getCalibrationStepUpperHoughLineItem(self):
        if self.calibrationStepUpperHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 2)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.calibrationStepUpperHoughLineItem = BaseGraphicsLineItem()
            self.calibrationStepUpperHoughLineItem.itemName='calibrationStepUpperHoughLine'
            self.calibrationStepUpperHoughLineItem.setPen(pen)
            self.scene.addItem(self.calibrationStepUpperHoughLineItem)
        return self.calibrationStepUpperHoughLineItem

    def __getCalibrationStepLowerHoughLineItem(self):
        if self.calibrationStepLowerHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 2)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.calibrationStepLowerHoughLineItem = BaseGraphicsLineItem()
            self.calibrationStepLowerHoughLineItem.itemName='calibrationStepLowerHoughLine'
            self.calibrationStepLowerHoughLineItem.setPen(pen)
            self.scene.addItem(self.calibrationStepLowerHoughLineItem)
        return self.calibrationStepLowerHoughLineItem

    def __getCalibrationStepCenterHoughLineItem(self):
        if self.calibrationStepCenterHoughLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 2)
            self.calibrationStepCenterHoughLineItem = BaseGraphicsLineItem()
            self.calibrationStepCenterHoughLineItem.itemName='calibrationStepCenterHoughLine'
            self.calibrationStepCenterHoughLineItem.setPen(pen)
            self.scene.addItem(self.calibrationStepCenterHoughLineItem)
        return self.calibrationStepCenterHoughLineItem

    def __getLeftBoundingLineItem(self):
        if self.leftBoundingLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 4)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.leftBoundingLineItem = BaseGraphicsLineItem()
            self.leftBoundingLineItem.itemName='leftBoundingLine'
            self.leftBoundingLineItem.setPen(pen)
            self.scene.addItem(self.leftBoundingLineItem)
        return self.leftBoundingLineItem

    def __getRightBoundingLineItem(self):
        if self.rightBoundingLineItem is None:
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 4)
            pen.setStyle(Qt.PenStyle.DotLine)
            self.rightBoundingLineItem = BaseGraphicsLineItem()
            self.rightBoundingLineItem.itemName='rightBoundingLine'
            self.rightBoundingLineItem.setPen(pen)
            self.scene.addItem(self.rightBoundingLineItem)
        return self.rightBoundingLineItem

