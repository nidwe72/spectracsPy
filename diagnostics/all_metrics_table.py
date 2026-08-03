"""EVERY metric, for EVERY run, of the 2026-07-29 and 2026-08-01 sessions. (Edwin's request 2026-08-02)

One row per report, so the raw record can be inspected directly rather than through set means. The
VERDICT BLOCK is exactly the THREE METRICS THE BENCH SHOWS, in the order it shows them, all on the
shipped 620-630 far anchor (§16.20, adopted 2026-08-03):

    M baseline + pedestal   B_Soret / (B_Q - r_Q)   `Verdict · baseline + pedestal`, T = 10.6
                            r_Q = -0.0184           RoastPedestalGaugeView -- the PRIMARY index, and the
                                                    one the LIMS publish badge carries
    M baseline              B_Soret / B_Q           `Verdict · baseline`, T = 12.5
                                                    RoastFar620GaugeView
    M raw Soret/Q           A_Soret / A_Q           `Verdict · raw Soret/Q (no verdict)` -- value only,
                            no baseline at all      no gauge, no threshold

⚠ THE THREE ARE ON THREE DIFFERENT SCALES. Compare a column against itself across runs; compare the
three only by their VERDICTS, never by their numbers. Each threshold belongs to its own column.

⚠ EACH INDEX MUST BE PAIRED WITH ITS OWN r_Q. Move the anchor and the residual moves with it; a
600-630 band divided by a 620-630 residual is a category error, not a variant.

⚠ `r_Q` = -0.0184 was fitted on Kiendler alone. Applying it to another oil assumes r_Q is universal --
`DOC_pedestal_correction.md` chapter 10 shows that assumption is NOT established.

WHAT WAS REMOVED FROM THESE TABLES, and why (2026-08-03, Edwin: "only the 3 metrics actually in use"):
  * the 615-630 columns (`M far615`, its corrected twin, and its bands) -- an intermediate proposal that
    NEVER SHIPPED and has no threshold, so no reading could ever be taken off it. Still reproducible on
    demand from `far_anchor_sweep.py`, which sweeps arbitrary windows.
  * `M 600-630 legacy corrected` -- the legacy anchor's pedestal-corrected index. `all_metrics_archive.py`'s
    dilution check computes its own copy internally, so nothing depended on the column.
  * `M 600-630 legacy` itself is KEPT, but demoted out of the verdict block into its own group. §16.21's
    acetone protocol requires it by name: an acetone run must be read on BOTH anchors so that "the solvent
    moved" can be told apart from "the window is too narrow".

Everything is computed through the SHIPPED code paths (`DevSpectralPlugin.__computeMetrics`,
`SpectrumFeatureUtil`), including the legacy tab's metrics, so this table is what the app would show.

    session      folder        oil                runs
    2026-07-29   20270729A_aged24h   Steirerkraft, 24 h-aged fill   3  ⚠
    2026-07-29   20270729B     Steirerkraft, fill 1              6
    2026-07-29   20270729C     Steirerkraft, fill 2              6
    2026-08-01   20260801A     Kiendler, 18 ml + 6 drops         6
    2026-08-01   20260801B     Kiendler, +1 drop into 14 ml      2
    2026-08-01   20260801C     Kiendler, fresh 18 ml + 7 drops   2

⚠ THE AGED SET IS NOT A LESS-PRECISE GREEN FILL -- IT IS A BROWNER OIL (diagnosed 2026-08-03; the folder
was renamed from `20270729A` on the same day so this cannot be read past). It was excluded from every
scoring basis in §16 for its precision (CV 4.95 % against 2.9 %), but that was never the whole story:

  * dilution does NOT explain it. B and C are the same fresh oil at two concentrations and give
    s = -0.049; propagating that to A's concentration predicts 15.96 and A reads 12.61 -- and dilution
    pushes the index UP, not down.
  * neither does the baseline. `rise/Q amp` is a ratio of two DIFFERENCES, so offset, slope and
    concentration all cancel (§16.13.9), and A sits 27 % below C on it.
  * per unit Soret the Qy rise is DOWN 17 % while the 572 nm feature is UP 14 %. Opposite signs mean
    conversion, not loss -- intact pigment turning into the degradation product (§7.4 of
    `DOC_metric_algebra.md` reads 572 as protopheophytin).

  => all three runs are classified TOO BROWN by the primary metric, and the set read brown on the legacy
     metric too (10.357 against that anchor's T = 10.6). "Measure within the hour" is a VERDICT
     requirement, not a precision one. The decay rate is unmeasured: one point at 24 h, n = 3, and
     confounded with concentration.

ℹ `M clean-anchor` (the 607-line-excision diagnostic of §16.19.3a) has been RETIRED from these tables.
It answered its question — excising the lamp line makes r_Q WORSE, not better — and the answer is
recorded in §16.19.3a and reproduced by `pedestal_correction.py`'s anchor-variant sweep.

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
# ⭐ The SHIPPED residual. It belongs to the 620-630 anchor and to no other (§16.20.2, Kiendler
# run-level straight-line fit). The legacy anchor's own -0.0246 is no longer needed here: the only
# column that used it, `M 600-630 legacy corrected`, was dropped on 2026-08-03. `rq_stability.py`
# and `all_metrics_archive.py`'s dilution check still carry their own copy, correctly paired.
R_Q_620 = -0.0184

SETS = [
    ("2026-07-29", "20270729A_aged24h", "Steirerkraft", "24 h-aged fill", 3),
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
        "far 620-630": quantities["A_far 620-630"],
        "B_Soret far620": quantities["A_Soret far620"],
        "B_Q far620": quantities["A_Q far620"],
        "baseline slope /100nm": slope * 100.0,
        "Pigment ratio clarity": soret / clarity,
        # ⭐ the three the bench shows, in the order it shows them
        "M baseline + pedestal": quantities["A_Soret far620"] / (quantities["A_Q far620"] - R_Q_620),
        "M baseline": quantities["S/Q far620"],
        "M raw Soret/Q": soret / qBand,
        # the inflation the pedestal correction undoes, on the SHIPPED anchor's own B_Q
        "inflation %": 100.0 * (-R_Q_620 / quantities["A_Q far620"]),
        "M 600-630 legacy": quantities["S/Q linear base"],
        "Greenness G": legacy.get("gGreen"),
        "Pigment D_Q": legacy.get("dQ"),
        "A_blue": legacy.get("aBlue"),
        "A_green": legacy.get("aGreen"),
        "browning A_blue/A_green": legacy.get("browning"),
        "G' D_Q/A_blue": legacy.get("gBlue"),
        "rise/Q amp": rise / amplitude,
    }


GROUPS = [
    # ⭐ THE VERDICT NUMBERS COME FIRST — in the printed tables and, because the CSV field order is
    # built from this list, in the CSV too. Since 2026-08-03 this block is EXACTLY the three metrics the
    # bench shows, in the bench's own order; the competing anchors were demoted or dropped (see the
    # module docstring for what went and why).
    ("⭐ THE VERDICT — the three metrics the bench shows, in its own order (620-630 anchor)",
     [("M baseline + pedestal", "M base+ped"), ("M baseline", "M baseline"),
      ("M raw Soret/Q", "M raw"), ("inflation %", "inflation%")]),
    ("RAW BANDS — de-spiked absorbance, before any baseline",
     [("Soret 440-460", "Soret"), ("Q 560-580", "Q"), ("Clarity 510-540", "Clarity"),
      ("turbidity 520-540", "turbidity"), ("far 620-630", "far 620"), ("far 600-630", "far 600")]),
    ("AFTER THE LINEAR BASELINE — the shipped 620-630 anchor first, then the legacy 600-630 one",
     [("B_Soret far620", "B_Sor 620"), ("B_Q far620", "B_Q 620"),
      ("B_Soret", "B_Sor 600"), ("B_Q", "B_Q 600"),
      ("baseline slope /100nm", "slope/100nm")]),
    # KEPT for one named reason: §16.21's acetone protocol reads every acetone run on BOTH anchors, so
    # that a solvent-induced band shift can be told apart from a window that is simply too narrow.
    ("THE SUPERSEDED 600-630 ANCHOR — kept for §16.21's acetone protocol, NOT a verdict",
     [("M 600-630 legacy", "M 600-630")]),
    ("OTHER RATIOS — computed, not shown by the bench",
     [("Pigment ratio clarity", "S/clarity")]),
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
        print("   %-18s %-4s %-13s %s" % ("", label, "", "".join(cells)))
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
        print("   %-18s %-4s %-13s %s"
              % ("folder", "run", "oil", "".join("%12s" % short for _, short in columns)))
        print("   " + "-" * (32 + 12 * len(columns)))
        lastFolder = None
        for values in rows:
            if lastFolder is not None and values["folder"] != lastFolder:
                summarise(rows, lastFolder, columns, cell)
            lastFolder = values["folder"]
            print("   %-18s %-4s %-13s %s" % (values["folder"], values["run"], values["oil"],
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
