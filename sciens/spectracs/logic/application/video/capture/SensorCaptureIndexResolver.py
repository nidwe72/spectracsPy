"""R0 — resolve a SpectrometerSensor's USB VID/PID to its cv2 capture index (Linux sysfs).

Lifted from the verified standalone probe (`camera_capture_probe.py`). The distinction that makes this
necessary: `usb.core.find(vid, pid)` (`ApplicationSpectrometerUtil.isSensorConnected`) only answers
*presence* — is a device with this VID/PID on the bus? It cannot yield the integer index that
`cv2.VideoCapture(N)` wants. On Linux the bridge from a USB device to a capture index is the V4L2 layer
exposed through sysfs: `/sys/class/video4linux/videoN` links back to its USB parent (idVendor/idProduct)
and carries an `index` file (0 = the capture node, >=1 = the UVC metadata node, which is NOT capturable).

Returns `None` — so callers show the existing not-connected notice instead of blindly opening index 0 —
when: the sensor is virtual, the platform is not Linux (Windows moniker-path resolution is a deferred
milestone, SPEC_real_camera_capture.md §2.1), or no matching capturable node is found.
"""
import glob
import os
import sys

from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class SensorCaptureIndexResolver:

    def resolveCaptureIndex(self, sensor: SpectrometerSensor):
        if sensor is None or sensor.isVirtual:
            return None
        if not sys.platform.startswith('linux'):
            # Windows (DirectShow moniker path) / Android are deferred — see spec §2.1.
            return None
        return self.__resolveByVidPid(sensor.vendorId, sensor.modelId)

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
