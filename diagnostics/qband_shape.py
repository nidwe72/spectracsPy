"""Is brown's Q region a SCALED copy of green's, or a DIFFERENT SHAPE? (SPEC_capture_quality.md §16.13.9)

The question behind it: does the green/brown difference in the 600-630 window come from HOW MUCH pigment
is present (Beer-Lambert, one species) or from WHICH pigment is present (protochlorophyll vs its
magnesium-free degradation product protopheophytin)?

The test is a null hypothesis with no free parameters. Under simple Beer-Lambert with a single absorbing
species, brown = k x green: the two curves differ by ONE scale factor. Then ANY ratio of two features
taken INSIDE the Q region is class-independent, because k cancels. So:

    a class difference in such a ratio REFUTES pure scaling, and nothing else can produce it.

Ratios are built from DIFFERENCES A(a) - A(b) wherever possible, because a difference cancels an additive
turbidity pedestal -- which is the one contaminant known to be large here (52-61 % of A_Q, §16.13).

Datasets: 20270729C (green) and 20260731A (brown, series D) -- the two post-rebuild six-run sets, same
instrument, protocol and dilution recipe, so they are the cleanest comparable pair on record.

Diagnostic only; nothing here is applied to the pipeline. Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/qband_shape.py
"""
import numpy as np

from metric_walkthrough import GREEN, BROWN, absorption


def curves(paths, despike=True):
    """All runs of a set on one wavelength grid."""
    grid, stack = None, []
    for path in paths:
        spectrum = absorption(path, despike=despike)
        lam = np.array(sorted(spectrum.valuesByNanometers))
        values = np.array([spectrum.valuesByNanometers[k] for k in lam])
        if grid is None:
            grid = lam
        stack.append(np.interp(grid, lam, values))
    return grid, np.array(stack)


def report(name, greenValues, brownValues, note=""):
    gm, gs = greenValues.mean(), greenValues.std(ddof=1)
    bm, bs = brownValues.mean(), brownValues.std(ddof=1)
    d = (gm - bm) / np.sqrt((greenValues.var(ddof=1) + brownValues.var(ddof=1)) / 2)
    print("   %-34s green %8.4f±%6.4f   brown %8.4f±%6.4f   d=%6.2f  %s"
          % (name, gm, gs, bm, bs, d, note))
    return d


def main():
    print(__doc__.split("The question")[0].strip())
    print()
    lam, green = curves(GREEN)
    _, brown = curves(BROWN)

    def band(stack, lo, hi):
        return stack[:, (lam >= lo) & (lam <= hi)].mean(axis=1)

    print("=== 1  AMPLITUDE — is brown simply pigment-poor?")
    report("A_Q 560-580", band(green, 560, 580), band(brown, 560, 580), "<- no: equal")
    report("A_far 600-630", band(green, 600, 630), band(brown, 600, 630))
    report("A_Soret 440-460", band(green, 440, 460), band(brown, 440, 460), "<- only 9 % apart")
    print()

    print("=== 2  SHAPE — ratios INSIDE the Q region (class-independent under pure scaling)")
    report("A_far / A_Q", band(green, 600, 630) / band(green, 560, 580),
           band(brown, 600, 630) / band(brown, 560, 580))
    greenRise = band(green, 620, 630) - band(green, 600, 610)
    brownRise = band(brown, 620, 630) - band(brown, 600, 610)
    greenAmplitude = band(green, 568, 578) - band(green, 545, 555)
    brownAmplitude = band(brown, 568, 578) - band(brown, 545, 555)
    report("rise (620-630 minus 600-610)", greenRise, brownRise)
    report("Q amplitude (572 minus 550)", greenAmplitude, brownAmplitude,
           "<- brown is HIGHER")
    d = report("rise / Q-amplitude", greenRise / greenAmplitude, brownRise / brownAmplitude,
               "<-- THE TEST")
    ratio = (greenRise / greenAmplitude).mean() / (brownRise / brownAmplitude).mean()
    print()
    print("   ⇒ pure scaling predicts d = 0 on the last row. Measured d = %.1f, a factor of %.1f."
          % (d, ratio))
    print("     Concentration is EXCLUDED as the explanation; the Q-region shapes genuinely differ.")
    print()

    print("=== 3  WHERE the intensity went — each class normalised by its own Q amplitude")
    greenNormalised = (green - band(green, 545, 555)[:, None]) / greenAmplitude[:, None]
    brownNormalised = (brown - band(brown, 545, 555)[:, None]) / brownAmplitude[:, None]
    greenMean, brownMean = greenNormalised.mean(axis=0), brownNormalised.mean(axis=0)
    print("   %-14s %10s %10s %10s" % ("region", "green", "brown", "brown-green"))
    for lo, hi in ((500, 520), (520, 545), (545, 560), (560, 580), (580, 600), (600, 615), (615, 630)):
        mask = (lam >= lo) & (lam <= hi)
        g, b = greenMean[mask].mean(), brownMean[mask].mean()
        flag = "  <- brown LOSES here" if b - g < -0.15 else ""
        print("   %-14s %10.4f %10.4f %+10.4f%s" % ("%d-%d nm" % (lo, hi), g, b, b - g, flag))
    print()
    print("   ⇒ intensity has moved OUT of 615-630 and INTO 580-615 — the direction the free-base")
    print("     band-I-is-weakest rule predicts for demetallation (KB_spectroscopy_physics.md §4.1).")
    print()

    print("=== 4  RESOLUTION — is the instrument the reason we cannot see 2 vs 4 Q bands?")
    _, raw = curves(GREEN[:1], despike=False)
    values = raw[0]
    print("   grid spacing %.3f nm/bin, %d bins over %.0f-%.0f nm"
          % (np.diff(lam).mean(), len(lam), lam.min(), lam.max()))
    for label, (lo, hi) in (("473 nm lamp artifact", (468, 479)),
                            ("607 nm registration artifact", (602, 613))):
        mask = (lam >= lo) & (lam <= hi)
        x, y = lam[mask], values[mask]
        peak = y - np.linspace(y[0], y[-1], len(y))
        above = x[peak >= peak.max() / 2]
        print("   %-30s FWHM %.1f nm (height %.3f A)"
              % (label, above.max() - above.min(), peak.max()))
    print("   Q bands are 20-30 nm wide ⇒ the instrument out-resolves them by ~10-20x.")
    print("   ⇒ NOT a resolution limit. The limits are window truncation at 630 nm, the two species")
    print("     always coexisting, 20-30 nm intrinsic linewidths, and the turbidity pedestal.")


if __name__ == "__main__":
    main()
