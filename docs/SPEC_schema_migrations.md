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
- **Baselines** autogenerated: server rev `f641f17a1539` (15 tables), app rev `7200faf1d770` (2 tables).
- **`authorMigration.sh`** (app repo) — the dev author helper. Deps `alembic` + `PyNaCl` added to `requirements.txt`.
- **Proven:** the calibration `OperationalError` is gone (fresh at-head DB); and an existing DB at baseline `f641`
  **upgraded to `405d2ce2cec1`** (the B0/B1 migration), gaining 5 columns — the evolve `create_all` could never do.

## Verification (met)

1. ✅ Adding columns (B1) + a migration → an **existing** dev DB gained them after `upgrade head` (f641 → 405d).
2. ✅ A fresh empty DB comes up fully at `head` (create_all + stamp head).
3. ✅ Both DBs migrate independently, each tracking its own `alembic_version`.
