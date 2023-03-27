from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton
from sqlalchemy import inspect

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from logic.persistence.database.applicationConfig.PersistGetApplicationConfigToSpectrometerProfilesLogicModule import \
    PersistGetApplicationConfigToSpectrometerProfilesLogicModule
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile
from model.databaseEntity.spectral.device import SpectrometerProfile
from view.application.widgets.page.PageWidget import PageWidget


class RegisterSpectrometerProfileViewModule(PageWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__registerButton: QPushButton = None
        self.__serialLineEdit:QLineEdit=None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label.setText(
            "Your spectrometer has been calibrated in the factory. \nPlease supply the serial number of the device for downloading the calibration profile.");
        result['label'] = label

        label.setProperty('style-primary', True)
        label.setProperty('style-bold', True)
        label.setProperty('style-large', True)

        serialLineEdit = self.getSerialLineEdit()
        result['serialLineEdit'] = self.createLabeledComponent('serial', serialLineEdit)

        registerButton = self.getRegisterButton()
        result['button'] = registerButton

        return result

    def _getPageTitle(self):
        return 'Download/Register calibration profile'

    def onTextChangeSerialLineEdit(self):
        text = self.getSerialLineEdit().text()
        self.getRegisterButton().setEnabled(len(text) >0)

    def getRegisterButton(self):
        if self.__registerButton is None:
            self.__registerButton = QPushButton()
            self.__registerButton.setText("Download/Register")
            self.__registerButton.setEnabled(False)
            self.__registerButton.clicked.connect(self.onClickedRegisterButton)

        return self.__registerButton

    def getSerialLineEdit(self):
        if self.__serialLineEdit is None:
            self.__serialLineEdit = QLineEdit()
            self.__serialLineEdit.textChanged.connect(self.onTextChangeSerialLineEdit)
        return self.__serialLineEdit

    def onClickedRegisterButton(self):

        serial = self.getSerialLineEdit().text()

        spectrometerProfiles = SpectrometerProfileUtil().getSpectrometerProfiles()

        spectrometerProfilesBySerials=dict((spectrometerProfile.serial,spectrometerProfile) for spectrometerProfile in list(spectrometerProfiles.values()))
        spectrometerProfile=spectrometerProfilesBySerials.get(serial)

        applicationConfig = ApplicationContextLogicModule().getApplicationConfig()

        applicationConfigToSpectrometerProfile = ApplicationConfigToSpectrometerProfile()
        applicationConfigToSpectrometerProfile.spectrometerProfile=spectrometerProfile


        persistApplicationConfigToSpectrometerProfileLogicModule = PersistGetApplicationConfigToSpectrometerProfilesLogicModule()

        applicationConfigToSpectrometerProfile.spectrometer_profile_id=spectrometerProfile.id
        applicationConfigToSpectrometerProfile.application_config_id=applicationConfig.id
        persistApplicationConfigToSpectrometerProfileLogicModule.getModuleParameters().setBaseEntity(applicationConfigToSpectrometerProfile)
        applicationConfigToSpectrometerProfiles = persistApplicationConfigToSpectrometerProfileLogicModule.getApplicationConfigToSpectrometerProfiles()

        if len(applicationConfigToSpectrometerProfiles)==1:
            applicationConfigToSpectrometerProfile=applicationConfigToSpectrometerProfiles.get(next(iter(applicationConfigToSpectrometerProfiles)))

        entityInspect = inspect(applicationConfigToSpectrometerProfile)
        if entityInspect.transient:
            applicationConfig.spectrometerProfiles.append(applicationConfigToSpectrometerProfile)
            session = session_factory()
            session.add(applicationConfig)
            session.commit()

        return

