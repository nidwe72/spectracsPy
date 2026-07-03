# P0 · Composition spike

The go/no-go gate for the whole Android port (`docs/SPEC_android_port.md` P0). It proves the one
thing with **no public precedent**: that **PySide6 + real scipy + cv2 + a multi-repo `sciens.*`
import** run together under python-for-android on a real device.

Scipy being on-device is *why* Spectracs is Python/PySide6 (not C++), so this gate validates the
load-bearing assumption of the stack on mobile — not just a build.

## What it does
`main.py` shows a full-screen screen that imports and exercises each piece and prints the result:
- `numpy` — version
- `scipy` — `find_peaks` + `numpy.linalg.svd` (LAPACK) numeric results
- `cv2` — `cvtColor`
- `sciens.*` — imports from **both** the base repo (`sciens.base.PlatformUtil`) and the model repo
  (`sciens.spectracs.model.databaseEntity.AppDataPathUtil`), proving the PEP-420 namespace bundles
  across repos.

## GO / NO-GO
- **GO**: every line ends in `OK` with numbers. Record the build recipe (p4a fork, versions,
  bundling approach) — P4 reuses it.
- **NO-GO**: any `FAIL`. **Escalate** — K3 (vendored numpy) was opted out, so there is no silent
  fallback. Capture the full `adb logcat` around the failing import.

## The three things this gate is actually testing
1. **scipy composes with PySide6 in one p4a build.** The mainline p4a scipy recipe
   (`scipy → libopenblas → fortran`/flang) must be present in the p4a that Qt's PySide6 build uses.
   If Qt's fork lacks it, porting the recipe chain into the fork is the core P0 work.
2. **cv2 builds/loads** alongside the above (opencv p4a recipe).
3. **The 4-repo `sciens.*` namespace survives p4a bundling** (p4a expects one `source.dir`; see the
   note in `buildozer.spec`).

## Version matrix to lock (reconcile desktop pins ↔ p4a recipe versions)
| Component | Desktop (venv) | Android (p4a recipe) | Note |
|---|---|---|---|
| Python | (venv) | p4a python3 | must match PySide6's supported Python |
| PySide6 / shiboken6 | 6.5.0 | Qt p4a fork | fork/branch must match this PySide6 |
| numpy | 1.26.4 | p4a CORE_RECIPE | align with the scipy recipe |
| scipy | 1.10.1 | p4a recipe (~1.16.2) | newer on Android is fine; verify API used |
| OpenBLAS / flang | n/a | recipe deps of scipy | the chain scipy depends on |
| opencv (cv2) | opencv-python-headless 4.7 | p4a opencv recipe | recipe builds cv2 |

## Build (on a Linux host; buildozer is Linux-only)
```
python -m pip install --user buildozer
# fill the TODOs in buildozer.spec (NDK/SDK/API, Qt p4a fork), stage the sciens/ trees, then:
buildozer -v android debug
adb install -r bin/*.apk       # sideload to the phone
adb logcat | grep -i python    # watch imports; screenshot the result screen
```

## Desktop sanity
`main.py`'s checks run on desktop too (all deps are in the venv) — run it first to confirm the spike
logic before wrestling the Android build:
```
PYTHONPATH=".:../../:../../../spectracsPy-base:../../../spectracsPy-model" \
  QT_QPA_PLATFORM=offscreen python -c "import main; print(main._run_checks())"
```
