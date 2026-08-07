"""410-680 nm lamp study — score Avonec 3 W LED combinations for the pumpkin-oil bands.

Widens `led_combination_search.py` (which answered `SPEC_capture_quality.md` §16.25.4a over 430-670 nm)
to the range Edwin asked for, **410-680 nm** (corrected 2026-08-07 from a 689 typo; 680 is also
exactly where `KB_spectroscopy_physics.md` §7.2 puts the last measurable response), and prices a
**deep-red 3 W STAR emitter** — which Avonec turns out to sell itself.

What changes against the 430-670 study, and why each change matters:

  1. **Thirteen digitised Avonec SPDs, not seven.** The four colour LEDs that study excluded rather than
     guessed (440-450, 455-460, 590-600, 600-610) plus the two remaining whites (2900-3200 K,
     4000-4500 K) now have their axes read off the plots. `--verify` checks every digitised peak
     against the part number.
  2. **The grid is 410-680 nm.** Both new ends carry a specific pigment question:
       - **410-430** brackets the **Soret peak at ~432 nm** from BELOW. Demetallation
         (protochlorophyll -> protopheophytin, the green->brown chemistry, `KB_spectroscopy_physics.md`
         §4.1) **weakens AND blue-shifts** the Soret. A shift cannot be measured from one flank.
       - **660-680** is the first genuinely **pigment-free window** (Qy is at ~623-626 nm, not 665), so
         it is the natural baseline anchor the metric has never had.
  3. **The deep-red star.** Modelled from the Avonec 660 measured curve as the shape proxy, with a
     peak/width sensitivity sweep, because the second vendor's part has no measured SPD on file.
  4. **Emitted vs DELIVERED.** An emitted-photon ranking is only half the answer past 630 nm: the
     instrument's own response falls steeply there (`KB_spectroscopy_physics.md` §7.2 — the red channel
     drops ~40x between 631 and 657 nm). Every combination is therefore scored twice, and the delivered
     score is bracketed by an optimistic and a pessimistic response model rather than a single curve.

⚠ What this can and cannot say. It ranks CANDIDATE SPECTRA. It knows nothing about drive current,
binning, thermal droop, diffuser transmission, or how emitters combine behind one diffuser. Real
per-part output varies far more than these normalised curves suggest. Treat the ranking as a shortlist
for the bench, not a result.

Run from the spectracsPy repo root:
    ./venv/bin/python diagnostics/led_lamp_410_680.py [--verify] [--figures]
"""
import itertools
import json
import os
import sys

import numpy as np
from PIL import Image

LED_DIRECTORY = "/home/nidwe72/development/spectracs/spectracs-references/leds/avonec/"
OUT_DIRECTORY = "/home/nidwe72/development/spectracs/spectracs-references/tmp/lamp410680/"

# file -> (first gridline label, last gridline label, label interval, nominal peak).
# ⚠ Hand-read from each plot's x axis. The interval is a SELF-CHECK: the number of detected gridlines
# must equal (last-first)/interval + 1, so a mis-read axis fails loudly instead of shifting a curve
# silently. `--verify` then checks the digitised peak against the part number.
# The first seven were calibrated for the 430-670 study; the last seven were read for this one.
PLOTS = {
    "410nm-420nm.jpg":   (375.0, 470.0,  5.0, 421.0),
    "430nm-435nm.jpg":   (390.0, 490.0, 10.0, 432.0),
    "440nm-450nm.jpg":   (400.0, 490.0,  5.0, 441.0),
    "455nm-460nm.jpg":   (410.0, 510.0, 10.0, 458.0),
    "480nm-485nm.jpg":   (435.0, 530.0,  5.0, 481.0),
    "515nm-525nm.jpg":   (458.0, 598.0, 10.0, 520.0),
    "590nm-600nm.jpg":   (549.0, 629.0,  5.0, 594.0),
    "600nm-610nm.jpg":   (561.0, 656.0,  5.0, 615.0),
    "630nm-640nm.jpg":   (584.0, 674.0,  5.0, 635.0),
    "660nm.jpg":         (606.0, 701.0,  5.0, 661.0),
    "2900k-3200k.jpg":   (406.0, 726.0, 20.0, None),
    "4000k-4500k.jpg":   (399.0, 759.0, 20.0, None),
    "5500k-6000k.jpg":   (402.0, 702.0, 20.0, None),
    "6500k-7000k.jpg":   (400.0, 720.0, 20.0, None),
    "10000k-20000k.jpg": (407.0, 687.0, 20.0, None),
}

GRID = np.arange(410.0, 680.5, 0.5)

# ⭐ MEASURED on the rig, DN per bin — `SPEC_capture_quality.md` §16.25.4 (Edwin 2026-08-07: put the real
# lamps into the figures). These are the only numbers in this file that are lamp x instrument TOGETHER,
# which is exactly what makes them worth plotting: they are what the camera actually recorded.
#   ⚠ Two source tables, and they may not share a scale. The 440-630 sweep is "full sweep, same
#     registration"; the 430/450/650/656/680 points come from four screenshots at "same exposure".
#     The Sansi RISES from 149 DN at 630 to 176 at 650 across that join, which no phosphor continuum
#     does — so either the two tables are on different scales, or the Sansi has a line-emitting red
#     phosphor (KSF/PFS Mn(4+) has narrow lines near 631/648/660). Do not read the join as physical.
#   ⛔ The 680 nm column is NOT trustworthy: SPEC_metric_research.md §9.1 P3 records the "Sansi 24 DN at
#     680" figure came from "a screenshot ending at ~676 nm with a transferred wavelength scale".
MEASURED_LAMPS = {
    "Yuji":  {430: 39, 440: 81, 450: 84, 460: 72, 480: 147, 500: 136, 520: 115, 540: 98,
              560: 83, 580: 90, 600: 91, 620: 63, 630: 52, 650: 47, 656: 21, 680: 2},
    "Sansi": {430: 39, 440: 108, 450: 147, 460: 122, 480: 161, 500: 196, 520: 182, 540: 168,
              560: 153, 580: 180, 600: 185, 620: 159, 630: 149, 650: 176, 656: 115, 680: 24},
    "DIY 7x3W": {430: 140, 440: 113, 450: 106, 460: 120, 480: 128, 500: 43, 520: 35, 540: 43,
                 560: 47, 580: 50, 600: 43, 620: 18, 630: 12, 650: 8, 656: 2, 680: 0},
}
# ⚠ The Sansi CLIPS at 255 through 600-640 in the screenshot set, so its mid-range there is a floor,
# not a value. The sweep table's Sansi numbers (<=196) are not clipped.
UNTRUSTED_ABOVE = 676.0

# The pigment's own band centres — KB_spectroscopy_physics.md §4.1a. This is what we want light AT.
PIGMENT = {"Soret 432": 432.0, "Q 574": 574.0, "Qy 625": 625.0}

# The two ends the widened range exists to buy, and what each is for.
SORET_SHAPE = (415.0, 450.0)     # bracket the Soret so a BLUE SHIFT is measurable, not just a depth
QUIET_WINDOW = (660.0, 680.0)    # first pigment-free region -> the baseline anchor the metric lacks

# The bands the metric integrates today, where a steep emitter edge does real damage, plus the two
# the widened range would add.
BANDS = {
    "Soret 428-440": (428.0, 440.0),   # NEW — the peak itself, not the 448-460 flank
    "Soret 448-460": (448.0, 460.0),   # shipped window
    "near 520-540":  (520.0, 540.0),
    "Q 560-580":     (560.0, 580.0),
    "far 620-630":   (620.0, 630.0),
    "quiet 662-678": (662.0, 678.0),   # NEW — the pigment-free anchor
}
# §16.24.2: an error in the Q band is levered ~17x relative to the Soret. The two new bands are
# weighted as what they are — a shape measurement and a baseline anchor, both high-value, neither yet
# load-bearing for the shipped metric.
BAND_WEIGHT = {"Soret 428-440": 2.0, "Soret 448-460": 1.0, "near 520-540": 2.0,
               "Q 560-580": 4.0, "far 620-630": 4.0, "quiet 662-678": 3.0}


# --------------------------------------------------------------------------- digitiser

def digitise(fileName):
    """The plotted curve as values on GRID, normalised to its own peak.

    ⚠ x is calibrated on the GRIDLINES, after discarding the image borders that also read as grey. The
    gridline count is checked against the axis labels, so a mis-read axis fails loudly instead of
    silently shifting a curve. y needs no calibration — every Avonec plot is normalised to 1.00 at its
    own peak."""
    first, last, interval, _ = PLOTS[fileName]
    image = np.asarray(Image.open(LED_DIRECTORY + fileName).convert("RGB")).astype(float)
    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    curve = (blue > red + 25) & (blue > green + 15)
    columns = np.where(curve.any(axis=0))[0]
    if len(columns) == 0:
        raise ValueError("no curve found in %s" % fileName)

    rows = np.where(curve.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    band = image[top:bottom + 1]
    grey = (np.abs(band[:, :, 0] - band[:, :, 1]) < 12) & (np.abs(band[:, :, 1] - band[:, :, 2]) < 12) \
        & (band[:, :, 0] > 150) & (band[:, :, 0] < 245)
    gridColumns = np.where(grey.mean(axis=0) > 0.7)[0]
    if len(gridColumns) < 2:
        raise ValueError("gridlines not found in %s" % fileName)
    groups, start = [], gridColumns[0]
    for a, b in zip(gridColumns, gridColumns[1:]):
        if b - a > 3:
            groups.append((start + a) / 2.0)
            start = b
    groups.append((start + gridColumns[-1]) / 2.0)
    # ⚠ The outermost two "groups" are the IMAGE BORDERS, not gridlines — the white margin reads as
    # grey. Drop them, then the count must match the axis labels exactly.
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
    # ⚠ left/right = 0 outside the plotted extent. Every colour LED is genuinely dark there; the one
    # place this bites is 10000k-20000k, whose plot stops at ~687 nm (flagged in coverage()).
    return np.interp(GRID, pixelNm[valid], values[valid], left=0.0, right=0.0)


def gaussianEmitter(peak, fullWidthHalfMaximum, redSkew=1.25):
    """A skew-normal stand-in for an emitter with no measured curve on file.

    Only used for the SENSITIVITY sweep on the second-vendor star and for the 670/680/690 nm parts that
    are not in the Avonec range at all. AlGaInP deep-reds are visibly red-skewed (see 660nm.jpg), so a
    symmetric Gaussian would flatter the long-wavelength side; `redSkew` widens the red flank."""
    sigma = fullWidthHalfMaximum / 2.3548
    widths = np.where(GRID >= peak, sigma * redSkew, sigma)
    return np.exp(-0.5 * ((GRID - peak) / widths) ** 2)


# --------------------------------------------------------------------------- instrument response

def instrumentResponse(kind):
    """Modelled DETECTED-signal response of the current instrument, normalised to 1.0 at 630 nm.

    ⚠ THIS IS A MODEL, and it is the weakest input in the study — say so wherever its numbers appear.
    It is pinned to the two things actually measured (`KB_spectroscopy_physics.md` §7.2):
      - the red channel falls ~40x between 631 and 657 nm (IR-cut edge + sensor QE + source decline
        combined — the measurement cannot separate the three, so attributing all of it to the
        instrument is the PESSIMISTIC reading and attributing part of it to the lamp the OPTIMISTIC);
      - the Eu(3+) 650.7 nm line still resolves as a genuine peak, and response continues to ~680 nm.
    Below 440 nm nothing is measured at all — the stored spectra start there — so the blue end is a
    stated assumption, not a result. 'optimistic' keeps full response to 425 nm; 'pessimistic' starts
    the blue roll-off at 450 nm."""
    response = np.ones_like(GRID)
    if kind == "optimistic":
        blueKnee, blueDecades = 425.0, 0.9       # -> ~0.13 of peak at 410 nm
        redFall631to657, redDecadesTo680 = 12.0, 0.92
    elif kind == "pessimistic":
        blueKnee, blueDecades = 450.0, 1.6       # -> ~0.007 of peak at 410 nm
        redFall631to657, redDecadesTo680 = 40.0, 1.75
    else:
        raise ValueError(kind)

    blue = GRID < blueKnee
    response[blue] = 10.0 ** (-blueDecades * ((blueKnee - GRID[blue]) / (blueKnee - 410.0)) ** 2)
    red = GRID > 631.0
    slope = np.log10(redFall631to657) / (657.0 - 631.0)
    response[red] = 10.0 ** (-slope * (GRID[red] - 631.0))
    beyond = GRID > 657.0
    extra = np.log10(10.0 ** redDecadesTo680 / redFall631to657) / (680.0 - 657.0)
    response[beyond] = 10.0 ** (-np.log10(redFall631to657)) * 10.0 ** (-extra * (GRID[beyond] - 657.0))
    return response


# --------------------------------------------------------------------------- scoring

def logSlope(spectrum):
    """|dlnI/dlambda| in percent per nm — the factor by which any R->S mismatch is amplified."""
    return np.abs(np.gradient(np.log(np.maximum(spectrum, 1e-6)), GRID)) * 100.0


def at(spectrum, nanometers):
    return float(np.interp(nanometers, GRID, spectrum))


def score(spectrum):
    """Lower is better. Returns (total, parts).

    Five criteria, in the order `SPEC_capture_quality.md` §16.25.4a fixes them, extended for the two
    ends this study adds:
      1 photons at the pigment's own centres 432 / 574 / 625 nm;
      2 photons across the two NEW regions — the Soret bracket 415-450 and the quiet window 660-689;
      3 |dlnI/dlambda| inside every measurement band, weighted by §16.24.2's 17x asymmetry;
      4 no hole anywhere across 410-680 (the DIY array's 3x cliff at 500 nm is the failure to avoid).
    """
    normalised = spectrum / max(spectrum.max(), 1e-9)
    slope = logSlope(normalised)
    parts = {}

    for name, centre in PIGMENT.items():
        parts["dark@%d" % centre] = 1.0 / max(at(normalised, centre), 1e-3)

    for label, (lo, hi) in (("soretBracket", SORET_SHAPE), ("quietWindow", QUIET_WINDOW)):
        mask = (GRID >= lo) & (GRID <= hi)
        parts[label] = 1.0 / max(float(np.median(normalised[mask])), 1e-3)

    steep = 0.0
    for name, (lo, hi) in BANDS.items():
        mask = (GRID >= lo) & (GRID <= hi)
        steep += BAND_WEIGHT[name] * float(np.median(slope[mask]))
    parts["steepness"] = steep / sum(BAND_WEIGHT.values())

    level = normalised[(GRID >= 410.0) & (GRID <= 680.0)]
    parts["hole"] = float(np.median(level) / max(level.min(), 1e-3))

    parts["holeAt"] = float(GRID[(GRID >= 410.0) & (GRID <= 680.0)][int(np.argmin(level))])

    total = combineParts(parts, WEIGHTINGS["as written"])
    return total, parts


# The objective is a judgement call, so it is stated five ways and the recommendation has to survive
# all of them. "Soret peak only" is the control: drop the bracket term and the study reduces to the
# 430-670 question, where a spike at 432 is all that is asked for.
WEIGHTINGS = {
    "as written":       {"dark@432": 2.0, "dark@574": 1.0, "dark@625": 2.0,
                         "soretBracket": 1.5, "quietWindow": 1.5, "steepness": 1.5, "hole": 0.3},
    "photons first":    {"dark@432": 4.0, "dark@574": 2.0, "dark@625": 4.0,
                         "soretBracket": 1.5, "quietWindow": 1.5, "steepness": 0.5, "hole": 0.3},
    "smoothness first": {"dark@432": 2.0, "dark@574": 1.0, "dark@625": 2.0,
                         "soretBracket": 1.5, "quietWindow": 1.5, "steepness": 4.0, "hole": 0.3},
    "quiet window":     {"dark@432": 2.0, "dark@574": 1.0, "dark@625": 2.0,
                         "soretBracket": 1.5, "quietWindow": 4.0, "steepness": 1.5, "hole": 0.3},
    "Soret peak only":  {"dark@432": 3.0, "dark@574": 1.0, "dark@625": 2.0,
                         "soretBracket": 0.0, "quietWindow": 1.5, "steepness": 1.5, "hole": 0.3},
}


def combineParts(parts, weights):
    return sum(weight * parts[key] for key, weight in weights.items())


def describe(name, spectrum, emitters):
    normalised = spectrum / max(spectrum.max(), 1e-9)
    slope = logSlope(normalised)
    total, parts = score(spectrum)
    bandSlopes = {b: float(np.median(slope[(GRID >= lo) & (GRID <= hi)])) for b, (lo, hi) in BANDS.items()}
    row = {"name": name, "emitters": emitters, "total": total,
           "i410": at(normalised, 410.0), "i432": at(normalised, 432.0),
           "i574": at(normalised, 574.0), "i625": at(normalised, 625.0),
           "i660": at(normalised, 660.0), "i680": at(normalised, 680.0),
           "soretBracket": 1.0 / parts["soretBracket"], "quietWindow": 1.0 / parts["quietWindow"],
           "worstBandSlope": max(bandSlopes.values()), "bandSlopes": bandSlopes,
           "hole": parts["hole"], "holeAt": parts["holeAt"], "parts": parts,
           "i480": at(normalised, 480.0), "i500": at(normalised, 500.0),
           "i420": at(normalised, 420.0),
           "belowSoret": float(np.median(normalised[(GRID >= 415.0) & (GRID <= 428.0)])),
           "spectrum": normalised}
    for weighting, weights in WEIGHTINGS.items():
        row["score_" + weighting] = combineParts(parts, weights)
    for kind in ("optimistic", "pessimistic"):
        delivered = normalised * instrumentResponse(kind)
        delivered = delivered / max(delivered.max(), 1e-9)
        row["delivered_" + kind] = score(delivered)[0]
        row["dq_" + kind] = float(np.median(delivered[(GRID >= 662.0) & (GRID <= 678.0)])
                                  / max(np.median(delivered[(GRID >= 620.0) & (GRID <= 630.0)]), 1e-9))
    return row


# --------------------------------------------------------------------------- candidate lamps

WHITES = ["2900k-3200k.jpg", "4000k-4500k.jpg", "5500k-6000k.jpg",
          "6500k-7000k.jpg", "10000k-20000k.jpg"]
# The slots an add-on emitter can fill. Two violets because 410-420 and 430-435 answer different halves
# of the Soret question — one brackets the peak from below, one sits almost on it.
ADDONS = ["410nm-420nm.jpg", "430nm-435nm.jpg", "440nm-450nm.jpg", "455nm-460nm.jpg",
          "480nm-485nm.jpg", "515nm-525nm.jpg", "590nm-600nm.jpg", "600nm-610nm.jpg",
          "630nm-640nm.jpg",
          "660nm.jpg", "star660", "star670", "star680", "star690"]
SLOTS = 7


def label(mix):
    order = {p: i for i, p in enumerate(WHITES + ADDONS)}
    return " + ".join("%d × %s" % (count, part.replace(".jpg", ""))
                      for part, count in sorted(mix.items(), key=lambda kv: order[kv[0]]))


# Edwin's question has three nested answers, and conflating them would be the easiest way to mislead:
#   A — the Avonec catalogue alone, which is what can be ordered from one shop today;
#   B — Avonec plus the 3 W 660 nm STAR from the second vendor, which is the question as asked;
#   C — B plus deep-reds Avonec does not sell at all (670 / 680 / 690 nm), which is the only family
#       that can actually put light at 689 nm.
FAMILIES = {
    "A · Avonec only": [p for p in ADDONS if not p.startswith("star")],
    "B · Avonec + 660 star": [p for p in ADDONS if not p.startswith("star")] + ["star660"],
    "C · + longer deep-reds": list(ADDONS),
}


def buildCandidates(curves, slots=SLOTS, maxAddonKinds=3):
    """Every buildable allocation of `slots` emitters, as INTEGER counts.

    Matches Edwin's construction sketch (§16.25.4: a white phosphor lamp in the centre ringed by ~4
    small heatsinked emitters behind one common diffuser), and it is what actually gets soldered — a
    continuous weight is not orderable. At least one white, at most `maxAddonKinds` distinct add-on
    part numbers so the board stays a board and not a laboratory.

    ⚠ ASSUMPTION, and it is a real one: one part = weight 1.0 of its own normalised curve, i.e. every
    3 W emitter is treated as delivering the same radiant flux. It does not — a 3 W green is the
    weakest part in the range by roughly 2x — so counts are a first-order allocation, and the green
    slot in particular should be read as "at least this many"."""
    seen, candidates = set(), []
    for whiteCount in range(1, slots + 1):
        for white in WHITES:
            remaining = slots - whiteCount
            for kinds in range(0, maxAddonKinds + 1):
                if kinds > remaining:
                    break
                for chosen in itertools.combinations(ADDONS, kinds):
                    for counts in _compositions(remaining, kinds):
                        mix = {white: whiteCount}
                        mix.update(dict(zip(chosen, counts)))
                        key = tuple(sorted(mix.items()))
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append((label(mix), mix))
    return candidates


def _compositions(total, parts):
    """Every way to write `total` as `parts` POSITIVE integers (order matters — the parts differ)."""
    if parts == 0:
        if total == 0:
            yield ()
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


def combine(curves, mix):
    total = np.zeros_like(GRID)
    for part, weight in mix.items():
        total = total + weight * curves[part]
    return total


# --------------------------------------------------------------------------- figures

def writeFigures(curves, ranked, best, verdicts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(OUT_DIRECTORY, exist_ok=True)
    ink, grid = "#1f2933", "#d7dde3"

    def frame(axes, title, xlabel="wavelength (nm)"):
        axes.set_title(title, fontsize=11, color=ink)
        axes.set_xlabel(xlabel, fontsize=9)
        axes.set_xlim(410, 680)
        axes.grid(True, color=grid, linewidth=0.6)
        for spine in ("top", "right"):
            axes.spines[spine].set_visible(False)
        axes.tick_params(labelsize=8)

    # 1 — every digitised Avonec SPD, so the calibration can be eyeballed against the part numbers.
    figure, (upper, lower) = plt.subplots(2, 1, figsize=(9.2, 6.4), sharex=True)
    colours = plt.cm.turbo(np.linspace(0.05, 0.95, len([f for f in PLOTS if "k-" not in f])))
    index = 0
    for name in PLOTS:
        if "k-" in name:
            continue
        upper.plot(GRID, curves[name], color=colours[index], linewidth=1.3,
                   label=name.replace(".jpg", ""))
        index += 1
    for name in [f for f in PLOTS if "k-" in f]:
        lower.plot(GRID, curves[name], linewidth=1.3, label=name.replace(".jpg", ""))
    frame(upper, "Avonec 3 W colour LEDs — measured spectra, digitised")
    frame(lower, "Avonec 3 W white LEDs — measured spectra, digitised")
    for axes in (upper, lower):
        axes.legend(fontsize=7, ncol=3, frameon=False)
        axes.set_ylabel("relative power", fontsize=9)
    figure.tight_layout()
    figure.savefig(OUT_DIRECTORY + "avonec_spd_atlas.png", dpi=170)
    plt.close(figure)

    # 2 — the recommendations against the incumbent, with the pigment centres marked.
    figure, axes = plt.subplots(figsize=(9.2, 4.6))
    for title, colour, style, width in (
            ("R0 incumbent (430-670 study)", "#9aa5b1", "--", 1.3),
            ("R2 Avonec 660 star (BUILD)", "#0b6e4f", "-", 2.0),
            ("R4 reach 680 (670 star)", "#3b5bdb", "-", 1.6)):
        axes.plot(GRID, verdicts[title]["spectrum"], color=colour, linestyle=style,
                  linewidth=width, label=title)
    axes.plot(GRID, curves["4000k-4500k.jpg"], color="#c9a227", linewidth=1.1,
              linestyle=":", label="4000-4500 K backbone alone")
    # ⭐ The two lamps actually on the bench, as MEASURED DN, each normalised to its own maximum so it
    # sits on the same 0-1 scale as the candidate curves. These are lamp x instrument together.
    for lamp, marker, colour in (("Yuji", "o", "#7b4b94"), ("Sansi", "s", "#b0413e")):
        points = sorted(MEASURED_LAMPS[lamp].items())
        xs = [w for w, _ in points if w <= UNTRUSTED_ABOVE]
        peak = max(MEASURED_LAMPS[lamp].values())
        ys = [MEASURED_LAMPS[lamp][w] / peak for w in xs]
        axes.plot(xs, ys, marker=marker, markersize=4.5, linewidth=1.0, linestyle="-.",
                  color=colour, alpha=0.85, label="%s — MEASURED on the rig" % lamp)
    for name, centre in PIGMENT.items():
        axes.axvline(centre, color="#b0413e", linewidth=0.9, alpha=0.55)
        axes.text(centre + 2, 1.19, name, fontsize=7.5, color="#b0413e")
    axes.axvspan(*QUIET_WINDOW, color="#0b6e4f", alpha=0.07)
    axes.text(661, 1.19, "quiet window", fontsize=7.5, color="#0b6e4f")
    axes.axvspan(*SORET_SHAPE, color="#3b5bdb", alpha=0.06)
    axes.text(411, 1.26, "Soret bracket 415-450", fontsize=7.5, color="#3b5bdb")
    frame(axes, "Candidate lamps against the two real ones — measured points, normalised to each lamp's own peak")
    axes.set_ylabel("relative power", fontsize=9)
    axes.set_ylim(0, 1.32)
    axes.legend(fontsize=8, frameon=False, loc="lower center", ncol=2)
    figure.tight_layout()
    figure.savefig(OUT_DIRECTORY + "recommended_vs_backbone.png", dpi=170)
    plt.close(figure)

    # 3 — ⛔ THE DELIVERED-RESPONSE MODEL IS WITHDRAWN (Edwin 2026-08-07, and he is right).
    # It rested on §7.2's "~40x between 631 and 657 nm", which was measured through a CFL — whose red
    # output is Eu(3+) LINE emission, so 631 sits on the flank of the 626.6 line and 657 sits in the gap
    # before 662. That ratio is the lamp's own structure. The earlier rebuttal in this file compared it
    # against phosphor-WHITE LEDs, which is the wrong source class and proved nothing.
    # What replaces it is the measurement itself: three real lamps, as recorded.
    figure, axes = plt.subplots(figsize=(9.2, 4.4))
    for lamp, marker, colour in (("Yuji", "o", "#7b4b94"), ("Sansi", "s", "#b0413e"),
                                 ("DIY 7x3W", "^", "#0b6e4f")):
        points = sorted(MEASURED_LAMPS[lamp].items())
        xs = [w for w, _ in points if w <= UNTRUSTED_ABOVE]
        ys = [MEASURED_LAMPS[lamp][w] for w in xs]
        axes.plot(xs, ys, marker=marker, markersize=5, linewidth=1.2, color=colour, label=lamp)
        far = [w for w in MEASURED_LAMPS[lamp] if w > UNTRUSTED_ABOVE]
        axes.plot(far, [MEASURED_LAMPS[lamp][w] for w in far], marker=marker, markersize=5,
                  linewidth=1.2, linestyle=":", color=colour, alpha=0.35)
    axes.axvspan(UNTRUSTED_ABOVE, 690, color="#b0413e", alpha=0.09)
    axes.text(651, 205, "680 nm column\nNOT trustworthy\n(§9.1 P3)", fontsize=7.5, color="#b0413e")
    axes.axvspan(600, 640, color="#7b8794", alpha=0.08)
    axes.text(601, 240, "Sansi clips at 255 here", fontsize=7.5, color="#7b8794")
    axes.annotate("Sansi still reads 115 DN at 656 nm —\nthe camera is NOT collapsed in the red",
                  xy=(656, 115), xytext=(560, 60), fontsize=8, color="#b0413e",
                  arrowprops=dict(arrowstyle="->", color="#b0413e", linewidth=1.0))
    frame(axes, "What the camera has actually recorded — three lamps, measured DN (§16.25.4)")
    axes.set_xlim(425, 690)
    axes.set_ylim(0, 265)
    axes.set_ylabel("DN per bin", fontsize=9)
    axes.legend(fontsize=8, frameon=False, loc="upper left")
    figure.tight_layout()
    figure.savefig(OUT_DIRECTORY + "measured_lamps.png", dpi=170)
    plt.close(figure)

    # 4 — the deep-red slot: which part actually reaches 689 nm.
    figure, axes = plt.subplots(figsize=(9.2, 4.0))
    for part, colour in (("630nm-640nm.jpg", "#c9a227"), ("660nm.jpg", "#b0413e"),
                         ("star670", "#8b3a62"), ("star680", "#5f3b8b"), ("star690", "#2f4858")):
        axes.plot(GRID, curves[part], color=colour, linewidth=1.5,
                  label=part.replace(".jpg", "").replace("star", "star ~") + " nm"
                  if part.startswith("star") else part.replace(".jpg", ""))
    axes.axvspan(*QUIET_WINDOW, color="#0b6e4f", alpha=0.08)
    axes.axvline(680, color=ink, linewidth=1.0)
    axes.text(672, 0.9, "quiet window\n660-680 nm", fontsize=8, color="#0b6e4f")
    frame(axes, "The deep-red slot — which part actually reaches the top of the range")
    axes.set_xlim(600, 682)
    axes.set_ylabel("relative power", fontsize=9)
    axes.legend(fontsize=8, frameon=False)
    figure.tight_layout()
    figure.savefig(OUT_DIRECTORY + "deep_red_candidates.png", dpi=170)
    plt.close(figure)

    print("figures -> %s" % OUT_DIRECTORY)


# --------------------------------------------------------------------------- main

def main():
    curves = {f: digitise(f) for f in PLOTS}
    # The second-vendor star and the parts Avonec does not sell. ⚠ modelled, not measured.
    curves["star660"] = gaussianEmitter(660.0, 22.0)
    curves["star670"] = gaussianEmitter(670.0, 22.0)
    curves["star680"] = gaussianEmitter(680.0, 24.0)
    curves["star690"] = gaussianEmitter(690.0, 25.0)

    if "--verify" in sys.argv:
        print("DIGITISER CHECK — peak of each digitised curve vs the part number\n")
        for fileName, (_, _, _, nominal) in PLOTS.items():
            peak = float(GRID[int(np.argmax(curves[fileName]))])
            inRange = curves[fileName].max() > 0.99
            flag = "  (white — no single peak)" if nominal is None else \
                ("  ok" if abs(peak - nominal) <= 6 else "  ⚠ OFF")
            print("   %-20s digitised peak %6.1f nm   part says %-8s%s%s"
                  % (fileName, peak, "%.0f" % nominal if nominal else "-", flag,
                     "" if inRange else "   ⚠ peak lies OUTSIDE 410-689"))
        print()

    candidates = buildCandidates(curves)
    rows = [describe(name, combine(curves, mix), mix) for name, mix in candidates]
    rows.sort(key=lambda r: r["total"])

    WIDTH = 70
    header = ("%-*s %6s %6s %6s %6s %6s %6s %6s %7s" %
              (WIDTH, "combination (7 emitters)", "I@432", "I@574", "I@625", "I@660", "I@680",
               "worst", "hole", "score"))

    def show(row):
        print("%-*s %6.3f %6.3f %6.3f %6.3f %6.3f %6.1f %6.1f %7.2f"
              % (WIDTH, row["name"][:WIDTH], row["i432"], row["i574"], row["i625"], row["i660"],
                 row["i680"], row["worstBandSlope"], row["hole"], row["total"]))

    print("EMITTED-SPECTRUM RANKING over 410-680 nm — %d buildable allocations\n" % len(rows))
    for family, allowed in FAMILIES.items():
        permitted = set(WHITES) | set(allowed)
        inFamily = [r for r in rows if set(r["emitters"]) <= permitted]
        print("### %s — %d allocations" % (family, len(inFamily)))
        print(header)
        print("-" * len(header))
        for row in inFamily[:6]:
            show(row)
        print()

    print("### the five backbones alone (7 × white), for reference")
    print(header)
    print("-" * len(header))
    for white in WHITES:
        mix = {white: 7}
        show(describe("7 × " + white.replace(".jpg", ""), combine(curves, mix), mix))

    print("\n### the 430-670 study's winner (§16.25.4a), rescored on the 410-680 objective")
    incumbentMix = {"6500k-7000k.jpg": 3, "430nm-435nm.jpg": 2, "515nm-525nm.jpg": 1, "660nm.jpg": 1}
    incumbent = describe(label(incumbentMix), combine(curves, incumbentMix), incumbentMix)
    rank = 1 + sum(1 for r in rows if r["total"] < incumbent["total"])
    show(incumbent)
    print("   -> rank %d of %d; its 410-680 weaknesses are I@680 %.3f and the 415-450 bracket %.3f"
          % (rank, len(rows), incumbent["i680"], incumbent["soretBracket"]))

    best = rows[0]
    print("\n⭐ BEST EMITTED: %s   score %.2f" % (best["name"], best["total"]))
    print("   Soret bracket 415-450 median %.3f · quiet window 660-680 median %.3f"
          % (best["soretBracket"], best["quietWindow"]))
    print("   deepest dip %.2f of the median, at %.0f nm · I@480 %.3f · I@500 %.3f"
          % (1.0 / best["hole"], best["holeAt"], best["i480"], best["i500"]))
    print("   per-band |dlnI/dλ| (median): %s"
          % "  ".join("%s %.1f %%/nm" % (b, v) for b, v in best["bandSlopes"].items()))

    print("\nWEIGHT SENSITIVITY — the objective is a judgement call, so state it five ways")
    print("  %-18s %-62s %s" % ("weighting", "winner", "rank of the 'as written' winner"))
    for weighting in WEIGHTINGS:
        key = "score_" + weighting
        ordered = sorted(rows, key=lambda r: r[key])
        rank = 1 + sum(1 for r in rows if r[key] < best[key])
        print("  %-18s %-62s %d/%d" % (weighting, ordered[0]["name"][:62], rank, len(rows)))

    print("\nDELIVERED ranking — same allocations through the modelled instrument response")
    for kind in ("optimistic", "pessimistic"):
        byDelivered = sorted(rows, key=lambda r: r["delivered_" + kind])
        print("\n  %s response model:" % kind)
        for row in byDelivered[:6]:
            print("     %-*s delivered %7.2f   quiet/far %5.3f"
                  % (WIDTH, row["name"][:WIDTH], row["delivered_" + kind], row["dq_" + kind]))
        print("     (best-emitted allocation sits at delivered %.2f, rank %d)"
              % (best["delivered_" + kind],
                 1 + sum(1 for r in rows if r["delivered_" + kind] < best["delivered_" + kind])))

    print("\nHOW MUCH DEEP RED IS NEEDED — emitted power to put 662-678 nm on a par with 620-630 nm")
    for kind in ("optimistic", "pessimistic"):
        response = instrumentResponse(kind)
        quiet = float(np.median(response[(GRID >= 662.0) & (GRID <= 678.0)]))
        far = float(np.median(response[(GRID >= 620.0) & (GRID <= 630.0)]))
        print("  %-12s response at 662-678 is %.4f of 620-630  =>  need %.0f× the emitted power there"
              % (kind, quiet / far, far / quiet))

    print("\nDEEP-RED SLOT — same 6 other emitters, only the red part swapped (1 emitter)")
    baseMix = {k: v for k, v in best["emitters"].items()
               if not (k.startswith("star") or k in ("630nm-640nm.jpg", "660nm.jpg"))}
    if sum(baseMix.values()) == SLOTS:                 # winner had no red slot — free one from the white
        heaviest = max(baseMix, key=baseMix.get)
        baseMix[heaviest] -= 1
    print("  %-16s %6s %6s %6s %8s %8s %s"
          % ("red part", "I@625", "I@660", "I@680", "far slope", "quiet", "note"))
    for part in ("630nm-640nm.jpg", "660nm.jpg", "star660", "star670", "star680", "star690"):
        mix = dict(baseMix)
        mix[part] = 1
        row = describe(part, combine(curves, mix), mix)
        note = "measured (Avonec)" if part.endswith(".jpg") else "MODELLED — no SPD on file"
        print("  %-16s %6.3f %6.3f %6.3f %8.1f %8.3f %s"
              % (part.replace(".jpg", ""), row["i625"], row["i660"], row["i680"],
                 row["bandSlopes"]["far 620-630"], row["quietWindow"], note))

    print("\nDEEP-RED BIN SENSITIVITY — what an unmeasured 660 nm part could do; sweep peak & width")
    print("  %-22s %6s %6s %6s %8s" % ("assumed part", "I@625", "I@660", "I@680", "far slope"))
    for peak in (650.0, 655.0, 660.0, 665.0, 670.0):
        for width in (18.0, 22.0, 28.0):
            mix = dict(baseMix)
            curves["sweep"] = gaussianEmitter(peak, width)
            mix["sweep"] = 1
            row = describe("sweep", combine(curves, mix), mix)
            print("  %-22s %6.3f %6.3f %6.3f %8.1f"
                  % ("%.0f nm, FWHM %.0f" % (peak, width), row["i625"], row["i660"], row["i680"],
                     row["bandSlopes"]["far 620-630"]))
    curves.pop("sweep", None)

    print("\nNAMED RECOMMENDATIONS — the spectrum each one puts on the grid, every 20-30 nm")
    # ⭐ Reworked 2026-08-07 on the shop check: Avonec sells the 660 nm on a Starplatine ITSELF
    # (EUR 2.75), so the "second-vendor star" slot is Avonec's own MEASURED part, not a modelled
    # stand-in. A second vendor is needed only for 670/680 nm, which Avonec does not sell.
    named = {
        "R0 incumbent (430-670 study)": incumbentMix,
        "R1 Avonec, no deep red":       {"4000k-4500k.jpg": 3, "410nm-420nm.jpg": 2,
                                         "430nm-435nm.jpg": 1, "455nm-460nm.jpg": 1},
        "R2 Avonec 660 star (BUILD)":    {"4000k-4500k.jpg": 3, "410nm-420nm.jpg": 2,
                                         "430nm-435nm.jpg": 1, "660nm.jpg": 1},
        "R3 R2 + the 480 cyan filler":  {"4000k-4500k.jpg": 3, "410nm-420nm.jpg": 1,
                                         "430nm-435nm.jpg": 1, "480nm-485nm.jpg": 1,
                                         "660nm.jpg": 1},
        "R4 reach 680 (670 star)":      {"4000k-4500k.jpg": 3, "410nm-420nm.jpg": 2,
                                         "440nm-450nm.jpg": 1, "star670": 1},
    }
    probes = [410, 432, 450, 480, 500, 520, 540, 574, 600, 625, 660, 680]
    print("  %-30s %s" % ("", "  ".join("%5d" % p for p in probes)))
    verdicts = {}
    for title, mix in named.items():
        row = describe(title, combine(curves, mix), mix)
        verdicts[title] = row
        print("  %-30s %s" % (title, "  ".join("%5.3f" % at(row["spectrum"], p) for p in probes)))
    print("\n  %-30s %7s %6s %8s %8s %7s %6s %10s" %
          ("", "score", "rank", "sub-Sor", "quiet", "dip@nm", "dip", "quiet/far"))
    for title, row in verdicts.items():
        rank = 1 + sum(1 for r in rows if r["total"] < row["total"])
        print("  %-30s %7.2f %6d %8.3f %8.3f %7.0f %6.3f %5.3f/%.3f"
              % (title, row["total"], rank, row["belowSoret"], row["quietWindow"],
                 row["holeAt"], 1.0 / row["hole"], row["dq_optimistic"], row["dq_pessimistic"]))

    print("\n  one violet added to a bare 4000-4500 K backbone — the cheap step, priced on its own")
    for extra in (None, "410nm-420nm.jpg", "430nm-435nm.jpg"):
        mix = {"4000k-4500k.jpg": 7 if extra is None else 6}
        if extra:
            mix[extra] = 1
        row = describe(label(mix), combine(curves, mix), mix)
        print("  %-46s I@410 %.3f  I@432 %.3f  sub-Soret %.3f  score %.2f"
              % (row["name"][:46], at(row["spectrum"], 410.0), row["i432"],
                 row["belowSoret"], row["total"]))

    if "--figures" in sys.argv:
        writeFigures(curves, rows, best, verdicts)

    os.makedirs(OUT_DIRECTORY, exist_ok=True)
    with open(OUT_DIRECTORY + "ranking.json", "w") as handle:
        json.dump([{k: v for k, v in r.items() if k != "spectrum"} for r in rows[:40]],
                  handle, indent=1)

    print("\n⚠ CANDIDATE SPECTRA ONLY — no drive current, binning, thermal droop or diffuser "
          "transmission.\n⚠ The instrument-response model is the weakest input; below 440 nm nothing "
          "has ever been measured.")


if __name__ == "__main__":
    main()
