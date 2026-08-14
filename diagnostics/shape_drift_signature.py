"""Is a fill's run-to-run shape scatter NOISE or DRIFT? (`SPEC_history_tracker.md` §6.4 — the result
   that reframes the whole floor question. Cf. §16.33, §16.34.4: Ja! Natürlich's run-to-run CV is
   93 % settling drift, not measurement noise.)

Runs within a fill are time-ordered, which noise cannot exploit and a drift cannot hide from. Noise
has no memory, so D(1,2), D(1,3), D(2,3) should be alike. A monotone drift must satisfy

    D(1,3) > D(1,2)   and   D(1,3) > D(2,3)          <- the drift signature

because the pair furthest apart IN TIME is then furthest apart in shape. And for a straight-line
trajectory the triangle inequality becomes tight, so

    straightness = D(1,3) / (D(1,2) + D(2,3))        ~1.0 a straight march, ~0.5 a random walk

⭐ Why it matters: if the within-fill scatter is drift, then it is NOT the instrument's floor. It is
the tracker correctly reporting that the sample changed while it was being measured — which is a
protocol problem (settling time, §16.34.3a item 1), not a limit on the metric.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"  \
        ./venv/bin/python diagnostics/shape_drift_signature.py
"""
import numpy as np

from shape_similarity import shape, dissimilarity

# Every three-run fill available, including BOTH Billa Clever fills of 2026-08-12.
FILLS = [("Ja! Natürlich", ["20260812BillJaNatuerlich/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Steirerkraft", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar Steirisches", ["20260807A/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar Premium", ["20260807C/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Spar S-Budget", ["20260807B/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Billa Clever A", ["20260812_BillaClever/%03d.pdf" % i for i in (1, 2, 3)]),
         ("Billa Clever B", ["20260812_BillaCleverB/%03d.pdf" % i for i in (1, 2, 3)])]


def run(window):
    print("=" * 92)
    print("WINDOW %g-%g nm" % window)
    print("=" * 92)
    print("   %-18s %8s %8s %8s   %-16s %12s" %
          ("fill", "D(1,2)", "D(2,3)", "D(1,3)", "signature", "straightness"))
    for name, paths in FILLS:
        vectors = [shape(p, window) for p in paths]
        first = dissimilarity(vectors[0], vectors[1])
        second = dissimilarity(vectors[1], vectors[2])
        span = dissimilarity(vectors[0], vectors[2])
        drift = span > first and span > second
        print("   %-18s %7.2f%% %7.2f%% %7.2f%%   %-16s %11.2f" %
              (name, first, second, span, "DRIFT" if drift else "noise-like",
               span / (first + second)))
    print()


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    run((550.0, 600.0))
    run((560.0, 580.0))


if __name__ == "__main__":
    main()
