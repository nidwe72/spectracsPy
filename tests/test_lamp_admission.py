"""L2 (SPEC_shelly_instrument_memory.md §11.3, E6, R16–R19/R25/R31/R43): registered-only switching with TWO plugs.

The case that used to switch a stranger: discovery found several Shellys and took `found[0]`. Now the lamp takes only
the plug whose id is the active instrument's serial AND that carries a server-signed copy made for that id.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \\
        QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_lamp_admission.py -q

NOTE: the copy is built from the real server DB in appdata, seeded like server startup (as test_instrument_copy)."""
import os
import tempfile
import unittest

from PySide6.QtWidgets import QApplication

from fakes.FakeShellyServer import FakeClock, FakeShellyServer
from test_offline_instrument_plug import _InProcessClient
from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule
from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugLabel, PlugRegistry
from sciens.spectracs.logic.lamp.LampAdmission import LampAdmission
from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampService import LampService
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.logic.security.InstrumentCopySignatureUtil import fingerprint
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule

SERIAL = UserSeedLogicModule.DYNAREX_SERIAL           # the box: shellyplusplugs-e86beae3cb60 = FakeShellyServer.MAC
OTHER_MAC = "E465B8B6B4F8"
OTHER_SERIAL = "shellyplusplugs-e465b8b6b4f8"


def app():
    return QApplication.instance() or QApplication([])


class LampAdmissionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from nacl.signing import SigningKey
        app()
        UserSeedLogicModule().seed()
        key = SigningKey.generate()
        handle, cls.keyFile = tempfile.mkstemp(suffix=".seed")
        os.write(handle, bytes(key))
        os.close(handle)
        cls.previousKey = os.environ.get("SPECTRACS_INSTRUMENT_COPY_KEY")
        os.environ["SPECTRACS_INSTRUMENT_COPY_KEY"] = cls.keyFile
        publicKey = bytes(key.verify_key)
        cls.trusted = {fingerprint(publicKey): publicKey.hex()}
        import sciens.spectracs.logic.security.TrustedKeys as trustedKeys
        cls.trustedModule = trustedKeys
        trustedKeys.TRUSTED_COPY_KEYS.update(cls.trusted)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.keyFile)
        for keyId in cls.trusted:
            cls.trustedModule.TRUSTED_COPY_KEYS.pop(keyId, None)
        if cls.previousKey is None:
            os.environ.pop("SPECTRACS_INSTRUMENT_COPY_KEY", None)
        else:
            os.environ["SPECTRACS_INSTRUMENT_COPY_KEY"] = cls.previousKey

    def setUp(self):
        PlugRegistry.forget()
        self.clock = FakeClock()
        self.plugs = []
        self.service = None

    def tearDown(self):
        if self.service is not None:
            self.service.shutdown()
        for plug in self.plugs:
            plug.__exit__(None, None, None)
        LampService.instance = None
        PlugRegistry.forget()

    # --- fixtures ---
    def plug(self, mac=FakeShellyServer.MAC, password=None, copyFor=None):
        plug = FakeShellyServer(clock=self.clock, mac=mac).__enter__()
        self.plugs.append(plug)
        if copyFor is not None:                            # write the copy of `copyFor` onto this plug
            device = LampDevice("shelly-gen2", plug.host, mac, deviceId=plug.realm)
            InstrumentFactoryLogicModule(client=_InProcessClient(), plugStore=LampPlugStore()).write(
                device, None, "masterUserDynarex", "masterUserDynarex") if copyFor == plug.realm else \
                self.__writeForeignCopy(device, copyFor)
        plug.password = password                           # harden only after the copy is on it
        return plug

    def __writeForeignCopy(self, device, serial):
        from sciens.spectracs.logic.instrument.InstrumentCopyLogicModule import InstrumentCopyLogicModule
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugInstrumentMemory
        PlugInstrumentMemory.forDevice(device, None).writeCopy(InstrumentCopyLogicModule().build(serial))

    def service_(self, hosts, serial=SERIAL, controller="SHELLY_GEN2", store=None):
        LampService.instance = None
        store = store or LampPlugStore()
        discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: list(hosts), subnetHosts=lambda: [],
                                  probeTimeout=0.5)
        registry = PlugRegistry(store=store, trustedKeys=self.trusted, knownSerials=lambda: [])
        self.service = LampService(clock=self.clock, threaded=False, discovery=discovery, plugStore=store,
                                   wifiScan=lambda: [], admission=LampAdmission(registry),
                                   instrument=lambda: (serial, controller))
        self.service.configure(True)
        return self.service

    # --- the defect: two plugs, the stranger first ---
    def test_only_the_registered_plug_of_the_active_serial_is_taken(self):
        stranger = self.plug(OTHER_MAC)
        box = self.plug(copyFor=SERIAL)
        service = self.service_([stranger.host, box.host])          # the stranger answers first
        self.assertEqual(LampState.OFF, service.state)
        self.assertEqual(FakeShellyServer.MAC, service.device.mac)
        service.toggleManual()
        self.assertEqual([], stranger.callsTo("Switch.Set"))        # never touched
        self.assertTrue(box.callsTo("Switch.Set"))

    def test_a_plug_without_a_copy_is_never_switched(self):
        stranger = self.plug(OTHER_MAC)
        service = self.service_([stranger.host], serial=OTHER_SERIAL)   # even under its own id
        self.assertEqual(LampState.NO_PLUG, service.state)
        self.assertIsNone(service.switch)
        self.assertIn("no valid instrument data", service.refusedReason)
        self.assertEqual([], stranger.callsTo("Switch.Set"))

    def test_a_copy_made_for_another_plug_does_not_count(self):
        impostor = self.plug(OTHER_MAC, copyFor=SERIAL)              # the box's copy on someone else's plug
        service = self.service_([impostor.host], serial=OTHER_SERIAL)
        self.assertEqual(LampState.NO_PLUG, service.state)
        self.assertEqual([], impostor.callsTo("Switch.Set"))

    def test_another_instruments_plug_is_not_taken(self):
        box = self.plug(copyFor=SERIAL)
        service = self.service_([box.host], serial="ELP-0001")
        self.assertEqual(LampState.NO_PLUG, service.state)
        self.assertEqual([], box.callsTo("Switch.Set"))

    def test_no_serial_no_lamp(self):
        box = self.plug(copyFor=SERIAL)
        self.assertEqual(LampState.NO_PLUG, self.service_([box.host], serial=None).state)

    # --- R17: an instrument without a lamp switch does not even look ---
    def test_none_controller_skips_discovery(self):
        asked = []
        LampService.instance = None
        discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: asked.append(1) or [], subnetHosts=lambda: [])
        self.service = LampService(clock=self.clock, threaded=False, discovery=discovery, plugStore=LampPlugStore(),
                                   wifiScan=lambda: [], instrument=lambda: ("ELP-0001", "NONE"))
        self.service.configure(True)
        self.assertEqual(LampState.NOT_APPLICABLE, self.service.state)
        self.assertEqual([], asked)

    # --- R43: passwords ---
    def test_default_password_opens_and_is_flagged(self):
        box = self.plug(copyFor=SERIAL, password=FakeShellyServer.MAC)
        service = self.service_([box.host])
        self.assertEqual(LampState.OFF, service.state)
        self.assertTrue(service.defaultPassword)                     # the C2 reminder
        service.toggleManual()
        self.assertTrue(box.callsTo("Switch.Set"))

    def test_a_plug_hardened_after_the_probe_still_opens(self):
        # L7 A2 (2026-10-20): the lamp probed the plug open, the sync hardened it with the MAC a moment later —
        # the read must still try the MAC, not call the plug locked.
        box = self.plug(copyFor=SERIAL)
        probedOpen = LampDevice("shelly-gen2", box.host, FakeShellyServer.MAC, deviceId=SERIAL, authRequired=False)
        box.password = FakeShellyServer.MAC
        candidate = PlugRegistry(store=LampPlugStore(), trustedKeys=self.trusted,
                                 knownSerials=lambda: []).classify(probedOpen)
        self.assertEqual(PlugLabel.REGISTERED, candidate.label)
        self.assertEqual(FakeShellyServer.MAC, candidate.password)

    def test_an_overtaken_search_result_is_dropped(self):
        box = self.plug(copyFor=SERIAL)
        service = self.service_([box.host])
        self.assertEqual(LampState.OFF, service.state)
        service.discoveryId += 1                         # a newer search was started meanwhile
        service.state = LampState.SEARCHING
        from sciens.spectracs.logic.lamp.LampAdmission import Admission
        service._LampService__onDiscovered(None, Admission(reason="stale"), [], service.discoveryId - 1)
        self.assertEqual(LampState.SEARCHING, service.state)        # the stale "not found" did not win

    def test_a_stored_password_is_tried_before_the_mac(self):
        box = self.plug(copyFor=SERIAL, password="changed-pw")
        store = LampPlugStore()
        store.saveDevice(LampDevice("shelly-gen2", box.host, FakeShellyServer.MAC, deviceId=SERIAL))
        store.savePassword("changed-pw", mac=FakeShellyServer.MAC)
        service = self.service_([box.host], store=store)
        self.assertEqual(LampState.OFF, service.state)
        self.assertFalse(service.defaultPassword)

    def test_unknown_password_is_locked_not_switched(self):
        box = self.plug(copyFor=SERIAL, password="someone-elses")
        service = self.service_([box.host])
        self.assertEqual(LampState.NO_PLUG, service.state)
        self.assertTrue(service.needsPassword)
        self.assertEqual([], box.callsTo("Switch.Set"))

    def test_two_stored_plugs_keep_both_passwords(self):
        box = self.plug(copyFor=SERIAL, password="box-pw")
        other = self.plug(OTHER_MAC, password="other-pw")
        store = LampPlugStore()
        for plug, pw in ((box, "box-pw"), (other, "other-pw")):
            store.saveDevice(LampDevice("shelly-gen2", plug.host, plug.mac, deviceId=plug.realm))
            store.savePassword(pw, mac=plug.mac)
        self.service_([other.host, box.host], store=store)
        self.assertEqual("box-pw", store.load(mac=FakeShellyServer.MAC)[1])
        self.assertEqual("other-pw", store.load(mac=OTHER_MAC)[1])

    # --- the labels for the pickers (§11.3) ---
    def test_classify_all_labels_and_orders(self):
        box = self.plug(copyFor=SERIAL)
        known = self.plug("0123456789AB")
        stranger = self.plug(OTHER_MAC)
        locked = self.plug("AABBCCDDEEFF", password="secret")
        found = LampDiscovery(mdnsBrowse=lambda t, s: [stranger.host, locked.host, known.host, box.host],
                              subnetHosts=lambda: [], probeTimeout=0.5).discoverAll().devices
        registry = PlugRegistry(store=LampPlugStore(), trustedKeys=self.trusted,
                                knownSerials=lambda: [known.realm])
        labels = [(c.device.mac, c.label) for c in registry.classifyAll(found)]
        self.assertEqual([(FakeShellyServer.MAC, PlugLabel.REGISTERED), ("0123456789AB", PlugLabel.KNOWN),
                          ("AABBCCDDEEFF", PlugLabel.LOCKED), (OTHER_MAC, PlugLabel.FOREIGN)], labels)

    def test_discovery_never_falls_back_to_the_first_plug(self):
        stranger = self.plug(OTHER_MAC)
        box = self.plug()
        discovery = LampDiscovery(mdnsBrowse=lambda t, s: [stranger.host, box.host], subnetHosts=lambda: [],
                                  probeTimeout=0.5)
        self.assertIsNone(discovery.discover().chosen)
        self.assertEqual(FakeShellyServer.MAC, discovery.discover(wantedId=SERIAL).chosen.mac)
        self.assertIsNone(discovery.discover(wantedId="shellyplusplugs-000000000000").chosen)


if __name__ == "__main__":
    unittest.main()
