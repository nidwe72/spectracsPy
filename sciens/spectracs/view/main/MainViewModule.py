from PySide6.QtWidgets import QStackedWidget

from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.view.home.HomeViewModule import HomeViewModule
from sciens.spectracs.view.settings.SettingsViewModule import SettingsViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileViewModule import SpectrometerProfileViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileListViewModule import \
    SpectrometerProfileListViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileViewModule import \
    SpectrometerCalibrationProfileViewModule
from sciens.spectracs.view.settings.spectral.spectrometer.acquisition.device.virtualCamera.VirtualSpectrometerViewModule import \
    VirtualSpectrometerViewModule

from sciens.spectracs.view.spectral.spectralJob.SpectralJobViewModule import SpectralJobViewModule


from sciens.spectracs.view.spectral.spectralJob.importSpectrum.SpectralJobImportViewModule import SpectralJobImportViewModule
from sciens.spectracs.view.settings.user.UserListViewModule import UserListViewModule
from sciens.spectracs.view.settings.user.UserViewModule import UserViewModule
from sciens.spectracs.view.playground.PlaygroundViewModule import PlaygroundViewModule
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule
from sciens.spectracs.view.spectrometerConnection.SpectrometerConnectionViewModule import SpectrometerConnectionViewModule
from sciens.spectracs.view.settings.login.LoginViewModule import LoginViewModule


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

        userListViewModule = UserListViewModule()
        userListViewModule.initialize()
        self.addWidget(userListViewModule)

        userViewModule = UserViewModule()
        userViewModule.initialize()
        self.addWidget(userViewModule)

        playgroundViewModule = PlaygroundViewModule()
        playgroundViewModule.initialize()
        self.addWidget(playgroundViewModule)

        wizardViewModule = WizardViewModule()  # index 12 — the pumpkin measurement wizard (C.3)
        wizardViewModule.initialize()
        self.addWidget(wizardViewModule)

        loginViewModule = LoginViewModule()  # index 13 — in-window login (Android-safe; P4c)
        loginViewModule.initialize()
        self.addWidget(loginViewModule)

        self.setCurrentWidget(spectrometerConnectionViewModule)
