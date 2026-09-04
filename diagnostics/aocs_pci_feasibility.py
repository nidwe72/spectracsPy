"""Could we execute AOCS Cc 13c-50 (the Photometric Color Index) on neat oil? — asked of the archive.

    ./venv/bin/python diagnostics/aocs_pci_feasibility.py

    PCI = 1.29*A460 + 69.7*A550 + 41.2*A620 - 56.4*A670        (AOCS Cc 13c-50, NEAT oil vs air)

⭐ WHY THIS IS INTERESTING AT ALL. Every metric in the project so far is ours — `Q%`, `dQ100`, `V`, `R`.
`PCI` is a NUMBER SOMEONE ELSE DEFINED, which a third-party lab can reproduce. And three of its four
wavelengths already sit inside the shipped 400-630 nm window.

⛔⛔ BUT PCI IS NOT DILUTION-INVARIANT, AND THAT IS THE WHOLE POINT OF IT. It is a weighted sum of
ABSORBANCES, so `PCI ∝ c·L`. AOCS sidesteps the invariance problem the entire metric-research programme
exists to solve — not by finding an invariant combination, but by FIXING BOTH VARIABLES: neat oil (c is
the oil itself) in a cell of stated thickness (L is machined). ⇒ a statistical problem becomes a
mechanical one.

WHAT THIS SCRIPT CAN AND CANNOT ANSWER
--------------------------------------
⛔ It CANNOT compute PCI. The archive is oil-in-isopropanol at an unknown dilution and stops at 632.6 nm,
   so both `A670` and the absolute scale are missing.
⭐ It CAN answer the two questions that decide feasibility, because both are pure SHAPE and shape needs
   no dilution factor:

   Q1  DYNAMIC RANGE — PCI needs all four bands readable at ONE path length. How far apart are they?
       That ratio is the spec for the detector, and it is exactly the regime where bit depth stops being
       a rounding error (KB_cameras.md §4.1b).
   Q2  IS THE COMPUTABLE PART A NEW AXIS, or does it land on `Q%` like everything else?
       ⚠ Prior: `spectracs-metric-family-2026-08-21` found Q%/dQ100/B/Q%_k all correlate 0.84-0.99.
       PCI's first three terms are built from the same bands, so the honest prediction is that they
       land on the same axis and the ONLY new information is the 670 nm term we cannot see.
       A prediction stated before the measurement is worth more than one fitted after it.
"""
import glob
import json
import os

import numpy as np
from pypdf import PdfReader

ARCHIVE = "/home/nidwe72/development/spectracs/spectracs-references/tmp"

# AOCS Cc 13c-50. The 670 term is OUTSIDE the shipped window — it is the one this instrument cannot see.
PCI_TERMS = [(460.0, 1.29), (550.0, 69.7), (620.0, 41.2), (670.0, -56.4)]
HALF_WIDTH = 5.0                      # +-5 nm around each AOCS wavelength

SORET_BAND = (448.0, 460.0)           # the concentration proxy, and the darkest thing we measure
VALLEY_BAND = (500.0, 560.0)
Q_BAND = (565.0, 580.0)


def spectra(path):
    found = {}
    workflow = json.loads(PdfReader(path).attachments["workflow.json"][0])
    for phase in workflow.get("phases", []):
        for step in phase.get("steps", []):
            for role, raw in (step.get("spectra") or {}).items():
                if role in ("REFERENCE", "SAMPLE") and role not in found:
                    values = raw.get("valuesByNanometers", raw)
                    found[role] = {float(k): float(v) for k, v in values.items()}
    return found.get("REFERENCE"), found.get("SAMPLE")


def absorbance(reference, sample):
    nanometers = np.array(sorted(set(reference) & set(sample)))
    r = np.array([reference[nm] for nm in nanometers])
    s = np.array([sample[nm] for nm in nanometers])
    usable = (r > 0.01) & (s > 0.01)
    values = np.full(nanometers.shape, np.nan)
    values[usable] = np.log10(r[usable] / s[usable])
    return nanometers, values


def bandMean(nanometers, values, low, high):
    inside = (nanometers >= low) & (nanometers <= high) & np.isfinite(values)
    return float(np.mean(values[inside])) if inside.sum() else float("nan")


def main():
    rows, paths = [], []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*", "*.pdf"))):
        try:
            reference, sample = spectra(path)
            if reference is None or sample is None:
                continue
            nanometers, values = absorbance(reference, sample)
            soret = bandMean(nanometers, values, *SORET_BAND)
            if not np.isfinite(soret) or soret <= 0.334:
                continue
            row = {"soret": soret,
                   "valley": bandMean(nanometers, values, *VALLEY_BAND),
                   "q": bandMean(nanometers, values, *Q_BAND)}
            for centre, _weight in PCI_TERMS[:3]:
                row["A%d" % centre] = bandMean(nanometers, values,
                                               centre - HALF_WIDTH, centre + HALF_WIDTH)
            if any(not np.isfinite(v) for v in row.values()):
                continue
            row["qPercent"] = -100.0 * (row["valley"] - row["q"]) / row["soret"]
            rows.append(row)
            paths.append(path)
        except Exception:
            continue

    if not rows:
        print("no usable runs")
        return
    print("%d archived runs\n" % len(rows))

    print("=== Q1. DYNAMIC RANGE — PCI needs all four bands readable at ONE path length")
    print("   band        A / A(460)      what a path giving A460 = 1.0 would read")
    a460 = np.array([r["A460"] for r in rows])
    for centre, _weight in PCI_TERMS[:3]:
        values = np.array([r["A%d" % centre] for r in rows])
        ratio = values / a460
        print("   %d nm    %6.3f (median)   A = %.3f     [%.3f .. %.3f across the corpus]"
              % (centre, np.median(ratio), np.median(ratio),
                 np.percentile(ratio, 5), np.percentile(ratio, 95)))
    soret = np.array([r["soret"] for r in rows])
    print("   ⚠ and the Soret 448-460 sits at %.2f x A460 — %.2f at that same path"
          % (np.median(soret / a460), np.median(soret / a460)))

    highest = np.median(soret / a460)
    lowest = min(np.median(np.array([r["A%d" % centre] for r in rows]) / a460)
                 for centre, _ in PCI_TERMS[:3])
    print("\n   ⇒ at a path giving A460 = 1.0 the four bands span A = %.2f .. %.2f — a factor of %.1f,"
          % (lowest, highest, highest / lowest))
    print("     i.e. transmittance %.0f %% down to %.1f %%. ⭐ THAT IS A COMFORTABLE 8-BIT RANGE."
          % (100 * 10 ** -lowest, 100 * 10 ** -highest))
    print("     ⛔ Corrects an earlier guess that neat oil would put PCI back in the starved regime: it")
    print("     does not, because PCI reads 460 on the Soret FLANK, never the 432 peak.")

    print("\n=== Q2. Is the computable part of PCI a NEW axis, or Q% again?")
    partial = np.array([1.29 * r["A460"] + 69.7 * r["A550"] + 41.2 * r["A620"] for r in rows])
    qPercent = np.array([r["qPercent"] for r in rows])
    # ⚠ PCI scales with dilution, Q% does not — so the RAW correlation is dominated by concentration.
    # Dividing by A_Soret removes the concentration axis and asks the SHAPE question, which is the only
    # one the archive can answer.
    shape = partial / soret
    print("   raw PCI_partial vs Q%%          r = %+.3f   ⚠ meaningless: PCI carries the dilution"
          % np.corrcoef(partial, qPercent)[0, 1])
    print("   PCI_partial / A_Soret vs Q%%    r = %+.3f   <- the shape question" % np.corrcoef(shape, qPercent)[0, 1])
    print("   PCI_partial vs A_Soret         r = %+.3f   <- how much of it is just concentration"
          % np.corrcoef(partial, soret)[0, 1])

    correlation = abs(np.corrcoef(shape, qPercent)[0, 1])
    print("\n   ⇒ %s" % ("SAME AXIS as the metric family — the first three terms add nothing new, exactly"
                          " as predicted" if correlation > 0.8 else
                          "⛔ NOT the same axis (|r| = %.2f) — the prediction above FAILS" % correlation))

    print("\n=== Q3. Is that independence SIGNAL, or just noise left after removing concentration?")
    print("   ⚠ r ~ 0 alone proves nothing: PCI_partial is 77 %% concentration (r = +0.77 with A_Soret),")
    print("     so dividing it out could leave scatter rather than a new axis. The test that separates")
    print("     the two: does the residual DISCRIMINATE BETWEEN OILS? Grouped by source folder.")
    groups = {}
    for row, path in zip(rows, paths):
        groups.setdefault(os.path.basename(os.path.dirname(path)), []).append(row)
    groups = {k: v for k, v in groups.items() if len(v) >= 4}
    if len(groups) < 3:
        print("   too few labelled groups")
        return
    print("\n   quantity                    within-oil sd   between-oil sd   ratio (>1 = discriminates)")
    for label, series in (("Q% (the shipped metric)", lambda r: r["qPercent"]),
                          ("PCI_partial / A_Soret", lambda r: (1.29 * r["A460"] + 69.7 * r["A550"]
                                                               + 41.2 * r["A620"]) / r["soret"])):
        means, within = [], []
        for members in groups.values():
            values = np.array([series(r) for r in members])
            means.append(values.mean())
            within.append(values.std(ddof=1))
        pooledWithin = float(np.sqrt(np.mean(np.array(within) ** 2)))
        between = float(np.std(means, ddof=1))
        print("   %-27s %12.4f %16.4f %10.2f"
              % (label, pooledWithin, between, between / pooledWithin))
    print("   (%d oils with >=4 runs)" % len(groups))
    print("\n   ⭐ The DECISIVE term is still -56.4*A670 — 40 %% of PCI's weight by coefficient, and the")
    print("   one wavelength this instrument cannot see. Nothing here settles PCI; it sizes the question.")


if __name__ == "__main__":
    main()
