import numpy as np

from PySide6.QtCore import Qt, QEventLoop, QTimer, QRect
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QSlider, QCheckBox, QTabWidget, QStackedWidget, QScrollArea, QSizePolicy)

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.appliction.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.appliction.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
from sciens.spectracs.logic.appliction.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.acquisition.BenchRoiLogicModule import BenchRoiLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
from sciens.spectracs.logic.spectral.plugin.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, TRANSMISSION, ABSORPTION
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.development.DevCaptureVideoViewModule import DevCaptureVideoViewModule
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget


class DevMeasurementBenchViewModule(PageWidget):
    """Master "Swiss-knife" measurement bench (SPEC_dev_measure_bench.md). A generic real-camera run of the
    same pipeline an end-user plugin drives — capture REFERENCE + SAMPLE, compute transmission + absorption —
    without any use-case verdict. Backed by a transiently-injected DevSpectralPlugin; capture is owned by the
    view (real camera + exposure), extraction by ImageSpectrumAcquisitionLogicModule (shared). Transmission
    geometry only (sample between bulb and camera). Master-only; ephemeral (no saved runs)."""

    __EXPOSURE_MIN = 1
    __EXPOSURE_MAX = 500
    __EXPOSURE_FALLBACK = 150
    __AUTO_EXPOSE_MAX_PROBES = 8
    __FRAME_CHOICES = ["10", "20", "50"]
    __DEFAULT_FRAMES = "20"

    # Bench analysis window (SPEC_dev_measure_bench.md §12): the calibration ROI clips the VIS band, so the
    # bench temporarily widens the in-memory ROI to span this wavelength range (clamped to the raster).
    __NM_MIN = 400.0
    __NM_MAX = 700.0

    __REF_COLOR = "#5DADE2"      # reference spectrum (blue)
    __SAMPLE_COLOR = "#F5B041"   # sample spectrum (orange)
    __FRAME_COLOR = "#777777"    # per-frame traces (gray)
    __MEAN_COLOR = "#2ECC71"     # mean spectrum (green)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__resolver = SensorCaptureIndexResolver()
        self.__sensor = None
        self.__resolvedIndex = None
        self.__videoThread = None
        self.__latestImage = None
        self.__autoExposing = False

        self.__engine = None
        self.__workflow = None
        self.__cursor = 0
        self.__phases = [SpectralWorkflowPhaseType.ACQUISITION, SpectralWorkflowPhaseType.PROCESSING]

        self.__activeRole = REFERENCE
        self.__lockedExposure = None
        self.__roleSpectra = {}            # role -> extracted Spectrum (with N captured frames)
        self.__representativeFrames = {}   # role -> QImage (preview-only middle frame)
        self.__savedRoiX = None            # (x1, x2) authored originals while the extended window is applied

        # widgets
        self.__messageLabel = None
        self.__stepBar = None
        self.__stack = None
        self.__videoViewModule = None
        self.__statusLabel = None
        self.__roleComboBox = None
        self.__framesComboBox = None
        self.__exposureSlider = None
        self.__exposureLabel = None
        self.__autoExposureCheckBox = None
        self.__captureButton = None
        self.__rolePlot = None
        self.__processingTabs = None
        self.__backButton = None
        self.__cancelButton = None
        self.__nextButton = None

    def _getPageTitle(self):
        return "Settings > Development > Measurement bench"

    # --- page scaffold ---

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.__messageLabel = self.createMessageLabel("")
        result["message"] = self.__messageLabel
        self.__stepBar = StepBarWidget()
        result["stepBar"] = self.__stepBar
        self.__stack = QStackedWidget()
        self.__stack.addWidget(self.__buildAcquisitionPanel())   # index 0
        self.__stack.addWidget(self.__buildProcessingPage())     # index 1
        result["stack"] = self.__stack
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        self.__backButton = QPushButton("← Back")
        self.__backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self.__backButton, 0, 0, 1, 1)
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")
        self.__cancelButton.clicked.connect(self.__goToSettings)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__nextButton = QPushButton("Next →")
        self.__nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self.__nextButton, 0, 2, 1, 1)
        return result

    # --- acquisition panel (single shared live preview + role toggle) ---

    def __buildAcquisitionPanel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)
        panel.setLayout(layout)

        hint = self.createMessageLabel("Transmission geometry — place the sample between the bulb and the "
                                       "camera. Capture the reference (blank) first, then the sample.")
        layout.addWidget(hint)

        self.__videoViewModule = DevCaptureVideoViewModule()
        self.__videoViewModule.setObjectName("DevMeasurementBenchViewModule.videoViewModule")
        layout.addWidget(self.__videoViewModule)

        self.__statusLabel = self.createMessageLabel("")
        layout.addWidget(self.__statusLabel)

        controls = QWidget()
        controls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        controlsLayout = QGridLayout()
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.setSpacing(Metrics.S)
        controls.setLayout(controlsLayout)

        self.__roleComboBox = QComboBox()
        self.__roleComboBox.addItem("Reference", REFERENCE)
        self.__roleComboBox.addItem("Sample", SAMPLE)
        self.__roleComboBox.currentIndexChanged.connect(self.__onRoleChanged)
        controlsLayout.addWidget(self.createLabeledComponent("Capture", self.__roleComboBox), 0, 0, 1, 2)

        self.__framesComboBox = QComboBox()
        self.__framesComboBox.addItems(self.__FRAME_CHOICES)
        self.__framesComboBox.setCurrentText(self.__DEFAULT_FRAMES)
        controlsLayout.addWidget(self.createLabeledComponent("Frames", self.__framesComboBox), 1, 0, 1, 2)

        self.__exposureSlider = QSlider(Qt.Orientation.Horizontal)
        self.__exposureSlider.setMinimum(self.__EXPOSURE_MIN)
        self.__exposureSlider.setMaximum(self.__EXPOSURE_MAX)
        self.__exposureSlider.valueChanged.connect(self.__onExposureChanged)
        self.__exposureLabel = QLabel("")
        self.__autoExposureCheckBox = QCheckBox("auto-exposure")
        self.__autoExposureCheckBox.setChecked(True)
        self.__autoExposureCheckBox.toggled.connect(self.__updateControls)
        exposureRow = QWidget()
        exposureRowLayout = QGridLayout()
        exposureRowLayout.setContentsMargins(0, 0, 0, 0)
        exposureRowLayout.setSpacing(Metrics.S)
        exposureRow.setLayout(exposureRowLayout)
        exposureRowLayout.addWidget(self.__exposureSlider, 0, 0, 1, 1)
        exposureRowLayout.addWidget(self.__exposureLabel, 0, 1, 1, 1)
        exposureRowLayout.addWidget(self.__autoExposureCheckBox, 0, 2, 1, 1)
        exposureRowLayout.setColumnStretch(0, 70)
        exposureRowLayout.setColumnStretch(1, 10)
        exposureRowLayout.setColumnStretch(2, 20)
        controlsLayout.addWidget(self.createLabeledComponent("Exposure", exposureRow), 2, 0, 1, 2)

        self.__captureButton = QPushButton("Capture reference")
        self.__captureButton.clicked.connect(self.onClickedCapture)
        controlsLayout.addWidget(self.__captureButton, 3, 0, 1, 2)

        layout.addWidget(controls)

        self.__rolePlot = SpectrumPlotWidget()
        layout.addWidget(self.__rolePlot)
        return panel

    def __buildProcessingPage(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__processingTabs = QTabWidget()
        layout.addWidget(self.__processingTabs)
        return page

    # --- lifecycle ---

    def showEvent(self, event):
        super().showEvent(event)
        self.__startRun()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.__stopStream()
        self.__restoreRoi()  # leaving the view restores the authored ROI (never persisted; §12.4)

    def __startRun(self):
        # Reset run state.
        self.__restoreRoi()  # defensive: never start a run with a leftover widened ROI
        self.__cursor = 0
        self.__activeRole = REFERENCE
        self.__lockedExposure = None
        self.__roleSpectra = {}
        self.__representativeFrames = {}
        self.__latestImage = None

        # The user may have just authored the calibration (Save writes it on the server and does NOT
        # refresh the in-memory active profile). Re-fetch the current profile from the server by the
        # session's serial so the precondition below sees a freshly-calibrated setup (SPEC §11).
        ActiveSpectrometerProfileLogicModule().installFromSession()

        if not self.__hasCalibratedSetup():
            # D1 — in-window inline dialog; then back to Settings (instrument setup lives there).
            InWindowDialog.notify(self, "Calibration required",
                                  "No calibrated spectrometer setup is active. Set up and calibrate the "
                                  "spectrometer in Settings, then reopen the measurement bench.")
            self.__goToSettings()
            return

        self.__resolveCamera()
        self.__engine = SpectralWorkflowEngine(DevSpectralPlugin())
        self.__workflow = self.__engine.getWorkflow()
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.ACQUISITION)  # declares REFERENCE + SAMPLE

        self.__stepBar.setSteps(["Acquisition", "Processing"])
        self.__syncExposureToSensor()
        self.__rolePlot.plotSpectrum(None, title="Reference")
        self.__renderPhase()
        self.__startStream()

    def __hasCalibratedSetup(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        if profile is None:
            return False
        calibration = getattr(profile, "spectrometerCalibrationProfile", None)
        return calibration is not None and getattr(calibration, "interpolationCoefficientA", None) is not None

    def __resolveCamera(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        try:
            self.__sensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            self.__sensor = None
        self.__resolvedIndex = self.__resolver.resolveCaptureIndex(self.__sensor)
        if self.__sensor is None:
            self.__statusLabel.setText("The active setup has no camera device — re-run instrument setup.")
        elif self.__sensor.isVirtual:
            self.__statusLabel.setText("The active setup is a virtual device; the bench needs a real camera.")
        elif self.__resolvedIndex is None:
            self.__statusLabel.setText("Not connected — no %s:%s camera found. Plug the device directly into a "
                                       "USB port (not a hub) and reopen this view."
                                       % (self.__sensor.vendorId, self.__sensor.modelId))
        else:
            self.__statusLabel.setText("Connected: %s:%s → cv2 index %d."
                                       % (self.__sensor.vendorId, self.__sensor.modelId, self.__resolvedIndex))

    # --- rendering / navigation ---

    def __renderPhase(self):
        phaseType = self.__phases[self.__cursor]
        self.__stack.setCurrentIndex(self.__cursor)
        self.__stepBar.setCurrentIndex(self.__cursor)
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            self.__plotActiveRole()
        self.__refreshNav()

    def __refreshNav(self):
        terminal = self.__cursor >= len(self.__phases) - 1
        self.__backButton.setEnabled(True)  # Back always available (to prior phase or out to Settings)
        self.__nextButton.setText("Close" if terminal else "Next →")
        if terminal:
            self.__nextButton.setEnabled(True)
        else:
            self.__nextButton.setEnabled(self.__acquisitionComplete())
        self.__updateControls()

    def __acquisitionComplete(self):
        return REFERENCE in self.__roleSpectra and SAMPLE in self.__roleSpectra

    def onClickedBack(self):
        if self.__cursor > 0:
            self.__cursor -= 1
            self.__renderPhase()
            if self.__phases[self.__cursor] == SpectralWorkflowPhaseType.ACQUISITION:
                self.__startStream()
        else:
            self.__goToSettings()

    def onClickedNext(self):
        phaseType = self.__phases[self.__cursor]
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            if not self.__acquisitionComplete():
                return
            self.__stopStream()
            self.__runProcessing()
            self.__cursor = 1
            self.__renderPhase()
        else:
            self.__goToSettings()

    # --- capture ---

    def onClickedCapture(self):
        if self.__resolvedIndex is None or self.__videoThread is None or self.__autoExposing:
            return
        role = self.__activeRole
        if role == REFERENCE and self.__autoExposureCheckBox.isChecked():
            self.__runAutoExposure()

        frames = int(self.__framesComboBox.currentText())
        images = self.__grabFrames(frames)
        if not images:
            InWindowDialog.notify(self, "Capture failed", "No frames were delivered by the camera.")
            return

        # Widen the ROI to the bench analysis window before extraction — needs the real raster width to
        # clamp 700 nm to the sensor edge (§12). Idempotent; restored on leaving the view.
        self.__applyExtendedRoi(images[0].width())

        spectrum = None
        for image in images:
            signal = SpectralVideoThreadSignal()
            signal.image = image
            parameters = ImageSpectrumAcquisitionLogicModuleParameters()
            parameters.setVideoSignal(signal)
            parameters.spectrum = spectrum
            spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum

        step = self.__stepForRole(role)
        container = SpectraContainer()
        container.addToSpectra(spectrum, role)
        step.setContainer(container)

        self.__roleSpectra[role] = spectrum
        self.__representativeFrames[role] = images[len(images) // 2]

        if role == REFERENCE:
            self.__lockedExposure = self.__exposureSlider.value()
            # N2 — a fresh reference re-locks exposure; any earlier sample no longer matches.
            if SAMPLE in self.__roleSpectra:
                self.__roleSpectra.pop(SAMPLE, None)
                self.__representativeFrames.pop(SAMPLE, None)
                self.__stepForRole(SAMPLE).setContainer(None)

        self.__plotActiveRole()
        self.__refreshNav()

    def __grabFrames(self, count):
        self.__waitForFirstFrame()
        images = []
        for _ in range(count):
            self.__pumpFrames(120)  # let the stream advance a frame
            if self.__latestImage is not None:
                images.append(self.__latestImage.copy())
        return images

    def __stepForRole(self, role):
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in phase.getSteps().values():
            if step.getRole() == role:
                return step
        return None

    def __plotActiveRole(self):
        role = self.__activeRole
        title = "Reference" if role == REFERENCE else "Sample"
        spectrum = self.__roleSpectra.get(role)
        if spectrum is None:
            self.__rolePlot.plotSpectrum(None, title=title)
            return
        frames = spectrum.getCapturedValuesByNanometers()
        self.__rolePlot.plotSpectrum(None, title=title)  # clear + set title
        for values in frames:
            frameSpectrum = Spectrum()
            frameSpectrum.setValuesByNanometers(dict(values))
            self.__rolePlot.addTrace(frameSpectrum, color=self.__FRAME_COLOR, width=1)
        self.__rolePlot.addTrace(self.__meanSpectrum(spectrum), color=self.__MEAN_COLOR, width=2)

    def __meanSpectrum(self, spectrum):
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        return MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()

    # --- processing ---

    def __runProcessing(self):
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.PROCESSING)
        phase.getSteps().clear()  # idempotent if the user came Back then Next again
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.PROCESSING)

        self.__processingTabs.clear()
        self.__processingTabs.addTab(self.__rasterTab(REFERENCE), "Reference raster")
        self.__processingTabs.addTab(self.__rasterTab(SAMPLE), "Sample raster")

        for step in phase.getSteps().values():
            widget = self.__processingStepWidget(step)
            if widget is not None:
                self.__processingTabs.addTab(widget, step.getLabel())

    def __processingStepWidget(self, step):
        view = step.getView()
        if view is not None and getattr(view, "spectrum", None) is not None:
            plot = SpectrumPlotWidget()
            plot.plotSpectrum(view.spectrum, title=view.title)
            return plot
        # Spectra step: overlay reference + sample from the container.
        container = step.getContainer()
        if container is not None and REFERENCE in container.getSpectra() and SAMPLE in container.getSpectra():
            plot = SpectrumPlotWidget()
            plot.plotSpectrum(container.getSpectra()[REFERENCE], title=step.getLabel(),
                              color=self.__REF_COLOR)
            plot.addTrace(container.getSpectra()[SAMPLE], color=self.__SAMPLE_COLOR)
            return plot
        return None

    def __rasterTab(self, role):
        wrapper = QScrollArea()
        wrapper.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.M)
        content.setLayout(layout)

        image = self.__representativeFrames.get(role)
        if image is None:
            layout.addWidget(QLabel("No captured frame."))
            wrapper.setWidget(content)
            return wrapper

        roi = self.__roi()
        layout.addWidget(QLabel("Raw frame — region outside the ROI blacked out (preview only):"))
        layout.addWidget(self.__imageLabel(self.__maskOutsideRoi(image, roi)))
        layout.addWidget(QLabel("Cropped ROI raster:"))
        layout.addWidget(self.__imageLabel(self.__cropToRoi(image, roi)))
        layout.addStretch(1)
        wrapper.setWidget(content)
        return wrapper

    def __roi(self):
        calibration = ApplicationContextLogicModule().getApplicationSettings() \
            .getSpectrometerProfile().spectrometerCalibrationProfile
        x1 = int(calibration.regionOfInterestX1)
        y1 = int(calibration.regionOfInterestY1)
        x2 = int(calibration.regionOfInterestX2)
        y2 = int(calibration.regionOfInterestY2)
        return QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    # --- bench-extended ROI (SPEC_dev_measure_bench.md §12) -----------------------------------------
    # Temporarily widen the IN-MEMORY calibration's X1/X2 to span __NM_MIN..__NM_MAX (clamped to the
    # raster), so both extraction and the raster preview read the wider window with zero pipeline
    # plumbing. Never persisted; restored on leaving the view. Y and the A-D coefficients are untouched.

    def __calibration(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        return getattr(profile, "spectrometerCalibrationProfile", None) if profile is not None else None

    def __applyExtendedRoi(self, imageWidth):
        if self.__savedRoiX is not None:
            return  # already applied this session (idempotent)
        calibration = self.__calibration()
        if calibration is None:
            return
        x1, x2 = calibration.regionOfInterestX1, calibration.regionOfInterestX2
        if x1 is None or x2 is None:
            return
        newX1, newX2 = BenchRoiLogicModule().extendedXBounds(calibration, imageWidth,
                                                             self.__NM_MIN, self.__NM_MAX)
        if newX1 is None or newX2 is None:
            return
        self.__savedRoiX = (x1, x2)  # save originals only once we are actually widening
        calibration.regionOfInterestX1 = int(newX1)
        calibration.regionOfInterestX2 = int(newX2)
        self.__showEffectiveWindow(calibration, newX1, newX2)

    def __restoreRoi(self):
        if self.__savedRoiX is None:
            return
        calibration = self.__calibration()
        if calibration is not None:
            calibration.regionOfInterestX1, calibration.regionOfInterestX2 = self.__savedRoiX
        self.__savedRoiX = None

    def __showEffectiveWindow(self, calibration, x1, x2):
        # Quiet effective-range readout (§12.5) — the achieved window after the transparent clamp.
        try:
            polynomial = np.poly1d([calibration.interpolationCoefficientA, calibration.interpolationCoefficientB,
                                    calibration.interpolationCoefficientC, calibration.interpolationCoefficientD])
            self.__messageLabel.setText("Analysis window: %d–%d nm"
                                        % (round(float(polynomial(x1))), round(float(polynomial(x2)))))
        except (TypeError, AttributeError):
            pass

    def __maskOutsideRoi(self, image, roi):
        masked = image.copy()
        painter = QPainter(masked)
        black = QColor(0, 0, 0)
        width, height = masked.width(), masked.height()
        painter.fillRect(0, 0, width, roi.top(), black)                                  # above
        painter.fillRect(0, roi.bottom(), width, height - roi.bottom(), black)           # below
        painter.fillRect(0, roi.top(), roi.left(), roi.height(), black)                  # left
        painter.fillRect(roi.right(), roi.top(), width - roi.right(), roi.height(), black)  # right
        painter.end()
        return masked

    def __cropToRoi(self, image, roi):
        return image.copy(roi)

    def __imageLabel(self, image):
        label = QLabel()
        pixmap = QPixmap.fromImage(image)
        if pixmap.width() > 720:
            pixmap = pixmap.scaledToWidth(720, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pixmap)
        return label

    # --- controls / exposure (mirrors DevCaptureViewModule) ---

    def __onRoleChanged(self):
        self.__activeRole = self.__roleComboBox.currentData()
        if self.__activeRole == SAMPLE and self.__lockedExposure is not None:
            self.__exposureSlider.blockSignals(True)
            self.__exposureSlider.setValue(self.__lockedExposure)
            self.__exposureSlider.blockSignals(False)
            self.__updateExposureLabel()
            if self.__videoThread is not None:
                self.__videoThread.setLiveExposure(self.__lockedExposure)
        self.__captureButton.setText("Capture reference" if self.__activeRole == REFERENCE else "Capture sample")
        self.__plotActiveRole()
        self.__updateControls()

    def __onExposureChanged(self):
        self.__updateExposureLabel()
        if self.__videoThread is not None:
            self.__videoThread.setLiveExposure(self.__exposureSlider.value())

    def __updateExposureLabel(self):
        if self.__exposureLabel is not None:
            self.__exposureLabel.setText(str(self.__exposureSlider.value()))

    def __syncExposureToSensor(self):
        settings = SpectrometerSensorUtil().getSensorSettings(self.__sensor) if self.__sensor is not None else None
        value = settings.calibrationExposure if settings is not None and settings.calibrationExposure is not None \
            else self.__EXPOSURE_FALLBACK
        value = max(self.__EXPOSURE_MIN, min(self.__EXPOSURE_MAX, value))
        self.__exposureSlider.blockSignals(True)
        self.__exposureSlider.setValue(value)
        self.__exposureSlider.blockSignals(False)
        self.__updateExposureLabel()

    def __updateControls(self):
        onAcquisition = self.__phases[self.__cursor] == SpectralWorkflowPhaseType.ACQUISITION
        connected = self.__resolvedIndex is not None
        streaming = self.__videoThread is not None
        busy = self.__autoExposing
        # Sample role reuses the locked reference exposure: no auto-expose, no manual slider (correctness).
        sampleLocked = self.__activeRole == SAMPLE and self.__lockedExposure is not None
        autoOn = self.__autoExposureCheckBox is not None and self.__autoExposureCheckBox.isChecked()

        self.__captureButton.setEnabled(onAcquisition and connected and streaming and not busy)
        if self.__autoExposureCheckBox is not None:
            self.__autoExposureCheckBox.setEnabled(onAcquisition and not busy and not sampleLocked)
        if self.__exposureSlider is not None:
            self.__exposureSlider.setEnabled(onAcquisition and streaming and not busy
                                             and not autoOn and not sampleLocked)
        if self.__roleComboBox is not None:
            self.__roleComboBox.setEnabled(onAcquisition and not busy)
        if self.__framesComboBox is not None:
            self.__framesComboBox.setEnabled(onAcquisition and not busy)

    # --- streaming ---

    def __startStream(self):
        if self.__videoThread is not None or self.__resolvedIndex is None:
            self.__updateControls()
            return
        self.__latestImage = None
        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__resolvedIndex)
        exposure = self.__lockedExposure if (self.__activeRole == SAMPLE and self.__lockedExposure is not None) \
            else self.__exposureSlider.value()
        thread.setExposure(exposure)
        thread.setLiveExposure(exposure)
        thread.setFrameCount(0)  # continuous until stop()
        thread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        thread.finished.connect(self.__onThreadFinished)
        self.__videoThread = thread
        thread.start()
        self.__updateControls()
        # NOTE: auto-exposure runs on the Capture click (a user action), NOT here — running the
        # nested-event-loop bisection inside showEvent re-enters the view lifecycle and corrupts the
        # stream thread. The live preview opens at the seeded exposure; Capture auto-exposes then grabs.

    def __stopStream(self):
        if self.__videoThread is not None:
            self.__videoThread.stop()
        self.__updateControls()

    def __onThreadFinished(self):
        self.__videoThread = None
        self.__updateControls()

    def handleVideoThreadSignal(self, event, videoSignal):
        self.__latestImage = videoSignal.image
        if self.__videoViewModule is not None:
            self.__videoViewModule.handleVideoThreadSignal(videoSignal)
        event.set()

    # --- auto-exposure (bisection over the live stream — mirrors DevCaptureViewModule) ---

    def __runAutoExposure(self):
        if self.__videoThread is None or self.__autoExposing:
            return
        self.__autoExposing = True
        self.__updateControls()
        self.__waitForFirstFrame()
        probe = {"i": 0}

        def measure(exposure):
            probe["i"] += 1
            self.__emitAutoExposeProgress(probe["i"])
            self.__exposureSlider.setValue(exposure)
            self.__pumpFrames(350)
            return self.__brightness(self.__latestImage)

        try:
            result = AutoExposureLogicModule().findExposure(
                measure, self.__EXPOSURE_MIN, self.__EXPOSURE_MAX, iterations=self.__AUTO_EXPOSE_MAX_PROBES)
            self.__exposureSlider.setValue(result)
        finally:
            self.__autoExposing = False
            self.__clearStatus()
            self.__updateControls()

    def __waitForFirstFrame(self):
        for _ in range(12):
            if self.__latestImage is not None:
                return
            self.__pumpFrames(150)

    def __emitAutoExposeProgress(self, probeIndex):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = self.__AUTO_EXPOSE_MAX_PROBES
        signal.currentStepIndex = min(probeIndex, self.__AUTO_EXPOSE_MAX_PROBES)
        signal.text = "Auto-exposing… finding best exposure [%d/%d]" % (signal.currentStepIndex,
                                                                        self.__AUTO_EXPOSE_MAX_PROBES)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __clearStatus(self):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = True
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __pumpFrames(self, milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def __brightness(self, image):
        if image is None:
            return 0
        img = image.convertToFormat(image.format())
        width, height = img.width(), img.height()
        ptr = img.constBits()
        arr = np.frombuffer(ptr, np.uint8).reshape(height, img.bytesPerLine())[:, :width * 3].reshape(height, width, 3)
        return float(np.percentile(arr.max(axis=2), 99.9))

    # --- navigation ---

    def __goToSettings(self):
        self.__stopStream()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
