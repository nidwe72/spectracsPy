from sciens.spectracs.logic.application.video.VideoThread import VideoThread
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile


class CameraWarmupVideoThread(VideoThread):
    """Read-and-discard warm-keeper thread (SPEC_capture_quality.md §16). It streams the real device continuously so
    the sensor die stays at thermal equilibrium (continuous readout is what heats it). It uses the BASE VideoThread
    capture only — `afterCapture` merely advances the frame index, with NO emit and NO backpressure — so, unlike
    DevCaptureVideoThread (which emits a frame then blocks in `__waitForRender` until a subscriber sets the event),
    it never stalls with no subscriber. Exempt from CameraLease (it is the idle-holder, not a consumer)."""

    # ⭐ IDLE = MEASUREMENT minus the plugin (SPEC_camera_settings.md §3.3, D1). It used to open with calibration
    # semantics, which under "every open sets every control" would put auto WB and backlight 1 back between
    # sessions; now the measurement open finds them already in place. The exposure still changes (IDLE runs at
    # calibrationExposure), so the measurement's hold-back still applies (E5).
    CAMERA_PROFILE = CameraProfile.IDLE

    def __init__(self):
        super().__init__()
        self._isWarmKeeper = True
