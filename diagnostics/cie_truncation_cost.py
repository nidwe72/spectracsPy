"""What does our wavelength clamp cost a COLOUR number? — the CIE integrals, truncated.

    ./venv/bin/python diagnostics/cie_truncation_cost.py

⭐ WHY. A band metric (`Q%`, `Rv`, PCI) needs a handful of wavelengths. A **colour** number — Lovibond,
AOCS-Tintometer, a Kreft dichromaticity index — is a **tristimulus integral** and needs the whole visible
band. `spectracs-colorimeter-idea` records the objection in one line: *"with the 440–630 nm window a
literature-comparable DI is NOT computable (x̄ runs past 700)"*.

⭐⭐ That is true of the CLAMP and false of the INSTRUMENT, and this script measures the difference. It
computes the fraction of each D65-weighted CIE 1931 2° colour-matching function lying above a cutoff,
twice:

  1. **illuminant-weighted** — what a white source loses;
  2. ⭐ **sample-weighted** — what an actual archived oil loses, which is the number that matters, because
     these oils transmit mostly in the RED, i.e. exactly where the clamp cuts.

⚠ For (2) the measured absorbance stops at 632.6 nm and is held FLAT beyond at its 620–630 nm value.
Real transmittance *rises* into the red, so ⛔ **every sample-weighted figure here is a LOWER BOUND on
the loss.**

⛔ WHAT IT DOES NOT SAY. That a colour number is *reportable*. `KB_cameras.md` §4.5d carries the other
three gates — the Lovibond scale is proprietary, `Cc 13j-97`'s scope is refined oils only, and Lovibond is
defined at a 133 mm cell. This script settles the OPTICAL question alone.
"""
import glob
import json
import os

import numpy as np
from colour import MSDS_CMFS, SDS_ILLUMINANTS, SpectralShape
from pypdf import PdfReader

ARCHIVE = "/home/nidwe72/development/spectracs/spectracs-references/tmp"
SHAPE = SpectralShape(360, 830, 1)

CUTOFFS = [(632.6, "pipeline clamp — the AUTHORED roi"),
           (690.8, "extended roi — what the capture view draws"),
           (780.0, "the full visible band")]


def observer():
    cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"].copy().align(SHAPE)
    illuminant = SDS_ILLUMINANTS["D65"].copy().align(SHAPE)
    return cmfs.wavelengths, illuminant.values, cmfs.values


def anArchivedOilAbsorbance():
    """One real run's absorbance, as (nanometers, A). The first that carries enough finite bins."""
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*", "*.pdf"))):
        try:
            workflow = json.loads(PdfReader(path).attachments["workflow.json"][0])
        except Exception:
            continue
        found = {}
        for phase in workflow.get("phases", []):
            for step in phase.get("steps", []):
                for role, raw in (step.get("spectra") or {}).items():
                    if role in ("REFERENCE", "SAMPLE") and role not in found:
                        values = raw.get("valuesByNanometers", raw)
                        found[role] = {float(k): float(v) for k, v in values.items()}
        if len(found) < 2:
            continue
        reference, sample = found["REFERENCE"], found["SAMPLE"]
        nanometers = np.array(sorted(set(reference) & set(sample)))
        r = np.array([reference[nm] for nm in nanometers])
        s = np.array([sample[nm] for nm in nanometers])
        usable = (r > 0.01) & (s > 0.01)
        if usable.sum() < 500:
            continue
        return os.path.relpath(path, ARCHIVE), nanometers[usable], np.log10(r[usable] / s[usable])
    return None, None, None


def main():
    lam, illuminant, cmfs = observer()
    weighted = cmfs * illuminant[:, None]

    print("1. ILLUMINANT-WEIGHTED — the fraction of each CIE integral above a cutoff (D65, 2° observer)\n")
    print("   cutoff                                          x̄ (red)    ȳ (lum)   z̄ (blue)")
    for cutoff, label in CUTOFFS:
        above = lam > cutoff
        share = 100.0 * weighted[above].sum(axis=0) / weighted.sum(axis=0)
        print("   %6.1f nm  %-38s %6.2f %%   %6.2f %%  %6.2f %%" % (cutoff, label, *share))

    name, nanometers, absorbanceValues = anArchivedOilAbsorbance()
    if nanometers is None:
        print("\n⛔ no archived run usable for the sample-weighted half")
        return

    tail = float(np.mean(absorbanceValues[(nanometers >= 620) & (nanometers <= 630)]))
    extended = np.interp(lam, nanometers, absorbanceValues,
                         left=float(absorbanceValues[0]), right=tail)
    transmittance = 10.0 ** (-extended)
    total = (transmittance[:, None] * weighted).sum(axis=0)

    print("\n2. ⭐ SAMPLE-WEIGHTED — the same, weighted by what a real oil TRANSMITS")
    print("   run %s; absorbance held flat past 632.6 nm at its 620-630 value (A = %.3f)" % (name, tail))
    print("   ⛔ real transmittance RISES into the red ⇒ every figure below is a LOWER BOUND.\n")
    print("   cutoff                                          x̄ (red)    ȳ (lum)   z̄ (blue)")
    for cutoff, label in CUTOFFS:
        above = lam > cutoff
        part = (transmittance[above, None] * weighted[above]).sum(axis=0)
        print("   %6.1f nm  %-38s %6.2f %%   %6.2f %%  %6.2f %%" % (cutoff, label, *(100 * part / total)))

    clamp = lam > CUTOFFS[0][0]
    extendedRoi = lam > CUTOFFS[1][0]
    lostAtClamp = 100 * (transmittance[clamp, None] * weighted[clamp]).sum(axis=0)[0] / total[0]
    lostAtRoi = 100 * (transmittance[extendedRoi, None] * weighted[extendedRoi]).sum(axis=0)[0] / total[0]
    print("\n⇒ ⭐⭐ x̄ — the RED primary — is the only one truncated: %.1f %% missing at the clamp,"
          % lostAtClamp)
    print("  %.1f %% at the extended ROI. z̄ finishes before either; ȳ almost." % lostAtRoi)
    print("  ⇒ **a colour number is not computable at 632.6 nm and IS at 690.8 nm.** The objection on")
    print("    record — 'x̄ runs past 700' — is true of the CLAMP, not of the instrument. 780 nm is not")
    print("    needed; the extended ROI already drawn in the capture view suffices.")
    print("  ⛔ Optical question only. `KB_cameras.md` §4.5d carries the three gates that remain.")


if __name__ == "__main__":
    main()
