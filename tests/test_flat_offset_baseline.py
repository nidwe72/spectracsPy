"""
SPEC_capability_proof.md §7.0.1 — the flat-offset baseline LogicModule (E1/F2) with its two floor modes,
the median de-spike LogicModule, and the non-destructive plugin_sdk ops BaselineOffsetOp / SmoothOp /
MedianFilterOp (E2/F1).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_flat_offset_baseline.py -q
"""
import numpy

import sciens.spectracs.plugin_sdk as sdk
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModule import FlatOffsetBaselineLogicModule
from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModuleParameters import FlatOffsetBaselineLogicModuleParameters
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModule import MedianFilterSpectrumLogicModule
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModuleParameters import MedianFilterSpectrumLogicModuleParameters


def _spectrum(valuesByNanometers):
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(valuesByNanometers))
    return spectrum


def _flatOffset(spectrum, mode=None):
    parameters = FlatOffsetBaselineLogicModuleParameters()
    parameters.setSpectrum(spectrum)
    if mode is not None:
        parameters.setFloorMode(mode)
    return FlatOffsetBaselineLogicModule().flatOffsetBaseline(parameters).getSpectrum()


# --- F2: the flat-offset LogicModule, anchorMean (default) --------------------

def test_anchor_mean_makes_signal_free_region_read_zero():
    # A gaussian bump on a constant additive floor b=0.20. The default anchorMean floor reads the deep-red window
    # [615,625] (flat baseline there) → the signal-free tails read ~0 and the bump drops by exactly b.
    nm = numpy.arange(440, 631)
    values = 0.20 + numpy.exp(-((nm - 560.0) ** 2) / (2 * 12.0 ** 2))
    corrected = _flatOffset(_spectrum(zip(nm.tolist(), values.tolist()))).valuesByNanometers
    assert min(corrected.values()) >= 0.0
    assert corrected[440] < 1e-6
    assert abs(corrected[560] - 1.0) < 0.02


def test_anchor_mean_reads_the_red_end_window_not_the_global_min():
    # The floor is the MEAN over [615,625], not a global minimum. A lone low point outside the window must NOT set
    # the floor (that was the failure mode of the old min estimator, SPEC §7.0.1 (B)).
    nm = numpy.arange(440, 631)
    values = numpy.full(nm.shape, 0.10)
    values[(nm >= 615) & (nm <= 625)] = 0.40      # the anchor window sits higher than the rest
    values[50] = 0.01                              # a global-min dip OUTSIDE the window
    corrected = _flatOffset(_spectrum(zip(nm.tolist(), values.tolist()))).valuesByNanometers
    assert corrected[615] < 1e-6 and corrected[625] < 1e-6   # window itself reads ~0 (floor ≈ 0.40)
    assert corrected[500] < 1e-6                              # 0.10 baseline < 0.40 floor → clipped 0


# --- F2: the flat-offset LogicModule, medianMin (kept selectable) -------------

def test_median_min_mode_rejects_a_cold_pixel():
    nm = numpy.arange(440, 631)
    values = numpy.full(nm.shape, 0.50)
    values[75] = 0.02                              # lone cold pixel a naive min would latch onto
    corrected = _flatOffset(_spectrum(zip(nm.tolist(), values.tolist())), mode="medianMin").valuesByNanometers
    assert numpy.median(list(corrected.values())) < 0.05     # floor really ~0.50 → baseline ~0


# --- the median-filter LogicModule / de-spike ---------------------------------

def test_median_filter_module_rejects_a_lone_spike():
    nm = numpy.arange(440, 631)
    values = numpy.full(nm.shape, 0.30)
    values[40] = 5.0
    parameters = MedianFilterSpectrumLogicModuleParameters()
    parameters.setSpectrum(_spectrum(zip(nm.tolist(), values.tolist())))
    filtered = MedianFilterSpectrumLogicModule().medianFilter(parameters).getSpectrum()
    assert max(filtered.valuesByNanometers.values()) < 0.5
    assert abs(numpy.median(list(filtered.valuesByNanometers.values())) - 0.30) < 1e-6


# --- the plugin_sdk ops (role-agnostic + non-destructive) ---------------------

def test_median_filter_op_despikes_and_is_non_destructive():
    nm = numpy.arange(440, 631)
    values = numpy.full(nm.shape, 0.30)
    values[40] = 5.0                               # nm 480
    original = _spectrum(zip(nm.tolist(), values.tolist()))
    container = sdk.SpectraContainer()
    container.addToSpectra(original, sdk.ABSORPTION)

    out = sdk.MedianFilterOp().apply(container)

    assert original.valuesByNanometers[480] == 5.0            # input untouched
    despiked = out.getSpectra()[sdk.ABSORPTION].valuesByNanometers
    assert max(despiked.values()) < 0.5                       # spike gone
    assert out.getInputs() == [container]


def test_baseline_offset_op_is_non_destructive_and_uses_the_anchor_window():
    nm = numpy.arange(440, 631)
    values = numpy.full(nm.shape, 0.30)
    values[120] = 1.30                             # nm 560 bump; anchor window [615,625] stays flat 0.30
    original = _spectrum(zip(nm.tolist(), values.tolist()))
    container = sdk.SpectraContainer()
    container.addToSpectra(original, sdk.ABSORPTION)

    out = sdk.BaselineOffsetOp().apply(container)

    assert original.valuesByNanometers[560] == 1.30           # input untouched
    corrected = out.getSpectra()[sdk.ABSORPTION].valuesByNanometers
    assert abs(corrected[560] - 1.0) < 1e-6                   # floor 0.30 (anchor mean) subtracted
    assert corrected[440] < 1e-6
    assert out.getInputs() == [container]


def test_smooth_op_light_defaults_preserve_the_envelope_and_dont_mutate_input():
    nm = numpy.arange(440, 631)
    bump = numpy.exp(-((nm - 560.0) ** 2) / (2 * 15.0 ** 2))
    original = _spectrum(zip(nm.tolist(), bump.tolist()))
    peakBefore = original.valuesByNanometers[560]
    container = sdk.SpectraContainer()
    container.addToSpectra(original, sdk.ABSORPTION)

    out = sdk.SmoothOp().apply(container)

    assert original.valuesByNanometers[560] == peakBefore
    smoothedPeak = out.getSpectra()[sdk.ABSORPTION].valuesByNanometers[560]
    assert abs(smoothedPeak - 1.0) < 0.05


def test_ops_export_surface():
    for name in ("BaselineOffsetOp", "SmoothOp", "MedianFilterOp"):
        assert name in sdk.__all__ and hasattr(sdk, name)
