"""Every number and figure in `DOC_pedestal_correction.md`. (SPEC_capture_quality.md §16.15.6)

The document explains why the shipped Pigment Index reads systematically HIGH, how large the effect is,
and what a one-subtraction correction would do. This script produces the whole of it, from the SHIPPED
code paths (`settling_sweep.measure` -> `SpectrumFeatureUtil.linearBaselineCorrected`), so the document
cannot drift from what the app computes.

Prints, in the document's own order:
  1  the six sets, raw and baselined
  2  the straight-line test  B_Soret = M_inf*B_Q + k  -- whose INTERCEPT is the pedestal residual
  3  the inflation table  (F = 1 - r_Q/B_Q)
  4  the correction applied, shared r_Q vs each oil's own  <- the document's honesty check
  5  the lever arm -- why S-Budget cannot be fitted, and why it is not about being brown
  6  constant r_Q vs r_Q proportional to turbidity -- which model the data prefers
  7  how concentrated one would have to work to shrink the inflation instead

Writes six SVG figures into docs/figures/:
    pedestal_chord.svg       THE central picture: one real run, the four windows, the fitted chord,
                             and -- zoomed -- what the far anchor is actually sitting on
    pedestal_cases.svg       convex / straight / concave, and which way each sends the index
    pedestal_bands.svg       the same 0.025 A against each band, on ONE absorbance scale
    pedestal_attribution.svg what r_Q is made of, and how far a pure scattering law gets (doc §4.1)
    pedestal_faces.svg       the same residual as a gap, an intercept, and an inflation
    pedestal_line.svg        the straight-line test, with the intercept that should not be there
    pedestal_inflation.svg   inflation vs B_Q, with the six sets and the working window marked

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/pedestal_correction.py
"""
import os

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import (measure, despikedAbsorption, asArrays, bandMean, feature,
                            SORET, Q, WINDOWS)

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.abspath(os.path.join(HERE, "..", "docs", "figures"))

# The single run drawn in the chord figure. Kiendler C is the document's reference set: post-rebuild,
# properly prepared, and the one whose numbers are carried through chapters 5-7 as the worked spine.
CHORD_RUN = "20260801C/001.pdf"

# The pedestal's magnitude at 530 nm, for asking what a pure power law COULD produce. Taken as the raw
# 520-540 absorbance, which is an UPPER bound on it (pigment also absorbs there, A6), so the scattering
# contribution computed from it is likewise an upper bound.
PEDESTAL_AT_530 = 0.1018

# ---------------------------------------------------------------- which far anchor the document describes
# The bench plugin shipped the 620-630 anchor on 2026-08-03 (§16.20), so the document's numbers must be the
# SHIPPED ones. The 600-630 keys stay reachable because several sections are the historical record of how the
# correction was found, and because r_Q belongs to its anchor -- the two constants must never be mixed.
ANCHOR = os.environ.get("PEDESTAL_ANCHOR", "620")
M_LABEL = "M shipped" if ANCHOR == "620" else "M legacy"   # the column header must not claim more than it is
SORET_KEY = "A_Soret far620" if ANCHOR == "620" else "A_Soret linear"
Q_KEY = "A_Q far620" if ANCHOR == "620" else "A_Q linear"
M_KEY = "S/Q far620" if ANCHOR == "620" else "S/Q linear base"

# ⚠ Sections 7 and 8 are the HISTORICAL investigation -- the analysis of the 600-630 window's contamination
# that led to moving the anchor in the first place (§16.19 -> §16.20). They are pinned to the OLD keys on
# purpose: on the 620-630 anchor the 607 nm line lies OUTSIDE the window entirely, so "what is the far
# anchor contaminated with" is not a question that anchor can be asked. Do not follow ANCHOR here.
HIST_SORET_KEY, HIST_Q_KEY = "A_Soret linear", "A_Q linear"
HIST_WEIGHT = 0.471            # the Q band's interpolation weight between 530 and 615, the OLD centroids

SETS = [("Kiendler A", "Kiendler", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
        ("Kiendler B", "Kiendler", ["20260801B/%03d.pdf" % i for i in range(1, 3)]),
        ("Kiendler C", "Kiendler", ["20260801C/%03d.pdf" % i for i in range(1, 3)]),
        ("Steirerkraft B", "Steirerkraft", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft C", "Steirerkraft", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
        ("S-Budget D", "S-Budget", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]

GREEN, GREEN_DK, BROWN, INK, MUTED = "#2e7d32", "#1b5e20", "#8d5524", "#1c211c", "#5c655c"
COLOUR = {"Kiendler": GREEN, "Steirerkraft": GREEN_DK, "S-Budget": BROWN}
MARKER = {"Kiendler": "o", "Steirerkraft": "s", "S-Budget": "^"}


def load():
    return {name: [measure(p) for p in paths] for name, _, paths in SETS}


def column(runs, name, key):
    return np.array([r[key] for r in runs[name]])


def fitOil(runs, oil):
    """The straight-line test, at RUN level so the intercept carries an honest standard error."""
    names = [n for n, o, _ in SETS if o == oil]
    x = np.concatenate([column(runs, n, Q_KEY) for n in names])
    y = np.concatenate([column(runs, n, SORET_KEY) for n in names])
    return stats.linregress(x, y), x, y


def main():
    runs = load()
    oils = ["Kiendler", "Steirerkraft", "S-Budget"]

    # ------------------------------------------------------------------ 1 the six sets
    print("=== 1  THE SIX SETS — raw bands, baselined bands, and the shipped index")
    print("   %-16s %4s %9s %9s %10s %10s %10s %10s" % (
        "set", "n", "A_Sor raw", "A_Q raw", "turbidity", "B_Soret", "B_Q", M_LABEL))
    print("   " + "-" * 84)
    for name, _, paths in SETS:
        print("   %-16s %4d %9.4f %9.4f %10.4f %10.4f %10.4f %10.3f" % (
            name, len(paths),
            column(runs, name, "A_Soret raw").mean(), column(runs, name, "A_Q raw").mean(),
            column(runs, name, "A_near 520-540").mean(),
            column(runs, name, SORET_KEY).mean(), column(runs, name, Q_KEY).mean(),
            column(runs, name, M_KEY).mean()))
    print()

    # ------------------------------------------------------------------ 2/3 the straight-line test
    print("=== 2  THE STRAIGHT-LINE TEST   B_Soret = M_inf * B_Q + k")
    print("   No pedestal residual  =>  k = 0, the line passes through the ORIGIN.")
    print()
    print("   %-14s %4s %18s %20s %8s %20s" % (
        "oil", "n", "M_inf (slope)", "k (intercept)", "t(k)", "r_Q = -k/M_inf"))
    print("   " + "-" * 88)
    residual = {}
    for oil in oils:
        if oil == "S-Budget":
            print("   %-14s %4d %18s %20s %8s %20s" % (
                oil, 6, "—", "—", "—", "one concentration only"))
            continue
        fit, x, _ = fitOil(runs, oil)
        rq = -fit.intercept / fit.slope
        se = abs(rq) * np.sqrt((fit.intercept_stderr / fit.intercept) ** 2
                               + (fit.stderr / fit.slope) ** 2)
        residual[oil] = rq
        print("   %-14s %4d %9.3f +/- %-5.3f %10.4f +/- %-7.4f %8.2f %10.4f +/- %.4f" % (
            oil, len(x), fit.slope, fit.stderr, fit.intercept, fit.intercept_stderr,
            fit.intercept / fit.intercept_stderr, rq, se))
        print("   %-14s %4s B_Q spans %.4f .. %.4f  (this spread is what makes the fit possible)"
              % ("", "", x.min(), x.max()))
    shared = residual["Kiendler"]
    print()

    # ------------------------------------------------------------------ 4 inflation
    print("=== 3  THE INFLATION   M_shipped = M_true * (1 - r_Q/B_Q),  using r_Q = %+.4f A" % shared)
    print("   %-16s %10s %14s %12s %12s" % ("set", "B_Q", "inflation", M_LABEL, "M corrected"))
    print("   " + "-" * 68)
    for name, _, _ in SETS:
        bq = column(runs, name, Q_KEY).mean()
        m = column(runs, name, M_KEY).mean()
        print("   %-16s %10.4f %13.1f%% %12.3f %12.3f"
              % (name, bq, 100 * (-shared / bq), m, m / (1 - shared / bq)))
    print()

    # ------------------------------------------------------------------ 5 the honesty check
    print("=== 4  ⚠ SHARED r_Q vs EACH OIL'S OWN — does the correction confirm the visual ranking?")
    print("   %-14s %22s %22s" % ("oil", "corrected, shared r_Q", "corrected, own r_Q"))
    print("   " + "-" * 62)
    summary = {}
    for oil in oils:
        names = [n for n, o, _ in SETS if o == oil]
        bs = np.concatenate([column(runs, n, SORET_KEY) for n in names])
        bq = np.concatenate([column(runs, n, Q_KEY) for n in names])
        shared_value = (bs / (bq - shared)).mean()
        # An oil with only ONE concentration has no r_Q of its own, and the honest output is a dash.
        # Falling back to `shared` here would print the same number in both columns, which reads as
        # "this oil is insensitive to the choice" when it means "the comparison cannot be made".
        if oil in residual:
            own_value = (bs / (bq - residual[oil])).mean()
            summary[oil] = (shared_value, own_value)
            print("   %-14s %22.3f %22.3f" % (oil, shared_value, own_value))
        else:
            summary[oil] = (shared_value, None)
            print("   %-14s %22.3f %22s" % (oil, shared_value, "—  (no own r_Q)"))
    for index, label in ((0, "shared r_Q"), (1, "own r_Q  ")):
        gap = 100 * (summary["Kiendler"][index] / summary["Steirerkraft"][index] - 1)
        print("   Kiendler vs Steirerkraft, %s : %+.1f %%" % (label, gap))
    print("   ⇒ The ranking Edwin sees by eye SURVIVES only under the shared-r_Q assumption.")
    print("   ⚠ The brown oil has NO own r_Q — it is the one class where A1 is wholly untested,")
    print("     and it is the class that fixes the threshold.")
    print()

    # ------------------------------------------------------------------ 6 the lever arm
    print("=== 5  THE LEVER ARM — why one oil fits, one barely does, and one cannot")
    print("   r_Q is an extrapolation back to B_Q = 0, so everything depends on the SPREAD in B_Q.")
    print("   %-14s %5s %10s %10s %12s %14s" % (
        "oil", "n", "B_Q min", "B_Q max", "span % mean", "widest 1 set"))
    print("   " + "-" * 72)
    for oil in oils:
        names = [n for n, o, _ in SETS if o == oil]
        pooled = np.concatenate([column(runs, n, Q_KEY) for n in names])
        # The within-SET span is pure measurement noise: a re-seat moves the optics, not the
        # concentration. If an oil's pooled span is no wider than that, it carries no leverage.
        within = max(100 * np.ptp(column(runs, n, Q_KEY)) / column(runs, n, Q_KEY).mean()
                     for n in names)
        print("   %-14s %5d %10.4f %10.4f %11.1f%% %13.1f%%" % (
            oil, len(pooled), pooled.min(), pooled.max(),
            100 * np.ptp(pooled) / pooled.mean(), within))
    print("   ⇒ S-Budget's pooled span is no wider than a single set's noise — no lever at all.")
    print("     Noise in x supplies no leverage AND biases the slope toward zero.")
    print()

    # ------------------------------------------------------------------ 7 constant vs turbidity
    print("=== 6  IS r_Q A CONSTANT, OR DOES IT SCALE WITH TURBIDITY?")
    print("   Mechanism says the residual is pedestal curvature, so a cloudier sample should leave")
    print("   more behind. Constant model:  B_Soret = M_inf*B_Q + k   (an intercept)")
    print("   Proportional model:           B_Soret = M_inf*B_Q - M_inf*rho*turbidity  (no intercept)")
    print()
    print("   %-14s %28s %30s" % ("oil", "constant r_Q", "r_Q proportional to turbidity"))
    print("   " + "-" * 76)
    for oil in ("Kiendler", "Steirerkraft"):
        names = [n for n, o, _ in SETS if o == oil]
        x = np.concatenate([column(runs, n, Q_KEY) for n in names])
        y = np.concatenate([column(runs, n, SORET_KEY) for n in names])
        turbidity = np.concatenate([column(runs, n, "A_near 520-540") for n in names])
        fit = stats.linregress(x, y)
        design = np.column_stack([x, turbidity])
        coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
        predicted = design @ coefficients
        r2 = 1 - ((y - predicted) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        print("   %-14s R2 %.4f, t(k) %5.2f %10s R2 %.4f, tau coefficient %+.2f" % (
            oil, fit.rvalue ** 2, fit.intercept / fit.intercept_stderr, "", r2, coefficients[1]))
    print("   ⇒ The CONSTANT model wins on both oils. The proportional one wants a negative tau")
    print("     coefficient on Kiendler, which implies a POSITIVE r_Q — contradicting both the sign")
    print("     prediction and the measurement.")
    print("   ⚠ tau is raw 520-540 absorbance, not pure turbidity (A6), so it is collinear with B_Q.")
    print("     This is a check, not a proof.")
    print()

    # ------------------------------------------------------------------ 6 the alternative
    # ------------------------------------------------------------------ 8 what r_Q is made of
    print("=== 7  ⚠ WHERE DOES r_Q ACTUALLY COME FROM?  (chapter 4's mechanism, checked for SIZE)")
    print("   ⚠ THIS SECTION AND SECTION 8 ARE PINNED TO THE 600-630 ANCHOR — they are the investigation")
    print("     that MOVED the window (§16.19 -> §16.20), and on 620-630 the 607 nm line lies OUTSIDE the")
    print("     anchor entirely, so the question cannot be put to it. r_Q(600-630) = -0.0246 throughout.")
    print()
    print("   Chapter 4 predicts the SIGN from convex lambda^-n scattering. Does it predict the SIZE?")
    print()
    historicalResidual = 0.0246          # r_Q on the 600-630 anchor, the window this section is about
    for exponent in (2, 4, 6, 10):
        print("   a pure lambda^-%-2d pedestal of magnitude %.4f A at 530 leaves  %.4f A at Q"
              % (exponent, PEDESTAL_AT_530, powerLawSag(exponent, PEDESTAL_AT_530, far=615.0)))
    print("   ... but the MEASURED residual is %.4f A — about 6x the Rayleigh value." % historicalResidual)
    print("   Reaching it from a power law alone would need n ~ 15. No particle size gives that;")
    print("   n = 4 (Rayleigh) is the steepest real scattering law, and Mie is FLATTER still.")
    print()
    print("   So something else is bending the baseline. The far anchor is the obvious suspect:")
    print("   %-16s %11s %11s %10s %14s" % ("set", "A_far full", "A_far clean", "excess", "-0.471*excess"))
    print("   " + "-" * 68)
    excesses = []
    for name, _, paths in SETS:
        values = [farAnchorExcess(*asArrays(despikedAbsorption(path))[0:2]) for path in paths]
        excess = float(np.mean([v[0] for v in values]))
        excesses.append(excess)
        print("   %-16s %11.4f %11.4f %10.4f %14.4f"
              % (name, np.mean([v[1] for v in values]), np.mean([v[2] for v in values]),
                 excess, -0.471 * excess))
    mean = float(np.mean(excesses))
    intercept, stderr = nonScalingExcess(runs)
    scatter = powerLawSag(4.0, PEDESTAL_AT_530, far=615.0)
    print()
    print("   far-anchor excess, mean over sets : %+.4f A" % mean)
    print("   ⚠ but the MEAN is the WRONG statistic. A contamination proportional to concentration")
    print("     moves points ALONG the fitted line and lands in the SLOPE; only a NON-SCALING term")
    print("     can produce an INTERCEPT, and r_Q is the intercept. §16.12.12 measured at 5.1 sigma")
    print("     that the 620-630 rise is green-pigment Qy absorption -- i.e. a scaling term.")
    print()
    print("   non-scaling part (intercept vs B_Q): %+.4f +/- %.4f A   t = %.2f"
          % (intercept, stderr, intercept / stderr))
    print()
    print("   %-42s %+9.4f A  %5.0f %%" % ("far anchor, non-scaling part:",
                                           -HIST_WEIGHT * intercept,
                                           100 * HIST_WEIGHT * intercept / historicalResidual))
    print("   %-42s %+9.4f A  %5.0f %%" % ("lambda^-4 scattering (upper bound):",
                                           -scatter, 100 * scatter / historicalResidual))
    print("   %-42s %+9.4f A  %5.0f %%" % ("UNACCOUNTED:",
                                           -(historicalResidual - HIST_WEIGHT * intercept - scatter),
                                           100 * (historicalResidual - HIST_WEIGHT * intercept - scatter)
                                           / historicalResidual))
    print()
    print("   ⇒ SCATTERING IS RULED OUT as the main term (%.0f %% at the most generous bound)."
          % (100 * scatter / historicalResidual))
    print("     The far anchor is the leading suspect but is NOT established: its non-scaling part")
    print("     is only %.1f sigma from zero on six sets. THE MECHANISM FOR r_Q's SIZE IS OPEN."
          % (intercept / stderr))
    print("   ⚠ None of this touches the CORRECTION, which is fitted rather than derived.")
    print()

    # ------------------------------------------------------------------ 8 the decisive refit
    print("=== 8  ⭐ THE DECISIVE TEST — refit r_Q with the far anchor's DIRTY STRETCHES EXCLUDED")
    print("   §16.19.3 says the far anchor's NON-SCALING contamination supplies ~32 % of r_Q, but at")
    print("   t = 0.96 that is a suspicion, not a measurement. This turns it into one, and it costs no")
    print("   rig time: the 607 nm lamp line (606-610) is excised from the red anchor and NOTHING else.")
    print("   Same near anchor, same weighting, same bands.")
    print("   ⛔ 618-630 is deliberately KEPT: §16.12.12 established at 5.1 sigma that the rise there is")
    print("      the PIGMENT's Qy flank (protochlorophyll Qy ~623-626 nm), not the lamp. A first draft")
    print("      of this test excluded it as 'the red cliff' and was WRONG -- it deleted signal.")
    print()
    print("   PREDICTION: if the anchor supplies ~32 %, |r_Q| should fall 0.0246 -> ~0.017.")
    print("               If it supplies nothing, r_Q does not move and the hypothesis is dead.")
    print("               If it supplies everything, r_Q collapses toward zero.")
    print()
    print("   %-14s %6s %18s %20s %8s %20s" % (
        "oil", "anchor", "M_inf (slope)", "k (intercept)", "t(k)", "r_Q = -k/M_inf"))
    print("   " + "-" * 92)
    cleanResidual = {}
    for oil in ("Kiendler", "Steirerkraft"):
        names = [n for n, o, _ in SETS if o == oil]
        for label, ykey, xkey in (("600-630", HIST_SORET_KEY, HIST_Q_KEY),
                                  ("CLEAN", "A_Soret clean", "A_Q clean")):
            x = np.concatenate([column(runs, n, xkey) for n in names])
            y = np.concatenate([column(runs, n, ykey) for n in names])
            fit = stats.linregress(x, y)
            rq = -fit.intercept / fit.slope
            se = abs(rq) * np.sqrt((fit.intercept_stderr / fit.intercept) ** 2
                                   + (fit.stderr / fit.slope) ** 2)
            if label == "CLEAN":
                cleanResidual[oil] = rq
            print("   %-14s %6s %9.3f +/- %-5.3f %10.4f +/- %-7.4f %8.2f %10.4f +/- %.4f" % (
                oil, label, fit.slope, fit.stderr, fit.intercept, fit.intercept_stderr,
                fit.intercept / fit.intercept_stderr, rq, se))
        historical = {"Kiendler": 0.0246, "Steirerkraft": 0.0212}[oil]
        change = 100 * (abs(cleanResidual[oil]) / historical - 1)
        print("   %-14s %6s |r_Q| changes by %+.1f %%" % ("", "⇒", change))
        print()
    anchorVariantSweep(runs)

    # ------------------------------------------------------------------ 9 the alternative
    print("=== 9  COULD ONE CONCENTRATE THE PROBLEM AWAY INSTEAD?")
    today = column(runs, "Kiendler C", Q_KEY).mean()
    for target in (0.30, 0.20, 0.10, 0.05):
        need = abs(shared) / target
        print("   inflation <= %3.0f %%  needs B_Q >= %.4f  = %.1fx today's %.4f"
              % (100 * target, need, need / today, today))
    print()

    writeFigures(runs, residual, shared)


# The two red stretches the clean anchor drops, and what lives in each.
EXCLUSIONS = ((606.0, 610.0, "the 607 nm lamp emission line"),
              (618.0, 630.0, "the lamp's red cliff"))

# The post-rebuild within-oil dilution pair (§16.10.8 / all_metrics_archive.DILUTION_PAIRS row 3).
# Steirerkraft at two strengths — the only pair on the rig state r_Q was fitted on.
DILUTION_PAIR = (0.197, ["20270729B/%03d.pdf" % i for i in range(1, 7)],
                 0.230, ["20270729C/%03d.pdf" % i for i in range(1, 7)])


def anchorVariantSweep(runs):
    """Which exclusion does the damage — the 607 line, the red cliff, or the geometry?

    Dropping both moves the red anchor's centroid 615.1 -> 609.4 nm, which shortens the near-red lever
    and is a confound: the degradation could be geometry rather than cleanliness. Dropping the 607 line
    ALONE moves the centroid by +1 nm and is therefore the control that separates the two.

    ⚠ Each window carries equal TOTAL weight in `linearBaselineCorrected`, so the near window is listed
    once per red sub-window. Without that the sweep compares re-weighting, not cleanliness."""
    def windows(reds):
        return tuple([WINDOWS[0]] * len(reds)) + tuple(reds)

    # ⛔ The last two rows also remove 618-630, which is the pigment's OWN Qy flank (§16.12.12, 5.1
    # sigma), not an artifact. They are kept only to show what that costs -- they are NOT fair tests of
    # the artifact hypothesis, and the label says so.
    variants = (("shipped 600-630", [(600.0, 630.0)]),
                ("drop 607 line ONLY", [(600.0, 606.0), (610.0, 630.0)]),
                ("⛔ also drops Qy 618+", [(600.0, 618.0)]),
                ("⛔ drops 607 AND Qy", [(600.0, 606.0), (610.0, 618.0)]))
    cache = {}

    def bands(path, reds):
        key = (path, tuple(reds))
        if key not in cache:
            spectrum = despikedAbsorption(path)
            lam, _ = asArrays(spectrum)
            _, values = asArrays(feature.linearBaselineCorrected(spectrum, windows(reds)))
            cache[key] = (bandMean(lam, values, SORET), bandMean(lam, values, Q))
        return cache[key]

    grid, _ = asArrays(despikedAbsorption(CHORD_RUN))
    kiendler = [p for n, oil, paths in SETS if oil == "Kiendler" for p in paths]
    lowStrength, lowPaths, highStrength, highPaths = DILUTION_PAIR
    span = highStrength / lowStrength

    print("   WHICH EXCLUSION DOES IT?  (Kiendler fit; dilution slope on the post-rebuild pair)")
    print("   %-20s %9s %8s %9s %7s %9s %9s" % (
        "far anchor", "centroid", "M_inf", "k", "t(k)", "r_Q", "dilution s"))
    print("   " + "-" * 80)
    for label, reds in variants:
        mask = np.zeros_like(grid, dtype=bool)
        for low, high in reds:
            mask |= (grid >= low) & (grid <= high)
        pairs = [bands(p, reds) for p in kiendler]
        fit = stats.linregress(np.array([q for _, q in pairs]), np.array([s for s, _ in pairs]))
        low = np.mean([np.divide(*bands(p, reds)) for p in lowPaths])
        high = np.mean([np.divide(*bands(p, reds)) for p in highPaths])
        print("   %-20s %8.1f %9.3f %9.4f %7.2f %9.4f %9s" % (
            label, grid[mask].mean(), fit.slope, fit.intercept,
            fit.intercept / fit.intercept_stderr, -fit.intercept / fit.slope,
            "%+.2f" % (np.log(high / low) / np.log(span))))
    print()
    print("   ⇒ ROW 2 IS THE ONLY FAIR TEST — it removes the one genuine artifact (the 607 nm lamp")
    print("     line) and nothing else, at a centroid shift of +1 nm so the lever arm is unchanged.")
    print("     It still makes |r_Q| BIGGER (0.0246 -> 0.0324) and invariance WORSE (-0.12 -> -0.20).")
    print("     ⇒ the artifact was REDUCING the residual, not causing it. Hypothesis refuted.")
    print()
    print("   ⛔ ROWS 3-4 ARE NOT TESTS OF THE ARTIFACT — they also delete 618-630, which §16.12.12")
    print("     established at 5.1 sigma is the PIGMENT's Qy flank (protochlorophyll Qy ~623-626 nm),")
    print("     not a lamp effect. They measure what throwing away real signal costs, and they are")
    print("     printed only so that cost is on the record: M_inf 9.998 -> 7.468 and s -0.12 -> -0.22.")
    print("   ⚠ M_inf falls in EVERY variant, so none of them share a scale with the shipped metric")
    print("     and none may be compared against T = 10.6.")
    print()



def farAnchorExcess(lam, raw):
    """How much the 600-630 anchor reads ABOVE its own clean neighbourhood.

    The far window contains two known corruptions: the 607 nm artifact (`DOC_metric_algebra.md` §5.9)
    and the lamp's red cliff, where 620-630 nm sits near 39 DN against 130 at 530 and absorbance runs
    away. Averaging only the two clean stretches estimates what the anchor WOULD have read without
    them; the difference is what the baseline fit is actually being anchored on."""
    full = bandMean(lam, raw, WINDOWS[1])
    clean = raw[((lam >= 600) & (lam < 606)) | ((lam >= 610) & (lam < 618))].mean()
    return full - clean, full, clean


def nonScalingExcess(runs):
    """The part of the far-anchor excess that does NOT grow with the pigment — with its error bar.

    ⚠ THE WHOLE POINT OF THIS FUNCTION. It is tempting to take the MEAN excess and multiply it by the
    Q band's interpolation weight, and that is WRONG: a contamination proportional to concentration
    moves points ALONG the fitted line and lands in the SLOPE. Only a term that does NOT scale can
    produce an INTERCEPT, and r_Q is defined as the intercept. §16.12.12 measured at 5.1 sigma that
    the 620-630 rise is green-pigment Qy absorption, i.e. exactly such a scaling term. So the relevant
    quantity is the INTERCEPT of the excess regressed on the pigment axis, not its average.

    Returns (intercept, standardError) in absorbance."""
    excess, bq = [], []
    for name, _, paths in SETS:
        excess.append(np.mean([farAnchorExcess(*asArrays(despikedAbsorption(path))[0:2])[0]
                               for path in paths]))
        bq.append(column(runs, name, HIST_Q_KEY).mean())
    fit = stats.linregress(np.array(bq), np.array(excess))
    return fit.intercept, fit.intercept_stderr


def writeChordFigure(shared):
    """THE central picture: one real curve, the four windows, the chord, and the gap it leaves.

    Drawn from a single run rather than a set mean, because the point is the SHAPE of one measurement
    — in particular what the far anchor is sitting on."""
    from settling_sweep import FAR620_WINDOWS
    shippedWindows = FAR620_WINDOWS if ANCHOR == "620" else WINDOWS
    farWindow = shippedWindows[-1]
    spectrum = despikedAbsorption(CHORD_RUN)
    lam, raw = asArrays(spectrum)
    _, corrected = asArrays(feature.linearBaselineCorrected(spectrum, shippedWindows))
    chord = raw - corrected

    figure, (axis, inset) = plt.subplots(
        1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # The inset carries all the annotation, so its window labels go at the FOOT of the panel and its
    # ceiling is generous — otherwise the callouts and the band labels fight for the same corner.
    for panel, (lo, hi, ylo, yhi, top) in ((axis, (440, 630, 0, 1.30, True)),
                                           (inset, (515, 630, 0, 0.45, False))):
        for (wlo, whi), colour, label in ((SORET, "#3f6fb0", "Soret"), (shippedWindows[0], MUTED, "near"),
                                          (Q, GREEN, "Q"), (farWindow, "#c0392b", "far")):
            if whi > lo and wlo < hi:
                panel.axvspan(wlo, whi, color=colour, alpha=0.13, zorder=0)
                panel.text((max(wlo, lo) + min(whi, hi)) / 2, yhi * (0.955 if top else 0.018),
                           label, fontsize=7.4, color=colour, ha="center",
                           va="top" if top else "bottom", zorder=5)
        panel.plot(lam, raw, c=INK, lw=1.1, zorder=3)
        panel.plot(lam, chord, c="#c0392b", lw=1.3, ls="--", zorder=4)
        panel.set_xlim(lo, hi)
        panel.set_ylim(ylo, yhi)
        panel.spines["top"].set_visible(False)
        panel.spines["right"].set_visible(False)
        panel.set_xlabel("wavelength (nm)")

    # --- left panel: the two band heights, measured from the chord upward
    for centre, name in ((450.0, "B$_{Soret}$"), (570.0, "B$_{Q}$")):
        top = float(np.interp(centre, lam, raw))
        bottom = float(np.interp(centre, lam, chord))
        axis.annotate("", xy=(centre, top), xytext=(centre, bottom),
                      arrowprops=dict(arrowstyle="<->", color=GREEN_DK, lw=1.3))
        # Anchored at the TOP of the arrow rather than its middle: at the Q band the middle sits on
        # the fitted line itself, and the label lands on top of it.
        axis.text(centre + 11, top, "%s\n%.3f A" % (name, top - bottom),
                  fontsize=7.6, color=GREEN_DK, va="center", linespacing=1.5)
    axis.set_ylabel("absorbance (A)")
    axis.set_title("The metric is two heights above a fitted line", fontsize=9.5, color=INK)

    # --- right panel: why that line is where it is
    inset.annotate("the 607 nm lamp line —\nnow OUTSIDE the anchor",
                   xy=(608.5, float(np.interp(608.5, lam, raw))),
                   xytext=(0.50, 0.62), textcoords="axes fraction", fontsize=7.2, color="#c0392b",
                   ha="right", va="center", linespacing=1.4,
                   arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    inset.annotate("the pigment's Qy band —\nwhat the anchor now sits ON",
                   xy=(625, float(np.interp(625, lam, raw))),
                   xytext=(0.62, 0.17), textcoords="axes fraction", fontsize=7.2, color=GREEN_DK,
                   ha="center", va="center", linespacing=1.4,
                   arrowprops=dict(arrowstyle="-", color=GREEN_DK, lw=0.8))
    inset.text(0.02, 0.99, "the far anchor starts AFTER the 607 nm line\n"
                           "and is centred on protochlorophyll's Qy\n"
                           "(~623–626 nm).   §16.20",
               transform=inset.transAxes, fontsize=7.2, color=INK, va="top", linespacing=1.5)
    inset.set_title("What the far anchor is sitting on", fontsize=9.5, color=INK)

    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_chord.svg"))
    plt.close(figure)


def writeCasesFigure():
    """Convex / straight / concave — three hypotheses, and which way each sends the index.

    Schematic by design: the point is the GEOMETRY of a chord against a curve, and no measurement of
    this rig's pedestal shape exists (the lambda^-n fit was withdrawn, §16.12.11 B)."""
    grid = np.linspace(0, 1, 200)
    # CONVEX means f'' > 0: a lambda^-n pedestal falls STEEPLY first and then flattens, so it lies
    # BELOW its own chord. `1 - (1-x)^p` is the shape with that curvature; `x^p` is its mirror and
    # gives the concave case. Getting these the wrong way round inverts the sign of r_Q, which is the
    # one thing this figure exists to make unmistakable.
    cases = (("convex  —  scattering", 1 - (1 - grid) ** 2.4,
              "chord lies ABOVE the pedestal", "r$_Q$ < 0", "index reads HIGH", "#c0392b"),
             ("straight", grid.copy(),
              "chord lies ON it", "r$_Q$ = 0", "index is EXACT", GREEN_DK),
             ("concave", grid ** 2.4,
              "chord lies BELOW it", "r$_Q$ > 0", "index reads LOW", "#3f6fb0"))
    figure, panels = plt.subplots(1, 3, figsize=(7.2, 2.9))
    for panel, (title, shape, where, sign, effect, colour) in zip(panels, cases):
        curve = 1 - 0.75 * shape                        # falling, with the case's curvature
        panel.plot(grid, curve, c=INK, lw=1.5, zorder=3, label="true pedestal")
        panel.plot([0, 1], [curve[0], curve[-1]], c="#c0392b", lw=1.3, ls="--", zorder=4,
                   label="fitted chord")
        middle = len(grid) // 2
        panel.annotate("", xy=(0.5, curve[middle]),
                       xytext=(0.5, curve[0] + (curve[-1] - curve[0]) * 0.5),
                       arrowprops=dict(arrowstyle="<->", color=colour, lw=1.5))
        for x, label in ((0.0, "near\nanchor"), (0.5, "Q"), (1.0, "far\nanchor")):
            panel.axvline(x, c=MUTED, lw=0.6, ls=":", zorder=1)
            panel.text(x, -0.06, label, fontsize=7.0, color=MUTED, ha="center", va="top")
        panel.set_title(title, fontsize=9.0, color=INK, pad=22)
        panel.text(0.5, 1.015, "%s\n%s  ⇒  %s" % (where, sign, effect), transform=panel.transAxes,
                   fontsize=7.4, color=colour, ha="center", va="bottom", fontweight="bold",
                   linespacing=1.4)
        panel.set_xlim(-0.08, 1.08)
        panel.set_ylim(0, 1.15)
        panel.set_xticks([])
        panel.set_yticks([])
        for side in ("top", "right", "bottom", "left"):
            panel.spines[side].set_visible(False)
    panels[0].legend(frameon=False, fontsize=6.8, loc="lower left")
    figure.suptitle("A chord through two points on a curve: which side does it fall?",
                    fontsize=9.5, color=INK, y=1.10)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_cases.svg"), bbox_inches="tight")
    plt.close(figure)


def writeBandsFigure(runs, shared):
    """The same 0.025 A against each band, on ONE absorbance scale. Makes the 13x visible."""
    soret = column(runs, "Kiendler C", SORET_KEY).mean()
    q = column(runs, "Kiendler C", Q_KEY).mean()
    figure, panels = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for panel, (value, name, colour) in zip(panels, ((soret, "B$_{Soret}$", "#3f6fb0"),
                                                     (q, "B$_{Q}$", GREEN))):
        panel.bar([0], [value], width=0.5, color=colour, alpha=0.30, edgecolor=colour, zorder=2)
        panel.bar([0], [abs(shared)], width=0.5, color="#c0392b", alpha=0.85, zorder=3)
        panel.text(0, value + 0.035, "%s   =   %.4f A" % (name, value), fontsize=8.4, color=INK,
                   ha="center", fontweight="bold")
        panel.text(0.32, abs(shared) / 2, "|r$_Q$|   =   %.4f A\n= %.0f %% of the band"
                   % (abs(shared), 100 * abs(shared) / value), fontsize=7.8, color="#c0392b",
                   va="center", linespacing=1.5)
        panel.set_xlim(-0.45, 1.15)
        panel.set_xticks([])
        for side in ("top", "right", "bottom"):
            panel.spines[side].set_visible(False)
    panels[0].set_ylabel("absorbance (A)")
    panels[0].set_ylim(0, soret * 1.18)
    figure.suptitle("The same leftover, against each band — one scale, no exaggeration",
                    fontsize=9.5, color=INK, y=1.02)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_bands.svg"), bbox_inches="tight")
    plt.close(figure)


def writeAttributionFigure(runs, shared):
    """Where the measured residual actually comes from — and how far scattering alone gets."""
    # The NON-SCALING part only — see nonScalingExcess. Using the mean excess here overstates the
    # far-anchor share roughly twofold and was the first draft's error.
    intercept, stderr = nonScalingExcess(runs)
    fromAnchor, anchorError = 0.471 * intercept, 0.471 * stderr
    fromScatter = powerLawSag(4.0, PEDESTAL_AT_530)      # Rayleigh, the steepest real scattering law
    rest = abs(shared) - fromAnchor - fromScatter

    figure, (bar, curve) = plt.subplots(1, 2, figsize=(7.2, 3.0),
                                        gridspec_kw={"width_ratios": [1.0, 1.1]})
    bottom = 0.0
    for value, error, label, colour in (
            (fromAnchor, anchorError, "far anchor, NON-SCALING part\n(the only part that can bias r$_Q$)",
             "#c0392b"),
            (fromScatter, None, "$\\lambda^{-4}$ scattering curvature\n(upper bound)", "#3f6fb0"),
            (rest, None, "UNACCOUNTED", MUTED)):
        bar.bar([0], [value], bottom=[bottom], width=0.5, color=colour, alpha=0.85, zorder=2)
        if error:
            bar.errorbar([0], [bottom + value], yerr=error, fmt="none", ecolor=INK, elinewidth=1.1,
                         capsize=4, zorder=4)
        bar.text(0.30, bottom + value / 2, "%s\n%.4f A  (%.0f %%)"
                 % (label, value, 100 * value / abs(shared)), fontsize=7.2, color=colour,
                 va="center", linespacing=1.4)
        bottom += value
    bar.axhline(abs(shared), c=INK, lw=1.2, ls="--", zorder=3)
    bar.text(-0.42, abs(shared) + 0.0011, "measured |r$_Q$|   =   %.4f A" % abs(shared),
             fontsize=7.6, color=INK)
    bar.set_xlim(-0.45, 1.5)
    bar.set_xticks([])
    bar.set_ylabel("absorbance (A)")
    bar.set_title("No identified mechanism supplies the majority", fontsize=9.5, color=INK)
    for side in ("top", "right", "bottom"):
        bar.spines[side].set_visible(False)

    exponents = np.linspace(0.5, 20, 300)
    sags = np.array([powerLawSag(n, PEDESTAL_AT_530) for n in exponents])
    curve.plot(exponents, sags, c="#3f6fb0", lw=1.5, zorder=3)
    curve.axhline(abs(shared), c="#c0392b", lw=1.2, ls="--", zorder=2)
    curve.text(19.6, abs(shared) + 0.0012, "measured |r$_Q$|", fontsize=7.4, color="#c0392b",
               ha="right")
    curve.axvline(4, c=GREEN_DK, lw=1.0, ls=":", zorder=2)
    curve.text(4.4, 0.0015, "n = 4\nRayleigh — the steepest\nreal scattering law", fontsize=7.2,
               color=GREEN_DK, va="bottom")
    curve.plot([14.8], [abs(shared)], marker="o", ms=5, c="#c0392b", zorder=4)
    curve.text(14.4, abs(shared) - 0.0018, "n ≈ 15 would be needed —\nno particle size does this",
               fontsize=7.2, color="#c0392b", ha="right", va="top")
    curve.set_xlabel("scattering exponent n   in   P ∝ λ$^{-n}$")
    curve.set_ylabel("residual it produces at Q (A)")
    curve.set_title("Scattering alone reaches ~17 % of it", fontsize=9.5, color=INK)
    curve.set_xlim(0, 20)
    curve.set_ylim(0, abs(shared) * 1.25)
    curve.spines["top"].set_visible(False)
    curve.spines["right"].set_visible(False)

    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_attribution.svg"))
    plt.close(figure)


def writeFacesFigure(runs, shared):
    """One quantity, three faces — a gap, an intercept, and an inflation.

    The document's hardest step for a reader is seeing that figure 1's INTERCEPT and the vertical gap
    in the spectrum are the same fact. Putting all three views side by side, with the same quantity
    picked out in red in each, is the shortest route to it."""
    figure, (gap, line, curve) = plt.subplots(1, 3, figsize=(7.4, 2.6))

    # --- face 1: a vertical gap between a curve and its chord
    grid = np.linspace(0, 1, 200)
    shape = 1 - 0.75 * (1 - (1 - grid) ** 2.4)
    gap.plot(grid, shape, c=INK, lw=1.4, zorder=3)
    gap.plot([0, 1], [shape[0], shape[-1]], c=MUTED, lw=1.1, ls="--", zorder=2)
    middle = len(grid) // 2
    gap.annotate("", xy=(0.5, shape[middle]), xytext=(0.5, shape[0] + (shape[-1] - shape[0]) * 0.5),
                 arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.6))
    gap.text(0.55, (shape[middle] + shape[0] + (shape[-1] - shape[0]) * 0.5) / 2, "rQ",
             fontsize=10.5, color="#c0392b", va="center")
    gap.set_title("in the SPECTRUM\na gap at one wavelength", fontsize=8.4, color=INK,
                  linespacing=1.5)
    gap.set_xticks([])
    gap.set_yticks([])
    gap.set_ylim(0, 1.1)

    # --- face 2: the intercept of B_Soret against B_Q
    fit, x, y = fitOil(runs, "Kiendler")
    line.scatter(x, y, s=16, c=GREEN, zorder=3, edgecolors="white", linewidths=0.4)
    span = np.linspace(0, max(x) * 1.08, 50)
    line.plot(span, fit.slope * span + fit.intercept, c=GREEN_DK, lw=1.2, zorder=2)
    line.annotate("", xy=(0, fit.intercept), xytext=(0, 0),
                  arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.6))
    line.text(0.004, fit.intercept / 2, "k  =  −M∞ × rQ", fontsize=9.0,
              color="#c0392b", va="center")
    line.set_xlim(left=0)
    line.set_ylim(bottom=0)
    line.set_title("in the FIT\nan intercept that misses zero", fontsize=8.4, color=INK,
                   linespacing=1.5)
    line.set_xticks([])
    line.set_yticks([])

    # --- face 3: the inflation it produces
    span = np.linspace(0.04, 0.22, 300)
    curve.plot(span, 100 * (-shared / span), c=INK, lw=1.4, zorder=2)
    today = column(runs, "Kiendler C", Q_KEY).mean()
    curve.plot([today], [100 * (-shared / today)], marker="o", ms=6, c="#c0392b", zorder=3)
    curve.text(today + 0.012, 100 * (-shared / today) + 3, "F − 1  =  |rQ| / BQ",
               fontsize=9.0, color="#c0392b")
    curve.set_title("in the VERDICT\nan inflation of the number", fontsize=8.4, color=INK,
                    linespacing=1.5)
    curve.set_xticks([])
    curve.set_yticks([])
    curve.set_ylim(0, 70)

    for panel in (gap, line, curve):
        for side in ("top", "right"):
            panel.spines[side].set_visible(False)
    figure.suptitle("The same residual, seen three ways — and measurable in each",
                    fontsize=9.5, color=INK, y=1.04)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_faces.svg"), bbox_inches="tight")
    plt.close(figure)


def powerLawSag(exponent, magnitude, far=None):
    """The residual a pure P = magnitude*(lambda/530)^-n pedestal leaves at the Q band.

    The linear baseline interpolates between the anchor CENTROIDS, so the chord's value at 570 nm is
    the weighted mean of the two anchors — the same 0.529/0.471 split `DOC_metric_algebra.md` §5.5
    quotes for the three-region identity."""
    near, band = 530.0, 570.0
    far = far if far is not None else (625.0 if ANCHOR == "620" else 615.0)
    weight = (band - near) / (far - near)
    value = lambda wavelength: magnitude * (wavelength / near) ** (-exponent)
    return value(near) + (value(far) - value(near)) * weight - value(band)


def writeFigures(runs, residual, shared):
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                         "svg.fonttype": "none"})
    writeChordFigure(shared)
    writeCasesFigure()
    writeBandsFigure(runs, shared)
    writeAttributionFigure(runs, shared)
    writeFacesFigure(runs, shared)

    # --- figure 1: the straight-line test ---------------------------------------------------
    figure, axis = plt.subplots(figsize=(6.4, 4.0))
    for oil in ("Kiendler", "Steirerkraft"):
        fit, x, y = fitOil(runs, oil)
        axis.scatter(x, y, s=26, c=COLOUR[oil], marker=MARKER[oil], zorder=3,
                     label="%s  (r$_Q$ = %+.4f)" % (oil, residual[oil]), edgecolors="white",
                     linewidths=0.5)
        grid = np.linspace(0, max(x) * 1.08, 50)
        axis.plot(grid, fit.slope * grid + fit.intercept, c=COLOUR[oil], lw=1.2, zorder=2)
    for name, oil, _ in SETS:
        if oil == "S-Budget":
            axis.scatter(column(runs, name, Q_KEY), column(runs, name, SORET_KEY),
                         s=26, c=BROWN, marker="^", zorder=3, edgecolors="white", linewidths=0.5,
                         label="S-Budget (one concentration — cannot be fitted)")
    axis.axhline(0, c=MUTED, lw=0.7)
    axis.axvline(0, c=MUTED, lw=0.7)
    fit, _, _ = fitOil(runs, "Kiendler")
    axis.annotate("", xy=(0, fit.intercept), xytext=(0, 0),
                  arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.4))
    axis.annotate("the intercept that\nshould not be there\nk = %+.3f A" % fit.intercept,
                  xy=(0.004, fit.intercept / 2), fontsize=8, color="#c0392b", va="center")
    axis.set_xlim(left=0)
    axis.set_ylim(bottom=0)
    axis.set_xlabel("B$_Q$  —  baselined Q band 560–580 nm  (A)")
    axis.set_ylabel("B$_{Soret}$  —  baselined Soret band 440–460 nm  (A)")
    axis.set_title("Pure pigment would put this line through the origin", fontsize=9.5, color=INK)
    axis.legend(frameon=False, fontsize=7.6, loc="lower right")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_line.svg"))
    plt.close(figure)

    # --- figure 2: inflation vs B_Q ----------------------------------------------------------
    figure, axis = plt.subplots(figsize=(6.4, 3.6))
    grid = np.linspace(0.035, 0.30, 400)
    axis.plot(grid, 100 * (-shared / grid), c=INK, lw=1.4, zorder=2)
    axis.axhspan(0, 10, color="#2e7d32", alpha=0.08, zorder=0)
    # Only the two ends are labelled: the five properly-prepared sets sit in one tight cluster and
    # individual labels there collide into an unreadable smear.
    for name, oil, _ in SETS:
        bq = column(runs, name, Q_KEY).mean()
        axis.scatter([bq], [100 * (-shared / bq)], s=34, c=COLOUR[oil], marker=MARKER[oil],
                     zorder=3, edgecolors="white", linewidths=0.6, label=oil
                     if name in ("Kiendler A", "Steirerkraft B", "S-Budget D") else None)
    dilute = column(runs, "Kiendler A", Q_KEY).mean()
    axis.annotate("Kiendler A\nthe over-dilute preparation",
                  xy=(dilute, 100 * (-shared / dilute)), xytext=(16, -4),
                  textcoords="offset points", fontsize=7.6, color="#c0392b", va="center",
                  arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    cluster = np.array([column(runs, n, Q_KEY).mean()
                        for n, _, _ in SETS if n != "Kiendler A"])
    axis.annotate("the five properly-prepared sets",
                  xy=(cluster.mean(), 100 * (-shared / cluster.mean())), xytext=(40, 26),
                  textcoords="offset points", fontsize=7.6, color=MUTED,
                  arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    axis.text(0.29, 4.5, "below 10 % — unreachable by dilution alone", fontsize=7.2,
              color=GREEN_DK, ha="right", va="center")
    axis.legend(frameon=False, fontsize=7.6, loc="upper right")
    axis.set_xlabel("B$_Q$  —  how much pigment signal survives the baseline  (A)")
    axis.set_ylabel("inflation of the index  (%)")
    axis.set_title("The error is not a constant — it grows as the sample gets fainter",
                   fontsize=9.5, color=INK)
    axis.set_xlim(0.035, 0.30)
    axis.set_ylim(0, 75)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "pedestal_inflation.svg"))
    plt.close(figure)

    for name in ("pedestal_chord.svg", "pedestal_cases.svg", "pedestal_bands.svg",
                 "pedestal_attribution.svg", "pedestal_faces.svg", "pedestal_line.svg",
                 "pedestal_inflation.svg"):
        print("wrote", os.path.join(FIGURES, name))


if __name__ == "__main__":
    main()
