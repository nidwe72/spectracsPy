#!/usr/bin/env python3
"""CS0 — which UVC controls does the camera offer through DirectShow? (SPEC_camera_settings.md §3.1, D5)

W1.0b probed VideoProcAmp ids 0–5 and 7–9 only. This reads EVERY id the KS property sets define — VideoProcAmp
0–13 (6 ColorEnable, 10/11 DigitalMultiplier(Limit), 12 WhiteBalanceComponent, 13 PowerlineFrequency) and
CameraControl 0–19 (19 AutoExposurePriority = V4L2's "dynamic framerate") — through the app's OWN interface
declarations (`WindowsUvcControls`), so what it finds is what the app can use. ⛔ READ-ONLY: GetRange + Get only.

Run in the VM (ELP passed through), from a folder holding this file and the app sources on PYTHONPATH:
    C:\\spectracs-build\\venv\\Scripts\\python windows_cs0_controls_probe.py --out cs0.json
"""
import argparse
import json
import sys

VIDEO_PROC_AMP = {0: "Brightness", 1: "Contrast", 2: "Hue", 3: "Saturation", 4: "Sharpness", 5: "Gamma",
                  6: "ColorEnable", 7: "WhiteBalance", 8: "BacklightCompensation", 9: "Gain",
                  10: "DigitalMultiplier", 11: "DigitalMultiplierLimit", 12: "WhiteBalanceComponent",
                  13: "PowerlineFrequency"}
CAMERA_CONTROL = {0: "Pan", 1: "Tilt", 2: "Roll", 3: "Zoom", 4: "Exposure", 5: "Iris", 6: "Focus",
                  7: "ScanMode", 8: "Privacy", 9: "PanTilt", 10: "PanRelative", 11: "TiltRelative",
                  12: "RollRelative", 13: "ZoomRelative", 14: "ExposureRelative", 15: "IrisRelative",
                  16: "FocusRelative", 17: "PanTiltRelative", 18: "FocalLength", 19: "AutoExposurePriority"}


def readAll(interface, ids):
    found = {}
    for prop, name in ids.items():
        entry = {"id": prop}
        try:
            low, high, step, default, caps = interface.GetRange(prop)
            entry.update({"min": low, "max": high, "step": step, "default": default, "caps": caps})
        except Exception as error:
            entry["range"] = "not offered (%s)" % type(error).__name__
        try:
            value, flags = interface.Get(prop)
            entry.update({"value": value, "flags": flags})
        except Exception as error:
            entry["get"] = "%s" % type(error).__name__
        found[name] = entry
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vidpid", default="32e4:8830")
    parser.add_argument("--out", default="cs0.json")
    args = parser.parse_args()
    from cv2_enumerate_cameras import enumerate_cameras
    from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import CAP_MSMF
    from sciens.spectracs.logic.application.video.capture.WindowsUvcControls import DirectShowCamera
    vid, pid = (int(part, 16) for part in args.vidpid.split(":"))
    camera = next((c for c in enumerate_cameras(CAP_MSMF) if c.vid == vid and c.pid == pid), None)
    if camera is None:
        raise SystemExit("camera %s not enumerated by MSMF" % args.vidpid)
    procAmp, cameraControl = DirectShowCamera(camera.path).bind()
    report = {"camera": camera.name, "videoProcAmp": readAll(procAmp, VIDEO_PROC_AMP),
              "cameraControl": readAll(cameraControl, CAMERA_CONTROL)}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    for family in ("videoProcAmp", "cameraControl"):
        for name, entry in report[family].items():
            if "min" in entry:
                print("%-14s %2d %-24s min=%s max=%s step=%s default=%s caps=%s value=%s flags=%s"
                      % (family, entry["id"], name, entry["min"], entry["max"], entry["step"], entry["default"],
                         entry["caps"], entry.get("value"), entry.get("flags")))
    print("not offered:", ", ".join("%s.%s" % (family, name) for family in ("videoProcAmp", "cameraControl")
                                    for name, entry in report[family].items() if "min" not in entry))


if __name__ == "__main__":
    sys.exit(main())
