from PySide6.QtCore import Qt, QEvent, QEventLoop, QSize
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QWidget, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy)

from sciens.spectracs.logic.appliction.style.Metrics import Metrics


class InWindowDialog(QWidget):
    """A modal-looking dialog that lives INSIDE the top-level window — a dimmed scrim over the page
    plus a centered themed card with a title, message and buttons.

    Unlike QMessageBox/QDialog it never creates a second top-level window / EGL surface, which aborts
    the app on Qt-for-Android ("Failed to acquire deadlock protector … eglSurface()", P4c). It runs a
    nested event loop for a synchronous, exec()-like result, so call sites read naturally. Used on both
    desktop and Android (one code path, one themed look). Drop-in for QMessageBox.question /
    warning / information via confirm() / notify(). See docs/SPEC_android_port.md §P4c.
    """

    def __init__(self, host, title, message, buttons):
        super().__init__(host)
        self.__host = host
        self.__result = None
        self.__loop = QEventLoop()

        layout = QGridLayout(self)
        layout.setContentsMargins(Metrics.XL, Metrics.XL, Metrics.XL, Metrics.XL)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(2, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)

        card = QFrame()
        card.setObjectName("inWindowDialogCard")
        card.setStyleSheet("#inWindowDialogCard { background: #353535; border: 1px solid #5A5A5A;"
                           " border-radius: 6px; }")
        card.setMaximumWidth(520)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(card, 1, 1, 1, 1)

        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(Metrics.L, Metrics.L, Metrics.L, Metrics.L)
        cardLayout.setSpacing(Metrics.M)

        titleLabel = QLabel(title)
        titleLabel.setProperty("style-bold", True)
        cardLayout.addWidget(titleLabel)

        messageLabel = QLabel(message)
        messageLabel.setWordWrap(True)
        cardLayout.addWidget(messageLabel)

        buttonRow = QHBoxLayout()
        buttonRow.setSpacing(Metrics.S)
        buttonRow.addStretch(1)
        for text, value, buttonType in buttons:
            button = QPushButton(text)
            if buttonType is not None:
                button.setProperty("buttonType", buttonType)
            button.clicked.connect(lambda _checked=False, v=value: self.__finish(v))
            buttonRow.addWidget(button)
        cardLayout.addLayout(buttonRow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))  # dim scrim over the page

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
        self.__host.installEventFilter(self)  # keep the overlay covering the window on resize
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
    def notify(host, title, message):
        """One-shot message (replacement for QMessageBox.warning / information)."""
        window = host.window()
        InWindowDialog(window, title, message, [("OK", None, None)]).__run()
