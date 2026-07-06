"""Our own software auto-exposure (SPEC_real_camera_capture.md §9.3) — NOT the camera's built-in one,
which parks near-black on a mostly-dark emission spectrum.

Objective is spectroscopy-specific: drive the *brightest* part of the frame to just below saturation, so
the spectrum uses the full dynamic range without clipping (clipping merges close lines — e.g. the mercury
green doublet). Brightness is monotonic in exposure, so a bisection converges in a handful of probes.

Pure decision logic: it is handed a `measure(exposure) -> brightness` callable and knows nothing about how
the frame is grabbed — so the same module serves the dev-view live stream, the calibration burst, and the
measurement reference capture. `measure` MUST apply the exposure, let the stream settle, and return the
brightness metric (e.g. a high percentile of luminance)."""


class AutoExposureLogicModule:

    # Target ~92% of full-scale: high enough to use the range, with headroom so noise does not clip.
    DEFAULT_TARGET = 235

    def findExposure(self, measure, minExposure: int, maxExposure: int,
                     target: int = DEFAULT_TARGET, iterations: int = 8) -> int:
        """Largest exposure in [minExposure, maxExposure] whose measured brightness stays <= target.
        Assumes `measure` is monotonic non-decreasing in exposure."""
        lo = minExposure
        hi = maxExposure
        best = minExposure

        # If even the minimum already exceeds the target, that is the best we can do (return the floor).
        for _ in range(iterations):
            if hi - lo <= 1:
                break
            mid = (lo + hi) // 2
            if measure(mid) <= target:
                best = mid
                lo = mid          # room to brighten
            else:
                hi = mid          # too bright, back off
        return best
