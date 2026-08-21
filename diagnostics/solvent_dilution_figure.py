"""Why isopropanol's dilution-invariance is STRUCTURAL and white spirit's is not. (Edwin's request 2026-08-21)

A mechanism drawing, not a plot -- nothing here is measured. It exists because the argument in
`DOC_sample_physics.md` section 6 is the one that decides whether the hydrocarbon route is worth
adopting, and the argument is geometric: in an emulsion the pigment's LOCAL concentration is pinned
by the droplet, so dilution cannot reach it; in a true solution the pigment's real concentration IS
the nominal one, so every concentration-dependent equilibrium becomes live.

⛔ The droplet picture is an INFERENCE from solvent chemistry, not a measurement. What the archive
actually shows for it is the flat +0.078 A pedestal on a turbid fill (`SPEC_settled_measurement.md`
section 52.3), the clearing time courses, and the +0.44 / +0.80 first-to-second-pour term (section 36.2).
The experiment that would settle it -- arm B, three dilutions in both solvents -- has not run.

Writes  docs/figures/solvent_dilution_invariance.svg

Run:
    PYTHONPATH=. venv/bin/python diagnostics/solvent_dilution_figure.py
"""
import os

FONT = "Segoe UI,Helvetica Neue,Arial,sans-serif"
INK, MUTED, GREEN, RUST = "#1c211c", "#5c655c", "#3f7d3f", "#b4472f"
OIL_FILL, OIL_EDGE = "#f0d089", "#c9a233"
SOLV_FILL, SOLV_EDGE = "#eef3f7", "#b9c7d2"
PIG = "#2f6b34"
GLASS = "#98a49c"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "figures", "solvent_dilution_invariance.svg")

parts = []
def add(s): parts.append(s)

def text(x, y, s, size=11, fill=INK, anchor="start", weight=None, style=None):
    extra = ""
    if weight: extra += ' font-weight="%s"' % weight
    if style: extra += ' font-style="%s"' % style
    add('<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" fill="%s" '
        'xml:space="preserve" text-anchor="%s"%s>%s</text>'
        % (x, y, FONT, size, fill, anchor, extra, s))

def jar(x, top, width=92, height=132, liquidFill=SOLV_FILL, liquidEdge=SOLV_EDGE):
    """A beaker: glass outline plus a liquid body with a meniscus line."""
    add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="9" fill="#ffffff" '
        'stroke="%s" stroke-width="1.6"/>' % (x, top, width, height, GLASS))
    ly = top + 18
    add('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Q %.1f %.1f %.1f %.1f L %.1f %.1f '
        'Q %.1f %.1f %.1f %.1f Z" fill="%s" stroke="%s" stroke-width="1.1"/>'
        % (x + 4, ly, x + width - 4, ly, x + width - 4, top + height - 13,
           x + width - 4, top + height - 4, x + width - 13, top + height - 4,
           x + 13, top + height - 4, x + 4, top + height - 4, x + 4, top + height - 13,
           liquidFill, liquidEdge))
    return (x + 4, ly, x + width - 4, top + height - 6)

def droplet(cx, cy, r=10.5, dots=((-4,-3),(3,-4),(0,2),(-3,4),(5,3))):
    add('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.2"/>'
        % (cx, cy, r, OIL_FILL, OIL_EDGE))
    for dx, dy in dots:
        add('<circle cx="%.1f" cy="%.1f" r="2.1" fill="%s"/>' % (cx + dx, cy + dy, PIG))

def dot(cx, cy, r=3.0, fill=PIG):
    add('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (cx, cy, r, fill))

def leader(x1, y1, x2, y2):
    add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" '
        'stroke-dasharray="3 3" opacity="0.55"/>' % (x1, y1, x2, y2, MUTED))

def arrow(x1, x2, y, label):
    add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.6"/>'
        % (x1, y, x2 - 7, y, MUTED))
    add('<path d="M %.1f %.1f l -8 -4.5 l 0 9 Z" fill="%s"/>' % (x2, y, MUTED))
    text((x1 + x2) / 2.0, y - 9, label, 9, MUTED, "middle", style="italic")

W, H = 1000, 672
add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H))
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))

text(500, 28, "Why isopropanol&#8217;s dilution-invariance is structural &#8212; and white spirit&#8217;s is not",
     17, INK, "middle", weight="bold")
text(500, 48, "a mechanism drawing, not measured data · the experiment that would settle it (arm B) has not run",
     11, MUTED, "middle", style="italic")

# ---------------------------------------------------------------- panel A, the emulsion
yA = 70
add('<rect x="32" y="%d" width="936" height="262" rx="7" fill="#f5f8f5"/>' % yA)
text(48, yA + 24, "A · ISOPROPANOL — the oil does not dissolve; the pigment rides inside droplets",
     12, GREEN, weight="bold")

jar(60, yA + 42, liquidFill="#fbfdfb", liquidEdge="#d6e0d6")
jar(196, yA + 42, liquidFill="#fbfdfb", liquidEdge="#d6e0d6")
for cx, dy in ((80,80),(118,76),(98,110),(130,116),(80,142),(116,146)):
    droplet(cx, yA + dy)
for cx, dy in ((222,86),(256,116),(228,146)):
    droplet(cx, yA + dy)
text(106, yA + 196, "as prepared", 10, MUTED, "middle")
text(242, yA + 196, "diluted 2×", 10, MUTED, "middle")
arrow(160, 192, yA + 110, "+ solvent")

leader(128, yA + 116, 358, yA + 112)
leader(256, yA + 116, 504, yA + 128)
for cx, tag in ((410, "1×"), (556, "½×")):
    add('<circle cx="%d" cy="%d" r="54" fill="%s" stroke="%s" stroke-width="2"/>'
        % (cx, yA + 110, OIL_FILL, OIL_EDGE))
    for dx, dy in ((-26,-18),(-2,-27),(23,-14),(-30,8),(-6,-2),(19,10),(-19,29),(8,27),(30,-32)):
        dot(cx + dx, yA + 110 + dy, 5.2)
    text(cx, yA + 182, tag, 10, MUTED, "middle", weight="bold")
text(483, yA + 120, "=", 30, GREEN, "middle", weight="bold")
text(483, yA + 202, "inside one droplet — identical at both dilutions", 9.5, MUTED, "middle", style="italic")

vx = 660
text(vx, yA + 62, "The droplet&#8217;s inside is fixed.", 11.5, INK, weight="bold")
for i, line in enumerate([
        "Diluting changes only HOW MANY droplets sit",
        "in the beam — never the concentration inside",
        "one of them. Every concentration-dependent",
        "process (aggregation, dimerisation, self-",
        "quenching) is frozen at one operating point."]):
    text(vx, yA + 84 + i * 16, line, 10.5, INK)
text(vx, yA + 186, "⇒ invariance is STRUCTURAL", 11.5, GREEN, weight="bold")
text(vx, yA + 204, "measured at ±0.35 % across every dilution",  10, MUTED)
text(vx, yA + 219, "simulated, against an 8.7 % run-to-run spread", 10, MUTED)

# ---------------------------------------------------------------- panel B, the true solution
yB = 346
add('<rect x="32" y="%d" width="936" height="262" rx="7" fill="#f9f6f4"/>' % yB)
text(48, yB + 24, "B · WHITE SPIRIT — the oil dissolves; the pigment is loose in the solvent",
     12, RUST, weight="bold")

jar(60, yB + 42)
jar(196, yB + 42)
dense = ((74,78),(92,74),(110,80),(128,76),(140,86),
         (68,96),(104,98),(122,94),(138,104),
         (72,114),(90,110),(108,116),(126,112),(142,120),
         (66,132),(84,130),(102,134),(120,130),(136,140),
         (78,148),(96,150),(114,148),(132,152))
for cx, dy in dense:
    dot(cx, yB + dy)
add('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s"/>' % (86, yB + 92, RUST))
add('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s"/>' % (93, yB + 96, RUST))
sparse = ((216,80),(244,74),(268,88),(232,94),(210,106),(240,112),(272,118),
          (220,134),(250,138),(276,150),(214,150),(244,152))
for cx, dy in sparse:
    dot(cx, yB + dy)
text(106, yB + 196, "as prepared", 10, MUTED, "middle")
text(242, yB + 196, "diluted 2×", 10, MUTED, "middle")
arrow(160, 192, yB + 110, "+ solvent")

leader(142, yB + 120, 358, yB + 114)
leader(272, yB + 118, 504, yB + 126)
add('<circle cx="410" cy="%d" r="54" fill="%s" stroke="%s" stroke-width="2"/>' % (yB + 110, SOLV_FILL, SOLV_EDGE))
for dx, dy in ((-30,-20),(-8,-30),(16,-22),(-32,6),(-10,-4),(14,4),(-22,28),(6,24),(30,20)):
    dot(410 + dx, yB + 110 + dy, 5.2)
add('<circle cx="%.1f" cy="%.1f" r="6.0" fill="%s"/>' % (410 - 10, yB + 106, RUST))
add('<circle cx="%.1f" cy="%.1f" r="6.0" fill="%s"/>' % (410 + 1, yB + 112, RUST))
text(410, yB + 182, "1×", 10, MUTED, "middle", weight="bold")
add('<circle cx="556" cy="%d" r="54" fill="%s" stroke="%s" stroke-width="2"/>' % (yB + 110, SOLV_FILL, SOLV_EDGE))
for dx, dy in ((-28,-22),(14,-18),(-6,6),(26,18),(-24,26)):
    dot(556 + dx, yB + 110 + dy, 5.2)
text(556, yB + 182, "½×", 10, MUTED, "middle", weight="bold")
text(483, yB + 120, "≠", 30, RUST, "middle", weight="bold")
text(483, yB + 202, "the spacing between pigment molecules really changes", 9.5, MUTED, "middle", style="italic")

text(vx, yB + 62, "The pigment&#8217;s real concentration is the nominal one.", 11.5, INK, weight="bold")
for i, line in enumerate([
        "Halve it and the molecules sit ≈ 1.26× further",
        "apart (the cube root of two), so the same",
        "processes are now live variables. In a dry",
        "hydrocarbon the magnesium can take its fifth",
        "ligand from a NEIGHBOUR — a dimer, with shifted,",
        "broadened bands, and a concentration-dependent",
        "equilibrium behind it."]):
    text(vx, yB + 84 + i * 16, line, 10.5, INK)
text(vx, yB + 208, "⇒ invariance becomes CONDITIONAL — untested", 11.5, RUST, weight="bold")
text(vx, yB + 226, "arm B (three dilutions, both solvents) never ran", 10, MUTED)

# ---------------------------------------------------------------- footer
add('<line x1="32" y1="622" x2="968" y2="622" stroke="#d8ded8"/>')
text(32, 641, "The emulsion does NOT read the true spectrum — it reads a wrong one, consistently. "
               "That is exactly what a ratio metric survives:", 10.5, INK)
text(32, 657, "constant-but-wrong beats variable-but-right. Four arguments say the dimer never forms at "
               "micromolar in wet hardware-shop solvent — but they are arguments, not measurements.", 10.5, MUTED)

add('</svg>')

with open(OUT, "w") as handle:
    handle.write("".join(parts))
print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
