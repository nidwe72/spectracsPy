#!/usr/bin/env python
"""
diagnoseCapture.py — RIG diagnosis script (INTEGRATION: needs the real ELP camera connected AND the local server
running). Reproduces the reference gray-outlier / jitter investigation (SPEC_capability_proof.md §7.0.1).

It drives the REAL capture stack (DevCaptureVideoThread + SpectralWorkflowEngine) exactly as CapturePanel does,
running N consecutive REFERENCE captures — each a real auto-exposure sweep + a 150-frame burst — with a pause
between them. Per-frame spectra + the C1 dim-frame rejection mask are written to JSON via the engine's env-gated
CaptureDiagnosticsLogger, and a live per-capture readout (elapsed / exposure / red-green shape / rejected) prints
so you can WATCH the sensor-warm-up drift settle. The calibration comes from masterUserExakta's SpectrometerSetup
(resolved through the server, like login).

Run from the spectracsPy repo root, ELP connected, local server up (via ./runDiagnose.sh, or directly):
    SPECTRACS_DIAG_PASSWORD=<pwd> ./runDiagnose.sh [--runs N] [--interval S] [--ae-once] [--frames F]

  --runs N       number of REFERENCE captures            (default 3)
  --interval S   seconds to pause between captures        (default 5)
  --ae-once      auto-expose ONCE before the first capture, then reuse that exposure (recommended for a warm-up
                 curve: no ~15 s AE sweep each interval, exposure fixed, so you see pure sensor drift)
  --frames F     frames per burst                         (default 150)

Warm-up characterization example (sample every 60 s for ~20 min, fixed exposure):
    SPECTRACS_DIAG_PASSWORD=<pwd> ./runDiagnose.sh --runs 20 --interval 60 --ae-once
(If SPECTRACS_DIAG_PASSWORD is unset it prompts. SPECTRACS_LOG_SPECTRA defaults to ./captureDiagnostics.)
"""
import argparse
import copy
import getpass
import os
import sys
import time

from PySide6 import QtWidgets
from PySide6.QtCore import QEventLoop, QTimer

MASTER_USERNAME = "masterUserExakta"
EXPOSURE_MIN, EXPOSURE_MAX, AE_PROBES = 1, 500, 8      # mirror CapturePanel's AE sweep
EXPOSURE_FALLBACK = 90


def parseArgs():
    parser = argparse.ArgumentParser(description="Rig capture diagnosis / sensor-warm-up characterization.")
    parser.add_argument("--runs", type=int, default=3, help="number of REFERENCE captures (default 3)")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between captures (default 5)")
    parser.add_argument("--ae-once", dest="aeOnce", action="store_true",
                        help="auto-expose once, then reuse the exposure (warm-up curve; default: per capture)")
    parser.add_argument("--frames", type=int, default=150, help="frames per burst (default 150)")
    return parser.parse_args()


def reducedBands(spectrum):
    # Reduce the accumulated frames (robust mean, on a throwaway copy) and return the blue/green/red band means —
    # for the live red/green shape readout that tracks the sensor-warm-up drift.
    from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
    from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
    parameters = MeanSpectrumLogicModuleParameters()
    parameters.setSpectrum(copy.deepcopy(spectrum))
    values = MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum().valuesByNanometers

    def band(lo, hi):
        picked = [v for nm, v in values.items() if v is not None and lo <= float(nm) <= hi]
        return sum(picked) / len(picked) if picked else float("nan")

    return band(445.0, 490.0), band(505.0, 560.0), band(600.0, 625.0)


def pump(milliseconds):
    # Spin the Qt event loop for a fixed wall-clock window so queued thread signals (frames, AE-finished) are
    # delivered — the headless equivalent of CapturePanel.__pumpFrames.
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def waitForFrame(state, timeoutMs=25000):
    # The first frame after a 2592x1944 open can be several seconds out (slow high-res warm-up), so wait generously.
    waited = 0
    while state["image"] is None and waited < timeoutMs:
        pump(150)
        waited += 150
    return state["image"] is not None


def main():
    args = parseArgs()
    os.environ.setdefault("SPECTRACS_LOG_SPECTRA", os.path.abspath("./captureDiagnostics"))
    print("Per-frame spectra -> %s" % os.environ["SPECTRACS_LOG_SPECTRA"])
    print("runs=%d interval=%gs frames=%d ae=%s" % (args.runs, args.interval, args.frames,
                                                     "once" if args.aeOnce else "per-run"))

    app = QtWidgets.QApplication(sys.argv)   # noqa: F841 — needed for the QThread event loop

    from sciens.spectracs.model.databaseEntity.DatabaseInitializer import initAppDatabase
    initAppDatabase()

    from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
    from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
    from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
    from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

    # --- bootstrap the masterUserExakta calibration (the exact login path CapturePanel relies on) ---
    password = os.environ.get("SPECTRACS_DIAG_PASSWORD") or getpass.getpass("Password for %s: " % MASTER_USERNAME)
    loginResult = SpectracsPyServerClient().login(MASTER_USERNAME, password)
    if not loginResult or not loginResult.get("username"):
        print("LOGIN FAILED for %s — is the local server running (runServer.sh)?" % MASTER_USERNAME)
        return 1
    CurrentUserSession().login(loginResult)
    if not ActiveSpectrometerProfileLogicModule().installFromSession():
        print("Could not install masterUserExakta's calibration (serial/instrument not resolved).")
        return 1

    profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
    sensor = profile.spectrometer.spectrometerSensor if (profile and profile.spectrometer) else None
    if sensor is None:
        print("No spectrometer sensor on the installed profile.")
        return 1

    from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
    from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
    deviceIndex = SensorCaptureIndexResolver().resolveCaptureIndex(sensor)
    if deviceIndex is None:
        print("Camera not resolved — is the ELP connected?")
        return 1
    sensorSettings = SpectrometerSensorUtil().getSensorSettings(sensor)
    seedExposure = sensorSettings.calibrationExposure if (sensorSettings and sensorSettings.calibrationExposure) \
        else EXPOSURE_FALLBACK
    print("serial=%s  device=%s  seedExposure=%s" % (profile.serial, deviceIndex, seedExposure))

    # --- start the REAL capture thread (continuous stream) ---
    from sciens.spectracs.logic.application.video.DevCaptureVideoThread import DevCaptureVideoThread
    state = {"image": None}
    ae = {"done": False, "exposure": None}
    thread = DevCaptureVideoThread()
    thread.setIsVirtual(False)
    thread.setDeviceId(deviceIndex)
    thread.setExposure(seedExposure)
    thread.setLiveExposure(seedExposure)
    thread.setFrameCount(0)

    def onFrameSignal(event, signal):
        # Mirror CapturePanel.handleVideoThreadSignal: preview frames (emitted DURING the AE sweep) must NOT become
        # the burst's latest image (§14.6), but ALWAYS release the one-frame backpressure so the stream keeps
        # flowing — without event.set() the capture thread blocks after the first frame.
        if not getattr(signal, "isPreview", False):
            state["image"] = signal.image
        event.set()

    thread.videoThreadSignal.connect(onFrameSignal)
    thread.autoExposureFinished.connect(lambda exposure: ae.update(done=True, exposure=exposure))
    thread.start()
    if not waitForFrame(state):
        print("No frames from the camera after warm-up.")
        thread.stop(); thread.wait(3000)
        return 1

    from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
    from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
    from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
    from sciens.spectracs.plugin_sdk import REFERENCE
    engine = SpectralWorkflowEngine(DevSpectralPlugin())

    def provider():
        pump(120)                               # let the stream advance (same cadence as CapturePanel)
        if state["image"] is None:
            return None
        return state["image"].copy()            # detach from the live buffer

    start = time.monotonic()
    trend = []
    for run in range(1, args.runs + 1):
        print("\n===== REFERENCE %d/%d =====" % (run, args.runs))
        # faithful to CapturePanel.__onClickedCapture's REFERENCE branch: AE sweep -> wait -> drop stale -> burst.
        # --ae-once: sweep only before the first capture, then reuse that exposure (fixed) so the warm-up curve
        # reflects sensor drift alone, not AE variation.
        if run == 1 or not args.aeOnce:
            ae.update(done=False, exposure=None)
            thread.requestAutoExpose(EXPOSURE_MIN, EXPOSURE_MAX, iterations=AE_PROBES)
            waited = 0
            while not ae["done"] and waited < 40000:   # 8 probes x ~1.8s drain + settle -> ~20s; allow headroom
                pump(100); waited += 100
            state["image"] = None                       # discard the last pre-sweep stale frame
            waitForFrame(state)

        step = SpectralWorkflowStep()
        step.setRole(REFERENCE)
        step.setLabel("Reference")
        # the engine's CaptureDiagnosticsLogger writes the per-frame JSON + prints the CAPTURE-SPECTRA line
        spectrum = engine.captureAcquisitionStep(step, frameProvider=provider, frames=args.frames,
                                                 onFrame=lambda spectrum, index, total: None)

        elapsed = time.monotonic() - start
        blue, green, red = reducedBands(spectrum) if spectrum is not None else (float("nan"),) * 3
        redGreen = red / green if green else float("nan")
        trend.append((round(elapsed, 1), ae["exposure"], round(redGreen, 4)))
        print("  t=%6.1fs  exposure=%s  red/green=%.4f  (blue/green=%.4f)"
              % (elapsed, ae["exposure"], redGreen, blue / green if green else float("nan")))

        if run < args.runs:
            pump(int(args.interval * 1000))              # pause; stream stays live

    thread.stop(); thread.wait(3000)
    print("\nDone. red/green vs time (the sensor-warm-up curve):")
    for elapsed, exposure, redGreen in trend:
        print("  t=%6.1fs  exposure=%s  red/green=%.4f" % (elapsed, exposure, redGreen))
    print("Per-frame JSON written to: %s" % os.environ["SPECTRACS_LOG_SPECTRA"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
