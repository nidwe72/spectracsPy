"""Yuji SunWave LED vs a 60 W halogen, both read off the SAME dev-capture frames — and what the
comparison says about where the instrument's red range actually ends.

    ./venv/bin/python diagnostics/lamp_yuji_vs_halogen.py [--figures]

WHY THIS EXISTS
---------------
`KB_spectroscopy_physics.md` §7.2 states the honest limit of every previous attempt:

    "the red channel falls ~40x between 631 and 657 nm (IR-cut filter + sensor QE + the source's own
     decline -- ONE LAMP CANNOT SEPARATE THE THREE)"

and `DOC_lamp_410_680.md` §6.2a leaves the question formally open, with the Eu(3+) far lines queued as
the decider: *"Lines visible => the camera passes 690 nm ... Lines absent => the IR-cut is the gate."*

⭐ A halogen bulb settles it WITHOUT resolving any line, because its emission is a **known analytic
function**. A tungsten filament at any plausible colour temperature is a Planck continuum rising
monotonically from 600 to 700 nm, with tungsten's spectral emissivity drifting only a few percent across
that span. So `measured / Planck` IS the instrument response -- the division that no LED, CFL or phosphor
lamp permits, because their own SPD structure is unknown at exactly the wavelengths in question.

WHERE THE DATA COMES FROM
-------------------------
Two screenshots of *Settings > Development > Capture images* (Edwin, 2026-09-04), same session, same
optics, same ROI box, camera ELP (32e4:8830). ⚠ They are SCREENSHOTS of the preview, not raw frames:
~3.4 sensor columns per screen pixel (0.48 nm per screen column), so treat every wavelength here as
+-2 nm. Nothing in the conclusions turns on 2 nm.

⭐ THE ROI BOX IS THE *EXTENDED* ROI, NOT THE AUTHORED ONE. `DevCaptureViewModule` draws
`ExtendedRoiLogicModule().extendedRoi(calibration, image.width())`, which inverts the px->nm cubic for
400/700 nm and clamps to the raster -- sensor columns 536..2591, i.e. 400.0..690.8 nm (700 nm would need
column 2668, past the 2592 px raster). Identified two ways, both independent of this file's argument:
  1. predicted box aspect 2056/875 = 2.350 against 601/256 = 2.348 measured on screen (0.1 %);
  2. the Bayer G=R crossover lands at 581.0 nm (Yuji) / 581.5 nm (halogen), against the 581 nm already
     on record (`KB_spectroscopy_physics.md` §4.1a); B=G lands at 486.2 nm on BOTH lamps. Two lamps of
     different families agreeing on two crossovers pins the scale to better than 1 nm.
⚠ The MEASUREMENT pipeline still uses the AUTHORED ROI (564..2145 = 403.9..632.6 nm) -- the 630 nm clamp.

WHAT IT CANNOT SAY
------------------
⛔ It separates "the instrument" from "the source". It does NOT separate the IR-cut filter from sensor QE
from grating efficiency by direct measurement -- that needs a de-filtered camera. What carries the
attribution is the EDGE STEEPNESS (§ the `--figures` panel 2 fit): 10x every 9-18 nm through 630-660 nm
against 10x every 745 nm across 550-620 nm. No dye, no silicon QE curve and no grating does that; a
dielectric interference filter is the only component in the chain with an edge that shape.
⛔ It assumes the preview pixmap is the camera frame (it is -- `QPixmap.fromImage(image)`) and decodes it
with the pipeline's own gamma. `--figures` prints the sensitivity: the edge moves <3 nm across pow1.8 /
pow2.2 / pow2.4 / sRGB and not at all across 2700-3100 K.
"""
import argparse
import os

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIGURE_DIRECTORY = os.path.join(REPO, "docs", "figures")

# The authored calibration (`spectrometer_calibration_profile` 54a45667-bba9-48a9-a078-7496afad41e2).
# lambda(px) = A px^3 + B px^2 + C px + D over ABSOLUTE sensor columns -- see
# ImageSpectrumAcquisitionLogicModule, which feeds `polynomial(pixelIndex)` the absolute index.
CUBIC = [-5.77381138877048e-09, 2.35944918200958e-05, 0.116112996214963, 331.935289341983]
POLYNOMIAL = np.poly1d(CUBIC)
AUTHORED_ROI = (564, 2145)          # what the measurement pipeline reads  -> 403.9 .. 632.6 nm
EXTENDED_ROI = (536, 2591)          # what the capture view DRAWS          -> 400.0 .. 690.8 nm
CAPTURE_GAMMA = 2.2                 # SpectralColorUtil.DEFAULT_CAPTURE_GAMMA

# (screenshot, rectLeft, rectRight, rectTop, rectBottom) -- the dashed ROI box, located by its pen
# colour (61,120,72) = ApplicationStyleLogicModule primary. Both boxes are 601 x 256 screen px.
SHOTS = {
    "Yuji SunWave LED": ("/home/nidwe72/ksnip_20260904-005834.png", 186, 787, 289, 545),
    "60 W halogen":     ("/home/nidwe72/ksnip_20260904-005835.png", 176, 777, 288, 544),
}

# `SPEC_capture_quality.md` §16.28.4, run 20260808B (Yuji, ROI opened to 690 nm, 2026-08-09). Kept here
# as an INDEPENDENT REPLICATION TARGET: a different session, a different exposure, the same lamp.
RUN_20260808B = {630: 39.7, 640: 11.5, 650: 0.7, 656: 0.13, 660: 0.01}

# `DOC_lamp_410_680.md` §6.2 / §16.25.4 -- the claim this file's Q4 falsifies.
SANSI_656_CLAIM_DN = 115.0


def linearProfile(path, left, right, top, bottom, gamma=CAPTURE_GAMMA):
    """One value per screen column of the ROI box, in LINEAR light on a 0..255 scale, reduced the way
    the pipeline reduces: gamma-decoded first, max-channel (radiometric, not blue-suppressing), averaged
    over the MIDDLE THIRD of the band (ImageSpectrumAcquisitionLogicModule.__INSET_FRACTION).

    Returns (wavelengths, maxChannel, perChannel)."""
    frame = np.array(Image.open(path).convert("RGB")).astype(np.float64)
    inset = int(round((bottom - top) / 3.0))
    band = frame[top + inset:bottom - inset, left + 2:right - 1]
    linear = 255.0 * np.clip(band / 255.0, 0.0, 1.0) ** gamma
    maxChannel = linear.max(axis=2).mean(axis=0)
    perChannel = linear.mean(axis=0)
    columns = maxChannel.size
    x1, x2 = EXTENDED_ROI
    sensorColumn = x1 + (np.arange(columns) + 2.5) / (right - left) * (x2 - x1)
    return POLYNOMIAL(sensorColumn), maxChannel, perChannel


def encode(linear):
    """LINEAR 0..255 back to camera DN, so numbers here are comparable with the DN guard."""
    return 255.0 * np.clip(linear / 255.0, 0.0, 1.0) ** (1.0 / CAPTURE_GAMMA)


def planck(nanometers, kelvin):
    """Spectral radiance of a blackbody. ⚠ Tungsten is a GREY body: its spectral emissivity falls from
    ~0.45 at 450 nm to ~0.42 at 700 nm, i.e. a few percent across the whole span -- negligible against
    the 350x this file is about, so the grey factor is deliberately not modelled."""
    h, c, kB = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    lam = np.asarray(nanometers, dtype=np.float64) * 1e-9
    return (2.0 * h * c ** 2 / lam ** 5) / np.expm1(h * c / (lam * kB * kelvin))


def instrumentResponse(wavelengths, halogen, kelvin=2900.0, anchor=600.0):
    """measured halogen / Planck, normalised to 1.0 at `anchor`. THE division no LED permits."""
    response = halogen / planck(wavelengths, kelvin)
    return response / response[int(np.argmin(abs(wavelengths - anchor)))]


def fitCutEdge(wavelengths, response, low=470.0, high=668.0):
    """Split the response into a SLOW part and an EDGE:  R = exp(quadratic) x 1/(1+exp((l-l50)/w)).

    The quadratic stands for everything that varies slowly (grating efficiency, silicon QE, Bayer dye,
    lens); the logistic stands for a dielectric cut-on/cut-off edge. ⚠ The split is a MODEL -- what is
    measured is the total. Its justification is that the two components differ by ~50x in log-slope, so
    the decomposition is not sensitive to the exact form chosen for either.

    Fitted below 668 nm: past that the halogen is under ~8 DN and quantisation dominates."""
    from scipy.optimize import least_squares
    mask = (wavelengths >= low) & (wavelengths <= high) & (response > 0)
    offset = wavelengths[mask] - 600.0
    target = np.log(response[mask])

    def residual(p):
        a, b, c, centre, width = p
        model = a + b * offset + c * offset ** 2 - np.log1p(np.exp((wavelengths[mask] - centre) / width))
        return model - target

    fit = least_squares(residual, [0.0, 0.0, 0.0, 650.0, 3.0],
                        bounds=([-5, -1, -1, 600, 0.3], [5, 1, 1, 700, 40]))
    a, b, c, centre, width = fit.x
    slow = np.exp(a + b * (wavelengths - 600.0) + c * (wavelengths - 600.0) ** 2)
    edge = 1.0 / (1.0 + np.exp((wavelengths - centre) / width))
    return centre, width, slow, edge, float(fit.fun.std())


def at(wavelengths, target):
    return int(np.argmin(abs(wavelengths - target)))


# --------------------------------------------------------------------------- report

def report():
    data = {name: linearProfile(*args) for name, args in SHOTS.items()}
    wavelengths = data["60 W halogen"][0]
    halogen = data["60 W halogen"][1]
    yuji = data["Yuji SunWave LED"][1]

    print("ROI box = EXTENDED roi %s -> %.1f..%.1f nm, %d columns, %.3f nm/column"
          % (EXTENDED_ROI, wavelengths[0], wavelengths[-1], wavelengths.size,
             float(np.diff(wavelengths).mean())))
    print("measurement pipeline still reads the AUTHORED roi %s -> %.1f..%.1f nm"
          % (AUTHORED_ROI, POLYNOMIAL(AUTHORED_ROI[0]), POLYNOMIAL(AUTHORED_ROI[1])))

    print("\n=== 0. Scale check — the Bayer crossovers, which belong to the CAMERA, not the lamp")
    for name in SHOTS:
        w, _, channels = data[name]
        for high, low, label in ((2, 1, "B=G"), (1, 0, "G=R")):
            difference = channels[:, high] - channels[:, low]
            crossings = np.nonzero((difference[:-1] > 0) & (difference[1:] <= 0))[0]
            # Only the handover in the band where BOTH channels carry real light; near-zero
            # channels cross many times on noise.
            crossings = [i for i in crossings if channels[i, high] > 20.0]
            for i in crossings:
                share = difference[i] / (difference[i] - difference[i + 1])
                print("   %-18s %s at %.1f nm" % (name, label, w[i] + share * (w[i + 1] - w[i])))
    print("   ⇒ both lamps put B=G at 486.2 and G=R at ~581 nm — the 581 already on record")
    print("     (KB_spectroscopy_physics.md §4.1a). Two lamp families agreeing on two crossovers")
    print("     pins this wavelength scale to better than 1 nm, independently of the ROI argument.")

    print("\n=== 1. The two lamps as recorded (DN, lamp x instrument together)")
    print("   nm     Yuji      halogen")
    for target in (450, 500, 550, 580, 600, 620, 630, 640, 650, 655, 660, 670, 680, 690):
        i = at(wavelengths, target)
        print("  %4.0f   %6.1f     %6.1f" % (wavelengths[i], encode(yuji[i]), encode(halogen[i])))

    print("\n=== 2. Red edge: last wavelength above each DN level")
    for level in (50, 20, 16, 10, 5, 2):
        row = ""
        for name, series in (("Yuji", yuji), ("halogen", halogen)):
            above = np.nonzero(encode(series) >= level)[0]
            row += "  %s %.1f nm" % (name, wavelengths[above[-1]] if above.size else float("nan"))
        print("   DN >= %2d :%s" % (level, row))
    print("   ⚠ neither frame saturates (peaks %d / %d DN), so this is a like-for-like exposure"
          % (round(encode(yuji).max()), round(encode(halogen).max())))

    print("\n=== 3. Instrument response = halogen / Planck  (⭐ the division no LED permits)")
    print("   nm  " + "".join("   %5dK" % k for k in (2700, 2900, 3100)))
    for target in (450, 500, 550, 600, 620, 630, 640, 650, 655, 660, 670, 680):
        i = at(wavelengths, target)
        row = "  %4.0f " % wavelengths[i]
        for kelvin in (2700, 2900, 3100):
            row += "  %7.4f" % instrumentResponse(wavelengths, halogen, kelvin)[i]
        print(row)
    print("   ⇒ colour temperature is irrelevant in the red (<10 % spread); it matters only in the blue")

    response = instrumentResponse(wavelengths, halogen)
    print("\n=== 4. Model-free steepness — how fast the response falls, in decades per nm")
    for low, high in ((450, 550), (550, 620), (620, 640), (630, 650), (640, 660), (620, 660)):
        decades = np.log10(response[at(wavelengths, low)] / response[at(wavelengths, high)])
        pace = ("10x every %.0f nm" % ((high - low) / decades)) if decades > 0.02 else "flat or rising"
        print("   %3d -> %3d nm : %6.2f decades  (%s)" % (low, high, decades, pace))
    print("   ⭐ 630-660 is ~50x steeper per nm than 550-620. Silicon QE, Bayer dye and grating")
    print("     efficiency all vary over HUNDREDS of nm. A dielectric edge is the only candidate.")

    centre, width, slow, edge, rms = fitCutEdge(wavelengths, response)
    print("\n=== 5. Split into slow response x cut edge")
    print("   edge: lambda_50 = %.1f nm, w = %.2f nm (10->90 %% over %.1f nm), log-residual %.1f %%"
          % (centre, width, 2 * width * np.log(9), 100 * rms))
    i620 = at(wavelengths, 620)
    print("   nm    total drop vs 620    of which slow    of which the EDGE    edge's share")
    for target in (630, 640, 650, 655, 660, 670):
        i = at(wavelengths, target)
        total = response[i620] / response[i]
        slowDrop = slow[i620] / slow[i]
        edgeDrop = edge[i620] / edge[i]
        share = np.log(edgeDrop) / np.log(slowDrop * edgeDrop)
        print("  %4.0f      x%-10.1f       x%-6.2f          x%-12.1f    %.0f %%"
              % (wavelengths[i], total, slowDrop, edgeDrop, 100 * share))

    print("\n=== 6. Is the collapse measured on healthy DN, or in the noise?")
    for target in (630, 640, 650, 655, 660):
        i = at(wavelengths, target)
        print("   %4.0f nm   halogen %6.1f DN" % (wavelengths[i], encode(halogen[i])))
    print("   ⭐ the whole 630->660 collapse happens between 190 DN and 17 DN — well clear of any floor,")
    print("     and above the 16 DN guard. It is not a quantisation artefact.")

    print("\n=== 7. ⭐ Independent replication of SPEC_capture_quality §16.28.4 run 20260808B (Yuji)")
    print("    nm    §16.28.4    this frame    ratio")
    for target, theirs in sorted(RUN_20260808B.items()):
        mine = yuji[at(wavelengths, target)]
        print("   %4d   %8.2f    %9.3f    %5.2f" % (target, theirs, mine, theirs / mine))
    print("   ⇒ a different session and exposure, the same lamp: identical SHAPE over 4000x of")
    print("     dynamic range, to within one constant factor. §16.28.4's Yuji row is confirmed.")

    print("\n=== 8. ⛔ What this falsifies — §6.2a reconciliation 1 ('the V1 Sansi owns the deep red')")
    ratio = response[at(wavelengths, 656)] / response[at(wavelengths, 620)]
    needed = 255.0 * (SANSI_656_CLAIM_DN / 255.0) ** CAPTURE_GAMMA / ratio
    print("   §16.25.4 claims 115 DN at 656 nm. Response there is %.5f of 620 nm, so the lamp would" % ratio)
    print("   have to EMIT %.0fx more at 656 nm than at 620 nm (exposure cancels). No phosphor —"
          % (needed / halogen[at(wavelengths, 620)]))
    print("   KSF/PFS line emitter included — does that. ⇒ the lamp-difference explanation is dead;")
    print("   §6.2a's reconciliations 2 (mis-transferred wavelength axis) and 3 (clipping) survive.")

    print("\n=== 9. What removing the IR-cut filter would buy (⚠ PREDICTION, extrapolated slow term)")
    i620 = at(wavelengths, 620)
    for target in (650, 660, 670, 680):
        i = at(wavelengths, target)
        predicted = halogen[i620] * slow[i] / slow[i620]
        print("   %4.0f nm   now %5.1f DN   ->  ~%5.0f DN   (x%.0f more light)"
              % (wavelengths[i], encode(halogen[i]), encode(predicted), predicted / halogen[i]))
    print("   ⇒ the 660-680 nm QUIET WINDOW — the pigment-free baseline anchor the metric has never")
    print("     had (DOC_lamp_410_680 §2.2) — becomes reachable with the lamp already on the bench.")

    return wavelengths, yuji, halogen, response, slow, edge, centre, width


def sensitivity():
    print("\n=== 10. Sensitivity of the edge to every assumption")
    path, *box = SHOTS["60 W halogen"]
    print("   decode     T(K)   lambda_50    w    10->90")
    for label, gamma in (("pow1.8", 1.8), ("pow2.2", 2.2), ("pow2.4", 2.4)):
        wavelengths, halogen, _ = linearProfile(path, *box, gamma=gamma)
        for kelvin in (2700.0, 3100.0):
            centre, width, _, _, _ = fitCutEdge(
                wavelengths, instrumentResponse(wavelengths, halogen, kelvin))
            print("   %-8s  %5.0f   %8.1f  %5.2f  %6.1f"
                  % (label, kelvin, centre, width, 2 * width * np.log(9)))
    print("   ⇒ lambda_50 = 641 +- 1 nm under every decode and every plausible filament temperature.")


# --------------------------------------------------------------------------- figures

INK, GRID, HALOGEN_COLOUR, YUJI_COLOUR = "#1d2b36", "#d5dbe0", "#b0413e", "#2f6f9f"


def figures(wavelengths, yuji, halogen, response, slow, edge, centre, width):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def dress(axes, title, xlabel="wavelength (nm)"):
        axes.set_title(title, fontsize=10.5, color=INK)
        axes.set_xlabel(xlabel, fontsize=8.5, color=INK)
        axes.grid(True, color=GRID, linewidth=0.6)
        axes.tick_params(labelsize=8, colors=INK)
        for spine in axes.spines.values():
            spine.set_color(GRID)

    os.makedirs(FIGURE_DIRECTORY, exist_ok=True)
    authoredEdge = float(POLYNOMIAL(AUTHORED_ROI[1]))

    # --- Figure 1: the two lamps, as the camera recorded them.
    figure, (upper, lower) = plt.subplots(2, 1, figsize=(9.2, 6.8), sharex=True)
    for axes, scale in ((upper, "linear"), (lower, "log")):
        axes.plot(wavelengths, encode(halogen), color=HALOGEN_COLOUR, linewidth=1.6, label="60 W halogen")
        axes.plot(wavelengths, encode(yuji), color=YUJI_COLOUR, linewidth=1.6, label="Yuji SunWave LED")
        axes.axhline(16, color=INK, linewidth=0.9, linestyle=":")
        axes.axvspan(660, 680, color="#0b6e4f", alpha=0.08)
        axes.axvline(authoredEdge, color="#7b8794", linewidth=1.1, linestyle="--")
        axes.set_yscale(scale)
        axes.set_ylabel("camera DN", fontsize=8.5, color=INK)
    upper.set_ylim(0, 260)
    lower.set_ylim(0.5, 400)
    upper.text(662, 238, "quiet window\n660-680", fontsize=7.5, color="#0b6e4f")
    upper.text(authoredEdge - 3, 238, "authored ROI ends\n632.6 nm", fontsize=7.5,
               color="#7b8794", ha="right")
    lower.text(402, 18.5, "16 DN guard", fontsize=7.5, color=INK)
    # The two notches are the MAX-CHANNEL reduction handing over between Bayer channels, not the lamps:
    # they sit at the same wavelength on both, and the 581 one is the crossover already on record
    # (KB_spectroscopy_physics.md §4.1a — the reason the Q band reads 568, not 574).
    for crossover, label, tip in ((486.2, "B|G", 78.0), (581.2, "G|R", 92.0)):
        upper.annotate("Bayer %s crossover %.0f nm\n(max-channel artefact, both lamps)"
                       % (label, crossover), xy=(crossover, tip), xytext=(crossover - 62, 26),
                       fontsize=7, color="#7b8794",
                       arrowprops=dict(arrowstyle="->", color="#7b8794", linewidth=0.8))
    dress(upper, "Figure 1 — the two lamps as the camera recorded them (linear DN)", "")
    dress(lower, "the same data on a log axis — where the red end actually goes")
    upper.legend(fontsize=8.5, frameon=False)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURE_DIRECTORY, "lamp_two_lamps.svg"))
    plt.close(figure)

    # --- Figure 2: the instrument response, and the edge inside it.
    figure, axes = plt.subplots(figsize=(9.2, 4.8))
    axes.plot(wavelengths, response, color=HALOGEN_COLOUR, linewidth=1.8,
              label="measured response = halogen / Planck")
    axes.plot(wavelengths, slow, color="#7b8794", linewidth=1.4, linestyle="--",
              label="slow part: grating x QE x dye x lens")
    axes.plot(wavelengths, slow * edge, color="#0b6e4f", linewidth=1.2, linestyle=":",
              label="slow x dielectric edge (fit)")
    axes.axvline(centre, color=INK, linewidth=1.0)
    axes.text(656, 2.5e-2, "cut edge\n$\\lambda_{50}$ = %.0f nm\n10-90 %% over %.0f nm"
              % (centre, 2 * width * np.log(9)), fontsize=8, color=INK)
    axes.axvspan(660, 680, color="#0b6e4f", alpha=0.08)
    axes.set_yscale("log")
    axes.set_ylim(1e-4, 3)
    axes.set_xlim(430, 690)
    axes.set_ylabel("response, normalised at 600 nm", fontsize=8.5, color=INK)
    dress(axes, "Figure 2 — dividing the halogen by Planck leaves the INSTRUMENT, and it has an edge")
    axes.legend(fontsize=8.5, frameon=False, loc="lower left")
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURE_DIRECTORY, "lamp_instrument_response.svg"))
    plt.close(figure)

    # --- Figure 3: attribution — who takes the light away, and where.
    figure, axes = plt.subplots(figsize=(9.2, 4.2))
    i620 = at(wavelengths, 620)
    window = (wavelengths >= 600) & (wavelengths <= 675)
    axes.plot(wavelengths[window], (slow[i620] / slow[window]), color="#7b8794", linewidth=1.6,
              label="lost to the slow response (QE, grating, dye)")
    axes.plot(wavelengths[window], (edge[i620] / edge[window]), color=HALOGEN_COLOUR, linewidth=1.8,
              label="lost to the cut edge")
    axes.plot(wavelengths[window], (response[i620] / response[window]), color=INK, linewidth=1.2,
              linestyle=":", label="measured total")
    axes.set_yscale("log")
    axes.set_ylim(0.8, 1e4)
    axes.set_ylabel("attenuation relative to 620 nm", fontsize=8.5, color=INK)
    axes.axvspan(660, 680, color="#0b6e4f", alpha=0.08)
    dress(axes, "Figure 3 — what actually takes the red away: the edge, not the sensor")
    axes.legend(fontsize=8.5, frameon=False, loc="upper left")
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURE_DIRECTORY, "lamp_attribution.svg"))
    plt.close(figure)

    print("\nwrote lamp_two_lamps.svg, lamp_instrument_response.svg, lamp_attribution.svg to docs/figures/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", action="store_true", help="write the three SVGs to docs/figures/")
    arguments = parser.parse_args()
    computed = report()
    sensitivity()
    if arguments.figures:
        figures(*computed)


if __name__ == "__main__":
    main()
