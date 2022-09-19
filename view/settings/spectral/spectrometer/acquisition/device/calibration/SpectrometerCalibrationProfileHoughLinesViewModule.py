import threading
from typing import List

from PyQt6.QtCore import QLine
from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton, QGroupBox, QLineEdit

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
from logic.spectral.video.SpectrometerCalibrationProfileHoughLinesVideoThread import \
    SpectrometerCalibrationProfileHoughLinesVideoThread
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from model.application.navigation.NavigationSignal import NavigationSignal
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesVideoViewModule import \
    SpectrometerCalibrationProfileHoughLinesVideoViewModule

class SpectrometerCalibrationProfileHoughLinesViewModule(PageWidget):

    videoThread: SpectrometerCalibrationProfileHoughLinesVideoThread = None
    videoViewModule: SpectrometerCalibrationProfileHoughLinesVideoViewModule = None
    captureVideoButton: QPushButton = None
    allHoughLines: List[List[QLine]] = None

    x1Component: QLineEdit = None
    y1Component: QLineEdit = None
    x2Component: QLineEdit = None
    y2Component: QLineEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.videoViewModule = SpectrometerCalibrationProfileHoughLinesVideoViewModule()
        self.videoViewModule.setObjectName(
            'SpectrometerCalibrationProfileHoughLinesViewModule.videoViewModule')
        result[self.videoViewModule.objectName()] = self.videoViewModule

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
        buttonsPanel.setLayout(layout)

        self.captureVideoButton = QPushButton('Detect horizontal lines')
        self.captureVideoButton.clicked.connect(self.onClickedCaptureVideoButton)
        layout.addWidget(self.captureVideoButton, 0, 0, 1, 1)

        return buttonsPanel

    def onClickedCaptureVideoButton(self):

        self.allHoughLines = []
        self.videoThread = SpectrometerCalibrationProfileHoughLinesVideoThread()
        self.videoThread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        self.videoThread.setFrameCount(50)
        self.videoThread.start()

    def createRegionOfInterestNavigationGroupBox(self):
        result = QGroupBox("Region of interest")

        layout = QGridLayout()
        result.setLayout(layout);

        self.x1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x1', self.x1Component), 0, 0, 1, 1)

        self.x2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x2', self.x2Component), 0, 1, 1, 1)

        self.y1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y1', self.y1Component), 1, 0, 1, 1)

        self.y2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y2', self.y2Component), 1, 1, 1, 1)

        return result

    def handleVideoThreadSignal(self, event: threading.Event,
                                videoSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):
        if isinstance(videoSignal, SpectrometerCalibrationProfileHoughLinesVideoSignal):

            houghLineLogicModule = HoughLineLogicModule()
            houghLines = houghLineLogicModule.getHoughLines(videoSignal.image)
            self.allHoughLines.append(houghLines)

            videoSignal.calibrationStepUpperHoughLine = houghLines[0]
            videoSignal.calibrationStepLowerHoughLine = houghLines[1]

            centerY = videoSignal.calibrationStepUpperHoughLine.p1().y() + (
                    videoSignal.calibrationStepLowerHoughLine.p1().y() - videoSignal.calibrationStepUpperHoughLine.p1().y()) / 2.0

            videoSignal.calibrationStepCenterHoughLine = QLine(videoSignal.calibrationStepUpperHoughLine.p1().x(),
                                                               centerY,
                                                               videoSignal.calibrationStepUpperHoughLine.p2().x(),
                                                               centerY)

            boundingHoughLines = self.__getBoundingHoughLines()

            videoSignal.upperHoughLine = boundingHoughLines[0]
            videoSignal.lowerHoughLine = boundingHoughLines[1]

            centerY = videoSignal.upperHoughLine.p1().y() + (
                    videoSignal.lowerHoughLine.p1().y() - videoSignal.upperHoughLine.p1().y()) / 2.0

            videoSignal.centerHoughLine = QLine(videoSignal.upperHoughLine.p1().x(), centerY,
                                                videoSignal.upperHoughLine.p2().x(), centerY)

            someNavigationSignal = NavigationSignal(None)
            someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

            applicationStatusSignal = ApplicationStatusSignal()
            applicationStatusSignal.text = 'retrieving Hough lines'
            applicationStatusSignal.isStatusReset = False
            applicationStatusSignal.stepsCount = videoSignal.framesCount
            applicationStatusSignal.currentStepIndex = videoSignal.currentFrameIndex

            if applicationStatusSignal.stepsCount == applicationStatusSignal.currentStepIndex:
                self.y2Component.setText(str(videoSignal.upperHoughLine.p1().y()))
                self.y1Component.setText(str(videoSignal.lowerHoughLine.p1().y()))
                applicationStatusSignal.isStatusReset = True

            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
                applicationStatusSignal)

            self.videoViewModule.handleVideoThreadSignal(videoSignal)

            event.set()

    def __getBoundingHoughLines(self) -> List[QLine]:

        result = []

        resultUpperHoughLine: QLine = None
        resultLowerHoughLine: QLine = None

        for someHoughLines in self.allHoughLines:
            upperHoughLine = someHoughLines[0]
            lowerHoughLine = someHoughLines[1]

            if resultUpperHoughLine is None:
                resultUpperHoughLine = upperHoughLine
            elif upperHoughLine.p1().y() > resultUpperHoughLine.p1().y():
                resultUpperHoughLine = upperHoughLine

            if resultLowerHoughLine is None:
                resultLowerHoughLine = lowerHoughLine
            elif lowerHoughLine.p1().y() < resultLowerHoughLine.p1().y():
                resultLowerHoughLine = lowerHoughLine

        result.append(resultUpperHoughLine)
        result.append(resultLowerHoughLine)

        return result

    def createMainWidget(self):

        result = QWidget()
        resultLayout = QGridLayout()
        result.setLayout(resultLayout)
        resultLayout.addWidget(self.createRegionOfInterestNavigationGroupBox(), 0, 0, 1, 1)

        return result

    def initialize(self):
        super().initialize()

5
