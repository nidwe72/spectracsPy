from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.lamp.LampSetupHint import LampSetupHint
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class LampSettingsViewModule(PageWidget):
    """Settings → Lamp plug… (SPEC_lamp_switch.md §6, §16 U12; SPEC_shelly_instrument_memory.md §11, C3/R39/R45).
    Shows the instrument's plug (only a registered one is used, E6), takes the password of a locked plug (stored
    per plug in the app DB, R33), CHANGES the plug's password (API + its own WiFi together, C3), searches again and
    tests it ("On 2 s · 11.2 W ✓"). Lists every plug this PC remembers. Joining the WLAN is the plug page's
    "Add new plug" (Linux) or the Shelly app; an unconfigured Shelly nearby only produces a hint (§15.5)."""

    compactMainContainer = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__bound = None
        self.job = None

    def _getPageTitle(self):
        return "Lamp plug"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.plugValue = QLabel("—")
        self.plugValue.setObjectName("LampSettings.plug")
        self.plugValue.setWordWrap(True)
        self.plugValue.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.stateValue = QLabel("—")
        self.stateValue.setObjectName("LampSettings.state")
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setObjectName("LampSettings.password")
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)     # masked, like Login (§16 U12)
        self.passwordEdit.setPlaceholderText("only if the plug is locked with a password")
        self.newPasswordEdit = QLineEdit()
        self.newPasswordEdit.setObjectName("LampSettings.newPassword")
        self.newPasswordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.newPasswordEdit.setPlaceholderText("new plug password, at least 8 characters")
        result['form'] = self.createForm([("Lamp plug", self.plugValue), ("Status", self.stateValue),
                                          ("Password", self.passwordEdit), ("New password", self.newPasswordEdit)])

        buttons = QWidget()
        row = QHBoxLayout(buttons)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Metrics.S)
        self.saveButton = QPushButton("Save password")
        self.saveButton.setObjectName("LampSettings.save")
        self.saveButton.clicked.connect(self.onClickedSave)
        self.searchButton = QPushButton("Search again")
        self.searchButton.setObjectName("LampSettings.search")
        self.searchButton.setProperty("buttonType", "secondary")
        self.searchButton.clicked.connect(self.onClickedSearch)
        self.testButton = QPushButton("Test: on 2 s")
        self.testButton.setObjectName("LampSettings.test")
        self.testButton.setProperty("buttonType", "secondary")
        self.testButton.clicked.connect(self.onClickedTest)
        self.changeButton = QPushButton("Change password")
        self.changeButton.setObjectName("LampSettings.change")
        self.changeButton.setToolTip("Set a new password on the plug — for the plug itself and its own WiFi\n"
                                     "(both use the same one). Saved on this PC; other PCs ask for it once.")
        self.changeButton.clicked.connect(self.onClickedChange)
        for button in (self.saveButton, self.changeButton, self.searchButton, self.testButton):
            row.addWidget(button)
        result['buttons'] = buttons

        self.resultLabel = self.createMessageLabel("")
        self.resultLabel.setObjectName("LampSettings.result")
        result['result'] = self.resultLabel
        self.othersLabel = self.createMessageLabel("")
        result['others'] = self.othersLabel
        self.rememberedLabel = self.createMessageLabel("")
        self.rememberedLabel.setObjectName("LampSettings.remembered")
        result['remembered'] = self.rememberedLabel
        self.hintLabel = self.createMessageLabel("")
        self.hintLabel.setObjectName("LampSettings.hint")
        self.hintLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)  # the URL is copyable
        result['hint'] = self.hintLabel
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        backButton = QPushButton("Back")
        backButton.clicked.connect(self.onClickedBack)
        result.layout().addWidget(backButton, 0, 0, 1, 1)
        return result

    # --- lifecycle ---------------------------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self.resultLabel.setText("")
        service = self.__service()
        if service is not None and service is not self.__bound:
            self.__bound = service
            service.stateChanged.connect(self.refresh)
            service.hintChanged.connect(self.refresh)
            service.testResult.connect(self.resultLabel.setText)
        self.refresh()

    def refresh(self, *args):
        service = self.__service()
        live = service is not None and service.state != LampState.NOT_APPLICABLE
        for widget in (self.saveButton, self.searchButton, self.passwordEdit):
            widget.setEnabled(live)
        if not live:
            self.changeButton.setEnabled(False)
            self.newPasswordEdit.setEnabled(False)
            self.rememberedLabel.setText("")
            self.plugValue.setText("No lamp switch — log in with a real spectrometer whose light source is a "
                                   "Shelly plug (Spectrometer setup → Light source).")
            self.stateValue.setText("—")
            self.testButton.setEnabled(False)
            self.othersLabel.setText("")
            self.hintLabel.setText("")
            return
        device = service.device
        if device is None:
            stored, _ = service.plugStore.load()
            self.plugValue.setText("none found" + (" (last: %s)" % stored.describe() if stored else ""))
        else:
            self.plugValue.setText(device.describe())
        self.stateValue.setText(self.__stateText(service))
        self.testButton.setEnabled(service.switch is not None and service.state == LampState.OFF)
        self.changeButton.setEnabled(service.switch is not None and (self.job is None or not self.job.isRunning()))
        self.newPasswordEdit.setEnabled(service.switch is not None)
        remembered = service.plugStore.loadAll() if hasattr(service.plugStore, "loadAll") else []
        self.rememberedLabel.setText("Plugs this PC knows: " + ", ".join(
            "%s%s%s" % ("● " if device is not None and service.device is not None and device.mac == service.device.mac
                        else "", device.deviceId or device.formattedMac(), " (password saved)" if password else "")
            for device, password in remembered) if remembered else "")
        others = service.otherDevices
        self.othersLabel.setText("Also found: " + ", ".join(other.describe() for other in others) if others else "")
        self.hintLabel.setText("\n\n".join(LampSetupHint.hintText(ssid) for ssid in service.setupSsids))

    @staticmethod
    def __stateText(service):
        state = service.state
        if state == LampState.SEARCHING:
            return "● searching …"
        if state == LampState.NO_PLUG:
            if service.needsPassword:
                return "● needs a password — the instrument's plug is locked"
            return "● not found — switch the lamp at the socket" + (
                "\n(%s)" % service.refusedReason if service.refusedReason else "")
        if service.defaultPassword:
            return "● reachable · still its default password (the MAC) — set a new one below"
        if state == LampState.UNREACHABLE:
            return "● not answering"
        if state in (LampState.WARMING, LampState.ON):
            return "● reachable · lamp on"
        return "● reachable · lamp off"

    # --- actions -----------------------------------------------------------------------------------------
    def onClickedSave(self):
        service = self.__service()
        if service is None:
            return
        service.setPassword(self.passwordEdit.text())
        self.passwordEdit.clear()
        self.resultLabel.setText("Password saved — checking the plug …")

    def onClickedChange(self):
        # C3 (R45): AP first, then the API password, then stored — the factory step, off the GUI thread.
        service = self.__service()
        if service is None or service.device is None:
            return
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import _Job
        device, current, new = service.device, service.devicePassword, self.newPasswordEdit.text()
        self.newPasswordEdit.clear()
        self.resultLabel.setText("Changing the password …")
        self.job = _Job(lambda: InstrumentFactoryLogicModule().changePassword(device, current, new), self)
        self.job.done.connect(self.resultLabel.setText)
        self.job.done.connect(self.refresh)
        self.job.start()
        self.refresh()

    def onClickedSearch(self):
        service = self.__service()
        if service is not None:
            self.resultLabel.setText("")
            service.discover()

    def onClickedTest(self):
        service = self.__service()
        if service is not None:
            self.resultLabel.setText("Testing …")
            service.testPulse()

    def onClickedBack(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)

    @staticmethod
    def __service():
        from sciens.spectracs.logic.lamp.LampService import LampService
        return LampService.instance
