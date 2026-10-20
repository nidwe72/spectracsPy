"""
P6 of SPEC_lamp_switch.md §6 — the LampPlug table: its Alembic migration up/down on a scratch SQLite, and the
DB store's one-row rule (a new MAC replaces the plug and drops its password; the same MAC only updates the host).
Never touches the developer's real spectracsPy.db: the migration runs on an in-memory engine and the store's
session factory is pointed at a scratch one.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_lamp_plug_persistence.py -q
"""
import importlib.util
import os
import unittest

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.orm import sessionmaker

import sciens.spectracs.logic.lamp.LampPlugDbStore as storeModule
from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.model.databaseEntity.application.LampPlug import LampPlug

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "..", "spectracsPy-model", "alembic", "app", "versions",
                         "63efd411276f_lamp_plug.py")


def loadMigration():
    spec = importlib.util.spec_from_file_location("lamp_plug_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LampPlugMigrationTest(unittest.TestCase):

    def test_upgrade_then_downgrade(self):
        migration = loadMigration()
        self.assertEqual("cb8c2942a6bc", migration.down_revision)
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
            columns = {column["name"] for column in sa.inspect(connection).get_columns("lamp_plug")}
            self.assertEqual({"id", "driverName", "host", "mac", "model", "deviceId", "password"}, columns)
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            self.assertNotIn("lamp_plug", sa.inspect(connection).get_table_names())


class LampPlugDbStoreTest(unittest.TestCase):

    def setUp(self):
        engine = sa.create_engine("sqlite://")
        LampPlug.__table__.create(engine)
        self.original = storeModule.save_session
        storeModule.save_session = sessionmaker(bind=engine, expire_on_commit=False)
        self.store = storeModule.LampPlugDbStore()

    def tearDown(self):
        storeModule.save_session = self.original

    def test_empty(self):
        self.assertEqual((None, None), self.store.load())

    def test_same_mac_keeps_the_password_and_follows_the_host(self):
        self.store.saveDevice(LampDevice("shelly-gen2", "192.168.1.123", "E86BEAE3CB60", model="PlusPlugS"))
        self.store.savePassword("geheim")
        self.store.saveDevice(LampDevice("shelly-gen2", "192.168.1.140", "E86BEAE3CB60", model="PlusPlugS"))
        device, password = self.store.load()
        self.assertEqual("192.168.1.140", device.host)
        self.assertEqual("geheim", password)

    def test_a_second_plug_keeps_both_passwords(self):
        # SPEC_shelly_instrument_memory.md R33: one row per MAC — meeting a second plug forgets nothing.
        self.store.saveDevice(LampDevice("shelly-gen2", "192.168.1.123", "E86BEAE3CB60",
                                         deviceId="shellyplusplugs-e86beae3cb60"))
        self.store.savePassword("geheim", mac="E86BEAE3CB60")
        self.store.saveDevice(LampDevice("shelly-gen2", "192.168.1.121", "E465B8B6B4F8",
                                         deviceId="shellyplusplugs-e465b8b6b4f8"))
        self.store.savePassword("anderes", mac="E4:65:B8:B6:B4:F8")
        self.assertEqual(2, len(self.store.loadAll()))
        self.assertEqual("geheim", self.store.load(deviceId="shellyplusplugs-e86beae3cb60")[1])
        self.assertEqual("anderes", self.store.load(mac="E465B8B6B4F8")[1])
        self.store.savePassword(None, mac="E465B8B6B4F8")              # back to the default (the MAC)
        self.assertIsNone(self.store.load(mac="E465B8B6B4F8")[1])
        self.assertEqual("geheim", self.store.load(mac="E86BEAE3CB60")[1])
        self.assertEqual((None, None), self.store.load(deviceId="shellyplusplugs-000000000000"))

if __name__ == "__main__":
    unittest.main()
