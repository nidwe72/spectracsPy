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

# What the operator is asked to change each round. The analysis is identical — only the disturbance differs —
# so the same paired design (disturbed vs untouched control) measures whichever variable is being probed.
PROMPTS = {
    "jar": "TAKE THE CUVETTE OUT AND PUT IT BACK IN",
    "camera": "NUDGE THE CAMERA / UPPER CONE SLIGHTLY — about 1 mm, the SAME direction and amount each round",
    "holder": "NUDGE THE JAR HOLDER SLIGHTLY — about 1 mm, the SAME direction and amount each round",
    "stack": "NUDGE BOTH the camera/upper cone AND the jar holder — about 1 mm each, the SAME way each round",
    "none": "CHANGE NOTHING (null run — just wait a moment)",
}

# Run these with an EMPTY beam (no jar) to measure the mechanical stack on its own: whatever moves then owes
# nothing to the jar's optics. `holder` is the informative one — if moving an EMPTY holder shifts the spectrum,
# the holder itself is intercepting light (it is part of the aperture), which would make it a second thing to
# fix rigidly. If it does nothing, the holder only matters through the jar it carries.
EMPTY_BEAM_MODES = ("holder", "stack")

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
    """How much of the disturbance is a TRANSIENT that settles out, and how much is PERMANENT?

    The first reading is NOT the peak: the disturbance is still developing a second or two after the jar is put
    back, so measuring the jump from t=0 understates it (and can make "recovery" come out negative). Score the
    window against its own PEAK excursion instead, and against the settled value at the end."""
    if len(series) < 6:
        return None
    third = max(2, len(series) // 3)
    tilts = np.array([t for _e, t in series])
    late = tilts[-third:]
    early = tilts[:third]
    peak = float(np.max(np.abs(tilts)))
    settled = float(np.mean(late))
    permanent = abs(settled) / peak * 100 if peak > 0 else 0.0
    earlySpread, lateSpread = float(early.max() - early.min()), float(late.max() - late.min())
    print("      transient peak %.2f%%  ->  settled %+.2f%%   |   movement: first third %.2f%%, last third %.2f%%"
          % (peak, settled, earlySpread, lateSpread))
    if peak <= noiseFloor * 2:
        print("      (peak excursion is at the noise floor - nothing was really disturbed)")
    else:
        print("      -> %.0f%% of it is PERMANENT; the trace is %s at the end"
              % (permanent, "STILL MOVING" if lateSpread > earlySpread * 0.5 else "STEADY"))
    return dict(peak=peak, jump=series[0][1], residual=settled, permanent=permanent,
                earlySpread=earlySpread, lateSpread=lateSpread)


def main():
    parser = argparse.ArgumentParser(description="Cuvette re-seating repeatability (SPEC_capture_quality §16.7.1)")
    parser.add_argument("--changes", type=int, default=6, help="number of disturbances (default 6)")
    parser.add_argument("--disturb", choices=("jar", "camera", "holder", "stack", "none"), default="jar",
                        help="WHAT is disturbed each round. 'jar' = take the jar out and put it back "
                             "(§16.7.2). 'camera' = nudge the camera/upper cone instead, which probes the "
                             "alignment sensitivity the diffuser is supposed to remove (§16.9.3c). 'none' = a "
                             "null run: prompts but change nothing, to measure the floor.")
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

    if arguments.disturb == "jar":
        print("\nPut the SAME cuvette back each time — same liquid, same orientation if you can.")
        print("We are measuring the SEATING, not the contents.\n")
    elif arguments.disturb == "camera":
        print("\nNudge by a SIMILAR amount and in the SAME direction every round — comparisons between runs")
        print("only hold if the disturbance is comparable. Do NOT touch the jar at all: this run measures")
        print("ALIGNMENT sensitivity, not seating.\n")
    elif arguments.disturb in EMPTY_BEAM_MODES:
        print("\nRun this with the beam EMPTY — no jar at all. Then whatever moves is the MECHANICAL STACK")
        print("alone, with none of the jar's optics involved. Nudge a similar amount, the same way, each")
        print("round. Watch for the informative case: if moving an EMPTY holder shifts the spectrum, the")
        print("holder is intercepting light itself and needs fixing rigidly too (§16.9.3e).\n")
    else:
        print("\nNull run: change nothing at the prompts. Whatever this measures is the floor.\n")

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
            input("\n   >>> %s, then press Enter " % PROMPTS[arguments.disturb])
        except EOFError:
            print("   (non-interactive — continuing without a disturbance)")
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
        rounds.append((arguments.disturb, change))
        previousAfter = after            # the NEXT round's "before" closes the no-touch control interval
        print("   -> tilt %+.2f%%, level %+.2f%%, would move the pigment ratio %+.1f%%\n"
              % (change["tilt"], change["level"], change["ratio"]))

    backend.release()

    reseats = [d for kind, d in rounds if kind == arguments.disturb]
    notouch = [d for kind, d in rounds if kind == "no-touch"]
    if not reseats:
        return 0

    print("\n=== RESULT — disturbance: %s ===" % arguments.disturb.upper())
    print("%-12s %3s   %-22s %-22s %s" % ("", "n", "tilt (phosphor/pump)", "implied ratio swing", "level"))
    for label, group in ((arguments.disturb, reseats), ("no-touch", notouch)):
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
        if len(notouch) < 2:
            print("\n  only %d control interval(s) — run more rounds before comparing." % len(notouch))
            factor = None
        else:
            # A very QUIET control is a good result, not an unusable one; only floor the denominator so the
            # printed factor stays honest when the control is at the measurement floor.
            floored = max(notouchTilt, 0.02)
            factor = reseatTilt / floored
            print("\n  disturbing the %s moves the spectrum %s%.0fx as much as leaving it alone (control %.3f%%)."
                  % (arguments.disturb, ">=" if notouchTilt < 0.02 else "", factor, notouchTilt))
        if factor is None:
            pass
        elif reseatTilt < 0.5:
            print("  => nothing was meaningfully disturbed this run (re-seat arm is at the noise floor).")
        elif factor >= 3.0 and arguments.disturb == "camera":
            print("  => ALIGNMENT IS AN ERROR SOURCE. Run this again with the diffuser fitted: if the factor")
            print("     drops, that is what the diffuser buys, measured on the variable it targets (§16.9.3c).")
        elif factor >= 3.0:
            print("  => CUVETTE SEATING IS AN ERROR SOURCE. No warm-up protocol fixes this; the R->S->R' bracket")
            print("     (SPEC §16.7) catches it, and so would clamping/keying the cuvette holder.")
        elif factor <= 1.5:
            print("  => seating looks INNOCENT — re-seating is no worse than doing nothing. The 5% A/B tilt")
            print("     must then come from something else (the liquid itself, or an event we have not sampled).")
        else:
            print("  => inconclusive at this sample size; run more rounds (--changes 12).")
    if settles:
        jumps = np.array([r["peak"] for r in settles])          # peak excursion, not the first reading
        residuals = np.abs([r["residual"] for r in settles])
        permanents = np.array([r["permanent"] for r in settles])
        floor = float(np.abs([d["tilt"] for d in notouch]).mean()) if notouch else 0.26
        sensitivity = 0.434 / A_Q          # tilt % -> pigment-ratio % at Edwin's dilution
        print("\n=== DOES WAITING IT OUT FIX IT?  (%.0f s window after each change) ===" % arguments.relax)
        print("  peak during the window : tilt mean %5.2f%%  max %5.2f%%   -> ratio %5.1f%% / %5.1f%%"
              % (jumps.mean(), jumps.max(), jumps.mean() * sensitivity, jumps.max() * sensitivity))
        print("  after the window       : tilt mean %5.2f%%  max %5.2f%%   -> ratio %5.1f%% / %5.1f%%"
              % (residuals.mean(), residuals.max(), residuals.mean() * sensitivity, residuals.max() * sensitivity))
        print("  untouched control      : tilt mean %5.2f%%" % floor)
        print("  => %.0f%% of the disturbance is PERMANENT on average (%.0f%% settles out)"
              % (permanents.mean(), 100 - permanents.mean()))
        if jumps.mean() < max(floor * 2.0, 0.4):
            print("\n  => NO REAL DISTURBANCE was applied (the jumps are at the noise floor), so there is")
            print("     nothing to settle and nothing to conclude. This is the null case.")
        elif permanents.mean() <= 30.0:
            print("\n  => WAITING WORKS. Most of the excursion settles out, so the disturbance is transient")
            print("     (liquid slosh, mechanical relaxation) rather than a changed geometry. Protocol fix:")
            print("     pause after every change - and the curves above say how long.")
        elif residuals.mean() <= max(floor * 2.0, 0.5):
            print("\n  => MOSTLY PERMANENT, but SMALL. %.0f%% of each excursion survives the pause, yet what")
            print("     survives is close to the untouched floor (%.2f%% vs %.2f%%). The disturbance changes"
                  % (permanents.mean(), residuals.mean(), floor))
            print("     the geometry for good, but by little - this variable is not a major error source.")
        elif residuals.mean() >= jumps.mean() * 0.8:
            print("\n  => WAITING DOES NOT HELP. It is a PERMANENT STEP - the jar does not return to the same")
            print("     optical state. Fix the seating instead (fill to the brim, keyed holder), or never")
            print("     re-seat between reference and sample.")
        else:
            print("\n  => PARTLY. Some settles out, a residual step remains - both mechanisms are present.")
            print("     Waiting is worth doing, but it is not sufficient on its own.")
    levels = np.abs([d["level"] for d in reseats])
    print("\n  TILT vs LEVEL — they cost different things:")
    print("    tilt  mean %5.2f%%  max %5.2f%%   spectral shape -> corrupts the pigment RATIO" % (
        np.abs([d["tilt"] for d in reseats]).mean(), np.abs([d["tilt"] for d in reseats]).max()))
    print("    level mean %5.2f%%  max %5.2f%%   throughput/path -> scales ABSOLUTE absorbance; a pure path"
          % (levels.mean(), levels.max()))
    print("                                      change CANCELS in the ratio (both bands scale together)")
    print("\n  For scale: Edwin's A/B pair differed by 5.04% tilt, which swung the pigment ratio 20-28%.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
