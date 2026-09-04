# KB — Cameras

*The detector is half the instrument. This note holds what each camera on the roster actually is, what
its optical path does to the spectrum, and what changing camera would cost and buy. Written 2026-09-04,
after the halogen measurement in `KB_lamps.md` §4 turned "the camera's red response" from an assumption
into a number.*

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
| role | bench / dev — **the archive camera** | intended **production** camera | ⚠ candidate only, not owned |
| sensor | Sony IMX179 (inferred) | unrecorded | **Sony IMX290LLR mono** |
| colour | Bayer RGB | Bayer RGB | ⭐ **monochrome** |
| native | 3264 × 2448 (8 MP) | unrecorded | 1945 × 1097 (2.13 MP) |
| captured at | **2592 × 1944** (pinned) | ⛔ not wired | 1920 × 1080 |
| pixel pitch | 1.4 µm native | unrecorded | **2.9 µm** |
| imaging width | 3.63–4.57 mm (§4.1) | unrecorded | **5.57 mm** |
| bit depth | **8** | **8** | ⭐ **12** |
| transfer curve | ⚠ gamma-encoded (`pow2.2`) | ⚠ gamma-encoded | ⭐ **linear raw** |
| IR-cut filter | ⛔ **YES — measured, λ₅₀ = 641.8 nm** | ⭐ **NO** (remote test) | ⭐ **NO** — AR-coated clear window, IR-transmitting |
| red reach | 62 DN @ 650, 17 DN @ 660 nm | ⚠ **unmeasured** | ⚠ **unmeasured** |
| interface | UVC / V4L2 → `cv2` | UVC / V4L2 → `cv2` | ⛔ **proprietary `libtoupcam` SDK** |
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

## 4 · ⭐ The candidate: ToupTek GPCMOS02000KMA (IMX290 mono)

Sold as an astronomical **guiding** camera — which is exactly why it is interesting here, because guide
cameras are built to keep near-infrared rather than throw it away.

| item | value | source |
|---|---|---|
| sensor | Sony **IMX290LLR**, 1/2.8", back-illuminated (STARVIS), **monochrome** | Sony / vendor |
| effective pixels | 1945 × 1097 (~2.13 MP); camera outputs 1920 × 1080 | Sony datasheet |
| unit cell | **2.9 µm** square | Sony datasheet |
| active area | **5.57 × 3.13 mm**, diagonal 6.39–6.46 mm | vendor / Sony |
| ADC | **12 bit** | vendor |
| peak QE | ~81 % | vendor |
| read noise | 0.53–0.84 e⁻ | vendor |
| full well | ~11 200 e⁻ | vendor |
| exposure | **0.105 ms – 1000 s** | vendor |
| frame rate | ~16–18 fps at full resolution (USB 2.0) | vendor |
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

## 5 · What would have to change in the code

⚠ None of this is proposed work — it is the cost side of §4, so the trade is visible.

| change | where | why |
|---|---|---|
| capture resolution **per sensor** | `CaptureBackend.py` — its own `TODO: make this per-sensor when a second camera lands` | 2592 × 1944 is hardcoded and is the ELP's calibration size. Blocks *any* second camera, including the Microdia |
| a **non-V4L2 backend** | new sibling of `CaptureBackend` | `libtoupcam` is not UVC (§4.3) |
| **bit depth** through the chain | `ImageSpectrumAcquisitionLogicModule`, `SpectralColorUtil` | everything assumes 8-bit gamma-encoded: the decode, the tie window, the 16 DN guard |
| **mono** path | the same | max-channel over three channels is meaningless with one channel |
| a **second calibration profile** | already supported | per-`SpectrometerProfile`, so this is data, not code |

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
  honest ceiling is ~850 nm.
- ⭐⭐ **A repeat of §4.1a's arithmetic against a re-seat-free protocol** ⇒ the only thing that would make
  bit depth matter is removing the term that dwarfs it. `SPEC_settled_measurement.md`'s capillary/one-fill
  work is that; until it lands, no detector change moves the verdict.
