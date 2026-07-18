from PySide6.QtWidgets import QGridLayout, QGroupBox, QLineEdit, QPushButton, QWidget, QFileDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.security import PluginSigner
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.plugin.PluginPublishUtil import (
    inspectPluginSource, codeRefMatchesClass, PluginSourceError)
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class PluginViewModule(PageWidget):
    """Master plugin PUBLISHER (SPEC_plugin_distribution.md §8, B4). A published (codeRef, version) row is
    IMMUTABLE and signed, so this screen never edits an existing row — it PUBLISHES a new version:

      pick source .py -> import it on the master (trusted) to DERIVE title + targetSdkVersion (Q5) + the class
      name -> validate the codeRef's tail == the class name (D-coderef) -> SIGN the tuple locally with the
      master's private key -> INSERT a sealed row via savePlugin.

    'Add' starts a brand-new codeRef; 'New version' (from the list) inherits the codeRef + carries a fresh
    source. The private key never leaves the master; publishing is disabled when it is absent (§3)."""

    dto: dict = None
    title: QLineEdit = None
    codeRef: QLineEdit = None
    version: QLineEdit = None
    pdfRef: QLineEdit = None
    sourceField: QLineEdit = None
    targetSdkField: QLineEdit = None
    publishButton: QPushButton = None

    __source: str = None
    __className: str = None
    __targetSdkVersion = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compactMainContainer = True

    def _getPageTitle(self):
        return "Settings > Plugins > Publish a version"

    def __isNewVersion(self):
        # A dto means "new version of an existing plugin" — the codeRef is inherited (read-only); a fresh
        # source + version are still required. No dto -> a brand-new codeRef.
        return self.dto is not None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.title = QLineEdit()
        self.title.setReadOnly(True)  # derived from the picked source (Q5) — never hand-typed
        self.title.setPlaceholderText("derived from the picked source")
        result['title'] = self.createLabeledComponent('Title', self.title)
        self.codeRef = QLineEdit()
        result['codeRef'] = self.createLabeledComponent('Code reference', self.codeRef)
        self.version = QLineEdit()
        result['version'] = self.createLabeledComponent('Version', self.version)
        self.sourceField = QLineEdit()
        self.sourceField.setReadOnly(True)
        self.sourceField.setPlaceholderText("pick the plugin .py to publish")
        result['source'] = self.createLabeledComponent(
            'Source', self.__fieldWithButton(self.sourceField, "Pick…", self.onClickedPickSource))
        self.targetSdkField = QLineEdit()
        self.targetSdkField.setReadOnly(True)
        result['targetSdk'] = self.createLabeledComponent('Target SDK', self.targetSdkField)
        self.pdfRef = QLineEdit()
        result['pdfRef'] = self.createLabeledComponent('PDF reference', self.pdfRef)
        self.__applyModelToWidgets()
        return result

    def __fieldWithButton(self, field: QLineEdit, buttonText: str, onClicked):
        container = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)
        layout.addWidget(field, 0, 0, 1, 1)
        layout.setColumnStretch(0, 1)
        button = QPushButton()
        button.setText(buttonText)
        button.clicked.connect(onClicked)
        fieldHeight = field.sizeHint().height()
        button.setStyleSheet("height: %dpx;" % fieldHeight)
        button.setMaximumHeight(fieldHeight)
        layout.addWidget(button, 0, 1, 1, 1)
        return container

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

        self.publishButton = QPushButton()
        self.publishButton.setText("Sign & Publish")
        layout.addWidget(self.publishButton, 0, 1, 1, 1)
        self.publishButton.clicked.connect(self.onClickedPublishButton)
        self.__applyKeyAvailability()

        return result

    def getModel(self):
        return self.dto

    def setModel(self, dto: dict):
        self.dto = dto
        self.__source = None
        self.__className = None
        self.__targetSdkVersion = None
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def __applyModelToWidgets(self):
        if self.title is None:
            return
        dto = self.dto or {}
        self.title.setText(dto.get('title') or "")
        self.codeRef.setText(dto.get('codeRef') or "")
        self.version.setText("")  # a version is always fresh — published rows are immutable
        self.pdfRef.setText(dto.get('pdfRef') or "")
        self.sourceField.setText("")
        self.targetSdkField.setText("")
        # codeRef is read-only only when publishing a NEW VERSION of an existing plugin (inherited identity),
        # NOT because it is a mutable key — a published row is never edited (B4.6).
        self.codeRef.setReadOnly(self.__isNewVersion())
        self.__applyKeyAvailability()

    def __applyKeyAvailability(self):
        # §3 — the private key never leaves the master; with no key, publishing is impossible. Disable the
        # button and say why instead of failing at sign time.
        if self.publishButton is None:
            return
        available = PluginSigner.signingKeyAvailable()
        self.publishButton.setEnabled(available)
        self.publishButton.setToolTip(
            "" if available else "No signing key found (set SPECTRACS_SIGNING_KEY) — cannot publish.")

    def onClickedPickSource(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pick plugin source", "", "Python (*.py)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                source = handle.read()
            derived = inspectPluginSource(source)
        except (OSError, PluginSourceError) as error:
            InWindowDialog.notify(self, "Cannot publish this file", str(error))
            return
        self.__source = source
        self.__className = derived["className"]
        self.__targetSdkVersion = derived["targetSdkVersion"]
        self.sourceField.setText(path)
        self.title.setText(derived["title"])
        self.targetSdkField.setText(str(derived["targetSdkVersion"]))

    def onClickedPublishButton(self):
        if not PluginSigner.signingKeyAvailable():
            InWindowDialog.notify(self, "Cannot publish",
                                  "No signing key found (set SPECTRACS_SIGNING_KEY).")
            return
        codeRef = self.codeRef.text().strip()
        version = self.version.text().strip()
        pdfRef = self.pdfRef.text().strip() or None
        if not self.__source:
            InWindowDialog.notify(self, "Publish failed", "Pick a plugin source file first.")
            return
        if not codeRef or not version:
            InWindowDialog.notify(self, "Publish failed", "Code reference and version are required.")
            return
        if not codeRefMatchesClass(codeRef, self.__className):
            InWindowDialog.notify(self, "Publish failed",
                                  "The code reference must end with the class name '%s'." % self.__className)
            return

        signature, keyId = PluginSigner.sign(codeRef, version, self.__targetSdkVersion, self.__source)
        author = CurrentUserSession().username
        result = SpectracsPyServerClient().savePlugin(
            self.title.text().strip(), codeRef, version, pdfRef, self.__source, signature, keyId,
            author, self.__targetSdkVersion)
        if not result.get('ok'):
            InWindowDialog.notify(self, "Publish failed", result.get('message') or "publish failed")
            return
        self.__navigateToList()

    def __navigateToList(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("PluginListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
