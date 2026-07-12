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

import pyautogui
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS_DIR = os.path.join(REPO_ROOT, "automation", "screenshots")
RECORDINGS_DIR = os.path.join(REPO_ROOT, "automation", "recordings")
DEFAULT_PORT = 5555

pyautogui.FAILSAFE = True   # slam the cursor into a screen corner to abort a runaway run
pyautogui.PAUSE = 0.1


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
            "font-size: 22px; padding: 20px; background-color: #2E7D32; color: white; border-radius: 8px;")
        self.__button.clicked.connect(self.continued.emit)
        layout.addWidget(self.__button)

        self.setStyleSheet("QDialog { background: #1E1E1E; }")
        self.__placeOnPrompterScreen()

    def __placeOnPrompterScreen(self):
        # Put the Prompter on a screen the app does NOT occupy: the app maximizes on the primary screen,
        # so prefer a non-primary screen (dual-monitor). Falls back to the primary if there's only one.
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        target = next((s for s in screens if s is not primary), primary)
        geo = target.geometry() if target else None
        w, h = 480, 360
        if geo is not None:
            x = geo.x() + (geo.width() - w) // 2
            y = geo.y() + (geo.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.resize(w, h)

    def set_instruction(self, text):
        self.__instruction.setText(text)


class Scenario(QThread):
    """Runs the scenario `run(director)` off the GUI thread (spec §6.1)."""

    promptChanged = Signal(str)

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
        self.__proc = None
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

    def __app_window_region(self):
        """Return the app window's own rectangle (x,y,w,h) via xdotool, so recording captures exactly the
        app wherever it sits (no monitor guessing). Picks the LARGEST '^Spectracs' window (the maximized
        main window, not a transient). Even dimensions for libx264. None → record the whole desktop."""
        if self.__record_full:
            return None
        try:
            ids = subprocess.check_output(
                ["xdotool", "search", "--name", "^Spectracs"], timeout=3,
                stderr=subprocess.DEVNULL).decode().split()
            best = None
            for wid in ids:
                out = subprocess.check_output(
                    ["xdotool", "getwindowgeometry", "--shell", wid], timeout=3,
                    stderr=subprocess.DEVNULL).decode()
                pos = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
                x, y, w, h = int(pos["X"]), int(pos["Y"]), int(pos["WIDTH"]), int(pos["HEIGHT"])
                if best is None or w * h > best[2] * best[3]:
                    best = (x, y, w, h)
            if best is not None:
                x, y, w, h = best
                return (x, y, w - (w % 2), h - (h % 2))   # libx264 needs even dimensions
        except Exception:
            pass
        return None

    def bind_prompt(self, emit_fn):
        self.__prompt_emit = emit_fn

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
        """Update the app's right-side hint panel (viewer-facing)."""
        self.__rpc({"cmd": "set_hint", "text": text}, expect_reply=False)

    def prompt(self, text):
        """Update the left Prompter without pausing (operator-facing narration)."""
        self.__prompt_emit(text)

    def wait_for_human(self, text):
        """Show `text` on the Prompter and BLOCK until the operator clicks CONTINUE."""
        self.__prompt_emit(text)
        self.__continue.clear()
        self.__continue.wait()

    # --- navigation & interaction ---

    def nav(self, view):
        reply = self.__rpc({"cmd": "nav", "view": view})
        if not (reply and reply.get("ok")):
            raise RuntimeError("nav to %r failed: %r" % (view, reply))
        time.sleep(0.8)

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
        pyautogui.moveTo(reply["cx"], reply["cy"], duration=duration, tween=pyautogui.easeInOutQuad)
        time.sleep(0.2)
        activated = self.__rpc({"cmd": "activate", "name": name, "tab": tab})
        if not (activated and activated.get("ok")):
            raise RuntimeError("activate %r failed: %r" % (name, activated))
        time.sleep(0.4)

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
        # Activate ONLY the Spectracs app window. The app's title always starts with "Spectracs"
        # (e.g. "Spectracs > Measurement"), so anchor the regex to the start — a plain substring match
        # (wmctrl -a) also grabs the terminal, whose title contains the repo path ".../spectracs/...".
        try:
            subprocess.run(["xdotool", "search", "--name", "^Spectracs", "windowactivate"],
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
    scenario.promptChanged.connect(prompter.set_instruction)
    prompter.continued.connect(continue_event.set)
    scenario.finished.connect(app.quit)

    prompter.show()
    scenario.start()
    app.exec()
