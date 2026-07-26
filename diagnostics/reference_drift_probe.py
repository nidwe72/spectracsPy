"""Is the BLANK actually drifting, and if so — lamp or camera? (SPEC_capture_quality.md §16.7, open question.)

Two archived blanks five minutes apart differed by ~5% in phosphor/pump, which was enough to swing the pigment
ratio by 20-28%. That is a fact about those two captures; it is NOT proof of a continuous drift, and Edwin's
later captures looked stable. This probe settles it by MEASURING THE TIME COURSE instead of inferring it from two
points.

Design (the discriminators are built in):
  * EXPOSURE IS FIXED for the whole run — auto-exposure once at the start, then frozen. Otherwise AE silently
    compensates a dimming lamp and the drift hides in the exposure value instead of the spectrum.
  * Every sample logs the camera's own settings (exposure / WB / auto-WB / gain). If those move, the cause is the
    CAMERA (a bug — DevCaptureVideoThread pins 6500 K, AUTO_WB=0); if they hold and the spectrum still tilts, the
    cause is the LAMP.
  * The headline number is PHOSPHOR/PUMP: the blue InGaN pump (440-490) and the phosphor emission (500-630) of a
    white LED respond differently to junction heating, so their RATIO isolates a lamp effect from anything that
    scales the whole frame.
  * Per-sample frame spread is reported too — that is Edwin's "grey outliers" (§14.8 C1 dim-frame rejection).

NOTHING IS WRITTEN and no app state is touched; it only reads frames. The app must NOT be running (it holds the
camera through the warm-keeper lease — close it first, or this will fail with a device-busy error).

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/reference_drift_probe.py --minutes 12 --every 30
"""
import argparse
import os
import sys
import time

import numpy as np

PUMP = (440.0, 490.0)          # blue InGaN pump — what auto-exposure pins
PHOSPHOR = (500.0, 630.0)      # phosphor emission — what thermal quenching attacks
QBAND = (560.0, 580.0)         # the pigment ratio's denominator (§16.8: the fragile one)


def _appContext():
    """ROI + px->nm cubic + device index from the app's own settings (same as the M0 probe)."""
    from capture_quality_probe import _try_app_context
    return _try_app_context()


def _spectrum(image, roi, coefficients, inset=0.2):
    """The app's reduction: gamma-decode the ROI band, max-channel, median over rows -> {nm: linear value}."""
    from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
    from PySide6.QtGui import QImage

    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height = converted.width(), converted.height()
    frame = np.frombuffer(converted.constBits(), np.uint8).reshape(height, converted.bytesPerLine())
    frame = frame[:, :width * 3].reshape(height, width, 3)

    x1, y1, x2, y2 = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
    yLow, yHigh = min(y1, y2), max(y1, y2)
    pad = int(round((yHigh - yLow) * inset))
    band = frame[yLow + pad:yHigh - pad, x1:min(x2, width), :]

    linear = SpectralColorUtil().decodeGammaArray(band)
    columns = np.median(linear.max(axis=2), axis=0)
    polynomial = np.poly1d(coefficients)
    nanometers = polynomial(np.arange(x1, x1 + len(columns)))
    return nanometers, columns


def _bandMean(nanometers, values, low, high):
    selected = values[(nanometers >= low) & (nanometers <= high)]
    return float(np.mean(selected)) if selected.size else float("nan")


def _pickExposure(backend, candidates=(4, 8, 16, 32, 64, 128, 256), ceiling=245.0):
    """Pick an exposure ONCE the way the app's AE does — brightest whose channel peak stays under the no-clip
    ceiling — then it is pinned for the whole run. Drift must show up in the SPECTRUM, never in the exposure."""
    measured = {}
    for candidate in candidates:
        backend.setExposure(candidate)
        for _ in range(6):                      # drain: the ELP needs a beat for an exposure change to land
            backend.read()
        image = backend.read()
        if image is None:
            continue
        from PySide6.QtGui import QImage
        converted = image.convertToFormat(QImage.Format.Format_RGB888)
        width, height = converted.width(), converted.height()
        frame = np.frombuffer(converted.constBits(), np.uint8).reshape(height, converted.bytesPerLine())
        frame = frame[:, :width * 3].reshape(height, width, 3)
        measured[candidate] = float(np.percentile(frame.max(axis=2), 99.9))
        print("   exposure %4d -> channel peak %6.1f" % (candidate, measured[candidate]))
    below = [(e, b) for e, b in measured.items() if b <= ceiling]
    chosen = max(below, key=lambda item: item[1])[0] if below else min(measured, key=measured.get)
    backend.setExposure(chosen)
    for _ in range(10):
        backend.read()
    print("   -> pinned at exposure %d\n" % chosen)
    return chosen


def main():
    parser = argparse.ArgumentParser(description="Blank/reference drift time-course (SPEC_capture_quality §16.7)")
    parser.add_argument("--minutes", type=float, default=12.0, help="total duration")
    parser.add_argument("--every", type=float, default=30.0, help="seconds between samples")
    parser.add_argument("--frames", type=int, default=10, help="frames averaged per sample")
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None,
                        help="fix the exposure (default: pick once by sweep, then pin)")
    parser.add_argument("--roi", default=None, help="X1,Y1,X2,Y2 (default: app context)")
    parser.add_argument("--coeffs", default=None, help="A,B,C,D px->nm cubic (default: app context)")
    arguments = parser.parse_args()

    context = _appContext()
    device = arguments.device if arguments.device is not None else context.get("device", 0)
    roi = [int(v) for v in arguments.roi.split(",")] if arguments.roi else context.get("roi")
    coefficients = ([float(v) for v in arguments.coeffs.split(",")] if arguments.coeffs
                    else context.get("coeffs"))
    if roi is None or coefficients is None:
        print("ERROR: no ROI / calibration cubic in the app context — calibrate first, or pass them explicitly.")
        return 2
    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    # Mirror DevCaptureVideoThread: 6500 K fixed white balance, gain pinned, FIXED exposure for the whole run.
    exposure = arguments.exposure if arguments.exposure is not None else context.get("exposure")
    backend.open(deviceId=device, exposure=exposure or 150, whiteBalanceKelvin=6500)
    if exposure is None:
        exposure = _pickExposure(backend)
    print("camera %s at %s, exposure PINNED at %s, WB 6500 K\n" % (device, backend.getResolution(), exposure))

    print("%8s %9s %9s %9s %10s %9s %9s  %s"
          % ("t (s)", "pump", "phosphor", "ph/pump", "vs first", "Q 560-80", "peak DN", "camera settings"))
    samples = []
    started = time.time()
    deadline = started + arguments.minutes * 60.0
    first = None
    while time.time() < deadline:
        stack = []
        for index in range(arguments.frames):
            if index:
                time.sleep(0.7)     # at 2592x1944 the ELP delivers ~1.5 fps — without this we re-read one frame
            image = backend.read()
            if image is None:
                continue
            nanometers, values = _spectrum(image, roi, coefficients)
            stack.append(values)
        if not stack:
            print("  (no frames)")
            time.sleep(arguments.every)
            continue
        stack = np.array(stack)
        values = np.median(stack, axis=0)
        # Frame spread = Edwin's "grey outliers": how far the dimmest frame sits below the median frame.
        brightness = np.median(stack, axis=1)
        spread = (brightness.max() - brightness.min()) / np.median(brightness) * 100.0

        pump = _bandMean(nanometers, values, *PUMP)
        phosphor = _bandMean(nanometers, values, *PHOSPHOR)
        ratio = phosphor / pump if pump else float("nan")
        first = ratio if first is None else first
        settings = backend.readCameraSettings() or {}
        elapsed = time.time() - started
        print("%8.0f %9.2f %9.2f %9.4f %9.2f%% %9.2f %9.1f  exp=%s wb=%s autoWb=%s gain=%s  [frame spread %.1f%%]"
              % (elapsed, pump, phosphor, ratio, (ratio / first - 1) * 100,
                 _bandMean(nanometers, values, *QBAND), values.max(),
                 settings.get("exposure"), settings.get("wbTemperature"), settings.get("autoWb"),
                 settings.get("gain"), spread))
        samples.append((elapsed, ratio, pump, phosphor))
        time.sleep(max(0.0, arguments.every - (time.time() - started - elapsed)))

    backend.release()

    if len(samples) < 3:
        print("\nnot enough samples to judge")
        return 0
    ratios = np.array([s[1] for s in samples])
    pumps = np.array([s[2] for s in samples])
    total = (ratios[-1] / ratios[0] - 1) * 100.0
    print("\n=== verdict ===")
    print("  phosphor/pump: first %.4f -> last %.4f  (%+.2f%%), peak-to-peak %.2f%%"
          % (ratios[0], ratios[-1], total, (ratios.max() - ratios.min()) / ratios.mean() * 100))
    print("  pump level   : %+.2f%% over the run (a LAMP droop moves phosphor/pump; a camera GAIN change moves both)"
          % ((pumps[-1] / pumps[0] - 1) * 100))
    half = len(ratios) // 2
    print("  first half %.4f vs second half %.4f -> %s"
          % (ratios[:half].mean(), ratios[half:].mean(),
             "SETTLING (drift decays)" if abs(ratios[half:].std()) < abs(ratios[:half].std())
             else "NOT settling — drift continues or is episodic"))
    print("\n  Reference: the two archived blanks differed by 5.04%% in phosphor/pump, which swung the pigment")
    print("  ratio 20-28%%. If this run stays within ~1%%, those two captures were an EVENT, not a steady drift —")
    print("  and the R->S->R' bracket (§16.7) is the right guard rather than a warm-up wait.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
