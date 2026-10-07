#!/usr/bin/env python3
"""W1.0b Windows UVC controls probe — docs/SPEC_windows_build.md §6.6b, option (d).

The W1.0 spike showed that OpenCV can neither set white balance nor exposure finer than whole log2 steps on
Windows (DSHOW and MSMF). But DSHOW *read back* a white balance of 4600 — so the camera exposes the control and
OpenCV merely fails to set it. This probe talks to the camera's controls DIRECTLY through DirectShow
(IAMVideoProcAmp / IAMCameraControl via comtypes, interface plumbing from pygrabber), while the frames still come
from MSMF as raw YUY2 converted by our own cvtColor (the W1.0 conversion route). It answers:

  R  ranges   — min / max / step / default / auto-manual capability of every VideoProcAmp and CameraControl
                property, and its current value + mode. ⭐ Is the exposure step 1 (= whole log2) or finer?
  W  white balance — set MANUAL 6500 K: does the read-back say manual 6500, does 3000 K visibly change the image,
                does 6500 K bring it back, and does the blue/red ratio then STAY put (the Linux §14.8 freeze)?
                Baseline: the drift with WB on auto, same duration.
  P  persistence — after the DirectShow handle is released and re-bound, is WB still manual?
  E  exposure — set via CameraControl (manual flag) at the same log2 value: same brightness as via OpenCV?

At the end every control touched is RESTORED to the value and mode it was found in.
READ-ONLY towards the app (no DB, no app code). ⛔ Device paths are scrubbed (public repo).

Run in the VM (ELP passed through, lamp ON, empty jar), in a venv with opencv-python (non-headless) + pygrabber:
    C:\\spectracs-build\\probe-venv-full\\Scripts\\python windows_uvc_controls_probe.py --vidpid 32e4:8830
"""
import argparse
import json
import os
import re
import sys
import time
from ctypes import POINTER, byref, c_long
from datetime import datetime

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

WIDTH, HEIGHT = 2592, 1944
FLAG_AUTO, FLAG_MANUAL = 1, 2

VIDEO_PROC_AMP = {0: "Brightness", 1: "Contrast", 2: "Hue", 3: "Saturation", 4: "Sharpness", 5: "Gamma",
                  6: "ColorEnable", 7: "WhiteBalance", 8: "BacklightCompensation", 9: "Gain"}
CAMERA_CONTROL = {0: "Pan", 1: "Tilt", 2: "Roll", 3: "Zoom", 4: "Exposure", 5: "Iris", 6: "Focus"}
WHITE_BALANCE, EXPOSURE = 7, 4


def scrub(text):
    match = re.search(r"vid_([0-9a-f]{4}).{0,3}pid_([0-9a-f]{4})", str(text), re.IGNORECASE)
    return "vid_%s&pid_%s <scrubbed>" % (match.group(1).lower(), match.group(2).lower()) if match else "<scrubbed>"


def flagName(flags):
    if flags is None:
        return None
    names = [name for bit, name in ((FLAG_AUTO, "auto"), (FLAG_MANUAL, "manual")) if flags & bit]
    return "+".join(names) or str(flags)


# --------------------------------------------------------------------------------------------- DirectShow

def comInterfaces():
    """IAMVideoProcAmp and IAMCameraControl share one vtable layout: GetRange, Set, Get (strmif.h)."""
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

    def methods():
        return [
            COMMETHOD([], HRESULT, "GetRange", (["in"], c_long, "Property"),
                      (["out"], POINTER(c_long), "pMin"), (["out"], POINTER(c_long), "pMax"),
                      (["out"], POINTER(c_long), "pSteppingDelta"), (["out"], POINTER(c_long), "pDefault"),
                      (["out"], POINTER(c_long), "pCapsFlags")),
            COMMETHOD([], HRESULT, "Set", (["in"], c_long, "Property"), (["in"], c_long, "lValue"),
                      (["in"], c_long, "Flags")),
            COMMETHOD([], HRESULT, "Get", (["in"], c_long, "Property"),
                      (["out"], POINTER(c_long), "lValue"), (["out"], POINTER(c_long), "Flags")),
        ]

    class IAMVideoProcAmp(IUnknown):
        _iid_ = GUID("{C6E13360-30AC-11d0-A18C-00A0C9118956}")
        _methods_ = methods()

    class IAMCameraControl(IUnknown):
        _iid_ = GUID("{C6E13370-30AC-11d0-A18C-00A0C9118956}")
        _methods_ = methods()

    return IAMVideoProcAmp, IAMCameraControl


def bindCamera(vidpid):
    """The camera's DirectShow capture filter, found by VID/PID in its DevicePath. Returns (filter, name)."""
    from comtypes import GUID, client
    from comtypes.persist import IPropertyBag
    from pygrabber.dshow_core import ICreateDevEnum, qedit
    from pygrabber.dshow_ids import DeviceCategories, clsids
    vid, pid = vidpid.lower().split(":")
    enumerator = client.CreateObject(clsids.CLSID_SystemDeviceEnum, interface=ICreateDevEnum)
    monikers = enumerator.CreateClassEnumerator(GUID(DeviceCategories.VideoInputDevice), dwFlags=0)
    moniker, count = monikers.Next(1)
    while count > 0:
        bag = moniker.BindToStorage(0, 0, IPropertyBag._iid_).QueryInterface(IPropertyBag)
        name = bag.Read("FriendlyName", pErrorLog=None)
        try:
            path = str(bag.Read("DevicePath", pErrorLog=None)).lower()
        except Exception:
            path = ""
        if "vid_%s" % vid in path and "pid_%s" % pid in path:
            return moniker.BindToObject(0, 0, qedit.IBaseFilter._iid_).QueryInterface(qedit.IBaseFilter), name, scrub(path)
        moniker, count = monikers.Next(1)
    return None, None, None


class Controls:

    def __init__(self, vidpid):
        IAMVideoProcAmp, IAMCameraControl = comInterfaces()
        self.filter, self.name, self.path = bindCamera(vidpid)
        if self.filter is None:
            raise SystemExit("camera %s not found among DirectShow video input devices" % vidpid)
        self.procAmp = self.filter.QueryInterface(IAMVideoProcAmp)
        self.camera = self.filter.QueryInterface(IAMCameraControl)

    def interface(self, family):
        return self.procAmp if family == "VideoProcAmp" else self.camera

    def range(self, family, prop):
        try:
            low, high, step, default, caps = self.interface(family).GetRange(prop)
            return {"min": low, "max": high, "step": step, "default": default, "caps": flagName(caps)}
        except Exception as error:
            return {"unsupported": type(error).__name__}

    def get(self, family, prop):
        try:
            value, flags = self.interface(family).Get(prop)
            return {"value": value, "mode": flagName(flags), "flags": flags}
        except Exception as error:
            return {"error": type(error).__name__}

    def set(self, family, prop, value, flags):
        try:
            self.interface(family).Set(prop, int(value), int(flags))
            return True
        except Exception as error:
            return "%s: %s" % (type(error).__name__, error)

    def release(self):
        self.procAmp = self.camera = self.filter = None


# --------------------------------------------------------------------------------------------- frames (MSMF)

class Frames:

    def __init__(self, index, settle):
        import cv2
        self.cv2 = cv2
        self.settle = settle
        self.cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            raise SystemExit("MSMF could not open index %s (needs opencv-python, not -headless)" % index)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUY2"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)       # fixed at open — toggling breaks MSMF (W1.0)

    def bgr(self):
        for _ in range(12):
            ok, raw = self.cap.read()
            if ok and raw is not None and raw.size == WIDTH * HEIGHT * 2:
                return self.cv2.cvtColor(raw.reshape(HEIGHT, WIDTH, 2), self.cv2.COLOR_YUV2BGR_YUY2)
        return None

    def sample(self):
        image = self.bgr()
        if image is None:
            return None
        b, g, r = (float(image[..., i].mean()) for i in range(3))
        return {"blueOverRed": round(b / max(r, 1e-6), 4), "greenOverRed": round(g / max(r, 1e-6), 4),
                "mean": round(float(image.mean()), 2), "peak": round(float(np.percentile(image.max(axis=2), 99.9)), 1)}

    def settleThenSeries(self, frames):
        for _ in range(self.settle):
            self.bgr()
        return [s for s in (self.sample() for _ in range(frames)) if s is not None]

    def setExposureOpenCv(self, value):
        self.cap.set(self.cv2.CAP_PROP_EXPOSURE, value)

    def release(self):
        self.cap.release()


def drift(series, key="blueOverRed"):
    values = [s[key] for s in series]
    if len(values) < 2:
        return None
    return {"first": values[0], "last": values[-1], "min": min(values), "max": max(values),
            "spanPercent": round(100.0 * (max(values) - min(values)) / max(np.mean(values), 1e-6), 2),
            "n": len(values)}


# --------------------------------------------------------------------------------------------- run

def run(args):
    report = {"started": datetime.now().strftime("%Y-%m-%dT%H-%M-%S"), "args": vars(args)}
    controls = Controls(args.vidpid)
    report["device"] = {"name": controls.name, "path": controls.path}

    # R — every range and current state, BEFORE touching anything (also the restore point)
    found = {}
    for family, table in (("VideoProcAmp", VIDEO_PROC_AMP), ("CameraControl", CAMERA_CONTROL)):
        for prop, name in table.items():
            found["%s.%s" % (family, name)] = {"range": controls.range(family, prop), "now": controls.get(family, prop)}
    report["ranges"] = found
    print("== ranges / current state")
    for key, entry in found.items():
        if "unsupported" not in entry["range"]:
            print("  %-34s %s  now %s" % (key, entry["range"], entry["now"]))

    frames = Frames(args.index, args.settle)
    frames.setExposureOpenCv(args.exposure)
    controls.set("CameraControl", EXPOSURE, args.exposure, FLAG_MANUAL)

    # W — baseline drift with WB on AUTO, then the manual freeze
    wbRange = found["VideoProcAmp.WhiteBalance"]["range"]
    wbOriginal = found["VideoProcAmp.WhiteBalance"]["now"]
    white = {"range": wbRange, "original": wbOriginal}
    if "unsupported" in wbRange:
        white["verdict"] = "⛔ WhiteBalance not exposed through IAMVideoProcAmp"
    else:
        def clamp(kelvin):
            return max(wbRange["min"], min(wbRange["max"], kelvin))
        controls.set("VideoProcAmp", WHITE_BALANCE, wbOriginal.get("value", clamp(4600)), FLAG_AUTO)
        print("== WB auto, baseline %d frames" % args.frames)
        white["autoSeries"] = drift(frames.settleThenSeries(args.frames))
        steps = []
        for kelvin in (6500, 3000, 6500):
            target = clamp(kelvin)
            result = controls.set("VideoProcAmp", WHITE_BALANCE, target, FLAG_MANUAL)
            series = frames.settleThenSeries(4)
            steps.append({"requested": kelvin, "applied": target, "setResult": result,
                          "readBack": controls.get("VideoProcAmp", WHITE_BALANCE),
                          "blueOverRed": series[-1]["blueOverRed"] if series else None})
            print("  WB manual %s -> %s  B/R %s" % (target, steps[-1]["readBack"], steps[-1]["blueOverRed"]), flush=True)
        white["manualSteps"] = steps
        print("== WB manual %s, hold %d frames" % (clamp(6500), args.frames))
        white["manualSeries"] = drift(frames.settleThenSeries(args.frames))
        b65, b30 = steps[0]["blueOverRed"], steps[1]["blueOverRed"]
        honoured = None if None in (b65, b30) else abs(b65 - b30) > 0.03
        frozen = None
        if white["manualSeries"] and white["autoSeries"]:
            frozen = white["manualSeries"]["spanPercent"] <= max(0.5, 0.5 * white["autoSeries"]["spanPercent"])
        white["honoured"] = honoured
        white["frozen"] = frozen
        white["verdict"] = ("✅ WB settable AND stable under manual" if honoured and frozen else
                            "⚠ WB settable but still drifting" if honoured else
                            "⛔ WB set has no visible effect")

        # P — persistence across a release + re-bind of the DirectShow handle
        controls.release()
        again = Controls(args.vidpid)
        white["afterRebind"] = again.get("VideoProcAmp", WHITE_BALANCE)
        controls = again
    report["whiteBalance"] = white

    # E — exposure through CameraControl vs OpenCV, same log2 values
    expo = []
    for value in (args.exposure - 1, args.exposure):
        frames.setExposureOpenCv(value)
        viaOpenCv = frames.settleThenSeries(2)
        result = controls.set("CameraControl", EXPOSURE, value, FLAG_MANUAL)
        viaDshow = frames.settleThenSeries(2)
        expo.append({"value": value, "dshowSet": result, "readBack": controls.get("CameraControl", EXPOSURE),
                     "peakViaOpenCv": viaOpenCv[-1]["peak"] if viaOpenCv else None,
                     "peakViaDirectShow": viaDshow[-1]["peak"] if viaDshow else None})
    report["exposure"] = expo
    frames.release()

    # restore every control we touched to what it was
    restored = {}
    for key, family, prop in (("VideoProcAmp.WhiteBalance", "VideoProcAmp", WHITE_BALANCE),
                              ("CameraControl.Exposure", "CameraControl", EXPOSURE)):
        now = found[key]["now"]
        if "value" in now:
            restored[key] = controls.set(family, prop, now["value"], now["flags"])
    report["restored"] = restored
    controls.release()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--vidpid", default="32e4:8830")
    parser.add_argument("--index", type=int, default=0, help="MSMF index (W1.0 found the ELP at 0)")
    parser.add_argument("--exposure", type=int, default=-8, help="log2 exposure (W1.0: -8 is the last unclipped)")
    parser.add_argument("--frames", type=int, default=60, help="frames per drift series (~17 s at 3.6 fps)")
    parser.add_argument("--settle", type=int, default=5)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    report = run(args)
    out = args.out or os.path.join(os.getcwd(), "windows_uvc_controls_%s" % report["started"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)
    white = report["whiteBalance"]
    print()
    print("WB range      %s" % white.get("range"))
    print("WB auto drift %s" % white.get("autoSeries"))
    print("WB manual     %s" % white.get("manualSteps"))
    print("WB held drift %s" % white.get("manualSeries"))
    print("WB rebind     %s" % white.get("afterRebind"))
    print("⭐ %s" % white.get("verdict"))
    print("Exposure      %s" % report["ranges"]["CameraControl.Exposure"])
    print("Exposure set  %s" % report["exposure"])
    print("restored      %s" % report["restored"])
    print("written: %s" % out)


if __name__ == "__main__":
    main()
