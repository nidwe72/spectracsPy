"""The indeterminate ("fade") status bar — SPEC_settled_measurement.md §13.2, rebuilt in §27.23.

⛔ WRITTEN AFTER TWO RIG FINDINGS (2026-08-17). First: `stepsCount = 0` reached
`currentStepIndex / float(stepsCount)` and raised **ZeroDivisionError inside the signal handler**, so the
convention silently did nothing for a whole run. Second: Qt's own busy mode (range 0,0) slides a single
chunk AND swallows the format text — which is the half of §13.2 that carries the state and the turbidity.

⛔⛔ AND THEN A THIRD, WHICH THESE TESTS COULD NOT SEE (§27.23/P1). Edwin, at the rig: "I do not see
stripes: just the colors changing". The stylesheet was right all along — the app's OWN global sheet carried
`QProgressBar::chunk { width: 1px }`, which makes Qt tile the chunk in 1-pixel segments and map the
gradient into EACH one, so the whole bar painted the gradient's first colour. Every assertion here was on
the stylesheet STRING, so all of them passed while the bar was visibly flat.
⇒ `test_the_gradient_survives_the_application_stylesheet` RENDERS the widget and counts colours. It is the
only test in this file that can fail if `width: 1px` ever comes back.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule


def statusBar(withApplicationStyle=False):
    application = QApplication.instance() or QApplication([])
    # ⚠ The application sheet is what broke the picture, so a test that wants the REAL appearance has to
    # opt into it; the others deliberately keep the widget isolated.
    application.setStyleSheet(
        ApplicationStyleLogicModule().getApplicationStyleSheet() if withApplicationStyle else "")
    return MainStatusBarViewModule()


def signalOf(text, stepsCount=0, currentStepIndex=0):
    signal = ApplicationStatusSignal()
    signal.isStatusReset = False
    signal.stepsCount = stepsCount
    signal.currentStepIndex = currentStepIndex
    signal.text = text
    return signal


def animationOf(bar):
    return getattr(bar, "_fadeAnimation", None)


def distinctColoursAcross(widget, width=400):
    # ⛔ THE TEXT HAS TO GO FIRST, and forgetting that made this assertion useless on its first attempt:
    # the format string is drawn across the middle of the bar and its ANTIALIASED glyph pixels contribute
    # ~20 distinct colours all by themselves — enough to sail past any "is there a gradient?" threshold
    # while the chunk behind them was provably flat. Measured: 26 colours with the defect still in place.
    visible = widget.isTextVisible()
    widget.setTextVisible(False)
    try:
        widget.resize(width, 22)
        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
    finally:
        widget.setTextVisible(visible)
    image = pixmap.toImage()
    row = image.height() // 2
    return {image.pixelColor(x, row).name() for x in range(image.width())}


def test_an_unknown_end_animates_and_KEEPS_its_text():
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …   turbidity 0.0719  -0.0042/min"))

    assert bar.progressBar.format() == "clearing …   turbidity 0.0719  -0.0042/min", \
        "⛔ the state and the turbidity are the message — Qt's busy mode drops them"
    # Range 0..100 rather than (0,0): busy mode would animate for us but return "" from text().
    assert (bar.progressBar.minimum(), bar.progressBar.maximum()) == (0, 100)
    assert animationOf(bar) is not None and animationOf(bar).state() == animationOf(bar).State.Running
    assert "qlineargradient" in bar.progressBar.styleSheet()


def test_the_motion_is_the_VALUE_and_the_sheet_is_written_once():
    # ⭐ THIS INVERTS THE OLD ASSERTION (§27.23/P9). The stripes could only move by re-applying the
    # stylesheet 14x/s — a full style re-polish per tick — because Qt stylesheets have no animation. The
    # fade animates the bar's own `value` instead, so the sheet is written ONCE and never again.
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    sheet = bar.progressBar.styleSheet()
    animation = animationOf(bar)

    animation.setCurrentTime(0)
    start = bar.progressBar.value()
    animation.setCurrentTime(animation.duration() // 2)
    middle = bar.progressBar.value()

    assert start != middle, "the fade did not move the bar's value"
    assert bar.progressBar.styleSheet() == sheet, "the stylesheet was rewritten to animate — that is the old way"

    bar.handleApplicationStatusSignal(signalOf("clearing … still"))
    assert bar.progressBar.styleSheet() == sheet, "a second status signal rebuilt the sheet"


def test_the_gradient_survives_the_application_stylesheet():
    # ⛔⛔ §27.23/P1 — THE TEST THE OTHERS COULD NOT BE. With the app-global `chunk { width: 1px }` in
    # place this rendered as ONE flat colour while every string assertion above still passed. Measured
    # then: 1 distinct colour. Measured now: >8, i.e. an actual gradient.
    bar = statusBar(withApplicationStyle=True)
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    bar.progressBar.setValue(60)

    colours = distinctColoursAcross(bar.progressBar)
    assert len(colours) > 8, \
        "the chunk gradient collapsed to %d colour(s) — has `width` come back to QProgressBar::chunk?" \
        % len(colours)


def test_a_KNOWN_end_goes_back_to_a_real_fraction_and_stops_the_animation():
    # ⚠ An animation that outlives its cause reads as "still working" long after it finished — and the
    # plain burst (§10.6) still has a genuine fraction to show.
    # ⛔ It must also stop because it DRIVES `value` itself: left running it would fight every setValue
    # on the determinate path (§27.23/P6).
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    bar.handleApplicationStatusSignal(signalOf("Capturing sample frame 30 / 60", stepsCount=60,
                                               currentStepIndex=30))

    assert bar.progressBar.value() == 50
    assert animationOf(bar) is None
    assert "qlineargradient" not in bar.progressBar.styleSheet()


def test_a_status_reset_also_stops_the_animation():
    bar = statusBar()
    bar.handleApplicationStatusSignal(signalOf("clearing …"))
    reset = ApplicationStatusSignal()
    reset.isStatusReset = True
    bar.handleApplicationStatusSignal(reset)

    assert animationOf(bar) is None
    assert bar.progressBar.value() == 0


def test_guidance_text_is_still_a_plain_amber_line_not_a_bar():
    # ⚠ SPEC_acquisition_guidance's coach line has stepsCount 0 too, and it must NOT start animating.
    bar = statusBar()
    guidance = signalOf("Insert the oil dilution and capture")
    guidance.guidance = True
    bar.handleApplicationStatusSignal(guidance)

    assert animationOf(bar) is None
    assert "qlineargradient" not in bar.progressBar.styleSheet()
