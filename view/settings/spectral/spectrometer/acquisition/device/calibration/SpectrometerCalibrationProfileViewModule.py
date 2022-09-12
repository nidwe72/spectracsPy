from PyQt6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QWidget, QTabWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesViewModule import \
    SpectrometerCalibrationProfileHoughLinesViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationViewModule


class SpectrometerCalibrationProfileViewModule(PageWidget):

    model: SpectrometerCalibrationProfile = None

    tabWidget:QTabWidget=None
    houghLinesViewModule:SpectrometerCalibrationProfileHoughLinesViewModule=None
    wavelengthCalibrationViewModule:SpectrometerCalibrationProfileWavelengthCalibrationViewModule=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _getPageTitle(self):
        if not self._isTopMostPageWidget():
            return "Calibration Profile"
        else:
            return "Settings > Spectrometer profiles > Spectrometer profile > Calibration Profile"

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        if not self._isTopMostPageWidget():

            editCalibrationProfileButton=QPushButton('Edit')
            editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
            result[editCalibrationProfileButton.objectName()]=editCalibrationProfileButton
            editCalibrationProfileButton.clicked.connect(self.onClickedEditButton)

        else:

            self.tabWidget = QTabWidget()

            self.houghLinesViewModule=SpectrometerCalibrationProfileHoughLinesViewModule(self)
            self.houghLinesViewModule.initialize()
            self.tabWidget.addTab(self.houghLinesViewModule,'Region of interest')

            self.wavelengthCalibrationViewModule=SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
            self.wavelengthCalibrationViewModule.initialize()
            self.tabWidget.addTab(self.wavelengthCalibrationViewModule, 'Wavelength calibration')

            result['tabWidget']=self.tabWidget

        return result

    def onClickedEditButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

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
        pass

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)





