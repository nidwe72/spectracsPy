# SPEC — The Shelly as the instrument's memory (factory provisioning)

**Status:** DESIGN only, rev 7 2026-10-19. Nothing implemented, nothing written to the plug yet.
**Comes from:** `SPEC_ammo_box_camera.md` phase P1 (H3/H4 in `spectracs-hardware/ammoBox-spec.md`). Edwin
decided on 2026-10-19 that this gets its own spec, not a section in `SPEC_lamp_switch.md`.
**Builds on:** `SPEC_lamp_switch.md` (driver, discovery, `lamp_plug` row, password D9),
`SPEC_connection_and_calibration_ux.md` (serial → `SpectrometerProfile` → `SpectrometerSetup`, server-authoritative;
the resolve call `InstrumentLogicModule.resolveBundle`) and `SPEC_plugin_distribution.md` (Ed25519 signing, §4.3).

**Revisions.** rev 1: identity only on the plug. rev 2 (Edwin): the whole setup as an offline copy, serial =
plug id, standard password. **rev 3 (Edwin):** the calibration spectrum is not needed ⇒ the copy is ~1 KB ⇒
it is **spread across KVS pairs**, script slots dropped; JSON needs versioning too ⇒ the copy **is the
server's existing resolve response**, so there is no new format to version. **rev 4 (Edwin):** SQLite measured
(fits, ~17 keys compressed, §3.3); offline login in the same sweep (§4.5, S6); S0 spelled out (§7.1).
**rev 5 (Edwin):** the copy is **SQLite** (N12); the changed plug password lives in the **app DB** (N13);
implementation phases laid out (§7).
**rev 7 (Edwin):** one **key-value provider** in front of both storages (§4.7): small values → native KVS,
large values → script slots, invisible to the caller.
**rev 6 (Edwin):** one larger plugin on the plug is the goal (§3.6, bz2 stripped); the SQLite copy moves into a
**script slot** too (§4.6) ⇒ KVS keeps only the index and signatures; the spectrum travels **lossless**.

---

## 1 — Decisions (Edwin, 2026-10-19)

| # | Decision |
|---|---|
| N1 | `Spectrometer.modelName = "InVision"` is the **old two-cylinder spectrometer** (ELP camera). |
| N2 | `Spectrometer.modelName = "InLight"` is the **ammo-box variant**. |
| N3 | The box camera `2bc5:0529` (USB vendor id = **Orbbec**; the board is unbranded) gets the sensor code name **`Dynarex`** (an existing, unused `SpectrometerSensorCodeName` value). |
| N4 | Style **`GreenGold`** ⇒ the model is **`InLight-Dynarex-GreenGold`**. Model + plug serial together identify one instrument. |
| N5 | The **server holds the `SpectrometerSetup`** (authoritative). **The plug holds a copy**, so that the instrument can run **temporarily offline**. |
| N6 | **Serial = the Shelly device id**, e.g. `shellyplusplugs-e86beae3cb60`. |
| N7 | **Plug swap is accepted**: spectrometer and plug both get a **label with the plug's MAC**; plugging in the right plug is the user's job. No mechanical fix for now. |
| N8 | Plug password: a **standard password** that the user can change. |
| N9 | Keep the old seed row `InLight-Automat` (Microdia). |
| N10 | The factory tool: to be discussed later, probably a tool inside the app. |
| N11 | ⭐ rev 3: the copy is **spread across KVS key-value pairs**. |
| N12 | ⭐ rev 5: the copy is an **SQLite file** of the server's rows (§3.3), compressed and chunked across KVS. |
| N13 | ⭐ rev 5: the plug password (standard or changed) is saved in the **app DB** (`lamp_plug.password`, as today, D9). |
| N14 | ⭐ rev 6: **one larger plugin** on the plug (the dev bench is the yardstick), stored **bz2, without docstrings and comments**; ×3.5 headroom is enough. |
| N16 | ⭐ rev 7: a **key-value provider** hides the two storages: small values in native KVS, large ones in script slots (§4.7). |
| N15 | ⭐ rev 6 (proposal, Edwin's question): the SQLite copy goes into a **script slot** as well; KVS holds only index + signatures (§4.6). |

What exists today (server DB, 2026-10-19):

| `modelName` | sensor `codeName` | camera | style | profile serial |
|---|---|---|---|---|
| Phantom | Virtuax | virtual `0c99:9999` | SlightHaze | `TEST-0001` |
| InVision | Exakta | ELP `32e4:8830` | GreenGold | `ELP-0001` |
| InLight | Automat | Microdia `0c45:6366` | GreenGold | — (none; row kept, N9) |
| ★ **InLight** | ★ **Dynarex** | ★ Orbbec `2bc5:0529` | GreenGold | ★ `shellyplusplugs-<mac>` |

---

## 2 — What the plug can store (measured on Edwin's plug + Shelly docs)

Edwin's plug: **Shelly Plus Plug S, `SNPL-00112EU`, gen 2, firmware 1.3.3** (1.7.5 offered), device id
`shellyplusplugs-e86beae3cb60`, MAC `E86BEAE3CB60`, **no password set**. Read-only calls on 2026-10-19:

- Flash file system: **`fs_size` 448 KiB, `fs_free` 124 KiB**. KVS empty, no scripts.
- **No RPC writes a file** (no `FS.*` / upload in `Shelly.ListMethods`; `FFS.*` is undocumented and disabled).

| Route | Capacity | Readable without password? | Survives factory reset? |
|---|---|---|---|
| **Device id / MAC** (`GET /shelly`) | fixed in hardware | ✅ yes | ✅ **yes** |
| ⭐ **KVS** | **50 keys**, key ≤ **42** chars, value ≤ **253**, any JSON; ⚠ no dots in keys (fw ≤ 2.0.1) ⇒ **≤ ~12.6 KB in total** | no (with a password) | ⛔ no |
| Script slots | ✅ measured §7.3: **65 535 bytes per slot**, ≥ 2 slots, PutCode chunks ≥ 16 KB; ⛔ read in ≤ 4 KB pieces (a whole-slot read **rebooted the plug**) | no | ⛔ no |
| TLS slots | certificates | — | ⛔ abuse, never |

Script slots were rev 2's carrier for a ~22 KB copy. Since rev 3 the copy fits in KVS ⇒ **not used**.

**Factory reset of a Plus Plug S:** hold the button for **10 s**, **only within the first 60 s after plugging the
plug in** (5 s = reboot; 3 s = status, only with the output off). Also through `Shelly.FactoryReset`, the plug's
web page and the Shelly app. It erases WLAN, password and KVS; it does **not** change the device id.

---

## 3 — What the copy contains

### 3.1 The calibration spectrum stays out (Edwin's question, checked in the code)

`SpectrometerCalibrationProfile.calibrationSpectrumJson` **is** stored on the server: for the ELP, **2 591
points = 54 764 bytes**. But it is **provenance only**, the raw CFL capture the calibration was made from
(comment in `SpectrometerCalibrationProfile.py`: "provenance that a sane CFL spectrum was used"). It is shown in
the setup editor and **never used to measure**. Measuring needs the ROI, the four px→nm coefficients and the
spectral lines.

⇒ The copy **leaves the spectrum out** (`"spectrum": null`). That turns rev 2's ~56 KB into **~1 KB**.

### 3.2 The copy = the server's existing resolve response (rev 3, answers "JSON has to be versioned too")

Edwin is right: any stored format, JSON or SQLite, must be versioned. ⇒ The copy does **not** get a new format.
It is **exactly the document the server already sends** when the app resolves a serial
(`InstrumentLogicModule.resolveBundle`, `{"ok", "serial", "deviceCodeName", "pluginCodeRef", "pluginVersion", "calibration":
{ROI, A–D, spectralLines, spectrum}}`). The app parses this document today, at every login.

- When that response changes, the copy changes with it, and the app reads the copy with **the same code**.
  One format, versioned in one place.
- ⇒ It needs **one** `v` field (the resolve response has none today; S2 adds it to both).
- Two fields are added for the offline checks: `model` (`InLight-Dynarex-GreenGold`, §4.4) and `written`.
  ⚠ The ammo-box spec adds `captureWidth`/`captureHeight` to the calibration; they travel along the same way.
- SQLite would be a **second** form of the same data, beside the resolve response ⇒ two formats to version.
  That is the argument against it, not the schema work alone.

### 3.3 ⭐ SQLite fits too (measured, rev 4)

The same rows (setup, profile, spectrometer, sensor, chip, style, vendor, calibration **without** the spectrum,
6 spectral lines + their master data, plugin row), copied with the **server's own table definitions** into a
fresh SQLite file:

| Page size | File | zlib + base64 | KVS keys at 240 chars |
|---|---|---|---|
| 4 096 (default) | 106 496 B | 4 108 | **18** |
| 1 024 | 29 696 B | 3 776 | **16** |
| 512 | 20 480 B | 3 888 | **17** |

⇒ The file is mostly empty pages (one per table and index), which compress away. **~17 of 50 keys** ⇒ SQLite
on the plug is **possible**, compressed and chunked across KVS like the JSON.

| | JSON (the resolve response) | SQLite (the server's rows) |
|---|---|---|
| Keys | 4 + 2 | ~17 + 2 |
| Versioned by | "only add fields" + `v` | the **server's Alembic revision** (copy the `alembic_version` row along) |
| Old copy on a plug | read as is | **can be migrated** with the existing server Alembic tree |
| App side | the code that reads the resolve response today | open the file with the -model entity classes (same classes as the server) |
| Readable by eye in the plug's web page | yes | no (compressed binary) |

✅ **Decided (N12): SQLite**, page size 1 024 (smallest compressed of the three). The §3.2 JSON route is kept
only as the reasoning that led here; the resolve response stays a wire format, not a stored one.

**Measured** (ELP setup, serial and code name swapped for the box's): **944 bytes** with 6 spectral lines.

---

### 3.4 ⭐ With or without the spectrum (Edwin, 2026-10-19) — measured

The copy builder (S2) gets **one switch: with or without the calibration spectrum**. The index records which
(`"spectrum": "none" | "u16"`). Measured on the ELP rows, SQLite page 1 024, zlib + base64, chunks of 253:

| Variant | File | Base64 | Keys (+ index + sig) | Fits 50? |
|---|---|---|---|---|
| without spectrum | 29 696 | 3 776 | **17** | ✅ |
| with spectrum, as stored (JSON dict, 15+ digits) | 83 968 | 26 556 | 107 | ⛔ |
| with spectrum, rounded to 3 decimals | 65 536 | 19 648 | 80 | ⛔ |
| with spectrum, rounded to 1 decimal | 62 464 | 16 244 | 67 | ⛔ |
| ⭐ **with spectrum, packed as uint16** (`{"scale", "u16": base64}` in the same column) | 35 840 | 8 100 | **35** | ✅ |

- **Only the packed form fits.** The stored JSON is a dict of 2 591 `"index": float` pairs with 15–17 digits
  each; most of the bytes are digits that carry no information.
- **Packed = lossy, but far below anything that matters:** step = max/65 535 = **0.0037** on a range of
  −0.32…244.3. ⚠ The spectrum has small **negative** values (min −0.32) ⇒ pack over **min…max** (an offset
  in the header), not 0…max.
- The packed form exists **only in the copy**. The reader (S3) unpacks it back into the server's JSON dict,
  so everything after the reader sees the column as it is on the server. The server keeps the full spectrum.
- The box camera has 1 920 columns instead of 2 591 ⇒ ~¾ of the spectrum's keys (≈ 27 total).
- **Budget rule:** if the copy with spectrum exceeds 48 data keys (e.g. together with a DB-served signed plugin),
  the builder **drops the spectrum first** and records `"spectrum": "none"`. The spectrum is provenance only
  (§3.1); the instrument measures without it.

### 3.5 And the plugin itself? (Edwin, 2026-10-19) — measured

Plugin source, zlib + base64, in KVS keys of 253 (48 data keys available):

| Plugin | Raw | Compressed + base64 | Keys |
|---|---|---|---|
| ⛔ `DevSpectralPlugin.py` (dev measurement bench) | 204 685 | 91 668 | **363** |
| ⛔ dev bench, all 6 files (with the 5 gauge views it imports) | 230 273 | 101 104 | **400** |
| ⛔ `DevSpectralPlugin.py` without docstrings and comments | 77 109 | 27 480 | **109** |
| ✅ `PumpkinOilPlugin.py` (the sealed DB row: 5 428 source + 88 signature) | 5 815 | 2 800 | **12** |

- **The dev bench does not fit**, not even stripped: 7–8× the whole KVS. It would not even fit the flash
  comfortably (101 KB of the 124 KiB free, in undocumented script slots).
- **The pumpkin plugin fits:** 12 keys. With the setup (17) ⇒ 29; with the packed spectrum too (35) ⇒ **47
  of 50**, at the edge.
- ⇒ **Recommendation: plugin code does not go on the plug.** Built-in plugins (`codeRef`, e.g. the dev bench)
  ship in the app anyway. A DB-served signed plugin is better **cached in the app DB** at the last online login,
  where there is no size limit, and it is already signature-checked when loaded. The plug stays the
  **instrument's** memory (identity + calibration); the plugin is the **app's** business. The setup row in the
  copy still names the plugin (`codeRef` + version), so the app knows which one to load.
- ⭐ **Script slots tested 2026-10-19 (§7.3): even the dev bench fits** — 91 668 chars in 2 slots, identical
  round trip, 4 s to read. But it fills the flash to 24 KiB free. Option for later, not a plan.
- ✅ **Edwin, 2026-10-19: no plugin storage on the Shelly, for now.** The copy carries the plugin row only
  (`codeRef` + version), never its source.

### 3.6 ⭐ The target: setup + one user + one larger plugin, offline from the plug (Edwin, 2026-10-19)

Flash budget, from the measurements in §7.2/§7.3 (the plug reports flash in 4 KiB blocks), **rev 6 layout**
(§4.6: copy and plugin in script slots, KVS only index + signatures):

```
 file system 448 KiB ── used by the firmware's own files (not listable, see below) ──── 324 KiB
                     └─ free ───────────────────────────────────────────────────────── 124 KiB
                          reserve for the plug's own settings (password, WLAN, …)    −  16 KiB
                          KVS: index + 2 signatures (3 keys, ~400 B each)            −   2 KiB
                          slot 1: SQLite copy = setup + user + FULL spectrum, bz2    −  24 KiB   (5 without spectrum)
                          slot 2: dev bench plugin, stripped, bz2 (N14)              −  29 KiB
                          ════════════════════════════════════════════════════════
                          spare                                                      ≈  53 KiB
                          ⇒ the plugin alone may grow to ≈ 82 KiB stored (×2.8 of today's bench)
```

⚠ The §3.6 rows below were measured **before** rev 6, with the copy in KVS (8–16 KiB). With the copy in a slot
**with** the full spectrum (24 KiB), the plugin's headroom is **×2.8** instead of ×3.5 (×3.2 with packed spectrum):
(124 − 16 − 2 − 24) KiB ≈ 82 KiB ⇒ ~74 000 stored chars ⇒ 74 000 / 26 108 ≈ 2.8. Without the spectrum ≈ ×3.5.

| Dev bench plugin (205 KB source) | Stored size | Fits? | Buffer left |
|---|---|---|---|
| zlib + base64 (as tested, §7.3) | 91 668 chars ≈ 100 KiB flash | ⚠ exactly at the limit | **~0** |
| ⭐ **bz2 + base64** (measured) | **74 640** chars ≈ 80 KiB | ✅ | **~20 KiB** (~12 with spectrum) |
| lzma + base64 (measured) | 80 584 chars | ✅ | ~15 KiB |
| ⭐ **bz2, without docstrings and comments — all 6 bench files** (measured; ✅ Edwin's choice 2026-10-19) | **26 108** chars ≈ 29 KiB | ✅ | ~71 KiB |

- ⇒ **Possible.** With bz2, the largest plugin source that still fits is ≈ **260 KB** (the dev bench is 205 KB, so
  ~25 % growth). If the dev bench keeps growing past that, a stripped copy (no docstrings/comments, signed as such)
  buys ~4×.
- ⭐ **Growth headroom with Edwin's choice** (bz2, stripped; measured on all 6 bench files = 230 KB source → 81 830
  stripped → 26 108 chars): the bench can grow **×3.5** (to ~800 KB of source as written today) without the
  spectrum, **×3.2** (~740 KB) with the packed spectrum, assuming it keeps compressing the same way. Basis: the
  §7.3 measurement, 91 668 stored chars = exactly the space left after reserve + copy.
  ⚠ The signature must cover the **stripped** text (what is stored is what is signed).
- **The user** is one `app_user` row (+ role): the password is a **bcrypt** hash (`$2b$12$…`, 60 chars) ⇒ goes
  into the same SQLite copy, ~1 extra key. The app checks the password offline against that hash (§9).
  ⚠ Anyone with the standard plug password can **read** the hash; bcrypt cost 12 makes guessing slow, and the
  signature (§4.3) prevents **changing** it.
- **"Run from the plug"** = the plug **stores**, the app **runs**: at an offline start the app reads setup, user
  and plugin from the plug, verifies the signatures, and loads the plugin as it loads a sealed DB plugin today.
- **Where the other 324 KiB are:** the firmware's own files in the same file system (most likely its built-in web
  page and its settings and certificate files). The plug has no command that lists files, so this is **not
  verified**. The firmware program itself is not in these 448 KiB; it lives in a separate flash area.
- This supersedes Edwin's "no plugin storage on the Shelly, for now" (§3.5) **as the goal**; the order of work
  is still to be decided.

## 4 — The copy in KVS

### 4.1 Overview

```
 Shelly plug                                             server DB (authoritative)
 ──────────────────────────────────────────              ─────────────────────────────────────────
 id  shellyplusplugs-e86beae3cb60  (hardware) ── serial ─▶ SpectrometerProfile  serial = the plug id
   readable via GET /shelly, no password                    ├─▶ Spectrometer  InLight · Dynarex · GreenGold
                                                            └─▶ CalibrationProfile (later, on the box)
 KVS  spectracs_index/_sig     (2 keys)                    SpectrometerSetup (profile + plugin)
      spectracs_copy_0…n = 240-char chunks of an              │
                           SQLite file, zlib+b64 (~16) ◀─ rows of ┘  + alembic_version
```

- The **serial needs no storage**: the plug id is fixed and survives a reset (N6). The label on box and plug
  shows the MAC (N7) = the last 12 characters of the serial.

### 4.2 Keys

> ⚠ **Superseded by §4.6 (rev 6):** the copy now lives in a script slot; KVS keeps only the index and the
> signatures. The chunk layout below is kept as the measured fallback.

| Key | Value |
|---|---|
| `spectracs_index` | `{"v":1,"chunks":16,"len":3776,"rev":"<alembic rev>","sha256":"<64 hex>","key":"<keyId>","written":"2026-10-19T15:30:00Z"}` ≈ 190 chars |
| `spectracs_sig` | the Ed25519 signature over the copy, base64 = 88 chars. ⚠ Its own key: index + signature together measured **259 > 253** |
| `spectracs_copy_0` … `spectracs_copy_15` | the SQLite file (page size 1 024, spectrum left out), zlib-compressed, base64, split into **240-character** chunks |

- **Budget (measured, ELP rows):** 3 776 characters ⇒ **16 chunks + index + signature = 18 of 50 keys**.
  Headroom: a **DB-served signed plugin** (5.7 KB source, compresses well) adds roughly 10–24 chunks ⇒ still ≤ 50,
  but tight ⇒ S2 measures it. ⛔ With the spectrum (≥ 15.7 KB compressed ≈ 63 keys)
  it would **not** fit, which settles §3.1 from the other side too.
- 240, not 253: ✅ S0 measured it (§7.2): the limit is 253 on the **JSON-escaped** value; base64 is never
  escaped, so 253 would work too.
- ⛔ Reading: `KVS.GetMany` caps its answer at 2 048 bytes (S0) ⇒ the chunks are read **one `KVS.Get` each** (~2 s).
- **Write order:** the chunks first, the index **last**. Without an index (or with a `sha256` that doesn't
  match) the chunks are ignored ⇒ a write that breaks in the middle is detected, never half-used.
- `rev` = the server Alembic revision of the copy (from its `alembic_version` row), so the app knows before
  opening it whether it must migrate.

### 4.3 Signed by the master

With a **standard password** (N8) anyone who knows it can rewrite the copy, calibration included. ⇒ The copy is
**signed with Ed25519**, exactly like a sealed plugin (`PluginSignatureUtil`): the **master app signs** (PyNaCl,
`PluginSigner`), every app **verifies** with the vendored pure-Python Ed25519 against the trusted keys shipped
in the app. A factory tool inside the master app (N10) has that key at hand. An unsigned or altered copy is
**refused**. The password then only protects the lamp and the plug's settings.

### 4.4 The app at start

```
 1  discovery → GET /shelly → id = serial                       (no password)
 2  server reachable?
      yes → resolve serial as today; compare with the plug's index;
            plug copy missing or older → offer "update the plug's copy"
      no  → read the index + chunks (password) → check sha256 + signature → unpack to a temp SQLite file
            → migrate with the server Alembic tree if `rev` is older → open with the -model entities
            → use it, marked OFFLINE
 3  check: live camera hardware id = the copy's sensor (2bc5_0529); copy model = InLight-Dynarex-GreenGold
    any mismatch ⇒ no MEASUREMENT, with a message naming the part that disagrees
 4  self-registration pre-fills the serial from the plug
```

### 4.5 ⭐ Offline login — in the same sweep (Edwin, rev 4)

The copy makes the **instrument data** available offline. The app today also needs the server to **log in**
(server-side Pyro login, `SPEC_user_auth_login.md`), to save the measurement and to publish to the LIMS.
Edwin, 2026-10-19: **offline login is handled as soon as possible, in one sweep with the copy.** To be
designed (§9), at least:

- what the app checks offline instead of the server (e.g. a local, salted hash of the last successful
  online login, and the user's role from that login);
- how long an offline login stays valid;
- where an offline measurement waits (the app DB), and what is deferred until the server is back (LIMS, PDF
  upload, payment).

---

### 4.6 ⭐ rev 6: the SQLite copy in a script slot as well (Edwin's question, 2026-10-19)

Measured (SQLite page 1 024, ELP rows + 6 lines):

| Copy | zlib + base64 | bz2 + base64 | In KVS (keys) | In one script slot |
|---|---|---|---|---|
| without spectrum | 3 776 | 4 140 | 17 | ✅ 1 slot |
| packed uint16 spectrum | 8 100 | 8 796 | 35 | ✅ 1 slot |
| ⭐ **full spectrum, lossless** | 26 556 | **23 272** | ⛔ 107 | ✅ **1 slot** (≤ 65 535) |

| | KVS chunks (rev 3–5) | ⭐ Script slot (rev 6) |
|---|---|---|
| Spectrum | must be **packed (lossy)** to fit | **lossless**, as on the server ⇒ the uint16 packing (§3.4) is **dropped** |
| Read time | one `KVS.Get` per key: 2 s (17 keys) … 4 s (35) | 1–6 `GetCode` pieces of 4 KB: **< 1 s** (the 2.8 KB test read in 0.2 s) |
| Flash | ~400 B per key ⇒ 8–16 KiB | 4 KiB blocks ⇒ ~4–24 KiB, no per-key overhead |
| Limits | 50 keys × 253 | 65 535 per slot |
| One mechanism | KVS for the copy, slots for the plugin | **slots for both** big things; KVS only for small things |
| Risk | — | the 4 KB read rule (§7.3); slots appear in the plug's script list (`enable:false`) |

⇒ **Recommended.** Layout on the plug:

```
 KVS            spectracs_index   {v, rev, written, slots:{copy:1, plugin:2}, len, sha256 per slot}   1 key
                spectracs_sig_copy / spectracs_sig_plugin   Ed25519, 88 chars each                    2 keys
 script slot 1  spectracs_copy    SQLite (setup + profile + calibration WITH spectrum + user), bz2+b64   ~23 KB
 script slot 2  spectracs_plugin  the plugin, stripped, bz2+b64                                         ~26 KB
```

- **Torn writes:** a slot is written in pieces (`PutCode append`) ⇒ a break leaves a half slot. The index in KVS
  is written **last** and carries the `sha256` of each slot ⇒ a half slot never matches and is never used.
  Rewriting = write into a **new** slot, then switch the index, then delete the old slot (the old copy stays
  valid until the switch).
- The §3.4 budget rule (drop the spectrum first) still holds, but with slots it only bites past ~100 KiB.

Flash with N14 + N15 (dev bench as the plugin):

```
 free 124 KiB − reserve 16 − copy with full spectrum ~24 − plugin ~29 − KVS index+sigs ~2  ≈  53 KiB spare
```

### 4.7 ⭐ rev 7: one key-value provider over both storages (Edwin, 2026-10-19)

Edwin: *"an implementation that acts as a key-value provider from outside and uses script storage internally;
for small values it falls back to the Shelly's key-value pairs."*

```
   caller (copy builder, plugin bundle, factory tool, app start)
        │   set(key, value)  get(key)  delete(key)  keys()
        ▼
 ┌───────────────────────────── PlugKeyValueStore (-core, Qt-free) ─────────────────────────────┐
 │ encoded value ≤ 253 (JSON-escaped, §7.2)  ──▶  native KVS key  "spectracs_<key>"             │
 │ larger                                     ──▶  script slot(s) "spectracs_<key>" (+ "#2" …)  │
 │                                                 + META key in KVS "spectracs_m_<key>" =      │
 │                                                   {slots, len, sha256}   ← the commit point  │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
        │                                   │
   ShellyGen2 transport (real plug)    InMemory fake (unit tests, no plug)
```

**Contract**

| Call | Behaviour |
|---|---|
| `set(key, value)` | `value` = `str` or `bytes` (bytes are base64'd inside). Picks the storage by encoded size. **Atomic:** a large value goes into **new** slot(s); only when they read back with the right `sha256` is the meta key written; then the old slots are deleted. A crash in between leaves the **old** value valid. |
| `get(key)` | native key → its value; meta key → read the slots with `GetCode len ≤ 4096` (§7.3), check `len` + `sha256`, return. A mismatch = **missing**, never a half value. |
| `delete(key)` | meta key first, then its slots (or the native key). |
| `keys()` | our keys only (`spectracs_` prefix); orphan slots without a meta key are cleaned up on the next `set`. |

**Rules inside**
- Key names: KVS keys are ≤ 42 characters ⇒ `spectracs_m_` (12) leaves **30 characters** for the caller's key; no dots (R4).
- A value moving between sizes (small → large or back) deletes its other form.
- Slot spanning: one slot holds ≤ 65 535 bytes; a larger value spans `#2`, `#3` … The flash (~124 KiB free) is the
  real limit; `set` refuses before `fs_free` would drop below the 16 KiB reserve.
- **Not** inside the provider: compression and signatures. The caller compresses (bz2) and signs; the provider
  only stores text/bytes faithfully. That keeps it a plain store, testable with the fake.
- Password: the provider gets the plug password from the caller (app DB, N13).

**What it does to the layout (§4.6):** nothing changes on the plug, only who manages it:

```
 store.set("copy",   bz2+b64 SQLite)   → slot spectracs_copy   + meta spectracs_m_copy
 store.set("plugin", bz2+b64 bundle)   → slot spectracs_plugin + meta spectracs_m_plugin
 store.set("index",  {v, rev, …})      → native KVS spectracs_index
 store.set("sig_copy", "<88 b64>")     → native KVS spectracs_sig_copy
```

The per-slot `sha256` moves from the index into the meta keys, so the index only carries the copy's version
and revision.

## 5 — The factory tool (inside the app, details later — N10)

```
 1  find the plug           discovery (SPEC_lamp_switch §5), or the plug's own AP 192.168.33.1 when fresh
 2  harden the plug         standard password (N8 = SPEC_lamp_switch P7), initial_state off, auto-off,
                            LED ring (ammoBox-spec §5), firmware version recorded
 3  create on the server    SpectrometerProfile (serial = plug id, InLight-Dynarex-GreenGold)
                            + SpectrometerSetup (profile + plugin)
 4  write the plug          resolve the new serial on the server, sign, chunks → KVS, index LAST
 5  read back + verify      KVS.GetMany, sha256, signature; reboot the plug; read again
 6  (later) calibration     master calibration authoring on the box; then steps 4–5 again
```

- **Server first, plug second, index last.** Running the tool again is safe (idempotent by serial).
- **After a reset** the tool rewrites the copy from the server.
- **Replacing a broken plug** gives a **new serial**. The calibration belongs to the optics, not to the plug ⇒
  a "move this instrument to a new plug" action: new profile serial, same calibration.

---

## 6 — Rubber duck (rev 5)

- **R1 — Plug swap.** ✅ Accepted (N7). The camera can't help (USB serial `00000000`, both boxes `2bc5:0529`).
- **R2 — Factory reset** erases the copy, not the serial. ✅ The server rewrites it. ⚠ A reset while
  **offline** leaves the instrument unusable until the server is back.
- **⛔ R3 — A standard password is public** (public repos; readable from the app binary) ⇒ never in the repo;
  the signature (§4.3) protects the data. The user changes it under Settings → Lamp (`Shelly.SetAuth`), stored
  locally as today (D9, N13). ⚠ After a change, see R13.
- **R4 — No dots in KVS keys** ⇒ `spectracs_index`, `spectracs_sig`, `spectracs_copy_0`.
- **R5 — Two copies of one setup.** ✅ Allowed (N5): **the server wins whenever it is reachable**; never a merge.
- **R6 — 50 keys are shared with nothing else today.** If a later feature also uses KVS (e.g. lamp hours),
  it shares the budget ⇒ all our keys start with `spectracs_`, and the tool deletes only those.
- **R7 — Flash wear.** Writes only when the copy changed (compare `sha256` first), never at every start.
- **R8 — Serial format** changes for new instruments only (`ELP-0001`, `TEST-0001` stay). Code must accept the
  28-character id and never parse its prefix (the Gen3 plug is `shellyplugsg3-…`).
- **R9 — Spectrum only on the server.** Offline, the setup editor can't show the calibration spectrum. That is
  a master task anyway and needs the server.
- ~~R10 — The resolve response is now a stored format.~~ Void with N12: the resolve response stays a wire format.
- **R11 — The app needs the server's Alembic tree** to migrate an old copy. ✅ Both trees already live in
  -model (`SPEC_schema_migrations.md`), so the app ships it.
- **⛔ R12 — A copy NEWER than the app** (server migrated, app not updated): the app cannot downgrade it ⇒
  offline use is **refused** with "update the app".
  - ⭐ **Edwin (2026-10-19): the same problem exists without the Shelly**, between an old app and a newer server.
    Checked: it does, and **today nothing guards it**. `SpectracsPyServer.getVersion()` returns a hard-coded
    `'1.0.0'` and **no client calls it**; the only version check in the system is the plugin SDK check
    (`plugin_sdk/version.py`). An old app talking to a changed server fails wherever a field it expects is gone,
    with no clear message.
  - The difference is only *where* the newer data comes from: online from the server, offline from the plug.
    ⇒ **One rule for both:** the app knows the newest server schema revision it understands; the server reports
    its revision at login (replacing the dead `getVersion()`), the plug copy reports it in its index. Same check,
    same message ("update the app"). ⇒ Phase **S1b** (§7).
- **R13 — Password only in the app DB (N13).** A second computer, or a technician, does not know a password the
  user changed. ⇒ Their way in is the factory reset (§2), then the factory tool rewrites the plug from the
  server. Accepted with N13.
- **R14 — Migrating an SQLite file on the client** runs `alembic upgrade` on a temp file at start. It must be
  fast and silent; the copy is small, so it is, but it is a new code path ⇒ tested with an old fixture copy.

---

## 7 — Implementation phases

```
 ┌─────┬──────────────────────────────────────────┬────────────────────┬──────────────┬────────────────────────┐
 │ #   │ What                                     │ Where              │ Needs        │ Done when              │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S0  │ plug test: KVS write/read, the 253       │ rig (the plug)     │ DONE 10-19   │ limits known, data     │
 │     │ limit, reboot (§7.1/§7.2); script slots: │                    │              │ survives a reboot      │
 │     │ 64 KB/slot, 4 KB reads (§7.3); cleaned up│                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S1  │ seed: sensor Dynarex = 2bc5:0529,        │ -model, -server    │ —            │ server DB has the      │
 │     │ spectrometer InLight-Dynarex-GreenGold   │                    │              │ rows; tests green      │
 │     │ (InLight-Automat stays)                  │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S1b │ APP↔SERVER VERSION CHECK (R12): server   │ -server, app       │ —            │ an app older than the  │
 │     │ reports its schema revision at login;    │                    │              │ server's schema gets   │
 │     │ app refuses a newer one, same check as   │                    │              │ "update the app", not  │
 │     │ for the plug copy                        │                    │              │ a crash                │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S2  │ COPY BUILDER: setup + profile + calib.   │ -model (+ -core)   │ S1           │ unit test: ELP setup   │
 │     │ WITH spectrum + user rows → SQLite       │                    │              │ → ≤ 64 KB, signature   │
 │     │ (page 1024, alembic_version) → bz2 → b64 │                    │              │ verifies               │
 │     │ + sha256 + Ed25519 (master key)          │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S2b │ PLUGIN BUNDLE BUILDER: all files of one  │ -core, app (master)│ —            │ dev bench bundle       │
 │     │ plugin, docstrings + comments stripped,  │                    │              │ ≈ 26 KB, signature     │
 │     │ → bz2 → b64 + sha256 + Ed25519 over the  │                    │              │ verifies               │
 │     │ STRIPPED text (N14)                      │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S3  │ COPY READER: sha256 + signature → temp   │ -model (+ -core)   │ S2           │ round trip S2→S3 =     │
 │     │ SQLite → alembic upgrade → entities;     │                    │              │ same rows; old fixture │
 │     │ refuse: torn, unsigned, newer than app   │                    │              │ migrates; R12 refuses  │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S3b │ PLUGIN BUNDLE LOADER: verify, unpack,    │ -core, app         │ S2b          │ the bench runs from    │
 │     │ load like a sealed DB plugin (SDK check  │                    │              │ an unpacked bundle     │
 │     │ first); ⚠ multi-file = new for the loader│                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S4  │ PLUG KEY-VALUE STORE (§4.7): small →     │ -core              │ S0           │ against the real plug: │
 │     │ native KVS, large → script slots + meta  │                    │              │ write, read, compare,  │
 │     │ key as commit point; GetCode len ≤ 4096; │                    │              │ torn write ignored     │
 │     │ InMemory fake + ShellyGen2 transport;    │                    │              │                        │
 │     │ touch only spectracs_*                   │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S5  │ FACTORY TOOL in the master app (§5):     │ app (master)       │ S2–S4, P7    │ the box's plug carries │
 │     │ harden plug + standard password, create  │                    │              │ a verified copy +      │
 │     │ profile/setup, write + verify copy and   │                    │              │ plugin                 │
 │     │ plugin                                   │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S6  │ APP START (§4.4): serial from plug,      │ app                │ S5           │ server off → the box   │
 │     │ online = server, offline = copy + plugin │                    │              │ still resolves and     │
 │     │ from the plug, mismatch refusals,        │                    │              │ loads its plugin       │
 │     │ serial pre-fill                          │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S7  │ OFFLINE LOGIN (user row + bcrypt from    │ app, -server       │ §9 design    │ log in + measure with  │
 │     │ the copy) + offline results (§4.5, §9)   │                    │              │ the server off, sync   │
 │     │ — SAME SWEEP as S2–S6                    │                    │              │ afterwards             │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S8  │ move to a new plug; rewrite after reset  │ app (master)       │ S5           │ reset plug restored    │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S9  │ click-through on the rig: factory run,   │ rig                │ S1–S8        │ Edwin's click-through  │
 │     │ online start, offline start + login      │                    │              │                        │
 └─────┴──────────────────────────────────────────┴────────────────────┴──────────────┴────────────────────────┘
   order: S0 ∥ S1 ∥ S1b ∥ S2b → S2 → S3 ∥ S3b → S4 → S5 → S6 → S7 → S8 → S9   (S7 designed first, §9)
```

### 7.1 S0 in detail

| Step | What | Why | Undo |
|---|---|---|---|
| S0.1 | `KVS.Set` a dummy copy under `spectracs_test_*` (6 keys), `KVS.GetMany`, compare | the format works on the real firmware | `KVS.Delete` |
| S0.2 | one value at 253, 254, and 253 with `ä` (2 bytes) and `\"` | is the limit characters or bytes, and does JSON escaping count? ⇒ the safe chunk size | `KVS.Delete` |
| S0.3 | `Shelly.Reboot` (or 5 s button), read again | KVS really is in flash, not in RAM | — |
| S0.4 | ⚪ *optional* firmware update 1.3.3 → 1.7.5, read again | the plug offers it, and a user can start it in the Shelly app at any time ⇒ do our keys survive? **Not needed for us**; can wait until an update happens anyway | ⚠ none (no downgrade path planned) |
| S0.5 | ⚪ *optional* factory reset, check `GET /shelly` | confirms that the KVS is gone and the id stays. The docs already say so ⇒ **can be skipped** | ⚠ the plug forgets the WLAN: re-onboard through its AP `192.168.33.1` |

⇒ **Minimal S0 = S0.1–S0.3**, all undone at the end. S0.4/S0.5 only on a separate go.

### 7.2 ✅ S0.1–S0.3 RESULTS (run 2026-10-19 on Edwin's plug, fw 1.3.3, lamp off throughout)

Script: a throw-away test under the scratchpad (not in the repo), keys `spectracs_test_*` only.

| Step | Result |
|---|---|
| S0.1 | The real §3.3 copy (SQLite page 1 024 → zlib → base64 = **3 776 chars**) written as **16 chunks of 240 + index**, read back: **identical**; unpacked SQLite **29 696 bytes, identical byte for byte**. |
| S0.1 | ⛔ **`KVS.GetMany` refuses any answer over 2 048 bytes** (error −108, "Reached the maximum 2048 of response bytes"), also with `offset` ⇒ no paging. ⇒ The reader uses **`KVS.List` + one `KVS.Get` per key**: 20 keys in **1.8–2.0 s**. |
| S0.2 | Plain ASCII: **253 accepted, 254 refused** ("length should be less than 255"). |
| S0.2 | ⚠ The limit counts the **JSON-escaped** value: `ä` + 251 (252 characters, 253 bytes) and `"` + 252 (253 characters) were **refused**. Base64 has neither ⇒ **base64 chunks may use the full 253**; 240 stays as the safe default. |
| S0.3 | `Shelly.Reboot`: back after **~6 s**, all 20 keys **identical**, output stayed **off** (`initial_state` off). |
| flash | 20 keys took **8 KiB** of `fs_free` (126 976 → 118 784), ≈ 400 B per key ⇒ all 50 keys ≈ 20 KiB of the 124 KiB. Fully returned after the delete. |
| clean-up | 20 test keys deleted; KVS holds **0** keys; `fs_free` back to 126 976. |

Consequences for the design:
- §4.2 budget unchanged (16 chunks at 240; 15 at 253).
- **S4 (transport) must read key by key** and allow ~2 s for the offline start; writing is the same order.
- `KVS.GetMany` may still be used for the **index alone** (small answer), never for the chunks.

### 7.3 ✅ Script-slot storage test — holding a plugin (Edwin, run 2026-10-19, fw 1.3.3, lamp off throughout)

Scripts named `spectracs_test_*`, created **disabled** and never started; payload = plugin source, zlib + base64.

| Test | Result |
|---|---|
| `PutCode` chunk size | 1 024 … **16 384** all accepted (larger not tried). |
| ⭐ size per slot | **65 535 bytes** ("Script length exceeded 65535 bytes limit!"). |
| Pumpkin plugin (2 800 chars) | **1 slot**, read back in **0.2 s**, unpacked **identical** to `PumpkinOilPlugin.py`; 4 KiB of flash. |
| ⭐ Dev bench plugin (91 668 chars) | **2 slots** (49 152 + 42 516), unpacked **identical** to `DevSpectralPlugin.py` (204 685 bytes); read in **4.0 s** in 4 KB pieces. |
| flash | 126 976 → **24 576** free with the dev bench stored (≈ 100 KiB used). Guard in the test: stop before 16 KiB. |
| ⛔⛔ whole-slot read | `Script.GetCode` **without `len`** on the 49 KB slot: no answer, the **plug rebooted itself** (uptime 14 s). Lamp stayed off; the data survived. ⇒ **always read with `len` ≤ 4 096** (1 024 / 2 048 / 4 096 tested fine; larger not tried, to avoid more crashes). |
| reboot | the unplanned reboot above: both slots intact afterwards ⇒ stored in flash. |
| number of slots | ≥ 2 confirmed (the limit was not reached; the flash runs out first). |
| clean-up | all test scripts deleted; 0 scripts, 0 keys, `fs_free` back to 126 976. |

Consequences:
- Script slots hold **up to ~64 KB each**, and the flash (~124 KiB free) is the real limit: **one** dev-bench-sized
  plugin fits, with ~24 KiB left for the plug itself.
- Any reader of script slots must use `len` ≤ 4 096. A careless read can crash the plug.

---

## 8 — Open questions for Edwin

1. ~~Q1: go for the minimal S0~~ ✅ run 2026-10-19, §7.2.
2. **Q5:** design offline login (§9) now, before S2, so the sweep S2–S7 can start in one go?
3. ~~Q6: plugin code on the plug?~~ First "no, for now" (§3.5), then ✅ **one larger plugin is the goal** (N14, §3.6).

## 9 — Offline login (S7) — to be designed

Placeholder for the design in §4.5, same sweep as the copy. Input already settled: the user row with its bcrypt
hash travels in the copy (§3.6).
