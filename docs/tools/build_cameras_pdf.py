#!/usr/bin/env python3
"""
Generator for the internal *Cameras* knowledge-base PDF.

    SOURCE OF TRUTH:  docs/KB_cameras.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_Cameras.pdf

Seventh of the internal document set, and the DETECTOR counterpart to `build_lamps_pdf.py`'s light
source: what each camera on the roster is, what its optical path does to the spectrum, and what a
camera change would cost and buy (including the 1000 nm NIR question). The rendering is done by the
capture-fidelity renderer; this script only supplies the different source, output and title.

Figure 1 is produced by:
    ./venv/bin/python diagnostics/camera_reach_figure.py
which writes docs/figures/camera_reach.svg and prints the coverage arithmetic quoted in §4.2.
Re-run it if the calibration, the ROI or the candidate camera changes, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_cameras_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "KB_cameras.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_Cameras.pdf"))
TITLE = "Spectracs — Cameras"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
