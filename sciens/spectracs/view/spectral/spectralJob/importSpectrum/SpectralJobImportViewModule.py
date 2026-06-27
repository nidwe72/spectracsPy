from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QFileDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal

from sciens.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModuleParameters import ImportSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModule import ImportSpectrumLogicModule


class SpectralJobImportViewModule(QWidget):

    videoThread=None
    videoWidget=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        # NOTE: the former QtCharts preview chart here was never added to the
        # layout (the addWidget call was commented out), so it rendered nothing.
        # Removed with the QtCharts migration (docs/SPEC_pyside6_and_android.md).

        importButton = QPushButton()
        importButton.setText("Open file")
        layout.addWidget(importButton, 1, 0, 1, 1)
        importButton.clicked.connect(self.onClickedImportButton)

        backButton = QPushButton()
        backButton.setText("back")
        layout.addWidget(backButton, 1, 1, 1, 1)

        backButton.clicked.connect(self.onClickedBackButton)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJob")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedImportButton(self):
        filepath = self.getFilepathByDialog()
        importSpectrumLogicModuleParameters = ImportSpectrumLogicModuleParameters()
        importSpectrumLogicModuleParameters.setFilepath(filepath)

        importSpectrumLogicModule = ImportSpectrumLogicModule()
        importSpectrumLogicModule.importSpectrum(importSpectrumLogicModuleParameters)

        print(filepath)

    def getFilepathByDialog(self):
        result = None
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        # dlg.setFilter("Text files (*.txt)")

        if dlg.exec():
            filenames = dlg.selectedFiles()
            result = filenames[0]
        return result







