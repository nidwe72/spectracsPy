"""SNV spectra 448 nm -> the red peak, ALIGNED AT 580 nm. (Edwin's request 2026-08-21)

Edwin marked four features on a white-spirit trace and asked what the relations between them mean:

    (3) ~568 nm      (1) ~574 nm      (4) ~580 nm      (2) ~624 nm

and asked for the SNV'd spectra aligned at (4) to see whether that shows something. It does, and the
first thing it shows is that ONE OF THE FOUR IS NOT A BAND.

⛔⛔ (4) IS AN INSTRUMENT ARTIFACT — the 581 nm channel crossover. Measured on the REFERENCE trace of
four runs spanning both solvents and both rig eras, each normalised to its own 574 nm value:

    nm      580     581     582      -> the reference falls to a MINIMUM at 581 and then
    LUGsp  0.635   0.603   0.741        jumps +17 %/nm. Identical in all four runs.
    BCsp   0.636   0.609   0.759        This is a Bayer channel handover, the same class of
    LUGipa 0.636   0.611   0.765        feature as the documented 473 nm and 608 nm crossovers
    BCipa  0.635   0.598   0.742        (`DOC_lamp_rebuild.md` section 6).

(4) is the last sample before that minimum -- the dimmest, noisiest point in the region -- and the
"peak" is the residual of R and S not cancelling perfectly across the handover. ⇒ ⛔ IT MUST NEVER BE
USED AS A BAND. The second crossover at 611 nm is drawn too; the reference drops -17 %/nm into it.

⭐ (3) and (2) ARE REAL. Across 556-636 nm the reference falls smoothly at -2 to -4 %/nm through both
of them, with no discontinuity anywhere near 568 or 624.

⭐⭐ WHY THE ALIGNMENT AT 580 IS THE RIGHT IDEA ANYWAY, and it is Edwin's, not mine: because (4) is
instrumental it is a FIXED LANDMARK, present at the same wavelength and the same shape in every run
ever taken. Normalising there asks "how big is each real band against a ruler the instrument itself
provides" -- which is exactly the comparison that makes the isopropanol and white-spirit routes
readable side by side.

WHAT THE FIGURE SHOWS, and it is the whole answer to Edwin's last question:

    (4)/(3)      LUG ipa 1.528   BC ipa 1.228   |   LUG spirit 0.898   BC spirit 0.738
                 ^ in ISOPROPANOL the artifact is BIGGER than the pigment band, on both oils
                 ^ in WHITE SPIRIT the pigment band wins, on both oils
    (2)/(3)      LUG ipa 0.989   BC ipa 0.369   |   LUG spirit 0.831   BC spirit 0.394
                 ^ separates the OILS, and does it in BOTH solvents -- this is `R` of
                   `SPEC_metric_research.md` section 12

⇒ the visual difference Edwin sees is real, and it decomposes into one route effect ((4)/(3), an
instrument ratio) and one oil effect ((2)/(3), a pigment ratio).

Writes  spectracs-references/tmp/snv_aligned_580.png

Run:
    PYTHONPATH=. venv/bin/python diagnostics/snv_aligned_580.py
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy

ARCHIVE = os.path.expanduser("~/development/spectracs/spectracs-references/tmp")
OUT_PNG = os.path.join(ARCHIVE, "snv_aligned_580.png")

SNV_WINDOW = (448.0, 626.0)          # 448 = the Soret trim (SPEC_soret_448_trim); 626 = the red peak
ALIGN_AT = 580.0                     # Edwin's landmark -- and see the docstring for what it really is
PLOT_RANGE = (448.0, 630.0)          # 630 = the capture clamp; past it the lamp has no output

# dataviz categorical slots 1-4, light mode. validate_palette.js: ALL CHECKS PASS, contrast WARN on
# aqua/yellow -> every series carries a direct label, which is the required relief.
SETS = [
    ("Lugitsch · white spirit", "#2a78d6", ["20260821LugitschA__001", "20260821LugitschA__002"]),
    ("Lugitsch · isopropanol", "#eb6834", ["20260817LigitschA__%03d" % n for n in range(1, 8)]),
    ("Billa Clever · white spirit", "#1baf7a", ["20260821BillaCleverA__001", "20260821BillaCleverA__002"]),
    ("Billa Clever · isopropanol", "#eda100", ["20280819BillaClever__%03d" % n
                                               for n in (1, 2, 4, 5, 6, 7)]),
]

FEATURES = [(568.0, "(3)", "#333230"), (624.0, "(2)", "#333230")]
CROSSOVERS = [(581.0, "581 nm\ncrossover"), (611.0, "611 nm\ncrossover")]

SURFACE = "#fcfcfb"
INK, INK_SOFT, GRID = "#333230", "#63625c", "#e6e5e0"


def despikedTrace(path, scratch):
    listing = subprocess.run(["pdfdetach", "-list", path], capture_output=True, text=True).stdout
    index = next((l.split(":")[0].strip() for l in listing.splitlines()
                  if l.strip().endswith(": workflow.json")), None)
    if index is None:
        return None
    target = os.path.join(scratch, "w.json")
    subprocess.run(["pdfdetach", "-save", index, "-o", target, path], capture_output=True)
    with open(target) as handle:
        workflow = json.load(handle)
    for phase in workflow.get("phases", []):
        if phase.get("type") != "EVALUATION":
            continue
        for step in phase.get("steps", []):
            if step.get("label") != "Absorption (bands)":
                continue
            values = step["items"][0]["traces"][0]["values"]
            wavelengths = numpy.array([float(k) for k in values])
            absorbance = numpy.array(list(values.values()))
            order = numpy.argsort(wavelengths)
            return wavelengths[order], absorbance[order]
    return None


def pathFor(key):
    series, run = key.split("__")
    return os.path.join(ARCHIVE, series, run + ".pdf")


def snvAligned(wavelengths, absorbance, grid):
    """SNV over SNV_WINDOW, then shifted so every curve passes through 0 at ALIGN_AT."""
    window = numpy.arange(SNV_WINDOW[0], SNV_WINDOW[1] + 0.001, 0.25)
    inside = numpy.interp(window, wavelengths, absorbance)
    standardised = (numpy.interp(grid, wavelengths, absorbance) - inside.mean()) / inside.std()
    anchor = (numpy.interp(ALIGN_AT, wavelengths, absorbance) - inside.mean()) / inside.std()
    return standardised - anchor


def referenceTrace(path):
    """The run's raw reference DN — the lamp times the optics, before any division."""
    with tempfile.TemporaryDirectory() as scratch:
        index = next(l.split(":")[0].strip() for l in subprocess.run(
            ["pdfdetach", "-list", path], capture_output=True, text=True).stdout.splitlines()
            if l.strip().endswith(": workflow.json"))
        target = os.path.join(scratch, "w.json")
        subprocess.run(["pdfdetach", "-save", index, "-o", target, path], capture_output=True)
        workflow = json.load(open(target))
    for phase in workflow["phases"]:
        if phase["type"] != "PROCESSING":
            continue
        for step in phase["steps"]:
            if step.get("label") != "Spectra":
                continue
            for trace in step["items"][0]["traces"]:
                if trace.get("label") == "Reference":
                    w = numpy.array([float(k) for k in trace["values"]])
                    a = numpy.array(list(trace["values"].values()))
                    o = numpy.argsort(w)
                    return w[o], a[o]
    return None


def main():
    grid = numpy.arange(PLOT_RANGE[0], PLOT_RANGE[1] + 0.001, 0.25)
    curves = []
    with tempfile.TemporaryDirectory() as scratch:
        for label, color, keys in SETS:
            stack = []
            for key in keys:
                trace = despikedTrace(pathFor(key), scratch)
                if trace is None:
                    continue
                stack.append(snvAligned(trace[0], trace[1], grid))
            if stack:
                curves.append((label, color, numpy.array(stack)))

    figure, (lamp, full, zoom) = plt.subplots(
        3, 1, figsize=(13.0, 11.6), height_ratios=[0.8, 1.5, 2.2],
        facecolor=SURFACE, gridspec_kw={"hspace": 0.46})

    reference = referenceTrace(pathFor("20260821LugitschA__001"))

    for axis in (lamp, full, zoom):
        axis.set_facecolor(SURFACE)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        for side in ("bottom", "left"):
            axis.spines[side].set_color(GRID)
        axis.tick_params(colors=INK_SOFT, labelsize=10)
        axis.grid(axis="y", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)

    # ---- 1 · the lamp, so the crossovers read as causes rather than coincidences
    lampGrid = numpy.arange(448.0, 630.01, 0.25)
    lamp.plot(lampGrid, numpy.interp(lampGrid, *reference), color=INK_SOFT, linewidth=2.0)
    lamp.set_xlim(*PLOT_RANGE)
    lamp.set_ylabel("reference\nthroughput (DN)", color=INK_SOFT, fontsize=9.5)
    lamp.set_title("1 · THE INSTRUMENT FIRST — the lamp's own discontinuities",
                   color=INK, fontsize=12.5, loc="left", pad=8)
    for centre, note in CROSSOVERS:
        lamp.axvspan(centre - 1.8, centre + 1.8, color="#e34948", alpha=0.13, linewidth=0)
        lamp.annotate(note, xy=(centre, 0.96), xycoords=("data", "axes fraction"),
                      ha="center", va="top", fontsize=9, color="#a33a39", linespacing=1.25)

    # ---- 2 · the whole window Edwin asked for
    for label, color, stack in curves:
        full.plot(grid, stack.mean(axis=0), color=color, linewidth=1.8)
    full.set_xlim(*PLOT_RANGE)
    full.set_ylim(-1.6, 1.4)
    full.axhline(0.0, color=INK_SOFT, linewidth=1.0, linestyle=(0, (4, 3)))
    full.set_ylabel("SNV, shifted to 0 at 580 nm", color=INK, fontsize=10)
    full.set_title("2 · SNV over 448–626 nm, every curve pinned to 0 at 580 nm  "
                   "(the Soret runs off the top of this scale — it reaches SNV +6)",
                   color=INK, fontsize=12.5, loc="left", pad=8)
    full.legend(handles=[plt.Line2D([], [], color=c, linewidth=2.4, label="%s  (n=%d)" % (l, len(s)))
                         for l, c, s in curves],
                loc="lower right", frameon=False, fontsize=9.5, labelcolor=INK, ncol=2)

    # ---- 3 · where the four marked features live
    for label, color, stack in curves:
        mean = stack.mean(axis=0)
        if len(stack) > 1:
            zoom.fill_between(grid, stack.min(axis=0), stack.max(axis=0),
                              color=color, alpha=0.14, linewidth=0)
        zoom.plot(grid, mean, color=color, linewidth=2.2)
    zoom.set_xlim(550.0, 643.0)
    zoom.set_ylim(-1.35, 0.65)
    zoom.axhline(0.0, color=INK_SOFT, linewidth=1.0, linestyle=(0, (4, 3)))
    zoom.set_xlabel("wavelength (nm)", color=INK, fontsize=11)
    zoom.set_ylabel("SNV, shifted to 0 at 580 nm", color=INK, fontsize=10)
    zoom.set_title("3 · THE FOUR MARKED FEATURES — (3) and (2) are pigment, (4) is the lamp",
                   color=INK, fontsize=12.5, loc="left", pad=26)

    for centre, tag, _ in FEATURES:
        zoom.axvline(centre, color=GRID, linewidth=1.2, zorder=0)
        zoom.annotate("%s  %.0f nm" % (tag, centre), xy=(centre, 1.005),
                      xycoords=("data", "axes fraction"), ha="center", va="bottom",
                      fontsize=11, color=INK, fontweight="bold")
    for centre, _ in CROSSOVERS:
        zoom.axvspan(centre - 1.8, centre + 1.8, color="#e34948", alpha=0.13, linewidth=0)
    zoom.annotate("(4) 581 nm — INSTRUMENT", xy=(581.4, 1.005),
                  xycoords=("data", "axes fraction"), ha="left", va="bottom", fontsize=11,
                  color="#a33a39", fontweight="bold")
    zoom.annotate("aligned here", xy=(580.0, 0.0), xytext=(0, 9), textcoords="offset points",
                  ha="center", fontsize=9, color=INK_SOFT)

    # direct labels at 624, where the four curves are furthest apart -- the contrast-WARN relief
    for label, color, stack in curves:
        height = float(numpy.interp(624.0, grid, stack.mean(axis=0)))
        zoom.annotate(label, xy=(630.2, height), xytext=(4, 0), textcoords="offset points",
                      fontsize=9.5, color=INK, va="center",
                      bbox=dict(boxstyle="round,pad=0.22", fc=SURFACE, ec=color, linewidth=1.4))

    figure.savefig(OUT_PNG, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    print("wrote %s" % OUT_PNG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
