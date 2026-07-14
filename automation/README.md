# Doc-automation harness (`--doc-mode` screencasts)

Dev tooling to record documentation videos/screenshots by driving Spectracs with a **visible mouse** while
an in-app hint panel and a left-screen Prompter narrate. See `docs/SPEC_doc_automation.md` for the full
design. **Not app code** — nothing here is imported by the app.

## How it works (one line)

The app, launched with `--doc-mode`, shows a right-side hint panel and opens a UDP listener on
`127.0.0.1:5555`. An external **Director** script asks the app *where* a widget is (`locate`) and drives a
real mouse (PyAutoGUI) to that live coordinate — so the cursor motion is captured on video, yet targeting
stays robust because the app resolves its own widget coordinates.

## One-time setup

```bash
./venv/bin/pip install pyautogui pynput   # dev-only; never runtime deps of the app
# optional: sudo apt install scrot          # screenshots fall back to Pillow ImageGrab if absent
```

`pynput` powers the global **Ctrl+Shift+ß** advance hotkey (§16.7); if it's absent the Director prints a
notice and you advance with **Space/Enter on the Prompter** instead. `wmctrl` + `xdotool` (used to raise the
app window before each click, and to record the app-window rect) are already present on this box.
X11 only — on Wayland PyAutoGUI can't move the cursor (see spec §9).

## Config (unversioned) — `spectracsPy-config/director.ini`

A sibling of the repo, **not under git** (§16.8). `[default]` sets pacing (`wpm` / `speed` / `min_dwell`);
each `[scenario]` section holds `username` + `password` for scripted login. Leave `password` blank to fall
back to a human login gate. Override the path with `DOC_CONFIG=...`. Env vars `DOC_WPM` / `DOC_SPEED` /
`DOC_MIN_DWELL` override `[default]`.

## Artifacts (outside the code repo)

Recordings + screenshots write to `../spectracs-references/director/{recordings,screenshots}` (unversioned,
so heavy mp4s never touch git — §16.9). Override the base with `DOC_ARTIFACTS_DIR=...`.

## Run a scenario

Each scenario launches the app itself (`./runApp.sh --doc-mode`) and drives it:

```bash
# from repo root:
PYTHONPATH=.:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server \
  ./venv/bin/python automation/scenarios/<name>.py
```

| scenario | hardware | session prerequisite |
|----------|----------|----------------------|
| `_smoke.py` | none | any — proves the seam on the status-bar logo |
| `pumpkin_wizard.py` | none (virtual) | user with the pumpkin plugin configured |
| `measurement_bench.py` | **real camera + lamp** | `masterUserExakta`, a **non-virtual** spectrometer plugged **direct-to-USB**, lamp on the slit |

**Abort any run**: slam the mouse cursor into a screen corner (PyAutoGUI failsafe).

## Recording the video (manual, M1)

1. Two monitors. Put the **Prompter on the left** monitor, the **app on the right**.
2. OBS Studio: one wide canvas (e.g. 3840×1080); capture the left monitor to the left half, the right
   monitor to the right half.
3. Press **REC**, run the scenario, do the human beats the Prompter asks for (insert reference, swap
   sample), press **STOP**.

The composited file (`measurement_bench.mp4`) is the artifact; per-scene PNGs land in
`automation/screenshots/` for the written manual.

## Files

```
automation_director.py     Director API + Prompter + Scenario(QThread) + main()
scenarios/_smoke.py        P3 seam gate (no hardware)
scenarios/pumpkin_wizard.py  virtual measurement wizard (template for all chapters)
scenarios/measurement_bench.py  the bench first-sweep (hardware-in-the-loop)
screenshots/               per-scene PNG output (gitignored)
```

App side lives in the app tree: the `--doc-mode` flag (`spectracsMain.py`),
`sciens/spectracs/view/main/DocHintPanelViewModule.py`, and
`sciens/spectracs/logic/appliction/docmode/DocModeUdpService.py`.

## UDP protocol (127.0.0.1:5555, JSON datagrams)

| cmd | fields | reply |
|-----|--------|-------|
| `set_hint` | `text` | — (alias of `doc{caption}`) |
| `doc` | `use_case?`,`outline?`,`phase?`,`caption?`,`reveal?`,`wpm?` | — (updates the 3-zone panel; caption animates) |
| `locate` | `name`, opt `tab` | `{ok,cx,cy,x,y,w,h}` global px (tab → tab-header rect) or `{ok:false}` |
| `nav` | `view` | `{ok:true}` — reach a view whose menu entry is a `QAction` |
| `tabs` | `name` | `{ok,count,labels[],current}` for a QTabWidget — lets the Director walk every step-tab |
| `wait` | `name`, `enabled`/`visible`/`text` | `{ok:true}` if it matches now (Director polls) |
| `dismiss` | — | click an open in-window dialog's OK; `{ok,dismissed}` |
| `ping` | — | `{ok:true}` |
```
