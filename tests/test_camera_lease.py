"""
CameraLease coordination (SPEC_capture_quality.md §16.6) — the warm-keeper is paused on the FIRST consumer acquire
and resumed on the LAST release, with a nested/thread-safe count. Pure logic; no camera.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_camera_lease.py -q
"""
import threading

from sciens.spectracs.logic.application.video.CameraLease import CameraLease


def _freshLease():
    # The lease is a Singleton; reset its internal state for an isolated test.
    lease = CameraLease()
    lease._CameraLease__count = 0
    events = {"busy": 0, "idle": 0}
    lease.registerWarmKeeper(lambda: events.__setitem__("busy", events["busy"] + 1),
                             lambda: events.__setitem__("idle", events["idle"] + 1))
    return lease, events


def test_first_acquire_pauses_last_release_resumes():
    lease, events = _freshLease()
    lease.acquire()                      # first consumer → warm-keeper pauses
    assert events == {"busy": 1, "idle": 0} and lease.activeCount() == 1
    lease.acquire()                      # second consumer → no extra pause
    assert events == {"busy": 1, "idle": 0} and lease.activeCount() == 2
    lease.release()                      # still one holder → no resume
    assert events == {"busy": 1, "idle": 0} and lease.activeCount() == 1
    lease.release()                      # last release → warm-keeper resumes
    assert events == {"busy": 1, "idle": 1} and lease.activeCount() == 0


def test_release_below_zero_is_ignored():
    lease, events = _freshLease()
    lease.release()                      # nothing held → no-op, no onIdle
    assert events == {"busy": 0, "idle": 0} and lease.activeCount() == 0


def test_count_is_thread_safe():
    lease, events = _freshLease()
    N = 50

    def cycle():
        lease.acquire()
        lease.release()

    threads = [threading.Thread(target=cycle) for _ in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # every acquire matched a release → back to idle; onBusy/onIdle each fired at least once, and balanced
    assert lease.activeCount() == 0
    assert events["busy"] == events["idle"] and events["busy"] >= 1
