import os
import threading

from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QGroupBox, QLineEdit, QDialog, \
    QVBoxLayout, QLabel
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.CalibrationAlgorithm import CalibrationAlgorithm
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.video.SpectrometerCalibrationProfileWavelengthCalibrationVideoThread import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoThread
from sciens.spectracs.logic.appliction.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.model.signal import SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileSpectralLinesViewModule import \
    SpectrometerCalibrationProfileSpectralLinesViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule


class SpectrometerCalibrationProfileWavelengthCalibrationViewModule(PageWidget):

    # Wizard (§11): lock nav during a burst and refresh Finish validity when peak detection finishes.
    detectionStarted = Signal()
    detectionCompleted = Signal()

    model:SpectrometerCalibrationProfile=None

    detectPeaksButton: QPushButton=None
    expectedDetectionButton: QPushButton = None
    wavelengthCalibrationVideoThread: SpectrometerCalibrationProfileWavelengthCalibrationVideoThread = None
    wavelengthCalibrationVideoViewModule: SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule = None

    coefficientAComponent: QLineEdit = None
    coefficientBComponent: QLineEdit = None
    coefficientCComponent: QLineEdit = None
    coefficientDComponent: QLineEdit = None
    spectrometerCalibrationProfileSpectralLinesViewModule:SpectrometerCalibrationProfileSpectralLinesViewModule=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        if self.wavelengthCalibrationVideoViewModule is None:
            self.wavelengthCalibrationVideoViewModule = SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule()
        self.wavelengthCalibrationVideoViewModule.setModel(self.getModel())
        result['wavelengthCalibrationVideoViewModule'] = self.wavelengthCalibrationVideoViewModule

        mainWidget = self.createMainWidget()
        result['mainWidget'] = mainWidget

        buttonsPanel = self.createButtonsPanel()
        result[buttonsPanel.objectName()] = buttonsPanel

        return result

    def createButtonsPanel(self):
        buttonsPanel = QWidget()
        buttonsPanel.setObjectName(
            'SpectrometerCalibrationProfileViewModule.buttonsPanel')

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # holder adds no indent (spec C8)
        buttonsPanel.setLayout(layout)

        # Phase 3: algorithm selection seam. Only HEURISTIC is wired; RANSAC modes are placeholders
        # that get dispatched to a "not yet implemented" notice in onClickedDetectPeaksButtonNew.
        self.expectedDetectionButton = QPushButton('help: expected detection')
        self.expectedDetectionButton.setStyleSheet(
            "background-color: %s;" % ApplicationStyleLogicModule().getSecondaryColor().name())
        self.expectedDetectionButton.clicked.connect(self.onClickedExpectedDetectionButton)
        layout.addWidget(self.expectedDetectionButton, 0, 0, 1, 1)

        self.detectPeaksButton = QPushButton('Detect peaks')
        self.detectPeaksButton.clicked.connect(self.onClickedDetectPeaksButton)
        layout.addWidget(self.detectPeaksButton, 0, 1, 1, 1)
        return buttonsPanel

    def getSelectedAlgorithm(self) -> str:
        return CalibrationAlgorithm.HEURISTIC

    def _resourcePath(self, name):
        directory = os.path.dirname(os.path.abspath(__file__))
        while directory != os.path.dirname(directory):
            candidate = os.path.join(directory, 'resource', name)
            if os.path.exists(candidate):
                return candidate
            directory = os.path.dirname(directory)
        return os.path.join('resource', name)

    def onClickedExpectedDetectionButton(self):
        # Documentation: show where the app's target spectral lines should appear in a CFL spectrum.
        # In-window (no separate QDialog window) — §G3b.
        pixmap = QPixmap(self._resourcePath('expectedDetection.png'))
        InWindowDialog.showImage(self, 'Expected detection — target spectral lines', pixmap)

    def onClickedDetectPeaksButton(self):
        self.onClickedDetectPeaksButtonNew()

    def onClickedDetectPeaksButtonNew(self):

        calibrationProfile = self.getModel()

        # Fix C: peak detection needs the Region of Interest produced by the first tab. Without it
        # acquisition crashes on a None ROI, so guard and tell the user what to do first.
        if calibrationProfile is None \
                or calibrationProfile.regionOfInterestY1 is None \
                or calibrationProfile.regionOfInterestY2 is None:
            InWindowDialog.notify(
                self,
                "Region of interest required",
                "Please run 'Detect Region of Interest' on the 'Region of interest' tab "
                "(and Save) before detecting peaks.")
            return

        # Dispatch on the selected algorithm. The chosen matcher runs in the video view module's
        # final-frame handler; pass the selection down so it knows which matcher to use.
        algorithm = self.getSelectedAlgorithm()
        if not CalibrationAlgorithm.isImplemented(algorithm):
            InWindowDialog.notify(
                self,
                "Not yet implemented",
                f"'{CalibrationAlgorithm.getLabel(algorithm)}' is not implemented yet. "
                f"Please use '{CalibrationAlgorithm.getLabel(CalibrationAlgorithm.HEURISTIC)}'.")
            return
        if self.wavelengthCalibrationVideoViewModule is not None:
            self.wavelengthCalibrationVideoViewModule.setAlgorithm(algorithm)

        self.wavelengthCalibrationVideoThread = SpectrometerCalibrationProfileWavelengthCalibrationVideoThread()
        # Fix A: hand the peak-detection thread the same calibration profile this view edited (which
        # carries the ROI), instead of letting it re-fetch a possibly-stale one from ApplicationSettings.
        self.wavelengthCalibrationVideoThread.setCalibrationProfile(calibrationProfile)

        spectrometerProfile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        sensor = spectrometerProfile.spectrometer.spectrometerSensor
        isVirtual = sensor.isVirtual
        self.wavelengthCalibrationVideoThread.setIsVirtual(isVirtual)

        # Real camera: AUTO-EXPOSE the peak-detection burst so it adapts to the lamp (brightness drifts as the CFL
        # warms up) and — crucially — keeps the emission lines UNCLIPPED. A saturated line desaturates to white and
        # loses the colour the anchor detection depends on (SPEC_capture_quality.md §14.6), so the detection then
        # mis-anchors green onto the yellow line; a FIXED exposure clips once the lamp warms past it. The sweep runs
        # synchronously in the capture thread BEFORE the 50-frame burst (the base run loop picks up the request).
        if not isVirtual:
            deviceIndex = SensorCaptureIndexResolver().resolveCaptureIndex(sensor)
            if deviceIndex is not None:
                self.wavelengthCalibrationVideoThread.setDeviceId(deviceIndex)
            self.wavelengthCalibrationVideoThread.autoExposureProgress.connect(self.__onAutoExposeProgress)
            self.wavelengthCalibrationVideoThread.requestAutoExpose(1, 500)

        self.wavelengthCalibrationVideoThread.videoThreadSignal.connect(self.handleWavelengthCalibrationVideoSignal)
        self.wavelengthCalibrationVideoThread.setFrameCount(50)

        self.detectionStarted.emit()
        self.wavelengthCalibrationVideoThread.start()


    def __onAutoExposeProgress(self, probeIndex, totalProbes):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = totalProbes
        signal.currentStepIndex = min(probeIndex, totalProbes)
        signal.text = "Auto-exposing… [%d/%d]" % (signal.currentStepIndex, totalProbes)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def handleWavelengthCalibrationVideoSignal(self, event: threading.Event,
                                               videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        applicationStatusSignal = ApplicationStatusSignal()
        applicationStatusSignal.isStatusReset = False
        applicationStatusSignal.stepsCount = videoSignal.framesCount
        applicationStatusSignal.currentStepIndex = videoSignal.currentFrameIndex
        applicationStatusSignal.text = f"detecting peaks > step [{applicationStatusSignal.currentStepIndex+1}/{applicationStatusSignal.stepsCount}]"

        # print(f"applicationStatusSignal.stepsCount:{applicationStatusSignal.stepsCount}");
        # print(f"applicationStatusSignal.currentStepIndex:{applicationStatusSignal.currentStepIndex}");

        self.wavelengthCalibrationVideoViewModule.handleVideoThreadSignal(videoSignal)

        if applicationStatusSignal.stepsCount-1 == applicationStatusSignal.currentStepIndex:

            self.coefficientAComponent.setText(str(videoSignal.model.interpolationCoefficientA))
            self.coefficientBComponent.setText(str(videoSignal.model.interpolationCoefficientB))
            self.coefficientCComponent.setText(str(videoSignal.model.interpolationCoefficientC))
            self.coefficientDComponent.setText(str(videoSignal.model.interpolationCoefficientD))

            self.spectrometerCalibrationProfileSpectralLinesViewModule.setModel(videoSignal.model)

            self._warnIfImplausibleCalibration(videoSignal.model)

            applicationStatusSignal.isStatusReset = True

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
            applicationStatusSignal)

        if applicationStatusSignal.isStatusReset:
            self.detectionCompleted.emit()

        event.set()

    def _warnIfImplausibleCalibration(self, model):
        # Phase 4 guardrail: sanity-check the detected anchors so a collapsed/mis-matched calibration
        # (e.g. green and red pinned a few pixels apart, giving an absurd local dispersion) is flagged
        # instead of being silently saved. Checks that wavelength rises with pixel position and that
        # the per-segment dispersion (nm/pixel) is roughly uniform.
        lines = [line for line in (model.getSpectralLines() or []) if line.spectralLineMasterData is not None]
        if len(lines) < 3:
            return
        lines = sorted(lines, key=lambda line: line.pixelIndex)
        dispersions = []
        for i in range(len(lines) - 1):
            pixelGap = lines[i + 1].pixelIndex - lines[i].pixelIndex
            if pixelGap <= 0:
                dispersions = [-1.0]
                break
            nmGap = lines[i + 1].spectralLineMasterData.nanometer - lines[i].spectralLineMasterData.nanometer
            dispersions.append(nmGap / pixelGap)
        median = sorted(dispersions)[len(dispersions) // 2]
        implausible = any(d <= 0 for d in dispersions) or median <= 0 or \
            any(d > 4 * median or d < median / 4 for d in dispersions)
        if implausible:
            InWindowDialog.notify(
                self,
                "Calibration looks implausible",
                "The detected spectral lines do not increase smoothly in wavelength with pixel position "
                "(some anchors are likely mis-detected). The calibration is probably wrong — re-check the "
                "spectrum and Region of Interest before saving.")

    def createPolynomialCoefficientsGroupBox(self):
        result = QGroupBox("Polynomial coefficients")

        layout = QGridLayout()
        result.setLayout(layout)
        Metrics.applyPanelPadding(layout)

        self.coefficientAComponent = QLineEdit()
        self.coefficientAComponent.setReadOnly(True)
        layout.addWidget(self.createLabeledComponent('A', self.coefficientAComponent), 0, 0, 1, 1)

        self.coefficientBComponent = QLineEdit()
        self.coefficientBComponent.setReadOnly(True)
        layout.addWidget(self.createLabeledComponent('B', self.coefficientBComponent), 0, 1, 1, 1)

        self.coefficientCComponent = QLineEdit()
        self.coefficientCComponent.setReadOnly(True)
        layout.addWidget(self.createLabeledComponent('C', self.coefficientCComponent), 1, 0, 1, 1)

        self.coefficientDComponent = QLineEdit()
        self.coefficientDComponent.setReadOnly(True)
        layout.addWidget(self.createLabeledComponent('D', self.coefficientDComponent), 1, 1, 1, 1)

        return result


    def createMainWidget(self):
        result = QWidget()
        resultLayout = QGridLayout()
        resultLayout.setContentsMargins(0, 0, 0, 0)  # holder adds no indent (spec C8)
        result.setLayout(resultLayout)
        resultLayout.addWidget(self.createPolynomialCoefficientsGroupBox(), 0, 0, 1, 1)

        self.spectrometerCalibrationProfileSpectralLinesViewModule=SpectrometerCalibrationProfileSpectralLinesViewModule(self)
        self.spectrometerCalibrationProfileSpectralLinesViewModule.setModel(self.getModel())
        self.spectrometerCalibrationProfileSpectralLinesViewModule.initialize()
        resultLayout.addWidget(self.spectrometerCalibrationProfileSpectralLinesViewModule, 1, 0, 1, 1)

        return result

    def initialize(self):
        super().initialize()

    def setModel(self,model:SpectrometerCalibrationProfile):
        self.model=model

        if self.coefficientAComponent is None:
            self.coefficientAComponent=QLineEdit()
            self.coefficientAComponent.setReadOnly(True)
        if model.interpolationCoefficientA is None:
            self.coefficientAComponent.setText('')
        else:
            self.coefficientAComponent.setText(str(model.interpolationCoefficientA))

        if self.coefficientBComponent is None:
            self.coefficientBComponent=QLineEdit()
            self.coefficientBComponent.setReadOnly(True)
        if model.interpolationCoefficientB is None:
            self.coefficientBComponent.setText('')
        else:
            self.coefficientBComponent.setText(str(model.interpolationCoefficientB))

        if self.coefficientCComponent is None:
            self.coefficientCComponent=QLineEdit()
            self.coefficientCComponent.setReadOnly(True)
        if model.interpolationCoefficientC is None:
            self.coefficientCComponent.setText('')
        else:
            self.coefficientCComponent.setText(str(model.interpolationCoefficientC))

        if self.coefficientDComponent is None:
            self.coefficientDComponent=QLineEdit()
            self.coefficientDComponent.setReadOnly(True)
        if model.interpolationCoefficientD is None:
            self.coefficientDComponent.setText('')
        else:
            self.coefficientDComponent.setText(str(model.interpolationCoefficientD))


        if self.wavelengthCalibrationVideoViewModule is None:
            self.wavelengthCalibrationVideoViewModule = SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule()
        self.wavelengthCalibrationVideoViewModule.setModel(model)

        if self.spectrometerCalibrationProfileSpectralLinesViewModule is None:
            self.spectrometerCalibrationProfileSpectralLinesViewModule=SpectrometerCalibrationProfileSpectralLinesViewModule(self)
        self.spectrometerCalibrationProfileSpectralLinesViewModule.setModel(model)



    def getModel(self)->SpectrometerCalibrationProfile:
        return self.model

