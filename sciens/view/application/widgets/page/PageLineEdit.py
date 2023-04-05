from PySide6.QtWidgets import QLineEdit


class PageLineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        # super().installEventFilter(Polisher())



