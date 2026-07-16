from PySide6.QtCore import QObject


class ApplicationStatusSignal(QObject):
    stepsCount: int = 100
    currentStepIndex: int = 0
    text: str
    isStatusReset: bool = False
    # SPEC_acquisition_guidance: plugin/guidance text — render as muted-amber font with NO progress bar.
    guidance: bool = False

    def __init__(self, parent=None):
        super().__init__(parent)
