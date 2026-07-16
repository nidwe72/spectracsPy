#!/usr/bin/env python3
"""M0 capture-quality probe — SPEC_capture_quality.md §4 (dark & warmup diagnostic).

A STANDALONE, READ-ONLY diagnostic run on the real rig (real camera + lamp). It gathers the evidence that
decides the later milestones — whether black-level subtraction must be scalar or per-pixel (M3), whether a
bad-pixel map earns its place (M2), and how long the mains-LED bulb needs to warm up (§8). It writes NOTHING
to the app DB; results land as report.json + PNG plots under spectracs-references/probe/<timestamp>/.

Design (why it looks like this):
  * It grabs frames through the SAME backend the app uses (getCaptureBackend / DesktopCv2CaptureBackend), so
    resolution + manual-exposure flags match production exactly, and reduces each frame to intensity with the
    SAME qGray weighting the real extractor uses (ImageSpectrumAcquisitionLogicModule) — so verdicts transfer.
  * Scene config (device index, ROI, px->nm cubic, exposure) auto-resolves from the app's selected spectrometer
    profile when that context is populated; every field also has a CLI override, which is the reliable path for
    a cold standalone run. ROI x1,y1,x2,y2 + cubic A,B,C,D live on SpectrometerCalibrationProfile.
  * The numeric analysis is split into PURE functions (dark_stats / hot_pixels / warmup_stats / verdicts) that
    operate on numpy arrays, so `--selftest` exercises them offscreen with synthetic frames (no camera).

Phases (each gated on a console prompt so the operator can set the rig):
  A  Dark  — slit blocked / lamp off, N frames at operating exposure -> black level, uniformity, hot pixels,
             exposure-dependence.
  B  Warmup — lamp cold-start on, one frame every few seconds -> intensity/color drift, time-to-stable, dead px.

Run on the rig:
    PYTHONPATH=... python diagnostics/capture_quality_probe.py --device 0 --roi X1,Y1,X2,Y2 --coeffs A,B,C,D
Self-test offscreen (no camera, no rig):
    python diagnostics/capture_quality_probe.py --selftest
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np

# --- constants / thresholds (SPEC §4.4; tunable) ---------------------------------------------------------

FULL_SCALE = 255.0
BLACK_MATTERS_PCT = 1.0     # D0 above 1% full-scale -> Topic 4 matters
UNIFORM_STD_DN = 1.0        # ROI dark spatial std below this -> scalar black-level suffices
HOT_MAD_K = 6.0             # hot pixel if dark-mean > median + K*MAD ...
HOT_ABS_DN = 15.0           # ... or above this absolute DN
DEAD_ABS_DN = 5.0           # ROI pixel this dim while its neighbourhood is bright -> dead
DEAD_NEIGHBOUR_DN = 40.0    # "bright neighbourhood" floor for the dead-pixel test
WARMUP_STABLE_PCT = 0.5     # rolling change below this (over the window) -> stabilised
WARMUP_WINDOW_S = 30.0      # sustained window for the stability test
DEFAULT_DARK_FRAMES = 150
DEFAULT_WARMUP_PERIOD_S = 2.0
DEFAULT_WARMUP_DURATION_S = 300.0
DEFAULT_INSET_ROWS = 2      # drop this many rows off each edge of the ROI band (§6 inset band)
EXPOSURE_MIN = 1            # auto-exposure search bounds — mirror CapturePanel.__EXPOSURE_MIN/MAX
EXPOSURE_MAX = 500
AUTO_EXPOSE_TARGET = 235    # AutoExposureLogicModule.DEFAULT_TARGET (~92% FS, headroom below clip)
EXPOSURE_FALLBACK = 150     # CapturePanel.__EXPOSURE_FALLBACK — used only if auto-exposure is disabled


# --- pure frame reduction --------------------------------------------------------------------------------

def rgb_to_qgray(rgb):
    """Qt qGray weighting: (11*R + 16*G + 5*B) / 32 — matches the real extractor's per-pixel intensity."""
    rgb = rgb.astype(np.uint32)
    gray = (11 * rgb[..., 0] + 16 * rgb[..., 1] + 5 * rgb[..., 2]) // 32
    return gray.astype(np.uint8)


def qimage_to_rgb(qimage):
    """QImage (RGB888) -> HxWx3 uint8 numpy, copied (detached from Qt's buffer)."""
    qimage = qimage.convertToFormat(qimage.Format.Format_RGB888)
    w, h = qimage.width(), qimage.height()
    ptr = qimage.constBits()
    arr = np.frombuffer(ptr, np.uint8).reshape(h, qimage.bytesPerLine())[:, : w * 3]
    return arr.reshape(h, w, 3).copy()


def band_rows(roi, inset):
    """ROI (x1,y1,x2,y2) -> inclusive (yTop, yBottom, x1, x2) inset band; drops `inset` rows off each edge."""
    x1, y1, x2, y2 = roi
    y1, y2 = sorted((int(y1), int(y2)))
    x1, x2 = sorted((int(x1), int(x2)))
    top = y1 + inset
    bottom = y2 - inset
    if bottom <= top:                 # band too thin for the inset -> fall back to the full band
        top, bottom = y1, y2
    return top, bottom, x1, x2


# --- pure analysis (SANDBOX-testable) --------------------------------------------------------------------

def dark_stats(mean_img, std_img, roi, inset):
    """Per-pixel temporal mean/std images (HxW float) -> dark metrics over the inset ROI band.

    Returns black level D0, spatial uniformity, temporal noise, and the hot-pixel list (ROI-scoped)."""
    top, bottom, x1, x2 = band_rows(roi, inset)
    roi_mean = mean_img[top:bottom, x1:x2]
    roi_std = std_img[top:bottom, x1:x2]

    d0 = float(np.median(roi_mean))
    uniformity_std = float(np.std(roi_mean))
    uniformity_range = float(roi_mean.max() - roi_mean.min())
    temporal_noise = float(np.median(roi_std))

    hot_count, hot_sample = hot_pixels(mean_img, roi, inset)
    return {
        "black_level_dn": d0,
        "black_level_pct_full_scale": 100.0 * d0 / FULL_SCALE,
        "roi_uniformity_std_dn": uniformity_std,
        "roi_uniformity_range_dn": uniformity_range,
        "temporal_noise_dn": temporal_noise,
        "hot_pixels_in_roi": hot_sample,       # worst-50 sample for the report
        "hot_pixel_count_in_roi": hot_count,   # TRUE count over the ROI band
        "black_matters": (100.0 * d0 / FULL_SCALE) > BLACK_MATTERS_PCT,
        "structured": uniformity_std > UNIFORM_STD_DN,
    }


def hot_pixels(mean_img, roi, inset):
    """Hot pixels INSIDE the inset ROI band. A pixel is hot only if it clears BOTH the robust outlier
    threshold (median + K*MAD) AND an absolute floor — so a near-zero dark (median~0, MAD~0, where the
    robust threshold collapses toward 0) doesn't flag every 1-2 DN noise pixel as "hot". A genuine hot/stuck
    pixel reads far above black (tens to 255 DN), so the absolute floor keeps it while rejecting sensor noise.

    Returns (count, sample) — the TRUE count over the ROI band and the worst-50 {x,y,dn} for the report."""
    top, bottom, x1, x2 = band_rows(roi, inset)
    roi_mean = mean_img[top:bottom, x1:x2]
    med = np.median(roi_mean)
    mad = np.median(np.abs(roi_mean - med))
    robust_thresh = med + HOT_MAD_K * 1.4826 * mad     # 1.4826*MAD ~= sigma for a normal
    thresh = max(robust_thresh, float(HOT_ABS_DN))     # AND-of-both: robust outlier that is also absolutely high
    mask = roi_mean > thresh
    ys, xs = np.nonzero(mask)
    hits = [{"x": int(x1 + x), "y": int(top + y), "dn": float(roi_mean[y, x])} for y, x in zip(ys, xs)]
    hits.sort(key=lambda h: h["dn"], reverse=True)
    return int(mask.sum()), hits[:50]


def spectral_centroid(gray, roi, inset, coeffs):
    """Intensity-weighted centroid wavelength (nm) over the inset ROI band of a lit frame.

    coeffs = cubic [A,B,C,D] (px->nm), as stored on the calibration profile; None -> centroid in pixel units."""
    top, bottom, x1, x2 = band_rows(roi, inset)
    col_intensity = gray[top:bottom, x1:x2].astype(np.float64).mean(axis=0)   # per-column band average
    cols = np.arange(x1, x2)
    if coeffs is not None:
        axis = np.polyval(coeffs, cols)
    else:
        axis = cols.astype(np.float64)
    total = col_intensity.sum()
    if total <= 0:
        return float("nan")
    return float((axis * col_intensity).sum() / total)


def roi_band_mean(gray, roi, inset):
    top, bottom, x1, x2 = band_rows(roi, inset)
    return float(gray[top:bottom, x1:x2].astype(np.float64).mean())


def dead_pixels(gray, roi, inset):
    """Dead pixels: ROI-band pixels near 0 while their neighbourhood is bright (needs a LIT frame)."""
    top, bottom, x1, x2 = band_rows(roi, inset)
    band = gray[top:bottom, x1:x2].astype(np.float64)
    if band.size == 0 or band.mean() < DEAD_NEIGHBOUR_DN:
        return []                       # frame not bright enough to judge deadness
    ys, xs = np.nonzero(band < DEAD_ABS_DN)
    return [{"x": int(x1 + x), "y": int(top + y)} for y, x in zip(ys, xs)][:50]


def warmup_stats(times, means, centroids):
    """Time series (seconds, ROI-mean, centroid-nm) -> drift %, color shift, time-to-stable."""
    times = np.asarray(times, float)
    means = np.asarray(means, float)
    centroids = np.asarray(centroids, float)

    stable_val = float(np.median(means[-max(1, len(means) // 10):]))    # last ~10% = the settled plateau
    cold_val = float(means[0])
    drift_pct = 100.0 * (stable_val - cold_val) / stable_val if stable_val else 0.0
    color_shift_nm = float(centroids[-1] - centroids[0]) if len(centroids) else float("nan")

    stable_t = _time_to_stable(times, means)
    return {
        "cold_roi_mean_dn": cold_val,
        "stable_roi_mean_dn": stable_val,
        "drift_pct": drift_pct,
        "color_shift_nm": color_shift_nm,
        "time_to_stable_s": stable_t,
        "warmup_matters": abs(drift_pct) > WARMUP_STABLE_PCT,
    }


def _time_to_stable(times, means):
    """First time t after which every rolling change stays under WARMUP_STABLE_PCT for WARMUP_WINDOW_S."""
    n = len(times)
    for i in range(n):
        t0 = times[i]
        ref = means[i]
        if ref <= 0:
            continue
        ok = True
        j = i + 1
        covered = False
        while j < n and times[j] - t0 <= WARMUP_WINDOW_S:
            if abs(means[j] - ref) / ref * 100.0 > WARMUP_STABLE_PCT:
                ok = False
                break
            covered = times[j] - t0 >= WARMUP_WINDOW_S * 0.9
            j += 1
        if ok and (covered or j >= n):
            return float(t0)
    return float(times[-1]) if n else float("nan")


def verdicts(dark, warmup):
    """SPEC §4.5 — turn the metrics into explicit milestone-shaping verdicts (list of strings)."""
    out = []
    if not dark["black_matters"]:
        out.append("DARK: black level ~0 (%.2f%% FS) -> Topic 4 (M3) near-negligible."
                   % dark["black_level_pct_full_scale"])
    elif dark["structured"]:
        out.append("DARK: significant (%.2f%% FS) AND structured (ROI std %.2f DN) -> M3 option (a) PER-PIXEL dark."
                   % (dark["black_level_pct_full_scale"], dark["roi_uniformity_std_dn"]))
    else:
        out.append("DARK: significant (%.2f%% FS) but uniform (ROI std %.2f DN) -> M3 option (b) SCALAR black-level."
                   % (dark["black_level_pct_full_scale"], dark["roi_uniformity_std_dn"]))

    if dark["hot_pixel_count_in_roi"] > 0:
        out.append("BADPIX: %d hot pixel(s) inside the ROI band -> bad-pixel map EARNS its place (M2)."
                   % dark["hot_pixel_count_in_roi"])
    else:
        out.append("BADPIX: no hot pixels in ROI -> SKIP the bad-pixel map; M2 spatial biweight alone suffices.")

    if warmup is not None:
        if warmup["warmup_matters"]:
            out.append("WARMUP: drift %.2f%% (color %.1f nm); stabilises ~%.0fs -> add a warmup gate (§8)."
                       % (warmup["drift_pct"], warmup["color_shift_nm"], warmup["time_to_stable_s"]))
        else:
            out.append("WARMUP: drift %.2f%% below %.1f%% -> no warmup gate needed."
                       % (warmup["drift_pct"], WARMUP_STABLE_PCT))
    return out


# --- rig I/O (needs the real camera; run by Edwin) -------------------------------------------------------

def _gate(message):
    try:
        input("\n>>> %s  [Enter to continue] " % message)
    except EOFError:
        print("\n(non-interactive: proceeding)")


def open_camera(device, exposure):
    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    backend.open(deviceId=device, exposure=exposure)
    return backend


def _brightness(rgb):
    """Spectroscopy brightness metric — 99.9th percentile of the per-pixel max channel (== CapturePanel.__brightness).

    Monotonic in exposure, and keyed to the BRIGHTEST part of the frame so the spectrum uses full dynamic range
    without clipping the emission lines."""
    if rgb is None or rgb.size == 0:
        return 0.0
    return float(np.percentile(rgb.max(axis=2), 99.9))


def _roi_crop(rgb, roi, inset):
    """Crop an HxWx3 (or HxW) array to the inset ROI band; identity if roi is None."""
    if roi is None:
        return rgb
    top, bottom, x1, x2 = band_rows(roi, inset)
    return rgb[top:bottom, x1:x2]


AUTO_EXPOSE_CANDIDATES = [1, 2, 4, 8, 16, 32, 64, 128, 250, 500]


def auto_expose(backend, roi=None, inset=DEFAULT_INSET_ROWS, ceiling=AUTO_EXPOSE_TARGET, settle_ms=500):
    """Pick the operating exposure by SWEEPING candidates over the ROI band and choosing the brightest that
    stays just below clipping.

    NOTE: this does NOT reuse the app's AutoExposureLogicModule bisection — the --diagnose sweep proved this ELP's
    exposure control is INVERTED (lower value = brighter) and CLAMPS above ~16, which violates that module's
    monotonic-increasing assumption and floors it to the worst (brightest, channel-clipping) point. That is a real
    app bug (SPEC §4.8); the probe sidesteps it with a direction-agnostic sweep. Brightness = ROI max-over-channels
    99.9th-pct (strict against per-channel clipping, which merges close emission lines). Returns the chosen
    exposure, left applied."""
    scored = []
    for ev in AUTO_EXPOSE_CANDIDATES:
        backend.setExposure(ev)
        q = drain(backend, settle_ms)     # WALL-CLOCK settle so the exposure change actually takes effect
        # qGray LUMINANCE p99.9 over the ROI — NOT max-over-channels: on this ELP a low-weight channel (blue)
        # clips across the ROI at every exposure, pinning max-channel at 255 and making it useless for the
        # search (and it's the same metric the app's broken auto-exposure uses). Luminance discriminates.
        b = float(np.percentile(rgb_to_qgray(_roi_crop(qimage_to_rgb(q), roi, inset)), 99.9)) \
            if q is not None else float("inf")
        scored.append((ev, b))
        print("    exposure=%3d -> ROI luminance p99.9 = %6.1f" % (ev, b))
    below = [(ev, b) for ev, b in scored if b <= ceiling]
    if below:
        chosen = max(below, key=lambda t: t[1])[0]     # brightest ROI still under the clip ceiling
        print("  picked brightest-below-ceiling(%d)" % ceiling)
    else:
        chosen = min(scored, key=lambda t: t[1])[0]     # everything clips -> the least-bright (safest) point
        print("  all candidates clip -> picked least-bright (safest)")
    backend.setExposure(chosen)
    drain(backend, settle_ms)
    return chosen


def drain(backend, ms):
    """Read frames for `ms` of WALL-CLOCK time, discarding them, and return the last good one.

    cv2.VideoCapture.read() hands back BUFFERED frames near-instantly, so a fixed count of back-to-back reads
    pulls stale queued frames — an exposure change won't have taken effect yet (the auto-exposure "255 at every
    probe -> floor" symptom). Draining over real time lets the UVC stream actually turn over, mirroring the
    app's timed __pumpFrames(350)."""
    end = time.monotonic() + ms / 1000.0
    last = backend.read()              # always at least one read (ms may be 0)
    while time.monotonic() < end:
        f = backend.read()
        if f is not None:
            last = f
    return last


def grab_gray(backend, settle_ms=400):
    """Drain the stream for settle_ms (wall-clock), then return one qGray frame (HxW uint8) or None."""
    qimg = drain(backend, settle_ms)
    if qimg is None:
        return None
    return rgb_to_qgray(qimage_to_rgb(qimg))


def capture_dark_stack(backend, frames):
    """Accumulate per-pixel temporal mean/std over `frames` grabs without holding the whole stack in RAM."""
    n = 0
    acc = None
    acc_sq = None
    first = grab_gray(backend)
    if first is None:
        raise RuntimeError("camera returned no frames — check the device / connection")
    h, w = first.shape
    acc = np.zeros((h, w), np.float64)
    acc_sq = np.zeros((h, w), np.float64)
    for i in range(frames):
        g = grab_gray(backend, settle_ms=0) if i else first     # burst: one fresh frame each (exposure fixed)
        if g is None:
            continue
        gf = g.astype(np.float64)
        acc += gf
        acc_sq += gf * gf
        n += 1
        if (i + 1) % 25 == 0:
            print("    dark frame %d/%d" % (i + 1, frames))
    mean_img = acc / n
    var = np.maximum(acc_sq / n - mean_img * mean_img, 0.0)
    return mean_img, np.sqrt(var), n


def measure_exposure_dependence(backend, exposure, roi, inset):
    """D0 at 1/4x, 1x, 4x exposure -> flat (offset) vs scaling (dark current)."""
    out = {}
    for label, ev in (("quarter", max(1, exposure // 4)), ("nominal", exposure), ("quad", exposure * 4)):
        backend.setExposure(ev)
        mean_img, _, _ = capture_dark_stack(backend, 20)
        top, bottom, x1, x2 = band_rows(roi, inset)
        out[label] = {"exposure": ev, "d0_dn": float(np.median(mean_img[top:bottom, x1:x2]))}
    backend.setExposure(exposure)
    return out


def run_warmup(backend, roi, inset, coeffs, period_s, duration_s):
    times, means, centroids = [], [], []
    t0 = time.monotonic()
    last_gray = None
    while True:
        t = time.monotonic() - t0
        g = grab_gray(backend, settle_ms=200)
        if g is not None:
            last_gray = g
            times.append(t)
            means.append(roi_band_mean(g, roi, inset))
            centroids.append(spectral_centroid(g, roi, inset, coeffs))
            print("    t=%5.1fs  roi_mean=%6.2f  centroid=%7.2f" % (t, means[-1], centroids[-1]))
        if t >= duration_s:
            break
        time.sleep(period_s)
    dead = dead_pixels(last_gray, roi, inset) if last_gray is not None else []
    return times, means, centroids, dead


# --- config resolution -----------------------------------------------------------------------------------

def _parse_ints(s, n, name):
    if s is None:
        return None
    parts = [p for p in s.replace(" ", "").split(",") if p]
    if len(parts) != n:
        raise SystemExit("--%s needs %d comma-separated values, got %r" % (name, n, s))
    return [int(round(float(p))) for p in parts]


def resolve_scene(args):
    """Merge CLI overrides with best-effort app-context auto-resolution. CLI wins; missing -> None."""
    scene = {"device": args.device, "exposure": args.exposure,
             "roi": _parse_ints(args.roi, 4, "roi"),
             "coeffs": [float(c) for c in args.coeffs.split(",")] if args.coeffs else None}

    if None in (scene["device"], scene["roi"], scene["exposure"], scene["coeffs"]):
        auto = _try_app_context()          # populate only the still-missing fields
        for k in ("device", "exposure", "roi", "coeffs"):
            if scene[k] is None and auto.get(k) is not None:
                scene[k] = auto[k]
                print("  auto-resolved %s from app context: %s" % (k, auto[k]))

    if scene["device"] is None:
        scene["device"] = 0
        print("  device not resolved -> defaulting to cv2 index 0 (override with --device)")
    # exposure is intentionally left as-is (may be None): run_probe auto-exposes on the lamp unless a fixed
    # --exposure was given or auto-exposure was disabled.
    if scene["roi"] is None:
        print("  WARNING: no ROI (--roi X1,Y1,X2,Y2) — ROI-band verdicts will be skipped; full frame only.")
    if scene["coeffs"] is None:
        print("  note: no cubic (--coeffs A,B,C,D) — warmup centroid will be in PIXELS, not nm.")
    return scene


def list_modes(device):
    """Probe which capture resolutions the camera actually delivers (cv2/V4L2), to decide the resolution fix.

    The calibration ROI (x2=2226, y2=1658) needs a mode at least ~2240x1664. If such a mode exists, the backend
    should request it; if not, recalibrate at the delivered resolution. Uses cv2 directly (not the fixed-resolution
    backend) since the whole point is to try several modes."""
    import cv2
    from sys import platform
    api = cv2.CAP_V4L2 if platform == "linux" else cv2.CAP_ANY
    candidates = [(640, 480), (1280, 720), (1600, 1200), (1920, 1080), (2048, 1536),
                  (2560, 1440), (2592, 1944), (3264, 2448), (3840, 2160)]
    print("\n=== CAPTURE MODE PROBE (device %d) ===" % device)
    print("  requested -> delivered (calibration needs >= 2240x1664 for ROI x2=2226,y2=1658)")
    seen = set()
    for w, h in candidates:
        cap = cv2.VideoCapture(device, api)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        ok, frame = cap.read()
        aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real = frame.shape[1::-1] if ok and frame is not None else None   # (w,h) actually returned
        cap.release()
        fits = "  <== fits calibration" if real and real[0] >= 2240 and real[1] >= 1664 else ""
        print("  %4dx%-4d -> reported %dx%d, frame %s%s" % (w, h, aw, ah, real, fits))
        if real:
            seen.add(real)
    print("  distinct delivered frame sizes: %s" % sorted(seen))
    if not any(w >= 2240 and h >= 1664 for (w, h) in seen):
        print("  => NO mode reaches the calibration resolution -> recalibrate at the delivered size (e.g. 1600x1200).")
    else:
        print("  => a sufficient mode exists -> point the backend at it (or make ROI resolution-relative).")


def _column_profile(rgb):
    """Band-averaged (central rows) per-column qGray intensity — the dispersed spectrum's shape vs x."""
    gray = rgb_to_qgray(rgb).astype(np.float64)
    h = gray.shape[0]
    band = gray[h // 2 - h // 8: h // 2 + h // 8, :]     # central horizontal band (avoids frame edges)
    return band.mean(axis=0)


def compare_modes(device, out_dir=None, low=(1600, 1200), high=(3264, 2448)):
    """Decide DOWNSCALE (same field of view) vs CROP by capturing the same lit scene at two resolutions.

    If the low-res frame is a scaled-down copy of the high-res one, their column-intensity profiles overlay when
    the x-axis is normalised to [0,1] (and the high-res image, resized down, correlates with the low-res image).
    A crop would show the spectrum at different fractional positions / cut off. This settles whether the fix is a
    software rescale (downscale) or requires matching the capture resolution (crop)."""
    import cv2
    from sys import platform
    api = cv2.CAP_V4L2 if platform == "linux" else cv2.CAP_ANY

    def grab(w, h):
        cap = cv2.VideoCapture(device, api)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        last = None
        for _ in range(15):                 # settle: drain the resolution switch
            ok, f = cap.read()
            if ok and f is not None:
                last = f
        aw, ah = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        rgb = cv2.cvtColor(last, cv2.COLOR_BGR2RGB) if last is not None else None
        return rgb, (aw, ah)

    print("\n=== FOV COMPARE (downscale vs crop) ===")
    Lrgb, Ldim = grab(*low)
    Hrgb, Hdim = grab(*high)
    if Lrgb is None or Hrgb is None:
        print("  could not grab both resolutions (%s / %s)" % (Ldim, Hdim))
        return
    print("  low  captured: %s   high captured: %s" % (Ldim, Hdim))

    Lp, Hp = _column_profile(Lrgb), _column_profile(Hrgb)
    xs = np.linspace(0.0, 1.0, 1000)
    Lr = np.interp(xs, np.linspace(0, 1, len(Lp)), Lp)
    Hr = np.interp(xs, np.linspace(0, 1, len(Hp)), Hp)
    Ln, Hn = Lr / (Lr.max() or 1), Hr / (Hr.max() or 1)
    prof_corr = float(np.corrcoef(Ln, Hn)[0, 1])
    Lpk, Hpk = float(xs[int(np.argmax(Ln))]), float(xs[int(np.argmax(Hn))])

    # 2D confirmation: resize high down to low's shape and correlate the gray images
    Hgray = rgb_to_qgray(Hrgb).astype(np.float64)
    Lgray = rgb_to_qgray(Lrgb).astype(np.float64)
    Hds = cv2.resize(Hgray, (Lgray.shape[1], Lgray.shape[0]), interpolation=cv2.INTER_AREA)
    img_corr = float(np.corrcoef(Hds.ravel(), Lgray.ravel())[0, 1])

    print("  normalized column-profile correlation : %.3f" % prof_corr)
    print("  spectrum peak position  low=%.3f  high=%.3f  (|Δ|=%.3f of width)" % (Lpk, Hpk, abs(Lpk - Hpk)))
    print("  resized-image (high↓→low) correlation : %.3f" % img_corr)
    downscale = prof_corr > 0.9 and abs(Lpk - Hpk) < 0.03 and img_corr > 0.85
    if downscale:
        print("  VERDICT: DOWNSCALE (same FOV) -> the spectrum is present at every resolution, just resampled;")
        print("           fix = rescale ROI + px→nm cubic by the resolution ratio (no data lost, no recalibration).")
    else:
        print("  VERDICT: NOT a clean downscale (likely CROP / different FOV) -> capture must MATCH the calibration")
        print("           resolution, or recalibrate at the capture resolution.")

    if out_dir is not None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            os.makedirs(out_dir, exist_ok=True)
            plt.figure()
            plt.plot(xs, Ln, label="low %s" % (Ldim,))
            plt.plot(xs, Hn, label="high %s" % (Hdim,), ls="--")
            plt.xlabel("normalized column position (0-1)"); plt.ylabel("normalized intensity")
            plt.title("FOV compare: column profiles (overlay => downscale)"); plt.legend()
            plt.savefig(os.path.join(out_dir, "fov_compare.png"), dpi=110, bbox_inches="tight")
            plt.close()
            print("  overlay plot -> %s" % os.path.join(out_dir, "fov_compare.png"))
        except Exception as exc:
            print("  (plot skipped: %s)" % exc)


def _region_stats(gray):
    """mean, median, 99.9th-pct, %saturated(==255) for a gray region."""
    g = gray.astype(np.float64)
    return (float(g.mean()), float(np.median(g)), float(np.percentile(g, 99.9)),
            100.0 * float(np.mean(gray >= 255)))


def diagnose_exposure(backend, roi, inset):
    """Sweep exposure and print full-frame + ROI stats — reveals whether ANY statistic responds to exposure.

    If everything stays flat -> exposure control is not taking effect. If full-frame p99.9 sticks at 255 but ROI
    stats move -> the ROI is fine and stray light was flooring the (former full-frame) auto-exposure. If ROI stats
    also saturate at the lowest exposure -> genuine over-illumination (attenuate the lamp / check the optics)."""
    print("\n=== EXPOSURE DIAGNOSTIC (lamp ON) ===")
    print("  exp | FULL mean  med  p99.9 %%sat | ROI  mean  med  p99.9 %%sat")
    for ev in (1, 2, 4, 8, 16, 32, 64, 128, 250, 500):
        backend.setExposure(ev)
        qimg = drain(backend, 600)
        if qimg is None:
            print("  %3d | (no frame)" % ev)
            continue
        gray = rgb_to_qgray(qimage_to_rgb(qimg))
        fm, fmd, fp, fsat = _region_stats(gray)
        if roi is not None:
            rm, rmd, rp, rsat = _region_stats(_roi_crop(gray, roi, inset))
            print("  %3d | %6.1f %5.0f %5.0f %5.1f | %6.1f %5.0f %5.0f %5.1f"
                  % (ev, fm, fmd, fp, fsat, rm, rmd, rp, rsat))
        else:
            print("  %3d | %6.1f %5.0f %5.0f %5.1f | (no ROI)" % (ev, fm, fmd, fp, fsat))
    print("  (mean moving with exp => exposure works; flat => control not applied;\n"
          "   ROI unsat but FULL p99.9=255 => stray light outside ROI; ROI sat at exp=1 => over-illuminated)")


def diagnose_channels(backend, roi, inset, coeffs, out_dir=None):
    """Locate per-channel clipping across the ROI vs wavelength — tests the white-LED blue-peak hypothesis.

    A white LED's narrow ~450 nm blue-pump peak can saturate the BLUE channel specifically inside the pumpkin
    BLUE_BAND (450-490), corrupting T=S/R there even when luminance never clips. Part 1: per-channel %saturated
    vs exposure (does blue clip at every exposure?). Part 2: per-wavelength R/G/B band-mean + blue-saturation at a
    representative exposure (WHERE does blue clip?)."""
    if roi is None:
        print("  need --roi for the channel diagnostic")
        return
    top, bottom, x1, x2 = band_rows(roi, inset)

    # Resolution check: the calibration ROI may have been authored at a HIGHER resolution than the camera now
    # delivers, so the live frame can be narrower than x2 -> the px->nm cubic no longer maps and eval bands can fall
    # off the frame. Clip the ROI to the real frame and report the covered wavelength range.
    probe0 = qimage_to_rgb(drain(backend, 400))
    fh, fw = probe0.shape[0], probe0.shape[1]
    ex2, ebottom = min(x2, fw), min(bottom, fh)
    print("\n=== PER-CHANNEL SPECTRAL DIAGNOSTIC (lamp ON) ===")
    print("  captured frame: %dx%d | calibration ROI x:%d-%d y:%d-%d" % (fw, fh, x1, x2, top, bottom))
    if x2 > fw or bottom > fh:
        print("  *** RESOLUTION MISMATCH: ROI (x2=%d,y2=%d) exceeds the frame (%dx%d) -> ROI clipped to x2=%d,y2=%d."
              % (x2, bottom, fw, fh, ex2, ebottom))
    cols = np.arange(x1, ex2)
    nm = np.polyval(coeffs, cols) if coeffs is not None else cols.astype(float)
    if coeffs is not None and len(nm):
        print("  covered wavelength range at this width: %.0f-%.0f nm (calibration ROI intended up to x=%d)"
              % (float(np.min(nm)), float(np.max(nm)), x2))
        for name, lo_b, hi_b in (("BLUE_BAND", 450, 490), ("GREEN_BAND", 510, 540),
                                 ("Q_SEARCH", 565, 590), ("Q_BASELINE", 555, 600)):
            covered = float(np.min(nm)) <= lo_b and hi_b <= float(np.max(nm))
            if not covered:
                print("  *** EVAL BAND OFF-FRAME: %s (%d-%d nm) is NOT fully within the captured range." % (name, lo_b, hi_b))

    print("  Part 1 — %% of ROI pixels saturated (==255) per channel vs exposure:")
    print("    exp |    R      G      B")
    for ev in (500, 64, 8, 1):
        backend.setExposure(ev)
        q = drain(backend, 600)
        band = qimage_to_rgb(q)[top:ebottom, x1:ex2, :]
        sats = [100.0 * float(np.mean(band[:, :, c] == 255)) for c in range(3)]
        print("    %3d | %6.2f %6.2f %6.2f" % (ev, sats[0], sats[1], sats[2]))

    ev = 8   # a mid operating point (this ELP: lower value = brighter, so 8 is fairly bright but not the peak)
    backend.setExposure(ev)
    band = qimage_to_rgb(drain(backend, 600))[top:ebottom, x1:ex2, :]
    fband = band.astype(np.float64)
    print("  Part 2 — per-wavelength band-mean at exposure %d (R/G/B) + blue saturation:" % ev)
    print("      nm |    R     G     B  | Bsat%  (BLUE_BAND 450-490, BLUE_PEAK 450-465)")
    nbins = 24
    lo, hi = float(np.min(nm)), float(np.max(nm))
    edges = np.linspace(lo, hi, nbins + 1)
    blue_band_sat = []
    plot_nm, plot_r, plot_g, plot_b = [], [], [], []
    for i in range(nbins):
        m = (nm >= edges[i]) & (nm < edges[i + 1]) if i < nbins - 1 else (nm >= edges[i]) & (nm <= edges[i + 1])
        if not m.any():
            continue
        r = float(fband[:, m, 0].mean()); g = float(fband[:, m, 1].mean()); b = float(fband[:, m, 2].mean())
        bsat = 100.0 * float(np.mean(band[:, m, 2] == 255))
        center = (edges[i] + edges[i + 1]) / 2.0
        mark = " <-- BLUE_BAND" if 450 <= center <= 490 else ""
        print("   %5.0f | %5.0f %5.0f %5.0f | %5.1f%s" % (center, r, g, b, bsat, mark))
        plot_nm.append(center); plot_r.append(r); plot_g.append(g); plot_b.append(b)
        if 450 <= center <= 490:
            blue_band_sat.append(bsat)

    verdict = ("BLUE-CLIP CONFIRMED in the eval band -> reference blue is corrupted in BLUE_BAND; T=S/R unreliable "
               "450-490." if blue_band_sat and max(blue_band_sat) > 1.0 else
               "blue not meaningfully clipped in 450-490 at this exposure -> lead not confirmed here.")
    print("  VERDICT: " + verdict)

    if out_dir is not None:
        _plot_channels(out_dir, plot_nm, plot_r, plot_g, plot_b)
    return verdict


def _plot_channels(out_dir, nm, r, g, b):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        os.makedirs(out_dir, exist_ok=True)
        plt.figure()
        plt.plot(nm, r, color="tab:red", label="R")
        plt.plot(nm, g, color="tab:green", label="G")
        plt.plot(nm, b, color="tab:blue", label="B")
        plt.axhline(255, ls="--", color="gray", lw=0.8, label="clip")
        plt.axvspan(450, 490, color="tab:blue", alpha=0.08, label="BLUE_BAND")
        plt.xlabel("wavelength (nm)"); plt.ylabel("band-mean DN"); plt.title("Per-channel reference spectrum")
        plt.legend()
        plt.savefig(os.path.join(out_dir, "channels.png"), dpi=110, bbox_inches="tight")
        plt.close()
        print("  channel plot -> %s" % os.path.join(out_dir, "channels.png"))
    except Exception as exc:
        print("  (channel plot skipped: %s)" % exc)


def _try_app_context():
    """Read device/exposure/roi/coeffs off the app's selected spectrometer profile, if that context exists.

    Standalone runs usually have no populated session, so this quietly returns {} — CLI args are the real path."""
    try:
        from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
        from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
        from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        if profile is None:
            return {}
        cal = getattr(profile, "spectrometerCalibrationProfile", None)
        sensor = getattr(getattr(profile, "spectrometer", None), "spectrometerSensor", None)
        out = {}
        if sensor is not None:
            out["device"] = SensorCaptureIndexResolver().resolveCaptureIndex(sensor)
            settings = SpectrometerSensorUtil().getSensorSettings(sensor)
            out["exposure"] = getattr(settings, "calibrationExposure", None) if settings else None
        if cal is not None:
            roi = [getattr(cal, "regionOfInterestX1", None), getattr(cal, "regionOfInterestY1", None),
                   getattr(cal, "regionOfInterestX2", None), getattr(cal, "regionOfInterestY2", None)]
            out["roi"] = roi if None not in roi else None
            coeffs = [getattr(cal, "interpolationCoefficient" + c, None) for c in "ABCD"]
            out["coeffs"] = [float(x) for x in coeffs] if None not in coeffs else None
        return out
    except Exception as exc:                                   # any bootstrap gap -> fall back to CLI
        print("  (app-context auto-resolve unavailable: %s)" % exc)
        return {}


# --- report --------------------------------------------------------------------------------------------

def default_out_dir():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # spectracsPy/
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.dirname(root), "spectracs-references", "probe", stamp)


def write_report(out_dir, payload, mean_img=None, warmup=None):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(payload, f, indent=2)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        if mean_img is not None and payload.get("scene", {}).get("roi"):
            x1, y1, x2, y2 = payload["scene"]["roi"]
            y1, y2 = sorted((y1, y2)); x1, x2 = sorted((x1, x2))
            plt.figure()
            plt.imshow(mean_img[y1:y2, x1:x2], cmap="inferno")
            plt.colorbar(label="dark mean (DN)")
            plt.title("Dark mean over ROI band")
            plt.savefig(os.path.join(out_dir, "dark_roi.png"), dpi=110, bbox_inches="tight")
            plt.close()
        if warmup is not None:
            t, m = warmup["times"], warmup["means"]
            plt.figure()
            plt.plot(t, m)
            plt.xlabel("time (s)"); plt.ylabel("ROI mean (DN)"); plt.title("LED warmup")
            plt.savefig(os.path.join(out_dir, "warmup.png"), dpi=110, bbox_inches="tight")
            plt.close()
    except Exception as exc:
        print("  (plot step skipped: %s)" % exc)


# --- orchestration -------------------------------------------------------------------------------------

def run_probe(args):
    _ensure_qt()
    scene = resolve_scene(args)
    print("\nScene: device=%(device)s exposure=%(exposure)s roi=%(roi)s coeffs=%(coeffs)s" % scene)
    backend = open_camera(scene["device"], scene["exposure"])
    auto_exposed = False
    try:
        if args.diagnose:
            _gate("EXPOSURE DIAGNOSTIC: turn the lamp ON")
            diagnose_exposure(backend, scene["roi"], args.inset)
            return
        if args.channels:
            _gate("CHANNEL DIAGNOSTIC: turn the lamp ON")
            diagnose_channels(backend, scene["roi"], args.inset, scene["coeffs"],
                              out_dir=args.out or default_out_dir())
            return
        # Operating exposure — auto-expose on the LIT lamp (matches a real reference capture) unless a fixed
        # --exposure was supplied or auto-exposure was disabled. Runs FIRST so the dark uses the same exposure.
        if scene["exposure"] is not None:
            backend.setExposure(scene["exposure"])
            print("  using fixed exposure %d (auto-exposure skipped)" % scene["exposure"])
        elif args.no_auto_exposure:
            scene["exposure"] = EXPOSURE_FALLBACK
            backend.setExposure(scene["exposure"])
            print("  auto-exposure disabled -> fallback exposure %d" % scene["exposure"])
        else:
            _gate("AUTO-EXPOSURE: turn the lamp ON (as for a reference capture)")
            print("  auto-exposing: sweeping candidates over the ROI band (ceiling %d) ..." % args.target)
            scene["exposure"] = auto_expose(backend, roi=scene["roi"], inset=args.inset, ceiling=args.target)
            auto_exposed = True
            print("  >> converged operating exposure = %d" % scene["exposure"])

        # Phase A — dark
        _gate("PHASE A (dark): block the slit / turn the lamp OFF")
        backend.setExposure(scene["exposure"])   # re-assert after the lamp-on auto-expose
        print("  capturing %d dark frames @ exposure %d ..." % (args.dark_frames, scene["exposure"]))
        mean_img, std_img, n = capture_dark_stack(backend, args.dark_frames)
        print("  captured %d frames." % n)
        dark = None
        exp_dep = None
        if scene["roi"] is not None:
            dark = dark_stats(mean_img, std_img, scene["roi"], args.inset)
            if not args.skip_exposure_sweep:
                print("  measuring exposure dependence (1/4x, 1x, 4x) ...")
                exp_dep = measure_exposure_dependence(backend, scene["exposure"], scene["roi"], args.inset)

        # Phase B — warmup
        warm = None
        warmup_metrics = None
        if not args.skip_warmup and scene["roi"] is None:
            print("  skipping warmup phase: needs an ROI (pass --roi X1,Y1,X2,Y2).")
        elif not args.skip_warmup:
            if auto_exposed:
                print("  NOTE: auto-exposure briefly lit the lamp; for a true cold-start drift curve let the "
                      "bulb rest / power-cycle it before continuing.")
            _gate("PHASE B (warmup): switch the lamp ON now (cold start)")
            print("  sampling every %.1fs for %.0fs ..." % (args.warmup_period, args.warmup_duration))
            times, means, centroids, dead = run_warmup(backend, scene["roi"], args.inset, scene["coeffs"],
                                                        args.warmup_period, args.warmup_duration)
            warmup_metrics = warmup_stats(times, means, centroids)
            warmup_metrics["dead_pixel_count_in_roi"] = len(dead)
            warmup_metrics["dead_pixels_in_roi"] = dead
            warm = {"times": times, "means": means}

        vs = verdicts(dark, warmup_metrics) if dark is not None else \
            ["no ROI supplied -> dark verdicts skipped (pass --roi)"]
        payload = {"scene": scene, "auto_exposed": auto_exposed, "auto_expose_target": args.target,
                   "operating_exposure": scene["exposure"], "dark_frames": int(n), "dark": dark,
                   "exposure_dependence": exp_dep, "warmup": warmup_metrics, "verdicts": vs}

        out_dir = args.out or default_out_dir()
        write_report(out_dir, payload, mean_img=mean_img, warmup=warm)
        print("\n===== VERDICTS =====")
        for v in vs:
            print("  * " + v)
        print("\nReport written to %s" % out_dir)
    finally:
        backend.release()


def _ensure_qt():
    """QImage from a raw buffer is safe without a display, but a QGuiApplication must exist first."""
    try:
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            _ensure_qt.app = QGuiApplication(sys.argv[:1])
    except Exception as exc:
        print("  (Qt init note: %s)" % exc)


# --- self-test (offscreen, no camera) ------------------------------------------------------------------

def selftest():
    """Exercise the pure analysis on synthetic frames; asserts the verdicts route correctly. No rig needed."""
    rng = np.random.default_rng(0)
    h, w = 200, 640
    roi = (40, 80, 600, 120)      # x1,y1,x2,y2
    inset = DEFAULT_INSET_ROWS

    # --- case 1: significant + structured dark with a hot pixel in the ROI ---
    base = np.zeros((h, w), np.float64) + 8.0                       # ~3% FS uniform offset
    base += np.linspace(0, 6, w)[None, :]                          # horizontal gradient -> structured
    mean_img = base.copy()
    mean_img[100, 300] = 200.0                                     # a hot pixel inside the ROI band
    std_img = np.full((h, w), 1.2)
    d = dark_stats(mean_img, std_img, roi, inset)
    assert d["black_matters"], d
    assert d["structured"], d
    assert d["hot_pixel_count_in_roi"] >= 1, d

    # --- case 2: negligible, uniform, clean dark ---
    clean_mean = np.full((h, w), 0.4) + rng.normal(0, 0.05, (h, w))
    clean = dark_stats(clean_mean, np.full((h, w), 0.5), roi, inset)
    assert not clean["black_matters"], clean
    assert clean["hot_pixel_count_in_roi"] == 0, clean

    # --- warmup: rises then plateaus ---
    times = list(np.arange(0, 120, 2.0))
    means = [100 + 40 * (1 - np.exp(-t / 15.0)) for t in times]    # settles well before the end
    centroids = [560.0 + 2.0 * np.exp(-t / 15.0) for t in times]   # small color drift
    wm = warmup_stats(times, means, centroids)
    assert wm["warmup_matters"], wm
    assert 20 <= wm["time_to_stable_s"] <= 90, wm

    # --- centroid + dead pixels ---
    lit = np.zeros((h, w), np.uint8)
    lit[80:120, 40:600] = 180
    lit[100, 300] = 0                                              # a dead pixel in a bright band
    c_nm = spectral_centroid(lit, roi, inset, [0.0, 0.0, 0.5, 400.0])
    assert 400 < c_nm < 800, c_nm
    assert len(dead_pixels(lit, roi, inset)) >= 1

    # --- brightness metric (drives auto-exposure) is monotonic in "exposure" ---
    def synth(level):
        f = np.zeros((20, 40, 3), np.uint8)
        f[8:12, 10:30, :] = level          # a bright band on a dark field
        return f
    assert _brightness(synth(60)) < _brightness(synth(200)), "brightness not monotonic"
    assert _brightness(None) == 0.0

    v1 = verdicts(d, wm)
    v2 = verdicts(clean, None)
    assert any("PER-PIXEL" in s for s in v1), v1
    assert any("EARNS" in s for s in v1), v1
    assert any("near-negligible" in s for s in v2), v2
    print("selftest OK")
    for s in v1 + v2:
        print("  - " + s)


# --- CLI ------------------------------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(description="M0 capture-quality probe (SPEC_capture_quality.md §4)")
    p.add_argument("--selftest", action="store_true", help="run the offscreen analysis self-test (no camera)")
    p.add_argument("--device", type=int, default=None, help="cv2 capture index (auto/app-context if omitted)")
    p.add_argument("--exposure", type=int, default=None,
                   help="fixed manual exposure; disables auto-exposure (auto-expose on the lamp if omitted)")
    p.add_argument("--target", type=int, default=AUTO_EXPOSE_TARGET,
                   help="auto-exposure clip ceiling 0-255: brightest ROI below this wins (default %d)" % AUTO_EXPOSE_TARGET)
    p.add_argument("--no-auto-exposure", action="store_true", dest="no_auto_exposure",
                   help="skip auto-exposure; use the %d fallback (or --exposure)" % EXPOSURE_FALLBACK)
    p.add_argument("--roi", type=str, default=None, help="ROI as X1,Y1,X2,Y2 (px); auto from calibration if omitted")
    p.add_argument("--coeffs", type=str, default=None, help="px->nm cubic A,B,C,D; auto from calibration if omitted")
    p.add_argument("--inset", type=int, default=DEFAULT_INSET_ROWS, help="rows dropped off each ROI-band edge")
    p.add_argument("--dark-frames", type=int, default=DEFAULT_DARK_FRAMES, dest="dark_frames")
    p.add_argument("--warmup-period", type=float, default=DEFAULT_WARMUP_PERIOD_S)
    p.add_argument("--warmup-duration", type=float, default=DEFAULT_WARMUP_DURATION_S)
    p.add_argument("--diagnose", action="store_true",
                   help="exposure diagnostic sweep (lamp on): print full+ROI stats per exposure, then exit")
    p.add_argument("--channels", action="store_true",
                   help="per-channel spectral diagnostic (lamp on): locate R/G/B clipping vs wavelength, then exit")
    p.add_argument("--list-modes", action="store_true", dest="list_modes",
                   help="probe which capture resolutions the camera delivers (decides the resolution fix), then exit")
    p.add_argument("--compare-modes", action="store_true", dest="compare_modes",
                   help="FOV check (lamp on): capture at low+high res, decide downscale-vs-crop, then exit")
    p.add_argument("--skip-warmup", action="store_true", help="dark analysis only")
    p.add_argument("--skip-exposure-sweep", action="store_true", help="skip the 1/4x-4x dark exposure sweep")
    p.add_argument("--out", type=str, default=None, help="output dir (default spectracs-references/probe/<ts>)")
    return p


def _deglue_negative_coeffs(argv):
    """Allow `--coeffs -6.7e-9,...` (space form): argparse treats a leading-negative value as an option, so
    rewrite `--coeffs <val>` -> `--coeffs=<val>` before parsing. The `=` form already works untouched."""
    out = []
    i = 0
    while i < len(argv):
        if argv[i] == "--coeffs" and i + 1 < len(argv):
            out.append("--coeffs=" + argv[i + 1])
            i += 2
        else:
            out.append(argv[i])
            i += 1
    return out


def main():
    args = build_parser().parse_args(_deglue_negative_coeffs(sys.argv[1:]))
    if args.selftest:
        selftest()
        return
    if args.list_modes:
        _ensure_qt()
        list_modes(args.device if args.device is not None else 0)
        return
    if args.compare_modes:
        _ensure_qt()
        _gate("FOV COMPARE: turn the lamp ON (spectrum visible)")
        compare_modes(args.device if args.device is not None else 0, out_dir=args.out or default_out_dir())
        return
    run_probe(args)


if __name__ == "__main__":
    main()
