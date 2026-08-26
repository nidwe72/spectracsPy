"""Replay every archived run's RECORDED ROWS through today's read rule, and diff against what the run
actually reported. (SPEC_settled_measurement.md §42/W0; built 2026-08-26 for the sunflower read.)

⭐⭐ WHY IT CAN EXIST AT ALL: the read is a PURE FUNCTION OF THE ROWS. `MonitorEngine.__finish()` asks
`finalize(rows)` once, when no more data can come, and `MonitorRow.toDict()` round-trips losslessly into
`monitorRecord["rows"]`. So a rule change can be measured against the whole archive with no rig time.

⛔ IT IS THE GATE ON ANY READ-RULE CHANGE. Every ISOPROPANOL answer must come back BIT-IDENTICAL when a
rule is changed for sunflower only; one that moves means the branch leaked. And the archive's own record
of which rule produced a number (`evaluatorVersion`) is only trustworthy if a bump accompanies every
change — "clearing-2.0" already identifies two different algorithms because TEST C did not bump.

⚠ A row's `isDecisionRow` and `provisional` flags survive the round trip, so `__usableDecisions` sees
exactly what it saw live. `tooDark` rows likewise.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/settling_replay.py [baseline.json]

With no argument it WRITES the baseline; with one it DIFFS against it.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
from sciens.spectracs.plugin_sdk import MonitorRow
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

def ClearingEvaluatorVersion():
    from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator
    return ClearingEvaluator.version


BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settling_baseline.json")


def rowsFrom(record):
    """Rebuild MonitorRow objects from the persisted dicts. Keys the engine owns are lifted out; every
    other key is the PLUGIN's scalar and goes back into `values` untouched."""
    owned = {"t", "frameIndex", "n", "nAccepted", "provisional", "isDecisionRow"}
    rows = []
    for raw in record.get("rows") or []:
        rows.append(MonitorRow(
            t=raw.get("t"), frameIndex=raw.get("frameIndex"), n=raw.get("n"),
            nAccepted=raw.get("nAccepted"),
            values={k: v for k, v in raw.items() if k not in owned},
            provisional=bool(raw.get("provisional")),
            isDecisionRow=bool(raw.get("isDecisionRow"))))
    return rows


def replay(record, solvent=None):
    """What today's rule would answer for this recorded run, or None if it would promote nothing.

    ⭐⭐ IT SIMULATES THE ENGINE, not just `finalize()`. `MonitorEngine.__applyDecision` feeds every
    decision row to `decide()` and LATCHES the first promote (§14.6); `__finish` then asks `finalize()`
    once, which may revise or WITHDRAW it. Replaying only the finalize half tested 8 of 23 archived runs,
    because the other 15 were answered live by the gate and finalize correctly declined to touch them.

    ⚠ The evaluator is built DIRECTLY, not through `createMonitor` — that path needs a reference spectrum
    and a frame provider, neither of which a replay has. Neither `decide()` nor `finalize()` touches the
    reference, so the read is reproduced exactly; anything that DID need it would fail loudly."""
    from sciens.spectracs.plugins.dev.DevSpectralPlugin import ClearingEvaluator
    plugin = DevSpectralPlugin()
    if solvent is not None:
        plugin.solvent = solvent
    windowFrames = (record.get("policy") or {}).get("windowFrames")
    evaluator = ClearingEvaluator(plugin, reference=None, windowFrames=windowFrames)
    rows = rowsFrom(record)
    if not rows:
        return None
    valueKey = getattr(plugin, "valueKey", None) or getattr(ClearingEvaluator, "valueKey", "qPercent")

    def taken(decision, row):
        winner = decision.promoteRow if decision.promoteRow is not None else row
        if winner is None:
            return None
        value = decision.answer if decision.answer is not None else winner.get(valueKey)
        return None if value is None else {
            "value": float(value), "t": winner.t, "readAs": decision.readAs,
            "branch": decision.branch,
            "outcome": getattr(getattr(decision, "outcome", None), "value", None)}

    answer, seen = None, []
    for row in rows:
        seen.append(row)
        decision = evaluator.decide(seen)
        if decision is None:
            continue
        if decision.promote and answer is None:              # ⭐ the latch: first promote wins
            answer = taken(decision, row)
        if decision.stop:
            break
    final = evaluator.finalize(seen)
    if final is not None:
        if getattr(final, "withdraw", False):
            return None
        if final.promote:
            answer = taken(final, seen[-1]) or answer
    return answer


def collect():
    """(relativePath, record) for every archived run that carries a monitorRecord."""
    out = []
    with tempfile.TemporaryDirectory() as scratch:
        for folder, name in archive.walkReports():
            relative = os.path.relpath(os.path.join(folder, name), archive.ARCHIVE)
            workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
            if workflow is None:
                continue
            record = workflow.get("monitorRecord")
            if record and (record.get("rows") or record.get("answer")):
                out.append((relative, record))
    return out


def selfCheck(runs):
    """⛔ THE HARNESS'S OWN CREDIBILITY TEST. Replaying the CURRENT rule over runs the CURRENT rule
    produced must reproduce them. A mismatch here means the replay is not the live read, and every diff
    it reports afterwards is worthless."""
    same, moved, silent = 0, [], 0
    for relative, record in runs:
        recorded = (record.get("answer") or {}).get("value")
        if record.get("evaluatorVersion") != ClearingEvaluatorVersion():
            continue
        try:
            answer = replay(record)
        except Exception as error:
            moved.append((relative, recorded, "RAISED %s" % error))
            continue
        if answer is None:
            silent += 1
            continue
        value = answer.get("value")
        if recorded is not None and abs(value - recorded) < 1e-9:
            same += 1
        else:
            moved.append((relative, recorded, value))
    print("SELF-CHECK  reproduced %d   promoted-nothing %d   MISMATCHED %d" % (same, silent, len(moved)))
    for relative, recorded, value in moved:
        print("   ⛔ %-44s recorded %s  replayed %s" % (relative, recorded, value))
    return not moved


def main():
    runs = collect()
    print("archive: %d runs carry a monitorRecord" % len(runs))
    selfCheck(runs)
    snapshot = {}
    for relative, record in runs:
        answer = record.get("answer") or {}
        snapshot[relative] = {
            "recordedVersion": record.get("evaluatorVersion"),
            "recordedOutcome": record.get("outcome"),
            "recordedValue": answer.get("value"),
            "recordedReadAs": answer.get("readAs"),
            "solvent": (workflowSolvent(record)),
        }
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as handle:
            before = json.load(handle)
        moved = [k for k in sorted(set(before) & set(snapshot))
                 if before[k]["recordedValue"] != snapshot[k]["recordedValue"]]
        print("compared %d runs; %d recorded values differ" % (len(before), len(moved)))
        for key in moved:
            print("  %-46s %s -> %s" % (key, before[key]["recordedValue"],
                                        snapshot[key]["recordedValue"]))
        return
    with open(BASELINE, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=1, sort_keys=True)
    versions = {}
    for value in snapshot.values():
        versions[value["recordedVersion"]] = versions.get(value["recordedVersion"], 0) + 1
    print("wrote %s" % BASELINE)
    for version, count in sorted(versions.items(), key=lambda kv: str(kv[0])):
        print("  evaluatorVersion %-16s %3d runs" % (version, count))


def workflowSolvent(record):
    return None            # ⚠ pre-2026-08-26 runs record no solvent; the field lands in the HEADER, not here


if __name__ == "__main__":
    main()
