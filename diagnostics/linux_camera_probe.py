#!/usr/bin/env python3
"""W1.4 Linux camera probe — docs/SPEC_windows_build.md §6.3.4 / §12 row W1.4 / D10.

A STANDALONE diagnostic, the Linux twin of `windows_camera_probe.py`. It touches no app code and no DB; it only
needs numpy + OpenCV 4.7.0 and the ELP on V4L2. Three questions:

  B  bit-identity — does `CaptureBackend.yuy2ToBgr` on the raw YUYV buffer give the same 8-bit BGR as OpenCV's
                    V4L2 backend converting it itself (today's Linux path)? §6.3.4 wanted ONE grab, TWO retrieves;
                    in 4.7.0 that is structurally impossible (`retrieveFrame` re-queues the buffer and sets
                    `bufferIndex = -1`, so a second retrieve returns the stale frame), so the proof is the source
                    (printed below) and this section is the empirical cross-check: mean of N frames converted by the
                    backend (A1), mean of N raw frames converted by us (B), backend again (A2). A real matrix/range
                    difference would show as a slope/offset in B against (A1+A2)/2 far outside A1-vs-A2.
  S  settling     — D10: how many frames after (a) the open, (b) an exposure step, (c) a white-balance change
                    until the image is settled? Read exactly as the app reads (read() with BUFFERSIZE=1).
  K  controls     — every V4L2 control: as found (whatever the last user — the VM — left in the camera), after
                    the measurement open, and the default. Information only (D10: Linux image controls untouched).

The lamp is switched on through the Shelly plug (dead-man `toggle_after`, off in `finally`) and warmed up first.
Jar/slit as for a measurement, so the frame shows a bright spectrum.

    PYTHONPATH=. ./venv/bin/python diagnostics/linux_camera_probe.py [--device 0] [--out DIR] [--no-lamp]
"""
import argparse
import json
import os
import struct
import sys
import time
import urllib.request
from datetime import datetime

import numpy as np

WIDTH, HEIGHT = 2592, 1944          # CaptureBackend pins exactly this
EXPOSURE = 90                        # DevSpectralPlugin.exposure (V4L2 units, 100 µs)
EXPOSURE_STEP = 45                   # a factor-2 step, the size of one Windows log2 step
WB_KELVIN = 6500                     # DevCaptureVideoThread.WHITE_BALANCE_KELVIN
WB_OTHER = 3000
LAMP_HOST = "192.168.1.123"
LAMP_WARMUP_S = 30
AVERAGE_FRAMES = 20                  # section B
SETTLE_FRAMES = 24                   # frames recorded after each event (section S)
PLATEAU_FRAMES = 8                   # the last N of them define "settled"

V4L2_SOURCE = {
    "file": "opencv 4.7.0 modules/videoio/src/cap_v4l.cpp",
    "convertToRgb_yuyv": "case V4L2_PIX_FMT_YUYV: cv::cvtColor(cv::Mat(imageSize, CV_8UC2, start), destination, "
                         "COLOR_YUV2BGR_YUYV);  (start = currentBuffer.memories[MEMORY_ORIG].start, l.1665/1723)",
    "raw_path": "convert_rgb=false: memcpy(buffers[MAX_V4L_BUFFERS]...start, currentBuffer...start, bytesused) "
                "(l.2293) — the same mmap buffer, copied untouched",
    "second_retrieve": "retrieveFrame re-queues the buffer (VIDIOC_QBUF) and sets bufferIndex = -1 (l.2297-2303) "
                       "⇒ a 2nd retrieve on the same grab returns the stale frame",
    "ours": "CaptureBackend.yuy2ToBgr: cv2.cvtColor(raw.reshape(h, w, 2), cv2.COLOR_YUV2BGR_YUY2)",
}


# --------------------------------------------------------------------------------------------- lamp

def lamp(on, toggleAfter=None):
    query = "id=0&on=%s" % ("true" if on else "false")
    if toggleAfter:
        query += "&toggle_after=%d" % toggleAfter
    for attempt in range(3):                             # the plug is on Wi-Fi: one timeout is not an answer
        try:
            with urllib.request.urlopen("http://%s/rpc/Switch.Set?%s" % (LAMP_HOST, query), timeout=8) as response:
                response.read()
            return
        except OSError:
            if attempt == 2:
                raise


# --------------------------------------------------------------------------------------------- V4L2 controls

def _iowr(number, size):
    return 0xC0000000 | (size << 16) | (ord("V") << 8) | number


VIDIOC_QUERYCTRL = _iowr(36, 68)
VIDIOC_G_CTRL = _iowr(27, 8)
VIDIOC_QUERYMENU = _iowr(37, 44)
NEXT_CTRL = 0x80000000
CTRL_TYPE_MENU, CTRL_TYPE_CLASS = 3, 6


def readControls(node):
    """Every control of `node`: name, type, min/max/step/default, current value (+ menu name). Read-only."""
    import fcntl
    descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
    controls = []
    try:
        control = NEXT_CTRL
        while True:
            buffer = bytearray(struct.pack("I", control) + bytes(64))
            try:
                fcntl.ioctl(descriptor, VIDIOC_QUERYCTRL, buffer, True)
            except OSError:
                break
            cid, kind = struct.unpack_from("II", buffer, 0)
            name = bytes(buffer[8:40]).split(b"\0")[0].decode(errors="replace")
            low, high, step, default, flags = struct.unpack_from("iiiiI", buffer, 40)
            control = cid | NEXT_CTRL
            if kind == CTRL_TYPE_CLASS:
                continue
            value = None
            valueBuffer = bytearray(struct.pack("Ii", cid, 0))
            try:
                fcntl.ioctl(descriptor, VIDIOC_G_CTRL, valueBuffer, True)
                value = struct.unpack_from("i", valueBuffer, 4)[0]
            except OSError:
                pass
            entry = {"id": "0x%08x" % cid, "name": name, "type": kind, "min": low, "max": high, "step": step,
                     "default": default, "value": value, "flags": flags}
            if kind == CTRL_TYPE_MENU and value is not None:
                menu = bytearray(struct.pack("II", cid, value) + bytes(36))
                try:
                    fcntl.ioctl(descriptor, VIDIOC_QUERYMENU, menu, True)
                    entry["valueName"] = bytes(menu[8:40]).split(b"\0")[0].decode(errors="replace")
                except OSError:
                    pass
            controls.append(entry)
    finally:
        os.close(descriptor)
    return controls


# --------------------------------------------------------------------------------------------- capture

def yuy2ToBgr(raw, width, height):
    """Identical to CaptureBackend.yuy2ToBgr (kept local: this probe imports no app code)."""
    import cv2
    flat = np.ascontiguousarray(raw).reshape(-1)
    if flat.dtype != np.uint8 or flat.size != width * height * 2:
        return None
    return cv2.cvtColor(flat.reshape(height, width, 2), cv2.COLOR_YUV2BGR_YUY2)


def openMeasurement(cv2, device, convertRgb=True):
    """CaptureBackend.open's Linux measurement sequence, step for step (FOURCC before size, 8 grabs, AE manual,
    exposure, gain 0, WB manual + temperature, backlight 0). Returns (cap, seconds the open took)."""
    started = time.monotonic()
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise SystemExit("cannot open /dev/video%d — is the ELP still passed through to the VM?" % device)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    if not convertRgb:
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    if not any(cap.grab() for _ in range(8)):
        raise SystemExit("no frame after opening YUYV")
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_EXPOSURE, EXPOSURE)
    cap.set(cv2.CAP_PROP_GAIN, 0)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    cap.set(cv2.CAP_PROP_WB_TEMPERATURE, WB_KELVIN)
    cap.set(cv2.CAP_PROP_BACKLIGHT, 0)
    return cap, time.monotonic() - started


def readBgr(cap, convertRgb=True):
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    return frame if convertRgb else yuy2ToBgr(frame, WIDTH, HEIGHT)


def frameStats(bgr):
    means = bgr.reshape(-1, 3).mean(axis=0)            # B, G, R
    return {"b": float(means[0]), "g": float(means[1]), "r": float(means[2]),
            "peak": float(np.percentile(bgr.max(axis=2), 99.9)), "bOverR": float(means[0] / max(means[2], 1e-9))}


# --------------------------------------------------------------------------------------------- B: bit-identity

def meanFrame(cv2, device, convertRgb):
    cap, _ = openMeasurement(cv2, device, convertRgb)
    try:
        for _ in range(6):                               # past the settling (section S measures how many)
            readBgr(cap, convertRgb)
        total, count, shape = None, 0, None
        while count < AVERAGE_FRAMES:
            bgr = readBgr(cap, convertRgb)
            if bgr is None:
                continue
            shape = bgr.shape
            total = bgr.astype(np.float64) if total is None else total + bgr
            count += 1
        return total / count, shape
    finally:
        cap.release()


def fit(x, y):
    """y ≈ slope·x + offset per channel over a pixel subsample; plus mean and max |y−x|."""
    out = {}
    for index, channel in enumerate("bgr"):
        xs, ys = x[::7, ::7, index].ravel(), y[::7, ::7, index].ravel()
        slope, offset = np.polyfit(xs, ys, 1) if xs.std() > 0 else (float("nan"), float("nan"))   # a dark frame
        out[channel] = {"slope": float(slope), "offset": float(offset), "meanDiff": float((ys - xs).mean()),
                        "maxAbsDiff": float(np.abs(y[..., index] - x[..., index]).max())}
    return out


def sectionB(cv2, device):
    a1, shapeA = meanFrame(cv2, device, True)
    b, shapeB = meanFrame(cv2, device, False)
    a2, _ = meanFrame(cv2, device, True)
    reference = (a1 + a2) / 2
    return {"source": V4L2_SOURCE, "shapeBackend": list(shapeA), "shapeOurs": list(shapeB),
            "framesEach": AVERAGE_FRAMES, "codeYUYV_eq_YUY2": cv2.COLOR_YUV2BGR_YUYV == cv2.COLOR_YUV2BGR_YUY2,
            "A2_vs_A1_noiseFloor": fit(a1, a2), "ours_vs_backend": fit(reference, b),
            "meanLevel": [float(v) for v in reference.reshape(-1, 3).mean(axis=0)]}


# --------------------------------------------------------------------------------------------- S: settling

def record(cap, frames):
    series, t0 = [], time.monotonic()
    while len(series) < frames:
        bgr = readBgr(cap)
        if bgr is None:
            continue
        stats = frameStats(bgr)
        stats["t"] = round(time.monotonic() - t0, 3)
        series.append(stats)
    return series


def settledAt(series, key):
    """First frame index from which every frame lies within the plateau band (last PLATEAU_FRAMES frames:
    median ± max(4·1.4826·MAD, 0.3 % of the median))."""
    values = np.array([frame[key] for frame in series])
    plateau = values[-PLATEAU_FRAMES:]
    median = float(np.median(plateau))
    band = max(4 * 1.4826 * float(np.median(np.abs(plateau - median))), 0.003 * abs(median))
    inside = np.abs(values - median) <= band
    index = len(values)
    while index > 0 and inside[index - 1]:
        index -= 1
    return {"key": key, "settledAtFrame": int(index), "plateau": median, "band": band,
            "first": float(values[0]), "frameIntervalS": float(np.diff([f["t"] for f in series]).mean())}


def leaveAtDefaults(cv2, device):
    """Leave the camera in the CALIBRATION state (auto WB, default exposure/backlight) — what a measurement open
    meets after a calibration. Without this the open below changes nothing: UVC values persist in the camera."""
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_EXPOSURE, 150)                  # the ELP's calibrationExposure
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)
    cap.set(cv2.CAP_PROP_BACKLIGHT, 1)
    for _ in range(12):                                  # let auto WB converge on the lamp
        cap.read()
    cap.release()


def sectionS(cv2, device):
    leaveAtDefaults(cv2, device)
    cap, openSeconds = openMeasurement(cv2, device)
    try:
        events = {}
        series = record(cap, SETTLE_FRAMES)
        events["open"] = {"openSeconds": round(openSeconds, 2), "series": series,
                          "mean": settledAt(series, "g"), "bOverR": settledAt(series, "bOverR")}
        for label, value in (("exposure %d→%d" % (EXPOSURE, EXPOSURE_STEP), EXPOSURE_STEP),
                             ("exposure %d→%d" % (EXPOSURE_STEP, EXPOSURE), EXPOSURE)):
            cap.set(cv2.CAP_PROP_EXPOSURE, value)
            series = record(cap, SETTLE_FRAMES)
            events[label] = {"series": series, "mean": settledAt(series, "g"), "bOverR": settledAt(series, "bOverR")}
        for label, value in (("WB %d→%d" % (WB_KELVIN, WB_OTHER), WB_OTHER), ("WB %d→%d" % (WB_OTHER, WB_KELVIN),
                                                                             WB_KELVIN)):
            cap.set(cv2.CAP_PROP_WB_TEMPERATURE, value)
            series = record(cap, SETTLE_FRAMES)
            events[label] = {"series": series, "mean": settledAt(series, "g"), "bOverR": settledAt(series, "bOverR")}
        return events
    finally:
        cap.release()


# --------------------------------------------------------------------------------------------- report

def summary(report):
    lines = ["# W1.4 Linux camera probe — %s" % report["when"], ""]
    b = report["B"]
    lines += ["## B bit-identity", "", "backend shape %s, ours %s, %d frames each; YUYV code == YUY2 code: %s"
              % (b["shapeBackend"], b["shapeOurs"], b["framesEach"], b["codeYUYV_eq_YUY2"]), "",
              "| pair | ch | slope | offset | mean diff | max abs diff |", "|---|---|---|---|---|---|"]
    for pair in ("A2_vs_A1_noiseFloor", "ours_vs_backend"):
        for channel, f in b[pair].items():
            lines.append("| %s | %s | %.5f | %+.3f | %+.3f | %.2f |"
                         % (pair, channel, f["slope"], f["offset"], f["meanDiff"], f["maxAbsDiff"]))
    lines += ["", "## S settling (frames read after the event until settled)", "",
              "| event | G mean: settled at | first → plateau | B/R: settled at | first → plateau | frame Δt s |",
              "|---|---|---|---|---|---|"]
    for label, event in report["S"].items():
        m, r = event["mean"], event["bOverR"]
        lines.append("| %s | %d | %.2f → %.2f | %d | %.4f → %.4f | %.2f |"
                     % (label, m["settledAtFrame"], m["first"], m["plateau"], r["settledAtFrame"], r["first"],
                        r["plateau"], m["frameIntervalS"]))
    lines += ["", "## K controls (as found / after measurement open / default)", "",
              "| control | min..max | default | as found | after open |", "|---|---|---|---|---|"]
    after = {c["name"]: c for c in report["K"]["afterOpen"]}
    for control in report["K"]["asFound"]:
        later = after.get(control["name"], {})
        lines.append("| %s | %d..%d | %d | %s | %s |" % (
            control["name"], control["min"], control["max"], control["default"],
            control.get("valueName", control["value"]), later.get("valueName", later.get("value"))))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--out", default=None)
    parser.add_argument("--no-lamp", action="store_true", help="do not switch the Shelly (lamp on by hand)")
    args = parser.parse_args()
    import cv2
    node = "/dev/video%d" % args.device
    report = {"when": datetime.now().isoformat(timespec="seconds"), "opencv": cv2.__version__, "device": node}
    report["K"] = {"asFound": readControls(node)}
    try:
        if not args.no_lamp:
            lamp(True, toggleAfter=900)                 # dead-man: dark again in 15 min whatever happens here
            print("lamp on, warming up %d s" % LAMP_WARMUP_S, flush=True)
            time.sleep(LAMP_WARMUP_S)
        cap, _ = openMeasurement(cv2, args.device)
        peak = max(frame["peak"] for frame in record(cap, 4))
        cap.release()
        if peak < 50:                                    # a dark frame would make every section meaningless
            raise SystemExit("frame is dark (p99.9 peak %.0f) — lamp in the socket, socket switch on, jar/slit?"
                             % peak)
        print("S settling ...", flush=True)
        report["S"] = sectionS(cv2, args.device)
        report["K"]["afterOpen"] = readControls(node)    # the measurement state the last open left in the camera
        print("B bit-identity ...", flush=True)
        report["B"] = sectionB(cv2, args.device)
    finally:
        if not args.no_lamp:
            lamp(False)
    text = summary(report)
    print(text)
    out = args.out or "w14_linux_probe_%s" % datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print("\nwritten to %s" % out)


if __name__ == "__main__":
    sys.exit(main())
