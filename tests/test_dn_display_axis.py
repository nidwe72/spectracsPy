"""The live plot and the raw-spectra plot are drawn on a CAMERA-DN axis (SPEC_capture_quality.md §16.7.2e).

This is display-only: the pipeline keeps linear light (§17). What is asserted here is the property that makes
the display worth having — the operational landmarks land where the operator expects them, and the conversion
is the decode's exact inverse so nothing is invented.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_dn_display_axis.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView


def _spectrum(values):
    spectrum = Spectrum()
    spectrum.valuesByNanometers = dict(values)
    return spectrum


class DnDisplayAxisTest(unittest.TestCase):

    def setUp(self):
        self.util = SpectralColorUtil()

    def test_display_is_the_exact_inverse_of_the_decode(self):
        # Round-trip every code value: decode to linear, encode back, land on the same DN.
        for digitalNumber in (0, 1, 16, 60, 120, 180, 245, 255):
            linear = float(self.util.decodeGammaArray(
                __import__("numpy").array([digitalNumber], dtype="uint8"))[0])
            self.assertAlmostEqual(self.util.encodeGammaValue(linear), digitalNumber, places=3)

    def test_the_landmarks_land_where_the_operator_expects(self):
        # THE point of the axis: on a linear axis the low-DN guard sits at 0.58 of 255 (0.2% up the plot) and a
        # dim-but-healthy 60 DN band at 4.1% — indistinguishable from dead. On the DN axis they are at 6% and
        # 24%. These are the numbers in §16.7.2e's table.
        linearOfGuard = 255.0 * (16.0 / 255.0) ** 2.2
        linearOfDimBand = 255.0 * (60.0 / 255.0) ** 2.2
        self.assertAlmostEqual(linearOfGuard, 0.58, places=1)
        self.assertAlmostEqual(linearOfDimBand, 10.6, places=1)
        self.assertAlmostEqual(self.util.encodeGammaValue(linearOfGuard), 16.0, places=3)
        self.assertAlmostEqual(self.util.encodeGammaValue(linearOfDimBand), 60.0, places=3)

    def test_spectrum_conversion_does_not_mutate_the_source(self):
        # The pipeline's values must survive untouched — this is a display copy.
        source = _spectrum({440.0: 10.57, 500.0: 48.57, 600.0: 233.52})
        display = self.util.toDisplayDnSpectrum(source)
        self.assertEqual(source.valuesByNanometers[440.0], 10.57)
        self.assertIsNot(display, source)
        for nanometer, expected in ((440.0, 60.0), (500.0, 120.0), (600.0, 245.0)):
            self.assertAlmostEqual(display.valuesByNanometers[nanometer], expected, places=0)

    def test_conversion_tolerates_empty_and_none(self):
        self.assertIsNone(self.util.toDisplayDnSpectrum(None))
        empty = _spectrum({})
        self.assertIs(self.util.toDisplayDnSpectrum(empty), empty)

    def test_plot_view_carries_the_axis_through_serialization(self):
        # The report renderer reads the flag off the round-tripped view, so paper matches screen.
        view = SpectrumPlotView(title="Reference vs Sample", axis="dn")
        self.assertEqual(SpectrumPlotView.fromJson(view.toJson()).axis, "dn")

    def test_plot_view_defaults_to_no_axis_conversion(self):
        # Absorbance/transmission plots are unitless ratios and must NOT be re-encoded.
        self.assertIsNone(SpectrumPlotView(_spectrum({500.0: 1.0}), "A(λ)").axis)
        self.assertIsNone(SpectrumPlotView.fromJson(SpectrumPlotView(_spectrum({500.0: 1.0})).toJson()).axis)


if __name__ == "__main__":
    unittest.main()
