"""Master-side plugin signer (SPEC_plugin_distribution.md §8, B2). App-tier and desktop-only: it is the ONLY
place PyNaCl is used, and PyNaCl is imported lazily so importing this module never forces the dependency. Every
client VERIFIES with the pure-Python -core verifier instead, so Android never links libsodium.

The private key is a raw 32-byte Ed25519 seed in a file OUTSIDE every repo — never committed, never on the
server. Path from env `SPECTRACS_SIGNING_KEY`, default `../spectracs-keys/signing.seed`."""
import base64
import os

from sciens.spectracs.logic.security.PluginSignatureUtil import signing_tuple, fingerprint

DEFAULT_KEY_PATH = "../spectracs-keys/signing.seed"


def keyPath() -> str:
    return os.environ.get("SPECTRACS_SIGNING_KEY", DEFAULT_KEY_PATH)


def signingKeyAvailable() -> bool:
    return os.path.isfile(keyPath())


def _loadSigningKey():
    from nacl.signing import SigningKey
    with open(keyPath(), "rb") as handle:
        seed = handle.read()
    return SigningKey(seed[:32])


def sign(codeRef: str, version: str, targetSdkVersion, source: str):
    """Sign the tuple on the master. Returns (signatureBase64, keyId). Callers MUST check
    signingKeyAvailable() first and disable publishing with a clear message when the key is absent."""
    signingKey = _loadSigningKey()
    signature = signingKey.sign(signing_tuple(codeRef, version, targetSdkVersion, source)).signature
    keyId = fingerprint(bytes(signingKey.verify_key))
    return base64.b64encode(signature).decode("ascii"), keyId
