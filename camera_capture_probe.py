"""Standalone camera-capture probe (NOT wired into the app).

Proves two things on the real machine, cheese-style:
  1. Resolve the correct cv2 index for the spectrometer by USB VID/PID (Linux sysfs) —
     this is the 'R0 resolver' idea from docs/SPEC_real_camera_capture.md.
  2. Open that camera, warm up, grab one frame, save it as a PNG.

Run:  python3 camera_capture_probe.py           # uses the ELP 32e4:8830
      python3 camera_capture_probe.py 0c45 6366 # any VID PID
Delete this file whenever — it is a scratch probe, not app code.
"""
import glob
import os
import sys

VENDOR_ID = sys.argv[1] if len(sys.argv) > 1 else "32e4"   # ELP
PRODUCT_ID = sys.argv[2] if len(sys.argv) > 2 else "8830"


def resolve_capture_index(vid: str, pid: str):
    """Return the cv2 index of the /dev/videoN capture node for this USB VID:PID, or None."""
    matches = []
    for node in sorted(glob.glob("/sys/class/video4linux/video*")):
        n = int(os.path.basename(node).replace("video", ""))
        try:
            with open(os.path.join(node, "device/../idVendor")) as f:
                nvid = f.read().strip().lower()
            with open(os.path.join(node, "device/../idProduct")) as f:
                npid = f.read().strip().lower()
        except OSError:
            continue
        if nvid == vid.lower() and npid == pid.lower():
            v4l_index = None
            try:
                with open(os.path.join(node, "index")) as f:
                    v4l_index = int(f.read().strip())
            except OSError:
                pass
            matches.append((n, v4l_index))
    if not matches:
        return None
    # Prefer the capture node (v4l index 0); metadata node is index >= 1.
    matches.sort(key=lambda m: (m[1] if m[1] is not None else 99, m[0]))
    return matches[0][0]


def main():
    import cv2

    idx = resolve_capture_index(VENDOR_ID, PRODUCT_ID)
    print(f"[resolver] VID:PID {VENDOR_ID}:{PRODUCT_ID} -> cv2 index {idx}")
    if idx is None:
        print("[resolver] no matching capturable camera found — is it plugged in?")
        return 1

    import time

    def open_cap():
        for _ in range(3):
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if cap.isOpened():
                return cap
            cap.release()
            time.sleep(0.3)
        return None

    def grab(fourcc, w_req, h_req, warmup=6):
        cap = open_cap()
        if cap is None:
            return None
        if fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        if w_req:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w_req)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h_req)
        got = None
        for _ in range(warmup):     # warm-up: auto-exposure + MJPG stream settle
            try:
                ok, f = cap.read()  # OpenCV 4.13 can *raise* on an empty MJPG buffer
            except cv2.error:
                continue
            if ok and f is not None:
                got = f
        cap.release()
        return got

    frame = grab("MJPG", 1920, 1080)
    mode = "MJPG 1920x1080"
    if frame is None:               # some cv2/UVC combos choke on MJPG — fall back to raw YUYV
        frame = grab(None, 0, 0)
        mode = "default (YUYV)"

    if frame is None:
        print("[capture] opened but no usable frame returned (tried MJPG and default)")
        return 1

    h, w = frame.shape[:2]
    mean = float(frame.mean())
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_capture_probe.png")
    cv2.imwrite(out, frame)
    print(f"[capture] mode={mode}  frame {w}x{h}  mean-brightness {mean:.1f}/255  saved -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
