"""Closing the last door — can a CONSTRAINED band fit recover a peak we cannot see?

(SPEC_metric_research.md §7.10. Edwin's question, 2026-08-04: "is there no mathematical workaround?")

THE PROBLEM. Both principal bands are flanks: protochlorophyll's Soret peaks at ~432 nm below our
440 nm edge, its Qy at ~623-626 nm above our 629.8 nm edge (§3.1). On a flank the band and the pedestal
are BOTH smooth monotone functions of lambda, so the split between them is not identifiable -- any
measured curve decomposes into (band + background) infinitely many ways. A PEAK is what breaks the tie,
because it is a feature the background is assumed not to have. §7.8/§7.9 showed this kills four
independent routes.

THE LAST MATHEMATICAL ROUTE, and the only one never tried. Import the missing constraint from THEORY
rather than from data: fix the band CENTRE at its literature position and fix the SHAPE FAMILY, then
fit only amplitude and width to the flank. We hold the metalated positions (`KB_spectroscopy_physics.md`
§4.1: Soret ~432-440, Qy 623 in 80 % acetone / 626 in methanol), so unlike C7 -- which needed the
FREE-BASE positions we do not hold (Q3) -- this fit is actually specifiable today.

⚠ EXPECTATION, STATED BEFORE RUNNING. I expect this to fail, for a measured reason: what pins down a
width on a flank is its CURVATURE, and route B found the 2nd derivative at 625 nm scatters 41 % against
the Q peak's 15 % (§7.7). Amplitude and width also trade off strongly when only one side is visible.
Recording the expectation so the result cannot be reinterpreted afterwards.

THE TEST IS NOT "does it fit". Any 2-parameter model fits a smooth flank. The tests are:
  1  IDENTIFIABILITY -- how correlated are amplitude and width in the fit? |r| -> 1 means the two are
     exchangeable and the individual numbers are meaningless however good the fit looks.
  2  STABILITY -- refit on a slightly narrower window. A well-determined fit barely moves; an
     ill-conditioned one swings.
  3  ⭐ THE CONTROL -- run the identical procedure on the 574 nm band, which we CAN see whole. If the
     method works there and fails on the flanks, the failure is the flank, not the method.
  4  USEFULNESS -- does the recovered amplitude separate the oil classes better than what we have?

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/constrained_band_fit.py
"""
import numpy as np
from scipy.optimize import curve_fit

from metric_research_overview import load

# (label, fixed centre from theory, fit window, is the peak inside our range?)
BANDS = [("Soret  (centre 432, FLANK)", 432.0, (440.0, 470.0), False),
         ("Qy     (centre 625, FLANK)", 625.0, (610.0, 629.8), False),
         ("⭐ Q  (centre 574, VISIBLE — the control)", 574.0, (552.0, 596.0), True)]
NARROWED = 0.75            # test 2 refits on the middle 75 % of the window
GREENS = ("Kiendler", "Steirerkraft")


def model(lam, amplitude, sigma, offset, slope, centre):
    """A Gaussian at a FIXED centre, on a local linear background. Only 4 free parameters."""
    return amplitude * np.exp(-0.5 * ((lam - centre) / sigma) ** 2) + offset + slope * (lam - centre)


def fitBand(x, y, centre):
    """Returns (amplitude, sigma, correlation between them) or None if the fit will not converge."""
    guess = [max(y.max() - y.min(), 1e-3), 12.0, y.min(), 0.0]
    try:
        best, covariance = curve_fit(lambda lam, a, s, o, k: model(lam, a, s, o, k, centre),
                                     x, y, p0=guess, maxfev=200000,
                                     bounds=([0, 1.0, -np.inf, -np.inf], [np.inf, 200.0, np.inf, np.inf]))
    except (RuntimeError, ValueError):
        return None
    deviation = np.sqrt(np.diag(covariance))
    if deviation[0] <= 0 or deviation[1] <= 0:
        return best[0], best[1], float("nan")
    correlation = covariance[0][1] / (deviation[0] * deviation[1])
    return float(best[0]), float(best[1]), float(correlation)


def cohenD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("nan")


def main():
    grid, runs = load()
    print("=== CONSTRAINED BAND FIT — centre FIXED from theory, amplitude and width fitted\n")
    print("   %-42s %11s %11s %13s" % ("band", "amplitude", "sigma (nm)", "corr(A,sigma)"))
    print("   " + "-" * 82)

    results = {}
    for label, centre, window, visible in BANDS:
        mask = (grid >= window[0]) & (grid <= window[1])
        amplitudes, sigmas, correlations, byOil = [], [], [], {}
        for name, oil, values in runs:
            outcome = fitBand(grid[mask], values[mask], centre)
            if outcome is None:
                continue
            amplitude, sigma, correlation = outcome
            amplitudes.append(amplitude)
            sigmas.append(sigma)
            correlations.append(correlation)
            byOil.setdefault(oil, []).append(amplitude)
        results[label] = (np.array(amplitudes), np.array(sigmas), np.array(correlations), byOil,
                          centre, window, visible)
        print("   %-42s %5.3f±%-5.3f %5.1f±%-5.1f %13.3f"
              % (label, np.mean(amplitudes), np.std(amplitudes, ddof=1),
                 np.mean(sigmas), np.std(sigmas, ddof=1), np.nanmean(correlations)))

    print("\n=== TEST 1  IDENTIFIABILITY — are amplitude and width exchangeable?")
    print("   |corr| near 1 means the fit cannot tell a tall narrow band from a short wide one,")
    print("   so the individual numbers are meaningless however well the curve is reproduced.\n")
    # ⛔ A GUARD, for the same reason T4 needed one. A LOW correlation is only good news if the fit
    # actually found a band. When the Gaussian collapses to amplitude ~ 0 the linear background term
    # has absorbed the whole flank -- the fit's own answer is "there is no band here" -- and the
    # correlation between two parameters of a band that does not exist means nothing. Two independent
    # symptoms: an amplitude indistinguishable from zero, and a sigma too wide for the window to
    # constrain. Either one voids the identifiability reading.
    for label in results:
        amplitudes, sigmas, correlations, _, _, window, _ = results[label]
        correlation = np.nanmean(correlations)
        collapsed = (amplitudes.mean() < 2 * amplitudes.std(ddof=1)
                     or sigmas.mean() > (window[1] - window[0]) / 2)
        if collapsed:
            verdict = "⛔ COLLAPSED — the fit found NO band; the background ate the flank"
        else:
            verdict = "⛔ DEGENERATE" if abs(correlation) > 0.95 else (
                "⚠ poor" if abs(correlation) > 0.8 else "✅ identifiable")
        print("   %-42s corr = %+.4f   %s" % (label, correlation, verdict))
        if collapsed:
            print("   %-42s   amplitude %.4f ± %.4f (indistinguishable from 0), sigma %.1f nm in a "
                  "%.1f nm window" % ("", amplitudes.mean(), amplitudes.std(ddof=1), sigmas.mean(),
                                      window[1] - window[0]))

    print("\n=== TEST 2  STABILITY — refit on the middle %.0f %% of each window\n" % (100 * NARROWED))
    print("   %-42s %14s %14s" % ("band", "amplitude shift", "sigma shift"))
    print("   " + "-" * 74)
    for label, centre, window, visible in BANDS:
        span = window[1] - window[0]
        margin = span * (1 - NARROWED) / 2
        mask = (grid >= window[0] + margin) & (grid <= window[1] - margin)
        amplitudes, sigmas = [], []
        for name, oil, values in runs:
            outcome = fitBand(grid[mask], values[mask], centre)
            if outcome is not None:
                amplitudes.append(outcome[0])
                sigmas.append(outcome[1])
        full = results[label]
        print("   %-42s %13.0f %% %13.0f %%"
              % (label, 100 * (np.mean(amplitudes) - full[0].mean()) / full[0].mean(),
                 100 * (np.mean(sigmas) - full[1].mean()) / full[1].mean()))

    print("\n=== TEST 4  USEFULNESS — does the recovered amplitude separate the classes?\n")
    print("   %-42s %10s %12s" % ("band", "class d", "vs M = 6.91"))
    print("   " + "-" * 68)
    for label in results:
        byOil = results[label][3]
        greens = np.array(byOil["Kiendler"] + byOil["Steirerkraft"])
        brown = np.array(byOil["S-Budget"])
        separation = cohenD(greens, brown)
        print("   %-42s %10.2f %12s" % (label, separation,
                                        "better" if separation > 6.91 else "worse"))


if __name__ == "__main__":
    main()
