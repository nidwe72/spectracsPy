"""CS2 — the camera's UVC controls on Linux, set and read back through V4L2 ioctls (SPEC_camera_settings.md §5).

The twin of `WindowsUvcControls`: the ONE writer of every image control on Linux. OpenCV keeps only the stream
(format, size, buffer size, CONVERT_RGB); every control goes through here, because

  * UVC values PERSIST IN THE CAMERA — whatever the last program left is the next open's starting point, so every
    open writes every control (§2);
  * `cv2.set()` returns True on V4L2 even when it did nothing, and OpenCV exposes values but not ranges, steps,
    defaults or menus — this asks the driver for all of them (`VIDIOC_QUERYCTRL` / `QUERYMENU`);
  * the GUI thread reads back while the capture thread streams: an own fd (the kernel serialises ioctls) plus a
    lock, instead of calling into the worker's `VideoCapture` (E6).

ℹ What the read-back proves: uvcvideo answers `G_CTRL` from its cache once a control is loaded, so it catches
driver clamping and refusals, NOT a camera that silently ignores `SET_CUR` (§5). Stated, not hidden.

`fcntl` is imported lazily: this module is imported on Windows too (R7).
"""
import os
import struct
import threading

from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl
from sciens.spectracs.plugin_sdk.camera.CameraSettings import CameraSettings
from sciens.spectracs.logic.camera.CameraDevice import CameraDevice, CameraControlRange

C = CameraControl

# V4L2 control ids (videodev2.h) for the OS-neutral names (§3.1).
CONTROL_IDS = {
    C.BRIGHTNESS: 0x00980900, C.CONTRAST: 0x00980901, C.SATURATION: 0x00980902, C.HUE: 0x00980903,
    C.WHITE_BALANCE_AUTO: 0x0098090C, C.GAMMA: 0x00980910, C.GAIN: 0x00980913,
    C.POWER_LINE_FREQUENCY: 0x00980918, C.WHITE_BALANCE_KELVIN: 0x0098091A, C.SHARPNESS: 0x0098091B,
    C.BACKLIGHT: 0x0098091C,
    C.AUTO_EXPOSURE: 0x009A0901, C.EXPOSURE: 0x009A0902, C.DYNAMIC_FRAMERATE: 0x009A0903,
}

FLAG_DISABLED, FLAG_READ_ONLY = 0x0001, 0x0004
TYPE_BOOLEAN, TYPE_MENU = 2, 3

# ⛔ EXPOSURE_AUTO is a MENU, not a boolean: 0 AUTO, 1 MANUAL, 2 SHUTTER_PRIORITY, 3 APERTURE_PRIORITY — the value
# that means "auto-exposure OFF" is 1 (CaptureBackend's old `__exposureModeName` docstring cost an evening twice).
# UVC cameras usually publish only 1 and 3; "AUTO" is written as 3 where offered, else 0.
_EXPOSURE_MODES = {1: "MANUAL", 0: "AUTO", 3: "AUTO", 2: "AUTO"}
_POWER_LINE = {0: "DISABLED", 1: "50", 2: "60", 3: "AUTO"}


def _iowr(number, size):
    return 0xC0000000 | (size << 16) | (ord("V") << 8) | number


VIDIOC_G_CTRL = _iowr(27, 8)
VIDIOC_S_CTRL = _iowr(28, 8)
VIDIOC_QUERYCTRL = _iowr(36, 68)
VIDIOC_QUERYMENU = _iowr(37, 44)


class V4l2Node:
    """The four ioctls, on one fd. Every method answers None/an error text instead of raising — a control that
    will not answer simply says nothing. Tests replace this whole object with a fake."""

    def __init__(self, path):
        self.path = path
        self.__descriptor = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def queryControl(self, controlId):
        """{"type", "min", "max", "step", "default", "flags"} or None."""
        import fcntl
        buffer = bytearray(struct.pack("I", controlId) + bytes(64))
        try:
            fcntl.ioctl(self.__descriptor, VIDIOC_QUERYCTRL, buffer, True)
        except OSError:
            return None
        kind = struct.unpack_from("I", buffer, 4)[0]
        low, high, step, default, flags = struct.unpack_from("iiiiI", buffer, 40)
        return {"type": kind, "min": low, "max": high, "step": step, "default": default, "flags": flags}

    def queryMenu(self, controlId, index):
        import fcntl
        buffer = bytearray(struct.pack("=II32sI", controlId, index, b"", 0))
        try:
            fcntl.ioctl(self.__descriptor, VIDIOC_QUERYMENU, buffer, True)
        except OSError:
            return None
        return struct.unpack("=II32sI", bytes(buffer))[2].split(b"\0")[0].decode("ascii", "replace") or None

    def get(self, controlId):
        import fcntl
        buffer = bytearray(struct.pack("Ii", controlId, 0))
        try:
            fcntl.ioctl(self.__descriptor, VIDIOC_G_CTRL, buffer, True)
        except OSError:
            return None
        return struct.unpack_from("i", buffer, 4)[0]

    def set(self, controlId, value):
        """None on success, else the errno name."""
        import errno
        import fcntl
        buffer = bytearray(struct.pack("Ii", controlId, int(value)))
        try:
            fcntl.ioctl(self.__descriptor, VIDIOC_S_CTRL, buffer, True)
        except OSError as error:
            return errno.errorcode.get(error.errno, str(error.errno))
        return None

    def close(self):
        try:
            os.close(self.__descriptor)
        except OSError:
            pass


def cameraIdentity(deviceId):
    """{name, vendorId, modelId} of /dev/video<deviceId> from sysfs — best-effort, {} on anything unexpected."""
    if not isinstance(deviceId, int):
        return {}
    base = "/sys/class/video4linux/video%d" % deviceId
    identity = {}
    for key, relative in (("name", "name"), ("vendorId", "device/../idVendor"), ("modelId", "device/../idProduct")):
        try:
            with open(os.path.join(base, relative)) as handle:
                identity[key] = handle.read().strip()
        except OSError:
            pass
    return identity


class LinuxUvcControls:
    """Every UVC control of ONE /dev/videoN: describe (firmware defaults, ranges, menus), apply a resolution in
    order, read back, and the live exposure change. All model values in, all model values out (§3.1)."""

    def __init__(self, node):
        self.__node = node
        self.__lock = threading.Lock()
        self.__described = None
        self.__menus = {}

    @classmethod
    def forDevice(cls, deviceId):
        """The controls of the node the resolver found, or None when there is no such node.

        Safe: on Linux the cv2 V4L2 index IS the sysfs N (`SensorCaptureIndexResolver`), and cv2 opens exactly
        /dev/video<N>."""
        if not isinstance(deviceId, int):
            return None
        path = "/dev/video%d" % deviceId
        if not os.path.exists(path):
            return None
        try:
            return cls(V4l2Node(path))
        except OSError:
            return None

    # --- describe ---

    def describe(self):
        """CameraDevice — what the camera offers, from QUERYCTRL/QUERYMENU. Cached: the firmware's answer does not
        change under an open device."""
        with self.__lock:
            if self.__described is None:
                self.__described = self.__describe()
            return self.__described

    def __describe(self):
        ranges = {}
        self.__menus = {}
        for control, controlId in CONTROL_IDS.items():
            query = self.__node.queryControl(controlId)
            if query is None or query["flags"] & (FLAG_DISABLED | FLAG_READ_ONLY):
                continue
            if query["type"] == TYPE_MENU:
                offered = [index for index in range(query["min"], query["max"] + 1)
                           if self.__node.queryMenu(controlId, index) is not None]
                table = _EXPOSURE_MODES if control is C.AUTO_EXPOSURE else _POWER_LINE
                if control is C.AUTO_EXPOSURE:
                    menu = {"MANUAL": 1} if 1 in offered else {}
                    automatic = next((index for index in (3, 0, 2) if index in offered), None)
                    if automatic is not None:
                        menu["AUTO"] = automatic
                else:
                    menu = {table[index]: index for index in offered if index in table}
                self.__menus[control] = menu
                choices = [name for name in (["MANUAL", "AUTO"] if control is C.AUTO_EXPOSURE
                                             else ["DISABLED", "50", "60", "AUTO"])
                           if name in self.__menus[control]]
                ranges[control] = CameraControlRange(table.get(query["default"]), choices=choices)
            elif query["type"] == TYPE_BOOLEAN:
                ranges[control] = CameraControlRange(bool(query["default"]), choices=[False, True])
            else:
                ranges[control] = CameraControlRange(query["default"], query["min"], query["max"],
                                                     query["step"] or 1)
        return CameraDevice(ranges)

    # --- write / read ---

    def apply(self, resolution):
        """Write every requested control in the resolution's order; return (applied read-back, failures)."""
        self.describe()
        failures = []
        with self.__lock:
            for control, value in resolution.writes():
                error = self.__node.set(CONTROL_IDS[control], self.__toRaw(control, value))
                if error is not None:
                    failures.append("%s: %s" % (control.value, error))
        return self.read(), failures

    def setExposure(self, exposure):
        """The live change (AE sweep, slider, the lock onto the sample): manual mode re-asserted first — many UVC
        drivers ignore a mid-stream value otherwise — then the value. Returns the READ-BACK, or None."""
        self.describe()
        with self.__lock:
            if C.AUTO_EXPOSURE in self.__menus:
                self.__node.set(CONTROL_IDS[C.AUTO_EXPOSURE], self.__toRaw(C.AUTO_EXPOSURE, "MANUAL"))
            self.__node.set(CONTROL_IDS[C.EXPOSURE], int(exposure))
            return self.__node.get(CONTROL_IDS[C.EXPOSURE])

    def read(self):
        """CameraSettings of every control the camera offers, as it reads back now."""
        device = self.describe()
        values = {}
        with self.__lock:
            for control in device.ranges:
                raw = self.__node.get(CONTROL_IDS[control])
                if raw is not None:
                    values[control] = self.__fromRaw(control, raw)
        return CameraSettings(values)

    def close(self):
        with self.__lock:
            self.__node.close()

    def __toRaw(self, control, value):
        if control in self.__menus:
            return self.__menus[control][value]
        if isinstance(value, bool):
            return 1 if value else 0
        return int(value)

    def __fromRaw(self, control, raw):
        if control is C.AUTO_EXPOSURE:
            return _EXPOSURE_MODES.get(raw, raw)
        if control is C.POWER_LINE_FREQUENCY:
            return _POWER_LINE.get(raw, raw)
        if self.__described.rangeOf(control).choices == [False, True]:
            return bool(raw)
        return raw
