"""
Track B (B1-B3) — server-side plugin registry + AppUser config binding + seed (SPEC_pumpkin_integration.md
B.1/B.1a). Seeds idempotently, then asserts: the pumpkin DbPlugin row exists, pumpkinTestUser is bound to
it + the "Virtuax" device, login carries the binding through, and CurrentUserSession holds it.

NOTE: exercises the real server DB (spectracsPyServer.db in appdata), exactly as server startup does; the
seed is idempotent.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_plugin_binding_and_seed.py -q
"""
import unittest

from sciens.spectracs.logic.persistence.database.plugin.PersistPluginLogicModule import PersistPluginLogicModule
from sciens.spectracs.logic.persistence.database.user.PersistUserLogicModule import PersistUserLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.user.LoginLogicModule import LoginLogicModule
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule


class PluginBindingSeedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        UserSeedLogicModule().seed()

    def test_pumpkin_plugin_row_seeded(self):
        dbPlugin = PersistPluginLogicModule().findPluginByCodeRef(
            UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"])
        self.assertIsNotNone(dbPlugin)
        self.assertEqual(dbPlugin.title, "Pumpkin-seed-oil colour QM")

    def test_pumpkin_test_user_is_bound(self):
        # Binding is per-SERIAL now (SPEC_connection_and_calibration_ux): AppUser carries registeredSerial;
        # the device + plugin resolve THROUGH the serial at login, not via removed AppUser.pluginId columns.
        user = PersistUserLogicModule().findUserByUsername("pumpkinTestUser")
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.registeredSerial)

    def test_login_carries_the_binding(self):
        result = LoginLogicModule().login("pumpkinTestUser", "pumpkinTestUser")
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["pluginCodeRef"])
        # B5.4: the EXACT bound version travels too (the seed binds the "1.0" row).
        self.assertEqual(result["pluginVersion"], UserSeedLogicModule.PUMPKIN_PLUGIN["version"])
        self.assertEqual(result["spectrometerDevice"], "Virtuax")

    def test_current_user_session_holds_the_binding(self):
        CurrentUserSession().login(LoginLogicModule().login("pumpkinTestUser", "pumpkinTestUser"))
        self.assertIsNotNone(CurrentUserSession().getPluginCodeRef())
        self.assertEqual(CurrentUserSession().getPluginVersion(),
                         UserSeedLogicModule.PUMPKIN_PLUGIN["version"])
        self.assertEqual(CurrentUserSession().getSpectrometerDevice(), "Virtuax")

    def test_bad_credentials_still_return_binding_keys(self):
        result = LoginLogicModule().login("pumpkinTestUser", "wrong")
        self.assertFalse(result["ok"])
        self.assertIsNone(result["pluginCodeRef"])
        self.assertIsNone(result["pluginVersion"])

    def test_saveSetup_keys_on_the_exact_version(self):
        # B5.3 (F4): binding with an explicit (codeRef, version) resolves the exact seeded row; a version that
        # does not exist is refused rather than silently binding an arbitrary `.first()` row. Reuses the
        # seeded "1.0" row — creates nothing.
        from sciens.spectracs.logic.instrument.InstrumentAuthoringLogicModule import InstrumentAuthoringLogicModule
        codeRef = UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"]
        version = UserSeedLogicModule.PUMPKIN_PLUGIN["version"]
        ok = InstrumentAuthoringLogicModule().saveSetup(UserSeedLogicModule.DEMO_SERIAL, codeRef, version)
        self.assertTrue(ok["ok"])
        missing = InstrumentAuthoringLogicModule().saveSetup(
            UserSeedLogicModule.DEMO_SERIAL, codeRef, "9.9.9-nope")
        self.assertFalse(missing["ok"])


if __name__ == "__main__":
    unittest.main()
