from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLineEdit, QPushButton, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil import ApplicationSpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
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


class SpectrometerSetupViewModule(PageWidget):
    """Unified master instrument-setup editor (SPEC_connection_and_calibration_ux.md §11).

    The legacy spectrometer-profile composition — Spectrometer combo + serial + the embedded calibration
    profile (nm/px interpolation graph + Edit -> ROI/wavelength tabs) + read-only device info — plus the
    assignment block: Plugin (picker) and an optional User override (picker). Save persists the profile +
    setup to the server DB via RPC (server-authoritative), independent of virtual vs. real device.
    """

    compactMainContainer = True

    model: SpectrometerProfile = None
    dto: dict = None
    serial: QLineEdit = None
    spectrometersComboBox: QComboBox = None
    spectrometerViewModule: SpectrometerViewModule = None
    spectrometerCalibrationProfileViewModule: SpectrometerCalibrationProfileViewModule = None
    pluginField: QLineEdit = None
    userField: QLineEdit = None

    __pluginCodeRef: str = None
    __userId = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        super().initialize()
        self.spectrometersComboBox.currentIndexChanged.connect(self.onSelectedSpectrometer)

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

    # --- spectrometer combo (full device entities, like the legacy screen) ---

    def updateSpectrometersComboBox(self):
        spectrometers = SpectrometerUtil().getSpectrometers()
        model = QStandardItemModel()
        for spectrometerId, spectrometer in spectrometers.items():
            item = QStandardItem()
            item.setText(SpectrometerUtil().getEntityViewName(spectrometer))
            sensor = SpectrometerSensorUtil().getSensorByCodeName(spectrometer.spectrometerSensor.codeName)
            if sensor is None:
                item.setText(item.text() + ' (no such sensor)')
            elif not ApplicationSpectrometerUtil().isSensorConnected(sensor):
                item.setText(item.text() + ' (not connected)')
            item.setData(spectrometer)
            model.appendRow(item)
        self.spectrometersComboBox.setModel(model)

    def createSpectrometersComboBox(self):
        self.spectrometersComboBox = QComboBox()
        self.spectrometersComboBox.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.spectrometersComboBox.setMinimumContentsLength(1)
        self.updateSpectrometersComboBox()
        return self.spectrometersComboBox

    def onSelectedSpectrometer(self, index):
        spectrometer = self.__spectrometerAt(index)
        if isinstance(spectrometer, Spectrometer):
            self.getModel().spectrometer = spectrometer
            # The calibration wizard's ROI/peak detection reads the ACTIVE profile for the sensor
            # (virtual vs real) — point it at the profile being authored so it captures the right device.
            ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(self.getModel())
            if self.spectrometerViewModule is not None:
                self.spectrometerViewModule.setModel(spectrometer)

    def __spectrometerAt(self, index):
        model = self.spectrometersComboBox.model()
        if not isinstance(model, QStandardItemModel):
            return None
        row = index.row() if isinstance(index, QModelIndex) else index
        item = model.item(row)
        return item.data() if item is not None else None

    def __currentSpectrometer(self):
        return self.__spectrometerAt(self.spectrometersComboBox.currentIndex())

    # --- layout ---

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.serial = QLineEdit()
        self.pluginField = QLineEdit()
        self.pluginField.setReadOnly(True)
        self.userField = QLineEdit()
        self.userField.setReadOnly(True)
        self.userField.setPlaceholderText("optional — normally set at registration")

        # Assignment (Plugin/User) sits directly under the serial and shares the top form grid, so the two
        # rows — fields and their Select buttons — are the same single-line height as Spectrometer/serial.
        result['topForm'] = self.createForm([
            ('Spectrometer', self.createSpectrometersComboBox()),
            ('serial', self.serial),
            ('Plugin', self.__fieldWithButton(self.pluginField, "Select…", self.onClickedSelectPlugin)),
            ('User', self.__fieldWithButton(self.userField, "Select…", self.onClickedSelectUser)),
        ])

        self.spectrometerCalibrationProfileViewModule = SpectrometerCalibrationProfileViewModule(self)
        self.spectrometerCalibrationProfileViewModule.editReturnTarget = "SpectrometerSetupViewModule"
        self.spectrometerCalibrationProfileViewModule.setModel(self.getModel().spectrometerCalibrationProfile)
        self.spectrometerCalibrationProfileViewModule.initialize()
        result['calibration'] = self.spectrometerCalibrationProfileViewModule

        self.spectrometerViewModule = SpectrometerViewModule(self)
        self.spectrometerViewModule.initialize()
        result['device'] = self.spectrometerViewModule

        self.onSelectedSpectrometer(
            self.spectrometersComboBox.model().index(self.spectrometersComboBox.currentIndex(), 0))
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
        self.__pluginCodeRef = plugin.get('codeRef')
        self.pluginField.setText(plugin.get('title') or plugin.get('codeRef') or "")

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

        spectrometer = self.__findSpectrometerByDevice(dto.get('deviceCodeName'))
        if spectrometer is not None:
            profile.spectrometer = spectrometer

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

    def __findSpectrometerByDevice(self, deviceCodeName):
        if not deviceCodeName:
            return None
        for spectrometer in SpectrometerUtil().getSpectrometers().values():
            sensor = spectrometer.spectrometerSensor
            if sensor is not None and sensor.codeName == deviceCodeName:
                return spectrometer
        return None

    def __applyModelToWidgets(self):
        if self.serial is None:
            return
        dto = self.dto or {}
        model = self.getModel()

        self.serial.setText(model.serial or "")
        self.serial.setReadOnly(bool(dto.get('serial')))  # serial is the key — fixed once created

        if model.spectrometer is not None:
            self.__selectSpectrometerInCombo(model.spectrometer)

        if self.spectrometerCalibrationProfileViewModule is not None:
            self.spectrometerCalibrationProfileViewModule.setModel(model.spectrometerCalibrationProfile)

        if model.spectrometer is not None and self.spectrometerViewModule is not None:
            self.spectrometerViewModule.setModel(model.spectrometer)

        self.pluginField.setText(dto.get('pluginTitle') or dto.get('pluginCodeRef') or "")
        self.userField.setText(dto.get('username') or "")

    def __selectSpectrometerInCombo(self, spectrometer):
        comboModel = self.spectrometersComboBox.model()
        if not isinstance(comboModel, QStandardItemModel):
            return
        wanted = SpectrometerUtil().getName(spectrometer)
        for index in range(comboModel.rowCount()):
            candidate = comboModel.item(index).data()
            if candidate is not None and SpectrometerUtil().getName(candidate) == wanted:
                self.spectrometersComboBox.setCurrentIndex(index)
                break

    # --- save (server-authoritative) ---

    def onClickedSaveButton(self):
        serial = self.serial.text().strip()
        spectrometer = self.__currentSpectrometer()
        deviceCodeName = None
        if isinstance(spectrometer, Spectrometer) and spectrometer.spectrometerSensor is not None:
            deviceCodeName = spectrometer.spectrometerSensor.codeName
        if not serial or not deviceCodeName:
            InWindowDialog.notify(self, "Save failed", "Serial and device are required.")
            return

        client = SpectracsPyServerClient()
        result = client.saveSpectrometerProfile(serial, deviceCodeName, self.__harvestCalibration())
        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "profile save failed")
            return

        if self.__pluginCodeRef:
            result = client.saveSpectrometerSetup(serial, self.__pluginCodeRef)
            if not result.get('ok'):
                InWindowDialog.notify(self, "Save failed", result.get('message') or "setup save failed")
                return

        if self.__userId is not None:
            result = client.setRegisteredSerial(self.__userId, serial)
            if not result.get('ok'):
                InWindowDialog.notify(self, "Save failed", result.get('message') or "user assignment failed")
                return

        self.__navigateToList()

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
