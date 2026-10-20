"""
S5–S8 of SPEC_shelly_instrument_memory.md: the factory steps, the after-login sync and the offline login, end to end
against FakeShellyServer (POST /rpc, KVS + script slots) with the server side run in-process and a throw-away
copy-signing key. No hardware, no running server.

NOTE: builds copies from the real server DB in appdata, seeded like server startup.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fakes"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from FakeShellyServer import FakeShellyServer  # noqa: E402

from sciens.spectracs.logic.instrument.InstrumentCopyLogicModule import InstrumentCopyLogicModule  # noqa: E402
from sciens.spectracs.logic.instrumentMemory.InstrumentFactoryLogicModule import InstrumentFactoryLogicModule  # noqa: E402
from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import (  # noqa: E402
    OfflineLoginLogicModule, PlugInstrumentMemory, PlugInstrumentSync)
from sciens.spectracs.logic.lamp.LampDevice import LampDevice  # noqa: E402
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore  # noqa: E402
from sciens.spectracs.logic.security.InstrumentCopySignatureUtil import fingerprint  # noqa: E402
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession  # noqa: E402
from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry  # noqa: E402
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule  # noqa: E402

SERIAL = UserSeedLogicModule.DYNAREX_SERIAL          # = FakeShellyServer.REALM, the plug's device id


class _Locator:
    """The plug lookup without discovery: `device` is the one plug in reach."""

    def __init__(self, device, password=None, trusted=None):
        self.device, self.password, self.trusted = device, password, trusted

    def find(self, serial=None, discover=True):
        return self.device, self.password

    def registeredPlugs(self):
        return [(self.device, self.password)] if self.device is not None else []

    def findBySerial(self, serial):
        if self.device is None or self.device.deviceId != serial:
            return None
        from sciens.spectracs.logic.lamp.ShellyGen2Driver import ShellyGen2Driver
        self.device = ShellyGen2Driver().probe(self.device.host) or self.device     # auth_en as the plug says now
        from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
        PlugRegistry.forget()
        store = LampPlugStore()
        if self.password:
            store.saveDevice(self.device)
            store.savePassword(self.password, mac=self.device.mac)
        return PlugRegistry(store=store, trustedKeys=self.trusted, knownSerials=lambda: []).classify(self.device)


class _InProcessClient:
    """The server calls the factory and the sync make, answered in-process (no Pyro)."""

    def __init__(self):
        self.calls = []

    def getInstrumentCopy(self, username, password, serial):
        self.calls.append(("getInstrumentCopy", serial))
        return InstrumentCopyLogicModule().buildForUser(username, password, serial)

    def getPluginSource(self, codeRef, version):
        return {"ok": True, "source": None}                     # the seed's bare pumpkin row ⇒ built-in

    def saveSpectrometerProfile(self, serial, deviceCodeName, calibration=None, modelName=None, styleId=None,
                                lightSourceControllerType=None):
        self.calls.append(("saveSpectrometerProfile", serial, deviceCodeName, modelName, styleId,
                           lightSourceControllerType))
        return {"ok": True}

    def saveSpectrometerSetup(self, serial, codeRef, version=None):
        self.calls.append(("saveSpectrometerSetup", serial, codeRef, version))
        return {"ok": True}

    def moveInstrumentToSerial(self, oldSerial, newSerial):
        self.calls.append(("moveInstrumentToSerial", oldSerial, newSerial))
        return {"ok": True}


class OfflineInstrumentPlugTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from nacl.signing import SigningKey
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
        trustedKeys.TRUSTED_COPY_KEYS.update(cls.trusted)       # the factory's verify reads the shipped list

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
        self.plug = FakeShellyServer().__enter__()
        self.device = LampDevice("shelly-gen2", self.plug.host, FakeShellyServer.MAC, deviceId=SERIAL)
        self.client = _InProcessClient()
        self.previousSource = PluginRegistry.offlineBundleSource

    def tearDown(self):
        self.plug.__exit__(None, None, None)
        PluginRegistry.offlineBundleSource = self.previousSource
        CurrentUserSession().logout()

    def __factory(self, store=None):
        return InstrumentFactoryLogicModule(client=self.client, plugStore=store or LampPlugStore())

    def __offline(self, device=None):
        return OfflineLoginLogicModule(locator=_Locator(device or self.device), trustedKeys=self.trusted)

    def __writeCopy(self):
        return self.__factory().write(self.device, None, "masterUserDynarex", "masterUserDynarex")

    # --- S5 factory ---
    def test_write_then_verify(self):
        text = self.__writeCopy()
        self.assertIn("✓ Instrument data written", text)
        self.assertIn("ships with the app", text)               # the bound pumpkin plugin is a built-in
        self.assertIn("spectracs_index", self.plug.kvs)
        self.assertIn("✓ Instrument data valid", self.__factory().verify(self.device, None))

    def test_write_needs_valid_credentials(self):
        text = self.__factory().write(self.device, None, "masterUserDynarex", "wrong")
        self.assertTrue(text.startswith("✗"))
        self.assertEqual({}, self.plug.kvs)

    # --- §11 passwords: default = the MAC (E11/E12), AP first (R45), shipping (R48), identify (R24) ---
    def __ha1(self, password):
        import hashlib
        return hashlib.sha256(("admin:%s:%s" % (SERIAL, password)).encode()).hexdigest()

    def __methods(self):
        return [name for name, _ in self.plug.calls]

    def test_harden_sets_the_mac_for_api_and_ap(self):
        store = LampPlugStore()
        store.saveDevice(self.device)
        store.savePassword("old", mac=self.device.mac)
        text = self.__factory(store).harden(self.device, None)
        self.assertTrue(text.startswith("✓"), text)
        self.assertEqual("off", self.plug.switchConfig["initial_state"])
        self.assertEqual(self.__ha1(FakeShellyServer.MAC), self.plug.authHa1)
        self.assertEqual({"enable": True, "is_open": False, "pass": FakeShellyServer.MAC},
                         {k: self.plug.wifi["ap"][k] for k in ("enable", "is_open", "pass")})
        self.assertIsNone(store.load(mac=self.device.mac)[1])           # the default needs no stored password
        methods = self.__methods()
        self.assertLess(methods.index("WiFi.SetConfig"), methods.index("Shelly.SetAuth"))   # AP first (R45)

    def test_change_password_sets_both_and_stores_it(self):
        store = LampPlugStore()
        self.assertTrue(self.__factory(store).changePassword(self.device, None, "short").startswith("✗"))
        self.assertIsNone(self.plug.authHa1)
        text = self.__factory(store).changePassword(self.device, None, "our-own-pw")
        self.assertTrue(text.startswith("✓"), text)
        self.assertEqual(self.__ha1("our-own-pw"), self.plug.authHa1)
        self.assertEqual("our-own-pw", self.plug.wifi["ap"]["pass"])
        self.assertEqual("our-own-pw", store.load(mac=self.device.mac)[1])

    def test_prepare_for_shipping_resets_to_the_mac_then_forgets_the_wlan(self):
        store = LampPlugStore()
        store.saveDevice(self.device)
        store.savePassword("factory-changed", mac=self.device.mac)
        factory = InstrumentFactoryLogicModule(client=self.client, plugStore=store, sleep=lambda s: None)
        text = factory.prepareForShipping(self.device, None)
        self.assertTrue(text.startswith("✓ Ready to ship"), text)
        self.assertEqual(self.__ha1(FakeShellyServer.MAC), self.plug.authHa1)
        self.assertEqual(FakeShellyServer.MAC, self.plug.wifi["ap"]["pass"])
        self.assertIsNone(self.plug.wifi["sta"]["ssid"])
        self.assertIsNone(self.plug.wifi["sta1"]["ssid"])                 # both slots (R41)
        self.assertTrue(self.plug.dark)                                   # gone from the LAN (R42)
        self.assertIsNone(store.load(mac=self.device.mac)[1])
        methods = self.__methods()
        self.assertLess(methods.index("Shelly.SetAuth"), len(methods) - 1)  # passwords before the WLAN (R48)

    def test_prepare_for_shipping_stops_when_the_password_cannot_be_reset(self):
        self.plug.password = "unknown-to-us"
        factory = InstrumentFactoryLogicModule(client=self.client, plugStore=LampPlugStore(), sleep=lambda s: None)
        self.assertTrue(factory.prepareForShipping(self.device, None).startswith("✗ Not prepared"))
        self.assertEqual("Sciens2G6971", self.plug.wifi["sta"]["ssid"])   # still on the WLAN
        self.assertFalse(self.plug.dark)

    def test_identify_blinks_briefly_restores_and_never_switches(self):
        self.plug.uiConfig = {"leds": {"mode": "power", "colors": {}}}
        factory = InstrumentFactoryLogicModule(client=self.client, plugStore=LampPlugStore(), sleep=lambda s: None)
        self.assertTrue(factory.identify(self.device, None).startswith("✓"))
        self.assertEqual(2 * InstrumentFactoryLogicModule.IDENTIFY_CYCLES + 1, self.plug.uiWrites)   # few writes
        self.assertEqual({"mode": "power", "colors": {}}, self.plug.uiConfig["leds"])                # restored
        self.assertEqual([], self.plug.callsTo("Switch.Set"))

    # --- §11.16 firmware: OTA hop by hop up to the tested target, never beyond ---
    def __updater(self):
        return InstrumentFactoryLogicModule(client=self.client, plugStore=LampPlugStore(), sleep=lambda s: None)

    def test_update_hops_up_to_the_target_and_the_copy_survives(self):
        self.__writeCopy()
        self.plug.firmware = "0.13.0"
        said = []
        text = self.__updater().updateFirmware(self.device, None, said.append)
        self.assertEqual(["1.3.3", "1.7.5"], self.plug.updates)                  # two hops, like the real plugs
        self.assertIn("✓ Updated 0.13.0 → 1.3.3", text)
        self.assertIn("✓ Updated 1.3.3 → 1.7.5", text)
        self.assertIn("✓ Instrument data valid", text)                          # verified afterwards
        self.assertTrue(said and said[0].startswith("Updating 0.13.0 → 1.3.3"))
        self.assertEqual("1.7.5", self.device.firmware)

    def test_update_stops_at_the_target(self):
        self.plug.firmware = "1.7.5"
        self.plug.updateOffers = {"1.7.5": "1.8.0"}
        text = self.__updater().updateFirmware(self.device, None)
        self.assertEqual([], self.plug.updates)
        self.assertIn("the tested version (1.7.5) or newer", text)

    def test_an_offer_beyond_the_target_is_not_installed(self):
        self.plug.firmware = "1.3.3"
        self.plug.updateOffers = {"1.3.3": "1.8.0"}
        text = self.__updater().updateFirmware(self.device, None)
        self.assertEqual([], self.plug.updates)
        self.assertIn("newer than the tested 1.7.5 — not installed", text)

    def test_no_update_offered(self):
        self.plug.firmware = "1.3.3"
        self.plug.updateOffers = {}
        self.assertIn("offers no update", self.__updater().updateFirmware(self.device, None))

    def test_version_tuples(self):
        version = InstrumentFactoryLogicModule.versionTuple
        self.assertLess(version("0.13.0"), version("1.3.3"))
        self.assertLess(version("1.3.3"), version("1.7.5"))
        self.assertEqual((1, 4, 0), version("1.4.0-beta1"))
        self.assertEqual((), version(None))

    def test_move(self):
        moved = self.__factory().moveHere(self.device, None, "old-plug-serial", "masterUserDynarex",
                                          "masterUserDynarex")
        self.assertIn("moved from old-plug-serial", moved)
        self.assertIn(("moveInstrumentToSerial", "old-plug-serial", SERIAL), self.client.calls)

    # --- S6 sync: write only on change ---
    def test_sync_restores_hardens_then_leaves_the_plug_alone(self):
        # L5: an empty, open plug of the user's own serial (new, or factory-reset) is restored and hardened with
        # the MAC (E11) on the first online login; afterwards nothing is written while nothing changed (§9.5).
        locator = _Locator(self.device, trusted=self.trusted)
        sync = PlugInstrumentSync(locator=locator, client=self.client)
        self.assertEqual("restored, hardened", sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL))
        self.assertTrue(self.plug._FakeShellyServer__deviceInfo()["auth_en"])
        before = len(self.plug.callsTo("KVS.Set")) + len(self.plug.callsTo("Script.PutCode"))
        self.assertEqual("unchanged", sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL))
        after = len(self.plug.callsTo("KVS.Set")) + len(self.plug.callsTo("Script.PutCode"))
        self.assertEqual(before, after)

    def test_sync_repairs_a_factory_reset_plug(self):
        locator = _Locator(self.device, trusted=self.trusted)
        sync = PlugInstrumentSync(locator=locator, client=self.client)
        sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL)
        self.plug.kvs.clear(); self.plug.scripts.clear(); self.plug.authHa1 = None      # the 10 s button press
        reported = []
        self.assertEqual("restored, hardened",
                         sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL, onResult=reported.append))
        self.assertEqual(["restored, hardened"], reported)

    def test_sync_leaves_a_locked_plug_alone(self):
        self.plug.password = "not-ours"
        sync = PlugInstrumentSync(locator=_Locator(self.device, trusted=self.trusted), client=self.client)
        self.assertIn("locked", sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL))
        self.assertEqual({}, self.plug.kvs)

    def test_sync_ignores_another_plug(self):
        sync = PlugInstrumentSync(locator=_Locator(self.device), client=self.client)
        self.assertTrue(sync.sync("elpUser", "elpUser", "ELP-0001").startswith("no plug"))
        self.assertEqual({}, self.plug.kvs)

    # --- S7 offline login ---
    def test_offline_login_from_the_plug(self):
        self.__writeCopy()
        result = self.__offline().login("masterUserDynarex", "masterUserDynarex")
        self.assertTrue(result["ok"], result["message"])
        self.assertTrue(result["offline"])
        self.assertEqual("Dynarex", result["spectrometerDevice"])
        self.assertEqual(SERIAL, result["registeredSerial"])
        self.assertIn("MASTER_USER", result["roles"])
        self.assertIsNotNone(PluginRegistry.offlineBundleSource)

    def test_offline_login_only_for_the_registered_users(self):
        # E16: a master of another instrument is not on this plug (Q11 withdrawn) ⇒ online only.
        self.__writeCopy()
        self.assertEqual("invalid credentials",
                         self.__offline().login("masterUserExakta", "masterUserExakta")["message"])
        self.assertEqual("SHELLY_GEN2",
                         self.__offline().login("masterUserDynarex", "masterUserDynarex")["lightSourceController"])

    def test_offline_login_refusals(self):
        self.__writeCopy()
        self.assertEqual("invalid credentials", self.__offline().login("masterUserDynarex", "wrong")["message"])
        self.assertEqual("invalid credentials", self.__offline().login("elpUser", "elpUser")["message"])

    def test_offline_login_without_copy_or_plug(self):
        self.assertEqual(OfflineLoginLogicModule.NO_COPY,
                         self.__offline().login("masterUserDynarex", "masterUserDynarex")["message"])
        noPlug = OfflineLoginLogicModule(locator=_Locator(None), trustedKeys=self.trusted)
        self.assertEqual(OfflineLoginLogicModule.NO_PLUG, noPlug.login("masterUserDynarex", "x")["message"])

    def test_copy_on_the_wrong_plug_is_refused(self):
        self.__writeCopy()
        otherPlug = LampDevice("shelly-gen2", self.plug.host, FakeShellyServer.MAC,
                               deviceId="shellyplusplugs-000000000000")
        result = self.__offline(otherPlug).login("masterUserDynarex", "masterUserDynarex")
        self.assertFalse(result["ok"])
        self.assertIn("not signed for this plug", result["message"])

    def test_offline_session_installs_the_profile_without_the_server(self):
        import sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient as clientModule
        from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import \
            ActiveSpectrometerProfileLogicModule
        self.__writeCopy()
        CurrentUserSession().login(self.__offline().login("masterUserDynarex", "masterUserDynarex"))
        self.assertTrue(CurrentUserSession().isOffline())
        original = clientModule.SpectracsPyServerClient.resolveInstrumentBySerial
        clientModule.SpectracsPyServerClient.resolveInstrumentBySerial = \
            lambda self, serial: self.fail("must not call the server offline")
        try:
            self.assertTrue(ActiveSpectrometerProfileLogicModule().installFromSession())
        finally:
            clientModule.SpectracsPyServerClient.resolveInstrumentBySerial = original
        CurrentUserSession().logout()
        self.assertFalse(CurrentUserSession().isOffline())


class MoveToSerialServerTest(unittest.TestCase):
    """S8 on the server side: the profile (and its calibration) and the bound users move to the new serial."""

    def test_move_and_back(self):
        from sciens.spectracs.logic.instrument.InstrumentAuthoringLogicModule import InstrumentAuthoringLogicModule
        from sciens.spectracs.logic.persistence.database.spectrometerSetup.PersistSpectrometerSetupLogicModule import \
            PersistSpectrometerSetupLogicModule
        from sciens.spectracs.logic.persistence.database.user.PersistUserLogicModule import PersistUserLogicModule
        UserSeedLogicModule().seed()
        module, newSerial = InstrumentAuthoringLogicModule(), "shellyplusplugs-aaaaaaaaaaaa"
        try:
            result = module.moveToSerial(SERIAL, newSerial)
            self.assertTrue(result["ok"], result["message"])
            self.assertIn("masterUserDynarex", result["movedUsers"])
            self.assertIsNotNone(PersistSpectrometerSetupLogicModule().resolveBySerial(newSerial))
            self.assertEqual(newSerial, PersistUserLogicModule().findUserByUsername("masterUserDynarex").registeredSerial)
            self.assertFalse(module.moveToSerial(SERIAL, newSerial)["ok"])           # the old serial is gone
        finally:
            module.moveToSerial(newSerial, SERIAL)
        self.assertIsNotNone(PersistSpectrometerSetupLogicModule().resolveBySerial(SERIAL))


class SpectrometerTripleServerTest(unittest.TestCase):
    """Create on server: the spectrometer is (model, camera, style); a new combination becomes a new row."""

    SERIAL = "shellyplusplugs-bbbbbbbbbbbb"

    def test_existing_and_new_combination(self):
        from sciens.spectracs.logic.instrument.InstrumentAuthoringLogicModule import InstrumentAuthoringLogicModule
        from sciens.spectracs.model.databaseEntity.DbServerBase import server_session_factory
        from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
        from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
        UserSeedLogicModule().seed()
        module, session = InstrumentAuthoringLogicModule(), server_session_factory()
        created = []
        try:
            known = module.saveProfile(self.SERIAL, "Dynarex", None, "InLight", "GREEN_GOLD")
            self.assertTrue(known["ok"], known["message"] if "message" in known else "")
            self.assertFalse(known["spectrometerCreated"])
            new = module.saveProfile(self.SERIAL, "Dynarex", None, "InVision", "GREEN_GOLD")
            self.assertTrue(new["spectrometerCreated"])
            profile = session.query(SpectrometerProfile).filter(SpectrometerProfile.serial == self.SERIAL).first()
            created.append(profile.spectrometer)
            self.assertEqual(("InVision", "Dynarex", "GREEN_GOLD"), (
                profile.spectrometer.modelName, profile.spectrometer.spectrometerSensor.codeName,
                profile.spectrometer.spectrometerStyle.styleId))
            again = module.saveProfile(self.SERIAL, "Dynarex", None, "InVision", "GREEN_GOLD")
            self.assertFalse(again["spectrometerCreated"])
            self.assertFalse(module.saveProfile(self.SERIAL, "Dynarex", None, "InLight", "NO_SUCH")["ok"])
        finally:
            profile = session.query(SpectrometerProfile).filter(SpectrometerProfile.serial == self.SERIAL).first()
            if profile is not None:
                calibration = profile.spectrometerCalibrationProfile
                session.delete(profile)
                if calibration is not None:
                    session.delete(calibration)
            for spectrometer in created:
                session.delete(session.get(Spectrometer, spectrometer.id))
            session.commit()


class InstrumentPlugPageTest(unittest.TestCase):
    """The factory page offscreen: masters only, buttons follow the found plug."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        CurrentUserSession().logout()

    def __page(self):
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import InstrumentPlugViewModule
        page = InstrumentPlugViewModule()
        page.initialize()
        page._rows = {SERIAL: {"serial": SERIAL, "modelName": "InLight", "deviceCodeName": "Dynarex",
                               "pluginCodeRef": "x.PumpkinOilPlugin"}}            # no server in this test
        return page

    def __choose(self, page, label):
        from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugCandidate
        page.candidates = [PlugCandidate(LampDevice("shelly-gen2", "127.0.0.1:1", FakeShellyServer.MAC,
                                                    deviceId=SERIAL), label)]
        page.plugCombo.addItem(page.candidates[0].describe())
        page.plugCombo.setCurrentIndex(0)

    def test_page_gates_on_master_and_plug(self):
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import InstrumentPlugViewModule
        page = self.__page()
        page.refresh()
        self.assertFalse(page.searchButton.isEnabled())                          # logged out
        for button in (page.searchButton, page.identifyButton, page.addButton, page.hardenButton, page.writeButton,
                       page.verifyButton, page.shipButton, page.moveButton, page.setupButton):
            self.assertTrue(button.toolTip())
        self.assertFalse(hasattr(page, "createButton"))                          # E4: created on the setup page
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"]})
        page.refresh()
        self.assertTrue(page.searchButton.isEnabled())
        self.assertFalse(page.writeButton.isEnabled())                           # no plug chosen yet
        self.__choose(page, "registered")
        page.refresh()
        for button in (page.writeButton, page.hardenButton, page.shipButton, page.identifyButton, page.setupButton):
            self.assertTrue(button.isEnabled())
        self.assertFalse(page.moveButton.isEnabled())                            # it already has a setup
        page._rows = {}                                                          # a plug of no instrument yet
        page.refresh()
        self.assertTrue(page.moveButton.isEnabled())
        self.assertFalse(page.setupButton.isEnabled())
        page._rows = {SERIAL: {"serial": SERIAL, "modelName": "InLight", "deviceCodeName": "Dynarex",
                               "pluginCodeRef": "x.PumpkinOilPlugin"}}
        page.refresh()
        self.assertEqual(SERIAL, page.serialValue.text())
        self.assertIn("InLight-Dynarex", page.setupValue.text())                # which setup it belongs to
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"], "offline": True})
        page.refresh()
        # Offline: plug and serial still shown, Search + Identify + Verify work, the instrument-changing steps do not.
        self.assertEqual(SERIAL, page.serialValue.text())
        self.assertIn(InstrumentPlugViewModule.OFFLINE_NOTE, page.setupValue.text())
        for button in (page.searchButton, page.verifyButton, page.identifyButton):
            self.assertTrue(button.isEnabled())
        for button in (page.hardenButton, page.writeButton, page.shipButton, page.moveButton):
            self.assertFalse(button.isEnabled())

    def test_firmware_button_only_below_the_target(self):
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"]})
        page = self.__page()
        self.__choose(page, "registered")
        page.candidates[0].device.firmware = "0.13.0"
        page.refresh()
        self.assertTrue(page.firmwareButton.isEnabled())
        self.assertIn("older than the tested 1.7.5", page.firmwareValue.text())
        page.candidates[0].device.firmware = "1.7.5"
        page.refresh()
        self.assertFalse(page.firmwareButton.isEnabled())
        self.assertEqual("1.7.5 ✓", page.firmwareValue.text())

    def test_a_locked_plug_is_shown_but_not_acted_on(self):
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"]})
        page = self.__page()
        self.__choose(page, "locked")
        page.refresh()
        self.assertEqual(SERIAL, page.serialValue.text())
        for button in (page.writeButton, page.hardenButton, page.shipButton, page.identifyButton, page.verifyButton):
            self.assertFalse(button.isEnabled())


class SpectrometerSetupPageTest(unittest.TestCase):
    """L3 (§11, E3/R35): the setup page offscreen — the triple, the light source, the serial from the plug."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        UserSeedLogicModule().seed()

    def __page(self):
        from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupViewModule import \
            SpectrometerSetupViewModule
        page = SpectrometerSetupViewModule()
        page.initialize()
        return page

    def test_form_order_and_defaults_for_a_new_instrument(self):
        from PySide6.QtWidgets import QFormLayout, QLabel
        page = self.__page()
        labels = [w.text() for w in page.findChildren(QLabel)]
        order = [labels.index(name) for name in ("Model", "Camera", "Style", "Light source", "Serial", "Plugin",
                                                 "User")]
        self.assertEqual(sorted(order), order)                                   # R35
        self.assertEqual("SHELLY_GEN2", page.lightSourceCombo.currentData())     # a new box: a Shelly
        self.assertTrue(page.serial.isReadOnly())                                # ⇒ the serial comes from the plug
        self.assertTrue(page.findPlugButton.isEnabled())

    def test_manual_lamp_means_a_typed_serial(self):
        page = self.__page()
        page.lightSourceCombo.setCurrentIndex(page.lightSourceCombo.findData("NONE"))
        self.assertFalse(page.serial.isReadOnly())
        self.assertFalse(page.findPlugButton.isEnabled())

    def test_an_existing_setup_shows_its_triple_and_keeps_its_serial(self):
        page = self.__page()
        page.setModel({"serial": SERIAL, "modelName": "InLight", "deviceCodeName": "Dynarex", "styleId": "GREEN_GOLD",
                       "lightSourceController": "SHELLY_GEN2"})
        self.assertEqual(("InLight", "Dynarex", "GREEN_GOLD"), (page.modelCombo.currentData(),
                         page.cameraCombo.currentData(), page.styleCombo.currentData()))
        self.assertEqual(SERIAL, page.serial.text())
        self.assertTrue(page.serial.isReadOnly())
        self.assertFalse(page.findPlugButton.isEnabled())                        # the key is fixed once created

    def test_picking_a_plug_that_has_a_setup_opens_it(self):
        from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugCandidate
        import sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupListViewModule as listModule
        page = self.__page()
        existing = {"serial": SERIAL, "modelName": "InLight", "deviceCodeName": "Dynarex", "styleId": "GREEN_GOLD",
                    "lightSourceController": "SHELLY_GEN2"}
        original = listModule.SpectrometerSetupListViewModule.rowForSerial
        listModule.SpectrometerSetupListViewModule.rowForSerial = staticmethod(lambda serial: existing)
        try:
            page._SpectrometerSetupViewModule__pickPlug(PlugCandidate(
                LampDevice("shelly-gen2", "127.0.0.1:1", FakeShellyServer.MAC, deviceId=SERIAL), "registered"))
        finally:
            listModule.SpectrometerSetupListViewModule.rowForSerial = staticmethod(original)
        self.assertEqual(SERIAL, page.dto["serial"])                             # opened, not a second setup
        self.assertIn("already has a setup", page.plugHintLabel.text())

if __name__ == "__main__":
    unittest.main()
