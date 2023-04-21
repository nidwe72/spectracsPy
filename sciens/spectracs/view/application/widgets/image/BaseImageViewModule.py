from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGridLayout, QGraphicsView, QFrame

from spectracs.view.application.widgets.graphicsScene.BaseGraphicsPixmapItem import BaseGraphicsPixmapItem
from spectracs.view.application.widgets.graphicsScene.BaseGraphicsScene import BaseGraphicsScene


class BaseImageViewModule(QFrame):

    imageItem:BaseGraphicsPixmapItem = None
    graphicsView:QGraphicsView = None
    imageItem:BaseGraphicsPixmapItem=None
    videoWidget:QGraphicsView = None

    def setImage(self, image: QImage):
        scene=self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)
        self._fitInView()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)
        self.graphicsView = QGraphicsView()

        self.videoWidget = QGraphicsView()
        layout.addWidget(self.videoWidget, 0, 0, 1, 1)

        self.scene = BaseGraphicsScene()
        self.initialize()
        self.videoWidget.setScene(self.scene)

    def initialize(self):
        self.imageItem = BaseGraphicsPixmapItem()
        self.scene.addItem(self.imageItem)

    def resizeEvent(self, resizeEvent: QtGui.QResizeEvent) -> None:
        super().resizeEvent(resizeEvent)
        self.videoWidget.resizeEvent(resizeEvent)
        self._fitInView()

    def _fitInView(self):
        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)
