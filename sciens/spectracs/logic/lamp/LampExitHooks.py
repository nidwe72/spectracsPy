import atexit
import logging
import signal
import socket

from PySide6.QtCore import QSocketNotifier

LOG = logging.getLogger(__name__)


class LampExitHooks:
    # Lamp off when the app ends (SPEC_lamp_switch.md §7.1, D15) — wired to every exit path Python can see:
    #
    #   window closed / Quit / app.quit()          app.aboutToQuit
    #   window closed DURING a capture             MainContainerViewModule.closeEvent (aboutToQuit would wait for
    #                                              the capture's nested event loops, up to 25 min — §14 R3)
    #   sys.exit() / normal interpreter end        atexit
    #   Ctrl+C / kill / terminal closed / logout   SIGINT / SIGTERM / SIGHUP
    #
    # NOT sys.excepthook (§14 R2): in PySide6 a slot exception reaches it and the app keeps running.
    # kill -9, a segfault, power loss: no hook can run — the plug's own cap covers those (D4).
    #
    # Signals: Python runs a handler only when the interpreter gets control, and Qt's event loop sits in C++.
    # signal.set_wakeup_fd writes a byte to a socket pair; a QSocketNotifier on the other end wakes the loop,
    # and the pending Python handler runs (instead of a 500 ms polling timer, §14.2).

    __installed = False
    __keepAlive = []

    @staticmethod
    def shutdownLamp():
        """Idempotent; a no-op when no LampService was ever created (virtual device, never logged in)."""
        from sciens.spectracs.logic.lamp.LampService import LampService
        service = LampService.instance
        if service is not None:
            try:
                service.shutdown()
            except Exception as error:                 # an exit hook must never raise
                LOG.warning("lamp: shutdown failed: %s", error)

    @staticmethod
    def install(app):
        if LampExitHooks.__installed:
            return
        LampExitHooks.__installed = True
        app.aboutToQuit.connect(LampExitHooks.shutdownLamp)
        atexit.register(LampExitHooks.shutdownLamp)
        LampExitHooks.__installSignals(app)

    @staticmethod
    def __installSignals(app):
        def onSignal(signum, frame):
            LampExitHooks.shutdownLamp()
            app.quit()

        names = ("SIGINT", "SIGTERM", "SIGHUP")             # SIGHUP does not exist on Windows
        for name in names:
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), onSignal)
        try:
            reader, writer = socket.socketpair()
            reader.setblocking(False)
            writer.setblocking(False)
            signal.set_wakeup_fd(writer.fileno())
            notifier = QSocketNotifier(reader.fileno(), QSocketNotifier.Type.Read)
            notifier.activated.connect(lambda *args: LampExitHooks.__drain(reader))
            LampExitHooks.__keepAlive.extend([reader, writer, notifier])
        except (OSError, ValueError) as error:                # not the main thread / no socketpair
            LOG.warning("lamp: no signal wake-up fd: %s", error)

    @staticmethod
    def __drain(reader):
        try:
            while reader.recv(64):
                pass
        except (BlockingIOError, OSError):
            pass
