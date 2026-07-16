from PySide6.QtWidgets import QWidget, QComboBox
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QPushButton, QSizePolicy

from sciens.spectracs.view.application.widgets.ResponsiveRow import ResponsiveRow


from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.page.PageLabel import PageLabel
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.logic.application.style.Metrics import Metrics


class SettingsViewModule(QWidget):

    APP_NAME = "Spectracs"
    APP_VERSION = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)

        # B1: no per-row stretch (that spread the sections into huge uneven gaps). Sections take their
        # natural height and top-pack; a single spacer row (6) absorbs the slack so the nav pins to the
        # bottom like every other page.
        # §G2: dropped the dead Evaluation-profiles and Uploads sections. Kept Acquisition (Virtual
        # Spectrometer), Downloads (Repository profiles — future server-connection config), Infos, Admin.
        # Item C: Acquisition holds only "Virtual Spectrometer" (master authoring), so it is master-only
        # (kept on self so updateAdministrationVisibility can toggle it). SPEC_gui_cosmetic_tweaks §3.
        self.acquisitionSettingsGroupBox = self.createAcquisitionSettingsGroupBox()
        layout.addWidget(self.acquisitionSettingsGroupBox, 0, 0, 1, 1)

        downloadsGroupBoxGroupBox = self.createDownloadsGroupBox()
        layout.addWidget(downloadsGroupBoxGroupBox, 1, 0, 1, 1)

        infosGroupBox = self.createInfosGroupBox()
        layout.addWidget(infosGroupBox, 2, 0, 1, 1)

        self.administrationGroupBox = self.createAdministrationGroupBox()
        layout.addWidget(self.administrationGroupBox, 3, 0, 1, 1)

        self.developmentGroupBox = self.createDevelopmentGroupBox()
        layout.addWidget(self.developmentGroupBox, 4, 0, 1, 1)

        layout.setRowStretch(5, 1)  # spacer absorbs slack -> sections top-pack, nav at bottom

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 6, 0, 1, 1)

        # Administration + Development are master-only; refresh visibility on login/logout.
        ApplicationContextLogicModule().getApplicationSignalsProvider().userSessionSignal.connect(
            self.updateAdministrationVisibility)
        self.updateAdministrationVisibility()


    def createAcquisitionSettingsGroupBox(self):
        result = QGroupBox("Acquisition")
        result.setProperty("sectionLabel", True)  # B4: uniform borderless section heading

        layout = QGridLayout()
        result.setLayout(layout)
        layout.setSpacing(Metrics.S)

        # §G2: removed the dead "Measurement profile" combo + "Measurement profiles" button and the retired
        # "Connect spectrometer" screen (connection is now the header indicator + autoconnect; interactive
        # calibration lives in the SpectrometerSetup wizard, §11). Only Virtual Spectrometer remains here.
        openVirtualSpectrometerViewModuleButton = QPushButton()
        openVirtualSpectrometerViewModuleButton.setText("Virtual Spectrometer")
        openVirtualSpectrometerViewModuleButton.clicked.connect(self.onClickedOpenVirtualSpectrometerViewModuleButton)

        buttonsRow = ResponsiveRow([
            openVirtualSpectrometerViewModuleButton,
        ])
        layout.addWidget(buttonsRow, 0, 0, 1, 1)

        return result

    def createAdministrationGroupBox(self):
        result = QGroupBox("Administration")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        # Order (Edwin): Spectrometer setups, Users, Plugins. (Playground moved to Development.)
        openSetupsButton = QPushButton()
        openSetupsButton.setText("Spectrometer setups")
        layout.addWidget(openSetupsButton, 0, 0, 1, 1)
        openSetupsButton.clicked.connect(self.onClickedSpectrometerSetupsButton)

        openUserListViewModuleButton = QPushButton()
        openUserListViewModuleButton.setText("Users")
        layout.addWidget(openUserListViewModuleButton, 0, 1, 1, 1)
        openUserListViewModuleButton.clicked.connect(self.onClickedUsersButton)

        openPluginsButton = QPushButton()
        openPluginsButton.setText("Plugins")
        layout.addWidget(openPluginsButton, 0, 2, 1, 1)
        openPluginsButton.clicked.connect(self.onClickedPluginsButton)

        return result

    def createDevelopmentGroupBox(self):
        result = QGroupBox("Development")
        result.setProperty("sectionLabel", True)

        layout = QGridLayout()
        result.setLayout(layout)

        openPlaygroundViewModuleButton = QPushButton()
        openPlaygroundViewModuleButton.setText("Playground")
        layout.addWidget(openPlaygroundViewModuleButton, 0, 0, 1, 1)
        openPlaygroundViewModuleButton.clicked.connect(self.onClickedPlaygroundButton)

        captureImagesButton = QPushButton()
        captureImagesButton.setText("Capture images")
        layout.addWidget(captureImagesButton, 1, 0, 1, 1)
        captureImagesButton.clicked.connect(self.onClickedCaptureImagesButton)

        measurementBenchButton = QPushButton()
        measurementBenchButton.setText("Measurement bench")
        layout.addWidget(measurementBenchButton, 2, 0, 1, 1)
        measurementBenchButton.clicked.connect(self.onClickedMeasurementBenchButton)

        return result

    def __navigateTo(self, target):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedPluginsButton(self):
        self.__navigateTo("PluginListViewModule")

    def onClickedSpectrometerSetupsButton(self):
        self.__navigateTo("SpectrometerSetupListViewModule")

    def updateAdministrationVisibility(self):
        isMaster = CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value)
        self.acquisitionSettingsGroupBox.setVisible(isMaster)  # Item C: Virtual Spectrometer is master-only
        self.administrationGroupBox.setVisible(isMaster)
        self.developmentGroupBox.setVisible(isMaster)

    def onClickedUsersButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("UserListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedPlaygroundButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("PlaygroundViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedCaptureImagesButton(self):
        self.__navigateTo("DevCaptureViewModule")

    def onClickedMeasurementBenchButton(self):
        self.__navigateTo("DevMeasurementBenchViewModule")

    def createInfosGroupBox(self):
        result = QGroupBox("Infos")
        result.setProperty("sectionLabel", True)  # B4: uniform borderless section heading

        layout = QGridLayout()
        result.setLayout(layout)
        layout.setSpacing(Metrics.S)

        openApplicationAboutViewModuleButton = QPushButton()
        openApplicationAboutViewModuleButton.setText("About")
        layout.addWidget(openApplicationAboutViewModuleButton, 0, 0, 1, 1)
        openApplicationAboutViewModuleButton.clicked.connect(self.onClickedAboutButton)

        openApplicationHelpViewModuleButton = QPushButton()
        openApplicationHelpViewModuleButton.setText("Help")
        layout.addWidget(openApplicationHelpViewModuleButton, 0, 1, 1, 1)
        openApplicationHelpViewModuleButton.clicked.connect(self.onClickedHelpButton)

        return result

    def onClickedAboutButton(self):
        InWindowDialog.notify(self, "About %s" % self.APP_NAME,
                              "%s — version %s" % (self.APP_NAME, self.APP_VERSION))

    def onClickedHelpButton(self):
        InWindowDialog.notify(
            self, "Help",
            "%s turns a hand-held grating spectrometer and your device camera into a spectroscopy "
            "workstation: capture a spectrum, calibrate it against known lines, and run a plugin evaluation. "
            "A master authors calibrated instruments; an end user registers a device by its serial and "
            "measures." % self.APP_NAME)


    def createDownloadsGroupBox(self):
        result = QGroupBox("Downloads")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        # §G2 placeholder: kept as the intended home for spectracsPy-server connection details / repo config
        # (SPEC_gui_refinements §G2 note). Not wired yet.
        openRepositoryProfileListViewModuleButton = QPushButton()
        openRepositoryProfileListViewModuleButton.setText("Repository profiles")
        layout.addWidget(openRepositoryProfileListViewModuleButton, 0, 0, 1, 1)

        return result


    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        return result


    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedOpenVirtualSpectrometerViewModuleButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("VirtualSpectrometerViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def createLabeledComponent(self,label:str,component:QWidget):
        container=QWidget()

        layout=QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # align to container content edge (spec C7)
        container.setLayout(layout)
        labelComponent=PageLabel(label)
        # R1: chip fills its column so labels align uniformly (see PageWidget.createLabeledComponent).
        labelComponent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(labelComponent,0,0,1,1)
        layout.setColumnStretch(0,30)

        layout.addWidget(component, 0, 1, 1, 1)
        layout.setColumnStretch(1, 70)

        return container


