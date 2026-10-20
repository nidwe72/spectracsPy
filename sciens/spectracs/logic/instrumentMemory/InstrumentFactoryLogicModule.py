import hashlib
import time
from typing import Optional

from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugInstrumentMemory
from sciens.spectracs.logic.lamp.ShellyHttp import ShellyHttp


class InstrumentFactoryLogicModule:
    """The factory tool's steps (SPEC_shelly_instrument_memory.md §5, §11), Qt-free so they run headless in tests.
    Every step returns a short human-readable result line; none raises to the page.

        updateFirmware      Shelly OTA in hops up to the TESTED target, never beyond (§11.16, F1b)
        harden              API + AP password = the MAC (E11/E12), output off after a power cut; Bluetooth stays on
        changePassword      a user's own password for API + AP (C3, R45) — AP first, then the API, then stored
        prepareForShipping  passwords back to the MAC, then the factory WLAN forgotten (E14, R41/R42/R48)
        identify            a short LED blink (R24) — never the relay
        write               the server-signed copy (+ a sealed plugin as a master-signed bundle) onto the plug
        verify              read everything back exactly as an offline login would
        moveHere            a replaced plug: move the instrument's serial to this plug, then write
    The instrument itself (profile + setup) is created on the Spectrometer setup page (E3/E4)."""

    # §11.16 (Edwin, 2026-10-20): the firmware our code is tested on. The update goes up to it and stops; a plug that
    # is offered something NEWER is not updated (raise this only after a test run on that version).
    TARGET_FIRMWARE = "1.7.5"
    UPDATE_REBOOT_SECONDS = 300.0            # one hop: download + flash + reboot (measured ~1–2 min)
    UPDATE_MAX_HOPS = 4

    MIN_PASSWORD_LENGTH = 8                  # WPA needs ≥ 8 characters, and the AP shares the password (E12, R20)
    SHIPPING_GONE_SECONDS = 15.0             # R42: the plug must have left the LAN within this
    IDENTIFY_CYCLES = 4
    IDENTIFY_HALF_PERIOD = 0.6

    def __init__(self, client=None, memoryFactory=None, plugStore=None, sleep=None, clock=None):
        self.client = client
        self.memoryFactory = memoryFactory or PlugInstrumentMemory.forDevice
        self.plugStore = plugStore
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic

    # --- passwords (§11.10) ----------------------------------------------------------------------------
    @staticmethod
    def defaultPassword(device) -> str:
        """E11: the plug's default API (and AP) password is its MAC, e.g. E86BEAE3CB60."""
        return device.mac

    def harden(self, device, currentPassword: Optional[str]) -> str:
        """F2: password = the MAC for the API and the AP, output off after a power cut. Bluetooth stays on (E9)."""
        password = self.defaultPassword(device)
        try:
            self.__setPasswords(device, currentPassword, password, initialOff=True)
        except Exception as error:
            return "✗ Hardening failed: %s" % error
        self.__remember(device, None)                    # the default needs no stored password (R43)
        return "✓ Plug hardened: password = its MAC (%s) for the plug and its own WiFi, output stays off after a " \
               "power cut." % password

    def changePassword(self, device, currentPassword: Optional[str], newPassword: str) -> str:
        """C3 (R45): the user's own password, for the API and the AP together."""
        if not newPassword or len(newPassword) < self.MIN_PASSWORD_LENGTH:
            return "✗ The password needs at least %d characters." % self.MIN_PASSWORD_LENGTH
        try:
            self.__setPasswords(device, currentPassword, newPassword)
        except Exception as error:
            return "✗ Password not changed: %s" % error
        self.__remember(device, None if newPassword == self.defaultPassword(device) else newPassword)
        return "✓ Password changed for the plug and its own WiFi."

    def prepareForShipping(self, device, currentPassword: Optional[str]) -> str:
        """F5 (R48): ① API + AP password back to the MAC ② this PC forgets a stored one ③ the factory WLAN is
        forgotten (sta + sta1, R41) — which cuts the line (R42). A failure in ① stops before ③."""
        mac = self.defaultPassword(device)
        try:
            self.__setPasswords(device, currentPassword, mac)
        except Exception as error:
            return "✗ Not prepared — the plug stays on this WLAN: %s" % error
        self.__remember(device, None)
        http = ShellyHttp(device.host, password=mac, timeout=5.0)
        cleared = {"ssid": None, "pass": None, "enable": False}
        try:
            http.post("WiFi.SetConfig", config={"sta": cleared, "sta1": cleared})
        except Exception:
            pass                                          # the answer may be lost with the WLAN (R42)
        deadline = self.clock() + self.SHIPPING_GONE_SECONDS
        while self.clock() < deadline:
            try:
                ShellyHttp(device.host, timeout=1.0).get("/shelly")
            except Exception:
                return "✓ Ready to ship: password = its MAC (%s), the factory WLAN is forgotten — the plug starts " \
                       "in setup mode at the customer." % mac
            self.sleep(1.0)
        return "✗ The plug is still on the LAN — the WLAN was not forgotten."

    def __setPasswords(self, device, currentPassword, password, initialOff=False):
        # R45: the AP first (still authenticated with the old password), then the API password (SetAuth).
        http = ShellyHttp(device.host, password=currentPassword, timeout=5.0)
        if initialOff:
            http.post("Switch.SetConfig", id=0, config={"initial_state": "off"})
        http.post("WiFi.SetConfig", config={"ap": {"enable": True, "is_open": False, "pass": password}})
        ha1 = hashlib.sha256(("admin:%s:%s" % (device.deviceId, password)).encode()).hexdigest()
        http.post("Shelly.SetAuth", user="admin", realm=device.deviceId, ha1=ha1)

    def __remember(self, device, password):
        # Store (None = the default, the MAC) for this plug only (R33); a running lamp rebuilds its switch.
        from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
        from sciens.spectracs.logic.lamp.LampService import LampService
        PlugRegistry.forget(device.mac)
        self.__store().saveDevice(device)
        self.__store().savePassword(password, mac=device.mac)
        service = LampService.instance
        if self.plugStore is None and service is not None and service.device is not None \
                and service.device.mac == device.mac:
            service.setPassword(password)

    # --- firmware (§11.16) ------------------------------------------------------------------------------
    @staticmethod
    def versionTuple(version):
        """"1.7.5" → (1, 7, 5); "1.4.0-beta1" → (1, 4, 0); None/garbage → ()."""
        import re
        return tuple(int(part) for part in re.findall(r"\d+", (version or "").split("-")[0])[:3])

    def firmwareStatus(self, device, password):
        """(installed, offered stable or None) — `Shelly.CheckForUpdate` asks Shelly's server, so the plug needs
        internet."""
        http = ShellyHttp(device.host, password=password, timeout=15.0)
        installed = (http.get("/shelly") or {}).get("ver")
        offered = ((http.post("Shelly.CheckForUpdate") or {}).get("stable") or {}).get("version")
        return installed, offered

    def updateFirmware(self, device, password, progress=None) -> str:
        """F1b: OTA hop by hop up to TARGET_FIRMWARE. Refused while this plug's lamp is on. Settings, WLAN, password,
        KVS and scripts survive an update — checked: a copy on the plug is verified afterwards."""
        say = progress or (lambda text: None)
        from sciens.spectracs.logic.lamp.LampService import LampService
        from sciens.spectracs.logic.lamp.LampState import LampState
        service = LampService.instance
        if service is not None and service.device is not None and service.device.mac == device.mac \
                and (service.state in (LampState.WARMING, LampState.ON) or service.captureRunning):
            return "✗ Not now — this plug's lamp is in use. Switch it off first."
        target = self.versionTuple(self.TARGET_FIRMWARE)
        lines = []
        for hop in range(self.UPDATE_MAX_HOPS):
            try:
                installed, offered = self.firmwareStatus(device, password)
            except Exception as error:
                return "\n".join(lines + ["✗ The plug did not answer the update check (internet?): %s" % error])
            if self.versionTuple(installed) >= target:
                lines.append("✓ Firmware %s — the tested version (%s) or newer." % (installed, self.TARGET_FIRMWARE))
                break
            if not offered or self.versionTuple(offered) <= self.versionTuple(installed):
                lines.append("✗ Firmware %s, but Shelly offers no update — does the plug reach the internet?"
                             % installed)
                break
            if self.versionTuple(offered) > target:
                lines.append("✗ Firmware %s: Shelly offers %s, newer than the tested %s — not installed."
                             % (installed, offered, self.TARGET_FIRMWARE))
                break
            say("Updating %s → %s … (the plug reboots, up to %d min)" % (installed, offered,
                                                                     self.UPDATE_REBOOT_SECONDS // 60))
            try:
                ShellyHttp(device.host, password=password, timeout=15.0).post("Shelly.Update", stage="stable")
            except Exception as error:
                return "\n".join(lines + ["✗ Update %s → %s refused: %s" % (installed, offered, error)])
            now = self.__waitForVersion(device, offered)
            if now is None:
                return "\n".join(lines + ["✗ Update %s → %s: the plug did not come back with %s within %d min."
                                           % (installed, offered, offered, self.UPDATE_REBOOT_SECONDS // 60)])
            lines.append("✓ Updated %s → %s." % (installed, now))
        try:
            if self.memoryFactory(device, password).index() is not None:
                lines.append(self.verify(device, password).splitlines()[0])      # the copy survived?
        except Exception as error:
            lines.append("✗ After the update the plug's data could not be read: %s" % error)
        device.firmware = self.__installed(device) or device.firmware
        return "\n".join(lines)

    def __waitForVersion(self, device, version):
        deadline = self.clock() + self.UPDATE_REBOOT_SECONDS
        self.sleep(5.0)
        while self.clock() < deadline:
            installed = self.__installed(device)
            if installed is not None and self.versionTuple(installed) >= self.versionTuple(version):
                return installed
            self.sleep(5.0)
        return None

    @staticmethod
    def __installed(device):
        try:
            return (ShellyHttp(device.host, timeout=3.0).get("/shelly") or {}).get("ver")
        except Exception:                                   # rebooting
            return None

    # --- identify (R24) --------------------------------------------------------------------------------
    def identify(self, device, password: Optional[str]) -> str:
        """Blink the LED ring blue a few times (PLUGS_UI.SetConfig writes flash ⇒ few writes), then restore the
        ring exactly. The relay is never touched — also safe on a stranger's plug."""
        http = ShellyHttp(device.host, password=password, timeout=5.0)
        try:
            original = http.post("PLUGS_UI.GetConfig")
        except Exception as error:
            return "✗ The plug did not answer: %s" % error
        try:
            for _ in range(self.IDENTIFY_CYCLES):
                for rgb, brightness in (([0, 0, 100], 100), ([0, 0, 0], 0)):
                    colour = {"rgb": rgb, "brightness": brightness}
                    http.post("PLUGS_UI.SetConfig", config={"leds": {
                        "mode": "switch", "colors": {"switch:0": {"on": colour, "off": colour}}}})
                    self.sleep(self.IDENTIFY_HALF_PERIOD)
        except Exception as error:
            return "✗ Identify failed: %s" % error
        finally:
            try:
                http.post("PLUGS_UI.SetConfig", config={"leds": (original or {}).get("leds")})
            except Exception:
                pass
        return "✓ The plug %s blinked blue." % device.deviceId

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
            from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
            PlugRegistry.forget(device.mac)                 # the verdict for this plug may change now
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
