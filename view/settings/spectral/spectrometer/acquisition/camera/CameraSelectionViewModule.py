from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.settings.SettingsLogicModule import SettingsLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal

import usb.core

from model.databaseEntity.spectral.device.DbSpectralDevice import DbSpectralDevice


class CameraSelectionViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.camerasComboBox = QComboBox()

        layout = QGridLayout()
        self.setLayout(layout)

        cameraGroupBox = self.createCameraGroupBox()
        layout.addWidget(cameraGroupBox, 0, 0, 1, 1)
        layout.setRowStretch(0, 100)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 1, 0, 1, 1)

        self.camerasComboBox.currentIndexChanged.connect(self.onSelectedSpectralDevice)

    def onSelectedSpectralDevice(self, index):
        model = self.camerasComboBox.model()
        if isinstance(model, QStandardItemModel):
            item = model.item(index)
            spectralDevice = item.data()
            if isinstance(spectralDevice, DbSpectralDevice):
                print('vendor')
                print(spectralDevice.vendorId)

    def updateCamerasComboBox(self):

        settingsLogicModule = SettingsLogicModule()
        supportedSpectralDevices = settingsLogicModule.getSupportedSpectralDevices()

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

    def createCameraGroupBox(self):
        result = QGroupBox("Camera")

        layout = QGridLayout()
        result.setLayout(layout);

        self.updateCamerasComboBox()
        layout.addWidget(self.camerasComboBox, 0, 0, 1, 1)

        return result

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        return result

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)