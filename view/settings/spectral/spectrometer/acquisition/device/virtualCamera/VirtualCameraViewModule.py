from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QPushButton, QFileDialog

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
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
        fname = QFileDialog.getOpenFileName(self, 'Open picture',
                                            None, "Image files (*.jpg *.gif)")


