"""Why did the 2023 oils separate 8x better than the 2026 oils? (SPEC_capability_proof.md §11.4e)

§16.10 left this open: the 2023 set gave d ~ 10-24, the fresh 2026 oils only 2.88, "no explanation yet".

Edwin's hypothesis (2026-07-31): the 2023 oils were BOUGHT IN 2023 and are physically old. §11.4c's dispersion
settles in the BOTTLE just as it does in the cuvette, so three years of shelf life clarifies the oil and it
carries far less turbidity into the dilution.

That is testable, because turbidity is exactly the PEDESTAL - the additive scatter floor under the whole
absorbance curve. It is recoverable without any new measurement, from the two metric variants the plugin
already emits: raw S/Q is compressed by the pedestal, the linear-baseline S/Q is not. With

    raw = (B*q + c) / (q + c)        B = pedestal-free ratio (the baselined metric), c = pedestal

solving for the pedestal relative to the true Q-band signal gives

    c / Q_true = (B - raw) / (raw - 1)

⚠ This also RE-TESTS a claim made and withdrawn the same day: that the discriminating mechanism had "inverted"
between the two eras because the 2026 brown's raw A_Soret exceeds the green's. Comparing UNNORMALISED band means
across preparations at different concentrations is invalid; normalising by Q (which is what the metric does)
shows green leads brown in both eras. The check is printed so the error cannot be repeated silently.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/pedestal_by_vintage.py
"""
import numpy as np

from baseline_variants import cv
from far_anchor_probe import spectra
from metric_bench import feature, plugin
from sciens.spectracs.model.spectral.Spectrum import Spectrum

SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS
REPORT = "measurement_report_oil%s_%03d.pdf"

# Both sessions are PRE-rebuild (the rig rebuild was 2026-07-29), so the mechanical fix cannot explain the
# difference between them. The variable under test is the OIL's shelf age, not the rig.
FILLS = [("K green", "2023", [REPORT % ("K", i) for i in range(1, 5)]),
         ("L green", "2023", [REPORT % ("L", i) for i in range(1, 5)]),
         ("M brown", "2023", [REPORT % ("M", i) for i in range(1, 5)]),
         ("N brown", "2023", [REPORT % ("N", i) for i in range(1, 5)]),
         ("B green", "2026", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
         ("E green", "2026", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
         ("C brown", "2026", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
         ("D brown", "2026", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]


def bands(path):
    """(rawSoret, rawQ, baselinedSoret, baselinedQ) for one run."""
    values = spectra(path)["ABSORPTION"]
    source = Spectrum()
    source.valuesByNanometers = dict(values)
    corrected = feature.linearBaselineCorrected(source, WINDOWS)

    lam = np.array(sorted(values))
    raw = np.array([values[k] for k in lam])
    fixed = np.array([corrected.valuesByNanometers[k] for k in lam])

    def mean(data, window):
        return float(data[(lam >= window[0]) & (lam <= window[1])].mean())

    return mean(raw, SORET), mean(raw, Q), mean(fixed, SORET), mean(fixed, Q)


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    loaded = []
    for name, vintage, paths in FILLS:
        rows = np.array([bands(p) for p in paths])
        rawRatios = rows[:, 0] / rows[:, 1]
        baseRatios = rows[:, 2] / rows[:, 3]
        rawMean, baseMean = float(rawRatios.mean()), float(baseRatios.mean())
        pedestal = (baseMean - rawMean) / (rawMean - 1)
        loaded.append((name, vintage, rows.mean(axis=0), rawMean, baseMean, pedestal,
                       cv(rawRatios), cv(baseRatios)))

    print("=== THE PEDESTAL, per fill  (c / Q_true — the scatter floor relative to the pigment signal)")
    print("   %-10s %5s %10s %10s %11s %10s %10s" % (
        "fill", "oil", "S/Q raw", "S/Q base", "PEDESTAL", "raw CV%", "base CV%"))
    print("   " + "-" * 72)
    for name, vintage, _, rawMean, baseMean, pedestal, rawCv, baseCv in loaded:
        print("   %-10s %5s %10.3f %10.3f %11.2f %10.2f %10.2f" % (
            name, vintage, rawMean, baseMean, pedestal, rawCv, baseCv))
    print()

    for vintage in ("2023", "2026"):
        group = [row for row in loaded if row[1] == vintage]
        pedestals = np.array([row[5] for row in group])
        print("   %s oils   pedestal %.2f ± %.2f   raw CV %.2f %%   baselined CV %.2f %%" % (
            vintage, pedestals.mean(), pedestals.std(ddof=1),
            np.mean([row[6] for row in group]), np.mean([row[7] for row in group])))
    older = np.mean([row[5] for row in loaded if row[1] == "2023"])
    fresh = np.mean([row[5] for row in loaded if row[1] == "2026"])
    print("   ⇒ the FRESH oils carry %.1f× the pedestal" % (fresh / older))
    pedestals = np.array([row[5] for row in loaded])
    rawCvs = np.array([row[6] for row in loaded])
    print("   correlation pedestal vs raw CV, all %d fills: r = %.2f" % (len(loaded), np.corrcoef(pedestals, rawCvs)[0, 1]))
    print()

    # ---------------------------------------------------------------- the withdrawn "inversion"
    print("=== ⛔ THE WITHDRAWN 'MECHANISM INVERSION' — why unnormalised band means MISLEAD")
    print("   Raw A_Soret suggests the 2026 brown out-absorbs the green. It does not: the 2026 brown")
    print("   is simply more concentrated, which lifts ALL its band means together.\n")
    print("   %-6s %-7s %11s %8s   %13s %10s   %12s" % (
        "oils", "class", "A_Soret raw", "A_Q raw", "A_Soret BASE", "A_Q BASE", "Soret/Q BASE"))
    print("   " + "-" * 80)
    ratios = {}
    for vintage in ("2023", "2026"):
        for label in ("green", "brown"):
            group = [row for row in loaded if row[1] == vintage and label in row[0]]
            means = np.mean([row[2] for row in group], axis=0)
            ratios[(vintage, label)] = means[2] / means[3]
            print("   %-6s %-7s %11.3f %8.3f   %13.3f %10.3f   %12.2f" % (
                vintage, label, means[0], means[1], means[2], means[3], means[2] / means[3]))
    print()
    for vintage in ("2023", "2026"):
        print("   %s oils   green ÷ brown on Soret/Q = %.2f×   <- green leads in BOTH eras" % (
            vintage, ratios[(vintage, "green")] / ratios[(vintage, "brown")]))


if __name__ == "__main__":
    main()
