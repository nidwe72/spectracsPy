from PySide6 import QtCore
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QToolButton

from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.main.ProgressRing import drawProgressRing


class LampButton(QToolButton):
    """The header lamp icon (SPEC_lamp_switch.md §9.1 / §16.2), third beside the camera and account icons, same
    chrome. Shape carries the state, not only colour (§16 U11): outline bulb = off, filled bulb with rays = on,
    a progress ring while warming, a "?" when the plug is not answering / not found.

    Hidden when there is nothing to switch: virtual device, logged out, or a desk that never had a plug (U7).
    Click = toggle; ignored while a capture runs (U6); no plug / unreachable = an in-window notice, never a
    tooltip-only message (no tooltips on touch, U10)."""

    # viewBox -4 -4 32 32, not 0 0 24 24: the bulb drawn at 75 %, so the warm-up ring at the pixmap's edge keeps a
    # gap to it (Edwin 2026-10-02). All states share it — the bulb does not jump when the ring appears.
    OUTLINE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 32 32">
  <path d="M12 3.2 C8.3 3.2 5.8 6 5.8 9.3 C5.8 11.6 7 13.2 8.4 14.5 C9.1 15.2 9.4 15.9 9.4 16.8 L14.6 16.8
           C14.6 15.9 14.9 15.2 15.6 14.5 C17 13.2 18.2 11.6 18.2 9.3 C18.2 6 15.7 3.2 12 3.2 Z"
        fill="none" stroke="%(c)s" stroke-width="1.6" stroke-linejoin="round"/>
  <path d="M9.6 18.9 H14.4 M10.4 21 H13.6" stroke="%(c)s" stroke-width="1.6" stroke-linecap="round"/>
</svg>'''

    FILLED_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 32 32">
  <path d="M12 5.4 C9.4 5.4 7.6 7.4 7.6 9.8 C7.6 11.5 8.5 12.7 9.5 13.6 C10 14.1 10.3 14.7 10.3 15.4 L13.7 15.4
           C13.7 14.7 14 14.1 14.5 13.6 C15.5 12.7 16.4 11.5 16.4 9.8 C16.4 7.4 14.6 5.4 12 5.4 Z" fill="%(c)s"/>
  <path d="M10.4 17.4 H13.6 M10.9 19.4 H13.1" stroke="%(c)s" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M12 1.6 V3.2 M4.2 9.8 H2.6 M21.4 9.8 H19.8 M6.3 4.2 L5.2 3.1 M17.7 4.2 L18.8 3.1"
        stroke="%(c)s" stroke-width="1.5" stroke-linecap="round"/>
</svg>'''

    WHITE = '#FFFFFF'
    GREY = '#808080'
    GREEN = '#6FCF7F'                      # lamp on and warm = ready to measure (Edwin 2026-10-02); lighter than
                                           # the brand green #3D7848, which vanishes on the dark header
    DIM = '#555555'                        # plug ready, lamp off: present but quiet — must not distract (Edwin
                                           # 2026-10-02); darker than GREY, which with "?" means no plug

    def __init__(self, size, renderSvg, parent=None):
        super().__init__(parent)
        self.__size = size
        self.__renderSvg = renderSvg
        self.__service = None
        self.setObjectName("MainStatusBar.lampButton")       # Director anchor
        self.setAutoRaise(True)
        self.setStyleSheet(
            "QToolButton { background: transparent; border: 1px solid #5A5A5A; border-radius: 6px; }"
            "QToolButton:hover { background: rgba(255, 255, 255, 0.10); }"
            "QToolButton:pressed { background: rgba(255, 255, 255, 0.16); }")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(size - 24, size - 24))
        self.clicked.connect(self.__onClicked)
        self.setVisible(False)

    def bind(self, service):
        if service is self.__service:
            return
        self.__service = service
        service.stateChanged.connect(self.refresh)
        service.warmUpTick.connect(self.refresh)
        service.hintChanged.connect(self.refresh)
        self.refresh()

    # --- rendering -----------------------------------------------------------------------------------
    def refresh(self, *args):
        service = self.__service
        if service is None or service.state == LampState.NOT_APPLICABLE \
                or (service.state in (LampState.NO_PLUG, LampState.SEARCHING) and not service.hasKnownPlug()):
            self.setVisible(False)
            return
        self.setVisible(True)
        state = service.state
        if state == LampState.ON:
            # green once warm = ready to measure (Edwin 2026-10-02); filled with rays tells it from the plug-ready outline
            icon, tip = self.__svg(self.FILLED_SVG, self.GREEN), self.__onTooltip(service)
            if service.noPower:
                icon = self.__badge(icon, "!")
                tip = "The plug is on but the lamp draws no power — check the switch on the lamp socket"
        elif state == LampState.WARMING:
            remaining = service.warmUpRemainingSeconds()
            icon = self.__ring(self.__svg(self.OUTLINE_SVG, self.WHITE), service.warmUpSeconds, remaining)
            tip = "Lamp warming up — %d s left (click: off)" % remaining
        elif state == LampState.OFF:
            # always dim, also in ACQUISITION (Edwin 2026-10-02: the amber cue read as red after an off); the coach
            # line still says "Switch the lamp on" and the capture gate stays closed
            icon = self.__svg(self.OUTLINE_SVG, self.DIM)
            tip = ("Switch the lamp on to measure" if service.wantsOn
                   else "Lamp plug ready, lamp off — click to switch it on")
        elif state == LampState.SEARCHING:
            icon, tip = self.__svg(self.OUTLINE_SVG, self.GREY), "Looking for the lamp plug …"
        elif state == LampState.UNREACHABLE:
            icon, tip = self.__badge(self.__svg(self.OUTLINE_SVG, self.GREY), "?"), "Lamp plug not answering"
        else:                                                   # NO_PLUG on a desk that had one
            icon = self.__badge(self.__svg(self.OUTLINE_SVG, self.GREY), "?")
            tip = ("Lamp plug needs a password — Settings → Lamp" if service.needsPassword
                   else "Lamp plug not found — switch the lamp at the socket")
        self.setIcon(QIcon(icon))
        self.setToolTip(tip)

    @staticmethod
    def __onTooltip(service):
        remaining = service.capRemainingSeconds()
        if remaining is None:
            return "Lamp on (click: off)"
        return "Lamp on · switches off in %d min (click: off)" % max(1, round(remaining / 60.0))

    def __svg(self, template, colour):
        return self.__renderSvg(template % {'c': colour})

    def __ring(self, pixmap, total, remaining):
        return drawProgressRing(pixmap, total, remaining, self.WHITE)

    def __badge(self, pixmap, text):
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        diameter = pixmap.width() * 0.42
        rect = QRectF(pixmap.width() - diameter, pixmap.height() - diameter, diameter, diameter)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#5A5A5A"))
        painter.drawEllipse(rect)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(int(diameter * 0.7))
        painter.setFont(font)
        painter.setPen(QColor(self.WHITE))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return pixmap

    # --- click ---------------------------------------------------------------------------------------
    def __onClicked(self):
        service = self.__service
        if service is None or service.captureRunning:           # never touch the lamp mid-capture (U6)
            return
        if service.state == LampState.NO_PLUG:
            message = ("The lamp plug needs a password. Enter it in Settings → Lamp."
                       if service.needsPassword else
                       "The lamp plug was not found on the network. Switch the lamp on at the socket, or look "
                       "in Settings → Lamp.")
            InWindowDialog.notify(self, "Lamp", message)
            return
        if service.state == LampState.UNREACHABLE:
            InWindowDialog.notify(self, "Lamp", "The lamp plug is not answering. Check the Wi-Fi and that the "
                                                "plug has power; the app keeps trying.")
            return
        if service.state == LampState.SEARCHING:
            return
        service.toggleManual()
