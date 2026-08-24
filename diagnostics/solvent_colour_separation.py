"""Do the INDEX-MATCHED solvents separate by colour better than the ISOPROPANOL archive — and is
turbidity the reason?  (Edwin's hypothesis, 2026-08-24)

THE CLAIM. Pumpkin oil in isopropanol never truly dissolves: n = 1.377 against the oil's 1.47, so it
disperses and the droplets scatter (`DOC_solvent_and_hue.md` §2). Sunflower oil is n = 1.473 — like into
like, a real solution, and the baseline goes away (A_valley 0.018 against an archive typical 0.09 and a
worst 0.28). A flat Mie pedestal ADDS a broadband component to the absorbance, which drags the
chromaticity toward the white point. If the pedestal varies fill to fill, so does that drag — and the
classes smear into each other.

⚠ THE CONFOUND THAT DECIDES WHETHER THIS IS ANSWERABLE. The sunflower set is ONE oil pair, ONE session,
ONE rig, seven fills. The isopropanol corpus is 88 runs, many oils, a year, a mechanical rebuild and two
rigs. A larger within-class variance for isopropanol is therefore expected for reasons that have nothing
to do with turbidity, and a naive d-vs-d comparison would "confirm" the hypothesis whatever the truth.
So this script does three things, and only the last two are evidence:

  1  the naive comparison, printed so it can be seen and discounted;
  2  ⭐ the DIRECT test — within the isopropanol corpus alone, does colour track A_valley? If scatter
     drags chromaticity toward white, p_e must FALL as A_valley RISES, and the correlation is the claim;
  3  ⭐ the CONTROLLED test — restrict the corpus to its clearest fills and re-measure the separation.
     If turbidity is what smears the classes, cutting the turbid runs must improve it.

A_valley (500-560 nm) is the archive's own turbidity proxy: it sits between the two pigment bands and
should hold almost nothing, so what is there is scattering (`SPEC_settled_measurement.md` §52.3).

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python diagnostics/solvent_colour_separation.py
"""
import math
import os
import sys
import tempfile

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil

util = EvaluationColorUtil()

# ⛔ CORRECTED 2026-08-24. These are TWO different solvents, and an earlier cut of this script called
# all seven "sunflower": `20260821*` is the WHITE SPIRIT session (peak_ratio_archive's `SPIRIT` set),
# `20260822*` is the sunflower one (DOC_solvent_and_hue.md, "the evening of 22 August").
#
# They are grouped here because the physics groups them: both are NONPOLAR and both are close to the
# oil's n = 1.47 (white spirit ~1.44, sunflower 1.473), where isopropanol is polar and n = 1.377. Both
# therefore DISSOLVE the oil where isopropanol only emulsifies it. ⚠ Read every number below as
# "index-matched solvents", never as "sunflower": n = 3 sunflower is far too thin to stand alone.
WHITE_SPIRIT = [("brown", "20260821BillaCleverA/001.pdf"), ("brown", "20260821BillaCleverA/002.pdf"),
                ("green", "20260821LugitschA/001.pdf"), ("green", "20260821LugitschA/002.pdf")]
SUNFLOWER_ONLY = [("brown", "20260822BillaClever/001.pdf"),
                  ("green", "20260822Lugitsch/002.pdf"), ("green", "20260822Lugitsch/003.pdf")]
SUNFLOWER = WHITE_SPIRIT + SUNFLOWER_ONLY            # the index-matched group


# ---------------------------------------------------------------- 4: the session-matched comparison
# ⭐ THE ONLY FAIR TEST. The sunflower set is one pair, one session, one rig. Compare it against
# isopropanol SESSIONS that also carry both classes — like for like, with the year, the rebuild and the
# oil-to-oil variety held out. Sessions are dated folder prefixes that `peak_ratio_archive` labels.
MATCHED_SESSIONS = {
    "20260727": ["20260727B", "20260727E", "20260727C", "20260727D"],
    "20260807": ["20260807A", "20260807B", "20260807C"],
    "20260812": ["20260812BillJaNatuerlich", "20260812_BillaClever", "20260812_BillaCleverB"],
}


def bandMean(wavelengths, values, low, high):
    inside = [v for w, v in zip(wavelengths, values) if low <= w <= high]
    return float(numpy.mean(inside)) if inside else float("nan")


def measure(path, scratch):
    """Colour + turbidity for one report, or None when it carries no usable absorbance."""
    workflow = archive.workflowOf(path, scratch)
    if workflow is None:
        return None
    trace = archive.despikedTrace(workflow)
    if trace is None:
        return None
    wavelengths, absorbance = trace
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {float(w): float(a) for w, a in zip(wavelengths, absorbance)}
    xy = util.spectrumToChromaticity(spectrum, ceiling=util.RELATIVE)
    if xy is None:
        return None
    lightness, chroma, hue, _ = util.spectrumToLab(spectrum, path=3.0, ceiling=util.RELATIVE)
    return {"valley": bandMean(wavelengths, absorbance, 500.0, 560.0),
            "soret": bandMean(wavelengths, absorbance, 448.0, 460.0),
            "theta": util.directionFromWhite(xy), "purity": util.purityOf(xy),
            "L": lightness, "C": chroma, "h": hue}


def cohen(first, second):
    first, second = numpy.array(first, float), numpy.array(second, float)
    if len(first) < 2 or len(second) < 2:
        return float("nan"), True
    pooled = math.sqrt(((len(first) - 1) * first.var(ddof=1) + (len(second) - 1) * second.var(ddof=1))
                       / (len(first) + len(second) - 2))
    overlaps = not (first.min() > second.max() or second.min() > first.max())
    return (first.mean() - second.mean()) / pooled, overlaps


def report(title, rows):
    print(title)
    green = [r for r in rows if r["class"] == "green"]
    brown = [r for r in rows if r["class"] == "brown"]
    print("   n = %d green, %d brown   |   A_valley %.3f +/- %.3f"
          % (len(green), len(brown),
             numpy.mean([r["valley"] for r in rows]), numpy.std([r["valley"] for r in rows], ddof=1)))
    for field, unit in (("purity", "%"), ("theta", "deg"), ("h", "deg"), ("C", ""), ("L", "")):
        d, overlaps = cohen([r[field] for r in green], [r[field] for r in brown])
        print("     %-7s green %8.2f +/- %5.2f | brown %8.2f +/- %5.2f | d = %6.2f  %s"
              % (field + unit and field,
                 numpy.mean([r[field] for r in green]), numpy.std([r[field] for r in green], ddof=1),
                 numpy.mean([r[field] for r in brown]), numpy.std([r[field] for r in brown], ddof=1),
                 d, "OVERLAP" if overlaps else "SEPARATE"))
    print()


def main():
    with tempfile.TemporaryDirectory() as scratch:
        sunflower = []
        for label, relative in SUNFLOWER:
            row = measure(os.path.join(archive.ARCHIVE, relative), scratch)
            if row:
                row["class"] = label
                row["run"] = relative
                sunflower.append(row)

        isopropanol = []
        for folder, name in archive.walkReports():
            series = os.path.relpath(folder, archive.ARCHIVE)
            series = "(root)" if series == "." else series
            key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
            label = archive.classOf({"series": series, "run": key})
            if label not in ("green", "brown"):
                continue
            row = measure(os.path.join(folder, name), scratch)
            if row:
                row["class"] = label
                row["series"] = series
                isopropanol.append(row)

    print("=" * 96)
    print("1  THE NAIVE COMPARISON  -  printed to be discounted, not believed")
    print("=" * 96)
    report("  INDEX-MATCHED SOLVENTS  (white spirit + sunflower; one oil pair, two sessions)", sunflower)
    report("  ISOPROPANOL  (many oils, a year, two rigs, a rebuild)", isopropanol)
    report("    of which SUNFLOWER only (n = 3, far too thin to stand alone)",
           [r for r in sunflower if r["run"].startswith("20260822")])

    print("=" * 96)
    print("2  THE DIRECT TEST  -  inside the isopropanol corpus, does colour track A_valley?")
    print("=" * 96)
    valley = numpy.array([r["valley"] for r in isopropanol])
    print("   A_valley over the corpus: %.3f +/- %.3f   [%.3f .. %.3f]"
          % (valley.mean(), valley.std(ddof=1), valley.min(), valley.max()))
    print("   sunflower for comparison: %.3f +/- %.3f   [%.3f .. %.3f]"
          % (numpy.mean([r["valley"] for r in sunflower]),
             numpy.std([r["valley"] for r in sunflower], ddof=1),
             min(r["valley"] for r in sunflower), max(r["valley"] for r in sunflower)))
    print()
    print("   PREDICTED: a flat scattering pedestal drags chromaticity toward white => p_e FALLS as")
    print("              A_valley RISES, i.e. a NEGATIVE correlation.")
    for field in ("purity", "theta", "h", "C", "L"):
        values = numpy.array([r[field] for r in isopropanol])
        print("     r(%-7s, A_valley) = %+.3f" % (field, numpy.corrcoef(values, valley)[0, 1]))
    print()

    print("=" * 96)
    print("3  THE CONTROLLED TEST  -  cut the turbid runs; does the separation improve?")
    print("=" * 96)
    for cut in (0.30, 0.15, 0.10):
        subset = [r for r in isopropanol if r["valley"] <= cut]
        if len({r["class"] for r in subset}) < 2:
            continue
        report("  isopropanol, A_valley <= %.2f" % cut, subset)

    print("=" * 96)
    print("4  THE FAIR COMPARISON  -  isopropanol SESSIONS that carry both classes, like for like")
    print("=" * 96)
    for session, series in sorted(MATCHED_SESSIONS.items()):
        subset = [r for r in isopropanol if r.get("series") in series]
        if len({r["class"] for r in subset}) < 2:
            continue
        report("  isopropanol session %s" % session, subset)


if __name__ == "__main__":
    main()


