"""
S4 of SPEC_shelly_instrument_memory.md (§4.7): PlugKeyValueStore over the in-memory plug and, through the real
HTTP transport, over FakeShellyServer (POST /rpc, digest auth). No hardware.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fakes"))

from FakeShellyServer import FakeShellyServer  # noqa: E402

from sciens.spectracs.logic.plugstore.PlugKeyValueStore import PlugKeyValueStore  # noqa: E402
from sciens.spectracs.logic.plugstore.PlugStoreTransport import (  # noqa: E402
    InMemoryPlugStoreTransport, PlugStoreError, PlugStoreFull)
from sciens.spectracs.logic.plugstore.ShellyGen2PlugStoreTransport import ShellyGen2PlugStoreTransport  # noqa: E402


class PlugKeyValueStoreInMemoryTest(unittest.TestCase):

    def setUp(self):
        self.plug = InMemoryPlugStoreTransport()
        self.store = PlugKeyValueStore(self.plug)

    def test_small_text_goes_native(self):
        self.store.set("index", '{"v":1}')
        self.assertEqual('{"v":1}', self.store.get("index"))
        self.assertIn("spectracs_index", self.plug.kvs)
        self.assertEqual([], self.plug.scriptList())

    def test_large_bytes_go_to_slots_and_round_trip(self):
        blob = os.urandom(60000)                        # base64 = 80 000 chars ⇒ 2 slots
        self.store.set("plugin", blob)
        self.assertEqual(blob, self.store.get("plugin"))
        self.assertIn("spectracs_m_plugin", self.plug.kvs)
        self.assertNotIn("spectracs_plugin", self.plug.kvs)
        self.assertEqual(2, len(self.plug.scriptList()))
        self.assertIsNotNone(self.store.sha256("plugin"))

    def test_large_text_with_umlauts_round_trips(self):
        text = "Kürbiskernöl " * 100
        self.store.set("note", text)
        self.assertEqual(text, self.store.get("note"))

    def test_boundary_is_the_escaped_length(self):
        self.store.set("a", "a" * 251)                  # "s:" + 251 = 253 ⇒ native
        self.assertIn("spectracs_a", self.plug.kvs)
        self.store.set("b", "ä" * 100)                  # escaped \\u00e4 ⇒ far over 253 ⇒ slot
        self.assertIn("spectracs_m_b", self.plug.kvs)
        self.assertEqual("ä" * 100, self.store.get("b"))

    def test_rewrite_replaces_the_old_slots(self):
        self.store.set("copy", b"x" * 5000)
        first = {sid for sid, _ in self.plug.scriptList()}
        self.store.set("copy", b"y" * 5000)
        second = {sid for sid, _ in self.plug.scriptList()}
        self.assertTrue(first.isdisjoint(second))
        self.assertEqual(b"y" * 5000, self.store.get("copy"))

    def test_torn_write_keeps_the_old_value(self):
        self.store.set("copy", b"old" * 10000)
        self.plug.appends, self.plug.failAfterAppends = 0, 1
        with self.assertRaises(PlugStoreError):
            self.store.set("copy", b"new" * 10000)
        self.plug.failAfterAppends = None
        self.assertEqual(b"old" * 10000, self.store.get("copy"))
        self.store.removeOrphans()
        self.assertEqual(1, len(self.plug.scriptList()))

    def test_corrupt_slot_reads_as_missing(self):
        self.store.set("copy", b"z" * 5000)
        sid = self.plug.scriptList()[0][0]
        self.plug.scripts[sid][1] = "A" * len(self.plug.scripts[sid][1])
        self.assertIsNone(self.store.get("copy"))

    def test_small_after_large_drops_the_slots(self):
        self.store.set("copy", b"z" * 5000)
        self.store.set("copy", "tiny")
        self.assertEqual([], self.plug.scriptList())
        self.assertEqual("tiny", self.store.get("copy"))

    def test_delete_and_keys(self):
        self.store.set("index", "1")
        self.store.set("copy", b"z" * 5000)
        self.assertEqual(["copy", "index"], self.store.keys())
        self.store.delete("copy")
        self.store.delete("index")
        self.assertEqual([], self.store.keys())
        self.assertEqual([], self.plug.scriptList())
        self.assertIsNone(self.store.get("copy"))

    def test_flash_reserve_refuses(self):
        plug = InMemoryPlugStoreTransport(fsFree=40 * 1024)
        with self.assertRaises(PlugStoreFull):
            PlugKeyValueStore(plug).set("plugin", os.urandom(30000))
        self.assertEqual([], plug.scriptList())

    def test_no_room_for_both_refuses_unless_in_place(self):
        # Measured on the real plug: a 93 KB value cannot be rewritten atomically in 124 KiB.
        self.store.set("plugin", os.urandom(52000))                 # ≈ 69 KB base64
        with self.assertRaises(PlugStoreFull):
            self.store.set("plugin", os.urandom(52000))
        replacement = os.urandom(52000)
        self.store.set("plugin", replacement, replaceInPlace=True)
        self.assertEqual(replacement, self.store.get("plugin"))
        self.assertEqual(2, len(self.plug.scriptList()))

    def test_foreign_keys_and_scripts_are_untouched(self):
        self.plug.kvs["lamp_hours"] = "12"
        self.plug.scriptCreate("someone_elses_script")
        self.store.set("copy", b"z" * 5000)
        self.store.removeOrphans()
        self.store.delete("copy")
        self.assertEqual("12", self.plug.kvs["lamp_hours"])
        self.assertEqual([(1, "someone_elses_script")], self.plug.scriptList())

    def test_bad_keys(self):
        for key in ("", "a.b", "m_copy", "x" * 31):
            with self.assertRaises(ValueError):
                self.store.set(key, "v")


class PlugKeyValueStoreOverHttpTest(unittest.TestCase):
    """The same store through the real POST transport, with the plug's digest auth."""

    def test_round_trip_with_password(self):
        with FakeShellyServer(password="geheim") as plug:
            store = PlugKeyValueStore(ShellyGen2PlugStoreTransport(plug.host, password="geheim"))
            blob = os.urandom(70000)
            store.set("copy", blob)
            store.set("index", '{"v":1}')
            self.assertEqual(blob, store.get("copy"))
            self.assertEqual('{"v":1}', store.get("index"))
            self.assertIsNone(store.get("missing"))
            self.assertEqual(["copy", "index"], store.keys())
            self.assertTrue(all(int(p["len"]) <= 4096 for p in plug.callsTo("Script.GetCode")))
            store.delete("copy")
            self.assertEqual({}, plug.scripts)

    def test_wrong_password(self):
        from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed
        with FakeShellyServer(password="geheim") as plug:
            with self.assertRaises(LampAuthFailed):
                PlugKeyValueStore(ShellyGen2PlugStoreTransport(plug.host, password="falsch")).get("copy")


if __name__ == "__main__":
    unittest.main()
