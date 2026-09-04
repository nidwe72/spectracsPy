"""HOW MUCH DOES A LIGHT-LEVEL CHANGE MOVE EACH METRIC? Priced on the archive, per metric, with a null.

(Edwin, 2026-09-04: "i fear that with the camera with encoding change the light situation a little bit
changes metrics. and the camera providing raw captures would be more stable against this.")

He is right about the mechanism. In LINEAR DN a lamp change common to both legs cancels EXACTLY in
T = S/R, at every level -- that invariance is why the reference leg exists. It does not survive a
non-power-law encoding, because S and R sit at DIFFERENT DN in the same bin and are therefore read off
different parts of the curve. This puts a number on it, per metric, using the transfer curve MEASURED by
`diagnostics/transfer_curve.py`.

Three arms, so the two terms separate:

    1. measured curve + 8-bit rounding    the real instrument: what a lamp change actually does
    2. measured curve, no rounding        the smooth encoding nonlinearity ALONE
    3. LINEAR (e = 1) + 8-bit rounding    ⭐ THE NULL. A linear camera decoded with a power law is exactly
                                          invariant to a common level change, so whatever shows up in this
                                          arm is REQUANTISATION and not encoding. It returns 0.003-0.05
                                          on `Q%`, which is what validates the whole method.

⭐ THE ANSWER, for a 10 % light change, over the 72 archived runs where `Rv` is readable (80-140):

    metric        encoding curve   requantisation   ⇒
    Q%              0.204 (1.2 %)      0.046          the encoding dominates, ~0.7 sigma_fill
    Rv              0.182 (0.18 %)     1.028          ⭐ the BITS dominate, ~5x Rv's own read noise
    RvLin           0.881 (0.96 %)     1.488          worst on both axes
    Soret/Q raw     0.008 (0.2 %)      0.003          near-immune

⛔ CONDITION ON A READABLE `Rv` OR THE ANSWER IS WRONG. Over the whole corpus the same numbers read 1.693
and 2.730, because a brown oil drives `A_Q - A_valley` -- `Rv`'s denominator -- towards zero and every
sensitivity explodes with it. That fragility is the metric's own conditioning, not the camera's.

⚠ Three caveats, none of which the numbers carry on their face:
  * PARTLY CIRCULAR -- the curve was measured on the same C/D/F-vs-E contrast, so re-applying it to C
    partly reconstructs E. NOT circular: the null arm, and the ORDERING across metrics (one curve, four
    metrics).
  * The requantisation arm is an UPPER BOUND: this rounds one stored frame once, where a real capture
    averages 60 frames and dithers (`KB_cameras.md` section 4.1a's own point).
  * Below 18 DN the exponent is not measurable and is held flat.

Run:
    PYTHONPATH=".:./diagnostics:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/level_sensitivity.py            # whole corpus
    HEALTHY_RV=1 ... diagnostics/level_sensitivity.py                 # only where `Rv` is readable
"""
import math
import os
import sys
import time

import numpy as np
from scipy.signal import medfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import reduction_sum_vs_max as replay

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil

UTIL = SpectralColorUtil()

# e(DN) = dlnDN/dlnX, MEASURED on both legs of C/D/F vs E, three independent pairs
# (`diagnostics/transfer_curve.py --low`). ⭐ A raw LINEAR camera is e = 1 at every level; this camera runs
# from 2.0 in the dark to 0.41 near the clip, which is the whole of the effect priced below.
BAND_CENTRE = np.array([20.0, 30.0, 42.0, 62.0, 92.0, 135.0, 190.0, 235.0])
EXPONENT = np.array([2.00, 1.82, 1.46, 1.14, 0.94, 0.75, 0.60, 0.41])
LEVELS = [0.80, 0.90, 0.95, 1.05, 1.10, 1.20]
KEYS = ("Q%", "Rv", "RvLin", "Soret/Q raw")
SORET, VALLEY, QBAND = (448.0, 460.0), (500.0, 560.0), (565.0, 580.0)
RED, LOCAL, PB_Q = (622.0, 627.0), (612.0, 615.0), (560.0, 580.0)
ARMS = (("1 measured curve + rounding", True, True),
        ("2 measured curve, no rounding", True, False),
        ("3 LINEAR + rounding  (null)", False, True))


def localExponent(dn):
    return np.interp(np.log(np.clip(dn, 1.0, 255.0)), np.log(BAND_CENTRE), EXPONENT)


def levelShift(dn, m, curved=True, steps=40):
    """DN after the light changes by factor m, integrating dlnDN/dlnX = e(DN) (RK2)."""
    if m == 1.0:
        return dn.astype(float)
    if not curved:
        return np.clip(dn.astype(float) * m, 0.0, 255.0)
    lnDn = np.log(np.maximum(dn.astype(float), 0.5))
    h = math.log(m) / steps
    for _ in range(steps):
        first = localExponent(np.exp(lnDn))
        lnDn = lnDn + h * localExponent(np.exp(lnDn + 0.5 * h * first))
    return np.clip(np.exp(lnDn), 0.0, 255.0)


def band(nms, absorbance, window):
    return float(np.interp(np.arange(window[0], window[1] + 0.001, 0.25), nms, absorbance).mean())


def metrics(nms, absorbance):
    """`Q%`, `Rv`, `RvLin` and the un-baselined Soret/Q ratio, on the same windows the plugin declares."""
    soret, valley, q = (band(nms, absorbance, SORET), band(nms, absorbance, VALLEY),
                        band(nms, absorbance, QBAND))
    red, local = band(nms, absorbance, RED), band(nms, absorbance, LOCAL)
    out = {"Q%": 100.0 * (q - valley) / soret if soret else np.nan}
    out["Rv"] = 100.0 * (red - valley) / (q - valley) if (q - valley) > 0 else np.nan
    slope = (local - valley) / (613.5 - 530.0)
    line = lambda at: valley + slope * (at - 530.0)
    denominator = q - line(572.5)
    out["RvLin"] = 100.0 * (red - line(624.5)) / denominator if denominator > 0 else np.nan
    pbQ = band(nms, absorbance, PB_Q)
    out["Soret/Q raw"] = soret / pbQ if pbQ else np.nan
    return out


def decode(dn, roundIt):
    if roundIt:
        return UTIL.decodeGammaArray(np.round(dn).astype(np.uint8)).max(axis=1)
    return ((np.clip(dn, 0, 255) / 255.0) ** 2.2).max(axis=1)


def absorbanceOf(referenceDn, sampleDn, m, curved, roundIt):
    r = decode(levelShift(referenceDn, m, curved), roundIt)
    s = decode(levelShift(sampleDn, m, curved), roundIt)
    floor = 6.31e-5 * r.max()
    valid = (r > floor) & (s > 0)
    absorbance = np.full(len(r), np.nan)
    absorbance[valid] = -np.log10(s[valid] / r[valid])
    return medfilt(np.nan_to_num(absorbance), 7)


def main():
    paths = [os.path.join(folder, name) for folder, name in archive.walkReports()]
    limit = int(os.environ.get("LIMIT", "0"))
    if limit:
        paths = paths[:limit]
    healthyOnly = os.environ.get("HEALTHY_RV") == "1"
    shifts = {arm[0]: {k: {m: [] for m in LEVELS} for k in KEYS} for arm in ARMS}
    bases = {k: [] for k in KEYS}
    started, used, skipped = time.time(), 0, 0

    for index, path in enumerate(paths):
        try:
            reference, frames = replay.attachments(path)
            nms, referenceDn, offset = replay.alignedChannels(frames["reference"], reference)
            _, sampleDn, _ = replay.alignedChannels(frames["sample"], reference, offset=offset)
            nms = np.asarray(nms, float)
            base = metrics(nms, absorbanceOf(referenceDn, sampleDn, 1.0, True, True))
            rv = base.get("Rv")
            if not np.isfinite(base["Q%"]) or rv is None or not np.isfinite(rv) or abs(rv) > 500:
                skipped += 1
                continue
            if healthyOnly and not 80.0 <= rv <= 140.0:
                skipped += 1
                continue
            for key in KEYS:
                bases[key].append(base[key])
            for label, curved, roundIt in ARMS:
                for m in LEVELS:
                    values = metrics(nms, absorbanceOf(referenceDn, sampleDn, m, curved, roundIt))
                    for key in KEYS:
                        shifts[label][key][m].append(values[key] - base[key])
            used += 1
        except Exception:                       # a malformed or non-report PDF must not stop the sweep
            skipped += 1
        if (index + 1) % 50 == 0:
            print("   ... %d/%d  (%.0f s)" % (index + 1, len(paths), time.time() - started), flush=True)

    print("\n%d runs used, %d skipped%s (%.0f s)\n"
          % (used, skipped, " — Rv-readable only" if healthyOnly else "", time.time() - started))
    for key in KEYS:
        print("== %s   (typical value %.2f) ==" % (key, np.nanmedian(bases[key])))
        print("   arm                            " + "".join("%9s" % ("m=%.2f" % m) for m in LEVELS))
        for label, _, _ in ARMS:
            cells = ""
            for m in LEVELS:
                values = np.array(shifts[label][key][m], float)
                values = values[np.isfinite(values)]
                cells += "%9s" % ("%+.3f" % np.median(values) if len(values) else "-")
            print("   %-30s %s" % (label, cells))
        summary = []
        for label, _, _ in ARMS:
            values = np.abs(np.array(shifts[label][key][1.10], float))
            values = values[np.isfinite(values)]
            summary.append((np.median(values), np.percentile(values, 90)))
        print("   |shift| at m=1.10  median/p90:  real %.3f/%.3f   curve-only %.3f/%.3f   null %.3f/%.3f\n"
              % (summary[0][0], summary[0][1], summary[1][0], summary[1][1], summary[2][0], summary[2][1]))


main()
