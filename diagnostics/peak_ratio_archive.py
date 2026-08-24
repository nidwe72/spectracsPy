"""The 624/568 PEAK-HEIGHT RATIO, computed over every report on disk. (Edwin's request 2026-08-21)

Edwin marked two peaks on a white-spirit spectrum -- (1) at 568 nm, (2) at 624 nm -- and asked whether
the two oils differ there. They do, and the ratio of the two peak HEIGHTS turned out to separate green
from brown across the whole archive where the shipped `Q%` overlaps. This script is that check, so the
claim can be re-run rather than believed. `SPEC_metric_research.md` section 12 is the write-up.

  R = P2 / P1        P1 = A(568) above the straight chord through 542-546 and 600-606
                     P2 = A(623-626) - A(612-615)

⭐ WHY THIS SHAPE, and every choice in it is forced by something:

  * BOTH TERMS ARE DIFFERENCES of two absorbances, so a FLAT (grey/Mie) pedestal cancels in each of
    them exactly -- see `SPEC_settled_measurement.md` section 52.3, where one turbid fill carried
    +0.078 A of flat pedestal.
  * BOTH TERMS SCALE WITH CONCENTRATION, so the ratio is dilution-invariant on the same algebra as `V`
    (`DOC_metric_algebra.md`).
  * ⛔ NO SORET ANYWHERE. Every window lies between 542 and 626 nm at A = 0.1-0.5. The 448-460 flank
    runs A = 1.2-1.7 with the 440-447 bins past 2.0, and section 16.24's error budget is dominated by
    it. A metric that never touches it has no saturation term.
  * ⛔ THE RIGHT-HAND ANCHOR IS 612-615, NOT ANYTHING PAST 630. The capture clamp is 440-630
    (137 of the archive's reports carry exactly that span), so 632-636 is extrapolation. An earlier
    variant anchored there scored BETTER and is rejected for reading outside the clamp.
  * ⚠ 612 IS THE EARLIEST USABLE LEFT ANCHOR. The 608-610 nm lamp line (section 6 of
    `DOC_lamp_rebuild.md` calls it a Bayer channel crossover) reads 1.6-2.2x the 613 nm value in every
    run on disk, and it already contaminates the 612 nm bin of `20260817LigitschA/007`. Five anchor
    windows were tried (612-615, 613-616, 614-617, 612-616, 613-617); all keep the corridor, the
    worst at +0.317. 612-615 is the widest margin.

⚠ FOUR WARNINGS, all of which matter when reading the output.

  1  ⛔⛔ THE PAPER DIFFUSER DESTROYS THE 624 nm BAND, and that is this metric's one known failure
     mode. `20260727B` is the archive's diffuser A/B test (section 16.7.2f: it came off between run
     003 and run 004). Split by that:
         diffuser IN  (001-003, 008-009)   R = 0.121 +/- 0.126, P2 collapses to 0.000-0.031 A
         diffuser OUT (004-007)            R = 0.635 +/- 0.013, P2 a steady 0.066-0.072 A
     Perfect separation on an INSTRUMENT change, with `Q%` moving barely at all (15.6-17.1 either
     way) and section 16.15.9's table recording the shipped M moving -2.4 %. A 5 nm band near the clamp
     edge is exactly what a diffuser washes out. The five diffuser-IN runs are excluded by
     `DIFFUSER_IN` below and NOTHING ELSE IS. ⚠ Read this as a live warning about
     `SPEC_lamp_rebuild.md`: an optical change that the shipped metric shrugs off can erase this one.
  2  Oil identity comes ONLY from `all_metrics_archive.OILS` plus the two later namings the specs
     make (`20260807D` Steirerkraft, `SPEC_lamp_rebuild.md` section 205; the 2026-08-12 onward
     sessions). The reports carry no sample label. Blank means "not documented".
  3  The 63 loose root one-offs, `20260806A` and the `20260811A` lamp study are NOT scored. 39 of the
     63 have a NEGATIVE R -- no 624 band above the 613 anchor at all -- and 46 fall outside `Q%`'s own
     12-22 verdict band. Mixed rigs, mixed doses, no identity. Unusable for either metric.
  4  `Q%` here is recomputed from each report's own despiked trace, because 176 of the 196 reports
     predate the settling monitor and have no latched answer. Against the 20 that do have one it runs
     +0.019 +/- 0.023 (max 0.106), so it is a faithful proxy -- but it is NOT the shipped read.

⛔ THE THRESHOLD IS FITTED, NOT VALIDATED. T = 0.510 is the midpoint of a corridor drawn on this same
corpus. The pre-rebuild sets and the two white-spirit sessions are genuine out-of-sample confirmations;
nothing else here is.

Reads the `workflow.json` embedded in each report by `pypdf` (section 2 of `SPEC_pdf_export.md`) and
uses the report's OWN despiked trace -- not the shipped code path, because the old reports predate it.

Writes the full matrix to
    spectracs-references/tmp/peak_ratio_archive.csv

Run:
    PYTHONPATH=. venv/bin/python diagnostics/peak_ratio_archive.py
"""
import collections
import csv
import json
import os
import subprocess
import sys
import tempfile

import numpy

ARCHIVE = os.path.expanduser("~/development/spectracs/spectracs-references/tmp")

# ⛔ `oldPdfs` holds the PRE-2026-08-24 copies of every report (Edwin's request). It lives INSIDE the
# archive root, so every tool that walks the tree would otherwise count each run TWICE and silently halve
# every archive statistic. Excluded here, and in peak_ratio_archive / all_metrics_archive /
# regenerate_reports / report_reconstruct / pedestal_slope_era. Earlier backups (tmp_backup_*) were placed
# OUTSIDE tmp/ precisely to avoid this.
EXCLUDED_DIRS = {"oldPdfs", "discussion"}
OUT_CSV = os.path.join(ARCHIVE, "peak_ratio_archive.csv")


def walkReports(root=None):
    """Yield `(folder, name)` for every report PDF under `root`, deterministically ordered.

    ⛔⛔ USE THIS -- never `for folder, subfolders, names in sorted(os.walk(root))`. `sorted()` consumes
    the generator BEFORE the loop body runs, so the in-place `subfolders[:] = [...]` prune that
    `EXCLUDED_DIRS` depends on can no longer influence the traversal: os.walk has already decided where
    it went. Every `oldPdfs/` copy then leaks back in and each run is counted TWICE -- silently, because
    the duplicates parse fine and only inflate whole-corpus counts. Found 2026-08-24 while auditing
    section 16.12.7g's n = 72 (`SPEC_red_ratio_metric.md` section 11.1).

    Pruning is done in place on the live `subfolders` list, and ordering comes from sorting that list
    plus `names` -- which yields the same order the buggy `sorted(os.walk(...))` produced for the
    directories it did visit, so no caller's output is reordered.
    """
    for folder, subfolders, names in os.walk(root if root is not None else ARCHIVE):
        subfolders[:] = sorted(d for d in subfolders if d not in EXCLUDED_DIRS)
        for name in sorted(names):
            if name.endswith(".pdf"):
                yield folder, name


# The two bands Edwin marked, and the anchors each is measured against. See the docstring for why
# every one of these numbers is forced.
P1_PEAK = 568.0
P1_ANCHOR_LEFT = (542.0, 546.0)
P1_ANCHOR_RIGHT = (600.0, 606.0)
P2_BAND = (623.0, 626.0)
P2_ANCHOR = (612.0, 615.0)

THRESHOLD = 0.510                                       # fitted on this corpus, NOT validated -- docstring
CLAMP = (440.0, 630.0)                                  # section 16.10.1's capture clamp

# `20260727B` is the diffuser A/B test of section 16.7.2f: in for 001-003 and 008-009, out for 004-007.
# ⛔ These five are the ONLY runs excluded for an instrument reason. Warning 1 in the docstring.
DIFFUSER_IN = {"20260727B__%03d" % n for n in (1, 2, 3, 8, 9)}

# The opaque fill. `SPEC_settled_measurement.md` section 51 gives it no answer at all under clearing-3.0.
OPAQUE = {"20280819BillaClever__003"}

# Unlabelled or not-an-oil. Scored and printed, never counted into a class.
UNSCORED = {"(root)", "20260806A", "20260811A"}

GREEN = ["20260727B", "20260727E", "20270729B", "20270729C", "20260807D", "20260807A",
         "20260801A", "20260801B", "20260801C", "20260814_Lugitsch_A", "20260817LigitschA",
         "20260812BillJaNatuerlich"]
# ⚠ `20260807C` (Spar Premium ggA) is BROWN by section 16.30.1a's third relabel. `T_V` contradicts that
# relabel (`SPEC_v_metric_integration.md` section 4.3); R agrees with it. Counted as brown here, which is
# the archive's own current label -- see section 12.5.
BROWN = ["20260727C", "20260727D", "20260731A", "20260807B", "20260807C",
         "20260812_BillaClever", "20260812_BillaCleverB", "20280819BillaClever"]
SPIRIT = {"20260821LugitschA": "green", "20260821BillaCleverA": "brown"}


def workflowOf(pdfPath, scratch):
    """The embedded workflow.json, or None if the report predates the attachment."""
    listing = subprocess.run(["pdfdetach", "-list", pdfPath],
                             capture_output=True, text=True).stdout
    index = next((line.split(":")[0].strip() for line in listing.splitlines()
                  if line.strip().endswith(": workflow.json")), None)
    if index is None:
        return None
    target = os.path.join(scratch, "w.json")
    subprocess.run(["pdfdetach", "-save", index, "-o", target, pdfPath],
                   capture_output=True)
    with open(target) as handle:
        return json.load(handle)


def despikedTrace(workflow):
    """The report's own de-spiked absorbance, as (wavelengths, values). The OLD reports have no
    other trace in common with the new ones, which is why this and not the shipped code path."""
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


def bandMean(wavelengths, absorbance, low, high):
    grid = numpy.arange(low, high + 0.001, 0.25)
    return float(numpy.interp(grid, wavelengths, absorbance).mean())


def chordHeight(wavelengths, absorbance, at, left, right):
    """Height of the curve at `at` above the straight line through the two anchor windows."""
    leftCentre, rightCentre = (left[0] + left[1]) / 2.0, (right[0] + right[1]) / 2.0
    leftValue = bandMean(wavelengths, absorbance, *left)
    rightValue = bandMean(wavelengths, absorbance, *right)
    baseline = leftValue + (rightValue - leftValue) * (at - leftCentre) / (rightCentre - leftCentre)
    return float(numpy.interp(at, wavelengths, absorbance)) - baseline


def peakRatio(wavelengths, absorbance):
    p1 = chordHeight(wavelengths, absorbance, P1_PEAK, P1_ANCHOR_LEFT, P1_ANCHOR_RIGHT)
    p2 = bandMean(wavelengths, absorbance, *P2_BAND) - bandMean(wavelengths, absorbance, *P2_ANCHOR)
    return p1, p2, (p2 / p1 if p1 > 0 else float("nan"))


def qPercent(wavelengths, absorbance):
    """`Q%` = -100 V, recomputed from this report's own trace. Warning 4 in the docstring."""
    soret = bandMean(wavelengths, absorbance, 448.0, 460.0)
    valley = bandMean(wavelengths, absorbance, 500.0, 560.0)
    qBand = bandMean(wavelengths, absorbance, 565.0, 580.0)
    return 100.0 * (qBand - valley) / soret


def peak2Position(wavelengths, absorbance):
    """Where the 624 nm band's maximum sits. ⚠ The clamp ENDS at 630, so a value at the top of this
    window means "at or beyond the clamp", NOT "there is no peak"."""
    grid = numpy.arange(614.0, 629.01, 0.25)
    values = numpy.interp(grid, wavelengths, absorbance)
    return float(grid[values.argmax()])


def collect():
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for folder, name in walkReports():
            path = os.path.join(folder, name)
            series = os.path.relpath(folder, ARCHIVE)
            series = "(root)" if series == "." else series
            run = name[:-4]
            key = run if series == "(root)" else "%s__%s" % (series, run)
            workflow = workflowOf(path, scratch)
            if workflow is None:
                continue
            trace = despikedTrace(workflow)
            if trace is None:
                continue
            wavelengths, absorbance = trace
            if wavelengths[0] > 542.0 or wavelengths[-1] < 628.0:
                rows.append({"run": key, "series": series, "note": "coverage %.0f-%.0f"
                             % (wavelengths[0], wavelengths[-1])})
                continue
            p1, p2, ratio = peakRatio(wavelengths, absorbance)
            rows.append({"run": key, "series": series,
                         "wlo": "%.0f" % wavelengths[0], "whi": "%.0f" % wavelengths[-1],
                         "P1": "%.4f" % p1, "P2": "%.4f" % p2, "R": "%.4f" % ratio,
                         "Qpct": "%.3f" % qPercent(wavelengths, absorbance),
                         "peak2nm": "%.1f" % peak2Position(wavelengths, absorbance),
                         "soret": "%.4f" % bandMean(wavelengths, absorbance, 448.0, 460.0),
                         "valley": "%.4f" % bandMean(wavelengths, absorbance, 500.0, 560.0)})
    return rows


def classOf(row):
    if row["series"] in SPIRIT:
        return "spirit"
    if row["series"] in UNSCORED:
        return None
    if row["run"] in OPAQUE or row["run"] in DIFFUSER_IN:
        return None
    if row["series"] in GREEN:
        return "green"
    if row["series"] in BROWN:
        return "brown"
    return None


def describe(label, values):
    array = numpy.array(values)
    print("  %-22s n=%3d   %7.3f +/- %.3f   [%7.3f .. %7.3f]"
          % (label, len(array), array.mean(), array.std(ddof=1), array.min(), array.max()))


def main():
    rows = collect()
    scored = [r for r in rows if "R" in r and numpy.isfinite(float(r["R"]))]
    print("reports with a workflow.json : %d" % len(rows))
    print("scorable (542-628 nm covered): %d" % len(scored))
    print("clamp exactly %.0f-%.0f nm     : %d  <- the archive's own comparable subset"
          % (CLAMP[0], CLAMP[1],
             sum(1 for r in scored if r["wlo"] == "440" and r["whi"] == "630")))

    print("\n=== PER SERIES")
    bySeries = collections.defaultdict(list)
    for row in scored:
        bySeries[row["series"]].append(row)
    for series in sorted(bySeries):
        values = numpy.array([float(r["R"]) for r in bySeries[series]])
        print("  %-26s n=%3d   R %7.3f +/- %6.3f   peak2 median %.1f nm"
              % (series, len(values), values.mean(),
                 values.std(ddof=1) if len(values) > 1 else 0.0,
                 numpy.median([float(r["peak2nm"]) for r in bySeries[series]])))

    print("\n=== THE DIFFUSER SPLIT -- this metric's one known failure mode (warning 1)")
    for label, keys in (("diffuser IN ", DIFFUSER_IN),
                        ("diffuser OUT", {"20260727B__%03d" % n for n in (4, 5, 6, 7)})):
        values = [float(r["R"]) for r in scored if r["run"] in keys]
        if values:
            describe(label, values)

    print("\n=== CLASS SEPARATION -- R against the shipped Q%, same corpus")
    green = [r for r in scored if classOf(r) == "green"]
    brown = [r for r in scored if classOf(r) == "brown"]
    for field, name, greenIsLow in (("R", "R ", False), ("Qpct", "Q%", True)):
        g = numpy.array([float(r[field]) for r in green])
        b = numpy.array([float(r[field]) for r in brown])
        pooled = numpy.sqrt(((len(g) - 1) * g.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                            / (len(g) + len(b) - 2))
        corridor = (b.min() - g.max()) if greenIsLow else (g.min() - b.max())
        print("  %s n=%d/%d  green %7.3f [%7.3f..%7.3f]  brown %7.3f [%7.3f..%7.3f]"
              "  d=%.2f  corridor %+.3f  %s"
              % (name, len(g), len(b), g.mean(), g.min(), g.max(), b.mean(), b.min(), b.max(),
                 abs(g.mean() - b.mean()) / pooled, corridor,
                 "CLEAN" if corridor > 0 else "OVERLAP"))
    wrong = ([r["run"] for r in green if float(r["R"]) < THRESHOLD]
             + [r["run"] for r in brown if float(r["R"]) > THRESHOLD])
    print("  R at T = %.3f -- misclassified: %s" % (THRESHOLD, ", ".join(wrong) or "NONE"))

    print("\n=== OUT-OF-SAMPLE: the two WHITE SPIRIT sessions against that same T")
    for series, expected in SPIRIT.items():
        values = [float(r["R"]) for r in scored if r["series"] == series]
        got = "green" if min(values) > THRESHOLD else ("brown" if max(values) < THRESHOLD else "split")
        print("  %-24s R %s -> %-6s (expected %s) %s"
              % (series, " ".join("%.3f" % v for v in values), got, expected,
                 "OK" if got == expected else "MISMATCH"))

    with open(OUT_CSV, "w", newline="") as handle:
        fields = ["run", "series", "wlo", "whi", "P1", "P2", "R", "Qpct", "peak2nm",
                  "soret", "valley", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("\nwrote %s" % OUT_CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
