"""R2 — scoring. Reads ONLY the JSON feature table; never touches a PDF.

(docs/SPEC_metric_research.md §6 — the evaluation protocol.)

Every candidate gets the same three scores, and S1 and S2 are always reported TOGETHER because a
metric can be perfectly dilution-invariant by being blind (§6.2 — a constant scores S1 = 0).

  S1  dilution invariance  -- spread of the SET means within one oil, as % of that oil's mean.
                             Kiendler has 3 strengths (B_Q spans x1.46), Steirerkraft 2 (x1.08).
                             ⚠ green-only: S-Budget exists at one strength (§2.1).
  S2  class separation     -- Cohen's d, {Kiendler, Steirerkraft} vs S-Budget. Q6 (answered
                             2026-08-04) makes green-vs-brown the target; the incumbent scores 6.91.
  S3  re-seating stability -- within-set CV, worst set. S-Budget's 6 re-seats of one fill are the
                             cleanest probe on the rig.

⚠ §3.4 THE SESSION CONFOUND IS NOT SCORED AND CANNOT BE. Each oil is one evening, so every S2 here is
also a between-evening difference. R0b (postponed) is the only thing that separates them.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_scores.py
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "out", "metric_features.json")

GREENS, BROWN = ("Kiendler", "Steirerkraft"), "S-Budget"

# feature key -> (candidate id, needs a baseline?, one-line description)
CANDIDATES = [
    ("M__shipped560_580", "C11", "yes", "the INCUMBENT — B_Soret/B_Q, shipped window"),
    ("M_corrected__shipped560_580", "C12", "yes", "incumbent + pedestal correction"),
    ("M__centred566_582", "C11b", "yes", "incumbent, Q window re-centred on the 574 nm peak"),
    ("M__wide564_584", "C11c", "yes", "incumbent, Q window centred and widened"),
    ("M_corrected__centred566_582", "C12b", "yes", "corrected, re-centred window"),
    ("q_peak_nm", "C14", "NO", "Q-peak position, raw"),
    ("q_peak_nm_cal", "C14c", "NO", "Q-peak position, recalibrated per RUN"),
    ("q_peak_nm_calsession", "C14s", "NO", "⭐ R2a — Q-peak position, recalibrated per SESSION"),
    ("q_centroid_545_605", "C5", "NO", "Q first moment, raw"),
    ("q_centroid_545_605_cal", "C5c", "NO", "Q first moment, recalibrated per run"),
    ("q_centroid_545_605_calsession", "C5s", "NO", "Q first moment, recalibrated per session"),
    ("q_peak_A", "C15a", "NO", "Q-peak height above its own chord"),
    ("c1_flank_slope_ratio", "C1", "NO", "flank-slope ratio (parked — green-vs-brown d≈0)"),
    ("slope_far_620_630", "C10a", "NO", "far-window slope alone"),
    # ---- C16, the Q-manifold ratio (§7.2). Existence before buildability.
    ("c16_v1_trough_chord", "V1", "trough", "⭐ C16 — both bands above the trough chord"),
    ("c16_v2_anchor_free", "V2", "NO", "⭐ C16 — peak height ÷ far slope, ANCHOR-FREE"),
    ("c16_v3_raw_ratio", "V3", "none", "C16 — raw A(574)/A(625), the naive control"),
    ("c16_v4_hybrid", "V4", "mixed", "C16 — local-chord height ÷ trough-chord far band"),
    # ---- R4a: C18, the third band pair (§7.4.2)
    ("c18_sf_raw", "C18r", "none", "⛔ C18 — Soret/far RAW; the control that shows it cannot work"),
    ("c18_sf_trough", "C18", "trough", "⭐ C18 — Soret/far above the trough chord"),
    # ---- R4b: C19, Q-region shape (§7.4.3 route A). ⚠ dilution is the PRIMARY risk, not discrimination.
    ("q_sigma_nm", "C19s", "local", "⭐ C19 — Q-region 2nd moment (sigma)"),
    ("q_fwhm_nm", "C19w", "local", "⭐ C19 — Q-region FWHM"),
    ("q_skew", "C19k", "local", "⭐ C19 — Q-region 3rd moment (skew)"),
    ("q_kurtosis", "C19u", "local", "C19 — Q-region 4th moment"),
    ("q_height_over_fwhm", "C19h", "local", "C19 — peak height ÷ FWHM"),
    ("q_area_over_height", "C19a", "local", "C19 — area ÷ height (an effective width)"),
    # ---- R4d: C20, derivatives (§7.4.3 route B) — the last of the four routes
    ("c20_d2_ratio", "C20", "NO", "⭐ C20 — D2(574) ÷ D2(625), second-derivative Q-manifold ratio"),
    ("d2_far_625", "C20f", "NO", "C20 — the far D2 term alone (the suspect)"),
    ("d2_q_574", "C20q", "NO", "C20 — the Q D2 term alone"),
    ("c20b_d2_soret_over_q", "C20b", "NO", "C20b — D2(Soret flank) ÷ D2(574), the control"),
]


def cohenD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("nan")


def main():
    with open(TABLE) as handle:
        payload = json.load(handle)
    rows = payload["runs"]
    print("table: %s  rev %s  %d runs\n" % (payload["harness"], payload["revision"], len(rows)))

    def values(key, predicate):
        return np.array([r["features"][key] for r in rows if predicate(r)])

    setsOf = {}
    for row in rows:
        setsOf.setdefault(row["oil"], {}).setdefault(row["set"], []).append(row)

    # ⛔ S1 WAS QUOTED AS A PER CENT OF THE METRIC'S OWN VALUE, AND THAT IS INVALID ACROSS FAMILIES.
    # A wavelength carries a huge arbitrary offset: the Q peak's 0.26 nm dilution spread reads as
    # 0.045 % of 574 nm, but as 6.4 % if the SAME feature is expressed as "nm above 570". A pure
    # relabelling moved the score by 140x, which is the definition of a meaningless statistic. It
    # produced the claim that the position was "355x more dilution-stable than M" -- retracted.
    #
    # The scale-free question is: how big is the nuisance COMPARED WITH THE SIGNAL the metric must
    # carry? Both ratios below are invariant under any affine relabelling of the feature.
    print("%-30s %-5s %-6s | %9s %9s | %7s %7s | %7s"
          % ("candidate", "id", "base", "sep/dilut", "sep/withn", "d", "d(K|S)", "⭐RATIO"))
    print("-" * 100)
    scored = []
    for key, ident, baseline, _ in CANDIDATES:
        greenValues = values(key, lambda r: r["oil"] in GREENS)
        brownValues = values(key, lambda r: r["oil"] == BROWN)
        separation = abs(greenValues.mean() - brownValues.mean())
        kiendler = np.array([np.mean([r["features"][key] for r in group])
                             for group in setsOf["Kiendler"].values()])
        dilution = kiendler.max() - kiendler.min()          # in the feature's OWN units
        within = np.mean([np.std([r["features"][key] for r in group], ddof=1)
                          for oil in setsOf for group in setsOf[oil].values() if len(group) > 1])
        s2 = cohenD(greenValues, brownValues)
        # ⭐ §2.2 — the honest bar. Cohen's d divides by RE-SEATING noise; the unit of replication for
        # a CLASS question is the oil. Kiendler-vs-Steirerkraft is the only same-class oil pair we own,
        # so it is the empirical floor a class claim has to clear. `M` sets the bar at 5.70.
        withinClass = cohenD(values(key, lambda r: r["oil"] == "Kiendler"),
                             values(key, lambda r: r["oil"] == "Steirerkraft"))
        ratio = s2 / withinClass if withinClass else float("inf")
        scored.append((ratio, key, ident, baseline, s2, withinClass))
        print("%-30s %-5s %-6s | %9.2f %9.2f | %7.2f %7.2f | %7.2f"
              % (key, ident, baseline, separation / dilution, separation / within,
                 s2, withinClass, ratio))

    print("\n   sep/dilut  = class separation ÷ the dilution-induced spread across Kiendler's 3 strengths")
    print("   sep/within = class separation ÷ mean within-set sd (the re-seating nuisance)")
    print("   Both are SCALE-FREE. Higher is better. They are the honest form of the old S1/S3.")

    # ⚠ R4b's duck: for a SHAPE statistic, dilution survival is the primary risk, not discrimination.
    # Width has no protection against concentration -- the band top approaches saturation while the
    # flanks do not -- so this must be read BEFORE any separation number for the C19 family.
    print("\n⚠ DILUTION FIRST — Kiendler's 3 preparations span x1.46 in concentration.")
    print("   A shape statistic that moves here is measuring the recipe, not the oil.")
    print("   %-24s %10s %10s %10s %10s" % ("candidate", "6 drops", "7 drops", "7 drops", "spread"))
    print("   " + "-" * 68)
    order = ["Kiendler A", "Kiendler B", "Kiendler C"]
    for key, ident, _, _ in CANDIDATES:
        if not (ident.startswith("C19") or ident.startswith("C18") or ident.startswith("C20")):
            continue
        means = [np.mean([r["features"][key] for r in rows if r["set"] == name]) for name in order]
        span = 100 * (max(means) - min(means)) / abs(np.mean(means))
        print("   %-24s %10.4f %10.4f %10.4f %9.1f %%" % (ident, means[0], means[1], means[2], span))
    print("   (for comparison: M spreads 10.3 %, M+correction 3.0 %, the Q-PEAK POSITION 0.05 %)")

    print("\n⭐ RANKED BY THE §2.2 RATIO — class d ÷ within-class d. The bar is `M` = 5.70.")
    for ratio, key, ident, baseline, s2, wc in sorted(scored, reverse=True):
        flag = "  <-- beats M" if ratio > 5.70 and ident not in ("C11",) else ""
        print("   %7.2f  %-6s %-30s (d %.2f / %.2f)%s" % (ratio, ident, key, s2, wc, flag))

    # ------------------------------------------------------------------ C15: pairs, not scalars
    # §3.7 found the position candidate is 355x more dilution-stable than M but separates 1.7x worse
    # -- the shape of a metric worth COMBINING rather than choosing between. Two ways to say "how well
    # do these two features separate the classes TOGETHER", both stated before looking:
    #
    #   z-sum        both features standardised by their POOLED WITHIN-CLASS sd, then added with unit
    #                weights and matched orientation. No weights are fitted, so no freedom is spent.
    #   Mahalanobis  the multivariate analogue of Cohen's d, using the pooled 2x2 covariance. This is
    #                the BEST any linear combination could do -- and therefore optimistically biased,
    #                because that best direction is chosen with the same 28 points it is scored on.
    print("\n" + "=" * 92)
    print("C15 — COMBINING a stable position with a discriminating amplitude")
    print("=" * 92)
    green = [r for r in rows if r["oil"] in GREENS]
    brown = [r for r in rows if r["oil"] == BROWN]

    def pooledSd(key):
        return np.sqrt((( len(green) - 1) * np.var([r["features"][key] for r in green], ddof=1)
                        + (len(brown) - 1) * np.var([r["features"][key] for r in brown], ddof=1))
                       / (len(green) + len(brown) - 2))

    def mahalanobis(keys):
        a = np.array([[r["features"][k] for k in keys] for r in green])
        b = np.array([[r["features"][k] for k in keys] for r in brown])
        pooled = (((len(a) - 1) * np.cov(a, rowvar=False) + (len(b) - 1) * np.cov(b, rowvar=False))
                  / (len(a) + len(b) - 2))
        delta = a.mean(axis=0) - b.mean(axis=0)
        return float(np.sqrt(delta @ np.linalg.inv(np.atleast_2d(pooled)) @ delta))

    def zSum(keys):
        total = []
        for r in rows:
            score = 0.0
            for k in keys:
                sd = pooledSd(k)
                z = (r["features"][k] - np.mean([x["features"][k] for x in rows])) / sd
                greenHigher = (np.mean([x["features"][k] for x in green])
                               > np.mean([x["features"][k] for x in brown]))
                score += z if greenHigher else -z
            total.append(score)
        total = np.array(total)
        mask = np.array([r["oil"] in GREENS for r in rows])
        return cohenD(total[mask], total[~mask])

    PAIRS = [("M__shipped560_580", "q_peak_nm_calsession"),
             ("M__shipped560_580", "q_peak_nm_cal"),
             ("M__centred566_582", "q_peak_nm_calsession"),
             ("M_corrected__shipped560_580", "q_peak_nm_calsession"),
             ("q_peak_A", "q_peak_nm_calsession"),
             ("M__shipped560_580", "q_peak_A")]
    print("%-52s %9s %9s %9s" % ("pair", "best of 1", "z-sum d", "Mahal. D"))
    print("-" * 84)
    for keys in PAIRS:
        best = max(cohenD(values(k, lambda r: r["oil"] in GREENS),
                          values(k, lambda r: r["oil"] == BROWN)) for k in keys)
        print("%-52s %9.2f %9.2f %9.2f"
              % (" + ".join(k.replace("__", " ") for k in keys), best, zSum(keys), mahalanobis(keys)))
    print("\n⚠ Mahalanobis is the CEILING of any linear combination and is fitted on the same 28 runs")
    print("   it is scored on — read it as optimistic. The z-sum fits nothing and is the honest one.")
    print("\n⚠ %d scalar candidates + %d pairs scored — quote both with any result (§6.4 rule 2)."
          % (len(scored), len(PAIRS)))


if __name__ == "__main__":
    main()
