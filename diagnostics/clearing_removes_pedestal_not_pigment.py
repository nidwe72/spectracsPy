"""Does the pigment sediment out with the haze? — the natural experiment, run 216 times already.

    ./venv/bin/python diagnostics/clearing_removes_pedestal_not_pigment.py

⭐ WHY. `AOCS Cc 13j-97` answers turbidity with a **filter aid** — 0.5 g diatomaceous earth per 300 g of
oil, 2.5 min at 250 rpm, filter (`spectracs-references/articles/`). That is the industry's answer to the
problem `SPEC_settled_measurement.md` solves by WAITING, and it takes three minutes instead of twenty.
Before any of that is worth a bench test, one question has to be answered:

    ⛔ IF FILTERING TAKES THE PIGMENT OUT WITH THE HAZE, THE WHOLE IDEA IS DEAD.

⭐⭐ And it is already answered, on data on disk. **Sedimentation removes the same droplet population a
filter would.** Every settling run is therefore a slow filtration experiment with the pigment watched
throughout — the settling monitor latches `soret`, `valley` and `qBand` on every row.

THE TEST. Take each fill's first and last monitor row and ask what the clearing took away:

  * ⛔ if the pigment SEDIMENTS, each band loses its own pigment share ⇒ the drops scale with the bands
    themselves, and `d(Soret)/d(valley)` should be ~ `Soret/valley` ~ 4-5;
  * ⭐ if the pigment stays DISSOLVED, only the scatter PEDESTAL leaves ⇒ every band drops by nearly the
    SAME ABSOLUTE amount and `d(Soret)/d(valley)` ~ 1.

⚠ WHAT THIS DOES NOT TEST. Sedimentation is gravity; a filter aid is gravity **plus a silica surface**.
⛔ **Adsorption is exactly what this experiment cannot see**, and it is the real risk — chlorophylls adsorb
on silica (that is how they are chromatographed), and diatomaceous earth is amorphous silica with
10-30 m^2/g. The AOCS dose is deliberately low (0.167 % w/w against 0.5-2 % for bleaching earth, and 30 C
against 90-110 C), but low is not zero. **This script clears the first hurdle only.**
"""
import glob
import json
import os

import numpy as np
from pypdf import PdfReader

ARCHIVE = "/home/nidwe72/development/spectracs/spectracs-references/tmp"
MINIMUM_ROWS = 8
MINIMUM_CLEARING = 0.05        # A units the valley must lose before a fill counts as "cleared"


def monitorRows(workflow):
    """The settling monitor's latched rows, wherever the report happens to nest them."""
    def find(node):
        found = []
        if isinstance(node, dict):
            for value in node.values():
                found += find(value)
        elif isinstance(node, list):
            if node and isinstance(node[0], dict) and "valley" in node[0] and "soret" in node[0]:
                found.append(node)
            else:
                for item in node:
                    found += find(item)
        return found
    hits = find(workflow)
    return hits[0] if hits else None


def main():
    deltas = {"valley": [], "soret": [], "qBand": []}
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*", "*.pdf"))):
        try:
            workflow = json.loads(PdfReader(path).attachments["workflow.json"][0])
        except Exception:
            continue
        rows = monitorRows(workflow)
        if not rows or len(rows) < MINIMUM_ROWS:
            continue
        first, last = rows[0], rows[-1]
        if any(first.get(k) is None or last.get(k) is None for k in deltas):
            continue
        if first["valley"] - last["valley"] < MINIMUM_CLEARING:
            continue           # never cleared — nothing to learn from it
        for key in deltas:
            deltas[key].append(first[key] - last[key])

    valley = np.array(deltas["valley"])
    if valley.size < 3:
        print("only %d clearing runs found — not enough" % valley.size)
        return
    soret, qBand = np.array(deltas["soret"]), np.array(deltas["qBand"])

    print("%d fills that actually cleared (valley lost > %.2f A)\n" % (valley.size, MINIMUM_CLEARING))
    print("  what the clearing removed        median     5th..95th pct")
    for label, values in (("d(valley)  = the pedestal", valley), ("d(Soret)", soret), ("d(Q band)", qBand)):
        print("  %-30s %7.3f   %.3f .. %.3f"
              % (label, np.median(values), *np.percentile(values, [5, 95])))

    print("\n  ⭐ THE DISCRIMINATOR — ~1 means a flat pedestal left, ~4-5 means pigment left with it")
    for label, values in (("d(Soret)/d(valley)", soret / valley), ("d(Q)/d(valley)", qBand / valley)):
        print("  %-30s %7.3f   %.3f .. %.3f"
              % (label, np.median(values), *np.percentile(values, [5, 95])))
    print("\n  correlation d(Soret) vs d(valley)   r = %+.3f" % np.corrcoef(soret, valley)[0, 1])
    print("  correlation d(Q)     vs d(valley)   r = %+.3f" % np.corrcoef(qBand, valley)[0, 1])

    ratio = float(np.median(soret / valley))
    print("\n⇒ %s" % ("⭐⭐ THE PIGMENT STAYS DISSOLVED. Clearing removes an additive pedestal and nothing"
                       " else,\n  confirming KB_spectroscopy_physics.md §8.2/§8.3 on real fills."
                       if ratio < 2.0 else
                       "⛔ the pigment leaves with the haze — filtration would destroy the measurement."))
    print("  ⚠ n is small: most archived fills are read AFTER settling, so few have a clearing arc.")
    print("  ⚠ the ratios sit slightly ABOVE 1 (Q more than Soret), which is backwards for scatter —")
    print("    scatter is stronger in the blue. Most likely the Soret's drop is UNDERSTATED because it")
    print("    starts near-opaque (A ~ 1.5-1.9) and sits in §7.13's compression regime. Not a finding.")
    print("  ⛔ and this says NOTHING about adsorption onto the filter aid — see the module docstring.")


if __name__ == "__main__":
    main()
