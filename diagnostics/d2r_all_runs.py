"""Every archived run that can carry a 2nd derivative at 624 nm, in one figure. (Edwin, 2026-08-25)

⛔ WHY SO FEW. A 2nd derivative at 624 nm needs the band's FAR FLANK, so the trace must reach past
632 nm. The archive's 629.8 nm epoch cannot supply that at all -- which is the standing limitation of
`d2R` as a metric and the reason this figure is smaller than the corpus. Every count in the figure is
COMPUTED, never typed, because a new session can change it -- 20260826Esterer added four at 636 nm.

    d2R = D2(624) / D2(568),  both taken as the MINIMUM of the 2nd derivative inside a PINNED window.

⛔⛔ THE WINDOWS ARE PINNED, NOT SEARCHED, and that is load-bearing. Two INSTRUMENT features sit inside
the Q region: the 581 nm reference minimum (`DOC_lamp_rebuild.md` section 326) and the 609 nm Bayer
crossover (section 6 of the same). Searching 560-582 for "the 568 dip" lands on the 581 artefact in the
large majority of runs -- ALL of the isopropanol ones. Hence 565-573 and 621-627, both clear of both
artefacts. ⛔ Do not quote a number here: it moves with every session. `main()` RECOUNTS it and prints
the per-solvent split, which is the only version that cannot go stale.

Writes  spectracs-references/tmp/20260825_d2r_all_runs.pdf

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/d2r_all_runs.py
"""
import os
import sys
import hashlib
import tempfile
import textwrap

import numpy
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors
from scipy.signal import savgol_filter
import matplotlib.pyplot as pyplot
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import all_metrics_archive as metrics
from solvent_colour_separation import SUNFLOWER as INDEX_MATCHED

GRID = numpy.arange(500.0, 634.01, 0.25)
SMOOTH_NM = 7.0
RED_WINDOW = (621.0, 627.0)
Q_WINDOW = (565.0, 573.0)
CUT = 1.0
OUT = os.path.join(archive.ARCHIVE, "20260825_d2r_all_runs.pdf")

# ⭐ The archive's series names are not oil names, and the SAME oil appears under several of them.
# Without this the by-solvent panel cannot line Lugitsch in isopropanol up against Lugitsch in sunflower.
SERIESOIL = {"20260812BillJaNatuerlich": "Ja Natuerlich",
             "20260812_BillaClever": "Billa Clever", "20260812_BillaCleverB": "Billa Clever",
             "20280819BillaClever": "Billa Clever",
             "20260814_Lugitsch_A": "Lugitsch", "20260817LigitschA": "Lugitsch"}

# The sunflower sessions, which `walkReports` cannot label because they are not in the archive's own
# GREEN/BROWN sets. Runs are DISCOVERED, not enumerated -- 20260826Esterer carries four.
# ⭐⭐ EYE-RANKING RECORDED 2026-08-27 (Edwin): Esterer and Stekko are BOTH GREEN, a little browner than
# Lugitsch but green — visible by eye, and photographed. They were held as "unlabelled" all through the
# 08-26 session precisely so their class could not be taken from the metric that was being judged on them
# (SPEC_metric_research §7 / M9). The label now comes from the eye, which is what makes them scorable.
# ⭐ THE INTERESTING TEST IS NO LONGER GREEN-VS-BROWN — all three pass that easily. It is whether the
# metric REPRODUCES THE EYE'S ORDER WITHIN green: Lugitsch greenest, then Esterer and Stekko.
TODAY = {"20260824Lugitsch": ("Lugitsch", "green"), "20260824SparPremium": ("Spar Premium", "brown"),
         "20260824SparSBudget": ("Spar S-Budget", "brown"),
         "20260826Esterer": ("Esterer", "green"),
         "20260826Stekko": ("Stekko", "green"),
         # ⭐ Lugitsch is SCORED where Esterer and Stekko are not, and the difference is not the metric:
         # Lugitsch already carries an eye-ranking in the archive, in all three solvents. Reusing that
         # label is reading prior truth; inventing one for a new oil would be reading the metric.
         "20260826Lugitsch": ("Lugitsch", "green"),
         # ⭐ A SECOND, INDEPENDENTLY PREPARED FILL of the same oil on the same evening. Matched to
         # 20260824Lugitsch/001 to within 7 % on the Soret and 1 % on the valley, and it reads with fill
         # A, not with 08-24 -- which is what rules the fill out as the cause of the session step.
         "20260826LugitschB": ("Lugitsch", "green"),
         # ⭐ A THIRD independently prepared fill of the same oil, ~2 h after B. It is the most turbid of
         # the three (A_valley 0.119 against A's 0.049) and reads the highest Rv — which is what put the
         # metric's turbidity dependence on the table.
         "20260826LugitschC": ("Lugitsch", "green"),
         # ⭐⭐ A SECOND ESTERER FILL, and the one that refuted the turbidity story. Its A_valley is
         # indistinguishable from fill A's (0.171 vs 0.182) while its Rv is 15.4 HIGHER — so the +0.86
         # correlation the three Lugitsch fills showed was three points of a coincidence.
         "20260826EstererB": ("Esterer", "green"),
         # ⚠ WAS `20260826LugitschD`, renamed 2026-08-27: Edwin believes the fill was drawn from the
         # Esterer bottle by mistake. See PROVISIONAL_ATTRIBUTION — it is PLOTTED but it SCORES NOTHING.
         "20260826EstererC": ("Esterer", "green"),
         # ⚠ Measured AS Esterer — the label is the bench's, and it is not mine to withdraw because the
         # numbers surprise me. ⛔ But it reads Rv 105.1/109.8 against the other Esterer fills' 77–90,
         # repeats to 4.8 within itself, and is indistinguishable from Lugitsch fill C (107.2). It is
         # SCORED; what it costs is reported by `eyeOrderNote`.
         "20260826EstererD": ("Esterer", "green"),
         # ⭐⭐ THE FIRST FILL MADE BY A DIFFERENT RECIPE (see PREP_PROTOCOL). Two-stage dilution:
         # 1 ml sunflower + the capillary, dissolved, then topped to 4 ml and rotated ~60 s -- no hard
         # arm-swing. It is the TEST of the dissolution story, and it REFUTED it: dissolution measurably
         # improved (A_Soret +10.2 %, A_valley -6.9 % against fill B) while Rv moved -1.7, i.e. one run's
         # noise. ⇒ a real preparation gain that Rv is blind to, because BOTH of its bands held still.
         "20260826EstererE": ("Esterer", "green"),
         # ⛔⛔ NOT SUNFLOWER — MCT OIL. Present in this dict ONLY so that both of its runs pass through
         # `take` and are ANNOUNCED as excluded; every run of it is in EXCLUDED below and it scores
         # nothing. The label here is never read. See EXCLUDED for why it cannot be plotted beside the
         # sunflower fills, and ⛔ note the report header WRONGLY records `solvent: SUNFLOWER_OIL`.
         "20260828EstererA": ("Esterer", "green"),
         # ⭐⭐ THE MATCHED CONTROL for the MCT fill above: same oil, same evening, same 6 ml volume,
         # `c` matched to 1.3 %. It is the fill that made the MCT comparison interpretable at all.
         # ⚠ Its preparation is NOT the MCT fill's — 180 s in the sonic bath and a 60 s stand in the
         # jar, against 90 s and no stand. See PREP_PROTOCOL; the difference is why the FLOOR comparison
         # between the two is confounded while the `Rv` comparison is not (a flat pedestal cancels in
         # `Rv` by construction; adding this fill's measured MCT excess to it moves `Rv` by 0.0).
         "20260828EstererB": ("Esterer", "green"),
         # ⭐⭐ A SECOND INDEPENDENT FILL of B, same evening, same recipe, same volume — i.e. a σ_fill
         # replicate under the NEW preparation, which is the first one the archive has. Both fills
         # repeat to 1.1 `Rv` WITHIN themselves (the best on record) and differ by 8.8 BETWEEN
         # themselves. ⇒ the vortex improved the measurement and left σ_fill alone.
         "20260828EstererC": ("Esterer", "green"),
         # ⛔ D, E and F are here ONLY so their runs pass through `take` and are ANNOUNCED as excluded.
         # Every run of each is in EXCLUDED below; see OTHER_REFERENCE for why. The label is never read.
         "20260828EstererD": ("Esterer", "green"),
         "20260828EstererE": ("Esterer", "green"),
         "20260828EstererF": ("Esterer", "green"),
         # ⭐ The first BROWN fills made under the settled recipe, and a replicate PAIR of them --
         # `SPEC_metric_research.md` §16.9 is built on this pair. Excluded here for their reference
         # method, not for their quality.
         "20260828BillaCleverA": ("Billa Clever", "brown"),
         "20260828BillaCleverB": ("Billa Clever", "brown")}

# ⚠⚠ FILLS NOT MADE BY THE RECIPE THE REPORT HEADER CLAIMS. The plugin writes a hardcoded
# `prepProtocol` string into every report, so a recipe change is INVISIBLE in the record until the
# constant is updated. Until then the exception lives here, named, and is printed on every run.
# ⛔ Mixing preparations inside one oil's fill set without saying so is how a protocol change turns
# into unexplained σ_fill six weeks later.
PREP_PROTOCOL = {
    "20260826EstererE": "two-stage: 1 ml + capillary, which EMPTIES ITSELF in the solvent \u2014 no "
                        "arm-swing;\n     then ~45 s of FAST rotation at the bottom while still "
                        "concentrated, then to 4 ml and ~60 s more.\n     The 40 slow inversions are "
                        "gone. (header still records invert-40-after-capillaries-clear)",
    # ⭐ THE VORTEX RECIPE. The hand rotation of EstererE becomes a fixed-duration machine step, and
    # the volume moves 4 ml -> 6 ml (SPEC_capture_quality.md §16.23.2b's volume rule, which puts the
    # DN guard at ~48 instead of EstererE's 19.4).
    "20260828EstererB": "1 ml + 1 capillary, 40 s VORTEX, up to 6 ml, 60 s vortex,\n"
                        "     180 s ultrasonic bath, then 60 s standing in the jar.\n"
                        "     (header still records invert-40-after-capillaries-clear)",
    # ⚠ IDENTICAL TO B, deliberately — this is the replicate that measures σ_fill under that recipe.
    "20260828EstererC": "identical to 20260828EstererB — the σ_fill replicate.\n"
                        "     (header still records invert-40-after-capillaries-clear)"}

# ⛔⛔ ATTRIBUTION UNCERTAIN — PLOTTED, LABELLED, BUT EXCLUDED FROM EVERY STATISTIC.
# ⭐⭐ THE TRAP THIS EXISTS TO STOP. This fill was measured as Lugitsch, read Rv 86.8 — below Esterer's
# best fill — and so produced the FIRST Lugitsch/Esterer overlap in the archive. It was then reassigned
# to Esterer, partly because its numbers look like Esterer's. Letting it score would remove the overlap
# it created, and the metric would have been used to fix the label that the metric is then judged on.
# That is the circularity SPEC_metric_research §7's M9 gate exists to stop, arriving from a new direction.
# ⇒ it may inform NOTHING until an independent Esterer fill confirms the reassignment at the bench.
PROVISIONAL_ATTRIBUTION = {
    "20260826EstererC": "was measured as Lugitsch; reassigned to Esterer at the bench 2026-08-27, "
                        "NOT yet confirmed"}


def isScored(row):
    """A row may enter a corridor, a cut or an error count only if its OIL is certain."""
    return row["class"] in SCORED and sessionOf(row) not in PROVISIONAL_ATTRIBUTION
CLASSCOLOR = {"green": "#2e7d32", "brown": "#8b4513", "unlabelled": "#1565c0"}
# ⭐ SAME OIL, DIFFERENT FOLDER = DIFFERENT SHADE. Lugitsch spans six sessions and Billa Clever five,
# and the sunflower Lugitsch column alone runs d2R 1.10-2.76 -- session scatter that a single flat
# colour hides completely. The ramp stays INSIDE the class hue so green-vs-brown, which is what the
# figure is actually about, survives; only the lightness carries the session. Both ends are dark
# enough to read as text on white, because the strip page tints its row labels with this too.
# ⛔ Do not darken the far end further. Past roughly these values every ramp reads as BLACK, and the
# class hue -- the thing the figure is actually about -- is gone from the row labels.
CLASSRAMP = {"green": ("#8bc34a", "#1b5e20"),
             "brown": ("#cf9a5f", "#6b3410"),
             "unlabelled": ("#66b0e8", "#10429b")}
SCORED = ("green", "brown")                    # the classes a cut may be judged against

# ⭐⭐ THE 08-26 RUN POLICY (Edwin, 2026-08-27). Only the FIRST TWO READS of each aliquot are used. Later
# reads carry more lamp on a sample the lamp is known to change, and they are exactly where the widest
# within-fill spreads came from (Stekko 14.8 Rv over four runs against 0.9 over the first two). Two reads
# per fill is a repeatability figure; four is a dose series wearing one.
# ⛔⛔ THE FIRST TWO *DISTINCT* RUNS, NOT THE FILES NAMED 001 AND 002 — and the difference is real, not
# pedantic. 20260826Lugitsch/002 is a byte-identical copy of 001, a FAILED SAVE rather than a read; taking
# filenames would spend a slot on it and discard 003, the aliquot's genuine second read, leaving that fill
# with n = 1 and no within-fill scatter at all. A save failure must not cost a measurement.
# ⛔ It is a POLICY, not a filter buried in a loop: it changes what every number on these pages means, so
# it is named here, shared with `reference_band_scan`, and announced on every run.
# ⚠ A TUPLE, and deliberately not the prefix "202608": widening it that far would also catch the
# 08-22 and 08-24 sessions, which keep all three of their reads, and silently shrink the corpus.
# ⭐ Adding "20260828" changes NOTHING today — both 08-28 fills carry exactly two reads — but without
# it a third read added later would be kept while 08-26's third read is dropped, i.e. two rules at once.
LATE_RUN_SESSIONS = ("20260826", "20260828")
KEPT_RUN_COUNT = 2

# ⛔ HAND-EXCLUDED RUNS. Not deleted, not silently skipped: named here with a reason, announced on
# every run, and printed on the figure. A run dropped by judgement has to stay visible or the corpus
# quietly becomes whatever was convenient. Edwin's call, 2026-08-26, to be revisited.
EXCLUDED = {"20260826Lugitsch/004.pdf": "reads strange on the day — set aside pending discussion",
            # ⛔ NOT A MEASUREMENT OF THE OIL. A deliberately spoiled sample, run only to exercise the
            # clearing-4.0 read after the app restart. Its Q% is 8.0 against ~17 for the real fills and
            # its 624 band has collapsed; scoring it as Lugitsch would put a spoiled oil in the green set.
            "20260826LugitschC/test.pdf": "spoiled sample, software test only — not the oil",
            # ⛔⛔ EDWIN'S CALL, 2026-08-27 — AND THE ONE EXCLUSION THAT NEEDS WATCHING. D is the only
            # fill made with the hard arm-centrifuge extrusion, a step the two-stage recipe has since
            # RETIRED, so it is the last fill of a procedure that no longer exists. That is a reason
            # about the METHOD, not about the number, which is what makes it admissible.
            # ⚠ But it is still a fill removed after its value was seen, and it is the single largest
            # term in Esterer's σ_fill: 12.4 with it, 6.9 without. Both figures are printed on every
            # run so the cost of this decision can never be quiet. Revisit if the swing is ever
            # replicated — one fill by D's own method settles it.
            "20260826EstererD/001.pdf": "hard arm-swing extrusion, a retired procedure — set aside "
                                        "2026-08-27 pending a replicate",
            "20260826EstererD/002.pdf": "hard arm-swing extrusion, a retired procedure — set aside "
                                        "2026-08-27 pending a replicate",
            # ⛔⛔ A DIFFERENT SOLVENT, not a different fill. `20260828EstererA` is pumpkin oil in
            # **MCT** (medium-chain triglyceride), the only such fill in the archive. Edwin's call
            # 2026-08-29: it must not appear on pages whose whole question is what the metric does
            # within one solvent, and it cannot join the "sunflower" column without making that column
            # a mixture.
            # ⚠ THE HEADER DOES NOT SAY SO — `solvent` reads `SUNFLOWER_OIL` on both runs, because the
            # plugin writes a hardcoded constant. The solvent was identified from the REFERENCE leg,
            # which IS the pure solvent: normalised at 600 nm the two 08-28 references differ by
            # RMS 0.054 over 440-630 nm (MCT is water-clear, sunflower is yellow and reads 1.10 at
            # 440 nm against MCT's 1.25), while B and C agree to RMS 0.0086.
            # ⭐ It is not being buried: `Rv` 70.1 / 64.1, fill mean 67.1, against 86.7 ± 6.6 for the
            # six sunflower Esterer fills — -2.95 σ. That belongs in SPEC_red_ratio_metric, not here.
            "20260828EstererA/001.pdf": "pumpkin oil in MCT, not sunflower — a different solvent",
            "20260828EstererA/002.pdf": "pumpkin oil in MCT, not sunflower — a different solvent",
            # ⛔⛔ SAME-JAR REFERENCE — a different measurement, not a different fill. See OTHER_REFERENCE
            # for the method and for the `pq` drift that makes even their internal comparison unsafe.
            "20260828EstererD/001.pdf": "same-jar reference — not on the archive's footing",
            "20260828EstererD/002.pdf": "same-jar reference — not on the archive's footing",
            "20260828EstererE/001.pdf": "same-jar reference — not on the archive's footing",
            "20260828EstererE/002.pdf": "same-jar reference — not on the archive's footing",
            "20260828EstererF/001.pdf": "same-jar reference — not on the archive's footing",
            "20260828EstererF/002.pdf": "same-jar reference — not on the archive's footing",
            "20260828BillaCleverA/001.pdf": "same-jar reference — not on the archive's footing",
            "20260828BillaCleverA/002.pdf": "same-jar reference — not on the archive's footing",
            "20260828BillaCleverB/001.pdf": "same-jar reference — not on the archive's footing",
            "20260828BillaCleverB/002.pdf": "same-jar reference — not on the archive's footing"}
# ⛔ EXCLUDED FOR A REASON THAT IS NOT ABOUT THE FILL. These sessions are in `EXCLUDED` because they
# are a DIFFERENT SOLVENT, so they are not candidate members of any sunflower σ_fill and must never be
# priced as one (see `excludedCost`). They are still announced on every run like any other exclusion.
OTHER_SOLVENT = {"20260828EstererA": "MCT"}

# ⭐ `SPEC_metric_research.md` §14.2's pigment-free windows, shared with `diagnostics/red_anchor_ab.py`.
# ⛔ The blue one is load-bearing: dropping 472-500 turns RvCont's corridor from +5.1 to -6.1.
CONTINUUM_WINDOWS = [(472.0, 500.0), (505.0, 555.0), (588.0, 604.0)]

# ⛔⛔ A DIFFERENT REFERENCE METHOD, not a different fill. `20260828EstererD/E/F` were measured with the
# reference and the sample in the SAME JAR: 4 ml of solvent goes into the measurement jar, the reference
# is captured, and only then is the oil dosed in. That removes the jar-to-jar term every other run in
# this archive carries, so their absorbances are not on the same footing as anything else here.
# ⚠ AND THEY CARRY A TIME TERM. Across the six same-jar runs of 2026-08-29, 03:32 -> 04:53, `A_valley`
# climbs 0.0371 -> 0.0738, the floor 0.0563 -> 0.0949 and `pq` = (A_Q-Av)/(A_Soret-Av) 0.1267 -> 0.1537,
# monotonically. ⛔ `pq` is dose-free AND floor-free -- an oil property -- so it must not drift, and it
# does. Until that is explained the three fills cannot be scored against each other, let alone against
# the two-jar corpus.
# ⭐ They are NOT priced as a σ_fill cost, for the same reason `OTHER_SOLVENT` is not: a fill set aside
# because it was MEASURED differently is not a member of the population whose scatter is being reported.
OTHER_REFERENCE = {"20260828EstererD": "same-jar reference",
                   "20260828EstererE": "same-jar reference",
                   "20260828EstererF": "same-jar reference",
                   # ⚠ THE TWO BROWN FILLS OF THAT NIGHT, and the ones whose absence is most visible:
                   # without them the 08-28 row reads "1 oils" on a night that measured two. They are
                   # same-jar like D/E/F (A confirmed by Edwin, B by its reference fingerprint), so they
                   # go out by the same rule -- but they are NAMED here and in the caption, because
                   # 2026-08-29 they were simply absent from every page with nothing saying why.
                   "20260828BillaCleverA": "same-jar reference",
                   "20260828BillaCleverB": "same-jar reference"}

SOLVENTMARK = {"isopropanol": "o", "sunflower": "s", "spirit": "^"}


def firstDistinctRuns(series, limit=KEPT_RUN_COUNT):
    """The first `limit` DISTINCT reads of one fill, plus everything skipped and why.

    ⚠ A duplicate does NOT consume a slot, and neither does a hand-excluded run: the slots are for READS
    OF THE ALIQUOT, and a failed save is not a read. ⛔ Shared rather than reimplemented — three scripts
    disagreeing about which runs exist is worse than any of their individual answers."""
    folder = os.path.join(archive.ARCHIVE, series)
    digests, kept, skipped = {}, [], []
    for name in sorted(f for f in os.listdir(folder) if f.endswith(".pdf")):
        relative = "%s/%s" % (series, name)
        if relative in EXCLUDED:
            skipped.append((relative, "excluded by hand"))
            continue
        with open(os.path.join(archive.ARCHIVE, relative), "rb") as handle:
            digest = hashlib.md5(handle.read()).hexdigest()
        if digest in digests:
            skipped.append((relative, "byte-identical to %s" % digests[digest]))
            continue
        digests[digest] = relative
        if not series.startswith(LATE_RUN_SESSIONS) or len(kept) < limit:
            kept.append(relative)
        else:
            skipped.append((relative, "later read of the same aliquot"))
    return kept, skipped


def secondDerivative(nm, absorbance):
    y = numpy.interp(GRID, nm, absorbance)
    width = int(SMOOTH_NM / 0.25)
    width += (width + 1) % 2
    return savgol_filter(y, width, 3, deriv=2, delta=0.25)


def dipIn(d2, low, high):
    inside = (GRID >= low) & (GRID <= high)
    return float(d2[inside].min())


def collect():
    indexed = {relative for _, relative in INDEX_MATCHED}
    rows = []
    seen = {}                                  # content digest -> the run that claimed it first
    duplicates = []
    excluded = []
    lateRuns = []
    with tempfile.TemporaryDirectory() as scratch:
        def take(relative, label, oil, solvent):
            path = os.path.join(archive.ARCHIVE, relative)
            # ⛔ A BYTE-IDENTICAL COPY IS NOT A REPLICATE. 20260826Lugitsch/002.pdf is 001.pdf again,
            # and counting it would manufacture a perfect agreement out of one measurement -- the same
            # trap the archive walk hit before (duplicates were never labelled). Digest, don't trust.
            with open(path, "rb") as handle:
                digest = hashlib.md5(handle.read()).hexdigest()
            if relative in EXCLUDED:
                excluded.append(relative)
                return
            if digest in seen:
                duplicates.append((relative, seen[digest]))
                return
            seen[digest] = relative
            workflow = archive.workflowOf(path, scratch)
            if workflow is None:
                return
            trace = archive.despikedTrace(workflow)
            if trace is None:
                return
            nm, absorbance = trace
            if nm[-1] < 632.0:                     # no far flank -> no 2nd derivative at 624
                return
            d2 = secondDerivative(nm, absorbance)
            def bandMean(low, high):
                inside = absorbance[(nm >= low) & (nm <= high)]
                return float(inside.mean())
            valley = bandMean(500.0, 560.0)
            qBand = bandMean(565.0, 580.0)
            rows.append({"run": relative, "class": label, "oil": oil, "solvent": solvent, "d2": d2,
                         "provisionalOil": relative.split("/")[0] in PROVISIONAL_ATTRIBUTION,
                         "d2R": dipIn(d2, *RED_WINDOW) / dipIn(d2, *Q_WINDOW),
                         "Rv": 100.0 * (bandMean(622.0, 627.0) - valley) / (qBand - valley)})

        for label, relative in INDEX_MATCHED:
            series = relative.split("/")[0]
            oil = "Lugitsch" if "ugitsch" in series else "Billa Clever"
            take(relative, label, oil, "spirit" if series.startswith("20260821") else "sunflower")

        for folder, name in archive.walkReports():
            series = os.path.relpath(folder, archive.ARCHIVE)
            series = "(root)" if series == "." else series
            key = name[:-4] if series == "(root)" else "%s__%s" % (series, name[:-4])
            relative = os.path.relpath(os.path.join(folder, name), archive.ARCHIVE)
            if relative in indexed:
                continue
            label = archive.classOf({"series": series, "run": key})
            if label not in ("green", "brown"):
                continue
            take(relative, label, SERIESOIL.get(series, metrics.OILS.get(series, series)), "isopropanol")

        for series, (oil, label) in TODAY.items():
            kept, skipped = firstDistinctRuns(series)
            for relative, why in skipped:
                # ⚠ a HAND exclusion still goes through `take`, which records it — otherwise the
                # "entry never matched a file" guard fires on a file that plainly exists.
                if why == "excluded by hand":
                    take(relative, label, oil, "sunflower")
                else:
                    lateRuns.append("%s (%s)" % (relative, why))
            for relative in kept:
                take(relative, label, oil, "sunflower")
    for relative, original in duplicates:
        print("  [!] DUPLICATE dropped: %s is byte-identical to %s" % (relative, original))
    for relative in excluded:
        session = relative.split("/")[0]
        print("  [!] EXCLUDED BY HAND: %s -- %s%s"
              % (relative, EXCLUDED[relative],
                 "  [priced separately: %s, not a sunflower fill]" % OTHER_SOLVENT[session]
                 if session in OTHER_SOLVENT else
                 "  [priced separately: %s, not the archive's method]" % OTHER_REFERENCE[session]
                 if session in OTHER_REFERENCE else ""))
    for relative in sorted(set(EXCLUDED) - set(excluded)):
        print("  [!] EXCLUDED entry never matched a file: %s" % relative)
    if lateRuns:
        print("  [!] NOT USED (%s policy: first %d DISTINCT reads per fill):"
              % ("/".join(LATE_RUN_SESSIONS), KEPT_RUN_COUNT))
        for entry in sorted(lateRuns):
            print("        %s" % entry)
    for session, note in sorted(PREP_PROTOCOL.items()):
        if any(sessionOf(r) == session for r in rows):
            print("  [!] DIFFERENT PREPARATION: %s -- %s" % (session, note))
        else:
            print("  [!] PREP_PROTOCOL entry never matched a run: %s" % session)
    return rows


def sessionOf(row):
    return row["run"].split("/")[0]


def paint(rows):
    """Give every row a `color`: the class hue, darkened by which folder the run came from.

    An oil measured in ONE folder keeps the flat class colour -- a ramp of one would only invent a
    distinction that is not there. Sessions are ordered by name, which for this archive is by date."""
    groups = {}
    for row in rows:
        groups.setdefault((row["class"], row["oil"]), set()).add(sessionOf(row))
    order = {}
    for key, sessions in groups.items():
        order[key] = sorted(sessions)
    for row in rows:
        key = (row["class"], row["oil"])
        sessions = order[key]
        if len(sessions) == 1:
            row["color"] = CLASSCOLOR[row["class"]]
            continue
        light, dark = CLASSRAMP[row["class"]]
        ramp = matplotlib.colors.LinearSegmentedColormap.from_list("", [light, dark])
        row["color"] = matplotlib.colors.to_hex(ramp(sessions.index(sessionOf(row))
                                                     / float(len(sessions) - 1)))
    return rows


def sessionHandles(rows):
    """Legend entries for the oils that span more than one folder -- the only ones a shade encodes."""
    handles = []
    for (label, oil), _ in sorted({(r["class"], r["oil"]): None for r in rows}.items()):
        sessions = sorted({sessionOf(r) for r in rows if r["class"] == label and r["oil"] == oil})
        if len(sessions) < 2:
            continue
        for session in sessions:
            row = next(r for r in rows if sessionOf(r) == session)
            handles.append(pyplot.Line2D([], [], ls="", marker="o", color=row["color"], ms=6,
                                         markeredgecolor="black", markeredgewidth=0.4,
                                         label="%s  %s" % (oil[:12], session[:22])))
    return handles


def shortLabel(row):
    """`series run` plus the oil name only when it adds something the series name does not."""
    series, name = row["run"].rsplit("/", 1)
    series = series.replace("_", "")
    run = name[:-4]
    if len(run) > 4:                       # the newchips-style long file names
        run = run[:4]
    oil = row["oil"]
    if oil.lower().replace(" ", "").replace("-", "").replace("_", "") in series.lower():
        oil = ""
    label = "%s %s" % (series[:23], run)
    mark = " ?" if row.get("provisionalOil") else ""
    return "%-28s %s%s" % (label, oil[:11], mark)


def pageStrip(pdf, rows):
    """One row per run, sorted by d2R. ~50 rows still fit an A4 portrait; the label size follows n."""
    ordered = sorted(rows, key=lambda r: -r["d2R"])
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("d2R = D2(624) / D2(568) — every archived run that reaches 632 nm",
                    fontsize=13, fontweight="bold", y=0.975)
    figure.text(0.5, 0.952,
                "2nd derivative, Savitzky–Golay 7 nm / polyorder 3 on a 0.25 nm grid.  "
                "Minima taken in PINNED windows 621–627 and 565–573 nm.",
                ha="center", fontsize=8.5, style="italic")
    axes = figure.add_axes([0.30, 0.055, 0.66, 0.885])
    positions = numpy.arange(len(ordered))
    for position, row in zip(positions, ordered):
        axes.plot(row["d2R"], position, SOLVENTMARK[row["solvent"]],
                  color=row["color"], ms=6, markeredgecolor="black", markeredgewidth=0.4)
    axes.axvline(CUT, color="crimson", lw=1.4, ls="--")
    axes.set_yticks(positions)
    axes.set_yticklabels([shortLabel(r) for r in ordered],
                         fontsize=6.2 if len(ordered) <= 46 else 6.2 * 46.0 / len(ordered),
                         family="monospace")
    for tick, row in zip(axes.get_yticklabels(), ordered):
        tick.set_color(row["color"])
    axes.set_ylim(-1, len(ordered))
    axes.set_xlim(0, max(r["d2R"] for r in ordered) * 1.08)
    axes.invert_yaxis()
    axes.set_xlabel("d2R", fontsize=10, fontweight="bold")
    axes.grid(axis="x", alpha=0.3)
    axes.tick_params(axis="x", labelsize=8)
    scored = [r for r in rows if isScored(r)]
    green = [r["d2R"] for r in scored if r["class"] == "green"]
    brown = [r["d2R"] for r in scored if r["class"] == "brown"]
    axes.text(CUT + 0.05, len(ordered) - 1.5,
              "cut %.2f\ngreen ≥ %.2f\nbrown ≤ %.2f\n%d / %d errors"
              % (CUT, min(green), max(brown), sum(1 for r in scored
                 if (r["class"] == "green") != (r["d2R"] > CUT)), len(scored)),
              fontsize=8, color="crimson", va="bottom")
    fresh = [r for r in rows if r["class"] == "unlabelled"]
    if fresh:
        # Anchor on the MIDDLE unlabelled row and offset in points, so the arrow stays short however
        # many rows the archive grows to.
        marked = [(position, row) for position, row in zip(positions, ordered)
                  if row["class"] == "unlabelled"]
        position, row = marked[len(marked) // 2]
        axes.annotate("%s — %d runs, sunflower\nNOT SCORED: no eye-ranking recorded yet"
                      % (" · ".join(sorted({r["oil"] for r in fresh})), len(fresh)),
                      xy=(row["d2R"], position), xytext=(58, -26), textcoords="offset points",
                      fontsize=7.5, color=CLASSCOLOR["unlabelled"], ha="left", va="center",
                      arrowprops={"arrowstyle": "->", "color": CLASSCOLOR["unlabelled"], "lw": 1.0})
    handles = [pyplot.Line2D([], [], ls="", marker="o", color=CLASSCOLOR[c], ms=7,
                             markeredgecolor="black", label="%s (shade = folder)" % c)
               for c in ("green", "brown") + (("unlabelled",) if fresh else ())]
    handles += [pyplot.Line2D([], [], ls="", marker=m, color="#666666", ms=7,
                              markeredgecolor="black", label=s)
                for s, m in SOLVENTMARK.items()]
    axes.legend(handles=handles, fontsize=7.5, loc="lower right", ncol=2, framealpha=0.95)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageCurves(pdf, rows):
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("The %d second-derivative traces themselves" % len(rows),
                    fontsize=13, fontweight="bold", y=0.975)
    for index, (title, low, high, ylim) in enumerate([
            ("all %d, 540–634 nm" % len(rows), 540, 634, (-0.030, 0.018)),
            ("the 624 band only — the numerator", 614, 634, (-0.014, 0.006)),
            ("the 568 band only — the denominator", 556, 582, (-0.014, 0.006))]):
        axes = figure.add_axes([0.13, 0.700 - index * 0.275, 0.83, 0.185])
        for row in rows:
            axes.plot(GRID, row["d2"], "-", color=row["color"], lw=0.7, alpha=0.75)
        axes.axhline(0.0, color="#444444", lw=0.8)
        axes.axvspan(*RED_WINDOW, color="#cc6666", alpha=0.28, lw=0)
        axes.axvspan(*Q_WINDOW, color="#99cc66", alpha=0.28, lw=0)
        for lo, hi in ((577, 582), (605, 613)):
            if hi > low and lo < high:
                axes.axvspan(lo, hi, color="#999999", alpha=0.32, lw=0)
        axes.set_xlim(low, high)
        axes.set_ylim(*ylim)
        axes.set_ylabel("d²A / dλ²", fontsize=9)
        axes.grid(alpha=0.25)
        axes.tick_params(labelsize=8)
        if index == 2:
            axes.set_xlabel("wavelength (nm)", fontsize=9)
        figure.text(0.13, 0.915 - index * 0.275, "%d  ·  %s" % (index + 1, title),
                    fontsize=10.5, fontweight="bold")
    figure.text(0.13, 0.095,
                "[!]  Grey = INSTRUMENT, not pigment: the 581 nm reference minimum and the 609 nm Bayer crossover.\n"
                "Both search windows are pinned clear of them. Green/brown are the archive's own labels;\n"
                "blue is a run whose eye-ranking is not recorded yet, drawn but never scored.\n"
                "SHADE within a hue = which folder the run came from, so one oil's sessions stay apart.\n"
                "[*]  Panel 3 shows why the window must be PINNED: for many traces the DEEPEST dip is the 581 artefact,\n"
                "not the 568 band \u2014 a search over 560\u2013582 would return the instrument, not the pigment.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


RV_CUT = 52.0


def dateTag(session):
    """`20260822Lugitsch` -> `08-22`. The folder name is the only date this archive carries.

    ⛔ This is the DAY, so a second folder on the same date collapses into it -- 20260826LugitschB is
    another fill of the same evening, not another evening. Use `folderTag` where the FOLDER must be
    told apart, e.g. labelling sub-clusters of one oil."""
    return "%s-%s" % (session[4:6], session[6:8]) if session[:8].isdigit() else session[:5]


def folderTag(session):
    """The day plus the folder's trailing capital, so two fills of one evening label distinctly."""
    suffix = session[-1] if (session[-1].isupper() and session[-2:-1].islower()) else ""
    return dateTag(session) + suffix


def eyeOrderNote(rows):
    """⭐⭐ THE TEST THAT MATTERS ONCE EVERYTHING IS GREEN. Edwin's eye, 2026-08-27: Lugitsch greenest,
    Esterer and Stekko a little browner but GREEN. Green-vs-brown is easy here — all three clear T = 52 by
    twenty or more. Whether the metric reproduces the ORDER WITHIN green is not.

    ⛔⛔ AND THE MEANS AGREEING IS THE WEAK CLAIM. By late 2026-08-26 the Esterer fills span 30 Rv and the
    best of them (107.4) is indistinguishable from Lugitsch's best (107.2) — so an oil's MEAN can sit in
    the right place while a SINGLE FILL of it cannot be told from the other oil at all. A verdict is read
    off ONE fill, so the fill ranges are what this reports, not only the ordering of the averages.
    ⚠ Fills whose oil attribution is unconfirmed are left out of both."""
    order = []
    for oil in ("Lugitsch", "Esterer", "Stekko"):
        values = [r["Rv"] for r in rows if r["oil"] == oil and r["solvent"] == "sunflower"
                  and not r.get("provisionalOil")]
        if values:
            order.append((oil, numpy.mean(values), min(values), max(values)))
    if len(order) < 2:
        return "no eye-ranked sunflower oils on this page"
    ranked = " > ".join("%s %.0f" % (oil, mean) for oil, mean, _, _ in order)
    same = all(order[i][1] > order[i + 1][1] for i in range(len(order) - 1))
    overlap = ["%s/%s" % (order[i][0], order[i + 1][0])
               for i in range(len(order) - 1) if order[i][2] <= order[i + 1][3]]
    return ("EYE 2026-08-27: Lugitsch greenest, Esterer and Stekko a little browner \u2014 all three GREEN.\n"
            "     Rv MEANS give %s%s\n"
            "     [!] SINGLE FILLS: %s"
            % (ranked, "   \u2713 same order." if same else "   \u2717 DIFFERENT ORDER.",
               ("run ranges OVERLAP for %s \u2014 one fill cannot tell those oils apart"
                % ", ".join(overlap)) if overlap
               else "each oil's runs stay clear of the next oil's."))


def setAsideNote():
    """The hand exclusions, listed by FILL rather than by file, and what removing them cost.

    ⛔⛔ AN EXCLUSION MUST CARRY ITS PRICE ON THE SAME PAGE AS THE NUMBER IT IMPROVES. Setting a fill
    aside after seeing its value is the most dangerous edit in this pipeline; printing σ_fill both ways
    is what stops it being a quiet one."""
    if not EXCLUDED:
        return ""
    # ⛔ WRAPPED, not joined into one line. Seven excluded sessions ran off the right edge and the last
    # ones were clipped mid-word -- on the page whose stated policy is that an exclusion stays visible.
    sessions = "; ".join(sorted({relative.split("/")[0] for relative in EXCLUDED}))
    line = "\nSET ASIDE BY HAND, not plotted: " + "\n     ".join(
        textwrap.wrap(sessions, width=88))
    # ⭐ A session set aside for its SOLVENT gets its OWN LINE. On a page whose whole question is what
    # the metric does within one solvent, "excluded" and "excluded because it is a different solvent"
    # are not the same statement — and ⛔ this cannot ride on the line above, which is already long
    # enough to be clipped at the figure edge.
    for session, solvent in sorted(OTHER_SOLVENT.items()):
        line += "\n     %s is %s, a DIFFERENT SOLVENT \u2014 not a \u03c3_fill term." % (session, solvent)
    if OTHER_REFERENCE:
        line += ("\n     %s use a SAME-JAR REFERENCE \u2014 a different measurement, not a \u03c3_fill term."
                 % ", ".join(sorted(OTHER_REFERENCE)))
    for oil, (n1, s1, n2, s2) in sorted(EXCLUSION_COST.items()):
        line += ("\n     COST: %s \u03c3_fill %.1f over the %d fills kept \u2014 %.1f over %d with "
                 "the set-aside fill back in." % (oil, s1, n1, s2, n2))
    return line


def prepNote(rows):
    """⚠ Name any fill on the page whose PREPARATION differs from the header's claim.

    ⛔ The report header carries one hardcoded recipe string, so a bench change is invisible in the
    record. A mixed-preparation fill set that does not say so is an unexplained σ_fill waiting to
    happen -- this makes the mixture visible on the figure itself, not only in the console."""
    named = sorted(s for s in PREP_PROTOCOL if any(sessionOf(r) == s for r in rows))
    if not named:
        return ""
    return "\nDIFFERENT PREPARATION, plotted and scored:\n" + "\n".join(
        "     %s \u2014 %s" % (s, PREP_PROTOCOL[s].split(" (header")[0]) for s in named)


def pageSunflower(pdf, rows):
    """Rv, sunflower only, the two views STACKED one per row down an A4 portrait.

    ⭐ Its own page because sunflower is now the chosen solvent, and because the question that keeps
    coming up -- does one oil hold still across folders? -- is invisible on the three-solvent page,
    where each oil is a single undifferentiated column."""
    rows = [r for r in rows if r["solvent"] == "sunflower"]
    oils = sorted({r["oil"] for r in rows},
                  key=lambda o: -numpy.mean([r["Rv"] for r in rows if r["oil"] == o]))
    ceiling = max(r["Rv"] for r in rows) * 1.12
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Rv in sunflower oil only — split by the folder each run came from",
                    fontsize=13, fontweight="bold", y=0.975)
    figure.text(0.5, 0.934,
                "Rv = 100·(A624 − A_valley) / (A_Q − A_valley).   Colour = folder, within the class hue.\n"
                "Red dashed = the provisional cut, Rv 52 — FITTED, not pre-registered.",
                ha="center", fontsize=8.2, style="italic", linespacing=1.5)

    # ---- row 1: by oil, folders as contiguous sub-clusters
    axes = figure.add_axes([0.105, 0.585, 0.865, 0.305])
    for index, oil in enumerate(oils):
        sessions = sorted({sessionOf(r) for r in rows if r["oil"] == oil})
        spans = numpy.linspace(-0.30, 0.30, len(sessions) + 1)
        for slot, session in enumerate(sessions):
            group = sorted((r for r in rows if r["oil"] == oil and sessionOf(r) == session),
                           key=lambda r: r["run"])
            low, high = spans[slot], spans[slot + 1]
            centres = numpy.linspace(low + 0.045, high - 0.045, len(group)) if len(group) > 1 \
                else [(low + high) / 2.0]
            for centre, row in zip(centres, group):
                axes.plot(index + centre, row["Rv"], "s", ls="", color=row["color"], ms=7,
                          markeredgecolor="black", markeredgewidth=0.4)
            if len(sessions) > 1:
                axes.annotate(folderTag(session),
                              xy=(index + (low + high) / 2.0, min(r["Rv"] for r in group)),
                              xytext=(0, -11 - 10 * (slot % 2)), textcoords="offset points",
                              ha="center", va="top",
                              fontsize=6.6, fontweight="bold", color=group[0]["color"])
    axes.axhline(RV_CUT, color="crimson", lw=1.3, ls="--")
    axes.set_xticks(range(len(oils)))
    axes.set_xticklabels([o.replace(" ", "\n") for o in oils], fontsize=8.5)
    axes.set_xlim(-0.6, len(oils) - 0.4)
    axes.set_ylim(0, ceiling)
    axes.set_ylabel("Rv", fontsize=10.5, fontweight="bold")
    axes.set_title("1  ·  by oil   ·   n=%d runs, %d folders"
                   % (len(rows), len({sessionOf(r) for r in rows})),
                   fontsize=10.5, fontweight="bold", loc="left")
    axes.grid(axis="y", alpha=0.3)
    axes.tick_params(labelsize=8)

    # ---- row 2: the same numbers against the calendar
    axes = figure.add_axes([0.105, 0.290, 0.865, 0.230])
    dates = sorted({dateTag(sessionOf(r)) for r in rows})
    slot = {date: index for index, date in enumerate(dates)}
    tags = []
    for oil in oils:
        sessions = sorted({sessionOf(r) for r in rows if r["oil"] == oil})
        means, positions = [], []
        for session in sessions:
            group = [r for r in rows if r["oil"] == oil and sessionOf(r) == session]
            x = slot[dateTag(session)]
            offsets = numpy.linspace(-0.08, 0.08, len(group)) if len(group) > 1 else [0.0]
            for offset, row in zip(offsets, group):
                axes.plot(x + offset, row["Rv"], "s", color=row["color"], ms=5.5,
                          markeredgecolor="black", markeredgewidth=0.35)
            means.append(numpy.mean([r["Rv"] for r in group]))
            positions.append(x)
        colour = CLASSCOLOR[next(r["class"] for r in rows if r["oil"] == oil)]
        if len(positions) > 1:                       # only a repeated oil can show a trend
            axes.plot(positions, means, "-", color=colour, lw=1.6, alpha=0.85, zorder=0)
        tags.append({"oil": oil, "y": means[-1], "x": positions[-1], "color": colour,
                     "bold": len(positions) > 1})
    # ⛔ Spar Premium/S-Budget and Esterer/Stekko sit within a few Rv of each other on the SAME date,
    # so labels drawn at the point overprint. Push them apart to a readable gap and lead a line back.
    gap = ceiling * 0.052
    tags.sort(key=lambda t: t["y"])
    for index in range(1, len(tags)):
        tags[index]["ty"] = max(tags[index]["y"], tags[index - 1].get("ty", tags[index - 1]["y"]) + gap)
    for tag in tags:
        tag.setdefault("ty", tag["y"])
        axes.annotate(tag["oil"], xy=(tag["x"], tag["y"]),
                      xytext=(len(dates) - 0.86, tag["ty"]), textcoords="data",
                      fontsize=7.5, fontweight="bold" if tag["bold"] else "normal",
                      color=tag["color"], va="center", ha="left",
                      arrowprops={"arrowstyle": "-", "color": tag["color"], "lw": 0.6,
                                  "alpha": 0.55, "shrinkA": 1, "shrinkB": 3})
    axes.axhline(RV_CUT, color="crimson", lw=1.3, ls="--")
    axes.set_xticks(range(len(dates)))
    axes.set_xticklabels(dates, fontsize=8.5)
    axes.set_xlim(-0.35, len(dates) + 0.48)
    axes.set_ylim(0, ceiling)
    axes.set_ylabel("Rv", fontsize=10.5, fontweight="bold")
    axes.set_title("2  ·  against the calendar   ·   line = folder mean",
                   fontsize=10.5, fontweight="bold", loc="left")
    axes.grid(axis="y", alpha=0.3)
    axes.tick_params(labelsize=8)

    figure.text(0.105, 0.245,
                "[*]  Only Lugitsch has been measured in sunflower on more than one date, so it is the only\n"
                "oil that can show a trend at all. Every other line in row 2 is a single folder.",
                fontsize=8.2, va="top", linespacing=1.5)
    figure.text(0.105, 0.208,
                "[*]  %s\n"
                "[!]  A fill's own scatter is the yardstick for any step between fills: WITHIN a fill Rv "
                "repeats to sd ~1.2, but\n"
                "     INDEPENDENT FILLS of one oil sit 7\u201313 Rv apart \u2014 the preparation now "
                "dominates the measurement by about ten to one.%s"
                % (eyeOrderNote(rows), prepNote(rows) +
                   ("" if not EXCLUDED else
                    setAsideNote())),
                fontsize=8.2, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageByDay(pdf, rows, key="Rv", cut=RV_CUT, label="Rv",
              title="Rv in sunflower — one row per measurement day", blurb=None, caveat="",
              extraRows=None):
    """Sunflower, ONE ROW PER MEASUREMENT DAY, stacked down an A4 portrait.

    ⭐ WHY PER DAY IS THE FAIR COMPARISON. Within a single day the lamp, the reference and the rig are
    held constant, so oil-vs-oil is read with the day divided out -- which the by-oil page cannot do,
    because there every oil except Lugitsch is a single folder and oil is perfectly confounded with day.
    Lugitsch is the only oil measured on all three days, so it acts as the running reference: its dotted
    line per row is where the one repeated oil sat THAT day.

    ⛔ Stacked, not side by side, and the shared y-axis is the whole point -- rows are meant to be read
    DOWN the page against one another, which columns of differing width made harder than it needed to be.

    ⭐ PARAMETERISED over the quantity (2026-08-27) so a candidate metric gets the SAME per-day view as
    the shipped one. That is deliberate: a candidate has to be judged on the plot that divides the day
    out, because between-day drift is exactly what a fill-scatter claim can otherwise borrow its win from.
    ⚠ `key` may go negative, so the y-window is taken from the data instead of pinned at zero."""
    rows = [r for r in rows if r["solvent"] == "sunflower"]
    # ⭐ A row may declare its own group instead of taking the folder's date. That is how the settled
    # SAME-JAR fills get a row of their own beside the two-jar fills of the same night: the page's whole
    # premise is "inside one row the rig is common to every oil", and it is TRUE within each method and
    # FALSE across them. Overridden groups sort last, after every real date.
    if extraRows:
        rows = rows + [r for r in extraRows if r["solvent"] == "sunflower"]
    groupOf = lambda row: row.get("dayOverride") or dateTag(sessionOf(row))
    days = sorted({groupOf(r) for r in rows}, key=lambda d: (1, d) if "·" in d else (0, d))
    values = [r[key] for r in rows]
    # ⚠ The headroom is for the mean ± sd LABELS, which sit above the highest marker in each cluster.
    # Applied uniformly, so "same vertical scale in every row" survives.
    if min(values) >= 0.0:                    # Rv and friends: keep the zero datum, the bar is meaningful
        floor, ceiling = 0.0, max(values) * 1.20
    else:
        pad = (max(values) - min(values)) * 0.10
        floor, ceiling = min(values) - pad, max(values) + pad * 1.8
    span = ceiling - floor
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle(title, fontsize=13, fontweight="bold", y=0.975)
    # ⚠ `va="top"` so the block HANGS from a fixed line instead of growing upward into the title —
    # a three-line blurb (RvTest carries one) overlapped the heading when the anchor was a baseline.
    figure.text(0.5, 0.952,
                blurb or
                "The comparison with the day divided out. Same vertical scale in every row, so the rows\n"
                "read against each other. Bar = that oil's mean for the row; dotted = that day's Lugitsch\n"
                "mean, the one oil measured on all days.",
                ha="center", va="top", fontsize=8.2, style="italic", linespacing=1.5)

    # ⛔⛔ THE ROW GEOMETRY IS DERIVED, NOT TYPED. It used to be `0.700 - index * 0.245` with a fixed
    # height, which fitted exactly three measurement days; the fourth (2026-08-28) put its row at
    # y = -0.035 — half of it off the bottom of the page and the rest underneath the two footnote
    # blocks, which are drawn at fixed figure coordinates. ⚠ This page is rendered for the shipped
    # metric AND for every candidate, so one more day of measurements silently corrupted several pages
    # at once. Rows now share whatever band is left between the blurb and the footnotes.
    TOP, BOTTOM = 0.895, 0.215
    pitch = (TOP - BOTTOM) / len(days)
    # ⚠ 0.72, not 0.80: the gap between rows has to clear the x tick labels, which are two lines tall
    # for any oil with a space in its name ("Billa\nClever"), plus the next row's title.
    height = pitch * 0.72
    for index, day in enumerate(days):
        axes = figure.add_axes([0.105, TOP - pitch * index - height, 0.865, height])
        today = [r for r in rows if groupOf(r) == day]
        oils = sorted({r["oil"] for r in today})
        reference = [r[key] for r in today if r["oil"] == "Lugitsch"]
        for position, oil in enumerate(oils):
            group = sorted((r for r in today if r["oil"] == oil), key=lambda r: r["run"])
            offsets = numpy.linspace(-0.22, 0.22, len(group)) if len(group) > 1 else [0.0]
            for offset, row in zip(offsets, group):
                axes.plot(position + offset, row[key], "s", color=row["color"], ms=7,
                          markeredgecolor="black", markeredgewidth=0.4)
            # ⭐ THE OIL'S MEAN FOR THIS ROW, drawn as a bar over its own cluster. The page exists to be
            # read ACROSS a row, and comparing two clusters of scattered squares by eye is exactly the
            # judgement the bar removes. ⚠ Drawn UNDER the markers (zorder) and in the flat class hue,
            # not a session shade, so it reads as an annotation rather than as another run.
            values = [r[key] for r in group]
            if len(group) > 1:
                # ⚠ 0.28 against the markers' ±0.22 spread: wide enough to read as a bar, narrow enough
                # that it still belongs to its own cluster on a two-oil row, where the x-axis is short.
                axes.plot([position - 0.28, position + 0.28], [numpy.mean(values)] * 2,
                          color=CLASSCOLOR[group[0]["class"]], lw=1.8, zorder=1,
                          solid_capstyle="butt", alpha=0.85)
            # ⭐ THE NUMBER, not only the bar. A reader comparing two clusters by eye is doing arithmetic
            # the plot can do for them, and the sd is what says whether the gap between two bars means
            # anything. ⚠ Anchored above the group's HIGHEST marker, not above the bar: on a bimodal
            # cluster the mean sits between the runs and a label there lands on top of them.
            caption = ("%.1f" % values[0] if len(values) == 1
                       else "%.1f ± %.1f" % (numpy.mean(values), numpy.std(values, ddof=1)))
            # ⚠ On a white PATCH: the label has to survive landing on the crimson threshold line, on the
            # dotted Lugitsch reference and on its own caption, all of which it does on some row.
            axes.text(position, min(max(values) + span * 0.04, ceiling - span * 0.06), caption,
                      fontsize=7, color=CLASSCOLOR[group[0]["class"]], ha="center", va="bottom",
                      fontweight="bold", zorder=5,
                      bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                                edgecolor="none", alpha=0.78))
        if reference:
            axes.axhline(numpy.mean(reference), color="#2e7d32", lw=1.0, ls=":", alpha=0.85)
            axes.text(len(oils) - 0.45, numpy.mean(reference) + span * 0.015,
                      "Lugitsch %.1f" % numpy.mean(reference), fontsize=7, color="#2e7d32",
                      ha="right", va="bottom", fontweight="bold")
        axes.axhline(cut, color="crimson", lw=1.3, ls="--")
        axes.set_xticks(range(len(oils)))
        axes.set_xticklabels([o.replace(" ", "\n") for o in oils], fontsize=8)
        axes.set_xlim(-0.6, len(oils) - 0.4)
        axes.set_ylim(floor, ceiling)
        axes.grid(axis="y", alpha=0.3)
        axes.tick_params(labelsize=8)
        axes.set_ylabel(label, fontsize=10, fontweight="bold")
        axes.set_title("%s   ·   %d runs, %d oils" % (day, len(today), len(oils)),
                       fontsize=10.5, fontweight="bold", loc="left")

    walk = " → ".join("%.1f" % numpy.mean([r[key] for r in rows
                                                if r["oil"] == "Lugitsch" and groupOf(r) == day])
                           for day in days
                           if any(r["oil"] == "Lugitsch" and groupOf(r) == day for r in rows))
    # ⚠ Anchored to BOTTOM, so the footnotes follow the rows instead of being overrun by them.
    figure.text(0.105, BOTTOM - 0.025,
                "[*]  Read ACROSS a row, not down the page: inside one day the rig is common to every oil,\n"
                "so the gaps within a row are the ones that mean something.",
                fontsize=8.2, va="top", linespacing=1.5)
    figure.text(0.105, BOTTOM - 0.075,
                "[!]  08-22 carries only two oils and 08-24 never saw Esterer or Stekko, so no single row\n"
                "ranks all six. Lugitsch's own line moves %s across the rows: the reference itself\n"
                "is not fixed, which is why an oil measured on one day only cannot be placed against one\n"
                "measured on another.%s%s"
                # ⛔ SESSIONS, NOT FULL PATHS. Joining the six excluded FILENAMES ran off the right
                # edge of the figure and was clipped mid-word, so the last exclusion in the list was
                # invisible on the very page whose policy is that an exclusion must stay visible.
                # The per-file reasons are announced on the console and live in `EXCLUDED`.
                # ⛔ WRAPPED. Sessions, not full paths (they ran off the edge), and now wrapped too:
                # at seven excluded sessions even the short names clip mid-word, on the page whose
                # stated policy is that an exclusion has to stay visible.
                # ⛔ "not plotted" HAS TO MEAN not plotted ON THIS PAGE. The settled same-jar fills are
                # in EXCLUDED — correctly, they touch no statistic — but they DO appear here, in their
                # own row. Listing them as absent while they are drawn above is worse than listing
                # nothing: it teaches the reader that the caption cannot be trusted.
                % (walk, caveat, "" if not EXCLUDED else
                   "\nSET ASIDE BY HAND, not plotted: "
                   + "\n     ".join(textwrap.wrap(
                       "; ".join(sorted({relative.split("/")[0] for relative in EXCLUDED}
                                        - {sessionOf(r) for r in (extraRows or [])})),
                       width=88))
                   + ("" if not extraRows else
                      "\n%s is drawn in its own row: same jar for reference AND sample, so it may be "
                      "read\n     ACROSS that row but NOT against the two-jar rows above."
                      % SAME_JAR_ROW)),
                fontsize=8.2, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageBySolvent(pdf, rows):
    """One panel per solvent, oils side by side. ⭐ Lugitsch and Billa Clever appear in ALL THREE, so
    the same oil can be read straight across the row -- which is the only way to see whether a metric
    is reporting the OIL or the SOLVENT."""
    solvents = [("isopropanol", "isopropanol  (the shipping recipe)"),
                ("sunflower", "sunflower  (index-matched, food-safe)"),
                ("spirit", "de-aromatised white spirit")]
    figure = pyplot.figure(figsize=(11.69, 8.27))
    figure.suptitle("Every oil, grouped by solvent — is the metric reporting the OIL or the SOLVENT?",
                    fontsize=13.5, fontweight="bold", y=0.965)
    metricRows = [("d2R", "d2R = D2(624) / D2(568)", CUT, (0.0, 4.7)),
                  ("Rv", "Rv = 100·(A624−A_valley)/(A_Q−A_valley)", 52.0, (0, 140))]
    counts = {name: sorted({r["oil"] for r in rows if r["solvent"] == name}) for name, _ in solvents}
    widths = [max(1.4, len(counts[name])) for name, _ in solvents]
    left = 0.065
    total = sum(widths)
    for column, (name, title) in enumerate(solvents):
        oils = counts[name]
        width = 0.86 * widths[column] / total
        for line, (key, label, cut, ylim) in enumerate(metricRows):
            axes = figure.add_axes([left, 0.575 - line * 0.375, width, 0.290])
            for index, oil in enumerate(oils):
                # ⭐ Sorted by SESSION, not left as found: that makes each folder a contiguous
                # sub-cluster, so session scatter is read straight off the horizontal grouping.
                group = sorted((r for r in rows if r["solvent"] == name and r["oil"] == oil),
                               key=lambda r: (sessionOf(r), r["run"]))
                offsets = (numpy.linspace(-0.24, 0.24, len(group)) if len(group) > 1 else [0.0])
                for offset, row in zip(offsets, group):
                    axes.plot(index + offset, row[key], SOLVENTMARK[name], ls="",
                              color=row["color"], ms=6,
                              markeredgecolor="black", markeredgewidth=0.4)
            axes.axhline(cut, color="crimson", lw=1.3, ls="--")
            axes.set_xticks(range(len(oils)))
            axes.set_xticklabels([o.replace(" ", "\n") for o in oils], fontsize=7.5)
            axes.set_xlim(-0.6, len(oils) - 0.4)
            axes.set_ylim(*ylim)
            axes.grid(axis="y", alpha=0.3)
            axes.tick_params(labelsize=7.5)
            if column == 0:
                axes.set_ylabel(label, fontsize=9, fontweight="bold")
            else:
                axes.set_yticklabels([])
            if line == 0:
                axes.set_title("%s   n=%d" % (title, sum(1 for r in rows if r["solvent"] == name)),
                               fontsize=9.5, fontweight="bold")
        left += width + 0.022
    figure.text(0.065, 0.145,
                "[*]  Lugitsch (green) and Billa Clever (brown) appear in ALL THREE solvents \u2014 read them straight across.\n"
                "Both metrics keep every oil on the same side of the line in every solvent. That is the property Q% does NOT have:\n"
                "the same Lugitsch oil reads Q% 13.5\u201315.5 in isopropanol and 20.6\u201320.8 in white spirit.",
                fontsize=8.2, va="top", linespacing=1.5)
    figure.text(0.065, 0.082,
                "[!]  %d runs, not the ~98 labelled ones \u2014 only traces reaching 632 nm can carry a 2nd derivative at 624.\n"
                "Red dashed = the provisional cut (d2R 1.00, Rv 52). Both are FITTED; neither is pre-registered.%s"
                % (len(rows),
                   "" if not [r for r in rows if r["class"] == "unlabelled"] else
                   "\nBlue = %s: measured, plotted, but held OUT of every cut until its eye-ranking is recorded."
                   % ", ".join(sorted({r["oil"] for r in rows if r["class"] == "unlabelled"}))),
                fontsize=8.2, color="#a03000", va="top", linespacing=1.5)
    handles = sessionHandles(rows)
    if handles:
        figure.legend(handles=handles, fontsize=6.4, loc="lower right",
                      bbox_to_anchor=(0.995, 0.012), ncol=2, framealpha=0.95,
                      title="shade = folder (only oils spanning several)", title_fontsize=7,
                      handletextpad=0.4, columnspacing=0.9, labelspacing=0.32)
    pdf.savefig(figure)
    pyplot.close(figure)


RV_REF_OLD = (565.0, 580.0)
RV_REF_NEW = (556.0, 566.0)
RV_T_OLD = 52.0
RV_T_NEW = 119.6


def addMetrics(row):
    """Every metric this file plots, computed onto one row. ⛔ SHARED, not duplicated: the same-jar
    corpus (`sameJarCorpus`) needs identical arithmetic, and two copies of a metric definition is how
    two pages of the same PDF end up disagreeing about what `RvLin` means."""
    if True:
        for tag, (low, high) in (("rvOld", RV_REF_OLD), ("rvNew", RV_REF_NEW)):
            valley = float(row["a"][(row["nm"] >= 500.0) & (row["nm"] <= 560.0)].mean())
            red = float(row["a"][(row["nm"] >= 622.0) & (row["nm"] <= 627.0)].mean())
            reference = float(row["a"][(row["nm"] >= low) & (row["nm"] <= high)].mean())
            row[tag] = 100.0 * (red - valley) / (reference - valley)
        # ⭐ `RV_REF_OLD` is (565, 580), so `rvOld` IS the shipped `Rv` -- give it that name too, because
        # the d2R corpus builds `Rv` in `take()` and the same-jar corpus does not go through `take()`.
        # ⛔ Without this the shipped per-day page silently drops the same-jar row while every candidate
        # page shows it, which is exactly the inconsistency it took a rendered page to notice.
        row["Rv"] = row["rvOld"]
        # ⭐⭐ THE DIFFERENCE METRIC (Edwin's question, 2026-08-27): should A_Soret be used as well?
        # ⛔ NOT as the reference — that is Q%'s anchor and it is the WORST of every candidate tried
        # (11 errors against Rv's 1; the Soret is carotenoid-contaminated, so it mixes pigment families).
        # ⭐ But as a CORRECTION it earns its place: Rv and Q% correlate at r = -0.64 over the archive, so
        # they are two readings of one axis; subtracting cancels what they share and keeps what they
        # disagree about. The archive's own rule: "differences survive, ratios don't."
        soret = float(row["a"][(row["nm"] >= 448.0) & (row["nm"] <= 460.0)].mean())
        qBand = float(row["a"][(row["nm"] >= 565.0) & (row["nm"] <= 580.0)].mean())
        row["qPct"] = 100.0 * (qBand - valley) / (soret - valley)
        row["rvMinusQ"] = row["rvOld"] - row["qPct"]
        # ⭐⭐ `RvTest` (Edwin, 2026-08-29, from the screenshot of two 08-28 fills): the 500-560 valley
        # is 70 nm from the band it is being asked to baseline, and over 37 sunflower runs the depth of
        # the 600-620 trough BELOW that valley tracks Rv at r = -0.89/-0.84/-0.94 (Esterer/Lugitsch/
        # Stekko) — the same sign in every oil. So give the red band its own local anchor and keep the
        # Q band on the valley. ⚠ 612-615 is the archive's own P2 anchor and the earliest usable one:
        # the 609 nm Bayer crossover reads 1.6-2.2x the 613 nm value in every run on disk.
        # ⛔ CHOSEN AFTER SEEING THE EFFECT, so it is a candidate and nothing more —
        # `diagnostics/red_anchor_ab.py` scores it over all three solvents and finds the trade: it fixes
        # isopropanol (corridor -11.5 -> +4.8, errors 1 -> 0) and loses the property Rv was chosen for
        # (one shared cut across solvents: 1 error becomes 4).
        localAnchor = float(row["a"][(row["nm"] >= 612.0) & (row["nm"] <= 615.0)].mean())
        row["rvTest"] = 100.0 * (red - localAnchor) / (qBand - valley)
        # ⭐⭐ `RvCont` (Edwin, 2026-08-29: "something more advanced" than swapping one anchor for
        # another). ONE least-squares line over EVERY pigment-free window -- §14.2's own 472-500 +
        # 505-555 + 588-604 -- subtracted from the whole spectrum, then both bands measured above it.
        # `A_valley` does not appear as a term because 505-555 is INSIDE the fit: after subtraction the
        # valley sits at ~0 by construction. ⭐ It is the only member of the family with no mismatched
        # lever arms, and it is exactly invariant to level AND tilt (§16.2's measured table).
        # ⛔ IT DOES NOT BEAT `Rv`. Fitted on all 124 labelled runs it scores 0 errors with a +5.1
        # corridor against Rv's 1 and -11.5 -- but §16.3a's HOLD-OUT reverses that: a cut fitted on
        # isopropanol and carried across gives Rv 0/36 and RvCont 1/36, the other way 5/88 against 8/88.
        # Its per-solvent cut spread is 16.7 against Rv's 6.8. ⚠ §16.3c then reverses it back INSIDE
        # sunflower. Nothing is adopted; this page exists so the candidate is visible, not preferred.
        # ⭐⭐ `RvLin` — the TWO-POINT line through (530, Av) and (613.5, Aloc), applied to BOTH bands.
        # It is the only member that is affine-invariant AND short-lever: it removes a baseline tilt
        # without RvCont's 20.5 nm extrapolation past its fit. ⇒ it never came within 16.3 of a sign
        # change over 132 runs where RvCont reached 1.0 (SPEC_metric_research.md §16.7c).
        # ⭐ On the 2026-08-29 fills it is the best of the four on gap-divided-by-worst-replicate-scatter
        # (7.17 against RvTest 6.33, RvCont 3.53, Rv 1.56) — §16.9. ⛔ It LOSES the archive-wide hold-out
        # (6/36 against Rv's 0/36, §16.3a), so it is a tracker candidate, not a verdict candidate.
        slope = (localAnchor - valley) / (613.5 - 530.0)
        baselineAt = lambda nanometer: valley + slope * (nanometer - 530.0)
        linDenominator = qBand - baselineAt(572.5)
        row["rvLin"] = (100.0 * (red - baselineAt(624.5)) / linDenominator
                        if linDenominator > 0 else float("nan"))
        mask = numpy.zeros_like(row["nm"], dtype=bool)
        for low, high in CONTINUUM_WINDOWS:
            mask |= (row["nm"] >= low) & (row["nm"] <= high)
        gradient, intercept = numpy.polyfit(row["nm"][mask], row["a"][mask], 1)
        corrected = row["a"] - (gradient * row["nm"] + intercept)
        correctedQ = float(corrected[(row["nm"] >= 565.0) & (row["nm"] <= 580.0)].mean())
        row["rvCont"] = (100.0 * float(corrected[(row["nm"] >= 622.0) & (row["nm"] <= 627.0)].mean())
                         / correctedQ) if correctedQ > 0 else float("nan")
        # ⛔ `reference_band_scan` builds its own rows and does not carry this flag, so without it the
        # unconfirmed fill silently counts as a fourth Esterer fill on the Rv pages while being excluded
        # everywhere else. One corpus, one rule.
        row["provisionalOil"] = row.get("session") in PROVISIONAL_ATTRIBUTION
    return row


def rvCorpus():
    """The Rv-capable corpus, which is BIGGER than this file's d2R corpus: Rv needs only 500-627 nm,
    where a 2nd derivative at 624 needs the far flank past 632. Imported lazily because
    `reference_band_scan` imports names from this module -- at module level it would be a cycle."""
    import reference_band_scan as scan
    return paint([addMetrics(row) for row in scan.collect()])


# ⭐⭐ THE SETTLED SAME-JAR RECIPE — same jar for reference and sample, NO ultrasonic bath, 6 minutes
# standing in the dark. `20260828EstererD` is NOT here: it had the bath and only 60 s, so it is a
# different preparation and would put two recipes on one row.
# ⛔ These fills stay in EXCLUDED, so they touch NO statistic, NO σ_fill figure and none of the by-oil,
# by-solvent or strip pages. They are read separately, ONLY for their own row on the per-day pages,
# where the premise of the page — "inside one row the rig is common to every oil" — actually holds for
# them: all four share one method, so green-vs-brown WITHIN the row is exactly the comparison the page
# is for. ⚠ What would be wrong is putting them on the two-jar row, and that is what this prevents.
SAME_JAR_ROW = "08-28 · same-jar"
SAME_JAR_6MIN = {"20260828EstererE": ("Esterer", "green"),
                 "20260828EstererF": ("Esterer", "green"),
                 "20260828BillaCleverA": ("Billa Clever", "brown"),
                 "20260828BillaCleverB": ("Billa Clever", "brown")}


def sameJarCorpus():
    """The four settled same-jar fills, read straight from disk because EXCLUDED (correctly) hides them
    from every other consumer. Same `addMetrics`, same run policy, and every row carries `dayOverride`
    so `pageByDay` can give them a row of their own."""
    import tempfile
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for session, (oil, label) in sorted(SAME_JAR_6MIN.items()):
            names = sorted(f for f in os.listdir(os.path.join(archive.ARCHIVE, session))
                           if f.endswith(".pdf"))
            for relative in ["%s/%s" % (session, name) for name in names]:
                workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
                if workflow is None:
                    continue
                trace = archive.despikedTrace(workflow)
                if trace is None or trace[0][0] > 500.0 or trace[0][-1] < 627.5:
                    continue
                rows.append(addMetrics({"run": relative, "session": session, "oil": oil,
                                        "class": label, "solvent": "sunflower",
                                        "nm": trace[0], "a": trace[1],
                                        "dayOverride": SAME_JAR_ROW}))
    return paint(rows)


def bestCut(rows, key):
    """The threshold this quantity can achieve, and the errors there. ⚠ FITTED on this corpus — it is a
    measurement of what the quantity CAN do, not a pre-registered constant (§7 / M9)."""
    scored = [r for r in rows if isScored(r)]
    green = numpy.array([r[key] for r in scored if r["class"] == "green"])
    brown = numpy.array([r[key] for r in scored if r["class"] == "brown"])
    best, cuts = None, numpy.unique(numpy.concatenate([green, brown]))
    for cut in cuts:
        errors = int((green < cut).sum() + (brown >= cut).sum())
        if best is None or errors < best[0]:
            best = (errors, cut)
    band = [c for c in cuts if int((green < c).sum() + (brown >= c).sum()) == best[0]]
    return best[0], float((min(band) + max(band)) / 2.0), green, brown


def pageRvNewStrip(pdf, rows, d2rCount):
    """Rv' by SESSION, not by run: 115 rows of text would be 2.7 pt. The runs are all still drawn."""
    sessions = sorted({sessionOf(r) for r in rows},
                      key=lambda s: -numpy.median([r["rvNew"] for r in rows if sessionOf(r) == s]))
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("REJECTED CANDIDATE \u00b7 Rv\u2032, the blue-flank reference \u2014 every run",
                    fontsize=13, fontweight="bold", y=0.975)
    figure.text(0.5, 0.937,
                "Rv\u2032 = 100\u00b7(A622\u2013627 \u2212 A_valley) / (A556\u2013566 \u2212 A_valley).  "
                "Same numerator and datum as Rv; only the REFERENCE moves.\n"
                "n = %d here against %d on the d2R pages \u2014 Rv needs no far flank, so it keeps runs a 2nd "
                "derivative at 624 cannot use." % (len(rows), d2rCount),
                ha="center", fontsize=8.2, style="italic", linespacing=1.5)
    axes = figure.add_axes([0.30, 0.058, 0.66, 0.868])
    for position, session in enumerate(sessions):
        for row in [r for r in rows if sessionOf(r) == session]:
            axes.plot(row["rvNew"], position, SOLVENTMARK[row["solvent"]], color=row["color"],
                      ms=6, markeredgecolor="black", markeredgewidth=0.4)
    axes.axvline(RV_T_NEW, color="crimson", lw=1.4, ls="--")
    axes.set_yticks(range(len(sessions)))
    axes.set_yticklabels(["%-24s" % s[:24] for s in sessions], fontsize=7, family="monospace")
    for tick, session in zip(axes.get_yticklabels(), sessions):
        tick.set_color(next(r["color"] for r in rows if sessionOf(r) == session))
    axes.set_ylim(-1, len(sessions))
    axes.invert_yaxis()
    axes.set_xlabel("Rv\u2032", fontsize=10, fontweight="bold")
    axes.grid(axis="x", alpha=0.3)
    axes.tick_params(labelsize=8)
    scored = [r for r in rows if isScored(r)]
    green = [r["rvNew"] for r in scored if r["class"] == "green"]
    brown = [r["rvNew"] for r in scored if r["class"] == "brown"]
    axes.text(RV_T_NEW + 4, len(sessions) - 1.5,
              "T = %.0f\ngreen \u2265 %.0f\nbrown \u2264 %.0f\n%d / %d errors"
              % (RV_T_NEW, min(green), max(brown),
                 sum(1 for r in scored if (r["class"] == "green") != (r["rvNew"] >= RV_T_NEW)),
                 len(scored)), fontsize=8, color="crimson", va="bottom")
    handles = [pyplot.Line2D([], [], ls="", marker="o", color=CLASSCOLOR[c], ms=7,
                             markeredgecolor="black", label="%s (shade = folder)" % c)
               for c in ("green", "brown", "unlabelled")]
    handles += [pyplot.Line2D([], [], ls="", marker=m, color="#666666", ms=7,
                              markeredgecolor="black", label=s) for s, m in SOLVENTMARK.items()]
    axes.legend(handles=handles, fontsize=7.5, loc="lower right", ncol=2, framealpha=0.95)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageRvOldNew(pdf, rows):
    """Does the new reference change any verdict, and does it hold an oil steadier across sessions?"""
    scored = [r for r in rows if isScored(r)]
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("REJECTED CANDIDATE \u00b7 Rv against Rv\u2032 \u2014 what the reference band buys",
                    fontsize=13, fontweight="bold", y=0.975)

    axes = figure.add_axes([0.115, 0.560, 0.845, 0.330])
    for row in rows:
        axes.plot(row["rvOld"], row["rvNew"], SOLVENTMARK[row["solvent"]], color=row["color"],
                  ms=6, markeredgecolor="black", markeredgewidth=0.4)
    axes.axvline(RV_T_OLD, color="crimson", lw=1.3, ls="--")
    axes.axhline(RV_T_NEW, color="crimson", lw=1.3, ls="--")
    axes.set_xlabel("Rv   (reference 565\u2013580,  T = %.0f)" % RV_T_OLD, fontsize=9.5)
    axes.set_ylabel("Rv\u2032   (reference 556\u2013566,  T = %.0f)" % RV_T_NEW, fontsize=9.5)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    green = numpy.array([[r["rvOld"], r["rvNew"]] for r in scored if r["class"] == "green"])
    brown = numpy.array([[r["rvOld"], r["rvNew"]] for r in scored if r["class"] == "brown"])
    figure.text(0.115, 0.944, "1  \u00b7  every run, both metrics", fontsize=10.5, fontweight="bold")
    figure.text(0.115, 0.931,
                "Old corridor (worst green \u2212 worst brown) %+.1f \u2014 the classes OVERLAP and T only "
                "threads the overlap.\nNew corridor %+.1f \u2014 a real gap. Errors %d \u2192 %d of %d."
                % (green[:, 0].min() - brown[:, 0].max(), green[:, 1].min() - brown[:, 1].max(),
                   sum(1 for r in scored if (r["class"] == "green") != (r["rvOld"] >= RV_T_OLD)),
                   sum(1 for r in scored if (r["class"] == "green") != (r["rvNew"] >= RV_T_NEW)),
                   len(scored)), fontsize=8.2, color="#444444", linespacing=1.5, va="top")

    axes = figure.add_axes([0.115, 0.115, 0.845, 0.330])
    repeats = {}
    for row in rows:
        repeats.setdefault((row["solvent"], row["oil"]), {}).setdefault(sessionOf(row), []).append(row)
    labels, oldDrift, newDrift = [], [], []
    for (solvent, oil), sessions in sorted(repeats.items()):
        usable = {k: v for k, v in sessions.items() if len(v) >= 2}
        if len(usable) < 2:
            continue
        for tag, store in (("rvOld", oldDrift), ("rvNew", newDrift)):
            means = numpy.array([numpy.mean([r[tag] for r in v]) for v in usable.values()])
            pooled = numpy.sqrt(numpy.mean([numpy.var([r[tag] for r in v], ddof=1)
                                            for v in usable.values()]))
            store.append((means.max() - means.min()) / pooled)
        labels.append("%s\n%s" % (oil[:13], solvent[:4]))
    positions = numpy.arange(len(labels))
    axes.bar(positions - 0.19, oldDrift, 0.36, color="#b0b0b0", edgecolor="black", lw=0.5, label="Rv")
    axes.bar(positions + 0.19, newDrift, 0.36, color="#1565c0", edgecolor="black", lw=0.5,
             label="Rv\u2032")
    axes.set_xticks(positions)
    axes.set_xticklabels(labels, fontsize=7.5)
    axes.set_ylabel("session drift  /  within-session sd", fontsize=9.5)
    axes.grid(axis="y", alpha=0.25)
    axes.tick_params(labelsize=8)
    axes.legend(fontsize=8.5, framealpha=0.95)
    figure.text(0.115, 0.485, "2  \u00b7  the same oil across sessions \u2014 lower is steadier",
                fontsize=10.5, fontweight="bold")
    figure.text(0.115, 0.469,
                "Only oils measured twice or more, with 2+ runs per session, can carry this. "
                "Mean over them: %.2f \u2192 %.2f."
                % (numpy.mean(oldDrift), numpy.mean(newDrift)),
                fontsize=8.2, color="#444444")
    figure.text(0.115, 0.072,
                "[!]  Rv\u2032 IS NOT A DECISION. Its window was chosen by sweeping this same archive, which is "
                "the fit-your-own-corpus\n"
                "problem SPEC_metric_research \u00a77's M9 gate exists to stop. It survives a datum change and "
                "wins on four independent\n"
                "measures, which makes it worth PRE-REGISTERING \u2014 not worth shipping. Its denominator is "
                "also ~4\u00d7 thinner, so it\n"
                "has less headroom on a weak fill.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageDifferenceMetric(pdf, rows):
    """`Rv − Q%′` — Edwin's "use the Soret as well", in the one form that survives testing.

    ⛔⛔ SIX ALGEBRAIC FORMS WERE TRIED AND THIS ONE WON ON THE CORPUS IT IS QUOTED AGAINST. That is the
    same setup that made the blue-flank reference look excellent on 115 runs before it failed on the first
    new sample (§12.3). It is a CANDIDATE, and the σ_fill run is the corpus it was not chosen on."""
    scored = [r for r in rows if isScored(r)]
    errorsRv, cutRv, _, _ = bestCut(rows, "rvOld")
    errorsD, cutD, greenD, brownD = bestCut(rows, "rvMinusQ")

    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("SHELVED CANDIDATE \u00b7 Rv \u2212 Q%\u2032 \u2014 A_Soret as a CORRECTION, not the reference",
                    fontsize=12.5, fontweight="bold", y=0.975)
    figure.text(0.5, 0.936,
                "Rv\u2032\u2032 = 100\u00b7[ (A624 \u2212 Av)/(A_Q \u2212 Av) \u2212 "
                "(A_Q \u2212 Av)/(A_Soret \u2212 Av) ]\n"
                "The first term IS Rv; the second IS Q%, valley-corrected. They correlate at r = \u22120.64, "
                "so the difference cancels what they share.",
                ha="center", fontsize=8.2, style="italic", linespacing=1.5)

    axes = figure.add_axes([0.115, 0.560, 0.845, 0.330])
    for row in rows:
        axes.plot(row["rvOld"], row["rvMinusQ"], SOLVENTMARK[row["solvent"]], color=row["color"],
                  ms=6, markeredgecolor="black", markeredgewidth=0.4)
    axes.axvline(cutRv, color="crimson", lw=1.3, ls="--")
    axes.axhline(cutD, color="crimson", lw=1.3, ls="--")
    axes.set_xlabel("Rv   (best cut %.0f, %d errors of %d)" % (cutRv, errorsRv, len(scored)), fontsize=9.5)
    # ⚠ the literal per-cent sign must be doubled: this string goes through the % operator
    axes.set_ylabel("Rv \u2212 Q%%\u2032   (best cut %.0f, %d errors)" % (cutD, errorsD), fontsize=9.5)
    axes.grid(alpha=0.25)
    axes.tick_params(labelsize=8)
    figure.text(0.115, 0.916, "1  \u00b7  every run, both quantities", fontsize=10.5, fontweight="bold")
    figure.text(0.115, 0.903,
                "Corridor %+.1f \u2192 %+.1f.  Nothing crosses a quadrant, so no VERDICT changes \u2014 "
                "what changes is the margin." % (min(numpy.array([r["rvOld"] for r in scored if r["class"] == "green"])) -
                    max(numpy.array([r["rvOld"] for r in scored if r["class"] == "brown"])),
                    greenD.min() - brownD.max()),
                fontsize=8.2, color="#444444", va="top")

    # ---- what it is actually FOR: the fill spread
    axes = figure.add_axes([0.115, 0.165, 0.845, 0.300])
    fills = {}
    for row in rows:
        if row["solvent"] == "sunflower" and not row.get("provisionalOil"):
            fills.setdefault(row["oil"], {}).setdefault(sessionOf(row), []).append(row)
    labels, spreadRv, spreadD = [], [], []
    for oil, sessions in sorted(fills.items()):
        if len(sessions) < 2:
            continue
        means = lambda key: numpy.array([numpy.mean([r[key] for r in v]) for v in sessions.values()])
        labels.append("%s\n%d fills" % (oil[:12], len(sessions)))
        spreadRv.append(float(means("rvOld").std(ddof=1)))
        spreadD.append(float(means("rvMinusQ").std(ddof=1)))
    positions = numpy.arange(len(labels))
    axes.bar(positions - 0.19, spreadRv, 0.36, color="#b0b0b0", edgecolor="black", lw=0.5, label="Rv")
    axes.bar(positions + 0.19, spreadD, 0.36, color="#1565c0", edgecolor="black", lw=0.5,
             label="Rv \u2212 Q%\u2032")
    axes.set_xticks(positions)
    axes.set_xticklabels(labels, fontsize=8)
    axes.set_ylabel("\u03c3_fill  (sd of the fill means)", fontsize=9.5)
    axes.grid(axis="y", alpha=0.25)
    axes.tick_params(labelsize=8)
    axes.legend(fontsize=8.5, framealpha=0.95)
    figure.text(0.115, 0.492, "2  \u00b7  the problem it was meant to solve \u2014 fill-to-fill scatter",
                fontsize=10.5, fontweight="bold")
    figure.text(0.115, 0.479,
                "Only oils with 2+ fills can carry this. Mean \u03c3_fill %.2f \u2192 %.2f."
                % (numpy.mean(spreadRv), numpy.mean(spreadD)),
                fontsize=8.2, color="#444444", va="top")

    figure.text(0.115, 0.118,
                "[!]  SHELVED 2026-08-27 \u2014 Edwin: \u201cdoes not change the problem\u201d. "
                "Kept rendered as the record (SPEC_red_ratio_metric \u00a712.7).\n"
                "[!]  A CANDIDATE, NOT A DECISION. Six algebraic forms were tried; this one won ON THE "
                "CORPUS IT IS QUOTED AGAINST \u2014 the\n"
                "same setup that made the blue-flank reference look excellent on 115 runs before it failed "
                "on the first new sample.\n"
                "[!]  It cannot fix what actually blocks the programme. Esterer fills B and D differ by "
                "9 % in A624 with A_Q identical to\n"
                "0.03 % \u2014 no Soret term touches that, because it is the measured band itself, not a "
                "dose or normalisation error.\n"
                "[!]  And it costs Rv's best property: Rv IS the height of the 624 band on the "
                "Rv-native plot.\n"
                "A difference of two ratios cannot be drawn at all.",
                fontsize=8, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def dayDriftNote(rows):
    """⭐⭐ THE PER-DAY VIEW'S OWN VERDICT ON THE CANDIDATE, in units the two metrics share.

    Rv - Q%' has a slightly WIDER scale than Rv (slope 1.08), so no absolute spread can be compared
    between them directly. Everything here is divided by that metric's own green-brown gap, which makes
    the comparison scale-free: how much of the distance it has to work with does the drift eat?"""
    sunflower = [r for r in rows if r["solvent"] == "sunflower"]
    scored = [r for r in rows if isScored(r)]
    parts = []
    for key, name in (("rvOld", "Rv"), ("rvMinusQ", "Rv \u2212 Q%\u2032")):
        days = sorted({dateTag(sessionOf(r)) for r in sunflower
                       if r["oil"] == "Lugitsch"})
        walk = [numpy.mean([r[key] for r in sunflower
                            if r["oil"] == "Lugitsch" and dateTag(sessionOf(r)) == d]) for d in days]
        gap = (numpy.mean([r[key] for r in scored if r["class"] == "green"])
               - numpy.mean([r[key] for r in scored if r["class"] == "brown"]))
        parts.append("%s %.2f" % (name, (max(walk) - min(walk)) / gap))
    return ("\nSHELVED 2026-08-27 \u2014 Edwin: \u201cdoes not change the problem\u201d; "
            "SPEC_red_ratio_metric \u00a712.7.\n"
            "DIVIDED BY ITS OWN GREEN\u2013BROWN GAP the one repeated oil drifts across the days by "
            "%s \u2014 essentially\nUNCHANGED. The candidate's pooled \u03c3_fill win does not reach "
            "the day-to-day drift, and Esterer still overlaps\nLugitsch inside 08-26 on both. It is a "
            "CANDIDATE chosen on this same archive; read the rows, not the pooled number."
            % ", ".join(parts))


EXCLUSION_COST = {}      # oil -> (kept fills, sigma, fills with the set-aside, sigma)


def exclusionCost(rv):
    """⭐⭐ WHAT THE HAND EXCLUSIONS COST, recomputed every run rather than remembered.

    ⛔ A fill removed after its value was seen is the most dangerous edit in this whole pipeline, and the
    only defence is that its price stays visible. This re-reads the excluded reports -- they are two
    files, so it is cheap -- and prints each affected oil's σ_fill both ways.

    ⛔⛔ ONLY EXCLUSIONS THAT ARE CANDIDATE MEMBERS OF THE SAME POPULATION MAY BE PRICED HERE. σ_fill is
    the scatter of one oil in ONE SOLVENT; a fill set aside because it is a DIFFERENT SOLVENT is not a
    σ_fill contributor, and folding it in would report a solvent difference as fill noise -- inflating the
    "cost" of every other exclusion on the same line. `OTHER_SOLVENT` names those, and they are announced
    separately so the exclusion still stays visible."""
    import tempfile
    import peak_ratio_archive as archive
    extra = {}
    with tempfile.TemporaryDirectory() as scratch:
        for relative in sorted(EXCLUDED):
            session = relative.split("/")[0]
            if session not in TODAY or session in OTHER_SOLVENT or session in OTHER_REFERENCE:
                continue
            workflow = archive.workflowOf(os.path.join(archive.ARCHIVE, relative), scratch)
            if workflow is None:
                continue
            trace = archive.despikedTrace(workflow)
            if trace is None:
                continue
            nm, absorbance = trace
            if nm[0] > 500.0 or nm[-1] < 627.5:
                continue
            band = lambda lo, hi: float(absorbance[(nm >= lo) & (nm <= hi)].mean())
            valley = band(500.0, 560.0)
            extra.setdefault(TODAY[session][0], {}).setdefault(session, []).append(
                100.0 * (band(622.0, 627.0) - valley) / (band(565.0, 580.0) - valley))
    # ⛔ ONLY A FILL SET ASIDE WHOLE COUNTS HERE. A single excluded RUN (a failed save, a spoiled test
    # capture) leaves its fill standing with its other reads, so adding that run back as if it were an
    # extra fill would invent a fill that never existed and overstate the cost several times over.
    if not extra:
        return
    print("\n=== WHAT THE HAND EXCLUSIONS COST  (sigma_fill over sunflower fill means)")
    for oil, sessions in sorted(extra.items()):
        kept = {}
        for row in rv:
            if row["oil"] == oil and row["solvent"] == "sunflower" and not row.get("provisionalOil"):
                kept.setdefault(sessionOf(row), []).append(row["rvOld"])
        whole = {s: v for s, v in sessions.items() if s not in kept}
        if not whole:
            continue
        without = [numpy.mean(v) for v in kept.values()]
        with_ = without + [numpy.mean(v) for v in whole.values()]
        if len(without) < 2:
            continue
        print("  %-10s %d fills kept  sigma %.2f   |   %d fills with the set-aside  sigma %.2f"
              % (oil, len(without), numpy.std(without, ddof=1), len(with_),
                 numpy.std(with_, ddof=1)))
        print("             set aside: %s" % ", ".join(
            "%s %.1f" % (s, numpy.mean(v)) for s, v in sorted(whole.items())))
        EXCLUSION_COST[oil] = (len(without), numpy.std(without, ddof=1),
                               len(with_), numpy.std(with_, ddof=1))


def main():
    rows = paint(collect())
    green = [r["d2R"] for r in rows if isScored(r) and r["class"] == "green"]
    brown = [r["d2R"] for r in rows if isScored(r) and r["class"] == "brown"]
    print("collected %d runs: %d green, %d brown, %d unlabelled"
          % (len(rows), len(green), len(brown), sum(1 for r in rows if r["class"] == "unlabelled")))
    print("  green [%.3f .. %.3f]   brown [%.3f .. %.3f]   gap %+.3f"
          % (min(green), max(green), min(brown), max(brown), min(green) - max(brown)))
    for oil in sorted({r["oil"] for r in rows if r.get("provisionalOil")}):
        values = [r for r in rows if r.get("provisionalOil")]
        print("  %-14s UNSCORED  d2R [%.3f .. %.3f]  Rv [%.1f .. %.1f]  -> reads %s on both"
              % (oil, min(r["d2R"] for r in values), max(r["d2R"] for r in values),
                 min(r["Rv"] for r in values), max(r["Rv"] for r in values),
                 "GREEN" if min(r["d2R"] for r in values) > CUT and min(r["Rv"] for r in values) > 52.0
                 else "BROWN" if max(r["d2R"] for r in values) < CUT else "SPLIT"))
    print("\n=== WHY THE WINDOWS ARE PINNED -- how often a naive 560-582 search returns the 581 artefact")
    for solvent in ("isopropanol", "sunflower", "spirit"):
        group = [r for r in rows if r["solvent"] == solvent]
        inside = (GRID >= 560.0) & (GRID <= 582.0)
        hits = sum(1 for r in group if GRID[inside][r["d2"][inside].argmin()] > 576.0)
        print("  %-12s %2d of %2d" % (solvent, hits, len(group)))

    # ⛔ the corpus and the cost of the hand exclusions are computed BEFORE anything is drawn: the
    # sunflower page prints that cost, so it has to exist by the time the page is rendered.
    rv = rvCorpus()
    # ⛔ Read SEPARATELY and never merged into `rows` or `rv`: the same-jar fills must reach the per-day
    # pages and NOTHING else. Every statistic on every other page is computed from corpora that cannot
    # see them, which is what `EXCLUDED` is for and why they stay in it.
    sameJar = sameJarCorpus()
    exclusionCost(rv)
    with PdfPages(OUT) as pdf:
        pageStrip(pdf, rows)
        pageCurves(pdf, rows)
        pageBySolvent(pdf, rows)
        pageSunflower(pdf, rows)
        pageByDay(pdf, rows, extraRows=sameJar)
        # ⭐ ORDER IS EDITORIAL: the LIVE metric first, every SHELVED candidate behind it. A rejected
        # candidate sitting between the pages that get read is how a refuted number gets quoted.
        # ⚠ `RvTest` sits at the FRONT of the candidates because it is the only OPEN one — the two
        # behind it are shelved and rejected respectively. It is still behind the shipped metric.
        pageByDay(pdf, rv, key="rvTest", cut=bestCut(rv, "rvTest")[1], extraRows=sameJar,
                  label="RvTest",
                  title="OPEN CANDIDATE · RvTest in sunflower, one row per measurement day",
                  blurb="RvTest = 100·(A622-627 − A612-615) / (A_Q − Av)  —  Rv with the RED band on "
                        "its OWN local anchor\ninstead of a valley 70 nm away. Same layout as the Rv "
                        "page, so the two read against each other.\n"
                        "Bar = that oil's mean for the row.   Red dashed = the cut FITTED on this "
                        "archive, not a pre-registered constant.",
                  caveat="\nWHAT IT BUYS AND WHAT IT COSTS (diagnostics/red_anchor_ab.py, 124 labelled "
                         "runs, three solvents):\nISOPROPANOL, the 88-run corpus M9 would be registered "
                         "on — corridor -11.5 (overlapping) becomes +4.8,\nerrors 1 -> 0, and the one "
                         "run Rv misclassifies (20270729B/002, green, Rv 39.5) reads 65.5. Cohen's d "
                         "2.54 -> 4.07.\nBUT ONE SHARED CUT ACROSS ALL THREE SOLVENTS gives 4 errors "
                         "against Rv's 1: the per-solvent cuts run\n44.4 / 65.5 (IPA / sunflower) "
                         "against Rv's 52.5 / 59.3. Rv's threshold transfers; RvTest's does not, and "
                         "that\nportability is the property Rv was chosen for on 2026-08-25.")
        # ⭐ RvCont gets the SAME per-day view. It is the only candidate measured entirely above ONE
        # fitted line, so its page is the one to read against the Rv page when asking whether a
        # difference between two fills is the oil or the baseline.
        pageByDay(pdf, rv, key="rvCont", cut=bestCut(rv, "rvCont")[1], extraRows=sameJar,
                  label="RvCont",
                  title="OPEN CANDIDATE · RvCont in sunflower, one row per measurement day",
                  blurb="RvCont = 100 · A′(622-627) / A′(565-580),  where A′ is the spectrum MINUS a "
                        "least-squares line\nfitted over the pigment-free windows 472-500 + 505-555 + "
                        "588-604 nm. Both bands above ONE continuum.\n"
                        "Bar = that oil's mean for the row.   Red dashed = the cut FITTED on this "
                        "archive, not a pre-registered constant.",
                  caveat="\nEXACTLY INVARIANT TO LEVEL AND TILT (measured): +0.10 A flat, or a tilt of "
                         "±0.02 A/100 nm, leaves it\nunmoved to three figures where Rv moves ±5.1 and "
                         "RvTest ∓1.5. No mismatched lever arms.\n"
                         "AND IT STILL DOES NOT BEAT Rv: fitted on all 124 runs it scores 0 errors / "
                         "+5.1 corridor against\nRv's 1 / −11.5, but a HOLD-OUT reverses it — a cut "
                         "carried from isopropanol gives Rv 0/36, RvCont 1/36.\nNothing is adopted. "
                         "SPEC_metric_research §16; diagnostics/red_anchor_ab.py reproduces every number.")
        # ⭐ RvLin last of the three open candidates, and NOT because it is least: on the 2026-08-29
        # fills it is the best of the four (§16.9). It is ordered here because it is the newest.
        pageByDay(pdf, rv, key="rvLin", cut=bestCut(rv, "rvLin")[1], extraRows=sameJar,
                  label="RvLin",
                  title="OPEN CANDIDATE · RvLin in sunflower, one row per measurement day",
                  blurb="RvLin = 100 · (A624 − B(624.5)) / (A_Q − B(572.5)),  B = the straight line "
                        "through (530, Av) and (613.5, A612-615).\nBoth bands above the SAME two-point "
                        "line — affine-invariant like RvCont, but with an 11 nm lever instead of 20.5.\n"
                        "Bar = that oil's mean for the row.   Red dashed = the cut FITTED on this "
                        "archive, not a pre-registered constant.",
                  caveat="\nBEST OF THE FOUR ON THE 2026-08-29 FILLS, on gap ÷ worst-case replicate "
                         "scatter: 7.17 against RvTest 6.33,\nRvCont 3.53, Rv 1.56 — and the only one "
                         "with no bad pair (3.60 / 6.28 / 4.02), where Rv and RvCont\nboth blow up on "
                         "the BROWN pair (36.3 and 22.8). Never within 16.3 of a sign change over 132 "
                         "runs.\nBUT IT LOSES THE ARCHIVE-WIDE HOLD-OUT, 6/36 against Rv's 0/36 ⇒ a "
                         "HISTORY TRACKER candidate, not a verdict one. §16.9.")
        pageDifferenceMetric(pdf, rv)
        # ⭐ the candidate gets the SAME per-day view as the shipped metric, on its own fitted cut --
        # the plot that divides the day out is where a fill-scatter claim has to hold up.
        pageByDay(pdf, rv, key="rvMinusQ", cut=bestCut(rv, "rvMinusQ")[1],
                  label="Rv − Q%′",
                  title="SHELVED CANDIDATE · Rv − Q%′ in sunflower, one row per day",
                  blurb="Rv′′ = 100·[ (A624 − Av)/(A_Q − Av) − "
                        "(A_Q − Av)/(A_Soret − Av) ].   Same layout as the Rv page, so the two "
                        "read against each other.\n"
                        "Red dashed = the cut FITTED on this archive, not a pre-registered constant.",
                  caveat=dayDriftNote(rv))
        pageRvNewStrip(pdf, rv, len(rows))
        pageRvOldNew(pdf, rv)
        pdf.infodict()["Title"] = "d2R over every archived run reaching 632 nm"
    print("wrote", OUT)


if __name__ == "__main__":
    main()
