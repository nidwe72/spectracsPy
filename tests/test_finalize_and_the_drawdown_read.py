"""The §40 drawdown read, the §43/RD1 finalize seam, and the §46/E clock — SPEC_settled_measurement.md.

⭐ `test_monitor_replay.py` proves these against the whole archive. This proves the MECHANISMS in isolation,
including the two the archive cannot reach: a repo skew, and a cap that fires before the clock.
"""
import pytest

from sciens.spectracs.plugin_sdk.acquisition.MonitorEngine import MonitorEngine
from sciens.spectracs.plugin_sdk.acquisition.MonitorOutcome import MonitorOutcome
from sciens.spectracs.plugin_sdk.acquisition.MonitorPolicy import MonitorPolicy
from sciens.spectracs.plugin_sdk.acquisition.MonitorRow import MonitorRow
from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator, DevSpectralPlugin


def rows(values, step=18.7):
    return [MonitorRow(t=step * (index + 1), frameIndex=60 * (index + 1) - 1, n=60, nAccepted=60,
                       values={"qPercent": value, "soret": 1.0, "valley": 0.2, "qBand": 0.4},
                       isDecisionRow=True)
            for index, value in enumerate(values)]


# --- §40.2 the rule itself -------------------------------------------------------------------------

def test_drawdown_is_the_largest_FALL_BACK_after_the_candidate():
    values = [20.0, 19.0, 19.5, 20.1, 19.8, 19.9]
    #                ^ index 1: the curve climbs to 20.1 then gives back 0.3
    fall, after = ClearingEvaluator.drawdownAfter(values, 1)
    assert fall == pytest.approx(0.3, abs=1e-9)
    assert after == 4


def test_a_minimum_the_curve_never_comes_back_down_from_has_ZERO_drawdown():
    fall, after = ClearingEvaluator.drawdownAfter([20.0, 19.0, 19.1, 19.2, 19.3], 1)
    assert fall == 0.0 and after == 3


def test_zero_rows_after_is_admissible_by_ABSENCE_of_evidence_and_says_so():
    """⚠ §48.3 — eight of thirteen archived runs have fewer than four rows after their minimum and six
    score 0.0000. The number alone cannot distinguish that from a genuinely flat tail, which is why
    `rowsAfterMinimum` is recorded beside it."""
    fall, after = ClearingEvaluator.drawdownAfter([20.0, 19.0, 19.1], 1)
    assert (fall, after) == (0.0, 1)


def test_tailSd_measures_scatter_about_a_LINE_not_about_a_mean():
    """⭐ A settled tail is usually browning gently; a mean would score that slope as noise."""
    times = [60.0 * index for index in range(8)]
    ramp = [19.0 + 0.05 * index for index in range(8)]           # a perfect ramp: no scatter at all
    sd, used = ClearingEvaluator.tailSd(times, ramp)
    assert used == 8 and (sd is None or sd < 1e-9)


def test_tailSd_REFUSES_below_four_rows_so_a_short_run_falls_back_instead_of_being_refused():
    """A2 / §45-M4, Edwin's call: fewer than four rows -> no yardstick exists -> fall back to the older
    read rather than condemning a fill on the strength of nothing."""
    sd, used = ClearingEvaluator.tailSd([0.0, 20.0, 40.0], [19.0, 19.1, 19.2])
    assert sd is None and used == 3


def test_the_read_takes_the_DEEPEST_minimum_the_curve_never_fell_below():
    """⭐⭐ Run 006 in miniature: a sharp spurious dip, then the real minimum, then a browning limb."""
    trace = [21.0, 20.4, 19.0, 19.6, 20.1, 19.9, 19.80, 19.81, 19.80, 19.81, 19.82, 19.82, 19.83, 19.83]
    #                     ^ the spike             ^ the real minimum, index 6, then a quiet browning limb
    evaluator = ClearingEvaluator(None, None, None, windowFrames=60)
    decision = evaluator.finalize(rows(trace))
    assert decision.promote
    assert decision.promoteRow.get("qPercent") == pytest.approx(19.80)
    assert decision.diagnostics["readPhase"] == "final"
    assert decision.diagnostics["rowsAfterMinimum"] == 7
    assert decision.diagnostics["drawdownTails"] < ClearingEvaluator.DRAWDOWN_TAIL_MULTIPLE
    assert any(rejected["value"] == pytest.approx(19.0)
               for rejected in decision.diagnostics["rejected"]), \
        "the spike must be REJECTED by name, so a refusal can be argued with (§46/C3)"


def test_a_curve_that_never_stops_falling_gets_NO_ANSWER_and_WITHDRAWS_the_gate_s():
    """⛔ §40.4 — run 003's shape: every turning point is one the curve later fell below."""
    trace = [24.0, 23.0, 22.5, 22.6, 22.0, 21.5, 21.6, 21.0, 20.5, 20.2, 20.0, 19.7, 19.4, 18.8]
    decision = ClearingEvaluator(None, None, None, windowFrames=60).finalize(rows(trace))
    assert decision.withdraw and not decision.promote
    assert decision.outcome == MonitorOutcome.NEVER_SETTLED


# --- §43/RD1 the seam ------------------------------------------------------------------------------

class _Evaluator:
    version, valueKey, columns = "stub", "qPercent", []

    def __init__(self, finalizeTo=None, withdraw=False):
        self.finalizeTo, self.withdraw, self.finalized = finalizeTo, withdraw, 0

    def evaluate(self, spectrum):
        return {"qPercent": 1.0}

    def decide(self, rows):
        from sciens.spectracs.plugin_sdk.acquisition.MonitorDecision import MonitorDecision
        return MonitorDecision(promote=True, readAs="GATE",
                               outcome=MonitorOutcome.SETTLED_IMMEDIATE) if len(rows) == 1 \
            else MonitorDecision.carryOn()

    def finalize(self, rows):
        from sciens.spectracs.plugin_sdk.acquisition.MonitorDecision import MonitorDecision
        self.finalized += 1
        if self.withdraw:
            return MonitorDecision(withdraw=True, outcome=MonitorOutcome.NEVER_SETTLED)
        if self.finalizeTo is None:
            return None
        return MonitorDecision(promote=True, answer=self.finalizeTo, readAs="FINAL", promoteRow=rows[-1])


def drive(evaluator, frames=6, planned=None):
    policy = MonitorPolicy(windowFrames=2, maxSeconds=100.0, plannedSeconds=planned)
    monitor = MonitorEngine(evaluator, None, policy, evaluatorId="stub")
    for index in range(frames):
        monitor.offer({500.0: 10.0 + index}, float(index))
    monitor.stall()
    return monitor


def test_the_engine_advertises_the_seam_so_a_repo_skew_can_be_caught_at_run_START():
    """⛔⛔ §45/M2 — an old core with a new plugin is not an error; the answer just silently reverts."""
    assert MonitorEngine.SUPPORTS_FINALIZE is True


def test_finalize_may_REVISE_the_latched_answer_exactly_once_and_the_gate_s_survives():
    """⛔⛔ The §14.6 amendment (§48.2). The latch stops OBSERVATION from moving a number; one deliberate
    re-read after the last frame is a different act — and it is never invisible."""
    monitor = drive(_Evaluator(finalizeTo=42.0))
    answer = monitor.result().answer
    assert answer["value"] == 42.0
    assert answer["readAs"] == "FINAL"
    assert answer["diagnostics"]["gateAnswer"] == 1.0


def test_a_finalize_that_REFUSES_takes_the_gate_s_answer_with_it():
    monitor = drive(_Evaluator(withdraw=True))
    result = monitor.result()
    assert result.answer is None and result.spectrum is None
    assert result.outcome == MonitorOutcome.NEVER_SETTLED
    assert result.rows, "the trajectory is kept — only the ANSWER is withdrawn"


class _NoFinalize(_Evaluator):
    finalize = None      # ⭐ the shape of every evaluator that reads as it goes — a plain burst (§10.6)


def test_an_evaluator_without_finalize_is_untouched():
    """⭐ §46/B1 — the probe finds nothing and the gate's answer simply stands, with no error."""
    monitor = drive(_NoFinalize())
    assert monitor.result().answer["value"] == 1.0
    assert monitor.result().outcome == MonitorOutcome.STALLED


def test_finalize_is_NOT_called_on_a_cancel():
    """§48.1 / §12.1 — 'a cancelled capture is not a capture', and not calling it makes that true by
    CONSTRUCTION rather than by the host remembering to ignore a number."""
    evaluator = _Evaluator(finalizeTo=42.0)
    policy = MonitorPolicy(windowFrames=2, maxSeconds=100.0)
    monitor = MonitorEngine(evaluator, None, policy, evaluatorId="stub")
    for index in range(6):
        monitor.offer({500.0: 10.0 + index}, float(index))
    monitor.cancel()
    assert evaluator.finalized == 0
    assert monitor.result().outcome == MonitorOutcome.CANCELLED


# --- §46/E the clock, and §49/F1 the cap in a costume ----------------------------------------------

def test_the_frame_cap_is_DERIVED_from_maxSeconds_and_no_longer_a_20_minute_limit_in_disguise():
    """⛔⛔ §49/F1 — at the measured 3.23-3.34 fps, `maxFrames = 4000` needs 3880-4008 frames for a 1200 s
    run and run 001's own rate is already OVER it. The FRAME cap would have fired before the clock on
    essentially every planned run, finishing NEVER_SETTLED."""
    policy = MonitorPolicy(windowFrames=60, maxSeconds=1500.0)
    assert policy.maxFrames > 1200 * 3.34, "a 20-minute run at the measured rate must fit"
    assert policy.maxFrames == int(1500.0 * MonitorPolicy.ASSUMED_MAX_FPS) + 1


def test_a_planned_duration_that_the_frame_cap_would_pre_empt_is_REFUSED_at_construction():
    with pytest.raises(ValueError, match="would fire before plannedSeconds"):
        MonitorPolicy(windowFrames=60, maxSeconds=1500.0, maxFrames=100, plannedSeconds=1200.0)


def test_plannedSeconds_may_never_exceed_the_termination_guarantee():
    with pytest.raises(ValueError, match="must not exceed maxSeconds"):
        MonitorPolicy(windowFrames=60, maxSeconds=600.0, plannedSeconds=1200.0)


def test_the_planned_end_is_flagged_separately_from_the_guarantee_cap():
    """⭐ §47.2 — no new outcome member: the outcome comes from finalize as it would anyway, and a boolean
    beside the existing `capsHit` is all that distinguishes 'ran its 20 minutes' from 'blew through'."""
    monitor = MonitorEngine(_Evaluator(), None,
                            MonitorPolicy(windowFrames=2, maxSeconds=100.0, plannedSeconds=3.0),
                            evaluatorId="stub")
    for index in range(10):
        monitor.offer({500.0: 10.0 + index}, float(index))
    result = monitor.result()
    assert result.plannedEnd is True
    assert result.capsHit is False
    assert result.toRecord()["plannedEnd"] is True


def test_the_dev_plugin_asks_for_a_planned_duration_of_twenty_minutes():
    assert DevSpectralPlugin.MONITOR_PLANNED_SECONDS == 1200.0
    assert DevSpectralPlugin.MONITOR_PLANNED_SECONDS < DevSpectralPlugin.MONITOR_MAX_SECONDS
