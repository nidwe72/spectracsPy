from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor

from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule


class SpectrometerCalibrationProfileHoughLinesVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):

    upperHoughLineItem:BaseGraphicsLineItem=None
    lowerHoughLineItem: BaseGraphicsLineItem = None

    def handleVideoSignal(self, videoSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):
        image = videoSignal.image
        scene = self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        self.__getUpperHoughLineItem().setLine(videoSignal.upperHoughLine.p1().x(),videoSignal.upperHoughLine.p1().y(),
                                        videoSignal.upperHoughLine.p2().x(),videoSignal.upperHoughLine.p2().y())

        self.__getLowerHoughLineItem().setLine(videoSignal.lowerHoughLine.p1().x(),videoSignal.lowerHoughLine.p1().y(),
                                        videoSignal.lowerHoughLine.p2().x(),videoSignal.lowerHoughLine.p2().y())

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)

    def initialize(self):
        super().initialize()

    def __getUpperHoughLineItem(self):
        if self.upperHoughLineItem is None:
            pen = QPen(QBrush(QColor(200, 200, 200, 255)), 1)
            self.upperHoughLineItem = BaseGraphicsLineItem()
            self.upperHoughLineItem.itemName='upperHoughLine'
            self.upperHoughLineItem.setPen(pen)
            self.scene.addItem(self.upperHoughLineItem)
        return self.upperHoughLineItem

    def __getLowerHoughLineItem(self):
        if self.lowerHoughLineItem is None:
            pen = QPen(QBrush(QColor(200, 200, 200, 255)), 1)
            self.lowerHoughLineItem = BaseGraphicsLineItem()
            self.lowerHoughLineItem.itemName='upperHoughLine'
            self.lowerHoughLineItem.setPen(pen)
            self.scene.addItem(self.lowerHoughLineItem)
        return self.lowerHoughLineItem



