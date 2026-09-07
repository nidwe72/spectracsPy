"""What the empty jar does to the beam -- the 2026-09-06 jar-vs-bare-lamp pair.

Edwin captured two REFERENCE frames minutes apart on the dev bench: one through the empty
polymer jar in its holder, one with the jar taken out and the camera looking straight down the
Yuji lamp. His reading of the pair was "the jar itself changes the spectrum". This script tests
that, and the answer is narrower: the jar changes the LEVEL, not the SHAPE.

    docs/DOC_jar_transmission.md    the written account  ->  Spectracs_JarTransmission.pdf
    SPEC_capture_quality.md §16.42  the entry in the evidence base

⚠ THE INPUT IS TWO SCREENSHOTS, NOT TWO SPECTRA. No run was archived -- what exists is a pair of
ksnip PNGs of the bench's Reference plot. So the curves here are DIGITISED from the rendered plot:
the anti-aliased curve colour (46,204,113) is found per pixel column and its mean row is mapped
back through the axis calibration. That costs roughly ±1 DN of resolution and it is the reason
nothing below is quoted past three digits. The two PNGs are preserved at

    ../spectracs-references/probe/jar_20260906/{jar,direct}.png

and the digitised result is committed as `diagnostics/data/jar_transmission_20260906.csv`, so the
figures regenerate without them.

⛔ THE DIRECT FRAME IS CLIPPED, 472-525 nm, at the 255 DN ceiling. That band is not a measurement
and every number here excludes it. Two of the three departures from a flat ratio -- the 580 nm
valley and the 615/618 step -- sit where that clipping would be expected to do damage, so neither
is claimed as a jar effect. §5 of the DOC says what to re-measure.

⚠ AND A FLAT RATIO IS ALSO WHAT A PURE EXPOSURE DIFFERENCE LOOKS LIKE. Two frames alone cannot
separate "the jar loses 14 %" from "the two captures ran at different exposure"; the
CAPTURE-SETTINGS line (§16.39) settles it and was not kept. Read the 0.86 as an upper bound on
the jar's loss until it is.

Prints the band table and the Fresnel comparison; writes three SVGs:
    docs/figures/jar_overlay.svg      the two curves, and the direct one scaled by a constant
    docs/figures/jar_ratio.svg        jar / direct, with the three contaminated zones marked
    docs/figures/jar_fresnel.svg      why a four-surface reflection loss is grey

Run:
    ./venv/bin/python diagnostics/jar_transmission.py
    ./venv/bin/python diagnostics/jar_transmission.py --digitise   # re-read the two PNGs
"""
import argparse
import csv
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
FIGURES = os.path.join(REPO, "docs", "figures")
CSV_PATH = os.path.join(HERE, "data", "jar_transmission_20260906.csv")
PNG_DIR = os.path.abspath(os.path.join(REPO, "..", "spectracs-references", "probe", "jar_20260906"))

# The bench plots the reference curve in this colour; the grid and frame are all greys, so a
# distance threshold in RGB isolates the curve with no other match anywhere in the frame.
CURVE_RGB = np.array([46, 204, 113])

# Axis calibration, in image pixels, read off the two screenshots themselves rather than assumed:
#   x400/x640  centres of the leftmost and rightmost x tick labels (the 13 labels 400..640 were
#              found by grouping the label-row pixel columns; both images gave 7.044 px/nm)
#   y250/y50   centres of the "250" and "50" y tick labels
#   yTop/yBot  the plot box, so that the OTHER green things in a bench screenshot -- the highlighted
#              step tab at the top, the "Spectrum" toggle, the "Capture reference" button at the
#              bottom -- cannot be mistaken for curve. They share the curve's colour exactly, and
#              without this the tab strip drags the first eight nanometres up by 100 DN.
# Held as constants because these two files will never be re-shot; --digitise re-reads THEM, not
# some future pair. A new pair needs its own entry.
CALIBRATION = {
    "jar":    dict(png="jar.png",    x400=115.2, x640=1805.8, y250=200.0, y50=511.0,
                   yTop=150, yBot=600),
    "direct": dict(png="direct.png", x400=140.2, x640=1830.8, y250=193.0, y50=506.0,
                   yTop=140, yBot=592),
}

GRID = np.arange(400.0, 637.0, 1.0)

# The three zones where the pair is not evidence. CLIPPED is measured (the ceiling run in the
# direct frame); the other two are the features that clipping would be expected to produce.
CLIPPED = (472.0, 528.0)
VALLEY = (576.0, 584.0)
STEP = (612.0, 620.0)

# The clipping is a hard ceiling, but the approach to it is not sharp: §16.41 measured the camera's
# transfer curve and it bends before the top. Samples where the DIRECT frame sits above this are
# therefore dropped as well -- not because they are clipped, but because the two frames are on
# different parts of a curved response there and their quotient is not the jar's transmission.
# The drift the guard removes is printed, so the choice can be judged rather than trusted.
DN_GUARD = 240.0

# Bands quoted in the DOC. Each avoids all three zones and sits where the lamp is neither steep
# nor faint, so a digitisation error of a pixel costs a thousandth of the ratio and not a tenth.
BANDS = [(435, 470), (530, 555), (560, 575), (585, 608), (622, 636)]

# Refractive indices for the four-surface arithmetic of §4. Polystyrol is what Edwin called the
# jar; the other three are what the measured number would imply instead.
INDICES = [("PMMA / polypropylene", 1.49), ("soda-lime glass", 1.52),
           ("polycarbonate", 1.585), ("polystyrene", 1.59)]


# --------------------------------------------------------------------------- digitising

def digitise(name):
    """Recover one curve from its screenshot. Returns DN on the 1 nm GRID."""
    from PIL import Image

    config = CALIBRATION[name]
    path = os.path.join(PNG_DIR, config["png"])
    pixels = np.asarray(Image.open(path).convert("RGB")).astype(int)
    mask = np.abs(pixels - CURVE_RGB).sum(2) < 120
    mask[:config["yTop"]] = False
    mask[config["yBot"]:] = False
    pxPerNm = (config["x640"] - config["x400"]) / 240.0

    def toDn(row):
        return 250.0 + (row - config["y250"]) * (50.0 - 250.0) / (config["y50"] - config["y250"])

    waves, values = [], []
    for column in range(mask.shape[1]):
        rows = np.nonzero(mask[:, column])[0]
        if not len(rows):
            continue
        wave = 400.0 + (column - config["x400"]) / pxPerNm
        if wave < GRID[0] - 2 or wave > GRID[-1] + 2:
            continue
        # The curve is 2-3 px thick and anti-aliased; its MEAN row is the drawn value. Where the
        # curve is near-vertical the column holds the whole jump and the mean is the midpoint --
        # which is why the step at 613-618 is read to a nanometre and not better.
        waves.append(wave)
        values.append(toDn(rows.mean()))
    return np.interp(GRID, np.array(waves), np.array(values))


def writeCsv(direct, jar):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["wavelength_nm", "direct_dn", "jar_dn"])
        for wave, dValue, jValue in zip(GRID, direct, jar):
            writer.writerow(["%.0f" % wave, "%.2f" % dValue, "%.2f" % jValue])
    print("wrote %s" % os.path.relpath(CSV_PATH, REPO))


def readCsv():
    rows = np.genfromtxt(CSV_PATH, delimiter=",", skip_header=1)
    return rows[:, 1], rows[:, 2]


# --------------------------------------------------------------------------- the numbers

def cleanMask():
    """Everything from 432 nm up that is outside the three contaminated zones.

    Below 432 nm the lamp's blue edge climbs 30 DN per nanometre, so the ratio there measures the
    digitiser's alignment and not the jar; that is the whole content of the 0.75 excursion at the
    left of Figure 2."""
    keep = GRID >= 432.0
    for lo, hi in (CLIPPED, VALLEY, STEP):
        keep &= ~((GRID >= lo) & (GRID <= hi))
    return keep


def linearMask(direct):
    """The clean set, less everything within 15 DN of the ceiling (see DN_GUARD).

    What survives still spans the whole window -- the blue edge at 432-441, the 460 dip, the 485
    dip and everything from 556 nm up -- so the flatness claim is not made on the red end alone."""
    return cleanMask() & (direct <= DN_GUARD)


def report(direct, jar):
    ratio = jar / np.clip(direct, 1.0, None)
    keep = linearMask(direct)
    grey = float(np.median(ratio[keep]))
    spread = float(np.std(ratio[keep]))

    print("\nCLIPPING")
    clipped = direct >= 252.0
    print("  direct >= 252 DN over %.0f-%.0f nm (%d of %d samples); peak %.1f"
          % (GRID[clipped].min(), GRID[clipped].max(), clipped.sum(), len(GRID), direct.max()))
    print("  jar    >= 252 DN: %d samples; peak %.1f" % ((jar >= 252.0).sum(), jar.max()))

    print("\nBAND RATIOS  (jar / direct)")
    for lo, hi in BANDS:
        band = (GRID >= lo) & (GRID <= hi)
        top = direct[band].max()
        flag = "  <- direct peaks at %.0f DN here, on the bend" % top if top > DN_GUARD else ""
        print("  %3d-%3d nm   %.4f  sd %.4f%s" % (lo, hi, ratio[band].mean(), ratio[band].std(), flag))
    print("  ------")

    print("\nTHE GUARD, AND THE DRIFT IT REMOVES")
    for cap in (255.0, 248.0, 242.0, DN_GUARD, 230.0, 225.0):
        subset = cleanMask() & (direct <= cap)
        print("  direct <= %3.0f DN   n = %3d   median %.4f   sd %.4f   spans %.0f-%.0f nm"
              % (cap, subset.sum(), np.median(ratio[subset]), ratio[subset].std(),
                 GRID[subset].min(), GRID[subset].max()))
    print("  => the estimate falls as the ceiling is backed away from and then stops. ADOPTED: %.3f"
          % grey)

    print("\nIS THERE A TILT ACROSS THE GUARDED SET?")
    slope, intercept = np.polyfit(GRID[keep], ratio[keep], 1)
    print("  least squares: %+.3e per nm  =>  %+.4f over 432-636 nm  (%.2f %% of the level)"
          % (slope, slope * 204.0, 100.0 * slope * 204.0 / grey))

    print("\nFEATURE POSITIONS  (a shape change would move these; a level change cannot)")
    for label, lo, hi, kind in [("Soret-side hump", 443, 458, "max"), ("462 dip", 455, 470, "min"),
                                ("485 dip", 481, 492, "min"), ("593 hump", 585, 612, "max"),
                                ("580 valley", 565, 590, "min")]:
        band = (GRID >= lo) & (GRID <= hi)
        pick = np.argmax if kind == "max" else np.argmin
        dW, jW = GRID[band][pick(direct[band])], GRID[band][pick(jar[band])]
        print("  %-16s direct %5.0f nm    jar %5.0f nm    %s"
              % (label, dW, jW, "same" if dW == jW else "MOVED %+.0f nm" % (jW - dW)))

    print("\nTHE THREE CONTAMINATED ZONES")
    for label, (lo, hi) in [("clipped", CLIPPED), ("valley", VALLEY), ("step", STEP)]:
        band = (GRID >= lo) & (GRID <= hi)
        print("  %-8s %3.0f-%3.0f nm   ratio %.3f  (clean set says %.3f)"
              % (label, lo, hi, ratio[band].mean(), grey))

    print("\nFOUR SURFACES, TWO WALLS  --  T = ((1-R)/(1+R))^2,  R = ((n-1)/(n+1))^2")
    for label, n in INDICES:
        reflect = ((n - 1.0) / (n + 1.0)) ** 2
        through = ((1.0 - reflect) / (1.0 + reflect)) ** 2
        print("  n = %.3f  %-22s R = %.4f   T = %.4f   %s"
              % (n, label, reflect, through, "<- measured" if abs(through - grey) < 0.004 else ""))
    implied = impliedIndex(grey)
    print("  measured T = %.4f  =>  implied n = %.3f" % (grey, implied))

    print("\nWHAT A FLAT FACTOR DOES TO ABSORBANCE, IF THE REFERENCE DOES NOT SHARE IT")
    offset = -math.log10(grey)
    print("  A gains a constant %+.4f at every wavelength" % offset)
    for soret in (0.6, 0.8, 1.0, 1.5):
        print("    A_Soret = %.1f  =>  Q%% reads %.1f %% low   (dQ100 reads 0.0 %% low)"
              % (soret, 100.0 * (1.0 - soret / (soret + offset))))
    return ratio, grey


def impliedIndex(through):
    """Invert T = ((1-R)/(1+R))^2 for n. Positive root only; n > 1 by construction."""
    root = math.sqrt(through)
    reflect = (1.0 - root) / (1.0 + root)
    r = math.sqrt(reflect)
    return (1.0 + r) / (1.0 - r)


# --------------------------------------------------------------------------- figures

INK, MUTED, LINE = "#1c211c", "#5c655c", "#b9c1b9"
GREEN, GREEN_DK = "#3f7d3f", "#2f5d2f"
BLUE, RED, AMBER, PANEL = "#3a5fa8", "#b03a3a", "#c8891f", "#f5f8f5"
FONT = 'font-family="Segoe UI,Helvetica Neue,Arial,sans-serif"'
MONO = 'font-family="Consolas,DejaVu Sans Mono,monospace"'


def text(x, y, body, size=12, fill=INK, anchor="start", weight=None, style=None, mono=False):
    bits = ['<text x="%.1f" y="%.1f" %s font-size="%.1f" fill="%s" xml:space="preserve"'
            % (x, y, MONO if mono else FONT, size, fill)]
    if anchor != "start":
        bits.append(' text-anchor="%s"' % anchor)
    if weight:
        bits.append(' font-weight="%s"' % weight)
    if style:
        bits.append(' font-style="%s"' % style)
    bits.append(">%s</text>" % body)
    return "".join(bits)


class Axes(object):
    """A minimal linear plot box -- enough for two panels, and no dependency to draw them."""

    def __init__(self, x0, y0, x1, y1, wLo, wHi, vLo, vHi):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.wLo, self.wHi, self.vLo, self.vHi = wLo, wHi, vLo, vHi

    def px(self, wave):
        return self.x0 + (wave - self.wLo) / (self.wHi - self.wLo) * (self.x1 - self.x0)

    def py(self, value):
        return self.y1 - (value - self.vLo) / (self.vHi - self.vLo) * (self.y1 - self.y0)

    def frame(self, wTicks, vTicks, vFormat="%g", vLabel=""):
        out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ffffff" stroke="%s"/>'
               % (self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0, LINE)]
        for wave in wTicks:
            x = self.px(wave)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.7"/>'
                       % (x, self.y0, x, self.y1, "#e8ece8"))
            out.append(text(x, self.y1 + 16, "%d" % wave, 11, MUTED, anchor="middle"))
        for value in vTicks:
            y = self.py(value)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.7"/>'
                       % (self.x0, y, self.x1, y, "#e8ece8"))
            out.append(text(self.x0 - 8, y + 4, vFormat % value, 11, MUTED, anchor="end"))
        out.append(text((self.x0 + self.x1) / 2, self.y1 + 36, "wavelength (nm)", 11.5, MUTED, anchor="middle"))
        if vLabel:
            out.append('<g transform="translate(%.1f,%.1f) rotate(-90)">%s</g>'
                       % (self.x0 - 44, (self.y0 + self.y1) / 2,
                          text(0, 0, vLabel, 11.5, MUTED, anchor="middle")))
        return out

    def band(self, lo, hi, colour, alpha):
        return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="%.2f"/>'
                % (self.px(lo), self.y0, self.px(hi) - self.px(lo), self.y1 - self.y0, colour, alpha))

    def path(self, waves, values, colour, width=1.9, dash=None):
        points = " ".join("%.1f,%.1f" % (self.px(w), self.py(v)) for w, v in zip(waves, values))
        extra = ' stroke-dasharray="%s"' % dash if dash else ""
        return ('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f" '
                'stroke-linejoin="round"%s/>' % (points, colour, width, extra))


def swatch(x, y, colour, label, dash=None):
    extra = ' stroke-dasharray="%s"' % dash if dash else ""
    return ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.6"%s/>'
            % (x, y, x + 26, y, colour, extra)) + text(x + 33, y + 4, label, 11.5, INK)


def writeSvg(name, width, height, body):
    os.makedirs(FIGURES, exist_ok=True)
    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
            '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height, width, height, width, height))
    path = os.path.join(FIGURES, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head + "".join(body) + "</svg>")
    print("wrote %s" % os.path.relpath(path, REPO))


def figureOverlay(direct, jar, grey):
    W, H = 940, 486
    ax = Axes(78, 66, 900, 372, 398, 640, 0, 268)
    out = [text(W / 2, 30, "The empty jar against the bare lamp", 16, GREEN_DK, anchor="middle", weight="700"),
           text(W / 2, 49, "two reference frames, 2026-09-06 18:47 and 18:48, digitised from the bench plot",
                11.5, MUTED, anchor="middle")]
    out += ax.frame(range(400, 641, 20), range(0, 261, 50), "%d", "camera DN")
    out.append(ax.band(CLIPPED[0], CLIPPED[1], RED, 0.09))
    y255 = ax.py(255)
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" '
               'stroke-dasharray="3 3"/>' % (ax.x0, y255, ax.x1, y255, RED))
    out.append(text(ax.x1 - 6, y255 - 7, "255 DN \u2014 the sensor ceiling", 10.5, RED, anchor="end"))
    out.append(ax.path(GRID, direct, BLUE, 2.0))
    out.append(ax.path(GRID, direct * grey, GREEN_DK, 1.3, dash="6 4"))
    out.append(ax.path(GRID, jar, GREEN, 2.0))
    midClip = (CLIPPED[0] + CLIPPED[1]) / 2
    out.append(text(ax.px(midClip), ax.py(104), "the direct frame is CLIPPED here", 11.5, RED,
                    anchor="middle", weight="700"))
    out.append(text(ax.px(midClip), ax.py(86), "%.0f\u2013%.0f nm \u2014 not a measurement" % CLIPPED, 10.5,
                    RED, anchor="middle"))
    out.append(swatch(90, 418, BLUE, "direct, straight down the Yuji lamp"))
    out.append(swatch(90, 440, GREEN, "through the empty jar in its holder"))
    out.append(swatch(490, 418, GREEN_DK, "the direct curve \u00d7 %.3f" % grey, dash="6 4"))
    out.append(text(490, 440, "one constant, applied at every wavelength", 11.5, MUTED))
    out.append(text(90, 470, "Where the dashed line hides under the green one \u2014 which is everywhere "
                             "outside the clipped band \u2014 the jar has done nothing but dim the lamp.",
                    11.5, INK))
    return writeSvg("jar_overlay.svg", W, H, out)


def figureRatio(ratio, grey):
    W, H = 940, 478
    ax = Axes(78, 66, 900, 330, 398, 640, 0.70, 1.03)
    out = [text(W / 2, 30, "jar \u00f7 direct \u2014 flat at %.3f, and the three places it is not" % grey,
                16, GREEN_DK, anchor="middle", weight="700"),
           text(W / 2, 49, "every departure sits in a zone the clipped reference already explains", 11.5,
                MUTED, anchor="middle")]
    out += ax.frame(range(400, 641, 20), [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00], "%.2f", "jar / direct")
    out.append(ax.band(398, 432, MUTED, 0.10))
    out.append(ax.band(CLIPPED[0], CLIPPED[1], RED, 0.09))
    out.append(ax.band(VALLEY[0], VALLEY[1], AMBER, 0.16))
    out.append(ax.band(STEP[0], STEP[1], AMBER, 0.16))
    yGrey = ax.py(grey)
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4" '
               'stroke-dasharray="7 4"/>' % (ax.x0, yGrey, ax.x1, yGrey, GREEN_DK))
    out.append(text(ax.x1 + 6, yGrey + 4, "%.3f" % grey, 11.5, GREEN_DK, weight="700"))
    # Below 414 nm the lamp gives under 15 DN and the quotient is all digitiser; it is not drawn.
    visible = GRID >= 414
    out.append(ax.path(GRID[visible], np.clip(ratio[visible], 0.70, 1.03), INK, 1.6))
    for label, lo, hi, colour in [("blue edge", 398, 432, MUTED),
                                  ("clipped", CLIPPED[0], CLIPPED[1], RED),
                                  ("valley", VALLEY[0], VALLEY[1], AMBER),
                                  ("step", STEP[0], STEP[1], AMBER)]:
        out.append(text(ax.px((lo + hi) / 2), ax.y1 - 12, label, 11, colour, anchor="middle", weight="700"))
    for offset, line in enumerate(["the lamp climbs 30 DN per",
                                   "nm here, so this measures",
                                   "the digitiser, not the jar"]):
        out.append(text(ax.px(399) + 6, ax.py(0.995 - 0.024 * offset), line, 10, MUTED))
    notes = [
        ("clipped %.0f\u2013%.0f nm" % CLIPPED, RED,
         "the direct frame sits on the ceiling, so the quotient is a fiction \u2014 and it reads HIGH, "
         "because the true direct value is above 255"),
        ("valley %.0f\u2013%.0f nm" % VALLEY, AMBER,
         "the lamp\u2019s darkest point. Veiling glare off a saturated neighbour fills in the direct frame "
         "most where the signal is least"),
        ("step %.0f\u2013%.0f nm" % STEP, AMBER,
         "the same 18 DN cliff in both frames, 4 nm apart. Nothing in the light moved: the 452, 485 and 593 "
         "features are on the same nanometre"),
    ]
    y = 400
    for label, colour, body in notes:
        out.append('<rect x="78" y="%.1f" width="10" height="10" fill="%s" opacity="0.55"/>' % (y - 9, colour))
        out.append(text(96, y, label, 11.5, colour, weight="700"))
        out.append(text(228, y, body, 10.8, MUTED))
        y += 24
    return writeSvg("jar_ratio.svg", W, H, out)


def figureFresnel(grey):
    W, H = 940, 452
    out = [text(W / 2, 30, "Why the loss is grey: four surfaces, no absorber", 16, GREEN_DK,
                anchor="middle", weight="700"),
           text(W / 2, 49, "a reflection at an index step is nearly wavelength-flat across the visible; "
                           "an absorber never is", 11.5, MUTED, anchor="middle")]
    top, bottom, beamY = 88, 208, 148
    walls = [(244, 274), (532, 562)]
    out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfdfb" stroke="%s"/>'
               % (274, top, 258, bottom - top, LINE))
    for index, (x0, x1) in enumerate(walls):
        out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#dfe6ee" stroke="%s"/>'
                   % (x0, top, x1 - x0, bottom - top, LINE))
        out.append(text((x0 + x1) / 2, top - 11, "wall %d" % (index + 1), 11, MUTED, anchor="middle"))
    out.append(text(403, top - 11, "the fill", 11, MUTED, anchor="middle"))
    out.append('<line x1="86" y1="%d" x2="244" y2="%d" stroke="%s" stroke-width="2.4"/>' % (beamY, beamY, GREEN))
    out.append('<line x1="562" y1="%d" x2="700" y2="%d" stroke="%s" stroke-width="2.4"/>' % (beamY, beamY, GREEN))
    out.append('<line x1="274" y1="%d" x2="532" y2="%d" stroke="%s" stroke-width="2.0" '
               'stroke-dasharray="4 3"/>' % (beamY, beamY, GREEN))
    out.append('<line x1="274" y1="%d" x2="244" y2="%d" stroke="%s" stroke-width="1.2" '
               'stroke-dasharray="2 3"/>' % (beamY, beamY, GREEN))
    out.append('<line x1="562" y1="%d" x2="532" y2="%d" stroke="%s" stroke-width="1.2" '
               'stroke-dasharray="2 3"/>' % (beamY, beamY, GREEN))
    out.append(text(86, beamY - 14, "lamp", 12, INK, weight="700"))
    out.append(text(700, beamY - 14, "sensor", 12, INK, weight="700", anchor="end"))
    for number, x in enumerate([244, 274, 532, 562], start=1):
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.0"/>'
                   % (x, beamY, x - 22, beamY - 40, RED))
        out.append('<polygon points="%d,%d %d,%d %d,%d" fill="%s"/>'
                   % (x - 22, beamY - 40, x - 15, beamY - 32, x - 25, beamY - 30, RED))
        out.append('<circle cx="%d" cy="%d" r="10" fill="#ffffff" stroke="%s" stroke-width="1.4"/>'
                   % (x, bottom + 28, RED))
        out.append(text(x, bottom + 32, "%d" % number, 11, RED, anchor="middle", weight="700"))
    out.append(text(403, bottom + 62, "four index steps, each turning about 4 % of the beam straight back",
                    11.5, RED, anchor="middle"))
    panelTop, rowStep = 82, 40
    out.append('<rect x="732" y="%d" width="182" height="%d" fill="%s" stroke="%s" rx="6"/>'
               % (panelTop, rowStep * len(INDICES) + 78, PANEL, LINE))
    out.append(text(823, panelTop + 24, "T through two walls", 12, GREEN_DK, anchor="middle", weight="700"))
    row = panelTop + 50
    for label, n in INDICES:
        reflect = ((n - 1.0) / (n + 1.0)) ** 2
        through = ((1.0 - reflect) / (1.0 + reflect)) ** 2
        hit = abs(through - grey) < 0.004
        out.append(text(746, row, "n %.3f" % n, 11, INK if hit else MUTED, mono=True,
                        weight="700" if hit else None))
        out.append(text(900, row, "%.3f" % through, 11, GREEN_DK if hit else MUTED, anchor="end",
                        mono=True, weight="700" if hit else None))
        out.append(text(746, row + 15, label, 9.5, MUTED))
        row += rowStep
    out.append('<line x1="742" y1="%d" x2="904" y2="%d" stroke="%s"/>' % (row - 14, row - 14, LINE))
    out.append(text(746, row + 6, "measured", 11, RED, weight="700"))
    out.append(text(900, row + 6, "%.3f" % grey, 11, RED, anchor="end", mono=True, weight="700"))
    out.append(text(78, 344, "T = ( (1 \u2212 R) / (1 + R) )\u00b2      with      R = ( (n \u2212 1) / "
                             "(n + 1) )\u00b2", 13, INK, mono=True))
    out.append(text(78, 374, "The measured %.3f lands on n \u2248 %.2f. Polystyrol (n = 1.59) predicts "
                             "%.3f \u2014 five points of transmission lower than what was seen."
                    % (grey, impliedIndex(grey), 0.812), 11.5, MUTED))
    out.append(text(78, 400, "\u26a0 A consistency check, not an assay of the plastic: the walls are curved, "
                             "so part of the loss is light refracted out of the ROI rather than", 11.5, MUTED))
    out.append(text(78, 418, "reflected \u2014 and an exposure difference between the two frames would move "
                             "the measured number without the jar moving at all.", 11.5, MUTED))
    return writeSvg("jar_fresnel.svg", W, H, out)


# --------------------------------------------------------------------------- entry point

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digitise", action="store_true",
                        help="re-read the two PNGs and rewrite the committed CSV")
    args = parser.parse_args()

    if args.digitise:
        direct, jar = digitise("direct"), digitise("jar")
        writeCsv(direct, jar)
    else:
        direct, jar = readCsv()

    ratio, grey = report(direct, jar)
    print()
    figureOverlay(direct, jar, grey)
    figureRatio(ratio, grey)
    figureFresnel(grey)


if __name__ == "__main__":
    main()
