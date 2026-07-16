#!/usr/bin/env python3
"""STANDALONE unit test for the color-constrained calibration anchor fix (SPEC_capture_quality.md §4.9).

Does NOT touch the app. It captures the real CFL spectrum, then runs the SAME wavelength-calibration line sequence the
app uses (SpectrometerWavelengthCalibrationLogicModule) but with ONE change: the green anchor is picked as the most
prominent GREEN-hued peak instead of the most prominent peak overall — so the sharp Europium RED line can no longer be
mislabelled as green. It marks every found line on the spectrum + on the ROI band image so the result can be checked
by eye (AI + human), and prints a table of found-vs-expected wavelengths.

If the lines land correctly here, we port the color constraint into the app.

    PYTHONPATH=... ./venv/bin/python diagnostics/calibration_fix_test.py     # CFL lamp ON
"""
import math
import os
import sys
import time
import numpy as np

ROI = (558, 902, 2191, 1785)   # the app's FRESH ROI detection (camera moved; stored 665,794,2226,1658 was stale)
COEFFS = [-6.72651743127379e-09, 2.68123787138496e-05, 0.115548014949371, 318.141502522378]
EXPOSURE = 150
OUTDIR = os.environ.get("CALIB_FIX_OUT", "/tmp/claude-1000/calib_fix")
# Standard fixture frame — kept in the UN-VERSIONED sibling references tree (persists, not in git):
DEFAULT_FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "spectracs-references", "unitTests", "spectracsPy", "cfl_2592.png")
DISTANCE, WIDTH = 3, 3                                    # same as the app's find_peaks

# expected anchor wavelengths (nm) — for the found-vs-expected table
EXPECTED = {"green": 546.5, "green_left": 542.4, "red(Eu)": 611.6, "violet": 435.8, "blue": 435.8, "aqua": 487.7}


def detect_roi(qimage):
    """Run the REAL app ROI detection (Hough horizontal band edges + column-brightness vertical bounds) on the live
    frame. Returns (x1, y1, x2, y2) or None on failure (caller falls back)."""
    try:
        from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerRegionOfInterestLogicModule \
            import SpectrometerRegionOfInterestLogicModule
        from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal \
            import SpectrometerCalibrationProfileHoughLinesVideoSignal
        roi = SpectrometerRegionOfInterestLogicModule()
        vs = SpectrometerCalibrationProfileHoughLinesVideoSignal()
        vs.image = qimage
        houghLines = roi.getHorizontalBoundingLines(vs)          # [upperLine, lowerLine]
        if not houghLines or len(houghLines) < 2:
            return None
        vs.upperHoughLine, vs.lowerHoughLine = houghLines[0], houghLines[1]
        roi.getVerticalBoundingLines(vs)                          # sets left/rightBoundingLine
        x1 = vs.leftBoundingLine.p1().x()
        x2 = vs.rightBoundingLine.p1().x()
        ys = [vs.upperHoughLine.p1().y(), vs.upperHoughLine.p2().y(),
              vs.lowerHoughLine.p1().y(), vs.lowerHoughLine.p2().y()]
        y1, y2 = min(ys), max(ys)
        if x2 <= x1 or y2 <= y1:
            return None
        return (int(x1), int(y1), int(x2), int(y2))
    except Exception as exc:
        print("  ROI detection failed (%s)" % exc)
        return None


def qimage_to_rgb(q):
    q = q.convertToFormat(q.Format.Format_RGB888)
    w, h = q.width(), q.height()
    arr = np.frombuffer(q.constBits(), np.uint8).reshape(h, q.bytesPerLine())[:, : w * 3]
    return arr.reshape(h, w, 3).copy()


# --- COMBINED colour model (SPEC_capture_quality.md §13.4): soft hue-similarity SELECTOR (physics-grounded via
#     wavelengthToColor) + per-channel dominance GUARD/CONFIDENCE. No hard-coded hue intervals. ---
LINE_NM = {"violet": 404.7, "blue": 435.8, "aqua": 487.7, "green": 546.5, "green_left": 542.4, "red(Eu)": 611.6}


def drain(backend, milliseconds):
    """Actively read+discard frames for `milliseconds` of wall-clock so an exposure change turns over and stale
    buffered frames flush (mirrors diagnostics/capture_quality_probe.drain and VideoThread.__drainSync). Returns
    the last good frame."""
    end = time.monotonic() + milliseconds / 1000.0
    last = backend.read()
    while time.monotonic() < end:
        frame = backend.read()
        if frame is not None:
            last = frame
    return last


def auto_expose(backend, min_exposure=2, max_exposure=500):
    """Synchronous auto-exposure on the rig — the SAME method the app's VideoThread now uses (SPEC §14.6): a
    warm-up drain to transition off the open() exposure, then per-probe setExposure + STABILIZE-drain (drain in
    chunks until the channel peak stops changing, so a big jump is fully applied before we read it) + the
    per-channel peak metric (keeps every channel below the 255 clip so no line saturates to white), with the
    direction-agnostic AutoExposureLogicModule choosing the winner. Mirrors a real acquisition — no hard-coded
    exposure."""
    from sciens.spectracs.logic.application.video.capture.AutoExposureLogicModule import AutoExposureLogicModule

    def measure(exposure):
        backend.setExposure(exposure)
        peak = AutoExposureLogicModule.channelPeak(drain(backend, 1800))  # drain past the ~1.5 s settle
        print("  [auto-exposure] exp=%3d -> channel peak %.1f" % (exposure, peak))
        return peak

    best = AutoExposureLogicModule().findExposure(measure, min_exposure, max_exposure)
    backend.setExposure(best)
    drain(backend, 600)
    print("  [auto-exposure] chosen exposure = %d" % best)
    return best


def load_frame(image_path, exposure, save_path):
    """Get a QImage frame + the exposure it was captured at. Replay a saved PNG (--image, deterministic / CI) or
    capture live from the rig — auto-exposing when no fixed --exposure was given (mirrors a real acquisition)."""
    from PySide6.QtGui import QImage
    if image_path:
        qimg = QImage(image_path)
        if qimg.isNull():
            raise SystemExit("could not load --image %s" % image_path)
        print("  REPLAY saved frame: %s (%dx%d)" % (image_path, qimg.width(), qimg.height()))
        return qimg, None
    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    backend.open(deviceId=0, exposure=(exposure if exposure is not None else EXPOSURE))
    try:
        used = exposure if exposure is not None else auto_expose(backend)  # fixed --exposure, else auto-expose
        for _ in range(12):
            backend.read()
        qimg = backend.read()
    finally:
        backend.release()
    if qimg is None:
        raise SystemExit("camera returned no frame")
    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        qimg.save(save_path)
        print("  saved captured frame -> %s   (replay it with:  --replay)" % save_path)
    return qimg, used


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Calibration line-detection UNIT TEST (live rig, or saved-frame replay)")
    ap.add_argument("--replay", action="store_true",
                    help="replay the standard fixture deterministically (no camera): %s" % DEFAULT_FIXTURE)
    ap.add_argument("--image", help="replay a SPECIFIC saved frame PNG instead of capturing")
    ap.add_argument("--save-frame", dest="save_frame", nargs="?", const=DEFAULT_FIXTURE,
                    help="capture live and SAVE the raw frame as a fixture (default: the standard path), then run")
    ap.add_argument("--exposure", type=int, default=None,
                    help="force a FIXED exposure for live capture (skip auto-exposure); default: auto-expose")
    args = ap.parse_args()
    image = args.image or (DEFAULT_FIXTURE if args.replay else None)

    os.makedirs(OUTDIR, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv[:1])
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    qimg, used_exposure = load_frame(image, args.exposure, args.save_frame)
    exposure_label = "replay" if used_exposure is None else str(used_exposure)

    detected = detect_roi(qimg)                                  # <-- REAL app ROI detection on the live frame
    if detected:
        print("  ROI DETECTED (real Hough + column-brightness): %s   [stored/app ref: %s]" % (detected, ROI))
        x1, y1, x2, y2 = detected
    else:
        print("  ROI detection failed -> fallback ROI %s" % (ROI,))
        x1, y1, x2, y2 = ROI
    yc = (y1 + y2) // 2

    rgb = qimage_to_rgb(qimg)
    h, w = rgb.shape[:2]
    ex2 = min(x2, w)
    cols = np.arange(x1, ex2)
    nm = np.polyval(COEFFS, cols)

    row_rgb = rgb[min(yc, h - 1), x1:ex2, :].astype(np.float64)                 # centre-row RGB
    gray = ((11 * row_rgb[:, 0] + 16 * row_rgb[:, 1] + 5 * row_rgb[:, 2]) // 32)
    intensities = gray.astype(np.float32)

    # DRY: build a Spectrum from the extracted row and call the SAME detection the app uses —
    # WavelengthLineDetectionLogicModule (single source of truth). Spectrum is keyed by array index (0..N-1) so a
    # returned pixelIndex indexes straight into cols[]/nm[].
    from PySide6.QtGui import QColor
    from sciens.spectracs.model.spectral.Spectrum import Spectrum
    from sciens.spectracs.logic.spectral.acquisition.device.calibration.WavelengthLineDetectionLogicModule import \
        WavelengthLineDetectionLogicModule
    from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import \
        SpectralLineMasterDataColorName as Name
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({i: float(intensities[i]) for i in range(len(intensities))})
    spectrum.setColorsByPixelIndices({i: QColor.fromRgb(int(row_rgb[i, 0]), int(row_rgb[i, 1]), int(row_rgb[i, 2]))
                                      for i in range(len(cols))})
    detected = WavelengthLineDetectionLogicModule().detect(spectrum)
    NAME_MAP = {Name.MERCURY_FRENCH_VIOLET: "violet", Name.MERCURY_BLUE: "blue", Name.TERBIUM_AQUA: "aqua",
                Name.MERCURY_MANGO_GREEN_LEFT: "green_left", Name.MERCURY_MANGO_GREEN: "green",
                Name.EUROPIUM_VIVID_GAMBOGE: "red(Eu)"}
    lines, conf = {}, {}
    for enumName, dl in detected.items():
        key = NAME_MAP.get(enumName)
        if key:
            lines[key] = int(dl.pixelIndex)
            conf[key] = (dl.hueScore, dl.chanScore)
    err = None if "green" in lines else "NO GREEN PEAK"

    # --- report table ---
    print("Output:", OUTDIR, "| frame %dx%d | exposure %s" % (w, h, exposure_label))
    if err:
        print("!! " + err)
    print("  line        found_col  found_nm  target_nm  hueScore  chanScore  (selector: colour-gated / *prominence)")
    line_color = {"violet": "violet", "blue": "blue", "aqua": "cyan", "green": "green",
                  "green_left": "darkgreen", "red(Eu)": "red"}
    for name in ["violet", "blue", "aqua", "green_left", "green", "red(Eu)"]:
        if name in lines:
            p = lines[name]
            hs, cs = conf.get(name, (0.0, 0.0))
            sel = "*prominence" if name == "red(Eu)" else "colour"
            print("  %-10s  %8d  %7.1f   %8.1f     %.2f      %.2f     %s"
                  % (name, cols[p], nm[p], LINE_NM.get(name, float("nan")), hs, cs, sel))
        else:
            print("  %-10s  (not found)" % name)

    # --- spectrum plot with found lines ---
    plt.figure(figsize=(12, 4.5))
    plt.plot(nm, intensities, color="0.35", lw=0.8)
    for name, p in lines.items():
        plt.axvline(nm[p], color=line_color.get(name, "black"), lw=1.4)
        plt.text(nm[p], intensities.max() * (0.98 if name != "green_left" else 0.80), "%s\n%.1f" % (name, nm[p]),
                 rotation=90, va="top", ha="right", fontsize=8, color=line_color.get(name, "black"))
    plt.xlabel("wavelength (nm) via stored cubic"); plt.ylabel("intensity (qGray)")
    plt.title("Color-constrained line detection (exp=%s) — found lines marked" % exposure_label)
    plt.savefig(os.path.join(OUTDIR, "lines_spectrum.png"), dpi=120, bbox_inches="tight"); plt.close()

    # --- REFIT: assign each detected line its TARGET wavelength (resource/expectedDetection.png) and fit a new
    #     cubic. A good, monotonic fit with small residuals == the detection calibrates correctly. ---
    TARGET = {"violet": 404.7, "blue": 435.8, "aqua": 487.7, "green": 546.5, "green_left": 542.4, "red(Eu)": 611.6}
    fit_cols = [float(cols[lines[n]]) for n in lines]
    fit_nm = [TARGET[n] for n in lines]
    deg = min(3, len(fit_cols) - 1)
    mono, max_resid = False, float("inf")
    if deg >= 1:
        coeffs_new = np.polyfit(fit_cols, fit_nm, deg)
        pred = np.polyval(coeffs_new, fit_cols)
        resid = np.array(fit_nm) - pred
        new_nm = np.polyval(coeffs_new, cols)
        mono = bool(np.all(np.diff(new_nm) > 0))
        max_resid = float(np.max(np.abs(resid)))
        print("\nREFIT (deg %d) from %d detected lines -> residuals (nm):" % (deg, len(fit_cols)))
        for n, r in zip(lines, resid):
            print("  %-10s target %.1f  residual %+.2f" % (n, TARGET[n], r))
        print("  max |residual| = %.2f nm | monotonic axis: %s" % (np.max(np.abs(resid)), mono))

        # spectrum on the REFITTED axis, with the app's reference targets overlaid
        plt.figure(figsize=(12, 4.5))
        plt.plot(new_nm, intensities, color="0.35", lw=0.8)
        for tnm, tname in [(405, "405"), (436, "436"), (487, "487"), (546, "546"), (611, "611")]:
            plt.axvline(tnm, color="white", ls="--", lw=1.2)
            plt.text(tnm, intensities.max() * 0.98, tname, rotation=90, va="top", ha="right", fontsize=8, color="0.2")
        for name, p in lines.items():
            plt.axvline(new_nm[p], color=line_color.get(name, "black"), lw=1.4, alpha=0.7)
        plt.xlabel("wavelength (nm) — REFITTED from detected lines"); plt.ylabel("intensity")
        plt.title("Refit check: detected lines (color) vs app targets (white dashed 405/436/487/546/611)")
        plt.savefig(os.path.join(OUTDIR, "refit_vs_target.png"), dpi=120, bbox_inches="tight"); plt.close()

    # --- ANNOTATED captured band: found lines painted ON the real color spectrum, labelled name + target nm ---
    TARGET = {"violet": 404.7, "blue": 435.8, "aqua": 487.7, "green": 546.5, "green_left": 542.4, "red(Eu)": 611.6}
    band = rgb[y1:min(y2, h), x1:ex2, :]
    bh = band.shape[0]
    plt.figure(figsize=(14, 5))
    plt.imshow(band, aspect="auto")
    order = sorted(lines.items(), key=lambda kv: kv[1])
    for i, (name, p) in enumerate(order):
        col = line_color.get(name, "white")
        plt.axvline(p, color=col, lw=1.6)
        # stagger labels vertically so a collision (two lines on one feature) is readable
        ytxt = bh * (0.04 + 0.16 * (i % 4))
        plt.annotate("%s\n(-> %.0f nm)\ncol %d" % (name, TARGET.get(name, 0), cols[p]),
                     xy=(p, ytxt), xytext=(p + 12, ytxt), color=col, fontsize=9, fontweight="bold",
                     va="top", bbox=dict(boxstyle="round,pad=0.2", fc="black", ec=col, alpha=0.6))
    # wavelength ruler along the bottom (old cubic — approximate, ~10 nm low, just for orientation)
    ticks_nm = [420, 440, 460, 480, 500, 520, 540, 560, 580, 600, 620]
    tick_cols = [int(np.interp(t, nm, np.arange(len(nm)))) for t in ticks_nm if nm.min() <= t <= nm.max()]
    plt.xticks(tick_cols, [str(t) for t in ticks_nm if nm.min() <= t <= nm.max()])
    plt.xlabel("wavelength (nm, old cubic — approximate)")
    plt.yticks([])
    plt.title("Captured CFL band with detected lines painted (name -> target wavelength)")
    plt.savefig(os.path.join(OUTDIR, "painted_band.png"), dpi=130, bbox_inches="tight"); plt.close()
    print("\nWrote lines_spectrum.png + painted_band.png (+ refit_vs_target.png) to", OUTDIR)

    # ==================== ASSERTIONS (unit-test pass/fail; exit code 0/1) ====================
    REQUIRED = ["violet", "blue", "aqua", "green_left", "green", "red(Eu)"]
    MAX_RESIDUAL_NM = 2.0
    checks = []
    checks.append(("all 6 lines found",
                   all(n in lines for n in REQUIRED),
                   "missing: %s" % [n for n in REQUIRED if n not in lines]))
    present = [n for n in REQUIRED if n in lines]
    ordered_cols = [int(cols[lines[n]]) for n in present]
    checks.append(("lines in ascending wavelength order",
                   ordered_cols == sorted(ordered_cols),
                   "%s -> cols %s" % (present, ordered_cols)))
    checks.append(("refit axis monotonic", mono, ""))
    checks.append(("refit max |residual| < %.1f nm" % MAX_RESIDUAL_NM,
                   max_resid < MAX_RESIDUAL_NM, "%.2f nm" % max_resid))
    # green must be a GREEN peak, not the (much brighter) Eu red — the original regression:
    checks.append(("green anchor left of Eu red",
                   ("green" in lines and "red(Eu)" in lines and lines["green"] < lines["red(Eu)"]), ""))

    print("\n==================== UNIT TEST ====================")
    passed = True
    for name, ok, detail in checks:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  (%s)" % detail) if detail else ""))
        passed = passed and ok
    print("RESULT: %s" % ("PASS ✔" if passed else "FAIL ✗"))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
