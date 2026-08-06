"""The NULL-RUN series (SPEC_capture_quality.md §16.26) — measure the instrument against itself.

A *null run* is an ordinary measurement in which the SAME empty beam is captured as both the reference and the
sample. The true answer is `A = 0` at every wavelength, so everything that comes back is error, and it is error
of the exact kind a real run suffers: two bursts, separated in time, with whatever happened in between.

That makes it the only experiment on the bench that prices the instrument WITHOUT the sample — and by choosing
what happens between the two bursts (nothing / reseat the jar / swap the lamp) it prices one disturbance at a
time.

Four candidate statistics are computed for each run. Two are outright decoys and NEITHER of the other two is
a reliable predictor — correlation against |M error| with the huge outlier 004 removed, which is the honest
test because one dominant point makes everything correlate:

  * `shift`  — the wavelength offset that best maps S onto R (cross-correlation over 450-620 nm).
               ⛔ DECOY, r = +0.43. And re-registering R to S recovers nothing at all (§16.26.4).
  * `scale`  — the overall level ratio.
               ⛔ DECOY, r = +0.20. It is a constant in absorbance and §16.24.9 proved M is exactly invariant
               to those. Run 010 is the demonstration: scale 1.074, M error +0.46 %.
  * `resid`  — what is left after removing BOTH shift and scale. r = +0.84, the best of the four.
  * `tilt`   — `A(448-460) - A(620-630)`, the blue-to-red slope of the null absorbance. r = +0.80.

⚠ **Run 005 defeats both of the survivors**: tilt -0.0008 and residual 1.44 %, yet M error -5.66 %. Its null
is BOWED rather than tilted (Soret -0.0200, Q -0.0097, far -0.0192), so a two-point slope reads ~zero while the
baseline chord through 520-540 + 620-630 still leaves a large deviation in both bands. What actually drives the
metric is each band's departure from the FITTED BASELINE, which is what `M error` computes directly — and no
simple scalar summarises it. ⇒ Report `M error`; treat `resid` and `tilt` as screens for a bad run, not as
predictors.

`M error` propagates each null's band errors onto the archive's Steirerkraft values (`B_Soret` 0.6924,
`B_Q` 0.0704 on the trimmed 448-460 window) — i.e. "what would this much instrument error have done to a real
measurement?" That is the number to compare against the archive's 3-5 % run-to-run CV.

⚠ The `config` column is what was RECORDED at the bench, not what the data proves. Two runs were mislabelled
during the session; §16.26.7 makes the note-per-run a rule. `classifyLamp()` below re-derives the lamp/diffuser
from the reference shape as a cross-check.

Run from the spectracsPy repo root:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/null_run_series.py
"""
import json

import numpy as np
from pypdf import PdfReader

from settling_sweep import BASE, plugin, feature, asArrays
from sciens.spectracs.model.spectral.Spectrum import Spectrum

# The archive reference point every `M error` is expressed against (Steirerkraft, trimmed Soret window).
B_SORET, B_Q = 0.6924, 0.0704
M0 = B_SORET / B_Q

SORET = (448.0, 460.0)
FAR = (620.0, 630.0)

# The series. `config` is the bench note; see the docstring's warning about it.
RUNS = [("003", "Sansi+paper", "NO jar, nothing moved"),
        ("004", "Sansi+paper", "jar reseated (careless)"),
        ("005", "Yuji", "jar reseated"),
        ("006", "Sansi", "empty jar reseated"),
        ("007", "Sansi", "empty jar reseated"),
        ("008", "Sansi?", "unlabelled"),
        ("009", "Sansi+paper", "jar reseated"),
        ("010", "Sansi+paper", "jar reseated"),
        ("011", "Sansi+paper", "jar reseated"),
        ("012", "Sansi+paper", "IPA jar reseated"),
        ("013", "Sansi+paper", "IPA jar reseated"),
        ("014", "Sansi+paper", "IPA jar, 1/3 band"),
        ("015", "Sansi+paper", "IPA jar, 1/3 band"),
        ("016", "Sansi+paper", "IPA jar, 1/3 band"),
        ("017", "Sansi+paper", "IPA jar, 1/3 band")]
FOLDER = "20260806A"

# Runs whose disturbance was a normal, careful reseat — the population §16.26.3 quotes.
CAREFUL = ("005", "006", "007", "009", "010", "011", "012", "013", "014", "015", "016", "017")

# ⭐ The 2x2 that separates what actually matters (§16.26.10). Jar CONTENTS dominate; the reduction band is a
# second-order effect. ⚠ n = 2 per cell — directional, not established.
CELLS = [("empty jar  + 0.2 band", ("006", "007")),
         ("IPA jar    + 0.2 band", ("012", "013")),
         ("IPA jar    + 1/3 band", ("014", "015", "016", "017")),
         ("unknown    + 0.2 band", ("005", "009", "010", "011"))]


def spectraOf(path, kind):
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            raw = (step.get("spectra") or {}).get(kind)
            if raw is not None:
                values = raw.get("valuesByNanometers", raw)
                keys = sorted(values, key=float)
                return (np.array([float(k) for k in keys]),
                        np.array([float(values[k]) for k in keys]))
    raise KeyError("%s has no %s" % (path, kind))


def bestShift(nanometers, reference, sample, lo=450.0, hi=620.0):
    """The (shift, residual, scale) that best maps S onto R. Residual is AFTER both are removed."""
    mask = (nanometers >= lo) & (nanometers <= hi)
    x, r, s = nanometers[mask], reference[mask], sample[mask]
    best = None
    for shift in np.arange(-2.0, 2.001, 0.005):
        shifted = np.interp(x, x + shift, r)
        scale = (shifted @ s) / (shifted @ shifted)
        residual = np.sqrt(np.mean((s - scale * shifted) ** 2)) / s.mean()
        if best is None or residual < best[1]:
            best = (float(shift), float(residual), float(scale))
    return best


def bandMeans(nanometers, absorbance):
    """The baselined Soret and Q means, through the SHIPPED pipeline (de-spike + linear baseline)."""
    spectrum = Spectrum()
    spectrum.valuesByNanometers = {float(k): float(v) for k, v in zip(nanometers, absorbance)}
    corrected = feature.linearBaselineCorrected(
        plugin._DevSpectralPlugin__despikedAbsorption(spectrum), plugin.PB_BASELINE_WINDOWS)
    lam, values = asArrays(corrected)
    band = lambda window: float(values[(lam >= window[0]) & (lam <= window[1])].mean())
    return band(SORET), band(plugin.PB_Q_BAND)


def metricError(soretError, qError):
    """What these band errors would do to M on the archive's fill, in percent."""
    return 100.0 * (((B_SORET + soretError) / (B_Q + qError)) - M0) / M0


def measure(tag):
    path = "%s/%s.pdf" % (FOLDER, tag)
    nanometers, reference = spectraOf(path, "REFERENCE")
    _, sample = spectraOf(path, "SAMPLE")
    _, absorbance = spectraOf(path, "ABSORPTION")
    shift, residual, scale = bestShift(nanometers, reference, sample)
    band = lambda w: float(absorbance[(nanometers >= w[0]) & (nanometers <= w[1])].mean())
    soretError, qError = bandMeans(nanometers, absorbance)
    return {"shift": shift, "scale": scale, "residual": 100.0 * residual,
            "aSoret": band(SORET), "aQ": band(plugin.PB_Q_BAND),
            "tilt": band(SORET) - band(FAR), "mError": metricError(soretError, qError),
            "redFeature": redFeature(nanometers, absorbance)}


def redFeature(nanometers, absorbance, lo=612.0, hi=629.8, window=41):
    """The far-anchor 'red peak' statistic (§16.26.11): the largest departure from a locally smoothed curve
    across 612-629.8 nm. It is what caught the moving 619/624 nm feature in runs 001/002 — a bump that is NOT
    noise (200-600x the point-to-point sd) and NOT visible in a same-liquid null, so it needs something to
    change between R and S. The Sansi's ~619 nm edge (-11 %/nm) amplifies whatever that change is, which is why
    this is the read-out for the refill-null protocol: quote it per run, per lamp."""
    mask = (nanometers >= lo) & (nanometers <= hi)
    values = absorbance[mask]
    if len(values) < window + 40:
        return float("nan")
    smoothed = np.convolve(values, np.ones(window) / window, mode="same")
    return float(np.abs(values - smoothed)[20:-20].max())


def classifyLamp(tag):
    """Re-derive lamp + diffuser from the reference SHAPE, independent of the bench note. The paper is a red
    filter (§16.26.6), so blue/far-red separates the three configurations cleanly."""
    nanometers, reference = spectraOf("%s/%s.pdf" % (FOLDER, tag), "REFERENCE")
    band = lambda lo, hi: float(reference[(nanometers >= lo) & (nanometers <= hi)].mean())
    return band(450, 460) / max(band(620, 630), 1e-9)


def main():
    print("NULL RUNS — the same empty beam as BOTH reference and sample. Truth is A = 0 everywhere.")
    print("M error = what each null's band errors would do to the archive fill (M0 = %.3f).\n" % M0)
    print("%-5s %-12s %-24s %7s %7s %7s | %8s %8s %8s | %8s"
          % ("run", "lamp", "what moved", "shift", "scale", "resid", "A_Soret", "A_Q", "tilt", "M error"))
    print("-" * 116)
    rows = {}
    for tag, lamp, what in RUNS:
        row = rows[tag] = measure(tag)
        print("%-5s %-12s %-24s %+7.3f %7.4f %6.2f%% | %+8.4f %+8.4f %+8.4f | %+7.2f%%"
              % (tag, lamp, what, row["shift"], row["scale"], row["residual"],
                 row["aSoret"], row["aQ"], row["tilt"], row["mError"]))

    floor = rows["003"]
    print("\n⭐ THE INSTRUMENT FLOOR (003, nothing moved between the bursts):")
    print("   residual %.2f %%   M error %+.2f %%   ⇒ the instrument is NOT the archive's 3-5 %% CV."
          % (floor["residual"], floor["mError"]))

    careful = np.array([rows[t]["mError"] for t in CAREFUL])
    print("\n⭐ THE CAREFUL-RESEAT POPULATION (%s):" % ", ".join(CAREFUL))
    print("   %s" % "  ".join("%+.2f%%" % v for v in careful))
    print("   median |error| %.2f %%   rms %.2f %%   max |error| %.2f %%   (careless 004: %+.2f %%)"
          % (np.median(np.abs(careful)), np.sqrt((careful ** 2).mean()),
             np.abs(careful).max(), rows["004"]["mError"]))
    print("   ⇒ SKEWED: most reseats cost little, a minority cost a lot. Not a steady penalty.")

    print("\n⭐⭐ WHAT ACTUALLY MATTERS — the 2x2 (§16.26.10). ⚠ n = 2-4 per cell.")
    print("   %-24s %3s %-34s %8s" % ("cell", "n", "M errors", "rms"))
    cellRms = {}
    for name, tags in CELLS:
        v = np.array([rows[t]["mError"] for t in tags])
        cellRms[name] = float(np.sqrt((v ** 2).mean()))
        print("   %-24s %3d %-34s %7.2f%%"
              % (name, len(v), " ".join("%+6.2f%%" % x for x in v), cellRms[name]))
    print("   ⇒ jar contents (same band): empty %.2f %% -> IPA %.2f %%  = %.1fx"
          % (cellRms["empty jar  + 0.2 band"], cellRms["IPA jar    + 0.2 band"],
             cellRms["empty jar  + 0.2 band"] / cellRms["IPA jar    + 0.2 band"]))
    print("   ⇒ reduction band (same IPA): 0.2 %.2f %% -> 1/3 %.2f %%  = %.1fx"
          % (cellRms["IPA jar    + 0.2 band"], cellRms["IPA jar    + 1/3 band"],
             cellRms["IPA jar    + 0.2 band"] / cellRms["IPA jar    + 1/3 band"]))
    ipa = np.array([rows[t]["mError"] for t in ("012", "013", "014", "015", "016", "017")])
    ipaRms = float(np.sqrt((ipa ** 2).mean()))
    print("   ⇒ ALL confirmed-IPA reseats (n=%d): rms %.2f %% — the OPERATING-condition figure."
          % (len(ipa), ipaRms))
    print("     ⚠ against a 3-5 %% archive CV that leaves ~%.1f %% unexplained: re-seating is NOT the whole CV."
          % np.sqrt(max(16.0 - ipaRms ** 2, 0.0)))

    print("\n⭐ CANDIDATE STATISTICS vs |M error| — correlation, with and without the 004 outlier.")
    print("   (one dominant point makes everything correlate, so the right-hand column is the honest one)")
    tags = [t for t, _, _ in RUNS]
    withoutBad = [t for t in tags if t != "004"]
    print("   %-10s %12s %16s" % ("statistic", "r (all 8)", "r (without 004)"))
    for name, key, offset in (("|shift|", "shift", 0.0), ("|scale-1|", "scale", 1.0),
                              ("residual", "residual", 0.0), ("|tilt|", "tilt", 0.0)):
        out = []
        for subset in (tags, withoutBad):
            x = np.array([abs(rows[t][key] - offset) for t in subset])
            y = np.array([abs(rows[t]["mError"]) for t in subset])
            out.append(np.corrcoef(x, y)[0, 1])
        print("   %-10s %+12.3f %+16.3f" % (name, out[0], out[1]))
    print("   ⛔ shift and scale are decoys. residual and tilt both sit near +0.8 and BOTH MISS run 005")
    print("      (tilt %+.4f, resid %.2f %% -> M error %+.2f %%): its null is bowed, not tilted."
          % (rows["005"]["tilt"], rows["005"]["residual"], rows["005"]["mError"]))
    print("   ⇒ no simple scalar predicts the damage; report M error itself.")

    print("\n⚠ LAMP CROSS-CHECK from the reference shape — blue(450-460)/far-red(620-630):")
    print("   paper ~0.96 · bare Sansi ~1.82 · Yuji archive ~2.97")
    for tag, lamp, _ in RUNS:
        print("   %-5s bench note %-12s  measured %.2f" % (tag, lamp, classifyLamp(tag)))


if __name__ == "__main__":
    main()
