"""The three-oil Spar session of 2026-08-07 (SPEC_capture_quality.md §16.27).

Three supermarket oils, one fill each, three re-seats each, one evening:

    20260807A  Spar Steirisches Kuerbiskernoel ggA
    20260807B  Spar S-Budget
    20260807C  Spar Premium Steirisches Kuerbiskernoel ggA

The session was not designed as an instrument experiment and produced one anyway. The auto-exposure
landed on TWO values across the evening -- 90 and 104 -- and the split does not follow the oil:

    A/001-003   exposure  90        B/001  exposure 104        C/001-003  exposure 104
                                    B/002-003  exposure  90

⭐ B/001 against B/002+003 is therefore the control §16.24.1 never had: the SAME fill, the SAME
seating, four minutes apart, at BOTH exposures. §16.24.1 concluded from a single run that a changed
exposure does not cancel in `T = S/R`; this pair tests it directly.

⚠ The exposures come from the stdout `CAPTURE-SETTINGS` log Edwin kept, NOT from the PDFs --
`exposure_applied` is still not persisted in `workflow.json` (§16.24.0's ROADMAP item). They are
recovered below from the reference level instead, which separates the two states cleanly (R530 = 127
against 154) and reproduces the log exactly. If that item is ever done, read the header instead.

Run from the spectracsPy repo root:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/spar_three_oils.py
"""
import numpy as np

from all_metrics_table import rowFor
from null_run_series import spectraOf
from settling_sweep import despikedAbsorption, asArrays, plugin, feature, R_Q_620

TRIM = (448.0, 460.0)                       # §7.13's trimmed Soret window
Q = plugin.PB_Q_BAND
WINDOWS = plugin.PB_BASELINE_WINDOWS        # the SHIPPED anchors, 520-540 + 620-630

SESSION = [("A  Spar ggA", "20260807A", 3),
           ("B  Spar S-Budget", "20260807B", 3),
           ("C  Spar Premium", "20260807C", 3),
           # Added after the first three (Edwin, same night, 01:22-01:33): Steirerkraft on the SAME
           # capillary recipe, to test whether the archive's Steirerkraft/Spar gap was the protocol.
           ("D  Steirerkraft", "20260807D", 3)]

# Retail price per litre, recorded at purchase (§16.27.6a). Kept here because "premium" is a second
# variable in the validation study and must not be reconstructed later (ROADMAP PRIO 3a).
PRICE = {"A  Spar ggA": 19.98, "B  Spar S-Budget": 11.98,
         "C  Spar Premium": 35.96, "D  Steirerkraft": 37.96}

# The post-rebuild archive, for scale. Classes from §16.15.1's roster.
ARCHIVE = [("Steirerkraft B", "20270729B", 6, "green"), ("Steirerkraft C", "20270729C", 6, "green"),
           ("Kiendler A", "20260801A", 6, "green"), ("Kiendler B", "20260801B", 2, "green"),
           ("Kiendler C", "20260801C", 2, "green"), ("S-Budget D", "20260731A", 6, "brown")]

# The concentration-free shape statistics, each as a band mean divided by the run's own Soret.
SHAPE = [("480-500", (480.0, 500.0)), ("560-580 Q", (560.0, 580.0)), ("590-610", (590.0, 610.0))]

EXPOSURE_SPLIT = 140.0      # R530 sits at 127 (exposure 90) or 154 (exposure 104); nothing between


def measure(path):
    """Every quantity §16.27 quotes, for one run."""
    shipped = rowFor(path)
    spectrum = despikedAbsorption(path)
    lam, corrected = asArrays(feature.linearBaselineCorrected(spectrum, WINDOWS))
    band = lambda window: float(corrected[(lam >= window[0]) & (lam <= window[1])].mean())
    soret448, qBand = band(TRIM), band(Q)

    nanometers, reference = spectraOf(path, "REFERENCE")
    _, sample = spectraOf(path, "SAMPLE")
    legBand = lambda values, window: float(values[(nanometers >= window[0])
                                                  & (nanometers <= window[1])].mean())
    r530 = legBand(reference, (520.0, 540.0))

    values = {"M base+ped": shipped["M baseline + pedestal"], "M baseline": shipped["M baseline"],
              "M raw": shipped["M raw Soret/Q"], "M448": soret448 / qBand,
              "M448+ped": soret448 / (qBand - R_Q_620),
              "A_Soret": shipped["Soret 440-460"], "A_Q": shipped["Q 560-580"],
              "B_Sor620": shipped["B_Soret far620"], "B_Q620": shipped["B_Q far620"],
              "turbidity": shipped["turbidity 520-540"], "rise/Q amp": shipped["rise/Q amp"],
              "R530": r530, "exposure": 104 if r530 > EXPOSURE_SPLIT else 90}
    values.update({name: band(window) / soret448 for name, window in SHAPE})
    values["legs"] = ([legBand(reference, w) for _, w in LEG_BANDS],
                      [legBand(sample, w) for _, w in LEG_BANDS])
    return values


LEG_BANDS = [("450", (448.0, 460.0)), ("490", (480.0, 500.0)), ("530", (520.0, 540.0)),
             ("570", (560.0, 580.0)), ("610", (600.0, 615.0)), ("625", (620.0, 630.0))]


def load(sets):
    return {label: [measure("%s/%03d.pdf" % (folder, i)) for i in range(1, count + 1)]
            for label, folder, count, *_ in sets}


def mean(runs, key):
    return float(np.mean([r[key] for r in runs]))


def sd(runs, key):
    return float(np.std([r[key] for r in runs], ddof=1)) if len(runs) > 1 else 0.0


def cohensD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("inf")


# ------------------------------------------------------------------ §16.27.0
def perRun(session):
    keys = ["M base+ped", "M baseline", "M raw", "M448", "M448+ped",
            "A_Soret", "A_Q", "B_Sor620", "B_Q620", "turbidity", "R530"]
    print("=== 16.27.0  PER RUN, with the AE exposure alongside")
    print("%-18s %-5s %4s %s" % ("oil", "run", "AE", "".join("%11s" % k for k in keys)))
    print("-" * (30 + 11 * len(keys)))
    for label, runs in session.items():
        for index, run in enumerate(runs, 1):
            print("%-18s %-5s %4d %s" % (label if index == 1 else "", "%03d" % index, run["exposure"],
                                         "".join("%11.4f" % run[k] for k in keys)))
        for tag, function in (("mean", mean), ("sd", sd)):
            print("%-18s %-5s %4s %s" % ("", tag, "",
                                         "".join("%11.4f" % function(runs, k) for k in keys)))
        print()


# ------------------------------------------------------------------ §16.27.1 - §16.27.3
def exposureControl(session):
    """B/001 (exposure 104) against B/002+003 (exposure 90). One fill, four minutes apart."""
    runs = session["B  Spar S-Budget"]
    high, low = runs[0], runs[1:]
    assert high["exposure"] == 104 and all(r["exposure"] == 90 for r in low), "the split moved"

    print("=== 16.27.1  THE EXPOSURE CONTROL — same oil, same fill, both exposures")
    print("%-14s %12s %12s %11s" % ("statistic", "B/001 @104", "B/002-3 @90", "change"))
    for key in ("M base+ped", "M baseline", "M raw", "M448", "M448+ped", "rise/Q amp"):
        loValue = mean(low, key)
        print("%-14s %12.4f %12.4f %+10.2f %%"
              % (key, high[key], loValue, 100.0 * (high[key] - loValue) / abs(loValue)))

    print("\n=== 16.27.2  THE LEG-SCALE TEST (§16.24.1: controls <= 0.5 %, the corrupted run 2.5 %)")
    highR, highS = np.array(high["legs"][0]), np.array(high["legs"][1])
    lowR = np.mean([r["legs"][0] for r in low], axis=0)
    lowS = np.mean([r["legs"][1] for r in low], axis=0)
    print("%-8s %10s %10s %10s %10s %11s" % ("band", "R @104", "R @90", "R ratio", "S ratio", "mismatch"))
    for index, (name, _) in enumerate(LEG_BANDS):
        refRatio, sampleRatio = highR[index] / lowR[index], highS[index] / lowS[index]
        print("%-8s %10.2f %10.2f %10.4f %10.4f %10.2f %%"
              % (name, highR[index], lowR[index], refRatio, sampleRatio,
                 100.0 * (sampleRatio / refRatio - 1.0)))
    refRatio, sampleRatio = (highR / lowR).mean(), (highS / lowS).mean()
    print("   mean R ratio %.4f   mean S ratio %.4f   LEG-SCALE MISMATCH %.2f %%"
          % (refRatio, sampleRatio, 100.0 * (sampleRatio / refRatio - 1.0)))
    print("   exposure ratio 104/90 = %.4f   observed reference scaling = %.4f   => decode is not "
          "pow2.2 by %+.1f %%" % (104 / 90, refRatio, 100.0 * (refRatio / (104 / 90) - 1.0)))


# ------------------------------------------------------------------ §16.27.4
def shapeAudit(session):
    """Which shape statistics survive the state change, and which are swamped by it.

    The state effect is measured on B (one fill, both exposures); the gap is A - C, which is split
    exactly along the same two states. A statistic whose state effect exceeds the gap it is being
    asked to carry cannot be used to compare A with C, whatever it says.
    """
    b = session["B  Spar S-Budget"]
    high, low = b[0], b[1:]
    a, c = session["A  Spar ggA"], session["C  Spar Premium"]

    print("\n=== 16.27.4  SHAPE STATISTICS — state effect against the gap each must carry")
    print("%-14s %10s %10s %11s %13s %s"
          % ("statistic", "A (@90)", "C (@104)", "A-C gap", "state effect", "verdict"))
    for key in ("M448", "480-500", "560-580 Q", "590-610", "rise/Q amp"):
        aValue, cValue = mean(a, key), mean(c, key)
        gap = 100.0 * (aValue - cValue) / abs(cValue)
        state = 100.0 * (high[key] - mean(low, key)) / abs(mean(low, key))
        print("%-14s %10.4f %10.4f %+10.1f %% %+12.1f %%   %s"
              % (key, aValue, cValue, gap, state,
                 "RETIRED — state >= gap" if abs(state) >= abs(gap) else "usable"))


# ------------------------------------------------------------------ §16.27.5 - §16.27.7
def verdicts(session, archive):
    print("\n=== 16.27.5  THE THREE OILS, against the post-rebuild archive")
    print("%-18s %2s %13s %13s %13s %9s %9s"
          % ("fill", "n", "M base+ped", "M448", "A_Q (floor .19)", "B_Q620", "turbidity"))
    for label, runs in list(session.items()) + list(archive.items()):
        print("%-18s %2d %6.3f±%-6.3f %6.3f±%-6.3f %13s %9.4f %9.4f"
              % (label, len(runs), mean(runs, "M base+ped"), sd(runs, "M base+ped"),
                 mean(runs, "M448"), sd(runs, "M448"),
                 "%.4f  %3.0f %%" % (mean(runs, "A_Q"), 100.0 * mean(runs, "A_Q") / 0.19),
                 mean(runs, "B_Q620"), mean(runs, "turbidity")))

    print("\n   effect sizes (Cohen's d)")
    pairs = [("A ggA        vs  B S-Budget", "A  Spar ggA", "B  Spar S-Budget"),
             ("C Premium    vs  B S-Budget", "C  Spar Premium", "B  Spar S-Budget"),
             ("A ggA        vs  C Premium", "A  Spar ggA", "C  Spar Premium")]
    both = dict(session, **archive)
    for name, left, right in pairs:
        print("   %-30s d(M base+ped) %6.2f   d(M448) %6.2f"
              % (name, cohensD([r["M base+ped"] for r in both[left]],
                               [r["M base+ped"] for r in both[right]]),
                 cohensD([r["M448"] for r in both[left]], [r["M448"] for r in both[right]])))

    print("\n=== 16.27.6  THE ggA OILS AGAINST T = 10.6 (M base+ped) and the archive greens")
    greens = ["Steirerkraft B", "Steirerkraft C", "Kiendler A", "Kiendler B", "Kiendler C"]
    pooled = [r["M base+ped"] for label in greens for r in archive[label]]
    print("   archive greens  %.3f - %.3f   (5 fills, 2 oils)"
          % (min(mean(archive[g], "M base+ped") for g in greens),
             max(mean(archive[g], "M base+ped") for g in greens)))
    for label in ("A  Spar ggA", "C  Spar Premium", "B  Spar S-Budget"):
        value = mean(session[label], "M base+ped")
        print("   %-18s %6.3f   %s T = 10.6   %+6.1f %% vs the green mean"
              % (label, value, "BELOW" if value < 10.6 else "above",
                 100.0 * (value - np.mean(pooled)) / np.mean(pooled)))

    print("\n=== 16.27.7  B AGAINST JULY'S S-BUDGET (`20260731A`) — a week, a new fill, a new protocol")
    print("   ⚠ quoted on the LEGACY 600-630 anchor, which is what §16.15 recorded S-Budget D on.")
    legacy = lambda runs: np.mean([rowFor(p)["M 600-630 legacy"] for p in runs])
    print("   2026-08-07 B  %.3f     2026-07-31 S-Budget D  %.3f"
          % (legacy(["20260807B/%03d.pdf" % i for i in (1, 2, 3)]),
             legacy(["20260731A/%03d.pdf" % i for i in range(1, 7)])))


def oneProtocol(session):
    """§16.27.6a — the four fills of this session, all on 2 capillaries / 12 ml, against price.

    This is the comparison the archive could never make: no protocol difference, no session
    difference, one rig, one night. The drift column is what argued the 2/12 ml dose is too thin.
    """
    print("\n=== 16.27.6a  ONE PROTOCOL, ONE NIGHT — greenness against price")
    print("%-18s %8s %16s %11s %11s %13s"
          % ("fill", "EUR/l", "M448", "A_Q (floor)", "drift/run", "560-580/Soret"))
    order = sorted(session, key=lambda label: -mean(session[label], "M448"))
    for label in order:
        runs = session[label]
        values = np.array([r["M448"] for r in runs])
        slope = np.polyfit(np.arange(len(values)), values, 1)[0]
        print("%-18s %8.2f %8.3f ± %-5.3f %6.4f %3.0f %% %+10.1f %% %13.4f"
              % (label, PRICE[label], mean(runs, "M448"), sd(runs, "M448"), mean(runs, "A_Q"),
                 100.0 * mean(runs, "A_Q") / 0.19, 100.0 * slope / values.mean(),
                 mean(runs, "560-580 Q")))

    ranks = lambda values: np.argsort(np.argsort(-np.asarray(values)))
    byMetric = ranks([mean(session[label], "M448") for label in order])
    byPrice = ranks([PRICE[label] for label in order])
    n = len(order)
    rho = 1.0 - 6.0 * float(((byMetric - byPrice) ** 2).sum()) / (n * (n * n - 1))
    print("   Spearman rho(greenness, price) = %+.2f over n = %d  ⚠ n = 4 cannot reach significance"
          % (rho, n))


def fillPairs(session, archive):
    """§16.27.9a — every oil with MORE THAN ONE independent preparation on record.

    ⚠ The archive is not silent on sigma_fill, as §16.27.9 first claimed. It holds three Steirerkraft
    fills, three Kiendler fills and two S-Budget fills. What it does NOT hold is a pair made to test
    repeatability: every one of them also varies the concentration on purpose, and the run counts
    (2-6) cannot separate preparation from seating. Hence PRIO 2b.
    """
    both = dict(session, **archive)
    groups = [("Steirerkraft", [("B 20270729B drops", "Steirerkraft B"),
                                ("C 20270729C drops", "Steirerkraft C"),
                                ("D 20260807D capillary", "D  Steirerkraft")]),
              ("Kiendler", [("A 20260801A", "Kiendler A"), ("B 20260801B", "Kiendler B"),
                            ("C 20260801C", "Kiendler C")]),
              ("S-Budget", [("D 20260731A drops", "S-Budget D"),
                            ("B 20260807B capillary", "B  Spar S-Budget")])]

    print("\n=== 16.27.9a  INDEPENDENT PREPARATIONS OF ONE OIL — what the archive already bounds")
    for oil, fills in groups:
        print("   %s — %d fills" % (oil, len(fills)))
        for label, key in fills:
            runs = both[key]
            print("      %-24s M448 %7.3f ± %-5.3f   A_Q %.4f   (n = %d)"
                  % (label, mean(runs, "M448"), sd(runs, "M448"), mean(runs, "A_Q"), len(runs)))
        for i in range(len(fills)):
            for j in range(i + 1, len(fills)):
                left, right = both[fills[i][1]], both[fills[j][1]]
                a, b = mean(left, "M448"), mean(right, "M448")
                se = np.sqrt(sd(left, "M448") ** 2 / len(left) + sd(right, "M448") ** 2 / len(right))
                print("      %-6s vs %-6s  %+6.3f  (%+5.2f %%)   t = %5.2f%s"
                      % (fills[i][0].split()[0], fills[j][0].split()[0], a - b, 100 * (a - b) / b,
                         (a - b) / se if se else float("nan"),
                         "" if abs(a - b) / se >= 2.0 else "   (not significant)"))
    print("   ⇒ the SAME-SESSION, SAME-RECIPE pairs — the nearest thing to a sigma_fill test — do not")
    print("     reach significance (Steirerkraft B/C t = 0.09, Kiendler B/C t = -1.82). The two pairs")
    print("     that DO (Steirerkraft B/D, Kiendler A/B) each carry a deliberate protocol or")
    print("     concentration change, so neither prices preparation alone.")


def main():
    session, archive = load(SESSION), load(ARCHIVE)
    perRun(session)
    exposureControl(session)
    shapeAudit(session)
    verdicts(session, archive)
    oneProtocol(session)
    fillPairs(session, archive)


if __name__ == "__main__":
    main()
