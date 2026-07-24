from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from sciens.spectracs.model.spectral.plugin.view.GaugeRender import GaugeRender
from sciens.spectracs.plugin_sdk.util.GaugeColorUtil import GaugeColorUtil

_CHIP_RADIUS = 6    # shared rounded-corner radius for the swatch chip and the verdict pill (Edwin 2026-07-24)
_CHIP_HEIGHT = 28   # shared height so the verdict pill is exactly as tall as the swatch chip (Edwin 2026-07-24)


class _GaugeBandBar(QWidget):
    # SPEC_roast_ampel.md §8.4 — the gradient band + marker, painted (QLinearGradient seeded from
    # GaugeColorUtil.gradientStops). A value past an edge clamps the marker to that edge (RD#5). Square corners
    # (Edwin 2026-07-24: no rounded border) and top-aligned so the band top lines up with the label chip.

    def __init__(self, view):
        super().__init__()
        self.__view = view
        self.__util = GaugeColorUtil()
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        view = self.__view
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)   # top at 0 → aligns with the label chip top

        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        for pos, hexColor in self.__util.gradientStops(view.gradientAnchors, view.bandLeft, view.bandRight, 32):
            gradient.setColorAt(pos, QColor(hexColor))
        painter.setPen(QPen(QColor("#5A5A5A"), 1))
        painter.setBrush(QBrush(gradient))
        painter.drawRect(rect)                       # square corners (no rounded border)

        markerPos = self.__util.positionOf(view.value, view.bandLeft, view.bandRight)
        markerX = rect.left() + markerPos * rect.width()
        painter.setPen(QPen(QColor("#111111"), 2))
        painter.drawLine(int(markerX), rect.top(), int(markerX), rect.bottom())
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(markerX - 5, rect.center().y() - 5, 10, 10))
        painter.end()


class GaugeWidget(QWidget):
    # Composes the render-flagged components of a VerdictGaugeView (§8.4): band+marker, swatch (value printed on
    # it), verdict pill. The app is single dark-themed, so class `colors` (hex) are used as-is. The caption is
    # the host-drawn left-column label chip, so it is not drawn here.

    def __init__(self, view):
        super().__init__()
        util = GaugeColorUtil()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        components = view.render

        if GaugeRender.BAND in components and view.gradientAnchors:
            layout.addWidget(_GaugeBandBar(view))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        fillsWidth = False

        if GaugeRender.SWATCH in components:
            swatchHex = view.swatchColor or util.gradientColorAt(view.value, view.gradientAnchors)
            swatch = QLabel(self.__valueText(view))
            swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
            swatch.setFixedSize(64, _CHIP_HEIGHT)
            swatch.setStyleSheet(
                "background-color: %s; color: %s; border: 1px solid #444; border-radius: %dpx; font-weight: bold;"
                % (swatchHex, view.valueColor or "#FFFFFF", _CHIP_RADIUS))
            row.addWidget(swatch)

        if GaugeRender.LABEL in components and view.verdictLabel:
            colors = self.__classColors(view, util)
            pill = QLabel(view.verdictLabel.upper())
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)   # consume all width
            pill.setFixedHeight(_CHIP_HEIGHT)                                            # as tall as the swatch
            pill.setStyleSheet(
                "background-color: %s; color: %s; border-radius: %dpx; padding: 0px 10px;"
                " font-weight: bold; font-size: 11px;" % (colors["bg"], colors["text"], _CHIP_RADIUS))
            row.addWidget(pill, 1)
            fillsWidth = True

        if GaugeRender.VALUE in components:
            value = QLabel(self.__valueText(view))
            value.setStyleSheet("font-weight: bold; font-size: 15px;")
            row.addWidget(value)

        if not fillsWidth:
            row.addStretch(1)
        layout.addLayout(row)

    @staticmethod
    def __valueText(view):
        try:
            return "%.2f" % float(view.value)
        except (TypeError, ValueError):
            return str(view.value)

    @staticmethod
    def __classColors(view, util):
        colors = {"text": "#DDDDDD", "bg": "#404040"}
        if view.classes and view.thresholds is not None and view.bandLeft is not None:
            index = util.classify(view.value, view.thresholds, view.bandLeft, view.bandRight)
            index = max(0, min(index, len(view.classes) - 1))
            declared = view.classes[index].get("colors", {})
            colors = {"text": declared.get("text", colors["text"]), "bg": declared.get("bg", colors["bg"])}
        return colors
