"""The pedestal's spectral SLOPE as a second, non-pigment channel -- and why it is NOT one.
(2026-08-21, from Edwin's "the oil is a black box" question.)

If the emulsion carries information the pigment channel misses, the obvious place to look is the
SHAPE of the scattering pedestal: particle size sets how blue-biased the scatter is
(`DOC_sample_physics.md` section 5.2), so a slope measure ought to read something about waxes, press
fines and moisture that `Q%` never touches.

    turbidity  = A(500-545) / A_Soret                 the pedestal's LEVEL
    blue-bias  = [A(470-490) - A(600-620)] / A_Soret  the pedestal's SLOPE

⛔ IT LOOKS LIKE A CHANNEL AND IT IS A CALENDAR. Between-oil over within-oil variance:

    turbidity level      F =  6.97
    blue-bias            F = 32.07     <- five times better, and NON-MONOTONE in Q%,
    Q% (the pigment)     F = 98.48        so it looks like an independent axis

But the blue-bias splits PERFECTLY BY DATE across 12 sessions and 52 fills -- 0.055-0.078 for every
session up to 2026-08-07, 0.018-0.029 for every session from 2026-08-12 on, with NO oil on both
sides. That is a rig-or-processing era boundary (the 448 nm Soret trim shipped 2026-08-10 and this
measure normalises by A448-460), not a property of any product.

⚠ THE NEAR-MISS IS THE LESSON, and it is why `DOC_metric_algebra.md` section 1.5a exists: an
unattributed channel cannot distinguish a rig change from an oil change. Recorded in
`SPEC_metric_research.md` section 13.4 so nobody re-runs it.

Reads the `workflow.json` embedded in each report by `pypdf` (`SPEC_pdf_export.md` section 2) and uses
the report's OWN despiked trace, like `peak_ratio_archive.py`.

Run:
    PYTHONPATH=. venv/bin/python diagnostics/pedestal_slope_era.py
"""
import json
import os
import subprocess
import tempfile

import numpy

ARCHIVE = os.path.expanduser("~/development/spectracs/spectracs-references/tmp")
GRID = numpy.arange(445.0, 630.01, 0.5)

# One session per entry, so "within" is fill-to-fill and never session-to-session. Labels from
# `all_metrics_archive.OILS` plus the later namings; "??" means the session is real but unlabelled
# on disk -- it still carries a DATE, which is the whole point of this script.
SESSIONS = [
    ("?? 0731A",            "20260731A"),
    ("?? 0801A",            "20260801A"),
    ("?? 0801B",            "20260801B"),
    ("?? 0807A",            "20260807A"),
    ("?? 0807B",            "20260807B"),
    ("Spar Premium 0807C",  "20260807C"),
    ("Steirerkraft 0807D",  "20260807D"),
    ("BillaClever 0812",    "20260812_BillaClever"),
    ("BillaCleverB 0812",   "20260812_BillaCleverB"),
    ("JaNatuerlich 0812",   "20260812BillJaNatuerlich"),
    ("Lugitsch 0814",       "20260814_Lugitsch_A"),
    ("Lugitsch 0817",       "20260817LigitschA"),
    ("BillaClever 0819",    "20280819BillaClever"),
]


def workflowOf(pdfPath, scratch):
    listing = subprocess.run(["pdfdetach", "-list", pdfPath],
                             capture_output=True, text=True).stdout
    index = next((line.split(":")[0].strip() for line in listing.splitlines()
                  if line.strip().endswith(": workflow.json")), None)
    if index is None:
        return None
    target = os.path.join(scratch, "w.json")
    subprocess.run(["pdfdetach", "-save", index, "-o", target, pdfPath], capture_output=True)
    with open(target) as handle:
        return json.load(handle)


def despikedTrace(workflow):
    for phase in workflow.get("phases", []):
        if phase.get("type") != "EVALUATION":
            continue
        for step in phase.get("steps", []):
            if step.get("label") != "Absorption (bands)":
                continue
            values = step["items"][0]["traces"][0]["values"]
            wavelengths = numpy.array([float(k) for k in values])
            absorbance = numpy.array(list(values.values()))
            order = numpy.argsort(wavelengths)
            return wavelengths[order], absorbance[order]
    return None


def bandMean(absorbance, low, high):
    window = (GRID >= low) & (GRID <= high)
    return float(absorbance[window].mean())


def collect():
    rows = {}
    with tempfile.TemporaryDirectory() as scratch:
        for label, folder in SESSIONS:
            directory = os.path.join(ARCHIVE, folder)
            if not os.path.isdir(directory):
                print("  MISSING %s" % folder)
                continue
            for name in sorted(os.listdir(directory)):
                if not name.endswith(".pdf"):
                    continue
                workflow = workflowOf(os.path.join(directory, name), scratch)
                if workflow is None:
                    continue
                trace = despikedTrace(workflow)
                if trace is None or trace[0][0] > 446.0 or trace[0][-1] < 628.0:
                    continue
                absorbance = numpy.interp(GRID, trace[0], trace[1])
                if bandMean(absorbance, 500.0, 560.0) > 1.0:       # the opaque fill
                    continue
                soret = bandMean(absorbance, 448.0, 460.0)
                rows.setdefault(label, []).append({
                    "turbidity": bandMean(absorbance, 500.0, 545.0) / soret,
                    "blueBias": (bandMean(absorbance, 470.0, 490.0)
                                 - bandMean(absorbance, 600.0, 620.0)) / soret,
                    "qPercent": 100.0 * (bandMean(absorbance, 565.0, 580.0)
                                         - bandMean(absorbance, 500.0, 560.0)) / soret})
    return rows


def fStatistic(rows, key):
    """Between-session variance over within-session variance -- one-way ANOVA's F."""
    groups = [numpy.array([r[key] for r in fills]) for fills in rows.values() if len(fills) >= 3]
    pooled = numpy.concatenate(groups)
    k, n = len(groups), len(pooled)
    between = sum(len(g) * (g.mean() - pooled.mean()) ** 2 for g in groups) / (k - 1)
    within = sum(((g - g.mean()) ** 2).sum() for g in groups) / (n - k)
    return between / within, k, n


def main():
    rows = collect()
    print("\n%-22s %3s | %-24s | %-16s | %s"
          % ("session", "n", "turbidity A500-545/A448", "blue-bias", "Q%"))
    for label, fills in rows.items():
        turbidity = numpy.array([r["turbidity"] for r in fills])
        blueBias = numpy.array([r["blueBias"] for r in fills])
        qPercent = numpy.array([r["qPercent"] for r in fills])
        print("%-22s %3d | %.3f ± %.3f (%.3f-%.3f) | %.3f ± %.3f  | %.2f ± %.2f"
              % (label, len(fills), turbidity.mean(), turbidity.std(ddof=1),
                 turbidity.min(), turbidity.max(),
                 blueBias.mean(), blueBias.std(ddof=1),
                 qPercent.mean(), qPercent.std(ddof=1)))

    print("\n  between-session variance / within-session variance:")
    for key, label in (("turbidity", "turbidity level"),
                       ("blueBias", "pedestal blue-bias"),
                       ("qPercent", "Q% (the pigment channel)")):
        f, k, n = fStatistic(rows, key)
        print("    %-26s F = %6.2f   (%d sessions, %d fills)" % (label, f, k, n))

    print("\n  ⛔ and now split the blue-bias BY DATE rather than by oil:")
    early = [(l, numpy.mean([r["blueBias"] for r in f])) for l, f in rows.items()
             if l.split()[-1] < "0810"]
    late = [(l, numpy.mean([r["blueBias"] for r in f])) for l, f in rows.items()
            if l.split()[-1] >= "0810"]
    for name, group in (("up to 2026-08-07", early), ("from 2026-08-12", late)):
        values = sorted(v for _, v in group)
        print("    %-18s %s" % (name, "  ".join("%.3f" % v for v in values)))
    print("    ⇒ perfect separation on DATE, crossing every oil. Not a channel.")


if __name__ == "__main__":
    main()
