"""
Track B (B4/B5) — plugin_sdk import surface, container->container op adapters (mean / transmission /
absorption), and the Qt-free EvaluationResult view-models (SPEC_pumpkin_integration.md B.2/B.3).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_plugin_sdk_ops.py -q
"""
import unittest

import sciens.spectracs.plugin_sdk as sdk
from sciens.spectracs.model.spectral.Spectrum import Spectrum


def _spectrum(values, captured=None):
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(values))
    if captured is not None:
        for frame in captured:
            spectrum.addToCapturedValuesByNanometers(dict(frame))
    return spectrum


class PluginSdkOpsTest(unittest.TestCase):

    def test_import_surface_is_complete(self):
        for name in sdk.__all__:
            self.assertTrue(hasattr(sdk, name), "plugin_sdk missing %s" % name)

    def test_mean_op_reduces_captured_frames(self):
        spectrum = _spectrum({450: 0.0, 500: 0.0},
                             captured=[{450: 1.0, 500: 2.0}, {450: 3.0, 500: 4.0}])
        container = sdk.SpectraContainer()
        container.addToSpectra(spectrum, sdk.REFERENCE)
        out = sdk.MeanOp().apply(container)
        meaned = out.getSpectra()[sdk.REFERENCE]
        self.assertAlmostEqual(meaned.valuesByNanometers[450], 2.0)
        self.assertAlmostEqual(meaned.valuesByNanometers[500], 3.0)
        self.assertEqual(out.getInputs(), [container])  # provenance recorded

    def test_transmission_op(self):
        container = sdk.SpectraContainer()
        container.addToSpectra(_spectrum({450: 1.0, 500: 0.5}), sdk.REFERENCE)
        container.addToSpectra(_spectrum({450: 0.5, 500: 0.25}), sdk.SAMPLE)
        transmission = sdk.TransmissionOp().apply(container).getSpectra()[sdk.TRANSMISSION]
        self.assertAlmostEqual(transmission.valuesByNanometers[450], 0.5)
        self.assertAlmostEqual(transmission.valuesByNanometers[500], 0.5)

    def test_absorption_op(self):
        container = sdk.SpectraContainer()
        container.addToSpectra(_spectrum({600: 1.0}), sdk.REFERENCE)
        container.addToSpectra(_spectrum({600: 0.1}), sdk.SAMPLE)
        absorption = sdk.AbsorptionOp().apply(container).getSpectra()[sdk.ABSORPTION]
        self.assertAlmostEqual(absorption.valuesByNanometers[600], 1.0)  # -log10(0.1)

    def test_evaluation_result_holds_view_models(self):
        result = sdk.EvaluationResult()
        result.addItem(sdk.ColorSwatchView((10, 200, 20), "measured"))
        result.addItem(sdk.VerdictView("PERFECT-ROASTED"))
        result.addItem(sdk.LabelView("hue 60°"))
        items = result.getItems()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].rgb, (10, 200, 20))
        self.assertEqual(items[1].roastState, "PERFECT-ROASTED")


if __name__ == "__main__":
    unittest.main()
