"""Director framework for --doc-mode screencasts (SPEC_doc_automation §6).

Dev tooling, NOT app code — never imported by the app. A scenario file (automation/scenarios/*.py)
supplies a thin `run(director)` body; this module gives it the reusable machinery:

  * Director   — the API a scenario calls (nav / click / wait_ready / set_hint / wait_for_human / ...).
  * Prompter   — a non-modal left-monitor window with a big CONTINUE button for human-in-the-loop beats.
  * Scenario   — a QThread so `sleep`s and blocking waits never freeze the Prompter's event loop.
  * main()     — wires the three together, launches the app, runs the scenario, tears down.

The Director talks to the running app over UDP (DocModeUdpService): it asks `locate` where a widget is,
then drives a REAL mouse (pyautogui) to that live coordinate so the cursor motion is captured on video.

Run a scenario:   python automation/scenarios/<name>.py
(the app's PYTHONPATH/venv recipe applies — see automation/README.md)
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time

import atexit
import configparser
import signal

import pyautogui
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECTRACS_ROOT = os.path.dirname(REPO_ROOT)   # /home/.../spectracs — the multi-repo parent

# Artifacts land OUTSIDE the code repo (SPEC_doc_automation §16.9): spectracs-references/ is not a git repo,
# so heavy mp4s never touch version control. DOC_ARTIFACTS_DIR overrides the base.
ARTIFACTS_DIR = os.environ.get(
    "DOC_ARTIFACTS_DIR", os.path.join(SPECTRACS_ROOT, "spectracs-references", "director"))
SHOTS_DIR = os.path.join(ARTIFACTS_DIR, "screenshots")
RECORDINGS_DIR = os.path.join(ARTIFACTS_DIR, "recordings")

# Unversioned sibling config (SPEC_doc_automation §16.8): per-scenario [sections] with login + pacing.
CONFIG_PATH = os.environ.get("DOC_CONFIG", os.path.join(SPECTRACS_ROOT, "spectracsPy-config", "director.ini"))

DEFAULT_PORT = 5555

pyautogui.FAILSAFE = True   # slam the cursor into a screen corner to abort a runaway run
pyautogui.PAUSE = 0.1


def _load_config():
    """Read the unversioned director.ini (§16.8). Missing file → an empty parser (all lookups fall back)."""
    parser = configparser.ConfigParser()
    try:
        if os.path.isfile(CONFIG_PATH):
            parser.read(CONFIG_PATH)
            print("Director: loaded config %s (sections: %s)" % (CONFIG_PATH, parser.sections()))
        else:
            print("Director: no config at %s — logins fall back to a human gate." % CONFIG_PATH)
    except Exception as exception:
        print("Director: could not read %s (%s)" % (CONFIG_PATH, exception))
    return parser


class Prompter(QDialog):
    """Left-monitor operator prompter: instruction text + a big CONTINUE button (spec §6.1)."""

    continued = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Director Prompter")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        self.__instruction = QLabel("Starting…")
        self.__instruction.setWordWrap(True)
        self.__instruction.setStyleSheet("font-size: 22px; font-weight: bold; color: #E8E8E8;")
        layout.addWidget(self.__instruction, stretch=1)

        self.__button = QPushButton("CONTINUE  ▶")
        self.__button.setStyleSheet(
            "QPushButton { font-size: 22px; padding: 20px; background-color: #2E7D32; color: white;"
            " border-radius: 8px; }"
            "QPushButton:disabled { background-color: #3A3A3A; color: #777777; }")
        self.__button.clicked.connect(self.continued.emit)
        self.__button.setEnabled(False)   # inactive until a gate actually expects a click/shortcut (Edwin)
        layout.addWidget(self.__button)

        # Keyboard-advance fallback (§16.7): Space/Enter on the (focused) Prompter, for when the global
        # Ctrl+Shift+ß hotkey (pynput) is unavailable. The Prompter is left-monitor, off the recording.
        for key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(QKeySequence(key), self, activated=self.continued.emit)

        self.setStyleSheet("QDialog { background: #1E1E1E; }")
        self.__targetScreen, self.__targetRect = self.__computeTarget()
        self.place()

    def __computeTarget(self):
        # The Prompter must never land on the app window (the recording grabs the app's own rect, so an
        # overlapping dialog gets filmed). Put it on a screen the app does NOT occupy. The app maximizes on
        # the PRIMARY screen, so default to a non-primary one. DOC_PROMPTER_SCREEN overrides:
        # left|right|primary|nonprimary|<index>. Compare by name(), not identity, to be safe.
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        primaryName = primary.name() if primary else None
        nonPrimary = [s for s in screens if s.name() != primaryName]
        choice = os.environ.get("DOC_PROMPTER_SCREEN", "").strip().lower()
        target = None
        if choice in ("left", "leftmost"):
            target = min(screens, key=lambda s: s.geometry().x())
        elif choice in ("right", "rightmost"):
            target = max(screens, key=lambda s: s.geometry().x())
        elif choice == "primary":
            target = primary
        elif choice in ("nonprimary", "secondary"):
            target = nonPrimary[0] if nonPrimary else primary
        elif choice.isdigit() and int(choice) < len(screens):
            target = screens[int(choice)]
        if target is None:
            target = nonPrimary[0] if nonPrimary else primary   # default: a screen off the app
        geo = target.geometry()
        w, h = 480, 360
        rect = (geo.x() + (geo.width() - w) // 2, geo.y() + (geo.height() - h) // 2, w, h)
        print("Director: Prompter → screen %r @ (%d,%d)  [DOC_PROMPTER_SCREEN=left|right|0|1 to override]"
              % (target.name(), rect[0], rect[1]))
        return target, rect

    def place(self):
        # Re-assert position (call again AFTER show()): many window managers ignore a QDialog's pre-show
        # geometry and auto-centre it on the active monitor — which is the app's. Force via the window
        # handle's screen + an explicit move so it lands off the recorded app window.
        x, y, w, h = self.__targetRect
        handle = self.windowHandle()
        if handle is not None and self.__targetScreen is not None:
            handle.setScreen(self.__targetScreen)
        self.setGeometry(x, y, w, h)
        self.move(x, y)

    def place_avoiding(self, ax, ay, aw, ah):
        # Re-place onto a screen that does NOT contain the app window (ax,ay,aw,ah). Honors an explicit
        # DOC_PROMPTER_SCREEN override (then this is a no-op). Called once the Director locates the app.
        if os.environ.get("DOC_PROMPTER_SCREEN", "").strip():
            return
        from PySide6.QtCore import QRect
        appRect = QRect(ax, ay, aw, ah)
        free = [s for s in QGuiApplication.screens() if not s.geometry().intersects(appRect)]
        if not free:
            print("Director: no monitor free of the app — Prompter may overlap (single screen?).")
            return
        target = free[0]
        geo = target.geometry()
        w, h = 480, 360
        self.__targetScreen = target
        self.__targetRect = (geo.x() + (geo.width() - w) // 2, geo.y() + (geo.height() - h) // 2, w, h)
        print("Director: app at (%d,%d %dx%d) → Prompter moved off it to screen %r @ (%d,%d)"
              % (ax, ay, aw, ah, target.name(), self.__targetRect[0], self.__targetRect[1]))
        self.place()

    def raise_and_focus(self):
        # Called at each human gate: bring the Prompter to the front on its (off-recording) screen, enable +
        # focus the CONTINUE button so Space/Enter reliably advances even without the global hotkey.
        self.set_gate_active(True)
        self.place()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.__button.setFocus()

    def set_gate_active(self, active):
        # The CONTINUE button is live ONLY while a gate is open (Edwin): disabled otherwise so it never
        # invites a click when nothing is waiting.
        self.__button.setEnabled(bool(active))

    def set_instruction(self, text):
        self.__instruction.setText(text)


class Scenario(QThread):
    """Runs the scenario `run(director)` off the GUI thread (spec §6.1)."""

    promptChanged = Signal(str)
    gateOpened = Signal()      # a human gate just opened → raise/focus the Prompter + enable CONTINUE
    gateClosed = Signal()      # the gate was satisfied (any advance path) → disable CONTINUE again
    appRect = Signal(int, int, int, int)   # the app window's rect once known → move the Prompter off it

    def __init__(self, run_fn, director):
        super().__init__()
        self.__run_fn = run_fn
        self.__director = director

    def run(self):
        try:
            self.__run_fn(self.__director)
        except pyautogui.FailSafeException:
            print("Director: FAILSAFE triggered — scenario aborted by operator.")
        except Exception as exception:
            print("Director: scenario error — %s" % exception)
        finally:
            self.__director.finish()


class Director:
    """The API a scenario calls. Lives on the Scenario thread (spec §6.1 method table)."""

    def __init__(self, continue_event, port=DEFAULT_PORT):
        self.__host = ("127.0.0.1", port)
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.settimeout(0.5)
        self.__continue = continue_event
        self.__prompt_emit = lambda text: None
        self.__gate_emit = lambda: None
        self.__gate_close_emit = lambda: None
        self.__app_rect_emit = lambda x, y, w, h: None
        self.__proc = None
        # Reading-time pacing (§16.5). director.ini [default] supplies defaults; env vars override.
        self.__config = _load_config()
        defaults = self.__config["default"] if self.__config.has_section("default") else {}
        self.__wpm = float(os.environ.get("DOC_WPM", defaults.get("wpm", 180)))
        self.__speed = float(os.environ.get("DOC_SPEED", defaults.get("speed", 1.0)))
        self.__min_dwell = float(os.environ.get("DOC_MIN_DWELL", defaults.get("min_dwell", 1.2)))
        # Attach mode (DOC_ATTACH=1): drive an ALREADY-running app the operator prepared (logged in,
        # calibrated) instead of launching a fresh one — required for the bench, which needs a real
        # session the harness can't synthesize. In attach mode we never spawn or terminate the app.
        self.__attach = os.environ.get("DOC_ATTACH") == "1"
        # Screen recording (DOC_RECORD=1): the Director spins up ffmpeg (x11grab) for the whole run so a
        # single command yields an .mp4 — no manual OBS. Name from DOC_RECORD_NAME.
        self.__record = os.environ.get("DOC_RECORD") == "1"
        self.__record_name = os.environ.get("DOC_RECORD_NAME", "recording")
        self.__record_full = os.environ.get("DOC_RECORD_FULL") == "1"
        self.__recorder = None
        self.__recording_path = None
        self.__screens = []            # [(x,y,w,h)] of every monitor, set from main() (GUI thread)
        os.makedirs(SHOTS_DIR, exist_ok=True)

    def set_screens(self, screens):
        """Monitor geometries [(x,y,w,h)] — kept for reference/debug; recording uses the app window rect."""
        self.__screens = list(screens)

    def __window_geometry(self, wid):
        """Absolute client geometry (x,y,w,h) via xwininfo. Preferred over `xdotool getwindowgeometry`,
        which on this WM reports Y off by the title-bar height — the recording then starts too low and clips
        the top of the app (Edwin, 2026-07-14). Returns None if it can't be read."""
        try:
            out = subprocess.check_output(
                ["xwininfo", "-id", wid], timeout=3, stderr=subprocess.DEVNULL).decode()
        except Exception:
            return None
        fields = {}
        for line in out.splitlines():
            line = line.strip()
            for key, tag in (("x", "Absolute upper-left X:"), ("y", "Absolute upper-left Y:"),
                             ("w", "Width:"), ("h", "Height:")):
                if line.startswith(tag):
                    try:
                        fields[key] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
        if all(k in fields for k in ("x", "y", "w", "h")):
            return (fields["x"], fields["y"], fields["w"], fields["h"])
        return None

    def __spectracs_windows(self):
        """[(wid, x, y, w, h)] for windows whose title starts with 'Spectracs' — CASE-SENSITIVE. xdotool's
        --name match is case-INsensitive, so a plain '^Spectracs' also grabs Geany's 'spectracsNotes.txt…'
        and the terminal's '.../spectracs/…' path; this second filter keeps only the real app. Geometry comes
        from xwininfo (accurate absolute coords). Skips the tiny helper window."""
        windows = []
        try:
            ids = subprocess.check_output(
                ["xdotool", "search", "--name", "Spectracs"], timeout=3,
                stderr=subprocess.DEVNULL).decode().split()
        except Exception:
            return windows
        for wid in ids:
            try:
                name = subprocess.check_output(
                    ["xdotool", "getwindowname", wid], timeout=3, stderr=subprocess.DEVNULL).decode().strip()
            except Exception:
                continue
            if not name.startswith("Spectracs"):
                continue
            geo = self.__window_geometry(wid)
            if geo is None:
                continue
            x, y, w, h = geo
            if w * h < 100 * 100:                    # skip the 1x1 helper window
                continue
            windows.append((wid, x, y, w, h))
        return windows

    def __main_app_window(self):
        """The largest real Spectracs window (the maximized main window), or None."""
        windows = self.__spectracs_windows()
        if not windows:
            return None
        return max(windows, key=lambda t: t[3] * t[4])

    def __app_window_region(self):
        """The app window's own rectangle (x,y,w,h) for x11grab, so recording captures exactly the app
        wherever it sits. Even dimensions for libx264. None → record the whole desktop."""
        if self.__record_full:
            return None
        window = self.__main_app_window()
        if window is None:
            return None
        _, x, y, w, h = window
        return (x, y, w - (w % 2), h - (h % 2))   # libx264 needs even dimensions

    def bind_prompt(self, emit_fn):
        self.__prompt_emit = emit_fn

    def bind_gate(self, emit_fn):
        self.__gate_emit = emit_fn

    def bind_gate_close(self, emit_fn):
        self.__gate_close_emit = emit_fn

    def bind_app_rect(self, emit_fn):
        self.__app_rect_emit = emit_fn

    def __place_prompter_off_app(self):
        # Once the app window is located, tell the Prompter to sit on a screen that does NOT contain it —
        # the app maximizes on whatever monitor the WM picks (here the 'non-primary' one), which is also the
        # Prompter's default, so without this they overlap and the Prompter gets filmed.
        window = self.__main_app_window()
        if window is not None:
            _, x, y, w, h = window
            self.__app_rect_emit(x, y, w, h)

    # --- UDP transport ---

    def __rpc(self, message, expect_reply=True, retries=4, settle=0.15):
        payload = json.dumps(message).encode("utf-8")
        for _ in range(retries):
            self.__sock.sendto(payload, self.__host)
            if not expect_reply:
                time.sleep(settle)
                return None
            try:
                data, _ = self.__sock.recvfrom(8192)
                return json.loads(data)
            except socket.timeout:
                continue
        return None

    # --- app lifecycle ---

    def launch_app(self, extra_args=(), timeout=40):
        if self.__attach:
            # Don't spawn — attach to an app the operator (or bench.sh) already started with --doc-mode.
            # Poll up to `timeout` so it works whether the app is already up or still starting.
            deadline = time.time() + timeout
            while time.time() < deadline:
                reply = self.__rpc({"cmd": "ping"}, retries=1)
                if reply and reply.get("ok"):
                    print("Director: attached to the running app.")
                    self.__place_prompter_off_app()
                    self.start_recording()
                    return
                time.sleep(0.5)
            raise RuntimeError("attach mode: no app answering on %s within %ss — start it with "
                               "'./runApp.sh --doc-mode'" % (self.__host, timeout))
        self.__proc = subprocess.Popen(
            ["./runApp.sh", "--doc-mode", *extra_args], cwd=REPO_ROOT)
        deadline = time.time() + timeout
        while time.time() < deadline:
            reply = self.__rpc({"cmd": "ping"}, retries=1)
            if reply and reply.get("ok"):
                print("Director: app is up.")
                time.sleep(1.0)
                self.__place_prompter_off_app()
                self.start_recording()
                return
            time.sleep(0.5)
        raise RuntimeError("app did not answer ping within %ss" % timeout)

    def start_recording(self):
        if not self.__record or self.__recorder is not None:
            return
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.__recording_path = os.path.join(RECORDINGS_DIR, "%s_%s.mp4" % (self.__record_name, stamp))
        display = os.environ.get("DISPLAY", ":0")
        region = self.__app_window_region()
        if region is not None:
            x, y, width, height = region
            grab_input = "%s+%d,%d" % (display, x, y)   # x11grab region offset = the app window
            print("Director: recording app window %dx%d @ +%d,%d" % (width, height, x, y))
        else:
            width, height = pyautogui.size()
            grab_input = display
        try:
            self.__recorder = subprocess.Popen(
                ["ffmpeg", "-y", "-f", "x11grab", "-framerate", "25",
                 "-video_size", "%dx%d" % (width, height), "-i", grab_input,
                 "-codec:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                 self.__recording_path],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Director: recording screen -> %s" % self.__recording_path)
        except FileNotFoundError:
            print("Director: ffmpeg not found — skipping screen recording (screenshots still saved).")
            self.__recorder = None

    def stop_recording(self):
        if self.__recorder is None:
            return
        try:
            self.__recorder.communicate(input=b"q", timeout=10)  # 'q' tells ffmpeg to finalise the mp4
        except Exception:
            self.__recorder.terminate()
        print("Director: saved video -> %s" % self.__recording_path)
        self.__recorder = None

    def finish(self):
        self.set_hint("Recording complete.")
        self.__prompt_emit("Scenario complete.")
        time.sleep(1.5)
        self.stop_recording()
        if self.__proc is not None:      # only terminate an app WE launched; never the operator's in attach mode
            self.__proc.terminate()

    # --- narration ---

    def set_hint(self, text):
        """Set the caption zone of the app's doc panel (viewer-facing; alias of doc(caption=…))."""
        self.__rpc({"cmd": "set_hint", "text": text}, expect_reply=False)

    def doc(self, use_case=None, outline=None, phase=None, caption=None, reveal=None, wpm=None):
        """Update the 3-zone doc panel (§16.4). Only non-None zones change; `caption` animates app-side."""
        message = {"cmd": "doc", "wpm": wpm or self.__wpm}
        for key, value in (("use_case", use_case), ("outline", outline),
                           ("phase", phase), ("caption", caption), ("reveal", reveal)):
            if value is not None:
                message[key] = value
        self.__rpc(message, expect_reply=False, settle=0.05)

    def narrate(self, text):
        """Reveal `text` in the caption zone (progressive) and hold for its reading time (§16.5).

        Register contract (§16.0 both-layers decision): this is the narrated *why*; the app's own
        status-bar coach line carries the terse imperative. Author narration so the two never echo."""
        self.doc(caption=text, reveal="auto")
        words = max(1, len(text.split()))
        dwell = max(self.__min_dwell, words / max(60.0, self.__wpm) * 60.0) * self.__speed
        time.sleep(dwell)

    def prompt(self, text):
        """Update the left Prompter without pausing (operator-facing narration)."""
        self.__prompt_emit(text)

    def wait_for_human(self, text):
        """Show `text` on the Prompter and BLOCK until the operator advances (hotkey / Space-Enter / CONTINUE)."""
        self.__prompt_emit(text)
        self.__gate_emit()          # raise + focus + ENABLE the Prompter's CONTINUE for this gate
        self.__continue.clear()
        self.__continue.wait()
        self.__gate_close_emit()    # gate satisfied (button / shortcut / hotkey) → disable CONTINUE again

    # --- scripted login (§16.8) ---

    def credentials(self, scenario):
        """(username, password) from director.ini [scenario], or (None, None) if absent."""
        if self.__config.has_section(scenario):
            section = self.__config[scenario]
            return section.get("username"), section.get("password")
        return None, None

    def login(self, scenario, landing=None):
        """Drive the visible login form from director.ini [scenario] (§16.8). Falls back to a human gate
        when no username/password is configured (e.g. before the operator fills the unversioned ini)."""
        username, password = self.credentials(scenario)
        if not username or not password:
            # Human-login fallback: nav to the login form first so it's visible for the operator — the cover
            # card may be current at this point (§18.1 order), which would otherwise hide the form.
            self.nav("LoginViewModule")
            self.wait_for_human("Log in to the app, then press Ctrl+Shift+ß to continue.")
            return
        self.nav("LoginViewModule")
        self.set_hint("Signing in as %s…" % username)
        self.click("LoginViewModule.usernameField")
        self.type_text(username)
        self.click("LoginViewModule.passwordField")
        self.type_text(password)
        self.click("LoginViewModule.loginButton")
        if landing is not None:
            self.wait_ready(landing, visible=True, timeout=20)
        else:
            time.sleep(1.5)

    # --- navigation & interaction ---

    def nav(self, view):
        reply = self.__rpc({"cmd": "nav", "view": view})
        if not (reply and reply.get("ok")):
            raise RuntimeError("nav to %r failed: %r" % (view, reply))
        time.sleep(0.8)

    def cover(self, label=None, points=None, hold=None, wpm=None):
        """Show the doc title card — a page in the MainViewModule stack — with breadcrumb
        `Documentation › <label>` (SPEC_doc_automation §18.1, C1c). No explicit hide: the scenario's next
        `nav` switches the stack away. Showing it after login also performs the CAMERA HANDOFF — the prior
        view's hideEvent releases /dev/video0 — so the measurements-overview (Home) is never filmed.

        `points` (list) types an overview agenda in char-by-char, app-side, at `wpm` (§18.7 CR-B). `hold`
        blocks this thread so the card stays on screen; if omitted it defaults to a short settle, OR — when
        `points` are given — to the agenda's typing time (so the agenda reliably finishes before the next
        step), keeping the Director paced with the app-side typewriter."""
        wpm = wpm or self.__wpm
        reply = self.__rpc({"cmd": "cover", "show": True, "label": label, "points": points, "wpm": wpm})
        if not (reply and reply.get("ok")):
            raise RuntimeError("cover %r failed: %r" % (label, reply))
        if hold is None:
            hold = self.__agenda_dwell(points, wpm) if points else 0.8
        time.sleep(hold)

    def __agenda_dwell(self, points, wpm):
        # Mirror the app-side typewriter cadence (TypewriterLabel: 60000/wpm/CHARS_PER_WORD ms per char, with
        # a 20 ms floor) so the Director waits ~exactly as long as the agenda takes to type, plus a read tail.
        lines = ["•  %s" % str(point).strip() for point in points]
        chars = sum(len(line) for line in lines) + max(0, len(lines) - 1)  # + the joining newlines
        per_char_s = max(0.020, 60.0 / max(60.0, wpm) / 5.0)
        return max(3.0, chars * per_char_s + 1.5)

    def click(self, name, tab=None, duration=1.1):
        # Glide the REAL cursor to the widget (visible, for the video), then trigger it programmatically
        # over UDP (reliable — never depends on pixel-precise landing or window focus). SPEC §3.
        message = {"cmd": "locate", "name": name}
        if tab is not None:
            message["tab"] = tab
        reply = self.__rpc(message)
        if not (reply and reply.get("ok")):
            raise RuntimeError("locate %r failed: %r" % (name, reply))
        self.__raise_app()
        time.sleep(0.2)
        glide = max(0.2, duration * self.__speed)   # cursor glide scales with DOC_SPEED (§16.5)
        pyautogui.moveTo(reply["cx"], reply["cy"], duration=glide, tween=pyautogui.easeInOutQuad)
        time.sleep(0.2)
        activated = self.__rpc({"cmd": "activate", "name": name, "tab": tab})
        if not (activated and activated.get("ok")):
            raise RuntimeError("activate %r failed: %r" % (name, activated))
        time.sleep(0.4)

    def go_to_tab(self, name, index, activate=True, duration=1.1):
        """Glide the visible cursor to a tab HEADER; SWITCH to it only if `activate` (SPEC §18.2, C2a).
        With activate=False the cursor visits the tab for continuity but issues no click — used for the tab
        already shown on phase entry, where a click would be a visible no-op. This is the `point` primitive
        the spec mentions (glide, don't activate)."""
        reply = self.__rpc({"cmd": "locate", "name": name, "tab": index})
        if not (reply and reply.get("ok")):
            raise RuntimeError("locate %r tab %r failed: %r" % (name, index, reply))
        self.__raise_app()
        time.sleep(0.2)
        glide = max(0.2, duration * self.__speed)
        pyautogui.moveTo(reply["cx"], reply["cy"], duration=glide, tween=pyautogui.easeInOutQuad)
        time.sleep(0.2)
        if activate:
            activated = self.__rpc({"cmd": "activate", "name": name, "tab": index})
            if not (activated and activated.get("ok")):
                raise RuntimeError("activate %r tab %r failed: %r" % (name, index, activated))
        time.sleep(0.4)

    def dismiss(self):
        """Dismiss any open in-window dialog (e.g. a capture-fail modal) so it can't wedge the run (§7.1).
        Harmless when nothing is open — returns {dismissed:false}."""
        return self.__rpc({"cmd": "dismiss"})

    def tabs(self, name):
        """Return the step-tab labels of the named QTabWidget (in order), or [] (§16 `tabs` command)."""
        labels, _current = self.__tabs_state(name)
        return labels

    def __tabs_state(self, name):
        """(labels, current_index) of the named QTabWidget, or ([], 0). The `tabs` reply already carries
        `current` (C2a) — surface it so walk_tabs can skip the already-shown tab."""
        reply = self.__rpc({"cmd": "tabs", "name": name})
        if reply and reply.get("ok"):
            return reply.get("labels", []), reply.get("current", 0)
        return [], 0

    def walk_tabs(self, name, narration=None, on_tab=None, screenshot=None):
        """Walk EVERY step-tab of the named QTabWidget, describing each — so a whole phase's steps are shown,
        not just the first (Edwin). Caption per tab = narration[label], else the label itself. `on_tab(label,
        index)` runs after each tab is shown (e.g. to describe the metric fields on Metrics).

        C2a: the tab already shown on entry is glide-to-pointed (cursor visits, no click) — clicking the
        active tab is a visible no-op. `shown` is tracked (not fixed to the entry index) so a phase entered on
        a non-zero tab still shows every tab."""
        labels, shown = self.__tabs_state(name)
        for index, label in enumerate(labels):
            self.go_to_tab(name, index, activate=(index != shown))
            shown = index
            self.narrate((narration or {}).get(label, label))
            if on_tab is not None:
                on_tab(label, index)
            if screenshot is not None:
                slug = "".join(ch if ch.isalnum() else "_" for ch in label.lower())
                self.screenshot("%s_%02d_%s" % (screenshot, index, slug))
        return labels

    def type_text(self, text, interval=0.06):
        pyautogui.write(text, interval=interval)

    def wait_ready(self, name, timeout=30, poll=0.25, **state):
        deadline = time.time() + timeout
        while time.time() < deadline:
            reply = self.__rpc({"cmd": "wait", "name": name, **state})
            if reply and reply.get("ok"):
                return
            time.sleep(poll)
        raise RuntimeError("wait_ready(%r, %r) timed out after %ss" % (name, state, timeout))

    def wait_capture(self, name, started_timeout=6, done_timeout=90):
        """Block until a capture — auto-exposure AND the multi-frame burst — FULLY completes (SPEC §18.3, C3b).

        The capture button disables for the whole capture (CapturePanel `__capturing`, C3a): wait for it to go
        disabled (capture STARTED), then enabled (DONE). The 'started' wait is short and NON-raising because a
        very fast capture can finish before we sample the disabled edge — in that case we fall straight through
        to the 'done' wait rather than aborting the scenario. Fixes the old `wait_ready(enabled=True)`, which
        returned mid-burst (or instantly, for the never-disabled SAMPLE capture)."""
        try:
            self.wait_ready(name, enabled=False, timeout=started_timeout)
        except RuntimeError:
            pass   # never caught the disabled edge (capture already finished) — proceed to the done wait
        self.wait_ready(name, enabled=True, timeout=done_timeout)

    def sleep(self, seconds):
        time.sleep(seconds)

    def screenshot(self, name):
        path = os.path.join(SHOTS_DIR, "%s.png" % name)
        try:
            pyautogui.screenshot(path)
            print("Director: screenshot -> %s" % path)
        except Exception as exception:
            print("Director: screenshot %r failed (%s)" % (name, exception))

    def __raise_app(self):
        # Activate ONLY the real Spectracs main window (by id). A plain 'xdotool search --name ^Spectracs
        # windowactivate' is case-insensitive and would also raise Geany ('spectracsNotes.txt…') or the
        # terminal (repo path), stealing focus from the app.
        window = self.__main_app_window()
        if window is None:
            return
        try:
            subprocess.run(["xdotool", "windowactivate", window[0]],
                           timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def _port_from_argv():
    for arg in sys.argv:
        if arg.startswith("--doc-port="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                pass
    return DEFAULT_PORT


def _install_global_hotkey(continue_event):
    """Primary advance gate (§16.7): a global Ctrl+Shift+ß hotkey via pynput, so advancing never needs the
    mouse or Prompter focus (both invisible to the app-window recording). Returns the listener (keep a
    reference so it isn't GC'd) or None if pynput is absent — the Prompter's Space/Enter is the fallback."""
    try:
        from pynput import keyboard
    except ImportError:
        print("Director: pynput not installed — global hotkey off; use Space/Enter on the Prompter.")
        return None
    # ß under Shift on a German layout emits a different keysym, so <ctrl>+<shift>+ß often never fires;
    # register the configured chord AND reliable alternates (Ctrl+ß without Shift, F9). Any advances a gate.
    configured = os.environ.get("DOC_HOTKEY", "<ctrl>+<shift>+ß")
    wanted = [configured, "<ctrl>+ß", "<f9>"]

    def on_activate():
        print("Director: hotkey → continue")
        continue_event.set()

    mapping = {}
    for chord in wanted:
        if chord in mapping:
            continue
        try:
            keyboard.HotKey.parse(chord)          # validate before adding; a bad chord else kills the whole set
            mapping[chord] = on_activate
        except Exception as exception:
            print("Director: skipping unparseable hotkey %r (%s)" % (chord, exception))
    if not mapping:
        print("Director: no valid global hotkey — use Space/Enter on the Prompter.")
        return None
    try:
        listener = keyboard.GlobalHotKeys(mapping)
        listener.daemon = True
        listener.start()
        print("Director: global hotkey(s) armed: %s" % ", ".join(mapping))
        return listener
    except Exception as exception:
        print("Director: could not arm hotkeys (%s) — use Space/Enter on the Prompter." % exception)
        return None


def main(run_fn, title="Director"):
    """Entry point for a single-scenario file (spec §6.1)."""
    main_chapters([(run_fn, title)])


def main_chapters(chapters):
    """Run one or more (run_fn, title) chapters back-to-back against one app launch (spec §12)."""
    app = QApplication(sys.argv)
    continue_event = threading.Event()
    director = Director(continue_event, port=_port_from_argv())
    # Hand the Director every monitor's geometry so it can record only the one the app window sits on
    # (detected via xdotool at record time) — the video is just the app + hint panel, not the left
    # Prompter. DOC_RECORD_FULL=1 records the whole desktop instead.
    director.set_screens([(s.geometry().x(), s.geometry().y(), s.geometry().width(), s.geometry().height())
                          for s in QGuiApplication.screens()])
    prompter = Prompter()

    def run_all(d):
        first = True
        for run_fn, title in chapters:
            d.set_hint("— %s —" % title)
            if not first:
                d.nav("Home")
            first = False
            run_fn(d)

    scenario = Scenario(run_all, director)
    director.bind_prompt(scenario.promptChanged.emit)
    director.bind_gate(scenario.gateOpened.emit)
    director.bind_gate_close(scenario.gateClosed.emit)
    director.bind_app_rect(scenario.appRect.emit)
    scenario.promptChanged.connect(prompter.set_instruction)
    scenario.gateOpened.connect(prompter.raise_and_focus)
    scenario.gateClosed.connect(lambda: prompter.set_gate_active(False))
    scenario.appRect.connect(prompter.place_avoiding)
    prompter.continued.connect(continue_event.set)
    scenario.finished.connect(app.quit)

    hotkey = _install_global_hotkey(continue_event)   # kept referenced for the app lifetime (no GC)

    # Never orphan the ffmpeg recorder (Edwin): stop it on ANY Director exit — normal, exception, or a kill
    # signal (Ctrl-C / terminal close). atexit covers the normal/exception paths; the signal handlers cover
    # SIGINT/SIGTERM/SIGHUP. A slow QTimer lets Python actually run the handler during Qt's C++ event loop.
    atexit.register(director.stop_recording)

    def _on_signal(_signum, _frame):
        director.stop_recording()
        app.quit()

    for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(_sig, _on_signal)
        except (ValueError, OSError):
            pass
    _sigTimer = QTimer()
    _sigTimer.start(400)
    _sigTimer.timeout.connect(lambda: None)   # wake the interpreter so queued Python signals are delivered

    prompter.show()
    prompter.place()                                  # force position now that it's mapped…
    QTimer.singleShot(300, prompter.place)            # …and again after the WM has settled (defeat re-centre)
    scenario.start()
    app.exec()
    if hotkey is not None:
        hotkey.stop()
