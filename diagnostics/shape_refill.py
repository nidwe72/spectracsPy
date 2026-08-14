"""What does a SECOND FILL of the same oil cost in shape distance?
   (`SPEC_history_tracker.md` §5.2, §5.3 — the nearest thing on disk to "same bag, second press")

The history tracker charts `D` against a stored reference. The alarm is meaningful only if a
re-preparation of the SAME oil lands inside the within-fill floor. Four products in the archive have
more than one fill:

    Steirerkraft   20270729B, 20270729C, 20260807D
    Kiendler       20260801A, 20260801B, 20260801C     ⭐ a DESIGNED dilution series - see below
    Spar S-Budget  20260731A, 20260807B
    Billa Clever   20260812_BillaClever, 20260812_BillaCleverB   (same evening, two fills)

⭐⭐ The Kiendler triple is the important one, because it is the only set where the dose was varied on
purpose and nothing else was (`kiendler_dilution.py`): A = 18 mL + 6 drops, B = A enriched to 7 drops
in place, C = a fresh 18 mL + 7 drops. So B-vs-C prices a re-preparation at constant dose, while
A-vs-B and A-vs-C price ONE DROP. That comparison is what §6.2 of the spec rests on.

⚠ OPPORTUNISTIC — these series were captured for other purposes and span lamp and protocol changes.
This is not the designed σ_fill run (ROADMAP PRIO 2b / §16.34.3); it is the best proxy available
before that run exists, and it is why §9 gates the product on that run rather than on this table.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_refill.py
"""
import numpy as np

from settling_sweep import despikedAbsorption, asArrays, bandMean, feature
from shape_similarity import shape, dissimilarity, template, BASELINE

PRODUCTS = [
    ("Steirerkraft", [("0729B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
                      ("0729C", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
                      ("0807D", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)])]),
    ("Kiendler", [("0801A 6drop", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
                  ("0801B 7drop", ["20260801B/%03d.pdf" % i for i in (1, 2)]),
                  ("0801C 7drop", ["20260801C/%03d.pdf" % i for i in (1, 2)])]),
    ("Spar S-Budget", [("0731A", ["20260731A/%03d.pdf" % i for i in range(1, 7)]),
                       ("0807B", ["20260807B/%03d.pdf" % i for i in (1, 2, 3)])]),
    ("Billa Clever", [("0812A", ["20260812_BillaClever/%03d.pdf" % i for i in (1, 2, 3)]),
                      ("0812B", ["20260812_BillaCleverB/%03d.pdf" % i for i in (1, 2, 3)])]),
]


def amplitude(path):
    lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE))
    return bandMean(lam, values, (560., 580.)) / bandMean(lam, values, (448., 460.))


def run(window):
    print("=" * 100)
    print("WINDOW %g-%g nm" % window)
    print("=" * 100)
    print("   %-15s %8s %10s %10s %9s   %11s %10s" %
          ("product", "fills", "D_within", "D_refill", "ratio", "amp spread", "amp ratio"))
    for name, fills in PRODUCTS:
        curves = {label: [shape(p, window) for p in paths] for label, paths in fills}
        templates = {label: template(v) for label, v in curves.items()}

        within = [dissimilarity(v, templates[label])
                  for label, vectors in curves.items() for v in vectors]
        labels = list(templates)
        between = [dissimilarity(templates[a], templates[b])
                   for i, a in enumerate(labels) for b in labels[i + 1:]]

        amplitudes = {label: np.array([amplitude(p) for p in paths]) for label, paths in fills}
        ampWithin = float(np.mean([100 * a.std(ddof=1) / a.mean() for a in amplitudes.values()]))
        means = np.array([a.mean() for a in amplitudes.values()])
        ampBetween = float(100 * means.std(ddof=1) / means.mean())

        floor, refill = float(np.mean(within)), float(np.mean(between))
        print("   %-15s %8d %9.2f%% %9.2f%% %8.1fx   %9.1f%% %9.1fx" %
              (name, len(fills), floor, refill, refill / floor, ampBetween, ampBetween / ampWithin))

    print()
    for name, fills in PRODUCTS:
        curves = {label: [shape(p, window) for p in paths] for label, paths in fills}
        templates = {label: template(v) for label, v in curves.items()}
        labels = list(templates)
        print("   %s" % name)
        for label in labels:
            values = [dissimilarity(v, templates[label]) for v in curves[label]]
            amp = np.array([amplitude(p) for p in dict(fills)[label]])
            print("      %-12s n=%d   D_within %5.2f%%   amp %.4f" %
                  (label, len(values), np.mean(values), amp.mean()))
        for i, a in enumerate(labels):
            for b in labels[i + 1:]:
                print("      %-12s vs %-12s  D_refill %6.2f%%" %
                      (a, b, dissimilarity(templates[a], templates[b])))
    print()


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    run((560.0, 580.0))
    run((550.0, 600.0))


if __name__ == "__main__":
    main()
