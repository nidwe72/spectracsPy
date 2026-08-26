"""Which band should A624 be measured AGAINST? The full archive, not one session. (Edwin, 2026-08-26)

Rv's numerator is fixed at 622-627. Everything else is a choice, and the question this answers is
whether the SHIPPED reference (A_Q 565-580, datum A_valley 500-560) is the best available one -- judged
on two things that pull against each other:

  DRIFT/sd    the same oil measured in DIFFERENT SESSIONS, session-mean spread over within-session sd.
              This is the property the 08-24 -> 08-26 Lugitsch step exposed.   LOWER is better.
  corr/drift  the green/brown corridor expressed in units of that same drift.  HIGHER is better.

⛔ Judging a window on the corpus you then quote it against is fitting. Nothing here changes the metric;
it measures what the knob does, so a pre-registered test can be aimed properly (SPEC_metric_research §7).

⛔ Two INSTRUMENT features sit in the region: the 581 nm reference minimum and the 609 nm Bayer
crossover (DOC_lamp_rebuild sections 326 and 6). A window that scores well by containing one of them has
learned the rig, not the oil, and is marked as such.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/reference_band_scan.py
"""
import os
import pickle
import sys
import tempfile

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import all_metrics_archive as metrics
from solvent_colour_separation import SUNFLOWER as INDEX_MATCHED
from d2r_all_runs import SERIESOIL, TODAY, EXCLUDED

CACHE = "/tmp/claude-1000/-home-nidwe72-development-spectracs-spectracsPy/105990a7-14f7-4f84-a40b-cf4d764597f2/scratchpad/refscan_traces.pkl"
RED = (622.0, 627.0)
VALLEY = (500.0, 560.0)
ARTEFACTS = ((579.0, 584.0, "581 reference minimum"), (605.0, 613.0, "609 Bayer crossover"))


def collect():
    """Every labelled run that covers 500-627 nm. Cached: the PDF extraction is the slow part."""
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as handle:
            return pickle.load(handle)
    rows = []
    indexed = {relative for _, relative in INDEX_MATCHED}
    with tempfile.TemporaryDirectory() as scratch:
        def take(relative, label, oil, solvent):
            if relative in EXCLUDED:
                return
            workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
            if workflow is None:
                return
            trace = archive.despikedTrace(workflow)
            if trace is None:
                return
            nm, absorbance = trace
            if nm[0] > 500.0 or nm[-1] < 627.5:
                return
            rows.append({"run": relative, "session": relative.split("/")[0], "oil": oil,
                         "class": label, "solvent": solvent, "nm": nm, "a": absorbance})

        for label, relative in INDEX_MATCHED:
            series = relative.split("/")[0]
            oil = "Lugitsch" if "ugitsch" in series else "Billa Clever"
            take(relative, label, oil, "spirit" if series.startswith("20260821") else "sunflower")
        for folder, name in archive.walkReports():
            series = os.path.relpath(folder, archive.ARCHIVE)
            series = "(root)" if series == "." else series
            key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
            relative = os.path.relpath(os.path.join(folder, name), archive.ARCHIVE)
            if relative in indexed:
                continue
            label = archive.classOf({"series": series, "run": key})
            if label not in ("green", "brown"):
                continue
            take(relative, label, SERIESOIL.get(series, metrics.OILS.get(series, series)), "isopropanol")
        for series, (oil, label) in TODAY.items():
            folder = os.path.join(archive.ARCHIVE, series)
            for name in sorted(f for f in os.listdir(folder) if f.endswith(".pdf")):
                take("%s/%s" % (series, name), label, oil, "sunflower")
    with open(CACHE, "wb") as handle:
        pickle.dump(rows, handle)
    return rows


def band(row, low, high):
    inside = row["a"][(row["nm"] >= low) & (row["nm"] <= high)]
    return float(inside.mean()) if inside.size else float("nan")


def ratios(rows, low, high, datum=True):
    out = []
    for row in rows:
        v = band(row, *VALLEY) if datum else 0.0
        denominator = band(row, low, high) - v
        out.append((band(row, *RED) - v) / denominator if denominator > 0.01 else float("nan"))
    return numpy.array(out)


def evaluate(rows, low, high, datum=True):
    """DRIFT/sd pooled over every oil measured in 2+ sessions; corridor over the scored runs."""
    values = ratios(rows, low, high, datum)
    if not numpy.isfinite(values).all():
        return None
    groups = {}
    for row, value in zip(rows, values):
        groups.setdefault((row["solvent"], row["oil"]), {}).setdefault(row["session"], []).append(value)
    drifts, withins = [], []
    for sessions in groups.values():
        usable = {s: v for s, v in sessions.items() if len(v) >= 2}
        if len(usable) < 2:
            continue
        means = numpy.array([numpy.mean(v) for v in usable.values()])
        pooled = numpy.sqrt(numpy.mean([numpy.var(v, ddof=1) for v in usable.values()]))
        if pooled <= 0:
            continue
        drifts.append(means.max() - means.min())
        withins.append(pooled)
    if not drifts:
        return None
    driftSd = float(numpy.mean(numpy.array(drifts) / numpy.array(withins)))
    drift = float(numpy.mean(drifts))
    green = values[[r["class"] == "green" for r in rows]]
    brown = values[[r["class"] == "brown" for r in rows]]
    pooled = numpy.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                        / (len(green) + len(brown) - 2))
    # ⭐ errors at the BEST threshold this candidate can achieve. Candidates live on different scales,
    # so a fixed cut would compare nothing; the corridor-overlap count I used first was far harsher
    # than misclassification and made the shipped window look broken when it scores 1/107.
    best = min(int((green < cut).sum() + (brown >= cut).sum())
               for cut in numpy.unique(numpy.concatenate([green, brown])))
    # a denominator near zero amplifies noise however good the separation looks
    thin = float(numpy.min([band(r, low, high) - (band(r, *VALLEY) if datum else 0.0) for r in rows]))
    return {"driftSd": driftSd, "corridor": float(green.min() - brown.max()) / drift,
            "cohen": float(abs(green.mean() - brown.mean()) / pooled),
            "errors": best, "thin": thin, "nDrift": len(drifts)}


def artefactNote(low, high):
    hits = [name for lo, hi, name in ARTEFACTS if high > lo and low < hi]
    return ("CONTAINS the " + " and the ".join(hits)) if hits else ""


def main():
    rows = collect()
    scored = [r for r in rows if r["class"] in ("green", "brown")]
    print("archive: %d runs covering 500-627 nm  (%d green, %d brown, %d unlabelled)"
          % (len(rows), sum(1 for r in scored if r["class"] == "green"),
             sum(1 for r in scored if r["class"] == "brown"),
             len(rows) - len(scored)))
    oils = {}
    for row in rows:
        oils.setdefault((row["solvent"], row["oil"]), set()).add(row["session"])
    repeat = {k: v for k, v in oils.items() if len(v) >= 2}
    print("oils measured in 2+ sessions (these carry the drift): %s\n"
          % ", ".join("%s/%s x%d" % (k[1], k[0][:3], len(v)) for k, v in sorted(repeat.items())))

    print("%-26s %9s %10s %8s %7s %8s  %s"
          % ("reference for A624", "DRIFT/sd", "corr/drift", "Cohen d", "errors", "min den", "note"))
    print("%-26s %9s %10s %8s %7s %8s" % ("", "lower", "higher", "higher",
                                          "/%d" % len(scored), "thicker"))
    named = [("Q 565-580  SHIPPED", 565., 580., True), ("Q 555-565", 555., 565., True),
             ("Q 558-566  blue flank", 558., 566., True), ("Q 560-568  blue flank", 560., 568., True),
             ("Q 562-572", 562., 572., True), ("Q 565-575", 565., 575., True),
             ("Q 570-580", 570., 580., True), ("Q 573-581", 573., 581., True),
             ("Q 576-584", 576., 584., True), ("Soret 448-460", 448., 460., True),
             ("Q 565-580 no datum", 565., 580., False)]
    for name, low, high, datum in named:
        out = evaluate(scored, low, high, datum)
        if out is None:
            print("%-26s %9s" % (name, "n/a"))
            continue
        print("%-26s %9.2f %10.2f %8.2f %7d %8.4f  %s"
              % (name, out["driftSd"], out["corridor"], out["cohen"], out["errors"], out["thin"],
                 artefactNote(low, high)))

    print("\n=== SWEEP, 10 nm windows, artefact-free only")
    best = []
    for low in numpy.arange(500.0, 606.0, 2.0):
        high = low + 10.0
        if artefactNote(low, high):
            continue
        out = evaluate(scored, low, high, True)
        if out is not None:
            best.append((out["corridor"], low, high, out))
    best = [b for b in best if b[3]["thin"] > 0.02]      # reject denominators that collapse
    for corridor, low, high, out in sorted(best, reverse=True)[:8]:
        print("  %5.0f-%-5.0f  DRIFT/sd %5.2f   corr/drift %6.2f   Cohen d %5.2f   errors %2d   "
              "min den %.4f" % (low, high, out["driftSd"], corridor, out["cohen"], out["errors"],
                                out["thin"]))


if __name__ == "__main__":
    main()
