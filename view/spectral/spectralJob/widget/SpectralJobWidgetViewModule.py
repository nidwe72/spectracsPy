from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout

import threading

from logic.spectral.video.SpectralImageLogicModule import SpectralImageLogicModule
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobGraphViewModuleParameters import SpectralJobGraphViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobGraphViewModulePolicyParameter import \
    SpectralJobGraphViewModulePolicyParameter
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModuleParameters import \
    SpectralJobWidgetViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobGraphViewModule import SpectralJobGraphViewModule
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.video.VideoSignal import VideoSignal
from view.application.widgets.video.VideoViewModule import VideoViewModule
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

class SpectralJobWidgetViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.tabWidget = QTabWidget()
        layout.addWidget(self.tabWidget)

        self.plotSpectraMeanViewModule = SpectralJobGraphViewModule()
        self.plotSpectraMeanViewModule.chart.setTitle("Intensities: mean")
        self.tabWidget.addTab(self.plotSpectraMeanViewModule, "Intensities (averaged)")

        self.spectralJobGraphViewModule = SpectralJobGraphViewModule()
        self.spectralJobGraphViewModule.chart.setTitle("Intensities: burst mode of 50 measurements holding the raw intensities")
        self.tabWidget.addTab(self.spectralJobGraphViewModule, "Intensities (raw)")

        self.videoViewModule = VideoViewModule()

        self.tabWidget.addTab(self.videoViewModule, "Spectrum image (last captured)")

        self.videoThread = SpectrumVideoThread()
        self.videoThread.spectralVideoThreadSignal.connect(self.handleSpectralVideoThreadSignal)


    def startVideoThread(self):
        spectralJobGraphViewModuleParameters=SpectralJobGraphViewModuleParameters()
        spectralJobGraphViewModuleParameters.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        spectralJobGraphViewModuleParameters.setPolicy(SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA)
        self.spectralJobGraphViewModule.setModuleParameters(spectralJobGraphViewModuleParameters)

        plotSpectraMeanViewModuleParameters=SpectralJobGraphViewModuleParameters()
        plotSpectraMeanViewModuleParameters.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        plotSpectraMeanViewModuleParameters.setPolicy(SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA_MEAN)
        self.plotSpectraMeanViewModule.setModuleParameters(plotSpectraMeanViewModuleParameters)

        self.videoThread.setFrameCount(50)
        self.videoThread.setSpectrumSampleType(self.getModuleParameters().getSpectrumSampleType())
        self.videoThread.start()

    def handleSpectralVideoThreadSignal(self, event:threading.Event,spectralVideoThreadSignal: SpectralVideoThreadSignal):
        if isinstance(spectralVideoThreadSignal, SpectralVideoThreadSignal):

            self.spectralJobGraphViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)
            self.plotSpectraMeanViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)

            videoSignal = VideoSignal()
            videoSignal.image = spectralVideoThreadSignal.image

            if spectralVideoThreadSignal.currentFrameIndex==spectralVideoThreadSignal.framesCount:
                spectralImageLogicModule=SpectralImageLogicModule()
                colorizedImage=spectralImageLogicModule.colorizeQImage(spectralVideoThreadSignal.image,132)
                videoSignal.image = colorizedImage

            self.videoViewModule.handleVideoSignal(videoSignal)

            event.set()

    def setModuleParameters(self,moduleParameters:SpectralJobWidgetViewModuleParameters):
        self.__moduleParameters=moduleParameters

    def getModuleParameters(self)->SpectralJobWidgetViewModuleParameters:
        return self.__moduleParameters


