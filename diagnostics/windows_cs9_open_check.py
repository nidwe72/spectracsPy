#!/usr/bin/env python3
"""CS9 — the real ELP through the real CaptureBackend in the VM (SPEC_camera_settings.md §9): every profile opens,
every control is written natively and reads back, a pinned 90 runs as −7 = 78, and the live exposure returns the
whole step. Prints the open records; writes nothing but what an app open writes anyway.

    C:\\spectracs-build\\venv\\Scripts\\python diagnostics\\windows_cs9_open_check.py
"""
import json
import sys

from sciens.spectracs.logic.application.video.capture.CaptureBackend import CaptureBackend, DesktopCv2CaptureBackend
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import CAP_MSMF
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile


def main():
    from cv2_enumerate_cameras import enumerate_cameras
    index = next(camera.index for camera in enumerate_cameras(CAP_MSMF) if (camera.vid, camera.pid) == (0x32E4, 0x8830))
    print("readDeviceDefaults:", CaptureBackend.readDeviceDefaults(index).defaults().toJson())
    for profile, override, seed in ((CameraProfile.MEASUREMENT, {"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500}, 150),
                                    (CameraProfile.CALIBRATION, None, 150), (CameraProfile.IDLE, None, 150)):
        backend = DesktopCv2CaptureBackend()
        record = backend.open(index, profile, override=override, exposureSeed=seed)
        frames = sum(1 for _ in range(10) if backend.read() is not None)
        print("\n== %s  refusal=%s  frames=%d/10" % (profile.value, record.refusal, frames))
        print("requested:", json.dumps(record.requested))
        print("applied:  ", json.dumps(record.applied))
        print("adjusted: ", record.adjusted, " mismatches:", record.mismatches, " failures:", record.failures)
        settings = backend.readCameraSettings()
        print("settings: exposure=%s native=%s range=%s..%s autoExposure=%s wb=%s autoWb=%s backlight=%s"
              % (settings.get("exposure"), settings.get("exposureNative"), settings.get("exposureMin"),
                 settings.get("exposureMax"), settings.get("autoExposure"), settings.get("wbTemperature"),
                 settings.get("autoWb"), settings.get("backlight")))
        if profile is CameraProfile.MEASUREMENT:
            print("setExposure 90 ->", backend.setExposure(90), " 104 ->", backend.setExposure(104),
                  " 150 ->", backend.setExposure(150), " native now", settings.get("exposureNative"))
        backend.release()


if __name__ == "__main__":
    sys.exit(main())
