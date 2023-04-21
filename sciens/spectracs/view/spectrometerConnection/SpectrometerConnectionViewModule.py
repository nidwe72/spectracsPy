from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QComboBox

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.spectrometerConnection.RegisterSpectrometerProfileViewModule import RegisterSpectrometerProfileViewModule


class SpectrometerConnectionViewModule(PageWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__selectSpectrometerProfileComboBox: QComboBox = None
        self.__registerSpectrometerProfileViewModule = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        selectSpectrometerProfileComboBox = self.getSelectSpectrometerProfileComboBox()
        result['selectSpectrometerProfileComboBox'] = self.createLabeledComponent('Spectrometer',
                                                                                  selectSpectrometerProfileComboBox)
        self.updateSelectSpectrometerProfileComboBoxModel()
        selectSpectrometerProfileComboBox.currentIndexChanged.connect(self.onChangedSelectSpectrometerProfileComboBox)

        result['registerSpectrometerProfileViewModule'] = self.getRegisterSpectrometerProfileViewModule()

        return result

    def getRegisterSpectrometerProfileViewModule(self):
        if self.__registerSpectrometerProfileViewModule is None:
            self.__registerSpectrometerProfileViewModule = RegisterSpectrometerProfileViewModule(self)
            self.__registerSpectrometerProfileViewModule.initialize()
        return self.__registerSpectrometerProfileViewModule

    def getSelectSpectrometerProfileComboBox(self):
        if self.__selectSpectrometerProfileComboBox is None:
            self.__selectSpectrometerProfileComboBox = QComboBox()
        return self.__selectSpectrometerProfileComboBox

    def updateSelectSpectrometerProfileComboBoxModel(self):
        model = QStandardItemModel()

        spectrometerProfilesMapping = ApplicationContextLogicModule().getApplicationConfig().getSpectrometerProfilesMapping()

        for spectrometerProfilesMappingEntry in spectrometerProfilesMapping:
            item = QStandardItem()

            spectrometerProfile = spectrometerProfilesMappingEntry.spectrometerProfile
            spectrometerName = SpectrometerUtil().getEntityViewName(spectrometerProfile.spectrometer);
            text = f"{spectrometerName} ({spectrometerProfile.serial})"
            item.setText(text)
            item.setData(spectrometerProfilesMappingEntry)
            model.appendRow(item)

        self.getSelectSpectrometerProfileComboBox().setModel(model)

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        return result

    def onChangedSelectSpectrometerProfileComboBox(self):
        spectrometerProfileComboBox = self.getSelectSpectrometerProfileComboBox()

        comboBoxModel = spectrometerProfileComboBox.model()
        if isinstance(comboBoxModel, QStandardItemModel):
            spectrometerProfileMappingEntry = comboBoxModel.item(spectrometerProfileComboBox.currentIndex()).data()
            if isinstance(spectrometerProfileMappingEntry,ApplicationConfigToSpectrometerProfile):

                applicationConfig = ApplicationContextLogicModule().getApplicationConfig()
                spectrometerProfilesMapping = applicationConfig.getSpectrometerProfilesMapping()
                for someSpectrometerProfilesMappingEntry in spectrometerProfilesMapping:
                    isDefault = False
                    if someSpectrometerProfilesMappingEntry.id==spectrometerProfileMappingEntry.id:
                        isDefault = True
                    someSpectrometerProfilesMappingEntry.isDefault=isDefault
                    session = session_factory()
                    session.add(someSpectrometerProfilesMappingEntry)
                    session.commit()

        self.setConfiguredSpectrometerProfileIntoApplicationSettings()

        return

    def onClickedBackButton(self):
        previousNavigationSignal = ApplicationContextLogicModule().getNavigationHandler().getPreviousNavigationSignal()
        previousTarget = None
        if previousNavigationSignal is not None:
            previousTarget = previousNavigationSignal.geTarget()

        navigationHandler = ApplicationContextLogicModule().getNavigationHandler()

        navigationHandler.getPreviousNavigationSignal()

        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            navigationHandler.handleNavigationSignal)

        someNavigationSignal = NavigationSignal(None)

        if previousTarget is None:
            someNavigationSignal.setTarget("Home")
        else:
            someNavigationSignal.setTarget(previousTarget)

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def _getPageTitle(self):
        return 'Connect spectrometer';

    def initialize(self):
        super().initialize()
        self.setConfiguredSpectrometerProfileIntoApplicationSettings()

    def setConfiguredSpectrometerProfileIntoApplicationSettings(self) :
        SpectrometerProfileUtil().setConfiguredSpectrometerProfileIntoApplicationSettings()


