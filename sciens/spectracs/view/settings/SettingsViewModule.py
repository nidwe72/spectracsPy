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
        self.setLayout(layout)

        acquisitionSettingsGroupBox = self.createAcquisitionSettingsGroupBox()
        layout.addWidget(acquisitionSettingsGroupBox, 0, 0, 1, 1)
        layout.setRowStretch(0, 15)

        evaluationProfilesGroupBox = self.createEvaluationProfilesGroupBox()
        layout.addWidget(evaluationProfilesGroupBox, 1, 0, 1, 1)
        layout.setRowStretch(1, 15)

        downloadsGroupBoxGroupBox = self.createDownloadsGroupBox()
        layout.addWidget(downloadsGroupBoxGroupBox, 2, 0, 1, 1)
        layout.setRowStretch(2, 15)

        uploadsGroupBoxGroupBox = self.createUploadsGroupBox()
        layout.addWidget(uploadsGroupBoxGroupBox, 3, 0, 1, 1)
        layout.setRowStretch(3, 15)

        infosGroupBox = self.createInfosGroupBox()
        layout.addWidget(infosGroupBox, 4, 0, 1, 1)
        layout.setRowStretch(4, 15)

        self.administrationGroupBox = self.createAdministrationGroupBox()
        layout.addWidget(self.administrationGroupBox, 5, 0, 1, 1)
        layout.setRowStretch(5, 15)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 6, 0, 1, 1)

        # The Administration group is master-only; refresh visibility on login/logout.
        ApplicationContextLogicModule().getApplicationSignalsProvider().userSessionSignal.connect(
            self.updateAdministrationVisibility)
        self.updateAdministrationVisibility()


    def createAcquisitionSettingsGroupBox(self):
        result = QGroupBox("Acquisition")

        layout = QGridLayout()
        result.setLayout(layout)
        Metrics.applyPanelPadding(layout)

        comboBox=self.createLabeledComponent('Measurement profile',QComboBox())
        layout.addWidget(comboBox, 0, 0, 1, 1)

        openSpectrometerConnectionViewModuleButton = QPushButton()
        openSpectrometerConnectionViewModuleButton.setText("Connect spectrometer")
        openSpectrometerConnectionViewModuleButton.clicked.connect(self.onClickedOpenSpectrometerConnectionViewModuleButton)

        openSpectrometerProfileListViewModuleButton = QPushButton()
        openSpectrometerProfileListViewModuleButton.setText("Spectrometer profiles")
        openSpectrometerProfileListViewModuleButton.clicked.connect(self.onClickedCameraSelectionButton)

        openMeasurementProfilesListViewModuleButton = QPushButton()
        openMeasurementProfilesListViewModuleButton.setText("Measurement profiles")

        openVirtualSpectrometerViewModuleButton = QPushButton()
        openVirtualSpectrometerViewModuleButton.setText("Virtual Spectrometer")
        openVirtualSpectrometerViewModuleButton.clicked.connect(self.onClickedOpenVirtualSpectrometerViewModuleButton)

        # R3: four action buttons that overflow 412 dp as a single row -> ResponsiveRow stacks them
        # vertically on the phone and keeps them in a row on the desktop.
        buttonsRow = ResponsiveRow([
            openSpectrometerConnectionViewModuleButton,
            openSpectrometerProfileListViewModuleButton,
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

        return result

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

        layout = QGridLayout()
        result.setLayout(layout)
        Metrics.applyPanelPadding(layout)

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

    def onClickedCameraSelectionButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileListViewModule")
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


