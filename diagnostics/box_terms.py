"""⭐ The THREE NUMBERS behind `V`, per fill — so the conditioning argument can be SEEN.

    V = (A_valley − A_Q) / A_Soret          (`SPEC_metric_research.md` §10, definition FROZEN)

This script does not compute a metric. It prints the ingredients and the candidate DENOMINATORS side
by side, because §10.2's claim — "`W` is the physics, `V` is the better-conditioned estimator of it" —
is a statement about denominators, and a table is the only way to feel it:

    V     divides by  A_Soret               a LEVEL, large, far from zero
    W     divides by  A_Soret − A_valley    a DIFFERENCE — buys exact offset-invariance, costs noise
    M448  divides by  B_Q                   a baseline-corrected level that approaches ZERO

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/box_terms.py
"""
import numpy as np

from box_metrics import (CONTEXT, PRIMARY, SHIPPED_CHORD, T_V, bandMeans, runsOf)
from settling_sweep import despikedAbsorption, asArrays, feature, plugin

# Every fill on the post-rebuild rig, oldest first. The 2026-08-07 block onward is the capillary
# recipe; the 07-29/07-31/08-01 block is the drop recipe.
FILLS = ([(label, name, count, cls) for label, name, count, cls in PRIMARY] +
         [(label, name, count, "") for label, name, count in CONTEXT])


def chordTerms(path):
    """B_Soret and B_Q — the shipped chord's own two band levels, for the denominator comparison."""
    lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), SHIPPED_CHORD))
    band = lambda lo, hi: float(values[(lam >= lo) & (lam <= hi)].mean())
    return band(448, 460), band(560, 580)


def termsOf(name, count):
    """Per-run terms, averaged over the fill, plus the sd of each column."""
    rows = []
    for path in runsOf(name, count):
        valley, q, soret = bandMeans(path)
        bSoret, bQ = chordTerms(path)
        rows.append((soret, valley, q, valley - q, valley / soret, soret - valley,
                     100.0 * (valley - q) / soret, (q - valley) / (soret - valley), bQ,
                     bSoret / bQ))
    return np.array(rows)


def main():
    print(__doc__.split("Run:")[0].strip())
    print()

    header = ("fill", "n", "A_Sor", "A_val", "A_Q", "val−Q", "u", "S−val", "V×100", "W", "B_Q", "M448")
    fmt = "   %-28s %2s %7s %7s %7s %7s %6s %7s %8s %6s %7s %7s"
    print("=" * 118)
    print("TABLE 1 — the ingredients, per fill (de-spiked RAW absorbance, no baseline)")
    print("=" * 118)
    print(fmt % header)
    print("   " + "-" * 113)

    table = {}
    for label, name, count, cls in FILLS:
        rows = table[label] = termsOf(name, count)
        m = rows.mean(axis=0)
        print(fmt % (label + ("*" if cls else ""), count,
                     "%.3f" % m[0], "%.3f" % m[1], "%.3f" % m[2], "%.3f" % m[3], "%.3f" % m[4],
                     "%.3f" % m[5], "%.2f" % m[6], "%.3f" % m[7], "%.4f" % m[8], "%.2f" % m[9]))
    print("   * = one of the 18 threshold-corpus runs.   u = A_valley/A_Soret.   "
          "S−val = A_Soret − A_valley.")

    print("\n" + "=" * 118)
    print("TABLE 2 — SPREAD ACROSS THE ARCHIVE: what each term does, and what each denominator costs")
    print("=" * 118)
    allRuns = np.concatenate([rows for rows in table.values()])
    names = ["A_Soret", "A_valley", "A_Q", "A_valley−A_Q", "u", "A_Soret−A_valley",
             "V×100", "W", "B_Q", "M448"]
    print("   %-20s %9s %9s %9s %9s %9s" %
          ("term", "min", "max", "mean", "sd", "sd/mean"))
    print("   " + "-" * 71)
    for i, name in enumerate(names):
        column = allRuns[:, i]
        print("   %-20s %9.4f %9.4f %9.4f %9.4f %8.1f %%" %
              (name, column.min(), column.max(), column.mean(), column.std(ddof=1),
               100 * abs(column.std(ddof=1) / column.mean())))

    print("\n" + "=" * 118)
    print("TABLE 3 — DENOMINATOR CONDITIONING: how close each denominator gets to ZERO, in units")
    print("           of its OWN run-to-run scatter (per fill: mean ÷ within-fill sd = 1/CV)")
    print("=" * 118)
    print("   %-34s %9s %11s %11s %26s" %
          ("denominator (metric)", "min value", "median σ→0", "worst σ→0", "worst fill"))
    print("   " + "-" * 96)
    for label, i in [("A_Soret            (V)", 0), ("A_Soret − A_valley (W)", 5),
                     ("B_Q                (M448)", 8)]:
        ratios = []
        for name, _, count, _ in [(l, n, c, x) for l, n, c, x in FILLS]:
            if count < 3:
                continue
            rows = table[name]
            ratios.append((abs(rows[:, i].mean() / rows[:, i].std(ddof=1)), name))
        ratios.sort()
        print("   %-34s %9.4f %10.1f σ %10.1f σ %26s" %
              (label, allRuns[:, i].min(), np.median([r for r, _ in ratios]),
               ratios[0][0], ratios[0][1]))
    print("\n   ⇒ a ratio's variance is dominated by the RELATIVE error of its denominator.")
    print("     Subtracting the valley to buy exact offset-invariance shrinks the denominator and")
    print("     injects the valley's own noise into it — that is the whole of W's extra spread.")

    print("\n" + "=" * 118)
    print("TABLE 4 — WITHIN-FILL REPEATABILITY of each term (sd as %% of that fill's own mean)")
    print("=" * 118)
    cols = [("A_Soret", 0), ("A_valley", 1), ("A_Q", 2), ("val−Q", 3), ("S−val", 5),
            ("V", 6), ("W", 7), ("B_Q", 8), ("M448", 9)]
    print("   %-28s %2s" % ("fill", "n") + "".join("%9s" % c for c, _ in cols))
    print("   " + "-" * 113)
    pooled = {c: [] for c, _ in cols}
    for label, name, count, cls in FILLS:
        rows = table[label]
        if count < 3:
            continue
        cvs = []
        for c, i in cols:
            cv = 100 * abs(rows[:, i].std(ddof=1) / rows[:, i].mean())
            pooled[c].append(cv)
            cvs.append(cv)
        print("   %-28s %2d" % (label, count) + "".join("%8.1f%%" % v for v in cvs))
    print("   " + "-" * 113)
    print("   %-28s   " % "MEDIAN within-fill CV" +
          "".join("%8.1f%%" % np.median(pooled[c]) for c, _ in cols))
    print("   ⇒ A_valley is the FLAKIEST of the three terms. V touches it once, in a difference "
          "where it\n     is dwarfed by A_Q. W touches it in the DENOMINATOR too — see Table 5.")

    print("\n" + "=" * 118)
    print("TABLE 5 — THE CONTROLLED PAIRS: where V and W part company, term by term")
    print("=" * 118)
    pairs = [("dose ±40 %  (Kiendler 6 → 7 drops)", "Kiendler A 6drop", "Kiendler C 7drop"),
             ("⛔ HALF concentration (Steirerkraft)", "Steirerkraft capillary",
              "Steirerkraft half-strength"),
             ("refill, same oil+recipe (Billa Clever)", "Billa Clever A", "Billa Clever B"),
             ("green → brown (Steirerkraft B → S-Budget D)", "Steirerkraft B", "S-Budget series D")]
    span = {"V": 4.50, "W": 0.051}   # native-sampling class span (§10.1a)
    for label, a, b in pairs:
        ma, mb = table[a].mean(axis=0), table[b].mean(axis=0)
        print("   %s" % label)
        print("      %-14s A_Sor %6.3f   u %5.3f   1/(1−u) %5.3f   V×100 %7.2f   W %6.3f" %
              (a, ma[0], ma[4], 1 / (1 - ma[4]), ma[6], ma[7]))
        print("      %-14s A_Sor %6.3f   u %5.3f   1/(1−u) %5.3f   V×100 %7.2f   W %6.3f" %
              (b, mb[0], mb[4], 1 / (1 - mb[4]), mb[6], mb[7]))
        print("      %-14s ΔA_Sor %5.0f %%  Δu %+5.1f %%           ΔV %6.2f = %4.1f %% of class span"
              "   ΔW = %4.1f %%" %
              ("⇒", 100 * (mb[0] / ma[0] - 1), 100 * (mb[4] / ma[4] - 1), abs(mb[6] - ma[6]),
               100 * abs(mb[6] - ma[6]) / span["V"], 100 * abs(mb[7] - ma[7]) / span["W"]))
    print("\n   ⇒ ⭐ 1/(1−u) is the ONLY difference between the two (W = −V/(1−u), exact). On the "
          "dose pair\n     u nearly DOUBLES for a 1.4× concentration change — and W moves with it "
          "while V does not.")

    print("\n" + "=" * 118)
    print("TABLE 6 — ⭐ RECONCILIATION: this script vs the SHIPPED PLUGIN, on every archived run")
    print("=" * 118)
    print("   SPEC_v_metric_integration.md §8 (T2b). NOT a unit test — the plugin suite is hermetic and")
    print("   `spectracs-references/tmp/` is scratch, so the real-data check lives here and is read by eye.")
    print("   ⛔ Any non-zero difference means the two have drifted apart on windows, de-spike or sampling.")
    worst, checked = 0.0, 0
    for label, name, count, cls in FILLS:
        for path in runsOf(name, count):
            terms = plugin._DevSpectralPlugin__vTerms(despikedAbsorption(path))
            valley, q, soret = bandMeans(path)
            difference = abs(terms[3] - 100.0 * (q - valley) / soret)
            worst, checked = max(worst, difference), checked + 1
    print("   %d runs checked   worst |plugin − script| = %.3e   ⇒ %s"
          % (checked, worst, "IDENTICAL" if worst < 1e-9 else "⛔ DRIFTED"))


if __name__ == "__main__":
    main()
