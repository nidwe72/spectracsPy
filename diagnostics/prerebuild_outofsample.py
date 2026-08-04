"""⭐ THE OUT-OF-SAMPLE TEST — do the candidates survive a rig rebuild? (SPEC_metric_research.md §7.3)

WHY THIS IS THE DECIDING EXPERIMENT. Every score in §3.7-§7.2 comes from the same 28 post-rebuild runs.
They measure separation UNDER THE CONDITIONS EACH CONSTRUCTION WAS BUILT FOR, and say nothing about what
happens when the instrument changes. That distinction is not academic: `DOC_pedestal_correction.md`
chapter 9 showed `r_Q` did NOT survive the 2026-07-29 rebuild.

Edwin's intuition (2026-08-04) is that V3 -- the raw A(574)/A(625) ratio, no baseline of any kind -- is
the best metric despite scoring d = 3.54 against `M`'s 6.91. The claim behind that feeling is
ROBUSTNESS, and robustness is invisible to a Cohen's d computed on one rig state. This script is the
first test in the whole research that can tell "more robust" from "just weaker".

THE TEST SET, and it is genuinely out of sample:
  * PRE-REBUILD, different rig state, different oils, different protocol
  * oilK/oilL = one GREEN oil at 2 and 3 drops;  oilN/oilM = one BROWN oil at 2 and 3 drops
  * 20260727B/E green, 20260727C/D brown -- a second, independent pre-rebuild class contrast

⭐ AND IT ANSWERS SOMETHING THE MAIN CORPUS CANNOT. The post-rebuild corpus has ONE brown fill, so
brown-class dilution invariance is unmeasurable there (§2.1). Pre-rebuild there is a brown pair at two
strengths. This is the only place in the archive where a metric's dilution behaviour can be checked on
a BROWN oil.

⚠ Pre-rebuild runs carry ~3x the seating noise (all_metrics_archive.py warning 1). A metric scoring
lower here than post-rebuild is expected; what matters is the RELATIVE degradation between candidates.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/prerebuild_outofsample.py
"""
import json
import os

import numpy as np

from settling_sweep import despikedAbsorption, asArrays
from metric_features import featuresFor

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "out", "metric_features.json")

# (label, class, paths). Two independent pre-rebuild contrasts.
PRE = [("oilK  green 2 drops", "green", ["measurement_report_oilK_%03d.pdf" % i for i in (1, 2, 3, 4)]),
       ("oilL  green 3 drops", "green", ["measurement_report_oilL_%03d.pdf" % i for i in (1, 2, 3, 4)]),
       ("oilN  brown 2 drops", "brown", ["measurement_report_oilN_%03d.pdf" % i for i in (1, 2, 3, 4)]),
       ("oilM  brown 3 drops", "brown", ["measurement_report_oilM_%03d.pdf" % i for i in (1, 2, 3, 4)]),
       ("20260727B  green", "green", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
       ("20260727E  green", "green", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
       ("20260727C  brown", "brown", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
       ("20260727D  brown", "brown", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]

CANDIDATES = [("M__shipped560_580", "M shipped"),
              ("M_corrected__shipped560_580", "M + pedestal corr"),
              ("M__centred566_582", "M re-centred"),
              ("c16_v3_raw_ratio", "⭐ V3 raw 574/625"),
              ("q_peak_nm", "Q-peak position")]


def cohenD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("nan")


def main():
    grid, rows = None, []
    for label, klass, paths in PRE:
        for path in paths:
            try:
                lam, values = asArrays(despikedAbsorption(path))
            except Exception as error:                     # a missing run must not kill the table
                print("   skipped %s (%s)" % (path, type(error).__name__))
                continue
            if grid is None:
                grid = lam
            rows.append({"set": label, "class": klass,
                         "features": featuresFor(grid, np.interp(grid, lam, values))})
    print("loaded %d PRE-REBUILD runs across %d series\n" % (len(rows), len({r["set"] for r in rows})))

    with open(TABLE) as handle:
        post = json.load(handle)["runs"]

    def pick(source, key, keep):
        return np.array([r["features"][key] for r in source if keep(r)])

    print("=== CLASS SEPARATION — does it survive the rebuild?\n")
    print("%-22s %13s %13s %12s" % ("candidate", "POST-rebuild", "PRE-rebuild", "retained"))
    print("-" * 64)
    for key, label in CANDIDATES:
        postD = cohenD(pick(post, key, lambda r: r["oil"] in ("Kiendler", "Steirerkraft")),
                       pick(post, key, lambda r: r["oil"] == "S-Budget"))
        preD = cohenD(pick(rows, key, lambda r: r["class"] == "green"),
                      pick(rows, key, lambda r: r["class"] == "brown"))
        print("%-22s %13.2f %13.2f %11.0f %%" % (label, postD, preD, 100 * preD / postD))

    print("\n=== ⭐ DILUTION INVARIANCE ON A **BROWN** OIL — impossible on the post-rebuild corpus\n")
    print("%-22s %20s %20s" % ("candidate", "green 2→3 drops", "brown 2→3 drops"))
    print("-" * 64)
    for key, label in CANDIDATES:
        line = "%-22s" % label
        for lo, hi in (("oilK  green 2 drops", "oilL  green 3 drops"),
                       ("oilN  brown 2 drops", "oilM  brown 3 drops")):
            a = pick(rows, key, lambda r, s=lo: r["set"] == s).mean()
            b = pick(rows, key, lambda r, s=hi: r["set"] == s).mean()
            line += " %19s" % ("%+.1f %%" % (100 * (b - a) / abs(a)))
        print(line)
    print("\n   a dilution-INVARIANT metric moves ~0 % when the same oil is prepared stronger.")

    print("\n=== THE SECOND PRE-REBUILD CONTRAST (20260727), independent of oilK-N\n")
    print("%-22s %11s %11s %11s" % ("candidate", "green", "brown", "d"))
    print("-" * 58)
    greenSets = ("20260727B  green", "20260727E  green")
    brownSets = ("20260727C  brown", "20260727D  brown")
    for key, label in CANDIDATES:
        g = pick(rows, key, lambda r: r["set"] in greenSets)
        b = pick(rows, key, lambda r: r["set"] in brownSets)
        print("%-22s %11.4f %11.4f %11.2f" % (label, g.mean(), b.mean(), cohenD(g, b)))


if __name__ == "__main__":
    main()
