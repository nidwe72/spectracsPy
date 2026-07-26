"""Would SUM(R,G,B) beat MAX(R,G,B) as the per-column reduction? (SPEC_capture_quality.md §16.8 option (c).)

`max` throws away the photons in the other channels, which is why the blank shows a V at each filter crossover
(~485 and ~580 nm). `sum` keeps them — but §15 rejected sum-like reductions because they re-admit read noise from
channels that see no light. This settles it on data: every archived run embeds BOTH full-resolution capture
frames, so all three reductions can be replayed from the same pixels and scored on the two axes that matter —
class separation over the 32-run Capability-Proof set, and fragility across Edwin's drifted A/B pair.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/reduction_sum_vs_max.py
"""
import io
import json
import os
import sys

import numpy as np
import pypdf
from PIL import Image
from scipy.signal import medfilt

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil

REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")

GREEN_OILS = ["oilK", "oilL", "oilO", "oilP"]
BROWN_OILS = ["oilM", "oilN", "oilQ", "oilR"]
SORET, QBAND = (440.0, 460.0), (560.0, 580.0)
INSET = 0.2
DARK_FLOOR_DN = 6.0        # below this a channel is read noise, not signal (dark measured at 0.00% FS, §4)

util = SpectralColorUtil()


def attachments(path):
    reader = pypdf.PdfReader(path)
    workflow = json.loads(reader.attachments["workflow.json"][0])
    reference = None
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            spectra = step.get("spectra") or {}
            if "REFERENCE" in spectra and reference is None:
                reference = {float(k): float(v) for k, v in spectra["REFERENCE"].items()}
    frames = {}
    for role, name in (("reference", "capture_reference.png"), ("sample", "capture_sample.png")):
        frames[role] = np.asarray(Image.open(io.BytesIO(reader.attachments[name][0])).convert("RGB"))
    return reference, frames


def bandRows(frame):
    rows = frame.max(axis=2).mean(axis=1)
    lit = np.where(rows > (rows.min() + rows.max()) / 2.0)[0]
    y1, y2 = int(lit[0]), int(lit[-1])
    inset = int(round((y2 - y1) * INSET))
    return y1 + inset, y2 - inset


def alignedChannels(frame, reference, offset=None):
    """Per-column R,G,B (median over the inset band rows), aligned to the stored nm grid.

    The x-offset is found ONCE, on the reference frame, and then REUSED for the sample frame: both frames of a
    run come from the same camera and the same ROI, and a heavily absorbing sample correlates badly against the
    reference's shape (it would slide the window and produce nonsense absorbance)."""
    yLo, yHi = bandRows(frame)
    band = frame[yLo:yHi, :, :]
    nms = sorted(reference)
    width = len(nms)
    if offset is None:
        profile = np.median(band.max(axis=2), axis=0)
        stored = np.array([reference[nm] for nm in nms])
        best, bestScore = 0, -2.0
        for x1 in range(0, frame.shape[1] - width, 4):
            window = profile[x1:x1 + width]
            if window.std() == 0:
                continue
            score = float(np.corrcoef(window, stored)[0, 1])
            if score > bestScore:
                best, bestScore = x1, score
        offset = best
    columns = band[:, offset:offset + width, :]
    return np.array(nms), np.median(columns, axis=0), offset        # (width, 3) raw DN per channel


def reduce(channelsDn, kind):
    linear = util.decodeGammaArray(channelsDn.astype(np.uint8))      # decode FIRST, then combine (§17.4)
    if kind == "max":
        return linear.max(axis=1)
    if kind == "sum":
        return linear.sum(axis=1)
    if kind == "gatedSum":
        return np.where(channelsDn > DARK_FLOOR_DN, linear, 0.0).sum(axis=1)
    raise ValueError(kind)


def ratioFor(path, kind):
    reference, frames = attachments(path)
    nms, referenceChannels, offset = alignedChannels(frames["reference"], reference)
    _, sampleChannels, _ = alignedChannels(frames["sample"], reference, offset=offset)
    r, s = reduce(referenceChannels, kind), reduce(sampleChannels, kind)
    floor = 6.31e-5 * r.max()
    valid = (r > floor) & (s > 0)
    absorbance = np.full(len(nms), np.nan)
    absorbance[valid] = -np.log10(s[valid] / r[valid])
    absorbance = medfilt(np.nan_to_num(absorbance), 7)
    soret = np.nanmean(absorbance[(nms >= SORET[0]) & (nms <= SORET[1])])
    q = np.nanmean(absorbance[(nms >= QBAND[0]) & (nms <= QBAND[1])])
    return soret / q if q else float("nan"), nms, reduce(referenceChannels, kind)


def cohensD(green, brown):
    green, brown = np.array(green), np.array(brown)
    pooled = np.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                     / (len(green) + len(brown) - 2))
    return abs(green.mean() - brown.mean()) / pooled


def main():
    paths = []
    for oil in GREEN_OILS + BROWN_OILS:
        for index in range(1, 6):
            path = os.path.join(REPORTS, "measurement_report_%s_%03d.pdf" % (oil, index))
            if os.path.exists(path):
                paths.append((oil, path))
    print("replaying %d runs at PIXEL level (both frames each) — this takes a minute\n" % len(paths))

    results = {}
    for kind in ("max", "sum", "gatedSum"):
        green, brown = [], []
        for oil, path in paths:
            value, _nms, _ref = ratioFor(path, kind)
            (green if oil in GREEN_OILS else brown).append(value)
        results[kind] = (green, brown)

    print("%-12s %-16s %-16s %8s %10s %10s" % ("reduction", "green (mean±SD)", "brown (mean±SD)", "d",
                                               "green CV", "brown CV"))
    for kind in ("max", "sum", "gatedSum"):
        green, brown = results[kind]
        print("%-12s %6.3f ± %-7.3f %6.3f ± %-7.3f %8.2f %9.1f%% %9.1f%%"
              % (kind, np.mean(green), np.std(green, ddof=1), np.mean(brown), np.std(brown, ddof=1),
                 cohensD(green, brown),
                 np.std(green, ddof=1) / np.mean(green) * 100, np.std(brown, ddof=1) / np.mean(brown) * 100))

    print("\n--- fragility across the drifted pair (same oil, two dilutions) ---")
    print("%-12s %9s %9s %12s" % ("reduction", "A", "B", "divergence"))
    for kind in ("max", "sum", "gatedSum"):
        a, _, _ = ratioFor(os.path.join(REPORTS, "measurement_report_NowSteirerkraftA.pdf"), kind)
        b, _, _ = ratioFor(os.path.join(REPORTS, "measurement_report_NowSteirerkraftB.pdf"), kind)
        print("%-12s %9.3f %9.3f %11.1f%%" % (kind, a, b, (b / a - 1) * 100))

    print("\n--- what each reduction does to the blank's crossover notch (run A, linear light) ---")
    print("%-12s %10s %10s %10s %10s" % ("reduction", "550-560", "570-580", "590-600", "notch depth"))
    for kind in ("max", "sum", "gatedSum"):
        _r, nms, blank = ratioFor(os.path.join(REPORTS, "measurement_report_NowSteirerkraftA.pdf"), kind)
        band = lambda lo, hi: float(np.mean(blank[(nms >= lo) & (nms <= hi)]))
        shoulder = max(band(550, 560), band(590, 600))
        print("%-12s %10.1f %10.1f %10.1f %9.0f%%"
              % (kind, band(550, 560), band(570, 580), band(590, 600),
                 (1 - band(570, 580) / shoulder) * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
