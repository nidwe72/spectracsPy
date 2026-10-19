import base64
import json
import os
import threading
from typing import Optional, Tuple

from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.plugstore.PlugKeyValueStore import PlugKeyValueStore
from sciens.spectracs.logic.plugstore.ShellyGen2PlugStoreTransport import ShellyGen2PlugStoreTransport


class PlugLocator:
    """Find the lamp plug WITHOUT the server and before any login (SPEC_shelly_instrument_memory.md §9.2): offline
    login and the serial pre-fill need it, but LampService only starts after a login. Order: a running LampService,
    then the stored plug (one quick probe), then a full discovery. Returns (LampDevice, password) or (None, None)."""

    def __init__(self, plugStore=None, discovery=None):
        self.plugStore = plugStore
        self.discovery = discovery

    def find(self, discover: bool = True) -> Tuple[Optional[LampDevice], Optional[str]]:
        from sciens.spectracs.logic.lamp.LampService import LampService
        service = LampService.instance
        if service is not None and service.device is not None:
            return service.device, service.plugStore.load()[1]
        store = self.plugStore or self.__defaultStore()
        stored, password = store.load()
        if not discover:
            return stored, password
        override = os.environ.get(LampService.HOST_ENV)
        if override:
            stored = LampDevice("shelly-gen2", override, stored.mac if stored else "", deviceId=None)
        discovery = self.discovery or self.__defaultDiscovery()
        result = discovery.discover(stored=stored if stored and stored.mac else None)
        device = result.chosen
        if device is None:
            return None, None
        if stored is None or device.mac != stored.mac:
            password = None
        store.saveDevice(device)
        return device, password

    @staticmethod
    def storedSerial() -> Optional[str]:
        """The device id of the plug this PC used last (no network) — for the registration pre-fill."""
        try:
            device, _ = PlugLocator.__defaultStore().load()
        except Exception:
            return None
        return device.deviceId if device is not None else None

    @staticmethod
    def __defaultStore():
        from sciens.spectracs.logic.lamp.LampPlugDbStore import LampPlugDbStore
        return LampPlugDbStore()

    @staticmethod
    def __defaultDiscovery():
        from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
        return LampDiscovery()


class PlugInstrumentMemory:
    """The instrument's data on its plug (SPEC_shelly_instrument_memory.md §4.6/§4.7), over PlugKeyValueStore:

        copy       bytes   the server's bz2-compressed SQLite copy (setup + users)        → script slot
        sig_copy   text    its server signature (88 chars)                               → native KVS
        plugin     bytes   the plugin bundle, master-signed, bz2 (PluginBundleUtil.pack)  → script slot(s)
        plugin_id  text    {"codeRef", "version"} of that bundle                          → native KVS
        index      text    {"v", "revision", "sha256", "keyId"} — written LAST            → native KVS

    The index names the copy's sha256 ⇒ a copy without a matching index is never used, and an unchanged copy is
    never rewritten (one KVS.Get per online login, §9.5)."""

    VERSION = 1

    def __init__(self, store: PlugKeyValueStore):
        self.store = store

    @staticmethod
    def forDevice(device: LampDevice, password: Optional[str]) -> "PlugInstrumentMemory":
        return PlugInstrumentMemory(PlugKeyValueStore(ShellyGen2PlugStoreTransport(device.host, password=password)))

    # --- the copy ---
    def index(self) -> Optional[dict]:
        raw = self.store.get("index")
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return None

    def writeCopy(self, entry: dict) -> bool:
        """Write the server's copy entry {data, sha256, revision, signature, keyId}. False = unchanged, not written."""
        current = self.index()
        if current is not None and current.get("sha256") == entry["sha256"]:
            return False
        self.store.set("copy", base64.b64decode(entry["data"]))
        self.store.set("sig_copy", entry["signature"])
        self.store.set("index", json.dumps({"v": self.VERSION, "revision": entry["revision"],
                                            "sha256": entry["sha256"], "keyId": entry["keyId"]},
                                           separators=(",", ":")))
        return True

    def readCopyEntry(self) -> Optional[dict]:
        """The entry shape InstrumentCopyReader.read expects, or None if the plug holds no (complete) copy."""
        index = self.index()
        if index is None or index.get("v") != self.VERSION:
            return None
        data = self.store.get("copy")
        signature = self.store.get("sig_copy")
        if not isinstance(data, bytes) or not signature:
            return None
        return {"data": base64.b64encode(data).decode("ascii"), "sha256": index["sha256"],
                "revision": index.get("revision"), "signature": signature, "keyId": index.get("keyId")}

    # --- the plugin ---
    def writePlugin(self, packed: bytes, codeRef: str, version: str):
        self.store.delete("plugin_id")
        self.store.set("plugin", packed, replaceInPlace=True)        # the factory tool can always write again
        self.store.set("plugin_id", json.dumps({"codeRef": codeRef, "version": version}, separators=(",", ":")))

    def pluginId(self) -> Optional[dict]:
        raw = self.store.get("plugin_id")
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return None

    def readPluginEnvelope(self, codeRef: str, version: str) -> Optional[dict]:
        identity = self.pluginId()
        if identity is None or (identity.get("codeRef"), identity.get("version")) != (codeRef, version):
            return None
        packed = self.store.get("plugin")
        if not isinstance(packed, bytes):
            return None
        from sciens.spectracs.logic.security.PluginBundleUtil import unpack
        return unpack(packed)

    def clear(self):
        for key in ("index", "plugin_id", "sig_copy", "copy", "plugin"):
            self.store.delete(key)


class OfflineLoginLogicModule:
    """S7 (SPEC_shelly_instrument_memory.md §9): log in from the plug when the server is unreachable. Produces the
    SAME dict as the server's LoginLogicModule.login (plus "offline": True and the bundle for the profile install),
    so everything after login reads CurrentUserSession unchanged. Messages stay as generic as online."""

    NO_PLUG = "Server not reachable, and no instrument plug found."
    NO_COPY = "Server not reachable, and the instrument plug holds no instrument data."

    def __init__(self, locator: PlugLocator = None, memoryFactory=None, trustedKeys: dict = None):
        self.locator = locator or PlugLocator()
        self.memoryFactory = memoryFactory or PlugInstrumentMemory.forDevice
        self.trustedKeys = trustedKeys

    def login(self, username: str, password: str) -> dict:
        from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader, InstrumentCopyRefused
        from sciens.spectracs.logic.user.PasswordUtil import PasswordUtil
        try:
            device, plugPassword = self.locator.find()
        except Exception as error:
            print("OfflineLogin: plug lookup failed (%s)" % error)
            device, plugPassword = None, None
        if device is None or not device.deviceId:
            return self.__failed(self.NO_PLUG)
        try:
            memory = self.memoryFactory(device, plugPassword)
            entry = memory.readCopyEntry()
        except Exception as error:
            print("OfflineLogin: reading the plug failed (%s)" % error)
            return self.__failed(self.NO_COPY)
        if entry is None:
            return self.__failed(self.NO_COPY)
        trusted = self.trustedKeys
        if trusted is None:
            from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_COPY_KEYS as trusted
        try:
            copy = InstrumentCopyReader().read(entry, device.deviceId, trusted)
        except InstrumentCopyRefused as refused:
            return self.__failed(refused.reason)

        user = next((u for u in copy.users if u.username == username), None)
        if user is None or not user.enabled or not PasswordUtil().verify(password, user.passwordHash):
            return self.__failed("invalid credentials")

        bundle = copy.bundle
        ok = bool(bundle.get("ok"))
        self.__installPluginSource(memory)
        return {"ok": True, "userId": user.userId, "username": user.username, "roles": user.roles,
                "registeredSerial": copy.serial,
                "pluginCodeRef": bundle.get("pluginCodeRef") if ok else None,
                "pluginVersion": bundle.get("pluginVersion") if ok else None,
                "spectrometerDevice": bundle.get("deviceCodeName") if ok else None,
                "calibration": bundle.get("calibration") if ok else None,
                "offline": True, "offlineBundle": bundle, "message": None}

    @staticmethod
    def __installPluginSource(memory):
        # A sealed plugin version the server cannot deliver now comes from the plug's bundle (S3b), read once.
        from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
        cache = {}

        def source(codeRef, version):
            key = (codeRef, version)
            if key not in cache:
                try:
                    cache[key] = memory.readPluginEnvelope(codeRef, version)
                except Exception as error:
                    print("OfflineLogin: plugin bundle unreadable (%s)" % error)
                    cache[key] = None
            return cache[key]

        PluginRegistry.offlineBundleSource = staticmethod(source)

    @staticmethod
    def __failed(message):
        return {"ok": False, "userId": None, "username": None, "roles": [], "registeredSerial": None,
                "pluginCodeRef": None, "pluginVersion": None, "spectrometerDevice": None, "calibration": None,
                "message": message}


class PlugInstrumentSync:
    """S6 (SPEC_shelly_instrument_memory.md §9.5): after an ONLINE login on a box, bring the plug's copy up to date —
    written only when the server's copy differs (one KVS.Get otherwise). Runs off the GUI thread; never fails the
    login, it only prints."""

    def __init__(self, locator: PlugLocator = None, memoryFactory=None, client=None):
        self.locator = locator or PlugLocator()
        self.memoryFactory = memoryFactory or PlugInstrumentMemory.forDevice
        self.client = client

    def afterOnlineLogin(self, username: str, password: str, serial: Optional[str], background: bool = True):
        if not serial:
            return None
        if background:
            thread = threading.Thread(target=self.sync, args=(username, password, serial), daemon=True,
                                      name="PlugInstrumentSync")
            thread.start()
            return thread
        return self.sync(username, password, serial)

    def sync(self, username, password, serial) -> str:
        try:
            device, plugPassword = self.locator.find(discover=True)
            if device is None or device.deviceId != serial:
                return "no plug for %s" % serial                  # a master on a desk PC, or another box
            client = self.client
            if client is None:
                from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
                client = SpectracsPyServerClient()
            entry = client.getInstrumentCopy(username, password, serial)
            if not entry or not entry.get("ok"):
                return "no copy: %s" % (entry or {}).get("message")
            written = self.memoryFactory(device, plugPassword).writeCopy(entry)
            result = "written" if written else "unchanged"
        except Exception as error:
            result = "failed: %s" % error
        print("PlugInstrumentSync: %s" % result)
        return result
