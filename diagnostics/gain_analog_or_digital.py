"""Is the camera's GAIN analog or digital? (SPEC_capture_quality.md §16.23.6c / §14.9)

WHY IT MATTERS. `SPEC_metric_research.md` §7.13 measured that the 440-447 nm bins read 2.0-2.6 DN against a
reference near 88, and that those bins contribute 28 % of `r_Q`. The blue end is almost certainly
QUANTISATION-limited there: +-0.5 DN on 2.3 DN is +-20 %.

  * If the camera's gain is ANALOG -- applied before the ADC -- raising it spreads the same photons over
    more codes, so the quantisation error shrinks in proportion. That fixes the blue floor IN SOFTWARE.
  * If it is DIGITAL -- a multiply after the ADC -- it multiplies an already-quantised number and buys
    NOTHING. The blue floor then needs a bluer source, which is a purchase.

§16.23.6 showed that the DN guard and the `A_Q` window cannot both be met by any dilution, and that raising
R in the blue is the only route out that costs nothing. This script decides whether that route is open.

THE DECISIVE TEST -- HISTOGRAM GAPS. A digital gain of factor k maps ADC code n to k*n, so the output can
only take multiples of k: the histogram develops GAPS at every value not divisible by k. An analog gain
raises the signal before quantisation, so every code stays reachable and the histogram stays dense.

  gap fraction ~ 0  => ANALOG  (or the gain control does nothing at all -- checked separately)
  gap fraction > 0  => DIGITAL

Two supporting checks, because a single indicator can mislead:
  2  Does the MEAN actually move? A control that is accepted but ignored is common on UVC cameras.
  3  Does the NOISE-TO-SIGNAL ratio hold? Analog gain preserves it; digital gain preserves it too, but a
     digital gain cannot IMPROVE the quantisation floor, which is the whole point. Reported for the record.

⚠ Run with the rig in its normal state. Nothing here writes to the camera permanently -- gain and exposure
are restored on exit -- but it does grab frames, so do not run it during a measurement.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/gain_analog_or_digital.py
"""
import numpy as np
import cv2

DEVICE = 0
WARMUP = 12                     # frames to discard after any control change (AE/WB settle, §14.8's C2)
SAMPLES = 6                     # frames averaged per gain setting
GAINS = [0, 16, 32, 64, 128]    # probed; the camera's own range is read first and this is clipped to it


def grab(capture, count):
    frames = []
    for _ in range(count):
        ok, frame = capture.read()
        if ok:
            frames.append(frame)
    return frames


def gapFraction(values):
    """Fraction of the occupied code range that has ZERO counts -- the digital-gain signature.

    Restricted to the occupied span so that an image simply not using the top of the range does not
    register as gaps.
    """
    counts = np.bincount(values.ravel(), minlength=256)
    occupied = np.nonzero(counts)[0]
    if len(occupied) < 8:
        return float("nan")
    span = counts[occupied.min():occupied.max() + 1]
    return float((span == 0).mean())


def main():
    capture = cv2.VideoCapture(DEVICE)
    if not capture.isOpened():
        print("⛔ cannot open /dev/video%d" % DEVICE)
        return

    # Freeze everything that could move under us, so the only variable is gain.
    capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)      # 1 = manual on V4L2/UVC
    capture.set(cv2.CAP_PROP_AUTO_WB, 0)
    capture.set(cv2.CAP_PROP_EXPOSURE, 250)
    grab(capture, WARMUP)

    original = capture.get(cv2.CAP_PROP_GAIN)
    print("=== CAMERA: ELP 32e4:8830 on /dev/video%d" % DEVICE)
    print("   gain reads back as %.1f before we touch it" % original)
    print("   exposure fixed at 250, auto-exposure and auto-WB OFF\n")

    print("   %-8s %10s %10s %10s %12s %10s" % ("gain set", "reads", "mean DN", "sd DN", "gap frac", "verdict"))
    print("   " + "-" * 68)
    rows = []
    for gain in GAINS:
        capture.set(cv2.CAP_PROP_GAIN, gain)
        readBack = capture.get(cv2.CAP_PROP_GAIN)
        grab(capture, WARMUP)
        frames = grab(capture, SAMPLES)
        if not frames:
            print("   %-8d  (no frames)" % gain)
            continue
        # the BLUE channel is the one that matters -- it is what sees 440 nm
        blue = np.concatenate([f[:, :, 0].ravel() for f in frames])
        gaps = gapFraction(blue)
        rows.append((gain, readBack, blue.mean(), blue.std(), gaps))
        print("   %-8d %10.1f %10.2f %10.2f %12.3f" % (gain, readBack, blue.mean(), blue.std(), gaps))

    capture.set(cv2.CAP_PROP_GAIN, original)
    capture.release()

    if len(rows) < 2:
        print("\n⛔ not enough settings responded to judge.")
        return

    means = np.array([r[2] for r in rows])
    reads = np.array([r[1] for r in rows])
    gaps = np.array([r[4] for r in rows])
    print("\n=== VERDICT\n")
    moved = (means.max() - means.min()) / means.mean() > 0.05
    accepted = (reads.max() - reads.min()) > 0
    print("   1. does the control READ BACK a change?      %s" % ("yes" if accepted else "⛔ NO"))
    print("   2. does the image mean actually MOVE?        %s  (%.2f -> %.2f DN)"
          % ("yes" if moved else "⛔ NO", means[0], means[-1]))
    worst = np.nanmax(gaps)
    print("   3. worst histogram gap fraction:             %.3f" % worst)
    print()
    if not accepted or not moved:
        print("   ⛔ THE GAIN CONTROL DOES NOTHING on this camera.")
        print("      Neither analog nor digital -- there is no software lever here, and the blue floor")
        print("      needs a bluer source or a longer exposure (§16.23.6c).")
    elif worst > 0.05:
        print("   ⛔ DIGITAL. The histogram develops gaps, so the gain multiplies an already-quantised")
        print("      value. It cannot improve the blue quantisation floor. §16.23.6's brightness route")
        print("      needs hardware.")
    else:
        print("   ⭐ ANALOG (no quantisation gaps). Raising gain spreads the same photons over more")
        print("      codes, so the blue floor CAN be improved in software. §16.23.6's conflict may be")
        print("      resolvable without a lamp purchase -- verify next on a real reference capture.")


if __name__ == "__main__":
    main()
