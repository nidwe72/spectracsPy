from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


# The Spectracs wordmark's aspect ratio (native SVG viewBox 160.33255 / 15.725352 ≈ 10.2 : 1).
LOGO_ASPECT = 160.33255 / 15.725352


def renderLogoPixmap(svgString, height):
    """Render a wordmark SVG string into a transparent, aspect-correct QPixmap `height` px tall.

    Shared by MainStatusBarViewModule (the header logo) and DocCoverViewModule (the doc-mode
    title card), so the logo has ONE renderer (SPEC_doc_automation §18.1, C1a). Pure/side-effect
    free — takes the SVG source in, hands a pixmap back.
    """
    width = max(1, int(height * LOGO_ASPECT))
    pixmap = QPixmap(width, int(height))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer = QSvgRenderer()
    renderer.load(bytearray(svgString, "utf-8"))
    renderer.render(painter, pixmap.rect())
    painter.end()
    return pixmap
