"""B2 (SPEC_plugin_distribution.md §8) — the plugin-signature security core, in isolation (no DB, no RPC).

Signs with PyNaCl (as the master would) and verifies with the vendored pure-Python -core Ed25519, proving the
two implementations interoperate, then asserts the four refusals: tampered source, swapped version, re-pointed
codeRef, unknown keyId (plus a lied-about targetSdkVersion). Run from the repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python -m pytest tests/test_plugin_signature.py -q
"""
import base64
import unittest

from nacl.signing import SigningKey

from sciens.spectracs.logic.security.PluginSignatureUtil import signing_tuple, fingerprint, verify, verifySealed


class PluginSignatureTest(unittest.TestCase):

    def setUp(self):
        self.signingKey = SigningKey.generate()
        self.pub = bytes(self.signingKey.verify_key)
        self.keyId = fingerprint(self.pub)
        self.codeRef, self.version, self.sdk, self.source = "a.b.Plugin.Plugin", "1.0.0", 1, "print('hi')"
        self.signature = self.signingKey.sign(
            signing_tuple(self.codeRef, self.version, self.sdk, self.source)).signature
        self.sigB64 = base64.b64encode(self.signature).decode("ascii")
        self.trusted = {self.keyId: self.pub.hex()}

    def test_pynacl_signature_verifies_with_pure_python(self):
        self.assertTrue(verify(self.pub, self.signature, self.codeRef, self.version, self.sdk, self.source))

    def test_sealed_row_verifies(self):
        self.assertTrue(verifySealed(self.codeRef, self.version, self.sdk, self.source,
                                     self.sigB64, self.keyId, self.trusted))

    def test_tampered_source_refused(self):
        self.assertFalse(verifySealed(self.codeRef, self.version, self.sdk, "print('EVIL')",
                                      self.sigB64, self.keyId, self.trusted))

    def test_swapped_version_refused(self):
        self.assertFalse(verifySealed(self.codeRef, "9.9.9", self.sdk, self.source,
                                      self.sigB64, self.keyId, self.trusted))

    def test_repointed_coderef_refused(self):
        self.assertFalse(verifySealed("x.y.Other.Other", self.version, self.sdk, self.source,
                                      self.sigB64, self.keyId, self.trusted))

    def test_lied_targetsdk_refused(self):
        self.assertFalse(verifySealed(self.codeRef, self.version, 999, self.source,
                                      self.sigB64, self.keyId, self.trusted))

    def test_unknown_keyid_refused(self):
        self.assertFalse(verifySealed(self.codeRef, self.version, self.sdk, self.source,
                                      self.sigB64, self.keyId, {}))  # empty trust anchor


if __name__ == "__main__":
    unittest.main()
