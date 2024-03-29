from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
from typing import List, Dict

import Pyro5.api
import Pyro5.client
import psutil
from sqlalchemy.orm import make_transient

from sciens.spectracs.SpectracsPyServer import SpectracsPyServer
from sciens.spectracs.SqlAlchemySerializer import SqlAlchemySerializer
from sciens.spectracs.logic.base.network.NetworkUtil import NetworkUtil
from sciens.spectracs.logic.model.util.SpectrometerSensorChipUtil import SpectrometerSensorChipUtil
from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.SpectrometerVendorUtil import SpectrometerVendorUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.persistence.database.spectralLineMasterData.PersistSpectralLineMasterDataLogicModule import \
    PersistSpectralLineMasterDataLogicModule
from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer


class SpectracsPyServerClient:


    def getProxy(self):

        SpectracsPyServer.configure()

        port = SpectracsPyServer.NAMESERVER_PORT
        host = SpectracsPyServer.DAEMON_NAT_HOST
        addressUsingPort = NetworkUtil().getAddressUsingPort(port)
        if addressUsingPort is not None:
            host = addressUsingPort.ip

        nameserver = Pyro5.api.locate_ns(host=host,port=port)
        uri = nameserver.lookup("sciens.spectracs.spectracsPyServer")
        result = Pyro5.client.Proxy(uri)

        return result

    def syncSpectrometers(self):
        proxy = self.getProxy()
        remoteSpectrometers: List[Spectrometer] = proxy.getSpectrometers()

        remoteSpectrometers = SpectrometerUtil().getEntitiesByIds(remoteSpectrometers)
        localSpectrometers = SpectrometerUtil().getPersistentSpectrometers()
        localSpectrometers = SpectrometerUtil().getEntitiesByIds(localSpectrometers)
        for spectrometer in remoteSpectrometers.values():
            if spectrometer.id not in localSpectrometers.keys():

                spectrometerVendor = spectrometer.spectrometerVendor
                spectrometerVendorId= spectrometerVendor.id
                spectrometerVendors = SpectrometerVendorUtil().getPersistentSpectrometerVendors()
                localSpectrometerVendor=spectrometerVendors.get(spectrometerVendorId)
                if localSpectrometerVendor is not None:
                    spectrometer.spectrometerVendor=localSpectrometerVendor

                spectrometerStyle = spectrometer.spectrometerStyle
                spectrometerStyleId= spectrometerStyle.id
                spectrometerStyles = SpectrometerStyleUtil().getPersistentSpectrometerStyles()
                localSpectrometerStyle=spectrometerStyles.get(spectrometerStyleId)
                if localSpectrometerStyle is not None:
                    spectrometer.spectrometerStyle=localSpectrometerStyle

                spectrometerSensor = spectrometer.spectrometerSensor
                spectrometerSensorId=spectrometerSensor.id
                spectrometerSensors = SpectrometerSensorUtil().getPersistedSpectrometerSensors()
                localSpectrometerSensor = spectrometerSensors.get(spectrometerSensorId)
                if localSpectrometerSensor is not None:
                    spectrometer.spectrometerSensor=localSpectrometerSensor

                spectrometerSensor = spectrometer.spectrometerSensor
                spectrometerSensorChip = spectrometerSensor.spectrometerSensorChip
                spectrometerSensorChipId=spectrometerSensorChip.id
                spectrometerSensorChips=SpectrometerSensorChipUtil().getPersistentSpectrometerSensorChips()
                localSpectrometerSensorChip = spectrometerSensorChips.get(spectrometerSensorChipId)
                if localSpectrometerSensorChip is not None:
                    spectrometerSensor.spectrometerSensorChip=localSpectrometerSensorChip

                SpectrometerUtil().saveSpectrometer(spectrometer)
                continue

    def syncSpectralLineMasterDatas(self):
        proxy = self.getProxy()
        remoteSpectralLineMasterDatas: Dict[str, Spectrometer] = proxy.getSpectralLineMasterDatasByNames();
        localSpectralLineMasterDatas = SpectralLineMasterDataUtil().getPersistentSpectralLineMasterDatas()

        for remoteSpectralLineMasterData in remoteSpectralLineMasterDatas.values():
            if remoteSpectralLineMasterData.id not in localSpectralLineMasterDatas.keys():
                SpectralLineMasterDataUtil().saveSpectralLineMasterData(remoteSpectralLineMasterData)
        return
