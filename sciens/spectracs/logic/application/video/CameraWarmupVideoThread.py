from sciens.spectracs.logic.application.video.VideoThread import VideoThread


class CameraWarmupVideoThread(VideoThread):
    """Read-and-discard warm-keeper thread (SPEC_capture_quality.md §16). It streams the real device continuously so
    the sensor die stays at thermal equilibrium (continuous readout is what heats it). It uses the BASE VideoThread
    capture only — `afterCapture` merely advances the frame index, with NO emit and NO backpressure — so, unlike
    DevCaptureVideoThread (which emits a frame then blocks in `__waitForRender` until a subscriber sets the event),
    it never stalls with no subscriber. Exempt from CameraLease (it is the idle-holder, not a consumer)."""

    def __init__(self):
        super().__init__()
        self._isWarmKeeper = True
