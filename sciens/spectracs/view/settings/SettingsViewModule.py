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
from sciens.spectracs.logic.appliction.style.Metrics import Metrics


class SettingsViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)

        # B1: no per-row stretch (that spread the sections into huge uneven gaps). Sections take their
        # natural height and top-pack; a single spacer row (6) absorbs the slack so the nav pins to the
        # bottom like every other page.
        acquisitionSettingsGroupBox = self.createAcquisitionSettingsGroupBox()
        layout.addWidget(acquisitionSettingsGroupBox, 0, 0, 1, 1)

        evaluationProfilesGroupBox = self.createEvaluationProfilesGroupBox()
        layout.addWidget(evaluationProfilesGroupBox, 1, 0, 1, 1)

        downloadsGroupBoxGroupBox = self.createDownloadsGroupBox()
        layout.addWidget(downloadsGroupBoxGroupBox, 2, 0, 1, 1)

        uploadsGroupBoxGroupBox = self.createUploadsGroupBox()
        layout.addWidget(uploadsGroupBoxGroupBox, 3, 0, 1, 1)

        infosGroupBox = self.createInfosGroupBox()
        layout.addWidget(infosGroupBox, 4, 0, 1, 1)

        self.administrationGroupBox = self.createAdministrationGroupBox()
        layout.addWidget(self.administrationGroupBox, 5, 0, 1, 1)

        layout.setRowStretch(6, 1)  # spacer absorbs slack -> sections top-pack, nav at bottom

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 7, 0, 1, 1)

        # The Administration group is master-only; refresh visibility on login/logout.
        ApplicationContextLogicModule().getApplicationSignalsProvider().userSessionSignal.connect(
            self.updateAdministrationVisibility)
        self.updateAdministrationVisibility()


    def createAcquisitionSettingsGroupBox(self):
        result = QGroupBox("Acquisition")
        result.setProperty("sectionLabel", True)  # B4: uniform borderless section heading

        layout = QGridLayout()
        result.setLayout(layout)
        layout.setSpacing(Metrics.S)

        comboBox=self.createLabeledComponent('Measurement profile',QComboBox())
        layout.addWidget(comboBox, 0, 0, 1, 1)

        openSpectrometerConnectionViewModuleButton = QPushButton()
        openSpectrometerConnectionViewModuleButton.setText("Connect spectrometer")
        openSpectrometerConnectionViewModuleButton.clicked.connect(self.onClickedOpenSpectrometerConnectionViewModuleButton)

        openMeasurementProfilesListViewModuleButton = QPushButton()
        openMeasurementProfilesListViewModuleButton.setText("Measurement profiles")

        openVirtualSpectrometerViewModuleButton = QPushButton()
        openVirtualSpectrometerViewModuleButton.setText("Virtual Spectrometer")
        openVirtualSpectrometerViewModuleButton.clicked.connect(self.onClickedOpenVirtualSpectrometerViewModuleButton)

        # §11: the "Device calibration (legacy)" screen is retired — interactive calibration now lives in
        # the SpectrometerSetup editor's embedded wizard. R3: buttons stack on phone width, row on desktop.
        buttonsRow = ResponsiveRow([
            openSpectrometerConnectionViewModuleButton,
            openMeasurementProfilesListViewModuleButton,
            openVirtualSpectrometerViewModuleButton,
        ])
        layout.addWidget(buttonsRow, 1, 0, 1, 1)

        return result

    def createAdministrationGroupBox(self):
        result = QGroupBox("Administration")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        openUserListViewModuleButton = QPushButton()
        openUserListViewModuleButton.setText("Users")
        layout.addWidget(openUserListViewModuleButton, 0, 0, 1, 1)
        openUserListViewModuleButton.clicked.connect(self.onClickedUsersButton)

        openPlaygroundViewModuleButton = QPushButton()
        openPlaygroundViewModuleButton.setText("Playground")
        layout.addWidget(openPlaygroundViewModuleButton, 0, 1, 1, 1)
        openPlaygroundViewModuleButton.clicked.connect(self.onClickedPlaygroundButton)

        openPluginsButton = QPushButton()
        openPluginsButton.setText("Plugins")
        layout.addWidget(openPluginsButton, 0, 2, 1, 1)
        openPluginsButton.clicked.connect(self.onClickedPluginsButton)

        # §11 reconsolidation: the separate "Spectrometer profiles (authoring)" screen is retired — the
        # unified "Spectrometer setups" editor now assembles serial + device + calibration + plugin + user.
        openSetupsButton = QPushButton()
        openSetupsButton.setText("Spectrometer setups")
        layout.addWidget(openSetupsButton, 1, 0, 1, 1)
        openSetupsButton.clicked.connect(self.onClickedSpectrometerSetupsButton)

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
        self.administrationGroupBox.setVisible(isMaster)

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

    def createInfosGroupBox(self):
        result = QGroupBox("Infos")
        result.setProperty("sectionLabel", True)  # B4: uniform borderless section heading

        layout = QGridLayout()
        result.setLayout(layout)
        layout.setSpacing(Metrics.S)

        openApplicationAboutViewModuleButton = QPushButton()
        openApplicationAboutViewModuleButton.setText("About")
        layout.addWidget(openApplicationAboutViewModuleButton, 0, 0, 1, 1)

        openApplicationHelpViewModuleButton = QPushButton()
        openApplicationHelpViewModuleButton.setText("Help")
        layout.addWidget(openApplicationHelpViewModuleButton, 0, 1, 1, 1)

        return result


    def createEvaluationProfilesGroupBox(self):
        result = QGroupBox("Evaluation profiles")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        openEvaluationProfileListViewModuleButton = QPushButton()
        openEvaluationProfileListViewModuleButton.setText("Evaluation profiles")
        layout.addWidget(openEvaluationProfileListViewModuleButton, 0, 0, 1, 1)

        return result


    def createDownloadsGroupBox(self):
        result = QGroupBox("Downloads")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        openRepositoryProfileListViewModuleButton = QPushButton()
        openRepositoryProfileListViewModuleButton.setText("Repository profiles")
        layout.addWidget(openRepositoryProfileListViewModuleButton, 0, 0, 1, 1)

        return result

    def createUploadsGroupBox(self):
        result = QGroupBox("Uploads")
        result.setProperty("sectionLabel", True)  # single-child frame -> section label (spec C2b)

        layout = QGridLayout()
        result.setLayout(layout)

        openUploadProfileListViewModuleButton = QPushButton()
        openUploadProfileListViewModuleButton.setText("Upload profiles")
        layout.addWidget(openUploadProfileListViewModuleButton, 0, 0, 1, 1)

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

    def onClickedOpenSpectrometerConnectionViewModuleButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerConnectionViewModule")
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


