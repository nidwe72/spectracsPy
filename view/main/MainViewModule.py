from PyQt6.QtWidgets import QStackedWidget
from view.home.HomeViewModule import HomeViewModule
from view.settings.SettingsViewModule import SettingsViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileViewModule import SpectrometerProfileViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileListViewModule import \
    SpectrometerProfileListViewModule

from view.spectral.spectralJob.SpectralJobViewModule import SpectralJobViewModule


from view.spectral.spectralJob.importSpectrum.SpectralJobImportViewModule import SpectralJobImportViewModule

class MainViewModule(QStackedWidget):

    homeViewModule=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        homeViewModule = HomeViewModule()
        self.addWidget(homeViewModule)

        spectralJobViewModule = SpectralJobViewModule()
        self.addWidget(spectralJobViewModule)

        spectralJobImportViewModule=SpectralJobImportViewModule()
        self.addWidget(spectralJobImportViewModule)

        settingsViewModule = SettingsViewModule()
        self.addWidget(settingsViewModule)

        spectrometerProfileListViewModule=SpectrometerProfileListViewModule()
        spectrometerProfileListViewModule.initialize()
        self.addWidget(spectrometerProfileListViewModule)

        spectrometerProfileViewModule=SpectrometerProfileViewModule()
        spectrometerProfileViewModule.initialize()
        self.addWidget(spectrometerProfileViewModule)
