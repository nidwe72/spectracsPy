"""R0 — resolve a SpectrometerSensor's USB VID/PID to its cv2 capture index (Linux sysfs, Windows MSMF).

Lifted from the verified standalone probe (`camera_capture_probe.py`). The distinction that makes this
necessary: `usb.core.find(vid, pid)` (`ApplicationSpectrometerUtil.isSensorConnected`) only answers
*presence* — is a device with this VID/PID on the bus? It cannot yield the integer index that
`cv2.VideoCapture(N)` wants. On Linux the bridge from a USB device to a capture index is the V4L2 layer
exposed through sysfs: `/sys/class/video4linux/videoN` links back to its USB parent (idVendor/idProduct)
and carries an `index` file (0 = the capture node, >=1 = the UVC metadata node, which is NOT capturable).

On Windows there is no sysfs: the cv2 index is the device's POSITION in the backend's own enumeration, and MSMF
and DSHOW enumerate separately (SPEC_windows_build.md §6.1, W1.2). So the lookup enumerates through the backend
CaptureBackend opens — MSMF — with `cv2_enumerate_cameras`, whose device path carries `vid_32e4&pid_8830`. The
same enumeration answers presence on Windows (`isPresent`), so pyusb/libusb is not needed there (B6).

Returns `None` — so callers show the existing not-connected notice and REFUSE, never blindly open index 0 (R8) —
when: the sensor is virtual, the platform is neither Linux nor Windows (Android is deferred,
SPEC_real_camera_capture.md §2.1), or no matching capturable device is found.
"""
import glob
import os
import sys

from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor

# The backend Windows captures with — CaptureBackend pins it (§6.2); the index is only valid for that backend.
CAP_MSMF = 1400

# Enumeration failures already printed: the presence poll asks every 2 s, the log should say it once (cf. U4).
_reportedFailures = set()


class SensorCaptureIndexResolver:

    def __init__(self, enumerator=None):
        # `enumerator()` -> [camera with .index/.vid/.pid] in MSMF order; injectable for tests (W1.2).
        self.__enumerator = enumerator

    def resolveCaptureIndex(self, sensor: SpectrometerSensor):
        if sensor is None or sensor.isVirtual:
            return None
        if sys.platform.startswith('linux'):
            return self.__resolveByVidPid(sensor.vendorId, sensor.modelId)
        if sys.platform == 'win32':
            return self.__resolveByEnumeration(sensor.vendorId, sensor.modelId)
        return None  # Android is deferred — see spec §2.1.

    def isPresent(self, sensor: SpectrometerSensor) -> bool:
        """Windows presence (B6): is a device with this VID/PID in the MSMF enumeration? Same lookup as the index."""
        return self.__resolveByEnumeration(sensor.vendorId, sensor.modelId) is not None

    def __resolveByEnumeration(self, vid: str, pid: str):
        if not vid or not pid:
            return None
        # Parse outside the guard: a malformed VID/PID is a data bug and must stay loud (U5).
        vendorId, modelId = int(vid, 16), int(pid, 16)
        try:
            cameras = self.__enumerator() if self.__enumerator is not None else self.__enumerateMsmf()
        except Exception as exception:
            message = "%s: %s" % (type(exception).__name__, exception)
            if message not in _reportedFailures:
                _reportedFailures.add(message)
                print("SensorCaptureIndexResolver: camera enumeration failed (%s) - not connected" % message)
            return None
        matches = sorted(camera.index for camera in cameras if camera.vid == vendorId and camera.pid == modelId)
        return matches[0] if matches else None

    @staticmethod
    def __enumerateMsmf():
        from cv2_enumerate_cameras import enumerate_cameras
        return enumerate_cameras(CAP_MSMF)

    def __resolveByVidPid(self, vid: str, pid: str):
        if not vid or not pid:
            return None

        matches = []
        for node in sorted(glob.glob("/sys/class/video4linux/video*")):
            try:
                n = int(os.path.basename(node).replace("video", ""))
            except ValueError:
                continue
            try:
                with open(os.path.join(node, "device/../idVendor")) as f:
                    nvid = f.read().strip().lower()
                with open(os.path.join(node, "device/../idProduct")) as f:
                    npid = f.read().strip().lower()
            except OSError:
                continue

            if nvid == vid.lower() and npid == pid.lower():
                v4lIndex = None
                try:
                    with open(os.path.join(node, "index")) as f:
                        v4lIndex = int(f.read().strip())
                except OSError:
                    pass
                matches.append((n, v4lIndex))

        if not matches:
            return None

        # Prefer the capture node (v4l index 0); the metadata node is index >= 1 and cannot capture.
        matches.sort(key=lambda m: (m[1] if m[1] is not None else 99, m[0]))
        return matches[0][0]
