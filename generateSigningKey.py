"""One-time: generate the master Ed25519 signing key (SPEC_plugin_distribution.md B2).

Writes the raw 32-byte seed to SPECTRACS_SIGNING_KEY (default ../spectracs-keys/signing.seed — OUTSIDE every
repo, so it is never committed) and prints the TRUSTED_KEYS entry to paste into
sciens/spectracs/logic/security/TrustedKeys.py. Run:  ./venv/bin/python generateSigningKey.py"""
import os

from nacl.signing import SigningKey

from sciens.spectracs.logic.security.PluginSigner import keyPath
from sciens.spectracs.logic.security.PluginSignatureUtil import fingerprint


def main():
    path = keyPath()
    if os.path.exists(path):
        print("refusing to overwrite an existing key at %s" % path)
        return
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    signingKey = SigningKey.generate()
    with open(path, "wb") as handle:
        handle.write(bytes(signingKey))
    os.chmod(path, 0o600)
    publicKey = bytes(signingKey.verify_key)
    print("wrote private seed -> %s" % path)
    print('TRUSTED_KEYS entry ->  "%s": "%s"' % (fingerprint(publicKey), publicKey.hex()))


if __name__ == "__main__":
    main()
