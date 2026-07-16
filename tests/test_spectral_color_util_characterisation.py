"""
CHARACTERISATION tests for SpectralColorUtil (SPEC_project_structure.md phase S1a / §4d).

These pin the CURRENT, QColor-based behaviour so that S1b -- which replaces QColor with a Qt-free
SpectralColor -- can be proven behaviour-preserving instead of hoped to be.

Why this file exists: `hueSimilarity` and `channelDominance` are how emission lines are identified
during WAVELENGTH CALIBRATION (WavelengthLineDetectionLogicModule, SpectralLinesSelectionLogicModule).
Calibration is the foundation under every measurement, and calibration errors are SILENT -- a
slightly-off pixel->nm map poisons everything downstream without raising anything. Before S1a these
three functions had ZERO test coverage.

They are characterisation tests, not specification tests: the expected values were READ OUT of the
current implementation (and sanity-checked -- 440nm is pure blue, 490 cyan, 510 green, 580 yellow,
645 red, and the 380/780 ends dim via the vision-limit falloff). They assert "still the same", not
"correct in principle". If a change here fails, that is the point -- decide deliberately, don't
re-bless the numbers.

VERIFIED BY MUTATION (2026-07-17). A characterisation test that cannot fail is decoration, so each
mutant below was applied to SpectralColorUtil in turn and the suite re-run; every one is caught:

    achromatic hue -1 -> 0.0 (the naive S1b port)   2 failed
    gamma 0.80 -> 0.85                             11 failed
    drop channelDominance' max(0, ..) clamp        10 failed
    saturation gate 0.12 -> 0.05                    1 failed
    value gate 0.10 -> 0.02                         1 failed
    cosine -> linear hue distance                   2 failed
    drop the `h1 < 0 or h2 < 0` guard               2 failed
    max_intensity 255 -> 250                       21 failed

The first sweep wrongly reported the two gate mutants as SURVIVING -- the gate tests used colours far
from the threshold, so they proved only that *a* gate existed, not where. The boundary-straddling
tests below were added for exactly that. (Run mutations with `python -B` and purge __pycache__: a
stale .pyc from a previous mutant will silently poison the result -- it did.)

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_spectral_color_util_characterisation.py -q
"""
import math

import pytest
from PySide6.QtGui import QColor

from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


GREY = QColor.fromRgb(128, 128, 128)


def util():
    return SpectralColorUtil()


# --- wavelengthToColor --------------------------------------------------------
# Golden RGB per wavelength. Spot-checks of the recognisable anchors plus the two
# vision-limit ends, where `factor` dims the result (380/780 -> 0.3 gamma-adjusted).

WAVELENGTH_TO_RGB = [
    (380, (97, 0, 97)),      # violet, dimmed by the <420 falloff
    (400, (131, 0, 181)),
    (420, (106, 0, 255)),
    (430, (61, 0, 255)),     # the Soret peak's nominal position
    (440, (0, 0, 255)),      # pure blue
    (450, (0, 70, 255)),     # PB's blue window starts here-ish
    (460, (0, 123, 255)),
    (490, (0, 255, 255)),    # cyan
    (510, (0, 255, 0)),      # pure green
    (540, (129, 255, 0)),
    (570, (225, 255, 0)),    # PB's green Q-band centre
    (580, (255, 255, 0)),    # yellow
    (600, (255, 190, 0)),
    (645, (255, 0, 0)),      # pure red -- and every longer nm stays pure red
    (700, (255, 0, 0)),
    (780, (97, 0, 0)),       # dimmed by the >700 falloff
]


@pytest.mark.parametrize("nanometer,expectedRgb", WAVELENGTH_TO_RGB)
def test_wavelength_to_color_is_unchanged(nanometer, expectedRgb):
    color = util().wavelengthToColor(nanometer)
    assert (color.red(), color.green(), color.blue()) == expectedRgb


def test_wavelength_to_color_is_fully_saturated_across_the_range():
    # Spectral colours are pure hues: saturation is 1.0 everywhere, only VALUE falls off at the ends.
    # hueSimilarity gates on saturation >= 0.12, so this is what keeps wavelengthToColor's own output
    # usable as a reference colour.
    for nanometer in range(380, 781, 5):
        assert util().wavelengthToColor(nanometer).saturationF() == pytest.approx(1.0)


def test_wavelength_to_color_dims_at_the_vision_limits_only():
    subject = util()
    assert subject.wavelengthToColor(380).valueF() == pytest.approx(0.380, abs=1e-3)
    assert subject.wavelengthToColor(780).valueF() == pytest.approx(0.380, abs=1e-3)
    for nanometer in (420, 510, 645, 700):
        assert subject.wavelengthToColor(nanometer).valueF() == pytest.approx(1.0)


@pytest.mark.parametrize("nanometer", [379, 781, 0, -1, 1000])
def test_wavelength_to_color_rejects_out_of_range(nanometer):
    with pytest.raises(ValueError):
        util().wavelengthToColor(nanometer)


@pytest.mark.parametrize("nanometer", [380, 780])
def test_wavelength_to_color_accepts_the_inclusive_bounds(nanometer):
    assert util().wavelengthToColor(nanometer) is not None


# --- hueSimilarity ------------------------------------------------------------
# Saturation-weighted cosine closeness of hue. 1.0 = same hue & fully saturated;
# 0.0 when achromatic or >= 90 degrees away.

def test_hue_similarity_of_a_colour_with_itself_is_one():
    green = util().wavelengthToColor(510)
    assert util().hueSimilarity(green, green) == pytest.approx(1.0)


def test_hue_similarity_60_degrees_apart_is_cos_60():
    # green (hueF 1/3) vs cyan (hueF 1/2) = 60 degrees -> cos(60) = 0.5, weighted by saturation 1.0
    subject = util()
    assert subject.hueSimilarity(subject.wavelengthToColor(510),
                                 subject.wavelengthToColor(490)) == pytest.approx(0.5, abs=1e-6)


def test_hue_similarity_is_zero_at_or_beyond_90_degrees():
    # green vs blue = 120 degrees -> cos is negative -> clamped to 0.0, never negative
    subject = util()
    assert subject.hueSimilarity(subject.wavelengthToColor(510),
                                 subject.wavelengthToColor(440)) == 0.0


def test_hue_similarity_is_symmetric():
    subject = util()
    green, cyan = subject.wavelengthToColor(510), subject.wavelengthToColor(490)
    assert subject.hueSimilarity(green, cyan) == pytest.approx(subject.hueSimilarity(cyan, green))


def test_hue_similarity_wraps_around_the_hue_circle():
    # Hue is circular: a pair straddling the 0/1 seam must score on the SHORT way round, because
    # cos() is even and 360-periodic. Guards against a port that subtracts hues linearly.
    subject = util()
    nearRed = QColor.fromHsvF(0.97, 1.0, 1.0)   # just below the seam
    red = QColor.fromHsvF(0.0, 1.0, 1.0)        # on it -- true distance is 0.03 (10.8 deg), not 0.97
    assert subject.hueSimilarity(nearRed, red) == pytest.approx(math.cos(math.radians(10.8)), abs=1e-6)


@pytest.mark.parametrize("colour,reference", [
    (None, QColor.fromRgb(0, 255, 0)),
    (QColor.fromRgb(0, 255, 0), None),
    (None, None),
])
def test_hue_similarity_of_none_is_zero(colour, reference):
    assert util().hueSimilarity(colour, reference) == 0.0


def test_hue_similarity_gates_on_low_value():
    # near-black: valueF < 0.10 -> 0.0, before hue is consulted at all
    subject = util()
    assert subject.hueSimilarity(QColor.fromRgb(5, 5, 5), subject.wavelengthToColor(510)) == 0.0


def test_hue_similarity_gates_on_low_saturation():
    # washed-out: saturationF < 0.12 -> 0.0. This gate is what makes an ACHROMATIC *colour* safe
    # (its hue is never read), which is why only the *reference* needs the hue<0 branch below.
    subject = util()
    assert subject.hueSimilarity(QColor.fromRgb(200, 210, 200), subject.wavelengthToColor(510)) == 0.0


# --- the gate THRESHOLDS, pinned at the boundary ------------------------------
# The two tests above only prove *a* gate exists somewhere -- they pass for any threshold, because
# their colours sit far from it. Mutation testing (2026-07-17) confirmed exactly that: moving the
# saturation gate 0.12 -> 0.05 and the value gate 0.10 -> 0.02 left the whole suite green. These
# straddle each boundary so the numbers themselves are pinned.

def test_hue_similarity_saturation_gate_sits_at_0_12():
    subject = util()
    green = subject.wavelengthToColor(510)
    justBelow = QColor.fromHsvF(1 / 3, 0.115, 1.0)
    justAbove = QColor.fromHsvF(1 / 3, 0.125, 1.0)
    assert justBelow.saturationF() < 0.12 <= justAbove.saturationF(), "precondition: colours straddle the gate"
    assert subject.hueSimilarity(justBelow, green) == 0.0
    # same hue as the reference -> cos = 1 -> the result IS the saturation
    assert subject.hueSimilarity(justAbove, green) == pytest.approx(justAbove.saturationF(), abs=1e-6)


def test_hue_similarity_value_gate_sits_at_0_10():
    subject = util()
    green = subject.wavelengthToColor(510)
    justBelow = QColor.fromHsvF(1 / 3, 1.0, 0.09)
    justAbove = QColor.fromHsvF(1 / 3, 1.0, 0.11)
    assert justBelow.valueF() < 0.10 <= justAbove.valueF(), "precondition: colours straddle the gate"
    assert subject.hueSimilarity(justBelow, green) == 0.0
    # fully saturated and same hue -> 1.0, dim but not gated
    assert subject.hueSimilarity(justAbove, green) == pytest.approx(1.0)


# --- hueSimilarity: THE ACHROMATIC TRAP ---------------------------------------
# ** The single most important thing in this file. **
#
# QColor.hueF() returns -1.0 for an achromatic colour; colorsys (the obvious S1b replacement)
# returns 0.0 -- which is indistinguishable from RED. hueSimilarity branches on `if h1 < 0 or
# h2 < 0: return 0.0`, and ONLY the reference side needs it: an achromatic *colour* is already
# stopped by the saturation gate, but the *reference* is not gated at all.
#
# Port this naively and a GREY REFERENCE scores 1.0 -- a perfect match -- against a RED pixel.
# Verified 2026-07-17: current 0.0, naive-port 1.0. That is a silently mis-identified emission
# line during wavelength calibration.

def test_qcolor_returns_minus_one_hue_for_achromatic_colours():
    # Pins the upstream convention S1b's SpectralColor must reproduce. If this ever fails, Qt changed
    # under us and the assumption below needs re-deriving.
    for achromatic in (GREY, QColor.fromRgb(255, 255, 255), QColor.fromRgb(0, 0, 0)):
        assert achromatic.hueF() == -1.0
        assert achromatic.saturationF() == 0.0


def test_hue_similarity_of_grey_reference_against_red_is_zero_not_one():
    # THE regression guard for S1b. Red's hue is 0.0; a naive achromatic hue of 0.0 collides with it
    # exactly, so the two become "identical hues" and score 1.0.
    subject = util()
    red = subject.wavelengthToColor(645)
    assert red.hueF() == 0.0, "precondition: red sits at hue 0.0, where a naive achromatic hue lands"
    assert subject.hueSimilarity(red, GREY) == 0.0


def test_hue_similarity_of_grey_reference_is_zero_for_every_hue():
    # A grey reference is meaningless for every colour, not just red.
    subject = util()
    for nanometer in (440, 490, 510, 580, 645):
        assert subject.hueSimilarity(subject.wavelengthToColor(nanometer), GREY) == 0.0


def test_hue_similarity_of_grey_colour_is_zero():
    # The other direction: an achromatic colour never matches anything (via the saturation gate).
    subject = util()
    assert subject.hueSimilarity(GREY, subject.wavelengthToColor(510)) == 0.0


# --- channelDominance ---------------------------------------------------------
# Per-channel ratio that still discriminates at LOW saturation (where hue is unreliable),
# so it is the robust colour SELECTOR. Normalised to [0, 1].

@pytest.mark.parametrize("nanometer,kind", [(510, "green"), (440, "blue"), (490, "cyan"), (645, "red")])
def test_channel_dominance_is_one_for_its_own_pure_colour(nanometer, kind):
    subject = util()
    assert subject.channelDominance(subject.wavelengthToColor(nanometer), kind) == pytest.approx(1.0)


@pytest.mark.parametrize("nanometer,kind", [
    (510, "blue"), (510, "cyan"), (510, "red"),
    (440, "green"), (440, "cyan"), (440, "red"),
    (490, "green"), (490, "blue"), (490, "red"),
    (645, "green"), (645, "blue"), (645, "cyan"),
])
def test_channel_dominance_is_zero_for_the_other_kinds(nanometer, kind):
    subject = util()
    assert subject.channelDominance(subject.wavelengthToColor(nanometer), kind) == 0.0


def test_channel_dominance_is_never_negative():
    # The max(0, ...) clamp: blue-dominance of a red pixel is a large negative before clamping.
    subject = util()
    for kind in ("green", "blue", "cyan", "red"):
        for nanometer in range(400, 701, 25):
            assert subject.channelDominance(subject.wavelengthToColor(nanometer), kind) >= 0.0


def test_channel_dominance_of_grey_is_zero_for_every_kind():
    subject = util()
    for kind in ("green", "blue", "cyan", "red"):
        assert subject.channelDominance(GREY, kind) == 0.0


def test_channel_dominance_formula_is_a_normalised_channel_margin():
    # Pins the actual arithmetic, not just the pure-colour corners: value = (channel - max(others)) / 255.
    subject = util()
    colour = QColor.fromRgb(10, 200, 60)
    assert subject.channelDominance(colour, "green") == pytest.approx((200 - 60) / 255.0)
    assert subject.channelDominance(colour, "cyan") == pytest.approx((min(200, 60) - 10) / 255.0)
    assert subject.channelDominance(colour, "red") == 0.0


def test_channel_dominance_of_unknown_kind_is_zero():
    assert util().channelDominance(util().wavelengthToColor(510), "magenta") == 0.0


def test_channel_dominance_of_none_is_zero():
    assert util().channelDominance(None, "green") == 0.0


def test_channel_dominance_still_discriminates_at_low_saturation():
    # Its whole reason to exist: hueSimilarity gates this colour out (saturation < 0.12), yet
    # channelDominance still reports a usable green margin. Guards the division of labour.
    subject = util()
    barelyGreen = QColor.fromRgb(200, 210, 200)
    assert barelyGreen.saturationF() < 0.12
    assert subject.hueSimilarity(barelyGreen, subject.wavelengthToColor(510)) == 0.0
    assert subject.channelDominance(barelyGreen, "green") == pytest.approx(10 / 255.0)
