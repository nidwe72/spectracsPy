"""SHAPE distance between spectra — the concept, and whether it separates oils at all.
   (`SPEC_history_tracker.md` §3, §5.1. Edwin 2026-08-13: "could we put this similarity into a
   mathematical concept?")

After the linear baseline a run is a vector over a window. Everything the tracker must ignore —
concentration, seating, exposure — acts on it as `a -> k*a + b` (§16.7.2h's own error model). SNV
*within the window* is exactly the quotient map for that two-parameter group, so what survives is
pure shape, and similarity is the angle between two SNV vectors:

    D = sqrt(1 - r^2)  =  sin(angle)  =  the fraction of a run's own variation that the other curve
                                         CANNOT explain, after a free rescale and offset

reported in %, where `r` is the Pearson correlation over the window. ⚠ SNV is taken over the ANALYSIS
window, not the 448-629 capture window — otherwise the Soret dominates the sd and the Q-band shape is
a rounding error (the same choice that split §16.31 from §16.30.7).

Two numbers decide whether this is a metric or a mirage:
    D_within  - run vs its own fill's template  -> the shape-repeatability floor
    D_between - fill template vs fill template  -> whether oils differ in shape at all
⛔ and the risk is that every pumpkin oil correlates at r = 0.999 because they share one rising flank,
in which case D_between ~ D_within and the quantity says nothing. So the same table is recomputed
after removing the COMMON shape (PC1 across all fills), which is where any real difference lives.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_similarity.py
"""
import os

import numpy as np

from settling_sweep import despikedAbsorption, asArrays, bandMean, feature

# The six oils of `SPEC_history_tracker.md` §5, one fill each — the `all_oils_panel` set.
FILLS = [("Ja! Natürlich", ["20260812BillJaNatuerlich/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Steirerkraft g.g.A.", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar Steirisches", ["20260807A/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar Premium g.g.A.", ["20260807C/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar S-Budget", ["20260807B/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Billa Clever", ["20260812_BillaCleverB/%03d.pdf" % i for i in (1, 2, 3)])]
# The shipped chord anchors. ⛔ The far one sits ON the Qy band (`KB` §4.1a, ~625 nm), so a greener
# oil raises it, steepens the fitted line and gets MORE subtracted from the Q band it is measured on
# (SPEC_history_tracker.md §7.1a). Set SPECTRACS_FAR_ANCHOR=596-604 to re-run everything on a far
# foot that clears both the Qy rise and the 607.5-609 lamp lines.
#     PYTHONPATH=... SPECTRACS_FAR_ANCHOR=596-604 ./venv/bin/python diagnostics/<script>.py
# ⚠ Default unchanged, so every number already published reproduces byte-for-byte.
FAR = os.environ.get("SPECTRACS_FAR_ANCHOR", "620-630")
BASELINE = ((520.0, 540.0), tuple(float(x) for x in FAR.split("-")))


def shape(path, window):
    """SNV over the window alone -> the point on the shape sphere."""
    spectrum = feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE)
    lam, values = asArrays(spectrum)
    grid = np.arange(window[0], window[1] + .01, 0.5)
    y = np.interp(grid, lam, values)
    return (y - y.mean()) / y.std()


def dissimilarity(a, b):
    """sqrt(1 - r^2) in %, symmetric, zero iff the two agree up to scale and offset."""
    r = float(np.corrcoef(a, b)[0, 1])
    return 100.0 * np.sqrt(max(0.0, 1.0 - r * r))


def template(vectors):
    """Fréchet mean direction on the sphere: average, then re-normalise back onto it."""
    mean = np.mean(vectors, axis=0)
    return (mean - mean.mean()) / mean.std()


def analyse(window, label):
    curves = {name: [shape(p, window) for p in paths] for name, paths in FILLS}
    templates = {name: template(v) for name, v in curves.items()}

    print("=" * 108)
    print("%s   window %g-%g nm, %d points" % (label, window[0], window[1],
                                               len(next(iter(templates.values())))))
    print("=" * 108)

    for stage in ("raw shape", "after removing the COMMON shape (PC1)"):
        if stage.startswith("after"):
            stack = np.array([v for vectors in curves.values() for v in vectors])
            centred = stack - stack.mean(axis=0)
            pc1 = np.linalg.svd(centred, full_matrices=False)[2][0]
            common = stack.mean(axis=0)

            def strip(vector):
                residual = vector - common
                return residual - np.dot(residual, pc1) * pc1

            curves = {n: [strip(v) for v in vs] for n, vs in curves.items()}
            templates = {n: np.mean(vs, axis=0) for n, vs in curves.items()}

        print("\n--- %s ---" % stage)
        withins = []
        print("   %-22s %14s   %s" % ("fill", "D_within %", "run-vs-own-template"))
        for name, vectors in curves.items():
            values = [dissimilarity(v, templates[name]) for v in vectors]
            withins.extend(values)
            print("   %-22s %14.3f   %s" % (name, np.mean(values),
                                            "  ".join("%.3f" % x for x in values)))
        floor = float(np.mean(withins))
        print("   %-22s %14.3f" % ("POOLED FLOOR", floor))

        names = list(templates)
        print("\n   D_between %% (fill template vs fill template)")
        print("   %-22s%s" % ("", "".join("%9s" % n[:8] for n in names)))
        offDiagonal = []
        for a in names:
            row = []
            for b in names:
                value = 0.0 if a == b else dissimilarity(templates[a], templates[b])
                row.append(value)
                if a != b:
                    offDiagonal.append(value)
            print("   %-22s%s" % (a[:22], "".join("%9.2f" % x for x in row)))
        between = float(np.mean(offDiagonal))
        print("   mean D_between = %.3f %%   vs floor %.3f %%   ->  RATIO %.1f x"
              % (between, floor, between / floor))


def amplitudeContrast():
    """The same fills judged by AMPLITUDE — what the M448 family reads."""
    print("\n" + "=" * 108)
    print("CONTRAST: amplitude within the same fill")
    print("=" * 108)
    print("   %-22s %12s %12s %10s" % ("fill", "B_Q/B_Soret", "sd", "CV %"))
    for name, paths in FILLS:
        values = []
        for path in paths:
            lam, v = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE))
            values.append(bandMean(lam, v, (560., 580.)) / bandMean(lam, v, (448., 460.)))
        values = np.array(values)
        print("   %-22s %12.4f %12.4f %10.1f"
              % (name, values.mean(), values.std(ddof=1), 100 * values.std(ddof=1) / values.mean()))


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    analyse((560.0, 580.0), "EDWIN'S REGION")
    analyse((550.0, 600.0), "WIDER Q WINDOW — the one §7 adopts")
    amplitudeContrast()


if __name__ == "__main__":
    main()
