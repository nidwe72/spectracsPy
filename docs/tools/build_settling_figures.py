#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generators for the two SETTLING figures in *From Spectrum to Verdict* chapter 6.

    OUTPUT:  docs/figures/settling_sequence.svg  -- what happens when a muddy jar goes in, as a sequence
             docs/figures/settling_cases.svg     -- the four outcomes, on REAL archived trajectories

⭐ The case curves are MEASURED, not schematic. Each panel is one archived run's own `monitorRecord.rows`
— the per-window `Q%` and `A_valley` the instrument actually recorded — read out of the `workflow.json`
embedded in its report PDF. The cache is built by `/tmp` scratch tooling; the four runs and every number
quoted in the captions are listed in CASES below so the figure can be checked against the archive.

⚠ The runs pre-date `clearing-3.0` in three of the four panels, so the ANSWER marked is the one that run
actually recorded under the rule of its day. Where today's rule would answer differently the caption says
so — that is the point of panel D.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_settling_figures.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "docs", "figures")
ROWS = "/tmp/claude-1000/monitor_rows.json"

INK, MUTED, LINE = "#1c211c", "#5c655c", "#b9c1b9"
GREEN, GREEN_DK, ACCENT = "#3f7d3f", "#2f5d2f", "#8d5524"
BLUE, RED, PANEL = "#3a5fa8", "#b03a3a", "#f5f8f5"
AMBER = "#b8860b"
FONT = 'font-family="Segoe UI,Helvetica Neue,Arial,sans-serif"'
MONO = 'font-family="Consolas,DejaVu Sans Mono,monospace"'


def text(x, y, body, size=12, fill=INK, anchor="start", weight=None, style=None, mono=False, rotate=None):
    bits = ['<text x="%.1f" y="%.1f"' % (x, y)]
    if rotate is not None:
        bits.append(' transform="rotate(%.1f %.1f %.1f)"' % (rotate, x, y))
    bits.append(' %s font-size="%.1f" fill="%s" xml:space="preserve"'
                % (MONO if mono else FONT, size, fill))
    if anchor != "start":
        bits.append(' text-anchor="%s"' % anchor)
    if weight:
        bits.append(' font-weight="%s"' % weight)
    if style:
        bits.append(' font-style="%s"' % style)
    escaped = body.replace("&", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;").replace("<", "&lt;").replace(">", "&gt;")
    bits.append(">%s</text>" % escaped)
    return "".join(bits)


# ============================================================== figure 1 — the sequence

LANES = [("the OPERATOR", 92), ("the JAR", 232), ("the INSTRUMENT", 392),
         ("MonitorEngine", 566), ("ClearingEvaluator", 742), ("the REPORT", 884)]


def arrow(x1, x2, y, label, colour=INK, dashed=False, note=None, back=False):
    out = ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.6"%s/>'
           % (x1, y, x2, y, colour, ' stroke-dasharray="5 3"' if dashed else "")]
    d = 7 if x2 > x1 else -7
    out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
               % (x2, y, x2 - d, y - 4, x2 - d, y + 4, colour))
    out.append(text((x1 + x2) / 2, y - 6, label, 10.5, colour, "middle", "bold" if not back else None))
    if note:
        out.append(text((x1 + x2) / 2, y + 13, note, 9, MUTED, "middle", None, "italic"))
    return "".join(out)


def figureSequence():
    W, H = 980, 890
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H)]
    out.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    out.append(text(490, 30, "A muddy jar goes in — what happens next", 18, INK, "middle", "bold"))
    out.append(text(490, 52, "one fill · one wait · one best measurement", 12.5, MUTED, "middle", None, "italic"))

    for name, x in LANES:
        out.append('<rect x="%.1f" y="68" width="%.1f" height="30" rx="5" fill="%s" stroke="%s"/>'
                   % (x - 66, 132, PANEL, LINE))
        out.append(text(x, 88, name, 10.5, INK, "middle", "bold"))
        out.append('<line x1="%.1f" y1="98" x2="%.1f" y2="856" stroke="%s" stroke-width="1" '
                   'stroke-dasharray="3 4"/>' % (x, x, LINE))

    op, jar, inst, eng, ev, rep = (x for _, x in LANES)
    y = 128
    out.append(arrow(op, jar, y, "dilute · fill", GREEN_DK, note="2 capillaries / 10 mL"))
    y += 46
    out.append(arrow(jar, inst, y, "insert the MUDDY jar", GREEN_DK, note="it is a suspension, not a solution"))
    y += 46
    out.append(arrow(op, inst, y, "start", GREEN_DK))
    y += 40
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="26" rx="4" fill="#eef3ee" stroke="%s"/>'
               % (inst - 84, y - 17, 168, GREEN))
    out.append(text(inst, y, "capture the REFERENCE, once", 10.5, GREEN_DK, "middle", "bold"))

    # ---- the loop box ----
    y += 34
    top = y
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="330" rx="7" fill="none" stroke="%s" '
               'stroke-width="1.4"/>' % (inst - 130, top, ev - inst + 300, BLUE))
    out.append('<rect x="%.1f" y="%.1f" width="150" height="20" fill="%s"/>' % (inst - 130, top, BLUE))
    out.append(text(inst - 124, top + 14, "loop — every 60 frames", 10.5, "#ffffff", "start", "bold"))
    y = top + 44
    out.append(arrow(inst, eng, y, "offer(spectrum, t)", BLUE))
    y += 40
    out.append(arrow(eng, ev, y, "decide(rows)", BLUE))
    y += 34
    out.append('<rect x="%.1f" y="%.1f" width="250" height="46" rx="4" fill="#eef2f8" stroke="%s"/>'
               % (ev - 44, y - 16, BLUE))
    out.append(text(ev - 34, y, "A_Soret · A_valley · A_Q  →  Q%", 10.5, BLUE, "start", "bold", None, True))
    out.append(text(ev - 34, y + 16, "one row appended to the trajectory", 9, MUTED, "start", None, "italic"))
    y += 62

    guards = [("A_Soret &lt; 0.15", "MEASUREMENT_BROKEN — abort; there is nothing in the cuvette", RED),
              ("too dark to read", "not a look, and NOT broken — the fill is still clearing", AMBER),
              ("TEST C — a monotone RISE", "DEGRADING_FILL — it is ripening, not settling. End the run", AMBER),
              ("TEST A — flat, twice", "the GATE fires — |dA_valley/dt| &lt; 0.005/min ⇒ stop looking", GREEN_DK)]
    for cond, meaning, colour in guards:
        out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#ffffff" stroke="%s"/>'
                   % (ev - 118, y, ev - 100, y - 11, ev - 82, y, ev - 100, y + 11, colour))
        out.append(text(ev - 76, y + 4, cond, 10, colour, "start", "bold", None, True))
        out.append(text(ev - 76, y + 18, meaning, 9, MUTED, "start", None, "italic"))
        y += 40
    out.append(text(inst - 120, top + 318, "…otherwise: carry on, capture the next window",
                    9.5, MUTED, "start", None, "italic"))

    # ---- the read ----
    y = top + 358
    out.append(arrow(eng, ev, y, "finalize(rows)   ⭐ the END-OF-RUN read", GREEN_DK,
                     note="a minimum the curve later fell below was never a minimum"))
    y += 44
    out.append('<rect x="%.1f" y="%.1f" width="286" height="60" rx="5" fill="#eef3ee" stroke="%s"/>'
               % (ev - 62, y - 18, GREEN))
    out.append(text(ev - 52, y, "the curve turned  →  VERTEX at the minimum", 10, GREEN_DK, "start", "bold", None, True))
    out.append(text(ev - 52, y + 15, "it never turned  →  the FIRST look", 10, GREEN_DK, "start", "bold", None, True))
    out.append(text(ev - 52, y + 32, "drawdown ≤ 10 × tailSd, or the candidate is refused",
                    9, MUTED, "start", None, "italic"))
    y += 74
    out.append(arrow(ev, eng, y, "answer + readAs + branch", GREEN_DK, back=True))
    y += 34
    out.append(arrow(eng, rep, y, "MonitorRecord", GREEN_DK, note="outcome · every row · the version of the rule"))
    y += 40
    out.append('<rect x="%.1f" y="%.1f" width="220" height="26" rx="4" fill="#fdf3f3" stroke="%s"/>'
               % (rep - 200, y - 17, RED))
    out.append(text(rep - 190, y, "no value?  the record says WHY", 10, RED, "start", "bold"))
    out.append("</svg>")
    return "".join(out)


# ============================================================== figure 2 — the four cases

CASES = [
    ("20280819BillaClever__005", "A · THE MUDDY FILL — the case this is all for",
     "it clears 10-fold in the beam; Q% falls with it, turns, and the VERTEX is the answer", GREEN, True),
    ("20260821LugitschA__001", "B · IT ARRIVED CLEAR",
     "A_valley never falls, Q% never turns — the FIRST look is the answer and the run is short", GREEN, False),
    ("20260821LugitschA__002", "C · THE FILL GOES BACKWARDS",
     "A_valley RISES — ripening, not settling. TEST C ends the run: a value, but not a settled one", AMBER, False),
    ("20280819BillaClever__003", "D · ⛔ THE OPAQUE FILL — and why a ceiling is owed",
     "read through mud at A_valley 2.67 and reported 8.45 — a confident GREEN on a brown oil", RED, False),
]

PW, PH = 398, 190


def panel(x0, y0, key, title, sub, colour, primary, data):
    rows = [r for r in data[key]["rows"] if r.get("isDecisionRow") and r.get("qPercent") is not None]
    t = [r["t"] / 60.0 for r in rows]
    q = [r["qPercent"] for r in rows]
    v = [r["valley"] for r in rows]
    answer = data[key].get("answer") or {}
    out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="7" fill="%s"/>'
           % (x0 - 12, y0 - 30, PW + 24, PH + 74, PANEL)]
    out.append(text(x0 - 4, y0 - 12, title, 12, colour, "start", "bold"))
    lo, hi = min(q), max(q)
    pad = max(0.35, (hi - lo) * 0.18)
    lo, hi = lo - pad, hi + pad
    vlo, vhi = min(v), max(v)
    vpad = max(0.01, (vhi - vlo) * 0.18)
    vlo, vhi = vlo - vpad, vhi + vpad
    X = lambda tt: x0 + (tt - t[0]) / max(1e-9, t[-1] - t[0]) * PW
    Y = lambda qq: y0 + PH - (qq - lo) / (hi - lo) * PH
    YV = lambda vv: y0 + PH - (vv - vlo) / (vhi - vlo) * PH

    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (x0, y0 + PH, x0 + PW, y0 + PH, INK))
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (x0, y0, x0, y0 + PH, INK))
    for frac in (0.0, 0.5, 1.0):
        out.append(text(x0 + frac * PW, y0 + PH + 14, "%.0f" % (t[0] + frac * (t[-1] - t[0])),
                        9, MUTED, "middle"))
    out.append(text(x0 + PW / 2, y0 + PH + 27, "minutes", 9, MUTED, "middle", None, "italic"))
    out.append(text(x0 - 6, y0 + 8, "%.1f" % hi, 9, GREEN_DK, "end"))
    out.append(text(x0 - 6, y0 + PH, "%.1f" % lo, 9, GREEN_DK, "end"))
    out.append(text(x0 - 22, y0 + PH / 2, "Q%", 10, GREEN_DK, "middle", "bold", None, False, -90))
    out.append(text(x0 + PW + 6, y0 + 8, "%.2f" % vhi, 9, BLUE, "start"))
    out.append(text(x0 + PW + 6, y0 + PH, "%.2f" % vlo, 9, BLUE, "start"))
    out.append(text(x0 + PW + 26, y0 + PH / 2, "A_valley", 10, BLUE, "middle", "bold", None, False, -90))

    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.6" stroke-dasharray="5 3"/>'
               % (" ".join("%.1f,%.1f" % (X(a), YV(b)) for a, b in zip(t, v)), BLUE))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>'
               % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in zip(t, q)), GREEN_DK))
    for a, b in zip(t, q):
        out.append('<circle cx="%.1f" cy="%.1f" r="2.1" fill="%s"/>' % (X(a), Y(b), GREEN_DK))

    at = answer.get("t")
    if at is not None:
        ax, ay = X(at / 60.0), Y(answer.get("value"))
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2" '
                   'stroke-dasharray="3 3"/>' % (ax, y0, ax, y0 + PH, colour))
        out.append('<circle cx="%.1f" cy="%.1f" r="6" fill="none" stroke="%s" stroke-width="2.4"/>'
                   % (ax, ay, colour))
        lab = "%s  %.2f" % (answer.get("readAs", ""), answer.get("value"))
        anchor = "end" if ax > x0 + PW * 0.55 else "start"
        out.append(text(ax + (-10 if anchor == "end" else 10), ay - 14, lab, 9.5, colour, anchor, "bold", None, True))
    out.append(text(x0 - 4, y0 + PH + 44, sub, 9.5, MUTED, "start", None, "italic"))
    out.append(text(x0 - 4, y0 + PH + 58, "%s · %s · %d windows · %s"
                    % (key.replace("__", "/"), data[key].get("outcome"), len(rows),
                       data[key].get("evaluatorVersion")), 8.5, MUTED, "start", None, None, True))
    return "".join(out)


def figureCases():
    data = json.load(open(ROWS))
    W, H = 1000, 672
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H)]
    out.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    out.append(text(500, 28, "Four fills, four outcomes — every curve measured, none drawn",
                    17, INK, "middle", "bold"))
    out.append(text(500, 48, "solid = Q% (left axis) · dashed = A_valley, the turbidity (right axis) · "
                             "the ring is the reported answer", 11, MUTED, "middle", None, "italic"))
    spots = ((44, 100), (540, 100), (44, 392), (540, 392))
    for (x, y), (key, title, sub, colour, primary) in zip(spots, CASES):
        out.append(panel(x, y, key, title, sub, colour, primary, data))
    out.append("</svg>")
    return "".join(out)




# ============================================================== figure 3 — the drawdown rule

DRAWDOWN_RUN = "20280819BillaClever__006"
TAIL_ROWS, MULTIPLE = 8, 10.0


def tailSd(q):
    """Residual scatter of the last TAIL_ROWS about a straight line — the run's OWN noise floor.
    ⚠ n − 2 degrees of freedom, because a line costs two."""
    import numpy
    tail = numpy.array(q[-TAIL_ROWS:], dtype=float)
    x = numpy.arange(len(tail))
    resid = tail - numpy.polyval(numpy.polyfit(x, tail, 1), x)
    return float(math.sqrt((resid ** 2).sum() / (len(tail) - 2)))


def drawdownOf(q, i):
    """The largest FALL-BACK the curve makes anywhere after row i."""
    after = q[i + 1:]
    if not after:
        return 0.0, []
    runmax, peak = [], after[0]
    for v in after:
        peak = max(peak, v)
        runmax.append(peak)
    return max(p - v for p, v in zip(runmax, after)), runmax


def axes(x0, y0, w, h, xs, ys, colour, xlabel, ylabel, pad=0.10):
    lo, hi = min(ys), max(ys)
    span = max(1e-9, hi - lo)
    lo, hi = lo - span * pad, hi + span * pad
    X = lambda v: x0 + (v - xs[0]) / max(1e-9, xs[-1] - xs[0]) * w
    Y = lambda v: y0 + h - (v - lo) / (hi - lo) * h
    out = ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (x0, y0 + h, x0 + w, y0 + h, INK),
           '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (x0, y0, x0, y0 + h, INK)]
    for frac in (0.0, 0.5, 1.0):
        out.append(text(x0 + frac * w, y0 + h + 14, "%.0f" % (xs[0] + frac * (xs[-1] - xs[0])), 9, MUTED, "middle"))
    out.append(text(x0 + w / 2, y0 + h + 27, xlabel, 9, MUTED, "middle", None, "italic"))
    for v in (lo + span * pad, hi - span * pad):
        out.append(text(x0 - 6, Y(v) + 4, "%.2f" % v, 9, MUTED, "end"))
    out.append(text(x0 - 34, y0 + h / 2, ylabel, 10, INK, "middle", "bold", None, False, -90))
    return "".join(out), X, Y


def figureDrawdown():
    data = json.load(open(ROWS))
    rows = [r for r in data[DRAWDOWN_RUN]["rows"] if r.get("isDecisionRow") and r.get("qPercent") is not None]
    t = [r["t"] / 60.0 for r in rows]
    q = [r["qPercent"] for r in rows]
    sd = tailSd(q)
    shipped = data[DRAWDOWN_RUN]["answer"]["value"]          # what clearing-2.0 reported
    iBad = min(range(len(q)), key=lambda i: abs(q[i] - 19.004))
    iGood = min(range(len(q)), key=lambda i: abs(q[i] - 19.782))
    ddBad, _ = drawdownOf(q, iBad)
    ddGood, _ = drawdownOf(q, iGood)

    W, H = 980, 660
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H)]
    out.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    out.append(text(490, 30, "DRAWDOWN — the largest fall-back the curve makes AFTER a candidate",
                    17, INK, "middle", "bold"))
    out.append(text(490, 51, "judged against the run's own noise:  tailSd = %.4f Q%%  "
                             "(scatter of the last %d rows about a line)  ·  admissible if drawdown ≤ %.0f × tailSd"
                    % (sd, TAIL_ROWS, MULTIPLE), 11, MUTED, "middle", None, "italic"))

    # ---- top: the whole run ----
    x0, y0, w, h = 74, 92, 856, 188
    ax, X, Y = axes(x0, y0, w, h, t, q, INK, "minutes since insertion", "Q%")
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fdf1f1"/>'
               % (X(t[iBad]), y0, X(t[iGood]) - X(t[iBad]), h))
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#eef5ee"/>'
               % (X(t[iGood]), y0, x0 + w - X(t[iGood]), h))
    out.append(ax)
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>'
               % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in zip(t, q)), ACCENT))
    for a, b in zip(t, q):
        out.append('<circle cx="%.1f" cy="%.1f" r="2" fill="%s"/>' % (X(a), Y(b), ACCENT))
    bx, by = X(t[iBad]), Y(q[iBad])
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
               % (bx - 6, by - 6, bx + 6, by + 6, RED))
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
               % (bx - 6, by + 6, bx + 6, by - 6, RED))
    out.append(text(bx - 14, by - 16, "what clearing-2.0 read", 10, RED, "end", "bold"))
    out.append(text(bx - 14, by - 3, "%.3f — a noise dip" % shipped, 10, RED, "end", "bold"))
    gx, gy = X(t[iGood]), Y(q[iGood])
    out.append('<polygon points="%s" fill="%s"/>' % (
        " ".join("%.1f,%.1f" % (gx + 8 * math.cos(math.radians(90 + k * 72)),
                                gy - 8 * math.sin(math.radians(90 + k * 72))) for k in (0, 2, 4, 1, 3)), GREEN_DK))
    out.append(text(gx + 14, gy + 14, "what clearing-3.0 reads", 10, GREEN_DK, "start", "bold"))
    out.append(text(gx + 14, gy + 27, "19.782 — the real minimum", 10, GREEN_DK, "start", "bold"))
    out.append(text((bx + gx) / 2, y0 + 16, "the curve climbs … then FALLS BACK", 10.5, RED, "middle", "bold"))
    out.append(text((bx + gx) / 2, y0 + 30, "⇒ this was not the end of anything", 9.5, RED, "middle", None, "italic"))
    out.append(text((gx + x0 + w) / 2, y0 + 16, "from here the curve ONLY climbs", 10.5, GREEN_DK, "middle", "bold"))
    out.append(text((gx + x0 + w) / 2, y0 + 30, "⇒ browning, and browning goes one way",
                    9.5, GREEN_DK, "middle", None, "italic"))

    # ---- bottom: what happens after each candidate ----
    for k, (i, dd, colour, title, verdict) in enumerate((
            (iBad, ddBad, RED, "after the noise dip (%.3f)" % shipped, "REJECT"),
            (iGood, ddGood, GREEN_DK, "after 19.782", "ACCEPT"))):
        px, py, pw, ph = 74 + k * 486, 366, 370, 176
        tt, qq = t[i:], q[i:]
        a2, X2, Y2 = axes(px, py, pw, ph, tt, qq, colour, "minutes since insertion", "Q%")
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="%s"/>'
                   % (px - 44, py - 34, pw + 92, ph + 84, PANEL))
        out.append(text(px + pw / 2, py - 16, title, 12, colour, "middle", "bold"))
        out.append(a2)
        _, runmax = drawdownOf(q, i)
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.2" stroke-dasharray="4 3"/>'
                   % (" ".join("%.1f,%.1f" % (X2(a), Y2(b)) for a, b in zip(tt[1:], runmax)), MUTED))
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8"/>'
                   % (" ".join("%.1f,%.1f" % (X2(a), Y2(b)) for a, b in zip(tt, qq)), ACCENT))
        for a, b in zip(tt, qq):
            out.append('<circle cx="%.1f" cy="%.1f" r="1.9" fill="%s"/>' % (X2(a), Y2(b), ACCENT))
        worst = max(range(len(runmax)), key=lambda n: runmax[n] - qq[n + 1])
        wx = X2(tt[worst + 1])
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.2"/>'
                   % (wx, Y2(runmax[worst]), wx, Y2(qq[worst + 1]), colour))
        for yy, d in ((Y2(runmax[worst]), 1), (Y2(qq[worst + 1]), -1)):
            out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
                       % (wx, yy, wx - 4, yy + d * 8, wx + 4, yy + d * 8, colour))
        lx = min(max(wx, px + 58), px + pw - 58)
        base = Y2(qq[worst + 1]) + 20
        out.append(text(lx, base, "drawdown %.4f" % dd, 10, colour, "middle", "bold"))
        out.append(text(lx, base + 14, "= %.1f × tailSd" % (dd / sd), 10, colour, "middle", "bold"))
        out.append(text(px + pw / 2, py + ph + 44, "%.1f ×  %s  10  →  %s"
                        % (dd / sd, ">" if dd / sd > MULTIPLE else "≤", verdict),
                        12.5, colour, "middle", "bold", None, True))
        out.append(text(px + pw / 2, py + ph + 58, "dashed = the running high after the candidate",
                        9, MUTED, "middle", None, "italic"))
    out.append("</svg>")
    return "".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("settling_sequence.svg", figureSequence()),
                      ("settling_cases.svg", figureCases()),
                      ("settling_drawdown.svg", figureDrawdown())):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as h:
            h.write(svg)
        print("wrote", os.path.join(OUT, name))



if __name__ == "__main__":
    main()
