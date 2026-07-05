from PySide6.QtWidgets import QStackedWidget

from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.view.home.HomeViewModule import HomeViewModule
from sciens.spectracs.view.settings.SettingsViewModule import SettingsViewModule
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
from sciens.spectracs.view.settings.plugin.PluginListViewModule import PluginListViewModule
from sciens.spectracs.view.settings.plugin.PluginViewModule import PluginViewModule
from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupListViewModule import \
    SpectrometerSetupListViewModule
from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupViewModule import \
    SpectrometerSetupViewModule
from sciens.spectracs.view.registration.RegistrationViewModule import RegistrationViewModule


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

        # §11 wizard: the legacy Spectrometer-profile list+editor are retired; the calibration wizard
        # (idx 4) is reached only from the unified SpectrometerSetup editor's embedded Edit button.
        spectrometerProfile=SpectrometerProfile()
        SpectrometerProfileUtil().initializeSpectrometerProfile(spectrometerProfile)

        spectrometerCalibrationProfileViewModule=SpectrometerCalibrationProfileViewModule()  # index 4 — calibration wizard
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

        wizardViewModule = WizardViewModule()  # index 10 — the pumpkin measurement wizard (C.3)
        wizardViewModule.initialize()
        self.addWidget(wizardViewModule)

        loginViewModule = LoginViewModule()  # index 11 — in-window login (Android-safe; P4c)
        loginViewModule.initialize()
        self.addWidget(loginViewModule)

        # --- master authoring GUIs (SPEC_connection_and_calibration_ux.md §4.1 / §11, indices 12-16) ---
        # §11 reconsolidation: the separate SpectrometerProfileAuthoring list+editor is retired; the unified
        # SpectrometerSetupViewModule now assembles serial + device + calibration + plugin + user.
        pluginListViewModule = PluginListViewModule()  # index 12
        pluginListViewModule.initialize()
        self.addWidget(pluginListViewModule)

        pluginViewModule = PluginViewModule()  # index 13
        pluginViewModule.initialize()
        self.addWidget(pluginViewModule)

        spectrometerSetupListViewModule = SpectrometerSetupListViewModule()  # index 14
        spectrometerSetupListViewModule.initialize()
        self.addWidget(spectrometerSetupListViewModule)

        spectrometerSetupViewModule = SpectrometerSetupViewModule()  # index 15
        spectrometerSetupViewModule.initialize()
        self.addWidget(spectrometerSetupViewModule)

        registrationViewModule = RegistrationViewModule()  # index 16 — end-user self-registration (C1)
        registrationViewModule.initialize()
        self.addWidget(registrationViewModule)

        self.setCurrentWidget(spectrometerConnectionViewModule)
