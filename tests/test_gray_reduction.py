"""SPEC_capture_quality.md §15 / G1 — the three pixel-intensity reductions in SpectralColorUtil.

The point of the milestone: qGray (photometric luminance, weights blue 5/32) suppresses blue ~3x; the spectrum
reduction switches to max-channel (radiometric). This locks the three reduction formulas + their homogeneity
(the property that makes max cancel in T = S/R exactly as qGray did).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_gray_reduction.py -q
"""
import unittest

import numpy as np
from PySide6.QtGui import QColor, qGray

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


class GrayReductionTest(unittest.TestCase):

    def setUp(self):
        self.util = SpectralColorUtil()

    def test_maximum_is_the_brightest_channel(self):
        self.assertEqual(self.util.toGrayMaximum(QColor(10, 40, 200)), 200)   # blue-dominant -> the blue channel
        self.assertEqual(self.util.toGrayMaximum(QColor(200, 40, 10)), 200)   # red-dominant
        self.assertEqual(self.util.toGrayMaximum(QColor(0, 0, 0)), 0)

    def test_luminance_matches_qt_qgray(self):
        # toGrayLuminance must reproduce the OLD reduction exactly (Qt's qGray weighting).
        for c in (QColor(10, 40, 200), QColor(255, 255, 255), QColor(123, 45, 67), QColor(0, 200, 0)):
            self.assertEqual(self.util.toGrayLuminance(c), qGray(c.red(), c.green(), c.blue()))

    def test_mean_is_unweighted(self):
        self.assertEqual(self.util.toGrayMean(QColor(30, 60, 90)), 60)

    def test_blue_is_recovered_vs_luminance(self):
        # The whole reason for §15: a vivid blue pixel reads ~3x higher under max than under luminance.
        blue = QColor(0, 0, 240)
        self.assertEqual(self.util.toGrayMaximum(blue), 240)
        self.assertEqual(self.util.toGrayLuminance(blue), (5 * 240) // 32)   # 37 — the crushed value
        self.assertGreater(self.util.toGrayMaximum(blue), 3 * self.util.toGrayLuminance(blue))

    def test_array_siblings_match_scalars_and_qgray(self):
        r = np.array([0, 200, 123], dtype=np.float32)
        g = np.array([0, 40, 45], dtype=np.float32)
        b = np.array([240, 10, 67], dtype=np.float32)
        np.testing.assert_array_equal(self.util.toGrayMaximumArray(r, g, b), np.array([240, 200, 123]))
        np.testing.assert_allclose(self.util.toGrayLuminanceArray(r, g, b), (11 * r + 16 * g + 5 * b) / 32.0)
        np.testing.assert_allclose(self.util.toGrayMeanArray(r, g, b), (r + g + b) / 3.0)

    def test_maximum_is_homogeneous(self):
        # max(k*x) == k*max(x): this is WHY the reduction cancels in T = S/R (SPEC §15.2). Verify for a
        # colour proportion scaled by a transmission factor.
        r, g, b = np.array([20.0]), np.array([50.0]), np.array([200.0])
        for k in (0.25, 0.5, 0.8):
            scaled = self.util.toGrayMaximumArray(k * r, k * g, k * b)
            np.testing.assert_allclose(scaled, k * self.util.toGrayMaximumArray(r, g, b))


if __name__ == "__main__":
    unittest.main()
