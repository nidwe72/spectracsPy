from PySide6.QtWidgets import QTabWidget
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QGridLayout
from PySide6.QtGui import QImage

import threading

from spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.spectral.spectralJob.widget.SpectralJobGraphViewModuleParameters import SpectralJobGraphViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobGraphViewModulePolicyParameter import \
    SpectralJobGraphViewModulePolicyParameter
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModuleParameters import \
    SpectralJobWidgetViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobGraphViewModule import SpectralJobGraphViewModule
from sciens.spectracs.logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from sciens.spectracs.model.application.video.VideoSignal import VideoSignal
from view.application.widgets.video.VideoViewModule import VideoViewModule
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal


class SpectralJobWidgetViewModule(PageWidget):
    videoThread: SpectrumVideoThread = None
    plotSpectraMeanViewModule: SpectralJobGraphViewModule = None
    videoViewModule: VideoViewModule = None
    spectralJobGraphViewModule: SpectralJobGraphViewModule = None
    applicationSignalsProvider = None
    __moduleParameters: SpectralJobWidgetViewModuleParameters = None
    tabWidget: QTabWidget = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.tabWidget = QTabWidget()

        self.plotSpectraMeanViewModule = SpectralJobGraphViewModule()
        self.plotSpectraMeanViewModule.chart.setTitle("Intensities: mean")
        self.tabWidget.addTab(self.plotSpectraMeanViewModule, "Intensities (averaged)")

        self.spectralJobGraphViewModule = SpectralJobGraphViewModule()
        self.spectralJobGraphViewModule.chart.setTitle(
            "Intensities: burst mode of 50 measurements holding the raw intensities")
        self.tabWidget.addTab(self.spectralJobGraphViewModule, "Intensities (raw)")

        self.videoViewModule = VideoViewModule()
        self.tabWidget.addTab(self.videoViewModule, "Spectrum image (last captured)")

        result[self.tabWidget.objectName()] = self.tabWidget

        return result

    def startVideoThread(self):

        self.videoThread = SpectrumVideoThread()
        self.videoThread.videoThreadSignal.connect(self.handleSpectralVideoThreadSignal)

        spectralJobGraphViewModuleParameters = SpectralJobGraphViewModuleParameters()
        spectralJobGraphViewModuleParameters.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        spectralJobGraphViewModuleParameters.setPolicy(SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA)
        self.spectralJobGraphViewModule.setModuleParameters(spectralJobGraphViewModuleParameters)

        plotSpectraMeanViewModuleParameters = SpectralJobGraphViewModuleParameters()
        plotSpectraMeanViewModuleParameters.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        plotSpectraMeanViewModuleParameters.setPolicy(SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA_MEAN)
        self.plotSpectraMeanViewModule.setModuleParameters(plotSpectraMeanViewModuleParameters)

        self.spectralJobGraphViewModule.clearGraph()

        # todo:edwin
        self.videoThread.setFrameCount(50)
        self.videoThread.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        self.videoThread.start()

    def handleSpectralVideoThreadSignal(self, event: threading.Event,
                                        spectralVideoThreadSignal: SpectralVideoThreadSignal):
        if isinstance(spectralVideoThreadSignal, SpectralVideoThreadSignal):

            if spectralVideoThreadSignal.currentFrameIndex > 3:
                self.spectralJobGraphViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)
                self.plotSpectraMeanViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)

                videoSignal = VideoSignal()
                videoSignal.image = spectralVideoThreadSignal.image

                colorizedImage = spectralVideoThreadSignal.image.convertToFormat(QImage.Format.Format_Grayscale8)
                videoSignal.image = colorizedImage

                self.videoViewModule.handleVideoThreadSignal(videoSignal)

            applicationStatusSignal = ApplicationStatusSignal()
            applicationStatusSignal.isStatusReset = False
            applicationStatusSignal.stepsCount = spectralVideoThreadSignal.framesCount
            applicationStatusSignal.currentStepIndex = spectralVideoThreadSignal.currentFrameIndex
            applicationStatusSignal.text = f"capturing frames  > step [{applicationStatusSignal.currentStepIndex + 1}/{applicationStatusSignal.stepsCount}]"

            if applicationStatusSignal.stepsCount - 1 == applicationStatusSignal.currentStepIndex:
                applicationStatusSignal.isStatusReset = True

            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
                applicationStatusSignal)

            event.set()

    def setModuleParameters(self, moduleParameters: SpectralJobWidgetViewModuleParameters):
        self.__moduleParameters = moduleParameters

    def getModuleParameters(self) -> SpectralJobWidgetViewModuleParameters:
        return self.__moduleParameters
