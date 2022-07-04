import usb
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QGridLayout, QLineEdit, QComboBox
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.settings.SettingsLogicModule import SettingsLogicModule
from logic.settings.spectral.spectrometer.acquisition.camera.CameraSelectionLogicModule import \
    CameraSelectionLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from view.application.widgets.page.PageWidget import PageWidget


class SpectrometerProfileViewModule(PageWidget):

    model: SpectrometerProfile =None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.camerasComboBox.currentIndexChanged.connect(self.onSelectedSpectralDevice)

    def onSelectedSpectralDevice(self, index):
        model = self.camerasComboBox.model()
        if isinstance(model, QStandardItemModel):
            item = model.item(index)
            spectralDevice = item.data()
            if isinstance(spectralDevice, SpectrometerProfile):
                print('vendor')
                print(spectralDevice.vendorId)

    def updateCamerasComboBox(self):

        settingsLogicModule = SettingsLogicModule()
        supportedSpectralDevices = settingsLogicModule.getSupportedSpectrometerSensors()

        # videoInputs = QMediaDevices.videoInputs()

        model = QStandardItemModel()

        for spectralDeviceName, spectralDevice in supportedSpectralDevices.items():
            item = QStandardItem()
            item.setText(spectralDevice.name + ' (' + spectralDevice.description + ')')
            item.setData(spectralDevice)
            dev = usb.core.find(idVendor=int('0x' + spectralDevice.vendorId, base=16),
                                idProduct=int('0x' + spectralDevice.modelId, base=16))

            if dev is None:
                item.setEnabled(False)
                item.setText(item.text() + ' [not available]')

            model.appendRow(item)

        self.camerasComboBox.setModel(model)

    def createCamerasComboBox(self):
        self.camerasComboBox=QComboBox()
        self.updateCamerasComboBox()
        return self.camerasComboBox

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
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        camerasComboBox = self.createLabeledComponent('camera', self.createCamerasComboBox())
        result['camerasComboBox'] =camerasComboBox
        self.serial=QLineEdit()
        serial=self.createLabeledComponent('serial', self.serial)
        result['serial']=serial

        return result

    def getModel(self) -> SpectrometerProfile:

        if self.model is None:
            self.model=SpectrometerProfile()
        return self.model

