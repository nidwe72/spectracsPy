from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QPushButton

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from view.application.widgets.general.ToggleSwitch import ToggleSwitch
from view.application.widgets.page.PageWidget import PageWidget

class VirtualCameraViewModule(PageWidget):

    useVirtualCameraComponent:ToggleSwitch=None

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Virtual Camera")
        return result

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.useVirtualCameraComponent=ToggleSwitch(None,Qt.gray,ApplicationStyleLogicModule().getPrimaryColor())
        self.useVirtualCameraComponent.setCheckable(True)
        # self.useVirtualCameraCheckbox.setReadOnly(True)
        result['useVirtualCameraComponent']=self.createLabeledComponent('use virtual camera',self.useVirtualCameraComponent)

        return result

    def _getPageTitle(self):
        return "Virtual camera"


