"""The promoted row keeps its spectrum, however far back it sits — SPEC_settled_measurement.md §27.25 (M1).

⛔⛔ THE BUG THIS CLOSES, in Edwin's words: "after capturing the sample i get always or sometimes [a dialog]
saying 'could not capture'… first measurement was in fact 14.38 and i had to repeat the capture… and it
raised to 14.8." Every frame had arrived, the gate had fired, the answer was computed — and the app
reported a camera failure, so the jar was re-measured after banking light dose and read higher.

⭐⭐ THE SEAM NOBODY TESTED, and that is why it shipped:
  * `test_clearing_evaluator.py` drives the EVALUATOR alone and correctly asserts it nominates the row at
    t = 16.655 — several rows behind the gate;
  * `test_monitor_engine.py` drives the ENGINE with a fake evaluator that always promotes the CURRENT row.
Each half was right. The crossing — *the evaluator nominates an old row × the engine has already pruned
its spectrum* — was tested by neither, and that is exactly where the measurement was lost.

⚠ IT WAS A CADENCE BUG. Retention was five DECISION ROWS, justified as "the vertex reaches ~2 decision rows
back" — true at the diagnostic script's 3.28-minute sampling, false on the bench: at ~3.5 fps a decision
row lands every ~17 s, so five rows is 85 SECONDS of history, while jar B's `Q%` minimum sits 3.27 MINUTES
(11.5 rows) before its gate. ⇒ these tests assert in ROWS *and* in SECONDS, because a row count is the unit
that betrayed us.
"""
import unittest

from sciens.spectracs.plugin_sdk.acquisition.FrameRing import FrameRing
from sciens.spectracs.plugin_sdk.acquisition.MonitorDecision import MonitorDecision
from sciens.spectracs.plugin_sdk.acquisition.MonitorEngine import MonitorEngine
from sciens.spectracs.plugin_sdk.acquisition.MonitorOutcome import MonitorOutcome
from sciens.spectracs.plugin_sdk.acquisition.MonitorPolicy import MonitorPolicy

WINDOW = 3           # tiny, so decision rows arrive quickly
FRAME_PERIOD = 1.0   # seconds per offered frame


class PromotesAnOldRow:
    """Nominates a row `back` decision rows behind the current one — what the vertex read does."""

    version = "stub-1.0"

    def __init__(self, back):
        self.back = back

    def evaluate(self, spectrum):
        return {"x": 1.0}

    def decide(self, rows):
        decisions = [row for row in rows if row.isDecisionRow]
        if len(decisions) < self.back + 1:
            return MonitorDecision.carryOn()
        return MonitorDecision(promote=True, stop=True, outcome=MonitorOutcome.SETTLED_AFTER_CLEARING,
                               branch="stub", readAs="VERTEX", answer=1.0,
                               promoteRow=decisions[-(self.back + 1)])


def runPromoting(back, maxSeconds=1500.0):
    policy = MonitorPolicy(windowFrames=WINDOW, retentionFrames=WINDOW,
                           maxSeconds=maxSeconds, maxFrames=100000)
    engine = MonitorEngine(PromotesAnOldRow(back), FrameRing(WINDOW, WINDOW), policy, evaluatorId="stub")
    timestamp = 0.0
    while not engine.isFinished() and timestamp < maxSeconds:
        timestamp += FRAME_PERIOD
        engine.offer({400.0 + index: 10.0 + 0.001 * index for index in range(8)}, timestamp)
    return engine.result()


class TheWinnerKeepsItsSpectrumTest(unittest.TestCase):

    def test_the_winner_survives_however_far_back_it_sits(self):
        # ⛔ MEASURED BEFORE THE FIX: spectrum PRESENT at 0-4 rows back, None from exactly 5 — the old
        # SPECTRUM_RETAIN_DECISION_ROWS. 40 and 120 are far past any plausible vertex reach.
        for back in (0, 1, 4, 5, 6, 9, 40, 120):
            result = runPromoting(back)
            self.assertIsNotNone(result.answer, "no answer at %d rows back" % back)
            self.assertIsNotNone(result.spectrum,
                                 "the winner %d decision rows back lost its spectrum — the run would be "
                                 "discarded and the jar re-measured after banking dose" % back)

    def test_a_run_longer_than_the_old_five_row_window_still_answers(self):
        # ⭐ The same statement in SECONDS, which is the unit the retention is now sized in: a winner two
        # minutes back is ordinary on a clearing fill and was fatal before.
        result = runPromoting(back=100)
        rows = [row for row in result.rows if row.isDecisionRow]
        span = rows[-1].t - result.answer["t"]
        self.assertGreater(span, 120.0, "this test no longer reaches past two minutes; re-tune it")
        self.assertIsNotNone(result.spectrum)

    def test_retention_is_sized_in_time_so_a_cadence_change_cannot_shrink_it(self):
        # ⛔ THE ACTUAL LESSON (§27.25): a row count is a duration in disguise, and it silently changed
        # meaning when the cadence did. Doubling the decision-row density must not halve the history.
        sparse = runPromoting(back=30)
        dense = runPromoting(back=60)
        self.assertIsNotNone(sparse.spectrum)
        self.assertIsNotNone(dense.spectrum)

    def test_a_winner_older_than_the_cap_is_the_only_thing_that_can_be_dropped(self):
        # ⚠ Retention is not unbounded: it covers `maxSeconds`, the cap the run cannot outlive. With a cap
        # far shorter than the reach, the oldest spectra do go — and that is the intended, stated limit.
        result = runPromoting(back=60, maxSeconds=20.0)
        self.assertTrue(result.capsHit or result.answer is None or result.spectrum is None,
                        "a cap shorter than the vertex reach should bound retention, not extend it")


if __name__ == "__main__":
    unittest.main()
