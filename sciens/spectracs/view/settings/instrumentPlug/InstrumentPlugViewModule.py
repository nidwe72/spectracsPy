from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QPushButton, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class _Job(QThread):
    """One factory step off the GUI thread (plug + server calls take seconds); `done` carries its result line."""
    done = Signal(str)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work

    def run(self):
        try:
            self.done.emit(self.work())
        except Exception as error:                      # a step never takes the page down
            self.done.emit("✗ %s" % error)


class InstrumentPlugViewModule(PageWidget):
    """Settings → Administration → Instrument plug… — the factory tool (SPEC_shelly_instrument_memory.md §5, S5/S8),
    master only. One plug, one instrument: the serial IS the plug's device id (N6). Steps, top to bottom: find the
    plug, harden it (standard password, P7), create the instrument on the server, write its data (+ a sealed plugin)
    onto the plug, verify it as an offline login would; or move an instrument whose plug was replaced."""

    compactMainContainer = True

    TIP_FIND = ("Look for the lamp plug: the one the lamp uses, then the one this PC used last, then the network.\n"
                "Shows the plug and its serial (the plug's device id). Changes nothing. Works offline.")
    TIP_HARDEN = ("Prepare the plug for the field: set the standard plug password and keep the output OFF after a "
                  "power cut.\nThe password is saved in this app so the lamp keeps working; every other PC needs it "
                  "too.\nNeeds the server (online only).")
    TIP_CREATE = ("Create the instrument on the server under this plug's serial: a profile for the chosen\n"
                  "spectrometer (model + camera + style; created if that combination is new) with an empty\n"
                  "calibration, and a setup with the chosen plugin. Needs the server.")
    TIP_WRITE = ("Fetch the instrument's signed data from the server (setup, calibration, offline users) and write\n"
                 "it onto the plug — only if it changed. A signed DB plugin is stored too.\n"
                 "Needs the server and your password.")
    TIP_VERIFY = ("Read everything back from the plug and check it as an offline login would: complete, signed by\n"
                  "the server, made for this plug, not newer than this app. Changes nothing. Works offline.")
    TIP_MOVE = ("For a replaced plug: move the instrument from the old serial to this plug (calibration and bound\n"
                "users move with it), then write its data onto this plug. Needs the old serial, the server and your "
                "password.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = None
        self.plugPassword = None
        self.job = None

    def _getPageTitle(self):
        return "Instrument plug"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.plugValue = QLabel("—")
        self.plugValue.setObjectName("InstrumentPlug.plug")
        self.plugValue.setWordWrap(True)
        self.serialValue = QLabel("—")
        self.serialValue.setObjectName("InstrumentPlug.serial")
        self.serialValue.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.modelCombo = QComboBox()
        self.modelCombo.setObjectName("InstrumentPlug.model")
        self.modelCombo.setToolTip("The spectrometer model (e.g. InLight = the ammo box, InVision = the two-cylinder "
                                   "build).\nModel, camera and style together are the spectrometer.")
        self.deviceCombo = QComboBox()
        self.deviceCombo.setObjectName("InstrumentPlug.device")
        self.styleCombo = QComboBox()
        self.styleCombo.setObjectName("InstrumentPlug.style")
        self.pluginCombo = QComboBox()
        self.pluginCombo.setObjectName("InstrumentPlug.plugin")
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setObjectName("InstrumentPlug.password")
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passwordEdit.setPlaceholderText("your login password (the server checks it)")
        self.oldSerialEdit = QLineEdit()
        self.oldSerialEdit.setObjectName("InstrumentPlug.oldSerial")
        self.oldSerialEdit.setPlaceholderText("only to move an instrument from a replaced plug")
        result['form'] = self.createForm([("Plug", self.plugValue), ("Serial", self.serialValue),
                                          ("Spectrometer", self.modelCombo), ("Camera", self.deviceCombo),
                                          ("Style", self.styleCombo), ("Plugin", self.pluginCombo),
                                          ("Your password", self.passwordEdit), ("Old serial", self.oldSerialEdit)])

        buttons = QWidget()
        grid = QGridLayout(buttons)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(Metrics.S)
        self.findButton = self.__button("Find plug", "find", self.onClickedFind, secondary=True)
        self.hardenButton = self.__button("Harden plug", "harden", self.onClickedHarden)
        self.createButton = self.__button("Create on server", "create", self.onClickedCreate)
        self.writeButton = self.__button("Write to plug", "write", self.onClickedWrite)
        self.verifyButton = self.__button("Verify", "verify", self.onClickedVerify, secondary=True)
        self.moveButton = self.__button("Move instrument here", "move", self.onClickedMove, secondary=True)
        for button, tip in ((self.findButton, self.TIP_FIND), (self.hardenButton, self.TIP_HARDEN),
                            (self.createButton, self.TIP_CREATE), (self.writeButton, self.TIP_WRITE),
                            (self.verifyButton, self.TIP_VERIFY), (self.moveButton, self.TIP_MOVE)):
            button.setToolTip(tip)
        for index, button in enumerate((self.findButton, self.hardenButton, self.createButton,
                                        self.writeButton, self.verifyButton, self.moveButton)):
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
        self.__fillCombos()
        self.refresh()
        if self.device is None and self.isMaster():
            self.onClickedFind()

    OFFLINE_NOTE = "Offline: Create, Write, Move and Harden need the server."

    @staticmethod
    def isMaster():
        return CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value)

    @staticmethod
    def isOnline():
        return not CurrentUserSession().isOffline()

    def refresh(self):
        # Find and Verify only talk to the plug ⇒ also offline. The other four steps change the instrument
        # (server rows or the plug's settings) ⇒ online only.
        master, online = self.isMaster(), self.isOnline()
        have = self.device is not None and bool(self.device.deviceId)
        busy = self.job is not None and self.job.isRunning()
        self.findButton.setEnabled(master and not busy)
        self.verifyButton.setEnabled(master and have and not busy)
        for button in (self.hardenButton, self.createButton, self.writeButton, self.moveButton):
            button.setEnabled(master and online and have and not busy)
        if not master:
            self.plugValue.setText("Masters only.")
            self.serialValue.setText("—")
            return
        plugText = self.device.describe() if self.device is not None else "none found"
        self.plugValue.setText(plugText if online else "%s\n%s" % (plugText, self.OFFLINE_NOTE))
        self.serialValue.setText(self.device.deviceId if have else "—")

    def __fillCombos(self):
        from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
        from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
        from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
        from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
        self.modelCombo.clear()
        models = sorted({s.modelName for s in SpectrometerUtil().getSpectrometers().values()
                         if s.spectrometerSensor is not None and not s.spectrometerSensor.isVirtual and s.modelName})
        for modelName in models:
            self.modelCombo.addItem(modelName, modelName)
        self.modelCombo.setCurrentIndex(max(0, self.modelCombo.findData("InLight")))
        self.styleCombo.clear()
        for style in SpectrometerStyleUtil().getSpectrometerStyles().values():
            self.styleCombo.addItem(style.styleName, style.styleId)
        self.styleCombo.setCurrentIndex(max(0, self.styleCombo.findData("GREEN_GOLD")))
        self.deviceCombo.clear()
        for sensor in SpectrometerSensorUtil().getSpectrometerSensors().values():
            if not sensor.isVirtual:
                self.deviceCombo.addItem("%s  (%s:%s)" % (sensor.codeName, sensor.vendorId, sensor.modelId),
                                         sensor.codeName)
        self.deviceCombo.setCurrentIndex(max(0, self.deviceCombo.findData("Dynarex")))
        self.pluginCombo.clear()
        entries = PluginRegistry.listAll(includeDb=self.isOnline(), includeBenchOnly=False) if self.isMaster() else []
        for entry in sorted(entries, key=lambda e: e.version is None):          # versioned DB rows first
            self.pluginCombo.addItem("%s %s" % (entry.title, entry.version or "(built-in)"),
                                     (entry.codeRef, entry.version))

    # --- steps -------------------------------------------------------------------------------------------
    def __run(self, work, onDone=None):
        self.resultLabel.setText("…")
        self.job = _Job(work, self)
        self.job.done.connect(lambda text: self.__finished(text, onDone))
        self.job.start()
        self.refresh()

    def __finished(self, text, onDone):
        self.resultLabel.setText(text)
        if onDone is not None:
            onDone()
        self.refresh()

    def __factory(self):
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        return InstrumentFactoryLogicModule()

    def onClickedFind(self):
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugLocator

        def work():
            self.device, self.plugPassword = PlugLocator().find()
            return "✓ Found %s" % self.device.describe() if self.device is not None else "✗ No plug found."
        self.__run(work)

    def onClickedHarden(self):
        device, password = self.device, self.plugPassword

        def work():
            text = self.__factory().harden(device, password)
            if text.startswith("✓"):
                self.plugPassword = self.__factory().standardPassword()
            return text
        self.__run(work)

    def onClickedCreate(self):
        serial, codeName = self.device.deviceId, self.deviceCombo.currentData()
        modelName, styleId = self.modelCombo.currentData(), self.styleCombo.currentData()
        codeRef, version = self.pluginCombo.currentData() or (None, None)
        if not modelName or not codeName or not styleId or not codeRef:
            self.resultLabel.setText("✗ Choose spectrometer, camera, style and plugin.")
            return
        self.__run(lambda: self.__factory().createOnServer(serial, modelName, codeName, styleId, codeRef, version))

    def onClickedWrite(self):
        device, plugPassword = self.device, self.plugPassword
        username, password = CurrentUserSession().username, self.passwordEdit.text()
        self.__run(lambda: self.__factory().write(device, plugPassword, username, password))

    def onClickedVerify(self):
        device, plugPassword = self.device, self.plugPassword
        self.__run(lambda: self.__factory().verify(device, plugPassword))

    def onClickedMove(self):
        oldSerial = self.oldSerialEdit.text().strip()
        if not oldSerial:
            self.resultLabel.setText("✗ Enter the serial of the replaced plug.")
            return
        device, plugPassword = self.device, self.plugPassword
        username, password = CurrentUserSession().username, self.passwordEdit.text()
        self.__run(lambda: self.__factory().moveHere(device, plugPassword, oldSerial, username, password))

    def onClickedBack(self):
        navigationHandler = ApplicationContextLogicModule().getNavigationHandler()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            navigationHandler.handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
