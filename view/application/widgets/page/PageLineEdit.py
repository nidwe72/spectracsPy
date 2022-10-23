import typing

from PyQt6 import QtCore
from PyQt6.QtWidgets import QLineEdit

from logic.appliction.style.Polisher import Polisher


class PageLineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        super().installEventFilter(Polisher())



