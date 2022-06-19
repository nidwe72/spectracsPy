from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal


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


    def updateCamerasComboBox(self):

        videoInputs = QMediaDevices.videoInputs()
        for cameraDevice in videoInputs:
            cameraName = cameraDevice.description()
            # cameraId =str(cameraDevice.id())
            self.camerasComboBox.addItem(cameraName)


            continue

            # print(cameraName)

            # print("cameraDevice.position()")
            # print(cameraDevice.position())
            #
            # print("cameraDevice.photoResolutions()")
            # print(cameraDevice.photoResolutions())
            #
            # print(cameraId)
            # cameraDeviceFormats=cameraDevice.videoFormats()
            # print(cameraDeviceFormats)
            # for cameraDeviceFormat in cameraDeviceFormats:
            #     print(cameraDeviceFormat.resolution())
            #     print(cameraDeviceFormat.pixelFormat())

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
