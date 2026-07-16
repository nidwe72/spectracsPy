"""
Runnable usage sample / smoke test for the spectrum-processing + spectrum->colour chain
(SPEC_spectrum_processing.md §9.2). Also the template for PumpkinPlugin.evaluation (Roadmap #6).

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python tests/spectrum_to_color_usage_sample.py
"""
import numpy

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


def synthesizeGaussianSpectrum(peakNanometer: int, sigma: float = 15.0) -> Spectrum:
    nm = numpy.arange(380, 781)
    intensity = numpy.exp(-((nm - peakNanometer) ** 2) / (2 * sigma ** 2))
    spectrum = Spectrum()
    spectrum.setValuesByNanometers(dict(zip(nm.tolist(), intensity.tolist())))
    return spectrum


def evaluate(peakNanometer: int):
    spectrum = synthesizeGaussianSpectrum(peakNanometer)

    spectrumUtil = SpectrumUtil()
    spectrumUtil.smooth(spectrum)
    spectrumUtil.removeBaseline(spectrum)
    spectrumUtil.rebin(spectrum)
    spectrumUtil.normalize(spectrum)

    color = SpectralColorUtil().spectrumToColor(spectrum)
    print(f"peak {peakNanometer} nm -> {color.name()}  hue={color.hueF() * 360.0:.1f} deg")


if __name__ == "__main__":
    for peak in (450, 550, 620):
        evaluate(peak)
