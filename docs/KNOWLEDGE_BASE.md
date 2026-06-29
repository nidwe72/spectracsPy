# Spectracs — Knowledge Base

> Working notes on the Spectracs spectroscopy app, assembled while onboarding.
> Scope: the Python desktop app (`spectracsPy`) and its sibling repos. Last updated 2026-06-25.

## 1. What it is

A **PySide6 (Qt6) desktop application for optical spectroscopy with a DIY spectroscope**.
A camera images the light dispersed by the spectroscope into a spectral band; the app
extracts an intensity-vs-wavelength **spectrum** from that image, after a per-device
**calibration** that maps pixel position → wavelength.

## 2. Multi-repo layout

Under `/home/nidwe72/development/spectracs/` (four active sibling git repos):

| Repo | Role |
|------|------|
| `spectracsPy` | The PySide6 desktop app (this repo) |
| `spectracsPy-model` | Shared domain entities / SQLAlchemy ORM + model utils |
| `spectracsPy-base` | Shared base utilities (`Singleton`, `NetworkUtil`, …) |
| `spectracsPy-server` | Pyro5 server: spectrometer catalog + spectral-line master data |

Also present: `spectracs-hardware`, `spectracs-docs`, `spectracs-evaluations` (sample
data / analyses), and an older `spectracs-server` (predecessor).

`sciens` is a **PEP-420 implicit namespace package** (no `__init__.py`) split across the
repos; nothing pip-installs or `.pth`-links them, so launches must set `PYTHONPATH`.

## 3. Tech stack

- **UI:** PySide6 — QtWidgets, QtGui, **QtCharts** (spectrum plots), QtSvg. Dark stylesheet inlined in `spectracsMain.py`.
- **Imaging/signal:** OpenCV (`opencv-python-headless`), numpy, scipy.signal (`find_peaks`), scikit-image. Hough-line ROI detection.
- **Device I/O:** pyusb / cv2.VideoCapture; plus a **virtual** device that feeds a still image.
- **Persistence:** SQLAlchemy 2.0 + sqlalchemy-serializer, SQLite at `{appdata}/spectracsPy.db`.
- **Client/server:** **Pyro5** remote objects; serialization via marshmallow / SqlAlchemySerializer.
- **Spectrum import:** pyspectra (.dx/JCAMP); colormath (wavelength→RGB).
- venv: Python 3.10.12 at `spectracsPy/venv`. **`psutil` had to be added** (was missing; required by client/NetworkUtil).

## 4. Architecture (custom "…Module" pattern)

```
View (PySide6)  →  Controller  →  Logic  →  Persistence (SQLAlchemy/SQLite)
                                     ↘  Pyro5 client ⇄ SpectracsPyServer
```
- `controller/` — `ApplicationContextLogicModule` (Singleton hub), `NavigationHandlerLogicModule` (QStackedWidget routing, ~9 views), signals provider, settings.
- `logic/` — acquisition, Hough-line ROI, peak/line selection, spectral jobs/workflow, server client, image utils.
- `view/` — Qt widgets by screen (home, main, settings, spectrometer profiles, calibration, spectral jobs).
- Entry point `spectracsMain.py` → `MainContainerViewModule`.

## 5. Domain / DB object model (`spectracsPy-model`)

SQLAlchemy + SerializerMixin; UUID-string `id`; camelCase class → snake_case table.

**Type vs. instance split:**
- `Spectrometer` = device *type* → FK `SpectrometerVendor`, `SpectrometerStyle`, `SpectrometerSensor` (→ `SpectrometerSensorChip`). `SpectrometerSensor.isVirtual` (Boolean) marks the virtual device.
- `SpectrometerProfile` = user's *unit*: `serial` + FK to a `Spectrometer` + one `SpectrometerCalibrationProfile`.
- `SpectrometerCalibrationProfile` = ROI (`regionOfInterestX1/Y1/X2/Y2`) + polynomial coeffs A/B/C/D (`λ(px)=A·px³+B·px²+C·px+D`); owns `SpectralLine[]` (only real `back_populates`).
- `SpectralLine` (pixelIndex) → `SpectralLineMasterData` (reference catalog: name/nanometer/colors). `SpectralLine.color/prominence/intensity` are transient.
- `ApplicationConfig` → `ApplicationConfigToSpectrometerProfile[]` (assoc, `isDefault`) → `SpectrometerProfile`. `MeasurementProfile` → `SpectrometerProfile`.
- Runtime-only (NOT DB): `Spectrum`, `SpectraContainer`, `SpectralJob`, `SpectralWorkflow`. Only `DbSpectrum` is persisted.

```
ApplicationConfig ─(default?)─→ SpectrometerProfile ─┬─→ Spectrometer ─┬─→ Vendor / Style
                                                      │                 └─→ Sensor ─→ SensorChip
                                                      └─→ CalibrationProfile ──→ SpectralLine[] ──→ SpectralLineMasterData
```

## 6. Spectroscopy pipeline (camera → spectrum)

1. **Capture** — `VideoThread` (OpenCV), 1920×1080 MJPG; camera id hard-coded to 0.
2. **ROI detection (calibration)** — `HoughLineLogicModule`: auto-Canny + bilateral + HoughLinesP → top/bottom band bounds.
3. **Intensity profile** — grayscale, sample mid-row of ROI → `{pixel: intensity}` (`ImageSpectrumAcquisitionLogicModule`).
4. **Wavelength calibration** — polynomial A/B/C/D from the calibration profile → `{nm: intensity}`.
5. **Line detection** — scipy `find_peaks` + prominence (`SpectralLinesSelectionLogicModule`); ranked by prominence/intensity/pixel order.
6. **Output** — `Spectrum` + `SpectralLine`s grouped into `SpectralJob` (reference/sample/dark); plotted via QtCharts.

## 7. Virtual device

Driven by `SpectrometerSensor.isVirtual`. At capture the view reads
`profile.spectrometer.spectrometerSensor.isVirtual` → `VideoThread.setIsVirtual()`.
- virtual → `__captureVirtualFrame()` returns the stored `QImage` from `VirtualSpectrometerSettings.virtualCameraImage` (set via Settings → Virtual Spectrometer → **Set picture**; png/jpg/gif; held in memory, not a persisted path → likely lost on restart).
- physical → `__capturePhysicalFrame()` → `cv2.VideoCapture`.
- Both set `self.qImage` then `afterCapture()`, so downstream is source-agnostic.
- "Save physically captured images" toggle dumps frames to `{appdata}/tmpImages/test.png`.

## 8. Predefined spectrometers

Hard-coded in `spectracsPy-model/.../logic/model/util/*Util.py` with a **get-or-create** seeding
pattern at startup (not fixtures). Baseline three:
- **Spectracs Phantom** — sensor `VIRTUAX` (`isVirtual=True`) → the virtual device.
- **Spectracs InVision** — sensor `EXAKTA` (ELP 4K, USB `32e4:8830`).
- **Spectracs InLight** — sensor `AUTOMAT` (Microdia, USB `0c45:6366`).
Pyro5 `syncSpectrometers()` adds more on top.

## 9. Client/server (Pyro5)

- Host/port **hard-coded** in `spectracsPy-server/sciens/spectracs/SpectracsPyServer.py`
  (`NAMESERVER_PORT=8090`, `DAEMON_PORT=8091`, `DAEMON_NAT_HOST='sciens.at'`, `DAEMON_NAT_PORT=8092`).
  No config file / settings field / env var.
- `SpectracsPyServerClient.getProxy()` picks **local vs. remote at runtime**: if a process is
  listening locally on 8090 it uses that host, else `sciens.at`.
- Server exposes only `getSpectrometers()` and `getSpectralLineMasterDatasByNames()`.
- **Startup sync is now guarded** (2026-06-25): try local → remote → None; syncs no-op on None;
  `MainContainerViewModule.syncMasterData()` wrapped in try/except. App boots with no server.

## 10. Serial / register — UNFINISHED STUB

`SpectrometerProfile.serial` is **free text** the user invents (no validation, not sent to server).
`RegisterSpectrometerProfileViewModule` ("Download/Register calibration profile") only looks up a
profile **already in the local DB** by serial and links it (`:67-96`) — **no server download**.
Token files `spectracsToken.txt` / `spectracsServerToken.txt` are unreferenced.
Intended design (calibrate-on-server → download-by-serial) is only half implemented.

## 11. How to run

```bash
# Local Pyro server (dev) — terminal 1
cd /home/nidwe72/development/spectracs/spectracsPy-server
PYTHONPATH=".:../spectracsPy:../spectracsPy-model:../spectracsPy-base" \
  ../spectracsPy/venv/bin/python spectracsPyServer.py --local
#  (or ./runServer.sh)

# The app — terminal 2
cd /home/nidwe72/development/spectracs/spectracsPy
PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
  ./venv/bin/python spectracsMain.py
#  (or ./runApp.sh)
```
- App path needs `../spectracsPy-server` (client imports from it); server path needs `../spectracsPy`
  (it imports `logic.spectral.util.SpectralLineMasterDataUtil` from the app repo).
- `--local` binds nameserver:8090 + daemon:8091 to the LAN IP (`NetworkUtil` picks `wlp*`/`eth0*`).
- This dev box's shell has `DISPLAY=:0` (it is the desktop).

## 12. Usage click-path (virtual device)

1. Home → Settings → **Spectrometer profiles** → **Add** → pick "Spectracs Phantom Virtuax SlightHaze" → type any `serial` → **Save**.
2. Settings → **Virtual Spectrometer** → **Set picture** → choose `spectracsPy/testSpectra/cfl_philips_calibration.png`.
3. Calibrate (2 tabs): **Region of interest** → *Detect Region of Interest* (50 frames, Hough → x1/y1/x2/y2); **Wavelength calibration** → *Detect peaks* → assign known lines → A/B/C/D → **Save**.
4. Home → **New measurement** (tabs "Light"=reference, "Oil"=sample) → **Measure** → QtCharts: Intensities (averaged) / (raw) / Spectrum image.

**Test images** (in `spectracsPy/testSpectra/`, **currently NOT committed to git** — TODO: decide whether to
add these binaries later):
- `cfl_philips_calibration.png` (2592×1944) — original real capture; heuristic ✓. Origin `/home/nidwe72/data/migration/apollo-windows/spectracs#20/testPhilips.png`.
- `cfl_snowy_sharp_input.png` — clean sharp CFL band (from SpectralWorkbench spectrum 58696 `poly-Snowy-ADJ3ovc4`), framed Philips-style; heuristic ✓ (all 5 anchors, ~0.21 nm/px, guardrail passes).
- `cfl_reference_clean_input.png` — smeared/low-res band; heuristic mis-anchors violet 405 to the band onset → guardrail (correctly) flags it. Stress case.
- `cfl_reference_twinpeaks_fit.png` — visual ground-truth reference (white-dash line markers + nm axis); has overlays, not a clean input.
Note: `spectracs-evaluations/.../sample_step1_original.png` is a plotted CHART, not a usable frame.

**Heuristic status:** validated on TWO clean inputs (Philips + Snowy). RANSAC (both modes) tuned well in the
R0 spike but **still not producing correct fits in the actual app run** — open.

## 13. Known issues / loose ends

- **Calibration "Detect peaks" crashed when ROI (y1/y2) was unset** — `TypeError` at
  `ImageSpectrumAcquisitionLogicModule.execute` `y = int(y1 + (y2-y1)/2.0)` (None ROI).
  Root cause: the peak thread re-fetched the calibration profile from `ApplicationSettings`,
  which had diverged from the ROI-bearing object the calibration view edited (the profile is
  never persisted — `spectrometer_profile` had 0 rows). **Fixed 2026-06-25 (A+C):** the
  view now passes its own calibration model to the thread via `setCalibrationProfile()`
  (`...WavelengthCalibrationVideoThread`), and `onClickedDetectPeaksButtonNew` guards against a
  None ROI with a QMessageBox. Deeper fix (persist the profile + reload from DB = option B) still open.
- **Calibration spectral lines persisted orphaned → calibration looked empty after reload.**
  Root cause: `spectral_line` rows saved with `spectrometerCalibrationProfile_id = NULL` (duplicate/divergent
  transient calibration objects + bare `session.add+commit`). **Fixed 2026-06-25:** `spectralLines`
  relationship now `cascade="all, delete-orphan"`; `saveSpectrometerCalibrationProfile` flushes then
  explicitly links each line to the profile. Validated: lines linked on save, replaced (not duplicated)
  on re-run. One-time DB cleanup removed 10 orphan lines + 1 unreferenced calibration profile
  (backup at `~/.spectracsPy/spectracsPy.db.bak.*`). Confirmed working: saved calibration re-displays
  its spectral lines after navigating back.
- **Pixel↔wavelength matching (algorithm A — prominence anchors).** The heuristic anchored on absolute
  *intensity*, so the mercury green doublet (the two brightest peaks) mislabelled the right green peak as the
  red 611 line, collapsing calibration on virtual/over-exposed images. **Fixed 2026-06-25:**
  `SpectrometerWavelengthCalibrationLogicModule` now anchors green 546 first (single most-prominent peak), then
  red 611 (most-prominent peak right of green), then grows left for violet/blue/aqua — all by *prominence+position*
  (exposure-robust) instead of intensity. Validated on testPhilips: anchors 405→669, 436→887, 487→1225, 546→1618,
  611→2064 (dispersion ~0.148 nm/px, monotonic). Calibration samples full image width (not the ROI x-bounds),
  so violet/blue at x≈671/889 are seen even though the saved ROI starts at x=1216.
  - **No algorithm combo anymore** — "Detect peaks" directly runs the consensus (there was only one option).
    A gray **"help: expected detection"** button (left of "Detect peaks") opens a dialog showing
    `resource/expectedDetection.png` — a CFL reference (SpectralWorkbench `polySnowyADJ2steps`, cropped to just
    the corrected band + intensity curve + wavelength axis; the explanatory text/arrows and the upper captured
    band were removed) with **wavelength-coloured ticks** under the axis at the five app targets
    (405/436/487/546/611), documenting where the lines should appear. The dialog resolves the image by walking up
    from the module to find `resource/`.
  - **The matcher: a CONSENSUS** (`SpectrometerWavelengthCalibrationConsensusLogicModule`).
    The deliverable is the **five anchor lines** (405/436/487/546/611) — sufficient for the curve — but each is
    cross-checked to raise *confidence*: (1) **agreement** — does the advanced predict-and-snap cubic report the
    same wavelength at the simple-detected pixel? (independent for violet/blue/aqua; green/red agree by
    construction); (2) **colour** — is the band pixel the expected `mainColorName` bucket? (coarse, the camera
    isn't colour-safe — this is the independent check for red); (3) **green doublet** — are two close peaks
    (~4 nm) present? (the mercury-green fingerprint). Lines failing a check are surfaced as "low-confidence" so
    the user re-checks. Validated: all 5 confident on Philips + Snowy; the smeared stress image correctly flags
    violet (`disagree`) + green (`no-doublet`). RANSAC and the baseline checkbox were **removed from the GUI**
    (per user: only the 5 lines matter; baseline added fragility). `HEURISTIC_ADVANCED/PRO/RANSAC*` remain as
    internal constants; `RascalCalibrationLogicModule`/`removeBaseline` are kept but **no longer wired**.
  - **Predict-and-snap matcher** (`SpectrometerWavelengthCalibrationAdvancedLogicModule`, deterministic):
    anchor green + red by prominence → linear pixel→nm seed → predict every CFL line → **snap each detected
    peak to the nearest predicted line** (peak-centric, so the dense red cluster maps 1 peak↔1 line) → refit
    cubic, iterate (tighten tolerance). Resolves the green doublet + the 577–631 cluster. Validated: **8–13
    lines matched, <0.9 nm residual, monotonic** on Philips + Snowy — strictly better than the 5-anchor
    heuristic, and beats RANSAC. **Pro** adds a coarse color guard: reject a snap only if the band pixel's hue
    bucket and the line's `mainColorName` bucket differ by >2 (camera isn't colour-safe → gross swaps only).
  - **Baseline correction** (`SpectrumUtil.removeBaseline`): morphological opening (min then max filter) over
    a **resolution-adaptive window (~10% of spectrum width)** estimates the continuum; subtract it to isolate
    sharp lines. A *fixed* window broke the plain heuristic's anchor ranking on the lower-res image; ~10% keeps
    the heuristic correct on both Philips + Snowy while helping the advanced matcher (e.g. 8→10 lines on Philips).
    Applied once before whichever matcher runs.
  - **RANSAC matcher** (`RascalCalibrationLogicModule`, rascal 0.3.9, headless): CFL atlas from the master-data
    lines capped at 635 nm, `set_hough_properties(range_tolerance=500, min_wl=3500, max_wl=6500 Å)`,
    `fit(fit_deg=3)`; converts rascal's ascending-Angstrom `best_p` → our nm cubic `A/B/C/D` (A=p3/10 … D=p0/10),
    and matched peak↔atlas pairs → `SpectralLine`s. Seeded mode passes the heuristic cubic as `fit_coeff`.
    **Key tuning:** capping `max_wavelength` ~650 nm (so the rightmost peak can't map to the far-red lines)
    with a *loose* `range_tolerance` is what makes CFL converge — tightening it makes rascal find no solution.
    Validated on testPhilips: standalone ~1.4 nm, seeded ~0.5 nm max anchor error.
  - **Dispatch** is in `...WavelengthCalibrationVideoViewModule._runCalibrationMatcher` (runs on the UI thread
    with a wait cursor — the proper worker-thread move was deferred to avoid destabilising the working flow;
    a RANSAC fit briefly blocks the UI). rascal "no solution" → `RascalCalibrationError` → warning, no save.
  - **Deferred:** R5 consensus cross-check (run heuristic + RANSAC, warn on disagreement) — pairs with the
    postponed manual fallback (C) as the disagreement resolver.
  - **Guardrail:** `_warnIfImplausibleCalibration` flags a non-monotonic / inconsistent-dispersion fit before save.
  - Open: manual-assignment fallback (C, postponed); a real entity-backed headless test is blocked by a pre-existing
    SQLAlchemy mapper import-order fragility (stray class-body entity instantiations) — works in the app.
  - **RANSAC display fix (2026-06-26):** RANSAC matches the full atlas, so the calibration profile gets lines
    for wavelengths beyond the 5 heuristic anchors (587.6, 593.4, 631.1, …). `SpectrometerCalibrationProfileSpectralLinesViewModule`
    only builds fields for the anchor lines → `KeyError` on display. Fixed: `setModel` skips lines without a field
    (RANSAC's extras are still saved + used in the fit, just not shown in that view).
- **ROI left bound dropped blue/violet lines (fixed 2026-06-26).** `SpectrometerRegionOfInterestLogicModule.getVerticalBoundingLines`
  computed brightness as `qGray(red, green, green)` (blue channel dropped), so blue/violet emission lines read as
  near-black and the ROI x1 started past them. Fixed to `qGray(red, green, blue)`. Re-run "Detect Region of Interest"
  to pick up the corrected bounds (old saved ROIs don't auto-update). NOTE: calibration peak-detection samples the
  full image width anyway, but measurement uses the ROI x-bounds — so this matters for measurements.
- **Calibrating different-width images crashed in `SpectrumUtil.mean` (fixed 2026-06-26, spectracsPy-model).**
  `Spectrum.__capturedValuesByNanometers` was a class-level `[]` shared across all `Spectrum` instances, so
  frames from earlier runs / different image widths accumulated → ragged `numpy.matrix` → `mean()` TypeError.
  Fixed by resetting it per-instance in `Spectrum.__init__`. (Watch for other class-level mutable defaults in the
  entities — same anti-pattern appears elsewhere, e.g. stray class-body instantiations.)
- Color-based spectral-line validation incomplete (`SpectralLinesSelectionLogicModule`).
- Spectrum import/export backend partial; virtual spectrometer image not persisted across restarts.
- Camera device id hard-coded to 0; inlined stylesheet; master-data loads all rows (no pagination).
- Scratch scripts at app root (`spectracsTest*.py`, `match_orb.py`).
```

## 14. Planned work / specs

- **[`SPEC_pyside6_and_android.md`](SPEC_pyside6_and_android.md) — QtCharts → pyqtgraph (license-clean
  charting) + Android groundwork. IMPLEMENTED 2026-06-27 (charting part).** App is *already* 100% PySide6
  (LGPLv3, OK for closed-source); the one GPL leak was **Qt Charts** (GPLv3/commercial only). **Resolved:**
  all three charts moved to **pyqtgraph** (MIT) — `grep -rn QtCharts` is now clean, so the GPL obligation
  is gone and the app can ship closed-source under LGPL. Details:
  - New `view/application/widgets/chart/ChartThemeUtil.py` — single pyqtgraph theme adapter over
    `ApplicationStyleLogicModule` (transparent bg, light axes, subtle grid, static/no-zoom).
  - `SpectralJobGraphViewModule` → `pg.PlotWidget`; live raw overlay is a **bounded `deque(maxlen=200)`**
    ring buffer (was unbounded `addSeries`), mean = one persistent `setData` curve, axes **frozen to the
    first spectrum** for parity. Caller's two `.chart.setTitle(...)` calls became `.setTitle(...)`.
  - Calibration interpolation view → `pg.ScatterPlotItem` + `PlotDataItem`; the "spline" was never a
    spline — it's the calibration **cubic polynomial** sampled, so no scipy/guard was needed.
  - Import-preview chart was **dead code** (never added to its layout) → removed.
  - **Dep note:** `pyqtgraph 0.14.0` added to the venv; its install pulled numpy 2.x which breaks the
    numpy-1.x-compiled deps (colour-science pins `numpy<2`), so **numpy is pinned to 1.26.4**. Both
    PyInstaller specs now `collect_submodules('pyqtgraph')` (dynamic imports).
  - Android = future effort; real blockers are cv2/scipy/usb-serial, not charting.
- **[`SPEC_visual_harmonization.md`](SPEC_visual_harmonization.md) — spacing system + color
  consolidation.** Draft spec for a consistent look (spacing scale + Bootstrap-style semantic palette
  sourced from `ApplicationStyleLogicModule`).
- **[`SPEC_spectrum_processing.md`](SPEC_spectrum_processing.md) — spectrum processing + spectrum→colour
  (Roadmap #1).** Design spec: `SpectrumUtil` façade with one logic module per operation
  (mean/smooth/removeBaseline/rebin/normalize), plus `SpectrumToColorLogicModule` (CIE hue pipeline
  lifted from `spectrasTest.py`). Trims the prototype's heavy dependency set.
- **[`KB_spectrum_libraries.md`](KB_spectrum_libraries.md) — spectrum-related Python libraries
  (brain-helper).** Catalogue of the colour/spectrum libs (colour, colorsys, rgbxy, spectres, colormath,
  scipy) + the **dropped** ones (luxpy, BaselineRemoval, pyspectra, pandas, matplotlib) with "why it
  might return" notes.
