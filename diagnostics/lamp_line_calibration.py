"""R1b — is the wavelength scale stable across sessions? (docs/SPEC_metric_research.md §3.6a)

WHY THIS GATES EVERYTHING. §3.6 found the Q band's PEAK POSITION separates the oil classes by 0.85 nm,
with no baseline and no amplitude -- the strongest candidate in the research spec. But a position
metric measures WHERE a feature sits, and §3.4 says every oil was measured on its own evening. If the
instrument's wavelength scale drifts between evenings, a shift of the SCALE is indistinguishable from
a shift of the PIGMENT, and C14 is measuring the rig.

The two lamp lines of §3.5(b) -- 473 and 608 nm -- are fixed by physics, so they are a free internal
ruler. A first pass with a crude centroid was INCONCLUSIVE: its own scatter (0.12-0.33 nm) was a large
fraction of the 0.85 nm signal, and the two lines appeared to move in OPPOSITE directions between
sessions, which a rigid calibration offset cannot do. That smelled of the estimator, not the rig.

WHAT THIS DOES DIFFERENTLY. The crude version took a centroid over a fixed span, so the sloping
continuum under each line dragged the answer -- badly for the 608 line, which sits on the Qy flank.
Here the continuum is fitted from the WINGS ONLY (quadratic, so a curved flank is handled), subtracted,
and a GAUSSIAN is fitted to what is left. The centre of that Gaussian is the line position, on the same
footing as the Savitzky-Golay + parabolic refinement used for the Q peak.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/lamp_line_calibration.py
"""
import numpy as np
from scipy.optimize import curve_fit

from metric_research_overview import load

# (nominal centre, core half-width, wing half-width). The core is what the Gaussian is fitted to; the
# wings are what the continuum is fitted to. Core must cover the line and no more -- 607's FWHM was
# measured at 2.7 nm (`DOC_metric_algebra.md` §5.9), so +-4 nm is a comfortable core for both.
LINES = [(473.0, 4.0, 11.0), (608.2, 4.0, 11.0)]
SIGNAL = 0.85           # the Q-band class separation this ruler has to be small against (§3.6)


def gaussian(x, amplitude, centre, sigma, offset):
    return amplitude * np.exp(-0.5 * ((x - centre) / sigma) ** 2) + offset


def lineCentre(grid, values, centre, coreHalf, wingHalf):
    """Sub-bin line position: quadratic continuum from the WINGS only, then a Gaussian on the core."""
    wing = (((grid >= centre - wingHalf) & (grid < centre - coreHalf))
            | ((grid > centre + coreHalf) & (grid <= centre + wingHalf)))
    continuum = np.polyfit(grid[wing], values[wing], 2)
    core = (grid >= centre - coreHalf) & (grid <= centre + coreHalf)
    x, y = grid[core], values[core] - np.polyval(continuum, grid[core])
    try:
        fit, _ = curve_fit(gaussian, x, y, p0=[max(y.max(), 1e-6), x[np.argmax(y)], 1.0, 0.0],
                           maxfev=20000)
    except RuntimeError:
        return float("nan"), float("nan")
    return float(fit[1]), float(abs(fit[2]))


def main():
    grid, runs = load()
    sessions = {"Kiendler": "20260801", "Steirerkraft": "20270729", "S-Budget": "20260731"}

    print("=== R1b  LAMP-LINE POSITIONS — Gaussian on a wing-fitted continuum")
    print("   The ruler must be SMALL against the %.2f nm class signal it is checking.\n" % SIGNAL)
    table = {}
    for nominal, coreHalf, wingHalf in LINES:
        print("   line near %.1f nm" % nominal)
        print("   %-14s %-10s %18s %14s" % ("oil", "session", "centre (nm)", "FWHM (nm)"))
        print("   " + "-" * 60)
        perOil = {}
        for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
            rows = [v for _, o, v in runs if o == oil]
            found = [lineCentre(grid, v, nominal, coreHalf, wingHalf) for v in rows]
            centres = np.array([c for c, _ in found])
            widths = np.array([s for _, s in found]) * 2.3548
            perOil[oil] = centres
            print("   %-14s %-10s %9.3f ± %-6.3f %8.2f ± %.2f"
                  % (oil, sessions[oil], centres.mean(), centres.std(ddof=1),
                     np.nanmean(widths), np.nanstd(widths, ddof=1)))
        means = np.array([perOil[o].mean() for o in perOil])
        table[nominal] = perOil
        print("   %-14s %-10s spread of session means: %.3f nm   (signal %.2f nm)\n"
              % ("", "⇒", means.max() - means.min(), SIGNAL))

    # --- the two checks that decide it -------------------------------------------------------
    print("=== VERDICT")
    offsets = {}
    for nominal in table:
        means = {o: table[nominal][o].mean() for o in table[nominal]}
        grand = np.mean(list(means.values()))
        offsets[nominal] = {o: means[o] - grand for o in means}
    print("   per-session offset from that line's own grand mean:")
    print("   %-14s %12s %12s %14s" % ("oil", "473 nm", "608 nm", "agree in sign?"))
    print("   " + "-" * 56)
    agree = True
    for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
        a, b = offsets[473.0][oil], offsets[608.2][oil]
        same = (a >= 0) == (b >= 0)
        agree = agree and same
        print("   %-14s %+12.3f %+12.3f %14s" % (oil, a, b, "yes" if same else "NO"))
    worst = max(abs(v) for line in offsets.values() for v in line.values()) * 2
    print("\n   worst peak-to-peak session offset on either line : %.3f nm" % worst)
    print("   the Q-band class separation it must not explain  : %.3f nm" % SIGNAL)
    print("   ratio (ruler / signal)                           : %.0f %%" % (100 * worst / SIGNAL))
    print("\n   two lines move together (a rigid scale shift would): %s" % ("YES" if agree else "NO"))


if __name__ == "__main__":
    main()
