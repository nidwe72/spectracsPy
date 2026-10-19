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
    def __init__(self, device, password=None):
        self.device, self.password = device, password

    def find(self, discover=True):
        return self.device, self.password


class _InProcessClient:
    """The server calls the factory and the sync make, answered in-process (no Pyro)."""

    def __init__(self):
        self.calls = []

    def getInstrumentCopy(self, username, password, serial):
        self.calls.append(("getInstrumentCopy", serial))
        return InstrumentCopyLogicModule().buildForUser(username, password, serial)

    def getPluginSource(self, codeRef, version):
        return {"ok": True, "source": None}                     # the seed's bare pumpkin row ⇒ built-in

    def saveSpectrometerProfile(self, serial, deviceCodeName, calibration=None, modelName=None, styleId=None):
        self.calls.append(("saveSpectrometerProfile", serial, deviceCodeName, modelName, styleId))
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

    def test_harden_sets_password_and_safe_default(self):
        os.environ[InstrumentFactoryLogicModule.STANDARD_PASSWORD_ENV] = "standard-pw"
        try:
            store = LampPlugStore()
            store.saveDevice(self.device)
            text = self.__factory(store).harden(self.device, None)
        finally:
            os.environ.pop(InstrumentFactoryLogicModule.STANDARD_PASSWORD_ENV)
        self.assertTrue(text.startswith("✓"), text)
        self.assertEqual("off", self.plug.switchConfig["initial_state"])
        self.assertIsNotNone(self.plug.authHa1)
        self.assertEqual("standard-pw", store.load()[1])

    def test_harden_without_a_standard_password_refuses(self):
        os.environ.pop(InstrumentFactoryLogicModule.STANDARD_PASSWORD_ENV, None)
        os.environ[InstrumentFactoryLogicModule.STANDARD_PASSWORD_ENV + "_FILE"] = "/nonexistent"
        try:
            self.assertTrue(self.__factory().harden(self.device, None).startswith("✗"))
        finally:
            os.environ.pop(InstrumentFactoryLogicModule.STANDARD_PASSWORD_ENV + "_FILE")
        self.assertIsNone(self.plug.authHa1)

    def test_create_on_server_and_move(self):
        codeRef = UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"]
        self.assertTrue(self.__factory().createOnServer(SERIAL, "InLight", "Dynarex", "GREEN_GOLD", codeRef,
                                                        "1.0").startswith("✓"))
        self.assertIn(("saveSpectrometerProfile", SERIAL, "Dynarex", "InLight", "GREEN_GOLD"), self.client.calls)
        moved = self.__factory().moveHere(self.device, None, "old-plug-serial", "masterUserDynarex",
                                          "masterUserDynarex")
        self.assertIn("moved from old-plug-serial", moved)
        self.assertIn(("moveInstrumentToSerial", "old-plug-serial", SERIAL), self.client.calls)

    # --- S6 sync: write only on change ---
    def test_sync_writes_once_then_leaves_the_plug_alone(self):
        sync = PlugInstrumentSync(locator=_Locator(self.device), client=self.client)
        self.assertEqual("written", sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL))
        before = len(self.plug.callsTo("KVS.Set")) + len(self.plug.callsTo("Script.PutCode"))
        self.assertEqual("unchanged", sync.sync("masterUserDynarex", "masterUserDynarex", SERIAL))
        after = len(self.plug.callsTo("KVS.Set")) + len(self.plug.callsTo("Script.PutCode"))
        self.assertEqual(before, after)

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

    def test_offline_login_for_every_master(self):
        self.__writeCopy()
        self.assertTrue(self.__offline().login("masterUserExakta", "masterUserExakta")["ok"])

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

    def test_page_gates_on_master_and_plug(self):
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import InstrumentPlugViewModule
        page = InstrumentPlugViewModule()
        page.initialize()
        page.refresh()
        self.assertFalse(page.findButton.isEnabled())                            # logged out
        for button in (page.findButton, page.hardenButton, page.createButton, page.writeButton,
                       page.verifyButton, page.moveButton):
            self.assertTrue(button.toolTip())
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"]})
        page.refresh()
        self.assertTrue(page.findButton.isEnabled())
        self.assertFalse(page.writeButton.isEnabled())                           # no plug yet
        page.device = LampDevice("shelly-gen2", "127.0.0.1:1", FakeShellyServer.MAC, deviceId=SERIAL)
        page.refresh()
        self.assertTrue(page.writeButton.isEnabled())
        self.assertEqual(SERIAL, page.serialValue.text())
        CurrentUserSession().login({"ok": True, "userId": "m", "username": "masterUserDynarex",
                                    "roles": ["MASTER_USER"], "offline": True})
        page.refresh()
        # Offline: plug and serial still shown, Find + Verify work, the four instrument-changing steps do not.
        self.assertEqual(SERIAL, page.serialValue.text())
        self.assertIn(InstrumentPlugViewModule.OFFLINE_NOTE, page.plugValue.text())
        self.assertTrue(page.findButton.isEnabled())
        self.assertTrue(page.verifyButton.isEnabled())
        for button in (page.hardenButton, page.createButton, page.writeButton, page.moveButton):
            self.assertFalse(button.isEnabled())


if __name__ == "__main__":
    unittest.main()
