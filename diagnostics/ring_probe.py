"""How much of the light reaching the slit came through the jar WALL instead of the liquid?
(SPEC_capture_quality.md §16.9.3b — the measurement that decides whether the aperture mask is worth building.)

THE DESIGN — a 2x2, because there are TWO rings and only one of them matters for reproducibility:

                       no aperture      with aperture
     no jar                 A                 B        -> B/A = plain geometric vignetting
     jar + blank            C                 D        -> D/C = vignetting + ring blocking

                 f_ring = 1 - (D/C)/(B/A)

The LAMP throws a ring too (light diffusing through the outline of its own disk), and it is present in both
columns — so it cancels in the ratio-of-ratios and `f_ring` isolates the JAR-WALL ring, which is the one that
moves every time the jar is re-seated. A constant lamp ring costs accuracy; a moving jar ring costs
reproducibility, and that is what we are chasing.

TWO RULES THE MEASUREMENT DEPENDS ON:
  * ONE pinned exposure for all four cells, chosen on the brightest (cell A). Auto-exposing per cell would
    divide out the very quantity being measured.
  * Nothing else may change between cells: same lamp, same distances, same diffuser state.

Run it TWICE — once without the diffuser, once with it where you have it now — using --label to tag each block.
The exposure is pinned per block, and because f_ring is a ratio-of-ratios WITHIN a block the two remain
comparable. That comparison is a falsifiable test of §16.7.2n: if a diffuser in the jar's plane smears the rings
across the whole field, the aperture can no longer block them selectively and f_ring should come out SMALLER
with the diffuser fitted even though the contamination is unchanged.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \\
        ./venv/bin/python diagnostics/ring_probe.py --label no-diffuser \\
            --roi 564,907,2145,1782 \\
            --coeffs=-5.77381138877048e-09,2.35944918200958e-05,0.116112996214963,331.935289341983
"""
import argparse
import json
import os
import sys
import time

import numpy as np

from reference_drift_probe import PHOSPHOR, PUMP, _appContext, _bandMean, _pickExposure, _spectrum

# The four cells, in the order that costs the FEWEST handling steps: add the aperture, then add the jar,
# then take the aperture away. Three changes instead of four, and the jar is inserted only once.
CELLS = [("A", "NO jar, NO aperture", "take the jar OUT and the aperture OFF"),
         ("B", "NO jar, WITH aperture", "put the APERTURE on (jar still out)"),
         ("D", "jar + blank, WITH aperture", "put the JAR in (aperture stays on)"),
         ("C", "jar + blank, NO aperture", "take the APERTURE off (jar stays in)")]

BANDS = [("blue 440-490", 440.0, 490.0), ("green 500-560", 500.0, 560.0), ("red 570-630", 570.0, 630.0)]
SATURATION_DN = 250.0


def capture(backend, roi, coefficients, frames):
    stack, nanometers = [], None
    for index in range(frames):
        if index:
            time.sleep(0.7)          # ~1.5 fps at 2592x1944 — otherwise the same buffered frame is re-read
        image = backend.read()
        if image is None:
            continue
        nanometers, values = _spectrum(image, roi, coefficients)
        stack.append(values)
    if not stack:
        return None
    values = np.median(np.array(stack), axis=0)
    return {"nm": nanometers, "values": values, "level": float(values.mean()), "peak": float(values.max()),
            "pump": _bandMean(nanometers, values, *PUMP), "phosphor": _bandMean(nanometers, values, *PHOSPHOR),
            "bands": {label: _bandMean(nanometers, values, low, high) for label, low, high in BANDS}}


def selftest():
    """Fabricate four cells with a KNOWN wall-ring fraction and check the estimator recovers it.

    Model: the slit collects liquid light L, a constant lamp ring P (present with or without the jar), and a
    wall ring W (only when the jar is in). The aperture passes a fraction `pass_` of each ring and all of the
    liquid light. The jar also attenuates everything it transmits by `jarLoss` — which must NOT leak into
    f_ring, and that is the point of the ratio-of-ratios."""
    liquid, lampRing, wallRing, apertureKeeps, jarLoss = 100.0, 12.0, 8.0, 0.25, 0.82
    cells = {
        "A": liquid + lampRing,
        "B": liquid + lampRing * apertureKeeps,
        "C": jarLoss * (liquid + lampRing) + wallRing,
        "D": jarLoss * (liquid + lampRing * apertureKeeps) + wallRing * apertureKeeps,
    }
    estimate = 1.0 - (cells["D"] / cells["C"]) / (cells["B"] / cells["A"])
    truth = (wallRing * (1 - apertureKeeps)) / cells["C"]      # the share of C that the aperture removes
    print("SELFTEST — synthetic cells, liquid %.0f, lamp ring %.0f, WALL ring %.0f, aperture keeps %.0f%%,"
          % (liquid, lampRing, wallRing, apertureKeeps * 100))
    print("           jar transmits %.0f%% (a confounder the estimator must ignore)\n" % (jarLoss * 100))
    for key in "ABCD":
        print("   cell %s level %8.3f" % (key, cells[key]))
    print("\n   f_ring estimated %.4f   true wall-ring share removed %.4f   error %.4f"
          % (estimate, truth, abs(estimate - truth)))
    ok = abs(estimate - truth) < 0.02
    print("   %s" % ("PASS — the jar's overall loss and the constant lamp ring both cancel" if ok
                     else "FAIL — the estimator is picking up a confounder"))
    zero = {"A": liquid + lampRing, "B": liquid + lampRing * apertureKeeps,
            "C": jarLoss * (liquid + lampRing), "D": jarLoss * (liquid + lampRing * apertureKeeps)}
    none = 1.0 - (zero["D"] / zero["C"]) / (zero["B"] / zero["A"])
    print("   control: with NO wall ring at all, f_ring = %+.4f (must be ~0)  %s"
          % (none, "PASS" if abs(none) < 1e-9 else "FAIL"))
    return 0 if ok and abs(none) < 1e-9 else 1


def main():
    parser = argparse.ArgumentParser(description="Jar-wall ring fraction (SPEC_capture_quality §16.9.3b)")
    parser.add_argument("--label", default="block", help="tag for this block, e.g. no-diffuser / diffuser-on-jar")
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None, help="pin it yourself; default picks on cell A")
    parser.add_argument("--roi", default=None, help="X1,Y1,X2,Y2")
    parser.add_argument("--coeffs", default=None, help="A,B,C,D px->nm cubic")
    parser.add_argument("--out", default=None, help="where to write the JSON (default: alongside the probe)")
    parser.add_argument("--selftest", action="store_true",
                        help="verify the arithmetic on synthetic cells with a KNOWN ring fraction (no camera)")
    arguments = parser.parse_args()

    if arguments.selftest:
        return selftest()

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
    backend.open(deviceId=device, exposure=arguments.exposure or 150, whiteBalanceKelvin=6500)

    print("\n=== RING PROBE — block '%s' ===" % arguments.label)
    print("Four cells, ONE exposure. Change ONLY what each prompt asks for; leave the lamp, the")
    print("distances and the diffuser state alone for the whole block.\n")
    try:
        input(">>> Set up cell A first (jar OUT, aperture OFF), then press Enter to pin the exposure ")
    except EOFError:
        print("(non-interactive)")

    exposure = arguments.exposure
    if exposure is None:
        # Pin on the BRIGHTEST cell so nothing clips later; every other cell can only be dimmer.
        exposure = _pickExposure(backend)
    else:
        backend.setExposure(exposure)
    print("exposure PINNED at %s for all four cells (auto-exposure per cell would divide out the answer)\n"
          % exposure)

    results = {}
    for key, description, instruction in CELLS:
        if key != "A":
            try:
                input(">>> %-28s  — %s, then press Enter " % ("cell %s: %s" % (key, description), instruction))
            except EOFError:
                print("(non-interactive: skipping the change)")
        sample = capture(backend, roi, coefficients, arguments.frames)
        if sample is None:
            print("   no frames — aborting")
            backend.release()
            return 1
        results[key] = sample
        flag = "  ⚠ CLIPPING — lower the exposure and restart" if sample["peak"] >= SATURATION_DN else ""
        print("   %-28s level %8.2f   peak %6.1f   ph/pump %6.4f%s"
              % ("cell %s (%s)" % (key, description), sample["level"], sample["peak"],
                 sample["phosphor"] / sample["pump"], flag))
    backend.release()

    a, b, c, d = (results[k]["level"] for k in "ABCD")
    vignetting = b / a                       # what the aperture costs with NO jar = pure geometry (+ lamp ring)
    withJar = d / c                          # the same, plus the jar-wall ring being blocked
    ringFraction = 1.0 - withJar / vignetting

    print("\n=== RESULT — block '%s' ===" % arguments.label)
    print("   B/A  aperture with NO jar   %.4f   (geometric vignetting, incl. the constant lamp ring)" % vignetting)
    print("   D/C  aperture WITH the jar  %.4f   (the same, plus jar-wall ring blocked)" % withJar)
    print("   ------------------------------------------------------------------")
    print("   f_ring = 1 - (D/C)/(B/A) = %+.3f  ->  %.1f%% of what the slit collects came through the WALL"
          % (ringFraction, ringFraction * 100))
    if ringFraction >= 0.03:
        print("   => WORTH BUILDING. This is also the share that moves when the jar is re-seated,")
        print("      so it predicts how much of the re-seat error the aperture can remove.")
    elif ringFraction >= 0.0:
        print("   => small. The aperture would buy little; spend the effort on the diffuser mount instead.")
    else:
        print("   => NEGATIVE, which is not physical: something else changed between cells (lamp, distance,")
        print("      exposure, jar fill). Re-run the block without touching anything but the prompts.")

    print("\n   per band — a wall ring should be roughly NEUTRAL (acrylic is not very coloured):")
    for label, _low, _high in BANDS:
        va, vb = results["A"]["bands"][label], results["B"]["bands"][label]
        vc, vd = results["C"]["bands"][label], results["D"]["bands"][label]
        print("      %-16s f_ring %+6.3f" % (label, 1.0 - (vd / vc) / (vb / va)))

    payload = {"label": arguments.label, "exposure": exposure, "fRing": ringFraction,
               "vignetting": vignetting, "withJar": withJar,
               "cells": {k: {"level": v["level"], "peak": v["peak"], "bands": v["bands"],
                             "phosphorOverPump": v["phosphor"] / v["pump"]} for k, v in results.items()}}
    out = arguments.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "ring_probe_%s.json" % arguments.label)
    with open(out, "w") as handle:
        json.dump(payload, handle, indent=2)
    print("\n   written to %s" % out)

    # If the other block has already been run, compare them — that is the §16.7.2n test.
    sibling = [f for f in os.listdir(os.path.dirname(out))
               if f.startswith("ring_probe_") and f.endswith(".json") and f != os.path.basename(out)]
    for name in sibling:
        with open(os.path.join(os.path.dirname(out), name)) as handle:
            other = json.load(handle)
        print("\n   vs block '%s': f_ring %.3f  ->  %.3f" % (other["label"], other["fRing"], ringFraction))
        print("   (§16.7.2n predicts a SMALLER f_ring when a diffuser sits in the JAR's plane — it smears the")
        print("    rings across the field so the aperture can no longer block them selectively. Equal values")
        print("    would refute that, leaving only the mechanical reason to move the diffuser to the slit.)")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
