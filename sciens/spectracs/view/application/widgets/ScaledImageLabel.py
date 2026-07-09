from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class ScaledImageLabel(QLabel):
    # A QLabel that scales its image to the label's current width (keeping aspect ratio) on every resize, so
    # the image fits the panel — no horizontal scrollbar at narrow / phone width (SPEC_dev_measure_bench.md
    # §18/H2). Keeps the ORIGINAL pixmap and always rescales from it (never from the already-scaled one, so
    # there is no drift / feedback loop). Only scales DOWN — a small image is shown at native size.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original = None
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    def setImagePixmap(self, pixmap: QPixmap):
        self.__original = pixmap
        self.__rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__rescale()

    def __rescale(self):
        if self.__original is None:
            return
        width = max(1, self.width())
        if self.__original.width() <= width:
            self.setPixmap(self.__original)
        else:
            self.setPixmap(self.__original.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation))
