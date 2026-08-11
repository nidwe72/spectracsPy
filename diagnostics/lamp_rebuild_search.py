#!/usr/bin/env python3
"""
Lamp rebuild — choose the seven emitters on MEASURED noise.

    SOURCE OF TRUTH FOR THE PROSE:  docs/DOC_lamp_rebuild.md
    OUTPUT:  spectracs-references/tmp/lamprebuild/*.png  +  ranking.json

This is the successor to `led_lamp_410_680.py`, and it differs from it in exactly one way that matters:
that study scored the lamp's EMITTED spectrum through a MODELLED camera response, on a median across the
415-450 nm bracket. This one scores

    sigma_A(lambda) -- the noise the metric would actually carry --

computed from a MEASURED absorbance curve and a MEASURED per-curve noise level, with the lamp entering
only through its emitted SPD normalised to a 240 DN peak. Three reasons the objective had to change:

  1. `20260811A/001,002` (2026-08-11) are the first runs in the archive containing 400-440 nm. They
     resolve the Soret as a DOUBLET at 421.4 / 436.5 nm with a dip at 432 -- 20 of 20 independent slit
     rows. The old study's model put a single composite maximum near 439 nm and had no doublet at all.
  2. Those runs read 128 DN at 410 nm. `led_lamp_410_680.instrumentResponse` -- which says of itself
     "below 440 nm nothing is measured at all ... a stated assumption, not a result" -- predicts 13 DN
     (optimistic) / 3 DN (pessimistic). The blue half of that response model is falsified, so no forecast
     here uses it.
  3. The quantity that decides whether the doublet is USABLE is not a photon count at 432 nm. It is the
     noise on the CONTRAST between the dip and the second peak, which is only 0.025-0.030 in A. That is
     scored here directly (`doublet` below) and was scored nowhere before.

THE ARITHMETIC THAT IS EASY TO GET WRONG
----------------------------------------
Absorbance is defined on the LINEAR values; the noise and the plots live in DISPLAY DN; the two are
related by the pow2.2 capture decode. Therefore

    S_dn = R_dn * 10 ** (-A / 2.2)                       NOT  R_dn * 10 ** (-A)
    sigma_A = 0.434 * 2.2 * sqrt((s/S_dn)**2 + (s/R_dn)**2)

Verified against `20260811A/002` at 421 nm: R = 131 DN, A = 1.210 -> predicts S = 37.0 DN, measured 37.0.
`--verify` re-runs that check.

HOW TO RUN
----------
    source venv/bin/activate
    PYTHONPATH=diagnostics python diagnostics/lamp_rebuild_search.py --verify --figures
"""
import argparse
import itertools
import json
import os

import numpy as np
from scipy.signal import savgol_filter

import led_lamp_410_680 as lamp

REFS = "/home/nidwe72/development/spectracs/spectracs-references/"
TMP = REFS + "tmp/"
OUT = TMP + "lamprebuild/"

GRID = lamp.GRID                      # 410.0 .. 680.0, 0.5 nm
DECODE = 2.2                          # captureDecode = "pow2.2"
CEILING = 240.0                       # display DN the lamp peak is exposed to, of 255
SIGMA_DN = 0.5                        # measured per-curve noise, BOTH captures, EVERY band (§4.2)
BIN_NM = 0.1454                       # stored spectrum sampling, from the 1634-bin ROI

# --------------------------------------------------------------------------- measured inputs


def absorbanceFromPdf(path):
    """The ABSORPTION spectrum out of a bench report's embedded workflow.json."""
    import pypdf
    document = json.loads(pypdf.PdfReader(TMP + path).attachments["workflow.json"][0])
    for phase in document["phases"]:
        for step in phase.get("steps", []):
            if "ABSORPTION" in (step.get("spectra") or {}):
                values = step["spectra"]["ABSORPTION"]
                nanometers = np.array(sorted(float(k) for k in values))
                return nanometers, np.array([values[k] for k in sorted(values, key=float)])
    raise KeyError("no ABSORPTION spectrum in " + path)


def capturesFromPdf(path):
    """Reference and sample, as DISPLAY DN -- the axis the operator and the noise both live on."""
    import pypdf
    document = json.loads(pypdf.PdfReader(TMP + path).attachments["workflow.json"][0])
    out = {}
    for phase in document["phases"]:
        for step in phase.get("steps", []):
            for role in ("REFERENCE", "SAMPLE"):
                if role in (step.get("spectra") or {}) and role not in out:
                    values = step["spectra"][role]
                    nanometers = np.array(sorted(float(k) for k in values))
                    linear = np.array([values[k] for k in sorted(values, key=float)])
                    out[role] = (nanometers, 255.0 * np.clip(linear / 255.0, 0, 1) ** (1 / DECODE))
    return out


def compositeAbsorbance():
    """The anticipated A(lambda) over 404-680 nm, at the capillary dose. Three segments:

      404-448   MEASURED on the new lamp (`20260811A`), level-scaled onto the capillary dose by the
                448-460 anchor. The only data that exists below 440 nm.
      448-630   MEASURED, capillary corpus `20260807A` (Spar Steirisches g.g.A.), mean of 3 reseats.
      630-680   ANTICIPATED -- Fruhwirth Fig. 3A's SHAPE, anchored on the capillary curve's own 629.8
                value. Nobody has ever captured this stretch; it is drawn so the quiet window can be
                scored at all, and it is the weakest input in this file.
    """
    import csv
    band = lambda x, v, a, b: v[(x >= a) & (x < b)].mean()
    capNm, capA = None, []
    for run in ("001", "002", "003"):
        x, v = absorbanceFromPdf("20260807A/%s.pdf" % run)
        capNm = x
        capA.append(v)
    capA = np.mean(capA, axis=0)
    level = band(capNm, capA, 448, 460)

    blueGrid = np.arange(404, 462, 0.2)
    blue = []
    for run in ("001", "002"):
        x, v = absorbanceFromPdf("20260811A/%s.pdf" % run)
        v = savgol_filter(v, 35, 3)
        bad = ((x < 406) | (x > 632) | ((x > 468) & (x < 484))
               | ((x > 579) & (x < 587)) | ((x > 611) & (x < 618)))
        v = savgol_filter(np.interp(x, x[~bad], v[~bad]), 35, 3)
        blue.append(np.interp(blueGrid, x, v / band(x, v, 448, 460) * level))
    blue = np.mean(blue, axis=0)

    rows = list(csv.reader(open(REFS + "comparisons/fig3A_vs_spectracs/data/"
                                "fig3a_literature_digitized.csv")))
    literature = np.array([[float(c) for c in r] for r in rows[1:]])
    order = np.argsort(literature[:, 0])
    litNm, litA = literature[order, 0], literature[order, 1]
    floor = np.median(litA[(litNm >= 655) & (litNm <= 695)])
    shape = lambda w: ((np.interp(w, litNm, litA) - floor)
                       / (np.interp(629.8, litNm, litA) - floor))

    grid = np.arange(404, 681, 0.2)
    blend = np.clip((grid - 448.0) / 8.0, 0, 1)
    inBlue = np.interp(grid, blueGrid, blue, left=np.nan, right=np.nan)
    inCap = np.interp(grid, capNm, capA, left=np.nan, right=np.nan)
    inRed = capA[-1] * shape(grid)
    out = np.where(np.isnan(inCap), inBlue,
                   np.where(np.isnan(inBlue), inCap, (1 - blend) * inBlue + blend * inCap))
    out = np.where(grid > 629.8, inRed, out)
    return grid, savgol_filter(out, 21, 3)


CAPILLARY_OILS = [("20260807D", "Steirerkraft g.g.A.  M448 9.96", "#0b7a3f"),
                  ("20260807A", "Spar Steirisches g.g.A.  8.76", "#5aa02c"),
                  ("20260807C", "Spar Premium g.g.A.  7.69", "#c9a227"),
                  ("20260807B", "Spar S-Budget — brown  6.51", "#8a4a1e")]


def oilCurves():
    """The four capillary oils, each extended into the blue and out to 680 nm.

    ⚠ The blue segment is ONE oil's shape (the `20260811A` fills, normalised by their own 448-460 mean)
    scaled to each oil's own 448-460 level. Nobody has measured a second oil below 440 nm, so the four
    curves differ there only in LEVEL. Any green-vs-brown difference visible below 448 nm in the figures
    is dose, not chemistry -- that is exactly the open question of DOC_lamp_rebuild.md §9.1.
    """
    import csv
    band = lambda x, v, a, b: v[(x >= a) & (x < b)].mean()
    template, templateGrid = [], np.arange(404, 462, 0.2)
    for run in ("001", "002"):
        x, v = absorbanceFromPdf("20260811A/%s.pdf" % run)
        bad = ((x < 406) | (x > 632) | ((x > 468) & (x < 484))
               | ((x > 579) & (x < 587)) | ((x > 611) & (x < 618)))
        v = savgol_filter(np.interp(x, x[~bad], savgol_filter(v, 35, 3)[~bad]), 35, 3)
        template.append(np.interp(templateGrid, x, v / band(x, v, 448, 460)))
    template = np.mean(template, axis=0)

    rows = list(csv.reader(open(REFS + "comparisons/fig3A_vs_spectracs/data/"
                                "fig3a_literature_digitized.csv")))
    literature = np.array([[float(c) for c in r] for r in rows[1:]])
    order = np.argsort(literature[:, 0])
    litNm, litA = literature[order, 0], literature[order, 1]
    floor = np.median(litA[(litNm >= 655) & (litNm <= 695)])
    shape = lambda w: ((np.interp(w, litNm, litA) - floor)
                       / (np.interp(629.8, litNm, litA) - floor))

    grid = np.arange(404, 681, 0.2)
    blend = np.clip((grid - 448.0) / 8.0, 0, 1)
    out = []
    for run, name, colour in CAPILLARY_OILS:
        stack = [absorbanceFromPdf("%s/%s.pdf" % (run, n)) for n in ("001", "002", "003")]
        x = stack[0][0]
        v = np.mean([s[1] for s in stack], axis=0)
        blue = np.interp(grid, templateGrid, template * band(x, v, 448, 460),
                         left=np.nan, right=np.nan)
        middle = np.interp(grid, x, v, left=np.nan, right=np.nan)
        red = v[-1] * shape(grid)
        curve = np.where(np.isnan(middle), blue,
                         np.where(np.isnan(blue), middle, (1 - blend) * blue + blend * middle))
        out.append((name, colour, grid, savgol_filter(np.where(grid > 629.8, red, curve), 21, 3)))
    return out


# --------------------------------------------------------------------------- the objective

# Every scored quantity is a NOISE, in absorbance units. Lower is better.
#   ('band', lo, hi)  -> sigma on the mean absorbance over [lo, hi)
#   ('point', nm)     -> sigma at one wavelength
#   ('contrast', a, b)-> sigma on A(b) - A(a); the doublet's own signature
TARGETS = [
    ("soret-peak", ("point", 421.4), "Soret peak 1 -- the composite blue maximum"),
    ("doublet", ("contrast", 432.0, 436.5), "dip -> peak 2 contrast; the doublet signature (0.025-0.030)"),
    ("soret-band", ("band", 448.0, 460.0), "the shipped Soret window"),
    ("crossover", ("point", 476.0), "the Bayer B->G crossover, the largest artefact in the archive"),
    ("clarity", ("band", 510.0, 540.0), "clarity floor / near baseline anchor"),
    ("q-band", ("band", 560.0, 580.0), "the Q band -- the metric denominator"),
    ("far-anchor", ("band", 620.0, 630.0), "far baseline anchor + the 627 nm fourth peak"),
    ("quiet", ("band", 660.0, 680.0), "the pigment-free window; anchor the metric has never had"),
]

WEIGHTINGS = {
    "as written": {},
    "doublet first": {"doublet": 3.0, "soret-peak": 2.0},
    "shipped metric first": {"soret-band": 3.0, "q-band": 3.0, "clarity": 2.0, "far-anchor": 2.0},
    "quiet window first": {"quiet": 3.0},
    "control -- drop the crossover": {"crossover": 0.0},
    "control -- drop the quiet window": {"quiet": 0.0},
}


def sigmaAt(referenceDn, absorbance, bins=1.0):
    """sigma_A from a reference level in DISPLAY DN and the sample's absorbance. See the header."""
    sampleDn = np.maximum(referenceDn * 10.0 ** (-absorbance / DECODE), 1e-3)
    referenceDn = np.maximum(referenceDn, 1e-3)
    return (0.434 * DECODE * np.sqrt((SIGMA_DN / sampleDn) ** 2 + (SIGMA_DN / referenceDn) ** 2)
            / np.sqrt(bins))


def evaluate(spectrum, grid, absorbance):
    """Every TARGET's sigma for one lamp. `spectrum` is emitted SPD on GRID, any scale."""
    delivered = CEILING * spectrum / max(spectrum.max(), 1e-12)
    at = lambda w: (delivered[np.argmin(np.abs(GRID - w))],
                    float(np.interp(w, grid, absorbance)))
    out = {}
    for name, spec, _ in TARGETS:
        if spec[0] == "point":
            r, a = at(spec[1])
            out[name] = float(sigmaAt(r, a))
        elif spec[0] == "band":
            lo, hi = spec[1], spec[2]
            mask = (GRID >= lo) & (GRID < hi)
            r = float(np.median(delivered[mask]))
            a = float(np.mean(absorbance[(grid >= lo) & (grid < hi)]))
            out[name] = float(sigmaAt(r, a, bins=max((hi - lo) / BIN_NM, 1.0)))
        else:                                            # contrast
            r1, a1 = at(spec[1]); r2, a2 = at(spec[2])
            out[name] = float(np.hypot(sigmaAt(r1, a1), sigmaAt(r2, a2)))
    return out


def score(sigmas, weights):
    """Minimax: the worst weighted band decides. A metric is as good as its weakest input."""
    return max(sigmas[n] * weights.get(n, 1.0) for n, _, _ in TARGETS
               if weights.get(n, 1.0) > 0)


def doseSweep(spectrum, grid, absorbance):
    """Which dilution? -- and it must be scored on SIGNAL-to-noise, not on sigma alone.

    ⚠ Diluting lifts the sample level and shrinks the band depth at the SAME rate, so sigma_A on its own
    always says "more dilute" and never turns around. An earlier draft of the study picked x2.75 on a
    clear-the-DN-floor argument and was wrong for exactly that reason. Scoring depth/sigma gives a real
    optimum, and it is broad: f = 1.5-2.0.

    `f` = how many times more dilute than the 20260807 capillary session (2 capillaries / 12 mL).
    """
    at = lambda w: float(np.interp(w, grid, absorbance))
    inBand = lambda lo, hi: float(np.mean(absorbance[(grid >= lo) & (grid < hi)]))
    signals = {"doublet": at(436.5) - at(432.0),
               "soret-band": inBand(448, 460) - inBand(510, 540),
               "q-band": inBand(560, 580) - inBand(510, 540)}
    rows = []
    for f in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0):
        sigmas = evaluate(spectrum, grid, absorbance / f)
        rows.append({"f": f, "mlPer2Capillaries": 12.0 * f,
                     **{"snr_" + k: (v / f) / sigmas[k] for k, v in signals.items()}})
    return signals, rows


# --------------------------------------------------------------------------- the candidate set

WHITES = ["2900k-3200k.jpg", "4000k-4500k.jpg", "5500k-6000k.jpg",
          "6500k-7000k.jpg", "10000k-20000k.jpg"]
COLOURS = ["410nm-420nm.jpg", "430nm-435nm.jpg", "440nm-450nm.jpg", "455nm-460nm.jpg",
           "480nm-485nm.jpg", "515nm-525nm.jpg", "590nm-600nm.jpg", "600nm-610nm.jpg",
           "630nm-640nm.jpg", "660nm.jpg"]
SLOTS = 7
MAX_COLOUR_KINDS = 4


def label(mix):
    order = {p: i for i, p in enumerate(WHITES + COLOURS)}
    return " + ".join("%d x %s" % (int(n), p.replace(".jpg", ""))
                      for p, n in sorted(mix.items(), key=lambda kv: order[kv[0]]))


def candidates():
    for white in WHITES:
        for whiteCount in range(1, SLOTS):
            colourSlots = SLOTS - whiteCount
            for kinds in itertools.chain.from_iterable(
                    itertools.combinations(COLOURS, k)
                    for k in range(1, min(MAX_COLOUR_KINDS, colourSlots) + 1)):
                for counts in itertools.product(range(1, colourSlots + 1), repeat=len(kinds)):
                    if sum(counts) != colourSlots:
                        continue
                    mix = {white: float(whiteCount)}
                    mix.update({k: float(n) for k, n in zip(kinds, counts)})
                    yield mix


RECOMMENDED = {"4000k-4500k.jpg": 2., "410nm-420nm.jpg": 2., "440nm-450nm.jpg": 1.,
               "480nm-485nm.jpg": 1., "630nm-640nm.jpg": 1.}
"""The board this study recommends -- rank 6, not rank 1. They differ by 2.6 % on the binding constraint
(the doublet) and rank 6 is ahead on every other axis, including 2.3x at 476 nm where the instrument has a
known defect. See DOC_lamp_rebuild.md §5."""

REFERENCE_BUILDS = {
    "R2 as published": {"4000k-4500k.jpg": 3., "410nm-420nm.jpg": 2.,
                        "430nm-435nm.jpg": 1., "660nm.jpg": 1.},
    "R2 with 630-640 instead of 660": {"4000k-4500k.jpg": 3., "410nm-420nm.jpg": 2.,
                                       "430nm-435nm.jpg": 1., "630nm-640nm.jpg": 1.},
    "the incumbent of the old study": {"6500k-7000k.jpg": 3., "430nm-435nm.jpg": 2.,
                                       "515nm-525nm.jpg": 1., "660nm.jpg": 1.},
}


# --------------------------------------------------------------------------- figures

def writeFigures(curves, grid, absorbance, ranked, best, measured, legacyForecast=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True)
    ink, grey, line = "#111111", "#6b6b6b", "#d8d8d4"

    def frame(ax, title, xlabel="wavelength (nm)", ylabel=None):
        ax.set_title(title, fontsize=10.5, color=ink)
        ax.set_xlabel(xlabel, fontsize=9, color=grey)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=9, color=grey)
        ax.grid(alpha=.16, color=line)
        ax.tick_params(labelsize=8, colors=grey)

    # 1 -- the anticipated absorbance, with the three provenances shaded
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    ax.axvspan(404, 448, color="#7a5cd6", alpha=.07)
    ax.axvspan(448, 629.8, color="#0b7a5f", alpha=.07)
    ax.axvspan(629.8, 681, color="#888888", alpha=.10)
    ax.axvspan(660, 680, color="#c9a227", alpha=.16)
    ax.plot(grid, absorbance, color="#0b6e4f", lw=2.2)
    ax.annotate("421.4 nm", xy=(421.4, absorbance.max()), xytext=(455, absorbance.max() * .93),
                fontsize=8.5, color=ink, arrowprops=dict(arrowstyle="->", color=ink, lw=.9))
    for w, t, dy in ((432.0, "dip 432", 1.02), (436.5, "436.5", 1.07),
                     (575.0, "Q 575", 1.02), (627.0, "Qy 627", 1.02)):
        ax.axvline(w, color=ink, alpha=.15, lw=1)
        ax.text(w, absorbance.max() * dy, t, fontsize=7.5, ha="center", color=grey)
    ax.text(425, absorbance.max() * .28, "MEASURED\nnew lamp", fontsize=8, ha="center", color="#5a3fa6")
    ax.text(540, absorbance.max() * .28, "MEASURED\ncapillary corpus", fontsize=8, ha="center", color="#0b7a5f")
    ax.text(657, absorbance.max() * .28, "ANTICIPATED\nnever measured", fontsize=8, ha="center", color=grey)
    ax.set_xlim(404, 681); ax.set_ylim(-.04, absorbance.max() * 1.12)
    frame(ax, "The curve the lamp has to serve", ylabel="A = -log10(S/R)")
    fig.tight_layout(); fig.savefig(OUT + "anticipated_absorbance.png", dpi=170); plt.close(fig)

    # 2 -- delivered DN: winner vs R2 vs what is on the bench today
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    ax.axvspan(660, 680, color="#c9a227", alpha=.16)
    mNm, mDn = measured
    ax.plot(mNm, mDn, color="#8f8215", lw=1.6, label="the DIY lamp on the bench today (measured)")
    for name, colour, width in (("R2 as published", "#b0413e", 1.5),):
        v = lamp.combine(curves, REFERENCE_BUILDS[name])
        ax.plot(GRID, CEILING * v / v.max(), color=colour, lw=width, ls="--", label=name)
    v = lamp.combine(curves, RECOMMENDED)
    ax.plot(GRID, CEILING * v / v.max(), color="#0b6e4f", lw=2.2, label="this study's build")
    ax.axhline(16, ls=":", color="#c87a3c", lw=1.4)
    ax.text(678, 20, "16 DN", fontsize=7.5, color="#c87a3c", ha="right")
    ax.set_xlim(404, 681); ax.set_ylim(0, 255)
    frame(ax, "What each lamp puts on the sensor", ylabel="display DN (peak exposed to 240)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(OUT + "delivered_dn.png", dpi=170); plt.close(fig)

    # 3 -- sigma_A per target, the objective itself
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    names = [n for n, _, _ in TARGETS]
    xs = np.arange(len(names))
    series = [("this study's build", evaluate(lamp.combine(curves, RECOMMENDED), grid, absorbance), "#0b6e4f"),
              ("R2 as published", evaluate(lamp.combine(curves, REFERENCE_BUILDS["R2 as published"]),
                                           grid, absorbance), "#b0413e"),
              ("R2 with 630-640", evaluate(lamp.combine(
                  curves, REFERENCE_BUILDS["R2 with 630-640 instead of 660"]), grid, absorbance), "#c9822b")]
    width = 0.26
    for i, (name, sig, colour) in enumerate(series):
        ax.bar(xs + (i - 1) * width, [sig[n] for n in names], width, color=colour, label=name)
    ax.set_yscale("log"); ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=8, rotation=20, ha="right")
    frame(ax, "The objective: noise the metric would carry, per scored quantity", xlabel="")
    ax.set_ylabel("sigma_A (log scale)", fontsize=9, color=grey)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(OUT + "objective_by_target.png", dpi=170); plt.close(fig)

    # 4 -- the ranking, worst-band score of the top builds
    def shortLabel(text):
        """'2 x 4000k-4500k + 1 x 410nm-420nm' -> '2×4000K + 1×410'. The part numbers are long and the
        distinguishing part of each is its first token, so keep that and drop the rest."""
        parts = []
        for chunk in text.split(" + "):
            count, name = chunk.split(" x ")
            name = (name.replace("k-4500k", "K").replace("k-3200k", "K").replace("k-6000k", "K")
                        .replace("k-7000k", "K").replace("k-20000k", "K"))
            name = name.split("-")[0].replace("nm", "")
            parts.append("%s×%s" % (count, name))
        return " ".join(parts)

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    top = ranked[:12]
    ys = np.arange(len(top))[::-1]
    ax.barh(ys, [t["score"] for t in top], color=["#0b6e4f"] + ["#9bb8ab"] * (len(top) - 1))
    for y, t in zip(ys, top):
        ax.text(t["score"] * 1.01, y, "%.4f" % t["score"], va="center", fontsize=7.5, color=grey)
    ax.set_yticks(ys); ax.set_yticklabels([shortLabel(t["label"]) for t in top], fontsize=7.6)
    r2 = [t for t in ranked if t["label"] == label(REFERENCE_BUILDS["R2 as published"])]
    if r2:
        ax.axvline(r2[0]["score"], color="#b0413e", ls="--", lw=1.3)
        ax.text(r2[0]["score"] * 1.01, 3.0, "R2 as published\nrank %d of %d"
                % (1 + sum(1 for t in ranked if t["score"] < r2[0]["score"]), len(ranked)),
                fontsize=8, color="#b0413e", ha="left", va="center")
    ax.set_xlim(0, r2[0]["score"] * 1.30 if r2 else None)
    frame(ax, "Ranking of %d builds -- worst scored quantity, lower is better" % len(ranked),
          xlabel="sigma_A of the worst scored quantity")
    fig.tight_layout(); fig.savefig(OUT + "ranking.png", dpi=170); plt.close(fig)

    # 5 -- the board's own parts, so the bill of materials is visible
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    palette = {"410nm-420nm.jpg": "#6b3fa0", "440nm-450nm.jpg": "#2f6fd0",
               "480nm-485nm.jpg": "#1f9c9c", "4000k-4500k.jpg": "#c9a227",
               "630nm-640nm.jpg": "#b0413e"}
    for part, count in sorted(RECOMMENDED.items(), key=lambda kv: GRID[np.argmax(curves[kv[0]])]):
        c = curves[part] / curves[part].max()
        ax.plot(GRID, c, color=palette[part], lw=1.6,
                label="%d x %s" % (int(count), part.replace(".jpg", "")))
        ax.fill_between(GRID, 0, c, color=palette[part], alpha=.07)
    total = lamp.combine(curves, RECOMMENDED)
    ax.plot(GRID, total / total.max(), color="#111111", lw=2.2, label="the board, summed")
    ax.set_xlim(404, 681); ax.set_ylim(0, 1.08)
    frame(ax, "The board, part by part -- each normalised to its own peak",
          ylabel="relative emitted power")
    ax.legend(fontsize=8, frameon=False, ncol=2)
    fig.tight_layout(); fig.savefig(OUT + "board_parts.png", dpi=170); plt.close(fig)

    # 6 -- green vs brown absorbance. The successor to the old study's Figure 5, and the difference is
    # that this one is MEASURED over 440-630 rather than modelled from five Gaussians.
    oils = oilCurves()
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.axvspan(404, 448, color="#7a5cd6", alpha=.06)
    ax.axvspan(629.8, 681, color="#888888", alpha=.09)
    ax.axvspan(660, 680, color="#c9a227", alpha=.15)
    for name, colour, g, a in oils:
        ax.plot(g, a, color=colour, lw=2.0, label=name)
    if legacyForecast is not None:
        ax.plot(GRID, legacyForecast, color="#999999", lw=1.6, ls="--",
                label="the old study's modelled green -- peak 1.16 @ 439 nm, no doublet")
    top = max(a.max() for _, _, _, a in oils)
    ax.annotate("421.4 nm", xy=(421.4, top), xytext=(452, top * .93), fontsize=8.5, color=ink,
                arrowprops=dict(arrowstyle="->", color=ink, lw=.9))
    ax.text(425, top * .27, "blue: ONE oil's shape,\nscaled per oil", fontsize=7.5,
            ha="center", color="#5a3fa6")
    ax.text(540, top * .27, "MEASURED -- 4 oils x 3 reseats", fontsize=8, ha="center", color="#0b7a3f")
    ax.text(656, top * .27, "ANTICIPATED", fontsize=7.5, ha="center", color=grey)
    ax.set_xlim(404, 681); ax.set_ylim(-.04, top * 1.10)
    frame(ax, "Green against brown, across the whole range", ylabel="A = -log10(S/R)")
    ax.legend(fontsize=7.6, frameon=False, loc="center right")
    fig.tight_layout(); fig.savefig(OUT + "green_vs_brown.png", dpi=170); plt.close(fig)

    # 7 -- what the camera would see. Successor to the old Figure 6, at the f = 1.75 dose of §9.2.
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    board = lamp.combine(curves, RECOMMENDED)
    board = CEILING * board / board.max()
    ax.axvspan(660, 680, color="#c9a227", alpha=.15)
    ax.semilogy(GRID, board, color="#111111", lw=1.6, label="reference (the board, peak 240 DN)")
    for name, colour, g, a in (oils[0], oils[-1]):
        sample = board * 10 ** (-np.interp(GRID, g, a) / 1.75 / DECODE)
        ax.semilogy(GRID, sample, color=colour, lw=2.0, label="sample -- " + name)
    ax.axhline(16, ls=":", color="#c87a3c", lw=1.5)
    ax.text(678, 18.5, "16 DN floor", fontsize=8, color="#c87a3c", ha="right")
    ax.set_xlim(404, 681); ax.set_ylim(8, 300)
    frame(ax, "What the camera would see -- greenest and brownest, at the f = 1.75 dose",
          ylabel="display DN")
    ax.legend(fontsize=8, frameon=False, loc="lower center")
    fig.tight_layout(); fig.savefig(OUT + "transmitted.png", dpi=170); plt.close(fig)
    print("wrote 7 figures to " + OUT)


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="re-check the DN<->absorbance relation")
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    curves = {name: lamp.digitise(name) for name in lamp.PLOTS}
    grid, absorbance = compositeAbsorbance()

    captures = capturesFromPdf("20260811A/002.pdf")
    measuredNm, measuredDn = captures["REFERENCE"]
    measuredDn = savgol_filter(measuredDn, 41, 3)

    if args.verify:
        x, a = absorbanceFromPdf("20260811A/002.pdf")
        i = np.argmin(np.abs(measuredNm - 421.0))
        j = np.argmin(np.abs(x - 421.0))
        predicted = measuredDn[i] * 10 ** (-savgol_filter(a, 41, 3)[j] / DECODE)
        actual = savgol_filter(captures["SAMPLE"][1], 41, 3)[i]
        print("verify  421 nm: R = %.0f DN, A = %.3f -> S predicted %.1f DN, measured %.1f DN  (%s)"
              % (measuredDn[i], savgol_filter(a, 41, 3)[j], predicted, actual,
                 "OK" if abs(predicted - actual) < 1.0 else "MISMATCH"))
        print("verify  composite: peak A = %.3f at %.1f nm; A(660-680) = %.4f"
              % (absorbance.max(), grid[np.argmax(absorbance)],
                 absorbance[(grid >= 660) & (grid < 680)].mean()))

    rows, seen = [], set()
    for mix in candidates():
        key = tuple(sorted(mix.items()))
        if key in seen:
            continue
        seen.add(key)
        sigmas = evaluate(lamp.combine(curves, mix), grid, absorbance)
        row = {"label": label(mix), "mix": mix, "sigmas": sigmas,
               "score": score(sigmas, WEIGHTINGS["as written"])}
        for name, weights in WEIGHTINGS.items():
            row["score__" + name] = score(sigmas, weights)
        rows.append(row)
    rows.sort(key=lambda r: r["score"])
    print("\n%d distinct %d-emitter builds evaluated\n" % (len(rows), SLOTS))

    print("  rank  worst sigma_A | build")
    for i, row in enumerate(rows[:args.top]):
        print("  %4d  %12.5f | %s" % (i + 1, row["score"], row["label"]))

    print("\n  reference builds:")
    for name, mix in REFERENCE_BUILDS.items():
        sig = evaluate(lamp.combine(curves, mix), grid, absorbance)
        s = score(sig, WEIGHTINGS["as written"])
        rank = 1 + sum(1 for r in rows if r["score"] < s)
        print("  %4d  %12.5f | %s   (%s)" % (rank, s, label(mix), name))

    best = rows[0]
    print("\n  the winner, quantity by quantity:")
    for name, _, note in TARGETS:
        print("     %-12s %.5f   %s" % (name, best["sigmas"][name], note))

    # What the two violet slots cost the SHIPPED metric. The blue is optionality, not a bet, and this is
    # the number that says so -- see DOC_lamp_rebuild.md §9.1.
    shipped = ("soret-band", "clarity", "q-band", "far-anchor")
    withoutViolet = min((r for r in rows if "410nm-420nm.jpg" not in r["mix"]),
                        key=lambda r: max(r["sigmas"][k] for k in shipped))
    recommended = next(r for r in rows if r["mix"] == RECOMMENDED)
    print("\n  what the two violet slots cost the shipped metric bands:")
    print("     best board with NO 410-420: %s" % withoutViolet["label"])
    for key in shipped:
        print("        %-11s no-violet %.5f   recommended %.5f   %+.5f"
              % (key, withoutViolet["sigmas"][key], recommended["sigmas"][key],
                 recommended["sigmas"][key] - withoutViolet["sigmas"][key]))
    print("     and what they buy: soret-peak %.5f -> %.5f (%.1f x), doublet %.5f -> %.5f (%.1f x)"
          % (withoutViolet["sigmas"]["soret-peak"], recommended["sigmas"]["soret-peak"],
             withoutViolet["sigmas"]["soret-peak"] / recommended["sigmas"]["soret-peak"],
             withoutViolet["sigmas"]["doublet"], recommended["sigmas"]["doublet"],
             withoutViolet["sigmas"]["doublet"] / recommended["sigmas"]["doublet"]))

    signals, sweep = doseSweep(lamp.combine(curves, RECOMMENDED), grid, absorbance)
    print("\n  dose -- signal-to-noise against dilution, on the recommended board")
    print("     signal at the capillary dose: doublet %.4f | Soret %.4f | Q %.4f"
          % (signals["doublet"], signals["soret-band"], signals["q-band"]))
    print("        f    SNR doublet  SNR Soret  SNR Q   recipe (2 capillaries / x mL)")
    for row in sweep:
        print("     %5.2f      %7.1f    %7.1f  %6.1f   %.0f mL"
              % (row["f"], row["snr_doublet"], row["snr_soret-band"], row["snr_q-band"],
                 row["mlPer2Capillaries"]))
    peak = max(sweep, key=lambda r: r["snr_doublet"])
    print("     doublet SNR peaks at f = %.2f  (20260811A/002 sat at f = 1.91)" % peak["f"])

    print("\n  robustness -- rank of the winner under each weighting:")
    for name in WEIGHTINGS:
        ordered = sorted(rows, key=lambda r: r["score__" + name])
        rank = 1 + next(i for i, r in enumerate(ordered) if r["label"] == best["label"])
        print("     %-32s winner ranks %3d   (best there: %s)" % (name, rank, ordered[0]["label"]))

    os.makedirs(OUT, exist_ok=True)
    with open(OUT + "ranking.json", "w") as handle:
        json.dump({"targets": [{"name": n, "spec": s, "note": t} for n, s, t in TARGETS],
                   "sigmaDn": SIGMA_DN, "ceilingDn": CEILING, "decode": DECODE,
                   "ranked": [{k: v for k, v in r.items() if k != "mix"} for r in rows[:60]]},
                  handle, indent=1)
    print("\n  wrote " + OUT + "ranking.json")

    if args.figures:
        legacy = None
        try:                                   # the old study's modelled green, for the overlay
            import oil_forecast_410_680 as forecast
            legacy = forecast.buildOils()[0]
        except Exception as error:             # optional -- the figure just loses one dashed line
            print("  (legacy forecast unavailable: %s)" % error)
        writeFigures(curves, grid, absorbance, rows, best, (measuredNm, measuredDn), legacy)


if __name__ == "__main__":
    main()
