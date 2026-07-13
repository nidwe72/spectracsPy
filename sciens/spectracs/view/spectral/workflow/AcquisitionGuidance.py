from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPolygon

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal


class AcquisitionGuidance:
    """Host-agnostic acquisition-guidance primitives (SPEC_plugin_driven_convergence.md §9 D4 / S1a).

    The amber ● / ▶ cue icons, the capture-button dot, and the status-bar coach-line emit were mirrored
    byte-for-byte in `WizardViewModule` and `DevMeasurementBenchViewModule`. Lifted here so both hosts share
    ONE implementation. Each host keeps only its nav-specific bits — the acquisition entry gate and the
    highlight targets — which can't unify while the two nav skins stand (D3). No host state, so a host just
    holds one instance and delegates to it.

    The full guidance collapse (derivation + highlight application) is S4a; this is only the byte-identical
    primitives.
    """

    def __init__(self):
        self.__amberDot = None      # lazily-painted amber ● cue icon
        self.__amberArrow = None    # lazily-painted amber ▶ Next-button cue icon

    def amberDotIcon(self):
        if self.__amberDot is None:
            self.__amberDot = self.__paintGuidanceIcon("dot")
        return self.__amberDot

    def amberArrowIcon(self):
        if self.__amberArrow is None:
            self.__amberArrow = self.__paintGuidanceIcon("arrow")
        return self.__amberArrow

    def setButtonDot(self, button, on):
        if button is not None:
            button.setIcon(self.amberDotIcon() if on else QIcon())

    def emit(self, text):
        # Guidance text → muted-amber font, no progress bar. A None/empty text rests the bar instead
        # (equivalent to the hosts' former __emitStatusReset / __clearStatus).
        signal = ApplicationStatusSignal()
        if not text:
            signal.isStatusReset = True
        else:
            signal.isStatusReset = False
            signal.guidance = True
            signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __paintGuidanceIcon(self, shape):
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ApplicationStyleLogicModule().getGuidanceColor())
        if shape == "arrow":
            painter.drawPolygon(QPolygon([QPoint(3, 2), QPoint(10, 6), QPoint(3, 10)]))  # right-pointing ▶
        else:
            painter.drawEllipse(2, 2, 8, 8)  # ●
        painter.end()
        return QIcon(pixmap)
