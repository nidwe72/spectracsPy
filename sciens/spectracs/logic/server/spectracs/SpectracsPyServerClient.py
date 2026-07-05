from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
from typing import List, Dict

import Pyro5.api
import Pyro5.client
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

        # Bound the per-attempt wait so an unreachable host cannot hang startup.
        Pyro5.config.COMMTIMEOUT = 5.0

        # 1) Two-app on-device path (P6): connect straight to the local server APK's fixed-URI
        # daemon — no nameserver (Pyro's UDP discovery doesn't cross Android sandboxes). On the
        # phone this is the only server; on desktop it's a fast no-op when nothing is listening.
        try:
            localProxy = Pyro5.client.Proxy(SpectracsPyServer.localUri())
            localProxy._pyroBind()  # force a connection so we fail fast if nothing is listening
            return localProxy
        except Exception:
            pass

        port = SpectracsPyServer.NAMESERVER_PORT

        # 2) Otherwise: local dev nameserver (if listening on this machine's port), then the remote
        # (sciens.at) server. If neither is reachable, return None so sync is skipped, not crashed.
        candidateHosts = []
        addressUsingPort = NetworkUtil().getAddressUsingPort(port)
        if addressUsingPort is not None:
            candidateHosts.append(addressUsingPort.ip)
        candidateHosts.append(SpectracsPyServer.DAEMON_NAT_HOST)

        # Bound the per-attempt wait so an unreachable remote host cannot hang startup.
        Pyro5.config.COMMTIMEOUT = 5.0

        for host in candidateHosts:
            try:
                nameserver = Pyro5.api.locate_ns(host=host, port=port)
                uri = nameserver.lookup("sciens.spectracs.spectracsPyServer")
                return Pyro5.client.Proxy(uri)
            except Exception as exception:
                print("SpectracsPyServerClient: could not reach server at %s:%s (%s)" % (host, port, exception))
                continue

        print("SpectracsPyServerClient: no spectracs server reachable; skipping sync")
        return None

    def login(self, username, password):
        # Returns a plain dict {ok, userId, username, roles, message}. Never raises to the caller.
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "userId": None, "username": None, "roles": [], "message": "server unavailable"}
        try:
            return proxy.login(username, password)
        except Exception as exception:
            print("SpectracsPyServerClient.login failed: %s" % exception)
            return {"ok": False, "userId": None, "username": None, "roles": [], "message": "login failed"}

    def listUsers(self):
        # Returns a list of plain user DTOs, or None when the server is unreachable
        # (the None sentinel lets the UI distinguish "server unavailable" from "no users").
        proxy = self.getProxy()
        if proxy is None:
            return None
        try:
            return proxy.listUsers()
        except Exception as exception:
            print("SpectracsPyServerClient.listUsers failed: %s" % exception)
            return None

    def createUser(self, username, password, displayName, enabled, roleName):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "userId": None, "message": "server unavailable"}
        try:
            return proxy.createUser(username, password, displayName, enabled, roleName)
        except Exception as exception:
            print("SpectracsPyServerClient.createUser failed: %s" % exception)
            return {"ok": False, "userId": None, "message": "create failed"}

    def updateUser(self, userId, displayName, enabled, roleName, newPassword):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "userId": None, "message": "server unavailable"}
        try:
            return proxy.updateUser(userId, displayName, enabled, roleName, newPassword)
        except Exception as exception:
            print("SpectracsPyServerClient.updateUser failed: %s" % exception)
            return {"ok": False, "userId": None, "message": "update failed"}

    def deleteUser(self, userId):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "userId": None, "message": "server unavailable"}
        try:
            return proxy.deleteUser(userId)
        except Exception as exception:
            print("SpectracsPyServerClient.deleteUser failed: %s" % exception)
            return {"ok": False, "userId": None, "message": "delete failed"}

    # --- connection & calibration (SPEC_connection_and_calibration_ux.md §4) ---

    def resolveInstrumentBySerial(self, serial):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "message": "server unavailable"}
        try:
            return proxy.resolveInstrumentBySerial(serial)
        except Exception as exception:
            print("SpectracsPyServerClient.resolveInstrumentBySerial failed: %s" % exception)
            return {"ok": False, "message": "failed"}

    def registerEndUser(self, username, password, email, firstName, lastName, serial):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "message": "server unavailable"}
        try:
            return proxy.registerEndUser(username, password, email, firstName, lastName, serial)
        except Exception as exception:
            print("SpectracsPyServerClient.registerEndUser failed: %s" % exception)
            return {"ok": False, "message": "failed"}

    def listPlugins(self):
        proxy = self.getProxy()
        if proxy is None:
            return []
        try:
            return proxy.listPlugins()
        except Exception as exception:
            print("SpectracsPyServerClient.listPlugins failed: %s" % exception)
            return []

    def savePlugin(self, title, codeRef, version, pdfRef=None):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "message": "server unavailable"}
        try:
            return proxy.savePlugin(title, codeRef, version, pdfRef)
        except Exception as exception:
            print("SpectracsPyServerClient.savePlugin failed: %s" % exception)
            return {"ok": False, "message": "failed"}

    def saveSpectrometerProfile(self, serial, deviceCodeName, calibration=None):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "message": "server unavailable"}
        try:
            return proxy.saveSpectrometerProfile(serial, deviceCodeName, calibration)
        except Exception as exception:
            print("SpectracsPyServerClient.saveSpectrometerProfile failed: %s" % exception)
            return {"ok": False, "message": "failed"}

    def saveSpectrometerSetup(self, serial, pluginCodeRef):
        proxy = self.getProxy()
        if proxy is None:
            return {"ok": False, "message": "server unavailable"}
        try:
            return proxy.saveSpectrometerSetup(serial, pluginCodeRef)
        except Exception as exception:
            print("SpectracsPyServerClient.saveSpectrometerSetup failed: %s" % exception)
            return {"ok": False, "message": "failed"}

    def listSpectrometerProfiles(self):
        proxy = self.getProxy()
        if proxy is None:
            return []
        try:
            return proxy.listSpectrometerProfiles()
        except Exception as exception:
            print("SpectracsPyServerClient.listSpectrometerProfiles failed: %s" % exception)
            return []

    def listSpectrometerSetups(self):
        proxy = self.getProxy()
        if proxy is None:
            return []
        try:
            return proxy.listSpectrometerSetups()
        except Exception as exception:
            print("SpectracsPyServerClient.listSpectrometerSetups failed: %s" % exception)
            return []

    def syncSpectrometers(self):
        proxy = self.getProxy()
        if proxy is None:
            return
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
        if proxy is None:
            return
        remoteSpectralLineMasterDatas: Dict[str, Spectrometer] = proxy.getSpectralLineMasterDatasByNames();
        localSpectralLineMasterDatas = SpectralLineMasterDataUtil().getPersistentSpectralLineMasterDatas()

        for remoteSpectralLineMasterData in remoteSpectralLineMasterDatas.values():
            if remoteSpectralLineMasterData.id not in localSpectralLineMasterDatas.keys():
                SpectralLineMasterDataUtil().saveSpectralLineMasterData(remoteSpectralLineMasterData)
        return
