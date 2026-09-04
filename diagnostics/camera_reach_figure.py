"""Figure for KB_cameras.md — what spectral range each camera on the roster can actually deliver.

    ./venv/bin/python diagnostics/camera_reach_figure.py

⭐ The point of the drawing is that the three cameras fail and succeed for DIFFERENT reasons, and only
one of the three limits is a law of physics:

  ELP 32e4:8830      a dielectric IR-cut edge at 641.8 nm  -- MEASURED (KB_lamps.md §4)
  Microdia 0c45:6366 no IR-cut (remote test, KB_lamps.md §6.1) -- red reach UNMEASURED
  ToupTek IMX290     clear IR-transmitting window + mono    -- reach set by silicon's 1100 nm bandgap

⚠ Every ToupTek number here is a PROJECTION from the vendor spec and from silicon physics, not a
measurement. The bar is drawn hollow for that reason. Nothing in the Spectracs record has ever measured
past 690 nm.

Coverage arithmetic (§4 of the KB): with the optics unchanged, the wavelength span a sensor can hold is
its imaging WIDTH times the dispersion in nm/mm. The ELP ROI holds 290.8 nm across 2055 of its 2592
columns, so the full frame holds ~367 nm; the dispersion follows from the frame width in mm, which
depends on whether the 2592x1944 mode is a CROP or a SCALE of the 3264x2448 sensor -- unresolved, so
both are carried through.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIGURE_DIRECTORY = os.path.join(REPO, "docs", "figures")

INK, GRID = "#1d2b36", "#d5dbe0"
ELP_COLOUR, MICRODIA_COLOUR, TOUPTEK_COLOUR = "#b0413e", "#c9a227", "#2f6f9f"

# What the metric and the standards actually want light AT.
LANDMARKS = [
    (432.0, "Soret\n432", "#3b5bdb"),
    (568.0, "Q\n568", "#0b6e4f"),
    (625.0, "Qy\n625", "#0b6e4f"),
    (710.0, "AOCS\n710", "#7b4bb7"),
    (970.0, "water\n~970", "#7b4bb7"),
]
QUIET_WINDOW = (660.0, 680.0)
AUTHORED_CLAMP = 632.6      # what the pipeline reads today
ELP_EDGE = 641.8            # measured dielectric cut, KB_lamps.md §4.1
SILICON_CUTOFF = 1107.0     # 1.12 eV bandgap


def main():
    os.makedirs(FIGURE_DIRECTORY, exist_ok=True)
    figure, axes = plt.subplots(figsize=(9.2, 4.6))

    rows = [
        # label, y, start, solidEnd, fadedEnd, colour, hollow, note
        ("ToupTek IMX290 mono\n(clear IR window, 12-bit)", 2.6, 400, 900, 1050, TOUPTEK_COLOUR, True,
         "projected — never measured"),
        ("Microdia 0c45:6366\n(production; no IR-cut)", 1.6, 400, 690, 800, MICRODIA_COLOUR, True,
         "no cliff expected — UNMEASURED"),
        ("ELP 32e4:8830\n(bench; archive camera)", 0.6, 400, 650, 690, ELP_COLOUR, False,
         "measured: 62 DN @650, 17 DN @660"),
    ]
    for label, y, start, solidEnd, fadedEnd, colour, hollow, note in rows:
        axes.add_patch(Rectangle((start, y - 0.17), solidEnd - start, 0.34,
                                 facecolor="none" if hollow else colour,
                                 edgecolor=colour, linewidth=1.6,
                                 hatch="////" if hollow else None, alpha=0.9))
        # the fading tail = signal present but under the 16 DN working floor
        axes.add_patch(Rectangle((solidEnd, y - 0.17), fadedEnd - solidEnd, 0.34,
                                 facecolor=colour, edgecolor="none", alpha=0.13))
        axes.text(394, y, label, fontsize=8, color=INK, ha="right", va="center")
        axes.text(fadedEnd + 8, y, note, fontsize=7, color=colour, va="center", style="italic")

    axes.axvline(ELP_EDGE, color=ELP_COLOUR, linewidth=1.2, linestyle="--")
    axes.text(ELP_EDGE - 5, 3.30, "ELP IR-cut\n641.8 nm", fontsize=7.5, color=ELP_COLOUR,
              ha="right", va="top")
    axes.axvline(AUTHORED_CLAMP, color="#7b8794", linewidth=1.0, linestyle=":")
    axes.text(AUTHORED_CLAMP - 5, 0.02, "pipeline clamp 632.6", fontsize=7, color="#7b8794", ha="right")
    axes.axvline(SILICON_CUTOFF, color=INK, linewidth=1.4)
    axes.text(SILICON_CUTOFF - 6, 3.30, "silicon bandgap ~1100 nm\nthe only hard wall here",
              fontsize=7.5, color=INK, ha="right", va="top")

    axes.axvspan(*QUIET_WINDOW, color="#0b6e4f", alpha=0.09)
    axes.text(670, 3.30, "quiet\nwindow", fontsize=7, color="#0b6e4f", ha="center", va="top")

    for nanometers, label, colour in LANDMARKS:
        axes.axvline(nanometers, color=colour, linewidth=0.8, alpha=0.5)
        axes.text(nanometers, -0.28, label, fontsize=7, color=colour, ha="center", va="top")

    axes.set_xlim(330, 1180)
    axes.set_ylim(-0.75, 3.40)
    axes.set_yticks([])
    axes.set_xlabel("wavelength (nm)", fontsize=8.5, color=INK)
    axes.set_title("What each camera can reach — and why the three limits are not the same kind of limit",
                   fontsize=10.5, color=INK)
    axes.grid(True, axis="x", color=GRID, linewidth=0.6)
    axes.tick_params(labelsize=8, colors=INK)
    for side, spine in axes.spines.items():
        spine.set_color(GRID if side == "bottom" else "none")

    figure.tight_layout()
    path = os.path.join(FIGURE_DIRECTORY, "camera_reach.svg")
    figure.savefig(path)
    plt.close(figure)
    print("wrote", path)

    # --- the coverage arithmetic, printed so the KB never hand-copies a number
    roiNanometers, roiColumns, frameColumns = 290.8, 2055, 2592
    frameNanometers = roiNanometers * frameColumns / roiColumns
    print("\nELP full frame holds %.0f nm of spectrum (ROI holds %.1f over %d/%d columns)"
          % (frameNanometers, roiNanometers, roiColumns, frameColumns))
    print("\n case                      ELP frame   dispersion   IMX290 span   starting at 400 nm")
    for case, widthMillimetres in (("2592 mode is a CROP  (1.40 um)", 2592 * 1.40e-3),
                                   ("2592 mode is a SCALE (1.76 um)", 4.5696)):
        dispersion = frameNanometers / widthMillimetres
        span = 5.568 * dispersion
        print("  %-30s %5.2f mm   %6.1f nm/mm   %6.0f nm      400-%.0f nm"
              % (case, widthMillimetres, dispersion, span, 400 + span))
    print("\n⇒ one IMX290 frame covers roughly 400-850 .. 400-960 nm at TODAY's dispersion.")
    needed = 600 / 5.568
    print("  To guarantee 400-1000 (600 nm) needs %.1f nm/mm — i.e. spreading the spectrum %.0f-%.0f %%"
          % (needed, 100 * (needed / (frameNanometers / (2592 * 1.40e-3)) - 1),
             100 * (needed / (frameNanometers / 4.5696) - 1)))
    print("  LESS tightly (a coarser grating or a shorter focal length), which COSTS resolving power.")
    print("  ⭐ Affordable: the optical resolution is ~2 nm (Hg 576.96/579.07 doublet, ~14 px), while")
    print("    sampling is 0.14 nm/px (ELP) and 0.23 nm/px (IMX290) — both oversample ~10x.")


if __name__ == "__main__":
    main()
