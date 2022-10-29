import typing

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit

from logic.appliction.style.Polisher import Polisher


class PageLineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        # super().installEventFilter(Polisher())



