"""Every archived run that can carry a 2nd derivative at 624 nm, in one figure. (Edwin, 2026-08-25)

⛔ WHY ONLY 44. A 2nd derivative at 624 nm needs the band's FAR FLANK, so the trace must reach past
632 nm. The archive's 629.8 nm epoch cannot supply that at all -- which is the standing limitation of
`d2R` as a metric and the reason this figure is smaller than the corpus.

    d2R = D2(624) / D2(568),  both taken as the MINIMUM of the 2nd derivative inside a PINNED window.

⛔⛔ THE WINDOWS ARE PINNED, NOT SEARCHED, and that is load-bearing. Two INSTRUMENT features sit inside
the Q region: the 581 nm reference minimum (`DOC_lamp_rebuild.md` section 326) and the 609 nm Bayer
crossover (section 6 of the same). Searching 560-582 for "the 568 dip" lands on the 581 artefact in 5 of
9 sunflower runs. Hence 565-573 and 621-627, both clear of both artefacts.

Writes  spectracs-references/tmp/20260825_d2r_all_runs.pdf

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/d2r_all_runs.py
"""
import os
import sys
import tempfile

import numpy
import matplotlib
matplotlib.use("Agg")
from scipy.signal import savgol_filter
import matplotlib.pyplot as pyplot
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import all_metrics_archive as metrics
from solvent_colour_separation import SUNFLOWER as INDEX_MATCHED

GRID = numpy.arange(500.0, 634.01, 0.25)
SMOOTH_NM = 7.0
RED_WINDOW = (621.0, 627.0)
Q_WINDOW = (565.0, 573.0)
CUT = 1.0
OUT = os.path.join(archive.ARCHIVE, "20260825_d2r_all_runs.pdf")

# ⭐ The archive's series names are not oil names, and the SAME oil appears under several of them.
# Without this the by-solvent panel cannot line Lugitsch in isopropanol up against Lugitsch in sunflower.
SERIESOIL = {"20260812BillJaNatuerlich": "Ja Natuerlich",
             "20260812_BillaClever": "Billa Clever", "20260812_BillaCleverB": "Billa Clever",
             "20280819BillaClever": "Billa Clever",
             "20260814_Lugitsch_A": "Lugitsch", "20260817LigitschA": "Lugitsch"}

TODAY = {"20260824Lugitsch": ("Lugitsch", "green"), "20260824SparPremium": ("Spar Premium", "brown"),
         "20260824SparSBudget": ("Spar S-Budget", "brown")}
CLASSCOLOR = {"green": "#2e7d32", "brown": "#8b4513"}
SOLVENTMARK = {"isopropanol": "o", "sunflower": "s", "spirit": "^"}


def secondDerivative(nm, absorbance):
    y = numpy.interp(GRID, nm, absorbance)
    width = int(SMOOTH_NM / 0.25)
    width += (width + 1) % 2
    return savgol_filter(y, width, 3, deriv=2, delta=0.25)


def dipIn(d2, low, high):
    inside = (GRID >= low) & (GRID <= high)
    return float(d2[inside].min())


def collect():
    indexed = {relative for _, relative in INDEX_MATCHED}
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        def take(relative, label, oil, solvent):
            workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
            if workflow is None:
                return
            trace = archive.despikedTrace(workflow)
            if trace is None:
                return
            nm, absorbance = trace
            if nm[-1] < 632.0:                     # no far flank -> no 2nd derivative at 624
                return
            d2 = secondDerivative(nm, absorbance)
            def bandMean(low, high):
                inside = absorbance[(nm >= low) & (nm <= high)]
                return float(inside.mean())
            valley = bandMean(500.0, 560.0)
            qBand = bandMean(565.0, 580.0)
            rows.append({"run": relative, "class": label, "oil": oil, "solvent": solvent, "d2": d2,
                         "d2R": dipIn(d2, *RED_WINDOW) / dipIn(d2, *Q_WINDOW),
                         "Rv": 100.0 * (bandMean(622.0, 627.0) - valley) / (qBand - valley)})

        for label, relative in INDEX_MATCHED:
            series = relative.split("/")[0]
            oil = "Lugitsch" if "ugitsch" in series else "Billa Clever"
            take(relative, label, oil, "spirit" if series.startswith("20260821") else "sunflower")

        for folder, name in archive.walkReports():
            series = os.path.relpath(folder, archive.ARCHIVE)
            series = "(root)" if series == "." else series
            key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
            relative = os.path.relpath(os.path.join(folder, name), archive.ARCHIVE)
            if relative in indexed:
                continue
            label = archive.classOf({"series": series, "run": key})
            if label not in ("green", "brown"):
                continue
            take(relative, label, SERIESOIL.get(series, metrics.OILS.get(series, series)), "isopropanol")

        for series, (oil, label) in TODAY.items():
            for run in ("001", "002", "003"):
                take("%s/%s.pdf" % (series, run), label, oil, "sunflower")
    return rows


def shortLabel(row):
    """`series run` plus the oil name only when it adds something the series name does not."""
    series, name = row["run"].rsplit("/", 1)
    series = series.replace("_", "")
    run = name[:-4]
    if len(run) > 4:                       # the newchips-style long file names
        run = run[:4]
    oil = row["oil"]
    if oil.lower().replace(" ", "").replace("-", "").replace("_", "") in series.lower():
        oil = ""
    label = "%s %s" % (series[:23], run)
    return "%-28s %s" % (label, oil[:13])


def pageStrip(pdf, rows):
    """One row per run, sorted by d2R. 44 rows fits an A4 portrait at 7 pt."""
    ordered = sorted(rows, key=lambda r: -r["d2R"])
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("d2R = D2(624) / D2(568) — every archived run that reaches 632 nm",
                    fontsize=13, fontweight="bold", y=0.975)
    figure.text(0.5, 0.952,
                "2nd derivative, Savitzky–Golay 7 nm / polyorder 3 on a 0.25 nm grid.  "
                "Minima taken in PINNED windows 621–627 and 565–573 nm.",
                ha="center", fontsize=8.5, style="italic")
    axes = figure.add_axes([0.30, 0.055, 0.66, 0.885])
    positions = numpy.arange(len(ordered))
    for position, row in zip(positions, ordered):
        axes.plot(row["d2R"], position, SOLVENTMARK[row["solvent"]],
                  color=CLASSCOLOR[row["class"]], ms=6, markeredgecolor="black", markeredgewidth=0.4)
    axes.axvline(CUT, color="crimson", lw=1.4, ls="--")
    axes.set_yticks(positions)
    axes.set_yticklabels([shortLabel(r) for r in ordered], fontsize=6.2, family="monospace")
    for tick, row in zip(axes.get_yticklabels(), ordered):
        tick.set_color(CLASSCOLOR[row["class"]])
    axes.set_ylim(-1, len(ordered))
    axes.set_xlim(0, max(r["d2R"] for r in ordered) * 1.08)
    axes.invert_yaxis()
    axes.set_xlabel("d2R", fontsize=10, fontweight="bold")
    axes.grid(axis="x", alpha=0.3)
    axes.tick_params(axis="x", labelsize=8)
    green = [r["d2R"] for r in rows if r["class"] == "green"]
    brown = [r["d2R"] for r in rows if r["class"] == "brown"]
    axes.text(CUT + 0.05, len(ordered) - 1.5,
              "cut %.2f\ngreen ≥ %.2f\nbrown ≤ %.2f\n%d / %d errors"
              % (CUT, min(green), max(brown), sum(1 for r in rows
                 if (r["class"] == "green") != (r["d2R"] > CUT)), len(rows)),
              fontsize=8, color="crimson", va="bottom")
    handles = [pyplot.Line2D([], [], ls="", marker="o", color=CLASSCOLOR[c], ms=7,
                             markeredgecolor="black", label=c) for c in ("green", "brown")]
    handles += [pyplot.Line2D([], [], ls="", marker=m, color="#666666", ms=7,
                              markeredgecolor="black", label=s)
                for s, m in SOLVENTMARK.items()]
    axes.legend(handles=handles, fontsize=7.5, loc="lower right", ncol=2, framealpha=0.95)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageCurves(pdf, rows):
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("The 44 second-derivative traces themselves", fontsize=13, fontweight="bold", y=0.975)
    for index, (title, low, high, ylim) in enumerate([
            ("all 44, 540–634 nm", 540, 634, (-0.030, 0.018)),
            ("the 624 band only — the numerator", 614, 634, (-0.014, 0.006)),
            ("the 568 band only — the denominator", 556, 582, (-0.014, 0.006))]):
        axes = figure.add_axes([0.13, 0.700 - index * 0.275, 0.83, 0.185])
        for row in rows:
            axes.plot(GRID, row["d2"], "-", color=CLASSCOLOR[row["class"]], lw=0.7, alpha=0.75)
        axes.axhline(0.0, color="#444444", lw=0.8)
        axes.axvspan(*RED_WINDOW, color="#cc6666", alpha=0.28, lw=0)
        axes.axvspan(*Q_WINDOW, color="#99cc66", alpha=0.28, lw=0)
        for lo, hi in ((577, 582), (605, 613)):
            if hi > low and lo < high:
                axes.axvspan(lo, hi, color="#999999", alpha=0.32, lw=0)
        axes.set_xlim(low, high)
        axes.set_ylim(*ylim)
        axes.set_ylabel("d²A / dλ²", fontsize=9)
        axes.grid(alpha=0.25)
        axes.tick_params(labelsize=8)
        if index == 2:
            axes.set_xlabel("wavelength (nm)", fontsize=9)
        figure.text(0.13, 0.915 - index * 0.275, "%d  ·  %s" % (index + 1, title),
                    fontsize=10.5, fontweight="bold")
    figure.text(0.13, 0.095,
                "[!]  Grey = INSTRUMENT, not pigment: the 581 nm reference minimum and the 609 nm Bayer crossover.\n"
                "Both search windows are pinned clear of them. Green/brown are the archive's own labels.\n"
                "[*]  Panel 3 shows why the window must be PINNED: for many traces the DEEPEST dip is the 581 artefact,\n"
                "not the 568 band \u2014 a search over 560\u2013582 would return the instrument, not the pigment.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageBySolvent(pdf, rows):
    """One panel per solvent, oils side by side. ⭐ Lugitsch and Billa Clever appear in ALL THREE, so
    the same oil can be read straight across the row -- which is the only way to see whether a metric
    is reporting the OIL or the SOLVENT."""
    solvents = [("isopropanol", "isopropanol  (the shipping recipe)"),
                ("sunflower", "sunflower  (index-matched, food-safe)"),
                ("spirit", "de-aromatised white spirit")]
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("Every oil, grouped by solvent — is the metric reporting the OIL or the SOLVENT?",
                    fontsize=13.5, fontweight="bold", y=0.965)
    metricRows = [("d2R", "d2R = D2(624) / D2(568)", CUT, (0.0, 4.7)),
                  ("Rv", "Rv = 100·(A624−A_valley)/(A_Q−A_valley)", 52.0, (0, 140))]
    counts = {name: sorted({r["oil"] for r in rows if r["solvent"] == name}) for name, _ in solvents}
    widths = [max(1.4, len(counts[name])) for name, _ in solvents]
    left = 0.065
    total = sum(widths)
    for column, (name, title) in enumerate(solvents):
        oils = counts[name]
        width = 0.86 * widths[column] / total
        for line, (key, label, cut, ylim) in enumerate(metricRows):
            axes = figure.add_axes([left, 0.560 - line * 0.390, width, 0.300])
            for index, oil in enumerate(oils):
                values = [r[key] for r in rows if r["solvent"] == name and r["oil"] == oil]
                label_ = [r["class"] for r in rows if r["solvent"] == name and r["oil"] == oil][0]
                offsets = numpy.linspace(-0.17, 0.17, len(values)) if len(values) > 1 else [0.0]
                axes.plot([index + o for o in offsets], values, SOLVENTMARK[name],
                          ls="", color=CLASSCOLOR[label_], ms=6,
                          markeredgecolor="black", markeredgewidth=0.4)
            axes.axhline(cut, color="crimson", lw=1.3, ls="--")
            axes.set_xticks(range(len(oils)))
            axes.set_xticklabels([o.replace(" ", "\n") for o in oils], fontsize=7.5)
            axes.set_xlim(-0.6, len(oils) - 0.4)
            axes.set_ylim(*ylim)
            axes.grid(axis="y", alpha=0.3)
            axes.tick_params(labelsize=7.5)
            if column == 0:
                axes.set_ylabel(label, fontsize=9, fontweight="bold")
            else:
                axes.set_yticklabels([])
            if line == 0:
                axes.set_title("%s   n=%d" % (title, sum(1 for r in rows if r["solvent"] == name)),
                               fontsize=9.5, fontweight="bold")
        left += width + 0.022
    figure.text(0.065, 0.102,
                "[*]  Lugitsch (green) and Billa Clever (brown) appear in ALL THREE solvents \u2014 read them straight across.\n"
                "Both metrics keep every oil on the same side of the line in every solvent. That is the property Q% does NOT have:\n"
                "the same Lugitsch oil reads Q% 13.5\u201315.5 in isopropanol and 20.6\u201320.8 in white spirit.",
                fontsize=8.5, va="top", linespacing=1.6)
    figure.text(0.065, 0.044,
                "[!]  44 runs, not the ~98 labelled ones \u2014 only traces reaching 632 nm can carry a 2nd derivative at 624.\n"
                "Red dashed = the provisional cut (d2R 1.00, Rv 52). Both are FITTED; neither is pre-registered.",
                fontsize=8.5, color="#a03000", va="top", linespacing=1.6)
    pdf.savefig(figure)
    pyplot.close(figure)


def main():
    rows = collect()
    green = [r["d2R"] for r in rows if r["class"] == "green"]
    brown = [r["d2R"] for r in rows if r["class"] == "brown"]
    print("collected %d runs: %d green, %d brown" % (len(rows), len(green), len(brown)))
    print("  green [%.3f .. %.3f]   brown [%.3f .. %.3f]   gap %+.3f"
          % (min(green), max(green), min(brown), max(brown), min(green) - max(brown)))
    with PdfPages(OUT) as pdf:
        pageStrip(pdf, rows)
        pageCurves(pdf, rows)
        pageBySolvent(pdf, rows)
        pdf.infodict()["Title"] = "d2R over every archived run reaching 632 nm"
    print("wrote", OUT)


if __name__ == "__main__":
    main()
