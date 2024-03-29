from typing import TypeVar, Generic

from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import QWidget, QGridLayout, QGraphicsView, QFrame

from sciens.spectracs.view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from sciens.spectracs.view.application.widgets.graphicsScene.BaseGraphicsPixmapItem import BaseGraphicsPixmapItem
from sciens.spectracs.view.application.widgets.graphicsScene.BaseGraphicsScene import BaseGraphicsScene

VIDEO_SIGNAL = TypeVar('VIDEO_SIGNAL')

class BaseVideoViewModule(QFrame,Generic[VIDEO_SIGNAL]):

    def handleVideoThreadSignal(self, videoSignal:VIDEO_SIGNAL):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.graphicsView=QGraphicsView()

        self.videoWidget=QGraphicsView()
        layout.addWidget(self.videoWidget, 0, 0, 1, 1)

        #scene = QGraphicsScene();
        self.scene = BaseGraphicsScene()

        self.initialize()

        self.videoWidget.setScene(self.scene)

    def initialize(self):

        #imageItem = QGraphicsPixmapItem()
        self.imageItem = BaseGraphicsPixmapItem()
        #todo: pass 'objec name'
        # imageItem.setData()
        self.scene.addItem(self.imageItem)

        #pen = QPen(QBrush(QColor(200, 200, 200, 255)), 1)
        # lineItem = BaseGraphicsLineItem()
        # lineItem.setLine(0, 392, 1920, 392)
        # lineItem.setPen(pen)
        # self.scene.addItem(lineItem)

    def resizeEvent(self, resizeEvent: QtGui.QResizeEvent) -> None:
        super().resizeEvent(resizeEvent)
        self.videoWidget.resizeEvent(resizeEvent)
        self._fitInView()

    def _fitInView(self):
        self.videoWidget.fitInView(self.imageItem,Qt.AspectRatioMode.KeepAspectRatio)








