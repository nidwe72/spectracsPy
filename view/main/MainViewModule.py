from PySide6.QtWidgets import QStackedWidget

from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from view.home.HomeViewModule import HomeViewModule
from view.settings.SettingsViewModule import SettingsViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileViewModule import SpectrometerProfileViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileListViewModule import \
    SpectrometerProfileListViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileViewModule import \
    SpectrometerCalibrationProfileViewModule
from view.settings.spectral.spectrometer.acquisition.device.virtualCamera.VirtualSpectrometerViewModule import \
    VirtualSpectrometerViewModule

from view.spectral.spectralJob.SpectralJobViewModule import SpectralJobViewModule


from view.spectral.spectralJob.importSpectrum.SpectralJobImportViewModule import SpectralJobImportViewModule
from view.spectrometerConnection.SpectrometerConnectionViewModule import SpectrometerConnectionViewModule


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

        spectrometerProfile=SpectrometerProfile()
        SpectrometerProfileUtil().initializeSpectrometerProfile(spectrometerProfile)

        spectrometerProfileViewModule=SpectrometerProfileViewModule()
        spectrometerProfileViewModule.setModel(spectrometerProfile)
        spectrometerProfileViewModule.initialize()
        self.addWidget(spectrometerProfileViewModule)

        spectrometerCalibrationProfileViewModule=SpectrometerCalibrationProfileViewModule()
        spectrometerCalibrationProfileViewModule.setModel(spectrometerProfile.spectrometerCalibrationProfile)
        spectrometerCalibrationProfileViewModule.initialize()
        self.addWidget(spectrometerCalibrationProfileViewModule)

        virtualSpectrometerViewModule = VirtualSpectrometerViewModule()
        virtualSpectrometerViewModule.initialize()
        self.addWidget(virtualSpectrometerViewModule)

        spectrometerConnectionViewModule = SpectrometerConnectionViewModule()
        spectrometerConnectionViewModule.initialize()
        self.addWidget(spectrometerConnectionViewModule)

        self.setCurrentWidget(spectrometerConnectionViewModule)
