"""The two-lamp red-band control of 2026-08-09 (SPEC_capture_quality.md §16.28).

Two runs, one evening, 33 minutes apart, SAME rig and SAME calibration profile, ONE thing changed:

    20260808A   Sansi V2   (its own sharp lamp edge at ~614 nm)
    20260808B   Yuji       (its own sharp lamp edge at ~611 nm -- the 610.1 nm cliff of §16.26.7)

Both were captured with the ROI temporarily opened to 440-690 nm, which is why they are the only two
archive runs that can see past 630 at all.

⭐ WHAT THIS ESTABLISHES. A local absorbance maximum sits at 627-630 nm in BOTH runs. Because the two
lamps put their OWN sharp structure 3 nm apart while the maximum does not move, the maximum cannot be
lamp structure: an instrument artefact born on a steep emitter flank moves WITH the flank. It is
sample absorption -- protochlorophyll's Qy band, where `KB_spectroscopy_physics.md` §4.1 puts it.

⇒ The 620-630 far anchor (`PB_BASELINE_WINDOWS[1]`) is therefore sitting on a REAL, MEASURED pigment
band rather than on a window chosen by argument. §16.20 already said that window "MEASURES rather than
corrects"; this is the direct evidence for that sentence -- and it makes `PB_R_Q` MORE necessary, not
less, because a baseline anchor is supposed to sit where nothing is happening and this one does not.

⚠ WHAT IT DOES NOT ESTABLISH. The two runs' absorbances differ by factors of 0.68 to 3.00 across the
spectrum, which is neither a dilution change (flat, by Beer-Lambert) nor a lamp swap (should cancel
entirely in T = S/R). Whether A and B were the same fill is NOT recorded. So the metric-stability
spreads printed below are UPPER bounds on lamp transfer: if the fills differed, part of the spread is
sample, and the true lamp-transfer error is smaller.

Run from the spectracsPy repo root:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/red_band_two_lamps.py
"""
import numpy as np

from null_run_series import spectraOf
from settling_sweep import despikedAbsorption, asArrays, plugin, feature, R_Q_620

RUNS = [("A", "20260808A", "Sansi V2"),
        ("B", "20260808B", "Yuji")]

# The band-characterisation baseline. NOT a shipped constant -- these anchors bracket the 627-630 band
# for the purpose of measuring it, and 641-645 lies OUTSIDE the 636 nm capture clamp adopted after this
# session (§16.28.5). They can only ever be applied to spectra captured with a wider window, i.e. to
# these two runs and nothing else in the archive.
BLUE_ANCHOR, RED_ANCHOR = (608.0, 612.0), (641.0, 645.0)
SEARCH = (616.0, 645.0)          # where to hunt the maximum: red of the 614 nm lamp edge, blue of the death
QUIET = (560.0, 575.0)           # a flat stretch, for the absorbance noise floor


def smooth(values, width=5):
    return np.convolve(values, np.ones(width) / width, mode="same")


def logSlope(lam, values):
    """|dlnI/dlambda| per nm -- the quantity §16.26.7 prices emitter structure in."""
    return np.gradient(np.log(np.clip(smooth(values), 1e-3, None)), lam)


def bandOf(lam, absorbance):
    """Locate the red band and measure it against a linear baseline through the two anchors."""
    def anchor(window):
        mask = (lam >= window[0]) & (lam <= window[1])
        return lam[mask].mean(), absorbance[mask].mean()

    (x1, y1), (x2, y2) = anchor(BLUE_ANCHOR), anchor(RED_ANCHOR)
    mask = (lam >= SEARCH[0]) & (lam <= SEARCH[1])
    window, values = lam[mask], absorbance[mask]
    corrected = values - (y1 + (y2 - y1) * (window - x1) / (x2 - x1))
    peak = int(np.argmax(corrected))
    above = window[corrected >= corrected[peak] / 2.0]
    quiet = (lam >= QUIET[0]) & (lam <= QUIET[1])
    noise = (absorbance[quiet] - smooth(absorbance[quiet], 9))[4:-4].std()
    return {"rawPeakNm": float(window[int(np.argmax(values))]), "rawPeak": float(values.max()),
            "peakNm": float(window[peak]), "amplitude": float(corrected[peak]),
            "halfLo": float(above.min()), "halfHi": float(above.max()),
            "noise": float(noise), "sigma": float(corrected[peak] / noise)}


def alignment(lam, reference, sample, window, maxShift=20):
    """Normalised log-domain cross-correlation of S against R, cubic-detrended.

    A genuine reference/sample wavelength misregistration is CONSISTENT across windows. A per-window
    disagreement means the local SHAPE differs (absorption, or a lamp edge sampled differently), not
    the grid. §16.26.4 already files re-registration as a decoy; this reproduces that independently.
    """
    mask = (lam >= window[0]) & (lam <= window[1])
    a, b = np.log(np.clip(reference[mask], 1e-3, None)), np.log(np.clip(sample[mask], 1e-3, None))
    index = np.arange(len(a))
    a = a - np.polyval(np.polyfit(index, a, 3), index)
    b = b - np.polyval(np.polyfit(index, b, 3), index)
    scored = [(np.corrcoef(a[maxShift:-maxShift], b[maxShift + s:len(b) - maxShift + s])[0, 1], s)
              for s in range(-maxShift, maxShift + 1)]
    best, shift = max(scored)
    return shift * (lam[1] - lam[0]), best


TRIM = (448.0, 460.0)            # §7.13's trimmed Soret window — the one `M448` reads


def verdicts(lam, despiked):
    """The shipped pigment indices, on the SHIPPED anchors. §16.20: they are on different scales.

    `M448` / `M448+ped` are §16.27's headline pair: the SAME far-620 construction with the Soret window
    trimmed to 448-460. §16.27.3 located the exposure sensitivity in 440-447 nm, which is why the trim
    exists -- and 440-447 is also where these two lamps differ most (the Sansi V2's blue-pump spike sits
    at ~450 with its phosphor valley at 470), so the trim is expected to help here for the same reason.
    """
    spectrum = despikedFrom(lam, despiked)
    soret = feature.bandMean(spectrum, *plugin.PB_SORET_BAND)
    q = feature.bandMean(spectrum, *plugin.PB_Q_BAND)
    corrected = feature.linearBaselineCorrected(spectrum, plugin.PB_BASELINE_WINDOWS)
    farSoret = feature.bandMean(corrected, *plugin.PB_SORET_BAND)
    farQ = feature.bandMean(corrected, *plugin.PB_Q_BAND)
    trimmed = feature.bandMean(corrected, *TRIM)
    return {"raw": soret / max(q, 1e-9),
            "baseline": farSoret / max(farQ, 1e-9),
            "pedestal": farSoret / max(farQ - R_Q_620, 1e-9),
            "m448": trimmed / max(farQ, 1e-9),
            "m448ped": trimmed / max(farQ - R_Q_620, 1e-9)}


def despikedFrom(lam, values):
    from sciens.spectracs.model.spectral.Spectrum import Spectrum
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {float(k): float(v) for k, v in zip(lam, values)}
    return spectrum


def main():
    print("THE TWO-LAMP RED-BAND CONTROL — same rig, same calibration, 33 minutes apart, lamp swapped.\n")

    rows = {}
    for tag, folder, lamp in RUNS:
        lam, reference = spectraOf("%s/001.pdf" % folder, "REFERENCE")
        _, sample = spectraOf("%s/001.pdf" % folder, "SAMPLE")
        despiked = asArrays(despikedAbsorption("%s/001.pdf" % folder))
        rows[tag] = {"lamp": lamp, "lam": lam, "reference": reference, "sample": sample,
                     "absorbance": despiked, "band": bandOf(*despiked)}

    print("--- 1. THE BAND, measured on the DESPIKED absorbance ---")
    print("%-4s %-9s %9s %9s %9s %11s %8s %7s"
          % ("run", "lamp", "peak nm", "raw peak", "dA", "half-max", "noise", "sigma"))
    for tag, _, _ in RUNS:
        band, lamp = rows[tag]["band"], rows[tag]["lamp"]
        print("%-4s %-9s %9.2f %9.4f %9.4f %5.1f-%5.1f %8.5f %7.0f"
              % (tag, lamp, band["peakNm"], band["rawPeak"], band["amplitude"],
                 band["halfLo"], band["halfHi"], band["noise"], band["sigma"]))
    separation = abs(rows["A"]["band"]["peakNm"] - rows["B"]["band"]["peakNm"])
    print("    band position moves %.2f nm between the two lamps" % separation)

    print("\n--- 2. THE LAMPS — each one's OWN sharp structure, and the far anchor's footing ---")
    print("%-4s %-9s %22s %14s %14s"
          % ("run", "lamp", "steepest 600-636 nm", "620-630 med", "620-630 max"))
    for tag, _, _ in RUNS:
        lam, reference = rows[tag]["lam"], rows[tag]["reference"]
        slope = logSlope(lam, reference)
        hunt = (lam >= 600) & (lam <= 636)
        peak = int(np.argmax(abs(slope[hunt])))
        anchor = (lam >= 620) & (lam <= 630)
        print("%-4s %-9s   %6.1f %%/nm at %.1f %11.2f %%/nm %9.2f %%/nm"
              % (tag, rows[tag]["lamp"], abs(slope[hunt])[peak] * 100, lam[hunt][peak],
                 np.median(abs(slope[anchor])) * 100, abs(slope[anchor]).max() * 100))
    print("    ⇒ the lamps' own edges are ~3 nm apart; the band above is not. The far anchor sits in a")
    print("      QUIET stretch of both lamps, so a wavelength drift there is second-order (§16.26.7).")

    print("\n--- 3. R vs S alignment — is the band a misregistration artefact? ---")
    for tag, _, _ in RUNS:
        lam, reference, sample = rows[tag]["lam"], rows[tag]["reference"], rows[tag]["sample"]
        parts = []
        for window, label in (((555.0, 590.0), "Q (clean)"), ((610.0, 620.0), "lamp edge"),
                              ((465.0, 505.0), "blue-green")):
            shift, correlation = alignment(lam, reference, sample, window)
            parts.append("%s %+.2f nm (r %.3f)" % (label, shift, correlation))
        print("  %s: %s" % (tag, "; ".join(parts)))
    print("    ⇒ the CLEAN window reports 0.00 nm; the per-window disagreement is local shape, not grid.")
    print("      Consistent with §16.26.10's null runs (-0.000 to +0.005 nm) and §16.26.4's decoy finding.")

    print("\n--- 4. THE FAR ANCHOR'S PAYOFF — metric stability across the lamp swap ---")
    values = {tag: verdicts(*rows[tag]["absorbance"]) for tag, _, _ in RUNS}
    print("%-30s %11s %11s %9s" % ("construction", "A Sansi V2", "B Yuji", "spread"))
    for key, label in (("raw", "pigment ratio, no baseline"),
                       ("baseline", "far-620 baseline"),
                       ("pedestal", "far-620 baseline + pedestal"),
                       ("m448", "M448  (Soret trimmed 448-460)"),
                       ("m448ped", "M448 + pedestal")):
        a, b = values["A"][key], values["B"][key]
        print("%-30s %11.2f %11.2f %8.0f%%" % (label, a, b, abs(a - b) / ((a + b) / 2) * 100))
    print("    ⚠ levels are NOT comparable across rows (three scales, §16.20) — compare WITHIN a row.")
    print("    ⚠ these spreads are UPPER bounds on lamp transfer: the fills are not recorded as identical.")

    print("\n--- 5. THE NEAR ANCHOR 520-540 is NOT a flat stretch either ---")
    print("%-4s %-9s %8s %8s %8s %8s %8s   %s" % ("run", "lamp", "510", "520", "530", "540", "550", "min in 505-560"))
    for tag, _, _ in RUNS:
        lam, absorbance = rows[tag]["absorbance"]
        at = lambda nm: absorbance[int(np.argmin(abs(lam - nm)))]
        region = (lam >= 505) & (lam <= 560)
        print("%-4s %-9s %8.4f %8.4f %8.4f %8.4f %8.4f   %.1f nm (A=%.4f)"
              % (tag, rows[tag]["lamp"], at(510), at(520), at(530), at(540), at(550),
                 lam[region][int(np.argmin(absorbance[region]))], absorbance[region].min()))
    print("    ⇒ a reproducible bump peaks near 530 nm under BOTH lamps; the region's minimum is at")
    print("      505-511 nm. So BOTH baseline anchors sit on signal, not only the far one. §16.24 has")
    print("      the baseline contributing 62 % of the raw Q, so whatever sits here propagates into Q.")

    print("\n--- 6. WHY THE WINDOW STOPS AT 636 — the red end dies, cause NOT settled ---")
    print("%-4s %-9s %8s %8s %8s %8s %8s %8s" % ("run", "lamp", "630", "640", "645", "650", "656", "660"))
    for tag, _, _ in RUNS:
        lam, reference = rows[tag]["lam"], rows[tag]["reference"]
        at = lambda nm: reference[int(np.argmin(abs(lam - nm)))]
        print("%-4s %-9s %8.1f %8.1f %8.1f %8.1f %8.2f %8.2f"
              % (tag, rows[tag]["lamp"], at(630), at(640), at(645), at(650), at(656), at(660)))
    print("    ⇒ reference DN. Both lamps collapse together at ~645-655, which READS like a shared cutoff")
    print("      on a shared camera (the IR-cut filter).")
    print("    ⛔ BUT that is the claim DOC_lamp_410_680.md §6 WITHDREW on 2026-08-07 (Edwin's refutation),")
    print("      and §16.25.4 records the Sansi V1 at 115 DN at 656 nm — RISING from 630. Both cannot hold.")
    print("      Open: (a) V1 has a KSF line phosphor the V2 lacks; (b) §16.25.4's red end came from a")
    print("      screenshot with a TRANSFERRED wavelength scale; (c) that set clips at 255 through 600-640.")
    print("    ⭐ Decided by marking EUROPIUM_RED_FAR_680/690/700 (687.7/693.7/707.0 nm), already in the")
    print("      master data: lines visible => camera passes 690, §6 stands. Absent => IR-cut re-opens.")
    print("      See §16.28.4 — this tool does NOT resolve it.")


if __name__ == "__main__":
    main()
