"""
P1 of SPEC_lamp_switch.md — the Qt-free lamp driver against a FakeShellyServer (no hardware).

Covers the Shelly semantics measured on the real plug (§15.3), the SHA-256 digest auth the real plug demands
(§14 R1), and the error mapping (LampUnreachable / LampAuthFailed). Also the discovery order (§5) and the
unconfigured-plug hint parser (§15.5), with mDNS and the subnet list injected.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_lamp_driver.py -q
"""
import unittest

from fakes.FakeShellyServer import FakeClock, FakeShellyServer
from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable
from sciens.spectracs.logic.lamp.LampSetupHint import LampSetupHint
from sciens.spectracs.logic.lamp.NoLampSwitch import NoLampSwitch
from sciens.spectracs.logic.lamp.ShellyGen2Driver import ShellyGen2Driver
from sciens.spectracs.logic.lamp.ShellyGen2LampSwitch import ShellyGen2LampSwitch


class ShellySwitchTest(unittest.TestCase):

    def test_on_status_off(self):
        with FakeShellyServer() as plug:
            lamp = ShellyGen2LampSwitch(plug.host)
            lamp.on(1800)
            status = lamp.status()
            self.assertTrue(status.isOn)
            self.assertAlmostEqual(11.2, status.watts)
            self.assertTrue(status.timerRunning)
            self.assertEqual("1800", plug.callsTo("Switch.Set")[-1]["toggle_after"])
            lamp.off()
            status = lamp.status()
            self.assertFalse(status.isOn)
            self.assertFalse(status.timerRunning)

    def test_every_on_carries_the_cap(self):
        # an on WITHOUT toggle_after would cancel the running timer (§14.2) — the driver must never send one
        with FakeShellyServer() as plug:
            lamp = ShellyGen2LampSwitch(plug.host)
            lamp.on(30)
            lamp.on(60)
            self.assertTrue(all("toggle_after" in params for params in plug.callsTo("Switch.Set")))

    def test_the_cap_switches_the_plug_off(self):
        clock = FakeClock()
        with FakeShellyServer(clock=clock) as plug:
            lamp = ShellyGen2LampSwitch(plug.host)
            lamp.on(1800)
            clock.advance(1799)
            self.assertTrue(lamp.status().isOn)
            clock.advance(2)
            self.assertFalse(lamp.status().isOn)

    def test_digest_sha256_password_ok(self):
        with FakeShellyServer(password="geheim") as plug:
            lamp = ShellyGen2LampSwitch(plug.host, password="geheim")
            lamp.on(10)
            self.assertTrue(lamp.status().isOn)

    def test_wrong_or_missing_password(self):
        with FakeShellyServer(password="geheim") as plug:
            with self.assertRaises(LampAuthFailed):
                ShellyGen2LampSwitch(plug.host, password="falsch").on(10)
            with self.assertRaises(LampAuthFailed):
                ShellyGen2LampSwitch(plug.host).on(10)
            self.assertFalse(plug.output)

    def test_unreachable(self):
        with FakeShellyServer() as plug:
            plug.dark = True
            with self.assertRaises(LampUnreachable):
                ShellyGen2LampSwitch(plug.host, timeout=0.5).status()
        with self.assertRaises(LampUnreachable):
            ShellyGen2LampSwitch("127.0.0.1:9", timeout=0.5).off()       # nothing listens on port 9

    def test_no_lamp_switch_never_fails(self):
        lamp = NoLampSwitch()
        lamp.on(10)
        lamp.off()
        self.assertFalse(lamp.status().isOn)
        self.assertFalse(lamp.isSwitchable())


class ShellyProbeTest(unittest.TestCase):

    def test_probe_identifies_the_plug(self):
        with FakeShellyServer() as plug:
            device = ShellyGen2Driver().probe(plug.host)
            self.assertEqual("E86BEAE3CB60", device.mac)
            self.assertEqual("PlusPlugS", device.model)
            self.assertFalse(device.authRequired)
            self.assertEqual("E8:6B:EA:E3:CB:60", device.formattedMac())

    def test_probe_with_password_reports_auth_required(self):
        with FakeShellyServer(password="geheim") as plug:
            self.assertTrue(ShellyGen2Driver().probe(plug.host).authRequired)

    def test_probe_rejects_gen1_and_silence(self):
        with FakeShellyServer(gen=1) as plug:
            self.assertIsNone(ShellyGen2Driver().probe(plug.host))
        self.assertIsNone(ShellyGen2Driver().probe("127.0.0.1:9", timeout=0.3))

    def test_mac_from_setup_ssid(self):
        driver = ShellyGen2Driver()
        self.assertEqual("E86BEAE3CB60", driver.macFromSsid("ShellyPlusPlugS-E86BEAE3CB60"))
        self.assertIsNone(driver.macFromSsid("Sciens2G6971"))
        self.assertIsNone(driver.macFromSsid("ShellyPlusPlugS-XYZ"))


class LampDiscoveryTest(unittest.TestCase):

    @staticmethod
    def discovery(mdnsHosts=(), subnetHosts=()):
        return LampDiscovery(mdnsBrowse=lambda types, seconds: list(mdnsHosts),
                             subnetHosts=lambda: list(subnetHosts), probeTimeout=0.5)

    def test_stored_plug_is_used_without_browsing(self):
        with FakeShellyServer() as plug:
            browsed = []
            discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: browsed.append(1) or [],
                                      subnetHosts=lambda: browsed.append(2) or [])
            result = discovery.discover(LampDevice("shelly-gen2", plug.host, plug.MAC))
            self.assertEqual("stored", result.via)
            self.assertEqual(plug.MAC, result.chosen.mac)
            self.assertEqual([], browsed)

    def test_stored_host_answers_with_another_mac_then_browse(self):
        with FakeShellyServer(mac="AAAAAAAAAAAA") as other, FakeShellyServer() as plug:
            result = self.discovery(mdnsHosts=[other.host, plug.host]).discover(
                LampDevice("shelly-gen2", other.host, plug.MAC))
            self.assertEqual("mdns", result.via)
            self.assertEqual(plug.MAC, result.chosen.mac)            # the stored MAC wins over the first found
            self.assertEqual(["AAAAAAAAAAAA"], [device.mac for device in result.others()])

    def test_ip_changed_found_again_by_mac(self):
        with FakeShellyServer() as plug:
            result = self.discovery(mdnsHosts=[plug.host]).discover(LampDevice("shelly-gen2", "127.0.0.1:9", plug.MAC))
            self.assertEqual(plug.host, result.chosen.host)

    def test_subnet_fallback_when_mdns_finds_nothing(self):
        with FakeShellyServer() as plug:
            result = self.discovery(mdnsHosts=[], subnetHosts=["127.0.0.1:9", plug.host]).discover()
            self.assertEqual("subnet", result.via)
            self.assertEqual(plug.MAC, result.chosen.mac)

    def test_nothing_found(self):
        result = self.discovery(subnetHosts=["127.0.0.1:9"]).discover()
        self.assertIsNone(result.chosen)
        self.assertEqual([], result.devices)

    def test_a_failing_browser_does_not_break_discovery(self):
        def boom(types, seconds):
            raise OSError("no multicast")
        with FakeShellyServer() as plug:
            result = LampDiscovery(mdnsBrowse=boom, subnetHosts=lambda: [plug.host]).discover()
            self.assertEqual(plug.MAC, result.chosen.mac)


class LampSetupHintTest(unittest.TestCase):

    NMCLI = ("Sciens5G6971:WPA2\n"
             "ShellyPlusPlugS-E86BEAE3CB60:\n"
             "ShellyPlusPlugS-0123456789AB:\n"
             "ShellyPlusPlugS-FFFFFFFFFFFF:WPA2\n"
             "Odd\\:Name:--\n")

    def test_parse_nmcli_unescapes_colons(self):
        rows = LampSetupHint.parseNmcli(self.NMCLI)
        self.assertIn(("Odd:Name", "--"), rows)
        self.assertIn(("ShellyPlusPlugS-E86BEAE3CB60", ""), rows)

    def test_configured_plug_with_its_ap_still_on_is_not_hinted(self):
        rows = LampSetupHint.parseNmcli(self.NMCLI)
        self.assertEqual(["ShellyPlusPlugS-0123456789AB"],
                         LampSetupHint.unconfiguredSsids(rows, knownMacs=["E8:6B:EA:E3:CB:60"]))

    def test_without_known_plugs_every_open_setup_ssid_is_hinted(self):
        rows = LampSetupHint.parseNmcli(self.NMCLI)
        self.assertEqual(["ShellyPlusPlugS-E86BEAE3CB60", "ShellyPlusPlugS-0123456789AB"],
                         LampSetupHint.unconfiguredSsids(rows))


if __name__ == "__main__":
    unittest.main()
