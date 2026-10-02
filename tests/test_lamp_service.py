"""
P3 of SPEC_lamp_switch.md — LampService against a FakeShellyServer, unthreaded (the worker runs on the test
thread, so every command completes before the call returns) and on a FakeClock (no test waits for a cap).

Covers §16.2's state table, the warm-up and cap clocks, the Q1 re-arm, external changes (G5), the workflow
owner token (G7), logout (G4), the gate (D2) and the idempotent shutdown (§7.1).

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_lamp_service.py -q
"""
import unittest

from PySide6.QtWidgets import QApplication

from fakes.FakeShellyServer import FakeClock, FakeShellyServer
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampService import LampService
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.plugin_sdk import LampPolicy, SpectralWorkflowPhaseType

ACQ = SpectralWorkflowPhaseType.ACQUISITION
PROC = SpectralWorkflowPhaseType.PROCESSING


def app():
    # a QApplication, not a QCoreApplication: later tests in the same process build widgets (Qt aborts otherwise)
    return QApplication.instance() or QApplication([])


class LampServiceTestBase(unittest.TestCase):

    def setUp(self):
        app()
        self.clock = FakeClock()
        self.plug = FakeShellyServer(clock=self.clock).__enter__()
        self.service = self.makeService([self.plug.host])
        self.wentOff = []
        self.service.lampWentOff.connect(self.wentOff.append)

    def tearDown(self):
        self.service.shutdown()
        self.plug.__exit__(None, None, None)
        LampService.instance = None

    def makeService(self, hosts, store=None, wifi=()):
        LampService.instance = None
        discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: list(hosts), subnetHosts=lambda: [],
                                  probeTimeout=0.5)
        return LampService(clock=self.clock, threaded=False, discovery=discovery,
                           plugStore=store or LampPlugStore(), wifiScan=lambda: list(wifi))

    def ready(self):
        self.service.configure(True)
        self.assertEqual(LampState.OFF, self.service.state)


class DiscoveryStatesTest(LampServiceTestBase):

    def test_not_applicable_until_configured(self):
        self.assertEqual(LampState.NOT_APPLICABLE, self.service.state)
        self.assertTrue(self.service.readyForCapture())

    def test_plug_found_is_off(self):
        self.ready()
        self.assertEqual(self.plug.MAC, self.service.device.mac)

    def test_found_plug_gets_a_dim_off_led(self):
        self.ready()
        off = self.plug.uiConfig["leds"]["colors"]["switch:0"]["off"]
        self.assertEqual({"rgb": [20, 20, 20], "brightness": 3}, off)
        self.assertNotIn("on", self.plug.uiConfig["leds"]["colors"]["switch:0"])   # "on" stays the user's

    def test_no_plug(self):
        self.service = self.makeService([])
        self.service.configure(True)
        self.assertEqual(LampState.NO_PLUG, self.service.state)

    def test_password_needed_but_unknown(self):
        with FakeShellyServer(password="geheim") as locked:
            self.service = self.makeService([locked.host])
            self.service.configure(True)
            self.assertEqual(LampState.NO_PLUG, self.service.state)
            self.assertTrue(self.service.needsPassword)
            self.service.setPassword("geheim")
            self.assertEqual(LampState.OFF, self.service.state)
            self.assertFalse(self.service.needsPassword)

    def test_setup_ssid_hint_skips_the_known_plug(self):
        self.service = self.makeService([self.plug.host], wifi=[("ShellyPlusPlugS-E86BEAE3CB60", ""),
                                                                ("ShellyPlusPlugS-0123456789AB", "")])
        self.service.configure(True)
        self.assertEqual(["ShellyPlusPlugS-0123456789AB"], self.service.setupSsids)

    def test_already_on_plug_is_adopted(self):
        self.plug.output = True
        self.ready_or_on()
        self.assertEqual(LampState.ON, self.service.state)
        self.assertIsNone(self.service.capRemainingSeconds())

    def ready_or_on(self):
        self.service.configure(True)


class WorkflowTest(LampServiceTestBase):

    POLICY = LampPolicy.duringAcquisition(maxMeasurementSeconds=1500)

    def test_acquisition_on_warm_up_then_on(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.assertTrue(self.plug.output)
        self.assertEqual("1800", self.plug.callsTo("Switch.Set")[-1]["toggle_after"])
        self.assertEqual(LampState.WARMING, self.service.state)
        self.assertFalse(self.service.readyForCapture())
        self.clock.advance(12)
        self.service.tick()
        self.assertEqual(8, self.service.warmUpRemainingSeconds())
        self.clock.advance(8)
        self.service.tick()
        self.assertEqual(LampState.ON, self.service.state)
        self.assertTrue(self.service.readyForCapture())

    def test_processing_switches_off(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.service.applyPhase(self, self.POLICY, PROC)
        self.assertFalse(self.plug.output)
        self.assertEqual(LampState.OFF, self.service.state)

    def test_unswitched_plugin_never_touches_the_lamp(self):
        self.ready()
        self.service.applyPhase(self, LampPolicy.default(), ACQ)
        self.assertEqual([], self.plug.callsTo("Switch.Set"))
        self.assertTrue(self.service.readyForCapture())

    def test_reentering_acquisition_does_not_resend_or_rewarm(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.clock.advance(25)
        self.service.tick()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.assertEqual(1, len(self.plug.callsTo("Switch.Set")))
        self.assertEqual(LampState.ON, self.service.state)

    def test_q1_rearm_when_the_cap_is_nearly_spent(self):
        self.ready()
        self.service.toggleManual()                          # on by hand, host cap 1800
        self.clock.advance(1000)                             # 800 s left < 1500 needed
        self.service.tick()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.assertEqual(2, len(self.plug.callsTo("Switch.Set")))
        self.assertAlmostEqual(1800, self.service.capRemainingSeconds())
        self.assertEqual(LampState.ON, self.service.state)  # re-arm does not re-warm

    def test_cap_stops_and_reports(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.clock.advance(1800)
        self.service.tick()
        self.assertEqual(LampState.OFF, self.service.state)
        self.assertEqual(["cap"], self.wentOff)
        self.plug.tick()
        self.assertFalse(self.plug.output)                   # the plug's own timer did it

    def test_release_only_by_the_owner(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        other = object()
        self.service.releaseWorkflow(other)
        self.assertTrue(self.plug.output)
        self.service.releaseWorkflow(self)
        self.assertFalse(self.plug.output)
        self.assertTrue(self.service.readyForCapture())

    def test_plug_back_from_unreachable_during_acquisition_switches_on(self):
        # Rig 2026-10-02: the plug was re-plugged during ACQUISITION — it powers up OFF, and the workflow still
        # wants the lamp. It must switch on (fresh warm-up), not wait for a click on the icon.
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.plug.dark = True
        self.service.switch.setTimeout(0.3)
        self.service.poll()
        self.assertEqual(LampState.UNREACHABLE, self.service.state)
        self.plug.dark = False
        self.plug.output = False                             # a power cycle: the Shelly comes up off
        self.service.poll()
        self.assertTrue(self.plug.output)
        self.assertEqual(LampState.WARMING, self.service.state)
        self.assertFalse(self.service.readyForCapture())

    def test_plug_found_later_during_acquisition_switches_on(self):
        hosts = []
        self.service = self.makeService(hosts)
        self.service.configure(True)
        self.assertEqual(LampState.NO_PLUG, self.service.state)
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.assertTrue(self.service.readyForCapture())      # no plug: never locked out
        hosts.append(self.plug.host)                         # plugged in, then Settings -> [Search again]
        self.service.discover()
        self.assertTrue(self.plug.output)
        self.assertEqual(LampState.WARMING, self.service.state)

    def test_plug_back_outside_acquisition_stays_off(self):
        self.ready()
        self.service.applyPhase(self, self.POLICY, ACQ)
        self.service.applyPhase(self, self.POLICY, PROC)
        self.plug.dark = True
        self.service.switch.setTimeout(0.3)
        self.service.poll()
        self.plug.dark = False
        self.service.poll()
        self.assertFalse(self.plug.output)
        self.assertEqual(LampState.OFF, self.service.state)

    def test_on_while_searching_is_queued(self):
        self.service.state = LampState.SEARCHING
        self.service.switchOn(1800, 20, 1500, self)
        self.assertEqual([], self.plug.callsTo("Switch.Set"))
        stored, _ = self.service.plugStore.load()
        self.service._cmdDiscover.emit(stored)
        self.assertTrue(self.plug.output)


class ManualAndExternalTest(LampServiceTestBase):

    def test_manual_toggle(self):
        self.ready()
        self.assertTrue(self.service.toggleManual())
        self.assertEqual(LampState.WARMING, self.service.state)
        self.assertTrue(self.service.toggleManual())
        self.assertEqual(LampState.OFF, self.service.state)

    def test_manual_toggle_ignored_during_capture(self):
        self.ready()
        self.service.toggleManual()
        self.service.setCaptureRunning(True)
        self.assertFalse(self.service.toggleManual())
        self.assertTrue(self.plug.output)

    def test_external_off_is_reported(self):
        self.ready()
        self.service.toggleManual()
        self.plug.output = False
        self.service.poll()
        self.assertEqual(LampState.OFF, self.service.state)
        self.assertEqual(["external"], self.wentOff)

    def test_external_on_is_adopted(self):
        self.ready()
        self.plug.output = True
        self.service.poll()
        self.assertEqual(LampState.ON, self.service.state)

    def test_unreachable_keeps_the_state_and_recovers(self):
        self.ready()
        self.service.toggleManual()
        self.plug.dark = True
        self.service.switch.setTimeout(0.3)
        self.service.poll()
        self.assertEqual(LampState.UNREACHABLE, self.service.state)
        self.assertEqual([], self.wentOff)                   # no capture stop on a Wi-Fi blip
        self.plug.dark = False
        self.service.poll()
        self.assertEqual(LampState.WARMING, self.service.state)

    def test_no_power_hint(self):
        self.ready()
        self.plug.lampWatts = 0.0
        self.service.toggleManual()
        self.service._LampService__checkPower()
        self.assertTrue(self.service.noPower)


class SessionAndExitTest(LampServiceTestBase):

    def test_logout_switches_off(self):
        self.ready()
        self.service.toggleManual()
        self.service.configure(False)
        self.assertFalse(self.plug.output)
        self.assertEqual(LampState.NOT_APPLICABLE, self.service.state)

    def test_shutdown_is_synchronous_and_idempotent(self):
        self.ready()
        self.service.toggleManual()
        self.service.shutdown()
        self.service.shutdown()
        self.assertFalse(self.plug.output)
        self.assertEqual(1, len(self.plug.offCalls()))
        self.service.toggleManual()                          # after shutdown nothing switches any more
        self.assertFalse(self.plug.output)

    def test_shutdown_with_the_plug_gone_does_not_hang(self):
        self.ready()
        self.plug.dark = True
        self.service.shutdown()                              # 2 × 1 s at most, no exception


class ThreadedShutdownTest(unittest.TestCase):
    # The rig log of 2026-10-02: plug gone, a poll in flight on the worker thread, app closed =>
    # "QThread: Destroyed while thread is still running". The join must outlast one call on the normal timeout.

    def test_shutdown_joins_a_worker_stuck_in_a_poll(self):
        import time
        from PySide6.QtCore import QCoreApplication
        app()
        with FakeShellyServer() as plug:
            discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: [plug.host], subnetHosts=lambda: [],
                                      probeTimeout=0.5)
            service = LampService(threaded=True, discovery=discovery, plugStore=LampPlugStore(),
                                  wifiScan=lambda: [])
            try:
                service.configure(True)
                deadline = time.monotonic() + 5
                while service.state != LampState.OFF and time.monotonic() < deadline:
                    QCoreApplication.processEvents()
                    time.sleep(0.02)
                self.assertEqual(LampState.OFF, service.state)
                plug.silent = True
                service.poll()                              # the worker now waits ~2 s on the silent plug
                time.sleep(0.2)
                service.shutdown()
                self.assertTrue(service.thread.isFinished())
            finally:
                service.shutdown()
                LampService.instance = None


class StoreTest(LampServiceTestBase):

    def test_found_plug_is_stored_and_used_first(self):
        store = LampPlugStore()
        self.service = self.makeService([self.plug.host], store=store)
        self.service.configure(True)
        self.assertEqual(self.plug.MAC, store.load()[0].mac)
        self.service = self.makeService([], store=store)     # mDNS silent now: the stored host still works
        self.service.configure(True)
        self.assertEqual(LampState.OFF, self.service.state)


if __name__ == "__main__":
    unittest.main()
