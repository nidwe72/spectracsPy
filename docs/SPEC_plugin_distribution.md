# SPEC — Plugin distribution & storage (Milestone 3)

Status: **Track A IMPLEMENTED (A1·A2); A3 deferred; Track B: M0·B0·B1·B2·B3 IMPLEMENTED 2026-07-18, B4·B5·B6 DESIGN,
B7 postponed** (spec-first; implement on explicit request only). Source: Edwin (2026-07-10; **all open questions settled 2026-07-16**;
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
