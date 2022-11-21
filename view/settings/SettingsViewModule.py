from PySide6.QtWidgets import QWidget, QComboBox
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QPushButton


from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.page.PageLabel import PageLabel


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

        serviceLoginGroupBox = self.createServiceLoginGroupBox()
        layout.addWidget(serviceLoginGroupBox, 4, 0, 1, 1)
        layout.setRowStretch(4, 15)

        infosGroupBox = self.createInfosGroupBox()
        layout.addWidget(infosGroupBox, 5, 0, 1, 1)
        layout.setRowStretch(5, 15)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 6, 0, 1, 1)


    def createAcquisitionSettingsGroupBox(self):
        result = QGroupBox("Acquisition")

        layout = QGridLayout()
        result.setLayout(layout)

        comboBox=self.createLabeledComponent('Measurement profile',QComboBox())
        layout.addWidget(comboBox, 0, 0, 1, 3)

        openSpectrometerProfileListViewModuleButton = QPushButton()
        openSpectrometerProfileListViewModuleButton.setText("Spectrometer profiles")
        layout.addWidget(openSpectrometerProfileListViewModuleButton, 1, 0, 1, 1)
        openSpectrometerProfileListViewModuleButton.clicked.connect(self.onClickedCameraSelectionButton)

        openMeasurementProfilesListViewModuleButton = QPushButton()
        openMeasurementProfilesListViewModuleButton.setText("Measurement profiles")
        layout.addWidget(openMeasurementProfilesListViewModuleButton, 1, 1, 1, 1)

        openVirtualCameraViewModuleButton = QPushButton()
        openVirtualCameraViewModuleButton.setText("Virtual Camera")
        layout.addWidget(openVirtualCameraViewModuleButton, 1, 2, 1, 1)
        openVirtualCameraViewModuleButton.clicked.connect(self.onClickedOpenVirtualCameraViewModuleButton)



        return result

    def createServiceLoginGroupBox(self):
        result = QGroupBox("Service Login")

        layout = QGridLayout()
        result.setLayout(layout)

        openServiceLoginViewModuleButton = QPushButton()
        openServiceLoginViewModuleButton.setText("Login")
        layout.addWidget(openServiceLoginViewModuleButton, 0, 0, 1, 1)

        return result

    def createInfosGroupBox(self):
        result = QGroupBox("Infos")

        layout = QGridLayout()
        result.setLayout(layout)

        openApplicationAboutViewModuleButton = QPushButton()
        openApplicationAboutViewModuleButton.setText("About")
        layout.addWidget(openApplicationAboutViewModuleButton, 0, 0, 1, 1)

        openApplicationHelpViewModuleButton = QPushButton()
        openApplicationHelpViewModuleButton.setText("Help")
        layout.addWidget(openApplicationHelpViewModuleButton, 0, 1, 1, 1)

        return result


    def createEvaluationProfilesGroupBox(self):
        result = QGroupBox("Evaluation profiles")

        layout = QGridLayout()
        result.setLayout(layout)

        openEvaluationProfileListViewModuleButton = QPushButton()
        openEvaluationProfileListViewModuleButton.setText("Evaluation profiles")
        layout.addWidget(openEvaluationProfileListViewModuleButton, 0, 0, 1, 1)

        return result


    def createDownloadsGroupBox(self):
        result = QGroupBox("Downloads")

        layout = QGridLayout()
        result.setLayout(layout)

        openRepositoryProfileListViewModuleButton = QPushButton()
        openRepositoryProfileListViewModuleButton.setText("Repository profiles")
        layout.addWidget(openRepositoryProfileListViewModuleButton, 0, 0, 1, 1)

        return result

    def createUploadsGroupBox(self):
        result = QGroupBox("Uploads")

        layout = QGridLayout()
        result.setLayout(layout)

        openUploadProfileListViewModuleButton = QPushButton()
        openUploadProfileListViewModuleButton.setText("Upload profiles")
        layout.addWidget(openUploadProfileListViewModuleButton, 0, 0, 1, 1)

        return result


    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
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

    def onClickedOpenVirtualCameraViewModuleButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("VirtualCameraViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def createLabeledComponent(self,label:str,component:QWidget):
        container=QWidget()

        layout=QGridLayout()
        container.setLayout(layout)
        labelComponent=PageLabel(label)
        layout.addWidget(labelComponent,0,0,1,1)
        layout.setColumnStretch(0,30)

        layout.addWidget(component, 0, 1, 1, 1)
        layout.setColumnStretch(1, 70)

        return container


