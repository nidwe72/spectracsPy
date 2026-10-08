"""Draw the Spectracs app/server icon from resource/logo.png — SPEC_windows_build.md D7.

    makeIcon.py --logo <logo.png> --out <icon.png> [--frame] [--ico <icon.ico>]

The S glyph of the logo, centred on a dark 256 px square; --frame adds the brand-green border (the server icon).
--ico also writes a multi-size Windows icon (16/32/48/256). Moved verbatim out of buildAppImages.sh, so the PNG
stays byte-identical to the one the Linux AppImages have carried since 2026-09-09. Runs on Linux, before any
sources go to the Windows VM; writes only where it is told to (never into a repo).
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw


def makeIcon(logo, out, frame=False, ico=None):
    src = Image.open(logo).convert("RGBA"); a = np.array(src); alpha = a[:, :, 3]
    cols = (alpha > 10).any(axis=0); runs = []; s = None
    for i, v in enumerate(cols):
        if v and s is None: s = i
        if not v and s is not None: runs.append((s, i)); s = None
    x0, x1 = runs[0]                                   # the S — §16
    rows = (alpha[:, x0:x1] > 10).any(axis=1); ys = np.where(rows)[0]
    glyph = src.crop((x0, ys[0], x1, ys[-1] + 1))
    green = tuple(int(v) for v in a[np.unravel_index(alpha.argmax(), alpha.shape)][:3])
    icon = Image.new("RGBA", (256, 256), (26, 26, 26, 255))
    size = 150 if frame else 168
    sc = size / max(glyph.size)
    g = glyph.resize((int(glyph.width * sc), int(glyph.height * sc)), Image.LANCZOS)
    icon.paste(g, ((256 - g.width) // 2, (256 - g.height) // 2), g)
    if frame:
        ImageDraw.Draw(icon).rectangle([4, 4, 251, 251], outline=green + (255,), width=8)
    icon.save(out)
    if ico:
        icon.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--logo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--frame", action="store_true")
    parser.add_argument("--ico")
    args = parser.parse_args()
    makeIcon(args.logo, args.out, args.frame, args.ico)
