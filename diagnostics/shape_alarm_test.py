"""Edwin's acceptance test for the history tracker, run literally.
   (`SPEC_history_tracker.md` §8 — the entry gate)

    "Take run 001 of Ja! Natürlich as the reference shape. Compare S-Budget -> the tracker must say
     SOMETHING CHANGED. Compare Ja! Natürlich runs 002 and 003 -> the alarm must stay silent."

One reference RUN, not a template, because that is the stated setup: the first press is the
reference. So this is the k = 1 case — no model of natural variation, every deviation is residual,
and `D = sqrt(1 - r^2)` is the whole statistic (§3.4: D is the normalised SPE of a one-component
model whose single component is the reference spectrum).

Generalised past Ja! Natürlich: EVERY run takes its turn as the reference, and the test is

    max D(reference, own other runs)   <   min D(reference, any other oil's runs)

i.e. is there a silent zone holding all of the reference's own re-measurements and none of anyone
else's? The MARGIN between those two is what a control limit has to fit inside.

⚠ This is the EASY case. Telling two different products apart is a large change; "same seed bag,
second press" is a small one. Passing here is necessary, nowhere near sufficient (§8.2).

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_alarm_test.py
"""
import numpy as np

from shape_similarity import FILLS, shape, dissimilarity

REFERENCE_OIL = "Ja! Natürlich"


def literalTest(window):
    print("=" * 96)
    print("EDWIN'S TEST, LITERALLY: reference = %s run 001   (window %g-%g nm)"
          % (REFERENCE_OIL, window[0], window[1]))
    print("=" * 96)
    curves = {name: [shape(p, window) for p in paths] for name, paths in FILLS}
    reference = curves[REFERENCE_OIL][0]
    print("   %-20s %6s %12s   %s" % ("compared against", "run", "D %", "expected"))
    for name, _ in FILLS:
        for i, vector in enumerate(curves[name], start=1):
            if name == REFERENCE_OIL and i == 1:
                continue
            print("   %-20s %6d %11.2f%%   %s" % (name, i, dissimilarity(reference, vector),
                                                  "SILENT" if name == REFERENCE_OIL else "ALARM"))
    print()


def everyRunAsReference(window):
    print("=" * 96)
    print("GENERALISED: every run takes its turn as the reference   (window %g-%g nm)" % window)
    print("=" * 96)
    curves = {name: [shape(p, window) for p in paths] for name, paths in FILLS}
    print("   %-20s %10s   %-22s %10s   %-22s %8s" %
          ("reference run", "max D own", "worst own run", "min D other", "nearest stranger",
           "margin"))
    passes = total = 0
    for name, vectors in curves.items():
        for i, reference in enumerate(vectors, start=1):
            own = [(dissimilarity(reference, v), "run %03d" % j)
                   for j, v in enumerate(vectors, start=1) if j != i]
            other = [(dissimilarity(reference, v), "%s %03d" % (o, j))
                     for o, vs in curves.items() if o != name
                     for j, v in enumerate(vs, start=1)]
            worstOwn, ownLabel = max(own)
            nearestOther, otherLabel = min(other)
            total += 1
            passes += worstOwn < nearestOther
            print("   %-20s %9.2f%%   %-22s %9.2f%%   %-22s %7.2f%% %s" %
                  ("%s %03d" % (name, i), worstOwn, ownLabel, nearestOther, otherLabel,
                   nearestOther - worstOwn, "OK" if worstOwn < nearestOther else "<-- FAILS"))
    print("\n   %d / %d reference runs give a clean silent zone" % (passes, total))
    print()


def residualExample(window):
    """The RESIDUAL CURVE: a value per wavelength, not one number (§3.3)."""
    print("=" * 96)
    print("THE RESIDUAL CURVE — reference %s 001, sampled every 5 nm   (%g-%g nm)"
          % (REFERENCE_OIL, window[0], window[1]))
    print("=" * 96)
    grid = np.arange(window[0], window[1] + .01, 0.5)
    reference = shape("20260812BillJaNatuerlich/001.pdf", window)
    cases = [("Ja! Natürlich 002 (silent)", "20260812BillJaNatuerlich/002.pdf"),
             ("Spar S-Budget 001 (alarm)", "20260807B/001.pdf")]
    print("   %-28s %s" % ("nm", "".join("%7.0f" % x for x in grid[::10])))
    for label, path in cases:
        other = shape(path, window)
        scale = float(np.dot(other, reference) / np.dot(reference, reference))
        residual = other - scale * reference
        print("   %-28s %s" % (label, "".join("%7.2f" % x for x in residual[::10])))
    print("\n   The alarm row's SHAPE is the diagnosis — where it departs from zero names the change.")
    print()


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    literalTest((560.0, 580.0))
    everyRunAsReference((560.0, 580.0))
    literalTest((550.0, 600.0))
    everyRunAsReference((550.0, 600.0))
    residualExample((550.0, 600.0))


if __name__ == "__main__":
    main()
