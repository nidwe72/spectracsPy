# SPEC — Plugin distribution & storage (Milestone 3)

Status: **Track A IMPLEMENTED (A1·A2); A3 deferred; Track B: M0·B0·B1·B2·B3 IMPLEMENTED 2026-07-18; B4·B5 have a
settled build plan (§8 "B4+B5 build plan", 2026-07-18) — DESIGN, not built; B6 DESIGN with decisions settled (D-shadow
= (b) via ROW-SEALEDNESS dispatch: sealed row → DB exec, unsealed/bare row → built-in, so the seed needs no change and
F16 dissolves); B7 postponed; B8 batch-assign postponed. **Slice 1 (B5.4+B6.4+F16 load+dispatch) + Slice 2 (B4 publish
UI + B5 assign UI + F4 fix) ✅ IMPLEMENTED 2026-07-18** (unit-tested + headless; live GUI click-through of a real
publish→assign→load not yet rig-verified). **Remaining: B7 Android, B8 batch-assign, A3 provenance stamp.** (spec-first;
implement on explicit request only). Source: Edwin (2026-07-10; **all open questions settled 2026-07-16**;
**Track-B build order + crypto/key + migration prereq settled 2026-07-18** — see §8). **M1**
([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md)) shipped, and the
[`SPEC_project_structure.md`](SPEC_project_structure.md) tiering arc (S0–S7) is complete, so both prerequisites
are cleared. Track B additionally depends on [`SPEC_schema_migrations.md`](SPEC_schema_migrations.md) (Alembic).
Trust model **Option 1** (signed, client-side load).

Theme: **convergence makes a plugin a *droppable unit*; distribution *ships* it.**

**Purpose (settled):** ship **plugin updates without an APK rebuild**. *Not* third-party plugin authors — Edwin
authors every plugin. Some plugins will still require an app update; that is what the SDK version constant reports.

> **Runs after** [`SPEC_project_structure.md`](SPEC_project_structure.md) (Edwin's lean, agreed) — see §8. The two
> are near-independent; that spec owns the `spectracs-plugins` repo, which used to live here.

---

## 0. Why client-side signed load (Option 1)

- **CPU-time (Edwin).** Execution scales with **clients**, not the server — the server only stores. Option 2
  (server-side execution) would run every user's processing on your hardware; cost grows with users.
- **Matches the existing split** — master authors, end-user consumes.
- **Option 2 recorded as the alternative:** safer (client runs no plugin code) but loads server CPU and needs a
  client↔server split because the **camera is client-side**. Rejected on CPU + complexity.

---

## 1. THE HINGE — `DbPlugin` identity must become `(codeRef, version)`

**This is the whole milestone's linchpin. Everything else is a consequence.**

Today `SpectracsPyServer.savePlugin` **upserts keyed on `codeRef`**, and `SpectrometerSetup.pluginId` is an FK to a
`DbPlugin` **row**. So publishing pumpkin 1.3 would **overwrite the row every instrument already points at** — every
instrument in the field jumps to 1.3 at once, silently, at next login. That is the exact opposite of the
fine-grained rollout Edwin wants, and it is structural, not a missing feature.

Signing forces the same change independently: **a signed row must be immutable**, because mutating it invalidates
its own signature.

> **Change: one row per published version. `(codeRef, version)` is the identity. Insert, never update.**

Everything falls out of it:

| Verb | Mechanism | Notes |
|---|---|---|
| **Publish** | INSERT a new row | nobody is affected yet |
| **Assign** | repoint one `SpectrometerSetup.pluginId` | the fine-grained knob — **the column already exists** |
| **Pin** | do nothing | a setup keeps its row until moved |
| **Revoke** | repoint back to the previous row | **free** — the old row was never overwritten |
| **Provenance** | the run records `setup.pluginId` | **free** — that row *is* the exact version |

## 1b. The binding is per-SERIAL, not per-user

**Correction to this spec's earlier §3.** `AppUser` has **no `pluginId`**. Its own comment: *"The instrument bundle
(device + calibration + plugin) resolves through this serial via SpectrometerSetup, **NOT** through a per-user plugin
binding."* The chain is:

```
AppUser.registeredSerial -> SpectrometerProfile.serial -> SpectrometerSetup -> DbPlugin
```

The connection/calibration UX work ([`SPEC_connection_and_calibration_ux.md`](SPEC_connection_and_calibration_ux.md))
moved this after M3 was first written. So **fine-grained rollout keys on the instrument serial**. One user ↔ one
serial, so Edwin gets what he asked for — and the instrument is the better key anyway: device + calibration + plugin
version is one traceable bundle, exactly the unit a lab QM result must name.

---

## 2. The lifecycle — four verbs, of which the model has two

Automatic applies **within** an assignment; explicit **across** versions.

1. **Develop.** Edit the plugin, run it on the bench, iterate. Nothing touches the DB. Unchanged.
2. **Publish.** Master picks the source file + sets a version. The app reads the bytes, **signs them locally**, sends
   source + signature + version to the server, which **inserts** a row. Nobody runs it yet.
3. **Assign.** Point serial `ABCD-1234`'s `SpectrometerSetup` at pumpkin 1.3.0. Other serials stay on 1.2.0.
4. **Load.** User logs in → serial resolves → setup names the exact row → client fetches → **verifies signature** →
   checks SDK compat → loads → runs.

Publish and assign being **separate acts** *is* the fine-grained control — and is why upsert-on-`codeRef` must go.

---

## 3. Trust model — the honest version

**Security = key control, full stop.**

- **The private key lives on EDWIN'S MACHINE — never on the server.** (There is already a local sibling venv folder
  that can hold it.) A key on the server means a server compromise signs anything, and the signature then certifies
  only that bytes from the server came from the server — zero information. **The signature's entire value is that it
  survives a server compromise.** The server is a **dumb store**: it holds bytes it cannot forge.
- **The public key ships IN the app source**, as `TRUSTED_KEYS` — **a LIST, not a single key**, from day one. A list
  makes rotation boring (ship a release trusting `{A,B}`, wait for uptake, sign with `B`, drop `A` later); a single
  key makes rotation a flag day. Cheap now, painful to retrofit. Shipping the trust anchor with the software is
  **industry standard** — browser root CAs, `debian-archive-keyring`, Sparkle's `Info.plist`, TUF's root role.
- **NEVER fetch the anchor from the server.** It is circular: an attacker serves *their* public key, signs malicious
  source with *their* private key, and the client verifies it happily. **A trust anchor fetched from the thing you
  are verifying is not a trust anchor.** Trust must enter from somewhere already trusted — the installed app.
- **The signature covers the TUPLE**, not just the source: `codeRef | version | targetSdkVersion | sha256(source)`.
  Signing source alone permits **rollback** (re-serve signed old source under a new version) and **re-binding**
  (attach signed source to another `codeRef`).
- **`keyId` on the row is safe** — a hint naming which key signed it. The client looks it up **in its own shipped
  list** and refuses if absent. The list still gates it.
- **The "imports only `plugin_sdk`" check is hygiene, NOT a sandbox.** Static import analysis is trivially
  bypassable (`__import__`, `getattr`, `exec`). It catches honest mistakes — which, with a single author, is exactly
  its job. **Do not present it as a security boundary.** Sandboxing is ruled out: Python cannot safely execute
  untrusted code in-process.

### 3b. Key hierarchy (Edwin: build it, to close the subject)

A **root key** ships in the app and never changes. It signs a small *key-list document* naming the current signing
keys; that document **can** be served over Pyro, because the shipped root gates it — a substituted list carries no
valid root signature and is refused. This is TUF's / Debian's shape.

**Caveat, so it isn't a surprise:** this closes rotation for **signing keys**, never for the **root** — the anchor
cannot bootstrap itself, so replacing it will always need an app update. That is true of every PKI, including the
browser's.

### 3c. TLS — postponed, deliberately

**Not a prerequisite.** Pyro is plaintext today, so a network attacker can inject plugin source — and the signature
refuses it anyway. **That is the point of signing: it works over a channel you don't trust.**

**But** TLS was never only about plugins: login sends the **password in plaintext** today, and signing does nothing
for that, nor for measurement data or LIMS credentials. Postponing is a sound call for M3; just don't let "signing
covers it" become the reason TLS never lands. ([`SPEC_user_auth_login.md`](SPEC_user_auth_login.md) §6 phase D.)

---

## 4. `plugin_sdk` versioning — one integer

The SDK **ships inside the app**: exactly one per build, never distributed. Only the *plugin* travels. So the only
question at load is: the app has SDK `N`, this plugin targets `M` — safe?

- **`SDK_VERSION` = one integer, bumped ONLY on a breaking change.** Load rule: `plugin.targetSdk == app.SDK_VERSION`.
- **No back-compat promise. Do not freeze the model layer.** Edwin controls both sides and can rebuild any plugin.
- Its job is **a good error message** — an honest *"this plugin needs a newer app"* instead of a mystery
  `AttributeError` three phases deep. That is exactly the case Edwin named: *"in the long run there will be plugins
  that require an update of the app."*
- **Why it's needed at all:** while plugins live in-tree, plugin and SDK share a commit — consistent by construction.
  The moment you publish, **the DB becomes a second copy of code that git no longer governs.** The constant is what
  makes that drift detectable.

---

## 5. Storage + loading

- **`DbPlugin` extended** from today's `title` / `codeRef` / `version` / `pdfRef` to add: `source` (TEXT),
  `signature`, `keyId`, `author`, `targetSdkVersion` — with identity `(codeRef, version)` per §1.
- **Loader (client):** fetch row → **verify signature over the tuple** → check `targetSdkVersion` → import the source
  into a fresh module (`importlib.util` / `exec`) → find the `SpectralPlugin` subclass → instantiate. The
  import-hygiene check runs here as a **lint gate only**.
- **Qt-free stays load-bearing** — it keeps a plugin testable and headlessly runnable. See
  [`SPEC_project_structure.md`](SPEC_project_structure.md), which makes it true one layer down too.

### 5b. Signing library

**PyNaCl** (libsodium via cffi). Cross-platform wheels; libsodium is the reference Ed25519 implementation; and the
p4a precedent is already in the tree — [`SPEC_android_port.md`](SPEC_android_port.md) P5 builds **bcrypt + cffi +
pycparser** under mainline p4a. `cryptography` is Rust-backed now and not worth a Rust toolchain under p4a for one
signature check.

**De-risker:** only the **master signs**, and the master is always a desktop. Every client **verifies**, including
Android — the easy half. Worst case, a pure-Python Ed25519 *verifier* (no build step, run once per login) covers
Android while PyNaCl signs on desktop.

---

## 6. Android — no blockers

- **Permissions are irrelevant.** They govern OS resources (camera, network, storage). Executing Python source in
  your own process is not an OS resource — there is no permission to request and none to deny.
- **W^X doesn't bite.** Android 10+ forbids `dlopen()`ing a `.so` the app wrote itself — that is *native* code
  loading. `exec()` of Python source is not: CPython is already legitimately mapped executable from the APK, and
  handing it a string builds bytecode objects on the heap. Interpreted bytecode is data, not executable pages.
- **Play policy is moot — Edwin is not shipping via Play.** The DEX-download rule was always *policy* (Play would
  reject the listing), never an Android technical restriction. Sideloading removes it.
- Remaining gotchas are mundane: don't rely on writing `.pyc` caches to a read-only path (use `exec(source, ns)` or
  an in-memory loader); the plugin's transitive imports must already be in the APK (satisfied — plugins import only
  `plugin_sdk`); nothing may need a compiler at runtime. **B7 is a spike, not a gate.**

---

## 7. UI — extend what exists, don't build a CLI

The master screen, version field, RPC, persistence **and the assign action all already exist**:

| Piece | Today | After |
|---|---|---|
| `PluginViewModule` | Settings > Plugins > Plugin; title/codeRef/version/pdfRef; `codeRef` read-only when editing | **"Publish a version"**: + source file picker, + Sign & Publish. `codeRef` stops being read-only-on-edit because **editing a published row stops existing** — a signed row is immutable; you publish 1.3.0, you never edit 1.2.0 |
| `PluginListViewModule` | one row per plugin | one row per **version**, grouped by plugin |
| `savePlugin` (client + `@expose`d server, master-only) | upserts on `codeRef` | **inserts**; carries source + signature + keyId + targetSdkVersion |
| `SpectrometerSetupViewModule` | serial + spectrometer combo + plugin picker (`onClickedSelectPlugin` → `onPluginPicked` → `__pluginCodeRef`) + user field | **the rollout console**: + a **version picker** beside the plugin picker |
| `saveSpectrometerSetup(serial, pluginCodeRef)` | binds serial → plugin | widens to carry the **version** |

The original §5 proposed a separate master signing tool; **rejected** — the delta above is small, and "the private
key never leaves the master" is satisfied trivially, since the master's machine *is* the machine running the app.

---

## 8. Implementation phases

**A1·A2 were decision-free and are DONE. A3 was mis-filed as decision-free — it is NOT (see the ⚠️ note
below); it is deferred. Track B is the distribution proper; B0 is the hinge.**

| Ph | Change | Where | Verify |
|---|---|---|---|
| **A1** ✅ | **`PluginRegistry`** — enumerate in-app + resolve by `codeRef`; **retire the scattered copies** (bench class-list, the `CurrentUserSession` dev-bypass string) | host + logic | bench selector + dev-bypass both resolve via the registry; no regression |
| **A2** ✅ | `SDK_VERSION` constant; plugins declare `targetSdkVersion` | `plugin_sdk` | mismatch reports *"needs a newer app"* / *"rebuild the plugin"*, not `AttributeError` |
| **A3** ⏸ | **Provenance** — the run records the resolved plugin `(codeRef, version)` | model + engine | *deferred* — no run-record sink exists yet, and "version" is vacuous pre-B0; see ⚠️ below |

### ⚠️ A3 is deferred, not decision-free (rubber-duck finding, 2026-07-18)

The original table called Track A "no decisions, start any time." True for A1/A2, **wrong for A3**:

1. **No sink exists.** Workflow persistence (`DbMeasurement` JSON blob) and the M2 PDF embedded-JSON are both
   still DESIGN-only. "The run records…" has nowhere to write, so an in-memory `(codeRef, version)` stamp would
   be a field nobody reads — speculative generality.
2. **"version" is vacuous pre-B0.** Only `DbPlugin` rows carry a `version`; an in-app/bench plugin has none. A
   *meaningful* version identity does not exist until **B0** mints per-version rows.

So A3 depends on **B0 + a sink**. Decision (Edwin, 2026-07-18): **drop A3 from Track A entirely**; it becomes a
one-liner *inside* whichever sink lands first (B0 provenance, M2's JSON, or workflow-persistence), written at the
moment there is finally a reader.

### As built — A1·A2 (2026-07-18)

- **`PluginRegistry`** (`sciens.spectracs.logic.spectral.plugin.PluginRegistry`, app tier) is **lazy**: built-in
  entries carry a `codeRef` string + display `title` (+ `benchOnly`, + a `version` slot left null for built-ins),
  and the class is imported only on `resolve()`. This is the **same shape B6's DB-delivered plugins must take**
  (codeRef + source, exec'd on demand), so B6 appends to the list without reshaping anything. `resolve()` is the
  single owner of "codeRef → instance" and routes the A2 SDK check; the engine's `importPlugin` is now a thin
  delegator, so the bench, the wizard, and login-resolution all funnel through one gate.
- **Bug F1 retired.** The dev-login bypass in `CurrentUserSession` had a **stale, broken** codeRef
  (`…pumpkin.PumpkinOilPlugin` — one segment short, raised `AttributeError` through `importPlugin`) that had
  silently drifted from the DB-seed codeRef during S5. It now reads the registry's canonical `PUMPKIN_OIL_CODE_REF`
  constant — a literal codeRef string never appears at a call site again.
- **The -model seed keeps a literal string** (tier order forbids it importing a plugin class), so it can't be
  DRY'd into the registry. Closed instead by a **cross-check test**.
- **Guard test** (`tests/test_plugin_registry_and_sdk.py`): every registry `codeRef` resolves + instantiates + its
  entry `title` equals the class `title`; the -model seed codeRef is asserted ∈ the registry — the check that
  would have caught F1 at CI time. Plus a bad-fixture SDK test (target ±1 → directional error message).
- **A2**: `SDK_VERSION = 1` + `checkSdkCompatible` live in a dependency-free `plugin_sdk/version.py` (kept out of
  `__init__.py` to avoid a base import cycle); `SpectralPlugin.targetSdkVersion` defaults to `SDK_VERSION`, so an
  in-app plugin always matches by construction — the gate is **inert until B3** presents a DB plugin that can
  mismatch, exactly as §4 predicts. Its value now is the tested error path.
### Track B — the distribution proper (as designed, 2026-07-18)

**Prerequisite — schema migrations.** B0/B1 add columns to `DbPlugin`, and the codebase has **no migration
mechanism**: `create_all` builds missing *tables* but never adds a column to an existing one (the live
`calibrationSpectrumJson` seed bug). Adopting Alembic is pulled **out** of B0 into its own foundational piece —
[`SPEC_schema_migrations.md`](SPEC_schema_migrations.md). **M3 depends on it; it is not part of M3.**

**Signing is day-one** (Edwin): B2/B3 are core, *not* a fast-follow. **Build order:** migrations → **B0+B1** → **B2**
→ **fetch-RPC + B3** → **B4+B5** → **B6** → **B7**.

| Ph | Change | Where | Verify |
|---|---|---|---|
| **B0** | **IDENTITY** — `(codeRef, version)` **unique constraint** (`id` stays a uuid PK); insert-not-upsert; **kill `upsert()`**; seed `getOrCreate` re-keys on `(codeRef, version)` | model + server + **migration** | publishing v2 leaves v1 intact; **assigned setups do NOT move** |
| **B1** | Extend `DbPlugin`: `source`, `signature`, `keyId`, `author`, `targetSdkVersion` — one Alembic migration | model + server | a sealed row round-trips |
| **B2** | **Sign** on the master (PyNaCl; private seed **outside all repos**, path via env/config); **verify** pure-Python in `-core`; `TRUSTED_KEYS` **flat list** in app source (root hierarchy = fast-follow); sign the tuple; `keyId` = pubkey fingerprint | app (sign) · `-core` (verify) · server (store) | tampered source / swapped version / re-pointed `codeRef` / unknown `keyId` — **all refused** |
| **B3** | **fetch-RPC** (`getPluginSource`) + **Loader**: fetch sealed row → verify tuple → SDK check → `exec` as the codeRef module → `getattr` the class → instantiate | server `@expose` + client | a **signed** DB plugin loads + runs on the bench |
| **B4** | **Publish UI** — editor becomes publisher: source picker + **Sign & Publish**; `codeRef` no longer read-only (published rows are immutable — never edited) | `PluginViewModule` + `savePlugin` RPC (6 copies) | master publishes from the app; a new sealed row lands |
| **B5** | **Assign UI** — version picker; **fix `saveSetup` `.first()`** → key on the exact row (id, or codeRef+version) | `SpectrometerSetupViewModule` + `saveSetup` | serial A on v2, serial B on v1; re-assign back = revoke; **no arbitrary-version pick** |
| **B6** | Registry learns DB plugins — `resolve()` gains a DB branch (fetch→verify→`exec`); `listPlugins` RPC **already exists** | A1's registry | in-app + DB plugins both listed, both run |
| **B7** | Android spike — pure-Python verify + `exec` under p4a (**postponed**; Linux-first) | `android/` | a signed DB plugin runs on the Note 20 |

#### Findings (rubber-duck, 2026-07-18)

- **B0 is smaller than it sounds.** `id` is a random uuid PK and `SpectrometerSetup.pluginId` already targets a
  *row*, so per-version rollout needs no FK surgery — just a `(codeRef, version)` unique constraint, insert-not-upsert,
  and killing `upsert()`. Assign already repoints a FK to a specific row.
- **🔴 F3 — two blockers, no existing tooling.** (1) **No migrations** → [`SPEC_schema_migrations.md`](SPEC_schema_migrations.md).
  (2) **No crypto lib** — PyNaCl *and* cryptography are both absent from the venv and undeclared; B2 needs one chosen,
  installed, and (for Android) proven — see the crypto design below, which sidesteps the p4a risk.
- **🔴 F4 — `saveSetup` `.first()` becomes a silent mis-assign.** It queries `DbPlugin.codeRef == pluginCodeRef` and
  takes `.first()`; post-B0 there are many rows per codeRef, so it grabs an arbitrary version. B5 must key on the
  exact row.
- **🟠 F5 — login carries `codeRef` only, not `version`.** `LoginLogicModule` returns `pluginCodeRef`, and the client
  *can't query the server DB*. Post-B0 it must load a *specific version*, so login (serial→setup→the exact row) must
  carry **`(codeRef, version)`** — and this is where **A3 provenance** finally becomes real (login is the version's
  entry point to the client).
- **🟠 F6 — the "where do the bytes come from" gap.** The loader is client-side; the source lives in the server DB;
  the client can't reach it. B3 needs a **new `@expose` RPC** returning the *sealed tuple* (source + signature + keyId
  + version + targetSdkVersion) — the spec's "fetch row" hides an RPC.
- **Integration reality.** The first *demonstrable* thing is a **vertical slice** (migrations + B0 + B1 + fetch-RPC +
  B3 + one published signed row), not a single independently-shippable phase.

#### Crypto & key design (settled 2026-07-18)

- **The insight that dissolves the p4a risk:** only the master **signs** (always a desktop), every client only
  **verifies**, and Ed25519 *verification* is pure-Python with no build step. So **sign with a real library on
  desktop; verify pure-Python everywhere** — Android never links libsodium, and the p4a question stops existing.
- **Library:** **PyNaCl** signs (desktop-only; libsodium is the reference Ed25519); a **vendored pure-Python Ed25519
  verifier** verifies on all platforms. Alternative recorded (Edwin chose PyNaCl-signs): all-pure-Python for zero
  native dep anywhere — signing is offline on a trusted machine, so its slowness/side-channels are moot.
- **What is signed (the tuple):** the canonical bytes of `codeRef ⋀ version ⋀ targetSdkVersion ⋀ sha256(source)`.
  Verify recomputes the tuple from the row's own fields and re-hashes the stored source — so a tampered source,
  swapped version, re-pointed codeRef, or lied-about targetSdk all break it. Store `signature` (base64) + `keyId`.
- **Private key:** a raw Ed25519 seed in a file **outside every repo** (the sibling folder), **never committed,
  never on the server**; read only at Sign-time by the publish UI. Concrete (settled 2026-07-18): env var
  **`SPECTRACS_SIGNING_KEY`** → a file path, default **`../spectracs-keys/signing.seed`**; absent → publish disabled
  with a clear message.
- **`TRUSTED_KEYS`:** a **flat list** shipped *in app source* (`keyId → pubkey`). The loader looks up the row's
  `keyId` in *its own shipped list* and refuses if absent. **`keyId` = pubkey fingerprint** (derived, can't be
  mislabeled — same "derive, don't type" principle as A1's codeRef).
- **Root hierarchy — fast-follow, not day-one.** "Signed from day one" is satisfied by the flat list. The root-signed
  key-list (§3b) only buys signing-key rotation *without an app update*, which matters only once there are field
  installs you can't update — **there are none.** Build it as the immediate next step, still pre-deployment.
- **Tier placement:** the **verifier + tuple canonicalization live in `-core`** (Qt-free, Android-portable); the
  **signer is app-tier** (PyNaCl, used only by the publish UI). Everyone ships the verifier; only the master signs.

#### Ordering & trigger

[`SPEC_project_structure.md`](SPEC_project_structure.md) (S0–S7) is **DONE**, clearing the old ordering gate; the one
remaining prerequisite is the migrations spec. The **trigger** to actually build B is *Android-deployment* pain —
shipping a plugin change to a deployed device without a new APK; a desktop dev never feels it. Plan (Edwin): **build
Linux-first, keep every choice Android-viable, defer Android testing (B7).**

#### Open questions — resolved 2026-07-18

1. **Plugins are single self-contained modules** (verified: both ship-in plugins import only `plugin_sdk` + stdlib,
   zero sibling imports). B3 execs *one* `source` TEXT column as one module. This is now an **enforced constraint**:
   a **one-importable-module publish-time check** (B4) + a documented `plugin_sdk` rule. A multi-file plugin is
   rejected at publish, not silently broken at load.
2. **Verifier = a vendored public-domain reference `ed25519.py`** (~100 lines) in `-core` — no dependency, runs once
   per login (slowness irrelevant). Only the master's *signing* uses PyNaCl.
3. **Source at load = a separate `getPluginSource(codeRef, version)` RPC.** Login carries only the *identity*
   `(codeRef, version)`; the client fetches + verifies source on load. Keeps login lean and lets the bench load an
   arbitrary version.
4. **`version` = semver by convention.** Assign is an explicit per-row pick, so no ordering logic is needed day-one
   (string sort suffices for grouping the list).
5. **Publish reads `title` + `targetSdkVersion` by importing the picked source** on the master's (trusted) machine →
   stored on the row and in the signed tuple. No hand-typed values that must match the code.
6. **Keypair bootstrap = a one-time keygen helper** (B2): writes the private seed to the sibling folder, prints
   pubkey + fingerprint to paste into `TRUSTED_KEYS`.
7. **`author` = the logged-in master's username** at publish. **RPC ripple:** update only the **3 live** `savePlugin`
   paths (app client · server `@expose` · `-model` persist); the 3 android/spike copies stay frozen. **Immutability**
   = an insert-only code path (the signature already makes mutation detectable) — no DB trigger.

#### Phase dependency map

```
LEGEND   ◆ prereq   ● core (signing day-one)   ○ UI   ▸ postponed
         ══ first demonstrable "vertical slice" ══  (M0·B0·B1·B2·B3 + one published row)

  M0 ─▶ B0 ─┬─▶ B1 ─▶ B2 ─▶ B3 ─────────────┐
   ◆     ●  │    ●     ●     ●               ├─▶ B6 ─▶ (B7 ▸ postponed)
            │                                │      ○
            └─▶ B5 ────────────────┐         │
                 ○      B2 ─▶ B4 ───┴─────────┘
                         ●    ○

CROSS-CUTS:  A1 PluginRegistry (done) = the seam B3/B6 plug into.
             F5 login must carry (codeRef, version) — lands in B0/B3; also unblocks A3 provenance.
```

#### B0–B3 build plan — the first vertical slice (one sweep) — ✅ IMPLEMENTED 2026-07-18

> **As built (M0·B0·B1·B2·B3):** the four-checkpoint sweep landed green.
> - **M0** — Alembic adopted; see [`SPEC_schema_migrations.md`](SPEC_schema_migrations.md) §7. Calibration bug gone;
>   an existing DB evolved `f641 → 405d`.
> - **B0/B1** — `DbPlugin` identity `(codeRef, version)` (unique constraint, uuid PK kept) + 5 sealed columns, in one
>   migration (`405d2ce2cec1`). `upsert()` removed; `PersistPluginLogicModule.createVersion` inserts-not-upserts and
>   refuses re-publishing a version; the seed's `getOrCreate` re-keys on `(codeRef, version)`; server `savePlugin`
>   inserts. **Verified:** sealed row round-trips; publishing v2 leaves v1 intact; duplicate refused.
> - **B2** — vendored public-domain `ed25519.py` + `PluginSignatureUtil` (tuple canon, `fingerprint`, `verifySealed`,
>   `PluginSignatureError`) in `-core`; app-tier `PluginSigner` (PyNaCl, key via `SPECTRACS_SIGNING_KEY`), `TrustedKeys`
>   anchor, `generateSigningKey.py`. **Verified:** PyNaCl-sign ↔ pure-Python-verify interop, and all four refusals.
> - **B3** — `getPluginSource(codeRef, version)` `@expose` + client wrapper; `PluginRegistry.resolve(codeRef, version)`
>   now dispatches builtin (`importlib`) vs DB (fetch → `verifySealed` → SDK-check → `exec` module → `getattr`).
>   **Verified:** a signed DB plugin loads + runs; a tampered source and an untrusted key are both refused before exec.
> - **Stale test fixed:** `test_plugin_binding_and_seed` asserted the removed per-user `AppUser.pluginId`; M0 unmasked
>   it (the calibration setup-error had hidden it) → updated to the per-serial model.
> - Tests: `test_plugin_registry_and_sdk` (7) · `test_plugin_signature` (7) · `test_plugin_db_loader` (3) · updated
>   binding (5); 32 green across the blast radius incl. the T2 boundary. **Next sweep: B4 + B5** (publish/assign UI).

M0+B0–B3 is the natural first sweep: the phases below B3 have **no user-visible payoff until B3 ties them together**
(a signed plugin loading from the DB), so bundling them is the honest milestone, not greed. Concrete changes:

- **B0** (`-model`, `-server`) — `DbPlugin` gains `UniqueConstraint('codeRef','version')`. ⚠️ it inherits
  `__table_args__ = {'extend_existing': True}` from the mixin, so it must become
  `(UniqueConstraint('codeRef','version'), {'extend_existing': True})` — override **and** keep the flag. `id` stays a
  uuid PK. `PersistPluginLogicModule`: **kill `upsert()`**; publish = plain insert; `getOrCreate` re-keys on
  `(codeRef, version)` (+`findByCodeRefAndVersion`) so the seed stays idempotent per version. Server `savePlugin`
  `@expose` inserts.
- **B1** (`-model`) — `DbPlugin += source (Text), signature (String), keyId (String), author (String),
  targetSdkVersion (Integer)`. **B0+B1 ride one migration** (rev2, on top of the rev1 baseline).
- **B2** (`-core` verify · app sign) — vendored public-domain `ed25519.py` + a `PluginSignature` util in `-core`
  (tuple canon `codeRef\nversion\ntargetSdkVersion\nsha256hex(source)` + `verify(pubkey, sig, tuple)`); an app-tier
  `PluginSigner` (PyNaCl, **app-only dep** — `-core`/`-model` never import it); `TRUSTED_KEYS = {keyId: pubkey}` in
  app source (`keyId` = `sha256(pubkey)[:16]` hex); a one-time keygen helper. **Verify runs only on the DB branch** —
  builtins are trusted by shipping in the APK.
- **B3** (`-server`, app) — server `@expose getPluginSource(codeRef, version)` → sealed row dict; client wrapper;
  `PluginRegistry.resolve` gains a **DB branch**: not-a-builtin → fetch → verify tuple → SDK check → `exec` source as
  the codeRef module → `getattr` the class → instantiate.

**Four checkpoints, each green before the next:**

1. **M0** — a migration lands a column on an *existing* DB (proven by the calibration bug clearing).
2. **B0+B1** — a sealed row round-trips; publishing v2 leaves v1 intact (unique constraint holds).
3. **B2** — sign/verify round-trip + all four refusals (tamper source / swap version / re-point codeRef / unknown
   keyId), **pure unit tests, no DB/RPC** — the security core, isolated.
4. **B3** — a signed DB plugin loads + runs on the bench.

**The B4 stand-in.** B3's gate needs a *signed row in the DB*, but the publish UI is B4. So the sweep carries a
**signing test-helper** (B2's signer + a throwaway keypair → inserts one sealed `DbPlugin` row) as B4's stand-in,
plus a minimal builtin-vs-DB dispatch in `resolve()` (a sliver of B6) so the bench can pick it. Both test-scoped.

**Sequence note:** baseline rev1 = the *current* models (no plugin changes) so existing DBs adopt cleanly; **then**
make the B0/B1 model edits and autogenerate rev2. **Interim (B0 lands, B4 not yet):** the old `PluginViewModule`
editor now inserts rather than upserts — but a same-version re-save is **rejected by the unique constraint** (fails
loudly, never a silent dup), so the interim is self-protected; B4 rebuilds it as the publisher.

**Risks:** the `__table_args__` mixin merge; PyNaCl-sign ↔ pure-Python-verify **interop** (round-trip test across the
two implementations); the PyNaCl requirements entry (app tier only); keeping the exec'd `source` **byte-identical**
to what was hashed.

#### Definition of Done — M0+B0–B3 (met 2026-07-18)

- [x] **M0** — Alembic adopted; an existing DB *evolves* (`f641 → 405d`); the calibration `OperationalError` is gone;
  a fresh DB comes up via `create_all` + `stamp head`; two independent envs in `-model`; wired into app + server boot;
  `alembic`/`PyNaCl` in `requirements.txt`; `authorMigration.sh` helper.
- [x] **B0** — `DbPlugin` identity `(codeRef, version)` (unique constraint; uuid PK kept); `upsert()` removed;
  insert-not-upsert; seed re-keyed; **publishing v2 leaves v1 intact**; duplicate version refused.
- [x] **B1** — 5 sealed columns in migration `405d2ce2cec1`; a sealed row round-trips.
- [x] **B2** — vendored pure-Python `ed25519.py` + `PluginSignatureUtil` (`-core`); `PluginSigner` (PyNaCl) +
  `TrustedKeys` + `generateSigningKey.py` (app); **PyNaCl ↔ pure-Python interop** and **all four refusals** proven;
  master key generated, anchor populated (`keyId 0c618b47f8a17f36`), sign→verify **live-verified**.
- [x] **B3** — `getPluginSource` RPC + `resolve(codeRef, version)` builtin/DB dispatch; a **signed DB plugin loads +
  runs**; a tampered source and an untrusted key are **refused before exec**.
- [x] **Tests** — 32 green across the blast radius incl. the T2 boundary; the stale per-user binding test updated to
  the per-serial model (M0 unmasked it).
- [ ] **Out of scope (next):** B4 publish UI, B5 assign UI, B6 registry DB feed, B7 Android spike.
- [ ] **Not yet rig-verified:** full desktop GUI click-through (paths verified headlessly + by unit tests only).

#### B4+B5 build plan — the publish/assign UI (as designed, 2026-07-18)

**The one-sentence version:** B2/B3 already built the *hard* half (sign · store · fetch · verify · exec); B4/B5 are
**wiring the two existing master screens to that machinery** — with one non-obvious catch that makes them a **single
coupled sweep**, not two independent phases (see F5-reopened below).

##### Rubber-duck findings (impl) — grounded in the current code

- **🔴 F5 REOPENED — the linchpin, and it was NOT closed in B0/B3.** The phase-map said *"F5 login must carry
  `(codeRef, version)` — lands in B0/B3."* **It did not.** The end-user load chain still drops the version at every
  hop, and it *looks* fine today only because every assignable plugin is a **built-in** (`version=None` → the builtin
  branch of `resolve`), so the version is never consulted. The moment B4 publishes a real DB row and B5 assigns it,
  the chain breaks with a hard raise. Trace:
  - `InstrumentLogicModule.resolveBundle` (`-model`, line 29): `pluginCodeRef = setup.plugin.codeRef` — **drops
    `setup.plugin.version`**, even though `setup.plugin` *is* the exact row and carries it.
  - `LoginLogicModule` → returns `pluginCodeRef` only → `CurrentUserSession` stores `pluginCodeRef` only
    (`getPluginCodeRef()`).
  - `WizardViewModule` → `SpectralWorkflowEngine.importPlugin(codeRef)` → `PluginRegistry.resolve(codeRef)` **with no
    version** (`SpectralWorkflowEngine.py:48`).
  - `resolve(codeRef, None)` on a non-builtin → `_resolveDbPlugin(codeRef, None)` → **`raise ValueError("a DB plugin
    must be resolved by (codeRef, version)")`** (`PluginRegistry.py:89-90`).
  **Consequence:** B5 is not "add a version picker." Its real content is **threading `(codeRef, version)` end-to-end**
  through the bundle → login → session → engine → `resolve`. This is a cross-tier change (`-model` + app) and is the
  bulk of B5's cost. **It must ship together with — or before — the first real DB assignment**, or an assigned
  instrument cannot log in and run.

- **🟢 F7 — the 6-vs-3 `savePlugin` discrepancy, reconciled (and smaller than either number).** Source-tree total is
  **7** definitions (9 with `.buildozer` artifacts), but only **the live-tier canonical 3** matter — and of those, the
  **`-model` persist path is already B4-complete**:
  | Role | Path | B4 status |
  |---|---|---|
  | app client wrapper | `SpectracsPyServerClient.savePlugin(title, codeRef, version, pdfRef)` | **widen** — carry the sealed fields |
  | server `@expose` | `SpectracsPyServer.savePlugin(...)` → `createVersion(title, codeRef, version, pdfRef)` | **widen** — pass the sealed fields through |
  | `-model` persist | `PersistPluginLogicModule.createVersion(…, source, signature, keyId, author, targetSdkVersion)` | **already accepts them — no change** |
  So **§7's "6 copies" over-counts** (it swept the `android/spike` mirror + the non-RPC entity-saver); **§8-Q7's "3 live
  paths" counts the model path that's already done.** Honest count: **2 live RPC signatures to widen** (client + server),
  plus the view rewrite. The `android/spike` + `android/server` + `.buildozer` copies stay **frozen** (Q7).

- **🟢 F8 — B5 needs NO new version-picker widget.** `PluginListViewModule` already runs in SELECT mode as the plugin
  picker, and its table is **already one row per `(codeRef, version)`** (post-B0 `listPlugins` returns a row per
  version; columns are `Title · Code reference · Version`). So **selecting a row already IS selecting a version.** The
  only gap: `SpectrometerSetupViewModule.onPluginPicked` (line 184) captures `plugin.get('codeRef')` and **throws away
  `plugin.get('version')`**. B5 = capture the version too, show it in `pluginField`, thread it through save. The §7
  table's *"+ a version picker beside the plugin picker"* is **satisfied by the list that already exists** — don't build
  a second widget.

- **🔴 F4 CONFIRMED (unchanged) — `saveSetup`'s `.first()` is a live mis-assign.** `InstrumentAuthoringLogicModule.py:100`:
  `session.query(DbPlugin).filter(DbPlugin.codeRef == pluginCodeRef).first()` — post-B0 there are many rows per codeRef,
  so it binds an **arbitrary** version. B5 must key the exact row via `findByCodeRefAndVersion(codeRef, version)`.

- **🟠 F9 — B4 publish flow signs client-side, BEFORE the RPC; the key gates the button.** Order: pick source file →
  **import it on the master's trusted desktop** to read `title` + `targetSdkVersion` off the class (Q5: no hand-typed
  values that must match code) → run the **one-importable-module lint** (imports only `plugin_sdk` + stdlib; reject a
  multi-file plugin *at publish*, Q1) → read the source **once as text** → `PluginSigner.sign(codeRef, version,
  targetSdkVersion, source)` → `(signatureBase64, keyId)` → RPC `savePlugin(…, source, sig, keyId, author, targetSdk)`.
  The **Publish button is disabled with a clear message when `PluginSigner.signingKeyAvailable()` is false** (no
  `SPECTRACS_SIGNING_KEY` / seed) — the private key never leaves the master, exactly as §3. **`source` must stay
  byte-identical** from sign → store → fetch → exec (read once as `str`, pass that exact object through).

- **🟠 F10 — `author` is UNSIGNED provenance; the client supplies it.** The signed tuple is
  `codeRef|version|targetSdkVersion|sha256(source)` — `author` is **not** in it. So the server can't (and needn't)
  authenticate it cryptographically; the app passes `author = CurrentUserSession().getUsername()` at publish. It's a
  provenance label, not a security claim (Q7).

- **🟠 F11 — B4 changes the list's *Add/Edit* semantics.** A published row is **immutable**, so "Edit an existing
  plugin" stops meaning anything. `PluginViewModule.__applyModelToWidgets` currently sets `codeRef` read-only when
  editing (line 82) — that whole mode goes. New shape:
  - **Add** = a brand-new `codeRef` + version 1 (codeRef editable).
  - **New version** (replaces *Edit*) = prefill `codeRef` + `title` from the selected row, **blank the version**, pick
    a source; codeRef read-only again but now *because it's inherited*, not because it's a mutable key.
  Double-click-row = *New version* (not Edit). Update the stale docstrings ("Upsert keyed on codeRef", line 12) while
  there.

##### B4 — Publish UI (change table)

| # | Change | Where |
|---|---|---|
| B4.1 | Editor → **publisher**: source-file picker; derive `title` + `targetSdkVersion` by importing the picked source; **Sign & Publish** button gated on `signingKeyAvailable()` | `PluginViewModule` (app) |
| B4.2 | One-importable-module **lint gate** at publish (imports only `plugin_sdk` + stdlib) | `PluginViewModule` (app) — hygiene, not a sandbox (§3) |
| B4.3 | Sign the tuple client-side; call the widened RPC | `PluginViewModule` → `PluginSigner.sign` |
| B4.4 | **Widen** `savePlugin` to carry `source, signature, keyId, author, targetSdkVersion` | client wrapper **+** server `@expose` (2 copies) |
| B4.5 | Server passes the sealed fields into `createVersion` (already accepts them) | `SpectracsPyServer.savePlugin` |
| B4.6 | List: **Add / New-version** semantics; drop read-only-codeRef-on-edit; per-version rows already render | `PluginListViewModule` + `PluginViewModule` |

##### B5 — Assign UI (change table)

| # | Change | Where |
|---|---|---|
| B5.1 | `onPluginPicked` captures **`version`** too; show `title @ version` in `pluginField`; store `__pluginVersion` beside `__pluginCodeRef` | `SpectrometerSetupViewModule` (app) |
| B5.2 | **Widen** `saveSpectrometerSetup(serial, codeRef, version)` | client wrapper **+** server `@expose` (2 copies) |
| B5.3 | **Fix F4**: `saveSetup` keys the exact row via `findByCodeRefAndVersion` → `setup.pluginId = row.id` | `InstrumentAuthoringLogicModule.saveSetup` (`-model`) |
| B5.4 | **Fix F5 (the linchpin)**: `resolveBundle` returns `pluginVersion`; login/session carry it; `getPluginVersion()`; `importPlugin`/wizard pass it to `resolve(codeRef, version)` | `InstrumentLogicModule`, `LoginLogicModule`, `CurrentUserSession`, `SpectralWorkflowEngine`, `WizardViewModule` |
| B5.5 | Verify all three resolve paths (B6.4): `version=None` → built-in; a **bare/seed** row → built-in (unsealed); a **sealed** published row → DB exec | cross-tier |

**Sequencing:** B4 and B5 are **one coupled sweep** — publishing a DB row (B4) with no way to load it (B5.4) is a dead
end, and B5.4 with nothing published is untestable. Land them together; the demonstrable milestone is **publish pumpkin
`1.1.0` from the app → assign it to a serial → log in as that serial's end-user → the DB version loads, verifies, and
runs the wizard.** (B6 then lets the *bench* list DB versions too; today only the end-user load path exercises them.)

**Checkpoints (each green before the next):**
1. **B4 publish** — a signed row lands via the app; re-publishing the same version is refused (unique constraint);
   the Publish button is disabled with the key absent.
2. **B5 assign** — serial A → v2, serial B → v1; `.first()` no longer arbitrary; re-assign A back to v1 = revoke.
3. **B5.4 load** — the assigned end-user logs in and the **exact** assigned version loads + verifies + runs; a tampered
   row and an untrusted key are still refused before exec.

**Risks:** the F5 cross-tier thread (5 files, model↔app) is the real work — miss one hop and the version silently
drops, so a sealed DB row is never reached (the serial quietly stays on the built-in); importing untrusted-ish source
at *publish* to derive title/sdk (mitigated: master's own machine, same trust as running the app); keeping `source`
byte-identical across sign→exec.

> **As built — Slice 2 (B4 + B5) ✅ IMPLEMENTED 2026-07-18.** B5.4 already landed in Slice 1; this sweep added the
> publish + assign UI and widened the RPCs.
> - **Publish path (B4)** — new app-tier `PluginPublishUtil.inspectPluginSource` imports the picked `.py` on the
>   master to DERIVE `className`/`title`/`targetSdkVersion` (Q5) and LINT it self-contained (Q1: rejects `sciens.*`
>   sibling/relative imports, multi-class, no-class, missing title). `PluginViewModule` is now a **publisher**: pick
>   source → derive (title + target SDK read-only) → validate `codeRef` tail == class name (D-coderef) → `PluginSigner.sign`
>   the tuple locally → `savePlugin(...)` with the sealed fields; **Sign & Publish** is disabled when
>   `signingKeyAvailable()` is false. `savePlugin` widened (client wrapper + server `@expose`) to carry
>   `source/signature/keyId/author/targetSdkVersion` into the already-ready `createVersion`.
> - **List (B4.6)** — `PluginListViewModule`'s *Edit* → **New version** (inherits codeRef/title, fresh version+source);
>   `codeRef` read-only only when inheriting, never because it's a mutable key.
> - **Assign path (B5)** — `SpectrometerSetupViewModule.onPluginPicked` now captures the **version** (the picker
>   already lists one row per `(codeRef, version)`), shows `title @ version`, and passes it through the widened
>   `saveSpectrometerSetup(serial, codeRef, version)`. `InstrumentAuthoringLogicModule.saveSetup` **fixes F4** — keys
>   the exact `(codeRef, version)` row when a version is given (the old `.first()` bound an arbitrary version);
>   `listSetups` + the setup-list DTO carry `pluginVersion` so an edited setup round-trips its bound version.
> - **Tests** — new `test_plugin_publish` (inspect/derive + lint refusals + codeRef↔class); `test_plugin_binding_and_seed`
>   gains the F4 exact-version assertion (reuses the seed, creates no rows). Full plugin blast radius green; all changed
>   Qt views import headless; `signingKeyAvailable()` is True on the master (key `0c618b47…`) so publish is live.
> - **NOT yet rig-verified:** the live GUI click-through (publish a real pumpkin `1.1.0` from the app → assign → log
>   in as the serial → the sealed DB version loads & runs) — the F16 first-real-publish runbook. Paths verified by
>   unit tests + headless import only.
> - **Still deferred:** A3 provenance stamp (needs a `SpectralWorkflow.pluginVersion` migration); B6 bench DB-listing
>   *live* verification; B7 Android; B8 batch-assign.

**Provenance (A3) rides B5.4 for free:** once the session carries `(codeRef, version)`, `WizardViewModule:576`
(`workflow.pluginCodeRef = session.getPluginCodeRef()`) can also stamp the version — the first real reader, exactly as
§8's A3 note predicted.

#### B6 build plan — the registry learns DB plugins (as designed, 2026-07-18)

**B3 already built the *load* side of B6** (`PluginRegistry._resolveDbPlugin` — a "sliver of B6"). What's left is the
**enumerate** side: the only place that asks *"which plugins exist?"* — the **bench selector** — still sees built-ins
only. B6 is narrow and **bench-facing** (master dev tool); it does not touch the end-user login path (that's B5.4).

##### Rubber-duck findings (impl)

- **🔴 F12 — THE design question: built-in codeRefs SHADOW their DB versions.** `resolve` dispatches on
  *"is this codeRef a built-in?"* (`PluginRegistry.py:66`: `if entry is not None and entry.version is None → builtin`).
  So for **any codeRef that is also shipped as a built-in** — e.g. `PUMPKIN_OIL_CODE_REF` — `resolve(codeRef, "1.1.0")`
  hits `find()`, gets the built-in entry (`version=None`), and takes the **built-in branch, ignoring the requested
  version entirely.** A DB-published pumpkin `1.1.0` is **unreachable**. That directly contradicts the milestone's
  stated purpose (*"ship plugin updates without an APK rebuild"*): you could only ever distribute **brand-new**
  codeRefs, never fix a plugin already shipped in the app. **This needs an explicit decision (D-shadow, below) and it
  gates B6 — arguably the whole point of distribution.**

- **🟢 F13 — the bench has the SAME version-drop as F5, in miniature.** `DevMeasurementBenchViewModule` stores
  `__selectedCodeRef` (codeRef only, lines 74/647) and calls `PluginRegistry.resolve(self.__selectedCodeRef)` (line 234)
  — **no version.** A DB entry there would raise exactly like the login path. So B6 must carry the selected **entry**
  (or `codeRef + version`), not a bare codeRef. Same lesson, separate call site — independent of B5.4.

- **🟢 F14 — enumeration is the only new data path, and its RPC already exists.** `listPlugins()` (client + server)
  returns one dict per `(codeRef, version)` row — that's the whole feed. `entries()` today is a pure static returning
  `__BUILTINS`; making *it* hit the server would change its nature (network, auth, failure) and break the callers that
  must stay offline (the dev-login bypass reads only the codeRef constants). **Keep `entries()` static; add a separate
  DB-aware `listAll()`** that merges built-ins + `listPlugins()`. Only the bench calls it.

- **🟢 F15 — narrow blast radius.** The *only* enumeration consumer is the bench (`entries()` at line 73; `codeRefs()`
  is defined but otherwise unused). PluginListViewModule already lists DB versions via `listPlugins` directly — it does
  **not** go through the registry. So B6 = one new registry method + rewiring one combo. No other screen changes.

##### B6 — change table

| # | Change | Where |
|---|---|---|
| B6.1 | New `PluginRegistry.listAll(includeDb=True)` → built-in entries **+** one `PluginEntry(codeRef, title, version=…)` per `listPlugins()` row; server-down / non-master → built-ins only (bench stays usable offline) | `PluginRegistry` (app) |
| B6.2 | Bench stores the selected **entry** (`codeRef`+`version`), not a bare codeRef; `resolve(codeRef, version)` | `DevMeasurementBenchViewModule` |
| B6.3 | Combo label = `title` for built-ins, `title @ version` for DB rows; flat list | `DevMeasurementBenchViewModule` |
| B6.4 | **(D-shadow = (b), settled — dispatch on ROW-SEALEDNESS, Edwin 2026-07-18)** `version is None → built-in` (dev bench / unassigned, no fetch); else fetch the row → **`source` present → verify + exec** (a real distributed version) / **`source` NULL → built-in fallback** (a bare/seed row is a "use the shipped copy" pointer) / **fetch failed → built-in if shipped, else error** (offline) | `PluginRegistry.resolve` |

##### Decisions — B6 & B4 (settled 2026-07-18 by Edwin)

- **✅ D-shadow → (b), strengthened to a PRINCIPLE.** *"Plugins always come from the DB, delivered over the Pyro
  server."* The DB is the **source of truth** for distributable plugins; the built-in APK copy is a **fallback only**
  (offline, unassigned serial, dev bench, or a bare/unsealed row). **Dispatch keys on ROW-SEALEDNESS, not version-presence**
  (the refinement that dissolves F16): a *sealed* row (has `source`) runs the distributed code; an *unsealed* row (NULL
  `source`) is a "use the shipped built-in" pointer. So `resolve(pumpkin, "1.1.0-sealed")` → **DB exec**;
  `resolve(pumpkin, "1.0-seed-bare")` → **built-in**; `resolve(pumpkin, None)` → **built-in, no fetch**. This makes
  over-the-air fixes to *shipped* plugins work (a published sealed row overrides) — the whole reason to build Track B —
  **without** forcing any seed change.
- **✅ D-coderef → validate, don't free-type.** At publish, derive the class name from the imported source and refuse
  unless `codeRef.endswith('.'+className)` — a typo is caught at the master's desk, not at `getattr` on a field phone.
- **✅ D-verbench → all-flat.** The bench lists every `(codeRef, version)` row (+ built-ins), so any old version can be
  reproduced. Revisit only if the list bloats (it's a master dev tool).
- **✅ D-fallback → KEEP the built-in as the fallback** (reached via the *unsealed-row* branch and the *offline* branch
  of B6.4). "Always from the DB" holds for **assigned+sealed** users; the built-in is the safety net for everyone else
  (dev bench, offline, or a bare seed row). The plugin class therefore **stays in the APK** for now (dropping it for a
  smaller APK is a later, DB-only-hard decision — not now).
- **✅ F16 seed question → keep demo/ELP on the built-in for now (no signed seed).** The seed's bare `"1.0"` rows resolve
  to the built-in via the unsealed branch — **no seed change needed**, and pumpkin's *in-tree* source (under active
  peak-ratio dev) is what the demo runs, so no re-sign treadmill. A **real signed** seed row is deferred until pumpkin
  stabilizes (see F16 below for the mechanism when we do it).

##### New rubber-duck findings (2026-07-18, post-decision)

- **🟢 F16 — the "bootstrap gap" DISSOLVES into a dispatch choice (was 🔴, resolved by row-sealedness).** The concern:
  `UserSeedLogicModule` (`:121`, `:165`) binds demo + ELP to a `getOrCreate` pumpkin `"1.0"` row with
  **`source`/`signature`/`keyId` all NULL**, and the server **cannot** seed a *signed* row (private key is off-server,
  §3). A naïve *version-present → DB* dispatch would hit that bare row → `verifySealed` fails → demo login dead.
  **Resolution (B6.4): dispatch on row-sealedness** — an unsealed row is a deliberate "run the shipped built-in"
  pointer, not a broken row. So:
  1. **The seed needs NO change** — its bare `"1.0"` rows resolve to the built-in; the demo runs pumpkin's in-tree
     source, unaffected by signing.
  2. **Real DB delivery of pumpkin is still a one-time MASTER act** — but there are two routes, and we pick by phase:
     - **now / dev:** stay on the built-in (bare rows). Zero crypto, no drift.
     - **at release / to demo distribution:** *either* publish from the app once (B4/B5 runbook) *or* seed a
       **pre-signed** row via an Alembic **data migration** — Edwin signs pumpkin **offline** (his key) → the sealed
       blob (`source+signature+keyId+version+targetSdk`) is committed → the migration inserts it (immutable → migration,
       not the idempotent seed) and repoints the serials; bump `"1.0"` → `"1.0.0"` semver. Deferred (F16 seed decision
       above).
- **🟠 F17 — the SDK gate finally goes live (as designed, §4).** The first DB-delivered pumpkin whose `targetSdkVersion`
  exceeds the installed APK's `SDK_VERSION` yields the honest *"this plugin needs a newer app"* — the case §4 was built
  for. Inert until now; B6 is where it first bites. No new work, but the B6 verify must include the mismatch path.
- **🟢 F18 — batch assignment is cheap and safely postponable.** Assignment is per-serial (`SpectrometerSetup.pluginId`);
  a batch UI is just a loop over `saveSetup(serial, codeRef, version)` across many serials. Nothing in the model blocks
  it, and the per-serial path is unchanged by it. **Recorded as B8 (postponed, Edwin 2026-07-18)** — no structural debt
  incurred by deferring.

**B6 dependencies & the FIRST SLICE.** B6.4's dispatch flip is **coupled to F16 and B5.4**: flipping the dispatch
without the sealedness rule + the login version-thread would break the demo/ELP login (they'd fetch their bare seed
rows). So the honest first slice — if we start here rather than with the publish/assign UI — is:

> **Slice 1 = B5.4 (login carries `version`) + B6.4 (row-sealedness dispatch) + F16 (unsealed-row = built-in) + B6.1-B6.3 (bench lists DB rows).**
> No B4/B5 *UI* needed: DB-delivery becomes real, the demo keeps working on the built-in, and the bench can run a
> hand-seeded sealed row (a test-signed blob, the same "B4 stand-in" trick B0–B3 used). **B4+B5 publish/assign UI is Slice 2.**

This inverts the earlier "B4+B5 first" sequencing note above: with row-sealedness, the *load+dispatch* path is
demonstrable **before** any UI, and it's the lower-risk place to start. (The B4+B5 coupled-sweep description remains
correct for Slice 2.)

##### Slice 1 — checkpointed build order (as designed, 2026-07-18)

Four checkpoints, each green before the next — the same shape as the B0–B3 sweep. No new DB columns, no migration
(the seed is untouched); the only edits are `resolve`'s dispatch + the login version-thread + the bench enumeration.

| CP | Change | Where | Green when |
|---|---|---|---|
| **CP1** | **B6.4 dispatch** — `resolve(codeRef, version)` keys on row-sealedness: `version None → builtin` (no fetch); fetch row → `source present → verify+exec` / `source NULL or fetch-failed → builtin if shipped, else error`. Split the fetch out of `_resolveDbPlugin` into `_resolveDbPluginFromRow` | `PluginRegistry` (app) | pure unit tests: the 3 existing loader tests still pass **+** unsealed-row→builtin, offline→builtin, unknown-no-builtin→error |
| **CP2** | **B5.4 login version-thread** — `resolveBundle` returns `pluginVersion`; `LoginLogicModule` carries it; `CurrentUserSession` stores it + `getPluginVersion()`; `importPlugin(codeRef, version=None)` → `resolve(codeRef, version)`; wizard passes `getPluginVersion()` | `-model` ×2, app ×3 | `test_plugin_binding_and_seed` green; pumpkin login now carries `version="1.0"` and still resolves (bare row → builtin) |
| **CP3** | **B6.1–B6.3 bench enumeration** — `PluginRegistry.listAll()` = built-ins + `listPlugins()` rows; bench carries the selected **entry** (codeRef+version) and labels DB rows `title @ version` | `PluginRegistry`, `DevMeasurementBenchViewModule` | unit test: `listAll` merges built-ins + a mocked `listPlugins`; bench builds headless |
| **CP4** | **End-to-end** — a **test-signed sealed row** (ephemeral key → TRUSTED_KEYS, the B0–B3 stand-in trick) resolves + runs via the DB branch, while the demo user still rides the built-in | tests | full blast-radius suite green (registry · loader · binding · wizard-offscreen) |

**Provenance (A3) is explicitly OUT of Slice 1** — stamping `workflow.pluginVersion` needs a new `SpectralWorkflow`
column (a migration), so it stays deferred to whichever sink lands first (§8 A3 note). Slice 1 threads the version to
*resolve*, not to *persistence*.

**Risks:** the CP2 thread crosses model↔app (5 files) — miss a hop and the version silently drops to `None` (a sealed
row would then be shadowed by the built-in, the inverse of F12); `listAll()` must not fire a server call at app
*startup* (build the combo lazily / tolerate `listPlugins()==[]` when logged-out).

> **As built — Slice 1 ✅ IMPLEMENTED 2026-07-18.** All four checkpoints green.
> - **CP1** — `PluginRegistry.resolve` now dispatches on row-sealedness: `version is None → _resolveBuiltin` (no
>   fetch); else `_fetchDbRow` → `source` present → `_resolveDbPluginFromRow` (verify → SDK-check → exec) / else (bare,
>   offline, unknown) → built-in if shipped, else `ValueError`. `_resolveDbPlugin` split into `_fetchDbRow` +
>   `_resolveDbPluginFromRow`. Tests: the 3 loader tests hold + 4 new (`version=None` no-fetch, unsealed→builtin,
>   offline→builtin, unknown-no-builtin→raise).
> - **CP2** — version threaded end-to-end: `InstrumentLogicModule.resolveBundle` returns `pluginVersion`;
>   `LoginLogicModule` carries it (success + bad-creds); `CurrentUserSession` stores it + `getPluginVersion()`;
>   `SpectralWorkflowEngine.importPlugin(codeRef, version=None)` + `resolvePluginFromSession`; `WizardViewModule.__startNew`
>   passes it. `test_plugin_binding_and_seed` asserts the seed's `"1.0"` rides login→session (and resolves to the
>   built-in via the unsealed branch — offline in tests, bare-row online).
> - **CP3** — `PluginRegistry.listAll()` merges built-ins + `listPlugins()` rows; the bench carries the selected
>   **entry** (codeRef+version) and labels DB rows `title @ version`. `listAll` unit-tested (merge + empty-DB degrade);
>   bench imports headless and degrades to built-ins offline.
> - **CP4** — 37 green across the blast radius (registry · loader · binding · signature · sdk-ops · pumpkin wizard ·
>   pumpkin end-to-end); a **test-signed sealed row** loads + runs via the DB branch (`test_signed_db_plugin_loads_and_runs`).
> - **NOT rig-verified:** live desktop GUI click-through of the bench selector listing a real published DB row (needs
>   the B4 publish UI or a hand-inserted signed row); paths verified headlessly + by unit tests only.
> - **Out of scope (as planned):** A3 provenance stamp (`SpectralWorkflow.pluginVersion` — needs a migration), B4/B5
>   publish/assign UI (Slice 2).

##### B8 — batch assignment UI (postponed, Edwin 2026-07-18)

Assign one `(codeRef, version)` to **many serials** at once (a rollout console beyond the one-serial editor). Pure UI
over the existing per-serial `saveSetup` — a selection list + a loop. No model change. Deferred until there is a fleet
large enough to feel the one-at-a-time pain; recorded so the per-serial design (B5) is understood as its building block,
not a dead end.

## 9. Dropped from the original D0–D8

- **Separate `spectracs-plugins` repo** → moved to [`SPEC_project_structure.md`](SPEC_project_structure.md) (S5),
  along with its CI. It is a project-structure concern, not a distribution one.
- **Separate master publish CLI** → B4 extends `PluginViewModule` (§7).
- **`plugin_sdk` back-compat promise** → §4's integer is enough; the model layer stays free.
- **Play-policy gate** → moot (§6).
- **"Pin vs auto-update" as an open question** → answered by §1: pinning is what the model *does*; rollout is an
  explicit per-serial act.

## 10. Out of scope / unchanged

The camera mechanics, M1 rendering, the M2 report. This spec is **identity + trust + storage + loading** — not how
plugins render.

## Verification (when implemented)

1. A published plugin appears in the bench selector and runs, rendering via M1.
2. **Publishing v2 does not move any instrument.** Assigning serial A to v2 leaves serial B on v1. Re-assigning A
   back to v1 works — the row is still there.
3. A tampered/unsigned `DbPlugin.source` is **refused** by the client — as are a swapped `version`, a re-pointed
   `codeRef`, and an unknown `keyId`.
4. A workflow run records the exact plugin `codeRef`+`version` (visible in M2's embedded metadata).
