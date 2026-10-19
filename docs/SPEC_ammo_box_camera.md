# SPEC — The cheap webcam in the ammo box (ROADMAP §0d H2) (DESIGN)

*Edwin, 2026-10-19: "let us now turn to the integration of the new spectrometer with the chinese 30$ web cam
(impl on explicite request only)".* **DESIGN ONLY. Nothing here is built until Edwin asks for it.**

**What this covers.** The ammo-box spectrometer (`spectracs-hardware/ammoBox-spec.md`) and its ~30 $ Chinese colour
UVC webcam. Today the app runs **only** on the ELP `32e4:8830`. This spec lists every place where the ELP is built
in, shows where the new camera fits into the domain model, and proposes how it becomes a second camera that is
**data, not code** (`SPEC_camera_settings.md`).

**Not covered.** H1, characterising the box (null run, σ_fill, the `Rv` threshold re-check), comes after this
spec. H3/H4 (Shelly identity and on-plug memory) has its own spec since 2026-10-19:
[`SPEC_shelly_instrument_memory.md`](SPEC_shelly_instrument_memory.md) (§5 here is the short version). The ToupTek IMX290 is not UVC, so it
is a separate project.

---

## 1 — Which camera: `2bc5:0529`, not the Microdia

⭐ **Edwin, 2026-10-19: the camera in the box is the `2bc5:0529`** (Orbbec's vendor id, firmware strings
`webcamvendor` / `webcamproduct`, null serial, USB 2.0). The first draft of this spec assumed the Microdia
`0c45:6366`, because `ammoBox-spec.md` §7.4 and `KB_cameras.md` §3 say so. Edwin owns **several cheap boards
that look the same**, and they can enumerate with **different** USB ids.

⇒ **Rule: one USB id = one sensor row.** The seeded `AUTOMAT` row (`0c45:6366`, "ThunderOptics") stays untouched.
The box camera gets its own row. If a look-alike board turns up with a third id, it gets a third row, and nothing
in the code changes.

⚠ `ammoBox-spec.md` §7.4 ("Kamera: zuerst Microdia") is therefore stale. It is in a non-git folder, so the
correction is Edwin's call.

### 1.1 P0 — does it deliver images? ✅ yes (2026-10-19, lamp off)

| | result | how |
|---|---|---|
| nodes | `/dev/video0`, `/dev/video1` (`webcamproduct: usb-webcam`) | sysfs |
| frames | ✅ **YUYV 1920 × 1080 pinned and read back**, 10 frames in a 5 s grab that includes the open; the frame is black (max DN 64) because the box was closed and the lamp off | `cv2` grab, the same calls `CaptureBackend` makes |
| formats | MJPG (up to 2560 × 1440), **YUYV (up to 1920 × 1080)**, NV12, H.264 | `channel_replay.py --probe-only` |
| RAW / mono | ⛔ none | same |
| controls | WB auto 0/1 (default **on**), **WB temperature 0–255, default 128, NOT Kelvin**, gain 0–100 (default 5), auto exposure menu 0–3, **exposure 0–6500 (default 100)** | same |

This matches `SPEC_lamp_rebuild.md` §12.5a (2026-08-30) exactly, so it is very likely the same board.
**Still unmeasured, and these need the lamp on:** the gamma of the delivered frame (`DOC_capture_fidelity.md` KB 1,
the DN 118 / DN 46 test), how many frames it takes to settle after the open and after an exposure step, the real
frame rate at 1920 × 1080 (§12.5a estimated ~8 fps), and whether exposure gets brighter or darker as the value goes
up (the ELP's is inverted).

## 2 — The domain model today

```
                                    ┌──────────────────────────┐
                                    │ AppUser                  │
                                    │  username, role          │
                                    │  registeredSerial ───────┼──┐ soft link, by value
                                    └──────────────────────────┘  │
                                                                  ▼
 ┌─────────────────────┐ 1   1 ┌───────────────────────────────────┐ *   1 ┌─────────────────────────────┐
 │ SpectrometerSetup   │──────▶│ SpectrometerProfile = INSTRUMENT  │──────▶│ SpectrometerCalibration-    │
 │ (assignment)        │       │  serial  "ELP-0001"               │       │ Profile                     │
 └──────────┬──────────┘       └────────────────┬──────────────────┘       │  ROI x1,y1,x2,y2  (pixels)  │
            │ *                                 │ *                        │  px→nm cubic A,B,C,D        │
            ▼ 1                                 ▼ 1                        │  calibrationSpectrumJson    │
 ┌─────────────────────┐       ┌───────────────────────────────────┐       │  ⛔ no resolution            │
 │ DbPlugin            │       │ Spectrometer = MODEL              │       └──────────────┬──────────────┘
 │  codeRef, version   │       │  modelName "InVision"/"InLight"/  │                      │ 1
 │  source, signature  │       │            "Phantom"              │                      ▼ *
 │  (e.g. DevSpectral- │       └───┬──────────────┬────────────┬───┘              ┌───────────────┐
 │   Plugin: exposure  │           │ *            │ *          │ *                │ SpectralLine  │
 │   90 in ELP units)  │           ▼ 1            ▼ 1          ▼ 1                └───────────────┘
 └─────────────────────┘  ┌─────────────────┐ ┌──────────┐ ┌───────────┐
                          │SpectrometerSensor│ │ Vendor   │ │ Style     │
                          │ = CAMERA         │ └──────────┘ └───────────┘
                          │ vendorId:modelId │
                          │ codeName, virtual│
                          └────────┬─────────┘
                                   │ * → 1
                          ┌────────▼─────────┐
                          │ SensorChip       │
                          └──────────────────┘

 IN CODE, not in the DB:
   SpectrometerSensorUtil.__CAPTURE_SETTINGS_BY_HARDWARE_ID["32e4_8830"] → SpectrometerSensorSettings(calibrationExposure=150)
   CaptureBackend: 2592×1944 YUYV           CameraProfile: WB 6500 K, backlight 0, gain 0
   SpectralColorUtil: decode pow 2.2        VideoThread: settle 4 frames
```

Three things to read off it:
- **The instrument is `SpectrometerProfile`.** It is one physical unit with a serial, a model and *its own*
  calibration. `SpectrometerSetup` says which plugin that instrument runs. A user is bound to an instrument by its
  serial.
- **The camera (`SpectrometerSensor`) is a type, not a unit.** Every ELP shares one row. The *unit's* facts (where
  the spectrum lies on its sensor) live in the calibration profile.
- **How a camera is driven is code, keyed by `vendorId_modelId`.** That is the right place, since the set of
  cameras is small and known. But today only part of it is keyed: the resolution, decode and settling are
  global constants.

## 3 — The domain model with the box camera

```
 ┌─────────────────────┐       ┌───────────────────────────────────┐       ┌─────────────────────────────┐
 │ SpectrometerSetup   │──────▶│ SpectrometerProfile               │──────▶│ SpectrometerCalibration-    │
 │  plugin = DevSpec-  │       │  serial  ★ later from the Shelly  │       │ Profile  (authored LATER,   │
 │  tralPlugin         │       │          (§5, H3/H4)              │       │           on the box)       │
 └─────────────────────┘       └────────────────┬──────────────────┘       │  ROI, cubic                 │
                                                │                          │ ★ captureWidth  1920        │
                                                ▼                          │ ★ captureHeight 1080        │
                               ┌───────────────────────────────────┐       └─────────────────────────────┘
                               │ Spectrometer ★ NEW ROW            │
                               │  "InLight" (Edwin 2026-10-19)     │
                               └────────────────┬──────────────────┘
                                                ▼
                               ┌───────────────────────────────────┐
                               │ SpectrometerSensor ★ NEW ROW      │
                               │  2bc5:0529 (Orbbec), codeName     │
                               │  DYNAREX (Edwin 2026-10-19)       │
                               └───────────────────────────────────┘

 IN CODE, keyed by hardware id — SpectrometerSensorSettings grows:

   hardwareId   captureWidth×Height  pixelFormat  captureGamma  settlingFrames  calibrationExposure  frozen overrides
   ──────────   ───────────────────  ───────────  ────────────  ──────────────  ───────────────────  ──────────────────
   32e4_8830    2592×1944            YUYV         2.2           4               150                  —
   2bc5_0529    1920×1080            YUYV         ? (lamp on)   ? (lamp on)     ? (calibration)      WB temp = ? (0–255)

 IN THE PLUGIN — cameraSettings(deviceDefaults), deviceDefaults now carries "hardwareId":

   DevSpectralPlugin:   {"32e4_8830": {"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500},
                         "2bc5_0529": {"EXPOSURE": ?,  "WHITE_BALANCE_TEMPERATURE": ?}}[hardwareId]
                         unknown camera ⇒ no pin, the operator's slider / AE decides, record says so
```

★ = new. Nothing else in the model changes.

## 4 — Where the ELP is built in, and the fix

| # | where | ELP-specific | on the box camera | fix |
|---|---|---|---|---|
| E1 | `CaptureBackend.py:218-219`, `:408-409` | **2592 × 1944**, hard-coded (`:204` already has the TODO) | it has no such mode ⇒ V4L2 snaps to some other one | D1: the mode comes from the sensor settings |
| E2 | `CaptureBackend.__forceUncompressed` | forces YUYV | ✅ works; YUYV 1920 × 1080 is available | — |
| E3 | `SpectrometerCalibrationProfile` | no record of the resolution | see D2 | D2 |
| E4 | `SpectrometerSensorUtil` settings | only ELP keyed | falls back to 150, an ELP value | D1 |
| E5 | `CameraProfile._FROZEN` | `WHITE_BALANCE_KELVIN: 6500` | ⛔ **WB is 0–255; 6500 clamps to 255 ⇒ read-back ≠ request ⇒ Q4 refuses every MEASUREMENT** | D4 |
| E6 | `DevSpectralPlugin.py:965-967` | `exposure = 90`, ELP units | 90 of 0–6500 is a different light level | D5 |
| E7 | `SpectralColorUtil` | global `pow 2.2` | unknown | D6 |
| E8 | `VideoThread.py:32, :55` | settle 4 frames | unknown | D7 |
| E9 | `CapturePanel.py:78`, `DevCaptureViewModule.py:44` | slider 0–5000 | range 0–6500 | read the range from the device |
| E10 | `UserSeedLogicModule.py:36-52` | seeds only `ELP-0001` | no box instrument | D8 |
| E11 | plugin constants (`Rv` T, bands, 630 clamp) | fitted on the ELP **with its 642 nm IR-cut** | not portable | **H1**, not here |

## 5 — Decisions

| # | decision | status |
|---|---|---|
| D1 | capture mode, pixel format, gamma and settling move into `SpectrometerSensorSettings`, keyed by hardware id. A camera without a mode **refuses to open** (the R8 rule, no silent fallback) | proposal |
| D2 | the calibration profile records the resolution it was authored at, see below | proposal, open |
| D3 | only uncompressed (YUYV) for a measurement, never MJPG/H.264, even though MJPG goes up to 2560 × 1440 | settled by §16.39.5a |
| D4 | a profile control the device does not have, or has in other units (WB 0–255), is replaced by the camera's own value from the sensor settings; the 6500 K stays for cameras that speak Kelvin | proposal |
| D5 | **the plugin declares exposure (and WB) per camera**, chosen by the `hardwareId` handed to `cameraSettings()`. No SDK signature change, so the signed v1 rows keep loading | ✅ **Edwin likes it** (2026-10-19) |
| D6 | the gamma decode is per camera and stamped into `captureDecode` | proposal |
| D7 | settling frames per camera | proposal |
| D8 | the box becomes an instrument through the master UI, with its **own** calibration (never the ELP's). Serial: postponed, see the Shelly topic | ⏸ postponed |

**D2 in plain words.** The calibration says, for example, *"the 450 nm line is at column 812"*. That is only true
at the resolution the calibration was made at. If the camera delivers 1920 columns instead of 2592, column 812 is
a different wavelength, and every number downstream is wrong **without any error**. Today the calibration profile
does not say "made at 2592 × 1944", so the app cannot notice. The proposal: write the size into the profile when
calibrating; on every open, compare it with the camera's mode and refuse if they differ. The existing ELP profiles
get 2592 × 1944 written in, because that is how they were made. The alternative is the existing check "ROI lies
outside the frame", which only catches a frame that is *smaller*. ⇒ It matters the moment the box is calibrated,
and it protects the ELP from the same mistake.

## 6 — Phases, in Edwin's order

```
 ┌─────┬──────────────────────────────────────┬──────────────┬──────────────────────────┬──────────────────────────┐
 │  #  │ what                                 │ code?        │ needs                    │ status                   │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P0  │ does the camera deliver images?      │ none         │ the camera               │ ✅ 2026-10-19 (§1.1)     │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P1  │ ★ the Shelly as the instrument's     │ own spec     │ the plug                 │ designed, S0 run 10-19   │
 │     │ memory: SPEC_shelly_instrument_mem.  │              │                          │                          │
 │     │ a factory tool writes setup, user    │              │                          │                          │
 │     │ and plugin onto the plug (KVS +      │              │                          │                          │
 │     │ script slots)                        │              │                          │                          │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P2  │ measure with the lamp on: gamma,     │ diagnostics  │ lamp + box               │ open                     │
 │     │ settling, fps, exposure direction    │ only         │                          │                          │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P3  │ camera settings per camera:          │ app + core   │ P2's numbers             │ open                     │
 │     │ D1, D4, D5, D6, D7, slider range     │ + plugin row │                          │                          │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P4  │ the box as an instrument: sensor +   │ model (+ D2: │ P1 (serial)              │ open                     │
 │     │ model rows, D2 resolution guard      │ Alembic)     │                          │                          │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P5  │ wavelength calibration on the box    │ none (rig)   │ P3, P4                   │ LATER (Edwin)            │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P6  │ Windows: the same in the VM          │ app          │ P3                       │ open                     │
 ├─────┼──────────────────────────────────────┼──────────────┼──────────────────────────┼──────────────────────────┤
 │ P7  │ click-through: reference + sample,   │ none (rig)   │ P5                       │ open                     │
 │     │ PDF shows the camera table + decode  │              │                          │                          │
 └─────┴──────────────────────────────────────┴──────────────┴──────────────────────────┴──────────────────────────┘
   then H1 — characterise the box (its own archive, never pooled with the ELP's 98 runs)
```

## 7 — Open questions

1. **D2:** resolution columns on the calibration profile (§5, plain-words paragraph): yes or no?
2. ✅ **Decided 2026-10-19 (Edwin):** the Shelly topic (P1, factory provisioning / instrument memory) gets **its own
   spec**, not a section in `SPEC_lamp_switch.md`. ⇒ [`SPEC_shelly_instrument_memory.md`](SPEC_shelly_instrument_memory.md).
3. `ammoBox-spec.md` §7.4 still says "zuerst Microdia". Correct it to `2bc5:0529`?
