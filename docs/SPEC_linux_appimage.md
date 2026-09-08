# SPEC — Code freeze + standalone Linux AppImage (presentation build)

Status: **DESIGN — nothing built** (spec-first; implement on explicit request only).
Source: Edwin, 2026-09-08 — *"as this weekend I have a presentation of the project I would like to freeze the
code base as-is"* + *"build a standalone linux AppImage executable of the spectracsPy app"*.
**All four open questions answered by Edwin the same day (§11); rubber-duck pass §8, same day.**

Theme: **the demo must be a noun, not a procedure.** Today "running Spectracs" is `runApp.sh` +
`runServer.sh` + a five-repo `PYTHONPATH` + a 1.4 GB venv. The deliverable is *one file you double-click*,
built from *one identifiable point in history*.

| | deliverable | what it is |
|---|---|---|
| **F** | **the freeze** | one tag across all seven repos + a manifest + **a snapshot of the two live DBs** (§4) |
| **A** | **the AppImage** | a single x86-64 file that runs app **and** server, no venv, no PYTHONPATH (§5–§6) |

> ⭐⭐ **The governing constraint is D3: zero changes to application code.** Everything below is achievable
> without touching a line under `sciens/` — the freeze stays a real freeze. Every temptation to change code was
> resolved into a *packaging* trick instead; the tempting ones are recorded in §7 so the reasoning survives.

> ⛔ **"Standalone" means no venv, no PYTHONPATH, no repo checkout. It does NOT mean self-contained.**
> Edwin's answer O3 (keep the real DBs) makes the demo depend on **machine-local state that is in no repo**:
> the ELP calibration authored once into `~/.spectracsPy-server/spectracsPyServer.db` and the 50 MB run
> archive in `~/.spectracsPy/spectracsPy.db`. That is a deliberate, good trade — real history demos better
> than a virgin seed — but it is **why F6 exists**. Losing those two files loses the demo, and no tag brings
> them back.

---

## 1 — Scope

**In scope:** a Linux x86-64 AppImage of the desktop app, server bundled, that boots to the real login screen,
runs the **real ELP camera** (O4), and exports the M2 PDF. Target machine: **this development machine**
(Linux Mint 21.1, glibc 2.35) — O1.

**Out of scope (§10):** Windows/macOS, the Android APKs, SENAITE/PayPal live calls, plugin *publishing*,
auto-update, code signing, and any behaviour change to the app.

---

## 2 — What the app actually needs at runtime (the survey this spec rests on)

Every row was read out of the code, not assumed.

| # | need | where | consequence |
|---|---|---|---|
| 2.1 | **A server.** Login is server-side; the client returns `{"ok": False, … "server unavailable"}` when nothing answers | `SpectracsPyServerClient.py:74-82` | the AppImage must carry a server → **D1** |
| 2.2 | The client's **first** connect attempt is the fixed loopback URI `PYRO:sciens.spectracs.spectracsPyServer@127.0.0.1:8091`, *before* any nameserver | `SpectracsPyServerClient.py:36-42`, `SpectracsServerEndpoint.localUri()` | a bundled server there needs **no code change and no nameserver** |
| 2.3 | A server that serves exactly that: `SpectracsPyServer.serveLocalForever()` — plain daemon, fixed object id, blocking | `SpectracsPyServer.py:51-62` | reuse verbatim as the AppImage's server entry |
| 2.4 | **Two SQLite DBs**: `spectracsPy.db` (app) and `spectracsPyServer.db` (server), both under `get_app_data_dir()` | `DbBase.py:20`, `DbServerBase.py:11` | see 2.5 |
| 2.5 | On desktop that dir is **`~/.<basename of the current working directory>`** — `appdata.AppDataPaths.__init__`: `name = os.path.split(os.getcwd())[1]`. That, and nothing else, is why `~/.spectracsPy` and `~/.spectracsPy-server` are two folders | `AppDataPathUtil.get_app_data_dir()` | **the data dir is selectable from AppRun with a `cd`** → **D2** |
| 2.6 | ⛔ `ANDROID_PRIVATE` selects the same dir — **but setting it flips `is_android()`** (Android layout, back-button filter, capture backend) | `PlatformUtil.is_android():8-13` | **never set `ANDROID_PRIVATE`** in AppRun |
| 2.7 | Both processes run **Alembic at boot**; `DatabaseInitializer` resolves `<-model root>/alembic/{app,server}/alembic.ini`, four levels up from `__file__`; the ini says `script_location = %(here)s` | `DatabaseInitializer.py:26-31` | **`alembic/` must be bundled at the frozen-bundle root** as data (ini + `env.py` + `script.py.mako` + `versions/*.py`) |
| 2.8 | The server **seeds** roles, dev users, the pumpkin binding, the `TEST-0001` virtual instrument and the `ELP-0001` real instrument on every boot, **idempotently on the serial** | `UserSeedLogicModule.py:46-52,139-141` | a virgin machine gets working logins free — **and the seed will not overwrite the authored ELP calibration** |
| 2.9 | Plugins resolve from a **codeRef string** via `importlib.import_module` | `PluginRegistry.py:101` | PyInstaller cannot see them → **`hiddenimports`** |
| 2.10 | Three **file-relative resources**: `resource/logo.png` (PDF header), `resource/expectedDetection.png`, `testSpectra/cfl_philips_calibration.png` | `WorkflowReportBuilder.py:167,176-183`; `…WavelengthCalibrationViewModule.py:95-107`; `PlaygroundCalibrationLogicModule.py:38-41` | all three resolve if `resource/` and `testSpectra/` sit at the **bundle root** (path arithmetic checked; §8.3 confirms) |
| 2.11 | The **capture gate is the sysfs resolver**, not USB: buttons enable on `resolvedIndex is not None`, resolved by globbing `/sys/class/video4linux/*` for the VID/PID — **pure stdlib, no external tool** | `CapturePanel.py:442-456`, `SensorCaptureIndexResolver.py:36-66` | ⭐ capture works even if the USB backend is broken; nothing to bundle for it |
| 2.12 | **pyusb** drives only the *presence indicator* (`isSensorConnected`, `ConnectionPollThread`), via `libusb-1.0.so.0` loaded through **ctypes** | `ApplicationSpectrometerUtil.py:9-17`, `ConnectionPollThread.py:29-41` | PyInstaller does not follow ctypes loads → **§8.2**; host has the lib, so the demo is safe here |
| 2.13 | `ServerConfig` walks up for a sibling **`spectracsPy-server-config/`** (SENAITE + PayPal secrets) | `ServerConfig.py:39-50` | not found inside an AppImage → **D9** |
| 2.14 | The signing key defaults to `../spectracs-keys/signing.seed` | `PluginSigner.py:6,16` | plugin **publishing** unavailable; **loading** unaffected (vendored pure-Python Ed25519 in `-core`) |
| 2.15 | Qt modules actually imported anywhere in the five repos: **QtWidgets, QtCore, QtGui, QtSvg, QtNetwork** — and nothing else | grep, all repos | a large `excludes` list is safe → **D6** |
| 2.16 | The end-user wizard on the **real camera** belongs to **`elpUser`** — `ELP-0001` → EXAKTA device + **pumpkin plugin**. `pumpkinTestUser` is bound to `TEST-0001`, the **virtual** device | `UserSeedLogicModule.py:112-141` | ⭐ demo path, given O2/O4: **`elpUser`** for the wizard, **`masterUserExakta`** for the bench |
| 2.17 | ⚠ There are **two `spectracsPyServer.db` files** on this machine: `~/.spectracsPy-server/` (274 KB, current) and `~/.spectracsPy/` (176 KB, **stale, Jul 18**) — both created by the cwd rule (2.5) | filesystem, checked 2026-09-08 | the AppImage must land on the **first**; D2 does, but this is the landmine that makes D2 worth stating |

---

## 3 — Decisions

### D1 — ⛔ **REVERSED 2026-09-09: the server is NOT part of the AppImage**

Edwin: *"the server part should not be part of the appImage at all"* — and: *"I just want an AppImage file that
acts as `runApp.sh` does now."* That is the decision; this section records what it changes.

**The AppImage is the app, and only the app.** You start the server the way you do today, from the dev
checkout. The AppImage is `runApp.sh` in one file — no more, and deliberately no less.

**What it simplifies** (all of it welcome three days out):

* ⭐ **no entry shim** — the PyInstaller entry is `spectracsMain.py` itself, so the release adds **one** new
  file (the `.spec`) instead of two;
* ⭐ **`AppRun` collapses to ~12 lines** — no child process, no port probe, no `trap`, and **both bugs §8b.1
  found simply cease to exist** (there is nothing to orphan);
* the server implementation never enters the bundle: nothing in the app imports `SpectracsPyServer`, so
  PyInstaller will not pull it in. **The decision enforces itself.**

**What it costs, stated once:** the AppImage cannot log in on its own. At the venue you will still open a
terminal and start a server before double-clicking. That is the same dependency `runApp.sh` has today — parity,
not a regression — but it does mean the file is not useful to someone who has no checkout (N7).

⚠ **What stays on the path anyway:** `spectracsPy-server` remains in `pathex`, because `SpectracsPyServerClient`
imports `SpectracsServerEndpoint` **and** `SqlAlchemySerializer` from it (lines 8–9) — the client↔server
*contract* lives in that repo. Only the `@expose` implementation is left out, and that happens by itself.

⚠⚠ **The new risk this creates — the venue network (§7a).** `runServer.sh --local` binds the **LAN IP**,
resolved by `NetworkUtil.getLocalIpAddress()`, which scans for a `wlp*` / `eth0*` interface and returns `None`
when there is none. On a laptop with the WLAN off — a plausible venue — that is unreliable, and the client then
spends 5 s timing out toward `sciens.at` on **every** call.

⭐ **Mitigation, no new file and no code change: start the server with `service_pyro.py`.** It already exists in
`spectracsPy-server` (the Android foreground-service entry) and calls `serveLocalForever()` — a plain daemon on
**`127.0.0.1:8091`**, which is the client's **first** probe (2.2). No interface, no nameserver, no network:

```bash
cd ~/development/spectracs/spectracsPy-server      # cwd = the data-dir selector (D2) -> ~/.spectracsPy-server
PYTHONPATH=".:../spectracsPy:../spectracsPy-model:../spectracsPy-base" \
  ../spectracsPy/venv/bin/python service_pyro.py
```

**Rejected (this was the previous D1): bundling the server and starting it from `AppRun`.** It needed no code
change and removed the venue-network risk — but it made the AppImage something other than "`runApp.sh` in one
file", which is what was asked for. Recorded because the reasoning still holds if the question is reopened:
`serveLocalForever()` on loopback is what an embedded server would have used, and it is exactly what the
mitigation above runs by hand.

### D2 — Data directories are selected by `cd`, not by code — and they are **the real ones** (O3)

AppRun starts each process from a directory whose *basename* is the wanted data-dir name (2.5):

| process | AppRun `cd`s to | data dir | carries |
|---|---|---|---|
| app | `…/spectracsPy` | `~/.spectracsPy` | `spectracsPy.db` — **50 MB, the run archive** |
| server | `…/spectracsPy-server` | `~/.spectracsPy-server` | `spectracsPyServer.db` — **the authored ELP calibration** |

Exactly the two folders the dev checkout uses today. **Settled by O3: the AppImage opens on the real data.**

⭐ **The anchor directories are `~/Spectracs/spectracsPy` and `~/Spectracs/spectracsPy-server`** — visible, not
dotted. Only the *basename* feeds the data-dir rule, so the parent is free, and §8b.3 found a second job for it:
`QFileDialog.getSaveFileName(self, "Save report", "measurement_report.pdf", …)` passes a bare filename, so
**every save dialog defaults to the process cwd**. A hidden anchor would drop the demo's PDF into a dotted
folder; `~/Spectracs/spectracsPy` puts it somewhere a presenter can point at.

⭐ **`prepProtocol.txt` rides along for free.** The lab recipe stamped into every run resolves to
`get_app_data_dir()/prepProtocol.txt` (`PrepProtocolResolver.overridePath()`), i.e. `~/.spectracsPy/` — so the
AppImage stamps **the same recipe as the dev app**, automatically. ⚠ Which is also the sharp edge of `--fresh`:
a virgin data dir has no `prepProtocol.txt`, so runs silently fall back to the plugin's declared default — the
exact staleness that class was written to prevent (`SPEC_metric_research.md` §16.15). **Never demo a real
measurement under `--fresh`.**

`--fresh` remains as an escape hatch (basenames `spectracsPy-demo` / `spectracsPy-server-demo`) for a virgin
pair — rehearsing a customer's first launch, nothing more.

⛔ The `ANDROID_PRIVATE` route to the same effect is forbidden (2.6). ⚠ And note 2.17: the *wrong* cwd silently
picks up a stale server DB from July rather than failing.

### D3 — Zero changes to application code

The freeze is the point. No `sciens/` file is edited. New files are additions, all build-only: the PyInstaller
spec, an entry shim, `AppRun`, the `.desktop`, the icon, the manifest.

### D4 — PyInstaller **onedir**, entry = `spectracsMain.py`

* **onedir, not onefile.** AppImage already is a compressed single file mounting a squashfs; onefile inside it
  would extract ~450 MB to `/tmp` on **every** launch.
* **No entry shim** (D1 reversed): the entry is `spectracsMain.py` as-is. Verified — it ends in
  `sys.exit(app.exec())` at module level and parses its own `sys.argv`, so `--phone`, `--phone=` and
  `--phone-zoom=` survive into the frozen build untouched.

### D5 — Drop the splash screen

PyInstaller's `Splash` is implemented in **Tcl/Tk** and bundles the build host's `libtcl`/`libtk` — a
dependency and a failure mode for two seconds of cosmetics. Verified safe: `spectracsMain.py`'s `pyi_splash`
call already sits in a bare `try/except`, so a build without splash is a no-op there. The two existing dev
specs are left untouched; this is a **third** spec file (§6).

### D6 — Aggressive excludes

* **Qt:** keep `QtCore/QtGui/QtWidgets/QtSvg/QtNetwork` (+ what `pyqtgraph` pulls); drop Qt3D, QtWebEngine,
  QtQuick/QML, QtMultimedia, QtCharts, QtDesigner, QtPdf, QtBluetooth, translations, docs. PySide6 unpacked is
  **526 MB** and the used set is a small fraction.
* **`luxpy` (77 MB) + `pandas` (49 MB):** `luxpy` is a *lazy* import with a documented plain-Gaussian fallback
  (`SpectrumSynthesisUtil`, the 390–410 nm UV-A LED only) and it drags pandas. ⚠ §8.7 verifies the fallback.
* **`colormath`:** dead by `SPEC_project_structure.md` ("Dead chain").
* `tkinter`, `IPython`, `pytest`, `sphinx`, `notebook`.

Size estimate, **to be confirmed at first build**: ~400–480 MB AppDir → **~150–220 MB AppImage** (zstd).
Arithmetic on installed package sizes, not a measurement.

### D7 — **No virtual fileset ships** (O2/O4)

Edwin: *"we will need no virtual fileset as we are running the real device at the presentation."* So nothing is
bundled for the virtual path and AppRun copies nothing out. Consequences, stated plainly:

* the **ELP must be plugged in** for any capture at all — there is no fallback demo path in the AppImage;
* the virtual path still *works* if a master points the picker at a folder by hand (the screen is untouched,
  master-only, in-memory as always) — it simply ships empty;
* ⚠ this makes §9's **A5 a release gate, not a nice-to-have**, and makes a spare USB cable part of the kit.

### D8 — Portability: **the target machine is this machine** (O1)

Built and run on Linux Mint 21.1 / glibc 2.35. ⭐ **Rubber-ducked and cleared** (§8.1): every dependency of the
bundled Qt `libqxcb.so` already resolves here — `libxcb-cursor`, `libxcb-xinerama`, `libxkbcommon-x11` are all
installed — and **`libfuse2` is installed**, so a type-2 AppImage will mount. The biggest generic AppImage risk
is therefore *not present in this build's target*.

Those libs are still copied into `usr/lib/` (cheap, ~1 MB) so the file survives being handed to someone else on
Ubuntu 22.04+. Older-than-22.04 reach would need a container build — **out of scope**.

### D9 — Features that degrade, deliberately

| feature | in the AppImage | why |
|---|---|---|
| SENAITE publishing, PayPal | **off** — no `spectracsPy-server-config/` (2.13) | secrets must not ship in a distributable file |
| plugin **publishing** (signing) | **off** — no `signing.seed` (2.14) | the private key must never ship |
| plugin **loading**, incl. signed rows | on | verification uses vendored public keys |

Both switch on for a local demo without a rebuild — `SPECTRACS_SERVER_CONFIG_DIR=…`, `SPECTRACS_SIGNING_KEY=…`
are already read from the environment. ⚠ §8.6 verifies they degrade *quietly* (a disabled control, not a
traceback).

### D10 — Version stamping without touching code

1. the **filename** `Spectracs-<tag>-x86_64.AppImage`;
2. `RELEASE_MANIFEST.txt` inside the AppDir (seven SHAs, build host, date, DB-snapshot id);
3. `AppRun` **prints it to stdout**, so a terminal launch says what it is.

---

## 4 — F: the freeze

Seven repos, all clean on 2026-09-08, **none ever tagged**. This introduces the first tag.

```
spectracsPy         9b6c984   2026-09-08
spectracsPy-core    7bdd26c   2026-08-27
spectracsPy-model   45b5c6a   2026-08-31
spectracsPy-base    d9eada5   2026-07-03
spectracsPy-server  9c16122   2026-07-18
spectracs-plugins   e238e13   2026-09-08
spectracs-docs      80099ab   2026-09-07
```

**F1 — tag, and tag LAST (8d.1).** One annotated tag, same name in all seven: `presentation-2026-09-<dd>`,
applied **retroactively** to the SHAs recorded above — `git tag -a <tag> <sha>` works on any commit at any
time. Tagging before the build would only guarantee the `…-2` re-cut, because P2 edits the `.spec` that lives
in `spectracsPy`. The annotation carries the other six SHAs, so any one tag reconstructs the set.

⭐ **The freeze's insurance is the SHA list in this section plus F6's DB snapshot — both of which exist the
moment this file is committed.** The tag is the label, not the protection.

**F1a — the tag carries the EVENT date, not the build date.** `presentation-2026-09-12` (settled 2026-09-09;
the presentation is Saturday). Three dates are in play and the name can only hold one: the **commits** are
2026-09-08/09, the **build** is 09-09…09-11, the **event** is 09-12. Reasons for the event date:

* a tag names a *state of the code*, and the commits' own dates are already in `git log` — a date in the name
  adds nothing as provenance, only as a human label, and the label worth searching for in a year is *why* this
  state was frozen;
* ⛔ a build date **goes stale the moment it is true**: any re-build (P3 spilling to Friday) or any `…-2`
  re-cut under F4 leaves the name lying. The event cannot drift;
* the build date **already has a home** — `RELEASE_<tag>.md` records host, glibc, Python, PyInstaller, PySide6
  *and* the build timestamp (F2). Putting it in the tag too is the same defect as §10 having a second work
  plan: one fact, two homes, guaranteed to disagree.

⚠ One consequence: the AppImage **filename** carries the tag, so a re-build yields a same-named file with
different content. That is what the manifest *inside* it is for (D10 puts the identity in three places; only
the filename is ambiguous under a re-build).

ℹ️ Not chosen: a semantic name (`v0.1.0-demo`). 881 commits in with no tag ever, inventing a version scheme is
a larger decision than this weekend should make — and this tag does not block doing it properly later.

**F2 — manifest.** `spectracs-docs/RELEASE_<tag>.md`: the seven SHAs, build host (distro, glibc, Python,
PyInstaller, PySide6), the exact build command, the degraded features (D9), and the DB-snapshot id (F6). This is
what makes the build re-creatable in a year.

**F3 — build from the tag, not the working tree.** Seven `git worktree` checkouts of the tag into a scratch
build root. Otherwise "the AppImage matches the tag" is a hope. Cost: seven commands and one `rm -rf`.

**F4 — the freeze is a *tag*, not a branch.** `main` stays open. A rehearsal defect is fixed on `main`,
cherry-picked, and the tag re-cut as `…-2`; the presentation binary is always one named point.

**F5 — push the tags.** A tag that exists only on the laptop freezes nothing.

**F6 — ⭐ snapshot the two live DBs.** *Raised by the duck, and it is the sharpest finding in this spec.* O3
makes the demo depend on `~/.spectracsPy/spectracsPy.db` (50 MB) and
`~/.spectracsPy-server/spectracsPyServer.db` (274 KB) — **neither is in any repo, and one of them holds the
only copy of the authored ELP calibration.** A `sqlite3 … ".backup"` of both (consistent even if the app is
running), timestamped, stored **outside git** beside the other un-versioned material.

⛔ **Not into a repo.** They are public (`spectracs-application-areas`) and the app DB *is* the 98-run corpus —
the moat. `spectracs-references/` (un-versioned) is the right home.

⚠ And note 2.17 while doing it: back up the **`~/.spectracsPy-server/`** copy, not the stale July one.

---

## 5 — A: the AppImage

### 5.1 AppDir layout

```
Spectracs.AppDir/
├── AppRun                              # bash; §5.2
├── spectracs.desktop                   # Categories=Science;Education;
├── spectracs.png                       # 256×256, from resource/logo.png
├── usr/
│   ├── bin/spectracs/                  # PyInstaller onedir output
│   │   ├── spectracsMain               # the app; entry = spectracsMain.py (D4)
│   │   ├── alembic/{app,server}/…      # 2.7 — data, at the bundle root
│   │   ├── resource/  testSpectra/     # 2.10 — data, at the bundle root
│   │   └── … Qt libs, PYZ, .so …
│   ├── lib/                            # xcb/xkb/libusb host libs (D8, §8.2)
│   └── share/{applications,icons/hicolor/256x256/apps}/
└── RELEASE_MANIFEST.txt                # D10
```

### 5.2 `AppRun` — the contract

With the server out (D1), this is the whole thing:

```bash
#!/bin/bash
HERE=$(dirname "$(readlink -f "$0")")
BIN="$HERE/usr/bin/spectracs"
export LD_LIBRARY_PATH="$HERE/usr/lib:$BIN${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cat "$HERE/RELEASE_MANIFEST.txt"                      # D10

case "$1" in --fresh) SUFFIX="-demo"; shift;; *) SUFFIX="";; esac
APP_CWD="${SPECTRACS_CWD_ROOT:-$HOME/Spectracs}/spectracsPy$SUFFIX"
mkdir -p "$APP_CWD"                                   # D2 — the cwd IS the data-dir selector
cd "$APP_CWD" || exit 1
exec "$BIN/spectracsMain" "$@"
```

⭐ `exec` is correct **here**: with no child process there is nothing to clean up, so §8b.1's two bugs (the lost
`EXIT` trap, the late `$!`) are not fixed so much as **deleted**. That is the clearest single benefit of D1's
reversal.

⚠ `#!/bin/bash` is still right, and `$HOME/Spectracs` is still the anchor (8b.3 — save dialogs default to cwd).

### 5.3 Packaging

`appimagetool` (a single static binary, downloaded once, not vendored) over the AppDir, zstd. Nothing else —
no `linuxdeploy`, no `appimage-builder`; PyInstaller already did the dependency collection. `appimagetool` is
**not currently installed** here (checked); `libfuse2`, which the produced file needs to mount, **is** (§8.1).

---

## 6 — The PyInstaller spec (`spectracsAppImage.spec`, NEW)

A third spec beside `spectracsAppPyInstaller.spec` and `…Windows.spec`, which stay untouched. Delta:

| field | value | why |
|---|---|---|
| entry | **`spectracsMain.py`** — no shim (D1 reversed) | D4 |
| `pathex` | `-core`, `-model`, `-base`, **`-server`**, `spectracs-plugins` | ⚠ the existing spec **omits `-server`**, still required, for `SpectracsServerEndpoint` + `SqlAlchemySerializer` (D1) — not for the server impl |
| `datas` | `alembic/{app,server}` → `alembic/`; `resource/`; `testSpectra/`; `collect_data_files('colour')` | 2.7, 2.10. ⚠ only the **app** tree is reachable now (`initAppDatabase`), but `server/` is ~50 KB — ship both rather than bet on having enumerated every path |
| `hiddenimports` | `collect_submodules('pyqtgraph')` + the two modules named by `PUMPKIN_OIL_CODE_REF` / `DEV_CODE_REF` + `…databaseEntity.AllEntities` | 2.9; `AllEntities` is imported for its metadata side effect |
| `binaries` | `libusb-1.0.so.0` | 2.12 / §8.2 |
| `excludes` | the D6 list | size |
| `Splash` | **removed** | D5 |
| `console` | **True** (kept) | the app prints capture diagnostics; a terminal launch should show them |

⛔ Do **not** strip `versions/*.py` from the alembic copy: alembic loads them **by path**, so they must be data,
not hidden imports. ⛔ Do exclude the `__pycache__` folders that already sit in `alembic/{app,server}/`.

---

## 7 — Changes considered and rejected

All of them would have been code changes (D3):

* a `SPECTRACS_DATA_DIR` override in `AppDataPathUtil` — **unnecessary**, the cwd already decides (D2);
* persisting the virtual-fileset folder in the DB — a real improvement and a real code change. **Deferred**;
  O2 removed the need for this build;
* a `--server` flag on `spectracsMain.py` — replaced by the build-only entry shim (D4);
* guarding `isSensorConnected` against `NoBackendError` — **§8.2**: a one-line fix, but the host has libusb, so
  it stays a *post-freeze* item;
* bundling `spectracsPy-server-config/.env` — refused on principle (D9).

---

### 7a — the one live risk D1's reversal creates: **the venue network**

`runServer.sh --local` binds the **LAN IP**, resolved by `NetworkUtil.getLocalIpAddress()`, which scans for a
`wlp*` / `eth0*` interface and returns `None` when there is none (read, not assumed). With no WLAN the server
start is unreliable — and the client then burns 5 s (`COMMTIMEOUT`) failing over toward `sciens.at` on **every**
call: login, user list, master-data sync.

⭐ **Mitigation costs nothing:** start the server with `service_pyro.py` (D1's command) — `serveLocalForever()`
on `127.0.0.1:8091`, the client's *first* probe. No interface, no nameserver, no network.
⚠ **Rehearse it with the WLAN switched off**, since N9 makes Saturday's demo run from the AppImage.

---

## 8 — Rubber-duck pass (2026-09-08, against the as-is code and this machine)

Eight things that would have bitten. Two changed the plan; one added F6.

**8.1 — The classic AppImage killer is already dead here.** ⭐ The first draft called Qt/xcb "the unpredictable
step". Checked instead of feared: `ldd` on the bundled `PySide6/Qt/plugins/platforms/libqxcb.so` reports **no
unresolved libraries** on this machine, and `libxcb-cursor0` — the one Qt 6.5 famously needs and no wheel
carries — **is installed**, as are `libxcb-xinerama` and `libxkbcommon-x11`. `libfuse2` is installed too, so a
type-2 AppImage mounts. ⇒ **§9's A4 drops from "1–3 h, unpredictable" to a 20-minute copy-and-check**, and D8
becomes a statement rather than a risk. (Kept in `usr/lib/` anyway, for the second machine.)

**8.2 — pyusb loads libusb through ctypes, which PyInstaller does not follow.** `usb.core.find` is reached from
`ApplicationSpectrometerUtil.isSensorConnected` and `ConnectionPollThread`. Both guard `ImportError` — but
`isSensorConnected` does **not** guard `NoBackendError`, which is what a missing `libusb-1.0.so.0` actually
raises. ⇒ add the lib to `binaries` and keep `LD_LIBRARY_PATH` pointing at it. **Severity: low here** — the
host has libusb system-wide and `ctypes.util.find_library('usb-1.0')` resolves (checked) — but it is exactly
the failure that would appear on the *second* machine, silently, as a crash on a settings screen.

**8.3 — ⭐ The capture path does not depend on 8.2 at all.** The buttons gate on `resolvedIndex is not None`
(`CapturePanel.py:442`), and that index comes from globbing `/sys/class/video4linux/*` for the VID/PID —
**stdlib only, no `v4l2-ctl`, no `lsusb`, no libusb**. So even a broken USB backend costs only the presence
indicator, never the measurement. The real-device demo is more robust than the first draft assumed.

**8.4 — ⭐ The demo user is `elpUser`, not `pumpkinTestUser`.** With the virtual fileset gone (D7), the seeded
`pumpkinTestUser` is useless: it is bound to `TEST-0001`, the **virtual** device. The real-camera end-user
wizard belongs to **`elpUser`** (`ELP-0001` → EXAKTA + pumpkin plugin), and the bench to **`masterUserExakta`**.
Had this not surfaced, the acceptance run would have been written against a user that cannot capture.

**8.5 — ⭐ The demo depends on two files that are in no repo.** O3's "keep the real DB" means the ELP
calibration (authored once, server DB) and the 50 MB archive (app DB) are load-bearing and un-versioned.
⇒ **F6**, the DB snapshot, and the honest re-definition of "standalone" in the header.

**8.6 — There are two `spectracsPyServer.db` files, and one is two months stale.** `~/.spectracsPy/` holds a
176 KB July copy next to the app DB, because the *server* once ran from a `spectracsPy`-named cwd; the live one
is `~/.spectracsPy-server/spectracsPyServer.db` (274 KB, August). A wrong cwd in AppRun would not error — it
would quietly demo a July server with no authored calibration. D2's table is now explicit about which is which.

**8.7 — The server process writes an app DB too, and always has.** `SpectracsPyServer.__createBootstrapSession`
calls `session_factory()` — the **app** engine — so a `~/.spectracsPy-server/spectracsPy.db` exists (77 KB) and
a second one will appear under any new server cwd. Harmless, pre-existing, dev-identical. Recorded so it is not
mistaken for an AppImage bug at 2 a.m.

**8.8 — Removing the splash is verified safe, and Alembic-as-data is verified reachable.** `pyi_splash` is
already inside a bare `try/except` in `spectracsMain.py`, so D5 changes nothing at runtime. And the frozen path
arithmetic checks out: `__file__` for a frozen module is `<bundle>/sciens/…`, four levels up from
`databaseEntity/` is the bundle root, and `script_location = %(here)s` then resolves inside the bundled
`alembic/app/`. ⚠ Still *derived*, not observed — §9.2 is where it becomes a fact.

---

## 8b — Second rubber-duck pass (2026-09-09, aimed at the BUILD, not the design)

The first pass ducked the *design* against the code. This one ducks the **build and the run**, and it found two
defects in this spec's own `AppRun`.

**8b.1 — ⛔ Two bugs in §5.2, both mine.** (i) The last line was `exec "$BIN/…"`, which **replaces the shell —
so the `EXIT` trap never fires and the bundled server survives the app**, holding `127.0.0.1:8091` until the
laptop is rebooted. Nothing would look wrong until the *next* launch reused a stale daemon. (ii) `trap 'kill $!'`
expands `$!` at **fire** time, not at trap-set time. Both fixed in §5.2. ⭐ This is the argument for ducking a
shell script as carefully as a Python module: neither bug produces an error message.

**8b.2 — PyInstaller writes `build/` and `dist/` into the cwd, and `.gitignore` covers neither.** Building in
the repo would drop two untracked directories — one of them ~450 MB — into a tree we are tagging as *the*
frozen state. ⇒ §13 builds with explicit `--workpath` / `--distpath` outside every repo. (Checked: `.gitignore`
lists `.gallery/`, `__pycache__/` and the Android artifacts; no `build/`, no `dist/`.)

**8b.3 — Save dialogs default to the cwd**, because `getSaveFileName(…, "measurement_report.pdf", …)` passes a
bare filename (`DevMeasurementBenchViewModule.py:426`; same for "Save frame",
`DevCaptureViewModule.py:474`). Since D2 sets the cwd for the data-dir rule, it also silently sets where the
demo's PDF lands. ⇒ the anchor is now `~/Spectracs/…`, visible, instead of a dotted folder.

**8b.4 — ⭐ `prepProtocol.txt` is in the data dir, so it travels — and `--fresh` loses it.** The recipe stamped
into every run resolves to `~/.spectracsPy/prepProtocol.txt`. Keeping the real data dir (O3) means the AppImage
stamps the same recipe as the dev app; a `--fresh` run silently reverts to the plugin's declared default, which
is precisely the drift `PrepProtocolResolver` exists to stop. Recorded in D2 as a ⛔.

**8b.5 — ⛔ There is no app icon.** `resource/logo.png` is **606×59** — a wordmark, not an icon; `splash.png` is
468×388. An AppImage wants a square (256×256) for `.desktop` + the file's own thumbnail. Nothing in any repo
provides one. ⇒ **decision needed** (§14 N3): pad the wordmark onto a transparent 256×256 square (zero-effort,
looks thin), crop the splash, or draw a small mark. Build-time asset, no code change either way.

**8b.6 — The build must run with cwd = `spectracsPy`,** because the spec's `pathex` entries are relative
(`../spectracsPy-core`, …) and PyInstaller resolves them against the **process cwd**, not the spec file's
location. A build launched from anywhere else silently misses four repos and fails at import time, deep in the
run. §13 pins the cwd.

**8b.7 — Two Spectracs processes on one SQLite file.** If the dev app is left running during the demo, both it
and the AppImage open `~/.spectracsPy/spectracsPy.db`. SQLite permits it, but a write during a capture can
raise `database is locked`. Not worth engineering around — worth a line in the runbook: **close the dev app
before presenting.** (The server side is already handled: AppRun defers to a running daemon.)

**8b.8 — matplotlib builds its font cache on first use**, a few seconds, inside the first PDF export. Harmless
in dev, ugly in front of an audience. ⇒ §13's smoke run exports one PDF, which warms `~/.cache/matplotlib`
before the presentation.

---

## 8c — Third rubber-duck pass (2026-09-09, aimed at what LEAVES the building)

Two findings; the first is the only one in three passes with a consequence outside this laptop.

**8c.1 — ⛔⛔ The frozen bundle may ship Qt modules we do not use, and two of them are *not LGPL*.**
`QtCharts` is **dead in the source** — grep finds only comments recording the pyqtgraph migration, not one
import (`ChartThemeUtil`, `SpectralJobGraphViewModule`, …). But the libraries are physically in the venv, and
PyInstaller's PySide6 hook is historically greedy about `PySide6/Qt/lib`:

| library | size | licence |
|---|---|---|
| `libQt6WebEngineCore.so.6` | **160 MB** | LGPL, but never used — pure weight |
| `libQt6Charts.so.6` | 2.2 MB | ⛔ **GPL / commercial only** |
| `libQt6DataVisualization.so.6` | 1.5 MB | ⛔ **GPL / commercial only** |
| the rest of `Qt/lib` + `qml/` + `resources/` | 294 + 27 + 21 MB total | mixed |

⭐ **The whole QtCharts→pyqtgraph migration (`SPEC_pyside6_and_android.md`) was done to get out from under that
GPL.** Shipping `libQt6Charts.so.6` inside a file handed to a third party (N7) would silently undo it — for a
library the code no longer calls. And WebEngine alone is **54 % of `Qt/lib`**.

⇒ **N8, a build gate, not a hope:** after S1, list the frozen tree and **fail the build** if it contains
`libQt6Charts|libQt6DataVisualization|libQt6WebEngine`. One `grep` over `find`; it turns a licence question
into a checkable fact. Excluding WebEngine + QML also removes ~200 MB, which is most of the difference between
a 220 MB and a 400 MB file.

**8c.2 — The AppRun port-wait is load-bearing, not cosmetic.** `MainContainerViewModule.__init__` calls
`syncMasterData()` (line 23) *before the window appears*, and it is wrapped in a `try/except` that prints
`"master-data sync failed, continuing without it"` and carries on (line 75). So an app started before the
server binds does **not** fail — it comes up **silently missing synced spectrometer + spectral-line master
data**, and the only evidence is one line on a stdout nobody is reading during a presentation. ⇒ §5.2's poll
loop is the thing that prevents a quiet, wrong demo, and §9.2 should read the console for that string.

---

## 8d — Fourth rubber-duck pass (2026-09-09, aimed at THE PLAN)

Three passes ducked the artifact. This one ducks §15's ordering — and found the plan's own sequencing wrong.

**8d.1 — ⭐⭐ Tags are retroactive, so "freeze first" was a false constraint.** §15 had P2 (tag seven repos)
*before* P3 (build), because the freeze was framed as the thing that protects the presentation. But P3 **will**
edit `spectracsAppImage.spec` — iterating on missing hidden imports is the entire content of that phase — and
the spec file lives in a repo we just tagged. The plan as written **guaranteed** the `…-2` re-tag that F4
describes as an exception.

`git tag <name> <sha>` works on any commit at any time. So: **tag last, pointing at the SHAs recorded in §4.**
Nothing is lost, and the near-certain re-tag disappears.

⭐ **What actually carries the insurance is not the tag.** It is (a) the **DB snapshot** (F6 — the only
irreplaceable thing here) and (b) **the seven SHAs written down in §4 of this document**, which are in git the
moment this spec is committed. The tag is a convenience label over a record that already exists. That reframing
is what lets the freeze move to the end of the plan without weakening it.

**8d.2 — The icon does not block the build.** P1 was made to depend on N3 (the missing icon, 8b.5). Checked:
PyInstaller's `icon=` is **Windows/macOS only** — on Linux it logs *"Ignoring icon; supported only on Windows
and macOS!"* and carries on. The icon is needed **only** by the `.desktop` + `.DirIcon` in the AppDir. ⇒ N3
blocks **P6**, not P1, and the whole build can proceed while the artwork is still undecided.

**8d.3 — ⭐ The rig is live and the camera path is deterministic.** Checked right now:
`/sys/class/video4linux/` holds **video0 + video1, both "HD USB Camera"** — the ELP, exposing its capture node
and its UVC metadata node, which is exactly the pair `SensorCaptureIndexResolver` disambiguates through the
`index` file (2.11). There is **no laptop webcam** in the list, so nothing competes; and even if one appeared,
resolution is by VID/PID, never by index. ⇒ P5's gate is reachable today, and "which camera will it pick on
the day?" is a non-question. Recorded so it is not re-worried about at 2 a.m.

**8d.4 — One display case has never been tested: the projector.** The app opens `showMaximized()` and sizes its
minimums from `primaryScreen().availableGeometry()`. Every click-through in this project has run on this
monitor. A mirrored projector at 1024×768 is a geometry this GUI has never seen, and `--phone` addresses
*width*, not height. ⇒ **rehearsal item, not a build item**: plug the projector in once, before the day.

---

## 8e — Fifth rubber-duck pass (2026-09-09, re-ducking the design AFTER D1's reversal)

Removing the server changed the shape, so the design is worth re-reading. Four findings; the second is the one
that would have been mistaken for an AppImage bug.

**8e.1 — ⚠ Starting the app *before* the server costs ~10 s of dead window.** `getProxy()` is called fresh at
all **21** call sites — nothing is cached. `MainContainerViewModule.__init__` makes **two** of those calls
(`syncSpectrometers`, `syncSpectralLineMasterDatas`) *before the window appears*. With no server listening each
one walks: loopback (instant refusal) → a psutil socket scan → `locate_ns("sciens.at")` at `COMMTIMEOUT = 5 s`.
⇒ **~10 s of nothing, twice over, and every later call repeats it.** ⇒ the runbook's order is not a preference:
**server first, then double-click** (§17).

⭐ **The good news, checked:** because nothing is cached, the app **recovers without a restart**. Start the
server late, press *Log in* again, and the next `getProxy()` finds it. Worth knowing on stage.

**8e.2 — ⛔⛔ The AppImage is frozen; the server it talks to is not.** D1's reversal put the two halves of the
Pyro contract on different clocks: the app is pinned at `presentation-2026-09-12`, while `runServer.sh` starts
whatever is in the **live working tree**. Any post-freeze edit to an RPC signature or a serializer would break
the demo in a way that looks exactly like a packaging fault. ⭐ **Fix costs nothing, because P3 already creates
the worktrees: start the server from the tagged worktree**, not from `~/development`. Its directory is even
named `spectracsPy-server`, so D2's cwd rule still lands on `~/.spectracsPy-server`. Tag parity on both sides,
for free.

**8e.3 — `chmod +x`.** The single most common "the AppImage does nothing" cause, and it is invisible: a
double-click on a non-executable file silently does nothing in most file managers. One line in §17.

**8e.4 — Double-clicked, there is no console — and this app talks.** `AppRun`'s manifest print, the
CAPTURE-SETTINGS lines, `"master-data sync failed…"` (8c.2), every capture diagnostic: all of it goes to a
stdout that does not exist when launched from a file manager. If something misbehaves on Saturday there is
nothing to read. ⇒ **`AppRun` should tee to a log when it has no tty** — three lines, no app change:

```bash
if [ ! -t 1 ]; then exec >> "$APP_CWD/spectracs.log" 2>&1; fi   # double-clicked: keep the evidence
```

---

## 9 — Acceptance: the click-through that certifies the build

1. `./Spectracs-<tag>-x86_64.AppImage` → manifest prints; login screen within ~20 s (record the number).
2. No Qt platform-plugin error; **the alembic step ran** (no traceback from `DatabaseInitializer`) — this is
   where 8.8 stops being derived.
3. Log in `masterUser/masterUser` → user admin lists the seeded users ⇒ server, server DB, seeding work.
4. Saved-runs list shows the **real archive** ⇒ D2 landed on `~/.spectracsPy` (O3).
5. ⭐ **GATE (D7/O4): with the ELP plugged in**, log in `elpUser/elpUser` (8.4) → wizard → one reference + one
   sample capture → a `Q%` verdict ⇒ cv2/V4L2, the sysfs resolver, plugin import (2.9) and the science stack.
6. ⭐ **GATE: `masterUserExakta` → dev bench** → a capture against the **authored** calibration ⇒ the server DB
   snapshot (F6) is the right one (8.6).
7. Status bar shows the connection indicator green, and unplugging turns it red ⇒ 8.2's libusb bundling.
8. Settings for SENAITE / PayPal / plugin publishing show **disabled controls, not tracebacks** (D9).
9. Export the M2 PDF from the bench ⇒ matplotlib + `resource/logo.png` (2.10) + pypdf; and no
   `luxpy`/`pandas` ImportError anywhere (D6).
10. Close the app → `ss -ltn | grep 8091` is empty ⇒ no orphan daemon (5.2b).
11. *(optional, not a gate)* run once with a clean `HOME` ⇒ proves the file works for someone else.

---

## 10 — Work plan

⭐ **Superseded by §15 (Implementation phases), which carries exit gates.** Keeping two plans in one spec is
how they drift apart; §15 is the one to work from.

---

## 11 — Non-goals

Windows/macOS · the Android APKs · auto-update · GPG/code signing · a `.deb`/Flatpak · a remote server ·
shipping any secret, key, or corpus · **any** change to app behaviour, layout or science.

---

## 12 — Open questions — **all four answered 2026-09-08 (Edwin)**

| | question | answer | lands in |
|---|---|---|---|
| **O1** | date + machine | *"on this machine claude is running on"* | D8, §8.1 — portability risk collapses |
| **O2** | which virtual fileset | *"we will need no virtual fileset"* | **D7** — nothing ships |
| **O3** | shared or virgin data | *"keep the real db"* | **D2**, and it forced **F6** + the header caveat |
| **O4** | real ELP or virtual | *"the real ELP camera"* | D7, §9.5–9.6 become **gates** |

Residual, minor: the exact tag date (`presentation-2026-09-<dd>`), and where under
`spectracs-references/` the F6 snapshot lives.


---

## 13 — Where and how the build actually runs

### 13.1 Where

**Build root: `~/spectracs-build/<tag>/`** — on `/home` (135 GB free; the build needs ~2.5 GB for
`work/` + `dist/`). ⛔ **Not inside any repo** (8b.2), and ⛔ **not `/tmp`** (it lives on `/` here, and is wiped
on reboot — a build you may want to re-inspect on Saturday morning should survive Friday night).

```
~/spectracs-build/presentation-2026-09-XX/
├── src/            # seven `git worktree` checkouts of the tag, sibling-named (F3)
│   ├── spectracsPy/  spectracsPy-core/  spectracsPy-model/  spectracsPy-base/
│   └── spectracsPy-server/  spectracs-plugins/  spectracs-docs/
├── work/           # PyInstaller --workpath
├── dist/           # PyInstaller --distpath  → spectracsAppImageEntry/
├── smoke/          # throwaway cwd anchors for the staged tests (13.3)
├── Spectracs.AppDir/
└── Spectracs-<tag>-x86_64.AppImage
```

⚠ **The venv is not in the worktree.** `spectracsPy/venv` is untracked, so a fresh checkout has none — call
PyInstaller by its **absolute path in the live venv** while the *cwd* is the worktree. That is also why the
worktrees must keep their exact repo names: the spec's `pathex` entries are relative (`../spectracsPy-core`,
…) and resolve against the cwd (8b.6).

⭐ **Order matters:** write the build files → **commit** them → **tag** → *then* `git worktree add`. The entry
shim and the `.spec` are part of the release; a worktree cut before they are committed will not contain them.

### 13.2 The build command

```bash
TAG=presentation-2026-09-XX
B=~/spectracs-build/$TAG
cd $B/src/spectracsPy                                   # 8b.6 — cwd IS pathex's anchor
/home/nidwe72/development/spectracs/spectracsPy/venv/bin/pyinstaller \
    --noconfirm --clean \
    --workpath $B/work --distpath $B/dist \
    spectracsAppImage.spec
```

Python 3.10.12 · PyInstaller **5.10.1** · PySide6 6.5.0 · glibc 2.35 — all recorded in the manifest (F2), all
already installed. Expect **2–5 minutes** and `dist/spectracsAppImageEntry/`.

> ℹ️ On PyInstaller 5.x the bundled data lands *beside* the executable and `sys._MEIPASS` points there;
> PyInstaller 6.x moved it into `_internal/`. Both keep `_MEIPASS` correct, so 2.7/2.10's path arithmetic
> survives either — but the manifest pins the version that was actually used.

### 13.3 Staged bring-up — ⭐ the part that decides whether this is a good Friday or a bad one

Five stages, each proving one layer, so a failure is *localised* instead of "the AppImage doesn't start".

| stage | command (abbreviated) | proves | if it fails |
|---|---|---|---|
| **S1** | the build, 13.2 | imports resolve at *analysis* time | missing `hiddenimports` — read the warn file in `work/` |
| **S2** | ⭐ `QT_QPA_PLATFORM=offscreen …/spectracsMain` from a throwaway cwd | **Alembic-as-data (2.7/8.8)** — `initAppDatabase()` runs at import — plus plugin import (2.9), the science stack and the five-repo path merge, **with no display** | the alembic `datas` mapping, a missing `pathex` entry, or a lazy import PyInstaller could not see |
| ~~S3~~ | ⛔ **gone with D1** — the 10-second *server-only* smoke test no longer exists | it was the cheapest proof of the alembic mapping; S2 now carries that alone | — |
| **S4** | a real GUI run **straight out of `dist/`**, server from S2 up: login → ELP capture → **export one PDF** | everything except the AppImage layer; warms the matplotlib font cache (8b.8) | Qt platform / camera / resource paths |
| **S5** | AppDir + `AppRun` + `appimagetool` | the packaging layer only | fall back to **A6** — the `dist/` tree already works, tar it |

⭐ **S2 is the single highest-value test in this spec.** No display, no camera, no login, and it exercises the
two things most likely to be wrong in a frozen build (the Alembic tree as data, the five-repo path merge). Run
it before anything else. ⚠ D1's reversal cost the even cheaper server-only variant, so S2 is now the only
pre-GUI gate.

### 13.4 Packaging (S5)

```bash
wget …/appimagetool-x86_64.AppImage && chmod +x appimagetool-x86_64.AppImage
# AppDir: usr/bin/spectracs ← dist/…, AppRun (§5.2), spectracs.desktop, spectracs.png, .DirIcon → spectracs.png
ARCH=x86_64 ./appimagetool-x86_64.AppImage Spectracs.AppDir Spectracs-$TAG-x86_64.AppImage
```

One network fetch (the tool is itself an AppImage; `libfuse2` is present, §8.1). `.DirIcon` is a symlink to the
icon and appimagetool refuses to build without it.

---

## 14 — Decisions needed (nothing below is blocked on code)

| | decision | recommendation |
|---|---|---|
| **N1** | ~~the tag name~~ | ✅ **ANSWERED 2026-09-09: the presentation is Saturday ⇒ `presentation-2026-09-12`.** ⭐ Event date, **not** build date — rationale in **F1a** |
| **N2** | where the **F6 DB snapshot** lives | `spectracs-references/releases/<tag>/` — un-versioned, off git, beside the other material that must not be public |
| **N3** | the **app icon** (8b.5). Blocks **P6 only** (8d.2) | ✅ **LEAN: the S glyph on the splash's charcoal** (`icon_candidate_S_dark.png`) — your existing mark, cropped; no new artwork; legible at 32 px. Recipe + the measurement that killed the alternative: **§16** |
| **N4** | **worktrees (F3) or build in place** | worktrees. Seven commands, and it makes "the AppImage is the tag" true by construction rather than by hope |
| **N5** | the **anchor root** `~/Spectracs/` — it will appear in your home directory, and the demo's PDFs land in it (8b.3) | keep it; visible beats dotted for a live demo |
| **N6** | the two **post-freeze one-liners** (`isSensorConnected`'s missing `NoBackendError` guard, §8.2; persisting the virtual-fileset folder, §7) | **after** the presentation. Neither can bite on this machine, and a freeze that admits exceptions is not a freeze |
| **N7** | will the file be **handed to anyone else**? | ⚠ **weakened by D1**: an app-only AppImage is useless to someone with no server. Still bundle the xcb/xkb/libusb libs (~1 MB, 20 min) — cheap, and it keeps the option open |
| **N9** | ~~how you start it on Saturday~~ | ✅ **ANSWERED: "double clicking the appImage"** ⇒ **P6 + P7 are mandatory and Friday is a real deadline.** It also makes §7a a rehearsal item: start `service_pyro.py` with the WLAN off, once |
| **N10** | ~~the demo script~~ | ⛔ **WITHDRAWN 2026-09-09.** Edwin: *"I just want an AppImage file that acts as runApp.sh does now. Why do you need the user?"* — correct: the build is user-agnostic. The login only ever mattered to *my* acceptance run, which is my problem, not a decision. §9 simply tests **both** paths (`elpUser` wizard + `masterUserExakta` bench) |
| **N8** | ⛔ the **licence gate** (8c.1) — fail the build if `libQt6Charts` / `DataVisualization` / `WebEngine` are in the frozen tree | **yes, unconditionally.** It costs one `grep`, saves ~200 MB, and protects the reason the pyqtgraph migration happened in the first place |


---

## 15 — Implementation phases  *(re-ordered by §8d — the tag moved to the END)*

Gates are **exit criteria**: a phase is done when its gate is *observed*, not when its work is typed.

```
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| PH  | phase                     | EXIT GATE (observed, not assumed)         | effort | needs / blocks on |
+=====+===========================+===========================================+========+===================+
| P0  | DB SNAPSHOT (F6)          | 2 files copied via sqlite3 .backup,       |  5 min | nothing           |
|     | THE irreplaceable thing   | ~50 MB + ~274 KB, stored off git          |        | *** DO IT FIRST **|
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P1  | RECORD THE FREEZE         | this spec committed+pushed; SS4 lists the |  5 min | P0                |
|     | (SS4's 7 SHAs, in git)    | 7 SHAs; all 7 repos verified clean        |        | <- real insurance |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
|     |  >>> after 10 minutes the presentation is protected: code recorded, data copied. <<<               |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P2  | BUILD FILE (just one)     | spectracsAppImage.spec exists; NO shim    |  30 min| P1                |
|     | the .spec (NO icon yet)   | (D1); nothing under sciens/ touched       |        | (N3 not needed)   |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P3  | PYINSTALLER BUILD (S1)    | dist/spectracsMain/ exists AND LICENCE    | 2-4 h  | P2, N4            |
|     | 7 worktrees + build       | GATE N8 passes (no Charts / DataVis /     |        | open-ended tail:  |
|     |                           | WebEngine anywhere in the tree)           |        | hidden imports    |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P4  | HEADLESS SMOKE (S2)       | offscreen boot: alembic runs, plugins     |  15 min| P3                |
|     | offscreen app boot        | import, no traceback. No display needed   |        | <- cheapest test  |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P5  | REAL RUN FROM dist/ (S4)  | login -> ELP capture -> Q% -> one PDF;    |   1 h  | P4; rig LIVE;     |
|     | the demo, unpackaged      | console shows NO "sync failed" (8c.2)     |        | server started BY |
|     |                           |                                           |        | HAND (D1, SS17.5) |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
|     |  >>> a working artifact exists. Px is reachable from here on. Everything below is polish. <<<      |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P6  | APPIMAGE PACKAGING (S5)   | one .AppImage, chmod +x, double-click     | 1-2 h  | P5, N3 (icon), N5 |
|     | AppDir + AppRun + tool    | starts it (AppRun ~15 lines incl. the     |        | MANDATORY (N9)    |
|     |                           | no-tty log, 8e.4)                         |        |                   |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P7  | ACCEPTANCE (SS 9.1-9.11)  | 9.5 + 9.6 green with the real ELP on the  |   1 h  | P6  MANDATORY;    |
|     | + WLAN-OFF REHEARSAL      | authored calibration; plus ONE cold start |        | *** BY FRIDAY *** |
|     | via the AppImage          | with the WLAN off, server from the        |        | (N9)              |
|     |                           | WORKTREE (SS7a, 8e.2)                     |        |                   |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| P8  | THE TAG (F1-F5)           | 7 annotated tags pushed at SS4's SHAs;    |  20 min| P3's final .spec  |
|     | retroactive, LAST (8d.1)  | RELEASE_<tag>.md written                  |        | (N1 settled)      |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
| Px  | FALLBACK (A6)             | tar of dist/ + run.sh starts the app      |  15 min| P5 only           |
|     | if P6/P7 fight back       | same content, no AppImage layer           |        |                   |
+-----+---------------------------+-------------------------------------------+--------+-------------------+
```

**What changed against the first layout, and why (8d.1):** the tag was P2 and is now **P8**. P3 rewrites the
`.spec` several times — that is the *content* of P3 — and the `.spec` sits inside a repo the old plan had
already tagged, so the first layout guaranteed the `…-2` re-cut that F4 treats as an exception. Tags are
retroactive; nothing is lost by applying them at the end, and what actually protects the presentation moved
into **P0+P1, ten minutes at the front**: the corpus copied, the SHAs written down and pushed.

**Two structural facts worth reading off the table:**

* **After P1 (10 min) the freeze exists.** Not as a label — as a copied 50 MB DB and seven SHAs in a committed
  document. Everything after that is convenience, and can fail without costing the presentation.
* **After P5 a working artifact exists**, so **Px is always reachable**. The AppImage layer is allowed to lose.

⚠ **P3 is the only phase with an open-ended tail.** If its gate has not gone green by the time you want to
stop, go to Px from P5 and ship the tarball. ⚠ And one item is on nobody's critical path but belongs on the
day's list: **plug in the projector once** (8d.4) — the only display geometry this GUI has never met.


---

## 16 — The icon (N3), measured

⛔ **My first recommendation was wrong and the measurement says so.** "Pad the 606×59 wordmark onto a 256×256
square" is zero effort, but rendered down to a 32 px taskbar icon the wordmark is **32×3 px** — an illegible
smudge. Checked, not guessed.

⭐ **The icon already exists inside the wordmark: its first glyph.** `resource/logo.png` is the word SPECTRACS
in an outlined techno face; an alpha-column scan finds six glyph runs, the first being **x = 0…62, 62×59 px** —
a complete, on-brand **S**. Placed on the splash screen's own charcoal ground (`#1a1a1a`, read from
`resource/splash.png`) it is legible at 32 px and unmistakable at 256.

```python
# reproducible, no new artwork, no design decision to defend:
#   1. alpha-column scan of resource/logo.png -> glyph runs; take the first, (0,62)
#   2. crop to its alpha bounding box                        -> 62 x 59
#   3. scale to 168 px, centre on a 256x256 #1a1a1a canvas   -> spectracs.png
#   4. cp spectracs.png .DirIcon                             (appimagetool requires it)
```

Candidates rendered 2026-09-09 (scratchpad, not committed — a P6 build step, not a repo asset):
`icon_candidate_S_dark.png`, `icon_candidate_S_transparent.png`, `icon_candidate_wordmark.png`, and the two
`_at32.png` proofs that decide it.

ℹ️ A transparent-ground variant exists too; the dark ground matches the splash and reads better against a light
file manager. Either is one line of the recipe. Nothing here is a brand decision — it is *the existing mark,
cropped*.


---

## 17 — How to run it

### 17.1 On the day — the two steps, in this order

⛔ **Order matters (8e.1): server first.** Starting the app first costs ~10 s of dead window and a failed login.

```bash
# 1) the server — from the TAGGED worktree (8e.2), on loopback so no WLAN is needed (§7a)
cd ~/spectracs-build/presentation-2026-09-12/src/spectracsPy-server
PYTHONPATH=".:../spectracsPy:../spectracsPy-model:../spectracsPy-base" \
  ~/development/spectracs/spectracsPy/venv/bin/python service_pyro.py
# leave this terminal open; it prints:  SpectracsPyServer serving locally at PYRO:…@127.0.0.1:8091

# 2) the app — double-click Spectracs-presentation-2026-09-12-x86_64.AppImage
#    (once, beforehand:  chmod +x Spectracs-*.AppImage   — 8e.3)
```

Then log in as usual: **`masterUserExakta`** for the dev bench, **`elpUser`** for the end-user wizard (2.16).

⭐ **If you forget step 1**, nothing is lost: the login will say *server unavailable*, you start the server, you
press *Log in* again. No restart — the proxy is never cached (8e.1).

### 17.2 Where things go

| what | where | why |
|---|---|---|
| the app DB (saved runs, 50 MB) | `~/.spectracsPy/spectracsPy.db` | D2 — the real one, your archive |
| the server DB (users, the authored ELP calibration) | `~/.spectracsPy-server/spectracsPyServer.db` | D2; ⚠ **not** the stale copy in `~/.spectracsPy/` (8.6) |
| the lab recipe stamped into every run | `~/.spectracsPy/prepProtocol.txt` | 8b.4 — travels for free |
| exported PDFs, saved frames | `~/Spectracs/spectracsPy/` | 8b.3 — save dialogs default to the cwd |
| the console log when double-clicked | `~/Spectracs/spectracsPy/spectracs.log` | 8e.4 |

### 17.3 Flags

| flag | effect |
|---|---|
| *(none)* | ⭐ the normal case: your real DBs, exactly as `runApp.sh` today |
| `--fresh` | virgin app DB in `~/.spectracsPy-demo` — rehearsing a customer's first launch. ⛔ **never for a real measurement**: no `prepProtocol.txt`, so the recipe silently reverts to the plugin default (8b.4) |
| `--phone`, `--phone=412`, `--phone-zoom=1.1` | unchanged from today — they pass straight through to `spectracsMain` (D4) |

### 17.4 Stopping

Close the window. The server is a separate terminal: `Ctrl+C`. ⭐ With D1's reversal there is no background
process to leak — nothing to orphan on `127.0.0.1:8091` (§5.2).

### 17.5 During the build (not the day)

Run the frozen app straight out of `dist/` before it is ever packaged — that is stage **S4**, and it is the same
program the AppImage will run:

```bash
cd ~/Spectracs/spectracsPy && ~/spectracs-build/<tag>/dist/spectracsMain/spectracsMain
```
