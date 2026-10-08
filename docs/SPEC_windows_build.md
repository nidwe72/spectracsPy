# SPEC — Windows build of app + server (W0 packaging · W1 camera · W2 installer/signing)

Status (2026-10-08): **V0 DONE · W1.0 + W1.0b spikes RUN · W1.1 DECIDED · W0.1–W0.7 DONE (§11c.2–§11c.6) · W0.8 next (Edwin).**
Three rubber-duck passes folded in place (§11 R1–R14, §11b S1–S13, §11c U1–U24 — the third aimed at W0.1–W0.3 at
code level); phases + order in **§12**.

> ⭐ **RESUME HERE.** The VM is ready (§12 V0: `ssh spectracs-win`, venv `C:\spectracs-build\venv`, ELP passthrough,
> Shelly reachable). The camera questions are answered (§6.6b, §6.6c): MSMF + own YUY2 conversion (needs
> non-headless `opencv-python` on Windows), **white balance frozen natively via DirectShow `IAMVideoProcAmp`**,
> exposure **whole log₂ steps** accepted for now (decision W1.1). **W0.1–W0.3 are built and gated on Linux
> (§11c.2); W0.3b swapped the VM to `opencv-python`; **W0.4: `SpectracsServer.exe` runs in the VM** (§11c.3).
> **W0.5: `Spectracs.exe` builds, passes `--fresh --check-db` + `--check-lamp-imports`, and its GUI starts**
> (§11c.4). **W0.6/W0.7: `tools/buildWindows.sh` builds, self-verifies and zips both programs with one command**
> (§11c.5, §11c.6). Next: **V0.6** (virtual fileset + server config into the VM) and **W0.8 = Edwin's
> click-through §8.1**, then W0.9. ⏸ Null run (O3) postponed. Implementation only on explicit request.

Source: Edwin, 2026-10-07 — *"we have already build an linux AppImage of the spectracsPy and spectracsPy-server
— now i would like to have a windows version"*. His answers in the same session:

| # | question | Edwin's answer | consequence |
|---|---|---|---|
| A1 | where is it built/tested? | *"a VM hosted on Linux that runs the Windows instance"* | the VM is build host **and** test rig (§5, §7.6) |
| A2 | who is it for? | *"finally it will be used in production also"* | **W1 (real camera) is required**, not optional |
| A3 | zip or installer? | zip *"okay for now"* | W0 ships a zip; installer = W2 |
| A4 | the old `spectracsAppPyInstallerWindows.spec`? | *"forget it … just a manual try … use the mechanisms/script as was done for the Linux AppImage"* | reuse `buildAppImages.sh` + the AppImage specs (D2) |
| A6 | the server? | *"an independent artefact … only started manually on demand as usually the server will run on the internet"* | two zips, ⛔ no launcher (D6) |
| A7 | own YUYV conversion? | *"that's the way to go"* | §6.3, incl. Linux if bit-identical |
| A5 | the camera? | *"will be a subtask to make camera MS Windows aware/capable"* | W1 is its own milestone with its own gate (§6) |

Theme: **the packaging is a copy job; the camera is a measurement question.** Getting a Windows `.exe` that
starts is roughly the Linux AppImage work again. Getting a Windows capture whose Rv can be *believed* is not — every
Q%/Rv number to date was produced through OpenCV's V4L2 backend, and Windows replaces exactly that layer.

| | milestone | what it is | gate |
|---|---|---|---|
| **W0** | **packaging** | onedir app + server built in the VM by one command from Linux, zipped; runs on the virtual device, archive, PDF, LIMS | §8.1 |
| **W1** | **real camera** | find the ELP/Microdia by VID/PID on Windows, own the YUYV→BGR conversion, map exposure, then a **null run on Windows vs Linux** | §8.2 ⭐⭐ the go/no-go |
| **W2** | **installer + signing** | `Spectracs-Setup.exe` (Inno Setup), code signing so SmartScreen stays quiet | before the first customer install |

---

## 1 — Scope

In: Windows 10/11 x86-64; the app (`spectracsMain`) and the server (`spectracsServer`), as two programs like on
Linux; a build script on Linux that drives the VM; the camera path for UVC cameras (ELP `32e4:8830`, Microdia
`0c45:6366`).

Out (§10): macOS, Windows on ARM, cross-compiling on Linux, a single-file `.exe`, the ToupTek mono camera
(its Windows SDK is noted in §6.6 as an option, not planned work).

---

## 2 — Survey: what carries over, what breaks (against the as-is code, 2026-10-07)

### 2.1 Carries over unchanged

- **Server discovery.** The client probes `PYRO:…@127.0.0.1:8091` first (`SpectracsPyServerClient.getProxy`);
  `spectracsServerAppImageEntry.py` with no arguments runs `serveLocalForever()` on loopback. Both are plain
  Python and do not care about the OS. Loopback binds trigger **no** Windows Firewall prompt.
- **Dependencies.** Every pin in `requirements.txt` has a `cp310-win_amd64` wheel (PySide6 6.5.0, numpy 1.26.4,
  scipy 1.10.1, opencv-python-headless 4.7.0.72, bcrypt, PyNaCl, psutil) or is pure Python (Pyro5, SQLAlchemy,
  Alembic, pyqtgraph, colour-science, luxpy, zeroconf, pypdf, matplotlib). ✅ Confirmed by the V0.2 install.
  ⚠ Except OpenCV: Windows needs the **non-headless** `opencv-python` 4.7.0.72 (§6.6b) ⇒ `requirements.txt` is
  split by platform marker in W0.3b (D8, U19).
- **The licence gate.** `spectracsAppImage.spec:115-136` filters by name substring (`Charts`,
  `DataVisualization`, `WebEngine`) — that matches `Qt6Charts.dll` exactly as it matches `libQt6Charts.so.6`. ⚠ The **size** trimming does not
  carry over by itself: `DROP_DATA_DIRS` names `PySide6/Qt/…`, and on Windows PyInstaller files Qt under
  `PySide6/` (R9) ⇒ W0.3 adds the two missing Windows variants, `PySide6/qml` and `PySide6/resources`
  (`PySide6/translations` is already listed and is the Windows path too, U12).
- **Plugins** (M3, signed, DB-served, loaded by `importlib` from a codeRef) are pure Python ⇒ no difference.
- **The Shelly lamp plug** (HTTP + zeroconf/mDNS) works on Windows — ⚠ but see §7.5 (firewall prompt, VM NAT).

### 2.2 Breaks or differs

| # | where | what happens on Windows | milestone |
|---|---|---|---|
| B1 | `SensorCaptureIndexResolver.py:26` | returns `None` off Linux (it reads `/sys/class/video4linux`) ⇒ **no real camera at all**, only the virtual device | W1 |
| B2 | `CaptureBackend.py:__queryControl` | `import fcntl` sits **before** the guard ⇒ `ImportError` on Windows; reached from `readCameraSettings()` → `__exposureRange()`, i.e. on the CAPTURE-SETTINGS log line of every capture | W1 (does not crash — callers catch it; R7) |
| B3 | `CaptureBackend.py:__forceUncompressed` | asks for FOURCC `YUYV`; Windows names it **`YUY2`** ⇒ the read-back check prints a false "driver kept …" warning even when it worked — or the request is refused | W1 |
| B4 | `CaptureBackend.py:63` + `cap.read()` | `CAP_ANY` ⇒ MSMF (or DSHOW); **the backend, not OpenCV, does YUYV→BGR** (§6.3) | W1 |
| B5 | `SpectrometerSensorUtil.py:26`, `DevSpectralPlugin.exposure = 90`, `AutoExposureLogicModule` | all exposure numbers are **V4L2 units** (100 µs steps, ELP range 1–500, inverted axis). On Windows `CAP_PROP_EXPOSURE` is normally a **log₂-seconds exponent** (−13…−1) ⇒ `78`/`90`/`150` are meaningless there, and the AE ladder has **factor-2 steps** to work with | W1 ⭐ the science risk (§6.4) |
| B6 | `ConnectionPollThread`, `ApplicationSpectrometerUtil` | `usb.core.find` needs a libusb DLL backend; none is bundled ⇒ it raises `NoBackendError`. The poll thread and status module catch it (presence "absent"), but **`SpectrometerSetupViewModule.py:83-84` → `isSensorConnected` does not ⇒ the setup screen crashes, virtual spectrometers included** (R3) | **W0.1** (guard) + W1.1 (same lookup as B1) |
| B7 | `appdata` 2.2.0 `__init__.py:163` | the dot is Linux-only ⇒ data dir = `%USERPROFILE%\spectracsPy` (no dot), and still **named after the cwd basename** — a double-clicked exe has cwd = its own folder ⇒ the DB would be named after the **zip folder** (`%USERPROFILE%\Spectracs-<tag>-win64`), i.e. a fresh empty DB per release | W0 (D4) |
| B8 | windowed PyInstaller exe | `sys.stdout`/`sys.stderr` are `None` ⇒ `print()` is silently lost and any library calling `sys.stdout.write` raises | W0 (D5) |

---

## 3 — Decisions

### D1 — Build in the Windows VM, driven from Linux over SSH

PyInstaller is not a compiler: it collects the **running** interpreter and its DLLs, so a Windows bundle can only
be made on Windows. Wine is unsupported and unreliable with Qt6 + scipy + OpenCV and would cost more than it saves.
⇒ The VM (A1) has an OpenSSH server (a built-in optional Windows feature) and its own pinned venv; the Linux
script prepares the sources and calls PyInstaller **in** the VM (§5).

> The Linux AppImages are PyInstaller too: `spectracsAppImage.spec` builds a onedir bundle on Linux, and
> `appimagetool` only wraps that folder into one file. So it is the **same tool on both sides** — run once per OS,
> on that OS. The Windows build replaces the `appimagetool` step with a zip (W0) or Inno Setup (W2).

### D2 — Reuse the AppImage specs; no Windows-only `.spec`

`spectracsAppImage.spec` and `spectracsServerAppImage.spec` already carry the excludes, the datas (Alembic trees,
`resource/`, `testSpectra/`, colour data), the hiddenimports and the licence gate. A third spec would drift.
⇒ Each spec gets a **small `sys.platform == 'win32'` branch** for what really differs: `runtime_hooks=` (D4),
`console=` and `disable_windowed_traceback=True` (D5), `icon=` (`.ico`, D7), `name=` in EXE **and** COLLECT
(`Spectracs` / `SpectracsServer`), and the Windows `DROP_DATA_DIRS` variants (R9). The entry scripts stay
`spectracsMain.py` and `spectracsServerAppImageEntry.py` on both OSes.
⚠ The **app** spec has only one root today (`HERE` = SRC, `spectracsAppImage.spec:15`); the hook lives on the
recipe side ⇒ W0.3 gives it a `RECIPE = SPECPATH` root like `spectracsServerAppImage.spec:16-17` (S5), or the
hook would be looked for in the tagged worktree.
Both old specs — `spectracsAppPyInstallerWindows.spec` (A4: `Splash`, `upx=True`, `libusb0.dll` from
`C:\Windows\System32`) and `spectracsAppPyInstaller.spec` — are deleted in W0.

> ⚠ The file names keep "AppImage" for now; renaming them to `spectracsApp.spec` / `spectracsServer.spec`
> is a cosmetic follow-up, not part of W0.

### D3 — onedir + zip; ⛔ no single-file `.exe`

Windows has no AppImage equivalent: an AppImage **mounts** its image, while PyInstaller's `--onefile` **unpacks
~500 MB into `%TEMP%` on every start** — slow (the antivirus scans every unpacked file, every time), it leaves the
unpacked tree behind after a crash, and single-file Python exes are flagged as malware noticeably more often.
⇒ W0 ships the onedir folder as a zip. The Windows idiom for "one file" is the installer (W2), built from the same
folder.

### D4 — Two PyInstaller runtime hooks do what AppRun does: pick the data dir by `chdir`, before any import

AppRun selects the data directory with `cd` (Linux spec D2). On Windows the cwd is whatever started the exe (B7).
⇒ A **runtime hook** per program (`runtime_hooks=[RECIPE/tools/…]`, win32 only). PyInstaller runs custom runtime
hooks **before** PyInstaller's own `pyi_rth_*` hooks and the entry script (`build_main.py:607-613`,
`depend/analysis.py:686-695`; U23), and `spectracsMain.py` stays the
analysed entry, so its import graph is found as today (⛔ not `runpy` of a string — PyInstaller cannot see through
that, R4). The chdir lands before appdata resolves (`AppDataPathUtil.py:21-22` runs at import); the bootloader has
already made `sys.path` absolute, so moving the cwd is safe.

- **`tools/rthook_win_app.py`**: if `--fresh` is in `sys.argv` (anywhere), remove it and use suffix `-demo`; root =
  `SPECTRACS_CWD_ROOT` or `Path.home()\Spectracs` (the same home appdata uses, not `%USERPROFILE%`, U14);
  `os.chdir(<root>\spectracsPy<suffix>)` (created if missing); then D5.
- **Shape of both hooks (U14 — the test seam):** a pure `_plan(argv, environ, home, platform) -> (cwd, argv, log)`
  and an `_apply(plan, sysmod, osmod)`; the side effects run only under `if getattr(sys, "frozen", False):`, then
  the helper names are `del`-eted — hooks share `__main__` globals with `spectracsMain`. Tests load the file with
  `importlib.util.spec_from_file_location`, call `_plan` with `platform="win32"`, and `_apply` against `tmp_path`
  and a `SimpleNamespace` for `sys`.
- **`tools/rthook_win_server.py`**: `chdir` to `…\spectracsPy-server`; ⛔ **never adds or strips arguments** —
  any argument switches `spectracsServerAppImageEntry.py:20` to the stock CLI, and `--fresh` would hit argparse.
  With **no** arguments (the loopback mode) it does the 8g.3 check of `AppRun.server`: refuse if 8091 is already
  bound. ⭐ This matters more on Windows: Pyro5 defaults to `SOCK_REUSE=True` (`Pyro5/configure.py:50`), and on
  Windows `SO_REUSEADDR` lets a **second daemon bind 8091 silently**. ⇒ the hook also sets
  `PYRO_SOCK_REUSE=false` in `os.environ` (U15): Pyro5 builds its config from `PYRO_*` at import and nothing
  resets it ⇒ no Pyro5 import in the hook, and the stock-CLI path is covered too. The port check runs only when
  `len(sys.argv) == 1`: `socket.create_connection(("127.0.0.1", 8091), timeout=1)` succeeds ⇒ print why, `sys.exit(1)`
  (U16). The server hook redirects **nothing** (D5); it only sets `sys.stdout.reconfigure(errors="backslashreplace")`
  when stdout is not None (U7).

⇒ Data lands in `%USERPROFILE%\spectracsPy\` and `%USERPROFILE%\spectracsPy-server\` (B7: no dot on Windows),
**independent of where the zip was unpacked**. `--fresh` ⇒ `%USERPROFILE%\spectracsPy-demo\` — a double-click
cannot pass it, so `START_HERE.txt` documents a second shortcut. `SPECTRACS_CWD_ROOT` moves only the cwd, **not**
the data dir (appdata = home + cwd basename) — that is why verify uses `--fresh`, not a `-verify` dir (S5).

### D5 — The frozen Windows app logs to a file; the server keeps its console

The app is built windowed (`console=False`, no console window behind it). The app hook therefore points
`sys.stdout` and `sys.stderr` at **`spectracs.log` in the cwd folder** — the same place as Linux
(`AppRun.app`), i.e. `%USERPROFILE%\Spectracs\spectracsPy\spectracs.log` — opened
`"a", buffering=1, encoding="utf-8", errors="backslashreplace"` (U7: the locale default is cp1252, and 15 `print()`
calls in sciens/-core carry "→"/"●" ⇒ each would raise `UnicodeEncodeError` mid-run), with a start banner holding
the release manifest — or, when there is none yet (the by-hand builds W0.4/W0.5), `sys.executable` + argv (U18) —
and `faulthandler.enable(<log>)` for native crashes in cv2/Qt (U8). The default `sys.excepthook` already writes to
the redirected stderr; no custom one. ⚠ Known degradation: Qt's own qWarning output goes to OutputDebugString in a
windowed Windows app, not to fd 2 ⇒ unlike Linux it does not reach the log (UNVERIFIED, U8).
`disable_windowed_traceback=True` on win32 — ⛔ but it does **not** remove PyInstaller's modal MessageBox; it only
replaces the traceback in it with "this feature is disabled" (`PyInstaller/building/api.py:337-338`, U1). ⇒ The
real guard against a headless hang is that **every headless flag (`--check-db`, `--check-lamp-imports`) catches
`BaseException` itself**, prints the traceback, flushes both streams and leaves with `os._exit(code)` — it never
reaches the bootloader's error path. `Wait-Process -Timeout` stays as the safety net (§5.1.5). ⭐ Better than Linux, where the frozen app's `print()` never
reached a redirected stdout (Linux spec §18.2): on Windows the `CaptureBackend:` lines land in the log — and from
W1.2 on the CAPTURE-SETTINGS line too (until then it reads "unavailable", R7). The **server** is built with
`console=True`: its window is the "it is running" sign and closing it stops it, like the terminal on Linux.

### D6 — The server is an independent artefact, started by hand only when needed — ⛔ no launcher

Edwin, 2026-10-07: *"we want the server to be an independent artefact and to be only started manually on demand
as usually the server will run on the internet and starting it locally is not needed"*. ⇒ Same as the Linux D1:

- **two separate zips** — `Spectracs-<tag>-win64.zip` (the app) and `Spectracs-Server-<tag>-win64.zip`;
- the app never starts, waits for or stops a server; in production it talks to the **internet** server;
- the local server is a master/dev/demo tool: start `SpectracsServer.exe` by hand, then the app finds it on
  loopback first (`getProxy`), exactly as on Linux;
- ⛔ no combined launcher, no Job Object, nothing in the app zip that knows a server exists.

### D7 — The icon

`makeIcon()` is a bash heredoc inside `buildAppImages.sh:74-98`. ⇒ Extract it to **`tools/makeIcon.py`** (both
build scripts call it); it writes the 256 px PNG for Linux and a multi-size `.ico` (16/32/48/256, Pillow) for
Windows, **on Linux**, before the sources go to the VM. PyInstaller honours `icon=` on Windows only.
The script is the heredoc moved **verbatim** (the PNG must stay byte-identical, §12 W0.3 gate); CLI
`makeIcon.py --logo <png> --out <png> [--frame] [--ico <ico>]`. ⛔ The build never writes into a repo
(`buildAppImages.sh:8`) ⇒ the `.ico` is written into the build target, and the spec reads its absolute path from
**`SPECTRACS_ICON_ICO`** (app) and **`SPECTRACS_ICON_ICO_SERVER`** (the framed server icon), dropping `icon=`
when unset (U9).

### D8 — Same toolchain pins as Linux

Python **3.10.11** (python.org's last 3.10 Windows installer; the Linux venv has 3.10.12 — the patch level does
not touch numerics), PyInstaller **5.10.1**, `pyinstaller-hooks-contrib` at the Linux version, and
`requirements.txt` — ⚠ with **one platform split** (§6.6b, U19): `opencv-python-headless==4.7.0.72;
sys_platform != "win32"` and `opencv-python==4.7.0.72; sys_platform == "win32"` (same OpenCV version; the Windows
wheel adds MSMF and Win32 HighGUI, no Qt). Done in W0 (W0.3b), so the W0 zip carries the same cv2 as W1. In the
VM, `pip uninstall opencv-python-headless` **first** — both wheels own `cv2/`. `comtypes` + `pygrabber` stay W1
(W1.6); ⚠ W1 risk: comtypes' code generation (`GetModule`, `comtypes.gen`) in a frozen build. ⭐ A Windows/Linux difference in a measurement can then only come from the OS layer,
not from a different numpy/scipy/OpenCV. ⚠ `opencv-python-headless` 4.7.0.72 is the OpenCV whose MSMF/DSHOW
behaviour W1 measured — do not upgrade it on one OS alone. "Same" means: the `requirements.txt` pins + PyInstaller
+ hooks-contrib match and `pip check` is clean — **not** `pip freeze` equality (Linux has dev extras, Windows adds
`pefile`/`pywin32-ctypes`).

### D9 — A headless `--check-db` flag in `spectracsMain` (both OSes)

The Linux verify ends the app with `timeout 40` (`buildAppImages.sh:194`) because `--fresh` opens the GUI and never
exits. Windows has no such `timeout`, and a windowed exe started over ssh returns at once. ⇒ **`--check-db`**, a
sibling of `--check-lamp-imports` (`spectracsMain.py:95-100`), no QApplication:

- **Where (U2):** right after `import os, sys` (`spectracsMain.py:1-2`), **before** the view-tree imports (`:4-12`) —
  otherwise a module missing from the frozen bundle raises before the check, and that is U1's dialog. The imports
  happen **inside** its `try` (incl. `MainContainerViewModule`) ⇒ the check also proves the import graph. Verified:
  those imports need no QApplication and touch no DB.
- **What it prints (U3):** `check-db ok: app db <dbRev> head <scriptHead> at <dbFilepath>`. `dbRev` = the DB's
  `alembic_version` (`MigrationContext…get_current_revision()`); `scriptHead` = the bundled script tree's head,
  through a **new public helper in `-model`** (Edwin, 2026-10-08 — not the private `_config`). On a fresh DB the
  pair only proves create_all + stamp; the build compares `scriptHead` with a Linux-side
  `ScriptDirectory.from_config(Config(<src>/spectracsPy-model/alembic/app/alembic.ini))`. ⭐ The printed path proves
  at W0.5 that D4's chdir landed (`%USERPROFILE%\spectracsPy-demo`).
- **Exit codes:** 0 ok · 3 `dbRev != scriptHead` · 1 any exception (`except BaseException` → traceback → flush →
  `os._exit`, U1).
- `--fresh` exists only in `AppRun.app:8`, not in `spectracsMain` ⇒ on a Linux AppImage the order is
  `--fresh --check-db`; on Windows the hook strips `--fresh` from anywhere (D4).
- ⚠ **Testing from source (U21):** from the repo cwd it would resolve to `~/.spectracsPy` — the real archive —
  and migrate it. ⇒ the test runs it in a subprocess with `HOME=tmp_path`, cwd `tmp_path/spectracsPy-demo`,
  `QT_QPA_PLATFORM=offscreen`.
- **Who uses it:** the Windows build (§5.1) from W0.6. The Linux `buildAppImages.sh` switches to it **only once a
  tag contains W0.2** — not in W0.3, whose gate rebuilds an older ref without the flag (U22).

Code change in `spectracsPy` + one helper in `-model` (W0.2).

---

## 4 — W0: the bundle

### 4.1 Layout — two zips (D6)

```
Spectracs-<tag>-win64.zip
  Spectracs-<tag>-win64\
    Spectracs.exe + its DLLs/pyds next to it   (PyInstaller 5.x onedir; `_internal\` is 6.x)
    RELEASE_MANIFEST.txt    ← tag, per-repo SHAs, recipe SHA, toolchain — same content as Linux
    START_HERE.txt          ← where data and the log live, the Unblock step (§7.4), the firewall prompt (§7.5)

Spectracs-Server-<tag>-win64.zip
  Spectracs-Server-<tag>-win64\
    SpectracsServer.exe + …
    RELEASE_MANIFEST.txt
    START_HERE.txt          ← "only for local/dev use; the app normally uses the internet server"
```

### 4.2 What W0 deliberately does not fix

- B1–B5 (camera): W0 runs on the **virtual spectrometer** and on the archive. A real-camera capture on a W0 build
  is "not supported", not "broken".
- B6 is **partly** W0: the setup-screen crash is closed by the W0.1 guard (R3; the poll thread and status module
  already catch it). The presence light stays "absent" until W1.1.
- B2 does **not** crash — both callers catch `Exception` (R7); it only empties the CAPTURE-SETTINGS line.
- The lamp is **not tested** in W0: `LampService` exists only for a real sensor
  (`MainStatusBarViewModule.__configureLamp(not sensor.isVirtual)`, `AbstractPluginExecutionView.py:264-267`).
  W0 proves only that zeroconf imports (`--check-lamp-imports`); "lamp off when the window closes" moves to W1.6.
  ⚠ But it **runs** in W0 (U20, accepted by Edwin 2026-10-08): §8.1.4 logs in `elpUser`, whose sensor is the real
  ELP ⇒ `LampService` (zeroconf on 5353, maybe the §7.5 firewall prompt) and the 2 s USB poll thread start. With no
  libusb backend the poll thread reports "absent" once and stops (W0.1, U4) instead of logging tracebacks.

---

## 5 — The build: `tools/buildWindows.sh` (runs on Linux)

Same contract as `buildAppImages.sh`: `--app/--server/--tag/--out/--keep/--no-verify`, refuses to build inside a
git work tree, timestamped output folders, `latest` link. Differences (S2): `--tag` accepts **any git ref**
(default `main`; dev builds from the committed `main`, the release tag comes last); output under
**`~/spectracs-build/windows/`** (its own `latest`, out of reach of the Linux prune); and — ✅ **as built
(2026-10-08), instead of worktrees** — the sources are **`git archive <sha>` of each repo**, resolved per repo from
the ref: no `.git` to exclude, no worktree registrations in seven repos, and nothing on disk that a moved ref could
reuse stale (the reason worktrees were to be keyed by SHA). A non-tag ref labels the zips `<ref>-<sha7>`
(`Spectracs-main-bf5ac3f-win64.zip`), a tag by its name. The VM half is **`tools/windows/buildInVm.ps1`**, shipped
in the recipe; each build gets a fresh `C:\spectracs-build\b-<out name>\`, removed after a good copy back, kept
on failure.

```
 1. worktrees at <tag>                       (shared with buildAppImages.sh — same src-<tag>/ folder)
 2. tools/makeIcon.py → spectracs.ico        (on Linux, D7)
 3. tar -cf src.tar (worktrees minus .git,   scp → VM, `tar -xf` there (bsdtar ships with Win10),
    + recipe: specs, entry, hooks, .ico)     sha256 compared on both ends
 4. in the VM:  venv\Scripts\pyinstaller …   $env:SPECTRACS_SRC_ROOT set INSIDE the remote PowerShell command
 5. in the VM:  licence gate on dist\        (again on the artefact, as on Linux N8)
 6. in the VM:  verify (§5.1)
 7. tar dist\ → scp back to Linux
 8. on Linux:   RELEASE_MANIFEST.txt + START_HERE.txt into each folder, THEN `zip -r` → 2 zips
```

- **VM host** `spectracs-win` comes from `~/.ssh/config`; key login, never a password in the script.
- **sshd's DefaultShell = PowerShell** (V0.1): cmd's `set X=… && y` keeps a trailing space in the value.
- ⛔ No `tar | ssh` streaming: Windows PowerShell 5.1 can mangle binary stdin passed to a native command
  (unverified, but cheap to avoid) ⇒ file + `scp` + checksum.
- **Zip on Linux**, not `Compress-Archive` (slow; backslash entry names) — and only after the manifest is in.
- The worktrees' `.git` *files* point at Linux paths ⇒ excluded from the tar.

### 5.1 Self-verification (in the VM, headless, no GUI, no timeouts)

Mirrors the Linux script (`buildAppImages.sh:185-225`), adapted:

1. **Alembic head** — `Spectracs.exe --fresh --check-db` (D9) ⇒ the hook moves it to `spectracsPy-demo`, which
   in the build VM is throwaway (the build user is not a demo user). Read the `check-db ok:` line from the log;
   exit code 0; `scriptHead` == the head of the tagged `-model` Alembic tree; the path is under `spectracsPy-demo`.
2. **Lamp imports** — `Spectracs.exe --check-lamp-imports` (zeroconf's Cython modules bundled; exits before Qt).
3. **Port-taken refusal** — start a dummy listener on 8091, start `SpectracsServer.exe`: it must refuse (D4).
4. **Pair proof** — start `SpectracsServer.exe` (no args ⇒ loopback), wait for 8091, log in as
   `masterUserExakta` with `SpectracsPyServerClient` **from source** (the VM venv, `PYTHONPATH` = the worktrees),
   print role + serial; calibration is **information only** (a fresh VM server DB has none until it is authored
   once). Stop with `Stop-Process -Id <pid>`.
5. Any step that could hang runs as `Start-Process -PassThru` + `Wait-Process -Timeout` + `Stop-Process -Force`.

---

## 6 — W1: the camera on Windows

The order matters: **6.1–6.2 make the camera reachable, 6.3–6.4 make its numbers comparable, 6.5 proves it.**

### 6.1 Find the camera by VID/PID (B1, B6)

Windows has no sysfs. The cv2 index on Windows is the **position of the device in the backend's own enumeration**
(MSMF and DSHOW enumerate separately and not necessarily in the same order). ⇒ `SensorCaptureIndexResolver` gets
a `win32` branch that enumerates video-input devices **through the same backend `CaptureBackend` will open**, reads
each device's symbolic link / device path (it contains `vid_32e4&pid_8830`), and returns the matching index.

Candidates, decided in the spike (§6.7 step 1):
- `cv2-enumerate-cameras` (small pip package, MSMF + DSHOW, returns index + VID/PID + path) — least code;
- `pygrabber` (DSHOW only, device names, no VID/PID ⇒ weaker);
- our own ~60 lines of `ctypes` against Media Foundation (`MFEnumDeviceSources`) — no new dependency.

⭐ The **presence light** (B6) then uses the same enumeration ("is a device with this VID/PID listed?") instead of
pyusb/libusb on Windows ⇒ no libusb DLL in the bundle, and pyusb stays a Linux-only dependency.

### 6.2 Pick and pin the backend: MSMF, explicitly

`CAP_ANY` lets OpenCV choose, which is behaviour, not a contract (the same lesson as the pixel-format pin,
`SPEC_capture_quality.md` §16.39.5a). ⇒ `apiPreference = cv2.CAP_MSMF` on `win32`, with DSHOW as the documented
fallback if the spike finds MSMF cannot hold 2592×1944 YUY2. The chosen backend is printed in the CAPTURE-SETTINGS
line.

### 6.3 Own the YUYV→BGR conversion (B3, B4)

**Why the format is not OS-agnostic:** the bytes the ELP sends over USB are the same on every OS (YUYV 4:2:2). What
differs is **who turns them into the BGR array** `cap.read()` returns:

- on Linux, OpenCV's V4L2 backend converts with OpenCV's own `cvtColor` — every Q%/Rv to date went through that;
- on Windows, MSMF asks Media Foundation for RGB24 and its video processor converts — its colour matrix (BT.601
  vs BT.709), its range handling (16–235 vs 0–255) and its chroma upsampling are Microsoft's choices, not ours.

The MAD==0 bug showed how sensitive the pipeline is to the exact 8-bit codes. Edwin, 2026-10-07: own conversion
*"that's the way to go"*. ⇒ **Bit-identical 8-bit values on both OSes, by construction:**

1. **Enforce YUYV.** Request FOURCC **`YUY2`** on Windows (B3: same bytes, Windows' name) **before** the resolution,
   as on Linux; accept `YUY2` **or** `YUYV` in the read-back. MSMF and DSHOW both pick the camera's media type
   from the FOURCC request — the spike (§6.7) confirms the ELP's 2592×1944 YUY2 mode is offered and granted.
   ⛔ **On Windows there is no silent fallback**: if the read-back is not YUY2 (e.g. MJPG), the capture refuses to
   measure and says why — a JPEG spectrum must never become a Windows Rv. (Linux keeps today's guarded fallback,
   `__reopenUnforced`; changing it is not part of W1.)
2. **`CAP_PROP_CONVERT_RGB = 0`** ⇒ the backend hands over the raw YUY2 buffer untouched (the payload from the
   camera; `usbvideo.sys` does not rewrite it).
3. **Convert ourselves** with `cv2.cvtColor(raw, cv2.COLOR_YUV2BGR_YUY2)`, in one shared function.
4. ⭐ **Linux uses the same path** (step 2 + 3 on V4L2 too). OpenCV's V4L2 backend already converts YUYV with this
   very `cvtColor` internally, so the Linux frames should not change by a single code. ⇒ **gate for the Linux
   side:** convert the **same grabbed frame** both ways — one `grab()`, then `retrieve()` with
   `CONVERT_RGB=1` (old path) and with `CONVERT_RGB=0` + our `cvtColor` (new path); two separate grabs would differ
   by sensor noise and prove nothing. The per-pixel difference must be **exactly 0**. (If V4L2 will not toggle the
   flag between grab and retrieve, the spike says so and the proof falls back to reading OpenCV 4.7's
   `cap_v4l.cpp` `convertToRgb`.) Zero is a proof, not a statistic, so no Linux null run is needed; anything
   ≠ 0 stops the Linux change and only Windows uses the new path.

Same raw bytes + same function ⇒ same 8-bit values. What is then left between the OSes is only **what the camera
does before the bytes leave it** — exposure, gain, white balance, set through the controls ⇒ §6.4.

⚠ The shape of the raw buffer with `CONVERT_RGB=0` (1×N bytes vs H×W×2) differs between OpenCV backends and
versions ⇒ the spike measures it on 4.7.0.72 (MSMF, DSHOW and V4L2) and the reshape is written against that.

### 6.4 Exposure: a per-backend mapping, and the step-size question (B5) ⭐ the science risk

Everything that names an exposure today is in **V4L2 units**: `SpectrometerSensorSettings` (*"Values are V4L2
manual-exposure units"*), `calibrationExposure=150` for the ELP, `DevSpectralPlugin.exposure = 90`, and the AE
ladder in `AutoExposureLogicModule`, which bisects an integer range read by ioctl (`__exposureRange`).

On Windows the standard exposure property is normally **log₂ seconds** (−3 = 1/8 s, −4 = 1/16 s, …). That raises
two separate problems:

1. **Units.** A mapping `v4l2Units → windowsValue` per backend. UVC itself speaks 100 µs units; Windows' driver
   (`usbvideo.sys`) translates. The mapping is **measured** in the spike (sweep both, compare delivered brightness
   on the same lamp), not computed from the documentation.
2. **⭐⭐ Granularity.** If Windows only offers whole log₂ steps, the AE can land anywhere between ~50 % and 100 % of
   its target 245 — a factor-2 coarser exposure than on Linux. That costs dynamic range in the dark Q band, i.e.
   it can widen σ_fill. Options, in order of preference — decided by what the spike measures:
   - (a) the backend exposes finer steps after all (some UVC drivers and the MSMF *extended* exposure control in
     100 ns units do) ⇒ use them;
   - (b) accept whole steps and let the AE compensate with frame averaging (`FRAMES`) ⇒ only if §6.5 passes;
   - (c) talk UVC directly (libuvc over libusb) — ⛔ needs the camera re-bound to WinUSB (Zadig), after which no
     other Windows program sees it as a camera. Possible for a dedicated instrument PC, ugly for anything else.

**Every place that names an exposure (R5, S6)** — all switch to "range from the backend" on win32:

| site | today |
|---|---|
| `-model SpectrometerSensorUtil.py:26` | ELP `calibrationExposure=150` (V4L2) |
| `spectracs-plugins DevSpectralPlugin.exposure = 90` | signed, DB-served plugin |
| `CapturePanel.py:76-83, 608` | `MIN=1`, `FALLBACK=150`, `MAX_FALLBACK=5000`; rejects `high <= 1` ⇒ a −13…−1 range is thrown away |
| `CapturePanel.py:747-752` | stores `int(applied)` ⇒ truncates a fractional Windows value |
| `DevCaptureViewModule.py:40` | same constants |
| `…WavelengthCalibrationViewModule.py:162` | `requestAutoExpose(1, 500)` hard-coded |
| `CameraWarmupService.py:42-89` | V4L2 values |
| `CaptureBackend.py:127-128` | legacy `win32` default `-3` |
| `AutoExposureLogicModule` | direction-agnostic, copes with a non-positive range (`:79`) ⇒ **unchanged** |

Decisions:
- **The plugin contract stays V4L2 units**; the host converts per backend. Recorded in the plugin_sdk docs
  (`spectracsPy-core`) — no signed plugin needs re-publishing.
- `exposureApplied` is **not** a DB column: a plain attribute (`-model SpectralWorkflow.py:66-73`) that travels in
  the `toReportJson` header (`:148`) — the JSON embedded in the PDF and sent to LIMS. ⇒ **no Alembic migration**.
  It is stored as a **float**, and a sibling header key **`exposureUnit`** is added (absent ⇒ V4L2, so every
  archived report stays valid). `diagnostics/d2r_all_runs.py` / `report_reconstruct.py` read it.
- `__exposureRange()` reads the range from the backend on win32; `import fcntl` moves behind the guard in both
  `__queryControl` and `__exposureModeName`, with per-field catching (R7).

### 6.4b The other controls (R6)

The measurement path freezes white balance at 6500 K, `AUTO_WB=0`, `BACKLIGHT=0`, `GAIN=0`
(`CaptureBackend.py:126-147`, the §14.8 reference-tilt fix), and selects manual exposure with `AUTO_EXPOSURE=1`
— which means "manual" **only on V4L2** (on DSHOW a non-zero value plausibly means *auto*). If MSMF ignores
`WB_TEMPERATURE`, auto-WB keeps running and nothing reports it. ⇒ every control is set **and read back** per
backend; a capture whose read-back does not prove WB frozen is not a measurement. ⚠ UVC control values **stay in
the camera** across a VMware hand-over (no power cycle) ⇒ every open sets every control, on both OSes.

### 6.5 The gate: null run on Windows vs Linux ⭐⭐

Same oil, same lamp, same fill protocol as the null-run series (`SPEC_capture_quality.md` §16.26). The question
it answers: **does an Rv measured on Windows mean the same as one measured on Linux?** Two ways it could fail —
Windows scatters more (noise), or Windows reads systematically higher/lower (offset).

- **⛔ Interleave, never "all Linux, then all Windows".** A second fill reads lower (Rv fell A→B in 6/6, 2026-09-14)
  and light browns the sample ⇒ in a block design the order effect would masquerade as a Windows offset. ⇒ fills
  alternate L W L W …, each a **fresh aliquot from the dark** (T1 protocol). In the VM this is cheap: host and VM
  run at once and the ELP is handed over between fills (VMware's removable-devices menu; every open re-sets all
  controls, §6.4b). On the real Win11 PC it means moving the USB cable between two machines each fill.
- **The Linux arm doubles as the owed σ_fill for `Rv`** under one controlled protocol.

⏸ **POSTPONED 2026-10-07 (Edwin: *"i want to postpone this test! and to discuss this later"*).** The table below is a
**proposal only**, not decided; it is to be discussed before the run. W1.0–W1.7 do not depend on it.

**Pre-registration (O3 — Edwin decides BEFORE the run, nothing is tuned afterwards; M9 rule):**

| # | decision | proposal |
|---|---|---|
| P1 | oil | one mid-range oil with a known Rv, enough for all fills from one bottle |
| P2 | fills per OS | **5 + 5**, interleaved, starting with Linux |
| P3 | noise criterion | σ_fill(Windows) ≤ **1.5 ×** σ_fill(Linux) |
| P4 | offset criterion | \|mean Rv(W) − mean Rv(L)\| ≤ **1 × σ_fill(Linux)** — an offset smaller than the scatter between two fills of the same oil adds no more uncertainty than refilling the jar already does |
| P5 | if it fails | Windows ships without real-camera measurement; the failure mode (noise vs offset) picks §6.4 (b) or (c) |

⚠ With 5 + 5 fills the test only catches **large** differences (an offset of ~1 σ_fill is at the edge of what 5 per
side can see). That is deliberate: it is a go/no-go for "Windows is not broken", not a proof of equality. A finer
claim would need more fills — decide that in P2 if wanted.

### 6.6 Not in W1, but worth knowing

The ToupTek IMX290 mono (bought 2026-09-17) ships a **native Windows SDK** (`toupcam.dll`, µs exposure, RAW12) —
on Windows it is arguably the *easier* camera, with none of §6.3/§6.4. If the production camera moves to it,
W1's UVC work shrinks to the ELP/Microdia legacy path.

### 6.6b W1.0 RESULTS — the spike, run 2026-10-07 in the VM ⭐⭐

`diagnostics/windows_camera_probe.py`, ELP `32e4:8830` passed through (VMware Player 17.5, Windows 10 Home 19045),
lamp on, **empty jar**, OpenCV 4.7.0.72, Python 3.10.11. Three runs: full DSHOW + MSMF (headless), MSMF open
diagnosis + quick DSHOW, full MSMF (non-headless wheel).

| question | DSHOW (`opencv-python-headless`) | MSMF |
|---|---|---|
| found by VID/PID (`cv2_enumerate_cameras` 1.4.0) | ✅ index 0 | ✅ index 0 |
| opens at all | ✅ | ⛔ **not with `opencv-python-headless`** — the MSMF backend is absent from the headless Windows wheel ("backend is not available", also in 4.10.0.84). ✅ with **`opencv-python` 4.7.0.72** (non-headless) |
| YUY2 at 2592×1944 | ✅ granted, size read back exactly | ✅ (raw open reads back `YUY2`) |
| open → first frame | 3.5–3.7 s | 1.9 s (3.7 s raw) |
| frame rate | 3.6 fps | 3.64 fps |
| `CONVERT_RGB=0` | ⛔ **ignored**: still a 1944×2592×3 BGR frame ⇒ DirectShow converts, **our own conversion is impossible** | ✅ **raw YUY2**: `[1, 10 077 696]` uint8 = 2592·1944·2 ⇒ our `cvtColor` works |
| same grab, two retrieves (`CONVERT_RGB` toggled) | both succeed, but "raw" is BGR | ⛔ assertion in `cv::Mat` — toggling mid-stream breaks the stream ("Failed to select stream 0") |
| `AUTO_EXPOSURE` | read back −1 = unsupported; makes no difference | **no effect** under any value |
| exposure read-back | rounds to whole numbers (−12.5 → −12) | ⛔ **always −7** (broken read-back) |
| ⭐⭐ **exposure granularity** | **WHOLE log₂ STEPS ONLY** — every half step = its lower neighbour, 0 of 8 between | **WHOLE log₂ STEPS ONLY** — same, 0 of 8 between |
| delivered peak per step (this lamp, empty jar) | −10: 38 · −9: 99 · −8: 182 · −7: 218–255 | −10: 39 · −9: 104 · −8: 189 · −7: 255 |
| V4L2-style values (1…500) | clamped to −1 (≈ 0.5 s), clipped | same, clipped |
| `GAIN` | ✅ set + read back 0; 0→32 raises mean 21→33 | ✅ same |
| `BACKLIGHT` | ✅ 1→0 | ⛔ set returns True, read back stays 1 |
| white balance (`AUTO_WB`, `WB_TEMPERATURE`) | ⛔ unsupported (−1) | ⛔ unsupported (−1) |
| white balance (`WHITE_BALANCE_BLUE_U`) | read back **4600** (the camera's own value), ⛔ set returns False | ⛔ read back 1, set returns False |
| B/R ratio over the run | ⚠ **drifts**: 0.98→1.02 (run 1), 1.06→1.08→1.10 (run 2) ⇒ auto-WB is moving | stable 1.238 |
| `BUFFERSIZE` | unsupported | read back 1 |
| frames after an exposure step | **4 black frames**, then settled (~1.1 s) | **4 black frames**, then settled |

**What this means:**

1. ⭐⭐ **Exposure: whole doubling steps only, on both backends (§6.4 option (a) is NOT available through
   OpenCV).** With this lamp the best step under the AE target 245 is **−8 ⇒ peak 182–189 = 74–77 % of target**;
   −7 clips. On Linux the AE lands just under 245. So Windows loses about a quarter of the dynamic range here, and
   up to half in the worst case, depending on where the lamp falls between two steps.
2. ⭐⭐ **White balance cannot be frozen through OpenCV on either backend**, and on DSHOW the blue/red ratio was seen
   drifting by several % within minutes. The Linux measurement path freezes WB at 6500 K precisely because a
   drifting WB tilts the reference against the sample (§14.8). ⇒ **This is a second blocker, independent of the
   exposure steps** — own YUY2 conversion does not help, because WB is applied inside the camera before the bytes
   leave it.
3. **Conversion: only MSMF hands over raw YUY2**, and MSMF is only in the non-headless wheel. On Windows,
   `opencv-python` (non-headless) has a Win32 HighGUI, **no Qt** ⇒ no clash with PySide6. ⇒ requirements split:
   `opencv-python-headless==4.7.0.72; sys_platform != "win32"` + `opencv-python==4.7.0.72; sys_platform == "win32"`.
   ⚠ `CONVERT_RGB` must be fixed **at open** (toggling breaks MSMF) ⇒ §6.3's same-grab Linux proof cannot borrow a
   Windows trick; on Linux it is still to be tried (W1.4).
4. Gain works on both ⇒ a possible fine trim between exposure steps — but only if the ELP's gain is analogue
   (`diagnostics/gain_analog_or_digital.py` exists for that question); a digital gain only stretches 182 to 245
   without adding signal. And Linux pins gain 0 on purpose.
5. Not measured this time: the backend-vs-own conversion fit on MSMF (the `CONVERT_RGB` switch back to 1 broke the
   stream). Needs two separate opens; low priority now that MSMF + own conversion is the only raw path anyway.

**Options for the W1.1 decision (§6.4, extended by these results):**

| | route | exposure | white balance | cost / risk |
|---|---|---|---|---|
| (b) | OpenCV MSMF + own conversion, accept whole steps | ⚠ 74–77 % of target here | ⛔ not frozen | cheapest; **WB blocker remains** ⇒ only viable if WB can be fixed another way |
| (d) | **native UVC control through Windows**: DirectShow `IAMCameraControl` / `IAMVideoProcAmp` (or KS properties) via `comtypes`, frames still from MSMF | ⚠ probably still log₂ (to be checked) | ✅ likely — `WHITE_BALANCE_BLUE_U` *reads* 4600, so the control exists; OpenCV just fails to set it | a second, small spike: read the ranges/flags, set WB manual 6500 K, re-check the B/R drift |
| (c) | libuvc over WinUSB (Zadig) | ✅ 100 µs units like Linux | ✅ | camera no longer a Windows camera; driver swap per PC |
| (e) | a camera with its own Windows SDK (ToupTek, §6.6) | ✅ µs | n/a (mono) | production camera is open anyway (O2) |

⇒ ✅ **Done as W1.0b (§6.6c): (d) fixes white balance; exposure stays whole steps.**
⇒ **Recommendation (superseded by §6.6c):** run (d) as a short **W1.0b** spike before deciding — it is the only route that may fix
white balance without a driver swap, and it tells whether finer exposure exists below OpenCV. If (d) fails on WB,
Windows real-camera measurement with a UVC camera means (c) or (e).

### 6.6c W1.0b RESULTS — native UVC controls through DirectShow, run 2026-10-07 ⭐⭐

`diagnostics/windows_uvc_controls_probe.py`: controls via `IAMVideoProcAmp` / `IAMCameraControl` (comtypes, plumbing
from `pygrabber` 0.2), frames from MSMF as raw YUY2 + our own `cvtColor`, exposure −8, lamp on, empty jar.

**The camera's own control table (ELP under `usbvideo.sys`):**

| control | min | max | step | default | modes | found |
|---|---|---|---|---|---|---|
| Brightness | −64 | 64 | 1 | 0 | manual | 0 manual |
| Contrast | 0 | 64 | 1 | 32 | manual | 32 |
| Hue | −40 | 40 | 1 | 0 | manual | 0 |
| Saturation | 0 | 128 | 1 | 75 | manual | 75 |
| Sharpness | 0 | 6 | 1 | 3 | manual | 3 |
| Gamma | 72 | 500 | 1 | 100 | manual | 100 |
| **WhiteBalance** | **2800** | **6500** | 1 | 4600 | **auto + manual** | 4600 **auto** |
| BacklightCompensation | 0 | 2 | 1 | 1 | manual | 0 ⚠ (left by the W1.0 probe — UVC controls persist in the camera) |
| Gain | 0 | 100 | 1 | 0 | manual | 0 |
| **Exposure** | **−13** | **−1** | **1** | −7 | auto + manual | −7 manual |

**White balance — ✅ SOLVED by the native route:**

| step | read back | blue/red |
|---|---|---|
| manual 6500 K | 6500, manual | 1.715 |
| manual 3000 K | 3000, manual | 4.971 ⇒ the control really acts |
| manual 6500 K again | 6500, manual | 1.714 ⇒ back to the same colour |
| hold 6500 K, 60 frames (~17 s) | — | span **0.28 %** |
| (baseline, auto, 60 frames) | — | span 0.38 % (auto happened to be quiet this time) |
| release + re-bind the handle | 6500, **manual** | ⇒ the setting **persists in the camera** |

⇒ The Linux measurement path's WB freeze at 6500 K (§14.8) **can be reproduced on Windows**: set through
`IAMVideoProcAmp`, not OpenCV. Same for Gain/Backlight/the rest. Because the settings persist in the camera, the
app must set **every** control explicitly on every open (§6.4b) — on Linux too, or a Windows session leaves e.g.
Backlight=0 / WB manual behind for the next Linux session.

**Exposure — ⛔ still whole log₂ steps, now confirmed at the driver level:** `IAMCameraControl` reports the range
−13…−1 with **step 1**. Set through DirectShow or OpenCV, the same value gives the same brightness (−9: peak 65,
−8: peak 142 in this run). There is no finer exposure under `usbvideo.sys`.

⚠ Peaks differ from W1.0 (−8: 142 here vs 182–189 there) — here WB is manual 6500 K and the conversion is ours;
there WB was auto and the conversion the backend's. Not separated; it does not change the verdict.
Hint only, not proven: with WB on auto the blue/red ratio was 1.44 through our own conversion here vs 1.24 through
MSMF's conversion in W1.0 — consistent with MSMF converting differently, which is what §6.3 avoids anyway.

**What is left: exposure granularity only.** Routes, given that the gain is **analogue with 1.51× range**
(`SPEC_capture_quality.md` §16.23.6d, measured on Linux):

| | route | where the AE can land (target 245) |
|---|---|---|
| (b) | whole steps only | 50–100 % of target, depending on the lamp (here: 142 = 58 %) |
| (b+) | whole steps **+ analogue gain as the fine trim** (1.0–1.51×) | **76–100 %** worst case; here 142 × 1.51 = 214 = 87 % — but Linux pins gain 0 on purpose, so ref and sample must share the gain (T = S/R cancels it only then) and the null run must include it |
| (c) | libuvc over WinUSB | 100 µs steps like Linux, driver swap per PC |
| (e) | camera with own SDK (ToupTek) | µs steps |

**✅ W1.1 DECISION (Edwin, 2026-10-07):** *"would accept that for now. fine graining could be done later"* ⇒
- **controls: route (d)** — every UVC control set natively through `IAMVideoProcAmp` / `IAMCameraControl` on
  Windows (WB manual 6500 K, gain 0, backlight, and the rest explicitly, on every open);
- **exposure: route (b)** — whole log₂ steps, gain stays **0** (the Linux rule is kept); the AE picks the brightest
  step that does not clip. A "Windows exposure is coarse" note goes into the CAPTURE-SETTINGS line;
- **fine-graining is a later, separate task**: (b+) analogue gain trim, (c) WinUSB, or (e) another camera.

Unit bridge, for the exposure converter (W1.5): Windows step `k` = 2^k s; V4L2 = 100 µs units ⇒ `v4l2 = 10 000 · 2^k`.
So −8 = 3.9 ms ≈ V4L2 39, **−7 = 7.8 ms = V4L2 78** (exactly the ELP's old CFL calibration value), −6 = 15.6 ms ≈ V4L2
156 (next to today's `calibrationExposure=150`). Between two Windows steps Linux can choose freely — that is the whole
difference.

### 6.7 W1 run order

See §12, rows W1.0–W1.8. The order: spike (right after V0) → **Edwin decides §6.4 (a)/(b)/(c)** → resolver →
backend + own conversion → Linux bit-identical check → exposure sites + other controls → click-through → ⏸ null
run. ⚠ If the decision is (c) (WinUSB), W1.1's enumeration approach is void and W1 is re-planned.

---

---

## 7 — Risks and things learned in advance

### 7.1 Wheels and DLLs
A pin without a Windows wheel would surface at `pip install` in the VM — the first W0 step, so it fails early.
Qt's platform plugin (`qwindows.dll`) and the MSVC runtime are bundled by PyInstaller's hooks; the Linux lesson
"copying host libs bundles glibc" has no Windows twin, but the gate should still list unexpected DLLs from
`C:\Windows\System32` in the bundle (the old spec copied `libusb0.dll` from there).

⭐ **Observed 2026-10-07 (V0.2):** `pyspectra==0.0.1.2` pulls `spc-spectra==0.4.0` (same version as Linux), an
**sdist** whose `setup.py` imports numpy ⇒ under pip's build isolation it fails with `No module named 'numpy'`.
Fix: install `numpy==1.26.4 setuptools wheel` first, then `pip install --no-build-isolation spc-spectra==0.4.0`,
then `-r requirements.txt`. (pyspectra is only used lazily for `.dx` import, `ImportSpectrumLogicModule.py:9-11`.)

### 7.2 Path separators and hard-coded paths
`sciens/` uses `os.path`; the hard-coded `/home/nidwe72/…` paths live in `diagnostics/` and `docs/tools/`, which are
not in the bundle. ⇒ A `grep` for `"/` path literals under `sciens/` and the plugins is part of W0 bring-up; the
expected result is "nothing", but it is checked, not assumed.

### 7.3 `signal` and process control
`automation/` registers `SIGHUP` (absent on Windows); `automation/` is not in the bundle. The lamp's exit hooks
(`tests/test_lamp_exit_hooks.py`: SIGTERM/SIGINT/SIGHUP) — ⚠ to check: the lamp must still switch off when the app
window is closed on Windows (`atexit` + Qt `aboutToQuit`); there is no SIGHUP there, and `taskkill` without `/F`
sends `WM_CLOSE`, not a signal. The duck confirmed `SIGHUP` is guarded by `hasattr` (`LampExitHooks.py:56-58`) and
`closeEvent` + `aboutToQuit` cover the window close. ⇒ Click-through item in **W1.6** (§8.2) — the lamp only
exists with a real sensor (§4.2).

### 7.4 SmartScreen and the "downloaded from the internet" marker (Mark-of-the-Web)

**What the marker is.** When a browser, Outlook, Teams etc. saves a file on an NTFS disk, Windows attaches a hidden
*alternate data stream* named `Zone.Identifier` to it — a tiny text file glued to the real one:

```
[ZoneTransfer]
ZoneId=3                          ← 3 = Internet (0 local, 1 intranet, 2 trusted, 4 restricted)
HostUrl=https://…/Spectracs-<tag>-win64.zip
```

**How it applies.** Starting an `.exe` that carries `ZoneId=3` sends it through **SmartScreen**: unsigned and without
reputation ⇒ *"Windows protected your PC"* → "More info" → "Run anyway". A file without the marker is not checked
(SmartScreen-wise; the antivirus still scans it).

**How it travels** — the part that decides whether the user ever sees the box:
- **Explorer's "Extract all"** copies the marker from the zip onto **every** extracted file ⇒ the exe is marked.
  Third-party unzippers vary (7-Zip only with its "propagate Zone.Id" option).
- **Only NTFS can hold it.** Copying to a FAT32/exFAT USB stick drops it ⇒ a zip handed over on a normal stick
  arrives clean. An NTFS-formatted stick keeps it.
- A file **created** on the machine (our build in the VM, a zip written by `Compress-Archive`) never has it.
- ⚠ Running an exe directly **from** a network share can raise a separate "Open File – Security Warning",
  depending on how Windows zones that share ⇒ `START_HERE.txt` says: copy to a local folder first.

**Removing it ("Unblock")** — ⭐ do it on the **zip, before extracting**; then nothing extracted carries it:
- Explorer: right-click the zip → Properties → General → at the bottom *"This file came from another computer…"*
  → ☑ **Unblock** → OK. (No checkbox there ⇒ the file has no marker.)
- PowerShell: `Unblock-File .\Spectracs-<tag>-win64.zip` — or, if already extracted,
  `Get-ChildItem -Recurse .\Spectracs-<tag>-win64 | Unblock-File`.
- Check: `Get-Content .\Spectracs-<tag>-win64.zip -Stream Zone.Identifier` (error = no marker).
- A lab's IT can also allow the program centrally (Defender/Intune policy, or by publisher once it is signed).

⛔ **The one case Unblock does not cover: Smart App Control** (Windows 11; on only for some fresh installs, and
often switched off by itself). When it is on, it blocks unsigned/unknown exes **and** DLLs with no per-app
override. A PyInstaller bundle is hundreds of unsigned `.pyd`/`.dll` files ⇒ on such a machine only signing helps.

**Not part of the exe.** The marker lives in the **file system** next to the file, not in its bytes: the exe's
content and hash are unchanged, which is exactly why a FAT stick can drop it. (The opposite is the Authenticode
**signature** — that *is* embedded in the exe and travels with it everywhere.)

**And an installer (W2)?** A downloaded `Setup.exe` carries the marker ⇒ SmartScreen checks **the installer**, once.
The files it then writes into the install folder are *created* on the machine by the installer ⇒ **no marker** ⇒
`Spectracs.exe` starts without a SmartScreen box afterwards. ⇒ With an installer, signing the **`Setup.exe`**
covers SmartScreen; only Smart App Control still checks the installed binaries one by one. ⭐ W2 installs
**per user** (`%LOCALAPPDATA%\Programs\Spectracs`, no admin rights) — lab PCs often have no admin for the user,
and Program Files would also need a UAC prompt.

⇒ W0/W1: unsigned, the Unblock step in `START_HERE.txt`. W2 decides on signing: an OV code-signing certificate
(~€200–400/yr, key on a hardware token or cloud HSM; the warning fades only as reputation builds — EV no longer
skips that since 2024), or Microsoft's cloud signing service (~$10/month; ⚠ eligibility for an individual in
Austria to be checked). ⚠ For Smart App Control, signing means **every** binary in the bundle, not only the exe.

### 7.5 Firewall and the Shelly plug
Zeroconf/mDNS (lamp discovery) opens a UDP socket on the LAN ⇒ Windows Defender Firewall asks once ("allow on
private networks"). And **in the VM, mDNS only reaches the plug with bridged networking** — NAT hides the LAN.
⇒ VM network = bridged; `START_HERE.txt` mentions the firewall prompt.

### 7.6 The VM itself
- **Hypervisor** (O4 ✅ answered: **VMware**). For the record: **KVM/QEMU** (in the Linux kernel, `virt-manager` as GUI, `usb-host` passthrough) or
  ✅ **VMware Workstation** — free for personal and commercial use since Nov 2024 (Workstation *Player* was folded
  into it); its USB 2/3 passthrough handles webcams well. ⚠ VMware's own kernel modules (`vmmon`/`vmnet`) must be
  rebuilt after a Linux kernel update and occasionally break on a new kernel; the download needs a Broadcom account.
  ⛔ **VirtualBox** last: USB 2/3 needs the Extension Pack, and it is known to drop isochronous camera frames.
- **USB passthrough** of a UVC camera at 2592×1944 is the weak spot of any VM. Dropped frames are a **VM** artefact and
  could leak into the null run ⇒ the final W1 sign-off is on a **real Windows PC** (§6.5).
- OpenSSH server (Windows optional feature) + key login, once.
- A Windows licence for the VM — Edwin's call, noted so it is not a surprise.

---

## 8 — Acceptance

### 8.1 W0 — the click-through (in the VM)

1. unblock + unzip both zips anywhere (also: a path with a space). ⭐ To test Unblock at all, set a
   `Zone.Identifier` on the zip by hand first (a locally made zip has none):
   `Set-Content x.zip -Stream Zone.Identifier -Value "[ZoneTransfer]`nZoneId=3"`;
2. start the app **without** a server: it comes up and says it is offline;
3. start `SpectracsServer.exe` by hand, then the app; data dirs appear in `%USERPROFILE%\spectracsPy\` and
   `…\spectracsPy-server\` — **not** named after the zip folder;
4. login `masterUserExakta` (bench) and `elpUser` (end user) — ⚠ elpUser's sensor is the real ELP ⇒ the lamp
   service and the USB poll start (§4.2, U20); presence reads "absent", the log holds no repeating tracebacks;
5. **spectrometer-setup screen** opens without a crash (R3);
6. virtual spectrometer (fileset copied into the VM in V0.6) → one full plugin run → Rv shown;
7. one **PDF export** — opens in a PDF viewer; LIMS publish only if the server config dir from V0.6 is set;
8. `spectracs.log` holds the run's `print()` output;
9. licence gate: no `Qt6Charts*.dll` / `Qt6DataVisualization*.dll` / `Qt6WebEngine*.dll` in either folder.

### 8.2 W1
§8.1 steps 3–8 with the real ELP instead of the virtual device, plus: calibration authored once; CAPTURE-SETTINGS
shows YUY2, the backend, WB frozen; the **lamp switches on in ACQUISITION and off when the window is closed**
(§7.3). The null run (§6.5) is ⏸ postponed.

---

---

## 9 — Open questions

- ~~**O1 — production topology.**~~ ✅ **Answered 2026-10-07:** the server normally runs on the internet; locally
  it is started by hand on demand ⇒ independent artefact, no launcher (D6).
- **O2 — which camera is "production" on Windows?** ◐ **Partly answered 2026-10-07:** W1 is developed against the
  **ELP**; the production camera is not decided yet (ELP, Microdia or ToupTek, §6.6). ⇒ W1's code stays
  VID/PID-generic, and the §6.5 gate is re-run for whichever camera becomes production.
- ⏸ **O3 — the null-run pre-registration — POSTPONED, to be discussed later** (§6.5 table P1–P5): oil, fills per OS, noise and offset criteria, what a fail means. Set by Edwin before the run.
- ~~**O4 — the VM's hypervisor.**~~ ✅ **Answered 2026-10-07: VMware (Player/Workstation)**, with Edwin's
  existing **Windows 10** image. ⚠ Windows 10 left support in Oct 2025 and Smart App Control exists only on 11
  ⇒ fine for development; the final real-PC sign-off (§6.5, §8.2) should be on **Windows 11**.

## 10 — Non-goals

Cross-compiling on Linux (D1) · a single-file exe (D3) · a launcher that starts the server (D6) · macOS · Windows on
ARM · changing the Linux capture path beyond §6.3 step 4 (and that only if bit-identical) · the ToupTek camera
(§6.6) · auto-update.

## 11 — Rubber-duck pass (2026-10-07, against the as-is code and the installed packages)

Fourteen findings; every one is folded into the phase table (§12). Where a finding **overrides** an earlier
section, the earlier section is wrong and this one wins.

| # | sev | overrides | finding | fix |
|---|---|---|---|---|
| R1 | ⛔ | §5.1, D4 — ⚠ fix superseded by **S1** | app verify cannot work: the shim always chdirs to the real dir (no `--fresh`, no `SPECTRACS_CWD_ROOT` like `AppRun.app:13`); a windowed exe started over ssh returns at once; its stdout goes to the log (D5) | the hook honours `--fresh` (stripped from argv) + `SPECTRACS_CWD_ROOT`; verify = `Start-Process -Wait`, `QT_QPA_PLATFORM=offscreen`, result read from the log |
| R2 | ⛔ | §5.1 — verify dir superseded by **S5** | not "1:1" with Linux: `--check-lamp-imports` (zeroconf Cython, `buildAppImages.sh:203-206`) missing; "require calibration" fails on a fresh VM server DB (Linux only prints MISSING); pair proof needs the VM venv + `PYTHONPATH` to the worktrees; the 8g.3 "port 8091 already taken" refusal missing | add all four; calibration = **info only** |
| R3 | ⛔ | §4.2, B6 | **W0 crash path:** `SpectrometerSetupViewModule.py:84` calls `isSensorConnected` for every spectrometer (virtual too); `ApplicationSpectrometerUtil.py:9-15` catches only `ImportError` ⇒ pyusb is bundled, `usb.core.find` raises `NoBackendError` on Windows | **W0 code change:** catch `Exception` there ⇒ "absent"; spectrometer-setup screen joins §8.1 |
| R4 | ⚠ | D4 | `runpy` of a string is invisible to PyInstaller ⇒ `spectracsMain`'s import graph would be missed; `spectracsMain.py` is module-level, no `__main__` guard | the shim becomes a **runtime hook** (`runtime_hooks=[RECIPE/…]`): runs before the entry, `spectracsMain.py` stays the analysed entry, SRC/RECIPE split kept; same mechanism for the server |
| R5 | ⚠ | §6.4 | exposure surface larger than listed: `CapturePanel.py:76-83` (`MIN=1`, `FALLBACK=150`, `MAX_FALLBACK=5000`; `:608` rejects `high<=1` ⇒ a −13…−1 range is discarded), `DevCaptureViewModule.py:40`, `…WavelengthCalibrationViewModule.py:162` (`requestAutoExpose(1, 500)`), `CameraWarmupService.py:42-89`, `CaptureBackend.py:127-128` (legacy `win32` default −3); ⭐ **`SpectralWorkflow.exposureApplied` is persisted** (`-model …/SpectralWorkflow.py:73,148`) ⇒ log₂ values would mix silently into the archive | range from the backend at **every** site; the workflow record gets a **`captureBackend` / exposure-unit tag** |
| R6 | ⚠ | §6.4, §6.7 | the backend sets more V4L2-semantics controls than exposure: `AUTO_EXPOSURE=1` = manual only on V4L2 (on DSHOW plausibly the opposite); the measurement path freezes WB 6500 K / `AUTO_WB=0` / `BACKLIGHT=0` / `GAIN=0` (`:126-147`, the §14.8 reference-tilt fix) — if MSMF ignores `WB_TEMPERATURE`, auto-WB keeps running unreported; `BUFFERSIZE` likely ignored by MSMF | spike table gains all of these with read-back; a W1 step "freeze WB/gain per backend"; the null run is invalid unless WB is proven frozen |
| R7 | ⚠ | B2, §4.2, D5 | `import fcntl` before the guard in **two** places (`:193` `__queryControl`, `:243` `__exposureModeName`); it does **not** crash (callers catch `Exception`, `CapturePanel.py:598-603, 704-707`) but the **whole** CAPTURE-SETTINGS line reads "unavailable" on Windows | move `fcntl` behind the guard + per-field catching (W1, step with the backend) |
| R8 | ⚠ | B1, §6.3 | resolver `None` ⇒ calibration keeps VideoThread's default `_deviceId = 0` (`…WavelengthCalibrationViewModule.py:158-160`, `VideoThread.py:59`) ⇒ on Windows it would open **any** camera at index 0 (a laptop webcam) | same rule as §6.3: **no silent fallback** — a non-virtual sensor that does not resolve refuses to open |
| R9 | ⚠ | §2.1 | licence gate OK, but `qt_rel_dir` is `PySide6` on Windows, not `PySide6/Qt` (`PyInstaller/utils/hooks/qt/__init__.py:160-163`) ⇒ `DROP_DATA_DIRS` (`spectracsAppImage.spec:117`) never matches | add `PySide6/qml`, `PySide6/resources` variants |
| R10 | ⚠ | §5 | Windows OpenSSH has **no rsync**; sshd default shell = cmd.exe (`set X=… &&` keeps a trailing space); `Compress-Archive` slow + backslash entry names; manifest step ordered after the zip; Defender slows PyInstaller and quarantines `runw.exe`; `pyinstaller-hooks-contrib` unpinned | `tar -c \| ssh tar -x` (bsdtar ships with Win10), excluding the worktrees' `.git` files; DefaultShell = PowerShell; **zip on Linux** after copying `dist` back (manifest first); Defender exclusion for `C:\spectracs-build`; pin hooks-contrib to the Linux version |
| R11 | ⚠ | §8.1 | steps 4–5 assume a virtual fileset and LIMS — neither ships (Linux D7, D9: SENAITE/PayPal off without `SPECTRACS_SERVER_CONFIG_DIR`) | the VM gets a virtual fileset copied in by hand and a server config dir; both named in V0 |
| R12 | · | D5 | the log path must be computed by the hook (appdata resolves at import, `DbBase.py:18`) | ✅ decided: log in the **cwd folder**, like Linux (`%USERPROFILE%\Spectracs\spectracsPy\spectracs.log`); `--fresh` via a second shortcut; 8g.3 port check + manifest banner move into the server hook |
| R13 | · | §2 | survey gaps: `LampSetupHint.scanWifi` uses `nmcli` ⇒ `[]` on Windows (harmless, a hint only); `MSMF_ENABLE_HW_TRANSFORMS` (env var, own conversion path) | spike pins `MSMF_ENABLE_HW_TRANSFORMS=0`; nmcli = known degradation |
| R14 | · | — | inconsistencies: B2 pointed at a §8.1 item that did not exist; §7.6 still offered KVM after O4; exe names need `name=` in EXE **and** COLLECT; the old `spectracsAppPyInstaller.spec` exists too | fixed below / in §12; both old specs deleted in W0 |

**Confirmed by the duck:** B1, B3, B7 (appdata: dot only on Linux, name = cwd basename at construction, home =
`Path.home()` ⇒ D4's dirs are right); the licence gate; §7.3 lamp hooks (`SIGHUP` guarded by `hasattr`,
`closeEvent` + `aboutToQuit` cover the window close); **no** `multiprocessing` / `QProcess` / `subprocess` in
`sciens/` beyond nmcli ⇒ no `freeze_support` needed; resources + Alembic found via `__file__`; no Linux-only path
literals; `AutoExposureLogicModule` copes with a non-positive range; OpenCV's V4L2 YUYV path is `cvtColor(…,
COLOR_YUV2BGR_YUYV)` (= `_YUY2`, medium-high confidence); grab + two retrieves with toggled `CONVERT_RGB` plausible
but unverified ⇒ §6.3's fallback stands.

⇒ **Two code changes move into W0** (R3; and R4's hook is recipe-side, not `sciens/`). W0 is therefore **not**
zero-code like the Linux freeze — one guarded `except` in `ApplicationSpectrometerUtil`.

---

## 11b — Second rubber-duck pass (2026-10-07, aimed at THE PLAN and at the first pass's fixes)

The stale paragraphs it listed (D2, D4, D5, D7, D8, §2.1, B6, §4.2, §5, §5.1, §6.4, §6.5, §6.7, §7.3, §8.1, §8.2)
were **rewritten in place**, not overridden — the sections above are current.

| # | sev | finding | resolution |
|---|---|---|---|
| S1 | ⛔ | R1's `Start-Process -Wait` never returns: `--fresh` opens the GUI; a windowed exe shows a modal traceback MessageBox on error ⇒ headless hang | **D9 `--check-db`** (exits after DB init, both OSes); ~~`disable_windowed_traceback=True` + hook excepthook~~ ⚠ **corrected by U1**: that flag keeps the dialog ⇒ the flag catches `BaseException` itself and `os._exit`s (D5); `Wait-Process -Timeout` as the safety net (§5.1.5) |
| S2 | ⛔ | no tag step: builds run from worktrees at a tag, and `presentation-2026-09-12` has neither W0.1 nor `--check-lamp-imports`; W0.4/W0.5 had no way to get sources into the VM | `--tag` accepts **any git ref**; worktrees keyed by **SHA** (`src-<sha>`), so a moved ref can never reuse a stale folder; dev builds from the committed `main`, **the release tag comes LAST** (Linux §8d: tags are retroactive); the manual copy is its own step (W0.4) |
| S3 | ⚠ | the lamp cannot be tested in W0 (no `LampService` for a virtual sensor) | lamp check → W1.6 / §8.2; W0 proves only `--check-lamp-imports` |
| S4 | ⚠ | Pyro5 `SOCK_REUSE=True` ⇒ on Windows a 2nd server binds 8091 silently; any argv flips the server entry to the stock CLI | two separate hooks; the server hook never touches argv, refuses a taken port, sets `SOCK_REUSE=False` (D4) |
| S5 | ⚠ | app spec has no RECIPE root; hooks share `__main__` globals; `SPECTRACS_CWD_ROOT` cannot reach a `-verify` data dir | RECIPE root in W0.3; hook body in a function + `del`; verify uses `--fresh` (D2, D4, §5.1) |
| S6 | ⚠ | R5 overstated: `exposureApplied` is report-JSON only (no migration); but `int()` truncation, diagnostics readers, and the signed plugin's `exposure = 90` | float + `exposureUnit` key; plugin contract stays V4L2, host converts; W1.4 touches -app, -model, -core docs (§6.4) |
| S7 | ⚠ | §12 dependencies wrong: W1.4/W1.5 need W1.2; W1.0 needs V0.2 + sources + the lamp by hand; a decision step after the spike was missing; W1.6 needs a local server and W1.4 | fixed in §12 (new step **W1.1 = Edwin's decision**) |
| S8 | ⚠ | `tar \| ssh` through PowerShell 5.1 may corrupt binary stdin; "`pip freeze` == Linux" cannot hold; no python.org 3.10.12 for Windows | file + scp + checksum; D8 reworded (3.10.11, `pip check`) |
| S9 | · | "same file list" is checkable only as a sorted `find` diff — and that needs a Linux build | W0.3 done-when |
| S10 | · | no producer for the `.ico` or `START_HERE.txt` | `tools/makeIcon.py` (D7, W0.3); `START_HERE.txt` in W0.6 |
| S11 | · | no CI; repos per step; the spike table goes into a public repo | unit tests in "done when"; repos column in §12; spike table scrubbed of device-instance paths / serials |
| S12 | · | UVC controls survive a VMware hand-over; the real-PC null run is not "free"; Unblock untestable on a local zip | §6.4b, §6.5, §8.1.1 |
| S13 | · | split W0/W1/W2 is right, but the spike is a production go/no-go | **spike moves to right after V0**; W2.1 may come before W1 |

**Confirmed by the second duck:** one guard (W0.1) closes the W0 crash path (the poll thread and status module
already catch `Exception`); the hook's chdir precedes appdata; Linux is unaffected when `runtime_hooks` is win32
only; `--check-lamp-imports` exits before Qt and DB; the server spec excludes `usb`; no migration for
`exposureApplied`.

---

## 11c — Third rubber-duck pass (2026-10-08, aimed at W0.1–W0.3 at code level)

Read-only, against the as-is code, the installed PyInstaller 5.10.1 / hooks-contrib / pyusb / Pyro5 / appdata, a
built Linux dist (`pyi-archive_viewer`) and the VM venv (`pip list` over ssh). The stale sections it touched (§2.1,
D4, D5, D7, D8, D9, §4.2, §5.1, §8.1, S1, §12) were **rewritten in place** — the sections above are current.
Edwin's calls, 2026-10-08: U3 public helper in -model · U4 fix the poll thread properly, don't mute the logger ·
U19 split requirements now in W0 · U20 accept elpUser's real sensor in W0, note it.

| # | sev | step | finding | resolution |
|---|---|---|---|---|
| U1 | ⚠ | D5, S1 | `disable_windowed_traceback=True` keeps the modal dialog, it only hides the traceback (`api.py:337-338`) ⇒ S1's "no modal" premise was wrong | headless flags catch `BaseException`, print, flush, `os._exit(code)`; `Wait-Process -Timeout` as safety net (D5) |
| U2 | ⚠ | W0.2 | `--check-lamp-imports` sits **after** the view-tree imports (`spectracsMain.py:4-12`, flag `:95`) ⇒ a missing frozen module raises before the check | `--check-db` right after `import os, sys`; the imports inside its `try` ⇒ also proves the import graph (D9) |
| U3 | ⚠ | W0.2 | "prints the Alembic head" ambiguous; on a fresh DB create_all + stamp (`DatabaseInitializer.py:38-40`) makes the DB rev trivially equal; `_config()` is private | print `dbRev` + `scriptHead` + DB path; exit 3 on mismatch; public helper in **-model** (D9) |
| U4 | ⚠ | W0.1 | pyusb retries all backends on **every** `find()` (`usb/backend/libusb1.py:957-971`); frozen, `pyi_rth_usb` makes it log `exc_info=True` tracebacks to stderr ⇒ ~3 tracebacks every 2 s from the poll thread with a real-sensor login. Source runs don't show it | `ConnectionPollThread.run`: `NoBackendError` ⇒ emit False once, return; `ApplicationSpectrometerUtil`: module-level "no backend" flag ⇒ stop calling `find` |
| U5 | · | W0.1 | a blanket `except Exception` would also swallow a malformed `vendorId`/`modelId` (`int('0x'+…)`, `ApplicationSpectrometerUtil.py:14-15`) | parse IDs outside the try; guard only `import usb.core` + `find`; one printed line |
| U6 | · | W0.1 | `sys.modules["usb.core"] = fake` does not take once `usb.core` is imported | `monkeypatch.setattr(usb.core, "find", …)` with a real `NoBackendError`; `sys.modules["usb"] = None` for the ImportError case |
| U7 | ⚠ | D5 | log file in cp1252 by default; 15 non-ASCII `print()`s ⇒ `UnicodeEncodeError` | UTF-8, `errors="backslashreplace"`; server: `stdout.reconfigure` (D4, D5) |
| U8 | · | D5 | custom excepthook adds nothing; Qt warnings bypass fd 2 on windowed Windows (UNVERIFIED) | drop it; `faulthandler.enable(log)`; Qt warnings = known degradation |
| U9 | ⚠ | D7 | nowhere said where the `.ico` lives; build must not write into a repo | `.ico` in the build target; spec reads `SPECTRACS_ICON_ICO` (D7) |
| U10 | ⛔ | W0.3 gate | no valid baseline: `~/spectracs-build/latest` is 2026-09-09, the app spec changed since (c73e6b1) | fresh baseline at f843948 + candidate after W0.3, same ref, named `--out w03-base` / `w03-new` (not pruned by `--keep`) |
| U11 | ⚠ | W0.3 gate | a `dist/` file list cannot see the leaks W0.3 could cause: runtime hooks live inside the exe's CArchive; the PNG icon sits in the AppDir | + diff of `pyi-archive_viewer -l -b` for both exes; + `cmp` of both PNGs (reproducible, verified) |
| U12 | · | W0.3 (R9) | R9 confirmed; only `PySide6/qml`, `PySide6/resources` missing (`translations` already listed); neither matches a Linux path | add both under win32; after the first Windows build check for stray tool `.exe`s |
| U13 | · | W0.3 | `spectracsAppImage.spec:51-53` comment says isSensorConnected does not guard `NoBackendError` — stale after W0.1 | comment only |
| U14 | ⚠ | W0.3 | no test seam named; a hook acts on load | `_plan` / `_apply`, frozen-gated, `del` (D4) |
| U15 | · | D4 | Pyro5 config built from `PYRO_*` at import, never reset; threaded server reads `SOCK_REUSE` | `os.environ["PYRO_SOCK_REUSE"]="false"` in the hook, no Pyro5 import (D4) |
| U16 | · | D4 | port check: `sys.exit(1)` from a console hook + refused-connect latency UNVERIFIED | `create_connection(…, timeout=1)`, only when `len(argv)==1` |
| U17 | · | D5 | heading "every frozen process logs to a file" vs server `console=True` | heading fixed; server hook redirects nothing |
| U18 | · | D5 | banner reads `RELEASE_MANIFEST.txt`, added only in build step 8 ⇒ missing in W0.4/W0.5 | tolerate missing; print `sys.executable` + argv |
| U19 | ⚠ | D8 | VM venv is `opencv-python-headless` (no MSMF, §6.6b) + `cv2_enumerate_cameras` spike leftover; D8 said "requirements.txt as-is" | platform-marker split in **W0.3b**; uninstall headless first in the VM; comtypes/pygrabber stay W1 |
| U20 | · | §4.2, §8.1 | "lamp not exercised in W0" but §8.1.4 logs in elpUser = real ELP ⇒ LampService + poll thread start | accepted, noted (§4.2, §8.1.4) |
| U21 | · | W0.2 | "runs on Linux from source" from the repo cwd migrates the real `~/.spectracsPy`; `--fresh` is AppRun-only, first-arg-only | subprocess test with `HOME=tmp_path` (D9) |
| U22 | ⚠ | D9, §12 | switching `buildAppImages.sh` to `--check-db` in W0.3 breaks the U10 rebuild of a ref without the flag | W0.3 touches only makeIcon in `buildAppImages.sh`; Linux switch once a tag contains W0.2 ⇒ W0.3 no longer needs W0.2 |
| U23 | · | D4 | wrong citation `build_main.py:611-619` | `:607-613` + `analysis.py:686-695` |
| U24 | · | — | Linux dist carries dev-venv extras (astropy, imageio) ⇒ cross-OS content diffs mean nothing; deepest path ~200 chars under a Downloads unzip, < MAX_PATH | note only; only Linux before/after is a gate |

**Confirmed by the third duck:** custom runtime hooks run before `pyi_rth_*` and the entry (seen in the real
CArchive); the bootstrap makes `sys.path` absolute and the 5.10.1 loader never touches `sys.stdout`; appdata
resolves at construction from the cwd (dot Linux-only, `Path.home()`), `DbBase.py:18` / `DbServerBase.py:11` after
the hook, no query at import; `alembic.ini` uses `%(here)s` ⇒ cwd-independent; `initAppDatabase()` runs without a
QApplication, dbRev = scriptHead = `63efd411276f` today; **W0.1 is the only uncaught USB path** (poll thread and
status module catch, resolver returns early off Linux, all `usb` imports lazy, nmcli guarded); the server spec
excludes `usb`; the licence gate's `\`→`/` normalisation works on Windows; Pillow 9.5.0 in both venvs writes a
16/32/48/256 `.ico`; the heredoc's PNG is byte-reproducible.

### 11c.1 Change list for W0.1–W0.3

**W0.1 — `spectracsPy`**
- `sciens/spectracs/logic/model/util/spectrometerSensor/ApplicationSpectrometerUtil.py`: parse vid/pid first; try
  only `import usb.core` + `usb.core.find` (`except Exception` ⇒ False, one printed line); a module-level
  "no backend" flag on `NoBackendError` ⇒ later calls return False without touching pyusb (U4, U5).
- `sciens/spectracs/logic/connection/ConnectionPollThread.py:37-41`: `usb.core.NoBackendError` ⇒ emit False once,
  return; other exceptions as today (U4).
- `tests/test_application_spectrometer_util.py`: `NoBackendError`, generic error, `sys.modules["usb"]=None`, found,
  not found (U6); transient `SpectrometerSensor` vendorId `0c99`, no DB. + a poll-thread `run()` test.

**W0.2 — `spectracsPy` + `-model`**
- `-model`: public helper returning the app script tree's head (wraps `_config("app")` +
  `ScriptDirectory.get_current_head()`), next to `initAppDatabase`.
- `spectracsMain.py` after `:2`: the `--check-db` block as in D9 (U1, U2, U3).
- `tests/test_check_db_flag.py`: subprocess, `HOME=tmp_path`, cwd `tmp_path/spectracsPy-demo`,
  `QT_QPA_PLATFORM=offscreen`; rc 0, head == `ScriptDirectory`'s, DB under `tmp_path/.spectracsPy-demo` (U21).

**W0.3 — `spectracsPy` tools/ + specs**
- `tools/makeIcon.py` (D7, verbatim); `buildAppImages.sh:74-99` calls it — nothing else changes there (U22).
- `tools/rthook_win_app.py`, `tools/rthook_win_server.py` (D4, D5; `_plan`/`_apply`).
- `spectracsAppImage.spec`: `RECIPE = os.path.abspath(SPECPATH)`, `WIN = sys.platform == "win32"`;
  `runtime_hooks` win32 only; `DROP_DATA_DIRS += ("PySide6/qml", "PySide6/resources")` win32 only;
  `EXE`/`COLLECT` `name="Spectracs"` on win32 (else unchanged), `console=not WIN`,
  `disable_windowed_traceback=WIN`, `icon` only when win32 and `SPECTRACS_ICON_ICO` set; comment fix (U13).
- `spectracsServerAppImage.spec`: same pattern, `name="SpectracsServer"`, `console=True`, server hook + icon.
- `tests/test_rthooks_win.py`: `_plan` cases (`--fresh` anywhere, `SPECTRACS_CWD_ROOT`, server argv untouched);
  `_apply` into `tmp_path` (dir created, cwd restored after, UTF-8 log with "→", banner without manifest); server
  port check against a listener on an ephemeral port (port is a parameter).
- **W0.3b** `requirements.txt` platform split (D8, U19); VM: uninstall headless, install `opencv-python`.

### 11c.2 As built — W0.1–W0.3 (2026-10-08)

As §11c.1, with these differences:
- **Both** headless flags moved to the top of `spectracsMain.py` and share one `_runHeadlessCheck` (catch
  `BaseException` → traceback → flush → `os._exit`); `--check-lamp-imports` behaves as before on Linux.
- `-model` `DatabaseInitializer` gained three public helpers: `getAppScriptHead()`, `getAppDatabaseRevision()`,
  `getAppDatabasePath()`. Output: `check-db ok: app db 63efd411276f head 63efd411276f at …/.spectracsPy-demo/spectracsPy.db`.
- The hooks' `_plan` takes no `platform` argument: nothing in it differs by OS, the frozen gate is the switch and
  the spec wires the hooks on win32 only. The server hook leaves with `os._exit(1)` on a taken port (U16).
- `isSensorConnected` recognises `NoBackendError` by class name, so the module still needs no pyusb import.
- Two icon variables (D7): `SPECTRACS_ICON_ICO`, `SPECTRACS_ICON_ICO_SERVER`.

Tests: `tests/test_usb_guard.py` (6), `tests/test_check_db_flag.py` (2, incl. exit 1 + traceback when -model is
missing), `tests/test_rthooks_win.py` (9). `pytest tests/` **631 passed**.

**Gate (U10, U11), run 2026-10-08:** `w03-base` = recipe f843948, `w03-new` = the W0.3 tree, both
`--tag presentation-2026-09-12 --no-verify`. Sorted `find` of `dist/app/spectracsMain` (2059 entries) and
`dist/server/spectracsServer` (89): **diff empty**. `pyi-archive_viewer -l -b` of both exes (17 / 12 entries):
**diff empty**. `cmp` of `spectracs.png` and `spectracs-server.png`: **identical** (also identical to the
2026-09-09 build). ⇒ the Windows branches do not reach the Linux AppImages.

### 11c.3 W0.3b + W0.4 as run (2026-10-08)

- **W0.3b:** `requirements.txt` split by marker (D8); the Linux venv resolves with nothing to install. VM:
  `pip uninstall opencv-python-headless`, `pip install --no-deps opencv-python==4.7.0.72`, `pip check` clean;
  `cv2` 4.7.0 lists `MSMF` and `DSHOW`. (`cv2_enumerate_cameras` from the spike is still in the VM venv; nothing
  imports it.)
- **Sources:** `git archive HEAD` of the six code repos (no `.git`), spectracsPy `a006be1`, -core `7573029`,
  -model `3eab8a2`, -base `d9eada5`, -server `9c16122`, -plugins `59ced63`, plus both `.ico` from `makeIcon.py` →
  one 18 MB tar → `scp` → sha256 equal on both ends → `tar -xf` into `C:\spectracs-build\src-a006be1\`. Recipe =
  the same tree (SRC = RECIPE for the by-hand build).
- **Server build:** `SPECTRACS_SRC_ROOT` + `SPECTRACS_ICON_ICO_SERVER` set inside the remote PowerShell command,
  `pyinstaller spectracsServerAppImage.spec` → **36 s, rc 0**, `dist\server\SpectracsServer\` 34 entries,
  `SpectracsServer.exe` 5.4 MB. Only warnings: hidden imports `pysqlite2` / `MySQLdb` not found (SQLAlchemy's
  optional dialects — harmless).
- **Run** (`verifyServer.ps1`): port 8091 up within the 30 s wait; login **from source** in the VM venv →
  `MASTER_USER / ELP-0001 / calibration MISSING (info only)`; a second `SpectracsServer.exe` and a plain dummy
  listener on 8091 both make it **refuse with exit code 1** and the D4 message. Data landed in
  `%USERPROFILE%\spectracsPy-server\` (cwd `%USERPROFILE%\Spectracs\spectracsPy-server`) — not named after the
  build folder. ✅ D4 works frozen on Windows.
- **Learned for the script (W0.6/W0.7):**
  - PowerShell `Start-Process -PassThru` returns a null `ExitCode` unless `$p.Handle` is read right after the
    start ⇒ the script reads it.
  - Redirected stdout of the frozen server is block-buffered: the run log was **empty** after `Stop-Process
    -Force`. A real console window is line-buffered, so this hits only the script's logs ⇒ W0.7 checks the port
    and the login, not the server's stdout (or tries `PYTHONUNBUFFERED=1`, UNVERIFIED for the frozen bootloader).
  - The server dir also holds an empty-schema `spectracsPy.db` — same on Linux (`~/.spectracsPy-server/`), not a
    Windows issue.
  - The from-source login creates `%USERPROFILE%\spectracsPy-verify-client\` (appdata names it after the cwd) —
    throwaway, like the Linux verify's.

### 11c.4 W0.5 as run (2026-10-08)

- **App build:** same sources (`src-a006be1`), `SPECTRACS_ICON_ICO` set, `pyinstaller spectracsAppImage.spec` →
  **180 s, rc 0**; `dist\app\Spectracs\` 1255 files, **339 MB**; `Spectracs.exe` 18 MB. Warnings, all expected:
  `pyqtgraph.opengl` (no PyOpenGL — unused), Qt's `SetProcessDpiAwarenessContext … Zugriff verweigert` (the build's
  Qt probe in an ssh session), `api-ms-win-shcore-scaling-l1-1-1.dll` not found (a Windows API set the OS
  provides), pyusb "No backend available" during analysis.
- **Licence gate** (§8.1.9): no `Charts` / `DataVisualization` / `WebEngine` file. **U12:** `PySide6\qml`,
  `PySide6\resources`, `PySide6\translations` absent; the only `.exe` is `Spectracs.exe`.
- **`Spectracs.exe --fresh --check-db`** (`verifyApp.ps1`): **exit 0 in 3 s**, log in
  `%USERPROFILE%\Spectracs\spectracsPy-demo\spectracs.log`:
  `check-db ok: app db 63efd411276f head 63efd411276f at C:\Users\…\spectracsPy-demo/spectracsPy.db` — equal to
  -model `3eab8a2`'s head on Linux. The hook stripped `--fresh` (argv in the banner), the DB landed in
  `%USERPROFILE%\spectracsPy-demo\`. (The mixed `\`/`/` in the path is `DbBase`'s own join — SQLite does not care;
  cosmetic.)
- **`Spectracs.exe --check-lamp-imports`:** exit 0, `lamp imports ok` (zeroconf's Cython modules are bundled).
- **Extra, not in §5.1 — GUI smoke:** `QT_QPA_PLATFORM=offscreen Spectracs.exe --fresh` alive after 25 s, no
  traceback in the log; "no spectracs server reachable" as it should be with no server; **W0.1 fired once on real
  Windows** (`isSensorConnected: USB unavailable (NoBackendError …) - sensor absent`) and never again.
- VM scripts: `C:\spectracs-build\verifyServer.ps1`, `verifyApp.ps1`, `smokeGui.ps1` — the drafts of W0.7's
  self-verify.

### 11c.5 W0.6 as run (2026-10-08)

`tools/buildWindows.sh` (no arguments ⇒ both, `--tag main`) → **rc 0, 4 min 15 s** end to end:
ref resolved in all six repos (spectracsPy `bf5ac3f` …) → `upload.tar` 19 MB, sha256 equal in the VM → server
**29 s**, app **180 s**, licence gate ok → `dist.tar` back, sha256 equal → `Spectracs-main-bf5ac3f-win64.zip`
**135 MB** and `Spectracs-Server-main-bf5ac3f-win64.zip` **13 MB**, each with `RELEASE_MANIFEST.txt` (per-repo
SHAs, recipe SHA, toolchain read in the VM: Python 3.10.11 · PyInstaller 5.10.1 · opencv 4.7.0.72 · Windows 10
Home 10.0.19045) and `START_HERE.txt` (Unblock, local folder, data + log paths, `--fresh` shortcut, firewall,
the server's role) — both CRLF. VM build folder removed.
**Round trip:** the Linux-made app zip, `Expand-Archive`d in the VM into `Downloads\unzip test\` (a space),
runs `--fresh --check-db` → exit 0, `check-db ok … 63efd411276f`; the log banner now carries the manifest (U18's
other branch). Recipe read `+dirty` in that first run only because the script was not committed yet.

### 11c.6 W0.7 as built and run (2026-10-08)

**`tools/windows/verifyInVm.ps1`**, called by `buildWindows.sh` after the build and **before** the copy back (the
pair proof needs `src\` in the VM); a failure keeps the VM folder and zips nothing. One line per check, ends in
`VERIFY ok` or exit 1:

| # | check | pass when |
|---|---|---|
| 1 | `Spectracs.exe --fresh --check-db` | exit 0, `check-db ok` line, head == the archived -model's head (read on **Linux** from the staged tree, passed in), DB under `%USERPROFILE%\spectracsPy-demo` |
| 2 | `Spectracs.exe --fresh --check-lamp-imports` | exit 0, `lamp imports ok` — ⚠ with `--fresh` (unlike Linux), so the VM's real app dir stays untouched |
| + | GUI smoke, offscreen `--fresh` (beyond §5.1) | alive after 25 s, no `Traceback` in this run's log lines |
| 3 | dummy listener on 8091 → `SpectracsServer.exe` | exit 1 within 15 s |
| 4 | `SpectracsServer.exe` → 8091 within 30 s → login `masterUserExakta` from source | login ok; calibration info only |

Server checks skip (like Linux §8g.3) when 8091 is already taken. Timeouts 120 / 60 / 25 / 15 / 30 s; exit codes
via the process handle; the source client runs with `$ErrorActionPreference = "Continue"` (its stderr warnings
would abort PowerShell 5.1 under `Stop`).
**Negative test first**, against the W0.5 build via junctions: the right head → all ok; head `deadbeef0000` →
`FAIL check-db: bundled head 63efd411276f != -model head deadbeef0000`, `VERIFY FAILED (1)`, exit 1.
**Full run** `tools/buildWindows.sh` (main `e600f90`): server 30 s, app 218 s, licence gate ok, **all five checks
ok, `VERIFY ok`**, zips `Spectracs-main-e600f90-win64.zip` 135 MB + server 13 MB, ~5 min end to end.

### 11c.7 V0.6 as done (2026-10-08, Edwin chose "both")

- **Virtual filesets:** the six baked sets from `spectracs-references/pumpkin_oil/virtual_captures/`
  (`pumpkinoil_{perfect,over,under}_{v1,v2}`, each `calibration/reference/sample.png` + `set.json`, 6.5 MB) →
  `%USERPROFILE%\Spectracs\virtual_captures\` in the VM. §8.1.6 picks `pumpkinoil_perfect_v2`.
- **Server config:** a copy of `spectracsPy-server-config/.env` → `%USERPROFILE%\spectracsPy-server-config\.env`,
  user environment variable `SPECTRACS_SERVER_CONFIG_DIR` pointing there (the frozen server cannot walk up to a
  sibling folder, Linux D9). **One line differs** from the original: `LIMS_SENAITE_BASE_URL` uses the Linux box's
  bridged address `192.168.1.223:6090` instead of `localhost` (in the VM, localhost is the VM). Checked from source
  in the VM: `ServerConfig.configDir()` = that folder, 13 keys, the SENAITE URL as above. ⚠ SENAITE (Docker on the
  Linux box) must be **up** for §8.1.7's LIMS publish, and port 6090 reachable from the LAN.
- The verified zips `Spectracs-main-e600f90-win64.zip` + server zip were copied to the VM's `Downloads\` for W0.8.

---

## 12 — Implementation phases and order

Strictly top to bottom unless marked `∥` (may run in parallel). Every phase ends in a commit; `pytest tests/` green
before each commit (there is no CI). Repos: **Py** = spectracsPy, **-model**, **-core**, **-plugins**.

```
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
| step  | what                                                      | repo/where| needs       | done when                           |
+=======+===========================================================+===========+=============+=====================================+
|                         V0 — THE VM  (Edwin, once, by hand)                                                                   |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|✅V0.1 | OpenSSH server, key login, DefaultShell = PowerShell      | Win10 VM  | —           | `ssh spectracs-win` w/o password    |
|✅V0.2 | Python 3.10.11 + venv: requirements.txt, pyinstaller      | VM        | V0.1        | pins match, `pip check` clean (D8)  |
|       | 5.10.1, hooks-contrib = Linux's                           |           |             |                                     |
|✅V0.3 | Defender exclusion C:\spectracs-build                     | VM        | —           | exclusion listed                    |
|✅V0.4 | bridged network (Shelly mDNS)                             | VMware    | —           | plug answers from the VM            |
|✅V0.5 | ELP passthrough — live image in the Windows Camera app    | VMware    | —           | image visible                       |
|✅V0.6 | virtual fileset + server config dir copied in             | VM        | —           | files present                       |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|                         SPIKE — the production go/no-go, FIRST  (no app code)                                                 |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|✅W1.0 | probe diagnostics/windows_camera_probe.py: enumerate,     | Py diag.  | V0.2, V0.5, | ONE table in §6, scrubbed of        |
|       | MSMF vs DSHOW, HW_TRANSFORMS=0, YUY2 grant, CONVERT_RGB=0 | + VM      | lamp on by  | device paths/serials; committed     |
|       | buffer shape, exposure range/step/brightness sweep,       |           | hand        |                                     |
|       | AUTO_EXPOSURE meaning, WB/GAIN/BACKLIGHT read-back,       |           |             |                                     |
|       | BUFFERSIZE                                                |           |             |                                     |
| W1.0b | ✅ native controls spike (§6.6c): WB solved via (d),      | Py diag.  | W1.0        | ✅ done 2026-10-07                  |
|       | exposure confirmed whole log2 steps                       |           |             |                                     |
| W1.1  | ★ EDWIN ✅ DECIDED 2026-10-07: (d) native controls +      | —         | W1.0b       | ✅ written into §6.6c               |
|       | (b) whole exposure steps for now; fine-graining later     |           |             |                                     |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|                         W0 — PACKAGING  (virtual device; worth doing whatever W1.1 says)                                      |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|✅W0.1 | USB guard: isSensorConnected → "absent" on any USB    ∥   | Py        | —           | 5 util cases + poll-thread test     |
|       | error, IDs parsed outside; poll thread stops once on      |           |             | (U4–U6)                             |
|       | NoBackendError (R3, U4, U5)                               |           |             |                                     |
|✅W0.2 | --check-db right after `import os, sys`; prints dbRev +∥  | Py, -model| —           | subprocess test w/ HOME=tmp_path:   |
|       | scriptHead + path; exits 0/3/1 via os._exit; head helper  |           |             | rc 0, head == ScriptDirectory (U21) |
|       | public in -model (D9, U1-U3)                              |           |             |                                     |
|✅W0.3 | tools/makeIcon.py (verbatim + .ico); rthook_win_app/      | Py tools/,| — (U22)     | hooks unit-tested via _plan/_apply; |
|       | _server.py (_plan/_apply); spec win32 branches: RECIPE    | *.spec    |             | fresh Linux base (f843948) vs new,  |
|       | root, runtime_hooks, console, windowed_traceback,         |           |             | same ref: sorted `find` of both     |
|       | icon via SPECTRACS_ICON_ICO, name=, qml/resources drops   |           |             | dists, `pyi-archive_viewer -l -b`   |
|       | (D2-D7); buildAppImages.sh: makeIcon only                 |           |             | of both exes, `cmp` both PNGs —     |
|       |                                                           |           |             | all EMPTY (U10, U11)                |
|✅W0.3b| requirements.txt: opencv-python on win32, headless else   | Py, VM    | —           | Linux venv unchanged; VM: headless  |
|       | (D8, U19) → commit W0.1–W0.3b (Py + -model)               |           |             | out, opencv-python 4.7.0.72 in      |
|✅W0.4 | BY HAND: tar + scp sources/recipe to VM, set              | VM        | V0, W0.3b   | SpectracsServer.exe up; login from  |
|       | SPECTRACS_SRC_ROOT, build SERVER first (10 s, no Qt)      |           |             | source in the VM venv               |
|✅W0.5 | BY HAND: build APP; `--fresh --check-db`,                 | VM        | W0.4        | Alembic head == -model's head;      |
|       | `--check-lamp-imports`                                    |           |             | lamp imports ok                     |
|✅W0.6 | tools/buildWindows.sh (§5): ref→SHA archives, makeIcon,   | Py tools/ | W0.5        | one command → 2 zips + manifests    |
|       | tar/scp/checksum, remote build, gate, back, manifest +    |           |             |                                     |
|       | START_HERE.txt, zip on Linux                              |           |             |                                     |
|✅W0.7 | self-verify §5.1 (check-db, lamp imports, port-taken,     | Py tools/ | W0.6        | all green in the script output      |
|       | pair proof; timeouts as safety net) → commit              |           |             |                                     |
| W0.8  | click-through §8.1                                        | VM, Edwin | W0.7        | §8.1 ticked                         |
| W0.9  | delete both old PyInstaller specs → commit + push         | Py        | W0.8        | pushed                              |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|                         W1 — REAL CAMERA  (ELP; production camera still open, O2)                                             |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
| W1.2  | resolver win32 branch + presence light from the same      | Py        | W1.1        | unit test w/ fake enumerator; ELP   |
|       | enumeration; unresolved ⇒ REFUSE, never index 0  (R8)     |           |             | found, webcam ignored, in the VM    |
| W1.3  | backend pin MSMF, YUY2 strict (no win32 fallback),        | Py        | W1.2        | unit test: own convert == cv2 on a  |
|       | CONVERT_RGB=0 + own cvtColor, fcntl behind guard (R7)     |           |             | synthetic YUYV buffer; log: YUY2    |
| W1.4  | LINUX bit-identical: one grab, two retrieves (§6.3.4)     | Linux rig | W1.3        | diff == 0 ⇒ Linux adopts the path;  |
|       |                                                           |           |             | ≠ 0 ⇒ Windows-only                  |
| W1.5  | exposure: range from backend at ALL sites (§6.4 table),   | Py, -model| W1.3, W1.4, | converter unit-tested; float +      |
|       | per-backend converter, float, `exposureUnit` in report    | -core docs| W1.1        | exposureUnit in the report JSON     |
|       | JSON; plugin contract = V4L2 units (host converts)        |           |             |                                     |
| W1.6  | set + read back WB/gain/backlight/AE-mode per backend,    | Py        | W1.3        | CAPTURE-SETTINGS proves frozen      |
|       | every open (§6.4b)  → commit W1.2–W1.6                    |           |             |                                     |
| W1.7  | click-through §8.2 in the VM: local server, author        | VM, Edwin | W1.5, W1.6, | Rv on screen, PDF; lamp on/off      |
|       | calibration once, one measurement, lamp on/off            |           | W0.7        |                                     |
| W1.8  | ⏸ null run Windows vs Linux — POSTPONED (O3, §6.5)        | VM, Win11 | O3          | —                                   |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
|                         W2 — INSTALLER + SIGNING  (before the first customer; W2.1 may start after W0)                        |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
| W2.1  | Inno Setup, per-user (%LOCALAPPDATA%\Programs)       ∥    | Py tools/ | W0.7        | Setup.exe installs w/o admin        |
| W2.2  | signing: OV certificate vs Microsoft cloud signing        | Edwin     | —           | decided                             |
| W2.3  | sign Setup.exe (+ every binary if Smart App Control)      | build     | W2.1, W2.2  | no SmartScreen box on download      |
| W2.4  | real Windows 11 PC: install + §8.1 + §8.2                 | Win11 PC  | W2.3, W1.7  | ticked (same session as W1.8 later) |
| REL   | release: tag all 7 repos LAST at the built SHAs           | all       | W2.4        | tag == SHAs in RELEASE_MANIFEST     |
+-------+-----------------------------------------------------------+-----------+-------------+-------------------------------------+
```

**Order rationale.**
- **Spike first (W1.0 → W1.1).** If Windows only offers whole doubling steps of exposure, that decides whether
  Windows can measure in production at all — find out before anything else is built. W0 is worth doing either
  way (demos, archive, PDF, LIMS on Windows).
- **W0.1 ∥ W0.2 ∥ W0.3:** independent (U22 removed W0.3's dependency on W0.2), all testable on Linux without the VM.
- **W0.3 proves Linux is untouched** with empty diffs of the file lists, the exes' archive listings and the icons,
  against a fresh baseline built from the same ref (U10, U11) — the Windows branches must not leak.
- **By hand before the script (W0.4/W0.5 → W0.6):** the script automates what worked once; server before app (10 s,
  no Qt) as on Linux.
- **W1.4 before W1.5:** settle *one* conversion path before touching the exposure plumbing that feeds it.
- **Tag last (REL):** tags are retroactive (Linux §8d); dev builds run from the committed `main` by SHA.
