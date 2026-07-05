from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QPushButton

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerSetupViewModule(PageWidget):
    """Master instrument-setup editor (SPEC_connection_and_calibration_ux.md §4.1.c): bind a serial's
    profile to a plugin. Serials come from listSpectrometerProfiles; plugins from listPlugins."""

    dto: dict = None
    serialComboBox: QComboBox = None
    pluginComboBox: QComboBox = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compactMainContainer = True

    def _getPageTitle(self):
        return "Settings > Spectrometer setups > Setup"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.serialComboBox = QComboBox()
        result['serial'] = self.createLabeledComponent('Serial', self.serialComboBox)
        self.pluginComboBox = QComboBox()
        result['plugin'] = self.createLabeledComponent('Plugin', self.pluginComboBox)
        self.__populateChoices()
        self.__applyModelToWidgets()
        return result

    def __populateChoices(self):
        client = SpectracsPyServerClient()
        self.serialComboBox.clear()
        for profile in (client.listSpectrometerProfiles() or []):
            serial = profile.get('serial')
            if serial:
                self.serialComboBox.addItem(serial)
        self.pluginComboBox.clear()
        for plugin in (client.listPlugins() or []):
            # display the short title, carry the codeRef as item data
            self.pluginComboBox.addItem(plugin.get('title') or plugin.get('codeRef'), plugin.get('codeRef'))

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.__navigateToList)

        saveButton = QPushButton()
        saveButton.setText("Save")
        layout.addWidget(saveButton, 0, 1, 1, 1)
        saveButton.clicked.connect(self.onClickedSaveButton)

        return result

    def getModel(self):
        return self.dto

    def setModel(self, dto: dict):
        self.dto = dto
        self.__populateChoices()
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def __applyModelToWidgets(self):
        if self.serialComboBox is None:
            return
        dto = self.dto or {}
        serial = dto.get('serial')
        if serial is not None:
            index = self.serialComboBox.findText(serial)
            if index >= 0:
                self.serialComboBox.setCurrentIndex(index)
        pluginCodeRef = dto.get('pluginCodeRef')
        if pluginCodeRef is not None:
            index = self.pluginComboBox.findData(pluginCodeRef)
            if index >= 0:
                self.pluginComboBox.setCurrentIndex(index)

    def onClickedSaveButton(self):
        serial = self.serialComboBox.currentText().strip()
        pluginCodeRef = self.pluginComboBox.currentData()
        if not serial or not pluginCodeRef:
            InWindowDialog.notify(self, "Save failed",
                                  "Pick a serial (author a profile first) and a plugin.")
            return
        result = SpectracsPyServerClient().saveSpectrometerSetup(serial, pluginCodeRef)
        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "save failed")
            return
        self.__navigateToList()

    def __navigateToList(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerSetupListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
