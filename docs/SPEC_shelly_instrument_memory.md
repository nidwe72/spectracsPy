# SPEC — The Shelly as the instrument's memory (factory provisioning)

**Status:** ✅ **rev 10 L1–L6 IMPLEMENTED 2026-10-20** (§11.15) + firmware update (§11.16); L7 click-through part 1 ✅ A+B (§11.17), C–E open. ✅ **S0–S8 IMPLEMENTED + PUSHED 2026-10-19** (§10 as built, 775 tests green; app, -model, -server, -core).
◐ **S9 partly clicked through by Edwin** (offline login, the page offline, the Spectrometer/Style lists: "works so
far"); the rest of §10.3 continues with the story. The box's copy is on the real plug.
**Comes from:** `SPEC_ammo_box_camera.md` phase P1 (H3/H4 in `spectracs-hardware/ammoBox-spec.md`). Edwin
decided on 2026-10-19 that this gets its own spec, not a section in `SPEC_lamp_switch.md`.
**Builds on:** `SPEC_lamp_switch.md` (driver, discovery, `lamp_plug` row, password D9),
`SPEC_connection_and_calibration_ux.md` (serial → `SpectrometerProfile` → `SpectrometerSetup`, server-authoritative;
the resolve call `InstrumentLogicModule.resolveBundle`) and `SPEC_plugin_distribution.md` (Ed25519 signing, §4.3).

**rev 10 (Edwin, 2026-10-20):** one setup editor, registered-only switching, `LightSourceController` on the profile, BLE onboarding, default plug password = MAC, Prepare for shipping, workflows F1–F6 / C1–C8 — DESIGN, §11 (phases §11.13).

**Revisions.** rev 1: identity only on the plug. rev 2 (Edwin): the whole setup as an offline copy, serial =
plug id, standard password. **rev 3 (Edwin):** the calibration spectrum is not needed ⇒ the copy is ~1 KB ⇒
it is **spread across KVS pairs**, script slots dropped; JSON needs versioning too ⇒ the copy **is the
server's existing resolve response**, so there is no new format to version. **rev 4 (Edwin):** SQLite measured
(fits, ~17 keys compressed, §3.3); offline login in the same sweep (§4.5, S6); S0 spelled out (§7.1).
**rev 5 (Edwin):** the copy is **SQLite** (N12); the changed plug password lives in the **app DB** (N13);
implementation phases laid out (§7).
**rev 9 (Edwin):** a seeded dev instrument + `masterUserDynarex` as step S1 (§7.4), so the box can be logged
into before any plug code exists.
**rev 8:** offline login designed (§9); the copy is built and signed by the **server**.
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

### 4.3 Signed — the plugin by the master, the copy by the server (corrected in rev 8, §9.4)

With a **standard password** (N8) anyone who knows it can rewrite the copy, calibration included. ⇒ The copy is
**signed with Ed25519**, exactly like a sealed plugin (`PluginSignatureUtil`): the **master app signs** (PyNaCl,
`PluginSigner`), every app **verifies** with the vendored pure-Python Ed25519 against the trusted keys shipped
in the app. A factory tool inside the master app (N10) has that key at hand. An unsigned or altered copy is
**refused**. ⚠ **rev 8:** this holds for the **plugin** bundle. The **copy** (setup + user) must be re-signed
whenever the end user's app refreshes it, and the end user's app has no master key ⇒ the **server** signs the
copy with its own key (§9.4). The password then only protects the lamp and the plug's settings.

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
 │ S1  │ SEED the box as a dev instrument (§7.4): │ -model (seed)      │ —            │ server restart → login │
 │     │ chip + sensor Dynarex 2bc5:0529,         │                    │              │ masterUserDynarex →    │
 │     │ spectrometer InLight-Dynarex-GreenGold,  │                    │              │ bench opens on the box │
 │     │ instrument (serial = plug id, pumpkin,   │                    │              │ (capture: camera P3)   │
 │     │ empty calibration) + masterUserDynarex   │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S1b │ APP↔SERVER VERSION CHECK (R12): server   │ -server, app       │ —            │ an app older than the  │
 │     │ reports its schema revision at login;    │                    │              │ server's schema gets   │
 │     │ app refuses a newer one, same check as   │                    │              │ "update the app", not  │
 │     │ for the plug copy                        │                    │              │ a crash                │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S2  │ COPY BUILDER: setup + profile + calib.   │ -server, -model    │ S1           │ unit test: ELP setup   │
 │     │ WITH spectrum + user rows → SQLite       │                    │              │ → ≤ 64 KB, signature   │
 │     │ (page 1024, alembic_version) → bz2 → b64 │                    │              │ verifies               │
 │     │ + sha256 + Ed25519 (SERVER copy key, §9) │                    │              │                        │
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
 │ S7  │ OFFLINE LOGIN (§9): end user + all       │ app, -server       │ S2–S6        │ server off → login →   │
 │     │ masters from the copy, bcrypt check,     │                    │              │ measure → PDF; user    │
 │     │ isOffline badge, Publish disabled;       │                    │              │ disabled online →      │
 │     │ rewrite plug only on change (§9.5)       │                    │              │ refused offline later  │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S8  │ move to a new plug; rewrite after reset  │ app (master)       │ S5           │ reset plug restored    │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ S9  │ click-through on the rig: factory run,   │ rig                │ S1–S8        │ Edwin's click-through  │
 │     │ online start, offline start + login      │                    │              │                        │
 └─────┴──────────────────────────────────────────┴────────────────────┴──────────────┴────────────────────────┘
   order: S0 ∥ S1 ∥ S1b ∥ S2b → S2 → S3 ∥ S3b → S4 → S5 → S6 → S7 → S8 → S9   (S1 first: it gives the login)
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

### 7.4 S1 in detail — the box as a seeded dev instrument + `masterUserDynarex` (Edwin, 2026-10-19)

Goal (Edwin): *"set up a user masterUserDynarex analogous to masterUserExakta and a SpectrometerSetup for the new
spectrometer analogous to the existing one, directly in the database, as one implementation step, so we can start
up with the login from that."*

**As-is pattern (read in the code):** `UserSeedLogicModule.seed()` runs at every server start and is idempotent.
`__seedElpInstrument` calls `PersistSpectrometerSetupLogicModule.getOrCreateInstrument(ELP_SERIAL, elp.id,
pumpkin.id)` (empty calibration + profile + setup), and `__seedExaktaMasterUser` creates `masterUserExakta`
(MASTER_USER, password = username) bound to `ELP-0001`. The catalog rows come from the transient lists in
`SpectrometerSensorChipUtil`, `SpectrometerSensorUtil`, `SpectrometerUtil` (get-or-create by key).

**The step, analogous, five additions in -model:**

| # | Where | What | Key |
|---|---|---|---|
| a | `SpectrometerSensorChipUtil` | chip placeholder **`Orbbec_0529`** (the board's real chip is unknown; the ELP's `Sony_IMX1234` is a placeholder too) | `vendorName_productName` |
| b | `SpectrometerSensorUtil` | sensor **`Dynarex`**: vendorId `2bc5`, modelId `0529`, vendorName `Orbbec`, sellerName `unbranded`, description "ammo-box camera", chip a | `codeName` |
| b′ | `SpectrometerSensorUtil.__CAPTURE_SETTINGS_BY_HARDWARE_ID` | `'2bc5_0529': SpectrometerSensorSettings(None, None)` — "TBD", like the Microdia | hardware id |
| c | `SpectrometerUtil.getTransientSpectrometers` | **`InLight` · `Dynarex` · `GreenGold`**, vendor Spectracs | `getName()` |
| d | `UserSeedLogicModule` | `DYNAREX_SERIAL = "shellyplusplugs-e86beae3cb60"` (N6: serial = Edwin's plug id); `__seedDynarexInstrument` = `getOrCreateInstrument(DYNAREX_SERIAL, inLightDynarex.id, pumpkin.id)` | serial |
| e | `UserSeedLogicModule` | `DYNAREX_MASTER_USER = ("masterUserDynarex", "masterUserDynarex", MASTER_USER)`, `__seedDynarexMasterUser` bound to `DYNAREX_SERIAL` | username |

**Rubber duck — implementation**

- **D1 — "Directly in the database" = the seed, not a one-off SQL insert.** A hand insert would exist only in
  today's DB file; a fresh DB (Windows VM, AppImage, a deleted DB, the test DB) would not have it. The seed *is* a
  direct DB write, at server start, repeatable. Edwin's intent ("no factory tool, no UI") is met.
- **D2 — Order.** chip → sensor → spectrometer → instrument → user. The get-or-create utilities already resolve
  in that order (`SpectrometerUtil` asks `SpectrometerSensorUtil` asks the chip util); the seed only appends its
  two methods after `__seedExaktaMasterUser`.
- **D3 — Copy-paste debt.** `__seedElpInstrument` and `__seedExaktaMasterUser` already repeat the
  create-user-with-role block three times. ⇒ The Dynarex pair **reuses one private helper**
  `__getOrCreateUser(username, password, roleType)` instead of a fourth copy; the existing callers move onto it in
  the same step (behaviour unchanged, covered by the seed test).
- **D4 — The serial is a real device id in a public repo.** It is already in this spec; it identifies a plug, not
  a person, and the plug is behind a password once P7 is done. Accepted (like `ELP-0001`).
- **D5 — The calibration starts EMPTY.** `resolveBundle` returns `calibration: None` (no coefficient A) ⇒ login
  works, the bench opens and asks for a calibration. Authoring it on the box = camera spec **P5**, not this step.
- **⛔ D6 — Measuring stays blocked until camera spec P3.** With no settings for `2bc5_0529`, capture falls back to
  the global constants (2592×1944, WB 6500 K), and the box camera has WB 0–255 ⇒ `SPEC_ammo_box_camera.md` E5:
  read-back ≠ request ⇒ MEASUREMENT refused. ⇒ S1's "done when" is **login + bench opens + camera recognised**,
  not a measurement.
- **D7 — No schema change** ⇒ no Alembic migration; only rows. Existing rows are untouched (idempotent keys).
- **D8 — Which DB.** The seed writes the **server** DB; start the server with `runServer.sh` so it is
  `~/.spectracsPy-server/spectracsPyServer.db` (CWD gotcha). The app's local DB gets the new catalog rows through
  the existing `syncSpectrometers` at app start.
- **D9 — The camera lookup is generic** (`SensorCaptureIndexResolver` matches vendorId/modelId) ⇒ no code change
  for the box camera to be found and the connection indicator to go green.
- **D10 — The pumpkin plugin as the setup's plugin**, like the ELP setup. The dev bench is a built-in master view
  and does not depend on the setup's plugin (as with `masterUserExakta`).
- **D11 — Tests:** one new seed test against a temp server DB: seed twice ⇒ one `Dynarex` sensor, one
  `InLight-Dynarex-GreenGold`, one profile with `DYNAREX_SERIAL`, `masterUserDynarex` has MASTER_USER and the
  serial; `LoginLogicModule.login("masterUserDynarex", …)` ⇒ `ok`, `spectrometerDevice == "Dynarex"`,
  `calibration is None`. Then the whole suite.

---

## 8 — Open questions for Edwin

1. ~~Q1: go for the minimal S0~~ ✅ run 2026-10-19, §7.2.
2. ~~Q5: design offline login (§9) now?~~ ✅ designed, rev 8 (§9); its open points are Q7–Q10 (§9.10).
3. ~~Q6: plugin code on the plug?~~ First "no, for now" (§3.5), then ✅ **one larger plugin is the goal** (N14, §3.6).

## 9 — Offline login (S7) — DESIGN (rev 8, 2026-10-19)

### 9.1 What login does today (read in the code)

- `LoginLogicModule.login` (server): checks `bcrypt` against `app_user.passwordHash`, then calls
  `InstrumentLogicModule.resolveBundle(registeredSerial)` and returns **one dict**: user id, username, roles,
  serial, plugin `codeRef` + version, device code name, calibration. Never the hash.
- `CurrentUserSession` (app) keeps that dict **in memory**; there is no session token. Logout drops it.
- After login the app uses the server for: plugin source (`getPluginSource`, sealed DB plugins), the startup
  sync of spectrometers and spectral-line master data, **LIMS publishing** (`publishSampleToLims`), payments, user
  and instrument administration (master).
- The PDF report is written **locally** (file dialog) and needs no server.

⇒ Offline login = produce **the same dict** without the server, from the plug. Everything after login that
reads `CurrentUserSession` keeps working unchanged.

### 9.2 Flow

```
 Login dialog (unchanged: username + password)
   │
   ├─ server reachable ──▶ login as today ──▶ ONLINE session
   │                        └─ afterwards: rewrite the plug ONLY IF the copy changed (§9.5)
   │
   └─ server unreachable (the existing "server unavailable" path, after the Pyro timeout)
        │
        ├─ plug found (discovery) and its copy valid (sha256 + server signature, §9.4)?
        │     no  ──▶ "Server not reachable, and no usable instrument data on the plug." (as today)
        │     yes ──▶ user row in the copy with this username, enabled, bcrypt(password) matches?
        │               no  ──▶ "invalid credentials" (same generic message as online)
        │               yes ──▶ build the login dict from the copy ──▶ OFFLINE session
        ▼
 OFFLINE session = CurrentUserSession + isOffline = True; header badge "OFFLINE · data from <date>"
```

- **Same dialog, same message wording, no extra click.** The user does not choose "offline"; the app falls back
  when the server is not there.
- The **startup sync** (spectrometers, spectral lines) is skipped offline; the copy brings what the instrument needs.
- ⚠ **"Offline" means without the server, not without a network.** The plug must still be reachable: on the
  lab WLAN, or through the plug's own access point `192.168.33.1` (`ammoBox-spec.md` A12, "Rückfallweg").

### 9.3 Who is on the plug (Edwin, 2026-10-19)

- **The one end user bound to this instrument** (Q10: one end user per box for now): `app_user.registeredSerial` =
  the plug id. Their row (username, `bcrypt` hash, display name, enabled) and roles.
- ✅ **Master users too** (Q7, Edwin: "yes"): a master may measure offline on a box. ✅ **Q11 (Edwin): all
  enabled master users go onto all plugs** (a few rows, ~100 bytes each compressed). A master *may* carry a
  serial (`masterUserExakta` → `ELP-0001`, checked in the seed), but is not limited to that box.
  Offline they get the same measuring functions as online; administration still needs the server (§9.6).
- ⛔ **Q11 WITHDRAWN 2026-10-20 (Edwin, Q17 / R40):** only users **registered for this spectrometer**
  (`registeredSerial` = the plug id) go on the plug, **whatever their role**. A master not registered for a
  box logs in online there. On the box: only `masterUserDynarex`.

### 9.4 Who signs the copy — the server (correction to §4.3)

The copy is refreshed from the **end user's** app after an online login (§9.5). That app holds no master key, so
it cannot sign. ⇒ The **server builds the copy and signs it** with an **instrument-copy key** of its own; its public
key ships in the app next to the plugin keys (same `trustedKeys` mechanism, a different `keyId`). The app only
**carries** bytes from the server to the plug. The plugin bundle stays **master-signed** (§4.3).
- ⚠ The server needs a private key on disk (server config, never in a repo; R3).

### 9.5 Writes to the plug: only when the data changed (Edwin, 2026-10-19)

Rev 8 first proposed a **lease**: a "valid until" date (nothing to do with payment), renewed on the plug at
online logins, so that offline login stops working after N days without the server. Edwin: *a write should only
happen when the data has changed.* ⇒ **The lease is dropped.**

```
 after every ONLINE login:
   server builds the copy (setup + users) ──▶ sha256 ──▶ equal to the plug's?  ──▶ yes: NO write
                                                                                └▶ no:  write the copy (§4.7)
```

- The copy changes when the setup, the calibration, or a **user** on it changes (password, enabled, roles) ⇒ a
  user disabled on the server is written to the plug at the **next online login on that box**, because that *is*
  a change.
- What is lost without the lease: a box that **never** goes online again keeps its last state for good (a
  disabled user can still log in offline there). Accepted for now.
- Flash: writes only on real changes ⇒ a few per year.
- To compare without reading the whole slot: the meta key `spectracs_m_copy` already holds the `sha256` (§4.7) ⇒
  **one** `KVS.Get` per online login, no write.

### 9.6 What works offline, and what waits

| Function | Offline | How |
|---|---|---|
| Login (end user and master) | ✅ | §9.2, from the copy |
| Instrument (device, calibration, plugin) | ✅ | copy + plugin bundle from the plug (S3/S3b), or a built-in plugin |
| Lamp | ✅ | the plug, as today |
| Measure, evaluate, PDF report | ✅ | local, as today |
| **Publish to the LIMS** | ⛔ **disabled** | Edwin: delayed offline publishing **not for now**. The button says "needs the server"; the PDF can still be saved |
| Payment, account settings | ⛔ | "needs the server" |
| User / instrument administration (master) | ⛔ | needs the server |
| Startup sync | skipped | — |

### 9.7 ⏸ Postponed: an outbox for LIMS publishing

Edwin, 2026-10-19: postponed. Sketch kept for later: an app-DB table `DbPendingPublication` (`userId`, `serial`,
`createdAt`, `limsInfoJson` with the **measurement** time, `pdfBlob`, `state`, `lastError`), sent after the next
online login.

### 9.8 Security summary

| Threat | Covered by |
|---|---|
| Reading the password hashes from the plug (standard password) | `bcrypt` cost 12 ⇒ slow guessing. Not prevented. |
| Changing a hash, a role or the calibration on the plug | server signature (§9.4) ⇒ refused |
| Copying another box's copy onto this plug | the copy contains the serial = plug id ⇒ refused |
| Disabled user keeps logging in offline | until the next online login on that box (§9.5); ⚠ forever on a box that never goes online |
| A new PC that was never online | works, if the plug password is the standard one or typed in (N13) |

### 9.9 Phases (inside S7)

```
 S7.1  server: instrument-copy key; build + sign the copy incl. the     -server, -model
       box's end user and all enabled masters
 S7.2  app: offline login (user row from the copy, bcrypt check),       app
       CurrentUserSession.isOffline, header badge, Publish disabled
 S7.3  app: after online login compare sha256, write only on change     app
 S7.4  click-through: server off → login (end user, then master) →      rig
       measure → PDF; user disabled online → next online login →
       server off → that user refused
```

### 9.10 Questions

- ~~Q7: may a master measure offline?~~ ✅ yes (§9.3).
- ~~Q8: lease duration?~~ ✅ void, no lease (§9.5).
- ~~Q9: outbox?~~ ✅ not for now, *Publish* disabled offline (§9.6/§9.7).
- ~~Q10: several end users per box?~~ ✅ one end user for now.
- ~~Q11: all masters or selected?~~ ✅ all enabled masters on all plugs (§9.3).

---

## 10 — ✅ As built (2026-10-19)

Edwin: *"impl all S phases now"*. S0–S8 built; S9 is Edwin's click-through. Full suite **772 passed** (716 before,
56 new). Nothing committed.

| Phase | Where | What |
|---|---|---|
| S1 | -model | chip `Orbbec_0529`, sensor `Dynarex` 2bc5:0529 (+ `'2bc5_0529'` settings placeholder), spectrometer `InLight-Dynarex-GreenGold`; `UserSeedLogicModule`: `DYNAREX_SERIAL`, `__seedDynarexInstrument`, `__seedDynarexMasterUser`; the four create-user blocks folded into `__getOrCreateUser` + `__bindSerial` (D3) |
| S1b | -model, app | `LoginLogicModule` returns `serverSchemaRevision`; `DatabaseInitializer.getServerScriptRevisions/Head/DatabaseRevision/upgradeServerSchemaOn`; app `logic/server/ServerCompatibility.py`; `SpectracsPyServerClient.login` refuses a newer server |
| S2 | -model, -server, -core | `logic/instrument/InstrumentCopyLogicModule.py` (SQLite page 1 024, server DDL, `order by rowid` ⇒ byte-identical copies), `InstrumentCopySigner.py` (PyNaCl, own key), `-core logic/security/InstrumentCopySignatureUtil.py`; RPC `getInstrumentCopy(username, password, serial)` (credentials + bound-or-master) |
| S2b | -core, app | `-core logic/security/PluginBundleUtil.py` (strip, tuple, verify, pack); `PluginSigner.signBundle`; app `logic/spectral/plugin/PluginBundle.py` `PluginBundleBuilder` |
| S3 | -model | `logic/instrument/InstrumentCopyReader.py` (sha256, signature, revision gate, Alembic upgrade of an old copy on a temp file, ORM read); `InstrumentLogicModule.bundleFromSetup` shared with `resolveBundle`; server `alembic/server/env.py` takes a passed connection |
| S3b | app | `PluginBundleLoader` (meta-path finder, app's own modules put back afterwards); `PluginRegistry.offlineBundleSource` hook in `resolve` |
| S4 | -core | `logic/plugstore/PlugKeyValueStore.py`, `PlugStoreTransport.py` (+ `InMemoryPlugStoreTransport`), `ShellyGen2PlugStoreTransport.py`; `ShellyHttp.post` (JSON-RPC, digest for POST); `LampErrors.ShellyRpcError` |
| S5 | app | `logic/instrumentMemory/InstrumentFactoryLogicModule.py` (harden/createOnServer/write/verify/moveHere); page `view/settings/instrumentPlug/InstrumentPlugViewModule.py` = Settings → Administration → **Instrument plug** (stack index 20) |
| S6 | app | `logic/instrumentMemory/PlugInstrumentMemory.py`: `PlugLocator` (before login), `PlugInstrumentMemory` (copy/plugin keys, index last), `PlugInstrumentSync` (background, after online login, write only on change); registration pre-fills the serial |
| S7 | app | `OfflineLoginLogicModule` (same dict as online + `offline`); `CurrentUserSession.offline/offlineBundle/isOffline`; `installFromSession` uses the offline bundle; `LoginViewModule` falls back on "server unavailable"; header **OFFLINE** badge; bench *Publish* disabled offline |
| S8 | -model, -server, app | `InstrumentAuthoringLogicModule.moveToSerial` + RPC `moveInstrumentToSerial`; factory "Move instrument here" |

Keys: **`spectracs-keys/instrumentCopy.seed`** generated (mode 600, backup in `spectracs-keys/backup/`), public half
in `TrustedKeys.TRUSTED_COPY_KEYS` (`ff8fa4e8a10f8b2f`) — a list separate from the plugin keys.

Tests: `test_dynarex_instrument_seed.py` (5), `test_server_compatibility.py` (5), `test_plug_key_value_store.py`
(15), `test_instrument_copy.py` (11), `test_plugin_bundle.py` (5), `test_offline_instrument_plug.py` (15).
`FakeShellyServer` now speaks POST /rpc, KVS.*, Script.*, Sys.GetStatus, Switch.Set/GetConfig, Shelly.SetAuth.

### 10.1 Run on the real rig (2026-10-19, plug fw 1.3.3, no password, lamp off throughout)

| Check | Result |
|---|---|
| S4 store on the plug | 70 KB value in 2 slots, write 9.0 s / read 4.2 s, identical; deleted again |
| ⛔ **atomic rewrite of a big value** | refused: old (93 KB) + new do not fit 124 KiB together ⇒ `set(..., replaceInPlace=True)` (old first; used for the plugin by the factory tool only) |
| seed on the real server DB | `masterUserDynarex` → `shellyplusplugs-e86beae3cb60`; login gives `Dynarex`, revision `405d2ce2cec1` |
| copy built + signed with the real key | 4 660 chars (no spectrum yet: the box is not calibrated) |
| written to the real plug | 2.0 s; **second write skipped** (unchanged, 0.2 s) |
| verify | "valid · Dynarex · 3 users" (masterUserDynarex + every master) |
| offline login against the real plug | ✓ in 1.9 s, MASTER_USER; wrong password refused |
| ⚠ **left on the plug** | `spectracs_index`, `spectracs_m_copy`, `spectracs_sig_copy` + 1 slot (12 KiB) — the box's real data, for S9 |

### 10.2 Deviations and open points

- **The setup's plugin (pumpkin 1.0) is a bare seed row ⇒ a built-in**: the factory stores no plugin for it ("ships
  with the app"). A plugin goes onto the plug only for a **sealed** DB version; the bundle loader is tested with
  the whole dev bench (6 files) but no instrument uses it yet.
- **Standard password (P7):** read from `SPECTRACS_PLUG_STANDARD_PASSWORD` or `../spectracs-keys/plugStandardPassword.txt`
  (relative to the app's working dir, like the plugin key). ⏸ **Neither exists yet** ⇒ *Harden plug* refuses until Edwin
  creates the file. Not run on the real plug (it would change how the lamp is reached).
- **The running server** (started 15:02) has the old code ⇒ **restart it** for `getInstrumentCopy` /
  `moveInstrumentToSerial`. The seed already ran on its DB (in-process).
- **Frozen/Android server:** copy signing needs PyNaCl. The dev server has it; the server AppImage should bundle it
  (check `nacl` in the next `buildAppImages.sh`); the Android server does not ship it ⇒ there `getInstrumentCopy`
  fails with a message, the rest is unaffected.
- `moveInstrumentToSerial` is unauthenticated like the other MASTER RPCs (`saveSpectrometerProfile`, …): the role
  gate on RPCs (`SPEC_user_auth_login.md` phase G) is still not built. `getInstrumentCopy` checks credentials
  because it hands out password hashes.
- The offline fallback starts only after the client gave up on the server (Pyro timeout per candidate host) ⇒ an
  offline login takes those seconds plus ~2 s on the plug.
- Seen, not changed: the registration path does not call `installFromSession` after its auto-login (pre-existing).
- **Fixed after Edwin's first offline test (2026-10-19):** the factory page was locked to "master AND online", so offline
  it showed neither plug nor serial. Now: offline it still finds the plug, shows plug + serial and allows *Find* and
  *Verify* (plug only); *Harden*, *Create*, *Write*, *Move* stay online-only, with a note on the page.
- **Tooltips** on every button of the page; the page test checks that each has one.
- **Spectrometer + Style next to Camera (Edwin, 2026-10-19):** *Create on server* used to send only the camera
  code name, and the server took the **first** spectrometer with that camera. Edwin: *a camera model can sit in
  different spectrometers* ⇒ the page has three lists, **Spectrometer** (model name, default InLight), **Camera**
  (default Dynarex), **Style** (default GreenGold). `saveSpectrometerProfile(serial, device, calibration,
  modelName, styleId)` (server RPC + client) finds the exact triple and **creates the `Spectrometer` row** (vendor
  Spectracs) if the combination is new; an unknown camera or style is refused. Without `modelName`/`styleId` (the
  setup editor) the old camera-only lookup stays. Test: `SpectrometerTripleServerTest`.
- **Found 2026-10-19, fixed: duplicated catalog in the app's local DB.** `syncSpectrometers` matched the server's
  catalog **by id**, but the app's own get-or-create (`SpectrometerUtil.getSpectrometers` & co.) gives local rows
  their own uuids ⇒ every vendor/style/camera/chip/spectrometer existed twice in `~/.spectracsPy/spectracsPyServer.db`
  (surfaced by the seed test: two Orbbec 0529 chips). Fix: the sync matches by **natural key** (vendorId,
  model+camera+style, codeName, chip vendor_product). Test: `test_sync_spectrometers.py`. The existing duplicates
  are deleted by hand (server ids kept, local profiles re-pointed; backup
  `spectracsPyServer.db.bak-2026-10-19-dedup`). The server DB was never affected.

### 10.3 S9 — Edwin's click-through

◐ **2026-10-19, partly done:** offline login as `masterUserDynarex` ✓, the page offline shows plug + serial ✓ (after the
fix in §10.2), tooltips and the Spectrometer/Style lists ✓ — Edwin: *"works so far"*. Open: 2 (sync console line),
3 [Verify] online, 4 Publishing disabled offline, 5 Harden.

```
 1  restart the server (runServer.sh)
 2  app: login masterUserDynarex / masterUserDynarex          → online; console: "PlugInstrumentSync: unchanged"
 3  Settings → Administration → Instrument plug               → plug found, serial = shellyplusplugs-e86beae3cb60
    [Verify]                                                  → "valid · Dynarex · 3 users"
 4  logout, STOP the server, login masterUserDynarex          → header OFFLINE, camera found, bench opens
    bench → Publishing tab                                    → "needs the server", button disabled
 5  (optional) create ../spectracs-keys/plugStandardPassword.txt → [Harden plug] → Settings → Lamp still switches
```

---

## 11 — Rev 10: one setup editor, registered-only switching, lamp switch as a concept — DESIGN (Edwin, 2026-10-20)

**Why.** The Instrument plug page (S5/S8) and the Spectrometer setup page both create the same
`SpectrometerProfile` + `SpectrometerSetup` rows. Only the plug page picks the spectrometer as **model / camera /
style** (the server creates the triple if new), and only the setup page can calibrate. And with several Shellys in
one room, `LampDiscovery.discover()` falls back to `found[0]` ⇒ a fresh PC can switch **someone else's plug**.

### 11.1 Decisions (Edwin, 2026-10-20)

| # | Decision |
|---|---|
| E1 | **Serial = plug device id stays** (N6). The firmware builds it as `<app id lowercase>-<mac lowercase>` (`PlusPlugS` + `E86BEAE3CB60` ⇒ `shellyplusplugs-e86beae3cb60`). Model in the name, swap ⇒ new serial (Move), one instrument per room: all accepted. A future Pi design supplies its id by other means. |
| E2 | The serial lives only on **`SpectrometerProfile.serial`** (one setup → one profile → one spectrometer). Fix the stale "XXXX-XXXX" comment on `AppUser.registeredSerial`. |
| E3 | **The Spectrometer setup page is the only editor** of an instrument: three combos **model / camera / style** replace the one combined-key combo; **serial from the plug** (read-only once found, typed in if no plug); **camera preselected** from the connected USB camera. |
| E4 | **The Instrument plug page keeps only plug actions:** Find, Harden, Write, Verify, Move (+ Add new plug, §11.5). The four combos and *Create on server* go away; it shows the setup the found plug belongs to and offers "open its setup". **Separate page** (a). |
| E5 | **Save on the setup page also writes the copy to the plug** — only if it changed (§9.5); Save then asks for the password as Write does today (b). |
| E6 | **Only a registered plug is ever switched.** Registered = it carries a copy with a **valid server signature** whose serial **equals this plug's own id**. Checked once at discovery / login, remembered by MAC. Never a fallback to the first plug found. |
| E7 | **Lamp switch is its own concept**, the Shelly is one kind; **instrument memory** is a separate, optional capability (a Pi box would keep the copy on its own disk). |
| E8 | **`LightSourceController`** on **`SpectrometerProfile`** (hardware truth, beside the serial) — not on `Spectrometer`, because the same `InLight` may get a different switch later. |
| E9 | **Bluetooth stays ON** after Harden: the end user must move the plug from the factory WLAN to the room WLAN, and their PC may have no Bluetooth or not be Linux ⇒ the phone (Shelly app) or our Linux flow must still reach it. |
| E10 | **"Add new plug" over Bluetooth, Linux only:** joins the WLAN and **nothing else** — no Harden, no Write. |
| E11 | **Default plug API password = the plug's MAC** (`E86BEAE3CB60`); the user is **reminded to change it** until they do. Replaces the standard password (`plugStandardPassword.txt` / `SPECTRACS_PLUG_STANDARD_PASSWORD` go away). |
| E12 | **AP (WPA) password = the API password** — MAC by default, follows a change. |
| E13 | **The WLAN password is never stored by Spectracs.** The plug's firmware keeps it (`sta.pass`, write-only over RPC). |
| E14 | **"Prepare for shipping"** clears the factory WLAN from the plug before it leaves the house (F5) **and sets the API + AP password back to the MAC** (Edwin, 2026-10-20), so the sheet in the box is always right. |
| E15 | The AP password = MAC goes on a **sheet in the box or a label on the plug** (C1 b). |
| E16 | **Only users registered for this spectrometer are on its plug** (`registeredSerial` = plug id), any role. Q11 ("all enabled masters on all plugs") withdrawn (Q17 / R40). |

### 11.2 Domain model

```
SpectrometerSetup ──▶ SpectrometerProfile ──▶ Spectrometer ──▶ SpectrometerSensor ──▶ SpectrometerSensorChip
      │                 serial (= switch id)    modelName         ├─▶ SpectrometerStyle
      └──▶ DbPlugin     calibration             …                 └─▶ SpectrometerVendor
                        lightSourceController ──▶ LightSourceController   NEW, seeded master data
                                                    type: NONE | SHELLY_GEN2   (enum, extensible)
```

- Seeded like `SpectrometerStyle`; later it may carry the warm-up (20 s) and the cap (`SPEC_lamp_switch.md`).
- `NONE` ⇒ manual lamp, no instrument memory, serial typed in. `SHELLY_GEN2` ⇒ `LampDriver` `shelly-gen2` + the
  plug memory of §4.7.
- Alembic migration on the server tree; existing profiles: the box ⇒ `SHELLY_GEN2`, the rest ⇒ `NONE`
  (InVision ⇒ `SHELLY_GEN2` once it has its plug). The copy (§3.3) carries the new column automatically.

### 11.3 Discovery: all plugs, each labelled

`LampDiscovery` returns **every** plug; the app labels each one:

```
 ● ours        signed copy valid, serial = own id     "shellyplusplugs-e86b… · InLight-Dynarex-GreenGold"
 ◐ known       no valid copy, but the server knows the id as a profile serial      (online only)
 ○ not ours    neither                                 never switched, listed last
```

- **Lamp:** after login the **active instrument's serial** names the plug; only that plug, and only if ●.
  Not found / not ● ⇒ manual mode as today.
- **Offline login:** only ● plugs count (already so in §9.2).
- **Setup page / plug page:** one ● or one fresh plug ⇒ preselected; several ⇒ a list (id, MAC, IP, label);
  **[Identify]** blinks the LED ring of the selected plug.
- The factory page may **write to** a ○ plug; its lamp is never switched until **Write** made it ●.

### 11.4 Harden: access point

Today Harden sets `initial_state off` + the password. The plug's AP stays **on and open** next to the WLAN
(`WiFi.GetConfig` 2026-10-20: `ap.enable true, is_open true`; `BLE enable true, rpc true`; `auth_en false`).
With the password set, every RPC needs it (HTTP for sure, ⇒ over the AP too; **over Bluetooth to be checked in
the spike**, §11.6).

**✅ Q12 = B (Edwin, 2026-10-20).** The AP is the one route to a WLAN change that needs neither Bluetooth nor an app — any phone or
laptop browser on `192.168.33.1`. Options: (A) AP **off** (`WiFi.SetConfig ap.enable false`) — smallest
surface, WLAN change only via Bluetooth or a factory reset; (B) AP **on with a WPA password**
(`ap.is_open false`, `ap.pass` = the standard plug password) — every device can still re-point the plug;
(C) leave it open. ⇒ **B**: Harden sets `ap.is_open false` + `ap.pass` = the API password (MAC by default,
E12).

### 11.5 Add new plug (Linux, Bluetooth)

```
 1  [Add new plug…]           BLE scan (bleak/BlueZ) for "Shelly*" names not seen on the LAN
 2  pick one                  its LED blinks (Identify) so the right box is clear
 3  WLAN                      SSID prefilled from the PC's current connection (nmcli), password typed
 4  WiFi.SetConfig over BLE   Gen2 RPC over the BLE GATT service, same calls as HTTP
 5  wait for it on the LAN    mDNS → "on the LAN at 192.168.1.x" — STOP. Nothing else is written.
```

New dependency `bleak` (Linux only; the button is hidden elsewhere).

### 11.6 Spike before design is final (needs Edwin's go, the new plug `E465B8B6B4F8`)

1. BLE scan finds it; `Shelly.GetDeviceInfo` over BLE.
2. `WiFi.SetConfig` over BLE ⇒ it joins `Sciens2G6971` (Edwin types the WLAN password at run time).
3. Set a test password, then: does an RPC **over BLE without the password** fail? (decides E9's safety)
4. AP with WPA password (Q12 option B) — set, join from the workstation, web UI asks for the password.
5. Factory reset ⇒ AP open again, BLE on, KVS gone, id unchanged.
6. Identify: a short LED blink (R24) — is there an RPC lighter than `PLUGS_UI.SetConfig`?
7. Prepare for shipping (R41): clear `sta` + `sta1` — is `pass` really gone (re-enable without a password ⇒ no join)?

#### 11.6.1 ✅ L0 DONE — RESULTS (run 2026-10-20 on the new plug `E465B8B6B4F8`, fw **0.13.0**; Linux, BlueZ, `bleak`)

| # | Result |
|---|---|
| 1 | ✅ BLE RPC works from Linux, **no pairing**: GATT service `5f6d4f53-5f52-5043-5f53-56435f49445f` (`_mOS_RPC_SVC_ID_`), chars `…5f64-6174615f5f5f` (data), `…5f74-785f63746c5f` (tx_ctl), `…5f72-785f63746c5f` (rx_ctl); frame = 4-byte BE length → tx_ctl, JSON → data; rx_ctl → length, read data. ⚠ **BlueZ here only connects while a scan is running** (connect after the scan ⇒ "device not found") ⇒ `BleRpc` connects inside the scanner context. Also on the old plug (fw 1.3.3). |
| 2 | ✅ `WiFi.SetConfig {sta: ssid, pass, enable}` over BLE ⇒ `got ip` 192.168.1.121 after ~20 s, visible via mDNS. Nothing else written. |
| 3 | ✅ **A set password protects BLE exactly like HTTP.** After `Shelly.SetAuth` (password = MAC): without auth over BLE ⇒ 401 for `Switch.GetStatus`, `WiFi.GetConfig`, `KVS.List`, `WiFi.SetConfig`; only `Shelly.GetDeviceInfo` stays open. With digest auth (SHA-256, same as HTTP) over BLE ⇒ OK. ⇒ E9 (BLE stays on) is safe once hardened; **C6 works over BLE on a hardened plug**. |
| 4 | ✅ `WiFi.SetConfig {ap: {is_open: false, pass: <MAC>}}` ⇒ SSID becomes WPA2 (seen after ~20 s in the scan). Join without password fails; with the MAC succeeds; `192.168.33.1/shelly` answers, `/rpc/WiFi.GetConfig` over the AP ⇒ 401 (plug password still needed). ⚠ `curl --digest` POST of this call returned "Invalid request" — sent over BLE/JSON frame it worked; the app's `ShellyHttp` is the reference path. |
| 5 | ✅ Factory reset by Edwin ⇒ AP open again, BLE + BLE RPC on, `auth_en false`, `sta`/`sta1` empty, KVS empty (`rev 0`), LEDs default, **id unchanged** `shellyplusplugs-e465b8b6b4f8`. Re-onboarded over BLE without a password (C7 → C1 c) ⇒ `got ip` again. (KVS erasure only weakly shown: nothing had been written to this plug's KVS.) |
| 6 | ◐ No identify RPC (73 methods; only `PLUGS_UI.Get/SetConfig`). 3 × blue/dark = 6 `PLUGS_UI.SetConfig` writes, 6.1 s, original LED config restored **identical**. Edwin: *"yes, I think it has blinked"* ⇒ usable, but short; L4 may make it longer/brighter. |
| 7 | ✅ `WiFi.SetConfig {sta: {ssid: null, pass: null, enable: false}, sta1: {…same}}` (over BLE, authenticated) ⇒ plug off the LAN, both slots `ssid null, is_open true`. Trap test: re-enable `sta` with the SSID and **no** pass ⇒ firmware refuses *"Pass field required!"* ⇒ no password left in the slot (flash-level erasure not observable over RPC). |

Plug left **after the reset, on the WLAN** (192.168.1.121), **no password, AP open**, LEDs default — ready for
Edwin's manual Move of `ELP-0001`. WLAN password file deleted. ⚠ It runs **fw 0.13.0** (the box plug 1.3.3): results above hold for 0.13.0; L6
should be re-checked on the current firmware, and a firmware update is a factory step to decide (not done).

### 11.7 Factory reset ⇒ automatic repair (Q13 ✅ automatic, Edwin 2026-10-20)

A reset erases password, copy and plugin; the id (= serial) stays. At the next **online** login on that box the
app sees *the plug's id is the active instrument's serial, but there is no valid copy* ⇒ it repairs the plug by
itself: **Write** (the copy + plugin, with the login credentials it already holds) and **Harden** with the
default password (the MAC, E11) — on **any** PC, master or end user, since the default needs no secret. One
status line says so ("plug was reset — restored; change its default password"). ~~R21~~ / ~~R36~~ void.

### 11.8 Rubber duck (rev 10, checked against the code 2026-10-20)

**Design**

- **R15 — Edwin's own ELP rig loses its lamp.** The server holds three profiles: `TEST-0001` (Phantom),
  `ELP-0001` (InVision), `shellyplusplugs-e86beae3cb60` (InLight). Under E6 only the box's plug is switchable,
  and only for the box's serial. `ELP-0001` is not a plug id ⇒ the two-cylinder rig never switches a lamp.
  ⇒ **The new plug `E465B8B6B4F8` becomes the ELP rig's plug:** Edwin onboards it and **moves** (by hand, Q15) `ELP-0001` →
  `shellyplusplugs-e465b8b6b4f8` and Write. That is also exactly Edwin's two-plug test (Foo = box,
  Bar = ELP rig). `TEST-0001` keeps `NONE`.
- **R16 — "Active instrument" must be defined** before the lamp can follow it. Today `LampService` does not ask:
  it takes the stored or first plug. Rule: **active serial = the logged-in user's `registeredSerial`**; a master
  without one (e.g. `masterUserExakta` on the dev bench) ⇒ the serial of the profile the bench/setup page has
  loaded; none ⇒ no lamp. ⚠ This is a behaviour change on the dev bench, on purpose.
- **R17 — `NONE` skips discovery entirely.** Today every login runs mDNS + a /24 scan. With the profile's
  `LightSourceController = NONE` (Phantom, a manual rig) there is nothing to find ⇒ no scan, no "no plug" noise.
- **R18 — The registered check reads only index + sig + copy, never the plugin.** The copy check already
  enforces "serial = this plug's id" (`InstrumentCopyReader.read(entry, device.deviceId, …)`); the plugin read
  (~4 s) is left out of discovery. Result cached by MAC for the session.
- **R19 — A hardened plug whose password this PC does not know** cannot be read ⇒ it is labelled ○, never ●.
  On the active serial that is a distinct case ("plug found but locked — enter its password in Settings →
  Lamp"), not "no plug".
- **R20 — The AP password follows the plug password.** Settings → Lamp can change the plug password
  (`Shelly.SetAuth`); it must set `ap.pass` in the same step, else the AP keeps the old one. WPA needs **≥ 8
  characters** ⇒ the password field enforces it.
- ~~**R21**~~ *(void with E11: the default password is the MAC, any PC can harden)* — **Auto-repair needs the standard password, which only a master's PC has**
  (`SPECTRACS_PLUG_PASSWORD[_FILE]`, never in the repo, R3). An end user at the customer can still get the
  **copy** rewritten (Write needs only their own login), but not the **password**. ⇒ End user: Write only, the
  plug stays without a password, and the status line says "plug was reset — a master should harden it".
  Proposal; Edwin to confirm.
- **R22 — Auto-repair must not fire on a stranger's plug.** It only acts on the plug whose id **equals the
  active serial** and that the server confirms as that profile. A random ○ plug is never written.
- **R23 — WLAN password over Bluetooth.** Shelly's BLE RPC is very likely not encrypted at the link layer ⇒ the
  WLAN password is sniffable within range during onboarding. The Shelly app does the same. Accepted; it is never
  stored by the app.
- **R24 — Identify must not wear the flash or switch the relay.** Blinking by `PLUGS_UI.SetConfig` writes the
  config to flash each time; switching the relay would break E6 on a ○ plug. ⇒ A **short** blink (≤ 6
  colour writes), then restore the stored colour. The spike checks there is no lighter RPC.
- **R25 — Discovery now always scans** (no early return when the stored plug answers is fine, but the list
  for the picker needs all plugs). ⇒ Two calls: `findActive(serial)` (fast path: stored host + MAC, as today)
  for the lamp; `discoverAll()` (mDNS, then /24) only for the setup and plug pages.

**Implementation**

- **R26 — The setup page's Save drops model and style today.** It calls
  `saveSpectrometerProfile(serial, deviceCodeName, calibration)`; the server already takes
  `modelName, styleId` (the factory path passes them). ⇒ L3 only passes them; no server change for the triple.
- **R27 — The combined combo goes, but the device-info block stays.** It shows the `Spectrometer` row; after
  the change it shows the row the three combos resolve to, or "new — created on Save".
- **R28 — The copy carries the new table.** `LightSourceController` + the profile FK are server rows ⇒ the
  SQLite copy (§3.3) must include them, and its Alembic revision rises ⇒ R12: an app older than the server
  refuses the new copy offline ("update the app"). Ship app + server together.
- **R29 — Save writing the plug (E5) must not block Save.** Rows are saved first; the plug write runs on the
  worker thread; plug unreachable ⇒ Save still succeeds, status line "saved — plug not written".
- **R30 — `bleak` is cross-platform** (BlueZ / WinRT / CoreBluetooth). Linux only for now (E10), but the
  BLE code goes behind a small `BleRpc` seam so Windows later is a packaging question, not a rewrite. It must
  survive the AppImage build (pure-Python `dbus-fast`).
- **R31 — Tests:** discovery labelling and registered-only switching against `FakeShellyServer` with **two**
  fakes (one ●, one ○) — the case that today silently picks `found[0]`.

### 11.9 Rubber duck, pass 2 (after Q14–Q16, checked in the code 2026-10-20)

- **R32 — Auto-repair is half built already.** `PlugInstrumentSync.sync()` runs after every online login,
  refuses a plug whose id ≠ the user's serial (`device.deviceId != serial` ⇒ "no plug for …"), and
  `writeCopy` compares the sha256 ⇒ **a reset plug (no index) is rewritten today**. Missing: the plugin bundle,
  Harden on a master PC, a status line instead of a print, and finding the plug **by serial** instead of the
  remembered/first plug. ⇒ L5 shrinks to that.
- **⛔ R33 — The app remembers ONE plug.** `LampPlugDbStore.saveDevice()` **deletes every row** when the MAC
  differs, password included. With two plugs on one PC (Edwin's: box + ELP rig, one user each), every Find of
  the other plug wipes the first plug's password. ⇒ **One `lamp_plug` row per MAC** (host, password, last
  seen); the lamp picks the row whose device id = the active serial. Needed before Edwin's two-plug setup is
  hardened; harmless today (no password set). ⇒ in L2.
- **R34 — The migration cannot tell which profiles have a plug.** "box ⇒ SHELLY_GEN2, rest ⇒ NONE" (L1) would
  set `ELP-0001` to NONE — but after Edwin's manual Move (Q15) its serial is `shellyplusplugs-e465…`.
  ⇒ One-time **data** rule: a serial that starts with `shelly` ⇒ SHELLY_GEN2, else NONE. This parses the
  prefix, which R8 forbids for *code*; for a one-off migration of known rows it is acceptable. Afterwards the
  master sets it on the setup page.
- **R35 — Form order on the setup page follows the controller.** Light source first: `SHELLY_GEN2` ⇒ the serial
  comes from the plug picker (read-only); `NONE` ⇒ the serial is typed in. So: Model · Camera · Style ·
  **Light source** · Serial · Plugin · User.
- ~~**R36**~~ *(void with E11)* — **Q14 (proposal: a repaired plug at the customer stays without a password.** The
  copy is signed, so it cannot be falsified; an open plug only risks someone on the customer's WLAN switching
  the lamp. The standard password is never sent to an end user's PC. The AP is then open again too (§11.4) —
  the next master visit hardens both.
- **R37 — "Known" (◐) is one call, not one per plug.** `listProfiles()` already returns every serial ⇒ fetch it
  once per discovery, label locally. Offline ⇒ no ◐, only ● / ○.
- **R38 — Edwin's manual Move happens before L2.** Find then stores the new plug and (R33) drops the box's row
  ⇒ on this PC the lamp follows the ELP plug until Settings → Lamp → "Search again". Known, told to Edwin.
- **R39 — Lamp settings page.** Settings → Lamp today shows one plug + one password. With R33 it lists the
  remembered plugs (● marked) and the password belongs to a row. Small, but it is a UI change ⇒ in L4.

### 11.10 Three secrets (Edwin, 2026-10-20)

| secret | protects | default | who knows it | stored by Spectracs? |
|---|---|---|---|---|
| **Plug API password** | every RPC to the Shelly (switch, KVS, config) — digest auth, realm = device id | **the MAC** (E11) | anyone who reads the MAC; after a change only the user | a changed one only: local app DB `lamp_plug.password` (per MAC, R33) |
| **Plug AP password** | joining the plug's own network `ShellyPlusPlugS-…` | = the API password (E12) | as above | — (same value) |
| **WLAN password** (factory or room WLAN) | the WLAN itself | — | the WLAN owner | **never** (E13): typed during onboarding, kept by the plug's firmware only (`sta.pass`, not readable over RPC; assume readable from the chip with the plug in hand) |

### 11.11 Workflows

**Factory**

```
 F1  NEW PLUG ARRIVES       plug in → blinks (setup mode, own AP open, no password)
                            → onboard to the FACTORY WLAN: "Add new plug…" (Linux, BLE),
                              Shelly app, or browser on 192.168.33.1
 F2  HARDEN                 plug page [Harden]: API + AP password = MAC, output off after a power cut,
                            Bluetooth stays on; print the MAC label / sheet (E15)
 F3  CREATE THE INSTRUMENT  setup page [New]: Model · Camera (preselected) · Style · Light source
                            SHELLY_GEN2 · Serial = picked plug ([Identify]) · Plugin · (User)
                            → calibrate → [Save] → server rows + copy written onto the plug
 F4  CHECK                  plug page [Verify] → "valid · …"; one measurement: the lamp switches (●)
 F5  SHIP                   plug page [Prepare for shipping]: ① API + AP password back to the MAC
                            (whatever it was changed to at the factory) ② forget the factory WLAN
                            (sta + sta1) → the plug drops off the LAN = proof it will start in setup
                            mode (C1), with the password the sheet names
 F6  REPLACE A PLUG         new plug: F1 + F2 → [Move instrument here] (old serial → new id) → F4 → F5
```

**End customer**

```
 C1  UNPACK + FIRST START   plug in → blinks (no WLAN known) → onboard to the ROOM WLAN:
                              a) Shelly app on the phone (BLE; asks for the API password = MAC if set)
                              b) join "ShellyPlusPlugS-<MAC>", AP password = <MAC> (sheet/label),
                                 browser 192.168.33.1 → Wi-Fi → room WLAN + its password
                              c) Linux: Spectracs "Add new plug…" (BLE)
 C2  FIRST LOGIN (online)   plug found by the user's serial, ● → lamp works; copy synced if changed;
                            reminder "the lamp plug still uses its default password — change it in
                            Settings → Lamp" while the MAC still works
 C3  CHANGE THE PASSWORD    Settings → Lamp → new password (≥ 8) → API + AP password on the plug,
                            stored in the local app DB → reminder gone
 C4  DAILY WORK             login online or OFFLINE (plug copy) → measure → lamp on in ACQUISITION,
                            off after; hard cap on the plug itself
 C5  SECOND PC              default password: works by itself; changed: asked once, stored there
 C6  NEW ROUTER / WLAN      "lamp plug not found" → re-onboard as C1 b) / a); AP password = the
                            CURRENT API password; nothing else lost
 C7  PASSWORD FORGOTTEN     factory reset (10 s, within 60 s of plugging in) → like new: no WLAN, no
                            password, no copy, id stays → C1 → next ONLINE login: auto-repair (§11.7)
                            → reminder again. ⚠ offline the box can't measure until then (R2)
 C8  PLUG BROKEN            a new plug = a new id ⇒ Move (master only) → back to the factory (F6),
                            or a master does F6 remotely once the new plug is online
```

### 11.12 Rubber duck, final pass (after E11–E15, checked in the code 2026-10-20)

- **⛔ R40 — With the default password, anyone on the WLAN can read the copy — including bcrypt hashes of
  every enabled master** (Q11: all masters on all plugs). The MAC is public (`GET /shelly`, SSID, BLE name) ⇒
  until C3, the plug's KVS is readable by anyone in the room's WLAN, and the hashes can be attacked offline.
  The signature stops *changes*, not *reading*. ⇒ Proposal: **masters go only onto plugs at the factory**
  (removed from the copy at F5 / Prepare for shipping), the customer's plug carries only the end user(s) bound
  to it. A master on site logs in online. Edwin to decide (**Q17**).
  ✅ **Decided (E16, 2026-10-20):** simpler still — the copy carries **only users registered for this
  spectrometer**, at the factory too ⇒ Prepare for shipping removes nobody. Code: the user query in
  `InstrumentCopyLogicModule.__collect` drops `or id in (… MASTER_USER …)`; `buildForUser` keeps allowing a
  master to *fetch* any copy (factory Write). Residual: the registered user's own hash is readable on the
  WLAN until C3 — covered by the reminder. Tests to adapt: `test_instrument_copy.py`,
  `test_offline_instrument_plug.py`; Verify now reports "1 user" on the box.
- **R41 — "Prepare for shipping" must clear BOTH WLAN slots.** The live plug has the factory WLAN in `sta`
  **and** a disabled copy in `sta1` (`WiFi.GetConfig` 2026-10-20: `sta1.ssid = Sciens2G6971`). Clearing only
  `sta` ships the password in `sta1`. Whether setting `ssid: null` also erases `pass` is **not documented ⇒
  spike item**.
- **R48 — Prepare for shipping resets the password to the MAC first, the WLAN last** (Edwin, 2026-10-20). If a
  master changed the password at the factory, the plug would otherwise ship with one the customer does not
  know ⇒ locked out until a factory reset. Order: ① `WiFi.SetConfig ap.pass = MAC` and `Shelly.SetAuth` (MAC),
  authenticated with the current password ② the factory PC's `lamp_plug` row for this MAC drops its stored
  password (the MAC is the default again, R43) ③ clear `sta` + `sta1` (R41), which cuts the line (R42). A
  failure in ① stops before ③, so the plug never leaves the LAN with an unknown password.
- **R42 — Prepare for shipping cuts the line it is sent over.** The answer may never arrive ⇒ the page treats
  "plug gone from the LAN within 15 s" as success, and asks for confirmation first ("the plug will leave this
  WLAN; you need C1 to get it back").
- **R43 — Which password to try, in what order.** `lamp_plug.password` (if stored) → the MAC → none. "MAC
  works" ⇒ the C2 reminder; "none works" ⇒ R19 ("plug locked — enter its password"). The MAC comes from the
  unauthenticated `GET /shelly`, so it is known before any login.
- **R44 — Auto-harden is now possible on every PC — so it must stay narrow** (R22): only the plug whose id =
  the active serial, confirmed by the server, and only when `auth_en` is false. Never a stranger's plug.
- **R45 — Changing the password is two RPCs** (`Shelly.SetAuth`, then `WiFi.SetConfig ap.pass`). If the second
  fails, AP and API differ. ⇒ AP first (still authenticated with the old password), then SetAuth, then store;
  a failure is reported and the stored password stays the one the plug accepts.
- **R46 — `harden()` and the plug page read `standardPassword()` today** (`InstrumentFactoryLogicModule`
  lines 30–57, `InstrumentPlugViewModule` 227). Both switch to the MAC; the env/file and its error message go.
- **R47 — The MAC label (E15) is a factory step, not code.** It belongs in `spectracs-hardware/ammoBox-spec.md`
  (assembly), noted there when L4 lands.

### 11.13 Phases (final)

```
 ┌─────┬──────────────────────────────────────────┬────────────────────┬──────────────┬────────────────────────┐
 │ #   │ What                                     │ Where              │ Needs        │ Done when              │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ —   │ EDWIN, by hand (Q15): onboard E465, Move │ rig                │ today's app  │ ELP-0001 lives on      │
 │     │ ELP-0001 onto it with today's plug page  │                    │              │ shellyplusplugs-e465…  │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L0  │ DONE 2026-10-20 (§11.6.1): SPIKE + R41:  │ rig (new plug)     │ Edwin's go,  │ every item answered in │
 │     │ BLE scan, WLAN join over BLE, BLE RPC    │                    │ WLAN password│ §11.6; sta + sta1      │
 │     │ without the password, AP-WPA, Identify,  │                    │ typed at run │ cleared without trace  │
 │     │ clearing sta+sta1 (pass gone?), reset    │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L1  │ LightSourceController (NONE/SHELLY_GEN2) │ -model (+ Alembic  │ —            │ migration on the live  │
 │     │ + seed + profile FK; data rule R34; in   │ server tree),      │              │ DB: box + ELP ⇒ SHELLY,│
 │     │ the copy (R28); copy = registered users  │ -server (copy)     │              │ TEST ⇒ NONE; box copy  │
 │     │ only (E16); AppUser comment (E2)         │                    │              │ = 1 user; tests        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L2  │ REGISTERED-ONLY LAMP: discovery lists +  │ -core (discovery), │ L1           │ two fake plugs: only   │
 │     │ labels ●/◐/○ (R18/R19/R37); findActive(  │ app (LampService,  │              │ the ● one with the     │
 │     │ serial) vs discoverAll (R25); active     │ LampPlugDbStore)   │              │ active serial switches;│
 │     │ serial = registeredSerial (R16); NONE ⇒  │                    │              │ two stored plugs keep  │
 │     │ no scan (R17); one lamp_plug row per MAC │                    │              │ both passwords; MAC    │
 │     │ (R33); password order stored→MAC (R43)   │                    │              │ default accepted       │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L3  │ SETUP PAGE: Model·Camera·Style·Light     │ app                │ L2           │ create + edit an       │
 │     │ source·Serial·Plugin·User (R35); serial  │                    │              │ instrument from this   │
 │     │ from the plug picker; camera preselected;│                    │              │ page alone; plug       │
 │     │ Save sends model+style (R26), writes the │                    │              │ written in background  │
 │     │ copy if changed, never blocking (R29)    │                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L4  │ PLUG PAGE + PASSWORDS: combos/Create out │ app                │ L3           │ F1–F6 run from the     │
 │     │ (E4), "open its setup", picker, Identify │                    │              │ page; reminder shows   │
 │     │ (R24); Harden = MAC for API + AP (E11/   │                    │              │ until C3; password     │
 │     │ E12, R46); [Prepare for shipping] (E14,  │                    │              │ change sets API + AP   │
 │     │ R41/R42/R48: password → MAC, then WLAN   │                    │              │ ships with the MAC     │
 │     │ cleared); C2 reminder; Settings → Lamp   │                    │              │                        │
 │     │ lists plugs, change sets AP+API (R45/R39)│                    │              │                        │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L5  │ AUTO-REPAIR (R32/R44): PlugInstrument-   │ app                │ L2, L4       │ reset plug → online    │
 │     │ Sync finds by serial, writes copy +      │                    │              │ login on ANY PC → copy │
 │     │ plugin, hardens with the MAC on any PC,  │                    │              │ + plugin + MAC password│
 │     │ status line instead of print             │                    │              │ back, lamp switches    │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L6  │ ADD NEW PLUG over BLE, Linux (§11.5):    │ app (+ bleak,      │ L0           │ a fresh plug joins the │
 │     │ BleRpc seam (R30), connects DURING the   │ AppImage)          │              │ WLAN from the app;     │
 │     │ scan (L0 #1); scan → pick → WLAN →       │                    │              │                        │
 │     │ wait on the LAN; nothing else written    │                    │              │ nothing else written   │
 ├─────┼──────────────────────────────────────────┼────────────────────┼──────────────┼────────────────────────┤
 │ L7  │ EDWIN'S CLICK-THROUGH: F1–F6 on the new  │ rig                │ L1–L6        │ each user switches only│
 │     │ plug, C1–C7 on the box; two plugs, each  │                    │              │ their own lamp; a reset│
 │     │ user only their lamp; a third Shelly ○   │                    │              │ plug comes back alone  │
 └─────┴──────────────────────────────────────────┴────────────────────┴──────────────┴────────────────────────┘
```

Order: Edwin's manual Move and L0 any time. Main line **L1 → L2 → L3 → L4 → L5**; L6 needs only L0.
**L2 alone fixes the wrong-plug defect and the one-plug memory.** Q17 is decided (E16) and lands in L1 with the
other copy change.

### 11.14 Questions

- ~~Q12~~ ✅ B — AP stays, WPA-protected (§11.4).
- ~~Q13~~ ✅ automatic repair (§11.7).
- ~~**Q14**~~ void with E11 (default = MAC ⇒ any PC re-hardens). Was — R21: at the customer an end user's login rewrites the copy but cannot set the password (no
  standard password on their PC). OK, or should the server hand the standard password to a bound user's app?
- **Q15** — R15: ✅ Edwin moves `ELP-0001` onto the new plug **by hand** with today's plug page (Move instrument
  here, started with `SPECTRACS_LAMP_HOST=<new plug ip>` so Find takes the new plug) — not part of the phases.
- ~~Q16~~ void: both masters already have a `registeredSerial` (`masterUserExakta` → `ELP-0001`,
  `masterUserDynarex` → the box) ⇒ R16 shrinks to "active serial = `registeredSerial`, none ⇒ no lamp".
- ~~**Q17**~~ ✅ E16: only users registered for this spectrometer on the plug, any role; Q11 withdrawn.

### 11.15 ✅ As built — L1–L6 (2026-10-20; L7 = Edwin's click-through, §11.17)

```
 ┌─────┬──────────────────────────────────────────────────────────────────┬──────────────────────────────────────┐
 │ #   │ Built                                                            │ Where                                │
 ├─────┼──────────────────────────────────────────────────────────────────┼──────────────────────────────────────┤
 │ L1  │ LightSourceController (+ LightSourceControllerType NONE/         │ -model: entity, util, AllEntities,   │
 │     │ SHELLY_GEN2) + profile FK; migration b7c41e09d2a5 (seeds, rule   │ alembic/server b7c41e09d2a5, seed,   │
 │     │ R34, tolerant of a create_all table); seed sets it on fresh DBs; │ InstrumentLogicModule, Login, copy,  │
 │     │ saveProfile(lightSourceControllerType); moveToSerial ⇒ SHELLY;   │ Authoring; -server RPC; app client + │
 │     │ bundle + login + offline login carry it; copy = registered users │ CurrentUserSession                   │
 │     │ only (E16) + the controller row; AppUser comment (E2)            │                                      │
 │ L2  │ LampDiscovery: wantedId, discoverAll(), NO found[0]; PlugRegistry│ -core LampDiscovery(+Result);        │
 │     │ ●◐🔒○ with passwords stored→MAC (R43), cache MAC+sha (R18);       │ app PlugRegistry, LampAdmission,     │
 │     │ LampAdmission: only the active serial's ● plug; LampService asks │ LampWorker, LampService,             │
 │     │ CurrentUserSession (R16), NONE ⇒ NOT_APPLICABLE without a scan   │ LampPlugDbStore/LampPlugStore,       │
 │     │ (R17); lamp_plug one row per MAC (R33); PlugLocator find/        │ PlugLocator, OfflineLogin            │
 │     │ registeredPlugs/findBySerial/candidates; offline login tries     │                                      │
 │     │ every ● plug for the user (two rigs in one room)                 │                                      │
 │ L3  │ Setup page: Model·Camera·Style·Light source·Serial[Find plug…]·  │ SpectrometerSetupViewModule, List    │
 │     │ Plugin·User; Shelly ⇒ serial read-only from the picker; camera   │ (buildRows/rowForSerial/openEditor   │
 │     │ preselected (connected); a plug with a setup opens it; Save sends│ static, rows carry the triple),      │
 │     │ the triple + type, syncs a new spectrometer into the catalog,    │ InWindowDialog.askPassword/askFields │
 │     │ then asks the password and writes the plug in the background     │                                      │
 │ L4  │ Plug page: Search (picker ●◐🔒○), Identify, Add new plug, Harden,│ InstrumentPlugViewModule,            │
 │     │ Write, Verify, Prepare for shipping, Move, Open its setup;       │ InstrumentFactoryLogicModule,        │
 │     │ Harden = MAC for API + AP (WPA), off after power cut; change     │ LampSettingsViewModule, LampButton   │
 │     │ password AP→API→store (R45); Prepare for shipping MAC→store→     │                                      │
 │     │ sta+sta1 cleared, success = gone from the LAN (R41/R42/R48);     │                                      │
 │     │ Identify 4 × blue, restored (R24); Settings → Lamp: plugs this PC│                                      │
 │     │ knows, Change password, refusal reason; header icon "!" + tip    │                                      │
 │     │ while the default password is in use (C2); standard password +   │                                      │
 │     │ createOnServer REMOVED (R46/E4)                                  │                                      │
 │ L5  │ PlugInstrumentSync: by serial (findBySerial), restore = copy +   │ PlugInstrumentMemory, LoginView      │
 │     │ plugin via factory.write, harden with the MAC on ANY PC when the │ (plugSyncFinished → status line,     │
 │     │ plug has no password, locked ⇒ left alone; result → status line, │ lamp re-discovered)                  │
 │     │ the lamp looks again                                             │                                      │
 │ L6  │ ShellyBleRpc (seam R30: scan, call with digest, joinWlan, connect│ -core ShellyBleRpc; app              │
 │     │ inside the scan); PlugOnboardingLogicModule (new plugs = BLE ∖   │ PlugOnboardingLogicModule,           │
 │     │ LAN, SSID from nmcli, MAC tried on 401, wait on LAN 60 s);       │ AddPlugViewModule; requirements      │
 │     │ AddPlugViewModule in-window flow; bleak==3.0.2 (linux) + spec    │ bleak==3.0.2, spectracsAppImage.spec │
 │     │ hiddenimports                                                    │ hiddenimports                        │
 └─────┴──────────────────────────────────────────────────────────────────┴──────────────────────────────────────┘
```

**Deviations / open points**

- **SPECTRACS_LAMP_HOST is an explicit operator override** (`HostOverrideAdmission`): the plug at that host is
  admitted without the registered check (still only with a password that opens it). It is the test seam and
  Edwin's rig override, and the way to use a plug for the manual Move before it is registered.
- **Auto-repair stores the plugin only on a PC with the master signing key** (as Write always did); on an end
  user's PC the copy + password come back, the plugin bundle does not (offline login then needs a built-in plugin).
- **Identify over Bluetooth is not built** — the Add-new-plug picker lists by name (nearest first by RSSI); the
  LAN Identify works once the plug is on the WLAN.
- **Not verified on hardware yet:** Harden's `WiFi.SetConfig ap` and `Shelly.SetAuth` via `ShellyHttp.post`
  (the spike set them over BLE; `curl --digest` POST failed, the JSON-RPC POST of ShellyHttp is the reference
  path), Prepare for shipping end to end, Add new plug through the app, the AppImage with bleak.
- **The server seed recreates `ELP-0001`** (empty calibration) at the next server start after Edwin's manual
  Move — `getOrCreateInstrument` is idempotent on the serial, not on the instrument. Harmless stub; delete it by
  hand or drop the ELP seed.
- **Running server:** restart it — its DB (`~/.spectracsPy-server/`) migrates to b7c41e09d2a5 at boot. The
  app-local catalog `~/.spectracsPy/spectracsPyServer.db` was migrated on 2026-10-20 (backup
  `.bak-2026-10-20-L1`).

### 11.16 Firmware update on the plug page (Edwin, 2026-10-20) — IMPLEMENTED, run on the new plug

**Why.** L7 B1 failed on the new plug: fw **0.13.0** resets the connection on a `Script.PutCode` body ≥ 3 KiB
(measured: 2048 OK, 3072 not) — fixed independently (`PlugKeyValueStore.WRITE_PIECE` 8192 → 2048, the fake plug
enforces the limit), but plugs on old firmware are a moving target ⇒ bring them to one tested version.

**Decided (Edwin): the target is fixed at 1.7.5** (`InstrumentFactoryLogicModule.TARGET_FIRMWARE`) — up to it and
never beyond; a newer version only after a test run (raise the constant). Read-only check 2026-10-20:
`Shelly.CheckForUpdate` offers **0.13.0 → 1.3.3** (new plug) and **1.3.3 → 1.7.5** (box) ⇒ updates come in hops.

**As built.** Plug page: row **Firmware** (`/shelly` `ver`, carried on `LampDevice.firmware` from the probe) and
button **Update firmware** (enabled only below the target; confirm first). `updateFirmware`: per hop
`Shelly.CheckForUpdate` → stop at/above the target, stop if nothing is offered (no internet?), **refuse an offer
newer than the target**, else `Shelly.Update {stage: stable}` and wait (≤ 5 min) until `/shelly` reports the offered
version; ≤ 4 hops; refused while this plug's lamp is on or a capture runs; afterwards a copy on the plug is
**verified** (settings / KVS / scripts are expected to survive — this checks it). Progress lines on the page.
Factory step **F1b** (after Add new plug, before Harden). Tests: fake plug with the measured hops.

**Open.** Not yet run on a real plug (Edwin tries it in the app). Untested whether 1.7.5 changes anything we use
(KVS limits, `PLUGS_UI`, the 3 KiB POST limit, BLE) ⇒ after the first update: Verify, Identify, Lamp → Test.

**Update on the new plug: ✅ run by Edwin from the app, 2026-10-20** — 0.13.0 → 1.3.3 → 1.7.5 in two hops (~1 min
each), afterwards copy valid (2 users), password = MAC, AP still WPA, WLAN kept.
**Write piece by firmware (measured on the plug at 1.7.5, test slot deleted):** `Script.PutCode` 7936 B OK, 8192 B
→ **HTTP 413** (1.3.3 took 8192, 0.13.0 resets at 3072) ⇒ `PlugKeyValueStore.writePieceFor(firmware)`: **4096** from
1.3.3 on, **2048** below or unknown; `PlugInstrumentMemory.forDevice` passes the probed firmware. Real write at 4096
on 1.7.5: ✓, 9.9 s — no faster than 6.8 s at 2048 on the then-open plug: with a password every request costs a
second round trip (digest challenge) ⇒ the piece size is not the bottleneck.

### 11.17 L7 — Edwin's click-through, part 1 (2026-10-20): ✅ A1–A9, ✅ B1–B6

Run on the two real plugs (box `…e86beae3cb60` fw 1.3.3, new `…e465b8b6b4f8` fw 0.13.0 → 1.7.5) with the checklist
of the session (A one instrument, B second instrument via the manual Move, C passwords/offline, D reset/BLE/shipping,
E no lamp switch). **A and B pass.** C, D, E continue in the next session.

Found and fixed on the way:

| # | Found at | Defect | Fix |
|---|---|---|---|
| K1 | A2 | `getInstrumentCopy` failed on the real server: *No module named …InstrumentCopySignatureUtil* — `runServer.sh` had no `../spectracsPy-core` on PYTHONPATH (tests run in-process, so they never saw it) | `spectracsPy-server/runServer.sh` PYTHONPATH + `-core` |
| K2 | A2 | the box plug read as "not registered": lamp worker and plug sync read the copy **at once**, and the Alembic migration of the copy is not thread-safe (reproduced: 3/3 parallel reads failed) | `InstrumentCopyReader.read` serialised; `PlugRegistry.classify` serialised (2nd caller gets the cached verdict) |
| K3 | A5 | "Test" greyed — lamp said "locked": it probed the plug open, the sync hardened it with the MAC meanwhile, the read tried only "no password"; the re-search from the sync thread overlapped and its result was dropped | `passwordsFor`: open plug ⇒ none, then stored, then MAC; LampService search id (only the latest counts); re-search queued onto the GUI thread |
| K4 | B1 | Move: server step OK, writing the plug failed — fw 0.13.0 resets the connection on a `Script.PutCode` ≥ 3 KiB | piece by firmware: 2048 below 1.3.3, 4096 from 1.3.3 (§11.16); fake plug enforces the limits |
| K5 | B1 | the failure was invisible: the follow-up search overwrote the result line; the status line said "restored" for "**not** restored: …" | follow-up search keeps the step's line; status line matches the result exactly |
| K6 | B1 | Move offered on a plug that already has a setup (can only fail) | Move enabled only for a plug of no instrument |
| K7 | B1 | old firmware is a moving target | **Update firmware** (§11.16), target fixed at 1.7.5 by Edwin; run on the new plug: 0.13.0 → 1.3.3 → 1.7.5, data survived |

State after part 1: box plug ● (fw 1.3.3, password = MAC), new plug ● = the ELP instrument (fw 1.7.5, password = MAC,
2 users), `ELP-0001` moved onto it on the server. 821 tests green.

**Open for part 2:** C1–C4 (password change, offline with two registered plugs), D1–D5 (factory reset → Add new plug
over BLE in the app → auto-repair → Prepare for shipping), E1 (no lamp switch); box plug → 1.7.5 + Verify/Identify/
Test on 1.7.5; AppImage build with bleak; the seed's `ELP-0001` stub after the server restart (§11.15).
