"""§7.14 — the orthodox scatter corrections, priced against our window.

(docs/SPEC_metric_research.md §7.14. Edwin 2026-08-05: "that's a real, standard technique — make a web
research on this and tell me what and how we could use this.")

The wider spectroscopy community has standard machinery for removing a scattering pedestal. This prices the
two that are testable OFF-LINE against the shipped linear (= Morton-Stubbs) baseline. Both fail, and the
FAILURE MODES are the deliverable, not the metric numbers:

  ROUTE E  lambda^-n turbidity baseline. Physics-matched -- scattering IS a power law -- and it is the
           correction the literature reaches for first. It needs a SCATTERING-ONLY anchor to fit `n` on.
           ⭐ Ours is not one: the far window RISES 2.3x toward the red where scattering must FALL, so no
           physical exponent exists and curve_fit rails at its bound. That is the cleanest disproof of
           assumption A6 (a quiet far anchor) in the whole research -- it rests on no metric comparison,
           the fit simply has no admissible solution.

  ROUTE B' 2nd derivative, re-run as a |d2A| band ratio. Annihilates any locally-quadratic baseline exactly,
           so it needs no anchor at all -- but it needs CURVATURE, and a flank has none. Reproduces §7.7's
           route-B result from a different formulation.

⚠ This CONFIRMS §7.8 rather than extending it: §7.8 closed four routes from the inside and concluded the
problem is "30 nm of missing spectrum". The external literature turns out to need precisely the same 30 nm
for its own independent reasons. Two disjoint arguments, one fix.

⚠ The `n` column is the point of the first table. Read it before the metric columns.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/scatter_correction_audit.py
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter

from settling_sweep import despikedAbsorption, asArrays, plugin

NEAR, FAR = plugin.PB_BASELINE_WINDOWS
SORET, Q = plugin.PB_SORET_BAND, plugin.PB_Q_BAND
PIVOT = 530.0          # the power law's amplitude is quoted AT this wavelength
SG_WINDOW = 101        # 101 bins x 0.146 nm = 14.7 nm -- narrower than any band here

# The post-rebuild corpus (§2), plus the 20260804A controls as an out-of-sample check. 002 (exposure
# artifact) and 006 (turbidity event) are held out on purpose -- see SPEC_capture_quality.md §16.24.
#
# ⚠ `20260804A ctrl` is class "outOfSample", NOT "green", and that is deliberate. §2's corpus is the
# post-rebuild archive; 20260804A is a different session at ~55 % of its concentration and filtered, so
# pooling it into the green class would inflate the green spread with a dilution axis and understate every
# Cohen's d below. It is carried here only as an out-of-sample sanity column.
SETS = [("20260804A ctrl", "outOfSample", ["20260804A/%03d.pdf" % i for i in (1, 3, 4, 5)]),
        ("Steirerkraft B", "green", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft C", "green", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
        ("Kiendler A", "green", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
        ("S-Budget D", "brown", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]
ARTIFACTS = [("002 exp-90", "20260804A/002.pdf"), ("006 turbid", "20260804A/006.pdf")]


def anchorMask(lam):
    mask = np.zeros_like(lam, dtype=bool)
    for low, high in (NEAR, FAR):
        mask |= (lam >= low) & (lam <= high)
    return mask


def linearBaseline(lam, values):
    """The SHIPPED baseline: equal total weight per window, so a wider window cannot dominate (§16.10.9)."""
    x, y, w = [], [], []
    for low, high in (NEAR, FAR):
        inWindow = (lam >= low) & (lam <= high)
        x += list(lam[inWindow]); y += list(values[inWindow])
        w += [1.0 / inWindow.sum()] * inWindow.sum()
    x, y, w = np.array(x), np.array(y), np.array(w)
    weights = np.diag(w)
    design = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.solve(design.T @ weights @ design, design.T @ weights @ y)
    return slope * lam + intercept


def powerLawBaseline(lam, values):
    """`A = s*(PIVOT/lam)**n` through the same anchors. Returns (baseline, n) -- n is the interesting one.

    n is bounded to [-4, 8]. A NEGATIVE n means the fit rises toward the red, which no scattering law does;
    railing at -4 is therefore not a numerical nuisance but the RESULT (§7.14.2).
    """
    mask = anchorMask(lam)
    x, y = lam[mask], values[mask]

    def model(wavelength, amplitude, exponent):
        return amplitude * (PIVOT / wavelength) ** exponent

    try:
        (amplitude, exponent), _ = curve_fit(model, x, y, p0=[max(y.mean(), 1e-4), 4.0],
                                             bounds=([0.0, -4.0], [np.inf, 8.0]), maxfev=20000)
    except RuntimeError:
        return None, float("nan")
    return model(lam, amplitude, exponent), exponent


def bandRatio(lam, values, baseline):
    corrected = values - baseline
    band = lambda window: corrected[(lam >= window[0]) & (lam <= window[1])].mean()
    return band(SORET) / band(Q)


def secondDerivativeRatio(lam, values):
    """|d2A| peak in the Soret band over |d2A| peak in the Q band -- no baseline, no anchor (route B')."""
    step = float(np.median(np.diff(lam)))
    second = savgol_filter(values, SG_WINDOW, 3, deriv=2, delta=step)
    peak = lambda window: np.abs(second[(lam >= window[0]) & (lam <= window[1])]).max()
    return peak(SORET) / peak(Q)


def measure(path):
    lam, values = asArrays(despikedAbsorption(path))
    baseline, exponent = powerLawBaseline(lam, values)
    return {"linear": bandRatio(lam, values, linearBaseline(lam, values)),
            "power": None if baseline is None else bandRatio(lam, values, baseline),
            "n": exponent,
            "d2": secondDerivativeRatio(lam, values),
            "near": values[(lam >= NEAR[0]) & (lam <= NEAR[1])].mean(),
            "far": values[(lam >= FAR[0]) & (lam <= FAR[1])].mean()}


def cohen(green, brown):
    pooled = np.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                     / (len(green) + len(brown) - 2))
    return (green.mean() - brown.mean()) / pooled


def main():
    rows = {name: (klass, [measure(p) for p in paths]) for name, klass, paths in SETS}

    print("=== ROUTE E — lambda^-n power-law baseline against the SHIPPED linear (Morton-Stubbs) baseline\n")
    print("%-16s %4s %10s %9s %10s %9s %9s" % ("set", "n", "linear", "CV", "power", "CV", "n fitted"))
    print("-" * 72)
    for name, _, _ in SETS:
        _, got = rows[name]
        lin = np.array([g["linear"] for g in got])
        pw = np.array([g["power"] for g in got if g["power"] is not None])
        cv = lambda a: 100 * a.std(ddof=1) / a.mean()
        print("%-16s %4d %10.3f %8.2f %% %10.3f %8.2f %% %9.2f"
              % (name, len(got), lin.mean(), cv(lin), pw.mean(), cv(pw),
                 np.mean([g["n"] for g in got])))

    print("\n⭐ WHY n RAILS — scattering must FALL toward the red; ours RISES:")
    for name, _, _ in SETS:
        _, got = rows[name]
        near, far = np.mean([g["near"] for g in got]), np.mean([g["far"] for g in got])
        print("   %-16s near %.4f   far %.4f   far/near = %.2f%s"
              % (name, near, far, far / near, "   <-- no physical n exists" if far > near else ""))

    print("\n=== the two held-out artifact runs (do the corrections rescue either?)")
    controlLin = np.array([g["linear"] for g in rows["20260804A ctrl"][1]])
    controlPow = np.array([g["power"] for g in rows["20260804A ctrl"][1]])
    for label, path in ARTIFACTS:
        got = measure(path)
        print("   %-12s linear %+7.1f %%   power-law %+7.1f %%   (vs the 20260804A controls)"
              % (label, 100 * (got["linear"] / controlLin.mean() - 1),
                 100 * (got["power"] / controlPow.mean() - 1)))

    print("\n=== CLASS SEPARATION — the number that decides it")
    for key, label in (("linear", "LINEAR (shipped)"), ("power", "POWER-LAW"), ("d2", "2nd DERIVATIVE")):
        green = np.concatenate([[g[key] for g in got] for name, (klass, got) in rows.items()
                                if klass == "green"])
        brown = np.array([g[key] for g in rows["S-Budget D"][1]])
        print("   %-18s green %7.3f ± %.3f   brown %7.3f ± %.3f   d = %5.2f   overlap = %s"
              % (label, green.mean(), green.std(ddof=1), brown.mean(), brown.std(ddof=1),
                 cohen(green, brown), "YES" if green.min() < brown.max() else "no"))

    print("\n⇒ Both alternatives are WORSE. Route E has no admissible exponent (A6 is false); route B' has")
    print("  no curvature to differentiate (§7.7 again). Every orthodox method needs either an")
    print("  absorption-free region or a resolved peak — §7.8's missing 30 nm, from the outside.")


if __name__ == "__main__":
    main()
