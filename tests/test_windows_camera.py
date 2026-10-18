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

controlsModule.WindowsUvcControls_ = controlsModule.WindowsUvcControls   # the real class, for the fakes below
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from sciens.spectracs.logic.application.video.capture.CaptureBackend import CaptureBackend, DesktopCv2CaptureBackend, \
    yuy2ToBgr
from sciens.spectracs.plugin_sdk import CameraControl as C
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


# The ELP under usbvideo.sys as CS0 read it in the VM (SPEC_camera_settings.md §3.1): (min, max, step, default, caps)
# per DirectShow id. VideoProcAmp 6, 10–12 are absent; CameraControl 19 is offered but FIXED at 0.
PROC_AMP_RANGES = {0: (-64, 64, 1, 0, 2), 1: (0, 64, 1, 32, 2), 2: (-40, 40, 1, 0, 2), 3: (0, 128, 1, 75, 2),
                   4: (0, 6, 1, 3, 2), 5: (72, 500, 1, 100, 2), 7: (2800, 6500, 1, 4600, 3), 8: (0, 2, 1, 1, 2),
                   9: (0, 100, 1, 0, 2), 13: (0, 2, 1, 1, 0)}
CAMERA_RANGES = {4: (-13, -1, 1, -7, 3), 19: (0, 0, 0, 0, 0)}
MSMF_PATH = r"\\?\usb#vid_32e4&pid_8830&mi_00#7&abc&0&0000#{e5323777-f976-4f5b-9b55-b94699c46e44}\global"


class _FakeInterface:
    """IAMVideoProcAmp / IAMCameraControl: GetRange, Get, Set — the camera keeps what it is told, unless `stuck`."""

    def __init__(self, ranges, state, stuck=()):
        self.ranges, self.state, self.stuck, self.writes = ranges, state, set(stuck), []

    def GetRange(self, prop):
        if prop not in self.ranges:
            raise OSError("E_PROP_ID_UNSUPPORTED")
        return self.ranges[prop]

    def Get(self, prop):
        if prop not in self.ranges:
            raise OSError("E_PROP_ID_UNSUPPORTED")
        return self.state[prop]

    def Set(self, prop, value, flags):
        if prop not in self.ranges:
            raise OSError("E_PROP_ID_UNSUPPORTED")
        self.writes.append((prop, value, flags))
        if prop not in self.stuck:
            self.state[prop] = (value, flags)


class _FakeDirectShow:
    """The ELP as a session left it: WB 6500 manual, backlight 0, exposure −8 auto."""
    instances = []

    def __init__(self, stuck=(), broken=False):
        if broken:
            raise LookupError("camera not among the DirectShow video input devices")
        procState = {prop: (entry[3], 2) for prop, entry in PROC_AMP_RANGES.items()}
        procState.update({7: (6500, 2), 8: (0, 2), 13: (1, 0)})
        self.procAmp = _FakeInterface(PROC_AMP_RANGES, procState, stuck)
        self.camera = _FakeInterface(CAMERA_RANGES, {4: (-8, 1), 19: (0, 0)})
        _FakeDirectShow.instances.append(self)

    def bind(self):
        return self.procAmp, self.camera


def _openOnWindows(monkeypatch, grantedFourcc, profile=CameraProfile.MEASUREMENT, override=None, **camera):
    yuy2 = _syntheticYuy2(2592, 1944)
    fake = _FakeCv2(grantedFourcc, yuy2.reshape(1, -1))      # MSMF's 1×N raw buffer (§6.6b)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "cv2", fake)
    enumerator = ModuleType("cv2_enumerate_cameras")
    enumerator.enumerate_cameras = lambda api: [SimpleNamespace(index=1, path=MSMF_PATH, vid=0x32E4, pid=0x8830,
                                                                name="HD USB Camera")]
    monkeypatch.setitem(sys.modules, "cv2_enumerate_cameras", enumerator)
    _FakeDirectShow.instances = []
    monkeypatch.setattr(controlsModule, "WindowsUvcControls",
                        lambda path: controlsModule.WindowsUvcControls_(path, camera=_FakeDirectShow(**camera)))
    backend = DesktopCv2CaptureBackend()
    backend.open(1, profile, override=override)
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
    assert cv2.CAP_PROP_EXPOSURE not in props and cv2.CAP_PROP_GAIN not in props     # CS3: one writer, DirectShow

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
    # ⭐ CS3: the range in V4L2 units (10000·2^−13 ≈ 1 .. 10000·2^−1 = 5000), so the slider and the AE learn it
    assert (settings["exposureMin"], settings["exposureMax"]) == (1, 5000)
    assert settings["autoExposure"] == "MANUAL"
    assert "gain" in settings


# ------------------------------------------------------------------------- CS3 native controls (SPEC_camera_settings §5)

def test_the_converter_is_whole_log2_seconds():
    assert controlsModule.toLog2(90) == -7 and controlsModule.toV4l2(-7) == 78     # Edwin's pin runs as 78
    assert controlsModule.toLog2(150) == -6 and controlsModule.toV4l2(-6) == 156
    assert controlsModule.toLog2(9000) == -1 and controlsModule.toLog2(0.5) == -13   # clamped to the camera
    assert controlsModule.toV4l2(-13) == 1


def test_describe_reads_the_firmware_in_model_units():
    device = controlsModule.WindowsUvcControls_(MSMF_PATH, camera=_FakeDirectShow()).describe()
    defaults = device.defaults()
    assert defaults.get(C.EXPOSURE) == 78 and defaults.get(C.AUTO_EXPOSURE) == "AUTO"
    assert defaults.get(C.WHITE_BALANCE_KELVIN) == 4600 and defaults.get(C.WHITE_BALANCE_AUTO) is True
    assert defaults.get(C.BACKLIGHT) == 1 and defaults.get(C.POWER_LINE_FREQUENCY) == "50"
    assert device.rangeOf(C.DYNAMIC_FRAMERATE).choices == [False]          # CS0: fixed at 0
    assert device.rangeOf(C.EXPOSURE).quantise(90) == 78


def test_measurement_open_sets_every_control_natively(monkeypatch, capsys):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", override={"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500})
    record = backend.getOpenRecord()
    assert record.refusal is None, record.refusal
    camera = _FakeDirectShow.instances[-1]
    assert camera.camera.state[4] == (-7, 2)                         # 90 → −7, manual
    assert camera.procAmp.state[7] == (6500, 2) and camera.procAmp.state[8] == (0, 2)
    assert 19 not in [prop for prop, _, _ in camera.camera.writes]   # fixed: never written
    assert record.requested["EXPOSURE"] == 78 and record.adjusted["EXPOSURE"] == "requested 90 → 78 (snapped)"
    assert record.camera == {"name": "HD USB Camera", "vendorId": "32e4", "modelId": "8830"}
    assert "camera controls (MEASUREMENT)" in capsys.readouterr().out
    assert backend.read() is not None
    settings = backend.readCameraSettings()
    assert (settings["exposure"], settings["exposureNative"]) == (78, -7)
    assert (settings["wbTemperature"], settings["autoWb"], settings["gain"], settings["backlight"]) == (6500, 0, 0, 0)


def test_set_exposure_returns_the_whole_step(monkeypatch):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2")
    assert backend.setExposure(90) == 78
    assert backend.setExposure(104) == 78        # same step: probes that collapse onto one k are harmless
    assert backend.setExposure(120) == 156


def test_measurement_refused_when_white_balance_does_not_take(monkeypatch, capsys):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", override={"WHITE_BALANCE_KELVIN": 5000}, stuck=[7])
    assert backend.read() is None
    out = capsys.readouterr().out
    assert "REFUSED to capture on MSMF" in out and "WHITE_BALANCE_KELVIN requested 5000, applied 6500" in out


def test_unbindable_controls_refuse_a_measurement_but_not_a_calibration(monkeypatch, capsys):
    backend, fake, _ = _openOnWindows(monkeypatch, "YUY2", broken=True)
    assert backend.read() is None
    assert "native controls unavailable (LookupError" in capsys.readouterr().out

    backend, fake, _ = _openOnWindows(monkeypatch, "YUY2", profile=CameraProfile.CALIBRATION, broken=True)
    assert backend.read() is not None                # calibration warns and goes on, exposure via cv2 as before
    assert (cv2.CAP_PROP_EXPOSURE, -6) in fake.opened[-1].calls     # 150 → −6, in MSMF's own units
    assert "open continues" in capsys.readouterr().out


def test_calibration_open_puts_white_balance_and_backlight_on_their_defaults(monkeypatch):
    backend, _, _ = _openOnWindows(monkeypatch, "YUY2", profile=CameraProfile.CALIBRATION)
    settings = backend.readCameraSettings()
    assert (settings["autoWb"], settings["backlight"], settings["gain"]) == (1, 1, 0)


def test_read_device_defaults_on_windows(monkeypatch):
    _openOnWindows(monkeypatch, "YUY2")
    device = CaptureBackend.readDeviceDefaults(1)
    assert device.defaults().get(C.EXPOSURE) == 78
    assert CaptureBackend.readDeviceDefaults(7).defaults().toJson() == {}       # not enumerated


def test_device_key_matches_msmf_and_directshow_paths():
    dshow = MSMF_PATH.replace("{e5323777-f976-4f5b-9b55-b94699c46e44}", "{65e8773d-8f56-11d0-a3b9-00a0c9223196}")
    assert controlsModule.deviceKey(MSMF_PATH) == controlsModule.deviceKey(dshow.upper())
    other = MSMF_PATH.replace("7&abc&0&0000", "7&def&0&0000")
    assert controlsModule.deviceKey(MSMF_PATH) != controlsModule.deviceKey(other)
