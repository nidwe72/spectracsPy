from PySide6.QtCore import Qt, QEvent, QEventLoop
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics


class InWindowDialog(QWidget):
    """A dialog rendered as a STACKED-VIEW page (Edwin): an OPAQUE full-window page — title at the top,
    message/image in the body, action buttons in a full-width footer at the bottom — that visually replaces
    the current page (NOT a dimmed scrim with a floating card).

    It is technically an overlay widget on the top-level window running a nested event loop, so
    confirm()/notify()/showImage() still return synchronously (exec()-like) and never create a second
    top-level window / EGL surface (which aborts the app on Qt-for-Android, P4c) — but it LOOKS like
    navigating to another page on the stack. Drop-in for QMessageBox.question / warning / information via
    confirm() / notify(); showImage() for image help.
    """

    def __init__(self, host, title, message, buttons, pixmap=None, contentWidget=None):
        super().__init__(host)
        self.__host = host
        self.__result = None
        self.__loop = QEventLoop()

        layout = QVBoxLayout(self)
        # Page-style margins so it matches the other stacked views.
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.M)

        # A `contentWidget` fills the body (e.g. the full-size report preview) — no centering spacers, it
        # expands to the whole page. `message`/`pixmap` dialogs stay vertically centered as before (Edwin):
        # a top spacer balances the bottom one so a little block sits mid-height above the footer.
        fills = contentWidget is not None
        if not fills:
            layout.addStretch(1)

        titleLabel = QLabel(title)
        titleLabel.setProperty("style-bold", True)
        titleLabel.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(titleLabel)

        if message:
            messageLabel = QLabel(message)
            messageLabel.setWordWrap(True)
            layout.addWidget(messageLabel)

        if pixmap is not None:
            if pixmap.width() > 1000:
                pixmap = pixmap.scaledToWidth(1000, Qt.TransformationMode.SmoothTransformation)
            imageLabel = QLabel()
            imageLabel.setPixmap(pixmap)
            imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(imageLabel, 0, Qt.AlignmentFlag.AlignHCenter)

        if fills:
            layout.addWidget(contentWidget, 1)  # the content owns the body (fills to the footer)
        else:
            layout.addStretch(1)  # push the footer to the bottom (title/content top-pack like a page)

        footer = QWidget()
        footerLayout = QHBoxLayout(footer)
        footerLayout.setContentsMargins(0, 0, 0, 0)
        footerLayout.setSpacing(Metrics.S)
        for text, value, buttonType in buttons:
            button = QPushButton(text)
            if buttonType is not None:
                button.setProperty("buttonType", buttonType)
            button.clicked.connect(lambda _checked=False, v=value: self.__finish(v))
            footerLayout.addWidget(button, 1)
        layout.addWidget(footer)

    def paintEvent(self, event):
        # Opaque page background (not a translucent scrim) so it reads as a stacked view, not an overlay.
        painter = QPainter(self)
        painter.fillRect(self.rect(), ApplicationStyleLogicModule().getBackgroundColor())

    def eventFilter(self, watched, event):
        if watched is self.__host and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.__host.rect())
        return False

    def __finish(self, value):
        self.__result = value
        self.__loop.quit()

    def __run(self):
        self.setGeometry(self.__host.rect())
        self.show()
        self.raise_()
        self.__host.installEventFilter(self)  # keep the page covering the window on resize
        self.__loop.exec()
        self.__host.removeEventFilter(self)
        self.deleteLater()
        return self.__result

    @staticmethod
    def confirm(host, title, message, destructive=False):
        """Yes/No confirmation. Returns True on Yes. `destructive` makes the Yes button red."""
        window = host.window()
        yesType = "danger" if destructive else None
        dialog = InWindowDialog(window, title, message,
                                [("No", False, "secondary"), ("Yes", True, yesType)])
        return bool(dialog.__run())

    @staticmethod
    def choose(host, title, message, buttons):
        """Generic in-window chooser with custom button labels. `buttons` = list of
        (text, value, buttonType); returns the chosen value (exec()-like)."""
        window = host.window()
        return InWindowDialog(window, title, message, buttons).__run()

    @staticmethod
    def notify(host, title, message):
        """One-shot message (replacement for QMessageBox.warning / information)."""
        window = host.window()
        InWindowDialog(window, title, message, [("OK", None, None)]).__run()

    @staticmethod
    def showImage(host, title, pixmap):
        """One-shot image help, in-window (replacement for a QDialog that shows a QPixmap)."""
        window = host.window()
        InWindowDialog(window, title, None, [("OK", None, None)], pixmap=pixmap).__run()

    @staticmethod
    def showWidget(host, title, contentWidget):
        """One-shot full-window view of an arbitrary widget (e.g. the report preview at full size). The
        widget fills the body above a Close footer."""
        window = host.window()
        InWindowDialog(window, title, None, [("Close", None, None)], contentWidget=contentWidget).__run()
