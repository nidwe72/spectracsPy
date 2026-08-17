"""P1a — the SDK monitor parts, driven by a FAKE evaluator and SYNTHETIC timestamps.

⭐ THE POINT OF THE FAKE EVALUATOR (SPEC_settled_measurement.md §10.2): if a monitor with invented band
names works, the engine provably holds no oil knowledge — the composition boundary is real, not asserted.

⭐ THE POINT OF SYNTHETIC TIMESTAMPS (§25/X6): `offer(frame, timestamp)` takes the clock as an ARGUMENT,
so a 90-minute clearing curve replays in milliseconds. `tests/conftest.py` arms a 120 s per-test
watchdog; a monitor test that waited on wall-clock would be either useless or a suite hang.
"""
import numpy as np
import pytest

from sciens.spectracs.plugin_sdk import (BurstEvaluator, FrameRing, MonitorDecision, MonitorEngine,
                                         MonitorOutcome, MonitorPolicy)

FPS = 1.4
BINS = [400.0 + index for index in range(60)]


def frameOf(level, noise=0.0, seed=None):
    generator = np.random.default_rng(seed)
    return {nm: float(level + (generator.normal(0.0, noise) if noise else 0.0)) for nm in BINS}


class FakeEvaluator:
    """Knows nothing about spectroscopy: it reads a made-up scalar and settles when it stops moving."""

    version = "fake-1"
    valueKey = "widget"
    columns = [{"key": "widget", "label": "Widget", "unit": ""},
               {"key": "gate", "label": "Gate", "unit": ""}]

    def __init__(self, settleAfter=3):
        self.settleAfter = settleAfter
        self.decisionCount = 0

    def evaluate(self, spectrum):
        values = list(spectrum.valuesByNanometers.values())
        level = float(np.mean(values))
        return {"widget": level * 10.0, "gate": level}

    def decide(self, rows):
        self.decisionCount += 1
        if self.decisionCount >= self.settleAfter:
            return MonitorDecision(promote=True, stop=True, outcome=MonitorOutcome.SETTLED_IMMEDIATE,
                                   branch="arrived-clear", readAs="FIRST_SETTLED_WINDOW")
        return MonitorDecision.carryOn()


def drive(monitor, frames, startTime=1000.0, fps=FPS):
    """Push frames with SYNTHETIC monotonic timestamps. Returns the rows produced."""
    rows = []
    for index, frame in enumerate(frames):
        row = monitor.offer(frame, startTime + index / fps)
        if row is not None:
            rows.append(row)
        if monitor.isFinished():
            break
    return rows


def test_engine_holds_no_domain_knowledge_and_settles_on_the_fake_scalar():
    policy = MonitorPolicy(windowFrames=10, maxSeconds=600.0)
    monitor = MonitorEngine(FakeEvaluator(settleAfter=3), FrameRing(10, 14), policy)
    drive(monitor, [frameOf(0.5) for _ in range(40)])

    result = monitor.result()
    assert result.outcome == MonitorOutcome.SETTLED_IMMEDIATE
    assert result.hasValue()
    assert result.answer["valueKey"] == "widget"
    assert result.answer["branch"] == "arrived-clear"
    assert result.spectrum is not None            # ⭐ the winning window's mean, promoted OUT of the ring


def test_row_timestamp_is_the_window_CENTRE_not_its_last_frame():
    # ⭐ §9.3: a boxcar of W frames lags by (W-1)/2. Stamping at the last frame displaces every slope,
    # vertex and intercept systematically — a bias, not noise.
    policy = MonitorPolicy(windowFrames=10, maxSeconds=600.0)
    monitor = MonitorEngine(FakeEvaluator(settleAfter=99), FrameRing(10, 14), policy)
    rows = drive(monitor, [frameOf(0.5) for _ in range(10)])

    lastRow = rows[-1]
    expectedCentre = ((0 / FPS) + (9 / FPS)) / 2.0
    assert lastRow.t == pytest.approx(expectedCentre, abs=1e-6)
    assert lastRow.t < 9 / FPS                     # ⛔ definitively NOT the last frame's stamp


def test_decision_rows_are_keyed_on_FRAME_INDEX_so_the_cadence_can_change_freely():
    # ⭐ §25/X2: "every W-th ROW" would silently multiply the comparison span when the cadence rises.
    for cadence in (1, 3):
        policy = MonitorPolicy(windowFrames=10, evaluateEveryNFrames=cadence, maxSeconds=600.0)
        monitor = MonitorEngine(FakeEvaluator(settleAfter=99), FrameRing(10, 14), policy)
        rows = drive(monitor, [frameOf(0.5) for _ in range(40)])
        decisionFrames = [row.frameIndex for row in rows if row.isDecisionRow]
        assert decisionFrames == [9, 19, 29, 39], "cadence %d changed the decision spacing" % cadence


def test_the_answer_is_LATCHED_a_later_row_cannot_steal_it():
    # ⭐ §14.6: a diagnostic run keeps observing for 20 more minutes. Without the latch, a noise excursion
    # late in the photodamage ramp would become "the best value" — §2.2's selection bias by the back door.
    class PromoteAlways:
        version, valueKey, columns = "p", "widget", []

        def evaluate(self, spectrum):
            return {"widget": float(np.mean(list(spectrum.valuesByNanometers.values())))}

        def decide(self, rows):
            return MonitorDecision(promote=True, branch="arrived-clear", readAs="FIRST_SETTLED_WINDOW",
                                   outcome=MonitorOutcome.SETTLED_IMMEDIATE)

    policy = MonitorPolicy(windowFrames=5, maxSeconds=600.0)
    monitor = MonitorEngine(PromoteAlways(), FrameRing(5, 8), policy)
    frames = [frameOf(0.5) for _ in range(5)] + [frameOf(0.9) for _ in range(20)]
    drive(monitor, frames)

    answer = monitor.result().answer
    assert answer["value"] == pytest.approx(0.5, abs=1e-6), "a later row overwrote a latched answer"
    assert answer["t"] == pytest.approx(((0 / FPS) + (4 / FPS)) / 2.0, abs=1e-6)


def test_caps_always_fire_and_a_capped_run_reports_NO_value():
    # ⭐ §12.2/L2: the caps are the ENGINE's and the evaluator cannot disable them. ⛔ On a cap the last
    # row is NOT the answer.
    class NeverSettles:
        version, valueKey, columns = "n", "widget", []

        def evaluate(self, spectrum):
            return {"widget": 1.0}

        def decide(self, rows):
            return MonitorDecision.carryOn()

    policy = MonitorPolicy(windowFrames=5, maxSeconds=10.0, maxFrames=10000)
    monitor = MonitorEngine(NeverSettles(), FrameRing(5, 8), policy)
    drive(monitor, [frameOf(0.5) for _ in range(200)])

    result = monitor.result()
    assert result.outcome == MonitorOutcome.NEVER_SETTLED
    assert result.capsHit is True
    assert result.answer is None
    assert not result.hasValue()


def test_a_nullable_cap_is_refused_outright():
    # ⛔ §12.2: a nullable maxSeconds is the loophole that turns the guarantee into a comment.
    with pytest.raises(ValueError):
        MonitorPolicy(windowFrames=10, maxSeconds=None)


def test_an_evaluator_that_raises_fails_the_run_but_KEEPS_the_trajectory():
    # ⭐ §25/X5: a fifteen-minute arm must not evaporate because the last row raised.
    class RaisesLate:
        version, valueKey, columns = "r", "widget", []

        def __init__(self):
            self.calls = 0

        def evaluate(self, spectrum):
            self.calls += 1
            if self.calls > 3:
                raise RuntimeError("boom")
            return {"widget": 1.0}

        def decide(self, rows):
            return MonitorDecision.carryOn()

    policy = MonitorPolicy(windowFrames=2, evaluateEveryNFrames=1, maxSeconds=600.0)
    monitor = MonitorEngine(RaisesLate(), FrameRing(2, 4), policy)
    drive(monitor, [frameOf(0.5) for _ in range(20)])

    result = monitor.result()
    assert result.outcome == MonitorOutcome.FAILED
    assert result.error is not None and "boom" in result.error
    assert len(result.rows) >= 3, "the rows produced before the raise were thrown away"


def test_provisional_rows_are_marked_and_never_decision_rows():
    # ⚠ §14.2: a 20-frame window must never be read later as a 50-frame one.
    policy = MonitorPolicy(windowFrames=10, minWindowFrames=4, maxSeconds=600.0)
    monitor = MonitorEngine(FakeEvaluator(settleAfter=99), FrameRing(10, 14), policy)
    rows = drive(monitor, [frameOf(0.5) for _ in range(12)])

    provisional = [row for row in rows if row.provisional]
    assert provisional, "no provisional rows were emitted at all"
    assert all(not row.isDecisionRow for row in provisional)
    assert all(row.n < 10 for row in provisional)


def test_duplicate_frames_are_counted_because_they_inflate_the_noise():
    # ⭐ §23/V1: measured at 82 % distinct on the archive = a x1.10 noise inflation. A run whose duplicate
    # rate drifted is a run whose noise budget drifted with it, so it is recorded rather than assumed.
    policy = MonitorPolicy(windowFrames=4, maxSeconds=600.0)
    monitor = MonitorEngine(FakeEvaluator(settleAfter=99), FrameRing(4, 6), policy)
    frame = frameOf(0.5)
    drive(monitor, [frame, frame, frameOf(0.6), frameOf(0.7), frameOf(0.7), frameOf(0.8)])
    assert monitor.result().distinctFraction == pytest.approx(4 / 6.0, abs=1e-6)


def test_burst_evaluator_reproduces_a_plain_N_frame_capture():
    # ⭐ §10.6: today's burst IS a monitor whose evaluator has no opinion. ⚠ C3 counts frames that SURVIVE
    # C1 (§19/I4) — nAccepted, not frames offered.
    policy = MonitorPolicy(windowFrames=None, retentionFrames=None, maxSeconds=600.0)
    monitor = MonitorEngine(BurstEvaluator(targetFrames=8), FrameRing(None, None), policy)
    drive(monitor, [frameOf(0.5 + index * 0.001) for index in range(20)])

    result = monitor.result()
    assert result.outcome == MonitorOutcome.COMPLETED
    assert result.spectrum is not None
    assert result.rows[-1].n == 8, "the burst did not stop at its target frame count"
    assert result.answer["value"] is None       # ⭐ a burst has no metric at all, and that is legitimate
