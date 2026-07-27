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


def watchSettle(backend, roi, coefficients, frames, seconds, before):
    """Sample continuously for `seconds` after the jar was disturbed, printing the curve as it goes.

    Tilt is measured against the UNDISTURBED `before`, so the first reading is the jump the change caused and the
    last is what survives once it has settled. Those two numbers are the whole experiment: liquid slosh and
    mechanical settling DECAY over the window, a changed geometry HOLDS."""
    print("   settling window - %.0f s, do NOT touch anything now" % seconds)
    reference = before["phosphor"] / before["pump"]
    started, series, sample = time.time(), [], None
    while time.time() - started < seconds:
        current = capture(backend, roi, coefficients, max(2, frames // 3))
        if current is None:
            break
        sample = current
        elapsed = time.time() - started
        tilt = ((sample["phosphor"] / sample["pump"]) / reference - 1.0) * 100
        series.append((elapsed, tilt))
        print("      t=%5.1fs   ph/pump %7.4f   tilt %+6.2f%%"
              % (elapsed, sample["phosphor"] / sample["pump"], tilt))
    return series, sample


def settleReport(series, noiseFloor=0.26):
    """Did it calm down, and what is left? Compares the FIRST third of the window against the LAST third."""
    if len(series) < 6:
        return None
    third = max(2, len(series) // 3)
    early = np.array([t for _e, t in series[:third]])
    late = np.array([t for _e, t in series[-third:]])
    jump, residual = series[0][1], float(np.mean(late))
    recovered = ((abs(jump) - abs(residual)) / abs(jump) * 100) if abs(jump) > noiseFloor * 2 else float("nan")
    earlySpread, lateSpread = float(early.max() - early.min()), float(late.max() - late.min())
    print("      jump %+.2f%% -> settled %+.2f%%   |   movement: first third %.2f%%, last third %.2f%%"
          % (jump, residual, earlySpread, lateSpread))
    if abs(jump) <= noiseFloor * 2:
        print("      (the jump is at the noise floor - nothing was really disturbed)")
    else:
        print("      -> %.0f%% of the jump recovered; the trace is %s at the end"
              % (recovered, "STILL MOVING" if lateSpread > earlySpread * 0.5 else "STEADY"))
    return dict(jump=jump, residual=residual, recovered=recovered,
                earlySpread=earlySpread, lateSpread=lateSpread)


def main():
    parser = argparse.ArgumentParser(description="Cuvette re-seating repeatability (SPEC_capture_quality §16.7.1)")
    parser.add_argument("--changes", type=int, default=6, help="number of cuvette re-seats (default 6)")
    parser.add_argument("--frames", type=int, default=8, help="frames averaged per capture")
    parser.add_argument("--warmup", type=float, default=300.0,
                        help="seconds to let the sensor settle before starting (measured: ~1.6%% over 10 min)")
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None)
    parser.add_argument("--relax", type=float, default=60.0,
                        help="seconds to WATCH after each jar change (default 60). The window is analysed live, "
                             "and the SETTLED value is what counts as the 'after': liquid slosh and mechanical "
                             "settling decay over it, a changed geometry holds. 0 = one capture, no window.")
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
    settles = []
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
            series, after = watchSettle(backend, roi, coefficients, arguments.frames, arguments.relax, before)
            report = settleReport(series)
            if report is not None:
                settles.append(report)
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
        # The control can read ~0 by luck on a short run; dividing by it manufactures a huge, meaningless
        # factor. Floor the denominator at the measured noise level and refuse a verdict on a weak control.
        if len(notouch) < 2 or notouchTilt < 0.05:
            print("\n  control arm too small/quiet to compare against (n=%d, %.3f%%) — run more rounds."
                  % (len(notouch), notouchTilt))
            factor = None
        else:
            factor = reseatTilt / notouchTilt
            print("\n  re-seating moves the spectrum %.1fx as much as leaving it alone." % factor)
        if factor is None:
            pass
        elif reseatTilt < 0.5:
            print("  => nothing was meaningfully disturbed this run (re-seat arm is at the noise floor).")
        elif factor >= 3.0:
            print("  => CUVETTE SEATING IS AN ERROR SOURCE. No warm-up protocol fixes this; the R->S->R' bracket")
            print("     (SPEC §16.7) catches it, and so would clamping/keying the cuvette holder.")
        elif factor <= 1.5:
            print("  => seating looks INNOCENT — re-seating is no worse than doing nothing. The 5% A/B tilt")
            print("     must then come from something else (the liquid itself, or an event we have not sampled).")
        else:
            print("  => inconclusive at this sample size; run more rounds (--changes 12).")
    if settles:
        jumps = np.abs([r["jump"] for r in settles])
        residuals = np.abs([r["residual"] for r in settles])
        floor = float(np.abs([d["tilt"] for d in notouch]).mean()) if notouch else 0.26
        sensitivity = 0.434 / A_Q          # tilt % -> pigment-ratio % at Edwin's dilution
        print("\n=== DOES WAITING IT OUT FIX IT?  (%.0f s window after each change) ===" % arguments.relax)
        print("  right after the change : tilt mean %5.2f%%  max %5.2f%%   -> ratio %5.1f%% / %5.1f%%"
              % (jumps.mean(), jumps.max(), jumps.mean() * sensitivity, jumps.max() * sensitivity))
        print("  after the window       : tilt mean %5.2f%%  max %5.2f%%   -> ratio %5.1f%% / %5.1f%%"
              % (residuals.mean(), residuals.max(), residuals.mean() * sensitivity, residuals.max() * sensitivity))
        print("  untouched control      : tilt mean %5.2f%%" % floor)
        if jumps.mean() < max(floor * 2.0, 0.4):
            print("\n  => NO REAL DISTURBANCE was applied (the jumps are at the noise floor), so there is")
            print("     nothing to settle and nothing to conclude. This is the null case.")
        elif residuals.mean() <= max(floor * 2.0, 0.5):
            print("\n  => WAITING WORKS. What survives the pause is down at the untouched noise floor, so the")
            print("     disturbance is the LIQUID and the MECHANICS settling, not a changed geometry.")
            print("     Protocol fix: pause after every jar change - and the curves above say how long.")
        elif residuals.mean() >= jumps.mean() * 0.8:
            print("\n  => WAITING DOES NOT HELP. It is a PERMANENT STEP - the jar does not return to the same")
            print("     optical state. Fix the seating instead (fill to the brim, keyed holder), or never")
            print("     re-seat between reference and sample.")
        else:
            print("\n  => PARTLY. Some settles out, a residual step remains - both mechanisms are present.")
            print("     Waiting is worth doing, but it is not sufficient on its own.")
    print("\n  For scale: Edwin's A/B pair differed by 5.04% tilt, which swung the pigment ratio 20-28%.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
