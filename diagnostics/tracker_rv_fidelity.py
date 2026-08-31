"""Can `Rv` be the history tracker, and at what alarm level? (Edwin, 2026-08-31)

Reproduces every number in `SPEC_history_tracker.md`'s **2026-08-31 POSITION**. ⛔ This file exists because
that spec's rule is that a figure is COMPUTED, never typed: a σ moves the moment another fill is measured,
and a typed one goes stale silently.

⭐ IT READS THE SUITE, NOT THE ARCHIVE. `20280831_suite` is every fill confirmed same-jar AND 6-min
cold-box (`SPEC_metric_research.md` §16.15.7), so method and recipe are held constant and what is left is
the fill and the instrument. That is the only corpus here on which a tracker question has an answer without
a protocol term in it.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/tracker_rv_fidelity.py
"""
import os
import sys
import tempfile
from math import erf, sqrt

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive

SUITE = "20280831_suite"
BASELINE_FILLS = 3          # the reference a check is compared against, established once
DN_PER_A = 0.0100           # 1 count at the 624 window, `SPEC_capture_quality.md` §16.40.2
ALARMS = (8, 10, 12, 15, 20, 25)
CHANGES = (10, 20, 30)
MONTHS, HISTORIES, DRIFT_PER_MONTH = 24, 4000, 2.0

normal = lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0)))


def oilOf(session):
    for key, name in (("JaNat", "Ja Natuerlich"), ("SparS", "Spar S-Budget"),
                      ("Lugitsch", "Lugitsch"), ("Steirerkraft", "Steirerkraft")):
        if key in session:
            return name
    return session


def fills():
    """`{oil: [(fill mean Rv, fill mean 624 band), ...]}` over the suite."""
    band = lambda nm, a, low, high: float(numpy.mean(a[(nm >= low) & (nm <= high)]))
    out = {}
    base = os.path.join(archive.ARCHIVE, SUITE)
    with tempfile.TemporaryDirectory() as scratch:
        for session in sorted(os.listdir(base)):
            folder = os.path.join(base, session)
            if not os.path.isdir(folder):
                continue
            runs = []
            for name in sorted(f for f in os.listdir(folder) if f.endswith(".pdf")):
                workflow = archive.workflowOf(os.path.join(folder, name), scratch)
                nm, absorbance = archive.despikedTrace(workflow)
                valley = band(nm, absorbance, 500.0, 560.0)
                qBand = band(nm, absorbance, 565.0, 580.0)
                red = band(nm, absorbance, 622.0, 627.0)
                runs.append((100.0 * (red - valley) / (qBand - valley), red - valley))
            out.setdefault(oilOf(session), []).append(numpy.array(runs).mean(axis=0))
    return {oil: numpy.array(v) for oil, v in out.items()}


def perOil(data):
    print("PER OIL, in the suite (one method, one recipe)\n")
    print("%-15s %6s %8s %9s %9s %16s %16s"
          % ("oil", "fills", "Rv", "sigma_fill", "624 band", "1 fill detects", "3 fills detect"))
    weighted = []
    for oil, v in sorted(data.items(), key=lambda kv: -kv[1][:, 0].mean()):
        means, bands = v[:, 0], v[:, 1]
        sigma = means.std(ddof=1)
        weighted.append((len(means) - 1, sigma))
        detect = lambda n: 2.77 * sigma / sqrt(n)
        print("%-15s %6d %8.1f %9.2f %6.4f=%2.0fDN %7.1f (%4.1f %%) %7.1f (%4.1f %%)"
              % (oil, len(means), means.mean(), sigma, bands.mean(), bands.mean() / DN_PER_A,
                 detect(1), 100 * detect(1) / means.mean(),
                 detect(3), 100 * detect(3) / means.mean()))
    # ⛔ POOLED OVER DEGREES OF FREEDOM, not over oils: a two-fill sigma carries 1 df and must not weigh the
    # same as a six-fill one. ⚠ Only the oils with >=3 fills contribute — see the spec on why 1 df is unusable.
    usable = [(df, sigma) for df, sigma in weighted if df >= 2]
    pooled = sqrt(sum(df * sigma ** 2 for df, sigma in usable) / sum(df for df, _ in usable))
    df = sum(df for df, _ in usable)
    # ⚠ chi-square bounds on a standard deviation, the reason a two-fill sigma cannot be banked.
    from scipy.stats import chi2
    lo = pooled * sqrt(df / chi2.ppf(0.975, df))
    hi = pooled * sqrt(df / chi2.ppf(0.025, df))
    print("\n   pooled sigma_fill = %.2f Rv on %d df   95 %% CI [%.2f, %.2f]" % (pooled, df, lo, hi))
    return pooled, lo, hi


def dial(pooled):
    """⛔⛔ BOTH ERROR RATES IN ONE TABLE. Quoting a detection rate and a false-alarm rate for two DIFFERENT
    alarm levels in adjacent sentences reads as a contradiction — it happened, on 2026-08-31 — and the fix
    is to never separate them again."""
    sd = pooled * sqrt(1.0 + 1.0 / BASELINE_FILLS)
    print("\nTHE DIAL — one wobble of %.2f Rv on a check against a %d-fill baseline\n" % (sd, BASELINE_FILLS))
    print("%9s | %-22s | catches a REAL change of %s"
          % ("alarm at", "cries wolf", " / ".join("%d" % c for c in CHANGES)))
    print("-" * 74)
    for alarm in ALARMS:
        false = 2 * (1 - normal(alarm / sd))
        caught = [100 * ((1 - normal((alarm - c) / sd)) + normal((-alarm - c) / sd)) for c in CHANGES]
        print("%7d Rv | 1 in %-17s | %s"
              % (alarm, "{:,.0f}".format(1 / false) if false > 1e-9 else ">1e9",
                 "  ".join("%5.0f %%" % c for c in caught)))
    print("\n   read ACROSS: lowering the alarm raises BOTH columns -- that is the whole trade.")
    print("   read DOWN  : a change EQUAL to the setting is caught ~50 %, because it lands on the line.")
    return sd


def service(sd):
    print("\nIN SERVICE — %d monthly checks, %d simulated histories, an oil falling %.0f Rv a month\n"
          % (MONTHS, HISTORIES, DRIFT_PER_MONTH))
    generator = numpy.random.default_rng(1)
    truth = numpy.array([-DRIFT_PER_MONTH * month for month in range(MONTHS)])
    print("%9s | %-26s | %s" % ("alarm at", "false alarms in %d months" % MONTHS,
                                "drifting oil first trips (median) / its REAL drift"))
    print("-" * 88)
    for alarm in ALARMS:
        steady = generator.normal(0.0, sd, (HISTORIES, MONTHS))
        drift = truth + generator.normal(0.0, sd, (HISTORIES, MONTHS))
        tripped = numpy.abs(drift) > alarm
        month = numpy.where(tripped.any(axis=1), numpy.argmax(tripped, axis=1), numpy.nan)
        median = numpy.nanmedian(month)
        print("%7d Rv | %-26.2f | month %2.0f, real drift %4.1f Rv"
              % (alarm, numpy.mean(numpy.sum(numpy.abs(steady) > alarm, axis=1)),
                 median, DRIFT_PER_MONTH * median))


def referenceTilt():
    """⛔ How much of the wobble may be the LAMP. `Rv = 100(A624-Av)/(A_Q-Av)` with `A = log10(R/S)`, so a
    shift in the REFERENCE's own red/Q ratio moves `Rv` on an identical sample."""
    band = lambda nm, v, low, high: float(numpy.mean(v[(nm >= low) & (nm <= high)]))
    ratios = []
    base = os.path.join(archive.ARCHIVE, SUITE)
    with tempfile.TemporaryDirectory() as scratch:
        for session in sorted(os.listdir(base)):
            folder = os.path.join(base, session)
            if not os.path.isdir(folder):
                continue
            name = sorted(f for f in os.listdir(folder) if f.endswith(".pdf"))[0]
            workflow = archive.workflowOf(os.path.join(folder, name), scratch)
            for phase in workflow["phases"]:
                for step in phase.get("steps", []):
                    raw = (step.get("spectra") or {}).get("REFERENCE")
                    if raw is None:
                        continue
                    values = raw.get("valuesByNanometers", raw)
                    mapping = {float(k): float(v) for k, v in values.items()}
                    nm = numpy.array(sorted(mapping))
                    reference = numpy.array([mapping[k] for k in nm])
                    ratios.append(100.0 * band(nm, reference, 622.0, 627.0)
                                  / band(nm, reference, 565.0, 580.0))
                    break
                else:
                    continue
                break
    ratios = numpy.array(ratios)
    print("\nHOW MUCH OF THE WOBBLE MAY BE THE LAMP — the reference's own R(622-627)/R(565-580)\n")
    print("   over the suite: mean %.2f %%   sd %.2f   spread %.2f" % (ratios.mean(), ratios.std(ddof=1),
                                                                       ratios.max() - ratios.min()))
    for shift, label in ((ratios.std(ddof=1), "one sd"), (ratios.max() - ratios.min(), "the full spread")):
        for oil, denominator in (("green", 0.101), ("brown", 0.168)):
            print("   %-16s %5.2f %%  ->  %-5s Rv moves %5.2f on an IDENTICAL sample"
                  % (label, shift, oil, 100.0 * numpy.log10(1.0 + shift / 100.0) / denominator))


def main():
    data = fills()
    pooled, _, _ = perOil(data)
    sd = dial(pooled)
    service(sd)
    referenceTilt()


if __name__ == "__main__":
    main()
