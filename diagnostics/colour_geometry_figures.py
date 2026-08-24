#!/usr/bin/env python3
"""
Figures for the internal *Colour Geometry* discussion document.

    OUTPUT:  docs/figures/colour_*.png
    SOURCE:  spectracs-references/tmp/20260823_newchips/{001_BillaClever,002_Lugitsch}_newchips.pdf
             (the absorbance is read out of the PDF's embedded workflow.json - the SHIPPED artefact,
             so every number in the document is the number the app actually printed)

Every quantity is computed through the SHIPPED code path (`EvaluationColorUtil`), never re-derived
here, so the document cannot drift away from the plugin. The one exception is the deliberately WRONG
"constant-hold" red tail in figure 6, which exists to be refuted.

HOW TO REGENERATE
-----------------
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python diagnostics/colour_geometry_figures.py
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy
import pypdf
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle, Wedge

from colour import (MSDS_CMFS, SDS_ILLUMINANTS, SpectralDistribution, XYZ_to_Lab, XYZ_to_sRGB,
                    XYZ_to_xy, dominant_wavelength, sd_to_XYZ, xyY_to_XYZ)

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "docs", "figures")
RUNS = os.path.abspath(os.path.join(REPO, "..", "spectracs-references", "tmp", "20260823_newchips"))

INK, MUTED, LINE, PANEL = "#1c211c", "#5c655c", "#b9c1b9", "#f5f8f5"
BROWN, GREEN, BLUE, RED, GREY = "#8d5524", "#3f7d3f", "#3a5fa8", "#b03a3a", "#b9bec6"
W = (0.31270, 0.32900)                                   # D65 2 deg white
PATH_CM = 3.0

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 10.5,
                     "axes.titleweight": "bold", "figure.facecolor": "white"})

util = EvaluationColorUtil()
sanitize = util._EvaluationColorUtil__sanitize
cieXy = util._EvaluationColorUtil__cieXy


# --------------------------------------------------------------------------- data

def loadAbsorbance(name):
    reader = pypdf.PdfReader(os.path.join(RUNS, name + ".pdf"))
    workflow = json.loads(reader.attachments["workflow.json"][0])
    for phase in workflow["phases"]:
        for step in (phase.get("steps") or []):
            values = (step.get("spectra") or {}).get("ABSORPTION")
            if values:
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(k): float(v) for k, v in values.items()}
                return spectrum
    raise SystemExit("no ABSORPTION in " + name)


def polar(x, y):
    """Chromaticity in polar coordinates about the D65 white point: (angle deg, radius)."""
    return (math.degrees(math.atan2(y - W[1], x - W[0])) % 360.0, math.hypot(x - W[0], y - W[1]))


def swatch(rgb01):
    return tuple(min(1.0, max(0.0, float(c))) for c in rgb01)


class Oil:
    def __init__(self, key, label, colour, pdfName):
        self.key, self.label, self.colour = key, label, colour
        self.absorbance = loadAbsorbance(pdfName)
        self.clean = sanitize(self.absorbance, util.RELATIVE)
        self.nm = numpy.array(sorted(self.clean))
        self.a = numpy.array([self.clean[n] for n in self.nm])
        self.xy = cieXy(self.clean)
        self.angle, self.radius = polar(*self.xy)
        self.purity = util.spectrumToPurity(self.absorbance, ceiling=util.RELATIVE)
        wavelength, locusXy, _ = dominant_wavelength(list(self.xy), list(W))
        self.domWl = float(wavelength)
        self.locusXy = (float(locusXy[0]), float(locusXy[1]))
        self.locusRadius = math.hypot(self.locusXy[0] - W[0], self.locusXy[1] - W[1])
        self.rawRgb = XYZ_to_sRGB(xyY_to_XYZ([self.xy[0], self.xy[1], 0.5]))
        self.hslIntrinsic = util.spectrumToHsl(self.absorbance, converter="srgb", ceiling=util.RELATIVE)
        self.compXy = (2 * W[0] - self.xy[0], 2 * W[1] - self.xy[1])
        self.compAngle, self.compRadius = polar(*self.compXy)
        self.compRawRgb = XYZ_to_sRGB(xyY_to_XYZ([self.compXy[0], self.compXy[1], 0.5]))
        self.hslComplement = util.complementViaWhitePoint(self.absorbance, ceiling=util.RELATIVE)
        self.lightness, self.chroma, self.hue, self.seenRgb = util.spectrumToLab(
            self.absorbance, path=PATH_CM, ceiling=util.RELATIVE)
        self.reach = util.gamutMapXy(*self.xy)[2]

    def transmittance(self, path=PATH_CM):
        return numpy.minimum(1.0, 10.0 ** (-path * self.a))

    def seen01(self):
        return tuple(c / 255.0 for c in self.seenRgb)


OILS = [Oil("billa", "Billa Clever  (run 001)", BROWN, "001_BillaClever_newchips"),
        Oil("lugitsch", "Lugitsch  (run 002)", GREEN, "002_Lugitsch_newchips")]
BILLA, LUGITSCH = OILS


# --------------------------------------------------------------------------- helpers

def save(figure, name):
    path = os.path.join(OUT, name)
    figure.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print("wrote", os.path.relpath(path, REPO))


def spectrumLocus():
    cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    wavelengths = numpy.arange(390, 701, 1.0)
    points = []
    for nanometer in wavelengths:
        x, y, z = (float(v) for v in cmfs[nanometer])
        total = x + y + z
        points.append((x / total, y / total))
    return wavelengths, numpy.array(points)


def paintDiagram(axes, alpha=1.0):
    """The horseshoe, filled with an sRGB approximation of each chromaticity (clipped, so the
    out-of-gamut interior is only indicative - that limitation is exactly the document's subject)."""
    wavelengths, locus = spectrumLocus()
    resolution = 420
    xs = numpy.linspace(0.0, 0.75, resolution)
    ys = numpy.linspace(0.0, 0.85, resolution)
    grid = numpy.zeros((resolution, resolution, 4))
    path = matplotlib.path.Path(numpy.vstack([locus, locus[:1]]))
    meshX, meshY = numpy.meshgrid(xs, ys)
    inside = path.contains_points(numpy.column_stack([meshX.ravel(), meshY.ravel()])).reshape(meshX.shape)
    safeY = numpy.where(meshY > 1e-6, meshY, 1e-6)
    bigX = meshX / safeY
    bigZ = (1.0 - meshX - meshY) / safeY
    xyz = numpy.dstack([bigX, numpy.ones_like(bigX), bigZ])
    rgb = XYZ_to_sRGB(xyz.reshape(-1, 3)).reshape(resolution, resolution, 3)
    rgb = numpy.clip(rgb / numpy.maximum(1e-6, rgb.max(axis=2, keepdims=True)), 0.0, 1.0)
    grid[..., :3] = rgb
    grid[..., 3] = numpy.where(inside, alpha, 0.0)
    axes.imshow(grid, origin="lower", extent=(0.0, 0.75, 0.0, 0.85), interpolation="bilinear", zorder=0)
    axes.plot(locus[:, 0], locus[:, 1], color=INK, linewidth=1.0, zorder=3)
    axes.plot([locus[0, 0], locus[-1, 0]], [locus[0, 1], locus[-1, 1]], color=INK, linewidth=1.0, zorder=3)
    for nanometer in (430, 460, 480, 500, 520, 540, 560, 580, 600, 640):
        index = int(numpy.argmin(abs(wavelengths - nanometer)))
        px, py = locus[index]
        offset = 0.034
        direction = numpy.array([px - 0.31, py - 0.32])
        direction = direction / numpy.linalg.norm(direction)
        axes.plot([px], [py], marker="o", markersize=2.4, color=INK, zorder=4)
        axes.text(px + offset * direction[0], py + offset * direction[1], "%d" % nanometer,
                  fontsize=6.6, color=MUTED, ha="center", va="center", zorder=4)
    triangle = numpy.array([[0.64, 0.33], [0.30, 0.60], [0.15, 0.06]])
    axes.add_patch(Polygon(triangle, closed=True, fill=False, edgecolor="white",
                           linewidth=1.6, linestyle="--", zorder=3.5))
    axes.set_xlabel("CIE 1931  x"); axes.set_ylabel("CIE 1931  y")
    axes.set_xlim(-0.135, 0.76); axes.set_ylim(-0.01, 0.87)
    axes.set_aspect("equal")


# --------------------------------------------------------------------------- 1. the horseshoe

def figureHorseshoe():
    figure, axes = plt.subplots(figsize=(8.0, 7.2))
    paintDiagram(axes, alpha=0.62)
    axes.plot([W[0]], [W[1]], marker="o", markersize=7, markerfacecolor="white",
              markeredgecolor=INK, markeredgewidth=1.4, zorder=6)
    axes.annotate("D65 white\n$(x_W,\\;y_W)$ = (0.313, 0.329)", xy=W, xytext=(0.372, 0.268),
                  fontsize=8.4, color=INK, ha="left", zorder=6,
                  arrowprops=dict(arrowstyle="-", color=INK, linewidth=0.8))

    for oil in OILS:
        # the whole ray: locus -> sample -> white -> complement
        axes.plot([oil.locusXy[0], oil.compXy[0]], [oil.locusXy[1], oil.compXy[1]],
                  color=oil.colour, linewidth=1.0, linestyle=":", zorder=5)
        axes.plot([oil.locusXy[0]], [oil.locusXy[1]], marker="*", markersize=16, color=oil.colour,
                  markeredgecolor="white", markeredgewidth=0.9, zorder=7)
        axes.plot([oil.xy[0]], [oil.xy[1]], marker="o", markersize=9, color=oil.colour,
                  markeredgecolor="white", markeredgewidth=1.2, zorder=7)
        axes.plot([oil.compXy[0]], [oil.compXy[1]], marker="s", markersize=8, color=oil.colour,
                  markeredgecolor="white", markeredgewidth=1.2, zorder=7)

    # the purity construction, drawn once on Lugitsch (the outer of the two)
    outer = LUGITSCH
    for end_, offset, tint, label in ((outer.xy, 0.020, GREEN, "$r_W$"),
                                      (outer.locusXy, -0.024, MUTED, "$R_W$")):
        direction = numpy.array([end_[0] - W[0], end_[1] - W[1]])
        normal = numpy.array([-direction[1], direction[0]])
        normal = normal / numpy.linalg.norm(normal) * offset
        axes.annotate("", xy=(W[0] + normal[0], W[1] + normal[1]),
                      xytext=(end_[0] + normal[0], end_[1] + normal[1]),
                      arrowprops=dict(arrowstyle="<->", color=tint, linewidth=1.3))
        axes.text(0.5 * (W[0] + end_[0]) + normal[0] * 2.1,
                  0.5 * (W[1] + end_[1]) + normal[1] * 2.1, label, fontsize=11, color=tint,
                  fontweight="bold", ha="center", va="center", zorder=8)

    axes.annotate("Billa Clever\n$r_W$ = 0.242", xy=BILLA.xy, xytext=(-0.128, 0.345),
                  fontsize=8.4, color=BROWN, ha="left", va="top", zorder=7, fontweight="bold",
                  arrowprops=dict(arrowstyle="->", color=BROWN, linewidth=1.0))
    axes.annotate("Lugitsch\n$r_W$ = 0.312", xy=LUGITSCH.xy, xytext=(-0.128, 0.235),
                  fontsize=8.4, color=GREEN, ha="left", va="top", zorder=7, fontweight="bold",
                  arrowprops=dict(arrowstyle="->", color=GREEN, linewidth=1.0))
    axes.annotate("their COMPLEMENTS (reflected through white).\n"
                  "Lugitsch's lies OUTSIDE the locus - $p_e$ = 115 % -\n"
                  "so it is not a colour any eye can receive.",
                  xy=LUGITSCH.compXy, xytext=(0.400, 0.760), fontsize=8.0, color=RED, ha="left",
                  va="top", zorder=7, linespacing=1.5,
                  arrowprops=dict(arrowstyle="->", color=RED, linewidth=1.0))
    axes.text(0.500, 0.352, "sRGB gamut\n(what a screen can show)", fontsize=7.4, color="white",
              ha="center", va="center", zorder=6, fontweight="bold")

    # the two quantities, as one legend block
    axes.add_patch(Rectangle((0.360, 0.010), 0.392, 0.238, facecolor="white", alpha=0.94,
                             edgecolor=LINE, linewidth=0.9, zorder=7))
    axes.text(0.374, 0.236, "$\\bigstar$   $\\lambda_d$   dominant wavelength", fontsize=9.4,
              color=INK, fontweight="bold", va="top", zorder=8)
    axes.text(0.374, 0.199, "where the ray leaves the locus\nBilla 433 nm  ·  Lugitsch 430 nm",
              fontsize=8.0, color=MUTED, va="top", zorder=8, linespacing=1.5)
    axes.text(0.374, 0.130, "$p_e = r_W / R_W$   excitation purity", fontsize=9.4, color=GREEN,
              fontweight="bold", va="top", zorder=8)
    axes.text(0.374, 0.093, "how far out the ray the sample sits\n"
              "Billa      0.242 / 0.352  =  68.7 %\nLugitsch  0.312 / 0.353  =  88.3 %",
              fontsize=8.0, color=MUTED, va="top", zorder=8, linespacing=1.5)
    axes.annotate("", xy=LUGITSCH.locusXy, xytext=(0.360, 0.085),
                  arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=0.9,
                                  connectionstyle="arc3,rad=0.20"), zorder=8)

    axes.set_title("Both oils sit on the SAME ray out of white - only the DISTANCE differs",
                   loc="left", pad=12, fontsize=10.5)
    axes.text(0.0, -0.098, "The two absorbed chromaticities differ by 0.30$\\degree$ of $\\theta_W$ "
              "and by 36 % of $r_W$.\nEvery chromaticity chip reports the direction and discards the "
              "distance.",
              transform=axes.transAxes, fontsize=8.4, color=MUTED, va="top")
    save(figure, "colour_horseshoe.png")


# --------------------------------------------------------------------------- 2. angle vs radius

def figurePolar():
    figure = plt.figure(figsize=(9.4, 3.9))
    left = figure.add_axes([0.035, 0.13, 0.32, 0.66])
    middle = figure.add_axes([0.455, 0.20, 0.21, 0.58])
    right = figure.add_axes([0.775, 0.20, 0.20, 0.58])

    # -- the angle, magnified until the difference is visible at all. ⚠ centre and span are DERIVED, not
    # constants: they were hardcoded for a 0.30 deg gap and the panel broke silently when P1 moved it to 1.33.
    angles = [oil.angle for oil in OILS]
    centre = 0.5 * (min(angles) + max(angles))
    span = max(0.6, 1.5 * (max(angles) - min(angles)))
    left.add_patch(Wedge((0, 0), 1.0, -span, span, facecolor=PANEL, edgecolor=LINE, linewidth=0.8))
    for oil in OILS:
        theta = math.radians((oil.angle - centre) * 1.0)
        left.plot([0, math.cos(theta)], [0, math.sin(theta)], color=oil.colour, linewidth=2.2)
        left.text(1.04, math.sin(theta), "%.2f deg" % oil.angle, color=oil.colour,
                  fontsize=8.6, va="center", fontweight="bold")
    left.plot([0], [0], marker="o", markersize=6, color=INK)
    left.text(-0.06, 0, "D65\nwhite", ha="right", va="center", fontsize=8, color=INK)
    left.set_xlim(-0.35, 1.55); left.set_ylim(-math.radians(span) * 1.35, math.radians(span) * 1.35)
    left.set_yticks([]); left.set_xticks([])
    for spine in left.spines.values():
        spine.set_visible(False)
    left.set_title("a    $\\theta_W$  - the DIRECTION from white", loc="left", pad=26)
    left.text(0.0, 1.10, "KEPT by every chromaticity chip", transform=left.transAxes,
              fontsize=8.6, color=GREEN, fontweight="bold")
    left.text(0.0, -math.radians(span) * 1.20,
              "vertical scale magnified; the true gap is %.2f$\\degree$" % (max(angles) - min(angles)),
              fontsize=7.6, color=MUTED)
    left.annotate("", xy=(1.0, math.radians(BILLA.angle - centre)),
                  xytext=(1.0, math.radians(LUGITSCH.angle - centre)),
                  arrowprops=dict(arrowstyle="<->", color=RED, linewidth=1.3))
    left.text(0.88, 0.0, "%.2f deg" % (max(angles) - min(angles)), color=RED, fontsize=8.4,
              ha="right", va="center", fontweight="bold")

    # -- the radius, at true scale
    for axes, values, title, unit, note in (
            (middle, [oil.radius for oil in OILS], "b    $r_W$  - the DISTANCE", "",
         "in xy units; 36 % apart"),
            (right, [oil.purity for oil in OILS], "c    $p_e$  - PURITY", " %", "$r_W/R_W$, as a percent")):
        bars = axes.bar([0, 1], values, width=0.55, color=[oil.colour for oil in OILS],
                        edgecolor="white", linewidth=1.0)
        for bar, value in zip(bars, values):
            axes.text(bar.get_x() + bar.get_width() / 2, value * 1.02,
                      ("%.3f" % value) if value < 1 else ("%.1f%s" % (value, unit)),
                      ha="center", va="bottom", fontsize=9, fontweight="bold", color=INK)
        axes.set_xticks([0, 1]); axes.set_xticklabels(["Billa", "Lugitsch"], fontsize=8.4)
        axes.set_ylim(0, max(values) * 1.30)
        axes.set_yticks([])
        for side in ("top", "right", "left"):
            axes.spines[side].set_visible(False)
        axes.set_title(title, loc="left", pad=26, fontsize=10)
        axes.text(0.0, 1.115, "THROWN AWAY", transform=axes.transAxes, fontsize=8.6,
                  color=RED, fontweight="bold")
        axes.text(0.0, -0.185, note, transform=axes.transAxes, fontsize=7.6, color=MUTED)
    # ⚠ POINTS, not percent: p_e is already a percentage, so "26 % apart" would be a percentage of a
    # percentage and does not match the table in §2.
    right.text(0.5, 0.30, "%.0f points\napart" % abs(OILS[0].purity - OILS[1].purity),
               transform=right.transAxes, ha="center", fontsize=9.5,
               color=RED, fontweight="bold")
    save(figure, "colour_polar.png")


# --------------------------------------------------------------------------- 2b. seven runs

# Every archived fill of these two oils. Absorbance read from each run's own report PDF, then through
# the shipped EvaluationColorUtil - so the scatter here is fill-to-fill scatter, not method scatter.
ARCHIVE = [
    ("Billa Clever", "20260821BillaCleverA/001.pdf"), ("Billa Clever", "20260821BillaCleverA/002.pdf"),
    ("Billa Clever", "20260822BillaClever/001.pdf"),
    ("Lugitsch", "20260821LugitschA/001.pdf"), ("Lugitsch", "20260821LugitschA/002.pdf"),
    ("Lugitsch", "20260822Lugitsch/002.pdf"), ("Lugitsch", "20260822Lugitsch/003.pdf"),
]
ARCHIVE_ROOT = os.path.abspath(os.path.join(REPO, "..", "spectracs-references", "tmp"))


def archiveMeasurements():
    from colour import dominant_wavelength as domWl, excitation_purity as purity
    out = {}
    for oil, relative in ARCHIVE:
        reader = pypdf.PdfReader(os.path.join(ARCHIVE_ROOT, relative))
        workflow = json.loads(reader.attachments["workflow.json"][0])
        values = None
        for phase in workflow["phases"]:
            for step in (phase.get("steps") or []):
                values = (step.get("spectra") or {}).get("ABSORPTION") or values
        spectrum = Spectrum()
        spectrum.valuesByNanometers = {float(k): float(v) for k, v in values.items()}
        x, y = cieXy(sanitize(spectrum, util.RELATIVE))
        out.setdefault(oil, []).append((float(domWl([x, y], list(W))[0]),
                                        float(purity([x, y], list(W))) * 100.0))
    return out


SWEEP_CSV = os.path.join(ARCHIVE_ROOT, "dominant_wavelength_archive.csv")


def sweepRows():
    """The 88 labelled isopropanol runs, from `diagnostics/dominant_wavelength_archive.py`'s CSV.
    Classification (green / brown / excluded) is `peak_ratio_archive`'s, unchanged."""
    import csv
    import peak_ratio_archive as harness
    rows = []
    with open(SWEEP_CSV) as handle:
        for row in csv.DictReader(handle):
            label = harness.classOf(row)
            if label not in ("green", "brown"):
                continue
            for key in ("wlo", "wlHeld", "peHeld", "wlPad", "pePad"):
                row[key] = float(row[key])
            row["class"] = label
            rows.append(row)
    return rows


def strip(panel, groups, index, fmt, unit, separates):
    """One two-row strip plot: each fill a dot, the class range a bar, and the gap or overlap marked."""
    for oil, tint, y, values in groups:
        values = sorted(values)
        panel.plot([min(values), max(values)], [y, y], color=tint, linewidth=6, alpha=0.22,
                   solid_capstyle="round")
        panel.plot(values, [y] * len(values), marker="o", markersize=7, linestyle="none",
                   color=tint, markeredgecolor="white", markeredgewidth=1.0, alpha=0.85)
        panel.text(numpy.mean(values), y + (0.30 if y > 0.5 else -0.30),
                   "%s   n = %d\n" % (oil, len(values))
                   + ("mean " + fmt + " \u00b1 " + fmt) % (numpy.mean(values),
                                                           numpy.std(values, ddof=1)),
                   ha="center", va="bottom" if y > 0.5 else "top", fontsize=8.2,
                   color=tint, fontweight="bold", linespacing=1.6)
    first = sorted(groups[0][3])
    second = sorted(groups[1][3])
    low, high = (max(second), min(first)) if separates else (max(first), min(second))
    panel.axvspan(min(low, high), max(low, high), color=GREEN if separates else RED,
                  alpha=0.16, zorder=0)
    panel.annotate("", xy=(low, 0.5), xytext=(high, 0.5),
                   arrowprops=dict(arrowstyle="<->", color=GREEN if separates else RED, linewidth=1.4))
    panel.text(0.5 * (low + high), 0.60,
               ("a clear %.0f %s gap" % (abs(high - low), unit)) if separates
               else "they OVERLAP", ha="center", va="bottom", fontsize=8.8, fontweight="bold",
               color=GREEN if separates else RED, linespacing=1.4)
    allValues = [v for _, _, _, values in groups for v in values]
    span = max(allValues) - min(allValues)
    panel.set_xlim(min(allValues) - 0.14 * span, max(allValues) + 0.14 * span)
    panel.set_ylim(-1.05, 1.85)
    panel.set_yticks([])
    for side in ("top", "right", "left"):
        panel.spines[side].set_visible(False)


def figureArchive():
    seven = archiveMeasurements()
    sweep = sweepRows()
    figure = plt.figure(figsize=(11.0, 6.6))
    top = figure.add_axes([0.045, 0.605, 0.415, 0.300])
    middle = figure.add_axes([0.545, 0.605, 0.430, 0.300])
    bottom = figure.add_axes([0.045, 0.115, 0.930, 0.330])

    strip(top, [("Billa Clever", BROWN, 1.0, [v[0] for v in seven["Billa Clever"]]),
                ("Lugitsch", GREEN, 0.0, [v[0] for v in seven["Lugitsch"]])],
          0, "%.0f", "nm", True)
    top.set_xlabel("nm")
    top.set_title("a    the claim: seven sunflower fills, two oils", loc="left", pad=10)

    strip(middle, [("brown oils", BROWN, 1.0, [r["wlPad"] for r in sweep if r["class"] == "brown"]),
                   ("green oils", GREEN, 0.0, [r["wlPad"] for r in sweep if r["class"] == "green"])],
          0, "%.1f", "nm", False)
    middle.set_xlabel("nm")
    middle.set_title("b    the test: 88 labelled isopropanol runs", loc="left", pad=10)

    for label, tint in (("green", GREEN), ("brown", BROWN)):
        subset = [r for r in sweep if r["class"] == label]
        bottom.plot([r["wlo"] for r in subset], [r["wlPad"] for r in subset], marker="o",
                    markersize=6, linestyle="none", color=tint, markeredgecolor="white",
                    markeredgewidth=0.8, alpha=0.85, label="%s oils" % label)
    wlo = numpy.array([r["wlo"] for r in sweep])
    wl = numpy.array([r["wlPad"] for r in sweep])
    slope, intercept = numpy.polyfit(wlo, wl, 1)
    line = numpy.array([wlo.min() - 1, wlo.max() + 1])
    bottom.plot(line, slope * line + intercept, color=INK, linewidth=1.2, linestyle="--")
    bottom.text(0.985, 0.115, "r = %.3f" % numpy.corrcoef(wlo, wl)[0, 1], transform=bottom.transAxes,
                ha="right", fontsize=12, color=RED, fontweight="bold")
    bottom.set_xlabel("$\\lambda$ of the FIRST measured sample   (the blue edge of the capture) / nm")
    bottom.set_ylabel("$\\lambda_d$ / nm")
    bottom.legend(frameon=False, fontsize=8.2, loc="upper left")
    for side in ("top", "right"):
        bottom.spines[side].set_visible(False)
    bottom.set_title("c    and why: $\\lambda_d$ reports where the MEASUREMENT starts, not what is "
                     "in the jar", loc="left", pad=10)
    bottom.text(0.0, -0.30, "The two oils' fills happened to start at different wavelengths - Billa "
                "424 and 426 nm, Lugitsch 417 and 421 - and $\\lambda_d$ followed. Within the 60 "
                "runs that share\none capture span it separates at $d$ = -0.06. The gap in panel a "
                "is the coverage ordering, not the oil.",
                transform=bottom.transAxes, fontsize=8.4, color=RED, va="top", linespacing=1.55)
    save(figure, "colour_archive.png")


# --------------------------------------------------------------------------- 3. clipping

def figureClipping():
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(9.6, 7.4),
                                         gridspec_kw={"height_ratios": [1.25, 1.0], "hspace": 0.92})
    cases = [
        (top, "a   the `Absorbed` chips  -  the absorbed chromaticity, rendered at Y = 0.5",
         [(oil, oil.rawRgb, oil.hslIntrinsic) for oil in OILS],
         "Lugitsch's green channel wants to be -9.37. Clamped to 0 it becomes pure magenta #ff00ff:\n"
         "a gamut artefact with the shape of a measurement. Its hue of exactly 300.00 deg is not a\n"
         "property of the oil - it is the corner of the cube the arithmetic fell off."),
        (bottom, "b   the `Absorbed-complement` chips  -  the complement, rendered at Y = 0.5",
         [(oil, oil.compRawRgb, oil.hslComplement) for oil in OILS],
         "Both complements are outside sRGB (blue -0.574 and -1.650). Clamping projects them onto the\n"
         "same face of the gamut, which is why 1.33 deg of real angle arrives as a 2.68 deg difference\n"
         "in reported hue."),
    ]
    positions = [0, 1, 2, 4, 5, 6]
    for axes, title, rows, caption in cases:
        values, colours = [], []
        for oil, raw, hsl in rows:
            for channel, tint in zip(raw, ("#c0392b", "#27ae60", "#2c6fbb")):
                values.append(float(channel))
                colours.append(tint)
        low = min(-0.95, min(values) * 1.16)
        high = max(2.05, max(values) * 1.22)
        span = high - low
        axes.axhspan(low, 0.0, color=RED, alpha=0.07, zorder=0)
        axes.axhspan(1.0, high, color=RED, alpha=0.07, zorder=0)
        axes.axhline(0.0, color=MUTED, linewidth=0.9)
        axes.axhline(1.0, color=MUTED, linewidth=0.9, linestyle="--")
        axes.bar(positions, values, width=0.68, color=colours, edgecolor="white", linewidth=1.0)
        for position, value in zip(positions, values):
            axes.text(position, value + (0.018 if value >= 0 else -0.020) * span, "%.3f" % value,
                      ha="center", va="bottom" if value >= 0 else "top", fontsize=8.2,
                      fontweight="bold", color=RED if (value < 0 or value > 1) else INK)
        axes.set_xticks(positions)
        axes.set_xticklabels(["R", "G", "B", "R", "G", "B"], fontsize=8.8)
        axes.set_xlim(-0.75, 7.0)
        axes.set_ylim(low, high)
        axes.set_ylabel("linear sRGB channel")
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        axes.set_title(title, loc="left", pad=10)
        for centre, oil in ((1.0, OILS[0]), (5.0, OILS[1])):
            axes.annotate("", xy=(centre - 1.35, -0.115), xytext=(centre + 1.35, -0.115),
                          xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                          arrowprops=dict(arrowstyle="-", color=oil.colour, linewidth=1.1))
            axes.text(centre, -0.155, oil.label.split("  ")[0], transform=axes.get_xaxis_transform(),
                      ha="center", va="top", fontsize=9, color=oil.colour, fontweight="bold")
        axes.text(6.92, 1.0 + 0.022 * span, "clamped to 1", fontsize=7.6, color=RED,
                  va="bottom", ha="right")
        axes.text(6.92, -0.030 * span, "clamped to 0", fontsize=7.6, color=RED, va="top", ha="right")
        for index, (oil, raw, hsl) in enumerate(rows):
            y = low + span * (0.68 - 0.38 * index)
            axes.add_patch(Rectangle((7.25, y), 0.85, span * 0.26, facecolor=swatch(raw),
                                     edgecolor=INK, linewidth=0.8, clip_on=False))
            axes.text(8.28, y + span * 0.175, "H %.2f deg" % hsl[0], fontsize=8.6, va="center",
                      fontweight="bold", color=INK, clip_on=False)
            axes.text(8.28, y + span * 0.085, "S %.0f %%   L %.0f %%" % (hsl[1], hsl[2]),
                      fontsize=8.0, va="center", color=MUTED, clip_on=False)
            axes.text(8.28, y + span * 0.255, oil.label.split("  ")[0], fontsize=7.8, va="bottom",
                      color=oil.colour, fontweight="bold", clip_on=False)
        axes.text(0.0, -0.345, caption, transform=axes.transAxes, fontsize=8.4, color=RED,
                  va="top", linespacing=1.5)
    save(figure, "colour_clipping.png")


# --------------------------------------------------------------------------- 4. what LCh is

def figureLch():
    figure = plt.figure(figsize=(9.4, 4.6))
    wheel = figure.add_axes([0.02, 0.06, 0.42, 0.86])
    bars = figure.add_axes([0.545, 0.16, 0.42, 0.70])

    resolution = 300
    grid = numpy.zeros((resolution, resolution, 4))
    axis = numpy.linspace(-80, 80, resolution)
    aa, bb = numpy.meshgrid(axis, axis)
    lab = numpy.dstack([numpy.full_like(aa, 72.0), aa, bb])
    from colour import Lab_to_XYZ
    rgb = XYZ_to_sRGB(Lab_to_XYZ(lab.reshape(-1, 3), W).reshape(resolution, resolution, 3))
    grid[..., :3] = numpy.clip(rgb, 0, 1)
    grid[..., 3] = numpy.where(numpy.hypot(aa, bb) <= 78, 1.0, 0.0)
    wheel.imshow(grid, origin="lower", extent=(-80, 80, -80, 80), interpolation="bilinear")
    wheel.add_patch(Circle((0, 0), 78, fill=False, edgecolor=INK, linewidth=1.0))
    for angle, name in ((0, "0 deg  red"), (90, "90 deg  yellow"), (180, "180 deg  green"),
                        (270, "270 deg  blue")):
        theta = math.radians(angle)
        wheel.plot([0, 78 * math.cos(theta)], [0, 78 * math.sin(theta)], color="white",
                   linewidth=0.8, alpha=0.75)
        wheel.text(92 * math.cos(theta), 92 * math.sin(theta), name, fontsize=8.2, color=INK,
                   ha="center", va="center", fontweight="bold")
    for oil in OILS:
        theta = math.radians(oil.hue)
        wheel.plot([0, oil.chroma * math.cos(theta)], [0, oil.chroma * math.sin(theta)],
                   color=INK, linewidth=1.6)
        wheel.plot([oil.chroma * math.cos(theta)], [oil.chroma * math.sin(theta)], marker="o",
                   markersize=11, markerfacecolor=oil.seen01(), markeredgecolor=INK,
                   markeredgewidth=1.3, zorder=5)
    for index, oil in enumerate(OILS):
        y = -108 - 18 * index
        wheel.add_patch(Rectangle((-96, y - 6), 15, 13, facecolor=oil.seen01(), edgecolor=INK,
                                  linewidth=0.8, clip_on=False))
        wheel.text(-75, y, "%-9s C* %2.0f    h %3.0f deg" % (oil.label.split("  ")[0],
                   oil.chroma, oil.hue), fontsize=8.6, va="center", color=INK, fontweight="bold")
    wheel.set_xlim(-105, 105); wheel.set_ylim(-142, 105)
    wheel.set_aspect("equal"); wheel.axis("off")
    wheel.set_title("a    $h_{ab}$ and $C^{*}_{ab}$ live in the $a^{*}b^{*}$ plane   (at $L^{*}$ = 72)", loc="left", pad=6)

    values = [(oil.lightness, oil.chroma, oil.hue) for oil in OILS]
    names = ["L*\nlightness\n0 black .. 100 white", "C*\nchroma\n0 grey .. ~130 vivid",
             "h\nhue angle\ndegrees"]
    for column in range(3):
        offsets = [column - 0.17, column + 0.17]
        heights = [values[0][column], values[1][column]]
        scale = 130.0 if column < 2 else 360.0
        bars.bar(offsets, [h / scale * 100 for h in heights], width=0.30,
                 color=[oil.colour for oil in OILS], edgecolor="white", linewidth=1.0)
        for offset, height in zip(offsets, heights):
            bars.text(offset, height / scale * 100 + 1.6, "%.0f" % height, ha="center",
                      fontsize=9, fontweight="bold", color=INK)
    bars.set_xticks([0, 1, 2]); bars.set_xticklabels(names, fontsize=7.9, linespacing=1.5)
    bars.set_yticks([]); bars.set_ylim(0, 105)
    for side in ("top", "right", "left"):
        bars.spines[side].set_visible(False)
    bars.set_title("b   the three numbers on the 'As seen' chip", loc="left", pad=10)
    bars.text(0.0, -0.300, "Bars are scaled to each axis's own range, so compare within a group, "
              "not across.\nL* and C* are perceptually spaced - unlike HSL's L and S, which are "
              "display-space conveniences.",
              transform=bars.transAxes, fontsize=8.2, color=MUTED, va="top")
    save(figure, "colour_lch.png")


# --------------------------------------------------------------------------- 5. the path

def figurePath():
    figure, axes = plt.subplots(1, 3, figsize=(10.8, 3.7),
                                gridspec_kw={"width_ratios": [1.15, 1.15, 0.72], "wspace": 0.30})
    for oil in OILS:
        axes[0].plot(oil.nm, oil.a, color=oil.colour, linewidth=1.5, label=oil.label)
        axes[1].plot(oil.nm, oil.transmittance(), color=oil.colour, linewidth=1.5)
    axes[0].set_title("a    absorbance  $A(\\lambda)$", loc="left", pad=8)
    axes[0].set_xlabel("wavelength / nm"); axes[0].set_ylabel("A")
    axes[0].legend(frameon=False, fontsize=7.8, loc="upper right")
    axes[0].text(0.30, 0.86, "the 420 - 450 nm Soret band dominates\nBOTH curves - which is why both\n"
                 "point the SAME way out of white", transform=axes[0].transAxes,
                 fontsize=8.0, color=MUTED, fontweight="bold", va="top", linespacing=1.45)
    axes[0].text(0.30, 0.40, "Lugitsch carries relatively less\nabsorbance outside the Soret -\n"
                 "that, and only that, is its higher purity",
                 transform=axes[0].transAxes, fontsize=8.0, color=GREEN, fontweight="bold",
                 va="top", linespacing=1.45)
    axes[1].set_title("b    at $k$ = 3:   $T = 10^{-kA}$", loc="left", pad=8)
    axes[1].set_xlabel("wavelength / nm"); axes[1].set_ylabel("T")
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].text(0.04, 0.955, "3 cm of liquid separates them\nacross the whole visible band",
                 transform=axes[1].transAxes, fontsize=8.2, color=RED, fontweight="bold",
                 va="top", linespacing=1.45)
    for panel in axes[:2]:
        for side in ("top", "right"):
            panel.spines[side].set_visible(False)

    axes[2].axis("off")
    axes[2].set_title("c   what you see", loc="left", pad=8)
    for index, oil in enumerate(OILS):
        y = 0.68 - 0.44 * index
        axes[2].add_patch(Rectangle((0.02, y), 0.40, 0.30, transform=axes[2].transAxes,
                                    facecolor=oil.seen01(), edgecolor=INK, linewidth=0.9))
        axes[2].text(0.47, y + 0.215, oil.label.split("  ")[0], transform=axes[2].transAxes,
                     fontsize=8.8, fontweight="bold", color=oil.colour)
        axes[2].text(0.47, y + 0.115, "L* %.0f   C* %.0f" % (oil.lightness, oil.chroma),
                     transform=axes[2].transAxes, fontsize=8.2, color=INK)
        axes[2].text(0.47, y + 0.025, "h %.0f deg" % oil.hue, transform=axes[2].transAxes,
                     fontsize=8.2, color=INK)
    axes[2].text(0.02, 0.06, "30 deg of hue apart,\nagainst 1.33 deg for the\ninvariant chips.",
                 transform=axes[2].transAxes, fontsize=8.4, color=RED, fontweight="bold", va="top")
    save(figure, "colour_path.png")


# --------------------------------------------------------------------------- 6. the reference

def figureReference():
    """Why T = S/R needs no standardised reference - and what that costs the chip.

    ⚠ The 'what the tube shows' swatch is deliberately EMPTY: the solvent's own absorbance was never
    measured (it would need a blank-against-air capture), so there is no honest colour to draw there."""
    figure, axes = plt.subplots(figsize=(10.8, 6.0))
    axes.set_xlim(0, 1); axes.set_ylim(0, 1); axes.axis("off")

    def lamp(x, y):
        axes.add_patch(Circle((x, y), 0.021, facecolor="#ffe9a8", edgecolor=MUTED, linewidth=1.0))
        for angle in range(0, 360, 45):
            theta = math.radians(angle)
            axes.plot([x + 0.026 * math.cos(theta), x + 0.036 * math.cos(theta)],
                      [y + 0.026 * 1.72 * math.sin(theta), y + 0.036 * 1.72 * math.sin(theta)],
                      color="#d8a83a", linewidth=0.9)

    def jar(x, y, fill, label):
        axes.add_patch(Rectangle((x, y - 0.055), 0.062, 0.110, facecolor=fill, edgecolor=INK,
                                 linewidth=1.1))
        axes.text(x + 0.031, y - 0.072, label, ha="center", va="top", fontsize=7.8, color=INK)

    def camera(x, y):
        axes.add_patch(Rectangle((x, y - 0.036), 0.052, 0.072, facecolor=PANEL, edgecolor=MUTED,
                                 linewidth=1.1))
        axes.add_patch(Circle((x + 0.026, y), 0.019, facecolor="#3a3f3a", edgecolor=INK, linewidth=0.9))

    def beam(x0, x1, y):
        axes.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=11,
                                       color="#d8a83a", linewidth=1.6, shrinkA=0, shrinkB=0))

    rows = [(0.815, "#f2e39a", "solvent only", "REFERENCE   R", MUTED),
            (0.655, "#b9a545", "solvent + pumpkin oil", "SAMPLE   S", BROWN)]
    for y, fill, jarLabel, rowLabel, tint in rows:
        axes.text(0.005, y + 0.056, rowLabel, fontsize=9.2, fontweight="bold", color=tint)
        lamp(0.130, y)
        beam(0.172, 0.244, y)
        jar(0.248, y, fill, jarLabel)
        beam(0.316, 0.386, y)
        camera(0.390, y)
    axes.add_patch(FancyArrowPatch((0.470, 0.815), (0.556, 0.775), arrowstyle="-|>",
                                   mutation_scale=12, color=MUTED, linewidth=1.2))
    axes.add_patch(FancyArrowPatch((0.470, 0.655), (0.556, 0.705), arrowstyle="-|>",
                                   mutation_scale=12, color=MUTED, linewidth=1.2))

    box(axes, 0.560, 0.665, 0.185, 0.170, "T = S / R", "A = \u2212log\u2081\u2080(S/R)",
        "#eef3fb", BLUE, BLUE, fontsize=9.0)
    axes.text(0.765, 0.820, "the ratio CANCELS", fontsize=8.6, fontweight="bold", color=GREEN)
    for index, item in enumerate(("the lamp spectrum", "the jar glass",
                                  "the solvent's own absorbance", "the camera response")):
        axes.text(0.765, 0.784 - 0.031 * index, "\u2713  " + item, fontsize=8.2, color=INK)

    axes.plot([0.0, 1.0], [0.530, 0.530], color=LINE, linewidth=0.9)
    axes.text(0.005, 0.487, "\u21d2 what the ratio leaves in the picture",
              fontsize=9.6, fontweight="bold", color=INK)

    axes.add_patch(Rectangle((0.030, 0.215), 0.415, 0.235, facecolor="white", edgecolor=BROWN,
                             linewidth=1.2))
    axes.text(0.052, 0.415, "the chip renders", fontsize=9.0, fontweight="bold", color=BROWN)
    axes.text(0.052, 0.372, "D65   \u00d7   T\u00b3", fontsize=10.5, color=INK)
    axes.add_patch(Rectangle((0.320, 0.255), 0.100, 0.140, facecolor=BILLA.seen01(),
                             edgecolor=INK, linewidth=0.9))
    axes.text(0.052, 0.332, "the pumpkin oil's EXCESS\ncolour over the solvent",
              fontsize=8.2, color=MUTED, va="top", linespacing=1.5)
    axes.text(0.052, 0.233, "Billa Clever, #a48e5b", fontsize=7.8, color=MUTED)

    axes.add_patch(Rectangle((0.500, 0.215), 0.470, 0.235, facecolor="white", edgecolor=MUTED,
                             linewidth=1.2, linestyle="--"))
    axes.text(0.522, 0.415, "the tube actually shows", fontsize=9.0, fontweight="bold", color=MUTED)
    axes.text(0.522, 0.372, "D65   \u00d7   (solvent)\u00b3   \u00d7   T\u00b3", fontsize=10.5, color=INK)
    axes.add_patch(Rectangle((0.845, 0.255), 0.100, 0.140, facecolor="white", edgecolor=MUTED,
                             linewidth=0.9, linestyle="--"))
    axes.text(0.895, 0.325, "?", fontsize=17, color=MUTED, ha="center", va="center")
    axes.text(0.522, 0.332, "never measured - it would need a\nblank-against-air capture",
              fontsize=8.2, color=MUTED, va="top", linespacing=1.5)

    axes.text(0.0, 0.995, "The reference is the illuminant", fontsize=11.5,
              fontweight="bold", va="top")
    axes.text(0.0, 0.155, "Runs 001 and 002 used SUNFLOWER OIL as the solvent, and sunflower "
              "oil is visibly yellow. Its colour divided out with everything\nelse the ratio cancels. "
              "Against isopropanol - colourless in the visible - the two boxes above nearly coincide; "
              "against sunflower oil they\ndo not. Both are legitimate answers to different questions, "
              "and one label is currently doing duty for both.",
              fontsize=8.6, color=RED, va="top", linespacing=1.55)
    save(figure, "colour_reference.png")


# --------------------------------------------------------------------------- 6. the red tail

def redTailVariants(oil):
    """Billa rendered at 3 cm under the two ways of filling the un-measured 636-780 nm."""
    cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    illuminant = SDS_ILLUMINANTS["D65"]
    transmittance = numpy.minimum(1.0, 10.0 ** (-PATH_CM * oil.a))
    out = {}
    for name in ("transparent", "hold"):
        dense = {}
        for nanometer in cmfs.wavelengths:
            nanometer = float(nanometer)
            if nanometer < oil.nm[0]:
                dense[nanometer] = transmittance[0] if name == "hold" else 1.0
            elif nanometer > oil.nm[-1]:
                dense[nanometer] = transmittance[-1] if name == "hold" else 1.0
            else:
                dense[nanometer] = float(numpy.interp(nanometer, oil.nm, transmittance))
        distribution = SpectralDistribution(dense).align(cmfs.shape)
        xyz = sd_to_XYZ(distribution, cmfs, illuminant, method="Integration") / 100.0
        lab = XYZ_to_Lab(xyz, W)
        lightness, a, b = (float(v) for v in lab)
        out[name] = (lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0,
                     swatch(XYZ_to_sRGB(xyz, W)), dense)
    return out


def figureRedTail():
    variants = redTailVariants(BILLA)
    figure, (left, right) = plt.subplots(1, 2, figsize=(10.4, 3.9),
                                         gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.24})
    grid = sorted(variants["hold"][4])
    left.axvspan(BILLA.nm[0], BILLA.nm[-1], color=GREEN, alpha=0.09, zorder=0)
    left.plot(grid, [variants["hold"][4][n] for n in grid], color=RED, linewidth=1.6,
              label="'hold the last sample'  (colour.align's default)")
    left.plot(grid, [variants["transparent"][4][n] for n in grid], color=BLUE, linewidth=1.6,
              linestyle="--", label="'transparent above 636 nm'  (what we ship)")
    left.axvline(BILLA.nm[-1], color=INK, linewidth=0.9, linestyle=":")
    left.text(BILLA.nm[-1] + 4, 0.06, "636 nm - last measured sample", fontsize=7.8, color=INK,
              rotation=90, va="bottom")
    left.text((BILLA.nm[0] + BILLA.nm[-1]) / 2, 1.05, "MEASURED", ha="center", fontsize=8.2,
              color=GREEN, fontweight="bold")
    left.text(708, 1.05, "40 % of the visible red - INVENTED", ha="center", fontsize=8.2,
              color=RED, fontweight="bold")
    left.set_xlim(360, 780); left.set_ylim(-0.03, 1.16)
    left.set_xlabel("wavelength / nm"); left.set_ylabel("T at 3 cm")
    left.legend(frameon=False, fontsize=7.8, loc="lower left")
    left.set_title("a   the un-measured red is not a rounding error", loc="left", pad=8)
    for side in ("top", "right"):
        left.spines[side].set_visible(False)

    right.axis("off")
    right.set_title("b   and it decides the answer", loc="left", pad=8)
    rows = [("'hold'", variants["hold"], RED),
            ("'transparent'", variants["transparent"], BLUE),
            ("photographed", None, INK)]
    for index, (name, data, tint) in enumerate(rows):
        y = 0.79 - 0.235 * index
        if data is None:
            right.add_patch(Rectangle((0.03, y), 0.26, 0.17, transform=right.transAxes,
                                      facecolor="none", edgecolor=LINE, linewidth=0.9,
                                      linestyle="--"))
            right.text(0.16, y + 0.085, "phone", transform=right.transAxes, ha="center",
                       va="center", fontsize=7.6, color=MUTED)
            hue = "90.1 deg  +/- 3.5"
        else:
            right.add_patch(Rectangle((0.03, y), 0.26, 0.17, transform=right.transAxes,
                                      facecolor=data[3], edgecolor=INK, linewidth=0.9))
            hue = "%.1f deg" % data[2]
        right.text(0.34, y + 0.112, name, transform=right.transAxes, fontsize=8.8,
                   fontweight="bold", color=tint)
        right.text(0.34, y + 0.028, "hue " + hue, transform=right.transAxes, fontsize=8.4, color=INK)
    right.text(0.03, 0.215, "'hold' extrapolates the falling flank of the 624 nm\nband flat to 780 nm "
               "and renders Billa OLIVE-GREEN.\nIt inverts the visual ordering of the two oils.\n"
               "The photograph, taken afterwards, could have\nrefuted the fix. It confirmed it to "
               "within 2 deg.",
               transform=right.transAxes, fontsize=8.0, color=MUTED, va="top")
    save(figure, "colour_redtail.png")


# --------------------------------------------------------------------------- 7. what each chip drops

def box(axes, x, y, width, height, title, body, face, edge, titleColour=None, fontsize=8.2):
    axes.add_patch(Rectangle((x, y), width, height, facecolor=face, edgecolor=edge,
                             linewidth=1.2, zorder=2))
    axes.text(x + width / 2, y + height - 0.048, title, ha="center", va="top", fontsize=fontsize + 0.7,
              fontweight="bold", color=titleColour or INK, zorder=3)
    axes.text(x + width / 2, y + height * 0.44, body, ha="center", va="top", fontsize=fontsize,
              color=INK, zorder=3, linespacing=1.5)


def arrow(axes, start, end, label=None, colour=None):
    axes.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                                   color=colour or MUTED, linewidth=1.3, zorder=2,
                                   shrinkA=1, shrinkB=1))
    midX, midY = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    if label:
        axes.text(midX, midY + 0.022, label, ha="center", va="bottom", fontsize=7.8, color=MUTED)



def figureFamily():
    figure, axes = plt.subplots(figsize=(10.8, 5.6))
    axes.set_xlim(0, 1); axes.set_ylim(0, 1); axes.axis("off")

    box(axes, 0.005, 0.415, 0.215, 0.215, "absorbance  A(\u03bb)",
        "the measurement\n420 - 636 nm", PANEL, MUTED, fontsize=8.4)

    box(axes, 0.285, 0.610, 0.215, 0.215, "chromaticity  x, y",
        "drop luminance\n\u21d2 dilution-invariant", "#eef3fb", BLUE, BLUE, fontsize=8.4)
    box(axes, 0.285, 0.120, 0.215, 0.215, "transmittance at 3 cm",
        "T = 10\u207b\u00b3\u1d2c\nkeep luminance", "#fdf3e8", BROWN, BROWN, fontsize=8.4)

    box(axes, 0.565, 0.745, 0.195, 0.180, "angle  (hue)", "0.30\u00b0 apart", "white", BLUE, BLUE)
    box(axes, 0.565, 0.510, 0.195, 0.180, "radius  (purity)", "$p_e$ and $\\lambda_d$", "white", GREEN, GREEN)
    box(axes, 0.565, 0.135, 0.195, 0.190, "L*   C*   h",
        "30\u00b0 of hue\n29 points of L*", "white", BROWN, BROWN)

    box(axes, 0.795, 0.745, 0.200, 0.180, "the hue readout", "$\\theta_W$ - near-constant\non this pigment",
        "white", LINE, MUTED)
    box(axes, 0.795, 0.510, 0.200, 0.180, "'Absorbed \u00b7 purity'", "one row - and it\noverlaps (\u00a72.1)",
        "white", GREEN, GREEN)
    box(axes, 0.795, 0.135, 0.200, 0.190, "'\u00d73 path'", "the chip that\nmatches the eye",
        "white", BROWN, BROWN)

    arrow(axes, (0.220, 0.560), (0.285, 0.690), colour=BLUE)
    arrow(axes, (0.220, 0.480), (0.285, 0.260), colour=BROWN)
    arrow(axes, (0.500, 0.760), (0.565, 0.820), colour=BLUE)
    arrow(axes, (0.500, 0.690), (0.565, 0.610), colour=GREEN)
    arrow(axes, (0.500, 0.228), (0.565, 0.228), colour=BROWN)
    arrow(axes, (0.760, 0.835), (0.795, 0.835), colour=MUTED)
    arrow(axes, (0.760, 0.600), (0.795, 0.600), colour=GREEN)
    arrow(axes, (0.760, 0.228), (0.795, 0.228), colour=BROWN)

    axes.text(0.278, 0.664, "DISCARDS\nconcentration", fontsize=7.8, color=RED, ha="right",
              va="bottom", fontweight="bold")
    axes.text(0.278, 0.318, "KEEPS\nconcentration", fontsize=7.8, color=GREEN, ha="right",
              va="top", fontweight="bold")
    axes.text(0.532, 0.578, "the radius is\ndropped here", fontsize=7.6, color=RED, ha="center",
              va="top", fontweight="bold")

    axes.text(0.0, 0.995, "The family tree: every chip is a choice about what to throw away",
              fontsize=11.5, fontweight="bold", va="top")
    axes.text(0.0, 0.062, "Dilution-invariance and discriminating power are the SAME property seen "
              "from two sides. A chip that cannot be fooled by dilution\ncannot be moved by "
              "concentration either - and on two oils of one pigment family, concentration is most "
              "of the difference.",
              fontsize=8.6, color=INK, va="top", linespacing=1.5)
    save(figure, "colour_family.png")


# --------------------------------------------------------------------------- numbers for the prose

def dumpNumbers():
    print("\n--- numbers used in DOC_colour_geometry.md ---")
    for oil in OILS:
        print("%-10s xy %.5f %.5f | angle %.2f | radius %.4f | purity %.1f | domWl %.0f | reach %.3f"
              % (oil.key, oil.xy[0], oil.xy[1], oil.angle, oil.radius, oil.purity, oil.domWl, oil.reach))
        print("           intrinsic H %.2f S %.1f L %.1f | raw sRGB %s"
              % (oil.hslIntrinsic + (["%.3f" % float(c) for c in oil.rawRgb],)))
        print("           complement H %.2f S %.1f L %.1f | raw sRGB %s"
              % (oil.hslComplement + (["%.3f" % float(c) for c in oil.compRawRgb],)))
        print("           as seen L* %.1f C* %.1f h %.1f rgb %s  #%02x%02x%02x"
              % ((oil.lightness, oil.chroma, oil.hue, oil.seenRgb) + tuple(oil.seenRgb)))
    print("angle gap  %.2f deg | radius gap %.1f %% | hue-norm gap %.2f deg | as-seen hue gap %.1f deg"
          % (abs(BILLA.angle - LUGITSCH.angle),
             100.0 * abs(BILLA.radius - LUGITSCH.radius) / BILLA.radius,
             abs(BILLA.hslComplement[0] - LUGITSCH.hslComplement[0]),
             abs(BILLA.hue - LUGITSCH.hue)))
    variants = redTailVariants(BILLA)
    for name in ("hold", "transparent"):
        lightness, chroma, hue, rgb, _ = variants[name]
        print("billa red-tail %-12s L* %.1f C* %.1f h %.1f  #%02x%02x%02x"
              % ((name, lightness, chroma, hue) + tuple(int(round(c * 255)) for c in rgb)))


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    figureHorseshoe()
    figurePolar()
    figureArchive()
    figureClipping()
    figureLch()
    figurePath()
    figureReference()
    figureRedTail()
    figureFamily()
    dumpNumbers()


if __name__ == "__main__":
    main()
