from PyQt6.QtCore import QObject
from PyQt6.QtGui import QImage

class VideoSignal(QObject):
    image:QImage
    currentFrameIndex:int
    framesCount:int



