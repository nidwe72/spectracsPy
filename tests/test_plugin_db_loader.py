"""B3 (SPEC_plugin_distribution.md §8) — the DB-plugin loader end to end, minus the Pyro hop.

Signs a tiny SpectralPlugin source with an ephemeral key (as the master would), seals it into the shape the
server returns, then drives PluginRegistry.resolve(codeRef, version): it VERIFIES the signature against the
(monkeypatched) TRUSTED_KEYS, execs the source, instantiates the class, and runs a hook. Then asserts a
tampered row is REFUSED before exec. The RPC itself is stubbed so the test needs no server.

Run:  PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
          ./venv/bin/python -m pytest tests/test_plugin_db_loader.py -q
"""
import base64
import unittest

from nacl.signing import SigningKey

from sciens.spectracs.logic.security.PluginSignatureUtil import signing_tuple, fingerprint, PluginSignatureError
import sciens.spectracs.logic.security.TrustedKeys as trustedKeysModule
import sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient as clientModule
from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry, PUMPKIN_OIL_CODE_REF

_SOURCE = (
    "from sciens.spectracs.plugin_sdk import SpectralPlugin\n"
    "class Demo(SpectralPlugin):\n"
    "    title = 'Demo DB plugin'\n"
    "    targetSdkVersion = 1\n"
    "    def evaluation(self, workflow):\n"
    "        return 'ran-from-db'\n"
)
_CODEREF, _VERSION, _SDK = "db.demo.Demo.Demo", "1.0.0", 1


class DbPluginLoaderTest(unittest.TestCase):

    def setUp(self):
        self.signingKey = SigningKey.generate()
        pub = bytes(self.signingKey.verify_key)
        self.keyId = fingerprint(pub)
        sig = self.signingKey.sign(signing_tuple(_CODEREF, _VERSION, _SDK, _SOURCE)).signature
        self.row = {"ok": True, "codeRef": _CODEREF, "version": _VERSION, "title": "Demo DB plugin",
                    "source": _SOURCE, "signature": base64.b64encode(sig).decode("ascii"),
                    "keyId": self.keyId, "targetSdkVersion": _SDK}
        # trust this ephemeral key + stub the fetch RPC
        trustedKeysModule.TRUSTED_KEYS[self.keyId] = pub.hex()
        self._origFetch = clientModule.SpectracsPyServerClient.getPluginSource

    def tearDown(self):
        trustedKeysModule.TRUSTED_KEYS.pop(self.keyId, None)
        clientModule.SpectracsPyServerClient.getPluginSource = self._origFetch

    def _stubFetch(self, row):
        clientModule.SpectracsPyServerClient.getPluginSource = lambda _self, c, v: row

    def test_signed_db_plugin_loads_and_runs(self):
        self._stubFetch(self.row)
        plugin = PluginRegistry.resolve(_CODEREF, _VERSION)
        self.assertEqual(plugin.title, "Demo DB plugin")
        self.assertEqual(plugin.evaluation(None), "ran-from-db")

    def test_tampered_source_is_refused_before_exec(self):
        tampered = dict(self.row, source=_SOURCE + "raise RuntimeError('should never exec')\n")
        self._stubFetch(tampered)
        with self.assertRaises(PluginSignatureError):
            PluginRegistry.resolve(_CODEREF, _VERSION)

    def test_untrusted_key_is_refused(self):
        trustedKeysModule.TRUSTED_KEYS.pop(self.keyId, None)  # forget the key
        self._stubFetch(self.row)
        with self.assertRaises(PluginSignatureError):
            PluginRegistry.resolve(_CODEREF, _VERSION)


class DispatchSealednessTest(unittest.TestCase):
    """B6.4 — resolve dispatches on the ROW'S SEALEDNESS, so a bare/seed row and offline both fall back to the
    shipped built-in (the F16 resolution), while `version=None` never touches the server."""

    def setUp(self):
        self._origFetch = clientModule.SpectracsPyServerClient.getPluginSource

    def tearDown(self):
        clientModule.SpectracsPyServerClient.getPluginSource = self._origFetch

    def test_version_none_resolves_builtin_without_fetching(self):
        def _boom(_self, c, v):
            raise AssertionError("resolve(codeRef, None) must NOT hit the server")
        clientModule.SpectracsPyServerClient.getPluginSource = _boom
        plugin = PluginRegistry.resolve(PUMPKIN_OIL_CODE_REF)  # no version
        self.assertEqual(plugin.title, "Pumpkin-seed-oil colour QM")

    def test_unsealed_row_falls_back_to_builtin(self):
        # A bare/seed row (source NULL) is a "use the shipped copy" pointer, not a broken row.
        bare = {"ok": True, "codeRef": PUMPKIN_OIL_CODE_REF, "version": "1.0", "title": "x",
                "source": None, "signature": None, "keyId": None, "targetSdkVersion": None}
        clientModule.SpectracsPyServerClient.getPluginSource = lambda _s, c, v: bare
        plugin = PluginRegistry.resolve(PUMPKIN_OIL_CODE_REF, "1.0")
        self.assertEqual(plugin.title, "Pumpkin-seed-oil colour QM")

    def test_offline_falls_back_to_builtin(self):
        clientModule.SpectracsPyServerClient.getPluginSource = lambda _s, c, v: {"ok": False, "message": "down"}
        plugin = PluginRegistry.resolve(PUMPKIN_OIL_CODE_REF, "1.0")
        self.assertEqual(plugin.title, "Pumpkin-seed-oil colour QM")

    def test_unknown_version_with_no_builtin_raises(self):
        clientModule.SpectracsPyServerClient.getPluginSource = lambda _s, c, v: {"ok": False}
        with self.assertRaises(ValueError):
            PluginRegistry.resolve("no.such.Plugin.Plugin", "9.9.9")


if __name__ == "__main__":
    unittest.main()
