from PySide6.QtWidgets import QWidget, QGridLayout, QComboBox, QPushButton, QLabel, QFileDialog, QSizePolicy

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.appliction.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.appliction.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
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
        self.__videoThread = None

        self.videoViewModule = None
        self.sensorComboBox = None
        self.statusLabel = None
        self.startButton = None
        self.stopButton = None
        self.saveButton = None

    def _getPageTitle(self):
        return 'Capture images'

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.videoViewModule = DevCaptureVideoViewModule()
        self.videoViewModule.setObjectName('DevCaptureViewModule.videoViewModule')
        result[self.videoViewModule.objectName()] = self.videoViewModule

        controls = self.__createControlsPanel()
        result['controls'] = controls

        self.__populateSensors()
        self.__resolve()
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

        self.startButton = QPushButton('Start stream')
        # noinspection PyUnresolvedReferences
        self.startButton.clicked.connect(self.onClickedStart)
        layout.addWidget(self.startButton, 2, 0, 1, 1)

        self.stopButton = QPushButton('Stop stream')
        # noinspection PyUnresolvedReferences
        self.stopButton.clicked.connect(self.onClickedStop)
        layout.addWidget(self.stopButton, 2, 1, 1, 1)

        self.saveButton = QPushButton('Save frame…')
        # noinspection PyUnresolvedReferences
        self.saveButton.clicked.connect(self.onClickedSave)
        layout.addWidget(self.saveButton, 2, 2, 1, 1)

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

    def __currentSensor(self):
        if self.sensorComboBox is None or self.sensorComboBox.currentIndex() < 0:
            return None
        return self.sensorComboBox.currentData()

    def __onSensorChanged(self):
        # Switching camera while streaming: stop the current stream first (async), then re-resolve.
        if self.__videoThread is not None:
            self.__stopStream()
        self.__resolve()

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
        # Not-connected → Start/Save read-only (SPEC_dev_capture_view.md §3.2), not just a toast.
        self.startButton.setEnabled(connected and not streaming)
        self.stopButton.setEnabled(streaming)
        self.saveButton.setEnabled(connected and self.__latestImage is not None)

    def onClickedStart(self):
        if self.__resolvedIndex is None or self.__videoThread is not None:
            return
        self.__latestImage = None

        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__resolvedIndex)
        # This view captures the CFL-calibration scenario, so use the camera's seeded calibration
        # exposure (e.g. ELP=78; None falls back to the backend default). Live exposure controls +
        # the LED-measurement regime are a later increment (SPEC_dev_capture_view.md §6 / §9.3).
        settings = SpectrometerSensorUtil().getSensorSettings(self.__currentSensor())
        thread.setExposure(settings.calibrationExposure)
        thread.setFrameCount(0)  # 0 = continuous stream until stop()
        # noinspection PyUnresolvedReferences
        thread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        # noinspection PyUnresolvedReferences
        thread.finished.connect(self.__onThreadFinished)
        self.__videoThread = thread
        thread.start()
        self.__updateButtons()

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
        event.set()

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

    def hideEvent(self, event):
        super().hideEvent(event)
        # Leaving the view stops the camera (async).
        if self.__videoThread is not None:
            self.__stopStream()
