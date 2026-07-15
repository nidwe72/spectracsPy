#!/usr/bin/env python3
"""Offscreen unit test for the robust reduction estimators (SPEC_capture_quality.md §6, Topic 2/M2):
the SPATIAL Tukey-per-column (kills a fixed-location hot pixel) and the TEMPORAL sigma-clipped mean (kills a
transient glitch frame), plus the degenerate-input guards. Pure numpy — no rig, no Qt."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
import numpy as np
from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule

R = RobustReductionLogicModule()
checks = []


def check(name, ok, detail=""):
    checks.append((name, ok, detail))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  " + detail) if detail else ""))


# ---- SPATIAL: Tukey biweight per column ----
# A clean column ~ its true value; a column with ONE hot pixel (rest ~100) must NOT be dragged up by it.
rows, cols = 60, 4
band = np.full((rows, cols), 100.0)
band += np.random.default_rng(0).normal(0, 2, size=(rows, cols))  # mild noise (seed via default_rng, allowed)
band[10, 1] = 255.0   # a hot pixel in column 1 (would be masked as saturated by the caller normally)
band[20, 2] = 5.0     # a cold outlier in column 2
tuk = R.tukeyBiweightPerColumn(band)
plain = np.nanmean(band, axis=0)
check("tukey clean column ~100", abs(tuk[0] - 100) < 3, "got %.1f" % tuk[0])
check("tukey rejects hot pixel", abs(tuk[1] - 100) < 3 and tuk[1] < plain[1], "tukey=%.1f plainmean=%.1f" % (tuk[1], plain[1]))
check("tukey rejects cold outlier", abs(tuk[2] - 100) < 3, "got %.1f" % tuk[2])

# constant column (MAD==0) -> its median; all-NaN column -> NaN (caller supplies fallback)
degen = np.full((rows, cols), np.nan)
degen[:, 0] = 42.0                     # constant
degen[:, 1] = np.nan                   # all masked
d = R.tukeyBiweightPerColumn(degen)
check("tukey constant column -> median", abs(d[0] - 42.0) < 1e-9, "got %.3f" % d[0])
check("tukey all-NaN column -> NaN", np.isnan(d[1]))

# ---- TEMPORAL: sigma-clipped mean per bin ----
# 50 frames ~ true per-bin value; one GLITCH frame spikes bin 1; the clip must reject it.
frames, bins = 50, 3
rng = np.random.default_rng(1)
stack = np.tile(np.array([10.0, 50.0, 200.0]), (frames, 1)) + rng.normal(0, 1, size=(frames, bins))
stack[7, 1] = 500.0    # glitch frame, bin 1
sig = R.sigmaClippedMean(stack)
plainT = np.mean(stack, axis=0)
check("sigma-clip clean bin ~10", abs(sig[0] - 10) < 1.0, "got %.2f" % sig[0])
check("sigma-clip rejects glitch frame", abs(sig[1] - 50) < 1.0 and sig[1] < plainT[1], "clip=%.2f plainmean=%.2f" % (sig[1], plainT[1]))

# N<expected: drop some frames to NaN in a bin -> still averages survivors
stack2 = stack.copy()
stack2[:20, 2] = np.nan
sig2 = R.sigmaClippedMean(stack2)
check("sigma-clip tolerates dropped frames (N<expected)", abs(sig2[2] - 200) < 1.0, "got %.2f" % sig2[2])

# constant bin (sigma==0) -> unchanged, nothing clipped; all-NaN bin -> 0
const = np.full((frames, bins), np.nan)
const[:, 0] = 77.0
c = R.sigmaClippedMean(const)
check("sigma-clip constant bin -> value", abs(c[0] - 77.0) < 1e-9, "got %.3f" % c[0])
check("sigma-clip all-NaN bin -> 0", abs(c[1] - 0.0) < 1e-9, "got %.3f" % c[1])

allok = all(ok for _, ok, _ in checks)
print("RESULT:", "ALL PASS ✔" if allok else "FAIL ✗")
sys.exit(0 if allok else 1)
