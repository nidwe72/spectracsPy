# Spec — Documentation / screencast automation ("Director" harness)

Status: **IMPLEMENTED (M1, 2026-07-12).** Phases P0–P6 are built and validated on the virtual path (§10);
the bench first-sweep awaits the camera+lamp rig for its live recording. Scope is **desktop Linux (X11)**.
Android and Wayland are out of scope (see §9).

Goal: let the AI that wrote the app **generate a per-scenario script** that drives Spectracs for
tutorial **videos and screenshots**, including **human-in-the-loop** pauses (unplug/replug the USB
spectrometer) with on-screen prompts, and **doc hints rendered inside the app** while it runs. The
recorded video shows a **real, visibly gliding mouse cursor** clicking through the app, a left-screen
prompter telling the operator what to do, and a right-side hint panel narrating each step.

This spec is the settled distillation of the design conversation captured in
`~/Downloads/pumpkin/dokuAutomation.html` (Gemini thread, 2026-07-11/12). It adopts that thread's **final,
external-driver architecture** — not the collapsed all-in-app variant — per Edwin's closing decision to
"use the external tool from the beginning."

---

## 0. Grounding — verified on this machine (2026-07-12)

- **Session is X11** (`XDG_SESSION_TYPE=x11`, `DISPLAY=:0`, `WAYLAND_DISPLAY` empty). PyAutoGUI/xdotool
  move a **visible** cursor natively — no `ydotool` / `/dev/uinput` Wayland workaround is needed.
- The app is **PySide6** (not PyQt5). The Gemini snippets are PyQt5 and must be ported: `QUdpSocket`
  lives in `PySide6.QtNetwork`, signals are `Signal`/`Slot`, `app.exec_()` → `app.exec()`.
- The main window is **`MainContainerViewModule` — a `QFrame` with a `QGridLayout`** (status bar at
  row 0, `MainViewModule` at row 1), **not a `QMainWindow`**. There is therefore **no `QDockWidget`**;
  the hint panel is added as a new **grid column**, shown only in doc-mode.
- CLI flags are parsed by **manual string-scanning** in `spectracsMain.py` (the `--phone` /
  `--phone=` / `--phone-zoom=` family, `_parsePhoneModeArgs`), *before* `QApplication` is constructed.
  `--doc-mode` slots into the same pattern (though it is read *after* `QApplication`, since it does not
  touch `QT_SCALE_FACTOR`).
- `setObjectName` is used in only ~20 places, ad-hoc, with an informal `ClassName.widgetName`
  convention. **There is no systematic accessible-naming scheme yet** — §5 defines one and adds names
  incrementally, only to the widgets a scenario actually touches.
- `PySide6.QtNetwork` is available (Qt ships it). `pyautogui` is **not** yet a dependency (§8).

**Adversarial review findings (2026-07-12, "rubber-duck" pass) that shaped this revision:**
- The **dev measurement bench hard-rejects virtual devices** (`DevMeasurementBenchViewModule.py:404-405`)
  and Capture no-ops without a resolved real camera (`:484`); `Next →` no-ops until both captures exist
  (`:461`). So the bench can **never** be a no-hardware screencast — it needs a real ELP camera **plus a
  lamp on the slit, twice**. The bench is therefore demoted to an **M2 hardware-in-the-loop** screencast
  (§9), and **M1 is the pumpkin `WizardViewModule`** (§7), whose "Measure" runs the engine's
  **virtual-device round-trip** (`WizardViewModule.py:268-272`) — no camera, already covered by
  `test_pumpkin_wizard_offscreen.py`.
- **App entry cannot be driven by `click`.** The Settings entry is a `QAction` inside a `QMenu`
  (`MainStatusBarViewModule.py`), and `QAction` is **not a `QWidget`** → `findChild(QWidget, name)` can
  never resolve it. Navigation to a view therefore uses a **`nav` command** (fires the app's
  `NavigationSignal`), not a click (§4). Reaching the wizard = `nav {"view":"WizardViewModule"}`, which on
  `showEvent` auto-starts a fresh NEW run from the current user's configured plugin
  (`WizardViewModule.py:96-133`) — so the run must be logged in as a user with the pumpkin plugin.
- **Wizard acquisition steps are tabs.** Reference/Sample are two tabs in a `QTabWidget`
  (`WizardViewModule.py:218-233`), each with **its own** Measure button. `locate` must therefore support
  a **tab-header sub-rect** (`tabBar().tabRect(i)`), and per-tab buttons get **role-qualified**
  objectNames to stay unambiguous (§3, §5).
- **Gated transitions need a `wait`, not a `sleep`.** `Next →` is disabled until acquisition is complete
  (`:248-249`); a blind timed click dead-locks. The protocol adds a **`wait` command** that polls a named
  widget's state (§4).
- **Window stacking:** the Prompter is always-on-top; the Director must **raise/activate the app window**
  before each click so a glide doesn't land on the Prompter (§3, §11).

---

## 1. Architecture at a glance

Two processes, one thin seam of local UDP between them:

```
  LEFT SCREEN (operator)                 RIGHT SCREEN (recorded app)
  ┌───────────────────────┐              ┌──────────────────────────────────┐
  │  Director  (external)  │             │  Spectracs  --doc-mode             │
  │                        │  UDP 5555   │  ┌───────────────┬──────────────┐  │
  │  ┌──────────────────┐  │ ──set_hint─▶│  │  normal app   │  Hint panel  │  │
  │  │ Prompter dialog  │  │ ──locate?──▶│  │  (grid col 0) │ (grid col 1) │  │
  │  │ big CONTINUE btn │  │ ◀─rect─────  │  └───────────────┴──────────────┘  │
  │  └──────────────────┘  │  UDP reply  │                                     │
  │  QThread scenario ─────┼──PyAutoGUI──┼──▶ visible cursor glide + click     │
  └───────────────────────┘  (X11)      └──────────────────────────────────┘
```

- **App side** (`--doc-mode`): a **pure receiver**. It shows the hint panel and answers a small set of
  UDP commands (hint / locate / nav / wait / ping — §4). It contains **zero** automation logic and is
  unaffected when the flag is absent.
- **Director side** (external, standalone PySide6 app): owns the operator-facing **Prompter** window and
  runs the scenario on a `QThread`. It sends hints, asks the app *where* a widget is, then drives a
  **real mouse** to click it — so the cursor motion is captured on video.

Rationale for keeping the Director external (not folding clicks into the app, which the thread also
explored): the recorded video must show a **cursor physically moving**; programmatic
`widget.click()` is invisible. The external PyAutoGUI driver is the only variant that produces a
tutorial-grade cursor. The reverse-channel (§3) recovers the robustness we'd otherwise lose.

---

## 2. App side — `--doc-mode`

### 2.1 Flag parsing
Add a trivial scan in `spectracsMain.py` alongside `_parsePhoneModeArgs`:

```python
docMode = "--doc-mode" in sys.argv
```

Pass `docMode` into `MainContainerViewModule(docMode=...)`. Default `False` → the entire feature is
inert. `--doc-mode` composes with `--phone` (a phone-width screencast is valid).

### 2.2 Hint panel
`MainContainerViewModule.__init__`, when `docMode` is true, adds a right-side panel to the existing
`QGridLayout` at **column 1** (main content moves to column 0, span adjusted; status bar spans both):

- A word-wrapped `QLabel` (`objectName="docHintPanel.label"`), styled from the app stylesheet — large
  readable type, generous padding, panel background. Initial text: *"Waiting for Director…"*.
- Fixed/max width ~320 px so it reads well at 1080p and never dominates the app.
- Hidden entirely when `docMode` is false — no column reserved, no layout change (regression-safe).

The panel is owned by a small `DocHintPanelViewModule` (matches the repo's `*ViewModule` convention) so
`MainContainerViewModule` stays thin.

### 2.3 UDP service
A `DocModeUdpService(QObject)` created only in doc-mode:

- `QUdpSocket` bound to `QHostAddress.LocalHost`, **port 5555**.
- `readyRead` → drains datagrams; each is one **JSON object** `{ "cmd": ..., ... }` (§4). `readyRead`
  fires on the **GUI thread** (the socket is created there), so handlers mutate widgets directly — no
  cross-thread marshalling needed (verified).
- `set_hint` → `panel.setText(text)`.
- `locate` → resolve `objectName` via `mainContainerViewModule.findChild(QWidget, objectName)`; if
  found and visible, compute the **global center** and **rect** and reply (§4). With an optional
  `"tab": i` field on a `QTabWidget` target, reply with `tabBar().tabRect(i)` mapped global (so the
  Director can click a *tab header*, not the pane). Not found / not visible → `{ "ok": false }`.
- `nav` → build a `NavigationSignal().setTarget(view)` and hand it to
  `ApplicationContextLogicModule().getNavigationHandler()` — the **only** way to reach a view whose entry
  point is a `QMenu`/`QAction` (not a widget). Reply `{ "ok": true }` once switched.
- `wait` → poll a named widget's state (`enabled` / `visible`, optionally a `text` substring) and reply
  `{ "ok": true }` when satisfied or `{ "ok": false }` on timeout. Lets the Director block on gated
  transitions (e.g. `Next →` enabling only after acquisition completes) instead of guessing with `sleep`.
- `ping` → `{ "ok": true }`.

The service holds a reference to the top-level widget so `findChild` sees the whole tree. Binding
failure (port busy) is logged and non-fatal — the app still runs.

---

## 3. The reverse-channel (why clicks are robust *and* visible)

The recurring unresolved question in the Gemini thread — "how does the driver find the buttons?" — is
answered by exploiting the fact that **we own the target app**:

1. Director wants to click logical widget `"SomeViewModule.connectButton"`.
2. Director sends `{ "cmd": "locate", "name": "SomeViewModule.connectButton" }` and waits (short
   timeout) for the reply.
3. App replies with the widget's **live global coordinates** — computed from `mapToGlobal` at that
   instant, so it is correct regardless of window position, monitor, resolution, `--phone` zoom, theme,
   or scroll offset.
4. Director **raises/activates the app window** (X11 `wmctrl`/`xdotool windowactivate`, or the app
   `raise_()` on nav) so the click can't land on the always-on-top Prompter, then calls
   `pyautogui.moveTo(x, y, duration=…, tween=easeInOutQuad)` and `pyautogui.click()` — a **visible**
   glide to an **exact** target.

This beats both thread alternatives: no fragile fixed coordinates (PyAutoGUI-only) and no invisible
programmatic clicks or AT-SPI env-var setup (Dogtail). Dogtail/AT-SPI is kept as a **deferred fallback**
(§9) only if a target ever can't be reached this way (e.g. a native OS dialog outside the Qt tree).

**Two edge cases the review surfaced:**
- **Tab headers.** `mapToGlobal(center)` of a `QTabWidget` lands in the *pane*, not the tab bar, so it
  can't switch tabs. `locate` takes an optional `tab` index and returns the tab-header rect (§2.3) —
  the Director glides to *that* to switch tabs on camera.
- **Duplicate objectNames across simultaneous tabs.** In the wizard both acquisition tabs exist at once,
  each with a "Measure" button — a bare `findChild(QWidget, "…measureButton")` returns the wrong one.
  Per-tab widgets therefore get **role-qualified** objectNames (`…measureButton.reference`,
  `…measureButton.sample`) so `locate` is unambiguous (§5).

---

## 4. UDP command protocol (127.0.0.1:5555, JSON datagrams)

Director → App:

| cmd        | fields                              | effect / reply                                               |
|------------|-------------------------------------|--------------------------------------------------------------|
| `set_hint` | `text: str`                         | Update hint panel. No reply.                                 |
| `locate`   | `name: str`, opt `tab: int`         | Reply `{ok, cx, cy, x, y, w, h}` (global px) or `{ok:false}`. With `tab`, returns the tab-header rect. |
| `nav`      | `view: str`                         | Fire `NavigationSignal(setTarget=view)`. Reply `{ok:true}` when switched. The way to reach a `QMenu`-entry view. |
| `wait`     | `name: str`, `enabled`/`visible`/`text`, opt `timeout_ms` | Poll until the named widget matches. Reply `{ok:true}` or `{ok:false}` on timeout. |
| `ping`     | —                                   | Reply `{ok:true}` — Director uses it to confirm app is up.   |

App → Director (reply to `locate`/`nav`/`wait`/`ping`), sent to the datagram's origin port:

```json
{ "ok": true, "cx": 1462, "cy": 388, "x": 1400, "y": 372, "w": 124, "h": 32 }
```

Fire-and-forget for `set_hint` (UDP, no handshake — if a packet drops the next hint corrects it). For
`locate`, the Director retries a couple of times with a short timeout before surfacing an error, so a
missed packet doesn't wedge a scenario.

---

## 5. Widget-naming convention

Clicks are only as reliable as the target names. Convention (formalising the existing informal one):

- `objectName = "<ViewModuleClass>.<role>"`, e.g. `"WizardViewModule.nextButton"`.
- **Per-tab / repeated widgets are further qualified**: `"<ViewModuleClass>.<role>.<discriminator>"`,
  e.g. `"WizardViewModule.measureButton.reference"` and `".sample"` — because both acquisition tabs (and
  therefore both Measure buttons) exist in the tree at once, so a bare name is ambiguous (§3).
- Names are **stable public API for scenarios** — renaming one breaks a screencast script, so treat a
  rename like an API change.
- Added **incrementally**: a scenario declares the widgets it needs; we set `objectName` on exactly
  those. No repo-wide naming sweep.
- Scenarios reference names as plain strings; the spec keeps a small **name registry** table per
  scenario file so the AI (re)generating a script knows the vocabulary.

---

## 6. Director side — reusable framework

New top-level package `automation/` (outside `sciens/`, since it is tooling, not app code):

```
automation/
  automation_director.py     # reusable infra (built once)
  scenarios/
    measurement_bench.py       # (M2) hardware-in-the-loop bench screencast
    pumpkin_wizard.py          # (M1) first scenario (§7), AI-authored, thin
  screenshots/                 # per-scene PNG output (gitignored)
  README.md                    # run recipe + recording setup
```

### 6.1 `automation_director.py`

- **`Prompter(QDialog)`** — non-modal, `Qt.Window | Qt.WindowStaysOnTopHint`, sized for the left
  screen. A large word-wrapped instruction `QLabel` and a big **"CONTINUE"** `QPushButton`. Placed on
  the left monitor via `QScreen` geometry. Emits `continued` when clicked.
- **`Scenario(QThread)`** — runs the scene sequence off the GUI thread (so `sleep`s don't freeze the
  Prompter). Exposes signals `promptChanged(str)` (→ Prompter label) and the human-gate `Event`.
- **`Director`** — the API the scenario code calls. Constructed with the app's UDP endpoint. Methods:

  | method                       | behaviour                                                            |
  |------------------------------|---------------------------------------------------------------------|
  | `set_hint(text)`             | UDP `set_hint` to the app's right panel; small settle delay.         |
  | `prompt(text)`               | Update the Prompter label (no gate) — narrate without pausing.       |
  | `wait_for_human(text)`       | Show `text` on the Prompter, **block** the scenario thread until the operator clicks CONTINUE. |
  | `nav(view)`                  | UDP `nav` → app fires `NavigationSignal`. Jumps to a view whose entry is a `QMenu`/`QAction`. |
  | `click(name, tab=None)`      | raise app → `locate` (opt `tab`) via UDP → `pyautogui.moveTo(..., tween=easeInOutQuad)` → `click()`. Visible glide. |
  | `wait_ready(name, **state)`  | UDP `wait` → block until the named widget is enabled/visible/text-matches. For gated `Next →`. |
  | `type_text(text)`            | `pyautogui.write(text, interval=…)` for form input on video.         |
  | `sleep(seconds)`             | Pacing delay (thread-blocking, GUI stays live).                      |
  | `screenshot(name)`           | Save `screenshots/<name>.png` (PyAutoGUI/`scrot`) for the manual/doc.|
  | `launch_app(extra_args=[])`  | `subprocess.Popen(python spectracsMain.py --doc-mode …)`; `ping` until ready. |
  | `finish()`                   | Final hint, terminate app subprocess, close Prompter.                |

- **Entry point** builds `QApplication`, the `Prompter`, wires it to a `Scenario`, `show()`s the
  Prompter, `start()`s the thread, `app.exec()`. The scenario file supplies only the `run()` body.

### 6.2 Pacing & authenticity (from the thread's "Tips for Recording")
- Liberal `sleep(1..2)` between actions so a viewer can follow.
- `moveTo(duration≈1.0–1.5, tween=easeInOutQuad)` for human-looking motion.
- `type_text(interval≈0.05–0.1)` so typing is legible.

---

## 7. Scenarios — the first sweep and the harness template

Two scenarios anchor M1, with **different jobs**:
- **§7.1 the first video sweep** Edwin wants recorded first: the **dev measurement bench** running
  end-to-end — a **hardware-in-the-loop** clip (real camera + lamp).
- **§7.2 the harness template**: the **pumpkin wizard** — a **virtual, no-hardware** run used to validate
  the Director↔app seam and serve as the copy-paste template for every other chapter.

Build the seam smoke-gate (§10 step 0) and §7.2 first to prove the plumbing with zero hardware, **then**
record §7.1 on the rig. (§7.2 can even be skipped as a *recording* — but it's the cheapest way to know
the harness works before the camera and lamp are in the loop.)

### 7.1 First video sweep (hardware-in-the-loop) — dev measurement bench

`automation/scenarios/measurement_bench.py`. Drives `DevMeasurementBenchViewModule` through
`ACQUISITION (Reference | Sample) → PROCESSING → EVALUATION → [PUBLISHING]`. This is the **hero clip** — the
master's swiss-knife measuring a real sample end-to-end.

**Prerequisites (hard — the bench enforces them, §0):**
- **Real ELP camera plugged direct-to-USB** (not a hub) so `resolveCaptureIndex` finds it; the active
  setup must be a **non-virtual** spectrometer (`isVirtual == False`), else Capture no-ops (`:404,484`).
- A **light source on the slit**, steady, for both reference and sample — capture is a **blocking
  multi-frame loop**; on empty frames it raises a `Capture failed` **`InWindowDialog`** (`:524`).
- **Master session** (`masterUserExakta`) — the bench lives under the master-only Development group.

**New protocol item this forces into M1:** a **`dismiss` command** (or an `objectName` on the
`InWindowDialog` OK button) so an accidental capture-fail modal doesn't wedge the run.

**Verified bench structure:** role tabs **Reference | Sample** (`__roleTabs`, `:257-262`), inner tabs
**Captured image | Spectrum** (`:199-200`), one **"Capture reference/sample"** button whose label flips by
role (`__captureButton`, `:238`), **← Back / Cancel / Next →** (`:161-168`; `Next →` **disabled until both
captures exist**, `:461`), EVALUATION shows **Metrics | Spectrum**, PUBLISHING shows **"Send to LIMS"**.
Reached by nav target **`"DevMeasurementBenchViewModule"`** (verified `NavigationHandlerLogicModule:69`).

```python
def run(d: Director):
    d.launch_app()                                    # --doc-mode; ping until ready (master session)
    d.nav("DevMeasurementBenchViewModule")            # QMenu entry isn't clickable → nav
    d.set_hint("The measurement bench — a real sample, end to end.")

    d.set_hint("Step 1 — Acquire the reference.")
    d.wait_for_human("Place the REFERENCE in the beam, illuminate the slit, then CONTINUE.")
    d.click("DevMeasurementBenchViewModule.captureButton‹add›")   # "Capture reference"
    d.wait_ready("DevMeasurementBenchViewModule.captureButton‹add›", enabled=True)  # capture loop done
    d.screenshot("bench_01_reference")

    d.set_hint("Step 2 — Acquire the sample.")
    d.click("DevMeasurementBenchViewModule.roleTabs‹add›", tab=1)  # switch to the Sample tab (header rect)
    d.wait_for_human("Swap in the SAMPLE, then CONTINUE.")
    d.click("DevMeasurementBenchViewModule.captureButton‹add›")    # "Capture sample"
    d.wait_ready("DevMeasurementBenchViewModule.nextButton‹add›", enabled=True)     # both captured → Next on

    d.set_hint("Computing transmission / absorbance…")
    d.click("DevMeasurementBenchViewModule.nextButton‹add›")       # ACQUISITION → PROCESSING
    d.click("DevMeasurementBenchViewModule.nextButton‹add›")       # PROCESSING → EVALUATION
    d.screenshot("bench_02_evaluation")

    d.set_hint("Publishing to the lab (LIMS).")                    # only if the plugin declares PUBLISHING
    d.click("DevMeasurementBenchViewModule.nextButton‹add›")
    d.click("DevMeasurementBenchViewModule.sendToLimsButton‹add›")
    d.set_hint("Done."); d.finish()
```

`objectName`s to add (`‹add›`): `captureButton`, `roleTabs`, `nextButton`, `backButton`,
`sendToLimsButton` (+ the `InWindowDialog` OK for `dismiss`). Present already: `benchPhaseStack`,
`DevMeasurementBenchViewModule.videoViewModule`. Exact `roleTabs` tab-index→role and capture-loop duration
are confirmed by a click-through of the live bench before wiring.

### 7.2 Harness template (virtual, seam validation) — pumpkin measurement wizard

`automation/scenarios/pumpkin_wizard.py`: a **linear list of semantic scenes** — the only part
regenerated per screencast. It drives the end-user **measurement wizard** (`WizardViewModule`) through the
pumpkin plugin's phase sequence `ACQUISITION (Reference | Sample) → EVALUATION → …`.

**Why the wizard is the seam-validation template (no hardware):**
- Its "Measure" runs the engine's **virtual-device round-trip**
  (`WizardViewModule.py:268-272`, `engine.captureAcquisitionStep`) — **no camera, no lamp, no hardware**.
  The bench, by contrast, hard-rejects virtual devices (§0), so it cannot be the cheap first throw.
- It is already exercised headless by `test_pumpkin_wizard_offscreen.py`, so the capture path is known to
  produce a spectrum under automation.
- It exercises every Director primitive once: `nav`, `set_hint`, `click` (incl. a **tab switch**),
  `wait_ready` (the gated `Next →`), `screenshot`, and a demo `wait_for_human` gate.

Verified wizard structure (`WizardViewModule.py`): reached by nav target **`"WizardViewModule"`** which on
`showEvent` auto-starts a **NEW** run from `CurrentUserSession().getPluginCodeRef()` (so log in as a user
with the **pumpkin plugin configured**); ACQUISITION renders Reference/Sample as **two tabs in a
`QTabWidget`** (`:218-233`), each tab holding a **"Measure"** button + status label + spectrum plot; nav
row is **← Back / Cancel / 🗑 Delete / Next →** (`:79-92`), with `Next →` **disabled until both roles are
measured** (`:248-249`) and relabelled **"Save"** on the terminal step.

Illustrative shape (final wording/steps authored against the live UI at build time):

```python
def run(d: Director):
    d.launch_app()                          # spectracsMain.py --doc-mode; ping until ready
    d.nav("WizardViewModule")               # QMenu entry isn't clickable → nav command
    d.set_hint("Step 1 — Measure the reference.")
    d.prompt("The Director will run the pumpkin-oil measurement. Click CONTINUE to start.")
    d.wait_for_human("Click CONTINUE to begin.")            # demo gate (no hardware step here)

    d.click("WizardViewModule.measureButton.reference")     # engine virtual capture → reference spectrum
    d.screenshot("01_reference_measured")

    d.set_hint("Step 2 — Measure the sample.")
    d.click("WizardViewModule.tabWidget", tab=1)            # switch to the Sample tab (tab-header rect)
    d.click("WizardViewModule.measureButton.sample")        # → sample spectrum
    d.screenshot("02_sample_measured")

    d.set_hint("Computing transmission / absorbance and the pumpkin-oil evaluation…")
    d.wait_ready("WizardViewModule.nextButton", enabled=True)  # Next enables only when both measured
    d.click("WizardViewModule.nextButton")                  # ACQUISITION → EVALUATION
    d.screenshot("03_evaluation")

    d.set_hint("Result ready.")
    d.finish()
```

**Incremental `objectName`s this scenario needs** (per §5). None exist yet on the wizard; to **add** —
only these:

| objectName                                | widget                                                    |
|-------------------------------------------|-----------------------------------------------------------|
| `WizardViewModule.tabWidget`              | the phase `QTabWidget` (`__tabWidget`) — for tab-header locate |
| `WizardViewModule.measureButton.reference`| the Reference tab's "Measure" button (set in `__acquisitionPanel` by role) |
| `WizardViewModule.measureButton.sample`   | the Sample tab's "Measure" button                         |
| `WizardViewModule.nextButton`             | "Next →" / "Save" (`__nextButton`)                        |
| `WizardViewModule.backButton`             | "← Back" (`__backButton`)                                 |

`measureButton` is created **per acquisition panel** (rebuilt on each phase render), so its objectName is
set inside `__acquisitionPanel(step)` from `step.getRole()` — role-qualified so both tabs' buttons are
individually resolvable (§3). The tab **index → role** mapping (is Reference tab 0?) and the exact
EVALUATION landing are confirmed by a click-through of the live wizard (per Edwin's click-through-review
practice) before wiring.

---

## 8. Dependencies & run recipe

- `pip install pyautogui` (pulls `python3-xlib`/`scrot` on Linux — documented in `automation/README.md`;
  not added to the app's runtime requirements, it is dev-only tooling).
- Each scenario launches the app with `--doc-mode` itself; the app's normal `PYTHONPATH`/venv recipe
  applies (see the run-recipe memory).
- **First sweep — `python automation/scenarios/measurement_bench.py`** (§7.1): needs the **master session**
  (`masterUserExakta`), a **real non-virtual spectrometer** plugged **direct-to-USB**, and a **lamp on the
  slit**. Without the real device the bench refuses to capture (§0) — nothing to record.
- Seam template — `python automation/scenarios/pumpkin_wizard.py` (§7.2): **no hardware**; the session must
  be **logged in as a user with the pumpkin plugin configured** (`getPluginCodeRef()` non-empty), else the
  wizard shows *"No plugin configured for this user."*
- **Recording (manual, M1):** OBS Studio, wide canvas (e.g. 3840×1080), left monitor → left half
  (Prompter), right monitor → right half (app + hint panel). Operator starts/stops OBS by hand.

---

## 9. Out of scope / deferred (M2+)

- **Video-recorder orchestration** — Director launching/stopping `ffmpeg`/OBS automatically. M1 keeps
  recording manual.
- **Wayland / Android** — needs `ydotool` (Wayland) or an on-device path; not now.
- **Dogtail / AT-SPI fallback** — only if a target lands outside the Qt widget tree (native OS dialog).
- **Connection / calibration scenario** — the spectrometer setup flow with the real **USB
  unplug/replug** human step (`connect` / `reconnect` buttons); re-enumerates the device mid-run.
- **Additional scenarios** — error-handling, user calibration. Each is a new thin file in `scenarios/`
  reusing the framework, plus its incremental `objectName`s.
- **Scenario picker** — a dropdown in the Prompter to choose among workflows (thread's closing idea).

---

## 10. Milestones

Build order (de-risks the seam with zero hardware, *then* records the hero clip on the rig). **Status:
P0–P6 IMPLEMENTED 2026-07-12** — the harness runs end-to-end on the virtual path; the bench sweep awaits
the rig for its live recording.

| Ph | Goal | HW | Delivered | Status |
|----|------|----|-----------|--------|
| P0 | doc-mode hint panel | no | `--doc-mode` flag; `DocHintPanelViewModule`; gated grid col 1 | ✅ |
| P1 | UDP protocol | no | `DocModeUdpService` :5555 — set_hint/locate(+tab)/nav/wait/ping/dismiss | ✅ (round-trip tested) |
| P2 | Director framework | no | `automation/automation_director.py` — API + Prompter + Scenario(QThread) | ✅ |
| P3 | ★ seam proven | no | `scenarios/_smoke.py` (status-bar `logoBox` locate ✓) | ✅ |
| P4 | virtual validation | no | `scenarios/pumpkin_wizard.py` + 5 wizard objectNames (resolve ✓) | ✅ |
| P5 | ★ bench first sweep | **yes** | `scenarios/measurement_bench.py` (8-beat) + `dismiss` + bench objectNames | ✅ code; live recording pending rig |
| P6 | reproducible + shot | — | `automation/README.md`; `screenshots/.gitignore`; this table | ✅ |

- **M1:** P0–P6 + per-scene screenshots. OBS manual. Deliverable = the **bench run-through video**.
- **M2 (deferred):** the Tier A virtual chapters (§13) edited into the full feature tour, connection/
  calibration (real USB unplug/replug), recorder orchestration, scenario picker, Dogtail fallback,
  Wayland/Android.

**Verified at implementation (offscreen, UDP-only — no mouse):** `logoBox`, the wizard `tabWidget` /
`measureButton.reference` / `nextButton` / `backButton` / tab-header rect all resolve to live global
coordinates; `nav`/`wait`/`locate(tab)`/`dismiss` all round-trip. `measureButton.sample` and the bench
names resolve only once their tab/view is shown (Qt hides non-current-tab widgets), which the scenarios do
by switching tabs first; full bench-name + live-cursor validation happens at the rig recording.

---

## 11. Risk / regression notes

- The app is **untouched without the flag** — panel, service, and column are all gated on `docMode`.
  The only always-on change is adding `objectName`s (inert; they don't affect behaviour).
- UDP is localhost-only and best-effort; a lost packet degrades to a stale hint or a retried
  `locate`/`nav`/`wait`, never a crash. Port-bind failure is logged and non-fatal.
- **Gated transitions** (`Next →`) must be driven with `wait_ready`, never a blind `sleep`+`click` — a
  click on a disabled button silently no-ops and dead-locks the scenario (the failure mode the review
  caught on both bench and wizard). Every `wait` carries a timeout so a stuck run surfaces an error.
- **Window stacking**: the Director raises/activates the app before each click (§3); the Prompter is
  pinned to the **left monitor** so it never overlaps the click target on a single-monitor dev box.
- **Modal dialogs** the harness can't see block it. The §7.2 wizard has no capture-failed modal; the
  §7.1 **bench first sweep does** (`InWindowDialog` on empty frames) — hence the `dismiss` command is in
  **M1** scope (§7.1), not deferred.
- PyAutoGUI's failsafe (cursor to a screen corner aborts) stays **enabled** so a runaway scenario can be
  stopped by hand — documented in the README.

---

## 12. Feature-showcase tour (requirement: render *all* primary features)

The end goal is not one clip — it is a video that **showcases every primary feature of the app**. The
harness supports this directly: a showcase is just a **playlist of scenarios**, each a "chapter" driven by
the same Director primitives, with the hint panel + Prompter narrating the chapter title. The Director
gains one thin helper, `run_chapters([...])`, that runs scenario `run()` functions back-to-back against a
single app launch (or relaunches per chapter for a clean state).

**Primary features → chapters** (derived from the app's navigation targets and the feature specs). Marked
**[virtual]** = no hardware, **[HW]** = needs the real camera/lamp rig:

| # | Chapter                          | View(s) driven                         | HW? |
|---|----------------------------------|----------------------------------------|-----|
| 1 | Login / register                 | `LoginViewModule` / `RegistrationViewModule` | virtual |
| 2 | Spectrometer setup + connect     | `SpectrometerSetupListViewModule` → `SpectrometerSetupViewModule` | virtual (tour of UI); connect step **[HW]** |
| 3 | Calibration (ROI + wavelength)   | calibration wizard in the setup editor | **[HW]** (live frame) |
| 4 | **Measurement wizard** (pumpkin) | `WizardViewModule` — the §7 M1 chapter | **[virtual]** |
| 5 | Evaluation result                | wizard EVALUATION phase (metrics + spectrum) | [virtual] |
| 6 | PDF report                       | wizard Report step (`SPEC_bench_pdf_export`) | [virtual] |
| 7 | Publish to LIMS                  | wizard PUBLISHING step → SENAITE (`SPEC_lims_integration`) | [virtual]* |
| 8 | Saved runs                       | workflow persistence list/detail (`SPEC_workflow_persistence`) | [virtual] |
| 9 | Account / payment                | `AppUserSettingsViewModule` + PayPal tab (`SPEC_paypal_payment`) | [virtual] |
| 10| Master: plugins / users          | `PluginListViewModule`, `UserListViewModule` | [virtual] |
| 11| **Master: dev measurement bench**| `DevMeasurementBenchViewModule` — **the §7.1 first sweep** | **[HW]** |

\*needs the local SENAITE Docker up (`SPEC_lims_integration`).

**Recording order (Edwin's call): the bench first sweep leads.** Chapter 11 (the bench, §7.1) is the
**first clip recorded** — the hero shot of the master measuring a real sample end-to-end — even though it
is a Tier B hardware clip. The Tier A virtual chapters follow and are edited around it.

**Two tiers (by hardware need, not by recording order):**
- **Tier A — virtual (no rig):** chapters 1, 4, 5, 6, 7, 8, 9, 10 (+ the *UI* of 2). Recordable with no
  hardware; §13 enumerates their stubs. These build on the §7.2 wizard template.
- **Tier B — hardware (the rig):** the **bench (11, §7.1 — recorded first)**, plus connect/calibrate
  (2b, 3). Real camera + lamp + `wait_for_human` cuvette/USB steps.

Each chapter is a thin `scenarios/<name>.py` reusing the framework; its incremental `objectName`s are
added when that chapter is built (per §5). Build order: seam smoke-gate → §7.2 wizard template (proves the
plumbing, no HW) → **§7.1 bench first sweep (recorded)** → the rest of Tier A.

---

## 13. Tier A scenario stubs (per-chapter skeletons)

Six scenario files cover Tier A (chapters 4–7 collapse into the single wizard run). Each stub below is the
**skeleton only** — nav/launch + narration + the click sequence. Widget `objectName`s marked `‹add›` do
**not exist yet**; they are added (per §5) and the exact labels/flow confirmed by a **click-through of the
live view** when that chapter is built. Nav targets and the buttons marked ✓ are **verified** against the
current code.

Grounding used by these stubs (verified): `HomeViewModule` is stack index 0 and holds the **saved-runs
workflows table** + buttons **"New measurement"** ✓ (→ `WizardViewModule` when a plugin is configured,
`HomeViewModule.py:33`), **"Edit"** ✓, **"Delete"** ✓. Account/settings is `AppUserSettingsViewModule`
(nav target, PayPal tab per `SPEC_paypal_payment`). Nav targets `LoginViewModule` /
`RegistrationViewModule` / `SpectrometerSetupListViewModule` / `SpectrometerSetupViewModule` /
`PluginListViewModule` / `UserListViewModule` all exist (`NavigationHandlerLogicModule`).

**`scenarios/_tour.py` — the playlist** (chapter 3-part of the requirement)
```python
CHAPTERS = [login, spectrometer_setup_tour, pumpkin_wizard,
            saved_runs, account_payment, master_admin]   # Tier A order
def run(d):
    for chapter in CHAPTERS:
        d.set_hint("— %s —" % chapter.TITLE)
        chapter.run(d)                 # each chapter leaves the app on Home for the next
```

**Ch 1 — `login.py`**
```python
TITLE = "Signing in"
def run(d):
    d.nav("LoginViewModule")
    d.set_hint("Sign in to Spectracs.")
    d.click("LoginViewModule.usernameField‹add›"); d.type_text("edwin")
    d.click("LoginViewModule.passwordField‹add›"); d.type_text("•••••")
    d.click("LoginViewModule.loginButton‹add›")
    d.wait_ready("HomeViewModule.newMeasurementButton‹add›", visible=True)
    d.screenshot("ch1_home")
```

**Ch 2 — `spectrometer_setup_tour.py`** (UI walk only; the **connect** step is Tier B / HW)
```python
TITLE = "Instrument setup"
def run(d):
    d.nav("SpectrometerSetupListViewModule")
    d.set_hint("Your spectrometer setups live here.")
    d.click("SpectrometerSetupListViewModule.openFirstRow‹add›")   # or nav SpectrometerSetupViewModule
    d.set_hint("Each setup binds a device, ROI and wavelength calibration.")
    d.screenshot("ch2_setup")            # NOTE: do NOT drive the live 'Connect' here — Tier B
    d.nav("Home")
```

**Ch 4–7 — `pumpkin_wizard.py`** (the §7 chapter, extended through the tail phases)
```python
TITLE = "Measuring a sample"
def run(d):
    d.nav("Home"); d.click("HomeViewModule.newMeasurementButton‹add›")   # ✓ launches the wizard
    # ... §7 body: measure reference → Sample tab → measure sample → wait_ready(next) → Next ...
    d.set_hint("Evaluation — transmission, absorbance, pumpkin-oil metric.")
    d.screenshot("ch5_evaluation")
    d.click("WizardViewModule.nextButton")        # → Report step (PDF)   [ch 6]
    d.set_hint("A one-click PDF report of the whole run.")
    d.screenshot("ch6_report")
    d.click("WizardViewModule.nextButton")        # → Publishing (LIMS)   [ch 7]
    d.set_hint("Publishing the sample to the lab (SENAITE).")
    d.click("WizardViewModule.sendToLimsButton‹add›")   # needs SENAITE Docker up
    d.click("WizardViewModule.nextButton")        # "Save" (terminal) → back to Home
```

**Ch 8 — `saved_runs.py`** (Home *is* the list)
```python
TITLE = "Past measurements"
def run(d):
    d.nav("Home")
    d.set_hint("Every measurement is saved. Select one and open it.")
    d.click("HomeViewModule.workflowsTable‹add›", )      # select first row (locate row rect)
    d.click("HomeViewModule.editButton‹add›")            # ✓ opens the wizard in VIEW mode
    d.set_hint("The full run reopens read-only — spectra, metrics, report.")
    d.screenshot("ch8_saved_run")
    d.nav("Home")
```

**Ch 9 — `account_payment.py`**
```python
TITLE = "Account & subscription"
def run(d):
    d.nav("AppUserSettingsViewModule")
    d.set_hint("Manage your account and subscription.")
    d.click("AppUserSettingsViewModule.paypalTab‹add›")
    d.set_hint("Upgrade is a single PayPal checkout.")
    d.screenshot("ch9_account")
    d.nav("Home")
```

**Ch 10 — `master_admin.py`** (master session only)
```python
TITLE = "Administration"
def run(d):
    d.nav("PluginListViewModule")
    d.set_hint("Masters manage the analysis plugins distributed to users.")
    d.screenshot("ch10_plugins")
    d.nav("UserListViewModule")
    d.set_hint("…and the user accounts and their roles.")
    d.screenshot("ch10_users")
    d.nav("Home")
```

Build them in playlist order; each reuses the framework and adds only its `‹add›` names. `pumpkin_wizard`
(§7) is built first as the template — the others are variations on the same nav→hint→click→screenshot
rhythm.

---

## 14. As-built (2026-07-12) — what the implementation added beyond the design

All of P0–P6 landed and were **driven live on Edwin's machine**: the smoke gate, the virtual wizard
(end-to-end, real computed absorption curve), and the **bench on the real device** (all 8 beats,
reference spectrum captured off the real camera, recorded to mp4). Additions/changes discovered while
making live driving reliable:

- **`activate` UDP command + glide-then-activate clicks.** Pixel-precise `pyautogui.click()` alone was
  unreliable (focus, exact landing). The Director now **glides the visible cursor to the widget** (for the
  video) and then triggers it **programmatically** over UDP: `activate {name, tab?}` →
  `findChild` → `animateClick()` (buttons) / `setCurrentIndex()` (tabs). Reliable *and* visible.
- **Window raise = `xdotool search --name "^Spectracs" windowactivate`**, not `wmctrl -a Spectracs`
  (substring-matched the terminal, whose title carries the repo path `…/spectracs/…`).
- **Prompter on the non-app screen**; the app runs on the **right** monitor here, which is **non-primary**
  (primary = left `0,0`) — do not assume app = primary.
- **Attach mode (`DOC_ATTACH=1`)** — drive an app the operator already launched + logged in; required for
  the bench (rejects virtual, needs a real calibrated master session the harness can't synthesize).
- **Bypass virtual images (`SPECTRACS_DEV_VIRTUAL_CAPTURES`)** — the no-hardware wizard needs the
  reference/sample/calibration PNGs preloaded (`spectracsMain._loadDevVirtualCapturesIfEnabled`, pointing
  at `spectracs-references/pumpkin_oil/virtual_captures/pumpkinoil_perfect_v1`).
- **Screen recording (`DOC_RECORD=1`)** — the M2 "recorder orchestration", done: the Director runs
  **ffmpeg x11grab** for the whole run → `automation/recordings/<name>_<ts>.mp4`, grabbing the **app
  window's own rectangle** (`xdotool getwindowgeometry`, largest `^Spectracs` window, even dims) so the
  clip is app-only. `DOC_RECORD_FULL=1` grabs the whole desktop. **Videos are gitignored — never
  committed/versioned.**
- **Launchers:** `automation/run.sh <scenario> [bypass|attach|record]`, `automation/wizard.sh`
  (= wizard + bypass), `automation/bench.sh` (one command: launch app → attach → record; login is a human
  `wait_for_human` gate).
- **App-side changes** (all gated): `--doc-mode` flag; `DocHintPanelViewModule`; `DocModeUdpService`
  (set_hint/locate/nav/wait/activate/dismiss/ping); `objectName`s on the wizard (tabWidget /
  measureButton.<role> / next / back) and bench (captureButton / roleTabs / innerTabs / next / back /
  sendToLimsButton) + `InWindowDialog.primaryButton`.

---

## 15. Open issues — to specify later

Captured for a later spec pass (video capture essentially works; these are refinements/robustness):

1. **Login automation.** A fresh app starts logged-out; the bench needs a real master login. Today it's a
   `wait_for_human` gate. Option: a scripted **login chapter** (drive the login form) — needs stored/prompted
   credentials and login-screen `objectName`s.
2. **Bench calibration prerequisite.** The bench requires a **registered serial** (from the login result)
   whose server instrument has saved calibration coefficients. Just logging in / having a calibration isn't
   enough without the serial. Specify the operator setup path (or a dev seed) so the bench is reproducible.
3. **Recording starts at attach**, so the clip's head includes the login/prep. Specify starting the
   recording **after** the prep gate (scenario-controlled `start_recording`) for tight clips, + auto-trim.
4. **Measurement quality in the video** depends on a real lamp + sample (a test read empty/saturated →
   "—" metrics). Not a harness issue; note capture-quality guidance for recordings.
5. **Multi-run hygiene** — stale `--doc-mode` apps / port :5555 conflicts are handled by `pkill` in the
   launchers; specify a cleaner single-instance guard.
6. **Tier A chapters** (login, spectrometer-setup tour, saved_runs, account_payment, master_admin — §13)
   are stubs; build + string into the `_tour` playlist for the full feature video.
7. **Unattended / CI** — the no-hardware runs (smoke, wizard) can run headless under `xvfb` as a CI check;
   the bench can't (physical beats). Specify the CI job.
8. **Stale test assertion** — `tests/test_pumpkin_wizard_offscreen.py` expects `"Next ▶"` but the button
   is `"Next →"` (pre-existing; unrelated to this work). Fix or update.
9. **Wayland / Android** — still out of scope (needs `ydotool` / on-device path).

---

## 16. M3 — the narrated feature tour (refinements)

Status: **IMPLEMENTED (bench, 2026-07-14).** B0–B5 shipped and were driven live on the rig — the narrated
bench screencast records end-to-end (login → capture → every phase's steps → LIMS publish), rig-verified.
As-built deltas and the rig-driven fixes are in §16.15. The generic `describe`/`walk_workflow` and the other
chapters remain deferred (§17). Original design below.

Status (design, superseded by §16.15): **DESIGN (2026-07-13).** Requested by Edwin after the M1/M2 harness ran well on his machine; nothing
is built until an explicit "go". This pass turns the harness from hand-authored click-lists into a
**structure-driven, Claude-narrated tour**: a format-aware doc panel, reading-paced progressive text,
keyboard-only advancing, scripted login from an unversioned config, and artifacts written outside the code
repo. Load-bearing facts below were verified against the code (rubber-duck pass, 2026-07-13).

### 16.0 Scope & sequencing — bench-first (2026-07-13)

**The one near-term deliverable is a narrated screencast of the dev measurement BENCH**
(`DevMeasurementBenchViewModule`). The pumpkin-wizard chapter, saved-runs, account/payment, master-admin and
the `_tour` playlist are **postponed**.

> **Post-convergence update (2026-07-13).** The capture-panel convergence named below as this milestone's
> predecessor is now **DONE** (SPEC_plugin_driven_convergence §9, M3 — rig-verified). Four consequences:
> 1. **B5/B6 unblocked.** ACQUISITION on the bench now runs through the shared `CapturePanel`, so the
>    screencast is authored against a stable, converged UI — the rework risk this section warned about is gone.
> 2. **The capture objectNames MOVED.** The bench no longer owns `captureButton` / `roleTabs` / `innerTabs` —
>    they now live on the shared panel as `CapturePanel.captureButton` / `.roleTabs` / `.innerTabs` /
>    `.videoViewModule`, already set during the convergence. The §7.1 scenario must **retarget** to those
>    (`DevMeasurementBenchViewModule.*` → `CapturePanel.*`). Convergence dividend: almost no new objectNames
>    to add for B5, and the same names will later drive the wizard's real-capture path.
> 3. **Both narration layers coexist (Edwin, 2026-07-13).** The bench now shows its **own** in-app coach line
>    (status bar, from the plugin `CaptureView.prompt`) plus amber ●/▶ cues during ACQUISITION. The doc panel
>    (§16.4) is a *second* layer. Decision: **show both** — no suppression. They occupy disjoint zones
>    (status bar vs right column) and self-sync (the Director drives the same role/capture events the guidance
>    reacts to). The one obligation this creates: the narration table (§16.2, B5) must be authored in a
>    **different register** from the plugin prompt — the coach line is the terse imperative ("Capture
>    reference"), the doc caption is the narrated *why* ("the reference is our 100% baseline") — so the frame
>    never shows the same sentence twice.
> 4. **`getWorkflow()` correction.** A public `getWorkflow()` **already exists on the engine** (both hosts call
>    `self.__engine.getWorkflow()`); only a *view-level* accessor + current-view resolution in the UDP service
>    are missing. The deferred generic walker is therefore a lighter lift than the notes below imply. See §17.

A final rubber-duck pass (2026-07-13, verified against code) fixed the build shape for this scope:

- **The generic `describe` / `walk_workflow` (16.1–16.3) is DEFERRED, not built now.** Two reasons: (a) it needs
  new app plumbing that does **not** exist — no view exposes a public `getWorkflow()` (the bench keeps a private
  name-mangled `__workflow`; the wizard's is a private `__workflow()` method), and the UDP service holds only
  the root container, never resolving `currentWidget()`; (b) the bench acquisition is **structurally unlike**
  the wizard — a **single** `captureButton` whose label flips by role **plus** a `roleTabs` tab-switch, **not**
  one Measure button per step — so the wizard-shaped loop `click("measureButton.<role>")` has no target on the
  bench. With only one workflow in scope, the generic abstraction is speculative generality; it pays off at the
  2nd plugin (the wizard), which is postponed.
- **The bench screencast is HAND-AUTHORED**, extending the existing `automation/scenarios/measurement_bench.py`
  (8-beat) with a narration table + the refinements below — not rewritten as a walker.
- **The refinements (16.4–16.9) are orthogonal to generic-vs-hand-authored and are built regardless**: the
  3-zone panel, progressive reveal, reading-time pacing, `Ctrl+Shift+ß` hotkey, `director.ini` login, artifacts
  relocation. A hand-authored bench scenario consumes them directly.
- **Sequencing — the capture-panel convergence (roadmap Frontier #1) is the natural predecessor.** It routes
  ACQUISITION through the shared capture path and **dedupes the guidance logic mirrored across the bench AND the
  wizard**, i.e. it reshapes the bench's acquisition UI too. *Verified 2026-07-13:* `SPEC_plugin_driven_convergence.md`
  scopes the bench in explicitly (P7 = "both delegate ALL phase content to WorkflowPhaseRenderer"); the bench's
  `__buildAcquisitionPanel` (DevMeasurementBenchViewModule.py:183-274) is still bespoke (bypasses the shared
  renderer); and the ~98-line mirrored guidance block lives at `DevMeasurementBenchViewModule.py:604-702`
  (near-verbatim of `WizardViewModule.py:294-403`), whose collapse is "the main prize of P6". Recording the
  bench screencast *before* the
  convergence means authoring against a capture UI about to change (rework risk); doing the convergence *first*
  stabilizes one shared capture panel **and** is exactly what makes the deferred generic `walk_workflow` viable
  (a uniform step→button mapping across both hosts). The UI-independent refinements (B0–B4, §16.13) are safe to
  build either way; only the bench scenario + recording (B5–B6) should follow the converged UI.

The narration table (16.2) is still keyed by phase/step/role so it transfers unchanged when the generic walker
is un-deferred.

### 16.1 Principle — structure is introspected, words are authored

The M1 scenarios hard-code every click. The new asks (use-case heading → phase sub-headings → step walk →
metric descriptions) are all "**walk the live workflow**", which the app already declares
(plugin → phases → steps → view-models). So the two concerns are split:

- **STRUCTURE (what to click, in what order, which metrics exist) is read from the running app** via a new
  `describe` command — generic, always in sync with whatever the plugin declares.
- **WORDS (headings, step captions, metric prose) are authored by Claude** in a per-scenario **narration
  table**, because good screencast narration is an editorial judgement, not a data dump. The metric
  `tooltip` is the **fallback** when the table omits an entry.

This is the hybrid Edwin asked for ("tend to generic … but texts should come from Claude"). A new plugin
needs only a new (small) narration table; the generic driver is untouched.

> **Deferred (see 16.0).** The reply shape below is the *target* for when the generic walker lands — it is
> **not reachable today**. `MainViewModule` is a `QStackedWidget` so `currentWidget()` resolves the current
> page, and while the *engine* exposes a public `getWorkflow()` (both hosts call it), no *view* re-exposes it
> (bench caches a private `__workflow`; wizard wraps a private `__workflow()`), and the UDP service does not
> resolve the current view. The missing plumbing is a view-level accessor + current-view resolution, added when
> this is un-deferred.

`describe` reply — the app would walk the current view's live workflow:

```json
{ "ok": true,
  "useCase": "Pumpkin-oil measurement",
  "phases": [ { "key": "ACQUISITION", "label": "Acquisition",
                "steps": [ {"role":"REFERENCE","label":"Reference"},
                           {"role":"SAMPLE","label":"Sample"} ] },
              { "key": "EVALUATION", "label": "Evaluation", "steps": [] } ],
  "evaluation": [ { "label":"Greenness index",
                    "description":"D_Q ÷ A_green — headline quality index; higher = greener/fresher oil." } ] }
```

`evaluation[].description` = the `MetricFieldView.tooltip`, which is **already populated** in the plugins
(verified) — so "describe each metric field" needs **no new content authored into the app**.

### 16.2 The narration table (Claude-authored, per scenario)

A scenario supplies a dict keyed by structural id; the generic walker looks up each id, falling back to the
introspected label/tooltip when a key is missing:

```python
NARRATION = {
  "useCase":                 "Measuring pumpkin-seed oil",
  "phase:ACQUISITION":       "First we capture two spectra — a reference, then the sample.",
  "step:REFERENCE":          "The reference: the lamp through a blank. Our 100 % baseline.",
  "step:SAMPLE":             "Now the sample. The Director measures it on the virtual device.",
  "phase:EVALUATION":        "The plugin turns the two spectra into quality metrics.",
  "metric:Greenness index":  "Greenness — the headline number. Higher means fresher, greener oil.",
}
```

Keys: `useCase`, `phase:<KEY>`, `step:<ROLE>`, `metric:<label>`. This table is the **only** thing regenerated
per plugin.

### 16.3 The generic walker

```python
def walk_workflow(d, narration):
    wf = d.describe()                                     # UDP describe
    d.doc(use_case=narration.get("useCase", wf["useCase"]))
    d.doc(outline=[p["label"] for p in wf["phases"]])
    for phase in wf["phases"]:
        d.doc(phase=phase["key"])                         # highlight in outline; mark prior done
        d.narrate(text_for("phase", phase, narration))
        if phase["key"] == "ACQUISITION":
            for step in phase["steps"]:
                d.narrate(text_for("step", step, narration))
                d.click("WizardViewModule.measureButton.%s" % step["role"].lower())
            d.wait_ready("WizardViewModule.nextButton", enabled=True)
        d.click("WizardViewModule.nextButton")
    for metric in wf["evaluation"]:                       # inside the EVALUATION phase
        d.narrate(text_for("metric", metric, narration))
        # optional: d.highlight(<metric field>)  — see 16.6
```

Click targets still come from the §5 objectName convention; introspection supplies the **sequence**, not the
widget names.

### 16.4 The doc panel — three zones + progressive reveal (asks 3, 4, 5, 7, 8)

`DocHintPanelViewModule` replaces its single label with three stacked zones mapping to the heading hierarchy:

```
┌ DOCUMENTATION ─────────────┐
│ Bench                      │ ← 1. use-case  (H1, persistent)      ask #4
│ ────────────────────────── │
│ ▸ Acquisition              │ ← 2. phase outline: current = bold/  ask #5
│   Processing               │      accent, done = ✓, upcoming = dim
│   Evaluation               │
│   Publishing               │
│ ────────────────────────── │
│ Capture the reference —    │ ← 3. caption: current step, or       asks #6/#7
│ shine the lamp on the      │      (in EVALUATION) each metric's
│ slit, then Capture.        │      authored description
└────────────────────────────┘
```

Protocol: a structured `doc` command, each field updating only its zone (keep `set_hint` as a caption-only
alias): `doc { use_case?, outline?:[labels], phase?:key, caption?, reveal?, wpm? }`.

**Progressive reveal (Edwin's "sentence and/or word by word"):** the caption zone renders **app-side** with a
`QTimer` typewriter — **sentence-by-sentence**, dropping to **word-by-word when a sentence exceeds ~12 words**
— at `DOC_WPM` cadence. Keeping the reveal inside the panel (not as a UDP stream) keeps the wire light and the
animation smooth. The Director's dwell after `narrate()` = `reveal_time + tail_pause`, both derived from the
same `DOC_WPM`, so the two stay in lock-step.

### 16.5 Reading-time pacing (ask 8)

`narrate(text)` = `doc(caption=text, reveal="auto")` then hold `max(MIN_DWELL, words / DOC_WPM * 60) * DOC_SPEED`.
Knobs (from `director.ini [default]` or env): **`DOC_WPM`** (default 180 — deliberately slower than silent
reading, tuned for YouTube legibility), **`DOC_SPEED`** global multiplier, **`MIN_DWELL`** floor. Long metric
prose lingers; short captions don't overstay. Cursor glide `duration` also scales with `DOC_SPEED`.

### 16.6 (optional) In-app metric highlight

To make "describe each metric field" *visual*, an optional `highlight {name}` command flashes the metric's
widget (transient stylesheet border) while its caption is on screen. Requires key-qualified objectNames on the
metric rows (add in `QtWorkflowRenderer.visitMetricField`, e.g. `metricField.<label-slug>`, per §5). Deferrable
— narration reads fine without it; include only if the panel-only cut looks flat.

### 16.7 Keyboard-advance Prompter (ask 2)

Advance gates by keyboard, never the mouse — the left-monitor Prompter and its focus changes are invisible to
the app-window recording (`__app_window_region` grabs only the app rect, verified).

- **Primary: a global hotkey `Ctrl+Shift+ß`** (Edwin's pick) via `pynput.keyboard.GlobalHotKeys` (X11, no root)
  — works regardless of focus; its callback sets the existing `threading.Event` gate. `pynput` is a dev-only
  dep alongside `pyautogui`.
- **Fallback (no new dep):** a `QShortcut` (Space / Enter) on the Prompter, which `raise_()+activateWindow()`s
  at each gate; used if `pynput` is absent.
- PyAutoGUI corner **FAILSAFE stays on**. The exact `ß` keysym under X11+pynput is confirmed at build; the
  chord is config-overridable.

### 16.8 Scripted login + config (ask 1)

- New **sibling `/home/nidwe72/development/spectracs/spectracsPy-config/director.ini`** — **unversioned,
  outside every repo** — parsed with stdlib `configparser` (no dep). **Per-scenario `[sections]`** (Edwin's
  "prefixed section … script as prefix"):

  ```ini
  [default]
  wpm = 180
  [bench]
  username = masterUserExakta
  password = ••••••
  [wizard]
  username = edwin
  password = ••••••
  ```

- A **`login(scenario)`** chapter drives the **visible** form (nav `LoginViewModule` → type `[scenario]`
  username → type password → click Login → `wait_ready` Home/Wizard), so login appears *on* the tour and
  replaces the manual gate for virtual runs. The **bench** reads `[bench]` = **masterUserExakta**; it still
  keeps its human "calibrated master + registered serial" gate (hardware/enrolment reality, §15.2).
- **Bench pairing (attach-mode).** The bench's `showEvent` auto-starts a run and **bounces to Settings** if no
  calibrated serial is active, so scripted login is paired with the existing **attach-mode** (drive an
  already-prepared master session) rather than a fresh `launch_app`: the *login click* is scripted; the
  calibrated-setup prep is arranged before nav-in.
- **New objectNames** (§5): `LoginViewModule.usernameField`, `.passwordField`, `.loginButton`. Server must be
  up (`SpectracsPyServerClient().login`).

### 16.9 Artifacts outside the code repo (ask 10)

- Run output → **`/home/nidwe72/development/spectracs/spectracs-references/director/{recordings,screenshots}`**.
  `spectracs-references/` is **not a git repo** (verified), so heavy mp4s never touch version control. This
  **supersedes** the earlier `spectracs-docs/director` location for raw run output.
- `SHOTS_DIR` / `RECORDINGS_DIR` default there, overridable via `DOC_ARTIFACTS_DIR`.
- Director **code** stays in `spectracsPy/automation/` (tooling; nothing app-side imports it — verified).

### 16.10 More use-cases / the tour (ask 9)

`_tour` playlist via the existing `main_chapters`: **`login → [walk_workflow per plugin] → non-workflow
chapters`**. Non-workflow chapters stay short hand-authored files reusing the panel primitives:

- **saved runs** — Home list → open one read-only.
- **account / payment** — nav `AppUserSettingsViewModule` → PayPal tab → narrate the €1 checkout.
- **master admin** — `PluginListViewModule` / `UserListViewModule`.

### 16.11 Protocol delta (adds to §4)

| cmd | fields | effect |
|-----|--------|--------|
| `describe` | — | reply `{useCase, phases[], evaluation[]}` from the current view's workflow |
| `doc` | `use_case? / outline? / phase? / caption? / reveal? / wpm?` | update the 3-zone panel; `caption` animates (reveal) |
| `highlight` (opt) | `name` | transient flash of a metric widget |

`set_hint` stays as a `doc(caption=…)` alias (back-compat with M1 scenarios).

### 16.12 Incremental objectNames this milestone adds

`LoginViewModule.usernameField / .passwordField / .loginButton`; (optional) `metricField.<slug>` in
`QtWorkflowRenderer.visitMetricField`. Everything else reuses the M1 names.

### 16.13 Build order — bench-first (when Edwin says go)

B0–B4 are independent / parallelizable; **B5 depends on B0–B4**; **B6 depends on B5 + the rig**. If the
capture-panel convergence is done first (§16.0), B5–B6 follow the converged capture UI.

| Ph | Deliverable | Side | HW |
|----|-------------|------|----|
| B0 | 3-zone doc panel (use-case / phase-outline / caption) + `doc` cmd w/ progressive reveal; `set_hint` = caption alias | app | no |
| B1 | Director `doc()` / `narrate()` + reading-time dwell; `DOC_WPM` / `DOC_SPEED` / `MIN_DWELL` | director | no |
| B2 | `Ctrl+Shift+ß` global hotkey (pynput) → continue gate; Space-on-Prompter fallback; FAILSAFE kept | director | no |
| B3 | `director.ini` loader (`[bench]` = masterUserExakta) + scripted-login chapter; **+3** objectNames (`LoginViewModule.usernameField/.passwordField/.loginButton`) | app + director | no |
| B4 | Artifacts → `spectracs-references/director/{recordings,screenshots}`; `DOC_ARTIFACTS_DIR` override | director | no |
| B5 | **Bench narrated scenario** — extend `measurement_bench.py`: narration table (`useCase` / `phase:*` / `step:REFERENCE\|SAMPLE` / `metric:*` incl. `color`); hand-authored clicks (roleTabs ↔ single `captureButton`, **reference-then-sample**, `wait_ready` Next, `dismiss` on capture-fail, screenshot **before** the terminal click); **attach-mode**, hardware beats as `wait_for_human` | scenario | no (to author) |
| B6 | **Live rig recording** → the deliverable mp4 (prepared calibrated master + real ELP + lamp; human-gated captures) | rig | **yes** |
| — | *Deferred (un-defer with the wizard):* `describe` cmd + `getWorkflow()` plumbing + current-view resolution, generic `walk_workflow`, pumpkin / saved-runs / payment / master chapters, `_tour` playlist | — | — |

### 16.14 Open confirmations (tune against the first cut)

- Progressive-reveal threshold (word-wise beyond a ~12-word sentence) and `DOC_WPM` default (180) are starting
  points, tuned once the first clip is watched.
- The in-app metric highlight (16.6) is optional — decide after seeing the panel-only version.

### 16.15 As-built (2026-07-14) — what shipped for the bench, and the rig-driven fixes

**B0–B5 delivered** (all app-side changes gated on `--doc-mode`; Director is dev-only tooling):
- **B0** `DocHintPanelViewModule` = 3 zones (use-case H1 / phase-outline with ✓/▸/dim / caption) + progressive
  reveal (`QTimer`, sentence-by-sentence, word-wise past ~12 words). New `doc` UDP command; `set_hint` = caption
  alias.
- **B1** Director `doc()` / `narrate()` + reading-time dwell (`DOC_WPM` 180 / `DOC_SPEED` / `DOC_MIN_DWELL`);
  cursor glide scales with `DOC_SPEED`.
- **B2** global advance hotkey via pynput — registers `<ctrl>+<shift>+ß` **plus reliable alternates
  `<ctrl>+ß` and `<f9>`** (Shift+ß emits a different keysym on a German layout, so the original chord alone
  often never fires). Space/Enter on the Prompter is the no-dep fallback; the Prompter raises + focuses at each
  gate so keyboard advance is reliable.
- **B3** `director.ini` loader in the unversioned sibling `spectracsPy-config/`; scripted `login(scenario)`
  (human-gate fallback when a password is blank); Login objectNames.
- **B4** artifacts → `spectracs-references/director/{recordings,screenshots}` (`DOC_ARTIFACTS_DIR` override).
- **B5** the bench scenario walks the WHOLE workflow: acquisition step-tabs (Reference/Sample) with human
  capture beats, then **every step-tab of PROCESSING (rasters, Spectra, Transmission, Absorption) and
  EVALUATION (Metrics + each metric field, Spectrum, Report) and PUBLISHING** — each clicked and described.

**Rig-driven fixes (2026-07-14), all found by driving it live:**
- **Text-field activation.** `activate` only clicked buttons / switched tabs; a login `QLineEdit` needs
  **focus** (`setFocus` + `selectAll`) so a following `type_text` lands in it.
- **Duplicate objectNames across hosts.** Post-convergence BOTH hosts use `CapturePanel.*`; a plugin-bound
  login lands in the wizard (which builds its own hidden CapturePanel), so a root-wide `findChild` returned the
  wizard's hidden button. Fix: `locate`/`activate`/`wait`/`tabs` resolve **scoped to the current MainView page**
  first (the §17 current-view slice, arrived early), root as fallback.
- **`tabs` command + `walk_tabs()`.** New UDP `tabs` enumerates a QTabWidget's step-tabs so the Director walks
  every step of a phase without hard-coding counts — auto-covers whatever the plugin declares.
- **Camera handoff.** The wizard opens `/dev/video0`; `stopStream()` doesn't block on release, so navigating
  straight to the bench found "no camera". The scenario bounces via **Home + a short sleep** so the wizard's
  stream releases before the bench reopens the device.
- **Recording/Prompter geometry.** (a) `xdotool search --name "^Spectracs"` is case-**in**sensitive → matched
  Geany's `spectracsNotes.txt`; match the title **case-sensitively**. (b) `xdotool getwindowgeometry` reports Y
  off by the title-bar height → the clip clipped the top; read geometry from **`xwininfo`** (absolute coords).
  (c) the Prompter is moved onto a monitor that does **not** contain the app window so it's never filmed.
- **No orphaned recorder.** ffmpeg is stopped on any Director exit (`atexit` + SIGINT/SIGTERM/SIGHUP handlers +
  a QTimer to deliver signals under Qt); `bench.sh` also kills stray recorders on start.
- **Prompter CONTINUE** is disabled except while a gate is actually open (enabled on gate-open, disabled on any
  advance path — button, shortcut, or hotkey).
- Narration corrected: the reference "blank" is the **isopropanol solvent** (not an empty beam); the sample is
  isopropanol **with** the oil.

**Not done (deferred, §17):** the generic `describe`/`walk_workflow`, the wizard/saved-runs/payment/master
chapters, and the `_tour` playlist. The `tabs` command is the first concrete slice of that generic direction.

---

## 17. Future change request — generic, AI-rendered scenario driving

Status: **CHANGE REQUEST (2026-07-13, Edwin).** Recorded for a later milestone; **not scheduled**. The
hand-authored bench scenario (§16.0, B5) is the accepted near-term lean — for a single stable workflow a
hand-written click-list is clearer and the generic machinery pays nothing back. This CR is the direction that
lean evolves toward **once a second workflow exists** and per-scenario click-lists stop paying.

**Intent.** Sooner or later **every upcoming scenario should render generically, with "more or less" AI
contribution.** The external driver walks the *live* workflow (the deferred `describe` / `walk_workflow`,
§16.1–16.3, and the last row of §16.13) instead of a hand-written click sequence, so a new plugin costs little
or no bespoke script. The genericity carries the **structure** (the click sequence, which steps exist, which
metrics exist); authoring supplies only the **words**. This is the "structure introspected, words authored"
seam of §16.1, elevated from a deferred detail to the intended end-state for all scenarios.

**Three content sources for the narration** (evolves the §16.1 hybrid — this is what "more or less AI" means):
1. **Plugin-supplied prose (NEW — Edwin, 2026-07-13).** The plugin itself declares narration/description text
   for its use-case, phases, steps and metrics, so a plugin **ships its own tour copy**. Where the plugin
   supplies good prose the AI contribution drops to light touch-up; where it is silent the AI authors fully —
   hence "more or less". The metric `MetricFieldView.tooltip` already **prototypes** this: a plugin-declared
   string the tour reuses verbatim (§16.1). Generalise it to the whole workflow (use-case / phase / step
   captions), so the narration table (source 2) becomes an *override*, not the only voice.
2. **AI-authored narration table** (§16.2) — the editorial voice, per scenario, filling or overriding where the
   plugin is silent or where a screencast wants a different register than the in-app prose.
3. **Introspected label / tooltip fallback** — when neither of the above supplies text.

**The external-Director / real-cursor architecture is explicitly re-openable (Edwin, 2026-07-13).** The current
two-process split (§1, §3) exists for one reason: put a *visibly gliding* OS cursor on camera while keeping the
operator cockpit (Prompter, gates, hotkey) off it. The new version **need not keep that split** — moving the
mouse "can certainly be managed" another way in the anticipated version, e.g. an **in-app synthetic cursor
overlay** animated only in doc-mode, or a driver that runs **in-process**. Either would dissolve the UDP
keyhole and let the walker read the workflow **directly** (no `describe` round-trip needed), simplifying the
whole harness. So this CR leaves the process boundary open for reconsideration rather than treating it as fixed.

**Carries the deferred plumbing** (from §16.13's last row, with the §16.2 wording correction): a `describe`
command **or its in-process equivalent**; **current-view resolution** (today the UDP service holds only the
root container and `findChild`s by name — `MainViewModule` is a `QStackedWidget`, so the active page is one
`currentWidget()` call away); and a **view-level workflow accessor** — small, because the *engine* already
exposes a public `getWorkflow()` (both hosts use it); only the view→driver hop is missing. Plus the generic
`walk_workflow` and the per-plugin prose (sources 1–2 above).

**Trigger.** The second workflow (the pumpkin wizard) coming back into scope, **or** the scenario count growing
enough that per-scenario click-lists stop paying — whichever comes first. Until then: hand-authored (§16.0).

---

## 18. M4 — bench-screencast refinements (three asks, 2026-07-14)

Status: **COMPLETE (2026-07-15) — the Director task is closed (Edwin).** All of M4 shipped and was driven live on
Edwin's machine across several iterations: the three original tracks (C1 cover / C2 skip-tab / C3 capture-wait,
§18.1–§18.6), the post-first-cut cover refinements (CR-A hold + CR-B typed agenda, §18.7), the post-login
wizard-flash suppression (§18.8), and the 150-frame bench burst (§18.9). Sequence confirmed on camera:
`logo → login → logo+agenda → bench`. Remaining Tier-A chapters / the generic walker stay deferred (§17).
Load-bearing facts below verified against the code.

The three asks:
1. **A branded base/title screen at record start** — the opening frame is the Spectracs logo above a
   "Documentation" label, not a flash of the login/app.
2. **Never re-click a step-tab that is already active** when the phase is entered — clicking the already-selected
   `SpectralWorkflowStep` tab is a visible no-op on camera (the cursor glides and "clicks" but nothing changes).
3. **Wait for the whole capture to finish** — auto-exposure *and* the multi-frame burst — before the next
   automated click. Today the next click fires mid-burst.

### 18.0 Expected rendering (ASCII, common understanding)

Cover shown — it is a **page in the `MainViewModule` stack** (row 1, col 0), so the **status bar (row 0)** and the
**doc panel (col 1)** stay visible; only the main content area (where the overview lives) becomes the card. Label is
a **breadcrumb** `Documentation › <use case>`, reshown at each use case:

```
 ┌─ [logo]  Spectracs  ·············································  edwin ▾ ┐  ← status bar (row 0) STAYS
 ├────────────────────────────────────────────────────────────────┬─ doc panel ─┤
 │                                                                 │ DOCUMENTATION│
 │                 ┌────────────────────────────────┐              │ ──────────── │
 │                 │      ▄▄  S P E C T R A C S  ▄▄  │  ← logo(SVG) │ Measuring a  │
 │                 └────────────────────────────────┘              │ real sample  │
 │              Documentation › measurement bench    ← breadcrumb   │ ──────────── │
 │                                                                 │ ▸ Acquisition│
 │   COVER = a stacked-view PAGE. setCurrentWidget(cover) hides the │   Processing │
 │   prior view (fires its hideEvent → releases /dev/video0) AND    │   Evaluation │
 │   shows this card. Home is never navigated to → never filmed.    │   Publishing │
 └──────────────────── MainViewModule (row 1, col 0) ──────────────┴─────────────┘
```

C3 capture-state timeline (one Capture press):

```
  press ─┬─ auto-expose (REFERENCE only) ─┬─ multi-frame burst ─┐
         ▼                                ▼                     ▼
  TODAY: DISABLED ────────────────────────╳ RE-ENABLED (bug) ──   done   ← wait returns mid-burst
         (and for SAMPLE: never disabled at all — no auto-expose leg)
  FIXED: DISABLED ─────────────────────────────────────────────╳ done   ← busy = __autoExposing OR __capturing
  Director: wait enabled=False (started, non-raising) → wait enabled=True (done) → then reveal/next
```

### 18.1 Ask 1 — doc-mode cover / use-case title card (C1)

**What & why (Edwin, 2026-07-14).** A doc-mode-only cover surface: the Spectracs logo centred with a **breadcrumb
label** below it (`Documentation › <use case>`, e.g. `Documentation › measurement bench`), on the panel background.
Its **goal is to keep the measurements-overview (Home) out of the film**: at startup, and again at the start of
**each use case / chapter**, the cover stands in place of Home so the overview is never the framed content. It is
therefore **reshown per chapter** (not a one-shot opening card), each time with that chapter's breadcrumb.

**Where it lives — a page in the existing stacked view (Edwin, 2026-07-14).** `MainViewModule` is a
`QStackedWidget` (verified: `MainViewModule.py`, ~19 view pages; navigation is `setCurrentIndex`,
`NavigationHandlerLogicModule.py:12-119`). The cover is a **new page in that stack**, not a floating overlay — the
same mechanism the app already uses to swap views. A `DocCoverViewModule(QFrame)` (repo `*ViewModule` convention,
mirrors `DocHintPanelViewModule`) is added to `MainViewModule` **only in doc-mode**, from `MainContainerViewModule`
(which holds the `docMode` flag) via `self.mainViewModule.addWidget(cover)` after construction — so `MainViewModule`
itself stays flag-agnostic and the app is untouched without the flag.

**Why a stack page beats the overlay (supersedes rubber-duck C1.2's manual-geometry child):** switching the stack
to the cover page (a) **hides whatever view was showing — firing its `hideEvent`**, which is precisely what
releases `/dev/video0` today (the post-login wizard holds the camera; the current scenario bounces via `nav("Home")`
+ sleep for exactly this, §16.15), and (b) shows the branded card. So the cover page **replaces the Home
camera-release bounce**: the measurements-overview (Home) is **never navigated to at all**. No `resizeEvent`/`raise_`
overlay bookkeeping either — the stack already manages geometry.

**Scope (falls out of the mechanism):** the stack is `MainViewModule` = grid **row 1, col 0**, so the cover page
occupies the **main content area only**; the **status bar (row 0)** and the **doc panel (col 1)** stay visible
above/beside it. Good: the status bar shows the app chrome (and, after login, the signed-in user) while the card
names the use case, and the doc panel keeps narrating. The overview lives in `MainViewModule`, so covering exactly
that page is what the goal needs.

**Logo source.** Reuse the existing logo, not a new asset. `logo_png` is a **class-attribute SVG string**
(`MainStatusBarViewModule.py:351`) and `_renderLogoSource()` a **side-effect-free** QPixmap render — factor both
into a tiny shared helper used by the status bar and the cover. The SVG scales cleanly to a large centred card (its
green `#3D7848` strokes read fine on the `#2B2B2B` ground). `resource/logo.png` (606×59) is a low banner — not it.

**Order (Edwin, 2026-07-14): logo → visible login → bench.** The card names the use case up front, login is
**filmed**, then the bench. There is no separate "Sign in" card — the one `measurement bench` card bookends the
login, and its second showing is the camera handoff (the ▸ steps are what the camera sees):

1. **record starts** → `cover("measurement bench")` = `mainViewModule.setCurrentWidget(coverPage)` → **card shown**
   (status bar shows logged-out; main area = `Documentation › measurement bench`).
2. `nav("LoginViewModule")` → the login page replaces the card → **▸ login form visible** & submitted (scripted
   from `[bench]` creds *or* a human login into the shown form; the off-camera Prompter "confirm calibrated setup"
   gate runs here). Login lands in the wizard (masterUserExakta is plugin-bound → `/dev/video0` opens).
3. `cover("measurement bench")` again → the stack leaves the wizard (**its `hideEvent` releases the camera**) and
   shows the card; a short `sleep` lets the device release. This is the **camera handoff** — and it means **Home is
   never shown**. The viewer sees the branded card during the ~2 s load, not the measurements-overview.
4. `nav("DevMeasurementBenchViewModule")` → **▸ bench (ACQUISITION) on camera** → run the use case.
5. **next chapter** (`main_chapters` runs `nav("Home")` to reset): show the cover page *first*, so the reset never
   films the overview.

Home is thus **only ever replaced by the cover page, never navigated to**; **login is always filmed** (step 2).

**Protocol + Director.**
- New UDP command **`cover { show: bool, label?: str }`** → in doc-mode, `show:true` does
  `mainViewModule.setCurrentWidget(coverPage)` and sets the breadcrumb (the page renders the `Documentation › `
  prefix; `label` is the use-case name). There is **no explicit hide** — the next `nav` switches the stack away
  naturally (`show:false` is accepted as a no-op / return-to-previous for symmetry). Route via a cover reference the
  service holds (today `DocModeUdpService` holds `__root` + `__hintPanel`; add `__root.docCoverViewModule`), gated on
  `docMode`. Note: while the cover page is current, `__lookup`'s current-view scoping resolves to it — fine, the
  Director drives no view widgets until after the next `nav`.
- Director method **`cover(label=None)`** (thin: send `cover{show:true,label}`); the scenario navs away to lower it.
  `main_chapters.run_all` shows the cover with the chapter title before each chapter's reset nav.

### 18.2 Ask 2 — never re-click the already-active step-tab (C2)

**Verified cause.** On entering a `SpectralWorkflowPhase` the phase's step-tab `QTabWidget` already has a current
tab (index 0, or wherever it was left). `walk_tabs` (`automation_director.py:532`) clicks **every** tab including
that one; `setCurrentIndex(sameIndex)` emits nothing, so the cursor glides and "clicks" with no visible change —
reads as broken. Same for ACQUISITION: `CapturePanel` starts on step 0 = **Reference** (`__activeStep =
steps[0]`), so the scenario's explicit `click(ROLE_TABS, tab=REFERENCE_TAB)` (measurement_bench.py:126) is a
redundant no-op.

**Change.** The `tabs` command **already returns `current`** (`DocModeUdpService.__tabs`, line 226); today the
Director's `tabs()` drops it — surface it.

- **Track the currently-shown index, don't skip a fixed entry-current (rubber-duck C2.5, CONFIRMED bug).** A naive
  "skip whatever was current on entry" fails when a phase opens on a **non-zero** tab: walking 0,1,2,3 with
  entry-current=2 you'd click 0, click 1, then skip 2 while sitting on 1 → tab 2 is **narrated but never shown**.
  Correct rule (no extra RPC):
  ```python
  shown = entry_current           # from tabs()['current']
  for i, label in enumerate(labels):
      if i != shown:              # the displayed tab needs no activation
          go_to_tab(name, i); shown = i
      narrate(label); on_tab(...); screenshot(...)
  ```
- **Skipped tab still gets a cursor visit — glide-to-point, no click (was open; my lean).** "No click" must not mean
  "no cursor motion" (the viewer would see narration with a frozen pointer on the first tab). So the skip path
  **glides the visible cursor to the tab header** (`locate` → `pyautogui.moveTo`) but issues **no `activate`** — a
  `go_to_tab(name, index, activate=True|False)` / `point(name, tab)` primitive. Cursor continuity, zero redundant
  no-op click.
- Same rule for the ACQUISITION role tabs: `CapturePanel` opens on step 0 = **Reference** (`__activeStep =
  steps[0]`), so the Reference role-tab is glide-to-point-only on entry; the **Sample** switch clicks. (roleTabs is
  disabled while capturing, but the Reference visit is pre-capture and the Sample switch runs after `wait_capture`,
  so the tab-bar disable never interferes — C2.6.)
- Rationale is purely cosmetic-for-video; the workflow logic is unchanged.

### 18.3 Ask 3 — wait for the FULL capture (auto-expose + burst) before the next click (C3)

**Verified cause.** `CapturePanel.__onClickedCapture` (CapturePanel.py:422-475) runs the capture **synchronously on
the GUI thread** via nested `QEventLoop`s (`__pumpFrames`, line 406 — which keep servicing the UDP socket, so the
Director's `wait` polling is answered throughout, C3.10). It disables the capture button **only while
auto-exposing**: `__updateControls` sets `busy = self.__autoExposing` (line 300) → `captureButton.setEnabled(… and
not busy)` (line 304). The `__autoExposing` flag is cleared in the auto-exposure `finally` (line 387) **before**
the multi-frame burst (`captureAcquisitionStep`, line 455) runs — so during the burst the button is **re-enabled**.
`wait_ready(CAPTURE, enabled=True)` (measurement_bench.py:131,141) therefore returns the moment auto-exposure ends,
**mid-burst**, and the next click fires too early.

**Stronger for SAMPLE (rubber-duck C3.7).** Auto-exposure runs for **REFERENCE only** (line 429 gates
`role == REFERENCE and …isChecked()`). For the **sample** capture `__autoExposing` is **never set** → the button is
**never disabled at all** during the sample burst → the sample wait returns *instantly*. So `__capturing` is not
merely better — for the sample capture it is the **only** gating there is.

**App fix (also a genuine robustness fix outside doc-mode).** Add a `__capturing` flag spanning the **whole**
`__onClickedCapture` (auto-expose + burst), and fold it into `busy`: `busy = self.__autoExposing or self.__capturing`.
**Set/reset via try/finally (rubber-duck C3.8, CONFIRMED):** the failure branch `if spectrum is None or not images:
self.__onCaptureFailed(); return` (lines 459-461) returns **early** — a reset only at method end would leave the
button **permanently disabled** on a failed capture. So: set `__capturing = True` **after** the `step is None`
guard, then `try: … finally: self.__capturing = False; self.__updateControls()`. The capture button (and role tabs
/ frames combo) then stay disabled for the entire capture and re-enable on **every** exit path. Fix lives in
`CapturePanel`, so it covers **both** hosts (bench + wizard's real-capture path); the pumpkin wizard's *virtual*
Measure is a different path (`WizardViewModule.measureButton` → engine round-trip) and is out of this scope.

**Director fix (close the start race, gracefully).** `activate` triggers the capture via `animateClick()`
(~100 ms delayed), so a bare `wait_ready(enabled=True)` could sample *before* the click even fires. Wait for capture
to **start then finish** — `enabled=False` (began) → `enabled=True` (done) — wrapped as **`wait_capture(name)`**.
Real captures are seconds long (reference ≈ 8×~350 ms auto-expose + 20×~120 ms ≈ 4–5 s; sample ≈ 20×~120 ms ≈ 2.4 s)
so the disabled edge is easily observable. But **the "wait for started" leg must NOT raise on timeout** (rubber-duck
C3.9): `wait_ready` raises `RuntimeError` on timeout (automation_director.py:557), which aborts the scenario — so if
a future faster capture misses the disabled edge, `wait_capture` swallows that short timeout and **falls straight
through to the long-timeout `enabled=True` leg**. Reveal the spectrum / screenshot only after it returns.

### 18.4 Deltas summary

| Area | Add |
|------|-----|
| App — shared logo helper | factor `logo_png` + a static SVG→pixmap render out of `MainStatusBarViewModule` into a tiny util reused by the status bar and the cover |
| App — `DocCoverViewModule` (new) | doc-mode-only QFrame: centred logo + breadcrumb `Documentation › <label>` on `#2B2B2B`; `setLabel(useCase)` |
| App — `MainViewModule` / `MainContainerViewModule` | in `docMode`, `mainViewModule.addWidget(cover)` as a stack page + keep a ref; no overlay/`resizeEvent` |
| App — `DocModeUdpService` | `cover {show, label?}` → `mainViewModule.setCurrentWidget(coverPage)` + `setLabel`; (`tabs` already returns `current` — no change) |
| App — `CapturePanel` | `__capturing` flag spanning the whole capture via try/finally; `busy = __autoExposing or __capturing` |
| Director | `cover(label)` (→ `cover{show,label}`, scenario navs away to lower); `go_to_tab(name, index, activate)` + `point`; `wait_capture(name)` (non-raising "started" leg); `tabs()` surfaces `current`; `walk_tabs` tracks the shown index + glide-to-point on the shown tab |
| Scenario `measurement_bench.py` | `cover("measurement bench")` → `nav(Login)` (visible login) → `cover("measurement bench")` again (camera handoff, replaces the Home bounce) → `nav(Bench)`; Reference role-tab → glide-to-point-only; both capture waits → `wait_capture` |

### 18.5 Implementation phases (when Edwin says "go")

Three independent tracks; **C3 is the only one touching non-doc-mode app code** (`CapturePanel`) and is the
highest-value (fixes a real mid-burst race, incl. the sample capture which is ungated today). C1 and C2 are
doc-mode-only and cosmetic-for-video. All app-side changes stay gated on `--doc-mode` except the `CapturePanel`
`__capturing` fix, which is a legitimate always-on robustness improvement.

| Ph | Track | Deliverable | Side | Depends | Verify |
|----|-------|-------------|------|---------|--------|
| C3a | capture-wait | `CapturePanel.__capturing` + `busy = __autoExposing or __capturing`, set/reset in try/finally (covers the capture-failed early return) | app (always-on) | — | offscreen: button stays disabled across a full capture incl. failed frames |
| C3b | capture-wait | Director `wait_capture(name)` = wait `enabled=False` (non-raising short) → `enabled=True` (long); swap `measurement_bench.py` waits | director + scenario | C3a | rig: next click fires only after the burst ends |
| C1a | cover | shared logo-render helper (factor `logo_png` + render out of `MainStatusBarViewModule`); status bar still renders identically | app (always-on refactor) | — | app looks unchanged (logo pixel-identical) |
| C1b | cover | `DocCoverViewModule` (logo + breadcrumb `Documentation › <label>`, `setLabel`) + added as a `MainViewModule` stack page in `docMode` + `cover {show, label?}` → `setCurrentWidget` UDP cmd | app (doc-mode) | C1a | offscreen: `cover{show:true,label:"measurement bench"}` makes the cover page current; status bar + doc panel stay |
| C1c | cover | Director `cover(label)`; scenario: `cover("measurement bench")` → `nav(Login)` **visible login** → `cover(...)` again (camera handoff, replaces Home bounce) → `nav(Bench)`; `main_chapters.run_all` shows the cover before each chapter's reset nav | director + scenario | C1b | rig: login filmed; Home never navigated to / never filmed; card bookends login |
| C2a | skip-tab | Director `tabs()` surfaces `current`; `go_to_tab(name, index, activate)`/`point`; `walk_tabs` tracks the shown index + glide-to-point on it | director | — | offscreen: walking a 5-tab phase entered on idx 0 and on idx≠0 shows every tab, clicks none twice |
| C2b | skip-tab | `measurement_bench.py`: Reference role-tab → glide-to-point-only | scenario | C2a | rig: no visible no-op click on the already-active tab |
| C4 | recording | **live-rig re-record** the bench screencast with all three landed | rig | C1c,C2b,C3b | the deliverable mp4 |

**Rubber-duck pass (2026-07-14, fork against the code) folded in:** C1.1 auto-show→Director-driven (attach-mode
login), C1.2 manual-geometry child (**later superseded** — the cover is a `MainViewModule` stack page per Edwin,
which also makes the Home camera-release bounce disappear), C2.4 glide-to-point (not narrate-only), C2.5 track shown
index (fixed entry-current mis-skips a non-zero-entry phase), C3.7 sample burst is ungated today (stronger case),
C3.8 try/finally around the capture-failed early return, C3.9 non-raising "started" leg. All CONFIRMED against
`CapturePanel.py` / `DocModeUdpService.py` / `automation_director.py` / `measurement_bench.py` / `bench.sh`.

### 18.6 As-built (2026-07-14) — the one-sweep implementation

All C phases shipped together. Files:
- **C1a** — new `sciens/spectracs/logic/appliction/style/LogoRenderer.py` (`LOGO_ASPECT` + `renderLogoPixmap(svg,
  height)`); `MainStatusBarViewModule._renderLogoSource` delegates to it (logo pixel-identical). The SVG string
  stays the single source (the status bar class attr `logo_png`) — the *renderer* is shared, not the asset moved.
- **C1b** — new `sciens/spectracs/view/main/DocCoverViewModule.py` (QFrame: centred wordmark via `LogoRenderer` +
  `Documentation › <label>` breadcrumb, `setLabel`). `MainContainerViewModule`, in `docMode` only, does
  `mainViewModule.addWidget(self.docCoverViewModule)` and keeps the ref. `DocModeUdpService.__cover` handles
  `cover {show, label?}` → `docCoverViewModule.setLabel` + `mainViewModule.setCurrentWidget(cover)` (which fires
  the prior view's `hideEvent` → camera release); returns `{ok:true}`.
- **C1c** — Director `cover(label)`; `measurement_bench.run` order is now `cover("measurement bench")` →
  `login("bench")` (visible) → `cover("measurement bench")` (camera handoff, **replaced** the old `nav("Home")`) →
  `nav(Bench)`. `login()`'s human fallback now navs to the login form first (so the cover can't hide it).
- **C2a** — Director `__tabs_state` surfaces `current`; new `go_to_tab(name, index, activate=True)` (glide always,
  click only if `activate`); `walk_tabs` tracks the shown index and glide-to-points the already-shown tab.
- **C2b** — `measurement_bench` Reference role-tab → `go_to_tab(..., activate=False)`; Sample → `activate=True`.
- **C3a** — `CapturePanel.__capturing` flag set/reset in a try/finally over the whole `__onClickedCapture`;
  `busy = self.__autoExposing or self.__capturing`. Always-on (also fixes the previously-ungated sample burst and a
  re-entrant-click hole outside doc-mode).
- **C3b** — Director `wait_capture(name)` (non-raising `enabled=False` "started" leg → `enabled=True` "done" leg);
  `measurement_bench` swaps both `wait_ready(CAPTURE, enabled=True)` calls to `wait_capture(CAPTURE)`.

**Verified offscreen:** every changed file byte-compiles; `LogoRenderer`/`DocCoverViewModule`/`DocModeUdpService`
import under `QT_QPA_PLATFORM=offscreen`; the cover constructs and renders the wordmark (917×90 px). **Pending the
rig (C4):** the live cursor behaviour (glide-to-point on the active tab), the capture-timing wait, and the on-camera
cover/login/bench sequence — then the re-record.

### 18.7 Change requests after the first cut (2026-07-14, Edwin) — DESIGN

Status: **IMPLEMENTED (code, 2026-07-14) — awaiting rig re-record.** Edwin drove the first cut and asked for two
cover refinements; both landed in one sweep (compiles + the agenda types progressively offscreen). As-built note at
the end of this section. Load-bearing facts verified against the code.

**CR-A — the first logo card disappears too fast.** `cover()` sends the command then `time.sleep(0.8)`
(`automation_director.py`); the very next scenario line is `login("bench")`, whose scripted path immediately
`nav("LoginViewModule")` swaps the card out — so card #1 shows ~0.8 s. **Fix:** add a `hold` param to
`cover(label, hold=None)` (Director-side `time.sleep(hold or 0.8)`; a static-card sleep, the app keeps painting).
Scenario: first call `cover("measurement bench", hold=3)`.

**CR-B — the second logo card shows a typed "agenda".** Below the breadcrumb, type out (letter-by-letter) an overview
of what the video will show, so the viewer knows the arc up front. The four points (Edwin's wording, tunable):
1. Measurement on a real spectrometer of real oil.
2. Evaluations create some metrics.
3. A PDF is created for viewing, with all spectral data embedded.
4. The PDF can be sent to a laboratory information management system (LIMS).

Design, with the rubber-duck findings folded in:

- **Typewriter = a NEW shared `TypewriterLabel(QLabel)`, char-by-char — NOT the panel's `__buildChunks` (CONFIRMED
  trap).** `DocHintPanelViewModule.__buildChunks` splits on sentence punctuation (`[^.!?]+[.!?]?\s*`); the agenda
  points have **no periods**, so a joined block becomes a **single** chunk revealed *word-wise* (its `\s` even spans
  the `\n`, so a word straddling a line-break types as one token) — not the "letter-typing" Edwin asked for. So
  factor the reveal *engine* (QTimer tick + stop-guard) into a small `TypewriterLabel` with **explicit char
  granularity**, fed the point **list**. The cover uses it now; refactoring the (working) doc-panel caption to adopt
  it is **deferred** — keeps this change surgical.
- **`DocCoverViewModule` gains an agenda zone.** A max-width (~720 px), word-wrapped, left-aligned bullet block
  centred under the breadcrumb, font ~18 px (below the 22 px breadcrumb) — fits at 1080p under the 90 px logo with
  the existing top/bottom stretches (`--phone` 412 dp gets tall but the card is full-height → acceptable; tune on the
  rig). `setPoints(points, wpm)`: **None/empty ⇒ clear** (stop timer, `setText("")`, hide the zone) so card #1 shows
  no stale agenda (CR-B.4); a list ⇒ build `• …` lines and type them char-by-char. **Stop the running timer at the
  top of every `setPoints`/`setText`** and on `hideEvent` (CR-B.3) so a re-show or nav-away never double-runs a timer
  or ticks a hidden label.
- **Protocol:** `cover { show, label?, points?, wpm? }`. `__cover` calls `setLabel(label)` **and always**
  `setPoints(points, wpm)` (clearing when `points` absent). `wpm` is plumbed end-to-end so the agenda paces with the
  doc panel (CR-B.7). Reply stays `{ok:true}`.
- **Director:** `cover(label=None, points=None, hold=None, wpm=None)` — payload carries `wpm` (default `self.__wpm`);
  then sleeps `hold`. **If `points` and no explicit `hold`, compute the dwell** from the agenda's reading time
  (`words / wpm × 60`, floored), so the agenda reliably finishes typing on camera **before** the following
  `wait_for_human` gate opens (CR-B.6) rather than relying on the operator not continuing early.
- **Timing is cross-process (CR-B.1, not-a-problem):** the app is a separate process from the Director
  (`launch_app` → `subprocess.Popen`); the app's `QTimer` types the agenda in its own GUI loop regardless of the
  Director thread being blocked in `wait_for_human`. The `cover(hold=…)` dwell just keeps the two paced together.

Scenario delta (`measurement_bench.run`): card #1 → `cover("measurement bench", hold=3)`; card #2 →
`cover("measurement bench", points=[…the 4…])` (auto-computed dwell). No other flow change.

| Ph | Deliverable | Side | Depends |
|----|-------------|------|---------|
| D1 | shared `TypewriterLabel(QLabel)` — char-by-char reveal at a wpm, stop-on-set + `hideEvent` stop | app | — |
| D2 | `DocCoverViewModule` agenda zone (`setPoints(points, wpm)`, clear-on-None, max-width container) | app (doc-mode) | D1 |
| D3 | `cover {points?, wpm?}` in `DocModeUdpService.__cover` (always `setPoints`, plumb `wpm`) | app (doc-mode) | D2 |
| D4 | Director `cover(label, points, hold, wpm)` — `hold` sleep + computed dwell from points | director | D3 |
| D5 | `measurement_bench`: card #1 `hold=3`; card #2 `points=[…]` | scenario | D4 |
| D6 | rig re-record (folds into C4) | rig | D5 |

**As-built (2026-07-14):** D1 `view/application/widgets/TypewriterLabel.py` (char-by-char QLabel, `type(text,wpm)` /
`clear()`, stop-on-set + `hideEvent` stop). D2 `DocCoverViewModule.setPoints(points, wpm)` — bulleted `TypewriterLabel`
in a 720 px max-width column, hidden/cleared when points are falsy. D3 `__cover` always calls `setPoints` (plumbs
`points`+`wpm`). D4 Director `cover(label, points, hold, wpm)` + `__agenda_dwell` (mirrors the TypewriterLabel cadence
so the hold ≈ the typing time + read tail). D5 `measurement_bench` `AGENDA` list; card #1 `hold=3`, card #2
`points=AGENDA`. **Verified offscreen:** all compile; card #1 hides the agenda, card #2 types it progressively
(9 chars in ~0.5 s of a 229-char block). Pending rig: on-camera pacing/fit + the re-record.

### 18.8 Suppress the post-login wizard flash in doc-mode (2026-07-15) — IMPLEMENTED

Status: **IMPLEMENTED (code, 2026-07-15) — awaiting rig re-record.** Edwin's first cut showed
`(1) logo → (2) login → (3) the measurement WIZARD → (4) agenda card → bench`; he wants the desired sequence
`(1) logo → (2) login → (3) agenda card → (4) bench` with **no wizard flash**.

**Cause (verified):** the app's normal launch seam — `LoginViewModule.onClickedLoginButton`
(`LoginViewModule.py:127-129`) navigates a plugin-bound user (`masterUserExakta`) to `WizardViewModule` right
after login. That wizard both *flashes* between login and the agenda card and *opens `/dev/video0`* (which is why
the second cover was doing a "camera handoff").

**Fix (one app change, doc-mode-gated):** skip the launch-seam `__navigateTo(target)` when `--doc-mode` is set
(`"--doc-mode" not in sys.argv`, the same signal `DocModeUdpService` uses for its port). The Director drives all
navigation itself, so nothing needs to auto-land. Gated on the flag → the normal app's launch seam is untouched.

**Consequences (both good):** the wizard never becomes current → **no flash**; and it never opens the camera → **no
contention**, so the second cover is now *only* the agenda card (its former camera-handoff role is gone) and the
scenario's vestigial `sleep(2)` camera-release wait is dropped. In doc-mode the app simply stays on the login view
between login-success and the Director's next `cover()` (harmless — same screen already filmed; the card covers it).

**As-built files:** `LoginViewModule.py` (+`import sys`; the gated launch-seam skip); `measurement_bench.py` (drop
`sleep(2)`; second-cover comment updated). Compiles + imports offscreen. Pending rig: confirm the 4-step sequence
on camera, then the re-record.

### 18.9 Bench capture burst → 150 frames (2026-07-15) — IMPLEMENTED

Status: **IMPLEMENTED (code, 2026-07-15).** Edwin: "update the measurement-bench plugin to use 150 frames at
capturing." The bench averages more frames for a cleaner spectrum.

**Cause of the disconnect (verified):** `DevSpectralPlugin.FRAMES` was declared (20) and applied via
`step.setFrames`, but **real** capture through `CapturePanel` read its own **hardcoded** frame-count combo
(`__DEFAULT_FRAMES = "20"`), ignoring the plugin — so the plugin's `FRAMES` only affected the *virtual* path
(`SpectralWorkflowEngine.captureAcquisitionStep` falls back to `step.getFrames()` when no `frames` arg is passed).

**Fix:** `DevSpectralPlugin.FRAMES = 150`, and `CapturePanel` now **seeds its frame-count combo from the active
step's plugin-declared `getFrames()`** (added to the choices, set as default) instead of the hardcoded 20 — so a
plugin's declared burst actually drives real capture; the dropdown (when a plugin shows it) still overrides.

**Notes:** (a) 150 frames ≈ ~18 s per capture (150 × ~120 ms) + reference auto-exposure; `wait_capture`'s 90 s
done-timeout covers it. (b) Side effect: the pumpkin plugin's **real-device** capture now follows its own declared
`FRAMES = 5` (was an incidental 20); the pumpkin **virtual** demo already used 5, so it is unchanged. **Files:**
`DevSpectralPlugin.py`, `CapturePanel.py`.
