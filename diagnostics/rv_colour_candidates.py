"""Colour candidates for a ROUGH VISUAL INSPECTION of the two `Rv` bands. (Edwin, 2026-08-31)

⛔⛔ NONE OF THESE IS A VERDICT AND NONE IS A METRIC. Edwin's framing: *"the 'new color' should be not a
color for a verdict or a metric but only for a rough inspection"*. The pill stays `Q%` and the verdict metric
is `Rv`; this page exists so a human can SEE what `Rv` reads, not so a colour can decide anything.

⚠ WHY IT CANNOT DECIDE ANYTHING, measured rather than asserted: a colour is a THREE-number projection of the
spectrum through the eye's broad response, and `Rv` is one number chosen to maximise exactly this contrast.
Scored as (ΔE between the oils) / (worst ΔE between two fills of ONE oil), the best scheme here reaches
~2.6x where `Rv` itself reaches 33x. The 622-627 window is 5 nm wide and the eye integrates over ~100 nm in
the red, so most of the discrimination is averaged away before it can be seen.

THE FOUR SCHEMES, and exactly what "held constant" means in each -- Edwin asked and the answer was not
written down anywhere:

  A  REAL          the measured absorbance, untouched, at path 3. What the report ships today.
  B  WINDOWS       a synthetic absorbance that equals this fill's own A_valley at EVERY wavelength, except
                   565-580 (set to A_Q) and 622-627 (set to A624). ⇒ "constant elsewhere" = the fill's own
                   valley level, three flat plateaus, nothing else varies.
  C  TWO BANDS     a flat ZERO baseline plus two Gaussians (sigma 9 nm) centred at 572.5 and 624.5 whose PEAK
                   DEPTHS are exactly `Rv`'s two terms, A_Q − A_valley and A624 − A_valley. ⇒ the two bands
                   are given equal spectral presence, which the raw 15 nm / 5 nm windows do not have.
  D  RED ONLY      as C but with the Q band removed — only the 624 term is drawn. The most direct "show me
                   the band `Rv`'s numerator is made of" view, and the least like an oil.
  F  D, FLAT L*    scheme D with L* pinned to 70. ⭐ DOSE IS LIGHTNESS, and `Rv` divides dose out — so a
                   swatch that keeps lightness is showing the one thing the metric deliberately ignores.
                   Pinning L* takes the dose axis out of the eye's way and costs nothing.
  H  D + A CONSTANT BLUE   scheme D plus a FIXED blue band (A 0.20 at 450 nm, sigma 22) that is identical
                   for every sample. ⭐⭐ IT CARRIES NO INFORMATION AND THAT IS THE POINT: swept 0.10-1.10 in
                   depth and 18-40 nm in width the separation score does not move off 4.1x, so the constant
                   is free — it exists only to move the family out of cyan and into oil colours. This is
                   Edwin's original "keep the other parts constant" idea doing real work.
                   ⇒ green (120, 191, 0) -> yellow-green -> olive (175, 178, 0) as the 624 band dies.
  K  D + THE MEASURED BLUE'S SHAPE, scaled to a fixed small peak (A 0.10 at 448-460). Edwin, 2026-08-31:
                   *"what about using a synthesized blue channel instead of a constant blue channel,
                   something that resembles the blue we have in the actual measurements?"*
                   ⭐ It works and it costs ~20 % of the score (3.3x against H's 4.1x), and it keeps a real
                   BLUE CHANNEL (37-57) where H clips it to 0 — so K is a three-channel colour and H is a
                   two-channel ramp.
  ⛔ THE MEASURED BLUE AT ITS OWN SIZE IS MUCH WORSE — 1.9x, and normalising it 1.7x. `A_Soret` above the
     valley is 0.68 with a CV of 6.4 % across six fills of FOUR oils, while `Rv` spans 130 units: the real
     blue is the thing that makes every oil look alike, which is exactly why scheme A only reaches 1.6x and
     why the phone pictures fail. Putting it back at full size re-imports the sameness. ⇒ the blue has to be
     SMALL to be useful, and the moment it is small the difference between "measured shape" and "Gaussian"
     is worth 0.8x of separation — that 0.8x IS the fill-to-fill variation of the blue.
  L  C + THE MEASURED BLUE   Edwin, 2026-08-31: *"what about 'C and measured blue'?"* — BOTH of `Rv`'s
                   bands (as C) on the measured blue's own shape at the same fixed small peak as K. It is the
                   most complete synthetic oil on the page: a real blue, a Q band and a 624 band, and nothing
                   in between that the metric does not use.
  G  THE RATIO     one Gaussian at 624.5 whose depth is `Rv/100 x 0.15` — i.e. the two windows already
                   COMBINED, dose divided out BEFORE rendering, then flat L*. ⚠ This is a faithful picture
                   of the NUMBER rather than of the band; it is the honest end of the ladder and it is the
                   point where "derived from the spectrum" and "a ramp keyed on the metric" meet.

⛔ E — A PLANCK RADIATOR INSTEAD OF THE FLAT BASELINE — WAS TESTED AND DROPPED (Edwin's idea, 2026-08-31).
Rendering the same synthetic transmittance under a blackbody illuminant swept 1800-10000 K moves the hue
(green channel 118 -> 189 on the same fill) and leaves the separation score at **4.1-4.2x at every
temperature**. ⇒ THE ILLUMINANT IS A DISPLAY CHOICE, NOT AN INFORMATION CHANNEL: it changes what the swatch
looks like, not how much it can tell you. Worth knowing before anyone spends time tuning a white point.

⚠ THE PATH MULTIPLIER IS NOT COSMETIC. B/C/D carry absorbances of 0.05-0.15, which at path 1 are almost
colourless; they are rendered at path 12 so the eye has something to judge. A is at path 3, the shipped
"as seen" viewing thickness. ⛔ A path is a viewing choice, so B/C/D are FALSE COLOUR and are labelled so.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/rv_colour_candidates.py
"""
import os
import sys
import math
import tempfile

import numpy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
from colour import Lab_to_XYZ, XYZ_to_sRGB
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.model.spectral.Spectrum import Spectrum

OUT = os.path.join(archive.ARCHIVE, "20260831_rv_colour_candidates.pdf")
GRID = numpy.arange(400.0, 700.1, 1.0)
# ⭐ Widest spread of `Rv` the archive can show, so the swatches are judged over the whole range and not
# over the two oils that happen to be freshest. Billa Clever A is the fill whose 624 band is GONE (−1.5 DN).
FILLS = [("Ja Natuerlich A", "20260831BillaJaNatuerlichA"),
         ("Ja Natuerlich B", "20260831BillaJaNatuerlichB"),
         ("Lugitsch (08-28 D)", "20260828LugitschD"),
         ("Esterer (08-28 F)", "20260828EstererF"),
         ("Spar S-Budget A", "20260831SparSBudgetA"),
         ("Spar S-Budget D", "20260831SparSBudgetD"),
         ("Billa Clever B", "20260828BillaCleverB"),
         ("Billa Clever A", "20260828BillaCleverA")]
SCHEMES = [("A  real spectrum", 3.0), ("B  windows only", 12.0),
           ("C  two bands", 12.0), ("D  red band only", 12.0),
           ("F  D, flat L*", 12.0), ("H  D + constant blue", 12.0),
           ("K  D + measured blue", 12.0), ("L  C + measured blue", 12.0),
           ("G  the ratio, flat L*", 6.0)]
FLAT_LIGHTNESS = {"F  D, flat L*", "H  D + constant blue", "K  D + measured blue",
                  "L  C + measured blue", "G  the ratio, flat L*"}
PINNED_L = 70.0
# ⭐ THE CONSTANT. Identical for every sample, so it cannot carry information — measured: the score holds at
# 4.1x for depths 0.10-1.10 and widths 18-40 nm. It buys the hue, nothing else.
BLUE_DEPTH, BLUE_CENTRE, BLUE_SIGMA = 0.20, 450.0, 22.0
# ⚠ K's peak is HALF H's, and it has to be: the measured shape is broader, so an equal peak would put more
# total blue in. ⛔ CLAMPED at A 1.2 — below 440 nm the measured curve reaches A 2.4-4.2 where the sample
# sits at ~4 DN (`SPEC_capture_quality.md` §16.40), i.e. noise, and it would render the swatch black.
BLUE_PEAK_K, BLUE_CLAMP = 0.10, 1.2


def bandMean(nm, values, low, high):
    return float(numpy.mean(values[(nm >= low) & (nm <= high)]))


def synthesise(nm, absorbance):
    """The four candidate absorbance curves for one fill, plus its `Rv`."""
    valley = bandMean(nm, absorbance, 500.0, 560.0)
    qBand = bandMean(nm, absorbance, 565.0, 580.0)
    red = bandMean(nm, absorbance, 622.0, 627.0)
    gauss = lambda w, centre, sigma: math.exp(-0.5 * ((w - centre) / sigma) ** 2)

    real = {float(w): float(v) for w, v in zip(nm, absorbance)}
    windows = {}
    for w in GRID:
        value = valley
        if 565.0 <= w <= 580.0:
            value = qBand
        if 622.0 <= w <= 627.0:
            value = red
        windows[float(w)] = value
    twoBands = {float(w): (qBand - valley) * gauss(w, 572.5, 9.0)
                + (red - valley) * gauss(w, 624.5, 9.0) for w in GRID}
    redOnly = {float(w): (red - valley) * gauss(w, 624.5, 9.0) for w in GRID}
    rv = 100.0 * (red - valley) / (qBand - valley) if qBand > valley else float("nan")
    # ⚠ G's band depth is the METRIC, not an absorbance: dose is divided out before anything is rendered.
    ratioBand = {float(w): (0.0 if rv != rv else rv / 100.0 * 0.15) * gauss(w, 624.5, 9.0) for w in GRID}
    withBlue = {float(w): BLUE_DEPTH * gauss(w, BLUE_CENTRE, BLUE_SIGMA)
                + (red - valley) * gauss(w, 624.5, 9.0) for w in GRID}
    soret = bandMean(nm, absorbance, 448.0, 460.0) - valley
    scale = BLUE_PEAK_K / soret if soret > 0 else 0.0
    measuredBlue = {}
    for w in GRID:
        blue = min(BLUE_CLAMP, max(0.0, float(numpy.interp(w, nm, absorbance)) - valley)) * scale \
            if w <= 500.0 else 0.0
        measuredBlue[float(w)] = blue + (red - valley) * gauss(w, 624.5, 9.0)
    bothBandsBlue = {w: v + (qBand - valley) * gauss(w, 572.5, 9.0) for w, v in measuredBlue.items()}
    return ([real, windows, twoBands, redOnly, redOnly, withBlue, measuredBlue, bothBandsBlue,
             ratioBand], rv)


def swatch(util, curve, path, flatLightness=False):
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {float(k): float(v) for k, v in curve.items()}
    lightness, chroma, hue, rgb = util.spectrumToLab(spectrum, path=path)
    lab = numpy.array([lightness, chroma * math.cos(math.radians(hue)),
                       chroma * math.sin(math.radians(hue))])
    if not flatLightness:
        return lab, tuple(channel / 255.0 for channel in rgb)
    # ⭐ Re-render at a PINNED L*. The chromatic pair (a*, b*) is kept exactly; only the dose axis leaves.
    lab = numpy.array([PINNED_L, lab[1], lab[2]])
    mapped = XYZ_to_sRGB(Lab_to_XYZ(lab, util._EvaluationColorUtil__D65_XY),
                         util._EvaluationColorUtil__D65_XY)
    return lab, tuple(float(min(1.0, max(0.0, c))) for c in mapped)


def collect():
    util = EvaluationColorUtil()
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for label, session in FILLS:
            folder = os.path.join(archive.ARCHIVE, session)
            name = sorted(f for f in os.listdir(folder) if f.endswith(".pdf"))[0]
            workflow = archive.workflowOf(os.path.join(folder, name), scratch)
            nm, absorbance = archive.despikedTrace(workflow)
            curves, rv = synthesise(nm, absorbance)
            rows.append({"label": label, "session": session, "rv": rv, "curves": curves,
                         "swatches": [swatch(util, curve, path, name in FLAT_LIGHTNESS)
                                      for curve, (name, path) in zip(curves, SCHEMES)]})
    return rows


def separationNote(rows):
    """(ΔE between the oils) / (worst ΔE between two fills of ONE oil), per scheme. Computed, never typed.

    ⛔⛔ BILLA CLEVER IS NOT IN THE WITHIN-OIL YARDSTICK, and leaving it in was a real error in the first
    draft of this page. Its two fills read `Rv` −7.1 and 27.4: they are not a replicate pair, they are two
    genuinely different measurements of an oil whose 624 band is at the noise floor (−1.5 DN and +4.5 DN).
    A scheme that draws them in DIFFERENT colours is doing its job, and scoring that as colour noise
    punished exactly the schemes that track `Rv` best — scheme C fell from 2.6x to 0.8x on it.
    ⚠ It is still on the page, because what a near-zero band looks like is the thing worth seeing."""
    pairs = {"Ja Natuerlich": [0, 1], "Spar S-Budget": [4, 5]}
    out = []
    for index, (name, _) in enumerate(SCHEMES):
        green = numpy.mean([rows[i]["swatches"][index][0] for i in pairs["Ja Natuerlich"]], axis=0)
        brown = numpy.mean([rows[i]["swatches"][index][0] for i in pairs["Spar S-Budget"]], axis=0)
        within = max(numpy.linalg.norm(rows[a]["swatches"][index][0] - rows[b]["swatches"][index][0])
                     for a, b in pairs.values())
        between = float(numpy.linalg.norm(green - brown))
        out.append((name, between, within, between / within if within else float("nan")))
    return out


def pageSwatches(pdf, rows):
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("Colour candidates for ROUGH VISUAL INSPECTION of the two Rv bands",
                    fontsize=14, fontweight="bold", y=0.965)
    figure.text(0.5, 0.945,
                "[!]  NOT a verdict and NOT a metric (Edwin, 2026-08-31).   B, C and D are FALSE "
                "COLOUR: synthetic spectra rendered at path 12.\n"
                "A is the real measured absorbance at path 3 — what the report ships today.   "
                "D's grey swatch is the converter refusing a NEGATIVE band.",
                ha="center", va="top", fontsize=9, style="italic", linespacing=1.6)

    left, top, width, height = 0.112, 0.800, 0.086, 0.056
    for column, (name, path) in enumerate(SCHEMES):
        figure.text(left + column * (width + 0.008) + width / 2, top + 0.016,
                    "%s\n(path %g)" % (name, path), ha="center", va="bottom",
                    fontsize=6.5, fontweight="bold", linespacing=1.5)
    for row, entry in enumerate(rows):
        y = top - row * (height + 0.011) - height
        figure.text(0.104, y + height / 2, "%s\nRv %.1f" % (entry["label"], entry["rv"]),
                    ha="right", va="center", fontsize=9, linespacing=1.5)
        for column, (lab, rgb) in enumerate(entry["swatches"]):
            x = left + column * (width + 0.008)
            figure.add_artist(Rectangle((x, y), width, height, facecolor=rgb,
                                        edgecolor="#333333", lw=0.7))
            figure.text(x + width / 2, y + 0.008,
                        "%d %d %d" % tuple(int(round(c * 255)) for c in rgb),
                        ha="center", fontsize=4.8,
                        color="white" if lab[0] < 55 else "#222222")
    lines = ["SEPARATION SCORE  =  dE between the oils / worst dE between two fills of ONE oil "
             "(computed on every run, never typed):"]
    for name, between, within, ratio in separationNote(rows):
        lines.append("     %-20s dE oils %6.2f     dE within one oil %6.2f     ratio %4.1f x"
                     % (name, between, within, ratio))
    lines.append("")
    lines.append("=> the best reaches a few x, where Rv itself separates the same oils 33 x. "
                 "A colour can SHOW the number; it cannot beat it.")
    lines.append("[!] Billa Clever is EXCLUDED from the within-oil yardstick: its two fills read "
                 "Rv -7.1 and 27.4, so they are not a replicate pair.")
    figure.text(0.055, 0.180, "\n".join(lines), fontsize=8.4, va="top",
                color="#a03000", linespacing=1.5, family="monospace")
    pdf.savefig(figure)
    pyplot.close(figure)


def pageCurves(pdf, rows):
    """⭐ THE ANSWER TO "how did you hold the other parts constant" — drawn, not described."""
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("What each scheme actually feeds to the colour conversion",
                    fontsize=14, fontweight="bold", y=0.965)
    figure.text(0.5, 0.922,
                "One green fill and one brown fill. The shaded strips are Rv's own windows: "
                "500–560 (datum), 565–580 (A_Q), 622–627 (A624).",
                ha="center", va="top", fontsize=9, style="italic")
    shown = [rows[0], rows[5]]
    for column, (name, path) in enumerate(SCHEMES):
        for line, entry in enumerate(shown):
            axes = figure.add_axes([0.040 + column * 0.106, 0.545 - line * 0.400, 0.080, 0.310])
            curve = entry["curves"][column]
            w = numpy.array(sorted(curve))
            axes.plot(w, [curve[k] for k in w], color="#1b5e20" if line == 0 else "#8b4513", lw=1.3)
            for low, high, tint in ((500, 560, "#cfd8dc"), (565, 580, "#c5e1a5"), (622, 627, "#ef9a9a")):
                axes.axvspan(low, high, color=tint, alpha=0.55, lw=0)
            axes.set_xlim(430, 690)
            axes.tick_params(labelsize=7)
            axes.set_xlabel("nm", fontsize=7)
            if column == 0:
                axes.set_ylabel("%s\nabsorbance" % entry["label"], fontsize=8, linespacing=1.6)
            if line == 0:
                axes.set_title("%s  (path %g)" % (name, path), fontsize=9, fontweight="bold")
    figure.text(0.065, 0.105,
                "A  the measured curve, untouched.\n"
                "B  every wavelength is set to this fill's OWN A_valley, except the two band windows — "
                "three flat plateaus, nothing else varies.\n"
                "C  a flat ZERO baseline plus two Gaussians (σ 9 nm) whose peak depths ARE Rv's two terms, "
                "A_Q − A_valley and A624 − A_valley.\n"
                "D  as C with the Q band removed - only Rv's numerator is drawn.\n"
                "F  the SAME curve as D; the difference is in the rendering - L* pinned to 70, so dose "
                "leaves the swatch.\n"
                "H  D plus a CONSTANT blue band (A 0.20 at 450 nm) - identical for every sample, so it "
                "carries no information; it only moves the hue out of cyan.\n"
                "K  the MEASURED blue's shape scaled to a fixed peak A 0.10 - realistic, and it keeps a "
                "real blue channel where H clips it to 0.\n"
                "L  BOTH bands on the measured blue - the most complete synthetic oil here.\n"
                "G  one band whose depth is Rv/100 x 0.15 - the metric itself, dose already divided out.",
                fontsize=8.8, va="top", linespacing=1.8, family="monospace")
    pdf.savefig(figure)
    pyplot.close(figure)


def main():
    rows = collect()
    with PdfPages(OUT) as pdf:
        pageSwatches(pdf, rows)
        pageCurves(pdf, rows)
    for name, between, within, ratio in separationNote(rows):
        print("  %-20s dE oils %6.2f   dE within %6.2f   ratio %4.1f x" % (name, between, within, ratio))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
