"""
Unit tests for the spectrum-processing chain + spectrum->colour (SPEC_spectrum_processing.md §9.1).

Spectrum is a plain non-ORM class, so these construct it directly -- no DB / SQLAlchemy mapper needed.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_spectrum_processing.py -q
"""
import math

import numpy

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


def gaussianSpectrum(peakNanometer, start=380, stop=780, sigma=15.0):
    nm = numpy.arange(start, stop + 1)
    intensity = numpy.exp(-((nm - peakNanometer) ** 2) / (2 * sigma ** 2))
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(zip(nm.tolist(), intensity.tolist())))
    return spectrum


# --- SpectrumUtil.normalize ---------------------------------------------------

def test_normalize_max_is_one():
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({500: 2.0, 510: 4.0, 520: 1.0})
    SpectrumUtil().normalize(spectrum)
    assert max(spectrum.valuesByNanometers.values()) == 1.0


def test_normalize_all_zero_is_noop():
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({500: 0.0, 510: 0.0})
    SpectrumUtil().normalize(spectrum)  # must not raise (no divide-by-zero)
    assert set(spectrum.valuesByNanometers.values()) == {0.0}


# --- SpectrumUtil.rebin -------------------------------------------------------

def test_rebin_grid_and_no_nan_for_narrow_input():
    # Input only spans 400..700 nm; rebinning to 380..780 must fill the edges with 0.0, never NaN (§7.1).
    spectrum = gaussianSpectrum(550, start=400, stop=700)
    SpectrumUtil().rebin(spectrum)
    keys = list(spectrum.valuesByNanometers.keys())
    assert keys[0] == 380 and keys[-1] == 780 and len(keys) == 401
    values = list(spectrum.valuesByNanometers.values())
    assert not any(math.isnan(v) for v in values)
    assert spectrum.valuesByNanometers[380] == 0.0
    assert spectrum.valuesByNanometers[780] == 0.0


def test_rebin_preserves_peak_location():
    spectrum = gaussianSpectrum(550)
    SpectrumUtil().rebin(spectrum)
    items = list(spectrum.valuesByNanometers.items())
    peakNanometer = max(items, key=lambda kv: kv[1])[0]
    assert abs(peakNanometer - 550) <= 2


# --- SpectrumUtil.smooth / removeBaseline (behaviour preserved) ---------------

def test_smooth_preserves_keys():
    spectrum = gaussianSpectrum(550)
    originalKeys = list(spectrum.valuesByNanometers.keys())
    SpectrumUtil().smooth(spectrum)
    assert list(spectrum.valuesByNanometers.keys()) == originalKeys


def test_remove_baseline_non_negative():
    spectrum = gaussianSpectrum(550)
    SpectrumUtil().removeBaseline(spectrum)
    assert all(v >= 0 for v in spectrum.valuesByNanometers.values())


def test_mean_averages_captured_frames():
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({500: 0.0, 510: 0.0})
    spectrum.addToCapturedValuesByNanometers({500: 2.0, 510: 6.0})
    spectrum.addToCapturedValuesByNanometers({500: 4.0, 510: 2.0})
    SpectrumUtil().mean(spectrum)
    assert spectrum.valuesByNanometers == {500: 3.0, 510: 4.0}


# --- spectrum -> colour -------------------------------------------------------

def processedGaussian(peakNanometer):
    spectrum = gaussianSpectrum(peakNanometer)
    util = SpectrumUtil()
    util.smooth(spectrum)
    util.removeBaseline(spectrum)
    util.rebin(spectrum)
    util.normalize(spectrum)
    return spectrum


def hueDegrees(color):
    return color.hueF() * 360.0


def test_spectrum_to_color_blue_peak():
    color = SpectralColorUtil().spectrumToColor(processedGaussian(450))
    assert 220.0 <= hueDegrees(color) <= 300.0  # blue / violet


def test_spectrum_to_color_green_peak():
    color = SpectralColorUtil().spectrumToColor(processedGaussian(550))
    assert 45.0 <= hueDegrees(color) <= 180.0  # green / yellow-green


def test_spectrum_to_color_red_peak():
    hue = hueDegrees(SpectralColorUtil().spectrumToColor(processedGaussian(620)))
    assert hue <= 45.0 or hue >= 330.0  # red / orange (allow wraparound)


def test_spectrum_to_color_empty_is_neutral():
    color = SpectralColorUtil().spectrumToColor(Spectrum())
    assert color.red() == color.green() == color.blue()  # grey, no hue
