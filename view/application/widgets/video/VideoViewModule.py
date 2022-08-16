from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QGraphicsLineItem
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QColor

from PyQt6.QtCore import Qt

from logic.appliction.video.VideoThread import VideoThread

from model.application.video.VideoSignal import VideoSignal

class VideoViewModule(QWidget):

    videoThread:VideoThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.graphicsView=QGraphicsView()

        self.videoWidget=QGraphicsView()
        layout.addWidget(self.videoWidget, 0, 0, 1, 2)

        scene = QGraphicsScene();

        imageItem = QGraphicsPixmapItem()
        #todo: pass 'objec name'
        # imageItem.setData()
        scene.addItem(imageItem)

        pen = QPen(QBrush(QColor(200, 200, 200, 255)), 1)

        lineItem = QGraphicsLineItem()
        lineItem.setLine(0, 392, 1920, 392)
        lineItem.setPen(pen)
        scene.addItem(lineItem)

        self.videoWidget.setScene(scene)

    def setVideoThread(self,videoThread:VideoThread):
        self.videoThread=videoThread
        self.videoThread.videoSignal.connect(self.handleVideoSignal)

    def handleVideoSignal(self,videoSignal:VideoSignal):
        image = videoSignal.image
        scene=self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        item=scene.items()[1]
        item.setPixmap(somePixmap)

        self.videoWidget.fitInView(item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, resizeEvent: QtGui.QResizeEvent) -> None:
        super().resizeEvent(resizeEvent)
        self.videoWidget.resizeEvent(resizeEvent)
        scene=self.videoWidget.scene()
        item = scene.items()[1]
        self.videoWidget.fitInView(item,Qt.AspectRatioMode.KeepAspectRatio)









