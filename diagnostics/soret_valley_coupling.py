"""How much does turbidity move A_Soret? — SPEC_settled_measurement.md §31.9a.

⭐ Answers ONE question: is the sign of `A_Soret` usable as a second discriminator between a re-clouding
fill (TEST B) and a ripening one (TEST C)? It measures the scattering coupling `k = dA_Soret/dA_valley`
from the series F archive, derives each fill's photobleaching rate from it, and compares the two against
the 2026-08-19 degrading fill.

⛔ THE ANSWER IS NO — the coupling is real (k = 1.05) but is swamped by bleaching at any rise rate slow
enough to be TEST C's business. See §31.9a; this script is the arithmetic behind it.

Reads the PDFs directly (pypdf attachments["workflow.json"]), so it needs no fixture and no rig.
"""

import json
import math
import sys

from pypdf import PdfReader

SERIES_F = "/home/nidwe72/development/spectracs/spectracs-references/tmp/20260817LigitschA"
RUNS = ("001", "002", "003", "004", "005", "006", "007")

# ⭐ The 2026-08-19 degrading fill, first and last decision rows (§31.1). Transcribed rather than read,
# because that run's own PDF lives in a different day folder — repoint DEGRADING_PDF to re-derive it.
DEGRADING = {"valley": (0.0463, 0.0610), "soret": (0.6798, 0.6551), "t": (6.3, 758.1)}

SORET_NM, VALLEY_NM = 454.0, 530.0     # band centres: V_SORET_BAND 448-460, the valley 500-560


def decisionRows(path):
    workflow = json.loads(PdfReader(path).attachments["workflow.json"][0])
    rows = workflow["monitorRecord"]["rows"]
    return [row for row in rows if row.get("isDecisionRow") and not row.get("provisional")]


def couplingFromSweep(rows, upTo=9):
    """k over run 006's high-turbidity sweep, where bleaching is a rounding error (§31.9a)."""
    first, last = rows[0], rows[upTo - 1]
    dValley = last["valley"] - first["valley"]
    dSoret = last["soret"] - first["soret"]
    minutes = (last["t"] - first["t"]) / 60.0
    return [(bleach, (dSoret - bleach * minutes) / dValley) for bleach in (0.0, -0.005, -0.010, -0.020)]


def bleachRate(rows, k):
    first, last = rows[0], rows[-1]
    dValley = last["valley"] - first["valley"]
    dSoret = last["soret"] - first["soret"]
    minutes = (last["t"] - first["t"]) / 60.0
    return (dSoret - k * dValley) / minutes, dValley, dSoret, minutes


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else SERIES_F
    runs = {name: decisionRows("%s/%s.pdf" % (folder, name)) for name in RUNS}

    print("k FROM RUN 006's 13x TURBIDITY SWEEP (rows 0..8) — nearly free of any bleach assumption")
    for bleach, k in couplingFromSweep(runs["006"]):
        print("   assume bleach %+.3f/min  ->  k = %.3f" % (bleach, k))

    k = 1.05
    print("\nBLEACH RATE PER FILL, at k = %.2f" % k)
    rates = []
    for name in RUNS:
        rate, dValley, dSoret, minutes = bleachRate(runs[name], k)
        rates.append(rate)
        print("   %s  dValley %+.4f  dSoret %+.4f  dt %5.2f min  ->  b = %+.4f /min"
              % (name, dValley, dSoret, minutes, rate))
    print("   ⇒ %+.4f .. %+.4f /min — a %.1fx spread across seven fills of ONE oil"
          % (max(rates), min(rates), min(rates) / max(rates)))

    print("\nBREAK-EVEN — the Soret sign is diagnostic only above riseRate = |b| / k")
    for rate in (max(rates), sorted(rates)[3], min(rates)):
        print("   b = %+.4f/min  ->  riseRate must exceed %.4f /min" % (rate, abs(rate) / k))
    print("   ⛔ TEST B's theta is 0.0050/min, so the band STRADDLES it (§31.9a)")

    dValley = DEGRADING["valley"][1] - DEGRADING["valley"][0]
    dSoret = DEGRADING["soret"][1] - DEGRADING["soret"][0]
    minutes = (DEGRADING["t"][1] - DEGRADING["t"][0]) / 60.0
    print("\n20260819/001 — the degrading fill, rising at %.4f /min" % (dValley / minutes))
    print("   scattering lift  k*dValley = %+.4f" % (k * dValley))
    print("   bleaching        |b|*dt    = %+.4f  (at the median b)" % (sorted(rates)[3] * minutes))
    print("   ⛔ bleaching is %.1fx larger — the Soret falls whether or not the fill is re-clouding"
          % abs(sorted(rates)[3] * minutes / (k * dValley)))
    print("   implied bleach at k=%.2f: %+.5f /min   (series F: %+.4f..%+.4f)"
          % (k, (dSoret - k * dValley) / minutes, max(rates), min(rates)))
    print("   implied bleach at k=0   : %+.5f /min   — below the whole series F range"
          % (dSoret / minutes))

    print("\nSIDE FINDING (§31.9a, belongs to SPEC_capture_quality §16.12.2B): k = (%.0f/%.0f)^n"
          % (VALLEY_NM, SORET_NM))
    print("   n = %.2f   — Rayleigh is 4; large Mie droplets tend to 0"
          % (math.log(k) / math.log(VALLEY_NM / SORET_NM)))
    print("   ⚠ two band means, NOT §16.12.2B's ~50-point fit. It makes that fit urgent; it does not replace it.")


if __name__ == "__main__":
    main()
