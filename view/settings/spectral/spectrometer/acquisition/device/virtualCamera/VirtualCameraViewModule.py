from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QCheckBox, QPushButton, QFileDialog, QGroupBox, QGridLayout

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.general.ToggleSwitch import ToggleSwitch
from view.application.widgets.page.PageWidget import PageWidget

class VirtualCameraViewModule(PageWidget):

    useVirtualCameraComponent:ToggleSwitch=None
    openPictureButton:QPushButton=None

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Virtual Camera")
        return result

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.useVirtualCameraComponent=ToggleSwitch(None,Qt.gray,ApplicationStyleLogicModule().getPrimaryColor())
        #self.useVirtualCameraComponent.setCheckable(True)
        result['useVirtualCameraComponent']=self.createLabeledComponent('use virtual camera',self.useVirtualCameraComponent)

        self.openPictureButton=QPushButton('Set picture')
        result['openPictureButton'] = self.openPictureButton
        self.openPictureButton.clicked.connect(self.onClickedOpenPictureButton)

        return result

    def _getPageTitle(self):
        return "Virtual camera"


    def onClickedOpenPictureButton(self):
        filepath = QFileDialog.getOpenFileName(self, 'Open picture',                                            None, "Image files (*.png *.jpg *.gif)")
        image=QImage(filepath[0])
        #image.load(filepath,QImage.Format.Format_RGB888)
        ApplicationContextLogicModule().setVirtualCameraImage(image)

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
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)


