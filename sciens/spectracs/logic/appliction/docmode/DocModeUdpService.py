import json
import sys

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtWidgets import QWidget, QTabWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal


class DocModeUdpService(QObject):
    """Local UDP command endpoint for --doc-mode (SPEC_doc_automation §2.3).

    An external "Director" screencast script sends one-line JSON datagrams to 127.0.0.1:<port> to narrate
    and drive the app. Because we own the app, the Director never needs fragile screen coordinates: it asks
    `locate` where a widget is and the app answers with live global coordinates, so the Director can glide a
    real mouse there for the video.

    readyRead fires on the GUI thread (the socket is created here), so handlers touch widgets directly —
    no cross-thread marshalling. Every reply goes back to the datagram's sender address/port.

    Commands (see §4):
      set_hint {text}                      -> update the hint panel (no reply)
      ping                                 -> {ok:true}
      nav {view}                           -> fire a NavigationSignal to that view; {ok:true}
      locate {name, tab?}                  -> {ok, cx, cy, x, y, w, h} global px, or {ok:false}
      wait {name, enabled?/visible?/text?} -> ONE-SHOT state probe: {ok:true} if it matches now, else
                                              {ok:false}. The Director polls by resending (it owns the loop,
                                              so the GUI never blocks).
      dismiss                              -> click the OK of any open in-window dialog; {ok, dismissed}
    """

    DEFAULT_PORT = 5555

    def __init__(self, mainContainerViewModule, hintPanel):
        super().__init__(mainContainerViewModule)
        self.__root = mainContainerViewModule
        self.__hintPanel = hintPanel
        self.__socket = QUdpSocket(self)
        port = self.__parsePort(sys.argv)
        bound = self.__socket.bind(QHostAddress(QHostAddress.SpecialAddress.LocalHost), port)
        if not bound:
            print("DocModeUdpService: could not bind 127.0.0.1:%s (%s) — doc-mode driving disabled"
                  % (port, self.__socket.errorString()))
            return
        self.__socket.readyRead.connect(self.__drain)
        print("DocModeUdpService: listening on 127.0.0.1:%s" % port)

    def __parsePort(self, argv):
        for arg in argv:
            if arg.startswith("--doc-port="):
                try:
                    return int(arg.split("=", 1)[1])
                except ValueError:
                    pass
        return self.DEFAULT_PORT

    # --- datagram loop ---

    def __drain(self):
        while self.__socket.hasPendingDatagrams():
            datagram = self.__socket.receiveDatagram()
            try:
                message = json.loads(bytes(datagram.data()).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            try:
                reply = self.__handle(message)
            except Exception as exception:  # never let a bad command wedge the app
                reply = {"ok": False, "error": str(exception)}
            if reply is not None:
                self.__reply(datagram.senderAddress(), datagram.senderPort(), reply)

    def __reply(self, host, port, payload):
        self.__socket.writeDatagram(json.dumps(payload).encode("utf-8"), host, port)

    # --- command dispatch ---

    def __handle(self, message):
        command = message.get("cmd")
        if command == "set_hint":
            self.__hintPanel.setHint(message.get("text", ""))
            return None
        if command == "ping":
            return {"ok": True}
        if command == "nav":
            return self.__nav(message.get("view"))
        if command == "locate":
            return self.__locate(message.get("name"), message.get("tab"))
        if command == "activate":
            return self.__activate(message.get("name"), message.get("tab"))
        if command == "wait":
            return self.__wait(message)
        if command == "dismiss":
            return self.__dismiss()
        return {"ok": False, "error": "unknown cmd: %r" % command}

    def __nav(self, view):
        if not view:
            return {"ok": False, "error": "nav needs a view"}
        signal = NavigationSignal(None).setTarget(view)
        ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal(signal)
        return {"ok": True}

    def __find(self, name):
        if not name:
            return None
        widget = self.__root.findChild(QWidget, name)
        if widget is None or not widget.isVisible():
            return None
        return widget

    def __locate(self, name, tab):
        widget = self.__find(name)
        if widget is None:
            return {"ok": False, "error": "not found/visible: %r" % name}
        if tab is not None and isinstance(widget, QTabWidget):
            rect = widget.tabBar().tabRect(int(tab))
            topLeft = widget.tabBar().mapToGlobal(rect.topLeft())
            x, y, w, h = topLeft.x(), topLeft.y(), rect.width(), rect.height()
        else:
            topLeft = widget.mapToGlobal(widget.rect().topLeft())
            x, y, w, h = topLeft.x(), topLeft.y(), widget.width(), widget.height()
        return {"ok": True, "cx": x + w // 2, "cy": y + h // 2, "x": x, "y": y, "w": w, "h": h}

    def __activate(self, name, tab):
        # Deterministically trigger a widget the app owns, so activation never depends on pixel-precise
        # mouse landing or window focus. The Director still glides the visible cursor there first (for the
        # video); this guarantees the actual effect. Buttons -> click(); QTabWidget + tab -> setCurrentIndex.
        widget = self.__find(name)
        if widget is None:
            return {"ok": False, "error": "not found/visible: %r" % name}
        if tab is not None and isinstance(widget, QTabWidget):
            widget.setCurrentIndex(int(tab))
            return {"ok": True}
        if hasattr(widget, "animateClick"):
            widget.animateClick()   # visible press feedback + emits clicked
            return {"ok": True}
        if hasattr(widget, "click"):
            widget.click()
            return {"ok": True}
        return {"ok": False, "error": "widget %r is not activatable" % name}

    def __wait(self, message):
        widget = self.__find(message.get("name"))
        if widget is None:
            return {"ok": False, "error": "not found/visible"}
        if "enabled" in message and widget.isEnabled() != bool(message["enabled"]):
            return {"ok": False}
        if "visible" in message and widget.isVisible() != bool(message["visible"]):
            return {"ok": False}
        if "text" in message:
            text = widget.text() if hasattr(widget, "text") else ""
            if message["text"] not in text:
                return {"ok": False}
        return {"ok": True}

    def __dismiss(self):
        # Click the OK/primary button of any open in-window dialog (e.g. the bench's "Capture failed"
        # InWindowDialog, §7.1) so an unexpected modal can't wedge an automated run. Populated in P5.
        from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
        dialog = self.__root.findChild(InWindowDialog)
        if dialog is None:
            return {"ok": True, "dismissed": False}
        button = dialog.findChild(QWidget, "inWindowDialog.primaryButton")
        if button is not None and hasattr(button, "click"):
            button.click()
            return {"ok": True, "dismissed": True}
        return {"ok": False, "error": "dialog has no dismissable button"}
