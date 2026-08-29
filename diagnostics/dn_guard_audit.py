"""Where every archived run actually sits against the 16 DN floor and the 20-50 DN guard window.
(Edwin's question 2026-08-28: "the last measurement gave DN about 20?")

`SPEC_capture_quality.md` section 16.23.10f states, as built, that the 16 DN line is *off the plot*
because "it is never approached (minimum observed across 34 runs: 37.6 DN)". That sentence was written
on the ISOPROPANOL archive. This script re-runs the same check over every report on disk, and the
sunflower sessions falsify it: a large block of runs sits BELOW 16 DN in the Soret. Section 16.23.10j is
the write-up.

    guard      = encode(min(S) over 448-460 nm)  <- the shipped statistic, section 16.23.10f
    redGuard   = encode(min(S) over 622-627 nm)  <- `Rv`'s numerator band, which has no guard at all
    A(band)    = mean over the band of -log10(S/R), POINTWISE

⛔⛔ THE REPORT SPECTRA ARE LINEAR 0..255, NOT DN. `CapturePanel.__guardReading` takes the minimum on the
LINEAR spectrum and ENCODES IT ONCE -- `DN = 255 * (linear/255) ** (1/2.2)` -- because the thresholds live
in camera DN (section 16.23.10b, settled on `20260804A`). Reading the stored spectrum as DN understates
every number by a factor that grows as the value falls: 16 DN is linear 0.577, and `20260826EstererE`'s
Soret minimum of linear 0.885 is 19.4 DN, not 0.9. Both mistakes were made while writing this script.

⛔⛔ POINTWISE, NOT A RATIO OF BAND MEANS. On `20260826EstererE/001` the two disagree by 16 % at the
Soret (1.004 against the shipped 1.165) because the flank is steep and -log10 is convex; they agree to
three decimals everywhere else. Getting this wrong understates exactly the band this script is about.

⚠ WHAT THE NUMBERS ARE. The ACQUISITION `Reference` and `Sample` plots carry the capture legs in the
SAME units the shipped guard uses -- verified per run against `monitorRecord.answer.diagnostics`'s
`referenceSoret` / `referenceValley` / `referenceQ`, which this script recomputes and asserts. Runs whose
report predates those diagnostics are still scored; runs that carry them and DISAGREE are reported as a
unit failure, because that would mean the domain assumption above had silently changed.

⭐ THE DILUTION PROJECTION. `main()` also answers the question that prompted this: would a thinner fill
lift the red band off the floor? In the DN-floor-limited regime the noise on an absorbance goes as
sigma_A ~ 0.434 * sigma_DN / DN, so for a dose factor `f` the relative noise on `Rv`'s numerator scales
as (1/(f*num)) * (1/DN(f)) -- DN rises with dilution but the band shrinks faster. The projection is
ARITHMETIC on Beer-Lambert, not a measurement; it is printed with that label.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/dn_guard_audit.py
"""
import os
import sys
import tempfile

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive

GAMMA = 2.2                                             # captureDecode = "pow2.2", SpectralColorUtil

FLOOR = 16.0                                            # section 16.23.10b, the quantisation guard
WINDOW = (20.0, 50.0)                                   # section 16.23.10e, Edwin's provisional window
GUARD_BAND = (448.0, 460.0)                             # section 16.23.10f, the shipped anchor
RED_BAND = (622.0, 627.0)                               # SPEC_red_ratio_metric.md, `Rv`'s numerator
BANDS = [("Soret", 448.0, 460.0), ("valley", 500.0, 560.0),
         ("Q", 565.0, 580.0), ("red", 622.0, 627.0), ("far", 632.0, 636.0)]

# ⚠ `header.solvent` only exists on the newest reports (`SPEC_capture_quality.md` section 4A.5 item 1 is
# the standing complaint that it is missing). The era is therefore derived from the SESSION DATE, which is
# in every folder name, and cross-checked against the header wherever the header exists -- `main()` prints
# any disagreement rather than silently preferring one.
SPIRIT_SESSIONS = "20260821"                            # peak_ratio_archive.SPIRIT
SUNFLOWER_FROM = "20260822"                             # section 16.12.7g, the solvent migration

# ⛔ TWO SESSION FOLDERS CARRY A MISTYPED YEAR, and a date-derived era silently files them as sunflower
# because "2027..." and "2028..." sort after the migration date. `20270729` is the mechanical rebuild of
# 2026-07-29 (`all_metrics_archive.REBUILD`); `20280819` is 2026-08-19 (`SPEC_settled_measurement.md`
# section 32, the Billa Clever triad). Both are isopropanol, and together they are 16 runs -- enough to
# move every count in this script's per-era table.
TYPO_SESSIONS = {"20270729": "20260729", "20280819": "20260819"}


def eraOf(series):
    date = TYPO_SESSIONS.get(series[:8], series[:8])
    if not date.isdigit():
        return "(undated)"
    if date == SPIRIT_SESSIONS:
        return "WHITE_SPIRIT"
    return "SUNFLOWER_OIL" if date >= SUNFLOWER_FROM else "ISOPROPANOL"


def acquisitionLeg(workflow, label):
    """The `Reference` or `Sample` capture leg, as (wavelengths, DN). None if the report predates it."""
    for phase in workflow.get("phases", []):
        if phase.get("type") != "ACQUISITION":
            continue
        for step in phase.get("steps", []):
            if step.get("label") != label:
                continue
            for item in step.get("items", []):
                if item.get("type") != "plot" or not item.get("spectrum"):
                    continue
                spectrum = item["spectrum"]
                wavelengths = numpy.array([float(k) for k in spectrum])
                values = numpy.array(list(spectrum.values()), dtype=float)
                order = numpy.argsort(wavelengths)
                return wavelengths[order], values[order]
    return None


def encodeDn(linear):
    """LINEAR 0..255 -> camera DN. `SpectralColorUtil.encodeGammaFraction`, reproduced so this script has
    no Qt/app import; `main()` asserts the two agree on the 16 DN landmark."""
    return 255.0 * (max(0.0, float(linear)) / 255.0) ** (1.0 / GAMMA)


def bandArgMin(wavelengths, values, low, high):
    """(nanometer, LINEAR value) of the darkest bin in the window -- the shipped guard's own argmin, kept
    so the dilution projection can be evaluated at the wavelength that actually decides the verdict."""
    mask = (wavelengths >= low) & (wavelengths <= high)
    if not mask.any():
        return float("nan"), float("nan")
    index = values[mask].argmin()
    return float(wavelengths[mask][index]), float(values[mask][index])


def bandMean(wavelengths, values, low, high):
    mask = (wavelengths >= low) & (wavelengths <= high)
    return float(values[mask].mean()) if mask.any() else float("nan")


def absorbance(referenceWavelengths, reference, sampleWavelengths, sample):
    """-log10(S/R) POINTWISE, on the reference grid. See the docstring's second warning."""
    resampled = numpy.interp(referenceWavelengths, sampleWavelengths, sample)
    ratio = numpy.clip(resampled, 1e-6, None) / numpy.clip(reference, 1e-6, None)
    return referenceWavelengths, -numpy.log10(numpy.clip(ratio, 1e-9, None))


def rowFor(workflow):
    legs = acquisitionLeg(workflow, "Reference"), acquisitionLeg(workflow, "Sample")
    if legs[0] is None or legs[1] is None:
        return None
    (referenceWavelengths, reference), (sampleWavelengths, sample) = legs
    absorbanceWavelengths, values = absorbance(referenceWavelengths, reference,
                                               sampleWavelengths, sample)
    guardNm, guardLinear = bandArgMin(sampleWavelengths, sample, *GUARD_BAND)
    redNm, redLinear = bandArgMin(sampleWavelengths, sample, *RED_BAND)
    row = {"guard": encodeDn(guardLinear), "guardNm": guardNm,
           "redGuard": encodeDn(redLinear), "redNm": redNm,
           "solvent": (workflow.get("header") or {}).get("solvent") or "",
           "refPeak": encodeDn(reference.max()),
           "refPeakNm": float(referenceWavelengths[reference.argmax()])}
    for label, low, high in BANDS:
        row["dn_" + label] = encodeDn(bandMean(sampleWavelengths, sample, low, high))
        row["ref_" + label] = bandMean(referenceWavelengths, reference, low, high)
        row["A_" + label] = bandMean(absorbanceWavelengths, values, low, high)
    row["guardRefLinear"] = float(numpy.interp(guardNm, referenceWavelengths, reference))
    row["redRefLinear"] = float(numpy.interp(redNm, referenceWavelengths, reference))
    row["guardA"] = float(numpy.interp(guardNm, absorbanceWavelengths, values))
    row["redA"] = float(numpy.interp(redNm, absorbanceWavelengths, values))
    denominator = row["A_Q"] - row["A_valley"]
    row["Rv"] = 100.0 * (row["A_red"] - row["A_valley"]) / denominator if denominator else float("nan")
    row["Qpct"] = 100.0 * (row["A_Q"] - row["A_valley"]) / row["A_Soret"] if row["A_Soret"] else float("nan")
    row["check"] = domainCheck(workflow, row)
    return row


def domainCheck(workflow, row):
    """⭐ The unit test that runs on every row: do the recomputed reference band means match the ones
    the settling monitor latched? If they ever stop matching, the ACQUISITION legs are no longer the
    domain the shipped guard works in and every number here is wrong."""
    diagnostics = ((workflow.get("monitorRecord") or {}).get("answer") or {}).get("diagnostics") or {}
    pairs = [("referenceSoret", "ref_Soret"), ("referenceValley", "ref_valley"),
             ("referenceQ", "ref_Q")]
    latched = [(key, diagnostics[key], row[mine]) for key, mine in pairs if key in diagnostics]
    if not latched:
        return "no-monitor"
    worst = max(abs(a - b) for _, a, b in latched)
    return "ok" if worst < 0.01 else "MISMATCH %.3f" % worst


def collect():
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for folder, name in archive.walkReports():
            series = os.path.relpath(folder, archive.ARCHIVE)
            series = "(root)" if series == "." else series
            workflow = archive.workflowOf(os.path.join(folder, name), scratch)
            if workflow is None:
                continue
            row = rowFor(workflow)
            if row is None:
                continue
            row["run"] = "%s/%s" % (series, name[:-4])
            row["series"] = series
            row["era"] = eraOf(series)
            rows.append(row)
    return rows


def dilutionProjection(row, factors=(1.0, 0.8, 0.64, 0.5)):
    """ARITHMETIC, not a measurement -- Beer-Lambert on this run's own bands, evaluated at the two
    wavelengths that decide the two verdicts (the guard's argmin, and the red band's argmin)."""
    lines = []
    for factor in factors:
        numerator = (row["A_red"] - row["A_valley"]) * factor
        guardDn = encodeDn(row["guardRefLinear"] * 10.0 ** -(row["guardA"] * factor))
        redDn = encodeDn(row["redRefLinear"] * 10.0 ** -(row["redA"] * factor))
        # sigma_A ~ 0.434 * sigma_DN / DN for one DN of quantisation, taken relative to the band depth
        noise = (0.434 / redDn) / numerator if numerator else float("nan")
        lines.append((factor, row["A_Soret"] * factor, guardDn, redDn, numerator, noise))
    baseline = lines[0][-1]
    return [line + (line[-1] / baseline,) for line in lines]


def main():
    # ⭐ The landmark that pins the units: section 16.23.10b's "the 16 DN guard line lands at 0.58 of 255".
    assert abs(encodeDn(0.577) - 16.0) < 0.05, encodeDn(0.577)
    rows = collect()
    print("reports with both capture legs : %d" % len(rows))
    print("units check: linear 0.577 encodes to %.1f DN  (section 16.23.10b's landmark)" % encodeDn(0.577))
    bad = [r for r in rows if r["check"].startswith("MISMATCH")]
    print("domain check against monitorRecord : %d ok, %d without a monitor, %d MISMATCH"
          % (sum(1 for r in rows if r["check"] == "ok"),
             sum(1 for r in rows if r["check"] == "no-monitor"), len(bad)))
    for row in bad:
        print("  ⛔ %s %s" % (row["run"], row["check"]))

    under = [r for r in rows if r["guard"] < FLOOR]
    print("\n⛔ BELOW THE %.0f DN FLOOR in %s-%s nm : %d of %d runs"
          % (FLOOR, GUARD_BAND[0], GUARD_BAND[1], len(under), len(rows)))
    disagree = [r for r in rows if r["solvent"] and r["solvent"] != r["era"]]
    print("header `solvent` present on %d of %d reports; %d disagree with the date-derived era"
          % (sum(1 for r in rows if r["solvent"]), len(rows), len(disagree)))
    for row in disagree:
        print("  ⚠ %s header=%s era=%s" % (row["run"], row["solvent"], row["era"]))

    bySolvent = {}
    for row in rows:
        bucket = bySolvent.setdefault(row["era"], [])
        bucket.append(row)
    print("\n%-22s %5s %6s %6s %6s %7s %7s" % ("era", "n", "<16", "in win", ">50", "medGuard", "medRed"))
    for solvent, bucket in sorted(bySolvent.items()):
        guards = numpy.array([r["guard"] for r in bucket])
        reds = numpy.array([r["redGuard"] for r in bucket])
        print("%-22s %5d %6d %6d %6d %7.1f %7.1f"
              % (solvent, len(bucket), (guards < FLOOR).sum(),
                 ((guards >= WINDOW[0]) & (guards <= WINDOW[1])).sum(), (guards > WINDOW[1]).sum(),
                 numpy.median(guards), numpy.median(reds)))

    sunflower = sorted((r for r in rows if r["era"] == "SUNFLOWER_OIL"), key=lambda r: r["run"])
    if sunflower:
        print("\nTHE SUNFLOWER SESSIONS, run by run")
        print("%-30s %7s %7s %8s %7s %7s %8s" % ("run", "guard", "red", "A_Soret", "Rv", "Q%", "refPeak"))
        for row in sunflower:
            flag = "  <-- under %.0f" % FLOOR if row["guard"] < FLOOR else ""
            print("%-30s %7.1f %7.1f %8.3f %7.1f %7.2f %8.1f%s"
                  % (row["run"], row["guard"], row["redGuard"], row["A_Soret"],
                     row["Rv"], row["Qpct"], row["refPeak"], flag))

    # ⭐ DISCOVERED, not enumerated: every sunflower run that misses the window's LOW edge gets projected,
    # so a new session adds itself to this block without the script being edited.
    missing = [r for r in sunflower if r["guard"] < WINDOW[0]]
    print("\n%d sunflower runs read below the window's low edge (%.0f DN) => guard verdict "
          "`too-concentrated`" % (len(missing), WINDOW[0]))
    for row in missing:
        print("\nTHE DILUTION PROJECTION on %s   (guard %.1f DN at %.1f nm, red %.1f DN at %.1f nm)"
              % (row["run"], row["guard"], row["guardNm"], row["redGuard"], row["redNm"]))
        print("⚠ ARITHMETIC on Beer-Lambert at those two wavelengths. Not a measurement.")
        print("%6s %9s %9s %8s %10s %12s"
              % ("dose", "A_Soret", "guardDN", "redDN", "Rv numer", "rel. noise"))
        for factor, soret, guardDn, redDn, numerator, _, relative in dilutionProjection(row):
            print("%6.2f %9.3f %9.1f %8.1f %10.4f %11.2fx"
                  % (factor, soret, guardDn, redDn, numerator, relative))

    peaks = numpy.array([r["refPeak"] for r in sunflower])
    print("\n⛔ THE EXPOSURE HEADROOM. Reference peak across the sunflower sessions: %.1f - %.1f DN "
          "(median %.1f), against the 255 clip and the AE target of 245."
          % (peaks.min(), peaks.max(), numpy.median(peaks)))
    print("   A x1.15 exposure step would put %d of %d references at or past 255."
          % (int((peaks * 1.15 >= 255).sum()), len(peaks)))


if __name__ == "__main__":
    main()
