import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QPushButton, QFileDialog, QGroupBox, QGridLayout, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.general.ToggleSwitch import ToggleSwitch
from sciens.spectracs.view.application.widgets.image.BaseImageViewModule import BaseImageViewModule
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.logic.appliction.style.Metrics import Metrics

class VirtualSpectrometerViewModule(PageWidget):

    __doSavePhysicallyCapturedImagesComponent:ToggleSwitch=None
    openPictureButton:QPushButton=None
    __imageViewModule:BaseImageViewModule=None
    __doSavePhysicallyCapturedImagesComponent:ToggleSwitch=None

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Virtual spectrometer")
        return result

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        imageViewModule = self.__getImageViewModule()
        result['imageViewModule'] = imageViewModule

        result['doSavePhysicallyCapturedImagesComponent']=self.createLabeledComponent('save physically captured images', self.__getDoSavePhysicallyCapturedImagesComponent())

        buttonsPanel = self.__createButtonsPanel()
        result[buttonsPanel.objectName()] = buttonsPanel

        return result

    def __getDoSavePhysicallyCapturedImagesComponent(self):
        if self.__doSavePhysicallyCapturedImagesComponent is None:
            self.__doSavePhysicallyCapturedImagesComponent=ToggleSwitch(None, Qt.gray, ApplicationStyleLogicModule().getPrimaryColor())
            self.__doSavePhysicallyCapturedImagesComponent.stateChanged.connect(self.onStateChangedDoSavePhysicallyCapturedImagesComponent)

        return self.__doSavePhysicallyCapturedImagesComponent

    def __createButtonsPanel(self):
        buttonsPanel = QWidget()
        buttonsPanel.setObjectName(
            'VirtualSpectrometerViewModule.buttonsPanel')

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # holder adds no indent (spec C8)
        buttonsPanel.setLayout(layout)

        self.openPictureButton=QPushButton('Set image folder…')
        self.openPictureButton.clicked.connect(self.onClickedOpenPictureButton)
        layout.addWidget(self.openPictureButton, 0, 0, 1, 1)

        return buttonsPanel

    def __getImageViewModule(self):
        if self.__imageViewModule is None:
            self.__imageViewModule=BaseImageViewModule()
            self.__imageViewModule.initialize()
        return self.__imageViewModule

    def _getPageTitle(self):
        return "Virtual spectrometer"

    def onStateChangedDoSavePhysicallyCapturedImagesComponent(self):
        isChecked = self.__getDoSavePhysicallyCapturedImagesComponent().isChecked()
        if isChecked:
            print('checked')
        else:
            print('unchecked')
        ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().setDoSavePhysicallyCapturedImages(isChecked)

    # Filename convention inside the chosen folder (SPEC_pumpkin_integration.md A.4).
    __FILENAME_BY_ROLE = {
        VirtualCaptureRole.CALIBRATION: 'calibration.png',
        VirtualCaptureRole.REFERENCE: 'reference.png',
        VirtualCaptureRole.SAMPLE: 'sample.png',
    }

    def onClickedOpenPictureButton(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select virtual capture image folder')
        if not folder:
            return
        virtualSettings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        missing = []
        calibrationImage = None
        for role, filename in self.__FILENAME_BY_ROLE.items():
            path = self.__findImage(folder, filename)
            if path is None:
                missing.append(filename)
                continue
            image = QImage(path)
            virtualSettings.setImage(role, image)
            if role == VirtualCaptureRole.CALIBRATION:
                calibrationImage = image
        if calibrationImage is not None:
            self.__getImageViewModule().setImage(calibrationImage)
        if missing:
            print('virtual capture folder is missing: %s' % ', '.join(missing))

    def __findImage(self, folder, filename):
        target = filename.lower()  # PNG-only, case-insensitive match
        for entry in os.listdir(folder):
            if entry.lower() == target:
                return os.path.join(folder, entry)
        return None

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
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


