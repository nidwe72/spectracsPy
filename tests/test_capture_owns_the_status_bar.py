"""A capture owns the status bar from the click to its end — SPEC_settled_measurement.md §27.23/P4 (B2).

⛔⛔ THE BUG. Edwin, at the rig: "the blinking progress bar … stops blinking for about 10 seconds and then
starts blinking again". §27.10 made the bar start at the CLICK, but three older emitters still took it
away again mid-capture — and the worst of them reset it outright: `__onAutoExposeFinished` called
`__clearStatus()`, so "ready for action…" appeared on screen while the instrument was still measuring.

⭐ THE RULE. A sub-step may REFINE the bar — the auto-exposure sweep has a real n/N fraction, and showing
it beats animating — but it must hand ownership BACK, never drop it.
⚠ AND AE ALSO RUNS ON ITS OWN, from the checkbox, where resetting IS right (P5). So the fix is a
condition, and this test pins both halves of it.

⚠ Follows `tests/test_dn_guard_window.py`: `CapturePanel` needs a camera and cannot be constructed
offscreen (§9.5), so the method is called UNBOUND against a lightweight stand-in.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_capture_owns_the_status_bar.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.view.spectral.workflow.CapturePanel import CapturePanel

_onAutoExposeFinished = getattr(CapturePanel, "_CapturePanel__onAutoExposeFinished")


class _Slider:
    def __init__(self):
        self.value = None

    def setValue(self, value):
        self.value = value


class _Panel:
    """Only what `__onAutoExposeFinished` touches — no widget, no camera."""

    # the two status emitters are the REAL ones: this test is about which signal reaches the bar
    _CapturePanel__emitIndeterminate = getattr(CapturePanel, "_CapturePanel__emitIndeterminate")
    _CapturePanel__clearStatus = getattr(CapturePanel, "_CapturePanel__clearStatus")

    def __init__(self, capturing):
        self._CapturePanel__exposureSlider = _Slider()
        self._CapturePanel__autoExposing = True
        self._CapturePanel__capturing = capturing

    def _CapturePanel__updateControls(self):
        pass


class CaptureOwnsTheStatusBarTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def __recorded(self, capturing):
        signals = []
        # ⚠ ONE slot object, kept in a variable: `signals.append` builds a NEW bound method on every
        # attribute access, so connecting and disconnecting the expression hands Qt two different objects
        # and the disconnect raises.
        record = signals.append
        provider = ApplicationContextLogicModule().getApplicationSignalsProvider()
        provider.applicationStatusSignal.connect(record)
        try:
            _onAutoExposeFinished(_Panel(capturing=capturing), 240)
        finally:
            provider.applicationStatusSignal.disconnect(record)
        return signals

    def test_during_a_capture_the_sweep_hands_the_bar_BACK(self):
        signals = self.__recorded(capturing=True)

        self.assertTrue(signals, "the sweep finished and said nothing at all")
        self.assertFalse(any(signal.isStatusReset for signal in signals),
                         "⛔ the bar was reset to 'ready for action…' in the middle of a capture")
        # handed back to the capture's own indeterminate state: stepsCount 0 is the "no knowable end"
        # convention the fade answers (§13.2), and the text says what is being waited for.
        self.assertTrue(any(signal.stepsCount == 0 and signal.text for signal in signals),
                        "the capture did not get its indeterminate bar back")

    def test_a_STANDALONE_sweep_still_resets_the_bar(self):
        # ⚠ P5 — the auto-exposure checkbox runs the sweep with no capture around it, and then "ready for
        # action…" is exactly the right thing to show. An unconditional fix would have broken this.
        signals = self.__recorded(capturing=False)

        self.assertTrue(any(signal.isStatusReset for signal in signals),
                        "a standalone sweep left its progress on the bar")

    def test_the_landed_exposure_still_reaches_the_slider_either_way(self):
        # ⚠ The status change must not have disturbed what the handler is actually for.
        for capturing in (True, False):
            panel = _Panel(capturing=capturing)
            _onAutoExposeFinished(panel, 240)
            self.assertEqual(240, panel._CapturePanel__exposureSlider.value)
            self.assertFalse(panel._CapturePanel__autoExposing)


if __name__ == "__main__":
    unittest.main()
