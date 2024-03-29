from PySide6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QTabWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from sciens.spectracs.logic.persistence.database.spectrometerCalibrationProfile.PersistSpectrometerCalibrationProfileLogicModule import \
    PersistSpectrometerCalibrationProfileLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesViewModule import \
    SpectrometerCalibrationProfileHoughLinesViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule import \
    SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationViewModule


class SpectrometerCalibrationProfileViewModule(PageWidget):

    __model: SpectrometerCalibrationProfile = None

    tabWidget:QTabWidget=None
    houghLinesViewModule:SpectrometerCalibrationProfileHoughLinesViewModule=None
    wavelengthCalibrationViewModule:SpectrometerCalibrationProfileWavelengthCalibrationViewModule=None

    __spectralLinesInterpolationViewModule:SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verticalLayout=False

    def _getPageTitle(self):
        if not self._isTopMostPageWidget():
            return "Calibration Profile (nanometer/pixel)"
        else:
            return "Settings > Spectrometer profiles > Spectrometer profile > Calibration Profile"

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        if not self._isTopMostPageWidget():

            spectralLinesInterpolationViewModule = self.__getSpectralLinesInterpolationViewModule()
            spectralLinesInterpolationViewModule.initialize()
            result['spectralLinesInterpolationViewModule'] = spectralLinesInterpolationViewModule

            editCalibrationProfileButton=QPushButton('Edit')
            editCalibrationProfileButton.setMinimumWidth(100)
            editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
            result[editCalibrationProfileButton.objectName()]=editCalibrationProfileButton
            editCalibrationProfileButton.clicked.connect(self.onClickedEditButton)


        else:

            self.tabWidget = QTabWidget()

            if self.houghLinesViewModule is None:
                self.houghLinesViewModule=SpectrometerCalibrationProfileHoughLinesViewModule(self)
            # self.houghLinesViewModule.setStylesheetOnlySelf("border:1px solid #00000000;")
            self.houghLinesViewModule.initialize()
            self.tabWidget.addTab(self.houghLinesViewModule,'Region of interest')

            if self.wavelengthCalibrationViewModule is None:
                self.wavelengthCalibrationViewModule=SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
            self.wavelengthCalibrationViewModule.setModel(self.__getModel())
            # self.wavelengthCalibrationViewModule.setStylesheetOnlySelf("border:1px solid #00000000;")
            self.wavelengthCalibrationViewModule.initialize()
            self.tabWidget.addTab(self.wavelengthCalibrationViewModule, 'Wavelength calibration')

            result['tabWidget']=self.tabWidget

        return result

    def onClickedEditButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

        spectrometerCalibrationProfileViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(someNavigationSignal)
        spectrometerCalibrationProfileViewModule.setModel(self.__getModel())
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
        model = self.__getModel()
        PersistSpectrometerCalibrationProfileLogicModule().saveSpectrometerCalibrationProfile(model)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def setModel(self,model: SpectrometerCalibrationProfile):
        self.__model=model

        SpectrometerCalibrationProfileUtil().initializeSpectrometerCalibrationProfile(model)

        if self.wavelengthCalibrationViewModule is None:
            self.wavelengthCalibrationViewModule = SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
        self.wavelengthCalibrationViewModule.setModel(model)

        if self.houghLinesViewModule is None:
            self.houghLinesViewModule = SpectrometerCalibrationProfileHoughLinesViewModule(self)
        self.houghLinesViewModule.setModel(model)

        self.__getSpectralLinesInterpolationViewModule().setModel(model)

    def __getModel(self)->SpectrometerCalibrationProfile:
        return self.__model

    def __getSpectralLinesInterpolationViewModule(self)->SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule:
        if self.__spectralLinesInterpolationViewModule is None:
            self.__spectralLinesInterpolationViewModule=SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule(self)
        return self.__spectralLinesInterpolationViewModule