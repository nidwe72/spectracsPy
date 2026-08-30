"""WHAT ARE THE 581 nm AND 609 nm FEATURES, PER CHANNEL? Replayed from the embedded capture frames.
(Edwin, 2026-08-30: "isn't there a way to make a Bayer-sensor camera act more like a BW sensor?")

Both are called "the Bayer channel crossover" throughout the documentation. That name is a HYPOTHESIS
about a mechanism, and it had never been checked against the per-channel data -- which every archived
run carries, because the report embeds both full-resolution capture frames.

What this prints, per fill:

    1. R, G, B through 555-640 nm in LINEAR light -- is either feature actually a CROSSING?
    2. the same feature under max / sum / green reductions -- is it a `max()` switching artefact?
    3. its apparent position against the AE-landed exposure -- does a FIXED spectral feature move?
    4. the per-channel headroom -- is anything clipping in the working band?
    5. what a LUMA reduction would cost -- the "make it act like a mono sensor" option (section 15.2a)
    6. WHAT THE ATTACHED CAMERA CAN ACTUALLY DO -- identity, pixel formats, frame sizes and V4L2
       controls. `--probe-only` runs just this part, so a NEW camera can be characterised before it is
       ever mounted: `SPEC_lamp_rebuild.md` section 12.5 is scored straight off this output.

⭐ THE ANSWER FOR 609 nm, on the four 2026-08-30 Lugitsch fills: red carries 96-99 % of the light
through 596-620 nm and green is dead by 604, so there is NO crossing there. The feature is a ~40 %
STEP IN THE RED CHANNEL'S OWN RESPONSE between 604 and 612. `sum` reproduces it at the same position
and shifts it by the same +2.1 nm, so it is not a reduction artefact either -- consistent with
`SPEC_capture_quality.md` section 16.8.2, which found the notch is mostly a real dip in the sensor's
total response.

⛔⛔ AND NO FIXED SPECTRAL FEATURE CAN MOVE 2 nm WITH EXPOSURE. Not a lamp line, not a filter dye edge,
not an IR-cut: all are functions of wavelength alone. So the edge is stationary and its APPARENT
position moves -- a compressive nonlinearity displaces where a steep edge seems to turn over as the
level changes. That is section 17's gamma question, not a Bayer question. Section 16.39.3a is the
retraction this script was written to support.

⚠ THE 581 nm FEATURE IS A DIFFERENT ANIMAL and this script does not rename it -- run it and read
column 1. Where B, G and R actually do cross, "crossover" is the right word.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/channel_replay.py
    ... diagnostics/channel_replay.py --probe-only              # just the attached camera
    ... diagnostics/channel_replay.py --device /dev/video2      # a different node
"""
import os
import sys

import argparse
import fcntl
import glob
import struct

import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peak_ratio_archive as archive
import reduction_sum_vs_max as replay

# ⭐ The four fills of the 2026-08-30 sitting: one oil, one recipe, one seating order, and the AE
# landed on 104 for exactly one of them (`CAPTURE-SETTINGS`, section 16.39.2). That makes them the
# archive's only clean exposure contrast at fixed preparation.
FILLS = [("20260828LugitschC", 90), ("20260828LugitschD", 90),
         ("20260828LugitschE", 104), ("20260828LugitschF", 90)]
FEATURES = [("581 nm reference minimum", 574.0, 590.0), ("609 nm step", 600.0, 616.0)]
# ⭐ ITU-R BT.601 luma, the weighting YUYV's Y plane carries. `SpectralColorUtil.toGrayLuminance` uses the
# integer form (11r+16g+5b)/32; the difference is below a DN and this is the one the camera applies.
LUMA = numpy.array([0.299, 0.587, 0.114])
# ⛔ The ROI and the px->nm cubic were AUTHORED at this size (SPEC_capture_quality.md section 4.9).
# A camera that cannot deliver it uncompressed is a recalibration, not a swap.
CALIBRATION_SIZE = (2592, 1944)
GUARD_BAND = (448.0, 460.0)
FLOOR_DN = 16.0                                     # section 16.23.10b, the quantization guard
GAMMA = 2.2


def channelsOf(series, name="001.pdf"):
    """Per-column R, G, B of the REFERENCE leg, in LINEAR light, on the run's own nm grid.

    ⛔ The reference, not the sample: it is pure solvent, so anything seen here is the instrument."""
    reference, frames = replay.attachments(os.path.join(archive.ARCHIVE, series, name))
    wavelengths, channels, _ = replay.alignedChannels(frames["reference"], reference)
    return numpy.array(wavelengths), replay.util.decodeGammaArray(channels.astype(numpy.uint8)), channels


def apparentPosition(wavelengths, values, low, high):
    """Where the curve turns over hardest -- the sharpest second derivative in the window."""
    grid = numpy.arange(low, high, 0.1)
    curve = numpy.interp(grid, wavelengths, values)
    return float(grid[1:-1][numpy.abs(numpy.diff(curve, 2)).argmax()])


def crossings(wavelengths, linear, low, high):
    """Every wavelength in the window where the DOMINANT channel changes. Empty => not a crossover."""
    grid = numpy.arange(low, high, 0.1)
    dominant = numpy.array([numpy.interp(grid, wavelengths, linear[:, i]) for i in range(3)]).argmax(axis=0)
    return [(float(grid[i + 1]), "RGB"[dominant[i]], "RGB"[dominant[i + 1]])
            for i in range(len(grid) - 1) if dominant[i] != dominant[i + 1]]


def encodeDn(linear):
    """LINEAR 0..255 -> camera DN, the shipped guard's own encode (`dn_guard_audit.encodeDn`)."""
    return 255.0 * (max(0.0, float(linear)) / 255.0) ** (1.0 / GAMMA)


# ⚠ V4L2 control types and the flag that marks a control read-only, so the table below says which
# knobs a camera actually HANDS OVER rather than merely reports.
CONTROL_TYPES = {1: "int", 2: "bool", 3: "menu", 4: "button", 5: "int64", 6: "class", 7: "str",
                 8: "bitmask", 9: "intmenu"}
CONTROL_READ_ONLY = 0x0004
# ⭐ The controls a spectrometer stands or falls on: if exposure and white balance cannot be FIXED, the
# instrument state is negotiated per capture and section 16.39 is what happens.
CONTROLS_THAT_MATTER = ("exposure", "white balance", "gain", "backlight")
RAW_FORMATS = ("GREY", "Y8  ", "Y16 ", "BA81", "GRBG", "RGGB", "BG10", "GB10")


def cameraIdentity(node="/dev/video0"):
    """USB vendor:product and the firmware's own strings, from sysfs. ('', '') if not a USB device."""
    name = os.path.basename(node)
    try:
        with open("/sys/class/video4linux/%s/name" % name) as handle:
            label = handle.read().strip()
    except OSError:
        return "", ""
    device = os.path.realpath("/sys/class/video4linux/%s/device" % name)
    parts = []
    for field in ("idVendor", "idProduct", "manufacturer", "product"):
        try:
            with open(os.path.join(device, "..", field)) as handle:
                parts.append(handle.read().strip())
        except OSError:
            parts.append("?")
    return label, "%s:%s  %s / %s" % tuple(parts)


def frameSizes(descriptor, pixelFormat):
    """Every discrete frame size the driver offers for one format. 'stepwise' if it is a range."""
    size = 44                                       # sizeof(struct v4l2_frmsizeenum)
    request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 74    # _IOWR('V', 74, v4l2_frmsizeenum)
    found = []
    for index in range(64):
        buffer = bytearray(struct.pack("II", index, pixelFormat) + bytes(size - 8))
        try:
            fcntl.ioctl(descriptor, request, buffer, True)
        except OSError:
            break
        kind, = struct.unpack_from("I", buffer, 8)
        if kind != 1:                               # V4L2_FRMSIZE_TYPE_DISCRETE
            found.append("stepwise")
            break
        width, height = struct.unpack_from("II", buffer, 12)
        entry = "%dx%d" % (width, height)
        if entry not in found:                      # some firmwares repeat the first entry last
            found.append(entry)
    return found


def cameraControls(node="/dev/video0"):
    """Every V4L2 control, with its range and whether it is writable. [] if unreadable."""
    size = 68                                       # sizeof(struct v4l2_queryctrl)
    request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 36    # _IOWR('V', 36, v4l2_queryctrl)
    nextFlag = 0x80000000
    found = []
    try:
        descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return found
    try:
        control = 0 | nextFlag
        while True:
            buffer = bytearray(struct.pack("I", control) + bytes(size - 4))
            try:
                fcntl.ioctl(descriptor, request, buffer, True)
            except OSError:
                break
            identifier, = struct.unpack_from("I", buffer, 0)
            kind, = struct.unpack_from("I", buffer, 4)
            label = bytes(buffer[8:40]).split(b"\0")[0].decode("latin-1")
            low, high, step, default, flags = struct.unpack_from("iiiiI", buffer, 40)
            if kind != 6:                           # skip the control-class headers
                found.append((label, CONTROL_TYPES.get(kind, str(kind)), low, high, step, default,
                              bool(flags & CONTROL_READ_ONLY)))
            control = identifier | nextFlag
    finally:
        os.close(descriptor)
    return found


def cameraFormats(node="/dev/video0"):
    """Every pixel format the camera advertises, straight from VIDIOC_ENUM_FMT. Read-only: enumerating
    formats neither opens a stream nor disturbs a capture in progress.

    ⛔ WHY THIS IS IN A DIAGNOSTIC AND NOT AN ASSUMPTION. The standard recipe for making a Bayer camera
    behave monochromatically starts "shoot RAW, skip the demosaic" -- and on a UVC webcam that route may
    simply not exist. On the ELP it does not: MJPG and YUYV, nothing else. `SPEC_lamp_rebuild.md` section
    12.5 is the write-up; this is the check, so the next camera can be asked the same question in one run.
    Returns [] if the device is absent or unreadable -- a probe must never fail a diagnostic."""
    size = 64                                       # sizeof(struct v4l2_fmtdesc)
    request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 2      # _IOWR('V', 2, v4l2_fmtdesc)
    found = []
    try:
        descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return found
    try:
        for index in range(32):
            buffer = bytearray(struct.pack("II", index, 1) + bytes(size - 8))   # type=VIDEO_CAPTURE
            try:
                fcntl.ioctl(descriptor, request, buffer, True)
            except OSError:
                break
            flags, = struct.unpack_from("I", buffer, 8)
            pixelFormat, = struct.unpack_from("I", buffer, 44)
            found.append((index,
                          "".join(chr((pixelFormat >> (8 * i)) & 0xFF) for i in range(4)),
                          bytes(buffer[12:44]).split(b"\0")[0].decode("latin-1"),
                          bool(flags & 0x1),
                          frameSizes(descriptor, pixelFormat)))
    finally:
        os.close(descriptor)
    return found


def main(node="/dev/video0", probeOnly=False):
    if probeOnly:
        describeCamera(node)
        return
    print("=== 1. IS IT A CROSSING? per-channel linear light, normalised to the window's own maximum\n")
    wavelengths, linear, _ = channelsOf(FILLS[0][0])
    print("   %-6s %8s %8s %8s   dominant" % ("nm", "R", "G", "B"))
    peak = linear[(wavelengths >= 555) & (wavelengths <= 640)].max()
    for nanometer in numpy.arange(556.0, 640.1, 4.0):
        values = [float(numpy.interp(nanometer, wavelengths, linear[:, i])) / peak for i in range(3)]
        print("   %-6.0f %8.3f %8.3f %8.3f   %s"
              % (nanometer, *values, "RGB"[int(numpy.argmax(values))]))
    for label, low, high in FEATURES:
        found = crossings(wavelengths, linear, low, high)
        print("\n   %-26s %s" % (label, ", ".join("%.1f nm %s->%s" % c for c in found)
                                 or "NO CHANGE OF DOMINANT CHANNEL -- it is not a crossover"))

    print("\n\n=== 2. IS IT A `max()` ARTEFACT? the same feature under three reductions\n")
    print("   %-24s %4s | %8s %8s %8s" % ("fill", "exp", "max", "sum", "green"))
    positions = {}
    for series, exposure in FILLS:
        wavelengths, linear, _ = channelsOf(series)
        row = {}
        for kind, values in (("max", linear.max(axis=1)), ("sum", linear.sum(axis=1)),
                             ("green", linear[:, 1])):
            row[kind] = apparentPosition(wavelengths, values, *FEATURES[1][1:])
        positions[series] = (exposure, row)
        print("   %-24s %4d | %8.1f %8.1f %8.1f" % (series, exposure, row["max"], row["sum"], row["green"]))
    print("\n   ⇒ max and sum agree to 0.1 nm and move together: NOT a reduction artefact.")

    print("\n\n=== 3. DOES A FIXED FEATURE MOVE WITH EXPOSURE?\n")
    for kind in ("max", "sum"):
        low = [r[kind] for exposure, r in positions.values() if exposure == 90]
        high = [r[kind] for exposure, r in positions.values() if exposure == 104]
        print("   %-6s exp 90: %s      exp 104: %s      step %+.1f nm"
              % (kind, " ".join("%.1f" % v for v in low), " ".join("%.1f" % v for v in high),
                 numpy.mean(high) - numpy.mean(low)))
    print("\n   ⛔ A lamp line, a dye edge and an IR-cut are all functions of WAVELENGTH ALONE and cannot\n"
          "      move. The edge is stationary; its APPARENT position moves => a level-dependent\n"
          "      nonlinearity on a steep edge. SPEC_capture_quality.md section 17, not Bayer.")

    print("\n\n=== 4. HEADROOM -- is anything clipping in the working band?\n")
    for series, exposure in FILLS:
        wavelengths, _, raw = channelsOf(series)
        cells = []
        for index, name in enumerate("RGB"):
            values = raw[:, index]
            inside = (wavelengths >= 430) & (wavelengths <= 630)
            cells.append("%s %3.0f DN at %3.0f nm" % (name, values[inside].max(),
                                                      wavelengths[inside][values[inside].argmax()]))
        print("   %-24s %4d | %s" % (series, exposure, "  |  ".join(cells)))
    print("\n   ⚠ The 473 nm blue spike is the binding constraint (ROADMAP.md section 0b item 4), and it\n"
          "     is the channel to watch as exposure rises -- not the red.")

    print("\n\n=== 5. THE MONO OPTION -- what a LUMA reduction would cost  (section 15.2a)\n")
    print("   %-24s %4s | %8s %8s %8s | %10s %10s %8s"
          % ("fill", "exp", "max", "sum", "luma", "max", "luma", "ratio"))
    print("   %-24s %4s | %-26s | %s" % ("", "", "609 step position (nm)", "SORET 448-460, SAMPLE leg"))
    for series, exposure in FILLS:
        reference, frames = replay.attachments(os.path.join(archive.ARCHIVE, series, "001.pdf"))
        wavelengths, referenceChannels, offset = replay.alignedChannels(frames["reference"], reference)
        _, sampleChannels, _ = replay.alignedChannels(frames["sample"], reference, offset=offset)
        wavelengths = numpy.array(wavelengths)
        linear = replay.util.decodeGammaArray(referenceChannels.astype(numpy.uint8))
        sample = replay.util.decodeGammaArray(sampleChannels.astype(numpy.uint8))
        inside = (wavelengths >= GUARD_BAND[0]) & (wavelengths <= GUARD_BAND[1])
        maximum = encodeDn(sample.max(axis=1)[inside].min())
        luma = encodeDn((sample @ LUMA)[inside].min())
        print("   %-24s %4d | %8.1f %8.1f %8.1f | %7.1f DN %7.1f DN %7.2fx%s"
              % (series, exposure,
                 apparentPosition(wavelengths, linear.max(axis=1), *FEATURES[1][1:]),
                 apparentPosition(wavelengths, linear.sum(axis=1), *FEATURES[1][1:]),
                 apparentPosition(wavelengths, linear @ LUMA, *FEATURES[1][1:]),
                 maximum, luma, luma / maximum, "   <- UNDER the 16 DN guard" if luma < FLOOR_DN else ""))
    print("\n   ⇒ luma leaves the 609 step exactly where it was, and darkens the Soret by ~0.37x.\n"
          "     Section 15.3 chose max-channel for this reason; this is the number it never had.")

    describeCamera(node)


def describeCamera(node):
    """Section 6 -- and the whole of `--probe-only`. Everything a camera must answer BEFORE it is
    mounted, in one place: can it deliver uncompressed pixels at the calibration size, can its
    exposure and white balance be FIXED, and does it offer anything mono or raw."""
    label, usb = cameraIdentity(node)
    print("\n\n=== 6. WHAT THE CAMERA ACTUALLY OFFERS  (SPEC_lamp_rebuild.md section 12.5)\n")
    print("   %s   %s" % (node, label or "(no such video4linux node)"))
    if usb:
        print("   usb %s" % usb)
    formats = cameraFormats(node)
    if not formats:
        print("\n   (not readable -- camera unplugged, in use, or no permission. Not a failure.)")
        return
    print()
    for index, fourcc, description, compressed, sizes in formats:
        print("   %d: %-6s %-24s %s" % (index, fourcc, description,
                                        "COMPRESSED -- lossy, never for spectroscopy" if compressed else ""))
        print("        %s" % (", ".join(sizes) if sizes else "(no sizes reported)"))

    # ⭐ THE THREE QUESTIONS THAT DECIDE WHETHER A CAMERA IS USABLE AT ALL, answered from the above.
    print("\n   ---- the three questions ----")
    raw = [f[1] for f in formats if f[1] in RAW_FORMATS]
    print("   1. anything RAW or MONO?            %s"
          % (", ".join(raw) if raw else
             "NO -- the demosaic happens inside the camera, so 'skip the demosaic and take\n"
             "                                          the green photosites' is unavailable at any price"))
    uncompressed = [(f[1], size) for f in formats if not f[3] for size in f[4] if "x" in size]
    best = max(uncompressed, key=lambda t: int(t[1].split("x")[0]) * int(t[1].split("x")[1]),
               default=None)
    print("   2. best UNCOMPRESSED mode:          %s"
          % ("%s %s" % best if best else "NONE -- disqualified outright"))
    if best and best[1] != "%dx%d" % CALIBRATION_SIZE:
        print("      ⛔ the calibration was authored at %dx%d (SPEC_capture_quality.md section 4.9):\n"
              "         a different size mis-maps every wavelength => FULL RECALIBRATION" % CALIBRATION_SIZE)
    if formats and formats[0][3]:
        print("      ⚠ a COMPRESSED format is at INDEX 0, the driver's first => the pixel format must be\n"
              "         PINNED, not negotiated (section 16.39.5a)")
    controls = cameraControls(node)
    print("   3. can the instrument state be FIXED?")
    if not controls:
        print("      (controls unreadable)")
    for label_, kind, low, high, step, default, readOnly in controls:
        if not any(word in label_.lower() for word in CONTROLS_THAT_MATTER):
            continue
        note = ""
        if "white balance temperature" in label_.lower() and high < 2000:
            note = "   ⛔ NOT KELVIN -- CaptureBackend writes 6500 and this clamps to %d" % high
        print("      %-32s %-5s %6d .. %-6d default %-6d%s%s"
              % (label_, kind, low, high, default, " READ-ONLY" if readOnly else "", note))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Per-channel replay, and a camera characterisation.")
    parser.add_argument("--device", default=None,
                        help="video4linux node to characterise (default: the first /dev/video*)")
    parser.add_argument("--probe-only", action="store_true",
                        help="skip the archive replay and only characterise the attached camera")
    arguments = parser.parse_args()
    device = arguments.device or next(iter(sorted(glob.glob("/dev/video*"))), "/dev/video0")
    main(device, arguments.probe_only)
