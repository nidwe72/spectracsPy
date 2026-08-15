"""⭐ WHEN IS A JAR READY TO MEASURE? — Q% and the guard DN, every 3 minutes, for 90.

    (Edwin 2026-08-14, after the Lugitsch evening. `SPEC_capture_quality.md` §16.33,
     `SPEC_v_metric_integration.md` §3, `SPEC_metric_research.md` §10.)

THE QUESTION THIS ANSWERS. A muddy fill clears while it sits in the beam, and every metric moves with
it. Edwin's ten hand-run repeats showed the movement is real but slow, and — crucially — that it is
almost entirely a nuisance the metric divides out. What nobody can currently answer is the practical
one: HOW LONG DO I WAIT? This run measures the clearing curve directly and says when it has flattened.

WHAT IT DOES
    1  prompts for the REFERENCE jar, captures it once
    2  prompts for the SAMPLE jar
    3  then, untouched, every 3 minutes for 90: Q%, the three band means, and the guard DN
    4  optionally re-prompts for the REFERENCE at the very end, which BOUNDS how much of the whole
       curve was the reference drifting rather than the sample clearing (§16.7)

⛔ NOTHING IS RE-SEATED DURING THE RUN, AND THAT IS THE POINT. Edwin's series put the no-re-seat floor
of `Q%` at sd 0.063 against 0.70 with re-seating — 11x. So a curve measured without touching the jar
sees the CLEARING and essentially nothing else; the moment you re-seat, the clearing is buried under a
noise term eleven times larger. ⇒ do not open the lid, do not nudge the cone, do not adjust anything.

⭐ WHY BOTH Q% AND DN, AND WHY THEY DISAGREE. `DN` is the darkest bin inside 448-460 nm, gamma-encoded
— exactly what the app's CAPTURE-LOWDN line prints, reproduced here bin for bin. It measures how much
light gets through, so it tracks turbidity DIRECTLY. `Q%` is a ratio of a band DIFFERENCE to a band
LEVEL, so it is invariant to the multiplicative part of turbidity and only weakly sensitive to the
additive part. On the Lugitsch evening DN climbed 38 -> 56 (+47 %) while Q% moved 1.5 units, most of it
early. ⇒ DN is the SETTLING SENSOR; Q% is the ANSWER. Watching only Q% would hide how far from
equilibrium the jar still is; watching only DN would suggest a problem the verdict does not have.

⭐ THE READINESS RULE, AND IT IS NOT ARBITRARY. A fill is called SETTLED when the drift in `Q%` over
the last 15 minutes falls below **0.21 units — the measured refill floor** (§10.5). Below that the
clearing contributes less than the preparation variance you will have anyway, so waiting longer buys
nothing you can use. The DN slope is printed beside it as the physical corroboration, never as the
criterion: DN keeps creeping long after the verdict has stopped moving, and stopping on DN alone would
mean waiting for something that does not matter.

⚠ EXPOSURE IS PINNED FOR THE WHOLE RUN. Auto-exposure would silently compensate the very clearing this
is trying to measure — the drift must appear in the SPECTRUM, never in the camera (§16.7).

⚠ READ-ONLY. Nothing is written to the app DB and no report PDF is produced; the CSV is the artefact.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/clearing_time_course.py --label Lugitsch_B
        ... --minutes 90 --every 3 --frames 60     # the defaults
        ... --reference-at-end                     # re-prompt for the blank when the run finishes
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

from reference_drift_probe import _appContext, _pickExposure, _spectrum

# ⭐ READ FROM THE PLUGIN, NEVER COPIED. This script must print what the BENCH would print, so every
# window and every guard edge comes from the shipped constants. A transcribed copy is how a diagnostic
# silently stops agreeing with the app it exists to measure — §10.1a cost this project exactly that
# once already, and the 20-40 target pair had already moved to 20-50 (§16.23.10d) while this file was
# being written. ⚠ `diagnostics/box_metrics.py` deliberately does the opposite and freezes its own copy:
# it is the PRE-REGISTRATION record, and it must not follow the code.
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin as _Plugin

SORET = _Plugin.V_SORET_BAND
VALLEY = _Plugin.V_VALLEY_BAND
Q_BAND = _Plugin.V_Q_BAND
GUARD_BAND = _Plugin.DN_GUARD_BAND
GUARD_TARGET = (_Plugin.DN_TARGET_LOW, _Plugin.DN_TARGET_HIGH)
SORET_FLOOR = _Plugin.V_SORET_FLOOR         # §3.1 — below this there is no verdict at all
VERDICT_BAND = _Plugin.V_VERDICT_BAND       # §3.1a — outside this the value stands but no verdict is drawn
REFILL_FLOOR = 0.21             # §10.5 — the readiness threshold, in Q% units per 15 minutes
SETTLED_WINDOW_MIN = 15.0


def calibrationFromServerDb(path=None):
    """ROI + px->nm cubic straight out of the SERVER's own database.

    ⚠⚠ THE DATABASE IS CWD-DEPENDENT AND THERE ARE TWO OF THEM. `runServer.sh` runs from
    `spectracsPy-server/`, so the live server writes `~/.spectracsPy-server/spectracsPyServer.db`; a
    script started from the app directory sees `~/.spectracsPy/spectracsPyServer.db` instead — and on
    this machine THAT one's calibration rows are entirely NULL. Reading the wrong file therefore looks
    exactly like "no calibration exists", which is the wrong conclusion and cost a round to find.
    ⇒ the running server's file is tried FIRST, and the one that actually has values wins.

    `_appContext()` is still preferred when a session is populated; this is the fallback that makes the
    probe runnable from a plain shell with the app closed."""
    import sqlite3
    candidates = ([path] if path else
                  [os.path.expanduser("~/.spectracsPy-server/spectracsPyServer.db"),
                   os.path.expanduser("~/.spectracsPy/spectracsPyServer.db")])
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            connection = sqlite3.connect("file:%s?mode=ro" % candidate, uri=True)
            rows = connection.execute(
                "select id, regionOfInterestX1, regionOfInterestY1, regionOfInterestX2,"
                " regionOfInterestY2, interpolationCoefficientA, interpolationCoefficientB,"
                " interpolationCoefficientC, interpolationCoefficientD"
                " from spectrometer_calibration_profile"
                " where regionOfInterestX1 is not null and interpolationCoefficientA is not null").fetchall()
            connection.close()
        except Exception:
            continue
        if not rows:
            continue
        # ⛔ NEVER PICK ONE OF SEVERAL SILENTLY. Today exactly one of the two profiles carries values, so
        # the choice is forced and correct. The moment a second one is calibrated, `limit 1` would start
        # choosing by rowid — an arbitrary answer wearing the look of a resolved one — and every band
        # would land on the wrong wavelengths without a single error. ⚠ The schema has no user -> profile
        # link to disambiguate with (there is no serial on the sensor), so the honest move is to stop.
        if len(rows) > 1:
            print("   ⛔ %d calibration profiles carry values in %s:" % (len(rows), candidate))
            for row in rows:
                print("        %s  roi %s..%s  D %.4f" % (row[0], row[1], row[3], row[8]))
            print("      Cannot tell which one this rig is using. Pass --roi/--coeffs explicitly.")
            return {}
        row = rows[0]
        print("   calibration read from %s\n     profile %s  roi %d,%d,%d,%d"
              % (candidate, row[0], row[1], row[2], row[3], row[4]))
        return {"roi": [int(v) for v in row[1:5]], "coeffs": [float(v) for v in row[5:]]}
    return {}


def spectrumOf(values, nanometers):
    """{nm: linear value} -> the app's Spectrum, clamped to the plugin's capture range."""
    from sciens.spectracs.model.spectral.Spectrum import Spectrum
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({float(nm): float(v) for nm, v in zip(nanometers, values)
                                    if 400.0 <= float(nm) <= 636.0})
    return spectrum


def captureMean(backend, roi, coefficients, frames):
    """`frames` frames averaged in LINEAR space — the same reduction MeanOp performs in the app."""
    stack, nanometers = [], None
    for _ in range(frames):
        image = backend.read()
        if image is None:
            continue
        nanometers, columns = _spectrum(image, roi, coefficients)
        stack.append(columns)
    if not stack:
        return None, None
    return np.mean(np.array(stack), axis=0), nanometers


def guardDn(values, nanometers):
    """The app's CAPTURE-LOWDN number, reproduced: darkest bin in the guard window, gamma-ENCODED.

    ⚠ The spectrum is LINEAR here and the guard's thresholds live in ENCODED (camera) DN — §16.23.10b.
    Encoding once, here, is what stops a caller comparing across the two spaces."""
    from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
    inside = [v for nm, v in zip(nanometers, values) if GUARD_BAND[0] <= nm <= GUARD_BAND[1]]
    if not inside:
        return None
    return SpectralColorUtil().encodeGammaFraction(max(0.0, float(min(inside))) / 255.0)


def guardVerdict(digitalNumber):
    if digitalNumber is None:
        return "?"
    if digitalNumber < GUARD_TARGET[0]:
        return "too-concentrated"
    if digitalNumber > GUARD_TARGET[1]:
        return "too-dilute"
    return "in-window"


def metricsOf(referenceValues, sampleValues, nanometers):
    """(Q%, A_Soret, A_valley, A_Q) through the app's OWN op chain, so the numbers match the bench.

    ⭐ Absorption via AbsorptionOp and the de-spike via the plugin's own private helper — not a
    re-implementation. A re-implementation is exactly how a diagnostic drifts away from the app it is
    supposed to be measuring, which §10.1a already cost this project once."""
    from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
    from sciens.spectracs.plugin_sdk.ops.AbsorptionOp import AbsorptionOp
    from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE

    container = SpectraContainer()
    container.addToSpectra(spectrumOf(referenceValues, nanometers), REFERENCE)
    container.addToSpectra(spectrumOf(sampleValues, nanometers), SAMPLE)
    absorption = AbsorptionOp().apply(container).getSpectra()["ABSORPTION"]

    # ⭐ The plugin's OWN de-spike and its OWN band means — `__vTerms` is the very method the gauge reads,
    # so this row cannot disagree with the bench even in principle.
    plugin = _Plugin()
    despiked = plugin._DevSpectralPlugin__despikedAbsorption(absorption)
    terms = plugin._DevSpectralPlugin__vTerms(despiked)
    if terms is None:
        return None, None, None, None            # §3.1: the Soret floor — no numbers at all
    soret, valley, qBand, qPercent = terms
    return qPercent, soret, valley, qBand


def bandRatio(sample):
    """W = (A_Q − A_valley)/(A_Soret − A_valley) — the Gouterman Q:Soret ratio, valley as the zero.

    ⭐ WHY THIS EARNS A COLUMN. W is EXACTLY invariant to the whole `a -> k*a + b` nuisance group:
    numerator and denominator are both differences, so a multiplicative k cancels and an additive b
    cancels. Turbidity, seating, exposure and dilution cannot move it. ⇒ a monotone drift in W is not
    an artefact — it is the pigment's own band ratio changing, i.e. CHEMISTRY.
    ⚠ The invariance assumes k and b are flat in wavelength; a fit over 448-629 left 7 % unexplained,
    so a small part of any W move can still be the tail of the clearing."""
    denominator = sample["soret"] - sample["valley"]
    if denominator <= 0:
        return None
    return (sample["qBand"] - sample["valley"]) / denominator


def clearingDone(samples, threshold=0.005, consecutive=2):
    """Has the turbidity stopped falling? -> the moment to READ, and the gate that beats waiting.

    ⭐ TRIGGER ON THE CAUSE, NOT THE SYMPTOM. `Q%` turns because clearing (which biases it up and
    decays) hands over to photodamage (which biases it up and grows) — so its minimum is the moment
    both contaminations are smallest. But detecting that turn in `Q%` means resolving a sign change on
    a quantity with sd 0.063, which needs several rising samples to confirm and costs ~10 further
    minutes of light. A_valley meanwhile falls 97 % (0.95 -> 0.026) and then flattens: an enormous
    signal. Gating on it lands on the same sample with no waiting and no extra dose."""
    if len(samples) < consecutive + 1:
        return None
    for index in range(consecutive, len(samples)):
        steps = [abs(samples[k]["valley"] - samples[k - 1]["valley"])
                 for k in range(index - consecutive + 1, index + 1)]
        if all(step < threshold for step in steps):
            return index
    return None


def vertexRead(samples, index):
    """The Q% minimum read as a PARABOLA VERTEX through its three neighbours, not as the raw minimum.

    ⚠ The minimum of n noisy samples is biased LOW by ~0.9 sd (~0.06 here) because it selects the most
    negative excursion. A vertex through three points averages instead of selecting."""
    window = [s for s in samples[max(0, index - 1):index + 2] if s["qPercent"] is not None]
    if len(window) < 3:
        return samples[index]["qPercent"], samples[index]["minutes"]
    t = np.array([s["minutes"] for s in window]); q = np.array([s["qPercent"] for s in window])
    a, b, c = np.polyfit(t, q, 2)
    if a <= 0:
        return samples[index]["qPercent"], samples[index]["minutes"]
    at = -b / (2 * a)
    return float(a * at * at + b * at + c), float(at)


def zeroDoseEstimate(samples, index):
    """Extrapolate the post-clearing damage line back to insertion -> the UNDAMAGED value.

    ⛔ Even the Q% minimum is already damaged: on 2026-08-14 jar B accumulated ~17 min of light before
    it finished clearing, worth 0.36 units = 1.7 refill floors. This estimates that back out.
    ⚠ MODEL RISK, and it is why this is reported SEPARATELY and never folded into the answer: it
    assumes the damage rate during clearing matched the rate after, while the sample was turbid and the
    light distribution inside it was quite different. The measured post-clearing rate itself wandered
    (+1.14 -> +1.61 -> +0.96 per hour)."""
    tail = [s for s in samples[index:] if s["qPercent"] is not None]
    if len(tail) < 4:
        return None, None
    t = np.array([s["minutes"] for s in tail]); q = np.array([s["qPercent"] for s in tail])
    slope, intercept = np.polyfit(t, q, 1)
    return float(intercept), float(slope) * 60.0


def referenceDrift(startValues, endValues, nanometers):
    """The blank measured against ITSELF, 90 minutes apart -> (D_Soret, D_valley, D_Q) in absorbance.

    ⛔ WHAT THIS REPLACED, AND WHY IT WAS WRONG. The first version ran the METRIC on the two references
    and printed `Q%`, with a comment claiming 0 would be a stable blank. That is nonsense: a stable
    blank gives A = 0 in EVERY band, so `Q% = (0-0)/0` is 0/0 — the ratio of two near-zero numbers, i.e.
    noise, printed as though it were a drift measurement. On 2026-08-14 it printed 14.987 and meant
    nothing except that the §3.1 floor had not withheld it.

    ⭐ WHAT MATTERS INSTEAD. With `A_meas = -log10(S_t / R_0)` while the truth is `-log10(S_t / R_t)`,

        A_meas - A_true  =  -log10(R_t / R_0)  ==  D(λ)

    so D is EXACTLY the additive error carried by every absorbance in the run, per band, and it is
    computed through the same AbsorptionOp + de-spike path as the data it corrects.
    ⚠ It bundles a re-seat of the reference jar in with any lamp drift, so read it as an UPPER bound on
    the lamp. ⚠ And it assumes the drift ran monotonically to the value measured at the end."""
    from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
    from sciens.spectracs.plugin_sdk.ops.AbsorptionOp import AbsorptionOp
    from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
    container = SpectraContainer()
    container.addToSpectra(spectrumOf(startValues, nanometers), REFERENCE)
    container.addToSpectra(spectrumOf(endValues, nanometers), SAMPLE)
    drift = AbsorptionOp().apply(container).getSpectra()["ABSORPTION"]
    plugin = _Plugin()
    despiked = plugin._DevSpectralPlugin__despikedAbsorption(drift)
    from sciens.spectracs.plugin_sdk import SpectrumFeatureUtil
    util = SpectrumFeatureUtil()
    return (util.bandMean(despiked, *SORET), util.bandMean(despiked, *VALLEY),
            util.bandMean(despiked, *Q_BAND))


def loadBaseline(path):
    """A previous run's CSV -> [(A_valley, W, Q%, A_Soret)], for the matched-clearing comparison.

    ⭐ THE RE-RUN'S WHOLE POINT. Cooling a jar and measuring it again asks whether the change the lamp
    made SURVIVED — and that must be read at a MATCHED CLEARING STATE, never at a matched time, because
    the second run clears on its own schedule. W is the quantity to compare (see `bandRatio`)."""
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                soret, valley, qBand = float(row["aSoret"]), float(row["aValley"]), float(row["aQ"])
                if soret - valley > 0:
                    out.append((valley, (qBand - valley) / (soret - valley), float(row["qPercent"]), soret))
            except (KeyError, ValueError):
                continue
    # ⛔⛔ TRUNCATE TO THE CLEARING BRANCH, or the match is meaningless. After clearing, A_valley sits in
    # a narrow noisy band (0.023-0.032 for 70 minutes on 2026-08-14) while W climbs 11 % — so ONE
    # A_valley maps to MANY W, and nearest-neighbour matching lands wherever the noise puts it. Probing
    # 0.0250 / 0.0257 / 0.0260 against that full curve returned W = 0.1500 / 0.1366 / 0.1480: three
    # answers a thousandth apart, one of them the fully-damaged end state.
    # ⇒ a re-run that had RETAINED all its damage would have been reported as ~0 % changed.
    # On the clearing branch A_valley falls monotonically (0.95 -> 0.026), so the match is unique AND it
    # compares like with like: just-cleared against just-cleared, each minimally damaged.
    branch = [out[0]] if out else []
    for index in range(1, len(out)):
        if out[index][0] >= out[index - 1][0]:
            break
        branch.append(out[index])
    return branch


def baselineAt(baseline, valley):
    """The baseline point with the closest A_valley — matched clearing state, not matched time."""
    if not baseline:
        return None
    return min(baseline, key=lambda entry: abs(entry[0] - valley))


def settledYet(samples):
    """(isSettled, driftQ, driftDn) over the trailing SETTLED_WINDOW_MIN — the readiness rule.

    ⭐ The criterion is Q%, not DN: below the refill floor the clearing contributes less than the
    preparation variance the next jar will have anyway, so more waiting buys nothing usable."""
    if len(samples) < 2:
        return False, None, None
    cutoff = samples[-1]["minutes"] - SETTLED_WINDOW_MIN
    window = [s for s in samples if s["minutes"] >= cutoff]
    if len(window) < 2 or (window[-1]["minutes"] - window[0]["minutes"]) < SETTLED_WINDOW_MIN * 0.8:
        return False, None, None
    driftQ = window[-1]["qPercent"] - window[0]["qPercent"]
    driftDn = (window[-1]["dn"] - window[0]["dn"]) if None not in (window[-1]["dn"], window[0]["dn"]) else None
    return abs(driftQ) < REFILL_FLOOR, driftQ, driftDn


def promptFor(what):
    input("\n   >>> put the %s in the device, close everything, then press Enter " % what)


def main():
    parser = argparse.ArgumentParser(description="Clearing time-course: Q% + guard DN every N minutes")
    parser.add_argument("--minutes", type=float, default=90.0, help="total duration (default 90)")
    parser.add_argument("--every", type=float, default=3.0, help="minutes between samples (default 3)")
    parser.add_argument("--frames", type=int, default=60, help="frames averaged per sample (app default 60)")
    parser.add_argument("--label", default="clearing", help="folder name for the CSV")
    parser.add_argument("--out", default=None, help="CSV path (default: spectracs-references/tmp/<label>/)")
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--exposure", type=int, default=None, help="pin it; default = one sweep, then pinned")
    parser.add_argument("--roi", default=None, help="X1,Y1,X2,Y2 (default: the app's own context)")
    parser.add_argument("--coeffs", default=None, help="A,B,C,D px->nm cubic (default: the app's own context)")
    parser.add_argument("--reference-at-end", action="store_true",
                        help="re-prompt for the reference when the run ends, to bound its own drift")
    parser.add_argument("--compare", default=None,
                        help="a previous run's CSV to compare against at MATCHED CLEARING STATE "
                             "(default: the same label's own earlier CSV, if one exists)")
    parser.add_argument("--calibration-db", default=None,
                        help="explicit spectracsPyServer.db (default: the running server's, then the app's)")
    parser.add_argument("--check", action="store_true",
                        help="ONE reference + ONE sample capture, print the sanity numbers, exit. "
                             "Use this to verify --roi/--coeffs before committing 90 minutes.")
    arguments = parser.parse_args()

    context = _appContext()
    if context.get("roi") is None or context.get("coeffs") is None:
        # No populated session (the usual case for a standalone run) -> read the server's DB directly.
        context = {**calibrationFromServerDb(arguments.calibration_db), **{k: v for k, v in context.items()
                                                                          if v is not None}}
    device = arguments.device if arguments.device is not None else context.get("device", 0)
    roi = [int(v) for v in arguments.roi.split(",")] if arguments.roi else context.get("roi")
    coefficients = ([float(v) for v in arguments.coeffs.split(",")] if arguments.coeffs
                    else context.get("coeffs"))
    if roi is None or coefficients is None:
        # ⚠ MEASURED 2026-08-14: `_try_app_context()` reads the SELECTED spectrometer profile, and on this
        # machine both `spectrometer_calibration_profile` rows in ~/.spectracsPy/spectracsPyServer.db are
        # EMPTY — every ROI and coefficient column NULL — while the running app captures a perfectly good
        # 400.06-635.87 nm axis. So the live calibration is held in the app's session and is not in the DB
        # this helper reads. ⛔ Do NOT fall back to the pre-Alembic backup values: checked against tonight's
        # own spectra they give 404.86-634.02 nm over 1562 bins against the actual 400.06-635.87 over 1634,
        # i.e. the calibration HAS moved since July and the old numbers would silently mis-assign every band.
        print("ERROR: no ROI / calibration cubic available.")
        print("  The app holds the live calibration in its session; this DB copy is empty. Read the current")
        print("  ROI and the four cubic coefficients off the app's calibration view and pass them:")
        print("      --roi X1,Y1,X2,Y2  --coeffs=A,B,C,D")
        print("  Then verify them in one shot with --check before committing 90 minutes: the printed span")
        print("  must land on ~400.1-635.9 nm over ~1634 bins to match what the bench is producing.")
        return 2

    from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
    backend = getCaptureBackend()
    exposure = arguments.exposure if arguments.exposure is not None else context.get("exposure")
    # Mirror DevCaptureVideoThread: 6500 K fixed white balance, and an exposure that never moves again.
    backend.open(deviceId=device, exposure=exposure or 150, whiteBalanceKelvin=6500)
    if exposure is None:
        exposure = _pickExposure(backend)
    print("camera %s at %s, exposure PINNED at %s, WB 6500 K" % (device, backend.getResolution(), exposure))
    print("⛔ Do NOT re-seat, nudge or open anything until the run ends — the no-re-seat floor is sd 0.063,")
    print("   a re-seat costs 0.70, and one touch would bury the whole curve.")

    promptFor("REFERENCE jar")
    referenceValues, nanometers = captureMean(backend, roi, coefficients, arguments.frames)
    if referenceValues is None:
        print("ERROR: no frames from the camera.")
        return 2
    print("   reference captured (%d frames, peak %.1f DN linear)" % (arguments.frames, referenceValues.max()))

    promptFor("SAMPLE jar")

    if arguments.check:
        # ⭐ The 30-second version of the whole run. A wrong ROI or a stale cubic is invisible in the numbers
        # until the bands land on the wrong wavelengths — and by then 90 minutes are gone. This prints the
        # things that WOULD be wrong: the span, the bin count, the DN, and Q% itself.
        sampleValues, nanometers = captureMean(backend, roi, coefficients, arguments.frames)
        if sampleValues is None:
            print("ERROR: no frames from the camera.")
            return 2
        qPercent, soret, valley, qBand = metricsOf(referenceValues, sampleValues, nanometers)
        digitalNumber = guardDn(sampleValues, nanometers)
        print("\n   CHECK — verify these before running for real:")
        print("     wavelength span   %.2f .. %.2f nm over %d bins (the bench produces ~400.1-635.9 / ~1634)"
              % (nanometers.min(), nanometers.max(), len(nanometers)))
        print("     guard DN          %.1f   (%s, target %g-%g)"
              % (digitalNumber, guardVerdict(digitalNumber), GUARD_TARGET[0], GUARD_TARGET[1]))
        if qPercent is None:
            print("     ⛔ Q% withheld — A_Soret is under the %.2f floor (§3.1). Broken capture or empty beam."
                  % SORET_FLOOR)
            return 2
        print("     A_Soret %.4f   A_valley %.4f   A_Q %.4f" % (soret, valley, qBand))
        print("     Q%%                %.2f   %s" % (qPercent,
              "in domain" if VERDICT_BAND[0] <= qPercent <= VERDICT_BAND[1] else "⛔ OUT OF DOMAIN (§3.1a)"))
        print("\n   ⇒ if the span or Q% look wrong, fix --roi/--coeffs and re-check. Nothing was written.")
        return 0

    target = arguments.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                           "spectracs-references", "tmp", arguments.label,
                                           "clearing_time_course.csv")
    target = os.path.normpath(target)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    # ⛔ NEVER OVERWRITE A PREVIOUS SESSION. Re-running the same jar under the same --label is exactly
    # the experiment this script is for, and the naive `open(target,"w")` would destroy the very
    # baseline the re-run exists to be compared against. The earlier file becomes the comparison.
    comparePath = arguments.compare
    if os.path.exists(target):
        if comparePath is None:
            comparePath = target
        stem, extension = os.path.splitext(target)
        index = 2
        while os.path.exists("%s_%d%s" % (stem, index, extension)):
            index += 1
        target = "%s_%d%s" % (stem, index, extension)
        print("   ⚠ a CSV for this label already exists — writing %s instead" % os.path.basename(target))
        print("     and comparing against %s" % os.path.basename(comparePath))
    baseline = loadBaseline(comparePath)
    if baseline:
        print("   ⭐ baseline: %d samples on its CLEARING BRANCH, A_valley %.4f -> %.4f, W %.4f -> %.4f"
              % (len(baseline), baseline[0][0], baseline[-1][0], baseline[0][1], baseline[-1][1]))
        print("     (only the branch where A_valley still falls — after that it is degenerate and the"
              " match would be meaningless)")

    print("\n%8s %7s %8s %7s %8s %8s %9s %9s %11s  %s"
          % ("t (min)", "clock", "Q%", "DN", "ΔQ%", "W", "A_Soret", "A_valley",
             "W vs base" if baseline else "A_Q", "readiness"))
    print("   " + "-" * 104)

    samples = []
    started = time.time()
    deadline = started + arguments.minutes * 60.0
    announced = False
    while time.time() <= deadline:
        sampleValues, nanometers = captureMean(backend, roi, coefficients, arguments.frames)
        if sampleValues is None:
            print("   (no frames — skipping this point)", flush=True)
            time.sleep(arguments.every * 60.0)
            continue
        minutes = (time.time() - started) / 60.0
        qPercent, soret, valley, qBand = metricsOf(referenceValues, sampleValues, nanometers)
        digitalNumber = guardDn(sampleValues, nanometers)
        samples.append({"minutes": minutes, "qPercent": qPercent, "soret": soret, "valley": valley,
                        "qBand": qBand, "dn": digitalNumber})
        inDomain = VERDICT_BAND[0] <= qPercent <= VERDICT_BAND[1]
        isSettled, driftQ, driftDn = settledYet(samples)
        readiness = ("SETTLED (ΔQ%% %+.2f, ΔDN %+.1f / %.0f min)" % (driftQ, driftDn or 0.0, SETTLED_WINDOW_MIN)
                     if isSettled else
                     ("still moving: ΔQ%% %+.2f over %.0f min" % (driftQ, SETTLED_WINDOW_MIN)
                      if driftQ is not None else "warming up"))
        # ⭐ Q% and DN lead the row — they are the two numbers being watched, and the bands behind them
        # are context. ⚠ flush=True on EVERY line: a 90-minute run whose output only appears at the end
        # is unwatchable, and block-buffered stdout does exactly that the moment this is piped or
        # redirected (it bit the archive dry-run earlier the same day).
        W = bandRatio(samples[-1])
        # ⭐ the matched-clearing comparison: the SAME turbidity in the baseline run, and how far W has
        # moved from it. This is the re-run's whole answer, computed live instead of afterwards.
        match = baselineAt(baseline, valley)
        if match is not None and W is not None:
            lastColumn = "%.4f %+5.1f%%" % (match[1], 100.0 * (W / match[1] - 1.0))
        else:
            lastColumn = "%.4f    " % qBand
        print("%8.1f %7s %8.2f %7.1f %8.2f %8.4f %9.4f %9.4f %11s  %s%s"
              % (minutes, time.strftime("%H:%M"), qPercent,
                 digitalNumber if digitalNumber is not None else float("nan"),
                 qPercent - samples[0]["qPercent"], W if W is not None else float("nan"),
                 soret, valley, lastColumn, readiness,
                 "" if inDomain else "  ⛔ Q% OUT OF DOMAIN — no verdict (§3.1a)"), flush=True)
        if guardVerdict(digitalNumber) != "in-window":
            print("           ⚠ DN %s (target %g-%g) — the guard would flag this capture on the bench"
                  % (guardVerdict(digitalNumber), GUARD_TARGET[0], GUARD_TARGET[1]), flush=True)
        if isSettled and not announced:
            announced = True
            print("   ⭐ SETTLED at t = %.0f min — the drift over the last %.0f min is below the %.2f refill"
                  " floor (§10.5). Everything after this is confirmation." % (minutes, SETTLED_WINDOW_MIN,
                                                                             REFILL_FLOOR), flush=True)
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(arguments.every * 60.0, remaining))

    endReference = None
    if arguments.reference_at_end:
        # ⭐ §16.7 — a blank measured 90 minutes later bounds how much of the curve above was the
        # REFERENCE moving rather than the sample clearing. Without it the two are confounded and the
        # whole time-course rests on an assumption nobody checked.
        promptFor("REFERENCE jar again (the run is over — this bounds the reference's own drift)")
        endValues, endNanometers = captureMean(backend, roi, coefficients, arguments.frames)
        if endValues is not None:
            driftSoret, driftValley, driftQ = referenceDrift(referenceValues, endValues, endNanometers)
            print("\n   REFERENCE vs ITSELF, %.0f min apart — peak %.1f -> %.1f DN linear (%+.1f %%)"
                  % (arguments.minutes, referenceValues.max(), endValues.max(),
                     100.0 * (endValues.max() / referenceValues.max() - 1.0)))
            if None in (driftSoret, driftValley, driftQ):
                print("      ⛔ could not measure the drift bands.")
            else:
                print("      D = -log10(R_end/R_start), i.e. the additive error carried by every A in the run:")
                for name, value in (("Soret ", driftSoret), ("valley", driftValley), ("Q     ", driftQ)):
                    print("        D_%s %+.4f A" % (name, value))
                last = samples[-1]
                soretC = last["soret"] - driftSoret
                valleyC = last["valley"] - driftValley
                qBandC = last["qBand"] - driftQ
                if soretC > 0:
                    corrected = 100.0 * (qBandC - valleyC) / soretC
                    shift = corrected - last["qPercent"]
                    print("      ⇒ the LAST sample, corrected for it: Q%% %.2f -> %.2f  (%+.2f)"
                          % (last["qPercent"], corrected, shift))
                    # ⛔⛔ COMPARE AGAINST THE POST-CLEARING DRIFT, NEVER THE TOTAL. The total ΔQ% is
                    # dominated by the CLEARING — 8-12 units of it — so dividing by that makes any lamp
                    # drift look negligible by construction. On 2026-08-15 it reported "4 % — negligible,
                    # the curve is the SAMPLE" for a correction that was in fact 94 % of the only part
                    # under discussion. The clearing is not in question; the slope AFTER it is.
                    index = min(range(len(samples)), key=lambda k: samples[k]["qPercent"])
                    postDrift = last["qPercent"] - samples[index]["qPercent"]
                    total = last["qPercent"] - samples[0]["qPercent"]
                    print("      ⇒ the run's total ΔQ%% is %+.2f, but that is mostly the CLEARING and is not"
                          " what is in question." % total)
                    floor = 3.0 * 0.063
                    if abs(postDrift) < floor:
                        print("      ⇒ the POST-CLEARING drift is %+.2f, inside the %.2f measurement floor —"
                              " nothing to attribute." % (postDrift, floor))
                    else:
                        share = 100.0 * abs(shift) / abs(postDrift)
                        print("      ⇒ POST-CLEARING drift (t=%.1f min onward): %+.2f. The lamp accounts for"
                              " %.0f %% of it." % (samples[index]["minutes"], postDrift, share))
                        print("         %s"
                              % ("⛔ the LAMP dominates — this run's slope is NOT the sample" if share > 50
                                 else ("⚠ a material share; quote the corrected slope too" if share > 10
                                       else "⭐ negligible: the slope is the SAMPLE")))
                    # ⭐ W matters more than Q% for chemistry, so correct it too — but say when the
                    # correction is not trustworthy: A_valley is tiny and a constant end-state offset can
                    # drive it negative, which is unphysical.
                    if valleyC < 0:
                        print("      ⚠ the correction drives A_valley negative (%+.4f) — it is applied as a"
                              " constant end-state offset to a band whose absorbance is tiny, so the"
                              " corrected W below is INDICATIVE only." % valleyC)
                    if soretC - valleyC > 0:
                        print("      ⇒ W %.4f -> %.4f corrected (%+.1f %%)"
                              % (bandRatio(last), (qBandC - valleyC) / (soretC - valleyC),
                                 100.0 * (((qBandC - valleyC) / (soretC - valleyC)) / bandRatio(last) - 1.0)))
                print("      ⚠ this bundles a re-seat of the reference jar in with any lamp drift, so it is"
                      " an UPPER bound on the lamp.")

    with open(target, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["minutes", "qPercent", "W", "aSoret", "aValley", "aQ", "guardDn", "guardVerdict"])
        for row in samples:
            ratio = bandRatio(row)
            writer.writerow(["%.3f" % row["minutes"], "%.4f" % row["qPercent"],
                             "" if ratio is None else "%.6f" % ratio, "%.6f" % row["soret"],
                             "%.6f" % row["valley"], "%.6f" % row["qBand"],
                             "" if row["dn"] is None else "%.2f" % row["dn"], guardVerdict(row["dn"])])

    print("\n   %d samples over %.0f min -> %s" % (len(samples), arguments.minutes, target))
    if len(samples) >= 2:
        first, last = samples[0], samples[-1]
        print("   Q%%  %.2f -> %.2f  (%+.2f, %.1f x the %.2f refill floor)"
              % (first["qPercent"], last["qPercent"], last["qPercent"] - first["qPercent"],
                 abs(last["qPercent"] - first["qPercent"]) / REFILL_FLOOR, REFILL_FLOOR))
        if None not in (first["dn"], last["dn"]):
            print("   DN  %.1f -> %.1f  (%+.1f, %+.0f %%)"
                  % (first["dn"], last["dn"], last["dn"] - first["dn"],
                     100.0 * (last["dn"] / first["dn"] - 1.0)))
        isSettled, driftQ, _ = settledYet(samples)
        print("   ⇒ %s" % ("SETTLED — safe to measure on this recipe after the time shown above." if isSettled
                           else "NOT settled after %.0f min: ΔQ%% is still %+.2f per %.0f min. ⛔ Either wait"
                                " longer or fix the preparation." % (arguments.minutes, driftQ or 0.0,
                                                                     SETTLED_WINDOW_MIN)))

        # ⭐⭐ THE ANSWER THE RUN EXISTS TO PRODUCE — which sample to believe, and what it is worth.
        gate = clearingDone(samples)
        print()
        if gate is None:
            print("   ⛔ THE SAMPLE NEVER STOPPED CLEARING — A_valley was still falling at the end.")
            print("      There is no best value in this run: every reading is contaminated by turbidity.")
        else:
            index = min(range(len(samples)), key=lambda k: samples[k]["qPercent"])
            best, atMinutes = vertexRead(samples, index)
            print("   ⭐ BEST VALUE  Q%% %.2f  at t = %.1f min" % (best, atMinutes))
            print("      clearing finished at t = %.1f min (A_valley stopped falling); the Q%% minimum is"
                  % samples[gate]["minutes"])
            print("      where turbidity (decaying) hands over to photodamage (growing), so both"
                  " contaminations are smallest there.")
            print("      read as a parabola vertex, not the raw minimum, which is biased low by ~0.9 sd.")
            undamaged, ratePerHour = zeroDoseEstimate(samples, index)
            if undamaged is not None:
                print("   ⚠ zero-dose EXTRAPOLATION: %.2f  (the damage line runs %+.2f Q%%/hour, so %.2f of"
                      % (undamaged, ratePerHour, best - undamaged))
                print("      damage had already accumulated before the sample finished clearing).")
                print("      ⛔ Reported separately and never folded in — it assumes the damage rate during"
                      " clearing matched the rate after it.")
            if baseline:
                match = baselineAt(baseline, samples[index]["valley"])
                W = bandRatio(samples[index])
                if match is not None and W is not None:
                    change = 100.0 * (W / match[1] - 1.0)
                    print()
                    print("   ⭐⭐ VS THE BASELINE, at matched clearing (A_valley %.4f vs %.4f):"
                          % (samples[index]["valley"], match[0]))
                    print("        W  %.4f  ->  %.4f   %+.1f %%" % (match[1], W, change))
                    print("        A_Soret %.4f -> %.4f  %+.1f %%   ⚠ if this ROSE, the fill has"
                          " concentrated (evaporation) and W is dose-sensitive"
                          % (match[3], samples[index]["soret"], 100.0 * (samples[index]["soret"] / match[3] - 1.0)))
                    print("        ⇒ %s" % ("the change SURVIVED — irreversible, i.e. chemistry"
                                            if change > 2.0 else
                                            ("it RELAXED back — NOT chemistry, a reversible physical state"
                                             if change < -2.0 else
                                             "unchanged within ~2 %% — no detectable irreversible change")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
