import hashlib
import os
from typing import Optional

from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugInstrumentMemory
from sciens.spectracs.logic.lamp.ShellyHttp import ShellyHttp


class InstrumentFactoryLogicModule:
    """The factory tool's steps (SPEC_shelly_instrument_memory.md §5, S5/S8), Qt-free so they run headless in tests.
    Every step returns a short human-readable result line; none raises to the page.

        harden        standard password (P7) + output off after a power cut
        createOnServer profile (serial = plug id, device code name) + setup (plugin)
        write         the server-signed copy (+ a sealed plugin as a master-signed bundle) onto the plug
        verify        read everything back exactly as an offline login would
        moveHere      a replaced plug: move the instrument's serial to this plug, then write
    """

    STANDARD_PASSWORD_ENV = "SPECTRACS_PLUG_STANDARD_PASSWORD"
    STANDARD_PASSWORD_FILE = "../spectracs-keys/plugStandardPassword.txt"     # outside every repo (R3)

    def __init__(self, client=None, memoryFactory=None, plugStore=None):
        self.client = client
        self.memoryFactory = memoryFactory or PlugInstrumentMemory.forDevice
        self.plugStore = plugStore

    # --- P7: the standard password --------------------------------------------------------------------
    @classmethod
    def standardPassword(cls) -> Optional[str]:
        value = os.environ.get(cls.STANDARD_PASSWORD_ENV)
        if value:
            return value
        path = os.environ.get(cls.STANDARD_PASSWORD_ENV + "_FILE", cls.STANDARD_PASSWORD_FILE)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read().strip() or None
        return None

    def harden(self, device, currentPassword: Optional[str]) -> str:
        password = self.standardPassword()
        if not password:
            return "✗ No standard plug password configured (%s or %s)." % (self.STANDARD_PASSWORD_ENV,
                                                                          self.STANDARD_PASSWORD_FILE)
        http = ShellyHttp(device.host, password=currentPassword, timeout=5.0)
        try:
            http.post("Switch.SetConfig", id=0, config={"initial_state": "off"})
            realm = device.deviceId
            ha1 = hashlib.sha256(("admin:%s:%s" % (realm, password)).encode()).hexdigest()
            http.post("Shelly.SetAuth", user="admin", realm=realm, ha1=ha1)
        except Exception as error:
            return "✗ Hardening failed: %s" % error
        from sciens.spectracs.logic.lamp.LampService import LampService
        if self.plugStore is None and LampService.instance is not None:
            LampService.instance.setPassword(password)      # rebuilds the lamp switch with the new password
        else:
            self.__store().savePassword(password)
        return "✓ Plug hardened: standard password set, output stays off after a power cut."

    # --- server ------------------------------------------------------------------------------------------
    def createOnServer(self, serial: str, modelName: str, deviceCodeName: str, styleId: str, pluginCodeRef: str,
                       pluginVersion: str) -> str:
        """The spectrometer is the triple (model name, camera, style) — a camera can sit in different spectrometers;
        the server creates the spectrometer row when the combination is new."""
        client = self.__client()
        profile = client.saveSpectrometerProfile(serial, deviceCodeName, None, modelName, styleId)
        if not profile or not profile.get("ok"):
            return "✗ Profile not created: %s" % (profile or {}).get("message")
        setup = client.saveSpectrometerSetup(serial, pluginCodeRef, pluginVersion)
        if not setup or not setup.get("ok"):
            return "✗ Setup not created: %s" % (setup or {}).get("message")
        return "✓ Instrument %s on the server: %s-%s-%s%s, plugin %s %s." % (
            serial, modelName, deviceCodeName, styleId, " (new spectrometer)" if profile.get("spectrometerCreated") else "",
            pluginCodeRef.rsplit(".", 1)[-1], pluginVersion or "")

    # --- plug --------------------------------------------------------------------------------------------
    def write(self, device, plugPassword, username: str, password: str, force: bool = False) -> str:
        serial = device.deviceId
        entry = self.__client().getInstrumentCopy(username, password, serial)
        if not entry or not entry.get("ok"):
            return "✗ No instrument data from the server: %s" % (entry or {}).get("message")
        memory = self.memoryFactory(device, plugPassword)
        try:
            if force:
                memory.store.delete("index")
            written = memory.writeCopy(entry)
            lines = ["✓ Instrument data %s (%d bytes)." % ("written" if written else "unchanged",
                                                         len(entry["data"]) * 3 // 4)]
            lines.append(self.__writePlugin(memory, entry))
        except Exception as error:
            return "✗ Writing the plug failed: %s" % error
        return "\n".join(lines)

    def __writePlugin(self, memory, entry) -> str:
        from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader
        from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_COPY_KEYS
        bundle = InstrumentCopyReader().read(entry, entry["serial"], TRUSTED_COPY_KEYS).bundle
        codeRef, version = bundle.get("pluginCodeRef"), bundle.get("pluginVersion")
        if not codeRef:
            return "· No plugin bound to this instrument."
        row = self.__client().getPluginSource(codeRef, version) if version else None
        if not row or not row.get("ok") or not row.get("source"):
            memory.store.delete("plugin_id")
            memory.store.delete("plugin")
            return "· Plugin %s ships with the app — nothing to store." % codeRef.rsplit(".", 1)[-1]
        from sciens.spectracs.logic.security.PluginSigner import signingKeyAvailable
        if not signingKeyAvailable():
            return "✗ Plugin not stored: no master signing key on this computer."
        from sciens.spectracs.logic.spectral.plugin.PluginBundle import PluginBundleBuilder
        packed = PluginBundleBuilder.packSigned(PluginBundleBuilder.forSealedRow(row))
        memory.writePlugin(packed, codeRef, version)
        return "✓ Plugin %s %s stored (%d bytes)." % (codeRef.rsplit(".", 1)[-1], version, len(packed))

    def verify(self, device, plugPassword) -> str:
        from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader, InstrumentCopyRefused
        from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_COPY_KEYS
        try:
            memory = self.memoryFactory(device, plugPassword)
            entry = memory.readCopyEntry()
            if entry is None:
                return "✗ The plug holds no instrument data."
            copy = InstrumentCopyReader().read(entry, device.deviceId, TRUSTED_COPY_KEYS)
        except InstrumentCopyRefused as refused:
            return "✗ " + refused.reason
        except Exception as error:
            return "✗ Reading the plug failed: %s" % error
        bundle = copy.bundle
        lines = ["✓ Instrument data valid: %s · %s · %d user(s) for offline login." % (
            copy.serial, bundle.get("deviceCodeName"), len(copy.users))]
        identity = memory.pluginId()
        if identity:
            envelope = memory.readPluginEnvelope(identity["codeRef"], identity["version"])
            from sciens.spectracs.logic.security import PluginBundleUtil
            from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_KEYS
            ok = envelope is not None and PluginBundleUtil.verify(envelope["bundle"], envelope.get("signature"),
                                                                  envelope.get("keyId"), TRUSTED_KEYS)
            lines.append(("✓" if ok else "✗") + " Plugin %s %s %s." % (
                identity["codeRef"].rsplit(".", 1)[-1], identity["version"], "valid" if ok else "NOT valid"))
        return "\n".join(lines)

    def moveHere(self, device, plugPassword, oldSerial: str, username: str, password: str) -> str:
        result = self.__client().moveInstrumentToSerial(oldSerial, device.deviceId)
        if not result or not result.get("ok"):
            return "✗ Not moved: %s" % (result or {}).get("message")
        return "✓ Instrument moved from %s to this plug.\n%s" % (
            oldSerial, self.write(device, plugPassword, username, password, force=True))

    # --- helpers -----------------------------------------------------------------------------------------
    def __client(self):
        if self.client is None:
            from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
            self.client = SpectracsPyServerClient()
        return self.client

    def __store(self):
        if self.plugStore is None:
            from sciens.spectracs.logic.lamp.LampPlugDbStore import LampPlugDbStore
            self.plugStore = LampPlugDbStore()
        return self.plugStore
