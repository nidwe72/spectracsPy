"""Colour-constrained CFL emission-line detection — the SINGLE source of truth for wavelength-calibration line
anchoring (SPEC_capture_quality.md §13). Used by SpectrometerWavelengthCalibrationLogicModule (production) AND by the
calibration unit test (diagnostics/calibration_fix_test.py) — no duplicated algorithm.

Root cause it fixes: at high capture resolution the green Hg doublet splits and the sharp Europium red line
out-prominences it, so anchoring green by "most-prominent peak" mislabels red as green and the whole calibration
collapses. Here each line is picked the way that is ROBUST for it:
  * green / green_left / aqua  -> by COLOUR: gate on channel dominance (interval-free, robust at low saturation),
                                  rank by channel-strength × prominence. hue-similarity is confidence only.
  * violet + blue              -> both render blue-ish -> cluster the blue-dominant peaks left of green and split by
                                  POSITION (leftmost line = violet, next = blue).
  * Eu red                     -> by PROMINENCE: largest peak RIGHT of green (611 saturates toward white -> a colour
                                  filter would skip it).
"""
import numpy as np
from numpy import float32
from scipy.signal import find_peaks, peak_prominences

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import \
    SpectralLineMasterDataColorName as Name


class DetectedLine:
    def __init__(self, pixelIndex, hueScore, chanScore):
        self.pixelIndex = pixelIndex
        self.hueScore = hueScore
        self.chanScore = chanScore

    @property
    def confidence(self):
        return min(self.hueScore, self.chanScore)


class WavelengthLineDetectionLogicModule:

    DISTANCE = 3
    WIDTH = 3
    MIN_CHANNEL = 0.02          # channel-dominance gate: below this a peak is "not that colour"
    CLUSTER_GAP = 80            # px; merge a line's sub-peaks (they split at high resolution)
    PROMINENCE_FRACTION = 0.01  # SPEC_capture_quality.md §15/G4: prominence as a FRACTION of the spectrum peak,
                                # NOT an absolute (was prominence=1). Makes line detection invariant to the
                                # intensity reduction (qGray vs max-channel) and to exposure. 0.01 ~= the old
                                # absolute 1 at the qGray peak (~120); rig-tunable if spurious peaks appear.
    DOUBLET_LEFT = 60           # green-left search window (px left of the green anchor)
    DOUBLET_RIGHT = 4

    # reference wavelengths (nm) — used only to derive each line's reference COLOUR via wavelengthToColor
    NM = {Name.MERCURY_MANGO_GREEN: 546.5, Name.MERCURY_MANGO_GREEN_LEFT: 542.4,
          Name.EUROPIUM_VIVID_GAMBOGE: 611.6, Name.MERCURY_FRENCH_VIOLET: 404.7,
          Name.MERCURY_BLUE: 435.8, Name.TERBIUM_AQUA: 487.7}
    CHANNEL = {Name.MERCURY_MANGO_GREEN: "green", Name.MERCURY_MANGO_GREEN_LEFT: "green",
               Name.EUROPIUM_VIVID_GAMBOGE: "red", Name.MERCURY_FRENCH_VIOLET: "blue",
               Name.MERCURY_BLUE: "blue", Name.TERBIUM_AQUA: "cyan"}

    def detect(self, spectrum):
        """spectrum: pixel-indexed valuesByNanometers (qGray intensity) + colorsByPixelIndices (QColor per pixel).
        Returns {SpectralLineMasterDataColorName: DetectedLine} (empty if no green anchor is found)."""
        keys = list(spectrum.valuesByNanometers.keys())               # pixel indices, ascending
        intensities = np.asarray(list(spectrum.valuesByNanometers.values()), float32)
        colours = spectrum.getColorsByPixelIndices() or {}
        util = SpectralColorUtil()
        refColour = {name: util.wavelengthToColor(nm) for name, nm in self.NM.items()}

        peak = float(intensities.max()) if intensities.size else 0.0
        if peak <= 0.0:
            return {}                                                 # no signal at all -> no anchor
        prominence = self.PROMINENCE_FRACTION * peak                  # §15/G4: scale-invariant (was absolute 1)
        idx, _ = find_peaks(intensities, distance=self.DISTANCE, width=self.WIDTH, rel_height=0.5, prominence=prominence)
        if len(idx) == 0:
            return {}
        proms = peak_prominences(intensities, idx)[0]
        peaks = list(zip([int(i) for i in idx], [float(p) for p in proms]))     # (arrayIndex, prominence)

        def colourOf(i):
            return colours.get(keys[i]) if 0 <= i < len(keys) else None

        def line(i, name):
            colour = colourOf(i)
            return DetectedLine(int(keys[i]), util.hueSimilarity(colour, refColour[name]),
                                util.channelDominance(colour, self.CHANNEL[name]))

        result = {}
        green = self.__pickColour(peaks, colourOf, refColour[Name.MERCURY_MANGO_GREEN], "green", util)
        if green is None:
            return {}
        result[Name.MERCURY_MANGO_GREEN] = line(green, Name.MERCURY_MANGO_GREEN)

        # Eu red — most-prominent peak RIGHT of green (prominence, not colour)
        right = [(i, pr) for i, pr in peaks if i > green]
        if right:
            result[Name.EUROPIUM_VIVID_GAMBOGE] = line(int(max(right, key=lambda t: t[1])[0]),
                                                        Name.EUROPIUM_VIVID_GAMBOGE)

        # violet + blue — blue-dominant peaks LEFT of green -> cluster -> leftmost=violet, next=blue
        blueIdx = [i for i, _ in peaks if i < green and util.channelDominance(colourOf(i), "blue") > self.MIN_CHANNEL]
        clusters = self.__cluster(blueIdx, intensities)
        blueNames = [Name.MERCURY_FRENCH_VIOLET, Name.MERCURY_BLUE] if len(clusters) >= 2 else [Name.MERCURY_BLUE]
        for name, i in zip(blueNames, clusters):
            result[name] = line(i, name)

        aqua = self.__pickColour(peaks, colourOf, refColour[Name.TERBIUM_AQUA], "cyan", util, hi=green)
        if aqua is not None:
            result[Name.TERBIUM_AQUA] = line(aqua, Name.TERBIUM_AQUA)

        greenLeft = self.__pickColour(peaks, colourOf, refColour[Name.MERCURY_MANGO_GREEN_LEFT], "green", util,
                                      lo=green - self.DOUBLET_LEFT, hi=green - self.DOUBLET_RIGHT)
        if greenLeft is not None:
            result[Name.MERCURY_MANGO_GREEN_LEFT] = line(greenLeft, Name.MERCURY_MANGO_GREEN_LEFT)
        return result

    def __pickColour(self, peaks, colourOf, refColour, kind, util, lo=None, hi=None):
        # gate by channel dominance (robust), rank by channel-strength × prominence
        best = None
        for i, prom in peaks:
            if (lo is not None and i <= lo) or (hi is not None and i >= hi):
                continue
            channel = util.channelDominance(colourOf(i), kind)
            if channel < self.MIN_CHANNEL:
                continue
            score = channel * prom
            if best is None or score > best[0]:
                best = (score, i)
        return best[1] if best is not None else None

    def __cluster(self, indices, intensities):
        indices = sorted(indices)
        if not indices:
            return []
        groups, current = [], [indices[0]]
        for i in indices[1:]:
            if i - current[-1] <= self.CLUSTER_GAP:
                current.append(i)
            else:
                groups.append(current); current = [i]
        groups.append(current)
        reps = []
        for group in groups:
            group_proms = peak_prominences(intensities, np.array(group))[0]
            reps.append(int(group[int(np.argmax(group_proms))]))
        return sorted(reps)
