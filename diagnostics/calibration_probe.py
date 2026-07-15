#!/usr/bin/env python3
"""Calibration diagnostic — capture the CFL lamp from the REAL camera and save images so the wavelength-calibration
peak detection can be inspected directly (SPEC_capture_quality.md — peak-detection regression debug).

Reproduces the calibration's extraction (single ROI centre row, qGray per column) and its find_peaks call, at several
exposures, and writes PNGs: the raw frame (downscaled), the ROI band crop, and the 1-D spectrum with the peaks
find_peaks detects vs the EXPECTED Hg/Eu line positions (from the stored cubic). Run on the rig with the CFL lamp ON.

    diagnostics/probe.sh  # (uses the app PYTHONPATH) -- or:
    PYTHONPATH=... ./venv/bin/python diagnostics/calibration_probe.py
"""
import os
import sys
import numpy as np

# Stored calibration profile (masterUserExakta / ELP), authored at 2592x1944:
ROI = (665, 794, 2226, 1658)                     # x1, y1, x2, y2
COEFFS = [-6.72651743127379e-09, 2.68123787138496e-05, 0.115548014949371, 318.141502522378]  # px->nm cubic A,B,C,D
EXPOSURES = [8, 64, 150, 500]
# Known CFL/Hg-Eu anchor lines the calibration looks for (nm):
EXPECTED_NM = {"Hg violet": 435.8, "Hg blue": 435.8, "Tb aqua": 487.7, "Hg green": 546.5,
               "Hg green-left": 542.4, "Eu red": 611.6}
OUTDIR = os.path.join(os.environ.get("CALIB_PROBE_OUT", "/tmp/claude-1000/calib_probe"))


def qimage_to_rgb(qimage):
    qimage = qimage.convertToFormat(qimage.Format.Format_RGB888)
    w, h = qimage.width(), qimage.height()
    ptr = qimage.constBits()
    arr = np.frombuffer(ptr, np.uint8).reshape(h, qimage.bytesPerLine())[:, : w * 3]
    return arr.reshape(h, w, 3).copy()


def qgray(rgb):
    rgb = rgb.astype(np.uint32)
    return ((11 * rgb[..., 0] + 16 * rgb[..., 1] + 5 * rgb[..., 2]) // 32).astype(np.uint8)


def most_prominent_peaks(intensities, count, distance=3, width=3):
    """Replicate SpectralLinesSelectionLogicModule.__selectByProminence: raise the prominence threshold until <=count
    peaks remain. Returns (peaks_at_that_threshold, threshold, all_low_prominence_peaks)."""
    from scipy.signal import find_peaks
    allpeaks, _ = find_peaks(intensities, distance=distance, width=width, rel_height=0.5, prominence=1)
    chosen, thr = allpeaks, 1
    for candidate in range(1, 255):
        peaks, _ = find_peaks(intensities, distance=distance, width=width, rel_height=0.5, prominence=candidate)
        if len(peaks) <= count:
            chosen, thr = peaks, candidate
            break
    return chosen, thr, allpeaks


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv[:1])
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sciens.spectracs.logic.appliction.video.capture.CaptureBackend import getCaptureBackend

    x1, y1, x2, y2 = ROI
    yc = (y1 + y2) // 2
    cols = np.arange(x1, x2)
    nm = np.polyval(COEFFS, cols)

    backend = getCaptureBackend()
    backend.open(deviceId=0, exposure=EXPOSURES[0])
    print("Output dir:", OUTDIR)
    try:
        for i, ev in enumerate(EXPOSURES):
            backend.setExposure(ev)
            for _ in range(12):                          # wall-clock-ish settle (buffersize=1 keeps frames fresh)
                backend.read()
            qimg = backend.read()
            if qimg is None:
                print("exp %d: no frame" % ev); continue
            rgb = qimage_to_rgb(qimg)
            h, w = rgb.shape[:2]
            gray = qgray(rgb)

            # extract the centre-row spectrum (exactly what ImageSpectrumAcquisitionLogicModule reads) + band-mean
            ex2 = min(x2, w); eyc = min(yc, h - 1)
            row = gray[eyc, x1:ex2].astype(np.float64)
            band = gray[y1:min(y2, h), x1:ex2].astype(np.float64)
            band_mean = band.mean(axis=0)
            axis_nm = nm[: len(row)]

            peaks, thr, allpeaks = most_prominent_peaks(row.astype(np.float32), count=1)

            print("exp %3d | frame %dx%d | row: min %.0f max %.0f mean %.0f | peaks@prom1=%d, anchor@prom%d=%d"
                  % (ev, w, h, row.min(), row.max(), row.mean(), len(allpeaks), thr, len(peaks)))

            # --- save the raw frame (downscaled) + ROI band once (at a mid exposure) ---
            if i == len(EXPOSURES) // 2:
                small = rgb[::3, ::3]
                plt.figure(figsize=(8, 6)); plt.imshow(small)
                plt.axhline(eyc // 3, color="cyan", lw=0.6); plt.title("raw frame exp=%d (cyan=extraction row)" % ev)
                plt.savefig(os.path.join(OUTDIR, "raw.png"), dpi=110, bbox_inches="tight"); plt.close()
                plt.figure(figsize=(10, 2.5)); plt.imshow(band, aspect="auto", cmap="gray")
                plt.title("ROI band exp=%d (y %d-%d)" % (ev, y1, y2)); plt.savefig(
                    os.path.join(OUTDIR, "roi_band.png"), dpi=110, bbox_inches="tight"); plt.close()

            # --- spectrum plot with detected + expected lines ---
            plt.figure(figsize=(11, 4))
            plt.plot(axis_nm, row, color="0.4", lw=0.8, label="centre-row (extractor)")
            plt.plot(axis_nm[: len(band_mean)], band_mean, color="tab:blue", lw=1.0, label="band-mean")
            for p in allpeaks:
                if p < len(axis_nm):
                    plt.axvline(axis_nm[p], color="orange", lw=0.4, alpha=0.5)
            for p in peaks:
                if p < len(axis_nm):
                    plt.axvline(axis_nm[p], color="red", lw=1.2)
            for name, wnm in EXPECTED_NM.items():
                plt.axvline(wnm, color="green", ls="--", lw=0.8)
                plt.text(wnm, row.max() * 0.95, name, rotation=90, fontsize=7, color="green", va="top")
            plt.xlabel("wavelength (nm)"); plt.ylabel("intensity (qGray)")
            plt.title("exp=%d  | orange=all peaks, red=anchor(prom%d), green dashed=expected lines" % (ev, thr))
            plt.legend(loc="upper right", fontsize=8)
            plt.savefig(os.path.join(OUTDIR, "spectrum_exp%03d.png" % ev), dpi=110, bbox_inches="tight"); plt.close()
    finally:
        backend.release()
    print("\nWrote: raw.png, roi_band.png, spectrum_exp{008,064,150,500}.png in", OUTDIR)


if __name__ == "__main__":
    main()
