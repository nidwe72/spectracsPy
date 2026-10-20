import sys

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QPushButton, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class _Job(QThread):
    """One factory step off the GUI thread (plug + server calls take seconds); `done` carries its result line,
    `progress` an intermediate one (a firmware update takes minutes)."""
    done = Signal(str)
    progress = Signal(str)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work

    def run(self):
        try:
            self.done.emit(self.work())
        except Exception as error:                      # a step never takes the page down
            self.done.emit("✗ %s" % error)


class InstrumentPlugViewModule(PageWidget):
    """Settings → Administration → Instrument plug… — what concerns the PLUG only (SPEC_shelly_instrument_memory.md
    §5, §11 E4/L4), master only. The instrument itself (model, camera, style, light source, serial, plugin) is created
    on the Spectrometer setup page; this page shows which setup the plug belongs to and opens it.

    Top to bottom: [Search] lists every plug, labelled ● ◐ 🔒 ○ (never "the first one found", R25); pick one,
    [Identify] blinks it. The factory workflow F1–F6 (§11.11): [Add new plug] (Linux, Bluetooth: WLAN join only),
    [Harden] (password = MAC), [Write] / [Verify] the instrument data, [Prepare for shipping], or [Move] an instrument
    whose plug was replaced."""

    compactMainContainer = True

    TIP_SEARCH = ("Look for every plug on the network and label it:\n"
                  "● holds instrument data for its own id · ◐ known to the server · 🔒 locked (password unknown) · "
                  "○ not ours.\nChanges nothing. Works offline.")
    TIP_IDENTIFY = "Blink the chosen plug's LED ring blue — to tell plugs apart. Never switches the socket."
    TIP_ADD = ("A new or factory-reset plug (blinking, own WiFi open): join it to this PC's WLAN over Bluetooth.\n"
               "Writes nothing else. Linux only.")
    TIP_FIRMWARE = ("Update the plug's firmware over the internet, hop by hop, up to the version this app is tested "
                    "on (%s) — never beyond.\nThe plug reboots (1–2 min per hop); its settings and data stay. "
                    "Not while its lamp is on.")
    TIP_HARDEN = ("Prepare the plug for use: its password becomes its MAC (for the plug and its own WiFi), the "
                  "output stays OFF\nafter a power cut, Bluetooth stays on. The user is reminded to change it. "
                  "Needs the server (online only).")
    TIP_WRITE = ("Fetch the instrument's signed data from the server (setup, calibration, its users) and write\n"
                 "it onto the plug — only if it changed. A signed DB plugin is stored too.\n"
                 "Needs the server and your password.")
    TIP_VERIFY = ("Read everything back from the plug and check it as an offline login would: complete, signed by\n"
                  "the server, made for this plug, not newer than this app. Changes nothing. Works offline.")
    TIP_SHIP = ("Before the box leaves the house: the password goes back to the MAC (as the sheet in the box says),\n"
                "then the plug FORGETS this WLAN and drops off the network — the customer joins it to theirs.")
    TIP_MOVE = ("For a replaced plug: move the instrument from the old serial to this plug (calibration and bound\n"
                "users move with it), then write its data onto this plug. Needs the old serial, the server and your "
                "password.\nOnly for a plug that belongs to no instrument yet.")
    TIP_SETUP = "Open the Spectrometer setup of the instrument this plug belongs to."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.candidates = []
        self.job = None
        self.plugCombo = None

    def _getPageTitle(self):
        return "Instrument plug"

    # the chosen plug
    @property
    def candidate(self):
        index = self.plugCombo.currentIndex() if getattr(self, "plugCombo", None) is not None else -1
        return self.candidates[index] if 0 <= index < len(self.candidates) else None

    @property
    def device(self):
        return self.candidate.device if self.candidate is not None else None

    @property
    def plugPassword(self):
        return self.candidate.password if self.candidate is not None else None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.plugCombo = QComboBox()
        self.plugCombo.setObjectName("InstrumentPlug.plug")
        self.plugCombo.setToolTip(self.TIP_SEARCH)
        self.plugCombo.currentIndexChanged.connect(self.refresh)
        self.serialValue = QLabel("—")
        self.serialValue.setObjectName("InstrumentPlug.serial")
        self.serialValue.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.firmwareValue = QLabel("—")
        self.firmwareValue.setObjectName("InstrumentPlug.firmware")
        self.setupValue = QLabel("—")
        self.setupValue.setObjectName("InstrumentPlug.setup")
        self.setupValue.setWordWrap(True)
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setObjectName("InstrumentPlug.password")
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passwordEdit.setPlaceholderText("your login password (the server checks it)")
        self.oldSerialEdit = QLineEdit()
        self.oldSerialEdit.setObjectName("InstrumentPlug.oldSerial")
        self.oldSerialEdit.setPlaceholderText("only to move an instrument from a replaced plug")
        result['form'] = self.createForm([("Plug", self.plugCombo), ("Serial", self.serialValue),
                                          ("Firmware", self.firmwareValue), ("Belongs to", self.setupValue), ("Your password", self.passwordEdit),
                                          ("Old serial", self.oldSerialEdit)])

        buttons = QWidget()
        grid = QGridLayout(buttons)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(Metrics.S)
        self.searchButton = self.__button("Search", "search", self.onClickedSearch, secondary=True)
        self.identifyButton = self.__button("Identify", "identify", self.onClickedIdentify, secondary=True)
        self.addButton = self.__button("Add new plug…", "add", self.onClickedAdd, secondary=True)
        self.firmwareButton = self.__button("Update firmware", "firmware", self.onClickedFirmware, secondary=True)
        self.hardenButton = self.__button("Harden", "harden", self.onClickedHarden)
        self.writeButton = self.__button("Write to plug", "write", self.onClickedWrite)
        self.verifyButton = self.__button("Verify", "verify", self.onClickedVerify, secondary=True)
        self.shipButton = self.__button("Prepare for shipping", "ship", self.onClickedShip)
        self.moveButton = self.__button("Move instrument here", "move", self.onClickedMove, secondary=True)
        self.setupButton = self.__button("Open its setup", "setup", self.onClickedOpenSetup, secondary=True)
        self.addButton.setVisible(sys.platform.startswith("linux"))            # E10: Linux only for now
        tips = ((self.searchButton, self.TIP_SEARCH), (self.identifyButton, self.TIP_IDENTIFY),
                (self.addButton, self.TIP_ADD), (self.firmwareButton, self.TIP_FIRMWARE % self.__target()),
                (self.hardenButton, self.TIP_HARDEN),
                (self.writeButton, self.TIP_WRITE), (self.verifyButton, self.TIP_VERIFY),
                (self.shipButton, self.TIP_SHIP), (self.moveButton, self.TIP_MOVE), (self.setupButton, self.TIP_SETUP))
        for index, (button, tip) in enumerate(tips):
            button.setToolTip(tip)
            grid.addWidget(button, index // 3, index % 3)
        result['buttons'] = buttons

        self.resultLabel = self.createMessageLabel("")
        self.resultLabel.setObjectName("InstrumentPlug.result")
        self.resultLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        result['result'] = self.resultLabel
        return result

    def __button(self, text, name, slot, secondary=False):
        button = QPushButton(text)
        button.setObjectName("InstrumentPlug.%s" % name)
        if secondary:
            button.setProperty("buttonType", "secondary")
        button.clicked.connect(slot)
        return button

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
        self.refresh()
        if not self.candidates and self.isMaster():
            self.onClickedSearch()

    OFFLINE_NOTE = "Offline: Harden, Write, Prepare for shipping and Move need the server."

    @staticmethod
    def isMaster():
        return CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value)

    @staticmethod
    def isOnline():
        return not CurrentUserSession().isOffline()

    def refresh(self, *args):
        # Search, Identify, Verify and Add only talk to the plug ⇒ also offline. The steps that change the instrument
        # (server rows or the plug's settings) ⇒ online only. Nothing acts on a plug that is not chosen.
        master, online = self.isMaster(), self.isOnline()
        candidate = self.candidate
        have = candidate is not None and bool(candidate.device.deviceId)
        opens = have and candidate.label != "locked"
        busy = self.job is not None and self.job.isRunning()
        self.searchButton.setEnabled(master and not busy)
        self.addButton.setEnabled(master and not busy)
        for button in (self.identifyButton, self.verifyButton):
            button.setEnabled(master and opens and not busy)
        for button in (self.hardenButton, self.writeButton, self.shipButton, self.moveButton):
            button.setEnabled(master and online and opens and not busy)
        self.firmwareButton.setEnabled(master and opens and not busy and self.__belowTarget(candidate))
        if not master:
            self.serialValue.setText("Masters only.")
            self.setupValue.setText("—")
            self.setupButton.setEnabled(False)
            return
        self.serialValue.setText(candidate.device.deviceId if have else "—")
        self.firmwareValue.setText(self.__firmwareText(candidate) if have else "—")
        row = self.__setupRow(candidate.device.deviceId) if have and online else None
        self.setupButton.setEnabled(row is not None and not busy)
        # Move only onto a plug that belongs to no instrument yet — onto one with a setup it can only fail (L7 B1)
        self.moveButton.setEnabled(self.moveButton.isEnabled() and row is None)
        if not have:
            self.setupValue.setText("—")
        elif not online:
            self.setupValue.setText(self.OFFLINE_NOTE)
        elif row is None:
            self.setupValue.setText("no setup yet — create it on the Spectrometer setup page ([Find plug])")
        else:
            self.setupValue.setText("%s · %s · plugin %s" % (row.get("serial"), "-".join(
                part for part in (row.get("modelName"), row.get("deviceCodeName")) if part) or "—",
                (row.get("pluginTitle") or row.get("pluginCodeRef") or "—")))

    @staticmethod
    def __target():
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        return InstrumentFactoryLogicModule.TARGET_FIRMWARE

    def __belowTarget(self, candidate):
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        version = InstrumentFactoryLogicModule.versionTuple
        firmware = candidate.device.firmware if candidate is not None else None
        return bool(firmware) and version(firmware) < version(self.__target())

    def __firmwareText(self, candidate):
        firmware = candidate.device.firmware
        if not firmware:
            return "unknown"
        if self.__belowTarget(candidate):
            return "%s — older than the tested %s: [Update firmware]" % (firmware, self.__target())
        return "%s ✓" % firmware

    def __setupRow(self, serial):
        cache = getattr(self, "_rows", None)
        if cache is None:
            from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupListViewModule import \
                SpectrometerSetupListViewModule
            try:
                cache = {row.get("serial"): row for row in SpectrometerSetupListViewModule.buildRows()}
            except Exception:
                cache = {}
            self._rows = cache
        return cache.get(serial)

    # --- steps -------------------------------------------------------------------------------------------
    def __run(self, work, onDone=None, withProgress=False):
        self.resultLabel.setText("…")
        if withProgress:                                  # work(progress) reports intermediate lines
            holder = []
            self.job = _Job(lambda: work(holder[0].progress.emit), self)
            holder.append(self.job)
            self.job.progress.connect(self.resultLabel.setText)
        else:
            self.job = _Job(work, self)
        self.job.done.connect(lambda text: self.__finished(text, onDone))
        self.job.start()
        self.refresh()

    def __finished(self, text, onDone):
        self.resultLabel.setText(text)
        if onDone is not None:
            onDone(text) if onDone == self.__searchAfter else onDone()
        self.refresh()

    def __factory(self):
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        return InstrumentFactoryLogicModule()

    def onClickedSearch(self, *args):
        self.__search()

    def __searchAfter(self, text):
        # after a step that changes the plug: look again, but KEEP the step's result line (L7 B1: a failed write
        # was hidden behind "2 plug(s) found")
        self.__search(previous=text)

    def __search(self, previous=None):
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugLocator
        found = []

        def work():
            found.extend(PlugLocator().candidates())
            line = "✓ %d plug(s) found." % len(found) if found else "✗ No plug found — is it on the WLAN?"
            return "%s\n%s" % (previous, line) if previous else line

        def fill():
            previous = self.device.mac if self.device is not None else None
            self._rows = None
            self.candidates = found
            self.plugCombo.blockSignals(True)
            self.plugCombo.clear()
            for candidate in found:
                self.plugCombo.addItem(candidate.describe())
            index = next((i for i, c in enumerate(found) if c.device.mac == previous), 0)
            self.plugCombo.setCurrentIndex(index if found else -1)
            self.plugCombo.blockSignals(False)
        self.__run(work, fill)

    def onClickedIdentify(self):
        device, password = self.device, self.plugPassword
        self.__run(lambda: self.__factory().identify(device, password))

    def onClickedFirmware(self):
        device, password = self.device, self.plugPassword
        if not InWindowDialog.confirm(self, "Update the firmware?",
                                      "The plug %s (firmware %s) updates itself over the internet up to %s, hop by "
                                      "hop — it reboots each time (1–2 min) and is not reachable meanwhile. Keep it "
                                      "plugged in." % (device.deviceId, device.firmware or "?", self.__target())):
            return
        self.__run(lambda progress: self.__factory().updateFirmware(device, password, progress), self.__searchAfter,
                   withProgress=True)

    def onClickedHarden(self):
        device, password = self.device, self.plugPassword
        self.__run(lambda: self.__factory().harden(device, password), self.__searchAfter)

    def onClickedWrite(self):
        device, plugPassword = self.device, self.plugPassword
        username, password = CurrentUserSession().username, self.passwordEdit.text()
        self.__run(lambda: self.__factory().write(device, plugPassword, username, password), self.__searchAfter)

    def onClickedVerify(self):
        device, plugPassword = self.device, self.plugPassword
        self.__run(lambda: self.__factory().verify(device, plugPassword))

    def onClickedShip(self):
        device, plugPassword = self.device, self.plugPassword
        if not InWindowDialog.confirm(self, "Prepare for shipping?",
                                      "The plug %s gets its MAC as password again and then FORGETS this WLAN — it "
                                      "drops off the network. To get it back here: Add new plug." % device.deviceId,
                                      destructive=True):
            return
        self.__run(lambda: self.__factory().prepareForShipping(device, plugPassword), self.__searchAfter)

    def onClickedMove(self):
        oldSerial = self.oldSerialEdit.text().strip()
        if not oldSerial:
            self.resultLabel.setText("✗ Enter the serial of the replaced plug.")
            return
        device, plugPassword = self.device, self.plugPassword
        username, password = CurrentUserSession().username, self.passwordEdit.text()
        self.__run(lambda: self.__factory().moveHere(device, plugPassword, oldSerial, username, password),
                   self.__searchAfter)

    def onClickedAdd(self):
        from sciens.spectracs.view.settings.instrumentPlug.AddPlugViewModule import AddPlugViewModule
        AddPlugViewModule.run(self, onJoined=self.__searchAfter)

    def onClickedOpenSetup(self):
        row = self.__setupRow(self.device.deviceId) if self.device is not None else None
        if row is not None:
            from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupListViewModule import \
                SpectrometerSetupListViewModule
            SpectrometerSetupListViewModule.openEditor(row)

    def onClickedBack(self):
        navigationHandler = ApplicationContextLogicModule().getNavigationHandler()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            navigationHandler.handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
