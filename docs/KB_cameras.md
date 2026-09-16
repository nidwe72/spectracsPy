# KB — Cameras

*The detector is half the instrument. This note holds what each camera on the roster actually is, what
its optical path does to the spectrum, and what changing camera would cost and buy. Written 2026-09-04,
after the halogen measurement in `KB_lamps.md` §4 turned "the camera's red response" from an assumption
into a number. Updated 2026-09-17: the ToupTek was bought, and its driver library is read in §4.6.*

Companions: `KB_lamps.md` (the light source, and the measurement this note builds on),
`KB_spectroscopy_physics.md` §7 (the physical instrument), `SPEC_real_camera_capture.md` (the capture
wiring), `SPEC_capture_quality.md` §16 (the error budget), `SPEC_dev_capture_view.md` (the view every
measurement here was taken in).

<!--TOC-->

---

## 0 · ⭐⭐⭐ The answer up front: a better sensor does NOT fix the pumpkin measurement

*(Edwin, 2026-09-04: "isn't it that the biggest problem we have is sample preparation and a noise
floor?" — it is, and this section is the arithmetic that settles it. Recorded here so the camera
question is never re-opened on the wrong grounds.)*

**The whole instrument — camera, lamp, optics, quantisation, every electronic term — contributes 0.063
Q% units.** That is `DevSpectralPlugin.SINGLE_WINDOW_SIGMA`: the standard deviation of `Q%` over ten
repeats with the jar untouched (`SPEC_capture_quality.md` §16.36.6). Against it:

| what is being measured | Q% units | × the instrument |
|---|--:|--:|
| **the entire instrument, jar untouched** | **0.063** | 1× |
| second pour of the same dilution (§36) | 0.076 | 1.2× |
| clean set, aliquots kept dark (§40) | 0.198 | 3.1× |
| **σ_fill — five separate preparations** (§28) | **0.276** | **4.4×** |
| archive within-fill scatter (§28) | 1.255 | 19.9× |

⇒ ⭐⭐⭐ **A PERFECT detector — zero read noise, infinite bit depth, no Bayer array, no IR-cut — would
improve σ_fill by 2.6 % and the archive scatter by 0.1 %.** Not "12-bit buys 2.6 %": *anything* confined
to the instrument floor buys at most that, because √(0.276² − 0.063²) = 0.269 and no detector change can
subtract more than the whole floor. **This is an upper bound on every camera upgrade ever proposed, and
it needs no model of the new camera at all.**

⚠ **AMENDED 2026-09-04 by §4.1b** — the sentence below holds for `Q%` and **not** for `Rv`, whose
denominator is ~5× smaller and which is quantisation-limited. Read the two together.

⛔ **So the monochrome/12-bit case must not be made on measurement quality.** §4.1a re-quantised 225
archived runs to check the specific claim: quantisation contributes at most 0.063 and 12 bits shrinks it
3.1×. Real, and irrelevant. Mono's ~3× photon gain is a better argument than the bits — photon noise is
genuinely in the floor — but it is subject to the identical 2.6 % ceiling.

⭐ **What a camera change IS for, then:** buying **spectral range** that does not exist today (§4.2–4.5),
and unlocking two things the clamp forbids — **normed chlorophyll methods** (§4.5b narrows those to
exactly one, needing **710 nm**) and ⭐⭐ **any COLOUR number at all** (§4.5d: `x̄` is **11 % truncated at
632.6 nm and 0.2 % at 690.8**, so a tristimulus integral goes from impossible to essentially complete).
Those are capability arguments, not precision arguments. ⚠ **Judge any camera proposal by which of the
two it is making** — and note that both of the capability arguments are about the RED END, not the
sensor.

⇒ **The measurement is gated on the fill, not the detector.** `SPEC_settled_measurement.md` is where the
4.4× lives, and until its one-fill/capillary work lands, no detector purchase moves the verdict.

## 1 · The roster, at a glance

| | **ELP `32e4:8830`** | **Microdia/Sonix `0c45:6366`** | **ToupTek GPCMOS02000KMA** |
|---|---|---|---|
| role | bench / dev — **the archive camera** | intended **production** camera | ⭐ **bought 2026-09-17** — ⚠ not yet plugged in or characterised |
| sensor | Sony IMX179 (inferred) | unrecorded | **Sony IMX290LLR mono** |
| colour | Bayer RGB | Bayer RGB | ⭐ **monochrome** |
| native | 3264 × 2448 (8 MP) | unrecorded | 1945 × 1097 (2.13 MP) |
| captured at | **2592 × 1944** (pinned) | ⛔ not wired | 1920 × 1080 — the only mode the driver lists (§4.6) |
| pixel pitch | 1.4 µm native | unrecorded | **2.9 µm** |
| imaging width | 3.63–4.57 mm (§4.1) | unrecorded | **5.57 mm** |
| bit depth | **8** | **8** | ⭐ **12** |
| transfer curve | ⚠ gamma-encoded (`pow2.2`) | ⚠ gamma-encoded | ⭐ **linear raw** |
| IR-cut filter | ⛔ **YES — measured, λ₅₀ = 641.8 nm** | ⭐ **NO** (remote test) | ⭐ **NO** — AR-coated clear window, IR-transmitting |
| red reach | 62 DN @ 650, 17 DN @ 660 nm | ⚠ **unmeasured** | ⚠ **unmeasured** |
| interface | UVC / V4L2 → `cv2` | UVC / V4L2 → `cv2` | ⛔ **proprietary `libtoupcam` SDK** (USB `0547:10ff` or `0547:1368`, §4.6) |
| mount | M12 (S-mount) | M12 | 1.25" barrel + C-mount adapter |
| price class | ~€60 | ⭐ cheap — the reason it is the production part | ~€180–230 |

⭐ **The single most important row is the IR-cut row**, and it is the one that was assumed rather than
known until 2026-09-04.

![**Figure 1** — what each camera can reach, and why the three limits are different kinds of limit. Solid = measured. Hatched = projected, never measured. The faded tail is signal present but below the 16 DN working floor. Only the silicon bandgap at ~1100 nm is a law of physics; the other two boundaries are purchasing decisions.](figures/camera_reach.svg)

## 2 · ELP `32e4:8830` — the bench unit, and what the archive was captured through

**Identity.** `CaptureBackend` records the sensor maximum as **3264 × 2448** and pins capture to
**2592 × 1944**. 8 MP at 4:3 in that size is the **ELP-USB8MP02G** class, i.e. **Sony IMX179**, 1.4 µm
pixels. ⚠ *Inferred from the resolution — there is no datasheet or invoice in the repo, and
`KNOWLEDGE_BASE.md` §8 calls it "ELP 4K", which does not fit 3264 × 2448.* Worth confirming from the
purchase record.

**Why 2592 × 1944 is pinned, and must stay pinned.** `CaptureBackend.py` carries the full argument: the
ROI corners and the px→nm cubic on `SpectrometerCalibrationProfile` were **authored at that size**, so any
other capture size mis-maps every wavelength. Not the sensor maximum either — that would need a
recalibration and is slower still (~1.5 fps at 2592 over USB 2). ⚠ The file's own
`TODO: make this per-sensor ... when a second camera lands` is now due (§5).

**⛔ It has an IR-cut filter, and the edge is measured.** `KB_lamps.md` §4: dividing a 60 W halogen frame
by Planck leaves the instrument response, which carries a dielectric edge at **λ₅₀ = 641.8 nm, 10→90 %
over 16.5 nm** — 641 ± 1 nm under every decode assumption and filament temperature. At 650 nm ~82 % and at
660 nm ~87 % of the attenuation is that edge; everything else costs under 2× across 620–660 nm.

**⚠ Two artefacts this camera imprints on every archived spectrum.** Both are the Bayer array, not the
sample:

| | |
|---|---|
| **max-channel notches** | The reduction takes the maximum of R, G, B, so where two channels hand over the maximum dips. Measured at **B=G 486.2 nm** and **G=R 581.0/581.5 nm** on two different lamps. The 581 one is why `KB_spectroscopy_physics.md` §4.1a reads the Q band at 568 nm rather than 574 |
| ⭐ **and they are useful** | Being a property of the colour filters, they are a **free wavelength-scale check** — no calibration lamp needed. Two lamp families agreeing on both to 0.5 nm is what pins the scale in `KB_lamps.md` |

**⛔ Do not modify this unit.** Removing an IR-cut filter shifts the focal plane by ≈ *t*(1−1/n) — about
0.3 mm for 1 mm of glass — so the lens must be refocused, refocusing an M12 lens changes magnification,
and changed magnification changes dispersion ⇒ **a full recalibration**, which breaks registration with
the ~98-run archive that every fitted metric constant rests on.

## 3 · Microdia/Sonix `0c45:6366` — the production camera, and the surprise

`KB_spectroscopy_physics.md` §7 records this as *"the cheap Chinese cam intended for the production
batch"*. Almost nothing else about it is written down: no resolution, no calibration profile (the second
`spectrometer_calibration_profile` row is all NULL), and `CaptureBackend` has no branch for it.

⭐⭐ **But it has no IR-cut filter.** Edwin ran the remote test on 2026-09-04: in the dark it shows **a
white dot with a purple/violet halo**.

> **The halo is the diagnostic, not the dot.** A silicon sensor's three Bayer dyes all become transparent
> in the near infrared, so an unfiltered sensor renders an 850/940 nm source as white with a colour
> fringe — every channel responding at once. A camera *with* an IR-cut returns nothing, or a dim dot with
> no colour fringe.

⇒ **The production camera does not share the ELP's 642 nm wall.** That re-opens the deep-red half of
`DOC_lamp_410_680.md` §5.4/§7.3 for the shipped product, and it means the de-filtered camera that
`KB_lamps.md` §7 wanted to buy is **already on the bench**.

⚠ **What is not established:** "no IR-cut" ⇒ "good 660–690 nm response". Removing the *edge* leaves
silicon QE and the red dye, which are near plateau there, so a good response is *expected* — expected is
not measured. **The measurement is `KB_lamps.md` §7.1 and it is the cheapest open experiment in the
project**: halogen → this camera → look at the raw red end for a cliff. A 16 nm collapse is scale-free,
so step 1 needs no calibration at all.

⚠ **And two risks appear only once the filter is gone**, neither of which the ELP data can speak to:
**stray NIR scatter** raising the floor across the whole band, and **second-order diffraction** (§4.3).

## 4 · ⭐ ToupTek GPCMOS02000KMA (IMX290 mono) — bought 2026-09-17

Sold as an astronomical **guiding** camera — which is exactly why it is interesting here, because guide
cameras are built to keep near-infrared rather than throw it away.

⚠ **Bought on 2026-09-17, not yet on the bench.** Everything in §4.1–4.5 was written while it was only a
candidate and is unchanged by the purchase. §4.6 adds what its driver library can do, read from the SDK
itself. Nothing in this section has been measured on our unit yet.

| item | value | source |
|---|---|---|
| sensor | Sony **IMX290LLR**, 1/2.8", back-illuminated (STARVIS), **monochrome** | Sony / vendor |
| effective pixels | 1945 × 1097 (~2.13 MP); camera outputs 1920 × 1080 | Sony datasheet |
| unit cell | **2.9 µm** square | Sony datasheet |
| active area | **5.57 × 3.13 mm**, diagonal 6.39–6.46 mm | vendor / Sony |
| ADC | **12 bit** | vendor |
| peak QE | ~81 % | vendor |
| read noise | 0.53–0.84 e⁻ — ⚠ ZWO's chart for the same sensor shows 1–3.2 e⁻ | vendor / ZWO |
| full well | ~11 200 e⁻ (ZWO: 14.6 k e⁻ at 3.6 e⁻/ADU) | vendor / ZWO |
| exposure | **0.105 ms – 1000 s** | vendor |
| frame rate | ~16–18 fps at full resolution (USB 2.0), ⚠ an 8-bit figure — RAW12 is 2 bytes/pixel, so ~9 fps full frame is the bandwidth estimate | vendor / arithmetic |
| window | ⭐⭐ **AR-coated clear glass, "also transparent in the infrared"** | vendor |
| mount | 1.25" barrel; C-mount and CS-mount adapters | vendor |
| back focus | 8.5 mm (1.25"), 17.5 mm (C), 12.5 mm (CS) | vendor |
| interface | USB 2.0 + ST-4; ⛔ **`libtoupcam` SDK, not UVC** | vendor / SDK docs |
| mass | 70 g | vendor |

### 4.1 What it would buy — and what it would NOT

⚠ **12-bit linear raw removes a whole class of complexity — but NOT a whole class of error.** The
current chain is built around an 8-bit gamma-encoded frame: the quantisation window in
`ImageSpectrumAcquisitionLogicModule`, the `__TIE_WINDOW_CODES` tie-breaker, the low-DN guard at 16 DN
(§16.23.10f), the `pow2.2` decode and §17's "decode before you average" rule. A linear 12-bit sensor
makes all of that unnecessary, and the MAD==0 collapse (`spectracs-mad-zero-collapse`) could not occur.

⛔⛔ **What it would NOT do is make the verdict meaningfully more repeatable, and an earlier draft of this
section wrongly implied it would.** `diagnostics/bit_depth_gain.py` re-quantises **225 archived runs**
onto both grids and recomputes `Q%`. See §4.1a. The short version: **quantisation contributes at most
0.063 Q% units — the entire jar-untouched floor — and removing it improves σ_fill by 2.6 %.**

#### ⭐⭐ 4.1a How much is bit depth actually worth — measured on 225 archived runs

*(Added 2026-09-04 after Edwin's challenge: "isn't it that the biggest problem we have is sample
preparation and a noise floor?" — it is, and here is the arithmetic.)*

`diagnostics/bit_depth_gain.py` takes each archived report's stored **linear** reference and sample,
re-quantises **both** onto today's 8-bit gamma grid and onto a 12-bit linear grid, and recomputes
`Q% = −100·(A_valley − A_Q)/A_Soret`. 225 runs, `Q%` spanning −14.9 to 39.9.

| grid | mean \|shift\| | sd | 95th pct | max |
|---|--:|--:|--:|--:|
| 8-bit gamma | 0.0517 | **0.0668** | 0.1270 | 0.2360 |
| 12-bit linear | 0.0055 | **0.0215** | 0.0094 | 0.2853 |

⇒ 12 bits shrinks the quantisation term **3.1×**. ⚠ These are a **no-dither worst case**: archived values
are the mean of 60 frames, so real capture dithers and the true term is smaller.

⭐ **The simulation's own sanity check gives a better bound than the simulation does.** 0.0668 *exceeds*
the measured jar-untouched floor of **0.063** (`DevSpectralPlugin.SINGLE_WINDOW_SIGMA`, §16.36.6) — and
it cannot, because quantisation is one *component* of that floor. That over-shoot is positive evidence
that capture dithers, and it hands us a model-free ceiling: **quantisation contributes at most 0.063 Q%
units, because that is the entire spread of ten repeats with the jar untouched.**

Granting 12-bit that entire ceiling — the most generous case it could ever claim:

| what is being measured | today | with 12-bit | gain |
|---|--:|--:|--:|
| second pour of the same dilution (§36) | 0.076 | 0.043 | 44 % |
| clean set, aliquots kept dark (§40) | 0.198 | 0.188 | **5.2 %** |
| **σ_fill — five separate preparations** (§28) | **0.276** | 0.269 | **2.6 %** |
| archive within-fill scatter (§28) | 1.255 | 1.253 | 0.1 % |

⇒ ⭐⭐ **Edwin is right. The bit depth is not where the error is.** Preparation and re-seating dominate by
4–20×, and `SPEC_capture_quality.md` §16.26 already measured that directly: instrument floor **0.42 %**
against a jar re-seat of **median 1.7–3.0 %, max 14.4 %**. Buying 12 bits to improve the verdict would
be **spending on the smallest term in the budget.**

#### 4.1b ⚠ And gamma is not merely a nuisance — it spends codes where they are needed

One code, as a percentage of the level, with the reference parked at 90 % of full scale:

| A | sample level | 8-bit gamma | 12-bit linear | 12-bit is |
|--:|--:|--:|--:|---|
| 0.5 | 64.26 | 1.62 % | 0.10 % | 16.7× better |
| 1.0 | 20.32 | 2.74 % | 0.31 % | 9.0× better |
| 1.5 | 6.43 | 4.66 % | 0.97 % | 4.8× better |
| 2.0 | 2.03 | 7.92 % | 3.06 % | 2.6× better |
| 2.5 | 0.64 | 13.56 % | 9.69 % | 1.4× better |
| 3.0 | 0.20 | 23.44 % | 30.64 % | ⛔ 0.8× **worse** |

⭐ **This is why 8 bits has held up as well as it has**: `pow2.2` concentrates codes at the dark end,
which is exactly where an absorbance measurement lives. A *linear* 12-bit grid is uniform, so it wins by
3–10× through the working range but actually **loses past A ≈ 3.3** — where the bin is dead on any grid.

⇒ **Where 12-bit genuinely earns its place is the STARVED regime**, not the verdict: bins at 2–7 DN,
where one code is 8–23 %. That is the regime §7.13 measured as producing a *concentration-dependent
compression* that corrupted `r_Q`, the regime that forced the dilution-protocol change, and the regime
the **red extension would put us back into** (the halogen gives 62 DN at 650 nm but 17 DN at 660).
⭐ So bit depth is an enabler for **new range**, not an improvement to the **existing verdict**.

⛔⛔ **AND IT DOES NOT REMOVE THE EXPOSURE TILT — measured 2026-09-04, §4.1b.** The obvious remaining
argument for mono was that a colour camera's three channels carry three different curves, so a level change
tilts the colour balance and moves the numbers. It does not: the tilt is ONE shared transfer curve, and a
mono sensor reproduces it exactly. What removes it is **raw-linear output**, which is a property of having
no ISP — not of lacking a Bayer filter.

⭐ **Monochrome removes the Bayer array**, and with it: the two max-channel notches (§2), the ~3× light
loss to the colour filters, the demosaic, and the red dye's own roll-off. ⚠ It also removes the free
wavelength-scale check the crossovers provide — the CFL becomes the only scale reference.
⚠ ⭐ The ~3× light gain is worth more than the bit depth: it is a **photon** gain, and photon noise is a
real term in the floor, whereas quantisation demonstrably is not.

⭐ **The 1.25" barrel is a filter thread.** An order-sorting long-pass filter (§4.3) screws straight in.
That is a genuinely lucky mechanical fit for the one hard requirement of NIR work.

#### ⭐⭐⭐ 4.1b What mono buys, what RAW buys, and what BITS buy — measured, and they are three different things

*(Added 2026-09-04 after Edwin's question: "could it be that the BW camera is much better not due to
quantization, but due to the fact that on a color camera exposure changes shift the color hues much and thus
values?" The full derivation is `SPEC_capture_quality.md` §16.41; `diagnostics/transfer_curve.py` and
`diagnostics/level_sensitivity.py` are the two probes.)*

**The hypothesis is testable and the archive answers it.** Across an exposure step the per-bin gain
`DN_high/DN_low` falls monotonically from ~1.24 at DN 30–45 to ~1.077 at DN 190–245 — **13–17 %**, against
**1.6–4.3 %** for same-exposure controls — while the spread *between channels at equal DN* is **1.25–3.16 %**
against the controls' **1.33–3.11 %**, i.e. the same distribution. Per-column hue shifts 0.72–1.00° against
the controls' 0.23–0.46°.

⇒ ⛔ **it is a LEVEL effect, not a hue effect.** The measured local exponent `e = dlnDN/dlnX` runs
**2.00 → 0.41** from DN 20 to DN 235 (a raw-linear sensor is `e = 1` everywhere). A mono sensor sees exactly
the same curve.

**What each property is actually worth**, for a 10 % light change, on the 72 archived runs where `Rv` is
readable — median |shift| in metric units:

| metric | typical | the encoding curve | 8-bit requantisation | ⇒ which camera property helps |
|---|--:|--:|--:|---|
| `Q%` | 17.47 | **0.204** (0.74 σ_fill) | 0.046 | **raw-linear** |
| `Rv` | 102.43 | 0.182 | **1.028** (~5× its read noise) | ⭐ **12-bit** |
| `RvLin` | 91.99 | 0.881 | 1.488 | both, and it is worst on each |
| Soret/Q raw | 3.75 | 0.008 | 0.003 | neither — near-immune |

⭐⭐ **This is the one place §4.1a's conclusion does not transfer.** That section priced bit depth on `Q%`
and found it irrelevant — correct, and the null arm here agrees (0.046). But `Rv`'s denominator
`A_Q − A_valley` is ~19 % of `Q%`'s `A_Soret`, so the same code error is ~5× larger. **If `Rv` or `RvLin`
are ever to carry a threshold, that is a bit-depth argument, and it is a different argument from the range
one.**

⛔ **Raw is not reachable in software.** Raw Bayer output is not part of the UVC specification — the onboard
ISP demosaics, gamma-corrects and white-balances before the host sees anything — so there is no linear data
to recover on the ELP or the Microdia. ⭐ The ToupTek gets there by not being UVC at all (§4.3 blocker 2 is
the same fact, seen from the cost side), and so would a **raw colour** machine-vision camera.

⚠ **What has NOT changed:** §0's ceiling. σ_fill is 4.4× the whole instrument floor, the level term on `Q%`
is 0.74 σ_fill, and the §16.39.5 exposure pin already removes it for free. **This is still a capability
argument, not a precision one** — it just now has a second capability (linearity) beside the range.

### 4.2 Coverage arithmetic — how much spectrum fits on 5.57 mm

With the optics unchanged, the span a sensor holds is its **imaging width × the dispersion in nm/mm**.
The ELP ROI holds 290.8 nm across 2055 of 2592 columns, so the full ELP frame holds **~367 nm**:

| if the 2592 mode is… | ELP frame width | dispersion | IMX290 span | starting at 400 nm |
|---|---|---|---|---|
| a **crop** (1.40 µm pitch) | 3.63 mm | 101.1 nm/mm | 563 nm | **400–963 nm** |
| a **scale** (1.76 µm pitch) | 4.57 mm | 80.3 nm/mm | 447 nm | **400–847 nm** |

⚠ **Which one is unresolved** — nobody has recorded whether the ELP's 2592 × 1944 mode crops or downscales
the 3264 × 2448 array. It is one `v4l2-ctl --list-formats-ext` away.

⇒ **One IMX290 frame covers roughly 400–850 … 400–960 nm at today's dispersion.** To *guarantee* 400–1000
(a 600 nm span) needs 107.8 nm/mm — spreading the spectrum **7–34 % less tightly**, via a coarser grating
or a shorter focal length.

⭐ **That is affordable, because the instrument massively oversamples.** The optical resolution is ~2 nm
(the Hg 576.96 / 579.07 doublet is *marginally* resolved at ~14 px), while sampling is 0.14 nm/px on the
ELP and would be 0.23 nm/px on the IMX290 — roughly **10× finer than the optics deliver** in both cases.
Fewer, larger pixels cost nothing here; the slit and the grating are the limit, not the detector.

### 4.3 ⛔ The blockers, in the order they would bite

**1. ⛔⛔ Order overlap — this is the real one, and it is not optional.** A grating sends 2nd order of
400 nm to the same place as 1st order of 800 nm. Any instrument spanning 400→1000 nm therefore has the
blue end **folded on top of** the infrared end. It must be fixed with an **order-sorting long-pass
filter** (an OG/RG-type glass, e.g. ~695 nm) covering the red half, or by taking two exposures — one
plain, one long-passed — and splicing. ⭐ The 1.25" filter thread makes this trivial mechanically.
⛔ Ignore it and the NIR readings are pure artefact, silently.

**2. ⛔ It is not a UVC camera.** ToupTek uses a proprietary **`libtoupcam`** SDK on Linux;
`cv2.VideoCapture` will not see it. `CaptureBackend` is V4L2-only, so this needs a **second backend
implementation**. Not fatal — the SDK ships Linux `.so` builds and there is a third-party GStreamer
element — but it is real work, and ⚠ it is hostile to the **Android port** (`SPEC_android_port.md`),
where a vendor `.so` plus USB permissions is a much worse story than a UVC device.

⚠ **AMENDED 2026-09-17 by §4.6.7 — the Android half of this is overstated.** The SDK ships prebuilt
Android libraries and a sample that opens the camera from a `UsbManager` file descriptor. A UVC camera
on Android is not simple either: `CaptureBackend.AndroidUvcCaptureBackend` already plans libusb + libuvc
behind the same `UsbManager` permission. ⇒ the two routes cost about the same on Android. What remains
true is the desktop half: a second backend, and more than a backend (§4.6.8).

**3. ⚠ NIR focus shift.** Camera lenses are corrected for the visible. At 900 nm the focal plane moves
noticeably, so the infrared end of the spectrum would sit out of focus — which broadens lines exactly
where the new range is being added. Either accept the blur (it degrades resolution, not position) or
budget for an apochromatic or reflective collimator.

**4. ⚠ A full mechanical and calibration rebuild.** New mount (C or 1.25", not M12), new back focus, a new
grating holder, and a fresh ROI + px→nm calibration. ⛔ **Archive registration breaks** — every metric
constant is fitted on 98 runs taken through the ELP.

**5. ⚠ Silicon runs out at ~1100 nm** and is failing well before that (§4.4).

### 4.4 So — can a NIR spectrometer to 1000 nm be built on this camera?

**To ~850–900 nm: yes, and comfortably.** The window transmits IR, the sensor is back-illuminated STARVIS
that Sony explicitly designed for 850 nm, it is mono, and 12-bit. Nothing in the way but the order-sorting
filter and the rebuild.

**To 1000 nm: physically possible, but do not promise it.** Silicon's bandgap is 1.12 eV ⇒ a hard cutoff
near **1100 nm**, so 1000 nm is inside the sensor's range — but only just. The absorption depth in silicon
grows from ~1 µm at 550 nm to well over 100 µm approaching 1000 nm, while a back-illuminated photodiode is
only a few µm thick. ⇒ **QE at 1000 nm is single-digit percent** on any sensor of this class. Workable
against a bright halogen with long exposures and frame averaging; hopeless for a dim source.

⛔ **And Sony publishes no numeric QE beyond "improved sensitivity at 850 nm" and a graph.** No figure for
900, 940 or 1000 nm exists in any source checked. ⚠ **Treat 900–1000 nm as unquantified until measured.**

⚠ **AMENDED 2026-09-17 — one published curve does exist, and it is less pessimistic than "single-digit".**
ZWO publishes a relative-response chart for its ASI290MM, which uses the same IMX290 mono sensor
(`astronomy-imaging-camera.com/wp-content/uploads/ASI290MM-QE.jpg`). Read off the chart by eye (±0.02,
peak 1.00 at ~590 nm):

| λ (nm) | 400 | 500 | 700 | 800 | 850 | 900 | 950 | 1000 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| relative response | 0.57 | 0.90 | 0.83 | 0.63 | 0.52 | 0.40 | 0.25 | 0.14 |
| absolute QE, if the peak is ~80 % | — | — | ~66 % | ~50 % | ~42 % | ~32 % | ~20 % | **~11 %** |

⚠ The absolute row is our own multiplication: ZWO gives only relative values and does not say whether
the window is included. ⇒ **~11 % at 1000 nm, not single-digit**, and the "low single digits at 900 nm"
kill criterion in §7 looks unlikely. Still a vendor chart for a different camera body, so the halogen
test below remains the acceptance test.

⭐ **The good news: we now own the method to measure it.** `KB_lamps.md` §4's halogen ÷ Planck division
returns the instrument response of *whatever* camera it is pointed through. Applied to a new camera it
answers "what is the QE at 950 nm on my actual optical stack" directly — no datasheet needed. That is the
acceptance test to run on day one, before any redesign is committed.

⚠ **A halogen is also the right source for it**, and increasingly so: a 2900 K blackbody's radiance keeps
climbing to ~1000 nm, so the lamp is *strongest* exactly where the sensor is weakest. The two curves work
against each other in the helpful direction.

### 4.5 ⚠ And the question behind the question — what is at 700–1000 nm worth having?

| target | wavelength | verdict |
|---|---|---|
| **AOCS Cc 13i-96** chlorophyll baseline | **710 nm** | ⭐ comfortably in range ⇒ a **normed** method becomes executable |
| literature-comparable Kreft **DI** | > 700 nm | ⭐ in range |
| chlorophyll *a* | 430 / 662 nm | ⭐ in range (hemp oil, §95.2 of the lamp memory) |
| the **660–680 quiet window** | 660–680 nm | ⭐ in range — the pigment-free baseline anchor the metric has never had |
| C–H 3rd overtone (fat) | ~900–930 nm | ⚠ weak overtone; needs long path + chemometrics |
| **O–H 2nd overtone (water)** | **~970 nm** | ⚠ the classic NIR moisture band — see below |

⭐ **The 970 nm water band is the one with a business story attached.** `spectracs-alwera-group` records
that ALWERA/Estyria already use a **humimeter FSA** to check contract farmers' drying, and *return goods
on it*. Moisture is measured in the NIR, and 970 nm is where. ⛔ **But do not read that as a product.**
Moisture in seed is a **diffuse-reflectance** measurement with a chemometric calibration against oven
reference values — a different instrument geometry from a transmission cuvette, a different corpus, and a
validated incumbent already in the customer's hand. It is a reason to keep the door open at 1000 nm, not a
reason to claim the door leads anywhere yet.

### ⭐⭐ 4.5a The AOCS colour and chlorophyll methods — what each one actually needs *(2026-09-04)*

The **AOCS Official Methods and Recommended Practices** carries a whole `Cc 13*` family for the colour of
fats and oils. Read off the official 2003 method index (saved to
`spectracs-references/standards/AOCS_2003_method_index.pdf`):

| method | subject |
|---|---|
| Cc 13a-43 | Color — FAC method |
| Cc 13b-45 | Color — Wesson method (AOCS Lovibond) |
| ⭐⭐ **Cc 13c-50** | **Color — SPECTROPHOTOMETRIC method** |
| Cc 13d-55 | Chlorophyll pigments (refined and bleached oils) |
| Cc 13e-92 | Lovibond (per ISO standard) |
| ⭐ **Cc 13i-96 (01)** | **Chlorophyll pigments (crude vegetable oils)** |
| Cc 13j-97 | Automated method |
| Ak 2-92 | Chlorophyll pigments (rapeseed) |

**Cc 13i-96 — chlorophyll pigments in crude vegetable oils.** Absorbance of the **neat oil against air**
at three wavelengths, reported as pheophytin *a*:

```math
c = \frac{345.3 \, (A_{670} - 0.5\,A_{630} - 0.5\,A_{710})}{L}
  read: c is mg pheophytin a per kg of oil; L is the cell thickness in mm.
  The 630 and 710 points are a two-point BASELINE under the 670 nm Qy peak — that is all they are for.
```

⚠ **This corrects the form carried in the project record**, which had the 345.3 as a *divisor*. It is a
multiplier, and there is a path-length term. Stated detection limit: **> 1 mg/kg**.

**Cc 13c-50 — the photometric colour index**, and ⭐⭐ **the more interesting one for Spectracs**:

```math
PCI = 1.29\,A_{460} + 69.7\,A_{550} + 41.2\,A_{620} - 56.4\,A_{670}
```

Three of its four wavelengths — 460, 550, 620 nm — are inside today's 400–630 nm window already; only
**670 nm** is missing, which is precisely what the ELP's 641.8 nm IR-cut destroys.

#### ⛔⛔ 4.5b The obvious reading of that is WRONG — PCI is the one we CANNOT execute

*(`diagnostics/aocs_pci_feasibility.py`, 225 archived runs. A first draft of §4.5a called PCI "the
nearest normed method, one wavelength away". It is the opposite, and the reason is scale, not
wavelength.)*

**Cc 13c-50 specifies a 1-inch (25.4 mm) cell** — the method was built to grade *light* refined oils
against a Lovibond red. Scaling the archive's median `A460 = 0.411` (diluted, 1.3 cm jar) back to neat
oil at that cell:

| dilution factor | A₄₆₀ neat @ 25.4 mm | A₄₆₀ neat @ 0.7 mm | path for A₄₆₀ = 1.0 |
|--:|--:|--:|--:|
| 60 | **48** | 1.3 | 527 µm |
| 100 | **80** | 2.2 | 316 µm |
| 120 | **96** | 2.7 | 264 µm |

⛔ **Neat pumpkin oil in the AOCS cell reads A ≈ 48–96 — transmittance 10⁻⁴⁸. The method is inapplicable
by about fifty orders of magnitude.** PCI has no path-length term (unlike Cc 13i-96), so it is *defined*
at its cell; measuring at a thinner path and scaling yields a number that is **not** the norm's PCI. You
could publish a PCI-*like* index; you could not claim Cc 13c-50.

⭐⭐ **Cc 13i-96 is the one that survives, and for a structural reason: it carries `/L` explicitly.** Being
path-length-general by construction, its *arithmetic* applies at any cell — including a thin one. ⇒ **the
wavelength that unlocks a normed method is 710 nm, not 670**, and the bar for a camera change is
correspondingly higher.

⚠⚠ **But only the arithmetic travels.** Cc 13i-96 specifies a **5 mm or 10 mm cell**, and neat pumpkin
oil reads `A₆₃₀ ≈ 3–12` there — out of a spectrophotometer's range by 3–6×. A standard is a *procedure*,
not only a formula, so whether a read at an unspecified path may be reported *per Cc 13i-96* is a
question for the method text or a certifying body. ⛔ **Do not promise "we execute the AOCS method" on a
portable formula alone.** ⭐ The geometry news is nonetheless good: at this project's existing **~1 mm**
cell the same oil reads **A₆₃₀ ≈ 0.6–1.2**, dead centre of the usable window — it is the *lab's* cells
that are wrong for a dark oil, not ours. Full working: `SPEC_metric_research.md` §16.20.5d.

⭐ **And the thin cell is not exotic — it is the geometry the trade already uses.** 260–530 µm puts
`A460` at 1.0, and the **Kernöltestgerät is a backlit 0.7 mm viewer** (`spectracs-oelmuehlen-verzeichnis`)
where the same oil reads A ≈ 1.3–2.7. The gatekeeper's own instrument is already in the right regime.

#### 4.5c What the archive says about the three terms we CAN see

| question | answer |
|---|---|
| ⭐ **dynamic range** — can one path serve all four bands? | **Yes, easily.** At a path giving `A460 = 1.0` the bands span **A = 0.24 … 1.73** (T = 58 % … 1.8 %) — a factor of 7.3. ⛔ This **corrects** an earlier guess in this note that neat oil would put PCI back in the starved regime: it does not, because PCI reads 460 nm on the Soret **flank**, never the 432 nm peak |
| ⛔ **is `1.29·A460 + 69.7·A550 + 41.2·A620` a new axis?** | It is **77 % concentration** (r = +0.77 with `A_Soret`). Divided by `A_Soret` it is uncorrelated with `Q%` (r = +0.07) — ⚠ but that is *not* evidence of a new axis |
| ⛔ **is the residual signal or noise?** | **Noise.** Grouped by source (15 oils, ≥4 runs each) its between/within ratio is **0.74**, against `Q%`'s **0.93** on the identical grouping. The residual discriminates oils *worse* than the shipped metric |

⇒ **Everything rides on the −56.4·A₆₇₀ term** — 40 % of PCI's weight by coefficient, and the one
wavelength the instrument cannot see. ⚠ A prediction was recorded before the test (that the three visible
terms would land on the metric family's single axis, per `spectracs-metric-family-2026-08-21`); it
**failed** — they land nowhere, which is a weaker result than either alternative.

⚠⚠ **But both methods measure NEAT OIL against air, not a solvent dilution** — and that is a bigger
change than the wavelength. Consequences, none of them small:

| | |
|---|---|
| ⛔ **no dilution** | the whole `SPEC_settled_measurement.md` protocol, σ_fill, the clearing gate and every fitted constant assume oil-in-isopropanol. A neat-oil method shares none of that corpus |
| ⛔ **dynamic range** | neat pumpkin oil is near-opaque below ~550 nm at any normal path length. Cc 13c needs `A460` — ⚠ this is the starved regime again, and the one place §4.1b says bit depth genuinely helps |
| ⭐ **path length is the lever** | AOCS specifies `L` explicitly. The **Kernöltestgerät is a backlit 0.7 mm viewer** (`spectracs-oelmuehlen-verzeichnis`) — that is the right order of magnitude for neat dark oil, and it is the geometry the gatekeeper already accepts |
| ⭐ **simpler for the operator** | no capillaries, no solvent, no waiting for a fill to settle. ⚠ Which also removes the 4.4× error term §0 says dominates everything |

⇒ ⭐ **A neat-oil, short-path mode is a genuinely different product shape from the diluted `Q%`
workflow**, and §4.5b names the one that could carry a norm: **Cc 13i-96 at a thin cell, needing 710 nm.**
It would answer §89's fourth condition (*"the absence of a normed alternative"*) in the opposite
direction — by *executing* the norm instead of avoiding it.

⚠⚠ **But count what that trades away.** The moat on record is *the validated corpus, not the formula*
(`spectracs-alwera-group`). A normed number has **no corpus moat by construction** — anyone with a
spectrophotometer computes the same figure. What would remain is form factor and price: ~€900 at the
press against a lab instrument plus sample transport, which is `spectracs-international-market` §91's
"only non-destructive / at-the-mill survives" argument, now with a normed number attached instead of a
proprietary one. ⛔ Whether that trade is good is a business question this note cannot answer.

⛔ **Nothing here is a plan.** It is the first time the norms have been read closely enough to see what
they cost, and the headline is that one of the two is arithmetically impossible on this oil.

⚠ **On the source.** AOCS Official Methods is a **copyrighted commercial publication** — there is no
legitimate free full text, and none was obtained. What is on disk is the **2003 method INDEX** (22 pp,
numbers and titles only). The two formulas above are quoted from the open literature, not from the
standard. ⛔ **Before anything is certified against either method, buy the actual method text** (AOCS
sells them individually) — an index cannot tell you the cell, the blanking or the tolerances.

### ⭐⭐ 4.5d Could the device report LOVIBOND or AOCS colour? — the optics say yes at 690 nm  *(2026-09-04)*

A **band metric** (`Q%`, `Rv`, PCI) needs a handful of wavelengths. A **colour** number — Lovibond,
AOCS-Tintometer/Wesson, a literature Kreft dichromaticity index — is a **tristimulus integral** and needs
the whole visible band. `spectracs-colorimeter-idea` records the objection in one line: *"with the
440–630 nm window a literature-comparable DI is NOT computable (x̄ runs past 700)."*

⭐⭐ **That is true of the CLAMP and false of the INSTRUMENT.** `diagnostics/cie_truncation_cost.py`
measures the fraction of each D65-weighted CIE 1931 2° colour-matching function lying above each cutoff —
once for a white source, once weighted by what an archived oil actually transmits:

| cutoff | x̄ (red) | ȳ (luminance) | z̄ (blue) |
|---|--:|--:|--:|
| **632.6 nm** — the pipeline clamp | **9.9 %** / **11.1 %** | 3.6 % / 3.7 % | 0.0 % |
| **690.8 nm** — the extended ROI | **0.22 %** / **0.25 %** | 0.08 % | 0.0 % |
| 780.0 nm — the full visible | 0.00 % | 0.00 % | 0.0 % |

*(illuminant-weighted / sample-weighted. ⚠ The sample figures hold the measured absorbance FLAT past
632.6 nm at its 620–630 value; real transmittance rises into the red, so they are **lower bounds**.)*

⇒ ⭐⭐ **`x̄` — the red primary — is the only one truncated, and the extended ROI closes it. 780 nm is not
needed.** `z̄` is finished long before either cutoff and `ȳ` almost. **A colour number is not computable at
632.6 nm and is computable at 690.8 nm** — on the filterless camera already on the bench, through the ROI
the capture view already draws. ⭐ This is the sharpest single argument for the red extension yet
produced: it turns a *categorical* "not computable" into a **0.2 %** residual.

#### ⛔ But three gates remain, and two are worse than the optics

| gate | |
|---|---|
| ⛔⛔ **the Lovibond scale is PROPRIETARY** | converting a spectrum to R/Y/B needs Tintometer's glass transmission data and their matching algorithm — licensed, not published. It is why a PFX990 can do it and a generic spectrophotometer cannot. An approximation is possible; **"approximate Lovibond" is not Lovibond.** ⚠ **This is the binding constraint, and it is contractual, not technical** |
| ⛔ **scope** | `Cc 13j-97` is *"refined oils only … providing no turbidity is present"* (§4.5a) ⇒ cold-pressed is out whatever we compute |
| ⚠ **path length** | Lovibond is defined at **133 mm**. We would measure at ~1 mm and scale by Beer–Lambert — valid arithmetic, but a 133× extrapolation, and neat pumpkin at 133 mm is `A₄₆₀ ≈ 250–500`, off-scale in principle. Plausible for a light oil |
| ⚠ **photometric accuracy** | a ratio metric tolerates shape distortion that a tristimulus integral does not — stray light especially. ⭐ *Not* a problem: the 486/581 nm max-channel notches (§2) are common to reference and sample and **cancel in `T = S/R`** |

#### ⭐ PCI is the exception, and it is the one within reach

| | Lovibond / AOCS-Tintometer | **PCI (Cc 13c-50)** |
|---|---|---|
| needs the full visible band | ✅ yes — ⭐ solved at 690 nm | ⛔ no — four band means |
| needs proprietary data | ⛔ **yes** | ✅ no |
| computable by us | ⛔ only as an approximation | ⭐ **yes** |
| reportable *as the norm* | ⛔ scope + cell | ⛔ cell — §4.5b's fifty decades on pumpkin |

⇒ **The device could compute PCI on a light oil at the right cell, and a Lovibond-*like* number on
anything — but could not legitimately report either as the AOCS value.** ⛔ The remaining obstacles are
procedural and contractual; **the optical one closes at 690 nm.**

⭐⭐ **And there is a better target than approximating a licensed scale: `CIELAB` is ISO/CIE 11664 — open,
and exactly what modern food colorimetry uses.** ⇒ emit a *fully standard, non-indicative* coordinate any
lab reproduces exactly, and keep a declared-indicative Lovibond bridge as a separate courtesy. Two jobs;
only one carries liability. ⭐⭐⭐ **The number that actually matters here is Kreft's dichromaticity index**,
which §4.5d's 0.2 % makes *literature-comparable rather than a proxy* — and whose whole value is
legitimacy, which a proxy cannot supply. ⇒ **the red extension is a precondition for that argument, not an
enhancement of it.** The commercial reading is
`spectracs-references/business/SPEC_oelmuehlen_verzeichnis.md` **§142** (with §92/§93, which still
conclude: feature yes, business no).

### ⭐⭐⭐ 4.5e What a light-source spectrometer canNOT do — and why that is the position  *(Edwin, 2026-09-04)*

*Edwin's question: could a Sekonic C-800 SpectroMaster measure the colour of a liquid?* ⛔ **No, not out
of the box** — it is an **illuminance** spectrometer for light sources (380–780 nm, 1 nm output, CMOS
linear sensor, ~€1,700). No sample compartment, no cuvette, no defined path length, no reference beam. To
measure an oil with one you would have to build a cell, a holder and a stable geometry **around** it — i.e.
build a spectrophotometer. **That is this instrument.**

⇒ **The competitive map has two axes, not one, and price is the lesser of them:**

| | defined liquid geometry | true spectrum | price |
|---|---|---|---|
| Sekonic C-800 (light-source meter) | ⛔ no | ⭐ yes, 380–780 nm | ~€1,700 |
| RGB photo crop → Lab (§4.5d's "new approach") | ⛔ no | ⛔ no — 3 channels | ~€0 |
| AS7341-class multispectral chip | ⛔ no | ⛔ no — 11 channels | ~€10 |
| Lovibond PFX990 | ⭐ yes | ⭐ yes | €3,000–20,000 |
| ⭐⭐ **Spectracs** | ⭐ **yes** | ⭐ **yes** | **~€900** |

⇒ ⭐⭐⭐ **Only two rows carry both, and they differ by 3–22× in price.** The claim is therefore not
"cheaper than a Lovibond" but **"the only instrument under €3,000 that measures a liquid with a defined
path length AND a real spectrum."**

⚠ **Two limits, before that sentence goes anywhere.**
1. ⛔ **Cheap DIY spectrometers DO measure liquids** — Public Lab kits, DVD-webcam builds, exactly
   `Bestari 2022`'s architecture. "Nothing under €3,000 can do it" is **too strong**. ⭐ The defensible
   form: *nothing at that price does it with the geometry, calibration and repeatability that makes the
   number trustworthy* — and the proof is already on the shelf, since the same hardware and the same
   physics produced "smooth vs rough". **The difference is the corpus and the discipline, not the parts.**
2. ⛔ **"Our device can measure colour" is not yet true.** At 632.6 nm **11 % of x̄ is missing** (§4.5d), so
   a correct `L*a*b*` is not computable. It becomes true at **690.8 nm** (0.22 %). ⭐ That dates the claim
   rather than defeating it: **one calibration change, on hardware already on the bench.**

⭐⭐⭐ **And the chain closes on itself.** The C-800 cannot measure a liquid ⇒ we can. We cannot yet compute
correct colour ⇒ the red extension fixes it. We cannot yet claim *accurate* colour ⇒ **a rented C-800
characterises us** and closes §4.5d's remaining "photometric accuracy" gate (method in §6). **The
instrument that cannot do the job is the one that certifies us to do it** — for a few days' rental, not a
purchase. ⚠ Traceability against the PFX990 still has to be bought separately; that is Tintometer's
business, not the measurement's. Commercial reading:
`spectracs-references/business/SPEC_oelmuehlen_verzeichnis.md` **§143**.

### ⭐⭐⭐ 4.5f Where a FILTER PHOTOMETER wins — and the uncomfortable thing that says about `Q%`

§4.5e's map says we are one of only two instruments with both liquid geometry and a real spectrum. ⚠ That
only matters where the **shape** of the spectrum is the answer. Where it is not, a filter photometer wins
on price and always will.

The concrete instance: **Hanna HI96785 "Color of Honey"** — 420 and 525 nm, tungsten lamp + narrow-band
interference filters + silicon photodiode, 0–150 mm Pfund, ±2 mm @ 80, 10 mm cuvette, **€531.92**
(currently *nicht lieferbar*). ⭐ Exactly what §16.20.4 predicted: *"single-wavelength norms, all served by
€15–500 one-LED photometers."*
⭐ One borrowed idea: its reference is a **glycerin standard**, not air — refractive index near honey's, so
cuvette-wall reflections cancel between blank and sample. **Index matching, the same trick as sunflower**
(`SPEC_settled_measurement.md` §55.1).

| task | does a filter photometer suffice? |
|---|---|
| Pfund honey colour (2 λ) | ⛔ yes — €532 |
| EBC beer (1 λ, 430 nm) | ⛔ yes — €200–800 |
| **AOCS PCI (4 λ)** | ⛔ **yes, in principle** |
| ⭐ `D`, the SNV shape distance | ⭐ **no — needs the whole curve** |
| ⭐ correct CIELAB / Kreft DI | ⭐ **no — a tristimulus integral** |
| ⭐ peak POSITION (568 / 624, `R`) | ⭐ **no — needs resolution** |

⚠ **`Q%`'s FORMULA is three band means** — `Q% = −100·(A_valley − A_Q)/A_Soret`.

⛔⛔ **An earlier draft concluded from that "a three-filter photometer could compute the shipped verdict".
That is wrong, and Edwin corrected it (2026-09-04): *„ein Photometer kann das nicht, nur ein Spektrometer
und meine Metrik/Algorithmus — und das muss man mal umsetzen."*** Three reasons, and the first is
decisive:

1. ⭐⭐⭐ **The shipped measurement is not a snapshot.** It is the **settling read**: watch the clearing
   curve, find the minimum by the **drawdown rule**, and read `Q%` *there*. That is the whole of
   `SPEC_settled_measurement.md` — a time series plus a validated decision rule, not three numbers at one
   instant. **A photometer that reads once cannot produce the shipped number at all.**
2. ⭐ **A band mean is not a filter reading.** The valley window is **500–560 nm — 60 nm wide** — and the
   spectrum is a rising flank across it. An interference filter gives a ~10 nm weighted bandpass, not a
   flat mean. ⇒ a filter instrument returns a *different* quantity, and `T = 18.6` would not transfer;
   it would need its own corpus to re-derive.
3. ⭐ **Filters freeze the bands.** The Soret window was retrimmed 440–460 → **448–460 in software**; a
   filter set is fixed at manufacture.

⇒ ⭐⭐ **The corrected statement:** the *spectral information* `Q%` uses is concentrated in three bands, so
a competitor with a **spectrometer** is not blocked by optics — but they would still have to build the
settling apparatus and derive their own thresholds. **The barrier is the settling logic plus the corpus,
not the hardware.** That is a **higher** barrier than the withdrawn claim, not a lower one.

⭐⭐ **And the second justification, independent of the above: being able to change your mind — this
document's own session is the evidence.** The Soret band was retrimmed 440–460 → **448–460 in software**; with filters that would have
been new hardware *and a worthless archive*. On 2026-09-04 alone: 225 runs re-quantised for bit depth
(§4.1a), PCI's three visible terms (§4.5c), the CIE truncation (§4.5d), and the pedestal-vs-pigment test
(`KB_spectroscopy_physics.md` §8.3a) — **every one of those questions would have been unanswerable against
an archive of three numbers per run.**

⇒ ⭐⭐⭐ **The spectrometer earns itself on the CORPUS it preserves, not on the number it emits** — the
hardware-side statement of *"the moat is the validated corpus, not the formula"*. Commercial reading:
`SPEC_oelmuehlen_verzeichnis.md` **§144**; the honey-as-a-plugin consequence is **§145**.

### ⭐⭐ 4.6 The driver library — what `libtoupcam` lets us do  *(2026-09-17, after the purchase)*

*Edwin: "i have now bought the chinese mono webcam — make a research about the driver library and what we
can do with it." Nothing here is measured on our unit: the camera was not plugged in when this was
written. How each claim is known:*

| mark | means |
|---|---|
| **[H]** | read in the SDK's `toupcam.h` or `toupcam.py` |
| **[D]** | read in the SDK's API document (`doc/en.html`) |
| **[L]** | ⭐ read from the model table **inside `libtoupcam.so`**, loaded with ctypes. Needs no camera, and it is what the driver will actually do with this model |
| **[3P]** | third-party: INDI / INDIGO driver sources and issues, forums, ZWO's charts |

#### 4.6.1 Getting it

- **Download:** `https://www.touptek-astro.com/dl_software/toupcamsdk.20260908.zip` (~293 MB), found through
  the site's own download list `assets/data/download.json`. SDK version **60.32549.20260908** [H].
- **Contents** [H]: `libtoupcam.so` for Linux x64 / x86 / arm64 / armhf / armel, Android arm / arm64 / x86 /
  x64 (API ≥ 24), macOS and Windows; the C header; ⭐ **`python/toupcam.py`, an official ctypes wrapper**
  with samples (the Qt samples use PyQt6, not PySide6); a Linux viewer GUI (`extra/visionlite`); a
  firmware-update tool; `linux/udev/99-toupcam.rules`. ⛔ No pip package exists.
- **USB permissions** [H/D]: the rule grants mode 0666 to vendor IDs `0547` and `04b4`. Without it, opening
  fails with `E_ACCESSDENIED` (0x80070005).
- **Which library** [L]: the plain ToupTek library knows this model under **two product IDs, `0547:10ff`
  and `0547:1368`**, both named `GPCMOS02000KMA` (probably two hardware revisions). The rebrand libraries
  (Altair, Ogma, Omegon, …) each enumerate only their own models ⇒ use `libtoupcam`.
- ⛔ **Licence: the zip contains no licence, EULA or redistribution text, and the API document says nothing
  about it** [H/D]. INDI redistributes the binaries, but that is INDI's packaging, not a grant from
  ToupTek. ⇒ **Ask ToupTek (astro@touptek.com) in writing before bundling `libtoupcam.so` in the AppImage
  or an APK.**

#### 4.6.2 What the driver says this camera can and cannot do  [L]

| capability | this model | why it matters here |
|---|---|---|
| resolutions | **1920 × 1080 only** — no bin or skip modes | the imaging width is 1920 × 2.9 µm = 5.57 mm, so §4.2's arithmetic holds |
| mono | ✅ | |
| pixel formats | **RAW8, RAW12** (no packed RAW12) | 12-bit arrives as 2 bytes per pixel |
| hardware ROI | ✅ `ROI_HARDWARE` | ⭐ a strip around the slit image is read out on the sensor, not cropped on the host |
| conversion gain | ✅ HCG / LCG | a low-noise and a high-full-well setting |
| black level | ✅ | |
| trigger | ✅ software, **one frame per trigger** | |
| ST4 guide port | ✅ | ⭐ see §4.6.4 |
| still-snap mode | ⛔ none | use video or trigger mode |
| sensor temperature | ⛔ **none** (`GETTEMPERATURE` flag absent) | log room temperature separately |
| GPIO / external trigger | ⛔ none | |
| USB speed levels | 0–2 | |

#### 4.6.3 The settings a spectrometer wants — and the defaults that would silently spoil it

| option | set to | default | why |
|---|---|---|---|
| `TOUPCAM_OPTION_RAW` (0x04) | **1** | 0 = processed image | ⭐ sensor data with the hardware ISP off (`OPTION_ISP` 0 = auto turns it off in raw) [H]. ⛔ Not **−1**: that variant still runs the flat/dark/fixed-pattern corrections and black/white balance [H] |
| `OPTION_PIXEL_FORMAT` (0x1a) | `RAW12` (0x02) | RAW8 | or `OPTION_BITDEPTH` = 1 [H] |
| `OPTION_ZERO_PADDING` (0x78) | **0** | 0 | ⇒ values 0…4095, right-justified [H]. INDI sets 1 (values × 16) [3P]. ⚠ verify with a saturated frame |
| `OPTION_DEFECT_PIXEL` (0x40) | **0** | ⛔ **1 = on** | the document does not say whether it touches raw data ⇒ switch it off rather than find out from a spectrum [H] |
| `put_AutoExpoEnable` | **0** | — | the INDI driver turns it off straight after open [3P] |
| `put_ExpoTime` | µs | — | ⭐ **`get_RealExpoTime` returns what the sensor actually applied** [H] |
| `put_ExpoAGain` | 100 (= 1×) | — | query `get_ExpoAGainRange`; not published for this model |
| `OPTION_CG` (0x19) | decide by measurement | — | HCG vs LCG trades read noise against full well |
| `put_HZ` | **2 = DC** | — | no rounding of exposure to 50/60 Hz mains flicker [H] |
| `OPTION_BLACKLEVEL` (0x15) | fixed, **set LAST** | — | ⛔ changing conversion gain, bit depth or resolution resets it [3P, INDI issue #1238]. 12-bit maximum 496 [H] |
| `put_Roi` | strip around the slit | full frame | offsets and sizes **even**, width and height **≥ 8** [H/D] |

⛔ **Never use the "Grey16" output (`OPTION_RGB` = 4) for measurements.** It goes through the image
pipeline, whose built-in tone curve `OPTION_CURVE` **defaults to 2 = logarithmic**, and the document warns
that tone mapping "significantly compromises linearity" [H]. Raw mode skips that pipeline.

#### 4.6.4 What it lets us do that the ELP cannot

1. ⭐⭐ **Linear 12-bit data, with saturation at one number.** In raw mode nothing is gamma-encoded, so
   `ImageSpectrumAcquisitionLogicModule`'s `pow2.2` decode, the quantisation tie window, the 16 DN guard
   and the MAD==0 collapse have nothing to act on. At minimum gain the IMX290's full well and the 12-bit
   ceiling nearly coincide (ZWO: 3.6 e⁻/ADU × 4096 ≈ 14.7 k e⁻ against 14.6 k e⁻) [3P], so **a clipped
   pixel is simply 4095**.
   ⚠ **§0 still holds**: this is capability, not precision on `Q%`. Where it genuinely pays is `Rv`
   (§4.1b) and the starved red end.
2. ⭐⭐ **Every frame reports its own settings.** The frame-info struct carries a **sequence number, a
   µs timestamp, the exposure and gain it was taken with, and the black level**, each with a flag saying
   whether it is filled in [H]. `OPTION_FLUSH` (0x3d) discards queued frames [H]. ⇒ a capture can check that
   a frame was taken *after* an exposure change instead of hoping. That is what `CaptureBackend`'s
   `BUFFERSIZE=1` only works around today (`SPEC_capture_quality.md` §4.8). ⚠ Whether this USB 2.0 model
   fills the exposure / gain / black-level fields must be checked on the unit.
3. ⭐ **Many more frames per minute, probably.** A 1920 × 128 RAW12 strip is ~0.25 MB per frame against
   the ELP's 10.1 MB YUYV frame at ~3.3 fps. On a strip USB bandwidth stops being the limit, and exposure
   time becomes the limit. `SPEC_settled_measurement.md` §49's `maxFrames = 4000` is *"a ~20-min cap in
   disguise"* at today's rate. ⚠ **No published figure** for the strip rate — measure it.
4. **Frame capture without callbacks.** `Toupcam_TriggerSyncV4(h, waitMS, buf, bits, rowPitch, info)` fires
   one software trigger and **blocks until that frame arrives** [H], and the Python wrapper has it. One
   request, one frame, with its metadata.
5. ⭐ **A fixed serial number to key calibration on.** `get_SerialNumber` returns a unique 32-character
   serial, and `Toupcam_query_SerialNumber` reads it **without opening the camera** [H]; `Open("sn:…")`
   opens by serial. That fits the serial-keyed instrument setup in the connection & calibration UX spec
   better than a cv2 index does. Firmware, hardware version and production date are readable too.
6. ⭐ **The ST4 port as four timed outputs.** `Toupcam_ST4PlusGuide(h, direction, ms)` pulses one of four
   lines (N / S / E / W) for a given time [H]. ⇒ a candidate driver for the **shutter** that
   `SPEC_capture_quality.md` §16.36 asks for ("the lamp changes the sample"), or for switching the lamp,
   through a relay or opto-isolator. ⚠ The Python wrapper does not expose it (call it through ctypes), and
   ⛔ **the port's electrical design (open-collector? opto-isolated? current limit?) is undocumented —
   measure before connecting anything.**
7. **Digital binning without clipping.** `OPTION_BINNING` (0x17) = `0x40 | n` adds pixels without saturating,
   raw only, and the bit depth grows (12 → 14 bits for 2 × 2) [H]. ⚠ A rows-only sum along the slit is
   what the spectrum needs; host-side reduction of the strip keeps our robust per-column reduction and
   may be the better choice.

#### 4.6.5 ⚠ Dark subtraction becomes mandatory

A raw sensor has an **offset**: the black level sits above zero so that noise is not clipped. The
spectrum chain has **no dark-frame step today** (no dark handling anywhere under `sciens/spectracs/logic`),
because the ELP's on-chip processing hands over images whose black is already clamped. ⇒ on this camera
**T = (S − D) / (R − D)**, with `D` a dark capture at the same exposure, gain and black level. Skip it and
every transmission is biased upward, most at low signal, which is exactly where absorbance lives.

⭐ **Use our own dark, not the driver's.** The SDK has built-in dark-field, flat-field and fixed-pattern
corrections (`DfcOnce` / `FfcOnce` / `FpncOnce`, exportable as `.dfc` / `.ffc` / `.fpnc` files) [H], but
⛔ they only run in `RAW = −1` [H]. Keeping them in our code keeps every correction in the archive and
visible, which is §4.5f's argument about the corpus.

#### 4.6.6 Pitfalls, from other people's drivers

- ⚠ **Reopen needs a replug**: INDIGO lists GPCMOS02000KMA as tested, with the known issue that after the
  camera is reopened, exposures fail until it is replugged [3P]. Matters for `VideoThread`'s reopen path.
- ⚠ **Stale and dropped frames**: flush after every settings change. Check `seq` for gaps, and watch
  `OPTION_NUMBER_DROP_FRAME` (0x3e) and the front/back-end overflow events [H]. The default
  (`put_RealTime(0)`) pauses grabbing when the queue is full rather than silently dropping [H].
- ⚠ **Row banding** is a known IMX290 effect of its row-parallel readout, visible at bias level [3P].
  Per-pixel gain spread also mattered in an IMX290 X-ray paper (arXiv 2409.05954) [3P]. Both argue for a
  dark per session, and for reducing across rows rather than reading one row.
- ⚠ **Zero-copy on Linux x86/x64 is on by default** [D]. If images look wrong, open with `;zerocopy=0`.
- ⚠ **Settings files**: the driver dumps its settings when the camera stops (`OPTION_DUMP_CFG` defaults to
  1) and can load them from `;ini=` / `;json=` at open [D]. Set everything explicitly at open and do not
  rely on a file the driver wrote.
- ⚠ **Callbacks**: no `Close` / `Stop` inside a callback (deadlock), and ROI, trigger, bit depth and pixel
  format cannot be changed from inside one (`E_WRONG_THREAD`) [D]. `TriggerSyncV4` (§4.6.4, item 4) avoids
  callbacks entirely.

#### 4.6.7 Android

The SDK ships `android/{arm,arm64,x86,x64}/libtoupcam.so` and a JNI sample (`android/samples/demoandroid`)
[H]. The pattern: request permission through `UsbManager`, open the device, take its file descriptor and
call `Toupcam_Open("fd-<fd>-<vid>-<pid>")` [D]. `toupcam.py` already has `sys.platform == 'android'`
branches [H]. ⇒ **§4.3 blocker 2's Android half is amended**: the effort is comparable to the libusb +
libuvc route a UVC camera needs anyway. ⚠ Unproven in our python-for-android build, and ⛔ the licence
question of §4.6.1 applies to an APK just as to the AppImage.

#### 4.6.8 What it means for our code — more than a backend

`CaptureBackend.read()` returns an **8-bit RGB `QImage`**, and `ImageSpectrumAcquisitionLogicModule`
converts to RGB888, gamma-decodes each channel, takes the channel maximum and masks 255 as saturated. A
12-bit mono frame fits none of that. ⇒ this camera needs a **16-bit mono acquisition path** alongside the
existing one, not only a new `CaptureBackend` subclass. §5 lists the rows; the new ones are the frame
type, dark subtraction and settings that are specific to each camera (µs exposure, no white balance).

⚠ **Two ways to check the camera before writing any of it:** the SDK's own VisionLite viewer, and the
INDI driver (`indi_toupcam_ccd` in indi-3rdparty) with KStars / Ekos [3P].

#### 4.6.9 Day one on the bench — what only the unit can settle

1. `lsusb` → which product ID (`10ff` or `1368`); install the udev rule; open VisionLite; record serial,
   firmware and hardware version.
2. A **saturated raw frame** ⇒ maximum 4095 (right-justified) or 65520 (left), and the byte order.
3. **Dark frames** with defect-pixel correction on and off ⇒ does it touch raw data; black-level default;
   row-banding amplitude.
4. Read `get_ExpTimeRange` and `get_ExpoAGainRange`; check whether frame info fills exposure / gain / black
   level.
5. **fps and dropped frames on a 1920 × 128 RAW12 strip**, at each USB speed level.
6. How many frames after start or a settings change are stale.
7. HCG vs LCG: a photon-transfer curve (e⁻/ADU, read noise) and linearity up to 4095.
8. ⭐ **The halogen ÷ Planck run** (§6) ⇒ the real response to ~1000 nm on our optics, against §4.4's
   ZWO-based expectation.
9. ST4 port electrics, only if the shutter idea is pursued.
10. Close and reopen without a replug ⇒ is the INDIGO issue present on Linux x64.

## 5 · What would have to change in the code

⚠ None of this is proposed work — it is the cost side of §4, so the trade is visible.

| change | where | why |
|---|---|---|
| capture resolution **per sensor** | `CaptureBackend.py` — its own `TODO: make this per-sensor when a second camera lands` | 2592 × 1944 is hardcoded and is the ELP's calibration size. Blocks *any* second camera, including the Microdia |
| a **non-V4L2 backend** | new sibling of `CaptureBackend` | `libtoupcam` is not UVC (§4.3) |
| **bit depth** through the chain | `ImageSpectrumAcquisitionLogicModule`, `SpectralColorUtil` | everything assumes 8-bit gamma-encoded: the decode, the tie window, the 16 DN guard |
| **mono** path | the same | max-channel over three channels is meaningless with one channel |
| a **second calibration profile** | already supported | per-`SpectrometerProfile`, so this is data, not code |
| a **16-bit mono frame type** | `CaptureBackend.read()` → `VideoThread` → acquisition *(added 2026-09-17, §4.6.8)* | `read()` returns an 8-bit RGB `QImage`; a 12-bit frame cannot pass through it |
| **dark-frame subtraction** | acquisition / T computation *(§4.6.5)* | a raw sensor has a black-level offset; the chain has no dark step today |
| **per-camera settings** | `SpectrometerSensorUtil` *(§4.6.3)* | exposure in µs, gain in %, black level, conversion gain; white balance does not exist on a mono sensor |
| **the driver library** in the build | `tools/buildAppImages.sh`, udev rule | ⛔ blocked on redistribution permission (§4.6.1) |

⭐ The first row is required by the Microdia experiment too, so it is not specific to a camera purchase.

## 6 · How to characterise any camera on this bench

1. **Remote test in the dark** — white dot with a **violet halo** ⇒ no IR-cut; nothing or a dim dot ⇒ filter.
2. **Halogen frame, then divide by Planck** (`KB_lamps.md` §4) ⇒ the instrument response of that whole
   optical stack, with no datasheet and no reference detector.
2a. ⭐⭐ **Better, if a reference spectrometer can be borrowed:** measure the *same lamp* with a
   light-source spectrometer covering 380–780 nm (a Sekonic C-800 or similar, **rentable**), then
   **our recorded lamp spectrum ÷ its measurement = the instrument response directly**, with **no Planck
   assumption, no colour-temperature assumption, and reach BEYOND our own 690.8 nm raster edge.** ⇒ it
   would verify the 641.8 nm IR-cut edge independently, answer §3's open Microdia question in one evening,
   and supply the absolute response curve that §4.5d needs for colour work. ⚠ Its own calibration is
   photographic (~±2 % illuminance, ~±2 nm) and its optical resolution is ~5–10 nm despite 1 nm output —
   ample for lamps and colour, useless for narrow lines. ⚠ And it must sit where the sample sits, or a
   different optical path is being measured.
3. **Look for a cliff before doing any arithmetic** — a dielectric edge is a 15–25 nm collapse and is
   scale-free, so it is visible before the camera is calibrated at all.
4. **CFL frame for the scale** — Hg 435.83 / 546.07 for a two-point linear px→nm (`KB_spectroscopy_physics.md`
   §7.2 did this at 0.5057 nm/px), then the full cubic once the ROI is authored.
5. ⚠ **Never compare two cameras' absolute levels** — only their shapes. Exposure, aperture, gain and
   transfer curve all differ.

## 7 · What would change these conclusions

- ⭐⭐ **The Microdia halogen frame (§3)** ⇒ decides whether the production camera already has the red
  range. Cheapest open experiment in the project; needs no purchase and no calibration.
- **A `v4l2-ctl --list-formats-ext` on the ELP** ⇒ settles crop-vs-scale and halves §4.2's uncertainty.
- **The ELP purchase record** ⇒ confirms or refutes the IMX179 identification in §2.
- **A halogen ÷ Planck run on an IMX290** ⇒ the only thing that would turn §4.4's 900–1000 nm from
  unquantified into a number.
- ⛔ **A measured NIR QE in the low single digits at 900 nm** ⇒ the 1000 nm ambition is dead and the
  honest ceiling is ~850 nm. ⚠ *(2026-09-17: ZWO's chart for the same sensor implies ~32 % at 900 nm,
  §4.4, so this outcome now looks unlikely.)*
- ⭐ **§4.6.9 on the bought unit** ⇒ turns every [H]/[L] claim in §4.6 into a measured one; items 2, 3 and
  5 decide whether the linear 12-bit strip is as clean and as fast as the driver suggests.
- ⛔ **A "no" from ToupTek on redistribution** ⇒ the camera stays a bench and research instrument; it
  cannot ship in the AppImage or an APK.
- ⭐⭐ **A repeat of §4.1a's arithmetic against a re-seat-free protocol** ⇒ the only thing that would make
  bit depth matter is removing the term that dwarfs it. `SPEC_settled_measurement.md`'s capillary/one-fill
  work is that; until it lands, no detector change moves the verdict.
