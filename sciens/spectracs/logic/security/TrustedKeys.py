"""The trust anchor — shipped IN app source (SPEC_plugin_distribution.md §3). `keyId` (pubkey fingerprint) ->
public key hex. A dict/LIST from day one so key rotation is never a flag day. The loader looks up a sealed
row's keyId HERE and refuses if absent — the shipped list is what gates. NEVER fetch this from the server (a
trust anchor fetched from the thing you are verifying is not a trust anchor).

Populate with the line printed by generateSigningKey.py."""

TRUSTED_KEYS = {
    # "sha256(pubkey)[:16]": "pubkey-hex",
    "0c618b47f8a17f36": "4a3daf897a1055fb72bf6f1e0714071f5c83d35f400c123f88884f6417bf74b5",
}
