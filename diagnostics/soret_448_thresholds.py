"""DERIVE the two Roast-Ampel thresholds on the trimmed 448-460 Soret window (SPEC_soret_448_trim.md §5, C2).

The trim moves the scale: `B_Soret` falls by roughly a third, so both gauges' numbers move with it. The
tempting shortcut -- multiply T by §7.13's 0.674 -- is WRONG, and the archive says so: the measured
`M448 / M440` factor is CLASS-DEPENDENT (0.642 on the brown fill, 0.672 on the green ones, §16.27's table),
which is precisely why the trim improves separation. A single multiplier sits above every observed factor and
would push the line toward brown, silently reclassifying borderline greens.

So this derives instead:
  * per-run `M448` (620-630 anchor, no correction)     -> RoastFar620GaugeView's scale
  * per-run `M448 + pedestal` (same, r_Q added back)   -> RoastPedestalGaugeView's scale
  * per class: mean +/- sd, min green / max brown, the EMPTY CORRIDOR, Cohen's d
  * the corridor-midpoint threshold, and a CLASS-CHANGE CHECK against the shipped 440-scale thresholds:
    no archived run may change class, or the trim has quietly moved a verdict.

⚠ The window and r_Q are arguments, NOT imports of the live plugin constants (§18 duck #14). A derivation
script that silently follows a moving constant is how a threshold gets mis-attributed to the wrong window.

⚠ SCOPE: only the POST-REBUILD archive (2026-07-29 on, §16.11) -- the only data captured under today's optics.
The Spar oils of §16.27 are NOT part of the green/brown corpus: both ggA fills read BELOW the shipped green
threshold on the 440 scale (§16.27.6), which is a threshold question the validation study owns. They are
printed as UNCLASSED context so their position on the new scale is visible without steering the line.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/soret_448_thresholds.py
"""
import numpy as np

from settling_sweep import despikedAbsorption, asArrays, plugin, feature

# --- explicit parameters (never read the live plugin constants -- see the header) --------------------------
SORET_440 = (440.0, 460.0)          # the legacy window every shipped threshold was derived on
SORET_448 = (448.0, 460.0)          # the trim
Q_BAND = (560.0, 580.0)
WINDOWS = ((520.0, 540.0), (620.0, 630.0))    # the shipped 620-630 far anchor (§16.20)
R_Q = -0.0184                       # that anchor's pedestal residual, as SHIPPED (D-rq keeps it for now)

# The thresholds in force on the 440 scale, for the class-change check.
T_PEDESTAL_440 = 10.6
T_FAR620_440 = 12.5

# Post-rebuild fills, §16.15's roster. The 2027 in three folder names is a rig clock typo, kept as-is.
SETS = [("20270729B", "Steirerkraft B", "green", 6),
        ("20270729C", "Steirerkraft C", "green", 6),
        ("20260801A", "Kiendler A", "green", 6),
        ("20260801B", "Kiendler B", "green", 2),
        ("20260801C", "Kiendler C", "green", 2),
        ("20260804A", "Steirerkraft half-strength", "green", 6),
        ("20260731A", "S-Budget (series D)", "brown", 6),
        ("20260807B", "Spar S-Budget (capillary)", "brown", 3),
        ("20270729A_aged24h", "Steirerkraft A aged 24 h", "aged", 3),
        ("20260807A", "Spar ggA", "context", 3),
        ("20260807C", "Spar Premium ggA", "context", 3),
        ("20260807D", "Steirerkraft (capillary)", "context", 3)]

# §16.20.4's own derivation corpus — the 18 runs BOTH shipped thresholds were set from. Everything else in
# SETS is a robustness check or context, never an input to the line.
PRIMARY_GREEN = ("Steirerkraft B", "Steirerkraft C")
PRIMARY_BROWN = ("S-Budget (series D)",)


def metrics(path, soretWindow):
    """(M, M+pedestal) for one run on `soretWindow`, with the shipped anchors."""
    corrected = feature.linearBaselineCorrected(despikedAbsorption(path), WINDOWS)
    lam, values = asArrays(corrected)

    def band(window):
        return float(values[(lam >= window[0]) & (lam <= window[1])].mean())

    soret, qBand = band(soretWindow), band(Q_BAND)
    return soret / qBand, soret / (qBand - R_Q)


def cohensD(a, b):
    a, b = np.array(a), np.array(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled


def corridor(green, brown, name):
    """Print the class statistics and return the midpoint threshold."""
    green, brown = np.array(green), np.array(brown)
    low, high = green.min(), brown.max()
    threshold = round((low + high) / 2.0, 1)
    print("\n=== %s" % name)
    print("  green  n=%2d  %8.3f +/- %.3f   span %8.3f .. %8.3f" % (
        len(green), green.mean(), green.std(ddof=1), green.min(), green.max()))
    print("  brown  n=%2d  %8.3f +/- %.3f   span %8.3f .. %8.3f" % (
        len(brown), brown.mean(), brown.std(ddof=1), brown.min(), brown.max()))
    print("  Cohen's d %.2f   EMPTY CORRIDOR %.3f .. %.3f (width %.3f)" % (
        cohensD(green, brown), high, low, low - high))
    print("  ⭐ midpoint threshold  T = %.1f    margins: green +%.2f sigma   brown +%.2f sigma" % (
        threshold, (green.mean() - threshold) / green.std(ddof=1),
        (threshold - brown.mean()) / brown.std(ddof=1)))
    return threshold


def main():
    print("Soret %s (was %s)   Q %s   anchors %s   r_Q %+.4f\n"
          % (SORET_448, SORET_440, Q_BAND, WINDOWS, R_Q))

    rows = []
    print("=== PER RUN — the 448 scale, and the 440 scale it replaces")
    print("%-28s %-8s %-4s %9s %9s %9s %9s" % (
        "fill", "class", "run", "M448", "M448+ped", "M440", "M440+ped"))
    print("-" * 82)
    for folder, label, klass, count in SETS:
        for index in range(1, count + 1):
            path = "%s/%03d.pdf" % (folder, index)
            far448, ped448 = metrics(path, SORET_448)
            far440, ped440 = metrics(path, SORET_440)
            rows.append({"fill": label, "class": klass, "far448": far448, "ped448": ped448,
                         "far440": far440, "ped440": ped440})
            print("%-28s %-8s %-4s %9.3f %9.3f %9.3f %9.3f" % (
                label if index == 1 else "", klass if index == 1 else "", "%03d" % index,
                far448, ped448, far440, ped440))

    def pick(key, fills=None, klass=None):
        return [row[key] for row in rows
                if (fills is None or row["fill"] in fills) and (klass is None or row["class"] == klass)]

    # ⭐ DERIVE ON §16.20.4's OWN CORPUS — Steirerkraft B+C against S-Budget D, the exact 18 runs both shipped
    # thresholds were set from. Deriving on a WIDER corpus would change two things at once (the window AND the
    # population), and the whole point of this run is to isolate the window.
    print("\n" + "=" * 82)
    print("PRIMARY — derived on §16.20.4's corpus (Steirerkraft B+C vs S-Budget D), window the only change")
    print("=" * 82)
    pedestalThreshold = corridor(pick("ped448", PRIMARY_GREEN), pick("ped448", PRIMARY_BROWN),
                                 "RoastPedestalGaugeView — M448 + pedestal (the PRIMARY verdict)")
    far620Threshold = corridor(pick("far448", PRIMARY_GREEN), pick("far448", PRIMARY_BROWN),
                               "RoastFar620GaugeView — M448, no correction")

    # And the same two lines against EVERYTHING post-rebuild — a robustness check, not a second derivation.
    # It folds in Kiendler (incl. the thinnest fill on record) and the deliberate half-strength dilution, so a
    # threshold that survives here is not resting on two fills.
    print("\n" + "=" * 82)
    print("ROBUSTNESS — the same thresholds against the FULL post-rebuild green/brown corpus")
    print("=" * 82)
    for key, threshold, name in ((("ped448"), pedestalThreshold, "M448 + pedestal"),
                                 (("far448"), far620Threshold, "M448")):
        green, brown = np.array(pick(key, klass="green")), np.array(pick(key, klass="brown"))
        print("  %-16s green n=%2d min %7.3f (T %.1f, clears by %+.3f)   brown n=%2d max %7.3f (%+.3f)" % (
            name, len(green), green.min(), threshold, green.min() - threshold,
            len(brown), brown.max(), threshold - brown.max()))

    # --- CLASS-CHANGE CHECK (SPEC_soret_448_trim.md §5 step 3) ---------------------------------------------
    # ⚠ The gate as first written ("no archived run may change class") is the WRONG gate, and this run is what
    # showed it. The 440-scale pedestal threshold was INHERITED, not derived (§16.10.17d), so it does not agree
    # with its own corridor — meaning any correctly derived line must disagree with it somewhere. What the trim
    # must not do is move a run of the DERIVATION CORPUS; everything else is a threshold question the
    # validation study owns, and is reported per run so the moves are enumerated rather than absorbed.
    print("\n=== CLASS-CHANGE CHECK — 440 scale (T %.1f / %.1f) vs 448 scale (T %.1f / %.1f)"
          % (T_PEDESTAL_440, T_FAR620_440, pedestalThreshold, far620Threshold))
    print("%-28s %-4s %-22s %-22s %s" % ("fill", "run", "pedestal 440 -> 448", "far620 440 -> 448", "note"))
    print("-" * 100)
    corpusChanged, otherChanged = 0, 0
    for index, row in enumerate(rows):
        oldPed, newPed = row["ped440"] >= T_PEDESTAL_440, row["ped448"] >= pedestalThreshold
        oldFar, newFar = row["far440"] >= T_FAR620_440, row["far448"] >= far620Threshold
        flipped = (oldPed != newPed) or (oldFar != newFar)
        inCorpus = row["fill"] in PRIMARY_GREEN + PRIMARY_BROWN
        if flipped:
            corpusChanged += 1 if inCorpus else 0
            otherChanged += 0 if inCorpus else 1
            print("%-28s %-4s %-22s %-22s %s" % (
                row["fill"], "#%d" % (index + 1), "%s -> %s" % (_verdict(oldPed), _verdict(newPed)),
                "%s -> %s" % (_verdict(oldFar), _verdict(newFar)),
                "⛔ IN THE DERIVATION CORPUS" if inCorpus else "outside the corpus"))
    print("\n  %s  derivation corpus (n=18): %d runs change class"
          % ("⛔ FAIL —" if corpusChanged else "⭐ PASS —", corpusChanged))
    print("  %s  everything else  (n=%d): %d runs change class — enumerated above, each one a threshold"
          % ("⚠" if otherChanged else "⭐", len(rows) - 18, otherChanged))
    print("       question the validation study owns (§16.27.6 'the scale is graded, the threshold is binary')")

    print("\n=== the aged fill (§16.11.16 — a BROWNER OIL, not a noisier one), for reference only")
    for row in rows:
        if row["class"] == "aged":
            print("  M448 %8.3f   M448+ped %8.3f   -> %s / %s" % (
                row["far448"], row["ped448"],
                _verdict(row["ped448"] >= pedestalThreshold), _verdict(row["far448"] >= far620Threshold)))


def _verdict(isGreen):
    return "green" if isGreen else "brown"


if __name__ == "__main__":
    main()
