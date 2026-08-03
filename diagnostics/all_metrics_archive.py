"""EVERY metric, for EVERY measurement, of EVERY series in the archive. (Edwin's request 2026-08-02)

The whole-archive form of `all_metrics_table.py`, which covered only the 2026-07-29 and 2026-08-01
sessions. Series are DISCOVERED rather than listed, so nothing on disk can be silently omitted:

  * a directory of NNN.pdf files       -> one series, named after the directory
  * measurement_report_<name>_NNN.pdf  -> one series called <name>, runs NNN
  * measurement_report_<name>.pdf      -> a single-run series called <name>

Everything is computed through the SHIPPED code paths (`DevSpectralPlugin.__computeMetrics`,
`SpectrumFeatureUtil`), so the numbers are what the app would show for that report.

⚠ THREE WARNINGS, all of which matter when reading old rows.

  1  The archive spans a RIG REBUILD (2026-07-29) and several protocol changes. Pre-rebuild series
     carry ~3x the seating noise and are NOT directly comparable with post-rebuild ones.
  2  `r_Q` = -0.0184 was fitted on Kiendler in August, on the POST-rebuild rig, and it belongs to the
     620-630 anchor and to no other. Applying it to a pre-rebuild series assumes r_Q survived the
     rebuild, which is UNTESTED and which the dilution check at the end of this script shows is FALSE.
     Treat `M baseline + pedestal` as exploratory above the rebuild line — `DOC_pedestal_correction.md`
     chapter 10.
  2b THE VERDICT BLOCK IS THE THREE METRICS THE BENCH SHOWS and nothing else (2026-08-03, Edwin):
     `M baseline + pedestal` (T = 10.6), `M baseline` (T = 12.5) and `M raw Soret/Q` (no threshold),
     all on the shipped 620-630 anchor, in the bench's own order. They are on THREE DIFFERENT SCALES:
     read a column against itself across runs, and compare the three only by their verdicts.
     `M 600-630 legacy` is kept further right — §16.21's acetone protocol requires reading acetone runs
     on both anchors — but it is NOT a verdict and carries no threshold that still applies. The 615-630
     columns were dropped outright; that anchor never shipped. See `all_metrics_table.py`'s docstring.
     ℹ The earlier `M clean-anchor` diagnostic is RETIRED -- §16.19.3a answered it (excising the lamp
     line makes r_Q WORSE) and `pedestal_correction.py`'s anchor sweep still reproduces it.
  3  Oil identities are filled in only where a specification or the lab diary names them. Blank means
     "not documented", not "unknown to Edwin".

⭐ The three verdict numbers LEAD both the printed tables and the CSV. They used to sit mid-way
through ~20 columns.

Prints one table per metric group, and writes the whole matrix to
    spectracs-references/tmp/all_metrics_archive.csv

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/all_metrics_archive.py
"""
import csv
import os
import re
import sys

import numpy as np

from settling_sweep import BASE, measure
from all_metrics_table import GROUPS, rowFor

# Only where a doc names the oil. `SPEC_capture_quality.md` §16.7.2o/§16.10.2 (0727 series),
# §16.11.3 / §16.13 / §16.15 (rebuild onward), `SPEC_capability_proof.md` §11.1/§11.4 (oilK–oilN).
OILS = {
    "20260727B": "green", "20260727E": "green",
    "20260727C": "brown", "20260727D": "brown",
    "20270729A_aged24h": "Steirerkraft", "20270729B": "Steirerkraft", "20270729C": "Steirerkraft",
    "20260731A": "Spar S-Budget",
    "20260801A": "Kiendler", "20260801B": "Kiendler", "20260801C": "Kiendler",
    "oilK": "green, 2 drops", "oilL": "green, 3 drops",
    "oilN": "brown, 2 drops", "oilM": "brown, 3 drops",
    "NowSteirerkraft": "Steirerkraft", "NowSteirerkraftA": "Steirerkraft",
    "NowSteirerkraftB": "Steirerkraft", "NowSBudget": "Spar S-Budget",
}

REBUILD = "2026-07-29"                                  # SPEC_capture_quality.md §16.11, the mechanical rebuild

SKIP = {"CapabilityProof_pumpkin-oil_summary", "Spectracs_CapabilityProof_status"}


def discover():
    """[(seriesName, [relativePath, ...])], chronological by the series' earliest capture."""
    series = {}
    for entry in sorted(os.listdir(BASE)):
        full = os.path.join(BASE, entry)
        if os.path.isdir(full):
            runs = sorted(f for f in os.listdir(full) if f.endswith(".pdf"))
            if runs:
                series[entry] = ["%s/%s" % (entry, f) for f in runs]
        elif entry.endswith(".pdf"):
            match = re.match(r"measurement_report_(.+?)(?:_(\d{3}))?\.pdf$", entry)
            if not match or match.group(1) in SKIP:
                continue
            series.setdefault(match.group(1), []).append(entry)
    for paths in series.values():
        paths.sort()
    return sorted(series.items(),
                  key=lambda kv: min(os.path.getmtime(BASE + p) for p in kv[1]))


def main():
    print(__doc__.split("  * a directory")[0].strip())
    print()

    rows, skipped = [], []
    for name, paths in discover():
        for path in paths:
            label = os.path.basename(path)[:-4]
            run = label[-3:] if label[-3:].isdigit() else "001"
            try:
                values = rowFor(path)
            except Exception as error:                       # old reports may carry no workflow JSON
                skipped.append((path, "%s: %s" % (type(error).__name__, error)))
                continue
            values.update({"series": name, "oil": OILS.get(name, ""), "run": run, "path": path,
                           "captured": __import__("datetime").datetime.fromtimestamp(
                               os.path.getmtime(BASE + path)).strftime("%Y-%m-%d %H:%M")})
            rows.append(values)
        print("  ...%-22s %2d run(s)" % (name, len(paths)), file=sys.stderr)

    def cell(value):
        return "%12s" % ("—" if value is None else "%.4f" % value)

    for title, columns in GROUPS:
        print("=== %s" % title)
        print("   %-17s %-4s %-16s %s"
              % ("series", "run", "oil", "".join("%12s" % short for _, short in columns)))
        print("   " + "-" * (41 + 12 * len(columns)))
        last, rebuildShown = None, False
        for values in rows:
            if last is not None and values["series"] != last:
                summariseSeries(rows, last, columns, cell)
            if not rebuildShown and values["captured"] >= REBUILD:
                print("   %s RIG REBUILD %s %s" % ("-" * 26, REBUILD[:10], "-" * 26))
                print("   everything BELOW this line is post-rebuild and mutually comparable;")
                print("   everything above carries ~3x the seating noise and a different protocol.\n")
                rebuildShown = True
            last = values["series"]
            print("   %-17s %-4s %-16s %s" % (values["series"], values["run"], values["oil"],
                                              "".join(cell(values[key]) for key, _ in columns)))
        summariseSeries(rows, last, columns, cell)
        print()

    if skipped:
        print("=== SKIPPED — no usable absorbance in the embedded workflow")
        for path, reason in skipped:
            print("   %-40s %s" % (path, reason))
        print()

    dilutionCheck()

    fields = (["series", "oil", "run", "captured", "path"]
              + [key for _, cs in GROUPS for key, _ in cs])
    out = os.path.join(BASE, "all_metrics_archive.csv")
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for values in rows:
            writer.writerow({k: values[k] for k in fields})
    print("CSV written: %s" % out)
    print("%d measurements across %d series, %d metrics each; %d skipped."
          % (len(rows), len({r["series"] for r in rows}), len(fields) - 5, len(skipped)))


DILUTION_PAIRS = [
    ("green  oilK -> oilL", "pre-rebuild", 2.0, ["measurement_report_oilK_%03d.pdf" % i for i in (1, 2, 3, 4)],
     3.0, ["measurement_report_oilL_%03d.pdf" % i for i in (1, 2, 3, 4)]),
    ("brown  oilN -> oilM", "pre-rebuild", 2.0, ["measurement_report_oilN_%03d.pdf" % i for i in (1, 2)],
     3.0, ["measurement_report_oilM_%03d.pdf" % i for i in (1, 2, 3, 4)]),
    ("green  0729B -> 0729C", "POST-rebuild", 0.197, ["20270729B/%03d.pdf" % i for i in range(1, 7)],
     0.230, ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
]


def dilutionCheck():
    """⭐ The check the whole-archive view makes possible, and it is the most informative thing here.

    r_Q was fitted on ONE oil (Kiendler) on the POST-rebuild rig. Every within-oil dilution pair in the
    archive is therefore an OUT-OF-SAMPLE test of it: if the correction is right, it should push each
    pair's log-log slope TOWARD zero. It does exactly that on the post-rebuild pair and the opposite on
    both pre-rebuild ones -- which says r_Q is tied to the RIG STATE, not universal.

    ⚠ THIS TEST IS RUN ON THE LEGACY 600-630 ANCHOR, deliberately: it is the historical record of how
    the correction was validated, and its published numbers (-0.12 -> -0.00) are quoted throughout §16.
    The SHIPPED 620-630 anchor's own dilution slopes are in `far_anchor_sweep.py` and §16.20.4."""
    print("=== ⭐ OUT-OF-SAMPLE TEST — what the correction does to the archive's DILUTION PAIRS")
    print("   s = 0 is perfect dilution invariance. r_Q was fitted on post-rebuild Kiendler only,")
    print("   so every pair below is out-of-sample for it.")
    print()
    print("   %-24s %-13s %6s %20s %20s"
          % ("pair", "rig state", "span", "LEGACY   chg   s", "LEG CORR  chg   s"))
    print("   " + "-" * 88)

    def series(paths):
        runs = [measure(p) for p in paths]
        return (np.array([r["S/Q linear base"] for r in runs]),
                np.array([r["A_Soret linear"] / (r["A_Q linear"] - R_Q) for r in runs]))

    for label, state, low, lowPaths, high, highPaths in DILUTION_PAIRS:
        shippedLow, correctedLow = series(lowPaths)
        shippedHigh, correctedHigh = series(highPaths)
        span, cells = high / low, []
        for before, after in ((shippedLow, shippedHigh), (correctedLow, correctedHigh)):
            change = after.mean() / before.mean() - 1
            cells.append("%+8.1f%% %7.2f" % (100 * change,
                                             np.log(after.mean() / before.mean()) / np.log(span)))
        print("   %-24s %-13s %5.2fx %20s %20s" % (label, state, span, cells[0], cells[1]))
    print()
    print("   ⇒ On the POST-rebuild pair the correction moves the slope from -0.12 to -0.00 — it works,")
    print("     and it is NOT circular: r_Q came from Kiendler, this pair is Steirerkraft.")
    print("   ⇒ On BOTH pre-rebuild pairs it moves them from ~0 to ~+0.27 — it makes them WORSE.")
    print("   ⇒ READING: r_Q is real and transfers BETWEEN OILS, but NOT across a rig rebuild. It is a")
    print("     per-rig-state calibration constant, and it must never be applied retroactively to")
    print("     pre-rebuild data. The `M 600-630 legacy corrected` column is therefore MEANINGLESS")
    print("     above the rebuild line — it is printed only to show that it is.")
    print()


R_Q = -0.0246                                           # DOC_pedestal_correction.md §6


def summariseSeries(rows, series, columns, cell):
    """mean (n >= 1) and SD (n >= 2), labelled with the series so the row stands on its own."""
    group = [r for r in rows if r["series"] == series]
    for label, minimum, function in (("mean", 1, np.mean),
                                     ("sd", 2, lambda v: np.std(v, ddof=1))):
        cells = []
        for key, _ in columns:
            values = [r[key] for r in group if r[key] is not None]
            cells.append(cell(function(values) if len(values) >= minimum else None))
        print("   %-17s %-4s %-16s %s"
              % ("→ " + series, label, "n=%d" % len(group), "".join(cells)))
    print()


if __name__ == "__main__":
    main()
