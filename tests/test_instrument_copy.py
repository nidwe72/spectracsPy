"""
S2 + S3 of SPEC_shelly_instrument_memory.md: the server builds a signed SQLite copy of one instrument (+ the users
who may log in offline), the app reads it back into exactly the online login bundle, and refuses every copy it
must not use. Uses a throw-away signing key (env SPECTRACS_INSTRUMENT_COPY_KEY), never the real one.

NOTE: builds from the real server DB in appdata, seeded like server startup (as test_plugin_binding_and_seed).
"""
import base64
import bz2
import os
import sqlite3
import tempfile
import unittest

from sciens.spectracs.logic.instrument import InstrumentCopySigner
from sciens.spectracs.logic.instrument.InstrumentCopyLogicModule import InstrumentCopyLogicModule
from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader, InstrumentCopyRefused
from sciens.spectracs.logic.instrument.InstrumentLogicModule import InstrumentLogicModule
from sciens.spectracs.logic.security.InstrumentCopySignatureUtil import fingerprint, sha256hex
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule
from sciens.spectracs.model.databaseEntity.DatabaseInitializer import getServerScriptHead

SERIAL = UserSeedLogicModule.DYNAREX_SERIAL


class InstrumentCopyTest(unittest.TestCase):

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
        cls.entry = InstrumentCopyLogicModule().build(SERIAL)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.keyFile)
        if cls.previousKey is None:
            os.environ.pop("SPECTRACS_INSTRUMENT_COPY_KEY", None)
        else:
            os.environ["SPECTRACS_INSTRUMENT_COPY_KEY"] = cls.previousKey

    def __read(self, entry=None, serial=SERIAL, trusted=None):
        return InstrumentCopyReader().read(entry or self.entry, serial, trusted or self.trusted)

    # --- S2 builder ---
    def test_build_is_signed_and_small(self):
        self.assertTrue(self.entry["ok"], self.entry["message"])
        self.assertEqual(getServerScriptHead(), self.entry["revision"])
        self.assertLess(len(self.entry["data"]), 64000)        # one script slot (§4.6)

    def test_copy_holds_only_this_instrument_and_the_offline_users(self):
        db = self.__sqlite(self.entry)
        try:
            self.assertEqual([(SERIAL,)], db.execute("select serial from spectrometer_profile").fetchall())
            users = {r[0] for r in db.execute("select username from app_user")}
        finally:
            db.close()
        self.assertIn("masterUserDynarex", users)              # bound to the box (and a master)
        self.assertIn("masterUserExakta", users)               # every enabled master (Q11)
        self.assertIn("masterUser", users)
        self.assertNotIn("elpUser", users)                     # an end user of another instrument
        self.assertNotIn("endUser", users)

    def test_unchanged_data_gives_an_identical_copy(self):
        # §9.5: the app rewrites the plug only when the sha256 differs ⇒ builds must be deterministic.
        self.assertEqual(self.entry["sha256"], InstrumentCopyLogicModule().build(SERIAL)["sha256"])

    def test_unknown_serial_and_missing_key(self):
        self.assertFalse(InstrumentCopyLogicModule().build("no-such-serial")["ok"])
        os.environ["SPECTRACS_INSTRUMENT_COPY_KEY"] = self.keyFile + ".missing"
        try:
            self.assertFalse(InstrumentCopyLogicModule().build(SERIAL)["ok"])
        finally:
            os.environ["SPECTRACS_INSTRUMENT_COPY_KEY"] = self.keyFile

    def test_only_bound_users_or_masters_get_it(self):
        module = InstrumentCopyLogicModule()
        self.assertTrue(module.buildForUser("masterUserDynarex", "masterUserDynarex", SERIAL)["ok"])
        self.assertTrue(module.buildForUser("masterUserExakta", "masterUserExakta", SERIAL)["ok"])   # a master
        self.assertFalse(module.buildForUser("elpUser", "elpUser", SERIAL)["ok"])                    # another box
        self.assertFalse(module.buildForUser("masterUserDynarex", "wrong", SERIAL)["ok"])

    # --- S3 reader ---
    def test_round_trip_gives_the_online_bundle(self):
        copy = self.__read()
        online = InstrumentLogicModule().resolveBundle(SERIAL)
        self.assertEqual(online, copy.bundle)
        self.assertEqual("Dynarex", copy.bundle["deviceCodeName"])
        master = next(u for u in copy.users if u.username == "masterUserDynarex")
        self.assertIn("MASTER_USER", master.roles)
        self.assertTrue(master.passwordHash.startswith("$2"))

    def test_tampered_copy_is_refused(self):
        db = self.__sqlite(self.entry, keep=True)
        db.execute("update app_user set passwordHash = 'x'")
        db.commit()
        tampered = self.__entryFrom(db, self.entry["revision"], sign=False)
        with self.assertRaises(InstrumentCopyRefused):
            self.__read(tampered)

    def test_copy_for_another_plug_is_refused(self):
        with self.assertRaises(InstrumentCopyRefused):
            self.__read(serial="shellyplusplugs-000000000000")

    def test_unknown_key_is_refused(self):
        with self.assertRaises(InstrumentCopyRefused):
            self.__read(trusted={"0000000000000000": "00" * 32})

    def test_newer_revision_is_refused(self):
        db = self.__sqlite(self.entry, keep=True)
        db.execute("update alembic_version set version_num = 'ffffffffffff'")
        db.commit()
        newer = self.__entryFrom(db, "ffffffffffff")
        with self.assertRaises(InstrumentCopyRefused) as raised:
            self.__read(newer)
        self.assertIn("newer than this app", raised.exception.reason)

    def test_older_copy_is_migrated_and_read(self):
        from alembic import command
        from sqlalchemy import create_engine
        from sciens.spectracs.model.databaseEntity.DatabaseInitializer import _config
        sqliteBytes = bz2.decompress(base64.b64decode(self.entry["data"]))
        handle, path = tempfile.mkstemp(suffix=".db")
        os.write(handle, sqliteBytes)
        os.close(handle)
        engine = create_engine("sqlite:///" + path)
        try:
            cfg = _config("server")
            with engine.begin() as connection:
                cfg.attributes["connection"] = connection
                command.downgrade(cfg, "f641f17a1539")                 # the baseline revision
            engine.dispose()
            old = self.__entryFrom(sqlite3.connect(path), "f641f17a1539")
        finally:
            engine.dispose()
            if os.path.exists(path):                                   # __entryFrom removes it on success
                os.remove(path)
        copy = self.__read(old)
        self.assertEqual("Dynarex", copy.bundle["deviceCodeName"])
        self.assertEqual("f641f17a1539", copy.revision)

    # --- helpers ---
    def __sqlite(self, entry, keep=False):
        handle, path = tempfile.mkstemp(suffix=".db")
        os.write(handle, bz2.decompress(base64.b64decode(entry["data"])))
        os.close(handle)
        db = sqlite3.connect(path)
        if not keep:
            os.remove(path)                                            # the open handle keeps the data
        return db

    def __entryFrom(self, db, revision, sign=True):
        path = db.execute("pragma database_list").fetchone()[2]
        db.close()
        with open(path, "rb") as handle:
            sqliteBytes = handle.read()
        os.remove(path)
        digest = sha256hex(sqliteBytes)
        signature, keyId = (InstrumentCopySigner.sign(SERIAL, revision, digest) if sign
                            else (self.entry["signature"], self.entry["keyId"]))
        return {"data": base64.b64encode(bz2.compress(sqliteBytes)).decode(), "sha256": digest,
                "revision": revision, "signature": signature, "keyId": keyId}


if __name__ == "__main__":
    unittest.main()
