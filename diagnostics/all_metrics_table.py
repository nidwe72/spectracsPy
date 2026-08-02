"""EVERY metric, for EVERY run, of the 2026-07-29 and 2026-08-01 sessions. (Edwin's request 2026-08-02)

One row per report, so the raw record can be inspected directly rather than through set means. Covers
the SHIPPED metric set — both evaluation tabs — plus the analysis quantities this spec's recent work
introduced, plus the PROPOSED pedestal-corrected index of `DOC_pedestal_correction.md`.

Everything is computed through the SHIPPED code paths (`DevSpectralPlugin.__computeMetrics`,
`SpectrumFeatureUtil`), including the legacy tab's metrics, so this table is what the app would show.

    session      folder        oil                runs
    2026-07-29   20270729A     Steirerkraft, 24 h-aged fill      3
    2026-07-29   20270729B     Steirerkraft, fill 1              6
    2026-07-29   20270729C     Steirerkraft, fill 2              6
    2026-08-01   20260801A     Kiendler, 18 ml + 6 drops         6
    2026-08-01   20260801B     Kiendler, +1 drop into 14 ml      2
    2026-08-01   20260801C     Kiendler, fresh 18 ml + 7 drops   2

⚠ The corrected index uses ONE constant, r_Q = -0.0246 A, fitted on Kiendler. Applying it to
Steirerkraft assumes r_Q is universal — `DOC_pedestal_correction.md` chapter 10 shows that assumption
is NOT established. The column is exploratory, not a verdict.

Prints five grouped tables (the full set is too wide for one) and writes the whole thing as CSV to
    spectracs-references/tmp/all_metrics_20260729_20260801.csv

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/all_metrics_table.py
"""
import csv
import json
import os

import numpy as np
from pypdf import PdfReader

from settling_sweep import BASE, measure, despikedAbsorption
from metric_walkthrough import fittedLine
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

plugin, feature = DevSpectralPlugin(), SpectrumFeatureUtil()
R_Q = -0.0246                                     # DOC_pedestal_correction.md §6, Kiendler run-level fit

SETS = [
    ("2026-07-29", "20270729A", "Steirerkraft", "24 h-aged fill", 3),
    ("2026-07-29", "20270729B", "Steirerkraft", "fill 1", 6),
    ("2026-07-29", "20270729C", "Steirerkraft", "fill 2", 6),
    ("2026-08-01", "20260801A", "Kiendler", "18 ml + 6 drops", 6),
    ("2026-08-01", "20260801B", "Kiendler", "+1 drop into 14 ml", 2),
    ("2026-08-01", "20260801C", "Kiendler", "fresh 18 ml + 7 drops", 2),
]


def role(path, name):
    """Any spectrum role out of the report's embedded workflow JSON, as a Spectrum."""
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            raw = (step.get("spectra") or {}).get(name)
            if raw is not None:
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(k): float(v) for k, v in
                                               raw.get("valuesByNanometers", raw).items()}
                return spectrum
    return None


def band(spectrum, low, high):
    values = [v for nm, v in spectrum.valuesByNanometers.items() if low <= nm <= high]
    return float(np.mean(values)) if values else float("nan")


def rowFor(path):
    """Every metric for one run."""
    quantities = measure(path)                              # the analysis quantities
    despiked = despikedAbsorption(path)
    reference = role(path, "REFERENCE")
    legacy = plugin._DevSpectralPlugin__computeMetrics(despiked, reference) or {}
    slope, _ = fittedLine(despiked)

    soret, qBand = quantities["A_Soret raw"], quantities["A_Q raw"]
    clarity = band(despiked, *plugin.GREEN_BAND)
    bSoret, bQ = quantities["A_Soret linear"], quantities["A_Q linear"]

    rise = band(despiked, 620, 630) - band(despiked, 600, 610)
    amplitude = band(despiked, 571, 573) - band(despiked, 549, 551)

    return {
        "Soret 440-460": soret,
        "Q 560-580": qBand,
        "Clarity 510-540": clarity,
        "turbidity 520-540": quantities["A_near 520-540"],
        "far 600-630": quantities["A_far 600-630"],
        "B_Soret": bSoret,
        "B_Q": bQ,
        "baseline slope /100nm": slope * 100.0,
        "Pigment ratio raw": soret / qBand,
        "Pigment ratio clarity": soret / clarity,
        "M shipped": quantities["S/Q linear base"],
        "M corrected": bSoret / (bQ - R_Q),
        "inflation %": 100.0 * (-R_Q / bQ),
        "Greenness G": legacy.get("gGreen"),
        "Pigment D_Q": legacy.get("dQ"),
        "A_blue": legacy.get("aBlue"),
        "A_green": legacy.get("aGreen"),
        "browning A_blue/A_green": legacy.get("browning"),
        "G' D_Q/A_blue": legacy.get("gBlue"),
        "rise/Q amp": rise / amplitude,
    }


GROUPS = [
    ("RAW BANDS — de-spiked absorbance, before any baseline",
     [("Soret 440-460", "Soret"), ("Q 560-580", "Q"), ("Clarity 510-540", "Clarity"),
      ("turbidity 520-540", "turbidity"), ("far 600-630", "far")]),
    ("AFTER THE LINEAR BASELINE",
     [("B_Soret", "B_Soret"), ("B_Q", "B_Q"), ("baseline slope /100nm", "slope/100nm")]),
    ("THE RATIOS — including the shipped verdict and the proposed correction",
     [("Pigment ratio raw", "S/Q raw"), ("Pigment ratio clarity", "S/clarity"),
      ("M shipped", "M SHIPPED"), ("M corrected", "M corrected"), ("inflation %", "inflation%")]),
    ("LEGACY TAB",
     [("Greenness G", "Greenness G"), ("Pigment D_Q", "D_Q"), ("A_blue", "A_blue"),
      ("A_green", "A_green"), ("browning A_blue/A_green", "browning"), ("G' D_Q/A_blue", "G'")]),
    ("SHAPE — pedestal-immune by construction (§16.13.9)",
     [("rise/Q amp", "rise/Q amp")]),
]


def summarise(rows, folder, columns, cell):
    """mean and SD footer for one folder, so a set can be read without a calculator."""
    group = [r for r in rows if r["folder"] == folder]
    for label, function in (("mean", np.mean), ("sd", lambda v: np.std(v, ddof=1))):
        cells = []
        for key, _ in columns:
            values = [r[key] for r in group if r[key] is not None]
            cells.append(cell(function(values) if len(values) > 1 else None))
        print("   %-11s %-4s %-13s %s" % ("", label, "", "".join(cells)))
    print()


def main():
    print(__doc__.split("    session")[0].strip())
    print()

    rows = []
    for session, folder, oil, recipe, count in SETS:
        for index in range(1, count + 1):
            path = "%s/%03d.pdf" % (folder, index)
            values = rowFor(path)
            values.update({"session": session, "folder": folder, "oil": oil,
                           "prep": recipe, "run": "%03d" % index})
            rows.append(values)

    def cell(value):
        return "%12s" % ("—" if value is None else "%.4f" % value)

    for title, columns in GROUPS:
        print("=== %s" % title)
        print("   %-11s %-4s %-13s %s"
              % ("folder", "run", "oil", "".join("%12s" % short for _, short in columns)))
        print("   " + "-" * (32 + 12 * len(columns)))
        lastFolder = None
        for values in rows:
            if lastFolder is not None and values["folder"] != lastFolder:
                summarise(rows, lastFolder, columns, cell)
            lastFolder = values["folder"]
            print("   %-11s %-4s %-13s %s" % (values["folder"], values["run"], values["oil"],
                                              "".join(cell(values[key]) for key, _ in columns)))
        summarise(rows, lastFolder, columns, cell)
        print()

    fields = (["session", "folder", "oil", "prep", "run"]
              + [key for _, cs in GROUPS for key, _ in cs])
    out = os.path.join(BASE, "all_metrics_20260729_20260801.csv")
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for values in rows:
            writer.writerow({k: values[k] for k in fields})
    print("CSV written: %s   (%d runs x %d metrics)" % (out, len(rows), len(fields) - 5))


if __name__ == "__main__":
    main()
