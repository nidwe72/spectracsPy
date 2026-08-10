"""M with the Soret window trimmed to 448-460, against the shipped 440-460, on every run from 2026-07-29 on.

Edwin 2026-08-06: *"show me metric measured from 448 versus the metric as is ... for the measurement
including and after the 29th July"*. `SPEC_metric_research.md` §7.13 measured the trim on the whole
archive; this narrows it to the POST-REBUILD data only (§16.11 rig rebuild, 2026-07-29 onward), which
is the only data captured under today's optics.

Nothing changes but the Soret window: same de-spiked absorbance, same Q band, same SHIPPED linear
baseline anchors (520-540 + 620-630). So every difference below is the eight nanometres.

⚠ The two columns are on DIFFERENT SCALES -- trimming removes the largest absorbance in the numerator,
so M448 is systematically lower. Only the SPREAD and SEPARATION columns compare like with like; the
verdict threshold 4.4 belongs to the 440 scale alone and is not applied to the 448 one.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/soret_448_since_0729.py
"""
import numpy as np

from settling_sweep import BASE, despikedAbsorption, asArrays, plugin, feature

# ⚠ THE PAIR INVERTED on 2026-08-10: 448-460 IS the shipped window now (SPEC_soret_448_trim.md §2), so the
# comparison this script exists for is "what the trim did", read against the frozen old window. The columns
# keep their published headings -- "M 440-460" is the legacy scale, "M 448-460" is what the app now computes.
SHIPPED = plugin.PB_SORET_BAND_LEGACY_440    # (440, 460) -- the window this script's tables were published on
TRIMMED = plugin.PB_SORET_BAND               # (448, 460) -- now shipped; was §7.13's proposal
Q = plugin.PB_Q_BAND
WINDOWS = plugin.PB_BASELINE_WINDOWS         # the SHIPPED anchors, 520-540 + 620-630 (§16.20)

# Every fill captured on or after 2026-07-29, in capture order. Labels from §16.15's roster
# (SPEC_capture_quality.md line ~6417). The 2027 in three folder names is a rig clock typo, kept as-is
# because the paths are cited throughout §16.
SETS = [("20270729B", "Steirerkraft B", "green", 6),
        ("20270729C", "Steirerkraft C", "green", 6),
        ("20270729A_aged24h", "Steirerkraft A aged24h", "aged", 3),
        ("20260731A", "S-Budget (series D)", "brown", 6),
        ("20260801A", "Kiendler A", "green", 6),
        ("20260801B", "Kiendler B", "green", 2),
        ("20260801C", "Kiendler C", "green", 2),
        ("20260804A", "Steirerkraft half-strength", "green", 6)]


def metrics(path):
    """(M440, M448) for one run -- same spectrum, same baseline, two numerator windows."""
    corrected = feature.linearBaselineCorrected(despikedAbsorption(path), WINDOWS)
    lam, values = asArrays(corrected)

    def band(window):
        return float(values[(lam >= window[0]) & (lam <= window[1])].mean())

    q = band(Q)
    return band(SHIPPED) / q, band(TRIMMED) / q


def cohensD(a, b):
    """Pooled-sd effect size between two groups."""
    a, b = np.array(a), np.array(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled


def main():
    print("Soret shipped %s   vs   trimmed %s      Q %s   baseline %s\n"
          % (SHIPPED, TRIMMED, Q, WINDOWS))

    perSet = {}
    print("=== PER RUN")
    print("%-24s %-4s %-6s %9s %9s %8s" % ("fill", "run", "class", "M 440-460", "M 448-460", "delta"))
    print("-" * 66)
    for folder, label, klass, count in SETS:
        values440, values448 = [], []
        for index in range(1, count + 1):
            m440, m448 = metrics("%s/%03d.pdf" % (folder, index))
            values440.append(m440)
            values448.append(m448)
            print("%-24s %-4s %-6s %9.3f %9.3f %7.1f%%"
                  % (label if index == 1 else "", "%03d" % index, klass if index == 1 else "",
                     m440, m448, 100.0 * (m448 - m440) / m440))
        perSet[label] = (klass, np.array(values440), np.array(values448))
        print("-" * 66)

    print("\n=== PER FILL -- mean, and the CV that decides whether the trim is worth anything")
    print("%-24s %-6s %2s %9s %7s %9s %7s %8s"
          % ("fill", "class", "n", "M 440", "CV", "M 448", "CV", "CV change"))
    print("-" * 80)
    for label, (klass, a, b) in perSet.items():
        cvA, cvB = 100.0 * a.std(ddof=1) / a.mean(), 100.0 * b.std(ddof=1) / b.mean()
        print("%-24s %-6s %2d %9.3f %6.2f%% %9.3f %6.2f%% %+7.2f pp"
              % (label, klass, len(a), a.mean(), cvA, b.mean(), cvB, cvB - cvA))

    print("\n=== SEPARATION -- the only like-for-like comparison across the two scales")
    green = [label for label, (klass, _, _) in perSet.items() if klass == "green"]
    brown = [label for label, (klass, _, _) in perSet.items() if klass == "brown"]
    aged = [label for label, (klass, _, _) in perSet.items() if klass == "aged"]

    def pool(labels, column):
        return np.concatenate([perSet[label][column] for label in labels]) if labels else np.array([])

    print("%-46s %9s %9s %8s" % ("comparison", "d @ 440", "d @ 448", "change"))
    print("-" * 76)
    for name, left, right in (("green fills  vs  brown (S-Budget)", green, brown),
                              ("green fills  vs  24 h-aged Steirerkraft", green, aged),
                              ("Steirerkraft (fresh)  vs  Kiendler", ["Steirerkraft B", "Steirerkraft C"],
                               ["Kiendler A", "Kiendler B", "Kiendler C"])):
        if not left or not right:
            continue
        dA = cohensD(pool(left, 1), pool(right, 1))
        dB = cohensD(pool(left, 2), pool(right, 2))
        print("%-46s %9.2f %9.2f %+7.1f%%" % (name, dA, dB, 100.0 * (dB - dA) / dA))

    print("\n=== DILUTION SPREAD -- same oil, two strengths (Steirerkraft archive vs half-strength)")
    strong = pool(["Steirerkraft B", "Steirerkraft C"], 1)
    weak = perSet["Steirerkraft half-strength"][1]
    strong448 = pool(["Steirerkraft B", "Steirerkraft C"], 2)
    weak448 = perSet["Steirerkraft half-strength"][2]
    print("  @ 440-460   strong %.3f   half-strength %.3f   spread %+.1f%%"
          % (strong.mean(), weak.mean(), 100.0 * (weak.mean() - strong.mean()) / strong.mean()))
    print("  @ 448-460   strong %.3f   half-strength %.3f   spread %+.1f%%"
          % (strong448.mean(), weak448.mean(), 100.0 * (weak448.mean() - strong448.mean()) / strong448.mean()))


if __name__ == "__main__":
    main()
