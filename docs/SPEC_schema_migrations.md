# SPEC — Schema migrations (Alembic)

Status: **IMPLEMENTED (2026-07-18)** — as part of the M0+B0–B3 sweep. Source: Edwin (2026-07-18), surfaced as
finding **F3.1** while rubber-ducking [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md) Track B.
**Infrastructure, not a feature** — it outlives M3; M3 (and every future schema change) *depends on* it. Alembic,
both trees in `-model`, guarded init (policy c), boot-time auto-apply — see §3, and the as-built §7.

Theme: **the DB schema must be able to change without losing data — today it silently can't.**

---

## 0. The problem — `create_all` is blind to columns

Every DB in the codebase is built by SQLAlchemy `metadata.create_all(engine)` (see `DbBase.session_factory`,
`DbServerBase.server_session_factory`). `create_all` creates **missing tables** and nothing else — it **never adds
a column to a table that already exists**. So the moment a model grows a field, every already-existing DB file is
silently out of sync, and the first write to the new column throws:

```
sqlite3.OperationalError: table spectrometer_calibration_profile has no column named calibrationSpectrumJson
```

That is not hypothetical — it is a **live bug** on the current dev `spectracsPyServer.db`. Worked example:

```
MODEL (current):   SpectrometerCalibrationProfile.py:37   calibrationSpectrumJson = Column(Text)   ← added later
WRITE:             InstrumentAuthoringLogicModule.py:66    cal.calibrationSpectrumJson = json.dumps(spectrum)
LIVE DB:           spectrometer_calibration_profile   →   (no such column — table predates the field)
RESULT:            OperationalError: table … has no column named calibrationSpectrumJson
```

The model grew a column; `create_all` saw the table already existed and **did nothing**; the first write throws.
There is **no migration tooling of any kind** in the tree (no Alembic, no `ALTER TABLE`, no `schema_version`). Adding
columns "works" only because we keep deleting and reseeding dev DBs by hand.

**This is M0's built-in acceptance test.** Adopting Alembic makes rev1 (baseline) = the current models — which
*include* `calibrationSpectrumJson` — so the drifted dev DB, reseeded into rev1, gains the column and the bug clears
the moment M0 lands. It is exactly the failure **B1 would hit five times** (`source`, `signature`, `keyId`, `author`,
`targetSdkVersion` on `db_plugin`), which is why M0 gates Track B.

**This blocks M3 directly:** B1 adds five columns to `DbPlugin` (`source`, `signature`, `keyId`, `author`,
`targetSdkVersion`). Without a migration mechanism those columns never land on an existing server DB.

---

## 1. Decision — adopt Alembic

**Alembic** (SQLAlchemy's official migration tool). Ordered migration scripts, each with `upgrade()` / `downgrade()`;
a hidden `alembic_version` table records where a DB is; `upgrade head` applies exactly the pending ones in order. It
can autogenerate a migration by diffing the model classes against the live DB.

The lighter alternative — a hand-rolled `schema_version` table + a list of migration functions — was **rejected**:
for a "very sound / neat" solution (Edwin) it would just be a worse Alembic. Reconsider only if the two-DB setup
proves painful under p4a (low risk — see §4).

### Two nuances that bite here

- **SQLite has weak `ALTER TABLE`** (no in-place drop/alter of a column). Alembic handles this with **batch mode** —
  it copies the table, rebuilds it with the new shape, and swaps. Must be switched on (`with op.batch_alter_table(...)`).
- **Two databases, two metadatas.** `spectracsPy.db` (app, `DbBaseEntity`) and `spectracsPyServer.db` (server,
  `ServerDbBaseEntity`) are separate engines with separate metadata. Alembic must manage **both** — two migration
  environments (one per DB), each with its own `alembic_version` and script tree. Not a one-liner; see §3.

---

## 2. Why NOW — greenfield is the cheapest baseline

**There is no spectracsPy install in the real world yet.** Counter-intuitively that is the argument *for* adopting
now, not deferring:

- **The baseline is free today.** Adopting = declaring "the current schema = revision 1" and moving forward. With no
  field data to preserve, that baseline is trivial. Retrofit Alembic *after* there are deployed DBs and you must find
  every install and stamp it at the correct revision — the expensive version of the same job.
- **B0/B1 is the perfect first real migration** — low-stakes (no precious data; a botched run just reseeds), an ideal
  shakedown for the tooling.
- **It ends the drift-bug class** (the calibration error above stops being a way of life).

Meanwhile the *current* calibration bug clears independently, right now, by deleting the dev `spectracsPyServer.db`
and letting the seed rebuild it — it is all reproducible seed data. Alembic is about the day reseeding stops being
free (first real calibration, first real user, first field install).

---

## 3. Design (settled 2026-07-18)

Mental model: **Alembic is git, for the schema.** A migration script is a commit; the baseline is the initial
commit; `--autogenerate` is `git add -A`; `upgrade head` is a fast-forward.

### 3.1 Two moments — author (manual, rare) vs apply (automatic, every boot)

- **Authoring — the developer (human or AI), on a dev machine, only when a model changes.** A thin helper sets the
  multi-repo `PYTHONPATH` and calls `alembic … revision --autogenerate -m "…"`, producing a script under
  `alembic/<db>/versions/`; it is **reviewed and committed**. Autogenerate writes the script by diffing the model
  classes against the DB; hand-review because autogen misses some server-side defaults / constraints. Example:

  ```bash
  ./authorMigration.sh server "add plugin source column"
  #  → PYTHONPATH=<all repos> alembic -c alembic/server/alembic.ini revision --autogenerate -m "…"
  #  → writes alembic/server/versions/ab12_add_plugin_source_column.py  (upgrade()/downgrade(), batch mode)
  ```

- **Applying — every process, automatically, at startup.** `initDatabases()` calls
  `command.upgrade(cfg, "head")` — the app on its DB, the server on its DB. **The user never runs anything;** a
  booting machine just fast-forwards its DB. This replaces the lazy `create_all` in the hot path.

### 3.2 Location — both alembic trees in `-model`

Deps point down — `base ◀ model ◀ core ◀ app` — with the **server a sibling of the app** (neither imports the
other; they talk only over Pyro). So a DB's migration files must live where the process that owns that DB can reach
them: the **app** migrates `spectracsPy.db`, the **server** migrates `spectracsPyServer.db`, and the server does
**not** ship the app repo — so server-DB migrations may **not** live in the app repo.

`-model` is the one tier **both** processes already import (it defines every entity *and* the persistence logic), so
**both trees live in `-model`**, co-located with the entities they mirror:

```
-model/
  alembic/
    app/     alembic.ini · env.py · versions/    → applied by the APP process    (spectracsPy.db)
    server/  alembic.ini · env.py · versions/    → applied by the SERVER process (spectracsPyServer.db)
```

Two explicit environments (one per DB, each with its own `alembic_version` and script tree) — simpler than the
multi-DB template. Each `env.py` imports its metadata (`DbBaseEntity` / `ServerDbBaseEntity`) from `-model` locally.

### 3.3 `create_all` ↔ Alembic coexistence — the guarded init (policy **c**)

**The trap:** a DB built by `create_all` has head schema but **no `alembic_version` stamp** → Alembic thinks it is at
`base` and re-runs every migration. So `initDatabases()` **guards**, per DB, once at boot:

1. **No tables yet** → `create_all` (fast, builds head) → `alembic stamp head`.  ← *tests land here: no migration
   run, behaviour unchanged.*
2. **Tables + `alembic_version`** → `upgrade head` (apply pending — the real-world evolve case).
3. **Tables, no `alembic_version`** (a pre-Alembic DB) → `stamp <baseline>` then `upgrade head` (the adoption case).

This keeps `create_all` as the fast fresh-schema builder the **test-suite relies on** (tests never touch
`alembic_version`, so they neither slow down nor need the Alembic env), while Alembic only ever *evolves* an existing
DB. The current **drifted dev DBs** (missing `calibrationSpectrumJson`) are pre-baseline and disposable → **delete +
reseed**; they re-enter through case 1.

### 3.4 The boot refactor

There is **no explicit DB-init step today** — `create_all` fires lazily inside `session_factory()` /
`server_session_factory()` at ~19 call sites. Adoption adds **one `initDatabases()` called once at each entry point**
(app `main.py`, server `serveLocalForever()`) *before* any session use, and removes `create_all` from the lazy hot
path (the guarded init in §3.3 owns fresh-DB creation now).

### 3.5 Baseline

`--autogenerate` rev1 from the current models (the full existing schema), hand-reviewed. **Batch mode on** for all
SQLite ALTERs. Subsequent model changes → small autogenerated increments on top.

---

## 4. Android / p4a

Low risk, and postponed with the rest of Android. Migrations run **server-side**, and Alembic + its one templating
dep (Mako) are **pure Python** — no native build. The server-on-Android story is itself postponed, so this is a
"don't paint ourselves into a corner" note, not a now-problem. Keep migrations free of desktop-only assumptions.

---

## 5. Relationship to M3

M3 Track B **depends on this** and is its first customer:

- **B0** (identity `(codeRef, version)`, insert-not-upsert) + **B1** (the five sealed columns) ship as the **first
  post-baseline migration**.
- Ordering (from [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md) §8): **migrations → B0+B1 → …**.

## 6. Out of scope

Data *content* migrations beyond schema (none needed yet). ORM/SQLAlchemy version upgrades. The app-DB vs server-DB
split itself (unchanged — this spec only teaches each to evolve its own schema).

## 7. As built (2026-07-18)

- **`-model/alembic/{app,server}/`** — two envs, each `alembic.ini` + `env.py` (imports its metadata + the new
  `AllEntities` aggregator so every table registers) + `versions/`. `render_as_batch=True` (SQLite-safe ALTER).
- **`AllEntities.py`** (`-model`) imports every entity so both metadatas are complete for migrate/create.
- **`DatabaseInitializer.py`** (`-model`) — the guarded init (policy c): `initAppDatabase()` / `initServerDatabase()`.
  Wired into the app (`spectracsMain.py`, after QApplication) and the server (`SpectracsPyServer.__init__`, before
  bootstrap/seed). `create_all` is retained as the fresh-schema fast path (fresh → create_all + `stamp head`); it is
  harmless alongside Alembic because the guarded init runs first at boot.
- **Baselines** autogenerated: server rev `f641f17a1539` (15 tables), app rev `7200faf1d770` (2 tables). ⚠️ The
  app baseline's "2 tables" was a **symptom of the §8 `AllEntities` gap** (the 7-table workflow graph was invisible
  at M0), not a complete picture — left as-is deliberately (D-baseline-complete = NO); completeness is now enforced
  by the §8 guard test instead.
- **`authorMigration.sh`** (app repo) — the dev author helper. Deps `alembic` + `PyNaCl` added to `requirements.txt`.
- **Proven:** the calibration `OperationalError` is gone (fresh at-head DB); and an existing DB at baseline `f641`
  **upgraded to `405d2ce2cec1`** (the B0/B1 migration), gaining 5 columns — the evolve `create_all` could never do.

## Verification (met)

1. ✅ Adding columns (B1) + a migration → an **existing** dev DB gained them after `upgrade head` (f641 → 405d).
2. ✅ A fresh empty DB comes up fully at `head` (create_all + stamp head).
3. ✅ Both DBs migrate independently, each tracking its own `alembic_version`.

## 8. 🔴 `AllEntities` violates its own completeness invariant (rubber-duck 2026-07-19; ✅ AE.1–AE.4 IMPLEMENTED 2026-07-19)

> **✅ IMPLEMENTED 2026-07-19** (AE.1–AE.4): the 7 workflow entities added to `AllEntities` (app metadata 2→9 tables,
> no cycle); `tests/test_all_entities_complete.py` guard added and **proven both ways** — green with the fix, and it
> fails naming all 7 tables when they're removed; AE.2 dry-run autogenerate now yields an **empty diff** (no drops);
> docstring + this spec point to the guard. Two flaws found and fixed while building the test: (i) it must run in a
> **subprocess** — pytest collection imports `model.spectral`, polluting the process-global metadata and masking an
> omission; (ii) it must **filesystem-walk the `-model` tree** via `DbBase.__file__`, because `walk_packages` over the
> `sciens.spectracs.model` namespace (which spans both repos, app side Qt-bound) discovers nothing. Desktop trees only;
> Android `AllEntities` copies untouched (B7).

Surfaced by A3 (`SPEC_plugin_distribution.md` F-a3-3): authoring the `spectral_workflow.pluginVersion` migration,
autogenerate proposed **dropping the entire workflow table graph**. Root-caused here.

### The bug — one omission, stated as an invariant above

§5/§7 promise *"`AllEntities` imports **every** entity so both metadatas are **complete** for migrate/create."*
It doesn't. The **app** DB (`DbBaseEntity`) has **9** entities; `AllEntities` imports **2** of them
(`ApplicationConfig`, `ApplicationConfigToSpectrometerProfile`). The missing **7 are the whole `model.spectral`
workflow graph** — all `DbBaseEntity` subclasses, all app-DB tables:

    SpectralWorkflow · SpectralWorkflowPhase · SpectralWorkflowStep · SpectraContainer ·
    Spectrum · SpectralWorkflowMetadata · EvaluationResult

(The server side is fine — all 15 `ServerDbBaseEntity` entities are imported.) So Alembic's app `target_metadata` =
**2 tables** when the app DB really holds **9**.

### Two symptoms, one cause — and the smoking gun

- **(a) autogenerate wants to DROP the 7.** Metadata (2) vs the live create_all-built DB (9) → Alembic reads the 7 as
  "in DB, not in model" → emits `drop_table`. This is what bit A3; the migration had to be hand-written.
- **(b) the app baseline is frozen incomplete.** Server baseline `f641f17a1539` = **15** `create_table`; app baseline
  `7200faf1d770` = **2** (§7 records "2 tables" as if normal). The asymmetry *is* the fingerprint: at M0 the server
  entities were in `AllEntities`, the workflow ones weren't, so the app baseline captured only what `AllEntities` knew.

**Why it never broke at runtime:** the workflow tables are still built — by the *lazy* `create_all` in
`session_factory()` / `save_session()` (`DbBase.py:34/39`) once the app imports `SpectralWorkflow`. Only Alembic's
isolated env (imports **only** `AllEntities`) is blind. That's exactly why A3's save→reload passed while autogenerate
misfired.

### The fix — restore the invariant (Option A, validated read-only)

Add the 7 workflow entities to `AllEntities`' **app-DB** section (explicit per-entity, matching the file's style and
robust against the `SpectralWorkflow.py` footer-hub changing). Verified live, no code change: importing the graph
takes app `DbBaseEntity.metadata` from **2 → 9** tables, **no import cycle**, all Qt-free (`-model`;
`EvaluationResult` included). Consequences:

- Future workflow-table migrations autogenerate **cleanly** (metadata 9 == a create_all DB 9 → empty diff; a real
  column change → just that column).
- `DatabaseInitializer` boot `create_all` builds the workflow tables **at boot** instead of lazily — more
  deterministic, no regression (`create_all` is additive).
- **Server metadata untouched** (separate `ServerDbBaseEntity` Base) — no cross-contamination.
- **Android `AllEntities` copies** (`app_src`/`.buildozer`) left alone — B7.

### The one judgment call — D-baseline-complete (recommend: DON'T)

Should the app baseline *also* be made complete (add the 7 `create_table` to `7200faf1d770`, or a new create-table
migration), so migration history builds from truly-empty?

**Recommend NO.** §3.3's guarded init deliberately makes **`create_all` the fresh-schema builder** and Alembic *"only
ever **evolves** an existing DB"* — no real boot ever builds schema from migration history, so an incomplete baseline
is **permanently shielded** (the "`f0ac79b33dde` add_column would fail on a from-empty `upgrade`" path is unreachable
in the boot flow *and already exists today*). Editing a committed baseline is a history rewrite that Alembic won't
re-run on already-stamped DBs anyway → marginal value, and it contradicts the stated philosophy. **Fix `AllEntities`;
leave history as-is.**

### Residual discipline (even after the fix)

Keep authoring **app** migrations against a create_all-built (head) dev DB — the A3.3 discipline — because the baseline
stays intentionally partial; autogenerate's correctness rides on the DB it diffs having the tables. With `AllEntities`
complete, that create_all DB now matches metadata exactly, so the diff is clean.

### The completeness guarantee — a guard test, not a comment

**Today the only thing enforcing "import EVERY entity" is the docstring atop `AllEntities` — and it already failed**
(it says "EVERY" while omitting 7). A comment can't fail a build. So the fix (AE.1) is paired with a mechanism that
makes the invariant **self-enforcing**: a guard test that goes red, naming the missing table, the moment someone adds
an entity and forgets `AllEntities`. This mirrors the existing `test_plugin_registry_and_sdk` idiom (the check that
would have caught F1 at CI time) — the entity-registry equivalent, and it would have caught *this* bug before A3.

**Keep the explicit list; the test is its safety net.** The list is deliberately explicit — see the import-order
sensitivity below — so runtime import stays curated. Auto-discovery is used only *inside the test* as the oracle for
"what really exists".

**Why not runtime auto-import (`walk_packages`)? — import-order sensitivity.** Registration onto the metadata is
order-independent, but Python's *module loader* is not. `SpectralWorkflow.py` resolves its relationships by string
(`relationship("SpectralWorkflowPhase", …)`), resolved in one batch by `configure_mappers()` at first query — so every
target must be imported by then. Its footer "registration hub" guarantees that (importing the parent drags in the
graph), and does so in a **deliberately one-directional order**: the parent imports children at the *bottom* (after its
own class exists); children import only base + leaf enums, never back up. An unordered runtime walk can hit the reverse
order and trip a partially-initialized-module `ImportError`. So the walk belongs in a test, never in the hot path.

**Why the test itself is cycle-safe:** it imports `AllEntities` **first** (curated, safe order → whole graph loaded),
snapshots the declared tables, **then** walks the model tree — by which point every module is already in `sys.modules`,
so the walk re-imports nothing and only *discovers*. Walk = oracle, never a fresh import path.

    guardTest:
      import AllEntities                     # 1) curated order — builds the graph safely
      declared = {DbBaseEntity.metadata.tables} ∪ {ServerDbBaseEntity.metadata.tables}
      walk_and_import(sciens.spectracs.model) # 2) no-op re-imports; forces any un-listed entity to register
      actual   = {DbBaseEntity.metadata.tables} ∪ {ServerDbBaseEntity.metadata.tables}
      assert actual == declared, f"missing from AllEntities: {actual - declared}"

### Implementation phases

    +--------+------------------------------------------------+---------------------------------+------------------------------------------+
    | Phase  | Change                                         | Where                           | Verify                                   |
    +--------+------------------------------------------------+---------------------------------+------------------------------------------+
    | AE.1   | import the 7 app-DB workflow entities in the   | -model AllEntities.py           | app DbBaseEntity.metadata = 9 tables;    |
    |        | app-DB section (explicit per-entity)           | (app-DB section)                | no import cycle at boot / alembic env    |
    +--------+------------------------------------------------+---------------------------------+------------------------------------------+
    | AE.2   | regression: authoring an app migration now     | authorMigration.sh app          | autogenerate on an unchanged model =     |
    |        | proposes NO drops (empty diff on clean model)  | (dry run)                       | empty upgrade()/downgrade()              |
    +--------+------------------------------------------------+---------------------------------+------------------------------------------+
    | AE.3   | doc: AllEntities docstring + spec §7/§8 point   | -model AllEntities.py;          | docstring/spec say "enforced by          |
    |        | to the guard test (not a plea to remember)     | this spec §7/§8                 | test_all_entities_complete", not "EVERY" |
    +--------+------------------------------------------------+---------------------------------+------------------------------------------+
    | AE.4   | completeness guard test — curated-import-then- | -model tests/ (or spectracsPy   | red with the missing table name if any   |
    |        | walk oracle; assert declared == actual (both   | tests/) test_all_entities_      | DbBaseEntity/ServerDbBaseEntity entity   |
    |        | metadatas); the self-enforcing mechanism       | complete.py                     | is absent from AllEntities               |
    +--------+------------------------------------------------+---------------------------------+------------------------------------------+

**Settled decisions:** D-baseline-complete = **NO** (leave migration history; guarded init shields it). The AE set is
`AllEntities` + one guard test — no runtime auto-import, no baseline retrofit. AE.3 references the test AE.4 defines
(one coherent set). Impl on explicit request.
