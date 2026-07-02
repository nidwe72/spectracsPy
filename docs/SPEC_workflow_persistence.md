# SPEC — Workflow-record persistence + view saved runs  (Option A: the workflow IS the record)

> **Status:** DESIGN (spec-first; implement on explicit request only). **Captured:** 2026-07-02.
> Follows the pumpkin integration milestone (`SPEC_pumpkin_integration.md`, IMPLEMENTED) — makes the
> wizard's **Save** actually persist a run, and lets the user **browse + reopen** saved runs.
>
> **Direction (Edwin): Option A — realise concept §9.5.** The runtime `model/spectral/` classes **become the
> SQLAlchemy entities** (one class is *both* the runtime object and the DB row). **No separate `Db*` twins.**
> This makes `workflow_object_model.puml` (which already marks these `<<persisted>>`) and the DB model agree.
> *(This supersedes the earlier "lightweight `DbMeasurement`/`DbSpectrum`" draft — dropped.)*

## 1. Goal & shape

The wizard ends on **Save** (currently a no-op → Home). This spec makes Save **persist the `SpectralWorkflow`
graph** to the app DB, and adds a **per-user saved-runs list + read-only detail view**. Reopening a saved
run re-hydrates the same `SpectralWorkflow` object graph and re-renders it.

```
 view saved runs  =  list SpectralWorkflow rows (per user)
 open one         =  load the SpectralWorkflow graph  →  render its EVALUATION result + its spectra
```

## 2. Promote `model/spectral/` to entities  (APP DB, `DbBaseEntity + DbBaseEntityMixin`)

The run is client-side → the app DB (`spectracsPy.db`), like `SpectrometerProfile`. Each class gains
`id : String (uuid)` from the mixin and relationships replace the hand-rolled dict/list fields.

```
SpectralWorkflow        → table "spectral_workflow"          THE RECORD ROOT
    id, username, userId, pluginCodeRef, timestampIso        ← run metadata, stamped at Save (§2.1)
    phases        : relationship -> [SpectralWorkflowPhase]  (dict keyed by phaseType via
                                                              attribute_mapped_collection('type'))
    metadataFields: relationship -> [SpectralWorkflowMetadata]  ← plugin-declared rows (§2.3)
                                                              ⚠ NOT `metadata` — SQLAlchemy-reserved name
    currentPhase : TRANSIENT (not mapped)

SpectralWorkflowMetadata → table "spectral_workflow_metadata"   generic (EAV) metadata field row
    id, workflowId (FK)
    name       : str        ' field key, e.g. "title" | "temperature" | "dateOfRoasting"
    label      : str        ' display label (self-describing — plugin-declared, denormalized onto the row)
    type       : str        ' TEXT | NUMBER | DATE (drives the form widget + value cast)
    value      : str        ' stored as string (DATE = ISO yyyy-mm-dd); cast by `type` on render/sort
    showInWorkflowsTable : Boolean    ' plugin flag -> this field appears as a column in the Home list
    order      : Integer    ' form order

SpectralWorkflowPhase   → table "spectral_workflow_phase"
    id, workflowId (FK), type
    steps   : relationship -> [SpectralWorkflowStep]

SpectralWorkflowStep    → table "spectral_workflow_step"
    id, phaseId (FK), role, label, frames, mandatory, persist
    container        : relationship -> SpectraContainer? (0..1, cascade)
    evaluationResult : relationship -> EvaluationResult?  (0..1, cascade)
    view, widget     : TRANSIENT (host-built, never mapped)

SpectraContainer        → table "spectra_container"
    id, stepId (FK = producedBy)
    spectra : relationship -> [Spectrum]  (dict keyed by role via attribute_mapped_collection('role'))
    inputs  : self-ref link -> [SpectraContainer]   (provenance; OPTIONAL — §5 A3, may defer)

Spectrum                → table "spectrum"
    id, containerId (FK), role, sampleType
    valuesJson : Column(String)   ← the {nm: value} map, via Spectrum.toJson()/fromJson()  (§3)
    capturedValuesByNanometers, colorsByPixelIndices : TRANSIENT (the ~N-frame burst is NOT persisted)

EvaluationResult        → table "evaluation_result"
    id, stepId (FK)
    resultJson : Column(String)   ← the view-models, via EvaluationResult.toJson()/fromJson()  (§3)
    items (ColorSwatchView/VerdictView/LabelView) : TRANSIENT render specs, rebuilt from resultJson
```

- **Why a JSON column inside entities (not a spectra-values table):** even under A, a `Spectrum`'s values are
  a variable-length `{nm: value}` **map** — a `spectrum_value` row-per-nm table is thousands of rows for no
  query benefit. So the **structure** is entities (workflow→phase→step→container→spectrum) and the **leaf
  content** (the nm→value map, the view-model list) is a JSON column *on* its entity. This matches
  `workflow_object_model` (Spectrum / EvaluationResult are `<<persisted>>` — entities — with JSON payloads).
- **Cleanup:** delete BOTH dead stubs — `DbSpectrum` (`class DbSpectrum(): pass`) *and* `MeasurementProfile`.
  Under A, `Spectrum` **is** the entity, so no `DbSpectrum` is needed.
- **Persist util:** new `logic/persistence/database/spectral/PersistSpectralWorkflowLogicModule.py` (mirrors
  `PersistSpectrometerProfileLogicModule`): `save(workflow)` = `session.add(workflow); commit` (cascade
  persists the whole reachable graph); **`listForUser(userId)`** (ordered by `timestampIso` desc);
  `findById(id)` (eager-loads the graph). Import the entities before `create_all`.

### 2.1 Run metadata is stamped at Save; the Home list is per-user
The runtime `SpectralWorkflow` gains `username`/`userId`/`pluginCodeRef`/`timestampIso`, **stamped at Save**
from `CurrentUserSession` + `datetime.now()`. **The Home saved-runs list shows only the current user's runs**
(Edwin) — `listForUser(CurrentUserSession().userId)`. `userId` is the stable filter key (survives a rename).
This realises §9.5's "the workflow gains a User."

### 2.2 The one real cost — ORM-converting live classes (rubber-duck verified: a DEEP refactor)
Feasibility rubber-duck (2026-07-02) verdict: **feasible, no hard blockers, but a deep first-in-repo
refactor** — these would be the repo's first "rich domain object = ORM row" (all existing entities are thin
data holders with no custom `__init__`, no behaviour, no dict collections, no JSON blobs).

**🔴 PREREQUISITE (biggest risk) — the session strategy must change BEFORE A.** The app uses one
process-wide **singleton session with `autoflush=True`** (`DbBase.py:24,57-63`). Today the run path opens no
session, so the engine's transient graph is safe *by accident*. Once these classes are mapped **and**
`save()` does `session.add(workflow)`, the default `save-update` cascade + shared session + autoflush means a
**half-built or intentionally-transient object can be flushed by any unrelated query anywhere** (e.g. a
device profile lookup). **Fix first:** persist on a **short-lived / per-save `Session` with `autoflush=False`
and explicit cascade** — not the shared singleton. (De-risker: `SpectrometerProfile` is already a mapped
entity created transiently at runtime and held without a session — proof the pattern works.)

**The mechanical 80% (precedented):** drop private fields + custom `__init__`, declare `Column`/string
`relationship("...")` (bare, not `Mapped[...]` — the cyclic classes have import fallbacks), repoint getters
(the `ApplicationConfig` getter-over-relationship is the template), dict-keyed collections via
`attribute_keyed_dict('type'|'role'|'id')` so `getPhase(type)`/`getSpectra()[role]` survive.

**The hard 20% (each first-in-repo, no template):**
- **`@reconstructor`** to re-init the transient lists (`capturedValuesByNanometers`, …) after the custom
  `__init__` is stripped — else the class-level mutable-default sharing bug returns.
- **`valuesByNanometers` as a JSON property-over-column** (`_valuesJson = Column(Text)` + a `@property`) so
  direct `.valuesByNanometers` access across the codebase keeps working.
- **ADD a `role` column to `Spectrum`** — it has none today; `role` is only the container's external dict
  key. `attribute_keyed_dict('role')` needs it mapped, and `addToSpectra` must write it. *(A model change
  forced purely by persistence.)*
- **Dual disambiguated FKs** `Step↔Container` (both `step.container` and `container.producedBy`) + the
  **self-ref `Container.inputs`** — need explicit `foreign_keys=`/`primaryjoin`; a `configure_mappers()` at
  startup becomes effectively mandatory.
- **Polymorphic `EvaluationResult` items**, one of which (`SpectrumPlotView`) embeds a `Spectrum` → its
  `resultJson` must inline that spectrum's values (keep it self-contained; don't cross-reference a Spectrum row).

### 2.3 METADATA — a plugin-declared generic field table (Edwin)
METADATA is no longer skipped: the **plugin declares its metadata fields** — each with a **type, a label, and
a `showInWorkflowsTable` flag** — and they are **editable both at creation (in the wizard) and on view/edit**.
- The plugin's `metadata(workflow)` hook **returns a `list[MetadataField]`** — a new Qt-free `plugin_sdk`
  declaration type `MetadataField{name, label, type, showInWorkflowsTable, order}` (mirrors `MeasurementStep`). *(This
  is the one hook that DESCRIBES fields rather than mutating the workflow — decided contract.)*
- **Pumpkin fields (Edwin, for now)** — the plugin declares `showInWorkflowsTable`:
  | name | label | type | showInWorkflowsTable |
  |---|---|---|---|
  | `title` | Title | TEXT | ✅ (Home column) |
  | `temperature` | Roasting temperature (°C) | NUMBER | — |
  | `dateOfRoasting` | Date of roasting | DATE | — |
  Only `title` surfaces as a Home-list column (plugin-declared). Widgets: TEXT→`QLineEdit`, NUMBER→validated
  `QLineEdit`/spinbox, DATE→`QDateEdit` (ISO `value`).
- Values persist as **`SpectralWorkflowMetadata` rows** (generic/EAV, §2), one per field — **not** a JSON blob
  and **not** fixed columns, so a plugin can add fields freely. Each row is **self-describing** (label/type/
  showInWorkflowsTable copied onto it).
- **Self-describing ⇒ view/edit needs NO plugin.** At *creation* the wizard builds the form from the plugin's
  `MetadataField`s; on *reopen* it builds the same form from the loaded rows — a saved run renders + edits even
  if the plugin later changes or is absent. The plugin is consulted only at creation.
- **`showInWorkflowsTable=True` → the field becomes a column in the Home list** (e.g. `title`). Sortable/filterable is
  deferred, but the `QTableView` model is built data-driven (§6) so it lands later without rework.
- Editing metadata later = a **targeted UPDATE of the affected `SpectralWorkflowMetadata` rows** on the
  short-lived session (§2.2 PRE) — NOT `session.merge` of the whole workflow (which would re-serialise spectra).
- ⚠ **Reserved-name (biggest metadata risk):** the parent relationship must be `metadataFields` (or similar) —
  **`metadata` is reserved** on a SQLAlchemy declarative class and raises at import.

## 3. Serialization — owned by the model object (the float-key gotcha)

Leaf content is JSON on its entity; the **object owns its own (de)serialization**:
```python
# Spectrum
def toJson(self):        return { str(nm): v for nm, v in self.valuesByNanometers.items() }
def fromJson(self, obj): self.valuesByNanometers = { float(k): v for k, v in obj.items() }; return self
# valuesJson column <-> toJson()/fromJson()  (hook via a property or in the persist/reconstruct step)
```
- **⚠ FLOAT-KEY GOTCHA (biggest risk).** nm keys are `numpy.float64`; JSON emits **string** keys and on
  reload they stay strings → `SpectrumPlotWidget` does `sorted(keys())` → lexicographic → a **silently
  garbled plot, no exception**. **Mandatory:** `{str(nm): v}` out, `{float(k): v}` in; `fromJson` also
  assigns a real **dict** (the `__init__` sets it to a list). Covered by a round-trip test.
- **`EvaluationResult.toJson()/fromJson()`** ↔ `resultJson`; **`VerdictView` carries `hueDegrees`** so hue is
  a real field (not a `"hue 60°"` string). The saved-runs list reads verdict/hue off the deserialised
  `VerdictView`. `PumpkinOilPlugin.evaluation` sets `VerdictView(roast.value, hueDegrees=hue)` (it already
  computes `hue`).

## 4. Save flow

Hook point: `WizardViewModule.onClickedNext` — the terminal branch currently `self.__goHome()  # Save`. On
Save (NOT Cancel): read the filled METADATA form → `workflow.metadataJson`; stamp
`username`/`userId`/`pluginCodeRef`/`timestampIso`; call `PersistSpectralWorkflowLogicModule().save(workflow)`,
then Home. **No serializer/gather step** — the graph is already the entity graph; cascade persists it.
- **Persist on a short-lived session** (`autoflush=False`, explicit `cascade`), NOT the shared singleton (§2.2
  prerequisite) — so only the deliberately-`add()`-ed workflow graph flushes.
- `PersistSpectralWorkflowLogicModule` provides `save(workflow)` · `listForUser(userId)` · `findById(id)` ·
  **`update(workflow)`** (targeted metadataJson update) · **`delete(id)`** (cascade), with an ownership guard
  on update/delete.

## 5. Rubber-duck status — DONE (2026-07-02)

Two feasibility passes ran (ORM conversion + edit/delete). Findings folded into §2.2 (deep refactor + the
session prerequisite), §2.3 (metadata form), and §6 (view = the wizard in read-only mode; delete). Carried
base findings still live: **R1** float-key gotcha (§3, biggest correctness risk); **R2** `Spectrum.__init__`
list default → `fromJson` assigns a dict; **R4** `SpectralJobsOverviewViewModule` is a dead `QLabel` stub →
replace (§6); **R6** `EvaluationResultRenderer`'s `SpectrumPlotView` branch is text-only + curves live outside
the EvaluationResult → the view plots spectra itself via `SpectrumPlotWidget`. Edit/delete: the editable-form
(`UserViewModule`), delete-with-confirm (`UserListViewModule`), and all persist primitives (`add`/`merge`/
`query…delete`) are proven in-tree; **the codebase hand-deletes children (zero `cascade=`)** — but per Edwin
we add `cascade="all, delete-orphan"` on the new relationships (§6).

## 6. View / edit a saved run  (it IS the wizard, in read-only mode — Edwin)

**Not a separate page — reuse `WizardViewModule` in a VIEW/EDIT mode.** The wizard already renders the
acquisition/processing/evaluation tabs; opened on a saved run it **loads the persisted `SpectralWorkflow`
(`findById`) instead of running the engine**, and makes everything read-only **except the METADATA form**:

- **List (Home):** replace `SpectralJobsOverviewViewModule` (dead `QLabel` stub) with a real `QTableView`
  (mirror `UserListViewModule`), `listForUser(currentUserId)`, newest-first. Columns = **Date · Verdict ·
  Hue** (from the EVALUATION `EvaluationResult`) **+ one column per `showInWorkflowsTable` metadata field** (§2.3).
  ⚠ The `UsersTableModel` hardcodes columns — the new model must be **data-driven**: an instance column list
  `[Date,Verdict,Hue] + union(showInWorkflowsTable names across the listed workflows)`; missing field → blank cell.
  `listForUser` must **eager-load** the `SpectralWorkflowMetadata` (join / `selectinload`) to avoid N+1 and to
  build the union. Design `data()` to expose a **typed sort role** now (so the deferred numeric sort/filter
  drops in). Row click → open the wizard in VIEW mode for that id.
- **Wizard VIEW/EDIT mode:** a `mode` flag on `WizardViewModule`. In VIEW mode: no engine run; **Measure /
  Next-as-advance / Save-run are read-only/absent**; the result swatches + verdict and every spectrum plot
  render read-only; the **METADATA phase stays editable** (§2.3). Nav buttons become **Back · Cancel · Save
  changes (metadata) · Delete** (`Save changes` on the terminal phase; a targeted `update(metadataJson)` — not
  `merge`). *(As-built §10: METADATA is its **own terminal wizard phase**, not an EVALUATION tab.)*
- **Delete:** mirror `UserListViewModule`'s confirm dialog (`QMessageBox.question`, "cannot be undone");
  `delete(workflowId)` cascade-deletes the graph via `cascade="all, delete-orphan"`. An **ownership guard**
  (`workflow.userId == CurrentUserSession().userId`) gates `update`/`delete` (the list is already per-user;
  the guard is defence-in-depth). Reachable from the wizard VIEW mode (and optionally a per-row trash).
- **After Save (new run) → Home** (per-user list, new run on top). After a metadata Save-changes or Delete →
  Home (refreshed).

*(Metadata is thus editable in BOTH flows through the one wizard: at creation the METADATA phase is filled
before Save; on reopen the same phase is editable and Save-changes updates it.)*

## 7. Test plan

- `Spectrum.toJson`/`fromJson` round-trip: reload yields **float** nm keys in a **dict**, values within
  tolerance (R1/R2 guard).
- `EvaluationResult.toJson`/`fromJson`: swatch rgb, verdict, `VerdictView.hueDegrees` survive.
- `PersistSpectralWorkflowLogicModule`: `save(workflow)` persists the graph; `listForUser` returns only that
  user's runs newest-first; `findById` re-hydrates phases→steps→containers→spectra + evaluationResult.
- Headless E2E: run the pumpkin workflow (existing E2E), fill metadata, stamp + `save` (on a short-lived
  session), reload by id, re-render offscreen → verdict + spectra + metadata match. Assert **no
  transient/intermediate spectra leaked** into the DB (only the container-attached ones persist).
- `update(metadataJson)` changes only the two fields (spectra JSON untouched); `delete(id)` removes the whole
  graph (no orphaned phase/step/container/spectrum/evaluation rows); ownership guard rejects a foreign userId.
- Offscreen: Home list shows the saved row; opening it in the wizard VIEW mode renders read-only swatches +
  non-empty spectrum plots + an editable METADATA tab; `Save changes` + `Delete` behave.

## 8. Decisions locked (veto)

- **A** the workflow IS the record — promote `model/spectral/` to entities; no `Db*` twins (Edwin, reaffirmed
  after the "deep refactor" rubber-duck).
- **PRE** persist on a **short-lived session** (`autoflush=False` + explicit cascade), not the shared
  singleton — §2.2 prerequisite, must land first.
- **P1** structure = entities, leaf maps = JSON columns (Spectrum.valuesJson, EvaluationResult.resultJson) ·
  **P2** app DB · **P3** `save(workflow)` cascade-persists the finished graph; transients never mapped/flushed
  · **P4** stamp username/userId/pluginCodeRef/timestampIso at Save; Home list **per-user** · **P5**
  `str(nm)`/`float(k)` on `Spectrum.toJson/fromJson`, tested · **P6** the Home list replaces the dead overview;
  **view/edit reuses `WizardViewModule` in a read-only mode**, NOT a separate page (Edwin) · **P7** delete both
  dead stubs (`DbSpectrum` + `MeasurementProfile`) · **P8** verdict/hue inside `EvaluationResult.resultJson`
  via `VerdictView.hueDegrees` · **P9** add a `role` column to `Spectrum` (forced by the keyed collection).
- **METADATA** (Edwin): **plugin-declared generic field table** `SpectralWorkflowMetadata` (name/label/type/
  value/showInWorkflowsTable), editable at creation AND on view/edit; `showInWorkflowsTable` fields become **Home-list columns**
  (sortable/filterable later); edit = targeted UPDATE of the affected rows. Hook contract: `metadata()`
  **returns `list[MetadataField]`** (new `plugin_sdk` type); rows are **self-describing** so view/edit needs no
  plugin. ⚠ parent relationship named **`metadataFields`** (`metadata` is SQLAlchemy-reserved). Home list model
  is **data-driven** (union columns + blanks) and `listForUser` **eager-loads** metadata.
- **Delete** = `cascade="all, delete-orphan"` on the new relationships (Edwin) + confirm dialog + ownership
  guard. **After Save/edit/delete → Home.**

**No open questions — spec is final + buildable** (build order: the §2.2 session fix → the ORM conversion →
persist util → wizard VIEW mode + Home list + metadata + delete).

## 9. Out of scope (later)
- PUBLISHING (PDF/email) — separate spec.
- Re-DRIVING a saved run (continuing a reopened workflow) — we persist + view/edit; re-execution is future.
- `SpectraContainer.inputs` provenance links — persist later if needed; not required to view a run.
- Server-side sync / multi-device history; migration tooling for schema changes.

## 10. As-built — implemented + polished (2026-07-02)

Shipped as specced (§8 decisions all hold: Option A entities, short-lived save session, EAV metadata,
data-driven Home table, wizard VIEW mode, cascade delete + ownership guard). Deltas folded in from Edwin's
click-through review:

- **METADATA is its own terminal wizard phase**, *not* a step/tab of EVALUATION (Edwin). The wizard phase
  sequence is `ACQUISITION › PROCESSING › EVALUATION › METADATA` (METADATA appended only when the plugin
  declares fields). It renders a metadata form (TEXT `QLineEdit`, NUMBER, DATE `QDateEdit` with
  `setCalendarPopup(True)`); on the terminal phase Next becomes **Save** (new) / **Save changes** (view).
- **Chevron phase indicator** — a generic `StepBarWidget` (`view/application/widgets/`, see DESIGN_GUIDE §4b)
  replaces the old text rail: all phases visible at once, current in primary, inactive in secondary gray. The
  wizard shows the **full** sequence and highlights the current phase per render.
- **Wizard nav** — **Cancel** is a `secondary` button, confirmed via `QMessageBox`, present in **both** modes;
  **Delete** (confirmed) is **VIEW-only**. Back/Next(Save) as specced.
- **Home** — Edit / Delete buttons sit in the Home nav row right of *New measurement*
  (`[New measurement][Edit][Delete][Settings]`) and act on the selected workflows-table row (Delete confirmed,
  ownership-guarded). Double-click a row opens VIEW mode.
- **Workflows table styling** (shared QSS, benefits every table; DESIGN_GUIDE §4) — vertical header hidden;
  columns `QHeaderView.Stretch` (even, edge-to-edge — no ballooned last column); header band on `surfaceAlt`
  bold; framed `QTableView` + header sections drawing only right/bottom 1px separators so header dividers align
  pixel-for-pixel with the body gridlines.
- **Tests** — `test_workflow_persistence.py` (headless save/reload/update/delete), plus offscreen
  `test_workflow_wizard_persistence_offscreen.py`, `test_pumpkin_wizard_offscreen.py`,
  `test_step_bar_widget_offscreen.py`. Full suite green (41).
