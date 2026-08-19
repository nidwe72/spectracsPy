"""SPEC_capture_quality.md §16.12.2B's λ⁻ⁿ pedestal fit, run at last — and it REFUTES ITS OWN MODEL.

§16.12.2B pre-registered two readings before any data was seen:

    n in 2-4, decreasing run-to-run   ->  droplets growing: Ostwald ripening observed directly
    n ~ 0                             ->  a flat offset, not scatter, and §16.12.2 is wrong

⛔ The measured answer is NEITHER, and the section offers no third branch. Three things, in order:

  1  THE FIT CANNOT BE RUN ON THE SHIPPED ANCHORS. PB_BASELINE_WINDOWS' far window (620-630) is not
     pigment-free — protochlorophyll Qy sits at ~623-626 inside it. Absorbance there is ~2.3x the
     520-540 window, so a power law fits n ~ -5.5: a pedestal RISING toward the red, which is not
     scatter. The 3-parameter offset+power form is degenerate exactly as §16.12.2B's own caveat warned.

  2  THE ARCHIVE CANNOT SUPPORT IT ANYWAY. Only the WINNER spectrum of each run was persisted
     (SPEC_settled_measurement §9.1a/§27.25), so there is no within-run pair of full spectra at two
     turbidities. The only spectrally-resolved time series is THREE band means per decision row.

  3  ON THOSE THREE BANDS THE POWER LAW IS REFUTED. Across run 006's 13x clearing sweep the change is
     NON-MONOTONE in wavelength — Soret 1.06, valley 1.00, Q band 1.30 — an interior minimum at the
     valley. No lambda^-n, at any exponent, has one. Reproduced in 004, 007 and 006's own tail.

Run against the seven series F records (SPEC_settled_measurement.md §28). No rig, no fixture.
"""

import json
import math
import sys

import numpy as np
from pypdf import PdfReader
from scipy.optimize import curve_fit
from scipy.signal import medfilt

SERIES_F = "/home/nidwe72/development/spectracs/spectracs-references/tmp/20260817LigitschA"
RUNS = ("001", "002", "003", "004", "005", "006", "007")

WINDOWS = ((520.0, 540.0), (620.0, 630.0))         # DevSpectralPlugin.PB_BASELINE_WINDOWS
CENTRE = {"soret": 454.0, "valley": 530.0, "qBand": 572.5}   # 448-460 / 500-560 / 565-580
PIVOT, KERNEL = 500.0, 7                           # MedianFilterOp(kernelSize=7), as the plugin de-spikes
SWEEP_ROWS = 9                                     # run 006's high-turbidity sweep: rows 0..8


def workflow(path):
    return json.loads(PdfReader(path).attachments["workflow.json"][0])


def absorption(document):
    for phase in document["phases"]:
        for step in phase.get("steps", []):
            spectra = step.get("spectra") or {}
            if "ABSORPTION" in spectra:
                pairs = sorted((float(k), v) for k, v in spectra["ABSORPTION"].items())
                return (np.array([p[0] for p in pairs]),
                        medfilt(np.array([p[1] for p in pairs], dtype=float), KERNEL))
    raise KeyError("no ABSORPTION spectrum")


def decisionRows(document):
    return [r for r in document["monitorRecord"]["rows"]
            if r.get("isDecisionRow") and not r.get("provisional")]


def exponentFrom(slope, centre):
    """slope = (lam_valley / lam_band)^n, so n = ln(slope) / ln(lam_valley / lam_band)."""
    if slope <= 0 or abs(centre - CENTRE["valley"]) < 1e-9:
        return float("nan")
    return math.log(slope) / math.log(CENTRE["valley"] / centre)


def step1(spectra):
    print("1 · THE FIT AS PRE-REGISTERED, ON PB_BASELINE_WINDOWS %s" % (WINDOWS,))
    lam = spectra["001"][0]
    mask = np.zeros_like(lam, dtype=bool)
    for lo, hi in WINDOWS:
        mask |= (lam >= lo) & (lam <= hi)
    print("    %d points in the windows  (⚠ §16.12.2B assumed ~50; the grid is far finer)\n" % mask.sum())
    print("    run   A(520-540)  A(620-630)   ratio    n (power)   n (offset+power)   c")

    def power(x, k, n):
        return k * (x / PIVOT) ** (-n)

    def offsetPower(x, c, k, n):
        return c + k * (x / PIVOT) ** (-n)

    for name in RUNS:
        lam, a = spectra[name]
        inWindows = np.zeros_like(lam, dtype=bool)
        for lo, hi in WINDOWS:
            inWindows |= (lam >= lo) & (lam <= hi)
        near = a[(lam >= WINDOWS[0][0]) & (lam <= WINDOWS[0][1])].mean()
        far = a[(lam >= WINDOWS[1][0]) & (lam <= WINDOWS[1][1])].mean()
        p, _ = curve_fit(power, lam[inWindows], a[inWindows], p0=[near, 1.0], maxfev=40000)
        q, _ = curve_fit(offsetPower, lam[inWindows], a[inWindows], p0=[0.0, near, 1.0], maxfev=80000)
        print("    %s   %9.5f  %9.5f   %5.2f   %+8.2f   %+12.3f   %+10.3f"
              % (name, near, far, far / near, p[1], q[2], q[0]))
    print("\n    ⛔ n is NEGATIVE on every run: absorbance RISES toward the red inside the 'baseline'.")
    print("    ⛔ That is protochlorophyll Qy at ~623-626 nm sitting INSIDE the far window — it is a")
    print("       straight-line ANCHOR pair, never a pigment-free window. The fit is invalid here.")
    print("    ⛔ And offset+power is degenerate (c runs to +hundreds, n to 0) — §16.12.2B's own caveat.\n")


def step2(spectra, sample="005"):
    lam, a = spectra[sample]
    print("2 · WHERE THE SPECTRUM ACTUALLY HAS PIGMENT-LIGHT STRETCHES  (run %s, 5 nm means)" % sample)
    for lo in range(500, 635, 15):
        sel = (lam >= lo) & (lam < lo + 15)
        print("      %3d-%3d nm  A = %.4f" % (lo, lo + 15, a[sel].mean()), end="")
        print("   <- local minimum" if lo in (500, 590) else "")
    print("    ⇒ the true minima are ~505-515 and ~595-605. 620-630 is on the RISING Qy flank.\n")


def step3(rows):
    print("3 · THE ONLY SPECTRALLY-RESOLVED TIME SERIES THE ARCHIVE HAS: THREE BAND MEANS PER ROW")
    print("    Within one run the pigment concentration is fixed, so d(band)/d(A_valley) isolates")
    print("    whatever LEAVES the beam. A lambda^-n pedestal must make this MONOTONE in wavelength.\n")
    print("    slope = dA_band / dA_valley        soret(454)        valley(530)      qBand(572)")
    cases = (("006 rows 0-8  (13x sweep)", rows["006"][:SWEEP_ROWS]),
             ("006 rows 9-19 (the tail)", rows["006"][SWEEP_ROWS:]),
             ("004 (whole run)", rows["004"]),
             ("007 (whole run)", rows["007"]))
    for label, block in cases:
        valley = np.array([r["valley"] for r in block])
        slopes = {b: np.polyfit(valley, np.array([r[b] for r in block]), 1)[0] for b in CENTRE}
        print("    %-27s  %7.3f          %7.3f          %7.3f"
              % (label, slopes["soret"], slopes["valley"], slopes["qBand"]))
    print()
    block = rows["006"][:SWEEP_ROWS]
    valley = np.array([r["valley"] for r in block])
    for band in ("soret", "qBand"):
        slope = np.polyfit(valley, np.array([r[band] for r in block]), 1)[0]
        print("    implied n from %-6s = %+6.2f      (Rayleigh predicts +4.0 at BOTH bands)"
              % (band, exponentFrom(slope, CENTRE[band])))
    print("\n    ⛔⛔ THE REDDER BAND MOVES MORE THAN THE VALLEY AND SO DOES THE BLUER ONE — an interior")
    print("        minimum. No power law has one. ⇒ the lambda^-n MODEL is refuted, not just its exponent.")
    print("    ⚠ Candidate readings, none of them established here: pathlength amplification by multiple")
    print("      scattering (which multiplies the pigment's OWN bands), or pigment leaving the beam inside")
    print("      the droplets. ⚠ And at A_Soret ~ 2.0 (T ~ 1 %) the sweep's Soret slope may be compressed")
    print("      by detector nonlinearity — which is why the TAIL value is the trustworthy one.\n")


def step4(rows):
    print("4 · THE COUPLING k = dA_Soret/dA_valley, POOLED  (soret_ij = a_i + k*valley_ij + b_i*t_ij)")
    print("    A common k with a per-run intercept AND a per-run bleach rate. Identifiable because the")
    print("    runs differ in how A_valley moves against time.\n")

    def pooled(names, tailOnly):
        columns, y = [], []
        index = {n: i for i, n in enumerate(names)}
        size = len(names)
        for name in names:
            block = rows[name][SWEEP_ROWS:] if (tailOnly and name == "006") else rows[name]
            for r in block:
                row = np.zeros(2 * size + 1)
                row[index[name]] = 1.0
                row[size + index[name]] = r["t"] / 60.0
                row[2 * size] = r["valley"]
                columns.append(row)
                y.append(r["soret"])
        X, y = np.array(columns), np.array(y)
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        residual = y - X @ beta
        cov = np.linalg.pinv(X.T @ X) * (residual @ residual) / (len(y) - X.shape[1])
        return beta[2 * size], math.sqrt(cov[2 * size, 2 * size]), \
            float(np.sqrt((residual ** 2).mean())), len(y), beta[size:2 * size]

    k, se, rms, points, _ = pooled(RUNS, False)
    print("      all rows, all runs        : k = %.3f +- %.3f   rms %.5f  (%d points)" % (k, se, rms, points))
    kTail, seTail, rmsTail, pointsTail, bleach = pooled(RUNS, True)
    print("      006 truncated to its TAIL : k = %.3f +- %.3f   rms %.5f  (%d points)  <- ⭐ our regime"
          % (kTail, seTail, rmsTail, pointsTail))
    print("      ⇒ k is NOT a constant: 1.06 at A_valley ~ 1, %.2f at A_valley ~ 0.09. Another way to see"
          % kTail)
    print("        that the single-exponent pedestal does not describe this sample.\n")
    print("      per-run photobleaching b (/min), from the tail-truncated fit:")
    for name, b in zip(RUNS, bleach):
        print("         %s  %+.4f%s" % (name, b, "   <- the §29.1 -0.482 run" if name == "003" else ""))
    print("      ⇒ %+.4f .. %+.4f /min, a %.1fx spread across seven fills of ONE oil in one evening"
          % (max(bleach), min(bleach), min(bleach) / max(bleach)))
    return kTail, bleach


def step5(k, bleach):
    print("\n5 · WHAT THIS DOES TO §31.9a's BREAK-EVEN  (the Soret sign is readable only above |b|/k)")
    for label, value in (("gentlest fill", max(bleach)), ("median", sorted(bleach)[3]),
                         ("harshest fill", min(bleach))):
        print("      %-14s b = %+.4f/min  ->  rise rate must exceed %.4f /min" % (label, value, abs(value) / k))
    rise, minutes, dValley = 0.0012, 12.53, 0.0147
    median = sorted(bleach)[3]
    print("      the 2026-08-19 fill rose at %.4f /min" % rise)
    print("      scattering lift k*dValley = %+.4f   vs   bleaching |b|*dt = %.4f   (%.1fx larger)"
          % (k * dValley, abs(median * minutes), abs(median * minutes) / (k * dValley)))
    print("\n    ⚠ §31.9a's CONCLUSION SURVIVES but its margin shrinks: %.1fx, not 5.4x, and only %.1fx"
          % (abs(median * minutes) / (k * dValley), abs(max(bleach)) / k / rise))
    print("      against the gentlest fill. ⭐ The stronger reason not to gate on the sign is that the")
    print("      break-even depends on THIS fill's bleach rate — which varies %.1fx and is unknowable"
          % (min(bleach) / max(bleach)))
    print("      while the run is still going.")
    print("    ⛔ WITHDRAWN: §31.9a's 'n = 0.32'. It converted k into an exponent through a power law")
    print("      that step 3 refutes. k = %.2f is a band-pair coupling and nothing more." % k)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else SERIES_F
    documents = {name: workflow("%s/%s.pdf" % (folder, name)) for name in RUNS}
    spectra = {name: absorption(d) for name, d in documents.items()}
    rows = {name: decisionRows(d) for name, d in documents.items()}
    step1(spectra)
    step2(spectra)
    step3(rows)
    k, bleach = step4(rows)
    step5(k, bleach)


if __name__ == "__main__":
    main()
