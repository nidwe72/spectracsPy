import subprocess
import time
from typing import Iterable, List, Optional

from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed


class PlugOnboardingLogicModule:
    """Add new plug (SPEC_shelly_instrument_memory.md §11.5, E10, L6): a fresh or factory-reset Shelly joins a WLAN
    over Bluetooth — and NOTHING else is written (no Harden, no Write: the plug gets instrument data only once a
    master decides which instrument it belongs to). Linux only for now. Qt-free; every call blocks ⇒ off the GUI.

        newPlugs(lanMacs)   Shellys seen over Bluetooth that are not on the LAN yet
        currentSsid()       the WLAN this PC is on (nmcli) — the default to join
        join(...)           WiFi.SetConfig over Bluetooth; a hardened plug is opened with its MAC first (E11)
        waitOnLan(mac)      until the plug answers on the LAN (mDNS, then the /24) — its LampDevice, or None"""

    LAN_WAIT_SECONDS = 60.0
    LAN_POLL_SECONDS = 3.0

    def __init__(self, ble=None, discovery=None, sleep=None, clock=None, runner=None):
        self.ble = ble
        self.discovery = discovery
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
        self.runner = runner or subprocess.run

    @staticmethod
    def available() -> bool:
        import sys
        from sciens.spectracs.logic.lamp.ShellyBleRpc import ShellyBleRpc
        return sys.platform.startswith("linux") and ShellyBleRpc.available()

    def newPlugs(self, lanMacs: Iterable[str] = ()) -> List:
        lan = {mac.upper().replace(":", "") for mac in lanMacs}
        return [shelly for shelly in self.__ble().scan() if shelly.mac not in lan]

    def currentSsid(self) -> Optional[str]:
        try:
            out = self.runner(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"], capture_output=True, text=True,
                              timeout=10).stdout
        except Exception:
            return None
        for line in (out or "").splitlines():
            if line.startswith("yes:"):
                return line[4:].replace("\\:", ":") or None
        return None

    def join(self, shelly, ssid: str, wlanPassword: str, plugPassword: Optional[str] = None) -> str:
        """A short result line. A plug that asks for a password is tried with its MAC (the default, E11), then with
        `plugPassword`."""
        for password in dict.fromkeys((None, shelly.mac, plugPassword)):
            try:
                self.__ble().joinWlan(shelly.address, ssid, wlanPassword, password)
                return "✓ %s joins %s." % (shelly.name, ssid)
            except LampAuthFailed:
                continue
            except Exception as error:
                return "✗ %s did not take the WLAN: %s" % (shelly.name, error)
        return "✗ %s is locked with a password — enter it and try again." % shelly.name

    def waitOnLan(self, mac: str):
        mac = mac.upper().replace(":", "")
        deadline = self.clock() + self.LAN_WAIT_SECONDS
        while self.clock() < deadline:
            for device in self.__discovery().discoverAll().devices:
                if device.mac == mac:
                    return device
            self.sleep(self.LAN_POLL_SECONDS)
        return None

    def __ble(self):
        if self.ble is None:
            from sciens.spectracs.logic.lamp.ShellyBleRpc import ShellyBleRpc
            self.ble = ShellyBleRpc()
        return self.ble

    def __discovery(self):
        if self.discovery is None:
            from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
            self.discovery = LampDiscovery()
        return self.discovery
