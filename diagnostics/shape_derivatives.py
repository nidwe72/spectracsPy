"""Does comparing SLOPES or CURVATURES beat comparing the curves? (`SPEC_history_tracker.md` §6.3)

Edwin 2026-08-14: *"Steirerkraft g.g.A and also Spar Premium g.g.A should trigger the alarm — obviously
the slopes (resp. first derivatives) and also curvatures differ from the Ja! Natürlich runs."*

So run the alarm in derivative space. Three representations of the same baseline-corrected window,
each SNV'd in its own space so `a -> k*a + b` is still quotiented out:

    d0   the curve        - what §3 defines
    d1   its slope        - Savitzky-Golay 1st derivative (kills any additive offset outright)
    d2   its curvature    - Savitzky-Golay 2nd derivative (kills offset AND slope)

⚠ §16.31.5 already rejected derivatives — but it tested derivative EXTREMA, single adaptively located
points, which is why they lost to a 40-point windowed fit ("more points beat better math", §16.31.5a).
This compares the WHOLE derivative curve, every point, so the averaging is retained. Different test,
and §6.3 records that it loses anyway — which sharpens §16.31.5a rather than repeating it.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_derivatives.py
"""
import numpy as np
from scipy.signal import savgol_filter

from settling_sweep import despikedAbsorption, asArrays, feature
from shape_similarity import FILLS, dissimilarity, BASELINE

SMOOTH = 25            # points on the 0.5 nm grid = 12.5 nm, matching §16.31.5
ORDERS = ((0, "curve"), (1, "slope"), (2, "curvature"))
REFERENCE_OIL = "Ja! Natürlich"


def representation(path, window, order):
    """SNV of the curve (order 0), of its slope (1) or of its curvature (2)."""
    lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE))
    pad = 0.5 * SMOOTH                                   # smooth on a wider stretch, then cut
    grid = np.arange(window[0] - pad, window[1] + pad + .01, 0.5)
    y = np.interp(grid, lam, values)
    if order:
        y = savgol_filter(y, window_length=SMOOTH, polyorder=3 + (order == 2), deriv=order)
    y = y[(grid >= window[0]) & (grid <= window[1])]
    return (y - y.mean()) / y.std()


def edwinsCase(window):
    print("=" * 100)
    print("REFERENCE = %s 001,  window %g-%g nm" % (REFERENCE_OIL, window[0], window[1]))
    print("=" * 100)
    curves = {order: {name: [representation(p, window, order) for p in paths]
                      for name, paths in FILLS} for order, _ in ORDERS}
    print("   %-22s %14s %14s %14s" % ("compared against", "D on curve", "D on slope",
                                       "D on curvature"))
    for name, paths in FILLS:
        for i in range(len(paths)):
            if name == REFERENCE_OIL and i == 0:
                continue
            values = [dissimilarity(curves[o][REFERENCE_OIL][0], curves[o][name][i])
                      for o, _ in ORDERS]
            print("   %-22s %13.2f%% %13.2f%% %13.2f%%%s"
                  % ("%s %03d" % (name, i + 1), values[0], values[1], values[2],
                     "   <- own run" if name == REFERENCE_OIL else ""))
    print()
    for order, label in ORDERS:
        own = max(dissimilarity(curves[order][REFERENCE_OIL][0], v)
                  for v in curves[order][REFERENCE_OIL][1:])
        strangers = [(dissimilarity(curves[order][REFERENCE_OIL][0], v), "%s %03d" % (n, j + 1))
                     for n, _ in FILLS if n != REFERENCE_OIL
                     for j, v in enumerate(curves[order][n])]
        nearest, who = min(strangers)
        print("   %-11s worst own run %6.2f%%   nearest stranger %6.2f%% (%s)   margin %+6.2f%%  %s"
              % (label, own, nearest, who, nearest - own, "OK" if nearest > own else "FAILS"))
    print()


def allReferences(window):
    print("=" * 100)
    print("ALL 18 RUNS AS REFERENCE,  window %g-%g nm" % window)
    print("=" * 100)
    for order, label in ORDERS:
        curves = {name: [representation(p, window, order) for p in paths] for name, paths in FILLS}
        passes, margins, failures = 0, [], []
        for name, vectors in curves.items():
            for i, reference in enumerate(vectors):
                own = max(dissimilarity(reference, v) for j, v in enumerate(vectors) if j != i)
                other = min(dissimilarity(reference, v)
                            for o, vs in curves.items() if o != name for v in vs)
                margins.append(other - own)
                if other > own:
                    passes += 1
                else:
                    failures.append("%s %03d" % (name, i + 1))
        print("   %-11s %2d / 18 pass   median margin %+6.2f%%   worst %+6.2f%%   failures: %s"
              % (label, passes, float(np.median(margins)), min(margins),
                 ", ".join(failures) if failures else "none"))
    print()


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    for window in ((560.0, 580.0), (550.0, 600.0)):
        edwinsCase(window)
        allReferences(window)


if __name__ == "__main__":
    main()
