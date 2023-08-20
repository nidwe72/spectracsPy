from typing import List

import Pyro5.api
import Pyro5.client

from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer


class SpectracsPyServerClient:

    def getProxy(self):
        host = "192.168.8.111"
        port = 8090
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
        for spectrometer in remoteSpectrometers:
            if spectrometer.id not in localSpectrometers.keys():
                SpectrometerUtil.saveSpectrometer(spectrometer)
                continue
