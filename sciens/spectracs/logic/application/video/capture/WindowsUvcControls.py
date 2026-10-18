"""W1.6 + CS3 — the camera's UVC controls on Windows, set and read back NATIVELY (SPEC_windows_build.md §6.4b;
SPEC_camera_settings.md §5).

OpenCV cannot set white balance through MSMF or DSHOW, and MSMF's exposure read-back is broken (§6.6b). The camera
itself exposes every control to DirectShow — `IAMVideoProcAmp` (white balance, gain, backlight, brightness, …) and
`IAMCameraControl` (exposure) — so they are set and read there, while the frames keep coming from MSMF (W1.3).
⭐ CS3: the twin of `LinuxUvcControls` — describe (firmware defaults via GetRange), apply a resolution in order, read
back, and the live exposure — all in MODEL units (§3.1), so both OSes share one resolve() and one record.

⭐⭐ EXPOSURE IS CONVERTED HERE (§3.3a, D4). DirectShow exposure is whole log₂ SECONDS (the ELP: −13..−1); the model
and every plugin speak V4L2 units (100 µs): `v4l2 = 10000·2^k`. A pinned 90 therefore runs as k = −7 = 78 — the
quantiser says so before the write, so the read-back is compared with what the camera CAN do, and nothing is
refused on rounding.

⭐ The interfaces are declared here by hand with plain `comtypes` — no `pygrabber`, no `comtypes.client.GetModule`
(which generates code at runtime, a frozen-build risk, §6.7). Each call binds the camera afresh IN THE CALLING THREAD
and lets go again: the capture thread sets, the GUI thread reads back, and no COM pointer crosses an apartment.

CS0 (2026-10-18, the ELP in the VM): VideoProcAmp 0–5, 7–9 and 13 (PowerlineFrequency 0..2, no auto flag) are offered;
6, 10–12 are not; CameraControl 4 (Exposure −13..−1, default −7) and 19 (AutoExposurePriority, FIXED at 0 — reported,
never written). Pure parts (`deviceKey`, the converter) are tested on Linux.
"""
import math
import re

from sciens.spectracs.logic.camera.CameraDevice import CameraDevice, CameraControlRange
from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl
from sciens.spectracs.plugin_sdk.camera.CameraSettings import CameraSettings

C = CameraControl
FLAG_AUTO, FLAG_MANUAL = 1, 2

# IAMVideoProcAmp property ids (strmif.h VideoProcAmpProperty + KS 13 = PowerlineFrequency) for the model names.
VIDEO_PROC_AMP = {C.BRIGHTNESS: 0, C.CONTRAST: 1, C.HUE: 2, C.SATURATION: 3, C.SHARPNESS: 4, C.GAMMA: 5,
                  C.BACKLIGHT: 8, C.GAIN: 9, C.POWER_LINE_FREQUENCY: 13}
WHITE_BALANCE = 7
CAMERA_CONTROL_EXPOSURE = 4
CAMERA_CONTROL_AUTO_EXPOSURE_PRIORITY = 19
_POWER_LINE = {0: "DISABLED", 1: "50", 2: "60", 3: "AUTO"}

def toV4l2(log2Seconds):
    """DirectShow exposure (whole log₂ seconds) → model units (V4L2, 100 µs): −7 → 78."""
    return int(round(10000.0 * 2.0 ** int(log2Seconds)))


def toLog2(v4l2, low=-13, high=-1):
    """Model units → the NEAREST whole log₂ step the camera can do, clamped to its range: 90 → −7."""
    value = max(float(v4l2), 1e-6)
    return max(int(low), min(int(high), int(round(math.log2(value / 10000.0)))))


def deviceKey(path):
    """The part of a device path both backends share: MSMF's symbolic link and DirectShow's DevicePath differ only
    in the interface GUID after the last `#` (seen on the ELP in the VM)."""
    return (path or "").lower().rsplit("#", 1)[0]


_CLSID_SYSTEM_DEVICE_ENUM = "{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}"
_VIDEO_INPUT_DEVICE = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"


_interfaces = None


def _comInterfaces():
    """IAMVideoProcAmp / IAMCameraControl (same vtable: GetRange, Set, Get), ICreateDevEnum, IEnumMoniker, IMoniker —
    the minimum, declared once."""
    global _interfaces
    if _interfaces is not None:
        return _interfaces
    from ctypes import POINTER, c_long, c_ulong
    from comtypes import COMMETHOD, GUID, HRESULT, IPersist, IUnknown

    def controlMethods():
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
        _methods_ = controlMethods()

    class IAMCameraControl(IUnknown):
        _iid_ = GUID("{C6E13370-30AC-11d0-A18C-00A0C9118956}")
        _methods_ = controlMethods()

    class IPersistStream(IPersist):
        _iid_ = GUID("{00000109-0000-0000-C000-000000000046}")
        _methods_ = [COMMETHOD([], HRESULT, "IsDirty"), COMMETHOD([], HRESULT, "Load"),
                     COMMETHOD([], HRESULT, "Save"), COMMETHOD([], HRESULT, "GetSizeMax")]

    class IMoniker(IPersistStream):
        _iid_ = GUID("{0000000F-0000-0000-C000-000000000046}")

    class IEnumMoniker(IUnknown):
        _iid_ = GUID("{00000102-0000-0000-C000-000000000046}")

    IMoniker._methods_ = [
        COMMETHOD([], HRESULT, "BindToObject", (["in"], POINTER(IUnknown), "pbc"),
                  (["in"], POINTER(IMoniker), "pmkToLeft"), (["in"], POINTER(GUID), "riidResult"),
                  (["out"], POINTER(POINTER(IUnknown)), "ppvResult")),
        COMMETHOD([], HRESULT, "BindToStorage", (["in"], POINTER(IUnknown), "pbc"),
                  (["in"], POINTER(IMoniker), "pmkToLeft"), (["in"], POINTER(GUID), "riid"),
                  (["out"], POINTER(POINTER(IUnknown)), "ppvObj")),
    ]
    IEnumMoniker._methods_ = [
        COMMETHOD([], HRESULT, "Next", (["in"], c_ulong, "celt"),
                  (["out"], POINTER(POINTER(IMoniker)), "rgelt"), (["out"], POINTER(c_ulong), "pceltFetched")),
    ]

    class ICreateDevEnum(IUnknown):
        _iid_ = GUID("{29840822-5B84-11D0-BD3B-00A0C911CE86}")
        _methods_ = [
            COMMETHOD([], HRESULT, "CreateClassEnumerator", (["in"], POINTER(GUID), "clsidDeviceClass"),
                      (["out"], POINTER(POINTER(IEnumMoniker)), "ppEnumMoniker"), (["in"], c_ulong, "dwFlags")),
        ]

    _interfaces = (IAMVideoProcAmp, IAMCameraControl, ICreateDevEnum)
    return _interfaces


class DirectShowCamera:
    """The COM side of ONE camera, found by its device path (the MSMF symbolic link CaptureBackend opened).
    `bind()` returns (IAMVideoProcAmp, IAMCameraControl) bound IN THE CALLING THREAD. Raises on a camera that
    cannot be bound. Tests replace this whole object with a fake offering the same three COM methods."""

    def __init__(self, devicePath):
        self.__key = deviceKey(devicePath)
        match = re.search(r"vid_([0-9a-f]{4}).{0,3}pid_([0-9a-f]{4})", self.__key)
        self.__vidPid = match.groups() if match else None

    def bind(self):
        return self.__bind()

    def __bind(self):
        import comtypes
        from comtypes import GUID
        from comtypes.persist import IPropertyBag
        try:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        except OSError:
            pass                                      # this thread already has an apartment (Qt's GUI thread: STA)
        IAMVideoProcAmp, IAMCameraControl, ICreateDevEnum = _comInterfaces()
        devices = comtypes.CoCreateInstance(GUID(_CLSID_SYSTEM_DEVICE_ENUM), interface=ICreateDevEnum)
        monikers = devices.CreateClassEnumerator(GUID(_VIDEO_INPUT_DEVICE), 0)
        if not monikers:
            raise LookupError("no DirectShow video input devices")
        fallback = None
        while True:
            moniker, fetched = monikers.Next(1)
            if not fetched:
                break
            bag = moniker.BindToStorage(None, None, IPropertyBag._iid_).QueryInterface(IPropertyBag)
            try:
                path = str(bag.Read("DevicePath", pErrorLog=None))
            except Exception:
                continue
            if deviceKey(path) == self.__key:
                return self.__controlsOf(moniker, IAMVideoProcAmp, IAMCameraControl)
            if fallback is None and self.__vidPid and "vid_%s" % self.__vidPid[0] in path.lower() \
                    and "pid_%s" % self.__vidPid[1] in path.lower():
                fallback = moniker
        if fallback is not None:                       # same VID/PID, path shape differs: the only such camera
            return self.__controlsOf(fallback, IAMVideoProcAmp, IAMCameraControl)
        raise LookupError("camera not among the DirectShow video input devices")

    @staticmethod
    def __controlsOf(moniker, IAMVideoProcAmp, IAMCameraControl):
        filter_ = moniker.BindToObject(None, None, IAMVideoProcAmp._iid_)
        return filter_.QueryInterface(IAMVideoProcAmp), filter_.QueryInterface(IAMCameraControl)


class WindowsUvcControls:
    """Every UVC control of ONE camera through DirectShow, in MODEL units — the twin of `LinuxUvcControls`."""

    def __init__(self, devicePath, camera=None):
        self.__camera = camera if camera is not None else DirectShowCamera(devicePath)
        self.__described = None
        self.__exposureRange = (-13, -1)
        self.__fixed = set()            # offered with ONE value only (CS0: AutoExposurePriority) — read, never written

    # --- describe ---

    def describe(self):
        if self.__described is None:
            procAmp, camera = self.__camera.bind()
            self.__described = self.__describe(procAmp, camera)
        return self.__described

    def __describe(self, procAmp, camera):
        ranges = {}
        for control, prop in VIDEO_PROC_AMP.items():
            answer = _range(procAmp, prop)
            if answer is None:
                continue
            low, high, step, default, _caps = answer
            if control is C.POWER_LINE_FREQUENCY:
                ranges[control] = CameraControlRange(_POWER_LINE.get(default), choices=[
                    _POWER_LINE[index] for index in range(low, high + 1) if index in _POWER_LINE])
            else:
                ranges[control] = CameraControlRange(default, low, high, step or 1)
        whiteBalance = _range(procAmp, WHITE_BALANCE)
        if whiteBalance is not None:
            low, high, step, default, caps = whiteBalance
            ranges[C.WHITE_BALANCE_KELVIN] = CameraControlRange(default, low, high, step or 1)
            # ⚠ GetRange has no default MODE; an auto-capable control is taken to default to auto, as the same
            # camera reports through V4L2 (auto WB 1, aperture-priority exposure).
            ranges[C.WHITE_BALANCE_AUTO] = CameraControlRange(bool(caps & FLAG_AUTO), choices=(
                [False, True] if caps & FLAG_AUTO else [False]))
        exposure = _range(camera, CAMERA_CONTROL_EXPOSURE)
        if exposure is not None:
            low, high, _step, default, caps = exposure
            self.__exposureRange = (low, high)
            ranges[C.EXPOSURE] = CameraControlRange(
                toV4l2(default), toV4l2(low), toV4l2(high), 1,
                quantise=lambda v4l2, low=low, high=high: toV4l2(toLog2(v4l2, low, high)))   # bound NOW, not late
            ranges[C.AUTO_EXPOSURE] = CameraControlRange("AUTO" if caps & FLAG_AUTO else "MANUAL", choices=(
                ["MANUAL", "AUTO"] if caps & FLAG_AUTO else ["MANUAL"]))
        priority = _range(camera, CAMERA_CONTROL_AUTO_EXPOSURE_PRIORITY)
        if priority is not None:
            low, high, _step, default, _caps = priority
            if high > low:
                ranges[C.DYNAMIC_FRAMERATE] = CameraControlRange(bool(default), choices=[False, True])
            else:
                ranges[C.DYNAMIC_FRAMERATE] = CameraControlRange(bool(default), choices=[bool(default)])
                self.__fixed.add(C.DYNAMIC_FRAMERATE)
        return CameraDevice(ranges)

    # --- write / read ---

    def apply(self, resolution):
        """Write every requested control in the resolution's order; return (applied read-back, failures)."""
        self.describe()
        procAmp, camera = self.__camera.bind()
        failures = []
        for control, value in resolution.writes():
            if control in self.__fixed:
                continue
            try:
                self.__write(procAmp, camera, control, value)
            except Exception as error:
                failures.append("%s: %s" % (control.value, type(error).__name__))
        return self.__read(procAmp, camera), failures

    def __write(self, procAmp, camera, control, value):
        low, high = self.__exposureRange
        if control is C.AUTO_EXPOSURE:
            current, _ = camera.Get(CAMERA_CONTROL_EXPOSURE)
            camera.Set(CAMERA_CONTROL_EXPOSURE, current, FLAG_AUTO if value == "AUTO" else FLAG_MANUAL)
        elif control is C.EXPOSURE:
            camera.Set(CAMERA_CONTROL_EXPOSURE, toLog2(value, low, high), FLAG_MANUAL)
        elif control is C.WHITE_BALANCE_AUTO:
            current, _ = procAmp.Get(WHITE_BALANCE)
            procAmp.Set(WHITE_BALANCE, current, FLAG_AUTO if value else FLAG_MANUAL)
        elif control is C.WHITE_BALANCE_KELVIN:
            procAmp.Set(WHITE_BALANCE, int(value), FLAG_MANUAL)
        elif control is C.DYNAMIC_FRAMERATE:
            camera.Set(CAMERA_CONTROL_AUTO_EXPOSURE_PRIORITY, 1 if value else 0, FLAG_MANUAL)
        elif control is C.POWER_LINE_FREQUENCY:
            raw = next(index for index, name in _POWER_LINE.items() if name == value)
            procAmp.Set(VIDEO_PROC_AMP[control], raw, FLAG_MANUAL)
        else:
            procAmp.Set(VIDEO_PROC_AMP[control], int(value), FLAG_MANUAL)

    def setExposure(self, exposure):
        """The live change, in V4L2 units: manual at the nearest whole log₂ step. Returns the APPLIED value in V4L2
        units (90 → 78), read back from the camera, or None."""
        low, high = self.__exposureRange
        _procAmp, camera = self.__camera.bind()
        camera.Set(CAMERA_CONTROL_EXPOSURE, toLog2(exposure, low, high), FLAG_MANUAL)
        value, _ = camera.Get(CAMERA_CONTROL_EXPOSURE)
        return toV4l2(value)

    def nativeExposure(self):
        """The exposure as the camera holds it — whole log₂ seconds — for the record's `exposureNative`."""
        _procAmp, camera = self.__camera.bind()
        value, _ = camera.Get(CAMERA_CONTROL_EXPOSURE)
        return value

    def read(self):
        self.describe()
        procAmp, camera = self.__camera.bind()
        return self.__read(procAmp, camera)

    def __read(self, procAmp, camera):
        device = self.__described
        values = {}
        for control, prop in VIDEO_PROC_AMP.items():
            if not device.offers(control):
                continue
            try:
                value, _ = procAmp.Get(prop)
            except Exception:
                continue
            values[control] = _POWER_LINE.get(value, value) if control is C.POWER_LINE_FREQUENCY else value
        if device.offers(C.WHITE_BALANCE_KELVIN):
            try:
                value, flags = procAmp.Get(WHITE_BALANCE)
                values[C.WHITE_BALANCE_KELVIN] = value
                values[C.WHITE_BALANCE_AUTO] = bool(flags & FLAG_AUTO)
            except Exception:
                pass
        if device.offers(C.EXPOSURE):
            try:
                value, flags = camera.Get(CAMERA_CONTROL_EXPOSURE)
                values[C.EXPOSURE] = toV4l2(value)
                values[C.AUTO_EXPOSURE] = "AUTO" if flags & FLAG_AUTO else "MANUAL"
            except Exception:
                pass
        if device.offers(C.DYNAMIC_FRAMERATE):
            try:
                value, _ = camera.Get(CAMERA_CONTROL_AUTO_EXPOSURE_PRIORITY)
                values[C.DYNAMIC_FRAMERATE] = bool(value)
            except Exception:
                pass
        return CameraSettings(values)

    def close(self):
        return None


def _range(interface, prop):
    try:
        return tuple(interface.GetRange(prop))
    except Exception:
        return None
