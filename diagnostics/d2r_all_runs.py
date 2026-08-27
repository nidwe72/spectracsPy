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
         "20260826EstererD": ("Esterer", "green")}

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
LATE_RUN_SESSIONS = "20260826"
KEPT_RUN_COUNT = 2

# ⛔ HAND-EXCLUDED RUNS. Not deleted, not silently skipped: named here with a reason, announced on
# every run, and printed on the figure. A run dropped by judgement has to stay visible or the corpus
# quietly becomes whatever was convenient. Edwin's call, 2026-08-26, to be revisited.
EXCLUDED = {"20260826Lugitsch/004.pdf": "reads strange on the day — set aside pending discussion",
            # ⛔ NOT A MEASUREMENT OF THE OIL. A deliberately spoiled sample, run only to exercise the
            # clearing-4.0 read after the app restart. Its Q% is 8.0 against ~17 for the real fills and
            # its 624 band has collapsed; scoring it as Lugitsch would put a spoiled oil in the green set.
            "20260826LugitschC/test.pdf": "spoiled sample, software test only — not the oil"}
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
        print("  [!] EXCLUDED BY HAND: %s -- %s" % (relative, EXCLUDED[relative]))
    for relative in sorted(set(EXCLUDED) - set(excluded)):
        print("  [!] EXCLUDED entry never matched a file: %s" % relative)
    if lateRuns:
        print("  [!] NOT USED (%s policy: first %d DISTINCT reads per fill):" % (LATE_RUN_SESSIONS,
                                                                                 KEPT_RUN_COUNT))
        for entry in sorted(lateRuns):
            print("        %s" % entry)
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
    axes = figure.add_axes([0.105, 0.235, 0.865, 0.255])
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

    figure.text(0.105, 0.170,
                "[*]  Only Lugitsch has been measured in sunflower on more than one date, so it is the only\n"
                "oil that can show a trend at all. Every other line in row 2 is a single folder.",
                fontsize=8.2, va="top", linespacing=1.5)
    figure.text(0.105, 0.115,
                "[*]  %s\n"
                "[!]  A fill's own scatter is the yardstick for any step between fills: WITHIN a fill Rv "
                "repeats to sd ~1.2, but\n"
                "     INDEPENDENT FILLS of one oil sit 7\u201313 Rv apart \u2014 the preparation now "
                "dominates the measurement by about ten to one.%s"
                % (eyeOrderNote(rows),
                   "" if not EXCLUDED else
                   "\nSET ASIDE BY HAND, not plotted: " + "; ".join(sorted(EXCLUDED))),
                fontsize=8.2, color="#a03000", va="top", linespacing=1.5)
    pdf.savefig(figure)
    pyplot.close(figure)


def pageByDay(pdf, rows):
    """Rv, sunflower, ONE ROW PER MEASUREMENT DAY, stacked down an A4 portrait.

    ⭐ WHY PER DAY IS THE FAIR COMPARISON. Within a single day the lamp, the reference and the rig are
    held constant, so oil-vs-oil is read with the day divided out -- which the by-oil page cannot do,
    because there every oil except Lugitsch is a single folder and oil is perfectly confounded with day.
    Lugitsch is the only oil measured on all three days, so it acts as the running reference: its dotted
    line per row is where the one repeated oil sat THAT day.

    ⛔ Stacked, not side by side, and the shared y-axis is the whole point -- rows are meant to be read
    DOWN the page against one another, which columns of differing width made harder than it needed to be."""
    rows = [r for r in rows if r["solvent"] == "sunflower"]
    days = sorted({dateTag(sessionOf(r)) for r in rows})
    ceiling = max(r["Rv"] for r in rows) * 1.12
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Rv in sunflower — one row per measurement day", fontsize=13, fontweight="bold",
                    y=0.975)
    figure.text(0.5, 0.934,
                "The comparison with the day divided out. Same vertical scale in every row, so the rows\n"
                "read against each other. Dotted = that day's Lugitsch mean, the one oil measured on all days.",
                ha="center", fontsize=8.2, style="italic", linespacing=1.5)

    height = 0.195
    for index, day in enumerate(days):
        axes = figure.add_axes([0.105, 0.700 - index * 0.245, 0.865, height])
        today = [r for r in rows if dateTag(sessionOf(r)) == day]
        oils = sorted({r["oil"] for r in today})
        reference = [r["Rv"] for r in today if r["oil"] == "Lugitsch"]
        for position, oil in enumerate(oils):
            group = sorted((r for r in today if r["oil"] == oil), key=lambda r: r["run"])
            offsets = numpy.linspace(-0.22, 0.22, len(group)) if len(group) > 1 else [0.0]
            for offset, row in zip(offsets, group):
                axes.plot(position + offset, row["Rv"], "s", color=row["color"], ms=7,
                          markeredgecolor="black", markeredgewidth=0.4)
        if reference:
            axes.axhline(numpy.mean(reference), color="#2e7d32", lw=1.0, ls=":", alpha=0.85)
            axes.text(len(oils) - 0.45, numpy.mean(reference) + ceiling * 0.015,
                      "Lugitsch %.1f" % numpy.mean(reference), fontsize=7, color="#2e7d32",
                      ha="right", va="bottom", fontweight="bold")
        axes.axhline(RV_CUT, color="crimson", lw=1.3, ls="--")
        axes.set_xticks(range(len(oils)))
        axes.set_xticklabels([o.replace(" ", "\n") for o in oils], fontsize=8)
        axes.set_xlim(-0.6, len(oils) - 0.4)
        axes.set_ylim(0, ceiling)
        axes.grid(axis="y", alpha=0.3)
        axes.tick_params(labelsize=8)
        axes.set_ylabel("Rv", fontsize=10, fontweight="bold")
        axes.set_title("%s   ·   %d runs, %d oils" % (day, len(today), len(oils)),
                       fontsize=10.5, fontweight="bold", loc="left")

    walk = " → ".join("%.1f" % numpy.mean([r["Rv"] for r in rows
                                           if r["oil"] == "Lugitsch" and dateTag(sessionOf(r)) == day])
                      for day in days
                      if any(r["oil"] == "Lugitsch" and dateTag(sessionOf(r)) == day for r in rows))
    figure.text(0.105, 0.160,
                "[*]  Read ACROSS a row, not down the page: inside one day the rig is common to every oil,\n"
                "so the gaps within a row are the ones that mean something.",
                fontsize=8.2, va="top", linespacing=1.5)
    figure.text(0.105, 0.108,
                "[!]  08-22 carries only two oils and 08-24 never saw Esterer or Stekko, so no single row\n"
                "ranks all six. Lugitsch's own line moves %s across the rows: the reference itself\n"
                "is not fixed, which is why an oil measured on one day only cannot be placed against one\n"
                "measured on another.%s"
                % (walk, "" if not EXCLUDED else
                   "\nSET ASIDE BY HAND, not plotted: " + "; ".join(sorted(EXCLUDED))),
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


def rvCorpus():
    """The Rv-capable corpus, which is BIGGER than this file's d2R corpus: Rv needs only 500-627 nm,
    where a 2nd derivative at 624 needs the far flank past 632. Imported lazily because
    `reference_band_scan` imports names from this module -- at module level it would be a cycle."""
    import reference_band_scan as scan
    rows = scan.collect()
    for row in rows:
        for tag, (low, high) in (("rvOld", RV_REF_OLD), ("rvNew", RV_REF_NEW)):
            valley = float(row["a"][(row["nm"] >= 500.0) & (row["nm"] <= 560.0)].mean())
            red = float(row["a"][(row["nm"] >= 622.0) & (row["nm"] <= 627.0)].mean())
            reference = float(row["a"][(row["nm"] >= low) & (row["nm"] <= high)].mean())
            row[tag] = 100.0 * (red - valley) / (reference - valley)
    return paint(rows)


def pageRvNewStrip(pdf, rows, d2rCount):
    """Rv' by SESSION, not by run: 115 rows of text would be 2.7 pt. The runs are all still drawn."""
    sessions = sorted({sessionOf(r) for r in rows},
                      key=lambda s: -numpy.median([r["rvNew"] for r in rows if sessionOf(r) == s]))
    figure = pyplot.figure(figsize=(8.27, 11.69))
    figure.suptitle("Rv\u2032 \u2014 the blue-flank reference, every run of the archive",
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
    figure.suptitle("Rv against Rv\u2032 \u2014 what the reference band actually buys",
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

    with PdfPages(OUT) as pdf:
        pageStrip(pdf, rows)
        pageCurves(pdf, rows)
        pageBySolvent(pdf, rows)
        pageSunflower(pdf, rows)
        pageByDay(pdf, rows)
        rv = rvCorpus()
        pageRvNewStrip(pdf, rv, len(rows))
        pageRvOldNew(pdf, rv)
        pdf.infodict()["Title"] = "d2R over every archived run reaching 632 nm"
    print("wrote", OUT)


if __name__ == "__main__":
    main()
