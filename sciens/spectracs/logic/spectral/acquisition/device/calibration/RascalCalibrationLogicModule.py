from typing import List

import numpy as np
from numpy import float32, float64
from numpy.polynomial.polynomial import polyval
from scipy.signal import find_peaks
from rascal.atlas import Atlas
from rascal.calibrator import Calibrator
from rascal.util import refine_peaks

from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class RascalCalibrationError(Exception):
    """Raised when rascal cannot find a calibration solution."""


class RascalCalibrationResult:
    spectralLines: List[SpectralLine] = None
    interpolationCoefficientA: float = None
    interpolationCoefficientB: float = None
    interpolationCoefficientC: float = None
    interpolationCoefficientD: float = None

    def getSpectralLines(self):
        if self.spectralLines is None:
            self.spectralLines = []
        return self.spectralLines


class RascalCalibrationLogicModule:
    """RANSAC/Hough wavelength calibration via the `rascal` library, tuned for the CFL atlas.

    Two modes:
      - standalone: rascal matches detected peaks to the CFL atlas on its own.
      - seeded: the heuristic matcher's cubic (px -> nm) is passed as rascal's starting solution
        (fit_coeff), which is more accurate/stable in the dense europium red cluster.

    The recipe (atlas capped at MAX_ATLAS_NANOMETER, loose range_tolerance, cubic fit) was validated
    on the CFL test image: standalone ~1.4 nm max error, seeded ~0.5 nm.
    """

    # Cap the atlas below the dense far-red europium/argon lines so RANSAC cannot map the rightmost
    # peak past ~650 nm (the failure mode that wrecked an un-capped fit).
    MAX_ATLAS_NANOMETER = 635.0

    def _buildAtlasMasterDatas(self):
        masterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()
        masterDatas = [md for md in masterDatasByNames.values()
                       if md.nanometer is not None and md.nanometer <= self.MAX_ATLAS_NANOMETER]
        masterDatas.sort(key=lambda md: md.nanometer)
        return masterDatas

    def match(self, spectrum: Spectrum, seedCoefficients=None) -> RascalCalibrationResult:
        """seedCoefficients: optional cubic [A, B, C, D] (px -> nm, descending) from the heuristic."""
        intensities = np.asarray(list(spectrum.valuesByNanometers.values()), float32)
        numPixels = len(intensities)

        peaks = find_peaks(intensities, distance=3, width=3, rel_height=0.5, prominence=12)[0]
        peaks = refine_peaks(intensities, peaks, window_width=5)

        masterDatas = self._buildAtlasMasterDatas()
        atlas = Atlas()
        atlas.add_user_atlas(
            np.asarray(['Hg'] * len(masterDatas), str),
            np.asarray([md.nanometer * 10.0 for md in masterDatas], float64),   # Angstroms
            np.asarray([(md.intensity or 1) for md in masterDatas], float64))
        masterDataByAngstrom = {round(md.nanometer * 10.0): md for md in masterDatas}

        calibrator = Calibrator(peaks, spectrum=intensities)
        calibrator.set_calibrator_properties(num_pix=numPixels)
        calibrator.set_hough_properties(num_slopes=2000, range_tolerance=500.0, xbins=200, ybins=200,
                                        min_wavelength=3500.0, max_wavelength=6500.0)
        calibrator.set_ransac_properties(sample_size=5, top_n_candidate=5, filter_close=True)
        calibrator.set_atlas(atlas, candidate_tolerance=10.0)
        calibrator.do_hough_transform()

        fitKwargs = {}
        if seedCoefficients is not None:
            # heuristic cubic is px -> nm (descending); rascal wants ascending Angstrom coefficients.
            fitKwargs['fit_coeff'] = np.asarray(list(seedCoefficients[::-1]), float64) * 10.0

        try:
            result = tuple(calibrator.fit(max_tries=3000, fit_deg=3, **fitKwargs))
        except AssertionError as exception:
            raise RascalCalibrationError("rascal could not find a calibration solution") from exception

        bestPolynomial = np.atleast_1d(result[0])   # ascending Angstrom
        matchedPeaks = result[1]
        matchedAtlas = result[2]

        calibrationResult = RascalCalibrationResult()
        # ascending Angstrom [p0,p1,p2,p3] -> our nm cubic A*px^3+B*px^2+C*px+D
        calibrationResult.interpolationCoefficientA = float(bestPolynomial[3]) / 10.0
        calibrationResult.interpolationCoefficientB = float(bestPolynomial[2]) / 10.0
        calibrationResult.interpolationCoefficientC = float(bestPolynomial[1]) / 10.0
        calibrationResult.interpolationCoefficientD = float(bestPolynomial[0]) / 10.0

        for peakPixel, atlasAngstrom in zip(matchedPeaks, matchedAtlas):
            masterData = masterDataByAngstrom.get(round(float(atlasAngstrom)))
            if masterData is None:
                continue
            spectralLine = SpectralLine()
            spectralLine.pixelIndex = int(peakPixel)
            spectralLine.spectralLineMasterData = masterData
            calibrationResult.getSpectralLines().append(spectralLine)

        return calibrationResult
