"""
S2b + S3b of SPEC_shelly_instrument_memory.md (§3.6, N14): a whole plugin — the dev bench, six files — as one
stripped, bz2-compressed, master-signed bundle, loaded back without touching the app's own copy. Uses a throw-away
master key (env SPECTRACS_SIGNING_KEY), never the real one.
"""
import os
import sys
import tempfile
import unittest

from sciens.spectracs.logic.security import PluginBundleUtil
from sciens.spectracs.logic.security.PluginSignatureUtil import PluginSignatureError, fingerprint
from sciens.spectracs.logic.spectral.plugin.PluginBundle import PluginBundleBuilder, PluginBundleLoader
from sciens.spectracs.logic.spectral.plugin.PluginRegistry import DEV_CODE_REF, PluginRegistry
from sciens.spectracs.plugin_sdk.version import SDK_VERSION


class PluginBundleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from nacl.signing import SigningKey
        key = SigningKey.generate()
        handle, cls.keyFile = tempfile.mkstemp(suffix=".seed")
        os.write(handle, bytes(key))
        os.close(handle)
        cls.previousKey = os.environ.get("SPECTRACS_SIGNING_KEY")
        os.environ["SPECTRACS_SIGNING_KEY"] = cls.keyFile
        publicKey = bytes(key.verify_key)
        cls.trusted = {fingerprint(publicKey): publicKey.hex()}
        cls.bundle = PluginBundleBuilder.forBuiltin(DEV_CODE_REF, "9.9-test", SDK_VERSION, "Measurement bench (dev)")
        cls.packed = PluginBundleBuilder.packSigned(cls.bundle)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.keyFile)
        if cls.previousKey is None:
            os.environ.pop("SPECTRACS_SIGNING_KEY", None)
        else:
            os.environ["SPECTRACS_SIGNING_KEY"] = cls.previousKey

    def test_the_bench_is_six_stripped_modules_and_small(self):
        self.assertEqual(6, len(self.bundle["modules"]))
        self.assertTrue(all('"""' not in text for text in self.bundle["modules"].values()))
        self.assertLess(len(self.packed), 30000)          # ≈ 26 KB stored as base64 (§3.6)

    def test_loads_and_leaves_the_app_copy_alone(self):
        import sciens.spectracs.plugins.dev.DevSpectralPlugin as builtin
        plugin = PluginBundleLoader.load(PluginBundleUtil.unpack(self.packed), self.trusted)
        self.assertEqual("DevSpectralPlugin", type(plugin).__name__)
        self.assertIsNot(builtin.DevSpectralPlugin, type(plugin))
        self.assertIs(builtin, sys.modules["sciens.spectracs.plugins.dev.DevSpectralPlugin"])

    def test_tampered_bundle_is_refused(self):
        envelope = PluginBundleUtil.unpack(self.packed)
        name = next(iter(envelope["bundle"]["modules"]))
        envelope["bundle"]["modules"][name] += "\nprint('injected')\n"
        with self.assertRaises(PluginSignatureError):
            PluginBundleLoader.load(envelope, self.trusted)

    def test_unknown_key_is_refused(self):
        with self.assertRaises(PluginSignatureError):
            PluginBundleLoader.load(PluginBundleUtil.unpack(self.packed), {"0000000000000000": "00" * 32})

    def test_registry_uses_the_plug_bundle_when_the_server_is_away(self):
        import sciens.spectracs.logic.security.TrustedKeys as trustedKeys
        keyId, publicKey = next(iter(self.trusted.items()))
        originalFetch, originalSource = PluginRegistry._fetchDbRow, PluginRegistry.offlineBundleSource
        trustedKeys.TRUSTED_KEYS[keyId] = publicKey
        try:
            PluginRegistry._fetchDbRow = staticmethod(lambda codeRef, version: {"ok": False,
                                                                                "message": "server unavailable"})
            PluginRegistry.offlineBundleSource = staticmethod(
                lambda codeRef, version: PluginBundleUtil.unpack(self.packed)
                if (codeRef, version) == (DEV_CODE_REF, "9.9-test") else None)
            plugin = PluginRegistry.resolve(DEV_CODE_REF, "9.9-test")
            self.assertEqual("DevSpectralPlugin", type(plugin).__name__)
        finally:
            PluginRegistry._fetchDbRow, PluginRegistry.offlineBundleSource = originalFetch, originalSource
            trustedKeys.TRUSTED_KEYS.pop(keyId, None)


if __name__ == "__main__":
    unittest.main()
