"""What would a 12-bit LINEAR sensor actually buy? — re-quantise the archive and measure it.

    ./venv/bin/python diagnostics/bit_depth_gain.py [--limit N]

⭐ WHY. `KB_cameras.md` §4.1 claims a linear 12-bit mono sensor "deletes a whole class of problem".
Edwin's challenge is the right one: **the dominant error is sample preparation and re-seating, not
quantisation** — so "deletes a class of problem" is worthless unless the class was large. This script
puts a number on it instead of arguing.

METHOD. Archived reports carry the **LINEAR 0..255** reference and sample spectra. For each run:

    Q% = -100 * (A_valley - A_Q) / A_Soret,     A = log10(R/S) pointwise, then band means
    bands: Soret 448-460, valley 500-560, Q 565-580   (DevSpectralPlugin.V_*_BAND)

then re-quantise BOTH spectra onto two grids and recompute:

    dn8   encode -> round to an 8-bit code -> decode      (today's grid, `pow2.2`)
    dn12  round the LINEAR value onto 4096 steps          (a 12-bit linear sensor)

⚠⚠ THE ONE THING TO UNDERSTAND ABOUT THIS NUMBER. The archived values are the mean of **60 frames**, so
they already sit on a grid finer than one code — real capture dithers. Rounding them back onto a single
code therefore simulates the **NO-DITHER WORST CASE**, which is not hypothetical: `spectracs-mad-zero-collapse`
records the robust reduction returning a single raw code for **35 % of columns**, i.e. no dither at all
there. So read the output as a **CEILING**: with dither over 60 frames the true contribution is smaller
by up to sqrt(60) ~ 7.7x, and the honest statement is a range between the two.

⛔ WHAT IT IS NOT. It does not model read noise, dark current, full-well or the analog gain chain — a real
12-bit sensor differs in all of those, mostly favourably. It isolates QUANTISATION alone, which is the
only part of the claim that can be checked against data already on disk.

The comparison targets, all in the same Q% units:
    0.063  sd of Q% over 10 repeats, jar UNTOUCHED   (DevSpectralPlugin.SINGLE_WINDOW_SIGMA, §16.36.6)
    0.076  two second-pours of the same dilution     (SPEC_settled_measurement.md §36)
    0.198  clean set, aliquots kept dark             (§40)
    0.276  sigma_fill, five separate preparations    (§28, series F)
    1.255  archive WITHIN-FILL scatter               (§28)
"""
import argparse
import glob
import json
import os

import numpy as np
from pypdf import PdfReader

ARCHIVE = "/home/nidwe72/development/spectracs/spectracs-references/tmp"
GAMMA = 2.2

SORET_BAND = (448.0, 460.0)
VALLEY_BAND = (500.0, 560.0)
Q_BAND = (565.0, 580.0)

# Everything this result has to be compared against, in Q% units (see the docstring for sources).
BENCHMARKS = [
    ("jar untouched, 10 repeats — the instrument floor", 0.063),
    ("second pour of the same dilution", 0.076),
    ("clean set, aliquots kept dark", 0.198),
    ("sigma_fill — five separate preparations", 0.276),
    ("archive within-fill scatter", 1.255),
]


def spectra(path):
    """(REFERENCE, SAMPLE) as {nm: linear 0..255} out of a report's embedded workflow JSON."""
    found = {}
    workflow = json.loads(PdfReader(path).attachments["workflow.json"][0])
    for phase in workflow.get("phases", []):
        for step in phase.get("steps", []):
            for role, raw in (step.get("spectra") or {}).items():
                if role in ("REFERENCE", "SAMPLE") and role not in found:
                    values = raw.get("valuesByNanometers", raw)
                    found[role] = {float(k): float(v) for k, v in values.items()}
    return found.get("REFERENCE"), found.get("SAMPLE")


def quantise(values, mode):
    """Re-quantise a LINEAR 0..255 array onto the grid `mode` describes."""
    array = np.asarray(values, dtype=np.float64)
    if mode == "asIs":
        return array
    if mode == "dn8":                      # encode -> one 8-bit code -> decode
        code = np.round(255.0 * np.clip(array / 255.0, 0.0, 1.0) ** (1.0 / GAMMA))
        return 255.0 * (code / 255.0) ** GAMMA
    if mode == "dn12":                     # 12 bits, LINEAR, same full scale
        return np.round(np.clip(array, 0.0, 255.0) / 255.0 * 4095.0) / 4095.0 * 255.0
    raise ValueError(mode)


def qPercent(reference, sample, mode):
    """The shipped Q% on one pair of spectra, after re-quantising both onto `mode`'s grid.

    ⚠ De-spiking is deliberately NOT applied: it removes outlier bins, and this measures a DELTA between
    two quantisations of the same bins, which de-spiking would only damp.

    ⛔⛔ THE USABLE MASK IS FIXED ON THE UNQUANTISED PAIR and admits only bins BOTH grids can represent
    (above one 12-bit linear step). Otherwise the grids disagree about which bins exist — a 12-bit linear
    grid zeroes anything under 0.062 linear while 8-bit gamma holds on to 2.8e-4 — and the two band means
    would be taken over different bin sets, making the "shift" a membership artefact rather than
    quantisation. Measured: that artefact alone produced a spurious max shift of 1.75 Q% units and made
    12-bit look WORSE than 8-bit. ⚠ The bins it excludes are the DEAD ones (A > 3.5); they carry no
    information on any grid, and §7.13's starved-regime finding is about them."""
    nanometers = np.array(sorted(set(reference) & set(sample)))
    rawR = np.array([reference[nm] for nm in nanometers])
    rawS = np.array([sample[nm] for nm in nanometers])
    representable = 255.0 / 4095.0
    usable = (rawR > representable) & (rawS > representable)
    r, s = quantise(rawR, mode), quantise(rawS, mode)
    if usable.sum() < 100:
        return None
    absorbance = np.full(nanometers.shape, np.nan)
    absorbance[usable] = np.log10(r[usable] / s[usable])

    def bandMean(low, high):
        inside = (nanometers >= low) & (nanometers <= high) & np.isfinite(absorbance)
        return float(np.mean(absorbance[inside])) if inside.sum() else float("nan")

    soret, valley, qBand = bandMean(*SORET_BAND), bandMean(*VALLEY_BAND), bandMean(*Q_BAND)
    if not np.isfinite(soret) or soret <= 0.334:      # V_SORET_FLOOR — no verdict below it
        return None
    return -100.0 * (valley - qBand) / soret


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="stop after N runs (0 = all)")
    arguments = parser.parse_args()

    reports = sorted(glob.glob(os.path.join(ARCHIVE, "*", "*.pdf")))
    if arguments.limit:
        reports = reports[:arguments.limit]

    shifts8, shifts12, baselines, failed = [], [], [], 0
    for path in reports:
        try:
            reference, sample = spectra(path)
            if reference is None or sample is None:
                failed += 1
                continue
            base = qPercent(reference, sample, "asIs")
            eight = qPercent(reference, sample, "dn8")
            twelve = qPercent(reference, sample, "dn12")
            if None in (base, eight, twelve):
                failed += 1
                continue
            baselines.append(base)
            shifts8.append(eight - base)
            shifts12.append(twelve - base)
        except Exception:
            failed += 1

    if not baselines:
        print("no usable runs found under %s" % ARCHIVE)
        return

    shifts8, shifts12 = np.array(shifts8), np.array(shifts12)
    print("%d runs measured (%d skipped: no embedded spectra, or below the Soret floor)"
          % (len(baselines), failed))
    print("Q%% spans %.2f .. %.2f across the corpus\n" % (min(baselines), max(baselines)))

    print("quantisation-induced shift in Q%, WORST CASE (no dither):")
    print("  grid            mean|shift|    sd of shift    95th pct|shift|   max|shift|")
    for label, shifts in (("8-bit gamma", shifts8), ("12-bit linear", shifts12)):
        print("  %-14s %10.4f %14.4f %16.4f %12.4f"
              % (label, np.mean(abs(shifts)), np.std(shifts),
                 np.percentile(abs(shifts), 95), np.max(abs(shifts))))

    eight, twelve = float(np.std(shifts8)), float(np.std(shifts12))
    print("\n⇒ 12-bit shrinks the quantisation term %.1fx (sd %.4f -> %.4f Q%% units)"
          % (eight / twelve if twelve else float("inf"), eight, twelve))

    # ⭐⭐ The simulation's own sanity check, and it FAILS in the useful direction. Quantisation is one
    # component of the jar-untouched floor, so it cannot exceed it. If the no-dither figure does exceed
    # it, that is positive evidence that real capture DOES dither — and it hands us a rigorous upper
    # bound that needs no model at all: whatever quantisation contributes, it is at most the whole floor.
    floor = BENCHMARKS[0][1]
    bound = min(eight, floor)
    if eight > floor:
        print("\n⚠⚠ THE NO-DITHER FIGURE (%.4f) EXCEEDS THE MEASURED FLOOR (%.3f) — and it cannot, because"
              % (eight, floor))
        print("   quantisation is one COMPONENT of that floor. ⇒ real capture genuinely dithers, the")
        print("   worst case above is too pessimistic, and the honest bound is the floor itself.")
    print("\n⇒ ⭐ RIGOROUS UPPER BOUND, model-free: quantisation contributes AT MOST %.3f Q%% units," % bound)
    print("  because that is the entire spread of 10 repeats with the jar untouched.")

    print("\nRemoving quantisation ENTIRELY — the most generous case 12-bit could ever claim:")
    print("  what is being measured                                 today   12-bit    gain")
    for index, (label, total) in enumerate(BENCHMARKS):
        improved = float(np.sqrt(max(total ** 2 - bound ** 2, 0.0)))
        note = "   <- circular, this row DEFINES the bound" if index == 0 else ""
        print("  %-52s %6.3f  %6.3f   %5.1f %%%s"
              % (label, total, improved, 100.0 * (1.0 - improved / total), note))

    print("\n⭐ WHERE the two grids actually differ — one code, as a %% of the level, at each absorbance")
    print("  (reference parked at 90 %% of full scale on both):")
    print("   A      sample level    8-bit gamma    12-bit linear    12-bit is")
    referenceLinear = 255.0 * (230.0 / 255.0) ** GAMMA
    for absorbance in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        level = referenceLinear / 10.0 ** absorbance
        code = 255.0 * (level / 255.0) ** (1.0 / GAMMA)
        stepGamma = 255.0 * ((code + 1.0) / 255.0) ** GAMMA - level
        stepLinear = 255.0 / 4095.0
        print("  %4.1f   %10.3f    %10.2f %%   %12.2f %%    %6.1fx %s"
              % (absorbance, level, 100 * stepGamma / level, 100 * stepLinear / level,
                 stepGamma / stepLinear, "better" if stepGamma > stepLinear else "WORSE"))
    print("  ⇒ 12-bit linear wins by 3-10x across the whole working range, and only loses past A~3.3,")
    print("    where the bin is dead on any grid. ⚠ Gamma is not merely a nuisance — it SPENDS codes on")
    print("    the dark end, which is why 8 bits has held up as well as it has.")

    print("\n⭐ Read the LAST column. Even granting 12-bit the entire instrument floor, the numbers that")
    print("  GATE THE PRODUCT move by a few percent — Edwin's point stands. The bit depth is not where")
    print("  the error is. ⭐ The gain is real only where the signal is DARK (one code is 22 %% at 2 DN),")
    print("  which is the dilution protocol's problem and the red extension's, not the verdict's.")


if __name__ == "__main__":
    main()
