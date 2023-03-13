from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
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
            # self.__registerButton.clicked.connect(self.onClickedBackButton)

        return self.__registerButton

    def getSerialLineEdit(self):
        if self.__serialLineEdit is None:
            self.__serialLineEdit = QLineEdit()
            self.__serialLineEdit.textChanged.connect(self.onTextChangeSerialLineEdit)
        return self.__serialLineEdit

