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
