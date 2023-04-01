from PySide6.QtWidgets import QTabWidget
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QGridLayout

from chromos.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModule import SpectralJobWidgetViewModule
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModuleParameters import SpectralJobWidgetViewModuleParameters

class SpectralJobsWidgetViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.tabWidget = QTabWidget()
        layout.addWidget(self.tabWidget)

        self.sampleWidget=SpectralJobWidgetViewModule()
        sampleModuleParameters=SpectralJobWidgetViewModuleParameters()
        sampleModuleParameters.setSpectrumSampleType(SpectrumSampleType.SAMPLE)
        self.sampleWidget.setModuleParameters(sampleModuleParameters)
        self.tabWidget.addTab(self.sampleWidget,"Oil")

        self.referenceWidget=SpectralJobWidgetViewModule()
        referenceModuleParameters=SpectralJobWidgetViewModuleParameters()
        referenceModuleParameters.setSpectrumSampleType(SpectrumSampleType.REFERENCE)
        self.referenceWidget.setModuleParameters(referenceModuleParameters)
        self.tabWidget.addTab(self.referenceWidget, "Light")








