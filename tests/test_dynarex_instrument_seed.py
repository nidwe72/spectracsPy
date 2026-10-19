"""
S1 of SPEC_shelly_instrument_memory.md (§7.4): the ammo box is seeded as a dev instrument
(InLight-Dynarex-GreenGold under the plug's device id) with masterUserDynarex bound to it, analogous to
masterUserExakta. Seeds twice (idempotent), then checks the catalog rows, the setup and the login.

NOTE: exercises the real server DB in appdata, exactly as server startup does (like test_plugin_binding_and_seed).
"""
import unittest

from sciens.spectracs.logic.model.util.SpectrometerSensorChipUtil import SpectrometerSensorChipUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.persistence.database.spectrometerSetup.PersistSpectrometerSetupLogicModule import \
    PersistSpectrometerSetupLogicModule
from sciens.spectracs.logic.persistence.database.user.PersistUserLogicModule import PersistUserLogicModule
from sciens.spectracs.logic.user.LoginLogicModule import LoginLogicModule
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType


class DynarexInstrumentSeedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        UserSeedLogicModule().seed()
        UserSeedLogicModule().seed()  # idempotent: a second run creates nothing new

    def test_catalog_rows_exist_once(self):
        chips = SpectrometerSensorChipUtil().getPersistentSpectrometerSensorChips().values()
        self.assertEqual(1, sum(1 for c in chips if (c.vendorName, c.productName) == ("Orbbec", "0529")))

        sensors = [s for s in SpectrometerSensorUtil().getPersistedSpectrometerSensors().values()
                   if s.codeName == "Dynarex"]
        self.assertEqual(1, len(sensors))
        self.assertEqual("2bc5_0529", SpectrometerSensorUtil().getHardwareId(sensors[0]))

        inLight = [s for s in SpectrometerUtil().getPersistentSpectrometers().values()
                   if s.modelName == "InLight" and s.spectrometerSensor.codeName == "Dynarex"]
        self.assertEqual(1, len(inLight))
        self.assertEqual("GreenGold", inLight[0].spectrometerStyle.styleName)

    def test_the_old_inlight_automat_row_stays(self):
        names = [SpectrometerUtil().getName(s) for s in SpectrometerUtil().getPersistentSpectrometers().values()]
        self.assertIn("SPECTRACS InLight Automat GREEN_GOLD", names)
        self.assertIn("SPECTRACS InLight Dynarex GREEN_GOLD", names)

    def test_setup_under_the_plug_serial(self):
        setup = PersistSpectrometerSetupLogicModule().resolveBySerial(UserSeedLogicModule.DYNAREX_SERIAL)
        self.assertIsNotNone(setup)
        self.assertEqual(UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"], setup.plugin.codeRef)

    def test_master_user_is_bound(self):
        persist = PersistUserLogicModule()
        user = persist.findUserByUsername("masterUserDynarex")
        self.assertIsNotNone(user)
        self.assertEqual(UserSeedLogicModule.DYNAREX_SERIAL, user.registeredSerial)
        self.assertIn(UserRoleType.MASTER_USER.value, persist.getRoleNamesForUser(user))

    def test_login_carries_the_box(self):
        result = LoginLogicModule().login("masterUserDynarex", "masterUserDynarex")
        self.assertTrue(result["ok"])
        self.assertEqual("Dynarex", result["spectrometerDevice"])
        self.assertEqual(UserSeedLogicModule.DYNAREX_SERIAL, result["registeredSerial"])
        self.assertIsNone(result["calibration"])  # authored on the box later (camera spec P5)


if __name__ == "__main__":
    unittest.main()
