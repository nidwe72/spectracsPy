import os
import sys

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QGuiApplication

from sciens.base.PlatformUtil import is_android
from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.main.MainContainerViewModule import MainContainerViewModule


# Touch-density overrides appended to the base stylesheet on Android only (P3). Applied AFTER the
# base sheet's .format(), so these are literal QSS (single braces) and win by ordering. Desktop is
# untouched. Tune on-device during P4.
# Touch-density overrides applied on real Android AND desktop --phone (so the desktop width audit reproduces the
# phone's enlarged controls — see docs/SPEC_phone_width_responsiveness.md). The QComboBox::drop-down/::down-arrow
# overrides were removed (S14): styling ::drop-down suppresses Qt's native ▼ glyph, so we rely on the native arrow
# at every density instead of a border-box.
ANDROID_TOUCH_DENSITY_QSS = """
QScrollBar:vertical { width: 26px; }
QScrollBar:horizontal { height: 26px; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 30px; }
QSpinBox::up-arrow, QSpinBox::down-arrow, QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { width: 14px; height: 14px; }
"""

# S13: the enlarged checkbox/radio indicator is a REAL-DEVICE touch target only. Desktop --phone drives with a
# mouse, so it keeps the desktop 13px indicator (Edwin) — this is the one touch override --phone does NOT get.
ANDROID_ONLY_TOUCH_QSS = """
QRadioButton::indicator, QCheckBox::indicator { width: 26px; height: 26px; }
"""


class _AndroidBackButtonFilter(QtCore.QObject):
    """Map the Android hardware/gesture back button to in-app navigation instead of letting Qt
    close the activity. When not already on Home, route to Home and consume the event; on Home,
    fall through to the default (exit). P3; refine to true history-back later if needed.
    """

    def __init__(self, mainContainerViewModule):
        super().__init__()
        self._mainContainerViewModule = mainContainerViewModule

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress and event.key() == QtCore.Qt.Key.Key_Back:
            mainViewModule = self._mainContainerViewModule.mainViewModule
            if mainViewModule.currentIndex() != 0:
                ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal(
                    NavigationSignal().setTarget("Home"))
                return True
        return False


def _ensureFocusedWidgetVisible(old, now):
    """When a field gains focus and the Android soft keyboard shrinks the window (manifest
    windowSoftInputMode=adjustResize), scroll that field into view inside its enclosing QScrollArea
    (the PageWidget wrap). No-op if the focused widget isn't inside a scroll area. Android only."""
    if now is None:
        return
    widget = now.parentWidget()
    while widget is not None:
        if isinstance(widget, QtWidgets.QScrollArea):
            widget.ensureWidgetVisible(now)
            return
        widget = widget.parentWidget()


def _parsePhoneModeArgs(argv):
    """Desktop-only dev switch (P1): reproduce the phone's constrained *logical* width on desktop so
    too-wide / cut-off controls surface without an APK rebuild. Returns (phoneMode, phoneWidth,
    phoneZoom). Defaults target a Galaxy Note20 5G at default display zoom (412 dp) with a 1.1× view
    zoom that fits the full ~883 dp height on a 1920x1080 monitor.

    Order matters: '--phone' is a prefix of '--phone=' and '--phone-zoom=', so test the longer forms
    first. See docs/SPEC_phone_width_responsiveness.md."""
    phoneMode = False
    phoneWidth = 412
    phoneZoom = 1.1
    for arg in argv[1:]:
        if arg.startswith("--phone-zoom="):
            phoneZoom = float(arg.split("=", 1)[1])
        elif arg.startswith("--phone="):
            phoneMode = True
            phoneWidth = int(arg.split("=", 1)[1])
        elif arg == "--phone":
            phoneMode = True
    return phoneMode, phoneWidth, phoneZoom


# Parse the phone-mode flags BEFORE QApplication is constructed: QT_SCALE_FACTOR is read by Qt at
# construction time. An explicit QT_SCALE_FACTOR in the environment wins (escape hatch).
phoneMode, phoneWidth, phoneZoom = _parsePhoneModeArgs(sys.argv)
if phoneMode and "QT_SCALE_FACTOR" not in os.environ:
    os.environ["QT_SCALE_FACTOR"] = str(phoneZoom)

app = QtWidgets.QApplication(sys.argv)

# Stable identity for QStandardPaths / caches (P2). The SQLite path itself resolves via
# ANDROID_PRIVATE on device and `appdata` on desktop (see AppDataPathUtil).
app.setOrganizationName("Sciens")
app.setApplicationName("SpectracsPy")

styleSheet = ApplicationStyleLogicModule().getApplicationStyleSheet()
# phoneMode gets the width-relevant touch-density overrides too (scrollbars/spinbox), so enlarged controls
# contribute their real width to the desktop width audit (else desktop under-reports clipping). The checkbox
# indicator is the ONE exception (S13) — it's device-only, so --phone shows the desktop-size icon.
if is_android() or phoneMode:
    styleSheet += ANDROID_TOUCH_DENSITY_QSS
if is_android():
    # S13: 26px checkbox indicator only on a real touch device — desktop --phone stays at the desktop 13px.
    styleSheet += ANDROID_ONLY_TOUCH_QSS
app.setStyleSheet(styleSheet)

# Bring-up only (P4/P5): synthesize a logged-in dev session when SPECTRACS_DEV_LOGIN_BYPASS is set,
# so the virtual pipeline can run before the server app exists. No-op otherwise. Removed at P6 (D13).
CurrentUserSession().applyDevLoginBypassIfEnabled()

mainContainerViewModule = MainContainerViewModule()
mainContainerViewModule.setWindowTitle("Spectracs")

ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = mainContainerViewModule

_androidBackButtonFilter = None
if is_android():
    # Phones: fill the screen; the OS owns orientation (portrait is set in buildozer.spec / manifest).
    mainContainerViewModule.showFullScreen()
    _androidBackButtonFilter = _AndroidBackButtonFilter(mainContainerViewModule)
    app.installEventFilter(_androidBackButtonFilter)
    # Keep the focused input visible above the soft keyboard.
    app.focusChanged.connect(_ensureFocusedWidgetVisible)
elif phoneMode:
    # Desktop "phone mode" (P1): fix the window to the phone's logical width — the audit invariant —
    # so cut-off / too-wide controls surface exactly as on device. Height fits the monitor; vertical
    # scroll (PageWidget QScrollArea) handles overflow. See docs/SPEC_phone_width_responsiveness.md.
    availableHeight = QGuiApplication.primaryScreen().availableGeometry().height()
    mainContainerViewModule.setFixedWidth(phoneWidth)
    mainContainerViewModule.setFixedHeight(min(883, int(availableHeight * 0.95)))
    mainContainerViewModule.show()
else:
    geometry = QGuiApplication.primaryScreen().availableGeometry()
    mainContainerViewModule.setMinimumWidth(geometry.width() / 2)
    mainContainerViewModule.setMinimumHeight(geometry.height() * 0.9)
    mainContainerViewModule.showMaximized()  # G1: desktop opens maximized

try:
    import pyi_splash

    pyi_splash.update_text('UI Loaded ...')
    pyi_splash.close()
except:
    pass

sys.exit(app.exec())
