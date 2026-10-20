"""L1 (SPEC_shelly_instrument_memory.md §11.2/§11.13): the LightSourceController on the spectrometer profile.

  - the server migration b7c41e09d2a5 on a pre-L1 DB: seeds NONE + SHELLY_GEN2, applies the one-time data rule R34
    (a `shelly…` serial ⇒ SHELLY_GEN2, any other ⇒ NONE), and copes with a table create_all already built;
  - saveProfile sets / keeps the controller, refuses an unknown type; a move onto a plug makes it SHELLY_GEN2;
  - the resolve bundle (and so login) carries it.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \\
        ./venv/bin/python -m pytest tests/test_light_source_controller.py -q

NOTE: the authoring tests write to the real server DB in appdata (like test_offline_instrument_plug) under serials of
their own and remove them again."""
import os
import tempfile
import unittest

import sqlalchemy as sa
from alembic import command

from sciens.spectracs.logic.instrument.InstrumentAuthoringLogicModule import InstrumentAuthoringLogicModule
from sciens.spectracs.logic.instrument.InstrumentLogicModule import InstrumentLogicModule
from sciens.spectracs.logic.model.util.LightSourceControllerUtil import LightSourceControllerUtil
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule
from sciens.spectracs.model.databaseEntity.DatabaseInitializer import _config
from sciens.spectracs.model.databaseEntity.DbServerBase import server_session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile

PRE_L1 = "405d2ce2cec1"


class LightSourceControllerMigrationTest(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db", prefix="preL1_")
        os.close(handle)
        self.engine = sa.create_engine("sqlite:///" + self.path)

    def tearDown(self):
        self.engine.dispose()
        os.remove(self.path)

    def __migrate(self, revision):
        cfg = _config("server")
        with self.engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, revision)

    def __preL1WithProfiles(self):
        self.__migrate(PRE_L1)
        with self.engine.begin() as connection:
            for id_, serial in (("p1", "shellyplusplugs-e86beae3cb60"), ("p2", "ELP-0001"), ("p3", "TEST-0001")):
                connection.execute(sa.text("insert into spectrometer_profile (id, serial) values (:i, :s)"),
                                   {"i": id_, "s": serial})

    def __controllers(self):
        with self.engine.connect() as connection:
            return dict(connection.execute(sa.text(
                "select p.serial, c.controllerType from spectrometer_profile p "
                "join light_source_controller c on c.id = p.lightSourceControllerId")).fetchall())

    def test_seeds_and_applies_the_serial_rule(self):
        self.__preL1WithProfiles()
        self.__migrate("head")
        self.assertEqual({"shellyplusplugs-e86beae3cb60": "SHELLY_GEN2", "ELP-0001": "NONE", "TEST-0001": "NONE"},
                         self.__controllers())
        with self.engine.connect() as connection:
            types = {r[0] for r in connection.execute(sa.text("select controllerType from light_source_controller"))}
        self.assertEqual({"NONE", "SHELLY_GEN2"}, types)

    def test_copes_with_a_table_create_all_already_built(self):
        # server_session_factory() runs create_all before any session ⇒ the table can exist before the migration.
        self.__preL1WithProfiles()
        with self.engine.begin() as connection:
            connection.execute(sa.text("create table light_source_controller (id varchar primary key, "
                                       "controllerType varchar unique, name varchar, description varchar)"))
        self.__migrate("head")
        self.assertEqual("SHELLY_GEN2", self.__controllers()["shellyplusplugs-e86beae3cb60"])


class LightSourceControllerAuthoringTest(unittest.TestCase):
    NEW_SERIAL = "test-l1-profile"
    PLUG_SERIAL = "shellyplusplugs-l1test00000"

    @classmethod
    def setUpClass(cls):
        UserSeedLogicModule().seed()

    def tearDown(self):
        session = server_session_factory()
        for serial in (self.NEW_SERIAL, self.PLUG_SERIAL):
            for profile in session.query(SpectrometerProfile).filter(SpectrometerProfile.serial == serial).all():
                session.delete(profile)
        session.commit()

    def __type(self, serial):
        profile = server_session_factory().query(SpectrometerProfile).filter(
            SpectrometerProfile.serial == serial).first()
        return LightSourceControllerUtil.typeOf(profile)

    def test_new_profile_defaults_to_none_and_keeps_a_set_type(self):
        module = InstrumentAuthoringLogicModule()
        self.assertTrue(module.saveProfile(self.NEW_SERIAL, "Dynarex", None, "InLight", "GREEN_GOLD")["ok"])
        self.assertEqual("NONE", self.__type(self.NEW_SERIAL))
        self.assertTrue(module.saveProfile(self.NEW_SERIAL, "Dynarex", None, "InLight", "GREEN_GOLD",
                                           "SHELLY_GEN2")["ok"])
        self.assertEqual("SHELLY_GEN2", self.__type(self.NEW_SERIAL))
        self.assertTrue(module.saveProfile(self.NEW_SERIAL, "Dynarex", None, "InLight", "GREEN_GOLD")["ok"])
        self.assertEqual("SHELLY_GEN2", self.__type(self.NEW_SERIAL))           # None keeps what is set

    def test_unknown_type_is_refused(self):
        result = InstrumentAuthoringLogicModule().saveProfile(self.NEW_SERIAL, "Dynarex", None, "InLight",
                                                              "GREEN_GOLD", "RELAY")
        self.assertFalse(result["ok"])
        self.assertIn("unknown light source controller", result["message"])

    def test_a_move_onto_a_plug_makes_it_shelly(self):
        module = InstrumentAuthoringLogicModule()
        self.assertTrue(module.saveProfile(self.NEW_SERIAL, "Dynarex", None, "InLight", "GREEN_GOLD")["ok"])
        self.assertTrue(module.moveToSerial(self.NEW_SERIAL, self.PLUG_SERIAL)["ok"])
        self.assertEqual("SHELLY_GEN2", self.__type(self.PLUG_SERIAL))

    def test_the_bundle_carries_it(self):
        self.assertEqual("SHELLY_GEN2",
                         InstrumentLogicModule().resolveBundle(UserSeedLogicModule.DYNAREX_SERIAL)["lightSourceController"])
        self.assertEqual("NONE",
                         InstrumentLogicModule().resolveBundle(UserSeedLogicModule.DEMO_SERIAL)["lightSourceController"])


if __name__ == "__main__":
    unittest.main()
