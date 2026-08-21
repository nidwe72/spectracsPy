#!/usr/bin/env python3
"""
Generator for the SEE-SAW figure — how browning redistributes red absorption between two bands.

    OUTPUT:  docs/figures/tilt_seesaw.svg

The mechanism drawn here is the same one `pigment_qband_symmetry.svg` establishes from symmetry:
losing the central Mg splits the Q states and moves oscillator strength out of the lowest one. This
figure adds what that looks like as a MEASUREMENT, and why a metric built as a DIFFERENCE of the two
bands sees twice as much of it as a metric that reads one band.

⚠ The numbers are MEASURED, not schematic — class means over the 88 labelled isopropanol runs of the
report archive (diffuser-IN runs and the opaque fill excluded), each band read as

        100 x [ A(band) - A(500-560) ] / A(448-460)

so they are concentration-free and directly comparable. `SPEC_metric_research.md` §13 carries the
derivation and the per-oil table; `ROADMAP.md`'s 2026-08-21 evening block records the session.

⚠ The "tilt" drawn here is NOT the shipped `dQ100`, which divides by sd(448-626) rather than by the
Soret flank. The two track each other at r = 0.992 over the same corpus, which is what licenses the
figure — but the scales differ and the caption says so.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_tilt_figures.py
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "docs", "figures")

INK, MUTED, LINE = "#1c211c", "#5c655c", "#b9c1b9"
GREEN, GREEN_DK, ACCENT = "#3f7d3f", "#2f5d2f", "#8d5524"
BLUE, RED, PANEL = "#3a5fa8", "#b03a3a", "#f5f8f5"
GREY = "#b9bec6"
FONT = 'font-family="Segoe UI,Helvetica Neue,Arial,sans-serif"'
MONO = 'font-family="Consolas,DejaVu Sans Mono,monospace"'

# ---- the measured class means (see the module docstring for provenance) ----
G_Q, G_QY = 15.80, 12.78          # green oils: the 568 nm end, the 624 nm end
B_Q, B_QY = 20.00, 7.55           # brown oils
G_PIVOT, B_PIVOT = (G_Q + G_QY) / 2.0, (B_Q + B_QY) / 2.0
G_HALF, B_HALF = (G_Q - G_QY) / 2.0, (B_Q - B_QY) / 2.0


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


# --------------------------------------------------------------------------- the see-saw panel

def seesaw(cx, cy, left, right, label, colour):
    """One plank. The HEAVIER end sits LOWER, and the tilt is proportional to the difference."""
    half, angle = 100.0, min(18.0, 1.7 * (left - right))
    dx, dy = half * math.cos(math.radians(angle)), half * math.sin(math.radians(angle))
    out = ['<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
           % (cx - 13, cy + 30, cx + 13, cy + 30, cx, cy + 2, MUTED)]
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5" '
               'stroke-linecap="round"/>' % (cx - dx, cy + dy, cx + dx, cy - dy, INK))
    for sign, value in ((-1, left), (+1, right)):
        px, py = cx + sign * dx, cy - sign * dy
        radius = 3.9 * math.sqrt(value)
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.4" '
                   'fill-opacity="0.92"/>' % (px, py - radius - 3, radius, colour, INK))
        out.append(text(px, py - radius - 0.5, "%.1f" % value, 12.5, "#ffffff", "middle", "bold"))
    out.append(text(cx - half - 34, cy + 4, label, 13, colour, "end", "bold"))
    out.append(text(cx, cy + 48, "total  %.1f" % (left + right), 11.5, INK, "middle", "bold"))
    return "".join(out)


# --------------------------------------------------------------------------- the bar panel

BASE, UNIT, BARW = 600.0, 11.5, 40.0


def yOf(value):
    return BASE - value * UNIT


def bar(x, y0, y1, fill, stroke=INK, opacity=1.0, pattern=None):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="%.2f" '
            'stroke="%s" stroke-width="1.1"/>'
            % (x - BARW / 2, min(y0, y1), BARW, abs(y1 - y0),
               pattern if pattern else fill, opacity, stroke))


def bandBar(x, pivot, value, colour, adds):
    out = []
    if adds:
        out.append(bar(x, BASE, yOf(pivot), GREY))
        out.append(bar(x, yOf(pivot), yOf(value), colour))
        out.append(text(x, (yOf(pivot) + yOf(value)) / 2 + 4, "+%.1f" % (value - pivot),
                        11, "#ffffff", "middle", "bold"))
        out.append(text(x, yOf(value) - 8, "%.1f" % value, 13, colour, "middle", "bold"))
        out.append(text(x, yOf(pivot) + 16, "pivot", 9.5, "#3a3f46", "middle", "bold"))
        out.append(text(x, yOf(pivot) + 27, "%.1f" % pivot, 9.5, "#3a3f46", "middle", "bold"))
    else:
        out.append(bar(x, BASE, yOf(value), GREY))
        out.append(bar(x, yOf(value), yOf(pivot), colour, colour, 0.28, "url(#hatch)"))
        out.append(text(x, (yOf(value) + yOf(pivot)) / 2 + 4, "−%.1f" % (pivot - value),
                        11, colour, "middle", "bold"))
        out.append(text(x, yOf(value) + 17, "%.1f" % value, 13, colour, "middle", "bold"))
        out.append(text(x, yOf(pivot) - 10, "pivot %.1f" % pivot, 9.5, "#3a3f46", "middle", "bold"))
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4" '
               'stroke-dasharray="5 3"/>' % (x - BARW / 2, yOf(pivot), x + BARW / 2, yOf(pivot), INK))
    return "".join(out)


def tiltBar(x, value, colour, high, low):
    return (bar(x, BASE, yOf(value), colour)
            + text(x, yOf(value) - 22, "%.1f − %.1f" % (high, low), 9.5, colour, "middle", "bold", None, True)
            + text(x, yOf(value) - 8, "%.1f" % value, 13, colour, "middle", "bold")
            + text(x, (BASE + yOf(value)) / 2 + 4, "2 × %.1f" % (value / 2),
                   10.5, "#ffffff", "middle", "bold"))


def gap(x, v0, v1, label):
    out = ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.8"/>'
           % (x, yOf(v0), x, yOf(v1), RED)]
    for v, direction in ((v0, 1), (v1, -1)):
        out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
                   % (x, yOf(v), x - 4, yOf(v) - direction * 8, x + 4, yOf(v) - direction * 8, RED))
    out.append(text(x + 7, (yOf(v0) + yOf(v1)) / 2 + 4, label, 11.5, RED, "start", "bold"))
    return "".join(out)


def figureSeesaw():
    width, height = 900, 800
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           % (width, height, width, height)]
    out.append('<defs><pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" '
               'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" stroke="%s" '
               'stroke-width="2.4"/></pattern></defs>' % ACCENT)
    out.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height))

    out.append(text(450, 32, "Browning does not create red absorption — it MOVES it",
                    18, INK, "middle", "bold"))
    out.append(text(450, 54, "the same total, split differently between the two bands",
                    12.5, MUTED, "middle", None, "italic"))

    # ---- top left: the mechanism ----
    out.append('<rect x="18" y="72" width="404" height="244" rx="7" fill="%s"/>' % PANEL)
    out.append(text(34, 94, "the mechanism", 13, INK, "start", "bold"))
    out.append(seesaw(258, 140, G_Q, G_QY, "GREEN oil", GREEN))
    out.append(seesaw(258, 252, B_Q, B_QY, "BROWN oil", ACCENT))
    out.append(text(158, 308, "568 nm end", 11.5, BLUE, "middle", "bold"))
    out.append(text(358, 308, "624 nm end", 11.5, BLUE, "middle", "bold"))

    # ---- top right: the same thing as arithmetic ----
    out.append('<rect x="436" y="72" width="446" height="244" rx="7" fill="%s"/>' % PANEL)
    out.append(text(452, 94, "the same thing, in the numbers a metric uses",
                    13, INK, "start", "bold"))
    out.append(text(660, 116, "Q% reads ONE end of this see-saw. A DIFFERENCE reads the",
                    11.5, INK, "middle"))
    out.append(text(660, 132, "whole tilt — and drops the pivot entirely.", 11.5, INK, "middle"))

    out.append(text(660, 158, "pivot  = ( 568 end + 624 end ) / 2", 11.5, BLUE, "middle", "bold", None, True))
    out.append(text(660, 176, "½·tilt = ( 568 end − 624 end ) / 2", 11.5, BLUE, "middle", "bold", None, True))
    out.append(text(660, 198, "green  (15.8+12.8)/2 = 14.3   (15.8−12.8)/2 = 1.5",
                    10.5, GREEN_DK, "middle", "bold", None, True))
    out.append(text(660, 214, "brown  (20.0+ 7.5)/2 = 13.8   (20.0− 7.5)/2 = 6.2",
                    10.5, ACCENT, "middle", "bold", None, True))
    out.append('<line x1="470" y1="228" x2="850" y2="228" stroke="%s" stroke-width="1"/>' % LINE)
    out.append(text(660, 248, "Q% = pivot + ½·tilt      624 end = pivot − ½·tilt",
                    11.5, BLUE, "middle", "bold", None, True))
    out.append(text(660, 268, "green   14.3 + 1.5 = 15.8     14.3 − 1.5 = 12.8",
                    10.5, GREEN_DK, "middle", "bold", None, True))
    out.append(text(660, 284, "brown   13.8 + 6.2 = 20.0     13.8 − 6.2 =  7.5",
                    10.5, ACCENT, "middle", "bold", None, True))
    out.append(text(660, 306, "the same pivot, plus and minus the SAME half-tilt",
                    10.5, MUTED, "middle", None, "italic"))

    # ---- the bars ----
    for cx, title, sub in ((284, "the 568 nm end", "= Q%   (pivot + ½ tilt)"),
                           (484, "the 624 nm end", "= pivot − ½ tilt"),
                           (684, "the TILT", "= 568 end − 624 end   (no pivot)")):
        out.append(text(cx, 336, title, 13.5, INK, "middle", "bold"))
        out.append(text(cx, 353, sub, 10.5, MUTED, "middle", None, "italic"))

    out.append('<line x1="64" y1="%.1f" x2="800" y2="%.1f" stroke="%s" stroke-width="1.2"/>'
               % (BASE, BASE, INK))
    for value in (0, 5, 10, 15, 20):
        out.append('<line x1="60" y1="%.1f" x2="64" y2="%.1f" stroke="%s" stroke-width="1"/>'
                   % (yOf(value), yOf(value), MUTED))
        out.append(text(56, yOf(value) + 4, "%d" % value, 10, MUTED, "end"))
    out.append('<text transform="rotate(-90 30 500)" x="30" y="500" %s font-size="11" fill="%s" '
               'font-style="italic" text-anchor="middle">band height</text>' % (FONT, MUTED))

    out.append(bar(112, BASE, yOf(21.0), BLUE))
    zig = " ".join("%.1f,%.1f" % (112 - BARW / 2 + i * (BARW / 8), yOf(20.4) + (5 if i % 2 else -5))
                   for i in range(9))
    out.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="#ffffff"/>'
               % (zig, 112 + BARW / 2, yOf(21.6), 112 - BARW / 2, yOf(21.6)))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.1"/>' % (zig, INK))
    out.append(text(112, yOf(21.0) - 20, "A_Soret", 12.5, BLUE, "middle", "bold"))
    out.append(text(112, yOf(21.0) - 6, "= 100", 11, BLUE, "middle", "bold"))
    out.append(text(112, 470, "THE", 11, "#ffffff", "middle", "bold"))
    out.append(text(112, 484, "RULER", 11, "#ffffff", "middle", "bold"))
    out.append(text(112, 506, "each bar", 7.5, "#ffffff", "middle", "bold"))
    out.append(text(112, 516, "at right", 7.5, "#ffffff", "middle", "bold"))
    out.append(text(112, 526, "is a % of", 7.5, "#ffffff", "middle", "bold"))
    out.append(text(112, 536, "this one", 7.5, "#ffffff", "middle", "bold"))
    out.append(text(112, BASE + 20, "blue band", 11, BLUE, "middle", "bold"))

    out.append(bandBar(250, G_PIVOT, G_Q, GREEN, True))
    out.append(bandBar(318, B_PIVOT, B_Q, ACCENT, True))
    out.append(bandBar(450, G_PIVOT, G_QY, GREEN, False))
    out.append(bandBar(518, B_PIVOT, B_QY, ACCENT, False))
    out.append(tiltBar(650, G_Q - G_QY, GREEN, G_Q, G_QY))
    out.append(tiltBar(718, B_Q - B_QY, ACCENT, B_Q, B_QY))
    for cx, label in ((250, "green"), (318, "brown"), (450, "green"),
                      (518, "brown"), (650, "green"), (718, "brown")):
        out.append(text(cx, BASE + 20, label, 11,
                        GREEN_DK if label == "green" else ACCENT, "middle", "bold"))

    out.append(gap(356, G_Q, B_Q, "+4.2"))
    out.append(gap(556, G_QY, B_QY, "−5.2"))
    out.append(gap(756, G_Q - G_QY, B_Q - B_QY, "+9.4"))
    out.append(text(830, 452, "one end", 11, RED, "middle", "bold"))
    out.append(text(830, 467, "collects ONE", 11, RED, "middle", "bold"))
    out.append(text(830, 482, "gap. The", 11, RED, "middle", "bold"))
    out.append(text(830, 497, "difference", 11, RED, "middle", "bold"))
    out.append(text(830, 512, "collects BOTH:", 11, RED, "middle", "bold"))
    out.append(text(830, 532, "4.2 + 5.2", 11, RED, "middle", "bold", None, True))
    out.append(text(830, 546, "= 9.4", 11, RED, "middle", "bold", None, True))

    out.append(text(450, 650, "the SAME grey pivot sits under all four band bars — it is TOTAL "
                              "PIGMENT, not roast, and it wobbles on every refill",
                    11.5, "#3a3f46", "middle", "bold"))
    out.append(text(450, 672, "⇒ a metric built as a DIFFERENCE collects both gaps AND discards "
                              "the pivot, which is ~90 % of Q%'s number and none of its signal",
                    12, RED, "middle", "bold"))

    notes = [
        "Class means over the 88 labelled isopropanol runs of the report archive (55 green / 33 brown; "
        "diffuser-IN runs and the opaque fill excluded). Every bar is",
        "100 × [ A(band) − A(500–560) ] / A(448–460), so it is concentration-free and the Soret is the "
        "ruler — which is why the blue bar reads 100.",
        "⚠ The roast weakens the Soret too, so the ruler is not perfectly fixed; we read its FLANK "
        "(448–460 nm), not its peak (~432 nm).",
        "⚠ The “tilt” drawn here is NOT the shipped dQ100, which divides by sd(448–626) instead: "
        "green 3.8, brown 44.1. The two track each other at r = 0.992, so the",
        "mechanism transfers — the scale does not. Q%, by contrast, is drawn here exactly.",
    ]
    for i, line in enumerate(notes):
        out.append(text(450, 706 + i * 17, line, 10, MUTED, "middle", None, "italic"))

    out.append("</svg>")
    return "".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "tilt_seesaw.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(figureSeesaw())
    print("wrote", path)


if __name__ == "__main__":
    main()
