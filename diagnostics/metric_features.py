"""R1 — extraction. Every per-run quantity we know how to compute, into one JSON table.

(docs/SPEC_metric_research.md §6.3 — the artifact contract.)

WHY A TABLE AND NOT A PRINTOUT. Parsing the 28 PDFs is the slow step in every experiment in the metric
research; scoring a candidate from numbers already extracted takes milliseconds. More importantly,
Edwin's rule: every quantity discovered during ANY evaluation must survive into the next one, so that
nothing is ever recomputed and no past finding is lost.

THE CONTRACT (§6.3):
  1. Append-only in spirit -- a new evaluation ADDS feature keys, never removes or renames one.
  2. One row per RUN, never per set. Set/oil statistics are DERIVED by the scoring step.
  3. Raw features only, no verdicts. Cohen's d, S1/S2/S3 and any threshold live in metric_scores.py,
     so changing a threshold or a class roster costs nothing here.
  4. Provenance per row: run, set, oil, SESSION -- session because §3.4 makes it a first-class
     confounder that every future analysis must be able to condition on.
  5. The table is a CACHE, not a source of truth. Regenerate it; never hand-edit it.

⚠ TWO-PASS. Most features are per-run and independent. The RECALIBRATED wavelength features are not:
they need corpus-level reference positions for the two lamp lines (§3.6a), so they are added in a
second pass and the references used are recorded in the header for reproducibility.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_features.py
"""
import json
import os
import subprocess

import numpy as np
from scipy.signal import savgol_filter

from metric_research_overview import SETS, load
from lamp_line_calibration import lineCentre, LINES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "metric_features.json")

SESSION = {"Kiendler": "20260801", "Steirerkraft": "20270729", "S-Budget": "20260731"}

# Bands. SORET/NEAR/Q/FAR are the shipped windows; the Q_* variants exist because §3.6 found the band's
# peak at ~574 nm, i.e. the shipped 560-580 window is asymmetric about it (14 nm below, 6 nm above).
SORET, NEAR, FAR = (440.0, 460.0), (520.0, 540.0), (620.0, 630.0)
Q_WINDOWS = {"shipped560_580": (560.0, 580.0),      # what the plugin ships
             "centred566_582": (566.0, 582.0),      # symmetric about the measured 574 nm peak
             "wide564_584": (564.0, 584.0)}         # same centre, wider
R_Q = -0.0184                                       # the shared pedestal residual (Kiendler's fit)

# The Q peak search region, and the SG smoothing used to find it (§3.6).
PEAK_REGION, SG_WINDOW, SG_ORDER = (545.0, 605.0), 151, 3
SG_D2_WINDOW = 101              # 101 bins x 0.146 nm = 14.7 nm -- narrower than any band here
SLOPE_FAR, SLOPE_SORET = (620.0, 629.8), (460.0, 480.0)

# The red anchor C16 would need if the far window is promoted from baseline to signal. Sited on the
# trough between the two Q features and stopped at 606 nm to clear the 607 lamp line (which occupies
# 606.5-610.1 nm, measured). ⚠ The trough MOVES with oil class -- 598.5 / 601.3 / 617.6 nm for
# Kiendler / Steirerkraft / S-Budget -- so this anchor is class-dependent by construction. That is
# not a reason to skip it: V1 vs V2 is precisely how the size of that penalty gets measured instead
# of asserted (§7.2).
TROUGH_ANCHOR = (593.0, 606.0)


def bandMean(grid, values, window):
    mask = (grid >= window[0]) & (grid <= window[1])
    return float(values[mask].mean())


def slope(grid, values, window):
    mask = (grid >= window[0]) & (grid <= window[1])
    return float(np.polyfit(grid[mask], values[mask], 1)[0])


def chordBaselined(grid, values, near, far):
    """The shipped construction: a straight line through the two anchor-window means, subtracted."""
    xNear = grid[(grid >= near[0]) & (grid <= near[1])].mean()
    xFar = grid[(grid >= far[0]) & (grid <= far[1])].mean()
    yNear, yFar = bandMean(grid, values, near), bandMean(grid, values, far)
    fit = np.polyfit([xNear, xFar], [yNear, yFar], 1)
    return values - np.polyval(fit, grid)


def qPeak(grid, values):
    """Sub-bin position and height of the Q band's maximum above its own local chord (§3.6)."""
    smooth = savgol_filter(values, SG_WINDOW, SG_ORDER)
    mask = (grid >= PEAK_REGION[0]) & (grid <= PEAK_REGION[1])
    x, y = grid[mask], smooth[mask]
    chord = np.polyfit([x[0], x[-1]], [y[0], y[-1]], 1)
    excess = y - np.polyval(chord, x)
    index = int(np.argmax(excess))
    if 0 < index < len(x) - 1:
        low, mid, high = excess[index - 1], excess[index], excess[index + 1]
        offset = 0.5 * (low - high) / (low - 2 * mid + high)
        return float(x[index] + offset * (x[1] - x[0])), float(mid)
    return float(x[index]), float(excess[index])


def qCentroid(grid, values, window):
    """First moment of the band above its own chord -- a position that uses the whole band, not a tip."""
    mask = (grid >= window[0]) & (grid <= window[1])
    x, y = grid[mask], values[mask]
    chord = np.polyfit([x[0], x[-1]], [y[0], y[-1]], 1)
    excess = np.clip(y - np.polyval(chord, x), 0, None)
    return float((x * excess).sum() / excess.sum()) if excess.sum() > 0 else float("nan")


def featuresFor(grid, values):
    """Every per-run feature. ADD here; never rename or remove (contract rule 1)."""
    baselined = chordBaselined(grid, values, NEAR, FAR)
    features = {"A_Soret_raw": bandMean(grid, values, SORET),
                "A_near_raw": bandMean(grid, values, NEAR),
                "A_far_raw": bandMean(grid, values, FAR),
                "B_Soret": bandMean(grid, baselined, SORET),
                "slope_far_620_630": slope(grid, values, SLOPE_FAR),
                "slope_soret_460_480": slope(grid, values, SLOPE_SORET),
                "q_centroid_545_605": qCentroid(grid, values, PEAK_REGION)}
    features["c1_flank_slope_ratio"] = (features["slope_far_620_630"]
                                        / features["slope_soret_460_480"])

    # the metric, on each candidate Q window -- this is how Edwin's "does M hold with a re-centred
    # window?" question gets answered without touching the shipped plugin
    for label, window in Q_WINDOWS.items():
        bq = bandMean(grid, baselined, window)
        features["A_Q_raw__" + label] = bandMean(grid, values, window)
        features["B_Q__" + label] = bq
        features["M__" + label] = features["B_Soret"] / bq
        features["M_corrected__" + label] = features["B_Soret"] / (bq - R_Q)

    position, height = qPeak(grid, values)
    features["q_peak_nm"] = position
    features["q_peak_A"] = height

    # ---- C16, the Q-manifold ratio (Edwin 2026-08-04, §7.2). Four variants, because the question
    # "does the effect EXIST" must be answered before "what is the right baseline" -- the third
    # rubber-duck pass caught that order being backwards.
    #
    # The numerator band (566-582) BRACKETS fine: 545 and 605 are both measurable. Only the far-red
    # side lacks a red foot, because the Qy maximum is past our 629.8 nm cut-off. So the variants
    # differ ONLY in how the far side is handled.
    troughChord = chordBaselined(grid, values, NEAR, TROUGH_ANCHOR)
    features["A_far_620_6298"] = bandMean(grid, values, SLOPE_FAR)
    features["B_Q_trough"] = bandMean(grid, troughChord, Q_WINDOWS["centred566_582"])
    features["B_far_trough"] = bandMean(grid, troughChord, SLOPE_FAR)

    # V1 trough-anchored chord for both bands -- the natural baseline, trough movement and all
    features["c16_v1_trough_chord"] = features["B_Q_trough"] / features["B_far_trough"]
    # V2 ANCHOR-FREE: local-chord peak height over the far-red SLOPE. No red foot needed anywhere.
    features["c16_v2_anchor_free"] = height / features["slope_far_620_630"]
    # V3 the naive control: no baseline at all. Expected to fail dilution; informative if it does not.
    features["c16_v3_raw_ratio"] = (features["A_Q_raw__centred566_582"]
                                    / features["A_far_620_6298"])
    # V4 hybrid: LOCAL chord for the numerator, trough chord for the far side. V1 vs V4 isolates
    # whether the numerator's baseline choice matters at all.
    features["c16_v4_hybrid"] = height / features["B_far_trough"]

    # ---- C18 (R4a): the THIRD band pair, Soret / far-red. Edwin's framing made the gap obvious --
    # `M` is blue/green, V3 is green/red, and blue/red was never tried.
    #
    # ⛔ IT CANNOT BE RUN RAW. V3 survives without a baseline only because its two bands are NEARLY
    # EQUAL (0.16 vs 0.13), so a common pedestal delta nearly cancels in the ratio. S/F is ~1.0 over
    # ~0.15 -- a factor of 7 -- so the same delta moves the ratio by delta/0.15. That is exactly the
    # error/B failure the pedestal document is about. The raw form is computed anyway, as the control
    # that demonstrates it.
    #
    # ⛔ AND IT CANNOT USE THE SHIPPED CHORD: that chord is fitted THROUGH 620-630, so B_far would be
    # identically zero. C18 needs the trough-anchored chord, which leaves the far window free to be
    # signal -- at the cost of the ~5x penalty §7.2 measured for that moving anchor.
    features["B_Soret_trough"] = bandMean(grid, troughChord, SORET)
    features["c18_sf_raw"] = features["A_Soret_raw"] / features["A_far_620_6298"]
    features["c18_sf_trough"] = features["B_Soret_trough"] / features["B_far_trough"]
    # the identity check: S/F == (S/Q)*(Q/F) holds EXACTLY only under a shared baseline (§7.4.2)
    features["c18_identity_residual"] = (features["c18_sf_trough"]
                                         - (features["B_Soret_trough"] / features["B_Q_trough"])
                                         * features["c16_v1_trough_chord"])

    # ---- C19 (R4b): Q-region SHAPE. ⚠ NOT "pedestal-immune" -- only the POSITION is. Width and skew
    # are computed above a local chord, which removes offset and tilt but NOT curvature, so a curved
    # residual pedestal adds width and skew of its own. And unlike the position, width has no
    # protection against DILUTION: at higher concentration the band top approaches saturation while
    # the flanks do not, which changes the measured width. That is C19's primary risk, not a footnote.
    #
    # ⚠ NO DIRECTION IS PRE-REGISTERED. Demetallation splits 2 bands into 4, which could widen the
    # envelope or push strength out of the window and narrow it. §3.10 already failed to resolve the
    # splitting with a 2-Gaussian fit, so these statistics measure the ENVELOPE, not the components.
    features.update(qShape(grid, values))

    # ---- C20 (route B): the SECOND-DERIVATIVE Q-manifold ratio. A 2nd derivative annihilates any
    # LINEAR background exactly and suppresses broad smooth ones by (W_pedestal/W_band)^2, so it needs
    # no quiet window and no anchor -- pedestal removal by physics rather than by assumption.
    #
    # ⚠ ITS WEAKEST TERM SITS WHERE ROUTE C JUST DIED. D2 at 625 nm reads the curvature of the Qy
    # FLANK, and a flank has little curvature by definition -- its peak is past the 629.8 cut-off
    # (§3.1). Expect the denominator to be small and noisy. Two forms are computed so the failure, if
    # it comes, can be attributed: at a POINT (most sensitive to the edge) and over a WINDOW MEAN.
    #
    # Sign convention: an absorption band is a maximum, so its 2nd derivative is NEGATIVE at the peak.
    # Both terms are negated to keep the ratio positive and readable.
    step = float(np.median(np.diff(grid)))
    second = savgol_filter(values, SG_D2_WINDOW, SG_ORDER, deriv=2, delta=step)
    d2Q = -second[(grid >= 570.0) & (grid <= 578.0)].mean()
    d2Far = -second[(grid >= 620.0) & (grid <= 629.8)].mean()
    features["d2_q_574"] = float(d2Q)
    features["d2_far_625"] = float(d2Far)
    features["c20_d2_ratio"] = float(d2Q / d2Far) if d2Far else float("nan")
    # the Soret-flank comparison, for the same reason C1 existed: is the far term the problem, or is
    # the whole derivative family weak here?
    d2Soret = -second[(grid >= 465.0) & (grid <= 485.0)].mean()
    features["d2_soret_flank"] = float(d2Soret)
    features["c20b_d2_soret_over_q"] = float(d2Soret / d2Q) if d2Q else float("nan")

    for nominal, coreHalf, wingHalf in LINES:
        centre, sigma = lineCentre(grid, values, nominal, coreHalf, wingHalf)
        key = "line_%d" % round(nominal)
        features[key + "_nm"] = centre
        features[key + "_fwhm_nm"] = sigma * 2.3548
    return features


def qShape(grid, values):
    """Second and third moments of the Q region above its own local chord -- never looked at before."""
    smooth = savgol_filter(values, SG_WINDOW, SG_ORDER)
    mask = (grid >= PEAK_REGION[0]) & (grid <= PEAK_REGION[1])
    x, y = grid[mask], smooth[mask]
    chord = np.polyfit([x[0], x[-1]], [y[0], y[-1]], 1)
    excess = np.clip(y - np.polyval(chord, x), 0, None)
    total = excess.sum()
    if total <= 0:
        return {}
    weight = excess / total
    mean = float((x * weight).sum())
    variance = float((weight * (x - mean) ** 2).sum())
    sigma = np.sqrt(variance)
    peak = excess.max()
    half = excess >= peak / 2.0
    return {"q_area_545_605": float(np.trapz(excess, x)),
            "q_sigma_nm": float(sigma),                                   # 2nd moment
            "q_skew": float((weight * ((x - mean) / sigma) ** 3).sum()),  # 3rd moment
            "q_kurtosis": float((weight * ((x - mean) / sigma) ** 4).sum()),
            "q_fwhm_nm": float(x[half].max() - x[half].min()),
            # shape ratios: amplitude divides out, so these are the SCALE-FREE forms
            "q_height_over_fwhm": float(peak / (x[half].max() - x[half].min())),
            "q_area_over_height": float(np.trapz(excess, x) / peak)}


def revision():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def main():
    grid, loaded = load()
    byName = {name: paths for name, _, paths in SETS}
    order = [(name, oil, path) for name, oil, paths in SETS for path in paths]

    rows = []
    for (name, oil, path), (_, _, values) in zip(order, loaded):
        rows.append({"run": path.replace(".pdf", ""), "set": name, "oil": oil,
                     "session": SESSION[oil], "features": featuresFor(grid, values)})
    print("extracted %d runs x %d features" % (len(rows), len(rows[0]["features"])))

    # --- pass 2: the two-line wavelength recalibration (§3.6a). Two references, two parameters, so
    # the linear map measured -> corpus reference is exact. The reference is the corpus grand mean,
    # which removes RELATIVE drift between sessions; it makes no claim about the absolute scale.
    keys = ["line_%d_nm" % round(nominal) for nominal, _, _ in LINES]
    reference = {key: float(np.mean([r["features"][key] for r in rows])) for key in keys}
    lowKey, highKey = keys

    def linearMap(low, high):
        scale = (reference[highKey] - reference[lowKey]) / (high - low)
        return reference[lowKey] - scale * low, scale

    # --- per-RUN calibration: each run corrected by its own two line fits.
    for row in rows:
        offset, scale = linearMap(row["features"][lowKey], row["features"][highKey])
        row["features"]["wl_offset"], row["features"]["wl_scale"] = offset, scale
        for key in ("q_peak_nm", "q_centroid_545_605"):
            row["features"][key + "_cal"] = offset + scale * row["features"][key]

    # --- R2a: per-SESSION calibration. §3.6b found the per-run version reduces the between-session
    # BIAS but inflates within-oil spread, because each run inherits the noise of its own two line
    # fits. The drift being corrected is a property of the evening, not of the run -- so averaging the
    # lines over the session first should keep the bias correction and drop the added noise.
    for session in {row["session"] for row in rows}:
        group = [r for r in rows if r["session"] == session]
        low = float(np.mean([r["features"][lowKey] for r in group]))
        high = float(np.mean([r["features"][highKey] for r in group]))
        offset, scale = linearMap(low, high)
        for row in group:
            row["features"]["wl_offset_session"], row["features"]["wl_scale_session"] = offset, scale
            for key in ("q_peak_nm", "q_centroid_545_605"):
                row["features"][key + "_calsession"] = offset + scale * row["features"][key]

    payload = {"schema": 1,
               "harness": "diagnostics/metric_features.py",
               "revision": revision(),
               "corpus": "SPEC_metric_research.md §2 — aged fill excluded",
               "grid": {"min_nm": float(grid.min()), "max_nm": float(grid.max()),
                        "bins": int(len(grid))},
               "constants": {"r_Q": R_Q, "q_windows": Q_WINDOWS,
                             "wl_reference_nm": reference},
               "runs": rows}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
    print("wrote %s  (%d rows, %d features each)"
          % (OUT, len(rows), len(rows[0]["features"])))


if __name__ == "__main__":
    main()
