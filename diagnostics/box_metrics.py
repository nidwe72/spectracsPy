"""⭐⭐ `V` — the metric this project should ship, and every number behind it.
   (`SPEC_metric_research.md` §10. Edwin's session 2026-08-14.)

    V = (A_valley − A_Q) / A_Soret        on the DE-SPIKED RAW absorbance, no baseline anywhere

        A_valley = mean A over 500–560 nm      the flat window between the two bands
        A_Q      = mean A over 565–580 nm      the Q band
        A_Soret  = mean A over 448–460 nm      the Soret flank

⭐ SAMPLING (§10.1, settled 2026-08-14): each band mean is the PLAIN ARITHMETIC MEAN of the spectrum's
OWN NATIVE SAMPLES inside [lo, hi], BOTH EDGES INCLUSIVE — identical to the shipped
`SpectrumFeatureLogicModule.bandMean`, so this script and the app print the same number for the same
jar. ⛔ It used to resample onto a 0.5 nm grid first and read `V × 100` 0.082 ± 0.023 low.

Reported as `V × 100`. Less negative = greener. `V` is always negative because the valley lies below
the Q band.

WHY IT IS BUILT THIS WAY. The numerator is a DIFFERENCE, so any additive offset (stray light,
scattering, seating) cancels — both bands carry it equally. The denominator is a LEVEL, so
multiplicative scale (concentration, exposure) cancels. That is the same immunity the linear-baseline
chord provides, obtained arithmetically instead of by fitting — and because nothing is fitted, no
anchor can be contaminated. ⛔ That matters here specifically: the shipped chord's far foot sits at
620–630 nm, ON the Qy band (`KB_spectroscopy_physics.md` §4.1a), so its slope is fill-dependent and
every statistic computed on the corrected curve inherits a tilt (`SPEC_capture_quality.md` §16.31.3a).

WHAT IT MEASURES. `W = (A_Q − A_valley)/(A_Soret − A_valley)` is the same quantity in mechanistically
pure form: the Q : Soret band-intensity ratio with the valley as the pigment's own zero. Gouterman's
four-orbital model makes that ratio the diagnostic for loss of the central Mg²⁺ — pheophytinization,
the first step of degradation, and the same chemistry that turns cooked green vegetables olive.
`W = −V/(1−u)` with `u = A_valley/A_Soret` is an exact identity; `u` spans 22 % across the archive,
which is the whole of why `W` is the noisier of the two. ⚠ We measure the Soret FLANK (peak is at
432 nm), so `W` is a proxy, not the true band ratio — ROADMAP item 5 would fix that.

⛔ TWO KNOWN WEAKNESSES, both measured, both in §10.4:
   * a LAMP SWAP moves `V` by 4.84 units — more than the whole green/brown gap
   * HALF concentration moves it 2.19 units (a ±40 % dose change moves it 0.12 — fine)

⚠ SELECTION RISK: `V` was found by scanning ~9 candidates on 13 fills. Its definition is FROZEN here
so ROADMAP PRIO 2c / σ_fill can test it on data it was not tuned on. Do not re-tune the windows.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/box_metrics.py
"""
import numpy as np

from settling_sweep import despikedAbsorption, asArrays, feature

# ⛔ FROZEN 2026-08-14 — pre-registration. Changing these invalidates the PRIO 2c test.
VALLEY, Q_BAND, SORET = (500.0, 560.0), (565.0, 580.0), (448.0, 460.0)
# §10.3 — the SHIPPED line. The corridor midpoint on §16.20.4's own 18-run corpus is -18.665 (native
# sampling); -18.6 is kept deliberately, on the STRICT side of it, per §16.10.17d's policy that a
# false GREEN is the harder error to make. No archived run lies between the two.
T_V = -18.6
TRACKER_BAND = 1.0                # §10.5, provisional; 3σ on the measured refill sd would be 0.64
SHIPPED_CHORD = ((520.0, 540.0), (620.0, 630.0))
# ⛔ NO RESAMPLING GRID (removed 2026-08-14, §10.1 sampling convention). A band mean is taken over the
# spectrum's OWN native samples, both edges inclusive — because that is what the shipped `bandMean`
# does and the app cannot resample. This script used to interpolate onto a 0.5 nm grid first, which
# read Q% 0.082 ± 0.023 LOWER than the app would: a plain mean of N samples carries an
# ((f(a)+f(b))/2 − mean)/N term, so it is not portable across grids (see §10.1's caveat).
# ⚠ Curve-vs-curve work (the history tracker's D) still NEEDS a common grid — 10 distinct native axes
# live in this archive. The grid was dropped for band MEANS only.

# The threshold corpus: exactly the 18 runs `soret_448_thresholds.py` set the M448 lines from.
PRIMARY = [("Steirerkraft B", "20270729B", 6, "green"),
           ("Steirerkraft C", "20270729C", 6, "green"),
           ("S-Budget series D", "20260731A", 6, "brown")]
# Everything else post-rebuild with a documented oil — context, never an input to the line.
CONTEXT = [("Kiendler A 6drop", "20260801A", 6), ("Kiendler B 7drop", "20260801B", 2),
           ("Kiendler C 7drop", "20260801C", 2),
           ("Steirerkraft half-strength", "20260804A", 6),
           ("Steirerkraft aged 24 h", "20270729A_aged24h", 3),
           ("Spar Steirisches g.g.A.", "20260807A", 3),
           ("Spar S-Budget capillary", "20260807B", 3),
           ("Spar Premium g.g.A.", "20260807C", 3),
           ("Steirerkraft capillary", "20260807D", 3),
           ("Billa Clever A", "20260812_BillaClever", 3),
           ("Billa Clever B", "20260812_BillaCleverB", 3),
           ("Ja! Natürlich", "20260812BillJaNatuerlich", 3)]
# Same-product fill sets, for the refill floor the history tracker's band rests on.
REFILLS = {"Steirerkraft": ["20270729B", "20270729C", "20260807D"],
           "Spar S-Budget": ["20260731A", "20260807B"],
           "Billa Clever": ["20260812_BillaClever", "20260812_BillaCleverB"],
           "Kiendler": ["20260801A", "20260801C"]}
COUNTS = {"20270729B": 6, "20270729C": 6, "20260731A": 6, "20260801A": 6, "20260801B": 2,
          "20260801C": 2, "20260804A": 6, "20270729A_aged24h": 3, "20260807A": 3,
          "20260807B": 3, "20260807C": 3, "20260807D": 3, "20260812_BillaClever": 3,
          "20260812_BillaCleverB": 3, "20260812BillJaNatuerlich": 3}


def bandMeans(path):
    """(A_valley, A_Q, A_Soret) on the de-spiked raw absorbance — nothing subtracted."""
    lam, values = asArrays(despikedAbsorption(path))
    band = lambda window: float(values[(lam >= window[0]) & (lam <= window[1])].mean())
    return band(VALLEY), band(Q_BAND), band(SORET)


def valueOf(path):
    """⭐ THE METRIC, ×100 for readability."""
    valley, q, soret = bandMeans(path)
    return 100.0 * (valley - q) / soret


def pureForm(path):
    """W — the mechanistically pure Q:Soret band ratio, valley as zero (§10.2)."""
    valley, q, soret = bandMeans(path)
    return (q - valley) / (soret - valley)


def incumbent(path):
    """M448 on the shipped chord, for side-by-side comparison only."""
    lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path),
                                                           SHIPPED_CHORD))
    soret = float(values[(lam >= 448) & (lam <= 460)].mean())
    return soret / float(values[(lam >= 560) & (lam <= 580)].mean())


def runsOf(series, count=None):
    return ["%s/%03d.pdf" % (series, i) for i in range(1, (count or COUNTS[series]) + 1)]


def series(function, name, count=None):
    return np.array([function(p) for p in runsOf(name, count)])


def threshold():
    """The corridor-midpoint line, derived exactly as `soret_448_thresholds.py` derives M448's."""
    green = np.concatenate([series(valueOf, s, n) for _, s, n, c in PRIMARY if c == "green"])
    brown = np.concatenate([series(valueOf, s, n) for _, s, n, c in PRIMARY if c == "brown"])
    pooled = np.sqrt((green.var(ddof=1) + brown.var(ddof=1)) / 2)
    return green, brown, (green.min() + brown.max()) / 2, abs(green.mean() - brown.mean()) / pooled


def main():
    print(__doc__.split("Run:")[0].strip())
    print()

    green, brown, line, cohen = threshold()
    print("=" * 96)
    print("§10.3  THE THRESHOLD — corridor midpoint, on the same 18 runs M448's lines came from")
    print("=" * 96)
    for label, name, count, cls in PRIMARY:
        values = series(valueOf, name, count)
        print("   %-22s %-6s n=%d   V×100 %7.2f ± %.2f"
              % (label, cls, count, values.mean(), values.std(ddof=1)))
    print("   green %7.2f ± %.2f      brown %7.2f ± %.2f" %
          (green.mean(), green.std(ddof=1), brown.mean(), brown.std(ddof=1)))
    print("   empty corridor %.2f wide   ⇒  T_V = %.2f   (frozen: %.2f)   Cohen's d = %.2f"
          % (green.min() - brown.max(), line, T_V, cohen))

    print("\n" + "=" * 96)
    print("§10.3a WHERE EVERY OTHER FILL LANDS   (green above T_V, brown below)")
    print("=" * 96)
    print("   %-28s %3s %9s %9s %9s" % ("fill", "n", "V×100", "M448", "verdict"))
    for label, name, count in CONTEXT:
        values, m = series(valueOf, name, count), series(incumbent, name, count)
        split = not ((values > T_V).all() or (values < T_V).all())
        print("   %-28s %3d %9.2f %9.2f %9s%s"
              % (label, count, values.mean(), m.mean(),
                 "green" if values.mean() > T_V else "brown",
                 "  ⛔ runs SPLIT the line" if split else ""))

    print("\n" + "=" * 96)
    print("§10.5  THE HISTORY-TRACKER BAND — what a re-preparation actually costs")
    print("=" * 96)
    spreads = []
    print("   %-16s %-46s %9s" % ("product", "fills", "refill sd"))
    for product, names in REFILLS.items():
        means = np.array([series(valueOf, n).mean() for n in names])
        spreads.append(means.std(ddof=1))
        print("   %-16s %-46s %9.2f" % (product, " ".join(names), spreads[-1]))
    pooled = float(np.mean(spreads))
    within = np.sqrt(np.mean([series(valueOf, n).var(ddof=1)
                              for names in REFILLS.values() for n in names]))
    span = abs(green.mean() - brown.mean())
    print("   pooled refill sd %.2f   within-fill sd %.2f   class span %.2f" % (pooled, within, span))
    print("   ⇒ 3σ limit ±%.2f   |   SHIPPED BAND ±%.1f = %.1fσ, detecting %.0f %% of the class span"
          % (3 * pooled, TRACKER_BAND, TRACKER_BAND / pooled, 100 * TRACKER_BAND / span))

    print("\n" + "=" * 96)
    print("§10.4  THE TWO WEAKNESSES, and what stays silent")
    print("=" * 96)
    events = [("a refill of the same oil, same recipe", max(spreads)),
              ("Kiendler 6 → 7 drops (~1.4× concentration)",
               abs(series(valueOf, "20260801A").mean() - series(valueOf, "20260801C").mean())),
              ("⛔ HALF concentration + filtered",
               abs(series(valueOf, "20260804A").mean() - series(valueOf, "20260807D").mean())),
              ("⛔ LAMP SWAP, same oil (Sansi V2 → Yuji)",
               abs(valueOf("20260808A/001.pdf") - valueOf("20260808B/001.pdf"))),
              ("green oil → brown oil", span)]
    for label, delta in events:
        print("   %-46s |ΔV| %6.2f   %s"
              % (label, delta, "FIRES" if delta > TRACKER_BAND else "silent"))


if __name__ == "__main__":
    main()
