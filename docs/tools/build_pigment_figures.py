#!/usr/bin/env python3
"""
Generator for the schematic pigment figures in *Light, Pigment and Solvent*.

    OUTPUT:  docs/figures/pigment_macrocycle.svg      -- chlorin vs porphyrin, the one bond that differs
             docs/figures/pigment_qband_symmetry.svg  -- D4h -> D2h and what it does to the Q bands
             docs/figures/pigment_four_molecules.svg  -- the 2x2 family; which two are in our oil
             docs/figures/pigment_far_window_slope.svg -- why redistribution flattens the 600-630 slope

SVG, not PNG: these are line diagrams, they must stay sharp at any zoom in the PDF, and the renderer
embeds them as data URIs which Chrome rasterises at print resolution.

⚠ These are SCHEMATICS, not structural formulae. The macrocycle is drawn as four idealised pyrrole
pentagons around a metal; substituents, ring E and stereochemistry are omitted or stylised. Every
chemical claim they make is limited to: four pyrrole subunits, a central Mg, the ring-D C17-C18 bond,
and the phytol ester. Those are the only points the text draws from them.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_pigment_figures.py
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "docs", "figures")

INK, MUTED, LINE = "#1c211c", "#5c655c", "#b9c1b9"
GREEN, GREEN_DK, ACCENT = "#3f7d3f", "#2f5d2f", "#8d5524"
BLUE, RED, PANEL = "#3a5fa8", "#b03a3a", "#f5f8f5"

FONT = 'font-family="Segoe UI,Helvetica Neue,Arial,sans-serif"'


def polar(cx, cy, radius, degrees):
    angle = math.radians(degrees)
    return cx + radius * math.cos(angle), cy - radius * math.sin(angle)


# --------------------------------------------------------------------------- figure 1

def pyrrole(cx, cy, theta, highlight=False, reduced=False):
    """One pyrrole ring pointing its nitrogen at the macrocycle centre.

    Returns (svg, alphaAngles) — alphaAngles are the two outward bond attachment angles that the
    methine bridges connect to."""
    nitrogen = polar(cx, cy, 40, theta)
    alphaA, alphaB = polar(cx, cy, 74, theta + 25), polar(cx, cy, 74, theta - 25)
    betaA, betaB = polar(cx, cy, 108, theta + 16), polar(cx, cy, 108, theta - 16)

    points = " ".join("%.1f,%.1f" % p for p in (nitrogen, alphaA, betaA, betaB, alphaB))
    fill = "#eef4ee" if highlight else "#ffffff"
    stroke = GREEN_DK if highlight else INK
    width = 2.4 if highlight else 1.6
    out = ['<polygon points="%s" fill="%s" stroke="%s" stroke-width="%.1f"/>'
           % (points, fill, stroke, width)]

    # the C17-C18 bond = the OUTER edge, betaA--betaB. Double in a porphyrin, single in a chlorin.
    if not reduced:
        inner = [polar(cx, cy, 99, theta + 13), polar(cx, cy, 99, theta - 13)]
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.2"/>'
                   % (inner[0][0], inner[0][1], inner[1][0], inner[1][1], RED if highlight else INK))
    else:
        for point, offset in ((betaA, theta + 16), (betaB, theta - 16)):
            tip = polar(cx, cy, 128, offset)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>'
                       % (point[0], point[1], tip[0], tip[1], GREEN_DK))
            out.append('<text x="%.1f" y="%.1f" %s font-size="12" fill="%s" text-anchor="middle">H</text>'
                       % (tip[0], tip[1] + 4, FONT, GREEN_DK))

    out.append('<text x="%.1f" y="%.1f" %s font-size="12.5" font-weight="700" fill="%s" '
               'text-anchor="middle">N</text>' % (nitrogen[0], nitrogen[1] + 4.5, FONT, INK))
    return "".join(out), (theta + 25, theta - 25)


def macrocycle(cx, cy, reduced):
    """The four-pyrrole ring with Mg at the centre. Ring D (lower left) is the one that differs."""
    out = []
    ringAngles = {"A": 135, "B": 45, "C": 315, "D": 225}
    alphas = {}
    for label, theta in ringAngles.items():
        svg, alpha = pyrrole(cx, cy, theta, highlight=(label == "D"),
                             reduced=(reduced and label == "D"))
        out.append(svg)
        alphas[label] = alpha
        tx, ty = polar(cx, cy, 82, theta)
        out.append('<text x="%.1f" y="%.1f" %s font-size="12" font-style="italic" fill="%s" '
                   'text-anchor="middle">%s</text>'
                   % (tx, ty + 4, FONT, GREEN_DK if label == "D" else MUTED, label))

    # methine bridges at 0/90/180/270 joining neighbouring alpha carbons
    for bridge, (one, two) in ((90, ("A", "B")), (180, ("A", "D")), (270, ("D", "C")), (0, ("C", "B"))):
        point = polar(cx, cy, 88, bridge)
        for label, index in ((one, 0), (two, 1)):
            start = polar(cx, cy, 74, alphas[label][index] if label in (one,) else alphas[label][index])
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.6"/>'
                       % (start[0], start[1], point[0], point[1], INK))

    # Mg and its four coordination bonds
    for theta in ringAngles.values():
        nitrogen = polar(cx, cy, 40, theta)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2" '
                   'stroke-dasharray="3,2.5"/>' % (cx, cy, nitrogen[0], nitrogen[1], MUTED))
    out.append('<circle cx="%.1f" cy="%.1f" r="15" fill="%s" opacity="0.16"/>' % (cx, cy, GREEN))
    out.append('<text x="%.1f" y="%.1f" %s font-size="13.5" font-weight="700" fill="%s" '
               'text-anchor="middle">Mg</text>' % (cx, cy + 5, FONT, GREEN_DK))

    # phytol tail off ring D
    start = polar(cx, cy, 108, 225 - 16)
    path = ["M %.1f %.1f" % start]
    x, y = start
    for step in range(5):
        x, y = x - 15, y + (9 if step % 2 == 0 else -9)
        path.append("L %.1f %.1f" % (x, y))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.5"/>' % (" ".join(path), ACCENT))
    out.append('<text x="%.1f" y="%.1f" %s font-size="11" fill="%s">phytol tail</text>'
               % (x - 4, y + 18, FONT, ACCENT))
    return "".join(out)


def figureMacrocycle():
    width, height = 900, 470
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           % (width, height, width, height),
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height)]

    for index, (title, subtitle, reduced, colour) in enumerate((
            ("protochlorophyll a", "ring D NOT reduced  →  a PORPHYRIN", False, BLUE),
            ("chlorophyll a", "ring D reduced  →  a CHLORIN", True, GREEN_DK))):
        left = 20 + index * 450
        out.append('<rect x="%d" y="14" width="410" height="442" rx="9" fill="%s" stroke="%s"/>'
                   % (left, PANEL, LINE))
        out.append('<text x="%d" y="44" %s font-size="16" font-weight="700" font-style="italic" '
                   'fill="%s" text-anchor="middle">%s</text>'
                   % (left + 205, FONT, colour, title))
        out.append('<text x="%d" y="65" %s font-size="12.5" fill="%s" text-anchor="middle">%s</text>'
                   % (left + 205, FONT, MUTED, subtitle))
        out.append(macrocycle(left + 205, 250, reduced))
        note = ("C17=C18 double bond intact" if not reduced else "C17–C18 saturated (+2 H)")
        out.append('<text x="%d" y="424" %s font-size="12.5" font-weight="700" fill="%s" '
                   'text-anchor="middle">%s</text>' % (left + 205, FONT, RED if not reduced else GREEN_DK, note))
        band = ("Qy ~623–626 nm, weaker" if not reduced else "Qy ~662 nm, strong")
        out.append('<text x="%d" y="443" %s font-size="12" fill="%s" text-anchor="middle">%s</text>'
                   % (left + 205, FONT, MUTED, band))

    out.append('<text x="450" y="466" %s font-size="10.5" fill="%s" text-anchor="middle">'
               'Schematic — substituents and ring E omitted; only the ring-D bond is to scale as an idea.'
               '</text>' % (FONT, MUTED))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- figure 2

def ringGlyph(cx, cy, metal):
    """A small square-on-point macrocycle glyph with the transition dipoles drawn on it."""
    out = []
    corners = [polar(cx, cy, 52, angle) for angle in (90, 0, 270, 180)]
    points = " ".join("%.1f,%.1f" % p for p in corners)
    out.append('<polygon points="%s" fill="#ffffff" stroke="%s" stroke-width="1.8"/>' % (points, INK))
    for (px, py) in corners:
        out.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#ffffff" stroke="%s" stroke-width="1.4"/>'
                   % (px, py, INK))
        out.append('<text x="%.1f" y="%.1f" %s font-size="10.5" font-weight="700" fill="%s" '
                   'text-anchor="middle">N</text>' % (px, py + 3.7, FONT, INK))
    if metal:
        out.append('<circle cx="%.1f" cy="%.1f" r="14" fill="%s" opacity="0.18"/>' % (cx, cy, GREEN))
        out.append('<text x="%.1f" y="%.1f" %s font-size="12" font-weight="700" fill="%s" '
                   'text-anchor="middle">Mg</text>' % (cx, cy + 4.5, FONT, GREEN_DK))
        for (px, py) in corners:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.1" '
                       'stroke-dasharray="3,2.5"/>' % (cx, cy, px, py, MUTED))
    else:
        # two protons on the VERTICAL axis -> that axis is now distinguishable from the horizontal
        for (px, py) in (corners[0], corners[2]):
            out.append('<text x="%.1f" y="%.1f" %s font-size="11" font-weight="700" fill="%s" '
                       'text-anchor="middle">H</text>'
                       % (px + 17, py + 4, FONT, RED))
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4"/>'
                       % (px + 7, py, px + 11, py, RED))
    return "".join(out)


def dipoles(cx, cy, split):
    """The two in-plane transition dipoles: equal (degenerate) or unequal (split).

    Drawn as two half-arrows from the centre outwards rather than one double-headed line, because
    `marker-start` with orient="auto" points along the path and would render the head backwards."""
    out = []
    # both equal when degenerate; when split the x dipole is drawn shorter to signal the higher
    # energy / weaker band. Kept clear of the ring glyph (N nodes sit at radius 52 + 9).
    lengthY = 88 if not split else 104
    lengthX = 88 if not split else 70
    for dx, dy, length, colour, marker in ((0, -1, lengthY, GREEN_DK, "head-g"),
                                           (0, 1, lengthY, GREEN_DK, "head-g"),
                                           (-1, 0, lengthX, BLUE, "head-b"),
                                           (1, 0, lengthX, BLUE, "head-b")):
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3" '
                   'marker-end="url(#%s)"/>'
                   % (cx, cy, cx + dx * length, cy + dy * length, colour, marker))
    # beside the shaft near the tip, not above it — above would run into the panel subtitle
    out.append('<text x="%.1f" y="%.1f" %s font-size="12.5" font-weight="700" fill="%s">%s</text>'
               % (cx + 14, cy - lengthY + 18, FONT, GREEN_DK, "y" if not split else "Qy"))
    out.append('<text x="%.1f" y="%.1f" %s font-size="12.5" font-weight="700" fill="%s">%s</text>'
               % (cx + lengthX + 10, cy + 4, FONT, BLUE, "x" if not split else "Qx"))
    return "".join(out)


def levels(x, y, split):
    """A small energy-level diagram: ground state, Q origin(s), vibronic satellites."""
    out = ['<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.4"/>'
           % (x, y + 150, x + 150, y + 150, INK),
           '<text x="%d" y="%d" %s font-size="11.5" fill="%s">S%s</text>'
           % (x + 155, y + 154, FONT, MUTED, "₀")]
    if not split:
        rows = [(y + 46, "Q(1,0)", MUTED, "4,3"), (y + 86, "Q(0,0)", GREEN_DK, None)]
    else:
        rows = [(y + 20, "Qx(1,0)", MUTED, "4,3"), (y + 46, "Qx(0,0)", BLUE, None),
                (y + 86, "Qy(1,0)", MUTED, "4,3"), (y + 112, "Qy(0,0)", GREEN_DK, None)]
    for top, label, colour, dash in rows:
        dashes = ' stroke-dasharray="%s"' % dash if dash else ""
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.4"%s/>'
                   % (x, top, x + 150, top, colour, dashes))
        out.append('<text x="%d" y="%d" %s font-size="11.5" font-weight="%s" fill="%s">%s</text>'
                   % (x + 155, top + 4, FONT, "700" if not dash else "400", colour, label))
    caption = ("one Q origin — x and y at the SAME energy" if not split
               else "two Q origins — the degeneracy is lifted")
    out.append('<text x="%d" y="%d" %s font-size="11" font-style="italic" fill="%s" '
               'text-anchor="middle">%s</text>' % (x + 75, y + 180, FONT, ACCENT, caption))
    if split:                                    # brace showing what separated
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.2" '
                   'stroke-dasharray="2,2"/>' % (x - 12, y + 46, x - 12, y + 112, ACCENT))
        out.append('<text x="%d" y="%d" %s font-size="11" font-style="italic" fill="%s" '
                   'text-anchor="end">split</text>' % (x - 16, y + 83, FONT, ACCENT))
    return "".join(out)


def spectrum(x, y, split):
    """A schematic absorbance trace: Soret plus the Q region, two peaks or four."""
    width, height = 300, 96
    out = ['<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.3"/>'
           % (x, y + height, x + width, y + height, MUTED)]
    peaks = [(0.10, 0.95, 9, GREEN_DK)]                       # the Soret
    if not split:
        peaks += [(0.60, 0.16, 11, MUTED), (0.80, 0.30, 11, GREEN_DK)]
    else:
        peaks += [(0.44, 0.12, 10, BLUE), (0.56, 0.17, 10, BLUE),
                  (0.72, 0.13, 10, MUTED), (0.86, 0.26, 10, GREEN_DK)]
    path = ["M %d %d" % (x, y + height)]
    for step in range(0, width + 1, 3):
        fraction = step / width
        value = sum(amplitude * math.exp(-((fraction - centre) * width / spread) ** 2 / 2)
                    for centre, amplitude, spread, _ in peaks)
        path.append("L %.1f %.1f" % (x + step, y + height - min(value, 1.02) * height))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2"/>' % (" ".join(path), INK))
    labels = ([("Soret", 0.10), ("Q(1,0)", 0.60), ("Q(0,0)", 0.80)] if not split else
              [("Soret", 0.10), ("IV", 0.44), ("III", 0.56), ("II", 0.72), ("I", 0.86)])
    for text, centre in labels:
        out.append('<text x="%.1f" y="%d" %s font-size="10" fill="%s" text-anchor="middle">%s</text>'
                   % (x + centre * width, y + height + 14, FONT, MUTED, text))
    out.append('<text x="%d" y="%d" %s font-size="10.5" fill="%s">wavelength →</text>'
               % (x + width - 74, y + height + 30, FONT, MUTED))
    return "".join(out)


def figureSymmetry():
    width, height = 900, 700
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           % (width, height, width, height),
           '<defs>',
           '<marker id="head-g" markerWidth="7" markerHeight="7" refX="5.4" refY="3.2" orient="auto">'
           '<path d="M0,0 L6,3.2 L0,6.4 z" fill="%s"/></marker>' % GREEN_DK,
           '<marker id="head-b" markerWidth="7" markerHeight="7" refX="5.4" refY="3.2" orient="auto">'
           '<path d="M0,0 L6,3.2 L0,6.4 z" fill="%s"/></marker>' % BLUE,
           '</defs>',
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height)]

    headers = (("magnesium PRESENT  —  D₄ₕ", "intact protochlorophyll", GREEN_DK, False),
               ("magnesium REMOVED  —  D₂ₕ", "protopheophytin (roasted / aged)", RED, True))
    for index, (title, subtitle, colour, split) in enumerate(headers):
        left = 18 + index * 452
        out.append('<rect x="%d" y="12" width="412" height="650" rx="9" fill="%s" stroke="%s"/>'
                   % (left, PANEL, LINE))
        out.append('<text x="%d" y="42" %s font-size="15.5" font-weight="700" fill="%s" '
                   'text-anchor="middle">%s</text>' % (left + 206, FONT, colour, title))
        out.append('<text x="%d" y="63" %s font-size="12" fill="%s" text-anchor="middle">%s</text>'
                   % (left + 206, FONT, MUTED, subtitle))
        out.append(dipoles(left + 206, 178, split))
        out.append(ringGlyph(left + 206, 178, metal=not split))
        out.append('<text x="%d" y="%d" %s font-size="11.5" font-style="italic" fill="%s" '
                   'text-anchor="middle">%s</text>'
                   % (left + 206, 292, FONT, ACCENT,
                      "four-fold axis: x and y equivalent" if not split
                      else "the two H sit on ONE axis: x ≠ y"))
        out.append(levels(left + 46, 318, split))
        out.append(spectrum(left + 56, 528, split))

    out.append('<text x="450" y="688" %s font-size="10.5" fill="%s" text-anchor="middle">'
               'Schematic. Free-base band numbering I–IV runs from the longest wavelength: '
               'I = Qy(0,0), II = Qy(1,0), III = Qx(0,0), IV = Qx(1,0).</text>' % (FONT, MUTED))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- figure 3: the family

def moleculeCell(x, y, w, h, name, meaning, magnesium, reduced, ours):
    """One cell of the 2x2: a mini glyph plus the molecule's two defining modifications."""
    out = ['<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" stroke="%s" '
           'stroke-width="%s"/>' % (x, y, w, h, "#eef4ee" if ours else "#ffffff",
                                    GREEN_DK if ours else LINE, "2.2" if ours else "1.2")]
    if ours:
        out.append('<text x="%d" y="%d" %s font-size="10" font-weight="700" fill="%s" '
                   'text-anchor="end">IN OUR OIL</text>' % (x + w - 12, y + 20, FONT, GREEN_DK))
    out.append('<text x="%d" y="%d" %s font-size="14.5" font-weight="700" font-style="italic" '
               'fill="%s">%s</text>' % (x + 16, y + 38, FONT, GREEN_DK if ours else INK, name))
    out.append('<text x="%d" y="%d" %s font-size="11.5" fill="%s">%s</text>'
               % (x + 16, y + 57, FONT, MUTED, meaning))

    cx, cy = x + 54, y + 104
    corners = [polar(cx, cy, 27, angle) for angle in (90, 0, 270, 180)]
    out.append('<polygon points="%s" fill="#ffffff" stroke="%s" stroke-width="1.5"/>'
               % (" ".join("%.1f,%.1f" % p for p in corners), INK))
    if magnesium:
        out.append('<circle cx="%.1f" cy="%.1f" r="11" fill="%s" opacity="0.20"/>' % (cx, cy, GREEN))
        out.append('<text x="%.1f" y="%.1f" %s font-size="10.5" font-weight="700" fill="%s" '
                   'text-anchor="middle">Mg</text>' % (cx, cy + 4, FONT, GREEN_DK))
    else:
        out.append('<text x="%.1f" y="%.1f" %s font-size="10.5" font-weight="700" fill="%s" '
                   'text-anchor="middle">2 H</text>' % (cx, cy + 4, FONT, RED))
    out.append('<text x="%d" y="%d" %s font-size="11" fill="%s">%s</text>'
               % (x + 96, y + 92, FONT, GREEN_DK if magnesium else RED,
                  "✔ magnesium held" if magnesium else "✘ magnesium GONE"))
    out.append('<text x="%d" y="%d" %s font-size="11" fill="%s">%s</text>'
               % (x + 96, y + 112, FONT, INK,
                  "ring D reduced (chlorin)" if reduced else "ring D intact (porphyrin)"))
    out.append('<text x="%d" y="%d" %s font-size="10.5" font-style="italic" fill="%s">%s</text>'
               % (x + 96, y + 132, FONT, MUTED,
                  "Q bands SPLIT — Qx / Qy" if not magnesium else "Q bands degenerate"))
    return "".join(out)


def figureFamily():
    width, height = 900, 470
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           % (width, height, width, height),
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height),
           '<text x="248" y="34" %s font-size="13" font-weight="700" fill="%s" '
           'text-anchor="middle">magnesium PRESENT</text>' % (FONT, GREEN_DK),
           '<text x="660" y="34" %s font-size="13" font-weight="700" fill="%s" '
           'text-anchor="middle">magnesium REMOVED  (roasting, ageing)</text>' % (FONT, RED)]

    out.append('<text x="26" y="128" %s font-size="12.5" font-weight="700" fill="%s" '
               'transform="rotate(-90 26 128)" text-anchor="middle">ring D INTACT</text>' % (FONT, INK))
    out.append('<text x="26" y="330" %s font-size="12.5" font-weight="700" fill="%s" '
               'transform="rotate(-90 26 330)" text-anchor="middle">ring D REDUCED</text>' % (FONT, MUTED))

    cells = ((44, 48, "protochlorophyll a", "the pumpkin seed's green pigment", True, False, True),
             (456, 48, "protopheophytin a", "what roasting and storage make of it", False, False, True),
             (44, 250, "chlorophyll a", "ordinary leaf chlorophyll", True, True, False),
             (456, 250, "pheophytin a", "why overcooked greens go olive-drab", False, True, False))
    for x, y, name, meaning, magnesium, reduced, ours in cells:
        out.append(moleculeCell(x, y, 400, 170, name, meaning, magnesium, reduced, ours))

    out.append('<line x1="410" y1="440" x2="452" y2="440" stroke="%s" stroke-width="2.4" '
               'marker-end="url(#head-r)"/>' % RED)
    out.append('<defs><marker id="head-r" markerWidth="8" markerHeight="8" refX="6" refY="3.4" '
               'orient="auto"><path d="M0,0 L7,3.4 L0,6.8 z" fill="%s"/></marker></defs>' % RED)
    out.append('<text x="404" y="444" %s font-size="11.5" font-weight="700" fill="%s" '
               'text-anchor="end">the degradation our verdict measures</text>' % (FONT, RED))
    out.append('<text x="466" y="444" %s font-size="11.5" fill="%s">heat + acid strip the Mg²⁺</text>'
               % (FONT, MUTED))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- figure 4: the slope

def bandSum(lam, peaks):
    return sum(a * math.exp(-((lam - c) / s) ** 2 / 2) for c, a, s in peaks)


def slopePanel(x, y, w, h, peaks, title, subtitle, colour, lo=530.0, hi=690.0):
    """A Q-region spectrum with the 600-630 window shaded and the in-window trend drawn."""
    def px(nm):
        return x + (nm - lo) / (hi - lo) * w

    def py(value):
        return y + h - min(value, 1.15) / 1.15 * h

    out = ['<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" stroke="%s"/>'
           % (x - 26, y - 46, w + 52, h + 104, PANEL, LINE),
           '<text x="%.1f" y="%d" %s font-size="14" font-weight="700" fill="%s" '
           'text-anchor="middle">%s</text>' % (x + w / 2, y - 26, FONT, colour, title),
           '<text x="%.1f" y="%d" %s font-size="11.5" fill="%s" text-anchor="middle">%s</text>'
           % (x + w / 2, y - 8, FONT, MUTED, subtitle),
           # the measurement window
           '<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" opacity="0.13"/>'
           % (px(600), y, px(630) - px(600), h, ACCENT),
           '<text x="%.1f" y="%d" %s font-size="10.5" font-weight="700" fill="%s" '
           'text-anchor="middle">600–630 window</text>' % ((px(600) + px(630)) / 2, y + 14, FONT, ACCENT),
           # the capture clamp
           '<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1.6" '
           'stroke-dasharray="5,3"/>' % (px(630), y, px(630), y + h, RED),
           '<text x="%.1f" y="%d" %s font-size="10" font-weight="700" fill="%s">we see nothing</text>'
           % (px(630) + 5, y + h - 26, FONT, RED),
           '<text x="%.1f" y="%d" %s font-size="10" font-weight="700" fill="%s">beyond here</text>'
           % (px(630) + 5, y + h - 13, FONT, RED),
           '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.3"/>'
           % (x, y + h, x + w, y + h, MUTED)]

    for centre, amplitude, spread in peaks:                       # the individual transitions
        path = ["M %.1f %.1f" % (px(lo), py(0))]
        for step in range(0, 321):
            nm = lo + (hi - lo) * step / 320
            path.append("L %.1f %.1f" % (px(nm), py(bandSum(nm, [(centre, amplitude, spread)]))))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.1" stroke-dasharray="4,3" '
                   'opacity="0.75"/>' % (" ".join(path), MUTED))

    path = ["M %.1f %.1f" % (px(lo), py(bandSum(lo, peaks)))]      # their sum: what is measured
    for step in range(0, 321):
        nm = lo + (hi - lo) * step / 320
        path.append("L %.1f %.1f" % (px(nm), py(bandSum(nm, peaks))))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4"/>' % (" ".join(path), INK))

    left = sum(bandSum(nm, peaks) for nm in (600, 603, 606, 610)) / 4.0
    right = sum(bandSum(nm, peaks) for nm in (620, 623, 626, 630)) / 4.0
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3.4"/>'
               % (px(605), py(left), px(625), py(right), colour))
    for nm, value in ((605, left), (625, right)):
        out.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s"/>' % (px(nm), py(value), colour))
    # fixed position just left of the window and below its caption: clear of the curve in both panels
    out.append('<text x="%.1f" y="%d" %s font-size="12" font-weight="700" fill="%s" '
               'text-anchor="end">slope %s</text>'
               % (px(598), y + 42, FONT, colour,
                  "STEEP" if right - left > 0.25 else "nearly FLAT"))

    for nm in (550, 575, 600, 625, 650, 675):
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>'
                   % (px(nm), y + h, px(nm), y + h + 4, MUTED))
        out.append('<text x="%.1f" y="%d" %s font-size="9.5" fill="%s" text-anchor="middle">%d</text>'
                   % (px(nm), y + h + 16, FONT, MUTED, nm))
    out.append('<text x="%.1f" y="%d" %s font-size="10.5" fill="%s" text-anchor="middle">'
               'wavelength (nm)</text>' % (x + w / 2, y + h + 33, FONT, MUTED))
    return "".join(out), right - left


def figureSlope():
    width, height = 900, 660
    intact = [(624, 1.00, 13), (572, 0.42, 14)]
    degraded = [(630, 0.36, 13), (592, 0.22, 13), (568, 0.60, 13), (536, 0.32, 13)]

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           % (width, height, width, height),
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height),
           '<text x="450" y="26" %s font-size="14.5" font-weight="700" fill="%s" '
           'text-anchor="middle">Why redistributing the Q intensity FLATTENS the 600–630 slope</text>'
           % (FONT, INK)]

    topPanel, riseIntact = slopePanel(60, 96, 780, 170, intact,
                                      "INTACT protochlorophyll  —  magnesium present",
                                      "one dominant Q origin, sitting just past our window edge",
                                      GREEN_DK)
    bottomPanel, riseDegraded = slopePanel(60, 372, 780, 170, degraded,
                                           "DEGRADED protopheophytin  —  magnesium gone",
                                           "the same intensity split across four bands, spread to the blue",
                                           ACCENT)
    out += [topPanel, bottomPanel]

    out.append('<text x="450" y="624" %s font-size="11.5" fill="%s" text-anchor="middle">'
               'The window is narrow and sits on a FLANK, so its slope reports the height of the nearest '
               'peak — not the total pigment.</text>' % (FONT, INK))
    out.append('<text x="450" y="644" %s font-size="11" fill="%s" text-anchor="middle">'
               'Schematic; band positions for the degraded form are illustrative. Modelled slope ratio '
               '%.1f× — measured 4.5× (green 0.0547, brown 0.0121).</text>'
               % (FONT, MUTED, riseIntact / riseDegraded if riseDegraded else 0))
    out.append("</svg>")
    return "".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("pigment_macrocycle.svg", figureMacrocycle()),
                      ("pigment_qband_symmetry.svg", figureSymmetry()),
                      ("pigment_four_molecules.svg", figureFamily()),
                      ("pigment_far_window_slope.svg", figureSlope())):
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(svg)
        print("wrote", path)


if __name__ == "__main__":
    main()
