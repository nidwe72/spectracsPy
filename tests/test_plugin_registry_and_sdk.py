"""
A1/A2 (SPEC_plugin_distribution.md §8) — the PluginRegistry + the SDK-compat gate.

The resolve-all guard is the structural closure for bug F1: every codeRef the registry names must actually
import, instantiate, and match its declared title — so a stale/typo'd codeRef can never ship again. It also
cross-checks the -model DB seed (which structurally cannot import a plugin class, so it keeps a literal
string) against the registry, catching the exact drift that left the dev-login bypass broken.

Needs the plugins repo on the path. Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_plugin_registry_and_sdk.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry, PUMPKIN_OIL_CODE_REF
from sciens.spectracs.logic.user.UserSeedLogicModule import UserSeedLogicModule
from sciens.spectracs.plugin_sdk.version import (
    SDK_VERSION, PluginSdkVersionError, checkSdkCompatible)


class PluginRegistryResolveAllTest(unittest.TestCase):
    """Every registry codeRef resolves, instantiates, and the entry title matches the class title (F1)."""

    def test_every_coderef_resolves_and_title_matches(self):
        for entry in PluginRegistry.entries():
            plugin = PluginRegistry.resolve(entry.codeRef)
            self.assertIsNotNone(plugin, entry.codeRef)
            self.assertEqual(entry.title, plugin.title, entry.codeRef)

    def test_dev_plugin_is_bench_only(self):
        benchOnly = [e for e in PluginRegistry.entries() if e.benchOnly]
        self.assertTrue(benchOnly, "expected the Dev plugin to be present and benchOnly")
        # excluding benchOnly hides it from the end-user binding set
        self.assertNotIn(
            benchOnly[0].codeRef, PluginRegistry.codeRefs(includeBenchOnly=False))

    def test_model_seed_coderef_is_registered(self):
        # The -model seed can't import a plugin class (tier order), so it holds a literal codeRef string.
        # Assert it stays in lockstep with the registry — the guard that would have caught F1 at CI time.
        self.assertIn(UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"], PluginRegistry.codeRefs())
        self.assertEqual(UserSeedLogicModule.PUMPKIN_PLUGIN["codeRef"], PUMPKIN_OIL_CODE_REF)


class ListAllTest(unittest.TestCase):
    """B6.1 — listAll() = the built-in entries + one entry per DB-published (codeRef, version) row."""

    def setUp(self):
        import sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient as clientModule
        self._clientModule = clientModule
        self._orig = clientModule.SpectracsPyServerClient.listPlugins

    def tearDown(self):
        self._clientModule.SpectracsPyServerClient.listPlugins = self._orig

    def test_listall_merges_builtins_and_db_rows(self):
        self._clientModule.SpectracsPyServerClient.listPlugins = lambda _self: [
            {"codeRef": "db.demo.Demo.Demo", "title": "Demo", "version": "2.0.0"}]
        entries = PluginRegistry.listAll()
        builtinCount = len(PluginRegistry.entries())
        self.assertEqual(len(entries), builtinCount + 1)
        db = [e for e in entries if e.version == "2.0.0"]
        self.assertEqual(len(db), 1)
        self.assertEqual(db[0].codeRef, "db.demo.Demo.Demo")

    def test_listall_degrades_to_builtins_when_db_empty(self):
        self._clientModule.SpectracsPyServerClient.listPlugins = lambda _self: []
        self.assertEqual(len(PluginRegistry.listAll()), len(PluginRegistry.entries()))


class _FakePlugin:
    title = "Fake"

    def __init__(self, target):
        self.targetSdkVersion = target


class SdkCompatibilityTest(unittest.TestCase):

    def test_matching_sdk_is_accepted(self):
        checkSdkCompatible(_FakePlugin(SDK_VERSION))  # must not raise

    def test_default_target_matches_shipping_sdk(self):
        # A built-in plugin that never overrides targetSdkVersion inherits SDK_VERSION -> always loads.
        plugin = PluginRegistry.resolve(PUMPKIN_OIL_CODE_REF)
        self.assertEqual(plugin.targetSdkVersion, SDK_VERSION)

    def test_newer_target_says_update_the_app(self):
        with self.assertRaises(PluginSdkVersionError) as ctx:
            checkSdkCompatible(_FakePlugin(SDK_VERSION + 1))
        self.assertIn("newer app", str(ctx.exception))

    def test_older_target_says_rebuild_the_plugin(self):
        with self.assertRaises(PluginSdkVersionError) as ctx:
            checkSdkCompatible(_FakePlugin(SDK_VERSION - 1))
        self.assertIn("Rebuild", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
