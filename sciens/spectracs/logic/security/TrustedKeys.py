"""The trust anchor — shipped IN app source (SPEC_plugin_distribution.md §3). `keyId` (pubkey fingerprint) ->
public key hex. A dict/LIST from day one so key rotation is never a flag day. The loader looks up a sealed
row's keyId HERE and refuses if absent — the shipped list is what gates. NEVER fetch this from the server (a
trust anchor fetched from the thing you are verifying is not a trust anchor).

Populate with the line printed by generateSigningKey.py."""

TRUSTED_KEYS = {
    # "sha256(pubkey)[:16]": "pubkey-hex",
    "0c618b47f8a17f36": "4a3daf897a1055fb72bf6f1e0714071f5c83d35f400c123f88884f6417bf74b5",
}

# The SERVER's instrument-copy keys (SPEC_shelly_instrument_memory.md §9.4): a SEPARATE list on purpose, so the
# server's key can sign an instrument copy but never a plugin. Seed: spectracs-keys/instrumentCopy.seed.
TRUSTED_COPY_KEYS = {
    "ff8fa4e8a10f8b2f": "afb72917a567eb3cac5c59b0a4f5f03b1f43776fbb6cc3c799e6988f0264fdae",
}
