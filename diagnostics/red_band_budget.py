"""The DN budget of the RED band -- what one camera count is worth, and what a warming filter buys.

    docs/DOC_red_band_budget.md   the written account  ->  Spectracs_RedBandBudget.pdf
    SPEC_capture_quality.md §16.43   the entry in the evidence base

⭐ THE QUESTION THIS ANSWERS (Edwin, 2026-09-06/07): `Rv`'s verdict rests on A(622-627), and that band is the
faintest thing the instrument measures. How many counts is it, what is one count worth, and would a
blue-attenuating filter -- which cancels in `T = S/R` and so costs nothing in accuracy -- buy enough of them
to matter?

⛔⛔ THE ANSWER IS "NOT MUCH", AND THE MEASUREMENT THAT SETTLES IT IS NOT THE COUNT BUT THE VARIANCE SPLIT.
Two reads of ONE aliquot through ONE reference capture differ by ~1.5 Rv; two independent fills of the same
oil in the same sitting differ by ~4.0. The instrument -- quantisation included -- is 1.5 of the 4.0, and a
filter can only attack that part. An earlier draft of this analysis modelled the quantisation term at 2.8 Rv
from the count of distinct DN levels and over-stated the filter's value by a factor of three; the repeat-read
measurement replaced the model and is what this file now quotes.

⭐⭐ WHAT SURVIVES, AND IT IS THE MORE USEFUL FINDING: a **1 % error in the reference at 622-627 is worth
5.8-9.1 Rv**. That is the entire scale of every difference argued over on 2026-09-06. `ROADMAP.md` item 3
asks for a red reference channel in `monitorRecord` and prices it at "≈5 Rv, the size of σ_fill itself";
§16.43.4 records a measured instance of exactly that.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/red_band_budget.py
"""
import collections
import os

import numpy as np

import peak_ratio_archive as archive
import d2r_all_runs as d2r
import reduction_sum_vs_max as replay

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
FIGURES = os.path.join(REPO, "docs", "figures")

SUITE = "20280831_suite"
# The sittings, as `d2r_all_runs.DELAYED_FILL` records them. ⛔ Grouping by SESSION would put LugitschC-F in
# four sittings of one fill each and hide every within-sitting comparison this file is built on.
SITTING = {"20260828LugitschA": "night 08-29/30", "20260828LugitschB": "night 08-29/30",
           "20260828SteirerkraftA": "night 08-29/30", "20260828SteirerkraftB": "night 08-29/30",
           "20260828LugitschC": "afternoon 08-30", "20260828LugitschD": "afternoon 08-30",
           "20260828LugitschE": "afternoon 08-30", "20260828LugitschF": "afternoon 08-30"}

# An APPROXIMATE published shape for a Wratten 85, normalised at 640 nm. ⛔ INDICATIVE ONLY — the rig measures
# the real curve in one capture (a reference with the filter divided by one without), and §7 says to do that
# before buying anything. It is here so the expected gain can be estimated at all, not because it is trusted.
W85 = ([400, 450, 500, 550, 600, 650], [0.28, 0.42, 0.60, 0.76, 0.91, 0.97])


def sittingOf(session):
    return SITTING.get(session, "evening 08-31" if session.startswith("20260831") else "evening 09-06")


def legs(relative):
    """`(nm, referenceDN, sampleDN)` straight from the report's attached frames, max over the three channels.

    ⚠ THE MAX, not the sum or the green channel: at 448 nm only BLUE carries signal and at 624 only RED, so a
    single channel is zero over most of the window and the mean is a third of the truth. `reduction_sum_vs_max`
    is where that choice is argued."""
    reference, frames = replay.attachments(os.path.join(archive.ARCHIVE, relative))
    nm, referenceDn, offset = replay.alignedChannels(frames["reference"], reference)
    _, sampleDn, _ = replay.alignedChannels(frames["sample"], reference, offset=offset)
    return (np.asarray(nm, float),
            np.asarray(referenceDn, float).max(1), np.asarray(sampleDn, float).max(1))


def bandMean(nm, values, low, high):
    return float(values[(nm >= low) & (nm <= high)].mean())


def firstReads():
    return [row for row in d2r.suiteCorpus() if row["run"].endswith("001.pdf")]


# --------------------------------------------------------------------------- the numbers

def countsPerOil(rows):
    """Red-band counts and the Rv cost of ONE count, per oil.

    ⭐ `1 DN = x Rv` is the whole point of the file. dRv/dS = (100/den)·(2.2·log10 e)/S, where the 2.2 is the
    `pow2.2` capture decode (`captureDecode` in every header) and `den = A_Q − A_valley` is Rv's denominator."""
    out = collections.defaultdict(list)
    for row in rows:
        nm, reference, sample = legs(row["run"])
        band = lambda low, high: bandMean(row["nm"], row["a"], low, high)          # noqa: E731
        denominator = band(565.0, 580.0) - band(500.0, 560.0)
        referenceDn = bandMean(nm, reference, 622.0, 627.0)
        sampleDn = bandMean(nm, sample, 622.0, 627.0)
        perCount = 100.0 / denominator * 2.2 * np.log10(np.e) / sampleDn
        out[row["oil"]].append((referenceDn - sampleDn, perCount, denominator))
    return out


def varianceSplit(corpus):
    """`(instrument, fill)` in Rv — the measurement that decides what a filter can be worth.

    ⭐⭐ THE TWO ARE SEPARABLE BECAUSE 001 AND 002 SHARE A REFERENCE CAPTURE AND AN ALIQUOT. Their difference
    therefore contains the instrument and whatever the sample did in the gap, and NOTHING of the preparation.
    Independent fills of one oil in one sitting contain all three.
    ⚠ The 08-28 Steirerkraft pair is left in even though its two reads differ by 5-7 Rv: that is the sample
    browning under the lamp (§16.36), so the instrument figure quoted here is an OVER-estimate, which is the
    safe direction for a claim that the filter is not worth much."""
    reads = collections.defaultdict(dict)
    for row in corpus:
        reads[row["session"]][row["run"].split("/")[2][:3]] = row["Rv"]
    within = [abs(v["002"] - v["001"]) for v in reads.values() if "001" in v and "002" in v]
    instrument = float(np.median(within)) / np.sqrt(2.0)

    groups = collections.defaultdict(list)
    for row in corpus:
        if row["run"].endswith("001.pdf"):
            groups[(row["oil"], sittingOf(row["session"]))].append(row["Rv"])
    parts = [(len(v) - 1, np.std(v, ddof=1)) for v in groups.values() if len(v) > 1]
    dof = sum(p[0] for p in parts)
    fill = float(np.sqrt(sum(p[0] * p[1] ** 2 for p in parts) / dof))
    return instrument, fill, dof, sorted(within), groups


def filterGain(rows):
    """What a Wratten-85-shaped filter would do to the red band, per oil.

    ⛔ THE FILTER CANCELS IN `T = S/R` — it sits in both legs — so this changes the DN distribution and NOTHING
    ELSE. That is the entire argument for it: free counts, no new systematic. What it cannot do is flatten the
    580 nm Bayer crossover, which is a hole in the SENSOR and not in the lamp; §5 is the arithmetic of how much
    that costs the idea."""
    out = collections.defaultdict(list)
    for row in rows:
        nm, reference, sample = legs(row["run"])
        band = lambda low, high: bandMean(row["nm"], row["a"], low, high)          # noqa: E731
        denominator = band(565.0, 580.0) - band(500.0, 560.0)
        transmission = np.interp(nm, *W85)
        window = (nm >= 442.0) & (nm <= 632.0)
        gain = 230.0 / float(np.percentile((reference * transmission)[window], 99.5))
        before = (bandMean(nm, reference, 622.0, 627.0), bandMean(nm, sample, 622.0, 627.0))
        after = (bandMean(nm, reference * transmission * gain, 622.0, 627.0),
                 bandMean(nm, sample * transmission * gain, 622.0, 627.0))
        cost = lambda s: 100.0 / denominator * 2.2 * np.log10(np.e) / s             # noqa: E731
        out[row["oil"]].append((before[0] - before[1], after[0] - after[1],
                                cost(before[1]), cost(after[1]), gain))
    return out


def referenceLeverage(rows):
    """What a 1 % error in the reference at 622-627 costs, per oil — and the 09-06 instance of it."""
    out = {}
    for row in rows:
        band = lambda low, high: bandMean(row["nm"], row["a"], low, high)          # noqa: E731
        denominator = band(565.0, 580.0) - band(500.0, 560.0)
        out.setdefault(row["oil"], []).append(100.0 * 2.2 * np.log10(1.01) / denominator)
    return {oil: float(np.mean(v)) for oil, v in out.items()}


# --------------------------------------------------------------------------- figures

INK, MUTED, LINE = "#1c211c", "#5c655c", "#b9c1b9"
GREEN, GREEN_DK, BLUE, RED, AMBER, PANEL = "#3f7d3f", "#2f5d2f", "#3a5fa8", "#b03a3a", "#c8891f", "#f5f8f5"
FONT = 'font-family="Segoe UI,Helvetica Neue,Arial,sans-serif"'
MONO = 'font-family="Consolas,DejaVu Sans Mono,monospace"'


def text(x, y, body, size=12, fill=INK, anchor="start", weight=None, mono=False):
    bits = ['<text x="%.1f" y="%.1f" %s font-size="%.1f" fill="%s" xml:space="preserve"'
            % (x, y, MONO if mono else FONT, size, fill)]
    if anchor != "start":
        bits.append(' text-anchor="%s"' % anchor)
    if weight:
        bits.append(' font-weight="%s"' % weight)
    bits.append(">%s</text>" % body)
    return "".join(bits)


class Axes(object):
    def __init__(self, x0, y0, x1, y1, wLo, wHi, vLo, vHi):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.wLo, self.wHi, self.vLo, self.vHi = wLo, wHi, vLo, vHi

    def px(self, w):
        return self.x0 + (w - self.wLo) / (self.wHi - self.wLo) * (self.x1 - self.x0)

    def py(self, v):
        return self.y1 - (v - self.vLo) / (self.vHi - self.vLo) * (self.y1 - self.y0)

    def frame(self, wTicks, vTicks, fmt="%g", label=""):
        out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ffffff" stroke="%s"/>'
               % (self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0, LINE)]
        for w in wTicks:
            x = self.px(w)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e8ece8" stroke-width="0.7"/>'
                       % (x, self.y0, x, self.y1))
            out.append(text(x, self.y1 + 16, "%d" % w, 11, MUTED, anchor="middle"))
        for v in vTicks:
            y = self.py(v)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e8ece8" stroke-width="0.7"/>'
                       % (self.x0, y, self.x1, y))
            out.append(text(self.x0 - 8, y + 4, fmt % v, 11, MUTED, anchor="end"))
        out.append(text((self.x0 + self.x1) / 2, self.y1 + 36, "wavelength (nm)", 11.5, MUTED, anchor="middle"))
        if label:
            out.append('<g transform="translate(%.1f,%.1f) rotate(-90)">%s</g>'
                       % (self.x0 - 46, (self.y0 + self.y1) / 2, text(0, 0, label, 11.5, MUTED, anchor="middle")))
        return out

    def band(self, lo, hi, colour, alpha):
        return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="%.2f"/>'
                % (self.px(lo), self.y0, self.px(hi) - self.px(lo), self.y1 - self.y0, colour, alpha))

    def path(self, xs, ys, colour, width=1.9, dash=None):
        pts = " ".join("%.1f,%.1f" % (self.px(x), self.py(y)) for x, y in zip(xs, ys))
        extra = ' stroke-dasharray="%s"' % dash if dash else ""
        return ('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f" '
                'stroke-linejoin="round"%s/>' % (pts, colour, width, extra))


def writeSvg(name, width, height, body):
    os.makedirs(FIGURES, exist_ok=True)
    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
            '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height, width, height, width, height))
    path = os.path.join(FIGURES, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head + "".join(body) + "</svg>")
    print("wrote %s" % os.path.relpath(path, REPO))


def figureBudget(relative):
    """Where the counts are: the two legs, the four windows, and the gap that carries the verdict."""
    nm, reference, sample = legs(relative)
    window = (nm >= 442.0) & (nm <= 634.0)
    nm, reference, sample = nm[window], reference[window], sample[window]
    W, H = 940, 524
    ax = Axes(80, 66, 900, 372, 442, 634, 0, 260)
    out = [text(W / 2, 30, "Where the camera counts are", 16, GREEN_DK, anchor="middle", weight="700"),
           text(W / 2, 49, "one reference and one sample capture, and the four windows the metrics read",
                11.5, MUTED, anchor="middle")]
    out += ax.frame(range(450, 631, 20), range(0, 261, 50), "%d", "camera DN")
    for lo, hi, label, colour in ((448, 460, "Soret", BLUE), (500, 560, "valley", MUTED),
                                  (565, 580, "Q", GREEN), (622, 627, "red", RED)):
        out.append(ax.band(lo, hi, colour, 0.13))
        out.append(text(ax.px((lo + hi) / 2), 62, label, 10.5, colour, anchor="middle", weight="700"))
    out.append(ax.path(nm, reference, BLUE, 2.0))
    out.append(ax.path(nm, sample, RED, 2.0))
    gap = bandMean(nm, reference, 622, 627) - bandMean(nm, sample, 622, 627)
    x = ax.px(624.5)
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.4"/>'
               % (x, ax.py(bandMean(nm, sample, 622, 627)), x, ax.py(bandMean(nm, reference, 622, 627)), AMBER))
    out.append(text(x - 8, ax.py(bandMean(nm, sample, 622, 627)) + 26,
                    "%.0f counts — the whole verdict" % gap, 11.5, AMBER, anchor="end", weight="700"))
    soretGap = bandMean(nm, reference, 448, 460) - bandMean(nm, sample, 448, 460)
    out.append(text(ax.px(454), ax.py(140), "%.0f counts" % soretGap, 11, BLUE, anchor="middle"))
    out.append(text(90, 448, "reference", 12, BLUE, weight="700"))
    out.append(text(90, 468, "sample", 12, RED, weight="700"))
    out.append(text(200, 448, "The Soret gap is %.0f counts and the red gap is %.0f. `Rv` is built on the "
                              "second one." % (soretGap, gap), 11.5, INK))
    out.append(text(200, 468, "The dip at 580 nm is the green/red Bayer crossover — a hole in the sensor, "
                              "not in the lamp.", 11.5, MUTED))
    out.append(text(200, 488, "No filter in front of the lamp can fill it.", 11.5, MUTED))
    return writeSvg("redband_budget.svg", W, H, out)


def figureFilter(relative):
    """The target transmission the lamp asks for, against an approximate Wratten 85."""
    nm, reference, _ = legs(relative)
    window = (nm >= 442.0) & (nm <= 634.0)
    nm, reference = nm[window], reference[window]
    red = bandMean(nm, reference, 622.0, 627.0)
    ideal = np.clip(red / np.clip(reference, 1.0, None), 0.0, 1.0)
    W, H = 940, 492
    ax = Axes(80, 66, 900, 336, 442, 634, 0.0, 1.15)
    out = [text(W / 2, 30, "What the filter has to do, and what an 85 actually does", 16, GREEN_DK,
                anchor="middle", weight="700"),
           text(W / 2, 49, "transmission needed to flatten this lamp, normalised at 625 nm", 11.5, MUTED,
                anchor="middle")]
    out += ax.frame(range(450, 631, 20), [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f", "transmission")
    out.append(ax.band(622, 627, RED, 0.13))
    out.append(ax.path(nm, ideal, INK, 1.8))
    out.append(ax.path(nm, np.interp(nm, *W85) / np.interp(640.0, *W85), AMBER, 2.0, dash="7 4"))
    out.append(text(ax.px(520), ax.py(0.47), "what this lamp asks for", 11.5, INK, weight="700"))
    out.append(text(ax.px(500), ax.py(0.86), "a Wratten 85", 11.5, AMBER, weight="700"))
    out.append(text(ax.px(580), ax.py(1.08), "580 — the Bayer hole, not the lamp", 10.5, MUTED, anchor="middle"))
    out.append(text(80, 404, "The 85 is the right shape and slightly too gentle in the green. It cannot "
                             "follow the 580 nm spike, which is why the", 11.5, MUTED))
    out.append(text(80, 422, "realised gain is ×1.4–1.6 rather than the ×2.1 a perfectly matched filter "
                             "would give.", 11.5, MUTED))
    out.append(text(80, 452, "⚠ The dashed curve is an APPROXIMATE published shape. Measure the real one: one "
                             "reference capture with the filter,", 11.5, RED))
    out.append(text(80, 470, "divided by one without, IS its transmission on this rig's own wavelength axis.",
                    11.5, RED))
    return writeSvg("redband_filter.svg", W, H, out)


# --------------------------------------------------------------------------- entry point

def main():
    rows = firstReads()
    corpus = d2r.suiteCorpus()

    print("\nRED-BAND COUNTS, first read of each fill")
    print("%-16s %3s %11s %12s" % ("oil", "n", "ref-sample", "1 DN = Rv"))
    for oil, values in sorted(countsPerOil(rows).items()):
        v = np.array(values)
        print("%-16s %3d %11.1f %12.1f" % (oil, len(v), v[:, 0].mean(), v[:, 1].mean()))

    instrument, fill, dof, within, groups = varianceSplit(corpus)
    print("\nTHE VARIANCE SPLIT -- this is what decides whether more counts help")
    print("  same aliquot, same reference, two reads : median |dRv| %.2f  =>  instrument ~ %.1f Rv"
          % (np.median(within), instrument))
    print("  independent fills, same oil + sitting   : pooled sd %.2f Rv on %d df" % (fill, dof))
    print("  => the instrument is %.0f %% of the variance; the fill is the rest"
          % (100.0 * instrument ** 2 / fill ** 2))

    print("\nWHAT A 1 %% REFERENCE ERROR AT 622-627 IS WORTH")
    for oil, value in sorted(referenceLeverage(rows).items()):
        print("  %-16s %.1f Rv" % (oil, value))

    print("\nTHE FILTER, MODELLED (Wratten 85 shape)")
    print("%-16s %11s %10s %8s %11s %11s" % ("oil", "counts now", "with 85", "gain", "1DN now", "1DN after"))
    allGain = []
    for oil, values in sorted(filterGain(rows).items()):
        v = np.array(values)
        allGain.append(v)
        print("%-16s %11.1f %10.1f %7.2fx %11.1f %11.1f"
              % (oil, v[:, 0].mean(), v[:, 1].mean(), v[:, 1].mean() / v[:, 0].mean(),
                 v[:, 2].mean(), v[:, 3].mean()))
    stacked = np.vstack(allGain)
    scale = stacked[:, 3].mean() / stacked[:, 2].mean()
    other = np.sqrt(fill ** 2 - instrument ** 2)
    after = np.sqrt(other ** 2 + (instrument * scale) ** 2)
    print("  exposure multiplier x%.2f    instrument term scales by %.2f" % (stacked[:, 4].mean(), scale))
    print("  => sigma_fill %.2f -> %.2f  (%.0f %% better)" % (fill, after, 100 * (1 - after / fill)))

    reference = os.path.join(SUITE, "20260906BillaJaNatuerlichE", "001.pdf")
    print()
    figureBudget(reference)
    figureFilter(reference)


if __name__ == "__main__":
    main()
