from PyQt6.QtWidgets import QPushButton

from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from view.application.widgets.page.PageWidget import PageWidget


class SpectrometerCalibrationProfileViewModule(PageWidget):

    model: SpectrometerCalibrationProfile = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        super().initialize()

    def _getPageTitle(self):
        return "Calibration profile"

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        editCalibrationProfileButton=QPushButton('Edit')
        editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
        result[editCalibrationProfileButton.objectName()]=editCalibrationProfileButton

        return result





