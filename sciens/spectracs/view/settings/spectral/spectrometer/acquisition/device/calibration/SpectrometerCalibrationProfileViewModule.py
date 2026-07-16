from PySide6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QTabWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
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
from sciens.spectracs.logic.application.style.Metrics import Metrics

_ROI_FIELDS = ("regionOfInterestX1", "regionOfInterestY1", "regionOfInterestX2", "regionOfInterestY2")


class SpectrometerCalibrationProfileViewModule(PageWidget):
    """Embedded: the calibration graph + an Edit button. Top-most (reached via Edit): a two-step WIZARD
    (§11) — Region of interest → Wavelength calibration — with Cancel / Back / Next / Finish, no Save. The
    calibration is held in memory on the shared model; the SpectrometerSetup editor's Save persists it to
    the server. Cancel restores the on-entry snapshot; Next/Finish are disabled until their step is valid."""

    __model: SpectrometerCalibrationProfile = None

    # Where the wizard returns on Finish/Cancel; the embedded block sets this on the shared top-most editor.
    editReturnTarget: str = "SpectrometerSetupViewModule"

    tabWidget: QTabWidget = None
    houghLinesViewModule: SpectrometerCalibrationProfileHoughLinesViewModule = None
    wavelengthCalibrationViewModule: SpectrometerCalibrationProfileWavelengthCalibrationViewModule = None

    cancelButton: QPushButton = None
    backButton: QPushButton = None
    nextButton: QPushButton = None
    finishButton: QPushButton = None

    __spectralLinesInterpolationViewModule: SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule = None
    __snapshot: dict = None
    __detecting: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Graph over its Edit button vertically (Edwin) — unconditional.
        self.verticalLayout = True

    def _getPageTitle(self):
        if not self._isTopMostPageWidget():
            return "Calibration Profile (nanometer/pixel)"
        return "Settings > Spectrometer setup > Calibration"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        if not self._isTopMostPageWidget():
            spectralLinesInterpolationViewModule = self.__getSpectralLinesInterpolationViewModule()
            spectralLinesInterpolationViewModule.initialize()
            result['spectralLinesInterpolationViewModule'] = spectralLinesInterpolationViewModule

            editCalibrationProfileButton = QPushButton('Edit')
            editCalibrationProfileButton.setMinimumWidth(100)
            editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
            result[editCalibrationProfileButton.objectName()] = editCalibrationProfileButton
            editCalibrationProfileButton.clicked.connect(self.onClickedEditButton)
        else:
            self.tabWidget = QTabWidget()
            # Keep the tab bar visible as a STEP INDICATOR (Region of interest / Wavelength calibration) so
            # the user sees which step they're on (Edwin). Next/Back still drive it; currentChanged keeps the
            # nav in sync whether the step changes via a button or a tab click.

            # The sub-views are created in setModel() (which runs before initialize() at construction), so
            # initialize() must be called here UNCONDITIONALLY — otherwise the step content never builds
            # and the tab shows only the nav buttons.
            if self.houghLinesViewModule is None:
                self.houghLinesViewModule = SpectrometerCalibrationProfileHoughLinesViewModule(self)
            self.houghLinesViewModule.initialize()
            self.tabWidget.addTab(self.houghLinesViewModule, 'Region of interest')

            if self.wavelengthCalibrationViewModule is None:
                self.wavelengthCalibrationViewModule = SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
            self.wavelengthCalibrationViewModule.setModel(self.__getModel())
            self.wavelengthCalibrationViewModule.initialize()
            self.tabWidget.addTab(self.wavelengthCalibrationViewModule, 'Wavelength calibration')

            for step in (self.houghLinesViewModule, self.wavelengthCalibrationViewModule):
                step.detectionStarted.connect(self.__onDetectionStarted)
                step.detectionCompleted.connect(self.__onDetectionCompleted)
            self.tabWidget.currentChanged.connect(lambda _index: self.__configureNav())

            result['tabWidget'] = self.tabWidget

        return result

    def onClickedEditButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

        wizard = ApplicationContextLogicModule().getNavigationHandler().getViewModule(someNavigationSignal)
        wizard.editReturnTarget = self.editReturnTarget
        wizard.setModel(self.__getModel())
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    # --- wizard nav bar ---

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setProperty("buttonType", "secondary")
        self.cancelButton.clicked.connect(self.onClickedCancelButton)
        layout.addWidget(self.cancelButton, 0, 0, 1, 1)

        self.backButton = QPushButton("← Back")
        self.backButton.clicked.connect(self.onClickedBackButton)
        layout.addWidget(self.backButton, 0, 1, 1, 1)

        self.nextButton = QPushButton("Next →")
        self.nextButton.clicked.connect(self.onClickedNextButton)
        layout.addWidget(self.nextButton, 0, 2, 1, 1)

        self.finishButton = QPushButton("Finish")
        self.finishButton.clicked.connect(self.onClickedFinishButton)
        layout.addWidget(self.finishButton, 0, 2, 1, 1)  # same slot as Next; only one shows per step

        self.__configureNav()
        return result

    def __configureNav(self):
        if self.cancelButton is None:
            return
        step = self.tabWidget.currentIndex() if self.tabWidget is not None else 0
        model = self.__getModel()
        idle = not self.__detecting

        if self.tabWidget is not None:
            self.tabWidget.tabBar().setEnabled(idle)  # no step switching mid-burst

        self.cancelButton.setVisible(True)
        self.cancelButton.setEnabled(idle)
        self.backButton.setVisible(step == 1)
        self.backButton.setEnabled(idle)
        self.nextButton.setVisible(step == 0)
        self.nextButton.setEnabled(idle and self.__isRoiSet(model))
        self.finishButton.setVisible(step == 1)
        self.finishButton.setEnabled(idle and self.__isCoefficientsSet(model))

    def __isRoiSet(self, model):
        return model is not None and all(getattr(model, field) is not None for field in _ROI_FIELDS)

    def __isCoefficientsSet(self, model):
        return model is not None and model.interpolationCoefficientA is not None

    def __onDetectionStarted(self):
        self.__detecting = True
        self.__configureNav()

    def __onDetectionCompleted(self):
        self.__detecting = False
        self.__configureNav()

    def onClickedNextButton(self):
        if self.tabWidget is not None:
            self.tabWidget.setCurrentIndex(1)  # → __configureNav via currentChanged

    def onClickedBackButton(self):
        if self.tabWidget is not None:
            self.tabWidget.setCurrentIndex(0)

    def onClickedFinishButton(self):
        # Keep the in-memory calibration; the setup editor's Save persists it to the server.
        self.__navigate(self.editReturnTarget)

    def onClickedCancelButton(self):
        # Discard this session's detection: restore the on-entry snapshot onto the shared model.
        self.__restoreSnapshot()
        self.__navigate(self.editReturnTarget)

    def __navigate(self, target):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    # --- snapshot (Cancel = restore) ---

    def __captureSnapshot(self, model):
        if model is None:
            self.__snapshot = None
            return
        self.__snapshot = {
            'roi': tuple(getattr(model, field) for field in _ROI_FIELDS),
            'coefficients': (model.interpolationCoefficientA, model.interpolationCoefficientB,
                             model.interpolationCoefficientC, model.interpolationCoefficientD),
            'spectralLines': list(model.getSpectralLines() or []),
            'calibrationSpectrum': getattr(model, 'calibrationSpectrum', None),
        }

    def __restoreSnapshot(self):
        model = self.__getModel()
        if model is None or self.__snapshot is None:
            return
        for field, value in zip(_ROI_FIELDS, self.__snapshot['roi']):
            setattr(model, field, value)
        (model.interpolationCoefficientA, model.interpolationCoefficientB,
         model.interpolationCoefficientC, model.interpolationCoefficientD) = self.__snapshot['coefficients']
        model.spectralLines = list(self.__snapshot['spectralLines'])
        model.calibrationSpectrum = self.__snapshot['calibrationSpectrum']

    # --- model ---

    def setModel(self, model: SpectrometerCalibrationProfile):
        self.__model = model

        SpectrometerCalibrationProfileUtil().initializeSpectrometerCalibrationProfile(model)

        if self.wavelengthCalibrationViewModule is None:
            self.wavelengthCalibrationViewModule = SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
        self.wavelengthCalibrationViewModule.setModel(model)

        if self.houghLinesViewModule is None:
            self.houghLinesViewModule = SpectrometerCalibrationProfileHoughLinesViewModule(self)
        self.houghLinesViewModule.setModel(model)

        self.__getSpectralLinesInterpolationViewModule().setModel(model)

        # Snapshot for Cancel, and (re)enter the wizard at step 1 (ROI).
        self.__captureSnapshot(model)
        if self.tabWidget is not None:
            self.tabWidget.setCurrentIndex(0)
            self.__detecting = False
            self.__configureNav()

    def __getModel(self) -> SpectrometerCalibrationProfile:
        return self.__model

    def __getSpectralLinesInterpolationViewModule(self) -> SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule:
        if self.__spectralLinesInterpolationViewModule is None:
            self.__spectralLinesInterpolationViewModule = SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule(self)
        return self.__spectralLinesInterpolationViewModule
