"""The indeterminate ("moving stripes") status bar — SPEC_settled_measurement.md §13.2.

⛔ WRITTEN AFTER TWO RIG FINDINGS (2026-08-17). First: `stepsCount = 0` reached
`currentStepIndex / float(stepsCount)` and raised **ZeroDivisionError inside the signal handler**, so the
convention silently did nothing for a whole run. Second: Qt's own busy mode (range 0,0) slides a single
chunk AND swallows the format text — which is the half of §13.2 that carries the state and the turbidity.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule


def statusBar():
    QApplication.instance() or QApplication([])
    return MainStatusBarViewModule()


def signalOf(text, stepsCount=0, currentStepIndex=0):
    signal = ApplicationStatusSignal()
    signal.isStatusReset = False
    signal.stepsCount = stepsCount
    signal.currentStepIndex = currentStepIndex
    signal.text = text
    return signal


def test_an_unknown_end_animates_and_KEEPS_its_text():
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …   turbidity 0.0719  -0.0042/min"))

    assert bar.progressBar.format() == "clearing …   turbidity 0.0719  -0.0042/min", \
        "⛔ the state and the turbidity are the message — Qt's busy mode drops them"
    # Full bar + a striped chunk, rather than range (0,0): the stripes carry the motion.
    assert (bar.progressBar.minimum(), bar.progressBar.maximum()) == (0, 100)
    assert bar.progressBar.value() == bar.progressBar.maximum()
    assert "qlineargradient" in bar.progressBar.styleSheet()


def test_the_stripes_actually_move():
    # ⚠ Qt stylesheets have no animation, so movement can only come from re-applying the sheet.
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    before = bar.progressBar.styleSheet()
    bar._MainStatusBarViewModule__advanceStripes()
    assert bar.progressBar.styleSheet() != before


def test_a_KNOWN_end_goes_back_to_a_real_fraction_and_stops_the_animation():
    # ⚠ An animation that outlives its cause reads as "still working" long after it finished — and the
    # plain burst (§10.6) still has a genuine fraction to show.
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    bar.handleApplicationStatusSignal(signalOf("Capturing sample frame 30 / 60", stepsCount=60,
                                               currentStepIndex=30))

    assert bar.progressBar.value() == 50
    assert getattr(bar, "_stripeTimer", None) is None
    assert "qlineargradient" not in bar.progressBar.styleSheet()


def test_a_status_reset_also_stops_the_animation():
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    reset = ApplicationStatusSignal()
    reset.isStatusReset = True
    bar.handleApplicationStatusSignal(reset)

    assert getattr(bar, "_stripeTimer", None) is None
    assert bar.progressBar.value() == 0


def test_guidance_text_is_still_a_plain_amber_line_not_a_bar():
    # ⚠ SPEC_acquisition_guidance's coach line has stepsCount 0 too, and it must NOT start animating.
    bar = statusBar()
    guidance = signalOf("Insert the oil dilution and capture")
    guidance.guidance = True
    bar.handleApplicationStatusSignal(guidance)

    assert getattr(bar, "_stripeTimer", None) is None
    assert "qlineargradient" not in bar.progressBar.styleSheet()
