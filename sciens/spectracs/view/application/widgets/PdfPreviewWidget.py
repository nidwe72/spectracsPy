from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame

from sciens.spectracs.logic.appliction.style.Metrics import Metrics


class PdfPreviewWidget(QScrollArea):
    # SPEC_bench_pdf_export.md §1 — a vertical, fit-to-width preview of the report pages (each rendered page is
    # a QPixmap). Pages scale to the available viewport width preserving aspect, so at phone width (--phone) the
    # preview no longer overflows into a horizontal scrollbar; only a vertical scrollbar appears when the stacked
    # pages exceed the height. Rescales on resize. Never upscales past a page's native pixels (keeps it crisp).
    #
    # ZERO horizontal padding (Edwin): the preview is the whole point of the tab, so pages hug the full available
    # width. Only a small VERTICAL gap separates stacked pages (costs no width). For a bigger look on a small
    # device, the host offers an "Open bigger" full-window view (SPEC §1) — no need to reclaim the last few px.

    def __init__(self, pixmaps, parent=None):
        super().__init__(parent)
        self.__pixmaps = list(pixmaps)
        self.__labels = []
        self.__lastWidth = -1

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)  # no frame border → the preview sits flush
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # fit width → never scroll H
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)             # no padding — pages span the full width
        layout.setSpacing(Metrics.S)                      # vertical-only gap between stacked pages
        container.setLayout(layout)
        for _ in self.__pixmaps:
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(label)
            self.__labels.append(label)
        layout.addStretch(1)
        self.setWidget(container)

    def showEvent(self, event):
        super().showEvent(event)
        self.__rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__rescale()

    def __rescale(self):
        # Available content width = the full viewport (no L/R padding, no H scrollbar to subtract).
        width = self.viewport().width()
        if width <= 0 or width == self.__lastWidth:
            return
        self.__lastWidth = width
        for label, pixmap in zip(self.__labels, self.__pixmaps):
            target = min(width, pixmap.width())  # don't upscale past native → stays sharp on wide screens
            label.setPixmap(pixmap.scaledToWidth(target, Qt.TransformationMode.SmoothTransformation))
