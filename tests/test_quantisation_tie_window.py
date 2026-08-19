"""§16.12.17 — the MAD==0 collapse, and the tie-window that fixes it.

⛔⛔ THE BUG THIS PINS. `tukeyBiweightPerColumn` guarded its scale with `moving = mad > 0`, commented
"constant columns keep their median". But **MAD == 0 does not mean the column is constant — it means more
than half the rows share the median**, which below DN ~60 is the ordinary case, not a degenerate one. Such
a column returned ONE EXACT 8-BIT CODE, and everything the minority rows knew was discarded.

⭐ MEASURED ON A LIVE FRAME (2026-08-19, 291 rows per column): 35 % of all columns collapsed this way —
44-47 % below DN 30 and **0 % above DN 60**, which is exactly the boundary between a smooth blue end and a
staircase through 500-630 nm. In the collapsed columns the plain mean sat a median of **0.45 DN** from the
median that was returned instead.

⚠ AND WHY IT IS NOT A PLAIN MEAN. With 291 rows one hot pixel at 255 against a median of 12 moves a plain
mean by 0.84 DN — LARGER than the ~0.45 DN of real signal being recovered. The window is the whole point.
"""
import numpy as np
import pytest

from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule

GAMMA = 2.2
decode = lambda code: 255.0 * (code / 255.0) ** GAMMA
encode = lambda linear: 255.0 * (linear / 255.0) ** (1.0 / GAMMA)
window = lambda code: 1.5 * (decode(code + 1) - decode(code))


def column(*runs):
    """A column built from (code, count) pairs, in the LINEAR units the reduction actually sees."""
    values = []
    for code, count in runs:
        values.extend([decode(code)] * count)
    return np.array(values).reshape(-1, 1)


def test_a_tied_column_used_to_collapse_to_one_integer_code():
    """The defect itself, pinned so it cannot come back silently."""
    band = column((12, 175), (13, 115))                      # 60 % share the median -> MAD == 0
    collapsed = RobustReductionLogicModule().tukeyBiweightPerColumn(band)[0]
    assert encode(collapsed) == pytest.approx(12.0, abs=1e-9), \
        "without a tie window the column must still return the bare median — that is the documented old path"


def test_the_tie_window_recovers_the_dither_the_median_discarded():
    band = column((12, 175), (13, 115))
    reduced = RobustReductionLogicModule().tukeyBiweightPerColumn(band, tieWindow=np.array([window(12)]))[0]
    truth = (175 * 12 + 115 * 13) / 290.0
    assert encode(reduced) == pytest.approx(truth, abs=0.02), \
        "the fallback must average the tied rows, not return one of them"
    # ...and that is a real gain, not a rounding artefact
    assert abs(encode(reduced) - 12.0) > 0.3


def test_a_hot_pixel_cannot_pull_the_fallback():
    """⛔ The reason this is a WINDOWED mean. A plain mean over 291 rows would land near code 19."""
    band = column((12, 175), (13, 115), (200, 1))
    reduced = RobustReductionLogicModule().tukeyBiweightPerColumn(band, tieWindow=np.array([window(12)]))[0]
    assert encode(reduced) == pytest.approx((175 * 12 + 115 * 13) / 290.0, abs=0.02)
    assert encode(np.mean(band)) > 18.0, "the naive alternative really is that bad — keep the window"


def test_a_genuinely_constant_column_is_unchanged():
    """⚠ The fallback may never make a column worse than the median it replaces."""
    band = column((12, 291))
    for tie in (None, np.array([window(12)])):
        reduced = RobustReductionLogicModule().tukeyBiweightPerColumn(band, tieWindow=tie)[0]
        assert reduced == pytest.approx(decode(12), abs=1e-12)


def test_a_column_the_biweight_can_still_scale_is_untouched():
    """⭐ The fix is LOCAL to the MAD==0 branch — a normal column must take the identical old path."""
    values = decode(60) + np.linspace(-4.0, 4.0, 291)
    band = values.reshape(-1, 1)
    module = RobustReductionLogicModule()
    assert module.tukeyBiweightPerColumn(band)[0] == pytest.approx(
        module.tukeyBiweightPerColumn(band, tieWindow=np.array([window(60)]))[0], abs=1e-12)


def test_an_all_masked_column_still_returns_nan():
    band = np.full((291, 1), np.nan)
    for tie in (None, np.array([window(12)])):
        assert np.isnan(RobustReductionLogicModule().tukeyBiweightPerColumn(band, tieWindow=tie)[0])


def test_the_window_is_level_dependent_because_one_code_is_not_a_fixed_step():
    """⚠ One code is ~14 % of the level at DN 16 and ~1 % at DN 200 — a single constant would be wrong
    nearly everywhere, which is why the caller computes it per column."""
    assert window(16) < window(200)
    assert window(200) / window(16) > 3.0
