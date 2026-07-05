import os

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget

_CAL_FIELDS = ("regionOfInterestX1", "regionOfInterestY1", "regionOfInterestX2", "regionOfInterestY2",
               "interpolationCoefficientA", "interpolationCoefficientB",
               "interpolationCoefficientC", "interpolationCoefficientD")


class SpectrometerProfileAuthoringViewModule(PageWidget):
    """Master profile editor (SPEC_connection_and_calibration_ux.md §4.1.b). Assigning a virtual capture
    folder that contains calibration.png auto-calibrates in the background (ROI + pixel->nm coeffs) and the
    serial-keyed profile is saved to the server."""

    dto: dict = None
    serial: QLineEdit = None
    deviceComboBox: QComboBox = None
    calibrationLabel: QLabel = None
    __calibration: dict = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compactMainContainer = True

    def _getPageTitle(self):
        return "Settings > Spectrometer profiles (authoring) > Profile"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.serial = QLineEdit()
        result['serial'] = self.createLabeledComponent('Serial', self.serial)

        self.deviceComboBox = QComboBox()
        for codeName in self.__deviceCodeNames():
            self.deviceComboBox.addItem(codeName)
        result['device'] = self.createLabeledComponent('Device', self.deviceComboBox)

        loadButton = QPushButton()
        loadButton.setText("Load capture folder (auto-calibrate)")
        loadButton.clicked.connect(self.onClickedLoadFolderButton)
        result['loadFolder'] = loadButton

        self.calibrationLabel = QLabel("No calibration yet.")
        self.calibrationLabel.setWordWrap(True)
        result['calibration'] = self.calibrationLabel

        self.__applyModelToWidgets()
        return result

    def __deviceCodeNames(self):
        codeNames = []
        try:
            for spectrometer in SpectrometerUtil().getSpectrometers().values():
                sensor = spectrometer.spectrometerSensor
                if sensor is not None and sensor.codeName not in codeNames:
                    codeNames.append(sensor.codeName)
        except Exception as exception:
            print("SpectrometerProfileAuthoring: could not list devices: %s" % exception)
        return sorted(codeNames)

    def onClickedLoadFolderButton(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select virtual capture image folder')
        if not folder:
            return
        path = os.path.join(folder, 'calibration.png')
        if not os.path.isfile(path):
            InWindowDialog.notify(self, "No calibration image",
                                  "The folder has no calibration.png — cannot auto-calibrate.")
            return
        image = QImage(path)
        if image.isNull():
            InWindowDialog.notify(self, "Bad image", "calibration.png could not be read.")
            return
        try:
            calibrationProfile = PlaygroundCalibrationLogicModule().calibrateImage(image)
        except Exception as exception:
            InWindowDialog.notify(self, "Calibration failed", "Auto-calibration failed: %s" % exception)
            return
        self.__calibration = {}
        for field in _CAL_FIELDS:
            value = getattr(calibrationProfile, field, None)
            if value is not None and field.startswith("regionOfInterest"):
                value = int(value)
            self.__calibration[field] = value
        self.calibrationLabel.setText(
            "Calibrated: ROI x[%s..%s] y[%s..%s], nm(px)=%.3g x^3 + %.3g x^2 + %.3g x + %.1f" % (
                self.__calibration['regionOfInterestX1'], self.__calibration['regionOfInterestX2'],
                self.__calibration['regionOfInterestY1'], self.__calibration['regionOfInterestY2'],
                self.__calibration['interpolationCoefficientA'], self.__calibration['interpolationCoefficientB'],
                self.__calibration['interpolationCoefficientC'], self.__calibration['interpolationCoefficientD']))

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

    def getModel(self):
        return self.dto

    def setModel(self, dto: dict):
        self.dto = dto
        self.__calibration = None
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def __applyModelToWidgets(self):
        if self.serial is None:
            return
        dto = self.dto or {}
        self.serial.setText(dto.get('serial') or "")
        self.serial.setReadOnly(dto.get('serial') is not None)  # serial is the key — fixed once created
        device = dto.get('deviceCodeName')
        if device is not None:
            index = self.deviceComboBox.findText(device)
            if index >= 0:
                self.deviceComboBox.setCurrentIndex(index)
        if self.calibrationLabel is not None:
            self.calibrationLabel.setText("No calibration yet." if self.__calibration is None
                                          else self.calibrationLabel.text())

    def onClickedSaveButton(self):
        serial = self.serial.text().strip()
        deviceCodeName = self.deviceComboBox.currentText().strip()
        if not serial or not deviceCodeName:
            InWindowDialog.notify(self, "Save failed", "Serial and device are required.")
            return
        result = SpectracsPyServerClient().saveSpectrometerProfile(serial, deviceCodeName, self.__calibration)
        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "save failed")
            return
        self.__navigateToList()

    def __navigateToList(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerProfileAuthoringListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
