"""λ_d and excitation purity p_e over every labelled report on disk. (Edwin's request, 2026-08-24)

The claim under test comes from `DOC_colour_geometry.md` §2.1: on seven sunflower-solvent fills of two
oils, the DOMINANT WAVELENGTH separated them cleanly (a 2 nm gap, Cohen's d = 2.93) where EXCITATION
PURITY did not (ranges touching at 0.027 points). Seven runs of one oil pair over three days is not
evidence, and §1c of `SPEC_color_retrieval.md` has burned exactly this class of claim once already.
So: re-run it across the whole isopropanol archive before anything gets built on it.

  λ_d   where the ray from D65 white through the absorbed chromaticity meets the spectrum locus
  p_e   how far along that ray the sample sits, as a percent (r_W / R_W)

Both are computed through the SHIPPED `EvaluationColorUtil`, on each report's own de-spiked absorbance
(`peak_ratio_archive.despikedTrace` — the only trace the old and new reports have in common). Labelling,
exclusions and the diffuser A/B split are `peak_ratio_archive`'s, unchanged, so this scores exactly the
corpus `SPEC_metric_research.md` §12 scores.

⚠ TWO CONFOUNDS THIS SCRIPT EXISTS TO EXPOSE, not to hide:

  1  λ_d is set by the SORET, the sharpest feature in the spectrum, and the archive has MIXED BLUE-END
     COVERAGE (the §16.10.1 clamp starts at 440 nm; the 2026-08 sunflower runs start at 406-420). If λ_d
     tracks `wlo` the separation is an instrument artefact. The `--by-span` table is that check.
  2  The RELATIVE ceiling (2 x the spectrum's own 95th percentile) clips the Soret when it fires. On the
     sunflower fills it is dormant (5.24 against a 4.15 peak). On a concentrated fill it is not, and it
     would move λ_d more than any other quantity in the chip set. `ceilFired` counts it.

⭐ ALSO CHECKED (Edwin, 2026-08-24): the COMPLEMENT's excitation purity. `Absorbed-complement` is the
absorbed chromaticity reflected through white, `(2x_W - x, 2y_W - y)`. Nothing constrains the reflected
point to stay inside the horseshoe, and on run `20260822Lugitsch/002` it does not: p_e = 115.3 %, i.e.
BEYOND the spectrum locus, a stimulus no human eye can receive. `compImaginary` counts how often that
happens across the archive. The absorbed chromaticity's own xy is stored too, so a later question of
this kind needs no re-extraction.

⭐ AND (Edwin, 2026-08-24): §4's own headline claim. `SPEC_capability_proof.md` option (b) chose the
white-point complement over the old `+180°` HSL hue flip because it lands "~4° from the true perceived
hue, versus ~34°" — measured on FOUR runs (K/L/M/N). Since the complement is at or past the spectrum
locus on 70 % of the archive (see above), that number needs re-testing where it is worst. The reference
"true perceived hue" here is the TRANSMITTED chromaticity, derived as T = 10^(-A) from the same trace
(exact to 6e-17, verified) so both sides share one wavelength span — which is what isolates the
complement question from a coverage difference. Three angles are reported:

    dThetaComp   theta_W(complement)      vs theta_W(transmitted)   gamut-free, the honest comparison
    dHueComp     H_hsl(complement)        vs H_hsl(transmitted)     as the shipped chips report it
    dHueFlip     H_hsl(absorbed) + 180    vs H_hsl(transmitted)     the rejected +180 baseline

Also reported: the same two quantities under the D5 padding (un-measured wavelengths treated as A = 0
instead of `align`'s constant hold), because D5 moves λ_d by ~12 nm and any conclusion has to survive it.

HOW TO RUN
----------
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base" \
        ./venv/bin/python diagnostics/dominant_wavelength_archive.py
"""
import math
import os
import sys
import tempfile

import numpy
from colour import (MSDS_CMFS, SDS_ILLUMINANTS, SpectralDistribution, XYZ_to_xy,
                    dominant_wavelength, excitation_purity, sd_to_XYZ)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil

WHITE = [0.31270, 0.32900]
CMFS = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
ILLUMINANT = SDS_ILLUMINANTS["D65"]
util = EvaluationColorUtil()
sanitize = util._EvaluationColorUtil__sanitize
cieXy = util._EvaluationColorUtil__cieXy
OUT_CSV = os.path.join(archive.ARCHIVE, "dominant_wavelength_archive.csv")


def legacyAlignXy(clean):
    """The PRE-P1 chromaticity: `SpectralDistribution(...).align(cmfs.shape)`, whose constant hold
    extrapolates the boundary sample across the un-measured red. Reproduced explicitly here because
    2026-08-24's P1 removed it from the shipped path — the comparison below is the record of what it
    cost, and re-running this script must keep reproducing it rather than silently collapsing to one
    column. DOC_colour_geometry.md §9.2."""
    distribution = SpectralDistribution(dict(clean)).align(CMFS.shape)
    xyz = sd_to_XYZ(distribution, CMFS, ILLUMINANT, method="Integration") / 100.0
    xy = XYZ_to_xy(xyz)
    return float(xy[0]), float(xy[1])


def paddedXy(clean):
    """Chromaticity with the un-measured range padded with A = 0 — as SHIPPED since P1."""
    nanometers = sorted(clean)
    values = [clean[n] for n in nanometers]
    dense = {}
    for wavelength in CMFS.wavelengths:
        wavelength = float(wavelength)
        dense[wavelength] = (0.0 if (wavelength < nanometers[0] or wavelength > nanometers[-1])
                             else float(numpy.interp(wavelength, nanometers, values)))
    xyz = sd_to_XYZ(SpectralDistribution(dense).align(CMFS.shape), CMFS, ILLUMINANT,
                    method="Integration") / 100.0
    xy = XYZ_to_xy(xyz)
    return float(xy[0]), float(xy[1])


def complementPurity(xy):
    """Excitation purity of the WHITE-POINT COMPLEMENT. > 100 % means the reflected point lies outside
    the spectrum locus — an imaginary colour, which `Absorbed-complement` would then be reporting
    numbers for. `colour` returns the ratio unclamped, which is exactly what makes the test possible."""
    x, y = xy
    return float(excitation_purity([2.0 * WHITE[0] - x, 2.0 * WHITE[1] - y], WHITE)) * 100.0


def transmittedXy(spectrum):
    """The chromaticity of T = 10^(-A), on the trace's own grid. No ceiling — the shipped `Perceived`
    chip reads the measured transmission unclamped, and T is bounded by construction anyway."""
    clean = sanitize(spectrum, None)
    if clean is None:
        return None
    transmittance = Spectrum()
    transmittance.valuesByNanometers = {n: min(1.0, 10.0 ** (-v)) for n, v in clean.items()}
    return util.spectrumToChromaticity(transmittance, source=util.TRANSMITTANCE)


def angleFromWhite(xy):
    return math.degrees(math.atan2(xy[1] - WHITE[1], xy[0] - WHITE[0])) % 360.0


def hslHue(xy):
    return util._EvaluationColorUtil__hslFromXy(xy[0], xy[1])[0]


def angleGap(first, second):
    difference = abs(first - second) % 360.0
    return min(difference, 360.0 - difference)


def polar(xy):
    return (float(dominant_wavelength(list(xy), WHITE)[0]),
            float(excitation_purity(list(xy), WHITE)) * 100.0)


def collect():
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for folder, _, names in sorted(os.walk(archive.ARCHIVE)):
            for name in sorted(names):
                if not name.endswith(".pdf"):
                    continue
                series = os.path.relpath(folder, archive.ARCHIVE)
                series = "(root)" if series == "." else series
                key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
                workflow = archive.workflowOf(os.path.join(folder, name), scratch)
                if workflow is None:
                    continue
                trace = archive.despikedTrace(workflow)
                if trace is None:
                    continue
                wavelengths, absorbance = trace
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(w): float(a)
                                               for w, a in zip(wavelengths, absorbance)}
                clean = sanitize(spectrum, util.RELATIVE)
                if clean is None:
                    continue
                raw = {float(w): max(0.0, float(a)) for w, a in zip(wavelengths, absorbance)}
                ceiling = util._EvaluationColorUtil__resolveCeiling(raw, util.RELATIVE)
                heldXy, padXy = legacyAlignXy(clean), cieXy(clean)
                heldWl, heldPurity = polar(heldXy)
                padWl, padPurity = polar(padXy)
                compHeld = complementPurity(heldXy)
                compPad = complementPurity(padXy)
                complementXy = (2.0 * WHITE[0] - padXy[0], 2.0 * WHITE[1] - padXy[1])
                perceivedXy = transmittedXy(spectrum)
                if perceivedXy is None:
                    continue
                dThetaComp = angleGap(angleFromWhite(complementXy), angleFromWhite(perceivedXy))
                dHueComp = angleGap(hslHue(complementXy), hslHue(perceivedXy))
                dHueFlip = angleGap(hslHue(heldXy) + 180.0, hslHue(perceivedXy))
                rows.append({"run": key, "series": series,
                             "wlo": float(wavelengths[0]), "whi": float(wavelengths[-1]),
                             "peakA": max(raw.values()), "ceiling": ceiling,
                             "ceilFired": max(raw.values()) > (ceiling or 1e9),
                             "xHeld": heldXy[0], "yHeld": heldXy[1],
                             "xPad": padXy[0], "yPad": padXy[1],
                             "wlHeld": heldWl, "peHeld": heldPurity,
                             "wlPad": padWl, "pePad": padPurity,
                             "compHeld": compHeld, "compPad": compPad,
                             "compImaginary": compPad > 100.0,
                             "xPerc": perceivedXy[0], "yPerc": perceivedXy[1],
                             "dThetaComp": dThetaComp, "dHueComp": dHueComp,
                             "dHueFlip": dHueFlip})
    return rows


def describe(label, values, unit=""):
    array = numpy.array(values, dtype=float)
    if len(array) < 2:
        print("  %-26s n=%3d   (too few)" % (label, len(array)))
        return array
    print("  %-26s n=%3d   %8.2f +/- %5.2f %-3s [%7.2f .. %7.2f]"
          % (label, len(array), array.mean(), array.std(ddof=1), unit, array.min(), array.max()))
    return array


def separation(green, brown):
    green, brown = numpy.array(green, float), numpy.array(brown, float)
    pooled = math.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                       / (len(green) + len(brown) - 2))
    overlaps = not (green.min() > brown.max() or brown.min() > green.max())
    gap = 0.0 if overlaps else (green.min() - brown.max() if green.min() > brown.max()
                                else brown.min() - green.max())
    return (green.mean() - brown.mean()) / pooled, overlaps, gap


def main():
    rows = collect()
    with open(OUT_CSV, "w") as handle:
        keys = list(rows[0])
        handle.write(",".join(keys) + "\n")
        for row in rows:
            handle.write(",".join(str(row[k]) for k in keys) + "\n")
    print("%d reports scored -> %s\n" % (len(rows), OUT_CSV))

    classes = {}
    for row in rows:
        label = archive.classOf(row)
        if label in ("green", "brown"):
            classes.setdefault(label, []).append(row)

    for field, unit, name in (("wlHeld", "nm", "lambda_d   (LEGACY align-hold, pre-P1)"),
                              ("peHeld", "%", "p_e        (LEGACY align-hold, pre-P1)"),
                              ("wlPad", "nm", "lambda_d   (SHIPPED since P1)"),
                              ("pePad", "%", "p_e        (SHIPPED since P1)")):
        print(name)
        green = describe("green", [r[field] for r in classes.get("green", [])], unit)
        brown = describe("brown", [r[field] for r in classes.get("brown", [])], unit)
        if len(green) > 1 and len(brown) > 1:
            d, overlaps, gap = separation(green, brown)
            print("  %-26s d = %5.2f   %s%s" % ("->", d, "OVERLAP" if overlaps else "SEPARATE",
                                                "" if overlaps else "  gap %.2f %s" % (gap, unit)))
        print()

    print("CONFOUND 1 - does lambda_d track the blue edge of the measurement?  (on the SHIPPED path)")
    spans = {}
    for row in rows:
        if archive.classOf(row) in ("green", "brown"):
            spans.setdefault(round(row["wlo"]), []).append(row["wlPad"])
    for wlo in sorted(spans):
        describe("wlo = %d nm" % wlo, spans[wlo], "nm")
    scored = [r for r in rows if archive.classOf(r) in ("green", "brown")]
    if len({round(r["wlo"]) for r in scored}) > 1:
        print("  correlation lambda_d vs wlo: r = %.3f"
              % numpy.corrcoef([r["wlo"] for r in scored], [r["wlPad"] for r in scored])[0, 1])
    print()
    fired = [r for r in scored if r["ceilFired"]]
    print("CONFOUND 2 - the relative ceiling fired on %d of %d scored runs%s"
          % (len(fired), len(scored),
             ("  e.g. " + ", ".join(r["run"] for r in fired[:4])) if fired else ""))
    print()

    print("THE COMPLEMENT CHECK - is `Absorbed-complement` an imaginary colour?")
    for field, name in (("compHeld", "LEGACY align-hold"), ("compPad", "SHIPPED since P1")):
        imaginary = [r for r in scored if r[field] > 100.0]
        describe("complement p_e, " + name, [r[field] for r in scored], "%")
        print("  %-26s OUTSIDE THE LOCUS on %d of %d  (%.0f %%)%s"
              % ("->", len(imaginary), len(scored), 100.0 * len(imaginary) / len(scored),
                 "   worst %.1f %%" % max(r[field] for r in scored)))
    byClass = {}
    for row in scored:
        byClass.setdefault(archive.classOf(row), []).append(row)
    for label in sorted(byClass):
        subset = byClass[label]
        print("  %-26s %s: %d of %d imaginary"
              % ("", label, sum(1 for r in subset if r["compPad"] > 100.0), len(subset)))
    print()

    print("THE 4-DEGREE CLAIM - complement vs the transmitted colour it stands in for")
    describe("d theta_W  complement", [r["dThetaComp"] for r in scored], "deg")
    describe("d H_hsl    complement", [r["dHueComp"] for r in scored], "deg")
    describe("d H_hsl    +180 flip", [r["dHueFlip"] for r in scored], "deg")
    real = [r for r in scored if not r["compImaginary"]]
    imaginary = [r for r in scored if r["compImaginary"]]
    for name, subset in (("where the complement is REAL", real),
                         ("where it is IMAGINARY", imaginary)):
        if len(subset) > 1:
            describe("  " + name, [r["dThetaComp"] for r in subset], "deg")


if __name__ == "__main__":
    main()
