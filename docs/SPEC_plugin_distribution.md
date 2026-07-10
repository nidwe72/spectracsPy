# SPEC — Plugin distribution & storage (Milestone 3)

Status: **DESIGN — not implemented** (spec-first; implement on explicit request only). **Depends on M1**
([`SPEC_plugin_driven_convergence.md`](SPEC_plugin_driven_convergence.md)) — a distributed plugin is only useful once
the host renders whatever it declares. Source: Edwin (2026-07-10). Trust model **chosen: Option 1** (signed,
client-side load).

Theme: **convergence makes a plugin a *droppable unit*; distribution *ships* it.** Plugins are developed in their own
repo, stored as source in the DB, signed by a master, verified + loaded + executed **on the client**.

---

## 0. Why client-side signed load (Option 1)

- **CPU-time (Edwin).** Execution scales with **clients**, not the server — the server only stores/signs. Option 2
  (server-side execution) would run every user's processing/evaluation on your hardware; cost grows with users.
- **Matches the existing split** — master authors, end-user consumes.
- **Option 2 recorded as the alternative:** safer (client runs no plugin code — the server streams view-models) but
  loads server CPU and needs a client↔server split because the **camera is client-side**. Rejected on CPU + complexity.

---

## 1. Trust model — the honest version

**Security = key control, full stop.** The master signs plugin source with a **private key**; the client verifies with
a **public key** (shipped with the app) **before** loading. Trust reduces to *"you trust whoever holds the signing key."*

- **The "imports only `plugin_sdk`" check is hygiene, NOT a sandbox.** Static import analysis is trivially bypassable
  (`__import__`, `getattr`, `exec`, builtins), so it catches honest mistakes, not a malicious *signed* author. **Do not
  present it as a security boundary** — the signature is the only boundary.
- **Sandboxing is ruled out** — Python cannot safely execute untrusted code in-process.
- **Key management (decision point):** private signing key is master-held, ideally offline. Public verify key is either
  **shipped with the app** (rotation ⇒ app update) or **fetched over the trusted TLS/server channel**. §8.

---

## 2. `plugin_sdk` becomes a versioned public API (the big implication)

Once plugins live in a **separate repo + the DB**, `plugin_sdk` is no longer an internal facade you can change freely —
it is a **published contract**. Consequences:
- `plugin_sdk` must be **versioned and kept back-compatible**; adding view-models (M1) is an *additive* extension.
- A stored plugin records the **`plugin_sdk` version it targets**; the client checks compatibility before loading.
- This is new discipline distribution forces — and it's why M1's view-model additions should land *before* the API is
  externally frozen.

---

## 3. The registry — the shared linchpin

A **`PluginRegistry`** is where convergence-selection and distribution-loading meet: it **enumerates** available plugins
(for the bench selector, M1 §4b) and **resolves by `codeRef`** (for the end-user AppUser→plugin binding). In-app plugins
register directly; DB plugins are loaded via §4. Both the bench's free selection and the end-user's bound resolution go
through the one registry.

---

## 4. Storage + loading

- **`DbPlugin` (server), extended** from today's `codeRef`-only binding to carry: `source` (TEXT), `codeRef`
  (identity/key), `version`, `signature`, `author`, `targetSdkVersion`.
- **Loader (client):** fetch `DbPlugin` → **verify signature** → check `targetSdkVersion` compatibility → import the
  source into a fresh module (`importlib.util` / `exec`) → find the `SpectralPlugin` subclass → instantiate. The
  import-hygiene check runs here as a **lint gate only**.
- **Qt-free stays load-bearing** — it keeps a plugin testable/validatable and (if Option 2 is ever revisited) runnable
  server-side.

---

## 5. Separate repo + publish pipeline

- **`spectracs-plugins`** repo: plugins developed against a **pinned `plugin_sdk`**; CI runs each plugin headlessly
  (`engine.runAll`) + its tests, so a plugin is proven before it ships.
- **Publish:** a master tool **signs** the source and writes a `DbPlugin` row (source + version + signature + codeRef +
  targetSdkVersion) via a server endpoint. The private key never leaves the master.

---

## 6. Provenance / version pinning

Each **workflow run records the plugin `codeRef` + `version`** that produced it — a QM/lab result must be traceable to
the exact plugin version (reproducibility). This **feeds M2's embedded whole-Workflow metadata**
([`SPEC_bench_pdf_export.md`](SPEC_bench_pdf_export.md) §5). **Pinning:** a bound user stays on a version until
explicitly updated, so a plugin update never silently changes a lab's results.

---

## 7. Implementation phases

| Phase | Change | Where | Verify |
|---|---|---|---|
| **D0** | Freeze + **version** the `plugin_sdk` API; add an SDK-version constant; document the contract | `plugin_sdk` | plugins declare a target SDK version |
| **D1** | **`PluginRegistry`** — enumerate in-app plugins + resolve-by-`codeRef` (feeds the bench selector) | host + logic | selector lists plugins; binding resolves |
| **D2** | Extend **`DbPlugin`**: `source`, `version`, `signature`, `author`, `targetSdkVersion` | server model + migration | a plugin row round-trips |
| **D3** | **Sign + verify** — master signs source (private key); client verifies (public key) before load; key mgmt | server tool + client | tampered/​unsigned source is rejected |
| **D4** | **Loader** — verify → SDK-compat check → import source → find `SpectralPlugin` subclass → instantiate; lint gate | client | a DB plugin loads + runs |
| **D5** | **`spectracs-plugins` repo** + CI (headless `runAll` + tests) + **publish** tool (sign → ingest `DbPlugin`) | new repo + tool | a plugin published from the repo appears in the registry |
| **D6** | **Provenance** — record `codeRef`+`version` on the workflow run (feeds M2 metadata) | model + engine | a run names its plugin version |
| **D7** | **Wire selection** — bench selector (free) + end-user binding (bound) both resolve via the registry (in-app + DB) | hosts | both paths load in-app + DB plugins |
| **D8** | Spec + verify (desktop; Android `importlib`/`exec` check) | this spec | pumpkin loaded from DB runs on the bench |

## 8. Open decisions
- **Public key delivery:** shipped-with-app (rotation = app update) vs fetched over TLS from the server?
- **Update policy:** auto-update bound users to a new plugin version, or pin until explicit (lab reproducibility)?
- **Android exec:** confirm `importlib`/`exec` of source works under buildozer/p4a (desktop is fine).

## 9. Out of scope / unchanged
The camera mechanics, M1 rendering, the M2 report. This spec is **loading + trust + storage** — not how plugins render.

## Verification (when implemented)
1. A plugin published from `spectracs-plugins` appears in the bench selector and runs, rendering via M1.
2. A tampered/unsigned `DbPlugin.source` is **refused** by the client.
3. A workflow run records the exact plugin `codeRef`+`version` (visible in M2's embedded metadata).
