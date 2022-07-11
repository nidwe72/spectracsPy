import usb
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QTextDocument
from PyQt6.QtWidgets import QGridLayout, QLineEdit, QComboBox, QTextEdit
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.model.util.SpectrometerUtil import SpectrometerUtil
from logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from logic.settings.SettingsLogicModule import SettingsLogicModule
from logic.settings.spectral.spectrometer.acquisition.camera.CameraSelectionLogicModule import \
    CameraSelectionLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device import Spectrometer
from model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from view.application.widgets.page.PageWidget import PageWidget

class SpectrometerProfileViewModule(PageWidget):

    model: SpectrometerProfile =None
    spectrometerSensorTextEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spectrometersComboBox.currentIndexChanged.connect(self.onSelectedSpectrometer)

    def onSelectedSpectrometer(self, index):

        model = self.spectrometersComboBox.model()
        spectrometers=SpectrometerSensorUtil.getSupportedSpectrometerSensors()

        if isinstance(model, QStandardItemModel):

            spectrometer = model.item(index.row()).data()

            if isinstance(spectrometer, Spectrometer):
                spectrometerSensor=SpectrometerSensorUtil.getSensorByCodeName(spectrometer.spectrometerSensorCodeName)
                markup=None
                if spectrometerSensor is not None:
                    markup=SpectrometerSensorUtil.getSensorMarkup(spectrometerSensor)

                    markupDocument=QTextDocument()
                    markupDocument.setHtml(markup)

                    self.spectrometerSensorTextEdit.setDocument(markupDocument)

    def updateSpectrometersComboBox(self):

        spectrometers=SpectrometerUtil.getSpectrometers()

        # videoInputs = QMediaDevices.videoInputs()

        model = QStandardItemModel()

        for spectrometerId, spectrometer in spectrometers.items():
            item = QStandardItem()
            item.setText(spectrometer.vendorName+' '+spectrometer.modelName+' '+spectrometer.codeName+' '+spectrometer.spectrometerSensorCodeName)

            spectrometerSensor=SpectrometerSensorUtil.getSensorByCodeName(spectrometer.spectrometerSensorCodeName)

            if spectrometerSensor is None:
                item.setText(item.text() + ' (no such sensor)')
                item.setEnabled(False)
            else:
                if not SpectrometerSensorUtil.isSensorConnected(spectrometerSensor):
                    item.setText(item.text()+' (not connected)')
                    item.setEnabled(False)

            item.setData(spectrometer)
            model.appendRow(item)

        self.spectrometersComboBox.setModel(model)


        return


    def createSpectrometersComboBox(self):
        self.spectrometersComboBox=QComboBox()
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

        print("Save")

        model=self.getModel()
        model.serial=self.serial.text()

        currentIndex=self.camerasComboBox.currentIndex()
        print(currentIndex)

        comboBoxModel=self.camerasComboBox.model()
        if isinstance(comboBoxModel,QStandardItemModel):
            comboBoxModelItem=comboBoxModel.item(currentIndex)
            selectedSpectralDevice=comboBoxModelItem.data()

        if isinstance(selectedSpectralDevice, SpectrometerProfile):
            model.modelId=selectedSpectralDevice.modelId
            model.vendorId = selectedSpectralDevice.vendorId

        cameraSelectionLogicModule=CameraSelectionLogicModule()
        cameraSelectionLogicModule.saveSpectralDevice(model)

        pass

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        spectrometersComboBox = self.createLabeledComponent('Spectrometer', self.createSpectrometersComboBox())
        result['spectrometersComboBox'] =spectrometersComboBox

        self.serial=QLineEdit()
        serial=self.createLabeledComponent('serial', self.serial)
        result['serial']=serial

        result['spectrometerSensorGroupBox'] =self.createSpectrometerSensorGroupBox()

        self.onSelectedSpectrometer(
            self.spectrometersComboBox.model().index(self.spectrometersComboBox.currentIndex(), 0))

        return result

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Spectrometer profiles > Spectrometer profile")
        return result

    def createSpectrometerSensorGroupBox(self):
        result=QGroupBox('Sensor')

        layout=QGridLayout()
        result.setLayout(layout)

        self.spectrometerSensorTextEdit=QTextEdit()
        layout.addWidget(self.spectrometerSensorTextEdit,0,0,1,1)

        return result

    def getModel(self) -> SpectrometerProfile:

        if self.model is None:
            self.model=SpectrometerProfile()
        return self.model

    def setModel(self,model:SpectrometerProfile):
        self.model=model

    def loadView(self,model:SpectrometerProfile):
        self.setModel(model)
        self.serial.setText(model.serial)
        return