"""Edwin's THREE-TIER alarm on the shape distance. (`SPEC_history_tracker.md` §8.3)

    Edwin 2026-08-14, from `oil_shape_panel.png`: "I think we have three groups per shape.
      group A: the Ja! Natürlich runs
      group B: Spar Premium and Steirerkraft g.g.A.
      group C: Spar S-Budget, Billa Clever and Spar Steirisches g.g.A.
    We take Ja! Natürlich run 001 as the reference shape. If a subsequent measurement is JN 002 or
    003 the alarm is SILENT; if it is Spar Premium or Steirerkraft it says PROBABLY MINOR
    DIFFERENCE; if it is S-Budget or Billa Clever it says PROBABLY MAJOR DIFFERENCE."

Two thresholds on `D` implement that: `T1` between silent and minor, `T2` between minor and major.

⛔⛔ READ THIS BEFORE QUOTING ANY NUMBER BELOW. The window was CHOSEN by scanning 105 candidates and
keeping the one that makes the grouping work — only **4 of the 105 separate all three tiers**, and the
winner's margins are **+1.09 % and +1.28 %**, which is *at or below* the 1-2 % instrument floor of
§6.4. ⇒ This is a window fitted to a desired answer on 17 comparisons. It is recorded as a
HYPOTHESIS with a pinned configuration so it can be refuted out-of-sample, and for no other purpose.
§9.3 is the experiment that would earn it.

⚠ Note what the two rejected windows do: at 560-580 (where the grouping is visually obvious) tiers A
and B OVERLAP by 2.17 %; at 550-600 (§7.2's window, chosen for the two-tier alarm) group B and C
INVERT — Spar Premium runs to 53-55 % while S-Budget sits at 50-53 %. The grouping is not a property
of the oils alone; it is a property of the oils AND the window.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_tiered_alarm.py
"""
import numpy as np

from shape_similarity import shape, dissimilarity

REFERENCE = "20260812BillJaNatuerlich/001.pdf"
WINDOW = (540.0, 584.0)                 # ⛔ scanned, not derived — see the docstring and §8.3
T1, T2 = 14.7, 22.8                     # midpoints of the two gaps at that window

SILENT, MINOR, MAJOR = "silent", "probably minor difference", "probably major difference"
EXPECTED = [
    (SILENT, "Ja! Natürlich", ["20260812BillJaNatuerlich/%03d.pdf" % i for i in (2, 3)]),
    (MINOR, "Steirerkraft g.g.A.", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)]),
    (MINOR, "Spar Premium g.g.A.", ["20260807C/%03d.pdf" % i for i in (1, 2, 3)]),
    (MAJOR, "Spar S-Budget", ["20260807B/%03d.pdf" % i for i in (1, 2, 3)]),
    (MAJOR, "Billa Clever", ["20260812_BillaCleverB/%03d.pdf" % i for i in (1, 2, 3)]),
    (MAJOR, "Spar Steirisches", ["20260807A/%03d.pdf" % i for i in (1, 2, 3)]),
]
# Fills NOT in Edwin's grouping — reported so the tiers can be seen to generalise, or not.
OUT_OF_SAMPLE = [("Kiendler 0801A", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
                 ("Steirerkraft 0729B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
                 ("Billa Clever 0812A", ["20260812_BillaClever/%03d.pdf" % i for i in (1, 2, 3)]),
                 ("S-Budget 0731A", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]


def verdict(distance):
    if distance < T1:
        return SILENT
    return MINOR if distance < T2 else MAJOR


def alarm(path, reference=None):
    """The whole tracker, in three lines: shape, distance, tier."""
    reference = reference if reference is not None else shape(REFERENCE, WINDOW)
    distance = dissimilarity(reference, shape(path, WINDOW))
    return distance, verdict(distance)


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    print("=" * 92)
    print("REFERENCE %s   window %g-%g nm   T1 = %.1f%%   T2 = %.1f%%"
          % (REFERENCE, WINDOW[0], WINDOW[1], T1, T2))
    print("=" * 92)
    reference = shape(REFERENCE, WINDOW)

    print("   %-22s %5s %9s   %-26s %s" % ("fill", "run", "D", "alarm says", "expected"))
    right = total = 0
    for expected, name, paths in EXPECTED:
        for i, path in enumerate(paths, start=1):
            distance, says = alarm(path, reference)
            run = int(path[-7:-4])
            total += 1
            right += says == expected
            print("   %-22s %5d %8.2f%%   %-26s %s" %
                  (name, run, distance, says, "✓" if says == expected else "✗ want " + expected))
    print("\n   %d / %d runs land in the tier Edwin assigned" % (right, total))

    print("\n   --- fills OUTSIDE Edwin's grouping (no expectation, reported for generalisation) ---")
    for name, paths in OUT_OF_SAMPLE:
        values = [alarm(p, reference)[0] for p in paths]
        tiers = sorted({verdict(v) for v in values})
        print("   %-22s n=%d   D %6.2f - %6.2f%%   -> %s"
              % (name, len(values), min(values), max(values), " / ".join(tiers)))

    print("\n   --- the same six fills at the two REJECTED windows ---")
    for window in ((560.0, 580.0), (550.0, 600.0)):
        other = shape(REFERENCE, window)
        print("   window %g-%g nm" % window)
        for expected, name, paths in EXPECTED:
            values = [dissimilarity(other, shape(p, window)) for p in paths]
            print("      %-22s %-26s %s" % (name, expected,
                                            "  ".join("%6.2f%%" % v for v in values)))


if __name__ == "__main__":
    main()
