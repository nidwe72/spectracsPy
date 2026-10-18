"""CS2 (SPEC_camera_settings.md §5): Linux sets EVERY control on every open, reads each back, and a MEASUREMENT whose
read-back does not prove the request is refused (Q4) — tested with a fake V4L2 node and a fake cv2.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_linux_uvc_controls.py -q
"""
import sys

import cv2
import numpy as np

from fakes.FakeV4l2Node import FakeV4l2Node
from sciens.spectracs.logic.application.video.capture.CaptureBackend import CaptureBackend, DesktopCv2CaptureBackend
from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import LinuxUvcControls
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from sciens.spectracs.plugin_sdk import CameraControl as C

YUYV = np.random.default_rng(5).integers(0, 256, size=(48, 64, 2), dtype=np.uint8)


class _Capture:
    def __init__(self):
        self.calls = []

    def set(self, prop, value):
        self.calls.append((prop, value))
        return True

    def get(self, prop):
        if prop == cv2.CAP_PROP_FOURCC:
            return cv2.VideoWriter_fourcc(*"YUYV")
        return {cv2.CAP_PROP_FRAME_WIDTH: 64, cv2.CAP_PROP_FRAME_HEIGHT: 48}.get(prop, -1.0)

    def grab(self):
        return True

    def read(self):
        return True, YUYV

    def release(self):
        pass


class _Cv2:
    def __init__(self):
        self.capture = _Capture()

    def VideoCapture(self, index, api):
        return self.capture

    def __getattr__(self, name):
        return getattr(cv2, name)


def _open(monkeypatch, profile, node=None, override=None, exposureSeed=None, noNode=False):
    node = node or FakeV4l2Node()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "cv2", _Cv2())
    monkeypatch.setattr(DesktopCv2CaptureBackend, "controlsFactory",
                        staticmethod(lambda deviceId: None if noNode else LinuxUvcControls(node)))
    backend = DesktopCv2CaptureBackend()
    record = backend.open(0, profile, override=override, exposureSeed=exposureSeed)
    return backend, node, record


def test_describe_reads_the_firmware_not_the_camera_state():
    device = LinuxUvcControls(FakeV4l2Node()).describe()
    defaults = device.defaults()
    assert defaults.get(C.EXPOSURE) == 78                       # GET_DEF, though 90 is what the camera holds
    assert defaults.get(C.AUTO_EXPOSURE) == "AUTO"              # menu 3 = aperture priority = auto
    assert defaults.get(C.WHITE_BALANCE_AUTO) is True
    assert defaults.get(C.BACKLIGHT) == 1
    assert defaults.get(C.POWER_LINE_FREQUENCY) == "50"
    assert device.rangeOf(C.AUTO_EXPOSURE).choices == ["MANUAL", "AUTO"]
    assert device.rangeOf(C.POWER_LINE_FREQUENCY).choices == ["DISABLED", "50", "60"]


def test_measurement_writes_every_control_in_order_and_records_it(monkeypatch, capsys):
    backend, node, record = _open(monkeypatch, CameraProfile.MEASUREMENT, override={"EXPOSURE": 90},
                                  exposureSeed=150)
    assert record.refusal is None
    written = [controlId for controlId, _ in node.writes]
    assert len(set(written)) == len(C)                          # every control the ELP offers, also the defaults
    from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import CONTROL_IDS
    assert written.index(CONTROL_IDS[C.AUTO_EXPOSURE]) < written.index(CONTROL_IDS[C.EXPOSURE])
    assert written.index(CONTROL_IDS[C.WHITE_BALANCE_AUTO]) < written.index(CONTROL_IDS[C.WHITE_BALANCE_KELVIN])
    assert node.written(C.AUTO_EXPOSURE) == [1] and node.written(C.EXPOSURE) == [90]
    assert node.written(C.GAMMA) == [100]                       # at default, still WRITTEN (UVC values persist)
    assert record.applied["BACKLIGHT"] == 0 and record.sources["EXPOSURE"] == "plugin"
    assert record.deviceDefaults["BACKLIGHT"] == 1 and record.mismatches == []
    assert record.host["conversion"] == "own" and record.profile == "MEASUREMENT"
    assert backend.read() is not None
    assert "camera controls (MEASUREMENT)" in capsys.readouterr().out


def test_calibration_puts_auto_wb_and_backlight_back(monkeypatch):
    _backend, node, record = _open(monkeypatch, CameraProfile.CALIBRATION)
    assert node.written(C.WHITE_BALANCE_AUTO) == [1]
    assert node.written(C.WHITE_BALANCE_KELVIN) == []           # inactive under auto WB: never written
    assert node.written(C.BACKLIGHT) == [1]                     # D12: the device default, set explicitly
    assert node.written(C.EXPOSURE) == [150]                    # the legacy open value
    assert "WHITE_BALANCE_KELVIN" in record.inactive


def test_a_measurement_the_camera_does_not_confirm_is_refused(monkeypatch, capsys):
    backend, _node, record = _open(monkeypatch, CameraProfile.MEASUREMENT, node=FakeV4l2Node(ignore=[C.GAMMA]),
                                   override={"GAMMA": 120})
    assert record.refusal is not None and "GAMMA" in record.refusal
    assert record.mismatches == [{"control": "GAMMA", "requested": 120, "applied": 100}]
    assert backend.read() is None                               # no frame from a refused open
    assert "REFUSED" in capsys.readouterr().out


def test_calibration_and_idle_only_warn(monkeypatch, capsys):
    for profile in (CameraProfile.CALIBRATION, CameraProfile.IDLE):
        backend, _node, record = _open(monkeypatch, profile, node=FakeV4l2Node(ignore=[C.EXPOSURE]))
        assert record.refusal is None and record.mismatches[0]["control"] == "EXPOSURE"
        backend.release()
    out = capsys.readouterr().out
    assert "REFUSED" not in out and "open continues" in out


def test_a_camera_without_a_node_is_refused_for_a_measurement(monkeypatch):
    _backend, _node, record = _open(monkeypatch, CameraProfile.MEASUREMENT, noNode=True)
    assert record.refusal is not None and "no V4L2 node" in record.refusal
    _backend, _node, record = _open(monkeypatch, CameraProfile.CALIBRATION, noNode=True)
    assert record.refusal is None


def test_set_exposure_reasserts_manual_and_returns_the_read_back(monkeypatch):
    backend, node, _record = _open(monkeypatch, CameraProfile.MEASUREMENT)
    node.writes.clear()
    assert backend.setExposure(104) == 104
    assert [value for _, value in node.writes] == [1, 104]      # manual first, then the value


def test_camera_settings_line_reads_model_words(monkeypatch):
    backend, _node, _record = _open(monkeypatch, CameraProfile.MEASUREMENT, override={"EXPOSURE": 90})
    settings = backend.readCameraSettings()
    assert settings["autoExposure"] == "MANUAL"                 # no more menu index 1 beside an autoWb 0
    assert (settings["exposure"], settings["exposureMax"], settings["autoWb"]) == (90, 5000, 0)
    assert backend.readCameraState().get(C.WHITE_BALANCE_KELVIN) == 6500


def test_release_closes_the_controls_fd(monkeypatch):
    backend, node, _record = _open(monkeypatch, CameraProfile.IDLE)
    backend.release()
    assert node.closed


def test_read_device_defaults_needs_no_open(monkeypatch):
    node = FakeV4l2Node()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(LinuxUvcControls, "forDevice", classmethod(lambda cls, deviceId: cls(node)))
    device = CaptureBackend.readDeviceDefaults(0)
    assert device.defaults().get(C.EXPOSURE) == 78
    assert node.writes == [] and node.closed                   # read-only, and the fd is let go again


def test_profile_is_required():
    import pytest
    with pytest.raises(ValueError):
        DesktopCv2CaptureBackend().open(0)
