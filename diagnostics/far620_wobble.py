"""How much does the ADOPTED metric WOBBLE, run to run?  (Edwin 2026-08-02)

Two columns, on every POST-rebuild series:

    M legacy   600-630          the superseded anchor, uncorrected -- what the app computed until 2026-08-03
    M ADOPTED  620-630 + r_Q    the shipped primary: far anchor at 620-630 (§16.20) WITH its own pedestal
                                residual r_Q = -0.0184 put back (§16.20.2)

⚠ NOTE ON THE TITLE THIS SCRIPT USED TO CARRY. It was first written for the UNCORRECTED 620-630 metric and
said so everywhere; it was then repointed at the corrected one when §16.20.7 adopted it, and the prose was
not repointed with it. Corrected 2026-08-03. The uncorrected 620-630 index is still computed and still
appears in the per-run table as `UNCORRECTED_620`, so the two halves of the change can be told apart --
but it is NOT what the figure's right-hand column draws.

⚠ THE COMPARISON RULE THIS SCRIPT EXISTS TO RESPECT (§16.20.4). The two metrics sit on DIFFERENT SCALES
-- green reads 12.37 on the shipped anchor and 15.56 on this one -- so a percentage of each metric's own
mean (a CV) is NOT comparable between them: the denominator moved for reasons unrelated to noise. Every
wobble figure here is therefore quoted against the CLASS GAP (green mean - brown mean, measured on that
same anchor), which is the quantity the metric exists to resolve and the only scale-free reference
available. Reading CVs across anchors is what produced a wrong conclusion once already.

Prints per-run values, per-set scatter and the within-set time trend; writes one SVG:
    docs/figures/far620_wobble.svg

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/far620_wobble.py
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import BASE, measure

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.abspath(os.path.join(HERE, "..", "docs", "figures"))

# POST-rebuild only. Pre-rebuild series carry ~3x the seating noise and would swamp the comparison
# (§16.11); mixing them is what §16.20.1a caught.
SERIES = [("Kiendler A", "green", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
          ("Kiendler B", "green", ["20260801B/%03d.pdf" % i for i in range(1, 3)]),
          ("Kiendler C", "green", ["20260801C/%03d.pdf" % i for i in range(1, 3)]),
          ("Steirerkraft B", "green", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
          ("Steirerkraft C", "green", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
          ("S-Budget D", "brown", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]

# The shipped metric, and the ADOPTED candidate: 620-630 anchor + pedestal correction (Edwin
# 2026-08-02). The uncorrected 620-630 metric is carried alongside in the per-run table so the two
# halves of the change can still be told apart.
METRICS = [("S/Q linear base", "M legacy   600-630"),
           ("S/Q far620 corr", "M ADOPTED  620-630+r_Q")]
UNCORRECTED_620 = "S/Q far620"

# The class gap is measured on the sets that define the classes, not on all of them: Steirerkraft B+C
# is the green reference (§16.13.5) and series D the brown one.
GREEN_REFERENCE = ("Steirerkraft B", "Steirerkraft C")
BROWN_REFERENCE = ("S-Budget D",)

INK, MUTED, BROWN = "#1c211c", "#5c655c", "#8d5524"
# One colour AND one marker per series: six green traces in a single green are unreadable, and telling
# the sets apart is the entire point of a wobble plot.
STYLE = {"Kiendler A":      ("#1b5e20", "o"),
         "Kiendler B":      ("#43a047", "s"),
         "Kiendler C":      ("#81c784", "^"),
         "Steirerkraft B":  ("#1565c0", "D"),
         "Steirerkraft C":  ("#64b5f6", "v"),
         "S-Budget D":      (BROWN,     "P")}


def load():
    """{seriesName: (runs, elapsedMinutes)} -- each report read once."""
    out = {}
    for name, _, paths in SERIES:
        times = np.array([os.path.getmtime(BASE + p) for p in paths], dtype=float)
        out[name] = ([measure(p) for p in paths], (times - times.min()) / 60.0)
    return out


def classGap(data, key):
    green = np.concatenate([[r[key] for r in data[n][0]] for n in GREEN_REFERENCE])
    brown = np.concatenate([[r[key] for r in data[n][0]] for n in BROWN_REFERENCE])
    return float(green.mean() - brown.mean())


def trendPerHour(times, values):
    """Absolute drift in metric units per hour -- NOT a percentage, so it stays comparable."""
    if len(values) < 3 or np.ptp(times) == 0:
        return float("nan")
    slope = np.polyfit(times, values, 1)[0]
    return slope * 60.0


def main():
    print(__doc__.split("Prints per-run")[0].strip())
    print()
    data = load()

    for key, label in METRICS:
        gap = classGap(data, key)
        print("=== %s      (class gap on this anchor: %.3f)" % (label, gap))
        print("   %-16s %-6s %6s %8s %8s %9s %11s %11s" % (
            "series", "class", "n", "mean", "sd", "range", "sd / gap", "drift/h /gap"))
        print("   " + "-" * 86)
        for name, klass, _ in SERIES:
            runs, times = data[name]
            values = np.array([r[key] for r in runs])
            sd = values.std(ddof=1) if len(values) > 1 else float("nan")
            drift = trendPerHour(times, values)
            print("   %-16s %-6s %6d %8.3f %8.3f %9.3f %10.1f %% %10s" % (
                name, klass, len(values), values.mean(), sd, np.ptp(values), 100 * sd / gap,
                "—" if np.isnan(drift) else "%.1f %%" % (100 * drift / gap)))
        print()
        print("   per-run values:")
        for name, _, _ in SERIES:
            runs, _ = data[name]
            print("      %-16s %s" % (name, "  ".join("%7.3f" % r[key] for r in runs)))
        print()

    perRun(data)
    errorBudget(data)
    showWorking(data)
    writeFigure(data)


# Log-log dilution slopes, both measured on the POST-rebuild pair 0729B -> 0729C (§16.20.2). The metric
# multiplies by (concentration ratio)^s, so s = 0 would be perfect invariance.
# Derived from the DESIGNED dilution pair Kiendler A -> C (lever 1.88x on observed A_Q), not from
# Steirerkraft B/C (lever 1.17x, and its two fills were prepared to the SAME nominal recipe so their
# difference is unintended). The short-lever pair flatters the 620-630 anchor by roughly two-fold.
SLOPE_PAIR = ("Kiendler A", "Kiendler C")

# What an operator can actually get wrong. A drop is not a reproducible unit: drop size varies ~17 %,
# and one drop in six IS 17 % (§16.11.15).
MISTAKES = [("miscount one drop  6 -> 7", 7 / 6),
            ("miscount one drop  6 -> 5", 5 / 6),
            ("17 % sloppy drop size", 1.17),
            ("DOUBLE the dose    6 -> 12", 2.0),
            ("FOUR TIMES the dose", 4.0)]


def perRun(data):
    """Every post-rebuild measurement, run by run, on both anchors — the raw record behind every
    aggregate in this script and in §16.20. `dev` is the run's distance from its OWN set mean, as a
    percentage of that anchor's class gap, which is the only form comparable between the two."""
    print("=== EVERY POST-REBUILD MEASUREMENT, run by run")
    print("   raw = de-spiked band means, before any baseline.  B_* = after the linear baseline.")
    print("   dev = distance from this SET's mean, as % of that anchor's class gap.")
    print()
    # Take BOTH keys from METRICS rather than naming them again here: an earlier version hardcoded the
    # UNCORRECTED key for the adopted column, so the table printed the same numbers twice.
    shipped, far620 = METRICS[0][0], METRICS[1][0]
    gapShipped, gapFar = classGap(data, shipped), classGap(data, far620)
    print("   %-15s %4s %6s %8s %7s | %8s %7s %8s %7s | %8s %7s %9s %9s %7s" % (
        "series", "run", "min", "A_Soret", "A_Q",
        "B_Soret", "B_Q", "M ship", "dev", "B_Sor620", "B_Q620", "M 620 raw", "M ADOPTED", "dev"))
    print("   " + "-" * 132)
    for name, klass, _ in SERIES:
        runs, times = data[name]
        meanShipped = float(np.mean([r[shipped] for r in runs]))
        meanFar = float(np.mean([r[far620] for r in runs]))
        for index, run in enumerate(runs):
            print("   %-15s %4d %6.1f %8.4f %7.4f | %8.4f %7.4f %8.3f %6.1f%% | %8.4f %7.4f %9.3f %9.3f %6.1f%%" % (
                name if index == 0 else "", index + 1, times[index],
                run["A_Soret raw"], run["A_Q raw"],
                run["A_Soret linear"], run["A_Q linear"], run[shipped],
                100 * (run[shipped] - meanShipped) / gapShipped,
                run["A_Soret far620"], run["A_Q far620"], run[UNCORRECTED_620], run[far620],
                100 * (run[far620] - meanFar) / gapFar))
        sdShipped = float(np.std([r[shipped] for r in runs], ddof=1)) if len(runs) > 1 else 0.0
        sdFar = float(np.std([r[far620] for r in runs], ddof=1)) if len(runs) > 1 else 0.0
        meanRaw620 = float(np.mean([r[UNCORRECTED_620] for r in runs]))
        print("   %-15s %4s %6s %8s %7s | %8s %7s %8.3f %6s  | %8s %7s %9.3f %9.3f %6s" % (
            "-> " + klass, "mean", "", "", "", "", "", meanShipped, "", "", "",
            meanRaw620, meanFar, ""))
        print("   %-15s %4s %6s %8s %7s | %8s %7s %8.3f %5.1f%%  | %8s %7s %9s %9.3f %5.1f%%" % (
            "", "sd", "", "", "", "", "", sdShipped, 100 * sdShipped / gapShipped,
            "", "", "", sdFar, 100 * sdFar / gapFar))
        print()


def showWorking(data):
    """Every step of the 'one drop vs the wobble' comparison, traced back to the printed rows.

    The comparison joins TWO quantities that come from DIFFERENT places, which is why it cannot be read
    off the per-run table alone:
      * the WOBBLE comes from the sd rows of that table  (same fill, jar re-seated);
      * the DILUTION SLOPE comes from two DIFFERENT FILLS at different strengths (Steirerkraft B vs C),
        which the per-run table shows as two set means but never divides.
    """
    print("=== SHOWING THE WORKING — 'one miscounted drop against the run-to-run wobble'")
    print()
    for key, label in METRICS:
        gap = classGap(data, key)
        # --- step 1: the wobble, pooled over every series, from the sd rows above
        deviations, groups = [], 0
        print("   %s" % label)
        print("   STEP 1  the WOBBLE — pool the per-set scatter (the 'sd' rows of the table above)")
        for name, _, _ in SERIES:
            values = np.array([r[key] for r in data[name][0]])
            if len(values) > 1:
                groups += 1
                deviations.append(values - values.mean())
                print("             %-16s n=%d   sd = %.4f" % (name, len(values), values.std(ddof=1)))
        pooled = np.concatenate(deviations)
        # n - k degrees of freedom: k group means were subtracted, not one grand mean.
        wobble = float(np.sqrt((pooled ** 2).sum() / (len(pooled) - groups)))
        print("             pooled over %d runs and %d sets, %d df  ->  WOBBLE = %.4f  (%.1f %% of the gap %.3f)"
              % (len(pooled), groups, len(pooled) - groups, wobble, 100 * wobble / gap, gap))
        print()

        # --- step 2: the dilution slope, from two different FILLS
        low, high = SLOPE_PAIR
        mLow = float(np.mean([r[key] for r in data[low][0]]))
        mHigh = float(np.mean([r[key] for r in data[high][0]]))
        cLow = float(np.mean([r["A_Q raw"] for r in data[low][0]]))
        cHigh = float(np.mean([r["A_Q raw"] for r in data[high][0]]))
        slope = np.log(mHigh / mLow) / np.log(cHigh / cLow)
        print("   STEP 2  the DILUTION SLOPE — NOT in the table above; it needs two DIFFERENT FILLS")
        print("             pair: %s -> %s  (the DESIGNED dilution series; §16.20.4b)" % SLOPE_PAIR)
        print("             %-16s metric mean %.3f   at strength A_Q(raw) = %.4f" % (low, mLow, cLow))
        print("             %-16s metric mean %.3f   at strength A_Q(raw) = %.4f" % (high, mHigh, cHigh))
        print("             concentration ratio = %.4f / %.4f = %.4f  (+%.1f %% stronger)"
              % (cHigh, cLow, cHigh / cLow, 100 * (cHigh / cLow - 1)))
        print("             metric ratio        = %.3f / %.3f = %.5f" % (mHigh, mLow, mHigh / mLow))
        print("             s = ln(%.5f) / ln(%.4f) = %.5f / %.5f  ->  s = %+.4f"
              % (mHigh / mLow, cHigh / cLow, np.log(mHigh / mLow), np.log(cHigh / cLow), slope))
        print()

        # --- step 3: one drop
        ratio = 7 / 6
        factor = ratio ** slope
        mean = float(np.mean(np.concatenate(
            [[r[key] for r in data[n][0]] for n in GREEN_REFERENCE])))
        shift = abs(mean * (factor - 1.0))
        print("   STEP 3  ONE MISCOUNTED DROP, 6 -> 7, i.e. a concentration ratio of 7/6 = %.4f" % ratio)
        print("             metric multiplies by  %.4f^(%+.4f) = %.5f" % (ratio, slope, factor))
        print("             on a green mean of %.3f that is a shift of %.3f x %.5f = %.4f"
              % (mean, mean, abs(factor - 1.0), shift))
        print()
        print("   STEP 4  %.4f (one drop)  /  %.4f (wobble)  =  %.2f x"
              % (shift, wobble, shift / wobble))
        print("           => a miscounted drop is %.0f %% of the run-to-run noise%s"
              % (100 * shift / wobble,
                 " — INDISTINGUISHABLE from it" if shift / wobble > 0.5 else " — BURIED under it"))
        print()
        print("   " + "-" * 100)
        print()


def dilutionSlope(data, key):
    """The log-log slope s from SLOPE_PAIR, on the observed A_Q axis. Derived, never hardcoded."""
    low, high = SLOPE_PAIR
    strength = lambda n: float(np.mean([r["A_Q raw"] for r in data[n][0]]))
    value = lambda n: float(np.mean([r[key] for r in data[n][0]]))
    return float(np.log(value(high) / value(low)) / np.log(strength(high) / strength(low)))


def errorBudget(data):
    """Every error term in METRIC UNITS and as a share of the class gap, so the claim can be checked.

    The percentage column is the one that compares across anchors (§16.20.4); the metric column is
    there so the arithmetic can be redone by hand from the class means printed above it."""
    SLOPE = {key: dilutionSlope(data, key) for key, _ in METRICS}
    print("=== ERROR BUDGET — is the dilution error above or below the measurement's own noise?")
    print()
    keys = [k for k, _ in METRICS]
    gaps, means, wobbles = {}, {}, {}
    for key, _ in METRICS:
        gaps[key] = classGap(data, key)
        means[key] = float(np.mean(np.concatenate(
            [[r[key] for r in data[n][0]] for n in GREEN_REFERENCE])))
        wobbles[key] = float(np.std(np.concatenate(
            [np.array([r[key] for r in data[n][0]]) - np.mean([r[key] for r in data[n][0]])
             for n, _, _ in SERIES]), ddof=1))

    print("   %-30s %19s %19s" % ("", "shipped 600-630", "620-630"))
    print("   " + "-" * 70)
    for label, get in (("green class mean", lambda k: means[k]),
                       ("brown class mean", lambda k: means[k] - gaps[k]),
                       ("CLASS GAP", lambda k: gaps[k]),
                       ("dilution slope  s", lambda k: SLOPE[k])):
        print("   %-30s %19.3f %19.3f" % (label, get(keys[0]), get(keys[1])))
    print()
    print("   %-30s %9s %9s %9s %9s" % ("error term", "metric", "% of gap", "metric", "% of gap"))
    print("   " + "-" * 70)
    print("   %-30s %9.3f %8.1f %% %9.3f %8.1f %%" % (
        "run-to-run wobble  (1 sd)", wobbles[keys[0]], 100 * wobbles[keys[0]] / gaps[keys[0]],
        wobbles[keys[1]], 100 * wobbles[keys[1]] / gaps[keys[1]]))
    for label, ratio in MISTAKES:
        cells = []
        for key in keys:
            shift = abs(means[key] * (ratio ** SLOPE[key] - 1.0))
            cells += [shift, 100 * shift / gaps[key]]
        print("   %-30s %9.3f %8.1f %% %9.3f %8.1f %%" % (label, *cells))
    print()
    for key, label in METRICS:
        drop = abs(means[key] * ((7 / 6) ** SLOPE[key] - 1.0))
        print("   %-24s one dropped drop is %4.2fx the run-to-run wobble"
              % (label, drop / wobbles[key]))
    print()


def writeFigure(data):
    """Two views of the SAME uncorrected numbers.

    TOP  the metric itself, on its own absolute scale, every run in capture order, with each class's
         mean drawn in. This is the view that answers "how much does it move against what it has to
         resolve" -- the wobble and the separation in one picture.
    BOTTOM the same runs as deviations from their own set mean, scaled by the class gap, which is the
         only form in which the two anchors may be compared numerically (§16.20.4)."""
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                         "svg.fonttype": "none"})
    figure, panels = plt.subplots(2, 2, figsize=(7.6, 6.2),
                                  gridspec_kw={"height_ratios": [1.35, 1.0]})

    for column, (key, label) in enumerate(METRICS):
        gap = classGap(data, key)
        green = np.concatenate([[r[key] for r in data[n][0]] for n in GREEN_REFERENCE])
        brown = np.concatenate([[r[key] for r in data[n][0]] for n in BROWN_REFERENCE])

        # ---------------------------------------------------------------- absolute values
        top = panels[0][column]
        top.axhspan(brown.mean(), green.mean(), color=MUTED, alpha=0.09, zorder=0)
        for level, text, colour in ((green.mean(), "green class mean", "#1b5e20"),
                                    (brown.mean(), "brown class mean", BROWN)):
            top.axhline(level, c=colour, lw=1.0, ls="--", zorder=1)
            top.text(0.5, level, " %s  %.2f" % (text, level), fontsize=6.8, color=colour,
                     va="bottom", zorder=5)
        cursor = 0
        for name, _, _ in SERIES:
            values = np.array([r[key] for r in data[name][0]])
            colour, marker = STYLE[name]
            x = np.arange(cursor, cursor + len(values))
            top.plot(x, values, marker=marker, ms=4.5, lw=1.1, c=colour,
                     markeredgecolor="white", markeredgewidth=0.4)
            cursor += len(values)
            if cursor < 24:
                top.axvline(cursor - 0.5, c=MUTED, lw=0.5, ls=":", zorder=0)
        top.set_title("%s\nclass gap %.3f" % (label, gap), fontsize=9.0, color=INK, linespacing=1.5)
        top.set_xlabel("every post-rebuild run, in capture order")
        top.set_xticks([])
        if column == 0:
            top.set_ylabel("the metric itself")

        # ---------------------------------------------------------------- gap-scaled deviations
        bottom = panels[1][column]
        for name, _, _ in SERIES:
            values = np.array([r[key] for r in data[name][0]])
            colour, marker = STYLE[name]
            sd = values.std(ddof=1) if len(values) > 1 else 0.0
            bottom.plot(range(1, len(values) + 1), 100 * (values - values.mean()) / gap,
                        marker=marker, ms=4.5, lw=1.1, c=colour, markeredgecolor="white",
                        markeredgewidth=0.4,
                        label="%-15s %4.1f %%" % (name, 100 * sd / gap) if column == 0 else None)
        band = 100 * np.std(np.concatenate(
            [np.array([r[key] for r in data[n][0]]) - np.mean([r[key] for r in data[n][0]])
             for n, _, _ in SERIES]), ddof=1) / gap
        bottom.axhspan(-band, band, color=MUTED, alpha=0.10, zorder=0)
        bottom.axhline(0, c=MUTED, lw=0.7)
        bottom.set_title("pooled wobble ±%.1f %% of the class gap" % band, fontsize=8.6, color=INK)
        bottom.set_xlabel("run within the set")
        bottom.set_ylim(-24, 26)
        if column == 0:
            bottom.set_ylabel("deviation from the set's own mean\n(% of that anchor's class gap)")

    for row in panels:
        for panel in row:
            panel.spines["top"].set_visible(False)
            panel.spines["right"].set_visible(False)

    handles, labels = panels[1][0].get_legend_handles_labels()
    legend = figure.legend(handles, labels, frameon=False, fontsize=7.0, ncol=3,
                           loc="upper center", bbox_to_anchor=(0.5, 0.035),
                           title="series, and its sd as % of the class gap")
    legend.get_title().set_fontsize(7.0)
    legend.get_title().set_color(MUTED)
    figure.suptitle("Run-to-run wobble: the superseded 600-630 metric against the adopted 620-630 + r_Q",
                    fontsize=10.0, color=INK, y=1.01)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "far620_wobble.svg"), bbox_inches="tight")
    plt.close(figure)
    print("wrote %s" % os.path.join(FIGURES, "far620_wobble.svg"))


if __name__ == "__main__":
    main()
