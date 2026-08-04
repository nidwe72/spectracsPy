"""The last variant — a FIXED template, amplitude only, centre swept. (SPEC_metric_research.md §7.11)

WHY THIS EXISTS. §7.10 fixed the band CENTRE from theory and let amplitude and width float. It
collapsed: sigma ran to 70.8 nm, and a Gaussian that wide is nearly FLAT across a 20 nm window --
which is precisely what the free linear background can absorb. The fit's answer was "there is no band
here". ⭐ THE WIDTH WAS THE ESCAPE HATCH.

Fixing the width too closes it. A Gaussian with sigma ~8 nm centred near 628 rises 0.08 -> 0.61 -> 1.00
across 610-629.8 -- strongly curved, and a straight line cannot reproduce that shape. Only the
AMPLITUDE stays free, so this is a ONE-parameter fit against a fixed template: the best-conditioned
form the problem admits.

WHERE THE WIDTH COMES FROM. Not literature -- we hold no width. We MEASURE it: the visible 574 nm band
fits at sigma = 8.0 +- 0.3 nm (§7.10's control), same molecule, same Q manifold. Using it for Qy is an
assumption, and the sweep below prices what it costs.

⚠ AND THE CENTRE IS SWEPT, not assumed. The literature says Qy sits at 623 (80 % acetone) / 626
(methanol), but our sample is in IPA and our own data shows NO turnover: 28/28 runs are still rising at
the 629.8 cut-off, with the apparent maximum near 628 nm. So the centre is scanned across 623-631 and
the data is allowed to say which it prefers -- reported as a diagnostic, never as a fitted parameter
(§6.4 rule 3).

WHAT WOULD COUNT AS SUCCESS. Not "the fit converges" -- a one-parameter fit always converges. The bar:
  * the recovered amplitude must be well determined (small relative error), AND
  * it must be STABLE against the window and against the assumed width, AND
  * it must separate the oil classes better than `M`'s d = 6.91.
A method that is stable because it is measuring the background is worthless (§6.2's blindness trap),
so the amplitude is also checked against the pedestal it sits on.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/fixed_template_fit.py
"""
import numpy as np

from metric_research_overview import load

WINDOW = (610.0, 629.8)                 # everything we have on the Qy flank
SIGMA = 8.0                             # measured on the VISIBLE 574 nm band (§7.10 control)
CENTRES = np.arange(623.0, 631.5, 1.0)  # swept, not assumed -- diagnostic only
SIGMA_SWEEP = (6.0, 8.0, 10.0, 12.0)    # what does the assumed width cost?
GREENS = ("Kiendler", "Steirerkraft")


def fitAmplitude(x, y, centre, sigma):
    """Linear least squares on [template, 1, x]: amplitude is the ONLY band parameter.

    Closed form, so there is no optimiser to blame and no starting guess to tune. Returns the
    amplitude and the residual RMS.
    """
    template = np.exp(-0.5 * ((x - centre) / sigma) ** 2)
    design = np.column_stack([template, np.ones_like(x), x - centre])
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ solution
    return float(solution[0]), float(np.sqrt(np.mean(residual ** 2)))


def cohenD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("nan")


def scoreAt(grid, runs, centre, sigma, window=WINDOW):
    mask = (grid >= window[0]) & (grid <= window[1])
    byOil, amplitudes, residuals = {}, [], []
    for name, oil, values in runs:
        amplitude, rms = fitAmplitude(grid[mask], values[mask], centre, sigma)
        byOil.setdefault(oil, []).append(amplitude)
        amplitudes.append(amplitude)
        residuals.append(rms)
    greens = np.array(byOil["Kiendler"] + byOil["Steirerkraft"])
    brown = np.array(byOil["S-Budget"])
    return (np.array(amplitudes), np.mean(residuals), cohenD(greens, brown), byOil)


def main():
    grid, runs = load()

    print("=== SWEEP THE CENTRE — the data is allowed to say where the band is\n")
    print("   sigma fixed at %.1f nm (measured on the visible 574 band). Amplitude is the ONLY free"
          " band parameter.\n" % SIGMA)
    print("   %-10s %14s %14s %12s %10s" % ("centre", "amplitude", "rel. error", "fit RMS", "class d"))
    print("   " + "-" * 66)
    best = None
    for centre in CENTRES:
        amplitudes, rms, separation, _ = scoreAt(grid, runs, centre, SIGMA)
        relative = 100 * amplitudes.std(ddof=1) / abs(amplitudes.mean()) if amplitudes.mean() else np.nan
        negative = "  ⛔ NEGATIVE" if amplitudes.mean() < 0 else ""
        print("   %8.1f nm %14.4f %12.0f %% %12.5f %10.2f%s"
              % (centre, amplitudes.mean(), relative, rms, separation, negative))
        if best is None or rms < best[1]:
            best = (centre, rms, separation)
    print("\n   lowest fit RMS at centre = %.1f nm  (literature says 623-626; our data still rises"
          " at 629.8)" % best[0])
    print("   ⚠ the RMS minimum is a DIAGNOSTIC, not a measurement of the band position -- a wider")
    print("     template at a redder centre trades off against the linear background term.")

    print("\n=== WHAT DOES THE ASSUMED WIDTH COST?\n")
    print("   %-10s %14s %14s %12s" % ("sigma", "amplitude", "class d", "vs M = 6.91"))
    print("   " + "-" * 56)
    for sigma in SIGMA_SWEEP:
        amplitudes, _, separation, _ = scoreAt(grid, runs, best[0], sigma)
        print("   %8.1f nm %14.4f %14.2f %12s"
              % (sigma, amplitudes.mean(), separation, "better" if separation > 6.91 else "worse"))

    print("\n=== STABILITY — refit on a narrower window (614-629.8)\n")
    full = scoreAt(grid, runs, best[0], SIGMA)
    narrow = scoreAt(grid, runs, best[0], SIGMA, (614.0, 629.8))
    print("   %-24s %14s %14s" % ("", "full 610-629.8", "narrow 614-629.8"))
    print("   %-24s %14.4f %14.4f   -> shift %.0f %%"
          % ("amplitude", full[0].mean(), narrow[0].mean(),
             100 * (narrow[0].mean() - full[0].mean()) / abs(full[0].mean())))
    print("   %-24s %14.2f %14.2f" % ("class d", full[2], narrow[2]))

    print("\n=== ⚠ IS IT MEASURING THE BAND, OR THE PEDESTAL?\n")
    amplitudes, _, separation, byOil = scoreAt(grid, runs, best[0], SIGMA)
    raw = np.array([values[(grid >= WINDOW[0]) & (grid <= WINDOW[1])].mean() for _, _, values in runs])
    print("   correlation(recovered amplitude, RAW absorbance in the window) = %+.3f"
          % np.corrcoef(amplitudes, raw)[0, 1])
    print("   (near +1 means the 'band' is just tracking how much total absorbance is there)")
    print("\n   %-14s %14s" % ("oil", "amplitude"))
    for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
        series = np.array(byOil[oil])
        print("   %-14s %9.4f ± %.4f" % (oil, series.mean(), series.std(ddof=1)))
    print("\n   class d = %.2f   (M = 6.91, V3 = 3.54, Q-peak position = 3.87)" % separation)


if __name__ == "__main__":
    main()
