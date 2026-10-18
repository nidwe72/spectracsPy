"""W1.4b (SPEC_windows_build.md §6.3.4, §11c.11): Linux converts the YUYV itself too, tested with a fake V4L2.

W1.4 proved `yuy2ToBgr` makes the very call V4L2's backend makes on the same bytes, so Linux takes the raw buffer
whenever the driver GRANTED YUYV. A driver that kept MJPG — or the unforced reopen after a dead stream — is
converted by the backend as before (`yuy2ToBgr` cannot decode a JPEG). CAPTURE-SETTINGS says which one it was.
"""
import sys

import cv2
import numpy as np
import pytest

from sciens.spectracs.logic.application.video.capture.CaptureBackend import DesktopCv2CaptureBackend
from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import LinuxUvcControls
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from fakes.FakeV4l2Node import FakeV4l2Node

NO_NODE = 99            # the cv2 index; the camera's controls come from a FakeV4l2Node (CS2)
# What cv2 may still set after CS2 (SPEC_camera_settings.md §5): the stream, never a control.
STREAM_PROPS = {cv2.CAP_PROP_BUFFERSIZE, cv2.CAP_PROP_FOURCC, cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_CONVERT_RGB}


class _FakeV4l2Capture:
    """V4L2 as seen in W1.4: the FOURCC reads back at once; CONVERT_RGB=0 hands over the H×W×2 buffer."""

    def __init__(self, grantedFourcc, streams, yuyv):
        self.grantedFourcc, self.streams, self.yuyv = grantedFourcc, streams, yuyv
        self.values = {}
        self.calls = []

    def set(self, prop, value):
        self.calls.append((prop, value))
        self.values[prop] = value
        return True

    def get(self, prop):
        if prop == cv2.CAP_PROP_FOURCC:
            return cv2.VideoWriter_fourcc(*self.grantedFourcc)
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return self.yuyv.shape[1]
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return self.yuyv.shape[0]
        return self.values.get(prop, -1.0)

    def grab(self):
        return self.streams

    def read(self):
        if self.values.get(cv2.CAP_PROP_CONVERT_RGB) == 0:
            return True, self.yuyv
        return True, cv2.cvtColor(self.yuyv, cv2.COLOR_YUV2BGR_YUYV)      # what cap_v4l.cpp does itself

    def release(self):
        pass


class _FakeCv2:
    def __init__(self, captures):
        self.captures, self.opened = list(captures), []

    def VideoCapture(self, index, api):
        capture = self.captures.pop(0)
        self.opened.append((index, api, capture))
        return capture

    def __getattr__(self, name):
        return getattr(cv2, name)


@pytest.fixture
def yuyv():
    return np.random.default_rng(3).integers(0, 256, size=(48, 64, 2), dtype=np.uint8)


def _open(monkeypatch, *captures):
    fake = _FakeCv2(captures)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "cv2", fake)
    monkeypatch.setattr(DesktopCv2CaptureBackend, "controlsFactory",
                        staticmethod(lambda deviceId: LinuxUvcControls(FakeV4l2Node())))
    backend = DesktopCv2CaptureBackend()
    backend.open(NO_NODE, CameraProfile.MEASUREMENT, override={"EXPOSURE": 90})
    return backend, fake


def _rgbAt(image, x, y):
    pixel = image.pixelColor(x, y)
    return pixel.red(), pixel.green(), pixel.blue()


def test_linux_converts_itself_when_yuyv_is_granted(monkeypatch, yuyv, capsys):
    capture = _FakeV4l2Capture("YUYV", True, yuyv)
    backend, fake = _open(monkeypatch, capture)
    assert fake.opened[0][1] == cv2.CAP_V4L2
    assert (cv2.CAP_PROP_CONVERT_RGB, 0) in capture.calls                                 # fixed at open
    assert {prop for prop, _ in capture.calls} <= STREAM_PROPS                             # one writer: no cv2 control
    image = backend.read()
    expected = cv2.cvtColor(cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2), cv2.COLOR_BGR2RGB)
    assert _rgbAt(image, 10, 20) == tuple(int(v) for v in expected[20, 10])
    assert backend.readCameraSettings()["conversion"] == "own"
    assert "(V4L2, YUYV, own conversion)" in capsys.readouterr().out


def test_own_and_backend_conversion_give_the_same_codes(monkeypatch, yuyv):
    """The W1.4 identity in miniature: the backend's own conversion (CONVERT_RGB=1) and ours, same bytes."""
    ours, _ = _open(monkeypatch, _FakeV4l2Capture("YUYV", True, yuyv))
    mjpgLabel, _ = _open(monkeypatch, _FakeV4l2Capture("MJPG", True, yuyv))   # backend converts (fake: same bytes)
    a, b = ours.read(), mjpgLabel.read()
    assert all(_rgbAt(a, x, y) == _rgbAt(b, x, y) for x in range(0, 64, 7) for y in range(0, 48, 5))


def test_linux_leaves_a_kept_mjpg_to_the_backend(monkeypatch, yuyv, capsys):
    capture = _FakeV4l2Capture("MJPG", True, yuyv)
    backend, _ = _open(monkeypatch, capture)
    assert (cv2.CAP_PROP_CONVERT_RGB, 0) not in capture.calls
    assert backend.read() is not None
    assert backend.readCameraSettings()["conversion"] == "backend"
    assert "own conversion" not in capsys.readouterr().out


def test_unforced_reopen_hands_the_conversion_back_to_the_backend(monkeypatch, yuyv):
    dead = _FakeV4l2Capture("YUYV", False, yuyv)              # YUYV granted, but the stream never comes up
    unforced = _FakeV4l2Capture("MJPG", True, yuyv)
    backend, fake = _open(monkeypatch, dead, unforced)
    assert len(fake.opened) == 2
    assert (cv2.CAP_PROP_CONVERT_RGB, 0) not in unforced.calls
    settings = backend.readCameraSettings()
    assert (settings["pixelFormat"], settings["conversion"]) == ("MJPG", "backend")
    assert backend.read() is not None
