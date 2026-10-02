"""
P4 of SPEC_lamp_switch.md §7.1 — the lamp goes off on every exit path the app can see.

Each case starts tests/fakes/lamp_exit_child.py in a SUBPROCESS (an exit is not something a test can do to its
own process), lets it switch the lamp on through the real threaded LampService against a FakeShellyServer in
this process, ends it one way, and checks the fake plug received `off`. `twice` checks shutdown is idempotent.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_lamp_exit_hooks.py -q
"""
import os
import signal
import subprocess
import sys
import time
import unittest

from fakes.FakeShellyServer import FakeShellyServer

CHILD = os.path.join(os.path.dirname(__file__), "fakes", "lamp_exit_child.py")


class LampExitHooksTest(unittest.TestCase):

    def runChild(self, mode, sendSignal=None):
        with FakeShellyServer() as plug:
            env = dict(os.environ, SPECTRACS_LAMP_HOST=plug.host, QT_QPA_PLATFORM="offscreen")
            child = subprocess.Popen([sys.executable, CHILD, mode], env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
            try:
                line = child.stdout.readline()
                self.assertEqual("READY", line.strip(), child.stderr.read() if not line else line)
                # the on-command, not plug.output: 'quit' may already have switched off by the time we look
                self.assertTrue([p for p in plug.callsTo("Switch.Set") if p.get("on") == "true"])
                if sendSignal is not None:
                    child.send_signal(sendSignal)
                child.wait(timeout=15)
            finally:
                if child.poll() is None:
                    child.kill()
                child.stdout.close()
                child.stderr.close()
            time.sleep(0.1)
            self.assertFalse(plug.output, "lamp still on after '%s'" % mode)
            return plug

    def test_app_quit(self):
        self.runChild("quit")

    def test_sys_exit(self):
        self.runChild("sys.exit")

    def test_window_close(self):
        self.runChild("close")

    def test_sigterm(self):
        self.runChild("wait", signal.SIGTERM)

    def test_sigint(self):
        self.runChild("wait", signal.SIGINT)

    @unittest.skipUnless(hasattr(signal, "SIGHUP"), "no SIGHUP on this platform")
    def test_sighup(self):
        self.runChild("wait", signal.SIGHUP)

    def test_shutdown_twice_sends_one_off(self):
        plug = self.runChild("twice")
        self.assertEqual(1, len(plug.offCalls()))


if __name__ == "__main__":
    unittest.main()
