"""What happened across the three runs of 20260804A (filtered, over-dilute Steirerkraft)?

Edwin's observation 2026-08-04: 001 and 003 share a Soret level, 002 sits LOWER, and the
"Verdict · baseline" gauge follows. Non-monotonic in run order, so it is not settling and not a
one-way drift. This probe just puts every quantity we already know how to compute beside every run
so the pattern can be read instead of guessed at.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/probe_20260804A.py
"""
import json
import os
import time

import numpy as np
from pypdf import PdfReader

from settling_sweep import BASE, despikedAbsorption, asArrays, plugin, feature

RUNS = ["20260804A/%03d.pdf" % i for i in range(1, 7)]
# The AE-landed exposure per run, read off the CAPTURE-SETTINGS log and matched to the runs by reproducing
# each capture's CAPTURE-LOWDN value from its stored spectrum (see EXPOSURE table in main()).
EXPOSURE = {"001": 104, "002": 90, "003": 104, "004": 104, "005": 104, "006": 104}
# The archive's post-rebuild green sets, for scale: is 20260804A's Soret simply lower than everything?
ARCHIVE = {"Steirerkraft B": ["20270729B/%03d.pdf" % i for i in range(1, 7)],
           "Steirerkraft C": ["20270729C/%03d.pdf" % i for i in range(1, 7)],
           "Kiendler A": ["20260801A/%03d.pdf" % i for i in range(1, 7)]}

SORET, Q = plugin.PB_SORET_BAND, plugin.PB_Q_BAND
NEAR, FAR = plugin.PB_BASELINE_WINDOWS
R_Q = plugin.PB_R_Q


def rawSpectra(path):
    """Every spectrum kind the embedded workflow carries, as (lam, values) arrays."""
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    out = {}
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            for kind, raw in (step.get("spectra") or {}).items():
                values = raw.get("valuesByNanometers", raw)
                lam = np.array(sorted(float(k) for k in values))
                out.setdefault(kind, (lam, np.array([float(values[str(k) if str(k) in values else k])
                                                     for k in lam])))
    return out


def metrics(path):
    spectrum = despikedAbsorption(path)
    lam, values = asArrays(spectrum)
    band = lambda w: float(values[(lam >= w[0]) & (lam <= w[1])].mean())
    corrected = feature.linearBaselineCorrected(spectrum, plugin.PB_BASELINE_WINDOWS)
    clam, cvalues = asArrays(corrected)
    cband = lambda w: float(cvalues[(clam >= w[0]) & (clam <= w[1])].mean())
    row = {"soretRaw": band(SORET), "qRaw": band(Q), "nearRaw": band(NEAR), "farRaw": band(FAR),
           "a450": band((448.0, 452.0)),
           "soretBase": cband(SORET), "qBase": cband(Q)}
    row["ratioRaw"] = row["soretRaw"] / max(row["qRaw"], 1e-9)
    row["ratioBase"] = row["soretBase"] / max(row["qBase"], 1e-9)
    row["ratioPedestal"] = row["soretBase"] / max(row["qBase"] - R_Q, 1e-9)
    return row, lam, values


def main():
    print("bands: Soret %s  Q %s  near %s  far %s   r_Q %+.4f\n" % (SORET, Q, NEAR, FAR, R_Q))

    print("=== 20260804A — the three filtered runs")
    header = ("run", "mtime", "A450", "SoretRaw", "Qraw", "near", "far",
              "SoretB", "QB", "raw S/Q", "base S/Q", "pedestal")
    print("%-6s %-6s %7s %8s %8s %8s %8s %8s %8s %8s %9s %9s" % header)
    print("-" * 108)
    rows, curves = [], []
    for path in RUNS:
        row, lam, values = metrics(path)
        rows.append(row)
        curves.append((path[-7:-4], lam, values))
        stamp = os.path.getmtime(BASE + path)
        print("%-6s %-6s %7.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.3f %9.3f %9.3f" % (
            path[-7:-4], time.strftime("%H:%M", time.localtime(stamp)),
            row["a450"], row["soretRaw"], row["qRaw"], row["nearRaw"], row["farRaw"],
            row["soretBase"], row["qBase"], row["ratioRaw"], row["ratioBase"], row["ratioPedestal"]))

    # Ratios BETWEEN runs — is 002 a uniform scale-down (concentration) or a shape change?
    print("\n=== 002 and 003 as MULTIPLES of 001 — a pure dilution difference scales every band alike")
    print("%-10s %9s %9s %9s %9s" % ("run", "A450", "Soret", "Q", "far"))
    print("-" * 50)
    for name, row in zip(("002/001", "003/001"), rows[1:]):
        print("%-10s %9.3f %9.3f %9.3f %9.3f" % (
            name, row["a450"] / rows[0]["a450"], row["soretRaw"] / rows[0]["soretRaw"],
            row["qRaw"] / rows[0]["qRaw"], row["farRaw"] / rows[0]["farRaw"]))

    # Whole-curve scale factor: least-squares fit of run k onto run 001 over the full range. If the
    # difference is concentration only, one number explains the whole spectrum.
    print("\n=== whole-curve fit  A_k ≈ c · A_001   (residual RMS says whether ONE number explains it)")
    base = curves[0][2]
    for name, lam, values in curves[1:]:
        c = float(values @ base / (base @ base))
        residual = values - c * base
        print("   %s   c = %.4f   residual RMS = %.5f A   (%.1f %% of the Soret band)" % (
            name, c, float(np.sqrt((residual ** 2).mean())),
            100.0 * float(np.sqrt((residual ** 2).mean())) / rows[0]["soretRaw"]))

    # The archive, for scale.
    print("\n=== archive context — mean ± sd per set")
    print("%-16s %5s %9s %9s %9s %9s" % ("set", "n", "A450", "SoretRaw", "base S/Q", "pedestal"))
    print("-" * 62)
    for name, paths in ARCHIVE.items():
        got = [metrics(p)[0] for p in paths]
        f = lambda key: (np.mean([g[key] for g in got]), np.std([g[key] for g in got], ddof=1))
        print("%-16s %5d %9s %9s %9s %9s" % (
            name, len(got),
            "%.3f±%.3f" % f("a450"), "%.3f±%.3f" % f("soretRaw"),
            "%.2f±%.2f" % f("ratioBase"), "%.2f±%.2f" % f("ratioPedestal")))
    got = rows
    f = lambda key: (np.mean([g[key] for g in got]), np.std([g[key] for g in got], ddof=1))
    print("%-16s %5d %9s %9s %9s %9s" % (
        "20260804A", len(got), "%.3f±%.3f" % f("a450"), "%.3f±%.3f" % f("soretRaw"),
        "%.2f±%.2f" % f("ratioBase"), "%.2f±%.2f" % f("ratioPedestal")))

    # What the raw S and R legs did — a reference change moves T=S/R without the sample changing.
    print("\n=== the raw legs — REFERENCE and SAMPLE counts (a reference shift alone moves every band)")
    print("%-6s %-28s %10s %10s %10s" % ("run", "spectrum kinds present", "@450", "@530", "@625"))
    print("-" * 70)
    for path in RUNS:
        spectra = rawSpectra(path)
        for kind in sorted(spectra):
            lam, values = spectra[kind]
            at = lambda w: float(values[np.argmin(np.abs(lam - w))])
            print("%-6s %-28s %10.4f %10.4f %10.4f" % (path[-7:-4], kind, at(450), at(530), at(625)))


if __name__ == "__main__":
    main()
