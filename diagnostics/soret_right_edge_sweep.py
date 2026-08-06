"""Where should the Soret band END, now that the left edge moves to 448?

§16.11.14 swept the LEFT edge with the right pinned at 460, and slid the whole band. Nobody has ever
swept the RIGHT edge, and the answer may well have changed: 440-460 was a 21-bin window, 448-460 is a
13-bin one, so the averaging that made the left edge irrelevant is now thinner and extra bins on the
red flank are worth more than they used to be.

Two hazards to keep in view while reading the output:
  * the 473 nm LAMP LINE (SPEC_metric_research.md §3.5b -- |d2A/dl2| = 0.191, an order of magnitude
    above any real feature). The metric runs on DE-SPIKED absorbance (median, kernel 7 ~ 20 nm), so it
    is attenuated, not absent. Crossing 473 is the moment to distrust an improvement.
  * the Soret is a FLANK here, so extending right walks DOWN it: added bins carry less class contrast
    but more photons. The sweep is exactly that trade, priced.

Scored on the post-rebuild corpus only (2026-07-29 onward), on the four axes that matter, all at once.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/soret_right_edge_sweep.py
"""
import numpy as np

from settling_sweep import despikedAbsorption, asArrays, plugin, feature
from soret_448_since_0729 import SETS, cohensD

Q = plugin.PB_Q_BAND
WINDOWS = plugin.PB_BASELINE_WINDOWS
RIGHT_EDGES = [456.0, 458.0, 460.0, 464.0, 468.0, 472.0, 476.0, 480.0, 486.0, 492.0, 500.0]
LEFT_EDGES = [448.0, 440.0]

GREEN_FRESH = ["Steirerkraft B", "Steirerkraft C"]
KIENDLER = ["Kiendler A", "Kiendler B", "Kiendler C"]
HALF = "Steirerkraft half-strength"


def spectra():
    """Every run once, as (label, class, lam, baselined values) -- the PDFs are slow, so read them once."""
    out = []
    for folder, label, klass, count in SETS:
        for index in range(1, count + 1):
            corrected = feature.linearBaselineCorrected(
                despikedAbsorption("%s/%03d.pdf" % (folder, index)), WINDOWS)
            lam, values = asArrays(corrected)
            out.append((label, klass, lam, values))
    return out


def score(runs, left, right):
    """The four axes for one candidate window."""
    perFill = {}
    for label, klass, lam, values in runs:
        soret = float(values[(lam >= left) & (lam <= right)].mean())
        q = float(values[(lam >= Q[0]) & (lam <= Q[1])].mean())
        perFill.setdefault((label, klass), []).append(soret / q)
    perFill = {key: np.array(value) for key, value in perFill.items()}

    def pool(labels):
        return np.concatenate([v for (label, _), v in perFill.items() if label in labels])

    greens = pool([label for (label, klass) in perFill if klass == "green"])
    browns = pool([label for (label, klass) in perFill if klass == "brown"])
    strong, half = pool(GREEN_FRESH), pool([HALF])
    # Repeatability: the median within-fill CV, so one wobbly fill cannot carry the column.
    cv = float(np.median([100.0 * v.std(ddof=1) / v.mean() for v in perFill.values()]))
    return {"classD": cohensD(greens, browns),
            "greenD": cohensD(pool(GREEN_FRESH), pool(KIENDLER)),
            "cv": cv,
            "dilution": abs(100.0 * (half.mean() - strong.mean()) / strong.mean()),
            "mean": float(greens.mean())}


def main():
    runs = spectra()
    print("Soret LEFT edge swept over %s, right edge over %s.   Q %s   baseline %s"
          % (LEFT_EDGES, RIGHT_EDGES, Q, WINDOWS))
    print("⚠ the 473 nm lamp line sits between the 472 and 476 rows\n")

    for left in LEFT_EDGES:
        print("=== LEFT EDGE %.0f nm" % left)
        print("%-12s %8s %8s %8s %10s %9s" %
              ("window", "class d", "green d", "CV", "dilution", "M mean"))
        print("-" * 60)
        best = None
        for right in RIGHT_EDGES:
            row = score(runs, left, right)
            marker = ""
            if left == 448.0 and right == 460.0:
                marker = "  <- §7.13 proposal"
            if left == 440.0 and right == 460.0:
                marker = "  <- SHIPPED"
            if right > 473.0 >= RIGHT_EDGES[RIGHT_EDGES.index(right) - 1]:
                print("%-12s %s" % ("", ". . . . . . . . . . 473 nm lamp line crossed . . . . . . . . . ."))
            print("%-12s %8.2f %8.2f %7.2f%% %9.1f%% %9.3f%s"
                  % ("%.0f-%.0f" % (left, right), row["classD"], row["greenD"], row["cv"],
                     row["dilution"], row["mean"], marker))
            if best is None or row["greenD"] > best[1]["greenD"]:
                best = (right, row)
        print("   best within-green separation at right edge %.0f nm (d = %.2f)\n" % (best[0], best[1]["greenD"]))


if __name__ == "__main__":
    main()
