"""Does M448's separation lean on a line drawn where nothing was measured?  (Edwin 2026-08-10)

THE QUESTION. The shipped numerator subtracts `line(454)`, a value the fitted baseline predicts **76 nm to
the left of the nearest anchor** — pure extrapolation. And it is not an innocent one: the far anchor that
sets the line's slope is PIGMENT, not background (§16.12.12 measured the 620-630 rise tracking oil class at
5.1 sigma), so `line(454) = 1.8*A_near - 0.8*A_far` hands an oil with more red pigment a SMALLER subtraction
in the blue. Green oils get credited for their red band twice: once in the denominator, once here.

⇒ If the discrimination survives without that extrapolation, it was never leaning on it and we can say so.
If it collapses, the metric's separating power partly rests on a background model outside its own data.

THE VARIANTS. Denominator identical everywhere it can be (the Q band lies BETWEEN the anchors, so its
correction is interpolation — defensible on any background model):

  shipped        B_S = A_S - line(S)        B_Q = A_Q - line(Q)      the tilted line, both bands
  flat numerator B_S = A_S - A_near         B_Q = A_Q - line(Q)      <- THE TEST: no extrapolation
  flat both      B_S = A_S - A_near         B_Q = A_Q - A_near       no tilt anywhere
  raw            B_S = A_S                  B_Q = A_Q                no background model at all

WHAT IS SCORED. The same three axes §7.13 used to justify the 448 trim, so the numbers are comparable:
class separation (green vs brown), the harder within-green task, and dilution spread (the same oil at two
strengths, where a good metric should not move).

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/soret_extrapolation_test.py
"""
import numpy as np

from settling_sweep import BASE, despikedAbsorption, asArrays, plugin, feature

SORET = (448.0, 460.0)              # explicit, never the live constant (§18 duck #14)
Q_BAND = (560.0, 580.0)
NEAR, FAR = (520.0, 540.0), (620.0, 630.0)

# §16.20.4's derivation corpus + the fills that make the other two axes measurable.
SETS = [("20270729B", "Steirerkraft B", "green", 6),
        ("20270729C", "Steirerkraft C", "green", 6),
        ("20260731A", "S-Budget D", "brown", 6),
        ("20260801A", "Kiendler A", "green2", 6),
        ("20260801B", "Kiendler B", "green2", 2),
        ("20260801C", "Kiendler C", "green2", 2),
        ("20260804A", "Steirerkraft half-strength", "dilute", 6)]


def bands(path):
    """(A_S, A_Q, A_near, A_far, line(S), line(Q)) for one run — every variant is built from these six."""
    despiked = despikedAbsorption(path)
    corrected = feature.linearBaselineCorrected(despiked, (NEAR, FAR))
    lam, raw = asArrays(despiked)
    _, cor = asArrays(corrected)

    def band(values, window):
        return float(values[(lam >= window[0]) & (lam <= window[1])].mean())

    # the fitted line, read where it matters: raw minus corrected IS the line, pointwise
    line = raw - cor
    return (band(raw, SORET), band(raw, Q_BAND), band(raw, NEAR), band(raw, FAR),
            band(line, SORET), band(line, Q_BAND))


def variants(values):
    aSoret, aQ, aNear, _aFar, lineS, lineQ = values
    return {"shipped": (aSoret - lineS) / (aQ - lineQ),
            "flat numerator": (aSoret - aNear) / (aQ - lineQ),
            "flat both": (aSoret - aNear) / (aQ - aNear),
            "raw": aSoret / aQ}


def cohensD(a, b):
    a, b = np.array(a), np.array(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled


def main():
    print("Soret %s   Q %s   anchors %s / %s\n" % (SORET, Q_BAND, NEAR, FAR))
    scores = {}
    for folder, label, klass, count in SETS:
        for index in range(1, count + 1):
            for name, value in variants(bands("%s/%03d.pdf" % (folder, index))).items():
                scores.setdefault(name, {}).setdefault(klass, []).append(value)
                scores[name].setdefault("by fill", {}).setdefault(label, []).append(value)

    print("%-16s %19s %19s %8s | %8s | %9s" % (
        "variant", "green (n=12)", "brown (n=6)", "class d", "green-green d", "dilution"))
    print("-" * 92)
    for name in ("shipped", "flat numerator", "flat both", "raw"):
        s = scores[name]
        green, brown, green2 = np.array(s["green"]), np.array(s["brown"]), np.array(s["green2"])
        strong = np.array(s["by fill"]["Steirerkraft B"] + s["by fill"]["Steirerkraft C"])
        weak = np.array(s["dilute"])
        print("%-16s %9.3f +/- %-6.3f %9.3f +/- %-6.3f %8.2f | %13.2f | %+8.1f%%" % (
            name, green.mean(), green.std(ddof=1), brown.mean(), brown.std(ddof=1),
            cohensD(green, brown), cohensD(green, green2),
            100 * (weak.mean() - strong.mean()) / strong.mean()))

    print("\nRELATIVE to the shipped construction (what dropping the extrapolation costs):")
    reference = scores["shipped"]
    baseD = cohensD(reference["green"], reference["brown"])
    baseWithin = cohensD(reference["green"], reference["green2"])
    for name in ("flat numerator", "flat both", "raw"):
        s = scores[name]
        d = cohensD(s["green"], s["brown"])
        within = cohensD(s["green"], s["green2"])
        print("   %-16s class d %+6.1f %%   within-green d %+6.1f %%" % (
            name, 100 * (d - baseD) / baseD, 100 * (within - baseWithin) / baseWithin))

    print("\nCORRIDOR (min green .. max brown) — does a threshold still have room?")
    for name in ("shipped", "flat numerator", "flat both", "raw"):
        s = scores[name]
        low, high = min(s["green"]), max(s["brown"])
        print("   %-16s green min %7.3f   brown max %7.3f   %s" % (
            name, low, high, ("gap %.3f (%.0f %% of the green mean)"
                              % (low - high, 100 * (low - high) / np.mean(s["green"])))
            if low > high else "⛔ CLASSES OVERLAP"))


if __name__ == "__main__":
    main()
