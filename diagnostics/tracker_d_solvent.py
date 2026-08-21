"""The history tracker's shape distance `D` across a SOLVENT change. (2026-08-21)

`SPEC_history_tracker.md` alarms when a mill's oil moves away from its own reference lot:

    D = sqrt(1 - r^2) = sin(theta)      on SNV vectors, alarm at D = 0.25 (~3.2 Q% units)

⛔ THE QUESTION THIS ANSWERS: what would changing the solvent look like to that alarm? Measured over
the archive's labelled sessions plus the four white-spirit fills of `SPEC_capture_quality.md`
section 16.12.7f, on BOTH windows the spec names:

                                                    460-630 nm     550-600 nm
    within one oil, one solvent  (the noise floor)  0.047-0.274    0.012-0.258
    between two oils, same solvent  (the signal)    0.066-0.505    0.049-0.373
    SAME OIL, isopropanol vs white spirit           0.326-0.466    0.430-0.572
                                                    1.3x alarm     1.7x alarm

⇒ ⭐⭐ A SOLVENT CHANGE IS INDISTINGUISHABLE FROM AN OIL CHANGE. On the 550-600 nm window it is
LARGER than ANY oil difference in the archive; on 460-630 it sits inside the range two different
oils span. A history tracker is a longitudinal instrument: a protocol change does not degrade the
history, it DELETES it.

⚠ And one number here is a warning, not a reassurance: the within-oil floor reaches D = 0.274 --
ABOVE the 0.25 alarm, on one oil in one session, fill against fill. The fills
inflating it are the turbid ones, so the emulsion is also this tracker's largest noise source; the
fix is settling discipline (`SPEC_settled_measurement.md` section 40), not a change of solvent.

Frame: `DOC_metric_algebra.md` section 1.5a -- the less you explain, the more you must control.

Run:
    PYTHONPATH=. venv/bin/python diagnostics/tracker_d_solvent.py
"""
import itertools
import json
import os
import subprocess
import tempfile

import numpy

ARCHIVE = os.path.expanduser("~/development/spectracs/spectracs-references/tmp")
WINDOWS = [(460.0, 630.0), (550.0, 600.0)]              # SPEC_history_tracker.md sections 7.3 / 8
ALARM = 0.25

SETS = {
    "Lugitsch IPA":      "20260817LigitschA",
    "Lugitsch SPIRIT":   "20260821LugitschA",
    "Billa IPA":         "20280819BillaClever",
    "Billa SPIRIT":      "20260821BillaCleverA",
    "Steirerkraft IPA":  "20260807D",
    "JaNatuerlich IPA":  "20260812BillJaNatuerlich",
}


def workflowOf(pdfPath, scratch):
    listing = subprocess.run(["pdfdetach", "-list", pdfPath],
                             capture_output=True, text=True).stdout
    index = next((line.split(":")[0].strip() for line in listing.splitlines()
                  if line.strip().endswith(": workflow.json")), None)
    if index is None:
        return None
    target = os.path.join(scratch, "w.json")
    subprocess.run(["pdfdetach", "-save", index, "-o", target, pdfPath], capture_output=True)
    with open(target) as handle:
        return json.load(handle)


def despikedTrace(workflow):
    for phase in workflow.get("phases", []):
        if phase.get("type") != "EVALUATION":
            continue
        for step in phase.get("steps", []):
            if step.get("label") != "Absorption (bands)":
                continue
            values = step["items"][0]["traces"][0]["values"]
            wavelengths = numpy.array([float(k) for k in values])
            absorbance = numpy.array(list(values.values()))
            order = numpy.argsort(wavelengths)
            return wavelengths[order], absorbance[order]
    return None


def snvVectors(folder, grid):
    """Every fill in one session, resampled onto `grid` and SNV'd over it."""
    out = []
    directory = os.path.join(ARCHIVE, folder)
    with tempfile.TemporaryDirectory() as scratch:
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".pdf"):
                continue
            workflow = workflowOf(os.path.join(directory, name), scratch)
            if workflow is None:
                continue
            trace = despikedTrace(workflow)
            if trace is None or trace[0][0] > grid[0] + 1.0 or trace[0][-1] < min(grid[-1], 628.0):
                continue
            absorbance = numpy.interp(grid, trace[0], trace[1])
            valley = numpy.interp(numpy.arange(500.0, 560.01, 0.5), trace[0], trace[1]).mean()
            if valley > 1.0:                                    # the opaque fill
                continue
            out.append((absorbance - absorbance.mean()) / absorbance.std())
    return out


def distance(x, y):
    r = float(numpy.corrcoef(x, y)[0, 1])
    return numpy.sqrt(max(0.0, 1.0 - r * r))


def spread(values):
    return "%.3f – %.3f" % (min(values), max(values)) if values else "—"


def main():
    for low, high in WINDOWS:
        grid = numpy.arange(low, high + 0.01, 0.5)
        sets = {label: snvVectors(folder, grid) for label, folder in SETS.items()}
        within, between, crossSolvent = [], [], []
        for label, vectors in sets.items():
            within += [distance(a, b) for a, b in itertools.combinations(vectors, 2)]
        for a, b in itertools.combinations(sets, 2):
            solventA, solventB = a.split()[-1], b.split()[-1]
            oilA, oilB = a.rsplit(" ", 1)[0], b.rsplit(" ", 1)[0]
            pairs = [distance(x, y) for x in sets[a] for y in sets[b]]
            if solventA == solventB and oilA != oilB:
                between += pairs
            elif solventA != solventB and oilA.split()[0] == oilB.split()[0]:
                crossSolvent += pairs

        print("\n=== SNV window %.0f–%.0f nm     (alarm at D = %.2f)" % (low, high, ALARM))
        print("  within one oil, one solvent — the noise floor   %s" % spread(within))
        print("  between two oils, same solvent — the signal     %s" % spread(between))
        print("  ⛔ SAME OIL, isopropanol vs white spirit         %s" % spread(crossSolvent))
        if crossSolvent:
            verdict = ("LARGER than ANY oil difference here"
                       if min(crossSolvent) > max(between)
                       else "inside the range two different oils span")
            print("     ⇒ %.1f× the alarm, and %s" % (min(crossSolvent) / ALARM, verdict))
        if within and max(within) > ALARM:
            print("  ⚠ the within-oil floor reaches %.3f — ABOVE the alarm, on one oil in one session"
                  % max(within))


if __name__ == "__main__":
    main()
