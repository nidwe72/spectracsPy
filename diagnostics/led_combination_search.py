"""§16.25.4a — price the lamp in software: score LED combinations at the PIGMENT's band centres.

`SPEC_capture_quality.md` §16.25.4a sets the brief and `KB_spectroscopy_physics.md` §4.1a sets the target:
the pigment's centres are **432 / ~574 / ~625 nm**, and the shipped windows sit on FLANKS because they were
chosen by where the instrument had light, not by where the chemistry is. So this does NOT score for a flat
spectrum. It scores:

  1. photons at 432 and 625 nm — the two the instrument cannot currently reach properly;
  2. |dlnI/dl| at each measurement band — an emitter EDGE inside a band is the Sansi's failure (25 %/nm);
  3. coverage 430-670 with no hole — the DIY array's 3x cliff at 500 nm is the failure mode to avoid;
  4. the Q band and far anchor weighted above the middle (§16.24.2's 17x asymmetry).

⚠ The Avonec SPDs ship as Spektralmessung JPGs, not numbers (`spectracs-references/leds/avonec/`), so this
digitises the plotted curve. Each plot is normalised to 1.00 at its own peak, which means only the WAVELENGTH
axis needs calibrating — the x-ranges below were read off the axis labels by eye and are the one hand-entered
input here. `--verify` re-derives each peak and checks it against the part number.

⚠ What this can and cannot say. It ranks CANDIDATE SPECTRA. It knows nothing about drive current, binning,
thermal droop, or how the emitters combine behind a diffuser — so treat the ranking as a shortlist for the
bench, not a result. Real per-part output also varies far more than the normalised curves suggest.

Run from the spectracsPy repo root:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/led_combination_search.py [--verify]
"""
import itertools
import sys

import numpy as np
from PIL import Image

LED_DIRECTORY = "/home/nidwe72/development/spectracs/spectracs-references/leds/avonec/"

# file -> (first label, last label, label interval, nominal peak). The interval is a SELF-CHECK:
# the number of detected gridlines must equal (last-first)/interval + 1, which catches a mis-read axis.
# ⚠ Hand-read from the plot axes. `--verify` checks the digitised peak against the third column.
PLOTS = {
    "430nm-435nm.jpg": (390.0, 490.0, 10.0, 432.0),
    "515nm-525nm.jpg": (458.0, 598.0, 10.0, 520.0),
    "630nm-640nm.jpg": (584.0, 674.0, 5.0, 635.0),
    "660nm.jpg": (606.0, 701.0, 5.0, 661.0),
    "10000k-20000k.jpg": (407.0, 687.0, 20.0, None),   # cool white — bimodal, no single peak
    "6500k-7000k.jpg": (400.0, 720.0, 20.0, None),
    "5500k-6000k.jpg": (402.0, 702.0, 20.0, None),
}
# ⚠ Only files whose axis labels were READ OFF THE PLOT are listed. Four more exist in the folder
# (440-450, 455-460, 590-600, 600-610); they are omitted rather than guessed, because `--verify` caught
# guessed ranges putting their peaks 8-18 nm wrong. Add one by opening it and reading its first and last
# GRIDLINE label — not the curve's extent, which can run past the last gridline (6500k does).

GRID = np.arange(425.0, 675.0, 0.5)

# The pigment's own centres (KB §4.1a) — what we WANT light at.
PIGMENT = {"Soret": 432.0, "Q": 574.0, "Qy": 625.0}
# The bands the metric actually integrates — where a steep emitter edge does damage.
BANDS = {"Soret 448-460": (448.0, 460.0), "near 520-540": (520.0, 540.0),
         "Q 560-580": (560.0, 580.0), "far 620-630": (620.0, 630.0)}
# §16.24.2: an error in the Q band is levered ~17x relative to the Soret. Weight smoothness accordingly.
BAND_WEIGHT = {"Soret 448-460": 1.0, "near 520-540": 2.0, "Q 560-580": 4.0, "far 620-630": 4.0}


def digitise(fileName):
    """The plotted curve as values on GRID, normalised to its own peak.

    ⚠ x is calibrated on the GRIDLINES, after discarding the image borders that also read as grey. The
    gridline count is checked against the axis labels, so a mis-read axis fails loudly instead of silently
    shifting a curve. y needs no calibration — every plot is normalised to 1.00 at its own peak.
    y needs no calibration — every one of these plots is normalised to 1.00 at its own peak."""
    first, last, interval, _ = PLOTS[fileName]
    image = np.asarray(Image.open(LED_DIRECTORY + fileName).convert("RGB")).astype(float)
    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    curve = (blue > red + 25) & (blue > green + 15)
    columns = np.where(curve.any(axis=0))[0]
    if len(columns) == 0:
        raise ValueError("no curve found in %s" % fileName)

    # Plot area = the rows the curve lives in, generously padded; gridlines are grey and span it.
    rows = np.where(curve.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    band = image[top:bottom + 1]
    grey = (np.abs(band[:, :, 0] - band[:, :, 1]) < 12) & (np.abs(band[:, :, 1] - band[:, :, 2]) < 12) \
        & (band[:, :, 0] > 150) & (band[:, :, 0] < 245)
    gridColumns = np.where(grey.mean(axis=0) > 0.7)[0]
    if len(gridColumns) < 2:
        raise ValueError("gridlines not found in %s" % fileName)
    # Collapse runs of adjacent columns (a gridline is 1-2 px wide) to their centres.
    groups, start = [], gridColumns[0]
    for a, b in zip(gridColumns, gridColumns[1:]):
        if b - a > 3:
            groups.append((start + a) / 2.0)
            start = b
    groups.append((start + gridColumns[-1]) / 2.0)
    # ⚠ The outermost two "groups" are the IMAGE BORDERS (x = 0 and x = width-1), not gridlines — the white
    # margin reads as grey. Two earlier calibrations were wrong until this was found: mapping first-to-last
    # including them compressed the white curves by 6-10 nm, and rescaling on median spacing over-corrected
    # by +14 nm. Drop them, then the count must match the axis labels exactly.
    groups = groups[1:-1]
    expected = int(round((last - first) / interval)) + 1
    if len(groups) != expected:
        raise ValueError("%s: found %d gridlines, axis labels imply %d — re-read the axis"
                         % (fileName, len(groups), expected))
    pixelNm = np.interp(np.arange(image.shape[1]), [groups[0], groups[-1]], [first, last])

    heights = np.full(image.shape[1], np.nan)
    for column in columns:
        pixels = np.where(curve[:, column])[0]
        heights[column] = pixels.mean()
    values = -heights
    values -= np.nanmin(values)
    values /= np.nanmax(values)
    valid = ~np.isnan(values)
    return np.interp(GRID, pixelNm[valid], values[valid], left=0.0, right=0.0)


def logSlope(spectrum):
    """|dlnI/dlambda| in percent per nm — the amplification factor for any R->S mismatch."""
    return np.abs(np.gradient(np.log(np.maximum(spectrum, 1e-6)), GRID)) * 100.0


def at(spectrum, nanometers):
    return float(np.interp(nanometers, GRID, spectrum))


def score(spectrum):
    """Lower is better. Returns (total, parts) — see the module docstring for the four criteria."""
    normalised = spectrum / max(spectrum.max(), 1e-9)
    slope = logSlope(normalised)
    parts = {}

    # 1 · photons at the pigment's centres — the two the instrument cannot currently reach.
    parts["dark@432"] = 1.0 / max(at(normalised, 432.0), 1e-3)
    parts["dark@625"] = 1.0 / max(at(normalised, 625.0), 1e-3)

    # 2 · smoothness inside each measurement band, weighted by §16.24.2's leverage.
    steep = 0.0
    for name, (lo, hi) in BANDS.items():
        mask = (GRID >= lo) & (GRID <= hi)
        steep += BAND_WEIGHT[name] * float(np.median(slope[mask]))
    parts["steepness"] = steep / sum(BAND_WEIGHT.values())

    # 3 · no hole across 430-670: penalise the worst dip relative to the median level.
    working = (GRID >= 430.0) & (GRID <= 670.0)
    level = normalised[working]
    parts["hole"] = float(np.median(level) / max(level.min(), 1e-3))

    total = 2.0 * parts["dark@432"] + 2.0 * parts["dark@625"] + 1.5 * parts["steepness"] + 0.5 * parts["hole"]
    return total, parts


def describe(name, spectrum):
    normalised = spectrum / max(spectrum.max(), 1e-9)
    slope = logSlope(normalised)
    total, parts = score(spectrum)
    bandSlopes = {b: float(np.median(slope[(GRID >= lo) & (GRID <= hi)])) for b, (lo, hi) in BANDS.items()}
    return {"name": name, "total": total,
            "i432": at(normalised, 432.0), "i574": at(normalised, 574.0), "i625": at(normalised, 625.0),
            "worstBandSlope": max(bandSlopes.values()), "bandSlopes": bandSlopes,
            "hole": parts["hole"]}


def main():
    curves = {f: digitise(f) for f in PLOTS}

    if "--verify" in sys.argv:
        print("DIGITISER CHECK — peak of each digitised curve vs the part number\n")
        for fileName, (_, _, _, nominal) in PLOTS.items():
            peak = float(GRID[int(np.argmax(curves[fileName]))])
            flag = "" if nominal is None else ("  ok" if abs(peak - nominal) <= 6 else "  ⚠ OFF")
            print("   %-20s digitised peak %6.1f nm   part says %s%s"
                  % (fileName, peak, "%.0f" % nominal if nominal else "(white)", flag))
        print()

    whites = ["10000k-20000k.jpg", "6500k-7000k.jpg", "5500k-6000k.jpg"]
    blues = [None, "430nm-435nm.jpg"]
    reds = [None, "630nm-640nm.jpg", "660nm.jpg"]
    greens = [None, "515nm-525nm.jpg"]
    amounts = [0.0, 0.3, 0.6, 1.0]

    print("Candidate combinations, best first. Backbone weight fixed at 1.0; add-ons swept over %s.\n" % amounts)
    print("%-46s %7s %7s %7s %7s %8s %7s" %
          ("combination", "I@432", "I@574", "I@625", "worst", "hole", "score"))
    print("%-46s %7s %7s %7s %7s %8s %7s" % ("", "", "", "", "%/nm", "ratio", ""))
    print("-" * 96)

    results = []
    for white, blue, red, green in itertools.product(whites, blues, reds, greens):
        for blueAmount in (amounts if blue else [0.0]):
            for redAmount in (amounts if red else [0.0]):
                for greenAmount in (amounts if green else [0.0]):
                    total = curves[white].copy()
                    label = [white.replace(".jpg", "")]
                    for part, amount in ((blue, blueAmount), (red, redAmount), (green, greenAmount)):
                        if part and amount > 0:
                            total = total + amount * curves[part]
                            label.append("%s×%.1f" % (part.replace(".jpg", "").replace("nm", ""), amount))
                    results.append(describe(" + ".join(label), total))

    results.sort(key=lambda r: r["total"])
    seen = set()
    for row in results[:14]:
        if row["name"] in seen:
            continue
        seen.add(row["name"])
        print("%-46s %7.3f %7.3f %7.3f %7.1f %8.1f %7.2f"
              % (row["name"][:46], row["i432"], row["i574"], row["i625"],
                 row["worstBandSlope"], row["hole"], row["total"]))

    print("\n--- for reference, the backbones alone ---")
    for white in whites:
        row = describe(white.replace(".jpg", "") + "  (alone)", curves[white])
        print("%-46s %7.3f %7.3f %7.3f %7.1f %8.1f %7.2f"
              % (row["name"][:46], row["i432"], row["i574"], row["i625"],
                 row["worstBandSlope"], row["hole"], row["total"]))

    best = results[0]
    print("\n⭐ BEST: %s" % best["name"])
    print("   per-band |dlnI/dl| (median): %s"
          % "  ".join("%s %.1f %%/nm" % (b, v) for b, v in best["bandSlopes"].items()))
    print("   ⚠ ranking of CANDIDATE SPECTRA only — no drive current, binning, thermal droop or diffuser.")


if __name__ == "__main__":
    main()
