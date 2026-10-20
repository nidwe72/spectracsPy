from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil import ApplicationSpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.spectral.device.LightSourceControllerType import LightSourceControllerType
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.SpectrometerViewModule import \
    SpectrometerViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileViewModule import \
    SpectrometerCalibrationProfileViewModule

_CAL_FIELDS = ("regionOfInterestX1", "regionOfInterestY1", "regionOfInterestX2", "regionOfInterestY2",
               "interpolationCoefficientA", "interpolationCoefficientB",
               "interpolationCoefficientC", "interpolationCoefficientD")

def _plain(value):
    # catalog values are partly str-Enums (transient seed rows); QComboBox.findData needs the plain string
    return value.value if hasattr(value, "value") else value


_LIGHT_SOURCES = ((LightSourceControllerType.SHELLY_GEN2.value, "Shelly Gen2 plug"),
                  (LightSourceControllerType.NONE.value, "None (lamp switched by hand)"))


class SpectrometerSetupViewModule(PageWidget):
    """Unified master instrument-setup editor (SPEC_connection_and_calibration_ux.md §11) — THE one place an
    instrument is created or edited (SPEC_shelly_instrument_memory.md §11, E3/L3).

    Form (R35): Model · Camera · Style — the spectrometer as the triple, created on the server if new — · Light
    source (NONE / SHELLY_GEN2) · Serial · Plugin · User. With a Shelly the serial is the plug's id, taken from the
    plug picker ([Find plug]) and then read-only; without one it is typed. The camera is preselected from the one
    connected now. Then the embedded calibration profile (nm/px graph + Edit -> ROI/wavelength tabs) and the
    read-only device info. Save persists profile + setup (+ user) to the server DB via RPC (server-authoritative),
    then — with a Shelly — writes the instrument copy onto the plug in the background, only if it changed (E5/R29).
    """

    compactMainContainer = True

    model: SpectrometerProfile = None
    dto: dict = None
    serial: QLineEdit = None
    modelCombo: QComboBox = None
    cameraCombo: QComboBox = None
    styleCombo: QComboBox = None
    lightSourceCombo: QComboBox = None
    spectrometerViewModule: SpectrometerViewModule = None
    spectrometerCalibrationProfileViewModule: SpectrometerCalibrationProfileViewModule = None
    pluginField: QLineEdit = None
    userField: QLineEdit = None

    __pluginCodeRef: str = None
    __pluginVersion: str = None
    __userId = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = None

    def initialize(self):
        super().initialize()
        for combo in (self.modelCombo, self.cameraCombo, self.styleCombo):
            combo.currentIndexChanged.connect(self.onChangedSpectrometer)
        self.lightSourceCombo.currentIndexChanged.connect(self.onChangedLightSource)

    def _getPageTitle(self):
        # Short breadcrumb — matters on limited-width screens (Edwin).
        return "Settings > Spectrometer setup"

    def showEvent(self, event):
        # ① Returning from the ROI/wavelength tabs is just a stack switch — nothing re-renders the graph.
        # Repaint the embedded calibration block from the CURRENT in-memory model (NOT a re-fetch, so a
        # just-edited calibration is preserved) so the curve/points reflect the latest detection.
        super().showEvent(event)
        if self.spectrometerCalibrationProfileViewModule is not None and self.model is not None:
            self.spectrometerCalibrationProfileViewModule.setModel(self.model.spectrometerCalibrationProfile)

    # --- the spectrometer as the triple (model, camera, style) -------------------------------------------

    def __fillCombos(self):
        spectrometers = list(SpectrometerUtil().getSpectrometers().values())
        self.modelCombo.blockSignals(True)
        self.modelCombo.clear()
        for modelName in sorted({s.modelName for s in spectrometers if s.modelName}):
            self.modelCombo.addItem(_plain(modelName), _plain(modelName))
        self.modelCombo.blockSignals(False)

        self.cameraCombo.blockSignals(True)
        self.cameraCombo.clear()
        for sensor in SpectrometerSensorUtil().getSpectrometerSensors().values():
            text = "%s  (%s:%s)" % (sensor.codeName, sensor.vendorId, sensor.modelId)
            if not sensor.isVirtual and ApplicationSpectrometerUtil().isSensorConnected(sensor):
                text += "  — connected"
            self.cameraCombo.addItem(text, _plain(sensor.codeName))
        self.cameraCombo.blockSignals(False)

        self.styleCombo.blockSignals(True)
        self.styleCombo.clear()
        for style in SpectrometerStyleUtil().getSpectrometerStyles().values():
            self.styleCombo.addItem(_plain(style.styleName), _plain(style.styleId))
        self.styleCombo.blockSignals(False)

        self.lightSourceCombo.blockSignals(True)
        self.lightSourceCombo.clear()
        for value, text in _LIGHT_SOURCES:
            self.lightSourceCombo.addItem(text, value)
        self.lightSourceCombo.blockSignals(False)

    def __connectedCameraCodeName(self):
        for sensor in SpectrometerSensorUtil().getSpectrometerSensors().values():
            if not sensor.isVirtual and ApplicationSpectrometerUtil().isSensorConnected(sensor):
                return _plain(sensor.codeName)
        return None

    @staticmethod
    def __select(combo, data):
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def __triple(self):
        return self.modelCombo.currentData(), self.cameraCombo.currentData(), self.styleCombo.currentData()

    def __resolveSpectrometer(self):
        """(the catalog spectrometer for the chosen triple, or the first with that camera, isNew)."""
        modelName, codeName, styleId = self.__triple()
        spectrometers = list(SpectrometerUtil().getSpectrometers().values())
        for spectrometer in spectrometers:
            style = spectrometer.spectrometerStyle
            if _plain(spectrometer.modelName) == modelName and spectrometer.spectrometerSensor is not None \
                    and _plain(spectrometer.spectrometerSensor.codeName) == codeName \
                    and style is not None and _plain(style.styleId) == styleId:
                return spectrometer, False
        fallback = next((s for s in spectrometers
                         if s.spectrometerSensor is not None and _plain(s.spectrometerSensor.codeName) == codeName),
                        None)
        return fallback, True

    def onChangedSpectrometer(self, *args):
        spectrometer, isNew = self.__resolveSpectrometer()
        self.newSpectrometerLabel.setVisible(isNew)
        if isinstance(spectrometer, Spectrometer):
            self.getModel().spectrometer = spectrometer
            # The calibration wizard's ROI/peak detection reads the ACTIVE profile for the sensor
            # (virtual vs real) — point it at the profile being authored so it captures the right device.
            ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(self.getModel())
            if self.spectrometerViewModule is not None:
                self.spectrometerViewModule.setModel(spectrometer)

    # --- light source + serial (§11.3, R35) ----------------------------------------------------------------

    def __isShelly(self):
        return self.lightSourceCombo.currentData() == LightSourceControllerType.SHELLY_GEN2.value

    def onChangedLightSource(self, *args):
        fixed = bool((self.dto or {}).get('serial'))
        shelly = self.__isShelly()
        self.findPlugButton.setEnabled(shelly and not fixed)
        # a Shelly's serial is its device id — picked, never typed; a manual lamp's serial is typed
        self.serial.setReadOnly(fixed or shelly)
        self.serial.setPlaceholderText("[Find plug] — the plug's id is the serial" if shelly
                                       else "the instrument's serial, e.g. ELP-0002")

    def onClickedFindPlug(self):
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugLocator
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import _Job
        self.plugHintLabel.setText("Looking for plugs …")
        self.findPlugButton.setEnabled(False)
        self.__candidates = []

        def work():
            self.__candidates = PlugLocator().candidates()
            return "%d plug(s) found" % len(self.__candidates)
        self.job = _Job(work, self)
        self.job.done.connect(self.__onPlugsFound)
        self.job.start()

    def __onPlugsFound(self, text):
        self.findPlugButton.setEnabled(self.__isShelly())
        candidates = getattr(self, "_SpectrometerSetupViewModule__candidates", [])
        if not candidates:
            self.plugHintLabel.setText("No plug found — is it on the WLAN? (Settings → Administration → "
                                       "Instrument plug → Add new plug)")
            return
        if len(candidates) == 1:
            candidate = candidates[0]
        else:
            buttons = [(c.describe(), index, "secondary") for index, c in enumerate(candidates)]
            buttons.append(("Cancel", None, None))
            chosen = InWindowDialog.choose(self, "Which plug?", "Several plugs answer. ● = holds instrument data, "
                                                                "◐ = known to the server, 🔒 = locked, ○ = not ours. "
                                                                "Instrument plug → Identify blinks one.", buttons)
            if chosen is None:
                self.plugHintLabel.setText("")
                return
            candidate = candidates[chosen]
        self.__pickPlug(candidate)

    def __pickPlug(self, candidate):
        serial = candidate.device.deviceId
        # E3 point 3: a plug that already has a setup ⇒ open THAT setup, never a second one
        if not (self.dto or {}).get('serial'):
            from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupListViewModule import \
                SpectrometerSetupListViewModule
            existing = SpectrometerSetupListViewModule.rowForSerial(serial)
            if existing is not None:
                self.setModel(existing)
                self.plugHintLabel.setText("This plug already has a setup — opened it.")
                return
        self.serial.setText(serial)
        self.plugHintLabel.setText(candidate.describe())

    # --- layout ---

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.modelCombo, self.cameraCombo, self.styleCombo, self.lightSourceCombo = \
            QComboBox(), QComboBox(), QComboBox(), QComboBox()
        for combo, name in ((self.modelCombo, "model"), (self.cameraCombo, "camera"), (self.styleCombo, "style"),
                            (self.lightSourceCombo, "lightSource")):
            combo.setObjectName("SpectrometerSetup.%s" % name)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(1)
        self.modelCombo.setToolTip("The spectrometer model (InLight = the ammo box, InVision = the two-cylinder "
                                   "build).\nModel, camera and style together are the spectrometer — a new "
                                   "combination is created on Save.")
        self.lightSourceCombo.setToolTip("What switches this instrument's lamp. With a Shelly plug the serial is the "
                                         "plug's id\nand the plug also carries the instrument's data for offline use.")
        self.__fillCombos()

        self.serial = QLineEdit()
        self.serial.setObjectName("SpectrometerSetup.serial")
        self.findPlugButton = None
        self.pluginField = QLineEdit()
        self.pluginField.setReadOnly(True)
        self.userField = QLineEdit()
        self.userField.setReadOnly(True)
        self.userField.setPlaceholderText("optional — normally set at registration")

        serialRow = self.__fieldWithButton(self.serial, "Find plug…", self.onClickedFindPlug)
        self.findPlugButton = serialRow.findChild(QPushButton)
        self.findPlugButton.setObjectName("SpectrometerSetup.findPlug")
        result['topForm'] = self.createForm([
            ('Model', self.modelCombo),
            ('Camera', self.cameraCombo),
            ('Style', self.styleCombo),
            ('Light source', self.lightSourceCombo),
            ('Serial', serialRow),
            ('Plugin', self.__fieldWithButton(self.pluginField, "Select…", self.onClickedSelectPlugin)),
            ('User', self.__fieldWithButton(self.userField, "Select…", self.onClickedSelectUser)),
        ])
        self.plugHintLabel = self.createMessageLabel("")
        self.plugHintLabel.setObjectName("SpectrometerSetup.plugHint")
        result['plugHint'] = self.plugHintLabel
        self.newSpectrometerLabel = QLabel("New combination — the spectrometer is created on Save.")
        self.newSpectrometerLabel.setVisible(False)
        result['newSpectrometer'] = self.newSpectrometerLabel

        self.spectrometerCalibrationProfileViewModule = SpectrometerCalibrationProfileViewModule(self)
        self.spectrometerCalibrationProfileViewModule.editReturnTarget = "SpectrometerSetupViewModule"
        self.spectrometerCalibrationProfileViewModule.setModel(self.getModel().spectrometerCalibrationProfile)
        self.spectrometerCalibrationProfileViewModule.initialize()
        result['calibration'] = self.spectrometerCalibrationProfileViewModule

        self.spectrometerViewModule = SpectrometerViewModule(self)
        self.spectrometerViewModule.initialize()
        result['device'] = self.spectrometerViewModule

        self.__applyModelToWidgets()
        return result

    def __fieldWithButton(self, field: QLineEdit, buttonText: str, onClicked):
        container = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)
        layout.addWidget(field, 0, 0, 1, 1)
        layout.setColumnStretch(0, 1)
        button = QPushButton()
        button.setText(buttonText)
        button.clicked.connect(onClicked)
        # The app pins every QAbstractButton to height:50px; override so the Select button matches the
        # single-line field height (Edwin) — otherwise the assignment rows tower over Spectrometer/serial.
        fieldHeight = field.sizeHint().height()
        button.setStyleSheet("height: %dpx;" % fieldHeight)
        button.setMaximumHeight(fieldHeight)
        layout.addWidget(button, 0, 1, 1, 1)
        return container

    def __pluginLabel(self, name, version):
        # "title @ version" once a distributed version is bound; bare title otherwise (built-in / none).
        if not name:
            return ""
        return "%s @ %s" % (name, version) if version else name

    # --- plugin / user pickers (reuse the list screens in SELECT mode) ---

    def onClickedSelectPlugin(self):
        from sciens.spectracs.view.settings.plugin.PluginListViewModule import PluginListViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("PluginListViewModule")
        picker = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(picker, PluginListViewModule):
            picker.enterSelectMode(self.onPluginPicked, "SpectrometerSetupViewModule")
            self.__emitNavigation(navigationSignal)

    def onPluginPicked(self, plugin: dict):
        # B5.1: capture the EXACT version — the picker lists one row per (codeRef, version), so a picked row
        # names the version to bind (F4). The field shows "title @ version".
        self.__pluginCodeRef = plugin.get('codeRef')
        self.__pluginVersion = plugin.get('version')
        self.pluginField.setText(self.__pluginLabel(
            plugin.get('title') or plugin.get('codeRef'), self.__pluginVersion))

    def onClickedSelectUser(self):
        from sciens.spectracs.view.settings.user.UserListViewModule import UserListViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("UserListViewModule")
        picker = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(picker, UserListViewModule):
            picker.enterSelectMode(self.onUserPicked, "SpectrometerSetupViewModule")
            self.__emitNavigation(navigationSignal)

    def onUserPicked(self, user: dict):
        self.__userId = user.get('userId')
        self.userField.setText(user.get('username') or "")

    # --- nav bar ---

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.__navigateToList)

        saveButton = QPushButton()
        saveButton.setText("Save")
        saveButton.setObjectName("SpectrometerSetup.save")
        layout.addWidget(saveButton, 0, 1, 1, 1)
        saveButton.clicked.connect(self.onClickedSaveButton)

        return result

    # --- model wiring ---

    def getModel(self) -> SpectrometerProfile:
        if self.model is None:
            self.model = SpectrometerProfile()
            SpectrometerProfileUtil().initializeSpectrometerProfile(self.model)
        return self.model

    def setModel(self, dto: dict):
        self.dto = dto
        self.__pluginCodeRef = (dto or {}).get('pluginCodeRef')
        self.__pluginVersion = (dto or {}).get('pluginVersion')
        self.__userId = (dto or {}).get('userId')
        self.model = self.__buildModelFromDto(dto)
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def __buildModelFromDto(self, dto: dict) -> SpectrometerProfile:
        profile = SpectrometerProfile()
        SpectrometerProfileUtil().initializeSpectrometerProfile(profile)
        if not dto:
            return profile

        serial = dto.get('serial')
        profile.serial = serial

        if serial:
            bundle = SpectracsPyServerClient().resolveInstrumentBySerial(serial)
            calibration = bundle.get('calibration') if bundle and bundle.get('ok') else None
            if calibration:
                cal = profile.spectrometerCalibrationProfile
                for field in _CAL_FIELDS:
                    value = calibration.get(field)
                    if value is not None:
                        setattr(cal, field, value)
                self.__rebuildSpectralLines(cal, calibration.get('spectralLines'))
                spectrumObj = calibration.get('spectrum')
                if spectrumObj:
                    cal.calibrationSpectrum = Spectrum().fromJson(spectrumObj)
        return profile

    def __rebuildSpectralLines(self, cal, lines):
        # Rebuild transient SpectralLine objects (pixelIndex + a lightweight master-data carrying the
        # nanometer) so the interpolation graph's scatter points come back after reload. Not persisted
        # client-side — display only.
        if not lines:
            return
        rebuilt = []
        for entry in lines:
            if entry.get('pixelIndex') is None:
                continue
            masterData = SpectralLineMasterData()
            masterData.name = entry.get('name')
            masterData.nanometer = entry.get('nanometer')
            spectralLine = SpectralLine()
            spectralLine.pixelIndex = entry.get('pixelIndex')
            spectralLine.spectralLineMasterData = masterData
            rebuilt.append(spectralLine)
        cal.spectralLines = rebuilt

    def __applyModelToWidgets(self):
        if self.serial is None:
            return
        dto = self.dto or {}
        model = self.getModel()
        self.__fillCombos()

        # an existing instrument shows its triple; a new one starts from the connected camera (E3) and a Shelly
        self.__select(self.modelCombo, dto.get('modelName') or "InLight")
        self.__select(self.cameraCombo, dto.get('deviceCodeName') or self.__connectedCameraCodeName() or "Dynarex")
        self.__select(self.styleCombo, dto.get('styleId') or "GREEN_GOLD")
        self.__select(self.lightSourceCombo, dto.get('lightSourceController') or
                      (LightSourceControllerType.SHELLY_GEN2.value if not dto.get('serial')
                       else LightSourceControllerType.NONE.value))

        self.serial.setText(model.serial or "")
        self.plugHintLabel.setText("")
        self.onChangedLightSource()
        self.onChangedSpectrometer()

        if self.spectrometerCalibrationProfileViewModule is not None:
            self.spectrometerCalibrationProfileViewModule.setModel(model.spectrometerCalibrationProfile)

        self.pluginField.setText(self.__pluginLabel(
            dto.get('pluginTitle') or dto.get('pluginCodeRef'), self.__pluginVersion))
        self.userField.setText(dto.get('username') or "")

    # --- save (server-authoritative) ---

    def onClickedSaveButton(self):
        serial = self.serial.text().strip()
        modelName, deviceCodeName, styleId = self.__triple()
        lightSource = self.lightSourceCombo.currentData()
        if not serial or not deviceCodeName or not modelName or not styleId:
            InWindowDialog.notify(self, "Save failed", "Model, camera, style and serial are required."
                                  + (" With a Shelly, [Find plug] gives the serial." if self.__isShelly() else ""))
            return

        client = SpectracsPyServerClient()
        result = client.saveSpectrometerProfile(serial, deviceCodeName, self.__harvestCalibration(), modelName,
                                                styleId, lightSource)
        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "profile save failed")
            return
        if result.get('spectrometerCreated'):
            client.syncSpectrometers()               # the new triple into this PC's catalog

        if self.__pluginCodeRef:
            result = client.saveSpectrometerSetup(serial, self.__pluginCodeRef, self.__pluginVersion)
            if not result.get('ok'):
                InWindowDialog.notify(self, "Save failed", result.get('message') or "setup save failed")
                return

        if self.__userId is not None:
            result = client.setRegisteredSerial(self.__userId, serial)
            if not result.get('ok'):
                InWindowDialog.notify(self, "Save failed", result.get('message') or "user assignment failed")
                return

        if lightSource == LightSourceControllerType.SHELLY_GEN2.value and self.__pluginCodeRef:
            self.__writePlugInBackground(serial)
        self.__navigateToList()

    def __writePlugInBackground(self, serial):
        # E5/R29: the rows are saved; the plug gets the copy in the background — only if it changed — and Save
        # never waits on it. The server hands out the copy only against the user's password ⇒ ask for it once.
        password = InWindowDialog.askPassword(self, "Write the plug?",
                                              "Saved. Your password writes the instrument data onto the plug %s "
                                              "(Cancel: later, from the plug page)." % serial)
        if not password:
            return
        from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugLocator
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import _Job
        from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance
        username = CurrentUserSession().username

        def work():
            candidate = PlugLocator().findBySerial(serial)
            if candidate is None:
                return "Saved — the plug %s was not found, nothing written." % serial
            if candidate.label == "locked":
                return "Saved — the plug %s is locked, nothing written." % serial
            text = InstrumentFactoryLogicModule().write(candidate.device, candidate.password, username, password)
            return ("Saved — plug: " + text.splitlines()[0].lstrip("✓✗ ")) if text else "Saved."
        self.job = _Job(work, self)
        self.job.done.connect(AcquisitionGuidance().emit)
        self.job.start()

    def __harvestCalibration(self):
        cal = self.getModel().spectrometerCalibrationProfile
        if cal is None:
            return None
        result = {}
        for field in _CAL_FIELDS:
            value = getattr(cal, field, None)
            if value is not None and field.startswith("regionOfInterest"):
                value = int(value)
            result[field] = value

        # ③A — the detected lines (pixelIndex <-> master-data nanometer), for the scatter dots + provenance.
        lines = []
        for line in (cal.getSpectralLines() or []):
            masterData = line.spectralLineMasterData
            if line.pixelIndex is None or masterData is None:
                continue
            lines.append({"name": masterData.name, "nanometer": masterData.nanometer,
                          "pixelIndex": int(line.pixelIndex)})
        result["spectralLines"] = lines

        # ③-spectrum — the raw CFL capture via the common Spectrum serialization.
        spectrum = getattr(cal, "calibrationSpectrum", None)
        if spectrum is not None:
            result["spectrum"] = spectrum.toJson()

        return result

    def __navigateToList(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerSetupListViewModule")
        self.__emitNavigation(navigationSignal)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
