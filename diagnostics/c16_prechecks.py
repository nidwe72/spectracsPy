"""C16 pre-checks — is a Q-manifold ratio (574 nm ÷ far-red) buildable at all?

(docs/SPEC_metric_research.md §7 C16. Edwin's idea, 2026-08-04.)

C16 would measure the demetallation redistribution DIRECTLY -- both bands inside the Q manifold, so
total pigment cancels and speciation survives -- instead of via the Soret proxy that `M` uses. Two
things have to hold before it is worth building, and neither is about the metric's performance:

  PRE-CHECK 1  Promoting 620-630 from baseline ANCHOR to SIGNAL costs the chord its red foot. The only
               structurally equivalent replacement is the TROUGH between the two bands. Is there one?
               Is it flat enough to anchor on? And is it clear of the 607 nm lamp line, which sits
               right at its red edge?

  PRE-CHECK 2  There is no far PEAK -- the Qy maximum is past our 629.8 nm cut-off, so the far read is
               a rising FLANK at ~+0.008 A/nm. §3.6b measured +-0.2 nm of session-to-session wavelength
               SCALE drift. On a flank that converts directly into absorbance error. How much, against
               the band height C16 would divide by -- and does §3.8's per-session calibration remove it?

Neither check scores C16. They decide whether it can be built without inheriting a defect.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/c16_prechecks.py
"""
import json
import os

import numpy as np
from scipy.signal import savgol_filter

from metric_research_overview import load
from lamp_line_calibration import lineCentre, LINES

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "out", "metric_features.json")

NEAR = (520.0, 540.0)          # the blue anchor C16 would keep
FAR_SIGNAL = (620.0, 629.8)    # what C16 would promote from anchor to signal
TROUGH_SEARCH = (582.0, 620.0)  # between the 574 peak and the far-red rise
Q_BAND = (566.0, 582.0)        # the numerator, centred on the measured 574 nm peak


def main():
    grid, runs = load()
    oils = ("Kiendler", "Steirerkraft", "S-Budget")

    # ---------------------------------------------------------------- PRE-CHECK 1
    print("=== PRE-CHECK 1  Is there a usable trough to re-anchor on?\n")
    print("   %-14s %10s %10s %14s" % ("oil", "min at", "value", "flatness*"))
    print("   " + "-" * 54)
    minima = []
    for oil in oils:
        rows = [v for _, o, v in runs if o == oil]
        positions, values, flat = [], [], []
        for v in rows:
            smooth = savgol_filter(v, 151, 3)
            mask = (grid >= TROUGH_SEARCH[0]) & (grid <= TROUGH_SEARCH[1])
            x, y = grid[mask], smooth[mask]
            index = int(np.argmin(y))
            positions.append(x[index])
            values.append(y[index])
            # flatness: half-width over which the curve stays within 0.002 A of the minimum
            near = np.abs(y - y[index]) <= 0.002
            flat.append(x[near].max() - x[near].min())
        minima.append(np.mean(positions))
        print("   %-14s %8.1f nm %10.4f %11.1f nm" % (oil, np.mean(positions), np.mean(values),
                                                      np.mean(flat)))
    print("\n   * flatness = width over which the curve stays within 0.002 A of its minimum")
    print("   trough position spread across oils: %.1f nm" % (max(minima) - min(minima)))

    # where the 607 line actually sits, and how wide
    centres, widths = [], []
    for _, _, v in runs:
        centre, sigma = lineCentre(grid, v, *LINES[1])
        centres.append(centre)
        widths.append(sigma * 2.3548)
    lo = np.mean(centres) - np.mean(widths)
    hi = np.mean(centres) + np.mean(widths)
    print("\n   the 607 nm lamp line: centre %.2f nm, FWHM %.2f nm  =>  occupies %.1f-%.1f nm"
          % (np.mean(centres), np.mean(widths), lo, hi))
    print("   ⇒ a trough anchor must END BEFORE %.1f nm to stay clear of it." % lo)
    proposed = (np.floor(min(minima)) - 5, min(np.floor(lo), np.ceil(max(minima)) + 5))
    print("   ⇒ PROPOSED trough anchor: %.0f-%.0f nm  (width %.0f nm)"
          % (proposed[0], proposed[1], proposed[1] - proposed[0]))

    # ---------------------------------------------------------------- PRE-CHECK 2
    print("\n=== PRE-CHECK 2  What does wavelength drift cost on the far-red FLANK?\n")
    with open(TABLE) as handle:
        payload = json.load(handle)
    bySession = {}
    for row in payload["runs"]:
        bySession.setdefault(row["session"], []).append(row["features"])

    def chordAt(values, lam, anchorA, anchorB):
        xa = grid[(grid >= anchorA[0]) & (grid <= anchorA[1])].mean()
        xb = grid[(grid >= anchorB[0]) & (grid <= anchorB[1])].mean()
        ya = values[(grid >= anchorA[0]) & (grid <= anchorA[1])].mean()
        yb = values[(grid >= anchorB[0]) & (grid <= anchorB[1])].mean()
        fit = np.polyfit([xa, xb], [ya, yb], 1)
        return np.polyval(fit, lam)

    farMask = (grid >= FAR_SIGNAL[0]) & (grid <= FAR_SIGNAL[1])
    heights, slopes = [], []
    for _, _, v in runs:
        base = chordAt(v, grid[farMask], NEAR, proposed)
        heights.append((v[farMask] - base).mean())
        slopes.append(np.polyfit(grid[farMask], v[farMask], 1)[0])
    print("   far-red band above the PROPOSED baseline: %.4f A   (slope %+.5f A/nm)"
          % (np.mean(heights), np.mean(slopes)))
    print()
    print("   %-12s %14s %14s %12s" % ("session", "Δλ at 625 nm", "⇒ ΔA on flank", "% of height"))
    print("   " + "-" * 56)
    for session, rows in sorted(bySession.items()):
        scale = np.mean([r["wl_scale_session"] for r in rows])
        offset = np.mean([r["wl_offset_session"] for r in rows])
        shift = (offset + scale * 625.0) - 625.0
        error = shift * np.mean(slopes)
        print("   %-12s %+11.3f nm %+13.5f A %11.1f %%"
              % (session, shift, error, 100 * abs(error) / np.mean(heights)))

    # does correcting it actually tighten the far read?
    print("\n   Does §3.8's per-session calibration tighten the far-red read?")
    sessionOf = {"Kiendler": "20260801", "Steirerkraft": "20270729", "S-Budget": "20260731"}
    raw, corrected = [], []
    for name, oil, v in runs:
        rows = bySession[sessionOf[oil]]
        scale = np.mean([r["wl_scale_session"] for r in rows])
        offset = np.mean([r["wl_offset_session"] for r in rows])
        calibrated = offset + scale * grid            # the true wavelength of each measured bin
        base = chordAt(v, grid[farMask], NEAR, proposed)
        raw.append((v[farMask] - base).mean())
        mask = (calibrated >= FAR_SIGNAL[0]) & (calibrated <= FAR_SIGNAL[1])
        corrected.append((v[mask] - chordAt(v, grid[mask], NEAR, proposed)).mean())
    for label, series in (("raw", raw), ("wavelength-calibrated", corrected)):
        series = np.array(series)
        print("      %-22s far-red height  %.5f ± %.5f  (CV %.2f %%)"
              % (label, series.mean(), series.std(ddof=1), 100 * series.std(ddof=1) / series.mean()))


if __name__ == "__main__":
    main()
