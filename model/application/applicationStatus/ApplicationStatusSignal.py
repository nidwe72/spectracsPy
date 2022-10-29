from PySide6.QtCore import QObject


class ApplicationStatusSignal(QObject):
    stepsCount: int = 100
    currentStepIndex: int = 0
    text: str
    isStatusReset: bool = False

    def __init__(self, parent=None):
        super().__init__(parent)
