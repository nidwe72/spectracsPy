# SPEC — Pumpkin-oil integration (Tracks A / B / C)

> **Status: IMPLEMENTED 2026-07-02** (Tracks A + B + C; 37 tests green). **Supersedes** the wording of
> ROADMAP #5 and #6 with a single, buildable integration milestone that carries the *proven* playground
> pipeline into a **real, user-drivable plugin** running on the **virtual spectrometer**.
>
> **As-built summary** (deviations from the design below are noted inline where they occurred):
> - **Track A** — `SpectraContainer` §9.2 fix · `VirtualSpectrometerSettings` 3-slot role map + `activeRole`
>   + legacy shim · `SpectrumToVirtualImageUtil` (shared-vmax, linear) · `VirtualSpectrometerViewModule`
>   folder picker · baked demo sets in `spectracs-references/pumpkin_oil/virtual_captures/`. Round-trip test.
> - **Track B** — server-side `DbPlugin` + `AppUser.pluginId` FK + `spectrometerDevice` · seed
>   `pumpkinTestUser`/`pumpkinTestUser` bound to the pumpkin plugin + `Virtuax` · `plugin_sdk` façade
>   (container→container op adapters, `SpectralPlugin`/`MeasurementStep`, `EvaluationColorUtil`, `VerdictOp`)
>   · Qt-free `EvaluationResult` + view-models.
> - **Track C** — `SpectralWorkflowEngine` (5-phase spine, headless capture seam, **auto-calibrates from the
>   loaded `calibration.png`**) · `PumpkinOilPlugin` · **interactive** `WizardViewModule` (per-step **Measure**
>   button + real pyqtgraph spectrum plots; PROCESSING absorption curve; EVALUATION swatches+verdict;
>   Back/Cancel/Next→Save) · `EvaluationResultRenderer` · login carries `pluginCodeRef` and navigates to the
>   wizard · Home "New measurement" redirects to the wizard for a plugin-bound user.
> - **Tests:** `test_virtual_device_image_roundtrip`, `test_plugin_binding_and_seed`, `test_plugin_sdk_ops`,
>   `test_pumpkin_workflow_end_to_end` (headless), `test_pumpkin_wizard_offscreen` (GUI, offscreen).
> - **Known limits / follow-ups:** wizard not yet clicked through on a real display by a human;
>   re-measuring after downstream phases computed does not recompute (deterministic virtual capture);
>   workflow-**record** persistence still deferred (Save is a no-op → Home); adding `AppUser` columns needs a
>   fresh/migrated `spectracsPyServer.db` (SQLite `create_all` won't ALTER); legacy `SpectralJob` flow kept.
>
> **Companion docs:** `SPECTRAL_WORKFLOW_CONCEPT.md` (§9 object model, §10 SDK — the normative design),
> `SPEC_pipeline_playground.md` (the pipeline this integrates), `SPEC_spectrum_processing.md`
> (`SpectrumUtil`), `DESIGN_GUIDE.md` (UI conventions), `DB_ENTITIES.md` (app-DB entities; note the new
> `DbPlugin` lives **server-side** with `AppUser`, not here — D7).
>
> **What is already proven** (do NOT re-derive): synthesis → `T = S/R` → colour → verdict, end-to-end on
> synthetic data, in `PlaygroundViewModule` + `tests/test_pumpkin_oil_spectrum_to_color_eval.py`. This spec
> does **not** touch that math — it wires it through the virtual device + the workflow spine + a plugin.

---

## 0. The floor goal (acceptance target)

```
 (a) user drops 3 images        (b) the pumpkin plugin drives      (c) evaluation renders
     into the virtual device        the user through the phases         colour + verdict
     ┌───────────┐              ACQUISITION → PROCESSING → EVALUATION   ┌──────────────────┐
     │ CALIB.png │  ─ measure ─▶  ref+sample  ─▶  absorption  ─▶  hue ─▶│ ███ measured     │
     │ REF.png   │                spectra          plot            ↓    │ ▓▓▓ target       │
     │ SAMPLE.png│                                            verdict   │ "PERFECT ROAST"  │
     └───────────┘                                                      └──────────────────┘
```

**Done when:** a headless integration test drives a `PumpkinOilPlugin` through the real `SpectralWorkflow`
spine, sourcing frames from the **virtual device** (rasterised REFERENCE/SAMPLE strips), and produces an
`EvaluationResult` whose verdict matches the synthesised oil's roast state — *and* the same run renders in
the GUI as a nested wizard ending on the colour/verdict tab.

## 0.1 Decisions locked for this milestone (veto if wrong)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **5-phase spine kept**; `METADATA` + `PUBLISHING` are **skipped** (empty hooks → zero steps → no tab). | Honours "discard PDF/email for now" without amputating the spine (§9.1 auto-skip). No rework to re-enable. |
| D2 | **Workflow-*record* persistence deferred** — the run's spectra/steps stay **in-memory**. But the **CONFIG binding IS persisted + seeded** (D3). | The floor goal is *drive + render*, not *save the run*. Promoting `model/spectral/` to SQLAlchemy (concept §9.5) is a named follow-up; the *configuration* (who runs what) must be real. |
| D3 | **Config binding IN SCOPE + seeded** (Edwin, 2026-07-02): create the `DbPlugin` row for the pumpkin plugin, add the `AppUser → {SpectrometerProfile, Plugin}` links, and **seed a demo user** bound to the virtual profile + pumpkin plugin. The host resolves the plugin **via the logged-in user's binding**, not hard-coded. Pulls ROADMAP #3's *binding* portion into this milestone. | Edwin: the binding "should be implemented and seeded." The plugin must be run *because a user is configured to run it*, end-to-end. |
| D4 | Virtual device is the **only** acquisition source; no live camera path changes. | Matches "virtual devices first"; the read-back path already exists. |
| D5 | The `DbPlugin` row is created + **seeded** (title + code-ref + version + pdf-ref) but **not yet signature-verified or hot-loaded** — the host imports the plugin class by its `codeRef`. | The row is the real config seed for §11 trust work; execution stays first-party-trusted/in-repo. |

---

## 0.2 Rubber-duck findings (2026-07-02) — corrections, blockers, decisions

> Three per-track reviewers pressure-tested the tracks below against the real code. The **pipeline math and
> the overall structure hold**; the corrections here **supersede** any conflicting inline wording. Grouped:
> (X) cross-cutting blockers needing an Edwin decision, (P) applied corrections, (Q) smaller decisions.

### X — Blockers (all RESOLVED 2026-07-02)

- **X1 / D7 — Cross-database binding → RESOLVED: (a) server-side.** `AppUser` lives in the **server DB**
  (`spectracsPyServer.db`, `ServerDbBaseEntity`, seeded server-side by `UserSeedLogicModule`, over Pyro);
  `SpectrometerProfile` lives in the **app DB** (`spectracsPy.db`). Cross-DB FKs are impossible.
  **DECISION (Edwin): `AppUser`, `DbPlugin`, and the binding references ALL live on the Pyro/server side.**
  So `DbPlugin` is a **server-DB** entity; `AppUser` gets a real `pluginId` **FK → server `DbPlugin`**, and a
  **`spectrometerProfileId` soft-id string** (the app-DB profile is fetched by id **client-side after
  login** — matching concept §9.5 "login downloads profile + plugin"). Seeding is single-process (the
  server seeder). See B.1 / B.1a (rewritten for server-side).
- **X2 — Headless run vs the Qt capture thread (Track C, C.1/C.4).** `SpectrumVideoThread` uses a Qt queued
  `Signal` + `event.wait()` that **deadlocks with no `QApplication` event loop**. So C.1 "capture through
  VideoThread" and C.4 "headless" are **mutually exclusive**. **DECISION D8 (resolved, recommend):** the
  engine gets a **headless capture seam** that calls `ImageSpectrumAcquisitionLogicModule().execute(...)`
  **directly** (constructing a `SpectralVideoThreadSignal(image=…)`); `VideoThread`/`SpectrumVideoThread`
  stay the **GUI-only** driver. C.4 exercises the **real encode→decode** via that direct call — that is the
  whole point of Track A — not the synthetic shortcut the old playground test used.
- **X3 — No wizard / "Next advances a phase" concept exists (Track C, C.3).** `NavigationSignal` is a
  **page-by-name router** into a `QStackedWidget` (`NavigationHandlerLogicModule`); it switches whole pages,
  it does **not** advance state within a page. The spec's "Next triggers the engine via `NavigationSignal`"
  is a category error. **DECISION D9 (resolved, recommend):** the phase-advance **Next** is a **new
  page-local button + handler** owned by the wizard page/engine (holds the current-phase pointer), entirely
  separate from the `NavigationSignal` page router. The outer "phase rail" is one page with an inner
  `QTabWidget`, not N stacked pages.

### P — Corrections applied (supersede the inline track text)

- **P-A0 (`SpectraContainer` shape).** The surviving `__init__` fields are `__spectra: Dict`,
  `__spectraContainers: Dict`, `__sourceSpectraContainer` (scalar), `__workflowStep` — **not** the §9.2
  `spectra / inputs:List / producedBy`. A.0 is therefore a **rename + restructure of the fields and all
  getters/setters** (and `inputs` List ≠ the existing Dict+scalar), not "delete a dup line." The class is
  currently **dead code** (no importers), so the migration is low-risk but real. **Commit to the §9.2
  names** (settle before B.2's adapters — Q4/D10).
- **P-B1 (`DbPlugin` pk).** The entity pk is a **String UUID** (`DbBaseEntityMixin`), not `int`. Any FK to
  it is `String`. Table creation depends on the module being **imported before `create_all()`** — there is
  no registration list; ensure an import path pulls `DbPlugin` in.
- **P-B1a (relations home).** `DbRelations.py` is a **dead, non-compiling stub** — do **not** add relations
  there. The real convention is **inline in the entity**: `Column(String, ForeignKey("x.id"))` +
  `relationship("X")`. There is **no `AppUserSchema`** to extend (users move over Pyro), and the "predefined
  spectrometer seeder" analogy is false (that's a lazy get-or-create util, not a startup seeder) — the real
  seeder to mirror is server-side `UserSeedLogicModule.SEED_USERS`.
- **P-B2 (ops are `Spectrum`-based).** Every logic module takes `…Parameters(Spectrum)` → `…Result(Spectrum)`
  — **none** touch `SpectraContainer`. The `container → container` ops are **real adapters** (build params,
  pull the right `Spectrum` from a bag, run, write a result bag), not "thin wrappers." Also the module is
  **`NormalizeSpectrumLogicModule`** (no `NormalizeSpectrum`); baseline is `SpectrumUtil.removeBaseline`
  (no standalone `BaselineOp`).
- **P-B3/B4 (Qt-free boundary).** `SpectralColorUtil` **imports PySide6 and returns `QColor`** and lives in
  the **logic** repo — re-exporting it from `plugin_sdk` **breaks the Qt-free rule**. Fix: the plugin gets
  hue/`RoastState` (Qt-free); the **measured colour is converted `QColor → (r,g,b)` at a boundary** and
  `EvaluationResult`/view-models carry **plain RGB**. Keep `SpectralColorUtil` **out** of `plugin_sdk`.
  Likewise `SpectralWorkflowStep.widget` must be **untyped/`Any`** (a `QWidget` hint drags Qt into the model
  repo), and `EvaluationResult` (model) needing `RoastState` (logic) is a **dependency inversion** — move
  `RoastState` to the model layer (or carry the verdict as a plain enum/string).
- **P-B4b (phase enum = ADD, not replace).** Adding the 5 canonical values is non-breaking; **replacing**
  the legacy `ACQUIREMENT_VIEW`/`ACQUIREMENT` breaks `SpectralWorkflow.getAcquireViewPhase()` +
  `SpectralJobViewModule`. **Keep both this milestone**, retire legacy only after C.1 lands.
- **P-C2 (hue seam).** Use `SpectrumToColorLogicModule().spectrumToColor(params).getHue()` (**degrees**) —
  already fixed inline in C.2. `AbsorptionLogicModule` recomputes T internally, so keep the T spectrum from
  the `TransmissionOp` call for the colour step.
- **P-A2 (encoder reality).** The forward renderer (`renderStripArray`) and the reader are **not mirror
  images** — the renderer is cosmetic/lossy and has never been round-tripped. The A.2 encoder is **new
  code**. `Spectrum` has **no `value_at`/interpolation** (only a `{nm:value}` dict, and synth spectra are on
  an **integer-nm** grid) — the encoder needs a real resampling helper. ROI is stored **inverted**
  (`Y1 > Y2`) → paint `range(min,max)`, not `[y1..y2)`. The reader pulls the calibration profile from a
  **global singleton** (`ApplicationContextLogicModule`), not a parameter — the round-trip test must
  **install** the playground profile into app context + build a `SpectralVideoThreadSignal`.

### Q — Smaller decisions (all RESOLVED 2026-07-02)

- **Q4/D10 — `SpectraContainer` shape → §9.2.** Commit to `spectra{role→Spectrum}` + `inputs:[Container]`
  (generic **source**/provenance) + `producedBy:Step` (**owner**), and migrate the getters, *before* the B.2
  adapters. Low-risk (class is dead code).
- **Q2/D11 — encoder normalisation → SHARED white-point.** One `vmax` across the REFERENCE and SAMPLE
  strips. Rationale (Edwin): this **mirrors the physical capture** — the same camera + same light source
  shoot both, so they share one absolute intensity scale; the synthetic encoder must emulate that. (Hue is
  scale-invariant regardless, but a shared `vmax` also keeps the `A(λ)` plot magnitude truthful.)
- **Q3/D12 — resampling → LINEAR + ±3° tolerance.** The encoder interpolates `nm→value` **linearly** onto
  the integer-nm grid. The A.3 round-trip assert passes when the recovered **hue is within ±3°** of the
  source hue (tight enough to absorb 8-bit rounding, tight enough that quantisation can't flip a verdict at
  the 47/66° bands).
- **Q5/D13 — file format → PNG-only** in the 3-image picker (lossless; JPEG breaks the exact gray
  round-trip).
- **Q1/D14 — virtual selection is TWO independent levels.** (1) **`isVirtual`** already exists —
  a `Boolean` on `SpectrometerSensor` (the predefined "VIRTUAX" device has `isVirtual=True`), flowed into
  `VideoThread.setIsVirtual`; selecting the virtual device as the profile is the **user-facing** "use the
  virtual spectrometer" switch → **unchanged**. (2) **`activeRole`** is **new + internal**: with 3 stored
  images, the engine sets `activeRole ∈ {CALIBRATION,REFERENCE,SAMPLE}` before each capture and the shim
  `getVirtualCameraImage()` returns `images[activeRole]`. Captures are **serialised** (one logical slot at a
  time). Default when unset = last-set image, so the legacy single-image virtual path still works.

---

# TRACK A — Virtual device image round-trip

> **Goal:** the virtual spectrometer holds **three** images and, fed a rasterised REFERENCE/SAMPLE strip,
> the *existing* acquisition path reads back the **same spectra** the playground synthesised.
> **Nature:** mostly wiring — the forward renderer and the reverse reader already exist and are mirror
> images of each other.

## A.0 Foundational fix — `SpectraContainer` duplicate `__init__` (→ §9.2 shape, D10)
`model/spectral/SpectraContainer.py` defines `__init__` **twice**; the second (`self.spectraBySampleTypes
= {}`) shadows the first, so the named-bag fields never initialise. The surviving first `__init__` uses the
**old** private fields (`__spectra` Dict, `__spectraContainers` Dict, `__sourceSpectraContainer` scalar,
`__workflowStep`). This is a **rename + restructure**, not a one-line delete (class is dead code → safe):

```
SpectraContainer  (§9.2 — generic source/owner provenance, D10)
    spectra    : { role → Spectrum }        # the data (was __spectra)
    inputs     : [ SpectraContainer ]       # SOURCE / provenance (was __spectraContainers Dict + __sourceSpectraContainer scalar → now one List)
    producedBy : SpectralWorkflowStep       # OWNER (was __workflowStep)
```
Migrate all getters/setters to the new names; delete the legacy `spectraBySampleTypes` `__init__`.

## A.1 Three image slots
Grow `model/application/setting/virtualSpectrometer/VirtualSpectrometerSettings.py` from one
`__virtualCameraImage` to a **role→QImage map**:

```
VirtualSpectrometerSettings (Singleton)
    images : { VirtualCaptureRole → QImage }     # CALIBRATION | REFERENCE | SAMPLE
    setImage(role, qimage) ; getImage(role) -> QImage
    # keep getVirtualCameraImage()/setVirtualCameraImage() as thin shims over the ACTIVE role
    # so VideoThread.__captureVirtualFrame keeps working unchanged
```

- New enum `VirtualCaptureRole { CALIBRATION, REFERENCE, SAMPLE }` + an `activeRole` pointer.
- **Two independent levels (D14):** *(1)* **`isVirtual`** — the **existing** switch: a `Boolean` on
  `SpectrometerSensor` (predefined "VIRTUAX" device = `True`), flowed into `VideoThread.setIsVirtual`.
  Selecting the virtual device as the profile is the user-facing "use the virtual spectrometer" choice —
  **unchanged**. *(2)* **`activeRole`** — **new + internal**: the engine sets it before each virtual
  capture; the shim `getVirtualCameraImage()` returns `images[activeRole]`, so `VideoThread` is untouched.
  Captures are **serialised** (one role at a time); default when unset = last-set image (legacy path safe).

## A.2 Full-resolution SPD → image encoder
The display renderer (`playground/CameraCaptureRenderUtil.renderStripArray`) scales to `displayWidth=720`
and colours the strip by `wavelengthToColor × fraction` — **cosmetic, lossy under `qGray`**. The read-back
(`ImageSpectrumAcquisitionLogicModule`, `SpectralVideoThreadSignal` branch) reads **one gray row at full
image resolution** and maps `nm = poly(pixel)`.

**New:** `logic/spectral/synthesis/SpectrumToVirtualImageUtil.py` — a *faithful* encoder:

```
encode(spectrumR, spectrumS, calibrationProfile, imageWidth, imageHeight) -> (imgR, imgS)
    vmax = max( peak(spectrumR), peak(spectrumS) )      # SHARED white-point (D11)
    for each spectrum, image in [(R,imgR),(S,imgS)]:
        for x in [x1 .. x2):
            nm   = poly(x)                              # same cubic the reader uses
            v    = interp_linear(spectrum, nm)          # linear resample onto integer-nm grid (D12)
            gray = round(255 * v / vmax)                # 0..255
            paint column x, rows range(min(y1,y2), max(y1,y2)) with QColor(gray,gray,gray)   # ROI is inverted [P-A2]
        # columns outside [x1..x2) and rows outside the ROI band = black
```

- **Grayscale-intensity strip (D6):** `qGray(g,g,g) == g`, so `qGray(pixel) == round(255 · v/vmax)` — the
  reader recovers the SPD up to 8-bit quantisation. The pretty coloured `renderStripArray` stays
  **display-only** (it is lossy under `qGray` and was never round-tripped — do **not** reuse it).
- **SHARED `vmax` across R & S (D11)** — emulates one camera + one light source shooting both, so `T=S/R`
  and the `A(λ)` plot sit on a true scale. **Linear** resampling (D12) — `Spectrum` has **no** `value_at`;
  add a small interpolation helper (synth spectra are on an integer-nm grid).
- Emit at the calibration's real `imageWidth/imageHeight` (`PlaygroundCalibrationResult` exposes both), not
  720px, so pixel↔nm matches the reader exactly.

## A.3 Round-trip verification (test)
New `tests/test_virtual_device_image_roundtrip.py`:
1. Synthesise `R`, `S` (reuse `LedReferenceSynthesisLogicModule` / `OilSampleSynthesisLogicModule`).
2. `imgR, imgS = SpectrumToVirtualImageUtil.encode(R, S, profile, W, H)` — **both spectra in one call** so
   they share a `vmax` (D11); the two-spectrum signature is the only correct one (an A.3 single-spectrum
   call cannot share a white-point).
3. Run each image through `ImageSpectrumAcquisitionLogicModule` (`SpectralVideoThreadSignal` branch) with
   the **playground calibration profile** (`PlaygroundCalibrationLogicModule.calibrate()`).
   *(the reader reads calibration from the `ApplicationContextLogicModule` **singleton** [P-A2] — specifically
   `applicationSettings.getSpectrometerProfile().spectrometerCalibrationProfile` (one level deeper than "app
   context"); the test installs `calibration.profile` there and builds a `SpectralVideoThreadSignal(image)`.)*
4. Assert the recovered **hue is within ±3° of the source hue** (D12) after encode→decode, and that the
   `T`/verdict from the **recovered** spectra match the spectra-only path (no band flip at 47/66°).

## A.4 UI — "add a set of images" (FOLDER + naming convention, Edwin 2026-07-02)
`view/.../virtualCamera/VirtualSpectrometerViewModule.py`: replace the single **Set picture** button with
one **"Set image folder…"** button → a **directory** picker. Load the three images **by filename
convention** and map each to its `VirtualCaptureRole`:

```
 <chosen folder>/
    calibration.png   → CALIBRATION
    reference.png     → REFERENCE
    sample.png        → SAMPLE
 (PNG-only; case-insensitive match; show which of the 3 were found / missing)
```

- One pick sets all three via `setImage(role, QImage(path))`; simpler than three dialogs and self-documenting.
- Validate: all three present + PNG; surface a clear "missing reference.png" style message otherwise. This
  is floor-goal step (a). *(An "auto-generate from synthesis" button remains a Later-extension.)*

## A.5 Demo image sets — named & versioned (Edwin 2026-07-02)
The demo sets the folder-picker points at are **baked artifacts** (one per demo oil), so they get a naming
+ versioning convention. Home = the sibling `spectracs-references/` (where local ground-truth already lives):

```
 spectracs-references/pumpkin_oil/virtual_captures/
    pumpkinoil_perfect_v1/     calibration.png  reference.png  sample.png   [ + set.json ]
    pumpkinoil_under_v1/       …
    pumpkinoil_over_v1/        …

 folder name : <usecase>_<variant>_v<N>
 set.json    : { synthesis params, encoder version, shared vmax, roast target hue, date }   # provenance, optional
 versioning  : bump v<N> whenever the encoder or synthesis changes → old sets stay reproducible/comparable
```

The A.2 encoder (run as a **test/tooling harness**) **produces** these sets; the A.4 picker **consumes**
one. `set.json` is optional but cheap provenance (how a set was generated). *(Precedent: the only current
writer under `spectracs-references/` is the eval test's PDF report — the encoder is a new writer following
that harness pattern; the `virtual_captures/` subtree is new.)*

---

# TRACK B — Plugin substrate (greenfield)

> **Goal:** the curated import surface + result model + base class a plugin needs. Almost entirely
> **re-exports + thin wrappers** over existing logic modules; the only genuinely new code is the
> declarative `EvaluationResult` view-models.

## B.1 `DbPlugin` entity — **SERVER-SIDE** (D7=a), seeded
Lives with `AppUser` on the **server DB** (`ServerDbBaseEntity`, `spectracsPyServer.db`) so the
`AppUser→plugin` link is a real single-DB FK. New `model/databaseEntity/…/plugin/DbPlugin.py`
(+ `DbPluginSchema.py`), following the server-entity pattern:

```
DbPlugin  (extends ServerDbBaseEntity + the id mixin)
    id       : str (pk)       # String UUID — the mixin default (NOT int)  [P-B1]
    title    : str            # "Pumpkin-seed-oil colour QM"
    codeRef  : str            # import path of the SpectralPlugin subclass (imported by the host; not run from DB)
    version  : str
    pdfRef   : str?           # fs ref to a bundled report template — nullable (PDF deferred, D1)
    # signature/publicKey: DEFERRED (§11) — omit until the trust work lands (D5)
```

Ensure an import path **pulls `DbPlugin` in before `create_all()`** on the server side (no registration
list exists — the table materialises only if the module is imported).

## B.1a Config binding `AppUser → {Plugin, virtual device}` (D3/D15 — server-side, seeded)
The §9.5 config binding hangs off the user. Per **D7=(a)** everything binding-related is server-side.
**PLUGIN binding = a real same-DB FK; DEVICE binding = a stable predefined name (D15) — NOT a profile id.**

```
AppUser  (server entity — extend inline, NOT via DbRelations.py [P-B1a])
    pluginId          : Column(String, ForeignKey("db_plugin.id"))   # REAL FK, same server DB
                        + relationship("DbPlugin")                    # ⚠ table name is db_plugin (mixin: DbPlugin→db_plugin)
    spectrometerDevice: Column(String)   # D15: stable device code-name "VIRTUAX", NOT a random profile id
    # imports to add on AppUser: ForeignKey, relationship
```

- **D15 — why device, not profile id (rubber-duck fix).** No `SpectrometerProfile` is ever **seeded**, and
  profile ids are random per-client `uuid4` (`DbBase.py:54`) created at runtime — a seeded
  `spectrometerProfileId` would **dangle** (points at a row that doesn't exist on the resolving machine). So
  the user is bound to the **virtual device** by its stable predefined code-name (`VIRTUAX`,
  `isVirtual=True`); the concrete **calibration profile is produced locally** by the existing calibration
  setup on the loaded `calibration.png`. The §9.5 profile↔user binding proper stays in ROADMAP #3.
- **Seed — server-side, single process, but NOT a one-line list edit.** Needs: (1) a new
  `PersistPluginLogicModule` (get-or-create, idempotent like the skip-if-exists user seed) that inserts the
  `DbPlugin` row **before** users so its id is available; (2) widen the seed-user record beyond
  `(username,password,role)` to carry `pluginId` + `spectrometerDevice`; (3) `DbPlugin` **imported before
  the `AppUser` mapper configures** (i.e. before the first `AppUser` query at login — string relationship
  resolves at mapper-config time, not just `create_all`). Seed `pumpkinTestUser`/`pumpkinTestUser` (Edwin,
  bcrypt via `PasswordUtil`) bound to the pumpkin `DbPlugin` + `VIRTUAX`.
- **Login flow:** `LoginLogicModule` must also **emit `pluginId`/`spectrometerDevice`** in its result dict
  (today only `id/username/roles`); the client imports the plugin by `codeRef` and selects the virtual
  device. `CurrentUserSession` (today `userId/username/roles`) gains `pluginId` + `spectrometerDevice`.
- **Overlap with ROADMAP #3:** #3 owns profile deletion + the master binding UI; this spec needs only the
  **plugin link + device name + seed**.

## B.2 `plugin_sdk` namespace
New package `sciens/spectracs/plugin_sdk/` — the **only** namespace a plugin imports (concept §10). It is a
**façade**, not new logic:

```
plugin_sdk
  data  : SpectralWorkflow, SpectraContainer, Spectrum, SpectrumSampleType,
          SpectralWorkflowPhaseType, EvaluationResult (+ view-models, B.3)
  ops   : MeanOp, TransmissionOp, AbsorptionOp, NormalizeOp, BaselineOp
          # each: SpectraContainer -> SpectraContainer, thin wrapper over the existing *LogicModule
  util  : SpectralColorUtil (spectrumToColor), VerdictOp (wraps VerdictLogicModule)
  views : ColorSwatchView, VerdictView, LabelView, SpectrumPlotView   (declarative ViewSpecs)
  steps : MeasurementStep(role,label,frames,mandatory), FormStep(...)   # step declarations
  base  : SpectralPlugin (B.4), phase-type constants ACQUISITION/PROCESSING/EVALUATION/METADATA/PUBLISHING
```

The `Op` wrappers adapt the existing single-purpose modules
(`MeanSpectrumLogicModule`, `TransmissionLogicModule`, `AbsorptionLogicModule`, …) to the uniform
`container → container` shape by pulling the named bags from `inputs` and writing the result bag.

## B.3 `EvaluationResult` + view-models
New `model/spectral/evaluation/`:

```
EvaluationResult                      # a persistable, Qt-free CONTAINER of renderable view-models
    items : [ ViewModel ]             # ordered; host renders each into the EVALUATION tab
ViewModel (base)
  ├─ ColorSwatchView(color: rgb, label)          # a filled block  (lift PlaygroundViewModule.__swatch)
  ├─ VerdictView(roastState: RoastState)         # the verdict text/badge
  ├─ LabelView(text)                             # a caption / measured-hue readout
  └─ SpectrumPlotView(spectrum, title)           # an absorption/T curve (PROCESSING reuses this too)
```

- **Qt-free & declarative** — colours as plain RGB tuples, not `QColor`; the **host** renderer (C.3) turns
  each into a widget. This is the extraction of what `PlaygroundViewModule.__populate()` does imperatively.

## B.4 `SpectralPlugin` base + phase enum
- Extend `model/spectral/SpectralWorkflowPhaseType.py` to the canonical five:
  `ACQUISITION, PROCESSING, EVALUATION, METADATA, PUBLISHING`. The legacy `ACQUIREMENT_VIEW` /
  `ACQUIREMENT` values + the `SpectralWorkflowUtil.getWorkflow()` stub they feed are **superseded** by the
  Track-C engine (retire once C.1 lands).
- `plugin_sdk/base/SpectralPlugin.py` — abstract base, five hooks, each mutating the workflow (§9.4):

```python
class SpectralPlugin:
    title = ...
    def acquisition(self, workflow): ...   # DECLARE measurement steps (interactive)
    def processing(self, workflow):  ...   # CREATE+FILL: mean → absorption (container chain)
    def evaluation(self, workflow):  ...   # CREATE+FILL: colour → verdict → EvaluationResult
    def metadata(self, workflow):    ...   # empty for pumpkin (D1) → phase skipped
    def publishing(self, workflow):  ...   # empty for pumpkin (D1) → phase skipped
```

- `SpectralWorkflowStep` (`model/spectral/SpectralWorkflowStep.py`) grows the §9.3 carrier fields:
  `container: SpectraContainer?`, `evaluationResult: EvaluationResult?`, `view: ViewSpec?`,
  `widget: QWidget? (transient)`, `persist: bool`. (Persist is a no-op flag this milestone — D2.)

---

# TRACK C — Host engine + `PumpkinOilPlugin` + nested-wizard UI

> **Goal:** the host that assembles the spine, runs the plugin's hooks on **Next**, sources acquisition
> from the virtual device, and renders the nested wizard — ending on the colour/verdict tab. This is the
> integration that reaches the floor goal.

## C.0 Launch & landing seam (rubber-duck: the real missing integration piece)
The wizard interior is detailed, but **nothing today registers, gates, or launches it** — login only
recolours the account icon (`MainStatusBarViewModule.onClickedAccountButton`), navigation is two hardcoded
`if/elif` routers, and the startup page is `SpectrometerConnectionViewModule`. This seam must be built or
the configured end-user can never reach the wizard:

- **Register the wizard** as a new navigation target in **both** hardcoded routers: `MainViewModule`
  (widget list + index) and `NavigationHandlerLogicModule` (`handleNavigationSignal`/`__getWidgetIndex`).
  Mirror how `PlaygroundViewModule` was registered.
- **Login → navigate.** On successful login, if `CurrentUserSession` has a bound `pluginId`, the client
  **routes to the wizard** for that plugin (extend `onClickedAccountButton`'s success path, which today only
  emits `userSessionSignal`). Simplest end-to-end; a dedicated "start measurement" landing is a later nicety.
- **`Save`/`Cancel` → `"Home"`** uses the proven `NavigationSignal.setTarget("Home")` pattern
  (`SpectralJobViewModule.onClickedBackButton`). **Caveat:** `"Home"` (`HomeViewModule`, index 0) is *not*
  the app's startup page and is master-flavoured ("New measurement" → legacy `SpectralJob`). For this
  milestone Save/Cancel land on `"Home"`; giving the end-user a pumpkin-aware landing is follow-up.
- **Role gate:** none exists today (routers ignore roles). Not required for the milestone (login resolves
  the plugin and routes); note it as absent so nobody assumes a gate protects master pages.

## C.1 Workflow engine (host)
New `logic/spectral/workflow/SpectralWorkflowEngine.py` (replaces the `SpectralWorkflowUtil.getWorkflow`
stub):

- **Resolve the plugin from the logged-in user** (D3): read `CurrentUserSession()` →
  `pluginId` → `DbPlugin.codeRef` → import + instantiate the `SpectralPlugin` subclass. The plugin runs
  *because the user is bound to it* — not hard-coded. The bound `spectrometerDevice` (`VIRTUAX`, D15)
  selects the virtual device; its calibration profile is the one produced locally from `calibration.png`.
- **Build** the fixed 5-phase spine (`SpectralWorkflow` with a `SpectralWorkflowPhase` per phase type).
- **Advance:** on host **Next**, run the current phase's plugin hook; a phase whose hook created **0
  steps** is **auto-skipped** (no tab, no stop — §9.1). Order: ACQUISITION → PROCESSING → EVALUATION →
  (METADATA skipped) → (PUBLISHING skipped) → Finish.
- **Acquisition dispatch:** for each interactive `MeasurementStep`, set the virtual device **active role**
  (A.1) to the step's role, capture N frames through the existing `VideoThread` → `ImageSpectrumAcquisition`
  path into the step's container bag. (Virtual = the *same* image each frame; mean is trivial but the path
  is real.)
- **Computed phases:** run the plugin's `processing`/`evaluation` hooks, which compose the `plugin_sdk`
  ops over the accumulated containers.
- **Calibration staleness guard (2026-07-02):** `__ensureCalibration` trusts an installed polynomial **only
  when its ROI still lands on signal** in the *current* CALIBRATION image (samples the reader's own centre
  row `(Y1+Y2)/2` across `[X1,X2]`, same `gray>20` test as the vertical-edge scan). A profile left over from a
  different capture (e.g. an older, differently-sized virtual set) would otherwise read a black row → empty
  spectrum → no peaks; it now forces a re-detect. A real device (no virtual calibration image) keeps its
  stored profile untouched. Regression-tested in `tests/test_stale_calibration_recovery.py`. *(An earlier
  attempt to clear the whole `SpectrometerProfile` on folder-load was reverted — it nulled the sensor the
  manual calibration UI reads.)*
- **Manual ROI detection (Settings → …→ "Detect Region of Interest"):** the handler now guards its
  preconditions with feedback instead of dying silently in the Qt slot (no spectrometer selected → prompt to
  pick one; virtual sensor with no calibration image → prompt to load a folder) and pins the virtual
  **active role to CALIBRATION** so detection runs on the calibration frame. `HoughLineLogicModule` also
  guards `HoughLinesP` returning `None` on a featureless image.

## C.2 `PumpkinOilPlugin`
New `logic/spectral/plugin/pumpkin/PumpkinOilPlugin.py` (a `SpectralPlugin`), criteria as constants
(source of truth — §9.4):

```
title = "Pumpkin-seed-oil colour QM"
# band edges from VerdictLogicModuleParameters (overRoastedBelowHue=47, underRoastedAboveHue=66)

acquisition: declare REFERENCE step + SAMPLE step (frames=N, mandatory) — host fills from virtual device
processing : mean(ref) ; mean(sample) → T = TransmissionOp(ref,sample)
             → AbsorptionOp(persist=True, view=SpectrumPlotView("A(λ)"))   # A recomputes T internally
evaluation : result = SpectrumToColorLogicModule().spectrumToColor(params.setSpectrum(T))
             hue    = result.getHue()          # DEGREES 0-360 — the proven path (matches ground truth)
             color  = result  # measured QColor → convert to rgb at the model boundary (R-B4)
             roast  = VerdictOp(hue)                       # RoastState, bands 47/66°
             EvaluationResult[ ColorSwatchView(measured), ColorSwatchView(target),
                               LabelView(f"hue {hue:.0f}°"), VerdictView(roast) ]
             # DO NOT use QColor.hueF(): 0-1 vs degrees mismatch + grey→-1 → always OVER_ROASTED (R-C1)
metadata   : pass       # skipped (D1)
publishing : pass       # skipped (D1)
```

## C.3 Nested-wizard GUI (the one genuinely new UI)
The end-user view is a **nested wizard** (concept/ROADMAP #6): **outer** = phases advanced by a page-local
**Next**; **inner** = the step tabs of the current phase. **Two navigation levels, never conflated:** inner
tabs switch the *step view within a phase*; the bottom **Next/Back** advance *phases*.

**Window anatomy** (one `PageWidget`; header + full-width status bar already exist from #2):
```
 ┌ spectracs                                        [ 👤 pumpkinTestUser ▾ ] ┐  header (logo L · account R)
 ├──────────────────────────────────────────────────────────────────────────┤
 │  Pumpkin-seed-oil colour QM                              ← page title       │
 │  ┌ phase rail — READ-ONLY status indicator ─────────────────────────────┐  │
 │  │   ● ACQUISITION ───────── ◉ PROCESSING ───────── ○ EVALUATION         │  │
 │  └────────────────────────────────────────────────────────────────────────┘  │
 │  ┌ inner step tabs (current phase) ─── QTabWidget ──────────────────────┐  │
 │  │ [ Absorption ]                                                        │  │
 │  │ ┌───────────────────────────────────────────────────────────────────┐│  │
 │  │ │  step body: capture preview / plot / result                       ││  │
 │  │ └───────────────────────────────────────────────────────────────────┘│  │
 │  └────────────────────────────────────────────────────────────────────────┘  │
 │                                            [ ◀ Back ]      [ Next ▶ ]        │  nav group box (NEW, page-local)
 ├──────────────────────────────────────────────────────────────────────────┤
 │  status / progress bar (full width)                                        │  existing
 └──────────────────────────────────────────────────────────────────────────┘
```

**Phase rail** — read-only (D-UI-1); markers `●` done · `◉` current · `○` upcoming · `⊘` skipped (a
0-step phase is **not drawn** — pumpkin shows only the 3 non-skipped). You move with Back/Next, **not** by
clicking the rail (clickable-rail is a later nicety).

**Per-phase screens:**
```
 ① ACQUISITION (interactive)      [ Reference* ] [ Sample* ]   *mandatory
    each tab: capture preview from the virtual REFERENCE/SAMPLE image (frames + mean overlay, N/N ✓)
    left [ Cancel ]                right [ Next ▶ ] — OFF until BOTH tabs ✓   (Back hidden: first phase)

 ② PROCESSING (computed)          [ Absorption ]
    A(λ) = −log10(SAMPLE/REFERENCE) plot (SpectrumPlotView)
    left [ ◀ Back ] [ Cancel ]     right [ Next ▶ ] (always on)

 ③ EVALUATION (computed, FINAL)   [ Result ]
    measured swatch · target swatch · "hue 72°" · [ PERFECT ROAST ✓ ]
    left [ ◀ Back ] [ Cancel ]     right [ Save ]   — Save & Cancel BOTH → home (no-op now, D-UI-2)
```

**Navigation state machine** — a page-local button (the X3 fix; **not** `NavigationSignal`, which is a
page-by-name router). One **Next** click:
```
   1. validate current phase (mandatory steps satisfied?)   ── no ▶ stay, hint in status bar
   2. run the NEXT phase's plugin hook (it creates that phase's steps)
   3. if that phase produced 0 steps → auto-skip, run the following one   (METADATA∅ · PUBLISHING∅)
   4. move the phase pointer · rebuild the inner tabs · repaint the rail
   Back:   retreat one phase, captured data preserved (hidden on the first phase).
   Cancel: on every phase — abandon the run → home screen.
   Save:   only on EVALUATION — → home screen.
```
- **D-UI-1 — phase rail is a read-only status indicator** (Edwin): navigate via Back/Next only.
- **D-UI-2 — final step = Save + Cancel, both → home, both NO-OP for now** (Edwin). `Cancel` is available on
  every phase (abandon → home); `Save` appears only on the terminal EVALUATION phase (→ home). **Because
  nothing is persisted yet (D2), `Save` and `Cancel` are functionally identical today** (both discard →
  home) — the buttons are pre-placed so that when workflow-record persistence lands (follow-up), `Save`
  gets its real body (persist the run) while `Cancel` stays a discard. `Back` remains so the user can
  inspect how the result was reached.

**Build reuse & renderer:**
- **Reuse** the `PageWidget` contract (`getMainContainerWidgets`, `_getPageTitle`, `createNavigationGroupBox`,
  lazy `showEvent` populate) as `PlaygroundViewModule` does; inner tabs = a `QTabWidget` of one widget per
  **viewable step**.
- **`EvaluationResultRenderer`** (host) turns each B.3 view-model into a widget: swatch = styled block
  (lifted from `PlaygroundViewModule.__swatch`), verdict = label/badge, plot = the existing spectrum plot.
  The EVALUATION step carries the `EvaluationResult` → floor-goal step (c).

## C.4 End-to-end integration test
`tests/test_pumpkin_workflow_end_to_end.py` (headless, no GUI): virtual device seeded with encoded
REFERENCE/SAMPLE strips (Track A) for each of the 3 demo oils → `SpectralWorkflowEngine` + `PumpkinOilPlugin`
→ assert the resulting `EvaluationResult.VerdictView.roastState` matches the oil's known roast state
(the real-spine mirror of the existing playground regression test).

---

## Sequencing within the combined build

```
 A.0 fix SpectraContainer ─┐
 A.1 3 slots               │  (Track A is independent + test-verifiable on its own)
 A.2 full-res encoder      ├─▶ A.3 round-trip test ✅
 A.4 3-image UI            ┘
                                         B.1 DbPlugin ─┐
                                         B.2 plugin_sdk│ (substrate; B before C)
                                         B.3 EvalResult├─▶ B.4 SpectralPlugin + 5-phase enum
                                                        ┘
   A ✅ + B ✅ ──▶ C.1 engine ──▶ C.2 PumpkinOilPlugin ──▶ C.4 headless E2E test ✅
                                                       └──▶ C.3 nested-wizard GUI ──▶ FLOOR GOAL ✅
```

- **C.1 + C.2 are headless-testable** (C.4) *before* the GUI exists — build and verify the spine run first,
  then C.3 renders it. De-risks the new UI by proving the data flow independently.

## Explicitly out of scope (named follow-ups, not this milestone)
- **Workflow-*record* persistence** / promoting `model/spectral/` to SQLAlchemy (concept §9.5) — D2. *(The
  config binding IS in scope + seeded — B.1a/D3; only saving the run itself is deferred.)*
- **ROADMAP #3's master-facing binding UI** (profile deletion, pick-user-when-creating-a-profile) — the
  link + seed is in scope here (B.1a); the CRUD/UI stays in #3 unless folded in.
- **METADATA form + PUBLISHING (PDF/email)** — D1; empty hooks, re-introduce later.
- **Plugin signature verification / hot-loading** (concept §11) — D5; host imports the class directly.
- **LED-combination optimisation** — separate future task; current LED set fixed.

## Resolved defaults
1. **Frames per virtual measurement (N) = 5.** Virtual frames are identical (N=1 is faithful), but the
   reused capture-preview gates rendering on `currentFrameIndex > 3` (`SpectralJobWidgetViewModule.py:82`),
   so **N must be ≥ 5** or the preview shows nothing. N=5 exercises the mean path and satisfies the gate.
2. **Target swatch colour** = reuse `PlaygroundViewModule.__targetColor()` / `PLAYGROUND_DEMO_OILS`.
3. **`plugin_sdk` package root** = `sciens.spectracs.plugin_sdk` (matches the live namespace).
