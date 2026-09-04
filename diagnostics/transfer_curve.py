"""WHAT DOES A LEVEL CHANGE DO TO THE ENCODED FRAME? The camera's transfer curve, measured -- and the
test that decides whether a MONOCHROME sensor would help (`SPEC_capture_quality.md` section 16.41).

(Edwin, 2026-09-04: "could it be that the BW camera is much better not due to quantization, but due to
the fact that on a color camera exposure changes shift the color hues much and thus values?")

That hypothesis has a testable shape. Across an exposure step, form the per-bin gain g = DN_high/DN_low
per Bayer channel and ask two questions of it:

    g varying with DN                     => the transfer curve is not a power law  => a LEVEL effect,
                                             which a mono sensor reproduces exactly
    g differing between channels AT EQUAL  => the three filters carry different curves => a HUE effect,
    DN                                       which a mono sensor removes

⭐ THE ANSWER on the 2026-08-30 Lugitsch fills: LEVEL. The gain falls monotonically from ~1.24 at DN 30-45
to ~1.077 at DN 190-245 (13-17 % across the range, against 1.6-4.3 % for the same-exposure controls), while
the channel spread at equal DN is 1.25-3.16 % against the controls' 1.33-3.11 % -- the same distribution.
The per-column HSV hue shift is 0.72-1.00 degrees median against the controls' 0.23-0.46, i.e. real but two
orders below the ~30 degrees reported for processed camera data. ⇒ a mono sensor does not fix this; RAW
LINEAR data does.

⛔ THE PER-CHANNEL STRAIGHT-LINE FIT IS THE WRONG TEST and is not offered here. Each channel spans a
different DN range of a curve that is not a line, so fitting a line per channel manufactures per-channel
slopes even for one shared curve -- the same-exposure controls "improved" by exactly as much. Channels are
compared only INSIDE a DN band.

⚠ The controls are the whole method. C, D and F are the same oil at the same exposure, so any structure
they show is re-seating and read noise, not the exposure step.

Run:
    PYTHONPATH=".:./diagnostics:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/transfer_curve.py
    ... diagnostics/transfer_curve.py --low          # extend the curve below DN 30 on the SAMPLE leg
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import reduction_sum_vs_max as replay

CHANNELS = ("R", "G", "B")
# ⭐ The four fills of the 2026-08-30 sitting: one oil, one recipe, one seating order, and the AE landed on
# 104 for exactly one of them (section 16.39.2). The archive's only clean exposure contrast at fixed
# preparation -- which is also this measurement's ceiling (n = 1 step, see section 16.41.5).
FILLS = {"C": "20260828LugitschC", "D": "20260828LugitschD",
         "E": "20260828LugitschE", "F": "20260828LugitschF"}
STEP = [("C", "E"), ("D", "E"), ("F", "E")]
CONTROL = [("C", "D"), ("C", "F"), ("D", "F")]
K = 104.0 / 90.0                  # nominal exposure ratio -- see the gamma caveat in `main`
DN_MIN, DN_MAX = 30.0, 245.0      # 30 DN floor: below it one code is >3 % and quantisation drives the ratio
EDGES = [30, 45, 70, 100, 140, 190, 245]
LOW_EDGES = [4, 6, 9, 13, 18, 25, 35, 50, 75, 110, 160, 220, 250]
SLOPE_MAX = 0.02                  # |dlnDN/dbin| guard: an x-alignment error on a steep flank is not a gain


def legsOf(series):
    """Per-column R,G,B DN for both capture legs of a run, on the run's own nm grid."""
    reference, frames = replay.attachments(os.path.join(archive.ARCHIVE, series, "001.pdf"))
    nms, referenceChannels, offset = replay.alignedChannels(frames["reference"], reference)
    _, sampleChannels, _ = replay.alignedChannels(frames["sample"], reference, offset=offset)
    return (np.asarray(nms, float), np.asarray(referenceChannels, float),
            np.asarray(sampleChannels, float))


def steady(values):
    smooth = np.convolve(values, np.ones(9) / 9.0, mode="same")
    return np.abs(np.gradient(np.log(np.maximum(smooth, 1.0)))) <= SLOPE_MAX


def usable(low, high, channel, dnMin=DN_MIN, dnMax=DN_MAX):
    a, b = low[:, channel], high[:, channel]
    return ((a >= dnMin) & (a <= dnMax) & (b >= dnMin) & (b <= dnMax) & steady(a) & steady(b))


def gainByBand(low, high, edges=None):
    """(median gain, per-channel gains) for each DN band of the LOW run."""
    edges = edges or EDGES
    out = []
    for i in range(len(edges) - 1):
        gains = []
        for channel in range(3):
            keep = (usable(low, high, channel)
                    & (low[:, channel] >= edges[i]) & (low[:, channel] < edges[i + 1]))
            if keep.sum() >= 15:
                gains.append(float(np.median(high[keep, channel] / low[keep, channel])))
        out.append((edges[i], edges[i + 1], float(np.median(gains)) if gains else float("nan"), gains))
    return out


def hueDegrees(rgb):
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    top, bottom = rgb.max(axis=1), rgb.min(axis=1)
    span = top - bottom
    hue = np.zeros(len(rgb))
    ok = span > 0
    isR, isG, isB = (top == r) & ok, (top == g) & ok, (top == b) & ok
    hue[isR] = 60.0 * (((g - b)[isR] / span[isR]) % 6.0)
    hue[isG] = 60.0 * (((b - r)[isG] / span[isG]) + 2.0)
    hue[isB] = 60.0 * (((r - g)[isB] / span[isB]) + 4.0)
    return hue, top


def hueShift(low, high):
    hueLow, topLow = hueDegrees(low)
    hueHigh, topHigh = hueDegrees(high)
    keep = (topLow >= 40) & (topLow <= 240) & (topHigh >= 40) & (topHigh <= 240)
    return np.abs(((hueHigh - hueLow + 180.0) % 360.0) - 180.0)[keep]


def lowEndCurve(data):
    """e(DN) = dlnDN/dlnX below DN 30, measured on the SAMPLE leg.

    ⛔ The reference leg has almost no bins under 30 DN, and the sample's dark Soret/Q bins (5-40 DN) are
    exactly where `Rv` and `RvLin` take their numbers -- so a curve clamped at 30 is extrapolating into the
    region that decides those metrics. The sample legs of C/D/F against E are the same oil, same sitting.
    ⚠ Below ~18 DN the gains collapse onto small-integer fractions (1.5, 1.8333, 2.0): that is quantisation,
    not the camera, and the exponent is NOT measurable there."""
    for legIndex, legName in ((1, "REFERENCE"), (2, "SAMPLE")):
        print("\n=== %s leg — gain and implied local exponent e = dlnDN/dlnX ===" % legName)
        print("   DN band      E/C     E/D     E/F   |   e(E/C) e(E/D) e(E/F)")
        for i in range(len(LOW_EDGES) - 1):
            lo, hi = LOW_EDGES[i], LOW_EDGES[i + 1]
            gains = []
            for a in ("C", "D", "F"):
                low, high = data[a][legIndex], data["E"][legIndex]
                per = []
                for channel in range(3):
                    keep = ((low[:, channel] >= lo) & (low[:, channel] < hi) & (high[:, channel] >= 1)
                            & steady(low[:, channel]) & steady(high[:, channel]))
                    if keep.sum() >= 12:
                        per.append(np.median(high[keep, channel] / low[keep, channel]))
                gains.append(float(np.median(per)) if per else np.nan)
            exponents = [np.log(g) / np.log(K) if g == g and g > 0 else np.nan for g in gains]
            print("   %3d-%3d  %7.4f %7.4f %7.4f   | %6.2f %6.2f %6.2f"
                  % (lo, hi, gains[0], gains[1], gains[2], exponents[0], exponents[1], exponents[2]))


def main():
    data = {key: legsOf(series) for key, series in FILLS.items()}
    grid = data["C"][0]
    print("REFERENCE leg, 001.pdf per fill. %d bins %.0f-%.0f nm. DN %g-%g, steep flanks dropped."
          % (len(grid), grid[0], grid[-1], DN_MIN, DN_MAX))

    for title, pairs in (("EXPOSURE STEP  90 -> 104", STEP), ("CONTROL  90 -> 90", CONTROL)):
        print("\n" + "=" * 78 + "\n" + title + "\n" + "=" * 78)

        print("\nA. LEVEL — median gain by DN band (a shared power law would be FLAT)")
        print("      pair        30-45   45-70  70-100 100-140 140-190 190-245     top/bottom")
        for a, b in pairs:
            curve = gainByBand(data[a][1], data[b][1])
            values = [row[2] for row in curve if row[2] == row[2]]
            print("   %s over %s  %s     %6.2f %%"
                  % (b, a, "".join("%8.4f" % row[2] for row in curve),
                     (max(values) / min(values) - 1.0) * 100.0 if values else float("nan")))

        print("\nB. CHANNEL — compared only INSIDE a DN band (see the docstring for why)")
        print("      pair          spread at equal DN, per band (%)          median")
        for a, b in pairs:
            spreads = []
            for _, _, _, gains in gainByBand(data[a][1], data[b][1]):
                if len(gains) >= 2:
                    spreads.append((max(gains) / min(gains) - 1.0) * 100.0)
            print("   %s over %s   %s   %6.2f %%"
                  % (b, a, "".join("%7.2f" % s for s in spreads), float(np.median(spreads))))

        print("\nC. HUE — per-column HSV hue shift (degrees)")
        print("      pair        median   p90     p99    max      n")
        for a, b in pairs:
            delta = hueShift(data[a][1], data[b][1])
            print("   %s over %s   %6.2f  %6.2f  %6.2f  %6.2f   %5d"
                  % (b, a, np.median(delta), np.percentile(delta, 90),
                     np.percentile(delta, 99), delta.max(), len(delta)))

    print("\n" + "=" * 78)
    print("LOCAL GAMMA per DN band (gamma = ln k / ln g, k = %.4f)" % K)
    print("⚠ The ABSOLUTE gammas inherit the unverified assumption that the V4L2 exposure value is")
    print("  proportional to integration time. Their VARIATION across DN does not: k is one scalar and")
    print("  a scalar cannot make the gain depend on DN.")
    print("=" * 78)
    print("      pair        30-45   45-70  70-100 100-140 140-190 190-245")
    for a, b in STEP:
        curve = gainByBand(data[a][1], data[b][1])
        print("   %s over %s %s"
              % (b, a, "".join("%8.2f" % (np.log(K) / np.log(row[2])) for row in curve)))

    if "--low" in sys.argv:
        lowEndCurve(data)


main()
