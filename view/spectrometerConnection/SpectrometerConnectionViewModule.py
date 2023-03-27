from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel, QLineEdit, QComboBox

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.spectrometerConnection.RegisterSpectrometerProfileViewModule import RegisterSpectrometerProfileViewModule


class SpectrometerConnectionViewModule(PageWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__selectSpectrometerProfileComboBox:QComboBox=None
        self.__registerSpectrometerProfileViewModule=None



    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        applicationConfig = ApplicationContextLogicModule().getApplicationConfig()

        #todo:next

        # * rename this class to SelectSpectrometerViewModule
        # * view is not offered a start if
        #   * there is only one persisted SpectrometerProfile
        #     * in this case the SpectrometerProfile is set automatically into ApplicationSettings
        # * PersistentApplicationSettings
        #   * has a list of SpectrometerProfile/s
        #   * list of SpectrometerProfile/s is updated at saving a SpectrometerProfile
        #   * a superuser can push/pull the list
        # * normal user
        #  * offer list of spectrometers from PersistentApplicationSettings.spectrometerProfiles
        #  * if the list is empty: offer a text field letting the user specify the serial number
        #  * if the list is not empty:
        #    * mark entries as read-ony if the sensor is not connected
        #    * offer a select button
        #    * offer a refresh
        #    * if there are more selectable entries offer a note that it is only possible to have one spectrometer
        #      connected
        #  * superuser
        #    * offer another text field letting one filter the offered entries as there might be many
        #    * let one pull all profiles



        selectSpectrometerProfileComboBox = self.getSelectSpectrometerProfileComboBox()
        result['selectSpectrometerProfileComboBox'] = self.createLabeledComponent('Spectrometer',
                                                                                      selectSpectrometerProfileComboBox)

        result['registerSpectrometerProfileViewModule']=self.getRegisterSpectrometerProfileViewModule()

        return result

    def getRegisterSpectrometerProfileViewModule(self):
        if self.__registerSpectrometerProfileViewModule is None:
            self.__registerSpectrometerProfileViewModule=RegisterSpectrometerProfileViewModule(self)
            self.__registerSpectrometerProfileViewModule.initialize()
        return self.__registerSpectrometerProfileViewModule

    def getSelectSpectrometerProfileComboBox(self):
        if self.__selectSpectrometerProfileComboBox is None:
            self.__selectSpectrometerProfileComboBox=QComboBox()
        return self.__selectSpectrometerProfileComboBox

    def updateSelectSpectrometerProfileComboBoxModel(self):
        model = QStandardItemModel()

        spectrometerProfiles=ApplicationContextLogicModule().getApplicationConfig().getSpectrometerProfiles()

        for spectrometerProfile in spectrometerProfiles:
            item = QStandardItem()
            item.setText(spectrometerProfile.serial)
            item.setData(spectrometerProfile)
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

    def onClickedBackButton(self):
        previousNavigationSignal = ApplicationContextLogicModule().getNavigationHandler().getPreviousNavigationSignal()
        previousTarget=None
        if previousNavigationSignal is not None:
            previousTarget=previousNavigationSignal.geTarget()

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

