"""Is the 624 nm band BROADER in isopropanol than in an index-matched solvent?  (E3, 2026-08-24)

THE QUESTION. Edwin observed the red peak strengthening in BOTH white spirit and sunflower oil — both
nonpolar and index-matched to the oil (n ~ 1.44 and 1.473 against 1.47) where isopropanol is polar at
1.377 and only emulsifies it. `SPEC_color_retrieval.md` §7.16.4a proposes the mechanism: droplets
scatter into a ~17 deg forward lobe, a grating maps input angle onto wavelength, so an emulsion
broadens the instrument's effective linewidth and narrow features wash out while broad ones survive.

⛔ WHY NOT THE PROBE-LINE VERSION. §7.16.5's E3 said to measure the WIDTH of a narrow lamp line under
two solvents. There is no such line to measure. Both candidates are DETECTOR artefacts, not optical
features in the beam:
  * 608-610 nm is a Bayer channel crossover (`DOC_lamp_rebuild.md` §6) -- a position-space property of
    the sensor;
  * the 473 nm "blue-pump edge" rises in ONE OR TWO SAMPLES (0.15-0.29 nm) against a grid step of
    0.146 nm, which is far below any plausible instrument linewidth -- and it sits at 472.5 nm in the
    REFERENCE and 473.1 nm in the SAMPLE of the same run. An optical feature cannot move; a
    threshold where the dominant Bayer channel switches moves with signal level, which is exactly what
    that 0.6 nm shift is.
⇒ Measure the band we actually care about instead.

⭐⭐ THE MEASURE THAT WORKS: AREA, dose-free. CONVOLUTION CONSERVES AREA, so blurring must leave a band's
integral alone. Report `area(624) / area(Soret)` -- both scale with concentration, so the ratio is
dose-free and the comparison survives a recipe change. RESULT (2026-08-24):

    index-matched (spirit + sunflower, n = 7)   0.0221 +/- 0.0107   [0.0110 .. 0.0368]
    isopropanol                    (n = 72)     0.0013 +/- 0.0010   [0.0001 .. 0.0036]
    A_Soret, the dose check         0.877 +/- 0.263  vs  0.762 +/- 0.146   -- 1.2x, overlapping

  => 16.6x at matched dose, d = +6.65, ranges SEPARATE.  A 16.6x dose-free AREA difference is NOT
     convolution, so RESOLUTION LOSS IS REFUTED. And every other optical candidate fails for one shared
     reason -- they all hurt the SORET more, so each predicts a LARGER Soret-normalised Q band in the
     emulsion: veiling glare scales contrast by T_base/(T_base+S), severe at the Soret and mild at
     624 nm; the package/sieve effect flattens the strongest bands most.

⛔⛔ THE MEASURE THAT DOES NOT WORK, AND WHY IT IS STILL PRINTED. `W = area / height` -- the equivalent
width -- looked like the natural discriminator and is CONFOUNDED. Within isopropanol r(W, height) =
+0.543, and W rises across height tertiles (1.63 -> 2.21 -> 2.70 nm): a band near the noise floor has
its peak set by a noise excursion, which inflates height and deflates W. Worse, the two height
populations DO NOT OVERLAP -- every isopropanol band is fainter than the weakest index-matched one -- so
there is no fair slice to compare W on.
⚠ And the diffuser A/B could not validate it: that is the archive's one known blurring event, where W
should RISE, but the diffuser erases the 624 band completely (no band above the chord on all five
diffuser-IN runs) so W is undefined there. W HAS NEVER BEEN SHOWN TO DETECT BLURRING ON THIS INSTRUMENT.
It is printed below only so the confound stays visible; the conclusion rests on AREA alone.

⚠ THE PHENOMENON WAS NOT DISCOVERED HERE. `SPEC_metric_research.md` §12.6 established it on 110 fills --
Soret-normalised band height doubles in white spirit, no overlap, turbidity ruled out at r = -0.016 --
and recorded the cause as UNSETTLED. This script removes one candidate; it does not settle it. §12.4a.

Baseline: a straight chord under the band between the 612-615 anchor and 627-630, the same anchors
`SPEC_metric_research.md` §12 uses, so this measures the feature that metric reads.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python diagnostics/band_width_by_solvent.py
"""
import math
import os
import sys
import tempfile

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
from solvent_colour_separation import SUNFLOWER as INDEX_MATCHED

BAND = (617.0, 630.0)               # where the 624 feature lives
LEFT_ANCHOR = (612.0, 615.0)
RIGHT_ANCHOR = (627.0, 630.0)


def bandMean(nm, values, low, high):
    inside = values[(nm >= low) & (nm <= high)]
    return float(numpy.mean(inside)) if len(inside) else float("nan")


def equivalentWidth(nm, absorbance):
    """(W, height, area) for the 624 feature above its local chord — or None when the band is absent."""
    if nm[0] > LEFT_ANCHOR[0] or nm[-1] < RIGHT_ANCHOR[1] - 1.0:
        return None
    leftX = 0.5 * (LEFT_ANCHOR[0] + LEFT_ANCHOR[1])
    rightX = 0.5 * (RIGHT_ANCHOR[0] + RIGHT_ANCHOR[1])
    leftY = bandMean(nm, absorbance, *LEFT_ANCHOR)
    rightY = bandMean(nm, absorbance, *RIGHT_ANCHOR)
    if not (math.isfinite(leftY) and math.isfinite(rightY)):
        return None
    window = (nm >= leftX) & (nm <= rightX)
    x, y = nm[window], absorbance[window]
    chord = leftY + (rightY - leftY) * (x - leftX) / (rightX - leftX)
    residual = y - chord
    height = float(residual.max())
    if height <= 0.004:                      # no band above the chord -- nothing to measure
        return None
    area = float(numpy.trapz(numpy.clip(residual, 0.0, None), x))
    return (area / height, height, area)


def soretWidth(nm, absorbance):
    """The same equivalent width for the SORET, as the control: a 30 nm band should not broaden."""
    if nm[0] > 442.0:
        return None
    leftY = bandMean(nm, absorbance, 495.0, 505.0)
    window = (nm >= 442.0) & (nm <= 505.0)
    x, y = nm[window], absorbance[window]
    residual = y - leftY
    height = float(residual.max())
    if height <= 0.02:
        return None
    return float(numpy.trapz(numpy.clip(residual, 0.0, None), x)) / height


def describe(label, rows):
    if len(rows) < 2:
        print("  %-34s n=%d  (too few)" % (label, len(rows)))
        return
    for field, unit in (("W", "nm"), ("height", "A"), ("area", "A·nm"), ("soret", "nm")):
        values = [r[field] for r in rows if r[field] is not None]
        if len(values) < 2:
            continue
        a = numpy.array(values)
        print("  %-24s %-7s n=%2d   %7.3f +/- %6.3f %-5s [%7.3f .. %7.3f]"
              % (label if field == "W" else "", field, len(a), a.mean(), a.std(ddof=1), unit,
                 a.min(), a.max()))


def main():
    matched, isopropanol = [], []
    with tempfile.TemporaryDirectory() as scratch:
        def take(path, bucket, tag):
            workflow = archive.workflowOf(path, scratch)
            if workflow is None:
                return
            trace = archive.despikedTrace(workflow)
            if trace is None:
                return
            nm, absorbance = trace
            result = equivalentWidth(nm, absorbance)
            if result is None:
                return
            width, height, area = result
            bucket.append({"run": tag, "W": width, "height": height, "area": area,
                           "soret": soretWidth(nm, absorbance)})

        for _, relative in INDEX_MATCHED:
            take(os.path.join(archive.ARCHIVE, relative), matched, relative)

        for folder, subfolders, names in sorted(os.walk(archive.ARCHIVE)):
            subfolders[:] = [d for d in subfolders if d not in archive.EXCLUDED_DIRS]
            for name in sorted(names):
                if not name.endswith(".pdf"):
                    continue
                series = os.path.relpath(folder, archive.ARCHIVE)
                series = "(root)" if series == "." else series
                key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
                if archive.classOf({"series": series, "run": key}) not in ("green", "brown"):
                    continue
                take(os.path.join(folder, name), isopropanol,
                     "%s/%s" % (series, name) + ("  [diffuser IN]" if key in archive.DIFFUSER_IN else ""))

    print("EQUIVALENT WIDTH of the 624 nm band  =  area / height  above the 612-615 -> 627-630 chord")
    print("⭐ convolution CONSERVES AREA: blurring lowers the height and raises W, while veiling glare")
    print("   or less pigment scale height and area together and leave W alone.\n")
    describe("INDEX-MATCHED (spirit+sunflower)", matched)
    print()
    describe("ISOPROPANOL", isopropanol)
    print()
    a = numpy.array([r["W"] for r in matched])
    b = numpy.array([r["W"] for r in isopropanol])
    pooled = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                       / (len(a) + len(b) - 2))
    print("  ⇒ W:  index-matched %.3f nm  vs  isopropanol %.3f nm   |  d = %+.2f  %s"
          % (a.mean(), b.mean(), (a.mean() - b.mean()) / pooled,
             "OVERLAP" if not (a.min() > b.max() or b.min() > a.max()) else "SEPARATE"))
    print("     PREDICTED by resolution loss: isopropanol WIDER, i.e. d NEGATIVE.")
    print()
    print("  per index-matched fill:")
    for r in sorted(matched, key=lambda r: r["run"]):
        print("     %-34s W %6.3f nm  height %.4f  area %.4f" % (r["run"], r["W"], r["height"], r["area"]))


if __name__ == "__main__":
    main()
