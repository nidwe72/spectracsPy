from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class ScaledImageLabel(QLabel):
    # A QLabel that scales its image to FIT the label's current size — BOTH width and height, keeping aspect
    # ratio — so the image fits the panel with no scrollbar (SPEC_dev_measure_bench.md §18/H2) AND a TALL frame
    # never overflows the available height. The width-only version showed a tall 1600x1200 raster at native
    # size when the panel was wide (maximized), pushing the ROI band below the fold so the frame looked all
    # black; fitting height too fixes that. Keeps the ORIGINAL pixmap and always rescales from it (no drift).
    #
    # Size policy is Ignored on both axes so the LAYOUT controls the label's size (add it with a stretch factor
    # so it fills the available area); the pixmap is then centred and scaled to fit.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original = None
        self.__fill = False
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)

    def setFill(self, fill=True):
        # Fill the whole label (IgnoreAspectRatio) instead of fitting with margins — for a raster/spectrum strip
        # the exact aspect is not meaningful, so filling uses the full width available (Edwin, rig cosmetic).
        self.__fill = fill
        self.__rescale()

    def setImagePixmap(self, pixmap: QPixmap):
        self.__original = pixmap
        self.__rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__rescale()

    def __rescale(self):
        if self.__original is None:
            return
        mode = Qt.AspectRatioMode.IgnoreAspectRatio if self.__fill else Qt.AspectRatioMode.KeepAspectRatio
        scaled = self.__original.scaled(self.size(), mode, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
