"""W1.6 — the camera's UVC controls on Windows, set and read back NATIVELY (SPEC_windows_build.md §6.4b, §6.6c).

OpenCV cannot set white balance through MSMF or DSHOW, and MSMF's exposure read-back is broken (§6.6b). The camera
itself exposes every control to DirectShow — `IAMVideoProcAmp` (white balance, gain, backlight, brightness, …) and
`IAMCameraControl` (exposure) — so they are set and read there, while the frames keep coming from MSMF (W1.3).
Decision W1.1 (Edwin, 2026-10-07): route (d), every control set explicitly on every open, because UVC values
PERSIST IN THE CAMERA — a control one session leaves behind is the next session's starting point.

⭐ The interfaces are declared here by hand with plain `comtypes` — no `pygrabber`, no `comtypes.client.GetModule`
(which generates code at runtime, a frozen-build risk, §6.7). Each call binds the camera afresh IN THE CALLING THREAD
and lets go again: the capture thread sets, the GUI thread reads back, and no COM pointer crosses an apartment.

Pure parts (`planControls`, `provesFrozen`, `deviceKey`) carry the decisions and are tested on Linux.
"""
import re

FLAG_AUTO, FLAG_MANUAL = 1, 2

# IAMVideoProcAmp property ids (strmif.h VideoProcAmpProperty) and the one IAMCameraControl id we touch.
VIDEO_PROC_AMP = {"Brightness": 0, "Contrast": 1, "Hue": 2, "Saturation": 3, "Sharpness": 4, "Gamma": 5,
                  "WhiteBalance": 7, "BacklightCompensation": 8, "Gain": 9}
CAMERA_CONTROL_EXPOSURE = 4

# Image controls with no measurement role: always the camera's OWN default, so nothing a probe or another tool left
# behind leaks into a spectrum. (Linux never touches them — it relies on them being at default, §11c.10.)
_AT_DEFAULT = ("Brightness", "Contrast", "Hue", "Saturation", "Sharpness", "Gamma")

_CLSID_SYSTEM_DEVICE_ENUM = "{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}"
_VIDEO_INPUT_DEVICE = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"


def deviceKey(path):
    """The part of a device path both backends share: MSMF's symbolic link and DirectShow's DevicePath differ only
    in the interface GUID after the last `#` (seen on the ELP in the VM)."""
    return (path or "").lower().rsplit("#", 1)[0]


def planControls(ranges, whiteBalanceKelvin):
    """What to set, as [(name, value, flags)], from the camera's own ranges {name: (min, max, step, default, caps)}.

    Mirrors the Linux mode split (CaptureBackend.open, SPEC_capture_quality.md §14.8):
      measurement (`whiteBalanceKelvin` given) — WB MANUAL at that temperature, backlight 0, gain 0;
      calibration (None) — WB AUTO (the peak detection is tuned for it), backlight at its default, gain 0.
    Everything else at the camera's default, manual. A control the camera does not offer is skipped."""
    plan = []
    for name in _AT_DEFAULT:
        if name in ranges:
            plan.append((name, ranges[name][3], FLAG_MANUAL))
    if "WhiteBalance" in ranges:
        if whiteBalanceKelvin is None:
            plan.append(("WhiteBalance", ranges["WhiteBalance"][3], FLAG_AUTO))
        else:
            low, high = ranges["WhiteBalance"][0], ranges["WhiteBalance"][1]
            plan.append(("WhiteBalance", max(low, min(high, int(whiteBalanceKelvin))), FLAG_MANUAL))
    if "BacklightCompensation" in ranges:
        backlight = ranges["BacklightCompensation"][3] if whiteBalanceKelvin is None else 0
        plan.append(("BacklightCompensation", backlight, FLAG_MANUAL))
    if "Gain" in ranges:
        plan.append(("Gain", 0, FLAG_MANUAL))
    return plan


def provesFrozen(readBack, whiteBalanceKelvin):
    """Does the read-back PROVE a measurement-grade state (§6.4b)? WB manual at the requested temperature, gain 0,
    backlight 0, exposure manual. A camera that will not say is not proof."""
    def state(name):
        entry = readBack.get(name)
        return (entry.get("value"), entry.get("flags")) if entry else (None, None)
    return (state("WhiteBalance") == (int(whiteBalanceKelvin), FLAG_MANUAL)
            and state("Gain")[0] == 0
            and state("BacklightCompensation")[0] == 0
            and state("Exposure")[1] == FLAG_MANUAL)


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


class WindowsUvcControls:
    """The DirectShow controls of ONE camera, found by its device path (the MSMF symbolic link CaptureBackend
    opened). Every public call binds in the calling thread and releases before it returns. Raises on a camera that
    cannot be bound — the caller decides what that means (CaptureBackend: a refused measurement)."""

    def __init__(self, devicePath):
        self.__key = deviceKey(devicePath)
        match = re.search(r"vid_([0-9a-f]{4}).{0,3}pid_([0-9a-f]{4})", self.__key)
        self.__vidPid = match.groups() if match else None

    def apply(self, whiteBalanceKelvin):
        """Set every control per `planControls`, exposure mode MANUAL at its current value; return the read-back."""
        procAmp, camera = self.__bind()
        ranges = self.__ranges(procAmp)
        failures = []
        for name, value, flags in planControls(ranges, whiteBalanceKelvin):
            try:
                procAmp.Set(VIDEO_PROC_AMP[name], int(value), flags)
            except Exception as error:
                failures.append("%s: %s" % (name, type(error).__name__))
        try:
            exposure, _ = camera.Get(CAMERA_CONTROL_EXPOSURE)
            camera.Set(CAMERA_CONTROL_EXPOSURE, exposure, FLAG_MANUAL)
        except Exception as error:
            failures.append("Exposure: %s" % type(error).__name__)
        readBack = self.__read(procAmp, camera)
        readBack["failures"] = failures
        return readBack

    def read(self):
        procAmp, camera = self.__bind()
        return self.__read(procAmp, camera)

    def __ranges(self, procAmp):
        ranges = {}
        for name, prop in VIDEO_PROC_AMP.items():
            try:
                ranges[name] = tuple(procAmp.GetRange(prop))
            except Exception:
                pass                                  # the camera does not offer it
        return ranges

    def __read(self, procAmp, camera):
        readBack = {}
        for name, prop in VIDEO_PROC_AMP.items():
            try:
                value, flags = procAmp.Get(prop)
                readBack[name] = {"value": value, "flags": flags}
            except Exception:
                pass
        try:
            value, flags = camera.Get(CAMERA_CONTROL_EXPOSURE)
            low, high, _step, _default, _caps = camera.GetRange(CAMERA_CONTROL_EXPOSURE)
            readBack["Exposure"] = {"value": value, "flags": flags, "min": low, "max": high}
        except Exception:
            pass
        return readBack

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
