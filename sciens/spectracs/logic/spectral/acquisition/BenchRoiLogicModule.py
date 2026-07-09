import numpy as np


class BenchRoiLogicModule:
    """Compute the measurement bench's *extended* ROI x-bounds for a target wavelength window.

    Inverts the calibration's px->nm cubic for nmMin/nmMax, picks the real root on the physical
    monotonic branch (nearest the authored ROI edge), and clamps to the raster width — the transparent
    auto-adjust when a target wavelength falls off the sensor. Y is never touched; the extension is
    spectral (horizontal) only. See SPEC_dev_measure_bench.md §12. Pure/side-effect-free."""

    def extendedXBounds(self, calibration, imageWidth, nmMin=400.0, nmMax=700.0):
        x1 = getattr(calibration, "regionOfInterestX1", None)
        x2 = getattr(calibration, "regionOfInterestX2", None)
        coefficients = [getattr(calibration, name, None) for name in
                        ("interpolationCoefficientA", "interpolationCoefficientB",
                         "interpolationCoefficientC", "interpolationCoefficientD")]

        # Fallback: no usable polynomial / bounds -> behave exactly as today (authored ROI unchanged).
        if x1 is None or x2 is None or any(c is None for c in coefficients):
            return x1, x2

        coeffs = [float(c) for c in coefficients]
        left = self.__invert(coeffs, nmMin, int(x1))
        right = self.__invert(coeffs, nmMax, int(x2))

        # Clamp to the raster (transparent adjust) and keep ordering.
        left = max(0, min(imageWidth - 1, left))
        right = max(0, min(imageWidth - 1, right))
        return min(left, right), max(left, right)

    def __invert(self, coeffs, targetNm, referenceX):
        # Solve poly(x) = targetNm; a cubic yields 1 or 3 real roots. Choose the real root nearest the
        # calibrated reference column (the physical monotonic branch); fall back to the reference on
        # any degeneracy (no real root).
        shifted = list(coeffs)
        shifted[-1] = shifted[-1] - targetNm
        roots = np.roots(shifted)
        reals = [r.real for r in roots if abs(r.imag) < 1e-6]
        if not reals:
            return referenceX
        return int(round(min(reals, key=lambda r: abs(r - referenceX))))
