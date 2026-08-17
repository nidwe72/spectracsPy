"""⭐⭐ THE SETTLING RUN — the bench's OWN algorithm, driven from a script.  (SPEC_settled_measurement.md §10.7)

WHAT MAKES THIS DIFFERENT FROM `clearing_time_course.py`. That script computes the metric itself and
decides for itself when a fill has settled. This one does neither: it asks the DEV plugin for a monitor
and pushes frames into it.

    monitor = DevSpectralPlugin().createMonitor(reference, mode=DIAGNOSTIC)
    row     = monitor.offer(frameSpectrum(image), time.monotonic())

⭐ NOTHING IN THAT LOOP KNOWS WHAT Q% IS. The gate, the branch, the vertex, the guards and the stop rule
are the plugin's — so this script measures THE ALGORITHM THE BENCH RUNS rather than a transcription of
it. §10.1a cost this project exactly that once already, at the level of constants; this is the same
lesson one level up, at the level of the algorithm.

⭐ THE DIVISION OF LABOUR (§10.7a): the SCRIPT owns the CAMERA — device, white balance, and an exposure
PINNED for the whole run, because auto-exposure would silently compensate the very clearing being
measured (§16.7). The PLUGIN owns the MEANING. The bench does its own AE sweep and must; a diagnostic
must not.

⭐ THE ONE ALGORITHMIC DIFFERENCE (§11.9c): this runs in DIAGNOSTIC mode, so it keeps observing after the
answer is read — the 20-minute arc §11 needs to measure the photodamage slope. That is safe only because
the answer is LATCHED (§14.6): later rows join the trajectory but can never become the answer.

⚠ EXPOSURE IS PINNED. ⚠ READ-ONLY: nothing is written to the app DB.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/settling_run.py --label heat_arm_a --minutes 20 --npz
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

from reference_drift_probe import _appContext, _pickExposure

from sciens.spectracs.plugin_sdk import MonitorMode
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

# ⭐ READ FROM THE PLUGIN, NEVER COPIED (§10.1a).
_PLUGIN = DevSpectralPlugin()
GUARD_BAND = _PLUGIN.DN_GUARD_BAND
GUARD_TARGET = (_PLUGIN.DN_TARGET_LOW, _PLUGIN.DN_TARGET_HIGH)


def installCalibrationProfile(roi, coefficients):
    """Put the ROI + px->nm cubic into the APP CONTEXT, because the app's per-frame extractor reads its
    calibration from that singleton rather than from arguments (§10.7b).

    ⭐ THIS IS WHAT MAKES THE ROWS COMPARABLE WITH THE BENCH. `diagnostics/_spectrum()` keeps the middle
    60 % of the ROI band (inset 0.2); the app's `ImageSpectrumAcquisitionLogicModule` keeps the middle
    33 % (Edwin's "filet piece", 2026-08-06). Same algorithm, different pixels, different numbers.
    ⛔ The old probes hardcode 0.2 ON PURPOSE — they must keep reproducing their published figures — so
    this script uses the app's extractor instead of repointing theirs.
    """
    from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
    from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
    from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
        SpectrometerCalibrationProfile

    calibration = SpectrometerCalibrationProfile()
    calibration.regionOfInterestX1, calibration.regionOfInterestY1 = int(roi[0]), int(roi[1])
    calibration.regionOfInterestX2, calibration.regionOfInterestY2 = int(roi[2]), int(roi[3])
    for name, value in zip("ABCD", coefficients):
        setattr(calibration, "interpolationCoefficient" + name, float(value))
    profile = SpectrometerProfile()
    profile.spectrometerCalibrationProfile = calibration
    ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(profile)
    return calibration


def frameSpectrum(image):
    """ONE camera frame -> {nm: value}, through the APP's own extractor (inset 1/3)."""
    from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import \
        ImageSpectrumAcquisitionLogicModule
    from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
        ImageSpectrumAcquisitionLogicModuleParameters
    from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

    signal = SpectralVideoThreadSignal()
    signal.image = image
    parameters = ImageSpectrumAcquisitionLogicModuleParameters()
    parameters.setVideoSignal(signal)
    parameters.spectrum = None
    spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
    frames = spectrum.getCapturedValuesByNanometers() if spectrum is not None else None
    return frames[-1] if frames else None


def captureReference(backend, frames):
    """The blank, captured through the SAME machinery — a MonitorEngine with a BurstEvaluator (§10.6).

    ⭐ So both captures in the run go down one path, and the script exercises the "a plain burst IS the
    degenerate monitor" claim simply by working."""
    from sciens.spectracs.plugin_sdk import BurstEvaluator, FrameRing, MonitorEngine, MonitorPolicy
    policy = MonitorPolicy(windowFrames=None, maxSeconds=600.0, maxFrames=frames * 4)
    monitor = MonitorEngine(BurstEvaluator(frames), FrameRing(None, None), policy)
    while not monitor.isFinished():
        image = backend.read()
        if image is None:
            continue
        frame = frameSpectrum(image)
        if frame is not None:
            monitor.offer(frame, time.monotonic())
    return monitor.result().spectrum


def guardDn(spectrum):
    """The app's CAPTURE-LOWDN number: darkest bin in the guard window, gamma-ENCODED.

    ⚠ The spectrum is LINEAR and the guard's thresholds live in ENCODED (camera) DN — §16.23.10b."""
    from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
    inside = [value for nm, value in spectrum.valuesByNanometers.items()
              if GUARD_BAND[0] <= nm <= GUARD_BAND[1]]
    if not inside:
        return None
    return SpectralColorUtil().encodeGammaFraction(max(0.0, float(min(inside))) / 255.0)


def main():
    parser = argparse.ArgumentParser(description="Monitored settling run, on the DEV plugin's own algorithm")
    parser.add_argument("--label", default="settling")
    parser.add_argument("--minutes", type=float, default=20.0, help="the ARC — ⚠ identical in every §11 arm")
    parser.add_argument("--frames", type=int, default=50, help="W, the evaluation window")
    parser.add_argument("--reference-frames", type=int, default=60)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None)
    parser.add_argument("--roi", default=None)
    parser.add_argument("--coeffs", default=None)
    parser.add_argument("--npz", action="store_true",
                        help="also dump every raw frame spectrum (⚠ written ONCE at the end — np.savez "
                             "cannot append, §25/X1)")
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args()

    context = _appContext() or {}
    device = arguments.device if arguments.device is not None else context.get("device", 0)
    roi = [int(v) for v in arguments.roi.split(",")] if arguments.roi else context.get("roi")
    coefficients = ([float(v) for v in arguments.coeffs.split(",")] if arguments.coeffs
                    else context.get("coeffs"))
    if roi is None or coefficients is None:
        print("ERROR: no ROI / calibration cubic — calibrate first, or pass --roi/--coeffs.")
        return 2
    installCalibrationProfile(roi, coefficients)

    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    exposure = arguments.exposure if arguments.exposure is not None else context.get("exposure")
    backend.open(deviceId=device, exposure=exposure or 150, whiteBalanceKelvin=6500)
    if arguments.exposure is None:
        exposure = _pickExposure(backend)
    print("camera %s at %s, exposure PINNED at %s, WB 6500 K\n" % (device, backend.getResolution(), exposure))

    input("   Insert the REFERENCE jar (isopropanol) and press Enter … ")
    reference = captureReference(backend, arguments.reference_frames)
    if reference is None:
        print("ERROR: no frames from the camera.")
        return 2
    print("   reference captured (%d frames)\n" % arguments.reference_frames)

    input("   Insert the SAMPLE jar and press Enter … ")
    # ⭐ DIAGNOSTIC: keep observing past the read, for the whole arc — the photodamage slope is the point
    # of §11, and the latch (§14.6) is what stops a late noise dip from stealing the answer.
    monitor = _PLUGIN.createMonitor(reference, mode=MonitorMode.DIAGNOSTIC, frames=arguments.frames)
    monitor.policy.maxSeconds = arguments.minutes * 60.0

    outDirectory = arguments.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "spectracs-references", "tmp",
        arguments.label)
    os.makedirs(outDirectory, exist_ok=True)
    csvPath = os.path.join(outDirectory, "settling_run.csv")

    rawFrames, rawTimes = [], []
    started = time.monotonic()
    csvFile = open(csvPath, "w", newline="")
    writer = csv.writer(csvFile)
    # ⚠ TWO time columns, and the difference matters (§10.7c): `tCentre` is the WINDOW CENTRE and lags the
    # last frame by half a window, so a reader who takes it for "when the line appeared" mis-times every
    # event. ⚠ `n` is here because a provisional row must never later be read as a full-window one.
    writer.writerow(["tCentre", "wallClock", "n", "nAccepted", "provisional", "decision",
                     "qPercent", "soret", "valley", "qBand", "guardDn"])
    print("%8s %6s %8s %9s %9s %9s %7s  %s"
          % ("t (min)", "n", "Q%", "A_Soret", "A_valley", "A_Q", "DN", "state"))
    print("   " + "-" * 88)

    lastPrinted = 0.0
    try:
        while not monitor.isFinished():
            image = backend.read()
            if image is None:
                continue
            frame = frameSpectrum(image)
            if frame is None:
                continue
            if arguments.npz:
                rawFrames.append(frame)
                rawTimes.append(time.monotonic() - started)
            row = monitor.offer(frame, time.monotonic())
            if row is None:
                continue
            digitalNumber = guardDn(row.spectrum) if getattr(row, "spectrum", None) is not None else None
            writer.writerow(["%.3f" % row.t, time.strftime("%H:%M:%S"), row.n, row.nAccepted,
                             int(row.provisional), int(row.isDecisionRow),
                             "" if row.get("qPercent") is None else "%.4f" % row.get("qPercent"),
                             "" if row.get("soret") is None else "%.6f" % row.get("soret"),
                             "" if row.get("valley") is None else "%.6f" % row.get("valley"),
                             "" if row.get("qBand") is None else "%.6f" % row.get("qBand"),
                             "" if digitalNumber is None else "%.2f" % digitalNumber])
            csvFile.flush()          # ⭐ a killed run keeps every row it had
            # ⚠ Rows arrive at ~1.4 Hz and jitter; printing each is unreadable, so the CONSOLE is thinned
            # while the CSV keeps everything (§10.7c). ⛔ Never re-average rows onto a coarser grid.
            if row.t - lastPrinted >= 5.0 or row.isDecisionRow:
                lastPrinted = row.t
                coach = _PLUGIN and monitor.evaluator.coach(monitor.rows)
                print("%8.2f %6d %8s %9s %9s %9s %7s  %s"
                      % (row.t / 60.0, row.n,
                         "-" if row.get("qPercent") is None else "%.3f" % row.get("qPercent"),
                         "-" if row.get("soret") is None else "%.4f" % row.get("soret"),
                         "-" if row.get("valley") is None else "%.4f" % row.get("valley"),
                         "-" if row.get("qBand") is None else "%.4f" % row.get("qBand"),
                         "-" if digitalNumber is None else "%.1f" % digitalNumber,
                         coach.get("state", "")), flush=True)
    except KeyboardInterrupt:
        # ⭐⭐ §25/X1 + P3's gate: Ctrl-C at minute 15 of a 20-minute arm must NOT throw the arm away.
        print("\n   ⚠ interrupted — flushing what the run already has …")
    finally:
        csvFile.close()
        result = monitor.result()
        if arguments.npz and rawFrames:
            # ⛔ np.savez CANNOT APPEND — the archive is written once, so the frames were held in RAM
            # (~34 MB for 20 min) and land here, including on the Ctrl-C path (§25/X1).
            keys = sorted(rawFrames[0].keys())
            stack = np.array([[frame.get(key, np.nan) for key in keys] for frame in rawFrames], dtype=float)
            np.savez_compressed(
                os.path.join(outDirectory, "settling_run.npz"), nanometers=np.array(keys, dtype=float),
                frames=stack, timestamps=np.array(rawTimes, dtype=float),
                reference=np.array([reference.valuesByNanometers.get(key, np.nan) for key in keys]),
                meta=np.array([str({"inset": "1/3 (app extractor)", "exposure": exposure, "roi": roi,
                                    "coeffs": coefficients, "label": arguments.label,
                                    "windowFrames": arguments.frames})], dtype=object))
            print("   npz: %d frames -> %s" % (len(rawFrames), outDirectory))

        print("\n   OUTCOME  %s" % result.outcome.value)
        if result.answer:
            print("   ⭐ %s = %.3f   at t = %.2f min   read as %s   (%s)"
                  % (result.answer["valueKey"], result.answer["value"], result.answer["t"] / 60.0,
                     result.answer["readAs"], result.answer["branch"]))
            print("   clearing time %.2f min" % ((result.clearingSeconds or 0.0) / 60.0))
        else:
            print("   ⛔ NO VALUE — %s" % result.outcome.value)
        if result.distinctFraction is not None:
            # ⭐ §23/V1: 82 % on the archive = a x1.10 noise inflation. A run whose duplicate rate drifted
            # is a run whose noise budget drifted with it.
            print("   distinct frames %.1f %%  (W=%d behaves like %.0f independent frames)"
                  % (100.0 * result.distinctFraction, arguments.frames,
                     arguments.frames * result.distinctFraction))
        for note in result.notes:
            print("   note: %s" % note)
        print("   csv: %s" % csvPath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
