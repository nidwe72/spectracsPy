# Spec — Android port (scipy-in-app, two APKs, virtual-spectrometer-first)

Status: **IN IMPLEMENTATION.** P0 gate **PASSED 2026-07-03** (real scipy + PySide6 + OpenCV on a Galaxy
Note 20 — §7). P1/P2/P3-desktop done. **P4b reached: the REAL app builds, boots, and renders its UI
on-device** (full import chain resolved — see §8). **P5/P6 code done + desktop-verified** (two-app
localhost model — fixed-URI server + direct-proxy client + real login over loopback; §3.1). **P7
scaffolded** (capture backend abstraction; real backends deferred/hardware-gated). Remaining: package
the **server APK** (mainline p4a + foreground service + bcrypt/cffi) and integrate the two apps
on-device; plus postponed **P4c** (usage crashes) and **P4d** (on-device cosmetic/layout pass). Supersedes the earlier draft of this file and §5 of `docs/SPEC_pyside6_and_android.md`.

Goal: run SpectracsPy on Android as **two literal apps** (main UI + local server), with the **full
processing pipeline — including real `scipy` — running on-device in the main app**. First target is
**virtual-spectrometer-only**; real-hardware capture is designed but **deferred**.

---

## 0. Why this shape (the investigation that drove it)

- The app is **100% PySide6 (LGPL) + pyqtgraph (MIT)** — no binding change, no GPL leak.
- **`scipy` is foundational, not incidental.** It (with SQLAlchemy) is the reason this is a
  Python/PySide6 app rather than C++. So "keep real scipy on-device" is a hard requirement, not a
  convenience — the port must not force it out.
- **The "scipy can't cross-compile for Android" premise is now largely obsolete:**
  - **scipy 1.18.0 (Dec 2025) removed *all* of its own Fortran** (MINPACK, QUADPACK, L-BFGS-B,
    ODEPACK, FITPACK — all ported to C over 1.13→1.18; tracking issue #18566 closed 2025-12-18).
    scipy's own code no longer needs a Fortran compiler; it needs C/C++ + a linked LAPACK (OpenBLAS).
  - A **modern Android Fortran toolchain exists** anyway (termux **flang**), used by both Chaquopy
    and python-for-android; the dead classic gfortran-for-Android is superseded.
  - **python-for-android already ships a maintained `scipy` recipe** (scipy 1.16.2, Meson,
    `depends=[numpy, libopenblas, fortran]`, last touched 2026-05-10). It's on p4a's CI **skip** list
    only because the CI runner **runs out of disk** building it — not a compile failure. So it's
    intended-to-work but **under-verified** (no public on-device success log found).
  - `scipy.linalg.eigh/svd/eig` are thin wrappers over linked LAPACK (OpenBLAS) — so **LDA, PCA,
    PLS** and the linear-algebra core all work; real scipy additionally covers **airPLS/AsLS baseline
    (sparse/banded), spline smoothing (FITPACK), and `curve_fit` line-shape fitting**.
- **The processing surface is small and mostly dead weight today** (dependency audit):
  - Live heavy dep on the pipeline = **`scipy`** (only `scipy.signal.find_peaks`/`peak_prominences`/
    `savgol_filter` + `scipy.ndimage` min/max filters) and **`opencv`** (focus/Hough/cvtColor).
  - **`astropy`, `pandas`, `BaselineRemoval`** — only in root scratch scripts, not in the app.
  - **`scikit-image`** — a single dead, unused import.
  - **`rascal`** — **not live**: an orphaned module + one stray unused import; the developer's belief
    that it was removed is correct.
- **Tooling reality:** `pyside6-android-deploy` is a Technology-Preview wrapper (Linux-host,
  single-`main.py`) that **cannot build a service or a second app** and does not surface custom
  recipes. Two apps + a scipy recipe therefore require **raw buildozer + python-for-android**.
- **No physical spectrometer available now**, and a possible future **Raspberry-Pi tier** could carry
  capture over the network — so real capture (UVC-over-OTG) is deferred; the **virtual spectrometer**
  already runs the full pipeline with no hardware and is the first target.

---

## 1. Decisions locked in

| # | Decision | Choice |
|---|----------|--------|
| D1 | Toolchain | **Raw buildozer + python-for-android** (not `pyside6-android-deploy` — it can't do services/second app/custom recipes). PySide6 support comes from Qt's p4a fork; the scipy recipe gets ported into that toolchain (see D5) |
| D2 | Processing scope | **Full on-device (C).** First target = **virtual spectrometer only**; real-hardware capture deferred (§6) |
| D3 | `scipy` | **Kept as the real package (K2)**, running **in the main UI app** — via p4a's scipy recipe (OpenBLAS + flang). No offload, no vendoring |
| D4 | App topology | **Two literal APKs** — (1) **main app**: PySide6 + numpy + opencv + **scipy**; (2) **server app**: login/master-data, **no scipy** |
| D5 | Databases | **Two isolated DBs** — client DB in the main app's sandbox, server DB in the server app's sandbox |
| D6 | Server lifecycle | Server APK runs a **foreground service** hosting Pyro5 on **fixed `127.0.0.1:port`**; **user launches the server app** (Android forbids cross-app silent service start) |
| D7 | Filesystem | Drop `appdata`; use **`QStandardPaths.AppDataLocation`** (set `organizationName`/`applicationName`); handle desktop DB-path migration; remove hardcoded `/home/nidwe/...` paths |
| D8 | UI adaptation | **Concentrated phone pass**, not a rewrite (§ D-list in Phase 3) |
| D9 | Dead-dep cleanup | Remove `rascal` (orphan module + stray import), and the scratch/dead references to `astropy`/`pandas`/`BaselineRemoval`/`scikit-image`. Keep `scipy`, `numpy`, `opencv` |
| D10 | K3 (vendored numpy) | **Opted out.** Recorded as a considered alternative only; not the planned fallback (revisit solely if the Phase-0 spike fails) |
| D11 | Dependency manifest | Produce the long-deferred **`requirements.txt`**, version-aligned to the scipy/numpy/OpenBLAS/flang recipe set |
| D12 | Two p4a toolchains (finding B) | **Main app = Qt's p4a fork** (needs Qt + scipy). **Server app = mainline p4a** (needs `--service`/foreground service, no Qt). Fit-for-purpose; two build toolchains maintained |
| D13 | Login gate (finding A) | **Login is mandatory** — the milestone must exercise the full feature set. For on-device **bring-up only**, a **temporary dev login-bypass flag** lets the main app's virtual pipeline be validated before the server app exists; the bypass is **removed at P6** before the milestone counts |

---

## 2. Architecture

> Deployment diagram: `spectracs-docs/android_architecture.svg` (regenerate with
> `java -jar plantuml.jar -tsvg android_architecture.puml`).

```
┌────────────────────────────┐     Pyro5 over 127.0.0.1:<fixed port>      ┌───────────────────────────┐
│  MAIN APK                   │  ── login / listUsers / syncSpectrometers ▶│  SERVER APK               │
│  PySide6 UI                 │  ◀───────────  results / master data  ──── │  foreground service       │
│  numpy + opencv + SCIPY     │                                            │  Pyro5 + SQLAlchemy+bcrypt │
│  full virtual pipeline      │   (user must launch the server app first)  │  no scipy                 │
│  sandbox: spectracsPy.db    │                                            │  sandbox: …Server.db      │
└────────────────────────────┘                                            └───────────────────────────┘
```

- **Main app** does *all* compute on-device (this is where scipy lives) and its own SQLite DB. Boots
  and runs the virtual pipeline standalone; only login + remote master-data need the server.
- **Server app** hosts the Pyro5 daemon in a **foreground service** (persistent notification so
  Android doesn't kill it), fixed `127.0.0.1:<port>` (Pyro nameserver UDP-broadcast discovery does not
  work across sandboxes). Add a **"local" mode** to `SpectracsPyServerClient.getProxy()` beside the
  existing local-nameserver / NAT-host fallbacks: a direct `PYRO:…@127.0.0.1:<port>` URI.
- **Cross-app start restriction:** the main app cannot silently start the server app's service; the
  user launches the server app. The client already degrades gracefully when the server is unreachable,
  so the main app is independently usable.

---

## 3. Phases (execution-ordered)

> **P0 PASSED 2026-07-03** (§7). P1, P2, and P3-desktop are implemented + desktop-verified.
> Dependencies: P1/P2/P3 desktop-first (P2 **blocked** P4) · P4 → P5 · P6 needs P4+P5.
> Toolchain (corrected): **main app = mainline p4a `develop` + `qt` bootstrap** — there is NO separate
> Qt fork (the recipes are upstream). **Server app = mainline p4a**, headless.
> Login (D13): temporary **dev bypass** through P4–P5; **removed at P6**, real login gates all.
> `<MILE>` = counts toward the "existing app(s) running on Android" milestone.

| # | Content | Verify on | Status / done-when |
|---|---|:---:|---|
| **P0 · Composition spike (GATE)** | Minimal APK: `qt` bootstrap + scipy(→libopenblas→flang) + cv2 + a `sciens.*` import; lock the version matrix. | phone | ✅ **PASSED** — `numpy 2.3.0 / scipy 1.16.2 (find_peaks+svd) / cv2 4.12.0` all OK on device (§7) |
| **P1 · Desktop hardening** | Dead-dep cleanup; `main.py` shims ×2; import+call guards for `cv2.VideoCapture` & `usb`; dev login-bypass; split `requirements.txt`. | desktop | ✅ done + verified (offscreen full-UI boot, 13 views) |
| **P2 · Filesystem** | `appdata` → `AppDataPathUtil` (ANDROID_PRIVATE on device, appdata on desktop → **no migration**); `is_android()`. | desktop | ✅ done + verified (desktop DB path unchanged) |
| **P3 · UI phone pass (desktop parts)** | Dynamic logo (drop 720px min-width); `showFullScreen`+portrait; Android back-button event filter → Home; touch-density QSS appended on Android. | desktop | ✅ done + verified |
| **P3′ · UI device-only bits** | `QScrollArea` wrap (PageWidget + wizard, android-gated); soft-keyboard `windowSoftInputMode=adjustResize` + `ensureWidgetVisible`; wizard step-bar wrap. | device (in P4) | forms scroll; keyboard doesn't hide focused field; step-bar fits portrait |
| **P4a · Persist toolchain fixes** | Move the 3 p4a edits into `p4a.local_recipes` so clean builds keep them: numpy cross-file **patch**, scipy `Cython>=3.1.2`, `python3`+`hostpython3`=**3.11.9**; freeze the proven buildozer.spec (qt bootstrap, NDK r28c, minapi 26). | host | clean rebuild reproduces the working stack, no manual edits |
| **P4b · Package the REAL main app** | source = the 4 `sciens` repos (bundle the `sciens.*` namespace); full reqs: numpy,scipy,opencv,colour,colormath,luxpy,rgbxy,spectres,Pyro5,SQLAlchemy,marshmallow*,pyspectra. | host | app + all `sciens.*` + full dep set packaged |
| **P4 · MAIN APP on device** `<MILE>` | Build main APK; logcat-driven fixes; run the **virtual pipeline** via `SPECTRACS_DEV_LOGIN_BYPASS=1`. | phone | virtual pipeline runs end-to-end on the phone (dev bypass) — first summit |
| **P5 · SERVER APP on device** | buildozer.spec #2 (**mainline p4a**, headless); Pyro5 daemon on a **non-main thread** @ `127.0.0.1` fixed port (no nameserver); foreground service + `POST_NOTIFICATIONS`; bcrypt; 2nd isolated DB. | phone | server app launches, foreground service stays alive, reachable on loopback (airplane-mode ok) |
| **P6 · Integration + REAL login** `<MILE>` | Client "local" proxy mode; **remove dev bypass**; real login + master-data sync over loopback; "launch the server app" UX; functionality recap checklist. | phone | real login + sync + **full functionality checklist** pass; no public service — **milestone complete** |
| **P7 · Deferred: real capture** | UVC-over-OTG **or** RPi-network tier + USB permissions (§6). | **device** | separate future spec |

**Phase 3 — UI phone pass (concrete items):**
1. **Dynamic logo** — remove `MainStatusBarViewModule.py:48` `setMinimumWidth(720)` (forces the window
   wider than a phone); scale to available width; reconsider the fixed 100px header band.
2. **Scroll wrapping** — wrap `PageWidget` content + wizard panels (`WizardViewModule.py:247-315`) in
   `QScrollArea(setWidgetResizable(True))`; verify against the `setRowStretch(0,90)` interaction.
3. **Touch targets** — in the one QSS (`ApplicationStyleLogicModule.py`): checkbox/radio `::indicator`
   13px→~24-28px, scrollbars 15px→~24px, spin/combo arrows 3px→larger; gate enlarged values behind a
   **runtime touch-density flag** (`QSysInfo.productType() == "android"`) so desktop is unaffected.
4. **Android back button** — intercept and map to `QStackedWidget` "navigate back" (Qt default would
   *close the app*). Must-have.
5. **Soft-keyboard occlusion** — on focus, `ensureWidgetVisible` so text fields (serial/login/user
   forms) aren't hidden by the on-screen keyboard.
6. **Fullscreen + portrait** — `showFullScreen()` on Android; **portrait-locked**; drop the desktop
   `setMinimumWidth(screen/2)` sizing.
7. **Wizard step-bar** — `StepBarWidget.py:39` width grows `steps*150` at fixed 34px height; make it
   wrap or horizontally scroll.

---

### 3.1 Remaining after P4b (app runs on device)

| # | Remaining work | Verify on | Done-when |
|---|---|:---:|---|
| **P4c · Usage-crash fixes** | From live logcat: (a) delta-E `_bz2` — patch p4a python3 to wire arm64 libbz2 into the **target** build, OR reimplement `SpectralColorUtil.getColorDifference` (CIEDE2000 + sRGB→Lab) in numpy (removes the colormath→networkx→bz2 chain); (b) wire the dev-login bypass on Android (env not settable on device → bake a flag) so login-gated flows run; (c) whatever else the traceback shows. | device | no crash navigating the app / running the virtual flow |
| **P4d · On-device cosmetic/layout pass** | The many visual issues: QSS density/fonts/spacing, header band, scroll/overflow, touch targets — the real UI pass that only device-driving reveals. Screenshot-driven. | device | UI legible + usable in portrait |
| **P4e · Durable build recipe** | Fold `app_src` staging + full requirements + vendored colormath/rgbxy + import guards + libbz2/liblzma into a repeatable script (extends `android/patch_p4a.sh`). | host | a clean checkout rebuilds the APK with no manual dep-walking |
| **P5 · Server APK** | **Code done + desktop-verified** (`SpectracsPyServer.serveLocalForever()` — fixed URI, no nameserver; server `main.py` runs it). **Remaining:** package as a 2nd APK — mainline p4a (headless, no Qt) + **foreground service** + **bcrypt→cffi** + 2nd DB. | phone | server app stays alive, reachable on loopback |
| **P6 · Integration + REAL login** | **Code done + desktop-verified** (client `getProxy` local-proxy first; real login over loopback → `{ok:True}`). **Remaining:** run both APKs on-device, "launch server" UX, remove dev-bypass, functionality recap. | phone | real login + sync + functionality checklist |
| **P7 · Real capture** | **Scaffolded** (`logic/appliction/video/capture/CaptureBackend.py`: desktop cv2 real; Android-UVC + RPi-network = documented stubs). **Remaining:** deferred/hardware-gated (§6). | device+hw | separate future spec |

## 4. Dependency plan

| Package | Role | On device? | Note |
|---|---|:---:|---|
| `numpy` | everywhere | ✅ | p4a `CORE_RECIPE`; version aligned to the scipy recipe |
| `scipy` | signal (find_peaks/prominences/savgol) + ndimage filters; future LDA/airPLS/splines/curve_fit | ✅ (main app) | **p4a scipy recipe** (Meson + OpenBLAS + flang); the Phase-0 spike proves it under PySide6 |
| `opencv` (`cv2`) | image processing (focus, Hough, cvtColor) | ✅ (main app) | p4a recipe exists (builds `cv2`) |
| colour/colormath/luxpy/rgbxy/spectres | spectrum→colour on the critical path | ✅ | pure-Python over numpy |
| Pyro5 / SQLAlchemy / marshmallow* | RPC + persistence | ✅ | pure-Python |
| `bcrypt` | password hashing | ✅ (server app) | native; p4a recipe exists |
| `pyspectra` | `.dx` import view (off core path) | ➖ optional | include only if `.dx` import is wanted on device |
| `pyusb`, `psutil` | USB detection / local-addr discovery | ❌ deferred | pyusb rides with capture (§6); psutil likely unneeded given fixed 127.0.0.1 |
| **Removed** | `rascal`, `astropy`, `pandas`, `BaselineRemoval`, `scikit-image` | — | dead/scratch/unused (D9). Note: adopting the `BaselineRemoval` *package* later would pull `scipy.sparse` (fine under K2) **+ scikit-learn** (needs its own p4a recipe) — treat sklearn as a separate future recipe question |

---

## 5. Constraints / invariants

1. **scipy stays in the main app** (D3) — compute is co-located with the pipeline, never marshalled to
   the server for core steps.
2. **Phase-0 gates everything** — no packaging work (4/5/6) before the spike proves PySide6+scipy on a
   real device. K3 is not a standing safety net (D10).
3. **Version alignment is a first-class risk** — scipy ↔ numpy ↔ OpenBLAS ↔ flang ↔ (PySide6's Python)
   must line up; pin them together in `requirements.txt` and the p4a recipe set.
4. **arm64-v8a first** — target arm64 only initially (Qt + p4a scipy both favor it); no fat build.
5. **Desktop must keep working** at every phase — Phases 1–3 are desktop-verifiable and must not
   regress the desktop app (guard the filesystem migration especially).
6. **Server optional at runtime** — the main app boots and runs the virtual pipeline with the server
   app absent.

---

## 6. Deferred — real-hardware capture (out of the first target)

Documented so the deferral is deliberate. **Not built now; gated on hardware access AND the RPi-tier
decision.** Only the *capture* + *USB-detection* front-ends fork by platform; cv2/scipy processing is
shared.

| Concern | Desktop (keep) | Android (deferred) |
|---|---|---|
| Frame capture | `cv2.VideoCapture(0)` | **UVC-over-OTG**: `UsbManager` grants a device fd → libusb (`libusb_wrap_sys_device`) → libuvc → numpy/`QImage` |
| Device detection | `usb.core.find(vid,pid)` (libusb) | `UsbManager.getDeviceList()` via JNI/pyjnius, then permission grant |

Android permissions for the USB spectrometer (note: **not** `android.permission.CAMERA` — that's only
the built-in Camera2 camera): `<uses-feature android:name="android.hardware.usb.host"/>` + runtime
`UsbManager.requestPermission()` (or a `USB_DEVICE_ATTACHED` intent-filter + `device_filter.xml`).

**Strategic alternative for that phase:** if the **Raspberry-Pi tier** materializes, the phone talks to
the Pi over the network (no OTG), and the Pi can also carry capture — reusing the existing Pyro/HTTP
client pattern. Decide UVC-over-OTG **vs** RPi-network-capture then.

---

## 7. P0 result — the proven build config (2026-07-03)

**P0 GATE PASSED.** A minimal PySide6 spike carrying numpy + scipy + OpenCV ran on a Galaxy Note 20:
`numpy 2.3.0 OK · scipy 1.16.2 OK (find_peaks peaks=[1,3,5], svd0=5.465 via OpenBLAS) · cv2 4.12.0 OK`.
Real scipy runs under PySide6 on Android — the port's make-or-break, proven. The spike lives in
`android/spike/` (throwaway proof). The exact working recipe P4 must reuse:

| Component | Value |
|---|---|
| Packager | raw **buildozer** driving mainline **python-for-android `develop`** (the `pyside6-android-deploy`-generated `buildozer.spec` is reused as-is, then extended) |
| Bootstrap | `p4a.bootstrap = qt` |
| Python | **3.11.9** — pin BOTH `python3` and `hostpython3` recipe `version=` (must match). PySide6 Android binaries are cp311 |
| PySide6 / shiboken6 | **6.11.1** abi3 wheels from download.qt.io (`android/spike/wheels/`), rendered recipes in `deployment/recipes` |
| NDK | **r28c** (flang recipe hard-asserts it) |
| JDK | **17** (Gradle 8.14 rejects Java 25 — "major version 69"); kill stale GradleDaemons |
| minapi | **26** (libopenblas needs ≥24; python3 `endgrent` needs ≥26) |
| scipy recipe | `Cython>=3.1.2` (was 3.0.8 — too old for numpy 2.3 C-API) |
| numpy recipe | **PATCHED** (see below) |
| arch | `arm64-v8a` only |

**The critical p4a bug + fix (numpy `get_recipe_env`):** the OpenBLAS-linked numpy variant did a
destructive `self.extra_build_args = [...]` that clobbered the `--cross-file` injected by
`MesonRecipe.build_arch`, so meson ran a *native* build and tried to execute an arm64 test binary on
the x86 host → `sanitycheckc.exe: Exec format error`. Fix = filter out old blas/lapack args and
**append** the new ones (preserving `--cross-file`), idempotent. Upstream-reportable p4a bug; P4a moves
it (and the version pins) into `p4a.local_recipes` so clean rebuilds don't need manual edits.

---

## 8. Risks

1. **PySide6 + scipy composition (Phase 0)** — no public precedent; Qt's p4a fork may lag mainline's
   scipy recipe, so we may port the recipe into the fork. Mitigated by making it the cheap first gate.
2. **scipy build engineering** — version/toolchain alignment and the CI-storage issue (build it
   yourself, verify on-device). Days-to-weeks; low-to-moderate risk given the maintained recipe.
3. **Foreground service under raw p4a** — Java/manifest plumbing; the trickiest Android integration.
4. **APK size / cold start** — Qt + scipy + OpenBLAS + opencv is large; p4a unpacks Python on first
   launch. Note, don't optimize yet.
5. **Two literal APKs** — user must launch the server app; cross-app localhost is workable but the
   least-blessed part of the design.
6. **Capture (deferred)** — UVC-over-OTG unproven on the real device; RPi tier may supersede it.

---

## 9. Out of scope

- Real-hardware capture / USB (§6) — deferred, separate future spec.
- The Raspberry-Pi tier itself (hardware design).
- `pyside6-android-deploy` (rejected — no services/second app/custom recipes).
- Chaquopy (rejected — not a Qt runtime; can't host PySide6).
- **K3** vendored-numpy reimplementation (opted out, D10).
- iOS, tablet-specific layouts, app-store publishing, performance tuning beyond "virtual pipeline runs
  acceptably."
