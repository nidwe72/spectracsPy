"""P2b — the plugin's ClearingEvaluator, replayed on the 2026-08-14 curve.

⭐⭐ THE ACCEPTANCE GATE OF SPEC_settled_measurement.md §14.3: §2.1's criterion was derived as
"|ΔA_valley| < 0.005 between samples 3 MINUTES apart, twice running", and it fired at t ≈ 16.7 on jar B.
The shipped form is a RATE (0.0017/min) compared across j = 2 non-overlapping windows. ⇒ the rate form
must land on the SAME sample. If it does not, the conversion is wrong and nothing in §14 may be trusted.

⚠ The 2026-08-14 run is a CSV of 3-minute band means, not frames (§11.9b) — so this drives `decide()`
directly with synthetic rows, which is exactly the point: the risky arithmetic is the gate, the branch
and the vertex, and none of them need a camera.
"""
import pytest

from sciens.spectracs.plugin_sdk import MonitorMode, MonitorOutcome
from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator


class Row:
    """A stand-in for MonitorRow — the evaluator only reads t / values / isDecisionRow / provisional."""

    def __init__(self, minutes, valley, qPercent, soret=0.61):
        self.t = minutes * 60.0
        self.isDecisionRow = True
        self.provisional = False
        self.values = {"valley": valley, "qPercent": qPercent, "soret": soret,
                       "qBand": valley + qPercent * soret / 100.0}

    def get(self, key, default=None):
        return self.values.get(key, default)


# ⭐⭐ THE REAL RUN, not an approximation of it: jar B, 2026-08-14 Lugitsch, as written by
# `diagnostics/clearing_time_course.py` (minutes, aValley, qPercent). A_valley falls 97 %
# (0.9455 -> 0.0257) and Q% reaches its minimum of 13.2744 at t = 16.655 — the two numbers
# SPEC_settled_measurement.md §1 quotes. Transcribed here so the test needs no external file.
# ⚠ Samples are ~3.28 min apart, which is a COARSER cadence than the monitor's ~35 s windows — and that
# is deliberate: an algorithm whose gate depends on the sampling rate would pass on live frames and fail
# here, which is exactly the bug the span-based comparison of §14.3 was written to prevent.
JAR_B = [
    (0.275, 0.945454, 26.0574), (3.551, 0.088927, 14.0030), (6.827, 0.045262, 13.4689),
    (10.103, 0.036871, 13.4290), (13.379, 0.030531, 13.3417), (16.655, 0.025733, 13.2744),
    (19.931, 0.027348, 13.3814), (23.207, 0.032076, 13.4737), (26.483, 0.031579, 13.5233),
    (29.759, 0.029202, 13.5327), (33.035, 0.028259, 13.5824), (36.311, 0.027629, 13.6370),
    (39.587, 0.026707, 13.7015), (42.863, 0.026643, 13.8602), (46.139, 0.026332, 13.9032),
]


def drive(evaluator, samples):
    """Feed rows one at a time, exactly as the engine would. Returns (rows, decisions)."""
    rows, decisions = [], []
    for minutes, valley, qPercent in samples:
        rows.append(Row(minutes, valley, qPercent))
        decisions.append(evaluator.decide(rows))
    return rows, decisions


def firstPromote(decisions):
    for index, decision in enumerate(decisions):
        if decision.promote:
            return index, decision
    return None, None


def evaluatorFor(mode=MonitorMode.PRODUCT, windowFrames=60):
    # The evaluator needs no plugin instance for decide() — only evaluate() touches the plugin.
    # ⚠ W IS PASSED EXPLICITLY (§30.4): the depth threshold is 2σ of ONE window, and W is the operator's
    # Frames combo, not a constant. A test whose threshold follows a default is a test that has quietly
    # stopped being about the threshold.
    return ClearingEvaluator(plugin=None, reference=None, mode=mode, windowFrames=windowFrames)


def atTheta(theta):
    """Run the evaluator at a given θ. ⚠ θ is a CHOICE (§27.26/M2); the equivalences below are properties
    of the rate FORM, and each has to be asserted at the θ it is about."""
    import contextlib

    @contextlib.contextmanager
    def scoped():
        original = ClearingEvaluator.THETA_PER_MINUTE
        ClearingEvaluator.THETA_PER_MINUTE = theta
        try:
            yield
        finally:
            ClearingEvaluator.THETA_PER_MINUTE = original
    return scoped()


def gateMinutesOf(rows, decisions):
    return next((rows[position].t / 60.0
                 for position, item in enumerate(decisions) if item.note and "gate fired" in item.note), None)


def test_the_rate_form_reproduces_the_2026_08_14_criterion():
    # ⭐⭐ §14.3's acceptance test. The criterion this replaces (|ΔA_valley| < 0.005 between consecutive
    # 3-minute samples, twice running) has its two flat steps at 16.655 and 19.931 on this curve, so it
    # is CONFIRMED at 19.931. The rate form must land on the same sample — not earlier (it would settle a
    # fill that is still clearing) and not later (every extra sample is dose).
    #
    # ⚠ ASSERTED AT θ = 0.0017, WHICH IS THE θ THIS EQUIVALENCE IS ABOUT: 0.0017 IS §2.1's "0.005 per
    # 3-minute sample" re-expressed as a rate, so the two criteria are the same statement and must agree.
    # The SHIPPED θ is 0.005 (§27.26/M2) and deliberately fires earlier — pinned in the test below.
    # ⛔ Do not "fix" this test by moving it to the shipped θ: it would then assert nothing at all.
    with atTheta(0.0017):
        evaluator = evaluatorFor()
        rows, decisions = drive(evaluator, JAR_B)
        index, decision = firstPromote(decisions)

    assert index is not None, "the gate never fired on a curve that demonstrably settles"
    gateMinutes = gateMinutesOf(rows, decisions)
    assert gateMinutes == pytest.approx(19.931, abs=0.1), \
        "the gate fired at %.2f min, not at the 19.93 the old criterion confirms" % gateMinutes
    # ⭐ §30.1/§30.6: the branch is chosen by the DEPTH OF THE Q% CURVE, no longer by how far A_valley
    # fell. Jar B's minimum sits 12.783 below its first look — a hundred times the 0.126 threshold — so
    # this is the vertex branch by an enormous margin, and the old justification ("A_valley fell 0.92, far
    # beyond the 0.010 materiality") named a constant that no longer exists.
    assert decision.diagnostics["depth"] == pytest.approx(12.783, abs=0.001)
    assert decision.diagnostics["depthThreshold"] == pytest.approx(0.126, abs=0.001)
    assert decision.branch == "was-clearing"
    assert decision.readAs == "VERTEX"


def test_the_shipped_theta_saves_dose_and_reads_the_SAME_value():
    """θ = 0.005 (§27.26/M2) — what Edwin bought, what it cost, and ⭐⭐ WHO NOW OWNS THE SAVING.

    ⭐ The value is bit-identical at both θ, because θ decides only WHEN TO STOP LOOKING while the read
    decides what is reported.
    ⭐ BOUGHT: the answer arrives at 19.93 min instead of 23.21 — **3.3 minutes less lamp on the sample**.
    ⚠ AND THE §29 READ DID NOT TAKE THIS OVER, though the first cut of it tried to. Reading at the gate row
    on the vertex branch would have saved the same 3.3 minutes here — but replaying run 006 showed what it
    costs elsewhere: at ITS gate the deepest look so far already had a row on its far side, while the true
    minimum was two rows and 0.012 further on. ⇒ the vertex branch still waits one row (§14.4), exactly as
    §29.3 and §30.14 say it must, and the dose saving on this curve remains θ's.
    ⛔ THE COST OF θ = 0.005 IS UNCHANGED AND STILL REAL: the gate fires at ~13.4 min while this fill
    demonstrably keeps clearing until 16.66, so `clearingSeconds` means "when the gate said so", not "when
    the fill stopped clearing" — and it travels in the record as a σ_fill component (§2.4).
    ⛔ Do not "fix" either half by moving it to the other θ; each is asserted at the θ it is about.
    """
    with atTheta(0.0017):
        slowRows, slowDecisions = drive(evaluatorFor(), JAR_B)
        slowIndex, slowDecision = firstPromote(slowDecisions)
    with atTheta(0.005):
        fastRows, fastDecisions = drive(evaluatorFor(), JAR_B)
        fastIndex, fastDecision = firstPromote(fastDecisions)

    # ⭐ the same number...
    assert fastDecision.answer == pytest.approx(slowDecision.answer, abs=1e-9)
    assert fastDecision.answer == pytest.approx(13.2733, abs=0.0001)
    # ...read 3.3 minutes earlier
    assert JAR_B[slowIndex][0] == pytest.approx(23.207, abs=0.1)
    assert JAR_B[fastIndex][0] == pytest.approx(19.931, abs=0.1)
    assert fastDecision.readAs == "VERTEX" and fastDecision.branch == "was-clearing"

    # ⭐ the gate itself is untouched by the new read — it still fires where each θ says it does
    assert gateMinutesOf(slowRows, slowDecisions) == pytest.approx(19.931, abs=0.1)

    # ⛔ the cost: the gate's own claim moves ahead of the physics
    assert gateMinutesOf(fastRows, fastDecisions) == pytest.approx(13.379, abs=0.1), \
        "θ = 0.005 is expected to fire the gate early on this curve — if it no longer does, re-read §27.26"
    trueMinimum = min(JAR_B, key=lambda sample: sample[2])[0]
    assert gateMinutesOf(fastRows, fastDecisions) < trueMinimum, \
        "the documented cost of θ = 0.005 has vanished; the spec's warning needs revisiting"


def test_the_vertex_read_lands_on_the_measured_Q_MINIMUM_not_on_the_gate_row():
    # ⚠ §2.2: the raw minimum of n noisy samples is biased LOW by ~0.9 sd because it SELECTS the most
    # negative excursion; a vertex through three points averages instead.
    # ⛔ AND THE ROW MATTERS: the minimum sits at t = 16.655 while the gate only confirms it at 19.931.
    # Fitting around the GATE row would fit a rising ramp — a parabola with no minimum at all.
    evaluator = evaluatorFor()
    _, decisions = drive(evaluator, JAR_B)
    _, decision = firstPromote(decisions)

    assert decision.answer == pytest.approx(13.2744, abs=0.10), \
        "read %.4f, but the measured minimum is 13.2744" % decision.answer
    assert decision.promoteRow is not None
    assert decision.promoteRow.t / 60.0 == pytest.approx(16.655, abs=0.01), \
        "the promoted row is not the minimum — its spectrum would be the wrong one"


def test_an_ALREADY_CLEAR_fill_settles_immediately_and_is_not_a_lottery():
    # ⛔⛔ §17/D1 — the regression this test exists for. The first draft required `-theta <= rate <= 0`;
    # on a fill whose TRUE rate is zero the measured rate is zero-mean noise, so a signed test rejected
    # ~50 % of comparisons at random and two-consecutive succeeded ~25 % of the time. The fast path
    # would have become a lottery. TEST A is a MAGNITUDE test precisely so this is deterministic.
    evaluator = evaluatorFor()
    wobble = [(0.6, 0.0281, 13.31), (1.2, 0.0276, 13.27), (1.8, 0.0279, 13.35),
              (2.4, 0.0274, 13.30), (3.0, 0.0277, 13.33)]
    rows, decisions = drive(evaluator, wobble)
    index, decision = firstPromote(decisions)

    assert index is not None, "an already-clear fill never settled"
    assert index <= 3, "settled at row %d — the arrived-clear path took too long" % index
    assert decision.branch == "arrived-clear"
    assert decision.readAs == "FIRST_SETTLED_WINDOW"
    assert decision.outcome == MonitorOutcome.SETTLED_IMMEDIATE

    # ⭐⭐ AND IT READS THE FIRST LOOK, NOT THE ROW THE GATE FINISHED ON (§29.1 — the defect this whole
    # section exists for). ⚠ This curve HAS an interior minimum, at row 1 (13.27) — it is simply 0.04
    # deep, well inside the 0.126 noise threshold, so it is correctly rejected as noise rather than
    # promoted to a vertex. The answer is the first look, 13.31.
    assert decision.answer is None, "the clear branch reports a REAL look, never a fitted value (§9.1a)"
    assert decision.promoteRow is rows[0]
    assert decision.promoteRow.get("qPercent") == pytest.approx(13.31, abs=0.001)
    assert decision.diagnostics["depth"] == pytest.approx(0.04, abs=0.001)
    assert decision.diagnostics["depth"] < decision.diagnostics["depthThreshold"]


def test_a_RE_CLOUDING_dip_resets_the_gate_instead_of_settling_at_its_peak():
    # ⛔ §14.5 (Edwin's catch): the holder (~40 C) is cooler than the bath (52 C) and the cloud point is
    # 35-50, so a jar can re-cloud after insertion. At the TOP of that dip the rate passes through zero —
    # "flat" is momentarily true while the sample is at its WORST.
    evaluator = evaluatorFor()
    dip = [(0.6, 0.0310, 13.40), (1.2, 0.0600, 14.20), (1.8, 0.1200, 15.00), (2.4, 0.1900, 15.60),
           (3.0, 0.1950, 15.70), (3.6, 0.1900, 15.60), (4.2, 0.1200, 14.90), (4.8, 0.0700, 14.10),
           (5.4, 0.0400, 13.60), (6.0, 0.0320, 13.45), (6.6, 0.0305, 13.42), (7.2, 0.0301, 13.44),
           (7.8, 0.0299, 13.45), (8.4, 0.0298, 13.46), (9.0, 0.0297, 13.47)]
    rows, decisions = drive(evaluator, dip)
    index, _ = firstPromote(decisions)

    assert index is not None, "the fill re-cleared but the gate never fired"
    # ⭐ At the TOP of the dip (t = 3.6) the rate passes through exactly 0.0, so TEST A alone would call
    # it flat while the sample is at its worst. TEST B must have fired there instead.
    assert any(item.note and "re-clouding" in item.note for item in decisions), \
        "the re-clouding was never detected — TEST B did not fire"
    peakMinutes = 3.0
    assert rows[index].t / 60.0 > peakMinutes + 1.0, \
        "settled at %.1f min — at or near the top of the dip" % (rows[index].t / 60.0)
    assert rows[index].get("valley") < 0.05, "settled while the fill was still cloudy"

    # ⭐⭐ §30.8: TEST B RESETS THE HUNT WINDOW, not merely the gate. Everything before the cloud belongs
    # to a cloudier fill, so the read must not be able to reach back into it — otherwise "the first look"
    # would be 13.40 at t = 0.6, taken before the jar clouded at all, which is the one value on this
    # curve that is neither settled nor comparable.
    _, decision = firstPromote(decisions)
    assert decision.promoteRow.t / 60.0 > peakMinutes, \
        "the read reached back to %.1f min — across the re-clouding event" % (decision.promoteRow.t / 60.0)


def test_DIAGNOSTIC_mode_reads_the_answer_but_does_NOT_stop():
    # ⭐ §11.9c: one algorithm, two stop rules. The 20-minute arc is what §11 needs; the latch (§14.6) is
    # what makes observing past the read safe.
    productDecisions = drive(evaluatorFor(MonitorMode.PRODUCT), JAR_B)[1]
    diagnosticDecisions = drive(evaluatorFor(MonitorMode.DIAGNOSTIC), JAR_B)[1]

    _, productDecision = firstPromote(productDecisions)
    diagnosticIndex, diagnosticDecision = firstPromote(diagnosticDecisions)
    assert productDecision.stop is True
    assert diagnosticDecision.stop is False
    assert firstPromote(productDecisions)[0] == diagnosticIndex, "the READ moved with the mode"


def test_a_fill_that_never_clears_never_promotes():
    # ⛔ §2.5 / §12.3: the cap then ends the run with NEVER_SETTLED and ⛔ no value — the last row is not
    # an answer. (The cap itself is the ENGINE's job; here we only assert the evaluator stays silent.)
    evaluator = evaluatorFor()
    stillFalling = [(minutes, 0.90 - 0.02 * minutes, 20.0 - 0.1 * minutes) for minutes in range(0, 30, 3)]
    _, decisions = drive(evaluator, stillFalling)
    assert firstPromote(decisions)[0] is None


def test_no_provisional_Q_percent_is_offered_to_the_operator():
    # ⛔⛔ §17/U1: a number displayed while it is still moving is a number somebody writes down.
    evaluator = evaluatorFor()
    rows, _ = drive(evaluator, JAR_B[:4])
    coach = evaluator.coach(rows)
    assert "Q%" not in dict(coach["fields"]), "a provisional Q% reached the coach line"
    assert coach["state"] == "clearing …"


def test_the_depth_threshold_is_DERIVED_from_W_and_CLAMPED_below_the_measured_window():
    """§30.4 / §30.5 / §30.15 — the threshold is a function of the Frames combo, and it never grows.

    ⛔ 0.063 is the sd of WHOLE CAPTURES at W = 60 (SPEC_capture_quality §16.36.6), so it already carries
    lamp and auto-exposure drift that does NOT average down with more frames. Scaling it up for a smaller
    window over-states the noise, raises the threshold, and pushes runs onto the "arrived clear" branch —
    which is the ~100x expensive error (+12.783 on jar B against ~0.01 for a false vertex).
    ⇒ it may fall below the measured window, never rise above it.
    """
    assert ClearingEvaluator.depthThresholdFor(60) == pytest.approx(0.126, abs=0.0005)
    assert ClearingEvaluator.depthThresholdFor(80) == pytest.approx(0.1091, abs=0.0005)   # bigger W, finer
    assert ClearingEvaluator.depthThresholdFor(20) == pytest.approx(0.126, abs=0.0005)    # ⛔ clamped
    assert ClearingEvaluator.depthThresholdFor(10) == pytest.approx(0.126, abs=0.0005)    # ⛔ clamped
    # ⚠ Unclamped, W = 20 would ask for 0.218 — and run 004's real 0.149 dip would be called noise.
    assert 2 * ClearingEvaluator.SINGLE_WINDOW_SIGMA * (60.0 / 20) ** 0.5 == pytest.approx(0.218, abs=0.001)
    # ...and the evaluator carries the one it was built with, so the record can state it.
    assert evaluatorFor(windowFrames=20).depthThreshold == pytest.approx(0.126, abs=0.0005)


def test_the_read_WAITS_when_the_minimum_is_still_the_newest_look():
    """§30.3's third exit — the only branch that costs another decision row, and it must be reachable.

    ⭐ The gate can fire before the Q% minimum (§27.26a: at θ = 0.005 jar B's gate fires at 13.38 while the
    fill keeps clearing until 16.66). A minimum with no row on its far side is not a minimum yet, and a run
    that read one would report a value the curve was still moving away from.
    """
    stillFalling = [(1.2, 0.0300, 14.00), (2.4, 0.0298, 13.60), (3.6, 0.0297, 13.20),
                    (4.8, 0.0296, 13.10)]
    rows, decisions = drive(evaluatorFor(), stillFalling)
    assert firstPromote(decisions) == (None, None), "read a minimum that has no far side"
    assert any(item.note and "still the newest look" in item.note for item in decisions), \
        "the run waited, but the record never says why"

    # ...and the moment the far side arrives, it reads the VERTEX around that minimum — not the first look
    _, decisions = drive(evaluatorFor(), stillFalling + [(6.0, 0.0295, 13.30)])
    index, decision = firstPromote(decisions)
    assert decision is not None and decision.readAs == "VERTEX"
    assert decision.promoteRow.t / 60.0 == pytest.approx(4.8, abs=0.01)
