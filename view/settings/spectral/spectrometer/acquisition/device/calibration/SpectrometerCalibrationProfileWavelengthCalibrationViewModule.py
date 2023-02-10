import threading

from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QGroupBox, QLineEdit

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from logic.spectral.video.SpectrometerCalibrationProfileWavelengthCalibrationVideoThread import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoThread
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from spectracsTest2 import RascalLogicModule
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileSpectralLinesViewModule import \
    SpectrometerCalibrationProfileSpectralLinesViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule


class SpectrometerCalibrationProfileWavelengthCalibrationViewModule(PageWidget):

    model:SpectrometerCalibrationProfile=None

    detectPeaksButton: QPushButton=None
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
        buttonsPanel.setLayout(layout)

        self.detectPeaksButton = QPushButton('Detect peaks')
        self.detectPeaksButton.clicked.connect(self.onClickedDetectPeaksButton)
        layout.addWidget(self.detectPeaksButton, 0, 0, 1, 1)
        return buttonsPanel

    def onClickedDetectPeaksButton(self):
        self.onClickedDetectPeaksButtonNew()

    def onClickedDetectPeaksButtonNew(self):

        self.wavelengthCalibrationVideoThread = SpectrometerCalibrationProfileWavelengthCalibrationVideoThread()
        spectrometerProfile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        isVirtual = spectrometerProfile.spectrometer.spectrometerSensor.isVirtual
        self.wavelengthCalibrationVideoThread.setIsVirtual(isVirtual)

        self.wavelengthCalibrationVideoThread.videoThreadSignal.connect(self.handleWavelengthCalibrationVideoSignalNew)
        self.wavelengthCalibrationVideoThread.setFrameCount(50)

        self.wavelengthCalibrationVideoThread.start()


    def handleWavelengthCalibrationVideoSignalNew(self, event: threading.Event,
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

            self.coefficientAComponent.setText(str(videoSignal.model.interpolationCoefficientA))
            self.coefficientBComponent.setText(str(videoSignal.model.interpolationCoefficientB))
            self.coefficientCComponent.setText(str(videoSignal.model.interpolationCoefficientC))
            self.coefficientDComponent.setText(str(videoSignal.model.interpolationCoefficientD))

            self.spectrometerCalibrationProfileSpectralLinesViewModule.setModel(videoSignal.model)

        #self.testRascal(videoSignal)

        event.set()

    def testRascal(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        spectrumAcquisitionLogicModule = ImageSpectrumAcquisitionLogicModule()
        spectrum = spectrumAcquisitionLogicModule.execute(
            ImageSpectrumAcquisitionLogicModuleParameters().setVideoSignal(videoSignal)).spectrum

        rascalLogicModule = RascalLogicModule()
        rascalLogicModule.execute(spectrum)
        return


    def onClickedDetectPeaksButtonOld(self):

        self.wavelengthCalibrationVideoThread = SpectrometerCalibrationProfileWavelengthCalibrationVideoThread()
        spectrometerProfile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        isVirtual = spectrometerProfile.spectrometer.spectrometerSensor.isVirtual
        self.wavelengthCalibrationVideoThread.setIsVirtual(isVirtual)

        self.wavelengthCalibrationVideoThread.videoThreadSignal.connect(self.handleWavelengthCalibrationVideoSignalOld)
        self.wavelengthCalibrationVideoThread.setFrameCount(100)

        self.wavelengthCalibrationVideoThread.start()


    def handleWavelengthCalibrationVideoSignalOld(self, event: threading.Event,
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

            self.coefficientAComponent.setText(str(videoSignal.model.interpolationCoefficientA))
            self.coefficientBComponent.setText(str(videoSignal.model.interpolationCoefficientB))
            self.coefficientCComponent.setText(str(videoSignal.model.interpolationCoefficientC))
            self.coefficientDComponent.setText(str(videoSignal.model.interpolationCoefficientD))

            self.spectrometerCalibrationProfileSpectralLinesViewModule.setModel(videoSignal.model)

        event.set()


    def createPolynomialCoefficientsGroupBox(self):
        result = QGroupBox("Polynomial coefficients")

        layout = QGridLayout()
        result.setLayout(layout)

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

