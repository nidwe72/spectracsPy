"""L1 (SPEC_capture_quality.md §17.6/2, §17.7/13-14): the gamma decode LUT.

The load-bearing properties are not "it computes a power" — they are the ones the rest of the pipeline
silently depends on: the endpoints are FIXED (so the saturation/dead mask keeps its meaning), the map is
strictly monotone (so max/median still commute with it), the dtype is float32 (so the hot array is not
upgraded), and decode/encode are exact inverses (so the virtual device round-trips).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_gamma_decode.py -q
"""
import unittest

import numpy as np

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import (
    DEFAULT_CAPTURE_GAMMA, SpectralColorUtil)


class GammaDecodeTest(unittest.TestCase):

    def setUp(self):
        self.util = SpectralColorUtil()

    def test_endpoints_are_fixed(self):
        # THE property the saturation/dead mask rides on: 255 stays 255, 0 stays 0, and nothing else
        # lands on either endpoint (else `(gray < 255) & (gray > 0)` would start rejecting/accepting
        # the wrong pixels — §17.6/2).
        lut = self.util.gammaLut()
        self.assertEqual(lut[0], 0.0)
        self.assertEqual(lut[255], 255.0)
        self.assertTrue((lut[1:255] > 0.0).all())
        self.assertTrue((lut[1:255] < 255.0).all())

    def test_strictly_monotone(self):
        # max() and median() are order statistics: they commute EXACTLY with any strictly increasing map,
        # which is why decoding before or after the channel combine is provably identical (§17.5/§17.4).
        lut = self.util.gammaLut()
        self.assertTrue((np.diff(lut) > 0).all())

    def test_lut_matches_closed_form(self):
        expected = (np.arange(256) / 255.0) ** DEFAULT_CAPTURE_GAMMA * 255.0
        np.testing.assert_allclose(self.util.gammaLut(), expected, rtol=1e-6, atol=1e-4)

    def test_uint8_takes_the_lut_path_and_stays_float32(self):
        # A float64 LUT would silently upgrade the whole per-frame array (§17.7/14).
        decoded = self.util.decodeGammaArray(np.array([[0, 128], [200, 255]], dtype=np.uint8))
        self.assertEqual(decoded.dtype, np.float32)
        self.assertEqual(decoded.shape, (2, 2))
        self.assertAlmostEqual(float(decoded[0, 0]), 0.0)
        self.assertAlmostEqual(float(decoded[1, 1]), 255.0)

    def test_float_input_falls_back_to_the_closed_form(self):
        # Off-line replays and tests hand in floats; the two paths must agree on the integer grid.
        grid = np.arange(256, dtype=np.float64)
        np.testing.assert_allclose(self.util.decodeGammaArray(grid),
                                   self.util.decodeGammaArray(grid.astype(np.uint8)),
                                   rtol=1e-5, atol=1e-3)

    def test_negative_input_clamps_to_zero(self):
        self.assertAlmostEqual(float(self.util.decodeGammaArray(np.array([-5.0]))[0]), 0.0)

    def test_decode_undoes_encode(self):
        # The virtual encoder and the reader are inverse halves (§17.7/21) — round-trip a fraction.
        for fraction in (0.0, 0.05, 0.25, 0.5, 0.9, 1.0):
            encoded = self.util.encodeGammaFraction(fraction)
            self.assertLessEqual(encoded, 255.0)
            recovered = float(self.util.decodeGammaArray(np.array([encoded]))[0]) / 255.0
            self.assertAlmostEqual(recovered, fraction, places=6)

    def test_round_trip_survives_8bit_quantization(self):
        # What the virtual device actually does: encode -> round to uint8 -> decode. Gamma encoding gives
        # the DARK end more code levels, so the relative error stays bounded where the Soret band lives.
        for fraction in (0.02, 0.1, 0.4, 0.8):
            quantized = np.uint8(round(self.util.encodeGammaFraction(fraction)))
            recovered = float(self.util.decodeGammaArray(np.array([quantized], dtype=np.uint8))[0]) / 255.0
            self.assertLess(abs(recovered - fraction) / fraction, 0.02, "fraction %s" % fraction)

    def test_gamma_override_is_not_stored_on_the_singleton(self):
        # Singleton = one process-wide instance shared by threads AND by every test in the run: an
        # override must not leak into the next caller (§17.7/13).
        overridden = self.util.decodeGammaArray(np.array([128], dtype=np.uint8), gamma=1.0)
        self.assertAlmostEqual(float(overridden[0]), 128.0, places=4)
        self.assertEqual(SpectralColorUtil().captureGamma(), DEFAULT_CAPTURE_GAMMA)
        default = self.util.decodeGammaArray(np.array([128], dtype=np.uint8))
        self.assertLess(float(default[0]), 60.0)      # 128 -> ~55 under 2.2, not 128

    def test_descriptor_names_the_model(self):
        self.assertEqual(self.util.captureDecodeDescriptor(), "pow2.2")


if __name__ == "__main__":
    unittest.main()
