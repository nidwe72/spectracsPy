"""Is 440-447 a class-INDEPENDENT plateau? The test behind §7.13's interpretation.

If those bins are the camera's floor rather than the oil, they should read nearly the SAME absorbance
for a green and for a brown -- while 448-460, which is real, should track the class. That would make
the shipped Soret window carry an additive, oil-independent constant, which dilutes contrast in a ratio.

Reports, per fill, on the RAW de-spiked absorbance (no baseline -- the baseline would mask the levels):
  A(440-447), A(448-460), their ratio, and the between-class spread of each.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/soret_deadband_plateau.py
"""
import numpy as np

from settling_sweep import despikedAbsorption, asArrays
from soret_448_since_0729 import SETS

DEAD, LIVE, Q = (440.0, 447.0), (448.0, 460.0), (560.0, 580.0)


def bands(path):
    lam, values = asArrays(despikedAbsorption(path))

    def band(window):
        return float(values[(lam >= window[0]) & (lam <= window[1])].mean())

    return band(DEAD), band(LIVE), band(Q)


def main():
    print("RAW de-spiked absorbance, no baseline.   dead %s   live %s   Q %s\n" % (DEAD, LIVE, Q))
    print("%-24s %-6s %2s %12s %12s %10s" % ("fill", "class", "n", "A 440-447", "A 448-460", "A Q"))
    print("-" * 70)
    perClass = {}
    for folder, label, klass, count in SETS:
        rows = np.array([bands("%s/%03d.pdf" % (folder, index)) for index in range(1, count + 1)])
        print("%-24s %-6s %2d  %6.4f+-%.4f  %6.4f+-%.4f  %6.4f"
              % (label, klass, count, rows[:, 0].mean(), rows[:, 0].std(ddof=1),
                 rows[:, 1].mean(), rows[:, 1].std(ddof=1), rows[:, 2].mean()))
        perClass.setdefault(klass, []).append(rows)

    print("\n=== CLASS MEANS -- does the dead band discriminate at all?")
    print("%-8s %2s %12s %12s %10s" % ("class", "n", "A 440-447", "A 448-460", "A Q"))
    print("-" * 48)
    means = {}
    for klass, blocks in perClass.items():
        pooled = np.concatenate(blocks)
        means[klass] = pooled.mean(axis=0)
        print("%-8s %2d %12.4f %12.4f %10.4f" % (klass, len(pooled), *means[klass]))

    if "green" in means and "brown" in means:
        print("\n=== GREEN vs BROWN, band by band")
        for index, name in ((0, "dead 440-447"), (1, "live 448-460"), (2, "Q 560-580")):
            green, brown = means["green"][index], means["brown"][index]
            print("  %-14s green %.4f   brown %.4f   green/brown %5.2f   contrast %+6.1f%%"
                  % (name, green, brown, green / brown, 100.0 * (green - brown) / brown))


if __name__ == "__main__":
    main()


# --------------------------------------------------------------- the sharper test (added 2026-08-06)
# Under Beer-Lambert with an honest detector, A(dead)/A(live) is a SHAPE CONSTANT: both bands scale
# with concentration, so their ratio is a property of the pigment and must not depend on how strong
# the preparation is. If the dead band is compressed by a detector floor, the ratio must FALL as the
# sample darkens -- the floor eats a larger share of the darker band. That is a one-line prediction
# with a sign, and the fills happen to span a 2x concentration range.
def compression():
    print("\n\n=== THE COMPRESSION TEST -- A(dead)/A(live) must be constant, and is not")
    print("%-24s %-6s %10s %10s %8s" % ("fill", "class", "A live", "A dead", "ratio"))
    print("-" * 62)
    points = []
    for folder, label, klass, count in SETS:
        rows = np.array([bands("%s/%03d.pdf" % (folder, index)) for index in range(1, count + 1)])
        dead, live = rows[:, 0].mean(), rows[:, 1].mean()
        points.append((live, dead / live, label, klass))
    for live, ratio, label, klass in sorted(points):
        print("%-24s %-6s %10.4f %10.4f %8.3f" % (label, klass, live, live * ratio, ratio))
    live = np.array([p[0] for p in points])
    ratio = np.array([p[1] for p in points])
    slope, intercept = np.polyfit(live, ratio, 1)
    correlation = np.corrcoef(live, ratio)[0, 1]
    print("\n  fit: ratio = %+.4f * A_live %+.4f      r = %+.3f  (n = %d fills)"
          % (slope, intercept, correlation, len(points)))
    print("  ⇒ across the observed span (%.2f to %.2f A) the shape 'constant' moves %.3f -> %.3f, i.e. %+.1f%%"
          % (live.min(), live.max(), intercept + slope * live.min(), intercept + slope * live.max(),
             100.0 * (slope * (live.max() - live.min())) / (intercept + slope * live.min())))


compression()
