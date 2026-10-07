#!/usr/bin/env python3
"""W1.0 Windows camera probe — docs/SPEC_windows_build.md §6.7 / §12 row W1.0 (the production go/no-go spike).

A STANDALONE, READ-ONLY diagnostic. It touches no app code and no DB; it only needs numpy + OpenCV (the pinned
opencv-python-headless 4.7.0.72) and, optionally, `cv2_enumerate_cameras` for the VID/PID -> index lookup. It
answers the questions every later W1 step is written against:

  E  enumeration  — is the camera found by VID/PID, at which index, per backend (MSMF, DSHOW)?
  F  format       — is YUY2 granted at 2592x1944 (requested BEFORE the size, like CaptureBackend), how long does
                    the open take, what frame rate arrives?
  C  conversion   — with CONVERT_RGB=0, what does the raw buffer look like, can we convert it with our own
                    cv2.cvtColor(COLOR_YUV2BGR_YUY2), and how does the backend's own BGR differ from ours
                    (per-channel linear fit: slope/offset expose a BT.601/709 matrix or 16-235 range change)?
                    Can CONVERT_RGB be toggled between one grab() and two retrieve()s?
  A  AE mode      — which CAP_PROP_AUTO_EXPOSURE value actually means "manual" on this backend (V4L2: 1)?
  X  exposure     — the sweep: requested value -> read-back -> delivered brightness, over whole log2 steps,
                    half steps, and V4L2-style values. ⭐ The verdict "finer than whole doubling steps?" is the
                    SPEC §6.4 (a)/(b)/(c) decision input.
  K  controls     — WB_TEMPERATURE / AUTO_WB / GAIN / BACKLIGHT / BUFFERSIZE: set, read back, and (WB, gain)
                    does the image actually change?
  S  staleness    — after a large exposure change, how many frames until the brightness settles?

Every control is set on every open (SPEC §6.4b: UVC control values survive a VMware hand-over).
The lamp must be ON (by hand) and the jar/slit as for a measurement, so the frame has a bright spectrum.

Output: a markdown summary on stdout + report.json + summary.md in --out. ⛔ Device instance paths and serials
are SCRUBBED (public repo): only names and VID/PID are kept.

Run in the VM (ELP passed through, lamp on):
    C:\\spectracs-build\\venv\\Scripts\\python windows_camera_probe.py --vidpid 32e4:8830
Self-test (no camera, any OS):
    python diagnostics/windows_camera_probe.py --selftest
"""
import argparse
import json
import os
import platform
import re
import sys
import time
from datetime import datetime

import numpy as np

# The VM console is cp1252: printing the summary's ⭐ crashed the first run after the files were written.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Must be set BEFORE cv2 is imported: MSMF's hardware transforms are an extra, OS-owned conversion path (§11 R13).
if "--hwTransforms" in sys.argv:
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = sys.argv[sys.argv.index("--hwTransforms") + 1]
os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

WIDTH, HEIGHT = 2592, 1944          # the calibration resolution — CaptureBackend pins exactly this
TARGET_PEAK = 245                   # AutoExposureLogicModule.DEFAULT_TARGET

# Whole log2 steps, half steps between them, and V4L2-style values (100 µs units, the ELP's Linux numbers).
LOG2_WHOLE = [float(v) for v in range(-13, 0)]
LOG2_HALF = [v + 0.5 for v in range(-13, -1)]
V4L2_STYLE = [1.0, 5.0, 20.0, 78.0, 90.0, 150.0, 500.0]


# --------------------------------------------------------------------------------------------- pure analysis

def scrub(text):
    """Keep VID/PID, drop everything instance-specific (serials, USB topology, GUIDs). Public repo."""
    if text is None:
        return None
    text = str(text)
    match = re.search(r"vid_([0-9a-f]{4}).{0,3}pid_([0-9a-f]{4})", text, re.IGNORECASE)
    if match:
        return "vid_%s&pid_%s <scrubbed>" % (match.group(1).lower(), match.group(2).lower())
    return "<scrubbed>" if ("\\" in text or "#" in text or "{" in text) else text


def fourccName(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return None
    name = "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))
    return name if name.isprintable() else "0x%08x" % code


def channelPeak(bgr, percentile=99.9):
    """Same metric as AutoExposureLogicModule.channelPeak: high percentile of the brightest channel."""
    return float(np.percentile(bgr.max(axis=2), percentile))


def yuy2ToBgr(raw, width, height):
    """Our own conversion of a raw YUY2 buffer, whatever shape the backend handed it over in. None if the size
    does not fit a WxH YUY2 frame (then the backend did NOT give us raw YUY2)."""
    import cv2
    if raw is None:
        return None
    flat = np.ascontiguousarray(raw).reshape(-1)
    if flat.size != width * height * 2 or flat.dtype != np.uint8:
        return None
    return cv2.cvtColor(flat.reshape(height, width, 2), cv2.COLOR_YUV2BGR_YUY2)


def channelFit(ours, theirs, stride=7):
    """Per channel: theirs ≈ slope·ours + offset (least squares on a pixel subsample), plus mean |diff|.
    Slope≈1, offset≈0 ⇒ same conversion; slope≈1.164 & offset≈-18.6 ⇒ a 16-235 range expansion; a channel-
    dependent slope ⇒ a different colour matrix. Different grabs differ only by sensor noise, which a fit over
    ~10^5 pixels averages out."""
    result = {}
    for index, name in enumerate("BGR"):
        x = ours[::stride, ::stride, index].astype(np.float64).ravel()
        y = theirs[::stride, ::stride, index].astype(np.float64).ravel()
        keep = (x > 2) & (x < 253) & (y > 2) & (y < 253)          # clipped pixels carry no slope information
        if keep.sum() < 100:
            result[name] = {"slope": None, "offset": None, "meanAbsDiff": float(np.mean(np.abs(x - y)))}
            continue
        slope, offset = np.polyfit(x[keep], y[keep], 1)
        result[name] = {"slope": round(float(slope), 4), "offset": round(float(offset), 2),
                        "meanAbsDiff": round(float(np.mean(np.abs(x - y))), 3)}
    return result


def manualValueVerdict(trials):
    """trials: [{"value": v, "deltaPeak": brightness(exp A) - brightness(exp B)}]. The AUTO_EXPOSURE value under
    which an exposure change actually changes the image is the backend's 'manual'. Returns (value or None, why)."""
    responsive = [t for t in trials if t.get("deltaPeak") is not None and abs(t["deltaPeak"]) >= 5.0]
    if not responsive:
        return None, "no AUTO_EXPOSURE value made the exposure control take effect"
    if len(trials) > 1 and len({round(t["deltaPeak"], 0) for t in trials if t.get("deltaPeak") is not None}) == 1:
        return None, ("AUTO_EXPOSURE has NO effect (same Δpeak %.1f under every value) — setting EXPOSURE "
                      "alone already switches to manual" % trials[0]["deltaPeak"])
    best = max(responsive, key=lambda t: abs(t["deltaPeak"]))
    return best["value"], "exposure takes effect under AUTO_EXPOSURE=%s (Δpeak %.1f)" % (best["value"], best["deltaPeak"])


def granularityVerdict(rows):
    """rows: sweep rows with requested/readback/peak/mean. ⭐ The §6.4 input.

    'finer' needs a HALF step whose delivered brightness lies strictly between its two whole-step neighbours
    (by more than noise) — read-back alone is not evidence: drivers echo values they then round."""
    byValue = {r["requested"]: r for r in rows if r.get("mean") is not None}
    between = 0
    tested = 0
    for half in LOG2_HALF:
        low, high = byValue.get(half - 0.5), byValue.get(half + 0.5)
        mid = byValue.get(half)
        if not (low and high and mid):
            continue
        a, b = sorted((low["mean"], high["mean"]))
        if b - a < 4.0:                       # neighbours not distinguishable (clipped/dark) — no information
            continue
        tested += 1
        margin = 0.15 * (b - a)
        if a + margin < mid["mean"] < b - margin:
            between += 1
    v4l2Distinct = len({round(byValue[v]["mean"], 0) for v in V4L2_STYLE if v in byValue})
    if tested == 0:
        verdict = "UNDECIDED — no usable whole-step pair (all dark or all clipped?)"
    elif between >= max(1, tested // 2):
        verdict = "FINER than whole log2 steps (%d of %d half steps land between their neighbours)" % (between, tested)
    else:
        verdict = "WHOLE log2 STEPS ONLY (%d of %d half steps land between their neighbours)" % (between, tested)
    return {"verdict": verdict, "halfStepsBetween": between, "halfStepsTested": tested,
            "distinctBrightnessOverV4l2StyleValues": v4l2Distinct}


def settleFrames(series, tolerance=0.02):
    """Frames until the brightness series stays within ±tolerance of its final value."""
    if not series:
        return None
    final = series[-1]
    for index in range(len(series)):
        if all(abs(v - final) <= tolerance * max(final, 1.0) for v in series[index:]):
            return index
    return len(series)


# --------------------------------------------------------------------------------------------- camera access

class Probe:

    def __init__(self, args):
        self.args = args
        import cv2
        self.cv2 = cv2

    # -- frames
    def read(self, cap, tries=12):
        for _ in range(tries):
            try:
                ok, frame = cap.read()
            except self.cv2.error:
                ok, frame = False, None
            if ok and frame is not None and frame.size:
                return frame
        return None

    def bgr(self, frame, convertRgb):
        if frame is None:
            return None
        if convertRgb:
            return frame if frame.ndim == 3 and frame.shape[2] == 3 else None
        return yuy2ToBgr(frame, WIDTH, HEIGHT)

    def measure(self, cap, convertRgb=True):
        """Discard `settle` frames after a control change, then average `average` frames' metrics."""
        for _ in range(self.args.settle):
            self.read(cap, tries=3)
        peaks, means = [], []
        for _ in range(self.args.average):
            image = self.bgr(self.read(cap), convertRgb)
            if image is not None:
                peaks.append(channelPeak(image))
                means.append(float(image.mean()))
        if not peaks:
            return None, None
        return round(float(np.mean(peaks)), 2), round(float(np.mean(means)), 2)

    def get(self, cap, prop):
        try:
            value = cap.get(prop)
            return None if value is None else round(float(value), 4)
        except self.cv2.error:
            return None

    def set(self, cap, prop, value):
        try:
            return bool(cap.set(prop, value))
        except self.cv2.error:
            return False

    # -- open exactly the way CaptureBackend does (FOURCC before size, BUFFERSIZE=1), timed
    def open(self, index, backend, convertRgb=True):
        cv2 = self.cv2
        started = time.time()
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            return None, {"opened": False}
        self.set(cap, cv2.CAP_PROP_BUFFERSIZE, 1)
        fourccSet = self.set(cap, cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUY2"))
        self.set(cap, cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.set(cap, cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        convertSet = self.set(cap, cv2.CAP_PROP_CONVERT_RGB, 1 if convertRgb else 0)
        first = self.read(cap, tries=20)
        info = {
            "opened": True,
            "openToFirstFrameS": round(time.time() - started, 2),
            "fourccSetReturned": fourccSet,
            "fourccReadBack": fourccName(self.get(cap, cv2.CAP_PROP_FOURCC)),
            "widthReadBack": self.get(cap, cv2.CAP_PROP_FRAME_WIDTH),
            "heightReadBack": self.get(cap, cv2.CAP_PROP_FRAME_HEIGHT),
            "convertRgbSetReturned": convertSet,
            "convertRgbReadBack": self.get(cap, cv2.CAP_PROP_CONVERT_RGB),
            "firstFrame": None if first is None else {"shape": list(first.shape), "dtype": str(first.dtype)},
        }
        return cap, info

    def openVariants(self, index, backend):
        """Why did the open fail? Each variant drops one more of CaptureBackend's settings."""
        cv2 = self.cv2
        variants = {}
        for label, settings in (("bare", []),
                                ("size only", [(cv2.CAP_PROP_FRAME_WIDTH, WIDTH), (cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)]),
                                ("YUY2 only", [(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUY2"))])):
            started = time.time()
            try:
                cap = cv2.VideoCapture(index, backend)
            except cv2.error as error:
                variants[label] = {"error": str(error)}
                continue
            entry = {"isOpened": bool(cap.isOpened())}
            if cap.isOpened():
                for prop, value in settings:
                    self.set(cap, prop, value)
                frame = self.read(cap, tries=20)
                entry.update({"frame": None if frame is None else list(frame.shape),
                              "fourcc": fourccName(self.get(cap, cv2.CAP_PROP_FOURCC)),
                              "size": [self.get(cap, cv2.CAP_PROP_FRAME_WIDTH), self.get(cap, cv2.CAP_PROP_FRAME_HEIGHT)],
                              "seconds": round(time.time() - started, 2)})
            cap.release()
            variants[label] = entry
            print("  %s open variant %-10s %s" % ("MSMF" if backend == cv2.CAP_MSMF else backend, label, entry), flush=True)
        return variants

    # -- E
    def enumerate(self):
        cv2 = self.cv2
        found = {"package": None, "devices": []}
        try:
            from cv2_enumerate_cameras import enumerate_cameras
            found["package"] = "cv2_enumerate_cameras"
            for name, backend in (("MSMF", cv2.CAP_MSMF), ("DSHOW", cv2.CAP_DSHOW)):
                for camera in enumerate_cameras(backend):
                    index = int(camera.index)
                    found["devices"].append({
                        "backend": name, "index": index % 100 if index >= 100 else index,
                        "rawIndex": index, "name": camera.name,
                        "vid": None if camera.vid is None else "%04x" % camera.vid,
                        "pid": None if camera.pid is None else "%04x" % camera.pid,
                        "path": scrub(getattr(camera, "path", None))})
        except ImportError:
            found["package"] = "missing (pip install cv2-enumerate-cameras in the VM venv) — use --index"
        return found

    def pickIndex(self, enumeration, backendName):
        if self.args.index is not None:
            return self.args.index
        vid, pid = self.args.vidpid.lower().split(":")
        for device in enumeration["devices"]:
            if device["backend"] == backendName and device["vid"] == vid and device["pid"] == pid:
                return device["index"]
        return None

    # -- C: same grab, two retrieves with CONVERT_RGB toggled
    def toggleTest(self, cap):
        cv2 = self.cv2
        try:
            if not cap.grab():
                return {"grab": False}
            self.set(cap, cv2.CAP_PROP_CONVERT_RGB, 1)
            okA, converted = cap.retrieve()
            self.set(cap, cv2.CAP_PROP_CONVERT_RGB, 0)
            okB, raw = cap.retrieve()
            self.set(cap, cv2.CAP_PROP_CONVERT_RGB, 1)
        except cv2.error as error:
            return {"error": str(error)}
        result = {"retrieveConverted": bool(okA), "retrieveRaw": bool(okB),
                  "rawShape": None if raw is None else list(raw.shape)}
        ours = yuy2ToBgr(raw, WIDTH, HEIGHT) if okB else None
        if okA and ours is not None and converted is not None and converted.shape == ours.shape:
            diff = np.abs(converted.astype(np.int16) - ours.astype(np.int16))
            result["sameGrabMaxAbsDiff"] = int(diff.max())
            result["sameGrabMeanAbsDiff"] = round(float(diff.mean()), 4)
        return result

    # -- the whole run for one backend
    def runBackend(self, backendName, backend, enumeration):
        cv2 = self.cv2
        out = {"backend": backendName}
        index = self.pickIndex(enumeration, backendName)
        out["index"] = index
        if index is None:
            out["skipped"] = "camera %s not enumerated on %s (pass --index to force)" % (self.args.vidpid, backendName)
            return out

        # F + C(backend's own conversion)
        cap, out["openConverted"] = self.open(index, backend, convertRgb=True)
        if cap is None:
            out["openVariants"] = self.openVariants(index, backend)
            return out
        timings = []
        for _ in range(6):
            t = time.time()
            if self.read(cap, tries=3) is not None:
                timings.append(time.time() - t)
        out["fps"] = round(1.0 / float(np.median(timings)), 2) if timings else None

        # A — which AUTO_EXPOSURE value is "manual"?
        trials = []
        for value in self.args.aeValues:
            self.set(cap, cv2.CAP_PROP_AUTO_EXPOSURE, value)
            readBack = self.get(cap, cv2.CAP_PROP_AUTO_EXPOSURE)
            self.set(cap, cv2.CAP_PROP_EXPOSURE, -9)
            peakDark, _ = self.measure(cap)
            self.set(cap, cv2.CAP_PROP_EXPOSURE, -5)
            peakBright, _ = self.measure(cap)
            delta = None if None in (peakDark, peakBright) else round(peakBright - peakDark, 2)
            trials.append({"value": value, "readBack": readBack, "peakAtMinus9": peakDark,
                           "peakAtMinus5": peakBright, "deltaPeak": delta})
        manual, why = manualValueVerdict(trials)
        out["autoExposure"] = {"trials": trials, "manualValue": manual, "verdict": why}
        if manual is not None:
            self.set(cap, cv2.CAP_PROP_AUTO_EXPOSURE, manual)

        # K — fixed controls as the measurement path sets them (CaptureBackend.py:126-147), read back + effect
        controls = {}
        self.set(cap, cv2.CAP_PROP_EXPOSURE, self.args.workingExposure)
        for name, prop, value in (("GAIN", cv2.CAP_PROP_GAIN, 0), ("BACKLIGHT", cv2.CAP_PROP_BACKLIGHT, 0),
                                  ("AUTO_WB", cv2.CAP_PROP_AUTO_WB, 0),
                                  ("WB_TEMPERATURE", cv2.CAP_PROP_WB_TEMPERATURE, 6500),
                                  ("BUFFERSIZE", cv2.CAP_PROP_BUFFERSIZE, 1)):
            before = self.get(cap, prop)
            returned = self.set(cap, prop, value)
            controls[name] = {"before": before, "requested": value, "setReturned": returned,
                              "readBack": self.get(cap, prop)}
        wb = {}
        for kelvin in (6500, 3000, 6500):
            self.set(cap, cv2.CAP_PROP_WB_TEMPERATURE, kelvin)
            image = None
            for _ in range(self.args.settle):
                self.read(cap, tries=3)
            image = self.bgr(self.read(cap), convertRgb=True)
            if image is not None:
                b, g, r = (float(image[..., i].mean()) for i in range(3))
                wb.setdefault(str(kelvin), []).append(round(b / max(r, 1e-6), 4))
        ratio65, ratio30 = wb.get("6500", [None])[0], wb.get("3000", [None])[0]
        controls["WB_EFFECT"] = {"blueOverRed": wb,
                                 "honoured": None if None in (ratio65, ratio30) else abs(ratio65 - ratio30) > 0.03}
        wbBlue = {"before": self.get(cap, cv2.CAP_PROP_WHITE_BALANCE_BLUE_U)}
        for kelvin in (6500, 3000, 6500):
            returned = self.set(cap, cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, kelvin)
            for _ in range(self.args.settle):
                self.read(cap, tries=3)
            image = self.bgr(self.read(cap), convertRgb=True)
            ratio = None
            if image is not None:
                ratio = round(float(image[..., 0].mean()) / max(float(image[..., 2].mean()), 1e-6), 4)
            wbBlue.setdefault("trials", []).append({"requested": kelvin, "setReturned": returned,
                                                    "readBack": self.get(cap, cv2.CAP_PROP_WHITE_BALANCE_BLUE_U),
                                                    "blueOverRed": ratio})
        controls["WHITE_BALANCE_BLUE_U"] = wbBlue
        gainPeaks = {}
        for gain in (0, 32, 0):
            self.set(cap, cv2.CAP_PROP_GAIN, gain)
            gainPeaks.setdefault(str(gain), []).append(self.measure(cap)[1])
        controls["GAIN_EFFECT"] = {"meanByGain": gainPeaks}
        out["controls"] = controls

        # X — the exposure sweep
        rows = []
        candidates = LOG2_WHOLE + LOG2_HALF + V4L2_STYLE
        if self.args.quick:
            candidates = [-11.0, -9.0, -8.5, -8.0, -7.0, -5.0, 90.0, 150.0]
        for value in sorted(candidates):
            returned = self.set(cap, cv2.CAP_PROP_EXPOSURE, value)
            peak, mean = self.measure(cap)
            rows.append({"requested": value, "setReturned": returned,
                         "readBack": self.get(cap, cv2.CAP_PROP_EXPOSURE), "peak": peak, "mean": mean})
            print("  %-6s exposure %7.2f -> readback %-8s peak %-7s mean %s"
                  % (backendName, value, rows[-1]["readBack"], peak, mean), flush=True)
        out["exposureSweep"] = rows
        out["granularity"] = granularityVerdict(rows)

        # S — staleness after a big step
        self.set(cap, cv2.CAP_PROP_EXPOSURE, -11)
        self.measure(cap)
        self.set(cap, cv2.CAP_PROP_EXPOSURE, -6)
        series = []
        for _ in range(10):
            image = self.bgr(self.read(cap), convertRgb=True)
            series.append(None if image is None else round(float(image.mean()), 2))
        clean = [v for v in series if v is not None]
        out["staleness"] = {"meanPerFrameAfterStep": series, "framesToSettle": settleFrames(clean)}
        cap.release()

        # C — raw path: CONVERT_RGB=0 from the open on, our own conversion, compared with the backend's BGR
        cap, out["openRaw"] = self.open(index, backend, convertRgb=False)
        if cap is not None:
            if manual is not None:
                self.set(cap, cv2.CAP_PROP_AUTO_EXPOSURE, manual)
            self.set(cap, cv2.CAP_PROP_EXPOSURE, self.args.workingExposure)
            for _ in range(self.args.settle):
                self.read(cap, tries=3)
            raw = self.read(cap)
            ours = yuy2ToBgr(raw, WIDTH, HEIGHT)
            out["rawFrame"] = {"shape": None if raw is None else list(raw.shape),
                               "dtype": None if raw is None else str(raw.dtype),
                               "convertibleAsYuy2": ours is not None}
            # the backend's BGR at the same exposure, for the fit
            self.set(cap, cv2.CAP_PROP_CONVERT_RGB, 1)
            for _ in range(self.args.settle):
                self.read(cap, tries=3)
            theirs = self.bgr(self.read(cap), convertRgb=True)
            if ours is not None and theirs is not None and ours.shape == theirs.shape:
                out["backendVsOwnConversion"] = channelFit(ours, theirs)
            out["toggleSameGrab"] = self.toggleTest(cap)
            cap.release()
        return out


# --------------------------------------------------------------------------------------------- report

def summary(report):
    lines = ["# Windows camera probe — %s" % report["started"], "",
             "%s · Python %s · OpenCV %s · HW_TRANSFORMS=%s" % (report["platform"], report["python"],
                                                                 report["opencv"], report["hwTransforms"]), "",
             "Enumeration: %s" % report["enumeration"]["package"]]
    for device in report["enumeration"]["devices"]:
        lines.append("- %s #%s  %s  %s:%s" % (device["backend"], device["index"], device["name"],
                                              device["vid"], device["pid"]))
    for result in report["backends"]:
        lines += ["", "## %s (index %s)" % (result["backend"], result.get("index"))]
        if "skipped" in result:
            lines.append(result["skipped"])
            continue
        opened = result.get("openConverted", {})
        lines.append("| question | answer |")
        lines.append("|---|---|")
        lines.append("| opened / first frame after | %s / %s s |" % (opened.get("opened"), opened.get("openToFirstFrameS")))
        lines.append("| FOURCC granted (requested YUY2) | %s |" % opened.get("fourccReadBack"))
        lines.append("| size read back | %sx%s |" % (opened.get("widthReadBack"), opened.get("heightReadBack")))
        lines.append("| frame rate | %s fps |" % result.get("fps"))
        lines.append("| AUTO_EXPOSURE manual value | %s |" % result.get("autoExposure", {}).get("verdict"))
        lines.append("| ⭐ exposure granularity | %s |" % result.get("granularity", {}).get("verdict"))
        raw = result.get("rawFrame", {})
        lines.append("| CONVERT_RGB=0 buffer | shape %s %s, convertible as YUY2: %s |"
                     % (raw.get("shape"), raw.get("dtype"), raw.get("convertibleAsYuy2")))
        fit = result.get("backendVsOwnConversion")
        if fit:
            lines.append("| backend BGR vs own cvtColor | %s |" % "; ".join(
                "%s slope %s off %s" % (k, v["slope"], v["offset"]) for k, v in fit.items()))
        lines.append("| same-grab toggle | %s |" % result.get("toggleSameGrab"))
        for name, control in result.get("controls", {}).items():
            lines.append("| %s | %s |" % (name, control))
        lines.append("| frames to settle after exposure step | %s |" % result.get("staleness", {}).get("framesToSettle"))
    return "\n".join(lines) + "\n"


def selftest():
    assert scrub(r"\\?\usb#vid_32E4&pid_8830&mi_00#7&1a2b3c&0&0000#{e5323777}") == "vid_32e4&pid_8830 <scrubbed>"
    assert scrub("HD USB Camera") == "HD USB Camera"
    import cv2
    yuy2 = np.full((HEIGHT, WIDTH, 2), 128, np.uint8)
    yuy2[..., 0] = 100
    ours = yuy2ToBgr(yuy2.reshape(1, -1), WIDTH, HEIGHT)
    assert ours is not None and ours.shape == (HEIGHT, WIDTH, 3)
    assert np.array_equal(ours, cv2.cvtColor(yuy2, cv2.COLOR_YUV2BGR_YUYV)), "YUY2 and YUYV must be one conversion"
    assert yuy2ToBgr(np.zeros(10, np.uint8), WIDTH, HEIGHT) is None
    rng = np.random.default_rng(1)
    base = rng.integers(20, 230, (200, 300, 3)).astype(np.uint8)
    expanded = np.clip(base.astype(np.float64) * 1.164 - 18.6, 0, 255).astype(np.uint8)
    fit = channelFit(base, expanded, stride=1)
    assert abs(fit["G"]["slope"] - 1.164) < 0.01 and abs(fit["G"]["offset"] + 18.6) < 1.0
    rows = [{"requested": v, "mean": 10 * (v + 14)} for v in LOG2_WHOLE + LOG2_HALF]
    assert granularityVerdict(rows)["verdict"].startswith("FINER")
    rows = [{"requested": v, "mean": 10 * (int(v) + 14) if v == int(v) else 10 * (v - 0.5 + 14)}
            for v in LOG2_WHOLE + LOG2_HALF]
    assert granularityVerdict(rows)["verdict"].startswith("WHOLE")
    assert manualValueVerdict([{"value": 0.75, "deltaPeak": 1.0}, {"value": 0.25, "deltaPeak": 60.0}])[0] == 0.25
    assert manualValueVerdict([{"value": 1, "deltaPeak": 0.5}])[0] is None
    assert settleFrames([10, 50, 90, 100, 100, 100]) == 3
    print("selftest ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--vidpid", default="32e4:8830", help="camera VID:PID (default: the ELP)")
    parser.add_argument("--index", type=int, default=None, help="force the cv2 index (skips VID/PID lookup)")
    parser.add_argument("--backends", default="MSMF,DSHOW")
    parser.add_argument("--settle", type=int, default=4, help="frames discarded after a control change")
    parser.add_argument("--average", type=int, default=2, help="frames averaged per measurement")
    parser.add_argument("--workingExposure", type=float, default=-7.0,
                        help="log2 exposure for the control/conversion tests (pick one that does not clip)")
    parser.add_argument("--aeValues", type=lambda s: [float(v) for v in s.split(",")], default=[0.25, 0.75, 0, 1, 3])
    parser.add_argument("--hwTransforms", default="0", help="MSMF hardware transforms (read before cv2 import)")
    parser.add_argument("--quick", action="store_true", help="8-point exposure sweep instead of 38")
    parser.add_argument("--out", default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return

    import cv2
    probe = Probe(args)
    started = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    report = {"started": started, "platform": platform.platform(), "python": platform.python_version(),
              "opencv": cv2.__version__, "hwTransforms": os.environ.get("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"),
              "args": {k: v for k, v in vars(args).items() if k != "selftest"}}
    print("enumerating ...", flush=True)
    report["enumeration"] = probe.enumerate()
    report["backends"] = []
    backendIds = {"MSMF": cv2.CAP_MSMF, "DSHOW": cv2.CAP_DSHOW, "ANY": cv2.CAP_ANY}
    for name in args.backends.split(","):
        print("== %s" % name, flush=True)
        report["backends"].append(probe.runBackend(name, backendIds[name], report["enumeration"]))

    out = args.out or os.path.join(os.getcwd(), "windows_camera_probe_%s" % started)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)
    text = summary(report)
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print()
    print(text)
    print("written: %s" % out)


if __name__ == "__main__":
    main()
