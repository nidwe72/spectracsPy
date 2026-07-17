# SPEC — Project structure & tiering (`spectracsPy-core`)

Status: **S0 · S1a · S1b · S2 · S3a · S3b · S4 IMPLEMENTED (2026-07-16/17) — `spectracsPy-core` EXISTS and is Qt-free; S5 DESIGN — settled 2026-07-17 (§ *"S5 (DESIGN, settled 2026-07-17)"* before §6) · S7 (dependency tangle) DESIGN** (spec-first; implement on explicit request only). Source:
Edwin (2026-07-16), split out of [`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md) — it outgrew being a
track inside M3. Naming **settled: `spectracsPy-core`** (matches the existing layer-name pattern base / model /
server; `-sciens` was rejected because `sciens` is the org root in *every* repo).

Theme: **the science is not the app.** Extract a Qt-free shared tier that the app, the plugins, and a future LIMS
addon all consume — and that none of them can bypass by accident.

> **Pre-existing issues met during S0–S4 — none caused by the tiering.** They live in
> [`SPEC_test_hygiene_debt.md`](SPEC_test_hygiene_debt.md), which is the single place for this: **T1** (stale
> test-DB schema), **T2** (the suite-staller hang), **R1** (the server's `TypeError` — `NetworkUtil` matches only
> `wlp*`/`eth0*`, so a wired `eno1` yields no LAN IP), **R2** (`runServer.sh` lacks `-core` — mine), **D1**
> (`luxpy` wrongly listed as dead).
>
> **T1 and T2 were already catalogued there, and this work re-found both from scratch and wrote them down a second
> time** — precisely what that file exists to prevent. It only works if it is read *before* declaring something
> "pre-existing". Two more found here and still only recorded here, because they are not test/runtime failures but
> dead code: **`Polisher.py`** (`from base import SingletonQObject` — a path dead since `9dfa957`; invisible
> because its only caller is a commented-out line) and **`NavigationHandlerLogicModule.getPreviousNavigationSignal()`**
> (always `None`: `Singleton` guards `__new__` but not `__init__`, so the field re-initialises on every
> construction).


---

## 0. Why — three requirements, one move

This is not a plugin-distribution feature. Three independent requirements point at the same tier, which is the
argument for building it once:

1. **Plugin authoring isolation (Edwin).** Open a plugin project in PyCharm and see the SDK — *not* the app's code.
   Today impossible: plugins live in `spectracsPy` alongside view/controller/capture.
2. **A future SENAITE addon that shows spectra (Edwin).** A LIMS addon needs the science + the data + a renderer,
   and must not drag in Qt, the camera, or the app. See [`SPEC_lims_integration.md`](SPEC_lims_integration.md).
3. **A meaningful SDK boundary before distribution freezes it.** `plugin_sdk` becomes a published contract in M3
   ([`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md) §2). Versioning a namespace that is about to
   relocate and acquire a real boundary is versioning a moving target.

**Non-goal:** this spec does not sandbox anything. Python has no private dependencies — a plugin depending on
`-core` can reach past `plugin_sdk` into the science if it tries. The boundary is **namespace convention + a
publish-time lint gate**, which is what M3 §1 already concedes ("hygiene, NOT a sandbox") and is exactly
proportionate while Edwin is the only plugin author.

---

## 1. Target structure

> **Diagram:** [`project_structure.svg`](../../spectracs-docs/project_structure.svg) — the tiering + **external
> dependencies per repo**. Generated from [`project_structure.puml`](../../spectracs-docs/project_structure.puml);
> regenerate with `cd spectracs-docs && java -jar plantuml.jar -tsvg project_structure.puml`.

```
                      +--------------------------+
                      |    spectracsPy-base      |   sciens.base
                      |    (exists)              |   Singleton   (Qt-free since S0)
                      +--------------------------+
                                   ^
                                   |
                      +--------------------------+
                      |    spectracsPy-model     |   data classes, plugin view-models, DB entities
                      |    (Qt-free since S1b)   |   + SpectralColor (NEW, S1b)
                      +--------------------------+
                          ^                   ^
                          |                   |
                          |        +--------------------------+
                          |        |   spectracsPy-server     |  Pyro; DUMB STORE.
                          |        |   (exists)               |  Never signs. No core.
                          |        +--------------------------+
                          |
             +--------------------------+
             |     spectracsPy-core     |   THE SHARED TIER — Qt-free
             |     (NEW)                |     - spectral science
             |                          |     - plugin_sdk  (the facade)
             |                          |     - visitor + matplotlib renderer
             +--------------------------+
                ^             ^              ^
                |             |              |
   +-------------------+ +-------------------+ +---------------------+
   | spectracsPy (app) | | spectracs-plugins | | senaite-spectracs   |
   | (exists)          | | (NEW)             | | (FUTURE)            |
   |                   | |                   | |                     |
   | view, controller, | | PumpkinOilPlugin  | | LIMS addon:         |
   | capture, session, | | DevSpectralPlugin | | shows spectra       |
   | server client,    | |                   | |                     |
   | QtWorkflowRenderer| | imports plugin_sdk| | no Qt, no app,      |
   |                   | | ONLY (lint gate)  | | no camera           |
   | >> Qt LIVES HERE  | |                   | |                     |
   +-------------------+ +-------------------+ +---------------------+

   arrows = "depends on" (pointing at the dependency)
```

`sciens` stays the org root package in every repo; only the *repo* boundary moves, never a namespace. This is
load-bearing: **`sciens.spectracs.plugin_sdk` keeps its import path**, so plugin source written (or already
published, M3 B4) before this move still resolves after it.

### 1b. External dependencies per tier

Verified 2026-07-16 against `spectracsPy/requirements.txt` and the actual imports of the packages moving to `-core`.

| Tier | External dependencies |
|---|---|
| `spectracsPy-base` | — (stdlib) |
| `spectracsPy-model` | SQLAlchemy · SQLAlchemy-serializer · marshmallow · marshmallow-sqlalchemy — **Qt-free since S1b ✅** |
| **`spectracsPy-core`** | numpy · **scipy** · colour-science · rgbxy · spectres · matplotlib · Pillow · pypdf |
| `spectracsPy` (app) | PySide6 · pyqtgraph · scipy · opencv-python-headless · pyusb · psutil · appdata · colormath · luxpy · pyspectra |
| `spectracsPy-server` | Pyro5 · bcrypt · **PyNaCl** (new — M3 signature verify) |
| `spectracs-plugins` | — (only `-core`, via `plugin_sdk`) |

`-core` carries **scipy** (Edwin, 2026-07-16 — explicitly fine). That is a consequence of the conditioning chain
moving in (§2), and it costs nothing: wheels exist everywhere and [`SPEC_android_port.md`](SPEC_android_port.md) P0
proved real scipy on-device.

`-core` → `-model` used to drag SQLAlchemy **and PySide6**; **S0 + S1b closed the PySide6 half** (§4b). The
SQLAlchemy half remains — the `-model` split question in §8.

### 1c. The membership rule — and why the "app conditions / plugin interprets" line moved

**The rule (settled 2026-07-16). Core membership is cheap and reversible; only `plugin_sdk`'s exports are a
contract.** The façade is the boundary — *not* the repo. A class in `-core` that the façade does not export is
invisible to every plugin, so moving it in or out later is a `git mv`. A class *exported by the façade* is frozen
the moment a plugin imports it, and withdrawing it is a breaking SDK change.

So the test is **not** "would a plugin use it?" — that is speculative and unarguable. It is:

> **Is it science, free of app coupling — no Qt (incl. pyqtgraph), no camera, no session, no server, no DB?**
> If yes → `-core`. What plugins actually *see* is `plugin_sdk`'s separate, conservative decision.

**Be liberal about core, conservative about the façade.** The audit in §5 applies exactly this rule.

**Consequence for the conditioning chain.** [`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md)
(IMPLEMENTED) defines the canonical chain `mean → smooth → removeBaseline → rebin → normalize` behind the
`SpectrumUtil` façade, and its architectural line was *the app conditions, the plugin interprets*. That line
**survives — but it has moved from the repo boundary to the façade**:

- The chain's **code** now lives in `-core` (per the rule: it is Qt-free science).
- `plugin_sdk` **still exposes no** `SmoothOp` / `RebinOp` / `NormalizeOp` (**decision #2, settled**), so plugins
  still receive an *already-conditioned* spectrum and cannot condition their own.
- Exposing them later is **additive and free**; withdrawing them would not be. Hence: not yet.

scipy's 7 usages are all on the conditioning/calibration side of that line — 5× `find_peaks`/`peak_prominences`
(wavelength calibration ×4 + spectral-line selection), 1× `savgol_filter` (smooth), 1× `minimum/maximum_filter1d`
(baseline). Four of those now sit in `-core` and three stay in the app (§5).

---

## 2. What moves into `spectracsPy-core`

From `spectracsPy/sciens/spectracs/`:

| Moves | From | Why |
|---|---|---|
| `plugin_sdk/` (whole package) | `spectracs/plugin_sdk/` | it *is* the facade |
| `logic/spectral/absorption/` | `logic/spectral/` | `AbsorptionOp` wraps it |
| `logic/spectral/transmission/` | " | `TransmissionOp` wraps it |
| `logic/spectral/meanSpectrum/` | " | `MeanOp` wraps it |
| `logic/spectral/spectrumToColor/` | " | `EvaluationColorUtil` wraps it |
| `logic/spectral/verdict/` | " | `VerdictOp` wraps it |
| `logic/spectral/feature/` | " | `SpectrumFeatureUtil` wraps it |
| `logic/spectral/util/SpectralColorUtil.py` | " | used by `spectrumToColor` |
| `logic/spectral/util/SpectrumUtil.py` | " | **the conditioning-chain façade** — follows its chain |
| `logic/spectral/util/SpectralWorkflowUtil.py` | " | workflow phase/step helpers; plugins mutate `SpectralWorkflow` (#3) |
| `logic/spectral/util/SpectrallineUtil.py` | " | line helpers; Qt-free after S1b (#5) |
| `logic/spectral/smoothSpectrum/` | `logic/spectral/` | **scipy** `savgol_filter` — the chain |
| `logic/spectral/removeBaseline/` | " | **scipy** morphological opening — the chain |
| `logic/spectral/rebinSpectrum/` | " | the chain |
| `logic/spectral/normalizeSpectrum/` | " | the chain |
| `logic/spectral/spectralLine/` (8 files) | " | **scipy**, no Qt; generic peak selection (#5) |
| `logic/spectral/synthesis/` (8 of 9) | " | LED-ref + oil-sample synthesis = physics (#6); **not** `SpectrumToVirtualImageUtil` (QImage → app) |
| `logic/spectral/acquisition/RobustReductionLogicModule.py` | `logic/spectral/acquisition/` | **`MeanSpectrumLogicModule` imports it** — see the nick below |
| `logic/spectral/acquisition/ExtendedRoiLogicModule.py` | " | numpy-only; capture-quality M1 = *"plugin ROI clamp"* — the **plugin** declares the ROI (#4) |
| `view/.../render/WorkflowItemVisitor.py` | `view/spectral/workflow/render/` | **already Qt-free**; the M1 seam |
| `view/.../render/MatplotlibWorkflowRenderer.py` | " | **already Qt-free**; M2's PDF renderer |
| `view/.../render/WorkflowReportBuilder.py` | " | after S2 de-Qts it |

**`plugin_sdk` is not liftable on its own** — this is the finding that sizes the whole spec. Its ops and utils are
thin adapters over the logic modules above (`TransmissionOp` → `TransmissionLogicModule`, etc.). Lift the facade
alone and you get an empty shell reaching back into the app. **Extracting the SDK means extracting the science.**

**The good news: the seam already exists and is nearly sharp.** Those six logic packages import only `numpy`,
`colour`, `rgbxy`, `math`, `colorsys`, `enum`, plus `spectracsPy-model` and `sciens.base` — both already separate
repos. No view, no controller, no session, no server client. The science and the app drifted apart on their own;
nobody drew the line.

**One nick in it (found 2026-07-16):** `MeanSpectrumLogicModule` imports
`logic.spectral.acquisition.RobustReductionLogicModule` — a core-bound package reaching into `acquisition/`, which
otherwise stays in the app (capture-quality M2 wired robust reduction into `mean`). `RobustReduction` is **numpy-only
and Qt-free** (Tukey biweight, sigma-clipped mean): it is *science misfiled under acquisition*, the same pattern as
the render seam under `view/`. **It moves to `-core`**; the rest of `acquisition/` stays. Check for further nicks
during S3a — the seam is a claim to verify, not to assume.

## 3. What stays in `spectracsPy` (the app)

`view/` (incl. `QtWorkflowRenderer`), `controller/`, `logic/session/`, `logic/server/`, `logic/appliction/`, and
the camera-bound rest of `logic/spectral/` — **`video/`, `acquisition/` (minus `RobustReductionLogicModule`),
`device/`**. These are Qt- and camera-bound and genuinely belong to the app. `SpectralWorkflowEngine` stays (it
resolves the logged-in user's binding — a host concern), as does the M3 `PluginRegistry`.

**Wavelength calibration stays (decision #1)** — `acquisition/device/calibration/` (`CalibrationAlgorithm`,
`WavelengthLineDetectionLogicModule`, `SpectrometerWavelengthCalibration{,Advanced,Consensus,Parameters,Result}`,
`SpectrometerRegionOfInterestLogicModule`). **7 of its 8 files are Qt-free**, so §1c's coupling rule would admit
them — but no plugin and no LIMS addon will ever calibrate an instrument. This is the one place where the rule and
the semantics disagree; it is cheap to revisit either way.

**Also staying:** `importSpectrum/` (#7 — Qt-free after S0, but it is file I/O on the legacy `SpectralJob` path, not
science), `util/SpectralLineMasterDataUtil.py` (imports `logic/persistence` → DB-bound),
`synthesis/SpectrumToVirtualImageUtil.py` (QImage — the virtual camera), and
`logic/spectral/workflow/SpectralWorkflowEngine` (session + plugin import = host concern).

---

## 4. The Qt leaks — what actually blocks "Qt-free"

Verified against the code 2026-07-16. Three, of decreasing tractability:

- **L1 — the science's colour path.** `logic/spectral/util/SpectralColorUtil.py` imports `PySide6.QtGui.QColor`
  and uses it throughout (`fromRgb`, `hueSimilarity`, `channelDominance`, `getColorDifference`, `spectrumToColor`);
  `SpectrumToColorLogicModule` builds `QColor`s and `SpectrumToColorLogicModuleResult` carries one. It is RGB-triple
  maths that QColor barely earns its keep on — the *reach* is the problem, not the maths. **→ S1a/S1b.**
- **L2 — the report builder.** `WorkflowReportBuilder` imported `PySide6.QtGui.QImage, QPixmap`. **✅ CLOSED (S2).**
  It turned out to be a *split*, not a de-Qt: the class was designed as the host bridge and had Qt at both ends
  (QImage in, QPixmap out) around a Qt-free middle. Both ends moved to the host.
- **L3 — `spectracsPy-model` is not Qt-free.** Ten files import PySide6 (nine in `-model`, one in `-base`). The
  **plugin view-models are clean** (`ColorSwatchView` etc.), so nothing breaks at *import* time — but `-core` depends
  on `-model`, so a SENAITE addon carries PySide6 as an *install* dependency it never uses. **Resolved below: nine of
  the ten are not a Qt problem at all — they are a filing problem. → S0.**

### 4b. L3 — ask the right question

An earlier draft of this spec asked **"does this class *need* `QObject`?"**, found the answer was mostly no, and
concluded *delete the base class*. **That was the wrong question** (caught by Edwin, 2026-07-16). The right one is:

> **Does this class belong in `-model` at all?**

For nine of the ten, no. They are **app plumbing** — navigation between views, the status bar, "a DB row changed,
refresh the list", the camera pipeline, the virtual camera, a Qt metaclass. Nothing in the model layer uses them; no
plugin touches them; no LIMS addon touches them. **Once they move to the app, whether they need `QObject` stops
mattering — and Qt is entirely fine where they actually live.**

| Files | Verdict |
|---|---|
| `SpectralJob` · `NavigationSignal` · `ApplicationStatusSignal` · `DbEntityChangedSignal` (+ its subclasses `UserSignal`, `SpectrometerProfileSignal`) · `VideoSignal` · `SpectralVideoThreadSignal` · `SpectrometerCalibrationProfileHoughLinesVideoSignal` · `VirtualSpectrometerSettings` · `-base`'s `SingletonQObject` | **Move to the app, keep the Qt. → S0** |
| `SpectralLine.color: ClassVar[QColor]` | **The only genuine de-Qt.** A real DB entity, so it stays in `-model` and takes S1b's `SpectralColor`. **✅ DONE (S1b) — L3 is closed; `grep -rE 'PySide6\|pyqtgraph' -model/ -base/` now returns nothing.** |

**Verified they are movable (2026-07-16):** `NavigationSignal` and `ApplicationStatusSignal` have **zero** consumers
inside `-model`. `DbEntityChangedSignal` is used only by `UserSignal` / `SpectrometerProfileSignal` — themselves app
plumbing in `-model`. `SpectralJob` is used by `SpectralVideoThreadSignal` (also moving) and by **a comment** in
`SpectralWorkflowPhaseType` — not an import.

**Why moving beats de-QObject-ing, on every axis:** same outcome (`-model` goes Qt-free), but **no marshalling
change** — so the `Signal(NavigationSignal)` hazard a previous draft documented at length simply never arises; **no
click-through needed**, because relocation is semantically inert; and it is *correct* rather than merely safe. These
classes were **misfiled, not over-engineered**.

**Why the cargo exists (worth naming so it doesn't regrow):** classes named `*Signal` were made `QObject`s because
"signals are a Qt thing". But the payload of a Qt signal needs no base class at all — **only the *emitter* must be a
`QObject`**, and the emitter is `ApplicationSignalsProvider`, in the app. The `*Signal` classes are DTOs *carried by*
a signal, not signals themselves. `SingletonQObject`'s existence probably reinforced the habit. The observation is
true — it is just **irrelevant**, because the fix is the move, not the base class.

### 4d. Why S1 splits into characterise-then-replace

**S1 is the riskiest phase in Track S, not the routine one** — and it is the only one that is real code rather than
a file move. `SpectralColorUtil` does not merely *hold* colours: **`hueSimilarity` and `channelDominance` are how
emission lines get identified during wavelength calibration** (`WavelengthLineDetectionLogicModule`,
`SpectralLinesSelectionLogicModule`). Calibration is the foundation under every measurement, and **calibration
errors are silent** — a slightly-off pixel→nm map poisons everything downstream without raising anything.

**The coverage is exactly inverted from the risk** (verified 2026-07-16):

| Function | Feeds | Tests today |
|---|---|---|
| `spectrumToColor` | plugins / evaluation | **4** |
| `hueSimilarity` | calibration line detection | **none** |
| `channelDominance` | calibration line detection | **none** |
| `wavelengthToColor` | calibration reference colours | **none** |

The well-guarded half is the half a plugin **cannot even tell changed** (S1 is invisible behind
`EvaluationColorUtil`, §4's "not a leak"). The unguarded half is the one that can quietly break calibration.

**The specific trap: `QColor.hueF()` returns `-1` for achromatic colours; `colorsys` returns `0.0`.**
`hueSimilarity` explicitly branches on `if h1 < 0: return 0.0`. Port that naively and grey pixels start reading as
**red** with a confident-looking similarity score. This path has burned the project before — `EvaluationColorUtil`'s
own comment says *"the hue in DEGREES (0-360, the proven verdict path — **never QColor.hueF()**)"*.

**Hence the split, mirroring S3a/S3b — prove first, change second.** S1a pins today's behaviour while the QColor
code is still there to pin it against; S1b then *proves* it is behaviour-preserving instead of hoping. S1a is
**worth doing on its own merits**: it covers calibration-critical maths that has no tests at all today.

**What is NOT a leak (checked — the boundary holds):** `EvaluationColorUtil` already converts QColor → plain
`(r,g,b)` + hue-in-degrees before handing anything to a plugin, and `ColorSwatchView` carries a plain tuple. The
plugin-facing SDK surface is Qt-free **today, by deliberate design**. Consequence: **S1 is invisible to plugins and
is not a breaking SDK change.**

---

## 5. The audit — every package classified

Ran 2026-07-16 over **`spectracsPy/sciens/spectracs/{logic,view,controller,plugin_sdk}`** (`-model`/`-base` class
residue is §4b). Rule = §1c: **is it science, free of app coupling?** Decisions #1–#9 settled by Edwin the same day.

**`spectracsPy-model` has its own `logic/` tree — 52 files — and it was audited separately (2026-07-16):**
`config`, `instrument`, `lims` (incl. the SENAITE adapter), `model/util`, `payment`, `persistence` (14 pkgs), `user`.
**Zero Qt, zero numpy/scipy** — all persistence / LIMS / payment / user, i.e. server-side. **Nothing moves to
`-core`.** (Noted in passing: `-model` is therefore misnamed — it is model *plus* server-side logic. Out of scope.)

**Caveat on method — read this before trusting the tables.** Coupling was established by grep plus reads of the
ambiguous modules, **not** by reading every class. Two method failures were caught and corrected in the making of
it: the first pass grepped only `PySide6`, so **pyqtgraph** (which is Qt) looked clean; and it filtered out
`sciens.` imports, hiding the intra-project dependency that turned out to be the `MeanSpectrum → RobustReduction`
nick. Both were re-run. **A Qt detector must match `PySide6` AND `pyqtgraph` AND `shiboken`.**

> **The tables below are the *argument*, not the *manifest*.** Every claim checked while writing this spec moved on
> contact — "the seam is sharp" (it had a nick), "no scipy" (only as an SDK snapshot), "S1 breaks the SDK" (it does
> not), "Qt-free" (pyqtgraph), "the audit is complete" (`-model`'s `logic/`), "S0 is free" (signal typing). The
> lesson generalises: **this codebase's filing does not predict its coupling.** That is the reason for the spec —
> and the reason **S3a must re-derive the move list by grep on the day**, rather than trust a list written weeks
> earlier.

### → `spectracsPy-core`

| Package / class | Does | Coupling | Why |
|---|---|---|---|
| `logic/spectral/transmission` | T = S/R | numpy | SDK: `TransmissionOp` |
| `logic/spectral/absorption` | A = −log₁₀(T) | numpy | SDK: `AbsorptionOp` |
| `logic/spectral/meanSpectrum` | frame averaging | numpy | SDK: `MeanOp` |
| `logic/spectral/verdict` | metrics → verdict | — | SDK: `VerdictOp` |
| `logic/spectral/feature` | peak / band features | numpy | SDK: `SpectrumFeatureUtil` |
| `logic/spectral/spectrumToColor` | spectrum → colour | (!) QColor → S1b | SDK: `EvaluationColorUtil` |
| `util/SpectralColorUtil.py` | colour maths | (!) QColor → S1b | behind the façade |
| `acquisition/RobustReductionLogicModule` | Tukey biweight, sigma-clipped mean | numpy | the seam nick — science misfiled under `acquisition/` |
| `logic/spectral/smoothSpectrum` | `savgol_filter` | **scipy** | the chain |
| `logic/spectral/removeBaseline` | morphological opening | **scipy** | the chain |
| `logic/spectral/rebinSpectrum` | rebin 380–780 / 1 nm | numpy · spectres | the chain |
| `logic/spectral/normalizeSpectrum` | normalize | numpy | the chain |
| `util/SpectrumUtil.py` | **the chain façade** | — | follows its chain |
| `util/SpectralWorkflowUtil.py` | workflow phase/step helpers | `SpectralJob` → S0 | **#3** — plugins mutate `SpectralWorkflow` |
| `acquisition/ExtendedRoiLogicModule` | ROI extension / clamp | numpy | **#4** — M1's *"plugin ROI clamp"*; the plugin declares the ROI |
| `logic/spectral/spectralLine/` (8) | peak selection by prominence / intensity / colour | **scipy**, no Qt | **#5** — generic peak selection; calibration-only use today |
| ~~`util/SpectrallineUtil.py`~~ | ~~spectral-line helpers~~ | — | **RETRACTED by S3a** — DB-bound via `SpectralLineMasterDataUtil`, and calibration-only. **Stays in the app.** See "What S3a's re-derivation actually caught". |
| `logic/spectral/synthesis/` (8 of 9) | LED-reference + oil-sample synthesis, demo oils | numpy | **#6** — physics; feeds the future LED-optimisation task |
| `plugin_sdk/` | the façade | — | **is the contract** |
| `view/…/render/WorkflowItemVisitor` | M1 visitor seam | none — **already Qt-free** | misfiled under `view/` |
| `view/…/render/MatplotlibWorkflowRenderer` | PDF render | matplotlib — **already Qt-free** | misfiled under `view/` |
| `view/…/render/WorkflowReportBuilder` | PDF build + embed JSON | (!) QImage → S2 | misfiled under `view/` |

### → stays in `spectracsPy` (the app)

| Package | Why |
|---|---|
| `logic/spectral/video/` (4 Qt, 1 cv2) | capture threads |
| `acquisition/ImageSpectrumAcquisition*` | QImage / qGray → pixel spectrum |
| `acquisition/device/calibration/` (all 8) | **#1** — device calibration; semantics beat the coupling rule |
| `synthesis/SpectrumToVirtualImageUtil` | QImage — the virtual camera |
| `logic/spectral/workflow/` | `SpectralWorkflowEngine`: session + plugin import = host concern |
| `logic/spectral/importSpectrum/` | **#7** — file I/O on the legacy `SpectralJob` path |
| `util/SpectralLineMasterDataUtil.py` | imports `logic/persistence` → DB-bound |
| `logic/persistence/**` (9 pkgs) | DB access |
| `logic/appliction/**` | Qt, platform, docmode, Hough |
| `logic/{session,connection,settings,server,model/util,playground}` | session, Pyro client, app config |
| `view/**` (minus the render seam), `controller/**` | Qt / pyqtgraph. The Qt-free-*looking* ones are genuine views: the "Interpolation" ViewModule is pyqtgraph + `poly1d`; `EvaluationResultRenderer` is an 11-line façade over `QtWorkflowRenderer`; `ChartThemeUtil` / `SpectralJobGraphViewModule` are pyqtgraph |

### → `spectracs-plugins` (S5)

`logic/spectral/plugin/dev/` (`DevSpectralPlugin`) · `logic/spectral/plugin/pumpkin/` (`PumpkinOilPlugin`).
**Destination path re-homed at S5 (Option B):** `logic/spectral/plugin/*` → **`plugins/*`** — the codeRef stops
lying about a `logic` tier the file no longer lives in. Rationale + migration in the S5 subsection before §6.

### What S3a's re-derivation actually caught (2026-07-17)

**§5 was wrong about `SpectrallineUtil`, and this is exactly why S3a re-derives by grep.** §5/#5 put it in `-core`
alongside `spectralLine/`. It cannot go: `createSpectralLinesByNames()` reads **master data from the DB** via
`SpectralLineMasterDataUtil` (→ `logic/persistence`), and **every caller is calibration** — which stays in the app
by decision #1. **`SpectrallineUtil` stays in the app.** (`spectralLine/` itself is clean and still moves.)

*Why the audit missed it:* the original §5 grep truncated its output at `head -7` and the
`SpectralLineMasterDataUtil` import is on **line 9**. I never saw it. The lesson in §5's blockquote — *"the tables
are the argument, not the manifest"* — was written before this happened and then immediately proved by it.

**Two pre-existing defects surfaced by S3a's exhaustive import sweep (198 modules), neither caused by it:**
- **`Polisher.py` has been broken since the namespace migration.** It does `from base import SingletonQObject` —
  a path that stopped existing at commit `9dfa957` ("added all modules to namespace sciens"). Nobody noticed
  because it is **dead**: its only caller is a **commented-out line** in `PageLineEdit.py`. Left alone; recorded.
- The `.lighter()` regression below.

**A regression S1b shipped, caught by S3a's click-through — not by any test.** `PlaygroundViewModule:156` called
`measuredColor.lighter(160)`; `spectrumToColor` now returns a `SpectralColor`, which has no `lighter()`.
**S1b's own API inventory listed `.lighter()` and it was dismissed without being chased.** 106 unit tests never
touched the Playground; one navigation found it. Fixed in the **view** — `mkPen` wants a QColor anyway and
`lighter()` is a presentation concern, so the host converts rather than `SpectralColor` growing a faithful port of
`QColor::lighter` (HSV value scaling with its saturation-overflow quirk). Qt adapters belong in the host (S2's rule).
A re-run of the inventory across *all* tracked files confirms `.lighter()` was **the only** missing accessor.

### Retracted by S3b: "tests move with their subject"

S3b originally said the 12-of-17 tests that import the moving science would follow it into `-core`. **Wrong — it
contradicts this project's own convention.** Every tier's tests already live in `spectracsPy/tests/`: `-model` owns
`Spectrum`, `SpectralWorkflow`, `DbPlugin` and every view-model, and has **zero** tests; `-base` and `-server` have
none either. All 16 suites are in the app and test all tiers from there.

So the tests stayed. Consequences, all good: `-core` needs no venv, no `requirements.txt` and no runner — and the
QColor-vs-`SpectralColor` characterisation suite, which **inherently needs Qt** (its whole point is proving the two
dialects agree), has no Qt-free repo to be awkward in. That question consumed two rounds of analysis and was
dissolved by one `ls`.

Revisit only if `-core` gains its own CI. Note the spec only ever planned CI for **`spectracs-plugins`** (S5).

### S7 (NEW, DESIGN) — the `logic/` tiers are tangled across every repo boundary

Found while ducking S4 (2026-07-17), then **widened** when a full five-repo audit showed the first look had caught
**half** of it. The §1 tier diagram is aspirational, not descriptive.

**Every edge, measured:**

```
  model  -> app        3 files   *** VIOLATION ***
  server -> app        1 file    *** VIOLATION ***
  app    -> server     2 files   *** VIOLATION ***   (so app <-> server is MUTUAL)

  model  -> base      10   ok        core -> base     5   ok
  core   -> model     18   ok        app  -> core    11   ok
  app    -> base      21   ok        app  -> model   59   ok
  server -> model      2   ok
```

**1. `model -> app` (3 files).** `-model` reaches into the app — including the **controller** — closing a cycle:

```
  -model/logic/model/util/SpectrometerProfileUtil.py
        imports  controller.application.ApplicationContextLogicModule   ─────► THE APP
        imports  SpectrometerCalibrationProfileUtil  (-model)
                     └─ imports  logic.spectral.util.SpectrallineUtil   ─────► THE APP
                                      └─ imports  SpectralColorUtil     ─────► -core
                                                       └─ imports SpectralColor ──► -model   (cycle)
```
Also `InstrumentAuthoringLogicModule` → the app's `SpectralLineMasterDataUtil`.

**2. `app <-> server` — MUTUAL, and the worse one.**
- `SpectracsPyServerClient` does `from sciens.spectracs.SpectracsPyServer import SpectracsPyServer` — **the client
  imports the server class it is supposed to reach over Pyro.** The point of Pyro is that the client holds a
  *proxy*, not the implementation; this makes the desktop app unbuildable without the server's source.
- `SpectracsPyServer.py` imports **six** app modules: `SqlAlchemySerializer`, `SpectrometerUtil`,
  `SpectralLineMasterDataUtil`, `LoginLogicModule`, `UserAdminLogicModule`, `UserSeedLogicModule`.

Neither repo stands alone.

**Proven, not argued** — with only `-model` + `-base` importable, from a **neutral cwd**:

| `-model` class | |
|---|---|
| `Spectrum` · `SpectralColor` · `SpectralWorkflow` · `EvaluationResult` · `DbPlugin` | **import standalone ✅** |
| `SpectrometerProfileUtil` | **FAIL** → needs `sciens.spectracs.controller` |
| `SpectrometerCalibrationProfileUtil` | **FAIL** → needs `logic.spectral` |
| `InstrumentAuthoringLogicModule` | **FAIL** → needs `logic.spectral` |

**What this does and does not threaten.** `-core` is genuinely clean (S3a: 0 violations, re-verified), and
`-model`'s **data** classes stand alone — and those are exactly what a plugin and a LIMS addon consume. So the
plugin story and S3b's goals hold, and **S7 blocks neither S4 nor S5**. What is tangled is the **`logic/` trees**:
`-model` carries server-side logic that reaches into the app, and the app and server import each other. None of it
is "model" or "server" in the sense the repo names claim — §5 already noted `-model` is "model *plus* server-side
logic". The likely fix is that this logic belongs in neither repo where it currently sits.

**Scope: 6 files, all pre-existing.** A fourth `model -> app` edge was **mine and is FIXED** (S0 follow-up,
6c9be9a/54a1ec9): S0 moved `SpectralVideoThreadSignal` to the app and left `…WavelengthCalibrationVideoSignal` in
`-model` importing it — invisible to S0's `grep -l PySide6` because it inherits Qt through `VideoSignal` rather
than importing it.

**Deliberately NOT folded into S4.** S4 is a small integration gate; untangling three repos is its own work.

**Lesson for the checkers — every automated check in this spec has been pointed one way and been wrong for it.**
S3a's asked only *"does **core** import outward?"*, never *"does **model** import upward?"*. S0's move list came
from a direct-import grep and missed transitive Qt (twice: `.lighter()`, and this signal). The isolation probe was
contaminated by `cwd` on `sys.path` until `""`/`"."` were stripped. The Qt gate matched the word *pyqtgraph* in a
**comment**, three times. A stale `.pyc` made shipped code look buggy. **The harness has been less reliable than
the code it checks.** Check every direction, and verify the harness before trusting its verdict.

### Dead chain found by S1b's duck (2026-07-17) — record, don't fix here

One unfinished method keeps an entire dependency alive:

```
SpectralLinesSelectionLogicModule.__validateByColor   #todo:unfinished — UNREACHABLE
        |  (the only caller of)
        v
SpectralColorUtil.getColorDifference                  — therefore DEAD
        |  (the only importer of)
        v
colormath                                             — therefore a DEAD DEPENDENCY in requirements.txt
```

- **`__validateByColor` is unreachable.** `execute()` dispatches on exactly three parameter types
  (`…ByProminenceParameter`, `…ByIntensity`, `…ByPixelIndex`) — **there is no `SelectByColorParameter`
  branch**. The method is name-mangled private, has no other caller, is marked `#todo:unfinished`, ends in
  `pass`, and would **crash if reached**: it passes `selectedLine.pixelIndex` (an `int`) where a colour goes,
  and discards the result.
- **`getColorDifference`** (the colormath/ΔE-2000 path) therefore has no live caller. Its lazy-import defence —
  the `colormath → networkx → bz2` p4a workaround — guards a path nobody walks.
- **`colormath`** is imported by `SpectralColorUtil` and nowhere else, so it is dead weight in the app's
  dependency set. Precedent: [`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md) §174 already dropped
  `luxpy` and `pandas` for exactly this reason.

**Deliberately NOT done in S1b.** Deleting dead code inside the phase that rewrites calibration-critical colour
maths mixes two risks — the very thing S1a/S1b and S3a/S3b were split to avoid. S1b ports `getColorDifference`
mechanically to `SpectralColor` and changes nothing else. The deletion is its own decision, on its own day.

### Smells found, not blocking

- **`SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule` calls `find_peaks` inline** — science in a
  view. **#9:** push into a logic module opportunistically; app-side either way, so it does not block the tiering.
- **`logic/appliction` is a typo**, load-bearing across the tree. **#8:** rename to `logic/application` **inside
  S3a**, which is already a mass import rewrite — doing it standalone pays the same merge pain twice.

### S5 (DESIGN, settled 2026-07-17) — extract `spectracs-plugins`

**The code check that reframed S5.** Both plugins already import **`plugin_sdk` only** (+ stdlib `colorsys`):
`PumpkinOilPlugin`, `DevSpectralPlugin`. The isolation S5 exists to *prove* is already *true* — the lint gate is
green **before** the move. And they are **2 files**: no shared plugin base in the app, no `__init__` payloads. So
S5 is mechanically nothing like S3b's 67-file extraction; the real work is the **two decisions the move forces**.

#### Decision 1 (settled: Option B) — the codeRef moves now, because M3 is about to freeze it

The plugin's identity string is not just an import path; it is a **persisted, bound** identity in four places:

| Where | File | Role |
|---|---|---|
| **Server DB seed** | `spectracsPy-model/…/user/UserSeedLogicModule.py:26` | seeds `DbPlugin.codeRef` (idempotent, skip-if-exists) |
| Session dev-bypass fallback | `logic/session/CurrentUserSession.py:67` | resolves the bound plugin at login |
| Bench selector import | `view/settings/development/DevMeasurementBenchViewModule.py:17-18` | direct `from …plugin.pumpkin… import` |
| Login binding lookup | `-model/…/instrument/InstrumentAuthoringLogicModule.py:100` | `DbPlugin.codeRef == pluginCodeRef` |

**M3-B0 makes `(codeRef, version)` the immutable, signed DB key** ([`SPEC_plugin_distribution.md`](SPEC_plugin_distribution.md)
§1). The current string embeds **`logic`** — a lie the moment the file leaves the app's logic tier. So this is the
**last free moment** to fix it: after B0 seals rows, a codeRef change is a breaking *republish*, not a `git mv`.
Re-home (same shape as §1c's plugin_sdk-export rule — a contract is frozen the instant it is depended on):

```
old:  sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin
new:  sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin
      sciens.spectracs.plugins.dev.DevSpectralPlugin.DevSpectralPlugin
```

**The migration Option B carries — a data change, not just a code change.** The seed is idempotent *keyed on
codeRef*. Change the string alone and the seed **inserts a second row**, orphaning the old one **and any instrument
setup bound to it** → the binding then resolves a codeRef whose module no longer exists. So the change must
**UPDATE the existing `DbPlugin.codeRef` in place** (in dev, reset + reseed is equivalent — memory's *"restart
server to seed"*; the SENAITE runbook means a **persisted** server DB really holds the seeded row, so this is a real
step, not a paper one). Cheap **only because M3-B0 has not yet made rows immutable** — the same fact that makes B
now-or-never.

**The rename is a mass path rewrite, not "4 sites" — same shape as S3a's `appliction→application`.** The four in the
table are the *persisted-identity* sites; a grep for the old dotted path also finds it across **6 test files**
(`test_frame_provider_burst`, `test_stale_calibration_recovery`, `test_pumpkin_workflow_end_to_end` **import** it;
`test_step_bar_widget_offscreen`, `test_pumpkin_wizard_offscreen`, `test_workflow_wizard_persistence_offscreen` hold
it as a `PLUGIN_CODE_REF` **literal**). So step 1 is *"replace every occurrence of the old dotted path across all
repos, then the in-place DB update"*; `InstrumentAuthoringLogicModule:100` is a query, no literal. `DevSpectralPlugin`
has **no** seed row (injected transiently, no session codeRef) → its move is a pure import-path change, no migration.

#### Decision 2 (settled: Option A) — plugin CI synthesizes its input from `-core`; it does not run the engine

The existing `test_pumpkin_workflow_end_to_end` chain splits **exactly on the core/app line**:

```
 synthesize ref Spectrum ─┐   [CORE — pure science, already in -core]
 synthesize sample Spectrum┘   LedReferenceSynthesis · OilSampleSynthesis · PlaygroundDemoOils
        │
        ▼
 encode → QImage → engine( qGray + CurrentUserSession-calibration + ImageSpectrumAcquisition )   [APP — host]
        │
        ▼
 acquired Spectrum → plugin hooks ( mean→T→A→colour→verdict )   [PLUGIN — plugin_sdk only]
```

`SpectralWorkflowEngine` is genuinely **host** — `qGray` (Qt), `CurrentUserSession`, the camera-acquisition module;
`SpectrumToVirtualImageUtil` emits a `QImage`. Neither may move to `-core`, and neither belongs in a plugins-repo
test. So testing splits in two:

| Tier | Lives in | Feeds the plugin | Depends on |
|---|---|---|---|
| **T1 full end-to-end** *(exists)* | **app CI** (`spectracsPy/tests/`) | synthesize → QImage → `engine.runAll` → assert verdict | engine + synthesis = app (fine — plugin is namespace-merged there) |
| **T2 plugin-boundary** *(new, S5)* | **`spectracs-plugins` CI** | synthesize ref+sample `Spectrum` from `-core`, call the plugin hooks directly → assert `EvaluationResult` | `plugin_sdk` + `-core` synthesis — **app absent** |

This reconciles with **"tests stayed in the app"** (§5, the S3b retraction): `-core`/`-model`/`-base`/`-server` keep
their tests in `spectracsPy/tests/`, and **`spectracs-plugins` is the one tier the spec always planned to give its
own CI** — so T2, and only T2, lives in the new repo. T1 stays put; the engine can't leave the host.

**Why Option A is legal against the lint gate.** The gate constrains **plugin production source** (`plugin_sdk`-only);
it does **not** constrain *tests*. `-core` is a declared dependency of `spectracs-plugins`, and its synthesis
modules are pure science — so T2 may synthesize its input from `-core` with **no committed fixture** and no app
import. *(Deferred alternative: a frozen `Spectrum` fixture models an SDK-only **external** author — revisit when
M3 opens third-party distribution; not needed while the plugins are first-party.)*

#### Mechanize the lint gate — don't leave it a PyCharm property

§8b calls *"app code absent"* a **dev-time** PyCharm property that must not be read as a runtime guarantee (runtime
is one merged tree). Make it a **CI check**, with the PyCharm view as the human echo:

```
grep -rE 'from sciens\.spectracs\.' spectracs-plugins/sciens | grep -v 'plugin_sdk'   # MUST be empty
```

(`colorsys` is stdlib → fine.) This is the enforceable form of the "app code absent" verify.

#### The S4-shaped integration follow-through — the move is done only when the app still loads them

- **`stage_app_src.sh`** — add `spectracs-plugins` to the rsync loop (§8b: literally one line). The `android/server`
  + `android/spike` `app_src` mirrors are *generated*, so they regenerate; the committed vendored copies refresh.
  **⚠ Those mirrors are committed *and already stale*** — `android/spike/app_src/…/CurrentUserSession.py` carries the
  fallback at line 60 vs. the live source's 67, i.e. they drifted before S5. So they must be **re-staged, never
  hand-edited** (a hand-edit leaves the old codeRef in the merged tree the APK actually runs); re-run staging and let
  it overwrite, and clean any copy left under the old `logic/spectral/plugin/` path.
- **both PyInstaller `*.spec` `pathex`** — S4's fix (still unproven by an actual build) now spans a third repo.
- **desktop PYTHONPATH run recipe + PyCharm content root** — mirrors `b4dcfc1` for `-core`.

#### Ordering — prove before you move (S3a/S3b ethos, one phase)

Only 2 already-clean files, so **no repo-level 5a/5b split** — but sequence so each step is verifiable while still
cheap to undo:

1. **In-tree rename** `logic.spectral.plugin.* → plugins.*` + the four literal sites + the in-place DB migration.
   App still boots; **T1 green** under the new codeRef.
2. Add the **T2 synthesize-from-core** plugin test **in the app tree**; green.
3. **Extract** `spectracs-plugins` (`filter-repo`, history intact), delete from app, wire staging / `pathex` /
   PYTHONPATH / PyCharm, and **move T2 into the new repo's CI**.

Find out you were wrong at step 1, not after the checkout.

#### Verify

- New repo opens in PyCharm: `plugin_sdk` + `-core` resolve, **app code absent**; the grep gate returns empty.
- **T2 CI:** synthesize → plugin hooks → `EvaluationResult`, importing `plugin_sdk` + `-core` only (app not importable).
- **Fresh clones of all 6 repos** boot the app; both plugins load via namespace-merge and drive a run (bench
  selector **and** a Pumpkin login).
- **T1** (`test_pumpkin_workflow_end_to_end`) still green in the app under the new codeRef path.
- **Server DB:** no orphaned old-codeRef row; the bound setup resolves the new path.

## 6. Phases

| Ph | Change | Where | Verify |
|---|---|---|---|
| **S0** ✅ | **DONE 2026-07-16.** Moved the Qt app-plumbing out of `-model`/`-base` into the app — **11 files**: `SingletonQObject`, `SpectralJob`, `SpectralVideoThreadSignal`, `DbEntityChangedSignal` (+ `UserSignal`, `SpectrometerProfileSignal`), `HoughLinesVideoSignal`, `NavigationSignal`, `ApplicationStatusSignal`, `VideoSignal`, `VirtualSpectrometerSettings`. Kept their `QObject`; kept their package paths → **zero import changes**. | `-model` → `spectracsPy` | ✅ all 11 import; ✅ `-model`+`-base` import with **PySide6 blocked** (0 dragged); ✅ real `Signal(NavigationSignal)`/`Signal(ApplicationStatusSignal)` still marshal; ✅ real app boots, Home→Settings→Home→Playground→Home, status bar renders text+progress; ✅ 34 targeted tests pass. `grep -rE 'PySide6\|pyqtgraph' -model/ -base/` → **only `SpectralLine`** (S1b takes it). |
| **S1a** ✅ | **DONE 2026-07-17.** Characterisation tests pinning the **current** QColor behaviour of `SpectralColorUtil.wavelengthToColor` / `hueSimilarity` / `channelDominance`. **63 tests, no production change.** | `tests/test_spectral_color_util_characterisation.py` (NEW) | ✅ 63 pass against today's code; ✅ **verified by mutation — 8/8 mutants die**, incl. the achromatic trap, both gate thresholds, gamma, the clamp and the hue wrap-around. The red-vs-grey trap is pinned: current **0.0**, naive port **1.0**. |
| **S1b** ✅ | **DONE 2026-07-17.** `SpectralColor` (Qt-free, in `-model`) replaces QColor in `SpectralColorUtil`, `SpectrumToColorLogicModule(+Result)` and `SpectralLine.color`. Deliberately **QColor-shaped** (Option A): the camera still hands `hueSimilarity` a QColor from the app-side calibration path, so the two dialects must be interchangeable — incl. `hueF() == -1` for achromatic. | `-model` (new type + `SpectralLine`) + `logic/spectral/util` + `/spectrumToColor` | ✅ **S1a's 63 tests passed UNCHANGED** — the proof; then parametrised over **both** dialects (75 tests) because passing unchanged only proved *QColor-in* still works. ✅ **13 mutants die**, incl. the achromatic trap on the new type. ✅ 4096-colour RGB-cube sweep vs QColor: **0 mismatches**. ✅ `-model`+`-base` import with **PySide6 blocked**. ✅ 106 tests; ✅ Qt renders a stylesheet from `SpectralColor.name()`. |
| **S2** ✅ | **DONE 2026-07-17.** Not a de-Qt — a **split**. The class declared itself the host bridge (*"Runs on the host side (Qt allowed)"*) and had **two Qt ends pointing opposite ways**: `__qImageToPil` (QImage **in**) and `previewPixmaps()` (QPixmap **out**). Both moved to the host; the Qt-free ~80% stayed. The conversion now happens where `.image` is set (bench view :531) — which is what `SpectrumCaptureView`'s docstring always said: *"reportImage is the Qt-free rendition the host derives from .image"*. `previewPixmaps()` was **deleted, not ported** — `rasterize()` is already Qt-free, so the host wraps it in 3 lines via the new `figures()`. | `view/../render/WorkflowReportBuilder` → Qt-free; `DevMeasurementBenchViewModule` gains both Qt ends | ✅ **A full PDF built with PySide6 BLOCKED from the import system — the LIMS-addon scenario, proven not argued.** ✅ M2's gate holds: pages render, `workflow.json` + `capture_sample.png` still embed. ✅ preview renders page-for-page. ✅ 107 tests. |
| **S3a** ✅ | **DONE 2026-07-17.** Re-derived the move list by grep and **enforced the seam in-tree**: the core-bound set is **67 files** and now imports only `-model`, `-base`, itself and externals — **0 violations, 0 Qt**. Renamed `logic/appliction` → `logic/application` (52 files; every occurrence was the dotted module path). No files moved between packages: paths are already final (S3b only changes *repos*), so S3a's real work was **severing core→app edges**. | `spectracsPy` | ✅ **§5 was wrong and the grep caught it** (below). ✅ 197/198 modules import (the 1 is pre-existing dead `Polisher`). ✅ app boots; Settings/Playground/Home navigate. ✅ 112 tests. |
| **S3b** ✅ | **DONE 2026-07-17.** `spectracsPy-core` exists: **67 files, 24 commits, history intact** (`clone` + `filter-repo --path`×67; `git log --follow`/`blame` reach back through S1b to 2026). Deleted the matched 67 from the app. Phase 0 first (f203ed0): re-homed the render trio out of `view/` → `logic/spectral/report/`, and taught **26 files** the `-core` path — the spec said "ONE line in stage_app_src.sh"; that line is real, the other 26 weren't in the plan. | new repo + `stage_app_src.sh` + 26 PYTHONPATH sites | ✅ **fresh clones of all 5 repos boot the app** (131 modules, only pre-existing dead `Polisher` fails). ✅ all 67 `-core` modules import with **PySide6 blocked**; `-core` has **no `view/`**. ✅ app navigates Settings→Playground→Home, no uncaught exceptions. ✅ 112 tests. |
| **S4** ✅ | **DONE 2026-07-17 — renamed: it is the INTEGRATION GATE, not a change.** S3b already made the app depend on `-core`, and the two Qt renderers never moved; S4's stated content was a no-op. Its real content turned out to be three leftovers: **both PyInstaller specs** (`pathex` named only `-model`; the Windows one was **empty** — my S3b sweep missed them, different syntax), **`stage_app_src.sh`'s message** (staged 5 repos, said 4 — my bug), and **`-core/requirements.txt`** (deps were prose in the README). | `*.spec` · `stage_app_src.sh` · `-core` | ✅ real entrypoint `spectracsMain.py --phone` boots on `-core`; ✅ renders at 412×883, looked at it; ✅ Android staging includes `-core` (316 .py); ✅ 106 tests. **RIG-VERIFIED by Edwin 2026-07-17: the measurement bench runs end-to-end on `-core`** — the one gate no headless path could reach (the bench refuses virtual devices). Still unverified: the APK (deferred) and a PyInstaller build (unused today, so the `pathex` fix is *unproven*). |
| **S5** *(DESIGN, settled 2026-07-17 — see the S5 subsection before this table)* | **`spectracs-plugins`** repo — the 2 already-`plugin_sdk`-clean plugins move out. **(B)** re-home `logic.spectral.plugin.* → plugins.*` **now** (last free moment before M3-B0 freezes the codeRef) + **in-place `DbPlugin.codeRef` migration**. **(A)** new **T2 plugin-boundary CI** synthesizes its `Spectrum` from `-core` and calls the hooks directly — the app-coupled `engine.runAll` (T1) **stays in the app**. Add to `stage_app_src.sh` so they still ship. **Not blocked by M3** (§8b). | new repo + staging + both `*.spec` `pathex` + PYTHONPATH · in-place DB migration | grep gate `from sciens.spectracs.*` ∖ `plugin_sdk` **empty** (the enforced form of "app code absent"); T2 runs `plugin_sdk`+`-core` only; **6 fresh clones** boot + both plugins load via namespace-merge (bench selector + Pumpkin login); T1 still green under the new codeRef; no orphaned old-codeRef DB row |


Run order is **S0 → S1a → S1b → S2 → S3a → S3b → S4 → S5**. S0/S1b/S2 make `-model` and the science genuinely
Qt-free; S3a/S3b are the move; S5 is the payoff.

**Why S1 is split** — see §4d. It is the only phase here that is *real code* rather than a file move, it rewrites
maths that **wavelength calibration** depends on, and that maths has **no test coverage today**. S1a pins the
current behaviour while the QColor code is still there to pin it against; S1b then proves the swap changed
nothing. Same shape as S3a/S3b: prove first, change second.

**Why S3 is split.** It fused two unlike risks: *does everything still import and run* (risky, but verifiable and
undoable) and *does it live in its own repo* (mechanical, but irreversible). S3a proves the reorganisation while it
is still a `git mv`; S3b only then pays for a new checkout. Find out you were wrong in S3a, not S3b.

**S0 absorbed the old S6** (2026-07-16). They were the same job asked twice: the old S0 deleted `QObject` bases while
the old S6 moved Qt payloads to the app — but §4b shows *all nine are the move*, and none is a deletion. Merging them
also un-defers the work: the old S6 waited on the LIMS addon because it looked like real refactoring, whereas a pure
relocation has no reason to wait. **S0 is mechanically bigger than the old one (9 files vs 4) but semantically
smaller — nothing changes behaviour.**

> **Non-phase, and the only irreversible decision here — #2: `plugin_sdk` does NOT gain `SmoothOp` / `RebinOp` /
> `NormalizeOp`.** The conditioning chain moves to `-core` as *code*; the façade's exports do not change. Every other
> item in this spec is a `git mv` you can undo next week — an exported op is frozen the moment a plugin imports it.
> Adding them later is additive and free; that is precisely why there is no rush. See §1c.

---

## 7. Ordering against plugin distribution (M3)

**The tracks are near-independent.** M3's publish step is a file picker that signs bytes — it does not care which
repo the file came from. And `sciens.spectracs.plugin_sdk` keeps its import path across the move, so source
published *before* this spec still resolves *after* it. Either order works.

**Recommendation: this spec first**, for four reasons — none of them a hard blocker:

1. **This gets harder every week; M3 doesn't.** A re-tiering touches every import in the tree, so its cost grows
   with the code. M3's `DbPlugin` migration is the same size whenever it runs.
2. **Three customers vs one.** M3 buys APK-free updates — real, but least urgent, since Edwin is the only author
   and rebuilds APKs today anyway.
3. **It makes M3's story coherent.** Publishing source *from the app repo*, into a DB, to be loaded by the same app
   that already contains that code, is a strange demo. Publishing from a plugins repo the app cannot see is the
   feature.
4. **M3's D0/A2 (SDK version) wants a settled SDK** — not because S1 breaks it (it doesn't), but because the
   namespace is about to relocate and acquire a real boundary.

**What flips it:** if rebuilding APKs starts actually hurting, do M3 first — it costs almost nothing later.

`spectracs-plugins` (S5) is this spec's, not M3's — M3 §5 bundled the repo with the publish tool; they're separate
concerns. M3 keeps the publish path (which extends `PluginViewModule`) and the CI-proof idea rides here.

---

## 8. Open items

- **`-model`'s SQLAlchemy** (L3's Qt half is closed — §4b — and is now just **S0 + S1b**). Does `-model` also deserve
  a split? A SENAITE addon wants the data classes and view-models, **not** the app's DB entities. Decide when the
  addon is real; not a blocker for S0–S5.
- **Where the S0 files land.** Recommended: **keep their package paths** (e.g.
  `sciens.spectracs.model.application.navigation.NavigationSignal`) and simply relocate the file to the app repo —
  zero import changes across ~40 call sites, and `sciens/spectracs/logic/` **already** spans both repos this way
  (app: 11 subdirs, `-model`: 8), so it is the established convention. **Cost:** a package path no longer tells you
  which repo owns the file — already true of `logic/` today. **Alternative:** re-home them under an app-owned path,
  which is semantically cleaner but churns every call site. Cheap either way; decide at S0.
- **When to expose the conditioning chain via `plugin_sdk`** (#2 says: not yet). The trigger is a real plugin that
  needs to condition its own spectrum. Additive when it happens; §1c explains why waiting is free and acting is not.
- **Calibration's home** (#1 says: app). Revisit only if a LIMS addon ever needs to re-derive a wavelength
  calibration — currently not a thing. 7 of its 8 files are Qt-free, so the move stays cheap.
- **The LIMS addon is still speculative** — `senaite-spectracs` has no spec and no stated requirements, so its needs
  here are *guessed*. Two of §0's three drivers (plugin isolation, an SDK boundary before M3 freezes it) are real
  today and carry the tier on their own. But **S2's only beneficiary is that addon**: if it never happens, S2 bought
  nothing. Cheap enough to accept knowingly — just don't let it silently become the justification for more.

### 8b. Closed by the 2026-07-16 duck (recorded, not open)

- **Packaging — SOLVED, and it was never a question.** `android/spike/stage_app_src.sh` **rsyncs `sciens/` from each
  sibling repo into one merged tree** (`for repo in spectracsPy-model spectracsPy-base spectracsPy-server
  spectracsPy`). So the repos are **namespace-merged, not pip-installed** — `-core` is **one line** in that loop, and
  so is `spectracs-plugins`. Desktop does the same via the PYTHONPATH run recipe. No pip packaging is needed for
  S0–S5; revisit only if `senaite-spectracs` becomes real and wants a wheel.
- **Android `app_src` mirrors — same answer.** They are *generated* by the staging script, not hand-vendored. Adding
  a repo to the loop keeps them in step by construction. (S3b's verify covers it.)
- **S5 is NOT blocked by M3's loader.** An earlier draft worried that plugins leaving the app repo would strand
  `SpectralWorkflowEngine.importPlugin`. It does not: staging merges `spectracs-plugins` into the shipped tree, so
  plugins keep loading by import until M3-B3 replaces that with the DB loader.
- **…which makes the isolation *development-time*, not runtime.** At runtime the APK is **one merged `sciens`
  tree**, so a plugin *can* reach app code. That is consistent with §1c (hygiene, not a sandbox) — but S5's "app code
  absent" verify is a **PyCharm-project property**, and must not be read as a runtime guarantee.

---

## Verification (when implemented)

1. `grep -rE 'PySide6|pyqtgraph|shiboken' spectracsPy-core/` returns **nothing**. (All three spellings — the audit's
   first pass grepped only `PySide6` and pyqtgraph slipped through; see §5.)
2. `grep -rE 'PySide6|pyqtgraph' spectracsPy-model/ spectracsPy-base/` returns **nothing** (after S0 + S1b) — so a
   LIMS addon installs without PySide6.
3. `plugin_sdk.__all__` is **unchanged** by this spec — no `SmoothOp`/`RebinOp`/`NormalizeOp` appears (#2). The
   chain's code moves; the contract does not.
4. The app boots, the bench runs a workflow end-to-end, and the M2 PDF still exports with embedded JSON.
5. `spectracs-plugins` opens in PyCharm with the SDK resolvable and **no app code on the path**; its CI runs
   `engine.runAll` headlessly and passes.
6. A plugin's source is byte-identical before and after the move (proving the namespace was preserved).
