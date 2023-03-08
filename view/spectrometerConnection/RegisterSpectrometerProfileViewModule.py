from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from view.application.widgets.page.PageWidget import PageWidget


class RegisterSpectrometerProfileViewModule(PageWidget):

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # label.setAutoFillBackground(True)
        # label.palette().setColor(label.foregroundRole(),ApplicationStyleLogicModule().getPrimaryTextColor())
        # label.palette().setColor(label.backgroundRole(), ApplicationStyleLogicModule().getPrimaryTextColor())
        label.setText(
            "Your spectrometer has been calibrated in the factory. \nPlease supply the serial number of the device for downloading the calibration profile.");
        result['label'] = label

        label.setProperty('style-primary',True)
        label.setProperty('style-bold', True)
        label.setProperty('style-large', True)

        serialComponent = QLineEdit()
        result['serialComponent'] = self.createLabeledComponent('serial', serialComponent)

        registerButton = QPushButton()
        registerButton.setText("Download/Register")
        # registerButton.clicked.connect(self.onClickedBackButton)

        result['button'] = registerButton

        return result

    def _getPageTitle(self):
        return 'Download/Register calibration profile'
