"""Every number and figure in `DOC_pedestal_correction.md`. (SPEC_capture_quality.md §16.15.6)

The document explains why the shipped Pigment Index reads systematically HIGH, how large the effect is,
and what a one-subtraction correction would do. This script produces the whole of it, from the SHIPPED
code paths (`settling_sweep.measure` -> `SpectrumFeatureUtil.linearBaselineCorrected`), so the document
cannot drift from what the app computes.

Prints, in the document's own order:
  1  the six sets, raw and baselined
  2  the straight-line test  B_Soret = M_inf*B_Q + k  -- whose INTERCEPT is the pedestal residual
  3  r_Q per oil, with standard errors
  4  the inflation table
  5  the correction applied, shared r_Q vs each oil's own  <- the document's honesty check
  6  how concentrated one would have to work to shrink the inflation instead

Writes two SVG figures into docs/figures/:
    pedestal_line.svg      the straight-line test, with the intercept that should not be there
    pedestal_inflation.svg inflation vs B_Q, with the six sets and the working window marked

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

from settling_sweep import measure

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.abspath(os.path.join(HERE, "..", "docs", "figures"))

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
    x = np.concatenate([column(runs, n, "A_Q linear") for n in names])
    y = np.concatenate([column(runs, n, "A_Soret linear") for n in names])
    return stats.linregress(x, y), x, y


def main():
    runs = load()
    oils = ["Kiendler", "Steirerkraft", "S-Budget"]

    # ------------------------------------------------------------------ 1 the six sets
    print("=== 1  THE SIX SETS — raw bands, baselined bands, and the shipped index")
    print("   %-16s %4s %9s %9s %10s %10s %10s %10s" % (
        "set", "n", "A_Sor raw", "A_Q raw", "turbidity", "B_Soret", "B_Q", "M shipped"))
    print("   " + "-" * 84)
    for name, _, paths in SETS:
        print("   %-16s %4d %9.4f %9.4f %10.4f %10.4f %10.4f %10.3f" % (
            name, len(paths),
            column(runs, name, "A_Soret raw").mean(), column(runs, name, "A_Q raw").mean(),
            column(runs, name, "A_near 520-540").mean(),
            column(runs, name, "A_Soret linear").mean(), column(runs, name, "A_Q linear").mean(),
            column(runs, name, "S/Q linear base").mean()))
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
    print("   %-16s %10s %14s %12s %12s" % ("set", "B_Q", "inflation", "M shipped", "M corrected"))
    print("   " + "-" * 68)
    for name, _, _ in SETS:
        bq = column(runs, name, "A_Q linear").mean()
        m = column(runs, name, "S/Q linear base").mean()
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
        bs = np.concatenate([column(runs, n, "A_Soret linear") for n in names])
        bq = np.concatenate([column(runs, n, "A_Q linear") for n in names])
        own = residual.get(oil, shared)
        summary[oil] = ((bs / (bq - shared)).mean(), (bs / (bq - own)).mean())
        print("   %-14s %22.3f %22.3f" % (oil, *summary[oil]))
    for index, label in ((0, "shared r_Q"), (1, "own r_Q  ")):
        gap = 100 * (summary["Kiendler"][index] / summary["Steirerkraft"][index] - 1)
        print("   Kiendler vs Steirerkraft, %s : %+.1f %%" % (label, gap))
    print("   ⇒ The ranking Edwin sees by eye SURVIVES only under the shared-r_Q assumption.")
    print()

    # ------------------------------------------------------------------ 6 the alternative
    print("=== 5  COULD ONE CONCENTRATE THE PROBLEM AWAY INSTEAD?")
    today = column(runs, "Kiendler C", "A_Q linear").mean()
    for target in (0.30, 0.20, 0.10, 0.05):
        need = abs(shared) / target
        print("   inflation <= %3.0f %%  needs B_Q >= %.4f  = %.1fx today's %.4f"
              % (100 * target, need, need / today, today))
    print()

    writeFigures(runs, residual, shared)


def writeFigures(runs, residual, shared):
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                         "svg.fonttype": "none"})

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
            axis.scatter(column(runs, name, "A_Q linear"), column(runs, name, "A_Soret linear"),
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
        bq = column(runs, name, "A_Q linear").mean()
        axis.scatter([bq], [100 * (-shared / bq)], s=34, c=COLOUR[oil], marker=MARKER[oil],
                     zorder=3, edgecolors="white", linewidths=0.6, label=oil
                     if name in ("Kiendler A", "Steirerkraft B", "S-Budget D") else None)
    dilute = column(runs, "Kiendler A", "A_Q linear").mean()
    axis.annotate("Kiendler A\nthe over-dilute preparation",
                  xy=(dilute, 100 * (-shared / dilute)), xytext=(16, -4),
                  textcoords="offset points", fontsize=7.6, color="#c0392b", va="center",
                  arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    cluster = np.array([column(runs, n, "A_Q linear").mean()
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

    for name in ("pedestal_line.svg", "pedestal_inflation.svg"):
        print("wrote", os.path.join(FIGURES, name))


if __name__ == "__main__":
    main()
