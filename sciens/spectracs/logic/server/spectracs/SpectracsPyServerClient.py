from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
from typing import List

import Pyro5.api
import Pyro5.client
import psutil

from sciens.spectracs.logic.base.network.NetworkUtil import NetworkUtil
from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.SpectrometerVendorUtil import SpectrometerVendorUtil
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer


class SpectracsPyServerClient:


    def getProxy(self):

        port = 8090
        host='127.0.0.1'
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
                spectrometerStyleStyleId=spectrometerStyle.styleId
                localSpectrometerStyle=SpectrometerStyleUtil().getSpectrometerStyleWithId(spectrometerStyleStyleId)
                if localSpectrometerStyle is not None:
                    spectrometer.spectrometerStyle=localSpectrometerStyle


                SpectrometerUtil().saveSpectrometer(spectrometer)
                continue
