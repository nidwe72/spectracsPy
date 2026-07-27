"""Does RE-SEATING the cuvette tilt the spectrum? (SPEC_capture_quality.md §16.7.1, the last open candidate.)

Edwin's two blanks five minutes apart differed by a smooth 5% spectral tilt that swung the pigment ratio 20-28%.
Warm-up is excluded (measured: wrong sign, 3x too small) and the camera's controls are excluded (constant to the
digit for 12 minutes). What remains is that the cuvette was taken out and refilled between the two runs — and
re-seating it changes which part of the slit and grating is illuminated.

THE DESIGN — why it is not just "measure six times":

    round 1:  [capture BEFORE] -> "re-seat the cuvette" -> [capture AFTER]
    round 2:  [capture BEFORE] -> "re-seat the cuvette" -> [capture AFTER]   ...

The BEFORE of each round is taken WITHOUT touching anything since the previous AFTER. So the run yields two
paired sets over the same timescale:

    RE-SEAT deltas   (BEFORE_i  -> AFTER_i)   = re-seating + a little elapsed drift
    NO-TOUCH deltas  (AFTER_i   -> BEFORE_i+1) = elapsed drift + measurement noise ONLY

If re-seating is innocent the two distributions are indistinguishable. If it is the culprit, the re-seat deltas
stand out — and that is a controlled comparison, not a number floating on its own.

Put the SAME cuvette back each time (same liquid, same orientation if you can) — we are measuring the seating,
not the contents. Read-only: nothing is written to the app or the DB.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/cuvette_reseat_probe.py \
            --roi 564,907,2145,1782 \
            --coeffs=-5.77381138877048e-09,2.35944918200958e-05,0.116112996214963,331.935289341983
"""
import argparse
import os
import sys
import time

import numpy as np

from reference_drift_probe import PHOSPHOR, PUMP, QBAND, _appContext, _bandMean, _pickExposure, _spectrum

SORET = (440.0, 460.0)

# Sensitivity constants from Edwin's NowSteirerkraftB run (SPEC_capture_quality.md §16.7): with A_Soret = 0.801
# and A_Q = 0.144, a RELATIVE reference error d in a band moves that band's absorbance by 0.434*d, so the pigment
# ratio moves by 0.434*d/A. The Q band is ~5.6x more sensitive than the Soret band — that is the whole problem.
A_SORET, A_Q = 0.801, 0.144


def capture(backend, roi, coefficients, frames):
    stack, nanometers = [], None
    for index in range(frames):
        if index:
            time.sleep(0.7)             # ~1.5 fps at 2592x1944 — without this we re-read one buffered frame
        image = backend.read()
        if image is None:
            continue
        nanometers, values = _spectrum(image, roi, coefficients)
        stack.append(values)
    if not stack:
        return None
    values = np.median(np.array(stack), axis=0)
    level = float(np.mean(values))       # broad normaliser: the single max quantises by +-1 DN and would leak
    return {                             # ~2% of phantom ratio swing into every comparison
        "nm": nanometers, "values": values, "peak": float(values.max()), "level": level,
        "pump": _bandMean(nanometers, values, *PUMP),
        "phosphor": _bandMean(nanometers, values, *PHOSPHOR),
        "soretShare": _bandMean(nanometers, values, *SORET) / level,
        "qShare": _bandMean(nanometers, values, *QBAND) / level,
    }


def describe(label, sample):
    print("   %-22s pump %7.2f  phosphor %7.2f  ph/pump %7.4f  peak %6.1f"
          % (label, sample["pump"], sample["phosphor"], sample["phosphor"] / sample["pump"], sample["peak"]))


def delta(before, after):
    """What this change would have done to a measurement, in the units that matter."""
    tilt = (after["phosphor"] / after["pump"]) / (before["phosphor"] / before["pump"]) - 1.0
    soretError = after["soretShare"] / before["soretShare"] - 1.0
    qError = after["qShare"] / before["qShare"] - 1.0
    # A relative reference error d shifts absorbance by 0.434*d; the ratio error is the difference of the two
    # bands' contributions, each divided by that band's absorbance.
    ratioError = 0.434 * soretError / A_SORET - 0.434 * qError / A_Q
    return dict(tilt=tilt * 100, soret=soretError * 100, q=qError * 100, ratio=ratioError * 100,
                level=(after["level"] / before["level"] - 1.0) * 100)


def main():
    parser = argparse.ArgumentParser(description="Cuvette re-seating repeatability (SPEC_capture_quality §16.7.1)")
    parser.add_argument("--changes", type=int, default=6, help="number of cuvette re-seats (default 6)")
    parser.add_argument("--frames", type=int, default=8, help="frames averaged per capture")
    parser.add_argument("--warmup", type=float, default=300.0,
                        help="seconds to let the sensor settle before starting (measured: ~1.6%% over 10 min)")
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None)
    parser.add_argument("--relax", type=float, default=0.0,
                        help="after each re-seat, watch for N seconds instead of capturing once. THE "
                             "DISCRIMINATOR: liquid sloshing / mechanical settling RELAXES back over time, a "
                             "changed geometry is a permanent STEP. The last reading is used as the 'after'.")
    parser.add_argument("--roi", default=None, help="X1,Y1,X2,Y2")
    parser.add_argument("--coeffs", default=None, help="A,B,C,D px->nm cubic")
    arguments = parser.parse_args()

    context = _appContext()
    device = arguments.device if arguments.device is not None else context.get("device", 0)
    roi = [int(v) for v in arguments.roi.split(",")] if arguments.roi else context.get("roi")
    coefficients = ([float(v) for v in arguments.coeffs.split(",")] if arguments.coeffs
                    else context.get("coeffs"))
    if roi is None or coefficients is None:
        print("ERROR: need --roi X1,Y1,X2,Y2 and --coeffs A,B,C,D (read them off the calibration profile).")
        return 2

    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    exposure = arguments.exposure
    backend.open(deviceId=device, exposure=exposure or 150, whiteBalanceKelvin=6500)
    if exposure is None:
        exposure = _pickExposure(backend)
    print("camera %s at %s, exposure PINNED at %s, WB 6500 K" % (device, backend.getResolution(), exposure))

    if arguments.warmup > 0:
        print("\nletting the sensor settle for %.0f s (§16.7.1: ~1.6%% drift over the first ~10 min after the"
              " camera opens — do NOT touch the cuvette during this)" % arguments.warmup)
        settleEnd = time.time() + arguments.warmup
        while time.time() < settleEnd:
            backend.read()
            time.sleep(1.0)

    print("\nPut the SAME cuvette back each time — same liquid, same orientation if you can.")
    print("We are measuring the SEATING, not the contents.\n")

    rounds = []
    previousAfter = None
    for index in range(1, arguments.changes + 1):
        print("--- round %d of %d ---" % (index, arguments.changes))
        before = capture(backend, roi, coefficients, arguments.frames)
        if before is None:
            print("   no frames — aborting")
            break
        describe("before (untouched)", before)
        if previousAfter is not None:
            rounds.append(("no-touch", delta(previousAfter, before)))

        try:
            input("\n   >>> TAKE THE CUVETTE OUT AND PUT IT BACK IN, then press Enter ")
        except EOFError:
            print("   (non-interactive — continuing without a re-seat)")
        if arguments.relax > 0:
            print("   watching it settle for %.0fs — do NOT touch anything now" % arguments.relax)
            relaxEnd = time.time() + arguments.relax
            started, series = time.time(), []
            while time.time() < relaxEnd:
                sample = capture(backend, roi, coefficients, max(2, arguments.frames // 3))
                if sample is None:
                    break
                elapsed = time.time() - started
                tilt = ((sample["phosphor"] / sample["pump"])
                        / (before["phosphor"] / before["pump"]) - 1.0) * 100
                series.append((elapsed, tilt))
                print("      t=%5.0fs  ph/pump %7.4f   tilt vs before %+6.2f%%" % (elapsed, sample["phosphor"] / sample["pump"], tilt))
            after = sample
            if len(series) >= 3:
                # Settling shows as |tilt| shrinking from the first reading to the last; a geometry step holds.
                firstTilt, lastTilt = abs(series[0][1]), abs(series[-1][1])
                if firstTilt < 0.5:      # noise floor is ~0.26% — below this there is no jump to interpret
                    print("      -> initial jump %+.2f%% is within the noise floor: nothing was disturbed"
                          % series[0][1])
                else:
                    recovered = (firstTilt - lastTilt) / firstTilt * 100
                    print("      -> initial %+.2f%% settled to %+.2f%% (%.0f%% of the jump recovered) => %s"
                          % (series[0][1], series[-1][1], recovered,
                             "SETTLING (liquid / mechanics — it relaxes back)" if recovered > 50 else
                             "PERMANENT STEP (geometry — it stays put)" if recovered < 20 else
                             "MIXED: part settles, part is permanent"))
        else:
            after = capture(backend, roi, coefficients, arguments.frames)
        if after is None:
            print("   no frames — aborting")
            break
        describe("after re-seat", after)
        change = delta(before, after)
        rounds.append(("re-seat", change))
        previousAfter = after            # the NEXT round's "before" closes the no-touch control interval
        print("   -> tilt %+.2f%%, level %+.2f%%, would move the pigment ratio %+.1f%%\n"
              % (change["tilt"], change["level"], change["ratio"]))

    backend.release()

    reseats = [d for kind, d in rounds if kind == "re-seat"]
    notouch = [d for kind, d in rounds if kind == "no-touch"]
    if not reseats:
        return 0

    print("\n=== RESULT ===")
    print("%-12s %3s   %-22s %-22s %s" % ("", "n", "tilt (phosphor/pump)", "implied ratio swing", "level"))
    for label, group in (("re-seat", reseats), ("no-touch", notouch)):
        if not group:
            continue
        tilts = np.abs([d["tilt"] for d in group])
        ratios = np.abs([d["ratio"] for d in group])
        levels = np.abs([d["level"] for d in group])
        print("%-12s %3d   mean %5.2f%%  max %5.2f%%   mean %5.1f%%  max %5.1f%%   mean %5.2f%%"
              % (label, len(group), tilts.mean(), tilts.max(), ratios.mean(), ratios.max(), levels.mean()))

    if notouch:
        reseatTilt = np.abs([d["tilt"] for d in reseats]).mean()
        notouchTilt = np.abs([d["tilt"] for d in notouch]).mean()
        factor = reseatTilt / notouchTilt if notouchTilt else float("inf")
        print("\n  re-seating moves the spectrum %.1fx as much as leaving it alone." % factor)
        if factor >= 3.0:
            print("  => CUVETTE SEATING IS AN ERROR SOURCE. No warm-up protocol fixes this; the R->S->R' bracket")
            print("     (SPEC §16.7) catches it, and so would clamping/keying the cuvette holder.")
        elif factor <= 1.5:
            print("  => seating looks INNOCENT — re-seating is no worse than doing nothing. The 5% A/B tilt")
            print("     must then come from something else (the liquid itself, or an event we have not sampled).")
        else:
            print("  => inconclusive at this sample size; run more rounds (--changes 12).")
    print("\n  For scale: Edwin's A/B pair differed by 5.04% tilt, which swung the pigment ratio 20-28%.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
