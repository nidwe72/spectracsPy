"""Edwin's working hypothesis, tested on data already on disk. (`SPEC_history_tracker.md` §8.4)

    Edwin 2026-08-14: "maybe though the BillaJaNatürlich was measured with a faint A_Q, the shape is
    the one that would survive a stronger dilution. That is an assumption for now, a working
    hypothesis if you like."

Restated so it can be refuted: *the shape Ja! Natürlich shows at a weak fill is the same shape it
would show at a strong one* — i.e. `D` is invariant to concentration even near the sensor floor.

Three probes, two of them free.

PROBE 0 - the one DESIGNED dilution test in the archive (`shape_refill.py` §6.2, Kiendler): a
    one-drop dose change moves the shape 17.7-17.9 %, while two independent preparations at the SAME
    dose agree to 4.45 %. ⛔ That is direct evidence AGAINST the hypothesis, on a different oil.

PROBE 1 - the drift direction. §6.4 shows JN's three runs are a dissolving fill: 001 least dissolved,
    003 most. A better-dissolved fill is optically the stronger one, so IF the hypothesis holds the
    march should not carry the shape anywhere in particular; if instead the shape moves TOWARD the
    other oils as it dissolves, the weak-fill shape is a concentration artefact.

PROBE 2 - extrapolate that march by a factor f (f = 0 is run 001, f = 1 is run 003) and ask whether
    a hypothetically stronger JN keeps approaching group B or turns away.

⛔ Neither probe substitutes for the real test, which is one evening on the bench: §9.3's JN dilution
ladder — the same oil at 1x, 2x and 3x dose, settled, one session, one exposure state.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_dilution_hypothesis.py
"""
import numpy as np

from shape_similarity import shape, dissimilarity

JN = ["20260812BillJaNatuerlich/%03d.pdf" % i for i in (1, 2, 3)]
OTHERS = [("Steirerkraft  (B)", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)]),
          ("Spar Premium  (B)", ["20260807C/%03d.pdf" % i for i in (1, 2, 3)]),
          ("Spar Steirisch(C)", ["20260807A/%03d.pdf" % i for i in (1, 2, 3)]),
          ("Spar S-Budget (C)", ["20260807B/%03d.pdf" % i for i in (1, 2, 3)]),
          ("Billa Clever  (C)", ["20260812_BillaCleverB/%03d.pdf" % i for i in (1, 2, 3)])]


def renormalised(vector):
    return (vector - vector.mean()) / vector.std()


def probes(window):
    print("=" * 92)
    print("WINDOW %g-%g nm" % window)
    print("=" * 92)
    runs = [shape(p, window) for p in JN]
    templates = {name: renormalised(np.mean([shape(p, window) for p in paths], axis=0))
                 for name, paths in OTHERS}

    print("\n   PROBE 1 — distance from each JN run to each other oil, as the fill dissolves")
    print("   %-20s %8s %8s %8s   %s" % ("other oil", "JN 001", "JN 002", "JN 003", "trend 001→003"))
    for name, template in templates.items():
        values = [dissimilarity(v, template) for v in runs]
        print("   %-20s %7.2f%% %7.2f%% %7.2f%%   %s (%+.2f%%)"
              % (name, values[0], values[1], values[2],
                 "TOWARD it" if values[2] < values[0] else "AWAY from it", values[2] - values[0]))

    print("\n   PROBE 2 — extrapolating the 001→003 march (f = 0 is run 001, f = 1 is run 003)")
    direction = runs[2] - runs[0]
    print("   %-6s %s" % ("f", "".join("%20s" % n for n in templates)))
    for factor in (0.0, 1.0, 2.0, 4.0, 8.0):
        moved = renormalised(runs[0] + factor * direction)
        print("   %-6.1f %s"
              % (factor, "".join("%19.2f%%" % dissimilarity(moved, t) for t in templates.values())))
    print()


def main():
    print(__doc__.split("Run:")[0].strip())
    print()
    probes((540.0, 584.0))
    probes((560.0, 580.0))


if __name__ == "__main__":
    main()
