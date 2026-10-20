import base64
import json
import os
import threading
from typing import List, Optional, Tuple

from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.plugstore.PlugKeyValueStore import PlugKeyValueStore
from sciens.spectracs.logic.plugstore.ShellyGen2PlugStoreTransport import ShellyGen2PlugStoreTransport


class PlugLocator:
    """Find instrument plugs WITHOUT the server and before any login (SPEC_shelly_instrument_memory.md §9.2, §11.3):
    offline login, the sync after login, the factory pages. Never "the first plug found" (R25):

        find(serial)          the REGISTERED plug (●) of `serial` — or, without a serial, the first registered one
        registeredPlugs()     every registered plug in reach (offline login picks by the user, two rigs in one room)
        findBySerial(serial)  the plug whose id IS `serial`, whatever its label (the sync / auto-repair, §11.7: the
                              online login has just confirmed that serial with the server, R22)
        candidates()          every plug, labelled ● ◐ 🔒 ○ (the pickers)

    `find` / `registeredPlugs` return (LampDevice, password); the others PlugCandidate(s)."""

    def __init__(self, plugStore=None, discovery=None, registry=None):
        self.plugStore = plugStore
        self.discovery = discovery
        self.registry = registry

    def find(self, serial: Optional[str] = None, discover: bool = True) -> Tuple[Optional[LampDevice], Optional[str]]:
        from sciens.spectracs.logic.lamp.LampService import LampService
        service = LampService.instance
        if service is not None and service.switch is not None and service.device is not None \
                and (serial is None or service.device.deviceId == serial):
            return service.device, service.plugStore.load(mac=service.device.mac)[1] or \
                (service.device.mac if service.device.authRequired else None)
        if not discover:
            return self.__store().load(deviceId=serial) if serial else self.__store().load()
        if serial is not None:
            candidate = self.findBySerial(serial)
            return (candidate.device, candidate.password) if candidate is not None and candidate.isRegistered \
                else (None, None)
        plugs = self.registeredPlugs()
        return plugs[0] if plugs else (None, None)

    def registeredPlugs(self) -> List[Tuple[LampDevice, Optional[str]]]:
        return [(c.device, c.password) for c in self.candidates() if c.isRegistered]

    def findBySerial(self, serial: str):
        stored, _ = self.__store().load(deviceId=serial)
        result = self.__discovery().discover(stored=stored, wantedId=serial)
        device = result.chosen
        if device is None:
            return None
        self.__store().saveDevice(device)
        return self.__registry().classify(device)

    def candidates(self) -> list:
        result = self.__discovery().discoverAll()
        return self.__registry().classifyAll(result.devices)

    @staticmethod
    def storedSerial() -> Optional[str]:
        """The device id of a plug this PC has used (no network) — for the registration pre-fill."""
        try:
            device, _ = PlugLocator.__defaultStore().load()
        except Exception:
            return None
        return device.deviceId if device is not None else None

    # --- helpers ---
    def __store(self):
        if self.plugStore is None:
            self.plugStore = self.__defaultStore()
        return self.plugStore

    def __discovery(self):
        if self.discovery is None:
            from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
            from sciens.spectracs.logic.lamp.LampService import LampService
            host = os.environ.get(LampService.HOST_ENV)
            self.discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: [host], subnetHosts=lambda: []) \
                if host else LampDiscovery()
        return self.discovery

    def __registry(self):
        if self.registry is None:
            from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
            self.registry = PlugRegistry(store=self.__store())
        return self.registry

    @staticmethod
    def __defaultStore():
        from sciens.spectracs.logic.lamp.LampPlugDbStore import LampPlugDbStore
        return LampPlugDbStore()


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
        return PlugInstrumentMemory(PlugKeyValueStore(ShellyGen2PlugStoreTransport(device.host, password=password),
                                                      writePiece=PlugKeyValueStore.writePieceFor(device.firmware)))

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
        # Every REGISTERED plug in reach (§11.3) — two rigs in one room each carry their own users (E16), so the plug
        # is the one whose copy holds this user. A plug that cannot be read or verified is skipped, never trusted.
        try:
            plugs = self.locator.registeredPlugs() if hasattr(self.locator, "registeredPlugs") \
                else [self.locator.find()]
        except Exception as error:
            print("OfflineLogin: plug lookup failed (%s)" % error)
            plugs = []
        plugs = [(device, plugPassword) for device, plugPassword in plugs if device is not None and device.deviceId]
        if not plugs:
            return self.__failed(self.NO_PLUG)
        failure = self.NO_COPY
        for device, plugPassword in plugs:
            result = self.__loginOn(device, plugPassword, username, password)
            if isinstance(result, dict):
                return result
            if failure == self.NO_COPY or result == "invalid credentials":
                failure = result
        return self.__failed(failure)

    def __loginOn(self, device, plugPassword, username, password):
        """The login dict, or the reason this plug did not let the user in."""
        from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader, InstrumentCopyRefused
        from sciens.spectracs.logic.user.PasswordUtil import PasswordUtil
        try:
            memory = self.memoryFactory(device, plugPassword)
            entry = memory.readCopyEntry()
        except Exception as error:
            print("OfflineLogin: reading the plug failed (%s)" % error)
            return self.NO_COPY
        if entry is None:
            return self.NO_COPY
        trusted = self.trustedKeys
        if trusted is None:
            from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_COPY_KEYS as trusted
        try:
            copy = InstrumentCopyReader().read(entry, device.deviceId, trusted)
        except InstrumentCopyRefused as refused:
            return refused.reason

        user = next((u for u in copy.users if u.username == username), None)
        if user is None or not user.enabled or not PasswordUtil().verify(password, user.passwordHash):
            return "invalid credentials"

        bundle = copy.bundle
        ok = bool(bundle.get("ok"))
        self.__installPluginSource(memory)
        return {"ok": True, "userId": user.userId, "username": user.username, "roles": user.roles,
                "registeredSerial": copy.serial,
                "pluginCodeRef": bundle.get("pluginCodeRef") if ok else None,
                "pluginVersion": bundle.get("pluginVersion") if ok else None,
                "spectrometerDevice": bundle.get("deviceCodeName") if ok else None,
                "lightSourceController": bundle.get("lightSourceController") if ok else None,
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
    """S6 + L5 (SPEC_shelly_instrument_memory.md §9.5, §11.7): after an ONLINE login, bring the user's own plug up to
    date — and repair it after a factory reset, on ANY PC:

      - the plug is found BY the user's serial (never "the first plug", R25) — the login has just confirmed that
        serial with the server, so this is the instrument's plug whatever it holds now (R22/R44);
      - the copy is written only when the server's differs (one KVS.Get otherwise, §9.5); a plug that held none
        (reset, or new) gets copy + plugin: "restored";
      - a plug without a password is hardened with the default, its MAC (E11) — no secret needed, so any PC can;
      - a plug whose password this PC does not know is left alone ("locked", R19).

    Runs off the GUI thread; never fails the login. `onResult(text)` (if given) gets the one-line result."""

    def __init__(self, locator: PlugLocator = None, memoryFactory=None, client=None, factory=None):
        self.locator = locator or PlugLocator()
        self.memoryFactory = memoryFactory or PlugInstrumentMemory.forDevice
        self.client = client
        self.factory = factory

    def afterOnlineLogin(self, username: str, password: str, serial: Optional[str], background: bool = True,
                         onResult=None):
        if not serial:
            return None
        if background:
            thread = threading.Thread(target=self.sync, args=(username, password, serial, onResult), daemon=True,
                                      name="PlugInstrumentSync")
            thread.start()
            return thread
        return self.sync(username, password, serial, onResult)

    def sync(self, username, password, serial, onResult=None) -> str:
        try:
            result = self.__sync(username, password, serial)
        except Exception as error:
            result = "failed: %s" % error
        print("PlugInstrumentSync: %s" % result)
        if onResult is not None:
            try:
                onResult(result)
            except Exception:
                pass
        return result

    def __sync(self, username, password, serial):
        candidate = self.locator.findBySerial(serial)
        if candidate is None:
            return "no plug for %s" % serial                       # a master on a desk PC, or another box
        if candidate.label == "locked":
            return "plug of %s is locked — enter its password in Settings → Lamp" % serial
        device, plugPassword = candidate.device, candidate.password
        client = self.client
        if client is None:
            from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
            client = SpectracsPyServerClient()
        factory = self.factory
        if factory is None:
            from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import \
                InstrumentFactoryLogicModule
            factory = InstrumentFactoryLogicModule(client=client, memoryFactory=self.memoryFactory)
        if candidate.isRegistered:
            entry = client.getInstrumentCopy(username, password, serial)
            if not entry or not entry.get("ok"):
                return "no copy: %s" % (entry or {}).get("message")
            written = self.memoryFactory(device, plugPassword).writeCopy(entry)
            if written:
                from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
                PlugRegistry.forget(device.mac)
            result = "written" if written else "unchanged"
        else:
            text = factory.write(device, plugPassword, username, password)       # copy + plugin, as the factory
            if not text.startswith("✓"):
                return "not restored: %s" % text.lstrip("✗ ")
            result = "restored"
        if not device.authRequired:
            hardened = factory.harden(device, None)
            result += ", hardened" if hardened.startswith("✓") else ", not hardened (%s)" % hardened.lstrip("✗ ")
        return result
