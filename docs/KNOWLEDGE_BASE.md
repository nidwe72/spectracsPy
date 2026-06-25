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

**Test images:** raw CFL spectral band at `spectracsPy/testSpectra/cfl_philips_calibration.png`
(2592×1944) and `..._cropped.png` (1854×336); originals under
`/home/nidwe72/data/migration/apollo-windows/spectracs#20/testPhilips.png`. Note:
`spectracs-evaluations/.../sample_step1_original.png` is a plotted CHART, not a usable frame.

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
- **Pixel↔wavelength matching quality** is the open algorithm issue (peaks mapped to wrong reference lines).
- Color-based spectral-line validation incomplete (`SpectralLinesSelectionLogicModule`).
- Spectrum import/export backend partial; virtual spectrometer image not persisted across restarts.
- Camera device id hard-coded to 0; inlined stylesheet; master-data loads all rows (no pagination).
- Scratch scripts at app root (`spectracsTest*.py`, `match_orb.py`).
```
