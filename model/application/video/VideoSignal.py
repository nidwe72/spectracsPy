from PySide6.QtCore import QObject
from PySide6.QtGui import QImage

class VideoSignal(QObject):
    image:QImage
    currentFrameIndex:int
    framesCount:int



