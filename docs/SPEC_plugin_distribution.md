# SPEC — Plugin distribution & storage (Milestone 3)

Status: **DESIGN — not implemented** (spec-first; implement on explicit request only). Source: Edwin (2026-07-10;
**all open questions settled 2026-07-16**). **M1** ([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md))
shipped, so the original dependency is cleared. Trust model **Option 1** (signed, client-side load).

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

**Track A needs no decisions and can start any time. Track B is the distribution proper; B0 is the hinge.**

| Ph | Change | Where | Verify |
|---|---|---|---|
| **A1** | **`PluginRegistry`** — enumerate in-app + resolve by `codeRef`; **delete both hard-coded lists** (`DevMeasurementBenchViewModule.py:72`, the `CurrentUserSession.py:67` fallback) | host + logic | bench selector + login binding both resolve via the registry; no regression |
| **A2** | `SDK_VERSION` constant; plugins declare `targetSdkVersion` | `plugin_sdk` | mismatch reports *"needs a newer app"*, not `AttributeError` |
| **A3** | **Provenance** — the run records the resolved plugin row | model + engine | a run names its exact version in M2's embedded JSON |
| **B0** | **IDENTITY** — `(codeRef, version)` per row; insert-not-upsert; rows immutable once signed | model + server + migration | publishing v2 leaves v1 intact; **assigned setups do NOT move** |
| **B1** | Extend `DbPlugin`: `source`, `signature`, `keyId`, `author`, `targetSdkVersion` | model + server | a row round-trips sealed |
| **B2** | **Sign on the master's machine** (key never in git, never on the server); client verifies over the tuple; `TRUSTED_KEYS` **list** in app source; root-key hierarchy (§3b) | app (sign + verify), server (serve key-list) | tampered source, swapped version, re-pointed `codeRef`, unknown `keyId`: **all refused** |
| **B3** | **Loader** — verify → SDK check → `exec` source → find `SpectralPlugin` → instantiate; lint gate | client | a DB plugin loads + runs on the bench |
| **B4** | **Publish UI** — editor becomes publisher (§7) | `PluginViewModule` | master publishes from the app; a new row lands |
| **B5** | **Assign UI** — version picker | `SpectrometerSetupViewModule` | serial A on v2, serial B still on v1; re-assign back = revoke |
| **B6** | Registry learns DB plugins | A1's registry | in-app + DB plugins both listed, both run |
| **B7** | Android spike — `exec` under p4a | `android/` | a DB plugin runs on the Note 20 |

**Ordering vs. [`SPEC_project_structure.md`](SPEC_project_structure.md): that spec first** (Edwin's lean, agreed).
The tracks are near-independent — B4's publish step is a file picker that signs bytes and does not care which repo
the file came from, and `sciens.spectracs.plugin_sdk` keeps its import path across the move, so source published
before still resolves after. The reasons to re-tier first: its cost grows every week while B0's does not; it has
three customers to M3's one; and publishing source *from the app repo* to be loaded by *the app that already
contains it* is a strange demo of a good idea. **What flips it:** APK rebuilds actually starting to hurt.

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
