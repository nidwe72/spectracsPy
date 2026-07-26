"""Why does the ISOPROPANOL BLANK read so low around 570-580 nm when the ROI image looks uniform?
(Edwin 2026-07-27.) Replays the full-resolution capture frames embedded in the report PDFs and splits the
reduction back into its R/G/B parts — the stored spectrum is max(R,G,B), which hides which channel produced it.

Hypothesis under test: 560-580 nm falls in the sensor's GREEN->RED colour-filter CROSSOVER, where both filters
are off-peak, so max(R,G,B) dips even though the light is smooth. If so, the Q band sits in the camera's
worst-sensitivity valley — and the channel that "wins" the max there can flip between runs.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/gamma_reference_valley.py [runA runB]
"""
import io
import json
import os
import sys

import numpy as np
import pypdf
from PIL import Image

REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")
INSET = 0.2      # same band inset the extractor uses


def load(name):
    reader = pypdf.PdfReader(os.path.join(REPORTS, "measurement_report_%s.pdf" % name))
    workflow = json.loads(reader.attachments["workflow.json"][0])
    reference = None
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            spectra = step.get("spectra") or {}
            if "REFERENCE" in spectra and reference is None:
                reference = {float(k): float(v) for k, v in spectra["REFERENCE"].items()}
    png = reader.attachments["capture_reference.png"][0]
    frame = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(np.float32)
    return reference, frame


def roiBand(frame):
    # The lit slit band: rows whose max-channel mean is well above the frame's own median row.
    rows = frame.max(axis=2).mean(axis=1)
    lit = np.where(rows > (rows.min() + rows.max()) / 2.0)[0]
    y1, y2 = int(lit[0]), int(lit[-1])
    inset = int(round((y2 - y1) * INSET))
    return y1 + inset, y2 - inset


def channelColumns(frame, reference):
    # Align the ROI columns to the stored nm grid: the stored spectrum has one bin per ROI column, so find the
    # x-window of the same width whose max-channel profile best matches the stored (still gamma-encoded) shape.
    yLo, yHi = roiBand(frame)
    band = frame[yLo:yHi, :, :]
    nms = sorted(reference)
    width = len(nms)
    profile = np.median(band.max(axis=2), axis=0)
    best, bestScore = 0, -2.0
    stored = np.array([reference[nm] for nm in nms])
    for x1 in range(0, frame.shape[1] - width, 4):
        window = profile[x1:x1 + width]
        if window.std() == 0:
            continue
        score = float(np.corrcoef(window, stored)[0, 1])
        if score > bestScore:
            best, bestScore = x1, score
    columns = band[:, best:best + width, :]
    red = np.median(columns[:, :, 0], axis=0)
    green = np.median(columns[:, :, 1], axis=0)
    blue = np.median(columns[:, :, 2], axis=0)
    return nms, red, green, blue, bestScore


def binned(nms, values, low, high):
    selected = [v for nm, v in zip(nms, values) if low <= nm < high]
    return float(np.mean(selected)) if selected else float("nan")


def main(names):
    runs = []
    for name in names:
        reference, frame = load(name)
        nms, red, green, blue, score = channelColumns(frame, reference)
        runs.append(dict(name=name, nms=nms, r=red, g=green, b=blue, score=score))
        print("%s: frame %dx%d, ROI aligned (corr %.3f)" % (name, frame.shape[1], frame.shape[0], score))

    run = runs[0]
    print("\n=== the BLANK, per colour channel, in raw camera DN (run %s) ===" % run["name"])
    print("%10s %8s %8s %8s   %8s  %s" % ("nm", "R", "G", "B", "max", "winner"))
    for low in range(440, 630, 10):
        r, g, b = (binned(run["nms"], run[k], low, low + 10) for k in ("r", "g", "b"))
        winner = {r: "RED", g: "GREEN", b: "BLUE"}[max(r, g, b)]
        print("%10s %8.1f %8.1f %8.1f   %8.1f  %s" % ("%d-%d" % (low, low + 10), r, g, b, max(r, g, b), winner))

    if len(runs) > 1:
        a, b = runs[0], runs[1]
        print("\n=== per-channel CHANGE between the two blanks (B/A, raw DN) ===")
        print("%10s %8s %8s %8s   %8s" % ("nm", "R", "G", "B", "max"))
        for low in range(440, 630, 10):
            line = []
            for channel in ("r", "g", "b"):
                va, vb = binned(a["nms"], a[channel], low, low + 10), binned(b["nms"], b[channel], low, low + 10)
                line.append(vb / va if va else float("nan"))
            maxA = max(binned(a["nms"], a[c], low, low + 10) for c in ("r", "g", "b"))
            maxB = max(binned(b["nms"], b[c], low, low + 10) for c in ("r", "g", "b"))
            print("%10s %8.3f %8.3f %8.3f   %8.3f" % ("%d-%d" % (low, low + 10), line[0], line[1], line[2],
                                                      maxB / maxA if maxA else float("nan")))
        print("\n=== whole-channel level (a WB / gain shift moves channels differently) ===")
        for channel, label in (("r", "RED"), ("g", "GREEN"), ("b", "BLUE")):
            va = float(np.mean(a[channel]))
            vb = float(np.mean(b[channel]))
            print("   %-6s run A %7.2f DN | run B %7.2f DN | B/A %.4f" % (label, va, vb, vb / va))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["NowSteirerkraftA", "NowSteirerkraftB"]))
