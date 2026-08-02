"""Green oil "Ulrich Kiendler" at THREE concentrations — the dilution-invariance test, done on purpose.

   (SPEC_capability_proof.md §11.4f F step 3 "green #2"; SPEC_capture_quality.md §16.10.8 / §16.14)

Edwin's session of 2026-08-01/02, one oil, one evening, three preparations:

    A  tmp/20260801A   18 ml alcohol + 6 drops                     6 runs   = the SHIPPED recipe
    B  tmp/20260801B   A's remaining 14 ml + 1 more drop, restirred 2 runs   = A enriched in place
    C  tmp/20260801C   fresh 18 ml + 7 drops                       2 runs

The design SHOULD have been the best dilution test on record — one oil, one evening, one rig state,
with B sharing A's entire lineage — and it is deliberately NON-MONOTONE (time order A < B < C but
concentration order A < C < B), so drift and dilution are separated rather than confounded.

⚠ IT IS NOT ONE, AND THE SCRIPT'S MAIN RESULT IS WHY. The Beer-Lambert control in section 3 fails
outright: a nominal 21 % concentration step moved the 520-540 turbidity anchor by 143 %. Set A's
turbidity is the lowest of the six post-rebuild sets compared here (0.038 against 0.09-0.13 for all
five others), and set A was still clarifying while it was being measured (section 3c).

⚠⚠ BUT DO NOT STOP THERE — Edwin's challenge, section 9. He observed that the more concentrated
preparations read LOWER, and that is true of every pair here; the nominal-concentration axis in fact
fits this session BETTER than turbidity does. The reason this script still refuses to report a
dilution slope is NOT that concentration is refuted — it is that the session contains effectively
ONE informative contrast (set A against the two stirred preps), in which concentration and turbidity
moved together. It cannot separate them, and the -0.59 magnitude is separately incompatible with the
archive's larger 1.5x spans. Section 9 gives the one-evening experiment that WOULD separate them.

What the session DOES establish: the oil is decisively green on every discriminator (section 6-7),
and two independently prepared fills agree to 2.3 % (section 5).

Oils, as Edwin names them (his own visual read, recorded per §11.4f D3's operator pre-read):
    Kiendler        this session's green    — Edwin: "a little bit greener than" Steirerkraft
    Steirerkraft    20270729B/C, green #1
    Spar S-Budget   20260731A, series D brown

Reported, in order:
  1  the concentration model, and how much the eyeballed volumes can move it
  2  the raw record, run by run, on one session clock
  3  Beer-Lambert control — do the ABSOLUTE band absorbances track concentration? (⚠ they do not)
  3b what actually moved — pigment against turbidity
  3c set A was still changing while it was measured
  4  the invariance test, kept only to SIZE the artefact
  5  precision: re-seat CV of set A, and the B-vs-C pair as a σ_fill probe
  6  the class verdict: this oil against green #1, against brown, against the shipped T = 10.6
  7  speciation — §16.13.9's parameter-free shape discriminator on the new oil
  8  the actionable number: residual turbidity sensitivity, and what it costs the campaign

Diagnostic only — nothing here is applied to the pipeline. Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/kiendler_dilution.py
"""
import os

import numpy as np
from scipy import stats

from settling_sweep import BASE, detrend, measure
from qband_shape import curves

SET_A = ["20260801A/%03d.pdf" % i for i in range(1, 7)]
SET_B = ["20260801B/%03d.pdf" % i for i in range(1, 3)]
SET_C = ["20260801C/%03d.pdf" % i for i in range(1, 3)]

GREEN1_B = ["20270729B/%03d.pdf" % i for i in range(1, 7)]   # STEIRERKRAFT, green #1, dilution 1
GREEN1_C = ["20270729C/%03d.pdf" % i for i in range(1, 7)]   # STEIRERKRAFT, green #1, dilution 2
BROWN = ["20260731A/%03d.pdf" % i for i in range(1, 7)]      # SPAR S-BUDGET, series D (§16.13)

SHIPPED = "S/Q linear base"
THRESHOLD = 10.6                                             # §16.10.17d, shipped
ARCHIVE_SLOPE, ARCHIVE_SLOPE_SE = 0.033, 0.029               # §16.14 pooled, dilution_pooled.py

# drops per ml. B: A's 14 ml carries 6*(14/18) drops, plus one more.
NOMINAL_A, NOMINAL_C = 18.0, 18.0
REMAINDER = 14.0
CONCENTRATION = {"A": 6.0 / NOMINAL_A,
                 "B": (6.0 * REMAINDER / NOMINAL_A + 1.0) / REMAINDER,
                 "C": 7.0 / NOMINAL_C}

SETS = [("A", SET_A), ("B", SET_B), ("C", SET_C)]


def elapsed(paths, origin):
    """Minutes since `origin`. File mtimes are the real capture times — every embedded workflow's
    header.timestampIso is None in these PDFs (§16.12.11)."""
    return np.array([(os.path.getmtime(BASE + p) - origin) / 60.0 for p in paths])


def logLogSlope(cLo, vLo, cHi, vHi):
    """(slope, standardError) of log(value) against log(concentration) for two groups of runs.

    s = 0 is perfect dilution invariance; s = 1 is proportional to concentration (Beer-Lambert)."""
    span = np.log(cHi / cLo)
    seLo = vLo.std(ddof=1) / np.sqrt(len(vLo)) / vLo.mean()
    seHi = vHi.std(ddof=1) / np.sqrt(len(vHi)) / vHi.mean()
    return np.log(vHi.mean() / vLo.mean()) / span, np.sqrt(seLo ** 2 + seHi ** 2) / span


def runLevelSlope(runs, metric):
    """Regress log(metric) on log(concentration) over all ten INDIVIDUAL runs.

    Treats every run as an independent draw, which is right for re-seat noise and optimistic for
    fill noise — so read it beside the pairwise slopes, not instead of them."""
    x, y = [], []
    for name, paths in SETS:
        for path in paths:
            x.append(np.log(CONCENTRATION[name]))
            y.append(np.log(runs[path][metric]))
    x, y = np.array(x), np.array(y)
    result = stats.linregress(x, y)
    return result.slope, result.stderr


def cvInterval(values):
    """(CV%, lowCV%, highCV%) — the chi-square 95 % interval, because small n estimates σ loosely."""
    n = len(values)
    cv = values.std(ddof=1) / abs(values.mean()) * 100.0
    lo = cv * np.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1))
    hi = cv * np.sqrt((n - 1) / stats.chi2.ppf(0.025, n - 1))
    return cv, lo, hi


def main():
    print(__doc__.split("The design SHOULD")[0].strip())
    print()

    everything = SET_A + SET_B + SET_C + GREEN1_B + GREEN1_C + BROWN
    runs = {p: measure(p) for p in everything}
    origin = min(os.path.getmtime(BASE + p) for p in SET_A + SET_B + SET_C)

    def values(paths, metric):
        return np.array([runs[p][metric] for p in paths])

    # ------------------------------------------------------------------ 1 the concentration model
    print("=== 1  THE CONCENTRATION MODEL")
    print("   %-3s %-38s %10s %9s" % ("set", "preparation", "drops/ml", "vs A"))
    print("   " + "-" * 64)
    recipes = {"A": "18 ml + 6 drops (shipped recipe)",
               "B": "A's remaining 14 ml + 1 drop",
               "C": "fresh 18 ml + 7 drops"}
    for name, _ in SETS:
        print("   %-3s %-38s %10.4f %8.3fx"
              % (name, recipes[name], CONCENTRATION[name], CONCENTRATION[name] / CONCENTRATION["A"]))
    print()
    print("   Robustness to the eyeballed volumes — the ratios barely move:")
    print("      C/A = 7/6 = 1.1667 EXACTLY, whatever '18 ml' really was, provided both pours matched.")
    print("      B/A = 1 + 3/V, where V is the remainder Edwin called 14 ml:")
    for remainder in (13.0, 14.0, 15.0):
        print("         V = %4.1f ml  ->  B/A = %.4f" % (remainder, 1.0 + 3.0 / remainder))
    print("      Drop VOLUME cancels everywhere — it appears in numerator and denominator alike.")
    print()

    # ------------------------------------------------------------------ 2 the raw record
    print("=== 2  THE RAW RECORD  (one session clock, minutes from A/001)")
    print("   %-3s %-8s %6s %8s %8s %8s %8s %9s %9s" % (
        "set", "run", "min", "A_Soret", "A_Q", "A_near", "A_far", "S/Q raw", "S/Q_lin"))
    print("   " + "-" * 74)
    for name, paths in SETS:
        for path, minute in zip(paths, elapsed(paths, origin)):
            r = runs[path]
            print("   %-3s %-8s %6.1f %8.3f %8.3f %8.3f %8.3f %9.3f %9.3f" % (
                name, os.path.basename(path), minute, r["A_Soret raw"], r["A_Q raw"],
                r["A_near 520-540"], r["A_far 600-630"], r["S/Q raw"], r[SHIPPED]))
        print()

    print("   set means +/- SD")
    print("   %-3s %8s %16s %16s %16s %16s" % ("set", "n", "A_Soret", "A_Q", "S/Q raw", "S/Q lin"))
    print("   " + "-" * 78)
    for name, paths in SETS:
        cells = []
        for metric in ("A_Soret raw", "A_Q raw", "S/Q raw", SHIPPED):
            v = values(paths, metric)
            cells.append("%8.3f+/-%-6.3f" % (v.mean(), v.std(ddof=1)))
        print("   %-3s %8d %16s %16s %16s %16s" % (name, len(paths), *cells))
    print()

    # ------------------------------------------------------------------ 3 Beer-Lambert control
    print("=== 3  BEER-LAMBERT CONTROL — do the ABSOLUTE absorbances follow the concentration?")
    print("   If the drop-counting model describes what is IN THE BEAM, every absolute band")
    print("   absorbance should have log-log slope ~ 1. This control decides whether section 4")
    print("   is measuring dilution at all. ⚠ IT FAILS — read section 3b before section 4.")
    print()
    print("   %-18s %9s %9s %9s %10s %14s" % (
        "quantity", "A mean", "B mean", "C mean", "B/A obs", "slope A->B"))
    print("   " + "-" * 74)
    for metric in ("A_Soret raw", "A_Q raw", "A_near 520-540", "A_far 600-630"):
        a, b, c = values(SET_A, metric), values(SET_B, metric), values(SET_C, metric)
        slope, se = logLogSlope(CONCENTRATION["A"], a, CONCENTRATION["B"], b)
        print("   %-18s %9.3f %9.3f %9.3f %9.3fx %7.2f +/-%.2f"
              % (metric, a.mean(), b.mean(), c.mean(), b.mean() / a.mean(), slope, se))
    print()
    print("   expected B/A under strict Beer-Lambert: %.3fx" % (CONCENTRATION["B"] / CONCENTRATION["A"]))
    print("   ⚠ Every slope is far above 1, and the two BASELINE-ANCHOR windows (A_near, A_far) —")
    print("     which carry the turbidity pedestal, not pigment — moved the MOST. A 21 % change in")
    print("     oil content cannot raise the 520-540 anchor by 143 %. The axis is not concentration.")
    print()

    # ------------------------------------------------------------------ 3b what actually moved
    print("=== 3b  WHAT ACTUALLY MOVED — pigment against turbidity")
    print("   A_Soret/A_Q LINEAR are pedestal-removed, so they track PIGMENT. The 520-540 anchor is")
    print("   oil-quiet, so it tracks the TURBIDITY pedestal (§16.13: 52-61 % of raw A_Q).")
    print()
    print("   %-24s %5s %11s %10s %11s %10s" % (
        "set", "n", "A_Sor lin", "A_Q lin", "turbidity", "S/Q lin"))
    print("   " + "-" * 76)
    context = [("Kiendler A  18ml+6drp", SET_A), ("Kiendler B  14ml+1drp", SET_B),
               ("Kiendler C  18ml+7drp", SET_C), ("green #1 B  20270729B", GREEN1_B),
               ("green #1 C  20270729C", GREEN1_C), ("brown D     20260731A", BROWN)]
    for label, paths in context:
        print("   %-24s %5d %11.4f %10.4f %11.4f %10.3f"
              % (label, len(paths), values(paths, "A_Soret linear").mean(),
                 values(paths, "A_Q linear").mean(), values(paths, "A_near 520-540").mean(),
                 values(paths, SHIPPED).mean()))
    print()
    print("   ⇒ Kiendler A's turbidity is the lowest of the six post-rebuild sets above — the other")
    print("     five sit at 0.09-0.13, set A at 0.038. Set A is the anomaly, not B and C.")
    print()
    print("   ratios vs set A          nominal    A_Sor lin   A_Q lin   turbidity")
    print("   " + "-" * 66)
    for name, paths in (("B", SET_B), ("C", SET_C)):
        nominal = CONCENTRATION[name] / CONCENTRATION["A"]
        cells = [values(paths, m).mean() / values(SET_A, m).mean()
                 for m in ("A_Soret linear", "A_Q linear", "A_near 520-540")]
        print("   set %-20s %7.3fx %10.3fx %9.3fx %10.3fx" % (name, nominal, *cells))
    print()
    print("   Pigment moved ~1.3-1.5x against a nominal 1.17-1.21x — close-ish. TURBIDITY moved")
    print("   2.4-2.7x. The three preparations differ chiefly in SUSPENSION STATE.")
    print()

    # ------------------------------------------------------------------ 3c the sample was changing
    print("=== 3c  SET A WAS STILL CHANGING WHILE IT WAS MEASURED")
    times = elapsed(SET_A, origin)
    print("   %-18s %9s %9s %9s %9s" % ("quantity", "first", "last", "trend%", "t"))
    print("   " + "-" * 60)
    for metric in ("A_Soret raw", "A_Q raw", "A_near 520-540", "A_Soret linear", SHIPPED):
        v = values(SET_A, metric)
        _, _, trend, t = detrend(times, v)
        print("   %-18s %9.4f %9.4f %+8.1f%% %9.2f" % (metric, v[0], v[-1], trend, t))
    print("   (4 df: |t| > 2.78 is p < 0.05. The pigment and the pedestal are BOTH draining away.)")
    print()
    print("   ⇒ Mechanism, offered as INTERPRETATION not measurement: the oil is suspended rather")
    print("     than dissolved, and set A's stock separated — the beam saw a depleted, clarified")
    print("     layer that kept clarifying. B was RESTIRRED and C was FRESH, both read promptly.")
    print()

    # ------------------------------------------------------------------ 4 the invariance test
    print("=== 4  THE INVARIANCE TEST — does the shipped ratio hold still?")
    print("   s = 0 is perfect dilution invariance. s = 1 would mean the ratio tracks concentration.")
    print("   ⚠ VOID AS A DILUTION MEASUREMENT. Section 3 refuted the concentration axis, so every")
    print("     slope below is a SUSPENSION-STATE slope wearing a concentration label. It is kept")
    print("     because it sizes the artefact — NOT to be pooled with §16.14's archive figure.")
    print()
    for metric in ("S/Q raw", SHIPPED):
        print("   %s" % metric)
        print("      %-14s %8s %9s %9s %9s %16s" % (
            "pair", "span", "lo mean", "hi mean", "change", "slope s"))
        print("      " + "-" * 68)
        pairs = [("A -> B", "A", "B"), ("A -> C", "A", "C"), ("C -> B", "C", "B")]
        for label, loName, hiName in pairs:
            lo = values(dict(SETS)[loName], metric)
            hi = values(dict(SETS)[hiName], metric)
            span = CONCENTRATION[hiName] / CONCENTRATION[loName]
            slope, se = logLogSlope(CONCENTRATION[loName], lo, CONCENTRATION[hiName], hi)
            print("      %-14s %7.3fx %9.3f %9.3f %+8.1f%% %8.2f +/- %.2f"
                  % (label, span, lo.mean(), hi.mean(), 100 * (hi.mean() / lo.mean() - 1), slope, se))
        slope, se = runLevelSlope(runs, metric)
        print("      %-14s %7s %9s %9s %9s %8.2f +/- %.2f   <- all 10 runs"
              % ("run-level fit", "", "", "", "", slope, se))
        print("      95%% CI on s: %+.2f .. %+.2f" % (slope - 1.96 * se, slope + 1.96 * se))
        print()
    print("   archive comparison (§16.14, dilution_pooled.py): s = %+.3f +/- %.3f"
          % (ARCHIVE_SLOPE, ARCHIVE_SLOPE_SE))
    print()
    print("   TIME vs CONCENTRATION — the design separates them (see header note 2):")
    print("      time order       A < B < C   (C is last, ~70 min after A/001)")
    print("      concentration    A < C < B   (B is the strongest)")
    for metric in ("S/Q raw", SHIPPED):
        b, c = values(SET_B, metric).mean(), values(SET_C, metric).mean()
        verdict = "CONCENTRATION ordering" if b > c else "TIME ordering"
        print("      %-16s B = %7.3f, C = %7.3f  ->  B %s C, i.e. %s"
              % (metric, b, c, ">" if b > c else "<", verdict))
    print()

    # ------------------------------------------------------------------ 5 precision
    print("=== 5  PRECISION")
    times = elapsed(SET_A, origin)
    print("   set A, 6 re-seats of one fill — the directly comparable figure to series B/C/D")
    print("      %-18s %9s %9s %9s %9s %20s" % (
        "metric", "mean", "raw CV%", "resid CV%", "trend%", "95% CI on CV%"))
    print("      " + "-" * 80)
    for metric in ("S/Q raw", SHIPPED, "A_Soret raw", "A_Q raw"):
        v = values(SET_A, metric)
        rawCv, residCv, trend, t = detrend(times, v)
        cv, lo, hi = cvInterval(v)
        print("      %-18s %9.3f %9.2f %9.2f %+8.1f%% %9.2f .. %-8.2f (t=%.2f)"
              % (metric, v.mean(), rawCv, residCv, trend, lo, hi, t))
    print("      (t: 4 df, so |t| > 2.78 is p < 0.05 two-sided)")
    print()
    print("   reference sets, same metric %s:" % SHIPPED)
    for label, paths in (("green #1 B  20270729B", GREEN1_B), ("green #1 C  20270729C", GREEN1_C),
                         ("brown D     20260731A", BROWN)):
        v = values(paths, SHIPPED)
        cv, lo, hi = cvInterval(v)
        print("      %-24s n=%d  mean %7.3f  CV %5.2f%%  (95%% CI %.2f .. %.2f)"
              % (label, len(v), v.mean(), cv, lo, hi))
    print()
    print("   B vs C — a sigma_fill probe: INDEPENDENT preparations only %.3fx apart in concentration,"
          % (CONCENTRATION["B"] / CONCENTRATION["C"]))
    print("   so with s ~ 0 the concentration difference is negligible and the gap is nearly pure prep.")
    for metric in ("S/Q raw", SHIPPED):
        b, c = values(SET_B, metric), values(SET_C, metric)
        gap = 100 * (b.mean() / c.mean() - 1)
        pooledSd = np.sqrt((b.var(ddof=1) + c.var(ddof=1)) / 2)
        print("      %-18s B %7.3f   C %7.3f   gap %+6.2f%%   pooled within-set SD %.3f (%.2f%%)"
              % (metric, b.mean(), c.mean(), gap, pooledSd, 100 * pooledSd / c.mean()))
    print("      NOTE df = 1. This FALSIFIES or fails to falsify; it does not estimate sigma_fill.")
    print()

    # ------------------------------------------------------------------ 6 the class verdict
    print("=== 6  THE CLASS VERDICT  (§11.4f F/D2's pre-registered predictions)")
    allKiendler = np.concatenate([values(paths, SHIPPED) for _, paths in SETS])
    green1 = np.concatenate([values(GREEN1_B, SHIPPED), values(GREEN1_C, SHIPPED)])
    brown = values(BROWN, SHIPPED)
    print("   Kiendler (green #2), all %d runs   %7.3f +/- %.3f" % (
        len(allKiendler), allKiendler.mean(), allKiendler.std(ddof=1)))
    print("   green #1, B + C, 12 runs           %7.3f +/- %.3f" % (green1.mean(), green1.std(ddof=1)))
    print("   brown series D, 6 runs             %7.3f +/- %.3f" % (brown.mean(), brown.std(ddof=1)))
    print()
    print("   PREDICTION 'green #2 within 10 % of green #1' — ⚠ NOT DECIDABLE AS WRITTEN.")
    print("   §11.4f D2 fixed a threshold but never named the ESTIMATOR, and the three defensible")
    print("   choices straddle it. Recording all three rather than picking one after the fact:")
    setMeans = np.array([values(paths, SHIPPED).mean() for _, paths in SETS])
    green1SetMeans = np.array([values(GREEN1_B, SHIPPED).mean(), values(GREEN1_C, SHIPPED).mean()])
    readings = [("all runs pooled", allKiendler.mean(), green1.mean()),
                ("mean of set means", setMeans.mean(), green1SetMeans.mean()),
                ("properly-stirred fills B+C only",
                 np.concatenate([values(SET_B, SHIPPED), values(SET_C, SHIPPED)]).mean(),
                 green1.mean())]
    for label, kiendlerMean, referenceMean in readings:
        delta = 100 * (kiendlerMean / referenceMean - 1)
        print("      %-34s %7.3f vs %7.3f  = %+5.1f %%  -> %s"
              % (label, kiendlerMean, referenceMean, delta, "PASS" if abs(delta) <= 10 else "FAIL"))
    print("      ⇒ VERDICT: UNDECIDED. The lesson is for the pre-registration format, not the oil —")
    print("        a threshold without an estimator is not a pre-registration (§16.10.16).")
    print("   PREDICTION 'no oil crosses T = 10.6 against Edwin's read':")
    for name, paths in SETS:
        v = values(paths, SHIPPED)
        sd = values(SET_A, SHIPPED).std(ddof=1)                    # set A's re-seat SD, the honest one
        print("      set %s  mean %7.3f  ->  %-6s   margin %+6.2f = %+5.1f sigma_reseat"
              % (name, v.mean(), "GREEN" if v.mean() > THRESHOLD else "BROWN",
                 v.mean() - THRESHOLD, (v.mean() - THRESHOLD) / sd))
    print()
    pooledSd = np.sqrt((allKiendler.var(ddof=1) + brown.var(ddof=1)) / 2)
    d = (allKiendler.mean() - brown.mean()) / pooledSd
    print("   Kiendler vs brown D:  gap %+.3f, Cohen's d = %.2f" % (allKiendler.mean() - brown.mean(), d))
    print()

    # ------------------------------------------------------------------ 7 speciation
    print("=== 7  SPECIATION — §16.13.9's parameter-free shape discriminator")
    print("   rise / Q-amplitude is a ratio of two features INSIDE the Q region, so a single")
    print("   concentration factor cancels exactly. It should be blind to A/B/C by construction.")
    print()
    print("   %-26s %8s %10s %12s %14s" % ("set", "n", "rise", "Q amp", "rise/Q amp"))
    print("   " + "-" * 74)
    groups = [("Kiendler A", SET_A), ("Kiendler B", SET_B), ("Kiendler C", SET_C),
              ("green #1  20270729C", GREEN1_C), ("brown D   20260731A", BROWN)]
    shapes = {}
    for label, paths in groups:
        lam, stack = curves(paths)

        def band(lo, hi):
            return stack[:, (lam >= lo) & (lam <= hi)].mean(axis=1)

        rise = band(620, 630) - band(600, 610)
        amplitude = band(571, 573) - band(549, 551)
        ratio = rise / amplitude
        shapes[label] = ratio
        print("   %-26s %8d %10.4f %12.4f %9.4f+/-%.4f"
              % (label, len(paths), rise.mean(), amplitude.mean(), ratio.mean(), ratio.std(ddof=1)))
    print()
    kiendler = np.concatenate([shapes["Kiendler A"], shapes["Kiendler B"], shapes["Kiendler C"]])
    brownShape = shapes["brown D   20260731A"]
    pooledSd = np.sqrt((kiendler.var(ddof=1) + brownShape.var(ddof=1)) / 2)
    print("   Kiendler (all 10) %.4f +/- %.4f   vs brown %.4f +/- %.4f   ->  d = %.2f"
          % (kiendler.mean(), kiendler.std(ddof=1), brownShape.mean(), brownShape.std(ddof=1),
             (kiendler.mean() - brownShape.mean()) / pooledSd))
    print("   (§16.13.9 measured d = 10.26 for green #1 vs brown on this quantity)")
    print()
    x = np.concatenate([np.full(len(shapes["Kiendler " + n]), np.log(CONCENTRATION[n]))
                        for n in ("A", "B", "C")])
    result = stats.linregress(x, np.log(kiendler))
    print("   dilution slope of rise/Q amp across A/B/C:  s = %+.2f +/- %.2f  (expect 0 by construction)"
          % (result.slope, result.stderr))
    print()

    # ------------------------------------------------------------------ 8 the residual sensitivity
    print("=== 8  ⭐ THE ACTIONABLE NUMBER — residual turbidity sensitivity of the shipped metric")
    print("   The linear baseline exists to null the turbidity pedestal. It does not fully succeed.")
    print("   Regressing log(S/Q lin) on log(turbidity) across this oil's three preparations:")
    print()
    turbidity = np.concatenate([values(paths, "A_near 520-540") for _, paths in SETS])
    ratio = np.concatenate([values(paths, SHIPPED) for _, paths in SETS])
    across = stats.linregress(np.log(turbidity), np.log(ratio))
    print("      ACROSS preparations (10 runs, turbidity spans %.2fx):  slope %+.3f +/- %.3f"
          % (turbidity.max() / turbidity.min(), across.slope, across.stderr))
    within = stats.linregress(np.log(values(SET_A, "A_near 520-540")), np.log(values(SET_A, SHIPPED)))
    print("      WITHIN set A as it clarified (6 runs, spans %.2fx):    slope %+.3f +/- %.3f"
          % (values(SET_A, "A_near 520-540").max() / values(SET_A, "A_near 520-540").min(),
             within.slope, within.stderr))
    print()
    print("   ⇒ Within one liquid the metric is nearly immune (pigment and pedestal fall together).")
    print("     ACROSS preparations it is not: a %.1fx turbidity difference moved the verdict number"
          % (values(SET_B, "A_near 520-540").mean() / values(SET_A, "A_near 520-540").mean()))
    print("     by %+.1f %%. Harmless for an oil %.1f sigma clear of T; decisive for a borderline one."
          % (100 * (values(SET_B, SHIPPED).mean() / values(SET_A, SHIPPED).mean() - 1),
             (allKiendler.mean() - THRESHOLD) / values(SET_A, SHIPPED).std(ddof=1)))
    print()
    print("   ⇒ PROTOCOL CONSEQUENCE: stir-to-measure latency is now the largest UNCONTROLLED")
    print("     variable in the four-oil campaign, and turbidity (A@520-540) should be logged with")
    print("     every run as a QC covariate — it is free, it is already computed, and set A would")
    print("     have been flagged by it BEFORE the ratio was ever looked at.")
    print()

    # ------------------------------------------------------------------ 9 Edwin's challenge
    print("=== 9  ⭐ EDWIN'S CHALLENGE — 'the stronger preps read LOWER, so is it dilution?'")
    print("   The observation is correct on every pair here. This section tests it honestly rather")
    print("   than assuming section 3b's answer. A power law must give the SAME slope on every pair.")
    print()
    print("   %-10s %12s %12s %12s %12s" % ("pair", "nominal c", "pigment S", "pigment Q", "turbidity"))
    print("   " + "-" * 62)
    axesOf = {"nominal c": lambda n: CONCENTRATION[n],
              "pigment S": lambda n: values(dict(SETS)[n], "A_Soret linear").mean(),
              "pigment Q": lambda n: values(dict(SETS)[n], "A_Q linear").mean(),
              "turbidity": lambda n: values(dict(SETS)[n], "A_near 520-540").mean()}
    collected = {key: [] for key in axesOf}
    for loName, hiName in (("A", "B"), ("A", "C"), ("C", "B")):
        change = np.log(values(dict(SETS)[hiName], SHIPPED).mean()
                        / values(dict(SETS)[loName], SHIPPED).mean())
        cells = []
        for key, axis in axesOf.items():
            span = np.log(axis(hiName) / axis(loName))
            slope = change / span if abs(span) > 1e-3 else float("nan")
            collected[key].append(slope)
            cells.append(slope)
        print("   %-10s %12.2f %12.2f %12.2f %12.2f" % ("%s -> %s" % (loName, hiName), *cells))
    print()
    for key, slopes in collected.items():
        finite = np.array([s for s in slopes if np.isfinite(s)])
        print("      %-11s spread %.2f   %s" % (key, finite.max() - finite.min(),
              "CONSISTENT" if finite.max() - finite.min() < 0.3 else "inconsistent"))
    print()
    print("   ⚠ READ THIS BEFORE CONCLUDING. The nominal axis wins that comparison partly by")
    print("     CONSTRUCTION: it is exact arithmetic with no measurement noise, while every")
    print("     measured axis divides a noisy change by a noisy span — and C->B's span is tiny,")
    print("     so its measured slopes explode. Only the two A-pairs carry real leverage, and")
    print("     A->B and A->C are nearly the SAME comparison (set A against the two stirred preps).")
    print("     ⇒ This session contains effectively ONE informative contrast, and in it")
    print("       concentration and turbidity moved TOGETHER. It cannot separate them.")
    print()
    print("   What CAN be settled — how depleted set A actually was, measured four ways:")
    for name in ("B", "C"):
        for key in ("A_Soret linear", "A_Q linear"):
            effective = ((CONCENTRATION[name] / CONCENTRATION["A"])
                         / (values(dict(SETS)[name], key).mean() / values(SET_A, key).mean()))
            print("      vs set %s on %-16s set A sat at %3.0f %% of its nominal concentration"
                  % (name, key, 100 * effective))
    print("      ⇒ 8-21 % depleted, NOT the ~53 % that would be needed to reconcile s = -0.59")
    print("        with the archive. Correcting for it moves s to about -0.23 .. -0.42, not to 0.")
    print()
    print("   And why -0.59 cannot be a dilution law on its own — the archive spans are LARGER,")
    print("   where a power law would be far more visible:")
    for span, measured in ((1.50, "+0.4 %  green K/L"), (1.50, "+4.9 %  brown N/M"),
                           (1.167, "-1.9 %  green B/C (Steirerkraft)")):
        print("      at %.3fx   s = -0.59 predicts %+6.1f %%   |   archive measured %s"
              % (span, 100 * (span ** -0.59 - 1), measured))
    print()
    print("   ⇒ HONEST VERDICT: a real, MILD negative dilution dependence is now supported by two")
    print("     oils (Steirerkraft -0.12 +/- 0.11, and this session's sign). The -0.59 magnitude is")
    print("     not credible as a dilution law. Something set-A-specific carries most of the 10 %,")
    print("     and turbidity is the only other measured axis large enough — but unproven here.")
    print()
    print("   ⇒ THE DECIDING EXPERIMENT (one evening): repeat set A's recipe, 18 ml + 6 drops,")
    print("     read IMMEDIATELY after stirring. Same concentration as A, same turbidity as B/C.")
    print("        lands near 12.9 (with B/C)  -> turbidity did it, dilution is fine")
    print("        lands near 14.3 (with A)    -> concentration did it, s is real and large")
    print("     Nothing else in the queue separates these two, and the answer changes the protocol.")
    print()

    # ------------------------------------------------------------------ 10 the reconciliation
    print("=== 10  ⭐ THE RECONCILIATION — §16.14's pedestal curvature makes both readings ONE")
    print("   §16.14.4-6 already derived that the pedestal's departure from its own best-fit line,")
    print("   r_Q, produces a metric error r_Q/B_Q — which is CONCENTRATION-DEPENDENT (∝ 1/c).")
    print("   So 'it is turbidity' and 'it is dilution-dependent' are not rival explanations:")
    print("   they are the same mechanism seen from two sides. Turbidity sets r_Q; concentration")
    print("   sets B_Q; the bias is their ratio, and set A had the SMALLEST B_Q of any set here.")
    print()
    print("   The model in directly measurable form — no fitted concentration axis at all:")
    print("      B_Soret = M_inf * B_Q + (r_S - M_inf * r_Q)")
    print("   i.e. plot the baselined Soret against the baselined Q band. With no pedestal")
    print("   residual the line passes through the ORIGIN. The intercept IS the residual.")
    print()
    print("   %-14s %4s %18s %20s %10s" % ("oil", "n", "M_inf (slope)", "intercept", "t(icpt)"))
    print("   " + "-" * 72)
    fits = {}
    for oil, groups in (("Kiendler", (SET_A, SET_B, SET_C)),
                        ("Steirerkraft", (GREEN1_B, GREEN1_C))):
        x = np.concatenate([values(g, "A_Q linear") for g in groups])
        y = np.concatenate([values(g, "A_Soret linear") for g in groups])
        fit = stats.linregress(x, y)
        fits[oil] = fit
        print("   %-14s %4d %9.3f +/- %-5.3f %10.4f +/- %-7.4f %9.2f"
              % (oil, len(x), fit.slope, fit.stderr, fit.intercept, fit.intercept_stderr,
                 fit.intercept / fit.intercept_stderr))
    print()
    for oil, fit in fits.items():
        residual = -fit.intercept / fit.slope
        se = abs(residual) * np.sqrt((fit.intercept_stderr / fit.intercept) ** 2
                                     + (fit.stderr / fit.slope) ** 2)
        print("      %-14s r_Q = %+.4f +/- %.4f A" % (oil, residual, se))
    print("      %-14s |r_Q| <~ 0.0080 A   (§16.14.7's bound from the pooled archive)" % "archive")
    print()
    print("   ⇒ Two independent oils give the SAME residual (-0.025 and -0.021 A) and the same")
    print("     M_inf. Kiendler's intercept is 7 sigma from zero. The model works — but the")
    print("     residual is ~3x the archive's bound, so §16.14.7's |r_Q| <~ 0.008 A is too tight.")
    print()
    print("   ⚠ TWO CAUTIONS, both load-bearing:")
    print("     1  B_Soret and B_Q come from the same spectrum, so common-mode noise inflates the")
    print("        slope somewhat. The INTERCEPT is the claim, and it survives at t = 7.")
    print("     2  Steirerkraft's B_Q span is narrow, so its fit is weak (t = 1.13). The agreement")
    print("        of the two point estimates is the evidence, not either fit alone.")
    print()
    print("   ⭐ AND THE UNCOMFORTABLE COROLLARY — the shipped threshold lives on the INFLATED scale:")
    print("      pedestal-free M_inf:  Kiendler %.2f +/- %.2f   Steirerkraft %.2f +/- %.2f"
          % (fits["Kiendler"].slope, fits["Kiendler"].stderr,
             fits["Steirerkraft"].slope, fits["Steirerkraft"].stderr))
    print("      shipped threshold:    T = %.1f  — ABOVE BOTH." % THRESHOLD)
    print("      Remove the pedestal entirely and both GREEN oils fall BELOW T. T = 10.6 is")
    print("      therefore not a pigment-intrinsic constant: it is calibrated on pedestal-inflated")
    print("      numbers and is tied to the current recipe and turbidity regime. It must be")
    print("      RE-DERIVED, not carried over, if the prep ever gets cleaner (filter, solvent).")
    print()
    print("      Note also that on the pedestal-free scale the two green oils are INDISTINGUISHABLE")
    print("      (%.2f vs %.2f, overlapping errors) although their measured M differs by %.1f %%."
          % (fits["Kiendler"].slope, fits["Steirerkraft"].slope,
             100 * (allKiendler.mean() / green1.mean() - 1)))
    print("      So Edwin's 'Kiendler is greener' may be a pedestal difference rather than a")
    print("      pigment difference. Steirerkraft's error bar is too wide to tell. OPEN.")


if __name__ == "__main__":
    main()
