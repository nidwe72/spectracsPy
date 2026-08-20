"""R3.3 — the seven series F runs, replayed through the shipped evaluator.

⭐⭐ THE ACCEPTANCE GATE OF SPEC_settled_measurement.md §29/§30. These are the first measurements the
one-fill-one-wait protocol ever produced (Lugitsch A, 2026-08-17/18), and §29 was derived FROM them: the
clear branch reported the look at which the gate finished confirming, and the lamp had been bleaching the
sample throughout that confirmation (+0.482 on run 003). ⇒ the fix is only a fix if replaying those runs
under `clearing-2.0` reproduces the corrected reads — and leaves the three vertex runs exactly where they
already were.

⚠ THE FIXTURE IS TRANSCRIBED, NOT READ FROM THE MASTERS (§30.14/R3.1). The reports live under a hand-typed
path in a `tmp/` that has already been rotated twice; `tests/data/series_f_records.json` carries each run's
complete `monitorRecord` plus the values it reported under `clearing-1.0`, so this test needs no PDF, no
pypdf and no reference tree.

⛔ VALUES ONLY, AND THAT LIMIT IS PERMANENT. Only the WINNER's spectrum was ever persisted; under the new
read the four clear runs report their FIRST look, whose window mean was never kept. The first clear-branch
spectrum under this rule comes into existence at the rig (§30.14/R4), not here.
"""
import json
import os

import pytest

from sciens.spectracs.plugin_sdk import MonitorMode
from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator

FIXTURE = os.path.join(os.path.dirname(__file__), "data", "series_f_records.json")


class Row:
    """The engine's MonitorRow, as far as `decide()` can tell — the same stand-in the jar-B replay uses."""

    def __init__(self, record):
        self.t = record["t"]
        self.isDecisionRow = record.get("isDecisionRow", True)
        self.provisional = record.get("provisional", False)
        self.values = {key: record[key] for key in ("valley", "qPercent", "soret", "qBand")
                       if record.get(key) is not None}

    def get(self, key, default=None):
        return self.values.get(key, default)


def series():
    with open(FIXTURE) as handle:
        return json.load(handle)["runs"]


def replay(run):
    """Drive the shipped evaluator with this run's own decision rows, at this run's own W."""
    record = run["monitorRecord"]
    evaluator = ClearingEvaluator(plugin=None, reference=None, mode=MonitorMode.PRODUCT,
                                  windowFrames=record["policy"]["windowFrames"])
    rows, promoted = [], None
    for source in record["rows"]:
        rows.append(Row(source))
        decision = evaluator.decide(rows)
        if decision.promote and promoted is None:
            promoted = decision
    return rows, promoted


@pytest.mark.parametrize("name", sorted(series()))
def test_every_series_F_run_reads_what_29_2_measured(name):
    run = series()[name]
    expected = run["expected"]
    rows, decision = replay(run)

    assert decision is not None, "run %s never settled under clearing-2.0" % name
    assert decision.branch == expected["branchUnderClearing2_0"]
    assert decision.diagnostics["depth"] == pytest.approx(expected["depthBelowFirstLook"], abs=0.001)
    assert decision.diagnostics["windowFrames"] == expected["windowFrames"]
    # ⚠ 2.0 -> 3.0 on 2026-08-20 (§40, §46/C1): the read now happens at the END of the run and refuses a
    # minimum the curve later fell below. ⭐ EVERY OTHER ASSERTION IN THIS TEST IS UNCHANGED, which is the
    # evidence that the gate-time read §29/§30 derived is exactly where it was.
    # ⛔ The literal is deliberate. §51: TEST C changed a read on 2026-08-19 WITHOUT bumping this string, so
    # "clearing-2.0" names two different algorithms in the archive — a bump has to be a visible act.
    assert decision.diagnostics["readRule"] == "clearing-3.0"

    # ⭐ The value: a REAL look on the clear branch (`answer is None` ⇒ the engine takes the promoted
    # row's own number), a fitted vertex on the muddy one.
    read = decision.answer if decision.answer is not None else decision.promoteRow.get("qPercent")
    if expected["branchUnderClearing2_0"] == "arrived-clear":
        assert decision.answer is None, "a fitted value on the clear branch would have no spectrum (§9.1a)"
        assert read == pytest.approx(expected["firstLook"], abs=0.001)
        assert decision.promoteRow is rows[0]
    else:
        assert read == pytest.approx(expected["minimum"], abs=0.10), \
            "the vertex must sit on the measured minimum, not on the gate row"
        assert decision.promoteRow.t == pytest.approx(expected["argminT"], abs=0.1)


@pytest.mark.parametrize("name", sorted(series()))
def test_the_browning_rate_reproduces_29_1(name):
    """§29.5 — the diagnostic that was there all along and nobody looked at.

    ⭐ Two-point, from the read to the end of the run (§30.11): a fit drifts up to 5 % and models the
    damage instead of measuring it. Run 003 browned at 0.291 /min — 35x run 002 on the same evening — and
    until now that fact was folded silently INTO the answer instead of reported beside it.
    """
    run = series()[name]
    _, decision = replay(run)
    assert decision.diagnostics["browningPerMinute"] == \
        pytest.approx(run["expected"]["browningPerMinuteTwoPoint"], abs=0.001)
    assert decision.diagnostics["rowsAfterRead"] == run["expected"]["rowsAfterRead"]


def test_the_four_CLEAR_runs_move_DOWN_and_the_three_vertex_runs_do_not_move():
    """⭐⭐ §29.1's table, as an assertion — the whole point of the change, in one test.

    ⛔ The bias is ONE-DIRECTIONAL (always upward before the fix, so it never averaged out over repeats)
    and FILL-SPECIFIC (0.291 vs 0.008 /min between two fills of the same evening — a factor of 35, so no
    constant could be subtracted afterwards). Reporting an earlier moment is the only remedy.
    """
    moved = {}
    for name, run in sorted(series().items()):
        _, decision = replay(run)
        read = decision.answer if decision.answer is not None else decision.promoteRow.get("qPercent")
        moved[name] = read - run["expected"]["reportedUnderClearing1_0"]

    assert moved["001"] == pytest.approx(-0.084, abs=0.002)
    assert moved["002"] == pytest.approx(-0.013, abs=0.002)
    assert moved["003"] == pytest.approx(-0.482, abs=0.002)      # ⭐ 37 % of brown's whole margin to T
    assert moved["005"] == pytest.approx(-0.037, abs=0.002)
    for name in ("004", "006", "007"):
        assert moved[name] == pytest.approx(0.0, abs=0.002), \
            "run %s took the vertex branch before and after — it must not move" % name
