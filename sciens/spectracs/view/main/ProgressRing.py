from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen


def drawProgressRing(pixmap, total, remaining, colour='#FFFFFF'):
    """A warm-up ring along the edge of a header icon's pixmap, filled clockwise from 12 o'clock as `remaining`
    runs down to 0 (SPEC_lamp_switch.md §16.2). Shared by the lamp and the camera icon; the glyphs are drawn at
    75 % (viewBox -4 -4 32 32), so the ring keeps a gap to them."""
    done = 0.0 if total <= 0 else min(1.0, max(0.0, (total - remaining) / float(total)))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    width = max(3, pixmap.width() // 18)
    rect = QRectF(width, width, pixmap.width() - 2 * width, pixmap.height() - 2 * width)
    painter.setPen(QPen(QColor(255, 255, 255, 60), width))
    painter.drawEllipse(rect)
    painter.setPen(QPen(QColor(colour), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(rect, 90 * 16, -int(done * 360 * 16))
    painter.end()
    return pixmap
