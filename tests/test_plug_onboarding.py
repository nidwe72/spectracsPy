"""L6 (SPEC_shelly_instrument_memory.md §11.5, E10): Add new plug over Bluetooth — the logic, with a fake BLE link.

The real link (ShellyBleRpc) ran against both of Edwin's plugs in the L0 spike (§11.6.1); here: only plugs NOT on the
LAN are offered, a hardened plug is opened with its MAC first (E11), only the WLAN is written, and the flow waits
until the plug answers on the LAN.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \\
        ./venv/bin/python -m pytest tests/test_plug_onboarding.py -q"""
import subprocess
import unittest

from sciens.spectracs.logic.instrumentMemory.PlugOnboardingLogicModule import PlugOnboardingLogicModule
from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.lamp.LampDiscoveryResult import LampDiscoveryResult
from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed
from sciens.spectracs.logic.lamp.ShellyBleRpc import BleShelly, ShellyBleRpc


class _FakeBle:
    def __init__(self, shellys, password=None):
        self.shellys = shellys
        self.password = password
        self.calls = []

    def scan(self, seconds=None):
        return list(self.shellys)

    def joinWlan(self, address, ssid, wlanPassword, plugPassword=None):
        self.calls.append((address, ssid, wlanPassword, plugPassword))
        if self.password is not None and plugPassword != self.password:
            raise LampAuthFailed("401")
        return {"restart_required": False}


class _FakeDiscovery:
    def __init__(self, appearAfter, device):
        self.appearAfter, self.device, self.polls = appearAfter, device, 0

    def discoverAll(self):
        self.polls += 1
        return LampDiscoveryResult([self.device] if self.polls > self.appearAfter else [])


NEW = BleShelly("E4:65:B8:B6:B4:FA", "ShellyPlusPlugS-E465B8B6B4F8", "E465B8B6B4F8", -60)
BOX = BleShelly("E8:6B:EA:E3:CB:62", "ShellyPlusPlugS-E86BEAE3CB60", "E86BEAE3CB60", -70)


class PlugOnboardingTest(unittest.TestCase):

    def test_only_plugs_not_on_the_lan_are_offered(self):
        logic = PlugOnboardingLogicModule(ble=_FakeBle([BOX, NEW]))
        self.assertEqual([NEW.mac], [s.mac for s in logic.newPlugs(lanMacs=["E8:6B:EA:E3:CB:60"])])

    def test_the_ble_name_carries_the_mac(self):
        match = ShellyBleRpc.NAME.match("ShellyPlusPlugS-E465B8B6B4F8")
        self.assertEqual("E465B8B6B4F8", match.group(2))
        self.assertIsNone(ShellyBleRpc.NAME.match("SomeHeadphones"))

    def test_an_open_plug_joins_with_only_the_wlan(self):
        ble = _FakeBle([NEW])
        text = PlugOnboardingLogicModule(ble=ble).join(NEW, "Sciens2G6971", "wlan-pw")
        self.assertTrue(text.startswith("✓"), text)
        self.assertEqual([(NEW.address, "Sciens2G6971", "wlan-pw", None)], ble.calls)

    def test_a_hardened_plug_is_opened_with_its_mac(self):
        ble = _FakeBle([NEW], password=NEW.mac)
        text = PlugOnboardingLogicModule(ble=ble).join(NEW, "Sciens2G6971", "wlan-pw")
        self.assertTrue(text.startswith("✓"), text)
        self.assertEqual([None, NEW.mac], [call[3] for call in ble.calls])

    def test_a_locked_plug_says_so(self):
        text = PlugOnboardingLogicModule(ble=_FakeBle([NEW], password="secret")).join(NEW, "x", "y")
        self.assertIn("locked", text)

    def test_waits_until_the_plug_is_on_the_lan(self):
        device = LampDevice("shelly-gen2", "192.168.1.121", NEW.mac, deviceId="shellyplusplugs-e465b8b6b4f8")
        clock = [0.0]
        logic = PlugOnboardingLogicModule(discovery=_FakeDiscovery(2, device),
                                          sleep=lambda s: clock.__setitem__(0, clock[0] + s), clock=lambda: clock[0])
        self.assertEqual(device, logic.waitOnLan(NEW.mac))

    def test_gives_up_after_a_minute(self):
        clock = [0.0]
        logic = PlugOnboardingLogicModule(discovery=_FakeDiscovery(10 ** 6, None),
                                          sleep=lambda s: clock.__setitem__(0, clock[0] + s), clock=lambda: clock[0])
        self.assertIsNone(logic.waitOnLan(NEW.mac))

    def test_write_piece_follows_the_firmware(self):
        from sciens.spectracs.logic.plugstore.PlugKeyValueStore import PlugKeyValueStore
        self.assertEqual(2048, PlugKeyValueStore.writePieceFor("0.13.0"))     # 3 KiB already resets
        self.assertEqual(4096, PlugKeyValueStore.writePieceFor("1.3.3"))
        self.assertEqual(4096, PlugKeyValueStore.writePieceFor("1.7.5"))      # 8 KiB → HTTP 413
        self.assertEqual(2048, PlugKeyValueStore.writePieceFor(None))

    def test_current_ssid_from_nmcli(self):
        def runner(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, stdout="no:Other\nyes:Sciens2G6971\n", stderr="")
        self.assertEqual("Sciens2G6971", PlugOnboardingLogicModule(runner=runner).currentSsid())


if __name__ == "__main__":
    unittest.main()
