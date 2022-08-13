import usb
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QTextDocument
from PyQt6.QtWidgets import QGridLayout, QLineEdit, QComboBox, QTextEdit
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.model.util.SpectrometerUtil import SpectrometerUtil
from logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from logic.persistence.database.spectrometer.PersistSpectrometerLogicModule import PersistSpectrometerLogicModule
from logic.persistence.database.spectrometerProfile.PersistSpectrometerProfileLogicModule import \
    PersistSpectrometerProfileLogicModule

from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device import Spectrometer
from model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.camera.SpectrometerViewModule import SpectrometerViewModule


class SpectrometerProfileViewModule(PageWidget):
    model: SpectrometerProfile = None
    spectrometerViewModule: SpectrometerViewModule = None
    spectrometersComboBox:QComboBox = None
    serial:QLineEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        super().initialize()
        self.spectrometersComboBox.currentIndexChanged.connect(self.onSelectedSpectrometer)

    def onSelectedSpectrometer(self, index):

        model = self.spectrometersComboBox.model()
        spectrometers = SpectrometerSensorUtil().getSpectrometerSensors()

        if isinstance(model, QStandardItemModel):
            spectrometer = model.item(index.row()).data()

            if isinstance(spectrometer, Spectrometer):
                self.spectrometerViewModule.setModel(spectrometer)

    def updateSpectrometersComboBox(self):

        spectrometers = SpectrometerUtil().getSpectrometers()

        # videoInputs = QMediaDevices.videoInputs()

        model = QStandardItemModel()

        for spectrometerId, spectrometer in spectrometers.items():
            item = QStandardItem()

            spectrometerName = SpectrometerUtil().getEntityViewName(spectrometer)
            item.setText(spectrometerName)

            spectrometerSensor = SpectrometerSensorUtil().getSensorByCodeName(spectrometer.spectrometerSensor.codeName)

            if spectrometerSensor is None:
                item.setText(item.text() + ' (no such sensor)')
                #item.setEnabled(False)
            else:
                if not SpectrometerSensorUtil().isSensorConnected(spectrometerSensor):
                    item.setText(item.text() + ' (not connected)')
                    #item.setEnabled(False)

            item.setData(spectrometer)
            model.appendRow(item)

        self.spectrometersComboBox.setModel(model)

        return

    def createSpectrometersComboBox(self):
        self.spectrometersComboBox = QComboBox()
        self.updateSpectrometersComboBox()
        return self.spectrometersComboBox

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        saveButton = QPushButton()
        saveButton.setText("Save")
        layout.addWidget(saveButton, 0, 1, 1, 1)
        saveButton.clicked.connect(self.onClickedSaveButton)

        return result

    def onClickedSaveButton(self):

        model = self.getModel()
        model.serial = self.serial.text()

        currentIndex = self.spectrometersComboBox.currentIndex()

        comboBoxModel = self.spectrometersComboBox.model()
        if isinstance(comboBoxModel, QStandardItemModel):
            comboBoxModelItem = comboBoxModel.item(currentIndex)
            selectedSpectrometer = comboBoxModelItem.data()

        if isinstance(selectedSpectrometer, Spectrometer):
            PersistSpectrometerLogicModule().saveSpectrometer(selectedSpectrometer)
            model.spectrometer=selectedSpectrometer
            PersistSpectrometerProfileLogicModule().saveSpectrometerProfile(model)
        pass

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        spectrometersComboBox = self.createLabeledComponent('Spectrometer', self.createSpectrometersComboBox())
        result['spectrometersComboBox'] = spectrometersComboBox

        self.serial = QLineEdit()
        serial = self.createLabeledComponent('serial', self.serial)
        result['serial'] = serial

        self.spectrometerViewModule = SpectrometerViewModule(self)
        self.spectrometerViewModule.initialize()
        result['spectrometerViewModule'] = self.spectrometerViewModule

        self.onSelectedSpectrometer(
            self.spectrometersComboBox.model().index(self.spectrometersComboBox.currentIndex(), 0))

        return result

    def _getPageTitle(self):
        return "Settings > Spectrometer profiles > Spectrometer profile"

    def getModel(self) -> SpectrometerProfile:

        if self.model is None:
            self.model = SpectrometerProfile()
        return self.model

    def setModel(self, model: SpectrometerProfile):
        self.model = model
        self.serial.setText(model.serial)

        spectrometer=model.spectrometer

        if isinstance(spectrometer,Spectrometer):

            comboBoxModel = self.spectrometersComboBox.model()

            for index in range(comboBoxModel.rowCount()):
                comboBoxModelItem = comboBoxModel.item(index)
                someSpectrometer = comboBoxModelItem.data()
                if SpectrometerUtil().getName(someSpectrometer)==SpectrometerUtil().getName(spectrometer):
                    modelIndex=comboBoxModel.index(index,0)
                    self.onSelectedSpectrometer(modelIndex)
                    #self.spectrometersComboBox.setCurrentIndex(index)
                    break

        pass


    def loadView(self, model: SpectrometerProfile):
        self.setModel(model)

        return
