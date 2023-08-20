import Pyro5
from PySide6.QtWidgets import QGridLayout, QFrame

from sciens.spectracs.SqlAlchemySerializer import SqlAlchemySerializer
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerVendor import SpectrometerVendor
from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule

from sciens.spectracs.view.main.MainViewModule import MainViewModule


class MainContainerViewModule(QFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.syncMasterData()

        layout=QGridLayout()
        self.setLayout(layout)

        self.mainStatusBarViewModule=MainStatusBarViewModule()
        layout.addWidget(self.mainStatusBarViewModule, 0, 0, 1, 1)

        self.mainViewModule = MainViewModule()
        layout.addWidget(self.mainViewModule,1,0,1,1)
        layout.setRowStretch(0,100)


    def __createBootstrapSession(self):
        SpectrometerStyle()
        SpectrometerSensorChip()
        SpectrometerSensor()
        SpectrometerVendor()

        Spectrometer()
        session = session_factory()
        session.commit()

        className='sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer-Spectrometer'
        Pyro5.serializers.SerializerBase.register_dict_to_class(className, SqlAlchemySerializer.dictToClass)


    def syncMasterData(self):
        self.__createBootstrapSession()
        SpectracsPyServerClient().syncSpectrometers()




