"""What the recommended lamp would actually SEE — an anticipated green-vs-brown forecast.

*(Edwin 2026-08-07: "simulate an expected absorption curve based on typical green and brown oils … just
an anticipated estimate telling us what it all would boil down to".)*

⚠⚠ **THIS IS A FORECAST, NOT A MEASUREMENT.** No oil was measured for it. It is a forward model of
`A_oil(lambda)` built from the pigment physics in `KB_spectroscopy_physics.md` §4.1/§4.1a, with its free
amplitudes tuned so that the SHIPPED metric comes out at the values the rig actually reports for the
green and brown classes. That tuning is what makes it useful and also what limits it: it can say where
the light goes and which regions are usable, and it CANNOT confirm any band ratio, because the ratios
were put in by hand.

What it is anchored to, and those anchors are real:

  - band centres 432 / ~574 / ~623-626 nm — protochlorophyll, KB §4.1a (NOT chlorophyll a's 665);
  - the SHIPPED windows — Soret 440-460, near anchor 510-540, Q 560-580, far anchor 620-630
    (`DevSpectralPlugin.py`);
  - the SHIPPED class values — `M baseline` green 15.559 +- 0.615, brown 10.160 +- 0.197, threshold
    10.35 (`SPEC_roast_ampel.md` §2b, from 37 runs);
  - the measured green->brown direction — a demetallated (browner) fill reads Qy -17 % and 572 nm +14 %
    per unit Soret (`SPEC_capture_quality.md` §16.11.16);
  - the dilute-solution band ratio Soret : Q ~ 14 : 1 (Fruhwirth & Hermetter 2007 Fig. 3A).

⭐ The question it answers is NOT "is the ratio right" — it is **"with the recommended lamp, does each
region of 410-680 nm deliver enough transmitted light to measure at all?"** That is a photometric
question, and a forward model can answer it.

Run from the spectracsPy repo root:
    ./venv/bin/python diagnostics/oil_forecast_410_680.py [--figures]
"""
import sys

import numpy as np

import led_lamp_410_680 as lamp

GRID = lamp.GRID

# The shipped windows — DevSpectralPlugin.py. Soret is the 440-460 as shipped; §9.1 S1's adopted trim to
# 448-460 is reported alongside, because this forecast is exactly the thing that prices it.
SORET_BAND = (440.0, 460.0)
SORET_TRIMMED = (448.0, 460.0)
NEAR_ANCHOR = (510.0, 540.0)
Q_BAND = (560.0, 580.0)
FAR_ANCHOR = (620.0, 630.0)
QUIET_WINDOW = (660.0, 680.0)

# The rig's own class values, `M baseline` — SPEC_roast_ampel.md §2b (37 runs).
M_GREEN, M_BROWN, M_THRESHOLD = 15.559, 10.160, 10.35

# ⭐ The ABSOLUTE anchor, and it is needed: `M` is a ratio of two baselined band means, so it is
# INVARIANT under an overall scaling of A. Fitting only `M` leaves the absorbance LEVEL free — which is
# precisely the quantity this forecast exists to answer questions about. `SPEC_metric_research.md`
# §7.2's window table supplies it: the baselined Soret band mean, measured over the corpus.
B_SORET_440 = 1.0272        # shipped 440-460 window
B_SORET_448 = 0.6924        # ⭐ 448-460 — NOT fitted; used as a shape CHECK (see checkShape)

# ⚠ A DN floor is needed to say "measurable". §7.13's dead 440-447 bins and §16.7.2e's darkest-bin
# figures put the usable floor at a few DN out of 255; 1 % of full scale is the round number this study
# has used throughout. Everything below it is the regime that produced concentration-dependent
# compression, not merely noise.
FLOOR = 0.01


def gaussian(centre, fullWidth, amplitude):
    sigma = fullWidth / 2.3548
    return amplitude * np.exp(-0.5 * ((GRID - centre) / sigma) ** 2)


def absorbance(soret, soretShift, q574, qy625, carotenoid, browning, scale):
    """A_oil(lambda) for one oil, in absorbance units at the working recipe.

    Components and why each is here (KB §4.1, §4.1a):
      - Soret ~432 nm, the strong fully-allowed porphyrin band. `soretShift` is the demetallation
        BLUE shift: protochlorophyll -> protopheophytin lowers the macrocycle symmetry, which both
        weakens and blue-shifts it. That shift is the reason §2.1 of the lamp document wants light
        below 432 nm at all.
      - the two weak Q bands at ~574 and ~625 nm, which gain structure and change intensity on
        demetallation in OPPOSITE directions (§16.11.16: 572 up, Qy down).
      - carotenoid / lutein, a broad absorption 440-480 nm; it is NOT a pigment-ratio band but it
        shapes the blue wall.
      - Maillard browning from the roast: a smooth rise toward the blue, no structure.
    """
    a = (gaussian(432.0 - soretShift, 42.0, soret)
         + gaussian(574.0, 26.0, q574)
         + gaussian(625.0, 22.0, qy625)
         + gaussian(455.0, 62.0, carotenoid)
         + browning * np.exp(-(GRID - 410.0) / 95.0))
    return scale * a


def bandMean(curve, window):
    lo, hi = window
    return float(np.mean(curve[(GRID >= lo) & (GRID <= hi)]))


def baselinedMetric(a, soretWindow=SORET_BAND):
    """The shipped `M baseline` — two band means, each above a chord through the two anchor windows.

    Reproduces DevSpectralPlugin's three-region expansion: a straight line is fitted through the
    centroids of the near (510-540) and far (620-630) anchors and subtracted before the ratio.
    """
    nearCentre = sum(NEAR_ANCHOR) / 2.0
    farCentre = sum(FAR_ANCHOR) / 2.0
    nearValue, farValue = bandMean(a, NEAR_ANCHOR), bandMean(a, FAR_ANCHOR)
    slope = (farValue - nearValue) / (farCentre - nearCentre)

    def above(window):
        centre = sum(window) / 2.0
        chord = nearValue + slope * (centre - nearCentre)
        return bandMean(a, window) - chord

    return above(soretWindow) / above(Q_BAND)


def fitRatio(target, seed, browning):
    """Solve the Soret amplitude that puts the shipped metric on `target`.

    ⚠ This fixes only the Soret:Q RATIO. `M` is scale-invariant, so it says nothing about the level.
    """
    lo, hi = 0.05, 40.0
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if baselinedMetric(absorbance(scale=1.0, browning=browning, soret=mid, **seed)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def fitLevel(unscaled):
    """Scale so the baselined Soret band mean matches the measured 1.0272 over 440-460 nm."""
    nearCentre, farCentre = sum(NEAR_ANCHOR) / 2.0, sum(FAR_ANCHOR) / 2.0
    nearValue, farValue = bandMean(unscaled, NEAR_ANCHOR), bandMean(unscaled, FAR_ANCHOR)
    slope = (farValue - nearValue) / (farCentre - nearCentre)
    centre = sum(SORET_BAND) / 2.0
    perUnit = bandMean(unscaled, SORET_BAND) - (nearValue + slope * (centre - nearCentre))
    return B_SORET_440 / perUnit


def bandAbove(a, window):
    """A band mean with the two-anchor chord subtracted — the shipped `B_x`."""
    nearCentre, farCentre = sum(NEAR_ANCHOR) / 2.0, sum(FAR_ANCHOR) / 2.0
    nearValue, farValue = bandMean(a, NEAR_ANCHOR), bandMean(a, FAR_ANCHOR)
    slope = (farValue - nearValue) / (farCentre - nearCentre)
    centre = sum(window) / 2.0
    return bandMean(a, window) - (nearValue + slope * (centre - nearCentre))


def buildOils():
    """The two classes, differing only in the ways the rig has actually measured them to differ.

    Both are given the SAME overall scale — same recipe, same concentration x path — so the class
    difference lives entirely in the pigment chemistry, which is what the metric claims to measure.
    """
    green = dict(soretShift=0.0, q574=0.075, qy625=0.055, carotenoid=0.30)
    # §16.11.16, measured on a demetallated fill: Qy -17 %, 572 nm +14 %, both per unit Soret.
    # Demetallation also blue-shifts the Soret (KB §4.1) and the roast adds browning.
    brown = dict(soretShift=5.0, q574=0.075 * 1.14, qy625=0.055 * 0.83, carotenoid=0.30)

    rawGreen = absorbance(scale=1.0, browning=0.06,
                          soret=fitRatio(M_GREEN, green, 0.06), **green)
    rawBrown = absorbance(scale=1.0, browning=0.16,
                          soret=fitRatio(M_BROWN, brown, 0.16), **brown)
    scale = fitLevel(rawGreen)
    return rawGreen * scale, rawBrown * scale


def checkShape(aGreen):
    """⭐ The one thing here that is a TEST rather than a fit.

    Both free parameters were spent on 440-460 nm and on `M`. The 448-460 window was not — so the
    ratio B_Soret(448-460) / B_Soret(440-460) is a prediction of the model's SHAPE across the Soret's
    right-hand slope. The rig measures 0.6924 / 1.0272 = 0.674.
    """
    predicted = bandAbove(aGreen, SORET_TRIMMED) / bandAbove(aGreen, SORET_BAND)
    return predicted, B_SORET_448 / B_SORET_440


def at(curve, nanometers):
    return float(np.interp(nanometers, GRID, curve))


def main():
    aGreen, aBrown = buildOils()

    curves = {f: lamp.digitise(f) for f in lamp.PLOTS}
    for name, peak, width in (("star660", 660, 22), ("star670", 670, 22)):
        curves[name] = lamp.gaussianEmitter(float(peak), float(width))
    r2 = lamp.combine(curves, {"4000k-4500k.jpg": 3, "410nm-420nm.jpg": 2,
                               "430nm-435nm.jpg": 1, "660nm.jpg": 1})
    r2 = r2 / r2.max()
    incumbent = lamp.combine(curves, {"6500k-7000k.jpg": 3, "430nm-435nm.jpg": 2,
                                      "515nm-525nm.jpg": 1, "660nm.jpg": 1})
    incumbent = incumbent / incumbent.max()

    print(__doc__.split("Run from")[0])
    print("=" * 100)
    print("1 · THE FORECAST ABSORBANCE — does it reproduce what the rig reports?\n")
    print("  %-28s %8s %8s   %s" % ("", "green", "brown", "the rig reports"))
    print("  %-28s %8.2f %8.2f   %.3f vs %.3f  (fitted — this is the anchor, not a result)"
          % ("M baseline (440-460)", baselinedMetric(aGreen), baselinedMetric(aBrown),
             M_GREEN, M_BROWN))
    print("  %-28s %8.2f %8.2f   ⭐ PREDICTION — S1's adopted 448-460 trim, never yet measured"
          % ("M baseline (448-460)", baselinedMetric(aGreen, SORET_TRIMMED),
             baselinedMetric(aBrown, SORET_TRIMMED)))
    print("  %-28s %8s %8s   threshold %.2f, class gap %.0f %%"
          % ("", "", "", M_THRESHOLD, 100 * (M_GREEN - M_BROWN) / M_BROWN))

    print("\n  raw absorbance A(λ) at the places that matter:")
    print("  %-28s %8s %8s %8s" % ("", "green", "brown", "Δ"))
    for label, w in (("410 nm", 410), ("432 nm — Soret peak", 432), ("450 nm", 450),
                     ("460 nm", 460), ("510-540 near anchor", None), ("574 nm — Q", 574),
                     ("625 nm — Qy", 625), ("660 nm", 660), ("680 nm", 680)):
        if w is None:
            g, b = bandMean(aGreen, NEAR_ANCHOR), bandMean(aBrown, NEAR_ANCHOR)
        else:
            g, b = at(aGreen, w), at(aBrown, w)
        print("  %-28s %8.3f %8.3f %8.3f" % (label, g, b, b - g))

    print("\n" + "=" * 100)
    print("2 · WHAT THE CAMERA WOULD SEE — transmitted signal S = R · 10^(−A), relative to the")
    print("    lamp's own peak. ⛔ Below %.0f %% is the starved regime that made 440-447 dead bins.\n" % (100 * FLOOR))
    header = "  %-24s %10s %10s %10s %10s %10s" % (
        "", "R2 lamp", "S green", "S brown", "incumbent", "S green")
    print(header)
    print("  %-24s %10s %10s %10s %10s %10s" % ("", "", "(R2)", "(R2)", "lamp", "(incumbent)"))
    print("  " + "-" * (len(header) - 2))
    verdicts = []
    for label, w in (("410 nm", 410), ("432 nm — Soret PEAK", 432), ("440 nm", 440),
                     ("450 nm", 450), ("460 nm", 460), ("520 nm", 520), ("574 nm — Q", 574),
                     ("625 nm — Qy", 625), ("660 nm", 660), ("680 nm", 680)):
        lampR2, lampOld = at(r2, w), at(incumbent, w)
        sGreen = lampR2 * 10 ** (-at(aGreen, w))
        sBrown = lampR2 * 10 ** (-at(aBrown, w))
        sOld = lampOld * 10 ** (-at(aGreen, w))
        flag = "" if sGreen >= FLOOR else "  ⛔"
        print("  %-24s %10.4f %10.4f %10.4f %10.4f %10.4f%s"
              % (label, lampR2, sGreen, sBrown, lampOld, sOld, flag))
        verdicts.append((label, w, sGreen, sOld))

    print("\n" + "=" * 100)
    print("3 · WHAT IT BOILS DOWN TO\n")

    predicted, measured = checkShape(aGreen)
    print("  ⚠ FIRST, THE ONE FALSIFIABLE CHECK — AND IT FAILS. Both free parameters went on `M` and")
    print("     on the 440-460 band level, so the 448-460 window was NOT fitted. Its ratio to 440-460")
    print("     is therefore a genuine prediction of the Soret slope's shape:")
    print("       model %.3f   ·   rig %.3f   ·   %.0f %% apart"
          % (predicted, measured, 100 * abs(predicted - measured) / measured))
    print()
    print("     Trimming 440-447 off costs the rig 33 %% of its Soret band and costs the model only")
    print("     %.0f %%. So the real curve rises FAR more steeply below 448 nm than a Soret centred at"
          % (100 * (1 - predicted)))
    print("     432 with a 42 nm width can. Two readings, and they have different consequences:")
    print()
    print("     (a) the model's Soret is too broad / mis-placed  ⇒ the blue-end story would need")
    print("         re-checking, since it rests on that slope;")
    print("     (b) ⭐ the rig's 440-447 bins are NOT real absorbance. §7.13 documents exactly this:")
    print("         they are starved bins, and A = −log10(S/R) blows up when S approaches the floor,")
    print("         which INFLATES the 440-460 mean. `SPEC_metric_research.md` §7.2 calls the trim")
    print("         \"drops the non-measurements\" — that is the same claim from the metric's side.")
    print()
    print("     ⇒ (b) is independently documented and predicts the sign and rough size of what is")
    print("       seen, so the failure is CONSISTENT with a known instrument artefact rather than")
    print("       evidence against the pigment model. ⛔ But it is not proof, and it leaves the")
    print("       model's Soret slope UNVALIDATED. Treat every blue-end number below as indicative.\n")

    quietGreen = bandMean(aGreen, QUIET_WINDOW)
    print("  ⭐ 1 · THE QUIET WINDOW IS THE CLEAN WIN. A(660-680) = %.3f green / %.3f brown —"
          % (quietGreen, bandMean(aBrown, QUIET_WINDOW)))
    print("     transparent, so what arrives there IS the lamp, with no pigment in the way. R2 puts")
    print("     %.3f at 660 nm against the incumbent's %.3f (%.1f×), and %.3f vs %.3f at 680 (%.1f×)."
          % (at(r2, 660), at(incumbent, 660), at(r2, 660) / at(incumbent, 660),
             at(r2, 680), at(incumbent, 680), at(r2, 680) / at(incumbent, 680)))
    print("     ⇒ a baseline anchor with no pigment in it — which 620-630 is not, and never was.\n")

    print("  ⭐ 2 · THE BLUE GAIN IS BELOW THE PEAK, NOT AT IT — and that is the point.")
    print("     At 432 nm the two lamps are level (%.3f vs %.3f): the incumbent already carries two"
          % (at(r2, 432), at(incumbent, 432)))
    print("     430-435 emitters. The difference is the region under the peak:")
    for w in (410, 415, 420, 425, 430):
        gain = at(r2, w) / max(at(incumbent, w), 1e-6)
        sNew, sOld = at(r2, w) * 10 ** (-at(aGreen, w)), at(incumbent, w) * 10 ** (-at(aGreen, w))
        print("       %d nm   lamp %.3f vs %.3f (%4.1f×)   transmitted %.4f vs %.4f  %s"
              % (w, at(r2, w), at(incumbent, w), gain, sNew, sOld,
                 "" if sOld >= FLOOR else ("⛔ incumbent below floor" if sNew >= FLOOR
                                           else "⛔ both below floor")))
    print("     ⇒ ⭐ the incumbent cannot see the Soret's SHORT-wavelength side at all, so it cannot")
    print("       see the demetallation BLUE SHIFT. R2 can. That is the whole case for 410-420 nm.\n")

    print("  ⚠ 3 · AND THE HONEST CAVEAT — the blue is expensive in signal either way.")
    print("     A(432) = %.2f, so the oil transmits %.1f %% there at this recipe. Under R2 that is"
          % (at(aGreen, 432), 100 * 10 ** (-at(aGreen, 432))))
    print("     %.4f of the lamp peak — %s the %.0f %% floor. Halving the concentration would gain"
          % (at(r2, 432) * 10 ** (-at(aGreen, 432)),
             "above" if at(r2, 432) * 10 ** (-at(aGreen, 432)) >= FLOOR else "BELOW", 100 * FLOOR))
    print("     %.1f× there. ⇒ the lamp and the capillary protocol are ONE change, not two."
          % (10 ** (at(aGreen, 432) / 2.0)))
    print()

    print("  ⭐ 4 · THE THREE PEAKS SIT ON A SMOOTH LAMP — which is what you expected. |dlnI/dλ| of R2:")
    slope = lamp.logSlope(r2)
    for label, w, verdict in (("432 nm  Soret", 432, "on the 430-435 emitter's own peak"),
                              ("574 nm  Q", 574, "on the 4000 K phosphor's smooth hump"),
                              ("625 nm  Qy", 625, "flat — the 660 part's rise starts later")):
        print("       %-16s %5.2f %%/nm   %s" % (label, float(np.interp(w, GRID, slope)), verdict))
    print("     For scale: an emitter EDGE inside a band costs 25 %/nm (the Sansi's failure, §16.25.4);")
    print("     a source centred on a band costs 0-5 %/nm. All three land in the good regime.\n")

    print("  ⚠ 5 · A PREDICTION THAT CAN BE FALSIFIED: the S1 window trim 440-460 → 448-460 should")
    print("     move M from %.2f/%.2f to %.2f/%.2f — class gap %.0f %% → %.0f %%."
          % (baselinedMetric(aGreen), baselinedMetric(aBrown),
             baselinedMetric(aGreen, SORET_TRIMMED), baselinedMetric(aBrown, SORET_TRIMMED),
             100 * (baselinedMetric(aGreen) - baselinedMetric(aBrown)) / baselinedMetric(aBrown),
             100 * (baselinedMetric(aGreen, SORET_TRIMMED) - baselinedMetric(aBrown, SORET_TRIMMED))
             / baselinedMetric(aBrown, SORET_TRIMMED)))
    print("     ⚠ Believe the DIRECTION, not the number — the brown oil's chemistry is modelled from")
    print("       ONE measured fill (§16.11.16), which is the thinnest input in this file.")

    if "--figures" in sys.argv:
        writeFigures(aGreen, aBrown, r2, incumbent)


def writeFigures(aGreen, aBrown, r2, incumbent):
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = lamp.OUT_DIRECTORY
    os.makedirs(out, exist_ok=True)
    ink, gridColour = "#1f2933", "#d7dde3"
    green, brown = "#2f7d4f", "#7a4a1e"

    def frame(axes, title):
        axes.set_title(title, fontsize=11, color=ink)
        axes.set_xlabel("wavelength (nm)", fontsize=9)
        axes.set_xlim(410, 680)
        axes.grid(True, color=gridColour, linewidth=0.6)
        for spine in ("top", "right"):
            axes.spines[spine].set_visible(False)
        axes.tick_params(labelsize=8)

    def bands(axes, top):
        for (lo, hi), name, colour in ((SORET_BAND, "Soret\n440-460", "#3b5bdb"),
                                       (NEAR_ANCHOR, "near\n510-540", "#7b8794"),
                                       (Q_BAND, "Q\n560-580", "#c9a227"),
                                       (FAR_ANCHOR, "far\n620-630", "#b0413e"),
                                       (QUIET_WINDOW, "quiet\n660-680", "#0b6e4f")):
            axes.axvspan(lo, hi, color=colour, alpha=0.10)
            axes.text((lo + hi) / 2.0, top, name, fontsize=7, color=colour,
                      ha="center", va="top")

    # 5 — the forecast absorbance itself
    figure, axes = plt.subplots(figsize=(9.2, 4.6))
    axes.plot(GRID, aGreen, color=green, linewidth=2.0, label="green oil — forecast A(λ)")
    axes.plot(GRID, aBrown, color=brown, linewidth=2.0, linestyle="--",
              label="brown oil — forecast A(λ)")
    for centre, name in ((432.0, "Soret 432"), (574.0, "Q 574"), (625.0, "Qy 625")):
        axes.axvline(centre, color="#b0413e", linewidth=0.8, alpha=0.5)
    top = max(aGreen.max(), aBrown.max()) * 1.12
    axes.set_ylim(0, top)
    bands(axes, top * 0.99)
    frame(axes, "FORECAST absorbance of a typical green and a typical brown oil  ⚠ modelled, not measured")
    axes.set_ylabel("absorbance A", fontsize=9)
    axes.legend(fontsize=8, frameon=False, loc="center right")
    figure.tight_layout()
    figure.savefig(out + "oil_forecast_absorbance.png", dpi=170)
    plt.close(figure)

    # 6 — what the camera would see
    figure, axes = plt.subplots(figsize=(9.2, 4.6))
    for curve, colour, style, label in (
            (r2 * 10 ** (-aGreen), green, "-", "green oil under R2"),
            (r2 * 10 ** (-aBrown), brown, "--", "brown oil under R2"),
            (incumbent * 10 ** (-aGreen), "#9aa5b1", "-.", "green oil under the incumbent lamp")):
        axes.semilogy(GRID, np.maximum(curve, 1e-6), color=colour, linestyle=style,
                      linewidth=1.8, label=label)
    axes.axhline(FLOOR, color="#b0413e", linewidth=1.0)
    axes.fill_between(GRID, 1e-6, FLOOR, color="#b0413e", alpha=0.07)
    axes.text(412, FLOOR * 1.12, "1 % floor — below this is the regime that made 440-447 dead bins",
              fontsize=7.5, color="#b0413e")
    axes.set_ylim(4e-3, 3.4)
    bands(axes, 3.1)
    frame(axes, "What the camera would see — transmitted signal S = R · 10^(−A)")
    axes.set_ylabel("relative to the lamp's peak, log scale", fontsize=9)
    axes.legend(fontsize=8, frameon=False, loc="lower right")
    figure.tight_layout()
    figure.savefig(out + "oil_forecast_transmitted.png", dpi=170)
    plt.close(figure)
    print("\nfigures -> %s" % out)


if __name__ == "__main__":
    main()
