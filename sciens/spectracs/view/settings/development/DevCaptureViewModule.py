from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QGroupBox, QComboBox, QPushButton, QLabel, QFileDialog, \
    QSizePolicy, QSlider, QCheckBox

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.application.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.acquisition.ExtendedRoiLogicModule import ExtendedRoiLogicModule
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.development.DevCaptureVideoViewModule import DevCaptureVideoViewModule


class DevCaptureViewModule(PageWidget):
    """SM1 — "Capture images" dev view (Settings > Development, master-only). Live camera stream +
    save-frame-as-PNG. Auto-resolves the selected sensor's cv2 index via SensorCaptureIndexResolver
    (the same VID/PID match SM2 reuses). Capture params stay hardcoded (see SPEC_dev_capture_view.md)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__resolver = SensorCaptureIndexResolver()
        self.__resolvedIndex = None
        self.__latestImage = None
        self.__roiFrameWidth = None  # frame width the ROI overlay was last computed for (§11.7)
        self.__videoThread = None

        self.videoViewModule = None
        self.sensorComboBox = None
        self.statusLabel = None
        self.startButton = None
        self.stopButton = None
        self.saveButton = None
        self.exposureSlider = None
        self.exposureLabel = None
        self.autoExposureCheckBox = None
        self.__autoExposing = False

    # V4L2 manual-exposure slider range for the DIY cameras (empirically the useful window is well inside
    # this). Fallback default when a camera has no seeded calibration exposure.
    __EXPOSURE_MIN = 1
    __EXPOSURE_MAX = 500
    __EXPOSURE_FALLBACK = 150

    def _getPageTitle(self):
        return 'Settings > Development > Capture images'

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        # noinspection PyUnresolvedReferences
        backButton.clicked.connect(self.onClickedBackButton)

        return result

    def onClickedBackButton(self):
        if self.__videoThread is not None:  # leaving the view stops the camera (async)
            self.__stopStream()
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.videoViewModule = DevCaptureVideoViewModule()
        self.videoViewModule.setObjectName('DevCaptureViewModule.videoViewModule')
        result[self.videoViewModule.objectName()] = self.videoViewModule

        controls = self.__createControlsPanel()
        result['controls'] = controls

        self.__populateSensors()
        self.__resolve()
        self.__applyRoiOverlay()
        return result

    def __createControlsPanel(self):
        panel = QWidget()
        panel.setObjectName('DevCaptureViewModule.controls')
        # Keep the controls compact so the live view takes the slack height.
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        panel.setLayout(layout)

        self.sensorComboBox = QComboBox()
        # noinspection PyUnresolvedReferences
        self.sensorComboBox.currentIndexChanged.connect(self.__onSensorChanged)
        layout.addWidget(self.createLabeledComponent('Camera', self.sensorComboBox), 0, 0, 1, 3)

        self.statusLabel = self.createMessageLabel('')
        layout.addWidget(self.statusLabel, 1, 0, 1, 3)

        # Manual exposure control — applies live while streaming, so the human can dial the sweet spot per
        # setup and per light source (CFL calibration vs LED measurement). Default = the camera's seeded
        # calibration exposure. (Auto-expose button is the next increment — SPEC_dev_capture_view.md §6.)
        self.exposureSlider = QSlider(Qt.Orientation.Horizontal)
        self.exposureSlider.setMinimum(self.__EXPOSURE_MIN)
        self.exposureSlider.setMaximum(self.__EXPOSURE_MAX)
        # noinspection PyUnresolvedReferences
        self.exposureSlider.valueChanged.connect(self.__onExposureChanged)
        self.exposureLabel = QLabel('')
        exposureRow = QWidget()
        exposureRowLayout = QGridLayout()
        exposureRowLayout.setContentsMargins(0, 0, 0, 0)
        exposureRowLayout.setSpacing(Metrics.S)
        exposureRow.setLayout(exposureRowLayout)
        self.autoExposureCheckBox = QCheckBox('auto-exposure')
        self.autoExposureCheckBox.setToolTip('Auto-exposure: finds the exposure that puts the brightest '
                                             'line just below clipping (our own algorithm, not the '
                                             'camera\'s). Runs when enabled / on stream start; the manual '
                                             'slider is locked while it is on.')
        self.autoExposureCheckBox.setChecked(True)  # on by default
        # noinspection PyUnresolvedReferences
        self.autoExposureCheckBox.toggled.connect(self.__onAutoExposureToggled)
        exposureRowLayout.addWidget(self.exposureSlider, 0, 0, 1, 1)
        exposureRowLayout.addWidget(self.exposureLabel, 0, 1, 1, 1)
        exposureRowLayout.addWidget(self.autoExposureCheckBox, 0, 2, 1, 1)
        exposureRowLayout.setColumnStretch(0, 70)
        exposureRowLayout.setColumnStretch(1, 10)
        exposureRowLayout.setColumnStretch(2, 20)
        layout.addWidget(self.createLabeledComponent('Exposure', exposureRow), 2, 0, 1, 3)

        self.startButton = QPushButton('Start stream')
        # noinspection PyUnresolvedReferences
        self.startButton.clicked.connect(self.onClickedStart)
        layout.addWidget(self.startButton, 3, 0, 1, 1)

        self.stopButton = QPushButton('Stop stream')
        # noinspection PyUnresolvedReferences
        self.stopButton.clicked.connect(self.onClickedStop)
        layout.addWidget(self.stopButton, 3, 1, 1, 1)

        self.saveButton = QPushButton('Save frame…')
        # noinspection PyUnresolvedReferences
        self.saveButton.clicked.connect(self.onClickedSave)
        layout.addWidget(self.saveButton, 3, 2, 1, 1)

        return panel

    def __populateSensors(self):
        self.sensorComboBox.blockSignals(True)
        self.sensorComboBox.clear()

        sensors = SpectrometerSensorUtil().getSpectrometerSensors()
        realSensors = [s for s in sensors.values() if not s.isVirtual]
        for sensor in realSensors:
            label = '%s (%s:%s)' % ((sensor.description or sensor.codeName or '').strip(),
                                    sensor.vendorId, sensor.modelId)
            self.sensorComboBox.addItem(label, sensor)

        # Default selection: (1) the active profile's sensor if real, else (2) the first real sensor
        # that actually resolves to a connected camera (auto-resolve drives the pick), else (3) the first.
        defaultIndex = self.__activeRealSensorIndex(realSensors)
        if defaultIndex is None:
            for i, sensor in enumerate(realSensors):
                if self.__resolver.resolveCaptureIndex(sensor) is not None:
                    defaultIndex = i
                    break
        if defaultIndex is None and realSensors:
            defaultIndex = 0
        if defaultIndex is not None:
            self.sensorComboBox.setCurrentIndex(defaultIndex)

        self.sensorComboBox.blockSignals(False)
        self.__syncExposureToSensor()

    def __syncExposureToSensor(self):
        # Set the slider to the selected camera's seeded calibration exposure (fallback when unseeded).
        if self.exposureSlider is None:
            return
        settings = SpectrometerSensorUtil().getSensorSettings(self.__currentSensor())
        value = settings.calibrationExposure if settings.calibrationExposure is not None else self.__EXPOSURE_FALLBACK
        value = max(self.__EXPOSURE_MIN, min(self.__EXPOSURE_MAX, value))
        self.exposureSlider.blockSignals(True)
        self.exposureSlider.setValue(value)
        self.exposureSlider.blockSignals(False)
        self.__updateExposureLabel()

    def __updateExposureLabel(self):
        if self.exposureLabel is not None:
            self.exposureLabel.setText(str(self.exposureSlider.value()))

    def __onExposureChanged(self):
        self.__updateExposureLabel()
        # Apply live if streaming — the worker picks it up before the next grab.
        if self.__videoThread is not None:
            self.__videoThread.setLiveExposure(self.exposureSlider.value())

    def __activeRealSensorIndex(self, realSensors):
        try:
            profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
            activeSensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            activeSensor = None
        if activeSensor is None or activeSensor.isVirtual:
            return None
        for i, sensor in enumerate(realSensors):
            if sensor.vendorId == activeSensor.vendorId and sensor.modelId == activeSensor.modelId:
                return i
        return None

    # ROI overlay fields carried on the assigned profile's calibration.
    __ROI_FIELDS = ('regionOfInterestX1', 'regionOfInterestY1', 'regionOfInterestX2', 'regionOfInterestY2')

    def __applyRoiOverlay(self):
        # Overlay the calibrated ROI box iff the current SpectrometerSetup has a profile assigned — reached
        # here via the active SpectrometerProfile → spectrometerCalibrationProfile chain — that carries all
        # four ROI corners, AND the selected camera is that profile's sensor (else the box is meaningless).
        # SPEC_dev_capture_view.md §11.
        if self.videoViewModule is None:
            return
        roi = self.__assignedRoi()
        if roi is None:
            self.videoViewModule.clearRoi()
        else:
            self.videoViewModule.setRoi(*roi)

    def __assignedRoi(self):
        try:
            profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        except AttributeError:
            return None
        if profile is None:
            return None

        # Sensor-match guard: only show the ROI when the selected camera is the profile's device.
        try:
            profileSensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            profileSensor = None
        current = self.__currentSensor()
        if profileSensor is None or current is None:
            return None
        if profileSensor.vendorId != current.vendorId or profileSensor.modelId != current.modelId:
            return None

        calibration = getattr(profile, 'spectrometerCalibrationProfile', None)
        if calibration is None:
            return None
        values = [getattr(calibration, field, None) for field in self.__ROI_FIELDS]
        if any(value is None for value in values):  # half-populated calibration → treat as no ROI
            return None
        # Draw the EXTENDED 400–700 window (the same window the measurement bench analyses) once the frame
        # width is known; fall back to the authored ROI until the first frame arrives. §11.7 / shared module.
        image = self.__latestImage
        if image is not None:
            extended = ExtendedRoiLogicModule().extendedRoi(calibration, image.width())
            if extended is not None:
                return extended
        return tuple(values)

    def __currentSensor(self):
        if self.sensorComboBox is None or self.sensorComboBox.currentIndex() < 0:
            return None
        return self.sensorComboBox.currentData()

    def __onSensorChanged(self):
        # Switching camera while streaming: stop the current stream first (async), then re-resolve.
        if self.__videoThread is not None:
            self.__stopStream()
        self.__resolve()
        self.__syncExposureToSensor()
        self.__applyRoiOverlay()  # ROI belongs to a specific device — re-evaluate on camera switch

    def __resolve(self):
        sensor = self.__currentSensor()
        self.__resolvedIndex = self.__resolver.resolveCaptureIndex(sensor)

        if sensor is None:
            self.statusLabel.setText('No camera selected.')
        elif self.__resolvedIndex is None:
            self.statusLabel.setText('Not connected — no %s:%s camera found. Plug the device directly '
                                     'into a USB port (not a hub) and reopen this view.'
                                     % (sensor.vendorId, sensor.modelId))
        else:
            self.statusLabel.setText('Connected: %s:%s → cv2 index %d.'
                                     % (sensor.vendorId, sensor.modelId, self.__resolvedIndex))
        self.__updateButtons()

    def __updateButtons(self):
        streaming = self.__videoThread is not None
        connected = self.__resolvedIndex is not None
        busy = self.__autoExposing
        autoOn = self.autoExposureCheckBox is not None and self.autoExposureCheckBox.isChecked()
        # Not-connected → Start/Save read-only (SPEC_dev_capture_view.md §3.2), not just a toast.
        self.startButton.setEnabled(connected and not streaming and not busy)
        self.stopButton.setEnabled(streaming and not busy)
        self.saveButton.setEnabled(connected and self.__latestImage is not None and not busy)
        if self.autoExposureCheckBox is not None:
            self.autoExposureCheckBox.setEnabled(not busy)
        # Manual slider is locked while auto-exposure is on (Edwin) or a run is in progress.
        if self.exposureSlider is not None:
            self.exposureSlider.setEnabled(streaming and not autoOn and not busy)

    def onClickedStart(self):
        if self.__resolvedIndex is None or self.__videoThread is not None:
            return
        self.__latestImage = None

        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__resolvedIndex)
        # Open at the slider's current exposure (seeded from the camera's calibration value) and let the
        # slider adjust it live thereafter.
        exposure = self.exposureSlider.value()
        thread.setExposure(exposure)
        thread.setLiveExposure(exposure)
        thread.setFrameCount(0)  # 0 = continuous stream until stop()
        # noinspection PyUnresolvedReferences
        thread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        # noinspection PyUnresolvedReferences
        thread.autoExposureProgress.connect(self.__onAutoExposeProgress)
        # noinspection PyUnresolvedReferences
        thread.autoExposureFinished.connect(self.__onAutoExposeFinished)
        # noinspection PyUnresolvedReferences
        thread.finished.connect(self.__onThreadFinished)
        self.__videoThread = thread
        thread.start()
        self.__updateButtons()

        # Auto-exposure on by default → run it once the stream is delivering frames.
        if self.autoExposureCheckBox.isChecked():
            self.__runAutoExposure()

    def onClickedStop(self):
        self.__stopStream()

    def __stopStream(self):
        # Async stop: set the run flag off and let the worker finish its current (event-gated) frame.
        # Never wait() on the GUI thread here — the worker may be blocked in event.wait() for a queued
        # frame the GUI still has to deliver, so a join would deadlock. finished → __onThreadFinished.
        if self.__videoThread is not None:
            self.__videoThread.stop()
        self.__updateButtons()

    def __onThreadFinished(self):
        self.__videoThread = None
        self.__updateButtons()

    def handleVideoThreadSignal(self, event, videoSignal):
        self.__latestImage = videoSignal.image
        self.videoViewModule.handleVideoThreadSignal(videoSignal)
        self.__updateButtons()  # enable Save once the first real frame lands
        # Redraw the ROI overlay once the frame width is known (extended 400–700 window needs it — §11.7),
        # and again only if the capture resolution changes.
        width = videoSignal.image.width() if videoSignal.image is not None else None
        if width is not None and width != self.__roiFrameWidth:
            self.__roiFrameWidth = width
            self.__applyRoiOverlay()
        event.set()

    def __onAutoExposureToggled(self):
        self.__updateButtons()  # lock/unlock the manual slider
        # Turning it on while streaming → run the search now.
        if self.autoExposureCheckBox.isChecked() and self.__videoThread is not None and not self.__autoExposing:
            self.__runAutoExposure()

    __AUTO_EXPOSE_MAX_PROBES = 8

    def __runAutoExposure(self):
        # Hand the sweep to the capture thread, which runs it SYNCHRONOUSLY on the backend (set exposure -> drain
        # -> measure qGray peak) — no async live-stream reads, so no stale-frame lag (SPEC_capture_quality.md
        # §14.6). Progress + result come back on the thread's autoExposure* signals; the display simply freezes on
        # the "Auto-exposing…" status until it finishes.
        if self.__videoThread is None or self.__autoExposing:
            return
        self.__autoExposing = True
        self.__updateButtons()
        self.__videoThread.requestAutoExpose(
            self.__EXPOSURE_MIN, self.__EXPOSURE_MAX, iterations=self.__AUTO_EXPOSE_MAX_PROBES)

    def __onAutoExposeProgress(self, probeIndex, totalProbes):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = totalProbes
        signal.currentStepIndex = min(probeIndex, totalProbes)
        signal.text = 'Auto-exposing… finding best exposure [%d/%d]' % (signal.currentStepIndex, totalProbes)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __onAutoExposeFinished(self, exposure):
        self.exposureSlider.setValue(exposure)  # applies live + updates label (thread already applied it)
        self.__autoExposing = False
        self.__clearStatus()
        self.__resolve()  # restore the connection status text + button states

    def __clearStatus(self):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = True
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def onClickedSave(self):
        image = self.__latestImage
        if image is None:
            return
        snapshot = image.copy()  # detach from the live stream before the dialog (RD-2)

        path, _ = QFileDialog.getSaveFileName(self, 'Save frame', '', 'PNG image (*.png)')
        if not path:
            return
        if not path.lower().endswith('.png'):
            path = path + '.png'
        snapshot.save(path, 'PNG')

    def showEvent(self, event):
        super().showEvent(event)
        # Re-resolve on open in case the device was (un)plugged since the view was built.
        if self.sensorComboBox is not None:
            self.__resolve()
            self.__applyRoiOverlay()  # a profile may have been assigned/calibrated since last open

    def hideEvent(self, event):
        super().hideEvent(event)
        # Leaving the view stops the camera (async).
        if self.__videoThread is not None:
            self.__stopStream()
