from PySide6.QtWidgets import QGridLayout, QGroupBox, QLineEdit, QPushButton

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class PluginViewModule(PageWidget):
    """Master Plugin editor (SPEC_connection_and_calibration_ux.md §4.1.a). Upsert keyed on codeRef."""

    dto: dict = None
    title: QLineEdit = None
    codeRef: QLineEdit = None
    version: QLineEdit = None
    pdfRef: QLineEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compactMainContainer = True

    def _getPageTitle(self):
        return "Settings > Plugins > Plugin"

    def __isCreate(self):
        return self.dto is None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.title = QLineEdit()
        result['title'] = self.createLabeledComponent('Title', self.title)
        self.codeRef = QLineEdit()
        result['codeRef'] = self.createLabeledComponent('Code reference', self.codeRef)
        self.version = QLineEdit()
        result['version'] = self.createLabeledComponent('Version', self.version)
        self.pdfRef = QLineEdit()
        result['pdfRef'] = self.createLabeledComponent('PDF reference', self.pdfRef)
        self.__applyModelToWidgets()
        return result

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
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def __applyModelToWidgets(self):
        if self.title is None:
            return
        dto = self.dto or {}
        self.title.setText(dto.get('title') or "")
        self.codeRef.setText(dto.get('codeRef') or "")
        self.version.setText(dto.get('version') or "")
        self.pdfRef.setText(dto.get('pdfRef') or "")
        # codeRef is the key (upsert) — read-only when editing an existing plugin.
        self.codeRef.setReadOnly(not self.__isCreate())

    def onClickedSaveButton(self):
        title = self.title.text().strip()
        codeRef = self.codeRef.text().strip()
        version = self.version.text().strip()
        pdfRef = self.pdfRef.text().strip() or None
        if not title or not codeRef:
            InWindowDialog.notify(self, "Save failed", "Title and code reference are required.")
            return
        result = SpectracsPyServerClient().savePlugin(title, codeRef, version, pdfRef)
        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "save failed")
            return
        self.__navigateToList()

    def __navigateToList(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("PluginListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
