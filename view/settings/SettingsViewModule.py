from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton


from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal


class SettingsViewModule(QWidget):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        acquisitionSettingsGroupBox = self.createAcquisitionSettingsGroupBox()
        layout.addWidget(acquisitionSettingsGroupBox, 0, 0, 1, 1)
        layout.setRowStretch(0, 100)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 1, 0, 1, 1)


    def createAcquisitionSettingsGroupBox(self):
        result = QGroupBox("Acquisition")

        layout = QGridLayout()
        result.setLayout(layout)

        cameraSelectionButton = QPushButton()
        cameraSelectionButton.setText("Camera selection")
        layout.addWidget(cameraSelectionButton, 0, 0, 1, 1)
        cameraSelectionButton.clicked.connect(self.onClickedCameraSelectionButton)

        wavelengthCalibrationButton = QPushButton()
        wavelengthCalibrationButton.setText("Wavelength calibration")
        layout.addWidget(wavelengthCalibrationButton, 1, 0, 1, 1)

        # wavelengthCalibrationButton.clicked.connect(self.onClickedWavelengthCalibrationButton)

        regionOfInterestButton = QPushButton()
        regionOfInterestButton.setText("ROI (region of interest)")
        layout.addWidget(regionOfInterestButton, 2, 0, 1, 1)

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
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedCameraSelectionButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("CameraSelectionViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)


