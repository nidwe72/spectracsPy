"""CS2 + CS5 (SPEC_camera_settings.md §5, §3.3a): the video thread opens with its profile, STOPS on a refused open,
holds back the first frames after every change, and gives every exposure change its source.

Drives `VideoThread.run()` synchronously with a fake backend — no camera, no Qt event loop.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_video_thread_camera_state.py -q
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

import sciens.spectracs.logic.application.video.VideoThread as videoThreadModule
from sciens.spectracs.logic.application.video.CameraWarmupVideoThread import CameraWarmupVideoThread
from sciens.spectracs.logic.application.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.application.video.VideoThread import VideoThread
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from sciens.spectracs.model.spectral.camera.CameraOpenRecord import CameraOpenRecord

APP = QApplication.instance() or QApplication([])


class _Backend:
    def __init__(self, refusal=None, quantise=lambda value: value):
        self.refusal, self.quantise = refusal, quantise
        self.opened, self.exposures, self.reads, self.released = None, [], 0, False

    def open(self, deviceId, profile, override=None, exposureSeed=None):
        self.opened = (deviceId, profile, override, exposureSeed)
        return CameraOpenRecord(profile=profile.value, refusal=self.refusal,
                                requested={"EXPOSURE": exposureSeed}, applied={"EXPOSURE": exposureSeed},
                                sources={"EXPOSURE": "plugin" if override else "profile"})

    def read(self):
        self.reads += 1
        image = QImage(4, 4, QImage.Format.Format_RGB888)
        image.fill(self.reads)
        return image

    def setExposure(self, exposure):
        self.exposures.append(exposure)
        return self.quantise(exposure)

    def readCameraSettings(self):
        return {}

    def release(self):
        self.released = True


class _Recorder(VideoThread):
    """Counts what reached afterCapture (a burst would take these) and what was only previewed."""

    def __init__(self, frames=8, onFrame=None):
        super().__init__()
        self.captured, self.previews, self.onFrame = [], [], onFrame
        self.setFrameCount(frames + 1)          # afterCapture stops at frameCount - 1

    def afterCapture(self):
        self.captured.append(self.qImage)
        if self.onFrame is not None:
            self.onFrame(self, len(self.captured))
        super().afterCapture()

    def _emitPreview(self):
        self.previews.append(self.qImage)


def _run(monkeypatch, thread, backend):
    monkeypatch.setattr(videoThreadModule, "getCaptureBackend", lambda: backend)
    refusals = []
    thread.cameraRefused.connect(refusals.append)
    thread.setIsVirtual(False)
    thread.run()
    return refusals


def test_every_thread_has_its_profile():
    assert VideoThread.CAMERA_PROFILE is CameraProfile.CALIBRATION
    assert DevCaptureVideoThread.CAMERA_PROFILE is CameraProfile.MEASUREMENT
    assert CameraWarmupVideoThread.CAMERA_PROFILE is CameraProfile.IDLE
    assert not hasattr(VideoThread, "WHITE_BALANCE_KELVIN")


def test_the_profile_and_override_reach_the_backend(monkeypatch):
    thread, backend = _Recorder(frames=1), _Backend()
    thread.setCameraProfile(CameraProfile.MEASUREMENT)
    thread.setCameraOverride({"EXPOSURE": 90})
    thread.setExposure(150)
    _run(monkeypatch, thread, backend)
    assert backend.opened == (0, CameraProfile.MEASUREMENT, {"EXPOSURE": 90}, 150)


def test_a_refused_open_stops_and_says_why(monkeypatch):
    thread, backend = _Recorder(), _Backend(refusal="GAMMA requested 120, applied 100")
    refusals = _run(monkeypatch, thread, backend)
    assert refusals == ["GAMMA requested 120, applied 100"]
    assert backend.reads == 0 and thread.captured == []          # no spin, no "no frames were delivered"
    assert backend.released


def test_the_first_frames_after_open_are_preview_only(monkeypatch):
    thread, backend = _Recorder(frames=3), _Backend()
    _run(monkeypatch, thread, backend)
    assert len(thread.previews) == VideoThread.HOLD_BACK_FRAMES
    assert len(thread.captured) == 3
    held = {image.pixel(0, 0) for image in thread.previews}
    assert not held & {image.pixel(0, 0) for image in thread.captured}   # not one held-back frame in the burst
    assert thread.getOpenRecord().heldBackFrames == VideoThread.HOLD_BACK_FRAMES


def test_a_live_exposure_change_is_held_back_and_carries_its_source(monkeypatch):
    def lockOnSecondFrame(thread, count):
        if count == 2:
            thread.setLiveExposure(104, "locked-from-reference")

    thread, backend = _Recorder(frames=4, onFrame=lockOnSecondFrame), _Backend(quantise=lambda value: 78)
    thread.setExposure(90)
    _run(monkeypatch, thread, backend)
    assert backend.exposures == [104]                             # applied once — not re-applied every frame
    assert thread.getExposureState() == (104, 78, "locked-from-reference")   # requested, READ-BACK, source
    assert len(thread.previews) == 2 * VideoThread.HOLD_BACK_FRAMES
    assert thread.getHeldBackFrames() == VideoThread.HOLD_BACK_FRAMES


def test_the_open_exposure_keeps_the_resolved_source(monkeypatch):
    thread, backend = _Recorder(frames=1), _Backend()
    thread.setCameraOverride({"EXPOSURE": 90})
    thread.setExposure(90)
    _run(monkeypatch, thread, backend)
    assert thread.getExposureState() == (90, 90, "plugin")
