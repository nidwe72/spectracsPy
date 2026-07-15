import Pyro5
from PySide6.QtWidgets import QGridLayout, QFrame

from sciens.spectracs.SqlAlchemySerializer import SqlAlchemySerializer
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerVendor import SpectrometerVendor
from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule

from sciens.spectracs.view.main.MainViewModule import MainViewModule


class MainContainerViewModule(QFrame):

    def __init__(self, *args, docMode=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.syncMasterData()

        layout=QGridLayout()
        self.setLayout(layout)

        self.mainStatusBarViewModule=MainStatusBarViewModule()
        layout.addWidget(self.mainStatusBarViewModule, 0, 0, 1, 1)

        self.mainViewModule = MainViewModule()
        layout.addWidget(self.mainViewModule,1,0,1,1)
        layout.setRowStretch(0,100)

        # --doc-mode only (SPEC_doc_automation): a right-side hint panel (col 1, spanning both rows) driven
        # by an external Director script over UDP, plus the UDP listener itself. Everything is gated on
        # docMode, so the normal app is untouched when the flag is absent.
        self.docHintPanelViewModule = None
        self.docCoverViewModule = None
        self.docModeUdpService = None
        if docMode:
            from sciens.spectracs.view.main.DocHintPanelViewModule import DocHintPanelViewModule
            from sciens.spectracs.view.main.DocCoverViewModule import DocCoverViewModule
            from sciens.spectracs.logic.appliction.docmode.DocModeUdpService import DocModeUdpService
            self.docHintPanelViewModule = DocHintPanelViewModule()
            layout.addWidget(self.docHintPanelViewModule, 0, 1, 2, 1)
            layout.setColumnStretch(0, 100)  # app content keeps (almost) all the width
            # SPEC_doc_automation §18.1 (C1b): the title card is a PAGE in the MainViewModule stack, so making
            # it current both shows the card AND fires the prior view's hideEvent (releases the camera). Added
            # here (not in MainViewModule) so MainViewModule stays flag-agnostic and the app is untouched
            # without --doc-mode.
            self.docCoverViewModule = DocCoverViewModule()
            self.mainViewModule.addWidget(self.docCoverViewModule)
            self.docModeUdpService = DocModeUdpService(self, self.docHintPanelViewModule)


    def __createBootstrapSession(self):
        SpectrometerStyle()
        SpectrometerSensorChip()
        SpectrometerSensor()
        SpectrometerVendor()

        SpectralLineMasterData()

        Spectrometer()
        session = session_factory()
        session.commit()

    def syncMasterData(self):
        self.__createBootstrapSession()
        try:
            SpectracsPyServerClient().syncSpectrometers()
            SpectracsPyServerClient().syncSpectralLineMasterDatas()
        except Exception as exception:
            print("MainContainerViewModule: master-data sync failed, continuing without it (%s)" % exception)






