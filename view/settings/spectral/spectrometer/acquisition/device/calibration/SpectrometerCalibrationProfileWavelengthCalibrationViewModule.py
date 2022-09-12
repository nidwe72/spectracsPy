import threading

from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton, QGroupBox, QLineEdit

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.spectral.video.SpectrometerCalibrationProfileWavelengthCalibrationVideoThread import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoThread
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule


class SpectrometerCalibrationProfileWavelengthCalibrationViewModule(PageWidget):

    detectPeaksButton: QPushButton=None
    wavelengthCalibrationVideoThread: SpectrometerCalibrationProfileWavelengthCalibrationVideoThread = None
    wavelengthCalibrationVideoViewModule: SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule = None

    coefficientAComponent: QLineEdit = None
    coefficientBComponent: QLineEdit = None
    coefficientCComponent: QLineEdit = None
    coefficientDComponent: QLineEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.wavelengthCalibrationVideoViewModule = SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule()
        result['wavelengthCalibrationVideoViewModule'] = self.wavelengthCalibrationVideoViewModule

        mainWidget = self.createMainWidget();
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

        self.detectPeaksButton = QPushButton('Detect peaks')
        self.detectPeaksButton.clicked.connect(self.onClickedDetectPeaksButton)
        layout.addWidget(self.detectPeaksButton, 0, 0, 1, 1)
        return buttonsPanel

    def onClickedDetectPeaksButton(self):

        self.wavelengthCalibrationVideoThread = SpectrometerCalibrationProfileWavelengthCalibrationVideoThread()
        self.wavelengthCalibrationVideoThread.videoThreadSignal.connect(self.handleWavelengthCalibrationVideoSignal)
        self.wavelengthCalibrationVideoThread.setFrameCount(100)

        self.wavelengthCalibrationVideoThread.start()

    def createPolynomialCoefficientsGroupBox(self):
        result = QGroupBox("Polynomial coefficients")

        layout = QGridLayout()
        result.setLayout(layout);

        self.coefficientAComponent = QLineEdit()
        layout.addWidget(self.createLabeledComponent('A', self.coefficientAComponent), 0, 0, 1, 1)

        self.coefficientBComponent = QLineEdit()
        layout.addWidget(self.createLabeledComponent('B', self.coefficientBComponent), 0, 1, 1, 1)

        self.coefficientCComponent = QLineEdit()
        layout.addWidget(self.createLabeledComponent('C', self.coefficientCComponent), 1, 0, 1, 1)

        self.coefficientDComponent = QLineEdit()
        layout.addWidget(self.createLabeledComponent('D', self.coefficientDComponent), 1, 1, 1, 1)

        return result

    def createSpectralLinesNavigationGroupBox(self):
        result = QGroupBox("Spectral lines")
        return result

    def handleWavelengthCalibrationVideoSignal(self, event: threading.Event,
                                               videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        applicationStatusSignal = ApplicationStatusSignal()
        applicationStatusSignal.text = 'detecting peaks'
        applicationStatusSignal.isStatusReset = False
        applicationStatusSignal.stepsCount = videoSignal.framesCount
        applicationStatusSignal.currentStepIndex = videoSignal.currentFrameIndex

        if applicationStatusSignal.stepsCount == applicationStatusSignal.currentStepIndex:
            applicationStatusSignal.isStatusReset = True

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
            applicationStatusSignal)

        self.wavelengthCalibrationVideoViewModule.handleVideoThreadSignal(videoSignal)

        if applicationStatusSignal.stepsCount == applicationStatusSignal.currentStepIndex:
            interpolationPolynomialCoefficients = videoSignal.interpolationPolynomial.coefficients

            self.coefficientAComponent.setText(str(interpolationPolynomialCoefficients[0].item()))
            self.coefficientBComponent.setText(str(interpolationPolynomialCoefficients[1].item()))
            self.coefficientCComponent.setText(str(interpolationPolynomialCoefficients[2].item()))
            self.coefficientDComponent.setText(str(interpolationPolynomialCoefficients[3].item()))

            # self.y2Component.setText(str(videoSignal.upperHoughLine.p1().y()))
            # self.y1Component.setText(str(videoSignal.lowerHoughLine.p1().y()))
            # applicationStatusSignal.isStatusReset = True

        event.set()

    def createMainWidget(self):
        result = QWidget()
        resultLayout = QGridLayout()
        result.setLayout(resultLayout)
        resultLayout.addWidget(self.createPolynomialCoefficientsGroupBox(), 0, 0, 1, 1)
        resultLayout.addWidget(self.createSpectralLinesNavigationGroupBox(), 0, 1, 1, 1)

        return result

    def initialize(self):
        super().initialize()


