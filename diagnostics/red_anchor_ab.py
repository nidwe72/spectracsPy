"""THE BASELINE FAMILY -- five ways to reference the 624 nm band, scored on every labelled run.
(Edwin's question 2026-08-29, from a screenshot: "the red peak on one run has shifted more below A_valley")

    Rv      = 100 * (A[622-627] - Av) / (A_Q - Av)                     the shipped form
    RvTest  = 100 * (A[622-627] - Aloc) / (A_Q - Av)                   red on its OWN anchor
    RvLin   = 100 * (A624 - B(624.5)) / (A_Q - B(572.5))               two-point line through Av and Aloc
    RvCont  = 100 * A'[622-627] / A'[565-580]                          least-squares CONTINUUM removed
    R       = P2 / P1                                                  SPEC_metric_research.md §12

  Av = A[500-560]   Aloc = A[612-615]   A_Q = A[565-580]
  B  = the straight line through (530, Av) and (613.5, Aloc)
  A' = A minus a least-squares line fitted over the pigment-free windows of §14.2,
       472-500 + 505-555 + 588-604 nm -- so BOTH bands are measured above the SAME continuum.

⭐ WHY THE QUESTION IS WORTH ASKING. Over 37 sunflower runs the depth of the 600-620 nm trough below
`A_valley` correlates with `Rv` at r = -0.89 (Esterer), -0.84 (Lugitsch), -0.94 (Stekko) -- same sign in
every oil. The 500-560 valley is 70 nm away from the band it is being used to baseline, and the two
fills whose trough INVERTS (sits above the valley) are the archive's two high outliers,
`20260826EstererD` and `20260824Lugitsch`.

⛔⛔ AND WHY THE ANSWER CANNOT COME FROM THE SUNFLOWER FILLS THAT PROMPTED IT. The anchor was chosen
AFTER seeing the effect, on 14 fills of one solvent on one rig. That is the exact shape of the mistake
`SPEC_metric_research.md` §7's M9 gate exists to stop. This script therefore scores BOTH metrics on
every labelled run on disk -- three solvents, both sides of the 2026-07-29 rebuild -- and reports the
splits separately. A gain that lives only in the sunflower column is a corpus artefact.

⚠ THE ANCHOR IS 3 nm FROM A KNOWN ARTEFACT. `peak_ratio_archive`'s docstring records that the 608-610 nm
feature reads 1.6-2.2x the 613 nm value in every run on disk.
⛔ IT IS NOT A BAYER CHANNEL CROSSOVER -- measured per channel 2026-08-30 (`DOC_lamp_rebuild.md` §6.0a,
`diagnostics/channel_replay.py`): red carries 96-99 % of the light from 596 to 620 nm and green is dead by
604, so nothing hands over. It is a step in the RED CHANNEL'S OWN response, it survives a `sum` reduction
unchanged, and it moves +2.1 nm with the EXPOSURE alone. The window named below is right; the mechanism
this file used to assert was not, and believing it produced the retracted `SPEC_capture_quality.md`
§16.39.3a. 612-615 was placed to dodge it and is the earliest usable left anchor; ⛔ any optical change
moves that line, so a win here does not survive the lamp rebuild un-revalidated.

The corpus, the labels, the exclusions and the first-two-distinct-reads policy are `reference_band_scan`'s
-- i.e. the same ones the report pages use. Nothing is enumerated here.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \\
        ./venv/bin/python diagnostics/red_anchor_ab.py
"""
import os
import sys
import statistics

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reference_band_scan as scan
import peak_ratio_archive as archive

RED = (622.0, 627.0)
LOCAL = (612.0, 615.0)
VALLEY = (500.0, 560.0)
Q = (565.0, 580.0)
# ⭐ The pigment-free windows `SPEC_metric_research.md` §14.2 already uses to define the floor `F`.
# ⛔ THE BLUE ONE IS LOAD-BEARING: dropping 472-500 turns RvCont's corridor from +5.1 to -6.1 and its
# errors from 0 to 2. A continuum needs a long lever to be a continuum; two anchors are not one.
CONTINUUM = [(472.0, 500.0), (505.0, 555.0), (588.0, 604.0)]
KEYS = ("Rv", "RvTest", "RvLin", "RvCont", "R")


def bandMean(nm, absorbance, low, high):
    inside = (nm >= low) & (nm <= high)
    return float(absorbance[inside].mean())


def metricsOf(row):
    nm, absorbance = row["nm"], row["a"]
    valley = bandMean(nm, absorbance, *VALLEY)
    local = bandMean(nm, absorbance, *LOCAL)
    red = bandMean(nm, absorbance, *RED)
    qBand = bandMean(nm, absorbance, *Q)
    denominator = qBand - valley
    if denominator <= 0:
        return None
    values = {"Rv": 100.0 * (red - valley) / denominator,
              "RvTest": 100.0 * (red - local) / denominator}

    # ⚠ RvLin uses both anchors but is still only a TWO-POINT line. It improves on RvTest (corridor
    # -8.6 -> -5.2) and is still not enough -- see the docstring's note on the blue window.
    slope = (local - valley) / (centreOf(LOCAL) - centreOf(VALLEY))
    line = lambda at: valley + slope * (at - centreOf(VALLEY))
    linDenominator = qBand - line(centreOf(Q))
    values["RvLin"] = (100.0 * (red - line(centreOf(RED))) / linDenominator
                       if linDenominator > 0 else float("nan"))

    # ⭐ RvCont is the only member measured entirely above ONE fitted line, so it has no mismatched
    # lever arms. `Av` does not appear as a term because 505-555 is inside the fit: after subtraction
    # the valley sits at ~0 by construction.
    mask = numpy.zeros_like(nm, dtype=bool)
    for low, high in CONTINUUM:
        mask |= (nm >= low) & (nm <= high)
    gradient, intercept = numpy.polyfit(nm[mask], absorbance[mask], 1)
    corrected = absorbance - (gradient * nm + intercept)
    correctedQ = bandMean(nm, corrected, *Q)
    values["RvCont"] = (100.0 * bandMean(nm, corrected, *RED) / correctedQ
                        if correctedQ > 0 else float("nan"))

    # `R` is the archive's own, imported rather than reimplemented so the two cannot drift apart.
    values["R"] = 100.0 * archive.peakRatio(nm, absorbance)[2]
    return None if any(v != v for v in values.values()) else values


def centreOf(window):
    return (window[0] + window[1]) / 2.0


def bestThreshold(values, classes):
    """The cut with the fewest errors; ties broken by the widest margin to the nearest point.

    ⛔ FITTED ON WHATEVER IS PASSED IN. Quoting a per-solvent best cut as if it were a threshold is the
    error this whole script is about -- read the SHARED cut, not these."""
    candidates = sorted(set(values))
    best = None
    for index in range(len(candidates)):
        for cut in ({(candidates[index] + candidates[index + 1]) / 2.0}
                    if index + 1 < len(candidates) else {candidates[index] + 0.5}):
            errors = sum(1 for value, cls in zip(values, classes)
                         if (value >= cut) != (cls == "green"))
            margin = min(abs(value - cut) for value in values)
            if best is None or (errors, -margin) < (best[1], -best[2]):
                best = (cut, errors, margin)
    return best


def cohen(values, classes):
    green = [v for v, c in zip(values, classes) if c == "green"]
    brown = [v for v, c in zip(values, classes) if c == "brown"]
    if len(green) < 2 or len(brown) < 2:
        return float("nan")
    pooled = (((len(green) - 1) * statistics.stdev(green) ** 2
               + (len(brown) - 1) * statistics.stdev(brown) ** 2)
              / (len(green) + len(brown) - 2)) ** 0.5
    return (statistics.mean(green) - statistics.mean(brown)) / pooled if pooled else float("nan")


def report(label, rows, key):
    values = [r[key] for r in rows]
    classes = [r["class"] for r in rows]
    if len(set(classes)) < 2:
        print("   %-26s %-8s n=%3d   (one class only)" % (label, key, len(rows)))
        return
    cut, errors, _ = bestThreshold(values, classes)
    green = [v for v, c in zip(values, classes) if c == "green"]
    brown = [v for v, c in zip(values, classes) if c == "brown"]
    print("   %-26s %-8s n=%3d   best cut %6.1f   errors %2d   corridor %+6.1f   d=%5.2f"
          % (label, key, len(rows), cut, errors, min(green) - max(brown), cohen(values, classes)))


def main():
    rows = []
    for row in scan.collect():
        values = metricsOf(row)
        if values is None:
            continue
        row.update(values)
        rows.append(row)
    scored = [r for r in rows if r["class"] in ("green", "brown")]
    print("labelled runs with both metrics computable: %d" % len(scored))
    print("   by solvent: " + ", ".join(
        "%s %d" % (name, sum(1 for r in scored if r["solvent"] == name))
        for name in sorted({r["solvent"] for r in scored})))

    print("\n=== PER SOLVENT  (each cut FITTED on that solvent -- diagnostic only)")
    for solvent in sorted({r["solvent"] for r in scored}):
        subset = [r for r in scored if r["solvent"] == solvent]
        for key in KEYS:
            report(solvent, subset, key)
        print()

    print("=== THE WHOLE CORPUS, ONE SHARED CUT  <- this is the number that matters")
    print("   `Rv`'s case was that ONE threshold transfers across every solvent unchanged.")
    for key in KEYS:
        report("all solvents", scored, key)

    print("\n=== THAT SHARED CUT, APPLIED BACK PER SOLVENT")
    for key in KEYS:
        cut = bestThreshold([r[key] for r in scored], [r["class"] for r in scored])[0]
        line = []
        for solvent in sorted({r["solvent"] for r in scored}):
            subset = [r for r in scored if r["solvent"] == solvent]
            wrong = sum(1 for r in subset if (r[key] >= cut) != (r["class"] == "green"))
            line.append("%s %d/%d" % (solvent, wrong, len(subset)))
        print("   %-8s cut %6.1f   errors: %s" % (key, cut, "   ".join(line)))

    print("\n=== HOLD-OUT: fit the cut on ONE solvent, apply it UNTOUCHED to solvents the fit never saw")
    print("   ⛔ THE ONLY HONEST COLUMN ON THIS PAGE. Every cut above is fitted on the runs it is then")
    print("      scored against; §7's M9 gate exists because that flatters a candidate. This does not.")
    inside = [r for r in scored if r["solvent"] == "isopropanol"]
    outside = [r for r in scored if r["solvent"] != "isopropanol"]
    print("   %-8s %34s %34s" % ("metric", "fit IPA (%d) -> test %d" % (len(inside), len(outside)),
                                 "fit the other %d -> test IPA %d" % (len(outside), len(inside))))
    for key in KEYS:
        forward = bestThreshold([r[key] for r in inside], [r["class"] for r in inside])[0]
        backward = bestThreshold([r[key] for r in outside], [r["class"] for r in outside])[0]
        print("   %-8s %20s cut %6.1f -> %2d errors %14s cut %6.1f -> %2d errors"
              % (key, "", forward,
                 sum(1 for r in outside if (r[key] >= forward) != (r["class"] == "green")), "", backward,
                 sum(1 for r in inside if (r[key] >= backward) != (r["class"] == "green"))))

    print("\n=== BROWN-ONLY within-session scatter -- the class the threshold's edge sits against")
    brown = {}
    for row in scored:
        if row["class"] == "brown":
            brown.setdefault(row["session"], []).append(row)
    pooledBrown = {key: [] for key in KEYS}
    for runs in brown.values():
        if len(runs) < 2:
            continue
        for key in KEYS:
            values = [r[key] for r in runs]
            pooledBrown[key].extend([v - statistics.mean(values) for v in values])
    print("   %-26s %s" % ("pooled within-session sd",
                           " ".join("%10.2f" % statistics.pstdev(pooledBrown[k]) for k in KEYS)))
    print("   %-26s %s" % ("", " ".join("%10s" % k for k in KEYS)))

    print("\n=== FILL-TO-FILL SCATTER, per oil, sunflower only (where fills are identifiable)")
    print("   ⛔ READ IT BESIDE THE CORRIDOR, NEVER ALONE. The variants with the LOWEST sigma_fill have")
    print("      the WORST corridors: a locally fitted baseline lowers fill scatter partly by absorbing")
    print("      the class signal into the baseline. 600-620 nm is not pure background.")
    print("   %-14s %3s %s" % ("oil", "n", " ".join("%10s" % k for k in KEYS)))
    sunflower = [r for r in rows if r["solvent"] == "sunflower"]
    pooled = {key: [] for key in KEYS}
    byOil = {}
    for row in sunflower:
        byOil.setdefault(row["oil"], {}).setdefault(row["session"], []).append(row)
    for oil, sessions in sorted(byOil.items()):
        if len(sessions) < 2:
            continue
        cells = []
        for key in KEYS:
            means = [statistics.mean([r[key] for r in runs]) for runs in sessions.values()]
            cells.append("%10.2f" % statistics.stdev(means))
            pooled[key].extend([m - statistics.mean(means) for m in means])
        print("   %-14s %3d %s" % (oil, len(sessions), " ".join(cells)))
    print("   %-14s %3s %s" % ("POOLED sd", "",
                               " ".join("%10.2f" % statistics.pstdev(pooled[k]) for k in KEYS)))


if __name__ == "__main__":
    main()
