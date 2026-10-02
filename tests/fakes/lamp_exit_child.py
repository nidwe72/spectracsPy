"""Child process for test_lamp_exit_hooks: a minimal app with the real exit hooks, the lamp switched on through
the real (threaded) LampService against the parent's FakeShellyServer, then ended in the way argv[1] names.
Prints READY once the lamp is on, so the parent can send a signal."""
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

from sciens.spectracs.logic.lamp.LampExitHooks import LampExitHooks
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampService import LampService
from sciens.spectracs.logic.lamp.LampState import LampState

mode = sys.argv[1]
app = QApplication(sys.argv[:1])
LampExitHooks.install(app)


class Window(QWidget):
    def closeEvent(self, event):                     # what MainContainerViewModule.closeEvent does
        LampExitHooks.shutdownLamp()
        super().closeEvent(event)


window = Window()
window.show()
service = LampService(plugStore=LampPlugStore())     # host from SPECTRACS_LAMP_HOST


def onState(state):
    if state == LampState.OFF.value and not getattr(onState, "switched", False):
        onState.switched = True
        service.toggleManual()
    elif state == LampState.WARMING.value:
        print("READY", flush=True)
        if mode == "quit":
            app.quit()
        elif mode == "sys.exit":
            sys.exit(0)
        elif mode == "close":
            window.close()
            os._exit(0)                              # prove it was the closeEvent, not a later hook
        elif mode == "twice":
            LampExitHooks.shutdownLamp()
            LampExitHooks.shutdownLamp()
            os._exit(0)


service.stateChanged.connect(onState)
service.configure(True)
QTimer.singleShot(20000, lambda: os._exit(3))        # never hang the suite
app.exec()
