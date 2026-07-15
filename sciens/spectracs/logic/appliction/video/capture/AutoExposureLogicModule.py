"""Our own software auto-exposure (SPEC_real_camera_capture.md §9.3, SPEC_capture_quality.md §14) — NOT the
camera's built-in one, which parks near-black on a mostly-dark emission spectrum.

DIRECTION-AGNOSTIC. It does NOT assume brightness rises with the exposure VALUE: the ELP spectrometer camera's
exposure control is INVERTED — a higher value is DIMMER (SPEC_capture_quality.md §4.8) — which defeats a plain
low→high bisection (the old implementation, which walked the wrong way and landed dark/bloomed). Instead this
sweeps a ladder of candidate exposures, measures the DELIVERED brightness of each, and selects by that measured
brightness. So it converges whichever way the axis runs (and tolerates flat/clamped regions a bisection can't).

Objective is spectroscopy-specific: drive the *brightest* part of the frame to just below saturation, so the
spectrum uses the full dynamic range without clipping (clipping merges close lines — e.g. the mercury green
doublet). Pure decision logic: it is handed a `measure(exposure) -> brightness` callable and knows nothing about
how the frame is grabbed — so the same module serves the dev-view live stream, the measurement CapturePanel, the
calibration bursts, and the calibration unit test. `measure` MUST apply the exposure, let the stream settle, and
return the brightness metric — use `qGrayPeak` (below) for that."""
import numpy as np


class AutoExposureLogicModule:

    # Target ~92% of full-scale: high enough to use the range, with headroom so the peak channel does not clip.
    DEFAULT_TARGET = 235
    # Lowest exposure the sweep will probe — exposure=1 is a UVC edge artifact on the ELP (reads ~255, §14.6).
    MIN_SEARCH_EXPOSURE = 2

    def findExposure(self, measure, minExposure: int, maxExposure: int,
                     target: int = DEFAULT_TARGET, iterations: int = 8) -> int:
        """Exposure in [minExposure, maxExposure] whose MEASURED brightness is the highest that still stays
        <= target (the brightest capture that does not clip). Direction-agnostic: the winner is chosen purely by
        measured brightness, so the exposure axis may run either way. `measure` need only be LOCALLY monotonic
        between adjacent probes (used by the refinement), not globally."""
        # Never probe exposure=1: on the ELP (UVC) it reads anomalously bright — a power-on/edge artifact, not a
        # real brightness (SPEC_capture_quality.md §4.8/§14.6) — which the search would misread as clipping.
        lo = max(int(minExposure), self.MIN_SEARCH_EXPOSURE)
        hi = int(maxExposure)
        if hi <= lo:
            return lo
        iterations = max(3, int(iterations))

        # Phase 1 — coarse geometric ladder across the whole range (finer at the low end, where the ELP is bright).
        # Kept sparse so most of the probe budget goes to Phase 2, which is where precision (peak near target) is won.
        coarseCount = max(3, iterations - 5)
        measured = {}
        for exposure in self.__ladder(lo, hi, coarseCount):
            measured[exposure] = measure(exposure)

        # Phase 2 — hone the target-crossing between the first pair of adjacent (in exposure) probes that straddle
        # the target, i.e. one <= target and one > target. Bisect that exposure interval, tracking the crossing by
        # the <=target / >target SIGN (not by which side is brighter) — so it converges whether the axis rises or
        # falls. This lands the peak just below saturation instead of at a coarse-ladder step well under it.
        straddle = self.__straddle(measured, target)
        if straddle is not None:
            low, high = straddle
            for _ in range(iterations - coarseCount):
                mid = (low + high) // 2
                if mid == low or mid == high:
                    break
                measured[mid] = measure(mid)
                if (measured[low] <= target) == (measured[mid] <= target):
                    low = mid
                else:
                    high = mid
        return self.__select(measured, target, lo)

    def __straddle(self, measured: dict, target: int):
        """First adjacent (in exposure) probe pair whose <=target property flips — the target-crossing interval."""
        probes = sorted(measured.keys())
        for a, b in zip(probes, probes[1:]):
            if (measured[a] <= target) != (measured[b] <= target):
                return (a, b)
        return None

    def __ladder(self, lo: int, hi: int, count: int):
        """`count` exposures from lo to hi, geometrically spaced (so low exposures — brightest on the inverted
        ELP — are sampled densely), ints, deduped, ascending."""
        if count <= 1:
            return [lo]
        useGeometric = lo > 0
        ratio = (hi / lo) ** (1.0 / (count - 1)) if useGeometric else None
        values = []
        for k in range(count):
            value = int(round(lo * (ratio ** k))) if useGeometric else int(round(lo + (hi - lo) * k / (count - 1)))
            values.append(min(hi, max(lo, value)))
        seen, result = set(), []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @staticmethod
    def qGrayPeak(image, percentile: float = 99.9) -> float:
        """Shared brightness metric for the auto-exposure sweep: a high percentile of qGray luminance
        ((11R+16G+5B)/32) over the frame — the spectrum's peak. qGray (not max-over-channels) is used because on a
        coloured emission-line source max-over-channels pegs at 255 from a few saturated line pixels and defeats
        the search; qGray responds smoothly and monotonically to exposure (proven by the --diagnose sweep,
        SPEC_capture_quality.md §14.6). `image` is a detached RGB888 QImage; returns 0.0 for a missing frame."""
        if image is None:
            return 0.0
        converted = image.convertToFormat(image.format())
        width, height = converted.width(), converted.height()
        pointer = converted.constBits()
        pixels = np.frombuffer(pointer, np.uint8).reshape(height, converted.bytesPerLine())
        rgb = pixels[:, :width * 3].reshape(height, width, 3).astype(np.float32)
        qgray = (11.0 * rgb[:, :, 0] + 16.0 * rgb[:, :, 1] + 5.0 * rgb[:, :, 2]) / 32.0
        return float(np.percentile(qgray, percentile))

    def __select(self, measured: dict, target: int, fallback: int) -> int:
        """Brightest exposure whose measured brightness stays <= target; if every probe clips (all > target),
        the dimmest one (least clipped); `fallback` only if nothing was measured."""
        below = [(exposure, brightness) for exposure, brightness in measured.items() if brightness <= target]
        if below:
            return max(below, key=lambda pair: pair[1])[0]
        if measured:
            return min(measured.items(), key=lambda pair: pair[1])[0]
        return fallback
