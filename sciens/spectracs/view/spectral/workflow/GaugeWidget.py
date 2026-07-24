from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from sciens.spectracs.model.spectral.plugin.view.GaugeRender import GaugeRender
from sciens.spectracs.plugin_sdk.util.GaugeColorUtil import GaugeColorUtil

_CHIP_RADIUS = 6    # shared rounded-corner radius for the swatch chip and the verdict pill (Edwin 2026-07-24)
_CHIP_HEIGHT = 28   # shared height so the verdict pill is exactly as tall as the swatch chip (Edwin 2026-07-24)
HEADLINE_HEIGHT = 40  # LIMS Option B: the big pill / zone bar / "Verdict" chip all share this height (Edwin)


def _classColors(view, util):
    colors = {"text": "#DDDDDD", "bg": "#404040"}
    if view.classes and view.thresholds is not None and view.bandLeft is not None:
        index = util.classify(view.value, view.thresholds, view.bandLeft, view.bandRight)
        index = max(0, min(index, len(view.classes) - 1))
        colors = {**colors, **view.classes[index].get("colors", {})}
    return colors


class _GaugeBandBar(QWidget):
    # SPEC_roast_ampel.md §8.4 — the gradient band + value marker + threshold tick(s). Square corners, top-
    # aligned. A value past an edge clamps the marker to that edge (RD#5); the dashed light tick marks each
    # threshold so the reader sees the distance to the decision line (Option A).

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
        rect = self.rect().adjusted(0, 0, -1, -1)

        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        for pos, hexColor in self.__util.gradientStops(view.gradientAnchors, view.bandLeft, view.bandRight, 32):
            gradient.setColorAt(pos, QColor(hexColor))
        painter.setPen(QPen(QColor("#5A5A5A"), 1))
        painter.setBrush(QBrush(gradient))
        painter.drawRect(rect)

        # threshold tick(s): a thin dashed light line at each decision boundary
        for t in (view.thresholds or []):
            tx = rect.left() + self.__util.positionOf(t, view.bandLeft, view.bandRight) * rect.width()
            painter.setPen(QPen(QColor("#EAEAEA"), 1.4, Qt.PenStyle.DashLine))
            painter.drawLine(int(tx), rect.top(), int(tx), rect.bottom())

        # value marker: solid dark line + white dot
        markerPos = self.__util.positionOf(view.value, view.bandLeft, view.bandRight)
        markerX = rect.left() + markerPos * rect.width()
        painter.setPen(QPen(QColor("#111111"), 2))
        painter.drawLine(int(markerX), rect.top(), int(markerX), rect.bottom())
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(markerX - 5, rect.center().y() - 5, 10, 10))
        painter.end()


class _GaugeZoneBar(QWidget):
    # SPEC_roast_ampel.md §8.4 (ZONES, Option B) — a COARSE verdict bar: n+1 class-coloured segments of EQUAL
    # width (symbolic, D-zones-split), threshold(s) at the joins, and a marker at the value's depth within its
    # own class. Jitter-tolerant — a ±5% value wobble barely moves the marker and never crosses a join unless
    # the verdict itself changes.

    def __init__(self, view):
        super().__init__()
        self.__view = view
        self.__util = GaugeColorUtil()
        self.setMinimumHeight(_CHIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        view = self.__view
        util = self.__util
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        n = len(view.classes) or 1
        segW = rect.width() / n
        for i in range(n):
            colors = view.classes[i].get("colors", {}) if i < len(view.classes) else {}
            fill = colors.get("zone", colors.get("bg", "#888888"))   # zone matches its verdict badge (bg)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(fill)))
            painter.drawRect(QRectF(rect.left() + i * segW, rect.top(), segW, rect.height()))
        # threshold dividers at each join
        painter.setPen(QPen(QColor("#EAEAEA"), 2))
        for i in range(1, n):
            x = rect.left() + i * segW
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())
        # marker
        mp = util.zoneMarkerPosition(view.value, view.thresholds, view.bandLeft, view.bandRight)
        mx = rect.left() + mp * rect.width()
        painter.setPen(QPen(QColor("#111111"), 1.5))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(mx - 6, rect.center().y() - 6, 12, 12))
        painter.end()


class GaugeWidget(QWidget):
    # Composes the render-flagged components of a VerdictGaugeView (§8.4). Two layouts: with BAND = the precise
    # metric row (band + swatch + inline pill, Option A); without BAND = the headline (a BIG pill + coarse zone
    # bar, Option B). The caption is the host-drawn label chip in the row layout, so it is not drawn here.

    def __init__(self, view):
        super().__init__()
        util = GaugeColorUtil()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        components = view.render
        headline = GaugeRender.BAND not in components   # LIMS-style verdict headline: big pill, no fine band

        if GaugeRender.BAND in components and view.gradientAnchors:
            layout.addWidget(_GaugeBandBar(view))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        hasExpanding = False

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
            colors = _classColors(view, util)
            pill = QLabel(view.verdictLabel.upper())
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if headline:                                  # BIG headline pill (Option B) — fills the width
                pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                pill.setFixedHeight(HEADLINE_HEIGHT)
                pill.setStyleSheet(
                    "background-color: %s; color: %s; border-radius: 8px; padding: 0px 20px;"
                    " font-weight: bold; font-size: 15px;" % (colors["bg"], colors["text"]))
                hasExpanding = True
            else:                                         # inline pill (Option A); fills the value column
                pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                pill.setFixedHeight(_CHIP_HEIGHT)
                pill.setStyleSheet(
                    "background-color: %s; color: %s; border-radius: %dpx; padding: 0px 10px;"
                    " font-weight: bold; font-size: 11px;" % (colors["bg"], colors["text"], _CHIP_RADIUS))
                hasExpanding = True
            row.addWidget(pill)

        if GaugeRender.ZONES in components:
            zoneBar = _GaugeZoneBar(view)
            if headline:                                  # secondary, same height as the badge (Edwin 2026-07-24)
                zoneBar.setFixedSize(210, HEADLINE_HEIGHT)
                row.addWidget(zoneBar)
            else:
                row.addWidget(zoneBar)
                hasExpanding = True

        if GaugeRender.VALUE in components:
            value = QLabel(self.__valueText(view))
            value.setStyleSheet("font-weight: bold; font-size: 15px;")
            row.addWidget(value)

        if not hasExpanding:
            row.addStretch(1)
        layout.addLayout(row)

    @staticmethod
    def __valueText(view):
        try:
            return "%.2f" % float(view.value)
        except (TypeError, ValueError):
            return str(view.value)
