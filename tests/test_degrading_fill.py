"""C5 — TEST C, the degrading fill (SPEC_settled_measurement.md §31), replayed on the run that exposed it.

⭐⭐ THE ACCEPTANCE GATE OF §31.10. Edwin's day-old fill `20260819/001` raised `A_valley` 32 % monotonically
over 12.6 minutes and never settled. TEST A called it FLAT throughout (0.0012/min against θ = 0.005) and
TEST B stayed silent for the same reason; what blocked the gate for forty-two consecutive rows was
`__hasFallenSinceMaximum` — on a monotone rise the maximum is always the newest row — and it stalled without
a word. The run escaped only when the valley ticked from 0.0610 to 0.0609.

⛔ THE ANSWER WAS NEVER WRONG, so the gate on this work is that TEST C reproduces it BIT-IDENTICALLY while
ending the run at ~3 minutes instead of 12.6.

⚠ THE TRACE IS TRANSCRIBED at the precision `001.pdf`'s settling table printed it, exactly as the jar-B and
series F replays are transcribed — so this test needs no PDF, no pypdf and no reference tree.
"""
import pytest

from sciens.spectracs.plugin_sdk import MonitorMode, MonitorOutcome
from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator


class Row:
    """The engine's MonitorRow as far as `decide()` can tell — the stand-in the other replays use."""

    def __init__(self, seconds, valley, qPercent, soret):
        self.t = seconds
        self.isDecisionRow = True
        self.provisional = False
        # qBand is derived exactly as the metric defines it, so the row is self-consistent even though the
        # settling table did not print it.
        self.values = {"valley": valley, "qPercent": qPercent, "soret": soret,
                       "qBand": valley + qPercent * soret / 100.0}

    def get(self, key, default=None):
        return self.values.get(key, default)


# ⭐⭐ THE REAL RUN: 20260819/001, all 43 decision rows — (t seconds, A_valley, Q%, A_Soret).
# A_valley rises 0.0463 -> 0.0610 without ever falling; A_Soret falls 3.6 %; Q% dips to 13.474 at row 7 and
# then climbs to 14.185. The shipped code answered Q% = 13.585 at t = 6.3241 s, branch "arrived-clear",
# depth 0.111 against a threshold of 0.126 — a 12 % margin (§31.5).
DEGRADING_FILL = [
    (6.3, 0.0463, 13.585, 0.6798), (21.7, 0.0467, 13.643, 0.6787), (39.5, 0.0471, 13.677, 0.6777),
    (57.6, 0.0476, 13.640, 0.6775), (75.9, 0.0476, 13.568, 0.6767), (94.3, 0.0481, 13.551, 0.6763),
    (112.1, 0.0483, 13.507, 0.6755), (129.8, 0.0485, 13.474, 0.6749), (147.7, 0.0488, 13.480, 0.6739),
    (165.4, 0.0494, 13.479, 0.6738), (183.3, 0.0497, 13.478, 0.6728), (201.2, 0.0501, 13.482, 0.6724),
    (219.3, 0.0504, 13.485, 0.6716), (237.2, 0.0510, 13.483, 0.6713), (254.9, 0.0514, 13.533, 0.6705),
    (272.7, 0.0517, 13.525, 0.6701), (290.6, 0.0520, 13.549, 0.6692), (308.5, 0.0525, 13.556, 0.6688),
    (326.2, 0.0526, 13.597, 0.6675), (344.0, 0.0530, 13.605, 0.6670), (362.2, 0.0535, 13.630, 0.6666),
    (379.9, 0.0539, 13.653, 0.6661), (397.3, 0.0544, 13.679, 0.6657), (415.3, 0.0547, 13.703, 0.6648),
    (433.3, 0.0551, 13.736, 0.6643), (451.2, 0.0555, 13.753, 0.6641), (469.4, 0.0556, 13.773, 0.6629),
    (487.6, 0.0561, 13.806, 0.6627), (505.7, 0.0565, 13.821, 0.6621), (523.7, 0.0569, 13.872, 0.6618),
    (541.6, 0.0573, 13.894, 0.6612), (559.8, 0.0576, 13.911, 0.6608), (578.0, 0.0580, 13.926, 0.6604),
    (596.2, 0.0584, 13.965, 0.6599), (613.9, 0.0588, 14.007, 0.6595), (631.9, 0.0590, 14.014, 0.6587),
    (649.9, 0.0593, 14.042, 0.6582), (668.1, 0.0597, 14.065, 0.6578), (685.8, 0.0601, 14.113, 0.6577),
    (703.4, 0.0604, 14.137, 0.6570), (721.4, 0.0606, 14.176, 0.6564), (739.8, 0.0610, 14.187, 0.6559),
    (758.1, 0.0609, 14.185, 0.6551),
]

CADENCE = 18.0          # the run's own row spacing, near enough, for the synthetic curves below


def evaluatorFor(mode=MonitorMode.PRODUCT, windowFrames=60):
    return ClearingEvaluator(plugin=None, reference=None, mode=mode, windowFrames=windowFrames)


def drive(samples, mode=MonitorMode.PRODUCT):
    """Feed rows one at a time, as the engine would. Returns (rows, decisions, firstPromoteIndex)."""
    evaluator = evaluatorFor(mode=mode)
    rows, decisions, promoted = [], [], None
    for seconds, valley, qPercent, soret in samples:
        rows.append(Row(seconds, valley, qPercent, soret))
        decision = evaluator.decide(rows)
        decisions.append(decision)
        if decision.promote and promoted is None:
            promoted = len(decisions) - 1
    return rows, decisions, promoted


# ---------------------------------------------------------------------------------------------------
# §31.10.1 — the run that exposed it
# ---------------------------------------------------------------------------------------------------

def test_TEST_C_ends_the_degrading_run_early_and_reports_the_SAME_value():
    rows, decisions, promoted = drive(DEGRADING_FILL)

    assert promoted is not None, "the degrading fill produced no value at all"
    decision = decisions[promoted]

    # ⭐ THE VALUE IS BIT-IDENTICAL to what the shipped code reported — the answer was never the problem.
    assert decision.promoteRow.get("qPercent") == pytest.approx(13.585)
    assert decision.promoteRow.t == pytest.approx(6.3)
    assert decision.readAs == "FIRST_SETTLED_WINDOW"
    assert decision.branch == "arrived-clear"

    # ⭐⭐ AND THE RUN ENDS AT ~3 MINUTES INSTEAD OF 12.6. The shipped code escaped at row 42 (758.1 s) only
    # because the valley ticked down by 0.0001; TEST C decides on evidence instead of on luck.
    assert promoted == 10, "expected TEST C to fire on row 10, fired on %s" % promoted
    assert rows[promoted].t == pytest.approx(183.3)
    assert rows[promoted].t < 0.25 * DEGRADING_FILL[-1][0]


def test_the_outcome_SAYS_the_fill_was_degrading_and_still_carries_a_value():
    _, decisions, promoted = drive(DEGRADING_FILL)
    decision = decisions[promoted]

    # ⛔ Not SETTLED_IMMEDIATE: nothing settled. §31.7 — the operator must hear WHY the run ended, and
    # burying it in a diagnostics dict while the outcome says "settled" would be a lie.
    assert decision.outcome == MonitorOutcome.DEGRADING_FILL
    assert decision.outcome.hasValue()
    assert decision.stop is True


def test_the_diagnostics_say_how_fast_the_fill_was_dying():
    _, decisions, promoted = drive(DEGRADING_FILL)
    diagnostics = decisions[promoted].diagnostics

    assert diagnostics["degradingPerMinute"] == pytest.approx(0.00105, abs=2e-4)
    assert diagnostics["degradingSignificance"] > 4.0 * ClearingEvaluator.DEGRADE_SIGMA, \
        "the trend should clear its own threshold with room to spare, not scrape past it"
    assert diagnostics["degradingRisePercent"] == pytest.approx(6.0, abs=1.0)
    assert diagnostics["degradingRows"] == ClearingEvaluator.DEGRADE_TREND_ROWS
    # ⭐ §31.5: turbidity NEVER fell, which is what forbids the vertex on this run.
    assert diagnostics["valleyFell"] is False
    # the existing read diagnostics still travel with it
    assert diagnostics["depth"] == pytest.approx(0.111, abs=0.01)
    assert diagnostics["browningPerMinute"] is not None


def test_theta_could_never_have_caught_it_and_lowering_theta_is_NOT_the_fix():
    """⛔ §31.3 — the whole reason TEST C exists as a separate test."""
    # TEST B's magnitude term is 4x the measured rise rate, and even the pre-§27.26 θ of 0.0017 misses it.
    riseRate = (DEGRADING_FILL[-1][1] - DEGRADING_FILL[0][1]) / \
               ((DEGRADING_FILL[-1][0] - DEGRADING_FILL[0][0]) / 60.0)
    assert riseRate == pytest.approx(0.00122, abs=1e-4)
    assert riseRate < 0.0017 < ClearingEvaluator.THETA_PER_MINUTE

    # ⭐ TEST B therefore never fires — and if it HAD, it would have moved `huntFrom` forward behind the
    # degradation, so the promoted row would NOT be the first look (§30.8, read backwards).
    _, decisions, promoted = drive(DEGRADING_FILL)
    assert not any("re-clouding" in (d.note or "") for d in decisions[:promoted + 1])
    assert decisions[promoted].promoteRow.t == pytest.approx(DEGRADING_FILL[0][0])


# ---------------------------------------------------------------------------------------------------
# §31.10.4/5 — what must NOT happen
# ---------------------------------------------------------------------------------------------------

def flatNoisyFill(count=43, level=0.09, amplitude=0.0004):
    """A settled fill: zero true rate, a deterministic wobble, and Q% flat. TEST C must stay silent."""
    samples = []
    for index in range(count):
        wobble = amplitude * ((index * 7 % 5) - 2) / 2.0
        samples.append((6.0 + index * CADENCE, level + wobble, 13.9 + wobble, 0.68))
    return samples


def test_a_flat_noisy_fill_never_trips_TEST_C():
    _, decisions, promoted = drive(flatNoisyFill())
    assert promoted is not None, "a settled fill must still produce a value"
    assert decisions[promoted].outcome == MonitorOutcome.SETTLED_IMMEDIATE
    assert not any(d.outcome == MonitorOutcome.DEGRADING_FILL for d in decisions)


def test_a_CLEARING_fill_is_untouched_by_TEST_C():
    """A fill that is still clearing has a FALLING valley, so the signed test cannot fire on it."""
    samples = []
    valley, qPercent = 0.30, 15.5
    for index in range(20):
        samples.append((6.0 + index * CADENCE, valley, qPercent, 0.9))
        valley = max(0.085, valley - 0.012)
        qPercent = max(13.6, qPercent - 0.10)
    _, decisions, _ = drive(samples)
    assert not any(d.outcome == MonitorOutcome.DEGRADING_FILL for d in decisions)


def test_a_fill_that_CLEARED_before_it_ripened_is_read_by_the_GATE_not_by_TEST_C():
    """⭐ THE DIVISION OF LABOUR, and it falls out of the guard rather than being designed in.

    §31.5 reasons about a fill that clears, turns, and then ripens. In practice the gate reaches it first:
    once the valley has a maximum BEHIND it, `__hasFallenSinceMaximum` passes, TEST A finds the post-turn
    rows flat, and the vertex is read within two rows — long before TEST C's ten-row baseline can clear the
    falling tail. ⇒ TEST C receives exactly the runs the guard would otherwise have stalled: the ones whose
    turbidity NEVER fell. ⚠ The §31.5 refusal therefore stands as a SAFETY property, exercised by the run
    above, not as a branch this shape reaches.
    """
    samples, valley, qPercent = [], 0.30, 15.5
    for index in range(12):                       # clears hard
        samples.append((6.0 + index * CADENCE, valley, qPercent, 0.9))
        valley -= 0.018
        qPercent -= 0.16
    for index in range(12, 40):                   # then ripens, slowly enough to stay under θ
        samples.append((6.0 + index * CADENCE, valley, qPercent, 0.9))
        valley += 0.0012
        qPercent += 0.02
    _, decisions, promoted = drive(samples)

    assert promoted is not None
    assert decisions[promoted].outcome == MonitorOutcome.SETTLED_AFTER_CLEARING
    assert decisions[promoted].readAs == "VERTEX"
    assert decisions[promoted].diagnostics["valleyFell"] is True


# ---------------------------------------------------------------------------------------------------
# §31.8 — the guard must not stall silently
# ---------------------------------------------------------------------------------------------------

def test_the_blocked_gate_says_why_it_is_blocked():
    _, decisions, promoted = drive(DEGRADING_FILL)
    held = [d.note for d in decisions[:promoted] if d.note and "gate held" in d.note]
    assert held, "the guard blocked the gate on every row and said nothing"
    assert "maximum is the newest look" in held[-1]
    # ⛔ §14.3's acceptance test greps for this phrase; the held note must never contain it.
    assert not any("gate fired" in note for note in held)
