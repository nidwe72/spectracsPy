"""One-evening report for the 2026-08-24 session: 3 oils x 3 runs in fresh sunflower.

Renders, for every run of the day:
  * the shipped `Q%` and the candidate `Rv` (SPEC_red_ratio_metric.md, x100 scale, T = 52);
  * the `Transmitted from absorbance x3 path` swatch -- computed with the app's OWN
    `EvaluationColorUtil.spectrumToLab(path=3.0)`, verified to reproduce the strings the
    reports themselves printed (L* 73 / 74 / 66 on the three 001 runs);
  * per-oil means and standard deviations;
  * the absorbance curves, drawn three ways so they are actually comparable --
    raw, dose-normalised by A_Soret, and a 540-636 nm zoom where the two bands live.

⛔ The three runs of an oil are NOT replicates: 001 = first pour, 002 = the SAME already-exposed
aliquot 96 min later, 003 = a fresh pour of the remaining ~4 ml. The sd over them is therefore a
STABILITY figure across dose and pour, not a repeatability sigma. Labelled as such on the page.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python diagnostics/today_report.py
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
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.model.spectral.Spectrum import Spectrum

OILS = ["Lugitsch", "SparPremium", "SparSBudget"]
RUNS = ["001", "002", "003"]
TIMES = {("Lugitsch", "001"): "21:08", ("Lugitsch", "002"): "22:40", ("Lugitsch", "003"): "23:21",
         ("SparPremium", "001"): "21:01", ("SparPremium", "002"): "22:37", ("SparPremium", "003"): "23:17",
         ("SparSBudget", "001"): "20:56", ("SparSBudget", "002"): "22:32", ("SparSBudget", "003"): "23:13"}
WHAT = {"001": "1st pour", "002": "same aliquot, +96 min", "003": "fresh pour, 2nd half"}
EYE = {"Lugitsch": "green (by far)", "SparPremium": "brown", "SparSBudget": "brown (most)"}
LINESTYLE = {"001": "-", "002": "--", "003": ":"}
OILCOLOR = {"Lugitsch": "#4a7c1f", "SparPremium": "#b8860b", "SparSBudget": "#8b4513"}

# ⭐ THE 08-26 LUGITSCH, overlaid on page A only (Edwin, 2026-08-26). Drawn in a colour that belongs
# to NO oil on this page, because it is a DIFFERENT SESSION: blending it into the Lugitsch green would
# imply it is a fourth run of the same evening, which is exactly the confusion the page exists to avoid.
# ⛔ 002 is omitted: it is a BYTE-IDENTICAL copy of 001 (same md5), so plotting it would draw one
# measurement twice and manufacture an agreement out of nothing. 004 is Edwin's hand-excluded run.
# ⭐ TWO independently prepared fills of the same oil on that evening. Fill B is matched to
# 20260824Lugitsch/001 to within 7 % on the Soret and 1 % on the valley, and still reads with fill A --
# which is how the fill was ruled out as the cause of the step.
LATER = ("20260826Lugitsch", "08-26")
# ⛔ Runs are DISCOVERED, not listed: fill B gained a second run while this was being written, and a
# hardcoded list would have silently dropped it. LATER_SKIPPED is the only hand-maintained part.
LATER_SERIES = [("20260826Lugitsch", "A"), ("20260826LugitschB", "B"), ("20260826LugitschC", "C")]
# ⭐ The OTHER oils of that evening, loaded only to test the turbidity claim honestly — a slope seen in
# one oil's three fills is not a property of the metric until the other oils are asked the same question.
# ⭐⭐ ONLY THE FIRST TWO DISTINCT READS OF EACH ALIQUOT (Edwin, 2026-08-27). Later reads carry more lamp
# on a sample the lamp is known to change. ⛔ DISTINCT, not the files named 001/002: 20260826Lugitsch/002
# is a byte-identical copy of 001 — a failed save, not a read — and spending a slot on it would discard
# 003, that aliquot's genuine second read.
KEPT_RUN_COUNT = 2
# ⚠ 20260826EstererC is deliberately ABSENT: its oil attribution is unconfirmed (it was measured as
# Lugitsch and reassigned), and an unverified label must not enter a stated statistic.
# ⭐⭐ 20260826EstererE is the FIRST fill of the two-stage recipe: 1 ml sunflower + the capillary,
# which EMPTIES ITSELF in a short time — no arm-swing at all — then ~45 s of FAST rotation at the
# bottom while the mixture is still concentrated, then up to 4 ml and ~60 s more. The 40 slow
# inversions are gone.
# ⭐ TWO UNCONTROLLED OPERATOR VARIABLES LEAVE THE PROTOCOL AT ONCE: how hard the capillary was
# swung, and how vigorously the vial was inverted. Neither is measurable after the fact, and both
# were free to differ between fills. That is a σ_fill argument, not an Rv argument.
# ⛔ On Rv it changed nothing: A_Soret rose 10.2 % and A_valley fell 6.9 % against fill B — real,
# measurable, better dissolution — while Rv moved 1.7, i.e. one run of noise. The recipe works;
# Rv is blind to it, because both of its bands held still.
# ⛔ 20260826EstererD set aside 2026-08-27 (Edwin): the only fill made with the hard arm-centrifuge
# extrusion, a step the two-stage recipe has retired. ⚠ Removing it also removes the ONLY
# Esterer/Lugitsch single-fill overlap in the archive — see the all-runs report, which prints
# σ_fill both ways so that consequence cannot go unnoticed.
LATER_OTHERS = ["20260826Esterer", "20260826EstererB", "20260826EstererE", "20260826Stekko"]
LATER_SKIPPED = {"20260826Lugitsch/002": "byte-identical copy of 001",
                 "20260826Lugitsch/004": "set aside by hand, pending discussion",
                 # ⛔ a deliberately SPOILED sample, run only to exercise the clearing-4.0 read
                 "20260826LugitschC/test": "spoiled sample, software test only"}
LATER_COLOR = "#1565c0"
LATER_STYLE = {"A": ("--", 1.4), "B": ("-", 1.9), "C": ("-.", 1.7)}

RV_THRESHOLD = 52.0
OUT = os.path.join(archive.ARCHIVE, "20260824_session_report.pdf")

# ⛔ Isopropanol runs used ONLY as the contrast on the second-derivative page. All four reach 635.9 nm,
# so the "no resolved peak" result below is not a clamp artefact.
ISOPROPANOL = [("Lugitsch", "20260817LigitschA/001.pdf"), ("Lugitsch", "20260814_Lugitsch_A/001.pdf"),
               ("BillaClever", "20260812_BillaClever/001.pdf"), ("BillaClever", "20280819BillaClever/001.pdf")]
D2_GRID = numpy.arange(500.0, 634.01, 0.25)
D2_SMOOTH_NM = 7.0


def secondDerivative(nm, absorbance, smoothNanometers=D2_SMOOTH_NM):
    """2nd derivative on a uniform 0.25 nm grid. Savitzky-Golay needs even spacing, which the native
    trace does not have. ⭐ The window is NOT a sensitive knob: 4-13 nm all keep the green/brown gap
    positive (+0.52 .. +1.34), so 7 nm is a choice, not a fit."""
    y = numpy.interp(D2_GRID, nm, absorbance)
    width = int(smoothNanometers / 0.25)
    width += (width + 1) % 2
    return savgol_filter(y, width, 3, deriv=2, delta=0.25)


def loadIsopropanol():
    out = []
    with tempfile.TemporaryDirectory() as scratch:
        for oil, relative in ISOPROPANOL:
            workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
            nm, absorbance = archive.despikedTrace(workflow)
            out.append((oil, relative, nm, absorbance))
    return out


def bandMean(nm, values, low, high):
    inside = values[(nm >= low) & (nm <= high)]
    return float(numpy.mean(inside)) if len(inside) else float("nan")


def collect():
    colour = EvaluationColorUtil()
    rows = {}
    with tempfile.TemporaryDirectory() as scratch:
        for oil in OILS:
            for run in RUNS:
                path = os.path.join(archive.ARCHIVE, "20260824%s/%s.pdf" % (oil, run))
                workflow = archive.workflowOf(path, scratch)
                nm, absorbance = archive.despikedTrace(workflow)
                valley = bandMean(nm, absorbance, 500.0, 560.0)
                q = bandMean(nm, absorbance, 565.0, 580.0)
                red = bandMean(nm, absorbance, 622.0, 627.0)
                soret = bandMean(nm, absorbance, 448.0, 460.0)
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(k): float(v) for k, v
                                               in (self_spectra(workflow) or {}).items()}
                lightness, chroma, hue, rgb = colour.spectrumToLab(
                    spectrum, path=3.0, ceiling=EvaluationColorUtil.RELATIVE)
                monitor = workflow.get("monitorRecord") or {}
                rows[(oil, run)] = {
                    "nm": nm, "a": absorbance, "soret": soret, "valley": valley, "q": q, "red": red,
                    "qPercent": 100.0 * (q - valley) / soret,
                    "rv": 100.0 * (red - valley) / (q - valley),
                    "lch": (lightness, chroma, hue), "rgb": tuple(c / 255.0 for c in rgb),
                    "outcome": monitor.get("outcome")}
    return rows


def keptReads(series, folder):
    """The first KEPT_RUN_COUNT DISTINCT reads of one fill. A duplicate does not consume a slot."""
    import hashlib
    digests, kept = set(), []
    for name in sorted(f for f in os.listdir(folder) if f.endswith(".pdf")):
        run = name[:-4]
        if "%s/%s" % (series, run) in LATER_SKIPPED:
            continue
        with open(os.path.join(folder, name), "rb") as handle:
            digest = hashlib.md5(handle.read()).hexdigest()
        if digest in digests:
            continue
        digests.add(digest)
        kept.append(run)
        if len(kept) >= KEPT_RUN_COUNT:
            break
    return kept


def loadLater():
    """Today's Lugitsch, both fills, read exactly as the 08-24 rows are so they are comparable."""
    rows = {}
    with tempfile.TemporaryDirectory() as scratch:
        for series, fill in LATER_SERIES:
          folder = os.path.join(archive.ARCHIVE, series)
          for run in keptReads(series, folder):
            path = os.path.join(archive.ARCHIVE, "%s/%s.pdf" % (series, run))
            workflow = archive.workflowOf(path, scratch)
            if workflow is None:
                continue
            nm, absorbance = archive.despikedTrace(workflow)
            valley = bandMean(nm, absorbance, 500.0, 560.0)
            q = bandMean(nm, absorbance, 565.0, 580.0)
            red = bandMean(nm, absorbance, 622.0, 627.0)
            rows["%s%s" % (fill, run)] = {
                "nm": nm, "a": absorbance, "valley": valley, "q": q, "red": red, "fill": fill,
                "rv": 100.0 * (red - valley) / (q - valley)}
    return rows


def self_spectra(workflow):
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            if step["label"] != "Absorption":
                continue
            spectra = step.get("spectra") or {}
            if "ABSORPTION" in spectra:
                return spectra["ABSORPTION"]
    return None


def statsOf(rows, oil, key):
    values = numpy.array([rows[(oil, r)][key] for r in RUNS])
    return values.mean(), values.std(ddof=1), values.min(), values.max()


def pageSummary(pdf, rows):
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("Spectracs — session of 2026-08-24   ·   3 oils × 3 runs, fresh sunflower, one shared reference",
                    fontsize=14, fontweight="bold", y=0.975)
    figure.text(0.5, 0.937, "Rv  (THE VERDICT METRIC)  = 100 · (A[622–627] − A_valley) / (A[565–580] − A_valley)"
                "      T = 52, higher = greener\n"
                "Q%  (shipped today, superseded)  = 100 · (A_Q − A_valley) / A_Soret,  higher = browner",
                ha="center", fontsize=8.5, style="italic", linespacing=1.6, va="top")
    axes = figure.add_axes([0.04, 0.10, 0.92, 0.775])
    axes.axis("off")
    # ⛔ pin the coordinate system: text defaults to DATA coords, so an axes.plot() separator would
    # autoscale the limits and the transAxes swatches would drift away from their rows.
    axes.set_xlim(0.0, 1.0)
    axes.set_ylim(0.0, 1.0)
    # ⭐ Rv leads: it is the verdict metric (ROADMAP 2026-08-25), so it comes before Q% on every page.
    headers = ["oil", "run", "time", "what", "Rv", "Rv verdict", "Q%", "A_Soret",
               "×3 path  L* C* h", "swatch"]
    xs = [0.005, 0.115, 0.165, 0.225, 0.395, 0.470, 0.590, 0.665, 0.760, 0.945]
    top, rowHeight = 0.955, 0.088
    for x, header in zip(xs, headers):
        axes.text(x, top, header, fontsize=9, fontweight="bold", va="center")
    axes.plot([0, 1], [top - 0.030, top - 0.030], color="black", lw=1.0)
    y = top - 0.055
    for index, oil in enumerate(OILS):
        for run in RUNS:
            row = rows[(oil, run)]
            lightness, chroma, hue = row["lch"]
            cells = [oil if run == "001" else "", run, TIMES[(oil, run)], WHAT[run],
                     "%.1f" % row["rv"], "GREEN" if row["rv"] > RV_THRESHOLD else "brown",
                     "%.2f" % row["qPercent"], "%.3f" % row["soret"],
                     "L* %.0f · C* %.0f · h %.0f°" % (lightness, chroma, hue), ""]
            weight = "bold" if run == "001" else "normal"
            for x, cell, header in zip(xs, cells, headers):
                if header in ("Rv", "Q%", "A_Soret"):
                    axes.text(x + 0.050, y, cell, fontsize=9, va="center", ha="right",
                              fontweight="bold" if header == "Rv" else weight,
                              family="monospace")
                elif header == "Rv verdict":
                    axes.text(x, y, cell, fontsize=9, va="center", fontweight="bold",
                              color=OILCOLOR["Lugitsch"] if cell == "GREEN" else "#8b4513")
                else:
                    axes.text(x, y, cell, fontsize=9, va="center", fontweight=weight)
            axes.add_patch(Rectangle((xs[-1], y - 0.026), 0.050, 0.052,
                                     facecolor=row["rgb"], edgecolor="#555555", lw=0.6))
            y -= rowHeight
        if index < len(OILS) - 1:
            axes.plot([0, 1], [y + rowHeight * 0.42] * 2, color="#bbbbbb", lw=0.6)
            y -= 0.012
    figure.text(0.04, 0.055,
                "[!]  The three runs of an oil are NOT replicates.  001 = first pour ·  002 = the SAME already-exposed aliquot 96 min later ·  "
                "003 = a fresh pour of the remaining ~4 ml.",
                fontsize=8.5, color="#a03000")
    figure.text(0.04, 0.033,
                "[!]  Rv is THE VERDICT METRIC (ROADMAP 2026-08-25) but is CHOSEN, NOT YET BUILT \u2014 Q% still computes the pill "
                "until Rv lands and clears M9 (SPEC_red_ratio_metric.md §7).",
                fontsize=8.5, color="#a03000")
    pdf.savefig(figure)
    pyplot.close(figure)


def pageStats(pdf, rows):
    figure, grid = pyplot.subplots(1, 2, figsize=(11.69, 8.27), gridspec_kw={"width_ratios": [1.15, 1]})
    figure.suptitle("Means and standard deviations over the three runs of each oil",
                    fontsize=14, fontweight="bold")
    axes = grid[0]
    axes.axis("off")
    axes.text(0.0, 1.0, "mean ± sd   (n = 3: pour → dose → re-pour)", fontsize=10,
              fontweight="bold", va="top")
    y = 0.92
    for key, label, fmt in [("rv", "Rv", "%.1f"), ("qPercent", "Q%", "%.2f"),
                            ("soret", "A_Soret", "%.3f"), ("valley", "A_valley", "%.3f"),
                            ("q", "A_Q  565–580", "%.3f"), ("red", "A_624  622–627", "%.3f")]:
        y -= 0.075
        axes.text(0.0, y, label, fontsize=10, fontweight="bold", va="top")
        y -= 0.048
        for oil in OILS:
            mean, sd, low, high = statsOf(rows, oil, key)
            axes.text(0.04, y, oil, fontsize=9, va="top", color=OILCOLOR[oil])
            axes.text(0.42, y, ("%s  ± %s" % (fmt, fmt)) % (mean, sd), fontsize=9,
                      va="top", family="monospace", fontweight="bold" if key == "rv" else "normal")
            axes.text(0.72, y, ("[%s … %s]" % (fmt, fmt)) % (low, high), fontsize=8.5,
                      va="top", family="monospace", color="#555555")
            y -= 0.042
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)

    axes = grid[1]
    width = 0.6
    positions = numpy.arange(len(OILS))
    means = [statsOf(rows, oil, "rv")[0] for oil in OILS]
    sds = [statsOf(rows, oil, "rv")[1] for oil in OILS]
    axes.bar(positions, means, width, yerr=sds, capsize=8,
             color=[OILCOLOR[o] for o in OILS], alpha=0.85, edgecolor="black", lw=0.8)
    for position, oil in zip(positions, OILS):
        for run in RUNS:
            axes.plot(position, rows[(oil, run)]["rv"], "o", color="black", ms=4, zorder=5)
    axes.axhline(RV_THRESHOLD, color="crimson", lw=1.4, ls="--")
    axes.text(len(OILS) - 0.45, RV_THRESHOLD + 2, "T = 52  (provisional, fitted)",
              color="crimson", fontsize=9, ha="right")
    axes.set_xticks(positions)
    axes.set_xticklabels(["%s\n%s" % (o, EYE[o]) for o in OILS], fontsize=9)
    axes.set_ylabel("Rv", fontsize=11, fontweight="bold")
    axes.set_title("Rv, mean ± sd, with the three runs overplotted", fontsize=11)
    axes.set_ylim(0, 135)
    axes.grid(axis="y", alpha=0.3)
    figure.text(0.06, 0.035,
                "[!]  These sd values span a light dose AND a re-pour, so they are a STABILITY figure across the evening, "
                "not a repeatability σ_fill. SparSBudget is the outlier in every panel of this session.",
                fontsize=8.5, color="#a03000")
    pyplot.tight_layout(rect=[0, 0.06, 1, 0.95])
    pdf.savefig(figure)
    pyplot.close(figure)


def __bands(axes, labelAt=0.97):
    """Shade the four windows. `labelAt` is the fraction of the y-range the labels sit at, so a
    crowded panel can push them down out of the curves."""
    low_, high_ = axes.get_ylim()
    for low, high, label, colour in [(448, 460, "Soret", "#6699cc"), (500, 560, "valley", "#cccccc"),
                                     (565, 580, "A_Q", "#99cc66"), (622, 627, "A_624", "#cc6666")]:
        axes.axvspan(low, high, color=colour, alpha=0.22, lw=0)
        if low < axes.get_xlim()[0]:
            continue
        axes.text((low + high) / 2.0, low_ + (high_ - low_) * labelAt, label, fontsize=7.5,
                  ha="center", va="top", color="#444444")


def pageCurves(pdf, rows):
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Absorbance, drawn three ways so the nine runs are comparable",
                    fontsize=13, fontweight="bold", y=0.978)
    # ⛔ explicit axes rectangles, NOT tight_layout: the long multi-line titles make tight_layout
    # collapse the plot area toward the right-hand margin.
    boxes = [[0.10, 0.700, 0.86, 0.205],
             [0.10, 0.400, 0.86, 0.205],
             [0.10, 0.090, 0.86, 0.205]]

    axes = figure.add_axes(boxes[0])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            axes.plot(row["nm"], row["a"], LINESTYLE[run], color=OILCOLOR[oil], lw=1.0)
    axes.set_xlim(440, 636)
    axes.set_ylim(0, 1.45)
    __bands(axes)
    axes.set_ylabel("A", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.10, 0.930, "1  ·  RAW absorbance", fontsize=10.5, fontweight="bold")
    figure.text(0.10, 0.914, "Dominated by DOSE, not by the oil — the 003 pours carry 15–45 % more absorber.",
                fontsize=8.5, color="#444444")

    axes = figure.add_axes(boxes[1])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            axes.plot(row["nm"], row["a"] / row["soret"], LINESTYLE[run], color=OILCOLOR[oil], lw=1.0)
    axes.set_xlim(440, 636)
    axes.set_ylim(0, 1.35)
    __bands(axes)
    axes.set_ylabel("A / A_Soret", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.10, 0.630, "2  ·  NORMALISED by A_Soret", fontsize=10.5, fontweight="bold")
    figure.text(0.10, 0.614, "Dose divided out. The three runs of one oil now collapse onto one curve.",
                fontsize=8.5, color="#444444")

    axes = figure.add_axes(boxes[2])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            mask = row["nm"] >= 535
            axes.plot(row["nm"][mask], (row["a"] / row["soret"])[mask], LINESTYLE[run],
                      color=OILCOLOR[oil], lw=1.2)
    axes.set_xlim(535, 636)
    axes.set_ylim(0, 0.56)
    __bands(axes, labelAt=0.34)
    axes.axvline(609, color="#999999", lw=0.8, ls="-.")
    axes.text(608.0, 0.552, "609 nm Bayer crossover (detector artefact)", fontsize=6.5,
              color="#777777", va="top", ha="right")
    axes.set_xlabel("wavelength (nm)", fontsize=9)
    axes.set_ylabel("A / A_Soret", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.10, 0.320, "3  ·  ZOOM 535–636 nm, Soret-normalised — where the whole decision is made",
                fontsize=10.5, fontweight="bold")
    figure.text(0.10, 0.304, "The 568 band is the SAME height for Lugitsch and SparPremium; only the 624 band separates them.",
                fontsize=8.5, color="#444444")

    handles = [pyplot.Line2D([], [], color=OILCOLOR[o], lw=2, label="%s — %s" % (o, EYE[o])) for o in OILS]
    handles += [pyplot.Line2D([], [], color="#666666", lw=1.2, ls=LINESTYLE[r],
                              label="%s   %s" % (r, WHAT[r])) for r in RUNS]
    figure.legend(handles=handles, fontsize=8, loc="lower center", ncol=2,
                  bbox_to_anchor=(0.53, 0.005), framealpha=0.95)
    pdf.savefig(figure)
    pyplot.close(figure)


def fillStatistics(later):
    """⭐ COMPUTED, never typed. What VARIES between independently prepared fills of one oil?

    ⛔⛔ THIS REPLACES A TURBIDITY CLAIM THAT WAS WRONG. The three Lugitsch fills showed Rv rising with
    A_valley at r = +0.86, and it was reported as the metric riding turbidity. The SECOND ESTERER FILL
    refuted it: valley 0.171 against fill A's 0.182 — indistinguishable — and Rv 15.4 HIGHER. Over all
    sixteen 08-26 runs the correlation is ~0. Three points of one oil were a coincidence.
    ⭐ What survives is bigger and worse: fills are individually repeatable and mutually inconsistent,
    which is a PREPARATION variable, not measurement noise."""
    fills = {}
    for row in later.values():
        fills.setdefault(row["fill"], []).append(row["rv"])
    means = [numpy.mean(v) for v in fills.values()]
    within = [numpy.var(v, ddof=1) for v in fills.values() if len(v) > 1]
    spread = (max(means) - min(means)) if len(means) > 1 else 0.0
    withinSd = numpy.sqrt(numpy.mean(within)) if within else float("nan")
    return spread, withinSd, len(fills)


def crossOilTurbidity(later, scratch):
    """r between Rv and A_valley over EVERY oil measured that evening, not just the one on this page.

    ⭐ Also returns the per-fill means of the OTHER oils, because the strongest single refutation of the
    turbidity story is not the pooled r -- it is two fills of ONE oil that sit at the SAME valley and
    read far apart. That pair has to be FOUND in the data, not typed in: it was two fills when first
    written and is four now, and a hardcoded "15.4 Rv apart" would still be claiming the old pair."""
    valleys = [row["valley"] for row in later.values()]
    values = [row["rv"] for row in later.values()]
    fills = {}
    for series in LATER_OTHERS:
        for run in keptReads(series, os.path.join(archive.ARCHIVE, series)):
            workflow = archive.workflowOf(
                os.path.join(archive.ARCHIVE, "%s/%s.pdf" % (series, run)), scratch)
            if workflow is None:
                continue
            nm, absorbance = archive.despikedTrace(workflow)
            valley = bandMean(nm, absorbance, 500.0, 560.0)
            q = bandMean(nm, absorbance, 565.0, 580.0)
            red = bandMean(nm, absorbance, 622.0, 627.0)
            valleys.append(valley)
            values.append(100.0 * (red - valley) / (q - valley))
            fills.setdefault(series, []).append((valley, values[-1]))
    if len(valleys) < 4:
        return float("nan"), len(valleys), ""
    return float(numpy.corrcoef(valleys, values)[0, 1]), len(valleys), matchedValleyPair(fills)


def matchedValleyPair(fills, oil="Esterer"):
    """The two fills of one oil whose A_valley is closest, and how far apart their Rv is.

    ⛔ A pooled correlation cannot refute turbidity, because oils have opposite-signed slopes and
    pooling them gives ~0 by construction. What refutes it is a MATCHED pair: same turbidity, different
    reading. This picks that pair out of whatever fills exist today."""
    means = {s: (float(numpy.mean([v for v, _ in rows])), float(numpy.mean([r for _, r in rows])))
             for s, rows in fills.items() if oil in s}
    if len(means) < 2:
        return ""
    best = None
    for a in means:
        for b in means:
            if a < b:
                gap = abs(means[a][0] - means[b][0])
                if best is None or gap < best[0]:
                    best = (gap, a, b)
    _, a, b = best
    return ("%s's closest-matched fills (%d on record) sit at A_valley %.3f vs %.3f \u2014 "
            "%.1f Rv apart" % (oil, len(means), means[a][0], means[b][0],
                               abs(means[a][1] - means[b][1])))


def pageRvNative(pdf, rows, later=None, cross=None):
    """Edwin 2026-08-24: normalise on the window `Rv` ACTUALLY USES and datum it on A_valley.

    Two renderings, because they answer different questions:

      A  Rv-NATIVE   y = (A - A_valley) / (A_Q - A_valley)
         The valley becomes 0 and the Q band becomes 1 BY CONSTRUCTION, so the only thing left
         free on the page is the 624 band -- and its mean height over 622-627 IS Rv/100. The
         metric stops being a number beside a plot and becomes a distance you can read off it.

      B  SNV over 500-627 nm   y = (A - mean) / sd, both taken on that window ONLY
         The textbook transform, restricted to the span Rv touches. It keeps the band SHAPES
         but not the datum, so it is the fair "is the shape different?" picture.

    ⛔ Neither is a new metric. Both are re-plots of the same nine traces.
    """
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Normalised on Rv's own window (500\u2013627 nm), datum at A_valley",
                    fontsize=13, fontweight="bold", y=0.978)
    boxes = [[0.11, 0.737, 0.85, 0.168],
             [0.11, 0.395, 0.85, 0.200],
             [0.11, 0.085, 0.85, 0.177]]

    def rvNative(row):
        return (row["a"] - row["valley"]) / (row["q"] - row["valley"])

    def snv(row):
        window = (row["nm"] >= 500.0) & (row["nm"] <= 627.0)
        inside = row["a"][window]
        return (row["a"] - inside.mean()) / inside.std(ddof=1)

    axes = figure.add_axes(boxes[0])
    for oil in OILS:
        for run in RUNS:
            axes.plot(rows[(oil, run)]["nm"], rvNative(rows[(oil, run)]), LINESTYLE[run],
                      color=OILCOLOR[oil], lw=1.1)
    for run, row in sorted((later or {}).items()):
        axes.plot(row["nm"], rvNative(row), LATER_STYLE[row["fill"]][0],
                  color=LATER_COLOR, lw=LATER_STYLE[row["fill"]][1], alpha=0.95)
    axes.axhline(0.0, color="#444444", lw=0.9)
    axes.axhline(1.0, color="#444444", lw=0.9, ls=":")
    axes.set_xlim(495, 638)
    axes.set_ylim(-0.35, 1.38)
    axes.axvspan(500, 560, color="#cccccc", alpha=0.22, lw=0)
    axes.axvspan(565, 580, color="#99cc66", alpha=0.22, lw=0)
    axes.axvspan(622, 627, color="#cc6666", alpha=0.30, lw=0)
    axes.text(530, -0.26, "A_valley  \u2192  y = 0", fontsize=7.5, ha="center", color="#444444")
    axes.text(572, 1.10, "A_Q  \u2192  y = 1", fontsize=7.5, ha="center", color="#444444")
    axes.text(624, -0.26, "A_624", fontsize=7.5, ha="center", color="#aa3333")
    # the mean Rv of each oil, drawn as what it physically is: the height of the 624 band on this axis
    marks = [(OILCOLOR[oil], numpy.mean([rows[(oil, r)]["rv"] for r in RUNS]) / 100.0)
             for oil in OILS]
    if later:
        marks.append((LATER_COLOR, numpy.mean([r["rv"] for r in later.values()]) / 100.0))
    for index, (colour, height) in enumerate(marks):
        x = 630.4 + index * 1.75
        axes.annotate("", xy=(x, height), xytext=(x, 0.0),
                      arrowprops=dict(arrowstyle="<->", color=colour, lw=1.4))
        axes.text(x, height + 0.045, "%.0f" % (height * 100), fontsize=7.5,
                  color=colour, ha="center", fontweight="bold")
    axes.text(633.4, 1.28, "mean Rv", fontsize=7.5, color="#444444", ha="center", style="italic")
    axes.set_ylabel("(A \u2212 A_valley) / (A_Q \u2212 A_valley)", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.11, 0.932, "A  \u00b7  Rv-NATIVE \u2014 valley pinned to 0, Q band pinned to 1",
                fontsize=10.5, fontweight="bold")
    figure.text(0.11, 0.916,
                "Everything Rv divides out is now flat, so the ONLY free quantity on the page is the 624 band \u2014 "
                "and its height IS Rv/100.",
                fontsize=8.5, color="#444444")
    if later:
        for fill in sorted({r["fill"] for r in later.values()}):
            style, width = LATER_STYLE[fill]
            axes.plot([], [], style, color=LATER_COLOR, lw=width,
                      label="Lugitsch 08-26 fill %s" % fill)
        axes.legend(fontsize=7.5, loc="upper left", framealpha=0.95)
        figure.text(0.11, 0.707,
                    "[!]  BLUE = the SAME OIL measured %s, a different session \u2014 not a fourth run of this "
                    "evening. Its 624 band has fallen\n"
                    "     onto the Q band: Rv %.0f against %.0f on 08-24, over %d independently prepared "
                    "fills (%s).\n"
                    "     [!] But the %d fills span %.1f Rv while repeating to sd %.1f WITHIN a fill — "
                    "the variance is in the PREPARATION.\n"
                    "     Not turbidity: over all %d runs of that evening Rv vs A_valley is r = %+.2f,\n"
                    "     and %s.\n"
                    "     Until a sigma_fill exists, neither this step nor the "
                    "oil-to-oil gap has a yardstick."
                    % (LATER[1], numpy.mean([r["rv"] for r in later.values()]),
                       numpy.mean([rows[("Lugitsch", r)]["rv"] for r in RUNS]),
                       len({r["fill"] for r in later.values()}),
                       ", ".join(sorted({r["fill"] for r in later.values()})),
                       fillStatistics(later)[2], fillStatistics(later)[0], fillStatistics(later)[1],
                       (cross or (float("nan"), 0, ""))[1], (cross or (float("nan"), 0, ""))[0],
                       (cross or (float("nan"), 0, ""))[2] or "no matched pair yet"),
                    fontsize=8, color="#a03000", linespacing=1.5, va="top")

    axes = figure.add_axes(boxes[1])
    for oil in OILS:
        for run in RUNS:
            mask = rows[(oil, run)]["nm"] >= 600
            axes.plot(rows[(oil, run)]["nm"][mask], rvNative(rows[(oil, run)])[mask],
                      LINESTYLE[run], color=OILCOLOR[oil], lw=1.3)
    for run, row in sorted((later or {}).items()):
        mask = row["nm"] >= 600
        axes.plot(row["nm"][mask], rvNative(row)[mask], LATER_STYLE[row["fill"]][0],
                  color=LATER_COLOR, lw=LATER_STYLE[row["fill"]][1] + 0.1, alpha=0.95)
    axes.axhline(0.0, color="#444444", lw=0.9)
    axes.axvspan(622, 627, color="#cc6666", alpha=0.30, lw=0)
    axes.axvline(609, color="#999999", lw=0.8, ls="-.")
    axes.set_xlim(600, 636)
    axes.set_ylim(-0.05, 1.05)
    axes.set_ylabel("same axis, zoomed", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.11, 0.625, "B  \u00b7  the same axis, zoomed on the red band",
                fontsize=10.5, fontweight="bold")
    figure.text(0.11, 0.609,
                "Three green traces sit near 1.1\u20131.3; six brown traces sit near 0.3\u20130.45. "
                "No overlap, and the gap is the whole verdict.",
                fontsize=8.5, color="#444444")

    axes = figure.add_axes(boxes[2])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            # ⛔ slice BEFORE plotting: matplotlib autoscales y over all plotted data, so handing it
            # the full 413-636 trace and then setting xlim would scale the axis to the Soret at 440.
            mask = (row["nm"] >= 495.0) & (row["nm"] <= 636.0)
            axes.plot(row["nm"][mask], snv(row)[mask], LINESTYLE[run], color=OILCOLOR[oil], lw=1.1)
    for run, row in sorted((later or {}).items()):
        mask = (row["nm"] >= 495.0) & (row["nm"] <= 636.0)
        axes.plot(row["nm"][mask], snv(row)[mask], LATER_STYLE[row["fill"]][0],
                  color=LATER_COLOR, lw=LATER_STYLE[row["fill"]][1], alpha=0.95)
    axes.axhline(0.0, color="#444444", lw=0.9)
    axes.set_xlim(495, 636)
    axes.set_ylim(-1.5, 3.3)
    axes.axvspan(500, 560, color="#cccccc", alpha=0.22, lw=0)
    axes.axvspan(565, 580, color="#99cc66", alpha=0.22, lw=0)
    axes.axvspan(622, 627, color="#cc6666", alpha=0.30, lw=0)
    axes.set_xlabel("wavelength (nm)", fontsize=9)
    axes.set_ylabel("SNV  (A \u2212 \u03bc) / \u03c3, 500\u2013627 nm", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.11, 0.315, "C  \u00b7  SNV over 500\u2013627 nm only \u2014 the textbook transform on Rv's span",
                fontsize=10.5, fontweight="bold")
    figure.text(0.11, 0.299,
                "Mean and sd taken on that window ONLY. Shape is kept, the datum is not \u2014 the fair "
                "\u201cis the shape different?\u201d picture.",
                fontsize=8.5, color="#444444")
    figure.text(0.11, 0.2855,
                "[!]  The 624-vs-569 winner belongs to the oil ON A DAY, not to the oil: Lugitsch's own swing "
                "between these sessions is \u22120.46,\n"
                "     against a +0.58 gap to Esterer on 08-26.  SNV(624\u2212569) tracks Rv at r = 0.993 \u2014 "
                "not independent corroboration.",
                fontsize=7.6, color="#a03000", va="top", linespacing=1.45)
    # ⭐ falls straight out of the transform: which band is the TALLEST after SNV?
    axes.annotate("Lugitsch 08-24 peaks at 624", xy=(624, 2.25), xytext=(586, 2.98),
                  fontsize=8, color=OILCOLOR["Lugitsch"], fontweight="bold",
                  arrowprops=dict(arrowstyle="->", color=OILCOLOR["Lugitsch"], lw=1.2))
    if later:
        axes.annotate("the SAME oil on 08-26 peaks at 569", xy=(569, 2.26), xytext=(499, 1.72),
                      fontsize=8, color=LATER_COLOR, fontweight="bold",
                      arrowprops=dict(arrowstyle="->", color=LATER_COLOR, lw=1.2))
    axes.annotate("both Spars peak at 569", xy=(571, 2.7), xytext=(505, 2.95),
                  fontsize=8, color=OILCOLOR["SparSBudget"], fontweight="bold",
                  arrowprops=dict(arrowstyle="->", color=OILCOLOR["SparSBudget"], lw=1.2))

    handles = [pyplot.Line2D([], [], color=OILCOLOR[o], lw=2, label="%s \u2014 %s" % (o, EYE[o])) for o in OILS]
    handles += [pyplot.Line2D([], [], color="#666666", lw=1.2, ls=LINESTYLE[r],
                              label="%s   %s" % (r, WHAT[r])) for r in RUNS]
    figure.legend(handles=handles, fontsize=8, loc="lower center", ncol=2,
                  bbox_to_anchor=(0.53, 0.003), framealpha=0.95)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageSecondDerivative(pdf, rows):
    """Edwin 2026-08-25. The 2nd derivative annihilates any smooth background, so it tests whether the
    624 feature is a REAL BAND rather than a shoulder on a pedestal. It is - and the contrast with
    isopropanol is the finding: an index-matched solvent gives the whole peak, an emulsion does not."""
    isopropanol = loadIsopropanol()
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Second derivative \u2014 the bands are real,\nand whole only in an index-matched solvent",
                    fontsize=12.5, fontweight="bold", y=0.985, linespacing=1.4)

    # --- A: D2 of today's nine ------------------------------------------------------------------
    axes = figure.add_axes([0.13, 0.660, 0.83, 0.185])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            axes.plot(D2_GRID, secondDerivative(row["nm"], row["a"]), LINESTYLE[run],
                      color=OILCOLOR[oil], lw=1.0)
    axes.axhline(0.0, color="#444444", lw=0.8)
    axes.axvspan(565, 573, color="#99cc66", alpha=0.28, lw=0)
    axes.axvspan(621, 627, color="#cc6666", alpha=0.32, lw=0)
    axes.axvspan(605, 613, color="#999999", alpha=0.30, lw=0)
    # ⛔ the OTHER Bayer crossover. The reference itself falls to a minimum at 581 nm
    # (`DOC_lamp_rebuild.md` §326), and the D2 dip lands at 579.5-580.2 in all nine runs -- an
    # instrument feature, not a pigment band. Searching 560-582 for "the 568 dip" finds THIS instead
    # on 5 of 9 runs, which is why the window is pinned to 565-573.
    axes.axvspan(577, 582, color="#999999", alpha=0.30, lw=0)
    axes.set_xlim(540, 634)
    axes.set_ylim(-0.028, 0.016)
    axes.text(609, -0.0265, "609 nm artefact\n2.7\u20135.6\u00d7 the 624 band", fontsize=6.5,
              ha="center", va="bottom", color="#666666")
    axes.text(569, 0.013, "D2(568)", fontsize=7.5, ha="center", color="#446622")
    axes.text(579.5, -0.0265, "581 nm artefact\n(reference minimum)", fontsize=6.5,
              ha="center", va="bottom", color="#666666")
    axes.text(624, 0.013, "D2(624)", fontsize=7.5, ha="center", color="#aa3333")
    axes.set_ylabel("d\u00b2A / d\u03bb\u00b2", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.13, 0.912, "A  \u00b7  the nine sunflower runs, 2nd derivative",
                fontsize=10.5, fontweight="bold")
    figure.text(0.13, 0.896,
                "A minimum here is a real absorption band. No baseline, no A_valley, no pedestal.",
                fontsize=8.5, color="#444444")
    figure.text(0.13, 0.881,
                "[!]  The two grey bands are INSTRUMENT, not pigment \u2014 the 581 nm reference minimum and the\n"
                "609 nm Bayer crossover. Both search windows are pinned to avoid them.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)

    # --- B: whole peak vs plateau --------------------------------------------------------------
    axes = figure.add_axes([0.13, 0.400, 0.83, 0.200])
    for oil in OILS:
        for run in RUNS:
            row = rows[(oil, run)]
            floor = numpy.percentile(row["a"][(row["nm"] >= 604) & (row["nm"] <= 616)], 20)
            band = row["a"] - floor
            peak = band[(row["nm"] >= 618) & (row["nm"] <= 630)].max()
            mask = row["nm"] >= 614
            axes.plot(row["nm"][mask], (band / peak)[mask], "-", color="#2e7d32", lw=1.1)
    for oil, relative, nm, absorbance in isopropanol:
        floor = numpy.percentile(absorbance[(nm >= 604) & (nm <= 616)], 20)
        band = absorbance - floor
        peak = band[(nm >= 618) & (nm <= 634)].max()
        mask = nm >= 614
        axes.plot(nm[mask], (band / peak)[mask], "-", color="#c62828", lw=1.4)
    axes.axvspan(621, 627, color="#cc6666", alpha=0.20, lw=0)
    axes.axhline(1.0, color="#888888", lw=0.7, ls=":")
    axes.set_xlim(614, 636)
    axes.set_ylim(0, 1.15)
    axes.set_xlabel("wavelength (nm)", fontsize=9)
    axes.set_ylabel("band above its local floor,\nscaled to its own peak", fontsize=9)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    axes.legend(handles=[pyplot.Line2D([], [], color="#2e7d32", lw=2,
                                       label="sunflower (n=9) \u2014 max at 623\u2013625, falls 81\u201399 % by 633"),
                         pyplot.Line2D([], [], color="#c62828", lw=2,
                                       label="isopropanol (n=4) \u2014 rises to 629\u2013630, falls 4\u201314 %")],
                fontsize=7.5, loc="lower left", framealpha=0.95)
    figure.text(0.13, 0.632, "B  \u00b7  [*] the same band in two solvents, each scaled to its own peak",
                fontsize=10.5, fontweight="bold")
    figure.text(0.13, 0.616,
                "All thirteen runs reach 635.9 nm, so this is NOT a clamp artefact, and the reference falls "
                "identically in both solvents.",
                fontsize=8.5, color="#444444")

    # --- C: d2R --------------------------------------------------------------------------------
    axes = figure.add_axes([0.13, 0.135, 0.50, 0.175])
    for index, oil in enumerate(OILS):
        for run in RUNS:
            row = rows[(oil, run)]
            d2 = secondDerivative(row["nm"], row["a"])
            red = d2[(D2_GRID >= 621) & (D2_GRID <= 627)].min()
            green = d2[(D2_GRID >= 565) & (D2_GRID <= 573)].min()
            axes.plot(index, red / green, "o", color=OILCOLOR[oil], ms=7,
                      markeredgecolor="black", markeredgewidth=0.5)
    axes.axhline(1.0, color="crimson", lw=1.3, ls="--")
    axes.text(2.45, 1.05, "a cut near 1.0 separates all 44", fontsize=7.5, color="crimson", ha="right")
    axes.set_xticks(range(len(OILS)))
    axes.set_xticklabels(OILS, fontsize=8)
    axes.set_xlim(-0.5, 2.5)
    axes.set_ylim(0.4, 2.6)
    axes.set_ylabel("d2R = D2(624) / D2(568)", fontsize=9)
    axes.grid(axis="y", alpha=0.3)
    axes.tick_params(labelsize=8)

    figure.text(0.13, 0.335, "C  \u00b7  d2R = D2(624) / D2(568) \u2014 a baseline-free discriminator",
                fontsize=10.5, fontweight="bold")
    figure.text(0.68, 0.305, "Over all 44 runs that reach 635.9 nm:", fontsize=8.5, fontweight="bold")
    lines = [("d2R", "green 1.10\u20134.42   brown 0.27\u20130.94", "0 / 44 err", "|d| 2.74"),
             ("Rv", "green 98.4\u2013125.8  brown 28.3\u201346.4", "0 / 44 err", "|d| 10.48"),
             ("Q%", "green 12.7\u201320.8   brown 17.8\u201323.1", "5 / 44 err", "|d| 2.38")]
    for line, (name, span, err, effect) in enumerate(lines):
        y = 0.285 - line * 0.030
        figure.text(0.68, y, name, fontsize=8, fontweight="bold", family="monospace")
        figure.text(0.72, y, span, fontsize=7.5, family="monospace")
        figure.text(0.72, y - 0.013, "%s   %s" % (err, effect), fontsize=7.5,
                    family="monospace", color="#555555")
    figure.text(0.68, 0.185,
                "[*]  window-robust: 4/5/7/9/11/13 nm\nall separate (gap +0.52 \u2026 +1.34).",
                fontsize=7.5, color="#222222", va="top", linespacing=1.5)

    figure.text(0.13, 0.080,
                "[!]  A better DIAGNOSTIC than metric. It needs no baseline and is robust to the smoothing window \u2014 but it is\n"
                "computable on only 44 of ~98 labelled runs (the 629.8 nm epoch has no far flank), its effect size is 4\u00d7 worse\n"
                "than Rv on the same runs, and the 609 nm Bayer artefact is the LARGEST D2 feature in the region.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageSwatches(pdf, rows):
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("Transmitted from absorbance · ×3 path — what the tube looks like end-on",
                    fontsize=14, fontweight="bold")
    figure.text(0.5, 0.905,
                "Beer–Lambert T = 10^(−kA) modelled from the measured absorbance at 3× the poured depth, "
                "the sample's OWN luminance kept.\n"
                "[!] Deliberately NOT dilution-invariant — brownness IS lightness IS concentration. "
                "The reference is the illuminant, so this is the oil's EXCESS colour over the solvent blank.",
                ha="center", fontsize=9, style="italic")
    for column, oil in enumerate(OILS):
        for line, run in enumerate(RUNS):
            row = rows[(oil, run)]
            left = 0.07 + column * 0.305
            bottom = 0.60 - line * 0.205
            figure.add_artist(Rectangle((left, bottom), 0.20, 0.145, facecolor=row["rgb"],
                                        edgecolor="#333333", lw=1.0))
            lightness, chroma, hue = row["lch"]
            figure.text(left + 0.215, bottom + 0.105, "%s  %s" % (run, TIMES[(oil, run)]),
                        fontsize=8.5, fontweight="bold")
            figure.text(left + 0.215, bottom + 0.072, "L* %.0f" % lightness, fontsize=8, family="monospace")
            figure.text(left + 0.215, bottom + 0.045, "C* %.0f" % chroma, fontsize=8, family="monospace")
            figure.text(left + 0.215, bottom + 0.018, "h  %.0f°" % hue, fontsize=8, family="monospace")
        figure.text(0.07 + column * 0.305 + 0.10, 0.775, oil, fontsize=12, fontweight="bold",
                    ha="center", color=OILCOLOR[oil])
        figure.text(0.07 + column * 0.305 + 0.10, 0.752, EYE[oil], fontsize=9, ha="center", color="#555555")
    figure.text(0.07, 0.132,
                "Hue ordering per round   (truth: Lugitsch > SparPremium > SparSBudget):",
                fontsize=9, fontweight="bold")
    for line, (run, text, ok) in enumerate([
            ("001", "Lugitsch 115\u00b0  >  SparPremium 106\u00b0  >  SparSBudget  96\u00b0", True),
            ("002", "Lugitsch 115\u00b0  >  SparPremium 106\u00b0  >  SparSBudget  82\u00b0", True),
            ("003", "Lugitsch 113\u00b0  >  SparSBudget  100\u00b0  >  SparPremium  79\u00b0", False)]):
        figure.text(0.10, 0.108 - line * 0.019,
                    "%s   %s   %s" % (run, text, "OK" if ok else "WRONG"),
                    fontsize=8.5, family="monospace", color="#222222" if ok else "#c00000")
    figure.text(0.56, 0.132,
                "[!]  The \u00d73 path swatch is NOT dilution-invariant, by design, and on\n"
                "the 003 pours that bites: SparPremium gained +45.5 % absorber against\n"
                "SparSBudget's +15.2 %, which FLIPS their hue order. Rv, dose-invariant,\n"
                "keeps the order in all three rounds.  \u2192  use the swatch to SEE a\n"
                "sample, not to RANK two samples.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    figure.text(0.07, 0.014,
                "[!]  Chroma groups Lugitsch and SparPremium together on the first pours (C* \u2248 52) and separates only "
                "SparSBudget (C* \u2248 32) \u2014 C* alone would not reproduce the ranking either.",
                fontsize=8.5, color="#a03000")
    pdf.savefig(figure)
    pyplot.close(figure)


def main():
    rows = collect()
    later = loadLater()
    with tempfile.TemporaryDirectory() as scratch:
        cross = crossOilTurbidity(later, scratch)
    for run, why in sorted(LATER_SKIPPED.items()):
        print("  [!] %s omitted from the overlay -- %s" % (run, why))
    print("  overlay: n=%d  %s"
          % (len(later), "  ".join("%s Rv %.2f" % (k, later[k]["rv"]) for k in sorted(later))))
    with PdfPages(OUT) as pdf:
        pageSummary(pdf, rows)
        pageStats(pdf, rows)
        pageCurves(pdf, rows)
        pageRvNative(pdf, rows, later, cross)
        pageSecondDerivative(pdf, rows)
        pageSwatches(pdf, rows)
        info = pdf.infodict()
        info["Title"] = "Spectracs session 2026-08-24 — Rv, colour and absorbance"
        info["Subject"] = "3 oils x 3 runs in fresh sunflower; Rv (design-only) beside the shipped Q%"
    print("wrote", OUT)


if __name__ == "__main__":
    main()
