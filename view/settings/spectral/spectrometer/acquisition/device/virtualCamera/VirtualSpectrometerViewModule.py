from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QCheckBox, QPushButton, QFileDialog, QGroupBox, QGridLayout, QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.general.ToggleSwitch import ToggleSwitch
from view.application.widgets.image.BaseImageViewModule import BaseImageViewModule
from view.application.widgets.page.PageWidget import PageWidget

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
        buttonsPanel.setLayout(layout)

        self.openPictureButton=QPushButton('Set picture')
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

    def onClickedOpenPictureButton(self):
        filepath = QFileDialog.getOpenFileName(self, 'Open picture',                                            None, "Image files (*.png *.jpg *.gif)")
        image=QImage(filepath[0])
        ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().setVirtualCameraImage(image)
        self.__getImageViewModule().setImage(image)

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


