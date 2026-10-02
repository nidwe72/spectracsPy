# SPEC — Plugin-switched lamp (Shelly Plus Plug S)

Status: **IMPLEMENTED** 2026-10-02 (P0–P6, P8; §18 as built). First click-through on the rig passed (Edwin:
"everything seems to work fine for now"). Owed: **P7** (password on the real plug — none set yet) and a full P9.
Design history: §1–§17 (rubber-duck review folded in, §14–§16).
Source: Edwin, 2026-10-02, decisions given inline in the chat. Hardware context:
`spectracs-hardware/ammoBox-spec.md` §5 (ammo-box prototype, Yuji SunWave 230 V E27 in the lid, socket
plugged into a Shelly Plus Plug S).

## 1. Goal

The plugin switches the lamp itself: **on** when the workflow enters ACQUISITION, **off** when it enters any
other phase. A jar is in the beam only while it is being measured, so no light dose falls on a waiting
sample (`SPEC_capture_quality.md` §16.36: light browns, irreversibly). A lamp icon in the header shows the
state and lets the user switch the lamp by hand.

## 2. Decisions (Edwin, 2026-10-02)

| # | Decision |
|---|---|
| D1 | The lamp is **on for the reference and the sample capture**, one continuous on-period through the jar swap. The **plugin** declares it. |
| D2 | **Warm-up: fixed 20 s** after switching on, before the reference may be captured. **Visible in the GUI**. Closes the open question of `SPEC_capture_quality.md` §8 for the switched lamp. |
| D3 | **Hard cap = the plugin's maximal measurement time + 5 min**, then the lamp goes off, no deferral. Dev plugin: 1500 s + 300 s = **30 min**. |
| D4 | The cap is **enforced by the plug itself** (`toggle_after`), so it holds even when the app has crashed. No app heartbeat. ⏸ Postponed: a script running on the Shelly. |
| D5 | **Enter hooks only.** On entering a phase the host applies the plugin's lamp state for that phase (on in ACQUISITION, off elsewhere). No leave hook. |
| D6 | **Lamp icon** in the header, third beside camera and account, same chrome as the camera icon: shows off / warming / on, **click = toggle**. A phase entry **overrides** a manual toggle. |
| D7 | **Driver-agnostic**: one interface, one driver per vendor. **Shelly Gen2 only for now**; Tasmota / USB strip postponed. |
| D8 | **Discovery** of the plug on the LAN; no IP typed in by hand. Dependency **`zeroconf`** is added. |
| D9 | **Password**: entered in the GUI, **persisted locally in the app DB**. |
| D10 | **No plug found / unreachable ⇒ manual**: the measurement proceeds, the user switches the lamp at the socket. Never blocks. |
| D11 | **No lamp-on time** in the measurement record. |
| D12 | HTTP via the **stdlib** (`urllib`), no `requests`. |
| D13 | Tests use a **fake Shelly HTTP server**; no hardware in the suite. |
| D14 | **Cancel / go home / view hidden ⇒ off** (host safety, not a plugin hook). |
| D15 | **App closed ⇒ off**, guaranteed by a hook on every exit path the app can see (§7.1); the plug's cap covers the rest. |

⭐ **Heat is no longer a factor.** It was with isopropanol, where the lamp's heat cleared the fill. With
sunflower oil as the solvent, heat does not help clarify the sample, so switching the lamp off between
measurements costs nothing on that side (Edwin, 2026-10-02).

## 3. The Shelly Gen2 API (what is used)

All calls are `GET http://<ip>/rpc/<Method>?…`, JSON response. With a device password set: HTTP **digest**
auth, user `admin`.

| Call | Use |
|---|---|
| `GET /shelly` | identify without auth: `gen` = 2, `app` = `"PlusPlugS"`, `model` = `SNPL-00112EU`, `id` = `shellyplusplugs-<mac>`, `mac`, `auth_en` (read from Edwin's plug 2026-10-02, fw 1.0.7) |
| `Switch.Set?id=0&on=true&toggle_after=<cap>` | on + the hard cap (D3/D4) |
| `Switch.Set?id=0&on=false` | off |
| `Switch.GetStatus?id=0` | `output` (bool), `apower` (W), `timer_started_at` / `timer_duration` (remaining cap) |

- ⭐ **Power check:** ~1 s after `on`, read `apower`. The Yuji draws ~10 W. **< 2 W ⇒ the toggle switch on
  the E27 socket is off** (or the bulb is dead): coach line says so. Does not block (D10).
- The cap is sent **once, with the on-command**. An on-command to an already-on plug is **not** sent
  (it would restart the timer and stretch the cap). ⚠ Rig-verify that `Switch.Set on=false` clears a
  pending `toggle_after` (expected).
- Safety net independent of the app, set **once by hand** in the Shelly web UI (not by the app):
  `Auto off` after 30 min. Then even a lamp switched on with the plug's own button goes off.
- LED ring (`PLUGS_UI.SetConfig`) is also configured once by hand (ammoBox-spec §5).
- ⚠ Superseded by §15: power check at **3 s**; the "by hand" safety net is not set yet (`auto_off=false`).
- ✅ **Seen on Edwin's plug (2026-10-02):** on the home WLAN (`Sciens2G6971`, WPA2, 2.4 GHz) at `192.168.1.123`;
  `avahi-browse -rt _shelly._tcp` finds it with TXT `app=PlusPlugS gen=2 ver=1.0.7`; `/shelly` answers
  unauthenticated. Firmware updated to 1.3.3 the same day (`Shelly.Update?stage=stable`, ~40 s, settings kept;
  `initial_state` = off ⇒ after a power cut the lamp stays dark). Onboarding stalled in `connecting` until the WLAN password
  was written via `WiFi.SetConfig` — a typo in the web form is the usual cause, and the status gives no hint.

## 4. Structure

```
spectracsPy-core  (Qt-free)
  plugin_sdk/policy/LampPolicy.py          # what the plugin declares
  logic/lamp/LampSwitch.py                  # interface
  logic/lamp/LampDriver.py                  # vendor driver: discovery identity + probe + factory
  logic/lamp/ShellyGen2LampSwitch.py        # the only driver for now
  logic/lamp/NoLampSwitch.py                # no plug: manual at the socket; virtual device
  logic/lamp/LampDiscovery.py               # cache → mDNS → subnet, driver-agnostic

spectracsPy-model
  DbLampPlug + Alembic migration (app tree)

spectracsPy (app, Qt)
  logic/lamp/LampService.py                 # singleton: worker thread, warm-up clock, cap clock
  view/main/MainStatusBarViewModule.py      # lamp icon (D6)
  view/settings/…                           # lamp section: plug found, password, search again, test
  hooks in AbstractPluginExecutionView, CapturePanel, spectracsMain
```

### 4.1 `LampSwitch` (interface)

```python
class LampSwitch:
    def on(self, capSeconds: int) -> None: ...  # switch on + hard cap where the device supports it
    def off(self) -> None: ...
    def status(self) -> LampStatus: ...         # isOn, watts | None, capRemainingSeconds | None
    def describe(self) -> str: ...              # "Shelly Plus Plug S 192.168.1.42"
```

Short timeouts (2 s); raises `LampUnreachable` on any network error, `LampAuthFailed` on 401. stdlib
`urllib` + **an own SHA-256 digest helper** (`hashlib`): Shelly Gen2 challenges with `algorithm=SHA-256`, which
Python 3.10's `HTTPDigestAuthHandler` cannot answer (§14 R1). Still D12.

### 4.2 `LampDriver` (per vendor)

```python
class LampDriver:
    name: str                                     # "shelly-gen2"
    mdnsServiceTypes: list[str]                   # ["_shelly._tcp.local."]
    def probe(self, host) -> LampDevice | None    # confirm: a switchable plug of this vendor (mac, model, authRequired)
    def create(self, device, password) -> LampSwitch
```

A registry lists the drivers; Tasmota later = one more `LampDriver`, nothing else changes (D7).

### 4.3 `LampPolicy` (plugin_sdk)

```python
class LampPolicy:          # plain class + default() + getters, like NavigationPolicy (§14 R5)
    switched: bool = False                        # default: the plugin does not touch the lamp
    onDuringPhases: frozenset = frozenset({SpectralWorkflowPhaseType.ACQUISITION})
    warmUpSeconds: int = 20                       # D2
    maxMeasurementSeconds: int = 1500             # the plugin's longest capture (its MonitorPolicy.maxSeconds)
    marginSeconds: int = 300                      # D3
    # capSeconds = maxMeasurementSeconds + marginSeconds
```

Carried on `WorkflowPolicy` next to `NavigationPolicy` (`SpectralPlugin.policy()`), so existing plugins are
unchanged until they opt in. The dev plugin opts in with `maxMeasurementSeconds=MONITOR_MAX_SECONDS`
(one constant, no second copy) ⇒ cap 1800 s. The pumpkin plugin likewise.

⚠ The 5-min margin is the whole budget for **warm-up + reference + jar swap**. A user who takes longer
than that and then runs a full-length settled sample hits the cap inside the capture. That is accepted
(D3: hard). The app knows the cap clock, so it **stops the running capture at the cap** with the message
"Lamp switched off after 30 min — measurement stopped" instead of letting dark frames into the evaluation.

## 5. Discovery (D8)

The systematic route is **mDNS / DNS-SD**, the mechanism printers and Chromecasts use to announce
themselves. Shelly Gen2 devices advertise `_shelly._tcp` with hostname `shellyplusplugs-<mac>.local`.

1. **Stored plug** (`DbLampPlug`: driver, host, mac): probe it (`GET /shelly`, 1 s). Same MAC ⇒ use it.
   The normal case, no multicast needed.
2. **mDNS browse**, 3 s, over every registered driver's service types; each answer confirmed with the
   driver's `probe` (Shelly: `gen >= 2` and a `switch:0` component — accepts the Plus Plug S Gen3 too).
3. **Fallback heuristic:** the local /24 subnet, `GET /shelly` on all 254 addresses in parallel (~0.3 s
   timeout, ~2 s total). Catches networks that drop multicast.
4. Result:
   - **stored MAC found** ⇒ use it, update its host if the IP changed (DHCP).
   - **exactly one** plug ⇒ use it, store it.
   - **several** ⇒ the first, the others listed in the Settings lamp section (⏸ a picker is a later slice).
   - **none** ⇒ no plug (D10).

- `zeroconf` goes into `requirements.txt`, version pinned. ⚠ **Not pure Python** (Cython `.so` wheels): needs `collect_submodules("zeroconf")` + `ifaddr` in all three PyInstaller specs and an import check in the AppImage verify step; p4a needs `SKIP_CYTHON` or a recipe (§14 R7).
- ⚠ **Android:** receiving multicast needs `CHANGE_WIFI_MULTICAST_STATE` + a `WifiManager.MulticastLock`.
  Out of scope now (desktop first); steps 1 and 3 work there without it.
- Discovery runs on the worker thread at **app start**, and again on "Search again" in Settings or when
  the stored plug fails its probe.

## 6. Password (D9)

- New local entity **`DbLampPlug`** in the **app** DB (not the server: the plug belongs to this machine's
  network): `driver`, `host`, `mac` (unique), `model`, `password` (nullable). Alembic migration in the app
  tree (`SPEC_schema_migrations.md`).
- `/shelly` reports `auth_en`. Needed and missing/wrong ⇒ the icon shows "no plug" and the coach line says
  "Lamp plug needs a password — Settings → Lamp".
- ⚠ The password is stored **in plain text** in the local SQLite: the plug's own API only knows digest auth
  with the clear password, so a hash is of no use. Acceptable for a plug password on a lab machine; noted.

**Settings → Lamp** (new section in `SettingsViewModule`, all users, since every desk has its own plug):

```
 Lamp plug   Shelly Plus Plug S · 192.168.1.42 · MAC A8:03:2A:…   ● reachable
 Password    [••••••••        ]   [Save]
             [Search again]   [Test: on 2 s]
```

## 7. `LampService` (app)

Singleton, modelled on `CameraWarmupService`. All network I/O on **one worker QThread** (pattern:
`logic/connection/ConnectionPollThread.py`); the GUI thread never waits on HTTP. Results come back as
signals.

States: `NO_PLUG · OFF · WARMING(remaining) · ON`.

- `switchOn(capSeconds, warmUpSeconds)`:
  - OFF ⇒ `on(cap)`, start the **warm-up clock** (from the confirmed on) and the **cap clock**; power check
    after 1 s.
  - WARMING / ON ⇒ nothing (no re-send, the cap is not stretched; a warm lamp is not re-warmed).
  - NO_PLUG / `LampUnreachable` ⇒ NO_PLUG (D10).
- `switchOff()`: `off()` ⇒ OFF. Errors are logged, never shown as a failure — the plug's cap covers them.
- **Cap clock** expires ⇒ state OFF (the plug has already switched), signal `capReached` ⇒ CapturePanel
  stops a running capture (§4.3 ⚠).
- **External change** (someone pressed the plug's button, or the Shelly's own auto-off fired): a
  `Switch.GetStatus` poll every **10 s while not NO_PLUG** keeps the icon true. Cheap, one request.
- **App close ⇒ lamp off**: see §7.1 (D15).
- Signals: `stateChanged(state)`, `warmUpTick(remaining, total)`, `capReached()`, `hint(text)`.

### 7.1 Lamp off when the app closes (D15)

One idempotent `LampService.shutdown()`: if a plug is known and the lamp is not known to be off, send
`off()` **synchronously on the calling thread** (not via the worker, which may already be stopping), 2 s
timeout, **one retry**, then log. A flag makes the second and later calls no-ops. It is wired to every exit
path Python can see:

| Exit path | Hook |
|---|---|
| main window closed, File→Quit, `app.quit()` | `app.aboutToQuit.connect(shutdown)` in `spectracsMain.py`, before `sys.exit(app.exec())` (:197) |
| `sys.exit()` anywhere, normal interpreter end | `atexit.register(shutdown)` |
| Ctrl+C in the terminal, `kill`, terminal closed, session logout | `signal` handlers for `SIGINT`, `SIGTERM`, `SIGHUP` ⇒ `shutdown()` then `app.quit()`. A 500 ms `QTimer` no-op keeps the Python interpreter able to run the handler while Qt's event loop is in C++. |
| window closed **during a capture** (nested `QEventLoop`s, `aboutToQuit` would wait up to 25 min) | `MainContainerViewModule.closeEvent ⇒ shutdown()` |

⛔ **Not catchable by any hook**, and covered only by the plug's cap (D3/D4, ≤ 30 min): `kill -9`, a
segfault inside Qt/OpenCV, power loss of the PC, Wi-Fi gone at the moment of closing. That is why the cap
lives on the plug and not in the app.

Android (later): the same `shutdown()` from the activity's `onStop`/`onDestroy`; swiping the app away
does not reliably call either ⇒ again the cap.

## 8. Phase hook (D5)

Both hosts share `view/spectral/workflow/AbstractPluginExecutionView.py`. All phase changes go through
`_renderCursor` (:202) — Next, Back, AUTO_ADVANCE jumps, and the first render after `_startNewRun` (:102).

```
on entering a phase P (P != previous phase):
    if policy.lamp.switched:
        P in policy.lamp.onDuringPhases  ->  LampService.switchOn(cap, warmUp)
        otherwise                        ->  LampService.switchOff()
```

One enter hook, no leave hook: leaving ACQUISITION *is* entering PROCESSING (or METADATA, …), which
switches off. Re-entering ACQUISITION via Back switches on again (warm-up only if the lamp was off).

**Not a phase entry**, so D5 alone would leave the lamp on; host safeties switch it off (D14):
- **Cancel / go home** (Wizard `onClickedCancel` :313, Bench cancel → `__goToSettings` :532) and **the
  view being hidden** (Wizard `hideEvent` :80, Bench `hideEvent` :93) ⇒ `switchOff()` if the plugin is
  `switched`.
- **App closed** ⇒ §7.1.

## 9. GUI

### 9.1 Lamp icon (D6)

> ⚠ **Superseded in parts by §16** (states, glyphs, NO_PLUG click, visibility). Read §16.2 first.

Third icon in the header row of `MainStatusBarViewModule`, left of the camera (connection) icon, **same
chrome** (bordered `QToolButton`, `HEADER_CONTENT_HEIGHT`), a bulb glyph recoloured by state like the camera:

| State | Glyph | Click |
|---|---|---|
| NO_PLUG | grey bulb, tooltip "No lamp plug — switch the lamp at the socket" | opens Settings → Lamp |
| OFF | white bulb | on (cap + warm-up as in ACQUISITION) |
| WARMING | amber bulb + a filling ring / "12 s" overlay | off |
| ON | yellow bulb, tooltip "on · switches off in 23 min" | off |

- Hidden when logged out (same rule as the camera icon). Visible outside a workflow too, so the lamp can
  be checked from anywhere.
- A manual toggle is **overridden by the next phase entry** (D6): switch it on in EVALUATION and it stays
  on until the next phase change switches it off; switch it off in ACQUISITION and the capture gate (§9.2)
  holds until the user switches it on again.

### 9.2 Capture gate and countdown (D2)

- `CapturePanel.__updateControls` (:441) enable expression gains `and lampService.readyForCapture()`
  = state is ON, **or** NO_PLUG (no gate without a plug: the app cannot know when the lamp at the socket
  was switched on).
- **Countdown** in the status bar's determinate bar (`__emitElapsed` :1212 style): **"Lamp warming up 0:12
  of 0:20"**, plus the icon overlay (§9.1).
- **Coach line** (`AcquisitionGuidance.emit`), which wins over the normal next-action cue while warming:
  - WARMING: "Lamp is warming up — wait 20 s before the reference."
  - OFF in ACQUISITION: "The lamp is off — switch it on with the lamp icon."
  - power check < 2 W: "The plug is on but the lamp draws no power — check the switch on the lamp socket."
  - NO_PLUG: "No lamp plug found — switch the lamp on yourself and let it warm up 20 s."

## 10. Virtual device

`NoLampSwitch` silently, **no hint, icon hidden**: a virtual spectrometer has no lamp. Selected when the
spectrometer is virtual, before discovery is consulted.

## 11. Tests (D13)

- `tests/fakes/FakeShellyServer.py`: `http.server` on a random localhost port in a thread; implements
  `/shelly`, `Switch.Set` (incl. `toggle_after` against an injectable clock), `Switch.GetStatus`, optional
  digest auth, settable `apower`, and a "go dark" switch for unreachable.
- Driver: on/off/status, cap timer fires, digest auth ok/wrong, timeout ⇒ `LampUnreachable`.
- Discovery: stored-plug hit, IP changed (same MAC), MAC mismatch, subnet fallback against the fake (mDNS
  mocked), none ⇒ NO_PLUG.
- `LampService` (offscreen, fake timers): warm-up ticks → ON; on while ON sends nothing; cap ⇒ OFF +
  `capReached`; external change seen by the poll.
- Exit paths (§7.1), each in a **subprocess** that starts a minimal app with the service pointed at the fake
  server and switches on, then ends by: `app.quit()` · `sys.exit()` · `SIGTERM` · `SIGINT` · `SIGHUP` ·
  an unhandled exception ⇒ the fake server must have received `on=false`. `shutdown()` twice sends once.
- Host: entering ACQUISITION ⇒ on exactly once; entering PROCESSING ⇒ off; Back into ACQUISITION ⇒ on; a
  plugin without `switched` never touches the lamp; manual toggle overridden by the next phase entry.
- `DbLampPlug` migration up/down.

## 12. Slices

| Slice | Content | Rig? |
|---|---|---|
| L1 | `LampSwitch`, `ShellyGen2LampSwitch`, `NoLampSwitch`, fake server + driver tests | no |
| L2 | `LampDriver` registry + `LampDiscovery` + `zeroconf`; `DbLampPlug` + migration | no |
| L3 | `LampService`: worker thread, warm-up clock, cap clock, status poll, exit hooks (§7.1) + subprocess tests | no |
| L4 | `LampPolicy` in plugin_sdk; enter hook in `_renderCursor`; dev + pumpkin plugins opt in | no |
| L5 | GUI: lamp icon, Settings → Lamp (password, search, test), capture gate, countdown, coach lines, cap stops capture | no |
| L6 | **Rig click-through**: discovery on the real WLAN, password, warm-up gate, swap, enter PROCESSING ⇒ dark, manual toggle, cap ⇒ dark (with a shortened test cap), close the window / Ctrl+C / close the terminal ⇒ dark at once, `kill -9` ⇒ dark at the cap | yes |

## 13. Out of scope (now)

Tasmota / USB-strip drivers · a script on the Shelly (D4) · Android multicast lock · a picker between
several plugs · lamp-on time in the record (D11) · using the switched lamp as a **shutter during the
settled wait** (lamp on only for short bursts while the sample settles). `SPEC_settled_measurement.md`
§9.4 rejected that because the lamp's heat held the isopropanol sample above its cloud point; with the
sunflower solvent that reason is gone, so it could be revisited — but the 20 s warm-up per burst and the
question of what the settled wait still waits for without heat-clearing make it its own topic.

## 14. Rubber-duck review (2026-10-02)

An independent review of this spec against the code. All file:line references in §7–§9 were **confirmed**;
every phase entry (first render, Back, Next multi-jump, AUTO_ADVANCE, VIEW) does pass `_renderCursor`.

### 14.1 Corrections (already applied above)

| # | Was | Is |
|---|---|---|
| R1 | stdlib `HTTPDigestAuthHandler` | Shelly uses **SHA-256 digest**; Python 3.10 urllib only does MD5/SHA ⇒ own helper; the fake server must challenge with SHA-256 too, or the tests hide it |
| R2 | `sys.excepthook` ⇒ off | **dropped**: in PySide6 a slot exception reaches the excepthook and the app *keeps running* ⇒ the lamp would go off on any slot error |
| R3 | `aboutToQuit` covers the window close | not during a capture (nested loops) ⇒ **`MainContainerViewModule.closeEvent`** added |
| R4 | `PhaseType` | `SpectralWorkflowPhaseType` (spectracsPy-model, re-exported by `plugin_sdk`) |
| R5 | frozen dataclass | plain class + `default()` + getters; `WorkflowPolicy(navigation=None, lamp=None)` + `getLamp()`; `LampPolicy` in `__all__` |
| R6 | pumpkin cap from its `MonitorPolicy` | the pumpkin plugin has neither `policy()` nor a monitor ⇒ its own explicit number; dev's `MONITOR_MAX_SECONDS` is a float ⇒ `int()` |
| R7 | zeroconf "pure Python" | Cython wheels ⇒ hidden imports, pinned, verify step |
| R8 | probe `gen == 2 and app == "PlugS"` (wrong anyway: the real value is `"PlusPlugS"`) | `gen >= 2` + `switch:0` |

### 14.2 Additional rules

- **Every** `Switch.Set on=true` carries `toggle_after`: one without it **cancels** the running timer.
- The cap clock is the **app's**; `timer_started_at` is device time (unreliable without SNTP) ⇒ only "timer
  running yes/no" is read from the plug.
- Power check after **2–3 s**, not 1 s (meter latency).
- `_lastLampPhase` is reset in `_resetRunState` (Bench plugin change re-enters without a hide). Dedupe by
  **phase**, not cursor: Reference and Sample are two stops of one phase.
- An explicit `not self._isView()` guard in the hook, although VIEW already gets `WorkflowPolicy.default()`.
- Hooks only **post** to the worker; `capReached` only sets the capture's cancel flag (as
  `__onClickedCapture` does). Nothing blocks or spins a loop on the GUI thread.
- `shutdown()` also `quit()` + `wait(≤ 1 s)` the worker QThread ("QThread destroyed while running").
  Timeout **1 s** × 2 tries (not 2 s: a dead Wi-Fi would hang the close for 4 s).
- Signals via `signal.set_wakeup_fd` + `QSocketNotifier` instead of a 500 ms poll timer; `SIGHUP` guarded
  with `hasattr` (Windows build).
- **NO_PLUG icon click** shows a tooltip/menu, **not** a jump to Settings: navigating from inside a running
  capture would throw the run away.
- Entity name **`LampPlug`** (app entities carry no `Db` prefix, cf. `ApplicationConfig`), in
  `model/databaseEntity/application/`, listed in `AllEntities`, `down_revision` from `alembic heads`.
- Subnet scan: pick the interface carefully (docker, VPN bridges).

### 14.3 Decided (Edwin, 2026-10-02)

| # | Question | Decision |
|---|---|---|
| Q1 | Lamp switched on by hand long before; entering ACQUISITION sends nothing ⇒ the capture starts on a nearly spent cap | ✅ **re-arm** (`on` + `toggle_after=cap`) on ACQUISITION entry when the remaining cap < `maxMeasurementSeconds` |
| Q2 | Sealed DB plugins run against the host SDK. An opted-in plugin on an older app ⇒ ImportError instead of the friendly gate message | ⏸ **no SDK bump now**: no distributed plugin is in use, the change is additive. Bump to 2 (and reseal) **before the first plugin goes to an app that is not built from this tree** |

### 14.4 Implementation steps (first review; superseded by §15.4)

```
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| #  | Step                                 | Content                                       | Done when                      | Rig  |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 1  | Core driver                          | LampSwitch, ShellyGen2LampSwitch (own SHA-256 | driver tests green against the | no   |
|    | (spectracsPy-core)                   | digest), NoLampSwitch, FakeShellyServer with  | fake, incl. auth ok/wrong,     |      |
|    |                                      | SHA-256 challenge                             | timeout, toggle_after          |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 2  | Rig smoke test (CLI, ~10 min)        | tools/lampSmoke.py: /shelly fields, digest,   | the API assumptions of §3 and  | YES  |
|    |                                      | toggle_after, off clears timer, on w/o        | §14.2 confirmed on the real    |      |
|    |                                      | toggle_after cancels it, apower latency       | plug, or the spec corrected    |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 3  | SDK policy                           | LampPolicy, WorkflowPolicy.lamp + getLamp(),  | pure unit tests; plugins       | no   |
|    | (plugin_sdk)                         | export; no SDK_VERSION bump (Q2)              | without lamp unchanged         |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 4  | LampService (app)                    | worker QThread, warm-up + cap clocks, 10 s    | offscreen tests with fake      | no   |
|    |                                      | status poll, re-arm rule (Q1); plug host from | timers + fake server           |      |
|    |                                      | an env var until step 8                       |                                |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 5  | Exit hooks                           | closeEvent, aboutToQuit, atexit, SIGINT/TERM/ | subprocess tests: every exit   | no   |
|    |                                      | HUP via wakeup fd, worker join, idempotent    | path ⇒ fake server got off;    |      |
|    |                                      | shutdown()                                    | shutdown() twice sends once    |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 6  | Host enter-hook + safeties           | _renderCursor hook (phase dedupe, reset in    | host tests with a fake         | no   |
|    |                                      | _resetRunState, VIEW guard); cancel/home/     | service: on once, off on       |      |
|    |                                      | hide ⇒ off (D14); dev + pumpkin opt in        | PROCESSING, VIEW never         |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 7  | GUI                                  | lamp icon (4 states, toggle, NO_PLUG = tip),  | offscreen: gate holds while    | no   |
|    |                                      | capture gate via stateChanged ⇒               | WARMING/OFF, capReached sets   |      |
|    |                                      | __updateControls, countdown, coach lines,     | the cancel flag                |      |
|    |                                      | capReached ⇒ cancel flag                      |                                |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 8  | Persistence + discovery + Settings   | LampPlug entity + Alembic migration,          | migration up/down; discovery   | no   |
|    |                                      | AllEntities; discovery stored → subnet;       | tests vs fake; Settings saves  |      |
|    |                                      | Settings → Lamp (password, search, test)      | the password                   |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 9  | mDNS + packaging                     | zeroconf (pinned) browse; hidden imports in   | AppImage built, verify step    | no   |
|    |                                      | the 3 PyInstaller specs; AppImage import      | imports zeroconf               |      |
|    |                                      | check                                         |                                |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
| 10 | Rig click-through (old L6)           | discovery on the real WLAN, password, warm-   | Edwin's click-through          | YES  |
|    |                                      | up, swap, PROCESSING ⇒ dark, manual toggle,   |                                |      |
|    |                                      | short test cap, every close path ⇒ dark,      |                                |      |
|    |                                      | kill -9 ⇒ dark at the cap                     |                                |      |
+----+--------------------------------------+-----------------------------------------------+--------------------------------+------+
```

## 15. Rubber-duck review, round 2 (2026-10-02, after the real plug answered)

New facts: the plug is on the WLAN (`192.168.1.123`, fw **1.3.3**, `auth_en=false`, `auto_off=false`,
`initial_state=off`); `diagnostics/lamp_plug_blink.py` switched it 3× with `toggle_after`; **11.2 W at 3 s**
with the Yuji, 0.0 W off. ⇒ the power check reads at **3 s**; the §3 "safety net by hand" is **not set yet**.

### 15.1 Proposed answers (⏸ = Edwin to confirm)

| # | Gap | Proposal |
|---|---|---|
| G1 ✅ | **"Set up plug" button** in or out? | **OUT** (Edwin, 2026-10-02): joining the WLAN, the password, `auto_off=1800` and the LED ring are done **by the user in the Shelly's own web page**; the app never changes the plug's configuration, it only switches it. The app only **hints** (step 8b, §15.5). The password is typed into Settings → Lamp only so the app can log in (D9 unchanged). 2b runs once Edwin has set a password by hand |
| G2 | worker pattern: `ConnectionPollThread` has no command input | a `QObject` worker **moved to a QThread**, commands as queued slots; clocks behind an injectable monotonic-clock seam for the tests |
| G3 | manual toggle with **no workflow running**: which cap / warm-up? | host default **1800 s / 20 s** |
| G4 | **logout** / **virtual↔real device switch** | logout ⇒ `switchOff()`; device switch ⇒ off first, then `NoLampSwitch` or re-discovery (listens to `userSessionSignal`) |
| G5 | **external change** seen by the poll | seen on ⇒ ON with *unknown* remaining cap (⇒ the Q1 re-arm fires on the next ACQUISITION entry); seen off **during a capture** ⇒ stop the capture like `capReached` (no dark frames into the evaluation) |
| G6 | **two app instances** on one plug | accept and document: no single-instance lock; G5 catches the other instance's off |
| G7 | hook order + Bench/Wizard sharing the singleton | the lamp hook runs **first** in `_renderCursor`, before `_ensurePopulated` (else the lamp stays on through the PROCESSING compute); `switchOff()` from `hideEvent` carries an **owner token** — only the view that issued the last on may switch off |
| G8 | Settings → Lamp: role, device, position | **all roles** (outside `updateAdministrationVisibility`), **hidden for a virtual device**, grid row 1 before Downloads (rows renumbered) |
| G9 | "lamp line wins" has no mechanism | one shared `AcquisitionGuidance.lampLine(state)` that both hosts consult before their own cue |
| G10 | small fixes | paths are `sciens/spectracs/…`; driver tests + `tests/fakes/FakeShellyServer.py` live in `spectracsPy/tests/` (core has no tests dir); env var **`SPECTRACS_LAMP_HOST`** stays permanently as the test seam; `MainContainerViewModule.closeEvent` is **new**, not extended |

### 15.2 Order changes

- Old step 2 split: **2a** (no password, extends `diagnostics/lamp_plug_blink.py`) runs **first**, so the
  driver is written against verified behaviour; **2b** (digest auth, `auto_off` interaction) after 8b.
- **6 and 7 merged**: switching without the warm-up gate would let a capture start on a cold lamp.
- **mDNS moves into step 8** (avahi already found the plug); the subnet scan becomes the fallback; packaging
  stays step 9.

### 15.3 Rig checks for 2a

off clears a pending timer · on **without** `toggle_after` cancels a running timer · on to an already-on
plug restarts the timer · `timer_started_at` / `timer_duration` present · `apower` at 1 / 2 / 3 s.

### 15.4 Implementation steps with GUI changes (replaces §14.4)

```
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| #   | Step                       | Content                             | GUI change                               | Rig |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 2a  | Rig API check              | extend lamp_plug_blink.py: timer    | none (CLI)                               | YES |
|     |                            | semantics, apower latency (§15.3)   |                                          |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 1   | Core driver                | LampSwitch, ShellyGen2LampSwitch    | none                                     | no  |
|     |                            | (SHA-256 digest), NoLampSwitch,     |                                          |     |
|     |                            | FakeShellyServer + tests            |                                          |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 3   | SDK policy                 | LampPolicy, WorkflowPolicy.lamp     | none                                     | no  |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 4   | LampService                | QObject worker on QThread, clocks,  | none (plug only via SPECTRACS_LAMP_HOST) | no  |
|     |                            | poll, re-arm, G3/G4/G5              |                                          |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 5   | Exit hooks                 | closeEvent (new), aboutToQuit,      | nothing on screen; closing the app makes | no  |
|     |                            | atexit, signals, worker join        | the lamp dark (close may take <=2 s if   |     |
|     |                            |                                     | the plug is unreachable)                 |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 6+7 | Host hook + GUI            | _renderCursor hook (first, owner    | HEADER: bulb button left of the camera:  | no  |
|     |                            | token, VIEW guard), cancel/home/    |   grey  = no plug (tip on click)         |     |
|     |                            | hide/logout => off; dev + pumpkin   |   white = off (click = on)               |     |
|     |                            | opt in; icon, gate, countdown,      |   amber + "12 s" = warming (click = off) |     |
|     |                            | coach lines, cap/external-off stop  |   yellow = on, tooltip "off in 23 min"   |     |
|     |                            | the capture                         |   hidden: logged out / virtual device    |     |
|     |                            |                                     | STATUS BAR: "Lamp warming up 0:12/0:20"  |     |
|     |                            |                                     | CAPTURE PANEL: button greyed while       |     |
|     |                            |                                     |   warming or off                         |     |
|     |                            |                                     | COACH LINE: warming / lamp off / no      |     |
|     |                            |                                     |   power - check socket switch / no plug  |     |
|     |                            |                                     | CAP: capture stops, "Lamp switched off   |     |
|     |                            |                                     |   after 30 min - measurement stopped"    |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 8   | Persistence + discovery +  | LampPlug + migration; discovery     | SETTINGS: new "Lamp" section, all roles, | no  |
|     | Settings                   | stored -> mDNS -> subnet;           |   hidden for virtual device:             |     |
|     |                            | Settings -> Lamp                    |   plug model/IP/MAC + reachable dot,     |     |
|     |                            |                                     |   password + [Save], [Search again],     |     |
|     |                            |                                     |   [Test: on 2 s], other plugs found      |     |
|     |                            |                                     | COACH LINE: "Lamp plug needs a password  |     |
|     |                            |                                     |   - Settings -> Lamp"                    |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 8b  | Unconfigured-plug hint     | Wi-Fi scan for an open "Shelly..."  | SETTINGS -> Lamp + grey icon tooltip:    | no  |
|     | (G1, §15.5)                | SSID whose MAC is not on the LAN    |   "Unconfigured Shelly found nearby ..." |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 2b  | Rig auth check             | digest auth + auto_off interaction  | none (CLI)                               | YES |
|     |                            | on the real plug with a password    |                                          |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 9   | Packaging                  | zeroconf hidden imports, AppImage   | none                                     | no  |
|     |                            | import check                        |                                          |     |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
| 10  | Rig click-through          | the whole flow on the real rig      | none (verification)                      | YES |
+-----+----------------------------+-------------------------------------+------------------------------------------+-----+
```

### 15.5 Step 8b — the unconfigured-plug hint (G1)

The app does **not** set up the plug. It only notices a plug that still needs setting up and says how.

- **Heuristic:** the PC's Wi-Fi list (Linux: `nmcli -t -f SSID,SECURITY dev wifi list`) contains an **open**
  network matching `Shelly*-<12 hex>` ⇒ a Shelly in setup mode.
- ⚠ **A configured Shelly keeps its own network on** by default (Edwin's plug still broadcasts
  `ShellyPlusPlugS-E86BEAE3CB60` while on the WLAN). ⇒ the hint is **suppressed when the 12 hex digits in the
  SSID equal the MAC of a plug already found on the LAN**. Only a plug that is *not* on the LAN triggers it.
- **Where it shows:** Settings → Lamp, and the tooltip of the **grey** lamp icon (no plug found). Never a
  popup, never during a capture.
- **Text:** "Unconfigured Shelly `ShellyPlusPlugS-…` found nearby. Connect to its Wi-Fi, open
  http://192.168.33.1, and add your WLAN under Settings → Wi-Fi (2.4 GHz). Then set a password and auto-off
  (30 min) there, and enter the password here."
- When it runs: with discovery (app start, "Search again"). No Wi-Fi adapter, `nmcli` missing, or Windows/
  Android ⇒ no hint, silently (Windows `netsh wlan show networks` and Android later).
- Tests: the scan output is parsed by a pure function (fixture strings: unconfigured plug · configured plug
  with AP on · no Shelly).

## 16. Rubber-duck review, round 3 — GUI / UX (2026-10-02)

Checked against `MainStatusBarViewModule`, `CapturePanel`, `AcquisitionGuidance`, `SettingsViewModule`,
`DESIGN_GUIDE.md`, the Director scenarios. Fine as is: **no i18n** in the app (no `tr()`), English-only
texts are consistent; the bench refuses virtual devices and the virtual wizard path bypasses `CapturePanel`;
offscreen tests use plugins that do not opt in.

### 16.1 Findings and proposals (⏸ = Edwin to confirm)

| # | Finding (evidence) | Proposal |
|---|---|---|
| U1 | **One widget, three writers.** The status bar has a single `progressBar` (`MainStatusBarViewModule.handleApplicationStatusSignal` :410-444); guidance text, indeterminate and determinate bars overwrite each other; a capture owns it from click to end (`CapturePanel` :624-631). Countdown + coach line at once ⇒ flicker | WARMING = **one determinate emit that is also the coach line** ("Lamp warming up — 0:12 of 0:20"); written only in ACQUISITION and `not panel.isCapturing()`. Outside that (manual toggle in EVALUATION) only the icon counts down |
| U2 | **Nothing refreshes guidance on a lamp change**: hosts re-derive only on render/tab/capture (`WizardViewModule` :128, :241; Bench :141, :318) ⇒ "warming" would stick after ON | both hosts connect `LampService.stateChanged` → their guidance refresh (guarded: visible, ACQUISITION, not capturing) |
| U3 | **Amber means "act here"** (`getGuidanceColor` #C9942E; camera icon amber = warming) ⇒ an amber WARMING bulb invites a click that switches the lamp **off**; the amber ● is still painted on the gated capture button (`AcquisitionGuidance` :85-91) | WARMING = **white bulb + progress ring**; the amber cue goes **on the lamp icon only when OFF in ACQUISITION** (then it is the next action); no ● on the capture button while `not readyForCapture()` |
| U4 | **Director scenario breaks**: `automation/scenarios/measurement_bench.py:132-139` clicks CAPTURE right after `wait_for_human`; during the warm-up the click is lost, `wait_capture` returns, `wait_ready(NEXT)` times out; narration "illuminate the slit" is stale | `d.wait_ready(CAPTURE, enabled=True, timeout=40)` before each capture click; narration updated. Part of step 6+7 |
| U5 | **Wrong stop message**: the cancel flag path prints "Capture cancelled — nothing recorded…" (`CapturePanel` :911-918), then guidance overwrites it | a `cancelReason` on CapturePanel selecting the text ("Lamp switched off after 30 min — measurement stopped" / "Lamp went off — measurement stopped"), kept until the next user action |
| U6 ✅ | **Icon clickable during a capture**: one misclick kills a 25-min settled run | the icon keeps **showing the true state** (ON stays the yellow filled bulb); only its **click is ignored while a capture runs** (tooltip-free; no confirm dialog) |
| U7 ✅ | **Plug-less real desks get a nag every measurement**; grey bulb permanently in the header; virtual ≠ NO_PLUG but `lampLine(NO_PLUG)` would fire in the virtual path | new state **NOT_APPLICABLE** (virtual, or plugin not `switched`): no line, no icon, no gate. NO_PLUG = a short hint **appended** to the normal cue, not replacing it. **Icon shown only if a `LampPlug` row exists or discovery found one** |
| U8 | **No SEARCHING / UNREACHABLE**: discovery takes ~5 s at start ⇒ NO_PLUG flashes, gate open; a failed poll mid-capture (Wi-Fi drop) unspecified | **SEARCHING** (gate closed, `switchOn` queued until discovery ends); **UNREACHABLE** (last-known glyph + "?" badge, "Plug not answering", **no** capture stop — the lamp is probably still on) |
| U9 ⏸ deferred (Edwin: not of primary interest) | **Phone header**: logo + 70 px camera + 70 px account (:115-143); a third 70 px button squeezes the logo to ~17 px tall | header buttons **56 px under phone width**; with U7 the icon is absent on most desks anyway; check `--phone` and `--phone=360` |
| U10 | **No tooltips on touch; `QMenu` crashes on Android** (:300-305) — §14.2 and §15.5 relied on them | NO_PLUG / UNREACHABLE click ⇒ `InWindowDialog.notify` with the text; the §15.5 setup hint lives **only in Settings → Lamp** as a selectable label |
| U11 | **State by colour only** (white vs yellow) | outline bulb = OFF, **filled bulb with rays** = ON (same pairing as the account icon's `PERSON_*_SVG` :449-457), `%(c)s` SVG templates via `renderSvgPixmap`. App is dark-only ⇒ no light-theme variant |
| U12 | **A form inside the Settings hub** breaks DESIGN_GUIDE §1A (Settings = navigation buttons) | a "Lamp" group with a **"Lamp plug…"** button opening a new compact **`LampSettingsViewModule`** (registered at the 3 points of DESIGN_GUIDE §6). Password masked like Login (`LoginViewModule` :61). [Save] verifies against the plug; [Test] reports inline: "On 2 s · 11.2 W ✓" / "0 W — check the socket switch" / "Wrong password"; goes through `LampService` |
| U13 | **"→ Settings" hint loses the run**: `WizardViewModule.showEvent` (:73-78) starts a new run on return ⇒ a captured reference is thrown away | the password hint shows **outside workflows** (Home, once at discovery). Inside ACQUISITION: "Plug needs a password — switch the lamp at the socket; set the password after this measurement" |
| U14 | **§9.1 contradicts §14.2/§15.4** (NO_PLUG click opens Settings; icon always visible) | §9.1 marked superseded; §16.2 is authoritative |

### 16.2 Lamp states and icon (authoritative, replaces the §9.1 table)

| State | When | Icon | Click | Capture gate | Coach line (ACQUISITION) |
|---|---|---|---|---|---|
| NOT_APPLICABLE | virtual device, or plugin not `switched` | hidden | — | open | — |
| SEARCHING | discovery running | outline bulb, dimmed | — | **closed** | "Looking for the lamp plug…" |
| NO_PLUG | discovery found none | hidden unless a `LampPlug` row exists; then grey outline + "?" | `notify` "Lamp plug not found — switch the lamp at the socket" | open | appended: "· switch the lamp on at the socket, 20 s warm-up" |
| OFF | plug found, lamp off | **very dim grey** outline bulb = plug ready, quiet, also in ACQUISITION (Edwin 2026-10-02: no amber cue — it read as red) | on | **closed** | "Switch the lamp on (lamp icon)." |
| WARMING | ≤ 20 s since on | white bulb + progress ring | **disabled while capturing**, else off | **closed** | bar: "Lamp warming up — 0:12 of 0:20" |
| ON | warm | **green filled bulb with rays** = ready to measure (Edwin 2026-10-02) | disabled while capturing, else off | open | normal cue |
| UNREACHABLE | poll failed | last glyph + "?" badge | `notify` "Plug not answering" | unchanged | "Lamp plug not answering — check Wi-Fi" (no stop) |

Plus: LampService defaults to **NOT_APPLICABLE in tests** (no discovery, no subnet scan) unless
`SPECTRACS_LAMP_HOST` is set.

## 17. Implementation impact and phases (2026-10-02, final)

### 17.1 Impact

| Repo | New | Changed |
|---|---|---|
| spectracsPy-core | `logic/lamp/` LampSwitch, LampDriver (+registry), ShellyGen2LampSwitch (own SHA-256 digest), NoLampSwitch, LampDiscovery (stored → mDNS → subnet), SSID-hint parser; `plugin_sdk/policy/LampPolicy.py` | `WorkflowPolicy` (+`lamp`, `getLamp()`), `plugin_sdk/__init__` export |
| spectracsPy-model | `LampPlug` entity, Alembic migration (app tree) | `AllEntities` |
| spectracsPy (app) | `logic/lamp/LampService.py` (QObject worker on QThread, clocks, poll); `view/settings/LampSettingsViewModule.py`; bulb SVG templates | `spectracsMain.py` (signals, atexit, aboutToQuit); `MainContainerViewModule` (**new** `closeEvent`); `MainStatusBarViewModule` (lamp icon); `AbstractPluginExecutionView._renderCursor` (enter hook, first); Wizard + Bench (cancel/home/hide ⇒ off, guidance refresh on `stateChanged`); `CapturePanel` (gate, `cancelReason`, no ● while gated); `AcquisitionGuidance` (`lampLine`); `SettingsViewModule` (Lamp group + nav registration); `requirements.txt` (`zeroconf`, pinned); 3 PyInstaller specs + AppImage verify; `automation/scenarios/measurement_bench.py` (wait for enabled CAPTURE) |
| spectracs-plugins | — | DevSpectralPlugin + pumpkin plugin opt in (`LampPolicy`, cap from `MONITOR_MAX_SECONDS` / explicit) |
| tests | `tests/fakes/FakeShellyServer.py`; driver, discovery, SSID parser, LampService, exit-path subprocess, host-hook, gate tests; migration up/down | — |

Not touched: the server, the measurement record (D11), the evaluation, the SDK version (Q2). No change for
virtual devices or plugins that do not opt in (NOT_APPLICABLE).

### 17.2 Phases

```
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P  | Phase                | Content                                 | User sees                            | Rig | Tests |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P0 | Plug API check       | extend lamp_plug_blink.py: off clears   | nothing (CLI)                        | YES | -     |
|    |                      | timer, on w/o toggle_after cancels it,  |                                      |     |       |
|    |                      | repeat-on restarts it, apower 1/2/3 s   |                                      |     |       |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P1 | Core driver          | LampSwitch, ShellyGen2 (SHA-256 digest),| nothing                              | no  | fake  |
|    |                      | NoLampSwitch, FakeShellyServer          |                                      |     | server|
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P2 | SDK policy           | LampPolicy, WorkflowPolicy.lamp         | nothing                              | no  | unit  |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P3 | LampService          | worker thread, warm-up/cap clocks,      | nothing (plug via                    | no  | off-  |
|    |                      | poll, re-arm, all 7 states (§16.2),     | SPECTRACS_LAMP_HOST only)            |     | screen|
|    |                      | logout/device switch => off             |                                      |     |       |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P4 | Exit hooks           | closeEvent, aboutToQuit, atexit,        | closing the app => lamp dark         | no  | sub-  |
|    |                      | SIGINT/TERM/HUP, worker join            |                                      |     | proc. |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P5 | Workflow + GUI       | enter hook (first in _renderCursor,     | header bulb (outline/filled/ring/?), | no  | host +|
|    | (never ship half)    | owner token, VIEW guard); cancel/home/  |   click locked during capture;       |     | gate  |
|    |                      | hide => off; plugins opt in; capture    | capture button locked while          |     |       |
|    |                      | gate; warm-up line; lampLine + refresh; |   searching/off/warming;             |     |       |
|    |                      | cancelReason; Director scenario fix     | "Lamp warming up - 0:12 of 0:20";    |     |       |
|    |                      |                                         | stop message at the cap              |     |       |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P6 | Plug settings +      | LampPlug + migration; discovery         | Settings: "Lamp plug..." page with   | no  | migr. |
|    | discovery            | stored -> mDNS -> subnet; LampSettings- | plug, password, [Save] [Search       |     | disc. |
|    |                      | ViewModule; SSID hint (§15.5)           | again] [Test]; unconfigured-Shelly   |     | parser|
|    |                      |                                         | hint                                 |     |       |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P7 | Password check       | digest auth + auto_off on the real plug | nothing (CLI)                        | YES | -     |
|    | (after Edwin sets one| (by hand in the Shelly web page)        |                                      |     |       |
|    | in the web page)     |                                         |                                      |     |       |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P8 | Packaging            | zeroconf hidden imports, AppImage check | nothing                              | no  | build |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
| P9 | Click-through        | whole flow on the rig                   | -                                    | YES | Edwin |
+----+----------------------+-----------------------------------------+--------------------------------------+-----+-------+
```

Until P6 the app finds the plug only through `SPECTRACS_LAMP_HOST=192.168.1.123`; that is enough to drive
P3–P5 on the rig.

## 18. As built (2026-10-02)

### 18.1 Phase status

```
+----+------------------------+---------+------------------------------------------------------------+
| P  | Phase                  | Status  | Evidence                                                   |
+----+------------------------+---------+------------------------------------------------------------+
| P0 | Plug API check         | DONE    | all 5 timer behaviours confirmed on the real plug          |
| P1 | Core driver            | DONE    | spectracsPy-core logic/lamp; tests vs FakeShellyServer     |
| P2 | SDK policy             | DONE    | LampPolicy; dev 1500+300 s, pumpkin 600+300 s; opt-in only |
| P3 | LampService            | DONE    | real plug: 20 s warm-up -> ON, off on exit (3 runs)        |
| P4 | Exit hooks             | DONE    | quit, sys.exit, close, SIGTERM/INT/HUP, idempotent         |
| P5 | Workflow + GUI         | DONE    | enter hook, capture gate, header icon, Director wait       |
| P6 | Plug settings          | DONE    | LampPlug + migration 63efd411276f, Settings -> Lamp plug   |
| P7 | Password check         | OWED    | Edwin sets a password in the Shelly web page first         |
| P8 | Packaging              | DONE    | zeroconf hidden imports; frozen build imports the lamp     |
| P9 | Click-through          | PARTLY  | 2026-10-02 first pass OK incl. hot-replug + no-plug case   |
+----+------------------------+---------+------------------------------------------------------------+
```

Tests: 74 lamp tests, full suite 614.

### 18.2 Changes from the click-through (Edwin, 2026-10-02)

| # | Change | Where |
|---|---|---|
| A1 | **The plug back during ACQUISITION switches the lamp on.** The phase-entry on was lost when the plug was missing (NO_PLUG) or not answering (UNREACHABLE); a re-plugged Shelly comes up OFF, which closed the capture gate until a manual click. Now: plug found again / answering again + the owning workflow still `wantsOn` + state OFF ⇒ on, fresh 20 s warm-up. A cap or a press on the plug's button still leaves it off (those go through `__markOff(reason=…)`). | `LampService.__resumeForOwner` |
| A2 | **Icon colours** (supersede §16.2 colours): plug ready, lamp off = **very dim grey** outline `#555555` — also in ACQUISITION, the amber cue is gone (it read as red); warming = white outline + ring; on and warm = **green filled bulb with rays** `#6FCF7F`; no plug / unreachable = grey `#808080` with "?". | `LampButton` |
| A3 | **Bulb at 75 %** (`viewBox -4 -4 32 32`) in every state, so the warm-up ring keeps a gap to it and the bulb does not jump when the ring appears. | `LampButton` |
| A4 | **The plug's own LED ring:** off = rgb 20,20,20 % at brightness 3 % (factory: red 100 %), sent once per discovery via `PLUGS_UI.SetConfig`; only the "off" colour is sent, "on" stays as set on the plug (green). Best effort: a failure is ignored. | `ShellyGen2LampSwitch.applyIndicator`, `LampWorker.indicator` |
| A5 | **Camera icon gets the same warm-up ring** (shared `ProgressRing.drawProgressRing`), glyph at 75 %, 1 s refresh, tooltip counts down; **camera warm-up 3 min** (was 9, ⚠ see `SPEC_capture_quality.md` §16.6a); camera "connected & warm" green = the lamp's `#6FCF7F`. | `MainStatusBarViewModule` |

### 18.3 Bugs found on the rig and fixed

| # | Bug | Fix |
|---|---|---|
| B1 | App start failed: `table lamp_plug already exists`. `DbBase.save_session()` / `session_factory()` run `create_all` on every use, so code that touched the real app DB with the new model before the boot-time upgrade had built the table outside Alembic. | Migration `63efd411276f` skips `create_table` when the table exists. ⚠ The same trap waits for every future migration that adds a table — the clean fix (no `create_all` outside the initializer) is a separate task. |
| B2 | Exit with the plug gone: `QThread: Destroyed while thread is still running`. The worker join was 1 s, shorter than one in-flight call (2 s timeout). | Join 2.5 s; a worker still busy after that (a discovery scan) is kept referenced until the process ends and logged (`lamp: worker still busy at exit`). |
| B3 | `test_lamp_service.py` built a `QCoreApplication`; a widget test later in the same process aborted Qt. Hidden in the full suite by test order. | `QApplication`. |
| B4 | `test_app_quit` flaky: the child switched off before the parent looked at `plug.output`. | Assert the received on-command instead. |

### 18.4 Not lamp-related, seen during the click-through

The camera sometimes reports "Capture failed — no frames were delivered by the camera" — **with or without the
plug** (Edwin). The capture-failed path logs nothing, so the run log could not show it. Own task; first step:
log the failure with the frame / rejection counts.

### 18.5 Open

- Should the app search for the plug again by itself (e.g. every 30 s) while none was found? Today only
  Settings → [Search again] does.

