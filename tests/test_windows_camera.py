"""W1.2 + W1.3 (SPEC_windows_build.md §6.1–§6.3, R7, R8): the camera on Windows, tested on Linux with fakes.

W1.2 — the resolver finds the spectrometer by VID/PID in the MSMF enumeration (a webcam next to it is ignored),
answers presence from the same lookup, and says None — never index 0 — when it is not there.
W1.3 — the backend pins MSMF, asks for YUY2, takes the raw buffer and converts it with OUR function; anything but
YUY2 is refused, never reopened unforced; the CAPTURE-SETTINGS read-back survives without fcntl.
W1.6 — the controls are set natively (here: a fake camera with the ELP's own control table, §6.6c); a measurement
open whose read-back does not prove WB frozen is refused; the settings line reports the camera's own values.
"""
import sys
from types import ModuleType, SimpleNamespace

import cv2
import numpy as np
import pytest
import usb.core

import sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver as resolverModule
import sciens.spectracs.logic.application.video.capture.WindowsUvcControls as controlsModule
from sciens.spectracs.logic.application.video.capture.CaptureBackend import DesktopCv2CaptureBackend, yuy2ToBgr
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.connection.ConnectionPollThread import ConnectionPollThread
from sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil import ApplicationSpectrometerUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor

ELP = SimpleNamespace(index=1, name="HD USB Camera", vid=0x32E4, pid=0x8830)
WEBCAM = SimpleNamespace(index=0, name="Integrated Webcam", vid=0x046D, pid=0x0825)


def _sensor(vendorId="32e4", modelId="8830", isVirtual=False):
    sensor = SpectrometerSensor()
    sensor.vendorId = vendorId
    sensor.modelId = modelId
    sensor.isVirtual = isVirtual
    return sensor


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(resolverModule, "_reportedFailures", set())


# ------------------------------------------------------------------------------------------------ W1.2 resolver

def test_elp_found_and_webcam_ignored(windows):
    resolver = SensorCaptureIndexResolver(enumerator=lambda: [WEBCAM, ELP])
    assert resolver.resolveCaptureIndex(_sensor()) == 1
    assert resolver.isPresent(_sensor()) is True


def test_absent_spectrometer_is_none_never_index_0(windows):
    resolver = SensorCaptureIndexResolver(enumerator=lambda: [WEBCAM])
    assert resolver.resolveCaptureIndex(_sensor()) is None
    assert resolver.isPresent(_sensor()) is False


def test_enumeration_failure_reads_absent_and_is_printed_once(windows, capsys):
    def broken():
        raise OSError("MFStartup failed")

    resolver = SensorCaptureIndexResolver(enumerator=broken)
    assert resolver.resolveCaptureIndex(_sensor()) is None
    assert resolver.isPresent(_sensor()) is False
    assert capsys.readouterr().out.count("camera enumeration failed") == 1


def test_virtual_sensor_does_not_enumerate(windows):
    def mustNotRun():
        raise AssertionError("enumerated for a virtual sensor")

    assert SensorCaptureIndexResolver(enumerator=mustNotRun).resolveCaptureIndex(_sensor(isVirtual=True)) is None


def test_malformed_vendor_id_stays_loud(windows):
    with pytest.raises(ValueError):
        SensorCaptureIndexResolver(enumerator=lambda: [ELP]).resolveCaptureIndex(_sensor(vendorId="zz"))


def test_linux_keeps_sysfs_and_other_platforms_say_none(monkeypatch):
    def mustNotRun():
        raise AssertionError("enumerated off Windows")

    resolver = SensorCaptureIndexResolver(enumerator=mustNotRun)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(resolverModule.glob, "glob", lambda pattern: [])
    assert resolver.resolveCaptureIndex(_sensor()) is None
    monkeypatch.setattr(sys, "platform", "darwin")
    assert resolver.resolveCaptureIndex(_sensor()) is None


def test_presence_on_windows_asks_the_enumeration_not_usb(windows, monkeypatch):
    def noUsb(**kwargs):
        raise AssertionError("pyusb asked on Windows")

    monkeypatch.setattr(usb.core, "find", noUsb)
    monkeypatch.setattr(SensorCaptureIndexResolver, "_SensorCaptureIndexResolver__enumerateMsmf",
                        staticmethod(lambda: [WEBCAM, ELP]))
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor()) is True
    monkeypatch.setattr(SensorCaptureIndexResolver, "_SensorCaptureIndexResolver__enumerateMsmf",
                        staticmethod(lambda: [WEBCAM]))
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor()) is False


def test_poll_thread_on_windows_follows_the_enumeration(windows, monkeypatch):
    def noUsb(**kwargs):
        raise AssertionError("pyusb asked on Windows")

    monkeypatch.setattr(usb.core, "find", noUsb)
    thread = ConnectionPollThread("32e4", "8830", intervalSeconds=0.1)
    answers = iter([[WEBCAM, ELP], [WEBCAM, ELP], [WEBCAM]])

    def enumerate_():
        answer = next(answers)
        if answer == [WEBCAM]:
            thread.stop()
        return answer

    monkeypatch.setattr(SensorCaptureIndexResolver, "_SensorCaptureIndexResolver__enumerateMsmf",
                        staticmethod(enumerate_))
    emitted = []
    thread.presenceChanged.connect(emitted.append)
    thread.run()  # synchronously, on this thread: ends once stop() was called
    assert emitted == [True, False]      # edge-triggered: the repeated "present" is not re-emitted


# ------------------------------------------------------------------------------------------ W1.3 own conversion

def _syntheticYuy2(width, height, seed=7):
    return np.random.default_rng(seed).integers(0, 256, size=(height, width, 2), dtype=np.uint8)


@pytest.mark.parametrize("shape", ["1xN", "HxWx2", "flat"])
def test_own_conversion_equals_cv2_whatever_the_buffer_shape(shape):
    width, height = 64, 48
    yuy2 = _syntheticYuy2(width, height)
    expected = cv2.cvtColor(yuy2, cv2.COLOR_YUV2BGR_YUY2)
    raw = {"1xN": yuy2.reshape(1, -1), "HxWx2": yuy2, "flat": yuy2.reshape(-1)}[shape]
    assert np.array_equal(yuy2ToBgr(raw, width, height), expected)


def test_own_conversion_neutral_grey_and_wrong_sizes():
    # U=V=128 -> neutral; OpenCV converts BT.601 LIMITED range, so Y=128 -> 1.164·(128−16) = 130, not 128
    # (the conversion Linux's V4L2 backend applies too — the point of owning it is that both OSes share it).
    grey = np.full((2, 4, 2), 128, dtype=np.uint8)
    assert np.array_equal(yuy2ToBgr(grey, 4, 2), np.full((2, 4, 3), 130, dtype=np.uint8))
    bgr = np.zeros((2, 4, 3), dtype=np.uint8)                # a backend that converted after all
    assert yuy2ToBgr(bgr, 4, 2) is None
    assert yuy2ToBgr(None, 4, 2) is None
    assert yuy2ToBgr(grey, None, 2) is None


# ------------------------------------------------------------------------------------- W1.3 backend on "win32"

class _FakeCapture:
    def __init__(self, index, api, grantedFourcc, frame):
        self.index, self.api = index, api
        self.grantedFourcc = grantedFourcc
        self.frame = frame
        self.calls = []
        self.values = {}
        self.released = False
        self.streaming = False

    def set(self, prop, value):
        self.calls.append((prop, value))
        self.values[prop] = value
        return True

    def get(self, prop):
        if prop == cv2.CAP_PROP_FOURCC:
            # Like MSMF in the VM: blank until the stream is up, the granted format afterwards.
            return cv2.VideoWriter_fourcc(*self.grantedFourcc) if self.streaming else 0
        return self.values.get(prop, -1.0)

    def grab(self):
        self.streaming = True
        return True

    def read(self):
        return True, self.frame

    def release(self):
        self.released = True


class _FakeCv2:
    """The real cv2 (constants, cvtColor), with VideoCapture replaced by a recorder."""

    def __init__(self, grantedFourcc, frame):
        self.opened = []
        self.__granted, self.__frame = grantedFourcc, frame

    def VideoCapture(self, index, api):
        capture = _FakeCapture(index, api, self.__granted, self.__frame)
        self.opened.append(capture)
        return capture

    def __getattr__(self, name):
        return getattr(cv2, name)


# The ELP's own control table under usbvideo.sys (SPEC_windows_build.md §6.6c): (min, max, step, default, caps).
ELP_RANGES = {"Brightness": (-64, 64, 1, 0, 2), "Contrast": (0, 64, 1, 32, 2), "Hue": (-40, 40, 1, 0, 2),
              "Saturation": (0, 128, 1, 75, 2), "Sharpness": (0, 6, 1, 3, 2), "Gamma": (72, 500, 1, 100, 2),
              "WhiteBalance": (2800, 6500, 1, 4600, 3), "BacklightCompensation": (0, 2, 1, 1, 2),
              "Gain": (0, 100, 1, 0, 2)}
MSMF_PATH = r"\\?\usb#vid_32e4&pid_8830&mi_00#7&abc&0&0000#{e5323777-f976-4f5b-9b55-b94699c46e44}\global"


class _FakeControls:
    """A camera that applies `planControls` to its state — or, with `stuckAutoWb`, ignores the WB request."""
    instances = []

    def __init__(self, devicePath, stuckAutoWb=False, broken=False):
        self.devicePath, self.stuckAutoWb, self.broken = devicePath, stuckAutoWb, broken
        self.state = {name: {"value": r[3], "flags": 1 if name == "WhiteBalance" else 2} for name, r in ELP_RANGES.items()}
        self.state["Exposure"] = {"value": -8, "flags": 1, "min": -13, "max": -1}
        self.applied = []
        _FakeControls.instances.append(self)

    def apply(self, whiteBalanceKelvin):
        if self.broken:
            raise LookupError("camera not among the DirectShow video input devices")
        self.applied.append(whiteBalanceKelvin)
        for name, value, flags in controlsModule.planControls(ELP_RANGES, whiteBalanceKelvin):
            if not (self.stuckAutoWb and name == "WhiteBalance"):
                self.state[name] = {"value": value, "flags": flags}
        self.state["Exposure"]["flags"] = 2
        return dict(self.state, failures=[])

    def read(self):
        return dict(self.state)


def _openOnWindows(monkeypatch, grantedFourcc, whiteBalanceKelvin=6500, **controls):
    yuy2 = _syntheticYuy2(2592, 1944)
    fake = _FakeCv2(grantedFourcc, yuy2.reshape(1, -1))      # MSMF's 1×N raw buffer (§6.6b)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "cv2", fake)
    enumerator = ModuleType("cv2_enumerate_cameras")
    enumerator.enumerate_cameras = lambda api: [SimpleNamespace(index=1, path=MSMF_PATH, vid=0x32E4, pid=0x8830)]
    monkeypatch.setitem(sys.modules, "cv2_enumerate_cameras", enumerator)
    _FakeControls.instances = []
    monkeypatch.setattr(controlsModule, "WindowsUvcControls", lambda path: _FakeControls(path, **controls))
    backend = DesktopCv2CaptureBackend()
    backend.open(1, exposure=None, whiteBalanceKelvin=whiteBalanceKelvin)
    return backend, fake, yuy2


def test_windows_pins_msmf_yuy2_and_converts_itself(monkeypatch, capsys):
    backend, fake, yuy2 = _openOnWindows(monkeypatch, "YUY2")
    assert len(fake.opened) == 1
    capture = fake.opened[0]
    assert (capture.index, capture.api) == (1, cv2.CAP_MSMF)
    props = [prop for prop, _ in capture.calls]
    assert capture.calls[props.index(cv2.CAP_PROP_FOURCC)] == (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUY2"))
    assert props.index(cv2.CAP_PROP_FOURCC) < props.index(cv2.CAP_PROP_FRAME_WIDTH)   # format before size
    assert (cv2.CAP_PROP_CONVERT_RGB, 0) in capture.calls
    assert props.index(cv2.CAP_PROP_CONVERT_RGB) < props.index(cv2.CAP_PROP_EXPOSURE)  # fixed at open

    image = backend.read()
    assert (image.width(), image.height()) == (2592, 1944)
    expectedRgb = cv2.cvtColor(cv2.cvtColor(yuy2, cv2.COLOR_YUV2BGR_YUY2), cv2.COLOR_BGR2RGB)
    pixel = image.pixelColor(100, 50)
    assert (pixel.red(), pixel.green(), pixel.blue()) == tuple(int(v) for v in expectedRgb[50, 100])
    assert "capture resolution = 2592x1944 (MSMF, YUY2, own conversion)" in capsys.readouterr().out


def test_windows_refuses_mjpg_and_never_reopens(monkeypatch, capsys):
    backend, fake, _ = _openOnWindows(monkeypatch, "MJPG")
    assert len(fake.opened) == 1                  # no __reopenUnforced on Windows
    assert fake.opened[0].released
    assert backend.read() is None
    assert backend.readCameraSettings() == {}
    assert "REFUSED to capture on MSMF - the driver granted MJPG, not YUY2" in capsys.readouterr().out


def test_capture_settings_survive_without_fcntl(monkeypatch):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2")
    monkeypatch.setitem(sys.modules, "fcntl", None)   # Windows has none (R7)
    settings = backend.readCameraSettings()
    assert settings["backend"] == "MSMF"
    assert settings["pixelFormat"] == "YUY2"
    # no V4L2 ioctl answered (no fcntl) — the range and mode come from the camera's own controls instead (W1.6)
    assert (settings["exposureMin"], settings["exposureMax"]) == (-13, -1)
    assert settings["autoExposureMode"] == "manual"
    assert "gain" in settings


# ------------------------------------------------------------------------------------ W1.6 native controls

def test_measurement_open_sets_controls_natively_and_reports_them(monkeypatch, capsys):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2")
    controls = _FakeControls.instances[-1]
    assert controls.devicePath == MSMF_PATH and controls.applied == [6500]
    out = capsys.readouterr().out
    assert "white balance fixed" not in out          # OpenCV's WB path (which reads -1 on MSMF) is not taken
    assert "native controls (measurement, WB 6500K)" in out and "WhiteBalance=6500 " in out
    assert backend.read() is not None
    settings = backend.readCameraSettings()
    assert (settings["wbTemperature"], settings["autoWb"], settings["gain"], settings["backlight"]) == (6500, 0, 0, 0)
    assert (settings["exposure"], settings["autoExposureMode"]) == (-8, "manual")
    assert (settings["exposureMin"], settings["exposureMax"]) == (-13, -1)


def test_measurement_refused_when_white_balance_does_not_freeze(monkeypatch, capsys):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", stuckAutoWb=True)
    assert backend.read() is None
    assert "REFUSED to capture on MSMF - the read-back does not prove WB 6500K manual" in capsys.readouterr().out


def test_unbindable_controls_refuse_a_measurement_but_not_a_calibration(monkeypatch, capsys):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", broken=True)
    assert backend.read() is None
    assert "REFUSED to capture on MSMF - native controls unavailable (LookupError" in capsys.readouterr().out

    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", whiteBalanceKelvin=None, broken=True)
    assert backend.read() is not None                # calibration keeps auto WB anyway — warn, go on
    assert "⚠ native controls unavailable" in capsys.readouterr().out


def test_calibration_open_puts_white_balance_on_auto(monkeypatch):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", whiteBalanceKelvin=None)
    settings = backend.readCameraSettings()
    assert (settings["wbTemperature"], settings["autoWb"], settings["backlight"], settings["gain"]) == (4600, 1, 1, 0)


def test_plan_measurement_and_calibration():
    measurement = {name: (value, flags) for name, value, flags in controlsModule.planControls(ELP_RANGES, 6500)}
    assert measurement["WhiteBalance"] == (6500, 2)
    assert measurement["BacklightCompensation"] == (0, 2) and measurement["Gain"] == (0, 2)
    assert {name: measurement[name] for name in ("Brightness", "Contrast", "Hue", "Saturation", "Sharpness", "Gamma")} \
        == {"Brightness": (0, 2), "Contrast": (32, 2), "Hue": (0, 2), "Saturation": (75, 2), "Sharpness": (3, 2),
            "Gamma": (100, 2)}
    calibration = {name: (value, flags) for name, value, flags in controlsModule.planControls(ELP_RANGES, None)}
    assert calibration["WhiteBalance"] == (4600, 1)                # auto
    assert calibration["BacklightCompensation"] == (1, 2) and calibration["Gain"] == (0, 2)


def test_plan_clamps_the_temperature_and_skips_what_the_camera_lacks():
    plan = controlsModule.planControls({"WhiteBalance": (2800, 6500, 1, 4600, 3)}, 7200)
    assert plan == [("WhiteBalance", 6500, 2)]
    assert controlsModule.planControls({}, 6500) == []


@pytest.mark.parametrize("change, frozen", [
    ({}, True),
    ({"WhiteBalance": {"value": 6500, "flags": 1}}, False),     # still auto
    ({"WhiteBalance": {"value": 4600, "flags": 2}}, False),     # manual, wrong temperature
    ({"Gain": {"value": 5, "flags": 2}}, False),
    ({"BacklightCompensation": {"value": 1, "flags": 2}}, False),
    ({"Exposure": {"value": -8, "flags": 1}}, False),           # auto exposure
    ({"WhiteBalance": None}, False),                             # the camera did not say
])
def test_proves_frozen(change, frozen):
    readBack = {"WhiteBalance": {"value": 6500, "flags": 2}, "Gain": {"value": 0, "flags": 2},
                "BacklightCompensation": {"value": 0, "flags": 2}, "Exposure": {"value": -8, "flags": 2}}
    readBack.update(change)
    assert controlsModule.provesFrozen(readBack, 6500) is frozen


def test_device_key_matches_msmf_and_directshow_paths():
    dshow = MSMF_PATH.replace("{e5323777-f976-4f5b-9b55-b94699c46e44}", "{65e8773d-8f56-11d0-a3b9-00a0c9223196}")
    assert controlsModule.deviceKey(MSMF_PATH) == controlsModule.deviceKey(dshow.upper())
    other = MSMF_PATH.replace("7&abc&0&0000", "7&def&0&0000")
    assert controlsModule.deviceKey(MSMF_PATH) != controlsModule.deviceKey(other)
