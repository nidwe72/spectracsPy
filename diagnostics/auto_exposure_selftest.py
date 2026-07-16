"""Offscreen self-test of the direction-agnostic AutoExposureLogicModule: synthetic measure() curves for a
NORMAL camera, an INVERTED camera (ELP), and a CLAMPED-plateau camera. Asserts the chosen exposure lands the
peak brightness at or just below the target (235) and never on a clipping exposure when a non-clipping one exists."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
from sciens.spectracs.logic.application.video.capture.AutoExposureLogicModule import AutoExposureLogicModule

TARGET = 235
MIN, MAX = 1, 500

def clamp255(v):
    return max(0.0, min(255.0, v))

# brightness models: brightness as a function of exposure value (peak channel percentile, 0..255)
def normal(e):        # brighter with higher value; clips past ~300
    return clamp255(e * 0.9)
def inverted(e):      # ELP: brighter at LOW value, dimmer at high value
    return clamp255((MAX - e) * 0.85)
def clamped(e):       # rises then plateaus (control saturates above ~120)
    return clamp255(min(e, 120) * 2.2)
def dim(e):           # underexposed everywhere (never reaches target)
    return clamp255(e * 0.15)

def run(name, model):
    calls = {"n": 0}
    def measure(e):
        calls["n"] += 1
        return model(e)
    chosen = AutoExposureLogicModule().findExposure(measure, MIN, MAX, target=TARGET, iterations=8)
    peak = model(chosen)
    # is there ANY exposure that stays below target? then chosen must too (not clip)
    grid = [model(e) for e in range(MIN, MAX + 1)]
    exists_below = any(b <= TARGET for b in grid)
    best_possible = max([b for b in grid if b <= TARGET], default=None)
    ok_noclip = (peak <= TARGET) if exists_below else True
    # chosen should be reasonably close to the best achievable below-target peak
    near_best = (best_possible is None) or (best_possible - peak <= 30)
    status = "PASS" if (ok_noclip and near_best) else "FAIL"
    print("  [%s] %-9s chosen_exp=%3d peak=%6.1f (best<=target=%s) probes=%d"
          % (status, name, chosen, peak, ("%.1f" % best_possible) if best_possible else "n/a", calls["n"]))
    return ok_noclip and near_best

allok = True
print("direction-agnostic auto-exposure self-test (target=%d, range=%d..%d):" % (TARGET, MIN, MAX))
for name, model in (("normal", normal), ("inverted", inverted), ("clamped", clamped), ("dim", dim)):
    allok &= run(name, model)
print("RESULT:", "ALL PASS ✔" if allok else "FAIL ✗")
sys.exit(0 if allok else 1)
